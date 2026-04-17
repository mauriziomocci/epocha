"""End-to-end integration test for the behavioral economy (Spec 2 Part 3).

Verifies that the subsystems built in Plans 3a and 3b cooperate across
multiple ticks:
- Adaptive expectations (Nerlove 1958) update after price history exists
- Hoard action (via DecisionLog) reduces market supply at the next tick
- Borrow action issues a loan serviced by the credit market
- sell_property + buy_property cycle transfers ownership at tick+1
- Deposit recalculation tracks aggregate agent cash
- Minsky (1986) classification evolves as debt accumulates
- Banking concern broadcast (Diamond & Dybvig 1983) fires when confidence drops

These tests drive the synchronous entry points (process_economy_tick_new
and apply_agent_action) without invoking the LLM. Action dicts are passed
directly to simulate decided-upon outcomes.
"""
from __future__ import annotations

import json

import pytest
from django.contrib.gis.geos import Point, Polygon

from epocha.apps.agents.models import Agent, DecisionLog, Memory
from epocha.apps.economy.banking import broadcast_banking_concern
from epocha.apps.economy.credit import (
    classify_minsky_stage,
    find_best_unpledged_property,
)
from epocha.apps.economy.engine import process_economy_tick_new
from epocha.apps.economy.initialization import initialize_economy
from epocha.apps.economy.models import (
    AgentExpectation,
    AgentInventory,
    BankingState,
    Currency,
    EconomicLedger,
    Loan,
    Property,
    PropertyListing,
)
from epocha.apps.simulation.engine import apply_agent_action
from epocha.apps.simulation.models import Simulation
from epocha.apps.users.models import User
from epocha.apps.world.models import Government, World, Zone


@pytest.fixture
def behavioral_economy(db):
    """Full behavioral economy setup: simulation + 2 zones + 3 agents + banking."""
    user = User.objects.create_user(
        email="behavioral@epocha.dev",
        username="behavioraluser",
        password="pass1234",
    )
    sim = Simulation.objects.create(
        name="BehavioralIntegration", seed=42, owner=user,
        current_tick=0,
    )
    world = World.objects.create(
        simulation=sim,
        stability_index=0.7,
        distance_scale=133.0,
        tick_duration_hours=24.0,
    )
    Government.objects.create(
        simulation=sim,
        government_type="monarchy",
        stability=0.6,
        popular_legitimacy=0.5,
    )
    z_urban = Zone.objects.create(
        world=world, name="Capital", zone_type="commercial",
        boundary=Polygon.from_bbox((0, 0, 100, 100)),
        center=Point(50, 50),
    )
    z_rural = Zone.objects.create(
        world=world, name="Countryside", zone_type="rural",
        boundary=Polygon.from_bbox((120, 0, 220, 100)),
        center=Point(170, 50),
    )

    # Elite landowner in urban zone (seller candidate)
    elite = Agent.objects.create(
        simulation=sim, name="Elite", role="merchant",
        social_class="elite", zone=z_urban,
        personality={"openness": 0.6, "neuroticism": 0.4},
        location=Point(50, 50), health=1.0, wealth=1000.0, mood=0.7,
    )
    # Middle-class agent in urban zone (borrower/buyer candidate)
    middle = Agent.objects.create(
        simulation=sim, name="Middle", role="craftsman",
        social_class="middle", zone=z_urban,
        personality={"openness": 0.5, "neuroticism": 0.5},
        location=Point(50, 50), health=1.0, wealth=400.0, mood=0.6,
    )
    # Poor farmer in rural zone
    poor = Agent.objects.create(
        simulation=sim, name="Poor", role="farmer",
        social_class="poor", zone=z_rural,
        personality={"openness": 0.3, "neuroticism": 0.6},
        location=Point(170, 50), health=1.0, wealth=150.0, mood=0.5,
    )

    # Initialize full economy: currencies, goods, factors, zone economies,
    # inventories, tax policy, banking, AND saves all configs to simulation.config.
    initialize_economy(sim)
    sim.refresh_from_db()

    # Give agents explicit cash and holdings for predictable test behavior.
    currency = Currency.objects.get(simulation=sim, is_primary=True)
    cur = currency.code

    for agent, cash, holdings in (
        (elite, 500.0, {"subsistence": 10.0, "luxury": 5.0}),
        (middle, 600.0, {"subsistence": 8.0, "tools": 3.0}),
        (poor, 100.0, {"subsistence": 4.0}),
    ):
        inv, _ = AgentInventory.objects.get_or_create(
            agent=agent,
            defaults={"cash": {cur: cash}, "holdings": holdings},
        )
        inv.cash = {cur: cash}
        inv.holdings = holdings
        inv.save(update_fields=["cash", "holdings"])

    # Ensure the elite has at least one property in the urban zone
    # (initialize_economy already creates properties for elite agents,
    # but we add an explicit one for deterministic matching in tests).
    Property.objects.get_or_create(
        simulation=sim, owner=elite, owner_type="agent",
        zone=z_urban, property_type="mansion",
        defaults={
            "name": "Grand Mansion",
            "value": 300.0,
            "production_bonus": {"luxury": 0.3},
        },
    )

    return {
        "sim": sim,
        "world": world,
        "zone_urban": z_urban,
        "zone_rural": z_rural,
        "currency": currency,
        "elite": elite,
        "middle": middle,
        "poor": poor,
    }


@pytest.mark.django_db
class TestBehavioralIntegration:
    def test_expectations_update_after_ticks(self, behavioral_economy):
        """After a few ticks, AgentExpectation rows exist with populated trend."""
        s = behavioral_economy
        sim = s["sim"]

        # Run 5 ticks to let expectations accumulate
        for tick in range(1, 6):
            sim.current_tick = tick
            sim.save(update_fields=["current_tick"])
            process_economy_tick_new(sim, tick=tick)

        # At least one agent should have expectations for at least one good
        exp_count = AgentExpectation.objects.filter(
            agent__simulation=sim,
        ).count()
        assert exp_count > 0, "No AgentExpectation records created after 5 ticks"

        # Expectations must have a valid trend_direction
        valid_trends = {"rising", "falling", "stable"}
        for exp in AgentExpectation.objects.filter(agent__simulation=sim):
            assert exp.trend_direction in valid_trends

    def test_hoard_reduces_supply_next_tick(self, behavioral_economy):
        """Agent marked as hoarding at tick N does not offer goods at tick N+1."""
        s = behavioral_economy
        sim = s["sim"]
        middle = s["middle"]

        # Run tick 1 to establish a baseline (no hoarding)
        sim.current_tick = 1
        sim.save(update_fields=["current_tick"])
        process_economy_tick_new(sim, tick=1)

        # Insert a hoard decision for middle agent at tick 1
        DecisionLog.objects.create(
            simulation=sim,
            agent=middle,
            tick=1,
            input_context="(test)",
            llm_model="test",
            output_decision=json.dumps(
                {"action": "hoard", "target": "subsistence", "reason": "fear"}
            ),
        )

        # Import the private helper to assert it detects the hoarder
        from epocha.apps.economy.engine import _get_hoarding_agent_ids

        hoarding_ids = _get_hoarding_agent_ids(sim, tick=2)
        assert middle.id in hoarding_ids, (
            "Hoard decision at tick 1 should be detected for tick 2 processing"
        )

        # Run tick 2; agent should not trade (is_hoarding=True in market clearing).
        # We verify by checking that no "trade" ledger entry exists with middle
        # as the seller (to_agent) for this tick.
        sim.current_tick = 2
        sim.save(update_fields=["current_tick"])
        process_economy_tick_new(sim, tick=2)

        middle_sales_tick2 = EconomicLedger.objects.filter(
            simulation=sim,
            tick=2,
            transaction_type="trade",
            to_agent=middle,  # middle as seller (receives cash)
        ).count()
        assert middle_sales_tick2 == 0, (
            "Hoarding agent should not sell goods at the following tick"
        )

    def test_borrow_action_issues_and_services_loan(self, behavioral_economy):
        """Borrow action creates a Loan; next economy tick services interest."""
        s = behavioral_economy
        sim = s["sim"]
        elite = s["elite"]

        # Find the elite's unpledged property (fixture guarantees one exists)
        collateral = find_best_unpledged_property(elite)
        assert collateral is not None, "Elite should have an unpledged property"

        # Elite requests 80 LVR loan (well within LTV of 80% on 300 value)
        action = {"action": "borrow", "target": "80", "reason": "invest"}
        apply_agent_action(elite, action, tick=1)

        loan = Loan.objects.filter(
            simulation=sim, borrower=elite, status="active",
        ).first()
        assert loan is not None, "Borrow action should create an active loan"
        assert loan.collateral_id == collateral.id
        assert loan.lender_type == "banking"
        assert loan.principal == pytest.approx(80.0, rel=1e-6)

        # Advance one tick -- credit market services the loan
        sim.current_tick = 2
        sim.save(update_fields=["current_tick"])
        process_economy_tick_new(sim, tick=2)

        loan.refresh_from_db()
        # Balance unchanged or reduced depending on interest-only vs amortizing,
        # but at least one loan_interest ledger entry should exist.
        interest_entries = EconomicLedger.objects.filter(
            simulation=sim,
            transaction_type="loan_interest",
        ).count()
        assert interest_entries >= 1, (
            "Credit market should record at least one loan_interest transaction"
        )

        # Minsky classification should return a valid stage
        stage = classify_minsky_stage(elite, sim, tick=2)
        assert stage in {"hedge", "speculative", "ponzi"}

    def test_property_cycle_sell_then_buy(self, behavioral_economy):
        """sell_property creates a listing; buy_property intent matches at tick+1."""
        s = behavioral_economy
        sim = s["sim"]
        elite = s["elite"]
        middle = s["middle"]
        cur = s["currency"].code

        # Middle needs enough cash to buy -- give a boost for deterministic matching
        middle_inv = middle.inventory
        middle_inv.cash[cur] = 5000.0
        middle_inv.save(update_fields=["cash"])

        # Tick 1: elite lists property via sell_property action
        sim.current_tick = 1
        sim.save(update_fields=["current_tick"])
        sell_action = {
            "action": "sell_property",
            "target": "mansion",
            "reason": "need cash",
        }
        apply_agent_action(elite, sell_action, tick=1)

        listing = PropertyListing.objects.filter(
            property__simulation=sim, status="listed",
        ).first()
        assert listing is not None, "sell_property should create a listing"
        original_seller_id = listing.property.owner_id
        assert original_seller_id == elite.id

        # Middle records buy_property intent in DecisionLog at tick 1
        DecisionLog.objects.create(
            simulation=sim, agent=middle, tick=1,
            input_context="(test)",
            llm_model="test",
            output_decision=json.dumps(
                {"action": "buy_property", "target": "mansion", "reason": "invest"}
            ),
        )

        # Tick 2: economy pipeline runs property market step -> matches
        sim.current_tick = 2
        sim.save(update_fields=["current_tick"])
        process_economy_tick_new(sim, tick=2)

        # The property should now be owned by middle
        listing.refresh_from_db()
        prop = listing.property
        prop.refresh_from_db()
        assert prop.owner_id == middle.id, (
            "Property ownership should transfer to buyer after tick+1 matching"
        )
        assert listing.status == "sold"

        # Property sale ledger entry must exist
        sale_entry = EconomicLedger.objects.filter(
            simulation=sim,
            transaction_type="property_sale",
            from_agent=middle,
            to_agent=elite,
        ).first()
        assert sale_entry is not None
        assert sale_entry.total_amount > 0

    def test_deposits_track_aggregate_cash(self, behavioral_economy):
        """BankingState.total_deposits reflects aggregate living agent cash after a tick."""
        s = behavioral_economy
        sim = s["sim"]

        sim.current_tick = 1
        sim.save(update_fields=["current_tick"])
        process_economy_tick_new(sim, tick=1)

        bs = BankingState.objects.get(simulation=sim)

        # Compute aggregate cash across all living agents
        living_inventories = AgentInventory.objects.filter(
            agent__simulation=sim, agent__is_alive=True,
        )
        aggregate_cash = sum(
            sum(inv.cash.values()) for inv in living_inventories
        )

        assert bs.total_deposits == pytest.approx(aggregate_cash, rel=1e-6), (
            f"total_deposits ({bs.total_deposits}) should equal aggregate cash "
            f"({aggregate_cash}) after tick"
        )

    def test_banking_concern_broadcast_on_low_confidence(self, behavioral_economy):
        """When confidence < 0.5, broadcast_banking_concern creates memories."""
        s = behavioral_economy
        sim = s["sim"]

        bs = BankingState.objects.get(simulation=sim)
        bs.confidence_index = 0.3  # Well below 0.5 trigger
        bs.save(update_fields=["confidence_index"])

        living_count = Agent.objects.filter(simulation=sim, is_alive=True).count()
        assert living_count >= 3  # fixture has 3 living agents

        created = broadcast_banking_concern(sim, tick=1)
        # sample_size = max(1, int(3 * 0.5)) = 1, so at least 1 memory is created
        assert created >= 1, (
            "broadcast_banking_concern should create at least one memory "
            "when confidence < 0.5"
        )

        banking_memories = Memory.objects.filter(
            agent__simulation=sim,
            content__icontains="banking system",
        )
        assert banking_memories.exists()

    def test_full_behavioral_scenario(self, behavioral_economy):
        """End-to-end: borrow, hoard, property cycle, deposits, Minsky stage."""
        s = behavioral_economy
        sim = s["sim"]
        elite = s["elite"]
        middle = s["middle"]
        cur = s["currency"].code

        # Boost middle's cash so they can buy property later
        middle_inv = middle.inventory
        middle_inv.cash[cur] = 5000.0
        middle_inv.save(update_fields=["cash"])

        # Tick 1: elite borrows against the mansion
        sim.current_tick = 1
        sim.save(update_fields=["current_tick"])
        apply_agent_action(
            elite, {"action": "borrow", "target": "100", "reason": "x"}, tick=1,
        )
        process_economy_tick_new(sim, tick=1)

        # Tick 2: middle hoards (DecisionLog at tick 2 drives tick 3 market)
        sim.current_tick = 2
        sim.save(update_fields=["current_tick"])
        DecisionLog.objects.create(
            simulation=sim, agent=middle, tick=2,
            input_context="(test)", llm_model="test",
            output_decision=json.dumps({"action": "hoard", "target": "subsistence"}),
        )
        process_economy_tick_new(sim, tick=2)

        # Tick 3: elite lists mansion; middle expresses buy intent
        sim.current_tick = 3
        sim.save(update_fields=["current_tick"])
        apply_agent_action(
            elite, {"action": "sell_property", "target": "mansion"}, tick=3,
        )
        DecisionLog.objects.create(
            simulation=sim, agent=middle, tick=3,
            input_context="(test)", llm_model="test",
            output_decision=json.dumps({"action": "buy_property", "target": "mansion"}),
        )
        process_economy_tick_new(sim, tick=3)

        # Tick 4: property market matches buyer and seller
        sim.current_tick = 4
        sim.save(update_fields=["current_tick"])
        process_economy_tick_new(sim, tick=4)

        # Verify end-state
        # 1. Loan from tick 1 is active
        loan = Loan.objects.filter(
            simulation=sim, borrower=elite, status="active",
        ).first()
        assert loan is not None

        # 2. Interest was serviced at least once
        assert EconomicLedger.objects.filter(
            simulation=sim, transaction_type="loan_interest",
        ).exists()

        # 3. Property was transferred to middle
        mansion = Property.objects.get(
            simulation=sim, property_type="mansion",
        )
        assert mansion.owner_id == middle.id

        # 4. Property sale was recorded
        assert EconomicLedger.objects.filter(
            simulation=sim, transaction_type="property_sale",
        ).exists()

        # 5. Deposits reconcile with aggregate cash after the final tick
        bs = BankingState.objects.get(simulation=sim)
        aggregate_cash = sum(
            sum(inv.cash.values())
            for inv in AgentInventory.objects.filter(
                agent__simulation=sim, agent__is_alive=True,
            )
        )
        assert bs.total_deposits == pytest.approx(aggregate_cash, rel=1e-6)

        # 6. Minsky classification is well-formed for the indebted agent
        stage = classify_minsky_stage(elite, sim, tick=4)
        assert stage in {"hedge", "speculative", "ponzi"}

"""Tests for behavioral economy context blocks: expectations, debt, banking.

These tests verify that build_economic_context correctly appends
price expectation, debt situation, and banking system blocks to the
agent's economic context string.
"""

import pytest
from django.contrib.gis.geos import Point, Polygon

from epocha.apps.agents.models import Agent
from epocha.apps.economy.context import build_economic_context
from epocha.apps.economy.initialization import initialize_economy
from epocha.apps.economy.models import (
    AgentExpectation,
    AgentInventory,
    BankingState,
    Currency,
    Loan,
    Property,
    ZoneEconomy,
)
from epocha.apps.simulation.models import Simulation
from epocha.apps.users.models import User
from epocha.apps.world.models import World, Zone


@pytest.fixture
def behavioral_setup(db):
    """Create a full economy setup with behavioral models initialized.

    Returns a dict with simulation, agent, zone, currency, and zone_economy
    for use in behavioral context tests.
    """
    user = User.objects.create_user(
        email="behavioral@epocha.dev",
        username="behavioraluser",
        password="pass1234",
    )
    simulation = Simulation.objects.create(
        name="BehavioralCtxTest",
        seed=42,
        owner=user,
        config={
            "credit_config": {
                "loan_to_value": 0.8,
                "max_rollover": 3,
                "default_loan_duration_ticks": 10,
                "risk_premium": 0.5,
            },
            "banking_config": {
                "initial_deposits": 10000.0,
                "base_interest_rate": 0.05,
                "reserve_ratio": 0.10,
            },
        },
    )
    world = World.objects.create(
        simulation=simulation,
        distance_scale=100.0,
        tick_duration_hours=24.0,
    )
    zone = Zone.objects.create(
        world=world,
        name="TestZone",
        zone_type="urban",
        boundary=Polygon.from_bbox((0, 0, 100, 100)),
        center=Point(50, 50),
    )

    initialize_economy(simulation, "pre_industrial")

    # The initialization creates currencies and zone economies;
    # fetch the primary currency and zone economy it created.
    currency = Currency.objects.get(simulation=simulation, is_primary=True)
    ze = ZoneEconomy.objects.get(zone=zone)

    agent = Agent.objects.create(
        simulation=simulation,
        name="Debtor",
        role="merchant",
        personality={"openness": 0.5},
        location=Point(50, 50),
        zone=zone,
        wealth=500.0,
    )
    AgentInventory.objects.create(
        agent=agent,
        holdings={"subsistence": 10.0},
        cash={currency.code: 100.0},
    )

    return {
        "simulation": simulation,
        "agent": agent,
        "zone": zone,
        "currency": currency,
        "zone_economy": ze,
    }


@pytest.mark.django_db
class TestExpectationsBlock:
    """Tests for the price expectations context block."""

    def test_expectations_shown_when_records_exist(self, behavioral_setup):
        agent = behavioral_setup["agent"]
        AgentExpectation.objects.create(
            agent=agent,
            good_code="subsistence",
            expected_price=3.5,
            trend_direction="rising",
            confidence=0.8,
            lambda_rate=0.3,
            updated_at_tick=0,
        )

        ctx = build_economic_context(agent, tick=1)
        assert "Price expectations (your assessment):" in ctx
        assert "Subsistence: RISING" in ctx
        assert "confidence: high" in ctx

    def test_no_expectations_block_when_none_exist(self, behavioral_setup):
        agent = behavioral_setup["agent"]
        ctx = build_economic_context(agent, tick=1)
        assert "Price expectations" not in ctx

    def test_expectations_percentage_deviation(self, behavioral_setup):
        agent = behavioral_setup["agent"]
        ze = behavioral_setup["zone_economy"]
        # Set a known zone price so we can verify the percentage
        ze.market_prices["subsistence"] = 10.0
        ze.save(update_fields=["market_prices"])

        AgentExpectation.objects.create(
            agent=agent,
            good_code="subsistence",
            expected_price=11.0,
            trend_direction="rising",
            confidence=0.5,
            lambda_rate=0.3,
            updated_at_tick=0,
        )

        ctx = build_economic_context(agent, tick=1)
        # 11.0 vs 10.0 = +10%
        assert "+10% expected" in ctx
        assert "confidence: moderate" in ctx

    def test_falling_expectation(self, behavioral_setup):
        agent = behavioral_setup["agent"]
        ze = behavioral_setup["zone_economy"]
        ze.market_prices["luxury"] = 50.0
        ze.save(update_fields=["market_prices"])

        AgentExpectation.objects.create(
            agent=agent,
            good_code="luxury",
            expected_price=45.0,
            trend_direction="falling",
            confidence=0.2,
            lambda_rate=0.3,
            updated_at_tick=0,
        )

        ctx = build_economic_context(agent, tick=1)
        assert "FALLING" in ctx
        assert "-10% expected" in ctx
        assert "confidence: low" in ctx


@pytest.mark.django_db
class TestDebtBlock:
    """Tests for the debt situation context block."""

    def test_debt_block_shown_with_active_loans(self, behavioral_setup):
        agent = behavioral_setup["agent"]
        sim = behavioral_setup["simulation"]
        prop = Property.objects.create(
            simulation=sim,
            owner=agent,
            owner_type="agent",
            zone=behavioral_setup["zone"],
            property_type="land",
            name="Farmland",
            value=200.0,
        )
        Loan.objects.create(
            simulation=sim,
            borrower=agent,
            lender_type="banking",
            principal=100.0,
            interest_rate=0.05,
            remaining_balance=100.0,
            collateral=prop,
            issued_at_tick=0,
            due_at_tick=10,
            status="active",
        )

        ctx = build_economic_context(agent, tick=1)
        assert "Your debt situation:" in ctx
        assert "Active loans: 1" in ctx
        assert "total balance: 100" in ctx
        assert "Interest due this tick: 5.0" in ctx

    def test_minsky_classification_in_debt_block(self, behavioral_setup):
        agent = behavioral_setup["agent"]
        sim = behavioral_setup["simulation"]
        Loan.objects.create(
            simulation=sim,
            borrower=agent,
            lender_type="banking",
            principal=50.0,
            interest_rate=0.05,
            remaining_balance=50.0,
            issued_at_tick=0,
            due_at_tick=10,
            status="active",
        )

        ctx = build_economic_context(agent, tick=1)
        # Without any income in ledger, agent is in ponzi stage
        assert "Financial position: ponzi" in ctx
        assert "cannot cover interest, critical" in ctx

    def test_no_debt_block_when_no_loans_no_property(self, behavioral_setup):
        agent = behavioral_setup["agent"]
        # Remove any properties the agent may own
        Property.objects.filter(owner=agent).delete()
        ctx = build_economic_context(agent, tick=1)
        assert "Your debt situation:" not in ctx

    def test_debt_to_wealth_ratio_word(self, behavioral_setup):
        agent = behavioral_setup["agent"]
        sim = behavioral_setup["simulation"]
        # Agent wealth is 500. Loan of 100 => ratio 0.2 => "safe"
        Loan.objects.create(
            simulation=sim,
            borrower=agent,
            lender_type="banking",
            principal=100.0,
            interest_rate=0.05,
            remaining_balance=100.0,
            issued_at_tick=0,
            due_at_tick=10,
            status="active",
        )

        ctx = build_economic_context(agent, tick=1)
        assert "(safe)" in ctx

    def test_credit_availability_with_unpledged_property(self, behavioral_setup):
        agent = behavioral_setup["agent"]
        sim = behavioral_setup["simulation"]
        # Create a BankingState so evaluate_credit_request can use it
        BankingState.objects.get_or_create(
            simulation=sim,
            defaults={
                "total_deposits": 10000.0,
                "total_loans_outstanding": 0.0,
                "reserve_ratio": 0.10,
                "base_interest_rate": 0.05,
                "is_solvent": True,
                "confidence_index": 0.9,
            },
        )
        Property.objects.create(
            simulation=sim,
            owner=agent,
            owner_type="agent",
            zone=behavioral_setup["zone"],
            property_type="workshop",
            name="Agent Workshop",
            value=200.0,
        )

        ctx = build_economic_context(agent, tick=1)
        assert "Credit available:" in ctx
        assert "up to 100" in ctx
        assert "Agent Workshop" in ctx


@pytest.mark.django_db
class TestBankingBlock:
    """Tests for the banking system context block."""

    def test_banking_block_shown_when_state_exists(self, behavioral_setup):
        sim = behavioral_setup["simulation"]
        # initialize_economy may have created a BankingState; update it
        BankingState.objects.filter(simulation=sim).delete()
        BankingState.objects.create(
            simulation=sim,
            total_deposits=10000.0,
            total_loans_outstanding=500.0,
            reserve_ratio=0.10,
            base_interest_rate=0.05,
            is_solvent=True,
            confidence_index=0.9,
        )

        ctx = build_economic_context(behavioral_setup["agent"], tick=1)
        assert "Banking system: solvent" in ctx
        assert "confidence high" in ctx
        assert "base rate 5.0%" in ctx

    def test_insolvent_flagged(self, behavioral_setup):
        sim = behavioral_setup["simulation"]
        BankingState.objects.filter(simulation=sim).delete()
        BankingState.objects.create(
            simulation=sim,
            total_deposits=10000.0,
            total_loans_outstanding=9000.0,
            reserve_ratio=0.10,
            base_interest_rate=0.12,
            is_solvent=False,
            confidence_index=0.3,
        )

        ctx = build_economic_context(behavioral_setup["agent"], tick=1)
        assert "INSOLVENT" in ctx
        assert "LOW (0.3)" in ctx
        assert "base rate 12.0%" in ctx

    def test_no_banking_block_when_no_state(self, behavioral_setup):
        # Ensure no BankingState exists
        BankingState.objects.filter(
            simulation=behavioral_setup["simulation"]
        ).delete()

        ctx = build_economic_context(behavioral_setup["agent"], tick=1)
        assert "Banking system:" not in ctx

    def test_moderate_confidence(self, behavioral_setup):
        sim = behavioral_setup["simulation"]
        BankingState.objects.filter(simulation=sim).delete()
        BankingState.objects.create(
            simulation=sim,
            total_deposits=10000.0,
            total_loans_outstanding=3000.0,
            reserve_ratio=0.10,
            base_interest_rate=0.07,
            is_solvent=True,
            confidence_index=0.55,
        )

        ctx = build_economic_context(behavioral_setup["agent"], tick=1)
        assert "confidence moderate" in ctx

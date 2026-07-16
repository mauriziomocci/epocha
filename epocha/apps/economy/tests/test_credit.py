"""Tests for the credit market lifecycle: Minsky classification, loan issuance,
interest servicing, maturity handling, defaults, and cascade propagation.
"""

import pytest
from django.contrib.gis.geos import Point, Polygon

from epocha.apps.agents.models import Agent, Memory, ReputationScore
from epocha.apps.economy.credit import (
    classify_minsky_stage,
    evaluate_credit_request,
    issue_loan,
    process_default_cascade,
    process_defaults,
    process_maturity,
    service_loans,
)
from epocha.apps.economy.models import (
    AgentInventory,
    BankingState,
    Currency,
    EconomicLedger,
    Loan,
    Property,
)
from epocha.apps.simulation.models import Simulation
from epocha.apps.users.models import User
from epocha.apps.world.models import World, Zone


@pytest.fixture
def user(db):
    return User.objects.create_user(
        email="credit@epocha.dev",
        username="credituser",
        password="pass1234",
    )


@pytest.fixture
def simulation(user):
    sim = Simulation.objects.create(
        name="CreditTest",
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
    return sim


@pytest.fixture
def world_and_zone(simulation):
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
    return world, zone


@pytest.fixture
def currency(simulation):
    return Currency.objects.create(
        simulation=simulation,
        code="TST",
        name="Test Coin",
        symbol="T",
        is_primary=True,
        total_supply=50000.0,
    )


@pytest.fixture
def banking_state(simulation):
    return BankingState.objects.create(
        simulation=simulation,
        total_deposits=10000.0,
        total_loans_outstanding=0.0,
        reserve_ratio=0.10,
        base_interest_rate=0.05,
        is_solvent=True,
        confidence_index=1.0,
    )


@pytest.fixture
def borrower(simulation, world_and_zone, currency):
    _, zone = world_and_zone
    agent = Agent.objects.create(
        simulation=simulation,
        name="Borrower",
        role="merchant",
        social_class="middle",
        zone=zone,
        wealth=500.0,
        personality={"openness": 0.5},
        location=Point(50, 50),
        health=1.0,
    )
    AgentInventory.objects.create(
        agent=agent,
        holdings={},
        cash={currency.code: 200.0},
    )
    return agent


@pytest.fixture
def lender(simulation, world_and_zone, currency):
    _, zone = world_and_zone
    agent = Agent.objects.create(
        simulation=simulation,
        name="Lender",
        role="merchant",
        social_class="elite",
        zone=zone,
        wealth=2000.0,
        personality={"openness": 0.5},
        location=Point(50, 50),
        health=1.0,
    )
    AgentInventory.objects.create(
        agent=agent,
        holdings={},
        cash={currency.code: 1500.0},
    )
    return agent


@pytest.fixture
def collateral_property(simulation, world_and_zone, borrower):
    _, zone = world_and_zone
    return Property.objects.create(
        simulation=simulation,
        owner=borrower,
        owner_type="agent",
        zone=zone,
        property_type="land",
        name="Test Land",
        value=500.0,
        production_bonus={},
    )


@pytest.mark.django_db
class TestMinskyClassification:
    """Verify Minsky (1986) financing stage classification."""

    def test_hedge_when_income_covers_all(
        self,
        simulation,
        borrower,
        currency,
    ):
        """Agent with income exceeding interest + principal is 'hedge'."""
        # Create a wage record for previous tick
        EconomicLedger.objects.create(
            simulation=simulation,
            tick=0,
            to_agent=borrower,
            currency=currency,
            total_amount=100.0,
            transaction_type="wage",
        )
        # Create a small active loan
        Loan.objects.create(
            simulation=simulation,
            borrower=borrower,
            lender_type="banking",
            principal=50.0,
            interest_rate=0.05,
            remaining_balance=50.0,
            issued_at_tick=0,
            due_at_tick=1,
            status="active",
        )

        stage = classify_minsky_stage(borrower, simulation, tick=1)
        assert stage == "hedge"

    def test_speculative_when_income_covers_interest_only(
        self,
        simulation,
        borrower,
        currency,
    ):
        """Agent with income covering interest but not principal is 'speculative'."""
        EconomicLedger.objects.create(
            simulation=simulation,
            tick=0,
            to_agent=borrower,
            currency=currency,
            total_amount=10.0,
            transaction_type="wage",
        )
        # Large loan due at tick 1: interest=500*0.05=25, principal=500
        Loan.objects.create(
            simulation=simulation,
            borrower=borrower,
            lender_type="banking",
            principal=500.0,
            interest_rate=0.01,
            remaining_balance=500.0,
            issued_at_tick=0,
            due_at_tick=1,
            status="active",
        )

        stage = classify_minsky_stage(borrower, simulation, tick=1)
        # income=10 >= interest=5, but 10 < 5+500 => speculative
        assert stage == "speculative"

    def test_ponzi_when_income_below_interest(
        self,
        simulation,
        borrower,
        currency,
    ):
        """Agent with income below interest payments is 'ponzi'."""
        EconomicLedger.objects.create(
            simulation=simulation,
            tick=0,
            to_agent=borrower,
            currency=currency,
            total_amount=1.0,
            transaction_type="wage",
        )
        Loan.objects.create(
            simulation=simulation,
            borrower=borrower,
            lender_type="banking",
            principal=1000.0,
            interest_rate=0.10,
            remaining_balance=1000.0,
            issued_at_tick=0,
            status="active",
        )

        stage = classify_minsky_stage(borrower, simulation, tick=1)
        # income=1 < interest=100 => ponzi
        assert stage == "ponzi"

    def test_no_debt_is_hedge(self, simulation, borrower, currency):
        """Agent with no loans is always 'hedge' regardless of income."""
        stage = classify_minsky_stage(borrower, simulation, tick=1)
        assert stage == "hedge"


@pytest.mark.django_db
class TestCreditEvaluation:
    """Verify Stiglitz & Weiss (1981) credit evaluation logic."""

    def test_within_credit_limit(
        self,
        simulation,
        borrower,
        collateral_property,
        banking_state,
    ):
        """Loan within LTV * collateral value is approved."""
        approved, result = evaluate_credit_request(
            borrower,
            amount=300.0,
            collateral_property=collateral_property,
            simulation=simulation,
        )
        assert approved is True
        # result is the interest rate (float)
        assert isinstance(result, float)
        assert result > 0.0

    def test_exceeds_credit_limit(
        self,
        simulation,
        borrower,
        collateral_property,
        banking_state,
    ):
        """Loan exceeding LTV * collateral value is rejected."""
        # LTV=0.8, collateral=500 => limit=400; request 500 => rejected
        approved, reason = evaluate_credit_request(
            borrower,
            amount=500.0,
            collateral_property=collateral_property,
            simulation=simulation,
        )
        assert approved is False
        assert reason == "exceeds credit limit"

    def test_no_collateral_zero_limit(
        self,
        simulation,
        borrower,
        banking_state,
    ):
        """No collateral means zero credit limit."""
        approved, reason = evaluate_credit_request(
            borrower,
            amount=100.0,
            collateral_property=None,
            simulation=simulation,
        )
        assert approved is False
        assert reason == "exceeds credit limit"

    def test_interest_rate_increases_with_debt(
        self,
        simulation,
        borrower,
        collateral_property,
        currency,
        banking_state,
    ):
        """Interest rate should be higher when the borrower has existing debt."""
        # First evaluation: no existing debt
        _, rate_clean = evaluate_credit_request(
            borrower,
            amount=100.0,
            collateral_property=collateral_property,
            simulation=simulation,
        )

        # Add existing debt
        Loan.objects.create(
            simulation=simulation,
            borrower=borrower,
            lender_type="banking",
            principal=200.0,
            interest_rate=0.05,
            remaining_balance=200.0,
            issued_at_tick=0,
            status="active",
        )

        _, rate_leveraged = evaluate_credit_request(
            borrower,
            amount=100.0,
            collateral_property=collateral_property,
            simulation=simulation,
        )

        assert rate_leveraged > rate_clean

    def test_insolvent_bank_rejects(
        self,
        simulation,
        borrower,
        collateral_property,
        banking_state,
    ):
        """Insolvent banking system rejects all credit requests."""
        banking_state.is_solvent = False
        banking_state.save(update_fields=["is_solvent"])

        approved, reason = evaluate_credit_request(
            borrower,
            amount=100.0,
            collateral_property=collateral_property,
            simulation=simulation,
        )
        assert approved is False
        assert reason == "banking system insolvent"


@pytest.mark.django_db
class TestLoanIssuance:
    """Verify loan creation and cash transfer."""

    def test_banking_loan_transfers_cash(
        self,
        simulation,
        borrower,
        currency,
        banking_state,
    ):
        """Banking loan increases borrower cash and banking outstanding."""
        initial_cash = borrower.inventory.cash.get(currency.code, 0.0)

        loan = issue_loan(
            simulation=simulation,
            lender=None,
            borrower=borrower,
            amount=100.0,
            interest_rate=0.05,
            collateral=None,
            tick=1,
            lender_type="banking",
        )

        borrower.inventory.refresh_from_db()
        banking_state.refresh_from_db()

        assert loan.status == "active"
        assert loan.principal == 100.0
        assert borrower.inventory.cash[currency.code] == initial_cash + 100.0
        assert banking_state.total_loans_outstanding == 100.0

    def test_agent_loan_transfers_between_agents(
        self,
        simulation,
        lender,
        borrower,
        currency,
    ):
        """Agent-to-agent loan moves cash from lender to borrower."""
        lender_initial = lender.inventory.cash[currency.code]
        borrower_initial = borrower.inventory.cash[currency.code]

        loan = issue_loan(
            simulation=simulation,
            lender=lender,
            borrower=borrower,
            amount=100.0,
            interest_rate=0.05,
            collateral=None,
            tick=1,
            lender_type="agent",
        )

        lender.inventory.refresh_from_db()
        borrower.inventory.refresh_from_db()

        assert loan.lender_type == "agent"
        assert lender.inventory.cash[currency.code] == lender_initial - 100.0
        assert borrower.inventory.cash[currency.code] == borrower_initial + 100.0

    def test_loan_recorded_in_ledger(
        self,
        simulation,
        borrower,
        currency,
        banking_state,
    ):
        """Loan issuance creates a ledger entry."""
        issue_loan(
            simulation=simulation,
            lender=None,
            borrower=borrower,
            amount=100.0,
            interest_rate=0.05,
            collateral=None,
            tick=1,
            lender_type="banking",
        )
        entries = EconomicLedger.objects.filter(
            simulation=simulation,
            tick=1,
            to_agent=borrower,
        )
        assert entries.count() == 1
        assert entries.first().total_amount == 100.0


@pytest.mark.django_db
class TestLoanServicing:
    """Verify interest payment collection."""

    def test_interest_deducted_from_borrower(
        self,
        simulation,
        borrower,
        currency,
        banking_state,
    ):
        """Interest is deducted from borrower cash each tick."""
        issue_loan(
            simulation=simulation,
            lender=None,
            borrower=borrower,
            amount=100.0,
            interest_rate=0.10,
            collateral=None,
            tick=0,
            lender_type="banking",
        )
        borrower.inventory.refresh_from_db()
        cash_after_loan = borrower.inventory.cash[currency.code]

        defaulting = service_loans(simulation, tick=1)

        borrower.inventory.refresh_from_db()
        # Interest = 100 * 0.10 = 10
        assert borrower.inventory.cash[currency.code] == pytest.approx(
            cash_after_loan - 10.0,
        )
        assert len(defaulting) == 0

    def test_interest_credited_to_agent_lender(
        self,
        simulation,
        lender,
        borrower,
        currency,
    ):
        """For agent loans, interest is credited to the lender."""
        issue_loan(
            simulation=simulation,
            lender=lender,
            borrower=borrower,
            amount=100.0,
            interest_rate=0.10,
            collateral=None,
            tick=0,
            lender_type="agent",
        )
        lender.inventory.refresh_from_db()
        lender_cash = lender.inventory.cash[currency.code]

        service_loans(simulation, tick=1)

        lender.inventory.refresh_from_db()
        assert lender.inventory.cash[currency.code] == pytest.approx(
            lender_cash + 10.0,
        )

    def test_insufficient_cash_marks_default(
        self,
        simulation,
        borrower,
        currency,
        banking_state,
    ):
        """Borrower with insufficient cash is flagged for default."""
        # Give borrower very little cash
        inv = borrower.inventory
        inv.cash = {currency.code: 1.0}
        inv.save(update_fields=["cash"])

        Loan.objects.create(
            simulation=simulation,
            borrower=borrower,
            lender_type="banking",
            principal=1000.0,
            interest_rate=0.10,
            remaining_balance=1000.0,
            issued_at_tick=0,
            status="active",
        )

        defaulting = service_loans(simulation, tick=1)
        assert len(defaulting) == 1


@pytest.mark.django_db
class TestMaturity:
    """Verify maturity handling: repay, rollover, default."""

    def test_repay_at_maturity(
        self,
        simulation,
        borrower,
        currency,
        banking_state,
    ):
        """Borrower with enough cash repays at maturity."""
        loan = issue_loan(
            simulation=simulation,
            lender=None,
            borrower=borrower,
            amount=100.0,
            interest_rate=0.05,
            collateral=None,
            tick=0,
            duration=5,
            lender_type="banking",
        )

        process_maturity(simulation, tick=5)

        loan.refresh_from_db()
        assert loan.status == "repaid"
        assert loan.remaining_balance == 0.0

    def test_rollover_increments_count(
        self,
        simulation,
        borrower,
        currency,
        banking_state,
    ):
        """Rollover creates new loan with incremented times_rolled_over."""
        # Give borrower only enough for interest, not principal
        inv = borrower.inventory
        inv.cash = {currency.code: 10.0}
        inv.save(update_fields=["cash"])

        loan = Loan.objects.create(
            simulation=simulation,
            borrower=borrower,
            lender_type="banking",
            principal=100.0,
            interest_rate=0.05,
            remaining_balance=100.0,
            issued_at_tick=0,
            due_at_tick=5,
            status="active",
        )

        process_maturity(simulation, tick=5)

        loan.refresh_from_db()
        assert loan.status == "rolled_over"

        new_loan = Loan.objects.filter(
            simulation=simulation,
            borrower=borrower,
            status="active",
        ).first()
        assert new_loan is not None
        assert new_loan.times_rolled_over == 1
        assert new_loan.interest_rate == pytest.approx(0.05 * 1.1)

    def test_max_rollover_triggers_default(
        self,
        simulation,
        borrower,
        currency,
        banking_state,
    ):
        """Exceeding max_rollover count causes default instead of rollover."""
        inv = borrower.inventory
        inv.cash = {currency.code: 10.0}
        inv.save(update_fields=["cash"])

        # max_rollover is 3 in our config
        loan = Loan.objects.create(
            simulation=simulation,
            borrower=borrower,
            lender_type="banking",
            principal=100.0,
            interest_rate=0.05,
            remaining_balance=100.0,
            issued_at_tick=0,
            due_at_tick=5,
            times_rolled_over=3,
            status="active",
        )

        process_maturity(simulation, tick=5)

        loan.refresh_from_db()
        assert loan.status == "defaulted"


@pytest.mark.django_db
class TestDefaults:
    """Verify default processing: collateral seizure, reputation damage."""

    def test_collateral_seized_on_default(
        self,
        simulation,
        borrower,
        lender,
        currency,
        collateral_property,
    ):
        """Collateral property is transferred to the lender on default."""
        Loan.objects.create(
            simulation=simulation,
            lender=lender,
            borrower=borrower,
            lender_type="agent",
            principal=200.0,
            interest_rate=0.10,
            remaining_balance=200.0,
            issued_at_tick=0,
            collateral=collateral_property,
            status="defaulted",
        )

        losses = process_defaults(simulation, tick=5)

        collateral_property.refresh_from_db()
        assert collateral_property.owner == lender
        assert collateral_property.owner_type == "agent"
        assert len(losses) == 1

    def test_banking_default_seizes_to_government(
        self,
        simulation,
        borrower,
        currency,
        collateral_property,
        banking_state,
    ):
        """Banking system defaults transfer collateral to government."""
        Loan.objects.create(
            simulation=simulation,
            lender=None,
            borrower=borrower,
            lender_type="banking",
            principal=200.0,
            interest_rate=0.10,
            remaining_balance=200.0,
            issued_at_tick=0,
            collateral=collateral_property,
            status="defaulted",
        )

        process_defaults(simulation, tick=5)

        collateral_property.refresh_from_db()
        assert collateral_property.owner is None
        assert collateral_property.owner_type == "government"

    def test_default_creates_reputation_damage(
        self,
        simulation,
        borrower,
        lender,
        currency,
    ):
        """Default creates negative memory and reputation for borrower."""
        Loan.objects.create(
            simulation=simulation,
            lender=lender,
            borrower=borrower,
            lender_type="agent",
            principal=200.0,
            interest_rate=0.10,
            remaining_balance=200.0,
            issued_at_tick=0,
            status="defaulted",
        )

        process_defaults(simulation, tick=5)

        # Memory created for borrower
        memories = Memory.objects.filter(agent=borrower, tick_created=5)
        assert memories.exists()
        assert "Defaulted" in memories.first().content

        # Lender's reputation of borrower should be negative
        score = ReputationScore.objects.get(holder=lender, target=borrower)
        assert score.reputation < 0


@pytest.mark.django_db
class TestDeadAgentLoanDefault:
    """Loans held by dead agents should be automatically defaulted."""

    def test_dead_agent_loans_default(self, simulation, world_and_zone, currency):
        """Active loans belonging to dead agents are marked defaulted."""
        _, zone = world_and_zone
        agent = Agent.objects.create(
            simulation=simulation,
            name="Ghost",
            role="farmer",
            personality={},
            zone=zone,
            wealth=100.0,
            mood=0.5,
            health=0.0,
            is_alive=False,
        )
        AgentInventory.objects.create(agent=agent, holdings={}, cash={currency.code: 50.0})
        Loan.objects.create(
            simulation=simulation,
            borrower=agent,
            lender_type="banking",
            principal=100.0,
            interest_rate=0.05,
            remaining_balance=80.0,
            issued_at_tick=0,
            due_at_tick=20,
            status="active",
        )
        from epocha.apps.economy.credit import default_dead_agent_loans

        count = default_dead_agent_loans(simulation)
        assert count == 1
        loan = Loan.objects.get(simulation=simulation, borrower=agent)
        assert loan.status == "defaulted"

    def test_alive_agent_loans_unaffected(self, simulation, world_and_zone, currency):
        """Active loans belonging to living agents are not touched."""
        _, zone = world_and_zone
        agent = Agent.objects.create(
            simulation=simulation,
            name="Alive",
            role="farmer",
            personality={},
            zone=zone,
            wealth=100.0,
            mood=0.5,
            health=1.0,
            is_alive=True,
        )
        AgentInventory.objects.create(agent=agent, holdings={}, cash={currency.code: 50.0})
        Loan.objects.create(
            simulation=simulation,
            borrower=agent,
            lender_type="banking",
            principal=100.0,
            interest_rate=0.05,
            remaining_balance=80.0,
            issued_at_tick=0,
            due_at_tick=20,
            status="active",
        )
        from epocha.apps.economy.credit import default_dead_agent_loans

        count = default_dead_agent_loans(simulation)
        assert count == 0
        loan = Loan.objects.get(simulation=simulation, borrower=agent)
        assert loan.status == "active"


@pytest.mark.django_db
class TestDoublePledgeProtection:
    """Properties already used as collateral should not be re-pledged."""

    def test_find_unpledged_property(self, simulation, world_and_zone, currency):
        """Returns the highest-value property not pledged as active loan collateral."""
        _, zone = world_and_zone
        agent = Agent.objects.create(
            simulation=simulation,
            name="Owner",
            role="merchant",
            personality={},
            zone=zone,
            wealth=500.0,
            mood=0.5,
            health=1.0,
        )
        AgentInventory.objects.create(agent=agent, holdings={}, cash={currency.code: 200.0})
        prop1 = Property.objects.create(
            simulation=simulation,
            owner=agent,
            owner_type="agent",
            zone=zone,
            property_type="farmland",
            name="Farm A",
            value=200.0,
        )
        prop2 = Property.objects.create(
            simulation=simulation,
            owner=agent,
            owner_type="agent",
            zone=zone,
            property_type="farmland",
            name="Farm B",
            value=300.0,
        )
        # Pledge prop2 as collateral for an active loan
        Loan.objects.create(
            simulation=simulation,
            borrower=agent,
            lender_type="banking",
            principal=100.0,
            interest_rate=0.05,
            remaining_balance=100.0,
            collateral=prop2,
            issued_at_tick=0,
            due_at_tick=20,
            status="active",
        )
        from epocha.apps.economy.credit import find_best_unpledged_property

        best = find_best_unpledged_property(agent)
        assert best is not None
        assert best.id == prop1.id  # prop2 is pledged, prop1 is free

    def test_find_unpledged_property_deterministic_on_value_tie(
        self, simulation, world_and_zone, currency
    ):
        """Round 9 re-audit finding R9-NEW-1 (run wf_6a4ff6e6-e80): the
        canonical borrow-path collateral selector sorted `.order_by("-value")`
        with no id tiebreak, while its context twin (context.py, pinned to
        `("-value", "id")` in commit 98da17e) and every sibling gate
        (sell_property, the listing match) are id-pinned. On an exact value
        tie Postgres returns rows in unspecified physical order, so the
        pledged collateral -- and the entire default-seizure path it drives
        -- was not reproducible across identically-seeded runs, and the
        property the LLM context advertised as "best" could differ from the
        one actually pledged. The selector must break value ties on id,
        matching the twin and the module convention. This pins the
        deterministic contract (the pre-fix behavior is DB-order dependent,
        which is the defect itself)."""
        _, zone = world_and_zone
        agent = Agent.objects.create(
            simulation=simulation,
            name="TieOwner",
            role="merchant",
            personality={},
            zone=zone,
            wealth=500.0,
            mood=0.5,
            health=1.0,
        )
        AgentInventory.objects.create(agent=agent, holdings={}, cash={currency.code: 200.0})
        # Two unpledged properties with EXACTLY equal value.
        prop_a = Property.objects.create(
            simulation=simulation,
            owner=agent,
            owner_type="agent",
            zone=zone,
            property_type="farmland",
            name="Farm A",
            value=250.0,
        )
        prop_b = Property.objects.create(
            simulation=simulation,
            owner=agent,
            owner_type="agent",
            zone=zone,
            property_type="farmland",
            name="Farm B",
            value=250.0,
        )
        from epocha.apps.economy.credit import find_best_unpledged_property

        best = find_best_unpledged_property(agent)
        assert best is not None
        # Deterministic: the lowest id wins the tie, matching the id-pinned
        # context twin and the (-value, id) module convention.
        assert best.id == min(prop_a.id, prop_b.id)

    def test_no_unpledged_property(self, simulation, world_and_zone, currency):
        """Returns None when all properties are pledged as active collateral."""
        _, zone = world_and_zone
        agent = Agent.objects.create(
            simulation=simulation,
            name="AllPledged",
            role="merchant",
            personality={},
            zone=zone,
            wealth=500.0,
            mood=0.5,
            health=1.0,
        )
        AgentInventory.objects.create(agent=agent, holdings={}, cash={currency.code: 200.0})
        prop = Property.objects.create(
            simulation=simulation,
            owner=agent,
            owner_type="agent",
            zone=zone,
            property_type="farmland",
            name="Farm",
            value=200.0,
        )
        Loan.objects.create(
            simulation=simulation,
            borrower=agent,
            lender_type="banking",
            principal=100.0,
            interest_rate=0.05,
            remaining_balance=100.0,
            collateral=prop,
            issued_at_tick=0,
            due_at_tick=20,
            status="active",
        )
        from epocha.apps.economy.credit import find_best_unpledged_property

        best = find_best_unpledged_property(agent)
        assert best is None


@pytest.mark.django_db
class TestDefaultCascade:
    """Verify cascade propagation through the debt graph."""

    def test_cascade_propagates_through_chain(
        self,
        simulation,
        world_and_zone,
        currency,
    ):
        """Chain of 3 agents: A borrows from B, B borrows from C.
        When A defaults, B's losses exceed threshold, causing B to
        default on its loan from C.
        """
        _, zone = world_and_zone

        agents = []
        for i, name in enumerate(["AgentA", "AgentB", "AgentC"]):
            agent = Agent.objects.create(
                simulation=simulation,
                name=name,
                role="merchant",
                social_class="middle",
                zone=zone,
                wealth=100.0,
                personality={"openness": 0.5},
                location=Point(50, 50),
                health=1.0,
            )
            AgentInventory.objects.create(
                agent=agent,
                holdings={},
                cash={currency.code: 50.0},
            )
            agents.append(agent)

        agent_a, agent_b, agent_c = agents

        # A owes B 80 (> 50% of B's wealth=100 => cascade)
        Loan.objects.create(
            simulation=simulation,
            lender=agent_b,
            borrower=agent_a,
            lender_type="agent",
            principal=80.0,
            interest_rate=0.05,
            remaining_balance=80.0,
            issued_at_tick=0,
            status="defaulted",
        )

        # B owes C 60
        Loan.objects.create(
            simulation=simulation,
            lender=agent_c,
            borrower=agent_b,
            lender_type="agent",
            principal=60.0,
            interest_rate=0.05,
            remaining_balance=60.0,
            issued_at_tick=0,
            status="active",
        )

        depth = process_default_cascade(simulation, tick=5)

        # B's loan from C should now be defaulted due to cascade
        b_loan = Loan.objects.get(
            simulation=simulation,
            borrower=agent_b,
            lender=agent_c,
        )
        assert b_loan.status == "defaulted"
        assert depth >= 1

    def test_cascade_stops_at_max_depth(
        self,
        simulation,
        world_and_zone,
        currency,
    ):
        """Cascade stops at max_depth even if further propagation is possible."""
        _, zone = world_and_zone

        # Create a chain of 5 agents
        agents = []
        for i in range(5):
            agent = Agent.objects.create(
                simulation=simulation,
                name=f"Chain{i}",
                role="merchant",
                social_class="middle",
                zone=zone,
                wealth=100.0,
                personality={"openness": 0.5},
                location=Point(50, 50),
                health=1.0,
            )
            AgentInventory.objects.create(
                agent=agent,
                holdings={},
                cash={currency.code: 10.0},
            )
            agents.append(agent)

        # Each agent borrows 80 from the next (exceeds cascade threshold)
        for i in range(4):
            status = "defaulted" if i == 0 else "active"
            Loan.objects.create(
                simulation=simulation,
                lender=agents[i + 1],
                borrower=agents[i],
                lender_type="agent",
                principal=80.0,
                interest_rate=0.05,
                remaining_balance=80.0,
                issued_at_tick=0,
                status=status,
            )

        depth = process_default_cascade(simulation, tick=5, max_depth=2)

        # Depth should not exceed 2
        assert depth <= 2

    def test_no_cascade_when_losses_below_threshold(
        self,
        simulation,
        world_and_zone,
        currency,
    ):
        """No cascade when lender losses are below the threshold."""
        _, zone = world_and_zone

        agent_a = Agent.objects.create(
            simulation=simulation,
            name="SmallDebtor",
            role="merchant",
            social_class="middle",
            zone=zone,
            wealth=100.0,
            personality={"openness": 0.5},
            location=Point(50, 50),
            health=1.0,
        )
        AgentInventory.objects.create(
            agent=agent_a,
            holdings={},
            cash={currency.code: 10.0},
        )
        agent_b = Agent.objects.create(
            simulation=simulation,
            name="StrongLender",
            role="merchant",
            social_class="elite",
            zone=zone,
            wealth=1000.0,
            personality={"openness": 0.5},
            location=Point(50, 50),
            health=1.0,
        )
        AgentInventory.objects.create(
            agent=agent_b,
            holdings={},
            cash={currency.code: 500.0},
        )

        # A owes B only 10 (1% of B's wealth -- well below 50% threshold)
        Loan.objects.create(
            simulation=simulation,
            lender=agent_b,
            borrower=agent_a,
            lender_type="agent",
            principal=10.0,
            interest_rate=0.05,
            remaining_balance=10.0,
            issued_at_tick=0,
            status="defaulted",
        )

        depth = process_default_cascade(simulation, tick=5)
        assert depth == 0


@pytest.mark.django_db
class TestRepaymentLedgerType:
    """Round 4 re-audit fix (run wf_9fb030e4-8a1): full principal
    repayment at maturity was ledgered as transaction_type
    "loan_interest", misclassifying principal as interest in every
    money-flow analytic. It must be ledgered as "loan_repayment"."""

    def test_full_repayment_ledgered_as_loan_repayment(
        self,
        simulation,
        borrower,
        currency,
        banking_state,
    ):
        issue_loan(
            simulation=simulation,
            lender=None,
            borrower=borrower,
            amount=100.0,
            interest_rate=0.05,
            collateral=None,
            tick=0,
            duration=5,
            lender_type="banking",
        )

        process_maturity(simulation, tick=5)

        repayment_entries = EconomicLedger.objects.filter(
            simulation=simulation,
            tick=5,
            transaction_type="loan_repayment",
        )
        assert repayment_entries.count() == 1
        assert repayment_entries.first().total_amount == pytest.approx(100.0)
        # R7-NEW-1: the final period accrues on repayment too -- the
        # interest portion is ledgered separately as loan_interest
        # (the principal above stays a pure loan_repayment).
        interest_entries = EconomicLedger.objects.filter(
            simulation=simulation,
            tick=5,
            transaction_type="loan_interest",
        )
        assert interest_entries.count() == 1
        assert interest_entries.first().total_amount == pytest.approx(5.0)


@pytest.mark.django_db
class TestDefaultTerminalState:
    """Round 5 re-audit findings R5-CRED-1 / R5-CRED-2 (run
    wf_62d071a6-289): defaulted loans never reached a terminal state, so
    process_defaults re-processed EVERY historical default on every tick
    (banking total_loans_outstanding decremented again each tick,
    duplicate borrower memories and repeated reputation hits, collateral
    re-seized even after a legitimate resale), and process_default_cascade
    re-seeded lender losses from all-time defaults forever. A processed
    default must reach the terminal status "default_settled", and the
    cascade must consume the CURRENT tick's loss records."""

    def test_default_processed_exactly_once(
        self,
        simulation,
        borrower,
        currency,
        collateral_property,
        banking_state,
    ):
        banking_state.total_loans_outstanding = 500.0
        banking_state.save(update_fields=["total_loans_outstanding"])

        loan = Loan.objects.create(
            simulation=simulation,
            lender=None,
            borrower=borrower,
            lender_type="banking",
            principal=200.0,
            interest_rate=0.10,
            remaining_balance=200.0,
            issued_at_tick=0,
            collateral=collateral_property,
            status="defaulted",
        )

        first = process_defaults(simulation, tick=5)
        assert len(first) == 1

        loan.refresh_from_db()
        assert loan.status == "default_settled"

        banking_state.refresh_from_db()
        assert banking_state.total_loans_outstanding == pytest.approx(300.0)

        # A second tick must be a no-op: no re-decrement, no duplicate
        # borrower memory, no new loss records.
        second = process_defaults(simulation, tick=6)
        assert second == []

        banking_state.refresh_from_db()
        assert banking_state.total_loans_outstanding == pytest.approx(300.0)

        default_memories = Memory.objects.filter(
            agent=borrower,
            content__contains="Defaulted",
        )
        assert default_memories.count() == 1

    def test_seized_collateral_not_clawed_back_after_resale(
        self,
        simulation,
        world_and_zone,
        borrower,
        lender,
        currency,
        collateral_property,
    ):
        _, zone = world_and_zone
        Loan.objects.create(
            simulation=simulation,
            lender=lender,
            borrower=borrower,
            lender_type="agent",
            principal=200.0,
            interest_rate=0.10,
            remaining_balance=200.0,
            issued_at_tick=0,
            collateral=collateral_property,
            status="defaulted",
        )

        process_defaults(simulation, tick=5)
        collateral_property.refresh_from_db()
        assert collateral_property.owner == lender

        # The lender legitimately resells the seized property.
        new_owner = Agent.objects.create(
            simulation=simulation,
            name="NewOwner",
            role="merchant",
            social_class="middle",
            zone=zone,
            wealth=800.0,
            personality={"openness": 0.5},
            location=Point(50, 50),
            health=1.0,
        )
        collateral_property.owner = new_owner
        collateral_property.save(update_fields=["owner"])

        # The next tick must NOT claw the property back to the lender.
        process_defaults(simulation, tick=6)
        collateral_property.refresh_from_db()
        assert collateral_property.owner == new_owner

    def test_cascade_consumes_current_tick_loss_records(
        self,
        simulation,
        world_and_zone,
        borrower,
        lender,
        currency,
    ):
        _, zone = world_and_zone
        # The lender is fragile: the defaulted loan's loss (200) exceeds
        # CASCADE_LOSS_THRESHOLD * wealth (0.5 * 100), so the cascade
        # must force-default the lender's own borrowing.
        lender.wealth = 100.0
        lender.save(update_fields=["wealth"])

        upstream = Agent.objects.create(
            simulation=simulation,
            name="Upstream",
            role="merchant",
            social_class="elite",
            zone=zone,
            wealth=5000.0,
            personality={"openness": 0.5},
            location=Point(50, 50),
            health=1.0,
        )
        Loan.objects.create(
            simulation=simulation,
            lender=lender,
            borrower=borrower,
            lender_type="agent",
            principal=200.0,
            interest_rate=0.10,
            remaining_balance=200.0,
            issued_at_tick=0,
            status="defaulted",
        )
        lender_own_loan = Loan.objects.create(
            simulation=simulation,
            lender=upstream,
            borrower=lender,
            lender_type="agent",
            principal=300.0,
            interest_rate=0.10,
            remaining_balance=300.0,
            issued_at_tick=0,
            status="active",
        )

        records = process_defaults(simulation, tick=5)
        depth = process_default_cascade(simulation, tick=5, loss_records=records)
        assert depth >= 1

        lender_own_loan.refresh_from_db()
        assert lender_own_loan.status == "defaulted"

        # Next tick: the cascade-defaulted loan is settled once, and the
        # cascade driven by the NEW tick's records must not re-trigger
        # from the all-time default history.
        records6 = process_defaults(simulation, tick=6)
        assert len(records6) == 1  # only the lender's own loan, once

        depth6 = process_default_cascade(simulation, tick=6, loss_records=records6)
        # Upstream is wealthy (5000): loss 300 < 0.5*5000, no propagation.
        assert depth6 == 0

        # Nothing left to re-process on a third tick.
        records7 = process_defaults(simulation, tick=7)
        assert records7 == []
        assert process_default_cascade(simulation, tick=7, loss_records=records7) == 0


@pytest.mark.django_db
class TestRolloverInterestLedger:
    """Round 5 re-audit finding R5-LED-1 (run wf_62d071a6-289): the
    rollover branch of process_maturity moved the interest payment in
    cash with no EconomicLedger row, while the identical flow in
    service_loans is ledgered -- money-flow analytics silently lost
    every rollover interest payment."""

    def test_rollover_interest_is_ledgered(
        self,
        simulation,
        borrower,
        lender,
        currency,
    ):
        Loan.objects.create(
            simulation=simulation,
            lender=lender,
            borrower=borrower,
            lender_type="agent",
            principal=200.0,
            interest_rate=0.10,
            remaining_balance=200.0,
            issued_at_tick=0,
            due_at_tick=5,
            times_rolled_over=0,
            status="active",
        )
        # Borrower cash (200 fixture) covers the interest (20) but the
        # engine-side maturity handler sees remaining_balance 200 --
        # set cash below the balance so the rollover branch fires.
        inv = borrower.inventory
        inv.cash = {currency.code: 50.0}
        inv.save(update_fields=["cash"])

        process_maturity(simulation, tick=5)

        rollover_interest = EconomicLedger.objects.filter(
            simulation=simulation,
            tick=5,
            transaction_type="loan_interest",
            from_agent=borrower,
        )
        assert rollover_interest.count() == 1
        assert rollover_interest.first().total_amount == pytest.approx(20.0)


@pytest.mark.django_db
class TestMaturityInterestSingleCharge:
    """Round 6 re-audit findings R6-NEW-1 / R6-ROLL-1 (run
    wf_6b5ea862-41e): on a maturity tick service_loans charged one
    period's interest and the rollover branch charged the identical
    amount again (double charge, double ledger row), and the rollover
    proceeded even when the borrower could not pay the rollover
    interest, contradicting the documented Minsky semantics (rollover
    only when the interest portion is affordable)."""

    def _maturing_loan(self, simulation, borrower, lender, cash, currency):
        inv = borrower.inventory
        inv.cash = {currency.code: cash}
        inv.save(update_fields=["cash"])
        return Loan.objects.create(
            simulation=simulation,
            lender=lender,
            borrower=borrower,
            lender_type="agent",
            principal=200.0,
            interest_rate=0.10,
            remaining_balance=200.0,
            issued_at_tick=0,
            due_at_tick=5,
            times_rolled_over=0,
            status="active",
        )

    def test_interest_charged_once_on_rollover_tick(
        self,
        simulation,
        borrower,
        lender,
        currency,
    ):
        # Cash 50: covers interest (20), not the balance (200) -> rollover.
        self._maturing_loan(simulation, borrower, lender, 50.0, currency)

        service_loans(simulation, tick=5)
        process_maturity(simulation, tick=5)

        interest_rows = EconomicLedger.objects.filter(
            simulation=simulation,
            tick=5,
            transaction_type="loan_interest",
            from_agent=borrower,
        )
        assert interest_rows.count() == 1
        assert sum(e.total_amount for e in interest_rows) == pytest.approx(20.0)

        inv = borrower.inventory
        inv.refresh_from_db()
        assert inv.cash[currency.code] == pytest.approx(30.0)

    def test_rollover_denied_when_interest_unaffordable(
        self,
        simulation,
        borrower,
        lender,
        currency,
    ):
        # Cash 5: cannot pay the 20 interest -> the loan must default,
        # not roll over with a silently skipped payment.
        loan = self._maturing_loan(simulation, borrower, lender, 5.0, currency)

        service_loans(simulation, tick=5)
        process_maturity(simulation, tick=5)

        loan.refresh_from_db()
        assert loan.status == "defaulted"
        assert not Loan.objects.filter(
            simulation=simulation,
            borrower=borrower,
            status="active",
        ).exists()


@pytest.mark.django_db
class TestCascadeLossMeasure:
    """Round 6 re-audit findings R6-NEW-2 / R6-CASC-1 (run
    wf_6b5ea862-41e): interior BFS levels propagated the GROSS
    remaining balance ignoring collateral (inconsistent with the
    net-of-collateral seed measure R5-CRED-2 established), and a
    cascade-defaulted loan's loss was threshold-evaluated twice --
    in-tick by the BFS and again at t+1 when its settlement records
    re-seeded the cascade."""

    def test_interior_cascade_loss_nets_collateral(
        self,
        simulation,
        world_and_zone,
        borrower,
        lender,
        currency,
    ):
        _, zone = world_and_zone
        # Fragile middleman: seed loss 200 > 0.5 * 100 wealth.
        lender.wealth = 100.0
        lender.save(update_fields=["wealth"])

        upstream = Agent.objects.create(
            simulation=simulation,
            name="UpstreamLender",
            role="merchant",
            social_class="elite",
            zone=zone,
            wealth=500.0,
            personality={"openness": 0.5},
            location=Point(50, 50),
            health=1.0,
        )
        # Seed default: borrower owes the fragile lender 200, no collateral.
        Loan.objects.create(
            simulation=simulation,
            lender=lender,
            borrower=borrower,
            lender_type="agent",
            principal=200.0,
            interest_rate=0.10,
            remaining_balance=200.0,
            issued_at_tick=0,
            status="defaulted",
        )
        # The fragile lender's own borrowing from upstream is FULLY
        # collateralized: net loss to upstream is 0, so upstream
        # (wealth 500, threshold 250) must NOT be pushed past the
        # threshold by a gross 300 measure.
        collateral = Property.objects.create(
            simulation=simulation,
            owner=lender,
            owner_type="agent",
            zone=zone,
            property_type="land",
            name="Middleman Land",
            value=300.0,
            production_bonus={},
        )
        Loan.objects.create(
            simulation=simulation,
            lender=upstream,
            borrower=lender,
            lender_type="agent",
            principal=300.0,
            interest_rate=0.10,
            remaining_balance=300.0,
            issued_at_tick=0,
            collateral=collateral,
            status="active",
        )
        # Upstream's own borrowing that a spurious depth-2 default
        # would force-default.
        upstream_own_loan = Loan.objects.create(
            simulation=simulation,
            lender=None,
            borrower=upstream,
            lender_type="banking",
            principal=100.0,
            interest_rate=0.05,
            remaining_balance=100.0,
            issued_at_tick=0,
            status="active",
        )

        records = process_defaults(simulation, tick=5)
        process_default_cascade(simulation, tick=5, loss_records=records)

        upstream_own_loan.refresh_from_db()
        assert upstream_own_loan.status == "active"

    def test_cascade_defaulted_loan_does_not_reseed_next_tick(
        self,
        simulation,
        world_and_zone,
        borrower,
        lender,
        currency,
    ):
        _, zone = world_and_zone
        lender.wealth = 100.0
        lender.save(update_fields=["wealth"])

        upstream = Agent.objects.create(
            simulation=simulation,
            name="UpstreamFragile",
            role="merchant",
            social_class="elite",
            zone=zone,
            wealth=100.0,
            personality={"openness": 0.5},
            location=Point(50, 50),
            health=1.0,
        )
        Loan.objects.create(
            simulation=simulation,
            lender=lender,
            borrower=borrower,
            lender_type="agent",
            principal=200.0,
            interest_rate=0.10,
            remaining_balance=200.0,
            issued_at_tick=0,
            status="defaulted",
        )
        # Uncollateralized middleman borrowing: in-tick BFS already
        # evaluates upstream at depth 2 with this loss.
        Loan.objects.create(
            simulation=simulation,
            lender=upstream,
            borrower=lender,
            lender_type="agent",
            principal=300.0,
            interest_rate=0.10,
            remaining_balance=300.0,
            issued_at_tick=0,
            status="active",
        )

        records5 = process_defaults(simulation, tick=5)
        process_default_cascade(simulation, tick=5, loss_records=records5)

        # A NEW loan issued to upstream between the ticks: the t+1
        # settlement of the cascade-defaulted middleman loan must NOT
        # re-evaluate upstream (its loss was already propagated
        # in-tick) and instantly default the fresh loan.
        fresh_loan = Loan.objects.create(
            simulation=simulation,
            lender=None,
            borrower=upstream,
            lender_type="banking",
            principal=100.0,
            interest_rate=0.05,
            remaining_balance=100.0,
            issued_at_tick=5,
            status="active",
        )

        records6 = process_defaults(simulation, tick=6)
        process_default_cascade(simulation, tick=6, loss_records=records6)

        fresh_loan.refresh_from_db()
        assert fresh_loan.status == "active"


@pytest.mark.django_db
class TestPendingDefaultCollateralLock:
    """Round 6 re-audit finding R6-COLL-1 (run wf_6b5ea862-41e):
    find_best_unpledged_property excluded only collateral of ACTIVE
    loans, so the collateral of a loan sitting in the pending
    "defaulted" state (cascade-marked at t, settled at t+1) could be
    double-pledged for a fresh loan in the gap."""

    def test_collateral_of_pending_default_not_offered(
        self,
        simulation,
        world_and_zone,
        borrower,
        lender,
        currency,
        collateral_property,
    ):
        from epocha.apps.economy.credit import find_best_unpledged_property

        Loan.objects.create(
            simulation=simulation,
            lender=lender,
            borrower=borrower,
            lender_type="agent",
            principal=200.0,
            interest_rate=0.10,
            remaining_balance=200.0,
            issued_at_tick=0,
            collateral=collateral_property,
            status="defaulted",
        )

        assert find_best_unpledged_property(borrower) is None


@pytest.mark.django_db
class TestMaturityFinalPeriodInterest:
    """Round 7 re-audit finding R7-NEW-1 (run wf_d98bd880-53e): the
    R6-NEW-1 fix removed the maturity-tick servicing for ALL maturing
    loans, so full repayment collected only the balance with no
    final-period interest while the rollover branch charged it -- the
    same period was interest-bearing in one branch of the same event
    and interest-free in the other. The final period accrues in BOTH
    branches: repayment collects balance*(1+rate)."""

    def test_full_repayment_collects_final_period_interest(
        self,
        simulation,
        borrower,
        lender,
        currency,
    ):
        inv = borrower.inventory
        inv.cash = {currency.code: 500.0}
        inv.save(update_fields=["cash"])
        Loan.objects.create(
            simulation=simulation,
            lender=lender,
            borrower=borrower,
            lender_type="agent",
            principal=200.0,
            interest_rate=0.10,
            remaining_balance=200.0,
            issued_at_tick=0,
            due_at_tick=5,
            status="active",
        )

        process_maturity(simulation, tick=5)

        interest_rows = EconomicLedger.objects.filter(
            simulation=simulation, tick=5, transaction_type="loan_interest", from_agent=borrower
        )
        repay_rows = EconomicLedger.objects.filter(
            simulation=simulation, tick=5, transaction_type="loan_repayment", from_agent=borrower
        )
        assert interest_rows.count() == 1
        assert interest_rows.first().total_amount == pytest.approx(20.0)
        assert repay_rows.count() == 1
        assert repay_rows.first().total_amount == pytest.approx(200.0)

        inv.refresh_from_db()
        assert inv.cash[currency.code] == pytest.approx(500.0 - 220.0)

    def test_open_ended_loans_still_serviced(
        self,
        simulation,
        borrower,
        lender,
        currency,
    ):
        # Pinning test closing the Round 7 false positive: the
        # .exclude(due_at_tick=tick) maturing-loan exclusion must KEEP
        # open-ended loans (due_at_tick NULL) in the servicing set --
        # Django's exclude() on a nullable field retains NULL rows.
        Loan.objects.create(
            simulation=simulation,
            lender=lender,
            borrower=borrower,
            lender_type="agent",
            principal=200.0,
            interest_rate=0.10,
            remaining_balance=200.0,
            issued_at_tick=0,
            due_at_tick=None,
            status="active",
        )

        service_loans(simulation, tick=5)

        assert EconomicLedger.objects.filter(
            simulation=simulation,
            tick=5,
            transaction_type="loan_interest",
            from_agent=borrower,
        ).exists()


@pytest.mark.django_db
class TestMaturityCatchUp:
    """Round 8 re-audit finding R8-NEW-5 (run wf_75faf0db-ad2): both
    process_maturity and service_loans matched the maturity tick with
    exact equality (due_at_tick == tick). The credit block runs only
    for the first zone with a living agent, so a tick in which every
    zone is agent-empty skips maturity entirely; the loan that fell due
    that tick was then stranded -- exact-equality maturity never matched
    it again. The robust fix is a catch-up: process_maturity matures
    every loan due at OR BEFORE the current tick (due_at_tick__lte), and
    service_loans excludes the same set so the final period is charged
    exactly once by the maturity step, never double-charged. The normal
    path is unchanged (a loan due at tick t only satisfies
    due_at_tick <= t at tick t)."""

    def test_overdue_loan_matures_on_catch_up(
        self,
        simulation,
        borrower,
        currency,
        banking_state,
    ):
        inv = borrower.inventory
        inv.cash = {currency.code: 500.0}
        inv.save(update_fields=["cash"])
        loan = Loan.objects.create(
            simulation=simulation,
            borrower=borrower,
            lender_type="banking",
            principal=200.0,
            interest_rate=0.10,
            remaining_balance=200.0,
            issued_at_tick=0,
            due_at_tick=5,
            status="active",
        )

        # Maturity was skipped at tick 5 (a fully agent-empty credit
        # tick); the next executed credit tick must catch it up.
        process_maturity(simulation, tick=6)

        loan.refresh_from_db()
        assert loan.status == "repaid"
        assert loan.remaining_balance == 0.0

    def test_service_loans_skips_overdue_from_interest(
        self,
        simulation,
        borrower,
        currency,
        banking_state,
    ):
        inv = borrower.inventory
        inv.cash = {currency.code: 500.0}
        inv.save(update_fields=["cash"])
        Loan.objects.create(
            simulation=simulation,
            borrower=borrower,
            lender_type="banking",
            principal=200.0,
            interest_rate=0.10,
            remaining_balance=200.0,
            issued_at_tick=0,
            due_at_tick=5,
            status="active",
        )

        service_loans(simulation, tick=6)

        # An overdue loan belongs to the maturity catch-up, not
        # servicing: charging it interest here would double the final
        # period once process_maturity also charges it.
        inv.refresh_from_db()
        assert inv.cash[currency.code] == pytest.approx(500.0)
        assert not EconomicLedger.objects.filter(
            simulation=simulation,
            tick=6,
            transaction_type="loan_interest",
            from_agent=borrower,
        ).exists()


@pytest.mark.django_db
class TestBorrowAmountValidation:
    """Round 7 re-audit finding R7-VAL-1 (run wf_d98bd880-53e,
    INCORRECT): the borrow amount reached evaluate_credit_request and
    issue_loan with no positivity/finiteness guard -- a negative
    amount decremented total_loans_outstanding (phantom capacity) and
    a NaN permanently poisoned cash, deposits, money supply, the
    solvency check and the Fisher diagnostic. LLM output is a system
    boundary and must be validated like any external input."""

    @pytest.mark.parametrize("bad_amount", [-100.0, 0.0, float("nan"), float("inf")])
    def test_invalid_amounts_rejected(
        self,
        simulation,
        borrower,
        currency,
        collateral_property,
        banking_state,
        bad_amount,
    ):
        approved, _ = evaluate_credit_request(
            borrower=borrower,
            amount=bad_amount,
            collateral_property=collateral_property,
            simulation=simulation,
        )
        assert approved is False

    @pytest.mark.parametrize("bad_amount", [-100.0, 0.0, float("nan"), float("inf")])
    def test_issue_loan_rejects_invalid_amount(
        self,
        simulation,
        borrower,
        currency,
        banking_state,
        bad_amount,
    ):
        # R8-NEW-4 (Round 8 re-audit, run wf_75faf0db-ad2): pins the
        # SECOND defense-in-depth layer. evaluate_credit_request rejecting
        # invalid amounts was already tested; issue_loan's own guard --
        # which protects non-engine callers that skip evaluate -- was not.
        # A future refactor dropping it must break a test.
        loan = issue_loan(
            simulation=simulation,
            lender=None,
            borrower=borrower,
            amount=bad_amount,
            interest_rate=0.05,
            collateral=None,
            tick=0,
            duration=5,
            lender_type="banking",
        )
        assert loan is None


@pytest.mark.django_db
class TestIssueLoanCollateralExclusivity:
    """Round 7 re-audit finding R7-COLL-1 (run wf_d98bd880-53e): the
    loan-creation API accepted any Property as collateral -- the
    double-pledge exclusion lived only in the engine's borrow path
    helper. issue_loan itself must refuse already-pledged collateral."""

    def test_issue_loan_refuses_pledged_collateral(
        self,
        simulation,
        borrower,
        lender,
        currency,
        collateral_property,
        banking_state,
    ):
        Loan.objects.create(
            simulation=simulation,
            lender=lender,
            borrower=borrower,
            lender_type="agent",
            principal=100.0,
            interest_rate=0.10,
            remaining_balance=100.0,
            issued_at_tick=0,
            collateral=collateral_property,
            status="active",
        )

        loan = issue_loan(
            simulation=simulation,
            lender=None,
            borrower=borrower,
            amount=50.0,
            interest_rate=0.05,
            collateral=collateral_property,
            tick=1,
            duration=5,
            lender_type="banking",
        )
        assert loan is None

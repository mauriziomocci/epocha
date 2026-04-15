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

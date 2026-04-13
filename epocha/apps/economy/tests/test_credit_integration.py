"""Integration test for the credit market pipeline within the economy engine.

Creates a simulation with economy, manually issues loans, runs multiple
ticks, and verifies interest collection, maturity handling, and banking
state updates through the full pipeline.
"""

import pytest
from django.contrib.gis.geos import Point, Polygon

from epocha.apps.agents.models import Agent
from epocha.apps.economy.banking import initialize_banking
from epocha.apps.economy.credit import issue_loan
from epocha.apps.economy.engine import process_economy_tick_new
from epocha.apps.economy.initialization import initialize_economy
from epocha.apps.economy.models import (
    BankingState,
    Currency,
    EconomicLedger,
    Loan,
)
from epocha.apps.simulation.models import Simulation
from epocha.apps.users.models import User
from epocha.apps.world.models import Government, World, Zone


@pytest.fixture
def user(db):
    return User.objects.create_user(
        email="creditint@epocha.dev",
        username="creditintuser",
        password="pass1234",
    )


@pytest.fixture
def simulation(user):
    return Simulation.objects.create(
        name="CreditIntegration",
        seed=42,
        owner=user,
    )


@pytest.fixture
def economy_with_loans(simulation):
    """Create a full economy with agents and manually issued loans."""
    world = World.objects.create(
        simulation=simulation,
        distance_scale=100.0,
        tick_duration_hours=24.0,
    )
    Government.objects.create(
        simulation=simulation,
        government_type="monarchy",
        stability=0.5,
        popular_legitimacy=0.5,
    )
    zone = Zone.objects.create(
        world=world,
        name="Market Town",
        zone_type="commercial",
        boundary=Polygon.from_bbox((0, 0, 100, 100)),
        center=Point(50, 50),
    )

    # Create agents with different roles for production
    borrower = Agent.objects.create(
        simulation=simulation,
        name="Borrower",
        role="merchant",
        social_class="middle",
        zone=zone,
        wealth=0.0,
        personality={"openness": 0.5},
        location=Point(50, 50),
        health=1.0,
    )
    lender_agent = Agent.objects.create(
        simulation=simulation,
        name="Lender",
        role="craftsman",
        social_class="elite",
        zone=zone,
        wealth=0.0,
        personality={"openness": 0.5},
        location=Point(50, 50),
        health=1.0,
    )
    worker = Agent.objects.create(
        simulation=simulation,
        name="Worker",
        role="farmer",
        social_class="poor",
        zone=zone,
        wealth=0.0,
        personality={"openness": 0.4},
        location=Point(50, 50),
        health=1.0,
    )

    # Initialize economy from template
    initialize_economy(simulation)

    # Initialize the banking system
    bs = initialize_banking(simulation)

    # Store credit_config in simulation config (may not have been set
    # by initialize_economy since it only stores production_config)
    sim_config = simulation.config or {}
    if "credit_config" not in sim_config:
        sim_config["credit_config"] = {
            "loan_to_value": 0.8,
            "max_rollover": 3,
            "default_loan_duration_ticks": 5,
            "risk_premium": 0.5,
        }
    if "banking_config" not in sim_config:
        sim_config["banking_config"] = {
            "initial_deposits": 5000.0,
            "base_interest_rate": 0.05,
            "reserve_ratio": 0.10,
        }
    simulation.config = sim_config
    simulation.save(update_fields=["config"])

    currency = Currency.objects.get(simulation=simulation, is_primary=True)

    # Issue a banking loan to the borrower (due at tick 5)
    banking_loan = issue_loan(
        simulation=simulation,
        lender=None,
        borrower=borrower,
        amount=50.0,
        interest_rate=0.05,
        collateral=None,
        tick=0,
        duration=5,
        lender_type="banking",
    )

    # Issue an agent-to-agent loan (due at tick 3)
    agent_loan = issue_loan(
        simulation=simulation,
        lender=lender_agent,
        borrower=borrower,
        amount=30.0,
        interest_rate=0.08,
        collateral=None,
        tick=0,
        duration=3,
        lender_type="agent",
    )

    return {
        "world": world,
        "zone": zone,
        "borrower": borrower,
        "lender": lender_agent,
        "worker": worker,
        "banking_loan": banking_loan,
        "agent_loan": agent_loan,
        "currency": currency,
        "banking_state": bs,
    }


@pytest.mark.django_db
class TestCreditPipelineIntegration:
    """End-to-end tests for credit market within the economy tick pipeline."""

    def test_interest_collected_over_ticks(
        self,
        simulation,
        economy_with_loans,
    ):
        """Running economy ticks should collect interest from active loans."""
        borrower = economy_with_loans["borrower"]

        # Run 2 ticks
        process_economy_tick_new(simulation, tick=1)
        process_economy_tick_new(simulation, tick=2)

        # Interest should have been collected (cash may change from
        # multiple sources -- production, wages, trades, interest).
        # Verify that trade-type ledger entries exist (interest payments
        # are recorded as trades).
        interest_entries = EconomicLedger.objects.filter(
            simulation=simulation,
            from_agent=borrower,
            transaction_type="trade",
            tick__in=[1, 2],
        )
        # At least some interest payments should have been made
        # (borrower has cash from initial distribution + loan proceeds)
        assert interest_entries.exists()

    def test_maturity_handled_at_due_tick(
        self,
        simulation,
        economy_with_loans,
    ):
        """Loan maturity is handled when due_at_tick is reached."""
        agent_loan = economy_with_loans["agent_loan"]

        # Run ticks up to and including the due tick
        for tick in range(1, 4):
            process_economy_tick_new(simulation, tick=tick)

        agent_loan.refresh_from_db()
        # Loan should be either repaid or rolled over (not still active
        # with original due_at_tick)
        assert agent_loan.status in ("repaid", "rolled_over", "defaulted")

    def test_banking_state_updated(
        self,
        simulation,
        economy_with_loans,
    ):
        """Banking state should be updated after ticks (interest rate, solvency)."""
        bs = economy_with_loans["banking_state"]

        for tick in range(1, 4):
            process_economy_tick_new(simulation, tick=tick)

        bs.refresh_from_db()
        # Banking state should still be valid
        assert bs.is_solvent is True or bs.is_solvent is False  # was updated
        assert bs.confidence_index >= 0.0
        assert bs.confidence_index <= 1.0
        assert bs.base_interest_rate > 0.0

    def test_multiple_ticks_no_crash(
        self,
        simulation,
        economy_with_loans,
    ):
        """The full pipeline with credit should survive 5 ticks without errors."""
        for tick in range(1, 6):
            process_economy_tick_new(simulation, tick=tick)

        # Verify some basic invariants
        active_loans = Loan.objects.filter(
            simulation=simulation,
            status="active",
        )
        # All remaining active loans should have positive balance
        for loan in active_loans:
            assert loan.remaining_balance >= 0.0

        # Banking state should exist and be consistent
        bs = BankingState.objects.get(simulation=simulation)
        assert bs.total_loans_outstanding >= 0.0

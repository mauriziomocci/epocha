"""Tests for the banking system: initialization, interest rate adjustment,
solvency checking, and money multiplier computation.
"""

import pytest
from django.contrib.gis.geos import Point, Polygon

from epocha.apps.agents.models import Agent
from epocha.apps.economy.banking import (
    adjust_interest_rate,
    check_solvency,
    compute_actual_multiplier,
    initialize_banking,
)
from epocha.apps.economy.models import (
    AgentInventory,
    BankingState,
    Currency,
    Loan,
)
from epocha.apps.simulation.models import Simulation
from epocha.apps.users.models import User
from epocha.apps.world.models import World, Zone


@pytest.fixture
def user(db):
    return User.objects.create_user(
        email="banking@epocha.dev",
        username="bankinguser",
        password="pass1234",
    )


@pytest.fixture
def simulation(user):
    return Simulation.objects.create(
        name="BankingTest",
        seed=42,
        owner=user,
        config={
            "credit_config": {
                "loan_to_value": 0.8,
                "max_rollover": 3,
                "default_loan_duration_ticks": 10,
                "credit_adj_rate": 0.02,
            },
            "banking_config": {
                "initial_deposits": 10000.0,
                "base_interest_rate": 0.05,
                "reserve_ratio": 0.10,
            },
        },
    )


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


@pytest.mark.django_db
class TestInitializeBanking:
    """Verify banking system initialization from template config."""

    def test_creates_banking_state(self, simulation):
        """BankingState is created with values from simulation config."""
        bs = initialize_banking(simulation)

        assert bs.total_deposits == 10000.0
        assert bs.base_interest_rate == 0.05
        assert bs.reserve_ratio == 0.10
        assert bs.is_solvent is True
        assert bs.confidence_index == 1.0
        assert bs.total_loans_outstanding == 0.0

    def test_idempotent(self, simulation):
        """Calling initialize_banking twice returns the same instance."""
        bs1 = initialize_banking(simulation)
        bs2 = initialize_banking(simulation)
        assert bs1.id == bs2.id

    def test_defaults_when_no_config(self, user):
        """Falls back to conservative defaults when config is missing."""
        sim = Simulation.objects.create(
            name="NoConfig",
            seed=99,
            owner=user,
        )
        bs = initialize_banking(sim)

        assert bs.total_deposits > 0
        assert bs.base_interest_rate > 0
        assert bs.reserve_ratio > 0


@pytest.mark.django_db
class TestInterestRateAdjustment:
    """Verify Wicksell (1898) interest rate adjustment."""

    def test_rate_rises_when_demand_exceeds_supply(
        self,
        simulation,
        world_and_zone,
        currency,
    ):
        """When heavily indebted agents demand more credit, rate increases."""
        _, zone = world_and_zone
        bs = initialize_banking(simulation)
        initial_rate = bs.base_interest_rate

        # Create highly leveraged agents (debt_ratio > 0.3)
        for i in range(5):
            agent = Agent.objects.create(
                simulation=simulation,
                name=f"Debtor{i}",
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
            # debt_ratio = 80/100 = 0.8 > 0.3
            Loan.objects.create(
                simulation=simulation,
                borrower=agent,
                lender_type="banking",
                principal=80.0,
                interest_rate=0.05,
                remaining_balance=80.0,
                issued_at_tick=0,
                status="active",
            )

        # Set loans outstanding high to reduce supply to near zero
        # supply = 10000*(1-0.10) - 8900 = 100; demand = 5*80 = 400
        bs.total_loans_outstanding = 8900.0
        bs.save(update_fields=["total_loans_outstanding"])

        adjust_interest_rate(simulation, tick=1)

        bs.refresh_from_db()
        assert bs.base_interest_rate > initial_rate

    def test_rate_falls_when_supply_exceeds_demand(
        self,
        simulation,
        world_and_zone,
        currency,
    ):
        """When few agents need credit and supply is ample, rate decreases."""
        _, zone = world_and_zone
        bs = initialize_banking(simulation)
        initial_rate = bs.base_interest_rate

        # Create agents with low debt (debt_ratio < 0.3 => no demand)
        for i in range(3):
            agent = Agent.objects.create(
                simulation=simulation,
                name=f"Saver{i}",
                role="merchant",
                social_class="middle",
                zone=zone,
                wealth=1000.0,
                personality={"openness": 0.5},
                location=Point(50, 50),
                health=1.0,
            )
            AgentInventory.objects.create(
                agent=agent,
                holdings={},
                cash={currency.code: 500.0},
            )

        # No loans outstanding => supply = 10000 * 0.9 = 9000
        adjust_interest_rate(simulation, tick=1)

        bs.refresh_from_db()
        assert bs.base_interest_rate < initial_rate

    def test_rate_clamped_within_bounds(self, simulation, world_and_zone, currency):
        """Rate never goes below 0.5% or above 50%."""
        _, zone = world_and_zone
        bs = initialize_banking(simulation)

        # Set rate very low, create conditions for further decrease
        bs.base_interest_rate = 0.005
        bs.save(update_fields=["base_interest_rate"])

        agent = Agent.objects.create(
            simulation=simulation,
            name="Saver",
            role="merchant",
            social_class="middle",
            zone=zone,
            wealth=1000.0,
            personality={"openness": 0.5},
            location=Point(50, 50),
            health=1.0,
        )
        AgentInventory.objects.create(
            agent=agent,
            holdings={},
            cash={currency.code: 500.0},
        )

        adjust_interest_rate(simulation, tick=1)

        bs.refresh_from_db()
        assert bs.base_interest_rate >= 0.005
        assert bs.base_interest_rate <= 0.5


@pytest.mark.django_db
class TestSolvencyCheck:
    """Verify Diamond & Dybvig (1983) solvency checking."""

    def test_solvent_when_reserves_sufficient(self, simulation):
        """Bank is solvent when reserves exceed required ratio."""
        bs = BankingState.objects.create(
            simulation=simulation,
            total_deposits=10000.0,
            total_loans_outstanding=5000.0,  # reserves = 5000
            reserve_ratio=0.10,  # required = 1000
            base_interest_rate=0.05,
            is_solvent=True,
            confidence_index=0.8,
        )

        check_solvency(simulation)

        bs.refresh_from_db()
        assert bs.is_solvent is True
        assert bs.confidence_index == pytest.approx(0.85)  # +0.05

    def test_insolvent_when_overleveraged(self, simulation):
        """Bank is insolvent when loans outstanding are too high."""
        bs = BankingState.objects.create(
            simulation=simulation,
            total_deposits=10000.0,
            total_loans_outstanding=9500.0,  # reserves = 500
            reserve_ratio=0.10,  # required = 1000
            base_interest_rate=0.05,
            is_solvent=True,
            confidence_index=1.0,
        )

        check_solvency(simulation)

        bs.refresh_from_db()
        assert bs.is_solvent is False
        assert bs.confidence_index == pytest.approx(0.9)  # -0.1

    def test_confidence_erodes_over_ticks(self, simulation):
        """Confidence drops 0.1 per tick when insolvent."""
        bs = BankingState.objects.create(
            simulation=simulation,
            total_deposits=10000.0,
            total_loans_outstanding=9500.0,
            reserve_ratio=0.10,
            base_interest_rate=0.05,
            is_solvent=False,
            confidence_index=0.5,
        )

        check_solvency(simulation)

        bs.refresh_from_db()
        assert bs.confidence_index == pytest.approx(0.4)

    def test_no_banking_state_is_noop(self, simulation):
        """check_solvency does nothing when no BankingState exists."""
        check_solvency(simulation)  # should not raise


@pytest.mark.django_db
class TestActualMultiplier:
    """Verify money multiplier computation."""

    def test_multiplier_computation(self):
        """Multiplier = loans_outstanding / deposits."""
        bs = BankingState(
            total_deposits=10000.0,
            total_loans_outstanding=7000.0,
        )
        result = compute_actual_multiplier(bs)
        assert result == pytest.approx(0.7)

    def test_zero_deposits(self):
        """Zero deposits returns loans/1.0 to avoid division by zero."""
        bs = BankingState(
            total_deposits=0.0,
            total_loans_outstanding=100.0,
        )
        result = compute_actual_multiplier(bs)
        assert result == pytest.approx(100.0)

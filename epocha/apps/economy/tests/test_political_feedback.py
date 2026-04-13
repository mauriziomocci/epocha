"""Tests for economic feedback on political indicators."""
import pytest
from django.contrib.gis.geos import Point, Polygon

from epocha.apps.agents.models import Agent
from epocha.apps.economy.models import Currency, PriceHistory, ZoneEconomy
from epocha.apps.economy.political_feedback import apply_economic_feedback
from epocha.apps.simulation.models import Simulation
from epocha.apps.users.models import User
from epocha.apps.world.models import Government, World, Zone


@pytest.fixture
def user(db):
    return User.objects.create_user(
        email="pf@epocha.dev",
        username="pfuser",
        password="pass1234",
    )


@pytest.fixture
def simulation(user):
    return Simulation.objects.create(
        name="PFTest", seed=42, owner=user,
    )


@pytest.fixture
def political_setup(simulation):
    """Create economy with government for feedback tests."""
    world = World.objects.create(
        simulation=simulation,
        distance_scale=133.0,
        tick_duration_hours=24.0,
    )
    zone = Zone.objects.create(
        world=world, name="Capital", zone_type="urban",
        boundary=Polygon.from_bbox((0, 0, 100, 100)),
        center=Point(50, 50),
    )
    gov = Government.objects.create(
        simulation=simulation,
        government_type="democracy",
        stability=0.5,
        popular_legitimacy=0.5,
    )
    Currency.objects.create(
        simulation=simulation, code="LVR", name="Livre",
        symbol="L", is_primary=True, total_supply=10000.0,
    )
    ze = ZoneEconomy.objects.create(
        zone=zone,
        market_prices={"subsistence": 3.0},
    )

    # Create agents with diverse wealth for Gini computation
    for i, (name, wealth) in enumerate([
        ("Rich", 500.0), ("Middle", 100.0), ("Poor", 10.0),
    ]):
        Agent.objects.create(
            simulation=simulation, name=name, role="citizen",
            personality={"openness": 0.5}, location=Point(50, 50),
            zone=zone, wealth=wealth,
        )

    return {
        "world": world,
        "zone": zone,
        "government": gov,
        "zone_economy": ze,
    }


@pytest.mark.django_db
class TestInflationFeedback:
    def test_high_inflation_reduces_stability(self, simulation, political_setup):
        ze = political_setup["zone_economy"]
        # Tick 0: price 3.0, tick 1: price 4.0 => 33% inflation
        PriceHistory.objects.create(
            zone_economy=ze, good_code="subsistence", tick=0,
            price=3.0, supply=10, demand=10,
        )
        PriceHistory.objects.create(
            zone_economy=ze, good_code="subsistence", tick=1,
            price=4.0, supply=10, demand=12,
        )

        apply_economic_feedback(simulation, tick=1)

        gov = Government.objects.get(simulation=simulation)
        assert gov.stability < 0.5

    def test_low_inflation_no_penalty(self, simulation, political_setup):
        ze = political_setup["zone_economy"]
        # 3% inflation, below threshold
        PriceHistory.objects.create(
            zone_economy=ze, good_code="subsistence", tick=0,
            price=3.0, supply=10, demand=10,
        )
        PriceHistory.objects.create(
            zone_economy=ze, good_code="subsistence", tick=1,
            price=3.09, supply=10, demand=10,
        )

        apply_economic_feedback(simulation, tick=1)

        gov = Government.objects.get(simulation=simulation)
        assert gov.stability == 0.5


@pytest.mark.django_db
class TestGiniFeedback:
    def test_high_gini_reduces_legitimacy(self, simulation, political_setup):
        # Increase inequality: make one agent very rich
        Agent.objects.filter(simulation=simulation, name="Rich").update(wealth=10000.0)
        Agent.objects.filter(simulation=simulation, name="Poor").update(wealth=1.0)

        apply_economic_feedback(simulation, tick=0)

        gov = Government.objects.get(simulation=simulation)
        assert gov.popular_legitimacy < 0.5

    def test_moderate_gini_no_penalty(self, simulation, political_setup):
        # Set roughly equal wealth
        Agent.objects.filter(simulation=simulation).update(wealth=100.0)

        apply_economic_feedback(simulation, tick=0)

        gov = Government.objects.get(simulation=simulation)
        assert gov.popular_legitimacy == 0.5


@pytest.mark.django_db
class TestTreasuryFeedback:
    def test_negative_treasury_reduces_stability(self, simulation, political_setup):
        gov = political_setup["government"]
        gov.government_treasury = {"LVR": -100.0}
        gov.save()

        apply_economic_feedback(simulation, tick=0)

        gov.refresh_from_db()
        assert gov.stability < 0.5

    def test_positive_treasury_no_penalty(self, simulation, political_setup):
        gov = political_setup["government"]
        gov.government_treasury = {"LVR": 500.0}
        gov.save()

        apply_economic_feedback(simulation, tick=0)

        gov.refresh_from_db()
        assert gov.stability == 0.5


@pytest.mark.django_db
class TestNoGovernment:
    def test_no_crash_without_government(self, simulation, political_setup):
        Government.objects.filter(simulation=simulation).delete()
        # Should be a no-op, not raise
        apply_economic_feedback(simulation, tick=1)

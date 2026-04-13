"""Tests for economic context builder."""
import pytest
from django.contrib.gis.geos import Point, Polygon

from epocha.apps.agents.models import Agent
from epocha.apps.economy.context import build_economic_context
from epocha.apps.economy.models import (
    AgentInventory,
    Currency,
    GoodCategory,
    PriceHistory,
    Property,
    ZoneEconomy,
)
from epocha.apps.simulation.models import Simulation
from epocha.apps.users.models import User
from epocha.apps.world.models import World, Zone


@pytest.fixture
def user(db):
    return User.objects.create_user(
        email="ctx@epocha.dev",
        username="ctxuser",
        password="pass1234",
    )


@pytest.fixture
def simulation(user):
    return Simulation.objects.create(
        name="ContextTest", seed=42, owner=user,
    )


@pytest.fixture
def economy_setup(simulation):
    """Create minimal economy for context tests."""
    world = World.objects.create(
        simulation=simulation,
        distance_scale=133.0,
        tick_duration_hours=24.0,
    )
    zone = Zone.objects.create(
        world=world, name="Paris", zone_type="urban",
        boundary=Polygon.from_bbox((0, 0, 100, 100)),
        center=Point(50, 50),
    )
    currency = Currency.objects.create(
        simulation=simulation, code="LVR", name="Livre",
        symbol="L", is_primary=True, total_supply=10000.0,
    )
    sub = GoodCategory.objects.create(
        simulation=simulation, code="subsistence",
        name="Subsistence", is_essential=True,
        base_price=3.0, price_elasticity=0.3,
    )
    lux = GoodCategory.objects.create(
        simulation=simulation, code="luxury",
        name="Luxury", is_essential=False,
        base_price=50.0, price_elasticity=2.0,
    )
    ze = ZoneEconomy.objects.create(
        zone=zone,
        market_prices={"subsistence": 3.2, "luxury": 48.0},
    )
    # Previous tick prices for % change
    PriceHistory.objects.create(
        zone_economy=ze, good_code="subsistence", tick=0,
        price=3.0, supply=10, demand=10,
    )
    PriceHistory.objects.create(
        zone_economy=ze, good_code="luxury", tick=0,
        price=50.0, supply=5, demand=5,
    )

    agent = Agent.objects.create(
        simulation=simulation, name="Trader", role="merchant",
        personality={"openness": 0.5}, location=Point(50, 50),
        zone=zone, wealth=180.0,
    )
    AgentInventory.objects.create(
        agent=agent,
        holdings={"subsistence": 5.0, "luxury": 1.0},
        cash={"LVR": 50.0},
    )
    Property.objects.create(
        simulation=simulation, owner=agent,
        owner_type="agent", zone=zone,
        property_type="land", name="Trader's Land",
        value=100.0,
    )

    return {
        "agent": agent,
        "zone_economy": ze,
        "currency": currency,
    }


@pytest.mark.django_db
class TestBuildEconomicContext:
    def test_returns_string(self, economy_setup):
        ctx = build_economic_context(economy_setup["agent"], tick=1)
        assert isinstance(ctx, str)

    def test_contains_cash(self, economy_setup):
        ctx = build_economic_context(economy_setup["agent"], tick=1)
        assert "Cash: 50 L" in ctx

    def test_contains_inventory(self, economy_setup):
        ctx = build_economic_context(economy_setup["agent"], tick=1)
        assert "subsistence" in ctx
        assert "luxury" in ctx

    def test_contains_properties(self, economy_setup):
        ctx = build_economic_context(economy_setup["agent"], tick=1)
        assert "land" in ctx

    def test_contains_total_wealth(self, economy_setup):
        ctx = build_economic_context(economy_setup["agent"], tick=1)
        assert "Total wealth: 180 L" in ctx

    def test_contains_market_prices(self, economy_setup):
        ctx = build_economic_context(economy_setup["agent"], tick=1)
        assert "Market in Paris" in ctx
        assert "Subsistence" in ctx
        assert "Luxury" in ctx

    def test_contains_price_change(self, economy_setup):
        ctx = build_economic_context(economy_setup["agent"], tick=1)
        # subsistence went from 3.0 to 3.2 = +6.7%
        assert "up" in ctx

    def test_returns_none_without_currency(self, simulation, economy_setup):
        Currency.objects.filter(simulation=simulation).delete()
        ctx = build_economic_context(economy_setup["agent"], tick=1)
        assert ctx is None

    def test_returns_none_without_inventory(self, economy_setup):
        AgentInventory.objects.filter(agent=economy_setup["agent"]).delete()
        # Reload agent from DB to clear cached reverse relation
        agent = Agent.objects.get(pk=economy_setup["agent"].pk)
        ctx = build_economic_context(agent, tick=1)
        assert ctx is None


@pytest.mark.django_db
class TestHoardActionInPrompt:
    def test_hoard_in_system_prompt(self):
        from epocha.apps.agents.decision import _DECISION_SYSTEM_PROMPT
        assert "hoard" in _DECISION_SYSTEM_PROMPT

    def test_hoard_in_action_verbs(self):
        from epocha.apps.dashboard.formatters import _ACTION_VERBS
        assert "hoard" in _ACTION_VERBS

    def test_hoard_in_emotional_weight(self):
        from epocha.apps.simulation.engine import _ACTION_EMOTIONAL_WEIGHT
        assert "hoard" in _ACTION_EMOTIONAL_WEIGHT

    def test_hoard_in_mood_delta(self):
        from epocha.apps.simulation.engine import _ACTION_MOOD_DELTA
        assert "hoard" in _ACTION_MOOD_DELTA

"""Tests for the adaptive expectations engine (Nerlove 1958).

Tests cover:
- Lambda computation from personality traits (neutral, high N, high C, clamping)
- Trend detection (rising, falling, stable)
- Nerlove formula behavior via update_agent_expectations
"""

import pytest
from django.contrib.gis.geos import Point, Polygon

from epocha.apps.agents.models import Agent
from epocha.apps.economy.expectations import (
    compute_lambda_from_personality,
    detect_trend,
    update_agent_expectations,
)
from epocha.apps.economy.models import AgentExpectation, GoodCategory, ZoneEconomy
from epocha.apps.simulation.models import Simulation
from epocha.apps.users.models import User
from epocha.apps.world.models import World, Zone

# -- Pure function tests (no DB) --


class TestComputeLambda:
    """Tests for compute_lambda_from_personality."""

    def test_neutral_personality_returns_base(self):
        """All traits at 0.5 (population mean) should return lambda_base."""
        personality = {
            "neuroticism": 0.5,
            "openness": 0.5,
            "conscientiousness": 0.5,
        }
        result = compute_lambda_from_personality(
            personality,
            lambda_base=0.3,
            n_mod=0.15,
            o_mod=0.10,
            c_mod=0.10,
        )
        assert result == pytest.approx(0.3)

    def test_high_neuroticism_increases_lambda(self):
        """High neuroticism (N=1.0) should increase lambda above base."""
        personality = {
            "neuroticism": 1.0,
            "openness": 0.5,
            "conscientiousness": 0.5,
        }
        result = compute_lambda_from_personality(
            personality,
            lambda_base=0.3,
            n_mod=0.15,
            o_mod=0.10,
            c_mod=0.10,
        )
        # 0.3 + (1.0 - 0.5) * 0.15 = 0.3 + 0.075 = 0.375
        assert result == pytest.approx(0.375)

    def test_high_openness_increases_lambda(self):
        """High openness (O=1.0) should increase lambda."""
        personality = {
            "neuroticism": 0.5,
            "openness": 1.0,
            "conscientiousness": 0.5,
        }
        result = compute_lambda_from_personality(
            personality,
            lambda_base=0.3,
            n_mod=0.15,
            o_mod=0.10,
            c_mod=0.10,
        )
        # 0.3 + (1.0 - 0.5) * 0.10 = 0.3 + 0.05 = 0.35
        assert result == pytest.approx(0.35)

    def test_high_conscientiousness_decreases_lambda(self):
        """High conscientiousness (C=1.0) should decrease lambda."""
        personality = {
            "neuroticism": 0.5,
            "openness": 0.5,
            "conscientiousness": 1.0,
        }
        result = compute_lambda_from_personality(
            personality,
            lambda_base=0.3,
            n_mod=0.15,
            o_mod=0.10,
            c_mod=0.10,
        )
        # 0.3 - (1.0 - 0.5) * 0.10 = 0.3 - 0.05 = 0.25
        assert result == pytest.approx(0.25)

    def test_clamping_high(self):
        """Extreme traits should clamp lambda to 0.95."""
        personality = {
            "neuroticism": 1.0,
            "openness": 1.0,
            "conscientiousness": 0.0,
        }
        result = compute_lambda_from_personality(
            personality,
            lambda_base=0.8,
            n_mod=0.30,
            o_mod=0.20,
            c_mod=0.20,
        )
        # 0.8 + 0.15 + 0.10 + 0.10 = 1.15 -> clamped to 0.95
        assert result == 0.95

    def test_clamping_low(self):
        """Extreme opposite traits should clamp lambda to 0.05."""
        personality = {
            "neuroticism": 0.0,
            "openness": 0.0,
            "conscientiousness": 1.0,
        }
        result = compute_lambda_from_personality(
            personality,
            lambda_base=0.1,
            n_mod=0.15,
            o_mod=0.10,
            c_mod=0.10,
        )
        # 0.1 - 0.075 - 0.05 - 0.05 = -0.075 -> clamped to 0.05
        assert result == 0.05

    def test_missing_traits_default_to_neutral(self):
        """Missing personality keys should behave as 0.5 (no modulation)."""
        personality = {}
        result = compute_lambda_from_personality(
            personality,
            lambda_base=0.4,
            n_mod=0.15,
            o_mod=0.10,
            c_mod=0.10,
        )
        assert result == pytest.approx(0.4)

    def test_combined_traits(self):
        """Verify combined effect of all three traits."""
        personality = {
            "neuroticism": 0.8,
            "openness": 0.7,
            "conscientiousness": 0.3,
        }
        result = compute_lambda_from_personality(
            personality,
            lambda_base=0.3,
            n_mod=0.15,
            o_mod=0.10,
            c_mod=0.10,
        )
        # 0.3 + (0.8-0.5)*0.15 + (0.7-0.5)*0.10 - (0.3-0.5)*0.10
        # = 0.3 + 0.045 + 0.02 + 0.02 = 0.385
        assert result == pytest.approx(0.385)


class TestDetectTrend:
    """Tests for detect_trend."""

    def test_rising(self):
        # actual > expected * 1.05
        assert detect_trend(expected=10.0, actual=11.0, threshold=0.05) == "rising"

    def test_falling(self):
        # actual < expected * 0.95
        assert detect_trend(expected=10.0, actual=9.0, threshold=0.05) == "falling"

    def test_stable_within_threshold(self):
        # actual between 9.5 and 10.5
        assert detect_trend(expected=10.0, actual=10.3, threshold=0.05) == "stable"

    def test_stable_at_boundary(self):
        # actual = expected * 1.05 exactly (not strictly greater)
        assert detect_trend(expected=10.0, actual=10.5, threshold=0.05) == "stable"

    def test_large_threshold(self):
        """With a large threshold, most movements are stable."""
        assert detect_trend(expected=10.0, actual=12.0, threshold=0.25) == "stable"
        assert detect_trend(expected=10.0, actual=13.0, threshold=0.25) == "rising"

    def test_zero_expected(self):
        """When expected is 0, any positive actual is rising."""
        assert detect_trend(expected=0.0, actual=1.0, threshold=0.05) == "rising"


# -- Integration tests (DB required) --


@pytest.fixture
def user(db):
    return User.objects.create_user(
        email="exp@epocha.dev",
        username="expuser",
        password="pass1234",
    )


@pytest.fixture
def simulation(user):
    return Simulation.objects.create(
        name="ExpTest",
        seed=42,
        owner=user,
        config={
            "expectations_config": {
                "lambda_base": 0.3,
                "neuroticism_mod": 0.15,
                "openness_mod": 0.10,
                "conscientiousness_mod": 0.10,
                "trend_threshold": 0.05,
            },
        },
    )


@pytest.fixture
def world(simulation):
    return World.objects.create(
        simulation=simulation,
        distance_scale=133.0,
        tick_duration_hours=24.0,
    )


@pytest.fixture
def zone(world):
    return Zone.objects.create(
        world=world,
        name="TestZone",
        zone_type="urban",
        boundary=Polygon.from_bbox((0, 0, 100, 100)),
        center=Point(50, 50),
    )


@pytest.fixture
def zone_economy(zone):
    return ZoneEconomy.objects.create(
        zone=zone,
        market_prices={"subsistence": 3.0, "luxury": 50.0},
    )


@pytest.fixture
def goods(simulation):
    sub = GoodCategory.objects.create(
        simulation=simulation,
        code="subsistence",
        name="Subsistence",
        is_essential=True,
        base_price=3.0,
        price_elasticity=0.3,
    )
    lux = GoodCategory.objects.create(
        simulation=simulation,
        code="luxury",
        name="Luxury",
        is_essential=False,
        base_price=50.0,
        price_elasticity=2.0,
    )
    return [sub, lux]


@pytest.fixture
def agent(simulation, zone):
    return Agent.objects.create(
        simulation=simulation,
        name="TestAgent",
        role="farmer",
        personality={
            "openness": 0.5,
            "neuroticism": 0.5,
            "conscientiousness": 0.5,
        },
        location=Point(50, 50),
        zone=zone,
    )


@pytest.mark.django_db
class TestUpdateAgentExpectations:
    def test_creates_expectations_on_first_call(
        self,
        simulation,
        agent,
        zone_economy,
        goods,
    ):
        """First call should create expectations at current prices."""
        update_agent_expectations(simulation, tick=1)

        expectations = AgentExpectation.objects.filter(agent=agent)
        assert expectations.count() == 2

        sub_exp = expectations.get(good_code="subsistence")
        assert sub_exp.expected_price == pytest.approx(3.0)
        assert sub_exp.trend_direction == "stable"
        assert sub_exp.confidence == 0.5
        assert sub_exp.updated_at_tick == 1

    def test_nerlove_formula_on_second_call(
        self,
        simulation,
        agent,
        zone_economy,
        goods,
    ):
        """Second call should apply E_new = lambda * P + (1 - lambda) * E_old."""
        # Tick 1: initialize
        update_agent_expectations(simulation, tick=1)

        # Change prices for tick 2
        zone_economy.market_prices = {"subsistence": 4.0, "luxury": 50.0}
        zone_economy.save(update_fields=["market_prices"])

        update_agent_expectations(simulation, tick=2)

        exp = AgentExpectation.objects.get(agent=agent, good_code="subsistence")
        # lambda = 0.3 (neutral personality), E_old = 3.0, P = 4.0
        # E_new = 0.3 * 4.0 + 0.7 * 3.0 = 1.2 + 2.1 = 3.3
        assert exp.expected_price == pytest.approx(3.3)
        assert exp.updated_at_tick == 2
        assert exp.trend_direction == "rising"

    def test_personality_modulates_lambda(
        self,
        simulation,
        zone,
        zone_economy,
        goods,
    ):
        """High-neuroticism agent should adapt faster than neutral."""
        neurotic_agent = Agent.objects.create(
            simulation=simulation,
            name="Neurotic",
            role="merchant",
            personality={
                "openness": 0.5,
                "neuroticism": 1.0,
                "conscientiousness": 0.5,
            },
            location=Point(50, 50),
            zone=zone,
        )

        # Tick 1: initialize
        update_agent_expectations(simulation, tick=1)

        # Change price
        zone_economy.market_prices = {"subsistence": 5.0, "luxury": 50.0}
        zone_economy.save(update_fields=["market_prices"])

        update_agent_expectations(simulation, tick=2)

        exp = AgentExpectation.objects.get(
            agent=neurotic_agent,
            good_code="subsistence",
        )
        # lambda = 0.3 + (1.0 - 0.5) * 0.15 = 0.375
        # E_new = 0.375 * 5.0 + 0.625 * 3.0 = 1.875 + 1.875 = 3.75
        assert exp.expected_price == pytest.approx(3.75)
        assert exp.lambda_rate == pytest.approx(0.375)

    def test_confidence_increases_on_accurate_prediction(
        self,
        simulation,
        agent,
        zone_economy,
        goods,
    ):
        """Confidence should increase when prediction error is small."""
        update_agent_expectations(simulation, tick=1)

        # Price barely changes (within threshold)
        zone_economy.market_prices = {"subsistence": 3.1, "luxury": 50.0}
        zone_economy.save(update_fields=["market_prices"])

        update_agent_expectations(simulation, tick=2)

        exp = AgentExpectation.objects.get(agent=agent, good_code="subsistence")
        # Initial confidence was 0.5, prediction error |3.1 - 3.0| / 3.0 = 0.033 < 0.05
        assert exp.confidence == pytest.approx(0.55)

    def test_confidence_decreases_on_bad_prediction(
        self,
        simulation,
        agent,
        zone_economy,
        goods,
    ):
        """Confidence should decrease when prediction error is large."""
        update_agent_expectations(simulation, tick=1)

        # Large price change
        zone_economy.market_prices = {"subsistence": 6.0, "luxury": 50.0}
        zone_economy.save(update_fields=["market_prices"])

        update_agent_expectations(simulation, tick=2)

        exp = AgentExpectation.objects.get(agent=agent, good_code="subsistence")
        # prediction error |6.0 - 3.0| / 6.0 = 0.5 > 0.05
        assert exp.confidence == pytest.approx(0.45)

    def test_no_goods_skips_gracefully(self, simulation, agent, zone_economy):
        """No goods in simulation should not crash."""
        update_agent_expectations(simulation, tick=1)
        assert AgentExpectation.objects.count() == 0

    def test_no_prices_skips_gracefully(
        self,
        simulation,
        agent,
        goods,
    ):
        """No zone economies (so no prices) should not crash."""
        update_agent_expectations(simulation, tick=1)
        assert AgentExpectation.objects.count() == 0

    def test_multiple_agents(
        self,
        simulation,
        zone,
        zone_economy,
        goods,
    ):
        """Multiple agents should each get their own expectations."""
        agents = []
        for i in range(3):
            a = Agent.objects.create(
                simulation=simulation,
                name=f"Agent{i}",
                role="farmer",
                personality={"openness": 0.5},
                location=Point(50, 50),
                zone=zone,
            )
            agents.append(a)

        update_agent_expectations(simulation, tick=1)

        # 3 agents * 2 goods = 6 expectations
        assert AgentExpectation.objects.count() == 6

    def test_convergence_over_many_ticks(
        self,
        simulation,
        agent,
        zone_economy,
        goods,
    ):
        """After many ticks at constant price, expectation should converge."""
        # Start with expectation at 3.0, actual is 5.0
        update_agent_expectations(simulation, tick=1)

        zone_economy.market_prices = {"subsistence": 5.0, "luxury": 50.0}
        zone_economy.save(update_fields=["market_prices"])

        for t in range(2, 22):
            update_agent_expectations(simulation, t)

        exp = AgentExpectation.objects.get(agent=agent, good_code="subsistence")
        # After 20 ticks with lambda=0.3, E should be very close to 5.0
        assert abs(exp.expected_price - 5.0) < 0.01

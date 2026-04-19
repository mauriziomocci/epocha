"""Unit tests for demography/context.py integration helpers."""
from __future__ import annotations

import pytest
from django.contrib.gis.geos import Point, Polygon

from epocha.apps.agents.models import Agent
from epocha.apps.demography.context import (
    compute_aggregate_outlook,
    compute_subsistence_threshold,
)
from epocha.apps.economy.models import BankingState, GoodCategory, ZoneEconomy
from epocha.apps.simulation.models import Simulation
from epocha.apps.users.models import User
from epocha.apps.world.models import Government, World, Zone


@pytest.fixture
def sim_with_zone(db):
    """Build the minimum scaffolding: user, simulation, world, zone, and an agent."""
    user = User.objects.create_user(
        email="ctx@epocha.dev", username="ctxuser", password="pass1234",
    )
    sim = Simulation.objects.create(
        name="ContextTest", seed=1, owner=user, current_tick=0,
    )
    world = World.objects.create(simulation=sim, stability_index=0.7)
    zone = Zone.objects.create(
        world=world,
        name="CtxZone",
        zone_type="commercial",
        boundary=Polygon.from_bbox((0, 0, 100, 100)),
        center=Point(50, 50),
    )
    agent = Agent.objects.create(
        simulation=sim,
        name="CtxAgent",
        role="farmer",
        zone=zone,
        location=Point(50, 50),
        health=1.0,
        age=30,
        birth_tick=0,
        mood=0.5,
    )
    return sim, zone, agent


# ---------------------------------------------------------------------------
# compute_subsistence_threshold tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_subsistence_threshold_no_zone_economy(sim_with_zone):
    """Returns 0.0 when no ZoneEconomy record exists for the zone."""
    sim, zone, _ = sim_with_zone
    result = compute_subsistence_threshold(sim, zone)
    assert result == 0.0


@pytest.mark.django_db
def test_subsistence_threshold_positive_with_essentials(sim_with_zone):
    """Returns a positive value when essential goods and a ZoneEconomy exist.

    Creates a ZoneEconomy with a market_prices entry for the essential good so
    that at least one price * SUBSISTENCE_NEED_PER_AGENT contributes to the sum.
    """
    from epocha.apps.economy.market import SUBSISTENCE_NEED_PER_AGENT

    sim, zone, _ = sim_with_zone
    # price_elasticity=0.3 for essential food goods (Andreyeva et al. 2010)
    good = GoodCategory.objects.create(
        simulation=sim,
        code="FOOD",
        name="Food",
        is_essential=True,
        base_price=10.0,
        price_elasticity=0.3,
    )
    # market_prices maps good.code to the current local price
    ZoneEconomy.objects.create(
        zone=zone,
        market_prices={good.code: 5.0},
    )
    result = compute_subsistence_threshold(sim, zone)
    expected = 5.0 * SUBSISTENCE_NEED_PER_AGENT
    assert result == pytest.approx(expected)
    assert result > 0.0


# ---------------------------------------------------------------------------
# compute_aggregate_outlook tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_aggregate_outlook_no_banking_no_government(sim_with_zone):
    """Returns 0.0 when neither BankingState nor Government exist.

    With no BankingState, conf_norm defaults to 0.0.
    With no Government, stability_norm defaults to 0.0.
    Agent mood defaults to 0.5 (neutral), so mood_norm = 0.0.
    Average of (0.0, 0.0, 0.0) = 0.0.
    """
    _, _, agent = sim_with_zone
    result = compute_aggregate_outlook(agent)
    assert result == pytest.approx(0.0)


@pytest.mark.django_db
def test_aggregate_outlook_minimum_returns_minus_one(sim_with_zone):
    """Returns approximately -1.0 when mood, confidence, and stability are all at minimum.

    mood=0.0 -> mood_norm=-1.0
    confidence_index=0.0 -> conf_norm=-1.0
    stability=0.0 -> stability_norm=-1.0
    average = -1.0
    """
    sim, _, agent = sim_with_zone
    agent.mood = 0.0
    agent.save()

    BankingState.objects.create(
        simulation=sim,
        reserve_ratio=0.1,
        base_interest_rate=0.05,
        confidence_index=0.0,
    )
    Government.objects.create(simulation=sim, stability=0.0)

    result = compute_aggregate_outlook(agent)
    assert result == pytest.approx(-1.0)


@pytest.mark.django_db
def test_aggregate_outlook_combines_three_components(sim_with_zone):
    """Verifies the arithmetic mean of the three normalised components.

    mood=1.0     -> mood_norm = +1.0
    confidence=1.0 -> conf_norm = +1.0
    stability=0.5  -> stability_norm = 0.0
    expected average = (1.0 + 1.0 + 0.0) / 3 = 0.6667
    """
    sim, _, agent = sim_with_zone
    agent.mood = 1.0
    agent.save()

    BankingState.objects.create(
        simulation=sim,
        reserve_ratio=0.1,
        base_interest_rate=0.05,
        confidence_index=1.0,
    )
    Government.objects.create(simulation=sim, stability=0.5)

    result = compute_aggregate_outlook(agent)
    assert result == pytest.approx((1.0 + 1.0 + 0.0) / 3.0)

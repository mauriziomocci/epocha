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
        email="ctx@epocha.dev",
        username="ctxuser",
        password="pass1234",
    )
    sim = Simulation.objects.create(
        name="ContextTest",
        seed=1,
        owner=user,
        current_tick=0,
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


class TestHouseholdKeys:
    """Direct tests for the shared household derivation.

    Round 8 noted that nothing imported this function: its edges were only
    ever reached through its two callers, so a change in its contract would
    surface as a puzzling failure somewhere else. These pin the contract
    itself.
    """

    @staticmethod
    def _stub(agent_id, parent=None, other=None, caretaker=None):
        class _A:
            id = agent_id
            parent_agent_id = parent
            other_parent_agent_id = other
            caretaker_agent_id = caretaker

        return _A()

    def test_an_adult_is_its_own_household(self, db):
        from epocha.apps.demography.context import household_keys

        adult = self._stub(1)
        keys = household_keys([adult], [40.0], None, adulthood_age=18.0)
        assert keys == {1: (1,)}

    def test_an_adult_child_of_a_living_parent_is_not_anchored(self, db):
        """The age test, which keeps a sixty-year-old out of his father's roof."""
        from epocha.apps.demography.context import household_keys

        parent, child = self._stub(1), self._stub(2, parent=1)
        keys = household_keys([parent, child], [85.0, 60.0], None, adulthood_age=18.0)
        assert keys[2] == (2,)

    def test_the_guardian_order_is_mother_then_father_then_caretaker(self, db):
        from epocha.apps.demography.context import household_keys

        mother, father, guardian = self._stub(1), self._stub(2), self._stub(3)
        by_mother = self._stub(4, parent=1, other=2, caretaker=3)
        by_father = self._stub(5, parent=99, other=2, caretaker=3)
        by_caretaker = self._stub(6, parent=99, other=98, caretaker=3)
        living = [mother, father, guardian, by_mother, by_father, by_caretaker]
        ages = [40.0, 40.0, 40.0, 3.0, 3.0, 3.0]

        keys = household_keys(living, ages, None, adulthood_age=18.0)

        assert keys[4] == (1,), "a living mother must win"
        assert keys[5] == (2,), "the father must be used when the mother is gone"
        assert keys[6] == (3,), "the caretaker is the last resort, not the first"

    def test_a_cycle_terminates(self, db):
        """The data model does not forbid it, so the walk must not hang."""
        from epocha.apps.demography.context import household_keys

        a, b = self._stub(1, parent=2), self._stub(2, parent=1)
        keys = household_keys([a, b], [3.0, 3.0], None, adulthood_age=18.0)
        assert set(keys) == {1, 2}


class TestStarvingHouseholds:
    """`starving_households`, the one "under subsistence" of the subsystem.

    Pure over its inputs, so it is tested on stand-ins: the starvation
    counter and emergency flight both reach it only through a whole tick.
    """

    @staticmethod
    def _member(agent_id, wealth, zone_id=1):
        from types import SimpleNamespace

        return SimpleNamespace(id=agent_id, wealth=wealth, zone_id=zone_id)

    def test_the_threshold_is_the_line_itself_not_below_it(self):
        """Wealth exactly equal to the members' combined threshold feeds the
        household; one unit less does not. The counter's original predicate
        was a strict `<`, and the two callers must not drift from it."""
        from epocha.apps.demography.context import starving_households

        fed = [self._member(1, 6.0), self._member(2, 4.0)]
        short = [self._member(3, 6.0), self._member(4, 3.0)]
        keys = {1: (1, 2), 2: (1, 2), 3: (3, 4), 4: (3, 4)}

        starving = starving_households(fed + short, keys, {1: 5.0})

        assert starving == {(3, 4)}

    def test_each_member_is_priced_at_their_own_zone(self):
        """A household split across two zones owes each zone's threshold for
        the member who lives there, not the decider's twice."""
        from epocha.apps.demography.context import starving_households

        members = [self._member(1, 8.0, zone_id=1), self._member(2, 0.0, zone_id=2)]
        keys = {1: (1, 2), 2: (1, 2)}

        assert starving_households(members, keys, {1: 2.0, 2: 7.0}) == {(1, 2)}
        assert starving_households(members, keys, {1: 2.0, 2: 5.0}) == set()

"""Tests of the rule-based marriage market (spec 20261029-123404, phase 5).

The pure tests use `types.SimpleNamespace` agents; the database tests build
agents as `test_couple.py` does, and reuse its fixture and helper.
"""

from __future__ import annotations

import math
import random
import types
from dataclasses import dataclass

import pytest

from epocha.apps.agents.models import Agent
from epocha.apps.demography.couple import (
    MarketPopulation,
    MarriageHistory,
    dissolve_on_death,
    draw_seekers,
    form_couple,
    form_matched_couples,
    match_markets,
    partition_by_market,
    read_market_population,
    seek_probability_for,
)
from epocha.apps.demography.models import Couple
from epocha.apps.demography.nuptiality import first_marriage_schedule
from epocha.apps.demography.orchestrator import DemographyTickContext
from epocha.apps.demography.template_loader import load_template
from epocha.apps.demography.tests.test_couple import (  # reused fixture and helper
    _make_agent,
    sim_with_zone,  # noqa: F401
)

DAILY_WORLD_HOURS = 24.0
MARKET_TICK = 500


def _christian_context(sim, tick=MARKET_TICK):
    return DemographyTickContext(
        simulation=sim,
        tick=tick,
        template=load_template("pre_industrial_christian"),
        tick_duration_hours=DAILY_WORLD_HOURS,
    )


# ---------------------------------------------------------------------------
# read_market_population
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_the_market_population_keeps_only_the_eligible_unpartnered_binary_adults(
    sim_with_zone,  # noqa: F811
):
    sim, zone = sim_with_zone
    eligible_woman = _make_agent(sim, zone, "Eligible")
    bisexual_woman = _make_agent(
        sim, zone, "Bisexual", sexual_orientation=Agent.SexualOrientation.BISEXUAL
    )
    eligible_man = _make_agent(sim, zone, "Man", gender=Agent.Gender.MALE)
    # Everything below must be left out.
    partnered_woman = _make_agent(sim, zone, "Partnered")
    partner = _make_agent(sim, zone, "Partner", gender=Agent.Gender.MALE)
    form_couple(partnered_woman, partner, formed_at_tick=1)
    _make_agent(sim, zone, "Dead", is_alive=False)
    _make_agent(sim, zone, "NonBinary", gender=Agent.Gender.NON_BINARY)
    _make_agent(sim, zone, "Homosexual", sexual_orientation=Agent.SexualOrientation.HOMOSEXUAL)
    _make_agent(sim, zone, "Asexual", sexual_orientation=Agent.SexualOrientation.ASEXUAL)
    # Twelve at the fixture tick, 13.4 at the market tick: under the era's 14.
    _make_agent(sim, zone, "Girl", age=12)
    widow = _make_agent(sim, zone, "Widow")
    late_husband = _make_agent(sim, zone, "LateHusband", gender=Agent.Gender.MALE, is_alive=False)
    form_couple(widow, late_husband, formed_at_tick=1)
    dissolve_on_death(late_husband, tick=MARKET_TICK - 100)

    population = read_market_population(_christian_context(sim))

    assert isinstance(population, MarketPopulation)
    assert [a.id for a in population.women] == [eligible_woman.id, bisexual_woman.id]
    assert [a.id for a in population.men] == [eligible_man.id]
    assert set(population.ages) == {eligible_woman.id, bisexual_woman.id, eligible_man.id}


@pytest.mark.django_db
def test_a_widow_whose_mourning_has_ended_is_in_the_market_population(
    sim_with_zone,  # noqa: F811
):
    sim, zone = sim_with_zone
    widow = _make_agent(sim, zone, "Widow")
    late_husband = _make_agent(sim, zone, "LateHusband", gender=Agent.Gender.MALE, is_alive=False)
    form_couple(widow, late_husband, formed_at_tick=1)
    dissolve_on_death(late_husband, tick=MARKET_TICK - 400)

    population = read_market_population(_christian_context(sim))

    assert [a.id for a in population.women] == [widow.id]
    assert population.history.widowed_at_tick == {widow.id: MARKET_TICK - 400}


@pytest.mark.django_db
def test_the_market_population_costs_three_queries(
    sim_with_zone,  # noqa: F811
    django_assert_num_queries,
):
    sim, zone = sim_with_zone
    _make_agent(sim, zone, "Woman")
    _make_agent(sim, zone, "Man", gender=Agent.Gender.MALE)
    context = _christian_context(sim)

    with django_assert_num_queries(3):
        population = read_market_population(context)

    # The simulation is joined into the agent rows, so form_couple's
    # `agent.simulation` costs no query per couple.
    with django_assert_num_queries(0):
        population.women[0].simulation


# ---------------------------------------------------------------------------
# seek_probability_for
# ---------------------------------------------------------------------------

WEEKLY_YEARS_PER_TICK = 168 / 8760


def _population(women_ages, ever_partnered=()):
    """An in-memory population: women with the given ages, no men."""
    women = [types.SimpleNamespace(id=index + 1) for index in range(len(women_ages))]
    return MarketPopulation(
        women=women,
        men=[],
        ages={woman.id: age for woman, age in zip(women, women_ages)},
        history=MarriageHistory(frozenset(ever_partnered), {}),
    )


def _christian_schedule():
    return first_marriage_schedule(load_template("pre_industrial_christian")["couple"])


def test_a_never_partnered_woman_gets_the_first_marriage_probability():
    schedule = _christian_schedule()
    population = _population([25.0])

    probability = seek_probability_for(population, schedule, 0.10, WEEKLY_YEARS_PER_TICK)

    assert probability(population.women[0]) == schedule.tick_probability(
        25.0, WEEKLY_YEARS_PER_TICK
    )


def test_a_woman_who_was_partnered_gets_the_remarriage_probability():
    population = _population([25.0], ever_partnered={1})

    probability = seek_probability_for(
        population, _christian_schedule(), 0.10, WEEKLY_YEARS_PER_TICK
    )

    assert probability(population.women[0]) == pytest.approx(
        1 - math.exp(-0.10 * WEEKLY_YEARS_PER_TICK), abs=1e-15
    )


def test_a_never_partnered_girl_below_the_schedule_minimum_age_gets_zero():
    population = _population([13.5])

    probability = seek_probability_for(
        population, _christian_schedule(), 0.10, WEEKLY_YEARS_PER_TICK
    )

    assert probability(population.women[0]) == 0.0


# ---------------------------------------------------------------------------
# draw_seekers
# ---------------------------------------------------------------------------


def _women(count):
    return [types.SimpleNamespace(id=index + 1) for index in range(count)]


def test_with_probability_one_every_woman_is_a_seeker_and_with_zero_none():
    women = _women(20)

    assert draw_seekers(women, lambda woman: 1.0, random.Random(7)) == women
    assert draw_seekers(women, lambda woman: 0.0, random.Random(7)) == []


def test_the_stream_consumption_does_not_depend_on_the_probabilities():
    women = _women(20)
    rng_never, rng_always = random.Random(7), random.Random(7)

    draw_seekers(women, lambda woman: 0.0, rng_never)
    draw_seekers(women, lambda woman: 1.0, rng_always)

    assert rng_never.getstate() == rng_always.getstate()


def test_equal_seeds_give_equal_seekers():
    women = _women(50)

    first = draw_seekers(women, lambda woman: 0.3, random.Random(11))
    second = draw_seekers(women, lambda woman: 0.3, random.Random(11))

    assert first == second
    assert 0 < len(first) < len(women)


# ---------------------------------------------------------------------------
# partition_by_market
# ---------------------------------------------------------------------------


def _in_zones(*zone_ids):
    return [types.SimpleNamespace(id=index + 1, zone_id=z) for index, z in enumerate(zone_ids)]


def test_same_zone_groups_by_zone_with_the_null_zone_first():
    agents = _in_zones(7, None, 3, 7)

    markets = partition_by_market(agents, "same_zone")

    assert [key for key, _ in markets] == [None, 3, 7]
    assert [[a.id for a in group] for _, group in markets] == [[2], [3], [1, 4]]


def test_world_radius_is_one_market_keyed_none():
    agents = _in_zones(7, None, 3)

    markets = partition_by_market(agents, "world")

    assert markets == [(None, agents)]


def test_an_unknown_radius_raises():
    with pytest.raises(ValueError, match="adjacent_zones"):
        partition_by_market(_in_zones(1), "adjacent_zones")


# ---------------------------------------------------------------------------
# match_markets
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _Person:
    """A hashable stand-in for an agent: `stable_matching` keys dicts by agent,
    and a `SimpleNamespace` is not hashable (a model instance is)."""

    id: int
    zone_id: int | None


def _people(first_id, count, zone_id):
    return [_Person(id=first_id + i, zone_id=zone_id) for i in range(count)]


def test_surplus_seekers_stay_unmatched_and_no_candidate_is_taken_twice():
    """SC-004: 100 seekers for 10 candidates in one zone give exactly 10 pairs."""
    seekers = _people(1, 100, zone_id=1)
    candidates = _people(1001, 10, zone_id=1)

    pairs = match_markets(seekers, candidates, "same_zone", lambda w, m: 1 / (1 + abs(w.id - m.id)))

    assert len(pairs) == 10
    assert len({man.id for _, man in pairs}) == 10
    assert len({woman.id for woman, _ in pairs}) == 10


def test_the_radius_decides_whether_a_better_candidate_in_another_zone_counts():
    """User Story 3, scenario 2: the zone-B candidate scores higher for the
    seeker, but under `same_zone` only the zone-A one is reachable."""
    seeker = _Person(id=1, zone_id=10)
    near = _Person(id=100, zone_id=10)
    better_far = _Person(id=101, zone_id=20)

    def score(woman, man):
        return 0.9 if man is better_far else 0.1

    local = match_markets([seeker], [near, better_far], "same_zone", score)
    anywhere = match_markets([seeker], [near, better_far], "world", score)

    assert local == [(seeker, near)]
    assert anywhere == [(seeker, better_far)]


def test_the_pairs_come_out_in_ascending_woman_id_across_markets():
    low_zone_seeker = _Person(id=9, zone_id=1)
    high_zone_seeker = _Person(id=2, zone_id=5)
    man_low = _Person(id=50, zone_id=1)
    man_high = _Person(id=51, zone_id=5)

    pairs = match_markets(
        [low_zone_seeker, high_zone_seeker], [man_low, man_high], "same_zone", lambda w, m: 0.5
    )

    assert [woman.id for woman, _ in pairs] == [2, 9]


# ---------------------------------------------------------------------------
# form_matched_couples
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_two_seekers_and_two_men_form_two_couples_at_the_tick(sim_with_zone):  # noqa: F811
    sim, zone = sim_with_zone
    women = [_make_agent(sim, zone, f"Woman{i}") for i in range(2)]
    for i in range(2):
        _make_agent(sim, zone, f"Man{i}", gender=Agent.Gender.MALE)
    context = _christian_context(sim)
    population = read_market_population(context)

    couples = form_matched_couples(context, population, population.women)

    assert len(couples) == 2
    assert {c.formed_at_tick for c in couples} == {MARKET_TICK}
    assert {c.couple_type for c in couples} == {"monogamous"}
    assert {c.agent_a_id for c in couples} | {c.agent_b_id for c in couples} >= {
        w.id for w in women
    }
    assert Couple.objects.filter(simulation=sim).count() == 2


@pytest.mark.django_db
def test_no_seekers_issue_no_query(sim_with_zone, django_assert_num_queries):  # noqa: F811
    sim, zone = sim_with_zone
    _make_agent(sim, zone, "Woman")
    _make_agent(sim, zone, "Man", gender=Agent.Gender.MALE)
    context = _christian_context(sim)
    population = read_market_population(context)

    with django_assert_num_queries(0):
        assert form_matched_couples(context, population, []) == []

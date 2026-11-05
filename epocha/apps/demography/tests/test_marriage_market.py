"""Tests of the rule-based marriage market (spec 20261029-123404, phase 5).

The pure tests use `types.SimpleNamespace` agents; the database tests build
agents as `test_couple.py` does, and reuse its fixture and helper.
"""

from __future__ import annotations

import pytest

from epocha.apps.agents.models import Agent
from epocha.apps.demography.couple import (
    MarketPopulation,
    dissolve_on_death,
    form_couple,
    read_market_population,
)
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

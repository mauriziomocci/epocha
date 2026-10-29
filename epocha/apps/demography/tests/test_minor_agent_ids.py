"""The decision loop's exclusion list: who is too young to be asked to decide.

`migration.coordinate_family_migration` guarantees a household's minors move
with their guardian and are never offered a `move_to` choice of their own,
and assigns the enforcement to the orchestrator. `minor_agent_ids` is that
enforcement's single predicate: the tick loop asks it, the demography
subsystem answers, and the age threshold stays where the household derivation
already reads it (the era template's `migration.adulthood_age`).
"""

from __future__ import annotations

import pytest
from django.contrib.gis.geos import Point, Polygon
from django.db import connection
from django.test.utils import CaptureQueriesContext

from epocha.apps.agents.models import Agent
from epocha.apps.demography import orchestrator
from epocha.apps.demography.template_loader import load_template
from epocha.apps.simulation.models import Simulation
from epocha.apps.users.models import User
from epocha.apps.world.models import World, Zone

TICKS_PER_YEAR = 365.0  # the default 24h tick

# The shipped template the simulations below default to; its threshold is read
# from the template, never repeated here as a literal.
ADULTHOOD_AGE = float(load_template("pre_industrial_christian")["migration"]["adulthood_age"])


@pytest.fixture
def sim_with_zone(db):
    user = User.objects.create_user(
        email="minors@epocha.dev", username="minorsuser", password="pass1234"
    )
    sim = Simulation.objects.create(
        name="MinorsTest",
        seed=2026,
        owner=user,
        current_tick=5000,
        config={"demography_enabled": True},
    )
    world = World.objects.create(simulation=sim, stability_index=0.7)
    zone = Zone.objects.create(
        world=world,
        name="MinorsZone",
        zone_type="residential",
        boundary=Polygon.from_bbox((0, 0, 100, 100)),
        center=Point(50, 50),
    )
    return sim, zone


def _agent(sim, zone, name, age_years, **kwargs):
    defaults = dict(
        role="farmer",
        location=Point(50, 50),
        age=int(age_years),
        birth_tick=int(sim.current_tick - age_years * TICKS_PER_YEAR),
        personality={},
    )
    defaults.update(kwargs)
    return Agent.objects.create(simulation=sim, name=name, zone=zone, **defaults)


def test_a_newborn_and_a_child_are_minors_an_adult_is_not(sim_with_zone):
    sim, zone = sim_with_zone
    newborn = _agent(sim, zone, "Neonato", 0.0)
    child = _agent(sim, zone, "Bambino", ADULTHOOD_AGE - 2)
    adult = _agent(sim, zone, "Adulto", 30)

    minors = orchestrator.minor_agent_ids(sim, sim.current_tick)

    assert minors == {newborn.id, child.id}
    assert adult.id not in minors


def test_the_threshold_is_the_templates_and_is_inclusive_for_adults(sim_with_zone):
    """An agent exactly at `adulthood_age` is an adult (`age >= adulthood_age`,
    the comparison `household_keys` makes); one tick younger is a minor."""
    sim, zone = sim_with_zone
    at_threshold = _agent(sim, zone, "Sulla soglia", ADULTHOOD_AGE)
    one_tick_younger = _agent(
        sim,
        zone,
        "Un tick prima",
        ADULTHOOD_AGE,
        birth_tick=at_threshold.birth_tick + 1,
    )

    minors = orchestrator.minor_agent_ids(sim, sim.current_tick)

    assert at_threshold.id not in minors
    assert one_tick_younger.id in minors


def test_the_dead_are_not_listed(sim_with_zone):
    sim, zone = sim_with_zone
    dead_child = _agent(sim, zone, "Morto", 3, is_alive=False)

    assert dead_child.id not in orchestrator.minor_agent_ids(sim, sim.current_tick)


def test_age_follows_birth_tick_not_the_frozen_age_column(sim_with_zone):
    """`Agent.age` is written once and never advances: an agent whose column
    still says 5 but whose birth tick makes it 30 is an adult."""
    sim, zone = sim_with_zone
    grown = _agent(sim, zone, "Cresciuto", 30, age=5)

    assert grown.id not in orchestrator.minor_agent_ids(sim, sim.current_tick)


def test_an_agent_without_birth_tick_falls_back_to_the_age_column(sim_with_zone):
    sim, zone = sim_with_zone
    legacy_child = _agent(sim, zone, "Legacy bambino", 5, birth_tick=None, age=5)
    legacy_adult = _agent(sim, zone, "Legacy adulto", 40, birth_tick=None, age=40)

    minors = orchestrator.minor_agent_ids(sim, sim.current_tick)

    assert legacy_child.id in minors
    assert legacy_adult.id not in minors


def test_a_simulation_without_demography_has_no_minors_and_costs_no_query(
    sim_with_zone, django_assert_num_queries
):
    """Opt-in is the contract (FR-009): a simulation that never declared the
    key keeps its behaviour AND its query count, even if it holds children."""
    sim, zone = sim_with_zone
    sim.config = {}
    sim.save()
    _agent(sim, zone, "Bambino", 3)

    with django_assert_num_queries(0):
        assert orchestrator.minor_agent_ids(sim, sim.current_tick) == set()


def test_the_query_count_does_not_grow_with_the_population(sim_with_zone):
    sim, zone = sim_with_zone
    _agent(sim, zone, "Uno", 3)
    with CaptureQueriesContext(connection) as small:
        orchestrator.minor_agent_ids(sim, sim.current_tick)

    for index in range(20):
        _agent(sim, zone, f"Folla {index}", 3 if index % 2 else 30)
    with CaptureQueriesContext(connection) as large:
        orchestrator.minor_agent_ids(sim, sim.current_tick)

    assert len(large) == len(small)


def test_an_unknown_template_degrades_to_no_minors(sim_with_zone, caplog):
    """Same degradation as `run_demography_tick`: the block is skipped, named
    in the log, and the tick goes on."""
    sim, zone = sim_with_zone
    sim.config = {"demography_enabled": True, "demography_template": "no_such_era"}
    sim.save()
    _agent(sim, zone, "Bambino", 3)

    assert orchestrator.minor_agent_ids(sim, sim.current_tick) == set()
    assert any("no_such_era" in record.getMessage() for record in caplog.records)


def test_current_age_follows_birth_tick_at_the_simulations_current_tick(sim_with_zone):
    sim, zone = sim_with_zone
    grown = _agent(sim, zone, "Cresciuto", 30, age=5)

    assert orchestrator.current_age_in_years(grown) == pytest.approx(30.0, abs=0.01)


def test_current_age_falls_back_to_the_age_column_without_birth_tick(sim_with_zone):
    sim, zone = sim_with_zone
    legacy = _agent(sim, zone, "Legacy", 40, birth_tick=None, age=40)

    assert orchestrator.current_age_in_years(legacy) == 40.0

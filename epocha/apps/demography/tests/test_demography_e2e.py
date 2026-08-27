"""End-to-end acceptance for the whole work item (spec SC-001, US1).

The criterion the entire Plan 4 exists to satisfy: on a reference simulation
with demography active, agents are born, agents die, and the population
changes. Everything else in this branch is machinery for this.

It is deliberately an end-to-end run over many ticks rather than a unit test
with a forced draw. A unit test proves a step does what it is told; only a run
proves the steps compose -- that the order holds, that the seeded streams do
not collide, that the initialization leaves the population in a state where
the modules' preconditions are actually met.
"""

from __future__ import annotations

import pytest
from django.contrib.gis.geos import Point, Polygon

from epocha.apps.agents.models import Agent
from epocha.apps.demography.initialization import initialize_demography
from epocha.apps.demography.models import DemographyEvent, PopulationSnapshot
from epocha.apps.demography.orchestrator import run_demography_tick
from epocha.apps.simulation.models import Simulation
from epocha.apps.users.models import User
from epocha.apps.world.models import Government, World, Zone

TICKS_PER_YEAR = 365.0
# One simulated year. The per-tick hazards are annual rates divided by 365,
# so a shorter horizon over a small population expects well under one event
# and would fail or pass on luck rather than on behaviour.
TICKS = 365
FOUNDING_COUPLES = 30
# A cohort old enough that deaths are expected rather than hoped for. At the
# Heligman-Pollard senescence ages the annual hazard is tens of percent, so
# twenty of them over a simulated year expect several deaths; a handful of
# eighty-year-olds would expect well under one and the test would pass or
# fail on the seed rather than on the wiring.
ELDERS = 20
ELDER_AGE = 95


@pytest.fixture
def reference_simulation(db):
    """A founding population with the age and sex structure the templates
    assume: adults of both sexes across the fertile window, plus elders."""
    user = User.objects.create_user(
        email="e2e@epocha.dev", username="e2euser", password="pass1234"
    )
    sim = Simulation.objects.create(
        name="ReferenceRun",
        seed=2026,
        owner=user,
        current_tick=0,
        config={"demography_enabled": True},
    )
    world = World.objects.create(simulation=sim, stability_index=0.7)
    Government.objects.create(simulation=sim)
    zone = Zone.objects.create(
        world=world,
        name="Village",
        zone_type="residential",
        boundary=Polygon.from_bbox((0, 0, 100, 100)),
        center=Point(50, 50),
    )

    for i in range(FOUNDING_COUPLES):
        Agent.objects.create(
            simulation=sim,
            name=f"Uomo{i}",
            zone=zone,
            role="farmer",
            location=Point(50, 50),
            health=1.0,
            wealth=100.0,
            age=20 + (i % 14) * 5,
            birth_tick=None,  # the generator's state: initialization repairs it
            education_level=0.5,
            social_class="working",
            gender=Agent.Gender.MALE,
            personality={},
        )
        Agent.objects.create(
            simulation=sim,
            name=f"Donna{i}",
            zone=zone,
            role="farmer",
            location=Point(50, 50),
            health=1.0,
            wealth=100.0,
            age=18 + (i % 7) * 4,
            birth_tick=None,
            education_level=0.5,
            social_class="working",
            gender=Agent.Gender.FEMALE,
            personality={},
        )

    for i in range(ELDERS):
        Agent.objects.create(
            simulation=sim,
            name=f"Anziano{i}",
            zone=zone,
            role="elder",
            location=Point(50, 50),
            health=1.0,
            wealth=100.0,
            age=ELDER_AGE,
            birth_tick=None,
            education_level=0.5,
            social_class="working",
            gender=Agent.Gender.MALE if i % 2 else Agent.Gender.FEMALE,
            personality={},
        )
    return sim


@pytest.mark.django_db
def test_the_population_lives(reference_simulation):
    """SC-001: births happen, deaths happen, the population changes.

    This is the sentence the build map carried for months as untrue -- "the
    models are audited but the loop never calls them".
    """
    sim = reference_simulation
    initialize_demography(sim)
    population_at_start = Agent.objects.filter(simulation=sim, is_alive=True).count()

    for tick in range(1, TICKS + 1):
        run_demography_tick(sim, tick)
        sim.current_tick = tick
        sim.save(update_fields=["current_tick"])

    births = DemographyEvent.objects.filter(
        simulation=sim, event_type=DemographyEvent.EventType.BIRTH
    ).count()
    deaths = DemographyEvent.objects.filter(
        simulation=sim, event_type=DemographyEvent.EventType.DEATH
    ).count()
    population_at_end = Agent.objects.filter(simulation=sim, is_alive=True).count()

    # Observed on this fixture at the time of writing: 14 births and 4 deaths
    # over the simulated year, 80 agents becoming 90. The crude birth rate that
    # implies is far above the pre-industrial historical range, but the fixture
    # is not a population -- it is thirty couples all inside the fertile window,
    # which no real age structure looks like. Whether the MODEL reproduces
    # historical rates is the validation work item's question, on a calibrated
    # age pyramid; this test only asserts that the machinery runs.
    assert births > 0, f"no birth in {TICKS} ticks"
    assert deaths > 0, f"no death in {TICKS} ticks"
    assert population_at_end != population_at_start


@pytest.mark.django_db
def test_every_tick_leaves_a_snapshot(reference_simulation):
    """SC-007 at the run level: the series historical validation reads."""
    sim = reference_simulation
    initialize_demography(sim)

    for tick in range(1, 11):
        run_demography_tick(sim, tick)
        sim.current_tick = tick
        sim.save(update_fields=["current_tick"])

    ticks_with_a_snapshot = set(
        PopulationSnapshot.objects.filter(simulation=sim).values_list("tick", flat=True)
    )
    assert ticks_with_a_snapshot == set(range(1, 11))


@pytest.mark.django_db
def test_two_simulations_sharing_a_seed_do_not_share_a_history(reference_simulation):
    """The documented limit, asserted instead of contradicted.

    `get_seeded_rng` mixes the simulation's database primary key into the
    seed material alongside `simulation.seed`, so re-running a published seed
    against a fresh database yields different streams -- the whitepaper states
    it as "seed portability across databases does not hold". A first version
    of this test asserted the opposite and failed, which is the useful
    outcome: the property to pin is the one the system has.

    Per-simulation reproducibility is unaffected and is covered where the
    streams themselves are tested: the same simulation, tick and phase always
    yield the same sequence.
    """
    sim = reference_simulation
    initialize_demography(sim)
    for tick in range(1, 61):
        run_demography_tick(sim, tick)
        sim.current_tick = tick
        sim.save(update_fields=["current_tick"])

    twin = Simulation.objects.create(
        name="Twin",
        seed=sim.seed,
        owner=sim.owner,
        current_tick=0,
        config={"demography_enabled": True},
    )

    from epocha.apps.demography.orchestrator import stream_for

    original = stream_for(sim, tick=1, phase="mortality").random()
    twin_draw = stream_for(twin, tick=1, phase="mortality").random()

    assert original != twin_draw, (
        "two simulations with the same seed drew the same stream: the primary "
        "key is no longer part of the derivation, which changes a documented "
        "property of the system"
    )

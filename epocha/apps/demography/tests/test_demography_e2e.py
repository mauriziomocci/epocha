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
from django.db.models import Q

from epocha.apps.agents.models import Agent
from epocha.apps.demography.couple import form_couple
from epocha.apps.demography.initialization import initialize_demography
from epocha.apps.demography.models import DemographyEvent, PopulationSnapshot
from epocha.apps.demography.orchestrator import DEMOGRAPHY_STEPS, run_demography_tick
from epocha.apps.economy.models import Currency, GoodCategory, ZoneEconomy
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
# Adults with nothing, in the expensive zone: the only population for which
# the subsistence predicate is true, and therefore the only one that makes
# the counter step and the forced-migration step do any work at all.
DESTITUTE = 6


@pytest.fixture
def reference_simulation(db):
    """A founding population with the age and sex structure the templates
    assume: adults of both sexes across the fertile window, plus elders."""
    user = User.objects.create_user(email="e2e@epocha.dev", username="e2euser", password="pass1234")
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
    refuge = Zone.objects.create(
        world=world,
        name="Rifugio",
        zone_type="residential",
        boundary=Polygon.from_bbox((200, 200, 300, 300)),
        center=Point(250, 250),
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

    # An economy, so the subsistence line is a real number. Without it
    # `compute_subsistence_threshold` returns 0.0, no agent is ever under the
    # line, the starvation counter never increments and emergency flight is
    # unreachable -- two of the eight steps iterating over nothing while the
    # run reports success.
    Currency.objects.create(
        simulation=sim, code="DEN", name="Denarius", symbol="D", total_supply=100000.0
    )
    GoodCategory.objects.create(
        simulation=sim,
        code="grain",
        name="Grain",
        is_essential=True,
        base_price=2.0,
        price_elasticity=0.3,
    )
    ZoneEconomy.objects.create(zone=zone, market_prices={"grain": 4.0})
    ZoneEconomy.objects.create(zone=refuge, market_prices={"grain": 1.0})

    # Destitute adults in the expensive zone: they fall under the line, the
    # counter climbs, and once it passes the era's `flight_trigger_ticks` the
    # forced-migration step has somewhere cheaper to send them.
    # Paired with EACH OTHER, and that is what makes them destitute rather
    # than merely poor. Subsistence is a household property: the counter asks
    # whether a household can feed itself, so a penniless agent married to a
    # solvent one is not starving. Initialization pairs almost every eligible
    # adult -- thirty-six couples in this fixture -- so leaving these six
    # single handed each of them a solvent spouse and the step measured
    # nothing. Coupling them here keeps them out of that matching and gives
    # the run one genuinely insolvent household per pair.
    destitute: list = []
    for i in range(DESTITUTE):
        destitute.append(
            Agent.objects.create(
                simulation=sim,
                name=f"Indigente{i}",
                zone=zone,
                role="farmer",
                location=Point(50, 50),
                health=1.0,
                wealth=0.0,
                age=30 + i,
                birth_tick=None,
                education_level=0.2,
                social_class="working",
                # Only the two that get paired below carry a woman each:
                # the rest stay male, because initialization pairs every
                # eligible adult it can and the couple-intent fixture needs a
                # man it left free.
                gender=Agent.Gender.FEMALE if i in (0, 2) else Agent.Gender.MALE,
                personality={},
            )
        )
    # Four of the six are paired into two insolvent households; the last two
    # stay free because `_file_couple_intents` needs a free man to resolve,
    # and they were the only free men in the fixture.
    paired = destitute[:4]
    for first, second in zip(paired[::2], paired[1::2], strict=True):
        form_couple(first, second, formed_at_tick=sim.current_tick)

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


def _intent(sim, agent, tick, payload):
    """A DecisionLog row shaped the way the couple module reads them."""
    import json

    from epocha.apps.agents.models import DecisionLog

    return DecisionLog.objects.create(
        simulation=sim,
        agent=agent,
        tick=tick,
        input_context="{}",
        output_decision=json.dumps(payload),
        llm_model="test",
    )


def _file_couple_intents(sim, tick):
    """Mutual pair-bond intents, and a separation, for the tick after `tick`.

    The two couple steps read `DecisionLog` rows at `tick - 1`, so a run whose
    fixture files none of them iterates an empty queryset for every tick of
    its horizon. That is how an end-to-end run can report success while a
    quarter of the declared order never executes a line.
    """
    from epocha.apps.demography.models import Couple

    unpartnered = [
        a
        for a in Agent.objects.filter(simulation=sim, is_alive=True).order_by("id")
        if not Couple.objects.filter(
            Q(agent_a=a) | Q(agent_b=a), dissolved_at_tick__isnull=True
        ).exists()
    ]
    men = [a for a in unpartnered if a.gender == Agent.Gender.MALE]
    assert men, "the fixture leaves no free man: nothing to resolve"

    # The founding pass pairs every eligible woman, because the fixture has
    # more men than women -- so a free woman has to be created here, after
    # initialization, and she stands for the ordinary case the step exists
    # for: someone who reaches marriageable age, or arrives, after the world
    # was founded.
    free_woman = Agent.objects.create(
        simulation=sim,
        name="Nubile",
        zone=men[0].zone,
        role="farmer",
        location=Point(50, 50),
        health=1.0,
        wealth=50.0,
        age=24,
        birth_tick=int(sim.current_tick - 24 * TICKS_PER_YEAR),
        education_level=0.5,
        social_class="working",
        gender=Agent.Gender.FEMALE,
        personality={},
    )
    _intent(sim, men[0], tick, {"action": "pair_bond", "target": {"match": free_woman.name}})
    _intent(sim, free_woman, tick, {"action": "pair_bond", "target": {"match": men[0].name}})

    return free_woman


@pytest.mark.django_db
def test_every_declared_step_does_work_in_the_reference_run(reference_simulation):
    """The run has to exercise the order it claims to prove.

    The module docstring says only a run proves the steps compose. It did not:
    the fixture filed no couple intent and carried no economy, so separations,
    couple formation, the starvation counter and forced migration iterated
    empty querysets for all 365 ticks while the acceptance test passed on
    births and deaths alone. Deleting those four entries from
    `DEMOGRAPHY_STEPS` left both e2e tests green -- half the declared order
    was unmeasured by the test written to measure it composing.

    Each step is asserted through an observable only that step produces, so
    the assertion cannot be satisfied by another step's work.
    """
    sim = reference_simulation
    initialize_demography(sim)
    _file_couple_intents(sim, tick=0)
    # Filed so the negative on step 1 below is a real refusal rather than an
    # absence of input.
    from epocha.apps.demography.models import Couple as _Couple

    _intent(
        sim,
        _Couple.objects.filter(simulation=sim, dissolved_at_tick__isnull=True).first().agent_a,
        0,
        {"action": "separate"},
    )

    for tick in range(1, TICKS + 1):
        run_demography_tick(sim, tick)
        sim.current_tick = tick
        sim.save(update_fields=["current_tick"])

    from epocha.apps.demography.models import Couple

    kinds = set(DemographyEvent.objects.filter(simulation=sim).values_list("event_type", flat=True))

    # 1 separations is NOT assertable on this run and saying why is the
    # point: `pre_industrial_christian` ships `divorce_enabled: false`, the
    # canonical indissolubility regime, so the step correctly returns without
    # dissolving anything however many intents are filed. Asserting a
    # dissolution here would be asserting against the era's own model. It is
    # proven separately, on an era that permits divorce, by
    # `test_the_separation_step_works_where_the_era_permits_divorce`.
    assert not Couple.objects.filter(
        simulation=sim, dissolution_reason=Couple.DissolutionReason.SEPARATE
    ).exists(), (
        "a couple was dissolved by separation under an era that forbids "
        "divorce: the step is not reading the era's own predicate"
    )
    # 2 couple formation: a couple formed after the founding pass.
    assert Couple.objects.filter(simulation=sim, formed_at_tick__gt=0).exists(), (
        "step 2 did nothing: every couple in the run came from initialization"
    )
    # 3 mortality and 7 fertility.
    assert DemographyEvent.EventType.DEATH in kinds, "step 3 did nothing"
    assert DemographyEvent.EventType.BIRTH in kinds, "step 7 did nothing"
    # 4 succession: an estate actually moved.
    assert DemographyEvent.EventType.INHERITANCE_TRANSFER in kinds, (
        "step 4 did nothing: no estate was settled in a run that had deaths"
    )
    # 5 the starvation counter: somebody was under the subsistence line.
    assert Agent.objects.filter(
        simulation=sim, consecutive_ticks_under_subsistence__gt=0
    ).exists(), (
        "step 5 did nothing: no agent was ever under the subsistence line, so "
        "the fixture has no economy or nobody destitute in it"
    )
    # 6 forced migration: flight or the trapped crisis that stands in for it.
    assert kinds & {
        DemographyEvent.EventType.MIGRATION,
        DemographyEvent.EventType.TRAPPED_CRISIS,
        DemographyEvent.EventType.MASS_FLIGHT,
    }, "step 6 did nothing: nobody fled and nobody was recorded as trapped"
    # 8 the snapshot.
    assert PopulationSnapshot.objects.filter(simulation=sim).count() == TICKS

    assert len(DEMOGRAPHY_STEPS) == 8, (
        "the declared order changed length: this test enumerates eight steps "
        "and must be extended with the new one rather than left behind"
    )


@pytest.mark.django_db
def test_the_separation_step_works_where_the_era_permits_divorce(reference_simulation):
    """Step 1, proven on an era that admits it.

    The reference run cannot prove this one: its era forbids divorce, so the
    step declines every intent by design. Under `industrial`, which ships
    `divorce_enabled: true`, the same intent must dissolve the couple in the
    tick after it was filed -- and dissolve it by SEPARATION, not by a death
    that happened to fall in the same tick.
    """
    from epocha.apps.demography.models import Couple

    sim = reference_simulation
    sim.config["demography_template"] = "industrial"
    sim.save(update_fields=["config"])
    initialize_demography(sim)

    couple = Couple.objects.filter(simulation=sim, dissolved_at_tick__isnull=True).first()
    assert couple is not None, "initialization formed no couple: nothing to separate"
    _intent(sim, couple.agent_a, 0, {"action": "separate"})

    run_demography_tick(sim, 1)

    couple.refresh_from_db()
    assert couple.dissolved_at_tick == 1
    assert couple.dissolution_reason == Couple.DissolutionReason.SEPARATE


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

    # Measured on this fixture on 2026-09-26: 7 births and 5 deaths over the
    # simulated year, 86 agents becoming 88 (the figures written here earlier,
    # 14, 4 and 80 to 90, predate the six destitute agents the fixture gained
    # for the subsistence counter). The crude birth rate that implies is far
    # above the pre-industrial historical range, but the fixture is not a
    # population -- it is thirty couples all inside the fertile window,
    # which no real age structure looks like. Whether the MODEL reproduces
    # historical rates is the validation work item's question, on a calibrated
    # age pyramid; this test only asserts that the machinery runs.
    assert births > 0, f"no birth in {TICKS} ticks"
    assert deaths > 0, f"no death in {TICKS} ticks"
    # The accounting identity, not `end != start`. The streams are keyed on
    # the simulation's primary key, so the run's births and deaths depend on
    # how many simulations the suite created first, and a year in which they
    # happen to balance is a living population, not a failure: measured,
    # this assertion used to be `end != start` and failed at 86 against 86
    # once the suite created a few more simulations. The identity is also
    # the stronger claim -- every birth adds a living agent, every death
    # removes one, and migration moves agents without creating or losing any.
    assert population_at_end == population_at_start + births - deaths, (
        f"{population_at_start} + {births} births - {deaths} deaths should be "
        f"{population_at_start + births - deaths} living agents, found {population_at_end}"
    )


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

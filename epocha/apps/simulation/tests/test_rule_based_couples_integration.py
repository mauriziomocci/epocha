"""Three rule-only years of a pre-industrial founding population (SC-006, US1).

The unit tests of the marriage market and of the founding prove each piece;
this one proves that they compose on the real tick loop: with
`max_protagonists = 0` no LLM decision exists, so every couple formed after the
founding comes from the rules, and every birth needs such a couple in an era
that forbids births out of wedlock.

The simulation is `running`, because `run_simulation_loop` returns at once on
a paused one. The suite runs Celery eagerly, so the real `finalize_tick`
executes (with an empty chord header the loop calls it directly and it
advances the tick) and only its re-enqueue, `run_simulation_loop.apply_async`,
is stopped, so that the test drives the ticks itself. `chord` is a spy around
the real one: it must never be called, which proves that no decision task
exists (the same seam as the Celery K = 0 test of
`test_engine_demography_wiring.py`).

The male age at first marriage is logged, never asserted. It is an indication
only: it rests on a handful of marriages (the log line gives n), and the
random streams are keyed on the simulation primary key, so the figure changes
with the order in which the suite creates simulations (5 marriages gave 20.78,
7 gave 23.24 and 25.38 on different orders). It is not a validation.

The assertion that a couple forms after the initialization is probabilistic,
like the girls test of `test_initialization.py`. Over the nine sessions of
`phase6-measurements.md` the number of marriages was 7, 5, 6, 3, 9, 6, 10, 2
and 10 (mean 6.44, variance over mean 1.28, close to Poisson). Under a Poisson
count with that mean the probability of none in a run is exp(-6.44) = 1.6e-3;
with the lower 95% limit of the mean (Student t, 8 degrees of freedom: 4.23)
it is 1.5e-2. This is an estimate from nine runs, not a bound: the stream is
keyed on the primary keys, which change with the suite order. The births
assertion rests on 33 to 63 births per run (diagnosis file), whose probability
of none is negligible next to the marriages.
"""

from __future__ import annotations

import logging
import random
from unittest.mock import MagicMock, patch

import pytest
from celery import chord
from django.contrib.gis.geos import Point, Polygon

from epocha.apps.agents.models import Agent, DecisionLog
from epocha.apps.demography.initialization import initialize_demography
from epocha.apps.demography.models import Couple
from epocha.apps.demography.orchestrator import age_in_years
from epocha.apps.demography.template_loader import load_template
from epocha.apps.simulation.models import Simulation
from epocha.apps.simulation.tasks import run_simulation_loop
from epocha.apps.users.models import User
from epocha.apps.world.models import Government, World, Zone

logger = logging.getLogger(__name__)

FOUNDERS = 300
WEEKLY_TICK_HOURS = 168.0
THREE_YEARS_IN_TICKS = 156
# Fixed seed of the age draw: the population is a fixture, not a sample.
AGE_DRAW_SEED = 7
FIXED_FACTION_IDENTITY = ("Faction", "Objective")


def _draw_ages(template: dict, count: int, rng: random.Random) -> list[int]:
    """Whole-year ages drawn from the template pyramid: band by weight, then uniform in it."""
    bands = template["age_pyramid"]
    weights = [band[2] for band in bands]
    ages = []
    for _ in range(count):
        low, high, _weight = rng.choices(bands, weights=weights)[0]
        ages.append(rng.randrange(int(low), int(high)))
    return ages


def build_rule_only_founders(
    simulation: Simulation, world: World, count: int, rng: random.Random
) -> None:
    """Create `count` founders on the world's zones, ages drawn from the era pyramid.

    Women and men alternate (even index female) and each pair of founders
    takes the next zone in id order, all heterosexual farmers with the same health, wealth and
    education, and no `birth_tick`: `initialize_demography` backfills it from
    the age. Module-level so that the marital-schedule run of
    `scripts/measure_marital_schedule_run.py` builds the same population
    instead of a copy.
    """
    template = load_template(simulation.config["demography_template"])
    ages = _draw_ages(template, count, rng)
    zones = list(world.zones.order_by("id"))
    Agent.objects.bulk_create(
        [
            Agent(
                simulation=simulation,
                name=f"Founder{index}",
                # Pairs of founders take the zones in turn; `index % len(zones)`
                # would put every woman in one zone when there are two.
                zone=zones[(index // 2) % len(zones)],
                role="farmer",
                location=Point(50, 50),
                health=1.0,
                wealth=100.0,
                age=age,
                birth_tick=None,  # `initialize_demography` backfills it from the age
                education_level=0.5,
                social_class="working",
                gender=Agent.Gender.MALE if index % 2 else Agent.Gender.FEMALE,
                sexual_orientation=Agent.SexualOrientation.HETEROSEXUAL,
                personality={},
            )
            for index, age in enumerate(ages)
        ]
    )


def _founded_simulation() -> Simulation:
    """A weekly-tick, two-zone world of 300 founders, initialized for demography."""
    user = User.objects.create_user(
        email="integration@epocha.dev", username="integrationuser", password="pass1234"
    )
    sim = Simulation.objects.create(
        name="RuleOnlyThreeYears",
        seed=2026,
        owner=user,
        current_tick=0,
        status=Simulation.Status.RUNNING,
        config={
            "demography_enabled": True,
            "demography_template": "pre_industrial_christian",
            "max_protagonists": 0,
        },
    )
    world = World.objects.create(
        simulation=sim, stability_index=0.7, tick_duration_hours=WEEKLY_TICK_HOURS
    )
    Government.objects.create(simulation=sim)
    for index in range(2):
        Zone.objects.create(
            world=world,
            name=f"Zone{index}",
            zone_type="residential",
            boundary=Polygon.from_bbox((0, 0, 100, 100)),
            center=Point(50, 50),
        )
    build_rule_only_founders(sim, world, FOUNDERS, random.Random(AGE_DRAW_SEED))
    initialize_demography(sim)
    return sim


def _member_names(couple: Couple) -> tuple[str, str]:
    """Names of the two members: the live agent's, else the snapshot of a dissolved couple."""
    return (
        couple.agent_a.name if couple.agent_a else couple.agent_a_name_snapshot,
        couple.agent_b.name if couple.agent_b else couple.agent_b_name_snapshot,
    )


def _male_ages_at_first_marriage(sim: Simulation, initialization_tick: int) -> list[float]:
    """Age in years of each man at his first couple formed after the initialization.

    A couple dissolved by a death keeps only the name snapshots of its members
    (`dissolve_on_death` nulls the foreign key of the deceased), so the members
    are resolved by name. Only founders can marry in three years, and their
    names are unique, so the lookup is exact.
    """
    template = load_template("pre_industrial_christian")
    acceleration = float(template.get("acceleration", 1.0))
    agents_by_name = {agent.name: agent for agent in Agent.objects.filter(simulation=sim)}
    married: set[str] = set()
    ages: list[float] = []
    for couple in (
        Couple.objects.filter(simulation=sim)
        .select_related("agent_a", "agent_b")
        .order_by("formed_at_tick", "id")
    ):
        names = _member_names(couple)
        if couple.formed_at_tick > initialization_tick:
            men = [
                agents_by_name[name]
                for name in names
                if name not in married
                and name in agents_by_name
                and agents_by_name[name].gender == Agent.Gender.MALE
            ]
            ages.extend(
                age_in_years(man, couple.formed_at_tick, WEEKLY_TICK_HOURS, acceleration)
                for man in men
            )
        married.update(names)
    return ages


def _log_marriage_indicators(sim: Simulation, initialization_tick: int) -> None:
    """Log (never assert) the indicative male age at first marriage of the run.

    For comparison only: 27.02 is the mean male age at first marriage of the
    decades 1700-1749 (bachelor-spinster marriages) in Wrigley et al. (1997),
    read through the secondary copy of Munro; Newton gives 27.1. The logged
    figure rests on n marriages of a 300-founder fixture and depends on the
    simulation primary key (module docstring), so the two are never to be
    read as a comparison of values.
    """
    ages = _male_ages_at_first_marriage(sim, initialization_tick)
    formed = Couple.objects.filter(
        simulation=sim, formed_at_tick__gt=initialization_tick
    ).select_related("agent_a", "agent_b")
    by_intent = sum(
        DecisionLog.objects.filter(
            simulation=sim,
            agent__name__in=_member_names(couple),
            output_decision__contains="pair_bond",
        ).exists()
        for couple in formed
    )
    logger.info(
        "rule-only run: indicative male mean age at first marriage %s over n=%d marriages "
        "(depends on the simulation primary key; period of the 27.02 reference: 1700-1749); "
        "%d of %d post-initialization couples formed by intents",
        f"{sum(ages) / len(ages):.2f}" if ages else "n/a",
        len(ages),
        by_intent,
        formed.count(),
    )


# Real transactions, as in production: the engine commits once per tick, so
# PostgreSQL prunes the superseded row versions of `agents_agent` (two steps
# rewrite every living agent each tick). In the single transaction of a plain
# `django_db` test ~100k dead row versions pile up and every query slows down,
# so the runtime depended on the tests that ran before this one (decision
# D-05-E-14; diagnosis in specs/20261029-123404-rule-based-couples/
# phase6-t069-diagnosis.md). Tables are flushed at the end of the test.
@pytest.mark.django_db(transaction=True)
def test_three_rule_only_years_form_couples_and_births_without_any_decision(caplog):
    sim = _founded_simulation()
    initialization_tick = sim.current_tick

    decision_client = MagicMock(side_effect=AssertionError("the decision LLM was called"))
    with (
        caplog.at_level(logging.INFO, logger=__name__),
        patch("epocha.apps.agents.decision.get_llm_client", decision_client),
        # Defensive, not exercised: measured on 2026-11-05, this run makes 0
        # calls to _generate_faction_identity. It guards against a faction
        # forming in a longer run and reaching the LLM.
        patch(
            "epocha.apps.agents.factions._generate_faction_identity",
            return_value=FIXED_FACTION_IDENTITY,
        ),
        patch("epocha.apps.simulation.tasks.run_simulation_loop.apply_async"),
        patch("epocha.apps.simulation.tasks.chord", wraps=chord) as chord_spy,
    ):
        for _ in range(THREE_YEARS_IN_TICKS):
            run_simulation_loop(sim.id)
        _log_marriage_indicators(sim, initialization_tick)

    sim.refresh_from_db()
    assert sim.current_tick == initialization_tick + THREE_YEARS_IN_TICKS
    decision_client.assert_not_called()
    chord_spy.assert_not_called()
    assert not DecisionLog.objects.filter(simulation=sim).exists()
    assert Couple.objects.filter(simulation=sim, formed_at_tick__gt=initialization_tick).exists()
    assert Agent.objects.filter(simulation=sim, birth_tick__gt=initialization_tick).exists()

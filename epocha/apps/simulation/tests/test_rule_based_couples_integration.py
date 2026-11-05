"""Three rule-only years of a pre-industrial founding population (SC-006, US1).

The unit tests of the marriage market and of the founding prove each piece;
this one proves that they compose on the real tick loop: with
`max_protagonists = 0` no LLM decision exists, so every couple formed after the
founding comes from the rules, and every birth needs such a couple in an era
that forbids births out of wedlock.

The simulation is `running`, with `finalize_tick` doubled to advance the tick
counter and `chord` patched, because `run_simulation_loop` returns at once on a
paused simulation (the same seam as the Celery K = 0 test of
`test_engine_demography_wiring.py`).
"""

from __future__ import annotations

import logging
import random
from unittest.mock import MagicMock, patch

import pytest
from django.contrib.gis.geos import Point, Polygon

from epocha.apps.agents.models import Agent, DecisionLog
from epocha.apps.demography.initialization import initialize_demography
from epocha.apps.demography.models import Couple
from epocha.apps.demography.template_loader import load_template
from epocha.apps.simulation.models import Simulation
from epocha.apps.simulation.tasks import run_simulation_loop
from epocha.apps.users.models import User
from epocha.apps.world.models import Government, World, Zone

logger = logging.getLogger(__name__)

FOUNDERS = 300
WEEKLY_TICK_HOURS = 168.0
HOURS_PER_YEAR = 8760.0
THREE_YEARS_IN_TICKS = 156
# Fixed seed of the age draw: the population is a fixture, not a sample.
AGE_DRAW_SEED = 7
FIXED_FACTION_IDENTITY = ("Faction", "Objective")


def _draw_ages(template: dict, count: int) -> list[int]:
    """Whole-year ages drawn from the template pyramid: band by weight, then uniform in it."""
    rng = random.Random(AGE_DRAW_SEED)
    bands = template["age_pyramid"]
    weights = [band[2] for band in bands]
    ages = []
    for _ in range(count):
        low, high, _weight = rng.choices(bands, weights=weights)[0]
        ages.append(rng.randrange(int(low), int(high)))
    return ages


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
    zones = [
        Zone.objects.create(
            world=world,
            name=f"Zone{index}",
            zone_type="residential",
            boundary=Polygon.from_bbox((0, 0, 100, 100)),
            center=Point(50, 50),
        )
        for index in range(2)
    ]
    ages = _draw_ages(load_template("pre_industrial_christian"), FOUNDERS)
    Agent.objects.bulk_create(
        [
            Agent(
                simulation=sim,
                name=f"Founder{index}",
                zone=zones[
                    (index // 2) % 2
                ],  # not index % 2: that would put every woman in one zone
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
    founders = {agent.name: agent for agent in Agent.objects.filter(simulation=sim)}
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
                founders[name]
                for name in names
                if name not in married
                and name in founders
                and founders[name].gender == Agent.Gender.MALE
            ]
            ages.extend(
                (couple.formed_at_tick - man.birth_tick) * WEEKLY_TICK_HOURS / HOURS_PER_YEAR
                for man in men
            )
        married.update(names)
    return ages


def _log_marriage_indicators(sim: Simulation, initialization_tick: int) -> None:
    """Log (never assert) the indicative male age at first marriage of the run.

    Wrigley et al. (1997), via Munro, give 27.02 and Newton 27.1 for England;
    this population is a 300-founder fixture, so the number is an indication
    of the machinery, not a validation.
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
        "rule-only run: indicative male mean age at first marriage %s over %d marriages; "
        "%d of %d post-initialization couples formed by intents",
        f"{sum(ages) / len(ages):.2f}" if ages else "n/a",
        len(ages),
        by_intent,
        formed.count(),
    )


@pytest.mark.django_db
def test_three_rule_only_years_form_couples_and_births_without_any_decision(caplog):
    sim = _founded_simulation()
    initialization_tick = sim.current_tick

    def _advance_tick(results, simulation_id, tick):
        Simulation.objects.filter(id=simulation_id).update(current_tick=tick)

    decision_client = MagicMock(side_effect=AssertionError("the decision LLM was called"))
    with (
        caplog.at_level(logging.INFO, logger=__name__),
        patch("epocha.apps.agents.decision.get_llm_client", decision_client),
        patch(
            "epocha.apps.agents.factions._generate_faction_identity",
            return_value=FIXED_FACTION_IDENTITY,
        ),
        patch("epocha.apps.simulation.tasks.chord"),
        patch("epocha.apps.simulation.tasks.finalize_tick", side_effect=_advance_tick),
    ):
        for _ in range(THREE_YEARS_IN_TICKS):
            run_simulation_loop(sim.id)
        _log_marriage_indicators(sim, initialization_tick)

    sim.refresh_from_db()
    assert sim.current_tick == initialization_tick + THREE_YEARS_IN_TICKS
    decision_client.assert_not_called()
    assert not DecisionLog.objects.filter(simulation=sim).exists()
    assert Couple.objects.filter(simulation=sim, formed_at_tick__gt=initialization_tick).exists()
    assert Agent.objects.filter(simulation=sim, birth_tick__gt=initialization_tick).exists()

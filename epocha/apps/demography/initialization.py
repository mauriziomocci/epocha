"""Demographic initialization of a founding population.

The demography modules assume two things about the population they are handed,
and until this module existed nothing established either.

**Ageing.** `birth_tick` is the project's only source of it. `Agent.age` is
written once by the world generator and never advances, and the fertility
module falls back to that column only when `birth_tick` is NULL -- so a
founding population without birth ticks has mortality and fertility frozen for
the entire run, at whatever ages the generator happened to produce.

**Couples.** Three of the five era templates, the default among them, return a
birth probability of exactly zero for a mother who is not in an active couple.
A founding population with no couples therefore cannot produce a birth in the
early ticks, and since nothing in production created couples, there was no
path from a fresh world to a first newborn.

Both are repaired here, once, before the first tick -- and only for
simulations that opted into demography, because writing birth ticks and
couples into a simulation that never asked for the subsystem would break the
same invariance the tick-loop block is careful to preserve.
"""

from __future__ import annotations

import logging
from typing import Any

from epocha.apps.demography.orchestrator import is_demography_enabled

logger = logging.getLogger(__name__)

HOURS_PER_YEAR = 8760.0


def initialize_demography(simulation: Any) -> None:
    """Prepare a founding population for the demography tick.

    Idempotent: an agent that already has a `birth_tick` keeps it, and an
    agent already in an active couple is not paired again. Re-running is
    therefore harmless, which matters because "has this world been
    initialized" is not a state anything currently records.
    """
    if not is_demography_enabled(simulation):
        return

    backfill_birth_ticks(simulation)

    # The template gates couple formation only -- backfilling ages above
    # depends on nothing but the agents themselves, so it has already run.
    # The two failure modes are caught BY NAME, mirroring the per-tick
    # orchestrator: the generator calls this unguarded, and before this
    # guard an invalid `demography_template` raised out of couple formation
    # and aborted the whole world generation.
    from epocha.apps.demography.template_loader import load_template

    config = getattr(simulation, "config", None) or {}
    template_name = config.get("demography_template", "pre_industrial_christian")
    try:
        template = load_template(template_name)
    except FileNotFoundError:
        logger.warning(
            "demography initialization: couples skipped for simulation %s: template %r not found",
            simulation.id,
            template_name,
        )
        return
    except ValueError:
        logger.warning(
            "demography initialization: couples skipped for simulation %s: template %r is invalid",
            simulation.id,
            template_name,
        )
        return

    form_initial_couples(simulation, template=template)


def backfill_birth_ticks(simulation: Any) -> None:
    """Give every living agent a `birth_tick` consistent with its age.

    Derived from the age the generator wrote rather than invented: an agent
    the world describes as forty has to still be forty on the tick this runs,
    or the population's age structure is silently rewritten between
    generation and the first tick.

    Agents that already carry a `birth_tick` are left alone -- this repairs
    what is missing and never overwrites a lineage a birth recorded. The dead
    are skipped: their age no longer advances, and rewriting it would edit
    history for no consumer.

    Query shape: one read, one `bulk_update`.
    """
    from epocha.apps.agents.models import Agent

    pending = list(
        Agent.objects.filter(
            simulation=simulation, is_alive=True, birth_tick__isnull=True
        ).order_by("id")
    )
    if not pending:
        return

    # Resolved only once there is something to repair. The tick duration is a
    # query of its own, and the demography block calls this every tick as its
    # self-repair: on an already-initialized simulation, which is every tick
    # after the first, there is nothing pending and the read above is the
    # whole cost.
    ticks_per_year = HOURS_PER_YEAR / max(1e-9, _tick_duration_hours(simulation))

    for agent in pending:
        agent.birth_tick = int(round(simulation.current_tick - (agent.age or 0) * ticks_per_year))

    Agent.objects.bulk_update(pending, ["birth_tick"])
    logger.info(
        "demography initialization: backfilled birth_tick for %d agents of simulation %s",
        len(pending),
        simulation.id,
    )


def form_initial_couples(simulation: Any, template: dict | None = None) -> None:
    """Pair the founding population's eligible adults.

    Reuses the couple module end to end -- `homogamy_score` for preferences,
    Gale-Shapley `stable_matching` for the assignment, `form_couple` for the
    canonical ordering -- so initial couples are formed by exactly the
    mechanism that forms couples later in the run, rather than by a second,
    parallel rule that would drift from it.

    Eligibility comes from the era template's own minimum marriage ages, not
    from a threshold invented here, and agents already in an active couple are
    skipped so a repeated call cannot double-pair anyone.

    Args:
        simulation: the simulation whose founding population is paired.
        template: the already-loaded era template, when the caller validated
            it -- `initialize_demography` does, so a load failure is handled
            once and by name. Omitted, it is loaded here, which is what the
            tests exercising this function in isolation use.
    """
    from epocha.apps.agents.models import Agent
    from epocha.apps.demography.couple import (
        form_couple,
        homogamy_score,
        stable_matching,
    )
    from epocha.apps.demography.models import Couple
    from epocha.apps.demography.template_loader import load_template

    if template is None:
        config = getattr(simulation, "config", None) or {}
        template = load_template(config.get("demography_template", "pre_industrial_christian"))
    couple_config = template["couple"]
    weights = couple_config["homogamy_weights"]
    min_age_male = couple_config["min_marriage_age_male"]
    min_age_female = couple_config["min_marriage_age_female"]

    already_partnered = set()
    for pair in Couple.objects.filter(
        simulation=simulation, dissolved_at_tick__isnull=True
    ).values_list("agent_a_id", "agent_b_id"):
        already_partnered.update(pair)

    living = list(
        Agent.objects.filter(simulation=simulation, is_alive=True)
        .exclude(id__in=already_partnered)
        .order_by("id")
    )
    men = [a for a in living if a.gender == Agent.Gender.MALE and (a.age or 0) >= min_age_male]
    women = [
        a for a in living if a.gender == Agent.Gender.FEMALE and (a.age or 0) >= min_age_female
    ]
    if not men or not women:
        return

    def score(proposer, respondent):
        return homogamy_score(proposer, respondent, weights)

    # No RNG stream is derived here, and that is deliberate rather than an
    # omission: Gale-Shapley is deterministic given its inputs, and both
    # sides are ordered by `id`, so the founding pairing already reproduces
    # exactly without consuming randomness. Deriving a stream and discarding
    # it would look like reproducibility work while doing none.
    for proposer, respondent in stable_matching(men, women, score):
        form_couple(proposer, respondent, formed_at_tick=simulation.current_tick)

    logger.info(
        "demography initialization: formed initial couples for simulation %s",
        simulation.id,
    )


def _tick_duration_hours(simulation: Any) -> float:
    from epocha.apps.world.models import World

    world = World.objects.filter(simulation=simulation).first()
    return float(getattr(world, "tick_duration_hours", 24.0) or 24.0) if world else 24.0

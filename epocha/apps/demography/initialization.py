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

Both are repaired here for simulations that opted into demography, and only
for those: writing birth ticks and couples into a simulation that never asked
for the subsystem would break the same invariance the tick-loop block is
careful to preserve.

The two repairs run at different moments, and the difference is deliberate.
Couples are formed once, by the world generator, because pairing every
eligible adult at once is founding-population behaviour and doing it per tick
would bypass the pair-bond intents the couple step exists to resolve. Birth
ticks are backfilled by the generator AND on every tick by the demography
block, because a world generated before the flag was set carries none, and an
agent without one is absent from every candidate query for the rest of the
run.
"""

from __future__ import annotations

import logging
from typing import Any

from epocha.apps.demography.orchestrator import (
    HOURS_PER_YEAR,
    _tick_duration_hours,
    is_demography_enabled,
)

logger = logging.getLogger(__name__)


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


def backfill_birth_ticks(simulation: Any, template: dict | None = None) -> None:
    """Give every living agent a `birth_tick` consistent with its age.

    Derived from the age the generator wrote rather than invented: an agent
    the world describes as forty has to still be forty on the tick this runs,
    or the population's age structure is silently rewritten between
    generation and the first tick.

    **The era's `acceleration` is part of that consistency and was missing.**
    This module was the only one of the subsystem that never named the
    factor, while `age_in_years` -- the single reader of what is written
    here -- multiplies by it. The round trip therefore returned the written
    age times the acceleration, and the invariant stated above was false for
    any era that sets it away from 1.0: the Heligman-Pollard hazard would be
    evaluated at four hundred years for a forty-year-old, and the fertile
    window, which scales the other way, would exclude the entire founding
    population so that nobody ever conceived. Found by round 9 of the
    phase-6 gate, reading the whole branch diff rather than one remediation.
    The inversion is delegated to `age_in_years` rather than rewritten here,
    because rewriting it is exactly how the two clocks drifted apart.

    Agents that already carry a `birth_tick` are left alone -- this repairs
    what is missing and never overwrites a lineage a birth recorded. The dead
    are skipped: their age no longer advances, and rewriting it would edit
    history for no consumer.

    Query shape: one read, and nothing more when it comes back empty -- which
    is every tick of an initialized simulation, since the demography block
    calls this as its per-tick self-repair. When there is something to repair
    it also costs the tick-duration lookup and one `bulk_update`.
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
    from epocha.apps.demography.template_loader import load_template

    acceleration = 1.0
    if template is None:
        # Loaded here only when the caller has none. A named-but-broken era
        # must DEGRADE and not abort -- the same rule the rest of this module
        # follows -- because this function is also the demography block's
        # per-tick self-repair, and a template typo must not stop the whole
        # tick. Falling back to 1.0 reproduces exactly the behaviour that
        # preceded the acceleration fix, which is the least surprising thing
        # to do when the era cannot be read.
        name = simulation.config.get("demography_template", "pre_industrial_christian")
        try:
            template = load_template(name)
        except (FileNotFoundError, ValueError):
            logging.getLogger(__name__).warning(
                "demography: birth-tick backfill could not load template %r; "
                "ages are converted at acceleration 1.0",
                name,
            )
            template = None
    if template is not None:
        acceleration = float(template.get("acceleration", 1.0))
    from epocha.apps.demography.orchestrator import age_in_years

    tick_duration_hours = _tick_duration_hours(simulation)
    ticks_per_year = HOURS_PER_YEAR / max(1e-9, tick_duration_hours)
    tick = simulation.current_tick

    for agent in pending:
        # The inverse of `age_in_years`, which computes
        # `(tick - birth_tick) / ticks_per_year * acceleration`. `birth_tick`
        # is an integer, so the inverse cannot be exact when a year is not a
        # whole number of ticks (a weekly world has 52.14), and rounding to
        # the nearest tick alone put the read-back age BELOW the written one
        # for 40 of the 91 ages 0-90 on a weekly world: its integer part
        # then lost a year, the mortality step's age refresh rewrote the
        # column to that, and a founder written at exactly the era's minimum marriage age failed
        # the marriage-age rule. The reader is therefore the judge: the birth
        # tick moves back one tick while `age_in_years` reads less than the
        # written age -- at most once, since rounding is off by at most half
        # a tick. Flooring the formula instead is not enough on its own:
        # where the inverse is a whole number of ticks the float product can
        # land a hair above it, and the reader then returns 62.999... for 63,
        # measured on a weekly world.
        written = agent.age or 0
        agent.birth_tick = int(round(tick - written * ticks_per_year / max(1e-9, acceleration)))
        while age_in_years(agent, tick, tick_duration_hours, acceleration) < written:
            agent.birth_tick -= 1

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

    Eligibility is `couple.meets_marriage_age`, the one marriage-age rule the
    intent resolver applies too: the era template's own minimum ages, on the
    canonical age derived from `birth_tick`. This function used to apply its
    own copy of the rule, on the `age` column, while the intent path applied
    none -- round 9 of the Plan 4 phase-6 gate. Agents already in an active
    couple are skipped so a repeated call cannot double-pair anyone.

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
        meets_marriage_age,
        stable_matching,
    )
    from epocha.apps.demography.models import Couple
    from epocha.apps.demography.template_loader import load_template

    if template is None:
        config = getattr(simulation, "config", None) or {}
        template = load_template(config.get("demography_template", "pre_industrial_christian"))
    couple_config = template["couple"]
    weights = couple_config["homogamy_weights"]

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
    tick_duration_hours = _tick_duration_hours(simulation)
    eligible = [
        a
        for a in living
        if meets_marriage_age(a, template, simulation.current_tick, tick_duration_hours)
    ]
    men = [a for a in eligible if a.gender == Agent.Gender.MALE]
    women = [a for a in eligible if a.gender == Agent.Gender.FEMALE]
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

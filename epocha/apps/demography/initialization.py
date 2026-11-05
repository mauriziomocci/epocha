"""Demographic initialization of a founding population.

The demography modules assume two things about the population they are handed,
and until this module existed nothing established either.

**Ageing.** `birth_tick` is the project's only source of it. `Agent.age` is
written by the world generator and afterwards only refreshed, as a cache of
completed years, by the mortality step; the fertility module falls back to
that column only when `birth_tick` is NULL -- so a founding population
without birth ticks would have no canonical age to refresh it from.

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
Couples are formed once, by the world generator, because the founding
marriage is founding-population behaviour: it conditions on the ages the
generator wrote and runs on the `initialization` stream of the simulation's
current tick, whereas the marriages of later ticks come from the per-tick
marriage market and the pair-bond intents the couple step exists to resolve.
The founding couples are not a universal pairing of every eligible adult: each
eligible woman is declared married with the probability the era's first-marriage
schedule gives for her age, and the declared women are matched with the men of
their market by the same function the per-tick market uses. Birth ticks are
backfilled by the generator AND on every tick by the demography block, because
a world generated before the flag was set carries none, and an agent without
one is absent from every candidate query for the rest of the run.
"""

from __future__ import annotations

import logging
from typing import Any

from epocha.apps.demography.orchestrator import (
    HOURS_PER_YEAR,
    DemographyTickContext,
    _tick_duration_hours,
    is_demography_enabled,
    stream_for,
)

logger = logging.getLogger(__name__)


def initialize_demography(simulation: Any) -> None:
    """Prepare a founding population for the demography tick.

    Idempotent: an agent that already has a `birth_tick` keeps it, and the
    founding couples are formed once -- a simulation that already has any
    `Couple`, active or dissolved, is not founded again (see
    `form_initial_couples`). "Has this world been initialized" is not a state
    anything records, and the couple table is the evidence that the founding
    already ran, so re-running changes nothing -- except when the first
    founding formed zero couples: the table is then still empty and the next
    call founds again.
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
        # `(tick - birth_tick) * hours * acceleration / 8760`. `birth_tick`
        # is an integer, so the inverse cannot be exact when a year is not a
        # whole number of ticks (a weekly world has 52.14), and rounding to
        # the nearest tick alone put the read-back age BELOW the written one
        # for 40 of the 91 ages 0-90 on a weekly world: its integer part
        # then lost a year, the mortality step's age refresh rewrote the
        # column to that, and a founder written at exactly the era's minimum marriage age failed
        # the marriage-age rule. The reader is therefore the judge: the birth
        # tick moves back one tick while `age_in_years` reads less than the
        # written age -- at most once, since rounding is off by at most half
        # a tick. The inverse below is computed in floats, so the reader
        # stays the judge rather than a rounding direction.
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
    """Build the founding couples from the era's conditioned first-marriage schedule.

    Each eligible founder woman is declared married with probability
    `F*(x)` (`FirstMarriageSchedule.conditional_cdf`, the share of women
    married by age x among those who reach the minimum age single; Kaneko
    2003, eq. 3-4, conditioned as in the couples spec, R4), one draw per
    woman in ascending id from the `initialization` stream of the simulation's
    current tick. The declared women then propose to the eligible men of
    their market, through the same function the per-tick market uses
    (`couple.form_matched_couples`), so founding and later couples come from
    one mechanism. Eligibility is the market's: alive, a man or a woman,
    heterosexual or bisexual, in no active couple, of the era's marriage age
    on the canonical age; a homosexual or asexual founder is not paired
    (gate decision D-29-22). Founders widowed before t = 0 are not modelled:
    the founding population has no marriage history.

    Not every eligible adult is paired, which the previous universal pairing
    did: women still single at their age by the schedule stay single, and the
    surplus on either side of the market stays unpaired.

    Founding runs once: if the simulation already has any `Couple` the
    function returns without drawing. A second founding would draw again for
    the women the first one left single, marrying more of them and reading
    the same `initialization` stream numbers on a different set of women,
    which would break both the schedule's meaning (each woman declared once,
    at the founding age) and the reproducibility from the seed. Any couple,
    including a dissolved one, counts: a world that has run ticks has a
    marriage history, and the founding has none by construction.

    Args:
        simulation: the simulation whose founding population is paired.
        template: the already-loaded era template, when the caller validated
            it -- `initialize_demography` does, so a load failure is handled
            once and by name. Omitted, it is loaded here, which is what the
            tests exercising this function in isolation use.
    """
    from epocha.apps.demography.couple import (
        draw_seekers,
        form_matched_couples,
        read_market_population,
    )
    from epocha.apps.demography.models import Couple
    from epocha.apps.demography.nuptiality import first_marriage_schedule
    from epocha.apps.demography.template_loader import load_template

    if template is None:
        config = getattr(simulation, "config", None) or {}
        template = load_template(config.get("demography_template", "pre_industrial_christian"))
    if Couple.objects.filter(simulation=simulation).exists():
        return
    context = DemographyTickContext(
        simulation, simulation.current_tick, template, _tick_duration_hours(simulation)
    )
    population = read_market_population(context)
    schedule = first_marriage_schedule(template["couple"])
    rng = stream_for(simulation, simulation.current_tick, phase="initialization")
    seekers = draw_seekers(
        population.women, lambda woman: schedule.conditional_cdf(population.ages[woman.id]), rng
    )
    form_matched_couples(context, population, seekers)

    logger.info(
        "demography initialization: formed initial couples for simulation %s",
        simulation.id,
    )

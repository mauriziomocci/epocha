"""Per-tick demography orchestration: the declared step order and its drivers.

This module is what makes the demography subsystem *run*. Five audited modules
-- mortality, fertility, couple, inheritance, migration -- were implemented,
audited and documented as Methods in the whitepaper while the tick loop called
none of them, so every simulation result described a population that did not
die, did not reproduce and did not move. Two of those five expose no per-tick
entry point at all (mortality is four pure functions, fertility declares that
"callers are responsible for persisting the state changes"), and a third calls
itself "THE PLAN 4 DEATH-PATH ENTRY POINT (orchestrator step 2/3)", expecting
steps 1 and 3 to be written here.

Three things live in this module and nowhere else.

**The step order, as data.** `DEMOGRAPHY_STEPS` is a tuple, not a sequence of
calls. The five modules are not commutative and a wrong order produces results
that look plausible -- a population curve that rises or falls credibly -- which
no shallow test tells apart from a correct one. An order written as consecutive
statements can only be checked by re-reading the function and can be broken by
moving a line; as data it is inspectable by a test and permutable by one, which
is what lets each ordering property be proven by mutation.

**The activation predicate.** Demography runs only when the simulation declares
it explicitly. The era template cannot serve as the predicate: seven production
sites already apply `config.get("demography_template", "pre_industrial_christian")`,
so a simulation that declares nothing already behaves like one that declares
the default.

**The RNG discipline.** Every phase that consumes randomness derives exactly
one stream per `(tick, phase)` and threads it through a deterministic iteration
order. Deriving one stream per agent would satisfy the letter of "every call
receives a seeded RNG" and would hand every agent of a phase the same uniform
draw -- because the derivation key is only `(simulation, tick, phase)` -- making
them die in a block at an age threshold rather than independently. This is the
rule `migration.py` already applies to its own per-agent loop.

Ordering rationale is recorded on each entry of `DEMOGRAPHY_STEPS`.
"""

from __future__ import annotations

import random
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from epocha.apps.demography.rng import get_seeded_rng

CONFIG_KEY_ENABLED = "demography_enabled"


@dataclass(frozen=True)
class DemographyStep:
    """One step of the per-tick demography order.

    Attributes:
        index: position in the declared order, 1-based and contiguous.
        name: stable identifier of the step, unique within the order.
        rng_phase: the seeded-RNG phase this step draws from, or None when
            the step consumes no randomness. Must be a phase the seeded-RNG
            helper admits.
        run: the callable driving the step, taking the tick context.
        why_here: the requirement that fixes this step's position. Recorded
            with the data so a reader permuting the order sees what breaks.
    """

    index: int
    name: str
    rng_phase: str | None
    run: Callable[[DemographyTickContext], None]
    why_here: str


@dataclass(frozen=True)
class DemographyTickContext:
    """Everything a step needs, resolved once per tick.

    The era template is loaded once and shared: loading it per step would
    multiply a file read by the number of steps for a value that cannot
    change inside a tick.
    """

    simulation: Any
    tick: int
    template: dict


def is_demography_enabled(simulation: Any) -> bool:
    """Return whether this simulation opted into the demography subsystem.

    Requires the dedicated key to be explicitly true. Absent key, null config
    and an era template without the key all read as disabled, so simulations
    that predate the wiring keep their exact behaviour -- same query count,
    no new events (spec FR-009).
    """
    config = getattr(simulation, "config", None) or {}
    return config.get(CONFIG_KEY_ENABLED) is True


def stream_for(simulation: Any, tick: int, phase: str) -> random.Random:
    """Return the single RNG stream a phase uses for this whole tick.

    Thin pass-through to `demography.rng.get_seeded_rng`, kept here so every
    step reaches randomness the same way and so the one-stream-per-phase rule
    has a single place to be read and violated visibly rather than quietly.
    """
    return get_seeded_rng(simulation, tick, phase=phase)


def _not_yet_wired(context: DemographyTickContext) -> None:
    """Placeholder driver: the order exists before the steps that fill it.

    Replaced step by step as each driver lands. Deliberately a no-op rather
    than a raise: the order has to be inspectable and permutable by tests
    before every driver exists.
    """
    return None


# The declared per-tick order. Each entry records the requirement that fixes
# its position, because an order without its reasons is an order nobody can
# safely change.
DEMOGRAPHY_STEPS: tuple[DemographyStep, ...] = (
    DemographyStep(
        index=1,
        name="separations",
        rng_phase="couple",
        run=_not_yet_wired,
        why_here=(
            "Intents expressed at T-1 take effect at the start of T, before the"
            " conception window: a couple that separates at T does not conceive"
            " at T. One rule for every couple intent, applied symmetrically."
        ),
    ),
    DemographyStep(
        index=2,
        name="couple_formation",
        rng_phase="couple",
        run=_not_yet_wired,
        why_here=(
            "Couples form at T from intents at T-1, and birth probability is"
            " zero without an active couple in three templates of five,"
            " including the default. After fertility, every couple formed at T"
            " could not conceive before T+1 -- a systematic one-tick delay"
            " across all natality. Resolving separations first also leaves the"
            " couple state coherent when formation reads it."
        ),
    ),
    DemographyStep(
        index=3,
        name="mortality",
        rng_phase="mortality",
        run=_not_yet_wired,
        why_here="Whoever dies at T must not conceive at T.",
    ),
    DemographyStep(
        index=4,
        name="succession",
        rng_phase="inheritance",
        run=_not_yet_wired,
        why_here=(
            "An estate settles after the death that caused it, in the same"
            " tick. `dissolve_on_death` is deliberately absent from this order:"
            " `process_inheritance_batch` already calls it last."
        ),
    ),
    DemographyStep(
        index=5,
        name="starvation_counter",
        rng_phase=None,
        run=_not_yet_wired,
        why_here=(
            "The counter increments on the same predicate the flight trigger"
            " reads -- wealth against the zone subsistence threshold -- so it"
            " must read the post-succession wealth, or an heir who rose above"
            " the line this tick is still counted as starving."
        ),
    ),
    DemographyStep(
        index=6,
        name="forced_migration",
        rng_phase="migration",
        run=_not_yet_wired,
        why_here=(
            "Emergency flight reads post-death population and post-succession"
            " wealth. The current tick's zone statistics are not an ordering"
            " property: `process_emergency_flight` builds them itself from the"
            " current tick, so they hold wherever this step sits."
        ),
    ),
    DemographyStep(
        index=7,
        name="fertility",
        rng_phase="fertility",
        run=_not_yet_wired,
        why_here=(
            "After couple formation and after mortality. A newborn does not"
            " take part in this tick's other steps."
        ),
    ),
    DemographyStep(
        index=8,
        name="population_snapshot",
        rng_phase=None,
        run=_not_yet_wired,
        why_here=(
            "The snapshot describes the tick, so it is written once every"
            " mutation of that tick has happened."
        ),
    ),
)

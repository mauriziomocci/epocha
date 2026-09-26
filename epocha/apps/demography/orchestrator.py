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

import logging
import random
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from django.db import transaction
from django.db.models import Q

from epocha.apps.demography.rng import get_seeded_rng

CONFIG_KEY_ENABLED = "demography_enabled"

# The fertile window the fertility module itself documents: it assumes the
# caller has already filtered for living female agents inside `[12, 50]`.
FERTILE_AGE_MIN = 12
FERTILE_AGE_MAX = 50


@dataclass(frozen=True)
class DemographyStep:
    """One step of the per-tick demography order.

    Attributes:
        index: position in the declared order, 1-based and contiguous.
        name: stable identifier of the step, unique within the order.
        rng_phases: the seeded-RNG phases this step derives while running,
            in derivation order; empty when the step consumes no randomness.
            Each must be a phase the seeded-RNG helper admits, and a test
            holds the declaration to the code by recording what each step
            actually derives -- this field had no production consumer, was
            wrong for two steps, and as a single string could not even
            represent fertility, which derives two streams ("fertility" for
            its own draws, "inheritance" for the newborns' attributes).
        run: the callable driving the step, taking the tick context.
        why_here: the requirement that fixes this step's position. Recorded
            with the data so a reader permuting the order sees what breaks.
    """

    index: int
    name: str
    rng_phases: tuple[str, ...]
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
    # Resolved once per tick alongside the template, and for the same reason
    # the template is: it is a per-world constant that cannot change inside a
    # tick, and four steps need it. Left at `None` the accessor falls back to a
    # query, so a context built by hand -- as tests do -- still works.
    tick_duration_hours: float | None = None

    def hours_per_tick(self) -> float:
        """The world's tick duration, resolved at most once per context.

        The phase-6 closure review counted three identical private helpers
        resolving this with a query each, in `orchestrator`, `snapshot` and
        `initialization`, while this container existed precisely to resolve
        per-tick constants once. Two of the three now share this one;
        `initialization.backfill_birth_ticks` keeps its own because it runs
        without a context, and saying so is better than implying three.
        Memoised through `object.__setattr__`
        because the dataclass is frozen and the value is a cache of a
        world-level fact, not part of the context's identity.
        """
        if self.tick_duration_hours is None:
            object.__setattr__(self, "tick_duration_hours", _tick_duration_hours(self.simulation))
        return float(self.tick_duration_hours)


# Hours in a Julian year, the conversion every age and rate in this
# subsystem runs through. Named here rather than repeated as a literal:
# `snapshot.py` and `initialization.py` already name it, and round 9
# counted the same number in four forms across three modules.
HOURS_PER_YEAR = 8760.0


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


def pick_newborn_name(template: dict, gender: str, rng: random.Random) -> str:
    """Draw a given name from the era template's pool for this gender.

    The pool lives in the template and the draw uses the tick's seeded
    stream, because a name generated by the LLM would make the birth
    non-reproducible from the seed (spec FR-001a) -- widening a
    reproducibility limit that the whitepaper scopes to LLM sampling alone.

    The pools are keyed by birth sex, which is what `resolve_birth_attributes`
    can produce. `Agent.Gender` also admits a value outside that pair; a
    newborn cannot currently be assigned it, but the model can hold one, so
    the fallback draws from both pools rather than raising and turning a data
    state into a crash.
    """
    pools = template["names"]
    pool = pools.get(gender)
    if not pool:
        pool = list(pools["male"]) + list(pools["female"])
    return pool[rng.randrange(len(pool))]


def build_newborn(
    context: DemographyTickContext,
    mother: Any,
    father: Any | None,
    rng: random.Random,
    zone_class_mean: float | None = None,
) -> Any:
    """Return the newborn `Agent` for this birth, unsaved.

    Unsaved on purpose: the fertility step creates a tick's newborns in one
    `bulk_create`, and per-birth saves are exactly the per-agent query cost
    the plan forbids. `apply_inheritance_at_birth` has the same no-save
    contract, so the two compose.

    `birth_tick` is set here and is load-bearing well beyond this function:
    it is the project's only source of ageing. `Agent.age` is written once at
    world generation and never advances, and fertility falls back to it only
    when `birth_tick` is NULL -- so a newborn without `birth_tick` would be
    frozen at age zero forever.
    """
    from epocha.apps.agents.models import Agent
    from epocha.apps.demography.inheritance import apply_inheritance_at_birth

    child = Agent(
        simulation=context.simulation,
        name="",  # replaced below: the pool is chosen by the drawn gender
        age=0,
        birth_tick=context.tick,
        parent_agent=mother,
        other_parent_agent=father,
        role="child",
        location=mother.location,
        health=1.0,
    )

    # Inheritance draws the gender, so the name pool can only be chosen after
    # it has run.
    apply_inheritance_at_birth(
        child,
        mother,
        father,
        context.simulation,
        context.tick,
        rng,
        zone_class_mean=zone_class_mean,
    )
    child.name = pick_newborn_name(context.template, child.gender, rng)
    return child


def run_fertility_step(
    context: DemographyTickContext,
    rng: random.Random | None = None,
) -> None:
    """Resolve this tick's births and persist them.

    The fertility module decides whether a birth happens
    (`tick_birth_probability`) and resolves childbirth mortality
    (`resolve_childbirth_event`), and it states that "callers are
    responsible for persisting the state changes". This is that caller.

    Query shape, and the invariant it exists to hold: **resolving one
    candidate costs zero queries, and so does one birth.** The step pays,
    once each: one read of the candidate mothers, one of the living
    population count, one of the active-couple membership, two of the
    simulation-wide outlook terms, and one `in_bulk` of the candidates'
    partners -- which costs nothing at all when none of them is partnered,
    since an empty set of ids issues no query; then up to four reads per
    distinct candidate zone for the zonal Becker inputs and one more for
    that zone's mean class rank. It
    writes, once each and only when there is something to write: a savepoint
    pair around them all, a `bulk_update` and a settlement for the mothers
    who died in childbirth, a `bulk_create` for the newborns and a
    `bulk_create` for their events. Nothing here scales with the living
    population beyond that single read, and nothing scales with the number
    of births.

    Everything above exists to make that true, because
    `tick_birth_probability` and `apply_inheritance_at_birth` fetch whatever
    they are not given, which turns each of those reads into a per-candidate
    or per-birth one. The phase-6 gate measured seven per living fertile
    woman -- 70 at five couples, 105 at ten -- an N+1 against FR-016, and
    three more per birth, which FR-016a forbids by granting births no term of
    their own.

    Building the zone bundle once for the whole loop is sound because the
    loop writes nothing: newborns, dead mothers and events are all persisted
    after it ends, so no candidate sees a population the bundle predates.

    Args:
        context: the tick context.
        rng: the fertility-phase stream. Derived from the context when
            omitted, which is what production does; tests pass a scripted
            stream to steer a probabilistic outcome without reaching into
            this function's internals.
    """
    from epocha.apps.agents.models import Agent
    from epocha.apps.demography.context import load_outlook_terms
    from epocha.apps.demography.couple import active_couple_partners
    from epocha.apps.demography.fertility import (
        build_zone_fertility_context,
        resolve_childbirth_event,
        tick_birth_probability,
    )
    from epocha.apps.demography.inheritance import compute_zone_class_mean
    from epocha.apps.demography.models import DemographyEvent

    if rng is None:
        rng = stream_for(context.simulation, context.tick, phase="fertility")

    step_index = _step_index("fertility")
    tick_duration_hours = context.hours_per_tick()
    acceleration = float(context.template.get("acceleration", 1.0))

    candidates = list(
        Agent.objects.filter(
            _fertile_window_filter(context.tick, tick_duration_hours, acceleration),
            simulation=context.simulation,
            is_alive=True,
            gender=Agent.Gender.FEMALE,
        )
        .select_related("zone", "simulation", "fertility_state")
        .order_by("id")
    )
    if not candidates:
        return

    current_population = Agent.objects.filter(simulation=context.simulation, is_alive=True).count()
    partners = active_couple_partners(context.simulation)
    era_requires_a_couple = bool(
        context.template["fertility"].get("require_couple_for_birth", True)
    )
    if era_requires_a_couple and not partners:
        # Three of the five eras return a birth probability of exactly zero
        # for a mother not in an active couple, so a population with no
        # couple at all cannot conceive until step 2 has resolved enough
        # pair-bond intents. That is correct behaviour and it used to be
        # invisible: a world whose founding couples were never formed simply
        # produced no births, with nothing in any log to explain it. Reported
        # from the membership set this step has already read, so saying it
        # costs no query of its own.
        logging.getLogger(__name__).warning(
            "demography: simulation %s has %d fertile candidates and no active "
            "couple, and era %r requires one for any birth -- no birth is "
            "possible this tick",
            context.simulation.id,
            len(candidates),
            context.simulation.config.get("demography_template", "pre_industrial_christian"),
        )
    # Simulation-wide, so read once here rather than once per zone below.
    outlook_terms = load_outlook_terms(context.simulation)
    zone_contexts: dict[Any, dict] = {}

    # The two remaining per-birth reads, hoisted. Resolving the mother's
    # partner one birth at a time cost a couple lookup plus a foreign-key
    # dereference each, and
    # `apply_inheritance_at_birth` computes the zone's mean class rank in one
    # query of its own -- three per birth, against an FR-016a that grants
    # births no term at all ("one query per birth makes the cost measurement
    # fail"). Both are answered here once: the partners in a single `in_bulk`
    # over the candidates' partner ids, the class mean per distinct candidate
    # zone, which is a zone term and not a birth term.
    partner_objects = Agent.objects.in_bulk(
        {pid for m in candidates if (pid := partners.get(m.id)) is not None}
    )
    zone_class_means: dict[Any, float] = {}

    inheritance_rng = stream_for(context.simulation, context.tick, phase="inheritance")
    newborns: list[Any] = []
    mothers_of_newborns: list[Any] = []
    dead_mothers: list[Any] = []

    for mother in candidates:
        if mother.zone_id not in zone_contexts:
            zone_contexts[mother.zone_id] = build_zone_fertility_context(
                context.simulation, mother.zone, outlook_terms
            )
        probability = tick_birth_probability(
            mother,
            context.template,
            current_population,
            tick_duration_hours,
            acceleration,
            current_tick=context.tick,
            zone_context=zone_contexts[mother.zone_id],
            partnered_agent_ids=partners,
        )
        if rng.random() >= probability:
            continue

        outcome = resolve_childbirth_event(mother, context.template, context.tick, rng)

        if outcome["mother_died"]:
            mother.is_alive = False
            mother.death_tick = context.tick
            mother.death_cause = Agent.DeathCause.CHILDBIRTH
            dead_mothers.append(mother)

        if not outcome["newborn_survived"]:
            continue

        if mother.zone_id not in zone_class_means:
            zone_class_means[mother.zone_id] = compute_zone_class_mean(mother.zone)
        newborns.append(
            build_newborn(
                context,
                mother,
                partner_objects.get(partners.get(mother.id)),
                inheritance_rng,
                zone_class_mean=zone_class_means[mother.zone_id],
            )
        )
        mothers_of_newborns.append(mother)

    if not dead_mothers and not newborns:
        return

    # Up to four writes describing one tick's births: the mothers who died
    # of them, their settlement, the newborn rows and the birth events. One
    # boundary around all four, because any partial application is a state
    # the model forbids -- a newborn no event records, or a mother dead and
    # unsettled -- and because the steps that drive audited modules already
    # get one from those modules.
    with transaction.atomic():
        # The newborns are written FIRST, and the order is load-bearing: a
        # child born of a mother who dies bearing it is her heir, and
        # `process_inheritance_batch` resolves heirs with a query over her
        # living children. Settling before the insert left that child out of
        # its own mother's estate, and out of the caretaker pass, which walks
        # the same `heirs["children"]` -- so the only orphan this path can
        # produce was the only orphan the assignment could never reach, and
        # never would, because the batch runs solely in the tick of the
        # death. Found by the closure review of the phase-6 gate; the
        # succession rule itself was ratified rather than assumed.
        if newborns:
            Agent.objects.bulk_create(newborns)

        if dead_mothers:
            Agent.objects.bulk_update(dead_mothers, ["is_alive", "death_tick", "death_cause"])
            _settle_deaths(context, dead_mothers, step_index=step_index, step_name="fertility")

        if not newborns:
            return

        DemographyEvent.objects.bulk_create(
            [
                DemographyEvent(
                    simulation=context.simulation,
                    tick=context.tick,
                    event_type=DemographyEvent.EventType.BIRTH,
                    primary_agent=newborn,
                    secondary_agent=mother,
                    payload={
                        "step_index": step_index,
                        "step_name": "fertility",
                        "mother_died_in_childbirth": not mother.is_alive,
                    },
                )
                for newborn, mother in zip(newborns, mothers_of_newborns, strict=True)
            ]
        )


def age_in_years(agent: Any, tick: int, tick_duration_hours: float, acceleration: float) -> float:
    """The agent's age, derived from `birth_tick`.

    `birth_tick` is the canonical source and the only one that advances:
    `Agent.age` is written once at world generation and never updated, so
    reading it would freeze every hazard and every eligibility window for
    the whole run. The fallback to that column exists only for agents whose
    `birth_tick` is NULL, a state the initialization is required to leave
    behind.
    """
    if agent.birth_tick is None:
        return float(agent.age or 0)
    ticks_per_year = HOURS_PER_YEAR / max(1e-9, tick_duration_hours)
    return (tick - agent.birth_tick) / max(1e-9, ticks_per_year) * acceleration


def mortality_probability_for(
    agent: Any,
    context: DemographyTickContext,
    tick_duration_hours: float,
) -> float:
    """This tick's death probability for one agent (Heligman-Pollard)."""
    from epocha.apps.demography.mortality import tick_mortality_probability

    acceleration = float(context.template.get("acceleration", 1.0))
    return tick_mortality_probability(
        age_in_years(agent, context.tick, tick_duration_hours, acceleration),
        context.template["mortality"]["heligman_pollard"],
        tick_duration_hours,
        acceleration,
    )


def run_mortality_step(
    context: DemographyTickContext,
    rng: random.Random | None = None,
) -> None:
    """Decide who dies this tick, mark them, and emit the death events.

    This is step 1 of the death path. `mortality.py` exposes four pure
    functions and no per-tick entry point, so evaluating the schedule over
    the living population, persisting the outcome and recording it are all
    new work.

    Marking happens HERE and not in the succession step, deliberately:
    `process_inheritance_batch` documents `is_alive=False` as a load-bearing
    precondition it never verifies, because that is what makes intra-tick
    chaining through a dead intermediate structurally impossible rather than
    merely suppressed.

    Query shape: one read of the living population, one `bulk_update` for the
    dead, one `bulk_create` for the events.
    """
    from epocha.apps.agents.models import Agent
    from epocha.apps.demography.models import DemographyEvent
    from epocha.apps.demography.mortality import sample_death_cause

    if rng is None:
        rng = stream_for(context.simulation, context.tick, phase="mortality")

    step_index = _step_index("mortality")
    tick_duration_hours = context.hours_per_tick()
    acceleration = float(context.template.get("acceleration", 1.0))
    params = context.template["mortality"]["heligman_pollard"]

    living = list(Agent.objects.filter(simulation=context.simulation, is_alive=True).order_by("id"))
    if not living:
        return

    dead: list[Any] = []
    # `Agent.age` is a cache of `birth_tick`, and this is where it is
    # refreshed. `birth_tick` remains the canonical source and the only one
    # that advances by itself, but the column is READ by two paths that this
    # work item made live and that are not ours to rewrite:
    # `annuity_for_agent(agent.age, ...)` inside the third condition of
    # emergency flight, and `child.age >= adulthood_age` in the caretaker
    # pass. Left stale, every agent born in the run carried age 0 for life --
    # the longest working horizon the model admits, and permanent minority.
    # Refreshed here because this step already derives the age of every
    # living agent for the hazard, so the value costs nothing extra; only the
    # rows whose stored value actually moved are written, and they go in one
    # `bulk_update`, so the query count does not scale with the population.
    aged: list[Any] = []
    for agent in living:
        age = age_in_years(agent, context.tick, tick_duration_hours, acceleration)
        stored_age = max(0, int(age))
        if stored_age != agent.age:
            agent.age = stored_age
            aged.append(agent)
        probability = mortality_probability_for(agent, context, tick_duration_hours)
        if rng.random() >= probability:
            continue
        agent.is_alive = False
        agent.death_tick = context.tick
        agent.death_cause = sample_death_cause(age, params, rng)
        dead.append(agent)

    if aged:
        Agent.objects.bulk_update(aged, ["age"])

    if not dead:
        return

    # The marking and the events are one fact, so they commit together or
    # not at all. Split, a failure between them leaves agents dead that no
    # DEATH event describes -- invisible to the crude death rate, to the
    # event log and to succession, which is the second-class death this
    # branch already had to repair once for childbirth. The four audited
    # modules the other steps drive each open their own boundary; this is
    # the same discipline for a step written here.
    with transaction.atomic():
        Agent.objects.bulk_update(dead, ["is_alive", "death_tick", "death_cause"])
        DemographyEvent.objects.bulk_create(
            [
                DemographyEvent(
                    simulation=context.simulation,
                    tick=context.tick,
                    event_type=DemographyEvent.EventType.DEATH,
                    primary_agent=agent,
                    payload={
                        "step_index": step_index,
                        "step_name": "mortality",
                        "death_cause": agent.death_cause,
                    },
                )
                for agent in dead
            ]
        )


def _settle_deaths(
    context: DemographyTickContext,
    deceased: list,
    *,
    step_index: int,
    step_name: str,
) -> None:
    """Emit the death events and settle the estates of a set of deaths.

    Used by any step that kills AFTER the succession step has run -- today
    only the fertility step, when a mother dies in childbirth. Succession is
    the fourth step and filters `death_tick=current tick`, so a death
    produced by the seventh arrives when it has already passed, and on the
    next tick that filter no longer matches: the estate would never be
    distributed, the couple never dissolved -- leaving a widower bound to a
    dead partner and unable to re-pair -- and no DEATH event would exist, so
    the death would never reach the tick's crude death rate.

    Deaths produced BEFORE succession are settled by succession itself, and
    the two paths cannot overlap: the succession step only takes deaths whose
    event carries a step index lower than its own.
    """
    from epocha.apps.demography.inheritance import process_inheritance_batch
    from epocha.apps.demography.models import DemographyEvent

    if not deceased:
        return

    DemographyEvent.objects.bulk_create(
        [
            DemographyEvent(
                simulation=context.simulation,
                tick=context.tick,
                event_type=DemographyEvent.EventType.DEATH,
                primary_agent=agent,
                payload={
                    "step_index": step_index,
                    "step_name": step_name,
                    "death_cause": agent.death_cause,
                },
            )
            for agent in deceased
        ]
    )
    process_inheritance_batch(context.simulation, context.tick, deceased)


def run_succession_step(context: DemographyTickContext) -> None:
    """Settle the estates of the agents who died in this tick.

    Step 2 of the death path is `process_inheritance_batch`, which already
    exists and already calls `dissolve_on_death` last; what was missing is
    the caller that hands it this tick's dead. The batch is a no-op on an
    empty list, but the read is skipped anyway so a tick without deaths costs
    nothing beyond it.

    Only deaths produced EARLIER in this tick are settled here, and the
    filter is the declared order itself: a death event carries the index of
    the step that emitted it, and this step takes only those below its own.
    A step that kills after succession -- fertility does, when a mother dies
    in childbirth -- settles its own dead, and this bound is what keeps the
    two paths from ever settling the same estate twice, whatever the order
    is later changed to.
    """
    from epocha.apps.agents.models import Agent
    from epocha.apps.demography.inheritance import process_inheritance_batch
    from epocha.apps.demography.models import DemographyEvent

    own_index = _step_index("succession")
    settled_elsewhere = {
        event["primary_agent_id"]
        for event in DemographyEvent.objects.filter(
            simulation=context.simulation,
            tick=context.tick,
            event_type=DemographyEvent.EventType.DEATH,
        ).values("primary_agent_id", "payload")
        if (event["payload"] or {}).get("step_index", 0) > own_index
    }

    deceased = list(
        Agent.objects.filter(
            simulation=context.simulation,
            is_alive=False,
            death_tick=context.tick,
        )
        .exclude(id__in=settled_elsewhere)
        .order_by("id")
    )
    if not deceased:
        return

    process_inheritance_batch(context.simulation, context.tick, deceased)


def run_separations_step(context: DemographyTickContext) -> None:
    """Dissolve the couples whose partners asked to separate at T-1.

    First in the declared order, and that is the whole point: an intent
    expressed at T-1 takes effect at the START of T, before the conception
    window, so a couple that separates at T does not conceive at T. The same
    rule governs formations one step later, applied symmetrically -- two
    semantics for the price of one would make the effect of an intent depend
    on its sign.
    """
    from epocha.apps.demography.couple import resolve_separate_intents

    resolve_separate_intents(context.simulation, context.tick)


def run_couple_formation_step(
    context: DemographyTickContext,
    rng: random.Random | None = None,
) -> None:
    """Form the couples whose partners asked to pair-bond at T-1.

    Before fertility, necessarily: birth probability is zero without an
    active couple in three templates of five, including the default, so a
    couple formed at T could not conceive before T+1 if this ran after --
    a systematic one-tick delay across all natality, producing a perfectly
    credible population curve that no shallow test tells apart from the
    correct one.
    """
    from epocha.apps.demography.couple import resolve_pair_bond_intents

    if rng is None:
        rng = stream_for(context.simulation, context.tick, phase="couple")

    # The tick length is the context's, resolved once per tick: the resolver's
    # marriage-age rule needs it, and resolving it here moves the one query
    # the mortality step would otherwise pay, it does not add one.
    resolve_pair_bond_intents(
        context.simulation,
        context.tick,
        rng,
        tick_duration_hours=context.hours_per_tick(),
    )


def run_forced_migration_step(context: DemographyTickContext) -> None:
    """Drive emergency flight, trapped crisis and mass flight for this tick.

    After mortality and succession, so the trigger reads the post-death
    population and the post-succession wealth. The current tick's zone
    statistics are NOT an ordering property: `process_emergency_flight`
    builds them itself from the current tick, so they hold wherever this
    step sits.

    Voluntary Harris-Todaro migration is deliberately absent: it is an input
    to an agent's decision rather than a per-tick mutation, it belongs to the
    decision loop, and wiring it there needs a way to share `zone_stats`
    across parallel tasks that is a design of its own.
    """
    from epocha.apps.demography.migration import process_emergency_flight

    process_emergency_flight(context.simulation, context.tick)


def run_starvation_counter_step(context: DemographyTickContext) -> None:
    """Advance or reset every living agent's consecutive-starvation counter.

    The counter is what makes emergency flight reachable in a live run: the
    trigger compares it against the era template's `flight_trigger_ticks`,
    and until this column existed it took the count as an argument nobody
    could supply.

    The predicate is a HOUSEHOLD one: the household's combined wealth
    against the sum of its members' zone thresholds, with the household
    derived by `demography.context.household_keys` -- the same derivation the snapshot
    reports average household size from, shared rather than copied.

    That is a deliberate divergence from the flight trigger's own first
    condition, which stays individual, and it is written here because the
    previous version of this docstring claimed the two were the same. They
    were, and the consequence was found by the phase-6 closure review:
    `apply_inheritance_at_birth` writes `wealth = 0.0` on every newborn, so
    an individual predicate put every child in the world permanently below
    the line. After `flight_trigger_ticks` -- thirty ticks under the default
    era and FIVE under `sci_fi` -- each of them satisfied conditions one and
    two of emergency flight, and since mass flight fires above 30% of a
    zone's reference population the infant cohort alone was enough to trip
    it. Subsistence is a household question; the counter is what now gates
    the trigger, so a dependent minor in a solvent household never reaches
    it.

    Position in the declared order matters and is recorded there: this runs
    AFTER succession, so an heir who rose above the line thanks to this
    tick's inheritance is counted as recovered rather than as still starving.

    Query shape: one read of the living agents, one read of the active
    couples for the household derivation, up to TWO threshold queries per
    zone -- zones, not agents, and two rather than one because
    `compute_subsistence_threshold` reads the zone economy and then iterates
    the essential good categories -- and one `bulk_update`. None of these
    scales with the number of living agents.

    No transactional boundary, and that is a decision rather than an
    omission: this step performs exactly ONE write, so there is no partial
    state for a boundary to prevent. The two steps that write more than once
    -- mortality and fertility -- open one each, and the four steps that
    drive audited modules get theirs from those modules. A savepoint here
    would buy nothing and would cost two statements in a per-tick budget
    that is measured.
    """
    from epocha.apps.agents.models import Agent
    from epocha.apps.demography.context import compute_subsistence_threshold, household_keys

    living = list(
        Agent.objects.filter(simulation=context.simulation, is_alive=True)
        .select_related("zone")
        .order_by("id")
    )
    if not living:
        return

    tick_duration_hours = context.hours_per_tick()
    acceleration = float(context.template.get("acceleration", 1.0))
    ages = [
        age_in_years(agent, context.tick, tick_duration_hours, acceleration) for agent in living
    ]
    keys = household_keys(
        living,
        ages,
        context.simulation,
        adulthood_age=float(context.template["migration"]["adulthood_age"]),
    )

    thresholds: dict[Any, float] = {}
    changed: list[Any] = []
    for agent in living:
        zone_id = agent.zone_id
        if zone_id not in thresholds:
            thresholds[zone_id] = (
                compute_subsistence_threshold(context.simulation, agent.zone)
                if agent.zone is not None
                else 0.0
            )

    # Aggregated per household, then applied to each of its members: a
    # household feeds itself or it does not, and its dependants starve with
    # it rather than on their own account.
    household_wealth: dict[tuple[int, ...], float] = {}
    household_threshold: dict[tuple[int, ...], float] = {}
    for agent in living:
        key = keys[agent.id]
        household_wealth[key] = household_wealth.get(key, 0.0) + agent.wealth
        household_threshold[key] = household_threshold.get(key, 0.0) + thresholds[agent.zone_id]
    starving = {key for key, total in household_wealth.items() if total < household_threshold[key]}

    for agent in living:
        under_subsistence = keys[agent.id] in starving
        updated = agent.consecutive_ticks_under_subsistence + 1 if under_subsistence else 0
        if updated != agent.consecutive_ticks_under_subsistence:
            agent.consecutive_ticks_under_subsistence = updated
            changed.append(agent)

    if changed:
        Agent.objects.bulk_update(changed, ["consecutive_ticks_under_subsistence"])


def _tick_duration_hours(simulation: Any) -> float:
    world = _world_of(simulation)
    return float(getattr(world, "tick_duration_hours", 24.0) or 24.0) if world else 24.0


def _fertile_window_filter(tick: int, tick_duration_hours: float, acceleration: float) -> Q:
    """Filter the fertile window in SQL, on `birth_tick`.

    Filtering on `Agent.age` would read a column that is written once at
    world generation and never advances: an agent would stay fertile, or
    infertile, for the whole run regardless of how many ticks passed.
    `birth_tick` is the project's only source of ageing, and the window
    inverts cleanly onto it -- age in years is
    `(tick - birth_tick) / ticks_per_year * acceleration`, so the fertile
    ages map to a closed interval of birth ticks -- which keeps the
    selection one set-based query rather than one per living agent.

    Agents with a NULL `birth_tick` are excluded. The fertility module falls
    back to the frozen `age` column for them, and the initialization
    guarantees no living agent is left in that state; admitting them here
    would quietly reintroduce the frozen-age path this project is removing.
    """
    ticks_per_year = HOURS_PER_YEAR / max(1e-9, tick_duration_hours)
    scale = ticks_per_year / max(1e-9, acceleration)
    oldest_fertile_birth_tick = tick - FERTILE_AGE_MAX * scale
    youngest_fertile_birth_tick = tick - FERTILE_AGE_MIN * scale
    return Q(
        birth_tick__gte=oldest_fertile_birth_tick,
        birth_tick__lte=youngest_fertile_birth_tick,
    )


def run_demography_tick(simulation: Any, tick: int) -> None:
    """Run the whole demography block for one tick, or nothing at all.

    The single entry point the tick loop calls. It returns before issuing any
    query when the simulation has not opted in, which is what makes the
    invariance requirement measurable: a simulation without demography runs
    the same number of queries it ran before this subsystem was wired.

    Steps run in the order `DEMOGRAPHY_STEPS` declares, by iterating that
    tuple rather than by calling them one after another in code. The
    difference is not cosmetic: it is what lets a test permute the order and
    watch an ordering property break, which is the only way to tell a correct
    order from a wrong one that produces an equally plausible population.

    Template resolution failures degrade rather than abort the tick, and each
    failure mode is caught by name: a missing template file and a template
    that fails schema validation are different mistakes and are logged as
    such. No blind `except Exception` is introduced here -- the existing one
    in the engine's `avoid_conception` handler swallows exactly the malformed
    template case, and copying it would hide the same class again.
    """
    from epocha.apps.demography.template_loader import load_template

    logger = logging.getLogger(__name__)

    if not is_demography_enabled(simulation):
        return

    config = getattr(simulation, "config", None) or {}
    template_name = config.get("demography_template", "pre_industrial_christian")
    try:
        template = load_template(template_name)
    except FileNotFoundError:
        logger.warning(
            "demography skipped for simulation %s at tick %s: template %r not found",
            simulation.id,
            tick,
            template_name,
        )
        return
    except ValueError:
        logger.warning(
            "demography skipped for simulation %s at tick %s: template %r is invalid",
            simulation.id,
            tick,
            template_name,
        )
        return

    # A world generated before this simulation opted into demography carries
    # agents with a NULL `birth_tick`, because `initialize_demography` has
    # exactly one caller and it is the world generator. That is not cosmetic:
    # `birth_tick` is the only source of ageing and the fertile window is
    # filtered on it in SQL, so those agents are absent from every candidate
    # query -- they never conceive, never age, never die of senescence -- and
    # nothing said so anywhere. The repair is the initialization's own
    # backfill, which is idempotent and returns after a single read when
    # there is nothing pending, so a normally-initialized simulation pays one
    # query per tick for a guarantee that the population the steps see can
    # actually age.
    #
    # Only the backfill is reused here, never `form_initial_couples`: that
    # one pairs every eligible adult at once, which is founding-population
    # behaviour, and running it per tick would bypass the pair-bond intents
    # that step 2 exists to resolve.
    from epocha.apps.demography.initialization import backfill_birth_ticks

    backfill_birth_ticks(simulation, template=template)

    context = DemographyTickContext(
        simulation=simulation,
        tick=tick,
        template=template,
        tick_duration_hours=_tick_duration_hours(simulation),
    )
    for step in DEMOGRAPHY_STEPS:
        step.run(context)


def _step_index(name: str) -> int:
    """Return the declared position of a step, by name.

    Read from `DEMOGRAPHY_STEPS` rather than hardcoded, so a step that moves
    in the declared order carries its new index into the events it emits
    instead of silently reporting the old one.
    """
    for step in DEMOGRAPHY_STEPS:
        if step.name == name:
            return step.index
    raise KeyError(f"unknown demography step {name!r}")


def _world_of(simulation: Any) -> Any | None:
    from epocha.apps.world.models import World

    return World.objects.filter(simulation=simulation).first()


def _run_population_snapshot_step(context: DemographyTickContext) -> None:
    """Write the tick's aggregate demographic state.

    Thin adapter so the snapshot module stays free of the step protocol: the
    aggregation is demography, the step signature is orchestration.
    """
    from epocha.apps.demography.snapshot import write_population_snapshot

    write_population_snapshot(context)


# The declared per-tick order. Each entry records the requirement that fixes
# its position, because an order without its reasons is an order nobody can
# safely change.
DEMOGRAPHY_STEPS: tuple[DemographyStep, ...] = (
    DemographyStep(
        index=1,
        name="separations",
        rng_phases=(),
        run=run_separations_step,
        why_here=(
            "Intents expressed at T-1 take effect at the start of T, before the"
            " conception window: a couple that separates at T does not conceive"
            " at T. One rule for every couple intent, applied symmetrically."
        ),
    ),
    DemographyStep(
        index=2,
        name="couple_formation",
        rng_phases=("couple",),
        run=run_couple_formation_step,
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
        rng_phases=("mortality",),
        run=run_mortality_step,
        why_here="Whoever dies at T must not conceive at T.",
    ),
    DemographyStep(
        index=4,
        name="succession",
        rng_phases=(),
        run=run_succession_step,
        why_here=(
            "An estate settles after the death that caused it, in the same"
            " tick. `dissolve_on_death` is deliberately absent from this order:"
            " `process_inheritance_batch` already calls it last."
        ),
    ),
    DemographyStep(
        index=5,
        name="starvation_counter",
        rng_phases=(),
        run=run_starvation_counter_step,
        why_here=(
            "The counter increments on a HOUSEHOLD predicate -- the household's "
            "combined wealth against the sum of its members' zone thresholds -- "
            "which is deliberately NOT the flight trigger's own individual "
            "condition 1. A dependent minor owns nothing, so an individual "
            "predicate made every child a chronic starveling. It must still"
            " read the post-succession wealth, or an heir who rose above the"
            " line this tick would still be counted as starving."
        ),
    ),
    DemographyStep(
        index=6,
        name="forced_migration",
        rng_phases=("migration",),
        run=run_forced_migration_step,
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
        rng_phases=("fertility", "inheritance"),
        run=run_fertility_step,
        why_here=(
            "After couple formation and after mortality. A newborn does not"
            " take part in this tick's other steps."
        ),
    ),
    DemographyStep(
        index=8,
        name="population_snapshot",
        rng_phases=(),
        run=_run_population_snapshot_step,
        why_here=(
            "The snapshot describes the tick, so it is written once every"
            " mutation of that tick has happened."
        ),
    ),
)

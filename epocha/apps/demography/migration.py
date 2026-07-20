"""Context enrichment, family coordination, and forced flight for agent
migration decisions.

Sources:
- Harris, J.R. & Todaro, M.P. (1970). Migration, Unemployment and
  Development: A Two-Sector Analysis. American Economic Review 60(1),
  126-142. The expected-income model: a rational migrant compares the
  EXPECTED wage at a destination -- the wage weighted by the probability
  of actually finding work there -- against the wage at origin, not the
  raw wage differential alone. `compute_zone_wage` and
  `compute_zone_unemployment` below compute the two zone-level inputs
  this comparison needs (the destination's wage level and its
  employment probability, `1 - unemployment`); the comparison itself is
  `compute_expected_gain`, scoped to a later task (T033).
- Mincer, J. (1978). Family Migration Decisions. Journal of Political
  Economy 86(5), 749-773. Migration is a HOUSEHOLD decision, not an
  individual one -- a "tied mover" may relocate even against their own
  narrow interest because the family's joint gain is positive. Grounds
  `coordinate_family_migration`, scoped to a later task (T035).
- O'Rourke, K.H. (1994). The Economic Impact of the Famine in the Short
  and Long Run. European Review of Economic History 1(1), 3-22. Empirical
  grounding for FORCED, survival-driven migration under acute economic
  collapse (the Irish Famine as the calibration target) -- grounds the
  emergency-flight mechanism, scoped to a later task (T036-T039).
- Simon, H.A. (1955). A Behavioral Model of Rational Choice. Quarterly
  Journal of Economics 69(1), 99-118. Bounded rationality: below a
  survival threshold, an agent does not run a Harris-Todaro cost-benefit
  analysis before fleeing -- deliberation itself is bypassed. Grounds why
  emergency flight short-circuits the normal LLM decision loop, scoped to
  a later task (T037).

This module currently implements the two zone-level labor-market
aggregates (T030/T031), the zone-to-zone travel cost in whole ticks
(T032), and the Harris-Todaro expected-gain comparison over those three
(T033) -- all of user story 4. The family-coordination and
emergency-flight mechanisms above are named here because they are this
module's eventual scope and share its citation set, not because they
exist yet.
"""

from __future__ import annotations

import logging
import math
from typing import TYPE_CHECKING, Any

from django.db.models import Sum

if TYPE_CHECKING:
    # Type-check-only imports: the runtime imports live inside the
    # functions that touch the ORM, to avoid a circular import at module
    # load (this module's established convention, matching couple.py).
    # With `from __future__ import annotations`, annotations are lazy
    # strings, so this block never executes at runtime.
    from epocha.apps.simulation.models import Simulation
    from epocha.apps.world.models import World, Zone

logger = logging.getLogger(__name__)


# Trailing window, in ticks, that `compute_zone_wage` averages
# `EconomicLedger` wage transactions over, and the DEFAULT value of its
# own `window` parameter. Design parameter, not derived from a cited
# source: Harris & Todaro (1970) motivates WHY a wage level drives
# migration, not HOW MANY ticks of history should smooth a noisy per-tick
# wage signal before comparing two zones. 5 ticks is a documented,
# explicitly tunable smoothing choice -- short enough to track a zone's
# current labor-market conditions, long enough to absorb single-tick
# noise from a small agent population (a zone with few workers can see a
# single large wage payment swing a 1-tick average wildly).
ZONE_WAGE_WINDOW_TICKS = 5

# Trailing window, in ticks, that `compute_zone_unemployment` looks back
# over to decide whether a role-holding agent counts as currently
# employed. Deliberately SHORTER than ZONE_WAGE_WINDOW_TICKS (3 vs 5):
# unemployment here means "holds a role but has drawn no wage recently",
# a more volatile, faster-moving signal than a smoothed average wage
# level -- a shorter window tracks it more responsively, at the cost of
# more noise, an explicit and accepted trade-off. Design parameter, not
# derived from a cited source; documented and tunable like the wage
# window above.
ZONE_UNEMPLOYMENT_WINDOW_TICKS = 3


def compute_zone_wage(
    simulation: Simulation, zone: Zone, tick: int, window: int = ZONE_WAGE_WINDOW_TICKS
) -> float:
    """Mean per-capita, per-tick wage income in `zone` over the trailing
    `window` ticks (Harris & Todaro 1970's destination-wage input).

    ZONE ATTRIBUTION (modelling decision, not a mechanical detail):
    `EconomicLedger` carries no zone FK of its own (verified against
    `economy/models.py`). A wage transaction CREDITS the worker who
    earned it -- by this module's own convention (`to_agent`, mirroring
    how `EconomicLedger.to_agent`'s help_text and every wage-crediting
    caller in `economy/engine.py` use it) -- so a wage row is attributed
    to the WORKER's current zone, read via `to_agent__zone`, never
    `from_agent__zone` (the payer's zone, e.g. the employer or the
    treasury, is irrelevant to where the labor market this figure
    describes actually is).

    WINDOW (explicit, pinned by this function's own test suite): the
    CLOSED interval `[tick - window, tick]`, both ends inclusive -- a
    wage row at exactly `tick - window` counts, one at `tick - window - 1`
    does not; a wage row at exactly `tick` counts. For `window=5` this
    spans 6 distinct tick values when every one has data (5 ticks of
    look-back PLUS the current tick), not 5 -- "5-tick window" names the
    look-back span, not a row count. Averaging over ticks in addition to
    dividing by population is what turns a window-cumulative sum into a
    single PER-TICK flow figure: without it, doubling `window` would
    double the returned value for identical underlying wage activity,
    making zones' wage levels incomparable across different window
    sizes and breaking the apples-to-apples comparison T033's
    `compute_expected_gain` needs between `wage_j` (a candidate zone) and
    `wage_current` (the agent's own zone).

    PER CAPITA: divided by the zone's LIVING population
    (`Agent.objects.filter(zone=zone, is_alive=True)`, this codebase's
    dominant population-counting convention). A zone with zero living
    agents returns 0.0 without dividing by zero (FR-028) -- checked
    BEFORE the wage aggregate query runs, so a population-zero zone costs
    exactly 1 query, not 2.

    Query cost contract (bounded, independent of agent or ledger row
    count -- this is read once per reachable zone, per agent, per tick,
    once Plan 4 wires migration context into the decision loop): exactly
    2 queries when population is non-zero (1 population `COUNT`, 1 wage
    `Sum` aggregate), exactly 1 when population is zero (the aggregate is
    skipped entirely). Never a per-agent or per-ledger-row query.

    Args:
        simulation: the Simulation instance whose `EconomicLedger` rows
            are read.
        zone: the Zone to compute the wage for.
        tick: the current simulation tick; the window's upper (inclusive)
            bound.
        window: the trailing look-back span in ticks. Defaults to
            `ZONE_WAGE_WINDOW_TICKS`.

    Returns:
        The mean per-capita, per-tick wage in `zone`, or 0.0 when the
        zone has no living population.
    """
    from epocha.apps.agents.models import Agent
    from epocha.apps.economy.models import EconomicLedger

    population = Agent.objects.filter(zone=zone, is_alive=True).count()
    if population == 0:
        return 0.0

    total_wages = (
        EconomicLedger.objects.filter(
            simulation=simulation,
            transaction_type="wage",
            to_agent__zone=zone,
            tick__gte=tick - window,
            tick__lte=tick,
        ).aggregate(total=Sum("total_amount"))["total"]
        or 0.0
    )

    return total_wages / (population * window)


def compute_zone_unemployment(simulation: Simulation, zone: Zone, tick: int) -> float:
    """Fraction of `zone`'s role-holding living agents who drew no wage
    over the trailing `ZONE_UNEMPLOYMENT_WINDOW_TICKS` ticks (Harris &
    Todaro 1970's destination employment-probability input, as
    `1 - unemployment`).

    OPERATIONAL DEFINITION (several are defensible; this is the one this
    function implements, stated precisely because the paper will be read
    closely on it): the DENOMINATOR is the zone's living population that
    HAS A ROLE (`Agent.role` non-blank -- `Agent.role`'s own help_text,
    "Role in society (blacksmith, priest, farmer...)", frames it as an
    occupation slot, the closest existing field to "in the labor force").
    An agent with no role at all is excluded from BOTH numerator and
    denominator: this function measures joblessness among the nominally
    employed -- a role-holder who is not actually drawing a wage -- not
    raw labor-force non-participation (children, the retired, or anyone
    without an assigned role are simply outside this measure's scope, the
    same way official unemployment statistics exclude those not seeking
    work). The NUMERATOR is the subset of that denominator with NO
    `wage`-type `EconomicLedger` credit (`to_agent__zone`, same
    attribution reasoning as `compute_zone_wage` above) in the CLOSED
    window `[tick - ZONE_UNEMPLOYMENT_WINDOW_TICKS, tick]`.

    Zero role-holders in the zone returns 0.0 without dividing by zero
    (FR-028) -- checked before any wage-lookup query runs.

    Implementation note: the unpaid count is computed as `role_holders.
    exclude(id__in=<wage-paid ids subquery>).count()` -- the "which
    agents were paid" lookup is embedded as a SQL subquery inside the
    single `COUNT` query Django issues for `.exclude(id__in=...)`, not a
    separate round trip to fetch ids into Python first. This keeps the
    whole computation at 2 queries regardless of population or ledger
    size, with never a Python loop over agents.

    Query cost contract (bounded, independent of agent or ledger row
    count): exactly 2 queries when there is at least one role-holder (1
    `COUNT` for the denominator, 1 `COUNT` with an embedded subquery for
    the unpaid numerator), exactly 1 when there are none (the second
    query is skipped entirely).

    Args:
        simulation: the Simulation instance whose `EconomicLedger` rows
            are read.
        zone: the Zone to compute unemployment for.
        tick: the current simulation tick; the window's upper (inclusive)
            bound.

    Returns:
        The fraction (in `[0.0, 1.0]`) of role-holding living agents in
        `zone` who drew no wage in the window, or 0.0 when the zone has
        no role-holding living agents.
    """
    from epocha.apps.agents.models import Agent
    from epocha.apps.economy.models import EconomicLedger

    role_holders = Agent.objects.filter(zone=zone, is_alive=True).exclude(role="")
    total_with_role = role_holders.count()
    if total_with_role == 0:
        return 0.0

    paid_agent_ids = (
        EconomicLedger.objects.filter(
            simulation=simulation,
            transaction_type="wage",
            to_agent__zone=zone,
            tick__gte=tick - ZONE_UNEMPLOYMENT_WINDOW_TICKS,
            tick__lte=tick,
        )
        .values_list("to_agent_id", flat=True)
        .distinct()
    )

    unpaid_count = role_holders.exclude(id__in=paid_agent_ids).count()

    return unpaid_count / total_with_role


# ---------------------------------------------------------------------------
# compute_distance_cost (Plan 3, T032, user story 4)
# ---------------------------------------------------------------------------


def compute_distance_cost(from_zone: Zone, to_zone: Zone, world: World) -> int:
    """Whole-tick travel cost between two zone centers, on foot (design
    spec Sezione 6, "Costo distanza": `ceil(distance_km /
    (walking_speed_km_per_day * tick_duration_days))`).

    CONVERSION CHAIN (unit at every step -- this is a modelling decision,
    not a mechanical detail, and it is the EXACT inverse of the
    conversion `agents/movement.py`'s `calculate_max_distance` already
    establishes and cites as the source of this convention):
    1. `distance_grid = hypot(to_zone.center.x - from_zone.center.x,
       to_zone.center.y - from_zone.center.y)` -- Euclidean distance in
       GRID UNITS between the two zone centers, using plain `.x`/`.y`
       coordinate access, matching `agents/movement.py`'s own
       `execute_movement`. `Zone.center` declares `srid=4326`, but per
       `agents/movement.py`'s own documented warning, these coordinates
       are treated as an ABSTRACT GRID, never true WGS84 lat/lon -- that
       reading is inherited here unchanged, not "fixed".
    2. `distance_km = distance_grid * world.distance_scale / 1000.0` --
       `World.distance_scale` is METERS per grid unit (verified against
       `world/models.py`, default 133.0), so grid units times meters-per-
       unit gives meters, divided by 1000 gives KM. This is the exact
       inverse of `calculate_max_distance`'s own
       `max_distance_grid = max_distance_km * 1000.0 / meters_per_unit`.
       Mirrors that function's defensive fallback for a non-positive
       `distance_scale` (a corrupted World row falls back to the field's
       own default, 133.0, rather than dividing by a non-positive
       number).
    3. `km_per_tick = TRAVEL_SPEEDS["foot"] * (world.tick_duration_hours
       / 24.0)` -- `TRAVEL_SPEEDS["foot"]` (25.0 km/day, Chandler 1966 /
       Braudel 1979, already cited in `agents/movement.py`) times the
       fraction of a day one tick spans (`World.tick_duration_hours` is
       in HOURS, default 24.0 -- dividing by 24.0 is the same
       hours-to-days conversion `calculate_max_distance` uses for
       `max_distance_km`). This function reuses ONLY this arithmetic, not
       `calculate_max_distance` itself, which additionally layers on
       health / civil-stability / repression / terrain factors that
       describe an individual AGENT's journey, not an abstract
       zone-to-zone cost with no traveler yet assigned.
    4. `ticks = math.ceil(distance_km / km_per_tick)` -- a partial day's
       walk still costs a WHOLE tick (design spec's own `ceil`), so a
       same-zone or zero-distance move costs exactly 0 ticks (`ceil(0.0)
       == 0`), never rounded up to 1.

    Query cost: none -- this is a pure function over the three Python
    objects passed in; it issues no database queries of its own (`Zone.
    center` and the `World` fields are read as already-loaded attributes
    on the passed instances).

    Args:
        from_zone: the origin Zone (its `center` is read; otherwise
            unused -- the cost is symmetric in principle, though this
            function always computes it starting from `from_zone`).
        to_zone: the destination Zone.
        world: the World instance supplying `distance_scale` and
            `tick_duration_hours`.

    Returns:
        The whole number of ticks the journey costs, as a plain `int`.
        0 for the same zone or any two zones sharing a center point.
    """
    from epocha.apps.agents.movement import TRAVEL_SPEEDS

    dx = to_zone.center.x - from_zone.center.x
    dy = to_zone.center.y - from_zone.center.y
    distance_grid = math.hypot(dx, dy)

    meters_per_unit = world.distance_scale if world.distance_scale > 0 else 133.0
    distance_km = distance_grid * meters_per_unit / 1000.0

    km_per_tick = TRAVEL_SPEEDS["foot"] * (world.tick_duration_hours / 24.0)

    return math.ceil(distance_km / km_per_tick)


# ---------------------------------------------------------------------------
# compute_expected_gain (Plan 3, T033, user story 4)
# ---------------------------------------------------------------------------


def compute_expected_gain(
    unemployment_j: float, wage_j: float, wage_current: float, distance_cost_j: float
) -> float:
    """The declared operational variant of Harris & Todaro (1970) this
    plan implements (design spec Sezione 6): `E[gain_j] = (1 -
    unemployment_j) * wage_j - wage_current - distance_cost_j`.

    CANONICAL FORM VS. THIS OPERATIONAL VARIANT: Harris & Todaro (1970)
    compares a migrant's EXPECTED urban income, `p * w_urban + (1-p) *
    w_informal` (formal-sector wage weighted by the probability `p` of
    finding formal work, plus the informal-sector wage weighted by the
    complementary probability of not finding it), against the rural
    origin income. This implementation sets the informal-sector wage
    term to ZERO (an agent who fails to find formal work in the
    destination zone is modelled as earning nothing there, not falling
    back to an informal-sector wage), and adds an explicit distance-cost
    term the canonical two-sector model does not carry. Both
    simplifications are DOCUMENTED and TUNABLE, not silent: a per-zone
    informal-sector wage parameter could be added later without changing
    this function's shape, and the design spec itself frames the
    zero-informal-wage choice as a deliberate, revisitable placeholder.

    MANDATORY SCIENTIFIC DISCLOSURE -- a dimensional inconsistency in the
    CONVERGED design, implemented here VERBATIM and NOT silently
    corrected: `(1 - unemployment_j) * wage_j` and `wage_current` are a
    CURRENCY RATE -- the design spec's own worked example reports them in
    "LVR/tick" (docs/superpowers/specs/2026-04-18-demography-design-it.md,
    Sezione 6, the `migration_outlook` block) -- while `distance_cost_j`,
    as `compute_distance_cost` (T032) fixes it, is a raw COUNT OF TICKS,
    not a currency-denominated quantity. Subtracting a tick count from a
    currency rate does not balance dimensionally. The design's own worked
    example does not expose this: it computes the Paris case, whose
    distance cost is 0 ("Costo distanza in tick: Paris 0, Lyon 3,
    Countryside 5", line 811 of the same design spec document) --
    `(1 - 0.08) * 90 - 78 - 0 = 4.8`, matching the spec's own stated
    "+4.8 LVR/tick" -- with the third term simply absent, so the mismatch
    never surfaces. `TestComputeExpectedGain.
    test_pins_declared_not_endorsed_behavior_at_nonzero_distance_cost` in
    this module's test suite exercises the Lyon case instead
    (distance_cost_j=3.0) specifically to make the effect's magnitude
    VISIBLE rather than latent.

    This function implements the design EXACTLY as specified -- this plan
    executes a CONVERGED design and does not reopen it. The phase-6
    adversarial audit (T046) must rule between the two documented
    resolutions (tracked as handoff open question 11, NOT decided or
    implemented here): (a) monetizing the distance cost as forgone
    earnings, `distance_cost_ticks * wage_current`, which restores
    dimensional balance and still reproduces the Paris worked example
    exactly (its own distance cost is 0 either way); or (b) declaring an
    explicit one-currency-unit-per-tick scaling constant, making the unit
    mismatch a documented approximation rather than an oversight. Neither
    is implemented here.

    Query cost: none -- this is pure arithmetic over four float
    arguments; it issues no database queries and accepts no ORM objects.

    Args:
        unemployment_j: destination zone's unemployment fraction (e.g.
            `compute_zone_unemployment`'s return value), in `[0.0, 1.0]`.
        wage_j: destination zone's per-capita, per-tick wage (e.g.
            `compute_zone_wage`'s return value).
        wage_current: the agent's current zone's per-capita, per-tick
            wage, on the same footing as `wage_j`.
        distance_cost_j: the whole-tick travel cost to the destination
            zone (`compute_distance_cost`'s return value, an `int` widened
            to `float` here through ordinary arithmetic).

    Returns:
        The expected gain from moving to the destination zone, in the
        same currency-rate units as `wage_j` / `wage_current` -- positive
        favors moving, negative favors staying, subject to the dimensional
        caveat disclosed above.
    """
    return (1.0 - unemployment_j) * wage_j - wage_current - distance_cost_j


# ---------------------------------------------------------------------------
# build_migration_outlook (Plan 3, T034, user story 4)
# ---------------------------------------------------------------------------


def build_migration_outlook(
    agent: Any, simulation: Simulation, tick: int, zone_stats: dict
) -> dict:
    """Build the per-agent migration_outlook block (design spec Sezione
    6): wage differential, unemployment, distance cost, zone stability,
    and Harris-Todaro expected gain, for every reachable zone.

    `zone_stats` CONTRACT (this function's own contract -- designed here,
    not specified upstream of this task -- see the module test suite's
    own header comment for the canonical shape description):

        {
            "world": <World instance>,
            "government_stability": <float, Government.stability>,
            "zones": {
                zone_id: {
                    "zone": <Zone instance>,
                    "wage": <float, compute_zone_wage's return value>,
                    "unemployment": <float, compute_zone_unemployment's
                        return value>,
                },
                ...
            },
        }

    THE N+1 RISK THIS CONTRACT EXISTS TO CLOSE (load-bearing, this is the
    task's own acceptance criterion): `compute_zone_wage`,
    `compute_zone_unemployment`, and `Government.stability` are ALL
    per-tick CONSTANTS -- the same for every agent asking about the same
    zone in the same tick. Recomputing them inside this function, called
    once per agent per tick once Plan 4 wires migration into the decision
    loop, would multiply their cost by the agent count for no new
    information. `zone_stats` generalizes the task's own "compute zone
    aggregates once per tick" instruction to EVERY such per-tick constant
    this function needs, not only wage/unemployment: `Government` and
    `World` are each exactly one row per simulation (`Government` is a
    `OneToOneField` to `Simulation`, PREFLIGHT point 1), so bundling them
    into the SAME once-per-tick structure is exactly as safe as bundling
    the zone aggregates, and doing so is what lets this function issue
    ZERO database queries of its own, not merely zero zone-specific ones
    -- `agent.zone_id` (the plain FK column, no query) is used to locate
    the agent's own entry inside `zone_stats["zones"]` rather than
    touching the `agent.zone` descriptor, which would trigger one.

    REACHABLE ZONE (a definition this function fixes, not one handed down
    by the design spec): every zone present in `zone_stats["zones"]`
    OTHER than the agent's own current zone (`agent.zone_id`). No
    distance or radius bound is applied. There is no "maximum travel
    range" concept anywhere in the schema, and `compute_distance_cost`
    already assigns a (possibly large) whole-tick cost to every zone
    pair, so no zone is ever truly unreachable -- it may simply be
    expensive. The simplest defensible reading, and the one implemented,
    is "every other zone of the agent's world" (`zone_stats["zones"]` is
    expected to already carry every zone of that world, since the
    caller's once-per-tick precomputation has no cheaper way to build it).

    SIMULATION-WIDE STABILITY (PREFLIGHT point 1, logged as handoff open
    question 12): `Government` carries exactly ONE `stability` scalar per
    `Simulation` -- there is NO per-zone stability anywhere in the current
    schema, even though the design spec's own worked example shows
    stability differing by zone ("Paris crisi (0.3), qui stabile (0.7),
    Countryside stabile (0.6)"). This function reports the SAME
    simulation-wide `zone_stats["government_stability"]` value for EVERY
    reachable zone rather than inventing a per-zone proxy (population
    pressure, local unemployment, or anything else) -- the same
    conflation already exists in merged code at
    `demography/context.py`'s `compute_aggregate_outlook`, inherited here
    knowingly, not "fixed". Adding real per-zone stability would require
    a schema migration this plan's SC-005 forbids; the phase-6 audit
    (T046) must rule on whether the migration model needs a genuine
    per-zone signal.

    WAGE DIFFERENTIAL: `zone_stats["zones"][zone_id]["wage"] -
    zone_stats["zones"][agent.zone_id]["wage"]` -- destination minus the
    agent's CURRENT zone, both already the same per-capita, per-tick
    figure `compute_zone_wage` (T031) returns, keeping the units
    consistent with what `compute_expected_gain` (T033) expects for its
    own `wage_j` / `wage_current` arguments (the raw wage, NOT the
    differential, is what that function takes -- this block reports the
    differential for readability, per the design spec's own
    `migration_outlook` prompt wording, while still passing the RAW
    `wage` values into `compute_expected_gain` internally).

    Query cost contract: exactly 0 database queries. Every input is
    already resolved in `zone_stats` or already loaded on `agent`
    (`agent.zone_id`); `compute_distance_cost` and `compute_expected_gain`
    are both pure functions (see their own docstrings).

    Args:
        agent: the Agent instance considering migration. Only
            `agent.id` and `agent.zone_id` are read (both already-loaded
            plain columns).
        simulation: the Simulation instance (currently unused by this
            function's own body -- accepted for API symmetry with this
            module's other per-agent functions and because a future
            caller may need it; kept honest rather than silently dropped).
        tick: the current simulation tick (currently unused by this
            function's own body, for the same reason as `simulation`
            above -- `zone_stats` already carries every tick-dependent
            value this function reads).
        zone_stats: the once-per-tick precomputed bundle described above.

    Returns:
        `{"current_zone_id": agent.zone_id, "reachable_zones": {zone_id:
        {"wage_differential", "unemployment", "distance_cost",
        "zone_stability", "expected_gain"}, ...}}`.
    """
    world = zone_stats["world"]
    government_stability = zone_stats["government_stability"]
    zones = zone_stats["zones"]

    current_zone = zones[agent.zone_id]["zone"]
    wage_current = zones[agent.zone_id]["wage"]

    reachable_zones: dict[int, dict] = {}
    for zone_id in sorted(zones):
        if zone_id == agent.zone_id:
            continue

        entry = zones[zone_id]
        wage_j = entry["wage"]
        unemployment_j = entry["unemployment"]
        distance_cost_j = compute_distance_cost(current_zone, entry["zone"], world)

        reachable_zones[zone_id] = {
            "wage_differential": wage_j - wage_current,
            "unemployment": unemployment_j,
            "distance_cost": distance_cost_j,
            "zone_stability": government_stability,
            "expected_gain": compute_expected_gain(
                unemployment_j, wage_j, wage_current, distance_cost_j
            ),
        }

    return {"current_zone_id": agent.zone_id, "reachable_zones": reachable_zones}


# ---------------------------------------------------------------------------
# coordinate_family_migration (Plan 3, T035, user story 4). Mincer, J.
# (1978). Family Migration Decisions. Journal of Political Economy 86(5),
# 749-773: migration is a HOUSEHOLD decision -- a "tied mover" (a spouse
# or minor child) relocates along with the decision-maker even though the
# move is not their own choice.
# ---------------------------------------------------------------------------


def coordinate_family_migration(agent: Any, target_zone: Any, tick: int, template: dict) -> list:
    """Move `agent`'s partner and minor children into `target_zone` in
    the same tick as `agent`'s own `move_to` decision, emitting one
    `DemographyEvent` for the whole household (design spec Sezione 6,
    "Coordinamento familiare").

    SCOPE -- WHAT THIS FUNCTION DOES NOT DO: it never touches `agent.zone`
    itself. `agent`'s own zone change is the outcome of whichever
    mechanism processes their `move_to` decision (e.g.
    `agents/movement.py`'s `execute_movement`, which additionally handles
    multi-tick partial movement, arrival scattering, and mood/health
    costs for the DECIDING agent) -- called separately by the orchestrator
    BEFORE or AFTER this function, never by it. This function's sole
    responsibility is the household members who follow, which is why its
    name is "coordinate FAMILY migration", not "migrate agent and
    family": conflating the two would duplicate `execute_movement`'s own
    logic for the primary mover (a DRY violation) while giving the family
    members a DIFFERENT, cruder direct-teleport treatment that the design
    spec's own "nello stesso tick" (same tick) wording requires for them
    specifically -- household members always arrive immediately,
    unlike a decider whose own journey may still be a multi-tick partial
    movement in progress.

    HOUSEHOLD MEMBERSHIP:
    - Partner: `couple.active_couple_for(agent)`'s resolved partner, INCLUDED
      only if alive. `active_couple_for` does not itself filter on the
      partner's own aliveness (the same documented edge case
      `_resolve_spouse_heirs` and `generate_mourning_memories` already
      account for in `inheritance.py`) -- this function applies the
      "only if alive" qualifier itself.
    - Minor children: living agents with `agent` as EITHER parentage FK
      (`parent_agent` or `other_parent_agent`), with
      `age < template["migration"]["adulthood_age"]` (16 for the
      pre-industrial and industrial templates, 18 for modern_democracy
      and sci_fi -- verified against all five era template JSON files).
      ADULT children (`age >= adulthood_age`) are deliberately excluded:
      per the design spec, "I figli adulti decidono indipendentemente"
      (adult children decide independently) -- they are never moved by
      this function and never appear in its return value.

    MINORS ARE NOT CALLED TO THE DECISION LOOP: this function never
    creates a `DecisionLog` row or an additional `DemographyEvent` for
    any household member -- it moves them directly, structurally
    bypassing whatever would otherwise offer them a `move_to` choice.
    Enforcing that minors are never PRESENTED such a choice in the first
    place is Plan 4 orchestrator's responsibility (this function has no
    visibility into the decision loop itself); what this function
    guarantees is the ABSENCE of any decision-loop artifact for them --
    testable and tested as exactly that absence.

    EVENT PAYLOAD (design spec Sezione 6, line 833): ONE
    `DemographyEvent(event_type=MIGRATION, primary_agent=agent,
    tick=tick)` per call (never one per household member), with
    `payload = {"household_members": [...], "from_zone": agent.zone_id,
    "to_zone": target_zone.id, "reason": "voluntary"}`. `from_zone` is
    read as `agent.zone_id` (the already-loaded FK column, no query) --
    the household's shared origin zone, since living together implies
    the same starting zone regardless of whether `agent`'s own move has
    already been applied elsewhere by the time this function runs. When
    the household is empty (no living partner, no minor children), NO
    event is created and an empty list is returned -- mirrors this
    module's established "skip genuinely no-op work" convention (see
    `transfer_loans_as_lender`'s own early return in `inheritance.py`).

    PERSISTENCE: this IS the orchestrating entry point for family
    coordination -- moving agents between zones has no meaning left
    unpersisted, so, following the precedent `process_inheritance_batch`
    set (orchestrating entry points persist; pure resolvers do not), this
    function writes directly via ONE `Agent.objects.bulk_update(...,
    ["zone"])` for every household member, never a per-member `.save()`.

    Query cost contract: up to 5 queries, bounded, independent of
    household size -- (1) `active_couple_for` (the `Couple` lookup), (2)
    fetching the partner's own `Agent` row (skipped when there is no
    active couple), (3) the minor-children fetch (one query, either-FK
    filter, mirrors `_resolve_children_heirs`'s own shape in
    `inheritance.py`), (4) one `bulk_update` for every mover at once
    (skipped when the household is empty), (5) one `DemographyEvent`
    `create` (skipped when the household is empty).

    Args:
        agent: the deciding Agent instance. Must be saved. Its own `zone`
            is read (`.zone_id`, no query) but never written by this
            function.
        target_zone: the destination Zone instance the household moves
            into.
        tick: the current simulation tick.
        template: the era template dict; only
            `template["migration"]["adulthood_age"]` is read.

    Returns:
        The list of household member ids (partner, if any, then minor
        children oldest-first by `birth_tick`/`id`) moved by this call --
        identical to `payload["household_members"]` on the emitted event.
        Empty when there was no partner and no minor child to move.
    """
    from django.db.models import Q

    from epocha.apps.agents.models import Agent
    from epocha.apps.demography.couple import active_couple_for
    from epocha.apps.demography.models import DemographyEvent

    adulthood_age = template["migration"]["adulthood_age"]

    movers: list = []

    couple = active_couple_for(agent)
    if couple is not None:
        partner = couple.agent_b if couple.agent_a_id == agent.id else couple.agent_a
        if partner is not None and partner.is_alive:
            movers.append(partner)

    minor_children = Agent.objects.filter(
        Q(parent_agent=agent) | Q(other_parent_agent=agent),
        is_alive=True,
        age__lt=adulthood_age,
    ).order_by("birth_tick", "id")
    movers.extend(minor_children)

    if not movers:
        return []

    for mover in movers:
        mover.zone = target_zone
    Agent.objects.bulk_update(movers, ["zone"])

    household_member_ids = [mover.id for mover in movers]

    DemographyEvent.objects.create(
        simulation_id=agent.simulation_id,
        tick=tick,
        event_type=DemographyEvent.EventType.MIGRATION,
        primary_agent=agent,
        payload={
            "household_members": household_member_ids,
            "from_zone": agent.zone_id,
            "to_zone": target_zone.id,
            "reason": "voluntary",
        },
    )

    return household_member_ids

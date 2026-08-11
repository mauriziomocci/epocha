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
  `coordinate_family_migration`.
- O'Rourke, K.H. (1994). The Economic Impact of the Famine in the Short
  and Long Run. American Economic Review 84(2), 309-313 (Papers and
  Proceedings). Venue corrected during T043 (whitepaper promotion): this
  docstring previously cited European Review of Economic History 1(1),
  3-22, which cannot be right -- that journal's volume 1 is 1997, three
  years after this paper. The whitepaper's Section 13 bibliography
  carries the corrected venue. Empirical
  grounding for FORCED, survival-driven migration under acute economic
  collapse (the Irish Famine as the calibration target) -- grounds
  `evaluate_emergency_flight` and the mass-flight/trapped-crisis
  mechanisms, scoped to a later task (T038-T039).
- Simon, H.A. (1955). A Behavioral Model of Rational Choice. Quarterly
  Journal of Economics 69(1), 99-118. Bounded rationality: below a
  survival threshold, an agent does not run a Harris-Todaro cost-benefit
  analysis before fleeing -- deliberation itself is bypassed. Grounds why
  `evaluate_emergency_flight` short-circuits the normal LLM decision loop.

This module currently implements the two zone-level labor-market
aggregates (T030/T031), the zone-to-zone travel cost in whole ticks
(T032), the Harris-Todaro expected-gain comparison over those three
(T033), the per-agent migration_outlook context block (T034), family
coordination (T035), and the flight-vs-trapped trigger (T036/T037) --
all of user story 4 plus the trigger half of user story 5. The
mass-flight and trapped-crisis emission mechanisms are named here
because they are this module's eventual scope and share its citation
set, not because they exist yet.
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
#
# WINDOW CONVENTION, ALIGNED WITH compute_zone_wage (fix T046/NEW-5, phase-6
# audit T046 round 2): `compute_zone_unemployment` used to read this
# constant through a CLOSED interval, `[tick - N, tick]`, spanning N + 1
# distinct ticks -- FOUR for N=3, not three, silently contradicting this
# comment's own "3 vs 5" comparison, which is only literally true once
# both windows span exactly the ticks their own constant names. REASONED
# THROUGH, not mechanically copied from fix T046/I-8: unemployment's fraction
# has no divisor that a wrong tick-count could corrupt the way wage's
# per-tick average did (T046/I-8), so this was never an ARITHMETIC bug -- but
# both constants feed the SAME Harris & Todaro (1970) comparison
# (`compute_expected_gain`'s `wage_j` and `unemployment_j`), cite the
# SAME paper, and nothing in the "shorter window, more responsive" trade-
# off this comment states motivates an OPEN/CLOSED difference between
# the two windows specifically -- that divergence was inherited
# incidentally (both were closed intervals before T046/I-8 touched only the
# wage one), not a deliberate scientific choice. `compute_zone_
# unemployment` now reads this constant through the SAME half-open
# convention `(tick - N, tick]` fix T046/I-8 established, so "3 vs 5" is
# accurate as literally the number of ticks each window spans, not merely
# the two constants' own declared values.
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

    WINDOW (explicit, pinned by this function's own test suite; corrected
    under fix T046/I-8): the HALF-OPEN interval `(tick -
    window, tick]` -- a wage row at exactly `tick` counts, one at exactly
    `tick - window` does NOT (it fell inside the OLD closed interval this
    function used before the fix), one at `tick - window - 1` never did.
    For `window=5` this spans EXACTLY 5 distinct tick values (`tick-4`
    through `tick`), matching the divisor below one-for-one -- "a 5-tick
    window" is read here as "the trailing 5 ticks, current tick
    included", the plain-language meaning of the phrase, and the ONE
    reading under which the divisor `window` needs no adjustment of its
    own. PRE-FIX, this function used the CLOSED interval `[tick - window,
    tick]` (6 distinct ticks for `window=5`) while still dividing by
    `window` (5), silently overstating the true per-tick wage by 20% at
    the default window (33% at window=3, 100% at window=1) for any zone
    with wage activity spread across the window -- fixed here by
    narrowing the filter to match the divisor, rather than widening the
    divisor to match the filter, precisely because "N-tick window" reads
    more naturally as an N-tick span than as an (N+1)-tick span plus one.
    Averaging over ticks in addition to dividing by population is what
    turns a window-cumulative sum into a single PER-TICK flow figure:
    without it, doubling `window` would double the returned value for
    identical underlying wage activity, making zones' wage levels
    incomparable across different window sizes and breaking the
    apples-to-apples comparison T033's `compute_expected_gain` needs
    between `wage_j` (a candidate zone) and `wage_current` (the agent's
    own zone).

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
            tick__gt=tick - window,
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
    attribution reasoning as `compute_zone_wage` above) in the HALF-OPEN
    window `(tick - ZONE_UNEMPLOYMENT_WINDOW_TICKS, tick]` -- ALIGNED
    with `compute_zone_wage`'s own convention under fix T046/NEW-5 (phase-6
    audit T046 round 2; reasoning for the alignment lives on
    `ZONE_UNEMPLOYMENT_WINDOW_TICKS`'s own definition, not repeated
    here). For `ZONE_UNEMPLOYMENT_WINDOW_TICKS=3` this spans EXACTLY 3
    distinct tick values (`tick-2` through `tick`), not 4.

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
            tick__gt=tick - ZONE_UNEMPLOYMENT_WINDOW_TICKS,
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


# Hours in a Julian year, the divisor that turns `World.tick_duration_hours`
# into ticks per year. Fixed, not tunable: it is a unit conversion.
HOURS_PER_YEAR = 8760.0

# Sjaastad, L.A. (1962), "The Costs and Returns of Human Migration", Journal
# of Political Economy 70(5, part 2):80-93, uses 10% per annum and declares it
# an assumption at p.92 rather than an estimate, entertaining lower values in
# note 23 (p.90) and much higher ones in note 26 (p.91). Todaro (1969) states
# the present-value decision rule but supplies neither a discount rate nor a
# horizon. TUNABLE, and declared so: nothing in either source fixes it.
SJAASTAD_ANNUAL_DISCOUNT_RATE = 0.10

# The age at which residual working life reaches zero. DERIVED, not chosen:
# Sjaastad's own horizons are 45 remaining years for the 15-19 bracket and 40
# for 20-24 (p.89), and the midpoints of those brackets, 17 and 22, both give
# 62. Reproducing BOTH of his published figures from one constant is what
# makes this a derivation from the source rather than a preference.
WORKING_LIFE_END_AGE = 62


def residual_working_life_years(age: int | float) -> float:
    """Sjaastad's horizon: the working life the agent has left, in years.

    The horizon is DERIVED from age and is not a free parameter -- an older
    agent has fewer periods over which to recover the cost of a move, which
    is the whole content of treating migration as an investment. Past
    `WORKING_LIFE_END_AGE` it is zero and never negative: a negative horizon
    would flip the sign of the annuity below and pay an agent to migrate for
    having grown old.
    """
    return max(0.0, float(WORKING_LIFE_END_AGE) - float(age))


def present_value_annuity_ticks(horizon_ticks: float, rate_per_tick: float) -> float:
    """`a(H, r) = (1 - e^(-rH)) / r`, in TICKS.

    The present value of one unit of income PER TICK received for
    `horizon_ticks` ticks and discounted continuously at `rate_per_tick`.
    Because the result carries the dimension of ticks, multiplying it by a
    money-per-tick flow yields money -- which is the whole point, and what
    the previous form got wrong.

    Verified against the source: at 10% per annum with a tick that IS a year,
    45 and 40 remaining years give 9.889 and 9.817, the two factors Sjaastad
    prints at p.89.

    At `rate_per_tick = 0` the expression is `0/0`; the limit is `H`, since
    an undiscounted unit flow is worth exactly its duration. Returned
    directly rather than left for the caller to discover as a
    ZeroDivisionError.
    """
    if horizon_ticks <= 0.0:
        return 0.0
    if rate_per_tick <= 0.0:
        return float(horizon_ticks)
    return (1.0 - math.exp(-rate_per_tick * horizon_ticks)) / rate_per_tick


def annuity_for_agent(age: int | float, tick_duration_hours: float) -> float:
    """The agent's own present-value factor, in ticks.

    THE CONVERSION MUST GO THROUGH `World.tick_duration_hours` and MUST NOT
    assume a tick is a day: that field is configurable, and a model that
    hardcodes 24 silently misprices every simulation running at any other
    resolution.

        ticks_per_year = 8760 / tick_duration_hours
        r_tick         = r_year / ticks_per_year
        H_tick         = H_years * ticks_per_year
    """
    if tick_duration_hours <= 0.0:
        raise ValueError(f"tick_duration_hours {tick_duration_hours} must be positive")
    ticks_per_year = HOURS_PER_YEAR / float(tick_duration_hours)
    return present_value_annuity_ticks(
        residual_working_life_years(age) * ticks_per_year,
        SJAASTAD_ANNUAL_DISCOUNT_RATE / ticks_per_year,
    )


def compute_expected_gain(
    unemployment_j: float,
    wage_j: float,
    wage_current: float,
    distance_cost_ticks: float,
    annuity_ticks: float,
) -> float:
    """Discounted present value of moving to zone `j` (Todaro 1969; Sjaastad
    1962), in the currency of the wages:

        E[gain_j] = a(H, r) * [ (1 - u_j) * w_j - w_current ]
                    - distance_cost_ticks * w_current

    Every term is money. `a` carries ticks and the wages are money per tick,
    so the first term is money; the second prices the travel time at the wage
    the agent is currently earning, which is Sjaastad's own definition of the
    cost (p.84: outlays plus earnings foregone while travelling and searching,
    partly a function of distance).

    WHAT THIS REPLACED, AND WHY THE SOURCES CHANGED. The previous form was
    `(1 - u_j) * w_j - w_current - distance_cost_j`, which subtracts a COUNT
    OF TICKS from a MONEY-PER-TICK. The design spec's own worked example does
    not expose it, because it computes the destination whose distance cost is
    zero. Monetising the cost alone does not fix it either: that leaves one
    money against two rates.

    Harris & Todaro (1970), AER 60(1):126-142 -- the source this module used
    to cite for the whole comparison -- is a ONE-PERIOD equilibrium equality,
    `W_u * E_u / L_u = W_R`, with no horizon, no discounting and no cost. It
    remains the source of the employment-probability weighting on the
    destination wage and it CANNOT license a horizon. Todaro (1969), AER
    59(1):138-148, states the decision as `V(0) = sum [p(t) Y_u(t) - Y_r(t)]
    e^(-it) - C(0)`: a lump-sum cost subtracted from a DISCOUNTED FLOW, never
    netted against a rate. The correct structure was in the literature the
    module was already citing.

    THE DECLARED CONSEQUENCE, because it is large and it is a loss. At 24-hour
    ticks, a 40-year horizon and 10% per annum, `a` is 3583 ticks, so the
    design's worked example of +4.8 per tick becomes a present value of
    +17,199. The break-even distance cost moves from 4.8 ticks to 220.5,
    against shipped costs of 0, 3 and 5: DISTANCE STOPS BITING, and the
    threshold widens by roughly a factor of forty-five. This is what the cited
    model implies, and the source says so itself -- Sjaastad observes (p.84)
    that marginal costs per mile would have to be implausibly high to
    reconcile the observed distance effect with the present value of the
    differential, "even at very high discount rates". The investment model
    under-predicts the friction of distance, and its own author writes it down.

    DECLARED LIMIT, found by rebuilding this module's own trapped-agent
    fixtures against the new form. Sjaastad's cost has two components,
    out-of-pocket outlays AND earnings foregone, and only the second is
    modelled here, because `compute_distance_cost` returns ticks and nothing
    in the schema prices a journey in currency. The consequence is sharp at
    the bottom: an agent whose current zone has no wage data at all has
    `wage_current = 0`, so travel costs nothing and no destination paying
    anything is ever rejected on distance. That is correct under the
    modelled component -- someone earning nothing forgoes nothing by leaving
    -- and it is wrong under the unmodelled one, which is precisely the
    population for whom an out-of-pocket fare bites hardest. Adding it needs
    a currency-denominated travel price that does not exist yet.

    The informal-sector wage of the canonical Harris-Todaro model stays at
    zero -- an agent who finds no formal work in the destination earns nothing
    there -- a documented, tunable simplification unchanged by this amendment.

    Currency-scale invariance is preserved: `a` is dimensionless in the
    currency, and the cost is priced in it rather than added as a constant.

    Args:
        unemployment_j: destination zone's unemployment fraction, in [0, 1].
        wage_j: destination zone's per-capita, per-tick wage.
        wage_current: the agent's current zone's wage, on the same footing.
        distance_cost_ticks: whole-tick travel cost (`compute_distance_cost`).
        annuity_ticks: the agent's own present-value factor, from
            `annuity_for_agent`. Passed in rather than computed here so the
            function stays pure arithmetic and the caller resolves the agent's
            age and the world's tick duration once.

    Returns:
        The present value of moving, in the wages' currency. Positive favours
        moving.
    """
    flow_advantage = (1.0 - unemployment_j) * wage_j - wage_current
    return annuity_ticks * flow_advantage - distance_cost_ticks * wage_current


# ---------------------------------------------------------------------------
# build_migration_outlook (Plan 3, T034, user story 4)
# ---------------------------------------------------------------------------


def build_migration_outlook(
    agent: Any, simulation: Simulation, tick: int, zone_stats: dict
) -> dict:
    """Build the per-agent migration_outlook block (design spec Sezione
    6): wage differential, unemployment, distance cost and the discounted
    expected gain (Todaro 1969, Sjaastad 1962) for every reachable zone,
    plus the simulation-wide government stability reported once.

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

    SIMULATION-WIDE STABILITY (amendment A10, applied). `Government` carries
    exactly ONE `stability` scalar per `Simulation`; there is no per-zone
    stability anywhere in the schema, even though the design spec's own
    worked example prints three different values for three zones ("Paris
    crisi (0.3), qui stabile (0.7), Countryside stabile (0.6)"). A10 rules
    that the EXAMPLE is what is wrong, not the clause: the field is a
    simulation value. This function therefore reports it ONCE, at outlook
    level, under `government_stability`, and no longer copies it into every
    destination entry.

    Building a genuine per-zone signal was considered and rejected as a
    different piece of work: it means defining what makes a zone unstable,
    with its own source, and propagating it -- a new model, not the
    correction of a defect. The defect being removed here is precise, and it
    is not the absence of a signal: a constant repeated per zone induces a
    language model to believe it is comparing zones on a dimension where they
    are identical. Saying so removes exactly that deception at no cost.
    DECLARED LIMIT: the migration decision cannot discriminate between zones
    on stability.

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
        agent: the Agent instance considering migration. Only `agent.id`,
            `agent.zone_id` and `agent.age` are read (all already-loaded
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
        `{"current_zone_id": agent.zone_id, "government_stability": float,
        "reachable_zones": {zone_id: {"wage_differential", "unemployment",
        "distance_cost", "expected_gain"}, ...}}`.
    """
    world = zone_stats["world"]
    government_stability = zone_stats["government_stability"]
    zones = zone_stats["zones"]

    current_zone = zones[agent.zone_id]["zone"]
    wage_current = zones[agent.zone_id]["wage"]
    # The horizon is the AGENT'S, resolved once per agent rather than per
    # destination: it depends on age alone, and an older agent has fewer
    # periods over which to recover the cost of any move.
    annuity_ticks = annuity_for_agent(agent.age, world.tick_duration_hours)

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
            "expected_gain": compute_expected_gain(
                unemployment_j, wage_j, wage_current, distance_cost_j, annuity_ticks
            ),
        }

    return {
        "current_zone_id": agent.zone_id,
        # A10: reported ONCE, at outlook level, and named for what it is.
        # `Government.stability` is one scalar per simulation, and repeating
        # it inside every destination entry told a language model it was
        # comparing zones on a dimension where they are identical. Removing
        # the per-zone copy removes exactly that deception, at no cost.
        "government_stability": government_stability,
        "reachable_zones": reachable_zones,
    }


# ---------------------------------------------------------------------------
# coordinate_family_migration (Plan 3, T035, user story 4). Mincer, J.
# (1978). Family Migration Decisions. Journal of Political Economy 86(5),
# 749-773: migration is a HOUSEHOLD decision -- a "tied mover" (a spouse
# or minor child) relocates along with the decision-maker even though the
# move is not their own choice.
# ---------------------------------------------------------------------------


def _scatter_location_in_zone(zone: Any, rng: Any | None) -> Any:
    """Return a `Point` for a relocated agent's `location` inside `zone`
    (fix T046/I-12): every mechanism in this module that
    changes an agent's `zone` FK writes `location` alongside it, so the
    two fields never contradict each other the way `agents/movement.py`'s
    `execute_movement` documents them as a matched pair.

    REUSE, NOT REINVENTION: the scatter shape (a uniform offset on each
    axis, bounded by `_ARRIVAL_SCATTER_RANGE`) is `execute_movement`'s
    own arrival-scatter convention, imported directly rather than
    duplicating the magic number -- this codebase already has precedent
    for importing a leading-underscore "private" constant across app
    boundaries when it is the SAME quantity (e.g. `economy/engine.py`
    importing `_ROLE_PRODUCTION` from `template_loader`,
    `world/election.py` importing `_personality_similarity` from
    `agents/affinity`).

    SEEDED, UNLIKE `execute_movement`'S OWN CALL: `execute_movement`
    draws this same offset from the unseeded module-level `random`
    (verified directly in `agents/movement.py`) -- a pre-existing gap in
    that module, out of this module's scope to fix (touching
    `agents/movement.py` is explicitly out of bounds for this fix). This
    function instead draws from the caller-supplied `rng`, obtained via
    `demography.rng.get_seeded_rng(simulation, tick, phase="migration")`,
    so the same `(simulation.seed, simulation.id, tick)` triple
    reproduces the identical scattered coordinate every run -- the
    determinism discipline `inheritance.py`'s own birth pipeline already
    established for this app.

    `rng is None` FALLBACK: `zone.center` exactly, with NO random draw.
    This is the path every caller that cannot supply a properly seeded
    `rng` falls back to (see `coordinate_family_migration`'s own
    docstring for why that caller cannot always derive one). A fixed
    centroid is a strictly better answer than the pre-fix bug (a location
    silently left in the ORIGIN zone, contradicting the new `zone` FK):
    it is deterministic, needs no RNG, and satisfies the zone/location
    consistency invariant fix T046/I-12 exists for, even if every mover
    without an `rng` clusters on the exact same point rather than
    scattering.

    Falls back to `zone.center` (skipping the draw entirely) when
    `zone.boundary` is falsy too, matching `execute_movement`'s own guard
    for a zone with no boundary geometry.

    Args:
        zone: the destination Zone; `.center` and `.boundary` are read.
        rng: a seeded `random.Random`-compatible instance (must expose
            `.uniform(a, b)`), or `None` for the deterministic
            zone-center fallback. Consumes exactly two draws (`.uniform`
            for the x offset, then the y offset) when not `None` and
            `zone.boundary` is truthy; zero otherwise.

    Returns:
        A `django.contrib.gis.geos.Point` inside (or at the center of)
        `zone`.
    """
    from django.contrib.gis.geos import Point

    from epocha.apps.agents.movement import _ARRIVAL_SCATTER_RANGE

    if rng is None or not zone.boundary:
        return zone.center

    cx, cy = zone.center.x, zone.center.y
    return Point(
        cx + rng.uniform(-_ARRIVAL_SCATTER_RANGE, _ARRIVAL_SCATTER_RANGE),
        cy + rng.uniform(-_ARRIVAL_SCATTER_RANGE, _ARRIVAL_SCATTER_RANGE),
    )


def coordinate_family_migration(
    agent: Any,
    target_zone: Any,
    tick: int,
    template: dict,
    reason: str = "voluntary",
    emit_event_even_if_empty: bool = False,
    rng: Any | None = None,
) -> list:
    """Move `agent`'s partner and minor children into `target_zone` in
    the same tick as `agent`'s own `move_to` decision, emitting one
    `DemographyEvent` for the whole household (design spec Sezione 6,
    "Coordinamento familiare").

    ADDITIVE EXTENSION (T038/T039, backward-compatible -- the original
    T035 contract is unchanged for every existing caller): two new
    KEYWORD-ONLY-in-practice parameters, both defaulted to the original
    behavior, let `process_emergency_flight` reuse this function for
    forced flight instead of duplicating it.
    - `reason`: written verbatim into `payload["reason"]`. Defaults to
      `"voluntary"` (the only value T035 ever produced). Emergency flight
      passes `"emergency_flight"` (design spec Sezione 6, "Emergency
      flight", effect 4: `DemographyEvent(event_type="migration",
      payload={"reason": "emergency_flight", ...})` -- note the type is
      still MIGRATION with a `reason`, never a dedicated flight event
      type).
    - `emit_event_even_if_empty`: when `True`, the `DemographyEvent` is
      created even when the household has no partner and no minor child
      (`household_members=[]`). Defaults to `False`, preserving T035's
      original "skip genuinely no-op work" behavior for voluntary moves.
      Emergency flight needs `True`: the design spec requires the flight
      event UNCONDITIONALLY, regardless of whether the fleeing agent has
      any dependents -- a solo agent fleeing alone still must produce the
      event; only the FAMILY-COORDINATION side of this function (moving
      dependents) is naturally a no-op when there are none.
    - `rng` (fix T046/I-12, additive the same way):
      an OPTIONAL seeded `random.Random`-compatible instance, forwarded
      to `_scatter_location_in_zone` for every mover's `location` write.
      Defaults to `None`. `process_emergency_flight` derives ONE
      `demography.rng.get_seeded_rng(simulation, tick, phase="migration")`
      instance per call and threads it through every household this
      function moves that tick, so households processed earlier in the
      SAME tick consume earlier draws from the SAME deterministic stream
      -- consistent with `inheritance.py`'s own "one shared stream per
      call, consumed in a fixed order" discipline, generalized here to
      the whole-tick batch rather than a single birth. `rng` CANNOT
      always be derived internally: doing so needs the full `Simulation`
      instance (for `.seed`), which this function does not receive (only
      `agent.simulation_id`, the bare FK integer, to keep this function's
      query-cost contract at zero for that lookup) -- and this function's
      own existing signature cannot grow a new REQUIRED parameter without
      breaking `test_inheritance.py`'s own direct call, a file this fix
      is not permitted to touch. `rng=None` (the default, exercised by
      every caller that does not pass one, including that call) falls
      back to the deterministic zone-center placement `_scatter_location_
      in_zone` documents for that case -- see that function's own
      docstring for the full account.

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
    "to_zone": target_zone.id, "reason": reason}`. `from_zone` is
    read as `agent.zone_id` (the already-loaded FK column, no query) --
    the household's shared origin zone, since living together implies
    the same starting zone regardless of whether `agent`'s own move has
    already been applied elsewhere by the time this function runs.
    IMPORTANT for callers who also move `agent` itself (like
    `process_emergency_flight` does): call this function BEFORE mutating
    `agent.zone`, or `from_zone` and `to_zone` collapse to the same
    value. When the household is empty (no living partner, no minor
    children) AND `emit_event_even_if_empty` is `False` (the default), NO
    event is created and an empty list is returned -- mirrors this
    module's established "skip genuinely no-op work" convention (see
    `transfer_loans_as_lender`'s own early return in `inheritance.py`).
    When `emit_event_even_if_empty` is `True`, the event is still created
    with `household_members=[]` -- the return value is unaffected either
    way (always the actual list of movers, possibly empty).

    PERSISTENCE: this IS the orchestrating entry point for family
    coordination -- moving agents between zones has no meaning left
    unpersisted, so, following the precedent `process_inheritance_batch`
    set (orchestrating entry points persist; pure resolvers do not), this
    function writes directly via ONE `Agent.objects.bulk_update(...,
    ["zone", "location"])` for every household member, never a
    per-member `.save()`. `location` is written alongside `zone` (fix
    T046/I-12): `agents/movement.py` treats the two as a
    matched pair, and a mover left with a stale `location` from the
    origin zone would contradict their own `zone` FK for any spatial
    consumer -- see `_scatter_location_in_zone`'s own docstring for the
    placement itself.

    Query cost contract: up to 5 queries, bounded, independent of
    household size -- (1) `active_couple_for` (the `Couple` lookup), (2)
    fetching the partner's own `Agent` row (skipped when there is no
    active couple), (3) the minor-children fetch (one query, either-FK
    filter, mirrors `_resolve_children_heirs`'s own shape in
    `inheritance.py`), (4) one `bulk_update` for every mover at once
    (skipped when the household is empty), (5) one `DemographyEvent`
    `create` (skipped when the household is empty). `_scatter_location_
    in_zone` and the `rng` it consumes are pure Python (no ORM access),
    so adding `location` to the write does not change this count.

    Args:
        agent: the deciding Agent instance. Must be saved. Its own `zone`
            is read (`.zone_id`, no query) but never written by this
            function.
        target_zone: the destination Zone instance the household moves
            into.
        tick: the current simulation tick.
        template: the era template dict; only
            `template["migration"]["adulthood_age"]` is read.
        reason: written verbatim into `payload["reason"]`. Defaults to
            `"voluntary"`.
        emit_event_even_if_empty: when `True`, creates the event even for
            an empty household. Defaults to `False`.
        rng: an optional seeded `random.Random`-compatible instance
            forwarded to `_scatter_location_in_zone` for every mover's
            `location`. Defaults to `None` (deterministic zone-center
            fallback). See the ADDITIVE EXTENSION section above.

    Returns:
        The list of household member ids (partner, if any, then minor
        children oldest-first by `birth_tick`/`id`) moved by this call --
        identical to `payload["household_members"]` on the emitted event
        (when one is created). Empty when there was no partner and no
        minor child to move.
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

    if not movers and not emit_event_even_if_empty:
        return []

    if movers:
        for mover in movers:
            mover.zone = target_zone
            mover.location = _scatter_location_in_zone(target_zone, rng)
        Agent.objects.bulk_update(movers, ["zone", "location"])

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
            "reason": reason,
        },
    )

    return household_member_ids


# ---------------------------------------------------------------------------
# evaluate_emergency_flight (Plan 3, T036/T037, user story 5). O'Rourke
# (1994) grounds forced, survival-driven migration; Simon (1955) grounds
# why deliberation is bypassed below the survival threshold -- see both
# citations in full at the top of this module.
# ---------------------------------------------------------------------------

# Emotional weight of the memory a fleeing agent writes about their own
# emergency flight (design spec Sezione 6, "Emergency flight", effect 3).
# Deliberately BELOW inheritance.py's MOURNING_MEMORY_WEIGHT (0.9): losing
# one's home to starvation is severe, but the design places it below
# losing a close relation to death. A documented ordering, not an
# oversight -- see TRAPPED_CRISIS_MEMORY_WEIGHT below for the symmetric
# case that sits ABOVE mourning.
EMERGENCY_FLIGHT_MEMORY_WEIGHT = 0.85

# Emotional weight of the memory propagated to co-zone witnesses of a
# TRAPPED_CRISIS (fix MISS-3, design spec Sezione 6). Deliberately ABOVE
# inheritance.py's MOURNING_MEMORY_WEIGHT (0.9) and above
# EMERGENCY_FLIGHT_MEMORY_WEIGHT itself: witnessing a neighbor trapped by
# starvation with nowhere to go -- an ongoing, unresolved crisis, not a
# single completed event -- is the design's most severe first-hand social
# experience short of one's own death. The complete ordering this module
# and inheritance.py together establish: EMERGENCY_FLIGHT_MEMORY_WEIGHT
# (0.85) < MOURNING_MEMORY_WEIGHT (0.9, inheritance.py) <
# TRAPPED_CRISIS_MEMORY_WEIGHT (0.95) -- pinned by
# test_migration.py's own TestProcessEmergencyFlightMassFlight.
# test_memory_weight_ordering_flight_below_mourning_trapped_above.
TRAPPED_CRISIS_MEMORY_WEIGHT = 0.95

# Strict fraction threshold for MASS_FLIGHT (design spec Sezione 6,
# "Broadcast di mass flight": "Se >30% della popolazione vivente di una
# zona fugge..."). STRICT greater-than, not >=: exactly 30% does not
# qualify. A documented design parameter, not derived from a cited
# empirical source.
MASS_FLIGHT_THRESHOLD_FRACTION = 0.30


def evaluate_emergency_flight(
    agent: Any,
    simulation: Simulation,
    tick: int,
    template: dict,
    zone_stats: dict,
    consecutive_ticks_under_subsistence: int,
) -> Any | None:
    """Return the highest-expected-gain reachable zone if `agent` should
    flee NOW, or `None` (design spec Sezione 6, "Emergency flight").

    THREE SIMULTANEOUS CONDITIONS (AND, not any two of three -- fix I-5
    of the DESIGN SPEC's own numbering, which predates the phase-6 audit
    and is unrelated to the audit's separately-numbered `T046/I-5`, the
    single-parent genetic signal in `inheritance.py`):
    1. `agent.wealth` is BELOW `compute_subsistence_threshold(simulation,
       agent's current zone)` -- starving right now.
    2. `consecutive_ticks_under_subsistence >=
       template["migration"]["flight_trigger_ticks"]` -- starving long
       enough that this is not a single bad tick.
    3. At least one reachable zone offers a POSITIVE
       `compute_expected_gain` -- somewhere to actually go.

    THE DESIGN SPEC'S FIX I-5 IS CONDITION 3 SPECIFICALLY (again, not
    the audit's `T046/I-5`): an agent who satisfies 1 and 2
    but has NOWHERE better to go must NOT fire here. That is the TRAPPED
    case -- a distinct, later mechanism (T038/T039's `TRAPPED_CRISIS`
    emission) exists precisely to make that state observable. If this
    function fired on conditions 1+2 alone, every trapped agent would be
    silently reclassified as a fleeing one, and the trapped-crisis
    phenomenon this design spec names explicitly would never be
    observable at all -- fix I-5 is what keeps the two states distinct.

    SIGNATURE CHANGE -- `consecutive_ticks_under_subsistence` IS AN
    EXPLICIT ARGUMENT (user-approved, 2026-07-20, recorded in the
    handoff's decisions section): this counter does not exist ANYWHERE in
    the current schema. It was verified exhaustively before this
    decision: there is no field for it on `Agent`; there is no per-agent
    wealth HISTORY to derive it from (`Agent.wealth` holds only the
    CURRENT value, not a time series); `PopulationSnapshot` aggregates
    per SIMULATION, not per agent. A cross-tick counter has to persist
    somewhere, and every storage option carried a real cost: adding an
    `Agent` field would break this plan's SC-005 zero-migration contract
    (enforced by T042); stashing it inside `Agent.conditions` or
    `Agent.personality` (both JSONField blobs already used for OTHER
    purposes -- diseases/disabilities and Big Five traits respectively)
    would be a JSON-blob-where-relational-serves anti-pattern, encoding a
    numeric counter as an untyped nested value inside a field with an
    unrelated existing contract. The user's resolution: PASS IT IN. This
    function never reads it off `agent` and never derives it from
    anything else in the arguments -- it trusts the caller entirely.
    PLAN 4 OWNS creating the actual storage (a new mechanism, likely a
    per-agent counter table or cache, not decided here) and feeding this
    argument every tick. Until Plan 4 does that, emergency flight CANNOT
    fire in a live run -- a direct, accepted consequence, consistent with
    demography not being wired into the tick loop at all yet (verified:
    `simulation/engine.py` is untouched by this entire plan).

    REUSE, NOT REIMPLEMENTATION: condition 1 reuses
    `compute_subsistence_threshold` (`demography/context.py`) exactly as
    the task requires; condition 3 reuses `build_migration_outlook`
    wholesale (T034) rather than recomputing per-zone expected gains
    separately -- `build_migration_outlook` already turns `zone_stats`
    into exactly the `{"expected_gain": ...}` values this function needs,
    at zero extra database queries (T034's own proven contract), even
    though it also computes wage_differential / distance_cost /
    zone_stability values this function does not itself read. Recomputing
    that arithmetic separately here, just to avoid the unused fields,
    would be the DRY violation this module's Reuse-Before-Reinventing
    discipline exists to prevent.

    TARGET SELECTION AND TIE-BREAK: among reachable zones with a positive
    expected gain, the one with the STRICTLY HIGHEST `expected_gain` is
    returned. Ties break by zone id ASCENDING (this module's established
    convention, matching `inheritance.py`'s sibling/heir tiebreaks) --
    reachable-zone entries are explicitly sorted by id before the `max`
    scan, so the winner does not depend on `dict` iteration order being
    preserved by whatever built `zone_stats["zones"]`.

    SHORT-CIRCUIT ORDER: conditions are checked 1, then 2, then 3, each
    returning `None` immediately on failure -- condition 3's
    `build_migration_outlook` call (the only potentially non-trivial
    Python work here, though still zero queries) only runs when 1 and 2
    already hold.

    Query cost contract: bounded, independent of population or zone
    count -- `compute_subsistence_threshold`'s own cost (up to 2: one
    `ZoneEconomy` lookup, one `GoodCategory` fetch; 1 if `ZoneEconomy`
    does not exist for the zone, via its own documented early return)
    PLUS zero further queries when condition 3 is reached
    (`build_migration_outlook` is a proven zero-query call, T034). Never
    a zone-aggregate query of its own -- exactly the same discipline
    `build_migration_outlook` established, extended here.

    Args:
        agent: the Agent instance being evaluated. Only `agent.wealth`
            and `agent.zone_id` (the already-loaded FK column) are read.
        simulation: the Simulation instance, passed through to
            `compute_subsistence_threshold` and `build_migration_outlook`.
        tick: the current simulation tick, passed through to
            `build_migration_outlook`.
        template: the era template dict;
            `template["migration"]["flight_trigger_ticks"]` is read (30
            for the pre-industrial templates, 20 industrial, 10
            modern_democracy, 5 sci_fi -- verified against all five
            template JSON files; NEVER hardcoded here).
        zone_stats: the same once-per-tick precomputed bundle
            `build_migration_outlook` (T034) defines and consumes.
        consecutive_ticks_under_subsistence: EXPLICIT argument, see the
            SIGNATURE CHANGE section above. An `int` (or any value
            comparable to `template["migration"]["flight_trigger_ticks"]`
            via `>=`).

    Returns:
        The target Zone with the highest positive expected gain, or
        `None` when any of the three conditions fails.
    """
    _, target_zone = _resolve_flight_decision(
        agent, simulation, tick, template, zone_stats, consecutive_ticks_under_subsistence
    )
    return target_zone


def _resolve_flight_decision(
    agent: Any,
    simulation: Simulation,
    tick: int,
    template: dict,
    zone_stats: dict,
    consecutive_ticks_under_subsistence: int,
) -> tuple[bool, Any | None]:
    """Shared decision core factored out of `evaluate_emergency_flight`
    (T036/T037) so `process_emergency_flight` (T039) can distinguish
    "not starving long enough" from "starving long enough but trapped"
    WITHOUT re-deriving the three conditions and WITHOUT a second,
    redundant `compute_subsistence_threshold` query per agent (preflight
    point 2 and point 6, respectively) -- see PREFLIGHT DECISIONS in
    `process_emergency_flight`'s own docstring for the full account of
    why this split exists and why it does not change
    `evaluate_emergency_flight`'s own already-committed public contract
    (same signature, same `Zone | None` return; this function is purely
    an internal implementation detail, never imported by test code
    except through the two public functions that wrap it).

    CACHED SUBSISTENCE THRESHOLD (optional, backward-compatible):
    `zone_stats["zones"][zone_id]` may carry an OPTIONAL
    `"subsistence_threshold"` key (a float, T039's own addition to the
    `zone_stats` contract T034 defined). When present, it is used
    directly, skipping `compute_subsistence_threshold`'s own query cost
    entirely -- `process_emergency_flight` computes this ONCE PER ZONE
    before its per-agent loop, since the threshold depends only on the
    zone, never on the individual agent, and reusing it across every
    agent in that zone is exactly the same "compute once, never per
    agent" discipline `zone_stats` already applies to wage/unemployment.
    When absent (as in every T036/T037 test, which builds `zone_stats`
    without this key), this function falls back to calling
    `compute_subsistence_threshold` directly -- `evaluate_emergency_flight`
    called standalone, outside `process_emergency_flight`'s batch context,
    behaves EXACTLY as it did before this key existed.

    Returns:
        `(meets_preconditions, target_zone)`: `meets_preconditions` is
        `True` iff conditions 1 AND 2 both hold (starving, long enough),
        regardless of condition 3; `target_zone` is the resolved flight
        target (or `None`) exactly as `evaluate_emergency_flight`
        documents. The trapped case is precisely `meets_preconditions is
        True and target_zone is None`.
    """
    from epocha.apps.demography.context import compute_subsistence_threshold

    zone_entry = zone_stats["zones"][agent.zone_id]
    current_zone = zone_entry["zone"]
    subsistence_threshold = zone_entry.get("subsistence_threshold")
    if subsistence_threshold is None:
        subsistence_threshold = compute_subsistence_threshold(simulation, current_zone)

    if agent.wealth >= subsistence_threshold:
        return False, None

    flight_trigger_ticks = template["migration"]["flight_trigger_ticks"]
    if consecutive_ticks_under_subsistence < flight_trigger_ticks:
        return False, None

    outlook = build_migration_outlook(agent, simulation, tick, zone_stats)
    reachable_zones = outlook["reachable_zones"]
    if not reachable_zones:
        return True, None

    ordered_entries = sorted(reachable_zones.items(), key=lambda item: item[0])
    best_zone_id, best_entry = max(ordered_entries, key=lambda item: item[1]["expected_gain"])

    if best_entry["expected_gain"] <= 0.0:
        return True, None

    return True, zone_stats["zones"][best_zone_id]["zone"]


# ---------------------------------------------------------------------------
# process_emergency_flight (Plan 3, T038/T039, user story 5 closing
# task). Design spec Sezione 6, "Emergency flight" and "Broadcast di mass
# flight". This is the Plan 4 orchestrator step 5 entry point.
# ---------------------------------------------------------------------------


def process_emergency_flight(
    simulation: Simulation,
    tick: int,
    consecutive_ticks_under_subsistence_by_agent_id: dict[int, int] | None = None,
) -> None:
    """Drive `evaluate_emergency_flight` over every living, zoned agent
    in `simulation`: execute forced flight via `coordinate_family_
    migration`, emit `TRAPPED_CRISIS` with its MISS-3 co-zone memory
    propagation, and emit `MASS_FLIGHT` above the 30% threshold.

    PRECONDITION-COUNTER PARAMETER (user-approved, 2026-07-20, same
    resolution as `evaluate_emergency_flight`'s own SIGNATURE CHANGE,
    applied here because the problem resurfaces identically): T039's
    task text gives the signature `process_emergency_flight(simulation,
    tick)`, with no counter, no template, no zone_stats -- but this
    function must drive `evaluate_emergency_flight`, which REQUIRES
    `consecutive_ticks_under_subsistence` as an explicit argument (the
    same user-approved change already implemented in T036/T037, for the
    same reason: the counter exists nowhere in the schema). Resolved the
    SAME way and no other:
    `consecutive_ticks_under_subsistence_by_agent_id`, a mapping keyed by
    `Agent.id`, defaults to `None` (treated as `{}`). An agent ABSENT
    from the mapping is treated as ZERO consecutive ticks under
    subsistence -- below any real template's `flight_trigger_ticks` (the
    minimum across all five era templates is 5, sci_fi) -- and therefore
    CANNOT flee or become trapped. With an empty mapping (the default),
    this function is a WELL-DEFINED NO-OP: every agent evaluates to
    "does not meet preconditions", producing zero events. PLAN 4 OWNS
    building this mapping from whatever storage it creates for the
    counter (not decided here, not this plan's job) and feeding it every
    tick; until Plan 4 does that, emergency flight cannot fire in a live
    run, consistent with demography not being wired into the tick loop
    yet (`simulation/engine.py` untouched by this entire plan).

    PER-AGENT STEPS, in order, over every living agent in `simulation`'s
    world, `id` ascending (deterministic, this module's convention):
    1. Resolve `(meets_preconditions, target_zone)` via the SAME private
       `_resolve_flight_decision` helper `evaluate_emergency_flight`
       delegates to -- NOT by calling `evaluate_emergency_flight` and
       separately re-deriving "starving long enough" a second time, which
       would COST A SECOND `compute_subsistence_threshold` query per
       agent for no new information (see PREFLIGHT DECISIONS point 2
       resolution below).
    2. `target_zone is not None` -> FLEE: `coordinate_family_migration`
       moves the household (called BEFORE mutating `agent.zone`, so its
       own `payload["from_zone"]` reads correctly -- see that function's
       own docstring note), `reason="emergency_flight"`,
       `emit_event_even_if_empty=True` (the design requires the flight
       event even for a solo agent with no dependents), `rng=rng` (fix
       T046/I-12 -- see below). `agent.zone` AND `agent.location` (fix T046/I-12:
       this decider bypasses `agents/movement.py`'s `execute_movement`
       entirely -- nothing else in this call graph would otherwise ever
       write their `location`) are then set in memory, deferred to ONE
       batched `bulk_update` at the end covering every fleeing agent this
       tick. A `Memory` at `EMERGENCY_FLIGHT_MEMORY_WEIGHT` (0.85),
       `source_type=DIRECT`, `origin_agent=agent` (self-referential: this
       is the fleeing agent's own first-hand experience) is queued.
    3. `meets_preconditions and target_zone is None` -> TRAPPED: a
       `TRAPPED_CRISIS` event is queued (`payload={"zone": agent.zone_id,
       "consecutive_under_subsistence": <the counter value used>}`, per
       the design spec's own payload schema table). The agent is
       recorded for the batched co-zone witness pass below -- NEVER
       relocated.
    4. Neither -> no-op for this agent.

    Household members (partner, minor children) moved by step 2 for an
    EARLIER agent this tick are recorded and SKIPPED in their own turn
    later in the same loop, rather than re-evaluated: by the time the
    outer loop would reach them, their in-memory `Agent` instance (a
    SEPARATE Python object fetched by this function's own agents query,
    distinct from the one `coordinate_family_migration` fetched
    internally) would still show their OLD `zone_id` -- evaluating
    "starving in the old zone" after they have ALREADY been moved to a
    (by construction, better) new one would be evaluating a state that no
    longer holds, a determinism/correctness hazard, not merely a stylistic
    one. Skipping them is cheap (a Python `set` membership check, no
    query) and avoids it entirely.

    MISS-3 CO-ZONE PROPAGATION, BATCHED (not per trapped agent, and --
    fix T046/M-3 -- NOT per (trapped agent, witness) PAIR
    either): after the main loop, ONE query fetches every living agent
    across EVERY zone that has at least one trapped agent this tick
    (`zone_id__in={trapped zones}`), grouped in Python by zone -- so two
    trapped agents sharing a zone reuse the SAME fetched witness list
    instead of querying it twice.

    NO EXCLUSION (fix T046/NEW-4, round 2 -- corrects an
    over-widened exclusion the T046/M-3 row-volume fix introduced): EVERY
    living agent in the zone receives this memory, trapped agents
    included. FR-026 (spec.md:189) and acceptance scenario 3
    (spec.md:133) both state the requirement in the same words, "tutti
    gli agenti co-zone" -- ALL co-zone agents, with no carve-out --
    which is unambiguous where the design spec's own rationale sentence
    (quoted in the T046/M-3 fix that preceded this one: "Altri agenti
    testimoni..." / "OTHER witnessing agents...") was not. The earlier
    reading -- that a trapped agent is living the crisis rather than
    witnessing it, so should be excluded -- was flagged in this
    docstring as an interpretive choice, not an unambiguous fact, and
    the requirements text resolves that ambiguity: no exclusion, self or
    otherwise. A SOLE trapped agent, alone in their zone, therefore
    receives a self-referential memory (their own zone's `origin_agent`
    representative is themselves) -- this is the correct, spec-mandated
    outcome, not a residual bug.

    ROW VOLUME (fix T046/M-3): PRE-FIX, this pass created ONE `Memory` per
    (trapped agent, witness) PAIR -- N trapped agents among M living
    agents in a zone produced N * (M - N) rows. Starvation is zone-wide,
    so in the module's own calibration scenario (O'Rourke 1994, the
    Irish Famine) N approaches the templates' `max_population` (500)
    right alongside M, giving roughly 500 * 499 ~= 250,000 rows IN ONE
    TICK -- the docstring's OLD query-budget claim was true of query
    COUNT (still exactly 1 witness-fetch query, unaffected by this fix)
    and false of ROW VOLUME, which is what would actually exhaust the
    database. Fixed by aggregating: ONE memory per WITNESS PER ZONE
    (never per trapped agent), grouping `trapped_agents` by `zone_id` in
    the SAME `id`-ascending order the main loop above already produced
    (no bare `set` iteration -- the per-zone trapped-id list is a plain,
    already-ordered `list`), so the row count for a zone scales with its
    POPULATION, never with how many of its agents happen to be trapped
    this tick. Content and `origin_agent` are computed ONCE per zone
    (content mentions the zone name and the trapped COUNT, not every
    victim's name -- naming all N would reintroduce an O(N) content
    string per row, and MISS-3's own rationale is that a witness should
    learn "this zone is a starvation crisis", not receive a per-victim
    biography); `origin_agent` is the id-ascending FIRST trapped agent in
    that zone this tick, a deterministic representative for the field's
    own "dedup and traceability" purpose (`Memory.origin_agent`'s own
    help_text), not an implied claim that they alone caused the crisis.
    INFORMATION LOST relative to the pre-fix shape: a witness in a zone
    with several trapped agents no longer receives one SEPARATE memory
    per victim naming that specific individual -- only one aggregate
    memory about the zone's crisis, with `origin_agent` pointing at a
    single representative victim rather than all of them. Any consumer
    needing the COMPLETE per-victim record (not per-witness belief) still
    has it: every trapped agent still gets their own `TRAPPED_CRISIS`
    `DemographyEvent` (`primary_agent=<that agent>`), UNCHANGED by this
    fix and still O(N), since the event log -- unlike the witness memory
    fan-out -- was never the quadratic term. Each witness memory:
    `TRAPPED_CRISIS_MEMORY_WEIGHT` (0.95), `source_type=PUBLIC`,
    `origin_agent=<the zone's id-ascending first trapped agent>`.

    MASS-FLIGHT DENOMINATOR AND WINDOW (pinned precisely, since an
    ambiguous denominator is not reproducible; denominator corrected
    under fix T046/I-11, WINDOW SPAN corrected under fix T046/NEW-2, both phase-6
    audit T046): the numerator is every DISTINCT agent who fled that zone
    -- HISTORICAL flights already persisted by EARLIER calls to this
    function (`DemographyEvent.payload__reason="emergency_flight"`,
    `tick` in the OPEN-CLOSED window `(tick - flight_trigger_ticks,
    tick)`, fetched with ONE query) PLUS agents fleeing in THIS call (at
    exactly `tick`) -- combined, this spans EXACTLY `flight_trigger_ticks`
    distinct tick values, `(window_start, tick]`, matching the reading
    fix T046/I-8 already established for "an N-tick window" (the trailing N
    ticks, current tick included) -- NOT `flight_trigger_ticks + 1`
    ticks, which is what the historical query's PRE-FIX `tick__gte=
    window_start` bound produced once combined with this tick's own
    separately-added departures. A flight persisted at EXACTLY
    `tick - flight_trigger_ticks` (`== window_start`) is one tick outside
    any honest `flight_trigger_ticks`-tick window and must NOT count --
    pinned by `TestProcessEmergencyFlightMassFlight.
    test_flight_exactly_at_window_start_tick_does_not_count_fix_new2`.

    The DENOMINATOR is each zone's living population AS IT STOOD AT
    WINDOW START (`tick - flight_trigger_ticks`), not its CURRENT living
    population -- a point-in-time denominator paired with a WINDOWED
    numerator is not an apples-to-apples fraction: an agent who fled on
    an earlier tick stays in the numerator (the window still covers that
    tick) but has already left the zone's current population, so a
    current-population denominator double-penalizes the same departure --
    once by counting it in the numerator, again by shrinking the
    denominator it would otherwise still be part of. Left uncorrected,
    the reported fraction climbs over time at a CONSTANT departure rate
    and can exceed 1.0, purely from this arithmetic mismatch, not from
    any acceleration in actual flight.

    RECONSTRUCTION (honest, not exact -- its own two limits are stated
    below): population-at-window-start = the zone's CURRENT living
    population, captured ONCE via a single aggregate query at the START
    of this call BEFORE any of this tick's own flights execute (the
    `baseline_population` local) PLUS every agent HISTORICALLY known to
    have fled that zone during the window (the historical half of the
    numerator above, captured BEFORE this tick's own new flights are
    added into the same `fled_agent_ids_by_zone` structure -- an agent
    fleeing IN this tick is still present in `baseline_population`, so
    counting them a second time here would double them). This recovers
    the population as it stood at window start under the assumption that
    every agent who has since left did so via a recorded emergency
    flight FROM this zone, which has two known limits, both accepted
    rather than papered over:
    - AGENTS WHO DIED in the zone during the window are not part of
      `baseline_population` (they are no longer `is_alive`) and never
      appear in `fled_agent_ids_by_zone` (death is not a flight) -- the
      reconstruction UNDERSTATES population-at-window-start by exactly
      that count, inflating the fraction slightly in a zone with
      concurrent mortality.
    - AGENTS WHO ARRIVED into the zone during the window (via any kind of
      migration) ARE part of `baseline_population` despite not having
      been present at window start -- the reconstruction OVERSTATES
      population-at-window-start by exactly that count, deflating the
      fraction slightly in a zone receiving migrants. Voluntary
      out-migration (as opposed to emergency flight) during the window is
      symmetrically NOT added back, for the same reason: this module
      tracks only `payload__reason="emergency_flight"` events, matching
      the numerator's own scope; Plan 4's orchestrator does not exist yet
      (`simulation/engine.py` untouched), so no voluntary-migration
      traffic can occur in a live run until it does.

    When `len(fled) / population_at_window_start >
    MASS_FLIGHT_THRESHOLD_FRACTION` (STRICT, 0.30), a `MASS_FLIGHT` event
    is queued with `payload={"from_zone":
    zone.id, "agents": sorted(fled), "trigger_ticks":
    flight_trigger_ticks}` (the exact payload schema the design's own
    table specifies). Zones iterated `id` ascending for deterministic
    event order. NOT DEDUPLICATED ACROSS TICKS: this function holds no
    state between calls (decision D3), so if the >30% condition still
    holds on a LATER tick (no new flights needed -- the historical window
    alone can keep it true), it is reported AGAIN. Flagged for the
    phase-6 audit if event-ledger noise becomes a concern; not resolved
    here because doing so would require persisting an "already reported"
    flag this plan does not introduce.

    RNG STREAM (fix T046/I-12): ONE
    `demography.rng.get_seeded_rng(simulation, tick, phase="migration")`
    instance is drawn at the top of the transaction block below and
    threaded through the ENTIRE per-agent loop -- every fleeing agent's
    own `location` scatter and every `coordinate_family_migration` call
    for that agent's household consume draws from this SAME stream, in
    the loop's own `id`-ascending order, rather than each call deriving
    its own fresh (and, for two agents fleeing the same tick, IDENTICALLY
    seeded, since the derivation key is only `(simulation, tick, phase)`)
    instance. This mirrors `inheritance.py`'s own `apply_inheritance_at_
    birth` -- "one shared stream per call, consumed in a fixed order" --
    generalized here from a single birth to this function's whole-tick
    batch. `get_seeded_rng` is pure Python (a `hashlib` digest plus a
    `random.Random` construction); it issues no database queries, so
    this draw does not appear in the query cost contract below.

    TRANSACTION: the entire call -- zone_stats construction, every
    `coordinate_family_migration` invocation, the batched relocation
    `bulk_update`, every `Memory`/`DemographyEvent` `bulk_create` --
    runs inside one `django.db.transaction.atomic()` block, following
    the `process_inheritance_batch` precedent (`inheritance.py`): a
    failure partway through rolls back everything rather than leaving,
    for example, a relocated agent without their flight memory.

    Query cost contract (bounded by ZONE count and by the number of
    agents who actually flee or get trapped this tick, NEVER by total
    living population beyond the one unavoidable agent-fetch query):
    `World.objects.get` (1) + `Zone.objects.filter` (1) +
    `Government.objects.get` (1) + zone_stats construction (up to 6 per
    zone: `compute_zone_wage` 2, `compute_zone_unemployment` 2,
    `compute_subsistence_threshold` up to 2 -- cached per zone here so
    `_resolve_flight_decision` costs the per-agent evaluation ZERO extra
    queries, per its own "CACHED SUBSISTENCE THRESHOLD" contract) + 1
    population aggregate (`Count` grouped by zone, one query regardless
    of zone or agent count) + 1 historical-flight-window query + 1 query
    to fetch the living agents to iterate. PLUS, only for agents who
    actually flee: `coordinate_family_migration`'s own up-to-5-query cost
    EACH (inherent to reusing that function as-is, not a new N+1 this
    function introduces). PLUS, only when at least one agent is trapped:
    1 batched witness-fetch query (never per trapped agent). PLUS up to 5
    final writes (relocation `bulk_update`, flight-memory `bulk_create`,
    trapped-event `bulk_create`, trapped-memory `bulk_create`,
    mass-flight-event `bulk_create`), each skipped entirely when its
    input list is empty. TOTAL SCALES WITH ZONE COUNT AND WITH THE NUMBER
    OF ACTUAL FLEEING/TRAPPED AGENTS -- NEVER with total population beyond
    that one fixed-cost agent fetch.

    Args:
        simulation: the Simulation instance. Supplies `.config` (read for
            `demography_template`, matching `apply_inheritance_at_birth`'s
            and `process_inheritance_batch`'s own convention) and is
            written onto every emitted `DemographyEvent.simulation`.
        tick: the current simulation tick.
        consecutive_ticks_under_subsistence_by_agent_id: see the
            PRECONDITION-COUNTER PARAMETER section above. Defaults to
            `None`, treated as `{}`.

    Returns:
        None. Persists directly -- this is the orchestrated entry point,
        like `process_inheritance_batch` and `coordinate_family_migration`.
    """
    from collections import defaultdict

    from django.db import transaction
    from django.db.models import Count

    from epocha.apps.agents.models import Agent, Memory
    from epocha.apps.demography.context import compute_subsistence_threshold
    from epocha.apps.demography.models import DemographyEvent
    from epocha.apps.demography.rng import get_seeded_rng
    from epocha.apps.demography.template_loader import load_template
    from epocha.apps.world.models import Government, World, Zone

    counters = consecutive_ticks_under_subsistence_by_agent_id or {}

    template_name = simulation.config.get("demography_template", "pre_industrial_christian")
    template = load_template(template_name)
    flight_trigger_ticks = template["migration"]["flight_trigger_ticks"]

    world = World.objects.get(simulation=simulation)
    zones = list(Zone.objects.filter(world=world).order_by("id"))
    if not zones:
        return

    government = Government.objects.get(simulation=simulation)

    with transaction.atomic():
        # Fix T046/I-12: one seeded stream for the whole tick, shared by every
        # household coordination call and every primary-agent location
        # scatter below -- see this function's own docstring, RNG STREAM
        # section, for why it is derived exactly once here rather than
        # once per fleeing agent.
        rng = get_seeded_rng(simulation, tick, phase="migration")

        zone_stats = {
            "world": world,
            "government_stability": government.stability,
            "zones": {
                z.id: {
                    "zone": z,
                    "wage": compute_zone_wage(simulation, z, tick),
                    "unemployment": compute_zone_unemployment(simulation, z, tick),
                    "subsistence_threshold": compute_subsistence_threshold(simulation, z),
                }
                for z in zones
            },
        }

        baseline_population = {
            row["zone_id"]: row["count"]
            for row in Agent.objects.filter(zone__in=zones, is_alive=True)
            .values("zone_id")
            .annotate(count=Count("id"))
        }

        window_start = tick - flight_trigger_ticks
        fled_agent_ids_by_zone: dict[int, set[int]] = defaultdict(set)
        for row in DemographyEvent.objects.filter(
            simulation=simulation,
            event_type=DemographyEvent.EventType.MIGRATION,
            payload__reason="emergency_flight",
            tick__gt=window_start,
            tick__lt=tick,
        ).values("payload__from_zone", "primary_agent_id"):
            from_zone_id = row["payload__from_zone"]
            # PostgreSQL's JSONField key-transform (the implicit `->>` text
            # extraction `.values("payload__from_zone")` compiles to)
            # returns the value as a string, not the original JSON
            # integer -- cast explicitly so this key matches `Zone.id`
            # (a Python int) in every dict lookup below.
            if from_zone_id is not None and row["primary_agent_id"] is not None:
                fled_agent_ids_by_zone[int(from_zone_id)].add(row["primary_agent_id"])

        # Fix T046/I-11: snapshot of HISTORICAL-only fled counts per zone,
        # taken BEFORE this tick's own new departures are added into
        # `fled_agent_ids_by_zone` below. An agent fleeing THIS tick is
        # still present in `baseline_population` above (captured before
        # their own flight executes); an agent who fled on an EARLIER
        # tick is not (they already left by the time `baseline_population`
        # was queried). Adding only the HISTORICAL count back onto
        # `baseline_population` reconstructs each zone's population as it
        # stood at window start without double-counting this tick's own
        # departures -- see this function's own docstring, MASS-FLIGHT
        # DENOMINATOR AND WINDOW section, for the full derivation and its
        # two accepted limits (deaths, arrivals).
        historical_fled_counts_by_zone = {
            zone_id: len(fled_ids) for zone_id, fled_ids in fled_agent_ids_by_zone.items()
        }

        agents = Agent.objects.filter(zone__in=zones, is_alive=True).order_by("id")

        already_relocated_agent_ids: set[int] = set()
        agents_to_relocate: list = []
        flight_memories: list = []
        trapped_agents: list = []  # (agent, ticks) pairs, id-ascending order

        for agent in agents:
            if agent.id in already_relocated_agent_ids:
                continue

            ticks = counters.get(agent.id, 0)
            meets_preconditions, target_zone = _resolve_flight_decision(
                agent, simulation, tick, template, zone_stats, ticks
            )

            if target_zone is not None:
                origin_zone = zone_stats["zones"][agent.zone_id]["zone"]
                from_zone_id = agent.zone_id

                household_member_ids = coordinate_family_migration(
                    agent,
                    target_zone,
                    tick,
                    template,
                    reason="emergency_flight",
                    emit_event_even_if_empty=True,
                    rng=rng,
                )
                already_relocated_agent_ids.update(household_member_ids)

                agent.zone = target_zone
                # Fix T046/I-12: the decider's own `location`, not only their
                # household's -- this call graph bypasses
                # `agents/movement.py`'s `execute_movement` entirely for
                # the fleeing agent, so nothing else ever writes it.
                agent.location = _scatter_location_in_zone(target_zone, rng)
                agents_to_relocate.append(agent)

                fled_agent_ids_by_zone[from_zone_id].add(agent.id)

                flight_memories.append(
                    Memory(
                        agent=agent,
                        content=(
                            f"I had to leave {origin_zone.name} because of hunger. "
                            "There was no other choice."
                        ),
                        emotional_weight=EMERGENCY_FLIGHT_MEMORY_WEIGHT,
                        source_type=Memory.SourceType.DIRECT,
                        reliability=1.0,
                        tick_created=tick,
                        origin_agent=agent,
                    )
                )

            elif meets_preconditions:
                trapped_agents.append((agent, ticks))

        if agents_to_relocate:
            Agent.objects.bulk_update(agents_to_relocate, ["zone", "location"])
        if flight_memories:
            Memory.objects.bulk_create(flight_memories)

        trapped_events: list = []
        trapped_memories: list = []
        if trapped_agents:
            trapped_zone_ids = {agent.zone_id for agent, _ in trapped_agents}
            members_by_zone: dict[int, list[dict]] = defaultdict(list)
            for row in (
                Agent.objects.filter(zone_id__in=trapped_zone_ids, is_alive=True)
                .order_by("id")
                .values("id", "zone_id", "name")
            ):
                members_by_zone[row["zone_id"]].append(row)

            # Fix T046/M-3: group trapped agents by zone, preserving the
            # id-ascending order `trapped_agents` was already built in
            # above (a plain list, never a bare set) -- the witness
            # memory pass below then runs ONCE PER ZONE, not once per
            # (trapped agent, witness) pair. See this function's own
            # docstring, MISS-3 CO-ZONE PROPAGATION section, for the
            # row-volume argument this restructuring fixes.
            trapped_ids_by_zone: dict[int, list[int]] = defaultdict(list)
            trapped_agent_by_id: dict[int, Any] = {}
            for agent, ticks in trapped_agents:
                trapped_events.append(
                    DemographyEvent(
                        simulation=simulation,
                        tick=tick,
                        event_type=DemographyEvent.EventType.TRAPPED_CRISIS,
                        primary_agent=agent,
                        payload={
                            "zone": agent.zone_id,
                            "consecutive_under_subsistence": ticks,
                        },
                    )
                )
                trapped_ids_by_zone[agent.zone_id].append(agent.id)
                trapped_agent_by_id[agent.id] = agent

            for zone_id in sorted(trapped_ids_by_zone):
                trapped_ids_in_zone = trapped_ids_by_zone[zone_id]
                # Deterministic representative for `origin_agent`
                # (dedup/traceability, per that field's own help_text):
                # the id-ascending first trapped agent in this zone this
                # tick, matching `trapped_ids_in_zone`'s own construction
                # order above.
                representative_agent = trapped_agent_by_id[trapped_ids_in_zone[0]]
                trapped_count = len(trapped_ids_in_zone)
                zone_name = zone_stats["zones"][zone_id]["zone"].name
                content = (
                    f"{zone_name} is gripped by a starvation crisis: {trapped_count} "
                    f"{'person is' if trapped_count == 1 else 'people are'} trapped, "
                    "with nowhere better to go."
                )
                # NO exclusion (fix T046/NEW-4, round 2):
                # FR-026 (spec.md:189) and acceptance scenario 3
                # (spec.md:133) both require the memory to reach "tutti
                # gli agenti co-zone" -- ALL co-zone agents, victims
                # included, without exception. `members_by_zone[zone_id]`
                # is every living agent in the zone, trapped or not; all
                # of them receive this aggregate zone-crisis memory. This
                # is still O(M) rows per zone (T046/M-3's own bound), never
                # O(N*M) -- the row count equals the zone's population,
                # independent of how many of its agents happen to be
                # trapped this tick.
                for member_row in members_by_zone[zone_id]:
                    trapped_memories.append(
                        Memory(
                            agent_id=member_row["id"],
                            content=content,
                            emotional_weight=TRAPPED_CRISIS_MEMORY_WEIGHT,
                            source_type=Memory.SourceType.PUBLIC,
                            reliability=1.0,
                            tick_created=tick,
                            origin_agent=representative_agent,
                        )
                    )

        if trapped_events:
            DemographyEvent.objects.bulk_create(trapped_events)
        if trapped_memories:
            Memory.objects.bulk_create(trapped_memories)

        mass_flight_events: list = []
        for zone in zones:
            # Fix T046/I-11: population AT WINDOW START, not the zone's
            # current living population -- see the historical-only
            # snapshot's own comment above and this function's docstring
            # for the full derivation.
            population_at_window_start = baseline_population.get(
                zone.id, 0
            ) + historical_fled_counts_by_zone.get(zone.id, 0)
            if population_at_window_start == 0:
                continue
            fled_ids = fled_agent_ids_by_zone.get(zone.id, set())
            if not fled_ids:
                continue
            if len(fled_ids) / population_at_window_start > MASS_FLIGHT_THRESHOLD_FRACTION:
                mass_flight_events.append(
                    DemographyEvent(
                        simulation=simulation,
                        tick=tick,
                        event_type=DemographyEvent.EventType.MASS_FLIGHT,
                        payload={
                            "from_zone": zone.id,
                            "agents": sorted(fled_ids),
                            "trigger_ticks": flight_trigger_ticks,
                        },
                    )
                )

        if mass_flight_events:
            DemographyEvent.objects.bulk_create(mass_flight_events)

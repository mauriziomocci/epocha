"""Monetary velocity update, inflation computation, and wealth-mood feedback.

Fisher's equation MV=PQ is used as a DIAGNOSTIC check (is the simulated
economy internally consistent?), not as a price-determination mechanism.
Prices are set by the Walrasian market clearing, not by Fisher.

Source: Fisher, I. (1911). The Purchasing Power of Money.

Mood-wealth relationship follows Kahneman & Deaton (2010): emotional
well-being plateaus above a satiation threshold. Implemented as
exponential decay of mood boost above threshold.
"""

from __future__ import annotations

import logging
import math

logger = logging.getLogger(__name__)

# Mood constants. Tunable design parameters; the qualitative behavior
# (plateau above satiation, penalty below poverty) is from Kahneman &
# Deaton (2010). The specific numeric values are calibrated for the
# simulation's 0-1 mood scale and are not derived from empirical data.
_MOOD_BOOST_BASE = 0.02
_MOOD_SATIATION_DECAY = 0.005
_MOOD_PENALTY_POOR = 0.05
_MOOD_PENALTY_DESTITUTE = 0.10

# Absolute fallback thresholds, used only when a live median wealth is
# not available (e.g. no living agents this tick -- see
# derive_mood_thresholds). Kept as named constants instead of bare
# literals so compute_mood_delta's default signature and the fallback
# path share a single definition (DRY).
_POVERTY_THRESHOLD = 10.0
_DEFAULT_SATIATION_THRESHOLD = 100.0

# CM-6 fix (Round 1 audit report, monetary+initialization cross-module
# finding): the pre-fix constants above (poverty=10.0, satiation=100.0)
# were absolute values disconnected from the wealth scale of whichever
# era template seeded the simulation. In the pre-industrial template,
# every property-owning agent starts with property value alone (200 +
# 150 + 100 = 450) far past satiation=100, while the "poor" cash range
# (5-30) plus starting goods already exceeds poverty=10 for nearly
# everyone -- the poverty band was unreachable and the satiation
# plateau was trivially breached from tick 0. Worse, wealth_range
# scales by 2-3 orders of magnitude across templates (pre-industrial
# elite cash 300-500 vs sci-fi elite cash 5000-20000), so a single
# absolute pair of constants cannot be correct for more than one era.
#
# derive_mood_thresholds instead computes both bands as multiples of
# the population's median wealth this tick (see engine.py step 8),
# a relative-threshold approach that adapts automatically to any
# template's wealth scale:
#
# _POVERTY_FRACTION_OF_MEDIAN: the OECD/Eurostat relative-poverty
# convention classifies a household as at-risk-of-poverty when its
# equivalised disposable income falls below 50% of the population
# median (the EU/Eurostat headline indicator uses 60%; OECD's own
# uses 50%, adopted here). Source: OECD, "The OECD Approach to
# Measuring Income Distribution and Poverty" (2013); OECD, "Society
# at a Glance" income-poverty indicator methodology.
_POVERTY_FRACTION_OF_MEDIAN = 0.5

# _SATIATION_MULTIPLE_OF_MEDIAN: Kahneman & Deaton (2010) found
# emotional well-being plateaus above a household income of
# approximately $75,000/year, measured from 2008-2009 Gallup-
# Healthways survey data. US Census Bureau reported median household
# income of $50,303 for 2008 (Census Bureau, "Income, Poverty, and
# Health Insurance Coverage in the United States: 2008", Table H-8).
# The ratio 75,000 / 50,303 ~= 1.5 is adopted as the satiation-to-
# median-wealth multiplier: an approximation of where the plateau in
# the original study sat relative to that study's own median, applied
# here to the simulation's own median wealth instead of a fixed
# absolute figure. This is a scale-transfer approximation, not a
# claim that Kahneman & Deaton measured wealth -- their study measured
# household income, while this simulation's "wealth" aggregates cash
# + inventory value + property value (see update_agent_wealth).
_SATIATION_MULTIPLE_OF_MEDIAN = 1.5


def compute_velocity(
    transaction_volume: float,
    money_supply: float,
) -> float:
    """Compute monetary velocity V = transaction_volume / M.

    V is a MEASURED quantity (how many times money changed hands this
    tick), not a parameter. Storing it is caching, not asserting a
    constant.

    Source: Fisher (1911). V = PQ/M, here approximated as total
    transaction value / money supply.
    """
    if money_supply <= 0 or transaction_volume <= 0:
        return 0.0
    return transaction_volume / money_supply


def compute_circulating_money_supply(
    agent_cash_balances: list[dict[str, float]],
    currency_code: str,
) -> float:
    """Sum circulating cash across agents for one currency: the live M.

    CM-2 fix (Round 1 audit report, cross-module CM-2): Currency.
    total_supply was previously set once at initialization from the
    template's initial_supply constant and never updated, while agent
    cash moved independently every tick (trades conserve it, rent/
    wages/profit inject it). compute_velocity and check_fisher_
    consistency both depend on M meaning "money actually in
    circulation right now" -- this function computes exactly that,
    recomputed every tick by the caller (see engine.py step 8).

    Reconciliation with BankingState.total_deposits: deposits are NOT
    added on top of this sum. BankingState.recalculate_deposits
    (banking.py) sets total_deposits to the SAME sum of all agents'
    cash (its own docstring: "this approximation treats all agent
    cash as deposited") -- there is no disjoint reserve pool held by
    the bank in this model, only a shadow-accounting mirror of agent
    cash used for the reserve-ratio and solvency checks. Summing
    circulating cash and total_deposits would therefore double-count
    the identical money.

    Args:
        agent_cash_balances: one {currency_code: amount} dict per
            living agent (e.g. AgentInventory.cash values).
        currency_code: the currency to aggregate (the primary
            currency in practice, since Fisher's MV=PQ is evaluated
            per currency).

    Returns:
        Total circulating cash in currency_code across all agents.
    """
    return sum(cash.get(currency_code, 0.0) for cash in agent_cash_balances)


def check_fisher_consistency(
    money_supply: float,
    velocity: float,
    price_level: float,
    output_level: float,
) -> float:
    """Check MV vs PQ consistency (Fisher's equation as diagnostic).

    Returns the relative divergence: |MV - PQ| / max(MV, PQ, 1).
    Values above 0.2 (20%) warrant investigation.

    This is a diagnostic, not an enforcement. The market determines
    prices; Fisher tells us if the money supply is consistent with
    the observed price level and output.
    """
    mv = money_supply * velocity
    pq = price_level * output_level
    denominator = max(mv, pq, 1.0)
    divergence = abs(mv - pq) / denominator

    if divergence > 0.2:
        logger.warning(
            "Fisher MV=PQ divergence: %.1f%%. MV=%.1f, PQ=%.1f. "
            "Money supply may be inconsistent with price level.",
            divergence * 100,
            mv,
            pq,
        )

    return divergence


def aggregate_system_prices(
    zone_prices: list[dict[str, float]],
) -> dict[str, float]:
    """Aggregate per-zone prices into a genuine system-wide price per good.

    CM-5 fix (Round 1 audit report, cross-module CM-5): the previous
    implementation merged per-zone price dicts with dict.update() once
    per zone, which keeps only the LAST zone's price for any good
    present in multiple zones -- despite the "_all" naming in engine.py
    implying a true aggregate. This function instead computes the
    unweighted arithmetic mean of a good's price across every zone
    that quotes it, so a good present in N zones contributes all N
    observations to the system price, not just the last one processed.

    Simplification: this is an unweighted mean across zones, the same
    aggregation-bias caveat documented in compute_inflation applies
    here (a supply- or activity-weighted mean would better reflect
    where economic activity actually occurs, at the cost of requiring
    per-zone-per-good weights to be threaded through). What is lost:
    a zone with negligible trade volume for a good counts as much as
    a zone that dominates the market for it.

    Args:
        zone_prices: one {good_code: price} dict per zone (e.g. each
            zone's market_prices dict for the tick).

    Returns:
        {good_code: mean_price_across_the_zones_quoting_it}. Goods
        absent from every zone dict do not appear in the result.
    """
    totals: dict[str, float] = {}
    counts: dict[str, int] = {}
    for prices in zone_prices:
        for good, price in prices.items():
            totals[good] = totals.get(good, 0.0) + price
            counts[good] = counts.get(good, 0) + 1
    return {good: totals[good] / counts[good] for good in totals}


def compute_inflation(
    old_prices: dict[str, float],
    new_prices: dict[str, float],
) -> float:
    """Compute inflation rate as the unweighted arithmetic mean of price relatives.

    Returns a decimal rate (0.10 = 10% inflation, -0.05 = 5% deflation).

    Simplification: this is a Carli index (Carli 1764) - the unweighted
    arithmetic mean of per-good price relatives (new_price/old_price - 1).
    It carries a documented UPWARD bias relative to the expenditure- or
    quantity-weighted indices (Laspeyres, Paasche, Fisher-ideal) and the
    unweighted geometric-mean (Jevons) index that national statistical
    agencies adopted specifically to avoid this bias (ILO, IMF, OECD,
    UNECE, Eurostat & World Bank 2004, "Consumer Price Index Manual:
    Theory and Practice", ch. 20; the bias follows from the AM-GM
    inequality, AM(relatives) >= GM(relatives), with equality only when
    all relatives are equal).

    The fuller model would weight each good's price relative by its
    expenditure share (Laspeyres/Paasche/Fisher-ideal), or use the
    geometric mean (Jevons) for unweighted elementary aggregation. What
    is lost here: the simulation does not feed expenditure-share data
    into this function, so no weighting is applied, and the arithmetic-
    mean form retains the known upward formula/substitution bias that
    the geometric mean avoids.
    """
    if not old_prices or not new_prices:
        return 0.0

    changes = []
    for good, old_price in old_prices.items():
        new_price = new_prices.get(good)
        if new_price is not None and old_price > 0:
            changes.append((new_price - old_price) / old_price)

    if not changes:
        return 0.0

    return sum(changes) / len(changes)


def update_agent_wealth(
    holdings: dict[str, float],
    cash: dict[str, float],
    property_values: list[float],
    prices: dict[str, float],
) -> float:
    """Compute total agent wealth as sum of inventory value + cash + property.

    This replaces the old Agent.wealth as a computed summary for
    backward compatibility with modules that read it.
    """
    inventory_value = sum(qty * prices.get(good, 0.0) for good, qty in holdings.items())
    total_cash = sum(cash.values())
    total_property = sum(property_values)
    return inventory_value + total_cash + total_property


def compute_mood_delta(
    wealth: float,
    satiation_threshold: float = _DEFAULT_SATIATION_THRESHOLD,
    poverty_threshold: float = _POVERTY_THRESHOLD,
) -> float:
    """Compute mood change based on wealth level.

    Source: Kahneman, D. & Deaton, A. (2010). "High income improves
    evaluation of life but not emotional well-being." PNAS.

    Above satiation: diminishing mood boost approaching zero (exponential
    decay). The specific decay rate (_MOOD_SATIATION_DECAY = 0.005) is a
    tunable parameter; the qualitative behavior (plateau) is the paper's
    central finding.

    Below poverty: flat mood penalty (step function, not scaled by
    wealth). Any wealth in [0, poverty_threshold) incurs the same
    constant penalty -_MOOD_PENALTY_POOR regardless of how far below the
    threshold the agent is. Below zero: a more severe, likewise constant,
    penalty -_MOOD_PENALTY_DESTITUTE.

    Known discontinuity at the satiation threshold (Round 2 re-audit
    finding PROD-5, disclosed simplification): the moderate band pays
    _MOOD_BOOST_BASE * 0.5, while just above satiation_threshold the
    decay branch starts from the FULL _MOOD_BOOST_BASE (excess ~ 0), so
    the per-tick boost momentarily doubles exactly at the threshold
    before decaying toward zero. This is a piecewise simplification,
    locally at odds with the plateau narrative in a neighborhood of the
    threshold; the paper's qualitative finding (no further emotional
    gain from wealth far above satiation) still holds asymptotically. A
    continuous alternative would start the decay branch at
    _MOOD_BOOST_BASE * 0.5; the current form is kept as a tunable
    heuristic and the seam is documented rather than smoothed.

    CM-6 fix: poverty_threshold is now a parameter (previously hardcoded
    to the module constant _POVERTY_THRESHOLD), symmetric with
    satiation_threshold, so callers can pass wealth-scale-reconciled
    values derived from the current population (see
    derive_mood_thresholds). Both default to the module's absolute
    constants, preserving prior behavior for callers that pass neither.

    Args:
        wealth: the agent's total wealth (cash + inventory + property).
        satiation_threshold: wealth level above which the plateau
            applies. Defaults to _DEFAULT_SATIATION_THRESHOLD (100.0).
        poverty_threshold: wealth level below which the flat poverty
            penalty applies. Defaults to _POVERTY_THRESHOLD (10.0).
    """
    if wealth < 0:
        return -_MOOD_PENALTY_DESTITUTE
    elif wealth < poverty_threshold:
        return -_MOOD_PENALTY_POOR
    elif wealth > satiation_threshold:
        # Kahneman & Deaton (2010): plateau above satiation
        excess = wealth - satiation_threshold
        return _MOOD_BOOST_BASE * math.exp(-_MOOD_SATIATION_DECAY * excess)
    else:
        # Moderate wealth: small positive delta
        return _MOOD_BOOST_BASE * 0.5


def derive_mood_thresholds(median_wealth: float) -> tuple[float, float]:
    """Derive (poverty_threshold, satiation_threshold) from median wealth.

    CM-6 fix (Round 1 audit report, monetary+initialization
    cross-module finding): see the module-level comment above
    _POVERTY_FRACTION_OF_MEDIAN for the full defect description and
    the OECD / Kahneman-Deaton sourcing of the two multipliers.

    poverty_threshold = _POVERTY_FRACTION_OF_MEDIAN * median_wealth
    satiation_threshold = _SATIATION_MULTIPLE_OF_MEDIAN * median_wealth

    With the multipliers 0.5 and 1.5, the median wealth itself always
    falls strictly inside the "moderate wealth" band (poverty_threshold
    < median_wealth < satiation_threshold, for any median_wealth > 0):
    an agent at the population's center is neither classified as poor
    nor as satiated, regardless of the absolute wealth scale of the
    era template that seeded the simulation.

    Degenerate case: when median_wealth is not strictly positive (no
    living agents this tick, or a pathological all-zero/negative
    wealth population), a relative threshold is not meaningful --
    0.5 * 0 = 0 would make the poverty band unreachable AND collapse
    satiation to non-positive wealth. Falls back to the module's
    absolute defaults (_POVERTY_THRESHOLD, _DEFAULT_SATIATION_THRESHOLD)
    in that case.

    Args:
        median_wealth: median total wealth (cash + inventory value +
            property value) across the living population this tick.

    Returns:
        (poverty_threshold, satiation_threshold).
    """
    if median_wealth <= 0:
        return _POVERTY_THRESHOLD, _DEFAULT_SATIATION_THRESHOLD
    poverty_threshold = _POVERTY_FRACTION_OF_MEDIAN * median_wealth
    satiation_threshold = _SATIATION_MULTIPLE_OF_MEDIAN * median_wealth
    return poverty_threshold, satiation_threshold

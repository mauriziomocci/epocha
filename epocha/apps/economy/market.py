"""Walrasian tatonnement market clearing.

Each zone has a local market where supply meets demand. Prices adjust
iteratively toward equilibrium using the tatonnement mechanism.

Source: Walras, L. (1874). Elements of Pure Economics.
Warning: Scarf (1960) showed tatonnement may not converge with 3+ goods.
The max_iterations parameter is the safety net.
Implementation follows applied CGE practice: Shoven & Whalley (1992) ch. 4.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# Tatonnement parameters. Tunable design parameters without theoretical
# derivation for specific values. Consistent with applied CGE practice
# (Shoven & Whalley 1992).
#
# ADJUSTMENT_RATE: reduced from 0.1 to 0.03 to improve stability in small
# markets (4-15 agents). Faster steps cause oscillation rather than
# convergence in sparse markets. Tunable design parameter.
ADJUSTMENT_RATE = 0.03
# MAX_ITERATIONS: increased from 50 to 100 to compensate for the smaller
# step size. More iterations are needed to reach equilibrium at rate 0.03.
# Tunable design parameter.
MAX_ITERATIONS = 100
CONVERGENCE_THRESHOLD = 0.01
EPSILON = 0.001  # prevents division by zero in supply
# Maximum price relative to starting price. Prevents runaway prices
# when supply is at epsilon floor. Tunable design parameter.
# A 100x price increase represents hyperinflation and should trigger
# crisis events rather than further price escalation.
MAX_PRICE_RATIO = 100.0
# Minimum absolute price floor. No good can trade below this value.
# Prevents numerical collapse when supply floods a small market.
# Tunable design parameter.
MIN_PRICE = 0.01
# Maximum fractional price change per iteration. Prevents runaway
# oscillation when excess demand is extreme (e.g. zero supply, infinite
# excess). At 0.5, prices can at most double or halve each iteration.
# Tunable design parameter; no theoretical derivation.
MAX_CHANGE_RATIO = 0.5
# Subsistence need per agent per essential good per tick.
# Extracted on 2026-04-18 as part of the Demography Plan 1 integration
# contract (see docs/superpowers/specs/2026-04-18-demography-design-it.md).
# Shared with demography/context.py:compute_subsistence_threshold.
SUBSISTENCE_NEED_PER_AGENT: float = 1.0
# Maximum discretionary demand per agent per good per tick.
# Without a cap, low prices combined with high cash produce absurd
# demand quantities (e.g. cash=5000, price=0.02 => 25000 units).
# 5 units is a reasonable upper bound for a non-essential good in
# one tick. Tunable design parameter.
_MAX_DISCRETIONARY_DEMAND = 5.0
# Fraction of cash an agent allocates to discretionary (non-essential)
# spending per tick, BEFORE splitting across individual goods. Bounds
# total discretionary spend at cash * _DISCRETIONARY_SPEND_FRACTION
# regardless of how many non-essential goods exist in the template
# (MKT-5 fix: pre-fix this fraction was applied independently to EACH
# non-essential good against the agent's FULL cash, so total spend
# across K goods could reach ~0.1*K*cash, exceeding cash). Tunable
# design parameter; no theoretical derivation for the specific value.
_DISCRETIONARY_SPEND_FRACTION = 0.1
# Floor applied to price_elasticity when it is used as a budget-share
# weight (see _discretionary_budget_shares), preventing a
# near-zero-elasticity good from claiming an unboundedly large share.
# Tunable design parameter.
_MIN_PRICE_ELASTICITY = 0.1


def tatonnement_prices(
    current_prices: dict[str, float],
    total_supply: dict[str, float],
    total_demand: dict[str, float],
    *,
    base_prices: dict[str, float] | None = None,
    adjustment_rate: float = ADJUSTMENT_RATE,
    max_iterations: int = MAX_ITERATIONS,
    convergence_threshold: float = CONVERGENCE_THRESHOLD,
) -> tuple[dict[str, float], bool]:
    """Compute equilibrium prices via iterative tatonnement.

    For each good: P_new = P_old * (1 + rate * excess / max(supply, epsilon))
    Iterates until |excess/supply| < threshold for all goods, or max_iterations.

    Args:
        current_prices: {good_code: price} starting prices.
        total_supply: {good_code: quantity} total offered.
        total_demand: {good_code: quantity} total demanded.
        adjustment_rate: Step size per iteration. Tunable, default 0.03.
        max_iterations: Safety net for non-convergence (Scarf 1960).
        convergence_threshold: |excess/supply| target.

    Returns:
        Tuple of (new_prices, converged). If not converged, new_prices
        are the last iteration's values (approximate but not catastrophically
        wrong -- they reflect the direction of excess demand/supply).
    """
    prices = dict(current_prices)
    initial_prices = dict(current_prices)
    goods = list(prices.keys())

    for iteration in range(max_iterations):
        converged = True
        for good in goods:
            raw_supply = total_supply.get(good, 0.0)
            supply = max(raw_supply, EPSILON)
            demand = total_demand.get(good, 0.0)

            # Single MAX_PRICE_RATIO ceiling anchor for this good, shared
            # by BOTH branches below (zero-supply and normal tatonnement).
            # Prefer base_prices (the template's calibrated reference)
            # over this tick's starting price so the cross-tick-drift
            # protection does not depend on which branch updates the
            # price (MKT-6 fix: previously the zero-supply branch always
            # anchored to initial_prices, defeating the drift protection
            # documented below for the normal branch).
            price_reference = (base_prices or initial_prices).get(good, 1.0)

            # If there is no real supply AND no real demand for this good
            # in this zone, skip price adjustment entirely -- there is no
            # local market for it. Price stays at its current level.
            # This prevents goods with zero local production from having
            # their prices explode toward infinity via tatonnement.
            if raw_supply < EPSILON and demand < EPSILON:
                continue

            # If there is demand but zero supply, the good is unavailable
            # locally. Cap the price at MAX_PRICE_RATIO * price_reference
            # rather than iterating toward infinity. In a real economy,
            # unavailable goods simply aren't traded, not priced at infinity.
            if raw_supply < EPSILON and demand > 0:
                max_allowed = price_reference * MAX_PRICE_RATIO
                prices[good] = min(prices[good] * 1.1, max_allowed)
                continue

            excess = demand - supply

            relative_excess = abs(excess) / supply
            if relative_excess > convergence_threshold:
                converged = False

            adjustment = adjustment_rate * excess / supply
            new_price = prices[good] * (1.0 + adjustment)

            # Cap per-iteration price change to prevent runaway oscillation.
            # Without this cap, extreme excess demand (e.g. zero supply)
            # sends prices to astronomical levels in a single iteration.
            # MAX_CHANGE_RATIO=0.5 means prices can at most 1.5x or 0.5x
            # per iteration. Tunable design parameter.
            if prices[good] > 0:
                ratio = new_price / prices[good]
                if ratio > 1.0 + MAX_CHANGE_RATIO:
                    new_price = prices[good] * (1.0 + MAX_CHANGE_RATIO)
                elif ratio < 1.0 - MAX_CHANGE_RATIO:
                    new_price = prices[good] * (1.0 - MAX_CHANGE_RATIO)

            # Apply absolute floor then MAX_PRICE_RATIO ceiling, anchored
            # to price_reference (base_prices when supplied) rather than
            # the current tick's starting price. This prevents prices
            # from drifting to astronomical values across multiple ticks
            # when each tick's "initial price" is already inflated.
            max_price = price_reference * MAX_PRICE_RATIO
            prices[good] = min(max(MIN_PRICE, new_price), max_price)

        if converged:
            return prices, True

    logger.warning(
        "Tatonnement did not converge after %d iterations. "
        "Using last computed prices (approximate). "
        "This is expected with 3+ goods (Scarf 1960).",
        max_iterations,
    )
    return prices, False


def _discretionary_budget_shares(non_essential_cats: list[dict]) -> dict[str, float]:
    """Split the per-agent discretionary budget across non-essential goods.

    Shares are weighted by inverse price elasticity: share_i =
    (1/e_i) / sum_j(1/e_j), so shares sum to exactly 1 and a good with
    lower elasticity (more necessity-like, per the demand heterogeneity
    documented in Houthakker & Taylor 1970) claims a proportionally
    larger, more stable slice of the budget.

    This is a documented heuristic, NOT a solved Marshallian demand
    system. price_elasticity is the dimensionless own-price response
    dQ/dP * P/Q (e.g. constant-elasticity demand Q = A*P^(-e)); using
    it here as an inverse-weight on budget SHARES (rather than as a
    divisor on quantity, MKT-5's original defect) keeps it dimensionally
    sane without requiring a full numerical solve of a constant-elasticity
    demand system under a joint budget constraint. A full treatment would
    jointly estimate cross-price and income elasticities via e.g. an
    Almost Ideal Demand System (Deaton & Muellbauer 1980); what is lost
    here is that heterogeneity in demand response is approximated by a
    single static weight instead of a solved equilibrium allocation.

    Shares summing to 1 is what guarantees total discretionary spend is
    bounded at cash * _DISCRETIONARY_SPEND_FRACTION regardless of how
    many non-essential goods the template defines.
    """
    if not non_essential_cats:
        return {}
    inverse_elasticities = {
        cat["code"]: 1.0 / max(cat.get("price_elasticity", 1.0), _MIN_PRICE_ELASTICITY)
        for cat in non_essential_cats
    }
    total_inverse_elasticity = sum(inverse_elasticities.values())
    return {
        code: inv_elasticity / total_inverse_elasticity
        for code, inv_elasticity in inverse_elasticities.items()
    }


def collect_supply_and_demand(
    agent_inventories: list[dict],
    good_categories: list[dict],
    market_prices: dict[str, float],
) -> tuple[dict[str, float], dict[str, float], dict[str, list]]:
    """Collect supply and demand from all agents in a zone.

    Supply: agents offer holdings above subsistence reserve.
    Demand: agents want essential goods they lack, plus a budget-
    constrained discretionary demand for non-essential goods -- each
    agent allocates cash * _DISCRETIONARY_SPEND_FRACTION across all
    non-essential goods (split by _discretionary_budget_shares), so
    total discretionary spend never exceeds that budget regardless of
    how many non-essential goods exist (MKT-5 fix).

    The budget bound above holds at the SIZING prices (this tick's
    pre-clearing market_prices). Trades settle at the post-tatonnement
    equilibrium prices, which can exceed the sizing prices, and
    essential demand is a physical subsistence gap not sized by cash
    at all -- so the REALIZED spend bound is enforced at settlement by
    the engine's affordability guard, which scales each trade down to
    the buyer's remaining cash (MKT-7 fix; see engine.py's trade
    application loop).

    Args:
        agent_inventories: list of dicts with keys: agent_id, holdings,
            cash_amount, is_hoarding (bool).
        good_categories: list of dicts with keys: code, is_essential,
            price_elasticity.
        market_prices: current prices per good.

    Returns:
        (total_supply, total_demand, agent_orders) where agent_orders
        is a list of {agent_id, offers: {good: qty}, wants: {good: qty}}.
    """
    total_supply: dict[str, float] = {}
    total_demand: dict[str, float] = {}
    agent_orders: list[dict] = []

    essential_codes = {g["code"] for g in good_categories if g["is_essential"]}
    non_essential_cats = [g for g in good_categories if not g["is_essential"]]
    discretionary_budget_share = _discretionary_budget_shares(non_essential_cats)
    subsistence_need = SUBSISTENCE_NEED_PER_AGENT

    for inv in agent_inventories:
        offers: dict[str, float] = {}
        wants: dict[str, float] = {}

        # Supply: offer surplus above subsistence reserve
        if not inv.get("is_hoarding", False):
            for good_code, qty in inv["holdings"].items():
                if good_code in essential_codes:
                    surplus = max(0.0, qty - subsistence_need)
                else:
                    surplus = qty
                if surplus > 0:
                    offers[good_code] = surplus
                    total_supply[good_code] = total_supply.get(good_code, 0.0) + surplus

        # Demand: essential subsistence needs.
        for cat in good_categories:
            if not cat["is_essential"]:
                continue
            code = cat["code"]
            current = inv["holdings"].get(code, 0.0)
            need = max(0.0, subsistence_need - current)
            if need > 0:
                wants[code] = need
                total_demand[code] = total_demand.get(code, 0.0) + need

        # Discretionary demand: bounded budget split across non-essential
        # goods (see _discretionary_budget_shares docstring). The
        # per-good spend is capped at _MAX_DISCRETIONARY_DEMAND*price,
        # which can only reduce spend below the allocated share, never
        # exceed it -- so total spend across all non-essential goods
        # never exceeds cash * _DISCRETIONARY_SPEND_FRACTION.
        if non_essential_cats:
            cash = inv.get("cash_amount", 0.0)
            discretionary_budget = cash * _DISCRETIONARY_SPEND_FRACTION
            for cat in non_essential_cats:
                code = cat["code"]
                # R3-2 fix (Round 3 re-audit, run wf_af84ed13-dc3): an
                # agent must not project discretionary demand for a
                # good it is itself offering this tick -- the matching
                # sweep could pair the agent with itself, a wash trade
                # that nets to zero on its inventory but inflates the
                # measured transaction volume and hence velocity. An
                # agent wanting to keep such goods simply hoards them.
                # Documented trade-off (Round 4 re-audit): the skip
                # also removes this agent's contribution to the good's
                # NET excess demand (lowering the tatonnement price
                # signal versus the pre-fix behavior), and the skipped
                # per-good budget share is dropped for the tick rather
                # than reallocated to other goods -- both accepted, as
                # the pre-fix signal was inflated by demand that could
                # only ever settle against the agent itself.
                if code in offers:
                    continue
                price = max(market_prices.get(code, 1.0), EPSILON)
                per_good_budget = discretionary_budget * discretionary_budget_share.get(code, 0.0)
                discretionary = min(_MAX_DISCRETIONARY_DEMAND, per_good_budget / price)
                if discretionary > 0.01:
                    wants[code] = discretionary
                    total_demand[code] = total_demand.get(code, 0.0) + discretionary

        agent_orders.append(
            {
                "agent_id": inv["agent_id"],
                "offers": offers,
                "wants": wants,
            }
        )

    return total_supply, total_demand, agent_orders


def execute_trades(
    agent_orders: list[dict],
    equilibrium_prices: dict[str, float],
    total_supply: dict[str, float],
    total_demand: dict[str, float],
) -> list[dict]:
    """Execute trades at equilibrium prices, conserving traded quantity.

    Realized volume for a good is capped at min(total_supply,
    total_demand) and rationed on the short side: when demand exceeds
    supply, every buyer keeps demand_ratio = traded/demand of its want;
    when supply exceeds demand, every seller gives up supply_ratio =
    traded/supply of its offer (Walras 1874; Shoven & Whalley 1992
    ch. 4). These per-agent rationed volumes are the TARGETS matched
    below -- both sides' targets sum to exactly `traded`.

    Matching uses running totals: a two-pointer sweep decrements each
    buyer's remaining target and the CURRENT seller's remaining target
    as matches are made, advancing to the next seller only once it is
    exhausted (and to the next buyer only once its own target is met).
    This guarantees sum(trade quantities) == traded, and that no
    agent's cumulative matched volume exceeds its own rationed target
    (hence never exceeds its original want/offer, since both ratios are
    <= 1). Pre-fix, the matching re-matched EVERY buyer against EVERY
    seller without decrementing running totals, so aggregate matched
    volume scaled with N*M instead of being capped at `traded` (MKT-2).

    Returns list of trade records with keys: buyer_id, seller_id,
    good_code, quantity, price, total.
    """
    trades: list[dict] = []

    # R3-MKT-8 fix (Round 3 re-audit, run wf_af84ed13-dc3): iterate
    # goods in SORTED order. A plain set of str keys iterates in a
    # PYTHONHASHSEED-dependent order, and the engine's settlement
    # (affordability guard) is order-sensitive, so identically-seeded
    # runs could diverge. Sorting pins a deterministic trade order.
    for good_code in sorted(set(total_supply) | set(total_demand)):
        supply = total_supply.get(good_code, 0.0)
        demand = total_demand.get(good_code, 0.0)
        price = equilibrium_prices.get(good_code, 1.0)

        if supply <= 0 or demand <= 0:
            continue

        # Traded quantity is the minimum of supply and demand
        traded = min(supply, demand)

        # Rationing: if demand > supply, buyers get proportional shares
        demand_ratio = traded / demand if demand > 0 else 0.0
        supply_ratio = traded / supply if supply > 0 else 0.0

        # Rationed per-agent targets. remaining_sell entries are mutable
        # [seller_id, qty] pairs decremented by the sweep below; buyers
        # only need a read-only target since each buyer is visited once.
        buyer_targets = [
            (o["agent_id"], o["wants"].get(good_code, 0.0) * demand_ratio)
            for o in agent_orders
            if o["wants"].get(good_code, 0.0) > 0
        ]
        remaining_sell = [
            [o["agent_id"], o["offers"].get(good_code, 0.0) * supply_ratio]
            for o in agent_orders
            if o["offers"].get(good_code, 0.0) > 0
        ]

        # Two-pointer running-totals sweep: since sum(buyer_targets) ==
        # sum(seller targets) == traded, this consumes both sides exactly.
        seller_idx = 0
        for buyer_id, buy_target in buyer_targets:
            buy_left = buy_target
            while buy_left > EPSILON and seller_idx < len(remaining_sell):
                seller_entry = remaining_sell[seller_idx]
                seller_id, sell_left = seller_entry
                if sell_left <= EPSILON:
                    seller_idx += 1
                    continue
                share = min(buy_left, sell_left)
                trades.append(
                    {
                        "buyer_id": buyer_id,
                        "seller_id": seller_id,
                        "good_code": good_code,
                        "quantity": share,
                        "price": price,
                        "total": share * price,
                    }
                )
                buy_left -= share
                seller_entry[1] -= share
                if seller_entry[1] <= EPSILON:
                    seller_idx += 1

    return trades


def clear_market(
    agent_inventories: list[dict],
    good_categories: list[dict],
    market_prices: dict[str, float],
) -> tuple[dict[str, float], list[dict], dict[str, float], dict[str, float]]:
    """Convenience function: collect supply/demand, find prices, execute trades.

    Returns (equilibrium_prices, trades, total_supply, total_demand).
    """
    total_supply, total_demand, agent_orders = collect_supply_and_demand(
        agent_inventories,
        good_categories,
        market_prices,
    )
    equilibrium_prices, converged = tatonnement_prices(
        market_prices,
        total_supply,
        total_demand,
    )
    trades = execute_trades(
        agent_orders,
        equilibrium_prices,
        total_supply,
        total_demand,
    )
    return equilibrium_prices, trades, total_supply, total_demand

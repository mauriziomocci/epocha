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

            # If there is no real supply AND no real demand for this good
            # in this zone, skip price adjustment entirely -- there is no
            # local market for it. Price stays at its current level.
            # This prevents goods with zero local production from having
            # their prices explode toward infinity via tatonnement.
            if raw_supply < EPSILON and demand < EPSILON:
                continue

            # If there is demand but zero supply, the good is unavailable
            # locally. Cap the price at MAX_PRICE_RATIO * initial price
            # rather than iterating toward infinity. In a real economy,
            # unavailable goods simply aren't traded, not priced at infinity.
            if raw_supply < EPSILON and demand > 0:
                max_allowed = initial_prices.get(good, 1.0) * MAX_PRICE_RATIO
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

            # Apply absolute floor then MAX_PRICE_RATIO ceiling.
            # Use base_prices (from template) as the reference for the cap,
            # NOT the current tick's starting price. This prevents prices
            # from drifting to astronomical values across multiple ticks
            # when each tick's "initial price" is already inflated.
            reference = (base_prices or initial_prices).get(good, 1.0)
            max_price = reference * MAX_PRICE_RATIO
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


def collect_supply_and_demand(
    agent_inventories: list[dict],
    good_categories: list[dict],
    market_prices: dict[str, float],
) -> tuple[dict[str, float], dict[str, float], dict[str, list]]:
    """Collect supply and demand from all agents in a zone.

    Supply: agents offer holdings above subsistence reserve.
    Demand: agents want essential goods they lack, plus non-essential
    goods proportional to cash and inverse price elasticity.

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
    subsistence_need = 1.0  # 1 unit per essential good per tick

    # Maximum discretionary demand per agent per good per tick.
    # Without a cap, low prices combined with high cash produce absurd
    # demand quantities (e.g. cash=5000, price=0.02 => 25000 units).
    # 5 units is a reasonable upper bound for a non-essential good in
    # one tick. Tunable design parameter.
    MAX_DISCRETIONARY_DEMAND = 5.0

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

        # Demand: essential needs + discretionary spending
        for cat in good_categories:
            code = cat["code"]
            current = inv["holdings"].get(code, 0.0)

            if cat["is_essential"]:
                need = max(0.0, subsistence_need - current)
                if need > 0:
                    wants[code] = need
                    total_demand[code] = total_demand.get(code, 0.0) + need
            else:
                # Non-essential demand proportional to cash / (price * elasticity),
                # capped at MAX_DISCRETIONARY_DEMAND per agent per tick.
                # The cap prevents absurdly high demand when prices are very
                # low relative to cash holdings in small simulations.
                price = max(market_prices.get(code, 1.0), EPSILON)
                elasticity = max(cat.get("price_elasticity", 1.0), 0.1)
                cash = inv.get("cash_amount", 0.0)
                discretionary = min(
                    MAX_DISCRETIONARY_DEMAND,
                    (cash * 0.1) / (price * elasticity),
                )
                if discretionary > 0.01:
                    wants[code] = discretionary
                    total_demand[code] = total_demand.get(code, 0.0) + discretionary

        agent_orders.append({
            "agent_id": inv["agent_id"],
            "offers": offers,
            "wants": wants,
        })

    return total_supply, total_demand, agent_orders


def execute_trades(
    agent_orders: list[dict],
    equilibrium_prices: dict[str, float],
    total_supply: dict[str, float],
    total_demand: dict[str, float],
) -> list[dict]:
    """Execute trades at equilibrium prices.

    When demand exceeds supply, each buyer gets a proportional share.
    When supply exceeds demand, each seller sells a proportional share.

    Returns list of trade records with keys: buyer_id, seller_id,
    good_code, quantity, price, total.
    """
    trades: list[dict] = []

    for good_code in set(list(total_supply.keys()) + list(total_demand.keys())):
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

        # Collect sellers and buyers
        sellers = [
            (o["agent_id"], o["offers"].get(good_code, 0.0))
            for o in agent_orders
            if o["offers"].get(good_code, 0.0) > 0
        ]
        buyers = [
            (o["agent_id"], o["wants"].get(good_code, 0.0))
            for o in agent_orders
            if o["wants"].get(good_code, 0.0) > 0
        ]

        # Simple proportional matching
        for buyer_id, want_qty in buyers:
            actual_buy = want_qty * demand_ratio
            if actual_buy < 0.001:
                continue
            # Match with sellers proportionally
            for seller_id, offer_qty in sellers:
                actual_sell = offer_qty * supply_ratio
                if actual_sell < 0.001:
                    continue
                share = min(actual_buy, actual_sell)
                if share > 0.001:
                    trades.append({
                        "buyer_id": buyer_id,
                        "seller_id": seller_id,
                        "good_code": good_code,
                        "quantity": share,
                        "price": price,
                        "total": share * price,
                    })

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
        agent_inventories, good_categories, market_prices,
    )
    equilibrium_prices, converged = tatonnement_prices(
        market_prices, total_supply, total_demand,
    )
    trades = execute_trades(
        agent_orders, equilibrium_prices, total_supply, total_demand,
    )
    return equilibrium_prices, trades, total_supply, total_demand

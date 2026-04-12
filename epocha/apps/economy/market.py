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
ADJUSTMENT_RATE = 0.1
MAX_ITERATIONS = 50
CONVERGENCE_THRESHOLD = 0.01
EPSILON = 0.001  # prevents division by zero in supply
# Maximum price relative to starting price. Prevents runaway prices
# when supply is at epsilon floor. Tunable design parameter.
# A 100x price increase represents hyperinflation and should trigger
# crisis events rather than further price escalation.
MAX_PRICE_RATIO = 100.0


def tatonnement_prices(
    current_prices: dict[str, float],
    total_supply: dict[str, float],
    total_demand: dict[str, float],
    *,
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
        adjustment_rate: Step size per iteration. Tunable, default 0.1.
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
            supply = max(total_supply.get(good, 0.0), EPSILON)
            demand = total_demand.get(good, 0.0)
            excess = demand - supply

            relative_excess = abs(excess) / supply
            if relative_excess > convergence_threshold:
                converged = False

            adjustment = adjustment_rate * excess / supply
            new_price = max(EPSILON, prices[good] * (1.0 + adjustment))
            # Cap at MAX_PRICE_RATIO * initial price to prevent runaway
            # prices when supply is at the epsilon floor. A 100x increase
            # represents hyperinflation; further escalation would be
            # handled by crisis events, not price adjustment.
            max_price = initial_prices.get(good, 1.0) * MAX_PRICE_RATIO
            prices[good] = min(new_price, max_price)

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
                # Non-essential demand proportional to cash / (price * elasticity)
                price = max(market_prices.get(code, 1.0), EPSILON)
                elasticity = max(cat.get("price_elasticity", 1.0), 0.1)
                cash = inv.get("cash_amount", 0.0)
                discretionary = (cash * 0.1) / (price * elasticity)
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

"""Economic distribution: rent, wages, and taxation.

Conservation model (approach A, CM-1 / distribution PROD-2 remediation):
a zone's production for a tick has a single output value V = sum over
goods of (zone_production[good] * market_price[good]). Classical
economics and modern national-income accounting agree that V is
PARTITIONED among the factors of production, not paid out in full to
each factor independently:

    V = rent + wages + profit

Source: Ricardo, D. (1817). On the Principles of Political Economy and
Taxation, Chapter 2 ("On Rent"). Ricardo's tripartite division of the
annual produce of the land among landlords (rent), labourers (wages),
and capitalists (profits) is the classical statement of this identity.
The modern restatement is the income approach to GDP (national income
= compensation of employees + rents + profits + interest; see e.g. the
"National Income and Product Accounts" methodology).

This module implements the partition as three tunable shares that sum
to 1: wage_share (labor), rent_share (land), and profit_share (capital
residual = 1 - wage_share - rent_share). Each of compute_rent,
compute_wages, and compute_profit distributes its OWN share of V, so
calling all three and crediting the results as cash transfers keeps
the tick's money supply conserved: the total newly credited cash
equals V exactly, not a multiple of it (see engine.py steps 4/5/5b).

Rent: emergent from zone production proportional to property bonus.
Simplification: proportional to bonus instead of differential surplus
vs marginal land. See spec for detailed rationale.

Wages: share of each producing agent's OWN output value -- the labor
factor income. Property ownership no longer grants a separate "full
value" wage premium (that was the double-counting defect): an owner's
land/capital income is earned through compute_rent/compute_profit
instead, so the same unit of output value is never paid out twice.

Profit: the capital/entrepreneurial residual. For a good with at least
one property claiming a production_bonus share, profit follows the
same proportional-to-bonus allocation as rent (a Property in this
model bundles both land and capital, so its owner captures both
factor incomes). For a good with no property claiming it, there is no
distinct capital owner, so the producing agents retain the residual
themselves (a self-employed producer is their own landlord and
capitalist) -- this also absorbs the otherwise-unclaimed rent_share
for that good, so the partition still sums to exactly V good-by-good.

Taxes: flat income tax on wages + rent, collected into government
treasury. Source for bankruptcy-as-crisis: Doyle, W. (1989). The
Oxford History of the French Revolution.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# Factor-income shares partitioning the zone output value V = rent +
# wages + profit (Ricardo 1817; national-income accounting identity).
# Tunable design parameters, template-sourced in engine.py where a
# template overrides them; these are the fallback defaults.
# wage_share keeps the pre-existing template default (0.6) so simulations
# that do not set "wage_share" in production_config see no change in the
# labor share. rent_share defaults to 0.15 (land); profit_share is the
# residual 1 - wage_share - rent_share = 0.25 (capital).
_DEFAULT_WAGE_SHARE = 0.6
_DEFAULT_RENT_SHARE = 0.15
_DEFAULT_PROFIT_SHARE = 1.0 - _DEFAULT_WAGE_SHARE - _DEFAULT_RENT_SHARE


def _total_bonus_per_good(properties: list[dict]) -> dict[str, float]:
    """Sum production_bonus across all properties in a zone, per good.

    Shared by compute_rent and compute_profit: both allocate a share of
    output value among property owners in proportion to their bonus
    share of this per-good total (DRY -- avoids duplicating the
    accumulation loop in two places with the risk of it drifting out
    of sync).
    """
    total_bonus: dict[str, float] = {}
    for prop in properties:
        for good, bonus in prop.get("production_bonus", {}).items():
            total_bonus[good] = total_bonus.get(good, 0.0) + bonus
    return total_bonus


def _distribute_proportional_to_bonus(
    zone_production: dict[str, float],
    properties: list[dict],
    prices: dict[str, float],
    total_bonus: dict[str, float],
    value_share: float,
) -> dict[int, float]:
    """Distribute value_share * V_good among property owners of each good.

    For every good with a positive total production_bonus in the zone,
    each owner receives value_share * production[good] * price[good]
    scaled by (owner's bonus for good / total bonus for good). Owners
    with multiple properties accumulate across all of them. Goods with
    no property claiming a bonus (total_bonus[good] == 0) contribute
    nothing here -- the caller is responsible for routing that portion
    elsewhere so the overall partition still sums to V (see
    compute_profit's fallback for the goods branch).
    """
    result: dict[int, float] = {}
    for prop in properties:
        owner_id = prop.get("owner_id")
        if owner_id is None:
            continue
        owner_amount = 0.0
        for good, bonus in prop.get("production_bonus", {}).items():
            production = zone_production.get(good, 0.0)
            price = prices.get(good, 0.0)
            zone_total = total_bonus.get(good, 0.0)
            if zone_total > 0 and production > 0:
                share = bonus / zone_total
                owner_amount += production * price * value_share * share
        result[owner_id] = result.get(owner_id, 0.0) + owner_amount
    return result


def compute_rent(
    zone_production: dict[str, float],
    properties: list[dict],
    prices: dict[str, float],
    rent_share: float = _DEFAULT_RENT_SHARE,
) -> dict[int, float]:
    """Compute rent (land factor income) for each property owner in a zone.

    Rent for a property = rent_share * (zone output of good * property's
    share of total bonus for that good) * market price of that good,
    summed over the goods the property claims a bonus for.

    This is a simplified Ricardian model: rent emerges proportionally
    from production bonus rather than being computed as differential
    surplus over marginal land (Ricardo 1817). The qualitative behavior
    is correct (productive property yields more rent). rent_share
    bounds rent to its slice of the output value V so that rent no
    longer equals the full output value on its own (CM-1 fix -- see
    module docstring for the conservation identity V = rent + wages +
    profit).

    Args:
        zone_production: {good_code: total_quantity_produced_in_zone}
        properties: list of dicts with owner_id, production_bonus
        prices: {good_code: market_price}
        rent_share: fraction of each good's output value allocated to
            land (property owners). Tunable design parameter, default
            0.15. Template-sourced via engine.py's production_config.

    Returns:
        {owner_id: total_rent_in_currency}. Owners with multiple
        properties accumulate rent from all of them. Goods with no
        property claiming a bonus contribute no rent (see compute_profit
        for where that portion of the value goes instead).
    """
    if not properties:
        return {}
    total_bonus = _total_bonus_per_good(properties)
    return _distribute_proportional_to_bonus(
        zone_production, properties, prices, total_bonus, rent_share
    )


def compute_wages(
    agent_outputs: list[dict],
    prices: dict[str, float],
    wage_share: float = _DEFAULT_WAGE_SHARE,
) -> dict[int, float]:
    """Compute wages (labor factor income) for agents based on their output.

    Every producing agent -- owner or not -- earns wage_share of the
    value of their OWN production. Property ownership no longer grants
    a separate full-value payout here: an owner's land and capital
    income are earned through compute_rent and compute_profit instead.
    Paying an owner both wage_share*value here AND rent/profit on the
    same output was the CM-1 double-counting defect (an owner used to
    receive full value as "wage" plus a full-value rent share
    independently); this function now only ever pays the bounded labor
    share, regardless of ownership.

    Args:
        agent_outputs: list of {agent_id, good_code, quantity}
        prices: {good_code: market_price}
        wage_share: fraction of output value paid as wages (0-1).
            Tunable design parameter, default 0.6.

    Returns:
        {agent_id: wage_amount}
    """
    wages: dict[int, float] = {}
    for output in agent_outputs:
        agent_id = output["agent_id"]
        good = output["good_code"]
        qty = output["quantity"]
        price = prices.get(good, 0.0)
        wages[agent_id] = wages.get(agent_id, 0.0) + qty * price * wage_share

    return wages


def compute_profit(
    zone_production: dict[str, float],
    properties: list[dict],
    agent_outputs: list[dict],
    prices: dict[str, float],
    profit_share: float = _DEFAULT_PROFIT_SHARE,
    rent_share: float = _DEFAULT_RENT_SHARE,
) -> dict[int, float]:
    """Compute profit (capital/entrepreneurial residual factor income).

    profit_share of each good's output value is credited to whoever
    supplies capital for that good's production:

    - if at least one property in the zone claims a production_bonus
      for the good, profit is split among those property owners in
      proportion to their bonus share, mirroring compute_rent's
      allocation (a Property in this model bundles both land and
      capital, so its owner captures both rent and profit);
    - otherwise (no property claims the good), the good has no
      distinct capital owner, so the producing agents retain the
      residual themselves, proportional to their own output value.
      In this fallback case profit also absorbs the rent_share
      portion that compute_rent leaves uncredited for that good
      (there is no landlord to pay), so wages + rent + profit still
      sum to exactly V good-by-good -- see the module docstring.

    Args:
        zone_production: {good_code: total_quantity_produced_in_zone}
        properties: list of dicts with owner_id, production_bonus
        agent_outputs: list of {agent_id, good_code, quantity}
        prices: {good_code: market_price}
        profit_share: fraction of each good's output value allocated
            to capital. Tunable design parameter, default 0.25
            (residual of wage_share=0.6 + rent_share=0.15).
        rent_share: the rent_share used elsewhere in this tick's
            partition. Needed here only to size the fallback (no
            landlord) case correctly; must match the rent_share passed
            to compute_rent for the same tick or the partition will
            not sum to V.

    Returns:
        {agent_id_or_owner_id: profit_amount}
    """
    total_bonus = _total_bonus_per_good(properties)
    profit = dict(
        _distribute_proportional_to_bonus(
            zone_production, properties, prices, total_bonus, profit_share
        )
    )

    for output in agent_outputs:
        good = output["good_code"]
        if total_bonus.get(good, 0.0) > 0.0:
            # Already credited to the property owner(s) above.
            continue
        agent_id = output["agent_id"]
        qty = output["quantity"]
        price = prices.get(good, 0.0)
        value = qty * price
        # No landlord for this good: the producer absorbs both the
        # capital residual and the otherwise-unclaimed land share.
        profit[agent_id] = profit.get(agent_id, 0.0) + value * (rent_share + profit_share)

    return profit


def partition_output_value(
    zone_production: dict[str, float],
    properties: list[dict],
    agent_outputs: list[dict],
    prices: dict[str, float],
    wage_share: float = _DEFAULT_WAGE_SHARE,
    rent_share: float = _DEFAULT_RENT_SHARE,
    profit_share: float | None = None,
) -> dict[str, dict[int, float]]:
    """Partition a zone's output value V into rent + wages + profit.

    V = sum over goods of (zone_production[good] * prices[good]). This
    function is the single entry point that guarantees
    sum(rent.values()) + sum(wages.values()) + sum(profit.values()) == V
    (within floating-point epsilon) -- see compute_rent, compute_wages,
    and compute_profit for the per-factor allocation rules, and the
    module docstring for the classical/national-accounting source.

    Args:
        zone_production: {good_code: total_quantity_produced_in_zone}
        properties: list of dicts with owner_id, production_bonus
        agent_outputs: list of {agent_id, good_code, quantity}
        prices: {good_code: market_price}
        wage_share: labor's share of V. Default 0.6.
        rent_share: land's share of V. Default 0.15.
        profit_share: capital's share of V. Defaults to the residual
            1 - wage_share - rent_share. If wage_share + rent_share
            exceeds 1 (a misconfigured template), rent_share is
            clamped to 1 - wage_share and profit_share to 0 -- logged
            as a warning, since a share partition cannot exceed 1.

    Returns:
        {"rent": {owner_id: amount}, "wages": {agent_id: amount},
        "profit": {agent_id_or_owner_id: amount}}.
    """
    if wage_share + rent_share > 1.0:
        logger.warning(
            "partition_output_value: wage_share(%.3f) + rent_share(%.3f) "
            "exceeds 1.0; clamping rent_share to the residual and "
            "profit_share to 0.",
            wage_share,
            rent_share,
        )
        rent_share = max(0.0, 1.0 - wage_share)
        profit_share = 0.0
    elif profit_share is None:
        profit_share = 1.0 - wage_share - rent_share

    return {
        "rent": compute_rent(zone_production, properties, prices, rent_share),
        "wages": compute_wages(agent_outputs, prices, wage_share),
        "profit": compute_profit(
            zone_production, properties, agent_outputs, prices, profit_share, rent_share
        ),
    }


def compute_taxes(
    agent_incomes: dict[int, float],
    tax_rate: float,
) -> dict:
    """Compute flat income tax for all agents.

    Args:
        agent_incomes: {agent_id: taxable_income} (wages + rent)
        tax_rate: flat rate (0.0-1.0)

    Returns:
        {"agent_taxes": {agent_id: tax_amount}, "total_revenue": float}
    """
    agent_taxes: dict[int, float] = {}
    total_revenue = 0.0

    for agent_id, income in agent_incomes.items():
        tax = income * tax_rate
        agent_taxes[agent_id] = tax
        total_revenue += tax

    return {"agent_taxes": agent_taxes, "total_revenue": total_revenue}

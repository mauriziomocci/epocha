"""Economic distribution: rent, wages, and taxation.

Rent: emergent from zone production proportional to property bonus.
Source: Ricardo, D. (1817). On the Principles of Political Economy.
Simplification: proportional to bonus instead of differential surplus
vs marginal land. See spec for detailed rationale.

Wages: share of production value for non-property-owners.
In spec 1 this is a fixed share; spec 2 replaces with matching theory.

Taxes: flat income tax on wages + rent, collected into government treasury.
Source for bankruptcy-as-crisis: Doyle, W. (1989). The Oxford History
of the French Revolution.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def compute_rent(
    zone_production: dict[str, float],
    properties: list[dict],
    prices: dict[str, float],
) -> dict[int, float]:
    """Compute rent for each property owner in a zone.

    Rent for a property = (zone output of good * property's share of
    total bonus for that good) * market price of that good.

    This is a simplified Ricardian model: rent emerges proportionally
    from production bonus rather than being computed as differential
    surplus over marginal land (Ricardo 1817). The qualitative behavior
    is correct (productive property yields more rent). See spec for
    the full discussion of this simplification.

    Args:
        zone_production: {good_code: total_quantity_produced_in_zone}
        properties: list of dicts with owner_id, production_bonus
        prices: {good_code: market_price}

    Returns:
        {owner_id: total_rent_in_currency}. Owners with multiple
        properties accumulate rent from all of them.
    """
    if not properties:
        return {}

    # Sum total bonus per good across all properties in zone
    total_bonus: dict[str, float] = {}
    for prop in properties:
        for good, bonus in prop.get("production_bonus", {}).items():
            total_bonus[good] = total_bonus.get(good, 0.0) + bonus

    rents: dict[int, float] = {}
    for prop in properties:
        owner_id = prop.get("owner_id")
        if owner_id is None:
            continue
        prop_rent = 0.0
        for good, bonus in prop.get("production_bonus", {}).items():
            production = zone_production.get(good, 0.0)
            price = prices.get(good, 0.0)
            zone_total = total_bonus.get(good, 0.0)
            if zone_total > 0 and production > 0:
                share = bonus / zone_total
                prop_rent += production * share * price
        rents[owner_id] = rents.get(owner_id, 0.0) + prop_rent

    return rents


def compute_wages(
    agent_outputs: list[dict],
    prices: dict[str, float],
    wage_share: float = 0.6,
) -> dict[int, float]:
    """Compute wages for agents based on their production output.

    Property owners keep the full value of their output. Non-owners
    receive wage_share of the output value.

    wage_share is a template parameter (default 0.6 for pre-industrial).
    In spec 1 this is fixed; spec 2 replaces with Mortensen-Pissarides
    matching theory.

    Args:
        agent_outputs: list of {agent_id, good_code, quantity, owns_property}
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
        value = qty * price

        if output.get("owns_property", False):
            # Owner keeps full value
            wages[agent_id] = wages.get(agent_id, 0.0) + value
        else:
            # Worker gets wage_share
            wages[agent_id] = wages.get(agent_id, 0.0) + value * wage_share

    return wages


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

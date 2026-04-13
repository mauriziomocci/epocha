"""Build economic context strings for agent decision prompts.

Provides each agent with a summary of their financial situation and
local market conditions so the LLM can make economically informed
decisions.
"""
from __future__ import annotations

import logging

from .models import (
    AgentInventory,
    Currency,
    PriceHistory,
    Property,
    ZoneEconomy,
)

logger = logging.getLogger(__name__)


def build_economic_context(agent, tick: int) -> str | None:
    """Build a human-readable economic context string for an agent.

    Returns None if the simulation has no economy data (currencies not
    initialized), allowing the decision pipeline to skip the block.

    Queries:
    - AgentInventory (cash + holdings)
    - Property (agent's owned properties)
    - ZoneEconomy (local market prices)
    - PriceHistory (previous tick for % change computation)
    - Currency (symbol for display)

    The returned string is designed to be injected into the LLM prompt
    alongside other context blocks (political, zone, reputation).
    """
    simulation = agent.simulation

    # Get primary currency
    currency = (
        Currency.objects.filter(simulation=simulation, is_primary=True).first()
    )
    if not currency:
        return None

    symbol = currency.symbol

    # Get agent inventory
    try:
        inventory = agent.inventory
    except AgentInventory.DoesNotExist:
        return None

    cash_amount = sum(inventory.cash.values())

    # Holdings summary
    holdings_lines = []
    for good_code, qty in sorted(inventory.holdings.items()):
        if qty > 0:
            holdings_lines.append(f"{good_code} ({qty:.0f} units)")

    holdings_text = ", ".join(holdings_lines) if holdings_lines else "nothing"

    # Properties
    properties = list(
        Property.objects.filter(
            owner=agent, owner_type="agent",
        ).values_list("property_type", flat=True)
    )
    property_count = len(properties)
    property_text = f"{property_count} ({', '.join(properties)})" if properties else "none"

    # Total wealth (already computed on agent model)
    total_wealth = agent.wealth

    # Market prices in the agent's zone
    market_lines = []
    if agent.zone_id:
        try:
            ze = ZoneEconomy.objects.get(zone_id=agent.zone_id)
        except ZoneEconomy.DoesNotExist:
            ze = None

        if ze and ze.market_prices:
            # Get previous tick prices for % change
            prev_prices = {}
            if tick > 0:
                prev_records = PriceHistory.objects.filter(
                    zone_economy=ze, tick=tick - 1,
                )
                prev_prices = {ph.good_code: ph.price for ph in prev_records}

            zone_name = ze.zone.name if ze.zone else "your zone"

            for good_code, price in sorted(ze.market_prices.items()):
                prev = prev_prices.get(good_code)
                if prev and prev > 0:
                    pct_change = ((price - prev) / prev) * 100
                    if abs(pct_change) < 1.0:
                        trend = "stable"
                    elif pct_change > 0:
                        trend = f"up {pct_change:.0f}%"
                    else:
                        trend = f"down {abs(pct_change):.0f}%"
                else:
                    trend = "no prior data"

                market_lines.append(
                    f"- {good_code.capitalize()}: {price:.1f} {symbol}/unit ({trend})"
                )

    parts = [
        "Your economic situation:",
        f"- Cash: {cash_amount:.0f} {symbol}",
        f"- Inventory: {holdings_text}",
        f"- Properties: {property_text}",
        f"- Total wealth: {total_wealth:.0f} {symbol}",
    ]

    if market_lines:
        zone_label = ze.zone.name if ze and ze.zone else "your zone"
        parts.append(f"\nMarket in {zone_label}:")
        parts.extend(market_lines)

    return "\n".join(parts)

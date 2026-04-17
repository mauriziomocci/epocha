"""Build economic context strings for agent decision prompts.

Provides each agent with a summary of their financial situation and
local market conditions so the LLM can make economically informed
decisions. Extended with behavioral blocks: price expectations
(Nerlove 1958), debt situation with Minsky (1986) classification,
and banking system state (Diamond & Dybvig 1983).
"""
from __future__ import annotations

import logging

from .models import (
    AgentExpectation,
    AgentInventory,
    BankingState,
    Currency,
    Loan,
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

    # Behavioral blocks: expectations, debt, banking
    expectations_block = _build_expectations_block(agent)
    if expectations_block:
        parts.append("")
        parts.append(expectations_block)

    debt_block = _build_debt_block(agent, simulation, tick, symbol)
    if debt_block:
        parts.append("")
        parts.append(debt_block)

    banking_block = _build_banking_block(simulation)
    if banking_block:
        parts.append("")
        parts.append(banking_block)

    return "\n".join(parts)


def _confidence_word(confidence: float) -> str:
    """Map a 0-1 confidence float to a human-readable word.

    Thresholds: high > 0.7, moderate 0.4-0.7, low < 0.4.
    """
    if confidence > 0.7:
        return "high"
    elif confidence >= 0.4:
        return "moderate"
    return "low"


def _build_expectations_block(agent) -> str | None:
    """Build a context block showing the agent's price expectations.

    Uses AgentExpectation records (Nerlove 1958 adaptive expectations).
    For each good the agent tracks, shows the trend direction, the
    percentage deviation of the expected price from the current zone
    market price, and the agent's confidence level.

    Returns None if the agent has no expectations.
    """
    expectations = list(
        AgentExpectation.objects.filter(agent=agent).order_by("good_code")
    )
    if not expectations:
        return None

    # Fetch current zone prices for deviation computation
    zone_prices: dict[str, float] = {}
    if agent.zone_id:
        try:
            ze = ZoneEconomy.objects.get(zone_id=agent.zone_id)
            zone_prices = ze.market_prices or {}
        except ZoneEconomy.DoesNotExist:
            pass

    lines = ["Price expectations (your assessment):"]
    for exp in expectations:
        direction = exp.trend_direction.upper()
        actual_price = zone_prices.get(exp.good_code)
        if actual_price and actual_price > 0:
            pct_dev = ((exp.expected_price - actual_price) / actual_price) * 100
            sign = "+" if pct_dev >= 0 else ""
            dev_text = f"{sign}{pct_dev:.0f}% expected"
        else:
            dev_text = f"expected {exp.expected_price:.1f}"

        conf = _confidence_word(exp.confidence)
        good_label = exp.good_code.capitalize()
        lines.append(f"- {good_label}: {direction} ({dev_text}), confidence: {conf}")

    return "\n".join(lines)


def _build_debt_block(agent, simulation, tick: int, symbol: str) -> str | None:
    """Build a context block showing the agent's debt situation.

    Includes active loan summary, interest due, debt-to-wealth ratio
    with a qualitative label, Minsky (1986) financing classification,
    and credit availability from the best unpledged property.

    Returns None if the agent has no active loans AND no unpledged
    property (nothing useful to report).
    """
    active_loans = list(
        Loan.objects.filter(
            simulation=simulation,
            borrower=agent,
            status="active",
        )
    )

    # Find best unpledged property for credit availability
    unpledged_properties = list(
        Property.objects.filter(
            owner=agent,
            owner_type="agent",
        ).exclude(
            collateralized_loans__status="active",
        ).order_by("-value")
    )
    best_property = unpledged_properties[0] if unpledged_properties else None

    # Skip block if nothing to report
    if not active_loans and not best_property:
        return None

    lines = ["Your debt situation:"]

    if active_loans:
        total_balance = sum(loan.remaining_balance for loan in active_loans)
        interest_due = sum(
            loan.remaining_balance * loan.interest_rate for loan in active_loans
        )
        wealth = max(agent.wealth, 1.0)
        debt_ratio = total_balance / wealth

        if debt_ratio < 0.3:
            ratio_word = "safe"
        elif debt_ratio <= 0.6:
            ratio_word = "moderate"
        else:
            ratio_word = "dangerous"

        lines.append(
            f"- Active loans: {len(active_loans)} "
            f"(total balance: {total_balance:.0f} {symbol})"
        )
        lines.append(f"- Interest due this tick: {interest_due:.1f} {symbol}")
        lines.append(
            f"- Debt-to-wealth ratio: {debt_ratio:.0%} ({ratio_word})"
        )

        # Lazy import to avoid circular dependency between context and credit
        from .credit import classify_minsky_stage

        minsky_descriptions = {
            "hedge": "fully covered, safe",
            "speculative": "can pay interest, will need to refinance",
            "ponzi": "cannot cover interest, critical",
        }
        minsky_stage = classify_minsky_stage(agent, simulation, tick)
        minsky_desc = minsky_descriptions.get(minsky_stage, minsky_stage)
        lines.append(f"- Financial position: {minsky_stage} ({minsky_desc})")
    else:
        lines.append("- No active loans")

    # Credit availability from best unpledged property
    if best_property:
        from .credit import evaluate_credit_request

        test_amount = best_property.value / 2.0
        approved, result = evaluate_credit_request(
            borrower=agent,
            amount=test_amount,
            collateral_property=best_property,
            simulation=simulation,
        )
        if approved:
            lines.append(
                f"- Credit available: up to {test_amount:.0f} {symbol} "
                f"at {result:.1%} interest (secured by your {best_property.name})"
            )

    return "\n".join(lines)


def _build_banking_block(simulation) -> str | None:
    """Build a context block showing the banking system state.

    Shows solvency status, confidence level, and base interest rate
    from the BankingState model (Diamond & Dybvig 1983).

    Returns None if no BankingState exists for the simulation.
    """
    try:
        bs = BankingState.objects.get(simulation=simulation)
    except BankingState.DoesNotExist:
        return None

    if bs.is_solvent:
        status = "solvent"
    else:
        status = "INSOLVENT"

    conf_word = _confidence_word(bs.confidence_index)
    # Use uppercase for low confidence to signal urgency
    if conf_word == "low":
        conf_text = f"LOW ({bs.confidence_index:.1f})"
    else:
        conf_text = f"confidence {conf_word}"

    return (
        f"Banking system: {status}, {conf_text}, "
        f"base rate {bs.base_interest_rate:.1%}"
    )

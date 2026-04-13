"""Banking system: fractional reserve, interest rate adjustment, solvency.

Implements a simplified aggregate banking sector (one "bank" per
simulation) that manages deposits, loans, and the base interest rate.

Interest rate adjustment follows a Wicksellian mechanism (Wicksell 1898):
the rate rises when credit demand exceeds supply and falls when supply
exceeds demand. The natural rate of interest is the rate that balances
the credit market -- this implementation converges toward it over time.

Solvency checking follows Diamond & Dybvig (1983): when reserves fall
below the required ratio, confidence erodes and the banking system
enters a credit freeze.

References:
- Wicksell, K. (1898). Interest and Prices (Geldzins und Gueterpreise).
  Jena: Gustav Fischer. English translation by R.F. Kahn (1936),
  Macmillan.
- Diamond, D.W. & Dybvig, P.H. (1983). Bank Runs, Deposit Insurance,
  and Liquidity. Journal of Political Economy 91(3), 401-419.
"""

from __future__ import annotations

import logging

from django.db.models import Sum

from .models import (
    BankingState,
    EconomyTemplate,
    Loan,
)

logger = logging.getLogger(__name__)


def _get_banking_config(simulation) -> dict:
    """Retrieve banking configuration from the simulation's config.

    Falls back to conservative defaults when the config is missing.
    """
    sim_config = simulation.config or {}
    banking_config = sim_config.get("banking_config")
    if banking_config:
        return banking_config

    # Fall back to template config
    templates = EconomyTemplate.objects.all()[:1]
    if templates:
        template_config = templates[0].config or {}
        banking_config = template_config.get("banking_config", {})
        if banking_config:
            return banking_config

    return {
        "initial_deposits": 5000.0,
        "base_interest_rate": 0.05,
        "reserve_ratio": 0.10,
    }


def _get_credit_config(simulation) -> dict:
    """Retrieve credit configuration from the simulation's config."""
    sim_config = simulation.config or {}
    return sim_config.get("credit_config", {})


def initialize_banking(simulation) -> BankingState:
    """Create or retrieve the BankingState for a simulation.

    Initializes the banking system with parameters from the simulation's
    banking_config (set during economy initialization from the template).
    If a BankingState already exists, returns it unchanged to maintain
    idempotency.

    Args:
        simulation: The simulation instance.

    Returns:
        The BankingState instance.
    """
    try:
        return BankingState.objects.get(simulation=simulation)
    except BankingState.DoesNotExist:
        pass

    config = _get_banking_config(simulation)

    banking_state = BankingState.objects.create(
        simulation=simulation,
        total_deposits=config.get("initial_deposits", 5000.0),
        total_loans_outstanding=0.0,
        reserve_ratio=config.get("reserve_ratio", 0.10),
        base_interest_rate=config.get("base_interest_rate", 0.05),
        is_solvent=True,
        confidence_index=1.0,
    )

    logger.info(
        "Banking initialized for simulation %d: deposits=%.1f, rate=%.3f, reserve=%.2f",
        simulation.id,
        banking_state.total_deposits,
        banking_state.base_interest_rate,
        banking_state.reserve_ratio,
    )

    return banking_state


def adjust_interest_rate(simulation, tick: int) -> None:
    """Adjust the base interest rate toward credit market equilibrium.

    Implements a Wicksellian adjustment process (Wicksell 1898): the
    interest rate rises when credit demand exceeds available credit
    supply, and falls when supply exceeds demand. Over time, this
    converges to the "natural rate" that balances saving and investment.

    Credit demand is approximated by the number of agents with a
    debt-to-wealth ratio above 0.3 who could benefit from additional
    borrowing. This is a simplification -- the full Wicksellian model
    operates on the gap between the market rate and the natural rate
    of return on capital.

    Credit supply is the unused lending capacity of the fractional
    reserve system: deposits * (1 - reserve_ratio) - outstanding loans.

    The adjustment rate (default 0.02) determines how quickly the
    rate responds to imbalances. Tunable design parameter.

    Args:
        simulation: The simulation instance.
        tick: Current simulation tick.
    """
    try:
        bs = BankingState.objects.get(simulation=simulation)
    except BankingState.DoesNotExist:
        return

    credit_config = _get_credit_config(simulation)
    adj_rate = credit_config.get("credit_adj_rate", 0.02)

    # Approximate credit demand: count agents with debt_ratio > 0.3
    # and sum their potential borrowing needs.
    from epocha.apps.agents.models import Agent

    agents = Agent.objects.filter(
        simulation=simulation,
        is_alive=True,
    )

    credit_demand = 0.0
    for agent in agents:
        agent_debt_agg = Loan.objects.filter(
            simulation=simulation,
            borrower=agent,
            status="active",
        ).aggregate(total=Sum("remaining_balance"))
        agent_debt = agent_debt_agg["total"] or 0.0
        wealth = max(agent.wealth, 1.0)
        debt_ratio = agent_debt / wealth

        if debt_ratio > 0.3:
            # Agent wants more credit -- approximate demand as their
            # current debt (they would borrow more if available)
            credit_demand += agent_debt

    # Credit supply: unused lending capacity
    credit_supply = max(
        0.0,
        bs.total_deposits * (1.0 - bs.reserve_ratio) - bs.total_loans_outstanding,
    )

    # Wicksell (1898): rate adjusts proportionally to excess demand
    denominator = max(credit_supply, 0.001)
    r_old = bs.base_interest_rate
    r_new = r_old * (1.0 + adj_rate * (credit_demand - credit_supply) / denominator)

    # Clamp to [0.5%, 50%]. These bounds prevent the rate from
    # reaching zero (liquidity trap) or becoming unreasonably high.
    # Tunable design parameters.
    r_new = max(0.005, min(0.5, r_new))

    bs.base_interest_rate = r_new
    bs.save(update_fields=["base_interest_rate"])

    logger.debug(
        "Interest rate adjusted: %.4f -> %.4f (demand=%.1f, supply=%.1f)",
        r_old,
        r_new,
        credit_demand,
        credit_supply,
    )


def check_solvency(simulation) -> None:
    """Check whether the banking system remains solvent.

    Solvency condition: the banking system must hold enough reserves
    to cover the required reserve ratio. In accounting terms:

        reserves = total_deposits - total_loans_outstanding
        required_reserves = total_deposits * reserve_ratio

    The bank is solvent when reserves >= required_reserves, which
    simplifies to:

        total_deposits * reserve_ratio <= total_deposits - total_loans_outstanding

    When insolvent, confidence_index drops by 0.1 per tick. This
    models the self-fulfilling prophecy dynamic from Diamond & Dybvig
    (1983): depositors who expect the bank to fail withdraw their
    deposits, making failure more likely. The 0.1 decrement is a
    tunable design parameter -- faster decay produces sharper crises.

    When the bank returns to solvency, confidence recovers at 0.05
    per tick (slower than the decline, reflecting that trust is
    easier to lose than to rebuild). Tunable design parameter.

    Args:
        simulation: The simulation instance.
    """
    try:
        bs = BankingState.objects.get(simulation=simulation)
    except BankingState.DoesNotExist:
        return

    reserves = bs.total_deposits - bs.total_loans_outstanding
    required_reserves = bs.total_deposits * bs.reserve_ratio

    if reserves >= required_reserves:
        if not bs.is_solvent:
            logger.info(
                "Banking system recovered solvency (simulation %d)",
                simulation.id,
            )
        bs.is_solvent = True
        # Confidence recovery: slower than decline (trust asymmetry)
        bs.confidence_index = min(1.0, bs.confidence_index + 0.05)
    else:
        bs.is_solvent = False
        # Confidence decline: Diamond & Dybvig (1983) bank run dynamic
        bs.confidence_index = max(0.0, bs.confidence_index - 0.1)
        logger.warning(
            "Banking system INSOLVENT (simulation %d): "
            "reserves=%.1f, required=%.1f, confidence=%.2f",
            simulation.id,
            reserves,
            required_reserves,
            bs.confidence_index,
        )

    bs.save(update_fields=["is_solvent", "confidence_index"])


def compute_actual_multiplier(banking_state: BankingState) -> float:
    """Compute the observed money multiplier.

    The theoretical maximum multiplier in fractional reserve banking
    is 1 / reserve_ratio. The actual multiplier is the ratio of
    outstanding loans to deposits, which is always less than or equal
    to the theoretical maximum (unless the bank is overleveraged).

    This metric is useful for monitoring systemic risk: when the
    actual multiplier approaches the theoretical maximum, the banking
    system has little unused lending capacity.

    Args:
        banking_state: The BankingState instance.

    Returns:
        The actual money multiplier (loans / deposits).
    """
    return banking_state.total_loans_outstanding / max(
        banking_state.total_deposits,
        1.0,
    )

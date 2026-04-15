"""Credit market lifecycle: loan creation, servicing, maturity, default, cascade.

Implements the credit subsystem for the economy engine. The core model
is Minsky's Financial Instability Hypothesis (Minsky 1986): agents
move through hedge, speculative, and Ponzi financing stages as debt
accumulates during stable periods, increasing systemic fragility.

Loan pricing follows Stiglitz & Weiss (1981): interest rates include
a risk premium proportional to borrower leverage, reflecting
asymmetric information between lender and borrower.

Default cascades use breadth-first propagation over the debt graph,
capped at a configurable depth to prevent runaway contagion. The
threshold (50% of wealth) is a tunable design parameter -- empirical
calibration would require specific historical crisis data.

References:
- Minsky, H.P. (1986). Stabilizing an Unstable Economy. Yale Univ. Press.
- Stiglitz, J.E. & Weiss, A. (1981). Credit Rationing in Markets with
  Imperfect Information. American Economic Review 71(3), 393-410.
"""

from __future__ import annotations

import logging
from collections import deque

from django.db.models import Sum

from epocha.apps.agents.models import Agent, Memory
from epocha.apps.agents.reputation import update_reputation

from .models import (
    AgentInventory,
    BankingState,
    Currency,
    EconomicLedger,
    EconomyTemplate,
    Loan,
    Property,
)

logger = logging.getLogger(__name__)

# Loss threshold for cascade propagation: if a lender absorbs losses
# exceeding this fraction of their wealth, they default on their own
# loans. Tunable design parameter -- no empirical source; 50% is a
# conservative midpoint that avoids trivial cascades while still
# allowing contagion from severe shocks.
CASCADE_LOSS_THRESHOLD = 0.5


def _get_credit_config(simulation) -> dict:
    """Retrieve credit configuration from the simulation's economy template.

    Falls back to conservative defaults when the template or specific
    keys are missing, ensuring the credit system degrades gracefully
    for simulations created before the behavioral economy was added.
    """
    sim_config = simulation.config or {}
    # First check simulation-level config (set during initialization)
    credit_config = sim_config.get("credit_config")
    if credit_config:
        return credit_config

    # Fall back to template config
    templates = EconomyTemplate.objects.all()[:1]
    if templates:
        template_config = templates[0].config or {}
        credit_config = template_config.get("credit_config", {})
        if credit_config:
            return credit_config

    return {
        "loan_to_value": 0.5,
        "max_rollover": 3,
        "default_loan_duration_ticks": 20,
    }


def _get_banking_config(simulation) -> dict:
    """Retrieve banking configuration from the simulation's config."""
    sim_config = simulation.config or {}
    return sim_config.get("banking_config", {})


def _get_primary_currency(simulation) -> Currency | None:
    """Return the primary currency for the simulation, or None."""
    return Currency.objects.filter(simulation=simulation, is_primary=True).first()


def _get_or_create_inventory(agent: Agent) -> AgentInventory:
    """Return the agent's inventory, creating one if missing."""
    try:
        return agent.inventory
    except AgentInventory.DoesNotExist:
        return AgentInventory.objects.create(
            agent=agent,
            holdings={},
            cash={},
        )


def classify_minsky_stage(agent: Agent, simulation, tick: int) -> str:
    """Classify an agent's financing position per Minsky (1986).

    Minsky's Financial Instability Hypothesis defines three stages:
    - Hedge: income covers both interest and principal. Safe position.
    - Speculative: income covers interest but not principal. The agent
      must refinance (roll over) maturing debt.
    - Ponzi: income does not even cover interest. The agent must borrow
      more just to service existing debt -- the most fragile position.

    Income is approximated from the previous tick's wage and rent
    entries in the economic ledger.

    Reference: Minsky, H.P. (1986). Stabilizing an Unstable Economy.
    Yale University Press, ch. 9.

    Args:
        agent: The agent to classify.
        simulation: The simulation instance.
        tick: Current tick number.

    Returns:
        One of "hedge", "speculative", or "ponzi".
    """
    prev_tick = max(tick - 1, 0)
    income_agg = EconomicLedger.objects.filter(
        simulation=simulation,
        to_agent=agent,
        tick=prev_tick,
        transaction_type__in=["wage", "rent"],
    ).aggregate(total=Sum("total_amount"))
    income = income_agg["total"] or 0.0

    active_loans = Loan.objects.filter(
        simulation=simulation,
        borrower=agent,
        status="active",
    )

    interest_due = sum(
        loan.remaining_balance * loan.interest_rate for loan in active_loans
    )
    principal_due = sum(
        loan.remaining_balance for loan in active_loans.filter(due_at_tick=tick)
    )

    if income >= interest_due + principal_due:
        return "hedge"
    elif income >= interest_due:
        return "speculative"
    else:
        return "ponzi"


def evaluate_credit_request(
    borrower: Agent,
    amount: float,
    collateral_property: Property | None,
    simulation,
) -> tuple[bool, str | float]:
    """Evaluate whether a loan can be issued to the borrower.

    The evaluation implements two mechanisms from Stiglitz & Weiss (1981):
    1. Credit rationing via loan-to-value constraint: the total debt
       cannot exceed the collateral value multiplied by the LTV ratio.
    2. Risk-based pricing: interest rate increases with borrower leverage
       (debt-to-wealth ratio), reflecting the lender's inability to
       perfectly observe borrower risk.

    The risk premium scales linearly with the debt ratio. This is a
    simplification of the Stiglitz-Weiss adverse selection model, which
    would predict a non-linear relationship. The linear form is chosen
    for transparency and because the simulation operates on discrete
    ticks, not continuous time.

    Args:
        borrower: Agent requesting the loan.
        amount: Requested loan amount in primary currency.
        collateral_property: Property pledged as collateral, or None.
        simulation: The simulation instance.

    Returns:
        (True, interest_rate) if approved, or (False, rejection_reason).
    """
    credit_config = _get_credit_config(simulation)
    loan_to_value_ratio = credit_config.get("loan_to_value", 0.5)
    # Risk premium: multiplier applied to debt ratio to compute the
    # interest rate spread. Default 0.5. Tunable design parameter --
    # Stiglitz & Weiss (1981) predict that lenders increase rates with
    # perceived risk, but the magnitude is market-specific.
    risk_premium = credit_config.get("risk_premium", 0.5)

    collateral_value = collateral_property.value if collateral_property else 0.0
    credit_limit = collateral_value * loan_to_value_ratio

    existing_debt_agg = Loan.objects.filter(
        simulation=simulation,
        borrower=borrower,
        status="active",
    ).aggregate(total=Sum("remaining_balance"))
    existing_debt = existing_debt_agg["total"] or 0.0

    if existing_debt + amount > credit_limit:
        return (False, "exceeds credit limit")

    try:
        banking_state = BankingState.objects.get(simulation=simulation)
        if not banking_state.is_solvent:
            return (False, "banking system insolvent")
        base_rate = banking_state.base_interest_rate
    except BankingState.DoesNotExist:
        banking_config = _get_banking_config(simulation)
        base_rate = banking_config.get("base_interest_rate", 0.05)

    wealth = max(borrower.wealth, 1.0)
    debt_ratio = (existing_debt + amount) / wealth

    # Stiglitz & Weiss (1981): rate = base * (1 + risk_premium * debt_ratio)
    interest_rate = base_rate * (1.0 + risk_premium * debt_ratio)

    return (True, interest_rate)


def issue_loan(
    simulation,
    lender: Agent | None,
    borrower: Agent,
    amount: float,
    interest_rate: float,
    collateral: Property | None,
    tick: int,
    duration: int | None = None,
    lender_type: str = "banking",
) -> Loan:
    """Create a loan and transfer funds to the borrower.

    For banking-system loans, increments BankingState.total_loans_outstanding
    to maintain the aggregate balance sheet. For agent-to-agent loans,
    deducts cash from the lender's inventory.

    The cash transfer is recorded in the EconomicLedger as a "trade"
    transaction type (representing a financial transfer). A dedicated
    "loan" transaction type may be introduced in a future iteration.

    Args:
        simulation: The simulation instance.
        lender: Lending agent, or None for banking-system loans.
        borrower: The borrowing agent.
        amount: Loan principal in primary currency.
        interest_rate: Per-tick interest rate.
        collateral: Property pledged as collateral, or None.
        tick: Current simulation tick.
        duration: Loan duration in ticks. None for open-ended loans.
        lender_type: "agent" or "banking".

    Returns:
        The created Loan instance.
    """
    credit_config = _get_credit_config(simulation)
    if duration is None:
        duration = credit_config.get("default_loan_duration_ticks", 20)

    due_at = tick + duration if duration else None

    loan = Loan.objects.create(
        simulation=simulation,
        lender=lender,
        borrower=borrower,
        lender_type=lender_type,
        principal=amount,
        interest_rate=interest_rate,
        remaining_balance=amount,
        collateral=collateral,
        issued_at_tick=tick,
        due_at_tick=due_at,
        status="active",
    )

    # Transfer cash to borrower
    primary_currency = _get_primary_currency(simulation)
    if primary_currency:
        cur_code = primary_currency.code
        borrower_inv = _get_or_create_inventory(borrower)
        borrower_inv.cash[cur_code] = borrower_inv.cash.get(cur_code, 0.0) + amount
        borrower_inv.save(update_fields=["cash"])

        # Deduct from lender if agent-to-agent
        if lender_type == "agent" and lender:
            lender_inv = _get_or_create_inventory(lender)
            lender_inv.cash[cur_code] = lender_inv.cash.get(cur_code, 0.0) - amount
            lender_inv.save(update_fields=["cash"])

        # Record in ledger
        EconomicLedger.objects.create(
            simulation=simulation,
            tick=tick,
            from_agent=lender,
            to_agent=borrower,
            currency=primary_currency,
            total_amount=amount,
            transaction_type="trade",
        )

    # Update banking state for system loans
    if lender_type == "banking":
        try:
            banking_state = BankingState.objects.get(simulation=simulation)
            banking_state.total_loans_outstanding += amount
            banking_state.save(update_fields=["total_loans_outstanding"])
        except BankingState.DoesNotExist:
            pass

    logger.info(
        "Loan issued: %s -> %s, amount=%.1f, rate=%.3f, due_tick=%s",
        lender_type if not lender else lender.name,
        borrower.name,
        amount,
        interest_rate,
        due_at,
    )

    return loan


def service_loans(simulation, tick: int) -> list[int]:
    """Collect interest payments on all active loans.

    For each active loan, computes interest = remaining_balance * interest_rate
    and deducts it from the borrower's cash. If the lender is an agent,
    the interest is credited to their cash. If the borrower cannot pay,
    the loan is marked for default (returned in the list).

    Args:
        simulation: The simulation instance.
        tick: Current simulation tick.

    Returns:
        List of Loan IDs that could not pay interest (candidates for default).
    """
    active_loans = list(
        Loan.objects.filter(
            simulation=simulation,
            status="active",
        ).select_related("borrower", "lender")
    )

    primary_currency = _get_primary_currency(simulation)
    if not primary_currency:
        return []

    cur_code = primary_currency.code
    defaulting_loan_ids = []

    for loan in active_loans:
        interest = loan.remaining_balance * loan.interest_rate
        if interest <= 0:
            continue

        borrower_inv = _get_or_create_inventory(loan.borrower)
        borrower_cash = borrower_inv.cash.get(cur_code, 0.0)

        if borrower_cash >= interest:
            # Borrower can pay interest
            borrower_inv.cash[cur_code] = borrower_cash - interest
            borrower_inv.save(update_fields=["cash"])

            # Credit lender if agent-to-agent
            if loan.lender_type == "agent" and loan.lender:
                lender_inv = _get_or_create_inventory(loan.lender)
                lender_cash = lender_inv.cash.get(cur_code, 0.0)
                lender_inv.cash[cur_code] = lender_cash + interest
                lender_inv.save(update_fields=["cash"])

            # Record in ledger
            EconomicLedger.objects.create(
                simulation=simulation,
                tick=tick,
                from_agent=loan.borrower,
                to_agent=loan.lender,
                currency=primary_currency,
                total_amount=interest,
                transaction_type="trade",
            )
        else:
            # Borrower cannot pay interest -- mark for default
            defaulting_loan_ids.append(loan.id)
            logger.info(
                "Loan %d: borrower %s cannot pay interest %.1f (cash=%.1f)",
                loan.id,
                loan.borrower.name,
                interest,
                borrower_cash,
            )

    return defaulting_loan_ids


def process_maturity(simulation, tick: int) -> None:
    """Handle loans reaching maturity at the current tick.

    Three outcomes are possible:
    1. Repayment: borrower has enough cash to repay the remaining balance.
    2. Rollover: borrower can pay interest but not principal. A new loan
       is created with potentially higher interest rate (Minsky fragility).
       The rollover count is incremented.
    3. Default: borrower cannot pay either. Handled by process_defaults.

    Rollover is capped by credit_config.max_rollover. Exceeding the cap
    triggers default instead.

    Args:
        simulation: The simulation instance.
        tick: Current simulation tick.
    """
    maturing_loans = list(
        Loan.objects.filter(
            simulation=simulation,
            status="active",
            due_at_tick=tick,
        ).select_related("borrower", "lender", "collateral")
    )

    if not maturing_loans:
        return

    primary_currency = _get_primary_currency(simulation)
    if not primary_currency:
        return

    cur_code = primary_currency.code
    credit_config = _get_credit_config(simulation)
    max_rollover = credit_config.get("max_rollover", 3)
    default_duration = credit_config.get("default_loan_duration_ticks", 20)

    for loan in maturing_loans:
        borrower_inv = _get_or_create_inventory(loan.borrower)
        borrower_cash = borrower_inv.cash.get(cur_code, 0.0)
        balance = loan.remaining_balance

        if borrower_cash >= balance:
            # Full repayment
            borrower_inv.cash[cur_code] = borrower_cash - balance
            borrower_inv.save(update_fields=["cash"])

            # Credit lender
            if loan.lender_type == "agent" and loan.lender:
                lender_inv = _get_or_create_inventory(loan.lender)
                lender_inv.cash[cur_code] = lender_inv.cash.get(cur_code, 0.0) + balance
                lender_inv.save(update_fields=["cash"])

            # Update banking state
            if loan.lender_type == "banking":
                try:
                    bs = BankingState.objects.get(simulation=simulation)
                    bs.total_loans_outstanding = max(
                        0.0,
                        bs.total_loans_outstanding - balance,
                    )
                    bs.save(update_fields=["total_loans_outstanding"])
                except BankingState.DoesNotExist:
                    pass

            loan.status = "repaid"
            loan.remaining_balance = 0.0
            loan.save(update_fields=["status", "remaining_balance"])

            EconomicLedger.objects.create(
                simulation=simulation,
                tick=tick,
                from_agent=loan.borrower,
                to_agent=loan.lender,
                currency=primary_currency,
                total_amount=balance,
                transaction_type="trade",
            )

            logger.info("Loan %d repaid by %s", loan.id, loan.borrower.name)

        elif loan.times_rolled_over < max_rollover:
            # Rollover: create new loan with higher rate (Minsky fragility)
            interest = balance * loan.interest_rate
            if borrower_cash >= interest:
                # Pay the interest portion
                borrower_inv.cash[cur_code] = borrower_cash - interest
                borrower_inv.save(update_fields=["cash"])

                if loan.lender_type == "agent" and loan.lender:
                    lender_inv = _get_or_create_inventory(loan.lender)
                    lender_inv.cash[cur_code] = (
                        lender_inv.cash.get(cur_code, 0.0) + interest
                    )
                    lender_inv.save(update_fields=["cash"])

            # Mark old loan as rolled over
            loan.status = "rolled_over"
            loan.save(update_fields=["status"])

            # New loan with 10% higher rate. The rate increase on rollover
            # is a design choice reflecting lender risk adjustment. The 10%
            # increment is a tunable design parameter.
            new_rate = loan.interest_rate * 1.1

            Loan.objects.create(
                simulation=simulation,
                lender=loan.lender,
                borrower=loan.borrower,
                lender_type=loan.lender_type,
                principal=balance,
                interest_rate=new_rate,
                remaining_balance=balance,
                collateral=loan.collateral,
                issued_at_tick=tick,
                due_at_tick=tick + default_duration,
                times_rolled_over=loan.times_rolled_over + 1,
                status="active",
            )

            logger.info(
                "Loan %d rolled over (count=%d, new rate=%.3f)",
                loan.id,
                loan.times_rolled_over + 1,
                new_rate,
            )
        else:
            # Cannot repay and max rollovers exceeded: will be handled by
            # process_defaults. Mark status stays "active" for now; the
            # default processor picks up loans that could not be serviced.
            loan.status = "defaulted"
            loan.save(update_fields=["status"])
            logger.info(
                "Loan %d defaulted at maturity (max rollovers exceeded)",
                loan.id,
            )


def process_defaults(simulation, tick: int) -> list[dict]:
    """Process defaulted loans: seize collateral, record losses, damage reputation.

    For each defaulted loan:
    1. If collateral exists, transfer Property ownership to the lender
       (or to government if the lender is the banking system).
    2. Write off the remaining debt by zeroing the balance.
    3. Create a negative reputation memory for the borrower, reflecting
       the social cost of default.

    Args:
        simulation: The simulation instance.
        tick: Current simulation tick.

    Returns:
        List of dicts with lender loss information for cascade processing.
    """
    defaulted_loans = list(
        Loan.objects.filter(
            simulation=simulation,
            status="defaulted",
        ).select_related("borrower", "lender", "collateral")
    )

    if not defaulted_loans:
        return []

    lender_losses: dict[int | str, float] = {}
    loss_records = []

    for loan in defaulted_loans:
        loss = loan.remaining_balance

        # Seize collateral if available
        if loan.collateral:
            prop = loan.collateral
            if loan.lender_type == "agent" and loan.lender:
                prop.owner = loan.lender
                prop.owner_type = "agent"
            else:
                prop.owner = None
                prop.owner_type = "government"
            prop.save(update_fields=["owner", "owner_type"])

            # Reduce loss by collateral value
            loss = max(0.0, loss - prop.value)

        # Write off remaining debt
        loan.remaining_balance = 0.0
        loan.save(update_fields=["remaining_balance"])

        # Update banking state
        if loan.lender_type == "banking":
            try:
                bs = BankingState.objects.get(simulation=simulation)
                bs.total_loans_outstanding = max(
                    0.0,
                    bs.total_loans_outstanding - loan.principal,
                )
                bs.save(update_fields=["total_loans_outstanding"])
            except BankingState.DoesNotExist:
                pass

        # Track lender losses for cascade analysis
        if loan.lender_type == "agent" and loan.lender:
            lender_id = loan.lender.id
            lender_losses[lender_id] = lender_losses.get(lender_id, 0.0) + loss
            loss_records.append(
                {
                    "lender_id": lender_id,
                    "lender_type": "agent",
                    "loss": loss,
                    "loan_id": loan.id,
                }
            )
        else:
            lender_losses["banking"] = lender_losses.get("banking", 0.0) + loss
            loss_records.append(
                {
                    "lender_id": None,
                    "lender_type": "banking",
                    "loss": loss,
                    "loan_id": loan.id,
                }
            )

        # Create negative reputation memory for the borrower.
        # Defaulting on debt is a strongly negative social signal.
        # Emotional weight 0.8 (high but not traumatic) -- tunable
        # design parameter.
        _create_default_reputation_damage(
            simulation=simulation,
            borrower=loan.borrower,
            lender=loan.lender,
            amount=loan.principal,
            tick=tick,
        )

        logger.info(
            "Loan %d default processed: borrower=%s, loss=%.1f, collateral=%s",
            loan.id,
            loan.borrower.name,
            loss,
            "seized" if loan.collateral else "none",
        )

    return loss_records


def _create_default_reputation_damage(
    simulation,
    borrower: Agent,
    lender: Agent | None,
    amount: float,
    tick: int,
) -> None:
    """Record reputation damage from a loan default.

    Creates a memory for nearby agents and updates reputation scores
    via the reputation system (Castelfranchi, Conte & Paolucci 1998).

    The action sentiment of -0.7 represents a significant but not
    maximally negative action (compared to violence at -1.0). Tunable
    design parameter.
    """
    # Create memory for the borrower (self-awareness of default)
    Memory.objects.create(
        agent=borrower,
        content=f"Defaulted on a loan of {amount:.0f}. Financial reputation damaged.",
        emotional_weight=0.8,
        source_type="direct",
        reliability=1.0,
        tick_created=tick,
        origin_agent=borrower,
    )

    # Update reputation: all agents in the same zone learn about the default
    if borrower.zone_id:
        zone_agents = Agent.objects.filter(
            simulation=simulation,
            zone_id=borrower.zone_id,
            is_alive=True,
        ).exclude(id=borrower.id)

        for observer in zone_agents:
            update_reputation(
                holder=observer,
                target=borrower,
                action_sentiment=-0.7,
                reliability=0.8,
                tick=tick,
            )

    # The lender has direct knowledge -- stronger impact
    if lender:
        update_reputation(
            holder=lender,
            target=borrower,
            action_sentiment=-0.9,
            reliability=1.0,
            tick=tick,
        )


def default_dead_agent_loans(simulation) -> int:
    """Default all active loans held by dead borrowers.

    Agents who die (is_alive=False) cannot earn income or repay debt.
    Their loans are defaulted immediately. Collateral seizure and
    cascade propagation follow the existing default pipeline.

    Called at the start of the credit market step, before service_loans.

    Args:
        simulation: The simulation instance.

    Returns:
        Number of loans defaulted.
    """
    dead_loans = Loan.objects.filter(
        simulation=simulation,
        status="active",
        borrower__is_alive=False,
    )
    count = dead_loans.count()
    if count > 0:
        dead_loans.update(status="defaulted")
        logger.info(
            "Defaulted %d loans from dead agents in simulation %d",
            count, simulation.id,
        )
    return count


def find_best_unpledged_property(agent: Agent) -> "Property | None":
    """Find the agent's highest-value property not already used as collateral.

    Excludes properties that are collateral for active loans to prevent
    double-pledging. Uses the related_name 'collateralized_loans' defined
    on Loan.collateral.

    Args:
        agent: The agent whose properties to search.

    Returns:
        The highest-value unpledged Property, or None if none available.
    """
    return (
        Property.objects.filter(owner=agent, owner_type="agent")
        .exclude(collateralized_loans__status="active")
        .order_by("-value")
        .first()
    )


def process_default_cascade(
    simulation,
    tick: int,
    max_depth: int = 3,
) -> int:
    """Propagate defaults through the debt graph using BFS.

    When a lender absorbs losses exceeding CASCADE_LOSS_THRESHOLD of
    their wealth, they default on their own loans, potentially causing
    their own lenders to absorb losses and default in turn.

    This models the contagion mechanism observed in financial crises
    (Allen & Gale 2000, "Financial Contagion", Journal of Political
    Economy 108(1), 1-33). The max_depth cap prevents infinite
    propagation, which is realistic: real-world cascade circuits are
    typically short (3-5 links) because diversification limits
    exposure concentration.

    Args:
        simulation: The simulation instance.
        tick: Current simulation tick.
        max_depth: Maximum cascade depth. Tunable design parameter;
            default 3 based on typical financial network diameter.

    Returns:
        The maximum cascade depth reached.
    """
    # Compute per-agent losses from defaults processed in this tick
    defaulted_loans = Loan.objects.filter(
        simulation=simulation,
        status="defaulted",
        lender_type="agent",
        lender__isnull=False,
    ).select_related("lender")

    # Aggregate losses per lender
    lender_losses: dict[int, float] = {}
    for loan in defaulted_loans:
        lender_id = loan.lender_id
        lender_losses[lender_id] = lender_losses.get(lender_id, 0.0) + loan.principal

    if not lender_losses:
        return 0

    # BFS cascade
    queue: deque[tuple[int, int]] = deque()  # (agent_id, depth)
    visited: set[int] = set()
    max_depth_reached = 0

    for lender_id, total_loss in lender_losses.items():
        try:
            lender = Agent.objects.get(id=lender_id)
        except Agent.DoesNotExist:
            continue

        if total_loss > CASCADE_LOSS_THRESHOLD * max(lender.wealth, 1.0):
            queue.append((lender_id, 1))
            visited.add(lender_id)

    while queue:
        agent_id, depth = queue.popleft()
        if depth > max_depth:
            continue

        max_depth_reached = max(max_depth_reached, depth)

        # Default this agent's loans as borrower
        agent_loans = Loan.objects.filter(
            simulation=simulation,
            borrower_id=agent_id,
            status="active",
        ).select_related("lender")

        cascade_losses: dict[int, float] = {}
        for loan in agent_loans:
            loan.status = "defaulted"
            loan.save(update_fields=["status"])

            if loan.lender_type == "agent" and loan.lender_id:
                cascade_losses[loan.lender_id] = (
                    cascade_losses.get(loan.lender_id, 0.0) + loan.remaining_balance
                )

        # Check if cascade lenders should also default
        for next_lender_id, loss in cascade_losses.items():
            if next_lender_id in visited:
                continue
            try:
                next_lender = Agent.objects.get(id=next_lender_id)
            except Agent.DoesNotExist:
                continue

            if loss > CASCADE_LOSS_THRESHOLD * max(next_lender.wealth, 1.0):
                queue.append((next_lender_id, depth + 1))
                visited.add(next_lender_id)

    if max_depth_reached > 0:
        logger.warning(
            "Default cascade in simulation %d: depth=%d, agents affected=%d",
            simulation.id,
            max_depth_reached,
            len(visited),
        )

    return max_depth_reached

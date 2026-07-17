"""Property market: valuation, listing/matching, and expropriation.

Implements three property market mechanisms:

1. Gordon Growth Model valuation (Gordon, M.J. 1959. Dividends, Earnings,
   and Stock Prices. Review of Economics and Statistics 41(2), 99-105).
   Computes intrinsic property value as V = R / (r - g), where R is
   rental income, r is the discount rate, and g is the rent growth rate.

2. Property listing matching: buyers express intent via DecisionLog,
   listings are matched by zone and price, and transactions settle
   with cash transfer and ledger recording.

3. Expropriation on regime change (Acemoglu, D. & Robinson, J.A. 2006.
   Economic Origins of Dictatorship and Democracy. Cambridge University
   Press). Different regime types apply different redistribution policies
   to private property, from no change (democracy) to full nationalization
   (revolution).
"""

from __future__ import annotations

import json
import logging

from epocha.apps.agents.models import Agent, DecisionLog, Memory
from epocha.apps.world.government import add_to_treasury
from epocha.apps.world.models import Government

from .models import (
    AgentInventory,
    BankingState,
    Currency,
    EconomicLedger,
    Loan,
    Property,
    PropertyListing,
)

logger = logging.getLogger(__name__)


def _get_primary_currency(simulation) -> Currency | None:
    """Return the primary currency for the simulation, or None."""
    return Currency.objects.filter(simulation=simulation, is_primary=True).order_by("id").first()


def compute_gordon_valuation(prop: Property, simulation) -> float:
    """Compute intrinsic property value using the Gordon Growth Model.

    Gordon, M.J. (1959). Dividends, Earnings, and Stock Prices.
    Review of Economics and Statistics 41(2), 99-105.

    Formula: V = R / max(r - g, 0.01)
    - R: rental income from the last tick (EconomicLedger rent transactions
      for the property's zone). Falls back to property.value * r when no
      rent history exists.
    - r: discount rate, taken from BankingState.base_interest_rate
      (default 0.05 if no BankingState exists).
    - g: trailing 5-tick growth rate of rent in the property's zone.
    - Floor: property.value * 0.1 (prevents near-zero valuations).
    - Cap: property.value * 10 (prevents runaway speculation).

    The 0.01 minimum denominator prevents division by zero when r ~ g.
    This is a standard numerical guard used in DCF implementations.

    Simplification: the Gordon model assumes constant growth in perpetuity.
    Real property markets have cyclical rents. This approximation is
    acceptable for a simulation tick-level valuation where long-term
    trends dominate short-term noise.

    Args:
        prop: The Property instance to value.
        simulation: The simulation instance.

    Returns:
        Estimated intrinsic value in primary currency units.
    """
    # Discount rate from banking state
    try:
        banking_state = BankingState.objects.get(simulation=simulation)
        r = banking_state.base_interest_rate
    except BankingState.DoesNotExist:
        r = 0.05  # Conservative default (Stiglitz & Weiss 1981 baseline)

    # Rental income: sum of rent transactions in the property's zone
    # from the most recent tick that has any rent data.
    rent_entries = EconomicLedger.objects.filter(
        simulation=simulation,
        transaction_type="rent",
    ).order_by("-tick")

    # Find the latest tick with rent data
    latest_rent = rent_entries.first()
    if latest_rent:
        latest_tick = latest_rent.tick
        # Sum rent for the property's zone at the latest tick
        # id-ordered Python sum (R7-DET-1 determinism pin): SQL
        # SUM(float8) accumulates in scan order, which is heap-order
        # dependent -- the same ULP pinning applied to Python-side
        # accumulations applies to aggregates feeding persisted state.
        rental_income = sum(
            EconomicLedger.objects.filter(
                simulation=simulation,
                transaction_type="rent",
                tick=latest_tick,
            )
            .order_by("id")
            .values_list("total_amount", flat=True)
        )
    else:
        rental_income = 0.0

    # Fallback: if no rent history, estimate from property value * r
    if rental_income <= 0:
        rental_income = prop.value * r

    # Growth rate: trailing 5-tick rent growth
    g = _compute_rent_growth(simulation, num_ticks=5)

    # Gordon formula: V = R / max(r - g, 0.01)
    denominator = max(r - g, 0.01)
    valuation = rental_income / denominator

    # Floor and cap relative to current property value
    floor = prop.value * 0.1
    cap = prop.value * 10.0
    valuation = max(floor, min(valuation, cap))

    return valuation


def _compute_rent_growth(simulation, num_ticks: int = 5) -> float:
    """Compute trailing rent growth rate over the last num_ticks.

    Uses the compound growth formula: g = (R_latest / R_earliest)^(1/n) - 1
    where n is the number of ticks between measurements.

    Returns 0.0 if insufficient data (fewer than 2 distinct tick values).

    Args:
        simulation: The simulation instance.
        num_ticks: Number of ticks to look back.

    Returns:
        Per-tick growth rate (can be negative for declining rents).
    """
    # Get distinct ticks with rent data, most recent first
    rent_ticks = (
        EconomicLedger.objects.filter(
            simulation=simulation,
            transaction_type="rent",
        )
        .values("tick")
        .distinct()
        .order_by("-tick")[:num_ticks]
    )
    tick_list = [entry["tick"] for entry in rent_ticks]

    if len(tick_list) < 2:
        return 0.0

    latest_tick = tick_list[0]
    earliest_tick = tick_list[-1]
    span = latest_tick - earliest_tick
    if span <= 0:
        return 0.0

    # id-ordered Python sums (R7-DET-1 determinism pin, see
    # compute_gordon_valuation).
    latest_rent = sum(
        EconomicLedger.objects.filter(
            simulation=simulation,
            transaction_type="rent",
            tick=latest_tick,
        )
        .order_by("id")
        .values_list("total_amount", flat=True)
    )
    earliest_rent = sum(
        EconomicLedger.objects.filter(
            simulation=simulation,
            transaction_type="rent",
            tick=earliest_tick,
        )
        .order_by("id")
        .values_list("total_amount", flat=True)
    )

    if earliest_rent <= 0:
        return 0.0

    ratio = latest_rent / earliest_rent
    if ratio <= 0:
        return 0.0

    # Compound growth: g = ratio^(1/span) - 1
    g = ratio ** (1.0 / span) - 1.0
    return g


def process_property_listings(simulation, tick: int) -> dict:
    """Match property buyers to sellers via the listing mechanism.

    Process flow:
    1. Expire stale listings (older than 10 ticks) by setting status
       to "withdrawn".
    2. Read buy_property intents from DecisionLog at tick-1. Each intent
       is a JSON object with action="buy_property".
    3. Match each buyer to the cheapest active listing in their current
       zone, excluding self-purchase (seller cannot buy own property).
    4. If the buyer has enough cash: transfer property ownership, deduct
       cash from buyer, credit seller, mark listing "sold", and record
       the transaction in EconomicLedger.
    5. If insufficient cash: the match fails (no automatic loan issuance).

    The 10-tick listing expiration is a design parameter reflecting
    the assumption that property markets in pre-industrial to modern
    economies operate on multi-period timescales. Tunable via
    simulation config in future iterations.

    Args:
        simulation: The simulation instance.
        tick: Current simulation tick.

    Returns:
        Dict with keys "matched", "expired", "failed" (integer counts).
    """
    result = {"matched": 0, "expired": 0, "failed": 0}

    # Step 1: Expire stale listings (older than 10 ticks)
    stale_count = PropertyListing.objects.filter(
        property__simulation=simulation,
        status="listed",
        listed_at_tick__lte=tick - 10,
    ).update(status="withdrawn")
    result["expired"] = stale_count

    # Step 2: Read buy_property intents from DecisionLog at tick-1.
    # R4-DET-2 fix (Round 4 re-audit, run wf_9fb030e4-8a1): buyers
    # compete for listings (each sale removes one), so buyer order
    # decides contested-property winners -- pinned by agent id, then
    # row id, for seeded reproducibility. The DecisionLog default
    # ordering ("tick") is constant within this filter and pins
    # nothing. The cheapest-listing lookup below carries an id
    # tiebreak for equal asking prices for the same reason.
    buy_decisions = (
        DecisionLog.objects.filter(
            simulation=simulation,
            tick=tick - 1,
            output_decision__contains='"buy_property"',
        )
        .select_related("agent")
        .order_by("agent_id", "id")
    )

    buyers = []
    for decision in buy_decisions:
        try:
            data = json.loads(decision.output_decision)
        except (json.JSONDecodeError, TypeError):
            continue
        if data.get("action") == "buy_property":
            buyers.append(decision.agent)

    # Step 3-5: Match buyers to listings
    primary_currency = _get_primary_currency(simulation)
    if not primary_currency:
        return result

    cur_code = primary_currency.code

    for buyer in buyers:
        if not buyer.zone_id:
            result["failed"] += 1
            continue

        # Find cheapest active listing in buyer's zone, excluding self-purchase
        listing = (
            PropertyListing.objects.filter(
                property__simulation=simulation,
                property__zone_id=buyer.zone_id,
                status="listed",
            )
            .exclude(property__owner=buyer)
            # R6-PROP-1 fix (Round 6 re-audit): a property pledged as
            # collateral for an active (or pending-default) loan is
            # under lien -- selling it would strip the lender's
            # security while the loan stays outstanding. Such listings
            # are unmatchable until the loan is repaid or the default
            # settles (seizure transfers ownership through the credit
            # pipeline, not the market).
            .exclude(property__collateralized_loans__status__in=["active", "defaulted"])
            .select_related("property", "property__owner")
            .order_by("asking_price", "id")
            .first()
        )

        if not listing:
            result["failed"] += 1
            continue

        # Check buyer cash
        try:
            buyer_inv = buyer.inventory
        except AgentInventory.DoesNotExist:
            result["failed"] += 1
            continue

        buyer_cash = buyer_inv.cash.get(cur_code, 0.0)
        if buyer_cash < listing.asking_price:
            result["failed"] += 1
            continue

        # Execute the transaction
        seller = listing.property.owner
        prop = listing.property

        # R3-3 fix (Round 3 re-audit, run wf_af84ed13-dc3): a sale is a
        # TRANSFER, so the buyer's debit must always have a matching
        # credit. Pre-fix, an ownerless (government/public) listing
        # debited the buyer while the seller guard skipped the credit,
        # destroying money -- the same defect class as the fixed
        # CM-TAX-2. The sale price of an ownerless property is credited
        # to the government treasury; without a Government the sale
        # cannot settle and is skipped before any debit.
        treasury_gov = None
        if seller is None:
            try:
                treasury_gov = Government.objects.get(simulation=simulation)
            except Government.DoesNotExist:
                result["failed"] += 1
                continue

        # Deduct cash from buyer
        buyer_inv.cash[cur_code] = buyer_cash - listing.asking_price
        buyer_inv.save(update_fields=["cash"])

        # Credit seller (agent) or the treasury (ownerless property)
        if seller:
            try:
                seller_inv = seller.inventory
            except AgentInventory.DoesNotExist:
                seller_inv = AgentInventory.objects.create(agent=seller, holdings={}, cash={})
            seller_inv.cash[cur_code] = seller_inv.cash.get(cur_code, 0.0) + listing.asking_price
            seller_inv.save(update_fields=["cash"])
        else:
            add_to_treasury(treasury_gov, cur_code, listing.asking_price)

        # Transfer property ownership
        prop.owner = buyer
        prop.owner_type = "agent"
        prop.save(update_fields=["owner", "owner_type"])

        # Mark listing as sold
        listing.status = "sold"
        listing.save(update_fields=["status"])

        # Record in ledger
        EconomicLedger.objects.create(
            simulation=simulation,
            tick=tick,
            from_agent=buyer,
            to_agent=seller,
            currency=primary_currency,
            total_amount=listing.asking_price,
            transaction_type="property_sale",
        )

        result["matched"] += 1
        logger.info(
            "Property sale: %s -> %s, price=%.1f, property=%s",
            seller.name if seller else "government",
            buyer.name,
            listing.asking_price,
            prop.name,
        )

    return result


def process_expropriation(
    simulation,
    old_type: str,
    new_type: str,
    tick: int,
) -> int:
    """Redistribute property on regime change.

    Implements regime-dependent property redistribution following
    Acemoglu, D. & Robinson, J.A. (2006). Economic Origins of
    Dictatorship and Democracy. Cambridge University Press.

    Different regime types apply different expropriation policies:
    - "none": no redistribution (typical of democracy, monarchy).
    - "nationalize_all": all agent-owned properties transferred to
      government ownership (typical of communist revolution).
    - "elite_seizure": properties owned by elite/wealthy social classes
      transferred to government (typical of populist revolution).
    - "redistribute": properties with above-median value transferred
      to government (egalitarian redistribution).

    Side effects of expropriation:
    - Active listings for affected properties are withdrawn.
    - Loans collateralized by affected properties are defaulted.
    - Affected agents receive a negative memory (trauma of property loss).

    The expropriation_policies config maps new_type to policy. If no
    policy is defined, defaults to "none" (no expropriation).

    Args:
        simulation: The simulation instance.
        old_type: Previous regime type (unused but kept for logging).
        new_type: New regime type, used to look up expropriation policy.
        tick: Current simulation tick.

    Returns:
        Number of properties transferred.
    """
    sim_config = simulation.config or {}
    policies = sim_config.get("expropriation_policies", {})
    policy = policies.get(new_type, "none")

    if policy == "none":
        return 0

    # Select properties to expropriate based on policy
    agent_properties = Property.objects.filter(
        simulation=simulation,
        owner_type="agent",
        owner__isnull=False,
    ).select_related("owner")

    if policy == "nationalize_all":
        target_properties = agent_properties
    elif policy == "elite_seizure":
        # Target properties owned by elite or wealthy social classes
        target_properties = agent_properties.filter(
            owner__social_class__in=["elite", "wealthy"],
        )
    elif policy == "redistribute":
        # Target properties with above-median value
        all_values = list(agent_properties.values_list("value", flat=True))
        if not all_values:
            return 0
        all_values.sort()
        median_value = all_values[len(all_values) // 2]
        target_properties = agent_properties.filter(value__gt=median_value)
    else:
        logger.warning(
            "Unknown expropriation policy '%s' for regime '%s'",
            policy,
            new_type,
        )
        return 0

    # Materialize the queryset to iterate with side effects.
    # R10-DET-2 fix (Round 10 re-audit, run wf_9a6a807f-a41): pin the
    # transfer order by id so the seizure side effects (and the Memory
    # rows created below) are allocated in a reproducible order, matching
    # the create-order pinning convention of broadcast_banking_concern.
    properties_to_transfer = list(target_properties.order_by("id"))
    if not properties_to_transfer:
        return 0

    transferred = 0
    affected_agent_ids = set()

    for prop in properties_to_transfer:
        affected_agent_ids.add(prop.owner_id)

        # Withdraw active listings for this property
        PropertyListing.objects.filter(
            property=prop,
            status="listed",
        ).update(status="withdrawn")

        # Default loans collateralized by this property. R7-PROP-2 fix
        # (Round 7 re-audit): the collateral FK is CLEARED -- the state
        # has taken the security, so the later default settlement must
        # not re-seize the nationalized property for the lender
        # (silently reversing the expropriation); the lender's loss is
        # the gross remaining balance, which is exactly right since the
        # collateral is gone. R8-NEW-1/R8-PROP-1 fix (Round 8 re-audit,
        # run wf_75faf0db-ad2): the filter must reach the pending
        # "defaulted" state too -- a loan cascade-marked defaulted at
        # tick t but settled by process_defaults only at t+1 retains its
        # collateral claim through the pending-default window, so an
        # active-only filter left that claim live and the next-tick
        # settlement re-seized the nationalized property. This is the
        # same status pair ["active", "defaulted"] every other lien gate
        # uses (find_best_unpledged_property, issue_loan, the listing
        # match gate, sell_property).
        Loan.objects.filter(
            collateral=prop,
            status__in=["active", "defaulted"],
        ).update(status="defaulted", collateral=None)

        # Transfer ownership to government
        prop.owner = None
        prop.owner_type = "government"
        prop.save(update_fields=["owner", "owner_type"])

        transferred += 1

    # Create negative memories for affected agents. R10-DET-2 fix:
    # id-order the queryset so the Memory rows are created in a
    # reproducible order (same convention as broadcast_banking_concern).
    affected_agents = Agent.objects.filter(
        id__in=affected_agent_ids,
        is_alive=True,
    ).order_by("id")
    for agent in affected_agents:
        Memory.objects.create(
            agent=agent,
            content=(
                f"Property expropriated by the new {new_type} regime. "
                f"All holdings seized under {policy} policy."
            ),
            emotional_weight=0.9,
            source_type="direct",
            reliability=1.0,
            tick_created=tick,
            origin_agent=agent,
        )

    logger.info(
        "Expropriation: regime %s -> %s, policy=%s, properties=%d, agents=%d",
        old_type,
        new_type,
        policy,
        transferred,
        len(affected_agent_ids),
    )

    return transferred

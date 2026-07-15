"""Economy tick pipeline orchestrator.

Executes the 9-step economic cycle each tick:
0. Expectations update (Nerlove adaptive, personality-modulated)
1. Production (CES per agent per zone)
2. Market clearing (Walrasian tatonnement)
3. Credit market (loan servicing, maturity, defaults, cascade, banking)
4. Rent (land factor share, emergent Ricardian)
5. Wages (labor factor share)
5b. Profit (capital/entrepreneurial residual factor share)
6. Taxation (flat income tax -> treasury)
7. Essential consumption (1 unit/tick deducted)
8a. Money supply (live circulating-cash aggregate) + Fisher diagnostic
8b. Wealth + mood (population-median-relative thresholds) + stability
9. Deposit recalculation (banking)

Steps 4, 5 and 5b partition a single zone output value V into factor
incomes that sum to V (rent + wages + profit = V; Ricardo 1817 /
national-accounting identity -- see distribution.py's module
docstring). This replaced the pre-CM-1-fix behavior where rent and
wages each independently credited the full V as brand-new cash,
injecting strictly more money than the output actually produced
(Round 1 audit report, distribution/PROD-2 and cross-module CM-1).

Step 8a recomputes Currency.total_supply (M) as the live aggregate of
circulating agent cash every tick, instead of leaving it at the
static template constant set once at initialization, and invokes the
Fisher MV=PQ diagnostic (previously defined but never called). Step
8b derives the mood poverty/satiation thresholds from the living
population's median wealth instead of fixed absolute constants (see
monetary.derive_mood_thresholds). Both are the CM-2 and CM-6 fixes
from the Round 1 audit report's cross-module findings; the system
prices they and the inflation computation consume are themselves a
genuine cross-zone aggregate (monetary.aggregate_system_prices),
fixing the last-zone-wins dict.update() merge (CM-5).

This function replaces world/economy.py:process_economy_tick for
simulations that have the new economy app models initialized.
"""

from __future__ import annotations

import logging
import statistics

from epocha.apps.agents.models import Agent
from epocha.apps.world.government import add_to_treasury
from epocha.apps.world.models import Government

from .banking import (
    adjust_interest_rate,
    broadcast_banking_concern,
    check_solvency,
    recalculate_deposits,
)
from .credit import (
    default_dead_agent_loans,
    process_default_cascade,
    process_defaults,
    process_maturity,
    service_loans,
)
from .distribution import compute_taxes, partition_output_value
from .expectations import update_agent_expectations
from .market import (
    SUBSISTENCE_NEED_PER_AGENT,
    collect_supply_and_demand,
    execute_trades,
    tatonnement_prices,
)
from .models import (
    AgentInventory,
    Currency,
    EconomicLedger,
    GoodCategory,
    PriceHistory,
    Property,
    TaxPolicy,
    ZoneEconomy,
)
from .monetary import (
    aggregate_system_prices,
    check_fisher_consistency,
    compute_circulating_money_supply,
    compute_inflation,
    compute_mood_delta,
    compute_velocity,
    derive_mood_thresholds,
    update_agent_wealth,
)
from .production import compute_agent_output
from .property_market import process_property_listings
from .template_loader import _ROLE_PRODUCTION, _ZONE_TYPE_RESOURCES

logger = logging.getLogger(__name__)


def _get_hoarding_agent_ids(simulation, tick: int) -> set[int]:
    """Return IDs of agents who chose 'hoard' in the previous tick.

    Reads DecisionLog entries from tick-1 and checks if the JSON
    output_decision contains the "hoard" action. DecisionLog.output_decision
    is a TextField containing json.dumps() output, so __contains with
    '"hoard"' performs a PostgreSQL LIKE substring match.

    Returns an empty set at tick 0 (no previous tick to read).
    """
    if tick <= 0:
        return set()

    from epocha.apps.agents.models import DecisionLog

    hoarding_decisions = DecisionLog.objects.filter(
        simulation=simulation,
        tick=tick - 1,
        output_decision__contains='"hoard"',
    ).values_list("agent_id", flat=True)
    return set(hoarding_decisions)


def process_economy_tick_new(simulation, tick: int) -> None:
    """Execute one full economic tick for a simulation.

    This is the main entry point called by the simulation engine.
    It replaces process_economy_tick from world/economy.py for
    simulations with the new economy data layer.

    Requires: Currency, GoodCategory, ZoneEconomy, and AgentInventory
    records to exist for the simulation. If no currencies exist, the
    tick is silently skipped (economy not yet initialized).
    """
    currencies = list(Currency.objects.filter(simulation=simulation))
    if not currencies:
        logger.debug(
            "Simulation %d has no currencies; skipping economy tick",
            simulation.id,
        )
        return

    primary_currency = next((c for c in currencies if c.is_primary), currencies[0])
    goods = list(GoodCategory.objects.filter(simulation=simulation))
    good_map = {g.code: g for g in goods}

    try:
        tax_policy = TaxPolicy.objects.get(simulation=simulation)
    except TaxPolicy.DoesNotExist:
        tax_policy = None

    zone_economies = list(
        ZoneEconomy.objects.filter(zone__world__simulation=simulation).select_related("zone")
    )
    if not zone_economies:
        return

    # Retrieve template-level production config. These may be stored in the
    # simulation's config or in the zone economy's production_config (if the
    # template loader populated them). Fallback to the hardcoded defaults
    # from template_loader.py to ensure the engine works even when the
    # zone economy only contains per-good CES parameters.
    sim_config = simulation.config or {}
    prod_template = sim_config.get("production_config", {})
    default_sigma = prod_template.get("default_sigma", 0.5)
    # default_scale: the template's fallback CES scale parameter.
    # Defaults to 1.0 (conservative) when not specified, so legacy
    # simulations without this key are not affected. Tunable design parameter.
    default_scale = prod_template.get("default_scale", 1.0)
    role_production = prod_template.get("role_production", _ROLE_PRODUCTION)
    zone_type_resources = prod_template.get("zone_type_resources", _ZONE_TYPE_RESOURCES)
    # wage_share / rent_share: factor-income shares partitioning the zone
    # output value V into rent + wages + profit (Ricardo 1817 / national-
    # accounting identity Y = wages + rent + profit; see distribution.py's
    # module docstring). profit_share is the residual 1 - wage_share -
    # rent_share, clamped to 0 if the two shares alone already reach or
    # exceed 1 (a misconfigured template) -- see
    # distribution.partition_output_value for the clamp and its warning
    # log. Defaults match distribution.py's own defaults so callers that
    # invoke compute_rent/compute_wages/compute_profit directly (e.g.
    # tests) see the same numbers as the engine.
    wage_share = prod_template.get("wage_share", 0.6)
    rent_share = prod_template.get("rent_share", 0.15)

    total_transaction_volume = 0.0
    total_output = 0.0
    # CM-5 fix (Round 1 audit report, cross-module CM-5): collect one
    # price dict PER ZONE and aggregate them with
    # monetary.aggregate_system_prices after the loop, instead of
    # merging with dict.update() as the loop runs. The pre-fix
    # dict.update() approach kept only the LAST zone's price for any
    # good present in multiple zones, despite the "_all" naming
    # implying a genuine system-wide aggregate.
    old_prices_by_zone: list[dict[str, float]] = []
    new_prices_by_zone: list[dict[str, float]] = []

    credit_processed = False

    # === STEP 0: EXPECTATIONS UPDATE (Nerlove adaptive) ===
    # Update agent price expectations BEFORE market clearing so that
    # expectations reflect the previous tick's prices and can influence
    # trading decisions in the current tick.
    update_agent_expectations(simulation, tick)

    # Get agents who hoarded at the previous tick.
    # Their goods will not be offered to the market (is_hoarding=True).
    hoarding_ids = _get_hoarding_agent_ids(simulation, tick)

    for ze in zone_economies:
        zone = ze.zone
        agents = list(
            Agent.objects.filter(simulation=simulation, zone=zone, is_alive=True).select_related(
                "inventory"
            )
        )
        if not agents:
            continue

        properties = list(Property.objects.filter(simulation=simulation, zone=zone))

        old_prices = dict(ze.market_prices)
        old_prices_by_zone.append(old_prices)

        # === STEP 1: PRODUCTION (CES per agent) ===
        zone_production: dict[str, float] = {}
        agent_outputs: list[dict] = []

        for agent in agents:
            good_code, quantity = compute_agent_output(
                agent_role=agent.role,
                zone_economy=ze,
                properties_in_zone=properties,
                role_production=role_production,
                zone_type_resources=zone_type_resources,
                zone_type=zone.zone_type,
                default_sigma=default_sigma,
                default_scale=default_scale,
            )

            if quantity > 0:
                current = zone_production.get(good_code, 0.0)
                zone_production[good_code] = current + quantity
                total_output += quantity

                # Add produced goods to agent inventory
                try:
                    inv = agent.inventory
                except AgentInventory.DoesNotExist:
                    inv = AgentInventory.objects.create(
                        agent=agent,
                        holdings={},
                        cash={},
                    )

                current_qty = inv.holdings.get(good_code, 0.0)
                inv.holdings[good_code] = current_qty + quantity
                inv.save(update_fields=["holdings"])

                # Record production in ledger
                EconomicLedger.objects.create(
                    simulation=simulation,
                    tick=tick,
                    from_agent=None,
                    to_agent=agent,
                    currency=primary_currency,
                    good_category=good_map.get(good_code),
                    quantity=quantity,
                    unit_price=0.0,
                    total_amount=0.0,
                    transaction_type="production",
                )

            # Note: no "owns_property" flag here (CM-1 fix). Ownership no
            # longer affects wage computation -- an owner's land/capital
            # income is earned through the rent/profit steps below, on
            # the SAME output value, not through a separate full-value
            # wage payout (see distribution.compute_wages docstring).
            agent_outputs.append(
                {
                    "agent_id": agent.id,
                    "good_code": good_code,
                    "quantity": quantity,
                }
            )

        # === STEP 2: MARKET CLEARING (Walrasian tatonnement) ===
        agent_inventories = []
        for agent in agents:
            try:
                inv = agent.inventory
            except AgentInventory.DoesNotExist:
                continue
            agent_inventories.append(
                {
                    "agent_id": agent.id,
                    "holdings": dict(inv.holdings),
                    "cash_amount": sum(inv.cash.values()),
                    "is_hoarding": agent.id in hoarding_ids,
                }
            )

        good_dicts = [
            {
                "code": g.code,
                "is_essential": g.is_essential,
                "price_elasticity": g.price_elasticity,
            }
            for g in goods
        ]
        total_supply, total_demand, agent_orders = collect_supply_and_demand(
            agent_inventories,
            good_dicts,
            old_prices,
        )

        # base_prices from template (GoodCategory.base_price) used as absolute
        # reference for MAX_PRICE_RATIO cap, preventing cross-tick drift.
        template_base_prices = {g.code: g.base_price for g in goods}
        equilibrium_prices, converged = tatonnement_prices(
            old_prices,
            total_supply,
            total_demand,
            base_prices=template_base_prices,
        )

        # Execute trades at equilibrium prices
        trades = execute_trades(
            agent_orders,
            equilibrium_prices,
            total_supply,
            total_demand,
        )

        # Apply trades to inventories
        inv_cache: dict[int, AgentInventory] = {}
        for agent in agents:
            try:
                inv_cache[agent.id] = agent.inventory
            except AgentInventory.DoesNotExist:
                pass

        for trade in trades:
            buyer_inv = inv_cache.get(trade["buyer_id"])
            seller_inv = inv_cache.get(trade["seller_id"])
            if buyer_inv and seller_inv:
                good = trade["good_code"]
                qty = trade["quantity"]
                cost = trade["total"]

                buyer_inv.holdings[good] = buyer_inv.holdings.get(good, 0.0) + qty
                current_hold = seller_inv.holdings.get(good, 0.0)
                seller_inv.holdings[good] = max(0.0, current_hold - qty)

                cur_code = primary_currency.code
                buyer_inv.cash[cur_code] = buyer_inv.cash.get(cur_code, 0.0) - cost
                seller_inv.cash[cur_code] = seller_inv.cash.get(cur_code, 0.0) + cost

                total_transaction_volume += cost

                EconomicLedger.objects.create(
                    simulation=simulation,
                    tick=tick,
                    from_agent_id=trade["buyer_id"],
                    to_agent_id=trade["seller_id"],
                    currency=primary_currency,
                    good_category=good_map.get(good),
                    quantity=qty,
                    unit_price=trade["price"],
                    total_amount=cost,
                    transaction_type="trade",
                )

        # Save all modified inventories after trades
        for inv in inv_cache.values():
            inv.save(update_fields=["holdings", "cash"])

        # === STEP 3: CREDIT MARKET ===
        # Loan servicing, maturity, defaults, and cascade are processed
        # once (not per-zone), so we run them after the first zone's
        # trades. Subsequent zones skip this step via the flag.
        # Note: loan creation (issue_loan) is NOT called automatically
        # in the tick -- it is triggered by agent decisions.
        if not credit_processed:
            # === STEP 3: PROPERTY MARKET ===
            # Process listings and match buyers from previous tick.
            # Runs before credit so property sales generate cash that
            # may prevent loan defaults.
            process_property_listings(simulation, tick)

            default_dead_agent_loans(simulation)
            service_loans(simulation, tick)
            process_maturity(simulation, tick)
            process_defaults(simulation, tick)
            process_default_cascade(simulation, tick)
            adjust_interest_rate(simulation, tick)
            check_solvency(simulation)
            broadcast_banking_concern(simulation, tick)
            credit_processed = True

        # === STEP 4/5/5b: RENT + WAGES + PROFIT (conserved factor-income
        # partition, approach A / CM-1 fix) ===
        # zone_production's total value V = sum(zone_production[g] *
        # equilibrium_prices[g]) is partitioned into rent (land) + wages
        # (labor) + profit (capital residual) so the three shares sum to
        # exactly V -- see distribution.partition_output_value and its
        # module docstring for the Ricardo 1817 / national-accounting
        # source. This replaces the pre-fix behavior where compute_rent
        # and compute_wages each independently credited (approximately)
        # the full V as brand-new cash, injecting strictly more money
        # than the output actually produced every tick.
        # Round 2 re-audit fix (CM-TAX-1 / NEW-3, run wf_da2305bc-4cd):
        # Property.owner_id may point to an agent who is dead or lives
        # in another zone, while the payee lookup below (inv_cache) only
        # holds this zone's living agents. Owners are therefore resolved
        # against the SIMULATION-WIDE living-agent set: dead owners are
        # excluded from the partition entirely (their bonus share is
        # reallocated by compute_profit's no-landlord fallback, keeping
        # the partition summing to V), and living out-of-zone owners are
        # paid through the extended payee lookup built after the
        # partition instead of being silently dropped.
        owner_ids = {p.owner_id for p in properties if p.owner_type == "agent" and p.owner_id}
        alive_owner_ids: set[int] = (
            set(
                Agent.objects.filter(
                    simulation=simulation, id__in=owner_ids, is_alive=True
                ).values_list("id", flat=True)
            )
            if owner_ids
            else set()
        )
        prop_dicts = [
            {"owner_id": p.owner_id, "production_bonus": p.production_bonus}
            for p in properties
            if p.owner_type == "agent" and p.owner_id in alive_owner_ids
        ]
        factor_shares = partition_output_value(
            zone_production,
            prop_dicts,
            agent_outputs,
            equilibrium_prices,
            wage_share=wage_share,
            rent_share=rent_share,
        )
        rents = factor_shares["rent"]
        wages = factor_shares["wages"]
        profits = factor_shares["profit"]

        cur_code = primary_currency.code

        # Extended payee lookup (NEW-3 fix): factor incomes may be owed
        # to living owners resident in OTHER zones, absent from the
        # zone-local inv_cache. Fetch their inventories simulation-wide
        # so rent/profit credits (and the matching tax debits in step 6)
        # reach every living payee. Fresh per zone: a cross-zone owner
        # credited by an earlier zone is re-read from the DB here, so
        # running balances stay consistent across the zone loop.
        payee_invs: dict[int, AgentInventory] = dict(inv_cache)
        missing_payee_ids = (set(rents) | set(wages) | set(profits)) - payee_invs.keys()
        if missing_payee_ids:
            for inv in AgentInventory.objects.filter(
                agent_id__in=missing_payee_ids, agent__is_alive=True
            ):
                payee_invs[inv.agent_id] = inv

        # === STEP 4: RENT (land factor share, emergent Ricardian) ===
        for owner_id, rent_amount in rents.items():
            inv = payee_invs.get(owner_id)
            if inv and rent_amount > 0:
                inv.cash[cur_code] = inv.cash.get(cur_code, 0.0) + rent_amount
                inv.save(update_fields=["cash"])
                total_transaction_volume += rent_amount
                EconomicLedger.objects.create(
                    simulation=simulation,
                    tick=tick,
                    from_agent=None,
                    to_agent_id=owner_id,
                    currency=primary_currency,
                    total_amount=rent_amount,
                    transaction_type="rent",
                )

        # === STEP 5: WAGES (labor factor share) ===
        # Sanity cap: no single wage exceeds 100x the median wage. This
        # predates the conservation fix, when it guarded against price-
        # explosion artifacts creating billionaires in a single tick
        # (Fix 1-3 residuals / edge cases). With wages now structurally
        # bounded to wage_share*V (never the full output value), the cap
        # should rarely bind, but it is kept as a defense-in-depth
        # safety net -- documented, not removed. The floor of 100.0
        # ensures the cap is non-trivial even when the median is very
        # low. Tunable design parameter.
        if wages:
            sorted_wages = sorted(wages.values())
            median_wage = sorted_wages[len(sorted_wages) // 2]
            max_wage = max(median_wage * 100.0, 100.0)
            wages = {k: min(v, max_wage) for k, v in wages.items()}

        for agent_id, wage_amount in wages.items():
            inv = payee_invs.get(agent_id)
            if inv and wage_amount > 0:
                current_cash = inv.cash.get(cur_code, 0.0)
                inv.cash[cur_code] = current_cash + wage_amount
                inv.save(update_fields=["cash"])
                total_transaction_volume += wage_amount
                EconomicLedger.objects.create(
                    simulation=simulation,
                    tick=tick,
                    from_agent=None,
                    to_agent_id=agent_id,
                    currency=primary_currency,
                    total_amount=wage_amount,
                    transaction_type="wage",
                )

        # === STEP 5b: PROFIT (capital/entrepreneurial residual factor
        # share) ===
        for agent_id, profit_amount in profits.items():
            inv = payee_invs.get(agent_id)
            if inv and profit_amount > 0:
                current_cash = inv.cash.get(cur_code, 0.0)
                inv.cash[cur_code] = current_cash + profit_amount
                inv.save(update_fields=["cash"])
                total_transaction_volume += profit_amount
                EconomicLedger.objects.create(
                    simulation=simulation,
                    tick=tick,
                    from_agent=None,
                    to_agent_id=agent_id,
                    currency=primary_currency,
                    total_amount=profit_amount,
                    transaction_type="profit",
                )

        # === STEP 6: TAXATION (flat rate -> government treasury) ===
        # Taxable income is still wages + rent only (profit is not yet
        # in the taxable base -- a known scope limitation; taxing profit
        # would be a separate, deliberate policy change).
        #
        # Round 2 re-audit fixes (CM-TAX-1 / CM-TAX-2, run
        # wf_da2305bc-4cd): taxation is a TRANSFER, so debits and the
        # treasury credit must be two legs of the same amount.
        # (1) The step runs only when a Government exists: taxing with
        #     no fiscal authority to receive the revenue destroyed money
        #     (agents were debited while the `if gov` guard skipped the
        #     credit). Without a government, no tax is levied at all.
        # (2) The treasury is credited with the RUNNING TOTAL of taxes
        #     actually debited from agents, not compute_taxes' nominal
        #     total_revenue: pre-fix, income imputed to an owner absent
        #     from the payee lookup was credited to the treasury with no
        #     matching debit, creating money. With the extended
        #     payee_invs lookup every living earner is debitable, and
        #     the running total makes the conservation structural.
        if tax_policy:
            try:
                gov = Government.objects.get(simulation=simulation)
            except Government.DoesNotExist:
                gov = None

            if gov is not None:
                agent_incomes: dict[int, float] = {}
                for agent_id in set(list(wages.keys()) + list(rents.keys())):
                    income = wages.get(agent_id, 0.0) + rents.get(agent_id, 0.0)
                    if income > 0:
                        agent_incomes[agent_id] = income

                tax_result = compute_taxes(agent_incomes, tax_policy.income_tax_rate)

                collected_tax = 0.0
                for agent_id, tax_amount in tax_result["agent_taxes"].items():
                    if tax_amount > 0:
                        inv = payee_invs.get(agent_id)
                        if inv:
                            cur_cash = inv.cash.get(cur_code, 0.0)
                            inv.cash[cur_code] = cur_cash - tax_amount
                            inv.save(update_fields=["cash"])
                            collected_tax += tax_amount
                            EconomicLedger.objects.create(
                                simulation=simulation,
                                tick=tick,
                                from_agent_id=agent_id,
                                to_agent=None,
                                currency=primary_currency,
                                total_amount=tax_amount,
                                transaction_type="tax",
                            )

                if collected_tax > 0:
                    add_to_treasury(gov, cur_code, collected_tax)

        # Update zone prices and write price history
        ze.market_prices = equilibrium_prices
        ze.market_supply = total_supply
        ze.market_demand = total_demand
        ze.save(update_fields=["market_prices", "market_supply", "market_demand"])
        new_prices_by_zone.append(dict(equilibrium_prices))

        for good_code, price in equilibrium_prices.items():
            PriceHistory.objects.create(
                zone_economy=ze,
                good_code=good_code,
                tick=tick,
                price=price,
                supply=total_supply.get(good_code, 0.0),
                demand=total_demand.get(good_code, 0.0),
            )

        # === STEP 7: ESSENTIAL CONSUMPTION (1 unit/tick deducted) ===
        essential_codes = [g.code for g in goods if g.is_essential]
        for agent in agents:
            inv = inv_cache.get(agent.id)
            if inv:
                for code in essential_codes:
                    current = inv.holdings.get(code, 0.0)
                    inv.holdings[code] = max(0.0, current - SUBSISTENCE_NEED_PER_AGENT)
                inv.save(update_fields=["holdings"])

    # CM-5 fix: aggregate the per-zone price snapshots collected during
    # the loop above into genuine system-wide prices (mean across the
    # zones quoting each good), replacing the pre-fix last-zone-wins
    # dict.update() merge. Used below by the money-supply/Fisher step,
    # the wealth valuation, and the inflation/stability step.
    old_prices_all = aggregate_system_prices(old_prices_by_zone)
    new_prices_all = aggregate_system_prices(new_prices_by_zone)

    # === STEP 8: MONEY SUPPLY + WEALTH + MOOD + STABILITY FEEDBACK ===
    # Single pass over all living agents (with their inventory
    # prefetched) feeds three things that Round 1 audit found broken:
    # (a) the live circulating-cash aggregate for Currency.total_supply
    # (CM-2), (b) each agent's wealth for the mood update, and (c) the
    # population median wealth used to derive this tick's mood
    # thresholds (CM-6). Doing this in one query avoids re-fetching
    # the same agent/inventory rows for what were previously two
    # separate steps (N+1 avoidance).
    all_agents = list(
        Agent.objects.filter(simulation=simulation, is_alive=True).select_related("inventory")
    )

    # Property values grouped by owner in a single query instead of one
    # query per agent inside the loop below (N+1 avoidance; pre-existing
    # in the code this step replaces, fixed while rewriting the block).
    property_values_by_owner: dict[int, list[float]] = {}
    for owner_id, value in Property.objects.filter(
        simulation=simulation, owner_type="agent"
    ).values_list("owner_id", "value"):
        property_values_by_owner.setdefault(owner_id, []).append(value)

    agent_wealths: list[tuple[Agent, float]] = []
    cash_balances: list[dict[str, float]] = []

    for agent in all_agents:
        try:
            inv = agent.inventory
        except AgentInventory.DoesNotExist:
            continue

        cash_balances.append(inv.cash)

        property_values = property_values_by_owner.get(agent.id, [])
        wealth = update_agent_wealth(
            holdings=inv.holdings,
            cash=inv.cash,
            property_values=property_values,
            prices=new_prices_all or old_prices_all,
        )
        agent_wealths.append((agent, wealth))

    # === STEP 8a: MONEY SUPPLY (CM-2 fix) + FISHER DIAGNOSTIC ===
    # total_supply (M) is recomputed every tick as the live aggregate
    # of circulating cash across all living agents in the primary
    # currency, replacing the static template constant that was set
    # once at initialization and never updated (Round 1 audit report,
    # cross-module CM-2). See compute_circulating_money_supply's
    # docstring for why BankingState.total_deposits is NOT added on
    # top (it mirrors the same agent cash, not a disjoint pool).
    live_money_supply = compute_circulating_money_supply(cash_balances, primary_currency.code)
    primary_currency.total_supply = live_money_supply
    primary_currency.cached_velocity = compute_velocity(
        transaction_volume=total_transaction_volume,
        money_supply=live_money_supply,
    )
    primary_currency.save(update_fields=["total_supply", "cached_velocity"])

    # Fisher MV=PQ consistency check: a DIAGNOSTIC only (logs a warning
    # above 20% divergence; never alters simulation state). Round 1
    # audit report found check_fisher_consistency defined but never
    # invoked anywhere -- the one check that would have caught the
    # pre-fix money-supply/conservation defects (CM-1, CM-2) was dead
    # code. system_price_level is the unweighted mean of this tick's
    # system-aggregated prices (P); total_output is this tick's
    # aggregate physical output across all zones (Q).
    system_price_level = (
        sum(new_prices_all.values()) / len(new_prices_all) if new_prices_all else 0.0
    )
    check_fisher_consistency(
        money_supply=live_money_supply,
        velocity=primary_currency.cached_velocity,
        price_level=system_price_level,
        output_level=total_output,
    )

    # === STEP 8b: WEALTH + MOOD (CM-6 fix: relative thresholds) ===
    # Poverty/satiation thresholds are derived from THIS tick's living
    # population median wealth (monetary.derive_mood_thresholds)
    # instead of the fixed absolute constants (10.0 / 100.0) that were
    # disconnected from the era template's wealth scale -- e.g. every
    # property owner in the pre-industrial template started past the
    # old satiation=100 threshold from tick 0 (Round 1 audit report,
    # monetary+initialization cross-module finding).
    median_wealth = statistics.median([w for _, w in agent_wealths]) if agent_wealths else 0.0
    poverty_threshold, satiation_threshold = derive_mood_thresholds(median_wealth)

    agents_to_update = []
    for agent, wealth in agent_wealths:
        agent.wealth = wealth
        mood_delta = compute_mood_delta(
            wealth,
            satiation_threshold=satiation_threshold,
            poverty_threshold=poverty_threshold,
        )
        agent.mood = max(0.0, min(1.0, agent.mood + mood_delta))
        agents_to_update.append(agent)

    if agents_to_update:
        Agent.objects.bulk_update(agents_to_update, ["wealth", "mood"])

    # === STEP 8c: STABILITY FEEDBACK (inflation, system aggregate) ===
    # Alesina & Perotti (1996): political instability and income distribution.
    # High inflation destabilizes; low inflation is neutral-to-positive.
    # Thresholds are tunable design parameters, not derived from the paper.
    # old_prices_all/new_prices_all are now genuine system-wide
    # aggregates (CM-5 fix above), not a single zone's prices.
    inflation = compute_inflation(old_prices_all, new_prices_all)
    try:
        world = simulation.world
        if abs(inflation) > 0.15:
            world.stability_index = max(0.0, world.stability_index - 0.02)
        elif abs(inflation) < 0.05:
            world.stability_index = min(1.0, world.stability_index + 0.005)
        world.save(update_fields=["stability_index"])
    except Exception:
        pass

    # === STEP 9: DEPOSIT RECALCULATION ===
    # Recalculate total_deposits from all agent cash after all economic
    # transactions are complete.
    recalculate_deposits(simulation)

    trade_count = EconomicLedger.objects.filter(
        simulation=simulation,
        tick=tick,
        transaction_type="trade",
    ).count()
    logger.info(
        "Economy tick %d: output=%.1f, trades=%d, volume=%.1f, inflation=%.1f%%",
        tick,
        total_output,
        trade_count,
        total_transaction_volume,
        inflation * 100,
    )

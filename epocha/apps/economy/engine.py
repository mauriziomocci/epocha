"""Economy tick pipeline orchestrator.

Executes the 9-step economic cycle each tick:
0. Expectations update (Nerlove adaptive, personality-modulated)
1. Production (CES per agent per zone)
2. Market clearing (Walrasian tatonnement)
3. Credit market (loan servicing, maturity, defaults, cascade, banking)
4. Rent (emergent, Ricardian)
5. Wages (output share)
6. Taxation (flat income tax -> treasury)
7. Essential consumption (1 unit/tick deducted)
8. Monetary update (Fisher velocity) + wealth/mood/stability feedback

This function replaces world/economy.py:process_economy_tick for
simulations that have the new economy app models initialized.
"""

from __future__ import annotations

import logging

from epocha.apps.agents.models import Agent
from epocha.apps.world.models import Government

from .banking import adjust_interest_rate, check_solvency
from .credit import (
    process_default_cascade,
    process_defaults,
    process_maturity,
    service_loans,
)
from .distribution import compute_rent, compute_taxes, compute_wages
from .expectations import update_agent_expectations
from .market import collect_supply_and_demand, execute_trades, tatonnement_prices
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
    compute_inflation,
    compute_mood_delta,
    compute_velocity,
    update_agent_wealth,
)
from .production import compute_agent_output
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
        ZoneEconomy.objects.filter(zone__world__simulation=simulation).select_related(
            "zone"
        )
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
    wage_share = prod_template.get("wage_share", 0.6)

    total_transaction_volume = 0.0
    total_output = 0.0
    old_prices_all: dict[str, float] = {}
    new_prices_all: dict[str, float] = {}

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
            Agent.objects.filter(
                simulation=simulation, zone=zone, is_alive=True
            ).select_related("inventory")
        )
        if not agents:
            continue

        properties = list(Property.objects.filter(simulation=simulation, zone=zone))
        property_owner_ids = {p.owner_id for p in properties if p.owner_id}

        old_prices = dict(ze.market_prices)
        old_prices_all.update(old_prices)

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

            agent_outputs.append(
                {
                    "agent_id": agent.id,
                    "good_code": good_code,
                    "quantity": quantity,
                    "owns_property": agent.id in property_owner_ids,
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
            service_loans(simulation, tick)
            process_maturity(simulation, tick)
            process_defaults(simulation, tick)
            process_default_cascade(simulation, tick)
            adjust_interest_rate(simulation, tick)
            check_solvency(simulation)
            credit_processed = True

        # === STEP 4: RENT (emergent Ricardian) ===
        prop_dicts = [
            {"owner_id": p.owner_id, "production_bonus": p.production_bonus}
            for p in properties
            if p.owner_type == "agent" and p.owner_id
        ]
        rents = compute_rent(zone_production, prop_dicts, equilibrium_prices)

        cur_code = primary_currency.code
        for owner_id, rent_amount in rents.items():
            inv = inv_cache.get(owner_id)
            if inv:
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

        # === STEP 5: WAGES (share of output value) ===
        wages = compute_wages(agent_outputs, equilibrium_prices, wage_share=wage_share)

        # Sanity cap: no single wage exceeds 100x the median wage.
        # This prevents price-explosion artifacts (from Fix 1-3 residuals or
        # edge cases) from creating billionaires in a single tick.
        # The floor of 100.0 ensures the cap is non-trivial even when the
        # median is very low. Tunable design parameter.
        if wages:
            sorted_wages = sorted(wages.values())
            median_wage = sorted_wages[len(sorted_wages) // 2]
            max_wage = max(median_wage * 100.0, 100.0)
            wages = {k: min(v, max_wage) for k, v in wages.items()}

        for agent_id, wage_amount in wages.items():
            inv = inv_cache.get(agent_id)
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

        # === STEP 6: TAXATION (flat rate -> government treasury) ===
        if tax_policy:
            agent_incomes: dict[int, float] = {}
            for agent_id in set(list(wages.keys()) + list(rents.keys())):
                income = wages.get(agent_id, 0.0) + rents.get(agent_id, 0.0)
                if income > 0:
                    agent_incomes[agent_id] = income

            tax_result = compute_taxes(agent_incomes, tax_policy.income_tax_rate)

            try:
                gov = Government.objects.get(simulation=simulation)
            except Government.DoesNotExist:
                gov = None

            for agent_id, tax_amount in tax_result["agent_taxes"].items():
                if tax_amount > 0:
                    inv = inv_cache.get(agent_id)
                    if inv:
                        cur_cash = inv.cash.get(cur_code, 0.0)
                        inv.cash[cur_code] = cur_cash - tax_amount
                        inv.save(update_fields=["cash"])
                        EconomicLedger.objects.create(
                            simulation=simulation,
                            tick=tick,
                            from_agent_id=agent_id,
                            to_agent=None,
                            currency=primary_currency,
                            total_amount=tax_amount,
                            transaction_type="tax",
                        )

            if gov and tax_result["total_revenue"] > 0:
                treasury = gov.government_treasury or {}
                prev = treasury.get(cur_code, 0.0)
                treasury[cur_code] = prev + tax_result["total_revenue"]
                gov.government_treasury = treasury
                gov.save(update_fields=["government_treasury"])

        # Update zone prices and write price history
        ze.market_prices = equilibrium_prices
        ze.market_supply = total_supply
        ze.market_demand = total_demand
        ze.save(update_fields=["market_prices", "market_supply", "market_demand"])
        new_prices_all.update(equilibrium_prices)

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
                    inv.holdings[code] = max(0.0, current - 1.0)
                inv.save(update_fields=["holdings"])

    # === STEP 8a (global): MONETARY UPDATE (Fisher velocity) ===
    primary_currency.cached_velocity = compute_velocity(
        transaction_volume=total_transaction_volume,
        money_supply=primary_currency.total_supply,
    )
    primary_currency.save(update_fields=["cached_velocity"])

    # === STEP 8b: WEALTH + MOOD + STABILITY FEEDBACK ===
    all_agents = Agent.objects.filter(simulation=simulation, is_alive=True)
    agents_to_update = []

    for agent in all_agents:
        try:
            inv = agent.inventory
        except AgentInventory.DoesNotExist:
            continue

        property_values = list(
            Property.objects.filter(owner=agent, owner_type="agent").values_list(
                "value", flat=True
            )
        )

        agent.wealth = update_agent_wealth(
            holdings=inv.holdings,
            cash=inv.cash,
            property_values=property_values,
            prices=new_prices_all or old_prices_all,
        )

        mood_delta = compute_mood_delta(agent.wealth)
        agent.mood = max(0.0, min(1.0, agent.mood + mood_delta))

        agents_to_update.append(agent)

    if agents_to_update:
        Agent.objects.bulk_update(agents_to_update, ["wealth", "mood"])

    # Update world stability based on inflation
    # Alesina & Perotti (1996): political instability and income distribution.
    # High inflation destabilizes; low inflation is neutral-to-positive.
    # Thresholds are tunable design parameters, not derived from the paper.
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

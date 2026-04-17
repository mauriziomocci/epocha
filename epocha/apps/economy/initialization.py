"""Initialize economy models from a template at world generation time.

Creates all the economic infrastructure (currencies, goods, factors,
zone economies, agent inventories, properties, tax policy) needed for
the new economy engine to run.

Called at the end of generate_world_from_prompt so that every simulation
starts with a fully configured economy layer.
"""
from __future__ import annotations

import logging
import random

from epocha.apps.agents.models import Agent
from epocha.apps.world.models import Zone

from .models import (
    AgentInventory,
    Currency,
    GoodCategory,
    PriceHistory,
    ProductionFactor,
    Property,
    TaxPolicy,
    ZoneEconomy,
)
from .template_loader import get_template, load_default_templates

logger = logging.getLogger(__name__)


def initialize_economy(
    simulation,
    template_name: str = "pre_industrial",
    overrides: dict | None = None,
) -> dict:
    """Create all economy models for a simulation from a template.

    This is the single entry point for economy initialization. It is
    idempotent in practice because generate_world_from_prompt creates
    a fresh simulation each time, but the function does not guard
    against duplicate calls -- the caller is responsible for calling
    it exactly once per simulation.

    Args:
        simulation: The Simulation instance to initialize.
        template_name: Name of the EconomyTemplate to use.
        overrides: Optional dict to override template fields before
            applying them. Keys mirror the template fields
            (e.g. "tax_config", "initial_distribution").

    Returns:
        Summary dict with counts of created objects.
    """
    # Ensure templates exist in the database
    load_default_templates()
    template = get_template(template_name)

    if overrides:
        for key, value in overrides.items():
            if hasattr(template, key):
                setattr(template, key, value)

    # 1. Currencies
    currencies = []
    for cur_cfg in template.currencies_config:
        currencies.append(Currency.objects.create(
            simulation=simulation,
            code=cur_cfg["code"],
            name=cur_cfg["name"],
            symbol=cur_cfg["symbol"],
            is_primary=True,
            total_supply=cur_cfg["initial_supply"],
        ))
    primary_currency = currencies[0] if currencies else None
    primary_code = primary_currency.code if primary_currency else "LVR"

    # 2. Goods
    goods = []
    for good_cfg in template.goods_config:
        goods.append(GoodCategory.objects.create(
            simulation=simulation,
            code=good_cfg["code"],
            name=good_cfg["name"],
            is_essential=good_cfg.get("is_essential", False),
            base_price=good_cfg["base_price"],
            price_elasticity=good_cfg["price_elasticity"],
        ))
    good_map = {g.code: g for g in goods}
    essential_codes = [g.code for g in goods if g.is_essential]

    # 3. Production factors
    factors = []
    for factor_cfg in template.factors_config:
        factors.append(ProductionFactor.objects.create(
            simulation=simulation,
            code=factor_cfg["code"],
            name=factor_cfg["name"],
        ))

    # 4. Tax policy
    tax_cfg = template.tax_config
    TaxPolicy.objects.create(
        simulation=simulation,
        income_tax_rate=tax_cfg.get("income_tax_rate", 0.15),
    )

    # 5. Zone economies
    prod_cfg = template.production_config
    default_sigma = prod_cfg.get("default_sigma", 0.5)
    zone_type_resources = prod_cfg.get("zone_type_resources", {})
    role_production = prod_cfg.get("role_production", {})

    # Build initial market prices from goods base_price
    initial_prices = {g.code: g.base_price for g in goods}

    # Build per-good production config from template defaults.
    # Each good gets a CES function with equal factor weights and the
    # template's default sigma. Zone-specific resource abundances are
    # stored in natural_resources, not in the per-good config.
    factor_codes = [f.code for f in factors]
    n_factors = len(factor_codes) or 1
    default_good_production = {}
    for g in goods:
        default_good_production[g.code] = {
            "scale": 5.0,  # tunable design parameter: base output multiplier
            "sigma": default_sigma,
            "factors": {fc: 1.0 / n_factors for fc in factor_codes},
        }

    zones = list(Zone.objects.filter(world__simulation=simulation))
    zone_economies_created = 0
    for zone in zones:
        # Natural resources depend on zone type
        resources = zone_type_resources.get(zone.zone_type, {})
        ze = ZoneEconomy.objects.create(
            zone=zone,
            natural_resources=resources,
            production_config=default_good_production,
            market_prices=dict(initial_prices),
        )
        zone_economies_created += 1

        # Write initial PriceHistory at tick 0
        for g in goods:
            PriceHistory.objects.create(
                zone_economy=ze,
                good_code=g.code,
                tick=0,
                price=g.base_price,
                supply=0.0,
                demand=0.0,
            )

    # Store production config on simulation.config so the engine can
    # access template-level settings (role_production, zone_type_resources,
    # default_sigma) without re-reading the template.
    sim_config = simulation.config or {}
    sim_config["production_config"] = {
        "default_sigma": default_sigma,
        "role_production": role_production,
        "zone_type_resources": zone_type_resources,
    }

    # Save behavioral economy configs from the template so that
    # credit, banking, expectations, and expropriation subsystems
    # can read their parameters from simulation.config at runtime.
    # Without this, all behavioral lookups fall back to hardcoded
    # defaults, ignoring era-specific template calibration.
    template_behavioral = template.config or {}
    if template_behavioral.get("credit_config"):
        sim_config["credit_config"] = template_behavioral["credit_config"]
    if template_behavioral.get("banking_config"):
        sim_config["banking_config"] = template_behavioral["banking_config"]
    if template_behavioral.get("expectations_config"):
        sim_config["expectations_config"] = template_behavioral["expectations_config"]
    if template_behavioral.get("expropriation_policies"):
        sim_config["expropriation_policies"] = template_behavioral["expropriation_policies"]

    simulation.config = sim_config
    simulation.save(update_fields=["config"])

    # 6. Agent inventories and initial wealth distribution
    dist_cfg = template.initial_distribution
    wealth_ranges = dist_cfg.get("wealth_range", {})

    agents = list(Agent.objects.filter(simulation=simulation, is_alive=True))
    inventories_created = 0

    for agent in agents:
        social_class = getattr(agent, "social_class", "working")
        # Map social class to wealth range; fall through to "poor" default
        wrange = wealth_ranges.get(social_class)
        if not wrange:
            # Try broader category mappings
            if social_class in ("elite", "wealthy"):
                wrange = wealth_ranges.get("elite", [100, 300])
            elif social_class == "middle":
                wrange = wealth_ranges.get("middle", [50, 150])
            else:
                wrange = wealth_ranges.get("poor", [5, 30])

        initial_cash = random.uniform(wrange[0], wrange[1])

        # Start with 2 units of each essential good
        holdings = {code: 2.0 for code in essential_codes}

        AgentInventory.objects.create(
            agent=agent,
            holdings=holdings,
            cash={primary_code: initial_cash},
        )
        inventories_created += 1

        # Update agent wealth to reflect inventory value
        holdings_value = sum(
            qty * initial_prices.get(code, 0.0)
            for code, qty in holdings.items()
        )
        agent.wealth = initial_cash + holdings_value
        agent.save(update_fields=["wealth"])

    # 7. Property distribution
    properties_created = 0
    property_ownership = dist_cfg.get("property_ownership", "class_based")
    prop_types = template.properties_config.get("types", [])

    if property_ownership == "class_based":
        # Elite and wealthy agents get properties in their zone
        elite_agents = [
            a for a in agents
            if getattr(a, "social_class", "working") in ("elite", "wealthy")
        ]

        for agent in elite_agents:
            agent_zone = agent.zone
            if not agent_zone:
                continue

            for prop_cfg in prop_types:
                Property.objects.create(
                    simulation=simulation,
                    owner=agent,
                    owner_type="agent",
                    zone=agent_zone,
                    property_type=prop_cfg["code"],
                    name=f"{agent.name}'s {prop_cfg['name']}",
                    value=prop_cfg.get("base_value", 100),
                    production_bonus=prop_cfg.get("production_bonus", {}),
                )
                properties_created += 1

    # 8. Banking system initialization
    # Must run after simulation.config is saved so that initialize_banking
    # can read banking_config from simulation.config.
    from .banking import initialize_banking
    initialize_banking(simulation)

    logger.info(
        "Economy initialized for simulation %d: %d currencies, %d goods, "
        "%d factors, %d zone economies, %d inventories, %d properties",
        simulation.id,
        len(currencies),
        len(goods),
        len(factors),
        zone_economies_created,
        inventories_created,
        properties_created,
    )

    return {
        "currencies": len(currencies),
        "goods": len(goods),
        "factors": len(factors),
        "zone_economies": zone_economies_created,
        "inventories": inventories_created,
        "properties": properties_created,
    }

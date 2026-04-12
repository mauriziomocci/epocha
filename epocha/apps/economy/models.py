"""Economy models -- neoclassical general equilibrium data layer.

This module contains the data models for the economy system. The models
are per-simulation: each simulation has its own currencies, goods,
factors, markets, and properties. All numeric economic parameters are
stored in the database (not hardcoded) to support universal
configurability across eras and scenarios.

Scientific paradigm: neoclassical (Arrow et al. 1961, Walras 1874,
Fisher 1911, Ricardo 1817). See the spec for full references:
docs/superpowers/specs/2026-04-12-economy-base-design.md
"""

from __future__ import annotations

from django.db import models


class Currency(models.Model):
    """A monetary unit in the simulation.

    The total_supply field represents M in Fisher's equation MV=PQ
    (Fisher, I. 1911. The Purchasing Power of Money).
    The cached_velocity field is V, recomputed each tick from actual
    transaction volume -- it is NOT a stored constant. The equation
    is used as a diagnostic check, not as a price-determination
    mechanism: prices are set by Walrasian market clearing.
    """

    simulation = models.ForeignKey(
        "simulation.Simulation",
        on_delete=models.CASCADE,
        related_name="currencies",
    )
    code = models.CharField(max_length=10)
    name = models.CharField(max_length=100)
    symbol = models.CharField(max_length=5)
    is_primary = models.BooleanField(default=True)
    total_supply = models.FloatField(
        help_text="M in Fisher's MV=PQ: total money in circulation",
    )
    cached_velocity = models.FloatField(
        default=1.0,
        help_text="V in Fisher's MV=PQ: recomputed each tick from "
        "transaction volume, NOT a stored constant",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("simulation", "code")

    def __str__(self):
        return f"{self.name} ({self.code})"


class GoodCategory(models.Model):
    """A category of economic goods in the simulation.

    Price elasticity uses the absolute value convention from standard
    economics: 0 = perfectly inelastic (demand unaffected by price),
    1 = unit elastic, >1 = elastic (demand highly sensitive to price).
    Essential goods (food) typically 0.2-0.5; luxury goods 1.5-2.5.

    Source for empirical values: Houthakker & Taylor (1970), updated
    by Andreyeva et al. (2010).
    """

    simulation = models.ForeignKey(
        "simulation.Simulation",
        on_delete=models.CASCADE,
        related_name="good_categories",
    )
    code = models.CharField(max_length=30)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    is_essential = models.BooleanField(
        default=False,
        help_text="Essential goods cause crisis when scarce",
    )
    base_price = models.FloatField(
        help_text="Initial price in the primary currency",
    )
    price_elasticity = models.FloatField(
        help_text="|Price elasticity of demand|: 0=inelastic, 1=unit, >1=elastic",
    )
    config = models.JSONField(default=dict)

    class Meta:
        unique_together = ("simulation", "code")

    def __str__(self):
        return f"{self.name} ({self.code})"


class ProductionFactor(models.Model):
    """A factor of production (labor, capital, natural resources, knowledge).

    Factors are inputs to the CES production function (Arrow et al. 1961).
    Each zone has different abundances of each factor, and each good
    category has different factor requirements.
    """

    simulation = models.ForeignKey(
        "simulation.Simulation",
        on_delete=models.CASCADE,
        related_name="production_factors",
    )
    code = models.CharField(max_length=30)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    config = models.JSONField(default=dict)

    class Meta:
        unique_together = ("simulation", "code")

    def __str__(self):
        return f"{self.name} ({self.code})"


# -- Zone and agent economic models --


class ZoneEconomy(models.Model):
    """Economic state of a geographic zone.

    Each zone has its own market with local prices, supply, and demand.
    The production_config contains CES function parameters per good
    category. Natural resources are zone-specific endowments that affect
    production output.

    market_prices is a snapshot cache updated each tick for fast reads;
    the authoritative price history is in PriceHistory.
    """

    zone = models.OneToOneField(
        "world.Zone",
        on_delete=models.CASCADE,
        related_name="economy",
    )
    natural_resources = models.JSONField(
        default=dict,
        help_text="{factor_code: abundance_float}",
    )
    production_config = models.JSONField(
        default=dict,
        help_text="{good_code: {factors: {factor_code: exponent}, "
        "scale: A, sigma: sigma_CES}}",
    )
    market_prices = models.JSONField(
        default=dict,
        help_text="{good_code: current_price} -- snapshot cache",
    )
    market_supply = models.JSONField(default=dict)
    market_demand = models.JSONField(default=dict)

    def __str__(self):
        return f"Economy of {self.zone.name}"


class PriceHistory(models.Model):
    """Historical price record per good per zone per tick.

    Used by the analytics/psychohistoriography system for inflation
    detection, crisis identification, and time-series visualization.
    """

    zone_economy = models.ForeignKey(
        ZoneEconomy,
        on_delete=models.CASCADE,
        related_name="price_history",
    )
    good_code = models.CharField(max_length=30)
    tick = models.PositiveIntegerField()
    price = models.FloatField()
    supply = models.FloatField()
    demand = models.FloatField()

    class Meta:
        unique_together = ("zone_economy", "good_code", "tick")
        indexes = [
            models.Index(fields=["zone_economy", "good_code", "tick"]),
        ]


class AgentInventory(models.Model):
    """An agent's economic holdings: goods and cash.

    Replaces the single Agent.wealth float with a structured inventory.
    Agent.wealth continues to exist as a computed summary (total value
    of all holdings + cash + property) for backward compatibility with
    existing modules that read it.
    """

    agent = models.OneToOneField(
        "agents.Agent",
        on_delete=models.CASCADE,
        related_name="inventory",
    )
    holdings = models.JSONField(
        default=dict,
        help_text="{good_code: quantity}",
    )
    cash = models.JSONField(
        default=dict,
        help_text="{currency_code: amount}",
    )

    def __str__(self):
        return f"Inventory of {self.agent.name}"


# -- Property, fiscal, and ledger models --


class Property(models.Model):
    """An owned productive asset (land, workshop, factory, etc.).

    Rent is NOT a stored rate. It emerges from actual zone production
    multiplied by the property's production_bonus. This follows
    Ricardo's (1817) theory where rent is determined by differential
    land fertility, not by an arbitrary percentage.

    Simplification: the full Ricardian model computes rent as the
    surplus over the marginal (least fertile) land. This implementation
    uses proportional bonus as an approximation. The qualitative
    behavior is correct (fertile land yields more rent), but the
    quantitative derivation is simplified.
    """

    OWNER_TYPES = [
        ("agent", "Agent"),
        ("government", "Government"),
        ("commons", "Commons (unowned)"),
    ]

    simulation = models.ForeignKey(
        "simulation.Simulation",
        on_delete=models.CASCADE,
        related_name="properties",
    )
    owner = models.ForeignKey(
        "agents.Agent",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="owned_properties",
    )
    owner_type = models.CharField(max_length=20, choices=OWNER_TYPES)
    zone = models.ForeignKey(
        "world.Zone",
        on_delete=models.CASCADE,
        related_name="properties",
    )
    property_type = models.CharField(max_length=30)
    name = models.CharField(max_length=255)
    value = models.FloatField(
        help_text="Estimated value in primary currency",
    )
    production_bonus = models.JSONField(
        default=dict,
        help_text="{good_code: multiplier} -- how much this property "
        "boosts production of each good in its zone",
    )
    config = models.JSONField(default=dict)

    class Meta:
        indexes = [
            models.Index(fields=["simulation", "owner_type"]),
            models.Index(fields=["simulation", "zone"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.property_type}, {self.owner_type})"


class TaxPolicy(models.Model):
    """Fiscal policy for the simulation.

    Spec 1 implements flat income tax only. Spec 2 will add progressive
    rates, property tax, and tariffs via the config JSONField.
    """

    simulation = models.OneToOneField(
        "simulation.Simulation",
        on_delete=models.CASCADE,
        related_name="tax_policy",
    )
    income_tax_rate = models.FloatField(
        help_text="Flat income tax rate (0.0-1.0). Applied to wages + rent.",
    )
    config = models.JSONField(
        default=dict,
        help_text="Extensible for spec 2: progressive rates, property tax, tariffs",
    )

    def __str__(self):
        return f"TaxPolicy ({self.income_tax_rate:.0%})"


class EconomicLedger(models.Model):
    """Record of economic transactions.

    Clean replacement for the legacy EconomicTransaction in
    world/models.py which used integer IDs instead of proper
    ForeignKeys. All new transactions use this model.
    """

    TRANSACTION_TYPES = [
        ("production", "Production"),
        ("trade", "Trade"),
        ("tax", "Tax"),
        ("rent", "Rent"),
        ("wage", "Wage"),
    ]

    simulation = models.ForeignKey(
        "simulation.Simulation",
        on_delete=models.CASCADE,
        related_name="economic_ledger",
    )
    tick = models.PositiveIntegerField()
    from_agent = models.ForeignKey(
        "agents.Agent",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="outgoing_transactions",
    )
    to_agent = models.ForeignKey(
        "agents.Agent",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="incoming_transactions",
    )
    currency = models.ForeignKey(
        Currency,
        on_delete=models.CASCADE,
    )
    good_category = models.ForeignKey(
        GoodCategory,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    quantity = models.FloatField(default=0.0)
    unit_price = models.FloatField(default=0.0)
    total_amount = models.FloatField()
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["simulation", "tick"]),
            models.Index(fields=["from_agent"]),
            models.Index(fields=["to_agent"]),
            models.Index(fields=["simulation", "transaction_type", "tick"]),
        ]


# -- Economy template model --


class EconomyTemplate(models.Model):
    """Pre-configured economic template for an era or scenario.

    Templates define the complete economic setup: goods, factors,
    currencies, production functions, tax policy, property types, and
    initial distribution. The user selects a template when creating a
    simulation and can override any field.

    Four default templates are provided: pre_industrial, industrial,
    modern, sci_fi. CES sigma values: pre-industrial 0.5 (Antras 2004),
    industrial 0.8, modern 1.2 (Karabarbounis & Neiman 2014), sci-fi
    1.5 (speculative extrapolation, no empirical basis).
    """

    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    era_label = models.CharField(max_length=100)
    version = models.CharField(max_length=10, default="1.0")
    goods_config = models.JSONField()
    factors_config = models.JSONField()
    currencies_config = models.JSONField()
    production_config = models.JSONField()
    tax_config = models.JSONField()
    properties_config = models.JSONField()
    initial_distribution = models.JSONField()
    config = models.JSONField(default=dict)

    def __str__(self):
        return f"{self.name} ({self.era_label})"

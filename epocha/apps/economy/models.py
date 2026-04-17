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
        ("property_sale", "Property Sale"),
        ("loan_issued", "Loan Issued"),
        ("loan_interest", "Loan Interest"),
        ("expropriation", "Expropriation"),
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


# -- Behavioral economy models (Spec 2, Part 1) --


class Loan(models.Model):
    """A credit relationship between agents or between the banking system and an agent.

    Scientific basis:
    - Minsky, H.P. (1986). Stabilizing an Unstable Economy. Yale University Press.
      Minsky's Financial Instability Hypothesis: agents take on increasing debt
      during stable periods, leading to fragility. The times_rolled_over field
      tracks this progressive leveraging.
    - Stiglitz, J.E. & Weiss, A. (1981). Credit Rationing in Markets with
      Imperfect Information. American Economic Review 71(3), 393-410.
      Asymmetric information between lender and borrower justifies collateral
      requirements and interest rate spreads.
    """

    LENDER_TYPES = [
        ("agent", "Agent"),
        ("banking", "Banking system"),
    ]
    STATUS_CHOICES = [
        ("active", "Active"),
        ("repaid", "Repaid"),
        ("defaulted", "Defaulted"),
        ("rolled_over", "Rolled over"),
    ]

    simulation = models.ForeignKey(
        "simulation.Simulation",
        on_delete=models.CASCADE,
        related_name="loans",
    )
    lender = models.ForeignKey(
        "agents.Agent",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="loans_given",
        help_text="Null when lender_type is 'banking' (system-level credit)",
    )
    borrower = models.ForeignKey(
        "agents.Agent",
        on_delete=models.CASCADE,
        related_name="loans_taken",
    )
    lender_type = models.CharField(max_length=10, choices=LENDER_TYPES)
    principal = models.FloatField(
        help_text="Original loan amount in primary currency",
    )
    interest_rate = models.FloatField(
        help_text="Per-tick interest rate (not annualized)",
    )
    remaining_balance = models.FloatField(
        help_text="Outstanding balance including accrued interest",
    )
    collateral = models.ForeignKey(
        "economy.Property",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="collateralized_loans",
        help_text="Property pledged as collateral (Stiglitz & Weiss 1981)",
    )
    issued_at_tick = models.PositiveIntegerField()
    due_at_tick = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Null for open-ended loans",
    )
    times_rolled_over = models.PositiveIntegerField(
        default=0,
        help_text="Rollover count; high values signal Minsky fragility",
    )
    status = models.CharField(
        max_length=15,
        choices=STATUS_CHOICES,
        default="active",
    )

    class Meta:
        indexes = [
            models.Index(fields=["simulation", "status"]),
            models.Index(fields=["borrower", "status"]),
            models.Index(fields=["lender", "status"]),
        ]

    def __str__(self):
        return (
            f"Loan {self.id}: {self.principal:.0f} "
            f"({self.lender_type} -> {self.borrower}, {self.status})"
        )


class PropertyListing(models.Model):
    """A property listed for sale on the market.

    Fundamental value is computed using the Gordon Growth Model
    (Gordon, M.J. 1959. Dividends, Earnings, and Stock Prices.
    Review of Economics and Statistics 41(2), 99-105):
    V = D / (r - g), where D is the expected rent flow, r is the
    discount rate, and g is the expected rent growth rate.

    The asking_price may diverge from fundamental_value based on
    agent expectations and personality (speculative premium or
    distressed discount).
    """

    STATUS_CHOICES = [
        ("listed", "Listed"),
        ("sold", "Sold"),
        ("withdrawn", "Withdrawn"),
    ]

    property = models.OneToOneField(
        Property,
        on_delete=models.CASCADE,
        related_name="listing",
    )
    asking_price = models.FloatField(
        help_text="Price set by the seller, may differ from fundamental value",
    )
    fundamental_value = models.FloatField(
        help_text="Gordon (1959) intrinsic value: D / (r - g)",
    )
    listed_at_tick = models.PositiveIntegerField()
    status = models.CharField(
        max_length=15,
        choices=STATUS_CHOICES,
        default="listed",
    )

    def __str__(self):
        return (
            f"Listing for {self.property.name}: {self.asking_price:.0f} ({self.status})"
        )


class AgentExpectation(models.Model):
    """An agent's price expectation for a specific good.

    Expectations are updated each tick using the Nerlove (1958)
    adaptive expectations model:
    E_new = lambda * P_actual + (1 - lambda) * E_old

    The lambda_rate (adaptation speed) is modulated by Big Five
    personality traits following Costa & McCrae (1992):
    - High Neuroticism: overreacts to new information (higher lambda)
    - High Openness: more receptive to change (higher lambda)
    - High Conscientiousness: more conservative (lower lambda)

    References:
    - Nerlove, M. (1958). Adaptive Expectations and Cobweb Phenomena.
      Quarterly Journal of Economics 72(2), 227-240.
    - Costa, P.T. & McCrae, R.R. (1992). Revised NEO Personality Inventory
      (NEO PI-R) and NEO Five-Factor Inventory (NEO-FFI) Professional Manual.
      Psychological Assessment Resources.
    """

    TREND_CHOICES = [
        ("rising", "Rising"),
        ("falling", "Falling"),
        ("stable", "Stable"),
    ]

    agent = models.ForeignKey(
        "agents.Agent",
        on_delete=models.CASCADE,
        related_name="expectations",
    )
    good_code = models.CharField(max_length=30)
    expected_price = models.FloatField(
        help_text="Agent's expected price for next tick (Nerlove 1958)",
    )
    trend_direction = models.CharField(
        max_length=10,
        choices=TREND_CHOICES,
        default="stable",
    )
    confidence = models.FloatField(
        default=0.5,
        help_text="0.0 = no confidence, 1.0 = certain. "
        "Increases when expectations match reality.",
    )
    lambda_rate = models.FloatField(
        help_text="Adaptation speed [0.05, 0.95], modulated by "
        "Big Five personality (Costa & McCrae 1992)",
    )
    updated_at_tick = models.PositiveIntegerField()

    class Meta:
        unique_together = ("agent", "good_code")

    def __str__(self):
        return (
            f"{self.agent.name} expects {self.good_code}: "
            f"{self.expected_price:.2f} ({self.trend_direction})"
        )


class BankingState(models.Model):
    """Aggregate banking system state for a simulation.

    Models a simplified aggregate banking sector rather than
    individual banks. The reserve_ratio and confidence_index
    determine credit availability and systemic risk.

    Scientific basis:
    - Diamond, D.W. & Dybvig, P.H. (1983). Bank Runs, Deposit
      Insurance, and Liquidity. Journal of Political Economy 91(3),
      401-419. The confidence_index captures the self-fulfilling
      prophecy dynamic: low confidence triggers withdrawals, which
      further reduce confidence (bank run equilibrium).

    When is_solvent is False, no new loans can be issued and
    existing loans may be called in -- this models the credit
    freeze observed in financial crises.
    """

    simulation = models.OneToOneField(
        "simulation.Simulation",
        on_delete=models.CASCADE,
        related_name="banking_state",
    )
    total_deposits = models.FloatField(
        default=0.0,
        help_text="Sum of all agent deposits in the banking system",
    )
    total_loans_outstanding = models.FloatField(
        default=0.0,
        help_text="Sum of all active loan balances",
    )
    reserve_ratio = models.FloatField(
        help_text="Fraction of deposits held as reserves (0.0-1.0)",
    )
    base_interest_rate = models.FloatField(
        help_text="Base lending rate before risk adjustments",
    )
    is_solvent = models.BooleanField(
        default=True,
        help_text="False triggers credit freeze (Diamond & Dybvig 1983)",
    )
    confidence_index = models.FloatField(
        default=1.0,
        help_text="0.0 = bank run imminent, 1.0 = full confidence",
    )

    def __str__(self):
        status = "solvent" if self.is_solvent else "INSOLVENT"
        return f"Banking ({status}, confidence={self.confidence_index:.2f})"


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

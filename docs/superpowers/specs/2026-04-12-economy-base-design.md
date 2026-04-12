# Economy Base Design Specification

**Date**: 2026-04-12
**Status**: Approved for implementation
**Authors**: design session with three-step critical review and assertion verification
**Paradigm**: Neoclassical general equilibrium (spec 1 of 3)

## Purpose and Scope

Replace the placeholder MVP economy (fixed income per role, fixed cost of
living) with a scientifically grounded economic model based on neoclassical
general equilibrium theory. This is the first of three economic specs:

1. **Spec 1 (this document) — Neoclassical foundations**: CES production,
   market clearing, multi-currency, property, fiscal base
2. **Spec 2 (future) — Behavioral and institutional dynamics**: property
   transfers, debt/credit, labor market matching, prospect theory
   distortions, friction, aspettative
3. **Spec 3 (future) — Financial markets**: assets, exchanges, banking,
   speculation, bubbles, panics, contagion

Each spec is a complete, independently validatable scientific model. The
progression follows the historical development of economics itself:
neoclassical (Arrow, Walras, Fisher, Ricardo) → behavioral (Kahneman,
Minsky, Stiglitz) → computational finance (Arthur, LeBaron, Shiller).

**What this spec delivers:**
- 5 categories of goods + 4 production factors (configurable per scenario)
- CES production function per zone (Arrow et al. 1961)
- Multi-currency system with emergent monetary velocity (Fisher 1911)
- Property ownership with Ricardian emergent rent
- Centralized market with Walrasian price clearing
- Flat income tax with government treasury
- Template system for era-based configuration
- Economic context injected into agent decision prompts
- Feedback from economic indicators to the political system

**What this spec does NOT deliver (deferred to specs 2-3):**
- Property transfers (buy/sell/expropriate)
- Debt and credit
- Labor market with matching
- Big Five distortion of economic decisions
- Belief-system friction on market information
- Financial instruments, exchanges, banking
- Web scraping for real economic data

**Architectural principle**: the model is universally configurable. It
works for any era (neolithic to galactic), any scale (village to planet),
and any context (historical, contemporary, speculative, fictional). All
economic parameters are defined in templates and overridable. No economic
concept is hardcoded in Python.

## Scientific Foundations

- **Production function**: Arrow, K., Chenery, H., Minhas, B., & Solow,
  R. (1961). *Capital-labor substitution and economic efficiency*. Review
  of Economics and Statistics. (CES function with elasticity of
  substitution sigma; generalized to 3+ factors per Shoven & Whalley 1992.)
- **General equilibrium**: Walras, L. (1874). *Elements of Pure Economics*.
  (Tatonnement price adjustment toward market clearing.)
- **Tatonnement convergence caveat**: Scarf, H. (1960). *Some examples of
  global instability of the competitive equilibrium*. International
  Economic Review. (With 3+ goods, tatonnement may not converge; the
  implementation uses max_iterations as safety net.)
- **Tatonnement step size**: the adjustment rate 0.1 is a tunable
  parameter without theoretical derivation, consistent with applied CGE
  practice (Shoven, J. & Whalley, J. 1992. *Applying General Equilibrium*.
  Cambridge University Press, chapter 4).
- **Monetary theory**: Fisher, I. (1911). *The Purchasing Power of Money*.
  Macmillan. (Equation of exchange MV=PQ; velocity V is emergent from
  transaction volume, not a stored constant.)
- **Rent theory**: Ricardo, D. (1817). *On the Principles of Political
  Economy and Taxation*. John Murray. (Rent as differential surplus from
  land fertility; in this implementation, rent emerges proportionally from
  zone production bonus rather than differential computation against
  marginal land. This is a documented simplification; the full Ricardian
  model would require identifying the marginal zone, which is deferred.)
- **Wealth and well-being**: Kahneman, D. & Deaton, A. (2010). *High
  income improves evaluation of life but not emotional well-being*.
  Proceedings of the National Academy of Sciences. (Diminishing mood
  returns from wealth above a satiation point.)
- **Inequality and instability**: Alesina, A. & Perotti, R. (1996).
  *Income distribution, political instability, and investment*. European
  Economic Review. (High Gini → reduced political stability.)
- **Regime transitions**: Acemoglu, D. & Robinson, J. (2006). *Economic
  Origins of Dictatorship and Democracy*. Cambridge University Press.
  (Distributional conflict as driver of political transitions.)
- **Price elasticity values**: Houthakker, H. & Taylor, L. (1970).
  *Consumer Demand in the United States*. Harvard University Press.
  Updated by Andreyeva, T. et al. (2010). (Empirical elasticity values
  for food, materials, manufactures, and luxury goods.)
- **CES sigma by era**: Antras, P. (2004). *Is the U.S. Aggregate
  Production Function Cobb-Douglas?* American Economic Review. (Sigma < 1
  for historical economies.) Karabarbounis, L. & Neiman, B. (2014).
  *The Global Decline of the Labor Share*. Quarterly Journal of Economics.
  (Sigma > 1 for modern economies.)
- **Agent-based economic modeling**: Epstein, J. & Axtell, R. (1996).
  *Growing Artificial Societies*. MIT Press. (Foundation for ABM approach
  to economic simulation, including initial wealth distribution patterns.)
- **General equilibrium computation**: Shoven, J. & Whalley, J. (1992).
  *Applying General Equilibrium*. Cambridge University Press. (Reference
  for CGE model implementation, CES multi-factor extensions, tatonnement
  algorithms.)
- **Fiscal crisis and revolution**: Doyle, W. (1989). *The Oxford History
  of the French Revolution*. Oxford University Press. (Government
  bankruptcy as trigger for political crisis.)
- **Microeconomic theory reference**: Mas-Colell, A., Whinston, M., &
  Green, J. (1995). *Microeconomic Theory*. Oxford University Press.
  (Chapter 17: tatonnement dynamics.)

## Architecture Overview

A new Django app `epocha.apps.economy` replaces `epocha.apps.world.economy`
(the placeholder module). The app owns all economic models, the production
engine, the market clearing mechanism, the fiscal system, and the template
configuration.

The app sits alongside `world` and `agents`, consuming Zone and Agent
data and producing economic state that feeds into the decision engine and
the political system. The existing `process_economy_tick` call in the
simulation engine (`simulation/engine.py`) is redirected to the new app.

### Tick pipeline

```
1. PRODUCTION (CES per zone per agent)
   ↓
2. MARKET CLEARING (Walrasian tatonnement per zone)
   ↓
3. RENT (emergent from zone production, proportional to property bonus)
   ↓
4. WAGES (share of production value for non-owners)
   ↓
5. TAXATION (flat income tax → government treasury)
   ↓
6. MONETARY UPDATE (recompute velocity from transactions)
   ↓
7. WEALTH + MOOD + STABILITY UPDATE (feedback to agents and government)
```

## Data Model

### New app: `epocha.apps.economy`

```python
class Currency(models.Model):
    """A monetary unit in the simulation.

    The total_supply field represents M in Fisher's equation MV=PQ.
    The cached_velocity field is V, recomputed each tick from actual
    transaction volume (not a stored constant). The equation is used
    as a diagnostic check, not as a price-determination mechanism.

    Source: Fisher, I. (1911). The Purchasing Power of Money.
    """

    simulation = models.ForeignKey(
        "simulation.Simulation", on_delete=models.CASCADE,
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


class GoodCategory(models.Model):
    """A category of economic goods in the simulation.

    Price elasticity uses the absolute value convention from standard
    economics: 0 = perfectly inelastic (demand unaffected by price),
    1 = unit elastic, >1 = elastic (demand highly sensitive to price).
    Essential goods (food) are typically 0.2-0.5; luxury goods 1.5-2.5.

    Source for empirical values: Houthakker & Taylor (1970), updated
    by Andreyeva et al. (2010).
    """

    simulation = models.ForeignKey(
        "simulation.Simulation", on_delete=models.CASCADE,
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


class ProductionFactor(models.Model):
    """A factor of production (labor, capital, natural resources, knowledge)."""

    simulation = models.ForeignKey(
        "simulation.Simulation", on_delete=models.CASCADE,
        related_name="production_factors",
    )
    code = models.CharField(max_length=30)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    config = models.JSONField(default=dict)

    class Meta:
        unique_together = ("simulation", "code")


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
        "world.Zone", on_delete=models.CASCADE,
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
        help_text="{good_code: current_price} — snapshot cache",
    )
    market_supply = models.JSONField(default=dict)
    market_demand = models.JSONField(default=dict)


class PriceHistory(models.Model):
    """Historical price record per good per zone per tick.

    Used by the analytics/psychohistoriography system for inflation
    detection, crisis identification, and time-series visualization.
    """

    zone_economy = models.ForeignKey(
        ZoneEconomy, on_delete=models.CASCADE,
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
        "agents.Agent", on_delete=models.CASCADE,
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


class Property(models.Model):
    """An owned productive asset (land, workshop, factory, etc.).

    Rent is NOT a stored rate. It emerges from actual zone production
    multiplied by the property's production_bonus. This follows Ricardo's
    (1817) theory where rent is determined by differential land fertility,
    not by an arbitrary percentage.

    Simplification note: the full Ricardian model computes rent as the
    surplus over the marginal (least fertile) land. This implementation
    uses proportional bonus as an approximation. The qualitative behavior
    is correct (fertile land yields more rent), but the quantitative
    derivation is simplified.
    """

    OWNER_TYPES = [
        ("agent", "Agent"),
        ("government", "Government"),
        ("commons", "Commons (unowned)"),
    ]

    simulation = models.ForeignKey(
        "simulation.Simulation", on_delete=models.CASCADE,
        related_name="properties",
    )
    owner = models.ForeignKey(
        "agents.Agent", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="owned_properties",
    )
    owner_type = models.CharField(max_length=20, choices=OWNER_TYPES)
    zone = models.ForeignKey(
        "world.Zone", on_delete=models.CASCADE,
        related_name="properties",
    )
    property_type = models.CharField(max_length=30)
    name = models.CharField(max_length=255)
    value = models.FloatField(
        help_text="Estimated value in primary currency",
    )
    production_bonus = models.JSONField(
        default=dict,
        help_text="{good_code: multiplier} — how much this property "
                  "boosts production of each good in its zone",
    )
    config = models.JSONField(default=dict)

    class Meta:
        indexes = [
            models.Index(fields=["simulation", "owner_type"]),
            models.Index(fields=["simulation", "zone"]),
        ]


class TaxPolicy(models.Model):
    """Fiscal policy for the simulation.

    Spec 1 implements flat income tax only. Spec 2 will add progressive
    rates, property tax, and tariffs via the config JSONField.
    """

    simulation = models.OneToOneField(
        "simulation.Simulation", on_delete=models.CASCADE,
        related_name="tax_policy",
    )
    income_tax_rate = models.FloatField(
        help_text="Flat income tax rate (0.0-1.0). Applied to wages + rent.",
    )
    config = models.JSONField(
        default=dict,
        help_text="Extensible for spec 2: progressive rates, property tax, tariffs",
    )


class EconomicLedger(models.Model):
    """Record of economic transactions.

    Clean replacement for the legacy EconomicTransaction in world/models.py
    which used integer IDs instead of proper ForeignKeys. All new
    transactions use this model; the legacy model is kept for backward
    compatibility with existing simulations.
    """

    TRANSACTION_TYPES = [
        ("production", "Production"),
        ("trade", "Trade"),
        ("tax", "Tax"),
        ("rent", "Rent"),
        ("wage", "Wage"),
    ]

    simulation = models.ForeignKey(
        "simulation.Simulation", on_delete=models.CASCADE,
        related_name="economic_ledger",
    )
    tick = models.PositiveIntegerField()
    from_agent = models.ForeignKey(
        "agents.Agent", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="outgoing_transactions",
    )
    to_agent = models.ForeignKey(
        "agents.Agent", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="incoming_transactions",
    )
    currency = models.ForeignKey(
        Currency, on_delete=models.CASCADE,
    )
    good_category = models.ForeignKey(
        GoodCategory, null=True, blank=True,
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


class EconomyTemplate(models.Model):
    """Pre-configured economic template for an era or scenario.

    Templates define the complete economic setup: goods, factors,
    currencies, production functions, tax policy, property types, and
    initial distribution. The user selects a template when creating a
    simulation and can override any field.

    Templates are stored in the database (not config files) for
    extensibility: users and the Knowledge Graph can create custom
    templates.
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
```

### Modification to existing models

The `Government` model in `world/models.py` gains a treasury field:

```python
# Added to Government model
government_treasury = models.JSONField(
    default=dict,
    help_text="{currency_code: amount} — tax revenue collected",
)
```

The `Agent.wealth` field remains as-is but is now updated by the economy
app as a computed summary (total value of inventory + cash + property
value) at the end of each economic tick, maintaining backward compatibility
with all existing modules that read it.

## Production Engine

### CES Production Function

For each working agent in each zone, output is computed as:

```
Q = A * [sum_i(alpha_i * X_i^rho)]^(1/rho)

where:
  rho = (sigma - 1) / sigma
  sigma = elasticity of substitution (from template, per era)
  A = total factor productivity (scale parameter from zone config)
  alpha_i = factor weight (normalized to sum to 1)
  X_i = factor input quantity:
    - labor: agent skill weight for their role (from template)
    - capital: sum of property production_bonus in the zone for this good
    - natural_resources: zone abundance for this factor
    - knowledge: simulation-level technology factor (from template)

Source: Arrow et al. (1961), extended to 3+ factors per
Shoven & Whalley (1992), chapter 3.
```

The good produced depends on the agent's role as mapped in the template
`role_production` config. If the role is unmapped, the agent produces the
good with the highest production_config scale factor in their zone.

Every agent consumes 1 unit of essential goods (is_essential=True) per
tick regardless of action chosen (rest, socialize, etc.). Only agents who
chose `work` produce output. Non-working agents consume without producing.

## Market Clearing

### Walrasian Tatonnement

Per zone, per tick:

```
1. Collect supply: for each agent, offer = holdings - subsistence_reserve
   (subsistence_reserve = 1 unit per essential good per tick)
   Agents offer all non-essential goods to the market.

2. Collect demand: for each agent:
   - Essential goods: demand = max(0, subsistence_need - current_holdings)
   - Non-essential goods: demand proportional to available cash and
     price elasticity of the good

3. Price adjustment (iterate until convergence or max_iterations):
   For each good category:
     excess = total_demand - total_supply
     P_new = P_old * (1 + adjustment_rate * excess / max(total_supply, epsilon))
   Convergence when |excess/supply| < convergence_threshold for all goods.

   Parameters (tunable, no theoretical derivation for specific values):
     adjustment_rate = 0.1
     max_iterations = 50
     convergence_threshold = 0.01
     epsilon = 0.001 (prevents division by zero)

   Source: Walras (1874) for the mechanism. Scarf (1960) for the
   non-convergence warning. Shoven & Whalley (1992) ch. 4 for applied
   CGE practice with iterative methods.

4. Execute trades at equilibrium prices:
   - Match supply and demand, limited by the lesser of the two
   - Transfer goods and cash between agents
   - Record all transactions in EconomicLedger
   - Update ZoneEconomy.market_prices, market_supply, market_demand
   - Write PriceHistory row for each good
```

## Rent, Wages, and Taxation

### Rent (emergent, not fixed)

For each property owned by an agent:

```
zone_production = total output of the property's good in the zone
property_share = property.production_bonus[good] / sum(all bonuses in zone)
rent = zone_production * property_share * market_price[good]

Source: Ricardo (1817). Simplification: proportional to bonus instead
of differential surplus vs marginal land. Qualitatively correct
(fertile land yields more), quantitatively approximate.
```

### Wages

Agents working in a zone where they do not own property receive a wage:

```
wage = agent_output_value * wage_share

wage_share is a template parameter (default 0.6 for pre-industrial,
0.7 for modern). In spec 1 this is a fixed share; spec 2 replaces it
with Mortensen-Pissarides matching.
```

### Taxation and Government Treasury

```
taxable_income = wages + rent + trade_profit (per agent per tick)
tax = taxable_income * income_tax_rate
government_treasury[currency] += tax

Government bankruptcy occurs when treasury < 0. This triggers a
political crisis via the government.stability indicator.

Source for bankruptcy-as-crisis: Doyle (1989), documenting the
French fiscal crisis of 1789.
```

## Economic Context in Decision Engine

The existing `_build_context` function in `agents/decision.py` gains an
`economic_context` parameter built by the economy app:

```
Your economic situation:
- Cash: {amount} {currency_symbol}
- Inventory: {good}: {qty} units (x{count} goods)
- Properties owned: {count} ({types})
- Income this tick: {total} (wages: {w}, rent: {r})
- Taxes paid: {tax}
- Total wealth: {wealth} {currency_symbol}

Market in {zone_name}:
- {good}: {price} {symbol}/unit ({change}% vs last tick{shortage_warning})
(repeated for each good category)

Economy overview:
- Inflation: {rate}%
- Gini: {value} ({label})
- Government treasury: {status}
```

The `hoard` action is added to the action vocabulary. An agent choosing
`hoard` does not offer goods to the market, reducing supply and
potentially driving prices up.

## Feedback to Political System

| Economic indicator | Political indicator | Mechanism | Source |
|-------------------|--------------------|-----------|----|
| Inflation > 15% | `government.stability` decreases | Price instability erodes confidence | Alesina & Perotti (1996) |
| Gini > 0.6 | `government.popular_legitimacy` decreases | Inequality delegitimizes government | Acemoglu & Robinson (2006) |
| Unemployment > 25% | `government.stability` decreases | Idle population = instability | Empirical, documented as assumption |
| High tax + low services | `government.popular_legitimacy` decreases | Taxation without perceived benefit | Historical pattern, not from specific paper |
| Treasury < 0 | Direct political crisis trigger | Government cannot function | Doyle (1989) |

The thresholds (15%, 0.6, 25%) are tunable parameters, not derived from
specific studies. They are initial values chosen to produce interesting
dynamics in the default scenarios and should be recalibrated after
observing simulation behavior.

## Template System

Four pre-configured templates stored as `EconomyTemplate` rows:

| Template | Era | Sigma | Tax rate | Goods emphasis |
|----------|-----|-------|----------|---------------|
| `pre_industrial` | 1400-1800 | 0.5 | 0.15 | Subsistence dominant |
| `industrial` | 1800-1950 | 0.8 | 0.20 | Manufacture growing |
| `modern` | 1950-present | 1.2 | 0.30 | Services dominant |
| `sci_fi` | Future/fantasy | 1.5 | 0.25 | Knowledge dominant |

Sigma values: pre-industrial and industrial from Antras (2004); modern
from Karabarbounis & Neiman (2014); sci-fi is speculative (extrapolation
of the upward trend, no empirical basis).

Tax rates: pre-industrial approximates the dime royale (~10-15% of
agricultural output); industrial approximates early income taxes (~15-25%);
modern approximates OECD average (~30%); sci-fi is a middle value.
These are defensible starting points, not precise historical values.

Templates are loaded via a data migration. Users can create custom
templates or override any field when creating a simulation.

## Initialization

When `generate_world_from_prompt` creates a simulation, it calls
`initialize_economy(simulation, template_name, overrides)` after creating
World, Zones, and Agents:

1. Select template (user choice, KG suggestion, or default)
2. Create Currency, GoodCategory, ProductionFactor, TaxPolicy from template
3. Create ZoneEconomy for each zone (resources weighted by zone_type)
4. Create AgentInventory for each agent (cash from wealth class distribution)
5. Distribute Property based on template initial_distribution strategy
   (class_based, equal, random, custom)
6. Update Agent.wealth as computed total
7. Write initial PriceHistory at tick 0

## Error Handling

- CES with zero inputs: returns 0 output (no production without factors)
- Tatonnement non-convergence: after max_iterations, use the last
  computed prices with a log warning. Prices are approximate but not
  catastrophically wrong.
- Division by zero in market clearing: epsilon floor on supply
- Negative cash after purchase: transaction rejected, agent does not buy
- Government treasury negative: trigger political crisis, log warning

## Testing Strategy

- Unit tests for CES function: verify Cobb-Douglas behavior at sigma=1,
  Leontief at sigma→0, scaling with A, factor substitution
- Unit tests for tatonnement: convergence with 2 goods, convergence
  with 5 goods, non-convergence handling, price stability check
- Unit tests for rent computation: zero rent for no-bonus property,
  positive rent proportional to bonus, no rent for empty zone
- Integration test: full tick pipeline on a small scenario (3 agents,
  2 zones, 1 currency), verify prices change, wealth redistributes,
  taxes collected, Fisher MV≈PQ diagnostic passes
- Template test: load pre_industrial template, verify all entities created
- Backward compatibility test: existing simulations without economy app
  continue to work (Agent.wealth unchanged)
- Regression test: existing 456 tests still pass

All tests use PostgreSQL. No SQLite.

## Migration Path

- New app `epocha.apps.economy` registered in INSTALLED_APPS
- `simulation/engine.py`: `process_economy_tick` call redirected to new app
- `world/economy.py`: deprecated, kept for existing simulations, new
  simulations use economy app
- `Agent.wealth`: maintained as computed field, updated by economy app
- `Government`: gains `government_treasury` JSONField via migration
- Existing simulations: unaffected (no economy app entities created for
  them, old economy.py still runs for them)

## Known Limitations

- **Static property ownership**: properties are assigned at world
  generation and do not change hands during simulation. Dynamic property
  markets are deferred to spec 2.
- **Rational economic agents**: agents make economically optimal decisions
  (sell surplus, buy needs). Behavioral biases (prospect theory, loss
  aversion, herd behavior) are deferred to spec 2.
- **Perfect local information**: agents see all prices in their zone.
  Information friction (only seeing prices for goods they trade) is
  deferred to spec 2.
- **Fixed wage share**: the labor-capital split is a template parameter,
  not determined by market forces. Spec 2 replaces this with matching
  theory.
- **Single market per zone**: no distinction between wholesale and retail,
  no intermediaries. All agents trade at the same market.
- **Ricardian rent simplification**: proportional to production bonus
  rather than computed as differential surplus over marginal land.
- **Tatonnement tunable parameters**: adjustment_rate, max_iterations,
  convergence_threshold have no theoretical derivation. Initial values
  are practical choices to be recalibrated.
- **Fiscal simplification**: flat tax only, no progressive rates, no
  property tax, no tariffs. Government spending not modeled (taxes
  accumulate in treasury but are not redistributed). Deferred to spec 2.
- **No inter-zone trade**: each zone is a closed market. Goods produced
  in zone A cannot be sold in zone B. Inter-zone trade with transport
  costs is deferred to spec 2.

## FAQ

### Production

**Q: Why CES and not Cobb-Douglas directly?**
A: CES is the generalization that includes Cobb-Douglas (sigma=1) and
Leontief (sigma→0) as special cases. One implementation covers all eras
by changing a single parameter. A pure Cobb-Douglas implementation would
need to be replaced when we model pre-industrial economies where factor
substitution is limited.

**Q: What happens when an agent produces but the zone has no market demand?**
A: The goods enter the agent's inventory. At market clearing, if supply
exceeds demand, the price drops (tatonnement lowers it). If the price
drops to near-zero, the goods are effectively worthless but still exist
in the inventory. The agent's computed wealth decreases.

**Q: Why normalize CES factor weights to sum to 1?**
A: The CES function with unnormalized weights can produce scale artifacts
where changing one weight affects the overall output level, not just the
factor mix. Normalization ensures the weights control only the relative
importance of factors, while the scale parameter A controls the absolute
output level. This is standard practice in applied CGE (Shoven & Whalley
1992).

### Market

**Q: Why Walrasian tatonnement and not a more modern clearing mechanism?**
A: Tatonnement is the simplest mechanism that produces well-defined
equilibrium prices from supply and demand. More sophisticated mechanisms
(double auction, order book) are realistic for financial markets but
overkill for goods markets with 5 categories. The financial market
mechanism in spec 3 will use a different approach.

**Q: What if tatonnement doesn't converge?**
A: The max_iterations safety net ensures the algorithm always terminates.
Non-converged prices are the last iteration's values, which are
approximate but not catastrophically wrong (they reflect the direction of
excess demand/supply even if not at equilibrium). A log warning is emitted
for monitoring.

### Currency

**Q: Why is velocity recomputed and not stored as a constant?**
A: In Fisher's framework, V = PQ/M, meaning velocity is determined by
the actual volume of economic activity. Storing it as a constant would
assume the economy's transactional intensity never changes, which
contradicts the purpose of simulating economic dynamics. A crisis that
reduces trading (agents hoard instead of spending) should naturally
reduce velocity.

**Q: Why multi-currency from day one?**
A: Adding a currency FK to every price field later would require touching
every model and every query in the economy app. The marginal cost of
multi-currency now (one extra FK) is trivial compared to the refactoring
cost later. Spec 1 creates one currency per simulation; the architecture
supports N.

### Property and Rent

**Q: Why doesn't rent use the full Ricardian differential model?**
A: The full model requires identifying the "marginal land" (least
productive land in use) and computing each property's surplus over it.
This requires global knowledge of all zones' productivity, which is
computationally cheap but conceptually complex to configure correctly in
a template. The proportional approximation produces qualitatively correct
behavior (fertile land = more rent) with simpler configuration. The full
model is a candidate for spec 2.

### Integration

**Q: Can existing simulations still run after this migration?**
A: Yes. Existing simulations have no economy app entities. The simulation
engine detects whether a simulation has an associated EconomyTemplate and
dispatches to the new or old economy code accordingly. The old
`world/economy.py` is kept but deprecated.

**Q: How does hoard differ from simply not selling?**
A: Functionally, hoard means the agent does not offer any goods to the
market this tick. The market sees reduced supply, which drives prices up.
The difference from "not selling" is intentional: the LLM chose to hoard
based on perceived economic conditions, creating a feedback loop (fear →
hoard → scarcity → higher prices → more fear).

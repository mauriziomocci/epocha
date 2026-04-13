# Economy Behavioral Design Specification (Spec 2)

**Date**: 2026-04-13
**Status**: Approved for implementation
**Authors**: design session with three-step critical review and assertion verification
**Paradigm**: Behavioral economics (spec 2 of 3)

## Purpose and Scope

Add behavioral economics to the neoclassical foundation of Spec 1. This
spec introduces three interconnected systems that transform the economy
from a rational equilibrium model into one capable of producing crises,
bubbles, and panics:

1. **Debt and credit** — agents borrow and lend, creating leverage and
   financial fragility. The Minsky cycle (hedge → speculative → Ponzi →
   crisis) emerges from the interaction of debt, refinancing, and default.
2. **Property transfers** — properties become tradeable assets with
   market-determined prices. Expropriation connects economic ownership to
   political regime transitions.
3. **Adaptive expectations** — agents form beliefs about future prices
   from recent trends, modulated by their Big Five personality. This
   creates heterogeneous expectations that drive speculation and panic.

**Scientific paradigm**: behavioral economics (Minsky 1986, Kahneman &
Tversky 1979, Nerlove 1958, Simon 1955), extending the neoclassical
foundation (Arrow 1961, Walras 1874) with bounded rationality, financial
fragility, and heterogeneous expectations.

**What this spec delivers:**
- Bilateral loans between agents + institutional banking with fractional
  reserve
- Loan rollover mechanism enabling the full Minsky cycle
- Default with collateral seizure and cascading contagion
- Bank run as emergent behavior via information flow (not hardcoded
  threshold)
- Property market with listing, bidding, and transfer
- Government expropriation linked to regime transitions
- Dynamic property valuation (Gordon model)
- Adaptive expectations with Big Five personality modulation
- Interest rate determination via credit market equilibrium
- Integration with reputation, information flow, and political systems

**What this spec does NOT deliver (deferred):**
- Full prospect theory utility function (Spec 2b or 3)
- Labor market matching / Mortensen-Pissarides (Spec 2b or 3)
- Information friction on goods prices / Stiglitz (Spec 2b or 3)
- Multiple independent banks as agents (Spec 3)
- Financial instruments: stocks, bonds, derivatives (Spec 3)
- Stock exchanges and order books (Spec 3)

**Depends on:** Economy Spec 1 (neoclassical) — completed and functional.

## Scientific Foundations

- **Financial instability**: Minsky, H. P. (1986). *Stabilizing an
  Unstable Economy*. Yale University Press. (Hedge → speculative → Ponzi
  finance cycle; instability as endogenous to capitalism.)
- **Bank runs**: Diamond, D. & Dybvig, P. (1983). *Bank Runs, Deposit
  Insurance, and Liquidity*. Journal of Political Economy. (Bank runs as
  coordination game with multiple equilibria; sequential service
  constraint creates incentive to run.)
- **Credit rationing**: Stiglitz, J. & Weiss, A. (1981). *Credit
  Rationing in Markets with Imperfect Information*. American Economic
  Review. (Lenders ration credit rather than raise rates because higher
  rates attract riskier borrowers.)
- **Interest rate theory**: Wicksell, K. (1898). *Interest and Prices*.
  (The natural rate of interest equilibrates savings and investment.)
- **Asset pricing**: Gordon, M. (1959). *Dividends, Earnings, and Stock
  Prices*. Review of Economics and Statistics. (P = R / (r - g); the
  dividend discount model for asset valuation.)
- **Adaptive expectations**: Nerlove, M. (1958). *Adaptive Expectations
  and Cobweb Phenomena*. Quarterly Journal of Economics. (Agents update
  expectations as weighted average of prior expectation and current
  observation.)
- **Bounded rationality**: Simon, H. (1955). *A Behavioral Model of
  Rational Choice*. Quarterly Journal of Economics. (Agents satisfice
  rather than optimize; justification for adaptive over rational
  expectations.)
- **Heterogeneous expectations**: Hommes, C. (2011). *The Heterogeneous
  Expectations Hypothesis*. Journal of Economic Dynamics and Control.
  (Empirical evidence that agents use heterogeneous adaptive heuristics,
  not rational expectations.)
- **Prospect theory (partial)**: Kahneman, D. & Tversky, A. (1979).
  *Prospect Theory: An Analysis of Decision under Risk*. Econometrica.
  (Loss aversion and asymmetric risk perception; used here for the
  personality-expectation link, not the full utility function.)
- **Financial contagion**: Allen, F. & Gale, D. (2000). *Financial
  Contagion*. Journal of Political Economy. (Network topology of debt
  determines contagion speed; complete networks absorb shocks, incomplete
  networks propagate them.)
- **Personality traits**: Costa, P. T. & McCrae, R. R. (1992). *NEO
  PI-R Professional Manual*. (Big Five personality dimensions; used to
  modulate expectation formation speed.)
- **Noise traders**: De Long, J. B. et al. (1990). *Noise Trader Risk
  in Financial Markets*. Journal of Political Economy. (Heterogeneous
  expectations create systematic price deviations from fundamentals.)
- **Regime change and property**: Acemoglu, D. & Robinson, J. (2006).
  *Economic Origins of Dictatorship and Democracy*. (Regime transitions
  driven by distributional conflict over property.)

### Why adaptive expectations and not rational expectations

The dominant paradigm in academic macroeconomics is rational expectations
(Muth 1961): agents know the true model of the economy and form
statistically optimal forecasts. We deliberately choose adaptive
expectations for three reasons:

1. **Bounded rationality** (Simon 1955): agents in Epocha have limited
   information (filtered by the belief system) and limited cognitive
   capacity (personality-dependent). Rational expectations would require
   omniscience inconsistent with the agent model.
2. **Empirical evidence** (Hommes 2011): laboratory experiments and survey
   data show people use heterogeneous adaptive rules, not rational
   forecasting. Adaptive expectations produce dynamics (bubbles, crashes)
   that rational expectations cannot.
3. **Architectural consistency**: Epocha already models information
   distortion (Allport & Postman) and belief filtering (personality-
   dependent acceptance). Rational expectations would bypass these
   systems entirely. Adaptive expectations integrate with them naturally.

This is a deliberate design choice documented for scientific transparency,
not a simplification made for convenience.

## Architecture Overview

Three new modules in `epocha.apps.economy`:

- `credit.py` — loan creation, interest computation, rollover, default,
  cascade, banking mechanics
- `property_market.py` — listing, bidding, transfer, valuation, expropriation
- `expectations.py` — adaptive expectation formation with Big Five
  modulation

These integrate into the existing tick pipeline (Spec 1) as additional
steps inserted between existing steps.

### Extended tick pipeline

```
 1. PRODUCTION (CES, Spec 1)
 2. EXPECTATIONS UPDATE (new: adaptive expectations from trends + Big Five)
 3. MARKET CLEARING (tatonnement, Spec 1)
 4. PROPERTY MARKET (new: listings, bids, transfers, valuation)
 5. CREDIT MARKET (new: loan requests, issuance, interest rate adjustment)
 6. LOAN SERVICING (new: repayments, rollovers, defaults, cascade)
 7. RENT (emergent, Spec 1)
 8. WAGES (Spec 1)
 9. TAXATION (Spec 1)
10. MONETARY UPDATE (Spec 1 + banking multiplier update)
11. PROPERTY VALUATION (new: Gordon model R/(r-g) recomputation)
12. WEALTH + MOOD + STABILITY (Spec 1 + debt stress effects)
```

## Data Model

### New models

```python
class Loan(models.Model):
    """A debt contract between two parties.

    Loans can be bilateral (agent-to-agent) or institutional (banking
    system to agent). The Minsky classification (hedge/speculative/Ponzi)
    is computed dynamically from the borrower's income vs debt service,
    not stored as a field.

    Rollover: when a loan reaches due_at_tick and the borrower cannot
    repay the principal but CAN pay interest, the loan can be rolled
    over (extended with potentially worse terms). This is the mechanism
    that enables Minsky's speculative finance stage: the borrower is
    solvent on interest but depends on refinancing for the principal.

    Source: Minsky (1986) for the instability cycle.
    Collateral: Stiglitz & Weiss (1981) for credit rationing.
    """

    LENDER_TYPES = [
        ("agent", "Agent (bilateral)"),
        ("banking", "Banking institution"),
    ]

    STATUS_CHOICES = [
        ("active", "Active"),
        ("repaid", "Repaid"),
        ("defaulted", "Defaulted"),
        ("rolled_over", "Rolled over into new loan"),
    ]

    simulation = models.ForeignKey(
        "simulation.Simulation", on_delete=models.CASCADE,
        related_name="loans",
    )
    lender = models.ForeignKey(
        "agents.Agent", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="loans_given",
    )
    borrower = models.ForeignKey(
        "agents.Agent", on_delete=models.CASCADE,
        related_name="loans_taken",
    )
    lender_type = models.CharField(max_length=20, choices=LENDER_TYPES)
    principal = models.FloatField(
        help_text="Original loan amount in primary currency",
    )
    interest_rate = models.FloatField(
        help_text="Per-tick interest rate. Determined by credit market "
                  "equilibrium (Wicksell 1898) adjusted for borrower risk "
                  "(Stiglitz & Weiss 1981).",
    )
    remaining_balance = models.FloatField()
    collateral = models.ForeignKey(
        "economy.Property", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="securing_loans",
    )
    issued_at_tick = models.PositiveIntegerField()
    due_at_tick = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="Null for demand loans (callable at any time)",
    )
    times_rolled_over = models.PositiveIntegerField(
        default=0,
        help_text="Number of times this loan has been refinanced. "
                  "Minsky: hedge=0, speculative=1+, Ponzi=cannot service interest.",
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")

    class Meta:
        indexes = [
            models.Index(fields=["simulation", "status"]),
            models.Index(fields=["borrower", "status"]),
            models.Index(fields=["lender", "status"]),
        ]


class PropertyListing(models.Model):
    """A property offered for sale on the market.

    Price discovery follows the Gordon Growth Model (Gordon 1959):
    the fundamental value is P = R / max(r - g, 0.01) where R is the
    current rental income, r is the discount rate (market interest rate),
    and g is the trailing growth rate of rental income. The asking price
    may deviate from fundamental value based on the seller's expectations.

    The gap between market price and fundamental value is the definition
    of a bubble: when expectations of growth drive prices above what
    rental income justifies.
    """

    property = models.OneToOneField(
        "economy.Property", on_delete=models.CASCADE,
        related_name="listing",
    )
    asking_price = models.FloatField()
    fundamental_value = models.FloatField(
        help_text="Gordon model value: R / max(r - g, 0.01). "
                  "Deviation from asking_price indicates speculation.",
    )
    listed_at_tick = models.PositiveIntegerField()
    status = models.CharField(
        max_length=20,
        choices=[("listed", "Listed"), ("sold", "Sold"), ("withdrawn", "Withdrawn")],
        default="listed",
    )


class AgentExpectation(models.Model):
    """An agent's adaptive expectation about a future price.

    Updated each tick via the Nerlove (1958) formula:
        E(P_t+1) = E(P_t) + lambda * (P_t - E(P_t))
    which simplifies to:
        E(P_t+1) = lambda * P_t + (1 - lambda) * E(P_t)

    Lambda (adaptation speed) is modulated by Big Five personality:
    - High neuroticism: +0.15 (overreacts to new information)
    - High openness: +0.10 (embraces novelty quickly)
    - High conscientiousness: -0.10 (cautious, slow to update)
    - High agreeableness: herding modifier (moves toward group consensus)

    These personality-lambda mappings are tunable design parameters
    inspired by personality research (Costa & McCrae 1992) but without
    direct empirical calibration of the specific values.

    Source: Nerlove (1958) for the formula.
    Source: Simon (1955) and Hommes (2011) for the choice of adaptive
    over rational expectations (see spec rationale).
    """

    agent = models.ForeignKey(
        "agents.Agent", on_delete=models.CASCADE,
        related_name="expectations",
    )
    good_code = models.CharField(max_length=30)
    expected_price = models.FloatField()
    trend_direction = models.CharField(
        max_length=10,
        choices=[("rising", "Rising"), ("falling", "Falling"), ("stable", "Stable")],
    )
    confidence = models.FloatField(
        default=0.5,
        help_text="0-1: how confident the agent is in this expectation",
    )
    lambda_rate = models.FloatField(
        help_text="Adaptation speed derived from Big Five personality. "
                  "Tunable design parameters, not empirically calibrated.",
    )
    updated_at_tick = models.PositiveIntegerField()

    class Meta:
        unique_together = ("agent", "good_code")
        indexes = [models.Index(fields=["agent", "good_code"])]


class BankingState(models.Model):
    """Aggregate state of the banking system for a simulation.

    Spec 2 models banking as a single institutional entity (aggregate).
    Spec 3 will introduce multiple independent banks as agents.

    The fractional reserve mechanism: for every unit deposited, the bank
    retains reserve_ratio and lends (1 - reserve_ratio). The theoretical
    money multiplier is 1/reserve_ratio, but the ACTUAL multiplier is
    computed as total_loans/total_deposits and will be lower in practice
    because it depends on credit demand and bank willingness to lend.
    The theoretical maximum is a cap, not a target.

    Source: Diamond & Dybvig (1983) for the fractional reserve model.
    Note: the actual multiplier vs theoretical maximum distinction follows
    standard macroeconomic teaching (Mankiw, Principles of Economics,
    ch. 29) and post-2008 empirical evidence showing multipliers well
    below theoretical maximums.
    """

    simulation = models.OneToOneField(
        "simulation.Simulation", on_delete=models.CASCADE,
        related_name="banking_state",
    )
    total_deposits = models.FloatField(default=0.0)
    total_loans_outstanding = models.FloatField(default=0.0)
    reserve_ratio = models.FloatField(
        help_text="Fraction of deposits held in reserve. "
                  "Tunable per template (default 0.1 = 10%).",
    )
    base_interest_rate = models.FloatField(
        help_text="Base lending rate. Adjusted by credit market "
                  "equilibrium each tick (Wicksell 1898).",
    )
    is_solvent = models.BooleanField(default=True)
    confidence_index = models.FloatField(
        default=1.0,
        help_text="Public confidence in the banking system (0-1). "
                  "Drops trigger withdrawal pressure via information flow.",
    )
```

### Modifications to existing models

```python
# In government_types.py, add to each government type config:
"expropriation_policy": "none"  # or "elite_seizure", "nationalize_all", "redistribute"

# "none": democracy, federation, illiberal democracy
# "elite_seizure": revolution transitions — seize elite/wealthy properties
# "nationalize_all": totalitarian, communist transitions
# "redistribute": reform transitions — partial redistribution
```

No structural changes to Agent, Property, Government, or Institution
models. New behavior is in new tables and new logic modules.

## Debt and Credit System

### Loan lifecycle

```
1. REQUEST: borrower needs credit (insufficient cash for purchase,
   debt service, or speculation based on expectations)

2. EVALUATION: credit limit = collateral_value * loan_to_value_ratio
   (template param, default 0.6 for pre-industrial, 0.8 for modern).
   Interest rate = base_rate * (1 + risk_premium * debt_ratio)
   where debt_ratio = existing_debt / total_wealth.
   Source: Stiglitz & Weiss (1981) — higher leverage = higher risk premium.
   Risk_premium is a tunable design parameter (default 1.0).

3. ISSUANCE: if within credit limit, loan created. Cash transferred to
   borrower. If banking loan: BankingState.total_loans_outstanding
   increases (money creation via fractional reserve).

4. SERVICING (each tick): borrower pays interest = remaining_balance *
   interest_rate. Deducted from borrower's cash.

5. AT MATURITY (due_at_tick):
   a. If borrower can repay principal: loan repaid, status="repaid"
   b. If borrower can pay interest but NOT principal: ROLLOVER
      - New loan issued for remaining balance
      - Interest rate may increase (risk re-evaluation)
      - times_rolled_over increments
      - This is Minsky's "speculative finance" stage
   c. If borrower cannot pay interest: DEFAULT
      - This is Minsky's "Ponzi finance" → crisis

6. DEFAULT cascade:
   - Collateral (property) seized by lender
   - Remaining unpaid debt written off (loss for lender)
   - Borrower reputation damaged via information flow
   - If lender's losses exceed threshold: lender may default on own
     debts → cascade
   - Cascade limited to 3 propagation levels per tick (BFS traversal
     of debt graph). Deeper cascades propagate across subsequent ticks.
     This is a computational constraint, not a scientific finding.
   - Source: Allen & Gale (2000) for network topology effects on contagion.
```

### Minsky classification (computed, not stored)

For each agent with active loans, the Minsky stage is computed each tick:

```
income = wages + rent (from last tick)
interest_due = sum(loan.remaining_balance * loan.interest_rate for active loans)
principal_due = sum(loan.remaining_balance for loans at maturity this tick)

if income >= interest_due + principal_due:
    stage = "hedge"       # fully covered, safe
elif income >= interest_due:
    stage = "speculative" # can pay interest, needs to refinance principal
else:
    stage = "ponzi"       # cannot even cover interest, needs asset appreciation
```

This classification is logged for analytics and crisis detection. A
simulation-wide shift from hedge toward Ponzi indicates growing systemic
fragility — the approach of a Minsky moment.

### Interest rate determination

The base interest rate adjusts each tick based on credit market
equilibrium:

```
credit_demand = sum of all loan requests this tick
credit_supply = available lending capacity (deposits * (1 - reserve_ratio)
                - total_loans_outstanding)

r_new = r_old * (1 + credit_adj_rate * (credit_demand - credit_supply)
                 / max(credit_supply, epsilon))

# Separate mechanism from goods tatonnement (different market dynamics).
# Source: Wicksell (1898) for the natural rate concept.
# credit_adj_rate is a tunable design parameter (default 0.02, slower
# than goods market because interest rates are stickier).
```

### Bank run mechanism

Bank runs are NOT triggered by a threshold on `Institution.health` or
`BankingState.confidence_index`. They emerge from the information flow
system already implemented:

1. When bank confidence drops below 0.5 (from default cascades, bad news,
   or government instability), a "banking_concern" memory is created for
   agents in the zone.
2. This memory propagates through the information flow with Big Five
   distortion (high neuroticism agents amplify the concern).
3. Each agent who receives the memory and believes it (belief filter)
   decides whether to withdraw deposits. The LLM decision engine sees
   "Banking confidence is low. Other depositors are withdrawing." in the
   economic context.
4. Withdrawals reduce BankingState.total_deposits. If deposits fall below
   total_loans_outstanding * reserve_ratio, the bank becomes illiquid.
5. Illiquidity confirms the concern → more withdrawals → spiral.

This is a coordination game (Diamond & Dybvig 1983) emerging from
existing systems (information flow + belief filter + LLM decisions),
not a hardcoded mechanism.

## Property Market

### Listing and trading

Each tick, agents can list properties for sale and bid on listed
properties. The decision to sell or buy is driven by:

- **Sell**: agent needs cash (debt service, consumption), or expects
  property value to decrease (adaptive expectation trend = "falling")
- **Buy**: agent has excess cash and expects property value to increase,
  or needs productive capacity

### Price discovery

The fundamental value of a property is computed each tick:

```
R = actual rental income last tick (from distribution.compute_rent)
r = current market interest rate (from BankingState.base_interest_rate)
g = trailing 5-tick average growth rate of R for this property's zone

# Gordon Growth Model (Gordon 1959):
# Cap (r - g) at minimum 0.01 to prevent division by zero when g >= r.
# When g approaches r, the fundamental value becomes very high, indicating
# the market is approaching bubble territory.
fundamental_value = R / max(r - g, 0.01)

# g is computed OBJECTIVELY from historical production data,
# NOT from the agent's subjective expectations. This prevents circularity
# (price depends on expectations which depend on price).
# The difference between the agent's willing-to-pay price (subjective,
# influenced by expectations) and the fundamental value (objective)
# is the measure of speculative excess — the "bubble component."
```

### Expropriation

When a government transition occurs (already implemented in
`government.py`), the new regime's `expropriation_policy` is executed:

```
"none": no property changes (democracy, federation)
"elite_seizure": properties owned by agents with social_class in
    ("elite", "wealthy") are transferred to owner_type="government"
"nationalize_all": ALL agent-owned properties become government-owned
"redistribute": properties above a value threshold are redistributed
    proportionally to agents with social_class in ("working", "poor")
```

This connects the political system to the economic system with real
consequences: a revolution is no longer just a change of government_type
but a redistribution of productive assets.

## Adaptive Expectations

### Formation mechanism

Each tick, for each good category and for property values, agents update
their price expectations:

```
# Nerlove (1958) adaptive expectations formula:
E_new = E_old + lambda * (P_actual - E_old)

# Lambda (adaptation speed) base value: 0.3 (template parameter)
# Modulated by Big Five personality:
lambda = lambda_base
    + (neuroticism - 0.5) * 0.3     # high N: +0.15, low N: -0.15
    + (openness - 0.5) * 0.2        # high O: +0.10, low O: -0.10
    - (conscientiousness - 0.5) * 0.2  # high C: -0.10, low C: +0.10

lambda = clamp(lambda, 0.05, 0.95)  # always between 5% and 95%

# Personality-lambda mappings are tunable design parameters inspired
# by Costa & McCrae (1992) personality research but without direct
# empirical calibration of these specific coefficients. The qualitative
# direction (neuroticism increases reactivity, conscientiousness
# decreases it) is supported by the literature; the magnitudes are not.
```

### Trend detection

```
trend = "rising"  if E_new > P_actual * 1.02   # expect >2% increase
trend = "falling" if E_new < P_actual * 0.98   # expect >2% decrease
trend = "stable"  otherwise

confidence = 1.0 - abs(E_new - P_actual) / max(P_actual, 0.01)
confidence = clamp(confidence, 0.1, 1.0)
```

### Impact on decisions

The expectations are injected into the economic context of the LLM
decision prompt:

```
Price expectations (your assessment):
- Subsistence: RISING (+12% expected) — consider buying or hoarding
- Luxury: FALLING (-5% expected) — consider selling
- Property values in your zone: RISING — your land is appreciating

Your debt situation:
- Active loans: 2 (total 120 LVR, monthly interest 4.8 LVR)
- Debt-to-wealth ratio: 35% (moderate)
- Minsky classification: speculative (can pay interest, will need to
  refinance principal at maturity in 8 ticks)
```

## Integration with Existing Systems

### Credit → Reputation

Default events create strongly negative memories in the reputation
system:

```
# On default:
update_image(holder=lender, target=borrower, action_type="default", tick=tick)
# IMAGE_DELTA for "default" = -0.60 (tunable, strong negative signal)

# Propagate via information flow:
Memory.objects.create(
    agent=lender,
    content=f"{borrower.name} defaulted on a loan of {amount}",
    emotional_weight=0.7,
    source_type="direct",
    tick_created=tick,
)
# This memory propagates as hearsay, degrading the borrower's reputation
# across the social network, making future borrowing harder.
```

### Expectations → Hoard action

When an agent expects prices to rise significantly (trend="rising",
confidence > 0.7), the economic context in the LLM prompt explicitly
suggests hoarding. The agent's personality determines whether they act
on this: high neuroticism agents are more likely to hoard preemptively.
This creates a self-fulfilling prophecy: hoarding reduces supply →
prices rise → confirms expectations → more hoarding.

### Property transfers → Political system

Expropriation is now a concrete economic event:
- `_process_expropriation(simulation, new_government_type)` is called
  when `government.py` executes a regime transition
- Properties are transferred according to the new regime's
  `expropriation_policy`
- Affected agents lose wealth and gain grievance (mood drops, memories
  of loss, potential for counter-revolution)
- This feedback loop between economics and politics is the mechanism
  Acemoglu & Robinson (2006) describe as the driver of regime cycling

### Banking → Monetary system

The banking system affects the monetary dynamics from Spec 1:
- `Currency.total_supply` is now: base money + bank-created credit
- Actual money multiplier = `BankingState.total_loans_outstanding /
  BankingState.total_deposits` (measured, not theoretical)
- Fisher velocity (already computed) reflects both base money and
  credit money transactions
- When the banking system contracts (defaults, withdrawals), the money
  supply effectively shrinks → deflationary pressure

## Template Extensions

The EconomyTemplate gains new fields for Spec 2:

```python
"credit_config": {
    "loan_to_value_ratio": 0.6,     # pre-industrial: conservative
    "base_interest_rate": 0.05,      # 5% per tick
    "risk_premium": 1.0,             # multiplier on debt_ratio
    "max_loan_duration_ticks": 20,   # default maturity
    "credit_adj_rate": 0.02,         # interest rate adjustment speed
    "default_cascade_max_depth": 3,  # BFS depth limit per tick
},
"banking_config": {
    "reserve_ratio": 0.1,            # 10% fractional reserve
    "initial_deposits": 10000.0,     # starting deposits
},
"expectations_config": {
    "lambda_base": 0.3,              # base adaptation speed
    "neuroticism_modifier": 0.3,     # per 0.5 deviation from midpoint
    "openness_modifier": 0.2,
    "conscientiousness_modifier": 0.2,
    "trend_threshold": 0.02,         # 2% to detect rising/falling
},
"expropriation_policies": {
    "democracy": "none",
    "monarchy": "none",
    "revolution": "elite_seizure",
    "totalitarian": "nationalize_all",
    "communist": "nationalize_all",
    "junta": "elite_seizure",
    # ... for all 12 government types
}
```

## Error Handling

- **Loan with negative balance**: capped at 0, loan status set to repaid
- **Default cascade infinite loop**: BFS depth limit (3 per tick) prevents
  unbounded propagation; deeper cascades continue in subsequent ticks
- **Gordon model divergence**: `max(r - g, 0.01)` prevents infinite
  property values; values above `base_price * 1000` are capped
- **Lambda out of range**: clamped to [0.05, 0.95]
- **Bank insolvency**: when `total_deposits < total_loans * reserve_ratio`,
  bank is marked insolvent; no new loans issued; confidence drops;
  information flow propagates concern
- **Expropriation of mortgaged property**: if a seized property has loans
  secured against it, those loans default (collateral gone); lender bears
  the loss

## Testing Strategy

- Unit tests for Minsky classification computation (hedge/speculative/Ponzi
  from income vs debt service)
- Unit tests for loan rollover mechanics (principal unpayable but interest
  payable → new loan with incremented rollover count)
- Unit tests for default cascade (3 agents in chain, first defaults,
  verify cascade propagates to depth 3 and stops)
- Unit tests for Gordon model property valuation with g < r, g ≈ r,
  g > r (verify cap)
- Unit tests for Nerlove adaptive expectations with different lambda values
- Unit tests for Big Five → lambda modulation
- Unit tests for interest rate adjustment (credit_demand > supply → rate
  rises)
- Integration test: create simulation with economy, issue loans, run 10
  ticks, verify some agents reach speculative/Ponzi stage
- Integration test: expropriation after government transition changes
  property ownership
- Integration test: bank confidence drop → withdrawal cascade via
  information flow

All tests use PostgreSQL. No SQLite.

## Known Limitations

- **Single aggregate bank**: Spec 2 models banking as one institutional
  entity, not multiple independent banks. This prevents modeling interbank
  contagion (Bank A defaults, Bank B exposed). Spec 3 will introduce
  multiple banks as agents.
- **No deposit insurance**: Diamond & Dybvig (1983) show deposit insurance
  eliminates bank runs by removing the coordination incentive. This is not
  modeled — all deposits are uninsured. This makes bank runs more likely
  than in modern economies with FDIC/equivalent.
- **Expropriation is immediate**: in reality, nationalization takes time
  and may be contested legally. The model transfers ownership in one tick.
- **No bankruptcy protection**: defaulted agents lose collateral and
  reputation but continue to exist. Real bankruptcy involves legal
  proceedings, debt restructuring, and potentially discharge. Simplified
  to immediate collateral seizure.
- **Adaptive expectations are backward-looking**: agents cannot anticipate
  structural breaks (e.g., a war starting) until prices actually change.
  This is a known limitation of adaptive vs rational expectations.
- **Personality-lambda coefficients are not empirically calibrated**: the
  direction of each Big Five trait's effect on adaptation speed is supported
  by personality research, but the specific coefficients (0.3, 0.2, 0.2)
  are design parameters that should be recalibrated after observing
  simulation behavior.
- **Default cascade depth limit is computational, not scientific**: the
  3-level BFS limit per tick is a design constraint. In reality, cascades
  can propagate instantaneously through the entire network. The multi-tick
  propagation is a reasonable approximation for tick-based simulation.

## FAQ

### Debt

**Q: Why both bilateral and banking credit?**
A: Historical accuracy. Pre-industrial economies relied primarily on
bilateral lending (merchants lending to farmers). Modern economies use
banking intermediation. The coexistence is the reality in every era.
The template determines the mix.

**Q: Why rollover instead of just default at maturity?**
A: Rollover IS the Minsky cycle. Without it, agents go from hedge directly
to default — there's no speculative stage. The speculative stage (can pay
interest, needs to refinance principal) is where most of the interesting
dynamics happen: the economy looks stable but is actually fragile because
everyone is refinancing.

**Q: How does the default cascade stop?**
A: Two mechanisms. First, the BFS depth limit (3 per tick) caps immediate
propagation. Second, lenders who absorb losses but remain solvent (their
wealth exceeds the loss) do not cascade. The cascade stops when either
the depth limit is reached or a sufficiently wealthy lender absorbs the
shock. Allen & Gale (2000) show that a few well-capitalized nodes can
prevent systemic collapse — this emerges naturally in our model.

### Property

**Q: Why is fundamental value computed objectively but market price is
subjective?**
A: This is the standard distinction in asset pricing. Fundamental value
(Gordon model from actual rental income and growth) is what the property
is "worth" based on cash flows. Market price is what someone is willing
to pay, which includes expectations and speculation. The gap between the
two is the bubble. If we computed fundamental value from expectations,
the bubble would be invisible (the "fundamental" would be inflated too).

**Q: What happens to loans secured by expropriated property?**
A: They default. The collateral is gone (seized by the new government),
so the lender bears the full loss. This is historically accurate:
revolutions destroy creditor wealth (French assignats, Russian bonds
after 1917). The lender may cascade if the loss is large enough.

### Expectations

**Q: Why not rational expectations?**
A: See the dedicated rationale section above. Short version: bounded
rationality is more realistic, produces richer dynamics (bubbles, panics),
and integrates with existing information distortion and belief systems.

**Q: Can expectations create self-fulfilling prophecies?**
A: Yes, and that's the point. If enough agents expect prices to rise and
act on it (buying, hoarding), prices actually rise, confirming the
expectation. This positive feedback loop is the mechanism behind
speculative bubbles (De Long et al. 1990, Shiller 2000). The bubble
pops when reality (declining production, rising interest rates, a
political shock) overwhelms expectations.

### Banking

**Q: Why not multiple independent banks?**
A: Complexity management. Multiple banks with interbank lending, different
reserve ratios, and independent solvency is a significant system.
Spec 2's aggregate bank captures the essential dynamics (fractional
reserve, money creation, bank run). Spec 3 will disaggregate into
individual banks when building the financial market infrastructure.

**Q: Is the money multiplier realistic?**
A: The theoretical multiplier (1/reserve_ratio = 10 with 10% reserve) is
an upper bound. The actual multiplier in the model is computed from
real loan/deposit ratios and will be lower, reflecting real-world
evidence (post-2008, actual multipliers in advanced economies were 3-5,
not 10). The theoretical maximum is a cap, not a target.

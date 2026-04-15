# Economy Behavioral Integration Design (Spec 2 Part 3)

**Date**: 2026-04-15
**Status**: Approved for implementation
**Paradigm**: Behavioral economy integration into simulation engine
**Depends on**: Economy Spec 2 Part 1 (data layer + expectations) and Part 2 (credit + banking) -- both completed.
**Audit**: adversarial review completed 2026-04-15, all findings resolved (see Audit Resolution Log at end).

## Purpose and Scope

Wire the behavioral economy subsystems (expectations, credit, banking) into the
simulation so that agents perceive, react to, and drive economic dynamics through
LLM-based decisions. This plan also adds the property market and connects
government transitions to property redistribution.

**What this plan delivers:**

1. Extended economic context in agent decision prompts (expectations, debt,
   Minsky classification, banking state, credit availability)
2. Three new LLM-driven actions: `borrow`, `sell_property`, `buy_property`
3. Property market with Gordon (1959) valuation, listing, and matching
4. Expropriation on government transitions (Acemoglu & Robinson 2006)
5. Hoard-expectations link (hoard decision reduces supply at next tick)
6. Banking confidence broadcast via information flow (Diamond & Dybvig 1983)
7. Banking initialization in economy setup
8. Dynamic aggregate deposit tracking (total_deposits recalculated each tick)
9. Prerequisite fixes: save all template configs to simulation.config,
   double-pledging protection on collateral, dead agent loan default

**What this plan does NOT deliver (deferred):**

- Property negotiation / bidding wars (simple take-it-or-leave-it pricing)
- Agent-to-agent lending decisions via LLM (only banking system loans)
- Multiple independent banks (Spec 3)
- Full prospect theory utility (Spec 2b or 3)
- Per-agent deposit tracking (Spec 3)

## Scientific Foundations

- **Asset pricing**: Gordon, M. (1959). *Dividends, Earnings, and Stock Prices*.
  Review of Economics and Statistics 41(2), 99-105. (V = D / (r - g))
- **Property and regime change**: Acemoglu, D. & Robinson, J. (2006). *Economic
  Origins of Dictatorship and Democracy*. Cambridge University Press.
- **Bank runs**: Diamond, D. & Dybvig, P. (1983). *Bank Runs, Deposit Insurance,
  and Liquidity*. Journal of Political Economy 91(3), 401-419.
- **Financial instability**: Minsky, H.P. (1986). *Stabilizing an Unstable
  Economy*. Yale University Press.
- **Credit rationing**: Stiglitz, J. & Weiss, A. (1981). *Credit Rationing in
  Markets with Imperfect Information*. American Economic Review 71(3), 393-410.
- **Adaptive expectations**: Nerlove, M. (1958). *Adaptive Expectations and
  Cobweb Phenomena*. Quarterly Journal of Economics 72(2), 227-240.
- **Speculative bubbles**: Shiller, R.J. (2000). *Irrational Exuberance*.
  Princeton University Press. (bubble as divergence between market price and
  fundamental value)

## Architecture Overview

No new models are required -- Loan, PropertyListing, AgentExpectation, and
BankingState already exist from Part 1. One new module (`property_market.py`)
is created; existing modules (`context.py`, `engine.py`, `initialization.py`,
`decision.py`, `government.py`, `formatters.py`) are extended.

**Prerequisite fix (C-6):** `initialize_economy` currently saves only
`production_config` to `simulation.config`. This plan extends it to also
save `credit_config`, `banking_config`, `expectations_config`, and
`expropriation_policies`. Without this fix, all config lookups in the
behavioral subsystems would fail at runtime.

### Extended Tick Pipeline

```
 0. EXPECTATIONS UPDATE (existing: Nerlove adaptive)
 1. PRODUCTION (existing: CES)
 2. MARKET CLEARING (existing: tatonnement; NOW with is_hoarding from previous tick)
 3. PROPERTY MARKET (NEW: process listings, match buyers/sellers from previous tick decisions)
 4. CREDIT MARKET (existing: service, maturity, defaults, cascade)
 5. BANKING (existing: adjust rate, check solvency)
 5b. BANKING CONCERN BROADCAST (NEW: if confidence < 0.5)
 6. RENT (existing: Ricardian)
 7. WAGES (existing: output share)
 8. TAXATION (existing: flat rate)
 9. ESSENTIAL CONSUMPTION (existing)
10. DEPOSIT RECALCULATION (NEW: total_deposits = sum of all agent cash)
11. MONETARY UPDATE + WEALTH/MOOD/STABILITY (existing)
```

Property market runs BEFORE credit market because a property sale generates
cash that may prevent a default, and a purchase may require prior borrowing.

**Note on pipeline order (I-5):** The spec 2 original design placed
expectations at step 2 (after production). The current implementation
and this spec place expectations at step 0 (before production). This is
intentional: expectations must reflect the previous tick's prices and
be available before market clearing decisions. The change was made during
Part 1 implementation and is documented here for traceability.

### Decision Sequencing

Agent decisions happen AFTER the economy pipeline in the simulation tick.
Property and hoard decisions take effect at tick N+1 (the next economy
pipeline run). Borrow executes immediately (cash is transferred when the
agent decides). This tick+1 settlement is consistent with real-world
settlement delays and avoids circular dependencies in the pipeline.

## Section 1: Extended Economic Context

`context.py:build_economic_context` is extended with three new blocks appended
to the existing output.

### Expectations block

```
Price expectations (your assessment):
- Subsistence: RISING (+12% expected), confidence: high
- Luxury: FALLING (-5% expected), confidence: low
```

Source: AgentExpectation records for the agent. Shows trend_direction,
percentage deviation from actual, and a confidence word (high > 0.7,
moderate 0.4-0.7, low < 0.4).

### Debt block

```
Your debt situation:
- Active loans: 2 (total balance: 120 LVR)
- Interest due this tick: 4.8 LVR
- Debt-to-wealth ratio: 35% (moderate)
- Financial position: speculative (can pay interest, will need to refinance)
- Credit available: up to 80 LVR at 6.2% interest (secured by your farmland)
```

Source: Loan records (active, for this borrower), Minsky classification
computed via `classify_minsky_stage`, credit availability computed via
`evaluate_credit_request` using the agent's highest-value **unpledged**
property as hypothetical collateral (see M-6 fix below).

Debt-to-wealth ratio words: safe (< 0.3), moderate (0.3-0.6), dangerous (> 0.6).
Minsky words: hedge ("fully covered, safe"), speculative ("can pay interest,
will need to refinance"), ponzi ("cannot cover interest, critical").

The "Credit available" line is omitted when the agent has no unpledged
property (no available collateral = no borrowing capacity).

### Banking block

```
Banking system: solvent, confidence high, base rate 5.0%
```

Or when critical:

```
Banking system: INSOLVENT, confidence LOW (0.3), base rate 12.0%
```

Source: BankingState for the simulation. Confidence words: high (> 0.7),
moderate (0.4-0.7), low (< 0.4).

### Queries required

- AgentExpectation: batch-fetched per agent (already indexed by agent + good_code)
- Loan: filtered by simulation + borrower + status="active"
- BankingState: one query per simulation (singleton)
- Property: already fetched in the base context

All queries are direct lookups on indexed fields. No N+1 risk.

## Section 2: New LLM-Driven Actions

Three new actions added to the decision vocabulary in `decision.py`:

### `borrow`

The agent requests a loan from the banking system.

- **Target**: amount as string (optional; parsed as float, if omitted or
     not a valid number, requests maximum available credit)
- **Handler in apply_agent_action**:
  1. Find the agent's highest-value **unpledged** property as collateral
     (exclude properties already used as collateral for active loans --
     fix for M-6 double-pledging)
  2. Call `evaluate_credit_request(borrower, amount, collateral, simulation)`
  3. If approved: call `issue_loan(simulation, lender=None, borrower, amount,
     interest_rate, collateral, tick, lender_type="banking")`
  4. If rejected: create memory "Loan request denied: {reason}"
- **Executes immediately**: cash is transferred in the same tick
- **Dashboard verb**: "takes out a loan"

### `sell_property`

The agent lists a property for sale.

- **Target**: property type (optional; if omitted, lists the first owned property)
- **Handler in apply_agent_action**:
  1. Find the agent's property matching the target (or first owned)
  2. If property already has an active listing (status="listed"), skip
  3. Delete any old listing for this property (status="sold" or "withdrawn")
     to avoid OneToOneField constraint violation (fix for I-2/A-4)
  4. Compute Gordon valuation via `compute_gordon_valuation`
  5. Asking price = fundamental_value * expectation_multiplier
     - If agent's trend for the zone is "rising": multiplier = 1.1
     - If "falling": multiplier = 0.9
     - If "stable": multiplier = 1.0
     - These multipliers are tunable design parameters representing
       the speculative premium/distressed discount. Not empirically
       calibrated; the direction (premium on rising, discount on falling)
       is standard in real estate economics.
  6. Create PropertyListing(property, asking_price, fundamental_value, tick)
  7. Create memory "Listed {property.name} for sale at {price}"
- **Settlement at tick+1**: the listing becomes available for buyers at the
  next tick's property market step
- **Dashboard verb**: "lists property for sale"

### `buy_property`

The agent attempts to buy a listed property.

- **Target**: zone name or property type (optional)
- **Handler in apply_agent_action**:
  1. The intent is captured in DecisionLog.output_decision (the JSON action
     dict already contains `{"action": "buy_property", "target": "...", ...}`)
  2. Actual matching and transfer happens in the property market step at tick+1
  3. No immediate side effects beyond memory creation
- **Settlement at tick+1**: processed by `process_property_listings` in the
  economy pipeline
- **Dashboard verb**: "wants to buy property"

**Note on buy_property intent parsing (M-2):** `process_property_listings`
reads the previous tick's DecisionLog entries, calls `json.loads()` on
`output_decision`, and filters for `action == "buy_property"`. Parse
failures (malformed JSON) are silently skipped -- the agent's intent is
lost, which is equivalent to the agent changing their mind.

### System prompt update

The action list in `_DECISION_SYSTEM_PROMPT` is extended:

```
"action": "work|rest|socialize|explore|trade|argue|help|avoid|form_group|join_group|crime|protest|campaign|move_to|hoard|borrow|sell_property|buy_property"
```

### Mood and emotional weight

| Action | Mood delta | Emotional weight | Rationale |
|--------|-----------|-----------------|-----------|
| borrow | -0.02 | 0.2 | Tunable design parameter. Comparable to "protest" (-0.02). |
| sell_property | -0.01 | 0.3 | Tunable design parameter. Comparable to "move_to" (0.2). |
| buy_property | +0.02 | 0.3 | Tunable design parameter. Comparable to "explore" (+0.02). |

All mood deltas and emotional weights are tunable design parameters.
They are calibrated relative to the existing action values in
`simulation/engine.py` but without empirical source.

## Section 3: Property Market Module

New module `economy/property_market.py` with three functions.

### compute_gordon_valuation

```python
def compute_gordon_valuation(prop: Property, simulation) -> float:
    """Compute fundamental value using the Gordon Growth Model (1959).

    V = R / max(r - g, 0.01)

    where:
    - R = rental income from this property's zone in the last tick
      (from EconomicLedger rent transactions, proportional to
      property.production_bonus)
    - r = current base interest rate (from BankingState)
    - g = trailing 5-tick average growth rate of total rent in the zone

    The 0.01 floor on (r - g) prevents division by zero when g >= r.
    When g approaches r, the valuation becomes very high, indicating
    the market is in speculative territory where prices detach from
    fundamentals (Shiller 2000, "Irrational Exuberance", ch. 1).

    Returns the fundamental value, floored at property.value * 0.1
    and capped at property.value * 10. These bounds are tunable
    design parameters. The cap at 10x prevents extreme valuations
    from very low interest rates but also limits bubble magnitude --
    a documented trade-off (see Known Limitations).
    """
```

### process_property_listings

```python
def process_property_listings(simulation, tick: int) -> dict:
    """Process property market: expire old listings, match buyers with sellers.

    Called in the economy tick pipeline BEFORE credit market.

    Steps:
    1. Withdraw listings older than 10 ticks (auto-expire).
       The 10-tick expiry is a tunable design parameter representing
       the patience threshold of a seller in an illiquid market.
    2. Collect buy_property intents from previous tick's DecisionLog
       via json.loads(output_decision) filtering action == "buy_property".
       Parse failures are silently skipped.
    3. For each buyer intent, find a matching active PropertyListing
       in the buyer's CURRENT zone (zone at matching time, not at
       decision time -- fix for M-4).
    4. Exclude self-purchases: buyer cannot buy their own listing
       (fix for M-5).
    5. If buyer has sufficient cash: execute transfer (cash from buyer
       to seller, property ownership change, listing status = "sold").
    6. If buyer has insufficient cash: match FAILS, listing stays active.
       The buyer must first borrow (via "borrow" action) and then
       retry buy_property in a subsequent tick. No auto-trigger of
       loans -- all borrowing decisions must be explicit LLM choices
       (fix for A-5, architectural consistency).
    7. Record all transfers in EconomicLedger.

    Matching priority: listings in buyer's zone, cheapest first.
    Cross-zone matching is not supported in this version.

    Property sale transactions are recorded in EconomicLedger with
    transaction_type="property_sale". This requires adding "property_sale"
    to TRANSACTION_TYPES in the EconomicLedger model.

    Returns dict with counts: {"matched": N, "expired": M, "failed": K}
    """
```

### New transaction types

The `EconomicLedger.TRANSACTION_TYPES` list is extended with:

- `("property_sale", "Property Sale")` -- property market transfers
- `("loan_issued", "Loan Issued")` -- loan disbursement (currently uses "trade")
- `("loan_interest", "Loan Interest")` -- interest payments (currently uses "trade")
- `("expropriation", "Expropriation")` -- government seizure of property

This allows analytics to distinguish financial transactions from goods
trading. Existing `credit.py` code that uses `transaction_type="trade"`
for loan operations is updated to use the specific types.

### process_expropriation

```python
def process_expropriation(
    simulation,
    old_type: str,
    new_type: str,
    tick: int,
) -> int:
    """Execute property redistribution on government transition.

    The expropriation policy is determined by the NEW government type
    (new_type), not the old one. The new regime imposes its property
    policy on the population (fix for C-1 ambiguity).

    Reads expropriation_policies from simulation.config (populated from
    template by initialize_economy). Policies per government type:

    - "none": no change (democracy, federation, monarchy, illiberal_democracy)
    - "elite_seizure": properties owned by elite/wealthy agents -> government
    - "nationalize_all": ALL agent-owned properties -> government
    - "redistribute": properties above median value -> distributed to
      working/poor agents proportionally

    Note: "redistribute" is defined but not currently assigned to any
    government type in the default templates. It exists as an extension
    point for future scenarios.

    Side effects:
    - Active PropertyListings on expropriated properties are withdrawn
    - Loans collateralized by expropriated properties default immediately
      (collateral is gone; lender absorbs the loss)
    - Affected agents receive strongly negative memories
      (emotional_weight=0.8, tunable design parameter)
    - Reputation damage for the government (via update_reputation on all
      affected agents observing the government/head_of_state)

    Source: Acemoglu & Robinson (2006) -- regime transitions driven by
    distributional conflict over property. Expropriation is historically
    the primary mechanism (French Revolution assignats, Russian 1917
    nationalization, Cuban 1959 land reform).

    Returns the number of properties transferred.
    """
```

## Section 4: Hoard-Expectations Link

The `is_hoarding` flag in the market pipeline is currently hardcoded to
`False`. The fix:

1. At the start of the economy tick (`process_economy_tick_new`), query
   `DecisionLog` for the previous tick to find agents who chose `hoard`:
   ```python
   hoarding_decisions = DecisionLog.objects.filter(
       simulation=simulation,
       tick=tick - 1,
       output_decision__contains='"hoard"',
   ).values_list("agent_id", flat=True)
   hoarding_ids = set(hoarding_decisions)
   ```

2. When building `agent_inventories` for `collect_supply_and_demand`,
   set `is_hoarding=True` for agents in `hoarding_ids`.

3. The market module already handles `is_hoarding`: agents who hoard
   do not offer goods to the market, reducing supply and pushing
   prices up.

This creates the self-fulfilling prophecy loop:
expectations rising -> agent hoards -> supply drops -> prices rise ->
expectations confirmed -> more hoarding

**Note on query mechanism (I-3):** `DecisionLog.output_decision` is a
`TextField`, not a `JSONField`. The `__contains` lookup performs a
PostgreSQL `LIKE '%"hoard"%'` substring match, which correctly identifies
JSON actions containing `"hoard"` as a value. This works because the
field always contains `json.dumps()` output with consistent quoting.

**Note (N-2):** `DecisionLog` currently has no composite index on
`(simulation, tick)`. The model only defines `ordering = ["tick"]`.
This plan adds `models.Index(fields=["simulation", "tick"])` to
`DecisionLog.Meta.indexes` to support efficient querying of previous
tick decisions for both hoard and buy_property intent lookups.

## Section 5: Banking Initialization, Deposits, and Confidence Broadcast

### Banking initialization

`initialize_economy()` is modified to:

1. Call `initialize_banking(simulation)` after creating all other
   economic objects (currencies, goods, factors, zones, inventories,
   properties, tax policy).
2. Save `banking_config`, `credit_config`, `expectations_config`, and
   `expropriation_policies` from the template into `simulation.config`,
   alongside the existing `production_config`. This resolves the
   prerequisite gap (C-6) where these configs were missing at runtime.

### Dynamic aggregate deposit tracking (M-1 fix)

`BankingState.total_deposits` is recalculated each tick as the sum of
all living agents' cash holdings:

```python
# AgentInventory.cash is a JSONField ({currency_code: amount}),
# so aggregation requires Python iteration, not SQL aggregate().
# This is consistent with the pattern in context.py:55.
inventories = AgentInventory.objects.filter(
    agent__simulation=simulation,
    agent__is_alive=True,
)
total_cash = sum(
    sum(inv.cash.values()) for inv in inventories
)
banking_state.total_deposits = total_cash
```

This runs as step 10 in the tick pipeline (after taxation, consumption,
and all cash movements). The recalculation means:

- When agents hoard (keep cash out of trade), deposits stay the same
  (cash is still held, just not traded)
- When agents spend cash buying property, deposits redistribute
  (buyer's cash drops, seller's rises, total unchanged)
- When loans default and collateral is seized, the borrower's cash
  may be depleted, reducing aggregate deposits
- Bank-created money (via loans) inflates deposits above the base
  money supply, as expected in fractional reserve banking

This is an approximation: in reality, not all cash is deposited in
banks. But without per-agent deposit accounts (Spec 3), treating
total cash as total deposits is the simplest defensible model that
allows the reserve ratio and solvency checks to have real meaning.

### Banking confidence broadcast

New function `broadcast_banking_concern` in `banking.py`:

```python
def broadcast_banking_concern(simulation, tick: int) -> None:
    """Create banking concern memories when confidence is low.

    Trigger condition: BankingState.confidence_index < 0.5
    (REGARDLESS of solvency status -- fix for C-3).

    The condition is confidence alone, not confidence AND insolvency.
    This is essential for Diamond & Dybvig (1983): the bank run is
    triggered by the FEAR of insolvency, not by actual insolvency.
    If we required insolvency before broadcasting concern, the
    self-fulfilling prophecy mechanism would be broken -- agents
    could never cause insolvency through withdrawal because they
    would never learn about the risk until it was too late.

    Generates "banking concern" memories for a random sample of 50%
    of living agents. The 50% sample is a tunable design parameter
    modeling information asymmetry: not everyone is immediately aware
    of banking stress. The information flow system handles further
    propagation with Big Five distortion.

    This is NOT a bank run trigger -- it is an information event.
    The bank run emerges from the coordination game: agents who
    receive and believe the concern may decide to hoard cash,
    reducing aggregate deposits (tracked via total_deposits
    recalculation), worsening solvency, confirming the concern.
    """
```

Memory content: "The banking system is under stress. Some depositors
are worried about the safety of their savings."

Emotional weight: 0.6 (tunable design parameter, comparable to
"protest" action at 0.4 and "crime" at 0.6 in the existing system).
Source type: "public" (institutional information, not hearsay).

The broadcast runs once per tick when conditions are met. A dedup
check prevents creating duplicate banking concern memories in
consecutive ticks (check if agent already has an active banking
concern memory from the last 3 ticks, consistent with the existing
`_MEMORY_DEDUP_TICKS = 3` constant in `simulation/engine.py`).

## Section 6: Expropriation Hook

`government.py:check_transitions` is modified to:

1. Capture the `previous_type` before updating `government.government_type`
2. After the transition completes, call:
   ```python
   from epocha.apps.economy.property_market import process_expropriation
   process_expropriation(simulation, previous_type, target_type, current_tick)
   ```

The same hook is added to `attempt_coup` for coup-driven transitions.

The expropriation policy lookup uses `simulation.config["expropriation_policies"]`
with the **new_type** as the lookup key. The config is populated during
`initialize_economy` from the template. For simulations without economy
initialization, the hook is a no-op (no expropriation_policies in config
= no action).

## Section 7: Dead Agent Loan Handling (M-3 fix)

When an agent dies (`is_alive=False`), their active loans should default.
The fix is applied in `service_loans`:

```python
# Before servicing, default all loans held by dead borrowers
dead_borrower_loans = Loan.objects.filter(
    simulation=simulation,
    status="active",
    borrower__is_alive=False,
)
dead_borrower_loans.update(status="defaulted")
```

This runs at the start of the credit market step, before normal loan
servicing. Dead agents cannot earn income or repay debt, so immediate
default is the only realistic outcome. Collateral seizure and cascade
propagation follow the existing default processing pipeline.

## Section 8: Error Handling

- **No collateral for borrow**: loan request denied, memory created
- **No unpledged property for borrow**: loan request denied (double-pledge
  protection, M-6 fix)
- **No property for sell_property**: action silently becomes rest, no error
- **No listings for buy_property**: intent recorded but no match at tick+1
- **Buyer insufficient cash**: match fails, listing stays active. Buyer
  must borrow first via explicit "borrow" action (no auto-loan, A-5 fix)
- **Gordon valuation with zero rent**: fundamental_value = property.value
  (book value fallback, documented as "no rental income observed")
- **Expropriation of property with active listing**: listing withdrawn
  before ownership transfer
- **Re-listing a previously sold property**: old listing (sold/withdrawn)
  deleted before creating new listing (I-2/A-4 fix)
- **Banking concern dedup**: skip if agent has banking concern memory
  from last 3 ticks (prevents context saturation, consistent with
  _MEMORY_DEDUP_TICKS)
- **Dead agent with loans**: auto-default at credit market step (M-3 fix)
- **Self-purchase prevention**: buyer cannot match their own listing (M-5 fix)
- **Zone mismatch on buy**: matching uses buyer's zone at tick+1, not at
  decision time (M-4 fix)
- **Import circularity (A-1)**: all cross-app imports use lazy imports
  inside functions, consistent with existing patterns in `decision.py`
  and `simulation/engine.py`

## Section 9: Testing Strategy

- Unit tests for `compute_gordon_valuation` with g < r, g ~ r, g > r
- Unit tests for `process_property_listings`: match, no match, failed (no cash)
- Unit tests for `process_property_listings`: self-purchase blocked, zone filter
- Unit tests for `process_expropriation`: each policy type, loan default
  on expropriated collateral, listing withdrawal
- Unit tests for extended `build_economic_context`: expectations block,
  debt block (with Minsky classification), banking block, no-data graceful
  fallback, unpledged property for credit availability
- Unit tests for `borrow` action handler: approved, rejected, no collateral,
  double-pledge blocked
- Unit tests for `sell_property`: normal listing, re-listing after sold,
  no property owned
- Unit tests for hoard flag propagation from DecisionLog (TextField __contains)
- Unit tests for `broadcast_banking_concern`: confidence threshold (< 0.5
  triggers regardless of solvency), dedup, memory content
- Unit tests for deposit recalculation: verify total_deposits reflects
  agent cash after trades, defaults, and loan issuance
- Unit tests for dead agent loan default (M-3)
- Integration test: create simulation, initialize economy + banking, run
  5 ticks, verify expectations update, property listing created and matched,
  loan issued and serviced, hoard reduces supply, deposits track correctly

All tests use PostgreSQL. No SQLite.

## Known Limitations

- **Take-it-or-leave-it pricing**: property transactions use the seller's
  asking price without negotiation. A richer model would have buyers
  counter-offer, but this requires multi-tick negotiation that is not
  justified at the current scale.
- **Single collateral per loan**: an agent can only pledge one property
  per loan. Multiple-collateral loans would increase complexity without
  proportional benefit at MVP scale.
- **Borrow only from banking system**: agents cannot lend to each other
  via LLM decisions. Agent-to-agent lending is available programmatically
  (`issue_loan` with `lender_type="agent"`) but is not exposed as an
  LLM action. This may be added when the agent count justifies a lending
  market.
- **50% broadcast sample**: the banking concern broadcast reaches 50%
  of agents randomly. Tunable design parameter, not empirically calibrated.
  Higher values produce faster bank runs; lower values produce more gradual
  crises.
- **Tick+1 settlement**: property transactions and hoard effects take
  one tick to settle. In a tick-based simulation this is the minimum
  delay. Faster settlement would require intra-tick sequencing.
- **No deposit tracking per agent**: the current BankingState tracks
  aggregate deposits (recalculated as sum of all agent cash each tick),
  not per-agent deposit balances. This means individual withdrawal
  decisions are modeled indirectly (agent spends or hoards cash, reducing
  their contribution to aggregate deposits). Per-agent deposits would be
  needed for a full bank run model (Spec 3).
- **Gordon valuation cap at 10x**: the cap on fundamental value at 10x
  book value limits the magnitude of property bubbles. In reality, bubbles
  can exceed 10x (e.g., Tokyo 1989, US housing 2006). The cap prevents
  numerical instability but constrains simulation fidelity for extreme
  bubble scenarios. Tunable design parameter.
- **No buyer-side credit in property matching**: buyers must have
  sufficient cash at matching time. They cannot auto-borrow; the LLM
  must choose "borrow" first, then "buy_property" in a later tick.
  This is a deliberate architectural choice (LLM-driven decisions) but
  means property purchases with leverage require a minimum 2-tick sequence.
- **Credit market timing within zones (A-3)**: the credit market step
  runs once per tick (not per zone), after the first zone's market
  clearing. This is a pre-existing design choice from Part 2 that could
  cause timing artifacts if loan creation depends on a specific zone's
  production. Documented as a known limitation, not addressed in this plan.
- **risk_premium discrepancy (I-1/C-2)**: the original spec 2 design
  specified risk_premium=1.0, but the implementation uses 0.5. The 0.5
  value is retained as it produces less aggressive rate increases and is
  closer to observed credit spreads in pre-industrial economies. The
  template should be updated to include risk_premium explicitly. Tunable
  design parameter.

## Out of Scope

- Full prospect theory utility function (Spec 2b or 3)
- Labor market matching / Mortensen-Pissarides (Spec 2b or 3)
- Multiple independent banks as agents (Spec 3)
- Financial instruments: stocks, bonds, derivatives (Spec 3)
- Stock exchanges and order books (Spec 3)
- Inter-agent lending as LLM action (future enhancement)
- Per-agent deposit accounts (Spec 3)
- Adaptive trend_threshold reconciliation (current implementation uses
  0.05 vs original spec's 0.02; the 0.05 value is retained as it
  produces fewer false-positive trend detections with small agent counts)

## File Changes Summary

| File | Operation | Responsibility |
|------|-----------|----------------|
| `economy/property_market.py` | New | Gordon valuation, listings, matching, expropriation |
| `economy/context.py` | Modify | Add expectations, debt, Minsky, banking blocks |
| `economy/engine.py` | Modify | Property market step, hoard flag, banking concern, deposit recalc |
| `economy/initialization.py` | Modify | Call initialize_banking, save ALL configs to simulation.config |
| `economy/banking.py` | Modify | Add broadcast_banking_concern, deposit recalculation |
| `economy/credit.py` | Modify | Double-pledge check, dead agent default, new transaction types |
| `economy/models.py` | Modify | Add transaction types to EconomicLedger, add index to DecisionLog |
| `agents/models.py` | Modify | Add composite index (simulation, tick) to DecisionLog |
| `agents/decision.py` | Modify | New actions in system prompt |
| `simulation/engine.py` | Modify | Handlers for borrow/sell_property/buy_property in apply_agent_action |
| `world/government.py` | Modify | Expropriation hook after transitions and coups |
| `dashboard/formatters.py` | Modify | New verb entries |
| `economy/tests/test_property_market.py` | New | Property market tests |
| `economy/tests/test_context_behavioral.py` | New | Extended context tests |
| `economy/tests/test_integration_behavioral.py` | New | End-to-end integration |

## FAQ

### Property market

**Q: Why LLM-driven buy/sell instead of automated matching?**
A: Architectural consistency. Epocha's philosophy is that strategic decisions
emerge from LLM-based agent reasoning, not automated mechanisms. Property
transactions are bilateral, rare, and context-dependent (debt stress,
expectations, personality) -- exactly the kind of decision the LLM handles
well. Automated goods trading (tatonnement) works for fungible commodities
but not for unique assets.

**Q: Why tick+1 settlement?**
A: The economy pipeline runs BEFORE agent decisions in the tick. An agent
decides to sell at tick N; the listing becomes available for buyers at tick
N+1. This is consistent with how hoard works and with real-world settlement
delays. Implementing intra-tick settlement would require reordering the
pipeline (economy after decisions), which conflicts with the principle that
agents decide based on current economic state.

**Q: Why take-it-or-leave-it pricing?**
A: With 15-20 agents and few properties, a negotiation mechanism would rarely
activate and would add complexity. The asking price is already informed by
Gordon valuation and expectations. A buyer who disagrees with the price simply
does not buy (the listing persists). Multi-round negotiation can be added
when agent count justifies it.

**Q: Why no auto-loan on buy_property?**
A: Architectural consistency. If the system auto-triggers a loan when a buyer
lacks cash, the borrowing decision is made by a mechanism, not by the agent.
This contradicts Epocha's principle that strategic decisions emerge from LLM
reasoning. The 2-tick sequence (borrow, then buy) is a minor overhead that
preserves the emergent nature of the Minsky cycle: the agent consciously
chooses to take on leverage, not the system.

**Q: What about the OneToOneField on PropertyListing?**
A: The PropertyListing.property field is a OneToOneField, which prevents
multiple listings per property. When re-listing a previously sold/withdrawn
property, old listing records (non-"listed" status) are deleted before
creating the new one. This preserves the constraint while allowing re-listing.
Listing history is not tracked in this version; if needed, a ForeignKey with
partial unique constraint would replace the OneToOneField in a future revision.

### Credit

**Q: Why only banking system loans via LLM, not agent-to-agent?**
A: Reducing the action space. With 18 possible actions, adding nuanced
lending decisions (who to lend to, at what rate, for how long) would
overwhelm the LLM's decision quality. Agent-to-agent lending exists
programmatically for future use. Banking system loans are simpler: the
agent decides to borrow, the system evaluates, approve or deny.

**Q: How does the Minsky cycle emerge?**
A: Through the interaction of four systems:
1. Context shows credit availability -> agent borrows (borrow action)
2. Debt service reduces cash -> expectations shift -> hoard/sell decisions
3. Defaults cascade through debt graph (automated, already implemented)
4. Banking confidence drops -> information flow -> more hoarding -> spiral

The cycle is not hardcoded; it emerges from the feedback loops between
these independently implemented systems.

**Q: What prevents double-pledging of collateral?**
A: The `borrow` handler and `evaluate_credit_request` exclude properties
that are already referenced as collateral by an active Loan. The query
filters `Property.objects.exclude(collateralized_loans__status="active")`
to find only unpledged properties. The related_name `collateralized_loans`
is defined on `Loan.collateral` in `economy/models.py`.

### Banking

**Q: Why broadcast to 50% of agents, not all?**
A: Modeling information asymmetry. Not everyone is immediately aware of
banking stress. The information flow system handles further propagation.
The 50% is a tunable design parameter. In a more advanced model (Spec 3
with per-agent deposits), the broadcast could target depositors specifically.

**Q: Can the banking system recover?**
A: Yes. `check_solvency` already restores confidence at +0.05/tick when
the bank returns to solvency. If agents stop withdrawing (because the
information flow carries reassuring news, or the government intervenes
via policy changes), confidence recovers and the bank stabilizes. This
is the "good equilibrium" in Diamond & Dybvig (1983).

**Q: Why is the banking concern triggered by confidence alone, not by
confidence AND insolvency?**
A: Diamond & Dybvig (1983) show that bank runs are a coordination game
with multiple equilibria. The run occurs when depositors FEAR insolvency,
not when insolvency has already happened. Requiring actual insolvency
before broadcasting concern would break the self-fulfilling prophecy:
agents could never cause insolvency through withdrawal because they
would not learn about the risk until too late. The concern must precede
the crisis, not follow it.

**Q: How do aggregate deposits change over time?**
A: `total_deposits` is recalculated each tick as the sum of all living
agents' cash holdings. This means deposits change naturally as agents
earn, spend, trade, and default. This is an approximation (not all cash
is deposited in banks), but it is the simplest model that gives the
reserve ratio and solvency checks real economic meaning without requiring
per-agent deposit tracking (deferred to Spec 3).

### Expropriation

**Q: What happens to loans secured by expropriated property?**
A: They default. The collateral is gone (seized by the new government),
so the lender bears the full loss. This is historically accurate:
revolutions destroy creditor wealth. The lender may cascade-default if
the loss exceeds the CASCADE_LOSS_THRESHOLD of their wealth.

**Q: Does expropriation trigger on coups too?**
A: Yes. Both `check_transitions` (indicator-based) and `attempt_coup`
call the expropriation hook. A military junta seizing power triggers
"elite_seizure" just as a popular revolution would.

**Q: Which government type determines the expropriation policy?**
A: The NEW government type (the regime taking power), not the old one.
The incoming regime imposes its property policy. A revolution that
establishes a communist government applies "nationalize_all", regardless
of whether the previous regime was a monarchy or democracy.

## Audit Resolution Log

Adversarial review conducted 2026-04-15. Findings and resolutions:

| ID | Category | Finding | Resolution |
|----|----------|---------|------------|
| C-3 | INCONSISTENT | Banking concern condition AND (confidence + insolvency) breaks Diamond & Dybvig | Fixed: condition is confidence < 0.5 alone |
| I-2/A-4 | INCORRECT/ARCH | OneToOneField prevents re-listing | Fixed: delete old listing before creating new one |
| C-6 | INCONSISTENT | initialize_economy doesn't save configs | Fixed: now saves all 4 config blocks |
| M-1 | MISSING | total_deposits never updated | Fixed: recalculated each tick as sum of agent cash |
| M-6 | MISSING | No double-pledging protection | Fixed: exclude pledged properties from collateral |
| A-5 | ARCHITECTURAL | Auto-loan on buy contradicts LLM-driven philosophy | Fixed: removed auto-loan, buyer must borrow explicitly |
| I-3 | INCORRECT | Wrong justification (JSONField vs TextField) | Fixed: corrected to TextField with LIKE explanation |
| I-4 | INCORRECT | Gordon "bubble territory" citation attributed to wrong source | Fixed: attributed to Shiller (2000) |
| I-5/C-4 | INCONSISTENT | Pipeline order change undocumented | Fixed: documented as intentional with rationale |
| C-5 | INCONSISTENT | trend_threshold 2% vs 5% | Documented: 5% retained, rationale in Out of Scope |
| I-1/C-2 | INCORRECT/INCONSIST | risk_premium 1.0 vs 0.5 | Documented: 0.5 retained, rationale in Known Limitations |
| M-2 | MISSING | buy_property intent parsing unspecified | Fixed: json.loads + filter, documented in Section 2 |
| M-3 | MISSING | Dead agents with active loans | Fixed: auto-default in credit market step (Section 7) |
| M-4 | MISSING | Zone mismatch on buy | Fixed: use current zone at matching time |
| M-5 | MISSING | Self-purchase possible | Fixed: exclude seller from buyer matching |
| M-8 | MISSING | "redistribute" policy never assigned | Documented as extension point in process_expropriation |
| U-1..U-7 | UNJUSTIFIED | Parameters without source | All marked as "tunable design parameter" |
| A-1 | ARCHITECTURAL | Import circularity | Documented: lazy imports, consistent with existing patterns |
| A-2 | ARCHITECTURAL | DecisionLog as inter-tick channel is fragile | Accepted: simpler than new model, failure = no match (graceful) |
| A-3 | ARCHITECTURAL | Credit timing within zones | Documented as known limitation, pre-existing |
| C-1 | INCONSISTENT | Expropriation lookup key ambiguous | Fixed: explicitly uses new_type |
| M-7 | MISSING | Performance impact | Acceptable at 20 agents; documented for future scaling |
| N-1 | INCORRECT | Related name `securing_loans` errato in FAQ | Fixed: corrected to `collateralized_loans` per models.py |
| N-2 | INCORRECT | Affermazione falsa su indice DecisionLog | Fixed: plan adds Index(simulation, tick) to DecisionLog |
| N-3 | MISSING | TRANSACTION_TYPES non include property_sale | Fixed: added property_sale, loan_issued, loan_interest, expropriation |
| N-4 | MISSING | Cash aggregation su JSONField non banale | Fixed: pseudocode uses Python iteration, not SQL aggregate |
| N-5 | MISSING | Movimenti finanziari indistinguibili sotto "trade" | Fixed by N-3: new transaction types distinguish operations |
| N-6 | INCONSISTENT | Step numbering pipeline cosmetica | Accepted: cosmetic, implementation follows code structure |

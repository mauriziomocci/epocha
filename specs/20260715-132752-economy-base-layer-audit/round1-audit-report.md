# Economy base layer — Round 1 adversarial audit report

**Date**: 2026-07-15  
**Method**: 5 hostile module auditors (Opus, high effort) → each finding verified by two independent adversarial skeptics (source-accuracy lens + materiality lens, conjunctive survival) → cross-module synthesis. 66 agents, 0 errors.

**Overall verdict**: **NOT CONVERGED**

**Survival stats**: 10 confirmed, 20 rejected by verification, 6 recorded VERIFIED.


## Confirmed findings (survived two-lens adversarial verification)

### production/PROD-1 — INCORRECT (high)

**Claim under review**: The Leontief limit (sigma->0) of the CES function is Q = A * min(alpha_i * X_i).

**Location**: `epocha/apps/economy/production.py:87-92`

**Evidence**: Line 91 computes `min_val = min(alpha * x if x > 0 else 0.0 for alpha, x in pairs)` and line 92 returns `scale * min_val`, i.e. Q = A * min(alpha_i * X_i). But the module's own general-CES branch (lines 104-122) uses the normalized weighted-power-mean form (sum alpha_i * X_i^rho)^(1/rho) with weights alpha_i summing to 1. The limit of a weighted power mean as rho -> -inf is min(X_i); the weights VANISH in the limit (they only need to be positive). Numerically verified: with alpha=[0.9,0.1], X=[1,1], the general CES converges to 1.0 as sigma->0, while the Leontief branch returns min(0.9,0.1)=0.1 - a 10x error and a discontinuity at sigma=0.05. The docstring at lines 87-89 claims convergence to 'a fixed-proportions technology where the bottleneck factor determines output', i.e. the true CES limit, which is min(X_i), not min(alpha_i*X_i).

**Source check**: Arrow, Chenery, Minhas & Solow (1961): as the elasticity of substitution sigma->0, CES converges to the Leontief fixed-proportions form. For the normalized aggregator (sum alpha_i X_i^rho)^(1/rho) the limiting form is A*min_i(X_i) (weighted power mean -> min; distribution weights drop out). The Leontief coefficients in the min would only appear under a different normalization Q=A*min(X_i/a_i), which is NOT the aggregator implemented in the general branch. The code's min(alpha_i*X_i) matches neither the ACMS limit of its own aggregator nor the standard fixed-proportions form, and is internally inconsistent with lines 104-122.

### production/PROD-4 — UNJUSTIFIED (low)

**Claim under review**: Absent zone data, capital, natural_resources and knowledge factor inputs each default to a baseline of 0.5.

**Location**: `epocha/apps/economy/production.py:190,199,201`

**Evidence**: Lines 190/199/201 fall back to 0.5 for capital_base, natural_resources and knowledge when neither zone_resources nor the zone_type template supplies a value. The inline comment calls it 'a baseline capital level' but gives no source and does not tag it tunable. 0.5 is a bare magic number that materially scales output (it feeds directly into the CES aggregator).

**Source check**: No cited source; this is a model calibration choice. Project rules require every constant to be named, documented and justified, or explicitly flagged as a tunable design heuristic. The labor default (skill_weight 0.8/1.0) and default_scale are correctly flagged tunable; these 0.5 baselines are not.

### monetary/PROD-3 — INCONSISTENT (medium)

**Claim under review**: Below the poverty threshold the mood penalty is linear in wealth.

**Location**: `monetary.py:136 (docstring) vs monetary.py:140-141 (code)`

**Evidence**: The docstring line 136 states 'Below poverty: linear mood penalty.' The implementation (lines 140-141) returns a FLAT CONSTANT -_MOOD_PENALTY_POOR = -0.05 for any 0 <= wealth < _POVERTY_THRESHOLD, independent of wealth. There is no linear term; the penalty does not scale with how far below the threshold the agent is. The docstring and code disagree.

**Source check**: No external source is claimed for the shape (constants are tagged tunable, lines 21-24). This is a pure internal docstring-vs-implementation contradiction: the documented model (linear penalty) is not the implemented model (step function). Per Code Comments rule, the stated behavior must match the code.

### monetary/PROD-4 — MISSING (medium)

**Claim under review**: Inflation is computed as the average percentage change in prices.

**Location**: `monetary.py:93-102`

**Evidence**: compute_inflation builds an unweighted list of price relatives (new-old)/old per good (line 97) and returns their arithmetic mean sum(changes)/len(changes) (line 102). No expenditure/quantity weighting is applied, and the arithmetic-mean-of-relatives form is used. There is no comment documenting that this is a simplification, what the full model would be, or what is lost.

**Source check**: A standard price index (Laspeyres/Paasche/Fisher-ideal, or the geometric Jevons index the BLS adopted) weights price relatives by expenditure shares. An unweighted arithmetic mean of price relatives is the Carli index, which has a well-documented UPWARD bias relative to the geometric mean (the 'formula/substitution bias' that led statistical agencies to abandon Carli-type aggregation). The code neither weights by quantity/expenditure nor documents the omission, so the simplification and its known bias are undocumented (violates the 'every simplification documented' rule).

### market/MKT-2 — INCORRECT (high)

**Claim under review**: execute_trades does not conserve traded quantity: the buyer/seller double loop can generate total trade volume far exceeding min(total_supply, total_demand).

**Location**: `epocha/apps/economy/market.py:262-302`

**Evidence**: traded = min(supply, demand) is computed (line 263) but never used to bound the sum of matched shares. For each buyer, actual_buy = want_qty*demand_ratio is fixed (line 283); the inner loop then matches that SAME actual_buy against every seller, appending share = min(actual_buy, actual_sell) for each seller without decrementing actual_buy or actual_sell. A buyer therefore 'buys' up to actual_buy from each of the N sellers, and each seller 'sells' actual_sell to each of the M buyers, so aggregate traded volume scales with N*M rather than being capped at min(supply,demand). Goods and money are not conserved. No test exercises this path (tests/test_market.py only tests tatonnement_prices).

**Source check**: In any market-clearing model (Walras 1874; Shoven & Whalley 1992), realized trade of a good equals min(aggregate supply, aggregate demand) and is rationed across the short side so that sum of buyer purchases = sum of seller sales = the cleared quantity. The docstring itself (lines 246-247) states buyers/sellers get a 'proportional share', which the running-total-free double loop violates.

### market/MKT-5 — UNJUSTIFIED (high)

**Claim under review**: The non-essential (discretionary) demand function is an ad hoc formula that misuses 'price_elasticity' and carries an unsourced spend fraction of 0.1, with no per-agent budget constraint across goods.

**Location**: `epocha/apps/economy/market.py:212-225`

**Evidence**: discretionary = min(_MAX_DISCRETIONARY_DEMAND, (cash * 0.1) / (price * elasticity)). Quantity is obtained by dividing by 'elasticity' as if it were a demand-dampening divisor. The 0.1 (spend 10% of cash) is a magic number with no source. Crucially, this is computed independently for EACH non-essential good (loop line 202) using the agent's FULL cash each time, so an agent with K non-essential goods demands ~0.1*cash worth of each, total 0.1*K*cash, which can exceed cash — there is no cross-good budget constraint.

**Source check**: Price elasticity of demand is the dimensionless response dQ/dP · P/Q (e.g. a constant-elasticity demand Q = A·P^(-e)); it is not a divisor on quantity. A principled discretionary-demand rule would allocate a bounded budget across goods subject to sum(p_i·q_i) <= cash (Walras/consumer theory). The implemented form matches no cited demand system and is not documented as a heuristic with the full model it approximates and what is lost, as CLAUDE.md requires for every simplification.

### market/MKT-6 — INCONSISTENT (low)

**Claim under review**: The price-ceiling reference differs between the two price-update branches: the zero-supply branch always uses initial_prices while the main branch prefers base_prices.

**Location**: `epocha/apps/economy/market.py:111, 141-142`

**Evidence**: Zero-supply branch: max_allowed = initial_prices.get(good, 1.0) * MAX_PRICE_RATIO (line 111), ignoring the base_prices argument. Main branch: reference = (base_prices or initial_prices).get(good, 1.0) then max_price = reference * MAX_PRICE_RATIO (lines 141-142). The stated purpose of using base_prices (lines 137-140) — prevent cross-tick drift because this tick's initial price is already inflated — is defeated in the zero-supply branch, which re-anchors the cap to the inflated current-tick starting price.

**Source check**: Internal consistency: a single ceiling policy should apply to a good regardless of which code path updates it. Using two different reference anchors for the same MAX_PRICE_RATIO ceiling is an internal inconsistency, not attributable to any external source.

### distribution/PROD-2 — INCONSISTENT (high)

**Claim under review**: Output distributes to factors without leakage or double counting; a conservation-of-value property holds.

**Location**: `epocha/apps/economy/distribution.py:69 and 104-111; confirmed in engine.py:354-402`

**Evidence**: compute_rent distributes the full zone output value (PROD-1) as rent, while compute_wages independently distributes output value again from agent_outputs (value = qty*price, line 104; full value to owners line 108, wage_share*value to workers line 111). In the tick engine both are credited as brand-new cash with from_agent=None and no offsetting debit from any producer/firm (engine.py:357-371 rent, 387-402 wages). Per tick the money injected therefore equals (full output value as rent) + (owner full value + worker wage_share value as wages), i.e. strictly MORE than the output actually produced. Value is created from nothing every tick.

**Source check**: Classical/national-accounting identity: the value of output is split among factor incomes (rent + wages + profit) that SUM to output value, not each separately equal to it. Ricardo's own tripartite division (rent to landlords, wages to labour, profit to capital) is a partition of a single output. The module contract (compute_taxes docstring line 123: taxable_income = wages + rent) plus the engine confirm the same production is counted at least twice, breaking value conservation.

### initialization/PROD-1 — INCONSISTENT (high)

**Claim under review**: Per-good CES scale (output multiplier A) is seeded correctly from the era template's calibrated default_scale.

**Location**: `epocha/apps/economy/initialization.py:133 vs epocha/apps/economy/template_loader.py:239`

**Evidence**: Line 133 hardcodes "scale": 5.0 for every good in default_good_production, with the comment "tunable design parameter: base output multiplier". The pre_industrial template (template_loader.py:239) explicitly sets default_scale=2.0 with a multi-line comment: 'With scale=5.0 and typical factor inputs, a single farmer produces ~5 units/tick -- enough to flood a 4-agent market. Scale=2.0 yields ~2 units/tick, keeping supply/demand ratios reasonable.' Because production.py:173 does scale = good_prod.get("scale", default_scale) and good_prod always carries "scale":5.0, the fallback to default_scale is never reached. The effective scale is 5.0 everywhere -- exactly the value the template author documented as producing an UNPHYSICAL flooded-market seed. The template's calibration effort is silently discarded.

**Source check**: The project's own template comment (the authoritative calibration note) states scale must be 2.0 for pre_industrial to avoid an unphysical supply/demand ratio in small simulations; the code seeds 5.0. Direct contradiction between the seeded state and the documented calibration.

### initialization/PROD-2 — INCONSISTENT (medium)

**Claim under review**: default_scale from the template is made available to the production engine at runtime.

**Location**: `epocha/apps/economy/initialization.py:166-170; engine.py:138; template_loader.py:239`

**Evidence**: initialize_economy writes sim_config["production_config"] with only default_sigma, role_production, and zone_type_resources (lines 166-170). It omits default_scale. engine.py:138 then reads default_scale = prod_template.get("default_scale", 1.0), so the engine's fallback resolves to 1.0, not the template's 2.0. Combined with PROD-1 (per-good scale hardcoded to 5.0), BOTH paths that could carry the template's calibrated 2.0 are dead: the per-good path uses 5.0, and the engine fallback path uses 1.0. The template value 2.0 is never used anywhere.

**Source check**: engine/production docstrings claim default_scale comes from template's production_config["default_scale"]; initialization never propagates that key, so the documented data flow is broken.


## Cross-module findings

### [INCORRECT] distribution + engine + monetary

**Issue**: End-to-end money and value conservation is broken: rent and wages both distribute the full output value (double counting) and the engine credits both as brand-new cash (from_agent=None) with no offsetting producer/firm debit, so each tick injects strictly more money than output produced. Trades and taxes are conserved, but rent (engine 357-371) and wages (engine 387-402) are pure creation.

**Evidence**: distribution.compute_rent distributes production*share*price over full zone_production; distribution.compute_wages distributes qty*price (owners) + wage_share*qty*price (workers) over the SAME agent_outputs whose quantities sum to zone_production. engine.py credits rents to owner cash and wages to agent cash with from_agent=None and no debit. Confirms and elevates distribution PROD-2 to a layer-wide stock-flow defect.

### [INCONSISTENT] initialization + monetary + engine + models

**Issue**: The money-supply aggregate M is disconnected from circulating cash. Currency.total_supply is set once at init from the template's initial_supply (e.g. 50000 for pre_industrial) and never updated, while agent cash is independent random.uniform draws and rent/wages inject unbounded new cash. compute_velocity divides transaction_volume by this stale, unrelated M, and check_fisher_consistency (the MV=PQ diagnostic that would catch the money creation in CM-1) is defined in monetary.py but never called anywhere.

**Evidence**: initialization.py:76 sets total_supply=cur_cfg['initial_supply']; grep shows no other write to total_supply. engine.py:469 reads primary_currency.total_supply for velocity. models.py:22 docstrings total_supply as 'M in Fisher's equation MV=PQ'. Meanwhile banking.recalculate_deposits (engine:520) independently sums all agent cash into a separate total_deposits every tick, so two money aggregates coexist and diverge by construction. check_fisher_consistency appears only at its def (monetary.py:50), never invoked.

### [INCORRECT] market + engine

**Issue**: Goods are created from nothing at trade settlement. The execute_trades N*M double loop (MKT-2) emits aggregate traded quantity exceeding min(supply,demand); the engine floors seller holdings at max(0.0, hold-qty) but credits each buyer the full qty, so buyers receive more goods in aggregate than sellers relinquish, and sellers are paid cash for units they never held.

**Evidence**: market.execute_trades lines 282-302 append share=min(actual_buy, actual_sell) per (buyer,seller) pair without decrementing running totals. engine.py:298-304 applies buyer_inv.holdings += qty unconditionally and seller_inv.holdings = max(0.0, hold-qty), while cash moves buyer->seller for the full cost. Net effect: goods conservation violated whenever a zone has multiple buyers and multiple sellers of the same good.

### [INCONSISTENT] initialization + engine + template_loader

**Issue**: The production scale actually used is 5.0 everywhere, which the template author explicitly documented as producing an unphysical flooded market; the calibrated 2.0 is dead on every path. This directly feeds the market non-clearing / price-cap behavior and the excess supply that the discretionary-demand and price-ceiling code then paper over.

**Evidence**: initialization.py:133 hardcodes scale=5.0 per good; engine.py:138 fallback is 1.0 because default_scale is never propagated into sim_config['production_config']. template_loader.py:239 sets default_scale=2.0 with the note that 5.0 'floods a 4-agent market'. Both live paths bypass 2.0.

### [INCONSISTENT] engine + monetary

**Issue**: Inflation and the price-level used for stability feedback are computed on last-zone-wins dictionaries, not system aggregates. Despite the _all naming, for any good present in multiple zones only the final zone's prices survive the dict.update() merge.

**Evidence**: engine.py:174 old_prices_all.update(old_prices) and engine.py:444 new_prices_all.update(equilibrium_prices) run once per zone; compute_inflation(old_prices_all, new_prices_all) (engine:506) and the stability_index adjustment therefore reflect a single zone. Low severity in single-zone runs but wrong labeling and wrong aggregate in multi-zone worlds.

### [INCONSISTENT] monetary + initialization

**Issue**: Mood thresholds are not reconciled with the initialized wealth scale. Poverty threshold 10.0 and satiation 100.0 are applied to wealth = cash + inventory value + property value, but initialization seeds property base_value 100 and elite cash 300-500, so every property owner starts permanently past satiation and the poverty band is unreachable for most agents from tick 0.

**Evidence**: monetary.py:29 _POVERTY_THRESHOLD=10.0, compute_mood_delta satiation default 100.0. initialization.py:224 wealth = initial_cash + holdings_value with cash from wealth_range (template_loader.py: elite 300-500, poor 5-30) and Property base_value 100 (line 252). Thresholds are tagged tunable but never calibrated against this distribution.


## Per-module verdicts

- **production**: **NOT CONVERGED** (INCORRECT=1, UNJUSTIFIED=1, INCONSISTENT=0, MISSING=0)
  - PROD-1 (INCORRECT, high): the sigma->0 branch returns A*min(alpha_i*X_i), but the module's own general CES aggregator (sum alpha_i X_i^rho)^(1/rho) tends to A*min(X_i) as rho->-inf, with the weights vanishing. The Leontief branch is inconsistent with the branch it is supposed to approximate and with its own docstring; it introduces a discontinuity at sigma=0.05. Must implement A*min(X_i) (or A*min(X_i/a_i) under an explicit Leontief-coefficient normalization documented as such). PROD-4 (UNJUSTIFIED, low): the 0.5 baselines for capital/natural_resources/knowledge (lines 190/199/201) feed the CES aggregator directly yet carry no source and no tunable tag, unlike the correctly-tagged labor and scale defaults. Cite or tag tunable. Verdict open on Round 1: both findings unresolved.

- **monetary**: **NOT CONVERGED** (INCORRECT=0, UNJUSTIFIED=0, INCONSISTENT=1, MISSING=1)
  - Cheapest module to close: no algorithmic change needed. PROD-3 (INCONSISTENT, medium): compute_mood_delta docstring says 'Below poverty: linear mood penalty' but lines 140-141 return a flat -0.05 step, independent of wealth. Fix the docstring (or make it genuinely linear). PROD-4 (MISSING, medium): compute_inflation is an unweighted arithmetic mean of price relatives, i.e. a Carli index, which has a documented upward bias versus the geometric (Jevons) form statistical agencies adopted; no comment records the simplification or its bias. Add the simplification note per the Code Comments rule. By the letter of the convergence rule these are documentable, but both are currently unresolved contradictions, so the module is not yet converged. Note also the cross-module money-supply defect (CM-1) that surfaces through this module.

- **market**: **NOT CONVERGED** (INCORRECT=1, UNJUSTIFIED=1, INCONSISTENT=1, MISSING=0)
  - MKT-2 (INCORRECT, high): execute_trades computes traded=min(supply,demand) but never uses it to bound the buyer/seller double loop; neither actual_buy nor actual_sell is decremented as matches accrue, so aggregate matched volume scales with N*M. Confirmed materially harmful end-to-end (see CM-3): the engine floors seller holdings at 0 while crediting each buyer the full quantity, fabricating goods and paying sellers for phantom units. Rewrite as short-side rationing with running totals so sum(buys)=sum(sells)=min(supply,demand). MKT-5 (UNJUSTIFIED, high): discretionary demand min(5.0, cash*0.1/(price*elasticity)) misuses price_elasticity as a quantity divisor (elasticity is dimensionless dQ/dP*P/Q, not a divisor), carries an unsourced 0.1 spend fraction, and is computed on full cash per good with no cross-good budget constraint (total demand can reach 0.1*K*cash > cash). Replace with a budget-constrained rule sum(p_i*q_i)<=cash or document as a heuristic with the model it approximates. MKT-6 (INCONSISTENT, low): the zero-supply branch anchors the MAX_PRICE_RATIO ceiling to initial_prices while the main branch prefers base_prices, defeating the stated cross-tick-drift protection. Use one anchor.

- **distribution**: **NOT CONVERGED** (INCORRECT=0, UNJUSTIFIED=0, INCONSISTENT=1, MISSING=0)
  - PROD-2 is filed INCONSISTENT but I reclassify it as a correctness/conservation defect that must be fixed, not documented, so the module is NOT CONVERGED despite the letter of the rule. compute_rent distributes the full zone output value as rent while compute_wages independently distributes the same output value again (owners full value, workers wage_share*value); the classical identity is that rent+wages+profit PARTITION one output value, not each equal it. engine.py confirms both are credited as brand-new cash with from_agent=None and no offsetting producer/firm debit (rent 357-371, wages 387-402), so every tick injects strictly more money than output produced. Documenting 'we create money each tick' is not an acceptable resolution for a scientific simulation; the fix is to split a single output value into factor shares summing to 1 and settle them as transfers from a producing entity, not as net new cash.

- **initialization**: **NOT CONVERGED** (INCORRECT=0, UNJUSTIFIED=0, INCONSISTENT=2, MISSING=0)
  - PROD-1 and PROD-2 are both INCONSISTENT but compound into a de-facto wrong initial state, so NOT CONVERGED until reconciled (one-line fix). PROD-1: default_good_production hardcodes scale=5.0 for every good; because production.py reads good_prod.get('scale', default_scale) and 'scale' is always present, the default_scale fallback is dead, so the effective scale is 5.0 everywhere. PROD-2: initialize_economy writes production_config without default_scale, so engine.py:138 falls back to 1.0. I verified in template_loader.py that pre_industrial sets default_scale=2.0 with an explicit calibration note that scale=5.0 floods a 4-agent market and is unphysical. Both paths that could carry the calibrated 2.0 are dead (per-good=5.0, engine fallback=1.0), so the seed ships exactly the value the author documented as unphysical. Reconcile by seeding 2.0 (drop the hardcoded per-good scale or propagate default_scale into sim_config).


## Synthesis summary

The economy base layer is NOT CONVERGED and cannot be promoted from whitepaper section 8.2 to section 4 Methods in its current state. What is sound: the tatonnement price loop with its stability caps (ADJUSTMENT_RATE, MAX_CHANGE_RATIO, MAX_PRICE_RATIO, MIN_PRICE) is well documented and tagged tunable; the CES general and Cobb-Douglas branches are correct and sourced; the subsistence-need constant (1.0) is shared consistently between market.py and the engine's consumption step; trades and taxes move money conservatively; velocity is honestly framed as a measured, not asserted, quantity. What must be fixed before promotion, in priority order. First, the layer violates conservation of money and value end to end: distribution counts the same output value as both full rent and full wages, and the engine injects both as brand-new cash with no producing entity debited, so every tick creates money out of nothing (cross-module CM-1). This is the single most serious defect and it is not documentable away, it must be rewritten so one output value is partitioned into factor shares summing to one and settled as transfers. Second, execute_trades does not conserve traded quantity, and at engine settlement this fabricates goods and pays sellers for phantom units (MKT-2 confirmed by CM-3); it needs short-side rationing with running totals. Third, the money-supply aggregate M is a static template constant disconnected from circulating cash, the MV=PQ diagnostic that would have caught the money creation is defined but never called, and a second cash aggregate (banking total_deposits) is recomputed in parallel every tick, so the two diverge by construction. Fourth, the CES Leontief limit returns min(alpha_i*X_i) instead of the min(X_i) its own aggregator converges to, a 10x error with a discontinuity at sigma=0.05 (PROD-1). Fifth, the initialized production scale is 5.0 everywhere, exactly the value template_loader documents as producing an unphysical flooded market, while the calibrated 2.0 is dead on every path (init PROD-1, PROD-2, CM-4); this excess supply is what the discretionary-demand and price-ceiling heuristics are quietly compensating for. Beyond these, the discretionary demand formula misuses price_elasticity as a divisor and lacks a budget constraint (MKT-5), several magic constants need sourcing or tunable tags (production 0.5 baselines, market 0.1 spend fraction), and a set of low-severity docstring-versus-code and last-zone-wins inconsistencies remain (monetary linear-vs-step, Carli index bias, price-ceiling anchor, inflation aggregation, mood thresholds versus wealth scale). Monetary is the closest to closing since it needs only a docstring correction and a simplification note; the other four modules require real algorithmic changes. Recommend a full re-audit after the conservation rewrite, since fixing distribution and execute_trades will change the money and goods flows that several other findings depend on.


## Rejected findings (did not survive adversarial verification)

These were flagged by a module auditor but refuted on source-accuracy or materiality grounds:

- **production/PROD-2**: The three branch-switch thresholds produce a continuous production surface across sigma.
  - _Rejected because_: Verified against the code. The implemented CES (Q=A·[Σαᵢ·Xᵢ^ρ]^(1/ρ) with αᵢ normalized to sum 1) is a weighted power mean whose σ→0 (ρ→-∞) limit is provably min(Xᵢ), weights dropping out. The Leontief branch at line 91 computes A·min(αᵢ·Xᵢ), which is neither this limit nor the standard fixed-coefficients Leontief form (min(Xᵢ/aᵢ)). At σ=0.05 the general branch (ρ=-19) yields ~min(Xᵢ) while just b

- **production/PROD-3**: Branch thresholds 0.05, 0.95, 1.05 are the correct boundaries for switching to the Leontief and Cobb-Douglas approximations.
  - _Rejected because_: The finding is factually accurate about the code: the three thresholds at lines 30-35 are named and carry a rationale comment ("avoid numerical instability" as rho->0 or rho->-inf) but are NOT tagged as tunable, unlike comparable parameters at lines 149 and 167-168 which explicitly say "tunable design parameter". The source-accuracy lens gives no refutation: the finding misreads no cited source; i

- **monetary/PROD-1**: The module implements a single Fisher identity MV=PQ, but velocity is measured from transaction volume while the consistency check uses real output.
  - _Rejected because_: Source-accuracy: the auditor is historically correct that Fisher (1911) states MV=PT with T=transactions, but the output form MV=PY / MV=PQ (Q=real output) is the standard textbook statement of the equation of exchange, universally attributed to Fisher. Using the output form and labeling it "Fisher's MV=PQ" is conventional, not a category error; the module explicitly documents it as an approximati

- **monetary/PROD-2**: check_fisher_consistency is a meaningful diagnostic of whether the money supply is consistent with the price level.
  - _Rejected because_: The finding is algebraically airtight and corroborated by the codebase's own definitions. compute_velocity (monetary.py:47) defines V = transaction_volume/money_supply, and models.py:24-25 plus engine.py:467-470 confirm cached_velocity is recomputed every tick as exactly transaction_volume/total_supply — there is no lagged or exogenous velocity anywhere in the system. Therefore, when check_fisher_

- **monetary/PROD-5**: Mood delta is a smooth diminishing-returns curve implementing the Kahneman-Deaton plateau.
  - _Rejected because_: Verified in source: constants _MOOD_BOOST_BASE=0.02, _MOOD_SATIATION_DECAY=0.005, satiation_threshold default 100.0. At the boundary the else branch (moderate wealth) returns 0.02*0.5=0.01 (line 148); immediately above, the satiation branch returns 0.02*exp(0)=0.02 (line 145). The upward jump from 0.01 to 0.02 is mathematically real, and the decay only returns the boost to 0.01 at excess≈138.6, so

- **monetary/PROD-6**: The module attributes the form 'MV=PQ' / 'V = PQ/M' to Fisher (1911).
  - _Rejected because_: The auditor is literally correct that Fisher (1911) states the equation of exchange as MV=PT (transactions form), not MV=PQ. However, MV=PQ / MV=PY is the standard income/output restatement of Fisher's equation of exchange, universally attributed to Fisher in macroeconomics textbooks and dominant in modern usage. Writing "Fisher's equation MV=PQ" is therefore a defensible standard variant of the c

- **market/MKT-1**: The module claims to implement 'Walrasian tâtonnement (Walras 1874)' but omits the numéraire / Walras' law structure that defines the actual Walrasian model, and never documents this as a simplification.
  - _Rejected because_: The finding holds market.py to the standard of a full Walrasian general-equilibrium closure (numéraire + Walras' law), but the docstring only claims "Walrasian tatonnement market clearing" — the price-groping mechanism, which is correctly implemented (line 71/121-122: P_new = P_old*(1+rate*excess/supply), textbook Samuelson-style discrete tâtonnement). Three source-accuracy refutations: (1) The nu

- **market/MKT-3**: The convergence flag can be returned True while a good is in persistent excess demand (demand>0, zero supply), so the stopping criterion does not correspond to market equilibrium.
  - _Rejected because_: Verified in code (market.py:110-113): the zero-supply/positive-demand branch bumps the price and `continue`s without setting converged=False, unlike the normal branch (117-119). When all goods fall into this branch or the zero-zero skip (103-104), the loop returns (prices, True) on iteration 1. This contradicts the function's OWN documented stopping criterion at line 72 ("until |excess/supply| < t

- **market/MKT-4**: The zero-supply price bump uses a hardcoded 1.1 (10% per iteration) that is inconsistent with, and independent of, the tâtonnement adjustment_rate.
  - _Rejected because_: Verified line 112 = min(prices[good] * 1.1, max_allowed). The 1.1 is an inline literal with no name, no value-level justification, and no "tunable design parameter" tag, unlike every other tuning constant in the module (ADJUSTMENT_RATE, MAX_ITERATIONS, MAX_PRICE_RATIO, MIN_PRICE, MAX_CHANGE_RATIO at lines 18-45). Source-accuracy refutation fails: the finding is UNJUSTIFIED, not a source-mismatch. 

- **distribution/PROD-1**: compute_rent implements a simplified Ricardian differential rent (Ricardo 1817).
  - _Rejected because_: Verified against the actual code. In compute_rent, total_bonus[good] sums bonus over all properties producing that good (lines 52-56); each property's share = bonus/total_bonus (line 68) and prop_rent += production*share*price (line 69). For every good with total_bonus>0 and production>0, shares sum to exactly 1, so the full production*price is distributed and total rent equals the entire market v

- **distribution/PROD-3**: Wage flow correctly compensates producers without overpaying property owners.
  - _Rejected because_: The finding rests on a misreading of its cited source. Ricardo's partition divides output among three FUNCTIONAL classes (laborers→wages, capitalists→profits, landlords→rent), not among mutually exclusive persons. A person who both owns and works property occupies two roles and legitimately earns two distinct factor incomes — a labor income and a land income — which is standard factor-income accou

- **distribution/PROD-4**: wage_share default 0.6 is appropriate 'for pre-industrial' economies.
  - _Rejected because_: The code at distribution.py:93 explicitly documents wage_share as "Tunable design parameter, default 0.6", which the finding itself admits satisfies the project's tunable-heuristic exemption to the GOLDEN RULE ("all UNJUSTIFIED parameters cited or documented as tunable heuristics"). The only residual claim is that the parenthetical "for pre-industrial" (line 85) is an unsourced quantitative assert

- **distribution/PROD-5**: The flat income-tax model documents its simplification vs the full model.
  - _Rejected because_: Verified directly in distribution.py. compute_taxes (lines 116-137) implements a correct flat tax (income * rate) but documents neither the fuller model nor what the flat simplification loses. The only citation in the module docstring, Doyle (1989), is explicitly attributed to "bankruptcy-as-crisis," a concept with zero corresponding code in this module (which handles only rent/wages/taxes) — so t

- **distribution/PROD-6**: compute_rent guards handle degenerate inputs (negative/zero bonus, negative production or price).
  - _Rejected because_: The finding self-concedes it is "not a source-fidelity issue." Under the source-accuracy lens there is nothing to refute on source grounds because the code matches its cited source: the docstring cites Ricardo (1817), openly labels the proportional-to-bonus formula as a documented simplification of differential rent, and implements exactly that. The three degenerate inputs (negative production_bon

- **initialization/PROD-3**: The seeded balance sheet is stock-flow consistent: currency total_supply (M in Fisher MV=PQ) equals the money actually placed in circulation.
  - _Rejected because_: The finding's central consequence is false: check_fisher_consistency (monetary.py:50-79), which performs the MV=PQ divergence check, is never called anywhere in epocha/ (verified by grep) — it is dead code, so there is no divergence check to be rendered "meaningless at seed." The only live use of total_supply is compute_velocity (engine.py:467-469), whose output cached_velocity is written but neve

- **initialization/PROD-4**: Bank deposits at initialization are backed by money withdrawn from agents (conserved).
  - _Rejected because_: The finding's central premise is factually false. total_deposits is not a separate minted money pool additive to agent cash; it is a shadow-accounting quantity set equal to the sum of all living agents' cash by recalculate_deposits (banking.py:281-305), which runs every tick as STEP 10 (engine.py:517-520). The 5000 seed at banking.py:93 is a transient placeholder overwritten on the first tick. tot

- **initialization/PROD-5**: Initial wealth distribution is reproducible given the simulation seed.
  - _Rejected because_: Verified in code: initialization.py:210 uses the process-global random.uniform (imported line 14); a repo-wide grep found no random.seed / seeding of simulation.seed anywhere on the world-gen or economy-init path (the only Random(...) construction is demography/rng.py's get_seeded_rng, which has zero production callers). Simulation.seed is documented 'Seed for reproducibility (non-LLM part)' and t

- **initialization/PROD-6**: Each agent's starting endowment of 2.0 units per essential good is a justified/tunable value.
  - _Rejected because_: Verified line 213: holdings = {code: 2.0 for code in essential_codes}, commented only "Start with 2 units of each essential good". Line 133 sets scale: 5.0 with an explicit "tunable design parameter" tag. The finding's facts are accurate: 2.0 is an inline literal, uncited, not in the template's initial_distribution config, and not tagged tunable. No primary source is invoked, so the source-accurac

- **initialization/PROD-7**: Currency primary-flag assignment is consistent with a possibly multi-currency template.
  - _Rejected because_: Verified in source: initialization.py:75 sets is_primary=True unconditionally inside the currencies loop, while line 79 treats currencies[0] as the single primary. Confirmed all four templates (LVR/GBP/USD/CRD) declare exactly one currency, so the issue is latent, as the finding honestly states. The internal inconsistency is corroborated by real downstream code that assumes a single primary: prope

- **initialization/PROD-8**: Hardcoded wealth-range fallbacks are consistent with template calibration.
  - _Rejected because_: Verified initialization.py:200-210 and all four templates in template_loader.py. Each literal fallback is the second arg to an inner .get("elite"/"middle"/"poor", ...); every shipped template (pre_industrial, industrial, and two later eras) defines all three keys, so the inner .get always returns the template's own calibrated value and the literals never execute. The finding's core failure scenari

# Tasks: Economy base layer remediation (Round 1 audit fixes)

**Input**: [spec.md](./spec.md), [plan.md](./plan.md), [round1-audit-report.md](./round1-audit-report.md)

**Ratified**: full remediation now; conservation approach **A** (producing entity debited, output value partitioned into factor shares summing to 1).

**Tests**: test-first mandatory where the fix is behavioral (RED before implementation). Container is the pytest/ruff authority. Baseline suite must stay green + new tests.

**Ordering**: engine.py-coupled groups (C, D, E, F) run sequentially to avoid conflicts; A and B touch isolated files. One commit per group via git-commit-assistant.

## Group A — Production CES fixes (production.py, isolated)

- [ ] T001 [A] RED test in `epocha/apps/economy/tests/test_production.py` (create if absent): `test_ces_leontief_limit_continuity` — for alpha=[0.9,0.1], X=[1.0,1.0], assert the general CES value at sigma just above the Leontief threshold (e.g. 0.06) and the Leontief-branch value at sigma below it (e.g. 0.04) agree to within a small epsilon (continuity across sigma=0.05), and that both equal min(X)=1.0 (NOT min(alpha*X)=0.1). Fails today (returns 0.1). Also `test_ces_leontief_equals_min_inputs` — Leontief branch returns A*min(X_i).
- [ ] T002 [A] Fix `production.py:87-92`: Leontief limit returns `scale * min(x for _, x in pairs)` (i.e. A*min(X_i)), matching the ACMS limit of the normalized aggregator; update the docstring comment to state the true limit min(X_i) and that distribution weights vanish in the limit. GREEN T001.
- [ ] T003 [A] Fix `production.py:190,199,201`: tag the 0.5 capital/natural_resources/knowledge baselines as tunable design parameters in the inline comments (matching the labor/scale tagging style), or cite a source. No behavior change; existing tests stay green.
- [ ] T004 [A] Gates + commit `fix(economy): correct CES Leontief limit and tag production baselines`.

## Group B — Monetary documentation fixes (monetary.py, isolated)

- [ ] T005 [B] Fix `monetary.py:136`: docstring "Below poverty: linear mood penalty" → "Below poverty: flat penalty (step function, not scaled by wealth)"; the code is a deliberate step and the docstring must match (Code Comments rule). No behavior change.
- [ ] T006 [B] Fix `monetary.py:86-102`: add a simplification note to `compute_inflation` docstring — the unweighted arithmetic mean of price relatives is a Carli index, which carries a documented upward bias versus the expenditure-weighted or geometric (Jevons) forms used by statistical agencies; state what the full model would be and what is lost. No behavior change (the aggregation form is the documented simplification).
- [ ] T007 [B] Gates + commit `docs(economy): align monetary docstrings with implementation and disclose inflation-index simplification`.

## Group C — Production scale calibration (initialization.py + engine.py, engine-coupled)

- [ ] T008 [C] RED test in `epocha/apps/economy/tests/test_initialization.py` (or extend): `test_effective_production_scale_is_template_value` — after `initialize_economy` on a pre_industrial template (default_scale=2.0), assert the effective scale reaching the production engine is 2.0, not the dead 5.0 (per-good) or 1.0 (engine fallback). Fails today.
- [ ] T009 [C] Fix `initialization.py`: read `default_scale` from the template (`prod_cfg`), stop hardcoding per-good `scale=5.0` (drop the key so `production.py`'s `default_scale` fallback applies, OR set it to the template default_scale), and add `"default_scale": default_scale` to `sim_config["production_config"]` (line ~166) so `engine.py:138` receives the calibrated value. GREEN T008.
- [ ] T010 [C] Gates + commit `fix(economy): propagate calibrated production scale from template`.

## Group D — Conservation rewrite, approach A (distribution.py + engine.py, engine-coupled)

- [ ] T011 [D] RED test in `epocha/apps/economy/tests/test_distribution.py`: `test_factor_shares_partition_output_value` — for a zone with known output value V, assert compute_rent + compute_wages + residual profit sum to exactly V (shares sum to 1), NOT each equal V. `test_owner_not_double_paid` — a producing owner does not receive both full output value as wage AND rent on the same output. Design the new signatures: distribution functions return factor SHARES of a single output value V, with rent_share + wage_share + profit_share = 1 (defaults e.g. rent 0.15, wage 0.55, profit 0.30 — tunable, template-sourced where possible; document the partition and cite the classical tripartite factor-income identity, Ricardo 1817 / national accounting).
- [ ] T012 [D] RED test in `epocha/apps/economy/tests/test_economy.py` (engine integration): `test_tick_money_injection_equals_output_value` — over one economic tick, the net cash injected by the rent+wages+profit step equals the zone output value V (not >V), verified against the EconomicLedger entries. Fails today (injects rent≈V AND wages≈V).
- [ ] T013 [D] Implement conservation in `distribution.py`: refactor compute_rent/compute_wages to distribute a bounded SHARE of the single output value V (partition summing to 1), and add the profit residual to the producing entity (owner/firm). Document approach A and the identity. Keep dimensional consistency.
- [ ] T014 [D] Implement in `engine.py:348-402`: the rent/wages/profit step credits factor incomes summing to V per zone per tick (the monetary counterpart of newly produced goods), via a producing-entity account that is credited V and debited the factor payments — so the ledger shows the partition, not two independent full-V injections. Preserve the tax step (already conservative). GREEN T012.
- [ ] T015 [D] Regression: run `test_economy.py` (the §4.2 behavioral integration tests that consume these flows) — if any expectation encoded the old double-injection, update it with an explicit justification in the commit; §4.2 whitepaper doc-sync check (does the §4.2 model description depend on the old flow? if yes, note it). Gates + commit `fix(economy): partition output value into conserved factor incomes (approach A)`.

## Group E — Trade rationing + demand (market.py + engine.py, engine-coupled)

- [ ] T016 [E] RED test in `epocha/apps/economy/tests/test_market.py`: `test_execute_trades_conserves_quantity` — with N buyers and M sellers for one good, assert sum of trade quantities == min(total_supply, total_demand), and that no seller sells more than it offered and no buyer buys more than it wanted. Fails today (N*M fabrication). `test_execute_trades_short_side_rationing` — proportional short-side rationing.
- [ ] T017 [E] Fix `execute_trades` (`market.py:282-302`): short-side rationing with running totals — track remaining_buy per buyer and remaining_sell per seller, match `min(remaining_buy, remaining_sell)`, decrement both, so sum(buys)=sum(sells)=min(supply,demand). GREEN T016.
- [ ] T018 [E] RED + fix MKT-5 (`market.py:212-225`): replace the elasticity-as-divisor discretionary demand with a budget-constrained rule — allocate a bounded fraction of cash across non-essential goods subject to sum(p_i*q_i) <= cash*spend_fraction, OR document it explicitly as a heuristic with the demand model it approximates and what is lost; source or tag-tunable the spend fraction. Test that total discretionary spend across goods cannot exceed the agent's cash.
- [ ] T019 [E] Fix MKT-6 (`market.py:111,141-142`): use a single price-ceiling anchor (base_prices) in both the zero-supply and main branches so the cross-tick-drift protection is consistent.
- [ ] T020 [E] Gates + commit `fix(economy): ration trades on the short side and budget-constrain discretionary demand`.

## Group F — Live money aggregate + diagnostics (monetary.py + engine.py + models, engine-coupled)

- [ ] T021 [F] RED test: `test_money_supply_tracks_circulating_cash` — after economic ticks, the Currency.total_supply (M) equals the aggregate circulating cash + deposits, not the static template constant. `test_fisher_consistency_called` — check_fisher_consistency is invoked in the tick and its divergence recorded/logged.
- [ ] T022 [F] Implement CM-2: make M a live per-tick aggregate (sum of agent cash across the primary currency + banking deposits), reconciled with banking total_deposits (single source of truth); wire check_fisher_consistency into the tick as a diagnostic gate using the live M, the measured velocity, the system price level and output. Update models/engine as needed (no schema migration if total_supply is recomputed in place).
- [ ] T023 [F] Fix CM-5: inflation and the stability price-level use SYSTEM aggregates, not last-zone-wins dict.update() merges — aggregate prices across zones (e.g. mean or output-weighted) before computing inflation.
- [ ] T024 [F] Fix CM-6: reconcile mood thresholds (poverty 10, satiation 100) with the initialized wealth scale (property base_value 100, elite cash 300-500) — either scale the thresholds to the initialized wealth distribution or document the intended mapping so agents do not all start past satiation / below an unreachable poverty band.
- [ ] T025 [F] Gates + commit `fix(economy): make money supply a live aggregate and wire the Fisher diagnostic`.

## Round 2 re-audit

- [ ] T026 Re-run the audit workflow on the fixed code (fresh dispatch of `audit-workflow.js` or a targeted critical-analyzer per module) with the mandate: verify each Round 1 finding resolved AND hunt for new issues introduced by the conservation/trade rewrites (money/goods conservation now genuinely holds end-to-end; no new INCORRECT/UNJUSTIFIED). Loop until CONVERGED for all five modules.
- [ ] T027 Full container suite `pytest --cov=epocha -q` green (baseline + new tests, zero xfail/new skips); `ruff check .` and `ruff format --check .` exit 0.

## Promotion (after CONVERGED)

- [ ] T028 Promote the substrate from whitepaper §8.2 to a new §4.x Methods chapter (EN + IT mirrored): numbered formulas (CES, Fisher diagnostic, tâtonnement, factor-income partition), parameters into §6 calibration tables, entry into §7 validation surface. Remove §8.2; reconcile the §8 residual to Knowledge Graph only with a GLOBAL count grep in both languages (per the prior session's lesson).
- [ ] T029 Update README status table if relevant; update the tracker memory (`project_audit_repass_batch_2026_04_12_pending` residual is now Knowledge Graph only — but note this substrate was NOT in that batch; update the §8-residual tracking accordingly); session memory.
- [ ] T030 Final phase-6 adversarial code audit on the full diff; 8-point review; PR to develop (Draft); frozen-pin at merge.

## Dependencies

A, B independent. C → D → E → F sequential (engine.py). Round 2 after all groups. Promotion after CONVERGED.

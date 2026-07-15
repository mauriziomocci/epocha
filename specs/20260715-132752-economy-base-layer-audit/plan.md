# Implementation Plan: Economy base layer audit and promotion

**Branch**: `20260715-132752-economy-base-layer-audit` | **Date**: 2026-07-15 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/20260715-132752-economy-base-layer-audit/spec.md`

## State

Phase 1 (Round 1 adversarial scientific audit) is **DONE**: report at [round1-audit-report.md](./round1-audit-report.md), verdict **NOT CONVERGED**, 10 confirmed findings + 6 cross-module findings. Phase 2 heavy gate is **OPEN pending user ratification** of the remediation approach, because findings D1-D4 change the economic model and the money/goods flows that the already-CONVERGED §4.2 behavioral layer consumes.

## Remediation approach (proposed, awaiting ratification)

Ordered by the auditor's priority, because fixing conservation first changes the flows several later findings depend on (auditor recommends a full re-audit after the conservation rewrite).

1. **Conservation rewrite (CM-1 / distribution PROD-2)** — recommended approach A: the zone's production is credited once to a producing entity (owner/firm), then partitioned into rent + wages + residual profit shares that sum to 1 and settle as transfers, not net-new cash. Touches `distribution.py` + `engine.py` money-flow steps. Regression tests: per-tick money aggregate is conserved (Σ credits = Σ debits), no `from_agent=None` injection outside seigniorage.
2. **Trade rationing (MKT-2)** — proportional short-side rationing with running totals so `Σ buys = Σ sells = min(supply, demand)`; regression test asserting goods and money conservation across `execute_trades`.
3. **Live money aggregate M (CM-2)** — `Currency.total_supply` becomes a per-tick aggregate of circulating cash + deposits; `check_fisher_consistency` wired as a diagnostic gate; reconcile with banking `total_deposits`.
4. **CES Leontief limit (PROD-1)** — `A·min(Xᵢ)` (or documented `A·min(Xᵢ/aᵢ)`); regression test at σ→0 continuity across the σ=0.05 boundary.
5. **Production scale (init PROD-1/2, CM-4)** — propagate `default_scale=2.0`, remove the dead hardcoded per-good 5.0 and the dead engine 1.0 fallback; regression test that the effective scale is the calibrated template value.
6. **Documentation/parameter fixes (MKT-5, MKT-6, monetary PROD-3/4, production PROD-4, CM-5, CM-6)** — budget-constrained discretionary demand or heuristic disclosure; single price-ceiling anchor; docstring/inflation-index notes; tunable tags or citations for magic constants; system-aggregate inflation; mood-threshold vs wealth-scale reconciliation.

## Convergence loop

After the fixes: **Round 2 re-audit** (re-run `audit-workflow.js` via `resumeFromRunId` with the fixed code, or a fresh dispatch) covering the original findings' resolution plus new issues introduced by the conservation/trade rewrites. Loop until CONVERGED for all five modules.

## Promotion (after CONVERGED)

Promote the substrate from whitepaper §8.2 to a new §4.x Methods chapter (EN + IT mirrored), numbered formulas, parameters into §6 calibration tables, entry into §7 validation surface; reconcile the §8 residual to Knowledge Graph only (global count grep, both languages, per the prior session's lesson); update the tracker memory; frozen-pin at merge.

## Constitution Check

- **I/III (Scientific Method + Adversarial Audit)**: Round 1 audit done with two-lens adversarial verification; Round 2 mandatory before promotion. PASS (in progress).
- **II (Verify Before Asserting)**: every finding carries a verified file:line and a source_check; the 20 rejected findings show the verification actually refuted weak claims. PASS.
- **IV (Three-Step Design)**: the remediation approach above is the initial proposal; the phase-2 gate + user ratification is the review before any code. PASS (gate open).
- **V (Evidence-Based Verification)**: fixes are conservation-testable end-to-end (the substrate is live in the tick loop). PASS.
- **Documentation Discipline**: §4.2 doc-sync checked if a substrate fix changes §4.2-consumed values; promotion updates §8→§4 EN/IT. PASS (planned).

## Materialized artifacts

`spec.md`, `plan.md`, `round1-audit-report.md`, `audit-workflow.js`. `tasks.md` is written after the approach is ratified (the task list is the fix breakdown, which depends on D1-D4). `research.md`/`data-model.md` not needed (no schema change; the audit report is the research).

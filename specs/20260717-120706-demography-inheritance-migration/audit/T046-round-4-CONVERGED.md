# T046 — phase-6 adversarial code audit, round 4: **CONVERGED**

**Date**: 2026-08-05. **Branch**: `20260717-120706-demography-inheritance-migration`, tip `cb7a54c`.
**Suite at audit time**: 371 demography tests green, **1190 project-wide**, ruff check and format clean, zero pending migrations, working tree untouched. Demography re-run under `PYTHONHASHSEED=12345` also 371 green.
**Method**: hostile, blind to the coordinator's own conclusions, verifying against source rather than against any remediation summary. All probes ran against a throwaway copy inside the container, since `/app` bind-mounts the repo.

**Verdict: CONVERGED.**

The auditor opened by stating it expected the pattern to hold — three rounds running, each had found the previous round's repair was itself broken. It does not hold this time. Every functional mutation goes red and nothing escapes.

---

## The four round-3 open items

**`clark_regression` parent coefficient — RESOLVED.** `inheritance.py:906` is still two independent literals, so the auditor swept them **independently** rather than accepting the added scenario as proof. Patching only the parent coefficient, **0.60, 0.65, 0.6999, 0.700001, 0.71, 0.75, 0.80 and 0.85 all go red**; patching only the zone coefficient, **0.20, 0.29, 0.300001, 0.31, 0.40 and 0.50 all go red**. Round 3's surviving interval of roughly `[0.65, 0.80]` has collapsed to a `pytest.approx` neighbourhood of 0.7 — about 1e-6 relative on each coefficient separately. `test_weight_is_pinned_exactly_to_seventy_thirty` is the only test that discriminates at that precision; the rounded-label assertions still fire only at 0.85 and 0.4/0.5, exactly as round 2 measured. Scenario 2 also pins a structural choice, not just arithmetic: `_resolve_parent_rank` returns the *father's* rank, and the mother is deliberately set to `middle` (rank 2) against a father at `working` (rank 3), so substituting a midparent would give 2.35 against the asserted 2.7 and fail. The capturing monkeypatch delegates to the real `_rank_to_class_label`, so the label is still genuinely computed — the patch is observational only.

**NEW-3, the parse-stage `MemoryError` — RESOLVED.** The fix chose a 500-character bound over `except MemoryError`, so the auditor attacked the bound rather than the depth check: 46 families of pathological strings, each sized to the largest form fitting inside 500 characters, driven straight at `ast.parse` — nested parens, brackets and braces; unary minus, invert and `not` chains; nested calls, subscripts, attributes, slices, lambdas, f-strings, tuples, ternaries, boolean and comparison chains; 499-digit integers; combining characters, Cyrillic identifiers, BOM, NBSP, null bytes, line continuations, whitespace- and newline-only input. **Zero non-`SyntaxError` escapes.** The obvious evasion — nested parentheses, which cost parser stack but create no AST node and so slip past the depth bound — is closed by CPython's own tokenizer, which raises `SyntaxError: too many nested parentheses` at 201 levels (403 characters), comfortably inside the bound. Forty-five further payloads through the real `evaluate_derived_formula` found no escape either: `float(huge_int)` raises `OverflowError`, an `ArithmeticError`, already caught. The boundary is clean, `> 500` admits exactly 500, and no legitimate formula can approach it — all five templates carry the same 58-character expression, 442 characters of margin, and a realistic multi-term formula is still accepted at 24 terms and 477 characters. Critically the new test is not a tautology: **raising the bound to 10000 makes it fail with the literal `MemoryError: Parser stack overflowed`**, reproducing the exact round-3 defect.

**NEW-7, the broken query budget — RESOLVED at both levels.** `transfer_loans_as_lender` is one `SELECT` plus one `bulk_update` and nothing else when the caller threads; `process_inheritance_batch` resolves once and threads the same list into both consumers, with its QUERY BUDGET now accounting the sister cost separately instead of hiding it inside "up to 2". The auditor measured the delta at a size pair the shipped test does not use — **2 sisters cost 21 queries, 10 sisters cost 29, delta exactly 8** — so the linear claim is not an artefact of the 1-vs-4 comparison the test happens to make.

**NEW-6, the `migration.py` `I-5` labels — RESOLVED.** Both sites now name the design spec's numbering and disambiguate it from the audit's. A third bare `fix I-5` sits eight lines below the disambiguation inside the same docstring; nit, not a finding.

**NEW-8, test coupling — RESOLVED in substance.** The monkeypatch coupling remains, but it now buys both coefficients pinned to 1e-6, which is the property round 3 said it failed to purchase. A rounded label genuinely cannot discriminate a real-valued weight, so this is the only way to observe it.

## Hunting defects the round-4 fix introduced — none found

This was the priority, and where each of the previous three rounds found its worst material.

**Seven mutations against the full suite.** Making `_distribute_matrilineal` ignore `precomputed_heirs`; making `transfer_loans_as_lender` ignore `matrilineal_heirs`; threading `None` (the full pre-NEW-7 double resolution); threading `[]` (a silently wrong value); raising the length bound; removing the length check — **all six functional mutations go red**, naming the tests that catch them. Threading a wrong value is caught functionally, not merely by query count. Only a logging line survived (see residuals).

**The `None`-versus-empty sentinel is correct and honoured.** `None` means "nothing precomputed" and both consumers fall back to lazy resolution unchanged; `[]` means "resolved, none exist", and `_resolve_matrilineal_heirs` returns `[]` without issuing a query when the deceased has no sister, so the one-query-per-sister claim is exact at zero sisters. The default preserves pre-existing behaviour: across five estate magnitudes from 1e-9 to 1e15 the threaded and lazy allocations are identical dicts, and over five loans across two nieces the round-robin lands on the identical lender sequence.

**The hoist cannot drift.** Nothing between the resolution and either consumer mutates aliveness or parentage — `apply_estate_tax` writes only the treasury, and `generate_mourning_memories` and `dissolve_on_death` both run after the loan transfer. Two consecutive resolutions of a three-sister, six-niece family return identical ids; a dead niece and a non-binary sibling's child are correctly excluded from both. The batch-level case the hoist makes newly interesting — two deceased who are sisters of each other, settled in one batch — routes both estates and both loans to the surviving niece correctly. A niece who is simultaneously a child of the deceased is handled by the `agents_by_id` overwrite; a child shared by two sisters is de-duplicated to one entitlement.

## Conservation and the evaluator, re-attacked from scratch

The auditor tested the **corrected narrow guarantee** rather than the old overclaim, over **12,730 allocations** at magnitudes no prior round used: the smallest denormal `5e-324`, `1e-300`, `1e100`, `1e250`, `1.7e308`, every power of two from 2⁻⁶⁰ to 2⁶⁰ and the float immediately below each, at 1, 2, 3, 5, 7, 11, 13, 32, 64, 100, 501 and 1000 heirs, in both equal-split and 2:1-weighted shapes. **The narrow guarantee failed zero times.** The broad one failed 45.0%, consistent with round 3's independently measured 22.3% at 7 heirs and 48.4% at 11 — so the corrected docstring is accurate and now verified twice by different auditors. No production caller checks conservation via `sum()`; only tests do.

At the system level, through the real orchestrator across all five succession rules at four magnitudes, agent wealth plus treasury is conserved with worst relative error 1.8e-16 — C-1's known two-independent-products drift, which is out of scope. The matrilineal threaded path conserves exactly like the other four.

## Out of scope: nothing silently altered

Every ratified deferral verified against source: the kernel is still `h2 * midparent + (1 - h2) * noise` with unchanged single-parent branches (I-4, I-5); `spouse_fraction = 0.125 if children else 0.25` (I-7); `apply_estate_tax` still computes two independent products (C-1); the flight decision still compares a stock against a per-tick threshold (C-4); template rho values unchanged (U-1); era-noise defaults unchanged (U-3); `compute_expected_gain` still subtracts a raw tick count, monetisation still recorded as deferred. All eleven previously-resolved findings hold, including the three migration ones round 3 closed.

## Residuals — recorded, not blocking

The auditor names these as one pattern rather than three items: **the round-4 fix updated every place that stated a query-cost NUMBER, but not the two places that stated the RATIONALE those numbers came from.**

1. **INCONSISTENT, minor.** `inheritance.py:2328-2329` still says `matrilineal` "still pays its own sister-count queries once here" — false for the production path, where the orchestrator threads and zero queries happen in this function, and contradicted by the corrected Write-path paragraph a hundred lines below in the same docstring. Harm limited: the stale sentence's own cross-reference points at the section that corrects it, the code behaves better than the sentence claims, and nothing rests on it.
2. **INCONSISTENT, minor.** `test_inheritance.py:3553-3567` still argues that re-deriving eligibility "would double this function's query cost under `matrilineal`". Post-threading the function holds `matrilineal_heirs` itself, so the rejected alternative could thread at zero cost — the rationale is weaker than stated. It no longer contradicts the budget, which was round 3's actual charge.
3. **MISSING, minor.** The `unresolved_ids` WARNING block has **no test** — the one mutation that survived: deleting it leaves all 371 tests green. Reached by hand and confirmed correct (id dropped, warning fired, loans degrade to banking). The branch is unreachable through any of the five documented rules today.

*(All three were closed immediately after this report, before branch closure.)*

## What the verdict covers

The code as scoped: `inheritance.py`, `migration.py`, the `couple.py` `dissolve_on_death` change (untouched since round 1), and both test modules.

It does **NOT** cover: the deferred design defects — I-4, I-5, I-7, C-1, C-4, U-1, U-3 and the distance-cost monetisation — which remain open and belong to a separate work item with its own phase-2 gate. It does **not** cover the whitepaper, which has not been written for this module. And it says nothing about whether the demography modules are wired into the tick loop, which is Plan 4's business.

## What the auditor attempted that yielded nothing

The parser held against 46 payload families at the length boundary and the evaluator against 45 more, none used by any prior round — no escape, no bypass, no partial evaluation. `float("1e308*1e308")` returns `inf` and `1e400/1e400` returns `nan`, but the derived-trait clamp bounds both into the declared range and the module documents that decision explicitly, so it is not a gap. A non-numeric value in `symbols` escapes as `ValueError`/`TypeError` rather than `FormulaError`, but the Args contract specifies numeric values built internally from inherited floats, so it is a caller-contract question unreachable from template data and unchanged by any round. Passing a non-string expression raises `TypeError` from `len()` exactly as it previously did from `ast.parse` — the failure moved, it did not appear. The matrilineal threading survived every constructible shape: double membership, shared children, dead nieces, non-binary siblings, sisters without nieces, two sibling decedents in one batch, more loans than heirs, fully unresolvable ids. No ordering defect, no divergence between threaded and lazy resolution, no query-count regression on the four non-matrilineal rules. The suite is order- and hash-seed independent. `couple.py` and all five era templates are untouched by the round-4 commit, whose only executable changes are the length check, the two-branch heir selection in three functions, the orchestrator hoist, and the warning block.

# T046 — phase-6 adversarial code audit, round 2 (re-audit): NOT CONVERGED

**Date**: 2026-08-05. **Branch**: `20260717-120706-demography-inheritance-migration`, tip `52ead72`.
**Method**: the auditor ran hostile again, was told only the ratified in-scope/out-of-scope split, and verified every remediation claim against the source rather than against the round-1 report or the commit messages.
**Suite at audit time**: 361 demography tests green, ruff clean, zero pending migrations, working tree clean.

**Verdict: NOT CONVERGED.** Eleven of fifteen in-scope findings RESOLVED, four PARTIALLY RESOLVED — three of them because the fix introduced a new defect — one round-1 test item NOT RESOLVED, and six new findings.

The re-audit earned its cost: **two of the round-1 fixes introduced defects worse in kind than what they repaired.** One is a crash that rolls back a whole tick's inheritance batch; the other silently reduced a propagation the spec mandates to *zero* in the exact scenario the fix was written for.

---

## RESOLVED (11)

**I-1** — `_MAX_CLASS_RANK` is now `max(_CLASS_RANK.values())` = 4 (`inheritance.py:644`), clamped at 726. The auditor verified the rate analytically instead of trusting either Monte Carlo figure: for two poor parents in an all-poor zone `base_rank = 4`, so pre-fix `P(enslaved) = P(eps >= 0.5)` with `eps ~ N(0, 0.75)` = `1 - Φ(0.6667)` = **25.25%**, which is the single quantity behind round 1's 25.4%, the coordinator's 25.23% and the fix comment's 25.09%. Post-fix the label is unreachable by construction. `enslaved` as *input* still resolves via `_EXTENDED_CLASS_RANK`, and `_apply_patrilineal_rigid` still copies the string without a rank round-trip, so the one legitimate path survives. Accepted, tested consequence: under `clark_regression` a child of an enslaved father is now capped at `poor` rather than inheriting the status.

**I-2** — regression runs before the class-rule dispatch (`inheritance.py:925-944`). Nothing else depended on the old order: the regression reads no `social_class`, consumes no RNG draw, and `_apply_meritocratic` is the only branch reading `education_level`, so the shared stream is byte-identical. Residual nit: the `intelligence` precondition is undocumented alongside the `education_level` one.

**I-3** — `inheritance.py:303-314`. The auditor diffed the branch structure against `e685510` rather than reading the new code alone: the two single-parent branches are unchanged and no previously-working case changes value.

**I-8** — `migration.py:170-171` is half-open against an unchanged divisor, exactly `window` ticks. No consumer outside `migration.py` and its tests reads either window function.

**I-9** — all five templates declare `mental_health: 0.4`; `Agent.mental_health` is concrete, so `_agent_has_field` routes it to `setattr`. Data-only, no migration.

**I-10** — `inheritance.py:2915-2920` resolves the primary currency byte-identically to the three existing inline copies in the economy app; the fallback fires only with no `Currency` row.

**I-12** — `_scatter_location_in_zone` (`migration.py:568-635`) reuses `movement.py`'s own `_ARRIVAL_SCATTER_RANGE` and boundary guard; `location` is written with `zone` in both paths.

**C-2** — the auditor re-derived the invariant from scratch across spouse-also-sibling and spouse-also-child under both rules: every allocation sums exactly and the double-listed heir receives one entitlement. It also checked the two rules round 1 did not name and found neither vulnerable.

**C-3** — `inheritance.py:2960` reconstructs the applied tax from the conservation contract; verified against both degenerate clamp branches.

**M-2** — guarded before any personality-routed write, including inside `_apply_derived_traits`.

**U-2** — resolved as documentation, which is what the convergence rule asks for. The auditor checked the comment's Monte Carlo figures analytically: `P(rank=4) = 74.75%` vs the stated 74.61%, `P(rank=3) = 22.97%` vs 23.12%. Honest within sampling error.

## PARTIALLY RESOLVED (4)

**I-6** — both named failures genuinely fixed, but the fix introduces NEW-1.
**I-11** — the real bug is fixed and the denominator telescopes correctly to the window-start population, but the numerator now spans one tick too many: NEW-2.
**M-1** — `Pow`/`Mod` are out of the whitelist and the dispatch, `ArithmeticError` is wrapped, and twenty further payloads found no bypass. But the contract is still not true: NEW-3.
**M-3** — row volume genuinely fixed, but the fix also widened the witness exclusion: NEW-4.

## NOT RESOLVED (1)

**The `clark_regression` 70/30 split is still untested.** `test_inheritance.py:1303` still asserts `0 < child_rank < 4.0` and its docstring now defends the looseness, but round 1 named it a finding. The auditor computed what the whole suite pins for the weight `w`: test 1303 passes for `w ∈ [0.13, 0.875]`, the empty-zone test at 1898 for `w ∈ (0.5, 1.5]`, and the enslaved-father test at 1371 constrains nothing at all since `5w + 5(1-w) = 5` for every `w`. **Intersection: any `w` in `(0.5, 0.875]` passes the entire suite** — Clark's 70/30 could be 0.6, 0.8 or 0.85 and nothing goes red. The other three weak assertions were fixed properly.

---

## New findings introduced by the remediation

**NEW-1 — INCORRECT. `transfer_loans_as_lender` raises `KeyError` under `matrilineal`, rolling back the whole death batch.**
`inheritance.py:2258-2259` looks up `agents_by_id[heir_id]` directly, justified by a docstring claim that a cash-eligible id is always drawn from `heirs`. That is false for one of the five supported rules: `_resolve_matrilineal_heirs` issues a dedicated `_resolve_children_heirs` query per sister to reach nieces and nephews — a relationship the module's own docstring explains `resolve_heirs` cannot reach — so those ids are never in `heirs`. Reproduced end to end: one sister with one living child and one active lender-side loan raises `KeyError` inside `transaction.atomic()` at `inheritance.py:2997`, so the entire tick's inheritance batch rolls back and the loan is left untouched. Bounded only by no shipped template selecting `matrilineal`; it is nonetheless a supported, documented, separately-tested rule, and the fix's own test class covers `nationalized` and `primogeniture` while skipping exactly the one that breaks.

**NEW-2 — INCORRECT. The mass-flight numerator spans `flight_trigger_ticks + 1` ticks.**
`migration.py:1414-1421` filters `W` historical ticks and line 1487 adds this tick's departures, giving `[t-W, t]`. The docstring at 1236-1238 claims the opposite in plain words, and this is the same class of error the I-8 fix corrected fifteen hundred lines earlier in the same commit — I-8's own reasoning is the argument against it. At a constant rate the fraction inflates by `(W+1)/W`: 20% at sci-fi's 5, 10% at modern democracy's 10, 3.3% at the pre-industrial 30. Reproduced at the boundary: a 10-agent zone with five flights all at exactly `tick - 30` and nobody fleeing in the call still fires `MASS_FLIGHT` at `5/15 = 0.333`.

**NEW-3 — MISSING. `RecursionError` escapes the evaluator's `Raises` contract.**
`ArithmeticError` is caught; `_eval_node`'s own recursive descent is not arithmetic. Bisected in the container: `'-'*n + 'x'` returns `FormulaError` at n=900 and raises a bare `RecursionError` at n=1200, with `ast.parse` coping fine, so the blow-up is the evaluator's own descent. Low practical severity, but M-1's whole point was that this module never crashes the birth pipeline on template data.

**NEW-4 — INCORRECT. The M-3 aggregation drops FR-026 propagation to zero in the module's own calibration scenario.**
The fix widened the exclusion from "this victim" to every victim in the zone (`migration.py:1551`, 1566). FR-026 (`spec.md:189`) and acceptance scenario 3 (`spec.md:133`) both require the memory to reach *"tutti gli agenti co-zone"*. Reproduced: a single zone whose six living agents are all trapped produces six `TRAPPED_CRISIS` events and **zero** `Memory` rows — the Irish Famine case where N approaches M, which is exactly what M-3 was written for, so the row count goes from ~250,000 to zero rather than to one per witness. The existing test cannot see it because it always leaves two non-trapped witnesses, and a new assertion positively pins the exclusion, so a test now protects behaviour that contradicts the spec. The row-volume argument never required the narrowing: an aggregate memory delivered to every co-zone agent, victims included, is still `O(M)`.

**NEW-5 — INCONSISTENT. Three "trailing window of N ticks" conventions coexist in `migration.py`.**
`compute_zone_wage` spans `W` (half-open), `compute_zone_unemployment` spans `W+1` (closed, 244-245), the mass-flight window spans `W+1`. The unemployment case produces no arithmetic error, but its constant's comment claims it is "deliberately SHORTER (3 vs 5)" while in ticks actually spanned it is 4 vs 5, and both feed the same Harris-Todaro comparison.

**NEW-6 — INCONSISTENT. The audit labels collide with the design spec's own ratified fix numbering.**
`inheritance.py:248` "Fix I-1 — single-parent fallback" versus `:626` "Fix I-1 (phase-6 audit round 1)", with `:740` referring to "fix I-1 in `inherit_trait`" from inside the rank code where both meanings are live; `:2695` versus `:2824` for C-3 in the same docstring; `migration.py:918` "FIX I-5 IS CONDITION 3" where the audit's I-5 is the single-parent genetic signal. Every future reader has to guess which numbering is meant.

---

## Out-of-scope items — none was silently altered

Checked against the source, not the commit messages: the kernel is still `h2 * midparent + (1 - h2) * noise` (I-4 intact); the single-parent branches are byte-identical to `e685510` (I-5); `spouse_fraction = 0.125 if children else 0.25` is still gender-blind (I-7); `apply_estate_tax` still computes two independent products (C-1); `_resolve_flight_decision` still compares a stock against a per-tick flow (C-4); template rho values are still 0.5 / 0.4 / 0.4 / 0.2 (U-1); the era-noise defaults are unchanged (U-3); `compute_expected_gain` still subtracts the raw tick count (the monetisation ruling not applied).

Two honesty notes, non-blocking: the code carries no marker pointing at the deferred work item, so `inherit_trait`'s docstring still tells a reader the single-parent case "halves the genetic signal" and still cites Falconer & Mackay for a decomposition round 1 showed it does not implement; and `migration.py:383-392` and `:490-492` still say the audit "must rule" on open questions 11 and 12, which round 1 already ruled on.

One new consequence of an in-scope fix, belonging with U-3 in the design work item: `mental_health` now regresses toward `DEFAULT_ERA_MEAN = 0.5` while the model field's own baseline is 0.8, so newborns start around 0.62 and the population drifts to 0.5 over generations. `fertility` has the same mismatch and pre-dates this branch. Nothing reads `mental_health` outside the model definition today, so the drift is currently unobservable.

## What must change before round 3

1. **NEW-1**: survive a `cash_allocation` id absent from `heirs`; add the `matrilineal` case to the test class that skipped it.
2. **NEW-2**: `tick__gt=window_start`; correct the docstring; add a fixture at exactly `tick - flight_trigger_ticks` asserting it does not count.
3. **NEW-4**: restore the victims to the witness set, or escalate the exclusion to a phase-2 amendment; add a whole-zone-famine fixture, which the suite structurally cannot reach today.
4. **NEW-3**: catch `RecursionError`, or bound depth in the walk that already visits every node.
5. **Round-1 item**: pin `clark_regression` at 0.7/0.3.
6. **NEW-5 / NEW-6**: non-blocking, same pass.

## What the auditor attempted without finding anything

The evaluator held against twenty payloads beyond its own suite (`//`, `@`, bitwise ops, `~`, `not`, chained comparison, `yield`, set/dict/generator comprehensions, `print`, `globals`, `__debug__`, `intelligence.__class__.__mro__`, `().__class__`, `'a' * 10`, ternary) — every one refused, no bypass, no partial evaluation. Resource exhaustion beyond `Pow` did not materialise. The conservation invariant survived a fresh attack on exactly the paths C-2 touched, and the C-2 shape was absent from the two rules round 1 did not name. The I-2 reorder has no other dependent and leaves the RNG sequence unchanged. The I-3 fallback changes nothing for previously-working cases. No consumer outside the module assumed the closed wage window. `couple.py` is untouched since round 1.

The test remediation's discrimination claims held up under independent checking: `59778.33 / 7` and `214368.56 / 11` genuinely fail naive reconstruction while the remainder-absorption technique reproduces the target exactly, and the retired `10_000.33` divides exactly at n = 2, 3, 4 and 7, so the old fixtures really could not fail; the two chosen hash seeds genuinely produce different set iteration orders for the five extra personality names; the break-even trapped test lands `expected_gain` on exact `0.0` and is the only test separating `<=` from `<`.

# T046 — phase-6 adversarial code audit, round 1: NOT CONVERGED

**Date**: 2026-07-20. **Branch**: `20260717-120706-demography-inheritance-migration`.
**Scope**: `inheritance.py`, `migration.py`, the `couple.py` `dissolve_on_death` change, and both test modules.
**Method**: the auditor ran blind — it was given no advance list of the open questions already recorded in the handoff, so any overlap is independent rediscovery rather than confirmation bias.
**Suite at audit time**: 308 demography tests green, 1127 project-wide, ruff clean, zero pending migrations.

**Verdict: NOT CONVERGED.** Twelve INCORRECT, three UNJUSTIFIED, four INCONSISTENT, three MISSING.

Four findings were re-verified independently by the coordinator before this report was accepted, and all four reproduce exactly: I-1 (25.23% of children of poor parents in a poor zone are born `enslaved` under `becker_tomes`; the auditor's own figure below is 25.4%, and the small gap is simply two Monte Carlo estimates of the same quantity under different seeds, not a disagreement), I-9 (`mental_health_baseline` is not an `Agent` field; `mental_health` is, and no template declares heritability for it), I-3 (`inherit_trait(None, None, ...)` raises `TypeError`), and the rank-5 label mapping that produces I-1.

---

## INCORRECT

**I-1 — `becker_tomes` manufactures enslaved children out of Gaussian noise, in the modern-democracy template.**
`inheritance.py:676-679`. `_rank_to_class_label` clamps to `_MAX_CLASS_RANK` = 5, and rank 5 is `"enslaved"`. Any perturbed rank rounding to 5 assigns a newborn that class. The module comment at 526-531 asserts the opposite in plain words. `becker_tomes_elasticity_0.4` is `modern_democracy.json`'s `class_rule` — the one era where chattel slavery must never appear. Measured over 200,000 draws with no enslaved parent anywhere: 25.4% for a poor parent in an all-poor zone, 14.1% for a poor-ish zone, 2.2% for working/working, 39.6% where the zone already contains enslaved agents. Nothing downstream reassigns it: `world/stratification.py:45-51` emits only ranks 0-4. Fix: clamp the three sampled rules (`becker_tomes`, `clark_regression`, `meritocratic`) to rank 4, as `_MERIT_RANK_SPAN` already does for this stated reason, and reserve rank 5 for the `patrilineal_rigid` string copy, which never passes through `_rank_to_class_label`.

**I-2 — `_apply_meritocratic` reads `education_level` before it is inherited.**
`inheritance.py:692` reads `child.education_level`; `apply_social_inheritance` writes it later, at 792. For a fresh newborn it is always the field default 0.3. For `sci_fi` (meritocratic, rho 0.2), two parents at 0.9 should give 0.42, so merit is understated by 0.06, `merit_rank` by 0.24 and the final rank by 0.19 — enough to demote a child a full class. The educated elite is systematically under-ranked in the one era whose premise is that education determines standing.

**I-3 — `inherit_trait(None, None, ...)` raises `TypeError`, and the birth pipeline reaches it.**
`inheritance.py:231-239`. The docstring requires at least one parent value but nothing enforces it, and `apply_trait_inheritance` violates it routinely: none of the five Big Five traits is an `Agent` column, so values come from `personality`, which defaults to `{}`. Any birth where neither parent carries the key crashes the whole birth uncaught. Invisible to the tests only because the fixtures populate all six personality keys on both parents. Fix: fall back to `era_mean`, as `_regress_education_level` already does correctly at 720-721.

**I-4 — the polygenic kernel is not variance-preserving; trait diversity halves within three generations.**
`inheritance.py:239`. Falconer & Mackay give the offspring-midparent regression with a residual scaled so offspring variance reproduces parental variance — a stable `h² = V_A/V_P` is the point of the model. Weighting the residual by `(1 - h²)` is a convex combination, not Falconer's decomposition. Simulated over 4,000 agents and eight generations at h²=0.55, era_sd=0.15: sd collapses from 0.150 to a fixed point of 0.0733, **48.8% of the era distribution the code claims to sample**, and stays there. Realized heritability drifts from the declared value after generation one, so the template's cited Jang/Plomin/Zietsch figures stop describing the population. **The spec writes the same formula at line 651, so this is a design-level defect, not a coding error** — but the code asserts Falconer & Mackay as its source and the assertion does not hold.

**I-5 — the single-parent fallback does not halve the genetic signal; it doubles it relative to Falconer.**
`inheritance.py:233-236`, docstring 202-206. Replayed on identical RNG state, two parents at 0.9 and mother-only at 0.9 both yield 0.806952 — bit-identical, nothing halved. Against the cited source, the offspring-single-parent regression coefficient is `h²/2`: for h²=0.55 and a parent at 0.9 with era_mean 0.5, the correct expectation is 0.610, the code gives 0.720. **The spec repeats the same false parenthetical at line 699**, so spec and code agree with each other and both misdescribe the source.

**I-6 — `transfer_loans_as_lender` ignores the succession rule; nationalized estates hand loans to the family.**
`inheritance.py:1901-2018`. No `rule` parameter, never consulted. Spec line 787 requires loans to follow "la stessa regola di distribuzione", routing to banking when the rule yields no human heirs, naming `nationalized` explicitly. Under `nationalized` the cash is fully seized while the loans go round-robin to spouse and children. Under `primogeniture` cash goes 100% to one heir while loans spread across spouse, all children, all siblings and `extended_family` — a category no rule ever pays in cash.

**I-7 — the shari'a spouse fraction is gender-blind; Q4:12 gives the widower double the widow.**
`inheritance.py:1671`. Implemented as 1/8 with children and 1/4 without, for either partner. Q4:12 as documented by Powers (1986) is asymmetric: widower 1/2 without child and 1/4 with; widow 1/4 and 1/8. The implemented pair is the widow's schedule applied to everyone, so a surviving husband receives half his entitlement in both branches. The surrounding structure — fixed share first, 2:1 residuary after — was verified correct, including non-binary handling in `_split_two_to_one`. **The spec states the rule gender-blind at line 745 while citing Powers for a structure Powers does not support.**

**I-8 — `compute_zone_wage` divides by `window` while its filter admits `window + 1` ticks.**
`migration.py:153-164`. The closed interval spans `window + 1` distinct ticks — the docstring says so at 118-120 — but the divisor is `population * window`. With one 100.0 wage row per tick and one agent it returns 120.0 where the true per-tick wage is 100.0: a **20% overstatement** at the default, 33% at window 3, 100% at window 1. Worse, the error is proportional to how evenly wage activity spreads over the window, so steadily-employed zones are inflated and burst-paid zones are not, biasing every migration decision for a purely arithmetic reason. Every fixture places wage rows in one tick only, so no test can distinguish the two readings.

**I-9 — `mental_health_baseline` is not an `Agent` field; mental health is never inherited.**
All five templates declare `mental_health_baseline: 0.40` in the heritability table. `Agent` has `mental_health`, not `mental_health_baseline`. The value lands in `child.personality["mental_health_baseline"]`, which nothing reads, while `Agent.mental_health` keeps its default forever. The spec's table at line 673 clearly means the model field. The un-special-cased routing is correct in itself; the name mismatch is what makes the loss invisible.

**I-10 — estate revenue is credited under a hardcoded `"USD"` that no other treasury caller uses.**
`inheritance.py:2422`, used at 2668 and 2705. Every other `add_to_treasury` caller resolves the simulation's real primary currency (`economy/engine.py:732`, `economy/property_market.py:348`). In any simulation not denominated in literal USD — the design's own example uses LVR — ordinary revenue accumulates under one key while estate tax and heirless estates accumulate under another. For `modern_democracy` that is 40% of every estate plus every unclaimed estate, permanently sequestered in a bucket no spending path reads. Per-death arithmetic conserves; the system ledger does not.

**I-11 — the mass-flight fraction mixes a windowed numerator with a point-in-time denominator.**
`migration.py:1182-1205, 1322`. Agents who fled earlier remain in the numerator but have left the denominator, so the ratio inflates monotonically at a constant departure rate and can exceed 1.0. A 100-agent zone losing one agent per tick with `flight_trigger_ticks=30` crosses the strict 0.30 threshold at tick 24 (24/76 = 0.316) rather than never — the true cumulative share at tick 30 is exactly 0.300. The denominator should be the population at window start.

**I-12 — household migration writes `zone` without `location`.**
`migration.py:722` and `1261`. `agents/movement.py` treats the pair as matched, writing both on arrival and interpolating `location` on partial journeys. After a family coordination or emergency flight, partner and minor children have `zone = destination` while their coordinates still sit in the origin zone, so any spatial consumer computes from a position the zone FK contradicts.

## UNJUSTIFIED

**U-1 — `education_regression_rho` in three templates contradicts the spec's cited values.** Spec 727-731 gives 0.5 / 0.42 / 0.35 (Chetty et al. 2014) / 0.25; templates carry 0.5 / 0.4 / 0.4 / 0.2. Only pre-industrial matches. The modern value is attributed to Chetty and shipped at 0.4 with no citation. Pre-existing (templates last touched in `07ab8d4`), but this code turns it into outcomes.

**U-2 — `_BECKER_TOMES_RANK_NOISE_SD = 0.75` has no bound and no sensitivity check.** It is the parameter that produces I-1. Clamping at both ends also means the realized elasticity is not 0.4, since mass piles at ranks 0 and 5.

**U-3 — `DEFAULT_ERA_MEAN = 0.5` / `DEFAULT_ERA_SD = 0.15` are placeholders that are in fact the parameters.** No template declares an `era_noise` section, so these are used for every trait, every era, every birth. Combined with I-4 they set the fixed point the population converges to.

## INCONSISTENT

**C-1 — `apply_estate_tax` reintroduces the float drift `_allocate_with_exact_remainder` exists to eliminate.** `inheritance.py:1390-1391` computes tax and remainder as two independent products; over 200,000 random pairs, 18.8% fail `tax + remainder == total`, worst error 1.16e-10. Writing `remainder = total - tax` cuts it to 4.9%. Spec-specified at line 759, so inherited — but the module cannot claim an exact invariant while one step does not hold it.

**C-2 — a heir in two categories silently destroys value.** `inheritance.py:1682-1690` assigns rather than adds, so a spouse who is also a sibling overwrites their own sibling share: reproduced with 1000.0 inheritable and a spouse-sibling among two siblings, the allocation sums to 500.0. `_distribute_equal_split` has the same shape. Reachable: `couple.py:186-300` has **no consanguinity check** and `marriage_market_radius: "same_zone"` concentrates candidates among a small, related pool.

**C-3 — the event payload reports tax from the unclamped rate.** `inheritance.py:2670` uses the raw template rate while `apply_estate_tax` clamps internally, so a malformed rate credits the treasury correctly and reports 100× too much in every event.

**C-4 — comparing a wealth stock against a per-tick subsistence flow.** `migration.py:952`. Defensible as "cannot afford this tick's food" and spec-specified at 838, but it silently fixes the survival horizon at one tick and treats an agent with thirty ticks of savings identically to one with a single tick.

## MISSING

**M-1 — the evaluator's `Raises` contract is incomplete and `**` allows unbounded resource consumption.** Thirty payloads found **no code-execution bypass**; the two-stage design holds. But `1/0` raises `ZeroDivisionError` rather than `FormulaError`, and `9**9**9` passes both guards — a probe process hung past 120 seconds and had to be killed. Bound the exponent or drop `Pow`, which no current formula uses.

**M-2 — undeclared precondition: `child.personality` must be a mutable dict.** `inheritance.py:383` writes without a guard while every parent read two lines above is defensive.

**M-3 — trapped-crisis memory generation is quadratic in a starving zone.** `migration.py:1277-1307`. Starvation is zone-wide, so N trapped agents among M produce N×(M−1) rows with N≈M: roughly **250,000 `Memory` rows in one tick** at the templates' `max_population` of 500. The docstring's query-budget claim is true of query count and false of row volume. The famine scenario is the module's own calibration target.

## Rulings on the previously-recorded open questions

**Question 11, the Harris-Todaro dimensional inconsistency** — ruled: adopt monetisation, `distance_cost_ticks * wage_current`. It restores dimensional balance, reproduces the spec's Paris example exactly (distance cost 0 either way), and means something economically: wages lost while walking. A declared one-unit-per-tick scaling is strictly worse, because it makes the migration threshold depend on the arbitrary scale of the currency. Note this interacts with I-8: fixing the wage divisor moves `wage_current` and therefore the monetised cost by the same 20%.

**Question 12, per-zone stability** — ruled: the model does need a genuine per-zone signal, because a constant reported per zone carries no information and actively misleads the LLM into believing it is comparing zones on a dimension where they are identical. But refusing to invent a proxy under SC-005 was right for this plan. Either drop `zone_stability` from the per-zone block and report it once at outlook level, or label it explicitly as simulation-wide in the prompt text. A real per-zone field is a separate work item.

## Test quality — the findings that block re-audit

Several fixes above cannot be verified by the current suite:

- **The six AST refusal tests prove almost nothing.** They use `pytest.raises(Exception)` and never import `FormulaError`; five of six payloads also raise under a deliberately insecure `float(eval(...))`, because `float()` cannot swallow the result. Only `abs(intelligence)` discriminates. A payload returning a number would execute and the suite would stay green. Ten refusal categories the whitelist blocks have no test at all.
- **No conservation fixture is adversarial.** `10_000.33` does divide evenly in IEEE 754; every conservation test passes verbatim if `_allocate_with_exact_remainder` is replaced by naive division. `_CONSERVATION_TOLERANCE = 1e-6` is five orders of magnitude looser than the ~1e-11 drift it would need to see.
- **The determinism tests do not test determinism.** `test_same_seed_and_tick_yields_identical_child_state` evaluates a pure function twice on identical inputs. `TestBirthPathDeterminismSC003` shares one interpreter and therefore one `PYTHONHASHSEED`, so deleting `sorted(extra_names)` at `inheritance.py:359` would not fail it. Proving that needs a subprocess under a different hash seed.
- **Every `TRAPPED_CRISIS` test exercises the wrong branch.** All five use a single-zone world, so `reachable_zones` is empty and the helper short-circuits before the `expected_gain <= 0.0` branch its own docstring names. Changing `<=` to `<` passes the whole suite, and O'Rourke's scientifically meaningful case — destinations exist but none is better — is untested end to end.
- **The shari'a *radd* branch is untested.** No fixture builds a spouse with neither children nor siblings, so `inheritance.py:1687-1690` never runs; deleting it passes every test.
- Four weaker assertions: a window-default test that never calls the function; a negative-estate test asserting `>= 0.0` where the answer is exactly 0.0; an era-coverage `equal_split` assertion of `partner.wealth > 0.0` where every fixture starts at 100.0; and a `clark_regression` assertion of `0 < rank < 4.0` where the value is exactly 1.2, so any weighting between roughly 0.25 and 0.85 passes and Clark's 70/30 split is untested.

## What the auditor attempted without finding anything

Recorded so coverage can be judged, not only output. `_allocate_with_exact_remainder` could not be broken: 100,000 random amounts per rule across five heir configurations, zero non-exact allocations. No code-execution bypass in the AST evaluator across thirty payloads. The `compute_distance_cost` unit chain is dimensionally clean and is the exact inverse of `calculate_max_distance`. The sex-ratio conversion `p_male = ratio/(1+ratio)` is correct. No determinism defect in the ordering — every set is used only for membership or `id__in`, and every list reaching a persisted outcome is explicitly sorted. The `dissolve_on_death` ordering correction is right and the same-tick fallback makes per-partner idempotency hold. MISS-5 intra-tick chaining is structurally impossible as claimed. `pending_credits` accumulates correctly for an heir inheriting from two decedents in one batch.

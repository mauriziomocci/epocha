# Phase-2 heavy gate — adversarial specification review, round 5: **CONVERGED**

**Date**: 2026-08-06. **Branch**: `20260806-112409-demography-design-defects`, reviewed at `9a73b82`.
**Artifact**: `spec.md` and `checklists/requirements.md` in the parent directory.
**Method**: hostile, verifying against the code, the design spec, the five era templates and both whitepapers, re-measuring every figure rather than inheriting it. The reviewer drove the real functions — `inherit_trait`, `_regress_education_level`, `_apply_clark_regression`, `_apply_becker_tomes`, `_apply_meritocratic`, `_apply_patrilineal_rigid`, `_validate_template`, and the estate-tax arithmetic — against synthetic populations of 20,000 to 40,000 agents.

**Verdict: CONVERGED**, at the fifth round.

---

## The test that decided it

A requirements document written to correct something must **fail against the thing being corrected**. Round 3 rejected this specification because none of it did. Round 5 re-ran that test mechanism by mechanism, and every one of the twelve defect mechanisms is now bound by something measured false today:

| defect | bound by | measured today |
|---|---|---|
| polygenic kernel residual mis-scaled | SC-002 (≥90% of declared spread) | **48.72%** simulated, 48.845% analytic |
| education regression deterministic | FR-002b + SC-011 (≥50% of initial) | **0.024%** at ρ=0.5, **0.0000%** at ρ=0.2 |
| Clark class regression frozen | FR-002b + SC-012 (mobility > 0) | **exactly 0.0000** from generation 2 through 8 |
| single-/no-parent residual scale | FR-003 + SC-013 | 53.9% / 44.7% today |
| era-noise parameters unsourced | FR-004 | no template declares `era_noise` |
| shari'a spouse share gender-blind | FR-005 + SC-004 | gender never read |
| migration dimensionally inconsistent | FR-006 | a tick count subtracted from a per-tick rate |
| estate-tax conservation | FR-007 + SC-006 | 16.05% at 0.15, 6.05% at 0.40, 0% at 0.0 |
| subsistence horizon | FR-008 + SC-014 | design line 153 incoherent, line 841 single-tick |
| template ρ versus cited sources | FR-009 + SC-007 | design cites 0.35, templates ship 0.4 |
| template loader validates nothing | FR-014 + SC-015 | accepts invented key, rate 40, h² 5.0, ρ −0.9 together |
| zone stability not per-zone | FR-015 + SC-016 | one simulation-wide scalar |

## The split criterion, attacked specifically

Round 4 blocked because a single percentage floor spanned incommensurable scales. Round 5 attacked the replacement:

- **The dispersion floor is reachable and not vacuous** — the rare case of a number right on both sides. It fails today at 48.7% and a legitimately repaired model clears it: the whitepaper's own corrective form gives 99.4% two-parent, 95.7% single-parent, 92.1% no-parent. The worst branch clears the 90% floor by 2.1 points, and does so for every heritability the templates ship.
- **The mobility floor discriminates exactly where dispersion does not.** Clark's dispersion measures 90.8% of the founder partition — it would sail past a dispersion floor — while its mobility is zero. Becker-Tomes measures 0.5824 and passes.
- **The exemption does not leak.** The requirement is a closed positive list, so a broad reading of the exemption clause cannot reach further. The reviewer also tested the claim that the meritocratic rule heals itself rather than taking the argument on trust: repairing intelligence and education alone lifts its mobility from 0.094 to 0.328 and its dispersion from 33.3% to 46.9%, without touching the rule.

## Findings, all non-blocking, all repaired before this report was filed

1. **INCORRECT** — the post-repair figure for the meritocratic rule was 38%, which is the generation-2 unrepaired transient; measured 46.9% after full repair. The conclusion it supports (a 50% dispersion floor is unreachable for that rule) survives at the corrected figure. **Corrected to 47%.**
2. **INCORRECT** — the criterion asserted that the loader accepts all nested absences today. It does not: three distinct nested absences under `mortality` are rejected. So nesting alone does not discriminate — the *identity* of the section does, and `era_noise` is the real case. The criterion is conjunctive and still fails today on its other two clauses. **Statement corrected.**
3. **MISSING** — the mobility criterion did not name its referent, and the referent decides the verdict: Clark's mobility today is 0.0000 against the father, 0.7231 against the mother, 0.5058 against the midparent. Under two of three readings the criterion would have passed against unrepaired code — the exact failure mode rounds 3 and 4 each blocked on. **Pinned to `_resolve_parent_rank`'s referent, the father with fallback to the mother, verified in source.**
4. **MISSING** — a dependency between two requirements was unstated: if the noise parameters are resolved as project parameters rather than as a template section, the loader requirement loses its intended test case. **Dependency now stated.**
5. **UNJUSTIFIED** — the mobility floor carries no magnitude while its twin carries two. Judged non-blocking and left as is, consistent with the division of labour the document defends elsewhere: the magnitude of the innovation belongs to the amending design document, as does the choice of construction and of distributional family.

The title was also corrected — it said "eight defects" against a scope the body establishes as ten.

## What the verdict covers, and what it does not

**Covers**: the specification is sound and complete enough to plan a design amendment against.

**Does not cover**: none of the corrections it points at are validated. Whether the whitepaper's corrective kernel is the right one, whether Todaro's planning horizon is the right instantiation, whether the subsistence horizon should be a hunger test or a precautionary-savings test, and whether the chosen distributional family preserves variance under the clamp — all of that belongs to the design gate, and then to the phase-6 code gate.

One consequence worth carrying forward: a design that keeps the truncated Normal while resolving a per-trait era mean to 0.8 would land the no-parent branch at 86.4% and **fail** SC-013. That is the criteria working as intended, and it means the distributional-family change is mandatory in practice rather than optional.

## What the reviewer attempted without finding anything

It tried to break the single- and no-parent figures expecting them to be unreproducible, and found the whitepaper states the `h²/2` single-parent coefficient explicitly, which reproduces both exactly. It tried to refute the provenance claim about the discredited "one in five" conservation rate and instead confirmed it: drawing the tax rate from the range the shipped rates inhabit gives 20.1%, bracketing the figure the whitepaper published. It looked for a hole in the exemption and found the requirement positively scoped. And it looked for joint unsatisfiability between the dispersion floor, the three-branch criterion and the requirement that the suite stay green, and found the worst branch clears the floor for every shipped heritability.

## The five rounds, in one line each

Recorded because the shape repeated, and naming it is worth more than the individual findings.

1. **NOT CONVERGED** — three claims inherited from a prior audit and taken on trust; all three wrong, including a migration remedy that does not balance the units.
2. **NOT CONVERGED** — a floating-point construction the spec itself prescribed, exact only below a tax rate of one half and certified on a sample that never went there; plus a transmission defect four times larger than described, including an education regression with no stochastic term whose dispersion collapses to zero.
3. **NOT CONVERGED** — after round 2's rewrite, **not one requirement or criterion failed against the unrepaired kernel the work item exists to fix**: widening the requirement to cover four mechanisms lost the bite on the one that mattered.
4. **NOT CONVERGED** — one percentage floor across incommensurable scales: it certified the frozen class rule as sound (90.8% dispersion, zero mobility) and condemned another to a floor no repaired model can reach.
5. **CONVERGED** — every mechanism bound by something false today, both floors reachable and failing, remaining findings in rationale prose rather than in any binding requirement.

**The recurring shape**: at every round, the decisive defect was a criterion that could not fail where the requirement was false. It was found and fixed at the periphery three times before it was found at the centre.

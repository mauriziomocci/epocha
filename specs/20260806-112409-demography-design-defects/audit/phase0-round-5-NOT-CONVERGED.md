# Phase-0 adversarial audit, round 5 — NOT CONVERGED

**Context**: the amendment was REWRITTEN, not patched, after four rounds whose common diagnosis was that additive remediation kept creating fresh audit surface. Round 5 is therefore first a regression check.

**Verdict**: NOT CONVERGED. 5 INCORRECT, 1 UNJUSTIFIED (mitigated), 5 INCONSISTENT, 3 MISSING, and a large VERIFIED block.

## The regression check — 16 of 17 survived

Every INCORRECT and UNJUSTIFIED fix from rounds 1-4 was checked against the rewritten text. Surviving: the annuity in ticks via `World.tick_duration_hours`; rho = 0.60; the Beta rejected for non-closure with Bhatia-Davis declared universal; the recalibrated normal with the logit as migration path; `m_edu = 0.30`; A9 carrying A1's checks rather than the retracted margin; Clark's derived-then-solved amplitude with all four well-posedness conditions; `b = 0.7` not attributed to Clark; the 0.7-0.9 range; the 63.2% dispersion; the sqrt(2) bound; the SD/variance inflation figures; SC-015a as a strict superset of SC-015; the [0,5] input scale; `heritability["default"]` removed.

**Lost in the rewrite**: the estate-tax Sterbenz assignment, emitted inverted.

## The INCORRECT findings

**F-1 — the Sterbenz branches are inverted**, in the one section whose purpose is exactness, and A6 contradicts itself three lines later. Measured over 40,000 draws per rate, the clause as written fails on 7.04% at rate 0.15, 5.95% at 0.40, 3.54% at 0.55 and 12.66% at 0.70; the correct assignment fails on none from 0.0 to 0.99.

**F-2 — SC-002a is unsatisfiable by the corrected model.** It reads the standard deviation of the returned residual, but truncation acts after the draw, so that quantity is not `c*s`: measured by quadrature the relative miss is 2.8e-4 to 8.0e-4 for the trait branches and 1.2e-2 to 2.0e-2 for education, against a 1e-12 tolerance. A standard deviation is also a sampling quantity and can never be "exact, not sampled". The reading that works is a two-point probe on the pre-truncation path.

**F-3 — `flight_trigger_ticks` does not "vale 30"**, and A8's argument for the hunger test rests on it. The five templates ship 30, 30, 20, 10, 5, and the module documents "NEVER hardcoded here". The appeal to "a month" also assumes a tick is a day, which A7 in the same amendment declares MUST NOT be assumed.

**F-4 — the declared evaluation branch is the most permissive for the binding check.** Edge mass rises monotonically toward the no-parent branch (2.15/2.23/2.28% at the education pair), so evaluating on the two-parent branch admits templates that breach the property on a branch the model runs.

**F-5 — the assortative-mating crossings match neither the printed formula nor the adopted family.** From the formula they are r = 0.5217 and r = 0.4235; measured on the truncated normal, education does not reach 105% until r ~ 0.75.

## UNJUSTIFIED (mitigated)

**F-11 — the 3% edge ceiling is disclosed circularity, not removed circularity**: its lower anchor is the value it must admit, and it governs the family choice. Formally inside principle I's tunable-heuristic clause; substantively a threshold calibrated to its own answer.

## Verified clean, re-derived independently

The three residual scales and both signal coefficients, with A1's printed derivation correct and self-contained; the defect magnitudes (48.846%, 79.0%, 21.0-51.1%, 95.82%, 92.13%); the h2**4 inflation to the last digit; every truncated-normal verdict A1 claims; Clark end to end including the non-monotone map, the multiple fixed points and the root 0.6890; A7's arithmetic and Sjaastad's 9.889/9.817; A6's magnitudes and the one-ulp maximum relative error; SC-002b's sample sizes; and every code claim in the amendment against source.

## THE DECISION (auditor's)

Fix F-1 by swapping the operations back and deleting one of the two contradictory sentences. Then rewrite SC-002a as a two-point probe on the pre-clamp coefficient — as written, the criterion the whole amendment hangs on fails the model the amendment prescribes.

## Remediation applied

Both decisions taken, plus F-3, F-4, F-5 and the minor inconsistencies. The 3% ceiling was **deleted** rather than better justified: no source fixes a tolerable boundary mass, and a threshold anchored on the value it must admit is a parameter without a justified value. Boundary mass is now computed and reported at load as an observable, with the ~4.4% reached at the amplitude frontier declared. SC-019 was added to give FR-006 a mechanically failing test. The 90.8% figure was corrected in spec.md, and research.md now carries a superseded-decision warning at the head of deliberation 0.1a.

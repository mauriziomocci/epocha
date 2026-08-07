# Phase-0 adversarial gate, rounds 6 to 11 — CONVERGED at round 11

Rounds 1 to 5 are filed individually. This report covers the closing arc.

## Round 6 — NOT CONVERGED

Resolved every round-5 finding except those the round-5 remediation itself introduced. Worst: **SC-019 was inverted** — it asserted the expected gain is invariant to `World.tick_duration_hours`, but halving the tick doubles the annuity while the per-tick wage does not compensate, because the economy package never reads that field. The correct implementation failed the criterion and the hardcoded-24 mutant passed it. Also: A9 point 5 commanded four checks after A1 was reduced to three; the two-point probe failed a correct kernel on two unstated conditions; SC-002a dropped education; research.md's deliberation 0.2 still asserted reversed conclusions; A12 ordered spec.md amended and it had not been.

## Round 7 — NOT CONVERGED

Diagnosis narrowed: cross-references were clean, and what failed was **the boundary between two sections each repaired correctly**. A1's 95% admissible floor and SC-002b's 95-105% band were each defensible alone and incompatible together — at the floor the margin is zero and an admissible pair leaves the band at parental correlation 0.2 against a correct implementation. Also: FR-009 names two Chetty attributions and only one had been resolved; the precedence clause was conditioned on an event that had occurred and had self-expired.

## Round 8 — NOT CONVERGED

Established that **SC-002b cannot be repaired by choosing the target**. Corrected, a correct implementation leaves the band at r = 0.2; uncorrected, it exceeds 105% at r = 0.54 for traits and 0.74 for education, thresholds A4 declares reachable; and being sampled, at n = 5000 a pair on the floor fails 49% of replicates. First scoped round: 18 minutes against 24.

## Round 9 — NOT CONVERGED, one blocking finding

The band was demoted from gate to observable. That left **the absolute signal coefficient with no gate at all**: SC-002a probes along the draw axis with the signal fixed, SC-013 pins only the between-branch ratio, SC-003 forbids realized heritability. A kernel shipping `b = k*coeff` with exact residual scales passed everything, and at k = 0 that is the 92.13% the document itself reports. Round duration: 6.3 minutes.

## Round 10 — NOT CONVERGED

The parent-axis probe added in response pins `b` algebraically, but three operating conditions were transplanted from the draw axis without re-derivation: `p` undefined as midparent; `|p1 - p2| >= 1` on an axis of width 1, admitting only the truncation boundaries; and the no-parent branch, where the coefficient does not exist, not declared exempt. Round duration: 3.4 minutes.

## Round 11 — **CONVERGED**

All three conditions specified and independently verified, including the new 0.1 threshold measured at a worst-case relative error of 9.6e-15 against a 1e-12 tolerance — a factor of 104 in hand — and the b range [0.11, 0.55] checked against the thirteen shipped heritabilities. The mirror in spec.md carries all three. The Wrigley & Schofield citation form and the orthography defects are closed.

## What the eleven rounds cost, and what changed as a result

Each full round ran 18 to 25 minutes and 230k to 300k tokens because the auditor re-derived everything from scratch. Scoping the audit to the diff from round 8 onward cut that to 3 to 6 minutes with no loss of severity — round 9's scoped audit found the single most consequential defect of the closing arc.

Two structural decisions ended the loop, and both were deletions:

1. **The boundary-mass ceiling** was removed rather than better justified. Its only anchors were the value it had to admit and the value the amplitude check already admitted — a threshold calibrated to its own answer, governing a family choice.
2. **The amplitude band** was demoted to an observable, for the same class of reason: it could not be satisfied by a correct implementation under either choice of target, and it was sampled.

After both, every acceptance criterion is either exact to 1e-12 or provable by mutation, and everything sampled is reported rather than gated. That eliminated the class of defect that had generated rounds 4 through 8.

**The pattern across all eleven rounds**: where the amendment derived, it was correct every time, and three independent auditors reproduced the same figures. Where it generalised from a single measurement, or stated the consequence of a derivation instead of deriving it, it was wrong every time.

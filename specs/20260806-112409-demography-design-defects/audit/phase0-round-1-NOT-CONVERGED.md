# Phase-0 adversarial audit, round 1 — NOT CONVERGED

**Target**: the "EMENDAMENTO 2026-08-07" section of `docs/superpowers/specs/2026-04-18-demography-design-it.md`
**Date**: 2026-08-07
**Verdict**: NOT CONVERGED

## Tally

5 INCORRECT, 3 UNJUSTIFIED, 4 INCONSISTENT, 11 MISSING, 9 VERIFIED.

## The INCORRECT findings, and what they were

1. **A7, dimensional error survived the dimensional correction.** The annuity factor `a(H,r)` is in YEARS (Sjaastad p.89 computes it per dollar per YEAR) and was multiplied by a per-TICK wage. The 220.5-tick break-even quoted four paragraphs later is only reachable with a x365 conversion that appeared in research.md and never in the amendment, and which assumed a tick is a day while `World.tick_duration_hours` is configurable.
2. **A11 confused single-parent and midparent coefficients** in the paragraph after warning against exactly that. Plug (2004)'s 0.30/0.30 come from ONE joint regression, so the midparent coefficient is their SUM, 0.60. A factor of two on the only literature-anchored value the amendment proposed.
3. **A1's reason for rejecting the Beta was false.** `v < m(1-m)` is the universal Bhatia-Davis bound and constrains every distribution on [0,1] including the logit-normal. Within it the Beta hits any admissible pair exactly and in closed form.
4. **"The support stays open" was a measurement of two configurations promoted to a property.** At mean 0.90 with sd 0.28 - admissible under Bhatia-Davis and accepted by A9 as first written - the solved latent parameters put the saturation threshold 1.15 standard deviations away and 12.45% of the population saturates at exactly 1.0.
5. **`sigma_clark` was declared derived and then admitted to need numerical solving, in the same section.** Rounding and clamping are non-linear, so realized dispersion runs 110.3% / 102.6% / 94.8% / 83.9% of target for sigma_rank 0.8 / 1.0 / 1.2 / 1.5.

## The UNJUSTIFIED findings

6. `b = 0.7` kept "for continuity with the existing implementation" - convenience, which principle I subordinates to science.
7. The amendment's central formula rested on a citation declared unopened, with the cited chapter known to be wrong.
8. A2 made a template section mandatory while declaring not one number: five eras by thirteen traits by two parameters, plus sigma_edu and sigma_rank, all delegated to implementation - which is the escalation trigger, not a plan.

## The pattern the auditor named

Three of the five INCORRECT findings are the same error the amendment exists to correct, repeated one level deeper. The common cause: the amendment measured a lot and derived little. Where it derived - the three residual scales, Clark's variance identity, estate-tax conservation - the auditor's independent derivation coincided exactly. Where it measured one configuration and promoted the result to a property, the property failed just outside the measured point, and A2 guarantees stepping outside it.

**THE DECISION (auditor's)**: A2 must be written first, with the numbers in it. Until `era_noise` is a mandatory-but-empty section, A1 has no parameter space over which to claim correctness, A3 has neither sigma_edu nor sigma_rank, and A9 has nothing to validate beyond the presence of a key.

## What was VERIFIED

The variance identity in all three branches, derived independently and exact. The transport of stationarity onto the observed scale - stronger than the amendment claimed, since the latent process is linear-Gaussian and therefore exactly stationary, with the non-linear map outside the recursion. The `h2**2` vs `h2**4` inflation, analytically +6.03% and +2.12% against the amendment's measured +5.92% and +2.09%. Quran 4:12 word for word. Sjaastad p.84, p.89 and footnote 29, including the 9.89/9.90 rounding inconsistency the amendment reports. Clark's 0.75 constant and 0.7-0.9 range. Black & Devereux Table 3's numbers (the interpretation was the defect, not the figures). And every defect the amendment claims to be fixing, confirmed present in the code.

## Remediation

All eight INCORRECT and UNJUSTIFIED findings remediated in the same session, plus the INCONSISTENT and MISSING ones, including a new section A12 enumerating the acceptance criteria that do not fail against the defective models they are meant to exclude. See the amendment's own "Ciò che il primo giro di audit avversariale ha cambiato" section, which records the eight changes so the history is not lost.

# Phase-0 adversarial audit, round 2 — NOT CONVERGED

**Target**: the "EMENDAMENTO 2026-08-07" section of `docs/superpowers/specs/2026-04-18-demography-design-it.md`
**Date**: 2026-08-07
**Verdict**: NOT CONVERGED

## Half one — the round-1 findings

All eight INCORRECT/UNJUSTIFIED findings of round 1 verified RESOLVED, with the auditor re-deriving each fix rather than reading it. The annuity conversion was recomputed from scratch (a = 3583.15 ticks, worked example 17199.1 LVR, break-even 220.50 ticks, and `r_tick = r_year/ticks_per_year` confirmed exact for a continuously compounded rate). Plug's 0.60 confirmed as an identity and shown internally coherent with the recursion. The Beta retraction, the derivation replacing the unopened Falconer citation, the A10 decision, the SC-014 replacement and the rho table all verified. One INCONSISTENT survived: the (m,s)/(mu,sigma) separation was violated in three places.

## Half two — what the remediation introduced

Five findings at INCORRECT or UNJUSTIFIED, all in material written to fix round 1.

**F-1 INCORRECT — the new 95-105% band does not exclude the FR-003-violating model.** 95.8% is inside [95,105], not outside as two passages asserted. Measured across the fourteen shipped heritabilities, the violating model falls inside the band in 14 of 14 on the single-parent branch (95.82% to 99.39%) and 7 of 14 on the no-parent branch; education at rho=0.60 measures 98.3% and 96.7%, both inside. The band bites only the primary 48.85% collapse, which the old 90% threshold already caught.

**F-2 INCORRECT — A2's education values contradict the code they claim to reproduce.** `m_edu = 0.50` was justified as coinciding with today's fallback and changing nothing numerically. `DEFAULT_ERA_MEAN_EDUCATION` is 0.3 and `Agent.education_level` defaults to 0.3, so the declaration moves the stationary mean from 0.30 to 0.50. And `s_edu` cannot coincide with any fallback because education has no random term today.

**F-3 UNJUSTIFIED — A2's declared values dissolve the justification for the logit family.** A1 and the FAQ both justify the latent scale by the parameter space A2 opens. After remediation A2 declares a centred mean for all thirteen traits in all five eras and closes the space. At the one shipped configuration the recalibrated normal measures 100.1% with 0.07% edge mass; the latent apparatus buys 0.0 percentage points.

**F-4 UNJUSTIFIED — A3 calls the innovation amplitude not tunable while both its inputs are declared tunable heuristics.** `sigma_clark = sigma_rank * sqrt(1-b^2)` with both `b` and `s_rank` declared tunable. The source decides the form of the constraint, not the value.

**F-6 INCORRECT — A9's claim that the fallback ceases to be reachable is false.** The kernel extends the trait-name set with the keys of `Agent.personality`, an unvalidated LLM-populated JSONField, so template validation cannot close it. Removing the fallback as instructed would convert a silent fallback into an unhandled failure at birth.

Plus MISSING findings on sample size (the correct model fails the band 13/40 times at 200 individuals per generation), the parental-correlation bound at which the band becomes unsatisfiable, the admissible-region rule's one-sided rationale and unproven solver convergence, and the absence of any criterion binding sigma_clark to the identity.

## Verified clean

The estate-tax construction (Sterbenz applies from both sides; `total - residuo` exact iff rate <= 0.5, `total - tax` exact iff rate >= 0.5). A10 against FR-015's actual disjunctive wording — the requirement is met, not surrendered. The tick/year conversion including the configurable `tick_duration_hours`. Quran 4:12. Full FR/SC coverage with no orphaned requirement.

## The pattern

Round 1: the amendment measured a lot and derived little. Round 2: the amendment now derives correctly and states the consequence wrongly. Every derivation re-done independently came out exactly as written; what failed was the sentence after it.

**THE DECISION (auditor's)**: fix the criterion as a criterion, not as a number — widening or narrowing the band cannot separate models whose realized amplitudes overlap within Monte Carlo noise. Then resolve the family question: with A2's numbers on the table, either declare an off-centre mean with a source or drop the logit.

## Remediation

Both decisions taken. The criterion is now an exact assertion on the per-branch residual scale. The family is reversed to the recalibrated normal, with the logit declared as the migration path and its trigger condition enforced by a load-time check. See the amendment's "Ciò che il secondo giro di audit avversariale ha cambiato".

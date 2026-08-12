# Phase-0 adversarial audit, round 3 — NOT CONVERGED

**Verdict**: NOT CONVERGED. 7 INCORRECT, 1 UNJUSTIFIED, 4 INCONSISTENT, 4 MISSING.

## The diagnosis, which is about the SHAPE of the remediation

Round 1: the amendment measured a lot and derived little.
Round 2: it derived correctly and stated the consequence wrongly.
**Round 3: it corrected the sentence and left the wrong one next to it.**

Three findings were literally a retracted claim and its retraction sitting eight lines apart. And the two criteria written in round 2's remediation to close round 2's gaps reproduced round 2's headline defect exactly: the +/-5% band on rank dispersion admitted the 102.6% shortcut the same amendment forbids, and the three-sigma truncation margin rejected configurations that pass the property it protects (98.0% and 96.5% both refused), its only operational effect being to cut a declared scientific parameter by 40% so it would pass.

## The INCORRECT findings

1. The exact residual criterion was **vacuous on the no-parent branch**: read as "the sigma handed to the draw", `c0 = 1` passes at zero relative difference while the branch realizes 45% of target at h2=0.55.
2. SC-012's replacement (+/-5% on realized rank dispersion) admitted the construction A2 forbids, and was never shown red.
3. The family-reversal argument asserted "the only configuration this amendment declares" four times while A2 declares two, one off-centre, never measured.
4. A3's retracted "not tunable" headline left standing in bold above its own retraction.
6. `s_rank <= 2.0` justified as the "dispersion" of a uniform on five ranks — that is the variance; the sd is sqrt(2).
7. A11 claimed the code's 0.3 rho default becomes unreachable; there is no rho default, and the real 0.3 is the era mean.

## THE DECISION (auditor's)

Stop adding paragraphs. Delete the retracted text, then re-derive the two new thresholds against the models they must exclude and the configurations they must admit — the same test round 2 applied to the band, not yet applied to its replacements.

## Remediation

Applied by deletion rather than annotation. The three-sigma margin was replaced by the realized-amplitude property itself; SC-012's band by an exact criterion; the criterion's measurement point named explicitly; s_edu restored to 0.15; the replacement criteria given SC ids. Round 4 then found the deletion had been partial.

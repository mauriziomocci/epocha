# Phase-0 adversarial audit, round 4 — NOT CONVERGED

**Verdict**: NOT CONVERGED. 10 INCORRECT, 1 UNJUSTIFIED, 3 INCONSISTENT, 3 MISSING.

## The finding that matters most

**A9 point 5 is the loader contract an implementer reads, and it still carried the retracted three-sigma margin.** A1 had replaced it with the realized-amplitude property; the round-3 remediation edited the numeral "three checks" to "four checks" and left the criterion. Applied to `(m_edu = 0.30, s_edu = 0.15)` — the pair A2 declares and A1 measures as passing — `0.30 - 0.45 < 0` rejects it. The amendment required the loader to accept and to reject the same declared pair, which made it unimplementable.

## The other INCORRECT findings

- **The 3% edge ceiling makes the amplitude check dead code.** Scanned over a grid, eleven configurations pass amplitude >= 95% and fail edge <= 3%; zero fail the reverse. So check 3 can never fire, and the declared logit-migration trigger ("below 95% amplitude") is not what the loader implements.
- **The retraction of the three-sigma margin rested on a measurement that does not reproduce.** (0.50, 0.25) was cited at 96.5%; it measures 95.34-95.87%, and carries 4.4-4.8% edge mass, so A1's own check 4 rejects it. It is not a configuration that satisfies the property.
- **The 90.8% figure for Clark's current dispersion is arithmetically impossible** under the sqrt(2) anchor round 3 added: the deterministic map collapses the support to {1,2,3}, where the maximum sd is 1.0 = 70.7%. The measured value is 0.8944 = 63.2%, and the wrong figure has propagated to spec.md.
- **SC-012a is ill-posed over most of the range A9 admits.** The map sigma_clark -> realized dispersion is non-monotone (0.894 as sigma -> 0+, collapsing to 1e-4 at sigma = 0.075, then rising to 1.395), so for s_rank <= 0.894 the bisection bracket has no sign change while two roots exist, and above 1.395 no root exists.
- **"Five-state Markov chain" is not a Markov chain**: the zone class mean is computed from the population being solved for, making it a mean-field fixed point with genuinely multiple solutions — at sigma = 0.001, uniform start gives sd 0.894 and single-rank starts give 0.000, all exact fixed points.
- **Check 3 is not computable from its declared inputs**: realized amplitude depends on the branch coefficient as well as (m, s), and at (0.50, 0.25) the spread across branches straddles the 95% threshold.
- **h2**4 inflates the standard deviation by 6.03% and the variance by 12.43%**; the amendment reported the former calling it the latter, in the section demanding a variance assertion.
- **heritability["default"] is dead** once the transmitted set closes, and the rationale given for keeping it is contradicted by the source.

## Verified clean, re-derived independently

The three residual scales; the 48.85% collapse and the 21.0-51.1% loss range; 95.82% and 92.13% for uniform c2; SC-002b's sample sizes analytically; A3's discrete-scale table; A4's correlated-parent target and both band crossings; A7 end to end (a = 3583.9 ticks, 17,198 LVR, 220.5 ticks, Sjaastad's 9.889/9.817); A6's Sterbenz construction; A9's sqrt(2); A11's rho = 0.60 identity.

## THE DECISION (auditor's)

Rewrite A9 point 5 to A1's four checks before anything else, then decide whether the edge-mass ceiling is a real property with a derived threshold or delete it and keep the amplitude check alone — as written one of the two is dead and the surviving one was set to admit the value the amendment wanted.

## Remediation applied

A9 point 5 rewritten in A1's own words, with the evaluation branch named. The 3% ceiling declared as a tunable design threshold with its two anchors stated openly and its dominance over the amplitude check acknowledged, rather than defended as derived. The 90.8% corrected to 63.2%. The Clark solve given its well-posedness conditions: initial vector fixed at uniform, s_rank restricted to [0.95, 1.39] where the root is unique. The variance/sd confusion corrected.

**Findings NOT yet remediated when the session's working window closed**: the stale duplicate figures (F-13), the retrospective section's own staleness (F-14), the class-rank input scale being [0,5] rather than [0,4] (F-15), SC-015a's narrower coverage than SC-015 (F-12), heritability["default"] (F-9), and the two MUSTs without criteria (F-16). These are recorded here and remain open.

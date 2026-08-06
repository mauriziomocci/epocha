# Specification Quality Checklist: Correzione degli otto difetti di design della demografia

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-08-06
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs)
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous
- [x] Success criteria are measurable
- [x] Success criteria are technology-agnostic (no implementation details)
- [x] All acceptance scenarios are defined
- [x] Edge cases are identified
- [x] Scope is clearly bounded
- [x] Dependencies and assumptions identified

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria
- [x] User scenarios cover primary flows
- [x] Feature meets measurable outcomes defined in Success Criteria
- [x] No implementation details leak into specification

## Phase-2 adversarial review, round 1 — NOT CONVERGED, remediated

An adversarial reviewer audited the first draft against the code, the design spec, the templates and the whitepaper rather than against the spec's own account of them. It returned **NOT CONVERGED** with three INCORRECT findings, and all three were independently re-verified before remediation. They are recorded here because each one was inherited from a prior audit round and taken on trust — which is precisely the failure this gate exists to catch.

1. **The migration remedy the draft endorsed does not restore dimensional balance.** Round 1 of the Plan 3 code audit had ruled that the distance cost should be monetised as forgone earnings, and the draft carried that forward as settled. Verified by hand: `[T] × [M·T⁻¹] = [M]`, so the corrected term is money while the other two remain money per tick — one mismatch traded for another. Balance requires a planning horizon in ticks that nothing in the design, the code or the whitepaper names. User Story 3 was rewritten so the gate's job is to name and justify that horizon rather than ratify the prior ruling, and a note was added warning that the design's own worked example cannot discriminate between candidate corrections, since its distance cost is zero.

2. **"Nothing declares the survival horizon" was false.** The design spec declares it at line 153 as a general convention — `N` subsistence ticks, default 30 — and then omits it from the flight condition at line 841. This is a contradiction inside a CONVERGED spec, not an undeclared simplification, and it changes the remedy: declaring "one tick" would leave line 153 standing and contradicted. The story was rewritten and raised from P3 to P2, with the consequence stated that adopting `N = 30` alongside a `flight_trigger_ticks` of 30 converts a starvation test into a precautionary-savings test. The reviewer also found the same stock-over-flow comparison live in the fertility module, so the decision lands on two consumers, not one.

3. **Both magnitudes in User Story 4 were wrong.** Re-measured directly: the conservation failure rate is 16.1% at a 0.15 rate, 6.0% at 0.40, and **zero at a 0.0 rate, which three of the five templates ship** — so the defect is absent from two pre-industrial eras and from sci-fi. Maximum relative error is 1.9e-16, one ulp; the 1e-10 figure that circulated was an *absolute* error on a large estate, re-labelled. The "one in five" rate could not be reproduced under any distribution tried. The story now carries the measured numbers, states that the fix is warranted because the module asserts an exact invariant rather than because outcomes change, and names the construction that actually achieves exactness — deriving the last term by difference, verified at zero failures in 200,000 trials — while recording that round 1's proposed remedy does not.

Five further findings were incorporated: the residual scale must be specified for all three parentage branches, not only the two-parent case (FR-003); the trait clamp caps achievable variance in a way that worsens as the era mean moves off centre, so FR-002 and FR-004 pull against each other and the tolerance must be a function rather than a number; the sci-fi era's meritocratic class rule makes mating assortative on a heritable trait, breaking the random-mating assumption the variance target rests on (new FR-013); the Chetty attribution must itself be verified before becoming the target, since the design spec cites one source for two different quantities (FR-009); and the four shari'a shares are now written into the requirement instead of being referred to indirectly (FR-005, SC-004). FR-012's premise was corrected: no executable calibration benchmarks exist yet, so the requirement binds future ones.

**Scope insight adopted from the review**: four of the six stories have a correction already derived and published, and need a decision recorded rather than deliberated. Only three questions genuinely require deliberation — the migration planning horizon, the subsistence horizon and its reach into fertility, and the source of per-trait era parameters with its clamp interaction. That is where this work item should be split if it is split.

## Notes

Three points recorded during validation, none of them blocking:

1. **The spec deliberately names file paths** in Key Entities — the design spec, the era templates, the whitepaper chapter, the audit reports. That is not an implementation leak: those artefacts *are* the subject of the work item, since this is a correction of documented science rather than a new capability. The requirements themselves stay at the level of scientific properties (variance is preserved, units balance, shares match the cited source) and never prescribe how to achieve them — deliberately so, because the choice of correction is exactly what the phase-2 gate must decide.

2. **Two success criteria are stated against a tolerance yet to be declared** (SC-002 and SC-003, "within the declared tolerance"). This is intentional rather than vague: fixing the numeric tolerance for variance preservation is itself a modelling decision that belongs to the amended design spec, not to this specification. What is unambiguous and testable here is the property — the dispersion must not collapse to a fixed point, against the 48.8% measured today.

3. **The measured magnitudes carried over from the audit are assumptions, and are flagged as such**, with an explicit requirement to re-verify them against current code before using them as a baseline. Two of the three were already independently reproduced by a second party, but the project rule is verification before assertion, and a specification is not exempt.

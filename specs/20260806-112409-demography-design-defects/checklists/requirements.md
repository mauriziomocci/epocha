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

## Phase-2 adversarial review, round 2 — NOT CONVERGED, remediated

Round 2 found two INCORRECT and six MISSING. One of them changes what the work item is about, and it was found only because the reviewer was told to look for design defects that the *code* audit structurally could not see — it audited code against design, not design against science.

**The scope-changing finding.** User Story 1 described the variance collapse as one kernel in three manifestations. There are **four** intergenerational transmission mechanisms in the module, and only one of them — Becker-Tomes social mobility — carries an innovation term. The worst is the education regression, which takes no random generator at all: it is a pure deterministic contraction whose fixed point is **zero**, not a reduced dispersion. Independently reproduced: starting from a dispersion of 0.150, after eight generations it measures 0.00004 at the pre-industrial regression value and literally 0.000000 at the sci-fi one, with every agent converging on the fallback constant 0.3. It propagates — the meritocratic class rule averages intelligence with education, so that era's class becomes a function of intelligence alone; and the homogamy score weights education at a quarter, so a quarter of the mating criterion goes dead in all five eras. The equation is already published as audited Methods in whitepaper §4.1.4, whose own Simplifications block inventories the deferred defects and does not name it. Fixing only the polygenic kernel would leave traits keeping their spread while education and class homogenise — not a partial fix but a stranger model than the one we started with. User Story 1 was rewritten around the systemic statement: transmission was modelled as a weighted average rather than as a stochastic process, in four places.

**The remedy this spec itself prescribed was wrong.** The previous round wrote a floating-point construction into FR-007 and certified it at zero failures in 200,000 trials — measured only at the shipped rates, all at or below 0.40. The function accepts any rate up to 1.0 by contract, and the construction breaks exactly above one half: independently reproduced at 0.50% failures at rate 0.51, 3.52% at 0.55, 6.05% at 0.60, 12.68% at 0.70. Sterbenz's lemma explains the break precisely, and the worst absolute error the construction produces is 1.164e-10 — the very magnitude this spec's own Assumptions dismiss as a mislabelled artefact of the old report. The prescribed remedy reproduced the defect outside its sample. FR-007 now states the property and refuses to prescribe a construction, which is also what the checklist's own stated principle demanded and what this one requirement had been violating.

**The subsistence line is itself incoherent.** Round 1 corrected "nothing declares the horizon" to "line 153 declares it". Round 2 read line 153 in full: its gloss defines `N` as the number of ticks the agent can survive on current savings, which would reduce the condition to `wealth < wealth` and never fire, while its parenthetical defines `N` as a global tunable defaulting to 30. The line must be rewritten whichever model the gate picks, and FR-008 now says so instead of asking the gate to align one line to another.

Four further findings were incorporated. The variance/era-mean tension is not a trade-off between two scientific properties but the consequence of sampling an unbounded Normal for a variate the code bounds — the real decision is the distributional family, now its own requirement (FR-002a) naming Beta, logit-normal and moment-matched truncated Normal as the alternatives to weigh. The migration horizon is not a free parameter to invent: Sjaastad (1962) founds migration-as-investment with the horizon as expected remaining working life and a discount rate, and FR-006 now requires instantiating that framework or justifying a departure. FR-003 gained the third parentage branch, whose 92.1% is the largest of the three departures and had been quantified nowhere. FR-005 now cites Q4:12 as the primary source for the four shares, since requiring conformity to "the cited source" pointed at Powers — the very attribution the story exists to correct — and the project constitution requires the primary source where accessible.

Two things the previous round recorded without resolving are now resolved. The scope question is decided rather than noted: the six stay together, because all six amend the same design file and two concurrent phase-2 gates on one authoritative artefact would conflict at merge. And the priority criterion is stated honestly as three criteria rather than one, with the observation that "impact on simulated outcomes" is strictly vacuous today, since demography is not yet wired into the tick loop.

The absent FAQ is now argued rather than left silent: its mandated content belongs to the amending design document, and duplicating it here would create two places where the same decision lives and drifts.

## Phase-2 adversarial review, round 3 — NOT CONVERGED, remediated

Round 3's decisive finding is the sharpest of the three rounds, and it indicts the round-2 remediation directly: **not one requirement or success criterion in the document failed against the unrepaired polygenic kernel** — the very defect the work item exists for.

Round 2 had rewritten the requirement from "must preserve variance" to "must be a stochastic process with a non-degenerate stationary distribution", in order to cover all the transmission mechanisms at once. The current kernel *is* stochastic and its stationary distribution *is* non-degenerate — it is merely half as wide as declared. Independently reproduced: after thirty generations it sits at 49.0% of the declared spread and stays there. Widening the requirement to cover four mechanisms lost the bite on the one it was written for, and a plan drafted against that language could have shipped an amendment leaving the kernel exactly where it is while passing every gate. It is the same error this document had already identified and fixed for the conservation criterion one round earlier — a criterion that does not fail where the requirement is false — applied at the periphery and lost at the centre.

A second trap sat underneath it. The natural test — does realised heritability match the declared value — **passes today**: measured 0.5509 against a declared 0.55 at the collapsed fixed point, because the collapse affects the variance and not the regression slope. That criterion is now recorded as an explicit warning rather than a criterion, because it is the most natural thing to reach for and it proves nothing.

The remediation splits the requirement in two: one binding the realised dispersion numerically to the declared spread, with a floor the current model fails, and one covering the mechanisms that lack an innovation term at all.

**Two descriptive errors from round 2 were corrected.** The count is five mechanisms, not four, and **two** carry an innovation term — the polygenic kernel among them. Round 2's text claimed only Becker-Tomes had one, which contradicted its own figures: a mechanism with nothing regenerating dispersion goes to zero, as education does, while the kernel settles at 49% precisely because something regenerates it. And the meritocratic rule does not average a parent against a reference mean at all — it derives class from the child's own inherited traits, so repairing education and intelligence fixes it without a separate correction. Requiring one would have over-scoped the work.

**The Clark class regression's defect was misdescribed.** It does not collapse: integer label rounding freezes it in a single generation onto a fixed partition that is bit-identical for the following eight. Its defect is the opposite of a collapse — zero intergenerational mobility — in a rule cited to a source whose central thesis is slow but strictly non-zero status regression.

**Two new defects were brought into scope, on the document's own argument.** The template loader validates nothing: fed an invented top-level key, a typo'd section name, a tax rate of 40, a heritability of 5.0 and a *negative* education regression, all at once, it accepts them silently — while whitepaper §6.2 publishes the claim that unknown keys raise a validation error. This is the mechanism by which the defects under repair reached production unnoticed, and it is why a missing `era_noise` section is invisible. And zone stability carries the same shape of contradiction as line 153, in the same Sezione 6: the worked example prints three distinct per-zone values while the computation clause reads a scalar that is unique per simulation. Both amend the same design file, so the argument this spec uses to keep its stories together applies to them verbatim.

Smaller corrections: the education weight in the mating score is 0.25 to 0.40 depending on era, not a quarter everywhere — the third time in this document a code default was read as a shipped value; no trait has an era mean of 0.8 today, that being a *field* default of two attributes that regress toward 0.5, so the clamp risk is one the corrections would create rather than one that exists; two failure rates stated for the same tax rate described the same construction and were removed; Todaro (1969) is the nearer source for the planning horizon than Sjaastad, since the model being repaired is his; the whitepaper's other wrong remedy is now in scope for correction alongside the migration one; and restoring education's dispersion resurrects assortative mating in all five eras, not only in sci-fi, so the correction creates the condition that violates the assumption its own target rests on.

## Notes

Three points recorded during validation, none of them blocking:

1. **The spec deliberately names file paths** in Key Entities — the design spec, the era templates, the whitepaper chapter, the audit reports. That is not an implementation leak: those artefacts *are* the subject of the work item, since this is a correction of documented science rather than a new capability. The requirements themselves stay at the level of scientific properties (variance is preserved, units balance, shares match the cited source) and never prescribe how to achieve them — deliberately so, because the choice of correction is exactly what the phase-2 gate must decide.

2. **Two success criteria are stated against a tolerance yet to be declared** (SC-002 and SC-003, "within the declared tolerance"). This is intentional rather than vague: fixing the numeric tolerance for variance preservation is itself a modelling decision that belongs to the amended design spec, not to this specification. What is unambiguous and testable here is the property — the dispersion must not collapse to a fixed point, against the 48.8% measured today.

3. **The measured magnitudes carried over from the audit are assumptions, and are flagged as such**, with an explicit requirement to re-verify them against current code before using them as a baseline. Two of the three were already independently reproduced by a second party, but the project rule is verification before assertion, and a specification is not exempt.

# Adversarial scientific audit: marital fertility spec

Work item: `20261029-185654-marital-fertility`. Spec: `../spec.md`.

Each round is run by an independent `critical-analyzer` subagent dispatched
with a hostile mandate and no access to the author's reasoning beyond the spec
itself, the code of the two reference branches
(`origin/20260826-144432-demography-plan4-wiring`,
`origin/20261029-123404-rule-based-couples`) and the sources. The author
applies the fixes between rounds and records the resolution. Round cap: 10
(decision D-29-30).

Categories: INCORRECT, UNJUSTIFIED, INCONSISTENT, MISSING, VERIFIED.

**Current verdict: NOT CONVERGED after round 1; round 2 pending.**

## Round 1 (2026-10-29, 19:15-19:26, independent `critical-analyzer`)

The reviewer recomputed every number independently (own implementation of
(R1)-(R5), Plan 4 `mortality.py`) and re-read IUSSP PAPP103, Rodriguez (2017),
Woods (2000) and Alter, Newton, Oeppen (2020).

| # | Class | Finding (evidence) | Resolution |
|---|---|---|---|
| R1-01 | UNJUSTIFIED | Becker composition breaks the level claim at ordinary wealth: with seed coefficients the factor is 1.79 at a 340-tick survival horizon (outlook 0) or 46 ticks (outlook +1); realized level is M*E[m_BK], not M. The 60,000-tick figure for the 3.0 cap holds only with other terms at zero; worst case about 8,000. | (N1a) and (N4) now state that T_m is the level at m_BK = 1 and the realized level is M*E[m_BK]; numbers 1.79/340/46/8,000 written (author recomputed 7,991). New SC-006 configuration B measures E[m_BK], its deciles and the share of effective rates above 1, failing if abs(E - 1) > 0.10. New D-MF-09 (measure, then normalise or defer to B2-07; cap rejected because the Hutterite age schedule is unverified). Known limitation and FAQ rewritten. |
| R1-02 | UNJUSTIFIED | Rodriguez's identifiability is a property of estimation, and Epocha does not meet its condition (b, C heuristic; T_m pooled). | D-MF-01, K5, WARNING, (N2) paragraph and FAQ rewritten: the deciding argument is that only the marital factor has a published value; identifiability kept as context only; TFR0 declared to inherit the error of heuristic b and C. |
| R1-03 | UNJUSTIFIED | Hutterite TMFR 12 has no stated age range (likely 15-49); "highest ever observed" is stronger than Woods. | FR-003, source table, S3 and FAQ: 12 is a typo guard, tunable heuristic, age range unknown, probably 15-49; "maximum observed" wording removed. |
| R1-04 | UNJUSTIFIED | Same 6.7 for `industrial` contradicts the whitepaper's "industrial transition" (H = 4). | `industrial` T_m = 6.2, the value that keeps TFR0 at 3.984 against the declared 4.0; uniform-level representation of control declared as a shape error (rinvio 1). D-MF-05 rewritten with three positions; tables recomputed (TFR0 3.984/3.963, NRR 1.862/1.852, rates 0.317/0.272/0.115). |
| R1-05 | UNJUSTIFIED | SC-005 mortality configuration cannot fail. | New coherence failure: error if the lower 95% bound of the harness NRR exceeds the analytic no-widowhood NRR at monthly ticks (1.916), since widowhood can only remove years in union. The doubling-per-generation issue is declared without a threshold here, because it belongs to the mortality work item (rinvio 5). |
| R1-06 | MISSING | 6.7 is pooled over 1575-1849 (Appendix Table 1). | Source table, parameter table, rinvio 4 and limitations say "cumulato sul 1575-1849". The "downward-biased per the authors" reading was not verified by the author and is not written; only the 6.7 to 6.8 fact is. |
| R1-07 | MISSING | FR-006 omits whitepaper sites: §4.1.2 heading, §6.1 row, §9 roadmap item 3, §10 paragraph, Appendix A.2, Appendix C. | All listed in FR-006 for both languages, plus a phase-4 grep instruction for remaining sites. |
| R1-08 | INCONSISTENT | FR-005 named the wrong mechanism and files. | FR-005 rewritten: `hadwiger` appears only in `test_fertility.py` and `test_template_loader.py`; `test_orchestrator_birth.py` and `test_fertility_zone_context.py` change through FR-004; `test_integration_plan2.py` unaffected; phase-4 preflight enumerates all tests loading the three templates. |
| R1-09 | INCONSISTENT | SC-007 script does not exist yet; private `_annual_base_rate`; couples branch is based on develop. | FR-008: the couples phase 6 writes the script, this item modifies it after merge; FR-002 makes `annual_base_rate` public; D-MF-06 records the rebase of the couples branch onto Plan 4. |
| R1-10 | INCONSISTENT | Implied rates 2.37/0.33/0.023 are u = 25.5 values. | "Perché" point 3 uses u = 25.580 values (2.491/0.328/0.023) and states islamic (0.360/0.251/0.020) and industrial (1.391/0.318/0.021); author recomputed. |
| R1-11 | INCONSISTENT | US1 scenario 1 tolerance 1e-9 against a rounded M. | Expected values written as (6.7/8.995)*n(a), tolerance 1e-12; scenario 2 as (6.7/8.995)*0.431*168/8760 = 0.0061568. |
| R1-12 | INCONSISTENT | The draw is Bernoulli with p = r*dt, not a Poisson hazard; no cap p <= 1. | Rinvio 2 and FAQ reworded; expectation argument restated as a sum of per-tick probabilities; missing cap declared (exceeds 1 only with dt = 1 and Becker above 2.9). |
| R1-13 | MISSING | (0, 12] not expressible in the loader vocabulary; SC-003 0.55 unsourced and not independent of SC-001. | FR-003 adds one half-open range kind; SC-003 rewritten to go through `load_template` and the shipped files, 0.55 dropped. |
| R1-14 | MISSING | SC-006 infeasible (max_population 500, few births at 40-49). | SC-006 specifies a no-LLM test world, 2,000 founders, monthly ticks, 360 ticks, a test copy of the template with max_population 10^6; groups under 30 births reported, not judged. |
| R1-15 | VERIFIED | All numbers recomputed independently (list in the reviewer report). | none |
| R1-16 | VERIFIED | Citations (IUSSP, Rodriguez, Woods, Coale-Trussell via snippet) and code claims (`hadwiger` read only at `fertility.py:310`; flag at `fertility.py:298`, `orchestrator.py:364`; loader requires the flag). | none |

**Verdict round 1: NOT CONVERGED** (0 INCORRECT, 5 UNJUSTIFIED, 5 INCONSISTENT, 4 MISSING). Fixes applied in the same pass; round 2 re-audits.

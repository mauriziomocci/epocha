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

**Current verdict: NOT CONVERGED after round 2; round 3 pending.**

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

## Round 2 (2026-10-29, 19:35-19:46, independent `critical-analyzer`)

R1 statuses per the reviewer: R1-02 to R1-13 RESOLVED (R1-04 numbers only),
R1-01 and R1-14 PARTIAL. Verified on this pass: the SC-005 widowhood bound
(married indicator never above ever-married indicator, so the expected harness
NRR is at most 1.916), Becker thresholds (340^0.1 = 1.791, e^8.986 = 7,990),
the loader having only `UNIT` and `POSITIVE`, H = 4 "industrial transition" at
whitepaper EN line 826, template e0 = 70.7.

| # | Class | Finding (evidence) | Resolution |
|---|---|---|---|
| R2-01 | MISSING | SC-006 B outcome depends on the world: `compute_subsistence_threshold` returns 0 without a `ZoneEconomy`, so `becker_modulation` divides by 1e-6 and every agent above ~0.06 wealth gets factor 3.0. | SC-006 B world initialized through `economy.initialization.initialize_economy`, economy step running every tick; result declared valid only for that configuration and tick length; the zero-subsistence behaviour written into (N4) and D-MF-09. |
| R2-02 | INCORRECT | Realized level is 5*M*sum_g n_g*E[m_BK given g], not M*E[m_BK] over all exposure (factor depends on age; exposure outside 20-49 has zero weight). | New quantity rho_BK = realized TMFR_20-49 / T_m, the n-weighted mean of group means, defined under (N1a); SC-006 B, D-MF-09, limitations, S5 and FAQ use it; the gate is abs(rho_BK - 1) > 0.10. |
| R2-03 | INCONSISTENT | The SC-006 B error blocked nothing; 4.306 written into Table 7.2 unqualified. | The error blocks phase-6 closure until the user explicitly authorizes one of the two D-MF-09 paths; FR-006 labels 4.306 "at Becker factor 1, no mortality, no widowhood". |
| R2-04 | INCONSISTENT | Two rules for the two no-data eras; 6.2 is position B applied offline. | D-MF-05 states one ordered rule: (i) inherit the level of the era whose fertility block the whitepaper declares identical (islamic, 6.7); (ii) otherwise keep the declared TFR, i.e. position B offline (industrial), inheriting all K5 defects, accepted with the reason written. Industrial set to the exact B value 6.22 (TFR0 3.997/3.976, NRR 1.868/1.858, rates 0.318/0.273/0.115, recomputed); WARNING and table updated. |
| R2-05 | INCORRECT | SC-003 said (4.2) fails at 20 with 2.491; the code would compute f_H(20) = 0.241 (grid max 0.398). | SC-003 rewritten with the two real failure modes (0.241 against 0.343; 0.398 above the maximum). |
| R2-06 | INCONSISTENT | Stale `_annual_base_rate`; stale 2.37. | Both replaced (`annual_base_rate`, 2.491). |
| R2-07 | INCONSISTENT | 3.9845 rounds to 3.985. | Moot: industrial value now 6.22, TFR0 3.997 recomputed. |
| R2-08 | INCONSISTENT | p > 1 already for dt > 0.973 with factor 3. | Rinvio 2: factor above 2.92 and dt above 0.973 years. |
| R2-09 | MISSING | 8.995 must sum only the six 20-49 groups. | FR-001 states it; the 15-19 extension is a separate rule (otherwise 11.295). |
| R2-10 | INCONSISTENT | For `true` the loader raises a type error before the range check. | US3 scenario 3 expects the type error for `true`, the interval for the numbers. |
| R2-11 | MISSING | §11 bullet "Hadwiger ASFR is evaluated deterministically" not named. | Named in FR-006. |

**Verdict round 2: NOT CONVERGED** (2 INCORRECT, 0 UNJUSTIFIED, 6 INCONSISTENT, 3 MISSING). Fixes applied in the same pass; round 3 re-audits.

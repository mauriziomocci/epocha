# Adversarial scientific audit: rule-based couples spec

Work item: `20261029-123404-rule-based-couples`. Spec: `../spec.md`.

The `critical-analyzer` subagent could not be dispatched from this session, so
each round is run by the spec author as an explicit, separate hostile pass:
the reviewer re-reads the spec against the code of the Plan 4 branch
(`20260826-144432-demography-plan4-wiring`, commit `164da55`) and against the
sources, and is not allowed to accept a claim the spec makes about itself.
This is weaker than an independent reviewer, and it is stated so that the
Trinity gate can decide whether a dispatched audit is still required before
approval.

Categories: INCORRECT, UNJUSTIFIED, INCONSISTENT, MISSING, VERIFIED.

## Round 1 (2026-10-29, 12:44)

| # | Class | Finding (evidence) | Resolution |
|---|---|---|---|
| R1-01 | INCORRECT | FR-017 put an integer id in `target`. `agents/factions.py:598-601` (`update_group_cohesion`) does `target.lower()` on every decision's `target`: an integer raises `AttributeError` and stops the faction step. The dict form of `for_child`, accepted by the resolver today, already crashes the same line: a pre-existing latent defect. `dashboard/formatters.py:56-63` would print "formed a couple with 41". | `target` stays the display name; new keys `target_id` and `for_child_id` carry the ids (FR-017, FR-021). New FR-022: `update_group_cohesion` ignores a non-string `target`, with a red test on the dict form first. Doc-sync of §4.7 added to FR-018. |
| R1-02 | INCORRECT | The spec gave N = 2730 and N = 2152 for the Newton table. The `pdftotext` extraction of that slide is ambiguous (the N rows interleave with medians and the female/male labels), so the pairing of N to sex is not established. | N values removed; only the two means, which sit in unambiguous "mean" rows, are kept. |
| R1-03 | UNJUSTIFIED | The spec called Newton's "National" column a secondary of Wrigley et al. (1997). The slide does not say where "National" comes from; the only reference to Wrigley appears in a footnote of a different table (prenuptial pregnancy). | Attribution rewritten as an inference to be checked in the validation work item; the value stays a "secondary, provenance not stated on the slide" figure. |
| R1-04 | UNJUSTIFIED | The chapter title "Remarriage intervals and the effect of marriage order on fertility" and the volume for Schofield and Wrigley (1981) came from memory, not from any page read. | Title and volume removed; the claim is cited as read in a search result about the chapter "Marital dissolution and remarriage" of *Demographic Behavior in the Past* (Cambridge), primary unverified. |
| R1-05 | UNJUSTIFIED | SOCSIM authorship "Hammel, Wachter, Mason" asserted without a page read this session. | Marked as attribution not verified this session; only the repository host and the changelog content are stated. |
| R1-06 | MISSING | Walker and Davis (2013) is cited in "Alternative considerate" but not in the source table. | Added to the source table (JASSS 16(1) 6, page read). |
| R1-07 | INCONSISTENT | FR-004 said one relationship query "per mercato", so with `same_zone` the count grows with the number of zones, while FR-003 and SC-003 claim a constant count. | One relationship query per tick over all seekers and candidates of all markets. |
| R1-08 | MISSING | FR-014 needs the protagonist's living unmarried children to decide whether to offer `for_child`; the cost was not declared. | Declared: one query per protagonist with at least one child, so at most K per tick, independent of N. |
| R1-09 | MISSING | FR-018 omitted whitepaper §6.2, which the doc-sync table maps to `template_loader.py` and `templates/*.json`, both changed by FR-012 to FR-016. | §6.2 added to FR-018. |
| R1-10 | INCONSISTENT | User Story 1, scenario 2 was not testable ("at least one woman ... only if the run is long enough"). | Rewritten with measurable outcomes: couples formed after initialization > 0, births > 0, zero decision calls. |
| R1-11 | MISSING | The realized male age at first marriage is declared uncalibrated (S1) but no criterion measures it. | SC-007 also reports the realized male mean age, against Newton's 27,1 as a reference, with no threshold. |
| R1-12 | MISSING | The mourning conversion from days to ticks was not written down. | FR-006 states it: `ticks = days · 24 / (tick_duration_hours · acceleration)`, the inverse of Δt. |
| R1-13 | MISSING | The couple type of a rule-market couple was not stated. | FR-003: `couple_cfg["default_type"]`, as the intent resolver does. |
| R1-14 | MISSING | SC-005 measures "the pure market function" at 10^5 agents, but FR-003 defined only a DB-bound function. | FR-003 separates a pure core (eligibility draws and `stable_matching` on in-memory lists) from the DB read and write; SC-005 measures the core. |
| R1-15 | MISSING | The build map rule (trigger 5, work item opened) has no requirement in the spec. | FR-018 states that the build map records the work item at its opening and at every checkpoint, by the session that owns the map, published to the same URL. |
| R1-16 | VERIFIED | (R1a): the regularized upper incomplete gamma Q(α/β, exp(−β(z−μ))) equals the numerical integral of (R1) at z = −1,5, −1, 0, 1, 2,5 to six decimals (pure-Python series, 2026-10-29). | — |
| R1-17 | VERIFIED | Standardized form: integral 1,000000, mean 0,0001, variance 1,0008; constant 1,2808 against Kaneko's 1,2813 (rounding of α, β). Truncation below 14 years < 10^-4 for u = 25,5, b = 5,5. | — |
| R1-18 | VERIFIED | Code claims: `run_couple_formation_step` calls only `resolve_pair_bond_intents`; `rng` is received and unused by the resolver; `form_initial_couples` pairs all eligible adults with no RNG and carries the quoted comment; `homogamy_score` runs one `Relationship` query per call and `stable_matching` calls the score 2·S·M times; three templates of five set `require_couple_for_birth = true`; zones are 100-unit squares 120 apart in `world/generator.py`; the prompt never describes `for_child`. | — |
| R1-19 | VERIFIED | Licence of the reconstitution dataset: CC BY-NC-SA 4.0, read on the UK Data Service record. | — |

**Verdict round 1: NOT CONVERGED** (2 INCORRECT, 3 UNJUSTIFIED, 2 INCONSISTENT, 8 MISSING). Fixes applied to the spec in the same pass; round 2 re-audits.

## Round 2 (2026-10-29)

Re-audit of the R1 resolutions, then a fresh hostile pass over the whole spec.

**R1 findings re-checked**: R1-01 to R1-15 RESOLVED. R1-01 checked against the
code once more: with `target` kept a string, `update_group_cohesion`,
`format_decision_text` and the two `factions.py` readers see the same types as
today; the dict form remains a pre-existing hazard, now FR-022 with a red test
(SC-014).

| # | Class | Finding (evidence) | Resolution |
|---|---|---|---|
| R2-01 | INCORRECT | The "Modello dati" header said "three new keys, two removed". Only `allowed_types` is removed; the new keys are `first_marriage` (three sub-keys) and `remarriage_annual_rate_female`; `mourning_ticks` is renamed; `adjacent_zones` is a removed value. The "Parametri per era" lead had the same count error. | Both sentences rewritten with the exact list. |
| R2-02 | UNJUSTIFIED | The Islamic-era heuristics leaned on Hajnal as if his contrast described a pre-industrial Islamic era; Hajnal's non-European figures are Asian and African data of the twentieth century (secondary). | Parentheticals rewritten to say exactly what the secondary source covers and that it does not concern an Islamic era. |
| R2-03 | INCORRECT | "(R2) describes a cohort in the absence of mortality" was presented as a property of the source. Kaneko (2003) defines f(x) as the density of marrying at exact age x for all cohort members, with a note not read. | Reworded as the single-decrement interpretation adopted by the spec, stated as an assumption next to independence. |
| R2-04 | MISSING | `template_loader.py` rejects unknown and missing keys (lines 286-297) and validates enumerated values only where coded (`ALLOWED_FERTILITY_AGENCY`). The spec did not require value validation for `marriage_market_radius` and `marriage_market_type`, so `adjacent_zones` would still load. | FR-013 and FR-014 require validation against `{same_zone, world}` and `{autonomous, arranged}`. The edge case "template without the new keys is rejected" is now backed by lines 286-297. |
| R2-05 | MISSING | `Agent.zone` is nullable (`agents/models.py:90-96`); the `same_zone` partition did not say what happens to agents without a zone. | Partition on `zone_id` with the null zone as an ordinary key, no special case; declared as a limit (edge case, FR-007). |
| R2-06 | MISSING | FR-005 changes `form_initial_couples` from universal to age-graded pairing; the existing tests in `test_initialization.py` assert the old behaviour. | FR-005 requires adapting, not deleting, those tests. |
| R2-07 | VERIFIED | SC-002 tolerances: standard error of the mean b/√(nC) = 5,5/√17600 ≈ 0,041 years; of the proportion √(0,88·0,12/20000) ≈ 0,0023; the bands (0,15 years, 0,01) are about 3,6 and 4,3 standard errors, with margin for weekly discretization (at most half a tick, ≈ 0,01 years). | — |
| R2-08 | VERIFIED | SC-004: in `stable_matching` every respondent accepts any first proposal (`engagements.get(r) is None`), so with M ≥ S every seeker is matched and with M < S exactly M couples form; no respondent is held twice. | — |
| R2-09 | VERIFIED | `rng.ALLOWED_PHASES` contains `couple` and `initialization`; no new phase name is introduced. | — |
| R2-10 | VERIFIED | `Agent.zone`, `Group.leader` and `Government.head_of_state` are nullable FKs; `Government` is one-to-one with `Simulation`; the priority query of FR-008 can be one SQL statement with an `Exists` on `Group.leader` and a comparison with the head-of-state id. | — |

**Verdict round 2: NOT CONVERGED** (2 INCORRECT, 1 UNJUSTIFIED, 3 MISSING). Fixes applied; round 3 re-audits.

## Round 3 (2026-10-29)

**R2 findings re-checked**: R2-01 to R2-06 RESOLVED (the two key-count
sentences now list the exact keys; the Hajnal parentheticals state the scope
of the secondary source; (R2) is an adopted interpretation; FR-013 and FR-014
require enum validation; FR-007 partitions on `zone_id`; FR-005 adapts the
initialization tests).

| # | Class | Finding (evidence) | Resolution |
|---|---|---|---|
| R3-01 | INCONSISTENT | SC-003 still said one `Relationship` query "per mercato" after FR-004 moved to one per tick (R1-07 fixed the requirement, not the criterion). | SC-003: one per tick, independent of S·M and of the number of zones. |
| R3-02 | INCORRECT | D-RBC-02 said K = 10 "halves" the tokens of K = 30; it divides them by three. | Corrected to "a un terzo". |
| R3-03 | UNJUSTIFIED | SC-008 compares the married share with the mean of F(x), which holds only if every drawn woman finds a man; the criterion did not fix the number of men. | SC-008 fixes 5000 eligible men for 4000 women. |
| R3-04 | MISSING | The coordinator's instruction requires both positions, the evidence and the five costs (tokens, time, quality, working behaviour, end-user satisfaction) for every provisional decision; D-RBC-03 to D-RBC-10 listed only some of the five. | Every decision now states the five costs. D-RBC-11 is not a provisional decision but a question reserved to the user, and says so. |
| R3-05 | VERIFIED | SC-001 numbers against the numerical check of round 1: constant 1,2808 within 10^-3 of 1,2813; mean 0,0001 within 10^-3; variance 1,0008 within 2·10^-3. | — |
| R3-06 | VERIFIED | FR-021 list of `output_decision` readers outside `couple.py`, by `grep -rn output_decision epocha/apps/` on `develop` 2223968: `economy/property_market.py:251,260`, `economy/engine.py:117`, `agents/factions.py:594,1194`, `dashboard/views.py:217,273` via `format_decision_text`; none reads keys other than `action`, `target`, `reason`. To be re-run on the Plan 4 tree in the phase-4 preflight. | — |
| R3-07 | VERIFIED | Cost statements: FR-003 four reads plus inserts, FR-004 one per tick, FR-006 one per tick, FR-008 one statement, FR-014 at most K; none grows with N. | — |

**Verdict round 3: NOT CONVERGED** (1 INCORRECT, 1 UNJUSTIFIED, 1 INCONSISTENT, 1 MISSING). Fixes applied; round 4 re-audits.

## Round 4 (2026-10-29)

**R3 findings re-checked**: R3-01 to R3-04 RESOLVED.

| # | Class | Finding (evidence) | Resolution |
|---|---|---|---|
| R4-01 | UNJUSTIFIED | "Perché questo work item esiste", point 4, stated the 25,5 years as a fact about England 1701-1750, while the only source read is a secondary slide whose "National" column has no stated provenance (R1-03 fixed the table, not this sentence). The FAQ still called Newton "secondaria di Wrigley et al. (1997)". | Both sentences now name the slide, its secondary status and the unverified provenance. |
| R4-02 | UNJUSTIFIED | The spec said "SOCSIM and rsocsim are GPL". Only `rsocsim` is GPL in the 2026-10-29 survey (memory `reference_related_work_2026_10_29.md`); the licence of the SOCSIM C code was not read. Same claim in two FAQ answers. | All three sites now say rsocsim GPL, SOCSIM licence unverified, idea only in any case. |
| R4-03 | MISSING | (R3) applies a cohort schedule as a period hazard; that is valid only under stationarity, which was not stated. | New assumption: stationary schedule within an era; within-run nuptiality change not modelled. |
| R4-04 | MISSING | The remarriage hazard is age-independent, so a 70-year-old widow draws like a 30-year-old; not stated. | New known limitation, as part of the heuristic to calibrate. |
| R4-05 | INCORRECT | The contract-change header named "PATCH/PUT/POST on /api/v1/simulations/" loosely. `SimulationViewSet` (`simulation/views.py:21-24`) writes through `SimulationSerializer`; the Express action (`views.py:33`) uses `SimulationCreateExpressSerializer`, which has only `prompt` and `file`. | Header names the three viewset writes and excludes Express explicitly. |
| R4-06 | VERIFIED | `template_loader.py` (Plan 4) rejects unknown keys (line 286-289) and missing mandatory ones (297): `mourning_ticks` and `allowed_types` in an old template are rejected once removed from `SCHEMA`, as SC-012 expects. | — |

**Verdict round 4: NOT CONVERGED** (1 INCORRECT, 2 UNJUSTIFIED, 2 MISSING). Fixes applied; round 5 re-audits.

## Round 5 (2026-10-29)

**R4 findings re-checked**: R4-01 to R4-05 RESOLVED.

| # | Class | Finding (evidence) | Resolution |
|---|---|---|---|
| R5-01 | INCORRECT | "Alternative considerate" attributed logistic-regression matching to DYNASIM; Walker and Davis (2013) attribute an exponential function of age and education differences to DYNASIM and APPSIM, and logistic regression to CBOLT, FAMSIM, SAGE and LIAM. | Rewritten per the source. |
| R5-02 | UNJUSTIFIED | A FAQ answer asserted that agent-based mate-search models produce the Coale-McNeil shape from individual rules; no such model was read this session. | Claim removed; the answer now says those models were not verified. |
| R5-03 | MISSING | D-RBC-04 did not cite the strongest evidence: the whitepaper's own pre-industrial validation criterion, TFR in [4,5; 6,5] after fitting H, R, T (§7.3, Table 7.2, `epocha-whitepaper.md:2399`), which the expected post-work-item value (about 2,4) misses. | Cited in D-RBC-04 and in the known limitation, whose estimate now states its assumptions (no mortality, widowhood, remarriage). |
| R5-04 | UNJUSTIFIED | Matthews (2012) and Coale and Trussell (1974) were named without their verification status. | Matthews: read only in a search result; Coale and Trussell: cited by whitepaper §4.1.2, not re-read. |
| R5-05 | VERIFIED | Wrigley and Schofield (1981) bibliographic data match the whitepaper bibliography (`epocha-whitepaper.md:3342-3344`, Edward Arnold, reissued by CUP 1989). | — |
| R5-06 | VERIFIED | Kaneko (2003) row: pages 223-228 are the eight PDF pages read (title page, contents, 223-228). | — |

**Verdict round 5: NOT CONVERGED** (1 INCORRECT, 2 UNJUSTIFIED, 1 MISSING). Fixes applied; round 6 re-audits.

## Round 6 (2026-10-29)

**R5 findings re-checked**: R5-01 to R5-04 RESOLVED; the TFR criterion is now cited as §7.3, Table 7.2, which applies after fitting H, R, T, and the spec says the expected value misses it without that fit.

| # | Class | Finding (evidence) | Resolution |
|---|---|---|---|
| R6-01 | INCORRECT | The FAQ said couples become "many more" after the change. At initialization they become fewer (only the women the schedule declares married, against universal pairing today, `initialization.py:263-264`); during the run many more. | FAQ states both phases. |
| R6-02 | MISSING | Reproducibility: `same_zone` markets are a partition; the spec fixed the draw order by id but not the order in which markets are visited, which a dict would leave to insertion order and the stream consumption would then depend on it. | FR-003: markets visited by `zone_id`, null zone first. |
| R6-03 | MISSING | Security FAQ did not treat a model-returned id as untrusted input (cross-simulation or dead targets). | FAQ and FR-017 state the same-simulation, alive, integer check. |
| R6-04 | INCONSISTENT | User Story 2, scenario 2 said "25 agents ... all deliberate, as today", but today minors are excluded (D-29-4); and User Story 3, scenario 3 still named the old `for_child` form only. | Scenario 2 counts agents the selection admits; scenario 3 names both the new and the legacy form. |
| R6-05 | VERIFIED | Every SC is tied to a requirement or a story, every FR has a stated cost, every provisional decision has two positions, evidence and five costs; the FAQ covers design decisions, scientific mapping, integration, performance, reproducibility, alternatives, operations and security as CLAUDE.md requires. | — |

**Verdict round 6: NOT CONVERGED** (1 INCORRECT, 1 INCONSISTENT, 2 MISSING). Fixes applied; round 7 re-audits.

## Round 7 (2026-10-29)

**R6 findings re-checked**: R6-01 to R6-04 RESOLVED.

| # | Class | Finding (evidence) | Resolution |
|---|---|---|---|
| R7-01 | INCORRECT | The market's compute cost was stated as O(S·M). `stable_matching` (`couple.py:165-174`) sorts the M respondents for each of the S proposers, so the cost is O(S·M·log M), with 2·S·M score evaluations; the cost summary's "10^5 operations" for M ≈ 10^4 and a few seekers omitted the log factor. | Three sites corrected to O(S·M·log M); summary restated as 10^5-10^6 operations for about ten seekers. SC-005 still measures it. |
| R7-02 | MISSING | FR-020 "integer ≥ 0" would accept `true`, because `bool` is a subclass of `int` in Python. | FR-020 and FR-011 exclude booleans explicitly. |
| R7-03 | VERIFIED | "No other path creates a `Couple` after initialization": `git grep "form_couple(\|Couple.objects.create"` on the Plan 4 branch outside tests finds only `couple.py:216` (inside `form_couple`), `couple.py:468` (intent resolver) and `initialization.py:264`. | — |
| R7-04 | VERIFIED | `update_group_cohesion` is the function containing `factions.py:594-601` (definition at `factions.py:536`); the `target.lower()` claim of FR-022 holds on `develop` 2223968. | — |

**Verdict round 7: NOT CONVERGED** (1 INCORRECT, 1 MISSING). Fixes applied; round 8 re-audits.

## Round 8 (2026-10-29)

**R7 findings re-checked**: R7-01 RESOLVED (three sites say O(S·M·log M), the
summary gives 10^5-10^6 operations); R7-02 RESOLVED (FR-011 and FR-020 exclude
booleans).

Fresh pass, limited to what the earlier rounds had not checked against a page:

| # | Class | Finding (evidence) | Resolution |
|---|---|---|---|
| R8-01 | VERIFIED | Rodríguez and Trussell (1980): title "Maximum Likelihood Estimation of the Parameters of Coale's Model Nuptiality Schedule from Survey Data", World Fertility Survey, Technical Bulletins, No. 7, as listed in Kaneko (2003, p. 260). Coale (1971) and Coale and McNeil (1972) bibliographic data match the same list (p. 259). | Spec rows now cite the bibliography pages. |
| R8-02 | VERIFIED | Every number in the spec traced to a computation or a page: 25,5 / 27,1 (Newton slide); α, β, μ, 1,2813 (Kaneko eq. 2); 1,2808, mean, variance, truncation < 10^-4, Q identity (round-1 numerical checks); TFR 2,29-2,47 (computation of 2026-10-29, inputs stated); 10.950 and 36.500 calls; 4000 queries (2·5·400); SC tolerances (round 2); TFR [4,5; 6,5] (§7.3, Table 7.2). | — |
| R8-03 | VERIFIED | Every non-sourced parameter is labelled "euristica regolabile" in the parameter table, and the spec forbids presenting it as calibrated. The only unresolved question, D-RBC-11, is reserved to the user and does not block the design. | — |

No INCORRECT, UNJUSTIFIED, INCONSISTENT or MISSING finding is open.

**Verdict round 8: CONVERGED.**

Limit of this verdict: the eight rounds were run by the author of the spec as
separate hostile passes. The brief assumed no agent dispatch was available; it
was, so round 9 below is an independent `critical-analyzer` dispatch, run
precisely because a self-audit cannot remove confirmation bias. It reopened the
verdict, which is the evidence that it was needed.

## Round 9 (2026-10-29, independent `critical-analyzer`, Opus)

The auditor was briefed with the spec, the Plan 4 branch (read-only, head
`a6b64d4`) and the sources, and told not to read this file before writing its
findings. Each finding below was re-checked by the author before being
accepted (mutual skepticism): 1 against `engine.py:148-160` on the Plan 4 head;
2 and 3 by an independent pure-Python quadrature (mean on [14, 50] = 25,421,
F(50) = 0,8776; islamic F(14) = 0,0406, C* = 0,9687, mean 19,244); 11 by
`git grep mourning_ticks` on the Plan 4 whitepaper (lines 2731, 3563, 3786).

| # | Class | Finding (evidence) | Resolution |
|---|---|---|---|
| R9-01 | INCORRECT | FR-017 and FR-021 missed a third reader of `target`: `simulation/engine.py:148-160` `apply_agent_action`, on both paths, resolves the relationship and reputation target by `name__icontains` and `.first()`; in User Story 4 the couple would form with agent 41 while the relationship update went to the lowest-id substring match. | FR-017 makes `apply_agent_action` use a valid `target_id`, falling back to the name; FR-021 and User Story 4 updated. |
| R9-02 | INCORRECT | SC-002's target ignored the upper truncation: a cohort observed to 50 has mean 25,42 and F(50) = 0,8776, not 25,5 and 0,88; the 0,08 gap is about two standard errors, so the test was fragile in the wrong direction. | SC-002 and User Story 1 target the [m, 50] values, computed in the test; a mutation with the untruncated mean must fail. |
| R9-03 | INCONSISTENT | Runtime and initialization realised different schedules: runtime women reach the minimum age unmarried, so the hazard realises F*(x) = (F(x) − F(m))/(1 − F(m)); initialization used F(x). Negligible for christian, 0,0406 for islamic. | New (R4); FR-005 and the initialization section use F*; the realised C* and mean are stated per era and go into the whitepaper. |
| R9-04 | UNJUSTIFIED | FR-005 had no compute or memory bound: initialization runs `stable_matching` on S ≈ Σ F*(x) women against all eligible men, about 10^9 score calls for 10^5 founders in one market; SC-008 as written needed about 4·10^7 calls. | FR-005 states the bound and the per-zone reduction; SC-005 also measures initialization; SC-008 tests the Bernoulli draw as a pure function and the matching on a small fixture. |
| R9-05 | INCONSISTENT | FR-008 claimed at most K rows read, but if this work item lands before the life-course spec the minor exclusion is still `minor_agent_ids`, which reads every living agent in Python; dropping it would regress D-29-4. | FR-008 keeps the exclusion inside the function and declares O(N) rows in that case. |
| R9-06 | MISSING | Calendar fidelity under the default K = 30 was unquantified: in small worlds every agent has the intent channel, which with `implicit_mutual_consent = true` needs one side only and bypasses hazard and radius. | Known limitation: the calibrated calendar holds only at K = 0 and approximately for K ≪ N; SC-007 reports the share of couples formed by intents. |
| R9-07 | MISSING | SC-007 was statistically empty (about 16 births in the 3-year run) and confounded by Becker and the Malthusian ceiling (`max_population` 500), absent from the 2,29-2,47 integral. | SC-007 measures M(a), the male mean age and ∫ f_H M on a 20.000-woman synthetic population through the pure market core, with HP mortality, widowhood and remarriage, Becker and ceiling excluded by construction, each with a 95% interval. |
| R9-08 | INCONSISTENT | SC-006 and User Story 1 required an LLM double that raises on every call never to be invoked, but `factions._check_schism` calls `_generate_faction_identity`, an in-tick LLM call independent of decisions. | The double is scoped to the decision client; faction identity has its own non-raising double and is declared outside the K cap. |
| R9-09 | INCONSISTENT | FR-009 said no generated world changes; the generator only asks for 10-30 agents, creates every agent returned, and the knowledge-graph path has no cap. | Reworded: no guarantee; a world with more than 30 founders has only the first 30 deliberating. |
| R9-10 | INCORRECT | Deferral 7 said the `age` column lags "at most one tick"; it is floored to completed years, so it can differ by up to one year. | Deferral removed: FR-004 makes the homogamy age term use the canonical age the market already computes. |
| R9-11 | MISSING | FR-018 omitted whitepaper §11 and Appendices A and C, which name `mourning_ticks`. | Added to FR-018. |
| R9-12 | INCONSISTENT | Governance: the global rules forbid deciding a contract or data-model change in the user's absence, and a permission relayed by the coordinator is not the user's own permission in chat. | D-RBC-09 and the template-schema decisions (D-RBC-03, 05, 06, 07) are marked as proposals awaiting the user's confirmation before phase 5, in the header and in the decisions section. |
| R9-13 | UNVERIFIED | Schofield-Wrigley remarriage figure: refers to the sixteenth and nineteenth centuries, and the quantity (share of marriages that are remarriages vs share of widowed persons who remarry) is ambiguous. | Deferral 4 requires defining the calibration quantity and period first; the spec already uses the figure only as a future target. |
| R9-14 to R9-17 | VERIFIED | Kaneko eqs (1)-(4) and constants on the primary PDF; integral, mean, variance, constant 1,28082, the α↔β mutation (1,2708) fails as intended, (R1a) to 1e-15; SC-007's 2,290-2,470 reproduced; Coale-McNeil abstract; eleven code claims (formation step, `form_couple` sites, templates, initialization, query counts, unused streams, loader, zone geometry, `output_decision` readers, empty chord, Express serializer). | — |

**Verdict round 9: NOT CONVERGED** (3 INCORRECT, 1 UNJUSTIFIED, 5 INCONSISTENT, 3 MISSING, 1 UNVERIFIED). Fixes applied; round 10 re-audits.

## Round 10 (2026-10-29, independent `critical-analyzer`, re-audit)

Round-9 findings: 12 RESOLVED (R9-01 to R9-06, R9-08 to R9-13, each checked by
the auditor against the current line of the spec), R9-07 partly resolved and
carried into R10-03. New findings introduced by the fixes, re-checked by the
author before acceptance (the Φ(0,69) ≈ 0,75 survival probability of the SC-002
mutant follows from (25,45 − 25,421)/0,042):

| # | Class | Finding (evidence) | Resolution |
|---|---|---|---|
| R10-01 | INCORRECT | SC-002 could not detect the upper-truncation effect it named: the gap 25,5 − 25,421 = 0,08 years is inside the 0,15 tolerance, and the stated mutant (target 25,5, tolerance 0,05) survives on about one seed in four. | SC-002 split: a deterministic propagation of the never-married fraction with p(x), no random draws, against the integral within 0,02 years and 0,002 (discretisation only; the mutant now fails with certainty, the gap being four times the tolerance), plus the Monte Carlo scenario at 3 standard errors (0,13 years, 0,007). User Story 1 aligned. |
| R10-02 | UNJUSTIFIED | SC-005 timed the founding matching at 10^5 agents in one market, which FR-005 itself puts at about 10^9 evaluations and a dictionary of about 10^9 entries. | Measured at 10^3 and 10^4, extrapolated to 10^5 with the measured exponent, declared as an extrapolation. |
| R10-03 | MISSING | SC-007 was a mini-simulator with no stated horizon, cohort-or-period choice, interval method or radius. | SC-007 is a phase-6 measurement script outside the suite: one synthetic cohort of 20.000 women aged 12 to 50 at monthly ticks, radius `world`, a candidate pool of 500 never-married men redrawn each tick from the template pyramid (the female-dominance assumption made explicit), HP mortality for both sexes, mourning and r_f; M(a) is a cohort measure, so no stationarity is assumed; 95% t-interval over 20 seeds; cost about 2·10^7 evaluations per replicate (author's own estimate: about 18.000 marriages × 500 × 2), corrected from the auditor's per-tick estimate. |
| R10-04 | MISSING | FR-004 changed the age term and the signature of `homogamy_score` without naming the parameters, and FR-018 did not list the text of equation (4.6). | FR-004 names the signature `homogamy_score(a, b, weights, *, sentiments, ages, age_tolerance_years=10.0)`; FR-018 rewrites the (4.6) text. |

**Verdict round 10: NOT CONVERGED** (1 INCORRECT, 1 UNJUSTIFIED, 2 MISSING). Fixes applied; round 11 re-audits.

## Round 11 (2026-10-29, independent `critical-analyzer`, re-audit)

Round-10 findings R10-01 to R10-04 RESOLVED (checked by the auditor against
SC-002, SC-005, SC-007, FR-004 and FR-018). The auditor confirmed the author's
correction of the SC-007 cost (seekers summed over ticks equal total marriages,
about 1,8·10^7 evaluations per replicate, times a log M ≈ 9 sorting factor).

| # | Class | Finding (evidence) | Resolution |
|---|---|---|---|
| R11-01 | INCORRECT | SC-007 used a "female" Heligman-Pollard schedule for women and a "male" one for husbands; every template has a single `mortality.heligman_pollard` block and `mortality.py` has no sex term (author's own `grep` confirms both). | SC-007 applies the template's single schedule to both sexes and declares it a limit inherited from the mortality model. |
| R11-02 | INCONSISTENT | SC-007 compared the male mean age at first marriage with Newton's 27,1, but in the harness that number is fixed by the candidate pool, redrawn each tick from the whole pyramid, and men are not followed between ticks. | Male age removed from the harness; measured in the User Story 1 integration run, where men are simulated, and reported as indicative with its number of marriages. |

**Verdict round 11: NOT CONVERGED** (1 INCORRECT, 1 INCONSISTENT). Fixes applied; round 12 re-audits.

## Round 12 (2026-10-29, independent `critical-analyzer`, re-audit and final sweep)

R11-01 and R11-02 RESOLVED (SC-007 uses the single `mortality.heligman_pollard`
schedule for both sexes, declared as a limit; male age moved to the User Story 1
run). Final sweep against the Plan 4 code, VERIFIED: the FR-022 `AttributeError`
(`factions.py:598-603`, a non-empty dict is truthy and has no `.lower()`); the
smaller side is fully matched because every preference list is complete
(`couple.py:163-190`); the D-RBC-02 arithmetic; the 3-SE tolerances; the
FR-002 and FR-006 conversions against `HOURS_PER_YEAR` and `age_in_years`.

Three secondary residuals, applied although none changes a conclusion:

| # | Class | Finding | Resolution |
|---|---|---|---|
| R12-01 | MISSING (secondary) | The Coale-McNeil DOI 10.1080/01621459.1972.10481287 is unverified; a search returns the JSTOR DOI 10.2307/2284631. | Both listed with their provenance; neither opened. |
| R12-02 | MISSING (secondary) | FR-006 did not fix the rounding of `mourning_days` into ticks (365 days = 52,14 weekly ticks). | `ceil`, so mourning is never shorter than declared. |
| R12-03 | INCORRECT (secondary) | FR-013 said no geometric adjacency predicate is ever true; that holds for `touches`, while a distance predicate (gap 20 units) would be true. | Narrowed to `touches`; a distance predicate would need an unsourced threshold. |

No INCORRECT or UNJUSTIFIED finding of substance is open.

**Verdict round 12: CONVERGED.**

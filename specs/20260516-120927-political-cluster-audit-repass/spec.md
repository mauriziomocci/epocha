# Feature Specification: Political Cluster Audit Re-pass (Round 2)

**Feature Branch**: `20260516-120927-political-cluster-audit-repass`

**Created**: 2026-05-16

**Status**: Draft (post Round 1 audit, pre Round 2 verification + fixes)

**Input**: User description: "Round 2 adversarial audit re-pass for the political institutions cluster (government, government_types, stratification, election, institutions) — close 20 Round 1 findings from the 2026-04-12 audit and promote modules from whitepaper §8.1 to a new §4.5."

## Context

This feature is **Branch 3 of 6** in the F-CAMPAIGN audit re-pass batch documented in `docs/superpowers/plans/2026-05-12-audit-repass-campaign.md` (legacy plan, archival). The political cluster comprises five scientific modules under `epocha/apps/world/`: `government.py`, `government_types.py`, `stratification.py`, `election.py`, `institutions.py`. The original Round 1 adversarial audit (2026-04-12, transcript in `docs/scientific-audit-2026-04-12.md`) identified 20 outstanding findings spread across these modules.

Branch 1 (Reputation cluster, merged via PR#5) and Branch 2 (Rumor cluster, merged via PR#6 with promotion to §4.4) preceded this work. As a side effect, two Round 1 cross-module findings catalogued under the political batch are already CLOSED by prior branches:

- **Reputation normalization scattered** — closed by Branch 1 via the `reputation._normalize_reputation()` helper (commit `f1c4423` family).
- **`_memory_influence_score` dead-code keyword divergence** — closed by Branch 1 (the dead code was deleted in commit `f1c4423`), independently verifiable in current `election.py` (no symbol present).

Sequentially, the remaining work covers the 20 findings explicitly catalogued for the political cluster (6 in `government.py`, 1 in `government_types.py`, 4 in `stratification.py`, 5 in `election.py`, 3 in `institutions.py`, 1 cross-module corruption-layering). A spot-check of the current code on develop @ `1c75854` indicates several Round 1 findings have already been partially or fully remediated by interim commits since 2026-04-12 (G-2 coup already stochastic, E-2 dead code already removed, E-5 voter-count caching already applied, X-1 layering already documented in code comments). Round 2 verification confirms or closes each finding explicitly before promotion.

This spec is constitutional-compliant per `.specify/memory/constitution.md` v1.0.0: Principles I (Scientific Method), II (Verify Before Asserting), III (Adversarial Audit), V (Evidence-Based Verification).

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Close 5 INCORRECT findings to unblock whitepaper promotion (Priority: P1)

The Round 1 audit identified five INCORRECT findings on the political cluster that BLOCK the §8.1 → §4.5 whitepaper promotion until each is either resolved with a behavioral or substantive documentation fix, OR explicitly verified as already-closed by an interim commit. The five items are: coup formula citation overstates Powell-Thyne (G-1), coup decision was deterministic (G-2, *pre-verified* on develop — appears stochastic now, requires explicit confirmation), class-threshold attribution to Gilbert 2011 (S-1), corruption skim creates free wealth (S-2), election charisma cited to Zonis-Joseph 1994 (E-1). E-2 (dead `_memory_influence_score`) is recorded as ALREADY CLOSED by Branch 1 — the spec acknowledges it here so Round 2 audit verifies the absence.

**Why this priority**: per the audit verdict, the whitepaper §4.5 promotion (the deliverable that closes this branch) requires all INCORRECT findings resolved or independently verified as already closed. Convergence on all five items is the gating condition.

**Independent Test**: dispatch Round 2 critical-analyzer audit limited to the 5 INCORRECT findings (+ explicit confirmation of E-2 status); verdict must be CONVERGED for each.

**Acceptance Scenarios**:

1. **Given** the coup success formula in `government.py:check_coups`, **When** auditing its docstring and inline citations, **Then** Powell & Thyne (2011) is cited only as the empirical-dataset source for the ~50% base-rate calibration, NOT as the source of the multi-term weighted formula (which is documented as a simulation design parameter inspired by the coup literature).

2. **Given** the coup execution branch (`government.py:check_coups` around line 587), **When** the success probability is computed, **Then** the success/failure draw uses `random.random() < success_probability` (currently confirmed present; threshold-comparison `_COUP_SUCCESS_THRESHOLD` is no longer used and either marked deprecated or removed).

3. **Given** the 5-class stratification in `stratification.py`, **When** auditing its docstring and the class-boundary comments, **Then** Gilbert (2011) is cited as inspiration with an explicit acknowledgement that the implementation simplifies the original 6-class model into 5 classes with adjusted percentile thresholds.

4. **Given** the corruption mechanism in `stratification.py:process_corruption`, **When** an eligible agent skims `skim_amount`, **Then** `world.global_wealth` is reduced by exactly the same amount in the same transaction (wealth conservation invariant — no money creation).

5. **Given** the charisma component of the vote in `election.py`, **When** auditing its docstring and inline citations, **Then** the cited reference is one of Weber (1922) on charismatic authority, Bass (1985) on transformational leadership, or Merolla & Zechmeister (2011) on charisma in elections — and explicitly NOT Zonis & Joseph (1994) which addresses conspiracy thinking and is off-topic.

6. **Given** the election module on develop, **When** searching for the symbol `_memory_influence_score`, **Then** zero matches are found (the dead code was deleted by Branch 1; Round 2 confirms the absence).

---

### User Story 2 — Close 2 INCONSISTENT findings (Priority: P1)

The Round 1 audit identified two INCONSISTENT findings: a query-side N+1 in election manipulation (E-5), and the two-place corruption update on the same field (X-1).

**Why this priority**: same as P1 — whitepaper §4.5 promotion blocked until INCONSISTENT findings are resolved or documented. Per Constitution Principle III convergence loop.

**Independent Test**: dispatch Round 2 critical-analyzer audit on the resolved files; verdict CONVERGED.

**Acceptance Scenarios**:

1. **Given** the election manipulation bonus loop in `election.py`, **When** iterating over voters to apply the manipulation bonus, **Then** the voter count is captured once via `voters.count()` (or equivalent O(1) cached value) and reused inside the loop — no `len(list(voters))` re-evaluation per iteration. Current code is spot-confirmed already free of `len(list(voters))`; Round 2 verifies and records the resolution.

2. **Given** the corruption index update happens in two places (`stratification.py:process_corruption` at step 3 and `government.py:update_government_indicators` at step 4 of the political-tick pipeline), **When** auditing the data-flow, **Then** the layering is either unified into a single update path OR documented explicitly as deliberate co-existence with stated semantics ("step 3 models personality-driven petty corruption by head-of-state, step 4 models institutional-oversight-driven systemic corruption pressure; the two mechanisms compose additively within `_clamp`-bounded range"). The current code carries an inline `Note` comment around `government.py:339-342`; Round 2 audit verifies the documentation is sufficient or escalates a unification fix.

---

### User Story 3 — Close 12 UNJUSTIFIED + 1 MISSING findings (Priority: P2)

The Round 1 audit identified twelve UNJUSTIFIED findings requiring documentation upgrades, citation corrections, or alternative-citation substitutions, plus one MISSING (G-6: naming confusion between `World.stability_index` and the `economy` input variable in `_update_stability` and `update_government_indicators`). None blocks whitepaper promotion individually, but all are required for the cluster to meet Constitution Principle I ("No parameter without a justified value").

**Why this priority**: P2 because individually non-blocking but collectively required for CONVERGED verdict. Grouped fix in 2-3 commits.

**Independent Test**: dispatch Round 2 audit on the resolved files; verdict CONVERGED.

**Acceptance Scenarios**:

1. **Given** the institutional-trust decay constant `0.05` per tick in `government.py`, **When** auditing its origin, **Then** either a specific Freedom House report is cited with tick-to-year mapping OR the value is documented as a tunable design parameter inspired by Freedom House annual repression-trend data (G-3).

2. **Given** the government-type transition condition thresholds in `government_types.py`, **When** auditing their citations, **Then** the "Polity IV Table 3" attribution is removed and the thresholds are documented as design parameters inspired by Acemoglu-Robinson 2006 and Geddes 1999 patterns (G-4).

3. **Given** the legitimacy weights (health 0.20, education 0.15, economy 0.35, media 0.30) in `government.py`, **When** auditing their origin, **Then** either a specific paper is cited OR they are documented as tunable design parameters (G-5).

4. **Given** the `_update_stability` and `update_government_indicators` functions in `government.py`, **When** computing the "economy" input from `World.stability_index`, **Then** the naming mismatch is resolved either by renaming the local variable to `mood_proxy` (since `stability_index` is computed as average agent mood by the economy module) OR by routing the function through a dedicated economic indicator if one becomes available. Current code carries inline `Note` comments around lines 296-300 and 675-677; Round 2 verifies sufficiency (G-6).

5. **Given** the `government_types.py` parameter dictionaries (`repression_tendency`, `corruption_resistance`, `institution_effects`, `stability_weights`), **When** auditing their origin, **Then** a module-level disclaimer documents all values as design parameters inspired by the cited literature (Polity IV, Freedom House, Acemoglu-Robinson, Bueno de Mesquita). Current file already carries a module-level disclaimer (lines 25-26); Round 2 verifies it covers all four dictionaries explicitly (GT-1).

6. **Given** the corruption-susceptibility threshold `conscientiousness < 0.4` in `stratification.py:process_corruption`, **When** auditing its citation, **Then** Acemoglu-Robinson 2006 is removed as the source of the threshold (A-R discusses institutional constraints, not personality cutoffs) and the value is documented as a tunable design parameter with optional reference to Miller-Lynam (2001) for the personality-deviance link (S-3). Current code already cites Miller-Lynam 2001 in the inline comment (lines 207-212); Round 2 verifies the docstring at function level mirrors the same attribution.

7. **Given** the upward/downward mobility weights `0.4/0.7` in `stratification.py`, **When** auditing their relation to Kahneman-Tversky (1979), **Then** the docstring documents that the ~2:1 loss-aversion ratio is the principled anchor, and that the specific magnitudes (0.4 and 0.7) are tunable design choices preserving the ratio (S-4). Current code already carries the rationale (lines 58-63); Round 2 verifies presence and clarity.

8. **Given** the vote-component weights in `election.py` (relationship 0.25, personality 0.15, economic 0.20, reputation 0.25, charisma 0.15), **When** auditing their origin, **Then** they are documented as design parameters with a forward pointer to Lewis-Beck & Stegmaier (2000) suggesting the economic weight should be higher in future calibration (E-3).

9. **Given** the wealth-saturation cap `100.0` in `election.py`'s economic-vote computation, **When** auditing its derivation, **Then** the docstring states explicitly that the cap is anchored to the `Agent.wealth` default of 50.0 (twice the default) and removes the circular "median household wealth in pre-industrial simulations" justification (E-4).

10. **Given** the `INSTITUTION_EFFECT_SCALE = 20.0` constant in `institutions.py`, **When** auditing its derivation, **Then** the docstring documents the intended timescale mapping (1 tick ≈ 1 month → 33 ticks ≈ 2.75 years for near-peak institution recovery) explicitly (I-1).

11. **Given** the `FUNDING_EFFECT_RATE = 0.04` constant in `institutions.py`, **When** auditing its Gupta-et-al-2002 citation, **Then** the citation is removed (Gupta discusses public-spending-vs-poverty elasticity, not institution-health funding rate) and the value is documented as a tunable design parameter (I-2).

12. **Given** the `ENTROPY_PER_TICK = -0.005` constant in `institutions.py`, **When** auditing its Besley-Persson-2011 citation and the docstring claim of "half-life", **Then** either the implementation switches to exponential decay (multiply by ~0.993/tick for 100-tick half-life) consistent with the half-life concept, OR the docstring corrects the language to "linear decay reaching 50% after 100 ticks of zero investment" (I-3). Current code already carries a clarifying comment at line 57 ("linear decay, not exponential half-life"); Round 2 verifies sufficiency.

13. **Given** the absence of a single source of truth for the economy proxy used in stability and indicators, **When** running the test suite, **Then** at least one invariant test under `epocha/apps/world/tests/test_political_invariants.py` asserts the wealth-conservation contract from S-2 (corruption skim equals global-wealth decrement) and the naming clarity contract from G-6 (the variable named `economy` documents its proxy semantics).

---

### User Story 4 — Promote §8.1 → §4.5 in bilingual whitepaper after Round 2 CONVERGED (Priority: P1)

After the Round 2 re-audit verdict is CONVERGED, the five cluster modules must be promoted from `§8.1 Cluster: Political institutions (Government + Institutions + Stratification)` (audit pending) to a new `§4.5 Political institutions` (audited Methods) of the bilingual whitepaper. This is the campaign deliverable that closes the branch.

**Why this priority**: P1 — closes the branch and unlocks the next campaign branch (movement).

**Independent Test**: whitepaper EN+IT both contain a new `§4.5` chapter with 5 sub-sections (government, government_types, stratification, election, institutions), each following the canonical Methods schema (Background, Model, Equations, Parameters, Algorithm, Simplifications, Status header). `§8.1` is removed and subsequent §8.x renumbered. README EN+IT status table flips the five modules to "yes (CONVERGED YYYY-MM-DD round 2)". Doc-sync memory `feedback_whitepaper_doc_sync.md` adds 5 mapping rows for `epocha/apps/world/{government,government_types,stratification,election,institutions}.py` → §4.5.

**Acceptance Scenarios**:

1. **Given** Round 2 audit CONVERGED on the cluster, **When** inspecting the whitepaper EN at `§4`, **Then** a new `§4.5 Political institutions` chapter exists with 5 sub-sections matching the canonical schema; `§8.1` is removed.

2. **Given** EN promotion applied, **When** inspecting the IT mirror, **Then** the same structure exists translated, with equation numbering preserved.

3. **Given** the promotion commit, **When** inspecting `README.md` and `README.it.md` status table, **Then** the five cluster modules show "yes (CONVERGED YYYY-MM-DD round 2)" / "sì (CONVERGENTE YYYY-MM-DD round 2)".

4. **Given** the promotion commit, **When** inspecting `docs/memory-backup/feedback_whitepaper_doc_sync.md`, **Then** five new mapping rows exist for the cluster modules.

5. **Given** the merge commit on develop, **When** running a follow-up commit `docs: pin political cluster §4.5 frozen-at-commit`, **Then** the §4.5 status headers in EN+IT replace `<filled-on-merge>` with the merge SHA.

---

### Edge Cases

- **G-2 status reverification**: the user-supplied finding catalogue describes the original Round 1 deterministic-coup behavior; current code on develop @ `1c75854` already implements `random.random() < success_probability`. If Round 2 audit detects a regression OR if the deprecated `_COUP_SUCCESS_THRESHOLD` constant is still referenced by any test, the spec's User Story 1 acceptance scenario 2 becomes a behavioral fix instead of a verification step. The plan tasks must handle both paths.
- **Breaking change scope on coup behavior**: if any existing test relies on `_COUP_SUCCESS_THRESHOLD` (verified by `grep -rn _COUP_SUCCESS_THRESHOLD`), removal of the constant requires coordinated test updates with traceable rationale per Constitution Principle V.
- **X-1 unification vs documentation**: if Round 2 auditor flags the existing inline documentation as insufficient (the two-place mutation pattern is an architectural smell), an escalation to user is required before any unification refactor — the change reshapes the political-tick pipeline.
- **S-2 transaction safety**: the wealth-conservation fix must run inside a database transaction; if the existing `process_corruption` is not already wrapped in `transaction.atomic`, the fix scope expands to add that decorator. Escalate to user if scope grows.
- **Citation that cannot be verified via Crossref**: use `<!-- VERIFICATION PENDING: <reason> -->` HTML comment per the established whitepaper §13 convention; never leave a `[VERIFICATION PENDING]` visible body text.
- **Pytest regression**: any fix that breaks an existing test must be accompanied by either a test update with traceable rationale OR escalation to user. No `pytest.mark.skip` without explicit user authorization per Principle V.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST cite Powell & Thyne (2011) in `government.py` only as the empirical-dataset source (~50% coup-success base rate calibration), and document the multi-term coup-success formula as a simulation design parameter inspired by the coup literature (closes G-1).
- **FR-002**: System MUST execute the coup decision stochastically via `random.random() < success_probability`; if the legacy `_COUP_SUCCESS_THRESHOLD` constant is still exported, mark it deprecated or remove it with coordinated test updates (closes G-2; pre-verified on develop, Round 2 confirms).
- **FR-003**: System MUST document the institutional-trust decay rate `0.05` per tick either by citing a specific Freedom House report with tick-to-year mapping or by marking it as a tunable design parameter inspired by Freedom House annual repression trends (closes G-3).
- **FR-004**: System MUST remove the false "Polity IV Table 3" attribution for government-type transition thresholds in `government_types.py` and document them as design parameters inspired by Acemoglu-Robinson 2006 and Geddes 1999 (closes G-4).
- **FR-005**: System MUST document the legitimacy weights (health, education, economy, media) as either cited or tunable design parameters in `government.py` (closes G-5).
- **FR-006**: System MUST resolve the naming mismatch between the `economy` local variable and `World.stability_index` in `government.py:_update_stability` and `update_government_indicators` — either by renaming the variable to `mood_proxy` or by documenting the proxy semantics inline at both call sites (closes G-6).
- **FR-007**: System MUST carry a module-level disclaimer in `government_types.py` stating that all values in `repression_tendency`, `corruption_resistance`, `institution_effects`, `stability_weights` are design parameters inspired by the cited literature (closes GT-1).
- **FR-008**: System MUST acknowledge Gilbert (2011) as inspiration for the 5-class stratification with an explicit note about the simplification from 6 to 5 classes and the percentile-threshold adjustments (closes S-1).
- **FR-009**: System MUST enforce wealth conservation in `stratification.py:process_corruption`: every increment to a corrupt agent's `wealth` MUST be matched by an equal decrement of `world.global_wealth` in the same transaction (closes S-2).
- **FR-010**: System MUST document the `conscientiousness < 0.4` corruption threshold in `stratification.py` as a tunable design parameter (NOT a value derived from Acemoglu-Robinson 2006), with optional reference to Miller-Lynam (2001) for the personality-deviance link (closes S-3).
- **FR-011**: System MUST document the upward/downward mobility weights (0.4 / 0.7) in `stratification.py` as preserving the ~2:1 loss-aversion ratio from Kahneman-Tversky (1979) while explicitly marking the magnitudes as tunable (closes S-4).
- **FR-012**: System MUST replace the Zonis & Joseph (1994) citation for charisma's voting influence in `election.py` with one of Weber (1922), Bass (1985), or Merolla-Zechmeister (2011), DOI-verified via Crossref where applicable (closes E-1).
- **FR-013**: System MUST record E-2 as ALREADY CLOSED by Branch 1 (the dead `_memory_influence_score` symbol was deleted; Round 2 verifies absence via `grep`).
- **FR-014**: System MUST document the vote-component weights in `election.py` as design parameters with a forward pointer to Lewis-Beck & Stegmaier (2000) (closes E-3).
- **FR-015**: System MUST document the wealth-saturation cap `100.0` in `election.py` as anchored to the `Agent.wealth` default (2× default = 100), removing the circular "median household wealth in pre-industrial simulations" justification (closes E-4).
- **FR-016**: System MUST cache the voter count once before the manipulation-bonus loop in `election.py` (no `len(list(voters))` re-evaluation); Round 2 verifies the current code already satisfies this (closes E-5).
- **FR-017**: System MUST document `INSTITUTION_EFFECT_SCALE = 20.0` with its intended tick-to-year timescale mapping (33 ticks ≈ 2.75 years near-peak recovery, assuming 1 tick ≈ 1 month) (closes I-1).
- **FR-018**: System MUST remove the Gupta et al. (2002) citation for `FUNDING_EFFECT_RATE = 0.04` (off-topic) and document the value as a tunable design parameter (closes I-2).
- **FR-019**: System MUST reconcile the `ENTROPY_PER_TICK = -0.005` implementation with its documentation — either implement exponential decay or correct the docstring language from "half-life" to "linear decay reaching 50% after 100 ticks" (closes I-3).
- **FR-020**: System MUST either unify the two-place corruption update (`stratification.py:process_corruption` and `government.py:update_government_indicators`) into a single path OR document the layering explicitly with stated semantics (closes X-1).
- **FR-021**: System MUST add invariant tests under `epocha/apps/world/tests/test_political_invariants.py` for at least the wealth-conservation contract (FR-009) and the deprecation/absence of `_COUP_SUCCESS_THRESHOLD` if removed (FR-002). Additional invariants encouraged where enforceable.
- **FR-022**: System MUST reach Round 2 audit CONVERGED verdict before whitepaper promotion.
- **FR-023**: System MUST promote `§8.1` → `§4.5` in bilingual whitepaper per User Story 4 acceptance scenarios, including renumbering subsequent §8.x sections.
- **FR-024**: System MUST update README EN+IT status table and doc-sync memory mapping after promotion.
- **FR-025**: System MUST maintain pytest gate green (current baseline to be measured at T002 — expected ≥804 after Branch 2 closure; expected ≥805 with FR-021 invariant tests added).

### Key Entities

- **Government** (existing model `epocha/apps/world/models.py`): touched only by behavior fixes; no schema change planned.
- **World** (existing): `global_wealth` field is read+written by `stratification.process_corruption` after the FR-009 fix; no schema change.
- **Whitepaper EN/IT** (`docs/whitepaper/epocha-whitepaper.{md,it.md}`): receives new `§4.5` chapter, loses `§8.1`, renumbers §8.2-§8.5. Up to 4 new §13 citations may be required (Weber 1922 pre-DOI; Bass 1985 pre-DOI; Merolla-Zechmeister 2011 DOI; Miller-Lynam 2001 DOI) depending on chosen replacements for E-1 and S-3.
- **README EN/IT**: status table update for 5 modules.
- **Doc-sync memory** (`docs/memory-backup/feedback_whitepaper_doc_sync.md` + live): 5 new mapping rows.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Round 2 critical-analyzer audit on the five cluster modules returns verdict CONVERGED with zero INCORRECT, zero UNJUSTIFIED unresolved, zero INCONSISTENT unresolved, zero MISSING unresolved.
- **SC-002**: `pytest --cov=epocha -v` passes with zero failures (baseline measured at T002; expected ≥805 with FR-021 invariant tests added).
- **SC-003**: Whitepaper EN at `§4.5` contains 5 sub-sections following canonical schema; `§8.1` removed; subsequent `§8.x` sections renumbered.
- **SC-004**: Whitepaper IT mirrors §4.5 structure with translated content and identical equation numbering.
- **SC-005**: README EN+IT status table rows for the five modules show "CONVERGED YYYY-MM-DD round 2".
- **SC-006**: Doc-sync memory `feedback_whitepaper_doc_sync.md` contains 5 new mapping rows for `epocha/apps/world/{government,government_types,stratification,election,institutions}.py` → `§4.5.{1..5}`.
- **SC-007**: Branch merged to develop via PR with merge commit; `<filled-on-merge>` placeholders in the new §4.5 status headers replaced with merge SHA in a follow-up commit on develop.
- **SC-008**: Wealth conservation invariant test (FR-021) passes: post-`process_corruption` tick, `sum(agent.wealth)` delta + `world.global_wealth` delta = 0 within float tolerance.

## Assumptions

- The Round 1 audit findings catalogue (user-supplied, source `docs/scientific-audit-2026-04-12.md` transcript) is the authoritative input. No re-running of the original Round 1 audit; Round 2 verification + fixes go directly into execution.
- The fix-implementer prefers the lowest-risk path per Constitution Principle V; behavioral fixes (FR-002 if regression detected, FR-009, FR-016 if regression detected) are mandatory; documentation upgrades are sufficient for findings where listed in User Story 3 acceptance scenarios.
- The whitepaper promotion procedure follows the standard documented in project memory `project_whitepaper_promotion_pipeline.md`.
- No new external runtime dependencies introduced.
- No migration on existing models unless an escalated decision changes scope.
- Italian whitepaper translation follows the established style from prior promotions.
- Pytest runs in Docker via `docker compose -f docker-compose.local.yml exec -T web pytest`.
- The 6 Round 1 findings that appear already remediated by interim commits (G-2, E-2, E-5, X-1 inline note, S-3 inline cite of Miller-Lynam, S-4 docstring) require explicit Round 2 verification — the spec treats them as "verify and confirm" rather than "fix from scratch", but the plan must include a fallback fix-path if verification fails.

## Constitution Compliance

This spec is constitutional-compliant per `.specify/memory/constitution.md` v1.0.0:

- **Principle I (Scientific Method)**: every Round 1 finding resolution must produce either a verified citation, a documented tunable parameter, or a documented known limitation. No magic numbers introduced.
- **Principle II (Verify Before Asserting)**: every file path, function signature, and line range mentioned in this spec was verified against current code on develop @ commit `1c75854` (post Branch 2 closure).
- **Principle III (Adversarial Audit)**: Round 2 audit dispatch via `critical-analyzer` subagent is mandatory before any whitepaper promotion. Convergence loop: audit → fix → re-audit → CONVERGED, or repeat.
- **Principle IV (Three-Step Design)**: this spec is the consolidated output of the Round 1 audit catalogue + controller-side re-review; no further design iteration before plan.
- **Principle V (Evidence-Based Verification)**: pytest gate at every fix commit; promotion requires Round 2 CONVERGED verdict.

## Out of Scope

- Round 1 audit re-execution (already done 2026-04-12, output is the input to this spec).
- Other campaign branches (movement, factions, world-economy-deprecation, knowledge-graph) — separate Spec Kit features in subsequent timestamps.
- Demography Plan 4 (engine wiring) — post-campaign work item.
- Validation experiments execution — post-campaign work item.
- Unification of the corruption update into a single path if Round 2 auditor accepts the current inline documentation (X-1 acceptance scenario explicitly admits the documentation-only resolution path).
- Refactor of `stability_index` semantics into a dedicated economic indicator (G-6 acceptance scenario explicitly admits the documentation-only resolution path).
- Switching `ENTROPY_PER_TICK` to exponential decay if the linear-decay docstring correction is accepted (I-3 acceptance scenario explicitly admits the documentation-only resolution path).

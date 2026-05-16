# Feature Specification: Rumor Cluster Audit Re-pass (Round 2)

**Feature Branch**: `20260516-105818-rumor-cluster-audit-repass`

**Created**: 2026-05-16

**Status**: Draft (post Round 2 audit, pre-fix)

**Input**: User description: "Round 2 adversarial audit re-pass for the rumor propagation cluster (information_flow, distortion, belief, affinity) — close 16 findings from Round 2 audit of 2026-05-12 and promote modules from whitepaper §8.1 to a new §4.4."

## Context

This feature is part of the **F-CAMPAIGN audit re-pass batch 2026-04-12** documented in `docs/superpowers/plans/2026-05-12-audit-repass-campaign.md` (legacy plan, archival). The rumor cluster comprises four scientific modules in `epocha/apps/agents/`: `information_flow.py`, `distortion.py`, `belief.py`, `affinity.py`. Round 1 remediation commits `17f046a`, `7744016`, `951a606` applied documentation-level fixes to the original 2026-04-12 audit findings. A Round 2 adversarial audit on 2026-05-12 identified 16 outstanding findings (5 unfixed/partial from Round 1 + 11 new) blocking the §8.1 → §4.4 whitepaper promotion.

The Round 2 audit verdict was **NOT CONVERGED — 16 findings to resolve** (3 INCORRECT, 9 UNJUSTIFIED, 4 INCONSISTENT). Findings are catalogued in detail in the project memory `project_session_resume_2026_05_12.md`.

This spec is constitutional-compliant per `.specify/memory/constitution.md` v1.0.0: Principles I (Scientific Method), II (Verify Before Asserting), III (Adversarial Audit), V (Evidence-Based Verification).

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Close 3 INCORRECT findings to unblock whitepaper promotion (Priority: P1)

The Round 2 audit identified three INCORRECT findings that BLOCK the §8.1 → §4.4 whitepaper promotion until resolved. The project maintainer must close them with behavioral or substantive documentation fixes before requesting a Round 3 re-audit.

**Why this priority**: per the audit verdict, the whitepaper §4.4 promotion (the deliverable that closes this branch) requires all INCORRECT and INCONSISTENT findings resolved. The three INCORRECT items are: silent dropping of distinct public events in same tick (IF-5), cross-module vocabulary mismatch breaking the Castelfranchi-Conte-Paolucci dual-track on hearsay (N-1), distortion-induced reputation drift biased by transmitter personality (N-3).

**Independent Test**: dispatch Round 3 critical-analyzer audit limited to the 3 INCORRECT findings; verdict must be CONVERGED for each.

**Acceptance Scenarios**:

1. **Given** two distinct public events fire at the same tick for the same agent, **When** `_propagate_memory` Phase 4 stores them, **Then** both are persisted (currently only the first wins because dedup lookup at `information_flow.py:141-159` lacks content/event_id).

2. **Given** an agent observes another performing an action with structured `action_type` in the {`pair_bond`, `separate`, `borrow`, `form_group`, `protest`, `hoard`, `move_to`, `buy_property`, `sell_property`, `avoid_conception`, `explore`, `rest`, `campaign`, `join_group`} vocabulary, **When** the observation propagates as hearsay through `_propagate_memory`, **Then** the receiving agent's reputation of the observed target receives a non-zero update with sign consistent with `_IMAGE_DELTAS[action_type]` (currently `extract_action_sentiment` returns 0.0 for all these action types and the reputation update is silently skipped).

3. **Given** a memory of content "X argued with Y" propagates through a high-neuroticism transmitter (distortion expands to "fought bitterly") and then through a high-agreeableness transmitter (distortion softens to "discussed"), **When** the receiver applies `update_reputation`, **Then** the reputation delta on Y is computed from the original `"argued"` sentiment, NOT from the distorted variants (currently `extract_action_sentiment` is called on `distorted_content` at `information_flow.py:236` after the distortion pass at line 232).

---

### User Story 2 — Close 4 INCONSISTENT findings (Priority: P1)

The Round 2 audit identified four INCONSISTENT findings. Three are structural inconsistencies inside source files; one is the absence of test coverage for the cluster's invariants.

**Why this priority**: same as P1 — whitepaper §4.4 promotion blocked until INCONSISTENT findings are resolved. Per Constitution Principle III convergence loop.

**Independent Test**: dispatch Round 3 critical-analyzer audit on the resolved files; verdict CONVERGED.

**Acceptance Scenarios**:

1. **Given** the `distortion.py` module docstring declares only assimilation is implemented (lines 11-15), **When** inspecting individual pattern comments at lines 43 and 97 ("Allport-Postman: sharpening of negative affect"), **Then** the comments are reconciled with the module-level claim (D-1).

2. **Given** `belief.py` cites Mayer-Davis-Schoorman 1995, Graziano-Tobin 2002, Castelfranchi-Falcone-Tan 1998 in body and `affinity.py` cites McCrae-Costa 2003 in body, **When** searching whitepaper §13 for the corresponding entries, **Then** all four citations have full bibliographic entries with author, year, title, venue, DOI/URL (N-2).

3. **Given** `_apply_patterns` iterates patterns in declaration order and breaks on first match (`distortion.py:218-222`), **When** input contains multiple linguistically salient candidates, **Then** the source-order assumption is documented explicitly as deliberate OR the implementation switches to highest-strength match (N-4).

4. **Given** the rumor cluster's invariant contracts (vocabulary alignment between `_IMAGE_DELTAS` and sentiment keywords; reputation independence from transmitter personality), **When** running the test suite, **Then** at least the N-1 vocabulary alignment and N-3 distortion-independent reputation invariants are enforced by failing tests (or skip-marked with traceable rationale per Principle V) under `epocha/apps/agents/tests/test_rumor_invariants.py` (N-10).

---

### User Story 3 — Close 9 UNJUSTIFIED findings (Priority: P2)

The Round 2 audit identified nine UNJUSTIFIED findings requiring documentation upgrades, settings extractions, or minor refactors. None blocks whitepaper promotion alone but all are required for the cluster to meet Constitution Principle I ("No parameter without a justified value").

**Why this priority**: P2 because individually non-blocking but collectively required for CONVERGED verdict on the cluster. Group fix in 2-3 commits.

**Independent Test**: dispatch Round 3 audit on the resolved files; verdict CONVERGED.

**Acceptance Scenarios**:

1. **Given** the whitepaper §8.1 cluster narrative claims a "three families of literature" transcription (Allport-Postman + Bartlett + Granovetter), **When** auditing `information_flow.py:_propagate_memory`, **Then** either the Granovetter weak-tie weighting is implemented OR the §8.1 narrative is corrected to mention only the two transcribed families (IF-1).

2. **Given** `_estimate_hop` assumes initial reliability=1.0 (`information_flow.py:327-331`), **When** a memory inherits reliability < 1.0 from a noisy source, **Then** the limitation is documented explicitly as accepted OR `hop_count` is tracked as a Memory model field (IF-4).

3. **Given** high-openness pattern multi-hop accumulation (`distortion.py:78-86`) and low-conscientiousness proper-noun anonymization (`distortion.py:116-124`), **When** documenting Simplifications, **Then** both behaviors are documented as accepted known limitations with explicit reference (D-4, D-5).

4. **Given** the inline reputation normalization at `belief.py:81-85` duplicated from `ReputationScore.get_combined_score_normalized()`, **When** invoking either, **Then** both paths delegate to a single `_normalize_reputation(raw: float) -> float` helper in `reputation.py` (N-5).

5. **Given** the weak-rumor magic numbers `emotional_weight=0.1` and `reliability=new_reliability * 0.3` (`information_flow.py:311-313`), **When** searching for their origin, **Then** they are promoted to settings (`EPOCHA_INFO_FLOW_WEAK_RUMOR_WEIGHT`, `EPOCHA_INFO_FLOW_WEAK_RUMOR_DAMP`) with docstring marking them tunable design parameters (N-6).

6. **Given** `_personality_similarity` docstring (`affinity.py:100-103`) claims "missing traits contribute zero distance", **When** comparing A=0.9 (present) vs B=missing (defaults to 0.5), **Then** the docstring correctly describes the asymmetric behavior: `(0.9 - 0.5)^2 = 0.16`, not zero (N-7).

7. **Given** `_relationship_score` picks strongest record regardless of relation_type via `order_by("-strength").first()` (`affinity.py:153-162`), **When** an agent pair has both friendship and rivalry records, **Then** either a citation is added (Coleman 1990 *Foundations of Social Theory* or Axelrod 1984 on tit-for-tat) supporting the rival-coalition design choice OR the choice is marked as "tunable heuristic without empirical anchor" (N-8).

8. **Given** Phase 1 (`information_flow.py:71-91`) enforces `emotional_weight__gte=threshold` and Phase 2 (lines 92-111) does not, **When** documenting the propagation pipeline, **Then** the asymmetry is documented explicitly with rationale (N-9).

---

### User Story 4 — Promote §8.1 → §4.4 in bilingual whitepaper after Round 3 CONVERGED (Priority: P1)

After the Round 3 re-audit verdict is CONVERGED, the four cluster modules must be promoted from `§8.1 Rumor cluster` (audit pending) to a new `§4.4 Rumor propagation` (audited Methods) of the bilingual whitepaper. This is the campaign deliverable that closes the branch.

**Why this priority**: P1 — closes the branch and unlocks the next campaign branch (political cluster).

**Independent Test**: whitepaper EN+IT both contain a new `§4.4` chapter with 4 sub-sections (information_flow, distortion, belief, affinity), each following the canonical Methods schema (Background, Model, Equations, Parameters, Algorithm, Simplifications, Status header). `§8.1` is removed. README EN+IT status table flips the four modules to "yes (CONVERGED YYYY-MM-DD round 2)". Doc-sync memory `feedback_whitepaper_doc_sync.md` adds mapping rows for `epocha/apps/agents/{information_flow,distortion,belief,affinity}.py` → §4.4.

**Acceptance Scenarios**:

1. **Given** Round 3 audit CONVERGED on the cluster, **When** inspecting the whitepaper EN at `§4`, **Then** a new `§4.4 Rumor propagation` chapter exists with 4 sub-sections matching the canonical schema; `§8.1` is removed.

2. **Given** EN promotion applied, **When** inspecting the IT mirror, **Then** the same structure exists translated, with equation numbering preserved.

3. **Given** the promotion commit, **When** inspecting `README.md` and `README.it.md` status table, **Then** the four cluster modules show "yes (CONVERGED YYYY-MM-DD round 2)" / "sì (CONVERGENTE YYYY-MM-DD round 2)".

4. **Given** the promotion commit, **When** inspecting `docs/memory-backup/feedback_whitepaper_doc_sync.md`, **Then** four new mapping rows exist for the cluster modules.

5. **Given** the merge commit on develop, **When** running a follow-up commit `docs: pin rumor cluster §4.4 frozen-at-commit`, **Then** the §4.4 status headers in EN+IT replace `<filled-on-merge>` with the merge SHA.

---

### Edge Cases

- **Conflicting Round 2 findings**: if a behavioral fix for one finding (e.g. extending `_IMAGE_DELTAS` to cover the vocabulary in N-1) introduces a new INCORRECT in the keyword table (e.g. wrong sentiment direction for a specific action), the Round 3 audit must catch it and a Round 4 must be performed. Per Constitution Principle III, no shortcut.
- **Backward compatibility on Memory model**: if a fix requires a new field on Memory (e.g. `hop_count` for IF-4), a migration must be authored and the fix considered scope-positive — escalate to user before applying.
- **Pytest regression**: any fix that breaks an existing test must be accompanied by either a test update with traceable rationale OR escalation to user. No `pytest.mark.skip` without explicit user authorization per Principle V "Bug discipline".
- **Citation that cannot be verified via Crossref**: use `<!-- VERIFICATION PENDING: <reason> -->` HTML comment per the established whitepaper §13 convention; never leave a `[VERIFICATION PENDING]` visible body text.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST persist distinct public events occurring at the same tick for the same agent as separate Memory records (closes IF-5).
- **FR-002**: System MUST update reputation via hearsay for all structured action types present in `_IMAGE_DELTAS`, not only for keyword-extractable free-text content (closes N-1).
- **FR-003**: System MUST compute reputation deltas from the original source content sentiment, not from the post-distortion content sentiment (closes N-3).
- **FR-004**: System MUST document or resolve the distortion module's sharpening-vs-assimilation labelling contradiction (closes D-1).
- **FR-005**: System MUST add §13 bibliography entries for Mayer-Davis-Schoorman 1995, Graziano-Tobin 2002, Castelfranchi-Falcone-Tan 1998, McCrae-Costa 2003 (closes N-2). DOIs verified via Crossref before commit.
- **FR-006**: System MUST document or resolve the first-pattern-wins behavior in `_apply_patterns` (closes N-4).
- **FR-007**: System MUST add invariant tests under `epocha/apps/agents/tests/test_rumor_invariants.py` for at least the N-1 vocabulary alignment and N-3 distortion-independent reputation contracts (closes N-10).
- **FR-008**: System MUST resolve or document IF-1, IF-4, D-4, D-5, N-5, N-6, N-7, N-8, N-9 per User Story 3 acceptance scenarios.
- **FR-009**: System MUST reach Round 3 audit CONVERGED verdict before whitepaper promotion.
- **FR-010**: System MUST promote `§8.1` → `§4.4` in bilingual whitepaper per User Story 4 acceptance scenarios.
- **FR-011**: System MUST update README EN+IT status table and doc-sync memory mapping after promotion.
- **FR-012**: System MUST maintain pytest gate green (currently 801 passed, expected 801+N new invariant tests).

### Key Entities

- **Memory** (existing model `epocha/apps/agents/models.py`): Round 2 finding IF-4 raises a potential need for `hop_count` field (escalate if scope-positive).
- **ReputationScore** (existing): No structural change expected from this branch.
- **Whitepaper EN/IT** (`docs/whitepaper/epocha-whitepaper.{md,it.md}`): receives new `§4.4` chapter, loses `§8.1`, gains 4 new `§13` entries.
- **README EN/IT**: status table update.
- **Doc-sync memory** (`docs/memory-backup/feedback_whitepaper_doc_sync.md` + live): new mapping rows.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Round 3 critical-analyzer audit on the four cluster modules returns verdict CONVERGED with zero INCORRECT, zero UNJUSTIFIED unresolved, zero INCONSISTENT unresolved.
- **SC-002**: `pytest --cov=epocha -v` passes with zero failures (current baseline 801, expected ≥802 with N-10 invariant tests added).
- **SC-003**: Whitepaper EN at `§4.4` contains 4 sub-sections following canonical schema; `§8.1` removed; renumbering applied to subsequent `§8.x` entries.
- **SC-004**: Whitepaper IT mirrors §4.4 structure with translated content and identical equation numbering.
- **SC-005**: README EN+IT status table rows for the four modules show "CONVERGED YYYY-MM-DD round 2".
- **SC-006**: Doc-sync memory `feedback_whitepaper_doc_sync.md` contains 4 new mapping rows for `epocha/apps/agents/{information_flow,distortion,belief,affinity}.py` → `§4.4.{1..4}`.
- **SC-007**: Branch merged to develop via PR with merge commit; `<filled-on-merge>` placeholders in the new §4.4 status headers replaced with merge SHA in a follow-up commit on develop.
- **SC-008**: No new entry under `docs/superpowers/specs/` or `docs/superpowers/plans/` — Spec Kit absolute compliance.

## Assumptions

- The Round 2 audit findings catalogue in `project_session_resume_2026_05_12.md` is the authoritative input. No re-running of Round 2 audit; we go directly to fix-implementer + Round 3 verification.
- The fix-implementer prefers the lowest-risk path per Constitution Principle V; behavioral fixes (FR-001, FR-002, FR-003, FR-007) are mandatory because the findings are INCORRECT/INCONSISTENT; documentation upgrades are sufficient for UNJUSTIFIED findings where listed in User Story 3 acceptance scenarios.
- The whitepaper promotion procedure follows the standard `project_whitepaper_promotion_pipeline.md` memory.
- No new external dependencies introduced.
- No migration on `Memory` model unless IF-4 fix is chosen to add `hop_count` (escalate first).
- Italian whitepaper translation follows the established style from the catch-up branch.
- Pytest runs in Docker via `docker compose -f docker-compose.local.yml exec -T web pytest`.

## Constitution Compliance

This spec is constitutional-compliant per `.specify/memory/constitution.md` v1.0.0:

- **Principle I (Scientific Method)**: every Round 2 finding resolution must produce either a verified citation, a documented tunable parameter, or a documented known limitation. No magic numbers introduced.
- **Principle II (Verify Before Asserting)**: every file path and function signature mentioned in this spec verified against current code on develop @ commit `19279a1` (Spec Kit adoption).
- **Principle III (Adversarial Audit)**: Round 3 audit dispatch via `critical-analyzer` subagent is mandatory before any whitepaper promotion.
- **Principle IV (Three-Step Design)**: this spec is the consolidated output of the Round 2 audit + this controller-side re-review; no further design iteration before plan.
- **Principle V (Evidence-Based Verification)**: pytest gate at every fix commit; promotion requires Round 3 CONVERGED verdict.

## Out of Scope

- Round 2 audit re-execution (already done 2026-05-12, output is the input to this spec).
- Other campaign branches (political cluster, movement, factions, world-economy-deprecation) — separate Spec Kit features in subsequent timestamps.
- Demography Plan 4 (engine wiring) — post-campaign work item.
- Validation experiments execution — post-campaign work item.
- Behavioral implementation of Granovetter's weak-tie weighting (IF-1 acceptance scenario explicitly admits the documentation-only resolution path).
- Migration to add `hop_count` field on Memory (IF-4 acceptance scenario explicitly admits the documentation-only resolution path).

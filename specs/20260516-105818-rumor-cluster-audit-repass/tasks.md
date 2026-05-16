---
description: "Tasks for rumor cluster audit re-pass — Round 2 to CONVERGED + chapter 4.4 promotion"
---

# Tasks: Rumor Cluster Audit Re-pass (Round 2)

**Input**: Design documents from `specs/20260516-105818-rumor-cluster-audit-repass/`

**Prerequisites**: spec.md (16 findings → 4 user stories), plan.md (Constitution Check PASS, no data-model/contracts/quickstart), research.md (Crossref DOIs + N-3 safety + N-8 cite decision)

**Tests**: included — Round 2 finding N-10 mandates invariant test suite. Plus regression pytest gate.

**Organization**: tasks grouped by Spec user story. MVP = US1 (3 INCORRECT findings closed → unblocks promotion path). US2 + US3 + US4 incremental.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: parallel-safe (different files, no dependencies)
- **[Story]**: US1/US2/US3/US4/SETUP/FOUND/POLISH
- Absolute file paths

## Path Conventions

Django backend single project. Source at `epocha/apps/agents/`, tests at `epocha/apps/agents/tests/`, whitepaper at `docs/whitepaper/`.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: pre-flight verification before any fix.

- [ ] T001 [SETUP] Verify Docker compose stack up: `docker compose -f docker-compose.local.yml ps`. Start if needed with `docker compose -f docker-compose.local.yml up -d`. Confirm web container healthy via `docker compose -f docker-compose.local.yml exec -T web python -c "import django; print(django.get_version())"`.
- [ ] T002 [SETUP] Baseline pytest run: `docker compose -f docker-compose.local.yml exec -T web pytest 2>&1 | tail -5`. Expected `801 passed`. Record baseline.
- [ ] T003 [SETUP] Re-verify Round 2 finding code references still match develop @ `b82684e` (rebased base). Spot-check 5 critical line refs from spec.md: `information_flow.py:141-159` (IF-5 dedup), `information_flow.py:232-236` (N-3 distortion before sentiment), `information_flow.py:311-313` (N-6 magic), `distortion.py:11-15` vs `distortion.py:43,97` (D-1 contradiction), `affinity.py:100-103` (N-7 docstring). If any drifted, escalate before proceeding.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: shared refactors that other user-story tasks build on.

- [ ] T004 [FOUND] Extract `_normalize_reputation(raw: float) -> float` helper at top of `epocha/apps/agents/reputation.py` (resolves N-5 root). Single source of truth `return (raw + 1.0) / 2.0`. Add module-level docstring marking it tunable design choice.
- [ ] T005 [FOUND] Wire `epocha/apps/agents/models.py:ReputationScore.get_combined_score_normalized()` to delegate to `reputation._normalize_reputation()` via lazy import (pattern from prior Branch 1 reputation `_WEIGHT_IMAGE`/`_WEIGHT_REPUTATION` delegation).
- [ ] T006 [FOUND] Add settings constants to `config/settings/base.py`: `EPOCHA_INFO_FLOW_WEAK_RUMOR_WEIGHT = float(os.environ.get("EPOCHA_INFO_FLOW_WEAK_RUMOR_WEIGHT", 0.1))` and `EPOCHA_INFO_FLOW_WEAK_RUMOR_DAMP = float(os.environ.get("EPOCHA_INFO_FLOW_WEAK_RUMOR_DAMP", 0.3))`. Docstring marks tunable.

**Checkpoint**: foundation ready. User stories can begin.

---

## Phase 3: User Story 1 — Close 3 INCORRECT findings (Priority: P1) 🎯 MVP

**Goal**: close IF-5, N-1, N-3 — the three INCORRECT findings that BLOCK whitepaper promotion.

**Independent Test**: dispatch Round 3 critical-analyzer audit limited to these three findings; verdict CONVERGED for each.

### IF-5 — Public event dedup includes content (behavioral)

- [ ] T007 [US1] In `epocha/apps/agents/information_flow.py` Phase 4 (lines ~141-159), change the `Memory.objects.get_or_create` lookup to include `content` (or `event_id` if a structured field exists) so two distinct events same tick same agent produce two memories. Use `defaults={"emotional_weight": ..., "reliability": ...}` for non-lookup fields.
- [ ] T008 [US1] Add test in `epocha/apps/agents/tests/test_information_flow.py`: `test_distinct_public_events_same_tick_produce_two_memories`. Setup: create simulation + 1 agent + 2 distinct events at same tick. Assert `Memory.objects.filter(agent=a, source_type=PUBLIC, tick_created=tick).count() == 2`.
- [ ] T009 [US1] Run targeted test: `pytest epocha/apps/agents/tests/test_information_flow.py -v`. Verify all green.

### N-1 — Cross-module vocabulary alignment (behavioral)

- [ ] T010 [US1] In `epocha/apps/agents/reputation.py`, extend `_POSITIVE_KEYWORDS` and `_NEGATIVE_KEYWORDS` to cover the 14 missing action types from `_IMAGE_DELTAS`: `pair_bond`, `separate`, `borrow`, `form_group`, `protest`, `hoard`, `move_to`, `buy_property`, `sell_property`, `avoid_conception`, `explore`, `rest`, `campaign`, `join_group`. Sign per `_IMAGE_DELTAS[k]`. Magnitudes: use the same `0.5`/`1.0` convention as existing entries (`positive < 0.5`, `negative > 0.5` for high-magnitude). Document in docstring above the keyword tables as "alignment with _IMAGE_DELTAS for hearsay-path coverage of structured action types".
- [ ] T011 [US1] Alternative consideration (skip if T010 sufficient): rewrite `_propagate_memory` at `information_flow.py:236` to attempt structured `action_type` extraction first via regex `r"I decided to (\w+)\."` and fall back to `extract_action_sentiment(content)` only when no match. Marked optional — only if T010 fails to cover all cases.
- [ ] T012 [US1] Add invariant test in NEW file `epocha/apps/agents/tests/test_rumor_invariants.py`: `test_vocabulary_alignment_image_deltas_and_sentiment_keywords`. For each non-zero key in `reputation._IMAGE_DELTAS`, assert `reputation.extract_action_sentiment(f"I decided to {key}. reason")` has the same sign.
- [ ] T013 [US1] Run targeted: `pytest epocha/apps/agents/tests/test_rumor_invariants.py::test_vocabulary_alignment_image_deltas_and_sentiment_keywords -v`. Green.

### N-3 — Sentiment extracted from source content, not distorted (behavioral)

- [ ] T014 [US1] In `epocha/apps/agents/information_flow.py:_propagate_memory`, MOVE the call `action_sentiment = extract_action_sentiment(...)` from line ~236 (post-distortion) to BEFORE the distortion pass at line ~232. Pass `memory.content` (the original) not `distorted_content`. Distorted content continues feeding downstream retransmission unchanged.
- [ ] T015 [US1] Add invariant test in `test_rumor_invariants.py`: `test_reputation_delta_independent_of_transmitter_personality`. Setup: source memory "Marco argued with Elena", 2 propagation runs through transmitters with different personality (one high-neuroticism, one high-agreeableness), assert reputation delta on Elena is identical (both come from `extract_action_sentiment("argued")` not from distorted variants).
- [ ] T016 [US1] Run targeted tests for information_flow + invariants + reputation: `pytest epocha/apps/agents/tests/test_information_flow.py epocha/apps/agents/tests/test_rumor_invariants.py epocha/apps/agents/tests/test_reputation.py -v`. Green.

### US1 checkpoint

- [ ] T017 [US1] Full pytest gate: `pytest 2>&1 | tail -3`. Baseline 801 + ≥2 new invariant tests = ≥803 passed.
- [ ] T018 [US1] Commit `fix(agents): close round 2 INCORRECT findings IF-5 N-1 N-3 in rumor cluster`. Stage only the touched files: `information_flow.py`, `reputation.py`, `tests/test_information_flow.py`, `tests/test_rumor_invariants.py`.

---

## Phase 4: User Story 2 — Close 4 INCONSISTENT findings (Priority: P1)

**Goal**: close D-1, N-2 (4 missing §13 citations), N-4, N-10 (test suite).

**Independent Test**: dispatch Round 3 audit subset on resolved files; verdict CONVERGED.

### D-1 — Reconcile distortion docstring contradiction

- [ ] T019 [US2] In `epocha/apps/agents/distortion.py`, reconcile module docstring (lines ~11-15 "only assimilation implemented") with inline pattern comments at lines ~43 and ~97 (currently "sharpening of negative affect" / "sharpening of social salience"). Change inline comments to "assimilation toward negative-affect schema" / "assimilation toward expansive-social schema" to align with module-level claim.

### N-2 — Add 4 missing citations to §13 EN+IT + fix belief.py year attribution

- [ ] T020 [US2] In `epocha/apps/agents/belief.py` module docstring (around lines 18-21), correct the year attribution for Castelfranchi-Falcone-Tan from `1998` to `2001` per research.md Lookup 1.3 finding.
- [ ] T021 [US2] [P] In `docs/whitepaper/epocha-whitepaper.md` §13, insert 4 new bibliography entries alphabetically:
  - `Castelfranchi, C., Falcone, R., and Tan, Y.-H. (2001). The role of trust and deception in virtual societies. In *Proceedings of the 34th Annual Hawaii International Conference on System Sciences (HICSS-34)*. IEEE. https://doi.org/10.1109/hicss.2001.927042`
  - `Graziano, W. G., and Tobin, R. M. (2002). Agreeableness: dimension of personality or social desirability artifact? *Journal of Personality*, 70(5), 695-727. https://doi.org/10.1111/1467-6494.05021`
  - `Mayer, R. C., Davis, J. H., and Schoorman, F. D. (1995). An integrative model of organizational trust. *Academy of Management Review*, 20(3), 709-734. https://doi.org/10.2307/258792`
  - `McCrae, R. R., and Costa, P. T. (2003). *Personality in Adulthood: A Five-Factor Theory Perspective* (2nd ed.). Guilford Press, New York. ISBN 978-1-57230-827-2.`
- [ ] T022 [US2] [P] Mirror T021 in `docs/whitepaper/epocha-whitepaper.it.md` §13 (bibliography is identical EN/IT verbatim).

### N-4 — Document first-pattern-wins in distortion

- [ ] T023 [US2] In `epocha/apps/agents/distortion.py:_apply_patterns` (around lines 218-222) extend the docstring to document explicitly: "Patterns are evaluated in declaration order; the first matching pattern wins. This is a deliberate source-order assumption; patterns are listed in order of intended linguistic priority within each personality block. To change priority, reorder the patterns in the source."

### N-10 — Invariant test suite scaffold (extend T012/T015 file)

- [ ] T024 [US2] In `epocha/apps/agents/tests/test_rumor_invariants.py` (created by T012), add module docstring describing it as "Cross-module invariant test suite for the rumor propagation cluster — vocabulary alignment, distortion-independent reputation, future invariants per Constitution Principle V". Add `test_extract_action_sentiment_no_distortion_dependency` (acceptance scenario 4 of US2): run same source content through `extract_action_sentiment` with different decorations and verify the result depends only on keyword content. Already covered partially by T015; this test is the explicit constitutional invariant.

### US2 checkpoint

- [ ] T025 [US2] Full pytest gate. Expected ≥804 passed.
- [ ] T026 [US2] Commit `fix(agents): close round 2 INCONSISTENT findings D-1 N-2 N-4 N-10 in rumor cluster`. Stage: `distortion.py`, `belief.py`, `tests/test_rumor_invariants.py`, `docs/whitepaper/epocha-whitepaper.md`, `docs/whitepaper/epocha-whitepaper.it.md`.

---

## Phase 5: User Story 3 — Close 9 UNJUSTIFIED findings (Priority: P2)

**Goal**: documentation upgrades + minor refactors per US3 acceptance scenarios.

### IF-1 — Remove "three families" claim from §8.1 whitepaper

- [ ] T027 [US3] In `docs/whitepaper/epocha-whitepaper.md` §8.1 cluster narrative, remove the implicit "three families of literature transcription" framing where Granovetter is listed alongside Allport-Postman + Bartlett as a transcribed model. Replace with explicit "two families transcribed (Allport-Postman serial reproduction, Bartlett distortion mechanisms); Granovetter weak-tie theory CITED but NOT implemented at the propagation layer — see Simplifications".
- [ ] T028 [US3] [P] Mirror T027 in IT whitepaper §8.1.

### IF-4 — Document _estimate_hop limitation

- [ ] T029 [US3] In `epocha/apps/agents/information_flow.py:_estimate_hop` (around lines 322-346) extend docstring with explicit Known Limitation block: "Assumes initial reliability=1.0. Memories inheriting reliability<1.0 (e.g. derived from a noisy public event with severity<1.0) will have an overestimated hop count, causing premature propagation halt. Acceptable for current implementation; tracked as known simplification. A behavioral fix would require adding `hop_count` PositiveSmallIntegerField on the Memory model with backfill migration — scope-positive, deferred."

### D-4, D-5 — Document distortion accumulation / proper-noun anonymization

- [ ] T030 [US3] In `epocha/apps/agents/distortion.py` after `_apply_patterns` add module-level Known Limitations comment block enumerating: (D-4) "High-openness pattern (line ~78) inserts speculative clauses at every period-space boundary; multi-hop accumulation pathological. Documented as known limitation; future work could restrict to first/last sentence boundary or transmitter-count cap." (D-5) "Low-conscientiousness pattern (line ~113) replaces all mid-sentence capitalized words with 'somebody/someone/this person', destroying non-person proper nouns (place names, titles). Documented as known limitation; future work could ship a NER pre-pass."

### N-7 — Affinity docstring correction

- [ ] T031 [US3] In `epocha/apps/agents/affinity.py:_personality_similarity` docstring (around lines 100-103) rewrite the missing-trait paragraph: "Missing or non-numeric traits default to 0.5 for that agent. If BOTH agents are missing the trait, that dimension contributes zero distance. If only ONE agent has the trait missing, the present trait value is compared against 0.5 — producing a non-zero distance proportional to how far the present value is from neutral."

### N-8 — Affinity rival-coalition citation

- [ ] T032 [US3] In `epocha/apps/agents/affinity.py:_relationship_score` (around lines 125-164) extend docstring with: "Rival relationships contribute to coalition affinity through repeated-interaction reciprocity dynamics (Axelrod 1984 *The Evolution of Cooperation*; alternative: Coleman 1990 *Foundations of Social Theory* on coalition stability under rivalry). The `order_by('-strength').first()` tie-break across relation_types is a tunable heuristic — current behavior favors the strongest record regardless of type."

### N-9 — Document Phase 2 threshold asymmetry

- [ ] T033 [US3] In `epocha/apps/agents/information_flow.py` add Phase 2 docstring block (around lines 92-94) explaining: "Phase 2 does NOT enforce `emotional_weight__gte=threshold` like Phase 1 does. This is intentional: the threshold gates entry into the rumor network at hop 1; once a memory has been deemed worth transmitting, downstream agents receive it regardless of their personal salience threshold (gossip property — agents transmit what they have heard even when not personally invested). This asymmetry is documented; if undesired, enforce threshold consistently across all phases."

### N-6 — Replace magic numbers with settings reference

- [ ] T034 [US3] In `epocha/apps/agents/information_flow.py` (around lines 311-313 weak-rumor block) replace literal `0.1` with `settings.EPOCHA_INFO_FLOW_WEAK_RUMOR_WEIGHT` and `0.3` with `settings.EPOCHA_INFO_FLOW_WEAK_RUMOR_DAMP` (constants added in T006). Add `from django.conf import settings` import if missing.

### N-5 — Delegate inline normalize to helper

- [ ] T035 [US3] In `epocha/apps/agents/belief.py` (around lines 81-85) replace inline `(raw + 1.0) / 2.0` with call to `reputation._normalize_reputation(raw)` (helper from T004). Remove the misleading comment about migrating to ReputationScore method. Add brief comment "delegates to single source of truth in reputation module".

### US3 checkpoint

- [ ] T036 [US3] Full pytest gate. Expected ≥804 (no new tests added in this phase).
- [ ] T037 [US3] Commit `fix(agents): close round 2 UNJUSTIFIED findings IF-1 IF-4 D-4 D-5 N-5 N-6 N-7 N-8 N-9 in rumor cluster`. Stage: `information_flow.py`, `distortion.py`, `belief.py`, `affinity.py`, `config/settings/base.py`, `docs/whitepaper/epocha-whitepaper.md`, `docs/whitepaper/epocha-whitepaper.it.md`.

---

## Phase 6: Round 3 Adversarial Audit (Convergence Loop)

**Purpose**: per Constitution Principle III, re-audit before promotion. Loop until CONVERGED.

- [ ] T038 [US4 prep] Dispatch `critical-analyzer` subagent (Opus) for Round 3 audit on `epocha/apps/agents/{information_flow,distortion,belief,affinity}.py` + cross-module `reputation.py` + new `tests/test_rumor_invariants.py`. Prompt includes: original 16 findings + their resolution per US1+US2+US3 commits; mandate to verify each fix landed AND no new INCORRECT/UNJUSTIFIED introduced; whitepaper §13 4 new entries verified Crossref DOI; spec.md acceptance scenarios mapped to commits.
- [ ] T039 [US4 prep] If verdict NOT CONVERGED: dispatch fix-implementer for residual findings with same lowest-risk strategy. Repeat T038. Expect ≤2 round-trips per Branch 1 (Reputation) precedent.
- [ ] T040 [US4 prep] When verdict CONVERGED: record Round 3 audit transcript hash or summary in a brief commit note (not a new file under docs/superpowers/; per Spec Kit rule). Audit transcript may be embedded as appendix in the future tasks-completion log.

---

## Phase 7: User Story 4 — Whitepaper §8.1 → §4.4 Promotion (Priority: P1)

**Goal**: campaign deliverable. Promote 4 modules from designed-pending to audited-Methods.

### Whitepaper EN promotion

- [ ] T041 [US4] In `docs/whitepaper/epocha-whitepaper.md`, REMOVE §8.1 (Rumor cluster) entirely. Renumber subsequent §8.x: §8.2 → §8.1 (Political institutions), §8.3 → §8.2 (Movement), §8.4 → §8.3 (Factions), §8.5 → §8.4 (Knowledge Graph), §8.6 → §8.5 (Economy base layer). (Note: §8.5 Reputation was already promoted to §4.3 in prior catch-up Branch 1.)
- [ ] T042 [US4] Insert new §4.4 between current §4.3 and §5 Implementation. Title: `## 4.4 Rumor propagation`. Status header: `> Status: implemented as of commit <filled-on-merge>, code audit CONVERGED 2026-05-16 round 2.`
- [ ] T043 [US4] §4.4 body — 4 sub-sections per canonical Methods schema:
  - §4.4.1 Information flow (Bartlett 1932 serial reproduction; Granovetter 1973 CITED but NOT implemented at propagation layer, see Simplifications)
  - §4.4.2 Distortion (Allport-Postman 1947 assimilation only — sharpening + leveling NOT implemented; Costa-McCrae 1992 Big Five modulation)
  - §4.4.3 Belief filter (Mayer-Davis-Schoorman 1995 loosely inspired; Graziano-Tobin 2002 agreeableness-credulity; Castelfranchi-Falcone-Tan 2001 trust-deception)
  - §4.4.4 Affinity (McCrae-Costa 2003 Big Five Euclidean similarity; Axelrod 1984 rival-coalition dynamics)
  Each sub-section: Background, Model, Equations (numbered following the existing 4.1.x-4.3.x sequence), Parameters table, Algorithm, Simplifications (documenting D-1, D-4, D-5, IF-1, IF-4, N-3, N-4, N-9 limitations explicitly), Status header.

### Whitepaper IT mirror

- [ ] T044 [US4] Mirror T041 in `docs/whitepaper/epocha-whitepaper.it.md`: remove §8.1 IT, renumber.
- [ ] T045 [US4] Mirror T042+T043 in IT: insert `## 4.4 Propagazione del passaparola` with 4 sub-sections translated, equation numbering identical to EN. Status header in IT: `> Stato: implementato a partire dal commit <filled-on-merge>, audit del codice CONVERGENTE 2026-05-16 round 2.`

### README EN+IT status table

- [ ] T046 [US4] In `README.md` Status table flip 4 rows (information_flow, distortion, belief, affinity — currently listed under "Other modules (...)" cluster row) to `yes (CONVERGED 2026-05-16 round 2)`.
- [ ] T047 [US4] [P] Mirror T046 in `README.it.md` with `sì (CONVERGENTE 2026-05-16 round 2)`.

### Doc-sync memory

- [ ] T048 [US4] In `docs/memory-backup/feedback_whitepaper_doc_sync.md` mapping table add 4 rows:
  - `| epocha/apps/agents/information_flow.py | §4.4.1 (EN) | §4.4.1 (IT) |`
  - `| epocha/apps/agents/distortion.py | §4.4.2 (EN) | §4.4.2 (IT) |`
  - `| epocha/apps/agents/belief.py | §4.4.3 (EN) | §4.4.3 (IT) |`
  - `| epocha/apps/agents/affinity.py | §4.4.4 (EN) | §4.4.4 (IT) |`
  Copy updated file to live memory at `~/.claude/projects/-Users-mauriziomocci-Documents-workspace-Opensource-epocha/memory/feedback_whitepaper_doc_sync.md`.

### US4 checkpoint

- [ ] T049 [US4] Full pytest gate. Expected ≥804 (whitepaper/README/memory edits don't touch tests).
- [ ] T050 [US4] Commit `docs: promote rumor cluster from chapter 8.1 to chapter 4.4 after audit CONVERGED`. Stage: 2 whitepapers, 2 READMEs, doc-sync memory backup.

---

## Phase 8: Polish & Closure

**Purpose**: branch closure per Spec Kit conventions + frozen-at-commit pin.

- [ ] T051 [POLISH] Push branch: `git push -u origin 20260516-105818-rumor-cluster-audit-repass`.
- [ ] T052 [POLISH] Open draft PR via `\gh pr create --base develop --head 20260516-105818-rumor-cluster-audit-repass --title "fix(science): rumor cluster Round 2 audit CONVERGED + promote to whitepaper §4.4" --body "..."`. Body summarizes 16 findings closed + Round 3 verdict + whitepaper promotion + Spec Kit conformance.
- [ ] T053 [POLISH] `\gh pr merge <PR#> --merge --delete-branch`. Pull develop.
- [ ] T054 [POLISH] Frozen-at-commit pin: in `docs/whitepaper/epocha-whitepaper.md` and `.it.md`, replace 2 placeholders `<filled-on-merge>` in §4.4 status headers with the merge commit SHA from `\gh pr view <PR#> --json mergeCommit -q .mergeCommit.oid`. Commit `docs: pin rumor cluster §4.4 frozen-at-commit`. Push develop.
- [ ] T055 [POLISH] Update project memory: edit `~/.claude/projects/-Users-mauriziomocci-Documents-workspace-Opensource-epocha/memory/project_session_resume_2026_05_16.md` to mark rumor-cluster CLOSED + record next-step pointer to political-cluster branch. Sync to `docs/memory-backup/`. Commit `docs: mark rumor cluster session resume CLOSED + memory sync`. Push develop.

---

## Dependencies

| From | Blocks |
|------|--------|
| T001-T003 (SETUP) | all subsequent |
| T004-T006 (FOUND) | T034 (N-6 reads settings), T035 (N-5 delegates to helper) |
| T010 (extend keywords) | T012 (invariant test) |
| T014 (move sentiment call) | T015 (invariant test) |
| T012, T015 create test_rumor_invariants.py | T024 extends it |
| T017-T018 US1 done | T019+ US2 (can begin in parallel with US3 actually but sequential simpler) |
| T038 CONVERGED | T041+ US4 promotion |
| T050 commit | T051-T055 closure |

## Parallel Opportunities

- T021 and T022 ([P] EN and IT whitepaper §13 additions — different files)
- T027 and T028 ([P] EN and IT whitepaper §8.1 narrative correction)
- T046 and T047 ([P] EN and IT README status table)
- US2 and US3 fixes can interleave on different files (D-1 in distortion.py / N-7 in affinity.py / N-9 in information_flow.py) — but pytest gate between US blocks recommended for traceability.

## MVP Suggestion

US1 (T007-T018) IS the MVP: the 3 INCORRECT findings unblock whitepaper promotion path. Without US1 CONVERGED on those three, the promotion (US4) is blocked. US2+US3 can ship incrementally; US4 ships when all upstream CONVERGED.

## Format Validation

All 55 tasks above use the `- [ ] T<NNN> [TAG] description` checkbox format. Story tags map to `SETUP/FOUND/US1/US2/US3/US4/POLISH`. File paths absolute or repo-relative. Parallel markers `[P]` applied where independent.

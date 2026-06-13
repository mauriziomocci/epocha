---
description: "Tasks for factions audit re-pass — Round 1 catalogue to CONVERGED + chapter 4.7 promotion"
---

# Tasks: Factions Audit Re-pass (Round 2)

**Input**: Design documents from `specs/20260516-183045-factions-audit-repass/`

**Prerequisites**: spec.md (4 Round 1 findings → 4 user stories + optional US3), plan.md (Constitution Check PASS, no data-model/contracts/quickstart), research.md (Judge 2002 / Stogdill 1948 / Dunbar 1992 lookups closed with citation-rewrite text)

**Tests**: optional — no new tests are mandated for the doc-only R1 resolutions. Conditional regression tests under `test_factions.py` admitted only if Round 2 auditor flags concurrency or DRY issues. Pytest regression gate is mandatory.

**Organization**: tasks grouped by Spec user story. MVP = US1 (2 INCORRECT findings closed → unblocks promotion path). US2 + US3 + US4 incremental.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: parallel-safe (different files, no dependencies)
- **[Story]**: US1/US2/US3/US4/SETUP/FOUND/POLISH
- Absolute or repo-relative file paths

## Path Conventions

Django backend single project. Source at `epocha/apps/agents/factions.py`, tests at `epocha/apps/agents/tests/test_factions.py`, whitepaper at `docs/whitepaper/`.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: pre-flight verification before any fix.

- [ ] T001 [SETUP] Verify Docker compose stack up: `docker compose -f docker-compose.local.yml ps`. Start if needed with `docker compose -f docker-compose.local.yml up -d`. Confirm web container healthy via `docker compose -f docker-compose.local.yml exec -T web python -c "import django; print(django.get_version())"`.
- [ ] T002 [SETUP] Baseline pytest run: `docker compose -f docker-compose.local.yml exec -T web pytest 2>&1 | tail -5`. Record baseline count (expected ≥809 after Branch 4 closure). Pin the number in a scratch note for downstream gate comparisons.
- [ ] T003 [SETUP] Re-verify Round 1 finding code references still match develop @ `0afca1d`. Spot-check 7 critical line refs from spec.md: `factions.py:1-23` (module docstring "Scientific basis" header), `factions.py:43-49` (cohesion change coefficients comment with Baumeister attribution), `factions.py:55` (`_SCHISM_OUTWARD_SENTIMENT_THRESHOLD = -0.2`), `factions.py:58` (`_ALLY_SENTIMENT_THRESHOLD = 0.2`), `factions.py:96-117` (compute_leadership_score docstring with Stogdill + Judge citations), `factions.py:240-256` (update_group_cohesion docstring with Dunbar 1992 attribution at the size-penalty derivation), `factions.py:316-321` (cohesion delta formula with the 0.10/0.15/0.02/0.05 coefficients), `factions.py:465-468` (buried Known Limitation note on schism order-dependence). Also grep `docs/whitepaper/epocha-whitepaper.md` for existing Stogdill 1948 / Festinger 1950 / Olson 1965 / Axelrod 1984 / Baumeister 2001 §13 entries; record presence/absence of Judge 2002, Dunbar 1992, Weber 1922, Hackman 2002, Antonakis 2016, Zhou 2005. Record drift in a scratch note before proceeding.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: insert the shared Known Limitations substrate that F-1/F-2/F-3/F-4 disclaimers will forward-reference.

- [ ] T004 [FOUND] In `epocha/apps/agents/factions.py` module docstring (lines 1-23), add a dedicated "Known Limitations" subsection at the end of the docstring, before the closing `"""`, with four bullet placeholders that will be filled by US1/US2 tasks: `(a) Leadership weights (0.30/0.20/0.15/0.20/0.15) in compute_leadership_score are tunable design parameters consistent with Judge 2002 effect-size direction, not derived from them. See US1 / FR-001.\n(b) Size-penalty threshold of 5 in update_group_cohesion is a tunable design parameter; NOT derived from Dunbar 1992 (Dunbar's number is approximately 150; the 5 in Zhou et al. 2005 is the intimate-clique stratum, NOT a coordination cost boundary). See US1 / FR-002.\n(c) Cohesion delta coefficients (0.10 cooperation, 0.15 conflict, 0.02 size penalty, 0.05 leader effectiveness) are tunable design parameters; Baumeister 2001 grounds the qualitative DIRECTION of the conflict-over-cooperation asymmetry (negativity bias), NOT the specific 1.5:1 ratio. See US2 / FR-003.\n(d) Schism detection in _check_schism and cluster detection in _detect_and_propose_factions seed candidate splinter / cluster from the first agent in the queryset, making the result order-dependent. Overlapping potential schisms/clusters may exist; which one is detected depends on iteration order. A robust resolution would use graph-based connected-components or hierarchical clustering on the sentiment matrix — bound to a future "robust faction clustering" work item. See US2 / FR-004 / FR-005.`

**Checkpoint**: foundation ready. User stories can begin.

---

## Phase 3: User Story 1 — Close 2 INCORRECT findings on citation accuracy (Priority: P1) 🎯 MVP

**Goal**: rewrite the leadership-citation block (F-1) and the size-penalty Dunbar attribution (F-2) per research.md Lookup 1 and Lookup 3 text.

**Independent Test**: dispatch Round 2 `critical-analyzer` audit limited to F-1 and F-2; verdict CONVERGED for each. Run `docker compose -f docker-compose.local.yml exec -T web pytest epocha/apps/agents/tests/test_factions.py -v` to confirm no behavioral test depends on docstring text.

### F-1 — Leadership formula citation rewrite

- [ ] T005 [US1] In `epocha/apps/agents/factions.py` module docstring (lines 14-19), rewrite the "Scientific basis - Leadership emergence" clause to: `Leadership emergence: the trait-based scoring approach is grounded in Judge, Bono, Ilies, and Gerhardt (2002), "Personality and leadership: A qualitative and quantitative review", *Journal of Applied Psychology* 87(4):765-780, DOI 10.1037/0021-9010.87.4.765, which provides meta-analytic effect sizes for the Big Five trait-leadership relationship: Extraversion is the strongest correlate of leadership emergence (ρ ≈ 0.31), Conscientiousness (≈ 0.28), Openness (≈ 0.24), Neuroticism (≈ −0.24). Stogdill (1948), "Personal factors associated with leadership: A survey of the literature", *Journal of Psychology* 25(1):35-71, DOI 10.1080/00223980.1948.9917362, supports the broader principle that personal traits correlate with leadership emergence but does NOT propose a weighted-sum formula. Charisma is a Weberian sociological concept (Weber 1922) rather than a Stogdill trait correlate; its modern operationalization draws on Antonakis, Bastardoz, Jacquart, and Shamir (2016), "Charisma: An ill-defined and ill-measured gift", *Annual Review of Organizational Psychology and Organizational Behavior* 3:293-319, DOI 10.1146/annurev-orgpsych-041015-062305. The specific weights in compute_leadership_score (0.30/0.20/0.15/0.20/0.15) are tunable design parameters consistent with the direction of Judge 2002 effect sizes but not derived from them; see Known Limitations (a).`

- [ ] T006 [US1] In `epocha/apps/agents/factions.py` `compute_leadership_score()` docstring (around lines 111-116), rewrite the "Leadership emergence score" paragraph to: `Leadership emergence score. The trait-based scoring approach is grounded in Judge et al. (2002) meta-analytic effect sizes for the Big Five trait-leadership relationship (see module docstring "Scientific basis"). The five-component weighted formula (charisma 0.30, intelligence 0.20, wealth_rank 0.15, internal_sentiment 0.20, seniority 0.15) is consistent with the DIRECTION of those effect sizes (Extraversion strongest, then Conscientiousness, Openness, inverse Neuroticism) but the specific weights are tunable design parameters, not derived from the meta-analytic correlations. Stogdill (1948) is the original survey establishing the trait-correlate principle but did NOT propose a weighted-sum formula; charisma in particular is a Weberian concept (Weber 1922), not a Stogdill trait. See module Known Limitations (a).`

### F-2 — Size-penalty Dunbar attribution rewrite

- [ ] T007 [US1] In `epocha/apps/agents/factions.py` module docstring (lines 14-23), add a "Group cohesion size penalty" clause to the "Scientific basis" block (or extend the existing Group cohesion clause): `Group cohesion size penalty: coordination cost above a small-group threshold is a generic principle in organizational psychology (see Hackman 2002, "Leading Teams: Setting the Stage for Great Performances", Harvard Business School Press, ISBN 978-1-57851-333-1, for the argument that teams of 4-6 are typically the upper bound for fully-cohesive collaborative units before coordination overhead dominates). The specific threshold value of 5 in update_group_cohesion is a tunable design parameter; NOT derived from Dunbar 1992 (Dunbar's number is approximately 150 and addresses the cognitive limit on stable social relationships) nor from the nested-group hierarchy of Zhou, Sornette, Hill, and Dunbar (2005), "Discrete hierarchical organization of social group sizes", *Proc R Soc B* 272(1561):439-444, DOI 10.1098/rspb.2004.2970, in which the "5" is the innermost intimate-clique stratum (closest emotional ties) rather than a coordination cost boundary. See Known Limitations (b).`

- [ ] T008 [US1] In `epocha/apps/agents/factions.py` `update_group_cohesion()` docstring (around lines 246-252), rewrite the `size_penalty` derivation paragraph to: `size_penalty = max(0, member_count - 5): coordination cost above a small-group threshold. The threshold value 5 is a tunable design parameter consistent with Hackman 2002 "Leading Teams" (teams of 4-6 as the upper bound for fully-cohesive collaborative units before coordination overhead dominates) but NOT derived from Dunbar 1992 (cognitive limit on stable social relationships is approximately 150) nor from the Zhou et al. 2005 nested-hierarchy "5" stratum (intimate cliques, not coordination cost). See module Known Limitations (b).`

### US1 checkpoint

- [ ] T009 [US1] Targeted pytest: `docker compose -f docker-compose.local.yml exec -T web pytest epocha/apps/agents/tests/test_factions.py -v`. Expected all green (docstring-only edits; no behavior change).
- [ ] T010 [US1] Full pytest gate: `docker compose -f docker-compose.local.yml exec -T web pytest 2>&1 | tail -3`. Expected baseline.
- [ ] T011 [US1] Commit `docs(agents): close round 1 INCORRECT findings F-1 F-2 in factions docstring`. Stage only the touched file: `epocha/apps/agents/factions.py`.

---

## Phase 4: User Story 2 — Close 1 UNJUSTIFIED + 1 MISSING finding (Priority: P2)

**Goal**: reframe the cohesion-delta coefficients (F-3) and promote the schism order-dependence limitation to the module docstring (F-4). Doc-only resolutions per research.md Lookup 3.3 Option A precedent.

**Independent Test**: dispatch Round 2 audit subset on resolved file; verdict CONVERGED on F-3 and F-4.

### F-3 — Cohesion delta coefficients reframing

- [ ] T012 [US2] In `epocha/apps/agents/factions.py` (around lines 43-49, the `_CONFLICT_ACTIONS` comment block), rewrite the multi-line comment to: `# Actions considered conflictual (decrease cohesion).\n# Cohesion delta coefficients in update_group_cohesion (0.10 cooperation, 0.15 conflict, 0.02 size penalty, 0.05 leader effectiveness) are tunable design parameters. Baumeister, Bratslavski, Finkenauer, and Vohs (2001), "Bad is stronger than good", Review of General Psychology 5(4):323-370, DOI 10.1037/1089-2680.5.4.323, grounds the qualitative DIRECTION of the conflict-over-cooperation asymmetry (negative events have stronger psychological impact than positive events of equivalent magnitude). The specific 1.5:1 ratio between conflict and cooperation magnitudes, and the absolute values of all four coefficients, are NOT derived from Baumeister 2001 or any specific empirical fit; they are part of the simulation's calibration budget tied to tick frequency and the desired group-formation timescale. See module Known Limitations (c).`

- [ ] T013 [US2] In `epocha/apps/agents/factions.py` `update_group_cohesion()` docstring (around lines 240-256), rewrite the closing paragraph (currently citing Baumeister for the asymmetry) to: `The asymmetry (conflict has 1.5x the effect of cooperation) is consistent with the qualitative DIRECTION documented by Baumeister et al. (2001), "Bad is stronger than good", which shows that negative events have stronger psychological impact than positive events of equivalent magnitude. The specific 1.5:1 ratio and the absolute coefficient values (0.10, 0.15, 0.02, 0.05) are tunable design parameters per the simulation's calibration budget, NOT derived from Baumeister or any specific empirical fit. See module Known Limitations (c).`

### F-4 — Schism order-dependence promotion to docstring header

- [ ] T014 [US2] In `epocha/apps/agents/factions.py` `_check_schism()` (lines 465-468), replace the buried multi-line "Known limitation" comment block with a shortened single-line forward reference: `# Schism detection seeds from the first agent in the queryset (order-dependent). See module docstring "Known Limitations" (d).` The detailed explanation now lives in the module docstring Known Limitations block added by T004.

- [ ] T015 [US2] In `epocha/apps/agents/factions.py` `_detect_and_propose_factions()` (around the cluster-building loop near line 582), add a one-line comment immediately before the `for agent_a in candidates:` loop: `# Cluster detection seeds from the first agent in the queryset (order-dependent), same limitation as _check_schism. See module docstring "Known Limitations" (d).`

### US2 checkpoint

- [ ] T016 [US2] Full pytest gate: `docker compose -f docker-compose.local.yml exec -T web pytest 2>&1 | tail -3`. Expected baseline.
- [ ] T017 [US2] Commit `docs(agents): close round 1 UNJUSTIFIED F-3 and MISSING F-4 findings in factions module`. Stage: `epocha/apps/agents/factions.py`.

---

## Phase 5: User Story 3 — Optional Round 2 fresh-pass UNJUSTIFIED additions (Priority: P3, CONDITIONAL)

**Goal**: if the Round 2 audit (Phase 6) surfaces additional UNJUSTIFIED parameters beyond the R1 catalogue, address them with the same tunable-disclaimer pattern in a single commit. Scope ceiling: ≤3 new findings; escalate beyond.

**Note**: this phase runs AFTER Phase 6 audit dispatch. The audit verdict determines whether US3 has work to do. If no additional findings, US3 is closed with no commit.

- [ ] T018 [US3 conditional] If Round 2 auditor surfaces additional UNJUSTIFIED parameters (likely candidates: `_SCHISM_OUTWARD_SENTIMENT_THRESHOLD = -0.2`, `_ALLY_SENTIMENT_THRESHOLD = 0.2`, no-relationship fallback `0.3` at compute_leadership_score and compute_legitimacy, leaderless-group `-0.1`, leadership-transition penalty `-0.05`, splinter seed cohesion `0.5`, parent-cohesion-penalty `0.1`), add the tunable-disclaimer language inline at each parameter declaration AND extend the module docstring Known Limitations block with one additional bullet covering all the additions. Stage only `epocha/apps/agents/factions.py`.
- [ ] T019 [US3 conditional] Full pytest gate after additions: expected baseline.
- [ ] T020 [US3 conditional] Commit `docs(agents): close round 2 fresh-pass UNJUSTIFIED findings on factions tunable parameters`. If no additions, skip the commit and record "no-op, audit found no additional UNJUSTIFIED parameters" in the branch session log.

---

## Phase 6: Round 2 Adversarial Audit (Convergence Loop)

**Purpose**: per Constitution Principle III, re-audit before promotion. Loop until CONVERGED. Auditor mandate explicitly includes fresh-eyes pass beyond the R1 catalogue, plus concurrency / DRY / N+1 / bare-except checks per spec.md Edge Cases.

- [ ] T021 [US4 prep] Dispatch `critical-analyzer` subagent (Opus) for Round 2 audit on `epocha/apps/agents/factions.py` + `epocha/apps/agents/tests/test_factions.py`. Prompt includes: original 4 Round 1 findings (F-1 through F-4) + their resolution per US1+US2 commits; mandate to verify each R1 fix landed AND no new INCORRECT/UNJUSTIFIED introduced; explicit fresh-eyes mandate per Constitution III with ≤3 ceiling on new findings; concurrency check on `Group.cohesion`/`Group.leader`/`Agent.group`/`Memory` writes; DRY drift check against `affinity.py` (Branch 2 helper) and any reputation helper from Branch 1; bare `except Exception` discipline check; N+1 query pattern check in the per-group loop of `process_faction_dynamics()`; citation drift check against §13 bibliography. spec.md acceptance scenarios mapped to commits.
- [ ] T022 [US4 prep] If verdict NOT CONVERGED on R1 findings OR new findings ≤3: dispatch fix-implementer for residual findings with same lowest-risk strategy (US3 path); repeat T021. If new findings > 3: STOP and escalate to user. Expect ≤2 round-trips per Branch 1+2+3+4 precedent.
- [ ] T023 [US4 prep] When verdict CONVERGED: record Round 2 audit transcript hash or summary in a brief commit note (not a new file under `docs/superpowers/`; per Spec Kit rule). Audit transcript may be embedded as appendix in the future tasks-completion log.

---

## Phase 7: User Story 4 — Whitepaper §8.1 → §4.7 Promotion (Priority: P1)

**Goal**: campaign deliverable. Promote factions module from designed-pending to audited-Methods. Handle the §8 renumbering ripple in lock-step with internal cross-reference updates.

### Whitepaper EN promotion

- [ ] T024 [US4] In `docs/whitepaper/epocha-whitepaper.md`, REMOVE the `## 8.1 Factions` subsection (currently around line 1988-1992). Renumber subsequent `§8.x`: §8.2 Knowledge Graph → §8.1, §8.3 Economy base layer → §8.2. Grep the full document for `§8.1`, `§8.2`, `§8.3`, `8.1`, `8.2`, `8.3` references in body text (notably the §9 Roadmap around line 2012 and §10 Discussion around line 2064 which reference §8.x sections by number) and update all to the new numbering.
- [ ] T025 [US4] Insert new `§4.7` between current `§4.6 Movement` (around line 1739) and `§5 Implementation` of `docs/whitepaper/epocha-whitepaper.md`. Title: `## 4.7 Factions`. Status header: `> Status: implemented as of commit <filled-on-merge>, code audit CONVERGED 2026-05-16 round 2.`
- [ ] T026 [US4] §4.7 body — canonical Methods schema: Background (intra-faction dynamics covering cohesion, leadership emergence, leadership legitimacy, dissolution, schism, formation; conceptual anchor in Olson 1965 collective-action plus Festinger 1950 cohesion; the Iannaccone 1992 club-goods costly-signal mechanism is explicitly NOT implemented and is recorded as a deferred extension), Model (cohesion delta as weighted sum of cooperation, conflict, size penalty, leader effectiveness; leadership score as weighted sum of charisma, intelligence, wealth rank, internal sentiment, seniority; legitimacy as weighted sum of cohesion, leader sentiment, score rank), Equations (numbered following the existing §4.6.x sequence: cohesion_delta equation, leadership_score equation, legitimacy equation, schism trigger condition), Parameters table (cooperation/conflict/size/leader coefficients as tunable per F-3; leadership weights as tunable per F-1 with Judge 2002 direction-anchor; size penalty threshold as tunable per F-2 with Hackman 2002 generic-principle anchor; ally + outward sentiment thresholds; fallback sentiment values; leadership-transition and schism cohesion penalties; splinter seed cohesion), Algorithm (process_faction_dynamics orchestration + per-stage narrative summary of update_group_cohesion, update_group_leadership, _check_dissolution, _check_schism, _detect_and_propose_factions), Simplifications (F-1 weights as design choices not derived from Judge 2002; F-2 size threshold as design choice not derived from Dunbar 1992; F-3 cohesion coefficients tunable per calibration budget with Baumeister 2001 grounding qualitative direction only; F-4 schism + cluster detection order-dependent under greedy seed-first iteration with robust-clustering migration deferred; Iannaccone 1992 club-goods not implemented; faction-to-faction relationship modeling not implemented; LLM-driven identity generation covered by separate llm-adapter audit branch), Status header.
- [ ] T027 [US4] In §13 of `epocha-whitepaper.md`, verify (per T003 grep result) presence of Stogdill 1948, Festinger 1950, Olson 1965, Axelrod 1984, Baumeister 2001 entries. ADD Judge et al. 2002 entry with DOI `10.1037/0021-9010.87.4.765`. ADD Hackman 2002 entry with ISBN `978-1-57851-333-1`. CONDITIONALLY add Weber 1922 (English ed. Weber 1978, ISBN `978-0-520-03500-3`), Antonakis et al. 2016 (DOI `10.1146/annurev-orgpsych-041015-062305`), and Zhou et al. 2005 (DOI `10.1098/rspb.2004.2970`) per research.md Lookup 3.3 Option A. KEEP Dunbar 1992 entry (DOI `10.1016/0047-2484(92)90081-J`) with the explicit "NOT the source of the 5 threshold" disclaimer in the §4.7 narrative per Option A.

### Whitepaper IT mirror

- [ ] T028 [US4] Mirror T024 in `docs/whitepaper/epocha-whitepaper.it.md`: remove §8.1 Fazioni IT, renumber §8.2-§8.3 → §8.1-§8.2, update all internal §8.x cross-references in §9 Roadmap and §10 Discussione body text.
- [ ] T029 [US4] Mirror T025+T026+T027 in IT: insert `## 4.7 Fazioni` with the canonical Methods schema translated, equation numbering identical to EN; mirror §13 bibliography additions per T027. Status header in IT: `> Stato: implementato a partire dal commit <filled-on-merge>, audit del codice CONVERGENTE 2026-05-16 round 2.`

### README EN+IT status table + doc-sync memory

- [ ] T030 [US4] [P] In `README.md` Status table flip the factions row to `yes (CONVERGED 2026-05-16 round 2)`. Mirror in `README.it.md` with `sì (CONVERGENTE 2026-05-16 round 2)`. In `docs/memory-backup/feedback_whitepaper_doc_sync.md` mapping table add 1 row: `| epocha/apps/agents/factions.py | §4.7 (EN) | §4.7 (IT) |`. Copy updated file to live memory at `~/.claude/projects/-Users-mauriziomocci-Documents-workspace-Opensource-epocha/memory/feedback_whitepaper_doc_sync.md`.

### US4 checkpoint

- [ ] T031 [US4] Full pytest gate. Expected baseline (whitepaper/README/memory edits don't touch tests).
- [ ] T032 [US4] Commit `docs: promote factions from chapter 8.1 to chapter 4.7 after audit CONVERGED`. Stage: 2 whitepapers, 2 READMEs, doc-sync memory backup.

---

## Phase 8: Polish & Closure

**Purpose**: branch closure per Spec Kit conventions + frozen-at-commit pin.

- [ ] T033 [POLISH] Push branch: `git push -u origin 20260516-183045-factions-audit-repass`.
- [ ] T034 [POLISH] Open draft PR via `gh pr create --base develop --head 20260516-183045-factions-audit-repass --title "fix(science): factions Round 2 audit CONVERGED + promote to whitepaper §4.7" --body "..."`. Body summarizes 4 Round 1 findings closed + optional US3 verdict + Round 2 verdict + whitepaper promotion + §8 renumbering ripple + Spec Kit conformance.
- [ ] T035 [POLISH] `gh pr merge <PR#> --merge --delete-branch`. Pull develop.
- [ ] T036 [POLISH] Frozen-at-commit pin: in `docs/whitepaper/epocha-whitepaper.md` and `.it.md`, replace 2 placeholders `<filled-on-merge>` in §4.7 status headers with the merge commit SHA from `gh pr view <PR#> --json mergeCommit -q .mergeCommit.oid`. Commit `docs: pin factions §4.7 frozen-at-commit`. Push develop.
- [ ] T037 [POLISH] Update project memory: edit `~/.claude/projects/-Users-mauriziomocci-Documents-workspace-Opensource-epocha/memory/project_session_resume_2026_05_16.md` to mark factions CLOSED + record next-step pointer to Knowledge Graph branch. Sync to `docs/memory-backup/`. Commit `docs: mark factions session resume CLOSED + memory sync`. Push develop.

---

## Dependencies

| From | Blocks |
|------|--------|
| T001-T003 (SETUP) | all subsequent |
| T004 (FOUND Known Limitations stub) | T005-T015 (all US1 + US2 disclaimers forward-reference the stub) |
| T011 US1 commit | T012+ US2 (sequential simpler; same file) |
| T017 US2 commit | T021+ Phase 6 audit dispatch |
| T021/T023 CONVERGED | T024+ US4 promotion |
| T021/T022 audit findings | T018+ US3 (conditional) |
| T032 promotion commit | T033-T037 closure |

## Parallel Opportunities

- T030 has internal parallel-safe steps (EN README, IT README, doc-sync memory — three different files) but they are bundled in one commit; safe to perform in any order within the task.
- US1 and US2 disclaimers are on the same file (`factions.py`); sequential execution is safer to avoid merge friction. T012-T015 in particular touch adjacent line ranges and benefit from sequential edits.
- T028 (IT whitepaper mirror) can in principle run in parallel with T024-T027 (EN whitepaper), but the §8 renumbering ripple requires the EN to be settled first to confirm the new section numbers; sequential execution recommended.

## MVP Suggestion

US1 (T005-T011) IS the MVP: the 2 INCORRECT findings unblock the whitepaper promotion path. Without US1 CONVERGED on F-1 and F-2, the promotion (US4) is blocked. US2 closes F-3+F-4 doc-only and may ship incrementally; US3 is conditional on auditor verdict; US4 ships when all upstream CONVERGED.

## Format Validation

All 37 tasks above use the `- [ ] T<NNN> [TAG] description` checkbox format. Story tags map to `SETUP/FOUND/US1/US2/US3/US4/POLISH`. File paths absolute or repo-relative. Parallel markers `[P]` applied where independent.

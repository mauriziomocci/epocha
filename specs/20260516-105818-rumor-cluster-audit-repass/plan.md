# Implementation Plan: Rumor Cluster Audit Re-pass (Round 2)

**Branch**: `20260516-105818-rumor-cluster-audit-repass` | **Date**: 2026-05-16 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/20260516-105818-rumor-cluster-audit-repass/spec.md`

## Summary

Close 16 Round 2 adversarial audit findings (3 INCORRECT, 9 UNJUSTIFIED, 4 INCONSISTENT) on the rumor propagation cluster (`epocha/apps/agents/{information_flow,distortion,belief,affinity}.py`) accumulated since the 2026-04-12 audit. Sequence: behavioral fixes first (INCORRECT findings unblock promotion), then INCONSISTENT remediation including 4 missing §13 citations and an invariant test suite, then UNJUSTIFIED documentation upgrades and minor refactors. After Round 3 adversarial audit reaches CONVERGED verdict, promote `§8.1` → `§4.4` in the bilingual whitepaper following the standard procedure documented in project memory `project_whitepaper_promotion_pipeline.md`.

## Technical Context

**Language/Version**: Python 3.12

**Primary Dependencies**: Django 5.x, Django Channels, Celery, PostgreSQL, Redis, scipy (for HP fitting elsewhere; not used in this cluster)

**Storage**: PostgreSQL via Django ORM. No schema migration expected unless IF-4 fix opts to add `hop_count` field on `Memory` model (escalation required per spec Edge Cases).

**Testing**: pytest, executed inside the `epocha-web-1` container via `docker compose -f docker-compose.local.yml exec -T web pytest`. Current baseline 801 passed.

**Target Platform**: Docker Compose local development stack; production target Linux Kubernetes.

**Project Type**: Django backend with Celery async workers and Django Channels WebSocket layer. Audit re-pass touches only the agents app and cross-module reputation+simulation integration; no frontend/mobile/API contract changes.

**Performance Goals**: No new performance requirement introduced; cluster fix must NOT regress current tick throughput.

**Constraints**: No new external runtime dependency. No `pytest.mark.skip` without traceable rationale (Constitution Principle V). Whitepaper §4.4 promotion blocked until Round 3 CONVERGED.

**Scale/Scope**: 4 files (`information_flow.py` 346 LOC, `distortion.py` 272 LOC, `belief.py` 99 LOC, `affinity.py` 238 LOC = 955 LOC); 1 cross-module file (`reputation.py` for N-1/N-3/N-5 helpers); 1 test directory expansion (`tests/test_rumor_invariants.py` new); bilingual whitepaper EN+IT promotion edits; README EN+IT status table; doc-sync memory; 4 new §13 citations.

## Constitution Check

Compliance map per `.specify/memory/constitution.md` v1.0.0:

- **Principle I (Scientific Method Above All)**: PASS — every fix must produce a verified citation, a documented tunable parameter, or a documented known limitation. The 4 §13 citations (Mayer 1995, Graziano-Tobin 2002, Castelfranchi-Falcone-Tan 1998, McCrae-Costa 2003) must be DOI-verified via Crossref before commit.
- **Principle II (Verify Before Asserting)**: PASS — every file path, function signature, line range in spec.md was verified on develop @ `19279a1`. The plan tasks must re-verify before each fix-implementer dispatch to catch any drift from Round 2 audit date (2026-05-12) to fix execution.
- **Principle III (Adversarial Scientific Audit)**: PASS — Round 3 audit dispatch via `critical-analyzer` is mandatory before promotion. Convergence loop: audit → fix → re-audit → CONVERGED, or repeat.
- **Principle IV (Three-Step Design Process)**: PASS — spec.md is the consolidated output of Round 2 audit + controller-side re-review (this plan is the third step's consequence, not a new design iteration).
- **Principle V (Evidence-Based Verification)**: PASS — pytest gate at every fix commit (baseline 801, expected ≥802 with N-10 invariants). No bug-discipline shortcuts.

**GATE: PASS**. No constitutional violations require justification in the Complexity Tracking section below.

## Project Structure

### Documentation (this feature)

```text
specs/20260516-105818-rumor-cluster-audit-repass/
├── spec.md         # Feature spec (16 findings → 4 user stories + 12 FR + 8 SC) — already authored
├── plan.md         # This file
├── research.md     # Phase 0 output — limited scope, this branch is fix not new feature
├── data-model.md   # NOT APPLICABLE — no new entities; potential Memory.hop_count field deferred to escalation
├── contracts/      # NOT APPLICABLE — no external interfaces touched
├── quickstart.md   # NOT APPLICABLE — fix branch, no new user onboarding
└── tasks.md        # Phase 2 output (/speckit-tasks)
```

### Source Code (repository root)

```text
epocha/apps/agents/
├── information_flow.py     # Touched: IF-1 (doc), IF-4 (doc), IF-5 (behavior dedup), N-6 (settings), N-9 (doc), N-1 partial
├── distortion.py           # Touched: D-1 (doc reconcile), D-4 (doc), D-5 (doc), N-3 (behavior reorder), N-4 (doc)
├── belief.py               # Touched: N-2 (citations to §13), N-5 (refactor delegate to _normalize_reputation)
├── affinity.py             # Touched: N-2 (citation to §13), N-7 (doc), N-8 (doc or cite)
├── reputation.py           # Touched: N-1 (extend _IMAGE_DELTAS keyword coverage OR structured parsing), N-5 (extract _normalize_reputation helper)
└── tests/
    ├── test_information_flow.py   # Possibly extended for IF-5 invariant
    ├── test_distortion.py         # Possibly extended for D-1 reconcile assertion
    ├── test_belief.py             # Possibly extended for N-5 invariant
    ├── test_affinity.py           # Possibly extended for N-7 invariant
    └── test_rumor_invariants.py   # NEW — N-10 invariant suite: vocabulary alignment (N-1), distortion-independent reputation (N-3), more as deemed enforceable

config/settings/
├── base.py                 # Touched: N-6 add EPOCHA_INFO_FLOW_WEAK_RUMOR_WEIGHT, EPOCHA_INFO_FLOW_WEAK_RUMOR_DAMP

docs/whitepaper/
├── epocha-whitepaper.md      # Touched at promotion: §8.1 removal, §4.4 4-sub-section chapter, 4 new §13 entries (Mayer, Graziano-Tobin, Castelfranchi-Falcone-Tan, McCrae-Costa)
└── epocha-whitepaper.it.md   # Mirror

README.md, README.it.md      # Status table 4 rows flipped to CONVERGED

docs/memory-backup/
├── feedback_whitepaper_doc_sync.md   # 4 new mapping rows
└── (plus live sync to ~/.claude/projects/.../memory/)
```

**Structure Decision**: existing Django project layout. No new top-level directories. New file `epocha/apps/agents/tests/test_rumor_invariants.py` lives alongside existing per-module test files. Whitepaper edits per `project_whitepaper_promotion_pipeline.md` standard procedure.

## Complexity Tracking

No constitutional violations to justify. The branch is pure remediation + documentation promotion, no architectural change.

## Phase 0 — Research

The Round 2 audit (2026-05-12, full report in `project_session_resume_2026_05_12.md`) IS the research output for this branch. No additional research dispatches required. Three minor lookups deferred to Phase 5 task execution:

1. **Crossref DOI verification** for 4 missing §13 citations:
   - Mayer, R. C., Davis, J. H., & Schoorman, F. D. (1995). "An Integrative Model of Organizational Trust", AMR 20(3), 709-734, DOI `10.5465/amr.1995.9508080335`.
   - Graziano, W. G., & Tobin, R. M. (2002). "Agreeableness: Dimension of Personality or Social Desirability Artifact?", JPSP 70(5), 695-727 OR Journal of Personality 70(5), 695-727 (verify exact venue) — DOI `10.1111/1467-6494.05021`.
   - Castelfranchi, C., Falcone, R., & Tan, Y.-H. (1998). "The Role of Trust and Deception in Virtual Societies", HICSS-31 proceedings, IEEE.
   - McCrae, R. R., & Costa, P. T. (2003). *Personality in Adulthood: A Five-Factor Theory Perspective*, 2nd ed., Guilford Press, ISBN 978-1-57230-827-2.

2. **N-8 design-rationale citation candidate**: Coleman, J. S. (1990) *Foundations of Social Theory*, Belknap/Harvard (ISBN 978-0-674-31226-5) OR Axelrod, R. (1984) *The Evolution of Cooperation* (already in §13). Verify which best supports rival-coalition design.

3. **N-3 fix verification**: before moving `extract_action_sentiment` call before distortion pass, verify no downstream consumer in `information_flow.py` relies on the post-distortion sentiment value for any purpose other than reputation update. Quick grep + inspection.

**Output**: `research.md` documents the three lookups inline (no separate research dispatches required).

## Phase 1 — Design & Contracts

### Data Model

NOT APPLICABLE for the lowest-risk path. If IF-4 fix chooses to add `hop_count` PositiveSmallIntegerField on `Memory` model, this requires:
1. Migration `agents/migrations/00NN_memory_hop_count.py`
2. Default value handling for existing memories (backfill 0 or null)
3. Update `_propagate_memory` to increment on creation
4. Update `_estimate_hop` to read directly

Decision: **defer to escalation**. Per spec.md Edge Case "Backward compatibility on Memory model", IF-4 documentation-only resolution is acceptable. Plan tasks proceed with documentation-only fix for IF-4 unless user re-escalates.

### Contracts

NOT APPLICABLE. No new external interfaces. Existing `update_image`, `update_reputation`, `extract_action_sentiment` signatures unchanged.

### Agent Context Update

CLAUDE.md SPECKIT marker block already references the Spec Kit adoption rule (committed in `2b436ec`). Update the IMPL_PLAN reference between the `<!-- SPECKIT START -->` and `<!-- SPECKIT END -->` markers in CLAUDE.md to point to this plan file:

`specs/20260516-105818-rumor-cluster-audit-repass/plan.md`

This update happens in tasks.md execution, not here.

### Quickstart

NOT APPLICABLE for fix branch. Quickstart for onboarding new contributors lives in README, not per-feature.

## Re-evaluation of Constitution Check (post-design)

All 5 principles still PASS. No new violations introduced by the design phase. The deferred-to-escalation IF-4 `hop_count` decision is recorded in Phase 1 Data Model section as the only point where Principle V (Evidence-Based Verification) could be challenged if user later requests behavioral fix — in which case escalate and re-plan.

**GATE: PASS**.

## Phase 2 — Tasks (generated separately by `/speckit-tasks`)

The tasks.md file will be produced from this plan + spec.md by the `/speckit-tasks` workflow. Expected task structure:

| Block | Task count estimate |
|-------|---------------------|
| Phase 0 prep: Crossref DOI verification + N-3 grep | 3 tasks |
| INCORRECT fixes (US1): IF-5, N-1, N-3 | 6-8 tasks (each finding has fix + verify) |
| INCONSISTENT fixes (US2): D-1, N-2 (4 citations), N-4, N-10 (invariant tests) | 8-10 tasks |
| UNJUSTIFIED fixes (US3): IF-1, IF-4, D-4, D-5, N-5, N-6, N-7, N-8, N-9 | 9-12 tasks |
| Pytest gate after each fix block | 4 tasks |
| Round 3 adversarial audit dispatch + loop | 2-4 tasks (1 dispatch + 1-3 fix rounds if NOT CONVERGED) |
| Whitepaper §8.1 → §4.4 EN promotion + IT mirror + §13 4 citations | 4 tasks |
| README EN+IT status table update | 2 tasks |
| Doc-sync memory mapping (4 rows EN+IT) + live sync | 1 task |
| Branch closure: final pytest + push + draft PR + merge + frozen-at-commit pin | 4 tasks |

**Total estimate**: 43-52 tasks. Granularity: 2-5 min per task per Constitution Principle V / `feedback_task_breakdown_mandatory.md` legacy memory.

## Stop Conditions / Escalation

Per Spec Kit `/speckit-plan` skill: command ends after Phase 2 planning. The plan is complete; tasks.md is the next deliverable produced by `/speckit-tasks`.

Escalation triggers during downstream task execution (Constitution Principle II):
- Plan-quoted function signature does not match actual code (re-verify before fix-implementer dispatch).
- Round 2 finding remediation requires Memory model migration → STOP, ask user.
- Round 3 audit produces > 5 new findings (scope explosion) → STOP, re-plan.
- Pytest baseline shifts unexpectedly (not 801 ± 1) → STOP, diagnose before continuing.

## Generated Artifacts

After `/speckit-plan` completes successfully:
- `specs/20260516-105818-rumor-cluster-audit-repass/plan.md` — this file
- `specs/20260516-105818-rumor-cluster-audit-repass/research.md` — Crossref DOI verification log + N-8 candidate decision + N-3 grep result

`data-model.md`, `contracts/`, `quickstart.md` are intentionally NOT generated (NOT APPLICABLE per Phase 1 above).

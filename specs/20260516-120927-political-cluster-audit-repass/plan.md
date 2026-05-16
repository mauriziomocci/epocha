# Implementation Plan: Political Cluster Audit Re-pass (Round 2)

**Branch**: `20260516-120927-political-cluster-audit-repass` | **Date**: 2026-05-16 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/20260516-120927-political-cluster-audit-repass/spec.md`

## Summary

Close 20 Round 1 adversarial audit findings (5 INCORRECT, 12 UNJUSTIFIED, 2 INCONSISTENT, 1 MISSING) on the political institutions cluster (`epocha/apps/world/{government,government_types,stratification,election,institutions}.py`) accumulated since the 2026-04-12 audit. A spot-check of develop @ `1c75854` (post Branch 2 closure) confirms that several Round 1 findings have already been partially or fully remediated by interim commits (G-2 coup already stochastic, E-2 dead code already removed by Branch 1, E-5 voter-count caching already applied, X-1 layering inline-documented, S-3 Miller-Lynam already cited inline, S-4 docstring already explains loss-aversion ratio). Round 2 work consists of: (a) explicit verification of pre-remediated findings, (b) closure of residual gaps, (c) behavioral fix for S-2 wealth-conservation invariant (the only finding requiring a substantive code change), (d) systematic citation cleanup, (e) one new invariant test file, and (f) promotion of the cluster to whitepaper §4.5 after Round 2 CONVERGED.

Sequence: behavioral fix first (S-2 unblocks invariant test), then INCORRECT cleanup, then INCONSISTENT documentation, then UNJUSTIFIED grouped refactor, Round 2 audit dispatch, then §8.1 → §4.5 promotion in bilingual whitepaper following the standard procedure documented in project memory `project_whitepaper_promotion_pipeline.md`.

## Technical Context

**Language/Version**: Python 3.12

**Primary Dependencies**: Django 5.x, Django Channels, Celery, PostgreSQL, Redis. No new dependencies introduced. The S-2 wealth-conservation fix uses the existing `random` standard library and Django ORM transaction primitives.

**Storage**: PostgreSQL via Django ORM. No schema migration expected — `World.global_wealth` is an existing field; the FR-009 fix only changes the value written, not the schema.

**Testing**: pytest, executed inside the `epocha-web-1` container via `docker compose -f docker-compose.local.yml exec -T web pytest`. Baseline measured at T002 of tasks.md (expected ≥804 after Branch 2 closure).

**Target Platform**: Docker Compose local development stack; production target Linux Kubernetes.

**Project Type**: Django backend with Celery async workers and Django Channels WebSocket layer. Audit re-pass touches only the world app and one new test file; no frontend/mobile/API contract changes.

**Performance Goals**: No new performance requirement. The S-2 fix adds one in-transaction write to `World.global_wealth` per corrupt-agent skim — negligible impact at expected agent counts.

**Constraints**: No new external runtime dependency. No `pytest.mark.skip` without traceable rationale (Constitution Principle V). Whitepaper §4.5 promotion blocked until Round 2 CONVERGED.

**Scale/Scope**: 5 source files (`government.py` 786 LOC, `government_types.py` 449 LOC, `stratification.py` 326 LOC, `election.py` 245 LOC, `institutions.py` 111 LOC = 1917 LOC); 1 new test file (`tests/test_political_invariants.py`); 5 existing test files extended where needed; bilingual whitepaper EN+IT promotion edits; README EN+IT status table; doc-sync memory; up to 4 new §13 citations (Weber 1922 pre-DOI, Merolla-Zechmeister 2011 DOI, Miller-Lynam 2001 DOI, optional Bass 1985 pre-DOI).

## Constitution Check

Compliance map per `.specify/memory/constitution.md` v1.0.0:

- **Principle I (Scientific Method Above All)**: PASS — every fix must produce a verified citation, a documented tunable parameter, or a documented known limitation. The Weber/Merolla-Zechmeister/Miller-Lynam citations are DOI-verified via Crossref in research.md.
- **Principle II (Verify Before Asserting)**: PASS — every file path, function signature, line range, and pre-remediated state in spec.md was verified on develop @ `1c75854` via direct code reading and grep. The plan tasks must re-verify before each fix-implementer dispatch to catch any drift from Round 1 audit date (2026-04-12) to fix execution.
- **Principle III (Adversarial Scientific Audit)**: PASS — Round 2 audit dispatch via `critical-analyzer` is mandatory before promotion. Convergence loop: audit → fix → re-audit → CONVERGED, or repeat.
- **Principle IV (Three-Step Design Process)**: PASS — spec.md is the consolidated output of the Round 1 audit catalogue + controller-side re-review (this plan is the third step's consequence, not a new design iteration).
- **Principle V (Evidence-Based Verification)**: PASS — pytest gate at every fix commit (baseline measured at T002, expected ≥805 with FR-021 invariants added). No bug-discipline shortcuts.

**GATE: PASS**. No constitutional violations require justification in the Complexity Tracking section below.

## Project Structure

### Documentation (this feature)

```text
specs/20260516-120927-political-cluster-audit-repass/
├── spec.md         # Feature spec (20 findings → 4 user stories + 25 FR + 8 SC) — already authored
├── plan.md         # This file
├── research.md     # Phase 0 output — 4 lookups (E-1 citation pair, S-3 alt cite, X-1 decision, G-2 fix safety)
├── data-model.md   # NOT APPLICABLE — no new entities; S-2 fix uses existing World.global_wealth field
├── contracts/      # NOT APPLICABLE — no external interfaces touched
├── quickstart.md   # NOT APPLICABLE — fix branch, no new user onboarding
└── tasks.md        # Phase 2 output
```

### Source Code (repository root)

```text
epocha/apps/world/
├── government.py             # Touched: G-1 (doc Powell-Thyne), G-2 (verify + opt-remove constant), G-3 (doc 0.05), G-5 (doc legitimacy weights), G-6 (rename or doc economy var), X-1 (verify inline Note sufficiency)
├── government_types.py       # Touched: G-4 (remove Polity IV Table 3), GT-1 (verify module disclaimer covers all 4 dicts)
├── stratification.py         # Touched: S-1 (doc Gilbert simplification), S-2 (BEHAVIOR fix wealth conservation), S-3 (doc threshold tunable + verify Miller-Lynam cite), S-4 (verify loss-aversion ratio docstring), X-1 (mirror Note at process_corruption)
├── election.py               # Touched: E-1 (replace Zonis with Weber+Merolla-Zechmeister), E-3 (doc vote weights), E-4 (doc wealth cap), E-5 (verify already cached), E-2 (verify dead code absent)
├── institutions.py           # Touched: I-1 (doc 20.0 timescale), I-2 (remove Gupta cite), I-3 (verify linear-decay docstring)
└── tests/
    ├── test_government.py            # Possibly extended for G-1/G-2 verification asserts
    ├── test_stratification.py        # Extended for S-2 wealth conservation
    ├── test_election.py              # Possibly extended for E-1 citation presence check
    ├── test_institutions.py          # Possibly extended for I-1/I-3 invariant
    └── test_political_invariants.py  # NEW — FR-021 wealth conservation invariant + optional _COUP_SUCCESS_THRESHOLD absence check

docs/whitepaper/
├── epocha-whitepaper.md      # Touched at promotion: §8.1 removal + renumbering, new §4.5 chapter (5 sub-sections), up to 4 new §13 entries
└── epocha-whitepaper.it.md   # Mirror

README.md, README.it.md       # Status table 5 rows flipped to CONVERGED

docs/memory-backup/
├── feedback_whitepaper_doc_sync.md   # 5 new mapping rows
└── (plus live sync to ~/.claude/projects/.../memory/)
```

**Structure Decision**: existing Django project layout. No new top-level directories. New file `epocha/apps/world/tests/test_political_invariants.py` lives alongside existing per-module test files. Whitepaper edits per `project_whitepaper_promotion_pipeline.md` standard procedure.

## Complexity Tracking

No constitutional violations to justify. The branch is pure remediation + documentation promotion, with a single behavioral fix (S-2 wealth conservation) bounded to one function and one in-transaction write.

## Phase 0 — Research

The Round 1 audit (2026-04-12, transcript in `docs/scientific-audit-2026-04-12.md`) IS the substantive research input for this branch. Four lookups required, documented in `research.md`:

1. **Crossref DOI verification** for E-1 candidate citations (Weber 1922 pre-DOI; Merolla-Zechmeister 2011 `10.1177/0010414010381076`; Bass 1985 pre-DOI).

2. **Crossref DOI verification** for S-3 alternative citation Miller-Lynam 2001 `10.1111/j.1745-9125.2001.tb00940.x`.

3. **X-1 design decision**: unify corruption-update path OR document layering. Recommended decision: document the layering as deliberate co-existence (institutional vs personality semantics are distinct; unification would lose analytical clarity). Verify inline `Note` at `government.py:339-342` and add a mirror note at `stratification.py:process_corruption`.

4. **G-2 fix-safety**: verify no existing test asserts the deterministic threshold-comparison behavior. Grep result: only the deprecated constant declaration matches; the actual code path already uses `random.random() < success_probability`. G-2 is ALREADY FIXED on develop @ `1c75854`. Round 2 verification + optional dead-constant removal.

**Output**: `research.md` documents all four lookups with decisions and rationale.

## Phase 1 — Design & Contracts

### Data Model

NOT APPLICABLE. No new entities; no schema migration. The S-2 wealth-conservation fix writes to the existing `World.global_wealth` field which is already touched by `process_corruption` (currently only read at line 277-278 — the fix makes the write symmetric).

### Contracts

NOT APPLICABLE. No new external interfaces. Existing `check_coups`, `process_corruption`, `update_government_indicators`, `_update_stability`, `update_institution_health` signatures unchanged.

### Agent Context Update

CLAUDE.md SPECKIT marker block already references the Spec Kit adoption rule (committed in `2b436ec`). The IMPL_PLAN reference between the `<!-- SPECKIT START -->` and `<!-- SPECKIT END -->` markers in CLAUDE.md should point to this plan file:

`specs/20260516-120927-political-cluster-audit-repass/plan.md`

This update happens in tasks.md execution if the marker is currently stale, not here.

### Quickstart

NOT APPLICABLE for fix branch. Quickstart for onboarding new contributors lives in README, not per-feature.

## Re-evaluation of Constitution Check (post-design)

All 5 principles still PASS. No new violations introduced by the design phase. The X-1 documentation-only resolution is recorded as the design decision in Phase 1 Lookup 3 above as the only point where Principle V (Evidence-Based Verification) could be challenged if a future auditor demands unification — in which case escalate and re-plan as a separate spec.

**GATE: PASS**.

## Phase 2 — Tasks (generated separately by `/speckit-tasks`)

The tasks.md file will be produced from this plan + spec.md by the `/speckit-tasks` workflow. Expected task structure:

| Block | Task count estimate |
|-------|---------------------|
| Phase 1 setup: docker, baseline pytest, code-drift verification | 3 tasks |
| Phase 2 foundational: new invariant test file scaffold + S-2 behavioral fix (the only finding-shared prereq) | 3-4 tasks |
| Phase 3 US1 (5 INCORRECT verifications + minor doc fixes): G-1, G-2, S-1, S-2, E-1, E-2-verify | 10-12 tasks |
| Phase 4 US2 (2 INCONSISTENT verifications): E-5-verify, X-1-doc | 3-4 tasks |
| Phase 5 US3 (12 UNJUSTIFIED + 1 MISSING): G-3, G-4, G-5, G-6, GT-1, S-3, S-4, E-3, E-4, I-1, I-2, I-3 + invariant tests | 14-18 tasks |
| Phase 6 Round 2 adversarial audit dispatch + convergence loop | 2-4 tasks |
| Phase 7 US4 whitepaper §8.1 → §4.5 promotion + IT mirror + 5 README/memory updates | 10-12 tasks |
| Phase 8 polish & closure: push, draft PR, merge, frozen-pin, session memory | 5 tasks |

**Total estimate**: 50-60 tasks. Granularity: 2-5 min per task per Constitution Principle V / `feedback_task_breakdown_mandatory.md` legacy memory.

## Stop Conditions / Escalation

Per Spec Kit `/speckit-plan` skill: command ends after Phase 2 planning. The plan is complete; tasks.md is the next deliverable produced by `/speckit-tasks`.

Escalation triggers during downstream task execution (Constitution Principle II):
- Plan-quoted function signature or line range does not match actual code (re-verify before fix-implementer dispatch).
- S-2 wealth-conservation fix requires touching transaction boundary or model layer → STOP, ask user.
- Round 2 audit produces > 5 new findings (scope explosion) → STOP, re-plan.
- Pytest baseline shifts unexpectedly (not measured-baseline ± 1) → STOP, diagnose before continuing.
- X-1 auditor verdict insists on unification → STOP, escalate as separate spec.

## Generated Artifacts

After `/speckit-plan` completes successfully:
- `specs/20260516-120927-political-cluster-audit-repass/plan.md` — this file
- `specs/20260516-120927-political-cluster-audit-repass/research.md` — 4-lookup record

`data-model.md`, `contracts/`, `quickstart.md` are intentionally NOT generated (NOT APPLICABLE per Phase 1 above).

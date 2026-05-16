# Implementation Plan: Movement Audit Re-pass (Round 2)

**Branch**: `20260516-165137-movement-audit-repass` | **Date**: 2026-05-16 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/20260516-165137-movement-audit-repass/spec.md`

## Summary

Close 5 Round 1 adversarial audit findings (2 INCORRECT, 1 INCONSISTENT, 2 UNJUSTIFIED) on the movement module (`epocha/apps/agents/movement.py`) accumulated since the 2026-04-12 audit. A spot-check of develop @ `9d59037` (post Branch 3 closure) confirms that several Round 1 findings have already been partially or fully remediated by interim commits (commit `17f046a` reduced foot from 35 to 25 km/day and carriage from 80 to 60 km/day; the terrain block already carries a partial disclaimer; the arrival-scatter constant already documents the 100-unit zone-boundary assumption; the coordinate convention is acknowledged in a `Note` block in the module docstring). Round 2 work consists of: (a) explicit verification of pre-remediated findings, (b) closure of residual documentation gaps (notably the module docstring header which still describes the speeds without distinguishing the Chandler military rate from the Braudel civilian rate, and the coordinate convention block which acknowledges the simplification but does not enumerate the downstream consumers or the impact on real WGS84 data), (c) optional invariant test extension for the speed-ordering contract, and (d) promotion of the module to whitepaper §4.6 after Round 2 CONVERGED.

Sequence: documentation refinements first (no behavioral fixes mandated), Round 2 audit dispatch, then §8.1 → §4.6 promotion in bilingual whitepaper following the standard procedure documented in project memory `project_whitepaper_promotion_pipeline.md`. The §8 renumbering ripple (Movement removed; Factions, Knowledge Graph, Economy base layer shifted up by one slot) is handled in the promotion phase, in lock-step with internal cross-reference updates in §9 and §10.

## Technical Context

**Language/Version**: Python 3.12

**Primary Dependencies**: Django 5.x, Django Channels, Celery, PostgreSQL with PostGIS, Redis. No new dependencies introduced. The M-3 coordinate-convention resolution is documentation-only; no `pyproj` or projected-distance library is added.

**Storage**: PostgreSQL via Django ORM with PostGIS extension. No schema migration expected — `Agent.location`, `Zone.center`, `Zone.boundary` retain their existing `srid=4326` declarations; the FR-004 fix only documents the current grid-coordinate convention. The behavioral fix path for M-3 (real WGS84 + great-circle distance) is bound to the broader-PostGIS roadmap item, not to this branch.

**Testing**: pytest, executed inside the `epocha-web-1` container via `docker compose -f docker-compose.local.yml exec -T web pytest`. Baseline measured at T002 of tasks.md (expected ≥809 after Branch 3 closure).

**Target Platform**: Docker Compose local development stack; production target Linux Kubernetes.

**Project Type**: Django backend with Celery async workers and Django Channels WebSocket layer. Audit re-pass touches only the agents app (one source file and its test companion); no frontend/mobile/API contract changes.

**Performance Goals**: No new performance requirement. The documentation-only fixes have zero runtime impact. Optional FR-008 invariant test adds a single fast assertion.

**Constraints**: No new external runtime dependency. No `pytest.mark.skip` without traceable rationale (Constitution Principle V). Whitepaper §4.6 promotion blocked until Round 2 CONVERGED. No coordinate-system migration (deferred to broader-PostGIS work item).

**Scale/Scope**: 1 source file (`epocha/apps/agents/movement.py` 250 LOC); 1 existing test file (`epocha/apps/agents/tests/test_movement.py` 117 LOC) optionally extended; bilingual whitepaper EN+IT promotion edits (one chapter inserted, one chapter removed, three chapters renumbered, all internal §8.x cross-references updated); README EN+IT status table (1 row); doc-sync memory (1 row). No new §13 citations required (Chandler 1966 and Braudel 1979 already present in bibliography from prior catch-up; T003 verifies).

## Constitution Check

Compliance map per `.specify/memory/constitution.md` v1.0.0:

- **Principle I (Scientific Method Above All)**: PASS — every fix produces either a verified citation (Chandler 1966 military vs civilian split; Braudel 1979 road-quality grounding), a documented tunable parameter (terrain factors, arrival scatter), or a documented known limitation (coordinate convention). No magic numbers introduced.
- **Principle II (Verify Before Asserting)**: PASS — every file path, function signature, line range, and pre-remediated state in spec.md was verified on develop @ `9d59037` via direct code reading. The plan tasks re-verify before each fix-implementer dispatch to catch any drift from Round 1 audit date (2026-04-12) to fix execution.
- **Principle III (Adversarial Scientific Audit)**: PASS — Round 2 audit dispatch via `critical-analyzer` is mandatory before promotion. Convergence loop: audit → fix → re-audit → CONVERGED, or repeat.
- **Principle IV (Three-Step Design Process)**: PASS — spec.md is the consolidated output of the Round 1 audit catalogue + controller-side re-review (this plan is the third step's consequence, not a new design iteration).
- **Principle V (Evidence-Based Verification)**: PASS — pytest gate at every commit (baseline measured at T002, expected ≥809 with optional FR-008 invariant test added). No bug-discipline shortcuts.

**GATE: PASS**. No constitutional violations require justification in the Complexity Tracking section below.

## Project Structure

### Documentation (this feature)

```text
specs/20260516-165137-movement-audit-repass/
├── spec.md         # Feature spec (5 findings → 4 user stories + 10 FR + 7 SC) — already authored
├── plan.md         # This file
├── research.md     # Phase 0 output — 2 lookups (Chandler/Braudel civilian-vs-military rates; M-3 doc-only vs behavioral decision)
├── data-model.md   # NOT APPLICABLE — no new entities; no schema change
├── contracts/      # NOT APPLICABLE — no external interfaces touched
├── quickstart.md   # NOT APPLICABLE — fix branch, no new user onboarding
└── tasks.md        # Phase 2 output
```

### Source Code (repository root)

```text
epocha/apps/agents/
├── movement.py                       # Touched: M-1 (verify foot=25 + strengthen docstring), M-2 (verify carriage=60 + add no-relay caveat), M-3 (coord-convention block + impact analysis), M-4 (verify terrain disclaimer + Braudel grounding), M-5 (verify arrival-scatter assumption block)
└── tests/
    └── test_movement.py              # Possibly extended for FR-008 speed-ordering invariant

docs/whitepaper/
├── epocha-whitepaper.md              # Touched at promotion: §8.1 removal + renumbering (§8.2→§8.1, §8.3→§8.2, §8.4→§8.3), new §4.6 chapter, §9 + §10 internal cross-reference updates
└── epocha-whitepaper.it.md           # Mirror

README.md, README.it.md               # Status table 1 row flipped to CONVERGED

docs/memory-backup/
├── feedback_whitepaper_doc_sync.md   # 1 new mapping row
└── (plus live sync to ~/.claude/projects/.../memory/)
```

**Structure Decision**: existing Django project layout. No new top-level directories, no new test files (FR-008 optional extension lives in the existing `test_movement.py`). Whitepaper edits per `project_whitepaper_promotion_pipeline.md` standard procedure.

## Complexity Tracking

No constitutional violations to justify. The branch is pure documentation refinement + whitepaper promotion, with zero behavioral fixes mandated (M-1 and M-2 behavioral fixes were already applied by commit `17f046a`; M-3, M-4, M-5 accept doc-only resolutions per spec). The §8 renumbering ripple is the only multi-file touchpoint and is bounded to the whitepaper EN+IT pair.

## Phase 0 — Research

The Round 1 audit (2026-04-12, transcript in `docs/scientific-audit-2026-04-12.md`) IS the substantive research input for this branch. Two lookups required, documented in `research.md`:

1. **Chandler (1966) and Braudel (1979) civilian-vs-military travel rates**: confirm that Chandler's 20-35 km/day infantry figure refers to Napoleonic forced march and that the appropriate civilian estimate is the lower bound (15-25 km/day). Confirm that the Braudel medieval-merchant ~25 km/day figure is the canonical civilian anchor. Verify ISBN of canonical editions for the §13 bibliography entries if not already present (Chandler 1966 Weidenfeld & Nicolson edition; Braudel 1979 Harper & Row English edition Vol. 1).

2. **M-3 doc-only vs behavioral decision**: confirm that no current simulation seeds zones with real WGS84 latitude/longitude (a grep over the world generator and any test fixture confirms abstract grid coordinates are universal). If confirmed, the doc-only resolution is sufficient for this branch; the behavioral fix (projected coordinates or great-circle distance) is recorded as a scope-positive deferred item bound to the broader-PostGIS roadmap entry of whitepaper §9.

**Output**: `research.md` documents both lookups with decisions and rationale. No external dependency lookup, no Crossref DOI verification (both Chandler and Braudel are pre-DOI monographs cited via ISBN).

## Phase 1 — Design & Contracts

### Data Model

NOT APPLICABLE. No new entities; no schema migration. The M-3 documentation fix is text-only; the geometry field declarations on `Agent.location`, `Zone.center`, `Zone.boundary` are preserved unchanged.

### Contracts

NOT APPLICABLE. No new external interfaces. Existing `get_transport_type`, `calculate_max_distance`, `execute_movement` signatures unchanged.

### Agent Context Update

CLAUDE.md SPECKIT marker block already references the Spec Kit adoption rule (committed in `2b436ec`). The IMPL_PLAN reference between the `<!-- SPECKIT START -->` and `<!-- SPECKIT END -->` markers in CLAUDE.md should point to this plan file:

`specs/20260516-165137-movement-audit-repass/plan.md`

This update happens in tasks.md execution if the marker is currently stale, not here.

### Quickstart

NOT APPLICABLE for fix branch. Quickstart for onboarding new contributors lives in README, not per-feature.

## Re-evaluation of Constitution Check (post-design)

All 5 principles still PASS. No new violations introduced by the design phase. The M-3 documentation-only resolution is the only point where Principle V (Evidence-Based Verification) could be challenged if a future auditor demands behavioral resolution — in which case escalate and re-plan as a separate spec under the broader-PostGIS roadmap entry.

**GATE: PASS**.

## Phase 2 — Tasks (generated separately by `/speckit-tasks`)

The tasks.md file will be produced from this plan + spec.md by the `/speckit-tasks` workflow. Expected task structure:

| Block | Task count estimate |
|-------|---------------------|
| Phase 1 setup: docker, baseline pytest, code-drift verification | 3 tasks |
| Phase 2 foundational: minimal — optional named constant for civilian-foot disclaimer text reuse, or no-op if directly inlined | 1 task |
| Phase 3 US1 (M-1 + M-2 verification + docstring strengthening) | 5-6 tasks |
| Phase 4 US2 (M-3 coordinate-convention block) | 3 tasks |
| Phase 5 US3 (M-4 terrain disclaimer + M-5 arrival-scatter assumption + optional FR-008 invariant test) | 3 tasks |
| Phase 6 Round 2 adversarial audit dispatch + convergence loop | 3 tasks |
| Phase 7 US4 whitepaper §8.1 → §4.6 promotion + §8 renumbering + IT mirror + README/memory updates | 6 tasks |
| Phase 8 polish & closure: push, draft PR, merge, frozen-pin, session memory | 5 tasks |

**Total estimate**: 28-30 tasks. Granularity: 2-5 min per task per Constitution Principle V / `feedback_task_breakdown_mandatory.md` legacy memory.

## Stop Conditions / Escalation

Per Spec Kit `/speckit-plan` skill: command ends after Phase 2 planning. The plan is complete; tasks.md is the next deliverable produced by `/speckit-tasks`.

Escalation triggers during downstream task execution (Constitution Principle II):
- Plan-quoted function signature or line range does not match actual code (re-verify before fix-implementer dispatch).
- Pre-remediated speed values have been reverted on develop between this plan and the fix-implementer dispatch (M-1 or M-2 becomes a behavioral fix instead of a verification step) → re-plan the affected task.
- Round 2 audit produces > 3 new findings (scope explosion) → STOP, re-plan.
- M-3 auditor verdict insists on behavioral resolution (real WGS84 + great-circle distance) → STOP, escalate as separate spec under broader-PostGIS roadmap item.
- M-5 auditor verdict insists on behavioral resolution (relative-to-boundary arrival scatter) → STOP, escalate; possible mid-flight scope expansion within this branch if user approves.
- Pytest baseline shifts unexpectedly (not measured-baseline ± 1) → STOP, diagnose before continuing.

## Generated Artifacts

After `/speckit-plan` completes successfully:
- `specs/20260516-165137-movement-audit-repass/plan.md` — this file
- `specs/20260516-165137-movement-audit-repass/research.md` — 2-lookup record

`data-model.md`, `contracts/`, `quickstart.md` are intentionally NOT generated (NOT APPLICABLE per Phase 1 above).

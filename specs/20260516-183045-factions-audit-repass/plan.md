# Implementation Plan: Factions Audit Re-pass (Round 2)

**Branch**: `20260516-183045-factions-audit-repass` | **Date**: 2026-05-16 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/20260516-183045-factions-audit-repass/spec.md`

## Summary

Close 4 Round 1 adversarial audit findings (2 INCORRECT, 1 UNJUSTIFIED, 1 MISSING) on the factions module (`epocha/apps/agents/factions.py` 876 LOC, the largest single source file in the F-CAMPAIGN audit re-pass batch) accumulated since the 2026-04-12 audit. A spot-check of develop @ `0afca1d` (post Branch 4 closure) confirms that all 4 Round 1 findings remain open in the form documented in spec.md: F-1 Stogdill 1948 cited for the weighted leadership formula when it only supports the trait-correlate principle; F-2 Dunbar 1992 cited for the size-penalty threshold of 5 when Dunbar's number is 150 and the 5 refers to intimate cliques; F-3 cohesion delta coefficients 0.10/0.15/0.02/0.05 attributed to Baumeister 2001 when the source supplies only qualitative negativity-bias direction; F-4 schism detection order-dependent with the limitation note buried inline at lines 465-468 instead of surfaced at the module docstring or whitepaper level.

Round 2 work consists of: (a) corrected-citation rewrites for F-1 (Judge et al. 2002 added as primary meta-analytic reference; weights labelled as tunable design parameters) and F-2 (Dunbar attribution dropped or strongly qualified; threshold labelled as tunable); (b) reframed disclaimers for F-3 (Baumeister scoped to qualitative direction only; four coefficients labelled as tunable per the simulation's calibration budget); (c) Known Limitations block promotion for F-4 (move the buried inline note to the module docstring header; preserve a shortened inline forward reference); (d) Round 2 audit dispatch via `critical-analyzer` with explicit fresh-eyes mandate; (e) optional US3 closure for any additional UNJUSTIFIED findings the auditor surfaces beyond the R1 catalogue (≤3 ceiling, escalate otherwise); (f) promotion of the module to whitepaper §4.7 after Round 2 CONVERGED.

Sequence: documentation refinements first (no behavioral fixes mandated for the four R1 findings), Round 2 audit dispatch with explicit mandate to also check concurrency on `Group.cohesion`/`Group.leader`/`Agent.group`/`Memory` writes, DRY drift against the Branch 1+2+3+4 helpers (affinity.py in particular), bare `except Exception` discipline, and N+1 query patterns in the per-group loop. Then §8.1 → §4.7 promotion in bilingual whitepaper following the standard procedure documented in project memory `project_whitepaper_promotion_pipeline.md`. The §8 renumbering ripple (Factions removed; Knowledge Graph, Economy base layer shifted up by one slot) is handled in the promotion phase, in lock-step with internal cross-reference updates in §9 and §10.

## Technical Context

**Language/Version**: Python 3.12

**Primary Dependencies**: Django 5.x, Django Channels, Celery, PostgreSQL with PostGIS, Redis. No new dependencies introduced. The F-4 doc-only resolution is documentation-only; no `networkx` clustering or `scikit-learn` hierarchical clustering library is added.

**Storage**: PostgreSQL via Django ORM with PostGIS extension. No schema migration expected — `Agent.group`, `Group.cohesion`, `Group.leader`, `Group.parent_group`, `Relationship.sentiment`, `Memory.content`, `DecisionLog.output_decision` retain their existing declarations. The R1 + R2 resolutions are purely documentation refinements.

**Testing**: pytest, executed inside the `epocha-web-1` container via `docker compose -f docker-compose.local.yml exec -T web pytest`. Baseline measured at T002 of tasks.md (expected ≥809 after Branch 4 closure).

**Target Platform**: Docker Compose local development stack; production target Linux Kubernetes.

**Project Type**: Django backend with Celery async workers and Django Channels WebSocket layer. Audit re-pass touches only the agents app (one source file and its test companion); no frontend/mobile/API contract changes. If the Round 2 auditor flags concurrency findings on Group/Agent/Memory writes, the affected blocks gain `transaction.atomic` wrapping and a regression test under `test_factions.py` — admitted as in-scope only on auditor flag, otherwise deferred per spec.md Out of Scope.

**Performance Goals**: No new performance requirement. The documentation-only fixes have zero runtime impact. If the Round 2 auditor flags N+1 patterns in the per-group loop of `process_faction_dynamics()`, the fix adds `select_related`/`prefetch_related` annotations under the same convergence loop and runs a regression check against the existing test suite to confirm no behavior change.

**Constraints**: No new external runtime dependency. No `pytest.mark.skip` without traceable rationale (Constitution Principle V). Whitepaper §4.7 promotion blocked until Round 2 CONVERGED. No graph-clustering algorithm migration (deferred to "robust faction clustering" work item). No costly-signal club-goods cohesion implementation (deferred to "club-goods cohesion mechanics" work item).

**Scale/Scope**: 1 source file (`epocha/apps/agents/factions.py` 876 LOC, the largest in the campaign); 1 existing test file (`epocha/apps/agents/tests/test_factions.py` 153 LOC) possibly extended on auditor flag for concurrency regression; bilingual whitepaper EN+IT promotion edits (one chapter inserted, one chapter removed, two chapters renumbered, all internal §8.x cross-references updated); README EN+IT status table (1 row); doc-sync memory (1 row). Up to 4 new §13 citations possible (Judge 2002 added; Weber/Iannaccone/Antonakis/Hackman conditionally added per FR-001 / FR-002 rewrites; Dunbar conditionally removed).

## Constitution Check

Compliance map per `.specify/memory/constitution.md` v1.0.0:

- **Principle I (Scientific Method Above All)**: PASS — every fix produces either a corrected citation (Judge 2002 added per FR-001; Dunbar attribution dropped or qualified per FR-002; Baumeister scope narrowed per FR-003), an explicit Known Limitation (FR-004 schism order-dependence; FR-005 docstring promotion), or a documented tunable parameter (FR-001 leadership weights; FR-002 size threshold; FR-003 cohesion coefficients; FR-006 optional Round 2 additions). No magic numbers introduced.
- **Principle II (Verify Before Asserting)**: PASS — every file path, function signature, line range, and code reference in spec.md was verified on develop @ `0afca1d` via direct code reading. The plan tasks re-verify before each fix-implementer dispatch to catch any drift from the Round 1 audit date (2026-04-12) to fix execution.
- **Principle III (Adversarial Scientific Audit)**: PASS — Round 2 audit dispatch via `critical-analyzer` is mandatory before promotion. The auditor has the explicit mandate to find new issues beyond the R1 catalogue (per Constitution Principle III mandate). Convergence loop: audit → fix → re-audit → CONVERGED, or repeat. US3 admits up to ~3 additional findings; escalate beyond.
- **Principle IV (Three-Step Design Process)**: PASS — spec.md is the consolidated output of the Round 1 audit catalogue + controller-side re-review (this plan is the third step's consequence, not a new design iteration).
- **Principle V (Evidence-Based Verification)**: PASS — pytest gate at every commit (baseline measured at T002, expected ≥809 with no new tests for doc-only fixes). No bug-discipline shortcuts. No `pytest.mark.skip` without explicit user authorization.

**GATE: PASS**. No constitutional violations require justification in the Complexity Tracking section below.

## Project Structure

### Documentation (this feature)

```text
specs/20260516-183045-factions-audit-repass/
├── spec.md         # Feature spec (4 R1 findings + optional R2 fresh-pass → 4 user stories + 10 FR + 7 SC) — already authored
├── plan.md         # This file
├── research.md     # Phase 0 output — 3 lookups (Judge et al. 2002 DOI verification; Stogdill 1948 content verification; Dunbar 1992 nested-group hierarchy actual claim verification)
├── data-model.md   # NOT APPLICABLE — no new entities; no schema change
├── contracts/      # NOT APPLICABLE — no external interfaces touched
├── quickstart.md   # NOT APPLICABLE — fix branch, no new user onboarding
└── tasks.md        # Phase 2 output
```

### Source Code (repository root)

```text
epocha/apps/agents/
├── factions.py                          # Touched: F-1 (Judge 2002 added, weights tunable, charisma to Weber), F-2 (Dunbar dropped/qualified, threshold tunable), F-3 (Baumeister scope narrowed, four coefficients tunable), F-4 (inline limitation note → module docstring Known Limitations block + shortened inline forward reference), FR-005 Known Limitations subsection, FR-006 optional Round 2 additions
└── tests/
    └── test_factions.py                 # Untouched by default; possibly extended only if Round 2 auditor flags concurrency or DRY issues that require regression coverage

docs/whitepaper/
├── epocha-whitepaper.md                 # Touched at promotion: §8.1 removal + renumbering (§8.2 Knowledge Graph → §8.1, §8.3 Economy base layer → §8.2), new §4.7 chapter, §9 + §10 internal cross-reference updates, §13 bibliography (add Judge 2002 + conditional Weber/Iannaccone/Antonakis/Hackman; conditionally remove Dunbar 1992)
└── epocha-whitepaper.it.md              # Mirror

README.md, README.it.md                  # Status table 1 row flipped to CONVERGED

docs/memory-backup/
├── feedback_whitepaper_doc_sync.md      # 1 new mapping row
└── (plus live sync to ~/.claude/projects/.../memory/)
```

**Structure Decision**: existing Django project layout. No new top-level directories. The test file extension is conditional on Round 2 auditor flags (concurrency or DRY). Whitepaper edits per `project_whitepaper_promotion_pipeline.md` standard procedure.

## Complexity Tracking

No constitutional violations to justify. The branch is documentation refinement + whitepaper promotion, with zero behavioral fixes mandated for the four R1 findings (all accept doc-only resolutions per spec). The §8 renumbering ripple is the only multi-file touchpoint and is bounded to the whitepaper EN+IT pair plus the §9 Roadmap and §10 Discussion narrative cross-references.

The 876-LOC source file is materially larger than the comparable Branch 4 movement.py (250 LOC), which carries two operational consequences: (a) the Round 2 audit dispatch must budget for proportionally longer reading and analysis time; (b) the fresh-eyes pass is expected to surface more candidate UNJUSTIFIED findings than smaller modules — US3 explicitly admits up to ~3 additional rollups, with escalation beyond. This is a scope-management discipline, not a constitutional concern.

## Phase 0 — Research

The Round 1 audit (2026-04-12, transcript in `docs/scientific-audit-2026-04-12.md`) IS the substantive research input for this branch. Three lookups required, documented in `research.md`:

1. **Judge et al. (2002) primary reference verification**: confirm the DOI `10.1037/0021-9010.87.4.765`, journal *Journal of Applied Psychology* 87(4), pages 765-780, title "Personality and leadership: A qualitative and quantitative review". Confirm that the paper supplies meta-analytic effect sizes for the Big Five trait-leadership relationship (the empirical anchor that justifies the trait-based scoring approach without claiming the specific 0.30/0.20/0.15/0.20/0.15 weights are derived from it).

2. **Stogdill (1948) actual content verification**: confirm the canonical citation `Stogdill, R. M. (1948). "Personal factors associated with leadership: A survey of the literature". Journal of Psychology, 25(1), 35-71. DOI 10.1080/00223980.1948.9917362`. Confirm that the paper is a literature survey identifying trait correlates of leadership (intelligence, dependability, social participation, etc.) but does NOT supply a weighted-sum formula. Confirm charisma is NOT among the Stogdill trait correlates (it is a Weberian sociological concept).

3. **Dunbar (1992) nested-group hierarchy actual claim verification**: confirm the canonical citation `Dunbar, R. I. M. (1992). "Neocortex size as a constraint on group size in primates". Journal of Human Evolution, 22(6), 469-493. DOI 10.1016/0047-2484(92)90081-J`. Confirm that "Dunbar's number" is approximately 150 (the cognitive limit on stable social relationships) and that the nested hierarchy of 5/15/50/150 sublayers comes from later work (Zhou, W.-X., Sornette, D., Hill, R. A., and Dunbar, R. I. M. (2005), "Discrete hierarchical organization of social group sizes", *Proceedings of the Royal Society B*, 272(1561), 439-444, DOI `10.1098/rspb.2004.2970`). Confirm that the "5" refers to intimate-clique stratum, NOT to a coordination cost boundary.

**Output**: `research.md` documents all three lookups with decisions, rationale, and the citation-rewrite text to feed into tasks.md.

## Phase 1 — Design & Contracts

### Data Model

NOT APPLICABLE. No new entities; no schema migration. All R1 + R2 resolutions are documentation refinements that preserve existing field declarations on `Agent`, `Group`, `Relationship`, `Memory`, `DecisionLog`.

### Contracts

NOT APPLICABLE. No new external interfaces. Existing `process_faction_dynamics`, `compute_leadership_score`, `compute_legitimacy`, `update_group_cohesion`, `update_group_leadership`, `_check_dissolution`, `_check_schism`, `_detect_and_propose_factions`, `_check_join_existing_groups`, `_process_formation_decisions`, `_create_faction`, `_generate_faction_identity`, `_elect_new_leader` signatures unchanged.

### Agent Context Update

CLAUDE.md SPECKIT marker block already references the Spec Kit adoption rule (committed in `2b436ec`). The IMPL_PLAN reference between the `<!-- SPECKIT START -->` and `<!-- SPECKIT END -->` markers in CLAUDE.md should point to this plan file if the project convention runs that update on each Spec Kit feature:

`specs/20260516-183045-factions-audit-repass/plan.md`

This update happens in tasks.md execution if the marker is currently stale, not here.

### Quickstart

NOT APPLICABLE for fix branch. Quickstart for onboarding new contributors lives in README, not per-feature.

## Re-evaluation of Constitution Check (post-design)

All 5 principles still PASS. No new violations introduced by the design phase. The four R1 doc-only resolutions and the conditional US3 / concurrency / N+1 extensions all live within the constitutional envelope.

The F-4 schism order-dependence doc-only resolution is the only point where Principle V (Evidence-Based Verification) could be challenged if a future auditor demands behavioral resolution — in which case escalate and re-plan as a separate spec under the "robust faction clustering" work item. The current plan accepts the doc-only resolution as sufficient on the basis that the limitation has been documented (currently buried inline; promoted to module docstring header per FR-004) and the behavioral fix carries a meaningful scope expansion (algorithm choice, complexity analysis, regression on all schism tests, possible behavior change in detection rate).

**GATE: PASS**.

## Phase 2 — Tasks (generated separately by `/speckit-tasks`)

The tasks.md file will be produced from this plan + spec.md by the `/speckit-tasks` workflow. Expected task structure:

| Block | Task count estimate |
|-------|---------------------|
| Phase 1 setup: docker, baseline pytest, code-drift verification | 3 tasks |
| Phase 2 foundational: minimal — module docstring Known Limitations block insertion is a shared substrate consumed by F-1/F-2/F-3/F-4 disclaimer references | 1 task |
| Phase 3 US1 (F-1 leadership citation rewrite + F-2 size-penalty Dunbar rewrite) | 4-5 tasks |
| Phase 4 US2 (F-3 cohesion coefficients reframing + F-4 schism order-dependence promotion) | 4 tasks |
| Phase 5 US3 optional (Round 2 fresh-pass UNJUSTIFIED additions, ≤3 ceiling) | 2-3 tasks (conditional) |
| Phase 6 Round 2 adversarial audit dispatch + convergence loop | 3 tasks |
| Phase 7 US4 whitepaper §8.1 → §4.7 promotion + §8 renumbering + IT mirror + §13 bibliography updates + README/memory updates | 6-7 tasks |
| Phase 8 polish & closure: push, draft PR, merge, frozen-pin, session memory | 5 tasks |

**Total estimate**: 28-32 tasks. Granularity: 2-5 min per task per Constitution Principle V / `feedback_task_breakdown_mandatory.md` legacy memory.

## Stop Conditions / Escalation

Per Spec Kit `/speckit-plan` skill: command ends after Phase 2 planning. The plan is complete; tasks.md is the next deliverable produced by `/speckit-tasks`.

Escalation triggers during downstream task execution (Constitution Principle II):
- Plan-quoted function signature or line range does not match actual code (re-verify before fix-implementer dispatch).
- Round 2 audit produces > 3 new INCORRECT/UNJUSTIFIED findings (scope explosion) → STOP, re-plan whether to absorb into US3 or split into a separate spec.
- F-4 auditor verdict insists on behavioral resolution (graph-based clustering or hierarchical clustering on the sentiment matrix) → STOP, escalate as separate spec under "robust faction clustering" work item.
- Auditor flags concurrency findings on `Group.cohesion` / `Group.leader` / `Agent.group` / `Memory` writes → admit `transaction.atomic` wrapping + regression test as in-scope under the convergence loop; pytest baseline gate must account for the delta.
- Auditor flags N+1 query patterns in the per-group loop of `process_faction_dynamics()` → admit `select_related`/`prefetch_related` annotations as in-scope; verify no behavior change via existing test suite.
- Auditor flags bare `except Exception` blocks → admit specific exception narrowing as in-scope.
- Auditor flags DRY drift against `affinity.py` or other audited helpers → admit replacement with canonical helper as in-scope.
- Pytest baseline shifts unexpectedly (not measured-baseline ± expected delta) → STOP, diagnose before continuing.

## Generated Artifacts

After `/speckit-plan` completes successfully:
- `specs/20260516-183045-factions-audit-repass/plan.md` — this file
- `specs/20260516-183045-factions-audit-repass/research.md` — 3-lookup record

`data-model.md`, `contracts/`, `quickstart.md` are intentionally NOT generated (NOT APPLICABLE per Phase 1 above).

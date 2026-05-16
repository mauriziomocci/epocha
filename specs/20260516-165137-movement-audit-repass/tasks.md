---
description: "Tasks for movement audit re-pass — Round 1 catalogue to CONVERGED + chapter 4.6 promotion"
---

# Tasks: Movement Audit Re-pass (Round 2)

**Input**: Design documents from `specs/20260516-165137-movement-audit-repass/`

**Prerequisites**: spec.md (5 Round 1 findings → 4 user stories), plan.md (Constitution Check PASS, no data-model/contracts/quickstart), research.md (Chandler/Braudel civilian-vs-military mapping + M-3 doc-only decision)

**Tests**: optional — FR-008 invariant test extension is admitted but not mandatory; the existing `test_carriage_travels_farther_than_foot` already covers the ordering invariant. Pytest regression gate is mandatory.

**Organization**: tasks grouped by Spec user story. MVP = US1 (2 INCORRECT findings closed → unblocks promotion path). US2 + US3 + US4 incremental.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: parallel-safe (different files, no dependencies)
- **[Story]**: US1/US2/US3/US4/SETUP/FOUND/POLISH
- Absolute or repo-relative file paths

## Path Conventions

Django backend single project. Source at `epocha/apps/agents/movement.py`, tests at `epocha/apps/agents/tests/test_movement.py`, whitepaper at `docs/whitepaper/`.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: pre-flight verification before any fix.

- [ ] T001 [SETUP] Verify Docker compose stack up: `docker compose -f docker-compose.local.yml ps`. Start if needed with `docker compose -f docker-compose.local.yml up -d`. Confirm web container healthy via `docker compose -f docker-compose.local.yml exec -T web python -c "import django; print(django.get_version())"`.
- [ ] T002 [SETUP] Baseline pytest run: `docker compose -f docker-compose.local.yml exec -T web pytest 2>&1 | tail -5`. Record baseline count (expected ≥809 after Branch 3 closure). Pin the number in a scratch note for downstream gate comparisons.
- [ ] T003 [SETUP] Re-verify Round 1 finding code references still match develop @ `9d59037`. Spot-check 5 critical line refs from spec.md: `movement.py:1-20` (module docstring "Sources" block + Coordinate-convention `Note`), `movement.py:37-48` (TRAVEL_SPEEDS table — verify foot=25.0 and carriage=60.0), `movement.py:62-72` (_TERRAIN_FACTORS dict + tunable-disclaimer comment), `movement.py:93-97` (_ARRIVAL_SCATTER_RANGE 100-unit assumption note), `epocha/apps/agents/tests/test_movement.py` (existing test_carriage_travels_farther_than_foot at line 60-63). Also grep `docs/whitepaper/epocha-whitepaper.md` for existing Chandler 1966 and Braudel 1979 §13 bibliography entries; record their presence/absence. Record drift in a scratch note before proceeding.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: minimal — no shared refactor needed for this branch. The single foundational item is an optional helper-constant introduction.

- [ ] T004 [FOUND] Optional: if the docstring rewrite of T005/T006 produces repeated text strings between the module docstring header and the inline `TRAVEL_SPEEDS` comments, extract a module-level named constant or a leading attribution paragraph to avoid duplication. If the rewrite stays compact (no repetition warrants extraction), skip this task — record as "no-op, inline acceptable" in commit message.

**Checkpoint**: foundation ready. User stories can begin.

---

## Phase 3: User Story 1 — Close 2 INCORRECT findings on travel-speed table (Priority: P1) 🎯 MVP

**Goal**: verify foot=25 and carriage=60 already in place; strengthen module docstring and inline comments to make the Chandler military-vs-civilian split explicit and the carriage no-relay assumption explicit.

**Independent Test**: dispatch Round 2 `critical-analyzer` audit limited to M-1 and M-2; verdict CONVERGED for each. Optional `pytest epocha/apps/agents/tests/test_movement.py -v` regression to confirm `test_carriage_travels_farther_than_foot` and `test_returns_distance_in_grid_units` still green (the latter has a 100 < dist < 200 range assertion that depends on foot=25).

### M-1 — Foot speed civilian vs military attribution

- [ ] T005 [US1] In `epocha/apps/agents/movement.py` (around lines 37-42), verify `TRAVEL_SPEEDS["foot"] = 25.0` (pre-verified at T003). Strengthen the inline comment to: `# Civilian sustained travel rate on foot, ~25 km/day. Chandler (1966) reports 20-35 km/day for Napoleonic infantry on FORCED MARCH (military upper bound, light load, flat terrain, elite units); civilian travellers without those conditions average the lower-to-middle of that range. Braudel (1979) Vol. 1 corroborates ~25 km/day for medieval merchants on foot in good conditions, dropping to 15-20 km/day in difficult terrain or with loads. The 25 km/day value is the civilian anchor, NOT the Chandler military upper bound.`

### M-2 — Carriage speed no-relay assumption explicit

- [ ] T006 [US1] In `epocha/apps/agents/movement.py` (around lines 44-46), verify `TRAVEL_SPEEDS["carriage"] = 60.0` (pre-verified at T003). Strengthen the inline comment to: `# Horse-drawn carriage on good roads WITHOUT relay stations, ~60 km/day. Chandler (1966) reports 60-80 km/day with relay stations (a military, royal, or postal-system asset NOT available to the typical civilian agent in the Epocha population); 60 km/day is the lower bound of Chandler's range, achievable by a single team without relay. Braudel (1979) Vol. 1 corroborates ~50-60 km/day for pre-industrial post-coaches on good roads without relay. To use the 80 km/day upper bound, the simulation would need to model relay-station infrastructure explicitly, which is out of scope for the MVP.`

### Module docstring Sources block rewrite

- [ ] T007 [US1] In `epocha/apps/agents/movement.py` module docstring (lines 1-20), rewrite the "Sources" block to distinguish military and civilian rates explicitly: `Sources:\n- Chandler, D. G. (1966). *The Campaigns of Napoleon*. Weidenfeld & Nicolson, London. ISBN 978-0-297-74830-4. The logistics chapter documents Napoleonic MILITARY sustained march rates: 20-35 km/day for infantry on forced march, 60 km/day for cavalry, 60-80 km/day for horse-drawn carriages on good roads WITH RELAY STATIONS. Civilian sustained travel without relay infrastructure or military discipline averages the lower bound of each range.\n- Braudel, F. (1979). *Civilisation matérielle, économie et capitalisme, XVe-XVIIIe siècle. Vol. 1*. Armand Colin, Paris. English ed.: Braudel (1981). *Civilization and Capitalism, 15th-18th Century. Vol. 1: The Structures of Everyday Life* (S. Reynolds, Trans.). Harper & Row, New York. ISBN 978-0-06-014845-6. Vol. 1 records qualitative CIVILIAN pre-industrial European travel rates: ~25 km/day medieval merchants on foot, ~50 km/day river/canal boats, ~50-60 km/day post-coaches without relay.\n\nThe TRAVEL_SPEEDS table values are explicitly mapped to the civilian regime: foot=25 (Braudel medieval merchant, Chandler military lower bound), horse=60 (Chandler cavalry — applicable to mounted civilian travel), carriage=60 (Chandler lower bound without relay, Braudel post-coach), boat=50 (Braudel river/canal).`

### US1 checkpoint

- [ ] T008 [US1] Targeted pytest: `docker compose -f docker-compose.local.yml exec -T web pytest epocha/apps/agents/tests/test_movement.py -v`. Expected all green (the docstring changes are pure documentation; the inline comment edits do not change any numeric value).
- [ ] T009 [US1] Full pytest gate: `docker compose -f docker-compose.local.yml exec -T web pytest 2>&1 | tail -3`. Expected baseline (no behavioral change in this phase).
- [ ] T010 [US1] Commit `docs(agents): close round 1 INCORRECT findings M-1 M-2 in movement docstring`. Stage only the touched files: `epocha/apps/agents/movement.py`.

---

## Phase 4: User Story 2 — Close 1 INCONSISTENT finding on coordinate convention (Priority: P1)

**Goal**: document the coordinate-system convention explicitly with impact analysis and downstream-consumer enumeration. Doc-only resolution per research.md Lookup 2.

**Independent Test**: dispatch Round 2 audit subset on resolved file; verdict CONVERGED on M-3.

### M-3 — Coordinate convention block

- [ ] T011 [US2] In `epocha/apps/agents/movement.py` module docstring (around lines 16-19, replacing the existing `Note:` block), insert a dedicated "Coordinate convention" block: `Coordinate convention:\n  The PostGIS geometry fields on Agent.location, Zone.center, and Zone.boundary are declared with srid=4326 (WGS84 latitude/longitude) for forward compatibility with real geographic data. The current MVP implementation, however, seeds all zone geometries with ABSTRACT GRID COORDINATES (typically in the 0-1000 unit range produced by the world generator), NOT real WGS84 lat/lon. The grid-to-metres conversion is supplied by World.distance_scale (default 133 m/unit).\n  \n  Euclidean distance computations on the raw (x, y) values — math.hypot(dx, dy) in calculate_max_distance, the partial-movement vector arithmetic in execute_movement, and the arrival-scatter offsets — are valid under this grid convention. They would be WILDLY WRONG if zones were seeded with real WGS84 coordinates: a one-degree separation parses as ~1 grid unit and would be multiplied by distance_scale=133m to yield ~133 m, when the real great-circle distance is ~111 km at the equator.\n  \n  Downstream consumers of raw (x, y) arithmetic (all of which would need migration to a projected or great-circle distance if real WGS84 were introduced):\n    1. calculate_max_distance() — straight-line distance via math.hypot.\n    2. execute_movement() — partial-movement vector interpolation (new_x = location.x + dx * ratio).\n    3. The arrival-scatter logic (Point(cx + uniform(...), cy + uniform(...))) inside execute_movement().\n  \n  A future migration to real geographic data is tracked under the "broader PostGIS adoption" roadmap entry of whitepaper §9. It is out of scope for the present audit re-pass.`
- [ ] T012 [US2] Run targeted pytest: `pytest epocha/apps/agents/tests/test_movement.py -v`. Expected all green (docstring-only change).

### US2 checkpoint

- [ ] T013 [US2] Commit `docs(agents): close round 1 INCONSISTENT finding M-3 with coordinate-convention block`. Stage: `epocha/apps/agents/movement.py`.

---

## Phase 5: User Story 3 — Close 2 UNJUSTIFIED findings (Priority: P2)

**Goal**: strengthen the `_TERRAIN_FACTORS` disclaimer with Braudel grounding (M-4); reformat the `_ARRIVAL_SCATTER_RANGE` assumption block to make the 100-unit assumption explicit and tunable-via-setting (M-5). Optional FR-008 invariant test extension.

### M-4 — Terrain factors disclaimer with Braudel grounding

- [ ] T014 [US3] In `epocha/apps/agents/movement.py` around lines 61-72 (the `_TERRAIN_FACTORS` block), strengthen the existing comment to: `# Terrain traversal factor by zone type.\n# All five values are tunable design parameters without empirical fit to a specific historical road network. The RELATIVE ORDERING (urban ≥ commercial > industrial > rural > wilderness) is grounded in the qualitative pre-modern road-quality patterns documented by Braudel (1979) Vol. 1: urban and commercial zones carry well-maintained paved roads; industrial zones in the early-modern period typically had rougher cart tracks; rural zones had unpaved roads degraded by weather; wilderness has no road infrastructure at all and reduces sustained travel rate by half. The SPECIFIC MAGNITUDES (1.0/1.0/0.9/0.7/0.5) are not derived from any study and are tunable per simulation calibration. Future era templates may override these values to reflect period-specific road quality.`

### M-5 — Arrival scatter assumption block

- [ ] T015 [US3] In `epocha/apps/agents/movement.py` around lines 92-97 (the `_ARRIVAL_SCATTER_RANGE = 40.0` block), reformat the existing comment into an explicit assumption block: `# Random offset range (grid units) for final position within a zone.\n# Prevents all agents arriving at the exact center point of a zone.\n# \n# ASSUMPTION: standard zone half-side of ~100 grid units, as produced by the world generator (epocha/apps/world/services/world_generator.py). Under this assumption, a 40-unit scatter places agents within roughly the inner 80% of the zone, avoiding both center-clustering and boundary overshoot.\n# \n# BEHAVIOR UNDER NON-STANDARD ZONE SIZES:\n#   - Zones substantially smaller (half-side < ~50 grid units): scatter may place agents outside the zone boundary; the Zone.boundary check in execute_movement does NOT clamp the scatter to the boundary, so this is a known limitation.\n#   - Zones substantially larger (half-side > ~200 grid units): scatter range is small relative to the zone, producing tight clustering near the center.\n# \n# TUNABILITY: the value is a hardcoded module-level constant. If non-standard zone sizes become common, a future refactor should make this relative to the zone's actual boundary.envelope dimensions (e.g. 40% of the half-axis). The behavioral fix is bound to a future MVP-extension item, not to the current audit re-pass.`

### FR-008 optional invariant test extension

- [ ] T016 [US3] Optional: in `epocha/apps/agents/tests/test_movement.py`, add a new test method `test_speed_ordering_invariant` inside `TestCalculateMaxDistance`. Under identical health (1.0), repression (0.1), stability, and terrain conditions, assert `dist_carriage >= dist_horse >= dist_foot` and `dist_horse > dist_foot`. The existing `test_carriage_travels_farther_than_foot` covers part of this; the new test adds the horse comparison. If the test count discipline does not warrant the extension, skip and record "no-op, existing coverage sufficient" in commit message.

### US3 checkpoint

- [ ] T017 [US3] Full pytest gate: `docker compose -f docker-compose.local.yml exec -T web pytest 2>&1 | tail -3`. Expected baseline or baseline+1 (depending on whether T016 ran).
- [ ] T018 [US3] Commit `docs(agents): close round 1 UNJUSTIFIED findings M-4 M-5 in movement module`. Stage: `epocha/apps/agents/movement.py`, plus `epocha/apps/agents/tests/test_movement.py` if T016 ran.

---

## Phase 6: Round 2 Adversarial Audit (Convergence Loop)

**Purpose**: per Constitution Principle III, re-audit before promotion. Loop until CONVERGED.

- [ ] T019 [US4 prep] Dispatch `critical-analyzer` subagent (Opus) for Round 2 audit on `epocha/apps/agents/movement.py` + `epocha/apps/agents/tests/test_movement.py`. Prompt includes: original 5 Round 1 findings (M-1 through M-5) + their resolution per US1+US2+US3 commits; mandate to verify each fix landed AND no new INCORRECT/UNJUSTIFIED introduced; Chandler 1966 ISBN and Braudel 1979 ISBN accept doc-only resolution for M-3 with the impact-analysis enumeration; spec.md acceptance scenarios mapped to commits.
- [ ] T020 [US4 prep] If verdict NOT CONVERGED: dispatch fix-implementer for residual findings with same lowest-risk strategy. Repeat T019. Expect ≤2 round-trips per Branch 1+2+3 precedent.
- [ ] T021 [US4 prep] When verdict CONVERGED: record Round 2 audit transcript hash or summary in a brief commit note (not a new file under `docs/superpowers/`; per Spec Kit rule). Audit transcript may be embedded as appendix in the future tasks-completion log.

---

## Phase 7: User Story 4 — Whitepaper §8.1 → §4.6 Promotion (Priority: P1)

**Goal**: campaign deliverable. Promote movement module from designed-pending to audited-Methods. Handle the §8 renumbering ripple in lock-step with internal cross-reference updates.

### Whitepaper EN promotion

- [ ] T022 [US4] In `docs/whitepaper/epocha-whitepaper.md`, REMOVE the `## 8.1 Movement` subsection (currently around line 1922-1926). Renumber subsequent `§8.x`: §8.2 Factions → §8.1, §8.3 Knowledge Graph → §8.2, §8.4 Economy base layer → §8.3. Grep the full document for `§8.1`, `§8.2`, `§8.3`, `§8.4`, `8.1`, `8.2`, `8.3`, `8.4` references in body text (notably the §9 Roadmap and §10 Discussion which reference §8.x sections multiple times — see lines 1952, 1953, 1957, 1959, 2004-2005, 2195, 2361 per T003 grep result). Update all to the new numbering.
- [ ] T023 [US4] Insert new `§4.6` between current `§4.5 Political institutions` and `§5 Implementation` of `docs/whitepaper/epocha-whitepaper.md`. Title: `## 4.6 Movement`. Status header: `> Status: implemented as of commit <filled-on-merge>, code audit CONVERGED 2026-05-16 round 2.`
- [ ] T024 [US4] §4.6 body — canonical Methods schema: Background (per-tick relocation under three intent classes — voluntary economic migration, voluntary social migration, involuntary movement; citation anchors Chandler 1966 for military rates Braudel 1979 for civilian rates), Model (effective_speed factorisation as multiplicative combination of base_speed * health_factor * stability_factor * repression_factor * terrain_factor), Equations (numbered following the existing 4.5.x sequence: effective_speed equation, max_distance_km conversion, grid-unit conversion via World.distance_scale), Parameters table (TRAVEL_SPEEDS civilian regime mapping with the Chandler/Braudel split documented; _TERRAIN_FACTORS as tunable design parameters; cost constants _MOOD_COST_PER_MOVEMENT _HEALTH_COST_EXHAUSTING_TRAVEL _EXHAUSTION_THRESHOLD), Algorithm (calculate_max_distance + execute_movement narrative summary with the full-vs-partial movement branching), Simplifications (M-1/M-2 military-vs-civilian regime choice; M-3 coordinate-convention current grid + future broader-PostGIS migration item; M-4 terrain ordering grounded in Braudel with tunable magnitudes; M-5 arrival-scatter assumption; explicit known limitations: no path-finding, no inter-zone routed distance, no multi-tick journey continuity, no relay-station infrastructure model), Status header.
- [ ] T025 [US4] In §13 of `epocha-whitepaper.md`, verify (per T003 grep result) presence of `Chandler, D. G. (1966)` and `Braudel, F. (1979)` entries; add the canonical ISBN-attributed entries alphabetically if missing per research.md Lookup 1.1 and 1.2.

### Whitepaper IT mirror

- [ ] T026 [US4] Mirror T022 in `docs/whitepaper/epocha-whitepaper.it.md`: remove §8.1 Movimento IT, renumber §8.2-§8.4 → §8.1-§8.3, update all internal §8.x cross-references in §9 Roadmap and §10 Discussione body text.
- [ ] T027 [US4] Mirror T023+T024+T025 in IT: insert `## 4.6 Movimento` with the canonical Methods schema translated, equation numbering identical to EN; mirror §13 bibliography additions if T025 added entries. Status header in IT: `> Stato: implementato a partire dal commit <filled-on-merge>, audit del codice CONVERGENTE 2026-05-16 round 2.`

### README EN+IT status table + doc-sync memory

- [ ] T028 [US4] [P] In `README.md` Status table flip the movement row to `yes (CONVERGED 2026-05-16 round 2)`. Mirror in `README.it.md` with `sì (CONVERGENTE 2026-05-16 round 2)`. In `docs/memory-backup/feedback_whitepaper_doc_sync.md` mapping table add 1 row: `| epocha/apps/agents/movement.py | §4.6 (EN) | §4.6 (IT) |`. Copy updated file to live memory at `~/.claude/projects/-Users-mauriziomocci-Documents-workspace-Opensource-epocha/memory/feedback_whitepaper_doc_sync.md`.

### US4 checkpoint

- [ ] T029 [US4] Full pytest gate. Expected baseline or baseline+1 (whitepaper/README/memory edits don't touch tests; only T016 may have added an extra test).
- [ ] T030 [US4] Commit `docs: promote movement from chapter 8.1 to chapter 4.6 after audit CONVERGED`. Stage: 2 whitepapers, 2 READMEs, doc-sync memory backup.

---

## Phase 8: Polish & Closure

**Purpose**: branch closure per Spec Kit conventions + frozen-at-commit pin.

- [ ] T031 [POLISH] Push branch: `git push -u origin 20260516-165137-movement-audit-repass`.
- [ ] T032 [POLISH] Open draft PR via `gh pr create --base develop --head 20260516-165137-movement-audit-repass --title "fix(science): movement Round 2 audit CONVERGED + promote to whitepaper §4.6" --body "..."`. Body summarizes 5 Round 1 findings closed + Round 2 verdict + whitepaper promotion + §8 renumbering ripple + Spec Kit conformance.
- [ ] T033 [POLISH] `gh pr merge <PR#> --merge --delete-branch`. Pull develop.
- [ ] T034 [POLISH] Frozen-at-commit pin: in `docs/whitepaper/epocha-whitepaper.md` and `.it.md`, replace 2 placeholders `<filled-on-merge>` in §4.6 status headers with the merge commit SHA from `gh pr view <PR#> --json mergeCommit -q .mergeCommit.oid`. Commit `docs: pin movement §4.6 frozen-at-commit`. Push develop.
- [ ] T035 [POLISH] Update project memory: edit `~/.claude/projects/-Users-mauriziomocci-Documents-workspace-Opensource-epocha/memory/project_session_resume_2026_05_16.md` to mark movement CLOSED + record next-step pointer to factions branch. Sync to `docs/memory-backup/`. Commit `docs: mark movement session resume CLOSED + memory sync`. Push develop.

---

## Dependencies

| From | Blocks |
|------|--------|
| T001-T003 (SETUP) | all subsequent |
| T010 US1 commit | T011+ US2 (sequential simpler; same file) |
| T013 US2 commit | T014+ US3 |
| T019 CONVERGED | T022+ US4 promotion |
| T030 promotion commit | T031-T035 closure |

## Parallel Opportunities

- T028 has internal parallel-safe steps (EN README, IT README, doc-sync memory — three different files) but they are bundled in one commit; safe to perform in any order within the task.
- US2 and US3 docstring edits are on the same file (`movement.py`); sequential execution is safer to avoid merge friction.
- T026 (IT whitepaper mirror) can in principle run in parallel with T022-T025 (EN whitepaper), but the §8 renumbering ripple requires the EN to be settled first to confirm the new section numbers; sequential execution recommended.

## MVP Suggestion

US1 (T005-T010) IS the MVP: the 2 INCORRECT findings unblock the whitepaper promotion path. Without US1 CONVERGED on M-1 and M-2, the promotion (US4) is blocked. US2+US3 can ship incrementally; US4 ships when all upstream CONVERGED.

## Format Validation

All 35 tasks above use the `- [ ] T<NNN> [TAG] description` checkbox format. Story tags map to `SETUP/FOUND/US1/US2/US3/US4/POLISH`. File paths absolute or repo-relative. Parallel markers `[P]` applied where independent.

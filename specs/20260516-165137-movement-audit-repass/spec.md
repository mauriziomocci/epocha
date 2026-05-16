# Feature Specification: Movement Audit Re-pass (Round 2)

**Feature Branch**: `20260516-165137-movement-audit-repass`

**Created**: 2026-05-16

**Status**: Draft (post Round 1 audit, pre Round 2 verification + fixes)

**Input**: User description: "Round 2 adversarial audit re-pass for the movement module (`epocha/apps/agents/movement.py`) — close the 5 Round 1 findings catalogued against this module and promote it from whitepaper §8.1 to a new §4.6."

## Context

This feature is **Branch 4 of 6** in the F-CAMPAIGN audit re-pass batch documented in `docs/superpowers/plans/2026-05-12-audit-repass-campaign.md` (legacy plan, archival). Movement is a single-module cluster: `epocha/apps/agents/movement.py` (250 LOC) with companion test file `epocha/apps/agents/tests/test_movement.py` (117 LOC). The 2026-04-12 batch adversarial audit (`docs/scientific-audit-2026-04-12.md`) opened 5 outstanding Round 1 findings against this module: two INCORRECT on the historical travel-speed table (`M-1` foot 35 km/day overstated, `M-2` carriage 80 km/day without relay assumption), one INCONSISTENT on the coordinate-system convention (`M-3` PostGIS SRID 4326 declared but grid-unit coordinates used in practice), and two UNJUSTIFIED on tunable design parameters (`M-4` terrain factors, `M-5` arrival scatter range).

Branch 1 (Reputation cluster, merged via PR#5), Branch 2 (Rumor cluster, merged via PR#6 with promotion to §4.4) and Branch 3 (Political-institutions cluster, merged via PR#7 with promotion to §4.5) preceded this work. The conventions established by those branches — word-boundary regex for citation searches, `transaction.atomic` for any concurrent state write, lowest-risk fix posture, mandatory invariant tests for behavioral fixes — apply unchanged to this branch.

A spot-check of the current code on develop @ `9d59037` (post Branch 3 closure) confirms that several Round 1 findings have already been partially or fully remediated by interim commits since 2026-04-12 (the foot rate was reduced from 35 to 25 km/day in commit `17f046a`, the carriage rate was reduced from 80 to 60 km/day in the same commit, the terrain-factor block already carries an explicit "tunable design parameters without empirical source" disclaimer at `movement.py:62-65`, the `_ARRIVAL_SCATTER_RANGE = 40.0` block at `movement.py:93-97` already documents the 100-unit zone-boundary assumption). The remaining Round 1 work consists of (a) explicit Round 2 verification of the pre-remediated findings, (b) closure of residual documentation gaps (notably the docstring header which still describes 25 km/day as a "civilian sustained travel rate" without distinguishing it from the military rate cited by Chandler 1966), (c) the M-3 coordinate-system convention reconciliation (currently a `Note` block at `movement.py:16-19` admits the simplification; Round 2 must decide between a doc-only resolution and a behavioral fix), (d) optional invariant tests where enforceable, and (e) promotion of the module to whitepaper §4.6 after Round 2 CONVERGED.

This spec is constitutional-compliant per `.specify/memory/constitution.md` v1.0.0: Principles I (Scientific Method), II (Verify Before Asserting), III (Adversarial Audit), V (Evidence-Based Verification).

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Close 2 INCORRECT findings on the travel-speed table (Priority: P1)

The Round 1 audit identified two INCORRECT findings on the `TRAVEL_SPEEDS` constant table that BLOCK the §8.1 → §4.6 whitepaper promotion until each is resolved with a corrected citation or a behavioral parameter adjustment, OR explicitly verified as already-closed by an interim commit. The two items are: foot speed 35 km/day overstated for civilian travel (M-1, *pre-verified* on develop — foot is now 25.0 km/day, but the docstring still needs a clearer attribution split between Chandler's military rate and the civilian estimate), and carriage speed 80 km/day overstated without a relay assumption (M-2, *pre-verified* on develop — carriage is now 60.0 km/day, but the relay-stations caveat in the source attribution should be made explicit at both the module docstring and the inline `TRAVEL_SPEEDS` comment).

**Why this priority**: per the audit verdict, the whitepaper §4.6 promotion (the deliverable that closes this branch) requires all INCORRECT findings resolved or independently verified as already closed. Convergence on both items is the gating condition.

**Independent Test**: dispatch Round 2 `critical-analyzer` subagent audit limited to the M-1 and M-2 findings; verdict must be CONVERGED for each. Optional `pytest` regression on `test_movement.py::TestCalculateMaxDistance` to confirm that the relative ordering of speeds (carriage > horse ≥ foot in distance per tick under identical health/repression/stability conditions) is preserved.

**Acceptance Scenarios**:

1. **Given** the `TRAVEL_SPEEDS["foot"]` entry in `movement.py`, **When** auditing its value and docstring, **Then** the value is 20-25 km/day (consistent with pre-industrial civilian travel rather than Napoleonic military forced march), the inline comment cites Chandler (1966) explicitly as the *military* upper bound (20-35 km/day for infantry forced march) and Braudel (1979) as the *civilian* anchor for the chosen value (medieval merchants ~25 km/day on foot), and the module docstring header echoes the same split.

2. **Given** the `TRAVEL_SPEEDS["carriage"]` entry, **When** auditing its value and docstring, **Then** the value is 50-60 km/day (no relay assumption) OR the value is 60-80 km/day with an explicit "assumes relay stations available (military, royal, or postal use)" caveat in both the inline comment and the module docstring. The current implementation uses 60.0 km/day; Round 2 must verify that both the inline comment and the docstring header consistently state the no-relay assumption.

3. **Given** the module-level docstring at `movement.py:1-20`, **When** auditing the "Sources" block, **Then** Chandler (1966) attribution distinguishes between *military forced march* rates (20-35 km/day infantry, 60 km/day cavalry, 60-80 km/day carriages on good roads *with relay stations*) and *civilian sustained travel* rates (approximately 20-25 km/day on foot, 50-60 km/day by carriage without relay), with the chosen `TRAVEL_SPEEDS` values mapped explicitly to one or the other.

---

### User Story 2 — Close 1 INCONSISTENT finding on coordinate system convention (Priority: P1)

The Round 1 audit identified one INCONSISTENT finding (M-3): the project's PostGIS geometry fields on `Zone` and `Agent` are declared with `srid=4326` (WGS84 latitude/longitude), but the movement module computes Euclidean distances on the raw `(x, y)` coordinates as if they were grid units in metres, with a `World.distance_scale` field converting grid units to metres. The current code carries a `Note` block at `movement.py:16-19` acknowledging the simplification, but the docstring claim is not enforced anywhere and a future zone seeded from real lat/lon would silently produce wildly wrong distances (a one-degree separation at WGS84 would parse as ~1 grid unit, then be multiplied by `distance_scale = 133 m` to yield 133 m, when the real distance is ~111 km).

**Why this priority**: same as P1 — whitepaper §4.6 promotion blocked until INCONSISTENT findings are resolved or documented with explicit impact analysis. Per Constitution Principle III convergence loop.

**Independent Test**: dispatch Round 2 `critical-analyzer` audit on the resolved file; verdict CONVERGED. If the resolution is doc-only, the auditor must accept the impact analysis as sufficient.

**Acceptance Scenarios**:

1. **Given** the module docstring at `movement.py:1-20` and any place that reads `agent.location.x/y` or `zone.center.x/y` to compute Euclidean distance, **When** auditing the coordinate-system convention, **Then** the docstring carries an explicit "Coordinate convention" block stating: (a) PostGIS fields are declared with `srid=4326` for forward-compatibility with real WGS84 data; (b) the current MVP simulations seed zones with abstract grid coordinates, NOT real latitude/longitude; (c) Euclidean distance on `(x, y)` is therefore valid for grid coordinates but would be wildly wrong for real lat/lon (typical one-degree separation ≈ 111 km at the equator, not 1 metre); (d) any future migration to real geographic data MUST replace `math.hypot(dx, dy)` with a great-circle or projected-distance computation before being seeded.

2. **Given** the same docstring block, **When** the convention is documented, **Then** the impact analysis explicitly lists the three downstream consumers of `(x, y)` coordinates: `calculate_max_distance()` straight-line distance computation, `execute_movement()` partial-movement vector arithmetic, and the arrival-scatter logic. Each is named so a future auditor can trace the assumption.

3. **Given** the same convention block, **When** Round 2 audit examines whether a behavioral fix (projected coordinates) is in scope, **Then** the spec explicitly admits the doc-only resolution path as sufficient for this branch (no real lat/lon currently used in simulations); the behavioral fix is recorded as a scope-positive deferred item bound to the "broader PostGIS adoption" roadmap entry of whitepaper §9.

---

### User Story 3 — Close 2 UNJUSTIFIED findings on tunable design parameters (Priority: P2)

The Round 1 audit identified two UNJUSTIFIED findings: terrain factors `rural: 0.7`, `wilderness: 0.5`, `industrial: 0.9` unsourced (M-4), and `_ARRIVAL_SCATTER_RANGE = 40.0` hardcoded with an unenforced 100-unit zone-boundary assumption (M-5). The current code already carries a partial disclaimer for M-4 at `movement.py:62-65` and a partial assumption note for M-5 at `movement.py:93-97`. Neither blocks promotion individually, but both are required for the module to meet Constitution Principle I ("No parameter without a justified value").

**Why this priority**: P2 because individually non-blocking but collectively required for CONVERGED verdict. Grouped fix in one commit.

**Independent Test**: dispatch Round 2 audit on the resolved file; verdict CONVERGED.

**Acceptance Scenarios**:

1. **Given** the `_TERRAIN_FACTORS` dict in `movement.py`, **When** auditing the five values (`urban`, `commercial`, `industrial`, `rural`, `wilderness`), **Then** the block carries an explicit disclaimer that all five values are tunable design parameters without empirical fit; the relative ordering (urban ≥ commercial > industrial > rural > wilderness) is grounded inline in the qualitative pre-modern road-quality patterns documented by Braudel (1979) Vol. 1, with a forward pointer to per-template tuning when era-specific road-quality data become available; specific magnitudes are explicitly tunable per simulation calibration.

2. **Given** the `_ARRIVAL_SCATTER_RANGE = 40.0` constant, **When** auditing its derivation, **Then** the value is either made relative to actual zone boundary dimensions (e.g. 40% of the half-axis of the zone's `boundary.envelope` when available) OR documented with an explicit assumption block stating: (a) the value assumes standard zone half-side of ~100 grid units as produced by the world generator; (b) zones substantially smaller would cause arrival scatter outside the boundary, zones substantially larger would cause poor agent dispersion; (c) the value is tunable per `EPOCHA_MOVEMENT_ARRIVAL_SCATTER` setting if a future need arises. Doc-only is acceptable for this branch; the behavioral fix (relative-to-boundary) is admitted but optional.

3. **Given** the `_MOOD_COST_PER_MOVEMENT = 0.02`, `_HEALTH_COST_EXHAUSTING_TRAVEL = 0.01`, and `_EXHAUSTION_THRESHOLD = 0.5` constants at `movement.py:80-90`, **When** auditing their derivation, **Then** the existing inline disclaimers ("Tunable parameter -- no empirical source; set to match the magnitude of other action mood deltas in engine.py") are preserved unchanged; they are not flagged by Round 1 but Round 2 verifies they have not regressed during this branch's work.

---

### User Story 4 — Promote §8.1 → §4.6 in bilingual whitepaper after Round 2 CONVERGED (Priority: P1)

After the Round 2 re-audit verdict is CONVERGED, the movement module must be promoted from `§8.1 Movement` (currently chapter 8 first slot after the Branch 3 §8.1 → §4.5 promotion renumbered Movement to §8.1) to a new `§4.6 Movement` (audited Methods) of the bilingual whitepaper. This is the campaign deliverable that closes the branch.

**Why this priority**: P1 — closes the branch and unlocks the next campaign branch (factions, currently §8.2).

**Independent Test**: whitepaper EN+IT both contain a new `§4.6 Movement` chapter following the canonical Methods schema (Background, Model, Equations, Parameters table, Algorithm, Simplifications, Status header). `§8.1` is removed and subsequent `§8.x` renumbered (§8.2 Factions → §8.1, §8.3 Knowledge Graph → §8.2, §8.4 Economy base layer → §8.3). README EN+IT status table flips the movement module to "yes (CONVERGED YYYY-MM-DD round 2)". Doc-sync memory `feedback_whitepaper_doc_sync.md` adds 1 mapping row for `epocha/apps/agents/movement.py` → §4.6.

**Acceptance Scenarios**:

1. **Given** Round 2 audit CONVERGED on the movement module, **When** inspecting the whitepaper EN at `§4`, **Then** a new `§4.6 Movement` chapter exists following the canonical Methods schema; `§8.1` is removed; subsequent `§8.x` are renumbered (Factions → §8.1, Knowledge Graph → §8.2, Economy base layer → §8.3).

2. **Given** EN promotion applied, **When** inspecting the IT mirror, **Then** the same structure exists translated, with equation numbering preserved.

3. **Given** the promotion commit, **When** inspecting `README.md` and `README.it.md` status table, **Then** the movement module row shows "yes (CONVERGED YYYY-MM-DD round 2)" / "sì (CONVERGENTE YYYY-MM-DD round 2)".

4. **Given** the promotion commit, **When** inspecting `docs/memory-backup/feedback_whitepaper_doc_sync.md`, **Then** one new mapping row exists for `epocha/apps/agents/movement.py` → `§4.6`.

5. **Given** the merge commit on develop, **When** running a follow-up commit `docs: pin movement chapter 4.6 frozen-at-commit`, **Then** the §4.6 status header in EN+IT replaces `<filled-on-merge>` with the merge SHA.

---

### Edge Cases

- **Pre-remediated state drift**: the user-supplied finding catalogue describes Round 1 values (foot 35, carriage 80) but the current code already carries the post-remediation values (foot 25, carriage 60). If a future commit on develop between this spec and the fix-implementer dispatch reverts the speeds, US1 acceptance scenarios become behavioral fixes instead of documentation refinements. The plan tasks must re-verify at T003 before any commit.
- **M-3 escalation path**: if the Round 2 auditor rejects the doc-only resolution as insufficient (insisting on projected coordinates or great-circle distance), the branch scope expands materially (geometric library introduction, migration on agent and zone geometries, regression on all distance tests). Escalate to user before any behavioral expansion; this is a scope-positive item that belongs to its own spec under the "broader PostGIS adoption" roadmap entry of whitepaper §9.
- **M-5 behavioral fix optionality**: if Round 2 auditor accepts the doc-only assumption block at `_ARRIVAL_SCATTER_RANGE`, no behavioral change is required. If the auditor insists on relative-to-boundary scatter, the fix touches `execute_movement()` arrival branch and may break existing test assertions that rely on the 40-unit scatter envelope. Coordinate test updates with traceable rationale per Constitution Principle V.
- **Whitepaper §8 renumbering ripple**: any narrative reference to "§8.1 Movement" elsewhere in the whitepaper (the Discussion of §10 and the Roadmap of §9 both reference §8.x sections by number) must be updated in lock-step with the renumbering. The plan tasks must include a full-document grep pass for `§8.x` references before the promotion commit.
- **Citation that cannot be verified via Crossref**: Chandler (1966) and Braudel (1979) are pre-DOI monographs; use the ISBN of the canonical edition in the §13 bibliography entry. Avoid `[VERIFICATION PENDING]` visible body text per established whitepaper §13 convention.
- **Pytest regression**: any fix that breaks an existing test must be accompanied by either a test update with traceable rationale OR escalation to user. No `pytest.mark.skip` without explicit user authorization per Principle V.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST set `TRAVEL_SPEEDS["foot"]` to a value in the 20-25 km/day range consistent with pre-industrial civilian travel, with the inline comment citing Chandler (1966) explicitly as the *military* forced-march upper bound (20-35 km/day infantry) and Braudel (1979) as the *civilian* anchor for the chosen value (closes M-1; pre-verified on develop at 25.0).
- **FR-002**: System MUST set `TRAVEL_SPEEDS["carriage"]` to a value in the 50-60 km/day range without assuming relay stations, OR carry an explicit "assumes relay stations available" caveat at both the inline comment and the module docstring if the value is left at 60-80 (closes M-2; pre-verified on develop at 60.0 with implicit no-relay assumption that must be made explicit).
- **FR-003**: System MUST update the module-level docstring "Sources" block at `movement.py:1-20` to distinguish between *military forced march* rates and *civilian sustained travel* rates, mapping each `TRAVEL_SPEEDS` entry explicitly to one category (closes M-1 + M-2 docstring side).
- **FR-004**: System MUST carry an explicit "Coordinate convention" block in the module docstring stating that PostGIS fields use `srid=4326` for forward compatibility but the current implementation uses abstract grid coordinates with `World.distance_scale` conversion, that real WGS84 lat/lon would produce wildly wrong Euclidean distances, and listing the three downstream consumers of raw `(x, y)` arithmetic (closes M-3 via documentation-only resolution; behavioral fix deferred to the broader-PostGIS roadmap item).
- **FR-005**: System MUST carry an explicit "design parameters without empirical fit" disclaimer at the `_TERRAIN_FACTORS` block, grounding the relative ordering (urban ≥ commercial > industrial > rural > wilderness) in Braudel (1979) Vol. 1 qualitative road-quality patterns and marking the specific magnitudes as tunable per simulation calibration (closes M-4; current docstring already carries a partial disclaimer that must be verified and strengthened).
- **FR-006**: System MUST carry an explicit assumption block at the `_ARRIVAL_SCATTER_RANGE = 40.0` constant stating the 100-unit zone half-side assumption, the behavior under significantly larger or smaller zones, and the tunable-via-setting forward pointer (closes M-5 via documentation-only resolution; behavioral fix relative-to-boundary admitted as optional).
- **FR-007**: System MUST preserve the existing inline disclaimers on `_MOOD_COST_PER_MOVEMENT`, `_HEALTH_COST_EXHAUSTING_TRAVEL`, and `_EXHAUSTION_THRESHOLD` unchanged; Round 2 must verify they have not regressed.
- **FR-008**: System MUST optionally add at least one cross-module invariant test under `epocha/apps/agents/tests/test_movement.py` or a new `tests/test_movement_invariants.py` that asserts the relative ordering of travel speeds (carriage ≥ horse ≥ foot under identical conditions) and that `calculate_max_distance` returns a strictly positive value for any healthy agent with positive `distance_scale`. The test extension is optional because the existing `test_carriage_travels_farther_than_foot` already covers part of this invariant.
- **FR-009**: System MUST reach Round 2 audit CONVERGED verdict before whitepaper promotion.
- **FR-010**: System MUST promote `§8.1` → `§4.6` in bilingual whitepaper per User Story 4 acceptance scenarios, including renumbering subsequent §8.x sections (Factions → §8.1, Knowledge Graph → §8.2, Economy base layer → §8.3) and updating all internal cross-references in §9 and §10 body text.

### Key Entities

- **Agent.location** (existing model `epocha/apps/agents/models.py`): `PointField(srid=4326)` whose coordinates are documented post-fix as abstract grid units in the MVP; no schema change.
- **Zone.center, Zone.boundary** (existing): `PointField(srid=4326)` and `PolygonField(srid=4326)`; same convention. No schema change.
- **World.distance_scale, World.tick_duration_hours** (existing): float fields; no change.
- **Whitepaper EN/IT** (`docs/whitepaper/epocha-whitepaper.{md,it.md}`): receives new `§4.6` chapter, loses `§8.1` (movement), renumbers §8.2-§8.4 to §8.1-§8.3. No new §13 citations required (Chandler 1966 and Braudel 1979 are already in the bibliography from prior catch-up; verify at T003 and add if missing).
- **README EN/IT**: status table update for movement row.
- **Doc-sync memory** (`docs/memory-backup/feedback_whitepaper_doc_sync.md` + live): 1 new mapping row.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Round 2 `critical-analyzer` audit on `epocha/apps/agents/movement.py` returns verdict CONVERGED with zero INCORRECT, zero UNJUSTIFIED unresolved, zero INCONSISTENT unresolved.
- **SC-002**: `pytest --cov=epocha -v` passes with zero failures (baseline measured at T002; expected ≥809 after Branch 3 closure; expected baseline or baseline+1 with optional FR-008 invariant test added).
- **SC-003**: Whitepaper EN at `§4.6` contains the canonical Methods-schema chapter; `§8.1` removed; subsequent `§8.x` sections renumbered to §8.1-§8.3; all narrative cross-references updated.
- **SC-004**: Whitepaper IT mirrors §4.6 structure with translated content and identical equation numbering.
- **SC-005**: README EN+IT status table row for the movement module shows "CONVERGED YYYY-MM-DD round 2" / "CONVERGENTE YYYY-MM-DD round 2".
- **SC-006**: Doc-sync memory `feedback_whitepaper_doc_sync.md` contains 1 new mapping row for `epocha/apps/agents/movement.py` → `§4.6`.
- **SC-007**: Branch merged to develop via PR with merge commit; `<filled-on-merge>` placeholder in the new §4.6 status header replaced with merge SHA in a follow-up commit on develop.

## Assumptions

- The Round 1 audit findings catalogue (user-supplied, source `docs/scientific-audit-2026-04-12.md` transcript) is the authoritative input. No re-running of the original Round 1 audit; Round 2 verification + fixes go directly into execution.
- The fix-implementer prefers the lowest-risk path per Constitution Principle V; documentation upgrades are sufficient for all five Round 1 findings (M-1 and M-2 already have the behavioral fix applied; M-3, M-4, M-5 accept doc-only resolutions per spec).
- The whitepaper promotion procedure follows the standard documented in project memory `project_whitepaper_promotion_pipeline.md` and reproduced in Branch 1, 2, 3 tasks files.
- No new external runtime dependencies introduced. No coordinate-projection library (pyproj, shapely projected ops) added in this branch.
- No migration on existing geometry fields. The `srid=4326` declaration is preserved unchanged.
- Italian whitepaper translation follows the established style from prior promotions.
- Pytest runs in Docker via `docker compose -f docker-compose.local.yml exec -T web pytest`.
- The 4 Round 1 findings that appear already remediated by interim commits (M-1 foot rate, M-2 carriage rate, M-4 terrain partial disclaimer, M-5 zone-boundary assumption note) require explicit Round 2 verification — the spec treats them as "verify and strengthen" rather than "fix from scratch", but the plan must include a fallback fix-path if verification fails.

## Constitution Compliance

This spec is constitutional-compliant per `.specify/memory/constitution.md` v1.0.0:

- **Principle I (Scientific Method)**: every Round 1 finding resolution must produce either a verified citation (Chandler 1966 military vs civilian split per FR-001/FR-002/FR-003; Braudel 1979 road-quality grounding per FR-005), a documented tunable parameter (FR-005, FR-006), or a documented known limitation (FR-004 coordinate convention). No magic numbers introduced.
- **Principle II (Verify Before Asserting)**: every file path, function signature, and line range mentioned in this spec was verified against current code on develop @ commit `9d59037` (post Branch 3 closure).
- **Principle III (Adversarial Audit)**: Round 2 audit dispatch via `critical-analyzer` subagent is mandatory before any whitepaper promotion. Convergence loop: audit → fix → re-audit → CONVERGED, or repeat.
- **Principle IV (Three-Step Design)**: this spec is the consolidated output of the Round 1 audit catalogue + controller-side re-review; no further design iteration before plan.
- **Principle V (Evidence-Based Verification)**: pytest gate at every fix commit; promotion requires Round 2 CONVERGED verdict.

## Out of Scope

- Round 1 audit re-execution (already done 2026-04-12, output is the input to this spec).
- Other campaign branches (factions, world-economy-deprecation, knowledge-graph) — separate Spec Kit features in subsequent timestamps.
- Demography Plan 4 (engine wiring) — post-campaign work item.
- Validation experiments execution — post-campaign work item.
- Behavioral M-3 fix (real WGS84 coordinates with great-circle or projected distance) — bound to the broader-PostGIS roadmap item of whitepaper §9; this branch resolves M-3 with documentation only.
- Behavioral M-5 fix (zone-boundary-relative arrival scatter) — admitted as optional; default plan path is doc-only.
- Inter-zone routed-distance computation (replacing the abstract zone-graph distance with shortest-path against PostGIS geometry) — bound to the same broader-PostGIS roadmap item.
- Multi-tick journey path-finding (A* or Dijkstra over the zone graph) — out of scope; current `execute_movement()` is per-tick straight-line.

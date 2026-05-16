# Phase 0 Research: Movement Audit Re-pass

**Branch**: `20260516-165137-movement-audit-repass`
**Date**: 2026-05-16
**Source spec**: [spec.md](./spec.md)
**Plan**: [plan.md](./plan.md)

Two lookups required by `plan.md` Phase 0. Output feeds into tasks.md (docstring-strengthening text for M-1+M-2, design decision on M-3 doc-only vs behavioral resolution).

---

## Lookup 1 — Chandler (1966) and Braudel (1979) civilian-vs-military travel rates

### 1.1 Chandler, D. (1966)

- **Decision**: cite as `Chandler, D. G. (1966). *The Campaigns of Napoleon*. Weidenfeld & Nicolson, London.` ISBN `978-0-297-74830-4` for the canonical UK first edition. Pre-DOI monograph. The widely available 1995 Scribner paperback reprint (ISBN `978-0-02-523660-8`) carries identical pagination for the logistics chapter that contains the march-rate figures.
- **Rationale**: Chandler is the canonical reference in the military-history literature for Napoleonic sustained march rates: 20-35 km/day for infantry on forced march (with the higher figure achieved only by elite units in flat terrain with light loads), 60 km/day for cavalry on sustained operations, and 60-80 km/day for horse-drawn carriages on good roads *with relay stations* (post-station infrastructure that was a military or royal logistics asset, not available to civilian travellers in the same period). The 35 km/day upper bound applies to Napoleonic forced march, not to civilian sustained travel; the original Round 1 audit finding M-1 correctly flagged 35 as overstated for civilian use. The reduction to 25 km/day applied in commit `17f046a` is consistent with the lower bound of the Chandler military range and with the qualitative pre-industrial civilian estimate corroborated by Braudel (see 1.2). The carriage upper bound of 80 km/day similarly requires the relay-station assumption that does not apply to the typical Epocha civilian agent; the reduction to 60 km/day applied in the same commit is consistent with the lower bound of Chandler's military range *without* relay assumption.
- **Alternatives considered**: Engels (1978) *Alexander the Great and the Logistics of the Macedonian Army* provides an earlier comparison point (~25 km/day sustained for classical infantry) corroborating the Braudel medieval figure; van Creveld (1977) *Supplying War* surveys the broader logistics literature. Chandler remains the standard citation for the Napoleonic era specifically.

### 1.2 Braudel, F. (1979)

- **Decision**: cite as `Braudel, F. (1979). *Civilisation matérielle, économie et capitalisme, XVe-XVIIIe siècle. Vol. 1: Les structures du quotidien*. Armand Colin, Paris.` Original French. English translation `Braudel, F. (1981). *Civilization and Capitalism, 15th-18th Century. Vol. 1: The Structures of Everyday Life* (S. Reynolds, Trans.). Harper & Row, New York.` ISBN `978-0-06-014845-6`. Pre-DOI monograph.
- **Rationale**: Braudel's Vol. 1 is the canonical reference for pre-industrial European everyday life, including the qualitative travel-rate figures: medieval merchants on foot averaging ~25 km/day on good days, ~15-20 km/day in difficult terrain or with loads, river and canal boats averaging ~50 km/day downstream, post-coaches without relay averaging ~50-60 km/day on good roads. These figures are presented as qualitative pre-industrial averages rather than as fits to specific data series, which is the appropriate level of evidence for the `TRAVEL_SPEEDS` table calibration.
- **Alternatives considered**: Bairoch (1988) *Cities and Economic Development* offers complementary data on pre-industrial urban-to-urban travel times; Cipolla (1976) *Before the Industrial Revolution* covers similar ground. Braudel remains the canonical multi-volume reference.

### 1.3 Civilian-vs-military mapping

- **Decision**: the post-fix `TRAVEL_SPEEDS` table maps as follows for the docstring rewrite:
  - `foot = 25.0 km/day` — civilian sustained travel rate. Chandler 1966 reports 20-35 km/day for Napoleonic infantry forced march; 25 km/day is the lower-to-middle of that range, consistent with the qualitative civilian estimate from Braudel 1979.
  - `horse = 60.0 km/day` — cavalry sustained rate (Chandler 1966). This is genuinely a military figure but is the standard sustained-cavalry rate also applicable to mounted civilian travel (couriers, mounted nobility) per Braudel.
  - `carriage = 60.0 km/day` — horse-drawn carriage without relay stations. Chandler 1966 reports 60-80 km/day with relay; 60 km/day is the lower bound *without* the relay assumption, consistent with the Braudel qualitative figure for post-coaches.
  - `boat = 50.0 km/day` — river/canal boat in pre-industrial Europe (Braudel 1979).
- **Rationale**: minimal-scope docstring refinement. The values are already in place; the rewrite makes the civilian-vs-military attribution explicit in three places: the module docstring "Sources" block (lines 1-20), the inline comment at each `TRAVEL_SPEEDS` entry, and the whitepaper §4.6 Methods chapter at promotion time.

---

## Lookup 2 — M-3 doc-only vs behavioral decision

### 2.1 Real WGS84 seeding survey

Grep results for the world generator and zone-seeding paths:

```
epocha/apps/world/services/world_generator.py — uses random.uniform(0, 1000) for x and y of zone centers
epocha/apps/world/management/commands/seed_world.py — same pattern, abstract grid units
epocha/apps/agents/tests/test_movement.py:33 — Point(60, 60), Polygon.from_bbox((0, 0, 120, 120)), abstract grid
epocha/apps/world/templates/*.json — no real lat/lon in any era template
```

No current code path seeds zones with real WGS84 latitude/longitude coordinates. Every observed seed uses abstract grid units in the 0-1000 range with `World.distance_scale` (default 133 m/unit) converting to metres. The Euclidean distance `math.hypot(dx, dy)` at `movement.py:204` and the partial-movement vector arithmetic at lines 228-231 are valid under the current convention.

### 2.2 Decision

- **Decision**: doc-only resolution is sufficient for this branch. Document the coordinate convention explicitly in the module docstring (FR-004) with the impact analysis enumerating the three downstream consumers of raw `(x, y)` arithmetic.
- **Rationale**: no behavioral defect exists in any current execution path; the inconsistency is forward-compatibility-only. Introducing real WGS84 + great-circle distance now would require: (a) a coordinate-projection library dependency (pyproj or shapely projected ops), (b) a regression pass on all distance tests, (c) a re-tuning of `_ARRIVAL_SCATTER_RANGE` and other grid-relative constants, (d) a migration on existing zone fixtures and templates. All four items are scope-positive and belong to the "broader PostGIS adoption" roadmap entry of whitepaper §9, not to a Round 2 audit re-pass branch.
- **Decision risk**: if a Round 3 reviewer (future) insists on behavioral resolution, escalate as a separate spec under the broader-PostGIS roadmap entry. The doc-only resolution makes the future migration easier to scope by enumerating the affected consumers explicitly.
- **Alternatives considered**: behavioral resolution within this branch (rejected — out of scope, breaks all existing tests, drags in coordinate-projection dependency); partial behavioral resolution (a `_use_projected_distance` feature flag — rejected as architectural smell; the flag would itself be a code-quality liability with no current consumer).

---

## Output

Both lookups CLOSED. Findings to propagate to tasks.md:

1. **M-1 + M-2 docstring rewrite**: use the civilian-vs-military mapping from Lookup 1.3 in three places (module docstring, inline `TRAVEL_SPEEDS` comments, whitepaper §4.6 Methods chapter). Chandler 1966 ISBN `978-0-297-74830-4` (UK 1st ed.) or `978-0-02-523660-8` (Scribner reprint); Braudel 1979 English ed. ISBN `978-0-06-014845-6`. Verify presence in whitepaper §13 at T003; add if missing.

2. **M-3 doc-only**: the coordinate-convention block in the module docstring must enumerate (a) the `srid=4326` declaration kept for forward compatibility, (b) the abstract grid convention currently in use with `World.distance_scale` conversion, (c) the impact of seeding real lat/lon under the current implementation, (d) the three downstream consumers (`calculate_max_distance` Euclidean, `execute_movement` vector arithmetic, arrival-scatter). Behavioral fix bound to broader-PostGIS roadmap entry.

3. **M-4 + M-5 verification + strengthening**: doc-only; no Crossref or external lookup needed. The current inline disclaimers cover the disclaim-as-tunable angle but need explicit Braudel 1979 grounding for the M-4 relative ordering and explicit assumption-block formatting for M-5.

4. **No new §13 bibliography entries expected**: both Chandler 1966 and Braudel 1979 are already present in the bibliography from prior catch-up (commit `17f046a` and later); T003 verifies presence; if missing, add the canonical ISBN entry per Lookup 1.

5. **Pytest baseline expectation**: ≥809 after Branch 3 closure (per Branch 3 tasks.md T002 expectation); FR-008 optional invariant test adds at most 1 to the count.

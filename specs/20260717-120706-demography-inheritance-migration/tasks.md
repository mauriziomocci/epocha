# Tasks: Demography Plan 3 — Inheritance and Migration

**Branch**: `20260717-120706-demography-inheritance-migration` | **Date**: 2026-07-17

**Input**: [plan.md](./plan.md) (approved at the phase-3 light gate), [spec.md](./spec.md) (approved at the phase-2 gate)

**Design source**: `docs/superpowers/specs/2026-04-18-demography-design-it.md` sections 4, 5, 6 — CONVERGED after four adversarial audit rounds on 2026-04-18. Tasks execute this design; they never reopen it.

## Format: `[ID] [P?] [Story] Description`

- **[P]** — parallelisable: different file, no dependency on an incomplete task. Phase 5 still executes one task at a time; [P] marks what *could* be reordered, not permission to batch.
- **[US1]..[US5]** — the user story from spec.md this task serves.
- Every task names its file and its acceptance criterion. Toggle `- [ ]` to `- [x]` on completion, one at a time, before starting the next.

## Path Conventions

- Modules: `epocha/apps/demography/`
- Tests: `epocha/apps/demography/tests/`
- Test runner (authority): `docker compose -f docker-compose.local.yml exec -T web pytest -q`
- Lint (authority): `docker compose -f docker-compose.local.yml exec -T web ruff check .`

---

## READ THIS BEFORE ANY TASK — the three preflight traps

These come from the plan's code-verification preflight (Constitution Principle II), verified against the source tree at `develop` = `07aecaa`. They are reproduced verbatim in the tasks they affect. Do not "correct" them from memory.

1. **The education field is `Agent.education_level`, NOT `education`.** The design spec writes `child.education` as shorthand. The real field is `Agent.education_level` (FloatField, default 0.3, "0.0 = illiterate, 1.0 = scholar"). Do NOT add an `education` field — this plan produces zero migrations, and SC-005 asserts it.
2. **`strength` is two different things.** `Agent.strength` is an inherited physical trait (h² = 0.55, in the heritability table). `Relationship.strength` is tie strength and is the one the mourning cascade filters on (`> 0.6`). Confusing them sends grief memories to muscular agents instead of close friends.
3. **`couple.py:dissolve_on_death` cannot handle both partners dying in the same tick.** It resolves through `active_couple_for`, which filters `dissolved_at_tick__isnull=True`; the first partner's death sets that field, so the second call returns `None` and the second snapshot is never captured. Decision D1 fixes this by extending `dissolve_on_death`, not by duplicating snapshot logic into `inheritance.py`.

**Escalation rule (phase 5, non-negotiable)**: if a task requires a strategic decision rather than specified execution — an unforeseen edge case, a wrong assumption in spec or plan, an incoherence with existing code, a scientific doubt — STOP. Do not invent. Escalate to Opus, which revises spec or plan before work resumes.

---

## Phase 1: Setup

No setup tasks. Both modules land in the existing `epocha.apps.demography` app, which Plan 1 scaffolded and registered in `INSTALLED_APPS`. No new dependency, no new app, no migration. The preflight confirmed the template schema and the data layer are already complete.

---

## Phase 2: Foundational (blocking prerequisites)

**Purpose**: close the D1 integration gap and build the pure kernel every later phase depends on. Nothing in Phase 3+ may start until this phase is green.

- [x] T001 Write the RED test for the same-tick double death in `epocha/apps/demography/tests/test_couple.py`: create a Couple, kill both partners at the same tick, call `dissolve_on_death` once per partner, assert BOTH `agent_a_name_snapshot` and `agent_b_name_snapshot` are populated and BOTH FKs are `None`, with `dissolution_reason == "death"` and `dissolved_at_tick == tick`. **Trap 3 verbatim**: this test MUST fail today, because `active_couple_for` filters `dissolved_at_tick__isnull=True` and the second call returns `None`. Acceptance: the test fails for exactly that reason, confirmed by reading the failure output — not by assumption.
- [x] T002 Implement decision D1 in `epocha/apps/demography/couple.py`: extend `dissolve_on_death` so that when `active_couple_for` returns `None`, it falls back to a couple already dissolved at the SAME `tick` in which this agent is still a non-null partner, then captures that partner's name snapshot and nulls the FK. Do NOT pass batch state in; resolving "dissolved at this same tick" needs no knowledge of the caller's batch (rejected alternative in D1). Update the docstring to state the new contract: idempotent per partner, not once per couple. Acceptance: T001 goes green and every pre-existing test in `test_couple.py` stays green.
- [x] T003 [P] ~~Extend the §4.1 couple subsection in the same commit as T002.~~ **SUPERSEDED by decision of 2026-07-17 — consolidated into T043 at closure.** The §4.1 chapter is `frozen-at-commit` (front-matter pin + per-section "as of the pinned commit" status), and that pin is only re-stamped at merge, so updating the §4.1.3 dissolution prose while the pin still reads `368e972` would open a window where the text describes code ahead of its declared commit. The D1 fix is an integration detail that does NOT change the scientific model, so the doc-sync rule's escape clause applies: T002 commits without a whitepaper change, its PR note states this, and the entire §4.1 delta (couple MISS-4 same-tick capture + inheritance + migration + the frozen-at-commit re-pin to the merge SHA) lands as one coherent update in T043. Acceptance: the T002 commit carries no whitepaper edit; T043 carries the couple change.
- [x] T004 Write the RED tests for the inheritance kernel in `epocha/apps/demography/tests/test_inheritance.py`: `inherit_trait` returns `h2*midparent + (1-h2)*noise` for two known parents with a seeded RNG; clamps to the trait range; and applies the fix I-1 single-parent fallback `h2*parent + (1-h2)*noise` when one parent value is `None`. Acceptance: three failing tests, module does not exist yet.
- [x] T005 Create `epocha/apps/demography/inheritance.py` with the module docstring (citing Falconer & Mackay 1996 as the polygenic additive source and stating that per-trait h² values come from the trait-specific primary studies, with Polderman et al. 2015 as methodological backbone only, never as the source of an individual h²) and implement `inherit_trait(mother_val, father_val, h2, era_mean, era_sd, rng) -> float`, including the fix I-1 fallback when either parent value is `None`. Follow the shape of `mortality.py` and `couple.py`: `from __future__ import annotations`, `TYPE_CHECKING` imports, lazy model imports inside functions. Acceptance: T004 green.
- [x] T006 Write the RED tests for the restricted formula evaluator in `epocha/apps/demography/tests/test_inheritance.py`: `evaluate_derived_formula` computes `0.4*(1-agreeableness) + 0.3*neuroticism + 0.3*intelligence` correctly from a symbol dict; and REFUSES, raising, each of: a call (`abs(x)`), an attribute access (`x.__class__`), a dunder name (`__import__`), a subscript (`x[0]`), and a comprehension. This is SC-006. Acceptance: failing tests covering the happy path plus five distinct refusals.
- [x] T007 Implement `evaluate_derived_formula(expression: str, symbols: dict[str, float]) -> float` in `epocha/apps/demography/inheritance.py` per decision D5: parse with `ast.parse(expression, mode="eval")` and walk a NODE WHITELIST of `Expression`, `BinOp`, `UnaryOp`, `Constant`, `Name`, and the arithmetic operators only; resolve `Name` only against `symbols`; raise on everything else. `eval()` on the raw string is FORBIDDEN even though formulas come from versioned template files — the surface is not opened just because today's inputs are trusted. Acceptance: T006 green, including all five refusals.

**Checkpoint**: kernel and D1 fix green. Phases 3-7 may proceed.

---

## Phase 3: User Story 1 — A newborn inherits from its parents (Priority: P1)

**Goal**: a birth produces traits, social class and education derived from the parents per the era's rules.

**Independent test**: create two parents with known traits, birth a child with a seeded RNG, assert every trait follows the kernel and that class and education follow the loaded era template.

- [x] T008 [US1] Write the RED tests for `apply_trait_inheritance` in `epocha/apps/demography/tests/test_inheritance.py`: every trait in the template's `heritability` dict is written to the child; traits in `Agent.personality` JSONB without a published h² use the tunable default 0.30; `cunning` is NOT inherited biologically but computed from `derived_trait_formulas` against the freshly inherited traits. Acceptance: failing tests.
- [x] T009 [US1] Implement `apply_trait_inheritance(child, mother, father, template, rng) -> None` in `epocha/apps/demography/inheritance.py`: polygenic pass over `template["trait_inheritance"]["heritability"]`, clamping each result, then the derived-formula pass over `template["trait_inheritance"]["derived_trait_formulas"]` using T007's evaluator, resolving `Name` only against the freshly computed traits. Document the 0.30 default for unpublished traits as a tunable design parameter. Acceptance: T008 green.
- [x] T010 [P] [US1] Write the RED test for `resolve_birth_attributes` in `epocha/apps/demography/tests/test_inheritance.py`: gender drawn from `sex_ratio_at_birth` (default 1.05 M/F) and orientation from the era's `sexual_orientation_distribution`, both deterministic under a seeded RNG. Acceptance: failing test.
- [x] T011 [US1] Implement `resolve_birth_attributes(template, rng) -> tuple[str, str]` in `epocha/apps/demography/inheritance.py`, citing in the docstring that the 1.05 sex ratio is biologically universal and that the modern orientation defaults come from Chandra et al. (2011) and are tunable design parameters for non-modern eras. Acceptance: T010 green.
- [x] T012 [US1] Write the RED tests for `apply_social_inheritance` in `epocha/apps/demography/tests/test_inheritance.py`, one per era rule: `pre_industrial` copies the father's `social_class` (patrilineal rigid); `industrial` inherits 70% with 30% regression to the zone class mean (Clark 2014); `modern` samples with intergenerational elasticity 0.4 (Solon 1999; Chetty et al. 2014) rather than copying; `sci_fi` reassigns 80% meritocratically on intelligence + education. Plus the education regression. **Trap 1 verbatim**: the field is `Agent.education_level`, NOT `education` — the design spec's `child.education` is shorthand. Do NOT add an `education` field. Acceptance: five failing tests.
- [x] T013 [US1] Implement `apply_social_inheritance(child, mother, father, template, zone_class_mean, rng) -> None` in `epocha/apps/demography/inheritance.py`: the four `class_rule` branches, plus `child.education_level = rho * (mother.education_level + father.education_level)/2 + (1-rho) * era_mean_edu` with `rho` from `template["social_inheritance"]["education_regression_rho"]`. Cite each rule's source in the docstring. **Trap 1 verbatim**: the field is `Agent.education_level`. Acceptance: T012 green, and `makemigrations --check --dry-run` still clean.
- [x] T014 [US1] Write the RED test for the birth entry point in `epocha/apps/demography/tests/test_inheritance.py`: `apply_inheritance_at_birth` sequences traits, birth attributes and social inheritance, sets `wealth = 0` and `zone = mother.zone`, and is deterministic across two identically-seeded runs (part of SC-003). Acceptance: failing test.
- [x] T015 [US1] Implement `apply_inheritance_at_birth(child, mother, father, simulation, tick) -> None` in `epocha/apps/demography/inheritance.py`: load the template via `load_template`, derive the RNG via `get_seeded_rng(simulation, tick, phase)` with a phase string unique to inheritance, sequence T009/T011/T013, set `wealth = 0` and `zone = mother.zone`. No global state (decision D3). Acceptance: T014 green.

**Checkpoint**: User Story 1 delivers independently — births inherit correctly under all five era templates.

---

## Phase 4: User Story 2 — On death the estate passes to the heirs (Priority: P1)

**Goal**: an estate transfers per the era's succession rule net of estate tax, conserving value exactly.

**Independent test**: kill an agent with a known estate in a seeded simulation; assert heirs' cash plus treasury tax equals the initial estate exactly.

- [x] T016 [US2] Write the RED tests for `resolve_heirs` in `epocha/apps/demography/tests/test_inheritance.py`: the priority ladder from `economic_inheritance.heir_priority` returns surviving spouse first, then children, then siblings, then extended family to two generations, then empty (treasury case). Only LIVING heirs are returned. Acceptance: failing tests.
- [x] T017 [US2] Implement `resolve_heirs(deceased, template) -> list` in `epocha/apps/demography/inheritance.py`, using `select_related`/`prefetch_related` so the ladder costs a bounded number of queries regardless of family size (no N+1). Acceptance: T016 green, query count asserted with `assertNumQueries`.
- [x] T018 [US2] Write the RED test for `apply_estate_tax` in `epocha/apps/demography/tests/test_inheritance.py`: with rate 0.40 the treasury grows by exactly 40% of the estate via `add_to_treasury` and the function returns exactly 60%. Per-era default rates: pre_industrial 0.0, industrial 0.15, modern_democracy 0.40 (Piketty 2014 tables 14.1-14.2). Acceptance: failing test.
- [x] T019 [US2] Implement `apply_estate_tax(total_estate_value, rate, government, primary_currency_code) -> float` in `epocha/apps/demography/inheritance.py` verbatim from the design, routing tax through the existing `add_to_treasury` helper and returning the inheritable remainder. Acceptance: T018 green.
- [x] T020 [US2] Write the RED tests for `distribute_estate` in `epocha/apps/demography/tests/test_inheritance.py`, one per rule: `primogeniture` gives 100% to the eldest surviving son, falling back to eldest daughter then spouse then siblings (Blackstone 1765); `equal_split` divides equally among surviving children with the spouse taking a child's share (Napoleonic Code 1804); `shari'a` gives the spouse 1/8 with children present, sons twice a daughter's share (Powers 1986); `matrilineal` passes to the sister's children (Schneider & Gough 1961); `nationalized` gives 100% to the treasury (Nove 1969). Include the documented non-binary handling per rule. Acceptance: five failing tests.
- [x] T021 [US2] Implement `distribute_estate(deceased, heirs, rule, inheritable) -> dict` in `epocha/apps/demography/inheritance.py`: the five rules, returning a per-heir allocation mapping WITHOUT persisting, so conservation is assertable on the returned mapping alone. Cite each rule's source and document the non-binary simplification per rule in the docstring. Acceptance: T020 green.
- [x] T022 [US2] Write the conservation test (SC-002) in `epocha/apps/demography/tests/test_inheritance.py`: parametrised over all five succession rules, assert that the sum of the allocation mapping plus the tax routed to the treasury equals the deceased's estate exactly, with a documented decimal tolerance and zero tolerance on the integer path. **This is the invariant that protects §4.2 and §4.8, both CONVERGED.** Acceptance: the test passes for all five rules; if any rule leaks or fabricates value, STOP and escalate.
- [x] T023 [P] [US2] Write the RED test then implement `transfer_loans_as_lender(deceased, heirs) -> None` in `epocha/apps/demography/inheritance.py` and `tests/test_inheritance.py`: active `Loan` rows where the deceased is `lender` transfer to heirs by the same distribution rule; with no human heirs they move to `lender=None, lender_type="banking"` and keep being serviced. Document the MVP limitation that agent-to-agent loans without heirs are silently cancelled. Acceptance: tests green.

**Checkpoint**: User Story 2 delivers independently — estates settle and conserve value under all five rules.

---

## Phase 5: User Story 3 — Orphans are taken in and death leaves a mark (Priority: P2)

**Goal**: minors who lose both parents get a caretaker or state wardship; the bereaved remember.

**Independent test**: kill both parents of a minor and assert caretaker assignment by priority; assert spouse, children and strong ties get weight-0.9 memories.

- [ ] T024 [US3] Write the RED tests for `assign_orphan_caretaker` in `epocha/apps/demography/tests/test_inheritance.py`: priority is nearest living relative in the same zone (sibling, grandparent, aunt/uncle), then any living relative anywhere, then `None`; with `None` the orphan is flagged and the treasury covers subsistence; the orphan REMAINS the owner of inherited assets while the caretaker only administers (fix MISS-1). Acceptance: failing tests.
- [ ] T025 [US3] Implement `assign_orphan_caretaker(minor, tick) -> object | None` in `epocha/apps/demography/inheritance.py`, writing `Agent.caretaker_agent`. **This is the Plan 4 orchestrator step 3 entry point** — keep the signature callable without global state (decision D3). Acceptance: T024 green.
- [ ] T026 [US3] Write the RED test for `generate_mourning_memories` in `epocha/apps/demography/tests/test_inheritance.py`: surviving spouse, surviving children and ties with `Relationship.strength > 0.6` each receive a `Memory` with `emotional_weight = 0.9`. **Trap 2 verbatim**: the filter is `Relationship.strength`, NOT `Agent.strength` — `Agent.strength` is an inherited physical trait (h² = 0.55) and filtering on it would send grief memories to muscular agents instead of close friends. Acceptance: failing test.
- [ ] T027 [US3] Implement `generate_mourning_memories(deceased, tick) -> None` in `epocha/apps/demography/inheritance.py`, creating memories that the existing `propagate_information` system carries to the wider society with decayed weight. **Trap 2 verbatim**: filter on `Relationship.strength > 0.6`. Acceptance: T026 green.
- [ ] T028 [US3] Write the RED test for `process_inheritance_batch` in `epocha/apps/demography/tests/test_inheritance.py`: multiple deaths in one tick process in descending-age order (fix C-3, the deterministic tiebreak matching the Simultaneous Death Act convention); estate tax applies ONCE per actual transfer, not cumulatively when assets chain across several agents dying in the same tick; a grandparent cannot bequeath to a father already dead in an earlier tick, and the tax is NOT re-applied on that onward move (fix MISS-5). Acceptance: failing tests.
- [ ] T029 [US3] Implement `process_inheritance_batch(simulation, tick, deceased_agents) -> None` in `epocha/apps/demography/inheritance.py`: order by descending age, call the extended `dissolve_on_death` per deceased (decision D1, T002), settle each estate via T017/T019/T021, transfer loans, assign caretakers, generate mourning memories, and emit `DemographyEvent` rows of type `INHERITANCE_TRANSFER`. **This is the death-path entry point Plan 4 calls.** Acceptance: T028 green, plus the whole `test_inheritance.py` suite green.

**Checkpoint**: `inheritance.py` complete. User Stories 1, 2 and 3 all deliver.

---

## Phase 6: User Story 4 — Migrating with economic information (Priority: P2)

**Goal**: agents see wages, unemployment, distance and expected gain before choosing; households move together.

**Independent test**: build two zones with known wages and unemployment; assert the outlook block reports them and that expected gain follows the declared Harris-Todaro variant.

- [ ] T030 [P] [US4] Write the RED tests for the zone computations in `epocha/apps/demography/tests/test_migration.py`: `compute_zone_wage` averages `EconomicLedger` rows of `transaction_type="wage"` over a 5-tick window per capita; `compute_zone_unemployment` returns the fraction with a role but zero wage over 3 ticks and guards a zero-population zone without dividing by zero (FR-028). Acceptance: failing tests.
- [ ] T031 [US4] Create `epocha/apps/demography/migration.py` with its module docstring (citing Harris & Todaro 1970, Mincer 1978, O'Rourke 1994, Simon 1955) and implement `compute_zone_wage(simulation, zone, tick, window=5) -> float` and `compute_zone_unemployment(simulation, zone, tick) -> float` using ORM aggregates, never Python loops over agents (no N+1). Acceptance: T030 green, query counts asserted.
- [ ] T032 [P] [US4] Write the RED test then implement `compute_distance_cost(from_zone, to_zone, world) -> int` in `epocha/apps/demography/migration.py` and `tests/test_migration.py`: `ceil(distance_km / (walking_speed_km_per_day * tick_duration_days))` using the existing `World.distance_scale` and `TRAVEL_SPEEDS`, with walking speed 25 km/day (verified in the 2026-04-12 audit). Acceptance: tests green.
- [ ] T033 [US4] Write the RED test then implement `compute_expected_gain(unemployment_j, wage_j, wage_current, distance_cost_j) -> float` in `epocha/apps/demography/migration.py` and `tests/test_migration.py`: `E[gain_j] = (1 - unemployment_j) * wage_j - wage_current - distance_cost_j`. The docstring MUST state that this is an operational variant of Harris & Todaro (1970), that the canonical form compares `p*w_urban + (1-p)*w_informal` against rural income, that the informal-sector wage is set to zero here, and that the simplification is tunable and documented. Acceptance: tests green.
- [ ] T034 [US4] Write the RED test then implement `build_migration_outlook(agent, simulation, tick, zone_stats) -> dict` in `epocha/apps/demography/migration.py` and `tests/test_migration.py`: the block carries wage differential, unemployment, distance cost, zone stability (`Government.stability`) and expected gain per reachable zone. **Zone aggregates are computed once per tick and passed in as `zone_stats`, never recomputed per agent** — this is the N+1 risk the plan flags, because Plan 4 will call this per tick. Acceptance: tests green with `assertNumQueries` proving the per-agent call adds no zone queries.
- [ ] T035 [US4] Write the RED test then implement `coordinate_family_migration(agent, target_zone, tick, template) -> list` in `epocha/apps/demography/migration.py` and `tests/test_migration.py` (Mincer 1978): partner and children under `template["migration"]["adulthood_age"]` move in the same tick; a SINGLE `DemographyEvent` of type `MIGRATION` carries `household_members`; minors are NOT called to the decision loop for that migration; adult children decide independently and are not dragged along. Acceptance: tests green.

**Checkpoint**: voluntary migration delivers. User Story 4 complete.

---

## Phase 7: User Story 5 — Flight, entrapment and mass flight (Priority: P3)

**Goal**: the starving flee on instinct; those who cannot flee become a visible crisis.

**Independent test**: starve an agent past `flight_trigger_ticks` with a better zone available and assert automatic flight; repeat with no better zone and assert `trapped_crisis` and its propagation.

- [ ] T036 [US5] Write the RED tests for `evaluate_emergency_flight` in `epocha/apps/demography/tests/test_migration.py`: fires ONLY when all three conditions hold simultaneously — wealth below `compute_subsistence_threshold`, `consecutive_ticks_under_subsistence >= flight_trigger_ticks` (default 30), and at least one zone with positive expected gain (fix I-5). Assert it does NOT fire when only two hold, in particular the no-positive-zone case. Acceptance: failing tests.
- [ ] T037 [US5] Implement `evaluate_emergency_flight(agent, simulation, tick, template, zone_stats) -> object | None` in `epocha/apps/demography/migration.py`, returning the highest-gain target zone or `None`, using the existing `compute_subsistence_threshold` helper. Docstring cites Simon (1955) bounded rationality for why deliberation is bypassed below the survival threshold. Acceptance: T036 green.
- [ ] T038 [US5] Write the RED tests for the forced paths in `epocha/apps/demography/tests/test_migration.py`: a triggered flight migrates to the highest-gain zone bypassing the LLM, applies family coordination, and writes a memory with `emotional_weight = 0.85`; a trapped agent emits `TRAPPED_CRISIS` AND propagates a memory with `emotional_weight = 0.95` and `source_type = "public"` to every co-zone agent (fix MISS-3); more than 30% of a zone's living population fleeing within `flight_trigger_ticks` emits `MASS_FLIGHT` with the agent list. Acceptance: failing tests.
- [ ] T039 [US5] Implement `process_emergency_flight(simulation, tick) -> None` in `epocha/apps/demography/migration.py`: compute zone aggregates ONCE, drive T037 over the population, execute flights with `coordinate_family_migration`, emit `TRAPPED_CRISIS` with MISS-3 co-zone propagation, and emit `MASS_FLIGHT` above the 30% threshold. **This is the Plan 4 orchestrator step 5 entry point** — callable without global state (decision D3). Acceptance: T038 green, plus the whole `test_migration.py` suite green.
- [ ] T040 [P] [US5] Write the determinism test (SC-003) in `epocha/apps/demography/tests/test_migration.py` and `tests/test_inheritance.py`: two identically-seeded runs of the birth path and of the flight path produce identical state. Acceptance: passes; if it flakes, a draw is escaping `get_seeded_rng` — STOP and escalate rather than reseeding to hide it.

**Checkpoint**: `migration.py` complete. All five user stories deliver.

---

## Phase 8: Polish and closure

- [ ] T041 Write the era coverage test (SC-004) in `epocha/apps/demography/tests/test_inheritance.py`: all five era templates (`pre_industrial_christian`, `pre_industrial_islamic`, `industrial`, `modern_democracy`, `sci_fi`) load and drive inheritance and migration without error, exercising a different succession rule per era. Acceptance: passes for all five.
- [ ] T042 Assert SC-005 in CI terms: run `docker compose -f docker-compose.local.yml exec -T web python manage.py makemigrations --check --dry-run` and confirm it is clean. **If it is not, a field was invented — most likely `education` instead of `education_level` (trap 1). Revert it; do not accept the migration.** Acceptance: command exits clean.
- [ ] T043 Extend §4.1 of `docs/whitepaper/epocha-whitepaper.md` AND `docs/whitepaper/epocha-whitepaper.it.md` with the inheritance and migration models AND the couple-dissolution MISS-4 same-tick change absorbed from the superseded T003: the couple `dissolve_on_death` idempotent-per-partner contract; the Falconer & Mackay kernel; the per-trait heritability table with its primary sources; the four social-class rules; the five succession rules with their sources; the estate-tax rates; the Harris-Todaro operational variant with its declared simplification; Mincer family coordination; and emergency flight with the I-5 constraint. Update the §4.1 front-matter `frozen-at-commit` and every per-section "as of the pinned commit" status to the branch's merge SHA (this is the single re-pin the frozen mechanism expects — do it here, not piecemeal earlier). State every simplification and what it loses (FR-030, FR-032). Acceptance: both languages carry equivalent content; the §4.1.3 dissolution prose matches the new contract; the frozen-at-commit reflects the merge SHA; every author-year cited has a §13 bibliography entry.
- [ ] T044 Add `inheritance.py` and `migration.py` to the §4.1 row of the whitepaper doc-sync table in ALL FOUR synchronised copies (FR-032): `CLAUDE.md` Documentation Sync section, the Contributing section of `README.md` and `README.it.md`, and the memory `feedback_whitepaper_doc_sync.md` plus its backup at `docs/memory-backup/feedback_whitepaper_doc_sync.md`. Acceptance: the four copies list identical modules; a diff of the tables shows no drift.
- [ ] T045 Run the full suite and lint in the container: `docker compose -f docker-compose.local.yml exec -T web pytest -q` and `... ruff check .` (SC-001). Acceptance: zero failures, zero xfail, ruff clean. Report the actual output; do not claim green without reading it.
- [ ] T046 Dispatch the phase-6 heavy gate: `critical-analyzer` as a hostile scientific reviewer on the CODE of `inheritance.py`, `migration.py` and the `couple.py` change, verifying every formula and constant against its cited source, checking cross-module consistency of units and definitions, and the conservation invariant. Run the mandatory convergence loop — audit, fix, re-audit — until the verdict is explicitly CONVERGED with zero INCORRECT and zero UNJUSTIFIED (SC-007). No "close enough". Acceptance: an explicit CONVERGED verdict.
- [ ] T047 Confirm SC-008 by inspection: `assign_orphan_caretaker` and `process_emergency_flight` exist with signatures callable from a Plan 4 orchestrator, and `simulation/engine.py` is byte-for-byte untouched by this branch (`git diff develop -- epocha/apps/simulation/engine.py` is empty). Wiring is Plan 4's job. Acceptance: the diff is empty and both entry points are importable.

---

## Dependencies

```text
Phase 2 (T001-T007)  ── blocking ──┐
                                   ├─→ Phase 3 US1 (T008-T015) ─┐
                                   ├─→ Phase 4 US2 (T016-T023) ─┤
                                   │        └─→ Phase 5 US3 (T024-T029)
                                   ├─→ Phase 6 US4 (T030-T035) ─┤
                                   │        └─→ Phase 7 US5 (T036-T040)
                                   └────────────────────────────┴─→ Phase 8 (T041-T047)
```

- Phase 2 blocks everything: T002 (D1) is a hard prerequisite of T029, and T005/T007 (the kernel) of all of Phase 3.
- Phase 5 depends on Phase 4: `process_inheritance_batch` settles estates.
- Phase 7 depends on Phase 6: emergency flight consumes the expected-gain computation.
- `inheritance.py` and `migration.py` never import each other, so Phases 3-5 and Phases 6-7 are independent tracks. Phase 5 executes them sequentially anyway — one atomic task at a time, flag before moving on.

## Implementation strategy

**MVP**: Phase 2 + Phase 3 (User Story 1). That alone gives a demography where births carry heredity — demonstrable, testable, mergeable.

**Increments**: Phase 4+5 completes `inheritance.py` and closes the death path. Phase 6+7 completes `migration.py`. Phase 8 closes the work item.

**Model policy**: phase-5 execution runs on Sonnet per the model policy; escalate to Opus for any strategic decision. T046 (the heavy gate audit) is Opus.

**Confidence level at closure**: **unit tests only**. Neither module is observable in a live run until Plan 4 wires the orchestrator. Do not report this work as verified in a running simulation; that evidence is Plan 4's deliverable.

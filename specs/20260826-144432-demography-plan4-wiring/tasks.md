# Tasks: Demografia Plan 4 — inizializzazione, cablaggio, snapshot di popolazione

**Feature**: `20260826-144432-demography-plan4-wiring`
**Input**: [spec.md](spec.md) (CONVERGED, gate round 5), [plan.md](plan.md)

**Test command per task** (unless a task names another):

```bash
docker compose -f docker-compose.local.yml exec -T web pytest <path> -q
```

**Full suite**, required green before the first task and after each phase:

```bash
docker compose -f docker-compose.local.yml exec -T web pytest -q
```

## Conventions binding every task

- **RED first**: write the test, run it, watch it fail, then implement. A test
  never seen failing is not a test.
- **Mutation proof** where the task says so: introduce the named mutation, watch
  the test go red, revert. When a payload or a constant changes, re-run the
  mutation battery against the **previous** version too — a repair that deletes
  a witness while adding one has happened twice on this project.
- **Reuse statement** before writing any non-trivial code: "Searched [where] for
  [what]. Found [X] — reuse/extend. / Found nothing — building new."
- One task, one commit, checkbox flipped in the same commit.
- No demography module is rewritten. The two named exceptions are
  `apply_inheritance_at_birth` (T009) and `process_emergency_flight` (T024).

---

## Phase 1 — Setup

- [x] T001 Run the full suite and record the baseline count in the task's commit message; a red baseline is handled by the fix-vs-STOP rule before any other task starts. Command: `docker compose -f docker-compose.local.yml exec -T web pytest -q` — **baseline 1582 passed, ruff clean, measured 2026-08-27 before the first task.**
- [x] T002 [P] Add the `names` section to the era-template schema in `epocha/apps/demography/template_loader.py`, with the test that a template carrying an unknown sibling key is still rejected. Mutation proof: delete the new schema entry, the acceptance test goes red; delete the unknown-key rejection, the rejection test goes red. Test: `epocha/apps/demography/tests/test_template_loader.py`
- [x] T003 [P] Add the `names` section (male, female given-name pools) to all five templates in `epocha/apps/demography/templates/*.json`, with a test asserting every template loads and every pool is non-empty. Test: `epocha/apps/demography/tests/test_template_loader.py`

## Phase 2 — Foundational (blocks every user story)

- [x] T004 Add `consecutive_ticks_under_subsistence` (PositiveIntegerField, default 0) to `epocha/apps/agents/models.py` with its migration; test that a freshly created agent reads 0. Test: `epocha/apps/demography/tests/test_starvation_counter.py`
- [ ] T005 Create `epocha/apps/demography/orchestrator.py` with the module docstring stating the tick-order contract, and `DEMOGRAPHY_STEPS` as a tuple of `(step_index, phase_name, callable)` — callables stubbed to no-ops at this task. Test: the tuple is importable, indices are contiguous from 1, phase names are unique. Test: `epocha/apps/demography/tests/test_orchestrator_order.py`
- [ ] T006 Add the `demography_enabled` activation predicate helper in `epocha/apps/demography/orchestrator.py`, reading `simulation.config`. Test: absent key is false, explicit false is false, explicit true is true; and the era template's presence alone does **not** activate. Test: `epocha/apps/demography/tests/test_orchestrator_order.py`
- [ ] T007 Add the shared per-`(tick, phase)` RNG derivation helper used by every step in `epocha/apps/demography/orchestrator.py`, reusing `get_seeded_rng`. Reuse statement required. Test: two agents in the same phase draw from one stream (different values), and the same `(tick, phase)` reproduces the sequence. Test: `epocha/apps/demography/tests/test_orchestrator_order.py`

## Phase 3 — US1 The population lives (P1)

### Birth path

- [ ] T008 [US1] Write the RED test for per-newborn RNG independence: two newborns created in the same tick from different parents must not receive identical sex and orientation systematically (SC-006). Test: `epocha/apps/demography/tests/test_inheritance_birth_rng.py`
- [ ] T009 [US1] Fix the RNG derivation in `apply_inheritance_at_birth` (`epocha/apps/demography/inheritance.py`) so the stream is derived per newborn, not per `(simulation, tick, "inheritance")`. Mutation proof: restore the old derivation, T008 goes red. Update the function's docstring to describe the new derivation and drop any text describing the defect as current. **Doc-sync, same commit**: whitepaper §4.1.4 in both languages describes this derivation and its reproducibility consequence — update both, or the commit violates the project's doc-sync rule.
- [ ] T010 [P] [US1] Add the newborn-name selector in `epocha/apps/demography/orchestrator.py`: name drawn from the template pool with the phase RNG, never from the LLM (FR-001a). Test: same seed and tick reproduce the same name; the name comes from the pool. Test: `epocha/apps/demography/tests/test_orchestrator_birth.py`
- [ ] T011 [US1] Implement the birth orchestrator in `epocha/apps/demography/orchestrator.py`: create the `Agent` with `birth_tick`, `parent_agent`, `other_parent_agent`, the pooled name, then call `apply_inheritance_at_birth`, then emit a `DemographyEvent` of type `BIRTH` carrying the step index in `payload` (US1 test 2). Newborns and their events are written in bulk (FR-016a). Test: `epocha/apps/demography/tests/test_orchestrator_birth.py`
- [ ] T012 [US1] Wire `tick_birth_probability` and `resolve_childbirth_event` into the fertility step so the orchestrator persists what the pure resolvers decide, including maternal death and neonatal survival. Test: a mother who dies in childbirth is marked dead and the surviving newborn exists. Test: `epocha/apps/demography/tests/test_orchestrator_birth.py`

### Death path

- [ ] T013 [US1] Implement the death orchestrator in `epocha/apps/demography/orchestrator.py`: evaluate `tick_mortality_probability` over the living population with one stream, mark `is_alive`, `death_tick`, `death_cause` from `sample_death_cause`, in bulk. Test: `epocha/apps/demography/tests/test_orchestrator_death.py`
- [ ] T014 [US1] Emit the `DEATH` event with the step index in `payload`, in one `bulk_create`, and call `process_inheritance_batch` with the tick's freshly-deceased list, satisfying its documented precondition that `is_alive=False` is already set by the caller. Test: `epocha/apps/demography/tests/test_orchestrator_death.py`
- [ ] T015 [US1] Add the zero-population guard: with no living agent the block completes without exception and writes no event. Test: `epocha/apps/demography/tests/test_orchestrator_order.py`

## Phase 4 — US2 The tick order is declared and respected (P1)

- [ ] T016 [US2] Replace the T005 stubs with the real callables in `DEMOGRAPHY_STEPS`, in the order the plan declares: separations, couples, mortality+death, succession, starvation counter, forced migration, fertility+birth, snapshot. Test that the declared order is inspectable and its indices match the phase names. Test: `epocha/apps/demography/tests/test_orchestrator_order.py`
- [ ] T017 [US2] Mutation proof for FR-004: an agent who dies at T produces no birth at T; swapping the mortality and fertility steps turns the test red. Test: `epocha/apps/demography/tests/test_orchestrator_order.py`
- [ ] T018 [US2] Mutation proof for FR-005 and FR-005a: a couple formed at T can conceive at T, a couple separated at T cannot; moving the couple step after fertility, or the separation step after the formation step, turns the test red. Test: `epocha/apps/demography/tests/test_orchestrator_order.py`
- [ ] T019 [US2] Mutation proof for FR-006: succession of an agent who died at T happens at T, after the death; swapping the two steps turns the test red. Test: `epocha/apps/demography/tests/test_orchestrator_order.py`
- [ ] T020 [US2] Mutation proof for FR-007: an agent who inherits at T is evaluated for emergency flight on the post-inheritance wealth; moving the migration step before succession turns the test red. Test: `epocha/apps/demography/tests/test_orchestrator_order.py`
- [ ] T021 [US2] Implement the block entry point `run_demography_tick(simulation, tick)` in `epocha/apps/demography/orchestrator.py`: returns immediately when the predicate of T006 is false, otherwise iterates `DEMOGRAPHY_STEPS`. Test: `epocha/apps/demography/tests/test_orchestrator_order.py`
- [ ] T022 [US2] Call `run_demography_tick` from `run_simulation_loop` in `epocha/apps/simulation/tasks.py`, **after `run_economy` and before the chord header is built** (plan D2b), degrading explicitly on `FileNotFoundError` and on `ValueError` from `load_template` with a log line each, and introducing no blind `except Exception`. Test: a missing template and a malformed template each log and skip without aborting the tick; and an agent who dies in the block is absent from the chord header of the same tick. Test: `epocha/apps/simulation/tests/test_engine_demography_wiring.py`
- [ ] T023 [US2] Assert SC-004: a simulation with demography inactive issues the same query count as before the wiring and produces no demography event. Test: `epocha/apps/simulation/tests/test_engine_demography_wiring.py`

## Phase 5 — US3 The starvation counter exists (P1)

- [ ] T024 [US3] Change `process_emergency_flight` in `epocha/apps/demography/migration.py` to read the persisted counter instead of receiving the mapping from the caller (FR-012), keeping the flight logic untouched. Update the docstring, which currently states that Plan 4 owns building the mapping. **Doc-sync, same commit**: whitepaper §4.1.5 in both languages states that the counter has no storage and that flight cannot fire in a live run — both sentences become false here. Test: `epocha/apps/demography/tests/test_starvation_counter.py`
- [ ] T025 [US3] Implement the counter step in `epocha/apps/demography/orchestrator.py`: one bulk read and one `bulk_update`, incrementing when `agent.wealth` is below `compute_subsistence_threshold` and resetting to zero otherwise — the same predicate the flight trigger uses (FR-011). Test: `epocha/apps/demography/tests/test_starvation_counter.py`
- [ ] T026 [US3] Mutation proof for SC-003: a counter that never resets fails a test, and moving the counter step before succession fails a test on a fixture where the heir rises above the threshold thanks to the tick's inheritance. Test: `epocha/apps/demography/tests/test_starvation_counter.py`

## Phase 6 — Initialization

- [ ] T027 Create `epocha/apps/demography/initialization.py` with the `birth_tick` backfill consistent with each agent's generated age, and the post-condition that no living agent is left with `birth_tick` NULL (FR-013). Test: `epocha/apps/demography/tests/test_initialization.py`
- [ ] T028 Add initial-couple formation to `epocha/apps/demography/initialization.py`, reusing `stable_matching` and `form_couple` — reuse statement required — so the default template does not make birth impossible in the first ticks (FR-014). Test: `epocha/apps/demography/tests/test_initialization.py`
- [ ] T029 Call the initialization from the world-generation path, **under the same activation predicate as the block** (T006): a simulation that never enables demography is left untouched, or FR-009's invariance breaks at generation time. Assert both post-conditions end to end, and assert the untouched case. Test: `epocha/apps/demography/tests/test_initialization.py`

## Phase 7 — PopulationSnapshot

- [ ] T030 Create `epocha/apps/demography/snapshot.py` writing all ten data fields of `PopulationSnapshot` with set-based aggregates, no per-agent query. Test: `epocha/apps/demography/tests/test_population_snapshot.py`
- [ ] T031 Assert SC-007 field by field against a hand-built fixture that carries at least one birth, one death, one zone move, a sex ratio different from one, and at least one active couple — so that no expected value coincides with a model default. Test: `epocha/apps/demography/tests/test_population_snapshot.py`
- [ ] T032 Add the snapshot as the last step of `DEMOGRAPHY_STEPS` and assert every tick leaves exactly one snapshot row. Test: `epocha/apps/demography/tests/test_population_snapshot.py`

## Phase 8 — Cost budget

- [ ] T033 Measure and pin SC-005 part A: at equal vital events with identical family structures and a fixed zone count, doubling the living agents leaves the demography block's query count identical, with the absolute value written in the test. The measurement boundary is `assertNumQueries` around the single synchronous `run_demography_tick` call — which is what D2b's placement makes possible — not around the whole tick. Test: `epocha/apps/demography/tests/test_demography_cost.py`
- [ ] T034 Measure and pin SC-005 part B: at fixed population, varying the events, the count never exceeds `a + b·deaths + c·intents + d·flights` at the worst-case coefficients of FR-016a, and at least one fixture reaches the bound. Record the measured coefficients in the test and in the plan. Test: `epocha/apps/demography/tests/test_demography_cost.py`

## Phase 9 — US1 acceptance and documentation

- [ ] T035 [US1] End-to-end acceptance of SC-001: an N-tick simulation with demography active produces at least one birth and one death and a population that changes. Test: `epocha/apps/demography/tests/test_demography_e2e.py`
- [ ] T036 Update whitepaper §4.1 in **both** languages with the orchestrators, the declared order and the block's position in the tick (plan D2b), then close the FR-017 inventory row by row — the rows T009 and T024 already closed in their own commits are checked, not rewritten (Abstract, §4.1.1–§4.1.3, §4.1.4, §4.1.5, §4.2, §7.4, §7.5, §9, §10, §11, §12, Appendix B), leaving every calibration deferral untouched. Test: `docker compose -f docker-compose.local.yml exec -T web pytest epocha/apps/demography/tests/test_citation_hygiene.py -q`
- [ ] T037 Update `docs/build-map/epocha-build-map.html` in both languages, run `scripts/build_map_i18n.py fingerprint`, republish to the same artifact URL. Test: `docker compose -f docker-compose.local.yml exec -T web pytest epocha/apps/dashboard/tests/test_build_map_bilingual.py -q`
- [ ] T038 Full suite green, then Matteo-mode review of the whole branch diff before the phase-6 gate. Command: `docker compose -f docker-compose.local.yml exec -T web pytest -q && docker compose -f docker-compose.local.yml exec -T web ruff check .`

---

## Dependencies

- Phase 1 and 2 block everything: the schema extension (T002-T003) is needed by
  the birth name selector, the counter field (T004) by the counter step, and the
  step tuple (T005) by every ordering task.
- US1 (Phase 3) depends on Phase 2 and on nothing else; it is the MVP.
- US2 (Phase 4) depends on US1, because the order it proves is an order over
  steps that must exist.
- US3 (Phase 5) depends on T004 and on the migration step being in the tuple.
- Initialization (Phase 6) is independent of Phases 3-5 and can run in parallel
  with them, but SC-001 (T035) needs it.
- Cost (Phase 8) needs the whole block wired, so it comes after Phases 3-7.

## Parallel opportunities

- T002 and T003 touch different files and run in parallel.
- T010 is parallel to T008-T009 once T002-T003 land.
- Phase 6 runs in parallel with Phases 3-5 for a second worker.

## MVP scope

Phases 1, 2 and 3: the population lives. That alone closes the project's
largest gap — an audited scientific model that does not run — and every later
phase makes the result measurable, ordered, or documented rather than possible.

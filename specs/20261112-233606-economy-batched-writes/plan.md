# Implementation Plan: per-tick writes linear in the number of agents

**Branch**: `20261112-233606-economy-batched-writes` | **Date**: 2026-11-12 | **Spec**: `specs/20261112-233606-economy-batched-writes/spec.md` (revision 2)

**Input**: Feature specification from `specs/20261112-233606-economy-batched-writes/spec.md` (Italian, normative).

**API contract**: contract unchanged.

## Summary

Three `bulk_update` calls write every row of a per-tick update in one SQL statement whose `CASE` has one branch per row per column, which PostgreSQL evaluates in time proportional to the square of the rows: `epocha/apps/economy/expectations.py:235` (measured: 285 s for one statement over 10,020 rows), `epocha/apps/economy/engine.py:898` and `epocha/apps/world/stratification.py:192` (the political cycle runs every tick). The plan passes `batch_size=settings.EPOCHA_BULK_UPDATE_BATCH_SIZE` to the three, with the setting in `config/settings/base.py` and its default chosen by a measurement (T001-T003), guards the statement shape with three tests that fail today, measures the economy step before and after with a script outside the suite, and updates the §4.2 sentence and the 26 line citations that the change makes untrue. No value, read, computation or schema changes.

## Technical Context

**Language/Version**: Python 3.12 (project image), Django 5.1.15 (verified in the image).

**Primary Dependencies**: psycopg 3.3.3 (verified in the image), client-side binding; pytest-django (`settings` fixture).

**Storage**: PostgreSQL (tests run on it, as in production).

**Testing**: pytest with pytest-django; `django.test.utils.CaptureQueriesContext` for the shape guards (already used in `epocha/apps/demography/tests/test_inheritance.py:5573`).

**Target Platform**: the simulation's Celery worker.

**Project Type**: Django web service.

**Performance Goals**: spec SC-002 (ratio of the economy step at 2,000 and 200 founders at most 15) and SC-003 (economy step at 2,000 founders at most 15 s median).

**Constraints**: values written bit-identical (spec FR-004, SC-004); every run of tests and scripts in the session's own Docker project, never the `epocha` project.

**Scale/Scope**: three call sites, one setting, one test helper, three tests, one script, the §4.2 sentence and 26 line citations in the two whitepapers.

## Constitution Check

- **I. Scientific Method Above All**: no model, formula or parameter changes. The batch size is an engineering heuristic, declared tunable, with its cost model and a pointer to the measured table in its comment. PASS.
- **II. Verify Before Asserting**: the Django behaviour the design relies on (no backend limit on PostgreSQL, `transaction.atomic` around the batches, a cast around each `CASE`) was read in the installed Django 5.1.15 source; the political cycle running every tick was read in `world/government.py:779-797` and `simulation/engine.py:532`; the cost model is labelled an estimate until T002 measures it. PASS.
- **III. Adversarial Scientific Audit**: round 1 on spec, plan and tasks done (spec, *Stato dell'audit*); the phase-6 code audit as usual. PASS.
- **IV. Three-Step Design Process**: recorded in the spec, section *Decisioni di design*, with what each step and the audit killed. PASS.
- **V. Evidence-Based Verification**: SC-001 to SC-004 are measured by tests and a script; SC-005 is reported with its number and a profile. PASS.

## Reuse statement

Searched `epocha/` and `config/` for `batch_size` and `BATCH_SIZE`: found only `EPOCHA_KG_EMBEDDING_BATCH_SIZE` (`config/settings/base.py:240`), the knowledge graph's embedding batches, a different quantity; its **mechanism** (an `env.int` setting) is reused for the new setting. Searched `epocha/common/` for a database-write helper: found none, and none is added. Searched the test suites for a helper that counts rows per captured statement: found none (`CaptureQueriesContext` is used once, in `demography/tests/test_inheritance.py:5573`, for a query count), so `case_update_rows` is new. Searched `scripts/` on `develop` for a world builder without LLM: found none (`scripts/build_map_i18n.py` only; the founder builder of the measurement scripts lives on the unmerged couples branch), so the script builds its agents with `Agent.objects.bulk_create`, following the agent fields of the economy test fixtures, and reuses `initialize_economy` and `process_economy_tick_new` unchanged.

## Architectural placement

The batch size is a setting in `config/settings/base.py`, the place of every other tunable quantity of the project; `economy` and `world` read it through `django.conf.settings` at call time, with no dependency between the two apps. The shape helper serves the tests of two apps, so it goes to the shared core as `epocha/common/testing.py`, a module whose docstring says it is imported only by tests; `epocha/common/` has no test package today, and putting the helper in `economy/tests/` would make the world tests import the economy's tests. The script goes to `scripts/`, never collected by the suite (`python_files = ["test_*.py"]`, `pyproject.toml`).

## Design details

**PD-01, the batch size.** The measurement script of PD-03 carries `test_batch_size_candidates`, run before the setting exists. On the world of PD-03 at 2,000 founders, after tick 1 has created the expectations (R rows, printed), it loads the rows in `id` order and times one full `AgentExpectation.objects.bulk_update(rows, FIVE_FIELDS, batch_size=B)` for B in {5, 10, 15, 25, 50, 100, 200, 500}, three repetitions each, then times the first candidate again to detect drift, and times b as the median of 20 one-row updates. The unbatched call is not re-timed (285 s, measured on 2026-11-12). It prints, per candidate, the median total and the per-statement time, and a least-squares fit of t(B) = a·B² + c·B + b on the per-statement times, which is reported and never used to choose. T003 copies the table into *Measurements* below and picks the B with the lowest measured median total; ties within 10% go to the larger B (fewer statements). If the minimum sits at an edge of the grid, T002 is rerun once with the grid extended past that edge (halving below 5, doubling above 500). If the drift check differs from the first timing by more than 20%, the table is discarded and T002 is rerun. If no candidate writes the R rows in under 5 s, T003 stops and escalates to the user: batching alone cannot meet SC-003, and the `VALUES` alternative of the spec FAQ needs a decision.

**PD-02, the shape guard.** A helper `case_update_rows(captured_queries, model, field_count) -> list[int]` keeps the captured statements whose SQL starts with `UPDATE "<model._meta.db_table>"` and contains `CASE WHEN` (on PostgreSQL the cast renders as `(CASE WHEN ...)::type`, never `CAST(`), and returns, in execution order, `sql.count("WHEN") // field_count`. The guards set `settings.EPOCHA_BULK_UPDATE_BATCH_SIZE` with pytest-django's `settings` fixture, which accepts a name that does not exist yet, so the red run fails on the shape assertion and not on a missing attribute. Each guard is parametrized on two batch sizes, one dividing the rows and one leaving a remainder, so a size hard-coded at the call site fails one of them.

**PD-03, the measurement script.** `scripts/measure_economy_write_cost.py` runs under pytest (`pytest scripts/measure_economy_write_cost.py -s -p no:cacheprovider -k <function>`), every function marked `@pytest.mark.django_db(transaction=True)` (decision D-05-E-14 of the marital-fertility branch, `scripts/measure_marital_schedule_run.py:457-459` there): every write is committed, so a timing does not carry the row versions of the previous one. It reads `ECONOMY_COST_FOUNDERS` (default 2000), `ECONOMY_COST_TICKS` (default 5) and `ECONOMY_COST_SEED` (default 20261112) from the environment and prints them with every result. It builds one simulation with `seed=SEED`, a `World` with `tick_duration_hours=730`, a `Government`, two zones, the founders through one `Agent.objects.bulk_create` with role and personality drawn from `random.Random(SEED)`, then `initialize_economy(simulation, template_name="pre_industrial")`. `test_economy_step_cost` runs tick 1 untimed (it creates the expectations), then for ticks 2..1+TICKS records `time.perf_counter()` around `process_economy_tick_new(simulation, tick)` under `CaptureQueriesContext`; prints per tick the time, the total number of `UPDATE` statements, and count and maximum of `case_update_rows` for `AgentExpectation` (5 fields) and `Agent` (2 fields); then the median time, `simulation.id`, the seed and the SHA-256 fingerprint of spec FR-006. It is a measurement, not a judgment: SC-002 to SC-004 are judged by reading its output in T014.

**PD-04, base and head runs.** The "before" numbers come from the same script and helper copied, unmodified, into a temporary worktree at the base commit `2223968` (they do not exist there); the copies are deleted with the worktree after the runs and never committed there. Every fingerprint run is a separate pytest invocation, which creates the test database from scratch (the project's `addopts` has no `--reuse-db`), so the simulation gets the same `id` in every run; the script prints it and T014 compares it before comparing fingerprints, because the economy's random generator is derived from `simulation.id` and the seed (`economy/rng.py:31-55`).

## Project Structure

### Documentation (this feature)

```text
specs/20261112-233606-economy-batched-writes/
├── spec.md
├── plan.md
└── tasks.md
```

### Source Code (repository root)

```text
config/settings/base.py                             # + EPOCHA_BULK_UPDATE_BATCH_SIZE, validated
epocha/common/testing.py                            # new, test-only shape helper (PD-02)
epocha/apps/economy/expectations.py                 # bulk_update(..., batch_size=...)
epocha/apps/economy/engine.py                       # bulk_update(..., batch_size=...)
epocha/apps/world/stratification.py                 # bulk_update(..., batch_size=...)
epocha/apps/economy/tests/test_expectations.py      # + shape guard
epocha/apps/economy/tests/test_engine.py            # + shape guard
epocha/apps/world/tests/test_stratification.py      # + shape guard
scripts/measure_economy_write_cost.py               # new, measurement (PD-03)
docs/whitepaper/epocha-whitepaper.md                # §4.2 sentence, 13 line citations
docs/whitepaper/epocha-whitepaper.it.md             # §4.2 sentence, 13 line citations
```

**Structure Decision**: single Django project; no new app, no migration.

## Documentation impact

- Whitepapers §4.2, EN line 1162 and IT line 1199 at the base commit: the sentence on "two terminal `bulk_create` and `bulk_update` calls ... two writes per tick regardless of the agent count" becomes one `bulk_create` and one `bulk_update` in batches of `EPOCHA_BULK_UPDATE_BATCH_SIZE` rows, 1 + ⌈R/B⌉ statements.
- Line citations shifted by the added `from django.conf import settings` line (one per module), 13 per whitepaper, 26 in all. EN: `expectations.py:39-40` at lines 1146, 1160, 2353, 3464; `expectations.py:43-80` and `209-211` at 1136; `83-107` and `215-226` at 1146; `110-251` and `engine.py:210-214` at 1162; `146-159` at 1164; `economy/engine.py:445-503` at 1221 and 1256. IT: `39-40` at 1183, 1197, 2422, 3264; `43-80` and `209-211` at 1173; `83-107` and `215-226` at 1183; `110-251` and `engine.py:210-214` at 1199; `146-159` at 1201; `economy/engine.py:445-503` at 1258 and 1293. `expectations.py:1-23` (EN 1128, IT 1165) is the module docstring and moves only if the docstring changes. T009 re-greps both files for `expectations.py:` and `engine.py:` after the edit, because the citations of `engine.py:265-310` at EN 746 and 854 (IT 783, 891) belong to another `engine.py` and must not move.
- §4.5: citations of `stratification.py` are by name; "writes the assigned class back to each agent" stays true; unchanged.
- §4.8: no line citation of the economy engine; unchanged.
- Frozen-at-commit pin (whitepaper front matter): updated at closure, after the merge (T017).
- READMEs: no README-relevant change (internal performance fix; a new setting with a default needs no setup step).
- Build map: node `spine2.n14` lives on the Plan 4 branch, not on `develop`; the coordinator updates it on that branch when this work item opens and when it closes (the three sites leave the node; the every-tick political cycle enters it as its own defect; `world/economy.py` stays).

## Risks

- The cost model is one data point. Mitigated by T002-T003, which measure before choosing, with a drift check.
- The economy step holds about 6,000-10,000 one-row `save()` statements per tick at 2,000 agents (audit estimate), 3-10 s at b of 0.5-1 ms, against the 15 s of SC-003. The script prints the total `UPDATE` count per tick, so a failure of SC-003 is attributed to them or to the batched writes with numbers; if they cause it, they become the next work item (spec, *Fuori ambito*).
- Another superlinear cost in the economy step would show as a ratio above 15 in SC-002; T014 then profiles the step at 2,000 founders with `cProfile` and reports the top 15 functions instead of declaring success.
- Run-to-run nondeterminism would void SC-004. Mitigated by fresh test databases, the printed `simulation.id`, and the two base runs that must agree before the comparison is judged.

## Measurements

To be filled by T003 and T014.

## Complexity Tracking

No violation to justify.

## Cost estimate (a proposal, not a measure)

About 3.5 hours of implementation and measurement: T001-T003 about 1 hour (the grid has eight candidates), the code, tests and documentation about 1.25 hours, the step measurement about 30 minutes, the base and head runs about 45 minutes of machine time (the base run at 2,000 founders costs about 10 minutes by the 330 s per tick measured on 2026-11-12, and every fingerprint run creates its database from scratch).

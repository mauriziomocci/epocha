# Implementation Plan: per-tick writes linear in the number of agents

**Branch**: `20261112-233606-economy-batched-writes` | **Date**: 2026-11-12 | **Spec**: `specs/20261112-233606-economy-batched-writes/spec.md` (revision 6)

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
- **III. Adversarial Scientific Audit**: rounds 1 to 5 on spec, plan and tasks done, round 5 NOT CONVERGED with its findings fixed in revision 6, round 6 pending (spec, *Stato dell'audit*); the phase-6 code audit as usual. OPEN until the spec round converges.
- **IV. Three-Step Design Process**: recorded in the spec, section *Decisioni di design*, with what each step and the audit killed. PASS.
- **V. Evidence-Based Verification**: SC-001 to SC-004 are measured by tests and a script; SC-005 is reported with its number and a profile. PASS.

## Reuse statement

Searched `epocha/` and `config/` for `batch_size` and `BATCH_SIZE`: found only `EPOCHA_KG_EMBEDDING_BATCH_SIZE` (`config/settings/base.py:240`), the knowledge graph's embedding batches, a different quantity; its **mechanism** (an `env.int` setting) is reused for the new setting. Searched `epocha/common/` for a database-write helper: found none, and none is added. Searched the test suites for a helper that counts rows per captured statement: found none (`CaptureQueriesContext` is used once, in `demography/tests/test_inheritance.py:5573`, for a query count), so `case_update_rows` is new. Searched `scripts/` on `develop` for a world builder without LLM: found none (`scripts/build_map_i18n.py` only; the founder builder of the measurement scripts lives on the unmerged couples branch), so the script builds its agents with `Agent.objects.bulk_create`, following the agent fields of the economy test fixtures, and reuses `initialize_economy` and `process_economy_tick_new` unchanged.

## Architectural placement

The batch size is a setting in `config/settings/base.py`, the place of every other tunable quantity of the project; `economy` and `world` read it through `django.conf.settings` at call time, with no dependency between the two apps. The shape helper serves the tests of two apps, so it goes to the shared core as `epocha/common/testing.py`, a module whose docstring says it is imported only by tests; `epocha/common/` has no test package today, and putting the helper in `economy/tests/` would make the world tests import the economy's tests. The script goes to `scripts/`, never collected by the suite (`python_files = ["test_*.py"]`, `pyproject.toml`).

## Design details

**PD-01, the batch size.** The measurement script of PD-03 carries `test_batch_size_candidates`, run before the setting exists. On the world of PD-03 at 2,000 founders, after tick 1 has created the expectations (R rows, printed), it loads the rows in `id` order and times one full `AgentExpectation.objects.bulk_update(rows, FIVE_FIELDS, batch_size=B)` for B in {5, 10, 15, 25, 50, 100, 200, 500}, three repetitions each, then times the first candidate again to detect drift, and times b as the median of 20 one-row updates. The unbatched call is not re-timed (285 s, measured on 2026-11-12). It prints, per candidate, the median total and the per-statement time, and a least-squares fit of t(B) = a·B² + c·B + b on the per-statement times, which is reported and never used to choose. T003 copies the table into *Measurements* below and picks the B with the lowest measured median total; ties within 10% go to the larger B (fewer statements; the 10% is a tunable heuristic, chosen below the 20% drift tolerance so that a difference inside it is smaller than the run-to-run noise the drift check accepts). If the minimum sits at an edge of the grid, T002 is rerun once with the grid extended past that edge (halving below 5, doubling above 500). If the drift check differs from the first timing by more than 20%, the table is discarded and T002 is rerun (the 20% is a tunable heuristic: a machine whose same candidate timing moves by a fifth between two runs of one session cannot rank candidates that differ by 10%). If no candidate writes the R rows in under 5 s (a third of the 15 s of SC-003, which also has to hold the three writes of the step and the 3-10 s of one-row saves estimated in *Risks*, so a write above 5 s cannot leave the step under 15 s), T003 stops and escalates to the user: batching alone cannot meet SC-003, and the `VALUES` alternative of the spec FAQ needs a decision.

**PD-02, the shape guard.** A helper `case_update_rows(captured_queries, model, field_count) -> list[int]` keeps the captured statements whose SQL starts with `UPDATE "<model._meta.db_table>"` and contains `CASE WHEN` (on PostgreSQL the cast renders as `(CASE WHEN ...)::type`, never `CAST(`), and returns, in execution order, `sql.count("WHEN") // field_count`. The guards set `settings.EPOCHA_BULK_UPDATE_BATCH_SIZE` with pytest-django's `settings` fixture, which accepts a name that does not exist yet, so the red run fails on the shape assertion and not on a missing attribute. Each guard is parametrized on two batch sizes, one dividing the rows and one leaving a remainder, so a size hard-coded at the call site fails one of them.

**PD-03, the measurement script.** `scripts/measure_economy_write_cost.py` runs under pytest (`pytest scripts/measure_economy_write_cost.py -s -p no:cacheprovider -k <function>`), every function marked `@pytest.mark.django_db(transaction=True)` (decision D-05-E-14 of the marital-fertility branch, `scripts/measure_marital_schedule_run.py:457-459` there): every write is committed, so a timing does not carry the row versions of the previous one. It reads `ECONOMY_COST_FOUNDERS` (default 2000), `ECONOMY_COST_TICKS` (default 5) and `ECONOMY_COST_SEED` (default 20261112) from the environment and prints them with every result. It builds one simulation with `seed=SEED`, a `World` with `tick_duration_hours=730`, a `Government`, two zones, the founders through one `Agent.objects.bulk_create` with role and personality drawn from `random.Random(SEED)`, then `initialize_economy(simulation, template_name="pre_industrial")`. `test_economy_step_cost` runs tick 1 untimed (it creates the expectations), then for ticks 2..1+TICKS records `time.perf_counter()` around `process_economy_tick_new(simulation, tick)` under `CaptureQueriesContext`; prints per tick the time, the total number of `UPDATE` statements, and count and maximum of `case_update_rows` for `AgentExpectation` (5 fields) and `Agent` (2 fields); then the median time, `simulation.id`, the seed and the two SHA-256 fingerprints of spec FR-006: (a) the economy step (agent wealth and mood, the five expectation fields), taken before `update_social_classes`; (b) the social classes, taken after one `update_social_classes` call following the last measured tick, tie-invariant (the sorted multiset of (`wealth.hex()`, `social_class`) over living agents, the population `update_social_classes` iterates (`world/stratification.py:145-148`), plus the mobility memories sorted by (agent `wealth.hex()`, content, weight, tick)). Premise of the tie invariance: tied agents share the same previous class. It holds because every founder keeps the model default class "working" (`epocha/apps/agents/models.py:77-81`) and the measured call is the first of the run (its only caller is `world/government.py:795`); the script asserts that the set of founders' classes before the call is {"working"} and fails otherwise. It also prints, as information only, the exact per-agent-id class hash and the tied-wealth agent count. To make SC-004 exercise the batching, `test_economy_step_cost` also captures the statements of the `update_social_classes` call and prints, for each of the three sites (expectations, wealth and mood, social classes), the list of rows per statement from `case_update_rows`. The fingerprint runs of the head (200 founders) set `EPOCHA_BULK_UPDATE_BATCH_SIZE=50` in the environment of the pytest invocation (`sh -c 'EPOCHA_BULK_UPDATE_BATCH_SIZE=50 pytest ...'`), because the chosen default can be 200 or 500, which would write every row of a 200-founder run in one statement and leave the fingerprints equal for the wrong reason. Expected statements at 50, by reading the code, not yet measured: expectations about 20 (about 1,000 rows, five goods); wealth and mood 4 (every founder gets an inventory in `economy/initialization.py:233`); social classes 4 (`update_social_classes` appends every living agent to `agents_to_update` and writes them all, `world/stratification.py:160` and `:192`, whether or not the class changed, so the first call needs no class to move). The run is judged only if every site shows at least 2 statements (T014). It is a measurement, not a judgment: SC-002 to SC-004 are judged by reading its output in T014.

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
config/settings/base.py                             # + EPOCHA_BULK_UPDATE_BATCH_SIZE (no check of our own: Django's bulk_update rejects values below 1)
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
- Line citations shifted by two lines per module in `expectations.py` and `economy/engine.py`: the added `from django.conf import settings` line plus the blank line that ruff's import sorting adds before it (to be confirmed by `grep -n` on the edited sources in T009, which is the authority, never this count), 13 per whitepaper, 26 in all. EN: `expectations.py:39-40` at lines 1146, 1160, 2353, 3464; `expectations.py:43-80` and `209-211` at 1136; `83-107` and `215-226` at 1146; `110-251` and `engine.py:210-214` at 1162; `146-159` at 1164; `economy/engine.py:445-503` at 1221 and 1256. IT: `39-40` at 1183, 1197, 2422, 3264; `43-80` and `209-211` at 1173; `83-107` and `215-226` at 1183; `110-251` and `engine.py:210-214` at 1199; `146-159` at 1201; `economy/engine.py:445-503` at 1258 and 1293. `expectations.py:1-23` (EN 1128, IT 1165) is the module docstring and moves only if the docstring changes. T009 re-greps both files for `expectations.py:` and `engine.py:` after the edit, because the citations of `engine.py:265-310` at EN 746 and 854 (IT 783, 891) belong to another `engine.py` and must not move.
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

### T003: batch size candidates (PD-01)

Date 2026-11-26, base commit `3a688fb` (script and helper uncommitted at the time of the run), Apple M3 Pro (12 cores), macOS 27.2.1, Docker 29.8.2, `epocha-economy-scale` project, 2,000 founders, seed 20261112, 3 repetitions per candidate, run of `test_batch_size_candidates` as printed:

```text
FOUNDERS=2000 SEED=20261112 R=10000 REPETITIONS=3
b (median one-row update) = 0.001208 s
B=   5 statements= 2000 median_total=2.995 s per_statement=0.001497 s
B=  10 statements= 1000 median_total=2.990 s per_statement=0.002990 s
B=  15 statements=  667 median_total=2.618 s per_statement=0.003925 s
B=  25 statements=  400 median_total=2.407 s per_statement=0.006018 s
B=  50 statements=  200 median_total=2.540 s per_statement=0.012702 s
B= 100 statements=  100 median_total=2.533 s per_statement=0.025334 s
B= 200 statements=   50 median_total=2.589 s per_statement=0.051778 s
B= 500 statements=   20 median_total=2.882 s per_statement=0.144119 s
drift ratio (first candidate, second timing / median of first timings) = 1.143, within the tolerance of 0.20
fit per statement t(B) = a*B^2 + c*B + b: a=9.933e-08 c=2.378e-04 b=3.770e-04 (report only)
```

PD-01 rules, in order: drift 1.143 is within 20%, no rerun; the minimum (B=25, 2.407 s) is not at a grid edge; the minimum is under 5 s, no escalation. Choice: the lowest median total is B=25; the candidates within 10% of it (at most 2.648 s) are 15, 25, 50, 100 and 200; ties go to the larger B, so **B = 200** (2.589 s, 7.6% above the minimum; 50 statements per 10,000 rows).

### T014: base and head runs (PD-04, SC-002 to SC-004)

Date 2026-11-26, same machine as above. Base: commit `2223968` in a temporary worktree with the script and `epocha/common/testing.py` copied unmodified (the query log of the connection is replaced by an unbounded one before each capture: Django keeps only the last 9000 statements and `CaptureQueriesContext` slices by position, so the first version of the script, which did not, returned empty shapes past five ticks at 200 founders and was discarded before any number below was taken). Head: commit `6c8b888` plus the script of T012; default B = 200 unless stated. Every run is a separate pytest invocation, `simulation.id` = 1 and seed 20261112 in all of them. The economy step is `process_economy_tick_new`, tick 1 untimed, ticks 2 to 1+TICKS timed.

| Run | Founders | Ticks | Median s | Per tick s | UPDATE statements per tick | Expectation rows per statement | Wealth and mood rows per statement | Social-class rows per statement |
|---|---|---|---|---|---|---|---|---|
| base, run a | 200 | 5 | 1.521 | 1.412, 1.657, 1.731, 1.521, 1.346 | 1211 | {1000: 1} | {200: 1} | {200: 1} |
| base, run b | 200 | 5 | 1.583 | 1.546, 1.802, 1.583, 1.854, 1.498 | 1211 | {1000: 1} | {200: 1} | {200: 1} |
| base | 2000 | 2 | 379.637 | 303.951, 455.324 | 12011 | {10000: 1} | {2000: 1} | {2000: 1} |
| head, B = 50 | 200 | 5 | 1.277 | not kept | not kept | {50: 20} | {50: 4} | {50: 4} |
| head, B = 200 | 200 | 5 | 1.302 | 1.198, 1.290, 1.302, 1.302, 1.465 | 1215 | {200: 5} | {200: 1} | {200: 1} |
| head, B = 200 | 2000 | 5 | 13.401 | 12.466, 13.401, 13.721, 14.033, 13.385 | 12069 | {200: 50} | {200: 10} | {200: 10} |
| head, B = 200 | 2000 | 2 | 13.498 | 12.992, 14.004 | 12069 | {200: 50} | {200: 10} | {200: 10} |

Fingerprints (spec FR-006), as printed:

- 200 founders, 5 ticks: (a) `a425047cff5f8c8bf7d65a961444d5d7af9be5eb4a0007b0f07c5e587fdadcd3` and (b) `fff4aeacc139b289db9558581fb0a12518a0803be8793303da19a7834c0807f1` in both base runs, in head B = 50 and in head B = 200; per-agent-id class hash `bf1c8843401ea545a689a8ad08a10ad9be1aff4e18ea123e2e434f9fb574a0a8` in all four; tied-wealth agents 0.
- 2,000 founders, 2 ticks (extra comparison, not required by T014): (a) `8500fd2248e672b90b06743a2dfe83ab72d29c187bf2aaa2b804b415655bc040` and (b) `c293344a5d8184a286fa71dcf6dce88b44dd598b8c94b4a50df80a54b07fe2b9` on base and on head; per-agent-id class hash `decb528c807d92142b5e58d0424c22fcca9816403399f0fad984fdd8fee9c7a4` on both; tied-wealth agents 0.
- 2,000 founders, 5 ticks, head only: (a) `5c047c49f538a59d72f585db33cca6a05b7b60727a40283af393f1f4bd208399`, (b) `fe4bab87ad87ead43e1527660c0e60ed59ed437ffd5fb810207f183378624878` (no base run of five ticks at this size: it would take about 30 minutes).

Verdicts:

- **SC-004 (a) and (b): met.** Same `simulation.id` and seed; the two base runs agree on both fingerprints; head B = 50 (20, 4 and 4 statements, at least 2 at every site, so the batching was exercised) and head B = 200 equal the base on both; the 2,000-founder two-tick comparison is equal too. No difference in the informational class hash.
- **SC-002: met.** Ratio of the head medians 13.401 / 1.302 = 10.29, at most 15. For the record, the base medians give 379.637 / 1.521 = 249.6 and 379.637 / 1.583 = 239.8.
- **SC-003: met, with a thin margin.** Median 13.401 s at 2,000 founders, at most 15 s; the five ticks range from 12.466 to 14.033 s. Of the 12,069 `UPDATE` statements of a tick, 60 are the batched writes (50 expectation batches, 10 wealth and mood batches) and 12,009 are other statements, the one-row saves the audit estimated. At the one-row cost b of 1.208 ms measured in T003 they would take 14.5 s alone, more than the whole step, so b overestimates their cost inside the step; I did not measure their share of the step, so which part bounds the step now is not verified. SC-003 passes, so no `cProfile` run was made (T014 asks for it only on a failure).

## Complexity Tracking

No violation to justify.

## Cost estimate (a proposal, not a measure)

About 3.5 hours of implementation and measurement: T001-T003 about 1 hour (the grid has eight candidates), the code, tests and documentation about 1.25 hours, the step measurement about 30 minutes, the base and head runs about 45 minutes of machine time (the base run at 2,000 founders costs about 10 minutes by the 330 s per tick measured on 2026-11-12, and every fingerprint run creates its database from scratch).

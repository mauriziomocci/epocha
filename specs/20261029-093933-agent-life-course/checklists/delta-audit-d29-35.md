# Adversarial audit of the D-29-35 amendment (delta only)

**Scope**: the diff `ccaab3f..HEAD` on `spec.md`, `plan.md` and `tasks.md` of this feature, i.e. the amendment that applies Trinity decision D-29-35 (plan questions Q-1 to Q-4). Code claims are checked against `origin/20260826-144432-demography-plan4-wiring` (head `3c1e2c0`). Reviewer: `critical-analyzer`, hostile, read-only. Cap: two rounds.

## Round 1 (2026-10-29, delta `ccaab3f..4c0ef5d`)

**Verdict: NOT CONVERGED** (4 INCORRECT, 0 UNJUSTIFIED, 2 INCONSISTENT, 1 MISSING). I verified findings 2 and 3 on the Plan 4 branch myself before fixing them (`git show c1e8569:...` shows the group chat and the WebSocket prompt still without age; `git grep` finds eleven other sites of the default template name).

| # | Class | Finding | Fix |
|---|---|---|---|
| 1 | INCORRECT | The unloadable-template behaviour (no demography action, WARNING naming the template) was implemented in T022 but tested in T023, so its tests could never be seen red | Red tests moved into T022, before its code; T023 points to T022; plan Q-2 says T022 |
| 2 | INCORRECT | The spec attributed the age in all three chat prompts to merge `c1e8569`; that merge covers only the private chat, `02a1d47` adds the group chat, `430dfa6` the WebSocket chat and the move of `describe_speaker` | Spec "Perché", "Relazione con la guardia" and D-29-35 entry name the three commits |
| 3 | INCORRECT | PD-03 claimed the default template name would have "one spelling"; eleven other sites predate the work item | PD-03 claims only that the new code adds no spelling, and lists the out-of-scope sites |
| 4 | INCORRECT | T044 named `get_llm_client` for the group chat and contained a garbled sentence | T044 names the patch target `epocha.apps.llm_adapter.client.get_chat_llm_client`, one statement over three prompts and two group roles |
| 5 | INCONSISTENT | The premise of the spec listed two chat prompt builders; the first-draft code already had three | "I tre costruttori" |
| 6 | INCONSISTENT | The per-tick count of loader warnings omitted the selection clock and the demography block | Edge case and PD-03 add both sources |
| 7 | MISSING | The cited audit file did not exist | This file |

**Verified by the reviewer**: the arithmetic (`3285 * 168 / 8760 == 63.0` exactly; edge 3285; two-division form `62.99999999999999` and edge 3286; daily edges 3650, 5840, 6570; weekly 522, 835); the SC-010 mutation turns both pin tests of T020 red while age and edge still agree, so the literal pins are not tautological; FR-001b's description of `_years_elapsed` and `_fewest_ticks_to_reach`; the round-6 characterization holds only for the old arithmetic; `run_demography_tick` returns before every step on a missing template; today's `_build_system_prompt` behaviour; the group chat reads the clock once per request; no change to any scientific model, threshold, source, API contract or data model.

## Round 2 (2026-10-29, fix delta `4c0ef5d..5338073`)

**Verdict: CONVERGED** (0 INCORRECT, 0 UNJUSTIFIED, 0 INCONSISTENT, 0 MISSING). The reviewer found all seven round-1 findings resolved and no new issue introduced by the fixes.

| # | Round-1 finding | Status | Evidence checked by the reviewer |
|---|---|---|---|
| 1 | Unloadable template not tested red-first | RESOLVED | T022 tests precede its code; red on Plan 4 `decision.py` (`except FileNotFoundError: pass` keeps the actions; `logger.exception` logs at ERROR, not WARNING) |
| 2 | Commit attributions | RESOLVED | `c1e8569` private chat only; `02a1d47` group chat; `430dfa6` WebSocket chat and the move of `describe_speaker` |
| 3 | Default template name spelling | RESOLVED | Eleven production sites besides the one extracted into `template_name_of`, count exact |
| 4 | T044 patch target | RESOLVED | `epocha.apps.llm_adapter.client.get_chat_llm_client` serves the group chat and the consumer, as `test_chat_prompt.py` already patches |
| 5 | Two prompt builders | RESOLVED | Three builders, matching the first-draft code |
| 6 | Warning count | RESOLVED | Callers of `_load_simulation_template` enumerated; spec and PD-03 agree |
| 7 | Missing audit file | RESOLVED | This file |

Note from the reviewer, not a finding: before T022 the new tests call `_build_system_prompt(agent, clock)` against the old signature `(agent)`, so their first red is a `TypeError`; after the signature change they still go red for the stated reason.

**Final verdict of the delta audit: CONVERGED in 2 rounds.**

## Verifica indipendente del coordinatore (dopo il round 2)

**Scope**: the delta `ccaab3f..a6d6fc3`, re-checked from scratch against `origin/20260826-144432-demography-plan4-wiring` (head `3c1e2c0`), without relying on the round-2 table. Reviewer: `critical-analyzer`, read-only.

**Verdict: CONVERGED** under the criterion of this audit (all round-1 findings resolved, no new INCORRECT or UNJUSTIFIED). Two new INCONSISTENT phrasings, both one-phrase edits that do not reopen a round, are to be reconciled before the phase-2 gate, as the project's Golden Rule requires for every INCONSISTENT finding.

| # | Round-1 finding | Status | Independent evidence |
|---|---|---|---|
| 1 | Unloadable template not tested red-first | RESOLVED | T022 now carries the tests "written and seen red before the code"; T023 points to T022; plan Q-2 and the tasks closing note say T022. The stated red is real: Plan 4 `agents/decision.py` keeps all three actions on `except FileNotFoundError: pass` and logs the invalid case with `logger.exception` (ERROR, not WARNING); the logger is `agents/decision.py:21` `getLogger(__name__)`, so "one WARNING from `epocha.apps.agents.decision`" is assertable and distinct from the loader's records (`demography/orchestrator.py:1140-1170`, its own logger) |
| 2 | Commit attributions | RESOLVED | `c1e8569` (merge, parents `f4f3dfd 6c21973`) adds the age to `_build_chat_system_prompt` only; `02a1d47` introduces `_describe_speaker` and uses it in `group_chat_view`; `430dfa6` moves `describe_age`/`describe_speaker` to `demography/orchestrator.py` and calls it in `chat/consumers.py:93`. Order on the branch: `c1e8569` -> `02a1d47` -> `430dfa6` (`git log --ancestry-path`) |
| 3 | Default template name spelling | RESOLVED | `git grep` on the Plan 4 head, production code only: twelve code sites of the default; minus `orchestrator.py:1153` (inside `_load_simulation_template`, the one `template_name_of` extracts) leaves eleven: `couple.py:343,519`, `inheritance.py:1385,3527`, `initialization.py:69,147,230`, `migration.py:1433`, `orchestrator.py:381`, `simulation/engine.py:337`, `agents/decision.py:66`. The PD-03 list of places (demography, `engine.py`, `decision.py`) is exact |
| 4 | T044 patch target | RESOLVED | Both `group_chat_view` (`views.py:810`) and `ChatConsumer._generate_response` (`consumers.py:71`) import `get_chat_llm_client` inside the function, so patching `epocha.apps.llm_adapter.client.get_chat_llm_client` reaches both; `dashboard/tests/test_chat_prompt.py:112,154` already patches that target. Both group roles go through `describe_speaker(agent, age_clock)` (`views.py:876`), listener `max_tokens = 80` (`views.py:872`) |
| 5 | Two prompt builders | RESOLVED | Three builders on the first-draft tree and on the head (`views.py:105`, `views.py:876`, `consumers.py:93`); see N1 for a side effect of the rewrite |
| 6 | Warning count | RESOLVED | Callers of `_load_simulation_template` on the head: `current_age_clock` (`orchestrator.py:550`), `minor_agent_ids` (`:621`, gated by `is_demography_enabled`), `run_demography_tick` (`:1197`, gated). After the work item the selection clock (`age_clock_for` in `select_deliberating_agents`, plan PD-09) loads once per tick without the gate (PD-03, SC-007) and the demography block once when enabled; `engine.py:509` and `tasks.py:80` are alternative paths of one tick, not two loads. Spec edge case and PD-03 agree |
| 7 | Missing audit file | RESOLVED | The file exists and records rounds 1 and 2 |

**Arithmetic recomputed** (pure Python, one-division form of `_years_elapsed`, `orchestrator.py:520-527`, and the edge search of `_fewest_ticks_to_reach`, `:1095-1101`): `3285 * 168 * 1.0 / 8760 = 63.0` and edge `3285`; with the two-division mutation of T020 (`elapsed / (8760 / 168) * 1.0`) `62.99999999999999` and edge `3286`; daily edges 10, 16, 18 years = 3650, 5840, 6570; weekly 10, 16 years = 522, 835; the weekly 10-year limit is `87600 / 168 = 521.43`, as SC-010 states. T005 and T020 carry these literals correctly.

**New findings in the delta**

| # | Class | Finding | Action |
|---|---|---|---|
| N1 | INCONSISTENT | `spec.md:21`: the fix of finding 5 removed the disambiguator `(_build_chat_system_prompt)` and now names two dashboard prompts, but the next sentence still says "Il prompt della dashboard vieta inoltre le didascalie non verbali". Only the private prompt has that rule (`views.py:112`, "NEVER describe yourself in third person"); the group prompt (`views.py:874-880`) has no conversation rules and itself prescribes the stage direction `*ascolta in silenzio*` to listeners (`views.py:870`) | Replace "Il prompt della dashboard" with "Il prompt della chat privata della dashboard"; optionally add that the group chat, like `chat/consumers.py`, has no conversation rules |
| N2 | INCONSISTENT | `spec.md:475` (added in `a6d6fc3`): "NOT CONVERGED al round 1 (quattro INCORRECT, tutti corretti)" omits the two INCONSISTENT and the one MISSING that round 1 also raised and that were also fixed (round-1 table above) | "(quattro INCORRECT, due INCONSISTENT e un MISSING, tutti corretti)" |

Confirmed, not a finding: the round-2 note on the first red of the T022 tests. Called directly as `_build_system_prompt(agent, clock)` before the signature change they fail with `TypeError`; driven through `process_agent_decision`, or after the signature change, they fail for the stated behavioural reason. No change to any scientific model, threshold, source, API contract or data model in `ccaab3f..a6d6fc3`.

THE THING: reword `spec.md:21` so the non-verbal ban is attributed to the private chat only.

**Esito della verifica indipendente.** N1 e N2 sono corretti nel commit che registra questa sezione: `spec.md:21` attribuisce il divieto delle didascalie non verbali alla sola chat privata (`_build_chat_system_prompt`, `dashboard/views.py:112`) e nota che la chat di gruppo prescrive `*ascolta in silenzio*` (`views.py:870`, verificato dal coordinatore); `spec.md:475` elenca anche i due INCONSISTENT e il MISSING del round 1. Le due correzioni sono frasi descrittive, non toccano requisiti, criteri né modello: il verdetto resta **CONVERGED**.

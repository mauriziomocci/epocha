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

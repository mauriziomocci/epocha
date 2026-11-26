# Implementation Plan: Demografia Plan 4 — inizializzazione, cablaggio, snapshot di popolazione

**Branch**: `20260826-144432-demography-plan4-wiring` | **Date**: 2026-08-27 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/20260826-144432-demography-plan4-wiring/spec.md`, CONVERGED at round 5 of the phase-2 gate (`gate-phase2-round5.md`).

## Summary

Five audited demography modules exist and the tick loop calls none of them. This
plan wires them, and the wiring is not "call five functions": two of the five
modules expose no per-tick entry point at all and a third declares itself step
2 of 3 of an orchestrator nobody wrote. The plan therefore delivers, in this
order: the two orchestrators (birth and death), the initialization that makes
the modules' real preconditions hold (`birth_tick` and initial couples), the
wiring itself with the step order expressed **as data**, and the
`PopulationSnapshot` writer that makes historical validation executable. Two
pieces of state that do not exist today are created along the way: the
persisted starvation counter the emergency-flight trigger requires, and the
per-template newborn name pool.

One defect in merged code is corrected inside this work item because the birth
orchestrator makes it certain rather than latent:
`apply_inheritance_at_birth` re-derives its RNG stream from
`(simulation, tick, "inheritance")` on every call and consumes a draw count
independent of the parents, so two newborns in the same tick receive identical
sex and orientation.

## Technical Context

**Language/Version**: Python 3.12, Django 5.x

**Primary Dependencies**: Django ORM, Celery (the tick loop is a self-enqueuing
task plus a chord of per-agent tasks), Django Channels for the tick broadcast

**Storage**: PostgreSQL. Two schema changes: one new field on `Agent` for the
starvation counter, and the first production writer of the existing
`PopulationSnapshot` model (`demography/models.py`), which Plan 1 modelled and
nothing has ever written.

**Testing**: pytest against PostgreSQL, `assertNumQueries` for the cost budget,
mutation proofs for every ordering property (swap two steps, the test must go
red).

**Target Platform**: Linux containers (`docker-compose.local.yml`)

**Project Type**: Django monolith, per-app modules under `epocha/apps/`

**Performance Goals**: the demography block issues **no query per living
agent**. Per-vital-event cost is admitted and declared as an upper bound
`a + b·deaths + c·intents + d·flights` at worst-case coefficients, with the
zone count held fixed and births absorbed into the fixed term (FR-016, FR-016a).

**Constraints**: no demography module may be rewritten (Non-goals); the two
named exceptions are `apply_inheritance_at_birth` (SC-006) and
`process_emergency_flight` (FR-012). Every RNG-consuming phase derives exactly
one stream per `(tick, phase)` and threads it through a deterministic iteration
order (FR-010). Bilingual whitepaper and build map update in the same commit as
the code (FR-017).

**Scale/Scope**: MVP populations; six new or modified source modules, one
migration, one template-schema extension.

## Constitution Check

*GATE: passed before Phase 0, re-checked after Phase 1 design.*

| Principle | Status | Evidence |
|---|---|---|
| I — Scientific method above all | PASS | No new scientific model is introduced. The plan orchestrates audited models and never re-derives their formulas. The single model-level change, the birth RNG fix, restores a property the module already claims (independent draws per newborn) rather than inventing one. |
| II — Verify before asserting | PASS | Every function signature, field and file path named in this plan was read in the source during planning: `tick_mortality_probability`, `tick_birth_probability`, `resolve_childbirth_event`, `resolve_pair_bond_intents`, `resolve_separate_intents`, `apply_inheritance_at_birth`, `process_inheritance_batch`, `process_emergency_flight`, `PopulationSnapshot`, `load_template`. The task breakdown repeats the check per task before dispatch. |
| III — Adversarial audit | PASS (phase 2), PENDING (phase 6) | The spec converged at round 5 against a stopping rule written before the round. The code audit fires at the phase-6 gate, on the code and not on the spec. |
| IV — Three-step design | PASS | Applied during the spec's five gate rounds; this plan is the consolidation, not a fresh design. |
| V — Evidence-based verification | PASS by construction | No claim of "works" without a run. The wiring's own acceptance is a live simulation of N ticks producing births and deaths (SC-001), not a unit test. |
| Documentation discipline | PLANNED | FR-017 carries a section-by-claim inventory of every whitepaper passage the merge falsifies, in both languages, closed item by item in the merge commit. |

No violations. Complexity Tracking is empty by consequence.

## Architectural decisions

### D1 — Where the orchestrators live

`epocha/apps/demography/orchestrator.py`, a new module in the demography app.

**Rationale** (Golden Rule of App Design; Ghezzi principles 2, 3, 5): the birth
and death orchestrators compose demography's own modules and mutate demography's
own state. Their single responsibility is demographic, not simulation-control.
Putting them in `simulation/engine.py` would make the engine depend on the
internals of five demography modules and would grow a file that already owns
tick control flow, so the cohesion of both would drop.

**Dependency direction**: `simulation` USES `demography`, never the reverse. The
engine calls one entry point per tick and knows nothing of heir ladders or
Hadwiger schedules.

**Alternatives rejected**: (a) orchestrators inside `engine.py` — wrong app,
wrong dependency direction, the DVT-544 anti-pattern; (b) one orchestrator
module per path (`birth.py`, `death.py`) — the two share the era template, the
RNG derivation and the event emission helper, so splitting them would duplicate
that spine or invent a third module to hold it.

### D2 — The tick order as data

A module-level tuple of `(step_index, phase_name, callable)` in
`orchestrator.py`, iterated by the block entry point. FR-003 requires the order
to be data and inspectable by a test; SC-002 requires each ordering property to
be mutation-provable, which means a test must be able to reorder the sequence
programmatically.

The declared order, each position justified by a spec requirement:

| # | Step | Why here |
|---|---|---|
| 1 | separations resolved | FR-005a: intents from T-1 take effect at the start of T, before the conception window |
| 2 | couples formed | FR-005: same rule, and a couple formed at T must be able to conceive at T |
| 3 | mortality and the death orchestrator | FR-004: whoever dies at T cannot conceive at T |
| 4 | succession (`process_inheritance_batch`) | FR-006: succession follows the death that caused it, in the same tick |
| 5 | starvation counter updated | FR-011: reads the post-succession wealth, the same value the flight trigger reads |
| 6 | forced migration (`process_emergency_flight`) | FR-007: reads post-death population and post-succession wealth |
| 7 | fertility and the birth orchestrator | after 1-3 by FR-004 and FR-005; a newborn does not participate in this tick's other steps |
| 8 | `PopulationSnapshot` written | FR-015: the snapshot describes the tick after every mutation of it |

`dissolve_on_death` is deliberately absent: `process_inheritance_batch` already
calls it last (FR-007a).

### D2b — Where the block hangs in the tick

**Synchronously in `run_simulation_loop`, after `run_economy` and before the
chord of per-agent tasks.** The spec's FAQ delegates this choice to the plan;
here it is, with its reason.

The demography block is a set-based mutation of tick state, like the economy
block and unlike the per-agent decisions. Running it before the chord means the
agents deciding at tick T see the population that tick T actually has: the dead
are dead, the newborns exist, the estates are settled, the forced moves have
happened. Running it after the chord would have every agent decide against a
population one tick stale, and running it inside `finalize_tick` would do the
same while also mixing domain mutation into the callback that closes the tick.

It also keeps the cost measurable: FR-016's per-living-agent prohibition is
assertable with `assertNumQueries` around one synchronous call, which is not
true of work spread across a chord.

**Consequence, stated rather than discovered later**: an agent who dies in
demography step 3 is not in the chord's header for that tick, because the header
is built after the block runs. That is the correct reading of FR-004 — whoever
dies at T does not act at T — and it is what makes the ordering properties
observable from outside the block.

### D3 — Activation predicate

A dedicated `config` key, `demography_enabled`, checked once per tick by the
block entry point. It cannot be the era template's presence: seven production
sites already apply `config.get("demography_template", "pre_industrial_christian")`,
so a simulation that declares nothing behaves exactly like one that declares the
default (FR-008). Absent or false, the block returns before issuing any query,
which is what makes SC-004's equal-query-count assertion reachable.

### D4 — The starvation counter

A new non-null integer field with default 0 on `Agent`, plus a migration.

**Rationale**: the tick loop is distributed across Celery tasks and in-memory
state does not survive the process; the project rule is state in the database.
`process_emergency_flight` already accepts
`consecutive_ticks_under_subsistence_by_agent_id`, a mapping keyed by agent id,
so step 6 builds that mapping from the persisted column with one bulk read —
this is why FR-012 changes the function's body only to read the store, and why
the mapping shape does not change.

**Rejected**: a separate `AgentDemographyState` table. It would be a
one-to-one satellite of `Agent` carrying a single integer, joined on every tick.

### D5 — Newborn names

A new `names` section in each era template, read by the birth orchestrator.
FR-001a forbids an LLM-generated name because it would make birth
non-reproducible from the seed.

**Consequence that must not be missed**: the template loader validates a closed
schema and rejects every unknown key at any nesting level
(`demography/template_loader.py`). Adding the section therefore requires
extending the schema deliberately, with its own mutation-proven test. This is an
extension of a contract, not a weakening of a guard: the guard keeps rejecting
everything it rejected before.

### D6 — Cost strategy

Set-based work throughout: one bulk read of the living population per tick, one
`bulk_create` for newborns, one `bulk_create` for the orchestrators' events, one
`bulk_update` for the counter. The per-death and per-intent costs inside
`inheritance.py` and `couple.py` are contractual and stay: FR-016 admits them
and FR-016a bounds them. What FR-016 forbids — a query per living agent — is
exactly what the bulk shape avoids.

## Project Structure

### Documentation (this feature)

```text
specs/20260826-144432-demography-plan4-wiring/
├── spec.md                     # CONVERGED at gate round 5
├── plan.md                     # This file
├── gate-phase2-round2.md       # criterion + verdict, per round
├── gate-phase2-round3.md
├── gate-phase2-round4.md
├── gate-phase2-round5.md       # CONVERGED
└── tasks.md                    # /speckit-tasks output
```

No `research.md`: the spec's five gate rounds resolved every open question
against the source, and there is no NEEDS CLARIFICATION left to research. No
`contracts/`: the feature exposes no new external interface — it is internal
tick-loop wiring, and the one public surface it touches (`config` gaining
`demography_enabled`) is documented in the spec and in the whitepaper. No
`data-model.md` beyond section D4 above and the existing `PopulationSnapshot`,
which Plan 1 already modelled and documented.

### Source Code (repository root)

```text
epocha/apps/demography/
├── orchestrator.py             # NEW — birth and death orchestrators, the step order as data, the block entry point
├── snapshot.py                 # NEW — PopulationSnapshot writer (ten fields, set-based aggregates)
├── initialization.py           # NEW — birth_tick backfill and initial couples for a founding population
├── inheritance.py              # MODIFIED — per-newborn RNG derivation (SC-006) only
├── migration.py                # MODIFIED — process_emergency_flight reads the persisted counter (FR-012)
├── template_loader.py          # MODIFIED — schema extended with the names section (D5)
└── templates/*.json            # MODIFIED — names section per era

epocha/apps/agents/
├── models.py                   # MODIFIED — consecutive_ticks_under_subsistence
└── migrations/                 # NEW migration

epocha/apps/simulation/
└── engine.py                   # MODIFIED — one call into the demography block, guarded by D3

epocha/apps/demography/tests/   # tests per task, mutation proofs for D2, cost budget for FR-016a
docs/whitepaper/*.md            # FR-017 inventory, both languages
docs/build-map/*.html           # both languages, same commit
```

**Structure Decision**: everything demographic lands in `epocha/apps/demography/`
per D1; `simulation/engine.py` gains a single guarded call and no domain
knowledge; `agents/models.py` gains one field because the counter is a property
of an agent and of nothing else.

## Implementation phases

Ordered as the spec imposes; each phase is independently testable and leaves the
suite green.

**Phase A — the two orchestrators.** `orchestrator.py` with the birth path
(create the `Agent`, set `birth_tick`, `parent_agent`, `other_parent_agent`,
name from the template pool, call `apply_inheritance_at_birth`, emit the event)
and the death path (evaluate mortality, mark `is_alive`, `death_tick`,
`death_cause`, call `process_inheritance_batch`, emit the event). Includes the
`inheritance.py` RNG fix, because the birth orchestrator is what makes the
defect observable and SC-006 is its witness.

**Phase B — initialization.** `initialization.py`: `birth_tick` consistent with
the generated age for every living agent, with the post-condition that none is
left NULL, and the initial couples without which the default template makes
birth impossible.

**Phase C — the wiring.** The step order as data (D2), the activation predicate
(D3), the guarded call in `engine.py`, the persisted counter and its migration
(D4), and `process_emergency_flight` reading it. The mutation proofs for every
ordering property land here.

**Phase D — the snapshot.** `snapshot.py`, all ten fields, asserted field by
field against a hand-built fixture that carries at least one birth, one death,
one zone move, an unbalanced sex ratio and one active couple (SC-007).

**Phase E — cost and documentation.** The two-part cost measurement (SC-005),
then the whitepaper inventory of FR-017 closed item by item in both languages,
and the build map at the same checkpoint.

## Post-validation review of this plan (phase 4, before any code)

Four residual doubts raised by re-reading the plan and the task list with fresh
eyes. All four are resolved here rather than discovered mid-implementation.

1. **The block's position in the tick was missing.** The spec explicitly
   delegated it to this plan and the plan's first draft declared only the order
   *within* the block. Resolved as D2b.
2. **Doc-sync would have been violated.** Two tasks modify code that whitepaper
   §4.1 documents — the birth RNG derivation in `inheritance.py` and
   `process_emergency_flight` in `migration.py`. The project rule requires the
   bilingual whitepaper to change in the **same commit** as that code, and the
   first task list deferred every documentation change to the end. Each of those
   two tasks now carries its own whitepaper update; the closing task keeps only
   the inventory of passages the *wiring* falsifies.
3. **Initialization must respect the activation predicate.** Backfilling
   `birth_tick` and creating couples for a simulation that never enables
   demography would violate FR-009's invariance. The initialization tasks now
   run under the same predicate as the block.
4. **The cost measurement needs a boundary.** "The demography block's query
   count" is only meaningful because D2b makes the block a single synchronous
   call, so `assertNumQueries` wraps exactly it. Stated in the cost tasks so the
   measurement is not improvised.

One observation carried forward without change: thirty-eight tasks exceeds the
project's usual 15-25 per plan. Splitting them across two plan files would be
bookkeeping, not decomposition — the phases are already the seam, and the MVP
scope names where a first increment ends.

## Risks carried into implementation

1. **The order is the chief risk.** A wrong order produces a credible
   population curve that no shallow test distinguishes. Mitigation: D2 plus
   SC-002's mutation proofs; nothing else catches it.
2. **The cost budget is measured, not assumed.** The coefficients of FR-016a
   are unknown until phase C exists; if the measurement shows a per-living-agent
   query, the fix is the query shape, never the criterion.
3. **The template schema extension (D5)** touches a guard that a previous work
   item hardened over eleven audit rounds. It is extended for an observed need,
   with its own mutation proof, and no existing rejection is relaxed.

## Complexity Tracking

No constitution violations. Section intentionally empty.

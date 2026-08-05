# Implementation Plan: Demography Plan 3 — Inheritance and Migration

**Branch**: `20260717-120706-demography-inheritance-migration` | **Date**: 2026-07-17 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/20260717-120706-demography-inheritance-migration/spec.md` (approved at the phase-2 gate on 2026-07-17)

## Summary

Deliver the two remaining behavioural modules of the demography subsystem — `inheritance.py` and `migration.py` — as pure, orchestrable functions that the Plan 4 tick orchestrator will call. The scientific design is already CONVERGED (`docs/superpowers/specs/2026-04-18-demography-design-it.md`, sections 4, 5 and 6, four adversarial audit rounds, closed 2026-04-18); this plan does not reopen it. It fixes module boundaries, function signatures, build order, and the integration surface, and it records the code-verification preflight that Constitution Principle II requires before any task is dispatched.

The preflight found no blockers and three traps that would have cost implementation time. They are recorded below and must be carried into the task breakdown verbatim.

## Technical Context

**Language/Version**: Python 3.12

**Primary Dependencies**: Django 5.x ORM only. No new third-party dependency. `scipy` is already present but is not needed here (it was a Plan 1 concern for Heligman-Pollard fitting).

**Storage**: PostgreSQL. **No schema migration is produced by this plan** — verified, see preflight.

**Testing**: pytest on PostgreSQL (never SQLite). Test-first: a red test precedes each implementation task.

**Target Platform**: Linux container (`docker compose -f docker-compose.local.yml`), which is the authority for tests and lint.

**Project Type**: Django app module inside a scientific simulation monolith.

**Performance Goals**: no N+1 queries. Both modules are invoked once per tick over a batch of agents, so every cross-agent lookup must be set-based or prefetched. The Plan 4 benchmark target (500 agents × 1000 ticks < 30 min wall time) constrains this plan even though the benchmark itself is out of scope: a per-agent query here becomes a per-agent-per-tick query there.

**Constraints**: determinism is non-negotiable — every random draw derives from `get_seeded_rng(simulation, tick, phase)`, so identically-seeded runs reproduce identical state. The derived-trait formula evaluator must not permit arbitrary code execution.

**Scale/Scope**: two new modules, roughly 22 tasks, no migrations, no template changes.

## Constitution Check

*GATE: evaluated before Phase 0 and re-evaluated after design. Result: PASS, no violations, Complexity Tracking left empty.*

| Principle | How this plan complies |
|---|---|
| **I. Scientific Method Above All** | Every formula and constant comes from the CONVERGED design with a primary source: Falconer & Mackay (1996) for polygenic additive inheritance; per-trait h² from the trait-specific primary studies (Jang et al. 1996, Plomin & Deary 2015, Vernon et al. 2008, Nichols 1978, Zempo et al. 2017, Miyamoto-Mikami et al. 2018, Thomis et al. 1998, Zietsch et al. 2014), with Polderman et al. (2015) cited as methodological backbone only and never as the source of an individual h²; Clark (2014), Solon (1999) and Chetty et al. (2014) for social mobility; Blackstone (1765), Napoleonic Code (1804), Powers (1986), Schneider & Gough (1961), Nove (1969) for the succession rules; Piketty (2014) for modern estate-tax rates; Harris & Todaro (1970), Mincer (1978), O'Rourke (1994) and Simon (1955) for migration. Every simplification states what it loses. |
| **II. Verify Before Asserting** | The preflight table below verifies every symbol this plan names against the source tree at commit `07aecaa`. Three traps were caught (see Preflight). No task may be dispatched naming an unverified symbol. |
| **III. Adversarial Scientific Audit** | The spec-side audit is already discharged: the design CONVERGED after four rounds on 2026-04-18. The code-side audit is the phase-6 heavy gate and is tracked by SC-007. |
| **IV. Three-Step Design Process** | Discharged by the CONVERGED design spec, which was produced through it. This plan is a phase-3 artifact deriving from an approved design, not a new design document. |
| **V. Evidence-Based Verification** | Both modules are unit-testable in isolation but cannot be observed in a live run until Plan 4 wires the orchestrator. This plan therefore claims **"unit tests only"** as its terminal confidence level and states so explicitly; live-run evidence is Plan 4's deliverable, not this one's. This is a disclosure, not a gap. |

## Preflight — code verification (Constitution Principle II)

Verified against the source tree on 2026-07-17 at `develop` = `07aecaa`. Anchored to stable symbols, never to line numbers alone.

### Available and confirmed

| Symbol | Signature / fact | Location |
|---|---|---|
| `get_seeded_rng` | `(simulation, tick: int, phase: str) -> random.Random` | `epocha/apps/demography/rng.py` |
| `load_template` | `(name: str) -> dict[str, Any]` | `epocha/apps/demography/template_loader.py` |
| `add_to_treasury` | `(government, currency_code: str, amount: float) -> None` | `epocha/apps/world/government.py` |
| `compute_subsistence_threshold` | `(simulation, zone) -> float` | `epocha/apps/demography/context.py` |
| `compute_aggregate_outlook` | `(agent) -> float` | `epocha/apps/demography/context.py` |
| `propagate_information` | `(simulation: Simulation, tick: int) -> None` | `epocha/apps/agents/information_flow.py` |
| `TRAVEL_SPEEDS` | `dict[str, float]` | `epocha/apps/agents/movement.py` |
| `SUBSISTENCE_NEED_PER_AGENT` | `float = 1.0` | `epocha/apps/economy/market.py` |
| `dissolve_on_death` | `(deceased_agent, tick: int) -> Couple \| None` | `epocha/apps/demography/couple.py` |
| `active_couple_for` | `(agent) -> Couple \| None`, filters `dissolved_at_tick__isnull=True` | `epocha/apps/demography/couple.py` |
| `Agent` fields | `birth_tick`, `death_tick`, `death_cause`, `parent_agent`, `other_parent_agent`, `caretaker_agent`, `gender`, `sexual_orientation`, `personality` (JSONB), `intelligence`, `cunning`, `wealth`, `social_class` | `epocha/apps/agents/models.py` |
| `Couple` fields | `agent_a_name_snapshot`, `agent_b_name_snapshot`, `dissolved_at_tick`, `dissolution_reason` | `epocha/apps/demography/models.py` |
| `DemographyEvent.EventType` | `MIGRATION`, `INHERITANCE_TRANSFER`, `MASS_FLIGHT`, `TRAPPED_CRISIS` all present | `epocha/apps/demography/models.py` |
| `Loan` fields | `lender`, `lender_type` (choices), `borrower`, `principal` | `epocha/apps/economy/models.py` |
| `EconomicLedger.TRANSACTION_TYPES` | includes `("wage", "Wage")` | `epocha/apps/economy/models.py` |
| `World.distance_scale` | FloatField | `epocha/apps/world/models.py` |
| `Government.stability` | FloatField, 0.0 collapsing to 1.0 rock solid | `epocha/apps/world/models.py` |
| `Memory` fields | `content`, `emotional_weight`, `source_type` | `epocha/apps/agents/models.py` |
| Template keys | `trait_inheritance.{heritability,derived_trait_formulas}`, `social_inheritance.{class_rule,education_regression_rho}`, `economic_inheritance.{rule,heir_priority,estate_tax_rate}`, `migration.{flight_trigger_ticks,adulthood_age}` — present in all five era templates | `epocha/apps/demography/templates/*.json` |

### Traps — carry these into every affected task

1. **The education field is `education_level`, not `education`.** The design spec writes `child.education` as shorthand. The real field is `Agent.education_level` (FloatField, default 0.3, "0.0 = illiterate, 1.0 = scholar"). A task that names `education` will fail or, worse, tempt an implementer into adding a field and producing a migration this plan promises not to produce.
2. **`strength` is two different things.** `Agent.strength` is an inherited physical trait (h² = 0.55, in the heritability table). `Relationship.strength` is tie strength, and it is the one the mourning cascade filters on (`> 0.6`). Confusing them would send grief memories to muscular agents instead of close friends.
3. **`dissolve_on_death` cannot handle both partners dying in the same tick — by construction.** It resolves the couple through `active_couple_for`, which filters `dissolved_at_tick__isnull=True`. The first partner's death sets `dissolved_at_tick`, so the second call finds no active couple, returns `None`, and the second partner's `*_name_snapshot` is never captured while their FK stays populated. This contradicts design fix MISS-4, which requires both FKs nulled and both snapshots captured. See decision D1; this is not a live bug (demography is not wired into the tick loop, so the function is never called in production) and `dissolve_on_death` is correct against its own docstring. It is an integration gap this plan must close.

## Design decisions

### D1 — Where the both-partners-die case is handled

**Decision**: extend `couple.py:dissolve_on_death` to also resolve a couple that was dissolved at the *same* tick, rather than reimplementing snapshot logic inside `inheritance.py`.

**Rationale**: dissolving a Couple is `couple.py`'s single responsibility (Golden Rule of App Design; Ghezzi principles 2 and 3 — separation of concerns, high cohesion). Duplicating snapshot-and-null logic into `inheritance.py` would create the parallel twin that the project's DRY rule exists to prevent. `inheritance.py` stays the orchestrator of the death batch and calls `dissolve_on_death` once per deceased; the function becomes idempotent-per-partner instead of once-per-couple.

**Consequence**: this plan modifies `couple.py`, which is a §4.1 module in the whitepaper doc-sync table. The §4.1 update is already required by FR-032, so this adds no new obligation — but the doc-sync rule now bites for a second reason, and the task carrying this change must update the whitepaper in the same commit.

**Alternative rejected**: passing a `batch_deceased_ids` set down into `dissolve_on_death`. Rejected because it leaks the caller's batching concern into a function whose contract is about one agent, and because resolving "dissolved at this same tick" needs no knowledge of the batch.

### D2 — Module boundary between the two files

`inheritance.py` owns everything triggered by a birth or a death. `migration.py` owns everything triggered by a location decision, voluntary or forced. The orphan caretaker lives in `inheritance.py` because it is triggered by death; emergency flight lives in `migration.py` because it is a location decision. This matches the Plan 4 orchestrator, whose step 3 calls the former and step 5 the latter.

### D3 — Pure functions, no global state

Neither module decides tick ordering; that is Plan 4's orchestrator. Every public function takes its inputs explicitly (`simulation`, `tick`, `rng`, the resolved `template` dict) and returns its effect, so Plan 4 can compose them in the canonical six-step order without either module reaching for global state. Concretely: no module-level mutable caches, and the RNG is always passed in or derived from `get_seeded_rng(simulation, tick, phase)` with a phase string unique per subsystem.

### D4 — Two Scoops, not services/selectors

Per project rule, Epocha follows Two Scoops (fat models, thin views), explicitly **not** the HackSoftware services/selectors pattern. These modules are domain logic modules in the app package alongside `mortality.py`, `fertility.py` and `couple.py`, following the exact shape those already established: module-level functions, `from __future__ import annotations`, `TYPE_CHECKING` imports, lazy model imports inside functions to avoid circulars.

### D5 — The restricted formula evaluator

`derived_trait_formulas` is evaluated with an AST-based evaluator that whitelists nodes (`Expression`, `BinOp`, `UnaryOp`, `Constant`, `Name`, and the arithmetic operators) and resolves `Name` nodes only against the newly computed trait dict. Everything else — `Call`, `Attribute`, `Subscript`, `Import`, comprehensions, dunder access — raises. `eval()` on the raw string is forbidden even though the formulas come from versioned template files rather than user input: the surface is not opened just because today's inputs are trusted. SC-006 tests the refusals.

## Project Structure

### Documentation (this feature)

```text
specs/20260717-120706-demography-inheritance-migration/
├── spec.md                    # phase-2 artifact, approved
├── plan.md                    # this file
├── checklists/requirements.md # spec quality checklist
└── tasks.md                   # phase-4 artifact (/speckit-tasks, not created here)
```

`research.md` and `data-model.md` are deliberately **not** materialised. There is nothing to research: the design is CONVERGED and the spec carries zero `NEEDS CLARIFICATION` markers. There is nothing to model: the preflight confirms no schema change. This matches the three most recent Spec Kit features (`20260715-094457-world-economy-deprecation`, `20260715-111119-factions-round3-hardening`, `20260715-132752-economy-base-layer-audit`), none of which materialised those artifacts either. Producing empty ones would be ceremony.

### Source code (repository root)

```text
epocha/apps/demography/
├── inheritance.py          # NEW — birth path + death path
├── migration.py            # NEW — voluntary path + forced path
├── couple.py               # MODIFIED — dissolve_on_death same-tick fix (D1)
├── context.py              # unchanged, consumed
├── rng.py                  # unchanged, consumed
├── template_loader.py      # unchanged, consumed
├── models.py               # unchanged (no migration)
├── templates/*.json        # unchanged (schema already complete)
└── tests/
    ├── test_inheritance.py # NEW
    └── test_migration.py   # NEW

docs/whitepaper/
├── epocha-whitepaper.md    # MODIFIED — §4.1 extended
└── epocha-whitepaper.it.md # MODIFIED — §4.1 extended
```

**Structure Decision**: both modules live in the existing `epocha.apps.demography` app. No new app, no architectural placement question to escalate: the app's single responsibility is demographic dynamics, and inheritance and migration are demographic dynamics. The dependency direction is preserved — demography USES `world.government` (treasury), `economy.market` (subsistence constant), `agents.information_flow` (propagation) and `agents.movement` (travel speeds); none of them may import demography.

## Module design

### `inheritance.py`

Birth path:

- `inherit_trait(mother_val: float | None, father_val: float | None, h2: float, era_mean: float, era_sd: float, rng) -> float` — the Falconer & Mackay kernel, including the fix I-1 single-parent fallback when one parent value is `None`.
- `evaluate_derived_formula(expression: str, symbols: dict[str, float]) -> float` — the D5 restricted evaluator.
- `apply_trait_inheritance(child, mother, father, template: dict, rng) -> None` — polygenic pass over the heritability table, clamping, then the derived-formula pass. Writes `Agent` scalar traits and `personality` JSONB entries (default h² 0.30 for unpublished traits).
- `resolve_birth_attributes(template: dict, rng) -> tuple[str, str]` — gender from `sex_ratio_at_birth`, orientation from the era distribution.
- `apply_social_inheritance(child, mother, father, template: dict, zone_class_mean: float, rng) -> None` — the four class rules and the `education_level` regression (**trap 1**).
- `apply_inheritance_at_birth(child, mother, father, simulation, tick: int) -> None` — the single entry point a birth calls; loads the template, derives the RNG, sequences the above, sets `wealth = 0` and `zone = mother.zone`.

Death path:

- `resolve_heirs(deceased, template: dict) -> list` — the configured priority ladder, returning living heirs.
- `apply_estate_tax(total_estate_value: float, rate: float, government, primary_currency_code: str) -> float` — verbatim from the design; routes tax through `add_to_treasury` and returns the inheritable remainder.
- `distribute_estate(deceased, heirs: list, rule: str, inheritable: float) -> dict` — the five rules, returning the per-heir allocation without persisting, so the conservation invariant is assertable on the returned mapping alone.
- `transfer_loans_as_lender(deceased, heirs: list) -> None` — reassigns `Loan.lender`; falls back to `lender=None, lender_type="banking"`.
- `assign_orphan_caretaker(minor, tick: int) -> object | None` — **the Plan 4 orchestrator step 3 entry point**.
- `generate_mourning_memories(deceased, tick: int) -> None` — spouse, children, and `Relationship.strength > 0.6` (**trap 2**), weight 0.9.
- `process_inheritance_batch(simulation, tick: int, deceased_agents) -> None` — the death-path entry point; orders by descending age (fix C-3), calls `dissolve_on_death` per deceased (D1), settles each estate, assigns caretakers, emits `INHERITANCE_TRANSFER` events.

### `migration.py`

- `compute_zone_wage(simulation, zone, tick: int, window: int = 5) -> float` — mean of `EconomicLedger` `wage` rows over the window, per capita; aggregate query, never a Python loop.
- `compute_zone_unemployment(simulation, zone, tick: int) -> float` — fraction with a role but zero wage over 3 ticks; zero-population guard.
- `compute_distance_cost(from_zone, to_zone, world) -> int` — `ceil(distance_km / (walking_speed × tick_duration_days))` via `World.distance_scale` and `TRAVEL_SPEEDS`.
- `compute_expected_gain(unemployment_j: float, wage_j: float, wage_current: float, distance_cost_j: float) -> float` — the declared Harris & Todaro operational variant.
- `build_migration_outlook(agent, simulation, tick: int, zone_stats: dict) -> dict` — the whole context block, built from zone aggregates computed once per tick and passed in (see Risks).
- `coordinate_family_migration(agent, target_zone, tick: int, template: dict) -> list` — Mincer (1978); moves partner and children under `adulthood_age`, returns the household member ids for the single event payload.
- `evaluate_emergency_flight(agent, simulation, tick: int, template: dict, zone_stats: dict) -> object | None` — the three-condition trigger including fix I-5; returns the target zone or `None`.
- `process_emergency_flight(simulation, tick: int) -> None` — **the Plan 4 orchestrator step 5 entry point**; computes zone aggregates once, drives the above over the population, emits `TRAPPED_CRISIS` with MISS-3 co-zone propagation at weight 0.95, and `MASS_FLIGHT` above the 30% threshold.

## Build order

Strictly sequential; each step ends green. Test-first throughout: the red test precedes the implementation in every step.

1. **The trap fix and its regression net** — `couple.py:dissolve_on_death` same-tick resolution (D1), with the whitepaper §4.1 note in the same commit. Done first because `process_inheritance_batch` depends on it and because it is the only change to already-merged, already-audited code.
2. **The inheritance kernel** — `inherit_trait`, the restricted evaluator, `evaluate_derived_formula`. Pure functions, no ORM, fastest to drive red-green.
3. **The birth path** — `apply_trait_inheritance`, `resolve_birth_attributes`, `apply_social_inheritance`, `apply_inheritance_at_birth`. Closes User Story 1.
4. **The estate core** — `resolve_heirs`, `apply_estate_tax`, `distribute_estate`, plus the conservation test that SC-002 demands, per rule. Closes the money-moving half of User Story 2.
5. **The death batch** — `transfer_loans_as_lender`, `generate_mourning_memories`, `assign_orphan_caretaker`, `process_inheritance_batch`. Closes User Story 2 and User Story 3.
6. **The migration context** — the four computation helpers and `build_migration_outlook`. Closes User Story 4's context half.
7. **The migration paths** — `coordinate_family_migration`, `evaluate_emergency_flight`, `process_emergency_flight`, trapped-crisis and mass-flight emission. Closes User Story 4 and User Story 5.
8. **Closure** — whitepaper §4.1 extended in both languages, doc-sync table extended in its four copies (FR-032), full suite, `ruff`, phase-6 adversarial code audit to CONVERGED.

Steps 2 through 5 are `inheritance.py`; 6 and 7 are `migration.py`. The two modules do not import each other, so 6 could in principle start before 5 finishes — but the plan keeps them sequential because the phase-5 protocol is one atomic task at a time.

## Integration surface

- **Consumed, unchanged**: `add_to_treasury`, `compute_subsistence_threshold`, `compute_aggregate_outlook`, `propagate_information`, `TRAVEL_SPEEDS`, `SUBSISTENCE_NEED_PER_AGENT`, `get_seeded_rng`, `load_template`.
- **Modified**: `couple.py:dissolve_on_death` (D1) — the only change to merged code, and the only doc-sync trigger beyond FR-032.
- **Exposed to Plan 4**: `assign_orphan_caretaker` (step 3), `process_emergency_flight` (step 5), `process_inheritance_batch` and `apply_inheritance_at_birth` (called from the joint mortality-fertility resolution of step 2).
- **Not touched**: `simulation/engine.py`. Wiring is Plan 4. This plan must leave the tick loop exactly as it found it.

## Risks

| Risk | Mitigation |
|---|---|
| Conservation breaks and contaminates §4.2/§4.8, both CONVERGED | `distribute_estate` returns an allocation mapping without persisting, so conservation is assertable in isolation; a dedicated test per succession rule (SC-002) |
| N+1 in `build_migration_outlook` — it is per-agent over all zones, and Plan 4 will call it per tick | Zone aggregates computed once per tick in `process_emergency_flight` and passed in as `zone_stats`, never recomputed per agent; asserted with `assertNumQueries` in tests |
| The evaluator becomes an injection surface | AST whitelist, no `eval`, refusal tests (SC-006, D5) |
| Implementer invents an `education` field and produces a migration | Trap 1 carried verbatim into the task; SC-005 asserts `makemigrations --check --dry-run` stays clean |
| Design gap surfaces mid-implementation | Phase-5 escalation protocol: stop, return to Opus, revise spec or plan; never invent |

## Complexity Tracking

No constitution violations. Table intentionally empty.

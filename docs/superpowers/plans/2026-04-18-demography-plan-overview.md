# Demography Implementation — Plan Overview

> **Phase 3 artifact** of the canonical 7-phase workflow. This document describes the architectural decomposition of the Demography subsystem into sequential implementation plans. Detailed per-task breakdown with checkboxes is produced in Phase 4, one plan file at a time.

**Spec source**: `docs/superpowers/specs/2026-04-18-demography-design-it.md` (authoritative Italian spec, CONVERGED after 4 rounds of adversarial audit).

**Scope**: new Django app `epocha.apps.demography` with 12 modules, extensions to `Agent` model, integration hook in `simulation/engine.py`, 4 era templates, and historical validation against Wrigley-Schofield (1981) and HMD baselines.

## Plan decomposition (4 sequential plans)

The work is decomposed into four plans executed in strict order. Each plan ends with a working, testable subsystem that can be merged independently into `develop`. Dependencies between plans are acyclic: no plan N depends on a plan N+M for M>0.

### Plan 1 — Foundations: models, integration contracts, mortality

**Branch**: `feature/demography-1-foundations`
**Dependencies**: none (starts from clean `develop`)
**Estimated tasks**: 20

Delivers the data layer and the first scientific module (mortality), so that subsequent plans have a stable substrate.

Scope:
- New app scaffolding (`epocha/apps/demography/` with `__init__.py`, `apps.py`, `INSTALLED_APPS` registration)
- New models: `Couple`, `DemographyEvent`, `PopulationSnapshot`, `AgentFertilityState`
- `Agent` model extensions: `birth_tick`, `death_tick`, `death_cause`, `other_parent_agent`, `caretaker_agent` + migrations with backward-compatible defaults (populate `birth_tick` from existing `age`)
- Integration Contracts helpers (extracted as part of spec scope):
  - `epocha/apps/world/government.py:add_to_treasury()` helper
  - `epocha/apps/economy/market.py:SUBSISTENCE_NEED_PER_AGENT` module-level constant (extracted from the inline local)
  - `epocha/apps/demography/context.py:compute_subsistence_threshold()`
  - `epocha/apps/demography/context.py:compute_aggregate_outlook()`
- Template loader (`template_loader.py`) with 4 era templates as JSON fixtures: `pre_industrial_christian`, `pre_industrial_islamic`, `industrial`, `modern_democracy`, `sci_fi`
- RNG module (`rng.py`) with seeded per-subsystem streams
- Mortality module (`mortality.py`): Heligman-Pollard implementation, tick scaling (linear + geometric depending on q magnitude), cause-of-death attribution
- HP parameter numerical fitting task: `scipy.optimize.curve_fit` against Wrigley-Schofield pre-industrial life tables; store fitted parameters in the template (calibration task)
- Full unit test coverage for mortality, RNG, helpers, models
- Migration to `develop` via PR, tests green

Plan 1 leaves the repository with a demography app that can compute individual mortality deterministically but does not yet run in the tick pipeline.

### Plan 2 — Fertility, Couple market, LLM actions

**Branch**: `feature/demography-2-fertility-couple`
**Dependencies**: Plan 1 merged
**Estimated tasks**: 22

Delivers birth dynamics and couple formation, connecting the demography subsystem to the LLM decision pipeline.

Scope:
- Fertility module (`fertility.py`):
  - Hadwiger ASFR (canonical normalized form with `1/sqrt(π)`)
  - Becker modulation using Integration Contracts helpers (wealth signal, zone flp, outlook)
  - Malthusian soft ceiling with floor at `floor_ratio * baseline`
  - Joint mortality-fertility resolution for pregnant agents (childbirth mortality + neonatal survival conditional on maternal survival)
- Couple module (`couple.py`):
  - Gale-Shapley stable matching for initialization (deferred usage in Plan 4)
  - Homogamy compatibility scoring (Kalmijn-inspired weights)
  - Runtime `pair_bond` and `separate` handlers with tick+1 settlement (consistent with property market pattern)
  - Arranged marriage support via extended `pair_bond` payload (`for_child`, `match`)
  - Automatic couple dissolution on partner death with `agent_a_name_snapshot` / `agent_b_name_snapshot` population
  - `AgentFertilityState` management for `avoid_conception` 1-tick-settled flag
- `agents/decision.py` extensions:
  - Add `pair_bond`, `separate`, `avoid_conception` to the system prompt
  - Dynamic filter that removes era-unavailable actions from the prompt
- `simulation/engine.py` extensions:
  - Action handlers for `pair_bond`, `separate`, `avoid_conception`
  - Mood delta and emotional weight entries in the action dicts
- `dashboard/formatters.py`: verb entries for the three new actions
- Full unit test coverage for fertility, couple, joint resolution, action handlers

Plan 2 leaves the repository with a demography layer that reacts to LLM decisions but does not yet run autonomously per tick (that comes in Plan 4).

### Plan 3 — Inheritance and Migration

**Branch**: `feature/demography-3-inheritance-migration`
**Dependencies**: Plan 1 + Plan 2 merged
**Estimated tasks**: 22

Delivers the two remaining behavioral modules that integrate with existing subsystems (economy, information flow).

Scope:
- Inheritance module (`inheritance.py`):
  - Polygenic additive inheritance with Polderman-sourced heritability coefficients
  - `derived_trait_formulas` evaluator (restricted AST-based expression parser, no arbitrary code execution)
  - Per-era social class rules (patrilineal rigid, Clark 2014 regression, Solon-Chetty elasticity, meritocratic)
  - Education level intergenerational regression
  - Economic inheritance on death: primogeniture, equal_split, shari'a, matrilineal, nationalized
  - Estate tax via `add_to_treasury` helper
  - Loans-as-lender transfer on death
  - Simultaneous deaths batch ordering
  - Multi-generational cascade handling
  - Mourning memory cascade via existing `propagate_information` system
  - Orphan caretaker assignment logic
- Migration module (`migration.py`):
  - Migration context enrichment for `move_to` decisions (wage differential, unemployment, distance cost via `movement.TRAVEL_SPEEDS`, zone stability, Harris-Todaro expected gain)
  - Family coordination (Mincer 1978) extending existing `move_to` handler
  - Emergency flight (bypass-LLM under starvation conditions)
  - Trapped crisis event generation with co-zone memory propagation
  - Mass flight broadcast threshold (>30% flee)
- Full unit test coverage for inheritance, migration, edge cases (orphans, both-spouses-die, zero-population guards)

Plan 3 leaves the repository with all demographic modules implemented but not yet orchestrated into a per-tick process. That orchestration is Plan 4.

### Plan 4 — Initialization, Engine orchestration, Integration, Validation

**Branch**: `feature/demography-4-engine-validation`
**Dependencies**: Plan 1 + 2 + 3 merged
**Estimated tasks**: 20

Delivers the orchestrator and closes the subsystem with historical validation.

Scope:
- Initialization module (`initialization.py`):
  - Phase 1: age pyramid resampling from template PDF
  - Phase 2: Gale-Shapley retrospective couple formation across `marriage_market_radius`
  - Phase 3: synthetic genealogies with signal suppression and default personality/role population
  - Phase 4: consistency validation with logging (non-blocking)
  - `demographic_initializer` event with `rng_seed`, `template_hash`, `duration_ms`
- Engine orchestrator (`engine.py:process_demography_tick()`) with the 6 steps in canonical order:
  1. Implicit aging (no-op)
  2. Joint mortality-fertility resolution
  3. Orphan caretaker assignment
  4. Couple market (intent resolution tick+1)
  5. Emergency flight
  6. Population snapshot
- Zero-population guard and economy-disabled fallback at orchestrator entry
- Hook in `simulation/engine.py` calling `process_demography_tick` after `process_economy_tick_new`
- Context extension (`context.py:build_demographic_context()`) injecting life-situation block into decision prompts
- Historical validation suite in `tests/test_validation_historical.py`:
  - Validation 1: 1000-tick, 500-agent pre-industrial simulation; assert 5 indicators within tolerances
  - Validation 2: shock scenario (food supply -50% for 365 ticks); assert mortality spike, fertility drop, emergency flight activation, post-shock recovery
  - Validation reports written to `docs/validation/`
- Integration test (`test_integration_demography.py`) — full end-to-end scenario similar to Plan 3c of Economy
- Final adversarial code audit (critical-analyzer on the integrated codebase, per Phase 6 heavy gate)
- Performance benchmark: 500 agents × 1000 ticks < 30 minutes wall time

Plan 4 leaves the Demography subsystem fully integrated with the tick engine, historically validated, and closed.

## Dependencies graph

```
[develop]
    ↓
Plan 1 (Foundations + Mortality) ──→ merged to develop
    ↓
Plan 2 (Fertility + Couple + Actions) ──→ merged to develop
    ↓
Plan 3 (Inheritance + Migration) ──→ merged to develop
    ↓
Plan 4 (Init + Engine + Validation) ──→ merged to develop
```

Strict sequentiality: each plan starts from the develop HEAD updated with the previous plan. No cross-plan parallelism.

## Estimated totals

- **Plans**: 4
- **Tasks estimate**: 20 + 22 + 22 + 20 = **84 tasks**
- **Wall-clock per plan** (depending on model assignment per phase 5): 2-4 days each
- **Subsystem total**: ~8-16 days of active development

Task count is within the 60-80 typical range for a complex Epocha subsystem (the rule caps expectations, but demography is the largest subsystem on the roadmap; 84 is justified).

## Gate status of this Phase 3 artifact

| Component | Status |
|-----------|--------|
| Spec source CONVERGED (Phase 2 heavy gate) | Done |
| Architectural decomposition (this document) | Done |
| **Light gate — human validation of plan decomposition** | **Pending** |
| Phase 4: per-plan detailed task breakdown | Not started |

After human validation of this overview, we move to Phase 4: draft Plan 1 file with detailed checkbox tasks, request light gate + post-validation critical review, then execute Phase 5 starting from Plan 1.

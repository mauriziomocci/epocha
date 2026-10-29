# Implementation Plan: rule-based couples and the protagonist cap

**Branch**: `20261029-123404-rule-based-couples` | **Date**: 2026-10-29 | **Spec**: [spec.md](spec.md) (phase 2 approved by the Trinity, decision D-29-21; audit CONVERGED at round 12, delta round 13 in [checklists/audit.md](checklists/audit.md))

**Input**: Feature specification from `specs/20261029-123404-rule-based-couples/spec.md`

**Contract**: one CONTRACT CHANGE, the one the spec header declares and D-RBC-09 approves: the viewset writes of `/api/v1/simulations/` (`POST`, `PUT`, `PATCH /{id}/`, through `SimulationSerializer`) answer `400` with the body `{"config":{"max_protagonists":["Must be a whole number of 0 or more; omit the key to use the default of 30."]}}` when `config.max_protagonists` is present and is not a non-boolean integer of 0 or more (`null` included). Nothing else in any request or response changes shape: no route, field, enum value, `error_code` or status of a request that succeeds today. `output_decision` is unchanged (FR-021 left the spec with D-29-18, F6). A test freezes the field sets of `SimulationSerializer`, `AgentSerializer` and `DecisionLogSerializer` (SC-013).

**Data model**: no database field and no migration. The `couple` section of the era templates changes as FR-012, FR-013, FR-015 and FR-016 state; `max_protagonists` lives in the existing `Simulation.config` JSON field.

**Prerequisite**: phase 5 starts only after the Plan 4 branch (`20260826-144432-demography-plan4-wiring`, reopened by D-29-20 for mortality evaluated at continuous ages) is merged into `develop`. Every code reference in this plan was verified on the Plan 4 head `d8cd817` on 2026-10-29; the preflight tasks T003 and T004 re-verify them on the realigned tree.

## Summary

Couples stop depending on the language model. A pure module, `demography/nuptiality.py`, implements the Coale-McNeil first-marriage schedule in the standardized form of Rodriguez and Trussell (1980) as reported by Kaneko (2003), conditioned on the era's minimum age, with the location parameter derived from the historical observed mean by Brent's method. Step 2 of the demography tick runs, after the intent resolver, a female-dominant marriage market in `demography/couple.py`: eligible women draw a marriage event from the schedule (or from a constant remarriage hazard once widowed or separated), and the women who draw it propose to the eligible men of their market through the existing Gale-Shapley `stable_matching` with the existing homogamy score. The founding population is built with the same market and the conditioned schedule instead of universal pairing. Mourning and the market radius become rules; `allowed_types` is removed. In the `agents` app one selection function caps LLM deliberation at K protagonists per tick (default 30, 0 for validation), ordered head of state, group leaders, then id. The serializer validates the new key at the boundary. A pre-existing crash of `update_group_cohesion` on a non-string `target` is fixed.

## Technical Context

**Language/Version**: Python 3.12 (ruff `target-version = "py312"`).

**Primary Dependencies**: Django 5.x, DRF 3.15, Celery; `scipy` already a project dependency (`scipy.special.gammaincc`, `scipy.special.gammainc`, `scipy.special.gamma`, `scipy.integrate.quad`, `scipy.optimize.brentq`).

**Storage**: PostgreSQL. No migration.

**Testing**: pytest with pytest-django, `CaptureQueriesContext`, `django_assert_num_queries`, `caplog`, `unittest.mock.patch`. Command per task: `docker compose -f docker-compose.local.yml exec -T web pytest <path> -q`; when the container is not running, `DATABASE_URL=<a database this session owns> pytest <path> -q` from the repository root (parallel-session isolation: never the user's database).

**Target Platform**: Linux containers (Docker Compose).

**Project Type**: Django web service with a Celery tick loop.

**Performance Goals**: LLM decision calls per tick bounded by K, independent of the living population N. The marriage market issues a constant number of queries per tick (FR-003), reads O(N) rows, and computes O(S·M·log M) per market; measured by SC-005 with a failure exponent of 2.3.

**Constraints**: determinism from the seed for every rule-based draw (streams `couple` and `initialization`, ascending id order); no per-agent query in any new path; the cached template dict is never mutated (`load_template` shares one dict, enforced by `test_template_validation.py`).

**Scale/Scope**: validity range declared by the spec, tens of thousands of agents for the individual models; above that, cohort or weighted models (out of scope).

## Constitution Check

| Principle | Status for this plan |
|---|---|
| I. Scientific method | Every formula is cited below with its source and the verification status the spec records; every non-sourced parameter is a declared tunable heuristic (spec, "Parametri per era"). |
| II. Verify before asserting | Code facts verified on the Plan 4 head `d8cd817`; spec numbers recomputed with scipy on 2026-10-29 (u = 25.580, 18.639, 25.571, 28.172; F(14) = 1.68e-6 for the Christian era; F*(50) = 0.8776; bracket ends 18.78 and 46.48; deterministic SC-002 propagation 25.4999 and 0.8776; mutant u = 25.5 gives 25.421). T003 repeats the symbol check on the realigned tree. |
| III. Adversarial audit | Spec audit CONVERGED (round 12; delta round 13). The code audit by `critical-analyzer` is the phase-6 gate (T088). |
| IV. Three-step design | Done in the spec ("Registro del design"); this plan adds no design decision the spec did not make, only implementation choices, listed in "Implementation decisions fixed by the plan" so that the Sonnet implementer invents nothing. |
| V. Evidence-based verification | Confidence levels are reported per phase: unit tests, then integration test, then the phase-6 measurement scripts. |

No violation needs a Complexity Tracking entry.

## Scientific formulas and their sources

Every formula below goes into the docstring of the function that implements it, with author, year, equation number and verification status.

- **(R1) standardized density**, Rodriguez and Trussell (1980), as reported by Kaneko (2003, eq. 2; bulletin listed in Kaneko's bibliography, p. 260; bulletin itself not read): `g_s(z) = β/Γ(α/β) · exp[−α(z − μ) − exp(−β(z − μ))]`, with `α = 1.145`, `β = 1.896`, `μ = −0.805`, constant `β/Γ(α/β) = 1.2813` (1.28082 with the rounded α and β).
- **(R1a) standardized CDF**, derived: `G_s(z) = Q(α/β, exp(−β(z − μ)))`, `Q` the regularized upper incomplete gamma (`scipy.special.gammaincc`). Substituting `y = exp(−β(t − μ))` in the integral of (R1) from −∞ to z gives `Γ(α/β, y)/Γ(α/β)`; the docstring states this step.
- **(R2) era schedule**, Kaneko (2003, eq. 3-4), Coale and McNeil (1972): `f(x) = C·g_s((x − u)/b)/b`, `F(x) = C·G_s((x − u)/b)`.
- **(R3) hazard**, single-decrement definition: `h(x) = f(x)/(1 − F(x))`, with `1 − F(x)` computed as `(1 − C) + C·P(α/β, y)` (`P` = `scipy.special.gammainc`) so that it does not cancel; `h = 0` where that survival is not positive (FR-002). Per tick: `p = 1 − exp(−h(x)·Δt)`, `Δt = tick_duration_hours / 8760 · acceleration` (the fertility conversion, `fertility.py`, `tick_birth_probability`), `p = 0` below `min_marriage_age_female`.
- **(R4) schedule conditioned on the minimum age**: `F*(x) = (F(x) − F(m))/(1 − F(m))` for `x ≥ m`, 0 below; `C* = (C − F(m))/(1 − F(m))`.
- **(R5) location from the observed mean**: `E[X | m ≤ X ≤ 50] = ∫_m^50 x·g_s((x − u)/b)/b dx / [G_s((50 − u)/b) − G_s((m − u)/b)] = mean_age_female`, solved for `u` by `scipy.optimize.brentq` on `[m − 10·b, 50]`, `xtol = 1e-6` years; the integral by `scipy.integrate.quad`.
- **Remarriage**: constant hazard `r_f`, per tick `1 − exp(−r_f·Δt)`; tunable heuristic, no source (spec, FR-006).
- **Mourning in ticks**: `ceil(mourning_days · 24 / (tick_duration_hours · acceleration))` (FR-006, round 12 R12-02).
- **Matching**: Gale and Shapley (1962), proposer-optimal stable matching, `couple.stable_matching` (audited, §4.1.3); preferences by the homogamy score of Kalmijn (1998), equation (4.6), `couple.homogamy_score` (audited).
- **Female-dominant one-queue market**: the idea of the SOCSIM one-queue scheme (Hammel et al. 1979 line; the scheme read only in the SOCSIM ChangeLog through search results), cited as an idea, no code read (spec, "Licenze e attribuzione").
- **Shape universality**, Coale (1971): cohorts differ only in origin, scale and proportion marrying; the assumption that justifies one standard shape for every era.
- **Two-sex problem**, Schoen (1981): reason for rejecting two independent sex schedules (spec K1).
- **Historical value** 25.5: Wrigley et al. (1997, pp. 130-34) read only in the secondary copy of Munro (`14POPERMTables.doc`, Table 8), provisional.

## Architectural placement and reuse

Every component below was searched for before planning it. The reuse statements use the form the global rules require.

**1. The first-marriage schedule.** Searched `demography/` (`mortality.py`, `fertility.py`, `couple.py`, `truncated_moments.py`, `clark_calibration.py`) and `epocha/common/` for a nuptiality schedule, a Coale-McNeil density or a gamma-based CDF. Found nothing; `truncated_moments.py` solves a different fixed point. Building new. `demography/nuptiality.py` goes in `demography` because it is a pure population model of the same kind as `mortality.py` and `fertility.py` (one app, one thing; Ghezzi: cohesion, information hiding of the numerical method behind `FirstMarriageSchedule`). Rejected: `couple.py`, which orchestrates couples against the database and would mix a pure model with ORM code; `fertility.py`, a different model with its own audited chapter; `epocha/common/`, because no other app needs it. Dependency: `nuptiality` imports only `math`, `functools`, `dataclasses` and `scipy`; `couple`, `initialization` and `template_loader` use it, never the reverse.

**2. The marriage market.** Searched `couple.py` (`stable_matching`, `homogamy_score`, `form_couple`, `meets_marriage_age`, `active_couple_partners`, `resolve_pair_bond_intents`), `initialization.form_initial_couples`, `orchestrator` (`run_couple_formation_step`, `stream_for`, `age_in_years`, `_tick_duration_hours`, `DemographyTickContext`), `rng.ALLOWED_PHASES`. Found and reused: `stable_matching`, `homogamy_score` (extended), `form_couple`, `meets_marriage_age` (inside the one eligibility function), `active_couple_partners`, `age_in_years`, `stream_for` with the existing phases `couple` and `initialization`, `HOURS_PER_YEAR`. Building new only the market functions. They go in `demography/couple.py` because that module is the one owner of couple formation (one owner per concept); the step driver `run_couple_formation_step` stays in `orchestrator.py` and calls it. Rejected: a new `market.py`, which would split the owner of `Couple` creation in two; `orchestrator.py`, which drives steps and owns no couple rule. Growing `couple.py` by about 200 lines is accepted: cohesion outranks file length, and each new function stays under 40 lines.

**3. The one eligibility rule (FR-006).** Searched for a mourning or widowhood check: none (`mourning_ticks` is loaded and read by no code, verified with `grep -rn mourning_ticks epocha`). `meets_marriage_age` is the existing single marriage-age rule; the new `marriage_ineligibility` wraps it with mourning and is used by the market, the initialization and the intent resolver, so there is still one rule.

**4. The sentiment map (FR-004).** Searched for a bulk relationship reader: `agents/relationships.py` and `agents/affinity.py` read relationships per agent. Found nothing that returns sentiments for a set of pairs in one query. Building `couple.read_sentiments` beside its only consumer, `homogamy_score`.

**5. The deliberating-agents selection (FR-008 to FR-011).** Searched `simulation/tasks.py` (`run_simulation_loop`), `simulation/engine.py` (`SimulationEngine.run_tick`), `agents/tasks.py`, `agents/decision.py`, `demography/orchestrator.minor_agent_ids`, and the approved life-course spec (`20261029-093933-agent-life-course`, FR-003: one selection function in `agents`, not yet implemented). Found the two inline querysets `Agent.objects.filter(simulation=..., is_alive=True).exclude(id__in=minor_agent_ids(...))` and no function. Building `epocha/apps/agents/deliberation.py` with `select_deliberating_agents`, the one function the life-course spec will extend (or, if the life-course work item lands first, extending its function instead: T004 decides). It goes in `agents` because which agents deliberate is a rule of the agent decision layer, next to the decision loop (the life-course spec places it there too). Rejected: `simulation` (the tick driver would own an agent rule), `agents/tasks.py` (the sequential engine would import a Celery module), `demography` (the dependency would point the wrong way: `agents` uses `demography`, never the reverse). The simulation app USES `agents.deliberation`, not the reverse.

**6. The `max_protagonists` predicate.** One predicate, `agents.deliberation.is_valid_max_protagonists`, used both by `SimulationSerializer.validate_config` (FR-020, boundary) and by `max_protagonists` (FR-011, engine fallback), so the boundary and the engine cannot disagree on what is valid. The serializer lives in `simulation`, which already depends on `agents`.

**7. The faction fix (FR-022).** In place in `agents/factions.py::update_group_cohesion`.

**8. The measurement scripts (SC-005, SC-007).** `scripts/` already holds `build_map_i18n.py`; the two scripts go there because the spec puts them outside the suite. Rejected: a management command, which would add a runtime surface nobody calls; the test suite, which the spec excludes for cost.

**Apps touched: three** (`demography`, `agents`, `simulation`), within the limit. `epocha/common/` is not touched.

## Implementation decisions fixed by the plan

These are the choices the spec leaves to implementation. They are fixed here so that no phase-5 task has to decide anything.

- **PD-01 Draw order and stream consumption.** The market draws from the tick's `couple` stream (`stream_for(simulation, tick, phase="couple")`), which the resolver receives and does not use. It consumes exactly one `rng.random()` per eligible woman, in ascending id, whatever her probability; a woman is a seeker when the draw is `< p`. The consumption therefore does not depend on the probabilities.
- **PD-02 Market order.** Markets are keyed by `zone_id` for `same_zone` (the null zone is an ordinary key) and by the single key `None` for `world`; keys are visited in the order `sorted(keys, key=lambda k: (k is not None, k or 0))`, null first.
- **PD-03 Proposers and respondents.** Seekers (women) are proposers, candidates (men) respondents, both lists sorted by id; couples are written in ascending woman id. `couple_type = template["couple"]["default_type"]`.
- **PD-04 Score inputs.** `homogamy_score(a, b, weights, *, sentiments, ages, age_tolerance_years=10.0)`. `ages` maps agent id to `age_in_years(agent, tick, tick_duration_hours, acceleration)`. `sentiments` maps `pair_key(a_id, b_id) = (min, max)` to the sentiment of the lowest-primary-key `Relationship` row between the two agents in either direction, which is the row `.first()` returns today (`Relationship` has no `Meta.ordering`, so `.first()` orders by pk); an absent key reads 0.5, the audited neutral value.
- **PD-05 Marriage history.** One query on the simulation's dissolved couples, values `agent_a_id`, `agent_b_id`, `dissolved_at_tick`, `dissolution_reason`. `ever_partnered` holds every non-null partner id of a dissolved couple. `widowed_at_tick[id]` is the largest `dissolved_at_tick` among couples with `dissolution_reason == "death"` in which `id` is the non-null side (`dissolve_on_death` nulls the deceased's FK, so the survivor is the non-null side). Mourning follows death only, not separation.
- **PD-06 Mourning.** `mourning_ticks = ceil(mourning_days * 24 / (tick_duration_hours * acceleration))`, written literally (not through an inverted Δt, which reads 365.00000000000006 on a daily world and rounds up to 366). An agent is in mourning when `tick − widowed_at_tick < mourning_ticks`. Mourning applies to both sexes.
- **PD-07 Seek probability.** For an eligible woman in `ever_partnered`: `1 − exp(−r_f·Δt)`; otherwise `schedule.tick_probability(age, Δt)`. `Δt = tick_duration_hours / HOURS_PER_YEAR * acceleration`, written inline as `fertility.py` does (deferral R3 below).
- **PD-08 Market population.** Alive, `gender ∈ {male, female}`, `sexual_orientation ∈ {heterosexual, bisexual}`, not in `active_couple_partners`, and `marriage_ineligibility(...) is None`. One query for the agents, full rows with `.select_related("simulation")` so that `form_couple` (which reads `a.simulation`) costs no query per couple, plus `active_couple_partners`, plus the history: three queries. The sentiment query is the fourth and runs only when at least one seeker and one candidate exist.
- **PD-09 Initialization.** `form_initial_couples` builds a `DemographyTickContext` at `simulation.current_tick`, reads the same market population, draws one `rng.random()` per eligible woman in ascending id from `stream_for(simulation, simulation.current_tick, phase="initialization")` (the demography `initialization` stream is unused today; the economy one is namespaced apart, `economy/rng.py`), declares her married when the draw is `< schedule.conditional_cdf(age)`, and matches the declared women with the same market function. The orientation filter of PD-08 therefore applies at founding too (today `form_initial_couples` filters only by gender): this is stated by the spec clarification D-29-22 of D-29-21 (edge case on gender and orientation, and FR-005 pointing to point 1 of "Il mercato matrimoniale"), not inferred, and is recorded in the commit and in §4.1.3.
- **PD-10 Location cache.** `nuptiality.schedule_for(mean_age, sd_age, proportion, min_age)` is `functools.lru_cache(maxsize=32)`; the loader calls it to validate (rejecting the template when `brentq` fails), and the market calls it again through `first_marriage_schedule(template["couple"])`, a cache hit. `u` is never written into the template dict, which the loader cache shares across callers.
- **PD-11 Numerical guards.** In (R1) and (R1a), when `t = −β(z − μ) > 700` the density is 0.0, `G_s` is 0.0 and `P` is 1.0, instead of an `OverflowError` from `math.exp`. `1 − F(m)` in (R4) is strictly positive for every template the loader accepts, because the loader requires `mean_age_female > m` and a solvable (R5); no further guard.
- **PD-12 Protagonist priority.** One queryset: living agents of the simulation, `.exclude(id__in=minor_agent_ids(simulation, tick))` (kept until the life-course work item replaces it), annotated `priority = Case(When(Exists(Government head_of_state = OuterRef("pk"), simulation = simulation), then 0), When(Exists(Group leader = OuterRef("pk"), simulation = simulation), then 1), default 2)`, ordered `("priority", "id")`, sliced `[:K]`, returned as a list of `Agent`. `K = 0` returns `[]` before any query. The Celery path maps the list to ids; the sequential path iterates it.
- **PD-13 Reading K.** `max_protagonists(simulation)`: absent key returns 30 silently; a valid value is returned; an invalid one (non-int, bool, negative, `None`) returns 30 and logs at ERROR, every time it is read (FR-011).
- **PD-14 Serializer.** `SimulationSerializer.validate_config(self, value)` checks only when `value` is a dict containing `max_protagonists`; it raises `serializers.ValidationError({"max_protagonists": [MAX_PROTAGONISTS_ERROR]})` with the exact message of FR-020, and otherwise returns `value` unchanged.
- **PD-15 Faction fix.** `target_is_member = isinstance(target, str) and bool(target) and any(...)`.
- **PD-16 `stable_matching` queue.** `free_proposers` becomes a `collections.deque` with `popleft()`: the same first-in-first-out order, so a step-for-step identical run and the same matching, ties included, without the O(S) cost of `list.pop(0)` inside a loop of up to S·M proposals, which would push the founding matching above the exponent SC-005 allows. The docstring's "O(n * m)" becomes "O(n·m·log m), with 2·n·m score evaluations" (R7-01 of the audit corrected the spec, not the code).
- **PD-17 Test seams.** Pure tests pass the probability callable to `draw_seekers` directly. Database tests that need `p = 1` monkeypatch `epocha.apps.demography.couple.seek_probability_for` to return `lambda woman: 1.0`, and initialization tests that need universal declaration monkeypatch `epocha.apps.demography.nuptiality.FirstMarriageSchedule.conditional_cdf` to `lambda self, x: 1.0`. No production parameter exists only for tests.
- **PD-18 Realignment after the Plan 4 merge.** The branch is pushed and the global rules forbid force-push, so the default is `git merge --no-ff origin/develop` into the branch. A rebase is used only if the user explicitly authorizes the force-push of this branch in chat.
- **PD-19 Doc-sync commit groups.** The doc-sync rule requires the whitepaper chapter in the same commit as the code it describes. Tasks stay atomic and are flagged one at a time, but a group of tasks marked `Commit group G<n>` shares one commit, made at the last task of the group.

## Module and file changes

| File | Change | FR / SC |
|---|---|---|
| `epocha/apps/demography/nuptiality.py` | NEW: constants α, β, μ, observation ceiling, bracket multiple, solver tolerance; `standard_density`, `standard_cdf`, `_standard_lower`; `FirstMarriageSchedule` (`density`, `cdf`, `hazard`, `conditional_cdf`, `tick_probability`); `truncated_mean`; `location_from_observed_mean`; `schedule_for` (cached); `first_marriage_schedule(couple_cfg)` | FR-001, FR-002, FR-016; SC-001, SC-002 |
| `epocha/apps/demography/couple.py` | `stable_matching` deque and docstring; `pair_key`; `read_sentiments`; `homogamy_score` new signature; `MarriageHistory`, `read_marriage_history`; `mourning_ticks`; `marriage_ineligibility`; `MarketPopulation`, `read_market_population`; `seek_probability_for`; `draw_seekers`; `partition_by_market`; `match_markets`; `form_matched_couples`; `run_marriage_market`; resolver uses `marriage_ineligibility` | FR-003, FR-004, FR-006, FR-007; SC-003, SC-004, SC-009, SC-010 |
| `epocha/apps/demography/orchestrator.py` | `run_couple_formation_step` calls `run_marriage_market` after the resolver; docstrings of the step and of its `DEMOGRAPHY_STEPS` entry; the comment in `run_demography_tick` about `form_initial_couples` | FR-003 |
| `epocha/apps/demography/initialization.py` | `form_initial_couples` rewritten on the market; module docstring and the "No RNG stream" comment rewritten | FR-005; SC-008 |
| `epocha/apps/demography/template_loader.py` | SCHEMA: `mourning_ticks` → `mourning_days`, `allowed_types` removed, `first_marriage` and `remarriage_annual_rate_female` added; `ALLOWED_MARRIAGE_MARKET_RADII`; `_check_couple_ranges`; `_check_first_marriage_solvable`; called from `validate_template` | FR-012, FR-013, FR-015, FR-016; SC-012 |
| `epocha/apps/demography/templates/*.json` (5) | keys as in the spec table "Parametri per era"; `industrial` radius `same_zone` | FR-012, FR-013, FR-015, FR-016 |
| `epocha/apps/agents/deliberation.py` | NEW: `DEFAULT_MAX_PROTAGONISTS = 30`, `is_valid_max_protagonists`, `max_protagonists`, `select_deliberating_agents` | FR-008 to FR-011; SC-006 |
| `epocha/apps/agents/factions.py` | `update_group_cohesion` ignores a non-string `target` | FR-022; SC-014 |
| `epocha/apps/simulation/tasks.py` | chord header from `select_deliberating_agents` | FR-008, FR-010 |
| `epocha/apps/simulation/engine.py` | sequential loop from `select_deliberating_agents` | FR-008, FR-010 |
| `epocha/apps/simulation/serializers.py` | `SimulationSerializer.validate_config`, `MAX_PROTAGONISTS_ERROR`, class docstring | FR-009, FR-020; SC-013 |
| tests | `demography/tests/test_nuptiality.py` (NEW), `test_marriage_market.py` (NEW), `test_couple.py`, `test_initialization.py`, `test_template_loader.py`, `test_template_validation.py`, `test_demography_cost.py`, `test_orchestrator_order.py`; `agents/tests/test_deliberation.py` (NEW), `test_factions.py`; `simulation/tests/test_api.py`, `test_api_contract.py` (NEW), `test_tasks.py`, `test_engine.py`, `test_rule_based_couples_integration.py` (NEW) | all SC |
| `scripts/measure_marriage_market_cost.py`, `scripts/measure_nuptiality_fertility.py` | NEW phase-6 measurement scripts | SC-005, SC-007 |
| `docs/whitepaper/epocha-whitepaper.md` and `.it.md` | §3.2, §4.1.0, §4.1.2, §4.1.3 (calendar R1-R5, market, remarriage, mourning, radius, equation (4.6) text, initialization, Table 4.5, Simplifications), §4.7, §6.2, §7.1 (two rows of Table 7.1), §7.3 (one row of Table 7.2), §11, Appendix A, Appendix C, §13 references | FR-018 |
| `CLAUDE.md`, `README.md`, `README.it.md`, memory `feedback_whitepaper_doc_sync.md` and its copy in `docs/memory-backup/` | doc-sync table row §4.1 gains `nuptiality` | FR-018 |
| `docs/build-map/epocha-build-map.html` | status at every checkpoint, both languages, by the session that owns the map | FR-018 |
| `specs/20261029-123404-rule-based-couples/phase6-measurements.md` | NEW at phase 6: the SC-005 and SC-007 numbers and the indicative male age, as the spec requires | SC-005, SC-007 |

## Pipeline ordering and integration surface

Step 2 of `DEMOGRAPHY_STEPS` keeps its index, name and `rng_phases=("couple",)` and runs two phases in order: the intent resolver (as today, plus mourning), then the market. Mortality (step 3) runs after, so a woman who marries at T and dies at T is a widowhood the next tick sees; fertility (step 7) sees the couples formed at T, as the step's `why_here` requires.

```text
run_demography_tick
  step 1 separations
  step 2 couple_formation
         resolve_pair_bond_intents (mourning via marriage_ineligibility)
         run_marriage_market
           read_market_population   3 queries
           seek_probability_for     pure
           draw_seekers             pure, stream "couple"
           form_matched_couples
             read_sentiments        1 query (only with seekers and candidates)
             match_markets          pure, stable_matching per market
             form_couple            1 INSERT per couple, one transaction
  steps 3-8 unchanged
run_simulation_loop / SimulationEngine.run_tick
  select_deliberating_agents        constant queries, at most K agents
```

Integration surfaces: `household_keys`, inheritance and family migration read couples through `active_couple_partners` and are unchanged; `fertility.tick_birth_probability` reads couple membership as today. The dashboard and the chat are not touched.

## Doc-sync obligations

The whitepaper chapters change in the commit of the code they describe (PD-19); the commit groups in `tasks.md` name the chapter for each. The full list (FR-018): §4.1.3 (calendar R1-R5 with the derivation of (R1a), market, remarriage, mourning, radius, the text of equation (4.6), the initialization paragraph, Table 4.5 with removed, renamed and new keys, Simplifications rewritten); §4.1.2 (with `require_couple_for_birth` equation (4.2), a Hadwiger schedule for all women, applies to married women only: a model error, realized TFR 2.374 without mortality against `H = 5`, no refit of `H`, `R`, `T` repairs it, marital-fertility work item deferred); §4.1.0 (step 2 with its two phases; the initialization); §3.2 (the K cap; `config` replaced whole on write); §4.7 (the FR-022 fix); §6.2 (new keys and their heuristic status; the three never-read keys become one, `marriage_market_type`); §7.1 (Table 7.1 rows "Couple formation (European marriage pattern)" and "Fertility (Hadwiger ASFR fit)"); §7.3 (Table 7.2 row "Fertility (Hadwiger fit)" unreachable in the eras that require a couple); §11; Appendices A and C; §13 entries for Coale (1971), Coale and McNeil (1972), Rodriguez and Trussell (1980), Kaneko (2003), Schoen (1981), Wrigley et al. (1997) and the Munro document, and for Walker and Davis (2013) only if the text cites it. The doc-sync table row §4.1 gains `nuptiality` in its four copies at once (`CLAUDE.md`, `README.md`, `README.it.md`, memory `feedback_whitepaper_doc_sync.md`, whose repository copy is `docs/memory-backup/feedback_whitepaper_doc_sync.md`). README check: both READMEs are reread for statements the change makes false (the `demography/` line of the tree, the status table row "Demography (Plan 1+2)", the roadmap paragraph) and updated only where false. The build map records the plan, each checkpoint and the closure, in both languages, republished to the same URL by the session that owns it, with `scripts/build_map_i18n.py fingerprint` after each text change.

## Gates

- Per task: red test first where behaviour changes, touched-area tests, 8-point review.
- Per phase of `tasks.md`: module suite.
- Before phase 6: the mechanical taste gate on changed files (functions over 40 lines, nesting over 3, `ruff check --select C901,PLR0912,PLR0915,PLR1702`), full suite, `ruff check .` and `ruff format --check .`.
- Phase 6 (heavy gate): the measurement scripts SC-005 and SC-007 (both configurations) with their failure conditions, the integration run's indicative male age, `critical-analyzer` on the code, Matteo-mode review of the branch diff with the thresholds, the 8/10 quality score, explicit validation of closure.

## Rinvii (pre-existing defects found while planning, out of scope)

None of these goes into the code of this work item. Each is to be opened as a work item on the build map by the session that owns it.

- **R1 No mechanical taste gate in CI.** The project has no `quality_gate.py` and `pyproject.toml` selects only `E, F, I, N, W, UP`; the global rules require the gate in CI. This work item runs it locally (T084).
- **R2 No import-contract check, and an app-level cycle.** `agents/decision.py` and `agents/movement.py` import `world`, while `world/generator.py` and `world/election.py` import `agents`. No import-linter configuration exists.
- **R3 The Δt conversion is written inline in three places.** `fertility.py` (`tick_birth_probability`, `HOURS_PER_YEAR`), `mortality.py` (`tick_mortality_probability`, literal `8760.0`) and now the market. One helper would remove the copies; extracting it touches two audited modules and belongs to a refactor work item.
- **R4 Which relationship counts in the homogamy score.** `Relationship.Meta.unique_together` includes `relation_type`, so a pair can carry several rows, and the score takes the lowest-pk one, an arbitrary relation type. The sentiment map keeps that behaviour (PD-04); choosing the relation type is a model question for the agents owners.
- **R5 Per-intent queries in `resolve_pair_bond_intents`.** One `Agent` read per target and `is_in_active_couple` per proposer and target; bounded by the intents, at most K after this work item. Belongs to the id-resolution work item (spec deferral 7).
- **R6 Template reloaded by name in the resolvers.** `resolve_pair_bond_intents` and `resolve_separate_intents` call `load_template` by name instead of receiving `context.template`; a cache hit, but a second way to obtain the template.
- **R7 The `slow` pytest marker is described as "downloads bge-m3 model".** Reusing it for long demography tests would mislabel them; if the User Story 1 integration test exceeds its time budget (T069), a marker decision is needed.
- **R8 Unregistered `custom_exception_handler`.** Already spec deferral 8; listed so that this plan does not register it by accident.

## Project Structure

### Documentation (this feature)

```text
specs/20261029-123404-rule-based-couples/
├── spec.md
├── checklists/audit.md
├── plan.md                    this file
├── tasks.md
└── phase6-measurements.md     written at phase 6
```

`research.md`, `data-model.md`, `quickstart.md` and `contracts/` are not created: the research is the spec's source table and design log, the data model has no database change (the template schema change is the table above), and the one contract change is stated at the top of this plan and frozen by SC-013. Four files repeating the spec would be four places to drift.

### Source code (repository root)

```text
epocha/apps/demography/
├── nuptiality.py              NEW
├── couple.py                  market, eligibility, sentiments
├── initialization.py          founding population on the market
├── orchestrator.py            step 2 calls the market
├── template_loader.py         couple schema
├── templates/*.json           five templates
└── tests/                     test_nuptiality.py, test_marriage_market.py NEW
epocha/apps/agents/
├── deliberation.py            NEW
├── factions.py                FR-022
└── tests/test_deliberation.py NEW
epocha/apps/simulation/
├── serializers.py             validate_config
├── tasks.py, engine.py        use the selection
└── tests/test_api_contract.py, test_rule_based_couples_integration.py NEW
scripts/
├── measure_marriage_market_cost.py     NEW
└── measure_nuptiality_fertility.py     NEW
```

**Structure Decision**: the existing Django app layout; no new app.

## Complexity Tracking

No constitution violation to justify.

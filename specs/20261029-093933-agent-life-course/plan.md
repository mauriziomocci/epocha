# Implementation Plan: agent behaviour by age across the life course

**Branch**: `20261029-093933-agent-life-course` | **Date**: 2026-10-29 | **Spec**: [spec.md](spec.md) (phase 2 approved provisionally by the Trinity, decision D-29-22; adversarial audit CONVERGED at round 8; three clarifications recorded in the spec, section "Chiarimenti"; amended after this plan by Trinity decision D-29-35, which answered Q-1 to Q-4, delta audit in `checklists/delta-audit-d29-35.md`)

**Input**: Feature specification from `specs/20261029-093933-agent-life-course/spec.md`

**Contract**: **contract unchanged**. No route, request parameter, response field, enum value, `error_code` or HTTP status changes; the life stage is not exposed by any serializer, route or HTML template (FR-014). `output_decision` keeps its shape: a sanitized decision is a normal `{"action": "rest", "reason": ...}` object, the shape of the existing fallback. The field sets of `AgentSerializer` and `DecisionLogSerializer` stay frozen by the test the prerequisite work item creates (couples T005, `simulation/tests/test_api_contract.py`), which this work item reuses for SC-009 (PD-14).

**Data model**: no field, no migration, no new era-template key.

**Prerequisites (both, before any code task)**: the Plan 4 branch `20260826-144432-demography-plan4-wiring` (which already carries the D-29-4 guard, merge `c1e8569`) and the rule-based couples branch `20261029-123404-rule-based-couples` (which creates `agents/deliberation.py::select_deliberating_agents`, its plan PD-12) are both merged into `develop`. T001 verifies it and stops otherwise. Every code reference below was read on 2026-10-29 on the Plan 4 head (`3c1e2c0`) and on the couples head (`8c43c9c`) through `git show <ref>:<path>`; `select_deliberating_agents` does not exist yet on the couples head (its task T062 is open), so its shape is taken from the couples plan PD-12 and re-verified by T003.

## Summary

The simulator gets one notion of life stage, derived on the fly from `birth_tick`, never stored. Three stages are wired: childhood [0, 10), adolescence [10, `migration.adulthood_age`), adulthood. The stage is computed by one pure function in `demography/orchestrator.py`, next to the canonical `age_in_years`, from an `AgeClock` that every caller builds once per tick (or per chat request) from an already-loaded `World`. The same module holds the SQL filter that expresses "at least an adolescent" on `birth_tick`, with the same integer edge `_fewest_ticks_to_reach` already used by the fertile window, so the SQL and the Python comparisons cannot disagree (FR-001b).

Four consumers read it. The deliberation selection of the prerequisite (`select_deliberating_agents`) replaces `minor_agent_ids` with that SQL filter, applied before the protagonist slice, so a child never takes a protagonist slot. The decision prompt states age and stage, drops `borrow`, `sell_property`, `buy_property` and `move_to` below adulthood, offers `pair_bond` only from the era's marriage age, and the parsed decision is sanitized before the `DecisionLog` is written. `compute_agent_output` returns zero for a child. The chat's shared opening, `describe_speaker`, gains the speech registers of FR-009 and FR-010, and both prompts stop calling an adult born in the run "a child" (FR-011).

## Technical Context

**Language/Version**: Python 3.12 (ruff `target-version = "py312"`).

**Primary Dependencies**: Django 5.x, DRF 3.15, Celery, Django Channels. No new dependency.

**Storage**: PostgreSQL. No migration.

**Testing**: pytest with pytest-django, `CaptureQueriesContext`, `django_assert_num_queries`, `connection.execute_wrapper` (SC-001), `caplog`, `unittest.mock.patch`. Command per task: `docker compose -f docker-compose.local.yml exec -T web pytest <path> -q`; when the container is not running, `DATABASE_URL=<a database this session owns> pytest <path> -q` from the repository root (parallel-session isolation: never the user's database, never a container this session did not start).

**Target Platform**: Linux containers (Docker Compose).

**Project Type**: Django web service with a Celery tick loop and a Channels chat.

**Performance Goals**: the age rule adds no query per agent anywhere. The selection issues a constant number of queries (SC-001); the Celery path adds at most one query per tick for the `World` (FR-003); the economy step adds none (FR-007); the chat adds at most two per message (FR-009).

**Constraints**: one age conversion for the thresholds (FR-001b); no second age predicate left in the decision loop or the chat (spec, "Relazione con la guardia del Plan 4"); dependencies point one way: `agents`, `economy`, `dashboard`, `chat` and `simulation` use `demography`, never the reverse.

**Scale/Scope**: the spec does not claim scale; with the prerequisite the decision step makes at most K = `max_protagonists` LLM calls per tick.

## Constitution Check

| Principle | Status for this plan |
|---|---|
| I. Scientific method | No formula is introduced. Every threshold carries its source or is declared a tunable heuristic, as the spec decides: 10 years (WHO; Sawyer et al. 2018); `adulthood_age` (Family Law Reform Act 1969 for the modern era, tunable heuristic elsewhere, discrepancy with Blackstone 1765 documented); speech bands up to 4 years (Zubler et al. 2022); the 4-10 band and the switch at 10 (heuristics); zero output under 10 (heuristic, Humphries 2010 as the reason it is one); minors move with the household (Rogers and Castro 1981). PD-12 adds one constant, the restrictive fallback of 18, derived from the shipped templates and pinned by a test. |
| II. Verify before asserting | Code facts read on the Plan 4 and couples heads (see Prerequisites). Two facts found while planning contradicted the spec (Q-1, Q-4); the Trinity decided them with Q-2 and Q-3 (D-29-35) and the spec is corrected. T003 repeats the symbol check on the realigned tree. |
| III. Adversarial audit | Spec audit CONVERGED (round 8). The code audit by `critical-analyzer` is the phase-6 gate (T055). |
| IV. Three-step design | Done in the spec ("Log del design"). This plan adds only implementation decisions, listed as PD-nn so that the Sonnet implementer invents nothing. |
| V. Evidence-based verification | Unit tests per task; the Celery end-to-end run (SC-002); the real-environment chat check (SC-006) reported as "verified in local environment" with the five answers attached. |

No violation needs a Complexity Tracking entry.

## Architectural placement and reuse

**1. Life stage and the shared age conversion.** Searched `demography/orchestrator.py` (`age_in_years`, `_years_elapsed`, `_fewest_ticks_to_reach`, `_most_ticks_within`, `_fertile_window_filter`, `_age_clock`, `current_age_clock`, `minor_agent_ids`, `describe_age`, `describe_speaker`), `demography/couple.py` (`meets_marriage_age`), `demography/context.py` (`household_keys`), `demography/inheritance.py` (its import of `_age_clock`). Found the canonical age, the integer edge search the fertile window inverts with, and the D-29-4 predicate; reuse all of them. Building new: the `LifeStage` enum, the `AgeClock` value, `life_stage`, `at_least_adolescent_filter` and `presented_role`.
They go in `demography/orchestrator.py`, beside `age_in_years` and in place of `minor_agent_ids`, because demography owns the canonical age and the era thresholds, and because the spec allows "where Plan 4 put its predicate, as long as it is one". A separate `demography/life_course.py` was considered and rejected: it would import the private edge search and template resolver from `orchestrator.py`, while `describe_speaker` in `orchestrator.py` would import the stage back from it, a cycle; moving `age_in_years` and the chat helpers out to break it would touch the audited §4.1.0 surface for no behaviour. `agents` was rejected because `economy` and the chat consume the stage too, and the dependency would then point from `economy` into `agents`. `agents`, `economy`, `simulation`, `dashboard` and `chat` USE `demography`, not the reverse.

**2. Deliberation selection.** Searched `agents/deliberation.py` (couples branch), `simulation/engine.py::SimulationEngine.run_tick`, `simulation/tasks.py::run_simulation_loop`. Found `select_deliberating_agents` (couples PD-12, created by couples T062): extend it, do not create a second one (D-29-22). It stays in `agents`, next to the decision loop.

**3. Vocabulary filter and sanitization.** Searched `agents/decision.py` (`_BASE_ACTIONS`, `_build_system_prompt`, `_DEMOGRAPHY_ACTION_DESCRIPTIONS`, `_FALLBACK_ACTION`, `process_agent_decision`), `simulation/engine.py::apply_agent_action`, `economy/property_market.py::process_property_listings`. Found the era filter pattern of `_build_system_prompt` and the fallback object; extend the filter with one stage-indexed table and reuse the fallback's shape for the sanitized decision. Both stay in `agents/decision.py`: they are rules of the decision layer and have no other caller.

**4. Child output.** Searched `economy/production.py::compute_agent_output` and the production loop of `economy/engine.py::process_economy_tick_new`. Found the pure output function the spec names (FR-007); extend it with the stage. The `World` read of step 8c is moved before the zone loop and reused.

**5. Chat fragment.** Searched `dashboard/views.py` (`_build_chat_system_prompt`, the group chat block that calls `current_age_clock` once per request), `chat/consumers.py::_generate_response`. Found `describe_speaker` already shared by the three chat prompts (private dashboard chat, group dashboard chat, WebSocket consumer); extend it, so that one function produces the fragment (FR-009). No second fragment is written.

**6. World access for the tick paths.** Searched `orchestrator._world_of` (one query on every call), `orchestrator._tick_duration_hours`, `economy/engine.py` step 8c (`simulation.world`), `agents/tasks.py::process_agent_turn` (`World.objects.get`). The one-to-one accessor `simulation.world` is cached on the instance after the economy step; one helper, `loaded_world`, reads it with the `World.DoesNotExist` fallback for the two callers that need it (Celery loop and economy step), instead of two copies of the same `try` (PD-08).

## Implementation decisions fixed by the plan

- **PD-01 Stage values.** `class LifeStage(StrEnum)` in `orchestrator.py` with exactly three members: `CHILDHOOD = "childhood"`, `ADOLESCENCE = "adolescence"`, `ADULTHOOD = "adulthood"`. Old age is not a member: no rule distinguishes it (spec, design log K8, and "a stage exists in the code only if a rule distinguishes it"); the whitepaper documents it as defined and not wired.
- **PD-02 Constants.** `CHILDHOOD_END_YEARS = 10` (docstring: WHO, *Adolescent health and development*, URL of the spec, read 2026-10-29; Sawyer et al. 2018, Lancet Child & Adolescent Health 2(3):223-228; a statistical health band, not a measure of decision capacity). `NEWBORN_ROLE = "child"`, used by `build_newborn` (which today writes the literal) and by `presented_role`, so the placeholder has one spelling. `FALLBACK_ADULTHOOD_AGE = 18`, see PD-12.
- **PD-03 The clock.** `@dataclass(frozen=True) class AgeClock` with `tick: int`, `tick_duration_hours: float`, `acceleration: float`, `template_name: str`, `template: dict | None`, `adulthood_age: float`, `adolescence_elapsed: int`, `adulthood_elapsed: int`. Built only by `age_clock_for(simulation, tick, tick_duration_hours) -> AgeClock`: `template_name = template_name_of(simulation)`, a helper extracted from the first lines of `_load_simulation_template` (`config.get("demography_template", "pre_industrial_christian")`), which then calls it too, so the new code adds no spelling of the default name (eleven other `config.get("demography_template", "pre_industrial_christian")` sites in demography, `simulation/engine.py` and `agents/decision.py` predate this work item and stay out of scope, except `decision.py`, whose site T022 deletes); `template = _load_simulation_template(simulation, tick)` (file cache, no query; no `is_demography_enabled` check, because the rule applies without demography, SC-007); `acceleration = acceleration_of(template)`; `adulthood_age = template["migration"]["adulthood_age"]` or `FALLBACK_ADULTHOOD_AGE` when `template is None`; `adolescence_elapsed = _fewest_ticks_to_reach(CHILDHOOD_END_YEARS, ...)` and `adulthood_elapsed = _fewest_ticks_to_reach(adulthood_age, ...)`, after the positivity check of PD-04. `current_age_clock(simulation)` returns `age_clock_for(simulation, simulation.current_tick, _tick_duration_hours(simulation))` (its one world read, as today) instead of the 3-tuple; `current_age_in_years(agent, clock)` and `describe_age` read the clock's attributes. Carrying the template inside the clock means a deliberating agent resolves the template once, not twice, so the loader logs a broken template once per deliberating agent, plus once per tick from the selection clock and once from the demography block when it is enabled, as the spec states; the decision prompt adds its own warning on the consequence (PD-10).
- **PD-04 Clock domain.** `years_per_tick` rejects `dt > 1` because mortality needs it; the stage does not, and it now runs for every simulation, including those without demography, whose ticks may be longer than a year. The positivity check (`not dt > 0`, NaN included) is extracted into `_require_positive_years_per_tick(tick_duration_hours, acceleration) -> float`, which raises the existing `NonPositiveTickError`; `years_per_tick` calls it and then applies its own `dt > 1` check, so the message and type of today are unchanged. `age_clock_for` calls only the positivity check. A non-positive clock is a configuration error and stays loud (it would make the edge search loop); no fallback.
- **PD-05 Clock parts.** `tick_duration_hours_of(world) -> float` is the body of today's `_tick_duration_hours` (`float(getattr(world, "tick_duration_hours", 24.0) or 24.0) if world else 24.0`), and `_tick_duration_hours(simulation)` becomes `tick_duration_hours_of(_world_of(simulation))`. `acceleration_of(template) -> float` is the first line of today's `_age_clock`, which becomes `return _tick_duration_hours(simulation), acceleration_of(template)` with its signature unchanged, so `inheritance.py` (audited, §4.1.4) is not touched. Per-agent callers never call `_age_clock`: they receive an `AgeClock` built from a loaded `World` (FR-001).
- **PD-06 The comparisons (FR-001b).** `life_stage(agent, clock) -> LifeStage`: with `birth_tick` set, `elapsed = clock.tick - agent.birth_tick`, childhood when `elapsed < clock.adolescence_elapsed`, adolescence when `elapsed < clock.adulthood_elapsed`, otherwise adulthood; with `birth_tick` NULL the same three-way choice on the integer column, `agent.age < CHILDHOOD_END_YEARS` and `agent.age < clock.adulthood_age`. `at_least_adolescent_filter(clock) -> Q` returns `Q(birth_tick__lte=clock.tick - clock.adolescence_elapsed) | Q(birth_tick__isnull=True, age__gte=CHILDHOOD_END_YEARS)`, with integer bounds computed in Python (the reason `_fertile_window_filter` documents: a float bound on an integer column is truncated toward zero). The two functions sit next to each other and their docstrings name each other. Because `_fewest_ticks_to_reach` admits on `_years_elapsed`, the arithmetic of `age_in_years`, "elapsed ≥ edge" is equivalent to `age_in_years ≥ threshold` on the realigned code; the single comparison is kept anyway because FR-001b requires it and it removes the reliance on that equivalence.
- **PD-07 Role placeholder (FR-011).** `presented_role(agent, stage) -> str | None` returns `None` when `agent.role == NEWBORN_ROLE` and `stage is not LifeStage.CHILDHOOD`, otherwise `agent.role`. `describe_speaker` writes `"You are {name}, a {role}, {age} old. "` or `"You are {name}, {age} old. "`; `decision._build_context` writes `"- {name} ({role})"` or `"- {name}"` for the living-agent list and the same rule for the faction member list. Both `.only("name", "role")` querysets of `process_agent_decision` become `.only("name", "role", "birth_tick", "age")`.
- **PD-08 Loaded world.** `loaded_world(simulation) -> World | None` in `orchestrator.py`, beside `_world_of`: `return simulation.world`, `None` on `World.DoesNotExist`. Docstring: unlike `_world_of`, it reads the one-to-one accessor, cached on the instance, so a caller after the economy step pays no query. Callers: `run_simulation_loop` and `process_economy_tick_new`. `_world_of` is not changed (its query counts are pinned by the Plan 4 cost tests).
- **PD-09 Selection.** `select_deliberating_agents(simulation, tick, world) -> list[Agent]`: `clock = age_clock_for(simulation, tick, tick_duration_hours_of(world))`, then the couples queryset with `.filter(at_least_adolescent_filter(clock))` in place of `.exclude(id__in=minor_agent_ids(...))`, BEFORE the priority annotation, the `("priority", "id")` ordering and the `[:K]` slice, so a child never consumes a protagonist slot. `K = 0` still returns `[]` before any query. `SimulationEngine.run_tick` passes the `world` it already holds; `run_simulation_loop` passes `loaded_world(simulation)`, read after the demography block. `minor_agent_ids` is deleted with its import sites; its docstring's guarantee moves to `select_deliberating_agents`.
- **PD-10 Decision prompt (FR-005).** `_BASE_ACTIONS` becomes a tuple of names (same order), joined with `|` where the prompt is written. A table `_ACTIONS_FORBIDDEN_BY_STAGE: dict[LifeStage, frozenset[str]]` maps `CHILDHOOD` and `ADOLESCENCE` to `frozenset({"borrow", "sell_property", "buy_property", "move_to"})` and `ADULTHOOD` to `frozenset()`; the comment cites contractual capacity and Rogers and Castro (1981) with `coordinate_family_migration` for `move_to`. `_build_system_prompt(agent, clock)` drops the forbidden names from the base vocabulary; the demography actions use `clock.template` instead of loading the template a second time; `pair_bond` is offered only when `clock.template is not None and meets_marriage_age(agent, clock.template, clock.tick, clock.tick_duration_hours)`. With `clock.template is None` no demography action is offered and `logger.warning("Demography actions withheld from the decision prompt of agent %s at tick %d: template %r could not be loaded", agent.id, clock.tick, clock.template_name)` is logged once per prompt (spec FR-005, D-29-35; today a missing file kept all three silently and an invalid one dropped them with `logger.exception`). The loader's own warning states the cause, this one the consequence; both name the template. The old `FileNotFoundError` and `ValueError` branches of `_build_system_prompt` are deleted. `_build_context` opens with `"You are {name}[, a {role}], {describe_age(agent, clock)} old, {stage.value}."`, with no behavioural adjective. `process_agent_decision(agent, world_state, tick)` keeps its signature and builds `clock = age_clock_for(agent.simulation, tick, tick_duration_hours_of(world_state))`: `agent.simulation` is already loaded by the code that precedes it, so no query is added.
- **PD-11 Sanitization (FR-006).** `_sanitize_for_stage(action: dict, stage: LifeStage, agent, tick) -> dict` in `decision.py`, called in `process_agent_decision` after the JSON parse and the non-object fallback (couples commit `acc6b2a`) and before `DecisionLog.objects.create`. The action name is read as `str(action.get("action", "")).strip().lower()`; when it is in `_ACTIONS_FORBIDDEN_BY_STAGE[stage]` the whole dict is replaced by `{"action": "rest", "reason": REFUSED_FOR_AGE_REASON}` with `REFUSED_FOR_AGE_REASON = "not permitted at this age"` (it contains no action name and no `hoard`, so no substring reader can match it), and `logger.warning("Decision %r of agent %s refused at tick %d: not permitted at life stage %s", ...)` records agent id, action, tick and stage. The returned (sanitized) dict is what `apply_agent_action` receives, so `borrow`, `sell_property` and `move_to`, which act at once, are covered on both paths too. `pair_bond` below the marriage age is not sanitized: it is not a stage rule, and `resolve_pair_bond_intents` already refuses it through `meets_marriage_age`.
- **PD-12 Restrictive fallback.** `FALLBACK_ADULTHOOD_AGE = 18`, the maximum `migration.adulthood_age` over the five shipped templates (16, 16, 16, 18, 18); a test computes that maximum from `demography/templates/*.json` and compares it with the constant, so a template change cannot silently leave the fallback below a shipped value.
- **PD-13 Child output (FR-007).** `compute_agent_output(..., life_stage: LifeStage = LifeStage.ADULTHOOD)`: after the good is chosen as today, `CHILDHOOD` returns `(good_code, 0.0)`; the docstring states the tunable heuristic, Humphries (2010) as the reason it is one, and the "era labour keys" work item. The child therefore takes the existing path of an agent whose output is 0 (`if quantity > 0` skips inventory and ledger; `agent_outputs` keeps one row with quantity 0), so no downstream branch is added. The default keeps the pure tests of the function valid; the engine always passes the stage.
- **PD-14 Economy clock.** In `process_economy_tick_new`, before the zone loop: `world = loaded_world(simulation)`; `if world is None or not world.tick_duration_hours: logger.warning(...)`; `clock = age_clock_for(simulation, tick, tick_duration_hours_of(world))`, once per tick. In the loop, `life_stage=life_stage(agent, clock)` is passed to `compute_agent_output`. Step 8c uses the same `world`, wrapped in `if world is not None:`; the blind `except Exception: pass` around the stability update stays (spec deferral 10).
- **PD-15 Chat registers (FR-009, FR-010).** `describe_speaker(agent, clock=None)` appends `_speech_register(agent, clock)` to the identity line. `stage = life_stage(agent, clock)`; when it is not `CHILDHOOD`, the register is today's sentence `"Speak and react as a person of that age would. "`, and the displayed years are `max(int(years), CHILDHOOD_END_YEARS)` for an adolescent (FR-009, symmetric case). In childhood the band is chosen on `years = current_age_in_years(agent, clock)` with named constants `_PREVERBAL_BELOW_MONTHS = 12`, `_SINGLE_WORDS_BELOW_MONTHS = 24`, `_FEW_WORDS_BELOW_YEARS = 4` (docstring: Zubler et al. 2022, Pediatrics 149(3) e2021052138, milestones at the 75th percentile, read on the CDC manuscript; bands are prudent, not medians); the 4-10 band and the switch at 10 are declared heuristics. The texts, our own words (FR-015), are fixed here so that phase 5 does not invent them:
  - below 12 months: `"You cannot speak yet. Answer only with sounds, babbling and non-verbal reactions, for example crying, smiling, reaching out or turning away, and use no words of any language. This instruction overrides every other rule of this prompt about the number of sentences and about describing actions or gestures. "`
  - 12 to 24 months: `"You speak only in single words, a few at a time, together with sounds and gestures. This instruction overrides every other rule of this prompt about the number of sentences and about describing actions or gestures. "`
  - 2 to 4 years: `"You speak in short combinations of a few words, growing towards sentences of four words. This instruction overrides every other rule of this prompt about the number of sentences and about describing actions or gestures. "`
  - 4 to 10 years: `"Speak with the simple words and short sentences of a child of that age. "`
  The override sentence is self-contained and names no specific rule (FR-010); it appears below 4 years only. The three chat prompts (private dashboard chat `_build_chat_system_prompt`, group dashboard chat `group_chat_view` for both the addressed agent and the 80-token listener, WebSocket `ChatConsumer._generate_response`) already call `describe_speaker`, so no caller changes except the clock type; the group chat is in scope by D-29-35.
- **PD-16 Contract test reuse (SC-009).** The couples task T005 freezes `sorted(AgentSerializer().fields)` and `sorted(DecisionLogSerializer().fields)` before any change. This work item adds no test of its own: T004 verifies the test exists on the realigned tree and still passes, and a mutation proof (a dummy field) is run once. If T003 finds it absent, the test is created here with the same name and content, before any code task.
- **PD-17 Query-count baselines.** SC-001 part 2 and SC-003 compare with "before the change". Each baseline is pinned by a test written and seen green on the unmodified code (T006, T007), then kept green through the change: the pin is the evidence, never a number remembered from a run.
- **PD-18 Guard tests adapted, not duplicated.** `demography/tests/test_minor_agent_ids.py` loses the tests of `minor_agent_ids` with the function; its two `current_age_in_years` tests move to the new `demography/tests/test_life_stage.py`. `simulation/tests/test_engine.py::test_a_minor_gets_no_decision` and `test_without_demography_the_child_still_decides`, and `simulation/tests/test_engine_demography_wiring.py::test_a_minor_is_not_asked_to_decide_an_adult_still_is` and `test_a_population_of_minors_only_finalizes_the_tick_directly`, are rewritten on the 10-year threshold; each rewrite says in its commit which assertion changed and why (the 10-year-old now deliberates; without demography the 3-year-old no longer does). `demography/tests/test_decision_actions.py::test_prompt_filter_keeps_pair_bond_always` is rewritten as "kept for an agent of marriage age in every template".
- **PD-19 Doc-sync commit groups.** As couples PD-19: the doc-sync rule requires the whitepaper chapter in the same commit as the code, so a group `G<n>` of atomic tasks, flagged one at a time, shares one commit made at its last task.
- **PD-20 Realignment.** The branch is pushed and force-push is forbidden: T001 is `git merge --no-ff origin/develop`, never a rebase.

## Module and file changes

| File | Change | FR / SC |
|---|---|---|
| `epocha/apps/demography/orchestrator.py` | NEW `LifeStage`, `CHILDHOOD_END_YEARS`, `NEWBORN_ROLE`, `FALLBACK_ADULTHOOD_AGE`, `AgeClock`, `age_clock_for`, `template_name_of`, `_require_positive_years_per_tick`, `tick_duration_hours_of`, `acceleration_of`, `loaded_world`, `life_stage`, `at_least_adolescent_filter`, `presented_role`, `_speech_register`; CHANGED `years_per_tick`, `_tick_duration_hours`, `_age_clock`, `_load_simulation_template` (bodies only), `current_age_clock`, `current_age_in_years`, `describe_age`, `describe_speaker`, `build_newborn` (constant); DELETED `minor_agent_ids` | FR-001, FR-001a, FR-001b, FR-009 to FR-011, FR-016; SC-005, SC-010 |
| `epocha/apps/demography/migration.py` | docstring of `coordinate_family_migration` only: the "MINORS ARE NOT CALLED TO THE DECISION LOOP" header and the sentence giving the orchestrator the `move_to` duty | FR-016 |
| `epocha/apps/agents/deliberation.py` | `select_deliberating_agents(simulation, tick, world)` with the SQL age filter | FR-002, FR-003; SC-001, SC-002, SC-007, SC-010 |
| `epocha/apps/agents/decision.py` | `_BASE_ACTIONS` tuple, `_ACTIONS_FORBIDDEN_BY_STAGE`, `REFUSED_FOR_AGE_REASON`, `_build_system_prompt(agent, clock)`, `_build_context` opening and lists, `_sanitize_for_stage`, `process_agent_decision` | FR-005, FR-006, FR-011; SC-004 |
| `epocha/apps/economy/production.py` | `compute_agent_output(..., life_stage=...)` | FR-007; SC-003 |
| `epocha/apps/economy/engine.py` | world and clock before the zone loop; stage passed to production; step 8c on the loaded world | FR-007; SC-003 |
| `epocha/apps/simulation/engine.py` | `select_deliberating_agents(self.simulation, tick, world)`; drop the `minor_agent_ids` import | FR-002, FR-003 |
| `epocha/apps/simulation/tasks.py` | `loaded_world` after the demography block; selection with the world; comment on minors moved to the selection docstring | FR-002, FR-003 |
| `epocha/apps/dashboard/views.py` | no code change beyond the clock type; the private and the group chat prompts gain the registers through `describe_speaker`, and the group chat keeps `current_age_clock` once per request (new return type) | FR-009 |
| `epocha/apps/chat/consumers.py` | none (already calls `describe_speaker`) | FR-009 |
| tests | NEW `demography/tests/test_life_stage.py`, `agents/tests/test_life_course_decision.py`, `simulation/tests/test_life_course_integration.py`; CHANGED `demography/tests/test_minor_agent_ids.py` (deleted after the move), `demography/tests/test_decision_actions.py`, `agents/tests/test_deliberation.py`, `agents/tests/test_decision.py`, `economy/tests/test_engine.py`, `dashboard/tests/test_chat_prompt.py`, `simulation/tests/test_engine.py`, `simulation/tests/test_engine_demography_wiring.py`, `simulation/tests/test_tasks.py` | all SC |
| `docs/whitepaper/epocha-whitepaper.md` and `.it.md` | §3.1, §3.2, §3.3, §3.6, §3.8, §4.1.0, §4.1.5 (statement that it stays true, in the commit), §4.8, new §8.2, §11, §13 | FR-013, FR-016 |
| `README.md`, `README.it.md` | reread; updated only where a statement becomes false | FR-013 |
| `docs/build-map/epocha-build-map.html` | [COORD] by the session that owns the map | FR-013 |

## Pipeline ordering and integration surface

```text
run_simulation_loop (Celery)                      SimulationEngine.run_tick (sequential)
  economy step                                      economy step
    world = loaded_world(simulation)                  (same, inside process_economy_tick_new)
    clock = age_clock_for(...)       once per tick
    compute_agent_output(..., life_stage)  child -> 0
  run_demography_tick (births at T)                 (no demography on this path)
  world = loaded_world(simulation)   <=1 query
  select_deliberating_agents(sim, tick, world)      select_deliberating_agents(sim, tick, world)
    age_clock_for -> at_least_adolescent_filter       same
    priority order, [:K]             O(1) queries
  chord(process_agent_turn ...)                     for agent: process_agent_decision
    process_agent_decision(agent, world, tick)
      clock = age_clock_for(agent.simulation, tick, tick_duration_hours_of(world))
      prompt: age, stage, filtered vocabulary, pair_bond by meets_marriage_age
      LLM -> parse -> non-object fallback -> _sanitize_for_stage -> DecisionLog
    apply_agent_action(sanitized action)
chat (three prompts) -> describe_speaker(agent, clock) -> identity + register
```

Integration surfaces left unchanged: `household_keys` (`context.py`, float age) and `inheritance.py` (column `age`) keep their own `adulthood_age` comparisons, out of scope by FR-001b; `run_fertility_step` and its fertile-candidate filter are not touched (the marital-fertility work item asks, its T003); `resolve_pair_bond_intents` keeps its own marriage-age check; `world/election.py` still counts every living agent (spec deferral 7).

## Doc-sync obligations

The chapter changes go in the commit of the code they describe (PD-19). Whitepaper, both languages, with the Italian mirror following the normative English:

- **§3.1** (tick engine) and **§3.2** (decision pipeline, today "Each living agent goes through a four-stage pipeline"): the deliberating agents are chosen by `select_deliberating_agents`, children under 10 excluded in SQL before the protagonist slice; the prompt states age and stage; the vocabulary is filtered below adulthood; the decision is sanitized before the `DecisionLog`; the restrictive fallback with a broken template.
- **§3.3** (integration contracts): one row for `life_stage(agent, clock)` and `age_clock_for(...)` in `demography/orchestrator.py`, called by `agents`, `economy` and the chat.
- **§3.6** and **§4.8**: zero output under 10 as a tunable heuristic (FR-007); the legacy economy still pays children (FR-007a).
- **§3.8**: the chat's age fragment and its registers, one function for the three prompts.
- **§4.1.0**: the paragraph that today names `minor_agent_ids` (English line 693 on the Plan 4 head) is rewritten for the new predicate and threshold; the extension of the clock helpers; `NEWBORN_ROLE`.
- **§4.1.5**: no text change; the commit of FR-016 states that it stays true (no minor receives a `DecisionLog` for a move it did not choose, now guaranteed by FR-005 and FR-006).
- **New §8.2 "Life course"** (designed subsystem, audit pending): stages, thresholds, their sources and heuristics, the era table of `adulthood_age` with the Blackstone discrepancy, the speech bands, the cost per tick, the known limitations of the spec.
- **§11** (Known Limitations): the spec's Known Limitations that are not already there.
- **§13**: new entries for WHO (adolescent health), Sawyer et al. (2018), Zubler et al. (2022), Rogers and Castro (1981), Family Law Reform Act 1969, United Nations (1998), Humphries (2010), Elder (1998) if cited; Blackstone already has an entry (1765-1769). Every body citation has an entry and every entry is cited (constitution, bibliography rigor).
- **§9 roadmap**: the item "Behaviour by age across the life course" is added by the marital-fertility work item (its T039, branch `20261029-185654-marital-fertility`). This work item does not add it; when it lands it moves that item from §9 to §8.2 (T051 checks which state the realigned tree is in).

The doc-sync table in `CLAUDE.md` and its three copies needs no row: every touched module is already mapped (`orchestrator.py` to §4.1.0, `migration.py` to §4.1, `production.py` and `engine.py` of economy to §4.8), and `agents/decision.py`, `agents/deliberation.py` are not in §4. README check: both READMEs are reread; the tree line "agents/ Personality, memory, decision pipeline, ..." stays true. The build map records the plan, each checkpoint and the closure [COORD].

## Gates

- Per task: red test first where behaviour changes, touched-area tests, 8-point review.
- Per phase of `tasks.md`: module suite.
- Before phase 6: the mechanical taste gate on changed files (functions over 40 lines, nesting over 3, `ruff check --select C901,PLR0912,PLR0915,PLR1702` on the changed files), full suite, `ruff check .` and `ruff format --check .`. `process_agent_decision` is already far above 40 lines on the Plan 4 head; this work item adds two lines to it and must not grow it further: the stage logic lives in the helpers, and the review states the pre-existing length as a finding to defer (R1 below).
- Phase 6 (heavy gate): `critical-analyzer` on the code, Matteo-mode review of the branch diff with the thresholds, the 8/10 quality score, SC-006 in the local environment, explicit validation of closure.

## Coordination with the other open work items

- **Rule-based couples** (prerequisite): owns `select_deliberating_agents`, `max_protagonists` and `test_api_contract.py`. This work item changes the selection's signature (adds `world`); couples tests that call it with two arguments are updated in the same commit (T030).
- **Marital fertility** (`20261029-185654-marital-fertility`): its T003 asks whether this work item changed the fertile-candidate filter; it does not. Its T039 adds the §9 roadmap item this work item later moves to §8.2.
- **Build map** [COORD]: open this work item's phase 3-4 checkpoint, the two separate work items of D-29-5 if not yet opened, and the deferrals 7-10 of the spec.

## Pre-existing defects found while planning (out of scope)

None goes into the code of this work item; each is to be opened on the build map by the coordinating session.

- **R1 Long functions on the decision path.** `process_agent_decision` and `_build_system_prompt` exceed 40 lines and contain five blind `except Exception: pass` blocks (political, reputation, economic, zone context). Untouched here beyond the lines the spec requires.
- **R2 Two `DecisionLog` writers.** `apply_agent_action` writes `DecisionLog` rows for the intent actions (`demography/tests/test_decision_actions.py`, "creates a DecisionLog entry"), besides `process_agent_decision`. The sanitized action reaches both, so FR-006 holds; whether a decision should be logged twice is a question for the agents owners.
- **R3 `_world_of` queries on every call** where `simulation.world` would be cached; changing it would move Plan 4's pinned query counts.

## Questions answered by the Trinity (D-29-35, provisional)

The four questions found while planning were decided by the Trinity on 2026-10-29 (decision D-29-35, provisional until the user returns) and written into the spec (section "Chiarimenti", D-29-35).

- **Q-1 SC-010, second test.** The spec's premise was false on the Plan 4 head: since round 15 of the Plan 4 phase-6 gate, `_years_elapsed` is `elapsed * hours * acceleration / 8760` and `3285 * 168 * 1.0 / 8760` is exactly `63.0`; `_fewest_ticks_to_reach(63, 168, 1.0)` is `3285`. The old two-division form `3285 / (8760 / 168) * 1.0` gives `62.99999999999999` and moves the edge to `3286` (recomputed 2026-10-29 in a scratch script replicating both forms). The spec now asserts the current literals (`63.0` by equality, `3285`) and names the mutation that must turn the test red: `_years_elapsed` back to the two-division form. Asserting only agreement would not catch it, because under the mutation age and edge move together. T020 is unparked.
- **Q-2 Demography actions with an unresolvable template.** PD-10 kept: no demography action, plus a WARNING per prompt naming the template (`AgeClock.template_name`). Tested red-first in T022, before the code that implements it.
- **Q-3 Group chat.** In scope. SC-005 covers the three chat prompts, the group chat for both the addressed agent and the listener (T044, T045).
- **Q-4 Stale sentence.** Corrected in the spec: `chat/consumers.py` already calls `describe_speaker` (Plan 4 commit `430dfa6`) and the D-29-4 guard is merged into the Plan 4 branch (`c1e8569`). No task redoes it; T044 only checks the fragment there.

## Project Structure

### Documentation (this feature)

```text
specs/20261029-093933-agent-life-course/
├── spec.md
├── checklists/requirements.md
├── plan.md                    this file
└── tasks.md
```

`research.md`, `data-model.md`, `quickstart.md` and `contracts/` are not created: the research is the spec's source tables and design log, there is no data model change, and there is no contract change (stated at the top and frozen by the reused test, PD-16). Four files repeating the spec would be four places to drift.

### Source code (repository root)

```text
epocha/apps/demography/
├── orchestrator.py            life stage, clock, filter, registers
├── migration.py               docstring of coordinate_family_migration
└── tests/test_life_stage.py   NEW
epocha/apps/agents/
├── deliberation.py            SQL age filter in the selection
├── decision.py                vocabulary, sanitization, role and age lines
└── tests/test_life_course_decision.py NEW
epocha/apps/economy/
├── production.py              child output
└── engine.py                  world and clock before the zone loop
epocha/apps/simulation/
├── engine.py, tasks.py        selection with the world
└── tests/test_life_course_integration.py NEW
```

**Structure Decision**: the existing Django app layout; no new app and no new module outside the tests.

## Complexity Tracking

No constitution violation to justify.

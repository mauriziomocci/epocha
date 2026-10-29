# Implementation Plan: marital fertility schedule for the eras that require a couple

**Branch**: `20261029-185654-marital-fertility` | **Date**: 2026-10-29 | **Spec**: [spec.md](spec.md) (phase 2 approved provisionally by the Trinity, decision D-29-31; audit CONVERGED at round 5, delta round 6 CONVERGED, log in [checklists/audit.md](checklists/audit.md))

**Input**: Feature specification from `specs/20261029-185654-marital-fertility/spec.md`

**Contract**: **contract unchanged.** No route, response field, enum value, error code or HTTP status changes. The work item touches `demography/fertility.py`, one statement of `demography/orchestrator.py`, `demography/template_loader.py` and the five era templates; none is exposed by an API (`Simulation.config` carries only the template **name**).

**Data model**: no database field and no migration. The `fertility` section of the era templates changes (FR-003, FR-004): three templates replace `hadwiger` with `marital`, all five lose `require_couple_for_birth` (D-MF-03).

**Prerequisite (D-MF-06)**: phase 5 starts only after the rule-based couples branch (`20261029-123404-rule-based-couples`) is merged into `develop`, which itself waits for the user's merge of Plan 4 (PR #18, branch `20260826-144432-demography-plan4-wiring`). Verified on 2026-10-29: this branch's base is `develop` at `2223968`; neither the Plan 4 head `3677f7f` nor the couples head `8c43c9c` is an ancestor of `develop`, and the couples branch does not contain Plan 4. Every code reference in this plan was read on the Plan 4 head `3677f7f` and on the couples head `8c43c9c`; T003 re-verifies all of them on the merged tree, because both branches still move.

## Summary

In the three eras that require a couple for birth, the base fertility schedule becomes the marital schedule of Coale and Trussell (1974) with m = 0, that is Henry's (1961) natural fertility scaled by a level M (N1), with M = T_m / 8.995 read from the published total marital fertility rate 20-49 that the template now carries (N1a). The total fertility rate stops being a template parameter in those eras and becomes a product of nuptiality (from the couples work item) and marital fertility (N2, N3). Becker modulation and the Malthusian ceiling multiply the new base schedule exactly as they multiply Hadwiger today (N4). The couple rule is no longer a flag: it is the presence of the `marital` block, read through one public predicate, and the loader admits exactly one of `marital` and `hadwiger`. The two eras without the couple rule keep equation (4.2) unchanged.

## Technical Context

**Language/Version**: Python 3.12 (ruff `target-version = "py312"`).

**Primary Dependencies**: Django 5.x, Celery; `scipy` already a project dependency (used by `nuptiality.py`; this work item uses `scipy.integrate.quad` only in tests and scripts). Standard library `bisect` for the group lookup. No new dependency.

**Storage**: PostgreSQL. No migration. Templates are JSON files under `epocha/apps/demography/templates/`.

**Testing**: pytest with pytest-django, `CaptureQueriesContext`. Command per task: `docker compose -f docker-compose.local.yml exec -T web pytest <path> -q`; when the container is not running, `DATABASE_URL=<a database this session owns> pytest <path> -q` from the repository root, never against the user's database. The implementer never starts, stops or recreates a container.

**Target Platform**: Linux containers (Docker Compose).

**Project Type**: Django web service with a Celery tick loop.

**Performance Goals**: the fertility step's query count unchanged (SC-004): r(a) is a lookup in a six-element tuple in place of the evaluation of (4.2), zero queries, O(1) per candidate, O(N) per tick in the living population N, no LLM call.

**Constraints**: the cached template dict is never mutated (`load_template` shares one dict); determinism unchanged (same `fertility` RNG stream, same draw order); no per-candidate query added.

**Scale/Scope**: five templates, one pure function, one dispatcher, one predicate, one loader clause; two phase-6 scripts (one modified, one new).

## Constitution Check

| Principle | Status for this plan |
|---|---|
| I. Scientific method | Every formula (N1)-(N4) and every constant carries its source in the code comment, with the verification status the spec records (IUSSP page read, Coale-Trussell primary not read). The two heuristics (D-MF-04 extension to 15-19, the 12 upper bound of the loader) are named as tunable heuristics in code and whitepaper. PASS |
| II. Verify before asserting | T003 is the code-verification preflight on the merged tree; every symbol named below is re-read there, and any mismatch stops phase 5. The spec numbers that tests assert (8.995, 0.0061568, 4.283, 4.306, 2.363) were recomputed on 2026-10-29 for this plan with the couples `nuptiality.py` (`location` 25.580). PASS |
| III. Adversarial audit | Spec audit CONVERGED (rounds 5 and 6). The code audit is T053 (phase 6, `critical-analyzer` on the branch diff, convergence loop). PASS, pending phase 6 |
| IV. Three-step design | Done in the spec (Registro del design). The plan decisions below are implementation choices inside the approved design, each with its rejected alternative. PASS |
| V. Evidence-based verification | SC-005 and SC-006 are run in phase 6 and reported with the commit they ran on; confidence levels stated in the phase-6 report. PASS |

Global rules that bind the tasks: red test first; taste thresholds (functions about 40 lines, nesting at most 3, no catch-all `except`, typed errors, no dead code, no duplicated logic); English identifiers; every formula and constant cites its source in a comment; commits through `git-commit-assistant`, no AI reference, no `Co-Authored-By`; doc-sync in the same commit.

## Scientific formulas and their sources

| Eq. | Formula | Source (verification status) | Code |
|---|---|---|---|
| (N1) | r(a) = M · n(a), n(a) piecewise constant on five-year groups, n = 0.460 for 15 ≤ a < 25, 0.431, 0.395, 0.322, 0.167, 0.024 for the groups 25-29 to 45-49, 0 outside [15, 50) | Coale and Trussell (1974) with m = 0 (primary not read; form verified on Rodríguez 2017 and IUSSP PAPP103); n(a) values from IUSSP PAPP103, session 3, from Henry (1961); the 15-19 extension is the heuristic D-MF-04 | `fertility.HENRY_NATURAL_FERTILITY`, `fertility.marital_fertility_rate` |
| (N1a) | M = T_m / TMFR_Henry, TMFR_Henry = 5 · Σ n(a) over the six 20-49 groups = 8.995 | Definition of M in Coale and Trussell (1974) written in the published quantity; T_m = 6.7 from Alter, Newton and Oeppen (2020, sec. 3.1.3), provisional (cumulated 1575-1849) | `fertility.HENRY_TMFR_20_49` computed from the tuple, never written by hand |
| (N2) | f(a) = π(a) · r(a) | Coale and Trussell (1974) via Rodríguez (2017), "assuming no fertility outside marriage"; If = Ig·Im + Ih·(1 − Im) with Ih = 0, Woods (2000, eq. 1.1) | Not code: the orchestrator already passes only partnered mothers a positive rate |
| (N3) | TFR₀ = M · ∫ n(a) · F*(a) da | Composition of (N2) with (R4) of the couples spec | Tests (SC-002) and scripts (SC-005) only |
| (N4) | P_tick = c_MT(b(a) · m_BK, n, n_max, ρ) · Δt, b(a) = r(a) with the `marital` block, f_HW(a; H, R, T) otherwise | Whitepaper (4.3), (4.4), (4.5) unchanged, base schedule chosen by one discriminator | `fertility.annual_base_rate`, called by `tick_birth_probability` |

## Architectural placement and reuse

**Reuse statement.** Searched `demography/fertility.py` (`hadwiger_asfr`, `becker_modulation`, `malthusian_soft_ceiling`, `tick_birth_probability`, `_effective_age_in_years`), `demography/orchestrator.py` (`run_fertility_step`, `years_per_tick`, `age_in_years`), `demography/template_loader.py` (`SCHEMA`, `_Optional`, `_check_leaf`, `_interval_text`, `_fail`, `validate_template`), `demography/truncated_moments.py` (interval or bound helpers: none applicable, it computes admissible regions of moment pairs), `demography/nuptiality.py` on the couples branch (`first_marriage_schedule`, `FirstMarriageSchedule.tick_probability`, `conditional_cdf`) and the five templates. **Found and reused**: the whole composition of `tick_birth_probability` (couple gate, `avoid_conception`, Becker, ceiling, Δt); `years_per_tick`; the canonical age; the loader's `_Optional` wrapper, error helper `_fail`, path-naming messages and unknown-key rejection; `nuptiality.first_marriage_schedule` for the tests and scripts that compose F*. **Found nothing** for a marital schedule, a schedule dispatcher or a half-open interval: building `marital_fertility_rate`, `HENRY_NATURAL_FERTILITY`, `base_schedule_kind`, `requires_couple_for_birth`, `annual_base_rate`, `FertilityScheduleError` and the interval vocabulary change. **Deleted**: the `require_couple_for_birth` key from the schema and the templates, and its two `.get(..., True)` reads.

**Placement.** `marital_fertility_rate`, the Henry constant, the dispatcher, the predicate and the typed error go in `demography/fertility.py`, because that module is the single owner of the fertility schedules and their composition (Ghezzi: cohesion; one owner per concept); a `marital_fertility.py` would be a second owner of the same concept (D-MF-08). Alternatives rejected: a new module (second owner); putting the exactly-one-block rule in the loader only (the hand-built dicts of FR-002 would escape it, and the rule would exist twice). The loader USES `fertility.base_schedule_kind` for its seventh clause, not the reverse; `template_loader` importing a pure function of `fertility` adds no cycle (verified on the Plan 4 head: `fertility.py` imports only `math` and `Mapping` at module level, everything else lazily) and follows the precedent of the couples branch, where the loader calls `nuptiality`. `fertility.py` does not import `nuptiality.py` or `couple.py` at run time for this feature; only tests and scripts compose the two.

## Implementation decisions fixed by the plan

These choices are inside the approved design and not settled by the spec text; each is flagged so the phase-6 audit can attack it.

- **PD-01 Henry constant.** `HENRY_NATURAL_FERTILITY: tuple[tuple[float, float], ...] = ((20.0, 0.460), (25.0, 0.431), (30.0, 0.395), (35.0, 0.322), (40.0, 0.167), (45.0, 0.024))`, pairs (start age of the five-year group, n). `HENRY_TMFR_20_49 = FIVE_YEAR_GROUP_WIDTH * sum(n for _, n in HENRY_NATURAL_FERTILITY)` (= 8.995 in floating point 8.995000000000001). The 15-19 extension (D-MF-04) is a separate named constant, `MARITAL_SCHEDULE_MIN_AGE = 15.0`, and is implemented by clamping the lookup age to the first group start (`max(age, 20.0)`), not by a seventh tuple element, so the sum stays over 20-49 (spec R2-09). Upper bound `MARITAL_SCHEDULE_END_AGE = 50.0` (exclusive). Lookup with `bisect.bisect_right` on the group starts: no if-chain, no special case per group.
- **PD-02 One dispatch point.** `_BASE_SCHEDULES = {"marital": marital_fertility_rate, "hadwiger": hadwiger_asfr}`; `base_schedule_kind(fertility_cfg) -> str` returns the single key of `_BASE_SCHEDULES` present in the section and raises `FertilityScheduleError` when the count is not exactly one, with a message naming `fertility.marital` and `fertility.hadwiger` and the keys found; `requires_couple_for_birth(cfg)` is `base_schedule_kind(cfg) == "marital"`; `annual_base_rate(age, cfg)` is `_BASE_SCHEDULES[kind](age, cfg[kind])`. The exactly-one rule therefore exists once, in `fertility.py`, and the predicate and the dispatcher cannot disagree. Alternative rejected: an `if "marital" in cfg` in each function (two copies of the rule, and a section with both blocks would silently pick one).
- **PD-03 Typed error.** `class FertilityScheduleError(ValueError)`, in `fertility.py`. Subclassing `ValueError` keeps every existing caller that treats template defects as `ValueError` correct; callers decide by type, never by message.
- **PD-04 Loader seventh clause.** `validate_template` calls `fertility.base_schedule_kind(data["fertility"])` after `_walk`, inside `try/except FertilityScheduleError as exc: _fail(source, str(exc))`. The except is typed and re-raises through the loader's own error path (the message gains `Template <source>:` like every other clause); it swallows nothing. In `SCHEMA["fertility"]` both `marital` and `hadwiger` become `_Optional`, so `_walk` validates whichever is present and the seventh clause decides the count; `require_couple_for_birth` leaves the schema, so a template still carrying it fails as an unknown key (US3 scenario 2) through the existing clause 1.
- **PD-05 Interval vocabulary.** The leaf intervals become a `NamedTuple` `Interval(low, high, low_open)`: `UNIT = Interval(0.0, 1.0, low_open=False)`, `POSITIVE = Interval(0.0, None, low_open=True)`, and the new `MARITAL_LEVEL_RANGE = Interval(0.0, 12.0, low_open=True)`, the half-open (0, 12] of FR-003. One rule in `_check_leaf` (below `low` or at `low` when open, above `high` when bounded) replaces the two branches; `_interval_text` renders `[a, b]`, `(a, b]` and `greater than a`. The existing two message strings are kept byte-identical for `UNIT` and `POSITIVE` values (T003 lists the tests that match them). Alternative rejected: a third ad-hoc tuple shape or a separate class next to the tuples, which would add a special case instead of removing one. The 12 bound carries the comment of FR-003 (Woods 2000, p. 9, n. 19, citing Eaton and Mayer 1954; tunable heuristic against typos, probably a 15-49 value).
- **PD-06 Equation numbering in the whitepaper.** The spec asks for (N1)-(N4) "numbered in the chapter sequence" without fixing the scheme. Renumbering (4.6) onwards would move every later equation reference of both whitepapers and of the couples chapter. The plan numbers the new equations (4.2a) r(a), (4.2b) M, (4.2c) f = π·r, (4.2d) TFR₀, and rewrites (4.5) in place as (N4), keeping its number. **Flagged as a plan decision**; the phase-6 audit may reverse it.
- **PD-07 Commit groups (doc-sync).** The switch is indivisible: removing the key from the schema breaks the shipped templates, editing the templates without the predicate makes `modern_democracy` require a couple (today's default `True`) and makes `fertility_cfg["hadwiger"]` raise for the Christian era. Group **G3** therefore carries the loader, the five templates, the wiring in `fertility.py` and `orchestrator.py`, the test adaptations of FR-005 and every whitepaper and README change of FR-006 in one commit; its tasks are done and flagged one at a time and committed together at the last one. Groups G1 and G2 add pure functions not yet called by the tick loop and say so in their `CHANGE:` paragraph (doc-sync module touched, model unchanged). If a session must stop inside G3, it stops with nothing committed for G3, never a code commit without its chapter.
- **PD-08 SC-002 propagation lives in the test.** The deterministic monthly propagation is about ten lines of test code in `test_marital_fertility.py`. The couples script `scripts/measure_nuptiality_fertility.py` already computes its own reference propagation (couples T080). Putting one shared helper in a production module would make production code that only tests and scripts use; importing a test helper from a script is fragile. Kept as two copies, declared, re-examined by the phase-6 review (residual doubt 4 in `tasks.md`).
- **PD-09 SC-006 harness.** `scripts/measure_marital_schedule_run.py` is a pytest module whose name does not match `python_files = ["test_*.py"]`, so the default suite never collects it; it runs only when named on the command line (`pytest scripts/measure_marital_schedule_run.py -s`), where pytest collects an explicitly given path regardless of the pattern. It gets pytest-django's throwaway test database (the name `test_<DATABASE_URL name>`, so the session points `DATABASE_URL` at a name it owns) and never touches the user's database. It reuses the founder builder of the couples integration run (couples T069) instead of a copy (T003 decides whether that builder must first be lifted to a module-level function), patches the template directory with copies (Becker coefficients zero for A, seed for B, `max_population` = 10⁶ for both), and instruments the run by wrapping `fertility.tick_birth_probability` and `fertility.becker_modulation` with `unittest.mock.patch(..., wraps=...)`, so the exposure (woman-years in a couple per group) and the Becker factor are the ones the model actually used; no production code is added for measurement. The orchestrator imports `tick_birth_probability` inside `run_fertility_step` from the module at call time (Plan 4 head, `orchestrator.py` around line 333), so the module-attribute patch is seen; T003 re-verifies.
- **PD-10 Feature pin.** `.specify/feature.json` on `develop` pins `specs/20260812-143706-bilingual-build-map`, which makes `.specify/scripts/bash/setup-plan.sh` resolve the wrong feature (observed on 2026-10-29: it overwrote that work item's `plan.md`, reverted at once). This branch sets the pin to its own directory; T001 keeps this branch's value on conflict, as the couples branch does for its own.

## Module and file changes

| File | Change | FR |
|---|---|---|
| `epocha/apps/demography/fertility.py` | Add `HENRY_NATURAL_FERTILITY`, `FIVE_YEAR_GROUP_WIDTH`, `HENRY_TMFR_20_49`, `MARITAL_SCHEDULE_MIN_AGE`, `MARITAL_SCHEDULE_END_AGE`, `marital_fertility_rate`, `FertilityScheduleError`, `_BASE_SCHEDULES`, `base_schedule_kind`, `requires_couple_for_birth`, `annual_base_rate`; `tick_birth_probability` uses the predicate and `annual_base_rate`; module and function docstrings cite (N1)-(N4) | FR-001, FR-002 |
| `epocha/apps/demography/orchestrator.py` | `run_fertility_step`: the warning's condition becomes `requires_couple_for_birth(context.template["fertility"])` (one statement) | FR-002 |
| `epocha/apps/demography/template_loader.py` | `Interval` vocabulary; `marital` and `hadwiger` `_Optional`; key removed; seventh clause; module and `validate_template` docstrings count seven clauses, the seventh attributed to this spec, not to A9; the Hadwiger-calibration sentence corrected | FR-003 |
| `epocha/apps/demography/templates/{pre_industrial_christian,pre_industrial_islamic,industrial}.json` | `hadwiger` and `require_couple_for_birth` removed; `marital: {total_marital_fertility_20_49: 6.7 / 6.7 / 6.22}` | FR-004 |
| `epocha/apps/demography/templates/{modern_democracy,sci_fi}.json` | `require_couple_for_birth` removed | FR-004 |
| `epocha/apps/demography/tests/test_marital_fertility.py` | New: SC-001, SC-002, SC-003, US1 scenario 1, US3 scenario 4 | SC-001 to SC-003, SC-007 |
| `epocha/apps/demography/tests/test_fertility.py`, `test_fertility_zone_context.py`, `test_integration_plan2.py`, `test_orchestrator_birth.py`, `test_template_loader.py`, `test_demography_cost.py` | Adapted (FR-005); US1 scenarios 2-3; US3 scenarios 1-3; SC-004 | FR-005, SC-004, SC-007 |
| `scripts/measure_nuptiality_fertility.py` (couples) | Base rate through `annual_base_rate`; the coherence failure condition of SC-005 | FR-008, SC-005 |
| `scripts/measure_marital_schedule_run.py` | New phase-6 harness | SC-006 |
| `docs/whitepaper/epocha-whitepaper.md`, `.it.md` | §4.1.2, §6.1, §6.2, §6.3, §7.1, §7.3, §9, §10, §11, §13, Appendices A.2 and C | FR-006 |
| `README.md`, `README.it.md` | Roadmap paragraph (line 125 on the Plan 4 head) | FR-006 |
| `.specify/feature.json`, `CLAUDE.md` (SPECKIT block) | Point to this feature | PD-10 |

## Pipeline ordering and integration surface

The demography step order does not change: fertility is still the step that calls `tick_birth_probability` per candidate, after couple formation, with `partnered_agent_ids` from `active_couple_partners`. Inside `tick_birth_probability` the order of operations is unchanged: (1) couple gate, now `requires_couple_for_birth(fertility_cfg)`; (2) `avoid_conception`; (3) base rate, now `annual_base_rate(age, fertility_cfg)`, returning 0.0 early when the base rate is not positive (so Becker is not evaluated for a mother of 14 or 50); (4) Becker; (5) Malthusian ceiling; (6) Δt. The fertility RNG stream and the draw order are untouched, so determinism is unchanged. Integration surface: `annual_base_rate` is public and is called by `tick_birth_probability` and by the SC-005 script; `requires_couple_for_birth` is called by `tick_birth_probability` and `run_fertility_step`; `base_schedule_kind` is called by those two and by the loader. No other module reads the `fertility` section (T003 re-runs the grep on the merged tree, including `agents/`, `simulation/`, `dashboard/` and the life-course branch if merged).

## Doc-sync obligations

All in G3, in both languages (FR-006): §4.1.2 title, status line, Model block ((4.2a)-(4.2d), (4.5) rewritten), the sentence that rejected Coale and Trussell rewritten with the m = 0 reason, the text the couples work item wrote there (their FR-018 and T051: the model-error statement with 2.374) replaced by the correction, Table 4.3 split (Hadwiger for two eras, marital level for three with status), Algorithm (predicate), Simplifications (Becker level T_m·ρ_BK, the 3.0 cap giving 1.03 births per year, the memoryless draw of deferral 2, the "evaluated deterministically" sentence); §6.1 row "Fertility (Hadwiger ASFR + Becker modulation)"; §6.2 new key, the exactly-one rule, seven clauses; §6.3 `fit_marital` does not exist yet and belongs to the validation work item; §7.1 Table 7.1 row "Fertility (Hadwiger ASFR fit)"; §7.3 Table 7.2 row "Fertility (Hadwiger fit)" with TFR₀ = 4.306 labelled "at Becker factor 1, below the Malthusian ceiling, without mortality and without widowhood"; §9 item 3 delivered with this spec's numbers; §10 paragraph "evaluated deterministically at the agent's age"; §11 the spec's known limitations and the "is evaluated deterministically" entry; §13 new sources; Appendix A.2 and Appendix C. Both READMEs, roadmap paragraph. Loader docstrings ("six clauses"). The FR-006 search (T003) adds any further site. The doc-sync table does not change (`fertility.py` is already in row §4.1, the loader and templates in row §6.2). Separately, after G3: two §9 roadmap items the whitepaper lacks today (behaviour by age across the life course; agent context, that is the world setting lost by the Express generation and the chat coherence), each with its source branch or memory note. The build map is updated by the session that owns it, both languages, `scripts/build_map_i18n.py fingerprint` after each text change, republished to the same URL; at closure it registers the deferred birth-interval work item (spec deferral 2).

## Gates

- Phase 3 and 4 (light gates): this plan and `tasks.md`, under the Trinity's provisional approval path.
- Phase 6 (heavy gate): mechanical taste gate on the delta; full suite and ruff green; SC-005 and SC-006 run and reported; **D-MF-09 stop**: if SC-006 configuration B fails, phase 6 halts until the user explicitly chooses one of its two paths (the Trinity cannot choose it); `critical-analyzer` on the code until CONVERGED; Matteo-mode review of the delta; quality at least 8/10 per lens (`quality-scoring`).
- Phase 7: merge into `develop` by the user only.

## Rinvii (out of scope, from the spec)

Parity-dependent control m ≠ 0 (deferral 1); birth intervals (deferral 2, to register on the build map at closure); births outside marriage (deferral 3); the 1700-1749 value and the Table 7.2 interval (deferral 4, validation work item); template mortality (deferral 5, couples deferral 9); Becker calibration (debt B2-07, D-MF-09).

## Phase 0 and Phase 1 artifacts

`research.md`, `data-model.md`, `contracts/` and `quickstart.md` are not generated. The research (sources, verification status, alternatives) is the spec's "Fondamenti scientifici" and "Alternative considerate", audited six rounds; a copy would drift. There is no database entity, and the template schema change is fully specified by FR-003 and FR-004. There is no external interface (contract unchanged). The quickstart is the test command above and the two phase-6 commands in `tasks.md`. Same choice as the couples work item.

## Project Structure

### Documentation (this feature)

```text
specs/20261029-185654-marital-fertility/
├── spec.md              # Italian, phase 2
├── checklists/audit.md  # spec audit log, rounds 1-6
├── plan.md              # this file
├── tasks.md             # phase 4
└── phase6-measurements.md  # written by T052 in phase 6
```

### Source code (repository root)

```text
epocha/apps/demography/
├── fertility.py            # marital schedule, dispatcher, predicate, typed error
├── orchestrator.py         # one statement in run_fertility_step
├── template_loader.py      # interval vocabulary, schema, seventh clause
├── templates/*.json        # five templates
└── tests/
    ├── test_marital_fertility.py   # new
    └── (six adapted test modules)
scripts/
├── measure_nuptiality_fertility.py   # from the couples work item, modified
└── measure_marital_schedule_run.py   # new, phase 6 only
docs/whitepaper/epocha-whitepaper{,.it}.md
README.md, README.it.md
```

**Structure Decision**: existing Django app layout; no new app, no new module in production code.

## Complexity Tracking

No constitution violation. The one structurally large item is commit group G3 (PD-07), justified by the indivisible switch and the same-commit doc-sync rule.

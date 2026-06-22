---
description: "Tasks for ruff repo-wide lint cleanup — restore green CI lint gate"
---

# Tasks: Ruff Repo-Wide Lint Cleanup

**Input**: design documents from `specs/20260622-152915-ruff-repo-wide-cleanup/`

**Prerequisites**: spec.md (3 user stories, 11 FR, 7 SC), plan.md (9-step ordered strategy, Constitution PASS), research.md (F821 root cause, per-rule strategy, ordering constraint)

**Tests**: no new feature tests mandated; this is a no-behavior-change cleanup. The pytest 809 baseline is the regression gate after every commit. New tests admitted only if an F821/F841 investigation reveals a real defect needing coverage.

**Authority**: container ruff 0.15.11 (`docker compose -f docker-compose.local.yml exec -T web ruff ...`). Host ruff is NOT used for gating.

**Ordering is load-bearing**: line-length config (Phase 2) MUST precede the format pass (Phase 3), per research.md Lookup 3.

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: parallel-safe (different files, no dependency on an incomplete task)
- **[Story]**: US1 / US2 / US3 (setup/foundational/polish carry no story label)

---

## Phase 1: Setup (pre-flight)

- [ ] T001 [SETUP] Confirm docker stack up: `docker compose -f docker-compose.local.yml ps`; start with `up -d` if needed; confirm web healthy via `exec -T web python -c "import django; print(django.get_version())"`.
- [ ] T002 [SETUP] Record baseline pytest: `docker compose -f docker-compose.local.yml exec -T web pytest 2>&1 | tail -3`. Expect 809 passed. Pin the number.
- [ ] T003 [SETUP] Snapshot baseline ruff: `docker compose -f docker-compose.local.yml exec -T web ruff check . 2>&1 | tail -2` (expect 1183 errors) and `ruff format --check . 2>&1 | tail -2` (expect 212 would-reformat). Record both for the final delta.

---

## Phase 2: Foundational (BLOCKING — must precede the format pass)

- [ ] T004 [FOUND] In `pyproject.toml` `[tool.ruff]`, change `line-length = 88` to `line-length = 100` (FR-001). Run `docker compose -f docker-compose.local.yml exec -T web ruff check . --select E501 2>&1 | tail -1` to confirm the E501 count drops (~567 fewer). Commit `style(config): raise ruff line-length to 100`. Stage only `pyproject.toml`.

**Checkpoint**: config in place. The format pass below now targets width 100.

---

## Phase 3: User Story 1 — Green CI lint gate, mechanical fixes (Priority: P1) 🎯 MVP

**Goal**: resolve every mechanically-safe violation so the bulk of the gate goes green.

**Independent Test**: after this phase, `ruff check .` shows only the residual naming (US2) and F821/F841 (US3) categories; `ruff format --check .` exits 0; pytest 809.

- [ ] T005 [US1] Run `docker compose -f docker-compose.local.yml exec -T web ruff format .` repo-wide (FR-002). Run pytest (expect 809; format is semantically neutral but the gate is mandatory). Commit `style: ruff format repo-wide` as an ISOLATED commit (no other change staged) for reviewability (SC-006).
- [ ] T006 [US1] Auto-fix safe rules: `docker compose -f docker-compose.local.yml exec -T web ruff check . --fix --select I001,F401,F811,F541,UP035,UP012` (FR-003). NOTE: hold UP037 for T013 (couple.py interacts with the F821 fix). Inspect the diff: confirm no F401 removal drops a re-export side-effect import (check `__init__.py` and any `# noqa`-worthy re-exports). Run pytest (expect 809). Commit `style: ruff auto-fix imports and modernizations`.
- [ ] T007 [US1] Re-measure: `docker compose -f docker-compose.local.yml exec -T web ruff check . --output-format concise 2>&1` and bucket the residual by rule. Record the residual E501 file list and confirm only E501 + N8xx + F821 + F841 + E402 remain. (No commit; produces the worklist for T008-T009 and Phases 4-5.)
- [ ] T008 [US1] Resolve E402 at `epocha/apps/llm_adapter/providers/openai.py:24` (FR-007): if `import openai` sits after code deliberately, move it to the import block, else add `# noqa: E402 -- <reason>`. Run pytest. (Group commit with T009.)
- [ ] T009 [US1] Resolve residual E501 repo-wide (FR-004): wrap cleanly where readable; `# noqa: E501 -- <reason>` for calibration data tables, long DOI URLs, and lines where wrapping harms readability. Work file-by-file from the T007 list. Run `ruff check . --select E501` to confirm zero. Run pytest (expect 809). Commit `style: wrap or annotate residual long lines (E501) and fix E402`.

**Checkpoint**: US1 done — only naming (US2) and F821/F841 (US3) remain in `ruff check .`.

---

## Phase 4: User Story 2 — Scientific naming preserved (Priority: P1)

**Goal**: resolve N806/N803/N802 (36 sites) with formula-variable names preserved via `# noqa` rationale; rename only genuine non-scientific identifiers (FR-005).

**Independent Test**: `ruff check . --select N802,N803,N806` exits 0; `git diff` shows no numeric/formula change; every preserved name carries a rationale noqa.

- [ ] T010 [US2] `epocha/apps/demography/mortality.py` (16 sites): these are Heligman-Pollard law parameters (A,B,C,D,E,F,G,H) and related formula symbols matching the cited paper. Preserve each with `# noqa: N806 -- Heligman-Pollard (1980) parameter notation`. Run pytest. (Group commit with T011-T012.)
- [ ] T011 [US2] [P] `epocha/apps/demography/fertility.py` (3 sites) and `epocha/apps/economy/market.py` (1 site) and `epocha/apps/world/stratification.py` (1 site): triage each; scientific-formula variables → `# noqa: N8xx -- <paper> notation`; non-scientific → rename to snake_case with call-site updates. Run pytest.
- [ ] T012 [US2] [P] Test files `epocha/apps/demography/tests/test_integration_plan2.py` (8) and `test_fertility.py` (3): triage; test-local formula mirrors → noqa with rationale; plain non-scientific locals → rename. Run pytest.
- [ ] T013 [US2] `epocha/apps/dashboard/views.py` (4 sites): these are view-layer locals (non-scientific) → rename to snake_case, update any local uses. Then apply the held UP037 auto-fix here only if relevant. Run pytest. Confirm `ruff check . --select N802,N803,N806` is zero. Commit `style: preserve scientific variable names (noqa) and rename non-scientific (N8xx)`.

**Checkpoint**: US2 done — naming category green, scientific names intact.

---

## Phase 5: User Story 3 — Latent findings investigated, not silenced (Priority: P2)

**Goal**: root-cause-fix the 4 F821 and clear F841 dead-code by investigation (FR-006, FR-007).

**Independent Test**: `ruff check . --select F821,F841` exits 0; each F821 has a documented cause; no F841 silenced with bare `_`.

- [ ] T014 [US3] `epocha/apps/demography/couple.py` F821 (4 sites: lines ~158/178/319/369): add a `TYPE_CHECKING` import block (`from typing import TYPE_CHECKING` + `if TYPE_CHECKING: from epocha.apps.demography.models import Couple`) and unquote the `"Couple"` annotations (this also clears the related UP037 in this file). Verified root cause in research.md: type-annotation hygiene, not a runtime bug (local imports cover runtime; `from __future__ import annotations` makes annotations lazy). Then run the held UP037 auto-fix repo-wide AFTER the couple.py TYPE_CHECKING import is in place: `docker compose -f docker-compose.local.yml exec -T web ruff check . --fix --select UP037` (clears couple.py's now-resolvable annotations plus any UP037 elsewhere). Run `ruff check . --select F821,UP037` (zero) and pytest (couple tests must pass). (Group commit with T015.)
- [ ] T015 [US3] F841 sites (`factions.py`, `dashboard/views.py`, `economy/context.py`, `economy/initialization.py`, and test files `test_couple.py`, `test_context.py`, `test_views.py`): investigate each — remove genuinely-dead variables; if a variable signals an intended-but-omitted use (a real latent bug), restore the use rather than delete. Do NOT silence with bare `_` unless the value is intentionally discarded. Run `ruff check . --select F841` (zero) and pytest (expect ≥809). Commit `fix: resolve F821 Couple annotations and clear F841 dead variables`.

**Checkpoint**: US3 done — F821/F841 green, no real bug left silenced.

---

## Phase 6: Polish & Closure (final heavy gate)

- [ ] T016 [POLISH] Generated/migration files (FR-011): if the T007 residual or any remaining violation sits in Django migrations or generated code, add a scoped `[tool.ruff.lint.per-file-ignores]` / `extend-exclude` entry in `pyproject.toml` with a justifying comment instead of hand-editing. If none, record "no generated-file exclusions needed".
- [ ] T017 [POLISH] Final gate: `docker compose -f docker-compose.local.yml exec -T web ruff check . ; echo exit=$?` (expect exit 0, zero errors) and `ruff format --check . ; echo exit=$?` (expect exit 0) (FR-008, SC-001, SC-002).
- [ ] T018 [POLISH] Final regression: `docker compose -f docker-compose.local.yml exec -T web pytest 2>&1 | tail -3` (expect 809, FR-009, SC-003).
- [ ] T019 [POLISH] Final adversarial review of the FULL diff (`git diff develop...HEAD`) for the no-behavior-change invariant: confirm no numeric constant, formula, or algorithm changed and every scientific name preserved (SC-004); confirm every introduced `# noqa` carries a rationale (SC-005); confirm the format pass is isolated (SC-006). Dispatch a reviewer subagent if the diff is large.
- [ ] T020 [POLISH] Push branch (`/opt/homebrew/bin/gh` for any GitHub op — `gh` is shell-aliased to `git hist`). Open PR to `develop`. After merge: update memory (`project_ruff_cleanup_pending.md` → CLOSED, session resume), sync `docs/memory-backup/`.

---

## Dependencies

| From | Blocks |
|------|--------|
| T001-T003 (setup) | all |
| T004 (line-length 100) | T005 (format pass) and all E501 work |
| T005 (format) | T006-T009 (re-measure depends on formatted tree) |
| T006 (auto-fix) | T007 (re-measure) |
| T007 (re-measure) | T008-T009, Phase 4, Phase 5 worklists |
| T013 held UP037 | T014 (couple.py UP037 handled with F821 fix) |
| Phases 3+4+5 complete | T017-T019 final gates |
| T017-T019 green | T020 PR + merge |

## Parallel Opportunities

- T011 and T012 touch different files → `[P]`.
- Within T009, different files' E501 are independent but bundled in one commit; safe in any order.
- Phases 4 and 5 are independent of each other (naming vs F821/F841) and could interleave, but sequential keeps commits clean.

## Implementation Strategy

MVP = Phase 2 + Phase 3 (US1): config + format + auto-fix + E501/E402 — this clears the large majority of the gate. US2 (naming) and US3 (F821/F841) are the remaining slices; the gate is only fully green (SC-001) after all three. Commit granularity = one commit per strategy step so the 212-file format diff stays isolated from semantic edits.

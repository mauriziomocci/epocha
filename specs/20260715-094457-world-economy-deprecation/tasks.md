# Tasks: Deprecate legacy world/economy.py module

**Input**: Design documents from `/specs/20260715-094457-world-economy-deprecation/`

**Prerequisites**: plan.md, spec.md

**Tests**: test-first is mandatory per project rules (RED before implementation) — test tasks included.

**Organization**: grouped by user story. US1 (deprecation marker) is the MVP; US2 (behavior preservation) is verification-only; US3 (campaign closure docs) is documentation.

## Phase 1: Setup

- [x] T001 Verify preflight anchors still valid: `grep -n "from epocha.apps.world.economy import process_economy_tick" epocha/apps/simulation/engine.py epocha/apps/world/tests/test_economy.py` returns engine.py:38 and test_economy.py:8; `grep -n "run_economy(simulation)" epocha/apps/simulation/tasks.py` returns line 46; `sed -n '2063p;2081p;2221p;2305p' docs/whitepaper/epocha-whitepaper.md` and `sed -n '2131p;2149p;2179p' docs/whitepaper/epocha-whitepaper.it.md` show the stale counts inventoried in spec FR-007. If any anchor drifted, STOP and re-verify before editing (escalation per constitution Principle II).

## Phase 2: Foundational

*(none — no shared infrastructure needed)*

## Phase 3: User Story 1 — Deprecation marker (P1) MVP

**Goal**: developer importing `epocha.apps.world.economy` gets an explicit DeprecationWarning and a docstring naming the replacement and residual callers.

**Independent test**: `pytest epocha/apps/world/tests/test_economy.py -v` — new warning test green, existing tests untouched and green.

- [x] T002 [US1] RED test first: add `test_module_emits_deprecation_warning` to `epocha/apps/world/tests/test_economy.py` — `import importlib`, then inside `with pytest.warns(DeprecationWarning, match="deprecated"):` call `importlib.reload(<module ref to epocha.apps.world.economy>)`. The reload MUST be inside the `pytest.warns` block (pytest sets `simplefilter("always")` there, bypassing `__warningregistry__` dedup). Run it in container and confirm it FAILS (no warning emitted yet). Commit message hint: `test(world): add red test for economy module deprecation warning`.
- [x] T003 [US1] Add deprecation marker to `epocha/apps/world/economy.py`: rewrite the module docstring header to a DEPRECATED block stating — legacy MVP placeholder; superseded by `epocha.apps.economy.*` (audited CONVERGED 2026-04-15, whitepaper §4.2); do not extend; migrate callers and remove in a follow-up work item; verified residual callers: `epocha/apps/simulation/engine.py:38` (module-level import), `run_economy` (engine.py:354) and `SimulationEngine.run_tick` (engine.py:446) fallback paths gated on `Currency` existence, Celery production path `epocha/apps/simulation/tasks.py:46` → `run_economy`, and `epocha/apps/world/tests/test_economy.py`. Keep the existing scientific content of the docstring (Kahneman & Deaton note) below the deprecation block. Add `import warnings` to imports and, after the imports/logger block, `warnings.warn("epocha.apps.world.economy is deprecated, use epocha.apps.economy.* instead", DeprecationWarning, stacklevel=2)`. DO NOT touch any constant, formula, or statement of `process_economy_tick`. Commit message hint: `chore(world): deprecate legacy economy placeholder module`.
- [x] T004 [US1] GREEN check: run `docker compose -f docker-compose.local.yml exec -T web pytest epocha/apps/world/tests/test_economy.py -v` — all tests green including the new one. Run `ruff check epocha/apps/world/` and `ruff format --check epocha/apps/world/` — exit 0.

## Phase 4: User Story 2 — Behavior preservation (P1)

**Goal**: fallback behavior byte-for-byte unchanged.

**Independent test**: full container suite green at baseline+1.

- [x] T005 [US2] Verify diff surface: `git diff epocha/apps/world/economy.py` shows ONLY docstring/import/warn additions — zero changes inside `process_economy_tick` body or module constants. `git diff --stat` shows no other code file touched.
- [x] T006 [US2] Full container suite: `docker compose -f docker-compose.local.yml exec -T web pytest --cov=epocha -q` — zero failures, zero errors, zero new skips/xfail; count = baseline 809 + 1 new.

## Phase 5: User Story 3 — Campaign closure documentation (P2)

**Goal**: whitepaper globally consistent on pending-module count; campaign tracked honestly.

**Independent test**: SC-004 grep checks pass; cross-read memory/retrospective/whitepaper coherent.

- [x] T007 [P] [US3] Fix EN whitepaper `docs/whitepaper/epocha-whitepaper.md` per FR-007 inventory: line ~2063 (§8 intro) "the three Epocha clusters" → "the two Epocha clusters" and "The resolution pass and the convergence re-audit on those three" → "on those two"; line ~2081 (§9 intro) "the audit re-pass on the three modules still pending" → "on the two modules still pending" and append factions to the parenthetical converged list ("; factions converged on round 2 in 2026-05-16 and was promoted to §4.7"); line ~2221 (§11 intro) "the four §8 modules still pending" → "the two §8 modules still pending"; lines ~2305-2318 (§11 body paragraph "Designed subsystems pending Round 2 audit (§8)", hard-wrapped across multiple lines): mirror the ALREADY-CORRECT IT paragraph at it.md line 2218 — "Three modules across three clusters" → "Two modules across two clusters"; remove "factions;" from the pending enumeration (leaving "the Knowledge Graph; the economy base layer"); "Four clusters from the original batch have already converged" → "Five clusters"; append ", and factions on round 2 (2026-05-16) to §4.7" to the converged list after movement. NO other whitepaper edits.
- [x] T008 [P] [US3] Fix IT whitepaper `docs/whitepaper/epocha-whitepaper.it.md` mirroring T007: line ~2131 (§8 intro) "i tre cluster Epocha" → "i due cluster Epocha"; line ~2149 (§9 intro) "sui tre moduli ancora pendenti" → "sui due moduli ancora pendenti" and append factions to the parenthetical converged list ("; le fazioni sono convergenti sul round 2 nel 2026-05-16 e promosse al §4.7"); line ~2179 (§11 intro) "sui tre moduli rimasti in §8" → "sui due moduli rimasti in §8". Verify line ~2218 (§11 body) already says "Due moduli" — leave untouched.
- [x] T009 [US3] SC-004 verification: `grep -n "three modules\|tre moduli\|four §8\|quattro moduli\|three Epocha clusters\|tre cluster" docs/whitepaper/epocha-whitepaper.md docs/whitepaper/epocha-whitepaper.it.md` — zero occurrences referring to the §8 residual; `grep -n "world/economy" docs/whitepaper/*.md` — zero. EN/IT §11 intro now both say two/due.
- [x] T010 [US3] Rewrite `docs/memory-backup/project_audit_repass_batch_2026_04_12_pending.md` body per FR-008: keep name/frontmatter (update description), state F-CAMPAIGN closed 6/6 with per-branch PR + merge SHA table (PR#5 c196281, PR#6 a0ea075, PR#7 dfeb709, PR#8 c543c10, PR#9 5406b95, PR#10 side-work ruff, branch 6 = this feature — PR/SHA filled at closure), then the actually-tracked residual: §8.1 Knowledge Graph and §8.2 economy base layer, Round 2 pending, findings in `docs/scientific-audit-2026-04-12.md`. Whitepaper references in §10/§11/§12 must remain true statements.
- [x] T011 [P] [US3] Write campaign retrospective `docs/memory-backup/project_audit_repass_2026_04_12_completed.md` per FR-009: per-branch outcomes (rounds to converge, promoted section), what Round 2 caught that Round 1 missed (lesson source: branch retrospectives in git history / campaign plan), campaign span 2026-05-12 → closure date, residual explicitly named (§8.1, §8.2, factions Round 3 hardening deferred behavioral findings).
- [x] T012 [US3] Update `docs/memory-backup/MEMORY.md` index: audit-repass entry → campaign closed, residual tracked; add retrospective entry. (Live memory `~/.claude/projects/.../memory/` synced at closure phase together with session-resume update per FR-010.)

## Final Phase: Polish & Verification

- [x] T013 8-point code review on the full diff (Pythonic style, DRY, exceptions, consistency, scalability, security, documentation EN + citations, doc sync incl. bilingual whitepaper mirroring).
- [x] T014 Full gates: `ruff check .` exit 0; `ruff format --check .` exit 0; full container pytest green (evidence pasted in PR); SC-001..SC-005 checked one by one against spec.
- [x] T015 Phase-6 adversarial code audit: dispatch `critical-analyzer` on the complete diff (marker semantics, test robustness, whitepaper edit correctness EN vs IT, memory truthfulness); loop fixes until CONVERGED.

## Dependencies

- T001 → everything (preflight).
- US1: T002 → T003 → T004 (strict TDD order).
- US2: T005, T006 after US1 complete.
- US3: T007/T008/T011 parallelizable [P]; T009 after T007+T008; T010 → T012; T010 PR/SHA fields finalized at closure.
- Final: T013-T015 after all stories.

## Implementation Strategy

MVP = US1 (marker + test). US2 is pure verification. US3 is documentation, parallelizable. Single small PR to develop; commits per story via git-commit-assistant, no push until closure approval.

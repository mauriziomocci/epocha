# Implementation Plan: Deprecate legacy world/economy.py module

**Branch**: `20260715-094457-world-economy-deprecation` | **Date**: 2026-07-15 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/20260715-094457-world-economy-deprecation/spec.md`

## Summary

Mark `epocha/apps/world/economy.py` as deprecated (path B of the F-CAMPAIGN plan): deprecation docstring with verified caller inventory plus a module-level `DeprecationWarning`, with zero behavior change to the `process_economy_tick` fallback. Close the F-CAMPAIGN audit re-pass campaign (branch 6/6): fix the stale pending-module counts in the bilingual whitepaper (7 verified occurrences), rewrite the campaign tracker memory so it keeps tracking only the real residual (§8.1 Knowledge Graph, §8.2 economy base layer), and write the campaign retrospective.

The spec passed the phase-2 adversarial audit loop (Round 1: 6 findings, all resolved; Round 2 verdict recorded in this feature directory's audit notes).

## Technical Context

**Language/Version**: Python 3.12, Django 5.x

**Primary Dependencies**: stdlib `warnings` (no new dependencies)

**Storage**: N/A (no schema change, no data change)

**Testing**: pytest in Docker container (`docker compose -f docker-compose.local.yml exec -T web pytest`), baseline 809 passing

**Target Platform**: unchanged (Docker local / Linux server)

**Project Type**: Django monolith with app packages under `epocha/apps/`

**Performance Goals**: zero runtime impact — one `warnings.warn` per process at import time

**Constraints**: `process_economy_tick` logic byte-for-byte equivalent behavior; suite stays green with zero weakened assertions; `ruff check .` and `ruff format --check .` stay exit 0; EN/IT whitepaper mirrored

**Scale/Scope**: 1 code file touched (marker only), 1 new test, 2 whitepaper files (count fixes only), 3-4 memory/tracking markdown files

## Constitution Check

*GATE: evaluated against `.specify/memory/constitution.md` v1.0.0.*

- **I. Scientific Method**: no formula, parameter, or model changed. The deprecation marker cites the audited replacement (`epocha/apps/economy/*`, CONVERGED 2026-04-15, whitepaper §4.2). PASS.
- **II. Verify Before Asserting**: caller inventory, whitepaper line numbers, pytest config, and warning semantics verified against sources during spec authoring; line-number claims re-verified in Round 2 audit. Code-verification preflight for tasks is embedded in tasks.md (each task lists exact file:line anchors). PASS.
- **III. Adversarial Audit**: spec audit Round 1 → 6 findings (1 blocking cluster on whitepaper scoping, 1 on memory rewrite, 2 minor) → all fixed → Round 2 re-audit. Code audit fires again at phase 6 on the diff. PASS.
- **IV. Three-Step Design**: initial proposal, first self-review (warning category, import caching, Celery noise, pytest filters), consolidation — performed before spec authoring; recorded in spec FAQ/Assumptions. PASS.
- **V. Evidence-Based Verification**: success criteria are all mechanically checkable (grep, pytest, ruff). Confidence level at closure will be "unit tests + container suite"; no production deployment involved. PASS.
- **Documentation Discipline**: whitepaper §4 untouched (module is not a chapter-4 module — doc-sync rule satisfied by PR description note); §8/§9/§11 count fixes keep EN/IT mirrored; frozen-at-commit pin procedure applies at closure because the whitepaper is touched. PASS.

No violations → Complexity Tracking not needed.

## Project Structure

### Documentation (this feature)

```text
specs/20260715-094457-world-economy-deprecation/
├── spec.md              # Phase 2 artifact (approved via audit loop)
├── plan.md              # This file
├── tasks.md             # Phase 4 artifact (/speckit-tasks)
└── checklists/
    └── requirements.md  # Spec quality checklist (passed)
```

research.md, data-model.md, contracts/ and quickstart.md are intentionally not materialized: no unknowns survived spec authoring (all resolved with file:line evidence in the spec), no data model is touched, and no external interface changes. This follows the artifact-materialization gradation of the spec-driven layout for a small, fully-scoped work item.

### Source Code (repository root)

```text
epocha/apps/world/economy.py            # deprecation docstring + warnings.warn (logic untouched)
epocha/apps/world/tests/test_economy.py # +1 regression test: DeprecationWarning on reload
docs/whitepaper/epocha-whitepaper.md    # count fixes: lines ~2063 (§8), ~2081 (§9), ~2221 (§11 intro), ~2305 (§11 body)
docs/whitepaper/epocha-whitepaper.it.md # count fixes: lines ~2131 (§8), ~2149 (§9), ~2179 (§11 intro)
docs/memory-backup/project_audit_repass_batch_2026_04_12_pending.md   # body rewrite (campaign closed, residual tracked)
docs/memory-backup/project_audit_repass_2026_04_12_completed.md       # NEW campaign retrospective
docs/memory-backup/MEMORY.md            # index updates (via live-memory sync at closure)
```

**Structure Decision**: single-module marker change inside the existing `epocha/apps/world/` app; no new modules, no placement decision required (nothing new is created — Architectural Placement rule trivially satisfied).

## Implementation approach

1. **Marker (US1)**: replace the module docstring header with a DEPRECATED block naming the replacement and the verified callers (`simulation/engine.py:38` import; `run_economy` ~372 and `SimulationEngine` loop ~463 fallback gated on `Currency`; Celery path `simulation/tasks.py:46` → `run_economy`; `world/tests/test_economy.py:8`). Add `import warnings` + `warnings.warn(..., DeprecationWarning, stacklevel=2)` after imports. Keep every constant, comment, and statement of the tick logic untouched.
2. **Regression test (US1, test-first)**: new test in `epocha/apps/world/tests/test_economy.py` — `importlib.reload(economy)` inside `pytest.warns(DeprecationWarning, match="deprecated")`. Written RED-first against the unmodified module (it fails because no warning is emitted), then the marker turns it GREEN. `pytest.warns` uses `simplefilter("always")` internally, so `__warningregistry__` dedup does not suppress re-emission (verified in audit F-12).
3. **Behavior preservation (US2)**: no assertion in existing tests changes. Full container suite must stay at baseline+1.
4. **Whitepaper count fixes (US3)**: apply the FR-007 inventory exactly — 4 EN edits, 3 IT edits; nothing else. EN §8 intro also fixes its internal "three clusters / two modules / those three" self-contradiction.
5. **Memory closure (US3)**: rewrite tracker memory body per FR-008; write retrospective per FR-009; update session-resume memory and MEMORY.md index per FR-010; sync live memory ↔ `docs/memory-backup/`.
6. **Verification**: `ruff check .`, `ruff format --check .`, container pytest, grep-based SC-004 global-coherence check, adversarial code audit on the final diff (phase-6 heavy gate).

## Risks

- **Warning-based test flakiness**: mitigated by reload-inside-`pytest.warns` (audit-verified pattern). If the container's pytest version behaves differently, escalate rather than weaken the test.
- **Whitepaper edit drift EN/IT**: mitigated by editing from the exact FR-007 inventory and re-grepping both files afterwards (SC-004).
- **Docker unavailable at test time**: suite must run in container (authority per project rules). If the daemon is down, closure blocks and the session reports "unit tests only" — no green claim without container evidence.

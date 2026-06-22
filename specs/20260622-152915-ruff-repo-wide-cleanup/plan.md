# Implementation Plan: Ruff Repo-Wide Lint Cleanup

**Branch**: `20260622-152915-ruff-repo-wide-cleanup` | **Date**: 2026-06-22 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/20260622-152915-ruff-repo-wide-cleanup/spec.md`

## Summary

Restore the green CI lint gate (`ruff check .` and `ruff format --check .`, both currently failing on develop with 1183 check-errors and 212 files needing format). Approach: raise `line-length` to 100, run `ruff format` repo-wide as an isolated commit, auto-fix the mechanically-safe rules, then resolve the residual style/naming/structure findings by hand with scientific-naming preserved via `# noqa` rationale, and root-cause the 4 F821 findings. Zero scientific-model change, pytest baseline 809 preserved.

## Technical Context

**Language/Version**: Python 3.12 (Django 5.1.x), container ruff 0.15.11 (authority; host ruff 0.15.8 not used for gating)

**Primary Dependencies**: ruff (linter + formatter); Django; pytest. No new dependency.

**Storage**: N/A (no schema change)

**Testing**: pytest in web container (`docker compose -f docker-compose.local.yml exec -T web pytest`); baseline 809 passed.

**Target Platform**: Linux container (CI + local docker)

**Project Type**: Single Django project (`epocha/apps/*`, `config/`, `tests/`)

**Performance Goals**: N/A (no runtime change)

**Constraints**: zero behavior change; no numeric constant / formula / algorithm change; scientific-formula variable names preserved.

**Scale/Scope**: 1183 `ruff check` violations across 150 files + 212 files needing `ruff format`; 14 rule categories.

## Constitution Check

*GATE: pass before Phase 0; re-check after Phase 1.*

- **I. Scientific Method Above All** — PASS. No model/formula/parameter/algorithm change. The only scientific-adjacent risk is naming (N806/N803/N802): mitigated by FR-005 (preserve formula variable names with `# noqa` rationale; rename only genuine non-scientific identifiers). FR-010 + SC-004 enforce zero change to numeric constants and formulas.
- **II. Verify Before Asserting** — PASS. Every rule count/category measured against container ruff (recorded in spec table). F821 root cause verified in source before planning the fix.
- **III. Adversarial Audit** — PASS (scope-appropriate). No scientific code is authored; the adversarial check reduces to "did any fix change behavior?" — covered by the pytest 809 gate after every commit and a final reviewer pass on the full diff (Phase 6 heavy gate). A full `critical-analyzer` scientific audit is N/A for a no-model refactor; the final review verifies the no-behavior-change invariant instead.
- **IV. Three-Step Design** — PASS. Spec consolidated after the 3 upfront strategic decisions (line-length, format-all, naming policy).
- **V. Evidence-Based** — PASS. pytest gate mandatory per phase; ruff exit-0 is the objective success signal.

No violations. Complexity Tracking not required.

## Project Structure

### Documentation (this feature)

```text
specs/20260622-152915-ruff-repo-wide-cleanup/
├── plan.md              # this file
├── spec.md              # approved spec
├── research.md          # Phase 0: F821 root cause + rule-handling strategy + ordering
├── checklists/
│   └── requirements.md  # spec quality checklist (all pass)
└── tasks.md             # Phase 2 (/speckit-tasks)
```

data-model.md, contracts/, quickstart.md are **N/A** for this feature: no new entities, no external interfaces, no user-facing flow beyond the CI gate. Skipped deliberately per the Spec Kit "skip if purely internal" rule.

### Source Code (repository root)

```text
pyproject.toml                 # [tool.ruff] line-length 88 -> 100; possible per-file-ignores / exclude for generated code
epocha/apps/*/                 # bulk of violations (demography, economy, agents, world, simulation, ...)
config/                        # settings, asgi, celery, urls
tests/, epocha/apps/*/tests/   # test files (test_integration.py needs format)
.github/workflows/ci.yml       # the gate being restored (no edit needed; it already runs the two ruff steps)
```

**Structure Decision**: existing single-project layout; the cleanup touches files across all apps plus `pyproject.toml`. No structural change.

## Implementation Strategy (ordered — ordering is load-bearing)

The order is dictated by the formatter/line-length interaction (spec Edge Cases):

1. **Config first**: raise `line-length` to 100 in `pyproject.toml` (FR-001). Commit alone so the format pass below uses the new width.
2. **Format pass**: `ruff format .` repo-wide (FR-002), isolated commit `style: ruff format repo-wide`. Verify pytest 809 (format is semantically neutral but the gate is mandatory).
3. **Auto-fix safe rules**: `ruff check --fix` for I001, F401, UP037, F811, F541, UP035, UP012 (FR-003). Verify pytest. Commit. NOTE: UP037 on the couple.py annotations interacts with the F821 fix in step 5 — sequence so the TYPE_CHECKING import lands before/with unquoting.
4. **Re-measure**: `ruff check .` to get the residual set after steps 1-3 (most E501 and the manual categories). This drives the exact per-file task list in `/speckit-tasks`.
5. **F821 root-cause** (FR-006): add a `TYPE_CHECKING` import block for `Couple` in `epocha/apps/demography/couple.py` and unquote the 4 annotations. Verified root cause: `Couple` is only imported locally inside functions (circular-import avoidance) and referenced in string annotations at lines 158/178/319/369; with `from __future__ import annotations` present, runtime is unaffected, so this is type-annotation hygiene, not a runtime bug. Add/confirm a test exercises couple formation.
6. **Naming N806/N803/N802** (FR-005): triage each of the 36 sites scientific-vs-not. Scientific-formula variables -> `# noqa: N806 -- matches <paper> notation`. Genuine non-scientific -> rename + update call sites + pytest. N803 on public/serializer args -> prefer noqa if renaming breaks an external contract.
7. **F841 / E402** (FR-007): remove genuinely-dead variables; for E402 move the import or `# noqa: E402` with rationale if a deliberate late import.
8. **Residual E501** (FR-004): wrap cleanly where possible; `# noqa: E501 -- <reason>` for data tables, long DOI URLs, and lines where wrapping harms readability.
9. **Final gate**: `ruff check .` exit 0, `ruff format --check .` exit 0, pytest 809. Final reviewer pass on full diff for the no-behavior-change invariant (Phase 6 heavy gate).

Commit granularity: one commit per strategy step (config, format, auto-fix, F821, naming, dead-code, E501) so the large format diff stays isolated from semantic edits (SC-006).

## Complexity Tracking

No constitution violations; section not required.

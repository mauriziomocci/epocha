# Feature Specification: Ruff Repo-Wide Lint Cleanup

**Feature Branch**: `20260622-152915-ruff-repo-wide-cleanup`

**Created**: 2026-06-22

**Status**: Draft

**Input**: User description: "Ruff repo-wide lint cleanup to restore green CI lint gate."

## Context

The CI pipeline (`.github/workflows/ci.yml`) runs `ruff check .` and `ruff format --check .` as gating steps. Both currently fail on `develop`: `ruff check .` reports **1183 errors across 150 files** and `ruff format --check .` reports **212 files would be reformatted**. The lint gate has been red for a long time. A permanently-red gate trains the team to ignore CI red, which lets genuine failures (a broken test, a real format regression) pass unnoticed. The risk being addressed is the loss of CI-signal reliability, not code style as such.

This was discovered during the closure of Branch 5 (factions audit re-pass) of the F-CAMPAIGN. That branch introduced zero new violations; the debt is pre-existing and accumulated across the project's history. It is recorded in the project memory `project_ruff_cleanup_pending.md`.

This is a refactor/cleanup work item. It changes no scientific model, formula, parameter, or algorithm. Constitution Principle I (Scientific Method Above All) is satisfied by preserving every scientific behavior and every formula-matching variable name unchanged; the only scientific-adjacent risk is the naming category (N806/N803/N802), handled explicitly below.

### Current violation breakdown (`ruff check .`, container ruff 0.15.11)

| Rule | Count | Auto-fixable | Nature |
|---|---|---|---|
| E501 line-too-long | 1056 | no (formatter handles code lines only) | style; median 99 char, max 627 |
| I001 unsorted-imports | 32 | yes | style |
| F401 unused-import | 30 | yes | dead code |
| N806 non-lowercase-variable-in-function | 26 | no | naming (scientific-sensitive) |
| F841 unused-variable | 9 | no | dead code |
| N803 invalid-argument-name | 8 | no | naming (API-sensitive) |
| UP037 quoted-annotation | 5 | yes | modernization |
| F821 undefined-name | 4 | no | possible real bug (`Couple` in demography/couple.py) |
| F811 redefined-while-unused | 4 | yes | dead code |
| UP035 deprecated-import | 3 | yes | modernization |
| N802 invalid-function-name | 2 | no | naming |
| F541 f-string-missing-placeholders | 2 | yes | style |
| UP012 unnecessary-encode-utf8 | 1 | yes | modernization |
| E402 module-import-not-at-top | 1 | no | structure |

Plus `ruff format --check .`: 212 files would be reformatted, 86 already formatted.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Green CI lint gate restored (Priority: P1) — MVP

As the maintainer, when CI runs on a PR, both `ruff check .` and `ruff format --check .` exit 0, so a red CI run again means a genuine problem rather than chronic lint debt.

**Why this priority**: This is the entire purpose of the work item. Restoring the gate's reliability is the deliverable; everything else is in service of it.

**Independent Test**: run `ruff check .` and `ruff format --check .` in the web container; both exit 0. Run the full pytest suite; still 809 passed.

**Acceptance Scenarios**:
1. Given the repo at the cleanup HEAD, when `ruff check .` runs, then it exits 0 with zero reported errors.
2. Given the repo at the cleanup HEAD, when `ruff format --check .` runs, then it exits 0 with zero files needing reformat.
3. Given the cleanup HEAD, when the full test suite runs, then 809 tests pass and zero behavior changed.

### User Story 2 - Scientific naming and formulas preserved (Priority: P1)

As the scientific author, the cleanup must not rename variables whose uppercase or paper-matching identifiers encode formula notation (e.g. CES production `Q`, `A`, `X`; matrix/coefficient symbols), nor alter any numeric constant or formula.

**Why this priority**: Constitution Principle I. A blind snake_case rename of scientific variables would break the name-to-formula traceability the project mandates and could obscure the link between code and cited papers. This constraint gates how N806/N803/N802 are resolved.

**Independent Test**: inspect every N806/N803/N802 resolution; each scientific-formula variable retains its name via `# noqa` with a rationale, and `git diff` shows no change to any numeric literal or formula expression.

**Acceptance Scenarios**:
1. Given an N806 on a formula variable in a scientific module, when resolved, then the name is preserved with an inline `# noqa: N806` carrying a short scientific rationale.
2. Given an N803 on a genuinely non-scientific helper argument, when resolved, then it may be renamed to snake_case provided all call sites are updated and tests pass.
3. Given the full cleanup diff, when reviewed, then no numeric constant, formula, or algorithm has changed.

### User Story 3 - Latent bugs surfaced are investigated, not silenced (Priority: P2)

As the maintainer, the 4 F821 undefined-name findings (`Couple` in `demography/couple.py`) and the F841/F401 dead-code findings are investigated for real defects before being cleared, rather than blanket-suppressed.

**Why this priority**: F821 undefined-name can indicate a genuine bug (missing import, typo, broken forward reference). Suppressing it without understanding would violate the No-Bug-Left-Behind rule. Lower than P1 because it touches few sites, but it must not be skipped.

**Independent Test**: for each F821, the root cause is identified (missing import vs string annotation vs real undefined symbol) and the fix matches the cause; a regression test or existing test covers the affected code path.

**Acceptance Scenarios**:
1. Given the 4 F821 `Couple` findings, when investigated, then the root cause is determined and documented in the commit.
2. Given an F841 unused-variable, when cleared, then either the variable is genuinely dead (removed) or its intended use is restored (not silenced with `_`).

### Edge Cases

- **line-length interaction with the formatter**: raising `line-length` to 100 changes how `ruff format` wraps. The line-length change MUST be applied before running `ruff format`, otherwise the format pass produces 88-wrapped code that then re-fails E501 under the 100 setting (or vice versa).
- **E501 the formatter cannot fix**: long comments, long string literals, long data-table rows, and URLs are not rewrapped by `ruff format`. After format + the 100 limit, remaining E501 must be wrapped manually where clean, or carry a per-line `# noqa: E501` with rationale where wrapping would harm readability (e.g. a calibration data table or a DOI URL).
- **noqa vs per-file-ignore for naming**: per-line `# noqa` is preferred over `[tool.ruff.lint.per-file-ignores]` because it documents intent at the site and does not blanket-disable the rule for unrelated future code in the same file.
- **F-string F541 in logging**: removing an f-prefix from a log message with no placeholder must not change the emitted string.
- **Migrations and generated files**: Django migration files may carry violations; decide whether to fix or exclude via ruff config rather than hand-editing generated code.
- **Format churn vs review**: the 212-file format pass produces a large diff; it must be an isolated commit so semantic fixes remain reviewable separately.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: `pyproject.toml` `[tool.ruff] line-length` MUST be raised from 88 to 100. (Decision: option "100" — eliminates ~54% of E501 while keeping a compact style.)
- **FR-002**: `ruff format` MUST be run across the whole repository and committed as a single dedicated, semantically-neutral commit, applied AFTER FR-001.
- **FR-003**: All auto-fixable rules (I001, F401, UP037, F811, F541, UP035, UP012) MUST be resolved via `ruff check --fix`, verified to introduce no behavior change.
- **FR-004**: Remaining E501 after FR-001+FR-002 MUST be resolved by manual wrapping where clean, or per-line `# noqa: E501` with a short rationale where wrapping harms readability.
- **FR-005**: N806/N803/N802 on scientific-formula variables MUST be preserved with per-line `# noqa` carrying a scientific rationale; only genuinely non-scientific identifiers may be renamed, and a rename MUST update all call sites with tests passing.
- **FR-006**: The 4 F821 `Couple` findings MUST be root-caused and fixed according to cause (missing import / forward reference / real undefined name), not blanket-suppressed.
- **FR-007**: F841 unused-variable and E402 module-import-not-at-top MUST be resolved case by case (remove genuinely-dead code; move imports or `# noqa` with rationale where a deliberate late import is required).
- **FR-008**: After all fixes, `ruff check .` and `ruff format --check .` MUST both exit 0 in the web container.
- **FR-009**: The full pytest suite MUST remain at the 809-test green baseline with zero behavior change.
- **FR-010**: No scientific model, formula, numeric constant, parameter, or algorithm may change. No whitepaper §4/§8 chapter content changes (this is not a model change; the whitepaper doc-sync rule does not trigger).
- **FR-011**: If any ruff rule is decided to be excluded rather than fixed (e.g. for migrations or generated files), the exclusion MUST be expressed in `pyproject.toml`/ruff config with a comment justifying it, not by hand-editing generated files.

### Key Entities

- **Ruff rule category**: a class of violation (E501, I001, F401, N806, F821, ...) with a count, an auto-fixable flag, and a resolution strategy (auto-fix / format / manual-wrap / noqa-rationale / rename / root-cause-fix / config-exclude).
- **Scientific-formula variable**: an identifier whose name encodes paper notation; resolution = preserve + noqa-rationale.
- **CI lint gate**: the two CI steps `ruff check .` and `ruff format --check .`; success = both exit 0.

## Success Criteria *(mandatory)*

- **SC-001**: `ruff check .` exits 0 with zero errors in the web container.
- **SC-002**: `ruff format --check .` exits 0 with zero files needing reformat.
- **SC-003**: The full pytest suite reports 809 passed (or higher if F821/F841 fixes add regression tests), zero failed, zero xfail.
- **SC-004**: `git diff` of the cleanup against the base shows no change to any numeric constant, formula expression, or algorithm; every scientific-formula variable retains its name.
- **SC-005**: Every `# noqa` introduced carries a short rationale; no blanket file-level rule disables beyond what FR-011 justifies in config.
- **SC-006**: The `ruff format` mass change is isolated in its own commit, separate from semantic fixes, for reviewability.
- **SC-007**: Each of the 4 F821 findings has a documented root cause and a cause-matched fix.

## Assumptions

- The web container's ruff (0.15.11) is the authority; host ruff (0.15.8) may differ and is not used for gating.
- Raising line-length to 100 is an accepted project-style change (user-approved), not requiring a separate constitution amendment.
- The `${word^^}` bashism failure in `create-new-feature.sh` (sequential numbering fallback) is an environment quirk already corrected by renaming the branch/dir to the timestamp convention; it is out of scope for this feature.
- Migration files and any generated code, if they carry violations, are candidates for ruff config exclusion rather than hand-editing.

## Scope

**In scope**: all `ruff check .` and `ruff format --check .` violations repo-wide; the `pyproject.toml` line-length change; CI gate restoration.

**Out of scope**: any scientific model change; whitepaper content; new features; the F-CAMPAIGN Branch 6 (world economy deprecation); the factions Round 3 hardening; Demography Plan 4. Fixing the `create-new-feature.sh` bashism permanently (tracked separately if desired).

## Dependencies

- Docker stack (`docker-compose.local.yml`) up, web container healthy, for ruff and pytest gates.
- Spec Kit mandatory authoring path (this spec then plan then tasks then implement).

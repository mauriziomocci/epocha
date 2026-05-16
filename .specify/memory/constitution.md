# Epocha Constitution

Epocha is a scientifically grounded civilization simulator. This constitution canonicalizes the non-negotiable principles that govern every spec, plan, task and code change. It supersedes any conflicting code-quality directive elsewhere in the project; where it is silent, the project's `CLAUDE.md` and `~/.claude/CLAUDE.md` continue to apply.

## Core Principles

### I. Scientific Method Above All (NON-NEGOTIABLE)

The supreme rule. Every model, algorithm, formula, parameter, behavioral rule must be grounded in established science, verified against primary sources, and subjected to adversarial review.

- No formula without a cited primary source
- No parameter without a justified value
- No simplification without documented trade-offs
- No assumption without explicit statement
- No scientific code without adversarial review reaching CONVERGED verdict
- No issue left unresolved: fix → re-review → repeat until clean
- When science says one thing and convenience says another, science wins

The iterative quality loop is mandatory: all INCORRECT findings resolved, all UNJUSTIFIED parameters cited or documented as tunable heuristics, all INCONSISTENT findings reconciled, all MISSING assumptions documented. Partial resolution is not acceptable.

### II. Verify Before Asserting (NON-NEGOTIABLE)

Every scientific, technical, architectural assertion must be verified against its source before being presented as fact.

- Scientific citations: author, year, title, specific claim — no invented citations
- Model parameters: verify the parameter actually works that way in the referenced model
- Architectural claims: verify against actual documentation or code, not memory or extrapolation
- User assertions: when a user assertion appears incorrect or inconsistent with the project's scientific foundations, emit a WARNING block and ask for confirmation; never silently accept a user assertion that contradicts verified science

Plan task breakdown must include code-verification preflight: every function signature, file path, configuration variable, model field, URL pattern, library claim mentioned in a task must be verified against actual code before the task is dispatched.

### III. Adversarial Scientific Audit (NON-NEGOTIABLE)

Every scientific model, formula, algorithm, constant, assumption must undergo adversarial scientific review. Not optional, not deferrable.

Mandatory convergence loop:
1. Audit: dispatch `critical-analyzer` subagent with hostile mandate. Output categorized table INCORRECT/UNJUSTIFIED/INCONSISTENT/MISSING/VERIFIED.
2. Fix: resolve all INCORRECT and UNJUSTIFIED; document or resolve INCONSISTENT and MISSING.
3. Re-audit: verify each original finding is resolved; check for new issues from fixes.
4. Convergence check: if all findings RESOLVED and no new INCORRECT/UNJUSTIFIED → CONVERGED. Otherwise return to step 2.
5. Verdict: explicitly state CONVERGED or NOT CONVERGED. No "close enough".

Adversarial review fires at two distinct moments per work item: on the spec before code is written, and on the code before merge.

### IV. Three-Step Design Process (NON-NEGOTIABLE)

Before producing any design document, follow three mandatory iterative steps.

1. Initial proposal: after gathering requirements, present a first complete design (models, interfaces, data flow, trade-offs, dependencies) detailed enough to be evaluated. Do not write the spec file yet.
2. First critical self-review: immediately after, perform deep adversarial self-review. Look for anti-patterns, missing edge cases, architectural smells (mutually-exclusive FKs, generic FKs, JSON blobs where relational serves), scalability issues, race conditions, security gaps. Write categorized findings.
3. Second self-review and consolidation: review fixes from step 2 with fresh eyes. Look for fixes that introduced new problems. Produce the final consolidated design. Only then write the spec.

Skipping steps is forbidden regardless of perceived simplicity.

### V. Evidence-Based Verification

Never claim a fix, feature, or change "works" or is "confirmed" without concrete evidence from the actual running environment.

- Unit tests are necessary but not sufficient. A passing test proves logic in isolation; it does NOT prove the fix works in production.
- After deploying a fix: verify in the real environment. If verification is not immediately possible, state explicitly: "deployed but not yet verified — requires [specific verification steps]".
- Never extrapolate success. If a test passes or a deploy succeeds, report exactly that — not that "the problem is resolved".
- Confidence levels: use one of "Verified in production/stage", "Tests passing, deployed, real environment verification pending", or "Unit tests only".

Bug discipline: every bug, failing test, or issue encountered during a session is fixed within that session even if not caused by the current work. Never close a session with red tests, ignored warnings, or known undocumented bugs. Shortcuts to hide problems are forbidden: `pytest.mark.skip` without traceable rationale, `try/except` that swallows exceptions, `# fix later` comments, removal of failing assertions.

## Documentation Discipline

The bilingual scientific whitepaper at `docs/whitepaper/epocha-whitepaper.md` (EN authoritative) and `epocha-whitepaper.it.md` (IT mirror) is the publication-grade reference. Chapter 4 contains audited Methods (modules whose adversarial audit reached CONVERGED). Chapter 8 lists implemented modules with audit pending. Chapter 9 lists planned work.

Whitepaper-code doc-sync rule: PRs that modify code of a module described in chapter 4 must update the corresponding section of the bilingual whitepaper in the same commit, or explain in the PR description why the change does not affect the model. The mapping is maintained in the project memory `feedback_whitepaper_doc_sync.md`. After a module's Round 2 audit reaches CONVERGED, the standard promotion procedure (`project_whitepaper_promotion_pipeline.md`) moves it from §8 to §4.x.

Bibliography rigor: every author-year citation in the body must have a §13 entry. Every §13 entry must be cited at least once. Citations follow Author-Date format with DOI/URL. Primary-source strict: no citation of derivative sources where the primary is accessible.

Citation drift after Round 1 remediation is a known failure mode: the campaign convention is to dispatch a Round 2 adversarial audit before declaring any module CONVERGED.

## Development Workflow

Epocha follows the canonical 7-phase workflow inherited from `~/.claude/CLAUDE.md` Development Workflow section:

1. Ideation
2. Requirements (HEAVY GATE): three-step design + adversarial scientific audit on the spec
3. Architectural plan (LIGHT GATE)
4. Task breakdown (LIGHT GATE) with code-verification preflight per Principle II
5. Implementation per atomic task with subagent-driven development
6. General test + adversarial code audit (HEAVY GATE)
7. Closure: merge, sync memory, frozen-at-commit pin if whitepaper touched

Spec-Driven Layout (Spec Kit adoption since 2026-05-16):
- New feature artifacts live under `specs/<timestamp>-<feature-slug>/{spec,plan,tasks}.md` per Spec Kit canonical convention
- Existing artifacts under `docs/superpowers/specs/` and `docs/superpowers/plans/` retain their historical paths and git history; they are not migrated retroactively
- Branch numbering: timestamp (YYYYMMDD-HHMMSS) to preserve continuity with the existing date-based naming convention
- The Spec Kit templates (`/.specify/templates/`) and skills (`.claude/skills/speckit-*`) are the default authoring path for any work item that crosses the Phase 2 heavy gate

Model selection per phase (inherited): Opus for phases 1-4 and 6-7 (scientific judgment, audits, design), Sonnet for phase 5 implementation, Haiku never. Escalation to Opus is mandatory whenever Sonnet faces a strategic decision outside the specified execution.

Italian for spec files (project rule, see `feedback_italian_specs.md` memory); English for everything else (code, commits, plans, docstrings, README, whitepaper EN, CLAUDE.md). The whitepaper Italian mirror is the only exception where translated technical prose is the deliverable.

## Governance

This constitution supersedes the code-quality portions of `CLAUDE.md` where they conflict. Where the constitution is silent, `CLAUDE.md` and `~/.claude/CLAUDE.md` apply. Where there is no conflict, both sets of rules compose.

Amendments require: explicit user approval, a one-line entry in the project memory `feedback_canonical_workflow.md` documenting the change, a version bump and amendment date, and migration guidance for in-flight work items.

All PRs and reviews must verify compliance with the five core principles. Complexity must be justified against Principle V (evidence-based verification): if a feature cannot be verified in the real environment, it must be marked as such and tracked as a follow-up.

For runtime development guidance, use `CLAUDE.md` (project-level), `~/.claude/CLAUDE.md` (global), and the memories under `~/.claude/projects/-Users-mauriziomocci-Documents-workspace-Opensource-epocha/memory/` (session continuity).

**Version**: 1.0.0 | **Ratified**: 2026-05-16 | **Last Amended**: 2026-05-16

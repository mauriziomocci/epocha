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

Italian for spec files (see `feedback_italian_specs.md`) **and for the build map** (added by amendment 1.1.0, recorded in `feedback_canonical_workflow.md`); English for everything else (code, commits, plans, docstrings, README, whitepaper EN, CLAUDE.md). The build map joins the specs rather than the code because it is the artifact the user must read and act on at every checkpoint, which is the same reason the specs are in Italian.

Two deliverables carry translated technical prose, and each declares which text is normative: the **whitepaper**, whose Italian mirror follows the normative English; and the **build map**, whose normative text is the Italian one, with English as the mirror. A bilingual deliverable without a declared normative text cannot answer "verify against reality first" — it does not say against which text — so declaring it is part of the deliverable, not an afterthought.

A bilingual deliverable must state how its languages are kept aligned, and whether that is a mechanism or a manual practice. The build map's two languages are watched by a structural guard in the suite —
watched, not held together: no checksum distinguishes a translation from a lazy
bump, so the guard makes an omission a deliberate, diff-visible act rather than a
silent one. **The whitepapers are not**: the doc-sync rule is a PR review checklist, the project has no active git hooks, and `feedback_whitepaper_doc_sync.md` says building one is deliberately deferred while the developer is single. The frozen-at-commit pin records a fact; it does not fail.

That asymmetry is stated rather than papered over, because the first version of this clause claimed both deliverables were mechanically held and was caught in the same gate that wrote it. A property asserted in prose and not enforced by a mechanism gets violated silently — measured sixteen times during the phase-6 gate of the demography design-defects work item — and a constitution that misdescribes its own enforcement is the worst place for that class to live. Promoting the whitepaper doc-sync to a mechanism is a separate work item, not a sentence.

## Governance

This constitution supersedes the code-quality portions of `CLAUDE.md` where they conflict. Where the constitution is silent, `CLAUDE.md` and `~/.claude/CLAUDE.md` apply. Where there is no conflict, both sets of rules compose.

Amendments require: explicit user approval, a one-line entry in the project memory `feedback_canonical_workflow.md` documenting the change, a version bump and amendment date, and migration guidance for in-flight work items.

All PRs and reviews must verify compliance with the five core principles. Complexity must be justified against Principle V (evidence-based verification): if a feature cannot be verified in the real environment, it must be marked as such and tracked as a follow-up.

For runtime development guidance, use `CLAUDE.md` (project-level), `~/.claude/CLAUDE.md` (global), and the memories under `~/.claude/projects/-Users-mauriziomocci-Documents-workspace-Opensource-epocha/memory/` (session continuity).

## Amendment log

**1.1.0 — 2026-08-12.** The language rule gains the build map, which moves from
"everything else" to the Italian side, and the constitution now names both
bilingual deliverables with their normative text and requires each to state HOW
its languages are kept aligned — by a mechanism or by a manual practice — rather
than leaving that unsaid. It does not require a mechanism for both: the
whitepapers are held by a review checklist, and saying so is the point. Ratified explicitly by the user on 2026-08-12,
raised by the phase-2 gate of work item `20260812-143706-bilingual-build-map`,
whose first audit round found the feature would otherwise create a second
exception to a sentence reading "the only exception".

*Migration guidance for in-flight work items*: none is affected. The only work
item open at ratification is the one that raised the amendment. Existing
artifacts do not move: the whitepapers keep English as their normative text and
the specs stay Italian, both unchanged. The build map is English-only until
`20260812-143706-bilingual-build-map` ships; until then it satisfies the amended
rule by being a single-language artifact, and the guard that FR-006 to FR-007b
require is what makes the bilingual state enforceable when it arrives. No
retroactive translation of anything is implied.

**Version**: 1.1.0 | **Ratified**: 2026-05-16 | **Last Amended**: 2026-08-12

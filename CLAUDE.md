# CLAUDE.md

Guide for Claude Code — Epocha: AI-powered civilization simulator.

## Project

- **Repository**: https://github.com/mauriziomocci/epocha
- **License**: Apache 2.0
- **Owner**: Maurizio Mocci (@mauriziomocci)
- **Status**: MVP in development (pre-release)

## Quick Reference

```bash
# Health check
docker compose -f docker-compose.local.yml ps

# Development
docker compose -f docker-compose.local.yml up --build

# Testing
pytest --cov=epocha -v               # Full suite
pytest epocha/apps/simulation/ -v     # Single app
pytest -k "test_specific" -v          # Single test

# Quality
ruff check .
ruff format --check .
```

## Architecture

**Stack**: Django 5.x + DRF | PostgreSQL (future: + PostGIS + pgvector) | Celery + Redis | Django Channels | OpenAI-compatible LLM API

**Apps**: `epocha.apps.users` (auth), `simulation` (tick engine, events), `agents` (personality, memory, decisions), `world` (map, economy, zones), `chat` (WebSocket conversations), `llm_adapter` (provider abstraction)

**API** (`/api/v1/`): `users/`, `simulations/`, `agents/`, `worlds/`, `chat/`

**WebSocket**: `ws/simulation/<id>/` (real-time state), `ws/chat/<agent_id>/` (agent conversations)

**Celery**: `run_simulation_loop` (self-enqueuing tick loop), `process_agent_turn` (single agent decision), `generate_agent_response` (chat response)

**Config**: `config/settings/` — `base.py` (shared), `local.py` (dev), `production.py` (prod), `test.py` (pytest)

**Files**:
- `config/` — Django settings, ASGI, Celery, URL routing
- `epocha/apps/` — All Django apps (domain logic)
- `epocha/common/` — Shared utilities (pagination, permissions, exceptions)
- `compose/` — Dockerfiles and entrypoints
- `requirements/` — Dependency files (base, local, production)
- `docs/` — Design specs and implementation plans

## Agent Rules

### GOLDEN RULE: Scientific Method Above All

**THIS IS THE SUPREME RULE OF THE ENTIRE PROJECT. It takes precedence over every other rule, guideline, or convention in this document. When any other rule conflicts with this one, this one wins.**

The scientific method must be prioritary over everything and perfectly executed following established best practices. Epocha is a scientific simulation. Every model, algorithm, formula, parameter, and behavioral rule must be grounded in established science, verified against sources, and subjected to adversarial review.

**The iterative quality loop**: all scientific issues identified at any level (code, design, specification, or runtime behavior) must be resolved, and a new review must be conducted after each resolution. This cycle repeats until the result reaches an acceptable optimum — defined as: all INCORRECT findings resolved, all UNJUSTIFIED parameters either cited or explicitly documented as tunable heuristics, all INCONSISTENT findings reconciled, and all MISSING assumptions documented. There is no shortcut: partial resolution is not acceptable; the review loop must converge.

**This means:**
1. No formula without a cited source
2. No parameter without a justified value
3. No simplification without documented trade-offs
4. No assumption without explicit statement
5. No scientific code without adversarial review
6. No issue left unresolved — fix, re-review, repeat until clean
7. When the science says one thing and convenience says another, the science wins

### CRITICAL: Scientific Rigor (detailed requirements)

**CRITICAL RULE**: the Golden Rule above establishes the principle; this section specifies the operational requirements.

**Requirements:**
1. **Every mathematical model must cite its source** — whether it is a textbook formula, a peer-reviewed paper, or an established algorithm. The source must be documented in the code (docstring or comment with reference).
2. **Parameters must have realistic values** — not arbitrary numbers. If a parameter represents a real-world quantity (population growth rate, inflation coefficient, disease transmission rate), its default value must come from real data. Document where the value comes from.
3. **Models must be validated** — before merging any scientific model, verify it produces outputs consistent with known historical data or published results. Include validation tests that compare model output against reference data.
4. **No "magic numbers"** — every constant in a formula must be named, documented, and justified. `DECAY_RATE = 0.002` is not acceptable without a comment explaining why 0.002 and where it comes from.
5. **Game theory equilibria must be computed correctly** — Nash equilibria, Shapley values, and other game-theoretic computations must use established algorithms, not approximations, unless the approximation is documented and justified.
6. **When in doubt, simplify rather than guess** — a simple model with correct assumptions is better than a complex model with made-up parameters. If we do not have data to calibrate a model, use the simplest defensible version and document the limitation.

### CRITICAL: Code Quality Standards

**CRITICAL RULE**: All code in Epocha must be elegant, scalable, Pythonic, and follow Django best practices. This is not aspirational — it is a mandatory standard for every line of code.

**Principles:**

1. **DRY (Don't Repeat Yourself)** — No duplicated logic anywhere. If code appears twice, extract it. No exceptions. This applies to: models, views, serializers, tasks, tests, templates, configurations.

2. **Pythonic code** — Follow PEP 20 (The Zen of Python by Tim Peters):
   - Beautiful is better than ugly
   - Explicit is better than implicit
   - Simple is better than complex
   - Flat is better than nested
   - Readability counts
   - There should be one — and preferably only one — obvious way to do it

3. **Django best practices** — Follow the official Django documentation and Two Scoops of Django (Feldroy) conventions:
   - Fat models, thin views — business logic belongs in models and service modules, not in views
   - Use Django's built-in tools before reaching for third-party packages
   - Keep apps small and focused (single responsibility)
   - Use `select_related()` and `prefetch_related()` proactively, not as afterthought
   - Use class-based views when they simplify, function-based when they clarify
   - Settings split by environment (base/local/production/test)
   - Use `django-environ` for configuration
   - Use `reverse()` for URL references, never hardcode paths

4. **Reusable by design** — Every component should be written with reuse in mind where it makes sense:
   - Extract common patterns into mixins, base classes, or utility functions in `epocha/common/`
   - Serializer mixins for shared field sets
   - Model mixins for shared behaviors (TimestampMixin, etc.)
   - Service layer functions that can be called from views, tasks, and management commands
   - But: do not over-abstract. Three similar lines are better than a premature abstraction

5. **Scalable architecture** — Code must work at small scale (MVP, 20 agents) and be ready for large scale (hundreds of agents, multiple simulations) without rewriting:
   - Database queries must be efficient at any scale (N+1 forbidden)
   - Celery tasks must be idempotent and safe for concurrent execution
   - State management through database, not in-memory globals
   - Horizontal scaling must be possible without code changes

6. **Reference standards:**
   - [Django Official Documentation](https://docs.djangoproject.com/)
   - [Two Scoops of Django](https://github.com/feldroy/two-scoops-of-django-3.x)
   - [PEP 8](https://peps.python.org/pep-0008/) — Style Guide
   - [PEP 20](https://peps.python.org/pep-0020/) — The Zen of Python
   - [DRF Best Practices](https://www.django-rest-framework.org/)

### ABSOLUTE PRIORITY: Verify Every Assertion

**ABSOLUTE PRIORITY RULE**: this rule takes precedence over all other rules. Every scientific, technical, and architectural assertion must be verified against its source before being presented as fact. Never assume an assertion is correct just because it sounds plausible.

**What to verify:**
1. **Scientific citations**: when citing a paper or model, verify that the author, year, title, and the specific claim attributed to the source are correct. Do not invent citations or misattribute claims.
2. **Model parameters**: when proposing a parameter "derived from the literature" (a threshold, a rate, an exponent, a range), verify that the parameter actually works that way in the referenced model. A velocity that should be emergent must not be stored as a constant. A rent that should derive from production must not be a magic percentage.
3. **Parameter ranges**: when stating that a parameter ranges from X to Y, verify that this is the standard range in the discipline. Do not invent ranges.
4. **Architectural claims**: when stating that a pattern "follows best practice" or "is standard in Django", verify it against the actual documentation or established convention.
5. **Consistency with prior decisions**: when building on earlier design sections, verify that the new section does not contradict what was already approved.
6. **User assertions**: the user's statements and requests must ALSO be verified. The user can make mistakes, state incorrect facts, or propose approaches that conflict with established science. When a user assertion appears questionable, incorrect, or potentially inconsistent with the scientific foundations of the project, emit a **WARNING** block and ask for explicit confirmation before proceeding. Format: `**WARNING**: [explanation of the concern]. Do you confirm or should we reconsider?`. Never silently accept a user assertion that contradicts verified science.

**How to apply:**
- During brainstorming: after proposing a design section, immediately re-read it looking for unverified assertions. Flag them and fix them before the user approves.
- During the three-step design process: step 2 and step 3 must specifically hunt for unverified assertions as a dedicated check, not just architectural smells.
- During implementation: when writing code that implements a scientific formula, verify the formula against the cited source before committing.
- When in doubt: say "I am not certain about X, it needs verification" rather than presenting X as fact.
- When the user says something that seems incorrect or inconsistent: do NOT silently comply. Emit a WARNING, explain the concern with evidence, and ask for confirmation. The user expects to be challenged when wrong — blind compliance is a disservice.

**Why**: Epocha is a scientific simulation. Every unverified assertion that makes it into the codebase degrades the scientific credibility of the entire project. A single magic number without justification, a single misattributed citation, a single parameter stored as constant when it should be emergent — each of these is a crack in the foundation. This applies equally to assertions from the AI assistant AND from the user: science does not care who made the mistake. This rule was formalized on 2026-04-12 after discovering six unverified assertions in a single data model proposal during the economic model brainstorming, and strengthened the same day when the user explicitly requested to be warned about their own potential errors.

### ABSOLUTE PRIORITY: Adversarial Scientific Audit

**ABSOLUTE PRIORITY RULE**: every scientific model, formula, algorithm, constant, and assumption in Epocha must undergo adversarial scientific review. This is not optional, not deferrable, not skippable for "simple" changes.

**When to audit:**
1. **Before committing any spec**: after the three-step design process completes, dispatch an adversarial review subagent that examines the spec as a hostile scientific reviewer would. The reviewer looks for: incorrect citations, misapplied formulas, unjustified parameters, undocumented simplifications, internal contradictions, missing edge cases, and claims presented as facts without evidence.
2. **Before committing scientific code**: after implementation, dispatch a review subagent that reads the actual code and verifies every formula, constant, and algorithm against the cited sources. Code comments claiming "Source: X (1961)" must be checked against what X (1961) actually says.
3. **Periodically on existing code**: when starting work on a feature that touches scientific modules, audit the existing code in those modules first. Do not build on unverified foundations.
4. **On user request**: the user can request a full audit of any module at any time.

**How the audit works:**
- Dispatch a `critical-analyzer` subagent (or equivalent) with the specific mandate of being adversarial: its job is to find flaws, not to confirm that things are correct.
- The audit produces a structured report with categories: INCORRECT (wrong formula, wrong citation, wrong parameter), UNJUSTIFIED (parameter without source, simplification without documentation), INCONSISTENT (contradictions between modules), MISSING (undocumented assumptions, missing edge cases), VERIFIED (items checked and confirmed correct).
- Every INCORRECT and UNJUSTIFIED finding must be resolved before the code is committed. INCONSISTENT and MISSING findings should be resolved or explicitly documented as known limitations.

**Mandatory convergence loop (re-audit protocol):**
The audit is not a one-shot activity. It follows a mandatory convergence loop:
1. **Audit**: dispatch `critical-analyzer` with adversarial mandate. Produces INCORRECT/UNJUSTIFIED/INCONSISTENT/MISSING/VERIFIED report.
2. **Fix**: resolve all INCORRECT and UNJUSTIFIED findings. Document or resolve INCONSISTENT and MISSING.
3. **Re-audit**: dispatch `critical-analyzer` again with explicit mandate to verify that each original finding is resolved, and to check for new issues introduced by the fixes.
4. **Convergence check**: if all original findings are RESOLVED and no new INCORRECT or UNJUSTIFIED issues are found, the loop CONVERGES. If any finding remains open or new issues appear, return to step 2.
5. **Verdict**: the re-audit must explicitly state one of: CONVERGED (acceptable optimum reached) or NOT CONVERGED (another cycle needed). There is no "close enough" — the loop runs until CONVERGED.

This protocol is integrated into every scientific audit, not run as a separate process. When dispatching the `critical-analyzer`, always include both the initial audit scope AND the re-verification mandate in the same workflow.

**What the auditor checks:**
- Every mathematical formula: is it correctly transcribed from the cited source? Are variable names consistent? Are units consistent?
- Every constant: does the cited source actually contain this value? Is the context of the citation correct (not cherry-picked or misapplied)?
- Every algorithm: does it implement what it claims to implement? Are the convergence properties correctly stated? Are the complexity claims correct?
- Every simplification: is it documented? Is the full model stated alongside the simplification? Is the loss from simplifying acknowledged?
- Every assumption: is it stated explicitly in the code/docstring? Is it consistent with assumptions in other modules?
- Cross-module consistency: do modules that interact (economy + government, information flow + reputation, etc.) use compatible definitions and units?

**Why**: Epocha's value proposition is scientific rigor. An unaudited scientific model is an unverified claim. The adversarial posture is essential because confirmation bias makes self-review insufficient: the person who wrote the formula naturally believes it is correct. An independent reviewer with the explicit mandate to find errors catches what self-review misses. This rule was formalized on 2026-04-12 at the user's explicit request, extending the verification paradigm from individual assertions to systematic institutional review.

### CRITICAL: Three-Step Design Process

**CRITICAL RULE**: before producing any design document (spec, architecture proposal, data model, API contract), follow a mandatory three-step iterative process. Skipping steps is forbidden. This applies to every design task, regardless of perceived simplicity.

**Step 1 — Initial proposal**: after gathering requirements through brainstorming, present a first complete design. It must be detailed enough to be evaluated on its merits (models, interfaces, data flow, trade-offs, dependencies). Do not write the spec file yet.

**Step 2 — First critical self-review**: immediately after presenting the initial proposal, perform a deep critical review of your own work. Look for: anti-patterns, missing edge cases, decisions hidden behind "for simplicity", architectural smells (mutually-exclusive FKs, generic foreign keys, JSON blobs where relational would serve, free-text fields where controlled vocabularies should exist), scalability issues, missing dependencies, unclear versioning, race conditions, security gaps. Be as critical as an adversarial reviewer. Write the findings as a categorized list (critical / important / minor / what works). Propose fixes for each finding.

**Step 3 — Second critical self-review and consolidation**: review the fixes from step 2 with fresh eyes. Look for fixes that introduced new problems, fixes that are still too shallow, gaps not addressed in the first review. Then produce the final consolidated design that integrates all valid fixes from both reviews. Only after this step write the spec document.

**Why**: a single-pass design hides unexamined assumptions. The first review catches obvious smells; the second catches problems introduced or missed by the fixes. Two rounds of critical self-review are the minimum to produce a design worth implementing. This process was formalized on 2026-04-11 after it produced a materially better Knowledge Graph design than a single-pass attempt would have.

**How to apply**:
- After brainstorming, present the design in sections (step 1)
- Immediately launch the self-review without waiting for the user to ask (step 2)
- Before writing the spec, run a second review explicitly on the fixes (step 3)
- Only after step 3 write the spec file and proceed to the planning phase

### CRITICAL: Every Spec Includes a FAQ Section

**CRITICAL RULE**: every design specification document must include a FAQ section at the end that answers the questions a reviewer or implementer is most likely to ask. The FAQ is not optional filler; it is the place where design rationale is explicitly surfaced so future readers do not need to re-derive it from context.

**Why**: a spec describes *what* is being built. Without an explicit FAQ, the *why* lives only in the chat transcripts and tribal knowledge of whoever wrote it. Six months later, when someone reviews the code and asks "why did we pick X instead of Y?", the answer is either lost or requires archaeological work to reconstruct. A FAQ locks the reasoning into the versioned spec where it cannot be lost.

**What the FAQ must cover**:
- **Design decisions**: for every non-obvious choice (ontology size, data types, algorithms, thresholds), answer "why this and not the alternative?"
- **Scientific rigor**: how the cited references map to implementation details
- **Integration**: how the new feature interacts with existing systems
- **Performance and limits**: expected latency, throughput, cost, hard caps
- **Reproducibility**: what is deterministic, what is not, and why
- **Comparison with alternatives**: how the choice compares to off-the-shelf libraries, other databases, competing approaches
- **Operational concerns**: privacy, failure modes, recovery procedures
- **Security**: attack surface and mitigations

**How to apply**:
- Write the FAQ as the last section of the spec, after the Known Limitations and Out of Scope sections
- Phrase questions in the voice of someone reviewing the spec critically, not in marketing voice
- Each answer should be 2-5 sentences; longer answers belong in the main body of the spec, with a pointer from the FAQ
- Include questions the reviewer actually asked during brainstorming — those are the most valuable because they document real ambiguities that existed
- When in doubt, add the FAQ entry: a spec with too many FAQ entries is a minor inconvenience, a spec with missing FAQ entries leaves the reader guessing

**When to update the FAQ**: any time the spec is revised based on review feedback, add a FAQ entry capturing the decision that was clarified. The FAQ grows with the spec.

### CRITICAL: Canonical 7-Phase Development Workflow

**CRITICAL RULE**: every new subsystem, major feature, or spec in Epocha MUST follow the canonical 7-phase workflow below without exceptions. Skipping phases or confusing gates is a rule violation.

**The 7 phases**:

```
1. IDEATION (natural-language user input)
        ↓
2. REQUIREMENTS
   - Brainstorming: agent asks in-depth clarifying questions
   - Spec file written to docs/superpowers/specs/YYYY-MM-DD-<name>.md
   - Must include: scientific foundations, architecture, design decisions log,
     alternatives considered, FAQ, known limitations
   HEAVY GATE:
   - Three-step design process
   - Adversarial scientific audit (critical-analyzer subagent)
   - Mandatory convergence loop (audit → fix → re-audit until CONVERGED)
   - Explicit human validation of final spec
        ↓
3. ARCHITECTURAL PLAN DESIGN
   - Agent drafts the plan from validated spec
   - Plan defines: modules, file changes, pipeline ordering, integration surface
   - Plan does NOT yet contain operational task breakdown
   LIGHT GATE: human validation of the architectural plan
        ↓
4. TASK BREAKDOWN
   - Decompose plan into small, detailed tasks (see task-breakdown rule)
   - Each task: checkbox + detailed description + files involved + tests + commit msg
   - Granularity 2-5 minutes per task; no vague tasks
   LIGHT GATE: human validation of breakdown
   + Critical post-validation review (agent rereads with fresh eyes and raises any
     residual doubts BEFORE touching code; trigger: transition design → implementation;
     scope: overlooked details likely to be lost during writing; NOT a second
     brainstorming, NOT a second adversarial audit)
        ↓
5. IMPLEMENTATION (task-by-task, sequential)
   For each task:
   - Write code exactly as described
   - Test the task (unit + regression)
   - Critical, punctual, in-depth code review (8-point Mandatory Code Review)
   - Flag task as resolved
   - Move to next task ONLY after completion + flag
        ↓
6. GENERAL IMPLEMENTATION TEST
   - Full test suite (pytest --cov=epocha -v)
   - End-to-end integration test
   - Zero failing tests; zero xfail
   HEAVY GATE:
   - Final adversarial review (critical-analyzer on CODE, not spec)
   - Explicit human validation of closure
        ↓
7. CLOSURE
   - Merge feature branch to develop (--no-ff)
   - Sync memory backup (docs/memory-backup/)
   - Push
   - Update progress memory
```

**Operational principles (non-negotiable)**:

1. **Strict sequentiality between phases**: phase N+1 requires phase N's gate closed. No shortcuts.

2. **Heavy vs light gates**:
   - **Heavy gates** (rigorous validation): REQUIREMENTS gate (closes the scientific phase; spec is the foundation) and FINAL gate (closes the work).
   - **Light gates** (quick review, prerequisites already rigorously validated): DESIGN gate (confirm plan coherence with spec) and TASK BREAKDOWN gate (confirm granularity and completeness).
   - Distinction prevents gate fatigue: each subsystem has 4 gates, 2 heavy and 2 light.

3. **Adversarial review fires at two distinct moments**:
   - Requirements gate: adversarial on the SPEC (scientific rigor, citations, formulas)
   - Final gate: adversarial on the CODE (correctness, security, performance)
   - Separate reviews with distinct scope.

4. **Critical post-validation review (phase 4 gate tail)**:
   - Trigger: transition from design to code writing
   - Scope: details that risk being lost because not explicit
   - NOT a second brainstorming
   - NOT a second adversarial audit
   - It is the "last coherence check" before writing code

5. **Task-breakdown rule** activates at phase 4 and governs phase 5 execution.

6. **Verify-before-asserting** and **GOLDEN RULE** are always active, never suspended.

**Mapping to superpowers skills**:
- Phase 2 (Requirements): `superpowers:brainstorming`
- Phase 3 + 4 (Design + Task breakdown): `superpowers:writing-plans`
- Phase 5 (Implementation): `superpowers:executing-plans` or `superpowers:subagent-driven-development`
- Phase 6 (General test): `superpowers:verification-before-completion`
- Phase 7 (Closure): `superpowers:finishing-a-development-branch`

**Revision of this rule**: the workflow is modified only on explicit user request. New lessons produce NEW feedback memories, not silent alterations of this rule.

### CRITICAL: Model Selection Policy per Workflow Phase

**CRITICAL RULE**: each phase of the canonical 7-phase workflow uses a specific Claude model. The assignment is NOT a per-session option; it is codified to optimize scientific rigor where it matters and cost/speed where it does not matter less.

**Model assignment per phase**:

| Phase | Model | Rationale |
|-------|-------|-----------|
| 1. Ideation | Opus 4.7 | Conceptual exploration, initial clarifications |
| 2. Requirements (brainstorming, spec, adversarial audit, convergence loop) | **Opus 4.7 with extended thinking** | Scientific rigor, bibliography, formulas, heavy gate. Errors here propagate through the entire pipeline. |
| 3. Architectural plan design | Opus 4.7 | Architecture, cross-module trade-offs, integration with existing subsystems |
| 4. Task breakdown + post-validation critical review | Opus 4.7 | Accurate decomposition, detection of hidden gaps before code |
| 5. Implementation (per-task) | **Sonnet 4.6** | Execution of fully-specified tasks; 3-5× faster and ~5× cheaper than Opus |
| 5-bis. Per-task routine code review | Sonnet 4.6 | 8-point Mandatory Code Review on atomic task |
| 5-ter. Final cross-task integration code review | Opus 4.7 | Overall architectural judgment, coherence across tasks |
| 6. General test + final adversarial code audit | **Opus 4.7** | Heavy final gate; scientific correctness of code; hostile, in-depth auditor |
| 7. Closure (merge, memory sync, push) | Sonnet 4.6 | Mechanical, deterministic operations |

**Escalation protocol (non-negotiable)**: during phase 5 (Sonnet implementation), if a task reveals an unforeseen edge case, wrong spec assumption, required undeclared refactor, incoherence with existing code, or scientific doubt about a formula/citation — the Sonnet subagent does NOT invent a solution. It **escalates to Opus** via the orchestrating dispatcher. Sonnet resumes only after Opus has revised the spec/plan/task.

Escalation trigger: any time the task requires a **strategic decision** rather than **specified execution**. Bright line: if the answer to "what do I do?" is not fully derivable from the task and spec, escalate.

**Scientific citation accuracy**: Epocha's docstrings cite exact sources (Heligman & Pollard 1980, Jones & Tertilt 2008, etc.). Citations in code MUST match exactly those in the spec — no invention, no paraphrase. Per-task code review by Sonnet must verify this explicitly on every task with a scientific docstring.

**Context preservation paradox**: Sonnet has a smaller context window than Opus 1M. To make it usable in phase 5, tasks produced in phase 4 must be **truly atomic** (file-focused, narrow scope). If a task would require Sonnet to hold the entire plan + spec + reference codebase in context, the task is too large and must be split further in phase 4.

**Haiku is NEVER used**. Haiku is too lightweight for Epocha's constraints (scientific rigor, OWASP security, 8-point Mandatory Review, exact citations). The balance is: **Opus where it counts, Sonnet where it does not count less, Haiku never**.

**Technical mechanism**: per-model delegation is implemented via the `superpowers:subagent-driven-development` skill. The main dispatcher (Opus) orchestrates phases 1-4 and 6-7; for each phase-5 task, the dispatcher dispatches an Agent with explicit `model: "sonnet"` override. On escalation, the subagent returns an escalation flag; the Opus dispatcher takes over, revises, and re-launches or modifies the plan.

**Revising this policy**: only on explicit user request.

### CRITICAL: Task Breakdown and Sequential Execution (implementation plans only)

**CRITICAL RULE**: every **implementation plan** must be broken into as many well-detailed tasks as possible, each with a checkbox flag (`- [ ]` / `- [x]`), and executed strictly one task at a time with the flag toggled upon completion before moving to the next. No batching multiple tasks without intermediate flagging. No skipping ahead.

**Scope and trigger**: the rule activates when a spec has been approved (design + adversarial audit + CONVERGED) and implementation planning begins. It applies to plan files under `docs/superpowers/plans/`.

**What the rule does NOT cover**:
- Standalone edits not tied to a plan
- Answers to user questions
- Documentation commits unrelated to an implementation plan
- Micro-maintenance operations

Applying the rule to out-of-scope operations would create bureaucratic overhead without benefit. The bright line: if the work lives in `docs/superpowers/plans/` or is descending an approved spec into code, the rule applies; otherwise, it does not.

**Why**: four drivers:
1. **Transparency**: for a plan the user sees in real time exactly what is done and what remains, without reading diffs.
2. **Operational granularity**: small tasks mean safe steps, isolated failures, ability to interrupt and resume without losing context.
3. **Publication-grade audit trail**: each completed task is a documented piece of evidence, consistent with the scientific paper goal of the project.
4. **Context preservation for the AI agent**: in long plans with dozens of tasks, the currently "in progress" (not yet flagged) task is the agent's focus pointer. Working task-by-task keeps Claude focused on the specific context needed for that single task, without dispersing attention across the whole plan. Without breakdown and sequential flagging, the agent risks losing details, forgetting completed steps, or skipping required files. Flagging is the synchronization mechanism between work state and agent cognitive state — an operational necessity, not only a methodological preference.

**How to apply**:
- When drafting an implementation plan (after the spec is approved and audited), decompose the work into the smallest coherent tasks. A task is 2-5 minutes of work, a single atomic modification, or a tightly coupled group of files.
- Each task uses the checkbox syntax (`- [ ] **Step N**: ...`) compatible with the `superpowers:writing-plans` skill and the existing Epocha plan format (see `docs/superpowers/plans/`).
- No vague tasks. Never write "Implement the feature X"; always write "Create file X with class Y containing method Z that does W, with tests T1-T3".
- During execution:
  - Take ONE task
  - Implement precisely
  - Toggle the flag to `- [x]`
  - Move to the next
  - Do NOT skip ahead. Do NOT batch-process multiple tasks without intermediate flagging.
- When all tasks are flagged, the plan is done; proceed to merge/PR/memory-sync as usual.

**Non-negotiable within scope**: within the scope defined above, the rule is mandatory with no exceptions. Outside the scope the rule does not apply.

**Compatibility**: the existing plans (Plan 3a, 3b, 3c of Economy) already use this pattern; no retrofit required.

**Typical scale for Epocha**: for a complex subsystem such as Demography, expect 60-80 tasks distributed across 3-5 sequential plans, each containing 15-25 tasks of 2-5 minutes each.

### CRITICAL: Understand Before Implementing

**CRITICAL RULE**: before writing any code — whether fixing a bug, building a new feature, or designing an architecture — invest time in understanding the full context: how the existing system works, why it works that way, and what already exists. Solving a symptom without understanding the root cause leads to layered workarounds instead of clean solutions.

### CRITICAL: Verify Before Asserting

**CRITICAL RULE**: never present assumptions, hypotheses, or inferences as verified facts. Before stating how something works — in code, documentation, or communication — verify it directly in the source code or data. If something has not been verified, say so explicitly.

### CRITICAL: Exhaustive Bug Analysis

**CRITICAL RULE**: when a bug or inconsistency is found, **never stop at the first problem**. Follow a structured 4-phase process:

**Phase 1 — Define scope**: explicitly declare the analysis boundaries (method, class, module, flow) before starting.

**Phase 2 — Systematic comparison**: if a working "twin" method exists, perform a **complete line-by-line comparison**. Do not stop at the first divergence. Every differing line is a potential independent bug.

**Phase 3 — Symptom-cause map**: build an explicit table for every reported symptom:

| Symptom | Identified cause | Required fix | Covered by this fix? |
|---------|-----------------|--------------|---------------------|

If a symptom has no identified cause, the analysis is incomplete.

**Phase 4 — Explicit declaration**: conclusions must always follow the format: **"this fix resolves X. It does NOT resolve Y, which requires a separate fix on Z."** Never implicit conclusions, never present a partial fix as a complete solution.

### CRITICAL: Evidence-Based Verification

**CRITICAL RULE**: never claim that a fix, feature, or change "works" or is "confirmed" without concrete evidence from the actual running environment. Follow this protocol:

1. **Unit tests are necessary but not sufficient**: a passing test proves the logic is correct in isolation. It does NOT prove the fix works in production.

2. **After deploying a fix**: verify in the real environment. Check logs, reproduce the original scenario, or observe the expected behavior change. If verification is not possible immediately, explicitly state: **"deployed but not yet verified — requires [specific verification steps]"**.

3. **Never extrapolate success**: if a test passes or a deploy succeeds, report exactly that — not that "the problem is resolved".

4. **Explicit confidence level**: when reporting fix status, always use one of:
   - **"Verified in production/stage"**: the fix was observed working in the real environment
   - **"Tests passing, deployed, real environment verification pending"**: logic is correct, deployed, but not yet confirmed
   - **"Unit tests only"**: logic tested in isolation only

### CRITICAL: Memory Backup Sync

**CRITICAL RULE**: the project memory is stored in two locations that must stay in sync:

1. **Live memory**: `~/.claude/projects/-Users-mauriziomocci-Documents-workspace-Opensource-epocha/memory/` — read automatically by Claude Code at session start.
2. **Versioned backup**: `docs/memory-backup/` in the git repository — portable across machines, never lost.

**After every significant work session** (new features implemented, design decisions made, rules added, audit completed), the memory backup must be updated:

```bash
cp ~/.claude/projects/-Users-mauriziomocci-Documents-workspace-Opensource-epocha/memory/*.md docs/memory-backup/
git add docs/memory-backup/ && git commit -m "docs: sync memory backup" && git push
```

**When setting up on a new machine**, restore memory from the backup:

```bash
mkdir -p ~/.claude/projects/-Users-mauriziomocci-Documents-workspace-Opensource-epocha/memory/
cp docs/memory-backup/*.md ~/.claude/projects/-Users-mauriziomocci-Documents-workspace-Opensource-epocha/memory/
```

This is not optional. Lost memory means lost context, lost rules, lost decisions. The backup must always reflect the current state of the live memory.

### Core Behavior

- **Read CLAUDE.md first**: before starting any task, re-read the Agent Rules in this file
- **Read and understand existing files** before modifying code
- Avoid over-engineering: only implement what is requested
- Prefer editing existing files over creating new ones
- Do NOT create documentation files unless explicitly requested
- All code, comments, docstrings, logs: **English only**, NO emoji/emoticon
- Commit messages: **English** (Conventional Commits), PEP 8 with 120 char line limit, double quotes
- Plan files, test files, README, CLAUDE.md, memory backup: **English only**
- **Spec files** in `docs/superpowers/specs/` are written **in Italian only** (single authoritative version, no sync burden). An English translation is produced only when needed for paper publication. See `feedback_italian_specs` rule. All other documentation stays English only.
- Tests: **ZERO failing tests**. Use `pytest.mark.skip(reason="TODO: ...")` when necessary

### Execution Discipline

1. **Plan before acting**: read directives, understand the codebase context, then call tools, subagents, and MCP agents in the correct logical order. Do not guess or skip steps.
2. **Understand before implementing**: never start coding before understanding the full context and root cause.
3. **Verify before asserting**: never state something as fact without verifying it in the source code or data first.
4. **Handle errors, do not ignore them**: read the full error message and stack trace carefully. Diagnose the root cause, fix the code, and re-test until it passes.
5. **Evidence before assertions**: never claim something works without evidence from the real environment.
6. **Ask for clarification when needed**: if requirements are ambiguous or a decision has multiple valid approaches, ask the user before proceeding.
7. **Learn and update directives**: if you discover a new pattern or recurring pitfall, **propose** the update to CLAUDE.md to the user. Do not modify directives autonomously.

### Code Comments and Docstrings

- **Language**: English, professional and precise tone
- **NO emoji/emoticon** in any context
- **Write thorough comments**: Epocha is a scientific simulation, not a CRUD app. Code must be well-commented so that a researcher, contributor, or future AI session can understand the scientific basis of every non-trivial piece of logic without reading external papers.
- **What to comment**:
  - Every mathematical formula: state the formula name, cite the source (author, year), and document what each variable represents. Example: `# CES production function (Arrow et al. 1961). Q = A * [sum(alpha_i * X_i^rho)]^(1/rho), where rho = (sigma-1)/sigma`
  - Every constant or parameter: document its value, source, and why that value was chosen. Example: `# Price elasticity of subsistence goods: 0.3 (Houthakker & Taylor 1970, updated by Andreyeva et al. 2010)`
  - Every algorithm: state what it does, its computational complexity, known limitations, and cite the source. Example: `# Walrasian tatonnement (Walras 1874). Warning: may not converge with 3+ goods (Scarf 1960). Max iterations as safety net.`
  - Every simplification or approximation: document what the full model would be, why we simplified, and what we lose. Example: `# Simplified Ricardian rent: proportional to zone production bonus. Full model would compute differential surplus vs marginal land.`
  - Every assumption: state it explicitly. Example: `# Assumption: agents have perfect information about local prices (relaxed in spec 2 via belief system friction)`
- **What NOT to comment**: obvious code (`i += 1`), Python idioms, Django boilerplate, variable assignments whose purpose is clear from the name
- **Docstrings**: every module, class, and public function gets a docstring. Module docstrings cite the primary scientific sources. Class docstrings explain the model the class implements. Function docstrings explain inputs, outputs, and any non-obvious behavior.
- **Queryset and dependencies**: if a component requires specific `select_related`/`prefetch_related`, document the requirements in the class docstring

### Documentation Sync

After any code change, update all affected documentation **in the same commit**:

- **Docstrings**: update if method signature, behavior, or return value changed
- **README files**: update if the change affects architecture, workflows, configuration, or operational procedures

Do NOT leave documentation updates for a separate commit.

### Mandatory Code Review

**CRITICAL RULE**: after writing any code, **BEFORE proposing a commit** you must ALWAYS perform a thorough code review. No exceptions.

The code review must verify:

1. **Pythonic style and DRF best practices**
2. **DRY violations**: duplicated logic that can be extracted
3. **Exception handling**: specific exceptions (never bare `except Exception` if expected type is known)
4. **Codebase consistency**: field types, naming, architectural patterns
5. **Scalability**: no N+1 queries or uncontrolled recursive serialization
6. **Security**: no unexpected side-effects, no sensitive data exposure
7. **Documentation**: docstrings in English, clear and complete
8. **Documentation sync**: docstrings and README files are updated if the change affects them

Fix issues BEFORE proposing the commit. Report what was found and corrected.

## Mandatory Rules

### Query Performance (N+1 FORBIDDEN)
```python
# WRONG - for user in users: Activity.objects.filter(user=user).count()
# CORRECT - users.annotate(activity_count=Count('activity'))
```
- `select_related()` for FK/OneToOne, `prefetch_related()` for M2M/reverse FK
- `aggregate()`/`annotate()` instead of Python loops
- `[:limit]` or `.only()` on large queries
- Redis cache for aggregations (TTL: 5-15min)

### Security (OWASP Top 10)
```python
# WRONG - Model.objects.raw(f"SELECT * WHERE id = {user_input}")
# CORRECT - Model.objects.filter(id=user_input)
```
- NEVER SQL queries with string concatenation, NEVER log passwords/tokens
- Validate ALL inputs, verify permissions before every operation

### Test Quality
- **NO xfail** — Use `pytest.mark.skip(reason="TODO: ...")` instead
- **PostgreSQL** for all tests (not SQLite)
- Run full test suite before every commit

### Git Commits

**ALWAYS use** `git-commit-assistant` agent. **NEVER auto-push**.

```
type(scope): brief description

CHANGE: Technical explanation.
```

Types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `style`
Scope: Django app name (e.g. `simulation`, `agents`, `world`, `chat`, `llm-adapter`, `config`)

**FORBIDDEN**: References to Claude/AI, emoji/emoticon, Co-Authored-By, attribution lines. Commits must appear as entirely written by the human developer.

### Git Workflow

**Branch naming**: `feature/<short-description>`, `fix/<short-description>`, `refactor/<short-description>`

**Branch strategy**:

| Work item type | Base branch | PR target |
|----------------|-------------|-----------|
| Feature / Fix | `develop` | `develop` |
| Large feature with subtasks | feature branch from `develop` | feature branch → `develop` |
| Release | `develop` | `main` |

**Pull Request rules**:
- Title and description in English, complete and detailed
- Create as Draft until ready for review
- Code review must pass before merging
- Never force-push to shared branches

### Work Item Lifecycle

#### Phase 1 — Understand and design

1. **Analyze and plan** — Explore the codebase, understand the existing system, identify affected components. Produce a plan with architecture, trade-offs, and task list.
2. **Get user approval** — Wait for explicit approval before proceeding.

#### Phase 2 — Set up branch and PR

3. **Create the branch** — Branch name in English (e.g. `feature/agent-decision-pipeline`).
4. **Create Draft PR** — Title and description in English, complete and detailed.

#### Phase 3 — Implement

5. **Write code** — Follow all Agent Rules and Mandatory Rules.
6. **Code review (iterative)** — Before every commit, perform code review. All 8 review points must pass.
7. **Run tests locally** — `pytest --cov=epocha -v`. All must pass.
8. **Commit** — Use `git-commit-assistant` agent. NEVER auto-push.
9. **Push** — Push and verify CI pipeline passes.

Repeat steps 5-9 as needed.

#### Phase 4 — Complete the PR

10. **Final code review** — On full PR diff (all commits, not just last).
11. **Remove Draft status** — Mark PR as ready for review.
12. **Merge** — After approval.

### Writing Style (PRs, plans, documentation)

Text must read as if written by an experienced developer, not generated by AI:

- **Narrative, not mechanical**: write in a conversational form. Avoid endless bullet lists, repetitive structures, or telegraphic sentences.
- **Avoid AI-recognizable patterns**: never start every point with the same grammatical structure. Vary the form.
- **Direct and concrete tone**: like a colleague explaining to another colleague. No excessive formalism, no safety disclaimers, no obvious repetitions.
- **Proportion**: sections should have weight proportional to complexity. A trivial fix gets one line. A complex architecture gets a paragraph.
- **Context before detail**: briefly explain the why before listing the what.

## Conventions

### Settings
```python
from django.conf import settings
value = settings.EPOCHA_DEFAULT_LLM_PROVIDER
```

### LLM Calls
```python
from epocha.apps.llm_adapter.client import get_llm_client
client = get_llm_client()
response = client.complete(prompt="...", system_prompt="...")
```

### Django Signals
- Location: `{app}/signals.py` (NEVER in models.py)
- Registration via `AppConfig.ready()`

## Key Documents

| Document | When to consult |
|----------|-----------------|
| `docs/superpowers/specs/2026-03-22-epocha-design.md` | Full project design and vision |
| `docs/superpowers/plans/2026-03-23-mvp-implementation.md` | MVP implementation plan with tasks |
| `docs/letture-consigliate.md` | Recommended reading for contributors |

## Known Limitations

**AI Attribution**: FORBIDDEN any reference to Claude/AI in commits, comments, docstrings, docs, logs. No emoji/emoticon anywhere.

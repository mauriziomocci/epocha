# CLAUDE.md

Guide for Claude Code — Epocha: AI-powered civilization simulator.

## Project

- **Repository**: https://github.com/mauriziomocci/epocha
- **License**: Apache 2.0
- **Owner**: Maurizio Mocci (@mauriziomocci)
- **Status**: MVP in development (pre-release)

## Quick Reference

```bash
docker compose -f docker-compose.local.yml ps
docker compose -f docker-compose.local.yml up --build
pytest --cov=epocha -v
pytest epocha/apps/simulation/ -v
pytest -k "test_specific" -v
ruff check . && ruff format --check .
```

## Architecture

**Stack**: Django 5.x + DRF | PostgreSQL (future: + PostGIS + pgvector) | Celery + Redis | Django Channels | OpenAI-compatible LLM API

**Apps**: `epocha.apps.users` (auth), `simulation` (tick engine, events), `agents` (personality, memory, decisions), `world` (map, economy, zones), `chat` (WebSocket conversations), `llm_adapter` (provider abstraction)

**API** (`/api/v1/`): `users/`, `simulations/`, `agents/`, `worlds/`, `chat/`

**WebSocket**: `ws/simulation/<id>/` (real-time state), `ws/chat/<agent_id>/` (agent conversations)

**Celery**: `run_simulation_loop` (self-enqueuing tick loop), `process_agent_turn` (single agent decision), `generate_agent_response` (chat response)

**Files**:
- `config/` — Django settings, ASGI, Celery, URL routing
- `epocha/apps/` — All Django apps
- `epocha/common/` — Shared utilities (pagination, permissions, exceptions)
- `compose/` — Dockerfiles and entrypoints
- `requirements/` — base, local, production
- `docs/` — Design specs and implementation plans

---

## Agent Rules

### GOLDEN RULE: Scientific Method Above All

**THIS IS THE SUPREME RULE. It takes precedence over every other rule in this document and in `~/.claude/CLAUDE.md`. When any rule conflicts with this one, this one wins.**

Epocha is a scientific simulation. Every model, algorithm, formula, parameter, and behavioral rule must be grounded in established science, verified against sources, and subjected to adversarial review.

**The iterative quality loop**: all scientific issues identified at any level must be resolved, and a new review conducted after each resolution. The loop repeats until: all INCORRECT findings resolved, all UNJUSTIFIED parameters cited or documented as tunable heuristics, all INCONSISTENT findings reconciled, all MISSING assumptions documented. Partial resolution is not acceptable.

**This means:**
1. No formula without a cited source
2. No parameter without a justified value
3. No simplification without documented trade-offs
4. No assumption without explicit statement
5. No scientific code without adversarial review
6. No issue left unresolved — fix, re-review, repeat until clean
7. When science says one thing and convenience says another, science wins

### CRITICAL: The Build Map is the Source of Truth

**CRITICAL RULE**: `docs/build-map/epocha-build-map.html` is the authoritative record of what is built and what is not — the project board, the equivalent of a Jira for Epocha. It is published as an artifact at:

**https://claude.ai/code/artifact/c81c0d24-313c-474b-8440-c22275e1cb15**

It is **not a snapshot**. Keeping it current is mandatory, not optional, and not deferrable to "later". A build map that lags the code is worse than no build map, because it is trusted while being wrong.

**Update it whenever any of these happen — in the SAME session, and NOT deferred to "before closing":**

1. A phase changes status (not started -> in progress -> done)
2. An adversarial audit converges, or a new audit round opens
3. A module is wired into — or unwired from — the tick loop (`epocha/apps/simulation/engine.py`)
4. A whitepaper chapter is promoted from §8 (audit pending) to §4 (Methods)
5. A work item is opened, deferred to a separate branch, or closed
6. Any dependency between phases changes
7. **Any committed block of work makes something the map currently asserts untrue.** This is the catch-all and it fires far more often than 1-6. A phase already marked "in progress" still moves underneath that label: modules come into existence, user stories close, task counts advance, suite totals change. If a reader of the map would now be misled — "neither module exists yet" when one does, "911 passed" when it is 1002 — the map is stale and must be updated NOW, not at session end.

**The cadence that makes trigger 7 enforceable**: update the map at every checkpoint where a coherent block of work is committed — the close of a user story, a plan phase, an audit round. Not once per task, which is noise; not once per session, which is how it goes stale. If you are committing something worth a checkpoint, ask what the map now says that is no longer true.

**Why trigger 7 exists**: added 2026-07-17 after a real violation. Demography Plan 3 advanced from 0 to 23 of 47 tasks across nine code commits, closing two user stories and bringing a whole module into existence, while the map still read "neither module exists yet. Start at Plan 3." None of triggers 1-6 fired literally — the phase was already "in progress" — so the map silently lagged the code for an entire working session, which is precisely the failure the rule exists to prevent.

**Procedure (all four steps, in order):**

1. **Verify against reality first.** Check the status against the source tree and the whitepaper. NEVER inherit status from a memory note, from a handoff, or from the map's own previous state — all three go stale silently. Grep the tick engine to confirm a module is actually called, not merely defined and unit-tested.
2. **Edit the repo file** `docs/build-map/epocha-build-map.html`. That file is the source; the artifact is its rendering.
3. **Republish to the SAME URL**: call the Artifact tool with `file_path` set to the repo file and `url` set to the URL above. Omitting `url`, or publishing from a different path (e.g. a scratchpad copy), mints a NEW URL and forks the source of truth into two competing boards. This is the main failure mode — guard against it.
4. **Commit the file** together with the work it describes, never in a trailing "update the map" commit.

**How to view it.** The file is fully self-contained — inline CSS and JS, no external resources, no network calls. Open it directly, no server and no login required:

```bash
open docs/build-map/epocha-build-map.html
```

The artifact URL above is a shareable mirror of the same file, not a second source.

**Why it is not served by Django.** Considered and rejected on 2026-07-17. Serving it from the `dashboard` app would put the board behind a login (18 of the app's 25 views are auth-gated) and would couple project-level documentation to the simulation operator UI, whose single responsibility is operating and observing simulations — the dependency would point the wrong way, the DVT-544 anti-pattern. A project-level HTTP route was also rejected: it would buy a stable `localhost` URL at the cost of requiring the container to be up, for a file that already opens on its own. Do not re-propose either without a new reason.

**Precedence.** On any conflict about build status, the map wins over memory notes and over handoffs. The whitepaper remains authoritative for scientific content and for the audit status of its own chapters; the map records project-level progress across the 13 phases. The roadmap memory `project_roadmap_post_mvp.md` carries the phase scope, dependency order, and literature sources, and points AT the map for status — it must not duplicate status, or the two will drift.

**Why**: formalized 2026-07-17 at the user's explicit request ("è imperativo"). The roadmap memory had gone 94 days stale and misreported two load-bearing facts at once — it implied demography was unstarted when its models were audited but never wired into the tick loop, and it implied the economy integration was outstanding when it had shipped. The user lost sight of the project as a whole. A single verified board, updated as a matter of course, is the remedy.

### CRITICAL: Scientific Rigor

1. **Every mathematical model must cite its source** in the code (docstring or comment with reference).
2. **Parameters must have realistic values** from real data, with documented sources.
3. **Models must be validated** against known historical data or published results before merging.
4. **No magic numbers** — every constant must be named, documented, and justified.
5. **Game theory equilibria must use established algorithms**, not approximations unless documented.
6. **When in doubt, simplify rather than guess** — a simple correct model beats a complex guessed one.

### ABSOLUTE PRIORITY: Verify Every Assertion

Every scientific, technical, and architectural assertion must be verified against its source before being presented as fact.

**What to verify:**
1. Scientific citations: author, year, title, and the specific claim — no invented citations
2. Model parameters: verify the parameter actually works that way in the referenced model
3. Parameter ranges: verify against standard ranges in the discipline
4. Architectural claims: verify against actual documentation or established convention
5. Consistency with prior decisions: no contradictions with already-approved sections
6. **User assertions**: the user can also make mistakes. When a user assertion appears incorrect or inconsistent with the project's scientific foundations, emit a **WARNING** block and ask for confirmation: `**WARNING**: [explanation]. Do you confirm or should we reconsider?`. Never silently accept a user assertion that contradicts verified science.

**Why**: formalized 2026-04-12 after discovering six unverified assertions in a single data model proposal, and strengthened to challenge user errors after explicit user request.

### ABSOLUTE PRIORITY: Adversarial Scientific Audit

Every scientific model, formula, algorithm, constant, and assumption must undergo adversarial scientific review. Not optional, not deferrable.

**When to audit:**
1. Before committing any spec: after three-step design process, dispatch `critical-analyzer` subagent as a hostile scientific reviewer
2. Before committing scientific code: dispatch reviewer to verify every formula/constant against cited sources
3. When starting work on a feature touching scientific modules: audit existing code first
4. On user request: full audit of any module at any time

**Mandatory convergence loop:**
1. **Audit**: `critical-analyzer` produces INCORRECT/UNJUSTIFIED/INCONSISTENT/MISSING/VERIFIED report
2. **Fix**: resolve all INCORRECT and UNJUSTIFIED findings; document or resolve INCONSISTENT and MISSING
3. **Re-audit**: verify each original finding is resolved; check for new issues from fixes
4. **Convergence check**: if all findings RESOLVED and no new INCORRECT/UNJUSTIFIED → CONVERGED. Otherwise return to 2.
5. **Verdict**: explicitly state CONVERGED or NOT CONVERGED. No "close enough."

**What the auditor checks**: formula correctness vs cited source; constant values vs cited source; algorithm implementation vs claimed algorithm; simplification documentation; cross-module consistency of definitions and units.

**Why**: formalized 2026-04-12 at user's explicit request. Confirmation bias makes self-review insufficient — an adversarial reviewer with the mandate to find errors catches what self-review misses.

### CRITICAL: Three-Step Design Process

Before producing any design document, follow three mandatory steps. Skipping is forbidden regardless of perceived simplicity.

**Step 1 — Initial proposal**: present a first complete design (models, interfaces, data flow, trade-offs, dependencies). Do not write the spec file yet.

**Step 2 — First critical self-review**: immediately after, perform deep adversarial self-review. Look for: anti-patterns, missing edge cases, architectural smells (mutually-exclusive FKs, generic FKs, JSON blobs where relational serves, free-text where controlled vocab should exist), scalability issues, race conditions, security gaps. Write categorized findings (critical / important / minor / what works) with proposed fixes.

**Step 3 — Second self-review and consolidation**: review fixes from step 2 with fresh eyes. Look for fixes that introduced new problems or gaps not addressed in first review. Produce the final consolidated design. Only then write the spec document.

**Why**: formalized 2026-04-11 after producing a materially better Knowledge Graph design than a single-pass attempt.

### CRITICAL: Every Spec Includes a FAQ Section

Every design specification document must include a FAQ at the end covering:
- Design decisions: why X and not Y for every non-obvious choice
- Scientific rigor: how cited references map to implementation
- Integration: how the feature interacts with existing systems
- Performance and limits: latency, throughput, cost, hard caps
- Reproducibility: what is deterministic and what is not
- Comparison with alternatives: vs off-the-shelf libraries, other databases, competing approaches
- Operational concerns: privacy, failure modes, recovery
- Security: attack surface and mitigations

Write the FAQ in the voice of someone reviewing the spec critically. Each answer: 2-5 sentences. Add FAQ entries when the spec is revised.

### CRITICAL: Canonical 7-Phase Development Workflow

Every new subsystem, major feature, or spec MUST follow this workflow. Skipping phases or confusing gates is a rule violation.

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
   LIGHT GATE: human validation of the architectural plan
        ↓
4. TASK BREAKDOWN
   - Decompose plan into small tasks (see task-breakdown rule)
   - Each task: checkbox + detailed description + files + tests + commit msg
   - Granularity 2-5 minutes per task; no vague tasks
   LIGHT GATE: human validation of breakdown
   + Critical post-validation review (agent rereads with fresh eyes and raises
     residual doubts BEFORE touching code; scope: overlooked details likely to
     be lost during writing; NOT a second brainstorming, NOT a second audit)
        ↓
5. IMPLEMENTATION (task-by-task, sequential)
   For each task:
   - Write code exactly as described
   - Test the task (unit + regression)
   - 8-point code review (Mandatory Code Review)
   - Flag task as resolved; move to next ONLY after completion + flag
        ↓
6. GENERAL IMPLEMENTATION TEST
   - Full test suite (pytest --cov=epocha -v)
   - End-to-end integration test; zero failing tests; zero xfail
   HEAVY GATE:
   - Final adversarial review (critical-analyzer on CODE, not spec)
   - Explicit human validation of closure
        ↓
7. CLOSURE
   - Merge feature branch to develop (--no-ff)
   - Sync memory backup (docs/memory-backup/)
   - Push; update progress memory
```

**Gates**:
- **Heavy gates** (rigorous validation): REQUIREMENTS and FINAL — 2 per subsystem
- **Light gates** (quick coherence check on already-validated input): DESIGN and TASK BREAKDOWN

**Adversarial review fires at two distinct moments** with different scopes:
- Requirements gate: adversarial on the SPEC (scientific rigor, citations, formulas)
- Final gate: adversarial on the CODE (correctness, security, performance)

**Mapping to superpowers skills**:
- Phase 2: `superpowers:brainstorming`
- Phases 3+4: `superpowers:writing-plans`
- Phase 5: `superpowers:executing-plans` or `superpowers:subagent-driven-development`
- Phase 6: `superpowers:verification-before-completion`
- Phase 7: `superpowers:finishing-a-development-branch`

### CRITICAL: Model Selection Policy per Workflow Phase

| Phase | Model | Rationale |
|-------|-------|-----------|
| 1. Ideation | Opus | Conceptual exploration |
| 2. Requirements (brainstorming, spec, adversarial audit, convergence) | **Opus with extended thinking** | Scientific rigor, heavy gate — errors here propagate everywhere |
| 3. Architectural plan design | Opus | Architecture, cross-module trade-offs |
| 4. Task breakdown + post-validation review | Opus | Accurate decomposition, hidden gap detection |
| 5. Implementation (per-task) | **Sonnet** | Fully-specified tasks; 3-5× faster, ~5× cheaper |
| 5-bis. Per-task code review | Sonnet | 8-point review on atomic task |
| 5-ter. Final cross-task integration review | Opus | Architectural judgment, coherence across tasks |
| 6. General test + final adversarial code audit | **Opus** | Heavy final gate; hostile in-depth auditor |
| 7. Closure | Sonnet | Mechanical, deterministic operations |

**Escalation protocol (non-negotiable)**: during phase 5, if a task reveals an unforeseen edge case, wrong spec assumption, required undeclared refactor, incoherence with existing code, or scientific doubt — Sonnet does NOT invent a solution. It escalates to Opus. Sonnet resumes only after Opus revises the spec/plan/task.

Escalation trigger: any time the task requires a **strategic decision** rather than **specified execution**. Bright line: if "what do I do?" is not fully derivable from the task and spec, escalate.

**Haiku is NEVER used.** Too lightweight for Epocha's constraints (scientific rigor, OWASP, 8-point review, exact citations).

**Context preservation**: phase-5 tasks must be truly atomic (file-focused, narrow scope) for Sonnet to work without holding the entire plan in context. If a task requires holding the full plan + spec + codebase, split it further in phase 4.

### CRITICAL: Task Breakdown and Sequential Execution

Applies when a spec is approved and implementation planning begins. Plan files live under `docs/superpowers/plans/`.

**Rules**:
- Decompose into the smallest coherent tasks: 2-5 minutes, one atomic modification or tightly coupled file group
- Checkbox syntax: `- [ ] **Step N**: ...` compatible with `superpowers:writing-plans`
- No vague tasks. Never "Implement feature X" — always "Create file X with class Y containing method Z that does W, with tests T1-T3"
- Execute ONE task at a time; toggle flag to `- [x]`; move to next ONLY after flagging
- Do NOT batch tasks without intermediate flagging; do NOT skip ahead

**Typical scale for Epocha**: complex subsystem like Demography → 60-80 tasks across 3-5 sequential plans, 15-25 tasks per plan.

**Does NOT cover**: standalone edits not tied to a plan, answers to user questions, documentation commits unrelated to a plan, micro-maintenance.

### CRITICAL: Memory Backup Sync

Project memory lives in two locations that must stay in sync:

1. **Live memory**: `~/.claude/projects/-Users-mauriziomocci-Documents-workspace-Opensource-epocha/memory/`
2. **Versioned backup**: `docs/memory-backup/` in the git repository

After every significant work session:
```bash
cp ~/.claude/projects/-Users-mauriziomocci-Documents-workspace-Opensource-epocha/memory/*.md docs/memory-backup/
git add docs/memory-backup/ && git commit -m "docs: sync memory backup" && git push
```

When setting up on a new machine:
```bash
mkdir -p ~/.claude/projects/-Users-mauriziomocci-Documents-workspace-Opensource-epocha/memory/
cp docs/memory-backup/*.md ~/.claude/projects/-Users-mauriziomocci-Documents-workspace-Opensource-epocha/memory/
```

### Core Behavior — Language Override

**All code, comments, docstrings, logs, plan files, tests, README, CLAUDE.md, memory backup: English only.** This overrides the Italian default in `~/.claude/CLAUDE.md`.

**Exception**: spec files in `docs/superpowers/specs/` are written **in Italian only** (single authoritative version). English translation produced only when needed for paper publication.

### Code Comments and Docstrings

- **Language**: English, professional and precise tone. NO emoji/emoticon.
- **Write thorough comments** — Epocha is a scientific simulation, not a CRUD app. Code must be understandable by a researcher or future AI session without reading external papers.
- **What to comment**:
  - Every mathematical formula: name, source (author, year), variable definitions. Example: `# CES production function (Arrow et al. 1961). Q = A * [sum(alpha_i * X_i^rho)]^(1/rho), where rho = (sigma-1)/sigma`
  - Every constant or parameter: value, source, and why that value. Example: `# Price elasticity of subsistence goods: 0.3 (Houthakker & Taylor 1970, updated by Andreyeva et al. 2010)`
  - Every algorithm: what it does, complexity, known limitations, source. Example: `# Walrasian tatonnement (Walras 1874). Warning: may not converge with 3+ goods (Scarf 1960). Max iterations as safety net.`
  - Every simplification: what the full model would be, why simplified, what is lost.
  - Every assumption: stated explicitly.
- **What NOT to comment**: obvious code, Python idioms, Django boilerplate
- **Docstrings**: every module, class, and public function. Module docstrings cite primary sources. Class docstrings explain the model implemented.
- **Queryset dependencies**: document `select_related`/`prefetch_related` in class docstrings.

### Documentation Sync — Bilingual

After any code change, update documentation in the same commit:

- **Docstrings**: update if signature, behavior, or return value changed
- **README.md** (English, primary) AND **README.it.md** (Italian, companion) — both must stay in sync. README-relevant changes: architecture, stack, project rules, roadmap, setup/operational instructions, scientific references, validation benchmarks, public integration surface. Plain bug fixes, internal refactors, test-only commits do NOT trigger README update.
- **Scientific whitepapers**: **`docs/whitepaper/epocha-whitepaper.md`** (English) AND **`docs/whitepaper/epocha-whitepaper.it.md`** (Italian) — living documents. Scientific paper structure: numbered sections (Abstract, Introduction, Background, Methods, Implementation, Calibration, Validation, Discussion, Known Limitations, Conclusions, References, Appendices), numbered equations and figures, Author-Date citations, bibliography with DOI/URL, reproducibility notes. Every merge to develop touching scientific models, parameters, algorithms, calibration, or integration surface must update both whitepapers.

**Whitepaper-code doc-sync rule**: a PR that modifies code in any module listed below must update that module's chapter in **both** whitepapers (`docs/whitepaper/epocha-whitepaper.md` and `.it.md`) in the same commit, or state in the PR description why the change does not affect the model. Every chapter of §4 (Methods) is covered: a module reaches §4 only by converging its adversarial audit, and an audited chapter that drifts from its code is worse than an unaudited one, because it is trusted while being wrong.

| Whitepaper chapter | Code |
|---|---|
| §4.1 Demography | `epocha/apps/demography/{mortality,fertility,couple,inheritance,migration}.py` |
| §4.2 Economy — behavioral | `epocha/apps/economy/{expectations,credit,banking,property_market}.py` |
| §4.3 Reputation | `epocha/apps/agents/reputation.py` |
| §4.4 Rumor propagation | `epocha/apps/agents/{information_flow,distortion,belief,affinity}.py` |
| §4.5 Political institutions | `epocha/apps/world/{government,government_types,institutions,stratification,election}.py` |
| §4.6 Movement | `epocha/apps/agents/movement.py` |
| §4.7 Factions | `epocha/apps/agents/factions.py` |
| §4.8 Economy — base layer | `epocha/apps/economy/{production,market,distribution,monetary,initialization,engine}.py` |

Note the two traps in this mapping, both verified against the source tree on 2026-07-17: the §4.4 belief filter lives in `agents/belief.py`, not `belief_filter.py`, and §4.6 Movement lives in `agents/movement.py`, not under `world/`. The mapping is mirrored in the project memory `feedback_whitepaper_doc_sync.md` and in the Contributing section of both READMEs; all four copies change together. Extend the table whenever a module in §8 is promoted to §4 — the Knowledge Graph (§8.1) is the only one still pending.

### Mandatory Code Review — Epocha Overrides

The global 8-point code review (`~/.claude/CLAUDE.md`) applies with two Epocha-specific overrides:

- **Point 7 (Documentation)**: docstrings in **English** (not Italian), with scientific citations per the Code Comments rule above
- **Point 8 (Documentation sync)**: docstrings, **bilingual** READMEs, and **bilingual** whitepapers updated per the Documentation Sync rule above

---

## Mandatory Rules

### Code Quality Standards

1. **DRY** — no duplicated logic anywhere, no exceptions
2. **Pythonic code** — follow PEP 20 (The Zen of Python)
3. **Django best practices** — follow Two Scoops of Django (Feldroy): fat models, thin views; built-in tools first; small focused apps; `select_related`/`prefetch_related` proactively
4. **Reusable by design** — extract to mixins/base classes/utilities in `epocha/common/` where it makes sense; do not over-abstract
5. **Scalable architecture** — efficient queries at any scale; idempotent Celery tasks; state in database not in-memory globals

**Reference standards**: Django docs, Two Scoops of Django, PEP 8, PEP 20, DRF Best Practices

### Git Commits

**ALWAYS use** `git-commit-assistant` agent. **NEVER auto-push**.

Scope: `simulation`, `agents`, `world`, `chat`, `llm-adapter`, `config`

### Git Workflow

**Branch naming**: ALWAYS the timestamped form `<YYYYMMDD-HHMMSS>-<slug>` produced by `.specify/scripts/bash/create-new-feature.sh` through `/speckit-specify` — for example `20260715-132752-economy-base-layer-audit`. Never hand-craft a branch name, and never the legacy `feature/<short-description>` form. See **Spec-Driven Development MANDATORY** below, which is the authority on this.

| Work item type | Base branch | PR target |
|----------------|-------------|-----------|
| Feature / Fix | `develop` | `develop` |
| Large feature with subtasks | feature branch from `develop` | feature branch → `develop` |
| Release | `develop` | `main` |

**Pull Request rules** (GitHub, not GitLab):
- Title and description in English, complete and detailed
- Create as Draft until ready for review
- Never force-push to shared branches

### Work Item Lifecycle

1. `/speckit-specify "<description>"` — creates the timestamped branch and the `specs/<branch>/spec.md` scaffold
2. Analyze and plan — explore codebase, draft the spec, then `/speckit-plan` and `/speckit-tasks` for architecture, trade-offs, task list
3. Get user approval (heavy gate on the spec)
4. Create Draft PR on GitHub — title and description in English
5. Write code following all Agent Rules
6. 8-point code review before every commit
7. `pytest --cov=epocha -v` — all must pass
8. `git-commit-assistant` — NEVER auto-push; push and verify CI

---

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
| `docs/build-map/epocha-build-map.html` | **SOURCE OF TRUTH for build status.** What is done, in progress, not started, across the 13 phases; dependency order; "you are here". Read at the start of any session that touches project direction; **update it in the same session whenever status changes** (see the CRITICAL rule above). Artifact: https://claude.ai/code/artifact/c81c0d24-313c-474b-8440-c22275e1cb15 |
| `docs/superpowers/specs/2026-03-22-epocha-design.md` | Full project design and vision |
| `docs/superpowers/plans/2026-03-23-mvp-implementation.md` | MVP implementation plan with tasks |
| `docs/letture-consigliate.md` | Recommended reading for contributors |

## Known Limitations

## Django Development Style

This project intentionally follows **Two Scoops of Django** (fat models, thin views) rather than the HackSoftware Styleguide. This is a deliberate architectural choice documented in the project spec. Do **not** apply the HackSoftware services/selectors pattern here.

**AI Attribution**: FORBIDDEN any reference to Claude/AI in commits, comments, docstrings, docs, logs. No emoji/emoticon anywhere.

<!-- SPECKIT START -->
**Spec-Driven Development MANDATORY (GitHub Spec Kit, absolute from 2026-05-16)**

Every new work item — feature, fix campaign, refactor, deprecation — MUST use GitHub Spec Kit precisely and without exceptions. No ad-hoc spec/plan files outside Spec Kit.

Constitution authoritative at `.specify/memory/constitution.md` — supersedes code-quality portions of this file where they conflict; composes elsewhere.

**Mandatory authoring path**:
1. Start: `/speckit-specify "<description>"` → creates branch `<YYYYMMDD-HHMMSS>-<slug>` + `specs/<branch>/spec.md` scaffold
2. Spec draft: edit `specs/<branch>/spec.md` per `.specify/templates/spec-template.md`
3. `/speckit-plan` → `specs/<branch>/plan.md`
4. `/speckit-tasks` → `specs/<branch>/tasks.md`
5. `/speckit-implement` (or subagent-driven-development with tasks.md as input)
6. Heavy gate phase 2 + 6 adversarial audits via `critical-analyzer`
7. Closure: merge, frozen-at-commit pin if whitepaper touched, memory sync

**Optional Spec Kit skills**: `/speckit-clarify` (de-risk before plan), `/speckit-analyze` (cross-artifact consistency after tasks), `/speckit-checklist` (quality checklists after plan), `/speckit-constitution` (amend constitution).

**Branch naming**: ALWAYS timestamp `<YYYYMMDD-HHMMSS>-<slug>` produced by `.specify/scripts/bash/create-new-feature.sh`. Never ad-hoc branches like `feature/whatever` or `audit-repass/whatever`.

**Forbidden**: new files under `docs/superpowers/specs/` or `docs/superpowers/plans/`. These directories are READ-ONLY archival history of pre-2026-05-16 work. Continue editing legacy artifacts in place only when amending existing pre-2026-05-16 work.

**Legacy artifacts** (pre-2026-05-16, retain git history, no retroactive migration): Demography Plan 1+2, Economy base/behavioral, Reputation pre-promotion, Catch-up whitepaper, F-CAMPAIGN audit re-pass campaign plan.

**Composition with canonical 7-phase workflow**: Spec Kit is the authoring framework; the 7-phase workflow is the gating procedure (HEAVY GATE phases 2 + 6, LIGHT GATE phases 3 + 4). Adversarial scientific audit policy unchanged.

See memory `feedback_speckit_mandatory.md` for the absolute rule.

**Active feature plan**: `specs/20260806-112409-demography-design-defects/plan.md`
<!-- SPECKIT END -->

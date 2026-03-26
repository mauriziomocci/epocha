# Session Log: Initial Brainstorm and Project Setup

**Date:** 2026-03-23
**Participants:** Maurizio Mocci (project owner), Claude Code (AI assistant)
**Duration:** Extended session (~6+ hours)
**Outcome:** Complete project design, scaffold, MVP plan, and GitHub repository

---

## How the project was born

Maurizio described the idea as: "a virtual world where people are AI agents with specific personalities, stories, weaknesses, ambitions, leadership capabilities, positive and negative traits, active or passive in life — a real society that in certain situations behaves according to their personality, creating crises and situations, all to understand how society will evolve and also have the ability to interact, chat with various people."

The core inspiration is **Hari Seldon's psychohistory** from Asimov's Foundation saga — computational psychohistory using AI agents instead of mathematical equations.

## Name selection process

Several names were considered:

1. **Syntopia** (syn + topos = "place built together") — Liked by Maurizio, but web search revealed it was already heavily used: syntopia.ai (AI avatars for livestreaming), syntopia.in (software company), syntopia.bio (biotech)
2. **Aeonpolis** — Verified as available, considered but felt too long
3. **Kronopolis** — Initially chosen ("City of Time"), but a board game with that name exists on The Game Crafter
4. **Epocha** — Final choice. From Greek epochē (point of arrest, turning point). The final "a" gives it an Italian/Latin sound. Verified as available — "Epoch" is crowded but "Epocha" with the "a" is free. Also works well commercially: short, memorable, easy to pronounce in any language.

## Key design decisions and rationale

### Architecture: Modular Progressive (not microservices)

Three approaches were proposed:
- A) Monolith — too rigid for branching and scale
- B) Microservices — overkill for initial development
- **C) Modular Progressive (chosen)** — Django monolith with clean internal separation, extractable to services later. Celery already provides distributed processing.

Rationale: start fast with one deploy, but architecture is ready to scale. Pragmatic choice.

### Stack: Django/DRF

Maurizio's choice. He has 10 years of experience as a software engineer and prefers Django. No discussion needed.

### Time model: Hybrid

Not real-time continuous, not purely on-demand. The simulation runs autonomously but can be paused, accelerated, slowed down. User controls speed.

### Memory model: Realistic human memory

Considered: complete memory, realistic memory, configurable. Chose realistic because:
- Aligns with realism goal
- Creates authentic dynamics (distorted memories → false accusations → conflicts)
- Technically sustainable (complete memory with hundreds of agents over centuries would be enormous)

### Agent aggregation: Dynamic individual/group

Key insight from Maurizio: "an AI agent could also be a group of people." When homogeneous groups form, they become a single agent. This is both an optimization (fewer LLM calls) and realistic (groups develop collective identity). The hierarchy is fluid: individuals emerge from groups, subgroups form within groups, groups split and merge.

### Events and crises: Emergent + injectable + rule-based

Not purely emergent (too unpredictable), not purely scripted (not interesting). A mix where:
- Rules create conditions
- Agents react to conditions
- Crises emerge naturally
- The user can inject events as "experimenter" (social experiment approach)

### Economy: Full complexity but selectable levels

User wanted full economic simulation but also the ability to simplify depending on the experiment. Solution: three levels (simplified, base, complete) chosen before starting the simulation.

### Simulation branching with comparison

Inspired by Seldon's psychohistory: fork a simulation at a point in time, change one variable, compare outcomes. This is the "control group vs experimental group" approach.

### Input system: Express mode inspired by MiroFish

MiroFish's success taught us that zero-friction input is critical. Solution: two modes:
- Express: one text field + "Go" (like MiroFish)
- Advanced: full configuration for power users

Express is not a reduced version — it uses the same engine, AI makes all configuration decisions.

### Scientific Models: Hybrid approach

Critical differentiator from MiroFish (which has NO mathematical models). Epocha uses:
- Mathematical models for macro trends (economy, demographics, epidemics, climate)
- LLM for behavioral realism (agent decisions)
- The two feed into each other in a loop

Models calibrated on real historical data + peer-reviewed papers.

### Knowledge Engine: Web research before simulation

The system cannot credibly simulate technological/scientific evolution without deep domain knowledge. Solution: before starting, the Knowledge Engine researches relevant domains via web, structures knowledge in a dependency graph, and uses it throughout the simulation.

For future projections (2026 → 3026): researches current state of the world, applies plausibility framework with bifurcation points.

### Reproducibility: Statistical, not exact

Initial design claimed exact reproducibility (same seed = same simulation). Spec review correctly identified this as impossible with LLMs. Revised to:
- Statistical reproducibility (same parameters → similar macro outcomes)
- Full replay from decision logs (deterministic)
- Seed for non-LLM randomness

## Inspirations discussed

### From Asimov (Foundation saga)
- Seldon Crises: automatic detection of civilizational tipping points
- Second Foundation: invisible manipulation mode for the user
- Robotics Laws: AI within the simulation following configurable rules
- Gaia: possibility of collective consciousness emerging
- Galactic Encyclopedia: historical record queryable in natural language

### From Star Trek
- Prime Directive: ethics of interference with less advanced civilizations
- Post-scarcity economy: what happens when technology eliminates scarcity
- Federation vs Empire: two models of galactic organization

### From Star Wars
- Megacorporations as political entities
- Underground economy and piracy
- Ancient civilizations and ruins (discoverable lost technology)

### From Blade Runner / Dystopias
- Bioengineering and transhumanism
- Surveillance and social control
- Systemic environmental collapse

### From Dune
- Critical resource monopoly
- Cultures forged by environment

### From The Expanse
- Biological divergence of humans in different gravity
- Core vs Periphery (space colonialism)

### From Cyberpunk
- Parallel virtual worlds (metaverse as society)
- Digital immortality and its social consequences

### From real futurology
- Fermi's Great Filter
- Kardashev Scale

### From real history
- Vico's corsi e ricorsi (historical cycles)
- Ibn Khaldun's asabiyyah (social cohesion)
- Polybius' anacyclosis (government cycles)
- Kondratiev waves (economic cycles)
- Detailed historical patterns: Roman Empire, Mongol invasions, World Wars, revolutions, religious movements, totalitarian regimes

### From "The Man in the High Castle" (Philip K. Dick)
- Alternate history scenarios as a primary use case
- Added specific examples to README

## MiroFish analysis

Analyzed MiroFish (github.com/666ghj/MiroFish) in depth:
- 33K+ GitHub stars, $4.1M investment in 24 hours
- Built in 10 days by a student
- Uses OASIS engine, Zep Cloud for memory, Flask backend
- Key strength: zero-friction input (document → simulation → report)
- Key weakness: NO mathematical models, NO scientific validation, NO reproducibility

Decision: do NOT cite MiroFish in README (competitor). Learn from its success (simplicity of entry) but differentiate through scientific rigor.

## LLM provider decisions

- Subscription plans (Claude Max, ChatGPT Plus) are NOT usable programmatically — Anthropic explicitly blocked workarounds in January 2026
- Solution: OpenAI-compatible API with configurable base_url
- Default for development: Google Gemini free tier (1000 req/day, $0)
- Three-tier model routing for production (90% local, 8% cheap API, 2% premium)
- MCP Server for integration with Claude Code and other AI tools

## Project setup decisions

- **License:** Apache 2.0 (same as MiroFish, allows wide adoption, patent protection)
- **Language:** All code, comments, docstrings, commits, documentation in English
- **Django structure:** Inspired by cookiecutter-django but stripped down (removed allauth, crispy-forms, templates, Mailhog, Sphinx, WhiteNoise)
- **Git workflow:** main (releases) → develop (integration) → feature/* (work branches)
- **Default branch:** develop (changed from main on GitHub)
- **CLAUDE.md:** Adapted from RapsodiaTrace, in English, gitignored (personal, not shared)
- **README:** Bilingual (English + Italian) with language switcher

## Feedback and self-assessment

Maurizio asked for honest feedback on his architecture skills. Assessment:
- **Strengths:** Exceptional product vision, interdisciplinary thinking, strong technical intuition (PostGIS, Docker, MCP), ability to connect domains (science, history, technology, sociology)
- **Areas for growth:** Architectural decisions were largely delegated, tendency to accept all scope expansions without trade-off discussion
- **Context revealed later:** Maurizio is a software engineer with 10 years of experience who was deliberately delegating while multitasking on other work — not a lack of skill but an efficiency choice
- **Key trait:** Accepts and values honest constructive criticism

## Spec review results

Spec review identified:
- **4 critical issues:** Missing MVP, unrealistic cost estimates, no data model, impossible reproducibility claim
- **8 important issues:** No test strategy, no monitoring, no error handling, Knowledge Engine too ambitious, no security section, performance not analyzed
- **6 suggestions:** Simulation-first approach, non-goals, API versioning, data migration

All critical and important issues were addressed in the design doc.

## Post-session additions (2026-03-25)

### Simulation persistence and shutdown behavior

Decision: simulation state is persisted in PostgreSQL at every completed tick. If the system shuts down (computer off, Docker stopped, crash), the simulation pauses at the last completed tick and resumes cleanly on restart.

Implementation:
- `acks_late=True` on Celery tasks: task acknowledged only after completion, re-delivered if worker dies mid-tick
- `stop_grace_period: 60s` (local) / `120s` (production) in Docker Compose: allows current tick to finish before container stops
- Celery worker started with `--without-mingle --without-gossip` for faster boot and cleaner shutdown
- Two deployment modes: local (stops with computer) and cloud (runs 24/7 on server/VPS)

### Additional design decisions (2026-03-25 / 2026-03-26)

**Adaptive time resolution:** Simulation ticks cover variable time spans (hours to centuries). The system automatically slows down during crises and speeds up during peaceful periods. At low resolution, only mathematical models run. At high resolution, every agent thinks via LLM.

**Chat time adaptation:** When the user opens a chat, the simulation automatically adjusts speed to prevent agents from aging/dying between messages. Observer mode freezes time, Inhabitant/God mode slows it, Second Foundation pauses it.

**Timeline navigation:** Full media-player controls (play, pause, rewind, fast forward, go to start/end). Auto-milestones for significant events. Manual bookmarks with labels. Complete state snapshots at every milestone for instant time-travel and forking.

**Hierarchical society orchestration:** Three-phase tick cycle (top-down cascade → bottom-up feedback → consolidation). Each hierarchy level has its own processing frequency. Events propagate with delay. Conflict between levels drives rebellions and civil wars. Leadership emerges from below.

**Comprehensive political systems:** 12 government types with full operational mechanics (democracy, autocracy, democratura, theocracy, kleptocracy, etc.). Transition patterns between systems. Social stratification with 6 classes. Crime system (individual, organized, terrorism, corruption). 7 institutional types with health indicators.

**Living relationships (Task 19):** Relationships form from interactions, evolve over time, flip on betrayal, decay when unused. Agent decisions include relationship context. Factions and alliances emerge naturally.

**High-value MVP additions:** Document upload (PDF, DOCX, MD, TXT), real-time LLM cost tracking, auto-generated narrative report, WebSocket event feed.

**Subagent for critical decisions:** Level 4 in model routing — subagents with tools for multi-step reasoning during Seldon Crises and leader decisions. Deferred to v0.2 (too complex for MVP debugging).

**LLM bias correction:** Configurable parameter to counteract LLM tendency toward polarization and herd behavior.

---

## Current state at end of session

- **Repository:** github.com/mauriziomocci/epocha (Apache 2.0)
- **Branch:** feature/mvp (active), develop (default), main (releases)
- **Structure:** 100+ files, complete Django scaffold with 6 apps
- **Design doc:** ~3000+ lines covering everything from agent personality to interstellar civilization
- **MVP plan:** 20 tasks (Task 0-19), estimated 10-20 hours
- **README:** Bilingual (EN + IT), professional, comprehensive
- **Docker:** Local + Production setups ready (Nginx, multi-stage, health checks)
- **LLM:** Configured for Google Gemini free tier
- **Next step:** Execute MVP plan starting from Task 0 (migrations)

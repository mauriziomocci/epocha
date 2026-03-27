# Epocha

English | [Italiano](README.it.md)

[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/)
[![Status](https://img.shields.io/badge/status-MVP%20in%20development-yellow.svg)]()
[![Django](https://img.shields.io/badge/django-5.x-green.svg)](https://www.djangoproject.com/)

**An AI-powered civilization simulator. Watch societies emerge, evolve, collapse, and be reborn.**

---

## Overview

Epocha is a computational take on psychohistory — the fictional discipline from Asimov's Foundation saga that predicts the behavior of civilizations through mathematical modeling of mass dynamics. Where Hari Seldon used equations, Epocha uses AI agents.

Hundreds of autonomous agents — each with a distinct personality, memory, fears, ambitions, and social relationships — live inside a simulated world with a working economy, political systems, geographic constraints, and the full messy complexity of human society. Crises emerge from the bottom up. Alliances form and fracture. Technological revolutions reshape the social order. Dark ages follow golden ages. A single charismatic individual can alter the trajectory of an entire civilization.

The simulation can span timescales from a single village in its first decade to an interstellar civilization spread across star systems over millennia. At every scale, the same engine runs: agents making decisions, groups aggregating and fragmenting, societies rising and falling.

The user is not a passive observer. Depending on the chosen interaction mode, you can watch the simulation unfold from a distance, step inside it as an inhabitant, inject events and characters as a god-like presence, or guide history from the shadows like Asimov's Second Foundation — nudging civilizations toward stability without revealing your hand.

---

## Key Features

### Agents

- **Big Five personality model** — Each agent is defined by openness, conscientiousness, extraversion, agreeableness, and neuroticism. These traits are not cosmetic: they drive every decision the agent makes.
- **Realistic memory with emotional weight** — Recent memories are vivid. Traumatic events persist for a lifetime. Ordinary memories fade and distort over time. Secondhand information is less reliable than direct experience.
- **Full lifecycle** — Agents age, get sick, fall in love, form families, accumulate wealth or debt, and die. Children inherit cultural and genetic traits with variation. Economic and social status passes between generations.
- **Dynamic aggregation** — Individuals coalesce into groups when they share values and goals. Groups fragment when internal tension exceeds a threshold. Leaders emerge from the crowd and can be tracked individually. The hierarchy scales from family to faction to nation to civilization to interstellar federation.

### World Simulation

- **Multi-scale from village to galaxy** — The same architecture handles a medieval hamlet and a galactic federation. The simulation scales seamlessly from individual decisions to interstellar diplomacy.
- **Geographic foundation** — The world is built on a spatial model (PostGIS). Agents have real positions. Events propagate across geography. Proximity determines social interaction. Epidemics, revolts, and disasters have epicenters and spread through space.
- **Economy at configurable complexity** — From a simple wellbeing index to full supply-and-demand markets with inflation, unemployment, class structure, debt, and trade between regions.
- **Political systems** — Elections, coups, revolutions, and the slow decay of institutions. Governments respond to public trust, resource pressure, and the ambitions of powerful agents.
- **Entropy and decay** — Infrastructure degrades without maintenance. Knowledge gets lost between generations. Institutions corrupt. Civilizations that expand faster than they can sustain themselves collapse. Dark ages are followed by renaissances.

### Scientific Models

Epocha takes a hybrid approach: mathematical models handle macroscopic trends, and agents provide behavioral realism. Neither alone is sufficient.

The models are calibrated against real historical data before the simulation starts. If a simulation begins in 12th century Europe, the demographic, economic, and climatic parameters reflect the actual conditions of that period.

Supported scientific domains include macroeconomics (Phillips curve, IS-LM, Fisher equation), inequality (Gini coefficient, Lorenz curve), epidemiology (SIR/SEIR models), climate (radiative balance, feedback loops), social network dynamics (Granovetter, information cascades), military conflict (Lanchester attrition), resource depletion (Hubbert curve), and — when the simulation reaches spacefaring scales — orbital mechanics (Kepler, Tsiolkovsky, Hohmann transfers), the Drake equation, and exoplanet habitability models.

Scientific rigor is configurable: simplified (qualitative rules), standard (calibrated mathematical models), or rigorous (full equations from peer-reviewed papers with cross-validation).

### Knowledge Engine

Before a simulation starts, the Knowledge Engine builds a structured knowledge base by researching the relevant domains — history, science, economics, sociology, political science, climate, and more. This is stored as a dependency graph: every discovery or innovation has prerequisites, enabling conditions, probabilities of emergence, catalysts, and downstream consequences.

During the simulation, the engine evaluates which discoveries are "ripe" given the current state of the civilization, calculates emergence probabilities, and triggers innovations through credible agents when conditions are met.

For future-projection simulations starting from the present day, the engine researches the current geopolitical, economic, demographic, and technological state of the world and applies a plausibility framework: near-term extrapolation from real trends, mid-term branching scenarios, long-term emergent consequences.

The engine connects to external sources including Wikipedia, arXiv, World Bank data, IPCC climate projections, and the NASA Exoplanet Archive.

### Interaction Modes

| Mode | Identity | Effect on the simulation |
|------|----------|--------------------------|
| Observer | Invisible interviewer | Conversations do not alter the world |
| Inhabitant | A character living in the world | Your actions have real consequences |
| God | A superior entity | You can issue commands, alter rules, trigger events |
| Second Foundation | An unseen guide | You nudge history from behind the scenes |

### Real-Time Chat via WebSocket

Click any agent on the map to open a direct conversation. The agent responds in character — consistent with their personality, emotional state, memories, and current circumstances. Talk to groups gathered in a location and watch social dynamics play out in real time.

In God mode, agents react to your presence according to their nature: a rebel defies you, a devout follower obeys without question, a rationalist challenges your existence.

### Psychohistorical Dashboard

The analytics layer surfaces patterns that span generations:

- **Seldon Crises** — The system detects and names civilizational tipping points as they develop, tracking their causes, probable outcomes, and the key agents driving them.
- **Kardashev scale** — Tracks the civilization's energy mastery and technological reach over time.
- **Historical cycles** — Detects recurring patterns: inequality surges preceding revolts, expansion followed by over-extension and collapse, cultural golden ages following periods of crisis.
- **Branch comparison** — Run two versions of the same civilization with different variables and overlay their trajectories. See what changed and when the divergence became irreversible.

### Galactic Encyclopedia

The simulation maintains a complete historical record of everything that happens: every discovery, crisis, political transition, war, and cultural movement — with causes, agents involved, and consequences. Query this record in natural language: "What were the main causes of the 2087 collapse?" or "Who were the most influential individuals of the third century?"

### Branching Simulations

Fork any simulation at any point in time. The fork creates an independent world that shares history up to that moment. From there, inject a different variable — a dictator, a plague, a technological breakthrough — and compare how the two timelines diverge. Multiple forks from the same origin enable controlled experiments at civilizational scale.

### Express Mode

A single text field. Type a prompt and get a world.

```
"Simulate Italy from 2026 to 2126, focusing on the impact of AI on the labor market."

"A medieval society with two rival villages on opposite banks of a river, scarce
resources, and religious tension between a solar cult and a lunar cult."

"What would have happened if the Roman Empire had not collapsed in 476?"

"Europe in 1945, but the Axis powers won the war. Simulate 80 years of this
alternate history: politics, economy, resistance movements, cultural evolution."

"A small island nation discovers a massive energy source. Simulate 500 years:
who controls it, what wars it causes, how the society transforms."
```

The system analyzes the input, builds the knowledge base, generates the world, selects optimal parameters, and starts the simulation. No configuration required. Express mode uses the same engine as the advanced mode — the system makes all the configuration decisions instead of you.

### Multi-Format Input

The Express endpoint accepts:

| Format | How it works |
|--------|-------------|
| Plain text | Direct description in the API request |
| Markdown (.md) | Structure is preserved as world-building context |
| PDF (.pdf) | Text extracted and analyzed (history books, academic papers, news) |
| Plain text (.txt) | Read as-is |
| URL | Page content is fetched and extracted |

An optional prompt alongside any file or URL lets you add instructions: "Focus on the economic dynamics", "Simulate for 500 years", "Add a revolutionary leader after 50 years."

### MCP Server

Epocha exposes a Model Context Protocol server. Any MCP-compatible client can control and observe simulations without opening the web interface.

Supported MCP tools include: creating simulations, controlling playback, chatting with agents, injecting characters or events, modifying world rules, forking branches, comparing timelines, querying the encyclopedia, reading analytics and the Seldon Crisis feed, and exporting simulation data.

Compatible clients include Claude Code, Cursor, Windsurf, and any custom MCP client. Multiple clients can be connected simultaneously — multiplayer via MCP.

### Plugin Architecture

Every scientific model and simulation module is a plugin with a standard interface. Contributors do not need to know Django or the internal architecture. A sociologist can provide equations, calibration data, and parameters in the standard format and the system integrates them automatically.

Each plugin contribution goes through a four-stage pipeline: automated technical validation (tests, linting, interface compliance), automated scientific validation (equation correctness, parameter ranges, calibration against historical data), integration validation (no regressions, plausible simulation output), and human review by maintainers and domain experts.

### Collaborative and Multiplayer Worlds

Multiple users can participate in the same simulation with different roles: creator (full control), co-experimenter (inject events and characters, fork, observe), observer (read-only access and agent chat), inhabitant (live inside the world as a character), or local god (control a specific region or civilization).

Asynchronous collaboration (fork and compare), synchronous shared worlds, and competitive multiplayer (each user controls a different civilization in the same world) are all supported.

### Reproducibility

Every simulation is reproducible. The system produces statistical reproducibility (same parameters, statistically similar macro outcomes) and full replay capability (exact reproduction from the event log). Simulations can be exported as a portable package and shared with exact parameters for other researchers to replicate or extend.

---

## Use Cases

**Alternate history** — What if the Axis powers had won World War II? What if the Library of Alexandria had survived? What if the Roman Empire had discovered printing before collapse? Fork history at a specific moment, change one variable, and watch the consequences unfold over decades or centuries. Simulate resistance movements, cultural shifts, economic restructuring, and political evolution in worlds that never existed but could have.

**Future projection** — Start from 2026 and simulate to 2126 or 3026. The Knowledge Engine grounds the first decades in current real-world data and trend extrapolations, then follows the emergent consequences wherever the simulation leads. Watch the plausible futures of AI disruption, climate pressure, energy transitions, and demographic shifts play out through the lives of individual agents.

**Social experiments** — Inject a charismatic authoritarian into a stable democracy and observe the decades-long path to autocracy. Trigger an epidemic and watch the social fractures it reveals. Introduce a radical philosophical movement and trace how it propagates through the information network. Quantify how single individuals alter civilizational trajectories.

**Education** — A student can experience the dynamics of the French Revolution from the inside rather than reading about them. Sociology instructors can demonstrate inequality feedback loops in real time. Economics courses can watch demand-supply dynamics, inflation, and financial crises emerge from the behavior of individual agents without a textbook.

**Worldbuilding for fiction and games** — Generate a rich, internally consistent world history with a single prompt. The Galactic Encyclopedia provides a queryable record of everything that happened, ready to inform novels, tabletop campaigns, or game narratives with coherent lore.

**Social science research** — Run controlled experiments at civilizational scale. Hold all variables constant except one. Run a hundred parallel forks. Aggregate the results. Crowdsourced experiments (same starting world, different interventions, statistical comparison of outcomes across all participants) enable a form of community social science that is otherwise impossible.

---

## Architecture

Epocha is a modular Django application designed to be extracted into independent services when scale demands it.

```
+---------------------------------------------------------+
|                    FRONTEND (React)                      |
|  +----------+ +----------+ +----------+ +------------+  |
|  | 2D Map   | |   Chat   | |  Graph   | |  Analytics |  |
|  | (Pixi.js)| |  Panel   | |(Sigma.js)| |  Dashboard |  |
|  +----------+ +----------+ +----------+ +------------+  |
|                      WebSocket + REST                    |
+--------------------------+------------------------------+
                           |
+--------------------------+------------------------------+
|              DJANGO / DRF (Orchestrator)                 |
|                                                          |
|  +--------------+  +--------------+  +--------------+   |
|  |  Simulation  |  |    Agents    |  |    World     |   |
|  |    Engine    |  |    Module    |  |    Module    |   |
|  |              |  |              |  |              |   |
|  | - Tick loop  |  | - Personality|  | - Economy    |   |
|  | - Time       |  | - Memory     |  | - Resources  |   |
|  | - Branching  |  | - Decisions  |  | - Politics   |   |
|  | - Auto-stop  |  | - Aggregation|  | - Geography  |   |
|  +--------------+  +--------------+  +--------------+   |
|                          |                               |
|  +-----------------------------------------------+      |
|  |              Event Bus (internal)              |      |
|  +------------------------+----------------------+      |
|                           |                              |
|  +--------+ +--------+ +--------+ +--------+ +--------+ |
|  |  Chat  | | Info   | |Analyti-| |Knowled-| |Scienti-| |
|  | Module | | Flow   | |  cs    | |ge Eng. | |fic Mod.| |
|  |        | |        | |        | |        | |        | |
|  | -1-a-1 | |-Rumor  | |-Trends | |-Research| |-Equat. | |
|  | -Groups| |-Media  | |-Cycles | |-K.Graph| |-Papers | |
|  | -Modes | |-Distort| |-Compare| |-Validate|-Calibr. | |
|  +--------+ +--------+ +--------+ +--------+ +--------+ |
+--------------------------+------------------------------+
                           |
            +--------------+--------------+
            |              |              |
       +----+----+   +----+----+   +-----+-----+
       | Celery  |   |  Redis  |   | PostgreSQL |
       | Workers |   |         |   |            |
       |         |   | - State |   | - Agents   |
       | - Agent |   | - Cache |   | - History  |
       |   AI    |   | - PubSub|   | - Branches |
       | - Tick  |   |         |   | - Analytics|
       |   proc. |   |         |   |            |
       +----+----+   +---------+   +------------+
            |
       +----+------------------------+
       |   LLM Adapter Layer         |
       |                             |
       | +-------+ +-------+        |
       | | Local | |  API  | ...    |
       | | vLLM  | |Gemini |        |
       | +-------+ +-------+        |
       |                             |
       | - Rate limiting             |
       | - Quota management          |
       | - Fallback chain            |
       | - Cost tracking             |
       +-----------------------------+
```

### Tech Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Backend | Django 5.x + Django REST Framework | Core application and REST API |
| Async tasks | Celery + Redis (broker) | Parallel agent processing, tick loop |
| Database | PostgreSQL (future: + PostGIS + pgvector) | Agent data, history, branches, knowledge base |
| Cache / Real-time | Redis | Simulation state, pub/sub for WebSocket |
| WebSocket | Django Channels + Daphne | Real-time updates and agent chat |
| Frontend | React | Interactive UI |
| 2D Map | Pixi.js (WebGL) | High-performance sprite rendering |
| Relationship graph | Sigma.js (WebGL) | Large social graph visualization |
| Charts | Recharts | Analytics dashboard |
| State management | Zustand | Lightweight frontend state |
| LLM | Provider-agnostic adapter | Any OpenAI-compatible API |
| Integration | Model Context Protocol | MCP server + client for external sources |

---

## Quick Start

### Prerequisites

- Docker and Docker Compose

### Setup

**1. Clone the repository**

```bash
git clone https://github.com/mauriziomocci/epocha.git
cd epocha
```

**2. Configure environment variables**

```bash
cp .env.example .envs/.local/.django
cp .env.postgres.example .envs/.local/.postgres
```

Edit `.envs/.local/.django` and set your LLM API key. The default configuration uses Google Gemini, which has a free tier with 1,000 requests per day — sufficient for development and testing.

```
EPOCHA_LLM_PROVIDER=openai
EPOCHA_LLM_API_KEY=your-gemini-api-key-here
EPOCHA_LLM_MODEL=gemini-2.5-flash-lite
EPOCHA_LLM_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/
```

**3. Start the stack**

```bash
docker compose -f docker-compose.local.yml up --build
```

This starts Django (port 8000), PostgreSQL, Redis, a Celery worker, and Celery Beat.

**4. Initialize the database**

```bash
docker compose -f docker-compose.local.yml exec web python manage.py migrate
docker compose -f docker-compose.local.yml exec web python manage.py createsuperuser
```

**5. Create your first simulation**

```bash
curl -X POST http://localhost:8000/api/v1/simulations/express/ \
  -H "Authorization: Bearer <your-token>" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "A medieval village with 30 people, two rival families, and a disputed mill"}'
```

**6. Connect to an agent via WebSocket**

```
ws://localhost:8000/ws/chat/<agent_id>/
```

---

## LLM Provider Setup

Epocha uses the OpenAI SDK with a configurable `base_url`, making it compatible with any OpenAI-compatible API without code changes. Switch providers by editing environment variables only.

| Provider | `EPOCHA_LLM_BASE_URL` | Recommended model | Free tier |
|----------|----------------------|-------------------|-----------|
| Google Gemini | `https://generativelanguage.googleapis.com/v1beta/openai/` | `gemini-2.5-flash-lite` | 1,000 req/day |
| Groq | `https://api.groq.com/openai/v1` | `llama-3.1-8b-instant` | Limited |
| OpenRouter | `https://openrouter.ai/api/v1` | Various free models | 200 req/day |
| OpenAI | *(leave empty)* | `gpt-4o-mini` | Initial credits |
| Together AI | `https://api.together.xyz/v1` | Various | Initial credits |
| Mistral | `https://api.mistral.ai/v1` | `mistral-small-latest` | No |
| LM Studio | `http://localhost:1234/v1` | `qwen3-8b`, `gemma3-4b` | Unlimited, fully offline |
| Ollama | `http://localhost:11434/v1` | `qwen2.5:7b` | Unlimited |

**Get a free Gemini API key:** [aistudio.google.com/apikey](https://aistudio.google.com/apikey)

**Run models locally with LM Studio (free, offline, no limits):**

1. Download and install from [lmstudio.ai](https://lmstudio.ai/)
2. Open LM Studio, go to the **Discover** tab and search for `qwen3-8b` (or `gemma3-4b` for lighter hardware)
3. Click **Download** and wait for the model to finish downloading
4. Go to the **Developer** tab (or **Local Server** in older versions)
5. Select the downloaded model from the dropdown
6. Click **Start Server** — it will start on `http://localhost:1234`
7. Configure Epocha's `.envs/.local/.django`:

```
EPOCHA_LLM_API_KEY=lm-studio
EPOCHA_LLM_MODEL=qwen3-8b
EPOCHA_LLM_BASE_URL=http://localhost:1234/v1
```

The server must be running whenever the simulation is active. LM Studio runs on macOS (Apple Silicon recommended), Windows, and Linux.

**Minimum hardware for agent simulation:**
- 8B models (Qwen3, Llama 3.1): 8 GB RAM, any modern CPU. GPU recommended but not required.
- 4B models (Gemma3): 4 GB RAM, runs on most machines.

### Capacity estimate with Gemini free tier

With 20 agents and 1,000 requests per day:
- World generation: approximately 1 request
- Per simulation tick: approximately 20 requests (one per agent)
- Approximately 50 ticks per day within free limits
- Budget for agent chat: approximately 100 requests per day

This is more than sufficient for development and exploration. For longer simulations, either upgrade to a paid tier or switch to a provider with higher limits.

### Three-tier model routing (production)

For larger simulations, the LLM adapter routes requests by decision complexity:

| Tier | Share of calls | Decision type | Example models |
|------|---------------|---------------|----------------|
| Local | ~90% | Routine actions, movement, simple reactions | Ollama + Qwen 7B |
| Economy API | ~8% | Social decisions, commerce, voting | Gemini Flash-Lite, GPT-4o-mini |
| Premium API | ~2% | Crises, leadership moments, historical turning points | Gemini Pro, GPT-4o |

This keeps costs manageable for large-scale simulations while reserving stronger models for decisions that matter.

---

## Project Status

Epocha is currently in active MVP development. The backend is being built and validated first; the frontend will follow.

The MVP delivers: world generation from a text prompt, 20-50 AI agents with personality and memory, a tick-based simulation engine, real-time WebSocket chat with any agent, and a REST API for all core operations.

See the full implementation plan at [`docs/superpowers/plans/2026-03-23-mvp-implementation.md`](docs/superpowers/plans/2026-03-23-mvp-implementation.md).

---

## Roadmap

| Version | Scope | Status |
|---------|-------|--------|
| v0.1 — MVP | Backend engine, 20-50 agents, Express mode, WebSocket chat, REST API | In development |
| v0.2 | Frontend map (Pixi.js), agent graph (Sigma.js), analytics dashboard | Planned |
| v0.3 | Knowledge Engine, web research, knowledge graph, pre-simulation calibration | Planned |
| v0.4 | Scientific models integration (economy, epidemiology, demographics, climate) | Planned |
| v0.5 | Branching/forking, branch comparison, Seldon Crisis detection | Planned |
| v0.6 | MCP server, tool exposure, external client support | Planned |
| v0.7 | Plugin architecture, contribution pipeline, validation automation | Planned |
| v0.8 | Multiplayer worlds, collaborative simulation, permission system | Planned |
| v0.9 | Spacefaring scale, orbital mechanics, interstellar expansion | Planned |
| v1.0 | Full vision: all interaction modes, Galactic Encyclopedia, community features | Planned |

The design document at [`docs/superpowers/specs/2026-03-22-epocha-design.md`](docs/superpowers/specs/2026-03-22-epocha-design.md) describes the complete v1.0 vision in detail.

---

## Contributing

Epocha is open source and built to be extended. Contributions are welcome from developers, scientists, historians, economists, sociologists, and anyone with domain expertise relevant to how civilizations actually work.

### Getting started

```bash
# Install development dependencies
pip install -r requirements/local.txt

# Run the test suite
pytest --cov=epocha -v

# Code quality
ruff check .
ruff format --check .
```

### Plugin contributions

The plugin system is the primary extension point. A plugin is a self-contained module with a standard interface:

```
plugin-name/
+-- metadata.json          # name, author, version, domain, dependencies
+-- model.py               # implementation (standard Python interface)
+-- parameters.json        # default parameters, valid ranges, units
+-- calibration_data/      # historical data for calibration and validation
+-- tests/                 # unit and integration tests
+-- README.md              # documentation, equations, sources
+-- references.bib         # scientific bibliography
+-- examples/              # usage examples and expected output
```

You do not need to understand the internal architecture to write a plugin. A historian can contribute a calibrated historical template. An epidemiologist can contribute an improved SIR model with parameters from published research. An economist can contribute a model of hyperinflation grounded in documented historical cases.

### Contribution pipeline

Every pull request goes through four stages automatically:

1. **Technical validation** — Tests pass, plugin interface is respected, no regressions, linting clean.
2. **Scientific validation** — Equations are dimensionally consistent, cited papers exist and are relevant, parameters are within realistic ranges, the model reproduces historical calibration data.
3. **Integration validation** — The plugin does not contradict existing modules, performs within acceptable bounds, produces plausible simulation output end-to-end.
4. **Human review** — Maintainers and domain experts review the automated report, discuss publicly on the pull request, and approve or request changes.

### Branch and commit conventions

- Branch names: `feature/<short-description>`, `fix/<short-description>`, `refactor/<short-description>`
- Base branch for features and fixes: `develop`
- Commit style: [Conventional Commits](https://www.conventionalcommits.org/) — `feat(agents): add memory decay with emotional weight`
- Line length: 120 characters, double quotes, PEP 8

---

## Inspired By

**Isaac Asimov — Foundation series.** The concept of psychohistory: a mathematical science that predicts the behavior of large populations with high precision, even though individual behavior is unpredictable. Epocha is a computational implementation of that idea — not with equations alone, but with agents whose emergent collective behavior becomes predictable at scale.

**Sid Meier's Civilization.** The intuition that complex historical dynamics can be modeled in a playable, interactive form. Epocha takes the same thesis seriously and attempts to replace abstracted game mechanics with scientifically grounded simulation.

**Giambattista Vico** — The theory of historical cycles: societies move through recurring phases of growth, consolidation, and decline (corsi e ricorsi). These cycles are a structural feature of the Epocha simulation, not a forced script.

**Ibn Khaldun** — The 14th century sociologist who described how civilizations rise through social cohesion (asabiyyah) and fall through its erosion. The dynamics he identified — elite overreach, bureaucratic calcification, loss of legitimacy — are modeled explicitly in Epocha's political and institutional systems.

**Polybius** — The Greek historian who described the anacyclosis: the natural progression and degeneration of political systems. Epocha's political module draws on this model of institutional cycle.

---

## License

Apache License 2.0. See [LICENSE](LICENSE) for the full text.

---

## Links

- **Repository:** [github.com/mauriziomocci/epocha](https://github.com/mauriziomocci/epocha)
- **Design specification:** [`docs/superpowers/specs/2026-03-22-epocha-design.md`](docs/superpowers/specs/2026-03-22-epocha-design.md)
- **MVP implementation plan:** [`docs/superpowers/plans/2026-03-23-mvp-implementation.md`](docs/superpowers/plans/2026-03-23-mvp-implementation.md)

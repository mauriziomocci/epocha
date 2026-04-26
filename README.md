# Epocha

English | [Italiano](README.it.md)

[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/)
[![Status](https://img.shields.io/badge/status-MVP%20in%20development-yellow.svg)]()
[![Django](https://img.shields.io/badge/django-5.x-green.svg)](https://www.djangoproject.com/)

> An AI-powered civilization simulator combining demographic and economic
> micro-simulation with LLM-driven agent cognition.

## Vision

Epocha is a computational take on psychohistory. Hundreds of autonomous
agents — each with a Big Five personality, episodic memory, and LLM-driven
deliberation — live inside a simulated world with audited demographic and
economic dynamics. Crises emerge from the bottom up. The same engine
scales from a medieval village to a galactic federation across centuries
of simulated time.

## Authoritative documentation

- **Whitepaper (English)**: [`docs/whitepaper/epocha-whitepaper.md`](docs/whitepaper/epocha-whitepaper.md) — scientific reference: motivation, methods (audited Demography and Economy Behavioral), implementation, calibration, validation methodology, designed subsystems pending audit.
- **Whitepaper (Italian)**: [`docs/whitepaper/epocha-whitepaper.it.md`](docs/whitepaper/epocha-whitepaper.it.md) — Italian companion, kept in sync.
- **Project conventions**: [`CLAUDE.md`](CLAUDE.md) — workflow, code review checklist, scientific rigor rules.
- **Recommended reading**: [`docs/letture-consigliate.md`](docs/letture-consigliate.md) — curated bibliography for contributors.

## Quickstart

### Prerequisites

- Docker and Docker Compose
- Python 3.12 (only if developing without Docker)

### Run locally

```bash
docker compose -f docker-compose.local.yml up --build
```

The dashboard is served at `http://localhost:8000/dashboard/` after migrations complete.

### Run tests

```bash
docker compose -f docker-compose.local.yml exec web pytest --cov=epocha -v
```

### LLM provider

Default: a local OpenAI-compatible server such as LM Studio. Configure via environment variable:

```bash
EPOCHA_DEFAULT_LLM_PROVIDER=openai
EPOCHA_LLM_API_KEY=...
EPOCHA_LLM_BASE_URL=http://host.docker.internal:1234/v1
EPOCHA_LLM_MODEL=...
```

For Groq with key rotation, comma-separate the keys in `EPOCHA_LLM_API_KEY`. See whitepaper §3.5 for the full provider abstraction.

## Project Structure

```
config/                Django settings, ASGI, Celery, URL routing
epocha/apps/
  agents/              Personality, memory, decision pipeline, reputation, factions
  chat/                Real-time WebSocket conversations with agents
  dashboard/           Server-rendered UI with Alpine.js progressive enhancement
  demography/          Mortality, fertility, couple formation (audited)
  economy/             Production, monetary, market, behavioral integration (Behavioral audited)
  knowledge/           Knowledge graph: ingestion, embedding, ontology, RAG
  llm_adapter/         Provider abstraction with rate limiting and key rotation
  simulation/          Tick engine, crisis, snapshots, WebSocket consumers
  users/               Authentication
  world/               Geography (PostGIS), government, institutions, stratification
epocha/common/         Shared utilities (pagination, permissions, exceptions)
docs/                  Specs, plans, whitepaper, memory backup
```

## Status

| Module | Implemented | Audited |
|---|---|---|
| Demography (Plan 1+2): mortality, fertility, couple | yes | yes (CONVERGED 2026-04-18 round 4) |
| Economy Behavioral (expectations, credit, property) | yes | yes (CONVERGED 2026-04-15) |
| Economy base (production, monetary, market, distribution) | yes | spec audit pending |
| Reputation (Castelfranchi-Conte-Paolucci 1998) | yes | Round 1 audit + remediation, Round 2 pending |
| Information Flow + Distortion + Belief Filter | yes | Round 1 audit + remediation, Round 2 pending |
| Government + Institutions + Stratification | yes | Round 1 audit + remediation, Round 2 pending |
| Movement, Factions | yes | Round 1 audit + remediation, Round 2 pending |
| Knowledge Graph | yes | scientific audit pending |
| Demography Plan 3+4 (Inheritance + Migration + Engine integration + Validation execution) | not yet | n/a |
| Economy financial markets (Spec 3) | not yet | n/a |

The audit re-pass on the 2026-04-12 batch (8 modules) is the highest priority follow-up; see whitepaper §9 Roadmap.

## Roadmap

Highest priority: re-audit pass on the 2026-04-12 batch (Reputation, Information Flow, Distortion, Belief Filter, Government, Institutions, Stratification, Movement, Factions). Then Demography Plan 3 (Inheritance + Migration), Plan 4 (Init + Engine integration + Historical validation), Economy financial markets, validation experiments execution. Full list in whitepaper §9.

## Contributing

- **Workflow**: 7-phase canonical (ideation → requirements with adversarial audit → architectural plan → task breakdown → implementation per atomic task → general test with adversarial code audit → closure). See `CLAUDE.md`.
- **Branch naming**: `feature/<short-description>`, `fix/<short-description>`, `refactor/<short-description>`.
- **Commits**: Conventional Commits (`type(scope): brief description` + `CHANGE:` line). No AI attribution, no emoji.
- **Code style**: `ruff check . && ruff format --check .`
- **Tests**: `pytest --cov=epocha -v`. Zero failing tests.
- **Whitepaper-code doc-sync rule**: PRs that modify code under `epocha/apps/demography/` or `epocha/apps/economy/{expectations,credit,banking,property_market}.py` must update the corresponding chapter of the bilingual whitepaper (`docs/whitepaper/epocha-whitepaper.md` and `.it.md`, chapters §4.1 and §4.2 respectively) in the same commit, or explain in the PR description why the change does not affect the model. See `CLAUDE.md` Documentation Sync section.

## License

Apache 2.0 — see [LICENSE](LICENSE).

## Citing Epocha

```bibtex
@misc{mocci_epocha_2026,
  author       = {Mocci, Maurizio},
  title        = {Epocha: A Scientifically Grounded Civilization Simulator},
  year         = {2026},
  version      = {0.1},
  url          = {https://github.com/mauriziomocci/epocha},
  note         = {Bilingual whitepaper at docs/whitepaper/}
}
```

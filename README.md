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

- **Whitepaper (English)**: [`docs/whitepaper/epocha-whitepaper.md`](docs/whitepaper/epocha-whitepaper.md) — scientific reference: motivation, methods (§4.1–§4.8, all audited to convergence), implementation, calibration, validation methodology, designed subsystems pending audit (§8).
- **Whitepaper (Italian)**: [`docs/whitepaper/epocha-whitepaper.it.md`](docs/whitepaper/epocha-whitepaper.it.md) — Italian companion, kept in sync.
- **Build map**: [`docs/build-map/epocha-build-map.html`](docs/build-map/epocha-build-map.html) — the project board and the source of truth for build status: what is done, in progress, or not started across the 13 phases, and in which dependency order. Self-contained, no server needed: open the file directly in a browser.
- **Project conventions**: [`CLAUDE.md`](CLAUDE.md) — workflow, code review checklist, scientific rigor rules.
- **Recommended reading**: [`docs/letture-consigliate.md`](docs/letture-consigliate.md) — curated bibliography for contributors.

The board is **bilingual since 2026-08-26**: Italian is the normative text, English the mirror, both in the same file with a language selector, and a structural guard (`epocha/apps/dashboard/tests/test_build_map_bilingual.py`) fails when the two diverge. The two languages are updated together, in the same commit.

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

The default run never reaches the network. The tests marked `network`, which download the multilingual embedding model, are deselected by `addopts` in `pyproject.toml` and run only when asked for with `pytest -m network`.

### Configuration constraints

Two settings are refused rather than tolerated. `EPOCHA_INFO_FLOW_RELIABILITY_DECAY` must lie in the open interval (0, 1): any other value stops every web and worker process at boot with `ImproperlyConfigured`, before any tick and any paid LLM call. The era template named by `demography_template` in a simulation's config must be one of the templates shipped in `epocha/apps/demography/templates/` (`pre_industrial_christian`, `pre_industrial_islamic`, `industrial`, `modern_democracy`, `sci_fi`); any other name, a path such as `../x` included, is refused by `template_loader.load_template` with the not-shipped error before it is turned into a file path.

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
  demography/          Mortality, fertility, couple formation, inheritance,
                       migration, and the per-tick orchestrator (audited)
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
| Demography (Plan 1+2): mortality, fertility, couple | yes — called by the tick loop since Plan 4 | yes (CONVERGED 2026-04-18 round 4) |
| Economy Behavioral (expectations, credit, property) | yes | yes (CONVERGED 2026-04-15) |
| Economy base (production, monetary, market, distribution) | yes | yes (CONVERGED 2026-07-16 round 12) |
| Reputation (Castelfranchi-Conte-Paolucci 1998) | yes | yes (CONVERGED 2026-05-12 round 2) |
| Information Flow (Bartlett 1932; Granovetter 1973 cited not implemented) | yes | yes (CONVERGED 2026-05-16 round 2) |
| Distortion (Allport-Postman 1947 assimilation) | yes | yes (CONVERGED 2026-05-16 round 2) |
| Belief Filter (Mayer 1995; Graziano-Tobin 2002; Castelfranchi-Falcone-Tan 2001) | yes | yes (CONVERGED 2026-05-16 round 2) |
| Affinity (McCrae-Costa 2003; Olson 1965; Axelrod 1984) | yes | yes (CONVERGED 2026-05-16 round 2) |
| Government (regime + coup, Geddes 1999; Polity 5; Powell-Thyne 2011) | yes | yes (CONVERGED 2026-05-16 round 2) |
| Government Types (12 regimes; Polity 5; Freedom House; Bueno de Mesquita 2003) | yes | yes (CONVERGED 2026-05-16 round 2) |
| Institutions (health dynamics; Acemoglu-Robinson 2012; Besley-Persson 2011) | yes | yes (CONVERGED 2026-05-16 round 2) |
| Stratification (Gini 1912; Gilbert 2011; Kahneman-Tversky 1979; Miller-Lynam 2001) | yes | yes (CONVERGED 2026-05-16 round 2) |
| Election (Caprara 2006; Huckfeldt-Sprague 1987; Lewis-Beck-Stegmaier 2000; Lodge-Steenbergen-Brau 1995; Bass 1985; Weber 1922; Merolla-Zechmeister 2011) | yes | yes (CONVERGED 2026-05-16 round 2) |
| Movement (Chandler 1966; Braudel 1979) | yes | yes (CONVERGED 2026-05-16 round 2) |
| Factions (Olson 1965; Festinger 1950; Judge 2002; Baumeister 2001; Hackman 2002) | yes | yes (CONVERGED 2026-05-16 round 2) |
| Knowledge Graph | yes | scientific audit pending |
| Demography Plan 3 (Inheritance + Migration) | yes — merged | yes (CONVERGED 2026-08-05 round 4) |
| Demography Plan 4 (Initialisation + Engine integration) | yes — on its feature branch, awaiting the merge | yes (phase-6 code gate CONVERGED 2026-10-29 round 16) |
| Historical validation campaign (execution) | not yet | n/a |
| Economy financial markets (Spec 3) | not yet | n/a |

The Knowledge Graph is the only module still awaiting its first scientific audit. The economy base layer converged on round 12 (2026-07-16) and was promoted to whitepaper §4.8, which closed the 2026-04-12 audit re-pass batch on every other module. The live board is the [build map](docs/build-map/epocha-build-map.html); the scientific detail is in whitepaper §9 Roadmap.

## Roadmap

Six clusters have converged and been promoted to Methods: reputation on round 2 (2026-05-12) as §4.3, the rumor cluster — information flow, distortion, belief filter, affinity — on round 2 (2026-05-16) as §4.4, the political cluster — government, government types, institutions, stratification, election — on round 2 (2026-05-16) as §4.5, movement on round 2 (2026-05-16) as §4.6, factions on round 2 (2026-05-16) as §4.7, and the economy base layer on round 12 of its first audit (2026-07-16) as §4.8. The Knowledge Graph is the one module left in whitepaper §8.

Demography Plan 3 (inheritance + migration) is merged. Plan 4 wires the audited §4.1 models into the live tick loop and seeds the starting population from the era template; its phase-6 code gate converged on round 16 (2026-10-29) and the branch awaits the merge. The gate was reopened once, for a mortality defect: the wiring passed the continuous age to the Heligman-Pollard schedule, so a newborn spent its first year on `q(0.02)`, `q(0.04)`, … and infant mortality came out 0.0083 against `q(0) = 0.0291` at weekly ticks. `q(x)` is now read at the completed integer age and held over the whole year of age (whitepaper §4.1), so results produced before this fix are not comparable with later ones.

The order of the next work was agreed on 2026-10-29. First, rule-based couple formation (Coale and McNeil 1972), the prerequisite of every validation, because in the pre-industrial eras a birth needs a couple and after initialisation couples form today only from LLM intents: its spec is approved by the Trinity under the project's autonomy profile, provisionally, pending the user's confirmation (D-29-21), and implementation has started on branch `20261029-123404-rule-based-couples`. Second, marital fertility in the eras that require a couple, before any validation: the Hadwiger schedule is a rate over all women, and applied to married women alone it gives a TFR (total fertility rate, the children a woman would bear over her fertile life) of 2.394 against the whitepaper's reference range of 4.5-6.5. Third, the first historical validation, England 1700-1750 against Wrigley and Schofield (1981) for mortality, fertility and age at marriage; it cites the published values only, because the machine-readable data behind them are distributed under terms not compatible with Apache-2.0. Fourth, one data-grounded report of that validation. Everything else stays on the [build map](docs/build-map/epocha-build-map.html), unopened until the first validation result exists: the Knowledge Graph audit, the economy financial markets (Spec 3), the dashboard driven by the API, the agents' context and chat coherence, the feasibility study for scale to billions of agents, the structural-demographic model with ensemble runs. The one exception is life-course behaviour by age, whose spec is approved and whose implementation starts after the Plan 4 merge. Full list in whitepaper §9.

## Contributing

- **Spec-driven development (mandatory since 2026-05-16)**: every work item — feature, fix campaign, refactor, deprecation — is authored through [GitHub Spec Kit](https://github.com/github/spec-kit), with no exceptions. Start with `/speckit-specify "<description>"`, which creates the branch and the spec scaffold, then `/speckit-plan` and `/speckit-tasks`. The three artifacts live in `specs/<branch>/{spec,plan,tasks}.md`. The project constitution is [`.specify/memory/constitution.md`](.specify/memory/constitution.md) and supersedes the code-quality rules of `CLAUDE.md` where the two conflict. Ad-hoc spec or plan files are not accepted: `docs/superpowers/specs/` and `docs/superpowers/plans/` are read-only archives of work predating the rule.
- **Workflow**: Spec Kit is the authoring framework; the canonical 7-phase workflow is the gating procedure around it (ideation → requirements with adversarial audit → architectural plan → task breakdown → implementation per atomic task → general test with adversarial code audit → closure). Heavy gates at requirements and at final validation, light gates at plan and task breakdown. See `CLAUDE.md`.
- **Branch naming**: `<YYYYMMDD-HHMMSS>-<slug>`, produced by `.specify/scripts/bash/create-new-feature.sh` through `/speckit-specify` — for example `20260715-132752-economy-base-layer-audit`. Do not hand-craft branch names.
- **Commits**: Conventional Commits (`type(scope): brief description` + `CHANGE:` line). No AI attribution, no emoji.
- **Code style**: `ruff check . && ruff format --check .`
- **Tests**: `pytest --cov=epocha -v`. Zero failing tests.
- **Whitepaper-code doc-sync rule**: a PR that modifies code in any module below must update that module's chapter in both whitepapers (`docs/whitepaper/epocha-whitepaper.md` and `.it.md`) in the same commit, or state in the PR description why the change does not affect the model. A module reaches §4 only by converging its adversarial audit, so an audited chapter that drifts from its code is worse than an unaudited one: it is trusted while being wrong. Full mapping in the `CLAUDE.md` Documentation Sync section.

  | Whitepaper chapter | Code |
  |---|---|
  | §4.1 Demography | `epocha/apps/demography/{mortality,fertility,couple,inheritance,migration}.py` |
  | §4.1.0 Per-tick orchestration | `epocha/apps/demography/{orchestrator,initialization,snapshot,context}.py` |
  | §4.2 Economy — behavioral | `epocha/apps/economy/{expectations,credit,banking,property_market}.py` |
  | §4.3 Reputation | `epocha/apps/agents/reputation.py` |
  | §4.4 Rumor propagation | `epocha/apps/agents/{information_flow,distortion,belief,affinity}.py` |
  | §4.5 Political institutions | `epocha/apps/world/{government,government_types,institutions,stratification,election}.py` |
  | §4.6 Movement | `epocha/apps/agents/movement.py` |
  | §4.7 Factions | `epocha/apps/agents/factions.py` |
  | §4.8 Economy — base layer | `epocha/apps/economy/{production,market,distribution,monetary,initialization,engine}.py` |
  | §6.2 Era templates | `epocha/apps/demography/{template_loader,truncated_moments}.py`, `epocha/apps/demography/templates/*.json` |

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

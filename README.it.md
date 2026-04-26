# Epocha

[English](README.md) | Italiano

[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/)
[![Status](https://img.shields.io/badge/status-MVP%20in%20development-yellow.svg)]()
[![Django](https://img.shields.io/badge/django-5.x-green.svg)](https://www.djangoproject.com/)

> Un simulatore di civiltà alimentato da AI che combina micro-simulazione
> demografica ed economica con cognizione di agenti guidata da LLM.

## Visione

Epocha è un approccio computazionale alla psicostoria. Centinaia di agenti
autonomi — ciascuno con una personalità Big Five, memoria episodica e
deliberazione guidata da LLM — vivono in un mondo simulato con dinamiche
demografiche ed economiche sottoposte ad audit. Le crisi emergono dal
basso. Lo stesso motore scala da un villaggio medievale a una federazione
galattica nell'arco di secoli di tempo simulato.

## Documentazione autoritativa

- **Whitepaper (italiano)**: [`docs/whitepaper/epocha-whitepaper.it.md`](docs/whitepaper/epocha-whitepaper.it.md) — riferimento scientifico: motivazione, metodi (Demografia ed Economia Comportamentale audited), implementazione, calibrazione, metodologia di validazione, sottosistemi progettati ma in attesa di audit.
- **Whitepaper (inglese)**: [`docs/whitepaper/epocha-whitepaper.md`](docs/whitepaper/epocha-whitepaper.md) — versione inglese, mantenuta in sincrono.
- **Convenzioni di progetto**: [`CLAUDE.md`](CLAUDE.md) — workflow, checklist di code review, regole di rigore scientifico.
- **Letture consigliate**: [`docs/letture-consigliate.md`](docs/letture-consigliate.md) — bibliografia curata per contributori.

## Avvio rapido

### Prerequisiti

- Docker e Docker Compose
- Python 3.12 (solo per sviluppo senza Docker)

### Esecuzione locale

```bash
docker compose -f docker-compose.local.yml up --build
```

La dashboard è servita su `http://localhost:8000/dashboard/` al termine delle migrazioni.

### Esecuzione dei test

```bash
docker compose -f docker-compose.local.yml exec web pytest --cov=epocha -v
```

### Provider LLM

Predefinito: un server locale compatibile con OpenAI come LM Studio. Configura tramite variabili d'ambiente:

```bash
EPOCHA_DEFAULT_LLM_PROVIDER=openai
EPOCHA_LLM_API_KEY=...
EPOCHA_LLM_BASE_URL=http://host.docker.internal:1234/v1
EPOCHA_LLM_MODEL=...
```

Per Groq con rotazione delle chiavi, separa le chiavi con virgole in `EPOCHA_LLM_API_KEY`. Vedi whitepaper §3.5 per l'astrazione completa del provider.

## Struttura del progetto

```
config/                Settings Django, ASGI, Celery, routing URL
epocha/apps/
  agents/              Personalità, memoria, pipeline decisionale, reputazione, fazioni
  chat/                Conversazioni WebSocket in tempo reale con gli agenti
  dashboard/           UI server-rendered con miglioramento progressivo Alpine.js
  demography/          Mortalità, fertilità, formazione delle coppie (audited)
  economy/             Produzione, monetario, mercato, integrazione comportamentale (Behavioral audited)
  knowledge/           Knowledge graph: ingestione, embedding, ontologia, RAG
  llm_adapter/         Astrazione del provider con rate limiting e rotazione chiavi
  simulation/          Tick engine, crisi, snapshot, consumer WebSocket
  users/               Autenticazione
  world/               Geografia (PostGIS), governo, istituzioni, stratificazione
epocha/common/         Utility condivise (paginazione, permessi, eccezioni)
docs/                  Spec, piani, whitepaper, backup di memoria
```

## Stato

| Modulo | Implementato | Audited |
|---|---|---|
| Demografia (Plan 1+2): mortalità, fertilità, coppia | sì | sì (CONVERGED 2026-04-18 round 4) |
| Economia Comportamentale (aspettative, credito, proprietà) | sì | sì (CONVERGED 2026-04-15) |
| Economia base (produzione, monetario, mercato, distribuzione) | sì | audit della spec in attesa |
| Reputazione (Castelfranchi-Conte-Paolucci 1998) | sì | Round 1 audit + remediation, Round 2 in attesa |
| Information Flow + Distortion + Belief Filter | sì | Round 1 audit + remediation, Round 2 in attesa |
| Governo + Istituzioni + Stratificazione | sì | Round 1 audit + remediation, Round 2 in attesa |
| Movimento, Fazioni | sì | Round 1 audit + remediation, Round 2 in attesa |
| Knowledge Graph | sì | audit scientifico in attesa |
| Demografia Plan 3+4 (Eredità + Migrazione + Integrazione Engine + Esecuzione validazione) | non ancora | n/a |
| Mercati finanziari Economia (Spec 3) | non ancora | n/a |

Il re-pass di audit sul batch del 2026-04-12 (8 moduli) è il follow-up a priorità più alta; vedi whitepaper §9 Roadmap.

## Roadmap

Priorità più alta: re-audit pass sul batch del 2026-04-12 (Reputazione, Information Flow, Distortion, Belief Filter, Governo, Istituzioni, Stratificazione, Movimento, Fazioni). Poi Demografia Plan 3 (Eredità + Migrazione), Plan 4 (Init + Integrazione Engine + Validazione storica), mercati finanziari Economia, esecuzione esperimenti di validazione. Lista completa nel whitepaper §9.

## Contribuire

- **Workflow**: canonico a 7 fasi (ideazione → requisiti con audit avversariale → piano architetturale → task breakdown → implementazione per task atomico → test generale con audit avversariale del codice → chiusura). Vedi `CLAUDE.md`.
- **Naming dei branch**: `feature/<short-description>`, `fix/<short-description>`, `refactor/<short-description>`.
- **Commit**: Conventional Commits (`type(scope): brief description` + riga `CHANGE:`). No attribuzione AI, no emoji.
- **Stile del codice**: `ruff check . && ruff format --check .`
- **Test**: `pytest --cov=epocha -v`. Zero test falliti.
- **Regola di doc-sync whitepaper-codice**: le PR che modificano codice in `epocha/apps/demography/` o `epocha/apps/economy/{expectations,credit,banking,property_market}.py` devono aggiornare il capitolo corrispondente del whitepaper bilingue (`docs/whitepaper/epocha-whitepaper.md` e `.it.md`, capitoli §4.1 e §4.2 rispettivamente) nello stesso commit, oppure spiegare nella descrizione della PR perché la modifica non incide sul modello. Vedi sezione Documentation Sync di `CLAUDE.md`.

## Licenza

Apache 2.0 — vedi [LICENSE](LICENSE).

## Citare Epocha

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

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

- **Whitepaper (italiano)**: [`docs/whitepaper/epocha-whitepaper.it.md`](docs/whitepaper/epocha-whitepaper.it.md) — riferimento scientifico: motivazione, metodi (§4.1–§4.8, tutti convergenti all'audit), implementazione, calibrazione, metodologia di validazione, sottosistemi progettati ma in attesa di audit (§8).
- **Whitepaper (inglese)**: [`docs/whitepaper/epocha-whitepaper.md`](docs/whitepaper/epocha-whitepaper.md) — versione inglese, mantenuta in sincrono.
- **Build map**: [`docs/build-map/epocha-build-map.html`](docs/build-map/epocha-build-map.html) — la lavagna di progetto e la fonte di verità sullo stato di avanzamento: cosa è fatto, in corso o non iniziato lungo le 13 fasi, e in quale ordine di dipendenza. È autonoma, non serve alcun server: si apre direttamente nel browser.
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
| Demografia (Plan 1+2): mortalità, fertilità, coppia | sì — modelli testati in isolamento, non ancora invocati dal tick loop (Plan 4) | sì (CONVERGENTE 2026-04-18 round 4) |
| Economia Comportamentale (aspettative, credito, proprietà) | sì | sì (CONVERGENTE 2026-04-15) |
| Economia base (produzione, monetario, mercato, distribuzione) | sì | sì (CONVERGENTE 2026-07-16 round 12) |
| Reputazione (Castelfranchi-Conte-Paolucci 1998) | sì | sì (CONVERGENTE 2026-05-12 round 2) |
| Flusso di informazioni (Bartlett 1932; Granovetter 1973 citato non implementato) | sì | sì (CONVERGENTE 2026-05-16 round 2) |
| Distorsione (assimilazione Allport-Postman 1947) | sì | sì (CONVERGENTE 2026-05-16 round 2) |
| Filtro di credenza (Mayer 1995; Graziano-Tobin 2002; Castelfranchi-Falcone-Tan 2001) | sì | sì (CONVERGENTE 2026-05-16 round 2) |
| Affinità (McCrae-Costa 2003; Olson 1965; Axelrod 1984) | sì | sì (CONVERGENTE 2026-05-16 round 2) |
| Governo (regime + colpo di stato, Geddes 1999; Polity 5; Powell-Thyne 2011) | sì | sì (CONVERGENTE 2026-05-16 round 2) |
| Tipi di governo (12 regimi; Polity 5; Freedom House; Bueno de Mesquita 2003) | sì | sì (CONVERGENTE 2026-05-16 round 2) |
| Istituzioni (dinamiche di salute; Acemoglu-Robinson 2012; Besley-Persson 2011) | sì | sì (CONVERGENTE 2026-05-16 round 2) |
| Stratificazione (Gini 1912; Gilbert 2011; Kahneman-Tversky 1979; Miller-Lynam 2001) | sì | sì (CONVERGENTE 2026-05-16 round 2) |
| Elezioni (Caprara 2006; Huckfeldt-Sprague 1987; Lewis-Beck-Stegmaier 2000; Lodge-Steenbergen-Brau 1995; Bass 1985; Weber 1922; Merolla-Zechmeister 2011) | sì | sì (CONVERGENTE 2026-05-16 round 2) |
| Movimento (Chandler 1966; Braudel 1979) | sì | sì (CONVERGENTE 2026-05-16 round 2) |
| Fazioni (Olson 1965; Festinger 1950; Judge 2002; Baumeister 2001; Hackman 2002) | sì | sì (CONVERGENTE 2026-05-16 round 2) |
| Knowledge Graph | sì | audit scientifico in attesa |
| Demografia Plan 3+4 (Eredità + Migrazione + Integrazione Engine + Esecuzione validazione) | non ancora | n/a |
| Mercati finanziari Economia (Spec 3) | non ancora | n/a |

Il Knowledge Graph è l'unico modulo ancora in attesa del suo primo audit scientifico. Il layer base dell'economia è convergente sul round 12 (2026-07-16) ed è stato promosso a §4.8 del whitepaper, il che ha chiuso il re-pass di audit del batch del 2026-04-12 su tutti gli altri moduli. La lavagna aggiornata è la [build map](docs/build-map/epocha-build-map.html); il dettaglio scientifico sta nel whitepaper §9 Roadmap.

## Roadmap

La priorità più alta è l'audit scientifico avversariale del Knowledge Graph, l'unico modulo rimasto nel §8 del whitepaper e l'elemento bloccante prima che calibrazione e validazione possano chiudersi. Sei cluster sono già convergenti e promossi a Metodi: la reputazione sul round 2 (2026-05-12) come §4.3, il cluster del passaparola — information flow, distortion, belief filter, affinity — sul round 2 (2026-05-16) come §4.4, il cluster politico — governo, tipi di governo, istituzioni, stratificazione, elezioni — sul round 2 (2026-05-16) come §4.5, il movimento sul round 2 (2026-05-16) come §4.6, le fazioni sul round 2 (2026-05-16) come §4.7 e il layer base dell'economia sul round 12 del suo primo audit (2026-07-16) come §4.8.

Seguono la Demografia Plan 3 (eredità + migrazione) e la Plan 4, che cabla i modelli auditati di §4.1 dentro il tick loop dal vivo in cui ancora non entrano, semina la popolazione iniziale dal template dell'era ed esegue la campagna di validazione storica. Poi i mercati finanziari dell'economia (Spec 3, non ancora redatta) e l'esecuzione degli esperimenti di validazione. Lista completa nel whitepaper §9; stato corrente per fase nella [build map](docs/build-map/epocha-build-map.html).

## Contribuire

- **Spec-driven development (obbligatorio dal 2026-05-16)**: ogni work item — feature, campagna di fix, refactor, deprecazione — si scrive attraverso [GitHub Spec Kit](https://github.com/github/spec-kit), senza eccezioni. Si parte da `/speckit-specify "<descrizione>"`, che crea il branch e lo scaffold della spec, poi `/speckit-plan` e `/speckit-tasks`. I tre artefatti vivono in `specs/<branch>/{spec,plan,tasks}.md`. La costituzione di progetto è [`.specify/memory/constitution.md`](.specify/memory/constitution.md) e prevale sulle regole di qualità del codice di `CLAUDE.md` dove le due confliggono. File di spec o piano ad hoc non sono accettati: `docs/superpowers/specs/` e `docs/superpowers/plans/` sono archivi in sola lettura del lavoro precedente alla regola.
- **Workflow**: Spec Kit è il framework di scrittura; il workflow canonico a 7 fasi è la procedura di gating che lo racchiude (ideazione → requisiti con audit avversariale → piano architetturale → task breakdown → implementazione per task atomico → test generale con audit avversariale del codice → chiusura). Gate pesanti ai requisiti e alla validazione finale, gate leggeri al piano e al task breakdown. Vedi `CLAUDE.md`.
- **Naming dei branch**: `<YYYYMMDD-HHMMSS>-<slug>`, prodotto da `.specify/scripts/bash/create-new-feature.sh` tramite `/speckit-specify` — per esempio `20260715-132752-economy-base-layer-audit`. Non comporre i nomi dei branch a mano.
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

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

La lavagna è **bilingue dal 2026-08-26**: l'italiano è il testo normativo, l'inglese il mirror, entrambi nello stesso file con un selettore di lingua, e una guardia strutturale (`epocha/apps/dashboard/tests/test_build_map_bilingual.py`) fallisce quando le due divergono. Le due lingue si aggiornano insieme, nello stesso commit.

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

L'esecuzione predefinita non raggiunge mai la rete. I test marcati `network`, che scaricano il modello di embedding multilingue, sono esclusi da `addopts` in `pyproject.toml` e girano solo quando li si chiede con `pytest -m network`.

### Vincoli di configurazione

Due impostazioni vengono rifiutate invece che tollerate. `EPOCHA_INFO_FLOW_RELIABILITY_DECAY` deve stare nell'intervallo aperto (0, 1): qualunque altro valore ferma all'avvio ogni processo web e worker con `ImproperlyConfigured`, prima di qualsiasi tick e di qualsiasi chiamata LLM a pagamento. Il template d'era indicato da `demography_template` nella configurazione di una simulazione deve essere uno dei template distribuiti in `epocha/apps/demography/templates/` (`pre_industrial_christian`, `pre_industrial_islamic`, `industrial`, `modern_democracy`, `sci_fi`); qualunque altro nome, compreso un percorso come `../x`, viene rifiutato da `template_loader.load_template` con l'errore di template non distribuito prima di diventare un percorso di file.

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
  demography/          Mortalità, fertilità, formazione delle coppie, eredità,
                       migrazione e l'orchestratore per tick (auditati)
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
| Demografia (Plan 1+2): mortalità, fertilità, coppia | sì — invocati dal tick loop dal Plan 4 | sì (CONVERGENTE 2026-04-18 round 4) |
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
| Demografia Plan 3 (Eredità + Migrazione) | sì — mergiata | sì (CONVERGENTE 2026-08-05 round 4) |
| Demografia Plan 4 (Inizializzazione + Integrazione Engine) | sì — sul proprio ramo, in attesa del merge | sì (gate di fase 6 sul codice CONVERGENTE 2026-10-29 round 16) |
| Campagna di validazione storica (esecuzione) | non ancora | n/a |
| Mercati finanziari Economia (Spec 3) | non ancora | n/a |

Il Knowledge Graph è l'unico modulo ancora in attesa del suo primo audit scientifico. Il layer base dell'economia è convergente sul round 12 (2026-07-16) ed è stato promosso a §4.8 del whitepaper, il che ha chiuso il re-pass di audit del batch del 2026-04-12 su tutti gli altri moduli. La lavagna aggiornata è la [build map](docs/build-map/epocha-build-map.html); il dettaglio scientifico sta nel whitepaper §9 Roadmap.

## Roadmap

Sei cluster sono convergenti e promossi a Metodi: la reputazione sul round 2 (2026-05-12) come §4.3, il cluster del passaparola — information flow, distortion, belief filter, affinity — sul round 2 (2026-05-16) come §4.4, il cluster politico — governo, tipi di governo, istituzioni, stratificazione, elezioni — sul round 2 (2026-05-16) come §4.5, il movimento sul round 2 (2026-05-16) come §4.6, le fazioni sul round 2 (2026-05-16) come §4.7 e il layer base dell'economia sul round 12 del suo primo audit (2026-07-16) come §4.8. Il Knowledge Graph è l'unico modulo rimasto nel §8 del whitepaper.

La Demografia Plan 3 (eredità + migrazione) è mergiata. La Plan 4 cabla i modelli auditati di §4.1 dentro il tick loop dal vivo e semina la popolazione iniziale dal template dell'era; il suo gate di fase 6 sul codice è convergente al round 16 (2026-10-29) e il ramo è in attesa del merge. Il gate è stato riaperto una volta, per un difetto della mortalità: il cablaggio passava allo schema di Heligman-Pollard l'età continua, quindi un neonato passava il primo anno su `q(0.02)`, `q(0.04)`, … e la mortalità infantile risultava 0,0083 contro `q(0) = 0,0291` con tick settimanali. Ora `q(x)` si legge all'età intera compiuta e resta fermo per tutto l'anno d'età (whitepaper §4.1), quindi i risultati prodotti prima di questa correzione non sono confrontabili con quelli successivi.

L'ordine dei prossimi lavori è stato concordato il 2026-10-29. Primo, la formazione delle coppie a regole (Coale e McNeil 1972), prerequisito di ogni validazione, perché nelle ere pre-industriali una nascita richiede una coppia e dopo l'inizializzazione oggi le coppie si formano solo dagli intenti del LLM: la sua spec è approvata dalla Trinity sotto il profilo di autonomia del progetto, in via provvisoria, in attesa della conferma dell'utente (D-29-21), e l'implementazione è partita sul ramo `20261029-123404-rule-based-couples`. Secondo, la fertilità coniugale nelle ere che richiedono la coppia, prima di qualsiasi validazione: lo schema di Hadwiger è un tasso su tutte le donne, e applicato alle sole donne sposate dà un TFR (tasso di fecondità totale, i figli che una donna avrebbe nella sua vita fertile) di 2,394 contro l'intervallo di riferimento del whitepaper di 4,5-6,5. Terzo, la prima validazione storica, l'Inghilterra dal 1700 al 1750 contro Wrigley e Schofield (1981) per mortalità, fertilità ed età al matrimonio; cita solo i valori pubblicati, perché i dati leggibili da macchina che li sostengono sono distribuiti con termini non compatibili con Apache-2.0. Quarto, un solo rapporto di quella validazione fondato sui dati. Tutto il resto resta nella [build map](docs/build-map/epocha-build-map.html), non aperto finché non esiste il primo risultato di validazione: l'audit del Knowledge Graph, i mercati finanziari dell'economia (Spec 3), la dashboard comandata dalle API, il contesto degli agenti e la coerenza della chat, lo studio di fattibilità per la scala a miliardi di agenti, il modello demografico-strutturale con le esecuzioni d'insieme. L'unica eccezione è il comportamento per età lungo il corso della vita, la cui spec è approvata e la cui implementazione parte dopo il merge del Plan 4. Lista completa nel whitepaper §9.

## Contribuire

- **Spec-driven development (obbligatorio dal 2026-05-16)**: ogni work item — feature, campagna di fix, refactor, deprecazione — si scrive attraverso [GitHub Spec Kit](https://github.com/github/spec-kit), senza eccezioni. Si parte da `/speckit-specify "<descrizione>"`, che crea il branch e lo scaffold della spec, poi `/speckit-plan` e `/speckit-tasks`. I tre artefatti vivono in `specs/<branch>/{spec,plan,tasks}.md`. La costituzione di progetto è [`.specify/memory/constitution.md`](.specify/memory/constitution.md) e prevale sulle regole di qualità del codice di `CLAUDE.md` dove le due confliggono. File di spec o piano ad hoc non sono accettati: `docs/superpowers/specs/` e `docs/superpowers/plans/` sono archivi in sola lettura del lavoro precedente alla regola.
- **Workflow**: Spec Kit è il framework di scrittura; il workflow canonico a 7 fasi è la procedura di gating che lo racchiude (ideazione → requisiti con audit avversariale → piano architetturale → task breakdown → implementazione per task atomico → test generale con audit avversariale del codice → chiusura). Gate pesanti ai requisiti e alla validazione finale, gate leggeri al piano e al task breakdown. Vedi `CLAUDE.md`.
- **Naming dei branch**: `<YYYYMMDD-HHMMSS>-<slug>`, prodotto da `.specify/scripts/bash/create-new-feature.sh` tramite `/speckit-specify` — per esempio `20260715-132752-economy-base-layer-audit`. Non comporre i nomi dei branch a mano.
- **Commit**: Conventional Commits (`type(scope): brief description` + riga `CHANGE:`). No attribuzione AI, no emoji.
- **Stile del codice**: `ruff check . && ruff format --check .`
- **Test**: `pytest --cov=epocha -v`. Zero test falliti.
- **Regola di doc-sync whitepaper-codice**: una PR che modifica codice in uno qualunque dei moduli elencati sotto deve aggiornare il capitolo corrispondente in entrambi i whitepaper (`docs/whitepaper/epocha-whitepaper.md` e `.it.md`) nello stesso commit, oppure dichiarare nella descrizione della PR perché la modifica non incide sul modello. Un modulo arriva al §4 solo facendo convergere il proprio audit avversariale, quindi un capitolo auditato che diverge dal suo codice è peggio di uno non auditato: viene creduto pur essendo sbagliato. Mappa completa nella sezione Documentation Sync di `CLAUDE.md`.

  | Capitolo whitepaper | Codice |
  |---|---|
  | §4.1 Demografia | `epocha/apps/demography/{mortality,fertility,couple,inheritance,migration}.py` |
  | §4.1.0 Orchestrazione per tick | `epocha/apps/demography/{orchestrator,initialization,snapshot,context}.py` |
  | §4.2 Economia — comportamentale | `epocha/apps/economy/{expectations,credit,banking,property_market}.py` |
  | §4.3 Reputazione | `epocha/apps/agents/reputation.py` |
  | §4.4 Propagazione del passaparola | `epocha/apps/agents/{information_flow,distortion,belief,affinity}.py` |
  | §4.5 Istituzioni politiche | `epocha/apps/world/{government,government_types,institutions,stratification,election}.py` |
  | §4.6 Movimento | `epocha/apps/agents/movement.py` |
  | §4.7 Fazioni | `epocha/apps/agents/factions.py` |
  | §4.8 Economia — layer base | `epocha/apps/economy/{production,market,distribution,monetary,initialization,engine}.py` |
  | §6.2 Template d'era | `epocha/apps/demography/{template_loader,truncated_moments}.py`, `epocha/apps/demography/templates/*.json` |

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

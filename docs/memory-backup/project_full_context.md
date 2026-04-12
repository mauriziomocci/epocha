---
name: full-project-context
description: Complete project state, what was built, what's next -- the single source of truth for resuming work
type: project
originSessionId: 0a27799c-3d4b-4995-b144-424ee45e5764
---
# Epocha -- Stato completo del progetto

## Cosa e' Epocha

Simulatore di civilta' basato su agenti AI autonomi. Ogni agente ha personalita'
(Big Five), memoria, relazioni, reputazione. La simulazione gira a tick discreti
dove ogni agente prende decisioni via LLM. Il sistema produce dinamiche emergenti:
fazioni, governi, rivoluzioni, epidemie, corruzione.

Visione: simulare QUALSIASI civilta' -- dal neolitico alla galassia di Asimov.
Qualsiasi scala (villaggio -> pianeta -> galassia). Qualsiasi era. Qualsiasi
contesto (storico, contemporaneo, speculativo, fittizio).

## Stack tecnico

- Django 5.x + DRF + Django Channels + Celery + Redis
- PostgreSQL con PostGIS + pgvector (entrambi attivi nel custom Docker image)
- LLM: Groq (llama-3.3-70b) + GitHub Models (GPT-4o-mini per chat)
- Embedding: fastembed (intfloat/multilingual-e5-large, 1024 dim)
- Frontend: Django templates + Alpine.js + Tailwind CDN + Sigma.js
- Docker Compose: custom postgres (postgis+pgvector), web, celery, redis

## Apps Django

| App | Stato | Descrizione |
|-----|-------|-------------|
| users | Completo | Auth |
| simulation | Completo | Tick engine, events, snapshots, crisis detection |
| agents | Completo | Personalita', memoria, decisioni, relazioni, reputazione, fazioni, information flow, belief, distortion, movement |
| world | Completo | Map, zone (PostGIS), governi (12 tipi), istituzioni, stratificazione, elezioni, colpi di stato |
| chat | Completo | WebSocket conversations |
| llm_adapter | Completo | Provider abstraction, rate limiting, cost tracking |
| dashboard | Completo | Frontend completo con grafo sociale, analytics, chat |
| knowledge | **COMPLETATO** | Knowledge Graph: document ingestion, chunking, embedding (multilingual-e5-large), LLM extraction, merge/dedup, materialization, Celery orchestration, world generator integration, visualization Sigma.js, graph data API, upload API |
| economy | **IN CORSO** | Modello economico neoclassico. Part 1 (data layer) e Part 2 (engine) completati. Part 3 (integration) da fare. |

## Knowledge Graph (COMPLETATO 2026-04-12)

Pipeline end-to-end funzionante:
documents -> chunk -> embed -> cache check -> LLM extraction -> validate ->
merge/dedup -> cache -> materialize -> generate agents -> visualize

16 task in 4 plan. 10 modelli: KnowledgeDocument, KnowledgeDocumentAccess,
KnowledgeChunk (pgvector HNSW), ExtractionCache, KnowledgeGraph, KnowledgeNode
(10 entity types, 20 relation types), KnowledgeRelation, KnowledgeNodeCitation,
KnowledgeRelationCitation.

Ontologia: Searle (1995), CIDOC-CRM, Freeden (1996). Embedding: Wang et al.
(2024) multilingual-e5-large. Dedup: single-linkage clustering a soglia 0.85.

## Modello Economico (IN CORSO)

Tre spec sequenziali (paradigmi economici storici):
1. **Spec 1 (neoclassica)** -- IN CORSO: CES production (Arrow 1961), Walrasian
   tatonnement (Walras 1874), multi-currency (Fisher 1911), property (Ricardo
   1817), flat tax, template per era.
2. **Spec 2 (comportamentale)** -- FUTURE: property transfers, debt/credit
   (Minsky 1986), labor matching (Mortensen-Pissarides), prospect theory
   (Kahneman-Tversky), friction informativa (Stiglitz).
3. **Spec 3 (finanziaria)** -- FUTURE: borse, azioni, obbligazioni, derivati,
   banking (Diamond-Dybvig), bolle (Shiller), contagio (Allen-Gale).

### Stato implementazione Spec 1:
- **Part 1 (data layer)**: COMPLETATO. 10 modelli: Currency, GoodCategory,
  ProductionFactor, ZoneEconomy, PriceHistory, AgentInventory, Property,
  TaxPolicy, EconomicLedger, EconomyTemplate. Government.treasury aggiunto.
  4 template per era (pre_industrial sigma=0.5, industrial 0.8, modern 1.2,
  sci_fi 1.5). Template loader idempotente.
- **Part 2 (engine)**: COMPLETATO. 5 moduli: production.py (CES con limit
  CD/Leontief), market.py (tatonnement con price cap), distribution.py
  (rent/wages/tax), monetary.py (Fisher velocity + mood satiation),
  engine.py (pipeline 7 step).
- **Part 3 (integration)**: DA FARE. Contesto economico nel decision prompt,
  azione hoard, feedback politico (inflazione->stability, Gini->legitimacy,
  treasury<0->crisis), inizializzazione dal world generator, deprecazione
  old economy.py, integrazione in simulation/engine.py.

## Audit scientifico (COMPLETATO 2026-04-12)

Primo audit avversario su 11 moduli scientifici: 46 issue trovate
(14 INCORRECT, 19 UNJUSTIFIED, 6 INCONSISTENT, 7 MISSING).
Tutte risolte. Re-audit: CONVERGED.

Fix principali: citazioni false rimosse (Powell Table 2, Polity IV Table 3,
Miller 1956, Zonis 1994), colpo di stato reso stocastico, corruzione non
crea piu' ricchezza dal nulla, velocita' a piedi corretta a 25 km/giorno,
Kahneman satiation curve implementata, tutti i parametri non derivati
marcati come "tunable design parameter".

## Test

524 test passano (263 originali + 161 knowledge + 71 economy + 29 fix).

## Regole fondamentali (in CLAUDE.md)

- **GOLDEN RULE**: il metodo scientifico e' prioritario su tutto
- **Verify Every Assertion**: mai dare per scontate asserzioni (proprie E dell'utente)
- **Adversarial Scientific Audit**: ciclo audit -> fix -> re-audit fino a CONVERGED
- **Three-Step Design Process**: proposta -> review critica -> seconda review -> spec
- **Every Spec Includes FAQ**: domande e risposte sul perche' di ogni scelta
- **Code Comments**: ogni formula, costante, algoritmo, semplificazione documentata con fonte
- Estensibilita' sempre (no hardcoding, JSONField per parametri variabili)
- Ottimizzazione non negoziabile fin da subito
- Conversazione in italiano, codice in inglese

## Prossimi step immediati (in ordine)

1. **Economy Part 3 (integration)** -- collegare il motore al simulation engine,
   iniettare contesto economico nel decision prompt, hoard action, feedback
   politico, inizializzazione, deprecazione old economy.py
2. **Economy Spec 2 brainstorming** -- comportamentale: debito, property transfers,
   prospect theory, labor matching, friction
3. **Economy Spec 3 brainstorming** -- finanziaria: borse, bolle, panico
4. **Web scraping** -- acquisizione automatica dati per scenari reali
5. Resto roadmap: report agent, interview mode, demografia, epidemiologia SIR,
   mappa 2D, miglioramento grafo

## Simulazione attiva

Rivoluzione Francese 1789 -- 15 agenti, 4 zone PostGIS. Governo monarchia,
stability 0.2, corruption 0.6. Gini alto. L'economia attuale e' ancora il
placeholder MVP per le simulazioni esistenti; le nuove simulazioni useranno
il motore CES dopo Part 3.

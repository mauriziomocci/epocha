---
name: mirofish-comparison
description: Feature comparison with MiroFish, verified 2026-10-29 -- same per-agent LLM cost structure as Epocha, AGPL-3.0 (ideas only), where Epocha goes beyond
type: reference
originSessionId: 8f665d74-99ae-4441-b1f2-511d74b26c7d
---

## Aggiornamento verificato 2026-10-29 (lettura statica del codice MiroFish via API GitHub, nulla eseguito)

Le affermazioni sotto questa sezione sono anteriori e in parte superate: questa prevale.
- **Stessa struttura di costo "giocattolo".** Ogni agente MiroFish e' un agente LLM di OASIS: un
  agente che agisce in un round costa una chiamata LLM (`run_twitter_simulation.py:649`); il costo
  si contiene solo con un sottoinsieme casuale per round. Il numero di agenti e' uno per entita'
  estratta dai documenti. Il "milione di agenti" viene dal paper di OASIS, non da MiroFish.
- **Iniezione di variabili quasi assente nel codice**: `scheduled_events` e' una lista vuota fissa
  (`simulation_config_generator.py:725`); parametri tipo echo chamber, viral threshold sono generati
  ma non letti dagli script di run. Nessuna citazione, nessuna validazione.
- **Da cui prendere spunto (idee, mai codice)**: agente di report con strumenti, fatti correnti
  separati da quelli superati, intervista agli agenti senza far avanzare la simulazione.
- **Licenza AGPL-3.0**: niente codice ne' prompt copiati in Epocha (Apache-2.0).
- **Dove Epocha va oltre**: scala con coorti statistiche e un insieme limitato di protagonisti LLM
  (MiroFish non puo' senza abbandonare OASIS), rigore scientifico, demografia per tick.
Rapporto completo del 2026-10-29 nello scratchpad della sessione Epocha di quel giorno (temporaneo).

MiroFish (https://github.com/666ghj/MiroFish) -- simulatore multi-agente di
riferimento. Confronto con Epocha per identificare gap e vantaggi.

## Cosa MiroFish fa che noi dovremmo considerare

1. **Knowledge Graph (GraphRAG)** -- costruisce un knowledge graph dai materiali
   di input prima della simulazione. Estrae entita', relazioni, e contesto.
   Noi generiamo dal prompt LLM senza struttura intermedia. Il design doc
   prevede un Knowledge Engine -- da implementare.

2. **Report Agent avanzato** -- agente dedicato con toolset per generare report
   di sintesi ricchi. Il nostro auto-report e' basico (singola chiamata LLM).

3. **Iniezione variabili strutturate** -- non solo eventi testuali ma variabili
   che modificano parametri della simulazione in tempo reale.

4. **Memoria con Zep Cloud** -- retrieval semantico via embedding per la memoria
   degli agenti. Piu' efficace del nostro ranking per emotional_weight + recency.
   Considerare pgvector (gia' nel design doc) per retrieval semantico.

5. **Grafo visivamente impressionante** -- centinaia di nodi, multi-tipo
   (Entity/Organization/Disaster), sfondo chiaro, tab per viste diverse.
   Dettagli in feedback_graph_improvement.md.

## Cosa noi facciamo meglio di MiroFish

1. **Rigore scientifico** -- ogni formula citata (Gini, Bartlett, Castelfranchi).
   MiroFish non cita fonti scientifiche.
2. **Reputazione formale** -- modello Castelfranchi-Conte-Paolucci con
   image/reputation. MiroFish non ha reputazione.
3. **Sistema politico** -- 12 governi, transizioni, elezioni, colpi di stato.
   MiroFish non simula politica.
4. **Istituzioni e stratificazione** -- salute istituzionale, Gini, classi.
5. **PostGIS** -- spazialita' reale con query geometriche.
6. **Distorsione dell'informazione** -- Big Five rule-based. Unico.
7. **Belief filter** -- accettazione pesata per personalita' e reputazione.

## Analisi approfondita (codebase esplorata 2026-04-07)

MiroFish e Epocha fanno COSE DIVERSE:
- MiroFish: simula dinamiche social media (Twitter/Reddit) con agenti LLM.
  Usa OASIS (camel-ai) come motore. Knowledge graph via Zep Cloud.
  Non ha economia, politica, governi, modelli scientifici, spazialita'.
- Epocha: simula civilta' con modelli scientifici + agenti LLM.
  Ha economia, politica, istituzioni, reputazione, PostGIS.

Il grafo di MiroFish e' piu' denso perche' il knowledge graph ha centinaia
di entita' estratte dai documenti (persone, luoghi, concetti), non perche'
ha piu' agenti attivi. Il default di profile generation parallela e' 3.

Non sono concorrenti diretti. MiroFish NON simula civilta', nonostante
il marketing aggressivo ("predict anything", "parallel digital world").
Verificato il 2026-04-15: nessun modulo economy/government/military/
demographics nel codebase. L'utente aveva inizialmente pensato che
MiroFish avesse funzionalita' di civilta', ma ha confermato di aver
travisato dopo la verifica.

## Priority per colmare i gap

Alta: Knowledge Graph con pgvector (il differenziatore visivo piu' impattante)
Media: Report Agent avanzato, grafo multi-tipo con entita' non-agente
Bassa: Vue.js frontend (escluso dalla roadmap), Zep Cloud (pgvector basta)

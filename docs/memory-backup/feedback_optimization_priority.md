---
name: optimization-always-priority
description: Ottimizzare sempre il codice fin da subito, considerare performance e riuso delle risorse come requisito non negoziabile
type: feedback
originSessionId: 0a27799c-3d4b-4995-b144-424ee45e5764
---
Ogni scelta di design deve includere l'ottimizzazione come criterio fin dal primo momento, non come refactoring successivo.

**Why:** L'utente ha stabilito il 2026-04-11 durante il brainstorming del Knowledge Graph che l'ottimizzazione (caching intelligente, evitare duplicazione computazionale, riuso delle risorse) deve essere prioritaria fin dall'inizio. Regola confermata quando ho proposto l'opzione (a) "un grafo per simulation" giustificandola con semplicita' del modello, e l'utente ha preferito (c) "grafo per simulation con cache per hash dei documenti". Aggiungere ottimizzazioni dopo e' costoso e spesso richiede riscrivere intere sezioni.

**How to apply:**
- Quando propongo alternative, includere sempre una colonna "costo computazionale" e "riusabilita' risorse"
- Preferire soluzioni con caching deterministico (hash-based) rispetto a ricomputazione cieca
- Per operazioni LLM (costose), sempre cache persistente quando l'input e' deterministico
- Per query DB, N+1 e' vietato dal giorno zero, non e' qualcosa da "sistemare dopo"
- Le cache devono avere chiavi deterministiche che includano TUTTI i fattori che influenzano l'output (contenuto + versione del prompt + versione dell'ontologia), altrimenti contaminano i risultati
- Documentare nel codice quali ottimizzazioni sono attive e quali assunzioni fanno
- Quando rigore scientifico e ottimizzazione sembrano in conflitto, cercare una terza via: di solito una cache ben progettata con chiave deterministica preserva entrambi

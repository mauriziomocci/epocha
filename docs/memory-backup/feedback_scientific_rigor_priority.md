---
name: scientific-rigor-priority
description: Ogni scelta di design deve privilegiare il massimo rigore scientifico rispetto ad alternative piu' veloci o comode
type: feedback
originSessionId: 0a27799c-3d4b-4995-b144-424ee45e5764
---
Quando si valuta un trade-off di design, scegliere sempre l'opzione che garantisce il massimo rigore scientifico, anche se piu' costosa o complessa.

**Why:** Epocha e' una simulazione scientifica, non un giocattolo. Il valore del progetto sta proprio nella verificabilita' dei modelli e nella tracciabilita' delle fonti. Scelte di comodo erodono questo valore nel tempo. Regola confermata dall'utente il 2026-04-11 durante il brainstorming del Knowledge Graph, quando ho proposto l'opzione (c) "documenti + research agent" invece di (b) "LLM libero di inventare" proprio per rigore scientifico.

**How to apply:**
- Preferire sempre dati da fonti verificabili (documenti caricati, paper, dataset reali) rispetto a generazione LLM libera
- Quando l'LLM deve generare contenuto, vincolarlo a fonti esplicite o marcare esplicitamente l'output come ipotetico
- Citare le fonti direttamente nel codice (docstring, commenti) non solo nella documentazione
- Parametri numerici: sempre da letteratura o dati reali; mai "magic numbers" senza giustificazione
- Se non esistono dati per calibrare un modello, preferire la versione piu' semplice difendibile documentando la limitazione
- Nel proporre alternative all'utente, ordinarle per rigore scientifico decrescente e raccomandare sempre la piu' rigorosa

---
name: web-scraping-capability
description: Scraping automatico per acquisire contesto storico e dati economici reali da fonti web, da sviluppare come feature separata
type: project
originSessionId: 0a27799c-3d4b-4995-b144-424ee45e5764
---
L'utente ha richiesto il 2026-04-12 che il sistema possa fare scraping
per ottenere automaticamente contesto per scenari reali e storici.

**Scope**: acquisire dati economici, storici e contestuali da fonti web
per alimentare sia il Knowledge Graph (entita', relazioni) sia il
modello economico (parametri, prezzi, dati di produzione).

**Requisiti**:
- Scraping da fonti pubbliche (Wikipedia, archivi storici, dataset economici)
- Rispetto di robots.txt e rate limiting
- Cache dei risultati per evitare richieste ripetute
- Parsing strutturato (tabelle, infobox, serie storiche)
- Integrazione con la pipeline di ingestion del Knowledge Graph
- Separazione chiara: lo scraping produce documenti/dati, il KG e il
  modello economico li consumano

**Why:** Per scenari reali e storici, l'utente non dovrebbe dover
cercare e caricare manualmente tutti i documenti. Il sistema deve poter
arricchire autonomamente il contesto partendo da poche indicazioni
(es. "Francia 1789" o "crisi del 2008").

**How to apply:** Progettare il modello economico con input parametrici
agnostici rispetto alla fonte. Lo scraping si inserira' come estensione
della pipeline di ingestion del Knowledge Graph, non come parte del
motore economico. Feature da sviluppare DOPO il modello economico.

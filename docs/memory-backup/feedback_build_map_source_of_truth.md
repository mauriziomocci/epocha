---
name: build-map-source-of-truth
description: "REGOLA PERMANENTE e IMPERATIVA dal 2026-07-17 -- la build map e' la fonte di verita' dei lavori fatti e da fare (il Jira di Epocha). Sorgente versionato docs/build-map/epocha-build-map.html, artifact URL stabile. Va aggiornata NELLA STESSA sessione a ogni cambio di stato. Regola completa nel CLAUDE.md di progetto."
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 04c1bad8-c5e3-4aa6-a6fc-12ef535f744c
---

La **build map** e' la fonte di verita' di cosa e' costruito e cosa no in Epocha -- il board di progetto, l'equivalente di un Jira. L'utente l'ha dichiarata imperativa il 2026-07-17.

- **Sorgente** (versionato nel repo): `docs/build-map/epocha-build-map.html`
- **Artifact** (URL stabile, NON cambiarlo mai): https://claude.ai/code/artifact/c81c0d24-313c-474b-8440-c22275e1cb15
- **Regola completa**: sezione `### CRITICAL: The Build Map is the Source of Truth` nel `CLAUDE.md` di progetto.

**Why**: l'utente stava perdendo il focus sull'interezza del progetto (13 fasi). La memoria roadmap [[post-mvp-roadmap]] era vecchia di 94 giorni e sbagliava due fatti portanti insieme -- lasciava intendere che la demografia fosse da iniziare quando i suoi modelli sono auditati (§4.1) ma non cablati nel tick loop, e che l'integrazione economica fosse da fare quando era gia' in produzione. Una board unica e verificata, aggiornata per prassi, e' il rimedio. Una mappa che ritarda sul codice e' peggio di nessuna mappa: viene creduta mentre e' sbagliata.

**How to apply**:

1. **Aggiorna nella STESSA sessione**, prima di chiudere, quando: una fase cambia stato; un audit converge o apre un round; un modulo viene cablato (o scablato) dal tick loop; un capitolo passa da §8 a §4; un work item si apre/rinvia/chiude; cambia una dipendenza tra fasi.
2. **Verifica prima contro la realta'**: codice + whitepaper. MAI ereditare lo stato da una memoria, da un handoff, o dallo stato precedente della mappa stessa -- tutti e tre invecchiano in silenzio. Per sapere se un modulo e' vivo, grep del tick engine: definito e unit-testato NON significa cablato (e' esattamente l'errore che la demografia nascondeva).
3. **Ripubblica sullo STESSO URL**: tool Artifact con `file_path` = il file nel repo e `url` = l'URL sopra. Senza `url`, o pubblicando da un path diverso (es. una copia nello scratchpad), si conia un URL NUOVO e la fonte di verita' si biforca in due board concorrenti. E' il failure mode principale.
4. **Committa il file** insieme al lavoro che descrive, mai in un commit di coda "aggiorno la mappa".

**Come si apre**: il file e' autoconsistente (CSS e JS inline, zero risorse esterne, zero chiamate di rete). `open docs/build-map/epocha-build-map.html` -- niente server, niente login, niente container. L'artifact e' uno specchio condivisibile dello stesso file, non una seconda fonte.

**Perche' NON e' servita da Django** (valutato e scartato il 2026-07-17, decisione dell'utente): dentro l'app `dashboard` finirebbe dietro login (18 view su 25 sono auth-gated) e accoppierebbe documentazione di progetto all'UI operatore delle simulazioni, la cui unica responsabilita' e' operare/osservare simulazioni -- dipendenza nel verso sbagliato, anti-pattern DVT-544. Anche una rotta HTTP a livello progetto e' stata scartata: comprerebbe un URL `localhost` stabile al costo di richiedere il container su, per un file che si apre da solo. **Non riproporre nessuna delle due senza una ragione nuova.**

**Precedenza**: sui conflitti di stato di build la mappa vince su memorie e handoff. Il whitepaper resta autoritativo per il contenuto scientifico e per lo stato di audit dei suoi capitoli. [[post-mvp-roadmap]] porta scope, ordine delle dipendenze e fonti bibliografiche delle 13 fasi e **punta** alla mappa per lo stato: non deve duplicarlo, o le due divergono.

Correlate: [[whitepaper-doc-sync-rule]], [[whitepaper-promotion-pipeline]].

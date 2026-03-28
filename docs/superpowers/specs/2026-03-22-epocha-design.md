# Epocha — Design Document

## Il Nome

**Epocha** deriva dal greco **epochē** (ἐποχή) — che significa "punto di arresto", "momento di svolta", da cui derivano "epoca" in italiano, "epoch" in inglese, "époque" in francese. Nel greco antico indicava il momento in cui ci si ferma ad osservare, un punto di sospensione da cui si guarda il mondo con occhi nuovi.

La "a" finale dona al nome un suono latino/italiano, elegante e distintivo, e richiama la tradizione umanistica europea — quella stessa tradizione che ha dato vita alla storiografia, alla filosofia politica e allo studio delle civiltà.

**Epocha** è il luogo dove le ere si osservano, si vivono e si comprendono: una simulazione civilizzazionale dove il tempo e la società si intrecciano, e dove ogni momento può essere il punto di svolta di un'intera civiltà.

L'ispirazione concettuale è la **psicostoriografia** di Hari Seldon (saga della Fondazione, Isaac Asimov): una disciplina che prevede il comportamento delle masse su larga scala, non del singolo individuo, ma delle civiltà intere. Epocha è una psicostoriografia computazionale: invece di equazioni matematiche, usa agenti AI per simulare le dinamiche di massa e osservare pattern emergenti.

---

## Visione

Epocha è un **simulatore di civiltà basato su agenti AI autonomi**. Centinaia di agenti con personalità, storie, debolezze e ambizioni uniche vivono in una società complessa dotata di economia, politica, relazioni sociali e flussi di informazione. La simulazione può coprire scale temporali che vanno da giorni a secoli, generando dinamiche emergenti realistiche.

L'utente può osservare, analizzare, interagire e influenzare il mondo a diversi livelli di coinvolgimento, dal semplice osservatore fino al "dio" che altera il corso della storia.

### Obiettivi

1. **Realismo** — Personalità credibili, dinamiche sociali autentiche, contesto economico e politico realistico
2. **Emergenza** — Le crisi, le alleanze, i conflitti nascono dal basso, dall'interazione tra agenti e regole di sistema
3. **Sperimentazione** — L'utente può iniettare eventi, personaggi, modificare regole e osservare le conseguenze
4. **Analisi** — Dashboard psicostoriografica con trend, pattern, confronto tra scenari su scala generazionale

---

## Architettura di Sistema

### Approccio: Modulare Progressivo

Un'applicazione Django modulare con separazione interna chiara, progettata per essere estratta in servizi quando la scala lo richiede.

```
+---------------------------------------------------------+
|                    FRONTEND (React)                      |
|  +----------+ +----------+ +----------+ +------------+  |
|  | Mappa 2D | |   Chat   | |  Grafo   | |  Analytics |  |
|  | (Pixi.js)| |  Panel   | |(Sigma.js)| |  Dashboard |  |
|  +----------+ +----------+ +----------+ +------------+  |
|                      WebSocket + REST                    |
+--------------------------+------------------------------+
                           |
+--------------------------+------------------------------+
|              DJANGO / DRF (Orchestratore)                |
|                                                          |
|  +--------------+  +--------------+  +--------------+   |
|  |  Simulation  |  |    Agents    |  |    World     |   |
|  |    Engine    |  |    Module    |  |    Module    |   |
|  |              |  |              |  |              |   |
|  | - Tick loop  |  | - Personalita|  | - Economia   |   |
|  | - Tempo      |  | - Memoria   |  | - Risorse    |   |
|  | - Branch     |  | - Decisioni |  | - Politica   |   |
|  | - Auto-stop  |  | - Aggregaz. |  | - Geografia  |   |
|  +--------------+  +--------------+  +--------------+   |
|                          |                               |
|  +-----------------------------------------------+      |
|  |              Event Bus (interno)               |      |
|  +------------------------+----------------------+      |
|                           |                              |
|  +--------+ +--------+ +--------+ +--------+ +--------+ |
|  |  Chat  | |Info    | |Analyti-| |Knowled-| |Scienti-| |
|  | Module | |Flow    | |cs      | |ge Eng. | |fic Mod.| |
|  |        | |        | |        | |        | |        | |
|  | -1-a-1 | |-Passap.| |-Pattern| |-Ricerca| |-Equaz. | |
|  | -Gruppi| |-Media  | |-Trend  | |-K.Graph| |-Paper  | |
|  | -Modal.| |-Distor.| |-Confr. | |-Valida.| |-Calibr.| |
|  +--------+ +--------+ +--------+ +--------+ +--------+ |
+--------------------------+------------------------------+
                           |
            +--------------+--------------+
            |              |              |
       +----+----+   +----+----+   +-----+-----+
       | Celery  |   |  Redis  |   | PostgreSQL |
       | Workers |   |         |   |            |
       |         |   | - State |   | - Agenti   |
       | - Agent |   | - Cache |   | - Storia   |
       |   AI    |   | - PubSub|   | - Branch   |
       | - Tick  |   |         |   | - Analisi  |
       |   proc. |   |         |   |            |
       +----+----+   +---------+   +------------+
            |
       +----+------------------------+
       |   LLM Adapter Layer         |
       |                             |
       | +-------+ +-------+        |
       | |Claude | |OpenAI | ...    |
       | +-------+ +-------+        |
       |                             |
       | - Rate limiting             |
       | - Quota management          |
       | - Fallback chain            |
       | - Supporto abbonamenti      |
       +-----------------------------+
```

### Stack Tecnologico

| Componente | Tecnologia | Motivazione |
|-----------|------------|-------------|
| Backend | Django 5.x + DRF | Scelta dell'utente, ecosistema maturo |
| Task asincroni | Celery + Redis (broker) | Processamento parallelo agenti |
| Database | PostgreSQL + PostGIS + pgvector | Dati relazionali + query spaziali (GeoDjango) + retrieval semantico (embedding). Un unico DB per agenti, mappa, movimenti, prossimita e Knowledge Base |
| Cache/Real-time | Redis | Stato real-time, pub/sub per WebSocket |
| WebSocket | Django Channels | Real-time verso il frontend |
| Frontend | React | Ecosistema ricco per UI complesse |
| Mappa 2D | Pixi.js (WebGL) | Performance con centinaia di sprite |
| Grafo relazionale | Sigma.js | Ottimizzato per grafi grandi (WebGL) |
| Grafici/Analytics | Recharts | Integrazione naturale con React |
| State management | Zustand | Leggero, adatto al use case |
| LLM | Architettura agnostica | Claude, OpenAI, modelli locali, intercambiabili |
| MCP | Model Context Protocol | Epocha come MCP server + client per integrazioni esterne |

---

## Doppia modalita d'uso: App standalone + MCP Server

Epocha funziona in due modalita complementari che possono essere usate insieme.

### App standalone (Web App)

L'esperienza completa con interfaccia visiva:
- Mappa 2D interattiva, dashboard psicostoriografica, grafo relazionale
- Chat integrata con gli agenti
- Controlli simulazione (play/pausa/velocita/fork)
- Configurazione completa (Express + Avanzata)
- Tutto quello che abbiamo progettato nell'interfaccia utente

### MCP Server (Piattaforma integrabile)

Epocha espone un MCP server che permette a qualsiasi client AI di interagire con le simulazioni. L'utente non deve usare la web app: puo controllare tutto conversando con il suo AI preferito.

**Client supportati:**
- **Claude Code** (con piano Max) → interazione conversazionale, l'utente paga solo il suo abbonamento Max
- **Cursor, Windsurf** e altri IDE AI → integrazione in workflow di sviluppo
- **Client MCP custom** → chiunque puo costruire un'applicazione che interagisce con Epocha
- **Altri agenti AI** → agenti esterni possono controllare o osservare le simulazioni

**Tools MCP esposti da Epocha:**

| Tool | Descrizione |
|------|------------|
| `epocha_create_simulation` | Crea una nuova simulazione (Express: da testo/documento, o Avanzata: con parametri) |
| `epocha_simulation_status` | Stato corrente: tempo simulato, popolazione, indicatori, crisi attive |
| `epocha_play` / `epocha_pause` | Controllo play/pausa/velocita della simulazione |
| `epocha_chat_agent` | Parla con un agente specifico (1-a-1 o gruppo) |
| `epocha_inject_character` | Inietta un personaggio (archetipo o descrizione libera) |
| `epocha_inject_group` | Inietta un gruppo organizzato |
| `epocha_inject_event` | Inietta un evento (crisi, disastro, scoperta) |
| `epocha_modify_rules` | Modifica regole del mondo (economia, leggi, risorse) |
| `epocha_fork` | Fork della simulazione da un punto nel tempo |
| `epocha_compare_branches` | Confronta due branch della stessa simulazione |
| `epocha_query_encyclopedia` | Interroga l'Enciclopedia Galattica in linguaggio naturale |
| `epocha_get_analytics` | Metriche, trend, indicatori dalla dashboard psicostoriografica |
| `epocha_get_map_state` | Stato della mappa: posizione agenti, zone, risorse |
| `epocha_get_agent_profile` | Profilo completo di un agente: personalita, memoria, relazioni |
| `epocha_list_simulations` | Lista delle simulazioni attive con metadati |
| `epocha_export` | Esporta simulazione (JSON, DB dump, Enciclopedia PDF) |
| `epocha_seldon_crisis` | Crisi Seldon attive: cause, probabilita esiti, agenti chiave |
| `epocha_kardashev` | Posizione sulla scala di Kardashev |

**Resources MCP (dati consultabili):**

| Resource | Descrizione |
|----------|------------|
| `epocha://simulations` | Lista simulazioni |
| `epocha://simulation/{id}/timeline` | Timeline degli eventi chiave |
| `epocha://simulation/{id}/agents` | Catalogo agenti attivi |
| `epocha://simulation/{id}/map` | Stato della mappa |
| `epocha://simulation/{id}/cycles` | Posizione nei cicli storici |

**Esempio d'uso con Claude Code (Max):**

```
Utente in Claude Code:
> "Connetti a Epocha. Crea una simulazione dell'Italia dal 2026 al 2126.
>  Concentrati sull'impatto dell'AI sul mercato del lavoro."

Claude Code (via MCP):
→ chiama epocha_create_simulation(...)
→ "Simulazione creata. Ricerca iniziale in corso... Knowledge Base pronta.
   Il mondo e stato generato con 200 agenti. Vuoi che la avvii?"

Utente:
> "Si, avviala a velocita 10x. Fammi sapere quando succede qualcosa di interessante."

Claude Code:
→ chiama epocha_play(speed=10)
→ monitora epocha_seldon_crisis() periodicamente
→ "Anno 2041: Crisi Seldon rilevata. La disoccupazione tecnologica ha raggiunto
   il 35%. Tre partiti politici si contendono il potere con visioni opposte
   sull'AI. Vuoi che ti mostri i dettagli o preferisci parlare con il
   leader del movimento anti-AI?"
```

### Knowledge Engine come MCP Client

Il Knowledge Engine di Epocha si connette a MCP server esterni per arricchire la conoscenza:

| MCP Server esterno | Dati forniti |
|-------------------|-------------|
| Wikipedia / Wikidata | Dati storici, geografici, biografici |
| ArXiv / Google Scholar | Paper scientifici, formule, parametri |
| NASA Exoplanet Archive | Catalogo esopianeti reali con parametri fisici |
| World Bank / UN Data | Dati economici, demografici, sviluppo |
| IPCC / Climate Data | Modelli climatici, proiezioni |
| Database geologici | Tettonica, vulcanismo, risorse minerarie |

### Uso combinato App + MCP

Le due modalita funzionano insieme simultaneamente:
- La web app aperta nel browser mostra la mappa e la dashboard in tempo reale
- Claude Code connesso via MCP permette di interagire conversando
- Le azioni via MCP si riflettono immediatamente nella web app (e viceversa)
- Piu client MCP possono essere connessi contemporaneamente (multiplayer via MCP)

### Docker: servizio MCP

Il docker-compose include il servizio MCP server:

| Servizio | Ruolo |
|----------|-------|
| `mcp-server` | MCP server (stdio o SSE) espone tools e resources di Epocha |

L'utente configura il suo client (Claude Code, Cursor, ecc.) puntando all'MCP server di Epocha.

---

## Moduli di Dettaglio

### 1. Simulation Engine

Il cuore del sistema. Gestisce il ciclo di vita della simulazione con un'architettura di orchestrazione gerarchica ispirata ai sistemi distribuiti.

**Orchestrazione gerarchica della societa:**

La simulazione non processa gli agenti in modo piatto (tutti uguali, uno per uno). La societa e organizzata gerarchicamente e il tick segue questa struttura:

```
Orchestratore Globale (control plane)
    |
    +-- Civilta / Macro-regioni (politica estera, guerre, trattati)
    |       |
    |       +-- Nazioni / Regioni (economia regionale, leggi, tasse)
    |       |       |
    |       |       +-- Citta / Comunita (economia locale, ordine pubblico)
    |       |       |       |
    |       |       |       +-- Gruppi / Fazioni (obiettivi collettivi, proteste)
    |       |       |       |       |
    |       |       |       |       +-- Individui (decisioni personali)
    |       |       |       |
    |       |       |       +-- Individui liberi (non affiliati)
    |       |       |
    |       |       +-- Altra citta ...
    |       |
    |       +-- Altra nazione ...
    |
    +-- Altra civilta ... (processata indipendentemente)
```

Ogni livello e un "nodo" che orchestra quelli sotto di se. Le decisioni cascadano verso il basso e i feedback risalgono verso l'alto.

**Ciclo di processing per tick:**

Il tick non e un singolo passaggio ma un ciclo a tre fasi:

```
FASE 1 — Top-down (decisioni macro cascadano verso il basso)

    Orchestratore: valuta lo stato globale
        ↓
    Civilta: decisioni di politica estera (guerra, embargo, alleanza)
        ↓
    Nazioni: reagiscono alle decisioni macro (redistribuzione risorse, mobilitazione)
        ↓
    Citta: adattano le politiche locali (tasse, ordine pubblico)
        ↓
    Gruppi: reagiscono alle condizioni (proteste, cooperazione, scissione)
        ↓
    Individui: decidono in base al contesto (il loro mondo e cambiato dall'alto)


FASE 2 — Bottom-up (feedback individuali risalgono)

    Individui: le loro azioni (protesta, lavoro, migrazione) producono effetti
        ↑
    Gruppi: aggregano il comportamento dei membri (la protesta ha massa critica?)
        ↑
    Citta: il malcontento aggregato impatta la stabilita locale
        ↑
    Nazioni: l'instabilita delle citta impatta l'economia e la politica nazionale
        ↑
    Civilta: le crisi nazionali cambiano gli equilibri internazionali
        ↑
    Orchestratore: aggiorna lo stato globale


FASE 3 — Consolidamento

    - Applicare le conseguenze incrociate (la protesta in Citta A
      ispira una protesta in Citta B)
    - Aggiornare relazioni
    - Registrare eventi
    - Broadcast WebSocket
    - Avanzare il tick
```

**Frequenza di processing per livello:**

Non ogni livello processa ad ogni tick. I livelli alti (civilta, nazioni) prendono decisioni meno frequentemente degli individui:

| Livello | Frequenza di processing | Tipo di decisione |
|---------|------------------------|-------------------|
| Orchestratore globale | Ogni tick | Valutazione stato, coordinamento |
| Civilta | Ogni 10-50 tick | Politica estera, guerre, trattati |
| Nazione | Ogni 5-20 tick | Leggi, tasse, economia nazionale |
| Citta | Ogni 2-10 tick | Politiche locali, ordine pubblico |
| Gruppo | Ogni 1-5 tick | Azioni collettive, strategie di gruppo |
| Individuo | Ogni tick (se risoluzione alta) | Decisioni personali quotidiane |

A risoluzione temporale bassa (anni/decenni), solo i livelli alti processano. A risoluzione alta (ore/giorni), tutti i livelli processano.

**Propagazione degli eventi con ritardo:**

Le decisioni prese ai livelli alti non raggiungono istantaneamente gli individui. L'informazione viaggia attraverso la gerarchia con ritardi e distorsione (collegato all'Information Flow Module):

- Una dichiarazione di guerra della civilta raggiunge le nazioni immediatamente
- Le nazioni comunicano alle citta in 1-2 tick
- Le citta informano i cittadini in 1-3 tick
- La notizia arriva agli individui periferici (campagna, zone isolate) con ulteriore ritardo
- Ad ogni passaggio l'informazione puo distorcersi (passaparola, propaganda, censura)

Questo significa che un individuo in una zona remota potrebbe scoprire una guerra giorni dopo che e iniziata — realistico.

**Conflitto tra livelli:**

Cosa succede quando un livello inferiore si oppone a quello superiore? Questo e il meccanismo delle ribellioni, degli scismi, delle guerre civili:

- Un individuo rifiuta l'ordine del suo gruppo → possibile espulsione o scissione
- Un gruppo sfida la citta → protesta, rivolta, repressione
- Una citta sfida la nazione → secessione, guerra civile
- Una nazione sfida la civilta → uscita dall'alleanza, guerra

Il conflitto tra livelli e uno dei motori principali della storia. Non e un bug, e una feature.

**Leadership emergente:**

La gerarchia non e statica. I leader emergono dal basso:

- Un individuo con tratti di leadership + carisma + circostanze favorevoli sale nella gerarchia
- Il sistema traccia individualmente gli agenti che accumulano influenza
- Quando un gruppo non ha un leader, il sistema valuta chi tra i membri ha le caratteristiche per emergere
- Un leader puo essere rovesciato se perde legittimita (feedback dal basso)

**Rami indipendenti (parallelismo reale):**

Civilta o regioni che non interagiscono tra loro possono essere processate in parallelo reale:

```
Tick 42:
    Civilta A (continente ovest) ──→ [Worker 1] processa indipendentemente
    Civilta B (continente est)   ──→ [Worker 2] processa indipendentemente

    → Si sincronizzano SOLO se c'e un'interazione (commercio, guerra, contatto)
```

Questo e un'ottimizzazione naturale: due civilta che non si conoscono non hanno dipendenze di processing.

**Implementazione progressiva:**

| Fase | Orchestrazione | MVP? |
|------|---------------|------|
| MVP | Piatto (tutti gli agenti sequenziali) | Si |
| v0.2 | Fan-out Celery (agenti in parallelo, stesso tick) | No |
| v0.3 | Gerarchico a 3 livelli (individuo, gruppo, mondo) | No |
| v0.5 | Gerarchico completo (tutti i livelli) | No |
| v1.0 | Gerarchico + parallelismo per civilta indipendenti | No |

L'MVP processa tutto in modo piatto per semplicita. L'interfaccia (`process_single_agent(agent_id, tick)`) e gia progettata per essere compatibile con il fan-out e con l'orchestrazione gerarchica futura.

---

**Tempo ibrido controllabile:**
- Play/Pausa/Velocita variabile
- L'utente puo accelerare, rallentare, mettere in pausa
- La simulazione puo girare autonomamente anche quando l'utente non la guarda

**Risoluzione temporale adattiva:**

Ogni tick rappresenta un'unita di tempo simulato variabile. La risoluzione si adatta automaticamente a cio che sta succedendo nella simulazione:

| Risoluzione | 1 tick = | Quando si attiva | Cosa processa |
|------------|---------|-----------------|---------------|
| Ore | 1 ora simulata | Crisi acute, battaglie, negoziazioni | Ogni agente via LLM, dettaglio massimo |
| Giorni | 1 giorno simulato | Vita quotidiana, decisioni individuali | Ogni agente via LLM |
| Settimane | 1 settimana simulata | Dinamiche sociali, commercio | Agenti rilevanti via LLM, altri via regole |
| Mesi | 1 mese simulato | Economia, politica, stagioni | Modelli matematici + agenti chiave via LLM |
| Anni | 1 anno simulato | Evoluzione lenta, peacetime | Modelli matematici, solo eventi significativi via LLM |
| Decenni | 10 anni simulati | Cicli storici, ascesa/declino | Modelli matematici macro, aggregazione gruppi |
| Secoli | 100 anni simulati | Evoluzione civilizzazionale | Solo modelli macro e milestone tecnologiche |

**Risoluzione adattiva automatica:**
- Quando "non succede niente di importante" → risoluzione bassa (anni, decenni)
- Quando il sistema rileva una crisi, un conflitto, un evento significativo → **rallenta automaticamente** e passa a risoluzione alta (giorni, ore)
- Dopo la crisi → torna a risoluzione bassa
- L'utente puo anche forzare la risoluzione manualmente

In pratica funziona come un film: le parti tranquille passano velocemente ("10 anni dopo..."), i momenti cruciali si vivono in dettaglio.

**Coerenza scientifica a ogni risoluzione:**
- A risoluzione bassa (anni/decenni/secoli): il sistema usa i **modelli matematici** per calcolare i trend macro (demografia, economia, tecnologia) senza chiamare l'LLM per ogni agente. Genera solo gli eventi significativi.
- A risoluzione alta (ore/giorni): ogni agente prende decisioni individuali via LLM con contesto completo.
- La transizione tra risoluzioni e trasparente: i modelli macro e le decisioni individuali sono coerenti tra loro.

**Tempo massimo e condizioni di arresto:**
- L'utente puo definire un limite temporale (es. "simula 200 anni e fermati")
- Condizioni di auto-stop configurabili (es. "fermati quando la civilta collassa", "fermati quando la popolazione scende sotto X")

**Persistenza e shutdown:**
- Lo stato della simulazione e salvato in PostgreSQL ad ogni tick completato
- Se il sistema si spegne (computer spento, Docker fermato, crash), la simulazione si ferma al tick corrente senza perdita di dati
- Al riavvio, l'utente preme "play" e la simulazione riparte esattamente dal tick salvato
- **Graceful shutdown**: quando Docker riceve il segnale di stop, il tick in corso deve completarsi prima della chiusura per evitare stati inconsistenti
- Su deployment cloud (server/VPS), la simulazione continua 24/7 indipendentemente dal computer dell'utente
- Con `restart: unless-stopped` in Docker Compose, il sistema si auto-ripristina dopo crash

| Modalita | Comportamento | Quando usarla |
|----------|-------------|---------------|
| Locale (computer utente) | Si ferma quando Docker si ferma, riprende al riavvio | Esperimenti brevi, testing, sviluppo |
| Cloud (server/VPS) | Continua 24/7, indipendente dal computer | Simulazioni lunghe (secoli), multiplayer |

**Controlli di navigazione temporale:**

La simulazione funziona come un player multimediale per la storia. L'utente ha il pieno controllo del flusso temporale:

| Controllo | Funzione | Comportamento |
|-----------|---------|---------------|
| ⏸ Pausa | Ferma la simulazione | Il tempo si congela, l'utente puo esplorare lo stato corrente |
| ▷ Play | Riprende la simulazione | Avanza tick per tick alla velocita impostata |
| ▷▷ Fast forward | Avanzamento rapido | Salta i tick non significativi, si ferma automaticamente al prossimo evento importante |
| ◁ Rewind | Torna indietro di un tick | Ricarica lo stato dal tick precedente (dal DB) |
| ◁◁ Fast rewind | Torna indietro veloce | Salta al punto saliente precedente (auto-milestone o bookmark) |
| ▷▷\| Vai alla fine | Salta all'ultimo tick | Utile dopo un rewind per tornare al presente della simulazione |
| \|◁◁ Vai all'inizio | Torna al tick 0 | Ricarica lo stato iniziale della simulazione |
| 🔖 Bookmark | Salva il momento corrente | Crea un bookmark con label personalizzata |
| ↗ Fork da qui | Crea un branch | Fork della simulazione dal tick corrente |

**Rewind e replay:**
- Il rewind non "cancella" la storia: i tick futuri restano nel DB
- L'utente puo navigare avanti e indietro nella timeline liberamente
- Se l'utente fa "play" dopo un rewind, ha due opzioni:
  - **Riprodurre**: rivisita i tick gia calcolati (replay dal log, nessun costo LLM)
  - **Forkare e divergere**: crea un branch dal punto corrente e la simulazione riparte con nuove decisioni

**Punti salienti e bookmark:**

Il sistema mantiene due tipi di punti di riferimento sulla timeline:

*Auto-milestone (generati automaticamente):*
Il sistema rileva e salva automaticamente i momenti significativi:
- Crisi Seldon rilevate
- Guerre, rivoluzioni, colpi di stato
- Scoperte scientifiche e tecnologiche
- Cambi di governo o sistema politico
- Crolli o boom economici
- Nascita o estinzione di gruppi/fazioni rilevanti
- Primo contatto tra civilta
- Raggiungimento di soglie sulla scala di Kardashev
- Qualsiasi evento con severity > soglia configurabile

Ogni auto-milestone include: tick, titolo, descrizione, tipo evento, agenti coinvolti.

*Bookmark utente (creati manualmente):*
L'utente puo salvare qualsiasi momento con una label personalizzata:
- "Il fabbro sta per tradire il sindaco"
- "Situazione pre-rivoluzionaria interessante"
- "Punto di partenza per esperimento A/B"
- "Momento di massima stabilita — confronto futuro"

**Snapshot:**
Ogni punto saliente (auto-milestone o bookmark) include uno **snapshot completo** dello stato della simulazione:
- Stato di tutti gli agenti (posizione, salute, ricchezza, umore, relazioni)
- Stato del mondo (economia, risorse, zone)
- Stato politico e sociale
- Questo permette di tornare a quel punto e ripartire esattamente da li, o confrontare lo stato in due momenti diversi

**Navigazione visuale:**
La timeline e visualizzata come una barra con marcatori:
```
|----*--------*--*-----*---------*-----|
tick 0   auto   auto bookmark auto  ultimo tick
         milestone       utente
```
L'utente puo cliccare su qualsiasi marcatore per saltare a quel punto.

**Branching:**
- Fork di una simulazione da qualsiasi punto nel tempo (tick corrente, milestone, o bookmark)
- Ogni branch e una simulazione indipendente con il proprio stato
- Confronto parallelo tra branch (gruppo di controllo vs sperimentale)
- Gestito tramite namespace/prefissi nel DB e in Redis

### 2. Agents Module

Gestisce gli agenti AI — il cuore della simulazione sociale.

**Profilo completo dell'agente:**

Ogni agente e una persona completa, non una caricatura. Il profilo comprende tutte le dimensioni che definiscono un essere umano reale:

*Identita e anagrafica:*
- Nome, eta, genere (maschio, femmina, non-binario)
- Orientamento sessuale (eterosessuale, omosessuale, bisessuale, asessuale)
- Etnia e aspetto fisico (altezza, corporatura, tratti distintivi)
- Lingua madre e lingue parlate

*Personalita (Big Five + estensioni):*
- **Apertura**: curiosita intellettuale, creativita, apertura a nuove esperienze (0.0 → 1.0)
- **Coscienziosita**: disciplina, organizzazione, affidabilita (0.0 → 1.0)
- **Estroversione**: socievolezza, energia, assertivita (0.0 → 1.0)
- **Amabilita**: cooperazione, fiducia, empatia (0.0 → 1.0)
- **Neuroticismo**: instabilita emotiva, ansia, reattivita (0.0 → 1.0)
- Carattere: coraggioso/codardo, generoso/avaro, onesto/disonesto, paziente/impulsivo
- Temperamento: calmo, irascibile, melanconico, sanguigno
- Senso dell'umorismo: assente, sarcastico, empatico, nero

*Capacita cognitive:*
- QI / intelligenza generale (basso, medio, alto, geniale)
- Intelligenza emotiva (capacita di leggere e gestire le emozioni altrui)
- Creativita (pensiero laterale, innovazione)
- Astuzia / intelligenza pratica (furbizia, street smart)
- Capacita di apprendimento (veloce, lenta, specifica per dominio)

*Capacita fisiche:*
- Forza fisica (debole, media, forte, atletica)
- Resistenza / stamina
- Agilita e coordinazione
- Capacita atletiche specifiche (nuoto, corsa, combattimento, equitazione)
- Aspettativa di vita base (influenzata da genetica e condizioni)

*Salute e condizioni:*
- Stato di salute attuale (sano, malato, cronico, disabile)
- Patologie congenite o acquisite (cecita, sordita, malattie croniche, disturbi mentali)
- Dipendenze (alcol, sostanze, gioco)
- Disabilita fisiche (mobilita ridotta, menomazioni)
- Salute mentale (depressione, ansia, PTSD da eventi traumatici nella simulazione)
- Fertilita (influenza la demografia)

*Background e storia:*
- Storia personale: esperienze formative, traumi, successi
- Classe sociale di origine (influenza opportunita e visione del mondo)
- Educazione ricevuta (analfabeta, base, avanzata, specialistica)
- Professione e competenze lavorative
- Stato economico (povero, medio, ricco, ereditato vs guadagnato)

*Psicologia e motivazioni:*
- Ambizioni e obiettivi: cosa vuole dalla vita (potere, ricchezza, amore, conoscenza, pace, vendetta)
- Paure e fobie (morte, solitudine, poverta, fallimento, altezze, buio)
- Debolezze (vizi, tentazioni, punti ciechi)
- Valori morali (cosa considera giusto/sbagliato, quanto e disposto a compromettere)
- Credenze religiose/spirituali (fervente, tiepido, ateo, agnostico, superstizioso)
- Ideologia politica (conservatore, progressista, radicale, apatico)

*Capacita sociali:*
- Capacita di leadership (naturale, acquisita, assente)
- Carisma (quanto influenza gli altri con la presenza)
- Capacita di persuasione e manipolazione
- Empatia (alta → si preoccupa degli altri, bassa → egocentrico)
- Attitudine: ottimista/pessimista, attivo/passivo, proattivo/reattivo
- Affinita e compatibilita: tratti che attraggono o respingono certi tipi di persone

*Sessuali e relazionali:*
- Orientamento sessuale (influenza con chi forma relazioni romantiche)
- Stile di attaccamento (sicuro, ansioso, evitante — influenza la qualita delle relazioni)
- Desiderio di famiglia (forte, debole, assente)
- Fedeltà (leale, opportunista, seriale)

**Generazione del profilo:**

Non tutti i tratti vengono specificati esplicitamente per ogni agente. Il sistema funziona a livelli:

| Livello | Cosa si specifica | Quando |
|---------|------------------|--------|
| Generazione Express | L'LLM genera un profilo completo coerente da una descrizione breve ("un fabbro ambizioso") | Creazione del mondo |
| Tratti critici | Big Five, genere, eta, ruolo, background — sempre definiti esplicitamente | Sempre |
| Tratti secondari | QI, capacita fisiche, patologie — generati con distribuzione realistica | Se non specificati dall'utente |
| Tratti emergenti | Dipendenze, PTSD, cambiamenti di personalita — emergono dalla simulazione | Durante la simulazione |

I tratti secondari seguono **distribuzioni realistiche**: il QI segue una curva gaussiana (media 100, deviazione standard 15), le patologie hanno prevalenze basate su dati reali, l'orientamento sessuale segue le statistiche demografiche del contesto storico/culturale.

I tratti non sono statici: un evento traumatico puo aumentare il neuroticismo, una posizione di leadership puo aumentare l'assertivita, una dipendenza puo emergere da stress prolungato, la salute mentale puo deteriorarsi.

**Memoria umana realistica:**
- Ricordi recenti: vividi e dettagliati
- Ricordi emotivamente forti: persistono a lungo (tradimento, lutto, vittoria)
- Ricordi ordinari: sbiadiscono, si semplificano, possono distorcersi nel tempo
- Ricordi sociali: il "sentito dire" e meno affidabile del vissuto direttamente
- Implementazione: sistema a decadimento con peso emotivo che rallenta la perdita

**Aggregazione dinamica individuo/gruppo:**
Il sistema gestisce una gerarchia fluida:

```
Societa
|-- Individuo libero
|-- Gruppo (agente collettivo)
|   |-- Sotto-gruppo (fazione interna)
|   |   |-- individuo (membro generico)
|   |   +-- individuo (membro generico)
|   |-- Sotto-gruppo
|   |   +-- individuo (membro generico)
|   +-- * Individuo emergente (tracciato singolarmente)
+-- Individuo libero
```

Regole di aggregazione:
- **Individuo -> Gruppo**: quando N agenti convergono su valori/obiettivi simili, si fondono in un agente-gruppo
- **Gruppo -> Individui**: quando la tensione interna supera una soglia, il gruppo si frammenta
- **Emergenza individuale**: un membro puo emergere dal gruppo (leader, dissidente) e tornare ad essere tracciato individualmente
- **Sotto-gruppi**: fazioni interne possono formarsi dentro un gruppo, creando gerarchie a piu livelli
- **Il gruppo porta con se** la memoria collettiva e i tratti dominanti dei suoi membri

**Ciclo di vita:**
- Gli agenti invecchiano, si ammalano, muoiono
- Nascono nuovi agenti (figli che ereditano tratti culturali e genetici con variazioni)
- Immigrazione/emigrazione
- Eredita culturale: valori, credenze, pregiudizi si trasmettono tra generazioni (con mutazioni)
- Eredita economica: ricchezza, proprieta, debiti passano tra generazioni
- Memoria collettiva: la societa ricorda (o distorce) la storia. Eroi diventano miti o vengono dimenticati

### 3. World Module

Le regole del mondo in cui vivono gli agenti.

**Economia a complessita selezionabile:**

| Livello | Descrizione |
|---------|-------------|
| Semplificato | Benessere generico per agente |
| Base | Moneta, lavoro, stipendio, compravendita |
| Completo | Mercato domanda/offerta, inflazione, tasse, classi sociali, imprese, disoccupazione, debito |

L'utente sceglie il livello di complessita economica prima di avviare la simulazione.

**Sistemi politici e di governo:**

Ogni civilta ha un sistema di governo che non e una label statica ma un **meccanismo funzionante** con regole proprie. Il sistema puo cambiare nel tempo (transizioni, rivoluzioni, degenerazione).

*Sistemi di governo simulabili:*

| Sistema | Come funziona nella simulazione | Come mantiene il potere | Come cade |
|---------|-------------------------------|------------------------|-----------|
| Democrazia | Elezioni periodiche, gli agenti votano in base a personalita e condizioni. Candidati emergono dai gruppi. Partiti si formano per aggregazione | Legittimita popolare, istituzioni indipendenti, alternanza | Crisi economica → populismo, corruzione → sfiducia, emergenza → poteri speciali che non finiscono |
| Democrazia illiberale / Democratura | Elezioni formali ma manipolate. Media controllati, opposizione indebolita. L'apparenza democratica maschera il controllo autoritario | Propaganda, controllo dell'informazione, repressione selettiva, clientelismo | Crisi economica che il regime non puo nascondere, leader che perde il controllo della narrazione |
| Autocrazia / Dittatura | Un agente con tratti autoritari concentra il potere. Decisioni centralizzate, nessun contrappeso | Forza militare, lealta comprata, paura, culto della personalita | Morte del dittatore (crisi di successione), rivolta popolare, colpo di stato interno |
| Monarchia | Potere ereditario. Il monarca governa, la corte compete per influenza | Legittimita dinastica, tradizione, esercito leale, alleanze matrimoniali | Incompetenza dell'erede, rivolta nobiliare, rivoluzione popolare |
| Oligarchia | Un gruppo ristretto (ricchi, militari, clan) controlla il potere. Decisioni prese tra pochi | Ricchezza concentrata, controllo delle risorse, rete di favori | Conflitto interno tra oligarchi, rivolta della popolazione esclusa |
| Teocrazia | Autorita religiosa = autorita politica. Le leggi derivano dalla dottrina | Fede come legittimita, controllo dell'educazione, conformismo sociale | Secolarizzazione, scandali religiosi, generazioni che perdono la fede |
| Regime totalitario | Controllo totale: politica, economia, cultura, vita privata. Polizia segreta, delazione | Terrore, propaganda pervasiva, eliminazione del dissenso | Morte del leader, stagnazione economica, pressione esterna |
| Regime terroristico | Governo basato sul terrore sistematico. Esecuzioni pubbliche, persecuzioni di gruppo | Paura paralizzante, eliminazione di chiunque possa organizzare resistenza | Esaurimento (il terrore non e sostenibile a lungo), intervento esterno |
| Anarchia | Assenza di governo centrale. Autogestione locale, assemblee | Non serve mantenerlo — e l'assenza di struttura | Emerge spontaneamente un leader forte, o un gruppo si impone con la forza |
| Federazione | Entita autonome unite da un patto. Governo centrale limitato | Beneficio reciproco, difesa comune, commercio | Divergenza di interessi, secessione, centralizzazione eccessiva |
| Cleptocrazia | Governanti che usano il potere per arricchirsi. Corruzione sistematica | Rete di corruzione che coinvolge tutti i livelli, chi denuncia viene eliminato | Collasso economico, intervento esterno, rivolta quando la popolazione non ha piu nulla da perdere |
| Giunta militare | Militari al potere dopo un colpo di stato | Forza delle armi, coprifuoco, soppressione liberta | Divisioni interne, pressione internazionale, transizione negoziata |

*Transizioni tra sistemi:*

Le transizioni non sono casuali — seguono pattern storici documentati:

```
Democrazia → Democratura → Autocrazia
    (erosione graduale: emergenza, poteri speciali, media controllati, elezioni manipolate)

Autocrazia → Caos → Democrazia o nuova autocrazia
    (rivolta, vuoto di potere, chi lo riempie per primo vince)

Monarchia → Rivoluzione → Repubblica o Dittatura
    (dipende da chi guida la rivoluzione e quanto e organizzato)

Anarchia → Autocrazia
    (il vuoto di potere viene riempito dal piu forte o dal piu organizzato)

Qualsiasi sistema → Regime totalitario
    (in condizioni di crisi estrema, paura, e un leader carismatico/spietato)
```

Il sistema monitora gli indicatori che precedono le transizioni (fiducia nelle istituzioni, disuguaglianza, corruzione, coesione militare) e le rende possibili quando le condizioni sono mature.

**Stratificazione sociale e disuguaglianza:**

La societa simulata non e piatta — ha classi, caste, disuguaglianze che emergono e si evolvono:

| Strato | Come emerge | Effetto sulla societa |
|--------|------------|----------------------|
| Elite / Ultra-ricchi | Accumulo di ricchezza generazionale, posizioni di potere, monopoli | Influenzano la politica, accesso esclusivo a risorse, possono corrompere istituzioni |
| Classe agiata | Professionisti, mercanti di successo, proprietari | Stabilita sociale, consumo, aspirazione di mobilita verso l'alto |
| Classe media | Lavoratori qualificati, artigiani, piccoli commercianti | Spina dorsale dell'economia, piu vulnerabile alle crisi, motore delle rivoluzioni quando si impoverisce |
| Classe lavoratrice | Lavoratori manuali, operai, contadini dipendenti | Forza lavoro, vulnerabile a sfruttamento, potenziale rivoluzionario |
| Poveri / Emarginati | Disoccupati, malati, senza risorse | Tensione sociale, criminalita per sopravvivenza, invisibili al potere |
| Schiavi / Sottomessi | Prigionieri di guerra, debitori, nascita in schiavitu | Lavoro forzato, nessun diritto, fonte di rivolta se le catene si indeboliscono |

*Dinamiche di classe:*
- La disuguaglianza cresce naturalmente se non controbilanciata (chi ha ricchezza accumula piu ricchezza)
- Mobilita sociale: un individuo puo salire o scendere in base a talento, fortuna, relazioni, circostanze
- Quando il Gini coefficient supera una soglia critica, la probabilita di rivolta cresce esponenzialmente
- Le rivoluzioni spesso partono dalla classe media impoverita, non dai piu poveri (che non hanno le risorse per organizzarsi)

**Criminalita e economia sommersa:**

La criminalita non e un evento casuale — e un fenomeno sociale con cause e struttura:

*Criminalita individuale:*
- Agenti in poverta estrema con bassa agreeableness hanno probabilita di commettere crimini per sopravvivenza
- Agenti con alta neuroticism e bassa conscientiousness in ambienti degradati tendono al comportamento antisociale
- Il furto, la violenza, la truffa sono azioni possibili per qualsiasi agente in condizioni sufficientemente disperate

*Criminalita organizzata:*
- Emerge dove lo stato e debole e la disuguaglianza e alta
- Si struttura come un gruppo con gerarchia, leader, territorio, economia parallela
- Offre "servizi" che lo stato non fornisce: protezione, giustizia informale, credito
- Corrompe le istituzioni, creando un ciclo vizioso (stato piu debole → crimine piu forte)
- Mafie, cartelli, bande: gruppi emergenti con obiettivi economici e territoriali

*Terrorismo:*
- Emerge da ideologie estreme (politiche, religiose, nazionaliste) in condizioni di oppressione o radicalizzazione
- Piccoli gruppi con alta coesione e obiettivi distruttivi
- Impatto sproporzionato rispetto alla dimensione del gruppo (pochi individui destabilizzano un'intera societa)
- Genera reazione dello stato che puo essere proporzionata (intelligence, giustizia) o sproporzionata (repressione di massa, che alimenta altro terrorismo)

*Corruzione:*
- Presente in qualsiasi sistema ma con intensita diversa
- Cresce con: burocrazia eccessiva, stipendi pubblici bassi, assenza di controlli, cultura dell'impunita
- Erode le istituzioni dall'interno — tra le cause principali del collasso delle civilta
- Puo diventare sistemica: non un'eccezione ma la norma ("se tutti rubano, chi non ruba e lo stupido")

**Istituzioni:**

Le istituzioni non sono astrazioni — sono strutture con persone, risorse, legittimita:

| Istituzione | Funzione | Quando funziona | Quando fallisce |
|-------------|---------|-----------------|-----------------|
| Giustizia | Risolvere conflitti, punire crimini | Indipendente, finanziata, rispettata | Corrotta, lenta, politicizzata |
| Istruzione | Trasmettere conoscenza, formare cittadini | Accessibile, finanziata, libera | Censurata, elitaria, sottofinanziata |
| Sanita | Curare malati, prevenire epidemie | Universale, competente | Accessibile solo ai ricchi, sottofinanziata |
| Esercito | Difesa, ordine interno | Leale allo stato, professionale | Politicizzato, usato per repressione, corsa a colpo di stato |
| Media | Informare, controllare il potere | Liberi, plurali, indipendenti | Controllati dal governo o dai ricchi, propaganda |
| Religione organizzata | Senso, comunita, etica | Separata dal potere politico | Fusa con il potere, corrotta, fanatica |
| Burocrazia | Amministrare lo stato | Efficiente, meritocratica | Elefantiaca, corrotta, auto-referenziale |

Ogni istituzione ha un livello di "salute" che influenza il funzionamento della societa. Istituzioni sane stabilizzano, istituzioni malate destabilizzano.

**Geografia (PostGIS + GeoDjango):**
- Mappa con zone distinte (quartieri, citta, campagna) rappresentate come poligoni PostGIS
- Risorse naturali distribuite geograficamente con coordinate reali
- Infrastrutture (strade, edifici, piazze) come geometrie spaziali
- Gli agenti si muovono nello spazio con posizione tracciata come punto PostGIS
- Query spaziali native: "chi si trova nel raggio di X dalla piazza?", "quali agenti sono in questa zona?"
- Calcolo di prossimita per interazioni sociali (gli agenti vicini interagiscono piu facilmente)
- Propagazione spaziale di eventi (epidemie, rivolte, disastri con epicentro e buffer zone di diffusione)
- Per simulazioni dal mondo reale: importazione dati geografici reali (confini, citta, fiumi, risorse)

**Risorse:**
- Cibo, acqua, energia, materie prime
- Scarsita e abbondanza generano dinamiche sociali
- Commercio tra zone diverse

### Espansione spaziale e civilta interstellare

Se la simulazione si estende su secoli o millenni, la civilta potrebbe sviluppare tecnologie per l'esplorazione e la colonizzazione spaziale. Il World Module si espande per gestire scale cosmiche.

**Fasi di espansione spaziale (emergono dalla simulazione, non sono scriptate):**

| Fase | Scala | Tecnologie necessarie | Dinamiche sociali |
|------|-------|----------------------|-------------------|
| Pre-orbitale | Terra | Razzi chimici, satelliti | Competizione tra nazioni, corsa allo spazio |
| Orbitale | Orbita terrestre | Stazioni spaziali, turismo orbitale | Economia orbitale, mining asteroidale, diritto spaziale |
| Sistema solare interno | Luna, Marte, asteroidi | Propulsione avanzata, habitat chiusi | Colonie semi-autonome, identita coloniale, tensioni Terra-colonie |
| Sistema solare esterno | Giove, Saturno, Fascia di Kuiper | Propulsione nucleare/ionica, ecosistemi chiusi | Indipendenza coloniale, nuove culture, religioni spaziali |
| Interstellare | Sistemi stellari vicini | Propulsione a fusione/antimatter, navi generazionali o criogeniche | Civilta isolate, divergenza culturale totale, millenni di viaggio |

**Conoscenze scientifiche integrate:**

- **Meccanica orbitale**: equazioni di Keplero, trasferimenti di Hohmann, manovre gravitazionali, finestre di lancio — il Knowledge Engine ricerca dati reali da NASA/ESA per calibrare tempi e costi
- **Astrofisica**: distanze stellari reali, zone abitabili, catalogo esopianeti reali (database NASA Exoplanet Archive)
- **Equazione di Tsiolkovsky**: vincoli fisici reali su delta-v, massa propellente, limiti dei sistemi di propulsione
- **Ecologia spaziale**: modelli di ecosistemi chiusi (dati da Biosphere 2, ISS), terraforming, bilancio atmosferico
- **Medicina spaziale**: effetti della microgravita, radiazioni cosmiche, limiti biologici umani in ambiente spaziale

**Dinamiche sociali nello spazio:**

Le colonie spaziali non sono solo avamposti tecnologici ma societa complete con le proprie dinamiche:
- **Economia**: commercio interplanetario (quali risorse valgono il costo di trasporto?), economia di scarsita estrema nelle colonie
- **Politica**: governance delle colonie (dipendenza dalla Terra vs autonomia), dichiarazioni di indipendenza, federazioni interplanetarie
- **Cultura**: divergenza culturale accelerata dall'isolamento, nuove religioni nate nello spazio, identita "marziana" vs "terrestre"
- **Militare**: conflitti spaziali con vincoli fisici reali (distanze, delta-v, comunicazioni ritardate)
- **Ecologia**: fragilita degli ecosistemi artificiali, catastrofi ambientali in habitat chiusi

**Contatto con vita aliena:**

Se la simulazione raggiunge scale interstellari, il Knowledge Engine integra:
- **Equazione di Drake**: stima probabilistica del numero di civilta nella galassia
- **Paradosso di Fermi**: perche non abbiamo trovato nessuno? Varie ipotesi come filtri possibili
- **Scenari di contatto**: il sistema genera forme di vita/civilta aliene basandosi su vincoli biologici e fisici reali
  - Vita microbica (piu probabile, impatto scientifico enorme ma sociale limitato)
  - Vita complessa non tecnologica (impatto su biologia, filosofia, religione)
  - Civilta tecnologica (impatto totale: politico, militare, religioso, economico, esistenziale)
- **Reazioni degli agenti**: ogni agente reagisce al contatto alieno secondo la propria personalita — paura, curiosita, fervore religioso, opportunismo economico, paranoia militare
- **Vincolo di realismo**: le comunicazioni interstellari hanno ritardi di anni/decenni (velocita della luce), le civilta aliene non devono essere antropomorfe

**Mappa multi-scala:**

La visualizzazione si adatta alla scala della civilta:
- Scala terrestre: mappa 2D classica (PostGIS)
- Scala sistema solare: vista orbitale con pianeti, asteroidi, rotte di trasferimento
- Scala interstellare: mappa stellare con sistemi colonizzati, rotte, tempi di viaggio

---

### Scienze naturali e planetologia

Il sistema deve possedere conoscenze approfondite delle scienze naturali terrestri e usarle come base per generare in modo rigoroso le caratteristiche di altri mondi.

#### Conoscenze terrestri (Knowledge Base fondamentale)

Il Knowledge Engine ricerca e struttura conoscenze reali nei seguenti domini:

**Ecologia:**
- Ecosistemi terrestri (foreste, deserti, oceani, tundra, praterie)
- Catene alimentari e reti trofiche
- Cicli biogeochimici (carbonio, azoto, fosforo, acqua)
- Biodiversita e interazioni tra specie
- Impatto antropico, deforestazione, desertificazione
- Capacita di carico degli ecosistemi

**Geologia:**
- Tettonica a placche, vulcanismo, sismologia
- Ciclo delle rocce, erosione, sedimentazione
- Risorse minerarie e loro distribuzione
- Storia geologica della Terra (ere, estinzioni di massa)
- Formazione e evoluzione dei suoli

**Biologia:**
- Evoluzione e selezione naturale
- Genetica e ereditarieta (influenza su tratti degli agenti)
- Microbiologia (epidemie, fermentazione, agricoltura)
- Fisiologia umana (limiti fisici, longevita, adattamento)
- Biologia marina e terrestre

**Zoologia:**
- Fauna per bioma e periodo storico
- Domesticazione animale e il suo impatto sulla civilta
- Zoonosi (malattie animale-uomo)
- Estinzioni e loro cause

**Climatologia:**
- Modelli climatici, correnti oceaniche, monsoni
- Ere glaciali e periodi caldi
- Impatto del clima su agricoltura, migrazioni, conflitti
- Cambiamento climatico antropogenico

#### Generazione rigorosa di esopianeti

Quando la simulazione raggiunge la scala interstellare, il sistema genera mondi alieni basandosi su **parametri fisici reali**, non su fantasia. Ogni esopianeta e determinato da:

**Parametri stellari (input):**
- Tipo spettrale della stella (O, B, A, F, G, K, M)
- Massa, luminosita, eta della stella
- Metallicita (influenza la composizione planetaria)
- Stabilita (variabilita, flare, fase evolutiva)

**Parametri orbitali (input):**
- Distanza dalla stella (semi-asse maggiore)
- Eccentricita orbitale
- Inclinazione assiale (stagioni)
- Periodo di rotazione (durata del giorno)
- Presenza di lune (effetti su maree, stabilita assiale)

**Parametri planetari (input):**
- Massa e raggio (determina gravita superficiale)
- Composizione (roccioso, gassoso, oceanico)
- Campo magnetico (protezione da radiazioni)

**Caratteristiche derivate (calcolate dal sistema con modelli fisici reali):**

| Caratteristica | Calcolata da | Modello scientifico |
|----------------|-------------|-------------------|
| Zona abitabile | Luminosita stella, albedo pianeta | Modello di Kopparapu (2013) |
| Temperatura superficiale | Distanza, atmosfera, albedo, effetto serra | Bilancio radiativo, modello greenhouse |
| Composizione atmosferica | Massa pianeta, temperatura, vulcanismo | Outgassing, fotochimica, equilibrio chimico |
| Presenza acqua liquida | Temperatura, pressione atmosferica | Diagramma di fase dell'acqua |
| Gravita superficiale | Massa, raggio | g = GM/r² |
| Durata anno/giorno | Parametri orbitali | Leggi di Keplero |
| Maree | Massa luna, distanza | Forze gravitazionali |
| Radiazione superficiale | Tipo stella, campo magnetico, atmosfera | Modelli di schermatura |

**Generazione ecologica aliena:**

Se le condizioni fisiche lo permettono, il sistema genera ecosistemi alieni basandosi su vincoli biologici reali:
- **Biochimica**: carbonio + acqua (come la Terra)? O alternative plausibili (silicio, solventi alternativi come ammoniaca o metano)?
- **Energia**: fotosintesi con quale spettro stellare? Chemiosintesi? Altre fonti?
- **Gravita**: organismi piu bassi e robusti con alta gravita, piu alti e fragili con bassa gravita
- **Atmosfera**: composizione influenza metabolismo (ossigeno, metano, idrogeno)
- **Evoluzione**: tempo disponibile (eta del pianeta), pressioni selettive, nicchie ecologiche
- **Nessun antropomorfismo**: la vita aliena non deve assomigliare alla vita terrestre se le condizioni sono diverse

Il risultato e un pianeta con ecologia, geologia, clima e potenziale biologico **scientificamente coerente**, non inventato. I dati vengono dal catalogo NASA Exoplanet Archive per i pianeti reali, o generati da modelli astrofisici per pianeti fittizi.

---

### 4. Scientific Models Engine

A differenza di approcci puramente LLM-driven (come MiroFish, che non usa modelli matematici ne validazione scientifica), Epocha integra **modelli scientifici rigorosi** per calcolare i trend macro della civilta. Questo e un differenziatore fondamentale: i modelli matematici danno il rigore, gli agenti LLM danno il realismo comportamentale. Insieme sono molto piu potenti di entrambi da soli.

#### Approccio ibrido: Modelli matematici + LLM

```
Modelli matematici → calcolano trend macro (economia, demografia, clima)
        ↓
LLM → interpretano i risultati e decidono come gli agenti reagiscono
        ↓
Agenti → prendono decisioni che influenzano i parametri dei modelli
        ↓
Modelli → ricalcolano con i nuovi parametri
        ↓
(loop ad ogni tick)
```

I modelli non sostituiscono gli agenti: li informano. Un agente non "sa" che l'inflazione e al 15%, ma ne subisce gli effetti (prezzi alti, stipendio che non basta) e reagisce secondo la sua personalita.

#### Modelli matematici per dominio

| Dominio | Modelli / Equazioni | Fonte scientifica | Cosa calcolano |
|---------|--------------------|--------------------|----------------|
| Economia | Equilibrio generale, curva di Phillips, equazione di Fisher, modello IS-LM | Letteratura macroeconomica | PIL, inflazione, disoccupazione, tassi di interesse |
| Disuguaglianza | Coefficiente di Gini, curva di Lorenz, indice di Theil | Economia del benessere | Distribuzione ricchezza, tensioni di classe |
| Demografia | Crescita logistica, transizione demografica, tavole di mortalita/fecondita | UN Population Division | Popolazione, natalita, mortalita, struttura per eta |
| Epidemie | Modello SIR/SEIR (Susceptible-Infected-Recovered) | Epidemiologia matematica | Diffusione malattie, ondate pandemiche, immunita |
| Clima | Modelli di feedback climatico semplificati, bilancio radiativo | IPCC, climatologia | Temperature, eventi estremi, impatto su agricoltura |
| Diffusione innovazione | Curva S di Rogers, modello Bass | Sociologia dell'innovazione | Adozione tecnologie, diffusione idee |
| Conflitti | Modelli di Lanchester (attrition) | Studi strategici | Esiti militari, equilibri di deterrenza |
| Teoria dei giochi | Nash, dilemma del prigioniero iterato, Shapley, aste, voto | Economia comportamentale, scienze politiche | Interazioni strategiche, cooperazione, alleanze, negoziazione |
| Reti sociali | Granovetter (weak/strong ties), cascate informative, soglie di attivazione | Sociologia delle reti | Formazione gruppi, viralita, mobilitazione |
| Risorse | Curva di Hubbert (deplezione), carrying capacity, rendimenti decrescenti | Ecologia, geologia | Esaurimento risorse, sostenibilita, carestie |
| Commercio | Vantaggio comparato (Ricardo), gravita del commercio | Economia internazionale | Flussi commerciali, specializzazione, dipendenze |
| Urbanizzazione | Legge di Zipf, modello di Von Thunen | Geografia economica | Crescita citta, distribuzione spaziale attivita |
| Astrofisica / Navigazione | Meccanica orbitale (Keplero, Lambert), equazione di Tsiolkovsky, finestre di lancio | Astrodinamica, NASA/ESA | Viaggi spaziali, trasferimenti orbitali, delta-v |
| Esplorazione spaziale | Equazione di Drake, paradosso di Fermi, modelli di colonizzazione | Astrobiologia, SETI | Probabilita vita aliena, espansione interstellare |
| Ecologia planetaria | Modelli di terraforming, bilancio atmosferico, zone abitabili | Planetologia | Abitabilita esopianeti, sostenibilita colonie |

#### Il Knowledge Engine come ricercatore scientifico

Prima della simulazione, il Knowledge Engine non cerca solo informazioni generiche ma anche:

- **Paper scientifici** da arXiv, Google Scholar, PubMed, SSRN per ogni dominio rilevante
- **Formule e parametri** estratti dalla letteratura (es. tasso di riproduzione base R0 per diverse epidemie storiche)
- **Dati storici reali** per calibrare i modelli (es. crescita demografica europea dal 1000 al 2000)
- **Dataset pubblici** da World Bank, UN, IPCC, FAO per parametri iniziali

I modelli vengono **calibrati sui dati storici** prima dell'avvio: se la simulazione parte dall'Europa del 1200, i parametri demografici, economici e climatici riflettono i dati storici reali di quel periodo.

#### Livelli di rigore scientifico (configurabile)

| Livello | Descrizione | Uso |
|---------|-------------|-----|
| Semplificato | Regole qualitative senza equazioni (es. "piu disuguaglianza → piu instabilita") | Simulazioni rapide, esplorative |
| Standard | Modelli matematici di base calibrati su dati storici | Uso generale, buon equilibrio rigore/performance |
| Rigoroso | Modelli completi con parametri da paper scientifici, validazione incrociata | Esperimenti sociali seri, ricerca |

L'utente sceglie il livello di rigore nelle impostazioni, analogamente al livello di complessita economica.

#### Teoria dei giochi come framework trasversale

La teoria dei giochi non e un dominio specifico (come economia o clima) ma un framework trasversale che attraversa tutte le interazioni strategiche tra agenti. E il ponte matematico tra i modelli macro e le decisioni individuali.

**Principio di integrazione:**

La teoria dei giochi non sostituisce l'LLM nelle decisioni — calcola l'**esito razionale** di un'interazione e lo passa come contesto all'LLM, che poi decide tenendo conto della personalita dell'agente. Un agente razionale seguira l'equilibrio di Nash; un agente impulsivo no. Questo produce comportamenti realistici: a volte le persone fanno la scelta sbagliata, ed e proprio quello che genera storie interessanti.

```
Interazione strategica rilevata (commercio, conflitto, alleanza, voto)
    ↓
Game Theory Engine:
    1. Classifica il tipo di gioco
    2. Calcola equilibrio/esito ottimale
    3. Calcola payoff per ogni strategia possibile
    ↓
Contesto arricchito passato all'LLM:
    "L'equilibrio razionale sarebbe cooperare (payoff: +5 per entrambi).
     Tradire darebbe +8 a te ma -3 all'altro.
     Tu sei impulsivo (neuroticism: 0.8) e diffidente (agreeableness: 0.2).
     L'altro ti ha tradito 2 volte in passato."
    ↓
LLM decide in base a personalita + contesto strategico
```

**Modelli di gioco implementati:**

*Interazioni bilaterali (2 agenti):*

| Tipo di gioco | Quando si attiva | Cosa calcola | Esempio nella simulazione |
|---------------|-----------------|-------------|--------------------------|
| Dilemma del prigioniero (singolo) | Due agenti devono scegliere se cooperare o tradire senza comunicare | Equilibrio di Nash: tradire e dominante, ma cooperare e Pareto-ottimale | Due mercanti decidono se rispettare un accordo commerciale |
| Dilemma del prigioniero iterato | Stessi agenti interagiscono ripetutamente nel tempo | Strategia ottimale cambia: Tit-for-Tat, perdono, reputazione | Vicini di casa, colleghi, partner commerciali abituali |
| Gioco della fiducia (trust game) | Un agente deve fidarsi di un altro (investimento, prestito, delega) | Quantifica il rischio razionale della fiducia dato lo storico | Un contadino presta sementi a un vicino — le restituira? |
| Gioco del pollo (chicken) | Due agenti in rotta di collisione, chi cede per primo? | Equilibrio misto: nessuno vuole cedere ma lo scontro e il peggiore esito | Due fazioni rivali che si contendono un territorio |
| Contrattazione di Nash | Due parti negoziano la divisione di un surplus | Punto di Nash: divisione ottimale dato il potere negoziale di ciascuno | Negoziazione salariale, trattato di pace, accordo commerciale |
| Gioco dell'ultimatum | Una parte propone, l'altra accetta o rifiuta (niente per entrambi) | Soglia di accettabilita: offerte troppo basse vengono rifiutate per orgoglio | Tributo imposto da un conquistatore — troppo alto e la rivolta e piu conveniente |

*Interazioni collettive (N agenti):*

| Tipo di gioco | Quando si attiva | Cosa calcola | Esempio nella simulazione |
|---------------|-----------------|-------------|--------------------------|
| Tragedia dei beni comuni | Risorsa condivisa sfruttata da molti agenti | Tasso di deplezione vs cooperazione; punto di collasso | Pascolo condiviso, pesca, acqua |
| Problema del bene pubblico (free rider) | Contribuzione volontaria a un bene che beneficia tutti | Chi contribuisce? Chi fa il free rider? Soglia di contribuzione minima | Difesa comune, manutenzione strade, sistema educativo |
| Giochi di coalizione (Shapley value) | Formazione di alleanze tra gruppi/nazioni | Valore marginale di ogni membro della coalizione; chi e indispensabile? | Alleanza militare: ogni membro quanto contribuisce? Chi esce? |
| Gioco di coordinamento | Agenti devono accordarsi su una scelta comune senza comunicazione diretta | Equilibri multipli: quale prevale dipende da aspettative e focal points | Adozione di uno standard (moneta, lingua franca, sistema di misura) |
| Voto strategico (teoria del voto) | Elezioni, referendum, decisioni assembleari | Vincitore di Condorcet, paradosso di Arrow, voto strategico vs sincero | Elezioni: gli agenti votano per chi preferiscono o per il "male minore"? |
| Asta | Vendita di risorse scarse al miglior offerente | Prezzo di equilibrio, maledizione del vincitore, strategie di offerta | Concessione mineraria, appalto pubblico, vendita di terra |
| Deterrenza (MAD) | Due potenze con capacita distruttiva reciproca | Equilibrio del terrore: nessuno attacca per primo perche la risposta e catastrofica | Nazioni con armi potenti; civilta avanzate con tecnologie devastanti |

**Integrazione efficiente nel tick:**

La teoria dei giochi non si applica a ogni interazione — sarebbe troppo costoso. Il sistema la attiva **solo quando rileva interazioni strategiche significative**:

```
Per ogni tick:
    1. L'economia e il mondo si aggiornano (modelli macro)
    2. Per ogni agente, il sistema valuta le sue interazioni:
        a. Interazione di routine (lavoro, riposo) → decisione semplice, NO game theory
        b. Interazione strategica rilevata:
           - L'agente e in conflitto con un altro → game theory
           - L'agente deve negoziare risorse → game theory
           - C'e una risorsa condivisa contesa → game theory
           - C'e un'elezione/voto → game theory
        c. Game Theory Engine calcola l'equilibrio
        d. L'equilibrio viene passato come contesto all'LLM
    3. Le decisioni vengono applicate
```

**Trigger per l'attivazione:**
- Due agenti con relazione di rivalita nella stessa zona → potenziale dilemma/chicken
- Risorsa condivisa con piu di 3 agenti che la usano → tragedia dei beni comuni
- Agente che deve decidere se fidarsi di qualcuno → trust game
- Negoziazione commerciale tra agenti o gruppi → contrattazione di Nash
- Elezione o decisione assembleare → voto strategico
- Alleanza militare in formazione → gioco di coalizione

**Performance:**
- I calcoli di game theory sono **deterministici e veloci** (millisecondi, non richiedono LLM)
- Si attivano solo per il ~10% delle interazioni (quelle strategicamente rilevanti)
- Il costo computazionale e trascurabile rispetto alle chiamate LLM
- Possono essere pre-calcolati in batch per tutte le interazioni del tick

**Evoluzione delle strategie nel tempo:**

Il sistema traccia le strategie adottate dagli agenti nel tempo:
- Un agente che coopera sempre viene sfruttato → impara a difendersi (o no, se la sua personalita e troppo amabile)
- Un agente che tradisce sempre perde alleati → si ritrova isolato
- Le strategie vincenti si diffondono nella societa (gli agenti osservano e imitano chi ha successo)
- Emergono norme sociali: "qui si coopera" o "qui ognuno per se" a seconda della storia della comunita

Questo crea **evoluzione culturale delle strategie** — esattamente quello che Axelrod ha dimostrato nei tornei del dilemma del prigioniero iterato (1984). Le societa che sviluppano norme cooperative prosperano; quelle che non lo fanno si frammentano.

**Dilemma del prigioniero iterato — il cuore della cooperazione sociale:**

Il dilemma del prigioniero giocato una volta porta al tradimento razionale. Ma iterato (stessi agenti che si reincontrano), la cooperazione emerge naturalmente perche tradire ha costi futuri. Epocha simula questo con la memoria e le relazioni:

- L'agente A tradisce l'agente B → B lo ricorda → B non coopera piu con A → A perde un alleato
- La reputazione si diffonde via passaparola (Information Flow) → anche C e D sanno che A e inaffidabile
- A lungo termine, gli agenti che cooperano costruiscono reti di fiducia piu forti

La strategia Tit-for-Tat (coopera, poi imita l'altro) emerge naturalmente dagli agenti con buona memoria e amabilita media. Gli agenti troppo amabili vengono sfruttati; quelli troppo diffidenti restano isolati. Il punto di equilibrio dipende dalla composizione della societa — e questo e un risultato emergente, non scriptato.

#### Validazione e calibrazione continua

Durante la simulazione:
- I modelli vengono ricalcolati ad ogni tick con i parametri aggiornati dalle azioni degli agenti
- Periodicamente (es. ogni 50 anni simulati) un LLM "validatore scientifico" verifica che i risultati dei modelli siano coerenti con la letteratura scientifica
- Se i risultati divergono significativamente dai pattern storici conosciuti senza una causa chiara nella simulazione, il sistema segnala l'anomalia
- L'utente puo decidere se l'anomalia e un errore da correggere o un esito emergente interessante da osservare

---

### 5. Information Flow Module (invariato)

Come le informazioni viaggiano nella societa — fondamentale per il realismo.

**Canali di informazione:**
- **Esperienza diretta**: l'agente vede/vive qualcosa di persona (massima affidabilita)
- **Passaparola**: un agente racconta a un altro (distorsione progressiva)
- **Media/fonti pubbliche**: annunci, giornali, proclami (ampia diffusione, possibile propaganda)
- **Rumor**: voci che si propagano nella rete sociale, con distorsione crescente

**Meccaniche:**
- Ogni informazione ha un livello di affidabilita che degrada con i passaggi
- Gli agenti decidono se credere o meno in base alla fonte, alla propria personalita e alle proprie esperienze
- La propaganda e la manipolazione emergono naturalmente
- I pregiudizi influenzano come le informazioni vengono interpretate e ritrasmesse

### 6. Chat Module

Gestisce l'interazione tra l'utente e gli agenti.

**Modalita di interazione:**

| Modalita | Identita utente | Effetto sulla simulazione |
|----------|----------------|--------------------------|
| Osservatore | Intervistatore invisibile | Nessuno — le conversazioni non alterano il mondo |
| Abitante | Un personaggio nel mondo | Le conversazioni hanno conseguenze reali |
| Dio | Entita superiore | Puo dare ordini, cambiare regole, provocare eventi |

**Tipi di conversazione:**
- **1-a-1**: click su un agente, si apre la chat nel pannello laterale
- **Gruppo**: click su un luogo (piazza, bar, ufficio), si parla con tutti gli agenti presenti
- Gli agenti di gruppo reagiscono tra loro e all'utente con dinamiche di gruppo

**Comportamento degli agenti in chat:**
- Rispondono coerentemente con la propria personalita e stato emotivo attuale
- Sanno cosa gli e successo nella simulazione (memoria)
- In modalita Dio: reagiscono con timore, devozione, ribellione... a seconda della personalita
  - Un ribelle potrebbe ignorare i comandi
  - Un leader religioso potrebbe seguire ciecamente
  - Un razionalista potrebbe mettere in dubbio l'esistenza divina

**Adattamento del tempo durante la chat:**

Quando l'utente apre una chat, il tempo della simulazione si adatta automaticamente per evitare che un personaggio invecchi o muoia tra un messaggio e l'altro:

| Modalita | Comportamento del tempo durante la chat |
|----------|----------------------------------------|
| Osservatore | La chat avviene "fuori dal tempo". E come un'intervista a un momento congelato. La simulazione puo continuare in background, ma l'agente risponde dallo stato in cui si trovava quando la chat e stata aperta. |
| Abitante | La simulazione **rallenta automaticamente** a risoluzione ore/giorni. Le parole dell'utente hanno conseguenze e servono tick lenti per simularle. Quando la chat si chiude, il tempo torna alla velocita precedente. |
| Dio | Come l'abitante: la simulazione rallenta. I comandi divini devono essere processati in tempo "umano". |
| Seconda Fondazione | La simulazione **si mette in pausa**. Le manipolazioni invisibili sono delicate e richiedono precisione. |

Flusso:
```
Simulazione a 10 anni/tick (velocita massima)
    ↓
L'utente apre la chat con un agente
    ↓
Il sistema automaticamente:
    1. Completa il tick corrente
    2. Riduce la risoluzione a giorni/ore
    3. Rallenta la velocita
    ↓
L'utente chatta (tempo "umano")
    ↓
L'utente chiude la chat
    ↓
Il sistema torna alla risoluzione e velocita precedenti
```

**Se il personaggio e gia morto:**
- L'utente puo consultare l'**Enciclopedia Galattica**: "Chi era Marco il fabbro? Cosa ha fatto nella sua vita?"
- Il sistema suggerisce i **discendenti o successori** con cui chattare
- L'utente puo fare un **fork** per tornare al periodo in cui il personaggio era vivo e parlare con lui

### 7. Analytics Module — Dashboard Psicostoriografica

Il layer analitico per osservare i pattern civilizzazionali.

**Zoom temporale dinamico:**
- Scala di visualizzazione: giorni, mesi, anni, decenni, secoli
- L'utente sceglie la granularita dell'analisi

**Metriche e indicatori:**
- Indice di stabilita/instabilita sociale
- Distribuzione della ricchezza (coefficiente di Gini)
- Curve di potere (chi detiene il potere nel tempo)
- Umore collettivo e fiducia nelle istituzioni
- Crescita/declino demografico
- Indici economici (PIL virtuale, inflazione, disoccupazione)

**Confronto tra branch:**
- Grafici sovrapposti che mostrano come la stessa societa evolve diversamente nei vari scenari
- Analisi delta: cosa e cambiato e perche

**Rilevamento pattern:**
- Il sistema identifica pattern ricorrenti
- Esempio: "ogni volta che la disuguaglianza supera X, entro Y anni scoppia una rivolta"
- Correlazioni tra eventi e conseguenze su scala generazionale

**Timeline storica:**
- Vista cronologica degli eventi chiave su scala di secoli
- Filtri per tipo di evento (politico, economico, sociale, militare)
- Evidenziazione dei punti di svolta

### 8. LLM Adapter Layer

Astrazione per supportare qualsiasi provider AI, con architettura a livelli per ottimizzare costi e qualita.

**Nota importante:** I piani in abbonamento consumer (Claude Max, ChatGPT Plus, Gemini Advanced) non sono utilizzabili programmaticamente. Sono pensati per uso umano interattivo. Anthropic ha esplicitamente bloccato i workaround (proxy via OAuth token) a gennaio 2026. L'unico accesso programmatico affidabile e tramite API key (pay-per-token) o modelli locali.

#### Architettura a 3 livelli (Model Routing)

Il sistema sceglie automaticamente il modello in base alla complessita della decisione dell'agente:

| Livello | % Chiamate | Tipo decisione | Modelli consigliati | Costo indicativo |
|---------|-----------|----------------|--------------------|--------------------|
| Livello 1 - Locale | ~88% | Azioni quotidiane, movimenti, reazioni semplici | vLLM/Ollama + Qwen 3.5 7B | $0 (solo hardware) |
| Livello 2 - API economica | ~8% | Decisioni sociali, commercio, voto | GPT-5 Nano ($0.05/M), Gemini Flash-Lite ($0.10/M), Haiku 4.5 ($1/M) | ~$0.001/richiesta |
| Livello 3 - API premium | ~2% | Crisi, leadership, discorsi, svolte storiche | Sonnet 4.6 ($3/M), Opus 4.6 ($5/M), GPT-5.4 ($1.25/M) | ~$0.02/richiesta |
| Livello 4 - Subagent | ~2% | Strategie complesse, Crisi Seldon, leader in momenti critici | Claude Agent SDK, OpenAI Agents SDK | ~$0.10-0.50/decisione |

**Stima costi:** 200 agenti, 20.000 decisioni/giorno → ~$6-18/giorno (vs $200-500 con solo modelli premium).

#### Livello 4: Subagent per decisioni critiche

La maggior parte delle decisioni degli agenti e semplice ("lavoro", "riposo", "commercio") e una singola API call basta. Ma nei momenti critici — una Crisi Seldon, un leader che decide se dichiarare guerra, uno scienziato che fa una scoperta rivoluzionaria — serve un ragionamento multi-step.

In questi casi il sistema promuove la decisione a un **subagent** dotato di tools:

```
Situazione critica rilevata (alta severity, agente leader, Crisi Seldon)
    ↓
Subagent attivato con tools:
    - query_world_state()      → economia, risorse, stabilita
    - query_relationships()    → alleati, nemici, forza relativa
    - query_recent_events()    → cosa e successo di recente
    - query_knowledge()        → precedenti storici, conseguenze note
    - evaluate_options()       → pro/contro di ogni possibile azione
    ↓
Ragionamento multi-step (5-15 chiamate interne)
    ↓
Decisione strategica argomentata
```

**Quando si attiva il subagent:**
- Crisi Seldon rilevata dal sistema
- Agente con ruolo di leader (capo di stato, generale, leader religioso)
- Decisione con severity > 0.7 (guerra, rivoluzione, scoperta epocale)
- L'utente sta osservando specificamente quell'agente
- Il tick e a risoluzione alta (ore/giorni) e il momento e narrativamente importante

**Quando NON si attiva:**
- Decisioni quotidiane (90% dei casi)
- Agenti generici senza ruolo di leadership
- Tick a risoluzione bassa (anni/decenni)
- Budget in esaurimento

La differenza qualitativa e significativa. Un'API call semplice produce: `{"action": "declare_war", "reason": "they attacked us"}`. Un subagent produce: "Ho valutato la situazione: la nostra economia e forte ma l'esercito e indebolito dalla recente epidemia. Il nemico ha piu soldati ma e diviso internamente. Le mie alleanze con il Nord sono solide. Il popolo chiede vendetta per l'attacco. Dichiaro guerra, ma con una strategia difensiva iniziale per guadagnare tempo mentre l'esercito si riprende."

#### Provider supportati

| Provider | Modello economico | Costo (Input/Output per 1M token) | Batch -50% | Free tier |
|----------|------------------|------------------------------------|------------|-----------|
| Locale (vLLM/Ollama) | Qwen 3.5 7B, Llama 3.3 8B | $0 | N/A | Illimitato |
| OpenAI | GPT-5 Nano | $0.05 / $0.40 | Si | No |
| Google | Gemini Flash-Lite 2.5 | $0.10 / $0.40 | No | Si (1000 req/giorno) |
| Groq | Llama 3.1 8B | $0.06 blended | Si | Si (limitato) |
| Anthropic | Haiku 4.5 | $1 / $5 | Si | No |
| OpenRouter | Modelli gratuiti + 200+ modelli | $0+ | No | Si (200 req/giorno) |
| Together AI | Vari | da $0.10 | Si | No |

**Nota su vLLM vs Ollama:** Per alta concorrenza (centinaia di agenti), vLLM e nettamente superiore (145ms vs 3200ms di latenza con 50 richieste concorrenti). Ollama e preferibile per prototipazione e sviluppo.

#### Ottimizzazioni costi

- **Prompt Caching**: Anthropic offre 90% di sconto sui cache hit. Con centinaia di agenti che condividono lo stesso system prompt (regole del mondo, contesto), il risparmio e enorme
- **Batch API**: 50% di sconto (Anthropic, OpenAI, Groq). Per simulazioni a turni (non real-time), ideale: si accumulano le decisioni di tutti gli agenti per un tick e si inviano in batch
- **Aggregazione gruppo**: L'aggregazione individuo/gruppo riduce il numero totale di chiamate LLM
- **Decision Trees + LLM ibrido**: Per azioni ripetitive (movimento, routine quotidiana), usare template deterministici senza LLM. Usare LLM solo per decisioni che richiedono ragionamento

#### Gestione risorse

- Rate limiting per provider (rispetto dei limiti API di ogni tier)
- Fallback chain: se un provider non risponde, passa al successivo
- Budget massimo configurabile (giornaliero/mensile) con alert
- Monitoraggio costi in tempo reale nella dashboard
- Stima costi prima di avviare la simulazione

#### Configurazione utente

L'utente nelle impostazioni della simulazione puo:
- Scegliere quali provider attivare (locale, API, mix)
- Inserire le chiavi API per ogni provider
- Configurare il routing (quale modello per quale tipo di decisione)
- Impostare un budget massimo con auto-pausa al raggiungimento
- Scegliere tra modalita real-time o batch (batch = 50% risparmio, risultati differiti)
- Visualizzare costo stimato prima dell'avvio e costo effettivo in tempo reale

---

## Interfaccia Utente

### Layout principale

La schermata e dominata dalla mappa 2D con rendering WebGL (Pixi.js).

**Componenti:**
1. **Mappa 2D** (centro) — Vista principale con agenti che si muovono, luoghi, edifici
   - Level of detail: a basso zoom, agenti raggruppati in cluster; ad alto zoom, singoli individui
   - Viewport culling: renderizza solo cio che e visibile
2. **Pannello statistiche** (alto a destra, comprimibile) — Indicatori macro con trend
3. **Feed eventi** (basso, barra orizzontale) — Eventi filtrati per la zona visibile nel viewport
4. **Pannello laterale** (destra, su click agente) — Profilo, relazioni (micro-grafo), chat
5. **Vista grafo** (toggle) — Vista relazionale completa accessibile da un bottone

### Adattamento per modalita

| Modalita | Viewport | Feed | Controlli speciali |
|----------|----------|------|-------------------|
| Osservatore | Mappa intera, zoom libero | Globale | Nessuno |
| Chat | Mappa sullo sfondo, pannello chat espanso | Filtrato per agente | Input conversazione |
| Influenza | Mappa + heatmap di propagazione | Globale + effetti | Pannello iniezione eventi |
| Abitante | Centrato su avatar utente, zoom fisso quartiere | Solo rete sociale propria | Azioni personaggio |
| Dio | Mappa intera + overlay di potere | Tutti gli eventi | Pannello comandi divini |

### Controlli simulazione

Barra di controllo in alto:
- Play / Pausa
- Slider velocita (1x, 10x, 100x, 1000x)
- Indicatore tempo simulato (giorno/mese/anno corrente)
- Bottone "Fork" per creare un branch
- Selettore branch attivo
- Selettore livello di complessita economica
- Tempo massimo / condizioni di arresto

---

## Input System — Come alimentare il mondo iniziale

Il punto di partenza della simulazione richiede dati complessi: geografia, popolazione, economia, politica, tecnologia, cultura, religione. L'utente puo scegliere tra quattro modalita di input, combinabili tra loro.

### Modalita di input

**A) Template preconfigurati**
Preset pronti all'uso che l'utente puo selezionare e personalizzare:
- Storici: "Europa medievale 1200", "Impero Romano 100 d.C.", "Rivoluzione industriale 1800"
- Contemporanei: "Mondo attuale 2026", "Citta moderna", "Nazione emergente"
- Speculativi: "Post-apocalittico", "Colonia spaziale", "Societa post-scarsita"

Ogni template definisce: mappa, distribuzione popolazione, livello tecnologico, sistema politico, economia, cultura.

**B) Descrizione naturale + AI**
L'utente descrive il mondo a parole e l'AI genera tutto:
- Input: "Una societa agricola con 500 persone, due villaggi rivali sulle sponde di un fiume, risorse scarse, tensioni religiose tra culto solare e culto lunare"
- Output: mappa generata, agenti con personalita coerenti, economia agricola, strutture sociali, tensioni pre-esistenti

**C) Documento sorgente**
L'utente fornisce documenti da cui il sistema estrae il mondo:
- Testi storici, articoli accademici, dati demografici reali
- Il sistema estrae entita, relazioni, contesto e costruisce il mondo iniziale
- Utile per simulazioni basate su situazioni reali (es. "cosa sarebbe successo se...")

**D) Configurazione manuale dettagliata**
UI con form strutturati per definire ogni parametro:
- Numero e distribuzione agenti (eta, genere, professione, personalita)
- Mappa e risorse (zone, risorse naturali, infrastrutture)
- Sistema economico (livello di complessita, distribuzione ricchezza)
- Sistema politico (tipo di governo, istituzioni)
- Livello tecnologico (punto di partenza nell'albero tecnologico)
- Cultura e religione

Le modalita sono combinabili: si puo partire da un template, arricchirlo con una descrizione naturale e poi raffinare manualmente i dettagli.

---

## Knowledge Engine — Il motore della conoscenza

Componente fondamentale che costruisce e mantiene la base di conoscenza necessaria per simulare evoluzioni realistiche su scala di secoli. Il sistema non puo inventare evoluzioni credibili basandosi solo sulla conoscenza generica di un LLM: ha bisogno di conoscenza approfondita e strutturata costruita a partire da ricerche reali.

### Fase 1: Pre-simulazione — Costruzione della Knowledge Base

Quando l'utente configura una simulazione, il Knowledge Engine esegue ricerche web approfondite per dominio:

| Dominio | Cosa ricerca | Esempio |
|---------|-------------|---------|
| Scienza e tecnologia | Storia delle scoperte, ordine cronologico, prerequisiti, condizioni necessarie | Come si e passati dalla metallurgia del bronzo a quella del ferro? |
| Fisica e ingegneria | Principi fondamentali, concatenazione logica, applicazioni pratiche | Quali conoscenze servono per costruire un motore a vapore? |
| Astronomia e matematica | Sviluppo storico, dipendenze tra discipline | Perche la trigonometria e servita prima della navigazione oceanica? |
| Sociologia e antropologia | Pattern di evoluzione sociale, formazione di istituzioni, dinamiche di gruppo | Come emergono le democrazie? Quali condizioni le precedono? |
| Scienze politiche | Nascita e caduta dei sistemi di governo, rivoluzioni, transizioni | Quali fattori portano al collasso di un impero? |
| Economia | Sviluppo dei sistemi economici, commercio, moneta, crisi | Come nasce l'inflazione? Quando emerge il credito? |
| Religione e filosofia | Nascita, diffusione, trasformazione dei sistemi di credenze | Quali tensioni sociali generano nuovi movimenti religiosi? |
| Militare | Evoluzione strategia e tecnologia bellica, impatto sulla societa | Come la polvere da sparo ha cambiato gli equilibri politici? |
| Clima e ambiente | Impatto del clima sulla civilta, risorse, catastrofi naturali | Come le glaciazioni hanno influenzato le migrazioni? |
| Medicina e biologia | Epidemie, longevita, salute pubblica | Come le pandemie hanno accelerato cambiamenti sociali? |

### Fase 2: Strutturazione in Knowledge Graph

Le conoscenze raccolte vengono strutturate in un grafo di dipendenze:

```
Ogni nodo (scoperta/innovazione/evento) ha:
- Prerequisiti: cosa deve esistere prima
- Condizioni necessarie: risorse, popolazione, istituzioni
- Probabilita base: quanto e probabile che emerga quando le condizioni ci sono
- Catalizzatori: cosa accelera la scoperta (guerra, commercio, crisi)
- Conseguenze: cosa cambia nella societa dopo la scoperta
- Tempo tipico: quanto impiega storicamente a diffondersi
```

Esempio di catena nel grafo:
```
Agricoltura
  prerequisiti: nessuno (emerge da raccolta)
  condizioni: clima favorevole, terra fertile
  conseguenze: sedentarieta, surplus alimentare, crescita demografica
    ↓
Irrigazione
  prerequisiti: agricoltura, osservazione idraulica
  condizioni: fiumi, necessita di surplus
  conseguenze: aumento resa, specializzazione lavoro
    ↓
Urbanizzazione
  prerequisiti: irrigazione, surplus alimentare
  condizioni: popolazione > soglia, commercio
  conseguenze: classi sociali, artigianato specializzato, necessita di governance
    ↓
Scrittura
  prerequisiti: urbanizzazione, commercio
  condizioni: necessita di contabilita e comunicazione
  conseguenze: trasmissione conoscenza, leggi scritte, storia
```

### Fase 3: Durante la simulazione — Consultazione e arricchimento

Ad ogni tick significativo (es. ogni "decennio" simulato), il Knowledge Engine:

1. **Valuta le condizioni attuali** della civilta rispetto al grafo di conoscenza
2. **Identifica scoperte/innovazioni mature** (prerequisiti soddisfatti, condizioni presenti)
3. **Calcola probabilita** di emersione, influenzata da:
   - Catalizzatori attivi (guerra → innovazione militare, commercio → diffusione idee)
   - Agenti con tratti "innovatore" o "scienziato" nella civilta
   - Risorse disponibili per la ricerca
   - Pressione sociale (necessita genera invenzione)
4. **Se una scoperta scatta**, la attribuisce a un agente credibile e propaga le conseguenze
5. **Se necessario**, fa nuove ricerche web per approfondire un dominio specifico

### Simulazioni dal presente verso il futuro

Per simulazioni che partono dal mondo attuale e proiettano secoli avanti, il Knowledge Engine adotta un approccio specifico basato su orizzonti temporali.

#### Ricerca dello stato attuale del mondo

Al momento dell'avvio, il sistema ricerca:
- **Geopolitica**: alleanze, conflitti, tensioni attuali, equilibri di potere
- **Economia**: PIL per paese, debito, disuguaglianza, trend commerciali
- **Demografia**: tassi di natalita, invecchiamento, migrazioni, urbanizzazione
- **Clima**: modelli climatici IPCC, proiezioni temperature, risorse idriche
- **Energia**: mix energetico globale, transizione rinnovabili, curve esaurimento fossili
- **Tecnologie in sviluppo**: stato attuale di fusione nucleare, AI, biotecnologia, quantum computing, esplorazione spaziale, neuroscienze

#### Framework di plausibilita per orizzonte temporale

| Orizzonte | Approccio | Fonti di conoscenza |
|-----------|----------|-------------------|
| 0-30 anni | Estrapolazione da trend reali | Dati attuali, roadmap tecnologiche, proiezioni accademiche |
| 30-100 anni | Scenari multipli con biforcazioni | Pattern storici, vincoli fisici, conseguenze logiche dei trend |
| 100-300 anni | Speculazione vincolata dalla scienza | Leggi fisiche, pattern civilizzazionali storici, limiti biologici |
| 300-1000 anni | Evoluzione emergente dal sistema | Conseguenze logiche a cascata di tutto cio che e successo prima |

#### Biforcazioni: i punti di svolta

Il Knowledge Engine identifica i momenti in cui la storia potrebbe prendere direzioni radicalmente diverse. Ogni biforcazione e un punto in cui la simulazione "sceglie" un percorso basandosi sullo stato della civilta:

Esempio di biforcazione al ~2050:
```
Fusione nucleare commercialmente viable?
    ↓ SI                              ↓ NO
Energia abbondante              Crisi energetica
    ↓                                ↓
Crescita economica              Conflitti per risorse
Desalinizzazione                Migrazioni climatiche
Colonizzazione Marte            Guerre per acqua/energia
    ↓                                ↓
[cascata di conseguenze]        [cascata di conseguenze]
```

La scelta non e casuale: dipende dallo stato degli agenti, dalla ricerca accumulata, dalle risorse investite, dai conflitti in corso.

#### Vincoli di coerenza

Per evitare scenari incoerenti su scale temporali lunghe:

**Vincoli fisici invalicabili:**
- Leggi della termodinamica (nessuna energia infinita)
- Velocita della luce (nessun viaggio FTL)
- Limiti biologici umani (senza intervento genetico)
- Risorse finite del pianeta (senza fonti esterne)

**Vincoli logici:**
- Ogni stato deve essere conseguenza logica dello stato precedente
- Se una risorsa e esaurita, non puo ricomparire
- Le tecnologie perdute devono essere riscoperte, non "ricordate"
- I cambiamenti culturali richiedono generazioni, non anni

**Validazione periodica:**
A intervalli regolari (es. ogni 50 anni simulati), un LLM "validatore" analizza lo stato complessivo della civilta e verifica:
- Lo stato attuale e plausibile data la storia simulata?
- Ci sono contraddizioni o anacronismi?
- I trend sono coerenti con le cause che li hanno generati?
Se rileva incoerenze, le segnala e le corregge.

#### Registro storico

Il sistema mantiene un registro completo di tutto cio che e accaduto nella simulazione:
- Ogni scoperta, quando, dove, da chi, perche
- Ogni crisi, le sue cause, le sue conseguenze
- Ogni cambiamento politico, economico, culturale
- Le biforcazioni scelte e le alternative scartate

Questo registro alimenta sia la dashboard psicostoriografica sia la validazione di coerenza.

### Persistenza della Knowledge Base

- **PostgreSQL + PostGIS + pgvector**: storage strutturato, query spaziali (mappa, prossimita, propagazione) e retrieval semantico (embedding vettoriali) in un unico database
- **Knowledge Graph**: grafo di dipendenze tecnologiche/scientifiche/sociali
- **Cache locale**: le ricerche web vengono salvate per evitare ricerche duplicate
- La Knowledge Base e condivisa tra branch della stessa simulazione (la conoscenza possibile e la stessa, cambia cosa viene scoperto)

---

## Modalita d'ingresso

Epocha offre due modalita d'ingresso per abbattere la barriera di accesso, ispirate al successo di progetti come MiroFish dove la semplicita d'uso e il fattore chiave di adozione.

### Modalita Express

Un campo di testo e un bottone "Go". Zero configurazione.

**Input possibili:**
- Testo libero: "Simula l'Italia dal 2026 al 2126, concentrati sull'impatto dell'AI sul mercato del lavoro"
- Upload documento: un articolo, un report, un testo storico
- URL: un link a una notizia o a un paper

**Cosa fa il sistema:**
1. Analizza l'input e determina il tipo di simulazione (storica, contemporanea, futura)
2. Esegue ricerche web automatiche per costruire la Knowledge Base
3. Genera il mondo: mappa, agenti, economia, politica, cultura
4. Sceglie automaticamente i parametri ottimali (numero agenti, complessita economica, scala temporale)
5. Parte la simulazione
6. L'utente osserva e interagisce quando vuole

La modalita Express non e una versione ridotta: usa lo stesso motore della modalita avanzata, semplicemente l'AI prende tutte le decisioni di configurazione al posto dell'utente.

### Modalita Avanzata

Accesso completo a tutti i parametri di configurazione:
- Scelta tra template, descrizione naturale, documento sorgente, configurazione manuale (combinabili)
- Controllo su ogni aspetto: agenti, economia, politica, geografia, Knowledge Engine
- Configurazione provider LLM e budget
- Definizione condizioni di arresto e tempo massimo

L'utente puo anche partire in modalita Express e poi passare ad Avanzata per raffinare i parametri prima dell'avvio.

---

## Progetto Open Source

Epocha e un progetto open source. L'architettura e progettata per favorire contributi, estensioni e riuso da parte della community.

### Licenza e contributi

- Licenza open source (da definire: MIT, Apache 2.0, o AGPL in base alla strategia)
- Repository pubblica con documentazione per contributor
- Architettura modulare che facilita contributi isolati (un contributor puo lavorare su un modulo senza toccare gli altri)

### Predisposizione alla condivisione (Fase 2 — evoluzione futura)

L'architettura del core e predisposta per una futura piattaforma di condivisione, ma l'implementazione della community non fa parte della prima release.

**Cosa si implementa ora nel core:**
- Formato standard di export/import simulazioni (JSON + DB dump)
- Metadati per ogni simulazione: descrizione, parametri, screenshot automatici, timeline degli eventi chiave
- Identificatore univoco per ogni simulazione e branch
- API di export che produce un pacchetto autonomo e riproducibile

**Cosa si implementa dopo (Fase 2), basandosi sull'uso reale della community:**
- Hub di condivisione simulazioni
- Fork sociale: prendi la simulazione di un altro utente e crea un branch
- Template community: utenti che creano e condividono mondi iniziali
- Sfide/esperimenti collettivi: stesso mondo di partenza, variabili diverse, confronto risultati
- Rating e discovery delle simulazioni piu interessanti

### Visibilita e versioning delle simulazioni

Ogni simulazione ha un livello di visibilita che l'owner controlla:

| Visibilita | Chi vede | Chi puo forkare | Chi puo modificare |
|------------|---------|-----------------|-------------------|
| **Private** (default) | Solo l'owner | Nessuno | Solo l'owner |
| **Shared** | Owner + collaboratori invitati | I collaboratori | Owner (collaboratori possono iniettare variabili se permesso) |
| **Public** | Tutti gli utenti | Tutti | Nessuno (immutabile una volta pubblica) |

**Versioning:**
- Una volta resa pubblica o condivisa, la simulazione diventa **immutabile** (nessuno puo modificarla, nemmeno l'owner)
- L'owner puo creare **nuove versioni** (v1, v2, v3...) con modifiche
- I fork partono sempre da una versione specifica e immutabile
- Lo storico delle versioni e visibile a tutti i viewer
- Questo protegge chi forka: il mondo da cui sei partito non cambia sotto i piedi

**Ruoli utente:**

| Ruolo | Permessi |
|-------|----------|
| **Owner** | Controllo totale: crea, modifica, cancella, condivide, cambia visibilita, crea versioni |
| **Collaborator** | Osserva, chatta con agenti, forka, inietta variabili (se l'owner lo permette) |
| **Viewer** | Solo lettura: osserva e chatta con gli agenti |
| **Staff/Admin** | Promuove simulazioni in "Featured", modera contenuti, gestisce utenti, crea template ufficiali |

**Staff/Admin:**
- Curano una sezione "Featured" con le simulazioni piu interessanti della community
- Moderano contenuti inappropriati
- Gestiscono utenti (ban, assegnazione ruoli)
- Possono creare simulazioni "ufficiali" come template per la community (es. "Ancient Rome", "Medieval Europe")

### Mondi collaborativi e multiplayer

Epocha supporta diverse modalita di collaborazione tra utenti sullo stesso mondo.

#### Modalita di collaborazione

**1. Fork e divergenza (asincrono)**
- Un utente pubblica la propria simulazione (visibilita Public o Shared)
- Un altro utente fa un fork da qualsiasi punto temporale di una versione specifica
- Ognuno prosegue in modo indipendente con le proprie scelte
- I risultati possono essere confrontati: "stesso mondo, scelte diverse, esiti diversi"
- Non serve essere online contemporaneamente

**2. Mondo condiviso (sincrono/asincrono)**
- Piu utenti partecipano allo stesso mondo come co-gestori
- Ogni utente puo avere un ruolo diverso:

| Ruolo | Cosa puo fare | Esempio d'uso |
|-------|-------------|---------------|
| Creatore | Controllo totale, configura tutto, gestisce permessi | Chi ha creato il mondo |
| Co-sperimentatore | Iniettare eventi e personaggi, forkare, osservare | Ricercatore che collabora a un esperimento |
| Osservatore | Solo osservare, chattare con agenti, consultare l'enciclopedia | Studente, curioso, giornalista |
| Abitante | Vive nel mondo come personaggio, interagisce con gli agenti | Giocatore immersivo |
| Dio locale | Controlla una regione/nazione specifica del mondo | Ogni utente "governa" una civilta diversa |

**3. Civilta competitive (multiplayer)**
- Ogni utente controlla (in modalita Dio locale o Seconda Fondazione) una civilta diversa nello stesso mondo
- Le civilta evolvono, competono, commerciano, si scontrano
- Gli agenti AI prendono le decisioni autonomamente ma l'utente puo influenzare la direzione
- Simile a un gioco di strategia ma con agenti AI che hanno volonta propria — il "popolo" puo rifiutare le direttive dell'utente se non sono coerenti con i loro valori

**4. Esperimenti collettivi (community science)**
- Un mondo viene pubblicato con un "protocollo sperimentale": stessa configurazione iniziale, ogni partecipante inietta una variabile diversa
- I risultati di tutti i partecipanti vengono aggregati e confrontati statisticamente
- Esempio: "100 utenti hanno simulato lo stesso mondo medievale, 50 hanno iniettato una pandemia e 50 no — ecco le differenze statistiche nei risultati"
- Questo e vero crowdsourced social science

#### Gestione dei permessi e della coerenza

**Permessi:**
- Il creatore definisce chi puo fare cosa (matrice ruoli/azioni)
- I permessi possono essere granulari: "puoi iniettare personaggi ma non eventi climatici"
- Sistema di inviti o accesso pubblico/privato

**Coerenza in mondi multi-utente:**
- Le azioni di piu utenti contemporanei vengono serializzate dal Simulation Engine (nessun conflitto)
- Se due utenti danno ordini contraddittori nella stessa area, il sistema chiede risoluzione o applica priorita per ruolo
- La cronologia delle azioni di ogni utente viene tracciata nel registro storico

#### Predisposizione tecnica nel core (Fase 1)

Anche se il multiplayer completo e Fase 2, il core deve essere predisposto:
- **Ogni simulazione ha un owner e una lista di collaboratori** con ruoli
- **Le azioni dell'utente sono registrate con user_id** nel registro storico
- **Le API supportano autenticazione multi-utente** fin dall'inizio
- **Il branching supporta "parent simulation" remota** (fork da simulazione di un altro utente)
- **WebSocket supporta piu client connessi** allo stesso mondo contemporaneamente

**Sequenza pianificata:**
```
Fase 1: Core engine funzionante → rilascio open source
Fase 2: La community inizia a usarlo, condivide risultati manualmente
Fase 3: Si osserva come la community vuole condividere
Fase 4: Si costruisce la piattaforma basandosi sull'uso reale
```

### Architettura a plugin e contributi

Epocha e progettato per essere espanso da chiunque: sviluppatori, scienziati, sociologi, storici, teologi, economisti, politologi, persone comuni. Ogni aspetto del sistema e estendibile tramite plugin con un'interfaccia standard e una pipeline di validazione automatica.

#### Chi puo contribuire e cosa

| Contributore | Cosa puo aggiungere | Esempio |
|-------------|-------------------|---------|
| Sviluppatori | Moduli, fix, feature, provider LLM | Nuovo modulo "arte e letteratura" |
| Scienziati/Fisici | Modelli matematici, paper, parametri calibrati | Miglioramento modello meccanica orbitale |
| Sociologi/Antropologi | Pattern sociali, regole comportamentali, dati storici | Modello di formazione delle caste |
| Storici | Template storici, dati di calibrazione, cronologie | Template "Impero Ottomano 1500" calibrato su fonti |
| Economisti | Modelli economici, parametri, validazioni | Modello di iperinflazione basato su casi reali |
| Religiosi/Teologi | Dinamiche religiose, pattern di diffusione credenze | Come le religioni reagiscono a scoperte scientifiche |
| Politologi | Sistemi di governo, modelli di transizione politica | Condizioni che portano a democrazia vs autocrazia |
| Medici/Biologi | Modelli epidemiologici, genetica, medicina spaziale | Modello pandemico calibrato su dati COVID |
| Astrofisici | Modelli orbitali, dati esopianeti, propulsione | Catalogo stellare aggiornato con zone abitabili |
| Persone comuni | Template di mondo, scenari, bug report, feedback, traduzioni | Segnalazione di comportamenti irrealistici |

#### Struttura di un plugin

Ogni modello scientifico o modulo di simulazione e un plugin con un'interfaccia standard:

```
plugin-name/
+-- metadata.json          # nome, autore, versione, dominio, dipendenze
+-- model.py               # implementazione (interfaccia standard Python)
+-- parameters.json        # parametri di default, range validi, unita di misura
+-- calibration_data/      # dati storici per calibrazione e validazione
+-- tests/                 # test automatici (unit + integration)
+-- README.md              # documentazione, equazioni, fonti, istruzioni
+-- references.bib         # bibliografia scientifica
+-- examples/              # esempi di utilizzo e output attesi
```

Il contributore non deve conoscere Django o l'architettura interna di Epocha. Un sociologo puo fornire equazioni, parametri e dati in formato standard, e il sistema li integra automaticamente.

#### Pipeline di validazione automatica

Ogni contributo passa attraverso una pipeline CI/CD prima di essere accettato:

```
Contributo inviato (Pull Request su GitHub)
        |
        v
1. VALIDAZIONE TECNICA (automatica, CI/CD)
   - Test automatici passano?
   - Interfaccia del plugin rispettata?
   - Nessuna regressione nei test esistenti?
   - Linting e formattazione codice?
        |
        v
2. VALIDAZIONE SCIENTIFICA (semi-automatica, LLM reviewer)
   - Le equazioni sono corrette e dimensionalmente coerenti?
   - I paper citati esistono e sono pertinenti? (verifica web)
   - I parametri sono nei range realistici?
   - Il modello produce risultati coerenti con i dati storici di calibrazione?
   - Genera un report di review automatico allegato alla PR
        |
        v
3. VALIDAZIONE DI COERENZA (automatica)
   - Il nuovo plugin contraddice moduli esistenti?
   - Funziona integrato nel sistema end-to-end?
   - Simulazione di test: produce risultati plausibili?
   - Performance: non degrada le performance del sistema?
        |
        v
4. REVIEW UMANA (community + maintainer)
   - Maintainer ed esperti del dominio esaminano il report automatico
   - Discussione pubblica sulla PR
   - Per contributi scientifici: review di almeno un esperto del dominio
   - Approvazione o richiesta modifiche
        |
        v
5. MERGE E PUBBLICAZIONE
   - Il plugin entra nel registro ufficiale
   - Disponibile per tutti gli utenti
   - Changelog aggiornato automaticamente
```

#### Livelli di contributo e validazione

Non tutti i contributi richiedono lo stesso livello di scrutinio:

| Livello | Tipo | Validazione richiesta | Esempio |
|---------|------|----------------------|---------|
| Core | Moduli fondamentali del motore | Review rigorosa + test completi + esperti multipli | Simulation Engine, Agent Module |
| Scientifico | Modelli matematici, equazioni | Validazione scientifica automatica + review esperto dominio | Modello epidemiologico migliorato |
| Template | Mondi iniziali, scenari | Validazione di coerenza + community review | Template "Rivoluzione Francese 1789" |
| Dati | Dataset di calibrazione, parametri | Verifica fonti + validazione automatica range | Dati demografici Europa medievale |
| Community | Bug fix, documentazione, traduzioni | CI/CD standard + review maintainer | Fix, traduzione interfaccia |

---

## Scalabilita multi-scala: dall'individuo alla galassia

Epocha deve gestire ogni scala di complessita con la stessa architettura. Il sistema scala dall'individuo singolo alla colonizzazione interstellare, e ogni scala si sovrappone alle precedenti — un abitante di una colonia su Marte ha ancora una famiglia, un lavoro, delle ambizioni personali.

### Le scale della simulazione

```
Individuo → Famiglia → Comunita → Villaggio → Citta → Regione →
→ Nazione → Civilta → Civilta orbitale → Federazione interplanetaria →
→ Civilta interstellare → Federazione galattica
```

### Zoom semantico

Come lo zoom della mappa ma applicato alla complessita sociale. L'utente puo navigare tra le scale in tempo reale:

| Zoom | Cosa si vede | Unita di base | Dinamiche visibili |
|------|-------------|---------------|-------------------|
| Massimo | Singolo individuo | Persona | Emozioni, decisioni, conversazioni |
| Alto | Quartiere/comunita | Famiglie, gruppi | Relazioni, conflitti locali, commercio locale |
| Medio | Citta/regione | Quartieri, istituzioni | Economia locale, politica cittadina, criminalita |
| Basso | Nazione/civilta | Citta, regioni | Geopolitica, guerre, economia nazionale |
| Minimo (terrestre) | Pianeta | Nazioni, civilta | Equilibri globali, clima, commercio internazionale |
| Orbitale | Sistema solare | Pianeti, colonie | Rotte spaziali, economia interplanetaria |
| Interstellare | Sistemi stellari | Sistemi colonizzati | Civilta isolate, viaggi generazionali |

### Aggregazione dinamica multi-livello

L'aggregazione individuo/gruppo si estende a tutte le scale:

```
Galassia (agente collettivo)
+-- Sistema stellare (agente collettivo)
|   +-- Pianeta (agente collettivo)
|   |   +-- Nazione (agente collettivo)
|   |   |   +-- Citta (agente collettivo)
|   |   |   |   +-- Quartiere (agente collettivo)
|   |   |   |   |   +-- Gruppo sociale (agente collettivo)
|   |   |   |   |   |   +-- * Leader emergente (individuo tracciato)
|   |   |   |   |   |   +-- membro generico
|   |   |   |   |   +-- Individuo libero
|   |   |   |   +-- * Sindaco (individuo emergente)
|   |   |   +-- * Capo di stato (individuo emergente)
|   |   +-- * Scienziato rivoluzionario (individuo emergente)
|   +-- Colonia spaziale (agente collettivo)
+-- Sistema stellare remoto
    +-- Civilta aliena (agente collettivo con regole diverse)
```

A ogni livello:
- Il sistema decide **dinamicamente** chi merita di essere tracciato individualmente
- Un individuo puo emergere a qualsiasi scala e alterare la storia (il "Mulo")
- I gruppi possono frammentarsi, fondersi, gerarchizzarsi
- La transizione tra scale avviene fluidamente quando la simulazione lo richiede

### Modelli scientifici multi-scala

Ogni scala usa modelli matematici appropriati, connessi tra loro:

| Scala | Modelli | Input da scala inferiore | Output verso scala superiore |
|-------|---------|------------------------|----------------------------|
| Individuo | Psicologia, decision-making | — | Comportamento aggregato |
| Comunita | Dinamiche di gruppo, Granovetter | Decisioni individuali | Consenso, conflitti locali |
| Citta | Economia urbana, Zipf | Attivita delle comunita | Produzione, migrazione |
| Nazione | Macroeconomia, demografia | PIL citta, flussi migratori | Politica estera, commercio |
| Civilta | Geopolitica, modelli di Toynbee | Potenza nazioni | Guerre, alleanze, espansione |
| Sistema solare | Meccanica orbitale, economia spaziale | Risorse e tecnologia civilta | Rotte, costi trasporto |
| Interstellare | Equazione di Drake, modelli di colonizzazione | Capacita tecnologica | Contatto alieno, espansione |

I modelli si influenzano bidirezionalmente: una crisi economica nazionale (scala nazione) impatta le famiglie (scala individuo), e una rivolta locale (scala comunita) puo rovesciare un governo (scala nazione).

### Transizioni di scala

Il sistema riconosce automaticamente quando la civilta e pronta a una transizione di scala:

- **Terra → Orbita**: quando il livello tecnologico raggiunge la propulsione orbitale e c'e motivazione (competizione, risorse, curiosita)
- **Orbita → Sistema solare**: quando le infrastrutture orbitali sono mature e la colonizzazione e economicamente viable
- **Sistema solare → Interstellare**: quando la propulsione e la longevita (o le navi generazionali) lo permettono

Ogni transizione non e automatica: dipende dalle decisioni degli agenti, dalle risorse, dalla volonta politica, dai conflitti in corso. Una civilta potrebbe non raggiungere mai lo spazio se collassa prima.

---

## Lingua, comunicazione e deriva linguistica

Le lingue sono un elemento fondamentale della civilta e influenzano profondamente le dinamiche sociali. In una simulazione su scala di secoli, le lingue evolvono, si frammentano e si fondono.

### Meccaniche linguistiche

**Evoluzione linguistica:**
- Ogni civilta parte con una o piu lingue
- Le lingue evolvono nel tempo: nuove parole emergono, la pronuncia cambia, la grammatica si semplifica o complica
- Il tasso di cambiamento dipende da: isolamento geografico, contatti commerciali, conquiste, migrazioni
- Dopo secoli di separazione, due comunita che parlavano la stessa lingua non si capiscono piu (come latino → italiano, francese, spagnolo, rumeno)

**Barriere linguistiche:**
- Agenti che parlano lingue diverse hanno difficolta a interagire
- Il commercio e la diplomazia richiedono interpreti o una lingua franca
- Le barriere linguistiche generano incomprensioni, pregiudizi, conflitti
- L'imposizione di una lingua (colonizzazione linguistica) e un atto politico con conseguenze culturali profonde

**Lingue e identita:**
- La lingua e parte dell'identita di un gruppo
- Movimenti di indipendenza spesso includono la rivendicazione linguistica
- La perdita di una lingua equivale alla perdita di una cultura

**Scala interstellare:**
- Colonie isolate per secoli o millenni sviluppano lingue incomprensibili tra loro
- Il primo contatto con una civilta aliena pone il problema della comunicazione interspecifica
- Le comunicazioni ritardate (velocita della luce) accelerano la divergenza linguistica

### Implementazione

La lingua non e simulata a livello di grammatica reale ma come **attributo culturale con regole di evoluzione**:
- Ogni agente/gruppo ha un "vettore linguistico" che rappresenta la sua lingua
- La distanza tra vettori determina la comprensibilita reciproca
- Il vettore evolve nel tempo influenzato da contatti, isolamento, eventi culturali
- Un LLM puo generare "sapore linguistico" nelle conversazioni (arcaismi, neologismi, accenti)

---

## Civilta multiple e primo contatto

La simulazione puo contenere **piu civilta indipendenti** che nascono, si sviluppano e a un certo punto si scoprono a vicenda.

### Civilta parallele

- L'utente puo configurare piu civilta con punti di partenza diversi (es. continenti separati)
- Ogni civilta evolve indipendentemente: tecnologia, cultura, religione, lingua, politica
- Le civilta possono svilupparsi a velocita diverse (una puo essere nell'eta del bronzo mentre l'altra ha la polvere da sparo)

### Primo contatto tra civilta

Il momento in cui due civilta si scoprono e uno degli eventi piu drammatici della storia. Il sistema simula:

**Modalita di contatto:**
- Esplorazione marittima/terrestre (graduale)
- Scoperta improvvisa (una spedizione trova una civilta sconosciuta)
- Contatto commerciale indiretto (prodotti che arrivano prima delle persone)
- Contatto violento (invasione, conquista)

**Conseguenze del contatto:**
- Shock culturale e religioso (la mia visione del mondo e sbagliata?)
- Scambio colombiano: malattie, piante, animali, tecnologie
- Squilibrio tecnologico: la civilta piu avanzata ha un vantaggio enorme
- Assimilazione, conquista, o coesistenza — dipende dalle personalita degli agenti leader
- Fusione o scontro di sistemi economici, politici, religiosi

**Contatto con civilta aliene:**
- Stesse dinamiche ma amplificate all'estremo
- Biologia incompatibile: nessuno scambio di malattie, ma anche nessuna comprensione intuitiva
- Comunicazione: nessun riferimento culturale condiviso
- Reazioni: dalla venerazione al terrore, dall'opportunismo alla paranoia — dipende dalla personalita degli agenti

---

## Decadimento, entropia e manutenzione

Le civilta non crescono solo verso l'alto. Le cose si rompono, le competenze si perdono, le infrastrutture decadono. Senza questo meccanismo, le simulazioni producono civilta irrealisticamente stabili.

### Meccaniche di decadimento

**Infrastrutture:**
- Strade, ponti, acquedotti, edifici richiedono manutenzione continua
- Senza manutenzione, degradano nel tempo (modello esponenziale di decadimento)
- Il costo di manutenzione cresce con la complessita dell'infrastruttura
- Una civilta che si espande troppo velocemente puo non riuscire a mantenere le proprie infrastrutture (sovra-estensione imperiale)

**Conoscenza e competenze:**
- Le tecnologie richiedono persone che le comprendano e le mantengano
- Se una generazione non trasmette una competenza, questa si perde
- Esempio storico: Roma aveva calcestruzzo avanzato, il Medioevo no — la conoscenza era andata perduta
- Le tecnologie complesse sono piu fragili: piu facile perdere la capacita di costruire un microprocessore che un aratro

**Istituzioni:**
- Le istituzioni (governo, giustizia, istruzione) richiedono persone competenti e legittimita
- La corruzione, la burocrazia eccessiva, la perdita di fiducia pubblica degradano le istituzioni
- Un'istituzione degradata funziona male, generando crisi che accelerano il degrado (ciclo vizioso)

**Risorse:**
- Le risorse naturali si esauriscono (modello di Hubbert)
- Il suolo si impoverisce senza rotazione delle colture
- L'acqua puo inquinarsi o esaurirsi
- I rifiuti si accumulano

### Dark Age e rinascite

Il decadimento puo portare a periodi bui (Dark Age) seguiti da rinascite:
- Collasso di una civilta complessa → semplificazione forzata → lenta ricostruzione
- Le conoscenze perdute devono essere riscoperte (non "ricordate")
- Ma alcune conoscenze possono sopravvivere in monasteri, biblioteche, tradizioni orali
- Le rinascite spesso combinano conoscenze riscoperte con innovazioni nuove

---

## Arte, filosofia e produzione culturale

Le civilta non producono solo economia e politica. L'arte, la filosofia, la letteratura e la musica plasmano l'identita collettiva e influenzano il corso della storia.

### Meccaniche culturali

**Produzione artistica e filosofica:**
- Gli agenti con tratti "creativi" o "intellettuali" possono produrre opere
- Le opere riflettono il contesto sociale: un periodo di guerra produce arte diversa da un periodo di pace
- I movimenti culturali emergono naturalmente dall'aggregazione di agenti con idee simili
- Un'opera puo influenzare altri agenti, diffondendosi come un'idea nel sistema di Information Flow

**Movimenti filosofici e il loro impatto:**
- I movimenti filosofici cambiano il modo in cui gli agenti pensano e decidono
- Esempio: Illuminismo → razionalismo → messa in discussione dell'autorita → Rivoluzione Francese
- Esempio: una filosofia pacifista puo ridurre la probabilita di guerra
- Esempio: una filosofia espansionista puo accelerare la colonizzazione

**Religione come produzione culturale:**
- Le religioni nascono, si diffondono, si scindono, evolvono
- Sono influenzate da e influenzano: politica, scienza, arte, economia
- Le tensioni religiose sono tra le cause piu potenti di conflitto e cambiamento sociale
- Le scoperte scientifiche possono rafforzare o indebolire i sistemi di credenze

**Cultura e identita:**
- La produzione culturale definisce l'identita di un gruppo/nazione/civilta
- La cultura si diffonde attraverso il commercio, la conquista, la migrazione
- L'imposizione culturale (imperialismo culturale) e una forma di potere
- La resistenza culturale e una forma di opposizione

### Implementazione

La cultura non e simulata come "opere d'arte concrete" ma come **correnti culturali con attributi e influenza**:
- Ogni corrente ha: tema, valori, impatto sulle decisioni degli agenti, raggio di diffusione
- Le correnti competono per influenza nella societa
- Il LLM genera descrizioni narrative delle correnti culturali quando l'utente esplora la storia della civilta

---

## Educazione e trasmissione della conoscenza

Il sapere non si trasmette automaticamente tra generazioni. Servono istituzioni, persone e strumenti dedicati. Senza un sistema educativo, una civilta perde le proprie competenze in una generazione.

### Sistemi educativi

Evolvono con la civilta:

| Fase civilta | Sistema educativo | Effetto |
|-------------|-------------------|---------|
| Tribale | Tradizione orale, apprendistato diretto | Conoscenza fragile, legata a individui specifici |
| Agricola | Apprendistato formalizzato, sacerdoti come custodi del sapere | Conoscenza concentrata in elite religiose |
| Urbana | Scuole, accademie, biblioteche | Diffusione piu ampia, alfabetizzazione crescente |
| Industriale | Istruzione pubblica obbligatoria, universita | Alfabetizzazione di massa, specializzazione |
| Post-industriale | Universita di ricerca, formazione continua, accesso digitale | Innovazione accelerata, knowledge economy |
| Spaziale | Formazione a distanza interplanetaria, AI tutoring | Divergenza curricula tra colonie |

### Meccaniche

- **Tasso di alfabetizzazione**: influenza la capacita della societa di innovare, governarsi, comunicare
- **Biblioteche e archivi**: depositi di conoscenza che sopravvivono agli individui (ma possono essere distrutti — Biblioteca di Alessandria)
- **Censura**: governi e istituzioni religiose possono bloccare la diffusione di conoscenze (rallenta innovazione, genera tensioni)
- **Fuga di cervelli**: gli individui piu istruiti migrano dove le condizioni sono migliori (depaupera la societa di origine)
- **Ricerca**: universita e accademie accelerano le scoperte nel Knowledge Engine (piu ricercatori = piu probabilita di innovazione)

---

## Criminalita e giustizia

La criminalita e un fenomeno sociale emergente che riflette lo stato della societa. I sistemi di giustizia sono la risposta istituzionale.

### Dinamiche criminali

- La criminalita aumenta con: disuguaglianza, disoccupazione, debolezza delle istituzioni, carestia, guerre
- La criminalita diminuisce con: benessere diffuso, istituzioni forti, coesione sociale, occupazione
- La criminalita organizzata emerge quando lo stato e debole o corrotto (mafie, cartelli, bande)
- La corruzione e un tipo specifico di criminalita che erode le istituzioni dall'interno — tra le cause principali del collasso delle civilta

### Sistemi di giustizia

Evolvono con la civilta:

| Fase | Sistema | Caratteristiche |
|------|---------|----------------|
| Tribale | Giustizia del clan, vendetta, mediazione anziani | Soggettiva, basata su rapporti personali |
| Monarchica | Legge del re, giudici nominati | Centralizzata, spesso arbitraria |
| Repubblicana | Codici di legge scritti, tribunali | Piu prevedibile, ma accesso diseguale |
| Moderna | Stato di diritto, diritti individuali, appello | Garantista, lenta, costosa |
| Autoritaria | Legge come strumento di potere | Efficiente ma oppressiva |

### Effetti sulla simulazione

- Un sistema giudiziario forte stabilizza la societa ma costa risorse
- Un sistema corrotto genera sfiducia, resistenza, rivoluzioni
- L'assenza di giustizia genera anarchia o giustizia privata (vendette, milizie)
- Le leggi influenzano il comportamento degli agenti (deterrenza, incentivi)

---

## Disastri naturali

Eventi catastrofici che testano la resilienza della civilta. Non sono scriptati ma emergono dai modelli geologici e climatici del World Module.

### Tipi di disastri

| Tipo | Causa (modello scientifico) | Scala di impatto | Frequenza |
|------|----------------------------|-----------------|-----------|
| Terremoto | Tettonica a placche, faglie | Locale/regionale | Ricorrente |
| Eruzione vulcanica | Vulcanismo, hotspot, subduzione | Locale → globale (inverno vulcanico) | Rara/ricorrente |
| Tsunami | Terremoto sottomarino, frana | Costiero | Rara |
| Inondazione | Piogge estreme, scioglimento ghiacci | Regionale | Ricorrente |
| Siccita/Carestia | Variazioni climatiche, El Nino | Regionale/continentale | Ciclica |
| Pandemia | Modello SIR/SEIR, zoonosi | Globale | Irregolare |
| Impatto asteroidale | Meccanica orbitale, NEO | Regionale → estinzione di massa | Molto rara |
| Tempesta solare | Attivita stellare | Globale (tecnologia) | Rara |

### Meccaniche

- I disastri non sono casuali: emergono dai modelli geologici e climatici (PostGIS per la localizzazione, modelli scientifici per la probabilita)
- L'impatto dipende dalla preparazione della civilta: una societa con infrastrutture solide resiste meglio
- I disastri possono accelerare cambiamenti sociali: migrazioni, cambi di governo, innovazione forzata, movimenti religiosi ("punizione divina")
- La ricostruzione post-disastro puo rafforzare o indebolire la civilta
- Su scala interstellare: tempeste solari, radiazioni cosmiche, instabilita stellare minacciano le colonie

### Cascate di conseguenze

Un disastro raramente e un evento isolato:
```
Eruzione vulcanica → inverno vulcanico → carestia → migrazione →
→ conflitti con popolazioni vicine → instabilita politica →
→ cambio di governo → nuova politica agricola
```

---

## Strutture familiari e sistemi di parentela

La famiglia e l'unita sociale fondamentale. La sua struttura influenza economia, politica, alleanze e cultura.

### Tipi di struttura familiare

| Tipo | Descrizione | Effetto sulla societa |
|------|------------|----------------------|
| Nucleare | Coppia + figli | Mobilita sociale alta, legami comunitari deboli |
| Estesa | Piu generazioni sotto lo stesso tetto | Solidarieta forte, mobilita bassa, conservatorismo |
| Clan/Tribu | Famiglie imparentate con identita comune | Lealta di gruppo, faide, endogamia |
| Poligama | Un individuo con piu partner | Concentrazione risorse, tensioni interne, crescita demografica |
| Comunitaria | Famiglie non imparentate che condividono risorse | Egualitarismo, fragilita istituzionale |

### Regole matrimoniali

- **Endogamia** (matrimonio dentro il gruppo): rafforza l'identita di gruppo ma riduce diversita genetica e culturale
- **Esogamia** (matrimonio fuori dal gruppo): crea alleanze tra gruppi, diffonde geni e cultura
- **Matrimonio combinato**: strumento politico ed economico (alleanze tra famiglie potenti)
- **Matrimonio libero**: maggiore autonomia individuale, legami familiari piu deboli

### Sistemi di eredita

| Sistema | Effetto economico | Effetto politico |
|---------|------------------|-----------------|
| Primogenitura | Concentrazione ricchezza, famiglie potenti | Dinastie stabili, disuguaglianza |
| Divisione equa | Frammentazione terre, mobilita sociale | Instabilita, competizione |
| Matrilineare | Potere femminile, strutture diverse | Organizzazione sociale alternativa |
| Meritocratico | Incentivo al merito, meno disuguaglianza ereditaria | Mobilita sociale, meno stabilita dinastica |

### Effetti sulla simulazione

- La struttura familiare determina come si trasmettono ricchezza, potere, cultura e valori tra generazioni
- Le alleanze matrimoniali sono uno strumento politico fondamentale (Asburgo, regni medievali)
- I conflitti familiari (successioni, eredita, faide) possono destabilizzare intere nazioni
- La struttura familiare evolve con la societa (industrializzazione → nuclearizzazione della famiglia)

---

## Evoluzione dei sistemi finanziari

Il denaro e i sistemi finanziari sono tra le invenzioni piu trasformative della civilta. La loro evoluzione cambia radicalmente l'economia e la societa.

### Fasi evolutive

```
Baratto → Moneta-merce (bestiame, sale, conchiglie) →
→ Moneta metallica (bronzo, argento, oro) →
→ Moneta cartacea (note di banco, lettere di credito) →
→ Sistema bancario (depositi, prestiti, interessi) →
→ Borse e mercati finanziari (azioni, obbligazioni) →
→ Moneta fiduciaria (sganciata dall'oro) →
→ Moneta digitale / criptovalute →
→ [futuri sistemi finanziari emergenti dalla simulazione]
```

Ogni transizione non e automatica: emerge quando le condizioni economiche la richiedono e la tecnologia lo permette.

### Meccaniche finanziarie

**Moneta:**
- La moneta emerge quando il baratto diventa inefficiente (societa complesse con specializzazione)
- Il tipo di moneta influenza l'economia: monete metalliche sono deflazionarie, carta moneta permette inflazione
- La falsificazione e la svalutazione sono rischi costanti

**Banche e credito:**
- Le banche emergono quando il commercio richiede trasferimenti a distanza e prestiti
- Il credito accelera l'economia ma crea rischio sistemico (bolle, crolli)
- I tassi di interesse influenzano investimenti, risparmi, crescita

**Crisi finanziarie:**
- Bolle speculative: emergono da euforia collettiva (tulipani, immobili, azioni)
- Crolli bancari: quando i debiti superano la capacita di rimborso
- Iperinflazione: quando il governo stampa moneta senza copertura
- Ogni crisi finanziaria ha conseguenze sociali profonde: disoccupazione, proteste, cambi di governo

**Tassazione:**
- I sistemi fiscali emergono con lo stato organizzato
- Le tasse troppo alte generano evasione e rivolta
- Le tasse troppo basse impediscono servizi pubblici e difesa
- La progressivita fiscale influenza la distribuzione della ricchezza

### Su scala interstellare

- Il commercio tra pianeti richiede nuovi sistemi finanziari (come gestisci il credito con ritardi di comunicazione di anni?)
- Ogni colonia potrebbe sviluppare la propria moneta
- L'economia interstellare potrebbe basarsi su risorse fisiche (minerali rari) piu che su moneta fiduciaria

---

## Meccaniche ispirate alla saga di Asimov

Concetti dalla saga della Fondazione e dal ciclo dei Robot che arricchiscono la simulazione con meccaniche uniche e scientificamente interessanti.

### Crisi Seldon — Rilevamento automatico dei punti di svolta

Nel Piano Seldon, le "Crisi Seldon" sono momenti in cui la civilta e a un bivio: l'azione o l'inazione di pochi individui determina il futuro per secoli. Epocha rileva automaticamente queste crisi.

**Come funziona:**
- Il sistema monitora continuamente gli indicatori di stabilita (economici, politici, sociali, militari)
- Quando piu indicatori convergono verso valori critici contemporaneamente, il sistema identifica una "Crisi Seldon"
- L'utente riceve un alert: "Crisi rilevata: la civilta e a un punto di svolta"
- La dashboard mostra: cause della crisi, possibili esiti, agenti chiave coinvolti, probabilita di ciascun esito

**Tipi di crisi rilevabili:**
- Crisi di successione (vuoto di potere)
- Crisi economica sistemica (debito insostenibile, bolla speculativa)
- Crisi di legittimita (le istituzioni perdono fiducia)
- Crisi di risorse (esaurimento, scarsita critica)
- Crisi culturale/religiosa (vecchi valori crollano, nuovi non ancora affermati)
- Crisi tecnologica (innovazione che destabilizza l'ordine esistente)
- Crisi di contatto (scoperta di un'altra civilta)

**Uso sperimentale:**
L'utente puo forkare la simulazione al momento della crisi e testare diversi interventi:
- Branch A: nessun intervento (gruppo di controllo)
- Branch B: iniezione di un leader
- Branch C: iniezione di un evento economico
- Confronto: quale intervento ha prodotto l'esito migliore?

### La Seconda Fondazione — Manipolazione invisibile

Ispirata alla Seconda Fondazione di Asimov, questa modalita permette all'utente di influenzare la civilta in modo **sottile e indiretto**, senza che gli agenti percepiscano un intervento divino.

**Strumenti di manipolazione invisibile:**
- **Sussurri**: far arrivare un'informazione specifica a un agente specifico (sembra un passaparola naturale)
- **Incontri**: favorire l'incontro tra due agenti che normalmente non si incontrerebbero
- **Nudge economici**: piccole modifiche alle condizioni economiche locali (un raccolto leggermente migliore, un carico di merci che arriva in ritardo)
- **Ispirazione**: aumentare temporaneamente la creativita o l'ambizione di un agente specifico
- **Semina di idee**: introdurre un'idea nel flusso informativo come se fosse emersa naturalmente

**Differenza dalla modalita Dio:**
- Dio: comandi diretti, gli agenti sanno che c'e un'entita superiore
- Seconda Fondazione: manipolazione invisibile, gli agenti credono che tutto sia naturale
- Il risultato e diverso: gli agenti reagiscono diversamente a un ordine divino rispetto a un'idea che credono propria

### Leggi della Robotica — AI nella simulazione

Se la civilta simulata sviluppa intelligenza artificiale (come parte dell'evoluzione tecnologica), questa AI interna alla simulazione diventa un nuovo tipo di agente con regole proprie.

**Meccaniche:**
- Quando il livello tecnologico raggiunge l'AI, il sistema introduce agenti-AI nella civilta
- Questi agenti seguono regole (ispirate alle Tre Leggi ma non necessariamente identiche)
- L'utente puo configurare le regole dell'AI simulata
- Gli agenti umani reagiscono all'AI secondo la loro personalita: adozione entusiasta, paura, rifiuto, sfruttamento

**Esperimenti possibili:**
- Cosa succede se l'AI ha restrizioni etiche rigide vs nessuna restrizione?
- Cosa succede se l'AI diventa piu intelligente degli agenti umani?
- Come cambia l'economia quando l'AI sostituisce il lavoro umano?
- Come reagiscono le religioni all'esistenza di un'intelligenza non biologica?
- Un agente puo creare un'AI con regole diverse da quelle ufficiali? (il problema del "robot ribelle")

### Gaia — Coscienza collettiva

Ispirata al pianeta Gaia di Asimov, la possibilita che una civilta evolva verso una forma di **coscienza collettiva** — non piu individui separati ma una mente di gruppo.

**Come puo emergere:**
- Tecnologia neurale avanzata (brain-computer interface → brain-brain interface)
- Evoluzione biologica su scala di millenni
- AI che funge da connettore tra le menti
- Pratica spirituale/filosofica portata all'estremo

**Effetti sulla simulazione:**
- Gli agenti in una coscienza collettiva non prendono decisioni individuali ma collettive
- Scompaiono conflitti interni ma anche creativita individuale e dissenso
- La civilta diventa estremamente stabile ma potenzialmente stagnante
- Il contatto con civilta "individuali" crea tensioni profonde (liberta vs armonia)
- Non e necessariamente un punto di arrivo: una coscienza collettiva puo frammentarsi

**Scelta emergente, non forzata:**
La coscienza collettiva non viene imposta dal sistema ma puo emergere naturalmente se le condizioni tecnologiche e culturali lo permettono. L'utente puo anche iniettarla come variabile sperimentale.

### Enciclopedia Galattica — Registro storico narrativo

Ispirata all'Enciclopedia Galattica di Asimov, il registro storico della simulazione diventa un'**enciclopedia consultabile in linguaggio naturale**.

**Come funziona:**
- Il registro storico (gia previsto nel design) contiene tutti gli eventi, le scoperte, le crisi, i cambiamenti
- L'utente puo interrogare l'enciclopedia in linguaggio naturale:
  - "Cosa e successo nell'anno 347?"
  - "Chi era il leader piu influente del terzo secolo?"
  - "Perche e crollata la dinastia X?"
  - "Qual e stata la causa della guerra tra Nord e Sud?"
  - "Riassumi la storia della civilta dal secolo 5 al secolo 8"
- Il LLM genera risposte narrative, scritte come voci enciclopediche, basate sui dati reali della simulazione
- Le voci includono riferimenti incrociati: "Vedi anche: Crisi del Ferro (anno 234), Riforma di Kael (anno 251)"

**Stile narrativo:**
Le risposte sono scritte nello stile dell'Enciclopedia Galattica di Asimov — distaccate, accademiche, con la prospettiva di uno storico che guarda indietro. Questo trasforma i dati della simulazione in una **storia leggibile e coinvolgente**.

**Export:**
L'enciclopedia puo essere esportata come documento (PDF, Markdown) — la storia completa della civilta simulata, scritta come un libro di storia.

---

## Meccaniche ispirate alla fantascienza e alla futurologia

Concetti da universi di fantascienza e dalla futurologia reale che arricchiscono la simulazione con dinamiche avanzate. Queste meccaniche non sono attive dall'inizio: emergono quando la civilta raggiunge il livello tecnologico e sociale appropriato.

### Ispirazione Star Trek

#### Prima Direttiva — Etica dell'interferenza

Quando una civilta avanzata scopre una meno avanzata, quale politica adotta?

| Politica | Descrizione | Conseguenze |
|----------|------------|-------------|
| Non interferenza (Prime Directive) | Osservare senza intervenire | La civilta meno avanzata evolve naturalmente, ma potrebbe soffrire inutilmente |
| Assistenza guidata | Aiutare con cautela, senza rivelare tecnologie avanzate | Accelerazione controllata, rischio di dipendenza |
| Integrazione | Invitare nella propria federazione/alleanza | Scambio culturale, ma shock tecnologico e perdita di identita |
| Sfruttamento | Usare la civilta meno avanzata come risorsa | Colonialismo, resistenza, conflitto |
| Conquista | Sottomettere e assimilare | Dominio, ma instabilita e ribellioni |

L'utente puo configurare la politica di contatto come variabile sperimentale e osservare le conseguenze a lungo termine.

#### Economia post-scarsita

Cosa succede quando la tecnologia elimina la scarsita (replicatori, energia illimitata, automazione totale)?

- L'economia monetaria tradizionale perde significato
- Le motivazioni degli agenti cambiano: non piu sopravvivenza ma realizzazione, status, conoscenza, potere
- Emergono nuove forme di disuguaglianza: accesso all'informazione, influenza sociale, creativita
- Possibili esiti: utopia egualitaria, stagnazione, nuove gerarchie basate su merito o prestigio
- La transizione verso la post-scarsita e il periodo piu pericoloso (chi controlla la tecnologia durante la transizione?)

#### Federazione vs Impero galattico

Due modelli di aggregazione multi-planetaria che competono:

| Aspetto | Federazione | Impero |
|---------|-------------|--------|
| Governance | Democratica, consensuale | Centralizzata, autoritaria |
| Diversita | Valorizzata, protetta | Soppressa o tollerata |
| Stabilita | Alta in pace, fragile sotto stress | Alta in potenza, fragile in transizione |
| Innovazione | Diffusa, collaborativa | Concentrata, controllata |
| Espansione | Volontaria, diplomatica | Militare, coercitiva |
| Debolezza | Lenta nelle decisioni, vulnerabile a dissenso | Dipendente dal leader, vulnerabile a ribellioni |

Il sistema non forza nessuno dei due: l'organizzazione emerge dalle decisioni degli agenti e dalle condizioni.

### Ispirazione Star Wars

#### Megacorporazioni come entita politiche

Quando le corporazioni diventano cosi potenti da rivaleggiare con i governi:

- Eserciti privati e forze di sicurezza corporate
- Controllo di pianeti o regioni intere
- Lobby e corruzione che svuotano le istituzioni democratiche
- "Corporate states": territori governati da aziende, non da politici
- Conflitto tra interessi corporate e bene pubblico
- Possibile evoluzione: le corporazioni sostituiscono completamente gli stati

#### Economia sommersa e pirateria

L'economia informale che esiste parallela a quella ufficiale:

- **Mercato nero**: commercio di beni proibiti o tassati (emerge dove la regolamentazione e eccessiva)
- **Contrabbando**: trasporto illegale tra zone con regole diverse (specialmente tra pianeti/colonie)
- **Pirateria**: predazione sulle rotte commerciali (marittime o spaziali)
- **Corruzione**: l'economia sommersa si intreccia con le istituzioni
- Prospera dove lo stato e debole, le disuguaglianze sono alte, i confini sono porosi
- Puo essere un motore economico significativo (storicamente: pirati dei Caraibi, Via della Seta informale)

#### Civilta antiche e rovine

Resti di civilta collassate millenni prima:

- **Scoperta di rovine**: durante l'esplorazione, gli agenti possono trovare resti di civilta precedenti
- **Tecnologie perdute**: artefatti con tecnologia superiore a quella attuale — possono accelerare l'innovazione
- **Conoscenze sepolte**: testi, database, archivi di civilta scomparse
- **Impatto culturale**: la scoperta che "non siamo i primi" cambia la prospettiva filosofica e religiosa
- **Rischi**: tecnologie trovate senza comprenderne i pericoli (armi, AI incontrollate)
- Le rovine raccontano anche come quella civilta e collassata — un monito per quella attuale

### Ispirazione Blade Runner / Dystopie

#### Bioingegneria e transumanesimo

Quando la biologia diventa tecnologia:

- **Modifiche genetiche**: selezione embrionale, potenziamento cognitivo/fisico, eliminazione malattie
- **Cybernetics**: impianti neurali, arti artificiali superiori ai biologici, sensi potenziati
- **Estensione della vita**: terapie anti-invecchiamento, rigenerazione, longevita estrema
- **Esseri bioingegnerizzati**: creazione di nuovi tipi di umani per ambienti specifici (spazio, oceani, pianeti ostili)

**Conseguenze sociali:**
- Chi puo permettersi le modifiche? Nuove caste: "migliorati" vs "naturali"
- Cosa definisce l'"umano"? Diritti dei modificati, dei cloni, delle chimere
- Discriminazione basata sulla genetica o sugli impianti
- Evoluzione del concetto di identita personale
- Movimenti "pro-natura" che rifiutano le modifiche vs "transumanisti" che le abbracciano

#### Sorveglianza e controllo sociale

Tecnologia come strumento di controllo della popolazione:

- **Sorveglianza totale**: ogni comunicazione, movimento, transazione monitorata
- **Punteggio sociale**: cittadini valutati e classificati in base al comportamento
- **Propaganda algoritmica**: manipolazione dell'informazione personalizzata per ogni agente
- **Predizione del crimine**: arresti preventivi basati su probabilita (minority report)

**Reazioni degli agenti (dipendono dalla personalita):**
- Accettazione passiva ("non ho nulla da nascondere")
- Resistenza attiva (movimenti per la privacy, hacking, ribellione)
- Fuga (migrazione verso zone non sorvegliate, colonie spaziali come "terra di liberta")
- Adattamento (comportamento pubblico conforme, vita privata segreta)

#### Collasso ambientale sistemico

Non singoli disastri ma degradazione ambientale progressiva e irreversibile:

- Inquinamento che si accumula generazione dopo generazione
- Cambiamento climatico con feedback positivi (scioglimento ghiacci → meno albedo → piu calore)
- Perdita di biodiversita che indebolisce gli ecosistemi
- Esaurimento del suolo fertile, desertificazione
- Acidificazione degli oceani, collasso delle catene alimentari marine
- Il punto di non ritorno: quando il danno diventa irreversibile

**Effetto sulla civilta:**
- Pressione alla colonizzazione spaziale (la Terra diventa inabitabile)
- Conflitti per le ultime risorse abitabili
- Migrazioni di massa
- Movimenti ecologisti radicali vs negazione del problema
- Possibile collasso civilizzazionale se non si trova una soluzione

### Ispirazione Dune

#### Monopolio di una risorsa critica

Una singola risorsa che controlla tutto:

- Il sistema identifica quando una risorsa diventa critica per la civilta (es. un minerale per la tecnologia avanzata, un combustibile per i viaggi spaziali)
- Chi controlla la risorsa controlla la civilta: guerre, alleanze, diplomazia ruotano attorno ad essa
- La scarsita genera: innovazione (cercare alternative), conflitto (conquistare le fonti), diplomazia (accordi di fornitura)
- Cosa succede quando la risorsa si esaurisce o viene sostituita? Le potenze che la controllavano crollano, nuove potenze emergono
- Parallelo storico: petrolio nel XX-XXI secolo

#### Adattamento ambientale e culture forgiate dall'ambiente

L'ambiente non e solo sfondo ma motore della cultura:

| Ambiente | Cultura emergente | Tratti |
|----------|-------------------|--------|
| Deserto/aridita | Resiliente, austera, spirituale | Forte coesione, risorse condivise, guerriera |
| Abbondanza tropicale | Sofisticata, artistica, commerciale | Gerarchica, ricca, potenzialmente fragile |
| Ambiente artico/ostile | Pragmatica, cooperativa, minimalista | Egualitaria, adattabile, isolata |
| Oceano/isole | Navigatrice, commerciante, espansionista | Cosmopolita, innovativa, dispersa |
| Montagne | Indipendente, conservatrice, resistente | Frammentata, difficile da conquistare |
| Spazio (gravita zero) | Radicalmente nuova, post-terrestre | Fisicamente diversa, identita nuova |
| Pianeta ostile | Ingegneristica, cooperativa per sopravvivenza | Disciplinata, tecnologica, comunitaria |

Le culture non sono assegnate ma emergono dall'interazione tra agenti e ambiente su scala di generazioni.

### Ispirazione The Expanse

#### Divergenza biologica umana

Umani che vivono per generazioni in condizioni fisiche diverse si trasformano:

- **Gravita diversa**: ossa piu sottili, statura diversa, cuore adattato (un "marziano" non puo tornare sulla Terra)
- **Radiazioni**: adattamenti alla radiazione cosmica (pigmentazione, riparazione DNA)
- **Atmosfera**: capacita polmonare adattata a composizioni atmosferiche diverse
- **Alimentazione**: metabolismo adattato a diete diverse

**Conseguenze sociali:**
- Nuove "razze" umane basate non su etnia ma su pianeta di nascita
- Discriminazione e razzismo interplanetario
- Impossibilita fisica di tornare al pianeta d'origine (prigionieri della propria evoluzione)
- Identita "terrestre" vs "marziana" vs "spaziale" come nuova fonte di conflitto
- A lungo termine: speciazione — umani di pianeti diversi non possono piu riprodursi tra loro

#### Core vs Periferia

Il colonialismo si ripete su scala spaziale:

- **Pianeti centrali** (Terra, prime colonie): ricchi, potenti, controllano la tecnologia e il commercio
- **Colonie periferiche**: sfruttate per risorse, forza lavoro a basso costo, poca autonomia
- **Tensione crescente**: le colonie producono ricchezza ma non ne beneficiano
- **Ribellione**: le colonie chiedono autonomia o indipendenza (parallelo: Rivoluzione Americana, decolonizzazione)
- **Distanza come fattore**: piu una colonia e lontana, piu e autonoma de facto (i messaggi impiegano anni)

### Ispirazione Cyberpunk

#### Mondi virtuali paralleli

La civilta sviluppa un metaverso dove parte della popolazione vive permanentemente:

- **Due societa parallele**: quella fisica e quella digitale, con economie, politiche e culture proprie
- **Migrazione digitale**: agenti che scelgono di vivere permanentemente nel virtuale
- **Economia virtuale**: beni digitali, servizi virtuali, lavoro nel metaverso
- **Criminalita digitale**: hacking, furto di identita, sabotaggio virtuale, terrorismo informatico
- **Identita multiple**: un agente puo avere personalita diverse nel mondo fisico e virtuale
- **Dipendenza**: agenti che perdono interesse per il mondo fisico
- **Potere**: chi controlla l'infrastruttura del metaverso ha potere su milioni di persone

#### Immortalita digitale

Upload della coscienza e sue conseguenze:

- **Chi puo permetterselo**: inizialmente solo i ricchissimi → disuguaglianza permanente
- **Accumulo di potere**: gli immortali digitali accumulano ricchezza, conoscenza e influenza per secoli
- **"Mortali" vs "Immortali"**: nuova divisione di classe, piu profonda di qualsiasi altra nella storia
- **Identita**: un upload e la stessa persona o una copia? Dibattito filosofico che divide la societa
- **Stagnazione vs innovazione**: gli immortali diventano conservatori (hanno troppo da perdere) o sono i piu grandi innovatori (hanno tempo infinito)?
- **Politica**: i mortali possono essere governati da immortali che non comprendono piu la condizione umana
- **Religione**: l'immortalita digitale e salvezza o blasfemia?

### Futurologia reale

#### Il Grande Filtro di Fermi

Perche non vediamo civilta aliene? Forse c'e un ostacolo che distrugge le civilta prima che diventino interstellari.

**Possibili Grandi Filtri simulabili:**
- Guerra nucleare o con armi di distruzione di massa
- AI che sfugge al controllo
- Collasso ambientale irreversibile
- Pandemia ingegnerizzata (bioterrorismo)
- Stagnazione tecnologica (la civilta smette di innovare)
- Auto-distruzione per conflitti interni
- Dipendenza tecnologica seguita da collasso (troppo complesso da mantenere)

**Nel sistema:**
- La dashboard mostra un "indicatore di filtro": quanto la civilta e vicina a potenziali eventi di estinzione
- Se la civilta supera il filtro, il sistema lo segnala come milestone
- L'utente puo iniettare deliberatamente condizioni di filtro per testare la resilienza

#### Scala di Kardashev

Civiltà classificate per consumo energetico:

| Tipo | Energia | Equivalente | Milestone |
|------|---------|-------------|-----------|
| Tipo 0 | Fonti locali (legna, carbone, petrolio) | Civilta terrestre pre-2026 | Punto di partenza |
| Tipo I | Tutta l'energia del pianeta | ~10^16 W | Fusione, rinnovabili totali |
| Tipo II | Tutta l'energia della stella | ~10^26 W (Sfera di Dyson) | Megastrutture stellari |
| Tipo III | Tutta l'energia della galassia | ~10^36 W | Civilta galattica |

**Nel sistema:**
- La dashboard mostra la posizione sulla scala di Kardashev come indicatore di progresso civilizzazionale
- Ogni transizione tra tipi e un salto enorme con implicazioni sociali profonde
- La transizione Tipo 0 → Tipo I e la piu critica (corrisponde spesso al Grande Filtro)
- Il sistema calcola il consumo energetico reale della civilta basandosi sui modelli del Scientific Models Engine

---

## Pattern storici reali come base di conoscenza

La storia reale e il miglior dataset per una simulazione credibile. Il Knowledge Engine deve conoscere a fondo i grandi eventi, le crisi, i boom, i collassi della storia umana e usarli come pattern di riferimento per valutare la plausibilita della simulazione.

### Catalogo di pattern storici

Il sistema ricerca e struttura conoscenza approfondita su eventi storici reali, organizzati per tipo:

#### Crisi e collassi

| Evento storico | Pattern estratto | Condizioni che lo hanno generato |
|---------------|-----------------|--------------------------------|
| Caduta dell'Impero Romano (476) | Sovra-estensione + corruzione + invasioni + perdita di competenze | Burocrazia insostenibile, esercito mercenario, disuguaglianza estrema |
| Peste Nera (1347-1353) | Pandemia → crollo demografico → rivoluzione sociale | Sovrappopolazione, rotte commerciali, assenza di igiene |
| Crollo della civilta Maya (~900) | Collasso ambientale + guerre interne | Deforestazione, siccita, sovrappopolazione, conflitti tra citta-stato |
| Grande Depressione (1929) | Bolla speculativa → crollo finanziario → disoccupazione di massa | Eccesso di credito, speculazione, assenza di regolamentazione |
| Crollo dell'URSS (1991) | Stagnazione economica + rigidita istituzionale + perdita di legittimita | Economia pianificata inefficiente, corsa agli armamenti, aspirazioni nazionali |
| Crisi finanziaria 2008 | Bolla immobiliare → contagio finanziario globale | Deregolamentazione, derivati tossici, avidita sistemica |

#### Guerre e conflitti

| Evento | Pattern | Lezione per la simulazione |
|--------|---------|---------------------------|
| Guerre Puniche | Competizione tra potenze per egemonia → guerra totale | Due potenze in crescita nella stessa regione tendono al conflitto |
| Crociate (1096-1291) | Religione come motivazione bellica + interessi economici | I conflitti "religiosi" hanno quasi sempre cause economiche sottostanti |
| Guerra dei Trent'anni (1618-1648) | Conflitto religioso → devastazione → pace pragmatica | Le guerre ideologiche sono le piu distruttive, la pace arriva per esaurimento |
| Rivoluzioni del 1848 | Contagio rivoluzionario → ondata di insurrezioni simultanee | Le rivoluzioni si propagano come epidemie quando le condizioni sono mature |
| Prima Guerra Mondiale | Alleanze rigide + nazionalismo + incidente → escalation incontrollata | I sistemi di alleanze possono trasformare incidenti locali in catastrofi globali |
| Seconda Guerra Mondiale | Crisi economica + umiliazione nazionale + leader autoritario | Le grandi crisi economiche alimentano l'estremismo e la guerra |

#### Boom economici e rinascimenti

| Evento | Pattern | Condizioni |
|--------|---------|-----------|
| Rinascimento italiano (1400-1600) | Concentrazione di ricchezza + competizione tra citta + riscoperta classica | Commercio fiorente, mecenatismo, liberta intellettuale |
| Rivoluzione Industriale (1760-1840) | Innovazione tecnologica → trasformazione sociale totale | Carbone + ferro + vapore + capitale + liberta imprenditoriale |
| Miracolo economico giapponese (1950-1990) | Ricostruzione post-guerra + investimento in educazione + export | Distruzione come "reset", cultura del lavoro, protezione statale |
| Boom del dopoguerra USA (1945-1970) | Dominio industriale + consumi di massa + classe media | Assenza di concorrenza (Europa distrutta), GI Bill, suburbanizzazione |
| Rivoluzione digitale (1990-presente) | Tecnologia dell'informazione → nuova economia | Internet, semiconduttori, venture capital, globalizzazione |

#### Religioni e movimenti spirituali

| Evento | Pattern | Dinamica |
|--------|---------|----------|
| Nascita del Cristianesimo | Messaggio egualitario in societa diseguale → diffusione tra oppressi | Le religioni nascono dove c'e sofferenza e disuguaglianza |
| Espansione dell'Islam (632-750) | Unificazione tribale + motivazione religiosa + debolezza imperi vicini | Una religione puo unificare popoli frammentati in una forza militare |
| Scisma d'Oriente (1054) | Divergenza culturale + rivalita politica → rottura religiosa | Le divisioni religiose riflettono divisioni politiche e culturali |
| Riforma Protestante (1517) | Corruzione istituzionale + tecnologia (stampa) → frammentazione | La stampa ha fatto per la Riforma quello che internet fa per i movimenti moderni |
| Inquisizione | Istituzione religiosa che usa la violenza per mantenere il potere | Il potere religioso minacciato reagisce con repressione |
| Fondamentalismi moderni | Reazione alla modernizzazione rapida e alla perdita di identita | I movimenti fondamentalisti emergono come resistenza al cambiamento |

#### Regimi totalitari e autoritarismi

| Evento | Pattern | Condizioni di emergenza |
|--------|---------|----------------------|
| Fascismo italiano (1922) | Crisi post-bellica + paura del comunismo + leader carismatico | Instabilita, violenza politica, classe media spaventata |
| Nazismo (1933) | Umiliazione nazionale + crisi economica + propaganda di massa | Trattato di Versailles, iperinflazione, disoccupazione, antisemitismo radicato |
| Stalinismo | Rivoluzione → accentramento → terrore sistematico | Idealismo tradito, paranoia del leader, apparato burocratico |
| Maoismo | Rivoluzione contadina + culto della personalita + ingegneria sociale | Societa agraria, disuguaglianza estrema, imperialismo straniero |
| Apartheid (1948-1991) | Minoranza al potere → segregazione sistematica → resistenza crescente | Colonialismo, razzismo istituzionalizzato, sfruttamento economico |
| Autoritarismo digitale moderno | Tecnologia di sorveglianza + controllo dell'informazione | Stabilita in cambio di liberta, punteggio sociale |

#### Rivoluzioni e cambiamenti sociali

| Evento | Pattern | Meccanismo |
|--------|---------|-----------|
| Rivoluzione Francese (1789) | Disuguaglianza estrema + crisi finanziaria + idee illuministe | Le rivoluzioni scoppiano quando le aspettative crescono ma le condizioni peggiorano |
| Abolizione della schiavitu | Cambiamento morale + pressione economica + conflitto | I cambiamenti morali richiedono generazioni e spesso conflitto |
| Suffragio femminile | Movimento sociale graduale + crisi (guerre) come acceleratore | Le guerre cambiano i ruoli sociali e creano finestre di cambiamento |
| Decolonizzazione (1945-1975) | Indebolimento degli imperi + ideali di autodeterminazione | Gli imperi crollano quando il costo del controllo supera il beneficio |
| Caduta del Muro di Berlino (1989) | Stagnazione + contagio di liberta + perdita di legittimita | I regimi cadono quando smettono di credere in se stessi |

### Come il sistema usa questi pattern

1. **Calibrazione**: i modelli matematici del Scientific Models Engine vengono calibrati sui dati storici reali
2. **Riconoscimento pattern**: il sistema confronta lo stato della simulazione con i pattern storici noti per identificare parallelismi
3. **Plausibilita**: se la simulazione produce una situazione senza precedenti storici, il sistema la segnala per validazione
4. **Enciclopedia Galattica**: le voci enciclopediche possono fare riferimenti a paralleli storici reali
5. **Alert**: "Le condizioni attuali ricordano la Repubblica di Weimar pre-1933" — l'utente viene avvisato di pattern pericolosi

### Corsi e ricorsi — Cicli storici come modello predittivo

La storia non si ripete identica ma segue cicli ricorrenti. Il Knowledge Engine deve conoscere e riconoscere questi cicli per valutare dove si trova la civilta simulata e quali sviluppi sono probabili.

#### Ciclo degli imperi

Ogni grande impero nella storia ha seguito un pattern simile:

```
Fondazione (leader forte, popolo unito da un obiettivo)
    ↓
Espansione (conquiste militari, assimilazione, infrastrutture)
    ↓
Apogeo (ricchezza, cultura, stabilita, potenza massima)
    ↓
Sovra-estensione (confini troppo ampi, costi di difesa insostenibili)
    ↓
Declino (corruzione, perdita di coesione, eserciti mercenari, crisi fiscale)
    ↓
Crollo (invasioni, frammentazione, guerre civili)
    ↓
Dark Age o transizione → nuovo ciclo
```

Esempi storici che seguono questo pattern:
- Impero Romano (fondazione 753 a.C. → crollo 476 d.C.)
- Impero Mongolo (Gengis Khan 1206 → frammentazione ~1368)
- Impero Ottomano (1299 → dissoluzione 1922)
- Impero Britannico (ascesa ~1600 → decolonizzazione ~1960)
- Ogni impero ha le sue specificita ma il ciclo di base si ripete

#### Ciclo di Polibio — Anaciclosi

Il filosofo greco Polibio ha descritto il ciclo delle forme di governo:

```
Monarchia (governo di uno, legittimo)
    ↓ degenera in
Tirannide (governo di uno, corrotto)
    ↓ rovesciata da
Aristocrazia (governo dei migliori)
    ↓ degenera in
Oligarchia (governo dei ricchi, corrotto)
    ↓ rovesciata da
Democrazia (governo del popolo)
    ↓ degenera in
Oclocrazia (governo della folla, caos)
    ↓ genera bisogno di ordine →
Monarchia (ricomincia il ciclo)
```

Il sistema usa questo modello per valutare la stabilita del governo nella simulazione e la probabilita di transizioni.

#### Ciclo di Kondratiev — Onde economiche lunghe

Cicli economici di ~40-60 anni osservati nella storia moderna:

```
Fase di espansione (innovazione tecnologica → crescita → boom)
    ↓
Fase di saturazione (mercati maturi, rendimenti decrescenti)
    ↓
Fase di recessione (crisi, disoccupazione, tensioni sociali)
    ↓
Fase di depressione (ristrutturazione, distruzione creativa)
    ↓
Nuova innovazione → nuovo ciclo
```

Ogni onda e associata a una tecnologia chiave:
- 1a onda (1780-1840): macchina a vapore, tessile
- 2a onda (1840-1890): ferrovie, acciaio
- 3a onda (1890-1940): elettricita, chimica
- 4a onda (1940-1990): petrolio, automobile, elettronica
- 5a onda (1990-2030): informatica, telecomunicazioni
- 6a onda (2030-?): AI, biotecnologia, energia pulita?

#### Ciclo delle crisi di Ibn Khaldun — Asabiyyah

Lo storico arabo Ibn Khaldun (1377) ha descritto il ciclo delle civilta basato sulla "asabiyyah" (coesione sociale):

```
Popolo unito da forte asabiyyah (coesione, solidarieta, obiettivo comune)
    ↓
Conquista del potere (la coesione permette di vincere)
    ↓
Civilta urbana (ricchezza, cultura, raffinatezza)
    ↓
Perdita di asabiyyah (lusso, individualismo, disunita)
    ↓
Vulnerabilita (un nuovo popolo con forte asabiyyah conquista)
    ↓
Ciclo ricomincia con il nuovo popolo
```

Questo pattern spiega: i Barbari che conquistano Roma, i Mongoli che conquistano la Cina, i popoli nomadi che periodicamente rinnovano le civilta sedentarie.

#### Fattori scatenanti delle grandi guerre

Il Knowledge Engine deve conoscere i pattern che portano ai conflitti su larga scala:

**Guerre Mondiali — pattern comune:**
- Competizione tra potenze per egemonia (multipolarismo instabile)
- Corsa agli armamenti che aumenta la tensione
- Sistemi di alleanze rigidi che trasformano conflitti locali in globali
- Nazionalismo come forza mobilitante
- Crisi economica che alimenta estremismo
- Un incidente (Sarajevo 1914, Polonia 1939) che fa scattare il meccanismo

**Invasioni "barbariche" — pattern comune:**
- Civilta sedentaria ricca ma militarmente debole
- Popolo nomade o periferico con forte coesione e pressione (climatica, demografica)
- Frontiera che si indebolisce (costi di difesa troppo alti)
- Assimilazione graduale seguita da conquista improvvisa
- Spesso i "barbari" erano gia dentro l'impero come mercenari o alleati

**Conquiste di tipo "Gengis Khan" — pattern:**
- Leader eccezionale che unifica popoli frammentati
- Innovazione militare (cavalleria mongola, falangi macedoni, legioni romane)
- Civilta vicine divise e in conflitto tra loro
- Velocita di conquista che supera la capacita di reazione dei difensori
- Problema della successione: l'impero si frammenta dopo la morte del fondatore

#### Come il sistema usa i cicli

Il Scientific Models Engine integra i cicli storici come **modelli predittivi probabilistici**:

1. **Posizionamento ciclico**: il sistema valuta in quale fase di ogni ciclo si trova la civilta
   - Dashboard: "Ciclo imperiale: fase di declino (indicatori: corruzione +45%, coesione -30%, costi militari +60%)"
2. **Probabilita di transizione**: basata sulla posizione nei cicli, calcola la probabilita di eventi
   - "Probabilita di rivoluzione nei prossimi 20 anni: 67% (basato su: disuguaglianza alta, fiducia nelle istituzioni bassa, precedenti storici)"
3. **Pattern matching**: confronta lo stato attuale con situazioni storiche simili
   - "Le condizioni attuali ricordano l'Europa pre-1914: multipolarismo, corsa agli armamenti, alleanze rigide"
4. **Non determinismo**: i cicli indicano tendenze, non certezze. Un leader eccezionale, un'innovazione o un evento casuale possono rompere il ciclo

### Non determinismo storico

I pattern storici sono **indicatori, non destini**. Le stesse condizioni possono produrre esiti diversi:
- La crisi economica del 1929 ha prodotto il New Deal in USA e il Nazismo in Germania
- Il contesto, la leadership, la cultura e il caso determinano quale strada viene presa
- Epocha usa i pattern come probabilita, non come certezze

---

## Riproducibilita scientifica

Per essere un vero strumento di esperimento sociale, Epocha deve garantire riproducibilita: stesso input = stesso output.

### Seed deterministico

- Ogni simulazione ha un **seed numerico** che inizializza tutti i generatori di numeri casuali
- Stesso seed + stessi parametri + stessa versione di Epocha = stessa simulazione identica
- Questo permette esperimenti controllati: cambia UNA variabile e confronta i risultati

### Sfide della riproducibilita con LLM

I modelli LLM non sono perfettamente deterministici (temperature > 0, batching, aggiornamenti del modello). Strategie per mitigarle:

**Temperature zero dove possibile:**
- Per decisioni critiche che devono essere riproducibili, usare temperature = 0
- Per conversazioni e contenuto narrativo, temperatura piu alta e accettabile (non influenza la simulazione)

**Versioning completo:**
- Il seed della simulazione include: versione Epocha, versione modello LLM, parametri esatti
- Se il modello LLM cambia versione, la simulazione potrebbe divergere — questo viene tracciato e segnalato

**Logging deterministico:**
- Ogni decisione di ogni agente viene registrata con input e output esatti
- In caso di divergenza, si puo identificare il punto esatto in cui le simulazioni hanno preso strade diverse

### Confronto controllato

La riproducibilita abilita il confronto scientifico:
```
Simulazione A: seed=42, parametri standard
Simulazione B: seed=42, parametri standard + demagogo iniettato all'anno 50

Confronto: tutto cio che diverge tra A e B e conseguenza diretta del demagogo
```

Senza riproducibilita, non si puo distinguere la conseguenza di una variabile dal rumore stocastico. Con la riproducibilita, Epocha diventa uno strumento scientifico, non solo un simulatore.

---

## Iniezione di Variabili (Modalita Sperimentale)

L'utente puo intervenire sulla simulazione come uno sperimentatore:

**Iniezione eventi:**
- Crisi economica, epidemia, scoperta tecnologica, disastro naturale
- Scandalo politico, guerra, carestia
- Eventi personalizzabili con parametri (intensita, durata, area geografica)

**Iniezione personaggi:**

L'utente puo inserire un individuo con caratteristiche specifiche in qualsiasi momento della simulazione per osservare il suo effetto sulla societa. Due modalita:

*Modalita archetipo:* l'utente sceglie un profilo predefinito e lo personalizza:

| Archetipo | Tratti chiave | Effetto tipico sulla societa |
|-----------|-------------|------------------------------|
| Dittatore/Tiranno | Autoritario, carismatico, spietato, paranoico | Accentramento potere, repressione, polarizzazione |
| Leader democratico | Empatico, diplomatico, visionario, inclusivo | Riforme, dialogo, stabilita o cambiamento graduale |
| Demagogo/Populista | Carismatico, manipolatore, anti-establishment | Divisione sociale, erosione istituzioni, mobilitazione masse |
| Scienziato geniale | Intelletto estremo, ossessivo, visionario | Accelerazione tecnologica, disruption economica/sociale |
| Profeta/Leader religioso | Carisma spirituale, convinzione assoluta, ascetismo | Nuovo movimento religioso, scisma, conflitto con autorita |
| Rivoluzionario | Idealista, coraggioso, intransigente | Insurrezione, cambio di regime, instabilita |
| Conquistatore | Strategico, ambizioso, militarista | Espansione, guerre, unificazione forzata |
| Filosofo/Intellettuale | Pensatore profondo, comunicatore, anticonformista | Nuova corrente filosofica, cambiamento culturale |
| Imprenditore visionario | Innovativo, competitivo, ossessionato dal successo | Rivoluzione economica, nuove industrie, disuguaglianza |
| Sabotatore/Agente del caos | Distruttivo, imprevedibile, antisociale | Destabilizzazione, crisi, reazioni a catena |
| Diplomatico/Mediatore | Paziente, empatico, strategico | Pace, alleanze, risoluzione conflitti |
| Artista rivoluzionario | Creativo, provocatorio, carismatico | Movimento culturale, cambiamento di valori |

*Modalita libera:* l'utente descrive il personaggio in linguaggio naturale:
- "Un fisico nucleare con tendenze megalomani che vuole costruire un'arma definitiva"
- "Una giovane contadina analfabeta che crede di sentire la voce degli dei e inizia a predicare"
- "Un mercante straniero che arriva con tecnologie mai viste dalla civilta locale"

Il sistema genera un agente completo con personalita, storia, motivazioni coerenti con la descrizione.

*Personalita storiche (modalita "What if"):*
L'utente puo descrivere un personaggio ispirato a figure storiche reali per esperimenti controfattuali:
- "Un leader con le caratteristiche di Napoleone in una societa medievale"
- "Un pensatore con l'approccio di Gandhi in una societa militarista"
- "Uno scienziato con il genio di Einstein in una civilta pre-industriale"

Il sistema non replica la persona storica ma genera un agente con tratti simili, inserito nel contesto della simulazione.

*Configurazione dell'iniezione:*
- **Quando**: in qualsiasi momento della simulazione
- **Dove**: in quale zona geografica, citta, gruppo sociale
- **Con quale ruolo**: da semplice cittadino a posizione di potere
- **Con quali risorse**: povero, ricco, con seguaci, isolato
- **Osservazione**: l'utente puo seguire specificamente l'agente iniettato e il suo impatto nel tempo tramite la dashboard

L'agente "Mulo" — l'individuo imprevedibile che puo sovvertire le previsioni statistiche, ispirato alla saga della Fondazione di Asimov.

**Iniezione gruppi:**

Oltre ai singoli individui, l'utente puo iniettare **gruppi organizzati** che perseguono un obiettivo comune. Un gruppo iniettato e piu potente di un singolo perche ha massa critica, coordinazione e resilienza.

*Tipi di gruppi iniettabili:*

| Tipo | Descrizione | Esempio |
|------|------------|---------|
| Movimento politico | Gruppo con agenda politica comune | Partito rivoluzionario, lobby industriale, movimento indipendentista |
| Setta/Ordine religioso | Gruppo con credenze condivise e struttura interna | Ordine monastico, setta millenarista, missionari |
| Organizzazione segreta | Gruppo nascosto con obiettivi occulti | Cospirazione per rovesciare il governo, societa segreta di scienziati |
| Esercito/Milizia | Forza armata organizzata | Mercenari, esercito ribelle, guardia pretoriana |
| Corporazione/Gilda | Gruppo con interessi economici | Cartello commerciale, gilda di artigiani, monopolio |
| Comunita di coloni | Gruppo che si insedia in un nuovo territorio | Coloni ideologici, rifugiati, esploratori |
| Movimento culturale | Gruppo che promuove un cambiamento culturale | Artisti avanguardisti, filosofi illuministi, riformatori |
| Rete di spionaggio | Gruppo infiltrato nella societa | Spie di una civilta rivale, informatori, sabotatori |

*Configurazione del gruppo:*
- **Dimensione**: da pochi individui a centinaia
- **Coesione**: quanto sono uniti (monolitico vs fazioni interne)
- **Obiettivo**: descritto in linguaggio naturale ("rovesciare la monarchia", "diffondere una nuova religione", "monopolizzare il commercio del ferro")
- **Strategia**: aperta o clandestina, violenta o pacifica, rapida o graduale
- **Leadership**: il gruppo ha un leader definito o e orizzontale?
- **Risorse**: fondi, armi, conoscenze, contatti
- **Inserimento**: arrivano dall'esterno (immigrati, invasori) o emergono dall'interno (cellule dormienti, conversioni)

*Dinamiche del gruppo iniettato:*
- Il gruppo interagisce con la societa esistente secondo la sua strategia
- I membri della societa possono unirsi al gruppo se ne condividono i valori
- Il gruppo puo frammentarsi se sorgono dissidi interni
- La societa puo reagire: accoglienza, resistenza, persecuzione, assimilazione
- Il gruppo puo riuscire nel suo obiettivo, fallire, o trasformarsi in qualcosa di diverso da cio che era

*Combinazione individuo + gruppo:*
L'utente puo iniettare un leader E il suo gruppo insieme, o prima il gruppo e poi il leader (o viceversa), per testare se e l'individuo che crea il movimento o il movimento che crea il leader

**Modifica regole:**
- Cambiare le condizioni economiche (inflazione, tasse)
- Modificare le leggi
- Alterare la disponibilita di risorse
- Cambiare il sistema di governo

---

## Persistenza e Salvataggio

**Stato della simulazione:**
- PostgreSQL per la persistenza a lungo termine (agenti, storia, branch, analisi)
- Redis per lo stato real-time e la cache
- Ogni branch ha il proprio namespace nel DB

**Scenari multipli con branching:**
- Creazione di simulazioni parallele con parametri diversi
- Fork da qualsiasi punto temporale
- Confronto tra branch sulla stessa finestra temporale
- Ogni branch e una simulazione completa e indipendente

---

## Considerazioni Tecniche

### Scalabilita

- Celery con N worker per processare centinaia di agenti in parallelo
- L'aggregazione individuo/gruppo riduce il numero di chiamate LLM attive
- Level of detail nel rendering (clustering a basso zoom)
- Viewport culling per la mappa

### Costi LLM

- **Model Routing a 3 livelli**: 90% locale ($0), 8% API economica, 2% API premium → riduzione costi 90%+
- **Aggregazione gruppo**: Meno agenti attivi = meno chiamate LLM
- **Prompt Caching**: 90% di sconto su cache hit (Anthropic), system prompt condiviso tra agenti
- **Batch API**: 50% di sconto per simulazioni a turni (non real-time)
- **Decision Trees**: Azioni ripetitive senza LLM, solo decisioni complesse richiedono ragionamento AI
- **Modelli locali (vLLM)**: Costo zero per il grosso delle decisioni, performance ottimali con alta concorrenza
- **Budget control**: Monitoraggio costi in tempo reale, auto-pausa al raggiungimento del budget massimo
- **Stima pre-simulazione**: L'utente vede il costo stimato prima di avviare

### Deployment: Docker / Docker Compose

Il deployment tramite Docker e Docker Compose e un requisito fondamentale. L'utente deve poter avviare l'intero sistema con un singolo comando.

**docker-compose.yml** orchestrera i seguenti servizi:

| Servizio | Immagine | Ruolo |
|----------|---------|-------|
| `web` | Django/DRF | API server + Django Channels (WebSocket) |
| `frontend` | React (Nginx) | Interfaccia utente |
| `celery-worker` | Django + Celery | Processing agenti AI, tick simulazione |
| `celery-beat` | Django + Celery Beat | Scheduler per task periodici |
| `redis` | Redis | Cache, broker Celery, pub/sub real-time |
| `db` | PostGIS (PostgreSQL + PostGIS + pgvector) | Database principale: relazionale + spaziale + vettoriale |
| `vllm` (opzionale) | vLLM | Server modelli locali per inference |

**Avvio in un comando:**
```bash
git clone https://github.com/epocha/epocha.git
cd epocha
cp .env.example .env  # configurare API keys
docker compose up
```

**Requisiti:**
- `.env.example` con tutte le variabili documentate (API keys, configurazione DB, parametri simulazione)
- Dockerfile multi-stage per build ottimizzate (ridurre dimensione immagini)
- Volume per persistenza dati PostgreSQL e Redis
- Health check su tutti i servizi
- Scaling orizzontale dei worker Celery: `docker compose up --scale celery-worker=4`
- Profilo "lite" senza vLLM per chi usa solo API esterne: `docker compose --profile lite up`
- Profilo "full" con vLLM per chi vuole modelli locali: `docker compose --profile full up`

### Evoluzione futura

L'architettura modulare permette di:
- Estrarre il Simulation Engine in un servizio separato quando la scala lo richiede
- Aggiungere nuovi provider LLM senza modificare il resto
- Scalare i Celery worker orizzontalmente: `docker compose up --scale celery-worker=N`
- Aggiungere nuovi moduli (es. religione, arte, scienza) senza impattare i moduli esistenti
- Deployment su Kubernetes per ambienti production (Helm chart come evoluzione futura)

---

## MVP — Minimum Viable Product

Il design completo descrive un sistema con 15+ moduli. L'MVP contiene il minimo necessario per avere una simulazione funzionante, interessante e rilasciabile.

### Principio: una simulazione semplice ma completa

L'MVP deve permettere a un utente di: creare un mondo, farlo evolvere, osservarlo e chattare con gli agenti. Tutto il resto viene dopo.

### Cosa include l'MVP

```
MVP Epocha v0.1
|
|-- Simulation Engine (base)
|   |-- Tick loop con play/pausa/velocita
|   |-- Tempo simulato (giorni/mesi/anni)
|   +-- NO branching, NO auto-stop condizionale
|
|-- Agents Module (base)
|   |-- Agenti con personalita (Big Five + background)
|   |-- Memoria semplificata (ultimi N eventi + eventi emotivamente forti)
|   |-- Decisioni LLM per azioni significative
|   |-- NO aggregazione dinamica gruppo
|   |-- NO ciclo di vita (nascita/morte)
|   +-- 20-50 agenti (non centinaia)
|
|-- World Module (semplificato)
|   |-- Economia livello "Base" (moneta, lavoro, compravendita)
|   |-- Mappa semplice: 3-5 zone con risorse
|   |-- NO PostGIS inizialmente (coordinate semplici x,y)
|   |-- NO politica complessa, NO istituzioni
|   +-- Regole di base: se risorse scarse → tensione
|
|-- Chat Module (base)
|   |-- Chat 1-a-1 con qualsiasi agente
|   |-- Solo modalita osservatore
|   |-- NO chat di gruppo, NO modalita dio/abitante
|   +-- Pannello laterale semplice
|
|-- LLM Adapter (un solo provider)
|   |-- Supporto per UN provider (Claude API o OpenAI)
|   |-- NO model routing, NO modelli locali
|   |-- Rate limiting base
|   +-- Monitoraggio costi semplice
|
|-- Frontend (minimale)
|   |-- Mappa 2D semplice (Canvas, non Pixi.js)
|   |-- Lista agenti con posizione
|   |-- Feed eventi (lista testuale)
|   |-- Pannello chat
|   |-- Controlli play/pausa/velocita
|   +-- NO dashboard analitica, NO grafo relazionale
|
|-- Input (solo Express)
|   |-- Campo di testo: descrivi il mondo
|   |-- LLM genera: agenti, mappa, economia
|   +-- NO template, NO configurazione manuale
|
|-- Infrastruttura
|   |-- Django + DRF + Django Channels
|   |-- PostgreSQL (senza PostGIS, senza pgvector)
|   |-- Redis (cache + broker Celery)
|   |-- Celery (1-2 worker)
|   |-- Docker Compose (4 servizi: web, db, redis, celery)
|   +-- NO MCP server, NO vLLM
```

### Cosa NON include l'MVP

| Feature | Perche non nell'MVP | Quando |
|---------|-------------------|--------|
| Branching/Fork | Complesso da implementare, serve prima stabilita del core | v0.2 |
| Aggregazione gruppi | Richiede logica sofisticata, testabile solo con molti agenti | v0.2 |
| Knowledge Engine (ricerche web) | Progetto a se stante, l'MVP usa knowledge base statica | v0.3 |
| Scientific Models Engine | I modelli matematici arrivano dopo il core funzionante | v0.3 |
| PostGIS / pgvector | Overhead iniziale, coordinate semplici bastano per l'MVP | v0.2 |
| MCP Server | Serve prima un core stabile da esporre | v0.3 |
| Modalita Dio/Abitante | Chat osservatore e sufficiente per validare il concept | v0.2 |
| Dashboard analitica | Serve prima abbastanza dati da analizzare | v0.2 |
| Ciclo di vita (nascita/morte) | Aggiunge complessita, testabile dopo | v0.3 |
| Plugin system | Serve prima un'architettura stabile da estendere | v0.4 |
| Multiplayer | Feature avanzata, serve community prima | v0.5+ |
| Espansione spaziale | Molto avanzato, serve civilta terrestre funzionante prima | v1.0+ |
| Lingua/cultura/religione | Arricchimenti che vengono dopo il core | v0.4+ |
| Modelli locali (vLLM/Ollama) | Un provider API basta per validare | v0.2 |

### Roadmap incrementale

```
v0.1 (MVP)
  Simulazione base: 20-50 agenti, economia semplice,
  mappa 2D, chat osservatore, modalita Express.
  "Funziona, e interessante, posso parlare con gli agenti."

v0.2 (Core solido)
  + Branching/fork
  + PostGIS per geografia reale
  + Aggregazione individuo/gruppo
  + Model routing (locale + API)
  + Dashboard analitica base
  + Modalita Dio
  + 100-200 agenti

v0.3 (Profondita)
  + Knowledge Engine (ricerche web)
  + Scientific Models Engine (modelli matematici)
  + Ciclo di vita (nascita/morte/generazioni)
  + MCP Server
  + pgvector per retrieval semantico
  + Iniezione personaggi/gruppi/eventi

v0.4 (Ricchezza)
  + Lingua e deriva linguistica
  + Arte, filosofia, cultura, religione
  + Plugin system
  + Educazione, criminalita, giustizia
  + Strutture familiari
  + Information Flow (passaparola, distorsione)

v0.5 (Piattaforma)
  + Multiplayer / mondi collaborativi
  + Condivisione simulazioni
  + Crisi Seldon automatiche
  + Enciclopedia Galattica
  + Cicli storici come modello predittivo

v1.0 (La visione completa)
  + Espansione spaziale
  + Civilta multiple e primo contatto
  + Bioingegneria, transumanesimo
  + Scala di Kardashev
  + Generazione esopianeti
  + Tutto il design doc
```

### Criterio di successo dell'MVP

L'MVP e riuscito se:
1. Un utente scrive "Un villaggio medievale con 30 persone, un fabbro ambizioso e un prete corrotto"
2. Il sistema genera il mondo e parte la simulazione
3. Dopo 10 minuti di simulazione (= mesi simulati), sono successe cose interessanti ed emergenti
4. L'utente chatta con il fabbro e lui racconta cosa gli e successo con coerenza
5. L'utente vuole continuare a guardare cosa succede

Se questi 5 punti funzionano, l'MVP e un successo.

---

## Non-goals — Cosa Epocha NON e

Per evitare scope creep e chiarire i confini del progetto:

- **Non e un gioco** — Non c'e un obiettivo da raggiungere, un punteggio, una vittoria. E un simulatore e uno strumento di osservazione/sperimentazione.
- **Non e un motore di predizione** — A differenza di MiroFish, Epocha non promette di "prevedere il futuro". Produce scenari plausibili, non previsioni.
- **Non e un modello climatico/economico/demografico** — I modelli scientifici sono semplificazioni utili alla simulazione, non strumenti di ricerca specialistica.
- **Non e un social network** — La piattaforma di condivisione (Fase 2+) e un hub per simulazioni, non un social network.
- **Non e real-time** — La simulazione non gira in tempo reale come un MMO. E un simulatore a tick con controllo di velocita.
- **Non sostituisce paper scientifici** — I risultati delle simulazioni sono indicativi, non hanno valore di pubblicazione scientifica senza validazione indipendente.

---

## Riproducibilita — Riformulazione realistica

La sezione precedente sulla riproducibilita va riformulata. La riproducibilita esatta con LLM e **tecnicamente impossibile** anche con temperature=0, a causa di:
- Non-determinismo dei provider cloud (batching interno, hardware diverso)
- Non-determinismo dei modelli locali (parallelismo GPU)
- Aggiornamenti dei modelli che cambiano i pesi

### Approccio realistico: riproducibilita statistica + replay

**Riproducibilita statistica:**
- Stesse condizioni iniziali producono **distribuzioni di esiti simili**, non esiti identici
- Su N simulazioni con gli stessi parametri, i pattern macro convergono anche se i dettagli differiscono
- Esempio: "su 10 simulazioni con questi parametri, 7 producono una rivoluzione entro il secolo 3"

**Sistema di replay basato su log:**
- Ogni decisione di ogni agente viene registrata con: input (contesto), output (decisione), timestamp, modello usato
- Una simulazione puo essere "replayata" ri-applicando le stesse decisioni senza richiamare l'LLM
- Il replay e deterministico al 100%: produce sempre lo stesso risultato
- Utile per: debugging, analisi post-hoc, confronto preciso tra branch

**Seed per la parte non-LLM:**
- I generatori di numeri casuali (eventi stocastici, disastri naturali, mutazioni genetiche) usano un seed deterministico
- La parte deterministica della simulazione (modelli matematici, regole del mondo) e perfettamente riproducibile
- Solo le decisioni LLM introducono variabilita

**Versioning completo:**
- Ogni simulazione registra: versione Epocha, modello LLM usato (nome + versione), parametri completi, seed
- Se il modello LLM cambia, il sistema avvisa che le simulazioni precedenti non sono confrontabili a livello micro

---

## Modello Dati — Schema ad alto livello

### Entita principali

```
+------------------+       +------------------+       +------------------+
|   Simulation     |       |     Agent        |       |    Memory        |
|------------------|       |------------------|       |------------------|
| id (PK)          |       | id (PK)          |       | id (PK)          |
| name             |  1:N  | simulation_id(FK)|  1:N  | agent_id (FK)    |
| description      |------>| name             |------>| content          |
| seed             |       | personality_json |       | emotional_weight |
| status           |       | position (PostGIS|       | created_at       |
| current_tick     |       |   Point)         |       | decay_rate       |
| config_json      |       | age              |       | source_type      |
| parent_id (FK)   |       | health           |       | reliability      |
| branch_point     |       | wealth           |       | embedding(vector)|
| created_by       |       | role             |       +------------------+
| created_at       |       | group_id (FK)    |
+------------------+       | is_individual    |       +------------------+
                           | parent_agent(FK) |       |   Relationship   |
+------------------+       +------------------+       |------------------|
|     World        |                                   | id (PK)          |
|------------------|       +------------------+       | agent_from (FK)  |
| id (PK)          |       |     Group        |       | agent_to (FK)    |
| simulation_id(FK)|       |------------------|       | type (enum)      |
| economy_level    |       | id (PK)          |       | strength         |
| political_system |       | simulation_id(FK)|       | sentiment        |
| tech_level       |       | name             |       | since_tick       |
| climate_json     |       | objective        |       +------------------+
| resources_json   |       | cohesion         |
+------------------+       | parent_group(FK) |       +------------------+
                           | leader_id (FK)   |       |     Event        |
+------------------+       +------------------+       |------------------|
|     Zone         |                                   | id (PK)          |
|------------------|       +------------------+       | simulation_id(FK)|
| id (PK)          |       |  TechNode        |       | tick             |
| simulation_id(FK)|       |------------------|       | type (enum)      |
| name             |       | id (PK)          |       | description      |
| geometry (PostGIS|       | name             |       | zone_id (FK)     |
|   Polygon)       |       | domain           |       | caused_by        |
| type (enum)      |       | prerequisites[]  |       | consequences_json|
| resources_json   |       | conditions_json  |       | severity         |
| climate_zone     |       | discovered_tick  |       | is_seldon_crisis |
| population       |       | discovered_by(FK)|       +------------------+
+------------------+       +------------------+
                                                       +------------------+
+------------------+       +------------------+       |  DecisionLog     |
| KnowledgeEntry   |       |    User          |       |------------------|
|------------------|       |------------------|       | id (PK)          |
| id (PK)          |       | id (PK)          |       | simulation_id(FK)|
| domain           |       | username         |       | tick             |
| content          |       | email            |       | agent_id (FK)    |
| source_url       |       | role (enum)      |       | input_context    |
| embedding(vector)|       | api_keys_enc     |       | output_decision  |
| references_json  |       +------------------+       | llm_model        |
| created_at       |                                   | llm_temperature  |
+------------------+                                   | cost_tokens      |
                                                       +------------------+
```

### Strategia di branching nel database

Il branching (fork di simulazioni) e una feature critica. Strategia scelta: **Copy-on-Write con namespace**.

**Come funziona:**
1. Quando l'utente fa un fork, il sistema crea una nuova Simulation con `parent_id` che punta alla simulazione originale e `branch_point` che indica il tick di divergenza
2. **Non si copiano i dati**: il branch condivide i dati fino al `branch_point` con il parent
3. Da quel punto in poi, ogni modifica crea nuovi record nel branch
4. Le query leggono: prima i dati del branch corrente, poi risalgono al parent per i dati precedenti al branch_point

**Implementazione pratica:**
- Ogni tabella ha `simulation_id` come foreign key
- Una query per il branch B al tick 500 (branch_point = 300):
  - Tick 0-300: legge da simulation A (parent)
  - Tick 301-500: legge da simulation B
- Indice composto `(simulation_id, tick)` su tutte le tabelle temporali
- Per simulazioni con molti branch, si puo fare un "snapshot" periodico che materializza lo stato completo

**Vantaggi:**
- Fork istantaneo (nessuna copia di dati)
- Risparmio spazio disco
- Confronto naturale: i dati prima del branch_point sono gli stessi

**Svantaggi:**
- Query piu complesse (join con parent)
- Per branch molto divergenti su tempi lunghi, le performance possono degradare
- In quel caso: materializzazione periodica dello snapshot

### Tipo di dati chiave

| Campo | Tipo PostgreSQL | Note |
|-------|----------------|------|
| position | `geometry(Point, 4326)` | PostGIS, coordinate geografiche |
| zone geometry | `geometry(Polygon, 4326)` | PostGIS, aree |
| personality_json | `jsonb` | Tratti Big Five, valori, background (flessibile, interrogabile) |
| embedding | `vector(1536)` | pgvector, per retrieval semantico |
| resources_json | `jsonb` | Risorse per zona/agente (flessibile) |
| config_json | `jsonb` | Configurazione simulazione (tutti i parametri) |

---

## LLM Bias Correction

I modelli LLM tendono a produrre comportamenti degli agenti piu polarizzati, piu gregari e piu drammatici di quanto gli esseri umani reali farebbero nella stessa situazione. Senza correzione, le simulazioni esagerano sistematicamente conflitti, estremismo e pensiero di gruppo.

### Meccanismi di correzione

**Parametro di attenuazione (configurabile):**
- Ogni simulazione ha un parametro `bias_correction` (0.0 = nessuna correzione, 1.0 = massima attenuazione)
- Il sistema post-processa le decisioni degli agenti attenuando le reazioni estreme:
  - Se un agente decide un'azione molto aggressiva, il bias correction riduce la probabilita che venga eseguita
  - Se tutti gli agenti convergono sulla stessa opinione troppo velocemente (comportamento gregario), il sistema introduce dissenso artificiale proporzionale al parametro

**Calibrazione su dati storici:**
- Il Knowledge Engine confronta i pattern comportamentali della simulazione con quelli storici reali
- Se la polarizzazione nella simulazione cresce 5x piu velocemente di quanto storicamente documentato, il sistema segnala l'anomalia
- L'utente puo decidere se accettare il risultato o aumentare la correzione

**Trasparenza:**
- Ogni correzione applicata viene loggata nel DecisionLog
- La dashboard mostra un indicatore di "bias level" per la simulazione
- L'utente puo disattivare completamente la correzione per osservare il comportamento "raw" dell'LLM

---

## Stima pre-simulazione dei costi

Prima di avviare una simulazione, il sistema calcola e mostra una stima dettagliata di costi e tempi.

### Cosa viene stimato

| Metrica | Come si calcola | Esempio |
|---------|----------------|---------|
| Costo LLM totale | (agenti x tick stimati x costo medio per decisione) + generazione mondo | "$3.50 per 200 agenti, 100 tick" |
| Tempo di calcolo | tick stimati x tempo medio per tick (basato su provider e concorrenza) | "~2 ore con Gemini free tier" |
| Numero di richieste API | agenti x tick + chat stimate + generazione | "2.150 richieste, entro il limite free tier" |
| Spazio disco | agenti x tick x dimensione media record | "~150 MB di database" |

### Presentazione all'utente

Prima dell'avvio, il sistema mostra:
```
Stima simulazione:
- Agenti: 30
- Durata simulata: 200 anni (~500 tick a risoluzione adattiva)
- Costo LLM stimato: $2.80 (Gemini Flash-Lite)
- Tempo di calcolo: ~1.5 ore
- Richieste API: ~1.800 (entro limite free tier giornaliero)
- Spazio disco: ~100 MB

[Avvia] [Modifica parametri]
```

Se il costo supera il budget impostato dall'utente, il sistema suggerisce come ridurlo (meno agenti, risoluzione piu bassa, modello piu economico).

---

## Report automatico di fine simulazione

Al termine di una simulazione (raggiunto il tempo massimo, condizione di arresto, o pausa manuale), il sistema genera automaticamente un report narrativo strutturato che analizza cosa e successo.

### Contenuto del report

**Sezione 1 — Panoramica:**
- Periodo simulato (dal tick X al tick Y, corrispondente agli anni A-B)
- Numero di agenti coinvolti, gruppi formati, eventi significativi
- Posizione nella scala di Kardashev (se applicabile)

**Sezione 2 — Eventi chiave:**
- Timeline degli eventi piu significativi (auto-milestone) con descrizione narrativa
- Crisi Seldon rilevate e come sono state risolte (o non risolte)
- Scoperte tecnologiche e il loro impatto

**Sezione 3 — Analisi dei pattern:**
- Cicli storici identificati (ascesa/declino, cicli economici)
- Correlazioni rilevate ("ogni volta che X e successo, Y e seguito entro Z anni")
- Confronto con pattern storici reali ("questa dinamica ricorda la caduta dell'Impero Romano per...")

**Sezione 4 — Agenti notevoli:**
- Gli individui che hanno avuto il maggiore impatto sulla storia
- Leader, innovatori, rivoluzionari, distruttori emersi dalla simulazione
- Il loro profilo di personalita e come ha influenzato le loro azioni

**Sezione 5 — Confronto tra branch (se esistono):**
- Dove e quando i branch hanno diverguto
- Quali variabili hanno causato le differenze
- Quale branch ha prodotto l'esito "migliore" (per varie metriche)

**Sezione 6 — Metriche finali:**
- Stabilita sociale finale, distribuzione ricchezza (Gini), demografia
- Costo LLM effettivo vs stimato
- Statistiche di performance (tick/secondo, decisioni/tick)

### Formato e export

Il report e generato dall'LLM in stile narrativo professionale (come una voce dell'Enciclopedia Galattica) e puo essere esportato in:
- Markdown
- PDF
- JSON (dati strutturati per analisi programmatica)

---

## Gestione errori LLM

### Scenari di errore e risposte

| Errore | Risposta del sistema | Impatto sulla simulazione |
|--------|---------------------|--------------------------|
| Rate limit provider | Retry con backoff esponenziale, poi fallback a provider secondario | Ritardo nel tick, nessuna perdita |
| Timeout | Retry 1 volta, poi decisione di default basata su personality + regole | L'agente prende una decisione "sicura" senza LLM |
| Contenuto filtrato | Log dell'evento, rigenera prompt senza contenuto problematico | Decisione leggermente diversa |
| Risposta incoerente (allucinazione) | Validazione output: la decisione e coerente con la personalita e lo stato? Se no, rigenera | Ritardo, possibile decisione alternativa |
| Agente in loop | Contatore di decisioni ripetitive, dopo N ripetizioni forza una decisione diversa o mette l'agente in "pausa riflessiva" | L'agente si ferma a "pensare" per qualche tick |
| Modello locale non caricabile | Fallback ad API esterna, log warning | Costo aumentato temporaneamente |
| Budget esaurito | Auto-pausa simulazione, notifica utente | Simulazione in pausa fino a intervento utente |
| Fallback a modello diverso | Log che il modello e cambiato, flag nel DecisionLog | La coerenza potrebbe risentirne — segnalato nel log |

### Principio guida

La simulazione non deve mai **crashare** per un errore LLM. Ogni errore ha un fallback che mantiene la simulazione in esecuzione, anche se con qualita ridotta. L'utente viene sempre informato tramite il feed eventi e la dashboard.

---

## Strategia di test

### Livelli di test

| Livello | Cosa testa | Strumenti |
|---------|-----------|-----------|
| Unit test | Modelli matematici, logica di business, serializzatori DRF | pytest, Django TestCase |
| Integration test | Ciclo tick completo, interazione tra moduli, API endpoint | pytest + Django test client |
| LLM quality test | Coerenza decisioni agenti, qualita risposte chat | Framework di evaluation custom con metriche |
| Performance test | Latenza tick, throughput agenti, utilizzo memoria | locust, pytest-benchmark |
| End-to-end | Flusso completo: creazione simulazione → tick → chat → fork | Playwright (frontend) + API test |

### Test specifici per la simulazione

- **Test di coerenza**: una simulazione di 100 tick non deve produrre contraddizioni (agente morto che agisce, risorsa esaurita che viene usata)
- **Test di regressione**: simulazioni di riferimento salvate come "golden files", confrontate con output attuale
- **Test di stress**: 500 agenti, 1000 tick, monitoraggio memory leak e performance degradation
- **Test dei modelli scientifici**: ogni modello matematico ha test che verificano output contro dati storici reali

---

## Sicurezza

### Superficie di attacco e mitigazioni

| Rischio | Mitigazione |
|---------|------------|
| Prompt injection via chat | Sanitizzazione input, system prompt protetto, separazione tra input utente e contesto agente |
| Plugin malevoli | Sandboxing con container isolati, nessun accesso al filesystem host, review obbligatoria |
| API key esposte | Encryption at rest (Fernet/AES), mai in log o response, .env mai committato |
| Accesso non autorizzato MCP | Autenticazione token per ogni connessione MCP, ruoli e permessi verificati ad ogni tool call |
| SQL injection | ORM Django (parametrizzazione automatica), nessuna raw query senza validazione |
| Denial of service (simulazione infinita) | Limiti configurabili: max tick, max agenti, max branches, timeout per simulazione |
| Dati sensibili nelle simulazioni | Le simulazioni possono essere private (default) o pubbliche. Export anonimizzabile |

### Autenticazione MCP + Multiplayer

- Ogni client MCP si autentica con un **token API** associato a un utente
- Il token porta con se il ruolo dell'utente nella simulazione (creatore, co-sperimentatore, osservatore, ecc.)
- Ogni tool call verifica i permessi: un osservatore non puo chiamare `epocha_inject_event`
- Le sessioni WebSocket (web app) e MCP condividono lo stesso sistema di autenticazione (Django auth + token)

---

## Monitoraggio e Observability

### Metriche di sistema

| Metrica | Strumento | Alert |
|---------|-----------|-------|
| Latenza per tick | Prometheus + Grafana | > 30s per tick |
| Coda Celery (tasks in attesa) | Flower + Prometheus | > 100 task in coda |
| Utilizzo memoria Redis | Redis INFO | > 80% memoria |
| Dimensione DB per simulazione | Query periodica | > 10GB per simulazione |
| Costo LLM accumulato | Contatore interno | Budget al 80% e 100% |

### Metriche di simulazione

| Metrica | Dove | Uso |
|---------|------|-----|
| Agenti attivi per tick | Dashboard | Monitorare crescita/declino |
| Decisioni LLM / secondo | Dashboard + log | Performance tuning |
| Rapporto decisioni locali vs API | Dashboard | Ottimizzazione costi |
| Crisi Seldon attive | Dashboard + alert | Notifica utente |
| Coerenza (contraddizioni rilevate) | Log + alert | Qualita simulazione |

### Logging strutturato

- Formato JSON per tutti i log (ELK-ready)
- Ogni decisione LLM loggata nel DecisionLog (input, output, modello, costo, latenza)
- Livelli: DEBUG (ogni decisione), INFO (eventi significativi), WARNING (fallback, anomalie), ERROR (errori recuperati), CRITICAL (simulazione bloccata)

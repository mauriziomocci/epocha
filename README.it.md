[English](README.md) | Italiano

# Epocha

[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/)
[![Status](https://img.shields.io/badge/status-MVP%20in%20development-yellow.svg)]()
[![Django](https://img.shields.io/badge/django-5.x-green.svg)](https://www.djangoproject.com/)

**Un simulatore di civilta basato sull'intelligenza artificiale. Osserva societa che nascono, evolvono, collassano e rinascono.**

---

## Panoramica

Epocha e un approccio computazionale alla psicostoria -- la disciplina immaginaria della saga di Foundation di Asimov che prevede il comportamento delle civilta attraverso la modellazione matematica delle dinamiche di massa. Dove Hari Seldon usava equazioni, Epocha usa agenti AI.

Centinaia di agenti autonomi -- ciascuno con una personalita distinta, una memoria, paure, ambizioni e relazioni sociali -- vivono all'interno di un mondo simulato dotato di un'economia funzionante, sistemi politici, vincoli geografici e tutta la complessita disordinata della societa umana. Le crisi emergono dal basso. Le alleanze si formano e si frantumano. Le rivoluzioni tecnologiche ridisegnano l'ordine sociale. Eta oscure seguono eta dell'oro. Un singolo individuo carismatico puo alterare la traiettoria di un'intera civilta.

La simulazione puo coprire archi temporali che vanno da un singolo villaggio nel suo primo decennio a una civilta interstellare distribuita su sistemi stellari nell'arco di millenni. A ogni scala, lo stesso motore e in funzione: agenti che prendono decisioni, gruppi che si aggregano e si frammentano, societa che sorgono e cadono.

L'utente non e un osservatore passivo. A seconda della modalita di interazione scelta, e possibile osservare la simulazione da lontano, entrarvi come abitante, iniettare eventi e personaggi come una presenza divina, o guidare la storia dall'ombra come la Seconda Fondazione di Asimov -- indirizzando le civilta verso la stabilita senza rivelare la propria presenza.

---

## Funzionalita principali

### Agenti

- **Modello di personalita Big Five** -- Ogni agente e definito da apertura, coscienziosita, estroversione, amicalita e nevroticismo. Questi tratti non sono cosmetici: guidano ogni decisione presa dall'agente.
- **Memoria realistica con peso emotivo** -- I ricordi recenti sono vividi. Gli eventi traumatici persistono per tutta la vita. I ricordi ordinari sbiadiscono e si distorcono nel tempo. Le informazioni di seconda mano sono meno affidabili dell'esperienza diretta.
- **Ciclo di vita completo** -- Gli agenti invecchiano, si ammalano, si innamorano, formano famiglie, accumulano ricchezza o debiti e muoiono. I figli ereditano tratti culturali e genetici con variazioni. Lo status economico e sociale si trasmette tra le generazioni.
- **Aggregazione dinamica** -- Gli individui si coalizzano in gruppi quando condividono valori e obiettivi. I gruppi si frammentano quando la tensione interna supera una soglia. I leader emergono dalla folla e possono essere seguiti individualmente. La gerarchia scala dalla famiglia alla fazione, dalla nazione alla civilta, fino alla federazione interstellare.

### Simulazione del mondo

- **Multi-scala dal villaggio alla galassia** -- La stessa architettura gestisce un borgo medievale e una federazione galattica. La simulazione scala senza discontinuita dalle decisioni individuali alla diplomazia interstellare.
- **Fondamento geografico** -- Il mondo e costruito su un modello spaziale (PostGIS). Gli agenti hanno posizioni reali. Gli eventi si propagano attraverso la geografia. La prossimita determina l'interazione sociale. Epidemie, rivolte e disastri hanno epicentri e si diffondono nello spazio.
- **Economia a complessita configurabile** -- Da un semplice indice di benessere a mercati completi basati su domanda e offerta con inflazione, disoccupazione, struttura di classe, debito e commercio tra regioni.
- **Sistemi politici** -- Elezioni, colpi di stato, rivoluzioni e il lento decadimento delle istituzioni. I governi rispondono alla fiducia pubblica, alla pressione sulle risorse e alle ambizioni degli agenti piu potenti.
- **Entropia e decadimento** -- Le infrastrutture si degradano senza manutenzione. La conoscenza si perde tra le generazioni. Le istituzioni si corrompono. Le civilta che si espandono piu velocemente di quanto possano sostenersi collassano. Le eta oscure sono seguite da rinascimenti.

### Modelli scientifici

Epocha adotta un approccio ibrido: i modelli matematici gestiscono le tendenze macroscopiche, mentre gli agenti forniscono realismo comportamentale. Nessuno dei due, da solo, e sufficiente.

I modelli sono calibrati su dati storici reali prima dell'avvio della simulazione. Se una simulazione inizia nell'Europa del XII secolo, i parametri demografici, economici e climatici riflettono le condizioni effettive di quel periodo.

I domini scientifici supportati includono macroeconomia (curva di Phillips, IS-LM, equazione di Fisher), disuguaglianza (coefficiente di Gini, curva di Lorenz), epidemiologia (modelli SIR/SEIR), clima (bilancio radiativo, cicli di retroazione), dinamiche delle reti sociali (Granovetter, cascate informative), conflitti militari (attrito di Lanchester), esaurimento delle risorse (curva di Hubbert) e -- quando la simulazione raggiunge la scala spaziale -- meccanica orbitale (Kepler, Tsiolkovsky, trasferimenti di Hohmann), equazione di Drake e modelli di abitabilita degli esopianeti.

Il rigore scientifico e configurabile: semplificato (regole qualitative), standard (modelli matematici calibrati) o rigoroso (equazioni complete da articoli peer-reviewed con validazione incrociata).

### Motore della conoscenza

Prima dell'avvio di una simulazione, il Motore della conoscenza costruisce una base di conoscenza strutturata ricercando i domini pertinenti -- storia, scienza, economia, sociologia, scienze politiche, clima e altro. Questa viene memorizzata come un grafo delle dipendenze: ogni scoperta o innovazione ha prerequisiti, condizioni abilitanti, probabilita di emergenza, catalizzatori e conseguenze a valle.

Durante la simulazione, il motore valuta quali scoperte sono "mature" dato lo stato attuale della civilta, calcola le probabilita di emergenza e innesca innovazioni attraverso agenti credibili quando le condizioni sono soddisfatte.

Per le simulazioni di proiezione futura che partono dal giorno presente, il motore ricerca lo stato geopolitico, economico, demografico e tecnologico attuale del mondo e applica un framework di plausibilita: estrapolazione a breve termine dalle tendenze reali, scenari ramificati a medio termine, conseguenze emergenti a lungo termine.

Il motore si connette a fonti esterne tra cui Wikipedia, arXiv, dati della Banca Mondiale, proiezioni climatiche dell'IPCC e il NASA Exoplanet Archive.

### Modalita di interazione

| Modalita | Identita | Effetto sulla simulazione |
|----------|----------|---------------------------|
| Osservatore | Intervistatore invisibile | Le conversazioni non alterano il mondo |
| Abitante | Un personaggio che vive nel mondo | Le tue azioni hanno conseguenze reali |
| Dio | Un'entita superiore | Puoi impartire comandi, modificare regole, innescare eventi |
| Seconda Fondazione | Una guida invisibile | Influenzi la storia dietro le quinte |

### Chat in tempo reale via WebSocket

Fai clic su qualsiasi agente sulla mappa per aprire una conversazione diretta. L'agente risponde restando nel personaggio -- coerente con la sua personalita, stato emotivo, ricordi e circostanze attuali. Parla con gruppi riuniti in una localita e osserva le dinamiche sociali svolgersi in tempo reale.

In modalita Dio, gli agenti reagiscono alla tua presenza secondo la loro natura: un ribelle ti sfida, un seguace devoto obbedisce senza esitazione, un razionalista mette in discussione la tua esistenza.

### Dashboard psicostorica

Il livello analitico fa emergere schemi che attraversano le generazioni:

- **Crisi di Seldon** -- Il sistema rileva e nomina i punti di svolta delle civilta mentre si sviluppano, tracciandone le cause, gli esiti probabili e gli agenti chiave che li guidano.
- **Scala di Kardashev** -- Traccia la padronanza energetica e la portata tecnologica della civilta nel tempo.
- **Cicli storici** -- Rileva schemi ricorrenti: impennate della disuguaglianza che precedono rivolte, espansione seguita da sovra-estensione e collasso, eta dell'oro culturali che seguono periodi di crisi.
- **Confronto tra rami** -- Esegui due versioni della stessa civilta con variabili diverse e sovrapponi le loro traiettorie. Osserva cosa e cambiato e quando la divergenza e diventata irreversibile.

### Enciclopedia galattica

La simulazione mantiene un registro storico completo di tutto cio che accade: ogni scoperta, crisi, transizione politica, guerra e movimento culturale -- con cause, agenti coinvolti e conseguenze. Interroga questo registro in linguaggio naturale: "Quali furono le principali cause del collasso del 2087?" o "Chi furono gli individui piu influenti del terzo secolo?"

### Simulazioni ramificate

Crea un fork di qualsiasi simulazione in qualsiasi momento. Il fork genera un mondo indipendente che condivide la storia fino a quel punto. Da li, inietta una variabile diversa -- un dittatore, una pestilenza, una svolta tecnologica -- e confronta come le due linee temporali divergono. Fork multipli dalla stessa origine consentono esperimenti controllati a scala di civilta.

### Modalita Express

Un singolo campo di testo. Digita un prompt e ottieni un mondo.

```
"Simula l'Italia dal 2026 al 2126, concentrandoti sull'impatto dell'AI sul mercato del lavoro."

"Una societa medievale con due villaggi rivali sulle sponde opposte di un fiume, risorse
scarse e tensione religiosa tra un culto solare e un culto lunare."

"Cosa sarebbe successo se l'Impero Romano non fosse caduto nel 476?"
```

Il sistema analizza l'input, costruisce la base di conoscenza, genera il mondo, seleziona i parametri ottimali e avvia la simulazione. Nessuna configurazione necessaria. La modalita Express utilizza lo stesso motore della modalita avanzata -- il sistema prende tutte le decisioni di configurazione al posto tuo.

### Input multi-formato

L'endpoint Express accetta:

| Formato | Come funziona |
|---------|---------------|
| Testo semplice | Descrizione diretta nella richiesta API |
| Markdown (.md) | La struttura viene preservata come contesto di costruzione del mondo |
| PDF (.pdf) | Testo estratto e analizzato (libri di storia, articoli accademici, notizie) |
| Testo semplice (.txt) | Letto cosi com'e |
| URL | Il contenuto della pagina viene recuperato ed estratto |

Un prompt opzionale a corredo di qualsiasi file o URL permette di aggiungere istruzioni: "Concentrati sulle dinamiche economiche", "Simula per 500 anni", "Aggiungi un leader rivoluzionario dopo 50 anni."

### Server MCP

Epocha espone un server Model Context Protocol. Qualsiasi client compatibile con MCP puo controllare e osservare le simulazioni senza aprire l'interfaccia web.

Gli strumenti MCP supportati includono: creazione di simulazioni, controllo della riproduzione, chat con gli agenti, iniezione di personaggi o eventi, modifica delle regole del mondo, creazione di fork, confronto di linee temporali, interrogazione dell'enciclopedia, lettura delle analitiche e del feed delle Crisi di Seldon, ed esportazione dei dati della simulazione.

I client compatibili includono Claude Code, Cursor, Windsurf e qualsiasi client MCP personalizzato. Piu client possono essere connessi simultaneamente -- multiplayer via MCP.

### Architettura a plugin

Ogni modello scientifico e modulo di simulazione e un plugin con un'interfaccia standard. I contributori non hanno bisogno di conoscere Django o l'architettura interna. Un sociologo puo fornire equazioni, dati di calibrazione e parametri nel formato standard e il sistema li integra automaticamente.

Ogni contributo sotto forma di plugin attraversa una pipeline a quattro fasi: validazione tecnica automatizzata (test, linting, conformita dell'interfaccia), validazione scientifica automatizzata (correttezza delle equazioni, intervalli dei parametri, calibrazione su dati storici), validazione di integrazione (nessuna regressione, output di simulazione plausibile) e revisione umana da parte dei maintainer e degli esperti di dominio.

### Mondi collaborativi e multiplayer

Piu utenti possono partecipare alla stessa simulazione con ruoli diversi: creatore (controllo completo), co-sperimentatore (inietta eventi e personaggi, crea fork, osserva), osservatore (accesso in sola lettura e chat con gli agenti), abitante (vive nel mondo come personaggio) o dio locale (controlla una regione o civilta specifica).

Sono supportate la collaborazione asincrona (fork e confronto), i mondi condivisi sincroni e il multiplayer competitivo (ogni utente controlla una civilta diversa nello stesso mondo).

### Riproducibilita

Ogni simulazione e riproducibile. Il sistema garantisce riproducibilita statistica (stessi parametri, esiti macro statisticamente simili) e capacita di replay completo (riproduzione esatta dal log degli eventi). Le simulazioni possono essere esportate come pacchetto portabile e condivise con parametri esatti affinche altri ricercatori possano replicarle o estenderle.

---

## Casi d'uso

**Scenari storici "e se"** -- Crea un fork della storia in un momento specifico e inietta una variabile diversa. Cosa sarebbe successo se la Biblioteca di Alessandria fosse sopravvissuta? Se la Peste Nera fosse stata due volte piu letale? Se l'Impero Romano avesse scoperto la stampa prima del collasso? La simulazione sviluppa le conseguenze nel corso dei secoli con rigore scientifico.

**Proiezione futura** -- Parti dal 2026 e simula fino al 2126 o al 3026. Il Motore della conoscenza ancora i primi decenni ai dati reali del mondo attuale e alle estrapolazioni delle tendenze, poi segue le conseguenze emergenti ovunque la simulazione conduca. Osserva i futuri plausibili della disruzione dell'AI, della pressione climatica, delle transizioni energetiche e dei cambiamenti demografici attraverso le vite dei singoli agenti.

**Esperimenti sociali** -- Inietta un autoritario carismatico in una democrazia stabile e osserva il percorso pluridecennale verso l'autocrazia. Innesca un'epidemia e osserva le fratture sociali che rivela. Introduci un movimento filosofico radicale e traccia come si propaga attraverso la rete informativa. Quantifica come singoli individui alterano le traiettorie delle civilta.

**Istruzione** -- Uno studente puo sperimentare le dinamiche della Rivoluzione Francese dall'interno anziche leggerle su un libro. I docenti di sociologia possono dimostrare i cicli di retroazione della disuguaglianza in tempo reale. I corsi di economia possono osservare le dinamiche di domanda e offerta, l'inflazione e le crisi finanziarie emergere dal comportamento dei singoli agenti senza bisogno di un manuale.

**Costruzione di mondi per narrativa e giochi** -- Genera una storia del mondo ricca e internamente coerente con un singolo prompt. L'Enciclopedia galattica fornisce un registro interrogabile di tutto cio che e accaduto, pronto per arricchire romanzi, campagne da tavolo o narrative di gioco con un lore coerente.

**Ricerca nelle scienze sociali** -- Esegui esperimenti controllati a scala di civilta. Mantieni tutte le variabili costanti tranne una. Esegui cento fork paralleli. Aggrega i risultati. Gli esperimenti in crowdsourcing (stesso mondo di partenza, interventi diversi, confronto statistico degli esiti tra tutti i partecipanti) abilitano una forma di scienza sociale comunitaria altrimenti impossibile.

---

## Architettura

Epocha e un'applicazione Django modulare progettata per essere suddivisa in servizi indipendenti quando la scala lo richiede.

```
+---------------------------------------------------------+
|                    FRONTEND (React)                      |
|  +----------+ +----------+ +----------+ +------------+  |
|  | 2D Map   | |   Chat   | |  Graph   | |  Analytics |  |
|  | (Pixi.js)| |  Panel   | |(Sigma.js)| |  Dashboard |  |
|  +----------+ +----------+ +----------+ +------------+  |
|                      WebSocket + REST                    |
+--------------------------+------------------------------+
                           |
+--------------------------+------------------------------+
|              DJANGO / DRF (Orchestrator)                 |
|                                                          |
|  +--------------+  +--------------+  +--------------+   |
|  |  Simulation  |  |    Agents    |  |    World     |   |
|  |    Engine    |  |    Module    |  |    Module    |   |
|  |              |  |              |  |              |   |
|  | - Tick loop  |  | - Personality|  | - Economy    |   |
|  | - Time       |  | - Memory     |  | - Resources  |   |
|  | - Branching  |  | - Decisions  |  | - Politics   |   |
|  | - Auto-stop  |  | - Aggregation|  | - Geography  |   |
|  +--------------+  +--------------+  +--------------+   |
|                          |                               |
|  +-----------------------------------------------+      |
|  |              Event Bus (internal)              |      |
|  +------------------------+----------------------+      |
|                           |                              |
|  +--------+ +--------+ +--------+ +--------+ +--------+ |
|  |  Chat  | | Info   | |Analyti-| |Knowled-| |Scienti-| |
|  | Module | | Flow   | |  cs    | |ge Eng. | |fic Mod.| |
|  |        | |        | |        | |        | |        | |
|  | -1-a-1 | |-Rumor  | |-Trends | |-Research| |-Equat. | |
|  | -Groups| |-Media  | |-Cycles | |-K.Graph| |-Papers | |
|  | -Modes | |-Distort| |-Compare| |-Validate|-Calibr. | |
|  +--------+ +--------+ +--------+ +--------+ +--------+ |
+--------------------------+------------------------------+
                           |
            +--------------+--------------+
            |              |              |
       +----+----+   +----+----+   +-----+-----+
       | Celery  |   |  Redis  |   | PostgreSQL |
       | Workers |   |         |   |            |
       |         |   | - State |   | - Agents   |
       | - Agent |   | - Cache |   | - History  |
       |   AI    |   | - PubSub|   | - Branches |
       | - Tick  |   |         |   | - Analytics|
       |   proc. |   |         |   |            |
       +----+----+   +---------+   +------------+
            |
       +----+------------------------+
       |   LLM Adapter Layer         |
       |                             |
       | +-------+ +-------+        |
       | | Local | |  API  | ...    |
       | | vLLM  | |Gemini |        |
       | +-------+ +-------+        |
       |                             |
       | - Rate limiting             |
       | - Quota management          |
       | - Fallback chain            |
       | - Cost tracking             |
       +-----------------------------+
```

### Stack tecnologico

| Componente | Tecnologia | Scopo |
|------------|-----------|-------|
| Backend | Django 5.x + Django REST Framework | Applicazione principale e API REST |
| Task asincroni | Celery + Redis (broker) | Elaborazione parallela degli agenti, ciclo di tick |
| Database | PostgreSQL (futuro: + PostGIS + pgvector) | Dati degli agenti, storia, rami, base di conoscenza |
| Cache / Tempo reale | Redis | Stato della simulazione, pub/sub per WebSocket |
| WebSocket | Django Channels + Daphne | Aggiornamenti in tempo reale e chat con gli agenti |
| Frontend | React | Interfaccia utente interattiva |
| Mappa 2D | Pixi.js (WebGL) | Rendering ad alte prestazioni degli sprite |
| Grafo delle relazioni | Sigma.js (WebGL) | Visualizzazione di grafi sociali di grandi dimensioni |
| Grafici | Recharts | Dashboard analitica |
| Gestione dello stato | Zustand | Stato frontend leggero |
| LLM | Adapter indipendente dal provider | Qualsiasi API compatibile con OpenAI |
| Integrazione | Model Context Protocol | Server e client MCP per fonti esterne |

---

## Avvio rapido

### Prerequisiti

- Docker e Docker Compose

### Configurazione

**1. Clona il repository**

```bash
git clone https://github.com/mauriziomocci/epocha.git
cd epocha
```

**2. Configura le variabili d'ambiente**

```bash
cp .env.example .envs/.local/.django
cp .env.postgres.example .envs/.local/.postgres
```

Modifica `.envs/.local/.django` e imposta la tua chiave API per il LLM. La configurazione predefinita utilizza Google Gemini, che dispone di un piano gratuito con 1.000 richieste al giorno -- sufficiente per lo sviluppo e il testing.

```
EPOCHA_LLM_PROVIDER=openai
EPOCHA_LLM_API_KEY=your-gemini-api-key-here
EPOCHA_LLM_MODEL=gemini-2.5-flash-lite
EPOCHA_LLM_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/
```

**3. Avvia lo stack**

```bash
docker compose -f docker-compose.local.yml up --build
```

Questo avvia Django (porta 8000), PostgreSQL, Redis, un worker Celery e Celery Beat.

**4. Inizializza il database**

```bash
docker compose -f docker-compose.local.yml exec web python manage.py migrate
docker compose -f docker-compose.local.yml exec web python manage.py createsuperuser
```

**5. Crea la tua prima simulazione**

```bash
curl -X POST http://localhost:8000/api/v1/simulations/express/ \
  -H "Authorization: Bearer <your-token>" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "A medieval village with 30 people, two rival families, and a disputed mill"}'
```

**6. Connettiti a un agente via WebSocket**

```
ws://localhost:8000/ws/chat/<agent_id>/
```

---

## Configurazione del provider LLM

Epocha utilizza l'SDK OpenAI con un `base_url` configurabile, rendendolo compatibile con qualsiasi API compatibile con OpenAI senza modifiche al codice. Cambia provider modificando solo le variabili d'ambiente.

| Provider | `EPOCHA_LLM_BASE_URL` | Modello consigliato | Piano gratuito |
|----------|----------------------|---------------------|----------------|
| Google Gemini | `https://generativelanguage.googleapis.com/v1beta/openai/` | `gemini-2.5-flash-lite` | 1.000 req/giorno |
| Groq | `https://api.groq.com/openai/v1` | `llama-3.1-8b-instant` | Limitato |
| OpenRouter | `https://openrouter.ai/api/v1` | Vari modelli gratuiti | 200 req/giorno |
| OpenAI | *(lasciare vuoto)* | `gpt-4o-mini` | Crediti iniziali |
| Together AI | `https://api.together.xyz/v1` | Vari | Crediti iniziali |
| Mistral | `https://api.mistral.ai/v1` | `mistral-small-latest` | No |
| Locale (Ollama) | `http://localhost:11434/v1` | `qwen2.5:7b` | Illimitato |

**Ottieni una chiave API Gemini gratuita:** [aistudio.google.com/apikey](https://aistudio.google.com/apikey)

### Stima della capacita con il piano gratuito di Gemini

Con 20 agenti e 1.000 richieste al giorno:
- Generazione del mondo: circa 1 richiesta
- Per tick di simulazione: circa 20 richieste (una per agente)
- Circa 50 tick al giorno entro i limiti gratuiti
- Budget per la chat con gli agenti: circa 100 richieste al giorno

Questo e piu che sufficiente per lo sviluppo e l'esplorazione. Per simulazioni piu lunghe, e possibile passare a un piano a pagamento o utilizzare un provider con limiti piu elevati.

### Routing dei modelli a tre livelli (produzione)

Per simulazioni di grandi dimensioni, l'adapter LLM instrada le richieste in base alla complessita della decisione:

| Livello | Quota delle chiamate | Tipo di decisione | Modelli di esempio |
|---------|---------------------|-------------------|--------------------|
| Locale | ~90% | Azioni di routine, movimento, reazioni semplici | Ollama + Qwen 7B |
| API economica | ~8% | Decisioni sociali, commercio, voto | Gemini Flash-Lite, GPT-4o-mini |
| API premium | ~2% | Crisi, momenti di leadership, punti di svolta storici | Gemini Pro, GPT-4o |

Questo mantiene i costi gestibili per le simulazioni su larga scala, riservando i modelli piu potenti alle decisioni che contano.

---

## Stato del progetto

Epocha e attualmente in fase di sviluppo attivo dell'MVP. Il backend viene costruito e validato per primo; il frontend seguira.

L'MVP include: generazione del mondo da un prompt testuale, 20-50 agenti AI con personalita e memoria, un motore di simulazione basato su tick, chat in tempo reale via WebSocket con qualsiasi agente e un'API REST per tutte le operazioni principali.

Consulta il piano di implementazione completo in [`docs/superpowers/plans/2026-03-23-mvp-implementation.md`](docs/superpowers/plans/2026-03-23-mvp-implementation.md).

---

## Roadmap

| Versione | Ambito | Stato |
|----------|--------|-------|
| v0.1 -- MVP | Motore backend, 20-50 agenti, modalita Express, chat WebSocket, API REST | In sviluppo |
| v0.2 | Mappa frontend (Pixi.js), grafo degli agenti (Sigma.js), dashboard analitica | Pianificato |
| v0.3 | Motore della conoscenza, ricerca web, grafo della conoscenza, calibrazione pre-simulazione | Pianificato |
| v0.4 | Integrazione dei modelli scientifici (economia, epidemiologia, demografia, clima) | Pianificato |
| v0.5 | Ramificazione/fork, confronto tra rami, rilevamento delle Crisi di Seldon | Pianificato |
| v0.6 | Server MCP, esposizione degli strumenti, supporto per client esterni | Pianificato |
| v0.7 | Architettura a plugin, pipeline di contribuzione, automazione della validazione | Pianificato |
| v0.8 | Mondi multiplayer, simulazione collaborativa, sistema di permessi | Pianificato |
| v0.9 | Scala spaziale, meccanica orbitale, espansione interstellare | Pianificato |
| v1.0 | Visione completa: tutte le modalita di interazione, Enciclopedia galattica, funzionalita per la comunita | Pianificato |

Il documento di progettazione in [`docs/superpowers/specs/2026-03-22-epocha-design.md`](docs/superpowers/specs/2026-03-22-epocha-design.md) descrive la visione completa della v1.0 in dettaglio.

---

## Contribuire

Epocha e open source e progettato per essere esteso. I contributi sono benvenuti da parte di sviluppatori, scienziati, storici, economisti, sociologi e chiunque possieda competenze di dominio pertinenti al funzionamento effettivo delle civilta.

### Per iniziare

```bash
# Installa le dipendenze di sviluppo
pip install -r requirements/local.txt

# Esegui la suite di test
pytest --cov=epocha -v

# Qualita del codice
ruff check .
ruff format --check .
```

### Contributi tramite plugin

Il sistema di plugin e il principale punto di estensione. Un plugin e un modulo autonomo con un'interfaccia standard:

```
plugin-name/
+-- metadata.json          # nome, autore, versione, dominio, dipendenze
+-- model.py               # implementazione (interfaccia Python standard)
+-- parameters.json        # parametri predefiniti, intervalli validi, unita
+-- calibration_data/      # dati storici per calibrazione e validazione
+-- tests/                 # test unitari e di integrazione
+-- README.md              # documentazione, equazioni, fonti
+-- references.bib         # bibliografia scientifica
+-- examples/              # esempi d'uso e output atteso
```

Non e necessario comprendere l'architettura interna per scrivere un plugin. Uno storico puo contribuire un template storico calibrato. Un epidemiologo puo contribuire un modello SIR migliorato con parametri da ricerche pubblicate. Un economista puo contribuire un modello di iperinflazione fondato su casi storici documentati.

### Pipeline di contribuzione

Ogni pull request attraversa automaticamente quattro fasi:

1. **Validazione tecnica** -- I test passano, l'interfaccia del plugin e rispettata, nessuna regressione, linting superato.
2. **Validazione scientifica** -- Le equazioni sono dimensionalmente coerenti, gli articoli citati esistono e sono pertinenti, i parametri rientrano in intervalli realistici, il modello riproduce i dati di calibrazione storica.
3. **Validazione di integrazione** -- Il plugin non contraddice i moduli esistenti, opera entro limiti accettabili, produce output di simulazione plausibile end-to-end.
4. **Revisione umana** -- I maintainer e gli esperti di dominio esaminano il rapporto automatizzato, discutono pubblicamente sulla pull request e approvano o richiedono modifiche.

### Convenzioni per branch e commit

- Nomi dei branch: `feature/<short-description>`, `fix/<short-description>`, `refactor/<short-description>`
- Branch di base per funzionalita e correzioni: `develop`
- Stile dei commit: [Conventional Commits](https://www.conventionalcommits.org/) -- `feat(agents): add memory decay with emotional weight`
- Lunghezza della riga: 120 caratteri, virgolette doppie, PEP 8

---

## Fonti di ispirazione

**Isaac Asimov -- serie Foundation.** Il concetto di psicostoria: una scienza matematica che prevede il comportamento di grandi popolazioni con alta precisione, anche se il comportamento individuale e imprevedibile. Epocha e un'implementazione computazionale di quell'idea -- non con sole equazioni, ma con agenti il cui comportamento collettivo emergente diventa prevedibile su larga scala.

**Sid Meier's Civilization.** L'intuizione che le dinamiche storiche complesse possono essere modellate in una forma interattiva e giocabile. Epocha prende la stessa tesi sul serio e tenta di sostituire le meccaniche di gioco astratte con una simulazione scientificamente fondata.

**MiroFish.** Una dimostrazione iniziale che la simulazione sociale basata su agenti con LLM puo produrre comportamenti emergenti genuinamente interessanti. Epocha estende quella premessa con modelli scientifici, aggregazione multi-scala e un livello strutturato di conoscenza.

**Giambattista Vico** -- La teoria dei cicli storici: le societa si muovono attraverso fasi ricorrenti di crescita, consolidamento e declino (corsi e ricorsi). Questi cicli sono una caratteristica strutturale della simulazione di Epocha, non uno script forzato.

**Ibn Khaldun** -- Il sociologo del XIV secolo che descrisse come le civilta sorgono attraverso la coesione sociale (asabiyyah) e cadono a causa della sua erosione. Le dinamiche che identifico -- eccesso delle elite, calcificazione burocratica, perdita di legittimita -- sono modellate esplicitamente nei sistemi politici e istituzionali di Epocha.

**Polybius** -- Lo storico greco che descrisse l'anaciclosi: la progressione e degenerazione naturale dei sistemi politici. Il modulo politico di Epocha si ispira a questo modello di ciclo istituzionale.

---

## Licenza

Apache License 2.0. Consulta [LICENSE](LICENSE) per il testo completo.

---

## Link

- **Repository:** [github.com/mauriziomocci/epocha](https://github.com/mauriziomocci/epocha)
- **Specifica di progettazione:** [`docs/superpowers/specs/2026-03-22-epocha-design.md`](docs/superpowers/specs/2026-03-22-epocha-design.md)
- **Piano di implementazione MVP:** [`docs/superpowers/plans/2026-03-23-mvp-implementation.md`](docs/superpowers/plans/2026-03-23-mvp-implementation.md)

# Feature Specification: Deprecazione del modulo legacy world/economy.py

**Feature Branch**: `20260715-094457-world-economy-deprecation`

**Created**: 2026-07-15

**Status**: Draft

**Input**: User description: "Deprecate the legacy MVP economy placeholder module epocha/apps/world/economy.py. The module is superseded by the audited epocha/apps/economy package (CONVERGED 2026-04-15, whitepaper §4.2) but is still a live fallback in simulation/engine.py when a simulation has no Currency data. Add a deprecation marker (docstring block + warnings.warn DeprecationWarning) documenting the remaining callers, keep the fallback behavior unchanged, verify whitepaper §8 does not reference the legacy module, and close the F-CAMPAIGN audit re-pass campaign (branch 6 of 6) updating campaign tracking memory."

## Contesto e problema

Il modulo `epocha/apps/world/economy.py` è il placeholder economico dell'MVP: reddito per ruolo, costo della vita fisso, effetto della ricchezza sull'umore con sazietà alla Kahneman & Deaton (2010). È superato dal package `epocha/apps/economy/*`, auditato CONVERGED il 2026-04-15 e documentato nel whitepaper §4.2.

Il modulo NON è però codice morto. La verifica sui sorgenti (2026-07-15) trova due caller di produzione e uno di test:

1. `epocha/apps/simulation/engine.py:38` — import a livello modulo di `process_economy_tick`.
2. `epocha/apps/simulation/engine.py` funzione `run_economy` (riga ~372) e loop `SimulationEngine` (riga ~463) — fallback runtime: quando la simulazione non ha oggetti `Currency` (economia nuova non inizializzata), il tick economico usa il modulo legacy.
3. `epocha/apps/simulation/tasks.py:46` — percorso di produzione Celery: il task invoca `run_economy(simulation)`, che raggiunge il fallback legacy quando manca `Currency`.
4. `epocha/apps/world/tests/test_economy.py:8` — test unitari del modulo legacy.

Rimuovere il file (path A del piano F-CAMPAIGN) cambierebbe il comportamento delle simulazioni senza dati economici. La scelta corretta è il path B documentato nel piano campagna: marker di deprecazione, comportamento invariato, rimozione fisica rimandata a un work item dedicato alla migrazione dei caller.

Questo work item è il Branch 6 di 6 della campagna F-CAMPAIGN (re-audit batch 2026-04-12) e la chiude. La chiusura della campagna NON estingue l'intero debito di re-audit: restano fuori scope campagna i moduli §8.1 Knowledge Graph e §8.2 Economy base layer, il cui Round 2 resta tracciato dalla memoria `project_audit_repass_batch_2026_04_12_pending`.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Sviluppatore avvisato della deprecazione (Priority: P1)

Uno sviluppatore (o una sessione agente futura) che importa o estende `epocha.apps.world.economy` deve ricevere un segnale esplicito e immediato che il modulo è legacy, quale package lo sostituisce e quali caller restano da migrare.

**Why this priority**: è l'intero valore del work item — impedire che nuovo codice si appoggi al placeholder non auditato invece che al package economy auditato.

**Independent Test**: importare il modulo in un interprete pulito e osservare il `DeprecationWarning`; leggere il docstring e trovare il riferimento al sostituto e l'elenco dei caller residui.

**Acceptance Scenarios**:

1. **Given** un processo Python pulito, **When** `epocha.apps.world.economy` viene importato per la prima volta, **Then** viene emesso un `DeprecationWarning` che nomina il modulo deprecato e il sostituto `epocha.apps.economy`.
2. **Given** il file sorgente del modulo, **When** uno sviluppatore lo apre, **Then** il docstring dichiara lo stato DEPRECATED, cita il sostituto (CONVERGED 2026-04-15, whitepaper §4.2) ed elenca i caller residui verificati con percorso file.

### User Story 2 - Comportamento runtime invariato (Priority: P1)

Un operatore che esegue una simulazione senza dati economici inizializzati (nessuna `Currency`) deve ottenere esattamente lo stesso comportamento di prima: il fallback legacy processa il tick economico.

**Why this priority**: la deprecazione è solo segnaletica; una regressione comportamentale violerebbe il vincolo esplicito "keep the fallback behavior unchanged".

**Independent Test**: suite di test esistente (`epocha/apps/world/tests/test_economy.py` e test dell'engine di simulazione) verde senza modifiche di asserzioni.

**Acceptance Scenarios**:

1. **Given** la suite pytest completa (baseline 809 test), **When** eseguita dopo la modifica, **Then** zero test falliti e zero test rimossi o indeboliti.
2. **Given** una simulazione senza `Currency`, **When** gira un tick economico, **Then** il fallback legacy viene eseguito con la stessa logica di prima (reddito, costo vita, umore, stabilità).

### User Story 3 - Campagna F-CAMPAIGN chiusa e tracciamento onesto (Priority: P2)

Chi consulta la memoria di progetto e il whitepaper deve trovare uno stato coerente: campagna 6/6 chiusa, retrospettiva scritta, debito residuo (§8.1 Knowledge Graph, §8.2 Economy base layer) ancora tracciato e non dichiarato falsamente estinto.

**Why this priority**: il whitepaper cita la memoria `project_audit_repass_batch_2026_04_12_pending` come tracker del residuo §8 in §10 Discussion, §11 Known Limitations e §12 Conclusions; marcarla "DONE" senza qualificazione renderebbe stali quei riferimenti. Necessario ma successivo al codice.

**Independent Test**: leggere memoria aggiornata, retrospettiva e le sezioni §8, §9 e §11 del whitepaper (EN e IT) e verificarne la coerenza incrociata.

**Acceptance Scenarios**:

1. **Given** la memoria `project_audit_repass_batch_2026_04_12_pending`, **When** il branch è chiuso, **Then** dichiara la campagna 6/6 completata con data e afferma che il file traccia ora solo il residuo §8.1/§8.2.
2. **Given** il whitepaper (EN e IT), **When** il branch è chiuso, **Then** ogni occorrenza del conteggio dei moduli §8 pendenti (inventario in FR-007: §8 intro, §9 intro, §11 intro, §11 corpo EN) dice due (Knowledge Graph, economy base layer) e include factions tra i convergiti, con EN e IT speculari.
3. **Given** la retrospettiva di campagna richiesta dal piano F-CAMPAIGN, **When** il branch è chiuso, **Then** esiste `docs/memory-backup/project_audit_repass_2026_04_12_completed.md` con branch, PR, merge SHA e lezioni apprese.

### Edge Cases

- Il warning a livello modulo scatta una sola volta per processo (caching import di Python): il test di regressione deve forzare un re-import (`importlib.reload`) dentro `pytest.warns` per essere deterministico.
- `DeprecationWarning` è silenziato di default dai filtri Python fuori da `__main__`: accettato — il pubblico è lo sviluppatore (pytest e strumenti di lint li mostrano), non il runtime di produzione. Nessun log spam nei worker Celery.
- La config pytest del progetto (`pyproject.toml`) non ha `filterwarnings`: il warning non viene promosso a errore e non rompe la suite.
- `epocha/apps/world/tests/test_generator.py:125` matcha il grep (`world.economy_level`) ma è un falso positivo: campo `economy_level` del modello World, non il modulo legacy.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: il modulo `epocha/apps/world/economy.py` DEVE dichiarare nel docstring di testa lo stato DEPRECATED, il sostituto (`epocha.apps.economy.*`, CONVERGED 2026-04-15, whitepaper §4.2), il divieto di estensione e l'elenco verificato dei caller residui con percorso file, incluso il percorso di produzione Celery che raggiunge il fallback (`simulation/tasks.py:46` → `run_economy` → legacy quando manca `Currency`).
- **FR-002**: il modulo DEVE emettere `warnings.warn(..., DeprecationWarning, stacklevel=2)` al momento dell'import.
- **FR-003**: la logica di `process_economy_tick` NON DEVE cambiare: nessuna modifica a formule, costanti, query o effetti collaterali.
- **FR-004**: un test di regressione DEVE verificare l'emissione del `DeprecationWarning` al re-import del modulo.
- **FR-005**: la suite pytest completa DEVE restare verde (baseline 809), senza rimozione o indebolimento di asserzioni; `ruff check .` e `ruff format --check .` DEVONO restare exit 0.
- **FR-006**: il whitepaper §8 NON DEVE citare `world/economy.py` (verifica: già oggi zero menzioni; il requisito è confermarlo a fine lavoro, nessun edit atteso in §8).
- **FR-007**: TUTTE le occorrenze stale del conteggio dei moduli §8 pendenti nel whitepaper DEVONO essere portate al valore corretto (due: §8.1 Knowledge Graph, §8.2 economy base layer), con factions (§4.7) incluso negli elenchi dei convergiti dove omesso. Inventario verificato 2026-07-15 (audit avversariale Round 1 + verifica diretta): EN `epocha-whitepaper.md` riga 2063 (§8 intro: "three Epocha clusters" e "on those three" nella stessa frase che dice correttamente "remaining two modules"), riga 2081 (§9 intro: "three modules still pending", factions omesso dal parenthetical), riga 2221 (§11 intro: "four §8 modules still pending"), riga 2305 (§11 corpo: "Three modules across"); IT `epocha-whitepaper.it.md` riga 2131 (§8 intro: "i tre cluster" — attenzione all'asimmetria con l'EN: sulla stessa riga IT "restanti due moduli" e "su quei due" sono GIÀ corretti e non vanno toccati, quindi un solo edit contro i due dell'EN 2063), riga 2149 (§9 intro: "sui tre moduli ancora pendenti", factions omesso), riga 2179 (§11 intro: "sui tre moduli rimasti in §8"). Il §11 corpo IT (riga 2218), i punti §9 HIGH PRIORITY e il §10 sono già corretti e NON vanno toccati. EN e IT DEVONO risultare speculari dopo il fix (oggi §11 intro dice "four" in EN e "tre" in IT). AMENDMENT fase 6 (audit avversariale sul codice, 2026-07-15): l'inventario di 7 occorrenze era incompleto perché il pattern di ricerca copriva "modules/moduli" ma non "subsystems/sottosistemi" — l'audit fase 6 ha trovato altre 4 occorrenze stale: abstract EN (righe 34-35, "four subsystems ... (movement, factions, knowledge graph, economy base layer)" più il conteggio "eleven audited"), abstract IT (righe 35-37, "tre sottosistemi ... (fazioni, ...)" più "sei moduli"), §12 Conclusions EN ("three implemented-but-pre-audit subsystems ... covering factions, ..."), §12 Conclusions IT ("tre sottosistemi implementati-ma-pre-audit ... che coprono fazioni, ..."). Tutte corrette nella stessa feature: pending = due, movement e factions spostati tra gli auditati, conteggi numerici fragili dell'abstract sostituiti da forme senza numero. Totale occorrenze corrette: 11.
- **FR-008**: la memoria `project_audit_repass_batch_2026_04_12_pending` DEVE essere riscritta nel corpo (live + `docs/memory-backup/`), non solo rietichettata: la tabella degli 8 moduli del batch (tutti ormai CONVERGED e promossi) viene sostituita da (a) lo stato di chiusura campagna 6/6 con data, PR e merge SHA per branch, e (b) il residuo effettivamente tracciato — §8.1 Knowledge Graph e §8.2 economy base layer, Round 2 pendente — così che i riferimenti del whitepaper (§10, §11, §12) alla memoria restino veri. Il nome file resta invariato proprio perché il whitepaper lo cita testualmente; la memoria stessa DEVE contenere una riga che spiega perché il nome storico è mantenuto benché il contenuto tracci ora il residuo fuori-batch. L'indice `MEMORY.md` DEVE riflettere il nuovo stato.
- **FR-009**: DEVE essere scritta la retrospettiva di campagna `docs/memory-backup/project_audit_repass_2026_04_12_completed.md` (e copia live) come richiesto dalla sezione Closure del piano F-CAMPAIGN: esiti per branch, findings chiusi, lezioni apprese.
- **FR-010**: la memoria di sessione (session resume) DEVE essere aggiornata a fine lavoro: F-CAMPAIGN 6/6, prossimi item (factions Round 3 hardening, Demography Plan 4).

### Key Entities

- **Modulo legacy `world/economy.py`**: placeholder MVP, 113 righe, una funzione pubblica `process_economy_tick(world, tick)`; nessun modello dati proprio.
- **Fallback engine**: ramo `Currency.objects.exists() == False` in `simulation/engine.py` (`run_economy` e loop `SimulationEngine`), unico percorso di produzione che invoca il legacy.
- **Memoria di campagna**: `project_audit_repass_batch_2026_04_12_pending` (tracker), retrospettiva nuova, session resume.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: l'import del modulo legacy in un processo pulito produce esattamente 1 `DeprecationWarning` con messaggio che nomina modulo deprecato e sostituto.
- **SC-002**: suite pytest completa verde (809 baseline, +1 test nuovo), zero xfail, zero skip nuovi senza rationale.
- **SC-003**: `ruff check .` e `ruff format --check .` exit 0.
- **SC-004**: `grep` di `world/economy` su whitepaper EN+IT restituisce zero occorrenze in §8; il conteggio dei moduli §8 pendenti è GLOBALMENTE coerente su tutto il whitepaper (EN e IT speculari): `grep -inE "three modules|tre moduli|four §8|quattro moduli|three Epocha clusters|tre cluster|those three|four subsystems|three implemented|tre sottosistemi|quattro sottosistemi|awaiting Round 2|in attesa dell.audit|pre-audit"` non restituisce più occorrenze riferite al residuo §8, che è ovunque due (i match legittimi residui sono: narrative storiche "pre-audit implementation" in §4.2, nota IF-5, "tre transizioni" demografiche, e le righe corrette che ora dicono due). L'inventario autoritativo delle righe da correggere resta FR-007 (come emendato in fase 6); il grep allargato è il gate automatico anti-fix-parziale — la versione stretta iniziale (solo "modules/moduli") aveva dato un falso verde sull'abstract e sul §12.
- **SC-005**: F-CAMPAIGN dichiarabile 6/6 CHIUSA con PR mergiata e retrospettiva presente; nessun riferimento whitepaper alla memoria tracker reso stale.

## Assumptions

- Path B (marker) e non path A (rimozione): confermato dalla verifica caller — il fallback è vivo. La rimozione fisica del file è un work item futuro, esplicitamente fuori scope, condizionato alla migrazione dei caller (richiede decidere se una simulazione senza `Currency` debba auto-inizializzare l'economia nuova o fallire).
- Nessun aggiornamento README: il modulo legacy non è nominato nei README e la deprecazione non cambia architettura, stack, setup né roadmap pubblica.
- I ritocchi §8/§9/§11 del whitepaper (FR-007) attivano a chiusura la procedura frozen-at-commit pin prevista dalla constitution (fase 7) — sono modifiche documentali, non scientifiche: nessun capitolo Methods toccato, nessuna equazione, nessun parametro.
- Il warning a import time è accettabile per i worker Celery: una emissione per processo, filtrata di default da Python in produzione.
- La regola whitepaper-doc-sync (constitution, Documentation Discipline) non impone edit §4: `world/economy.py` non è un modulo di capitolo 4; la PR lo spiegherà in descrizione.

## FAQ

**Perché deprecare invece di rimuovere, visto che il sostituto è auditato?**
Perché il modulo è un fallback di produzione vivo: `simulation/engine.py` lo invoca quando la simulazione non ha `Currency`. Rimuoverlo ora cambierebbe il comportamento (o romperebbe l'import) per le simulazioni non inizializzate con l'economia nuova. La deprecazione congela il perimetro e rende esplicito il debito; la rimozione è un work item futuro con una decisione di design propria (auto-init dell'economia nuova vs errore esplicito).

**Perché `DeprecationWarning` e non `FutureWarning`, che non viene filtrato di default?**
Il pubblico del segnale è lo sviluppatore che importa o estende il modulo, non l'utente finale della simulazione. `DeprecationWarning` è la categoria semanticamente corretta per API destinate alla rimozione (PEP 565); pytest e i tool di sviluppo la mostrano. `FutureWarning` inonderebbe i log dei worker Celery a ogni avvio senza beneficio.

**Il warning a livello di modulo non scatta anche per il caller legittimo (l'engine)?**
Sì, ed è voluto: l'engine È un caller da migrare, e il warning lo documenta. Costo: una riga di warning per processo worker in ambienti di sviluppo. In produzione i filtri di default di Python lo silenziano.

**Perché toccare il whitepaper se il modulo legacy non vi compare?**
Nessuna sezione lo cita per nome (verificato, zero occorrenze) e il contenuto scientifico resta intatto. Gli edit sono correzioni del conteggio stale dei moduli §8 pendenti, disseminato in 7 punti tra EN e IT (inventario completo in FR-007) dopo le promozioni dei branch 1-5: dove dice "tre" o "four" il residuo reale è due, e factions manca dagli elenchi dei convergiti. L'audit avversariale Round 1 sulla spec ha dimostrato che limitarsi al solo §9 intro (prima formulazione di FR-007) avrebbe lasciato il documento auto-contraddittorio: la regola Exhaustive Bug Analysis impone il censimento e la correzione di tutte le occorrenze, ed è naturale farlo nel branch che chiude la campagna.

**Perché non marcare la memoria di campagna semplicemente "DONE" come dice il piano legacy (Task 6.5)?**
Perché il whitepaper cita `project_audit_repass_batch_2026_04_12_pending` in §10 Discussion, §11 Known Limitations e §12 Conclusions come tracker del Round 2 residuo di Knowledge Graph ed economy base layer, che NON erano nei 6 branch della campagna. Marcare "DONE" senza qualificazione renderebbe falsi quei riferimenti. Il corpo della memoria viene riscritto (FR-008): esito campagna 6/6 con riferimenti per branch, più il residuo §8.1/§8.2 che il file continua a tracciare.

**Come si testa un warning che scatta solo al primo import?**
Con `importlib.reload` del modulo dentro `pytest.warns(DeprecationWarning)`: il reload riesegue il corpo del modulo (solo costanti e definizione di funzione, nessun effetto collaterale) e riemette il warning in modo deterministico, indipendente dall'ordine dei test.

**Impatto su performance, sicurezza, riproducibilità?**
Nullo. Una chiamata `warnings.warn` per processo all'import; nessuna modifica a formule, RNG, query o superficie API. Il determinismo della simulazione è intoccato.

**Cosa resta esplicitamente fuori scope?**
La migrazione dei caller (engine fallback e test legacy), la rimozione fisica del file, il Round 2 di Knowledge Graph (§8.1) ed economy base layer (§8.2), e il factions Round 3 hardening. Tutti tracciati in memoria di progetto.

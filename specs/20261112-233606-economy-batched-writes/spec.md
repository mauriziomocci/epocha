# Feature Specification: scritture per tick lineari nel numero di agenti

**Feature Branch**: `20261112-233606-economy-batched-writes`

**Created**: 2026-11-12

**Status**: Draft, revisione 2 dopo il round 1 dell'audit avversariale; in attesa dell'approvazione dell'utente (gate pesante di fase 2). Verdetto e numeri nella sezione *Stato dell'audit* in fondo.

**Contratto API**: contract unchanged. Nessuna rotta, campo, valore o codice d'errore cambia; il lavoro tocca solo la forma delle istruzioni SQL che scrivono lo stato a ogni tick.

**Input**: decisione della Trinità D-12-E-22 sul difetto misurato D-12-E-18: «le scritture per tick dell'economia devono scalare linearmente negli agenti».

## Il problema misurato

Il 2026-11-12, durante la run di fase 6 SC-006 del ramo `20261029-185654-marital-fertility` (2.000 fondatori, era `pre_industrial_christian`, tick mensili, economia inizializzata da `economy.initialization.initialize_economy`), un tick ha richiesto circa 330 s contro circa 3,3 s a 200 fondatori: il tempo per tick è cresciuto di circa 100 volte per 10 volte gli agenti, quindi in modo quadratico. Il dato è registrato in `specs/20261029-185654-marital-fertility/tasks.md` di quel ramo (T047, correzione del 2026-11-12, righe 133 e 185) e nel nodo `spine2.n14` della build map sul ramo del Plan 4.

La causa misurata è una sola istruzione SQL: `epocha/apps/economy/expectations.py:235` chiama `AgentExpectation.objects.bulk_update(to_update, [5 campi])` senza `batch_size`, e un'istruzione su 10.020 righe e cinque colonne ha impiegato 285 s. Django costruisce `bulk_update` come `UPDATE ... SET col = (CASE WHEN pk = 1 THEN ... WHEN pk = 2 THEN ... END)::tipo, ... WHERE pk IN (...)`, con un ramo `WHEN` per riga e per colonna. L'ho verificato sul sorgente di Django 5.1.15 installato nell'immagine del progetto: `QuerySet.bulk_update` usa `connection.ops.bulk_batch_size(...)` quando `batch_size` manca, `BaseDatabaseOperations.bulk_batch_size` restituisce `len(objs)` e il backend PostgreSQL non lo ridefinisce, quindi tutte le righe finiscono in un'istruzione sola; lo stesso backend dichiara `requires_casted_case_in_updates = True`, quindi ogni `CASE` è avvolto in un cast. PostgreSQL valuta il `CASE` scorrendo i rami in ordine per ciascuna riga aggiornata, quindi un'istruzione su N righe costa un tempo proporzionale a N² per colonna.

Lo stesso schema, su tutte le righe a ogni tick, compare in altri due punti. `epocha/apps/economy/engine.py:898` scrive `wealth` e `mood` di tutti gli agenti vivi con inventario (`engine.py:800-804` salta quelli senza). `epocha/apps/world/stratification.py:192`, in `update_social_classes`, scrive `social_class` di tutti gli agenti vivi: gira a **ogni** tick, perché `process_political_cycle` (`world/government.py:779-797`) non ha alcun controllo d'intervallo ed è chiamata senza condizione da `simulation/engine.py:532`, mentre l'impostazione `EPOCHA_GOVERNMENT_CYCLE_INTERVAL` (`config/settings/base.py:213`) non è letta da nessuna parte nonostante la docstring di `government.py:756`. Questo l'ha trovato l'audit del round 1 e l'ho verificato.

Ricavo da quei numeri un modello di costo, che è una **stima** da un solo punto di misura e che il compito T002 del piano verifica: un'istruzione su B righe costa circa a·B² + c·B + b, con a ≈ 285 s / 10.020² ≈ 2,84 µs per coppia di righe sulle cinque colonne delle aspettative, c un costo lineare per riga e b il costo fisso di un'istruzione, entrambi non misurati. Con lotti di B righe, N righe costano circa N·(a·B + c + b/B): il costo diventa lineare in N, con una costante minima per B* = √(b/a). Con lo stesso modello stimo, a 2.000 fondatori, circa 4,6 s per la scrittura di ricchezza e umore e circa 2,3 s per quella delle classi sociali; a 200 fondatori (circa 1.000 righe di aspettative, stima 10.020/10, perché il template `pre_industrial` ha cinque beni) circa 2,8 s dei 3,3 s del tick andavano nell'istruzione delle aspettative.

**Questa correzione è necessaria ma non basta da sola per SC-006.** Togliendo dai 330 s le tre scritture stimate (285 + 4,6 + 2,3 s) restano circa 38 s per tick a 2.000 fondatori, contro circa 0,4 s a 200: anche il resto del tick cresce circa 100 volte, quindi contiene altri costi superlineari. Il nodo `spine2.n14` ne nomina due, le letture delle relazioni in `generate_mourning_memories` e `_propagate_memory`. È un'inferenza da numeri registrati, non una misura; SC-005 la misura.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Il passo economico scala linearmente (Priority: P1)

Chi lancia una simulazione con qualche migliaio di agenti (la run SC-006 della fertilità coniugale, la prima validazione storica concordata il 2026-10-29) vede il passo economico costare un tempo proporzionale al numero di agenti, non al suo quadrato, e ottiene esattamente gli stessi valori di prima.

**Why this priority**: è circa il 98% del costo stimato delle tre scritture (285 s su circa 292 s); senza, SC-006 richiede circa 33 ore per configurazione.

**Independent Test**: i test di forma di FR-005 sui due siti dell'economia falliscono oggi e passano dopo; lo script di FR-006 misura il passo economico prima e dopo.

**Acceptance Scenarios**:

1. **Given** R righe di aspettative da aggiornare e la dimensione del lotto B, **When** gira `update_agent_expectations`, **Then** l'aggiornamento delle aspettative usa ⌈R/B⌉ istruzioni `UPDATE` e nessuna porta più di B righe.
2. **Given** A agenti vivi con inventario, **When** gira `process_economy_tick_new`, **Then** la scrittura di ricchezza e umore usa ⌈A/B⌉ istruzioni `UPDATE` e nessuna porta più di B righe.
3. **Given** lo stesso mondo costruito con lo stesso seme e lo stesso `simulation.id` sul commit di base e sulla testa, **When** faccio girare il tick di riscaldamento e cinque tick economici, **Then** l'impronta dello stato scritto (FR-006) è identica, purché due run sul commit di base diano la stessa impronta.

### User Story 2 - La stratificazione scala linearmente (Priority: P2)

Lo stesso per la riassegnazione delle classi sociali, che gira a ogni tick su tutti gli agenti vivi.

**Why this priority**: costa circa 2,3 s per tick a 2.000 agenti (stima), lo 0,8% del costo misurato, ma cresce col quadrato degli agenti come le altre due e si corregge con la stessa riga; lasciarla significherebbe lasciare un difetto noto della stessa classe nello stesso tick.

**Independent Test**: il test di forma di FR-005 su `update_social_classes` fallisce oggi e passa dopo.

**Acceptance Scenarios**:

1. **Given** S agenti vivi, **When** gira `update_social_classes`, **Then** la scrittura di `social_class` usa ⌈S/B⌉ istruzioni `UPDATE` e nessuna porta più di B righe, e le memorie di mobilità restano quelle di oggi.

### Edge Cases

- Nessuna riga da aggiornare (primo tick, quando le aspettative si creano con `bulk_create`, o nessun agente vivo): il codice già salta la chiamata (`if to_update:`, `if agents_to_update:`, `if total == 0: return`) e il comportamento non cambia.
- R ≤ B: una sola istruzione, identica a quella di oggi.
- R multiplo esatto di B e R non multiplo di B (l'ultimo lotto più corto): ogni test di forma usa due valori di B, uno per caso, così una dimensione scritta a mano nel codice non passa.
- Errore a metà dei lotti: Django esegue tutti i lotti di un `bulk_update` dentro una sola `transaction.atomic(savepoint=False)` (verificato sul sorgente di Django 5.1.15), quindi o si scrivono tutti o nessuno, come oggi con un'istruzione sola.
- Un valore dell'impostazione minore di 1: è rifiutato al caricamento delle impostazioni (FR-003), così l'errore emerge all'avvio e non a metà di un tick.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: `update_agent_expectations` (`epocha/apps/economy/expectations.py`) passa `batch_size=settings.EPOCHA_BULK_UPDATE_BATCH_SIZE` al suo `bulk_update`. Costo per tick: O(R·B) invece di O(R²), con R = agenti vivi × beni con prezzo.
- **FR-002**: il passo 8b di `process_economy_tick_new` (`epocha/apps/economy/engine.py`) fa lo stesso per ricchezza e umore. Costo per tick: O(A·B) invece di O(A²).
- **FR-003**: B è l'impostazione `EPOCHA_BULK_UPDATE_BATCH_SIZE` in `config/settings/base.py`, letta con `env.int` come le altre impostazioni regolabili del progetto (per esempio `EPOCHA_KG_EMBEDDING_BATCH_SIZE`, riga 240), con un commento che riporta il modello di costo, il rimando alla tabella misurata da cui il valore predefinito è scelto (nel piano, sezione *Measurements*) e la natura del valore: un'euristica d'ingegneria regolabile, non un parametro scientifico; cambiarla cambia il tempo, mai i valori. Un valore minore di 1 solleva `ImproperlyConfigured` al caricamento delle impostazioni. Il valore predefinito è scelto dalla misura dei compiti T002 e T003, mai a mano. Le funzioni la leggono al momento della chiamata, non all'importazione.
- **FR-004**: cambia solo la forma delle istruzioni. I valori scritti, l'insieme di righe scritte a ogni tick, l'ordine delle righe nella lista e l'atomicità della scrittura restano identici. Nessuna lettura, nessun calcolo e nessuna altra scrittura cambia.
- **FR-005**: tre test di guardia sulla **forma** delle istruzioni, non sul tempo, uno per sito: con l'impostazione ridotta tramite la fixture `settings` di pytest-django a due valori (uno che divide le righe, uno che lascia un resto), catturano le query e verificano la lista esatta delle righe per istruzione `UPDATE` della tabella interessata (rami `WHEN` diviso numero di colonne). Oggi falliscono, perché c'è un'istruzione con tutte le righe.
- **FR-006**: uno script di misura `scripts/measure_economy_write_cost.py`, mai raccolto dalla suite (il nome non corrisponde a `test_*.py`), che gira con il database di test in modalità transazionale (`django_db(transaction=True)`, come deciso per gli script di misura nel ramo della fertilità coniugale, D-05-E-14), così ogni scrittura è confermata e una misura non eredita le versioni di riga di quella precedente. Costruisce senza LLM un mondo di N fondatori in due zone con `seed` fisso, inizializza l'economia con `initialize_economy(simulation, template_name="pre_industrial")`, fa girare un tick di riscaldamento (che crea le aspettative) e poi `process_economy_tick_new` per un numero di tick dato. Stampa per ciascun tick il tempo del passo economico, il numero totale di istruzioni `UPDATE`, il numero e la dimensione massima delle istruzioni `CASE` sulle due tabelle, e alla fine `simulation.id`, il seme e l'impronta SHA-256 dello stato scritto (per ogni agente, in ordine di `id` e per posizione: ricchezza, umore; per ogni aspettativa, in ordine di posizione dell'agente e di bene: i cinque campi), con i float scritti con `float.hex`.
- **FR-007**: documentazione nello stesso commit del codice. Il §4.2 dei due whitepaper (EN riga 1162, IT riga 1199 sul commit di base) afferma che le aspettative si scrivono con «due scritture per tick indipendentemente dal numero di agenti», che dopo la modifica è falso: la frase diventa «una `bulk_create` e una `bulk_update` a lotti di `EPOCHA_BULK_UPDATE_BATCH_SIZE` righe, cioè 1 + ⌈R/B⌉ istruzioni». La riga d'importazione aggiunta sposta le citazioni per numero di riga: in ciascun whitepaper `expectations.py:39-40` (quattro volte), `43-80`, `83-107`, `110-251`, `146-159`, `209-211`, `215-226`, ed `economy/engine.py:210-214` e `445-503` (due volte), 26 citazioni in tutto fra EN e IT, elencate per riga nel compito T009; si aggiornano tutte. Le citazioni di `stratification.py` nel §4.5 sono per nome e non si spostano, e la frase del §4.5 «writes the assigned class back to each agent» resta vera. Il modello scientifico non cambia, quindi nessuna equazione, tabella o parametro cambia; il §4.8 non cita righe del motore economico e non si tocca.
- **FR-008**: `update_social_classes` (`epocha/apps/world/stratification.py`) passa `batch_size=settings.EPOCHA_BULK_UPDATE_BATCH_SIZE` al suo `bulk_update`. Costo per tick: O(S·B) invece di O(S²).

### Fuori ambito, con la ragione

- **Il ciclo politico gira a ogni tick** invece che ogni `EPOCHA_GOVERNMENT_CYCLE_INTERVAL` tick. È un difetto a sé: aggiungere il controllo d'intervallo cambia la dinamica politica (istituzioni, corruzione, transizioni, elezioni) di ogni simulazione, quindi è una modifica del modello del §4.5 che richiede la sua spec e il suo audit. Lo registro per il nodo `spine2.n14`.
- `world/economy.py:126`: gira solo per le simulazioni senza `Currency` (`simulation/engine.py:403-411`), cioè mai nella configurazione SC-006; il modulo è deprecato e la sua correzione è la rimozione, già nel nodo `spine2.n14`.
- `world/stratification.py:328` (solo gli agenti al potere, righe 265-283), i `bulk_update` di `demography/` (`migration.py:996`, `1689`, `inheritance.py:2736`, `2743`, `3532`, `3572`) e `world/institutions.py:111`: scrivono sottoinsiemi piccoli per tick, non tutti gli agenti.
- La riscrittura delle classi sociali anche quando non cambiano (nodo `spine2.n14`): scrivere solo le righe cambiate cambierebbe l'insieme di righe scritte, contro FR-004; resta un miglioramento separato.
- Le `save(update_fields=...)` riga per riga del passo economico (`engine.py:285`, `443`, `606`, `645`, `665`, `719`, `759`): sono istruzioni da una riga, lineari in numero; l'audit le stima in 6.000-10.000 per tick a 2.000 agenti, cioè da 3 a 10 s con b fra 0,5 e 1 ms, una parte rilevante del budget di SC-003. Lo script ne stampa il numero per tick; accorparle cambia l'ordine delle scritture fra inventari, quindi se SC-003 fallisce per loro diventano il prossimo work item.
- Il `bulk_create` delle aspettative (`expectations.py:232`): è un `INSERT ... VALUES`, lineare.

### Key Entities

Nessuna entità nuova e nessuna migrazione: `AgentExpectation` e `Agent` restano come sono.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001 (guardia, deterministico)**: i tre test di FR-005 falliscono sul commit di base e passano sulla testa; la suite completa passa senza fallimenti.
- **SC-002 (pendenza, passo economico)**: con lo script di FR-006 sulla stessa macchina e nella stessa sessione, il rapporto fra la mediana del tempo del passo economico a 2.000 e a 200 fondatori, sui tick misurati, è al più 15 sulla testa del ramo. Un costo lineare darebbe 10 (righe × 10); 15 lascia il 50% di margine per i costi fissi del passo. Lo script gira anche sul commit di base a 200 e 2.000 fondatori con 2 tick misurati, per registrare il rapporto di partenza.
- **SC-003 (valore assoluto, passo economico)**: la mediana del tempo del passo economico a 2.000 fondatori è al più 15 s sulla macchina dell'utente (Docker locale). Ragione: il piano della fertilità coniugale fissa 3 ore per configurazione SC-006, cioè 30 s per ciascuno dei 360 tick, e assegno all'economia al più metà di quel tempo.
- **SC-004 (stessi valori)**: l'impronta di FR-006 a 200 fondatori, dopo il tick di riscaldamento e 5 tick misurati, è identica fra commit di base e testa. Il generatore casuale dell'economia è derivato da `simulation.id` e dal seme (`economy/rng.py:31-55`), quindi ogni run gira in un'invocazione nuova di pytest con un database di test creato da zero, e il confronto vale solo se `simulation.id` e il seme coincidono e se due run sul commit di base danno la stessa impronta; altrimenti il criterio è riportato come non giudicabile, con i valori, e non è considerato superato.
- **SC-005 (esito sulla configurazione SC-006, riportato)**: dopo che l'utente decide di incorporare questo ramo in quello della fertilità coniugale, lo script di quel ramo (`scripts/measure_marital_schedule_run.py` con `SC006_FOUNDERS=2000 SC006_TICKS=3`) misura il tempo per tick e un tick profilato con `cProfile` riporta le quindici funzioni più costose. L'obiettivo è al più 30 s per tick (360 tick in 3 ore). La stima di questa spec (circa 38 s di resto più l'economia) dice che probabilmente non lo raggiunge; il risultato si riporta con il suo numero e il profilo apre il work item successivo. SC-005 non blocca la chiusura di questo work item, perché misura codice che questo work item non tocca.

## Assumptions

- La misura di 285 s è rappresentativa: è un solo punto, quindi i compiti T002 e T003 misurano il costo per B prima di scegliere.
- Il driver è psycopg 3 (3.3.3 nell'immagine, `requirements/base.txt`), con il binding lato client predefinito di Django 5.1; lotti più piccoli non avvicinano alcun limite di parametri.
- I test girano su PostgreSQL, come in produzione.

## Decisioni di design

Il design è passato per i tre passi della regola di progetto e per il round 1 dell'audit. Riporto cosa ciascun passo ha eliminato.

**Proposta iniziale.** Un helper condiviso in `epocha/common/db.py` che scrive `UPDATE t SET ... FROM (VALUES ...) AS v WHERE t.id = v.id` con parametri, un'istruzione O(N) per sito; applicato ai due siti misurati, a `update_social_classes` e a `world/economy.py`; un test sull'albero sintattico che vieta ogni `bulk_update` senza `batch_size` nei moduli per tick; un test d'uguaglianza dei valori fra B = 2 e B illimitato.

**Prima revisione critica.**
- Eliminato l'helper con SQL scritto a mano: è un meccanismo nuovo e specifico di PostgreSQL che richiede un cast per tipo di colonna, cioè proprio il punto in cui un valore può cambiare rappresentazione, contro FR-004; Django offre già `batch_size`, e nessuna misura dice ancora che non basti. Resta la strada successiva se SC-003 fallisce per la scrittura stessa (vedi FAQ).
- Eliminato `world/economy.py` dall'ambito: non gira nella configurazione da sbloccare ed è deprecato.
- Eliminata `update_social_classes` dall'ambito, credendola eseguita ogni 10 tick (decisione rovesciata dal round 1, sotto).
- Eliminata l'idea di scrivere solo le righe cambiate per ricchezza e umore: la ricchezza si ricalcola a ogni tick e quasi tutte le righe cambiano, quindi aggiunge un confronto senza togliere righe.

**Seconda revisione e consolidamento.**
- Eliminato il test d'uguaglianza fra B = 2 e B illimitato: entrambe le esecuzioni calcolano i valori in Python prima della scrittura, quindi il test non può fallire per la modifica pianificata. Lo sostituisce SC-004, che confronta il codice di base con quello nuovo da un capo all'altro.
- Eliminato il test sull'albero sintattico: i test di forma coprono i siti, e nessuna prova mostra nuovi `bulk_update` aggiunti senza lotti.
- Corretto il test di guardia: contare solo le istruzioni passerebbe con un'istruzione sola quando le righe del fixture sono al più B; il test riduce B e confronta la lista esatta delle righe per istruzione.
- Diviso il criterio di successo fra passo economico (SC-002, SC-003, giudicati) e tick SC-006 (SC-005, riportato), perché il tick intero dipende da costi fuori ambito.

**Round 1 dell'audit (revisione 2).**
- Eliminata la costante di modulo in `epocha/common/utils.py` importata con `from ... import`: il progetto esprime le grandezze regolabili come impostazioni con override da ambiente (`config/settings/base.py:213`, `:240`); un'impostazione letta al momento della chiamata riusa quel meccanismo, si sostituisce nei test con la fixture `settings` senza la trappola del nome legato all'importazione, ed è condivisa da `economy` e `world` senza dipendenze fra app.
- Riportata dentro l'ambito `update_social_classes` (User Story 2): gira a ogni tick, non ogni 10 (il difetto del ciclo politico resta fuori ambito).
- Dichiarato che la correzione non basta per SC-006 (circa 38 s di resto superlineare, stima) invece di lasciarlo intendere.
- Script di misura in modalità transazionale, seme fisso, `simulation.id` confrontato, griglia di B estesa verso il basso, scelta sui tempi misurati e non sul modello adattato.
- Corretti i numeri non reali (1.002 righe), la popolazione scritta dal passo 8b (solo agenti con inventario) e l'elenco delle citazioni da spostare.

## Alternative considerate

- **`UPDATE ... FROM (VALUES ...)`**: costo O(N) con un'istruzione; rinviata per la ragione della prima revisione.
- **Tabella temporanea e `COPY`**: la più veloce per milioni di righe, ma introduce una tabella di appoggio per tick e un percorso di scrittura nuovo; sproporzionata per 10⁴ righe.
- **Aspettative in un campo JSON per agente**: una riga per agente invece di cinque, ma è una modifica dello schema che trasforma una relazione in un JSON e cambia il modello letto da `economy/context.py`.
- **Costante di modulo in `epocha/common/utils.py`**: la prima scelta, sostituita dall'impostazione per le ragioni del round 1.

## Known Limitations

- Il costo resta proporzionale a B per riga: a 2.000 fondatori stimo da 1 a 3 s per la scrittura delle aspettative, secondo B. Per popolazioni di 10⁵-10⁶ agenti nessuna forma di scrittura riga per riga regge; quella scala richiede lo stato aggregato descritto nella memoria di progetto sulla scalabilità, non questo work item.
- Il modello di costo è un'inferenza da un punto; T002 misura e il commento dell'impostazione rimanda ai numeri misurati.
- Il resto del tick a 2.000 fondatori resta superlineare (circa 38 s, stima): SC-005 lo misura e lo profila.

## FAQ

**Perché `batch_size` e non una scrittura O(N) vera?** Perché è la modifica più piccola che rende il costo lineare negli agenti, usa un parametro documentato di Django e non tocca né i tipi né i valori scritti. La scrittura con `VALUES` resta la strada successiva, da aprire solo se SC-003 fallisce per la scrittura stessa con il B migliore misurato.

**Come si sceglie B senza un numero magico?** T002 misura il tempo dell'intera scrittura delle aspettative di un mondo di 2.000 fondatori per B in {5, 10, 15, 25, 50, 100, 200, 500}, tre ripetizioni ciascuno, e ripete il primo candidato alla fine per controllare la deriva; se il minimo cade su un estremo della griglia, la griglia si estende. T003 sceglie il B con il tempo totale misurato minimo; il modello a·B² + c·B + b è adattato ai tempi per istruzione con i minimi quadrati solo per il commento, non per la scelta.

**Perché un'impostazione e non una costante?** Perché il progetto esprime così le grandezze regolabili, perché la leggono due app senza importarsi a vicenda, e perché nei test si sostituisce con la fixture `settings` invece di toccare un nome legato all'importazione.

**Il comportamento del modello cambia?** No. I valori sono calcolati in Python prima della scrittura e `batch_size` divide solo la lista in istruzioni. SC-004 lo verifica confrontando l'impronta dello stato fra il commit di base e la testa.

**Una scrittura a metà può lasciare lo stato incoerente?** No: Django esegue i lotti di un `bulk_update` dentro una `transaction.atomic`, quindi un errore annulla tutti i lotti come oggi annulla l'istruzione unica.

**Cosa succede al numero di query?** Cresce di ⌈R/B⌉ − 1 + ⌈A/B⌉ − 1 + ⌈S/B⌉ − 1 istruzioni per tick, ciascuna con un costo fisso b; a 2.000 fondatori e B = 100 sono circa 140 istruzioni in più, contro un'istruzione da 285 s.

**Si integra con la riproducibilità?** Sì: l'ordine delle righe resta quello di oggi (per `id` nell'economia, per ricchezza decrescente nella stratificazione), e i lotti seguono quell'ordine.

**Perché SC-005 non blocca la chiusura?** Perché misura il tick intero di un altro ramo, con passi che questo work item non tocca; bloccare qui su un costo altrui renderebbe il criterio non falsificabile per questo lavoro. Il numero e il profilo si riportano comunque.

**Perché non correggere anche il ciclo politico che gira a ogni tick?** Perché cambiarlo cambia la dinamica politica di ogni simulazione: è una modifica del modello del §4.5, con la sua spec e il suo audit.

**Quanto costa misurare?** La run di base a 2.000 fondatori con 2 tick misurati richiede circa 10 minuti (stima dai 330 s per tick), la testa pochi minuti; tutto nel progetto Docker isolato della sessione.

**Ci sono aspetti di sicurezza?** Nessuno nuovo: nessun SQL scritto a mano, nessuna rotta; l'unico input nuovo è una variabile d'ambiente intera, validata all'avvio.

## Stato dell'audit

**Round 1** (2026-11-12, `critical-analyzer` su Opus, su spec, piano e compiti della revisione 1):

```
VERDICT: NOT CONVERGED
FINDINGS: 3 INCORRECT, 4 UNJUSTIFIED, 4 INCONSISTENT, 2 MISSING
COVERAGE: partial (nessuna esecuzione: niente Docker né PostgreSQL; il costo fisso b e il ragionamento sulle versioni di riga sono inferiti; 285 s, 330 s e 3,3 s verificati solo come registrazioni scritte; il resto del tick non controllato riga per riga)
```

Ho verificato e corretto nella revisione 2 tutti i tredici rilievi. A1 (INCORRECT): il ciclo politico gira a ogni tick, verificato in `world/government.py:779-797` e `simulation/engine.py:532`; `update_social_classes` entra nell'ambito come User Story 2 e il difetto dell'intervallo è registrato fuori ambito. A2: dichiarato il resto superlineare stimato in circa 38 s e il profilo in SC-005. A3: script in modalità transazionale. A4: seme fisso, `simulation.id` stampato e confrontato, una invocazione di pytest per run. A5: griglia da 5 a 500 con estensione agli estremi. A6: scelta sui tempi misurati, modello a tre parametri solo riportato. A7: conteggio delle `UPDATE` per tick e stima delle `save()` riga per riga. A8: elencate le 26 citazioni e il pin del whitepaper. A9: citazione di `CaptureQueriesContext` corretta. A10: ogni guardia su due valori di B. A11: «circa 1.000 righe». A12: «agenti vivi con inventario». A13: adottata l'impostazione `EPOCHA_BULK_UPDATE_BATCH_SIZE` al posto della costante di modulo.

**Round 2**: non ancora eseguito (budget della notte). Lo stato resta **NOT CONVERGED** finché un round di verifica non conferma le correzioni e non trova rilievi nuovi; il gate di fase 2 aspetta quel round.

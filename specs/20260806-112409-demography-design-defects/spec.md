# Feature Specification: Correzione degli otto difetti di design della demografia

**Feature Branch**: `20260806-112409-demography-design-defects`

**Created**: 2026-08-06

**Status**: Draft — richiede gate pesante di fase 2 con emendamento della spec di design CONVERGED

**Input**: gli otto rilievi di livello design rinviati dall'audit avversariale di fase 6 della Demografia Plan 3 (report `specs/20260717-120706-demography-inheritance-migration/audit/T046-round-{1,2,3}-NOT-CONVERGED.md`), dove il codice implementa fedelmente il design e **il design stesso è sbagliato**.

## Perché questo work item esiste

L'audit di fase 6 della Demografia Plan 3 ha attraversato quattro round prima di convergere. La convergenza copre **il codice come delimitato**, non i difetti scientifici del modello che il codice riproduce fedelmente. Quegli otto rilievi sono stati deliberatamente separati, e ratificati come tali dall'utente il 2026-07-20, perché correggerli significa emendare `docs/superpowers/specs/2026-04-18-demography-design-it.md` — una spec dichiarata CONVERGED dopo quattro round di audit nell'aprile 2026 — e un emendamento di spec è un gate pesante di fase 2, non esecuzione di fase 5.

Tutti e otto sono già dichiarati nel capitolo §4.1 di entrambi i whitepaper come **attualmente veri del modello**, con la loro magnitudine misurata. Questo work item non li scopre: li chiude. Chiuderli comporta quindi anche riscrivere le parti di §4.1 che oggi documentano il difetto, in entrambe le lingue.

**Vincolo di sequenza non negoziabile**: nessuna modifica al codice prima che la spec di design emendata abbia superato il proprio ciclo di convergenza avversariale. L'ordine inverso — correggere il codice e poi allineare la spec — è precisamente ciò che ha prodotto questi difetti.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Il modello genetico conserva la varianza fra le generazioni (Priority: P1)

Un ricercatore fa girare una simulazione per molte generazioni e osserva la distribuzione dei tratti ereditabili nella popolazione. Oggi quella distribuzione si restringe generazione dopo generazione fino a stabilizzarsi attorno alla metà dell'ampiezza dichiarata, e l'ereditabilità realizzata smette di corrispondere ai valori che i template dichiarano. Il ricercatore ha bisogno che la popolazione mantenga nel tempo la variabilità che il modello afferma di campionare.

**Why this priority**: è il difetto che altera di più gli esiti simulati, tocca tutti e tredici i tratti ereditabili, e invalida qualunque risultato derivato dalla varianza dei tratti in una run multi-generazionale. Copre i rilievi 1, 2 e 7 dell'audit, che sono un unico difetto in tre manifestazioni: il kernel non conserva la varianza, il fallback a genitore singolo non dimezza il segnale come dichiarato, e i parametri di rumore d'era sono segnaposto che in pratica sono i parametri e fissano il punto di convergenza.

**Independent Test**: far girare una popolazione sintetica per otto generazioni con ereditabilità e ampiezza d'era note, e verificare che la deviazione standard dei tratti resti entro una tolleranza dichiarata dell'ampiezza iniziale invece di collassare; verificare separatamente che la somiglianza genitore-figlio misurata su un solo genitore noto sia la metà di quella misurata su due.

**Acceptance Scenarios**:

1. **Given** una popolazione con ereditabilità 0.55 e ampiezza d'era 0.15, **When** la si fa evolvere per otto generazioni, **Then** la dispersione dei tratti resta entro la tolleranza dichiarata dell'ampiezza iniziale invece di stabilizzarsi al 48,8%.
2. **Given** un figlio con un solo genitore noto di valore 0.9, **When** se ne calcola il tratto, **Then** il coefficiente di regressione applicato è la metà di quello del caso a due genitori, e la documentazione afferma questo e non altro.
3. **Given** un'era qualsiasi fra le cinque, **When** si risolve la distribuzione di rumore usata alla nascita, **Then** i suoi parametri provengono da una fonte dichiarata per quell'era e non da un valore di ripiego usato per ogni tratto di ogni era.
4. **Given** l'ereditabilità dichiarata in un template, **When** la si misura sulla popolazione dopo diverse generazioni, **Then** il valore realizzato corrisponde a quello dichiarato entro una tolleranza documentata.

---

### User Story 2 - La successione islamica rispetta l'asimmetria coranica (Priority: P2)

Un revisore confronta le quote successorie prodotte dalla simulazione nell'era pre-industriale islamica con quelle che la fonte citata prescrive. Oggi un vedovo riceve la metà di quanto gli spetterebbe, perché la quota coniugale è applicata in modo neutro rispetto al genere mentre la fonte è esplicitamente asimmetrica.

**Why this priority**: è un difetto di fedeltà alla fonte con conseguenze distributive reali, e la spec cita Powers (1986) per una struttura che Powers non sostiene. Un capitolo scientifico che cita una fonte per qualcosa che la fonte non dice è indifendibile in sede di pubblicazione, indipendentemente dalla magnitudine numerica.

**Independent Test**: liquidare quattro patrimoni nell'era islamica — vedovo con figli, vedovo senza figli, vedova con figli, vedova senza figli — e verificare le quattro quote contro quelle prescritte dalla fonte.

**Acceptance Scenarios**:

1. **Given** un defunto con coniuge superstite maschio e nessun figlio, **When** il patrimonio viene liquidato, **Then** il coniuge riceve la quota che la fonte prescrive per quel caso, distinta da quella della vedova nello stesso caso.
2. **Given** un defunto con coniuge superstite femmina e figli, **When** il patrimonio viene liquidato, **Then** la quota resta quella oggi implementata, che per questo caso è già corretta.
3. **Given** la documentazione della regola, **When** la si legge, **Then** la fonte è citata per ciò che effettivamente sostiene.

---

### User Story 3 - Il guadagno atteso di migrazione è dimensionalmente coerente (Priority: P2)

Un agente valuta se trasferirsi in un'altra zona confrontando il guadagno economico atteso col costo del viaggio. Oggi quel confronto sottrae un numero di tick da una quantità monetaria per tick: le unità non tornano, e l'esempio numerico del design non lo rivela solo perché calcola una destinazione a costo distanza zero.

**Why this priority**: una formula pubblicata le cui unità non bilanciano non è difendibile nel paper, ed è materia da GOLDEN RULE.

**IL RIMEDIO DEL ROUND 1 NON RISOLVE IL PROBLEMA, ed è questa la vera decisione del gate.** Il round 1 dell'audit di codice aveva stabilito di monetizzare il costo come reddito mancato, `costo_in_tick × salario_corrente`, motivandolo col ripristino dell'equilibrio dimensionale. Verificato: non lo ripristina. `[T] × [M·T⁻¹] = [M]`, cioè moneta, mentre gli altri due termini restano moneta per tick — si scambia uno squilibrio con un altro. Bilanciare richiede un **orizzonte di pianificazione** `H` in tick, sia dividendo il costo monetizzato per `H` per restare un tasso, sia moltiplicando i primi due termini per `H` per ottenere un totale. `H` è un parametro libero nuovo che sposta la soglia migratoria, e non è nominato né giustificato in nessun punto del design, del codice o del whitepaper. Il compito del gate non è ratificare il giudizio del round 1: è **nominare e giustificare `H`**, oppure motivare una formulazione diversa che bilanci senza introdurlo.

**Independent Test**: verificare per analisi dimensionale che ogni termine della formula emendata abbia la stessa unità; calcolare il guadagno atteso verso due destinazioni a costo distanza diverso e non nullo, e verificare che l'ordinamento fra esse sia quello economicamente atteso.

**Acceptance Scenarios**:

1. **Given** una destinazione a costo distanza non nullo, **When** si calcola il guadagno atteso, **Then** tutti i termini hanno la stessa unità e il risultato è interpretabile in quella unità.
2. **Given** la formula emendata, **When** se ne legge la documentazione, **Then** l'orizzonte di pianificazione è nominato, il suo valore è giustificato, e l'effetto della sua scelta sulla soglia migratoria è dichiarato.
3. **Given** due simulazioni identiche denominate in valute di scala diversa, **When** gli agenti valutano la stessa migrazione, **Then** la decisione è la stessa.

> **Nota su un test che NON discrimina.** L'esempio numerico della spec di design ha costo distanza zero, quindi ogni candidato correttivo lo riproduce identicamente — comprese le formulazioni che lasciano le unità squilibrate. Riprodurlo non è evidenza a favore di nessuna correzione, e non va usato come criterio di accettazione. L'ho verificato: `(1 − 0.08)·90 − 78 − 0 = 4.8`, che coincide col valore dichiarato dal design proprio perché il terzo termine è assente.

---

### User Story 4 - La conservazione del patrimonio è esatta anche nel passaggio d'imposta (Priority: P3)

Chi verifica i conti della simulazione somma imposta e residuo e si aspetta di ritrovare esattamente il patrimonio di partenza. Oggi il passaggio d'imposta calcola le due parti come prodotti indipendenti e la somma non torna, mentre il ripartitore fra eredi cinquanta righe più in là si prende cura di essere esatto.

**Le magnitudini, misurate direttamente e non ereditate dai report.** Il tasso di non-esattezza dipende dall'aliquota: **16,1% ad aliquota 0,15, 6,0% a 0,40, e 0% ad aliquota nulla — che è quella di tre template su cinque**, quindi il difetto non si manifesta affatto nelle due ere pre-industriali né in quella sci-fi. L'errore relativo massimo è **1,9·10⁻¹⁶**, cioè un ulp, non l'ordine di grandezza superiore che una lettura frettolosa del round 1 suggeriva: quel report riportava 1,16·10⁻¹⁰ come errore **assoluto** su un patrimonio di mezzo milione. La cifra "circa un caso su cinque" che circolava non è riproducibile sotto nessuna distribuzione provata.

**Why this priority**: la magnitudine è di un ulp e in tre ere su cinque il difetto è assente, quindi l'impatto sugli esiti è nullo. Resta però che il modulo **afferma** un invariante di conservazione esatto e non negoziabile, portante per l'impianto contabile del whitepaper, mentre uno dei suoi due passaggi aritmetici non lo rispetta. Si corregge perché l'affermazione deve essere vera, non perché i numeri cambino.

**L'esattezza è raggiungibile, e il rimedio proposto dal round 1 non la raggiunge.** Quel report proponeva `residuo = totale − imposta`, ammettendo che riduce il tasso al 4,9% senza azzerarlo (misurato: 6,2% alle aliquote spedite). La costruzione che funziona è **derivare all'indietro**: calcolato il residuo, si ridefinisce l'imposta come `totale − residuo`. Misurato: **zero fallimenti su 200.000 prove**. È esattamente la tecnica dell'ultimo-termine-assorbe che `_allocate_with_exact_remainder` già usa per gli eredi, quindi il modulo la possiede già.

**Independent Test**: liquidare molti patrimoni di importo casuale a ciascuna delle aliquote effettivamente spedite dai template, e verificare che imposta più residuo eguagli esattamente il patrimonio.

**Acceptance Scenarios**:

1. **Given** un patrimonio e una qualsiasi delle aliquote spedite, **When** si applica l'imposta, **Then** imposta più residuo eguaglia esattamente il patrimonio.
2. **Given** la documentazione della funzione, **When** la si legge, **Then** la garanzia dichiarata è quella che il codice offre davvero, e dichiara rispetto a quale ordine di somma vale.

---

### User Story 5 - La spec di design smette di contraddirsi sull'orizzonte di sopravvivenza (Priority: P2)

Un agente affamato decide se fuggire. Oggi la condizione confronta la sua ricchezza accumulata con il costo di sussistenza di un singolo tick: un agente con trenta tick di risparmi è trattato come uno che ne ha uno solo.

**NON è una semplificazione non dichiarata: è una contraddizione dentro la spec CONVERGED.** Verificato: la riga 153 del design stabilisce la convenzione generale — *"I confronti di ricchezza usano `agent.wealth < N * subsistence_threshold` dove `N` è il numero di tick di sussistenza che l'agente può sopravvivere con i risparmi attuali (parametro di design tunable, default 30 tick ≈ 1 mese)"* — e la riga 841 scrive poi la condizione di fuga **senza** `N`. Il codice segue la riga 841. Questo cambia il rimedio: non basta dichiarare l'orizzonte, perché dichiarare "un tick" lascerebbe in piedi la riga 153 contraddetta.

**Why this priority**: alzato da P3 a P2 rispetto alla prima stesura. Una contraddizione interna a una spec dichiarata CONVERGED è un difetto del processo di audit oltre che del modello, e il gate deve scegliere fra due concetti diversi, non fra due valori. Adottare `N = 30` non è gratis: anche `flight_trigger_ticks` vale 30, quindi il trigger diventerebbe "sotto un mese di risparmi, per un mese di fila" — un test di risparmio precauzionale, non di fame, che scatterebbe per una porzione ampia della popolazione. Mantenere un tick lo tiene un test di fame ma nega la riga 153. Sono due modelli diversi e la spec non dice quale sia quello voluto.

**Lo stesso confronto è vivo anche nella fertilità, ed è fuori dall'ambito di questa user story ma non della decisione.** `fertility.py` calcola il proprio segnale di ricchezza sullo stesso rapporto fra stock accumulato e flusso per tick, altrettanto non riconciliato con la riga 153. Poiché la decisione del gate è una decisione **sulla riga 153**, ricade su entrambi i consumatori: il capitolo §4.1.2 del whitepaper, già promosso, va aggiornato di conseguenza.

**Independent Test**: costruire due agenti con la stessa ricchezza corrente ma orizzonti di sopravvivenza diversi e verificare che il trigger li distingua secondo il criterio scelto; verificare separatamente che il criterio scelto sia lo stesso che governa il segnale di ricchezza della fertilità.

**Acceptance Scenarios**:

1. **Given** un agente con risparmi sufficienti per molti tick di sussistenza, **When** si valuta la condizione di fuga, **Then** l'esito riflette l'orizzonte che la spec emendata stabilisce, e la spec non contiene più due affermazioni incompatibili su quale sia.
2. **Given** la scelta dell'orizzonte, **When** la si legge nella spec emendata, **Then** è motivata rispetto alla distinzione fra test di fame e test di risparmio precauzionale, ed è dichiarata la sua interazione con `flight_trigger_ticks`.
3. **Given** il segnale di ricchezza della fertilità, **When** lo si confronta con la condizione di fuga, **Then** entrambi applicano la convenzione stabilita dalla spec emendata.

---

### User Story 6 - I parametri dei template corrispondono alle fonti citate (Priority: P3)

Chi legge il paper trova un valore attribuito a uno studio pubblicato e si aspetta di ritrovare quel valore nei dati che governano la simulazione. Oggi tre template portano valori di regressione dell'istruzione diversi da quelli che la spec attribuisce alle proprie fonti, e il caso più visibile è il valore moderno, attribuito a Chetty et al. (2014) come 0.35 e spedito come 0.4.

**Why this priority**: è una correzione di dati, la più contenuta delle otto, ma tocca direttamente la regola del progetto per cui nessun parametro esiste senza un valore giustificato.

**Independent Test**: confrontare ogni valore di regressione dei cinque template con quello che la spec attribuisce alla propria fonte per quell'era, e verificare che coincidano o che la divergenza sia dichiarata con la sua ragione.

**Acceptance Scenarios**:

1. **Given** ciascuna delle cinque ere, **When** si confronta il valore di regressione del template con quello citato nella spec, **Then** i due coincidono, oppure la spec dichiara perché il valore spedito differisce da quello della fonte.

---

### Edge Cases

- Che cosa succede alle simulazioni già eseguite e ai loro risultati, se il modello genetico cambia? Serve una dichiarazione esplicita di non comparabilità fra risultati prodotti prima e dopo l'emendamento.
- Come si distingue, nella regola successoria islamica, il coniuge superstite non binario, dato che la fonte è formulata su una dicotomia? La spec attuale documenta già un trattamento per i figli non binari nella ripartizione residuale e va estesa coerentemente.
- Il correttivo dimensionale sul costo distanza interagisce con il salario di zona: correggerne il divisore ha già spostato quel valore del venti per cento, e le due correzioni si compongono.
- Il troncamento dei tratti a `[0,1]` limita la varianza raggiungibile, e quanto la limiti dipende da dove cade la media d'era. Risolvere le medie per tratto — cioè fare quanto FR-004 chiede — sposta il troncamento e peggiora la conservazione della varianza. Quale delle due proprietà cede, e di quanto, è una decisione del gate.
- L'era sci-fi accoppia gli agenti su una funzione deterministica di un tratto ereditabile, tramite la regola di classe meritocratica, quindi l'assunzione di accoppiamento casuale che sta sotto l'obiettivo di varianza non vale lì.
- Se il gate adotta `N = 30` per l'orizzonte di sopravvivenza mentre `flight_trigger_ticks` vale anch'esso 30, il trigger di fuga cambia natura: da test di fame a test di risparmio precauzionale sostenuto per un mese. È un cambiamento di modello, non di parametro.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: la spec di design MUST essere emendata prima di qualunque modifica al codice, e l'emendamento MUST attraversare un ciclo di convergenza avversariale con verdetto CONVERGED esplicito.
- **FR-002**: il modello di trasmissione dei tratti MUST conservare la varianza della popolazione fra le generazioni, invece di contrarla verso un punto fisso. La tolleranza MUST essere dichiarata come **funzione** di ereditabilità, media d'era e ampiezza d'era, non come numero unico: il troncamento dei tratti all'intervallo `[0,1]` non costa nulla quando la media d'era è centrata (misurato: 99,7% dell'obiettivo a media 0,5) ma degrada in modo prevedibile quando si sposta, e con una media d'era reale di 0,8 il troncamento scende a 1,33 deviazioni standard e la varianza stazionaria misurata cala al 92,1% dell'obiettivo. **FR-002 e FR-004 tirano in direzioni opposte** e la spec emendata MUST riconciliarli esplicitamente.
- **FR-003**: il caso a genitore singolo MUST applicare il coefficiente di regressione che la fonte citata prescrive per quel caso, e la documentazione MUST descrivere ciò che il codice fa. Il requisito MUST coprire anche **la scala del residuo in tutti e tre i rami** — due genitori noti, uno solo, nessuno — e non solo il coefficiente: la forma correttiva già pubblicata nel whitepaper dà il residuo per il solo caso a due genitori, e implementata alla lettera negli altri rami misura il 95,7% dell'obiettivo invece di conservarlo.
- **FR-004**: i parametri della distribuzione di rumore MUST essere risolti per era e per tratto da una fonte dichiarata, oppure MUST essere dichiarati come parametri di progetto tarabili con la loro giustificazione, non come segnaposto interinali. La risoluzione MUST tenere conto dell'interazione con FR-002 descritta sopra.
- **FR-005**: la quota coniugale nella regola successoria islamica MUST dipendere dal genere del coniuge superstite secondo la fonte citata, che prescrive **vedovo 1/2 senza figli e 1/4 con figli, vedova 1/4 senza figli e 1/8 con figli** (oggi il codice applica 1/4 e 1/8 a entrambi). MUST inoltre definire il trattamento del coniuge non binario coerentemente con quanto la spec già stabilisce per i figli nella ripartizione residuale.
- **FR-006**: il guadagno atteso di migrazione MUST avere tutti i termini nella stessa unità, e la decisione migratoria MUST essere invariante rispetto alla scala della valuta. La spec emendata MUST nominare e giustificare l'orizzonte di pianificazione che il bilanciamento richiede, oppure motivare una formulazione che bilanci senza introdurlo; **NON è sufficiente monetizzare il costo distanza**, perché ciò produce una quantità monetaria contro termini che sono tassi.
- **FR-007**: il passaggio d'imposta di successione MUST conservare il valore esattamente. La spec emendata MUST nominare la costruzione usata: derivare l'ultimo termine per differenza, la stessa tecnica che il ripartitore fra eredi già impiega, verificata a zero fallimenti su 200.000 prove. Il rimedio proposto dal round 1 dell'audit di codice (`residuo = totale − imposta`) NON raggiunge l'esattezza e MUST NOT essere ereditato.
- **FR-008**: la spec di design MUST risolvere la propria contraddizione interna fra la convenzione generale della riga 153 (`N` tick di sussistenza, default 30) e la condizione di fuga della riga 841 (che omette `N`), scegliendo esplicitamente fra un test di fame e un test di risparmio precauzionale e dichiarando l'interazione con `flight_trigger_ticks`. La scelta MUST essere applicata a **tutti** i consumatori della soglia di sussistenza, inclusa la modulazione della fertilità.
- **FR-009**: ogni parametro dei template MUST corrispondere al valore attribuito alla sua fonte, oppure la divergenza MUST essere dichiarata con la sua ragione. **L'attribuzione stessa MUST essere verificata prima di diventare il bersaglio**: la spec di design cita Chetty et al. (2014) in due punti per due grandezze diverse — un intervallo di elasticità del reddito e un coefficiente di persistenza dell'istruzione — e allineare i dati spediti a un'attribuzione errata non sarebbe una correzione.
- **FR-010**: il capitolo §4.1 di ENTRAMBI i whitepaper MUST essere aggiornato nello stesso work item, sostituendo la dichiarazione del difetto con la descrizione del modello corretto, e MUST dichiarare la non comparabilità fra risultati prodotti prima e dopo. L'aggiornamento MUST includere §4.1.2 (fertilità), che condivide la decisione di FR-008, e MUST correggere l'affermazione secondo cui la monetizzazione del costo distanza ripristina l'equilibrio dimensionale, ovunque essa compaia.
- **FR-011**: ogni correzione MUST essere coperta da un test che fallisce contro il comportamento attuale, verificato per mutazione e non per sola ispezione.
- **FR-012**: il lavoro MUST dichiarare quali benchmark di calibrazione cambiano esito e perché il nuovo esito è quello corretto. **Nota di stato verificata**: nessun benchmark di calibrazione demografica eseguibile esiste oggi nella suite — quelli previsti sono tracciati come lavoro futuro — quindi il requisito vincola i benchmark da scrivere, non un insieme esistente.
- **FR-013**: la spec emendata MUST dichiarare l'assunzione di accoppiamento su cui poggia l'obiettivo di varianza. Verificato: il punteggio di omogamia non pesa nessuno dei tredici tratti ereditabili in quattro ere su cinque, ma nell'era sci-fi la regola di classe meritocratica deriva la classe sociale da intelligenza e istruzione, e la classe è il fattore di peso maggiore nell'omogamia — quindi lì l'accoppiamento è assortativo su una funzione deterministica di un tratto ereditabile, e il kernel corretto sovra-conserva (misurato: 108,2% dell'obiettivo sotto forte assortimento).

### Key Entities

- **Spec di design demografia**: `docs/superpowers/specs/2026-04-18-demography-design-it.md`, dichiarata CONVERGED nell'aprile 2026. È l'artefatto che questo work item emenda; le sue sezioni 4, 5 e 6 sono quelle toccate.
- **Template d'era**: i cinque file che dichiarano i parametri per era. Portano i valori di ereditabilità, di regressione dell'istruzione e le regole successorie.
- **Capitolo §4.1 dei whitepaper**: nelle due lingue, oggi documenta gli otto difetti come veri del modello. Va riscritto quando cessano di esserlo.
- **Report d'audit di fase 6**: i quattro report della Plan 3, che contengono l'evidenza misurata di ciascun difetto e sono il punto di partenza dell'emendamento.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: la spec di design emendata raggiunge un verdetto CONVERGED esplicito in un ciclo di audit avversariale, con zero rilievi INCORRECT e zero UNJUSTIFIED residui.
- **SC-002**: in una popolazione simulata per otto generazioni, la dispersione dei tratti ereditabili resta entro la tolleranza dichiarata da FR-002 per la combinazione di ereditabilità, media e ampiezza d'era usata, contro il 48,8% misurato oggi. La verifica MUST coprire i tre rami di parentela, non il solo caso a due genitori.
- **SC-003**: l'ereditabilità misurata sulla popolazione dopo diverse generazioni corrisponde a quella dichiarata nei template entro una tolleranza documentata, **in tutte e cinque le ere** — oppure l'era sci-fi è esplicitamente esentata con la ragione dell'accoppiamento assortativo di FR-013.
- **SC-004**: le quote coniugali della regola islamica valgono 1/2 e 1/4 per il vedovo (senza e con figli) e 1/4 e 1/8 per la vedova, e il trattamento del coniuge non binario è quello dichiarato dalla spec emendata.
- **SC-005**: due simulazioni identiche denominate in valute di scala diversa producono le stesse decisioni migratorie. **Nota**: questo criterio non discrimina fra le formulazioni candidate — è soddisfatto da qualunque monetizzazione — quindi non basta da solo a validare FR-006, che richiede in aggiunta la verifica dimensionale termine per termine.
- **SC-006**: imposta più residuo eguaglia esattamente il patrimonio a ciascuna delle aliquote spedite dai template, con asserzione di uguaglianza esatta, dichiarando rispetto a quale ordine di somma vale.
- **SC-007**: ogni valore parametrico dei cinque template coincide con quello attribuito alla sua fonte, oppure porta una divergenza dichiarata.
- **SC-008**: il capitolo §4.1 di entrambi i whitepaper non contiene più la dichiarazione degli otto difetti come veri, e dichiara la discontinuità dei risultati.
- **SC-009**: l'audit di fase 6 sul codice raggiunge un verdetto CONVERGED esplicito.
- **SC-010**: la suite di progetto resta verde, senza test disabilitati o marcati xfail per accomodare le correzioni.

## Assumptions

- Il gate pesante di fase 2 su questo emendamento è richiesto e sarà eseguito: la spec di design CONVERGED non si riapre senza di esso. Questa è la ragione per cui il work item è separato dalla Plan 3 e non un'appendice di essa.
- Le correzioni cambiano gli esiti numerici della simulazione. L'assunzione è che questo sia accettabile e anzi voluto, perché gli esiti attuali sono scientificamente scorretti; la conseguenza è che i risultati prodotti prima dell'emendamento non sono comparabili con quelli prodotti dopo, e va dichiarato.
- Il lavoro non tocca il cablaggio della demografia nel tick loop, che resta di competenza della Plan 4, né dipende da esso: tutti e otto i difetti sono osservabili e correggibili sui moduli in isolamento.
- **Le magnitudini sono state riverificate, e due erano sbagliate.** Il 48,8% del collasso della varianza regge: ricavato analiticamente e riprodotto in simulazione da due parti indipendenti. Il fattore due sulla quota del vedovo regge. Ma il tasso di non-esattezza della conservazione **non** è "circa un caso su cinque": è 16,1% ad aliquota 0,15, 6,0% a 0,40 e **zero** ad aliquota nulla, che è quella di tre template su cinque; e l'errore relativo massimo è 1,9·10⁻¹⁶, non l'ordine di 10⁻¹⁰ che circolava, perché quella cifra era un errore assoluto su un patrimonio grande. La prima stesura di questa spec riportava entrambe le cifre sbagliate, ereditate senza verifica.
- **Il giudizio del round 1 sulla migrazione non è assunto valido**: è stato verificato ed è errato, come documenta la User Story 3. Questo è il motivo per cui il gate serve davvero su quel punto.
- L'ordine di priorità riflette l'impatto sugli esiti simulati, non la difficoltà. La User Story 5 è stata alzata da P3 a P2 dopo la verifica, perché si è rivelata una contraddizione interna alla spec CONVERGED anziché una semplificazione taciuta.
- **Sull'ampiezza del gate**: quattro delle sei user story hanno una correzione già derivata e pubblicata, e per esse il gate deve registrare una decisione, non deliberarla. Le questioni che richiedono deliberazione sono tre: l'orizzonte di pianificazione della migrazione, l'orizzonte di sussistenza e la sua estensione alla fertilità, e la fonte dei parametri di rumore per era e per tratto con la sua interazione col troncamento. Se questo work item va spezzato, va spezzato lì.

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

**Why this priority**: una formula pubblicata le cui unità non bilanciano non è difendibile nel paper, ed è materia da GOLDEN RULE. L'audit ha già emesso il proprio giudizio nel round 1 — monetizzare il costo come reddito mancato — con la motivazione che ripristina l'equilibrio dimensionale, riproduce esattamente l'esempio del design e ha un significato economico, mentre una scala dichiarata di un'unità di valuta per tick legherebbe la soglia migratoria alla scala arbitraria della valuta.

**Independent Test**: calcolare il guadagno atteso verso due destinazioni a costo distanza diverso e verificare che il risultato sia omogeneo in unità monetarie per tick; ricalcolare l'esempio del design e confermare che il valore dichiarato è riprodotto.

**Acceptance Scenarios**:

1. **Given** una destinazione a costo distanza non nullo, **When** si calcola il guadagno atteso, **Then** tutti i termini sono omogenei e il risultato è interpretabile come quantità monetaria per tick.
2. **Given** l'esempio numerico della spec di design, **When** lo si ricalcola con la formula emendata, **Then** il valore dichiarato è riprodotto esattamente.
3. **Given** due simulazioni identiche denominate in valute di scala diversa, **When** gli agenti valutano la stessa migrazione, **Then** la decisione è la stessa.

---

### User Story 4 - La conservazione del patrimonio è esatta anche nel passaggio d'imposta (Priority: P3)

Chi verifica i conti della simulazione somma imposta e quote degli eredi e si aspetta di ritrovare esattamente il patrimonio di partenza. Oggi il passaggio d'imposta calcola le due parti come prodotti indipendenti e la somma non torna in circa un caso su cinque, mentre il ripartitore fra eredi cinquanta righe più in là si prende cura di essere esatto.

**Why this priority**: la magnitudine è trascurabile (dell'ordine di una parte su dieci miliardi), ma l'invariante di conservazione è dichiarato come non negoziabile e portante per l'impianto contabile del whitepaper. Un modulo non può affermare un invariante esatto mentre uno dei suoi due passaggi aritmetici non lo rispetta.

**Independent Test**: liquidare molti patrimoni di importo casuale a diverse aliquote e verificare che imposta più residuo eguagli esattamente il patrimonio, con la stessa asserzione di uguaglianza esatta già usata per il ripartitore fra eredi.

**Acceptance Scenarios**:

1. **Given** un patrimonio e un'aliquota qualsiasi, **When** si applica l'imposta, **Then** imposta più residuo eguaglia esattamente il patrimonio.
2. **Given** la documentazione della funzione, **When** la si legge, **Then** la garanzia dichiarata è quella che il codice offre davvero, con la stessa precisione già adottata altrove nel modulo.

---

### User Story 5 - Il trigger di fuga confronta grandezze omogenee (Priority: P3)

Un agente affamato decide se fuggire. Oggi la condizione confronta la sua ricchezza accumulata con il costo di sussistenza di un singolo tick: un agente con trenta tick di risparmi è trattato come uno che ne ha uno solo, e l'orizzonte di sopravvivenza risulta fissato a un tick senza che nulla lo dichiari.

**Why this priority**: è una semplificazione difendibile — "non può permettersi il cibo di questo tick" — ma non dichiarata, e interagisce col contatore di tick consecutivi sotto sussistenza in modo che assume implicitamente che la ricchezza non si accumuli.

**Independent Test**: costruire due agenti con la stessa ricchezza ma orizzonti di sopravvivenza diversi e verificare che il trigger li distingua secondo il criterio dichiarato.

**Acceptance Scenarios**:

1. **Given** un agente con risparmi sufficienti per molti tick di sussistenza, **When** si valuta la condizione di fuga, **Then** l'esito riflette l'orizzonte dichiarato dal modello e non un orizzonte implicito di un tick.
2. **Given** la documentazione della condizione, **When** la si legge, **Then** l'orizzonte di sopravvivenza assunto è dichiarato esplicitamente.

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
- Che cosa succede se la correzione della varianza modifica gli esiti dei test di calibrazione demografica esistenti, che sono stati costruiti sul comportamento attuale?
- Come si distingue, nella regola successoria islamica, il coniuge superstite non binario, dato che la fonte è formulata su una dicotomia? La spec attuale documenta già un trattamento per i figli non binari nella ripartizione residuale e va estesa coerentemente.
- Il correttivo dimensionale sul costo distanza interagisce con il salario di zona: correggerne il divisore ha già spostato quel valore del venti per cento, e le due correzioni si compongono.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: la spec di design MUST essere emendata prima di qualunque modifica al codice, e l'emendamento MUST attraversare un ciclo di convergenza avversariale con verdetto CONVERGED esplicito.
- **FR-002**: il modello di trasmissione dei tratti MUST conservare la varianza della popolazione fra le generazioni, entro una tolleranza dichiarata, invece di contrarla verso un punto fisso.
- **FR-003**: il caso a genitore singolo MUST applicare il coefficiente di regressione che la fonte citata prescrive per quel caso, e la documentazione MUST descrivere ciò che il codice fa.
- **FR-004**: i parametri della distribuzione di rumore MUST essere risolti per era e per tratto da una fonte dichiarata, oppure MUST essere dichiarati come parametri di progetto tarabili con la loro giustificazione, non come segnaposto interinali.
- **FR-005**: la quota coniugale nella regola successoria islamica MUST riflettere l'asimmetria della fonte citata, e MUST definire il trattamento del coniuge non binario coerentemente con quanto la spec già stabilisce per i figli.
- **FR-006**: il guadagno atteso di migrazione MUST essere dimensionalmente omogeneo, e la decisione migratoria MUST essere invariante rispetto alla scala della valuta.
- **FR-007**: il passaggio d'imposta di successione MUST conservare il valore esattamente, con la stessa garanzia già offerta dalla ripartizione fra eredi.
- **FR-008**: la condizione di fuga MUST confrontare grandezze omogenee e MUST dichiarare l'orizzonte di sopravvivenza assunto.
- **FR-009**: ogni parametro dei template MUST corrispondere al valore attribuito alla sua fonte, oppure la divergenza MUST essere dichiarata con la sua ragione.
- **FR-010**: il capitolo §4.1 di ENTRAMBI i whitepaper MUST essere aggiornato nello stesso work item, sostituendo la dichiarazione del difetto con la descrizione del modello corretto, e MUST dichiarare la non comparabilità fra risultati prodotti prima e dopo.
- **FR-011**: ogni correzione MUST essere coperta da un test che fallisce contro il comportamento attuale, verificato per mutazione e non per sola ispezione.
- **FR-012**: il lavoro MUST dichiarare esplicitamente quali test di calibrazione esistenti cambiano esito, e perché il nuovo esito è quello corretto.

### Key Entities

- **Spec di design demografia**: `docs/superpowers/specs/2026-04-18-demography-design-it.md`, dichiarata CONVERGED nell'aprile 2026. È l'artefatto che questo work item emenda; le sue sezioni 4, 5 e 6 sono quelle toccate.
- **Template d'era**: i cinque file che dichiarano i parametri per era. Portano i valori di ereditabilità, di regressione dell'istruzione e le regole successorie.
- **Capitolo §4.1 dei whitepaper**: nelle due lingue, oggi documenta gli otto difetti come veri del modello. Va riscritto quando cessano di esserlo.
- **Report d'audit di fase 6**: i quattro report della Plan 3, che contengono l'evidenza misurata di ciascun difetto e sono il punto di partenza dell'emendamento.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: la spec di design emendata raggiunge un verdetto CONVERGED esplicito in un ciclo di audit avversariale, con zero rilievi INCORRECT e zero UNJUSTIFIED residui.
- **SC-002**: in una popolazione simulata per otto generazioni, la dispersione dei tratti ereditabili resta entro la tolleranza dichiarata dell'ampiezza d'era, contro il 48,8% misurato oggi.
- **SC-003**: l'ereditabilità misurata sulla popolazione dopo diverse generazioni corrisponde a quella dichiarata nei template entro una tolleranza documentata.
- **SC-004**: le quattro quote coniugali della regola islamica corrispondono a quelle prescritte dalla fonte citata.
- **SC-005**: due simulazioni identiche denominate in valute di scala diversa producono le stesse decisioni migratorie.
- **SC-006**: imposta più residuo eguaglia esattamente il patrimonio in ogni caso testato, con asserzione di uguaglianza esatta.
- **SC-007**: ogni valore parametrico dei cinque template coincide con quello attribuito alla sua fonte, oppure porta una divergenza dichiarata.
- **SC-008**: il capitolo §4.1 di entrambi i whitepaper non contiene più la dichiarazione degli otto difetti come veri, e dichiara la discontinuità dei risultati.
- **SC-009**: l'audit di fase 6 sul codice raggiunge un verdetto CONVERGED esplicito.
- **SC-010**: la suite di progetto resta verde, senza test disabilitati o marcati xfail per accomodare le correzioni.

## Assumptions

- Il gate pesante di fase 2 su questo emendamento è richiesto e sarà eseguito: la spec di design CONVERGED non si riapre senza di esso. Questa è la ragione per cui il work item è separato dalla Plan 3 e non un'appendice di essa.
- Le correzioni cambiano gli esiti numerici della simulazione. L'assunzione è che questo sia accettabile e anzi voluto, perché gli esiti attuali sono scientificamente scorretti; la conseguenza è che i risultati prodotti prima dell'emendamento non sono comparabili con quelli prodotti dopo, e va dichiarato.
- Il lavoro non tocca il cablaggio della demografia nel tick loop, che resta di competenza della Plan 4, né dipende da esso: tutti e otto i difetti sono osservabili e correggibili sui moduli in isolamento.
- Le magnitudini riportate dall'audit (il 48,8%, il circa 19% dei casi di conservazione, il fattore due sulla quota del vedovo) sono assunte corrette: sono state misurate da auditor indipendenti e in due casi riprodotte in modo indipendente. Restano da riverificare contro il codice corrente prima di essere usate come baseline, secondo la regola di verifica del progetto.
- L'ordine di priorità fra le sei user story riflette l'impatto sugli esiti simulati, non la difficoltà. La prima è indipendentemente rilasciabile e da sola giustifica il work item.

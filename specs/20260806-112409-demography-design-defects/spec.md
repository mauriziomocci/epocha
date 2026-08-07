# Feature Specification: Correzione dei difetti di design della demografia

**Feature Branch**: `20260806-112409-demography-design-defects`

**Created**: 2026-08-06

**Status**: Draft — richiede gate pesante di fase 2 con emendamento della spec di design CONVERGED

**Input**: gli otto rilievi di livello design rinviati dall'audit avversariale di fase 6 della Demografia Plan 3 (report `specs/20260717-120706-demography-inheritance-migration/audit/T046-round-{1,2,3}-NOT-CONVERGED.md`), dove il codice implementa fedelmente il design e **il design stesso è sbagliato**.

## Perché questo work item esiste

L'audit di fase 6 della Demografia Plan 3 ha attraversato quattro round prima di convergere. La convergenza copre **il codice come delimitato**, non i difetti scientifici del modello che il codice riproduce fedelmente. Quegli otto rilievi sono stati deliberatamente separati, e ratificati come tali dall'utente il 2026-07-20, perché correggerli significa emendare `docs/superpowers/specs/2026-04-18-demography-design-it.md` — una spec dichiarata CONVERGED dopo quattro round di audit nell'aprile 2026 — e un emendamento di spec è un gate pesante di fase 2, non esecuzione di fase 5.

Gli otto rilievi originari sono già dichiarati nel capitolo §4.1 di entrambi i whitepaper come **attualmente veri del modello**, con la loro magnitudine misurata: per essi questo work item non scopre nulla, chiude. Chiuderli comporta riscrivere le parti di §4.1 che oggi documentano il difetto, in entrambe le lingue.

**Gli item in ambito sono però dieci, non otto**, e i due aggiunti dai giri di gate su questo stesso documento hanno uno statuto diverso che va detto: la mancata validazione dei template (User Story 7) e la stabilità di zona non differenziata (User Story 8) **non** figurano fra i difetti rinviati che il whitepaper inventaria. Il primo è anzi il contrario: il §6.2 pubblica come vera la proprietà che il caricatore non ha. Per questi due il work item scopre e chiude insieme, e la riscrittura tocca anche il §6.2 e la voce di §4.1.5 sulla stabilità di zona.

**Vincolo di sequenza non negoziabile**: nessuna modifica al codice prima che la spec di design emendata abbia superato il proprio ciclo di convergenza avversariale. L'ordine inverso — correggere il codice e poi allineare la spec — è precisamente ciò che ha prodotto questi difetti.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - La trasmissione intergenerazionale è un processo stocastico, non una media pesata (Priority: P1)

Un ricercatore fa girare una simulazione per molte generazioni e osserva come si distribuiscono nella popolazione i caratteri che passano di padre in figlio. Oggi ogni distribuzione si restringe generazione dopo generazione, e in alcuni casi collassa su un unico valore: la società simulata diventa progressivamente omogenea, e nessun risultato che dipenda dalla varianza di quei caratteri resta interpretabile.

**IL DIFETTO È PIÙ AMPIO DI COME LA PRIMA STESURA LO DESCRIVEVA, ma il secondo giro l'ha descritto male a sua volta.** I meccanismi di trasmissione intergenerazionale sono **sei**, non quattro, e solo tre sono in ambito, e si dividono così:

| meccanismo | innovazione | difetto | in ambito? |
|---|---|---|---|
| kernel poligenico dei tratti | **sì** | residuo scalato male: 0,0675 dove ne servirebbero 0,1382 | sì |
| regressione dell'istruzione | **no** | contrazione deterministica: collassa a un punto | sì |
| regressione di classe alla Clark | **no** | si congela: mobilità **esattamente zero** dalla 2ª generazione | sì |
| mobilità alla Becker-Tomes | **sì** | nessuno trovato | no |
| regola meritocratica | no | **ereditato**: si risana riparando istruzione e intelligenza | no |
| successione di classe patrilineare rigida | no | **nessuno: la rigidità È il modello** che le fonti descrivono | no |

Due meccanismi possiedono un termine di innovazione, non uno solo; e il kernel poligenico è fra questi. La stesura precedente scriveva che solo Becker-Tomes ne ha uno, il che contraddiceva i propri stessi numeri: un meccanismo senza nulla che rigeneri la dispersione va a **zero**, come infatti fa l'istruzione, mentre il kernel si assesta al 48,8% proprio perché qualcosa la rigenera. La regola meritocratica, poi, non calcola una media fra un genitore e un riferimento: deriva la classe dai tratti già ereditati del figlio, quindi una volta riparati istruzione e intelligenza la sua distribuzione torna non degenere da sola, e chiederne una correzione separata sarebbe sovradimensionare l'ambito.

**Il difetto della regressione di classe non è un collasso di dispersione, ed è il secondo errore di descrizione.** Misurata, non collassa affatto: l'arrotondamento a etichette intere la congela in **una** generazione su una partizione fissa, che resta bit-identica per le otto successive. Il difetto è l'opposto di un collasso — è **mobilità intergenerazionale nulla**, una partizione deterministica immobile, in una regola citata a una fonte la cui tesi centrale è che lo status regredisce lentamente ma in misura strettamente non nulla.

Il peggiore non è quello per cui il work item era nato. **La regressione dell'istruzione non riceve nemmeno un generatore casuale**: è una contrazione deterministica pura, e il suo punto fisso non è una dispersione ridotta ma **zero**. Misurato su 20.000 agenti per otto generazioni, partendo da una dispersione di 0,150, ai valori di regressione effettivamente spediti dai template:

| regressione | gen 2 | gen 4 | gen 8 |
|---|---|---|---|
| 0,5 (le due ere pre-industriali) | 0,0187 | 0,0023 | 0,00004 |
| 0,4 (industriale, moderna) | 0,0121 | 0,0010 | 0,00001 |
| 0,2 (sci-fi) | 0,0030 | 0,0001 | 0,000000 |

Ogni agente converge su 0,3, il valore di ripiego usato perché nessun template dichiara la chiave corrispondente. Le conseguenze si propagano: la regola di classe meritocratica calcola il merito come media di intelligenza e istruzione, quindi dopo poche generazioni nell'era sci-fi la classe sociale diventa funzione della sola intelligenza; e il punteggio di omogamia pesa l'istruzione fra il 25% e il **40%** a seconda dell'era — verificato sui template: 0,25 nelle due pre-industriali, 0,30 nell'industriale e nella sci-fi, 0,40 nella moderna — quindi da un quarto a due quinti del criterio di accoppiamento si spegne, con l'era moderna la più colpita. (Il "quarto" che circolava è il valore di ripiego nel codice, non quello spedito: è la terza volta in questo documento che un default è stato letto come valore effettivo.) La regressione di classe alla Clark ha la stessa forma deterministica, ed è citata a una fonte che descrive la lenta regressione dello status **dentro una distribuzione stazionaria** — una contrazione senza rumore non la riproduce, la cancella.

Questa equazione è già pubblicata come parte dei Metodi sottoposti ad audit nel capitolo §4.1.4 del whitepaper, e il blocco delle semplificazioni di quel capitolo, che inventaria i difetti rinviati, non la nomina.

**Why this priority**: è il difetto che altera di più gli esiti simulati e l'unico che porta una distribuzione a un punto. Correggere solo il kernel poligenico lascerebbe una società in cui i tratti mantengono la loro varianza mentre istruzione e classe si omogeneizzano — non una correzione parziale, ma un modello nuovo e più strano di quello di partenza. Assorbe i rilievi 1, 2 e 7 dell'audit di codice più i tre meccanismi che quell'audit non poteva vedere, perché confrontava il codice col design e non il design con la scienza.

**Independent Test**: far girare una popolazione sintetica per otto generazioni per **ciascuno dei tre meccanismi in ambito**, con parametri noti, verificando la dispersione per i due caratteri continui e la mobilita intergenerazionale per la regola di classe; verificare separatamente che la somiglianza genitore-figlio su un solo genitore noto sia la metà di quella su due.

**Acceptance Scenarios**:

1. **Given** una popolazione con ereditabilità 0.55 e ampiezza d'era 0.15, **When** la si fa evolvere per otto generazioni, **Then** la dispersione dei tratti resta entro la tolleranza dichiarata invece di stabilizzarsi al 48,8%.
2. **Given** la regressione dell'istruzione a uno qualsiasi dei tre valori spediti, **When** la si fa evolvere per otto generazioni, **Then** la dispersione resta entro la tolleranza dichiarata invece di collassare a zero.
3. **Given** la regressione di classe, **When** la si fa evolvere per otto generazioni, **Then** la mobilita intergenerazionale e strettamente positiva a regime, contro lo zero esatto misurato oggi dalla seconda generazione.
4. **Given** un figlio con un solo genitore noto di valore 0.9, **When** se ne calcola il tratto, **Then** il coefficiente applicato è la metà di quello del caso a due genitori, e la documentazione afferma questo e non altro.
5. **Given** un'era qualsiasi fra le cinque, **When** si risolve la distribuzione di rumore usata alla nascita, **Then** i suoi parametri provengono da una fonte dichiarata per quell'era e per quel tratto.

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

**Le magnitudini, misurate direttamente e non ereditate dai report.** Il tasso di non-esattezza dipende dall'aliquota **e dalla distribuzione degli importi**, che va dichiarata insieme al numero: su patrimoni uniformi fino a un milione vale **16,1% ad aliquota 0,15, 6,0% a 0,40, e 0% ad aliquota nulla — che è quella di tre template su cinque**; su altre distribuzioni degli importi lo stesso tasso si muove di un paio di punti, quindi il difetto non si manifesta affatto nelle due ere pre-industriali né in quella sci-fi. L'errore relativo massimo è **1,9·10⁻¹⁶**, cioè un ulp, non l'ordine di grandezza superiore che una lettura frettolosa del round 1 suggeriva: quel report riportava 1,16·10⁻¹⁰ come errore **assoluto** su un patrimonio di mezzo milione. La cifra "circa un caso su cinque" che circolava non e riproducibile sulle aliquote spedite; e raggiungibile solo estraendo l'aliquota stessa da una distribuzione, il che non e il regime in cui il modello opera.

**Why this priority**: la magnitudine è di un ulp e in tre ere su cinque il difetto è assente, quindi l'impatto sugli esiti è nullo. Resta però che il modulo **afferma** un invariante di conservazione esatto e non negoziabile, portante per l'impianto contabile del whitepaper, mentre uno dei suoi due passaggi aritmetici non lo rispetta. Si corregge perché l'affermazione deve essere vera, non perché i numeri cambino.

**L'esattezza è raggiungibile, ma NON dalla costruzione che la prima stesura di questa spec prescriveva.** Quella stesura diceva di calcolare il residuo e derivare l'imposta per differenza, certificandolo con zero fallimenti su 200.000 prove. La certificazione era presa solo alle aliquote spedite, tutte pari o inferiori a 0,40. La funzione però accetta per contratto qualunque aliquota fino a 1,0, e su quel dominio la costruzione si rompe **esattamente sopra un mezzo**: misurato, 0,50% a 0,51, 3,52% a 0,55, 6,05% a 0,60, 12,68% a 0,70. La ragione è strutturale: finché il residuo è almeno metà del totale, il lemma di Sterbenz rende la sottrazione esatta; oltre quella soglia non si applica più. E l'errore assoluto massimo che la costruzione produce è 1,164·10⁻¹⁰ — **precisamente la magnitudine che questa stessa spec liquidava come artefatto mal etichettato del vecchio report.** Il rimedio prescritto riproduceva il difetto, fuori dal campione su cui era stato misurato.

**Questa spec non prescrive più una costruzione.** Il requisito è la proprietà — conservazione esatta su tutto il dominio che la funzione accetta — e la scelta della tecnica spetta al design emendato, come per ogni altra correzione di questo work item. Si registra soltanto che una costruzione esatta su tutto il dominio esiste, verificata a zero fallimenti su 200.000 prove per aliquota fino a 0,99, e che deriva per differenza sempre il **minore** dei due termini, così che il lemma si applichi da entrambi i lati. Si registra anche, come monito, che il rimedio proposto dal round 1 dell'audit di codice (`residuo = totale − imposta`) non raggiunge l'esattezza nemmeno alle aliquote spedite. **Una precisazione dovuta**: a 0,40 quel rimedio e la costruzione attuale danno lo stesso identico verdetto di conservazione su ogni patrimonio provato, quindi le due percentuali che una stesura precedente riportava come distinte per la stessa aliquota descrivevano in realtà lo stesso comportamento. Il punto che regge è qualitativo e non dipende dalla cifra: nessuno dei due raggiunge l'esattezza.

**Independent Test**: liquidare molti patrimoni di importo casuale a ciascuna delle aliquote effettivamente spedite dai template, e verificare che imposta più residuo eguagli esattamente il patrimonio.

**Acceptance Scenarios**:

1. **Given** un patrimonio e una qualsiasi delle aliquote spedite, **When** si applica l'imposta, **Then** imposta più residuo eguaglia esattamente il patrimonio.
2. **Given** la documentazione della funzione, **When** la si legge, **Then** la garanzia dichiarata è quella che il codice offre davvero, e dichiara rispetto a quale ordine di somma vale.

---

### User Story 5 - La spec di design smette di contraddirsi sull'orizzonte di sopravvivenza (Priority: P2)

Un agente affamato decide se fuggire. Oggi la condizione confronta la sua ricchezza accumulata con il costo di sussistenza di un singolo tick: un agente con trenta tick di risparmi è trattato come uno che ne ha uno solo.

**NON è una semplificazione non dichiarata, e non è nemmeno solo una contraddizione fra due righe: la riga che dovrebbe dettare la convenzione è essa stessa incoerente.** Verificato leggendola per intero: la riga 153 del design scrive *"I confronti di ricchezza usano `agent.wealth < N * subsistence_threshold` dove `N` è il numero di tick di sussistenza che l'agente può sopravvivere con i risparmi attuali (parametro di design tunable, default 30 tick ≈ 1 mese)"*. La glossa e la parentesi definiscono due oggetti incompatibili. Se `N` è "il numero di tick che l'agente può sopravvivere coi risparmi attuali", allora `N = ricchezza / soglia` e la condizione si riduce a `ricchezza < ricchezza`, che non è mai vera. Se `N` è un parametro globale con default 30, la glossa dice il falso su che cosa `N` denoti. La riga 841 scrive poi la condizione di fuga senza `N`, e il codice segue la 841.

Questo cambia di nuovo il rimedio. Non basta scegliere fra riga 153 e riga 841, perché **la riga 153 va riscritta comunque**, qualunque modello il gate scelga: non fornisce una convenzione a cui allineare la 841.

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

### User Story 7 - Il caricatore dei template rifiuta ciò che il whitepaper dichiara rifiutato (Priority: P2)

Chi scrive un template d'era si aspetta che un refuso in un nome di sezione, un'aliquota espressa in punti percentuali invece che in frazione, o un'ereditabilità fuori scala vengano respinti al caricamento. Il whitepaper lo afferma esplicitamente: *"lo schema JSON è deliberatamente stretto: ogni chiave è consumata da un modello specifico del §4.1, nessun campo di estensione non tipizzato è accettato, e una chiave sconosciuta al caricamento solleva un errore di validazione anziché essere ignorata silenziosamente."*

**È falso, verificato eseguendo il validatore.** Gli ho dato un template industriale con una chiave di primo livello inventata, una sezione `era_noize` con refuso, `estate_tax_rate` pari a 40, un'ereditabilità di 5,0 e una regressione dell'istruzione **negativa**. Ha validato tutto pulito: non esiste alcun controllo di chiave sconosciuta, di tipo o di intervallo.

**Why this priority**: è il meccanismo per cui i difetti che questo work item corregge sono potuti passare inosservati. Una sezione `era_noise` richiesta dal design può mancare senza che nulla protesti — ed è esattamente il caso — e i valori di regressione divergenti dalle fonti citate della User Story 6 sono stati spediti senza che nulla li fermasse. Correggere i valori senza correggere il varco che li ha lasciati entrare significa ripetere il difetto alla prossima modifica. In più il whitepaper pubblica come vera una proprietà che il sistema non ha, che è la forma di difetto che la regola di doc-sync del progetto considera peggiore di un capitolo non auditato.

**Independent Test**: sottoporre al caricatore un template con una chiave sconosciuta, uno con un valore fuori intervallo e uno con una sezione richiesta mancante, e verificare che ciascuno venga respinto con un errore che nomina il problema.

**Acceptance Scenarios**:

1. **Given** un template con una chiave di primo livello non prevista, **When** lo si carica, **Then** il caricamento fallisce nominando la chiave.
2. **Given** un template la cui aliquota di successione vale 40 anziché 0,40, **When** lo si carica, **Then** il caricamento fallisce nominando il campo e l'intervallo ammesso.
3. **Given** un template privo di una sezione **annidata** che il design dichiara obbligatoria — il caso reale e `era_noise` — **When** lo si carica, **Then** il caricamento fallisce anziche ricadere silenziosamente su un valore di ripiego. Il livello di annidamento va nominato: verificato che il caricatore respinge gia oggi una sezione di PRIMO livello mancante, quindi uno scenario che non lo precisa non fallirebbe contro il codice attuale.
4. **Given** il capitolo §6.2 del whitepaper, **When** lo si rilegge dopo la correzione, **Then** descrive il comportamento reale del caricatore.

---

### User Story 8 - La stabilità di zona è un segnale di zona (Priority: P3)

Un agente confronta due zone per decidere dove trasferirsi e legge, fra gli altri indicatori, quanto ciascuna sia stabile. Oggi legge lo stesso numero per tutte, perché esiste un solo governo per simulazione.

**È la stessa contraddizione della riga 153, nello stesso capitolo del design.** L'esempio della Sezione 6 stampa tre valori distinti per tre zone — Parigi in crisi a 0,3, la zona corrente stabile a 0,7, la campagna a 0,6 — mentre la clausola di calcolo quattro righe dopo dice che il valore è il campo di stabilità del governo, che è unico per simulazione. Il codice segue la clausola e riporta la costante per ogni zona.

**Why this priority**: l'audit di codice della Plan 3 ha già stabilito che il modello ha bisogno di un segnale realmente per zona, perché una costante riportata per zona non porta informazione e induce il modello linguistico a credere di confrontare le zone su una dimensione su cui sono identiche; e ha registrato che il rimedio prescritto non è stato applicato. È in ambito qui per la stessa ragione per cui le altre storie stanno insieme: emenda la stessa Sezione 6 dello stesso file di design, e lasciarla fuori garantirebbe esattamente il conflitto di merge che quell'argomento vuole evitare. È P3 perché la correzione è nota e la sua implementazione, che richiede uno schema per zona, può essere sequenziata dopo.

**Independent Test**: costruire due zone con condizioni diverse e verificare che il blocco informativo riporti per esse valori di stabilità distinti, oppure che dichiari esplicitamente di riportare un valore di simulazione.

**Acceptance Scenarios**:

1. **Given** due zone in condizioni diverse, **When** un agente ne legge il blocco informativo, **Then** i valori di stabilità sono distinti, oppure il campo è dichiarato come valore di simulazione e non di zona.
2. **Given** la Sezione 6 del design emendato, **When** la si rilegge, **Then** l'esempio e la clausola di calcolo concordano.

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
- **FR-002**: la dispersione stazionaria dei tratti prodotta dal kernel poligenico MUST eguagliare l'ampiezza d'era dichiarata — dove la spec emendata MUST prima chiarire quale delle due letture oggi compresenti nel codice sia quella intesa, se l'ampiezza del rumore ambientale o l'ampiezza fenotipica della popolazione, che sotto la forma correttiva pubblicata differiscono di un fattore 0,921, entro una tolleranza che la spec emendata MUST fissare **numericamente** e che MUST NOT contenere il valore attuale. Questo è il vincolo portante dell'intero work item e la stesura precedente lo aveva perso: misurato, il kernel odierno si assesta al **48,8%** dell'ampiezza dichiarata.
- **FR-002b**: la regressione dell'istruzione e la regressione di classe alla Clark MUST possedere un termine di innovazione, perché entrambe sono citate a fonti che descrivono una società mobile e oggi non lo sono: la prima collassa a un punto, la seconda si congela a mobilità zero. **Il requisito NON si estende a due meccanismi, e la distinzione è sostanziale**: la regola di successione di classe patrilineare rigida è una copia deterministica dell'etichetta paterna, ed è la regola delle due ere pre-industriali proprio perché la sua rigidità **è** il modello che le sue fonti descrivono — imporle un'innovazione contraddirebbe le fonti citate; e la regola meritocratica non media un genitore contro un riferimento ma deriva la classe dai tratti già ereditati del figlio, quindi riparare istruzione e intelligenza la risana da sé, come la User Story 1 stabilisce.

> **Perché FR-002 e FR-002b sono separati, e perché il primo esiste.** La stesura precedente li fondeva in un unico requisito che chiedeva "un processo stocastico con distribuzione stazionaria non degenere". **Il kernel attuale, non riparato, soddisfa quel requisito**: estrae davvero un valore casuale e la sua distribuzione stazionaria non è degenere — è soltanto larga la metà di quanto dichiara. Allargando il requisito ai quattro meccanismi si era perso il morso su quello per cui il work item è nato, e un piano scritto contro quella formulazione avrebbe potuto consegnare un emendamento che lascia il kernel dov'è superando ogni gate. È lo stesso errore che questa spec aveva già identificato e corretto per SC-006 nel giro precedente — un criterio che non fallisce dove il requisito è falso — applicato alla periferia e perso al centro.
>
> **Attenzione a un test che sembra discriminante e non lo è.** L'ereditabilità realizzata, misurata come regressione del figlio sul valore medio dei genitori, al punto fisso collassato vale **0,5509 contro 0,55 dichiarato**: la recupera esattamente. Il collasso colpisce la varianza, non la pendenza. Qualunque criterio formulato sull'ereditabilità realizzata passa oggi e non serve a nulla.
- **FR-002a**: la spec emendata MUST scegliere la **famiglia distribuzionale** dei caratteri trasmessi — tratti **e istruzione**, che ha lo stesso troncamento a `[0,1]` e lo stesso problema — e MUST motivare la scelta. Verificato: il modello estrae oggi da una normale non limitata un carattere che il codice tronca, e il troncamento non costa quasi nulla quando la media d'era è centrata (**99,9%** dell'obiettivo a media 0,5) ma cala al 92,0% con una media d'era di 0,8, dove cade a 1,33 deviazioni standard. **Nessun tratto ha oggi una media d'era di 0,8**: quel valore è il default di campo di due attributi che regrediscono comunque verso 0,5, e la configurazione a 0,8 nascerebbe soltanto *dopo* che FR-004 avrà risolto le medie per tratto. È quindi un rischio introdotto da una delle correzioni, non una condizione attuale. **La tensione fra conservare la varianza e risolvere le medie per tratto NON è un compromesso fra due proprietà scientifiche: è la conseguenza di una famiglia distribuzionale sbagliata per una variabile limitata.** Chiedere al gate quale proprietà sacrificare produrrebbe la ratifica sbagliata. Le alternative da valutare esplicitamente sono almeno una Beta, una normale logit-trasformata, e una normale troncata con adattamento dei momenti perché l'ampiezza dichiarata sia quella realizzata.
- **FR-003**: il caso a genitore singolo MUST applicare il coefficiente di regressione che la fonte citata prescrive, e la documentazione MUST descrivere ciò che il codice fa. Il requisito MUST coprire **la scala del residuo in tutti e tre i rami di parentela**: la forma correttiva già pubblicata nel whitepaper la deriva per il solo caso a due genitori, e implementata alla lettera negli altri misura il 95,8% dell'obiettivo con un genitore noto e il **92,1% con nessuno dei due** — il ramo peggiore, che nessuna stesura precedente aveva quantificato. Attenzione a non confondere quest'ultimo numero con la cifra del troncamento di FR-002a, che coincide numericamente ma nasce da un meccanismo diverso: la spec emendata MUST tenerli distinti.
- **FR-004**: i parametri della distribuzione di rumore MUST essere risolti per era e per carattere da una fonte dichiarata, oppure MUST essere dichiarati come parametri di progetto tarabili con la loro giustificazione, non come segnaposto interinali. **Lo scopo copre anche i caratteri che oggi non hanno alcun parametro di rumore perché non sono stocastici**: l'istruzione e la classe alla Clark ne avranno bisogno per soddisfare FR-002b, e nessuno dei due esiste oggi — l'istruzione vive sotto `social_inheritance`, non fra i tratti ereditabili, quindi una lettura ristretta di questo requisito lascerebbe FR-002b senza il parametro che gli serve. La sola mobilità alla Becker-Tomes ha già la propria ampiezza di innovazione con la sua giustificazione misurata, e va presa a modello.
- **FR-005**: la quota coniugale nella regola successoria islamica MUST dipendere dal genere del coniuge superstite: **vedovo 1/2 senza figli e 1/4 con figli, vedova 1/4 senza figli e 1/8 con figli** (oggi il codice applica 1/4 e 1/8 a entrambi). La fonte primaria di queste quattro quote è **il Corano 4:12**, e la spec emendata MUST citarla come tale, mantenendo Powers (1986) come apparato accademico: la costituzione del progetto impone la fonte primaria dove è accessibile, e citare oggi Powers per la struttura è precisamente il difetto che questa user story corregge. MUST inoltre definire il trattamento del coniuge non binario coerentemente con quanto la spec già stabilisce per i figli nella ripartizione residuale.
- **FR-006**: il guadagno atteso di migrazione MUST avere tutti i termini nella stessa unità, e la decisione migratoria MUST essere invariante rispetto alla scala della valuta. **NON è sufficiente monetizzare il costo distanza**, perché ciò produce una quantità monetaria contro termini che sono tassi. Il bilanciamento richiede un orizzonte di pianificazione, e la spec emendata **MUST NOT trattarlo come un parametro libero da nominare**: l'economia della migrazione lo deriva. **Todaro (1969) è la fonte più vicina**, perché il modello da riparare è proprio Harris-Todaro e la formulazione di Todaro enuncia già la decisione del migrante come valore attuale del flusso di reddito atteso su un orizzonte di pianificazione, scontato; Sjaastad (1962) resta la fondazione più generale della migrazione come investimento, con l'orizzonte pari alla vita lavorativa residua attesa. Mandare il design a cercare altrove un orizzonte che il modello citato porta già con sé sarebbe la stessa forma di attribuzione approssimativa che la User Story 2 esiste per correggere. La spec emendata MUST istanziare quel quadro, oppure motivare esplicitamente perché se ne discosta. Soddisfare il requisito dimensionale nominando un numero passerebbe FR-006 e violerebbe la regola del progetto per cui nessuna formula esiste senza una fonte primaria citata.
- **FR-007**: il passaggio d'imposta di successione MUST conservare il valore esattamente **su tutto il dominio di aliquote che la funzione accetta**, non solo su quelle spedite dai template. Coerentemente con il resto di questo documento, il requisito enuncia la proprietà e **non prescrive la costruzione**: la scelta della tecnica spetta al design emendato. Si registra soltanto che una costruzione esatta sull'intero dominio esiste e che due candidati non lo sono — il rimedio del round 1 e quello prescritto dalla prima stesura di questa spec, quest'ultimo esatto solo fino ad aliquota 0,5.
- **FR-008**: la spec di design MUST riscrivere la riga 153, che è internamente incoerente: la sua glossa definisce `N` come il numero di tick che l'agente può sopravvivere coi risparmi attuali, il che ridurrebbe la condizione a `ricchezza < ricchezza`, mentre la sua parentesi lo definisce come parametro globale con default 30. La riscrittura MUST scegliere esplicitamente fra un test di fame e un test di risparmio precauzionale, dichiarare l'interazione con `flight_trigger_ticks`, e la scelta MUST essere applicata a **tutti** i consumatori della soglia di sussistenza, inclusa la modulazione della fertilità.
- **FR-009**: ogni parametro dei template MUST corrispondere al valore attribuito alla sua fonte, oppure la divergenza MUST essere dichiarata con la sua ragione. **L'attribuzione stessa MUST essere verificata prima di diventare il bersaglio**: la spec di design cita Chetty et al. (2014) in due punti per due grandezze diverse — un intervallo di elasticità del reddito e un coefficiente di persistenza dell'istruzione — e allineare i dati spediti a un'attribuzione errata non sarebbe una correzione.
- **FR-010**: il capitolo §4.1 di ENTRAMBI i whitepaper MUST essere aggiornato nello stesso work item, sostituendo la dichiarazione del difetto con la descrizione del modello corretto, e MUST dichiarare la non comparabilità fra risultati prodotti prima e dopo. L'aggiornamento MUST includere §4.1.2 (fertilità), che condivide la decisione di FR-008, e MUST correggere l'affermazione secondo cui la monetizzazione del costo distanza ripristina l'equilibrio dimensionale, ovunque essa compaia. MUST correggere allo stesso modo l'altro rimedio errato che il §4.1.4 pubblica — quello secondo cui scrivere il residuo come differenza ridurrebbe il tasso di fallimento al 4,9% — poiché è misurato inadeguato e, all'aliquota più alta fra quelle spedite, del tutto privo di effetto. E MUST correggere il §6.2, per la User Story 7.
- **FR-011**: ogni correzione MUST essere coperta da un test che fallisce contro il comportamento attuale, verificato per mutazione e non per sola ispezione.
- **FR-012**: il lavoro MUST dichiarare quali benchmark di calibrazione cambiano esito e perché il nuovo esito è quello corretto. **Nota di stato verificata**: nessun benchmark di calibrazione demografica eseguibile esiste oggi nella suite — quelli previsti sono tracciati come lavoro futuro — quindi il requisito vincola i benchmark da scrivere, non un insieme esistente.
- **FR-013**: la spec emendata MUST dichiarare l'assunzione di accoppiamento su cui poggia l'obiettivo di varianza, **in tutte e cinque le ere e non nella sola sci-fi**. Verificato: il punteggio di omogamia pesa l'istruzione fra 0,25 e 0,40 in ogni template. Oggi quell'accoppiamento è inerte perché l'istruzione è di fatto una costante — ma **è FR-002b a risvegliarlo**: restituendole dispersione si crea correlazione fra i genitori su un carattere trasmesso ovunque, non solo dove la regola meritocratica lega la classe all'intelligenza. La correzione crea da sé la condizione che viola l'assunzione su cui il proprio obiettivo poggia, e la spec emendata MUST trattare il caso invece di assumere accoppiamento casuale.
- **FR-014** *(dipende da FR-004)*: se FR-004 risolve i parametri di rumore come sezione dichiarata nei template, allora quella sezione diventa il caso di prova di questo requisito; se invece li risolve come parametri di progetto, `era_noise` non nascera' mai e il requisito va provato su un'altra sezione obbligatoria. La dipendenza va sciolta prima di scrivere i test. Il caricatore dei template MUST respingere chiavi sconosciute, valori fuori intervallo e sezioni obbligatorie mancanti, e il capitolo §6.2 del whitepaper MUST descrivere il comportamento reale. Verificato eseguendo il validatore: oggi accetta una chiave inventata, una sezione con refuso, un'aliquota di 40, un'ereditabilità di 5,0 e una regressione negativa, tutte insieme e senza protestare, mentre il whitepaper dichiara il contrario.
- **FR-015**: la stabilità riportata per zona nel blocco informativo di migrazione MUST essere un segnale realmente di zona, oppure MUST essere dichiarata come valore di simulazione; e la Sezione 6 del design MUST far concordare il proprio esempio con la propria clausola di calcolo.

### Key Entities

- **Spec di design demografia**: `docs/superpowers/specs/2026-04-18-demography-design-it.md`, dichiarata CONVERGED nell'aprile 2026. È l'artefatto che questo work item emenda; le sue sezioni 4, 5 e 6 sono quelle toccate.
- **Template d'era**: i cinque file che dichiarano i parametri per era. Portano i valori di ereditabilità, di regressione dell'istruzione e le regole successorie.
- **Capitolo §4.1 dei whitepaper**: nelle due lingue, oggi documenta gli otto difetti come veri del modello. Va riscritto quando cessano di esserlo.
- **Report d'audit di fase 6**: i quattro report della Plan 3, che contengono l'evidenza misurata di ciascun difetto e sono il punto di partenza dell'emendamento.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: la spec di design emendata raggiunge un verdetto CONVERGED esplicito in un ciclo di audit avversariale, con zero rilievi INCORRECT e zero UNJUSTIFIED residui.
- **SC-002**: in una popolazione simulata per almeno otto generazioni, la dispersione stazionaria dei tratti ereditabili è **almeno il 90% dell'ampiezza d'era dichiarata**. Il valore attuale è 48,8% e il criterio deve fallire contro di esso: una soglia agganciata a "la tolleranza dichiarata da FR-002" sarebbe circolare, perché nulla vieterebbe di dichiarare una tolleranza che contiene il 49%. La verifica MUST coprire i tre rami di parentela, non il solo caso a due genitori.
- **SC-003**: **NON usare l'ereditabilità realizzata come criterio.** Misurata al punto fisso collassato vale 0,5509 contro 0,55 dichiarato, quindi passa oggi e non discrimina. Il criterio che sostituisce l'intento originale è SC-002. Questo criterio resta a verbale come avvertenza, perché era presente nelle due stesure precedenti ed è la trappola più naturale in cui ricadere.
- **SC-004**: le quote coniugali della regola islamica valgono 1/2 e 1/4 per il vedovo (senza e con figli) e 1/4 e 1/8 per la vedova, e il trattamento del coniuge non binario è quello dichiarato dalla spec emendata.
- **SC-005**: due simulazioni identiche denominate in valute di scala diversa producono le stesse decisioni migratorie. **Nota**: questo criterio non discrimina fra le formulazioni candidate — è soddisfatto da qualunque monetizzazione — quindi non basta da solo a validare FR-006, che richiede in aggiunta la verifica dimensionale termine per termine.
- **SC-006**: imposta più residuo eguaglia esattamente il patrimonio **su tutto il dominio di aliquote che la funzione accetta**, campionato almeno agli estremi e sopra 0,5, con asserzione di uguaglianza esatta e dichiarando rispetto a quale ordine di somma vale. Un criterio limitato alle sole aliquote spedite non fallirebbe dove il requisito è falso, e sarebbe quindi inutile: è l'errore che la prima stesura conteneva.
- **SC-011** *(caratteri continui: tratti e istruzione)*: fatti evolvere per almeno otto generazioni ai parametri spediti, producono una dispersione stazionaria **almeno pari al 50% di quella iniziale**. Misurato oggi: l'istruzione collassa a 0,00004 e a zero netto, e fallisce.
- **SC-012** *(regole di classe, che producono ranghi discreti)*: la **mobilità intergenerazionale** — la frazione di figli il cui rango differisce da quello del genitore, dove *il genitore* e' quello che le regole di classe leggono davvero, cioe' il padre con ricaduta sulla madre se assente, come risolve `_resolve_parent_rank` — è **strettamente positiva a regime**, per ogni regola la cui fonte citata descrive una società mobile. Misurato oggi: la regressione alla Clark vale **esattamente 0,0000** dalla seconda generazione in poi, la mobilità alla Becker-Tomes 0,58.

> **Perché due criteri e non uno, e perché il primo da solo era sbagliato.** La stesura precedente applicava un'unica soglia di dispersione a tutti i meccanismi. È un errore di grandezze incommensurabili, e produce esattamente il difetto che questo documento ha già rifiutato due volte: **una soglia di dispersione certifica come sana la regressione di Clark**, la cui dispersione resta una frazione cospicua di quella della popolazione fondatrice mentre la sua mobilità è zero — **misurata per via esatta vale il 63,2%**, non il 90,8% che una prima stesura riportava: la mappa deterministica riduce il supporto a tre ranghi su cinque, dove la dispersione massima è il 70,7% di quella di una uniforme — cioè mentre porta intatto il difetto per cui FR-002b esiste. Nella direzione opposta la stessa soglia condanna la regola meritocratica, che misura il 33% oggi e resterebbe al **47%** anche dopo tutte le correzioni che questo work item impone, perché il merito è la media di due variabili di ampiezza 0,15 proiettata su una scala di ranghi la cui dispersione di riferimento nasce da una partizione per percentili di ricchezza che quella regola non tocca. Una soglia irraggiungibile e un criterio che non morde dove serve, nello stesso criterio.
- **SC-007**: ogni valore parametrico dei cinque template coincide con quello attribuito alla sua fonte, oppure porta una divergenza dichiarata.
- **SC-008**: il capitolo §4.1 di entrambi i whitepaper non contiene più la dichiarazione degli otto difetti come veri, e dichiara la discontinuità dei risultati.
- **SC-009**: l'audit di fase 6 sul codice raggiunge un verdetto CONVERGED esplicito.
- **SC-010**: la suite di progetto resta verde, senza test disabilitati o marcati xfail per accomodare le correzioni.
- **SC-013** *(copre FR-003)*: la somiglianza genitore-figlio misurata su un solo genitore noto è la metà di quella misurata su due, e la dispersione stazionaria rispetta la soglia di SC-002 in **tutti e tre** i rami di parentela — misurato oggi 95,8% con un genitore e 92,1% con nessuno, contro una scala del residuo derivata per il solo caso a due genitori.
- **SC-014** *(copre FR-008)*: la condizione di fuga e il segnale di ricchezza della fertilità applicano la stessa convenzione di orizzonte, e due agenti con pari ricchezza corrente ma orizzonti di sopravvivenza diversi ricevono esiti diversi — oggi ricevono lo stesso, perché l'orizzonte è implicitamente di un tick.
- **SC-015** *(copre FR-014)*: il caricatore respinge, nominando il campo, un template con una chiave di primo livello inventata, uno con una **sezione annidata** obbligatoria mancante, e uno con un valore fuori intervallo. Verificato che oggi il caricatore respinge gia' diverse assenze, comprese tre annidate sotto `mortality`: non e' quindi il livello di annidamento a discriminare ma l'IDENTITA' della sezione, ed e' `era_noise` — mai controllata — il caso reale. Il criterio resta congiuntivo e fallisce oggi grazie agli altri due casi, entrambi accettati.
- **SC-016** *(copre FR-015)*: due zone in condizioni diverse ricevono valori di stabilità distinti nel blocco informativo, oppure il campo è dichiarato di simulazione e non di zona; oggi ricevono lo stesso valore senza che nulla lo dichiari.

## Criteri sostitutivi recepiti dall'emendamento di fase 0

L'emendamento di fase 0 a `docs/superpowers/specs/2026-04-18-demography-design-it.md`, sezione A12, ha dimostrato per misura che diversi criteri qui sopra **non falliscono contro i modelli difettosi che devono escludere**. Si recepiscono qui i sostitutivi. **Dove questa sezione contraddice i criteri numerati sopra, prevale questa sezione**; i criteri superati restano a verbale come storia, non come cancelli.

- **SC-002a** *(sostituisce SC-002, SC-011 e la clausola di dispersione di SC-013)* — sonda a due punti sul percorso **pre-troncamento**: fissato il segnale, `(T(z₁) − T(z₂)) / ((z₁ − z₂)·s_T)` eguaglia `c_ramo(coeff)` entro `1·10⁻¹²` relativi, per ogni carattere trasmesso — **i tredici tratti e l'istruzione** — e per ciascuno dei tre rami, con `coeff` pari a `h²` per i tratti e `ρ` per l'istruzione, `|z₁ − z₂| ≥ 1`, ed entrambe le valutazioni strettamente interne a `[0,1]` **oppure** l'implementazione espone il valore pre-troncamento. Esatto, non campionario. **Motivo della sostituzione**: la soglia del 90% di SC-002 e quella del 50% di SC-011 sono superate dal modello che viola FR-003 — misurato 95,82% con un genitore e 92,13% con nessuno, e 79,0% per il kernel difettoso odierno a `h² = 0,22`.
- **SC-002b** *(osservabile, NON un cancello)* — l'ampiezza stazionaria realizzata è **misurata e riportata**, su almeno 5.000 individui per generazione e otto generazioni, per ciascuno dei tre rami su popolazioni sintetiche costruite per quel ramo, insieme alla correlazione fra i genitori e al bersaglio che la correzione di A4 implica. **Motivo della demozione**: una banda del 95-105% non è riparabile scegliendo il bersaglio. Sul bersaglio corretto il margine al pavimento della regione ammissibile è zero e un'implementazione corretta esce dalla banda a `r = 0,2`; sul bersaglio non corretto la stessa implementazione supera il 105% a `r = 0,54` per i tratti. Ed essendo campionario, a 5.000 individui una coppia posta al pavimento cade fuori banda nel 49% delle repliche. Il discriminante è SC-002a, che è esatto.
- **SC-012a** *(sostituisce SC-012)* — `σ_clark` eguaglia entro `1·10⁻¹²` la radice di `dispersione_realizzata(σ_clark) = s_rank`, ottenuta per punto fisso da vettore iniziale uniforme, con `s_rank ∈ [0,95, 1,39]`. **Motivo**: "mobilità strettamente positiva" è soddisfatta da qualunque rumore non nullo, e una banda del 5% ammetterebbe il 102,26% che si ottiene leggendo la formula invece di risolverla.
- **SC-013** — resta valida nella sola clausola sul coefficiente del ramo singolo, che è esatta e discrimina.
- **SC-014a** *(sostituisce SC-014)* — i due consumatori della soglia di sussistenza applicano la stessa definizione di orizzonte, verificato **per mutazione** cambiandola in un solo consumatore. **Motivo**: SC-014 non fallisce oggi, perché la soglia è già per zona, e presuppone l'esito della deliberazione che dovrebbe verificare.
- **SC-015a** *(sostituisce SC-015)* — il caricatore respinge, nominando il campo, **ciascuna delle sei clausole del contratto di A9**: chiave sconosciuta, valore fuori intervallo, sezione annidata obbligatoria mancante, voce per carattere mancante, coppia fuori regione ammissibile, incoerenza fra sezioni. **Motivo**: SC-015 non fallisce contro una sezione `era_noise` presente ma vuota.
- **SC-017** *(nuovo, copre l'accoppiamento assortativo)* — la correlazione fra i genitori sul carattere trasmesso è misurata e riportata, insieme all'ampiezza realizzata e al bersaglio che la formula di A4 implica per essa. Nessuno dei due entra in un cancello: servono a rendere visibile quanto l'accoppiamento sposti la varianza, non a bocciare.
- **SC-018** *(nuovo, copre la guardia di ripiego)* — l'attivazione della guardia emette un warning che nomina il carattere, verificato per mutazione inserendo un carattere non dichiarato.
- **SC-019** *(nuovo, copre FR-006)* — il fattore di annualità eguaglia `(1 − e^{−r_anno·H_anni})·(8760/tick_duration_hours)/r_anno` entro `1·10⁻¹²` **relativi**, per **almeno due valori distinti** di `tick_duration_hours`. Il criterio è sul **fattore**, non sul guadagno: il guadagno non è invariante al cambio di durata del tick, quindi un criterio di invarianza certificherebbe la mutazione che fissa 24 ore nel codice e boccerebbe l'implementazione corretta.

**Regola generale**: ogni criterio va provato **per mutazione** — si inietta il difetto, lo si guarda fallire, si ripristina — mai per sola ispezione.

## Assumptions

- Il gate pesante di fase 2 su questo emendamento è richiesto e sarà eseguito: la spec di design CONVERGED non si riapre senza di esso. Questa è la ragione per cui il work item è separato dalla Plan 3 e non un'appendice di essa.
- Le correzioni cambiano gli esiti numerici della simulazione. L'assunzione è che questo sia accettabile e anzi voluto, perché gli esiti attuali sono scientificamente scorretti; la conseguenza è che i risultati prodotti prima dell'emendamento non sono comparabili con quelli prodotti dopo, e va dichiarato.
- Il lavoro non tocca il cablaggio della demografia nel tick loop, che resta di competenza della Plan 4, né dipende da esso: tutti e otto i difetti sono osservabili e correggibili sui moduli in isolamento.
- **Le magnitudini sono state riverificate, e due erano sbagliate.** Il 48,8% del collasso della varianza regge: ricavato analiticamente e riprodotto in simulazione da due parti indipendenti. Il fattore due sulla quota del vedovo regge. Ma il tasso di non-esattezza della conservazione **non** è "circa un caso su cinque": è 16,1% ad aliquota 0,15, 6,0% a 0,40 e **zero** ad aliquota nulla, che è quella di tre template su cinque; e l'errore relativo massimo è 1,9·10⁻¹⁶, non l'ordine di 10⁻¹⁰ che circolava, perché quella cifra era un errore assoluto su un patrimonio grande. La prima stesura di questa spec riportava entrambe le cifre sbagliate, ereditate senza verifica.
- **Il giudizio del round 1 sulla migrazione non è assunto valido**: è stato verificato ed è errato, come documenta la User Story 3. Questo è il motivo per cui il gate serve davvero su quel punto.
- **Sull'ordine di priorità**: la prima stesura dichiarava un criterio unico, l'impatto sugli esiti simulati, e ne usava tre. Si dichiarano qui tutti e tre, perché sono legittimi ma diversi. La User Story 1 è ordinata per **impatto sul modello**; la 2 per **difendibilità della citazione**, esplicitamente a prescindere dalla magnitudine numerica; la 5 per **gravità di processo**, essendo un difetto della spec CONVERGED oltre che del modello. Si noti inoltre che "impatto sugli esiti simulati" è oggi una misura vuota in senso stretto: la demografia non è cablata nel tick loop, quindi nessuna delle otto cambia un esito **oggi**. L'ordinamento guarda agli esiti che si produrranno quando il Plan 4 la cablerà.
- **Sull'ampiezza del work item, con la decisione presa e non solo registrata**: quattro delle otto user story hanno una correzione già derivata, e per esse il gate registra una decisione anziché deliberarla; le questioni che richiedono deliberazione sono tre — l'orizzonte di pianificazione della migrazione, l'orizzonte di sussistenza con la sua estensione alla fertilità, e la famiglia distribuzionale dei tratti con i parametri per era. La prima stesura si limitava a osservare che, dovendo spezzare, si spezzerebbe lì. **Non si spezza, e la ragione è concreta**: tutte e otto emendano lo stesso file, la spec di design della demografia, e due branch concorrenti con due gate di fase 2 sullo stesso documento entrerebbero in conflitto al merge e sottoporrebbero due volte a gate lo stesso artefatto. Il costo di tenerle insieme è un work item più grande; il costo di separarle è un conflitto strutturale su un artefatto che il progetto tratta come autoritativo. Si tengono insieme.
- **Sull'assenza di una sezione FAQ**, che il workflow del progetto richiede per ogni spec: è deliberata. Il contenuto che la FAQ prescrive — perché X e non Y, alternative considerate, confronto con approcci alternativi — è esattamente il registro che **la spec di design emendata** deve portare, e duplicarlo qui produrrebbe due luoghi dove la stessa decisione vive e diverge. Questo documento stabilisce quali proprietà devono valere; il documento che emenda stabilisce come, e lì la FAQ è obbligatoria.

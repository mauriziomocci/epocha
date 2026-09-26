# Feature Specification: Demografia Plan 4 — inizializzazione, cablaggio, snapshot di popolazione

**Branch**: `20260826-144432-demography-plan4-wiring`
**Creata**: 2026-08-26
**Gate di fase 2**: CONVERGED al round 5, 2026-08-27 (`gate-phase2-round5.md`)
**APPROVATA**: 2026-08-27, ratifica esplicita dell'utente in sessione —
«ratifico la spec del Plan 4, procedi con l'implementazione». È l'evidenza
citabile che il gate pesante di fase 2 richiede e che nessuna skill può
sostituire.

## Il problema

I cinque moduli demografici sono scritti, auditati e coperti da test unitari:
`mortality`, `fertility`, `couple`, `inheritance`, `migration`, per un totale di
quarantatré funzioni pubbliche. Il §4.1 del whitepaper li documenta come Methods.

**Il tick loop non ne chiama nessuno.** L'unico contatto è
`set_avoid_conception_flag`, invocato da `apply_agent_action` quando un agente
sceglie di evitare il concepimento. Nessun agente nasce, nessuno muore di
mortalità demografica, nessun asse ereditario si liquida, nessuno migra.

Questo è lo scarto peggiore che il progetto porti: un modello scientifico
completo, auditato e pubblicato, che **non gira**. La build map lo dichiara da
mesi con la formula «i modelli sono auditati ma il loop non li chiama mai», e
finché resta vero ogni risultato del simulatore descrive una popolazione che non
nasce, non muore e non si sposta.

## Scope

**Plan 4 possiede l'orchestratore di nascita e quello di morte.** Non è «chiamare
cinque moduli»: due moduli su cinque non hanno alcun punto d'ingresso per tick, e
il terzo ne ha uno che si dichiara passo intermedio di un orchestratore che non
esiste. `mortality.py` espone quattro funzioni pure; `fertility.py` dichiara che
«i chiamanti sono responsabili di persistere i cambiamenti di stato»;
`inheritance.py` ha l'entry point per tick del percorso di morte —
`process_inheritance_batch`, «called once per tick» — ma si autodefinisce «THE
PLAN 4 DEATH-PATH ENTRY POINT (orchestrator step 2/3)», cioè si aspetta che i
passi 1 e 3 li scriva questo work item. Nessun codice di produzione emette oggi
un evento di nascita o di morte: il grep su `EventType.DEATH|EventType.BIRTH`
fuori dai test dà zero, contro le due occorrenze del controllo positivo su
`EventType.MIGRATION`.

Quattro parti:

1. **I due orchestratori**, che sono il lavoro vero: chi crea l'agente neonato e
   con quale nome, chi marca il morto, chi emette i due eventi.
2. **Inizializzazione** di una popolazione che soddisfi le precondizioni reali dei
   moduli.
3. **Cablaggio** nel tick loop, in un ordine dichiarato come dato.
4. **Le grandezze demografiche per tick**, cioè lo `PopulationSnapshot` che il
   Plan 1 ha modellato e che nessun codice scrive: è la macchina senza cui la
   validazione storica non è eseguibile.

**Fuori scope**: l'esecuzione dei benchmark (HMD, Wrigley-Schofield, carestia
irlandese, Hajnal), che resta il work item tracciato da
`project_validation_experiments_pending.md`; il cablaggio della migrazione
volontaria nel ciclo decisionale (vedi la sezione dedicata); le calibrazioni che
il whitepaper affida all'etichetta «Plan 4» (vedi la sezione dedicata). Qui si
costruisce ciò che rende eseguibile la validazione, non gli esperimenti.

## User Scenarios & Testing *(mandatory)*

### US1 — La popolazione vive (P1)

Un operatore avvia una simulazione con la demografia attivata dalla chiave
dedicata di FR-008 e, al passare dei tick, vede nascite, morti, formazioni di
coppia, successioni e migrazioni comparire negli eventi.

**Test di accettazione**:
1. Su una simulazione di N tick con la demografia attivata dalla chiave dedicata,
   il registro eventi contiene almeno una nascita e almeno una morte, e la
   popolazione varia.
2. Ogni evento demografico **emesso dagli orchestratori di questo work item**
   porta in payload l'indice del passo nell'ordine dichiarato da FR-003. Gli
   eventi che i moduli auditati emettono al proprio interno
   (`migration.py:1000,1770,1803`, `inheritance.py:3575`) non portano l'indice:
   aggiungerlo richiederebbe di modificarli, contro il Non-goal, e restano
   tracciati dal tipo di evento, che nello schema partiziona già per modulo.
3. Una simulazione **senza** demografia attivata gira esattamente come prima,
   senza errori e senza eventi demografici: il cablaggio non rompe le
   simulazioni economiche.

### US2 — L'ordine del tick è dichiarato e rispettato (P1)

I cinque moduli non sono commutativi. Chi muore in questo tick non deve poter
concepire nello stesso tick; l'asse ereditario di chi muore si liquida dopo che
la morte è registrata; chi valuta la fuga d'emergenza la valuta sul patrimonio
che ha dopo le successioni di questo tick, non su quello di prima.

**Test di accettazione**:
1. L'ordine è **scritto** nel codice come sequenza esplicita, non implicito
   nell'ordine delle chiamate.
2. Un agente che muore al tick T non genera nascite al tick T.
3. La successione di un agente morto al tick T avviene al tick T, dopo la morte.
4. Un agente che eredita al tick T non è valutato per la fuga d'emergenza al
   tick T sul patrimonio precedente all'eredità.
5. Una coppia formata al tick T può concepire a T; una coppia che si separa a T
   non concepisce a T.
6. Ogni proprietà d'ordine sopra è provata **per mutazione**: si scambiano due
   passi e il test diventa rosso.

### US3 — Il contatore di fame esiste (P1)

`evaluate_emergency_flight` prende `consecutive_ticks_under_subsistence` come
argomento perché nessun campo del genere esiste nello schema. È l'obbligo che il
Plan 3 ha lasciato scritto: senza quello storage la fuga d'emergenza non può
scattare in un'esecuzione viva, e il modulo è codice morto.

**Test di accettazione**:
1. Il contatore è persistito, si incrementa quando l'agente è sotto la soglia di
   sussistenza e si azzera quando risale sopra.
2. `process_emergency_flight` legge quel valore invece di riceverlo dal chiamante.
3. Provato per mutazione: un contatore che non si azzera fa fallire un test.

### Edge Cases

- **Template d'era nominato ma inesistente o malformato**: il cablaggio degrada e
  non aborta il tick. I casi sono tre e vanno distinti, perché il sito esistente
  (`apply_agent_action`) li tratta in tre modi diversi: chiave assente in config
  → default applicato a monte (`engine.py:335-337`); file mancante →
  `except FileNotFoundError` con log e skip (`engine.py:350-360`); template
  presente ma non valido → `ValueError` di `load_template`, che oggi finisce
  nell'`except Exception` cieco di `engine.py:361-362`. Il cablaggio nuovo
  degrada **esplicitamente per ciascun caso** — `FileNotFoundError` e
  `ValueError`, con log — e non introduce handler ciechi che ingoiano il resto.
- **Popolazione a zero**: quando l'ultimo agente muore, il tick successivo non
  deve sollevare eccezioni.
- **Costo per tick**: cinque moduli su N agenti possono introdurre N+1 query. Il
  budget va misurato e dichiarato, non scoperto in produzione.
- **Determinismo**: i moduli demografici usano `get_seeded_rng`; il tick loop
  deve passare il seme. Il fallback a zero dell'helper RNG — il debito A-5 del
  whitepaper — non è un rischio di questo percorso: `Simulation.seed` è NOT
  NULL nello schema (`simulation/models.py:35`), nessun sito di creazione può
  ometterlo — lo schema lo impone e sul percorso REST il serializer lo rende
  per giunta obbligatorio in input — e il tick loop gira solo su simulazioni
  persistite, quindi la
  condizione «seme e id entrambi assenti» è strutturalmente impossibile qui. Il
  debito resta tracciato per gli oggetti `Simulation` non salvati costruiti in
  codice.

## Requirements *(mandatory)*

**Gli orchestratori**

- **FR-001**: il **percorso di nascita** è un orchestratore che crea l'`Agent`
  neonato, ne valorizza `birth_tick`, `parent_agent` e `other_parent_agent`,
  chiama `apply_inheritance_at_birth`, e emette un evento di nascita.
- **FR-001a**: il **nome del neonato** è una decisione di requisito, non
  implementativa: viene da una lista per template d'era, non dall'LLM. Un nome
  generato dall'LLM renderebbe la nascita non riproducibile dal seme, che è il
  limite che il whitepaper dichiara per le sole decisioni LLM e che questo work
  item non deve estendere.
- **FR-002**: il **percorso di morte** è un orchestratore che valuta la mortalità,
  marca `is_alive`, `death_tick` e `death_cause`, chiama
  `process_inheritance_batch` e emette un evento di morte.

**L'ordine**

- **FR-003**: l'ordine dei passi è **dichiarato come dato**, non come sequenza di
  istruzioni, ed è ispezionabile da un test.
- **FR-004**: la mortalità precede la fertilità nello stesso tick.
- **FR-005**: **la formazione delle coppie precede la fertilità.** Le coppie si
  formano al tick T dagli intenti di T-1, e la probabilità di nascita è zero
  senza coppia attiva in tre template su cinque, incluso il default: se il passo
  coppia seguisse la fertilità, ogni coppia formata a T non potrebbe concepire
  prima di T+1, un ritardo sistematico su tutta la natalità.
- **FR-005a**: **le separazioni si risolvono prima delle formazioni, ed entrambe
  prima della fertilità**: una coppia che si separa a T non concepisce a T. La
  regola è una sola per tutti gli intenti di coppia: un intento espresso a T-1 ha
  effetto all'inizio di T, prima della finestra di concepimento del tick — la
  stessa semantica di FR-005, applicata simmetricamente. Risolvere le separazioni
  prima delle formazioni rende inoltre lo stato di coppia coerente nel momento in
  cui la formazione lo legge.
- **FR-006**: la successione di un agente segue la sua morte nello stesso tick.
- **FR-007**: la **migrazione forzata segue mortalità e successione** nello
  stesso tick: la valutazione di fuga d'emergenza legge il patrimonio
  post-successione e la popolazione post-morti. Le statistiche di zona del tick
  corrente non sono invece una proprietà d'ordine: `process_emergency_flight` le
  costruisce al proprio interno col tick corrente (`migration.py:1574-1586`),
  quindi sono garantite per costruzione in qualunque posizione del passo.
- **FR-007a**: `dissolve_on_death` **non** entra nell'ordine dichiarato:
  `process_inheritance_batch` lo chiama già per ultimo, deliberatamente.

**Il predicato di attivazione**

- **FR-008**: la demografia è attiva quando la simulazione lo **dichiara
  esplicitamente**, con una chiave dedicata, e quello è **l'unico predicato di
  attivazione** in tutto il work item: ogni scenario, test e criterio di questa
  spec che dice «demografia attiva» intende quella chiave. Non si può usare la
  presenza del template d'era: sette punti del codice di produzione applicano già
  `config.get("demography_template", "pre_industrial_christian")`, quindi oggi
  una simulazione che non dichiara nulla si comporta come una che dichiara il
  default, e il predicato che serve non esiste.
- **FR-009**: una simulazione con la demografia non attiva resta invariata: stesso
  numero di query, nessun evento nuovo, nessun errore.

**Determinismo**

- **FR-010**: ogni fase demografica deriva **un solo** stream RNG per
  `(tick, fase)` e lo condivide fra gli agenti in un ordine di iterazione
  deterministico. Derivarne uno per agente soddisfarebbe la lettera di «RNG
  seminato» e darebbe a ogni agente lo stesso sorteggio uniforme, facendoli
  morire in blocco per soglia d'età invece che indipendentemente. È la regola che
  `migration.py` già applica.
**Lo stato che manca**

- **FR-011**: il contatore di tick consecutivi sotto la soglia di sussistenza è
  **persistito** sull'agente, e il predicato che lo incrementa è **lo stesso** che
  `process_emergency_flight` usa come trigger — `agent.wealth` contro
  `compute_subsistence_threshold` — altrimenti contatore e innesco divergono in
  silenzio. Il passo che aggiorna il contatore è collocato nell'ordine
  dichiarato **dopo la successione e prima della migrazione forzata**, così
  l'incremento legge lo stesso patrimonio post-successione che il trigger di
  fuga legge nello stesso tick.
- **FR-012**: `process_emergency_flight` legge il contatore persistito.
- **FR-013**: l'inizializzazione valorizza **`birth_tick`** per ogni agente, in
  modo coerente con l'età generata, e al suo termine **nessun agente vivo ha
  `birth_tick` NULL**. La ragione: `birth_tick` è l'unica sorgente di
  invecchiamento del progetto. `Agent.age` è scritto una volta alla generazione
  (`world/generator.py:179` e `:398`, dall'output LLM) e non avanza mai; la
  fertilità lo legge come fallback solo quando `birth_tick` è NULL
  (`fertility.py:255-256`). Con `birth_tick` sempre valorizzato l'età deriva da
  un'unica sorgente che avanza, e il fallback congelato non è mai il percorso
  attivo.
- **FR-014**: l'inizializzazione crea **coppie iniziali**. Nessun codice le crea
  oggi, e senza di esse il template di default rende impossibile qualsiasi
  nascita nei primi tick.
- **FR-015**: il tick scrive uno `PopulationSnapshot` per tick con **tutti i
  campi dati del modello** (`demography/models.py:155-176`): `total_alive`,
  `age_pyramid`, `sex_ratio`, `avg_age`, `crude_birth_rate`, `crude_death_rate`,
  `tfr_instant`, `net_migration_by_zone`, `couples_active`,
  `avg_household_size`. Un campo lasciato al default del modello è un campo non
  calcolato, e lo snapshot esiste per la validazione: parziale non serve.

**Costo e documentazione**

- **FR-016**: il blocco demografico **non esegue query per agente vivo**. Il
  costo per evento vitale è invece ammesso, perché è contrattuale nei moduli
  che i Non-goals vietano di riscrivere: `resolve_heirs` costa **fino a** 7
  query per morto per dichiarazione del proprio docstring, e il docstring
  dichiara anche che il costo **varia con la struttura familiare del defunto**
  — zero query aggiuntive per il coniuge quando non c'è coppia attiva, zero per
  la famiglia estesa quando non risulta alcun genitore; la risoluzione di un
  intento di coppia costa una lettura e una scrittura.
- **FR-016a**: il budget per tick è dichiarato come **limite superiore** —
  `a + b·morti + c·intenti + d·fughe`, con i coefficienti fissati nel test al
  proprio **caso peggiore** — e non come uguaglianza. L'uguaglianza sarebbe
  insoddisfacibile dal codice che questo work item non può toccare: `b` non è
  un numero ma un intervallo, quindi due tick con lo stesso numero di morti e
  strutture familiari diverse hanno costi diversi, e un'implementazione
  corretta uscirebbe rossa. Il termine fisso `a` dipende inoltre dal numero di
  **zone**, non dalla popolazione: `compute_subsistence_threshold` esegue due
  query per zona (`demography/context.py`), quindi il numero di zone è tenuto
  fermo in ogni misura di costo, e dichiararlo è parte del budget. **Le nascite
  non hanno un termine proprio** perché costano un numero di query indipendente
  dal loro numero: i neonati e i loro eventi si scrivono in blocco, e
  `apply_inheritance_at_birth` per proprio contratto non salva nulla — muta
  l'oggetto figlio e basta. Il costo delle nascite sta quindi dentro `a`, ed è
  un vincolo sull'implementazione, non un'omissione: una query per nascita fa
  fallire la misura di costo.
- **FR-017**: nello stesso commit del codice, in entrambe le lingue: il
  whitepaper §4.1 documenta gli orchestratori e l'ordine dichiarato, e **ogni
  affermazione che il merge rende falsa viene aggiornata**. L'inventario è
  l'unità di chiusura, voce per voce, ancorato a **sezione più affermazione**
  e mai a numeri di riga, che ogni modifica al whitepaper invalida:

  | Sezione | Affermazione che il merge rende falsa |
  |---|---|
  | Abstract | la campagna empirica di validazione attribuita al Plan 4 |
  | §4.1.1–§4.1.3 | chiusure che rinviano l'integrazione al Plan 4, inclusa in §4.1.3 la modifica di una riga riservata al Plan 4 per il lutto |
  | §4.1.4 | «il modulo non è cablato nel tick loop; `engine.py` è intatto e l'integrazione è un deliverable del Plan 4» |
  | §4.1.5 | nessuna funzione del modulo è invocata dal ciclo di tick live, **e** «il Plan 4 possiede la creazione di quello storage; finché non lo fa, la fuga d'emergenza non può scattare in un'esecuzione viva», che FR-011 e FR-012 rendono falsa nello stesso commit |
  | §4.2 | «a differenza dei moduli di demografia di §4.1.x, l'economia comportamentale è davvero viva nella pipeline per tick» — il confronto si capovolge |
  | §7.4 | la directory `validation/` promessa come deliverable del Plan 4 |
  | §7.5 | la validazione è vincolata a un Plan 4 che comprende anche l'esecuzione della campagna |
  | §9 | la definizione tripartita «Initialisation, Engine integration, and Historical validation», che dopo questo work item non descrive più un work item unico |
  | §10 | l'integrazione nel tick loop come deliverable centrale ancora da fare |
  | §11 | le quattro voci «tick-loop integration deferred to demography Plan 4», rese in italiano «Integrazione tick-loop rimandata al Plan 4 di demografia», **più** l'affermazione che l'integrazione è il deliverable centrale del Plan 4 |
  | §12 | la demografia elencata fra il lavoro non ancora integrato |
  | Appendice B | il vincolo della campagna di validazione al Plan 4 e la directory `validation/` promessa come deliverable |

  **Restano vere e non si toccano** le occorrenze di «Plan 4» che rinviano
  **calibrazioni**: i coefficienti Becker, i parametri di Cagan, credito e
  banche, i dataset e le soglie di §7, l'euristica di Appendice A. Sono ciò che
  la sezione «Plan 4» di questa spec dichiara fuori consegna, e cancellarle
  sarebbe un difetto opposto e uguale.
- **FR-017a**: un grep su `Plan 4` in entrambi i whitepaper è un **innesco di
  revisione, non un cancello**: sui pattern inglesi il file italiano dà zero
  occorrenze, e i pattern che intercettano le voci di §11 sono ciechi sulla
  maggior parte delle altre. La chiusura si dichiara sull'inventario di FR-017,
  e il grep serve solo a scoprire voci che l'inventario non conosce. La build
  map è aggiornata in entrambe le lingue allo stesso checkpoint.

## Success Criteria *(mandatory)*

- **SC-001**: su una simulazione di riferimento nascono e muoiono agenti, e la
  popolazione varia.
- **SC-002**: ogni proprietà d'ordine di FR-004, FR-005, FR-005a, FR-006 e FR-007
  è provata **per mutazione**: si scambiano due passi e il test diventa rosso.
- **SC-003**: il contatore di fame si incrementa e si azzera come prescritto, con
  lo stesso predicato del trigger, provato per mutazione — inclusa la
  collocazione di FR-011: spostare il passo contatore prima della successione fa
  fallire un test su una fixture in cui l'erede risale sopra soglia grazie
  all'eredità del tick.
- **SC-004**: una simulazione con la demografia non attiva esegue **lo stesso
  numero di query** di prima del cablaggio e non produce eventi demografici.
- **SC-005**: due parti, entrambe con i valori attesi scritti nel test e a
  **numero di zone fisso**. **Parte A, uguaglianza**: a eventi vitali pari —
  stesso numero di morti, intenti e fughe, con le stesse strutture familiari, e
  il tick ne contiene almeno uno per tipo, non zero — raddoppiare gli **agenti
  vivi** lascia il conteggio di query del blocco demografico **identico**.
  Un'implementazione con query per agente vivo diventa rossa al raddoppio, e il
  criterio resta raggiungibile perché il costo per evento è invariato fra le
  due misure. **Parte B, limite superiore**: a popolazione fissa, facendo
  variare gli eventi, il conteggio misurato non supera mai
  `a + b·morti + c·intenti + d·fughe` ai coefficienti di caso peggiore
  dichiarati da FR-016a, e per almeno una fixture il limite è **raggiunto**,
  altrimenti un limite generoso non proverebbe nulla. Due forme sono vietate
  perché nessuna delle due può fallire dove serve: «raddoppiando la popolazione
  il conteggio non raddoppia» — con `q` query per agente e `c` fisse,
  `2qN + c` è sempre minore di `2(qN + c)`, quindi passa anche su un N+1 — e
  l'uguaglianza esatta della parte B, che invece non può passare, perché il
  costo per morto varia con la struttura familiare del defunto.
- **SC-006**: due agenti che nascono nello stesso tick non ricevono
  sistematicamente gli stessi attributi estratti a sorte.
- **SC-007**: ogni tick lascia uno `PopulationSnapshot` in cui **ciascun campo di
  FR-015 è asserito contro il valore atteso** calcolato da una popolazione di
  fixture costruita a mano, e **il tick misurato contiene almeno una nascita,
  una morte e uno spostamento di zona, con un rapporto fra i sessi diverso da
  uno e almeno una coppia attiva**: senza eventi vitali i valori attesi di
  `crude_birth_rate`, `crude_death_rate`, `tfr_instant` e
  `net_migration_by_zone` coincidono con i default del modello (0.0 e vuoto),
  su una popolazione bilanciata ci coincide `sex_ratio`, il cui default è 1.0,
  e senza coppie ci coincide `couples_active`, il cui default è 0 — **sei campi
  su dieci** passerebbero senza che nessuno li calcoli.
- **SC-008**: suite intera verde, `test_citation_hygiene.py` e
  `test_build_map_bilingual.py` compresi.

## Assumptions

- I cinque moduli sono corretti come auditati **con un'eccezione già nota e
  dentro lo scope**: `apply_inheritance_at_birth` deriva il proprio RNG da
  `(simulation, tick, "inheritance")` e consuma un numero di estrazioni che non
  dipende dai genitori, quindi **due neonati nello stesso tick ricevono sesso e
  orientamento identici** e gli stessi residui sui caratteri. È aritmetica sul
  numero di estrazioni, non un'ipotesi. Il difetto è invisibile finché non esiste
  un orchestratore di nascita e diventa certo il giorno in cui esiste, cioè qui:
  correggerlo è parte di questo work item, e SC-006 lo testimonia. Ogni ALTRO
  difetto trovato nei moduli va escalato, non corretto qui.
- La popolazione di riferimento per le misure di costo è quella dell'MVP.
- La validazione contro benchmark storici è un work item successivo.

## Non-goals

- Non si riscrive alcun modulo demografico, e non se ne modifica il corpo: le
  sole eccezioni sono quelle che i requisiti nominano per nome
  (`apply_inheritance_at_birth` per SC-006; `process_emergency_flight` per
  FR-012, dove cambiano la firma e la sola lettura del contatore, non la
  logica di fuga).
- Non si esegue la validazione contro HMD, Wrigley-Schofield, Hajnal.
- Non si cabla la migrazione volontaria nel ciclo decisionale (sezione dedicata).
- Non si esegue alcuna calibrazione (sezione dedicata).
- Non si tocca l'economia, se non per leggere i salari di zona che la migrazione
  già consuma.

## La migrazione volontaria: dove vive, e perché non qui

`build_migration_outlook` **non** è chiamata dal tick loop: il suo docstring dice
che sarà invocata «una volta per agente per tick quando il Plan 4 cabla la
migrazione nel ciclo decisionale», e quel ciclo è `process_agent_turn`, un task
Celery dentro il chord, non il tick loop.

**La collocazione è confermata**: la migrazione volontaria Harris-Todaro è un
input alla decisione dell'agente, non una mutazione di stato per tick, e vive nel
ciclo decisionale. **Il suo cablaggio però non è in questo work item.** La
ragione è tecnica e misurabile: `build_migration_outlook` esegue zero query
proprie solo perché riceve `zone_stats` già costruito — è il contratto che il suo
docstring dichiara load-bearing — e il ciclo decisionale è un insieme di task
paralleli senza memoria condivisa. Cablarla lì richiede di decidere chi
costruisce `zone_stats` una volta per tick e come lo condivide col chord, che è
una scelta d'architettura con un costo suo, da specificare e misurare nel proprio
work item. Farla entrare qui di soppiatto significherebbe o ricostruire
`zone_stats` N volte — l'N+1 che FR-016 vieta — o improvvisare quel meccanismo
fuori da ogni criterio di costo.

Il tick loop cabla la migrazione **forzata**, che è una mutazione di stato per
tick e ha già il suo entry point (`process_emergency_flight`). Al merge, FR-017
copre l'aggiornamento delle frasi del whitepaper che attribuiscono il cablaggio
decisionale a «Plan 4» senza qualificarlo.

## Ciò che il whitepaper chiama «Plan 4» e questo work item non consegna

Il whitepaper usa «Plan 4» come etichetta per un insieme più largo di questo work
item. Per non lasciare promesse pendenti implicite, l'elenco è esplicito. Questo
work item **non** consegna:

- la **calibrazione dei coefficienti Becker** per era (debito B2-07, Table 4.4);
- il **fitting Hadwiger** per la fertilità (`fit_hadwiger`, §6.3);
- le **calibrazioni dell'economia** (parametri Cagan di Table 4.7, parametri
  credito e banche di Table 4.9, dataset e soglie di §7);
- la **validazione storica** (capitolo 7), tracciata da
  `project_validation_experiments_pending.md`;
- il **cablaggio della migrazione volontaria** nel ciclo decisionale (sezione
  precedente);
- la chiusura del debito **A-5**: nel percorso che questo work item cabla la
  condizione non può presentarsi — `Simulation.seed` è NOT NULL nello schema,
  nessun sito di creazione può ometterlo, il tick loop gira su simulazioni
  persistite — quindi non c'è nulla da chiudere qui, e un requisito che vieti
  uno stato strutturalmente impossibile sarebbe verde per costruzione. Il
  debito resta tracciato per gli oggetti `Simulation` non salvati costruiti in
  codice.

Tutto il resto resta tracciato dove già è tracciato; FR-017 impone che al merge
il whitepaper non contenga più frasi che il merge stesso rende false.

## Rischi dichiarati

- **Il rischio maggiore è l'ordine.** Cinque moduli che mutano lo stesso stato in
  un tick hanno un ordine giusto e molti sbagliati, e uno sbagliato produce
  risultati plausibili — una popolazione che cresce o cala in modo credibile — che
  nessun test superficiale distingue. È per questo che FR-003 chiede l'ordine
  come dato e SC-002 lo prova per mutazione.
- **Il secondo è il costo.** `process_inheritance_batch` è la funzione più
  pesante fra quelle cablate qui; il budget va misurato prima di dichiarare il
  lavoro finito, non dopo. `build_migration_outlook`, l'altra funzione pesante
  del sottosistema, resta fuori da questo cablaggio proprio perché il suo costo
  va progettato, non subìto.
- **Il terzo è il determinismo.** I moduli sono pronti per un RNG seminato ma il
  tick loop vive in un'app dove il `random` globale non è mai seminato. Cablare
  senza passare il seme estenderebbe alla demografia un difetto che la build map
  registra fra i rischi trasversali; FR-010 delimita il perimetro che questo
  work item chiude.

## FAQ

**Perché non si valida contro i dati storici in questo work item?** Perché la
validazione richiede che la macchina giri, e oggi non gira. Costruire le due cose
insieme significherebbe non sapere, davanti a uno scostamento, se è sbagliato il
modello o il cablaggio.

**Perché l'ordine come dato e non come codice?** Perché un ordine scritto come
sequenza di chiamate si verifica solo rileggendo la funzione, e si cambia per
sbaglio spostando una riga. Come dato è ispezionabile da un test.

**Il contatore di fame non poteva stare in memoria?** No: il tick loop è
distribuito su task Celery e lo stato in memoria non sopravvive al processo. La
regola del progetto dice stato nel database, mai in variabili globali.

**Che cosa succede alle simulazioni esistenti?** Nulla, finché non attivano la
chiave dedicata di FR-008. La sola presenza o assenza del template d'era non
cambia niente — non può essere il predicato, perché sette punti del codice
applicano già il default in sua assenza — e FR-009 rende l'invarianza un
requisito verificato, non una speranza.

**Perché il debito A-5 non si chiude qui?** Perché nel percorso che questo work
item cabla non esiste: lo schema dichiara il seme NOT NULL, quindi nessun sito
di creazione può ometterlo, e il tick loop gira solo su simulazioni persistite,
quindi il fallback a zero dell'helper RNG non è raggiungibile dal cablaggio. Un
requisito che vietasse quello stato sarebbe verde per costruzione — la classe
di criterio che questo gate ha inseguito per tre round — e il debito resta
tracciato dove può presentarsi davvero, cioè negli oggetti non salvati
costruiti in codice.

**Dove gira il blocco demografico rispetto al chord delle decisioni?** La
collocazione — prima dei task per agente, dopo di essi, o in chiusura di tick —
è una scelta del piano architetturale di fase 3, non un requisito di questa
spec: i vincoli d'ordine di FR-003..FR-007 sono interni al blocco e valgono in
qualunque collocazione. Il piano la dichiara e la motiva, insieme a quale stato
del tick i task per agente vedono.

**Una coppia che si separa al tick T può concepire a T?** No. L'intento di
separazione è di T-1, e la regola di FR-005a è una sola per tutti gli intenti di
coppia: effetto all'inizio di T, prima della finestra di concepimento. La scelta
opposta — separare dopo la fertilità — darebbe un tick di concepimento a una
coppia già decisa a sciogliersi, e soprattutto renderebbe l'effetto degli intenti
dipendente dal loro segno, due semantiche al prezzo di una.

**Come si saprà che l'ordine scelto è quello giusto?** Non lo si saprà da questo
work item: si saprà dalla validazione storica, che è il work item successivo.
Qui l'ordine è dichiarato, giustificato e reso verificabile, il che è la
precondizione perché quella validazione significhi qualcosa.

# Feature Specification: Demografia Plan 4 — inizializzazione, cablaggio, validazione

**Branch**: `20260826-144432-demography-plan4-wiring`
**Creata**: 2026-08-26

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
cinque moduli»: tre moduli su cinque non hanno un punto d'ingresso per tick.
`mortality.py` espone quattro funzioni pure; `fertility.py` dichiara che «i
chiamanti sono responsabili di persistere i cambiamenti di stato»;
`inheritance.py` si autodefinisce «THE PLAN 4 DEATH-PATH ENTRY POINT
(orchestrator step 2/3)», cioè si aspetta che i passi 1 e 3 li scriva questo
work item. Nessun codice di produzione emette oggi un evento di nascita o di
morte: il grep su `EventType.DEATH|EventType.BIRTH` fuori dai test dà zero,
contro le due occorrenze del controllo positivo su `EventType.MIGRATION`.

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
`project_validation_experiments_pending.md`. Qui si costruisce ciò che li rende
eseguibili, non gli esperimenti.

## User Scenarios & Testing *(mandatory)*

### US1 — La popolazione vive (P1)

Un operatore avvia una simulazione con la demografia attiva e, al passare dei
tick, vede nascite, morti, formazioni di coppia, successioni e migrazioni
comparire negli eventi.

**Test di accettazione**:
1. Su una simulazione di N tick con un template d'era dichiarato, il registro
   eventi contiene almeno una nascita e almeno una morte, e la popolazione varia.
2. Ogni evento demografico porta in payload **l'indice del passo** nell'ordine
   dichiarato da FR-003. «Tracciabile al modulo» non era un criterio: il tipo di
   evento partiziona già per modulo nello schema, quindi qualunque
   implementazione lo soddisfaceva senza fare nulla.
3. Una simulazione **senza** demografia configurata gira esattamente come prima,
   senza errori e senza eventi demografici: il cablaggio non rompe le
   simulazioni economiche.

### US2 — L'ordine del tick è dichiarato e rispettato (P1)

I cinque moduli non sono commutativi. Chi muore in questo tick non deve poter
concepire nello stesso tick; l'asse ereditario di chi muore si liquida dopo che
la morte è registrata; chi migra lo fa sulla base dei salari di zona di questo
tick, non del precedente.

**Test di accettazione**:
1. L'ordine è **scritto** nel codice come sequenza esplicita, non implicito
   nell'ordine delle chiamate.
2. Un agente che muore al tick T non genera nascite al tick T.
3. La successione di un agente morto al tick T avviene al tick T, dopo la morte.
4. Ogni proprietà d'ordine sopra è provata **per mutazione**: si scambiano due
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

- **Template d'era nominato ma inesistente**: il cablaggio degrada e non aborte
  il tick, come già fa `apply_agent_action` — che però degrada solo su
  `FileNotFoundError`, cioè sul file mancante, **non** sulla chiave assente, dove
  applica il default. Sono due casi diversi e la prima stesura ne citava uno per
  l'altro.
- **Popolazione a zero**: quando l'ultimo agente muore, il tick successivo non
  deve sollevare eccezioni.
- **Costo per tick**: cinque moduli su N agenti possono introdurre N+1 query. Il
  budget va misurato e dichiarato, non scoperto in produzione.
- **Determinismo**: i moduli demografici usano `get_seeded_rng`; il tick loop
  deve passare il seme, altrimenti la demografia eredita il difetto dell'RNG
  globale non seminato che i rischi trasversali della build map già registrano.

## Requirements *(mandatory)*

**Gli orchestratori**

- **FR-001**: il **percorso di nascita** è un orchestratore che crea l'`Agent`
  neonato, ne valorizza `birth_tick`, `parent_agent` e `other_parent_agent`,
  chiama `apply_inheritance_at_birth`, e emette un evento di nascita.
- **FR-001a**: il **nome del neonato** è una decisione di requisito, non
  implementativa: viene da una lista per template d'era, non dall'LLM. Un nome
  generato dall'LLM renderebbe la nascita non riproducibile dal seme, che è
  quanto §4.8 del whitepaper dichiara come limite già esistente e che questo work
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
- **FR-005a**: la **risoluzione delle separazioni** è collocata nell'ordine in
  modo dichiarato, perché decide se una coppia che si separa a T concepisce
  comunque a T.
- **FR-006**: la successione di un agente segue la sua morte nello stesso tick.
- **FR-007**: la migrazione usa le statistiche di zona del tick corrente.
- **FR-007a**: `dissolve_on_death` **non** entra nell'ordine dichiarato:
  `process_inheritance_batch` lo chiama già per ultimo, deliberatamente.

**Il predicato di attivazione**

- **FR-008**: la demografia è attiva quando la simulazione lo **dichiara
  esplicitamente**, con una chiave dedicata. Non si può usare la presenza del
  template d'era: sette punti del codice di produzione applicano già
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
  silenzio.
- **FR-012**: `process_emergency_flight` legge il contatore persistito.
- **FR-013**: l'inizializzazione valorizza **`birth_tick`**, che è l'unica sorgente
  di invecchiamento del progetto: `Agent.age` non viene mai assegnato a runtime,
  e senza `birth_tick` la mortalità e la fertilità restano congelate per sempre.
- **FR-014**: l'inizializzazione crea **coppie iniziali**. Nessun codice le crea
  oggi, e senza di esse il template di default rende impossibile qualsiasi
  nascita nei primi tick.
- **FR-015**: il tick scrive uno `PopulationSnapshot` per tick, con la piramide
  per età, il rapporto fra i sessi, i tassi grezzi di natalità e mortalità, la
  fecondità totale istantanea e le coppie attive.

**Costo e documentazione**

- **FR-016**: il blocco demografico **non esegue query per agente**. Verificabile
  eseguendo lo stesso tick con N e con 2N agenti e pretendendo che il conteggio
  non cresca linearmente.
- **FR-017**: il whitepaper §4.1 in entrambe le lingue documenta gli orchestratori
  e l'ordine dichiarato, nello stesso commit del codice. La build map è aggiornata
  in entrambe le lingue allo stesso checkpoint.

## Success Criteria *(mandatory)*

- **SC-001**: su una simulazione di riferimento nascono e muoiono agenti, e la
  popolazione varia.
- **SC-002**: ogni proprietà d'ordine di FR-004, FR-005, FR-005a, FR-006 e FR-007
  è provata **per mutazione**: si scambiano due passi e il test diventa rosso.
- **SC-003**: il contatore di fame si incrementa e si azzera come prescritto, con
  lo stesso predicato del trigger, provato per mutazione.
- **SC-004**: una simulazione con la demografia non attiva esegue **lo stesso
  numero di query** di prima del cablaggio e non produce eventi demografici.
- **SC-005**: raddoppiando la popolazione, il conteggio di query del blocco
  demografico **non raddoppia**.
- **SC-006**: due agenti che nascono nello stesso tick non ricevono
  sistematicamente gli stessi attributi estratti a sorte.
- **SC-007**: ogni tick lascia uno `PopulationSnapshot` leggibile.
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

- Non si riscrive alcun modulo demografico.
- Non si esegue la validazione contro HMD, Wrigley-Schofield, Hajnal.
- Non si tocca l'economia, se non per leggere i salari di zona che la migrazione
  già consuma.

## La migrazione volontaria: dove vive

`build_migration_outlook` **non** è chiamata dal tick loop: il suo docstring dice
che sarà invocata «una volta per agente per tick quando il Plan 4 cabla la
migrazione nel ciclo decisionale», e quel ciclo è `process_agent_turn`, un task
Celery dentro il chord, non il tick loop.

**La lettura scelta è la seconda**: la migrazione volontaria Harris-Todaro entra
nel ciclo decisionale, non nel tick loop, perché è un input alla decisione
dell'agente e non una mutazione di stato per tick. Il tick loop cabla la
migrazione **forzata**, che è una mutazione. Dichiararlo è necessario perché le
due letture differiscono per una user story intera e per il costo per tick, e la
prima stesura le lasciava indistinguibili.

## Rischi dichiarati

- **Il rischio maggiore è l'ordine.** Cinque moduli che mutano lo stesso stato in
  un tick hanno un ordine giusto e molti sbagliati, e uno sbagliato produce
  risultati plausibili — una popolazione che cresce o cala in modo credibile — che
  nessun test superficiale distingue. È per questo che FR-002 chiede l'ordine
  come dato e SC-002 lo prova per mutazione.
- **Il secondo è il costo.** `process_inheritance_batch` e
  `build_migration_outlook` sono le due funzioni più pesanti del sottosistema; il
  budget va misurato prima di dichiarare il lavoro finito, non dopo.
- **Il terzo è il determinismo.** I moduli sono pronti per un RNG seminato ma il
  tick loop vive in un'app dove il `random` globale non è mai seminato. Cablare
  senza passare il seme estenderebbe alla demografia un difetto che la build map
  registra fra i rischi trasversali.

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

**Che cosa succede alle simulazioni esistenti?** Nulla, se non dichiarano un
template d'era. FR-009 lo rende un requisito verificato, non una speranza.

**Come si saprà che l'ordine scelto è quello giusto?** Non lo si saprà da questo
work item: si saprà dalla validazione storica, che è il work item successivo.
Qui l'ordine è dichiarato, giustificato e reso verificabile, il che è la
precondizione perché quella validazione significhi qualcosa.

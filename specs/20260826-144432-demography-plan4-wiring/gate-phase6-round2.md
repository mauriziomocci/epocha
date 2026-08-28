# Gate di fase 6 — Round 2 sul CODICE: criterio di convergenza

**Scritto prima del lancio del round, 2026-08-28.** Il round 1 è girato senza
che il criterio fosse fissato in anticipo su questo work item; qui lo è, e la
ragione è la stessa che il work item precedente ha pagato per undici round —
un criterio letto dopo aver visto il risultato è una trattativa, non un
criterio.

## Ambito: ristretto al diff della remediation

Il round giudica `git diff a9a7bb0..HEAD`, non l'intero branch. Il round 1 ha
già giudicato il diff completo `develop..a9a7bb0`; ri-giudicare quel codice
significherebbe rileggere duemila righe già lette per trovare gli stessi
rilievi.

Sul work item precedente restringere l'ambito al diff della remediation ha
portato un round da venticinque minuti a tre **senza perdere severità**: il
round così ristretto ha trovato il difetto più consequenziale dell'arco
finale.

**Il round 1 ha prodotto NOVE bloccanti, non otto.** L'handoff ne conta otto,
e la prima stesura di questo documento li contava otto qui e nove nella
sezione seguente, che ne elenca nove. Il nono è la coda documentale, che
l'handoff enumera separatamente dai bloccanti pur dovendo essere chiusa prima
del merge. Nove è il numero: la sezione che segue è la lista, e una lista
lunga nove è la definizione.

Il rischio del restringimento è dichiarato invece che taciuto: una
remediation può rompere codice che il round 1 aveva giudicato sano e che
questo round non rilegge. È mitigato dal fatto che la suite intera gira su
ogni commit, che le mutazioni sono eseguite contro la versione **precedente**
oltre che contro quella nuova, e che ogni file toccato dalla remediation
rientra comunque nell'ambito per intero, non solo nelle righe cambiate.

## I nove bloccanti del round 1, e che cosa si sostiene di aver chiuso

Il round deve **verificare ciascuna chiusura contro il codice**, non fidarsi
di questo elenco. Una chiusura dichiarata e non vera è il difetto peggiore
che questo round possa trovare, perché sposta un problema noto dentro la
categoria dei risolti.

1. **N+1 nel passo fertilità**, sette query per donna fertile viva.
   Sostenuto chiuso da `ae12137`: sei domande precaricate una volta per zona
   e per simulazione, la settima portata da `select_related`.
2. **Fixture della guardia di costo che non poteva fallire** (soli maschi
   contro un passo che filtra le femmine). Sostenuto chiuso già in `a9a7bb0`,
   e ri-verificato qui perché la guardia è stata riscritta due volte da
   allora.
3. **`_avg_household_size` senza soglia d'età**, contro la propria docstring.
   Sostenuto chiuso da `9a65ecb`, con la soglia presa dal template.
4. **Prove d'ordine SC-002 tautologiche** — asserzione sulla tupla permutata
   anziché sul comportamento. Sostenuto chiuso da `d773f7a`, che esegue
   l'ordine permutato.
5. **Nessun confine transazionale** nei passi scritti dall'orchestratore.
   Sostenuto chiuso da `45189e8` per mortalità e fertilità, con la
   dichiarazione esplicita che il passo contatore ha una sola scrittura e non
   ne ha bisogno.
6. **`load_template` nudo in `form_initial_couples`**, che abortiva la
   generazione del mondo. Sostenuto chiuso da `6ea106f`.
7. **`DemographyStep.rng_phase` senza consumatore e sbagliato per due passi**.
   Sostenuto chiuso da `6ea106f`, diventato `rng_phases` e tenuto al codice
   da un test che registra le derivazioni reali.
8. **Popolazione sterile su un mondo già generato, senza log**. Sostenuto
   chiuso da `bc93240`, con la riparazione del `birth_tick` per tick e
   l'avviso sull'assenza di coppie.
9. **Coda documentale**: §4.1.1–§4.1.3, l'ordine dichiarato in testa al §4.1,
   la mappa di default cancellata nel §4.1.5, la sezione `names` non
   documentata, la build map, `ruff format`. Sostenuta chiusa da `018d8ef`,
   `bc93240` e `1286458`.

## Che cosa il round deve cercare, in ordine di gravità

1. **Difetti di correttezza nel codice di produzione** introdotti dalla
   remediation stessa: è la classe che il work item precedente ha visto due
   volte di fila, dove una riparazione distrugge un testimone mentre ne
   aggiunge un altro.
2. **Criteri che non possono fallire** fra le guardie **nuove**. Su questo
   work item il conto sta a diciotto; la maggioranza di quelli trovati dalla
   remediation è stata trovata dentro guardie scritte per chiudere i primi.
3. **Chiusure dichiarate e non vere** fra le nove sopra.
4. **Doc-sync**: un modulo del §4.1 toccato dalla remediation senza il
   whitepaper aggiornato nello stesso commit.
5. **Prosa che descrive uno stato superato**, build map inclusa.

## Criterio di convergenza

Il gate dà **CONVERGED** quando il round non produce:

- alcun difetto di correttezza nel codice di produzione, **né**
- alcun criterio che non può fallire, **né**
- alcuna chiusura dichiarata e non vera fra le nove del round 1.

Cifre imprecise, riferimenti che puntano male, frasi da riformulare e
osservazioni sulla spec **non riaprono il gate**: si correggono nello stesso
commit e si registrano.

## Perché questo criterio può fallire

Il criterio è falsificabile e va detto in che modo, o è teatro. La
remediation aggiunge 2172 righe su 24 file, tocca due moduli auditati nelle
firme, cambia il costo per tick due volte, introduce una riparazione che gira
a ogni tick e riscrive undici file di test. Le mutazioni eseguite sono
ventisei e cinque sono sopravvissute al primo colpo, tutte chiuse. Se il
round non produce nulla delle tre classi bloccanti, la spiegazione ammessa è
che quelle mutazioni lo abbiano già colto — non che il round non abbia
guardato, e il verdetto deve dire quali percorsi ha verificato per
sostenerlo.

## Emendamenti a questo documento dopo il lancio

Registrati perché un criterio modificato in silenzio dopo aver visto il
risultato non è più un criterio. Nessuno dei due tocca ciò che blocca la
convergenza; entrambi correggono un difetto che il round stesso ha trovato in
questo file.

1. **La contraddizione otto/nove**, rilevata dal round come C9: il documento
   diceva otto nell'ambito e nove nella lista. Corretta a nove, che è la
   lunghezza della lista.
2. **Il conteggio dei criteri-che-non-possono-fallire**, da tredici a
   diciotto, rilevato dal round come C8: tredici era un sotto-conteggio della
   remediation stessa, e la cifra non è un cancello, è un contesto.

Le tre classi bloccanti sono quelle scritte prima del lancio e non sono state
toccate.

## Verdetto: NOT CONVERGED

Round eseguito il 2026-08-28 da tre revisori avversariali su classi disgiunte,
ambito ristretto come dichiarato sopra.

**Classe 1 — difetti di correttezza nel codice di produzione: nessun rilievo.**
Il revisore ha verificato e dichiarato i percorsi: l'equivalenza bit-identica
di `compute_aggregate_outlook` fallback inclusi; l'invarianza dei precarichi
attraverso il ciclo delle candidate, seguita fino alle foglie e non presa
dalla docstring; il `return` dentro `transaction.atomic()`, letto contro
`Atomic.__exit__` e corretto perché su un return normale committa;
l'annidamento del savepoint dentro `process_inheritance_batch`; l'equivalenza
fra la mappa di appartenenza e `is_in_active_couple` incluse le FK nullable e
la trappola del falsy; la legittimità del `select_related` sul one-to-one
inverso; l'allineamento degli zip in `_avg_household_size` e la provenienza
della soglia; l'idempotenza della riparazione per tick; l'assenza di
consumatori di `rng_phases` fuori dai test; e l'assenza di import circolare.

**Classe 2 — criteri che non possono fallire: UN rilievo, misurato, e blocca.**
`test_demography_cost.py:173`, la seconda asserzione della guardia sui
candidati assenti. Inerte due volte: oscurata dall'uguaglianza che la precede,
che pinna `observed` a una costante e la riduce al confronto di due costanti
di modulo; e, misurata con quell'ombra rimossa e con iniettata la regressione
esatta che il suo messaggio nomina — i precarichi spostati sopra il ritorno
anticipato — **ancora verde**, perché il conteggio gonfiato resta comunque
sotto l'altro termine. Il revisore ha eseguito quarantacinque mutazioni sul
codice di produzione contro una copia pristina di `c7683bf`: ogni altra
guardia dell'elenco muore ad almeno una.

**Classe 3 — chiusure e documentazione: la riga 9 NON CHIUSA, più dodici
rilievi non bloccanti.** Le prime otto chiusure reggono contro il codice, con
un sub-claim inesistente sulla riga 5. La nona no: §4.1.1, §4.1.2 e §4.1.3 di
entrambi i whitepaper dichiaravano ancora che la demografia non è invocata dal
tick loop, mentre il §4.1.4 le citava come già corrette — la chiusura che la
spec nomina per prima nell'inventario di FR-017, e l'unica riga che nessuno
aveva toccato.

### Che cosa è stato corretto in risposta

- La classe 2: l'asserzione inerte è stata **rimossa, non riparata**, e la
  ragione è scritta nella docstring del test. L'uguaglianza che la precede
  cattura la regressione da sola, come la stessa misura conferma.
- La riga 9: le tre chiusure di §4.1.1–§4.1.3 riscritte in entrambe le lingue.
- Il sub-claim della riga 5: il passo contatore ora **dichiara** di avere una
  sola scrittura e di non volere un confine, invece di lasciarlo dedurre.
- La tabella di doc-sync guadagna una riga per §4.1.0: elencava solo i cinque
  moduli di modello mentre il §4.1.0 è un intero sotto-capitolo su
  `orchestrator.py` e la tabella dei contratti del §4.1 documenta `context.py`
  per nome. Tre commit hanno toccato quei file senza che scattasse alcun
  obbligo, ed è così che il §4.1.0 è andato stale sul campo che avevano
  rinominato.
- Le cifre e le frasi superate: il §4.1.0 sul campo singolare, il §7.4
  divergente fra le due lingue, il commento delle misure di costo, la docstring
  del passo fertilità, quella del modulo di inizializzazione, i due conteggi
  incoerenti in `fertility.py`, la build map su commit e criteri, questo stesso
  documento sulla contraddizione otto/nove, e l'handoff marcato come superato.

### Un difetto trovato fuori dai tre revisori, e registrato qui

Verificando l'assunto che il ciclo delle candidate non scriva nulla — che
l'handoff dava per assunto e che ora è **misurato**, zero scritture — è emerso
che le nascite costavano **tre query ciascuna**: il partner, il dereference
della sua FK, e la media di classe della zona dentro
`apply_inheritance_at_birth`. FR-016a è categorico nel non concedere alle
nascite alcun termine proprio, e nessuna guardia lo coglieva perché nessuna
fixture di costo aveva una sola nascita. Corretto precaricando i partner in un
`in_bulk` e la media di classe per zona, con una guardia nuova che pretende
**uguaglianza** fra un tick con una nascita e uno con quattro, provata per
mutazione su tutti e tre i precarichi.

### Conseguenza

Il criterio scritto prima del lancio dichiara bloccante un criterio che non
può fallire. Ce n'era uno. Il round è **NOT CONVERGED**, e il round 3 giudica
la remediation di questo round — inclusa la correzione del costo per nascita,
che nessun revisore di questo round ha visto.

---

## Round 3: criterio, scritto prima del lancio

**2026-08-28, dopo il verdetto qui sopra e prima di lanciare il round 3.**

**Ambito**: `git diff c7683bf..HEAD`, la remediation del round 2. Include il
codice di produzione che nessun revisore del round 2 ha visto — la correzione
del costo per nascita — che è il primo posto dove guardare.

**Le tre classi bloccanti restano identiche**: un difetto di correttezza nel
codice di produzione, un criterio che non può fallire, una chiusura dichiarata
e non vera. Non sono state toccate e non lo saranno.

**Che cosa questo round deve sospettare per primo.** Il round 2 ha chiuso il
proprio unico bloccante rimuovendo un'asserzione. Sul work item precedente,
due volte di fila, una riparazione ha distrutto un testimone mentre ne
aggiungeva un altro, e la causa era sempre la stessa: la copertura misurata
dopo la correzione invece che come differenza. Quindi la domanda del round 3
è se la rimozione abbia lasciato scoperto qualcosa che quell'asserzione, per
quanto inerte contro la mutazione provata, copriva contro un'altra.

**Convergenza**: nessuna delle tre classi. Cifre e frasi si correggono nello
stesso commit.

**Perché può fallire**: la remediation aggiunge un precarico nuovo in un
ciclo caldo, cambia la firma di una funzione auditata per la quarta volta,
rimuove un'asserzione da una guardia di costo e riscrive tre chiusure di
capitolo in due lingue. Se non produce nulla, il verdetto deve dire quali
percorsi ha verificato.

### Verdetto round 3: NOT CONVERGED

Due revisori, classi disgiunte, ambito ristretto come dichiarato.

**Il criterio aveva ragione su cosa sospettare.** Aveva scritto, prima del
lancio, che la domanda era se rimuovere un'asserzione avesse lasciato
scoperto qualcosa. La risposta a quella domanda è no — misurata su due
varianti del file di test, una con l'asserzione e una senza, contro cinque
mutazioni: tutte rosse in entrambe, nessuna coppia verde/rosso. Ma la classe
che il criterio nominava — una riparazione che aggiunge un testimone e ne
lascia scoperto un altro — c'era lo stesso, un livello più in là.

**Bloccante, classe 2, due rilievi.** La correzione del costo per nascita ha
sostituito due query per nascita con due precarichi e ha aggiunto **solo un
testimone di costo**. Il valore che i precarichi producono non era guardato da
nulla:

- `orchestrator.py`, la risoluzione del padre. Sostituendola con un uomo
  arbitrario preso dalla mappa precaricata, **ogni neonato del tick riceve il
  genitore sbagliato e 880 test su 880 restano verdi**. Il conteggio di query
  non cambia, quindi la guardia nuova non lo vede; l'unico test che asserisce
  `other_parent_agent_id` chiama `build_newborn` a mano e non attraversa mai
  quella riga.
- `orchestrator.py`, la media di classe della zona. Passandone una inventata a
  ogni nascita — l'input dei rami `clark_regression` e
  `becker_tomes_elasticity_0.4` dell'ereditarietà sociale — la suite resta
  verde allo stesso modo.

**Non bloccante, classe 1, un rilievo.** `active_couple_partners` scartava
l'intera riga quando una delle due FK è nulla, mentre il `frozenset` che
sostituiva teneva il superstite come membro: per una coppia attiva mezza-nulla
i due rami dello stesso `if` in `tick_birth_probability` davano verdetti
opposti sulla stessa agente, mentre la docstring li dichiara intercambiabili.
Nessun percorso di produzione costruisce oggi quello stato — verificato:
`dissolve_on_death` annulla la FK e scrive `dissolved_at_tick` nello stesso
`save`, e nulla in `epocha/` cancella righe `Agent` — quindi il revisore lo ha
dichiarato non bloccante e io lo correggo comunque, perché è un'invariante
scritta in prosa e non tenuta da nulla.

### Che cosa è stato corretto in risposta

Tre testimoni **di valore**, ciascuno provato contro la mutazione esatta che
il revisore aveva misurato sopravvivere:

- ogni neonato riceve il partner di **sua** madre, su tre coppie con la madre
  alternata fra `agent_a` e `agent_b`, perché una coppia sola non separa una
  risoluzione che legge una colonna soltanto;
- una madre non accoppiata, sotto un'era che ammette la nascita fuori dalla
  coppia, riceve `other_parent_agent_id` nullo — così la risoluzione non può
  rispondere restituendo sempre qualcuno;
- la media di classe che arriva a una nascita è quella della zona di quella
  madre, confrontata con l'helper auditato **prima** del passo, perché il
  neonato entra nella zona e sposta la media.

La mappa dei partner entra ora ciascun lato per conto proprio, quindi il
superstite di una coppia mezza-nulla è membro con valore `None`, e la
membership si prova con `in` e mai per verità del valore. Una guardia lo
pretende.

### Conseguenza

Il round 3 è **NOT CONVERGED**: due criteri che non potevano fallire, entrambi
introdotti dalla remediation del round 2. Il round 4 giudica questa
remediation.

---

## Round 4: criterio, scritto prima del lancio

**2026-08-28, dopo il verdetto del round 3 e prima di lanciare il round 4.**

**Ambito**: `git diff 8b0555e..HEAD`, la remediation del round 3.

**Le tre classi bloccanti restano identiche** e non sono state toccate: un
difetto di correttezza nel codice di produzione, un criterio che non può
fallire, una chiusura dichiarata e non vera.

### Il pattern che questo gate continua a produrre, e che il round 4 deve rompere

Tre round, tre verdetti, e la stessa forma ogni volta: **la remediation del
round N introduce il bloccante del round N+1**, sempre della stessa classe e
sempre un passo più in là.

- Il round 2 ha trovato un'asserzione inerte e l'ha chiusa rimuovendola.
- Il round 3 ha trovato che la correzione del round 2 sul costo per nascita
  aveva aggiunto **solo un testimone di costo**, e nessuno guardava il valore
  che i precarichi producono.
- Il round 3 l'ho chiuso aggiungendo tre testimoni di valore.

La domanda del round 4 è quindi **la stessa un livello più fuori**: quei tre
testimoni coprono ciò per cui sono stati scritti — è misurato — ma che cosa
resta di ciò che il passo fertilità produce, e che nessun test asserisce per
valore? Il neonato ha nome, sesso, orientamento, caratteri, classe sociale,
istruzione, zona, `birth_tick`, genitori ed evento di nascita. I testimoni
aggiunti ne coprono due. Il round 4 deve enumerare gli altri e dire, per
ciascuno, quale mutazione lo lascerebbe verde.

### Regola di processo, obbligatoria per questo round

La lezione che il work item precedente ha pagato due volte: **quando una
riparazione cambia un testimone, la batteria di mutazioni va eseguita anche
contro la versione PRECEDENTE**, perché la copertura si misura come
differenza e non dopo la correzione. Il round 4 la applica alla remediation
del round 3 e lo dichiara nel verdetto.

### Che cosa il verdetto deve contenere, oltre ai rilievi

Se il round non produce nulla delle tre classi, deve **enumerare che cosa non
ha coperto**. Un verdetto che dice solo «nessun rilievo» dopo tre round che
ne hanno trovati non è un verdetto, è una resa.

**Convergenza**: nessuna delle tre classi bloccanti. Cifre e frasi si
correggono nello stesso commit.

### Verdetto round 4

*(da compilare a round concluso)*

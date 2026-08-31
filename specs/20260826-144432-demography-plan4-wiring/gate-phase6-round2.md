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
**Questa premessa era sbagliata, e il round 4 l'ha smentita: si legga la
rettifica sotto il verdetto del round 4.** Diceva: «Nessun percorso di
produzione costruisce oggi quello stato — verificato: `dissolve_on_death`
annulla la FK e scrive `dissolved_at_tick` nello stesso `save`, e nulla in
`epocha/` cancella righe `Agent`». La prima metà regge; la seconda no, perché
l'enumerazione cercava chiamate `.delete()` nel sorgente e il percorso vero
non è una chiamata nel sorgente.

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

### Verdetto round 4: NOT CONVERGED

**Il pattern si è ripetuto una quarta volta, e nel posto peggiore: dentro il
testimone scritto per chiuderlo.**

**Bloccante, classe 2.** Il testimone che il round 3 ha aggiunto per provare
che ogni neonato riceve il partner di *sua* madre dichiara, nel proprio
docstring, di separare le due colonne di `Couple` mettendo la madre in
`agent_a` in alcune coppie e in `agent_b` in altre. Non lo fa. `form_couple`
instrada entrambi i partner attraverso `_ordered_pair`, che ordina per id per
soddisfare il vincolo canonico del modello, quindi **l'ordine degli argomenti
al call site non decide nulla**: decide chi è stato creato prima, e la madre
era creata per prima in tutti e tre i cicli. Misurato: togliendo il lato
`agent_b` dalla mappa — esattamente la regressione che il docstring nomina —
tutti e 22 i test del file restano verdi. È strutturalmente identico al
bloccante 2 del round 1, la fixture di soli maschi contro un passo che filtra
le femmine: **una fixture che dichiara di costruire un caso che il sistema le
impedisce di costruire.**

**Due testimoni su tre erano più deboli di quanto dichiaravano.** Quello sulla
media di classe della zona girava su **una zona sola**, quindi «la media di
*quella* zona» non era separabile da «la media di *una* zona»; misurato, la
mutazione che legge la voce sbagliata della cache lo lasciava verde. E
l'ultima asserzione di quel test, `mean > 0.0`, era oscurata dall'uguaglianza
che la precede e giustificata da un commento che dichiarava il fallback
neutro pari a zero, mentre è il rango di `working`.

**La chiusura sulla mappa dei partner era metà.** La mappa è corretta e la
guardia sulla coppia mezza-nulla esiste, ma **nessun test pretendeva che la
membership si provasse con `in`**: sostituendo `mother.id in
partnered_agent_ids` con `bool(partnered_agent_ids.get(mother.id))` l'intera
suite restava verde, perché in ogni fixture i partner hanno id non nulli e
quindi truthy. L'unica forma che separa i due predicati è la coppia
mezza-nulla, e nessuna fixture la mandava attraverso `tick_birth_probability`.

**Classe 1: l'annotazione mentiva.** `active_couple_partners` dichiarava
`-> dict[int, int]` mentre il corpo dichiara `dict[int, int | None]` e il
docstring dice che il valore può essere `None`. Tre affermazioni sullo stesso
tipo nella stessa funzione, e quella sbagliata era la prima che un lettore
vede. Nessun type checker nel progetto la coglieva.

### Rettifica al verdetto del round 3

Il round 3 dichiarava non raggiungibile in produzione la coppia attiva
mezza-nulla, «verificato: nulla in `epocha/` cancella righe `Agent`». **È
falso.** `epocha/apps/agents/admin.py` registra `Agent` con il `ModelAdmin` di
default, quindi l'admin di Django espone «Delete selected agents», che fa
scattare `on_delete=SET_NULL` su `Couple.agent_a`/`agent_b` senza toccare
`dissolved_at_tick`: è esattamente una coppia attiva mezza-nulla, ed è il
motivo per cui `SET_NULL` esiste. L'enumerazione cercava chiamate `.delete()`
nel sorgente e non le trovava; il percorso admin non è una chiamata nel
sorgente. La conseguenza è sostanziale: in quello stato la superstite **ora
concepisce** sotto un'era che richiede la coppia, dove prima era esclusa. Il
cambio è quello giusto — l'equivalenza con `is_in_active_couple` è
l'invariante — ma era giustificato da una premessa che non regge, e ora è
esercitato da un test.

### Che cosa è stato corretto in risposta

- L'alternazione fra le due colonne è reale: il padre è creato per primo nei
  cicli pari, e **la fixture asserisce la propria forma** — che almeno una
  madre sia in `agent_a` e almeno una in `agent_b` — perché una fixture che
  smette in silenzio di costruire il caso che dichiara è il difetto che
  questo file continua a pagare. Misurato: togliendo l'uno o l'altro lato
  della mappa il testimone muore, in entrambe le direzioni.
- Il testimone sulla media di zona gira ora su **due zone che partoriscono
  entrambe nello stesso tick**, con composizioni di classe diverse e la
  distinzione asserita in anticipo, e cattura la media per singola nascita.
  Muore sia contro il valore inventato sia contro la lettura della zona
  sbagliata.
- Un testimone nuovo pretende che la membership si provi per chiave: la
  superstite di una coppia mezza-nulla deve poter concepire sotto un'era che
  richiede la coppia, perché *è* in una coppia attiva. Muore contro la
  sostituzione con il test di verità del valore.
- L'annotazione di ritorno dice ora `dict[int, int | None]`.

### Conseguenza

Round 4 **NOT CONVERGED**: un criterio che non poteva fallire più due
testimoni più deboli della loro stessa dichiarazione, tutti introdotti dalla
remediation del round 3. Il round 5 giudica questa remediation.

---

## Round 5: criterio, scritto prima del lancio

**2026-08-29, dopo il verdetto del round 4 e prima di lanciare il round 5.**

**Ambito**: `git diff 2849510..HEAD` — la remediation del round 4 più la
risposta alla domanda di copertura per valore che il round 4 aveva lasciato
aperta, e i due testimoni che ne discendono.

**Le tre classi bloccanti restano identiche** e non sono state toccate: un
difetto di correttezza nel codice di produzione, un criterio che non può
fallire, una chiusura dichiarata e non vera.

### Che cosa la domanda del round 4 ha prodotto, misurato

La domanda era: che cosa produce `run_fertility_step` che nessun test
asserisce per valore, attraversando il passo. La risposta, misurata e non
argomentata: **dodici cose su tredici**.

Dodici corruzioni applicate dentro il passo — nome, sesso, orientamento
sessuale, gli otto caratteri ereditabili scalari dimezzati, classe sociale,
livello d'istruzione, ricchezza, zona, più quattro proprietà dell'evento di
nascita (nome del passo, flag di morte in parto, appaiamento del neonato e
appaiamento della madre) — hanno lasciato **1717 test su 1717 verdi**, suite
intera e non solo il sottoinsieme demografico. L'unica che moriva era
`birth_tick`, con otto rossi.

La riparazione è **due testimoni, non dodici**, perché le otto corruzioni
sugli attributi del neonato sono lo stesso difetto: il passo che sovrascrive
ciò che il proprio produttore ha appena costruito. Il primo testimone cattura
l'oggetto restituito da `build_newborn` e pretende che la riga persistita gli
corrisponda campo per campo; il secondo pretende che ogni evento descriva la
propria nascita, su due nascite di cui una con la madre che muore in parto.

### La regola operativa, applicata e dichiarata

**La batteria è stata eseguita anche contro la versione precedente.** Prima
dei testimoni: dodici corruzioni su dodici sopravvivono alla suite intera.
Dopo: dodici su dodici muoiono, ciascuna misurata **singolarmente**, perché
una batteria combinata si ferma al primo campo e proverebbe solo quello.

**E il pattern si è ripetuto dentro la riparazione stessa, per la quinta
volta.** Il testimone sull'orientamento sessuale, alla prima stesura, era
inerte: la corruzione forza `heterosexual` e tutti e cinque i template lo
estraggono al 95,5%, quindi sovrascriveva un valore con se stesso. È emerso
solo perché le mutazioni sono state misurate campo per campo invece che tutte
insieme; la batteria combinata lo avrebbe dichiarato coperto. Corretto
sostituendo la distribuzione dell'era sul caricatore — non cercando un seme
fortunato — e ri-misurato.

### Che cosa questo round deve sospettare per primo

I due testimoni nuovi sono l'unica cosa che oggi separa dodici proprietà dal
nulla. La domanda è quindi la stessa un livello più fuori: **che cosa quei due
testimoni dichiarano di coprire e non coprono**, e che cosa resta fuori dal
loro perimetro. Il primo dichiara esplicitamente di non coprire una
corruzione interna a `build_newborn`; il round verifichi che quella frontiera
sia davvero presidiata altrove, e non solo dichiarata.

### Che cosa il verdetto deve contenere, oltre ai rilievi

Se il round non produce nulla delle tre classi, deve **enumerare che cosa non
ha coperto**. Quattro round su quattro hanno prodotto un bloccante; un quinto
che dice solo «nessun rilievo» non è un verdetto, è una resa.

**Convergenza**: nessuna delle tre classi bloccanti. Cifre e frasi si
correggono nello stesso commit.

### Perché questo criterio può fallire

La remediation aggiunge due classi di test e un monkeypatch sul caricatore dei
template, tocca un file di test già riscritto tre volte in questo gate, e
introduce una fixture che cambia la distribuzione di un'era. Se il round non
produce nulla, la spiegazione ammessa è che le ventiquattro misure di
mutazione — dodici prima, dodici dopo — lo abbiano già colto, e il verdetto
deve dire quali percorsi ha verificato per sostenerlo.

### Verdetto round 5: NOT CONVERGED

Un revisore, ambito ristretto come dichiarato, igiene di processo rispettata:
ogni mutazione ripristinata subito, un solo pytest per volta, nessun processo
lasciato vivo.

**Il pattern si è ripetuto per la sesta volta, e di nuovo dentro il testimone
scritto per chiuderlo.** Tre criteri che non potevano fallire, tutti e tre
nella classe `TestTheStepPersistsWhatItBuilt`, e due delle tre forme sono
letteralmente quelle che i round 1 e 4 avevano già nominato.

**Bloccante 1, classe 2 — il testimone si chiama «every field» e ne enumerava
diciotto scritti a mano.** Il perimetro era il letterale `WITNESSED` più gli
otto caratteri scalari, e nulla lo legava all'insieme dei campi che
`build_newborn` scrive davvero: il letterale era già fuori sincrono col
produttore il giorno in cui è nato. Fuori restavano `personality` — cinque
tratti Big Five scritti da `inheritance.py:656` —, `cunning`, `role` e
`health`. Misurato: azzerando la personalità di ogni neonato fra costruzione e
salvataggio, **1719 test su 1719 verdi**.

**Bloccante 2, classe 2 — la fixture aveva una zona sola**, quindi «la zona di
*quella* madre» non era separabile da «una zona». Misurato con la regressione
realistica, ogni neonato assegnato alla zona della prima candidata: 1719 su
1719 verdi. È il rilievo che il round 4 aveva già fatto sul testimone della
media di classe, ri-introdotto dentro il testimone scritto dopo di esso.

**Bloccante 3, classe 2 — la corruzione della classe sociale sovrascriveva un
valore con se stesso.** Madre `wealthy` e padre `elite` in entrambe le coppie,
sotto una regola patrilineare verbatim: entrambi i neonati ereditavano
`elite`, e pinnare quella colonna a `elite` lasciava 24 test su 24 verdi. È la
stessa inerzia che la remediation del round 4 aveva trovato e chiuso
sull'orientamento sessuale: riparata quella colonna, lasciata in piedi quella
accanto sulla stessa trappola.

**Non bloccante, prosa superata**: `test_fertility_zone_context.py` dichiarava
ancora che nessun percorso di produzione costruisce la coppia attiva
mezza-nulla, frase che il verdetto del round 4 aveva già rettificato in questo
stesso documento.

**Classe 1: nessun rilievo.** L'unica riga di produzione in ambito è
l'annotazione di `active_couple_partners`, ora concorde con corpo e docstring.
Tutte le chiusure del round 4 sono state ri-misurate e sono vive.

### Che cosa è stato corretto in risposta

- **L'insieme dei campi confrontati è derivato dal modello, non enumerato**:
  `Agent._meta.concrete_fields` meno `id` e `created_at`, che non possono
  combaciare per costruzione. Una colonna aggiunta domani è testimoniata senza
  che nessuno se ne ricordi. Una guardia nomina esplicitamente i cinque campi
  che il round 5 ha trovato mancanti, perché la regressione non torni in
  silenzio.
- **Due zone e due classi paterne**, con la fixture che **asserisce la propria
  forma**: se i due neonati finissero nella stessa zona o nella stessa classe,
  il test lo dice invece di andare inerte.
- La prosa superata corretta in loco, con la ragione per cui era falsa.

Ri-misurato: **ventidue mutazioni su ventidue muoiono**, comprese le quattro
che questo round aveva misurato sopravvivere. Suite 1719 verdi, ruff pulito.

### Conseguenza

Round 5 **NOT CONVERGED**. Il round 6 giudica questa remediation.

---

## Round 6: criterio, scritto prima del lancio

**2026-08-29, dopo il verdetto del round 5 e prima di lanciare il round 6.**

**Ambito**: `git diff 47a8d44..HEAD`, la remediation del round 5 — i commit
`281d5d7` e `c76c2f8`. Ogni file toccato rientra per intero.

**Le tre classi bloccanti restano identiche** e non sono state toccate dal
round 2 in poi: un difetto di correttezza nel codice di produzione, un
criterio che non può fallire, una chiusura dichiarata e non vera.

### Il conto onesto: sei round, sei volte lo stesso pattern

La remediation del round N introduce il bloccante del round N+1, e dal round 3
in poi **sempre dentro il testimone scritto per chiudere il round
precedente**. Il round 5 ne ha trovati tre in un colpo, e due erano forme già
nominate dai round 1 e 4: la fixture a una zona sola, e il valore corrotto che
coincide con quello vero.

**E il round 5 non li ha trovati tutti.** Dopo il suo verdetto, misurando il
testimone appena riparato, ne è emerso un quarto della stessa classe: i campi
erano catturati **per riferimento**, quindi `personality`, `conditions` e
`location` — le tre colonne mutabili — venivano confrontate con se stesse. La
forma che ri-assegna l'attributo moriva; una scrittura *in place*, che è la
forma che una regressione reale assume quando del codice entra dentro una
colonna JSON, lasciava tutti e 24 i test del file verdi. Chiuso con
`copy.deepcopy` e ri-misurato.

Questo è il fatto che il round 6 deve tenere davanti: **il round 5 ha
enumerato ciò che non aveva coperto, e in quell'elenco non c'era l'aliasing.**
Un revisore che dichiara i propri limiti resta comunque un revisore con
limiti, e la copertura di un round non è la copertura del problema.

### Che cosa questo round deve sospettare per primo

La mossa strutturale della remediation è **derivare l'insieme dei campi
confrontati da `Agent._meta.concrete_fields`** invece di enumerarli. È la
risposta giusta al bloccante 1, e proprio per questo va attaccata dove una
derivazione può mentire:

- `UNCOMPARABLE` esclude `id` e `created_at`. L'esclusione è giustificata nel
  commento, ma è un letterale scritto a mano dentro la riparazione di un
  letterale scritto a mano: che cosa succede se una colonna futura non può
  combaciare e nessuno la esclude, e che cosa succede se una che poteva
  combaciare finisce lì dentro.
- La guardia che nomina `personality`, `cunning`, `role`, `health`,
  `location` pinna il rilievo del round 5. È essa stessa un letterale: può
  restare verde mentre la derivazione a monte si svuota.
- Alcune colonne **non possono differire** fra i due neonati della fixture —
  `role` e `health` sono costanti per costruzione, `wealth` è zero
  incondizionatamente. Per quelle, una corruzione al medesimo valore è un
  no-op e non un difetto; ma il round dica esplicitamente quali colonne il
  testimone può solo confermare e non discriminare.
- Il wrapper di cattura ha una firma fissa. Se `build_newborn` acquisisce un
  parametro, il testimone si rompe rumorosamente o silenziosamente: quale
  delle due.

### Che cosa il round 5 ha dichiarato di NON aver coperto, e che questo round eredita

Sono i suoi passaggi, non i miei, e vanno chiusi o ri-dichiarati:

- la corruzione di `location`, mai misurata;
- i campi dell'evento fuori dal payload — `tick`, `event_type`, `simulation` —
  di cui nessuno ha verificato se qualcosa li asserisca;
- le quattro mutazioni sull'evento, **lette e non eseguite**;
- il diff di branch `develop..HEAD`, mai riletto per intero da nessun round.

### Che cosa il verdetto deve contenere

Se il round non produce nulla delle tre classi, deve **enumerare che cosa non
ha coperto**, e l'enumerazione del round 5 mostra che quell'elenco è la parte
più utile del verdetto, non un contorno. Cinque round su cinque hanno prodotto
un bloccante; un sesto che dice solo «nessun rilievo» non è un verdetto.

**Convergenza**: nessuna delle tre classi bloccanti. Cifre e frasi si
correggono nello stesso commit.

### Perché questo criterio può fallire

La remediation riscrive per intero la classe che regge dodici proprietà,
introduce una derivazione dal metamodello di Django, aggiunge una seconda zona
e una seconda classe sociale alla fixture, e cambia il modo in cui
l'istantanea è catturata. Le mutazioni eseguite sono ventiquattro e quattro
sono sopravvissute al primo colpo, tutte chiuse. Se il round non produce nulla
delle tre classi, la spiegazione ammessa è che quelle misure lo abbiano già
colto — non che il round non abbia guardato — e il verdetto deve dire quali
percorsi ha verificato per sostenerlo.

### Verdetto round 6: NOT CONVERGED

Un revisore, ambito ristretto, igiene rispettata. Un bloccante, classe 2, e di
nuovo dentro il testimone scritto per chiudere il round precedente: **settima
volta**.

**Bloccante — due delle trentaquattro colonne confrontate non possono
discriminare, e sono le due che in produzione variano.** La remediation del
round 5 ha sdoppiato zona e classe sociale e ha lasciato la posizione
inchiodata: `_agent` fissa `Point(50, 50)` per ogni agente, quindi le due
madri stavano sullo stesso punto in due zone diverse e i due neonati
ereditavano quel punto. Misurato, con la regressione che questo gate ha già
bloccato due volte su altre colonne — `newborns[-1].location =
newborns[0].location` — **1719 test su 1719 verdi**.

**La forma gemella sull'orientamento sessuale l'ha creata la remediation del
round 4.** Pinnare la distribuzione a `{"homosexual": 1.0}` uccideva la
corruzione a costante `= "heterosexual"`, ma dava a entrambi i neonati lo
stesso valore: il travaso da un neonato all'altro restava verde. La
riparazione di una forma aveva reso invisibile l'altra.

Delle diciassette colonne costanti fra i due neonati, quindici lo sono anche
in produzione — `build_newborn` le scrive come letterali o lascia il default
del modello — quindi per quelle il travaso è un no-op e non un difetto.
`location` e `sexual_orientation` erano le due eccezioni.

**Non bloccanti**: `UNCOMPARABLE` poteva assorbire in silenzio qualunque
colonna fuori dalle cinque nominate dalla guardia; il `tick` dell'evento di
nascita non aveva alcun testimone, ed è la colonna su cui ogni tasso dello
snapshot è raggruppato; la build map era ferma di un round.

**Le quattro domande del criterio hanno avuto risposta.** La guardia sui
cinque campi NON può restare verde mentre la derivazione si svuota: svuotando
il filtro, muore per prima. Il letterale delle esclusioni si rompe
rumorosamente nella direzione «colonna che non può combaciare», in silenzio
nell'altra — ora chiusa. Il wrapper di cattura si rompe rumorosamente se
`build_newborn` acquisisce un parametro. Le colonne che il testimone può solo
confermare sono state enumerate una per una.

**Classi 1 e 3: nessun rilievo**, e la ragione della classe 1 è che il diff in
ambito non tocca una sola riga di produzione.

### Che cosa è stato corretto in risposta

- **Due posizioni diverse** per le due madri, e la fixture **asserisce anche
  quella separazione**, accanto a zona e classe.
- **La distribuzione dell'era alterna** fra due valori non eterosessuali, così
  i due neonati differiscono sull'orientamento pur restando entrambi fuori dal
  valore che la corruzione a costante userebbe. La fixture asserisce che
  l'alternanza sia atterrata: se non lo fosse, fallisce invece di andare
  inerte.
- **`UNCOMPARABLE` è pinnata esattamente** a `{id, created_at}`: allargarla è
  ora un atto visibile nel diff che fallisce lì per primo.
- **Il `tick` dell'evento è asserito.**
- La build map avanza al round 6 in entrambe le lingue.

Ri-misurato: travaso della posizione, travaso dell'orientamento, `tick`
spostato di uno e allargamento di `UNCOMPARABLE` **muoiono tutti e quattro**.

### Un errore di processo, registrato perché non si ripeta

Durante la remediation ho annullato la mutazione sul file di test con
`git checkout --` su quel file, e poiché la riparazione non era ancora
committata **ho cancellato la riparazione insieme alla mutazione**. Le misure
erano già state prese e restano valide, ma il lavoro è stato riapplicato da
capo. La regola che ne discende: **non si mutano file di test non committati**
— o si committa prima, o si muta su una copia.

### Conseguenza

Round 6 **NOT CONVERGED**. Il round 7 giudica questa remediation.

---

## Round 7: criterio, scritto prima del lancio

**2026-08-29, dopo il verdetto del round 6 e prima di lanciare il round 7.**

**Ambito**: `git diff 98d8ab4..HEAD`, la remediation del round 6 (`f8815e7`).
Ogni file toccato rientra per intero.

**Le tre classi bloccanti restano identiche** dal round 2 e non sono state
toccate.

### Dove sta la debolezza del verdetto precedente, e da lì si comincia

Il round 6 ha enumerato le diciassette colonne che i due neonati della fixture
hanno identiche, e ne ha classificate **quindici come costanti anche in
produzione**, dichiarando testualmente di averlo stabilito «per lettura di
`build_newborn` e non per esperimento». È l'unica affermazione portante del
verdetto che non sia stata misurata, ed è esattamente la forma di ragionamento
che questo gate ha già smentito tre volte: una proprietà dedotta dalla lettura
e non provata per mutazione.

**La domanda del round 7 è quindi: quelle quindici sono davvero costanti in
produzione?** Per ciascuna, o si nomina il letterale o il default del modello
che la fissa, oppure si misura il travaso `newborns[-1].X = newborns[0].X` e
si dice se sopravvive. Se anche una sola di esse varia per neonato in una run
vera, è una colonna cieca e un bloccante di classe 2, identico a quello del
round 6 una colonna più in là.

### Gli altri punti da attaccare

- **L'iteratore che alterna le ere** presume che `load_template` sia chiamata
  esattamente due volte durante il passo. La fixture asserisce che
  l'alternanza sia atterrata, quindi un disallineamento fallisce rumorosamente
  — ma il round verifichi che sia davvero così e non per fortuna, e che cosa
  accade se un percorso futuro aggiunge una chiamata.
- **Le quattro asserzioni di forma della fixture** (zona, classe, posizione,
  orientamento) sono ora quattro letterali. Valgono ciò che il round 6 ha
  provato per la guardia dei cinque campi, o possono restare verdi mentre
  quello che asserivano si svuota?
- **`UNCOMPARABLE` pinnata a un'uguaglianza esatta** blocca l'allargamento, ma
  che cosa succede a chi ha una ragione legittima di allargarla.

### Debiti dichiarati, e dove vengono saldati

Il diff di branch `develop..HEAD` non è mai stato riletto per intero da nessun
round, ed è 1922 righe di produzione su 18 file. **Non è compito di questo
round**: è la review Matteo sull'intero diff prevista dal passo di chiusura, a
gate CONVERGED, e resta esplicitamente aperto fino a lì. Il round 7 non lo
legga e non lo dichiari coperto.

### Che cosa il verdetto deve contenere

Rilievi per gravità con classe, `file:riga` e misura. Se non produce nulla
delle tre classi, l'enumerazione esplicita di ciò che non ha coperto. Sei
round su sei hanno prodotto un bloccante, e cinque di questi sono nati dentro
il testimone scritto per chiudere il round precedente.

**Convergenza**: nessuna delle tre classi bloccanti.

### Perché questo criterio può fallire

La remediation cambia quattro cose in un file di test e nulla nel codice di
produzione: due posizioni, un iteratore di ere, un'uguaglianza sulle
esclusioni, un'asserzione sul tick. Le mutazioni eseguite sono quattro e
muoiono tutte. Se il round non produce nulla, la spiegazione ammessa è che la
superficie sia genuinamente piccola — non che il round non abbia guardato — e
il verdetto deve dirlo enumerando che cosa ha verificato, a partire dalle
quindici colonne che il round 6 non ha misurato.

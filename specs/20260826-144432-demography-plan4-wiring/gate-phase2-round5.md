# Gate di fase 2 — Round 5: criterio di convergenza

**Scritto prima del lancio del round, 2026-08-27.**

## Ambito

Il diff della revisione 5 rispetto alla revisione 4 (`c77dc91..HEAD`), limitato
a `specs/20260826-144432-demography-plan4-wiring/spec.md`. La spec intera si
legge per la coerenza; i rilievi nuovi valgono solo se nascono dal testo che il
diff introduce o modifica.

## Lista di ricontrollo

Il round 4 ha lasciato aperti, e la revisione 5 dichiara di chiudere:

1. **Voce 1 / N-20** — FR-016 non dichiara più affine ciò che cita come
   variabile; FR-016a dichiara il budget come **limite superiore** ai
   coefficienti di caso peggiore e fissa il numero di zone; SC-005 parte B
   diventa un limite superiore che almeno una fixture deve **raggiungere**.
2. **Voce 3 / N-18 / N-19** — la chiusura di FR-017 si dichiara
   sull'**inventario** per sezione e affermazione, mai su numeri di riga; il
   grep è declassato a innesco di revisione da FR-017a, con la ragione
   misurata (zero occorrenze dei pattern inglesi sul file italiano).
3. **N-21** — l'inventario include §4.1.4 e §4.2, e le occorrenze di
   calibrazione sono dichiarate da non toccare.
4. **N-22** — SC-007 impone un rapporto fra i sessi diverso da uno.
5. **N-23** — l'enumerazione dei siti di creazione è sostituita dal vincolo di
   schema, in tutti i punti in cui la spec ne parlava.

## Criterio di convergenza

Il round dà **CONVERGED** se e solo se:

1. Ciascuna delle cinque voci è **RESOLVED con evidenza**: riga citata della
   revisione 5 e ragione per cui indebolirla riaprirebbe il rilievo. Doppio
   test su ogni success criterion — l'implementazione più pigra lo rende rosso,
   E il codice che i Non-goals proteggono può soddisfarlo. Non falsificabile o
   insoddisfacibile = NOT RESOLVED.
2. **Nessun rilievo nuovo INCORRECT o UNJUSTIFIED** nell'ambito del diff, con
   le asserzioni fattuali nuove verificate contro il sorgente: la variabilità
   dichiarata del costo di `resolve_heirs`; le due query per zona di
   `compute_subsistence_threshold`; ogni riga della tabella di FR-017 contro il
   whitepaper in **entrambe** le lingue, e la classificazione delle occorrenze
   «Plan 4» fra da-aggiornare e da-lasciare; il default di `sex_ratio`; il
   vincolo NOT NULL sul seme.
3. Ogni rilievo nuovo INCONSISTENT o MISSING è bloccante (→ NOT CONVERGED)
   oppure dichiarato non bloccante con motivazione scritta.

**Regola di arresto, scritta prima del round** e derivata dai quattro round già
girati: dal round 2 in poi ogni round ha trovato meno e più piccolo, e nessuno
ha toccato codice di produzione, perché non ce n'è ancora. Il gate converge
quando un round non produce né un requisito falso rispetto al sorgente né un
criterio che non può fallire o non può passare. Cifre imprecise, riferimenti
che puntano male e frasi da riformulare si correggono nello stesso commit e
**non** riaprono il gate: sono la classe che i round 3 e 4 hanno già degradato
a coda. Le due classi bloccanti restano tali di proposito — sono le uniche che
propagano nel codice.

## Verdetto

**CONVERGED** (round concluso 2026-08-27, auditor avversariale su Opus, giudicato
contro la regola di arresto scritta sopra e non contro il risultato).

Tutte e cinque le voci RESOLVED con evidenza. Il round non ha prodotto **né** un
requisito falso rispetto al sorgente **né** un criterio che non può fallire o non
può passare, che sono le due sole classi bloccanti: le tre asserzioni nuove sul
codice reggono parola per parola — il contratto di costo variabile di
`resolve_heirs`, le due query per zona di `compute_subsistence_threshold`, il
default `1.0` di `sex_ratio` — il vincolo NOT NULL sul seme regge nello schema e
nel serializer, e i due success criterion riscritti superano entrambi i lati del
doppio test.

**Coda non ostativa, corretta nello stesso commit** (nessuna riapre il gate):
la riga Abstract dell'inventario descriveva un'affermazione inesistente e ora
nomina la campagna empirica; la riga Appendice B nomina il vincolo della
campagna e la directory `validation/` invece di un rinvio d'integrazione che lì
non c'è; FR-016a dichiara che le nascite costano un numero di query indipendente
dal loro numero e stanno dentro il termine fisso; SC-007 passa a sei campi su
dieci e impone almeno una coppia attiva, perché `couples_active` ha `default=0`;
l'inventario completa §4.1.5 e §11 e aggiunge §7.4 e la clausola di §4.1.3; il
refuso a spec.md:394 è corretto.

**Il pattern, registrato perché è il valore del gate.** Dal round 2 al round 4 le
classi trovate sono state due, entrambe propaganti: criteri che non potevano
fallire e requisiti falsi rispetto al codice. Il round 5 non ne ha trovato
nessuna delle due: quello che resta è un inventario documentale con due etichette
sbagliate, due sotto-conteggi e un refuso — difetti di puntamento in una tabella
la cui funzione è indirizzare chi revisiona, e che indirizzava comunque alla
sezione giusta. È esattamente la classe che la regola di arresto degradava a coda
prima che il round girasse.

**Il gate tecnico di fase 2 è chiuso; il gate pesante no.** Il CLAUDE.md del
progetto richiede la validazione umana esplicita della spec e non ammette
eccezioni per quel gate. La spec è pronta per il piano di fase 3, ma
l'implementazione non parte finché l'utente non ratifica.

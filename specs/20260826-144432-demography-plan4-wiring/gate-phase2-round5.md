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

*(da compilare a round concluso)*

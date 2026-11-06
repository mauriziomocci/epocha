# Gate di fase 2 — Round 4: criterio di convergenza

**Scritto prima del lancio del round, 2026-08-27.**

## Ambito

Il diff della revisione 4 rispetto alla revisione 3 (dal commit della revisione
3 a HEAD), limitato a `specs/20260826-144432-demography-plan4-wiring/spec.md`.
La spec intera si legge per la coerenza; i rilievi nuovi valgono solo se
nascono dal testo che il diff introduce o modifica.

## Lista di ricontrollo

Il round 3 ha lasciato aperti, e la revisione 4 dichiara di chiudere:

1. **B1 + voce 1** (FR-016/SC-005): il budget è ora una funzione affine
   dichiarata degli eventi vitali (`a + b·morti + c·intenti + d·fughe`), il
   divieto riguarda le sole query per **agente vivo**, e SC-005 ha due parti —
   raddoppio dei vivi a eventi pari (con almeno un evento per tipo, fixture
   inerte vietata) e verifica dei coefficienti a popolazione fissa.
2. **B2** (FR-010a): il requisito è cancellato; l'edge case Determinismo, la
   sezione «Plan 4» e una FAQ nuova spiegano perché A-5 non è raggiungibile dal
   percorso cablato e dove resta tracciato.
3. **B3** (FR-017): l'inventario colloca le quattro frasi in §11 e aggiunge
   Abstract, §4.1.5, §7.5, §9, §10, §12, Appendice B; la verifica di chiusura è
   il grep dichiarato, non l'inventario.
4. **B4 + metà voce 11** (SC-007): il tick misurato contiene almeno una
   nascita, una morte e uno spostamento di zona, con la motivazione sui quattro
   campi a default.
5. **B5**: `fit_hadwiger` citato a §6.3.
6. **N-14**: l'eccezione dei Non-goals nomina firma e lettura del contatore in
   `process_emergency_flight`, non la sola firma.
7. **N-15**: FR-011 colloca il passo contatore dopo la successione e prima
   della migrazione, e SC-003 lo prova per mutazione.
8. **N-16**: US2 porta il test per FR-005 e FR-005a (coppia formata a T
   concepisce a T; coppia separata a T no).
9. **N-17**: una FAQ dichiara che la collocazione del blocco rispetto al chord
   è una decisione del piano di fase 3.

## Criterio di convergenza

Il round dà **CONVERGED** se e solo se:

1. Ciascuna delle nove voci è **RESOLVED con evidenza**: riga citata della
   revisione 4 più la ragione per cui indebolirla riaprirebbe il rilievo. A
   ogni success criterion si applica il doppio test: l'implementazione più
   pigra che soddisfa gli FR lo rende rosso, E il codice che i Non-goals
   proteggono può soddisfarlo — un criterio non falsificabile e un criterio
   insoddisfacibile sono entrambi NOT RESOLVED.
2. **Nessun rilievo nuovo INCORRECT o UNJUSTIFIED** nell'ambito del diff, con
   le asserzioni fattuali nuove verificate contro il sorgente (fra le altre: il
   costo contrattuale per morto e per intento citato in FR-016; lo schema NOT
   NULL del seme e i tre siti di creazione; l'inventario FR-017 contro il
   whitepaper; i default dei quattro campi di snapshot).
3. Ogni rilievo nuovo INCONSISTENT o MISSING è bloccante (→ NOT CONVERGED)
   oppure dichiarato non bloccante con motivazione scritta.

Il criterio può fallire: fallisce se una voce è chiusa nella prosa ma non nel
requisito, se un'asserzione non regge al sorgente, o se una correzione ha
introdotto una contraddizione nuova fra FR, SC, Non-goals e FAQ.

## Verdetto

**NOT CONVERGED** (round concluso 2026-08-27, auditor avversariale su Opus).
Sette voci su nove RESOLVED. Restano aperte la voce 1 e la voce 3, più quattro
bloccanti nuovi e due non bloccanti, tutti riverificati dal supervisore contro
il sorgente:

- **Voce 1 / N-20**: la parte A di SC-005 è sanata; la parte B chiede
  un'uguaglianza esatta con un `b` che il docstring di `resolve_heirs` dichiara
  **variabile** con la struttura familiare del defunto (zero query per il
  coniuge senza coppia attiva, zero per la famiglia estesa senza genitore
  registrato), quindi un'implementazione corretta esce rossa. In più il termine
  fisso dipende dal numero di zone: `compute_subsistence_threshold` esegue due
  query per zona (`demography/context.py:24-27`).
- **Voce 3 / N-18 / N-19**: la verifica di chiusura di FR-017 poggia su un
  grep. Sul whitepaper italiano i due pattern inglesi danno **zero**
  occorrenze, quindi metà verifica è verde per costruzione; sull'inglese danno
  dodici righe, di cui cinque dell'inventario e sette rinvii di calibrazione
  che il merge lascia **veri**. Cieco su sette degli otto siti che la revisione
  4 aveva appena aggiunto.
- **N-21**: l'inventario manca §4.1.4 e soprattutto §4.2, che afferma «a
  differenza dei moduli di demografia di §4.1.x, l'economia comportamentale è
  davvero viva nella pipeline per tick» — un confronto che il merge capovolge,
  in un capitolo che FR-017 non nominava.
- **N-22, non bloccante**: `sex_ratio` ha `default=1.0`, quindi su una fixture
  bilanciata è la quinta trappola di SC-007.
- **N-23, non bloccante**: l'enumerazione «tre siti di creazione» è incompleta
  — `SimulationViewSet.perform_create` è una quarta via — benché la conclusione
  regga, perché il vincolo è nello schema.

La revisione 5 chiude tutti e sei: budget come limite superiore con coefficienti
di caso peggiore e numero di zone fisso (FR-016a, SC-005 in due parti con il
limite raggiunto almeno una volta); inventario tabellare per sezione e
affermazione, con §4.1.4 e §4.2 aggiunti, il grep declassato a innesco di
revisione (FR-017a) e le occorrenze di calibrazione dichiarate da non toccare;
`sex_ratio` diverso da uno nella fixture di SC-007; l'enumerazione dei siti
sostituita dal vincolo di schema.

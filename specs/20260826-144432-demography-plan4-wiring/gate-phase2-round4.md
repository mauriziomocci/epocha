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

*(da compilare a round concluso)*

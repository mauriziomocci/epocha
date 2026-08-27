# Gate di fase 2 — Round 3: criterio di convergenza

**Scritto prima del lancio del round, 2026-08-27.**

## Ambito

Il diff della revisione 3 rispetto alla revisione 2 (`ef732ad..HEAD`), limitato a
`specs/20260826-144432-demography-plan4-wiring/spec.md`. La spec intera si legge
per la coerenza, ma i rilievi nuovi valgono solo se nascono dal testo che il
diff introduce o modifica.

## Lista di ricontrollo

Il round 2 ha lasciato aperti, e la revisione 3 dichiara di chiudere:

1. **Bloccante 7 (round 1), riaperto al round 2**: SC-005 deve diventare rosso
   su un'implementazione N+1. La revisione 3 lo riscrive come conteggio
   **identico** a N e 2N, con il valore atteso scritto nel test.
2. **N-1**: la frase su `Agent.age`, ora riscritta in FR-013 con la regola di
   precedenza fra `birth_tick` e `age` e l'obbligo che nessun agente vivo resti
   con `birth_tick` NULL dopo l'inizializzazione.
3. **N-2**: il conteggio dei moduli senza entry point per tick (due, non tre) e
   il ruolo di `process_inheritance_batch`.
4. **N-3**: il predicato di attivazione unico (FR-008) e l'allineamento di US1
   test 1 e della FAQ.
5. **N-4**: l'indice del passo limitato agli eventi emessi dagli orchestratori,
   con la motivazione, contro il Non-goal sui moduli.
6. **N-5**: FR-005a ora dichiara la collocazione delle separazioni (prima delle
   formazioni, entrambe prima della fertilità) con la regola unica sugli intenti
   di T-1, e torna mutation-provable.
7. **N-6**: la descrizione dei tre casi di degradazione (chiave assente, file
   mancante, template malformato) e il divieto di handler ciechi nel cablaggio
   nuovo.
8. **N-7**: FR-007 riscritto come proprietà d'ordine reale (migrazione dopo
   mortalità e successione), con la nota che le statistiche di zona correnti
   sono garantite per costruzione.
9. **N-8**: il riferimento nei Rischi corretto a FR-003.
10. **N-9**: la migrazione volontaria dichiarata fuori scope con la motivazione
    su `zone_stats` nel chord; il Non-goal e la sezione dedicata allineati.
11. **N-10**: FR-015 elenca tutti i campi dati del modello e SC-007 asserisce
    campo per campo contro una fixture.
12. **N-11**: la sezione che elenca ciò che il whitepaper affida all'etichetta
    «Plan 4» e questo work item non consegna, l'inclusione di A-5 via FR-010a,
    e l'estensione di FR-017.
13. **N-12**: il titolo non promette più la validazione.
14. **N-13**: il refuso «aborte».

## Criterio di convergenza

Il round dà **CONVERGED** se e solo se:

1. Ciascuna delle quattordici voci sopra è **RESOLVED con evidenza**: riga o
   passaggio della revisione 3 citato, più la ragione per cui indebolirlo
   riaprirebbe il rilievo. Un criterio riscritto che resta soddisfacibile
   dall'implementazione più pigra che rispetta gli FR è NOT RESOLVED.
2. **Nessun rilievo nuovo INCORRECT o UNJUSTIFIED** nell'ambito del diff. Le
   asserzioni fattuali che la revisione 3 introduce o modifica si verificano
   contro il sorgente — fra le altre: i tre gestori di `apply_agent_action`
   (`engine.py:335-337`, `:350-360`, `:361-362`); i siti di emissione eventi
   dentro i moduli (`migration.py:1000,1770,1803`, `inheritance.py:3575`);
   `resolve_separate_intents` su intenti di T-1 (`couple.py:335`); il fallback a
   zero dell'helper RNG e il debito A-5; l'elenco dei campi di
   `PopulationSnapshot` (`demography/models.py:155-176`); `generator.py:179` e
   `:398` con `fertility.py:255-256`; il contratto zero-query di
   `build_migration_outlook`.
3. Ogni rilievo nuovo INCONSISTENT o MISSING è bloccante (→ NOT CONVERGED)
   oppure dichiarato non bloccante con motivazione scritta.

Il criterio può fallire: fallisce se una voce è chiusa nella prosa ma non nel
requisito, o se un'asserzione fattuale della revisione 3 non regge il confronto
col sorgente, o se una correzione ha introdotto una contraddizione nuova fra FR,
SC, Non-goals e FAQ.

## Verdetto

*(da compilare a round concluso)*

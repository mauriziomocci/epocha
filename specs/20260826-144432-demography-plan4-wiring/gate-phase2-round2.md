# Gate di fase 2 — Round 2: criterio di convergenza

**Scritto prima del lancio del round, 2026-08-27.**

## Ambito

`git diff e8531a4..ef732ad`, limitato a
`specs/20260826-144432-demography-plan4-wiring/spec.md`. Gli altri tre file del
diff (build map, memoria) non sono oggetto del gate di fase 2.

## I nove bloccanti del round 1

Ricostruiti dal messaggio di commit di `ef732ad`, che è il record persistito:

1. **Reframe**: Plan 4 possiede gli orchestratori di nascita e morte; tre moduli
   su cinque non hanno punto d'ingresso per tick. La spec deve dire chi crea il
   neonato, con quale nome, chi marca il morto, chi emette gli eventi.
2. **`birth_tick`**: unica sorgente di invecchiamento; senza requisito
   d'inizializzazione, mortalità e fertilità restano congelate.
3. **Coppie iniziali**: tre template su cinque, default incluso, danno
   probabilità di nascita zero senza coppia attiva; nessun codice le crea.
4. **Ordine coppia-fertilità**: coppie formate a T dagli intenti di T-1; se il
   passo coppia seguisse la fertilità, ritardo sistematico di un tick su tutta
   la natalità.
5. **RNG**: il requisito autorizzava uno stream per agente, che dà a ogni agente
   lo stesso sorteggio. Serve uno stream per (tick, fase) condiviso in ordine
   deterministico.
6. **Assumption 1 dissolta**: `apply_inheritance_at_birth` consuma estrazioni in
   numero indipendente dai genitori; due neonati nello stesso tick identici. Il
   difetto entra nello scope, SC-006 lo testimonia.
7. **Criterio costo non falsificabile**: sostituito da «nessuna query per
   agente, verificato raddoppiando la popolazione».
8. **Criterio d'invarianza non falsificabile**: sostituito da «stesso numero di
   query e nessun evento demografico a demografia spenta».
9. **Criterio di tracciabilità non falsificabile**: il tipo evento partiziona già
   per modulo; sostituito dall'indice del passo nel payload.

## Criterio di convergenza

Il round dà **CONVERGED** se e solo se valgono tutte e tre le condizioni:

1. **Ciascuno dei nove bloccanti è RESOLVED con evidenza**: il rilievo si
   considera chiuso solo se l'auditor cita la riga o il passaggio della
   revisione 2 che lo chiude e spiega perché rimuovere o indebolire quel testo
   riaprirebbe il rilievo. Un rilievo chiuso «per lettura complessiva» non è
   chiuso.
2. **Nessun rilievo nuovo INCORRECT o UNJUSTIFIED** dentro l'ambito del diff. Le
   asserzioni fattuali che la revisione 2 introduce o modifica — occorrenze di
   `EventType.DEATH|BIRTH` fuori dai test, i sette punti con
   `config.get("demography_template", ...)`, la regola che `migration.py` già
   applica, la derivazione RNG a `inheritance.py:1344`, `Agent.age` mai
   assegnato a runtime, `PopulationSnapshot` mai scritto, i tre template su
   cinque a probabilità zero senza coppia, le coppie formate a T dagli intenti
   di T-1, il comportamento di `apply_agent_action` su `FileNotFoundError`
   contro chiave assente — vanno verificate contro il codice sorgente, non
   contro la memoria dell'auditor.
3. **Ogni rilievo nuovo INCONSISTENT o MISSING** è o bloccante — e allora il
   verdetto è NOT CONVERGED — o dichiarato non bloccante con motivazione
   scritta.

Il criterio può fallire: fallisce se anche un solo bloccante risulta chiuso
nella prosa ma non nel requisito (per esempio un requisito riscritto che resta
non falsificabile), o se una qualsiasi asserzione fattuale della revisione 2
non regge il confronto col sorgente.

## Verdetto

**NOT CONVERGED** (round concluso 2026-08-27, auditor avversariale su Opus,
ambito rispettato).

Sette bloccanti su nove RESOLVED con evidenza. Il bloccante 7 è NOT RESOLVED:
SC-005 nella forma «raddoppiando la popolazione il conteggio non raddoppia» è
soddisfatto da qualunque implementazione N+1, perché con `q` query per agente e
`c` query fisse vale `2qN + c < 2(qN + c)` per ogni `c > 0`.

Tre asserzioni fattuali INCORRECT, verificate a campione dal supervisore contro
il sorgente: «`Agent.age` non viene mai assegnato a runtime» (falso:
`world/generator.py:179` e `:398`, letto come fallback da `fertility.py:255-256`);
«tre moduli su cinque non hanno un punto d'ingresso per tick» (sono due:
`process_inheritance_batch` è un entry point per tick, `inheritance.py:3156-3157`);
«degrada solo su `FileNotFoundError`» (sopra il gestore c'è l'`except Exception`
di `engine.py:361-362`).

Tre INCONSISTENT bloccanti: doppio predicato di attivazione (FR-008 contro FAQ e
US1); indice del passo su «ogni evento demografico» contro il Non-goal che vieta
di toccare i moduli (gli eventi nascono anche dentro `migration.py:1000,1770,1803`
e `inheritance.py:3575`); FR-005a dichiarato mutation-provable senza dichiarare
la collocazione, quindi senza proprietà da mutare.

Due criteri residui che non possono fallire: FR-007 dentro SC-002 (le statistiche
di zona del tick corrente sono garantite per costruzione da
`migration.py:1574-1586`, nessuno scambio di passi le falsifica) e SC-007
(«leggibile» passa su uno snapshot coi soli default; FR-015 copre 8 campi su 12
del modello).

Non bloccanti dichiarati con motivazione: riferimento pendente FR-002→FR-003 nei
Rischi; zone_stats scoperto per la migrazione volontaria nel ciclo decisionale e
promesse del whitepaper all'etichetta «Plan 4» più larghe del work item (decisioni
di scope, portate alla revisione 3 e flaggate per la ratifica del gate pesante);
titolo che promette «validazione»; un refuso.

Il registro integrale del round è nel transcript dell'agente; i rilievi sono
riportati per intero nel criterio del round 3, che li usa come lista di
ricontrollo.

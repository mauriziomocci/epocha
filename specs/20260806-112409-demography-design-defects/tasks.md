# Tasks — Demography design defects

> **Ricostruito il 2026-08-11, al gate di fase 6.** Questo file mancava: il
> percorso Spec Kit lo elenca come deliverable della fase 4 e l'audit del
> codice lo ha rilevato come assente. È ricostruito dal `plan.md` e dalla
> storia dei commit, quindi registra ciò che è stato **eseguito**, non ciò che
> era stato pianificato prima di eseguirlo. La distinzione va tenuta: un
> tasks.md scritto dopo non ha svolto la funzione di guida per cui esiste, e
> il modo di non ripetere l'omissione è scriverlo prima, non scriverlo meglio.

Ordine e numerazione seguono `plan.md`. Ogni voce chiusa porta il commit che
la ha chiusa.

## Fase 0 — Deliberazioni scientifiche (GATE PESANTE)

- [x] **0.1a** Famiglia distribuzionale: normale troncata contro scala latente logit. Deciso per la troncata; il logit era stato adottato in `research.md` e poi ribaltato quando l'argomento sulla massa di bordo è collassato (la banda che lo comprava era chiusa dai valori dichiarati dall'emendamento stesso).
- [x] **0.1b** Orizzonte di pianificazione della migrazione: valore attuale scontato per Todaro (1969) con orizzonte e definizione di costo di Sjaastad (1962). Harris & Todaro (1970) è a un solo periodo e non può licenziare un orizzonte.
- [x] **0.1c** Orizzonte di sussistenza: grandezza derivata, nessun `N` globale.
- [x] **0.2** Ordini di grandezza dei parametri.
- [x] **0.3** Verifica dell'attribuzione a Chetty: **fabbricata**. Sostituita con Black & Devereux (2011), Tabella 3, Plug congiunto, `ρ = 0,60` come SOMMA.
- [x] **0.4** Scrittura dell'emendamento A1-A12 in coda alla spec di design.
- [x] **0.5** GATE PESANTE: audit avversariale fino a CONVERGED. Converso al round 11, dopo due cancellazioni strutturali (tetto sulla massa di bordo, banda di ampiezza), entrambe di soglie ancorate al valore che dovevano ammettere.

## Fase 1 — Validazione dei template (US 7, FR-014, SC-015a)

- [x] **1.1** Schema dichiarativo e sei clausole di `validate_template`, ciascuna provata per mutazione.
- [x] **1.2** `truncated_moments.py`: punto fisso deterministico su griglia, regione ammissibile, dispersione di rango.
- [x] **1.3** I cinque template dichiarano `era_noise`; rimozione di `heritability.default`.
- [x] **1.4** Chiusura dell'insieme dei caratteri trasmessi.
- [x] **1.5** Whitepaper §6.2 in entrambe le lingue + riga di doc-sync mancante.

## Fase 2 — Nucleo della trasmissione

- [x] **2.1** Famiglia distribuzionale e kernel poligenico (FR-002, FR-003) — le tre scale del residuo dall'identità di varianza, coefficiente a genitore singolo dimezzato, segnale sullo scostamento dalla media d'era.
- [x] **2.2** Parametri di rumore per era (FR-004) — e la scoperta che l'istruzione leggeva una chiave che lo schema ora rifiuta.
- [x] **2.3** Innovazione dell'istruzione e di Clark (FR-002b) — `5e28677`, `4d3a17a`, `40dcc8b`.
- [x] **2.4** Accoppiamento assortativo (FR-013, SC-017) — `6fb8ca4`. Ha richiesto lo strumento che mancava: nessun solver committato poteva rigenerare le soglie che A4 pubblicava come misurate.

## Fase 3 — Successione ed economia

- [x] **3.1** Quota coniugale shari'a per genere (FR-005) — `ca4e519`.
- [x] **3.2** Conservazione esatta dell'imposta, costruzione di Sterbenz (FR-007) — `ca4e519`.
- [x] **3.3** Valori di regressione dei template, `ρ = 0,60` (FR-009) — `ca4e519`.

## Fase 4 — Migrazione

- [x] **4.1** Guadagno atteso come valore attuale (FR-006) — `923846f`.
- [x] **4.2** Orizzonte di sussistenza applicato a migrazione e fertilità (FR-008) — `923846f`, `8a969fc`.
- [x] **4.3** Stabilità di zona dichiarata valore di simulazione (FR-015) — `923846f`.

## Fase 5 — Chiusura

- [x] **5.1** Whitepaper §4.1.2, §4.1.4, §4.1.5, §6.2 e §11 in entrambe le lingue (FR-010), con la dichiarazione esplicita di non comparabilità.
- [x] **5.2** Suite intera, lint, controllo migrazioni.
- [x] **5.3** GATE PESANTE: audit avversariale sul codice fino a CONVERGED. Round 1: **NOT CONVERGED**, 18 rilievi. Round 2: **NOT CONVERGED**, 9, di cui il bloccante introdotto dalla remediation del round 1. Round 3: **NOT CONVERGED**, 13, con la stessa classe di difetto sulla citazione colta per la terza volta. Round 4: **NOT CONVERGED**, 7, di nuovo la citazione — chiusa ora con una guardia strutturale (`test_citation_hygiene.py`) invece che con una quinta passata a mano; ha trovato sette occorrenze in più al primo colpo. Round 5: **NOT CONVERGED**, 7, e il bloccante è che la guardia strutturale del round 4 non prendeva il difetto per cui era stata scritta — saltava l'intera finestra appena vi compariva una citazione corretta, e ogni citazione reale ne contiene una. Ricostruita: ogni riferimento giudicato per sé, intero repository, tre sonde che scrivono una violazione su disco e verificano che venga presa. Round 6: **NOT CONVERGED**, 11, con cinque nuove evasioni dimostrate contro la guardia ricostruita — tutte riconducibili a un limite espresso in numero di righe e tarato sull'ultimo caso visto. Sostituito dalla nozione di regione di citazione, con il limite residuo dichiarato e messo sotto test. Round 7: **NOT CONVERGED**, 8. La frase ritrattata sopravviveva nella build map, cioè nella fonte di verità; il limite espresso come paragrafo produceva falsi positivi dove non c'è nulla su cui spezzare, e lo split di elenco tagliava a metà una voce author-date. Il limite è la **regione di citazione**, e la guardia è scesa dal 16% al 2% della suite. Round 8: **NOT CONVERGED**, 10, e il verdetto è che la guardia andava tagliata: il bound di prossimità sopprimeva un falso positivo inesistente e apriva un buco reale a 812 caratteri. Rimosso con due test che non legavano nulla. Regola di processo adottata: la guardia si estende solo su una violazione osservata, mai su una costruita. Round 9: **NOT CONVERGED**, 6, ambito stretto al solo commit di remediation del round 8, e il bloccante e' che la difesa contro la citazione **come e' stata davvero scritta** non aveva testimone: le quattro voci di `FORBIDDEN_TITLES` sono minuscole e tutti i payload di prova erano minuscoli, quindi togliere `.lower()` lasciava diciotto test su diciotto verdi, mentre la violazione storica — `2026-04-18-demography-design-it.md:1893` e `inheritance.py:6` al commit `5a2713e` — porta le maiuscole di un titolo di capitolo. Altre tre diramazioni vive erano mascherate dalla stessa causa strutturale, l'unione `_title_offenders + _chapter_offenders` asserita come somma: un payload che ne esercita due non ne dimostra nessuna, e le due asserzioni ora sono separate. La forma numerata di `LIST_ITEM`, rimessa al round 8 per una bibliografia numerata che nel repository non esiste, e' cancellata: con e senza, 53 regioni, 20 file, zero offender. E la cifra "sotto le 300 righe" era falsa su quattro artefatti piu' l'oggetto del commit — serie vera 167, 543, 453 righe totali, con "sotto le 300" vero solo delle righe di codice. Round 10: **NOT CONVERGED**, 5 rilievi, di cui **2 bloccanti** secondo il criterio scritto in `5b33d4b` prima del round, e **zero in classe 1** (il diff non tocca un solo file di produzione, come i round 6, 7, 8 e 9). Il bloccante e' che **la correzione del round 9 ha cancellato un testimone mentre ne aggiungeva un altro**: capitalizzare il payload del titolo spezzato dal wrap ha dato a `.lower()` il testimone che gli mancava, giusto, ma nella stessa edit ha spostato l'a capo fuori dal titolo, lasciando l'appiattimento degli spazi — diramazione viva, dichiarata due volte in prosa — senza piu' nulla che la difendesse. Misurato sui due lati: la mutazione di `_normalise` uccide a `ad1d942` e sopravvive a `64be598`. Il secondo bloccante e' l'altra meta' della stessa correzione: separare le due liste di offender era necessario ma `assert titles` verifica solo la non-vacuita', quindi tre payload non potevano testimoniare per quattro stringhe proibite e `componenti della varianza` restava cancellabile a suite verde. Chiuso sulla classe: l'asserzione nomina QUALE titolo attende, un quarto payload porta la forma che il whitepaper italiano aveva davvero a `5a2713e`, e `test_every_forbidden_title_has_a_witness` rifiuta una quinta stringa senza sonda. Fuori dalle classi bloccanti: la cifra delle righe spese era sbagliata (27, non 25) ed e' stata rimossa perche' si autoinvalida a ogni edit; tre voci di `HTML_ENTITIES` avevano zero occorrenze nel repository e sono cancellate per la stessa regola applicata a `\d+\.`; e un inventario di tre diramazioni senza testimone ma senza violazione osservata dietro, che per la regola di processo NON vanno coperte. **Seconda regola di processo adottata**: quando cambia un payload o una costante, la batteria di mutazioni va rilanciata anche contro la versione PRECEDENTE — una correzione non si giudica dai mutanti che uccide ma da quelli che smette di uccidere. Round 11: **CONVERGED**. Sette rilievi, **nessuno nelle due classi bloccanti**. La domanda principale era se il round 10 avesse fatto a sua volta cio' che rimproverava al round 9: batteria di 34 mutazioni eseguita contro `64be598` e contro `37cc452`, **nessun mutante che uccideva prima sopravvive adesso** e quattro in piu' muoiono. Tutti e venti i test dimostrati uccidibili, ciascuno da una mutazione nominata. I sette rilievi sono cifre e frasi: la tabella di prova del round 10 nominava una mutazione e pubblicava i numeri di un'altra (ora nomina quella stretta e stampa entrambe le colonne); `&nbsp;` poggiava su una provenienza che `git log -S` smentisce — non e' mai comparsa fuori dal file della guardia — ed e' ora un'**eccezione dichiarata** con il giudizio scritto accanto, invece di un'eccezione taciuta; "12 occorrenze" di `&amp;` erano 13 su 12 righe; la "serie completa" del round 9 saltava `d25574f`; il commento sopra `INJECTION_CASES` prometteva l'opposto di cio' che il test faceva; il registro si intitolava "rounds 1 to 8" e ne tabulava dieci; e F-1 del round 9 restava "Closed" benche' il round 10 ne avesse dimostrato la riapertura. Tutti e sette corretti nello stesso commit, come il criterio prescrive, con la seconda regola applicata alla remediation stessa: batteria in differenza contro `37cc452`, risultati identici su ogni mutazione misurata. **Totale 101 rilievi, tutti chiusi. Sedici criteri che non potevano fallire.** GATE CHIUSO.
### Il criterio di arresto del gate 5.3, scritto prima del round 10

Nove round senza un criterio scritto, e la ragione per cui va scritto **adesso** e' che dopo aver visto girare il round 10 non sarebbe piu' un criterio ma una trattativa. La misura che lo motiva: **il codice scientifico eseguibile e' fermo dal round 3**. I round 1-3 toccavano `inheritance.py`, `migration.py`, `template_loader.py`, `truncated_moments.py`; il round 4 tocca `inheritance.py` per due righe di commento e aggiunge una guardia di dominio a `truncated_moments.py`; il round 5 solo docstring; **i round 6, 7, 8 e 9 non toccano un solo file di produzione**. Sei round su un modello che non cambia. Non sono sprecati — il `.lower()` senza testimone del round 9 era grave, perche' la guardia e' l'unica cosa che impedisce il ritorno di un difetto gia' ricomparso cinque volte — ma dicono che l'oggetto del gate si e' spostato dal modello alla prosa che lo descrive, e la prosa nuova e' sempre criticabile: tre dei sei rilievi del round 9 sono di quella specie.

**Il gate 5.3 converge quando un round non produce nessuna delle due classi seguenti:**

1. un difetto sul **codice di produzione** — `epocha/apps/**/*.py` fuori da `tests/`;
2. un **criterio che non puo' fallire** — un test verde che resta verde quando si inietta il difetto che dovrebbe testimoniare, ovunque esso viva, test compresi.

**Non bloccano il merge**, si correggono nello stesso commit e non riaprono il gate: cifre sbagliate in prosa, frasi contraddittorie, docstring superate dai fatti, formulazioni migliorabili, e ogni rilievo su artefatti che non eseguono.

La seconda classe resta bloccante **apposta**, ed e' cio' che impedisce a questo criterio di auto-assolversi: declassare i test sarebbe buttare via la lezione che questo work item ha pagato quattordici volte. Un test che non puo' fallire e' il meccanismo che sorveglia il codice, non commento sul codice.

- [x] **5.4** Merge e ri-pin del whitepaper al commit di merge — ratificato dall'utente e mergiato in `develop` con `--no-ff` al commit `fb893f5`. Entrambi i whitepaper ri-pinnati a quel commit; il merge ha reso false due frasi che dichiaravano il pin ancora fermo allo stato pre-emendamento, corrette in loco con la nota del perche', non sostituite in silenzio. Memory backup sincronizzato, build map aggiornata e ripubblicata.

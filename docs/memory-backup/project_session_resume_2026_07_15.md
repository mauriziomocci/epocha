---
name: project_session_resume_2026_07_15
description: "Stato di ripresa del progetto Epocha: in testa lo stato al 2026-11-26 (fecondità coniugale ferma sui difetti dell'economia, spec di Becker parcheggiata), sotto lo storico del Plan 4 e dei difetti di design"
metadata: 
  node_type: memory
  type: project
  originSessionId: 7c7baa02-253c-4d77-885d-7497b3471918
  modified: 2026-08-12T12:30:24.862Z
---

# AGGIORNAMENTO 2026-11-26 — fecondità coniugale, fattore di Becker, difetti dell'economia

**Da leggere per prima** la nota di ripresa:
`~/Documents/workspace/Diario/2026/11/2026-11-26/epocha-nota-di-ripresa.md`
(quattro problemi in ordine di dipendenza, prossimi passi, file, trappole).
In breve, stato al 2026-11-26:

- **Difetti dell'economia quando nascono bambini** (§4.8 auditato; build map
  `spine2.n20`): i neonati (ruolo `child` non mappato) producono dalla nascita
  col ripiego di `economy/production.py:186-190`; il ciclo dei prezzi itera
  contro quantità fisse (`economy/market.py:105-166`) e porta la sussistenza
  al pavimento 0,01; l'avviso di tatonnement è fuorviante. Nessuna spec
  aperta: e' il PRIMO passo, e serve il via dell'utente.
- **Fecondità coniugale** (ramo `20261029-185654-marital-fertility`): SC-006
  A passa, B fallisce con rho_BK 1,6162, ma quel numero misura il pavimento
  dei prezzi, non Becker. L'utente ha scelto la strada (a) di D-MF-09.
  T052-T057 fermi.
- **Fattore di Becker** (ramo `20261126-163030-becker-reference-state`,
  build map `spine2.n19`): spec in bozza, audit round 1 NOT CONVERGED, un
  giro di correzioni fatto, PARCHEGGIATA finche' la configurazione B non e'
  rimisurata su un'economia corretta (round usati 1 di 6).
- **Scala dell'economia**: PR #22 bozza, misurata e auditata.
- Ordine concordato come proposta: economia, nuova misura di B, Becker,
  chiusura della fecondità coniugale. I merge (#18, #20, #21, #22 e i rami
  in pila) restano all'utente. Le decisioni D-26-E-1..10 sono provvisorie.

Lo stato di dettaglio vive nella build map ([[feedback-build-map-source-of-truth]]),
non qui. Sotto, lo storico.

# AGGIORNAMENTO 2026-09-26 (sera) — demografia Plan 4

Work item in corso sul branch `20260826-144432-demography-plan4-wiring`, gate
di fase 6 al **round 11: NOT CONVERGED**, quattro bloccanti (R1 nucleo diviso
fra due zone attribuito alla zona del decisore; R2 mortalità per tick
sottostimata fino al 5% da `q*dt`; R3 prosa del §4.1.5; R4 pupillo dello
Stato, decisione di perimetro per l'utente), nessuno ancora corretto. Per
riprendere leggere `specs/20260826-144432-demography-plan4-wiring/HANDOFF-2026-09-26-round11.md`
e il documento di gate. Branch pushato su GitHub e PR in stato Draft verso
`develop` (URL nel commit successivo all'handoff). Il merge è dell'utente.
Vedi anche [[project-demography-couple-followups]] e [[project-public-website]].

# SESSION RESUME — aggiornato il 2026-08-12

**WORK ITEM "difetti di design della demografia" CHIUSO E MERGIATO.** Branch
`20260806-112409-demography-design-defects`, merge `--no-ff` in `develop` al
commit **`fb893f5`**, seguito da `3a6107c` che ri-pinna i due whitepaper a quel
commit. Tutto pushato. Suite **1573 verde**, ruff pulito, zero migrazioni
pendenti.

Dieci difetti di design corretti: kernel poligenico (il residuo era `(1 - h2)`,
una media pesata invece di una decomposizione di varianza — la popolazione si
assestava al 48,85% dell'ampiezza dichiarata a h²=0,55), parametri di rumore per
era, innovazione dell'istruzione e della regola di Clark, accoppiamento
assortativo, quota coniugale shari'a per genere, conservazione esatta
dell'imposta di successione per costruzione di Sterbenz, coefficienti
dell'istruzione ancorati a Black & Devereux (2011) dopo che l'attribuzione a
Chetty si era rivelata fabbricata, valore attuale scontato della migrazione,
orizzonte di sussistenza derivato, stabilita' di zona dichiarata valore di
simulazione.

## Il gate di fase 6: undici round, 101 rilievi, sedici criteri che non potevano fallire

Il numero da portarsi dietro non e' 101, e' **sedici**: i criteri verdi che non
verificavano nulla. Una conservazione riderivata dentro il test; una conversione
di unita' eseguita dal test stesso; sonde che dichiaravano lo stesso valore del
fallback; l'unione di due liste di offender asserita come somma, che maschera
entrambe le diramazioni; e da ultimo il `.lower()` della guardia sulle citazioni,
unica difesa contro la forma reale del difetto, cancellabile senza che un solo
test se ne accorgesse.

**Il codice scientifico eseguibile e' rimasto fermo dal round 3 in poi.** I round
6-11 non hanno toccato un solo file di produzione: hanno auditato la guardia che
impedisce il ritorno di un difetto, e la prosa che la descrive. Da qui il
criterio di arresto, scritto e committato **prima** di lanciare il round 10
(`5b33d4b`), perche' un criterio letto dopo aver visto il risultato e' una
trattativa.

## Le due regole di processo, che valgono piu' delle correzioni che le hanno prodotte

Vivono dentro `epocha/apps/demography/tests/test_citation_hygiene.py`, il file
che governano.

1. **Una guardia strutturale si estende SOLO per una violazione osservata nel
   repository, mai per una costruita da chi rivede.** I round 6, 7 e 8 hanno
   girato lo stesso ciclo — chi rivede inventa una forma, chi corregge aggiunge
   un caso e una costante, il round dopo batte la costante — e quel ciclo non ha
   punto fisso: gli input costruibili sono infiniti, le citazioni reali qui erano
   venti.
2. **Quando cambia un payload o una costante, la batteria di mutazioni va
   rilanciata anche contro la versione PRECEDENTE.** Due round di fila una
   riparazione ha distrutto un testimone mentre ne aggiungeva un altro. Una
   correzione non si giudica dai mutanti che uccide ma da quelli che smette di
   uccidere, e quella e' una differenza, non una lettura.

## Il criterio di arresto (`5b33d4b`, in `tasks.md`), riusabile per gli altri gate

Il gate converge quando un round non produce nessuna delle due classi:
1. un difetto sul **codice di produzione** (`epocha/apps/**/*.py` fuori da `tests/`);
2. un **criterio che non puo' fallire** — un test verde che resta verde quando si
   inietta il difetto che dovrebbe testimoniare, ovunque viva, test compresi.

Non bloccano: cifre sbagliate in prosa, frasi contraddittorie, docstring superate
dai fatti. Si correggono nello stesso commit e non riaprono il gate. La seconda
classe resta bloccante apposta — declassare i test butterebbe via l'unica lezione
che questo work item ha pagato sedici volte.

## Relazioni d'audit: adesso si depositano

Il round 9 ha scoperto che **nessuna relazione di fase 6 era mai stata
depositata**: otto round e 83 rilievi dichiarati chiusi senza un artefatto
controllabile, ed e' l'affermazione su cui poggia la ratifica del merge. Ora
`specs/20260806-112409-demography-design-defects/audit/` porta le relazioni dei
round 9, 10 e 11 piu' `phase6-REGISTER.md`, che dichiara esplicitamente cosa dei
round 1-8 e' ricostruibile dai commit e cosa non lo e'. **Regola: la relazione si
deposita nello stesso commit della remediation.**

## Frontiera

- **Demografia Plan 4 (wiring nel tick loop)** — eredita l'obbligo dello storage
  del contatore di fame. E' il prossimo blocco di lavoro sulla demografia.
- **Audit del Knowledge Graph, par. 8.1** — l'unico modulo ancora in coda per la
  promozione da par. 8 a par. 4 del whitepaper.
- **Build map in italiano** — l'utente l'ha chiesta il 2026-08-12. Va aperta come
  work item Spec Kit suo, **con una guardia strutturale nello scope fin dalla
  spec**: due copie della fonte di verita' senza un meccanismo che le tenga
  allineate divergono, e la regola della build map dice che una mappa creduta e
  sbagliata e' peggio di nessuna mappa.
- **Determinismo** — vedi [[project_determinism_enumeration_pending]], resta
  aperto e tocca l'integrita' del paper.

Stato dettagliato per fase: [[feedback_build_map_source_of_truth]] e la build map
stessa, che vince su questa memoria in caso di conflitto.

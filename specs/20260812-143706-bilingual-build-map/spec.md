# Feature Specification: Build map bilingue in un solo file

**Branch**: `20260812-143706-bilingual-build-map`
**Creata**: 2026-08-12
**Revisione**: 2, dopo il round 1 del gate pesante di fase 2 (NOT CONVERGED, 13 rilievi di cui 4 bloccanti)
**Stato**: bozza. **Un punto resta aperto e richiede una decisione dell'utente**: l'emendamento alla costituzione, sotto.

## Il problema, e perché non è "tradurre una pagina"

`docs/build-map/epocha-build-map.html` è la fonte di verità sullo stato di
costruzione del progetto. La regola CRITICAL che la governa dice due cose che
qui contano più di ogni altra: che una mappa in ritardo sul codice è **peggio**
di nessuna mappa, perché viene creduta mentre è sbagliata; e che pubblicare da
un percorso diverso «forka la fonte di verità in due board concorrenti».

L'utente legge in italiano, ha chiesto la mappa in italiano, e ha dichiarato
l'allineamento fra le due lingue **regola inderogabile**.

Il modo ingenuo — un secondo file — realizza ciò che quella regola vieta per
nome: due file, due URL, due board, sincronia affidata alla buona volontà. Il
deliverable è quindi **un file solo che porta entrambe le lingue, più il
meccanismo che impedisce loro di divergere**.

## Perché farlo, senza inventare causalità

La revisione ha demolito l'argomento della prima stesura, che diceva: la mappa è
in inglese, quindi si consulta malvolentieri, quindi va stale. Non c'era una
misura dietro nessuno dei due passaggi, e c'è una contro-evidenza: lo stesso
lettore ha scritto o approvato in quel file oltre seimila parole di prosa
inglese densa, aggiornandolo a ogni checkpoint. I 94 giorni di staleness che la
regola CRITICAL documenta sono attribuiti dalla regola stessa al fatto che lo
stato vivesse nelle memorie invece che in un board unico, **non alla lingua**.

L'argomento vero è un altro, ed è un precedente già deciso dal progetto: **gli
artefatti che l'utente deve leggere e approvare stanno in italiano**. È la regola
delle spec, scritta nella costituzione e nella memoria `feedback_italian_specs.md`.
La build map, per la regola CRITICAL, è esattamente un artefatto che l'utente
deve leggere e su cui deve agire a ogni checkpoint: appartiene alla classe delle
spec, non a quella del codice. A questo si aggiunge una preferenza dell'utente
dichiarata come tale, che è una ragione sufficiente e non ha bisogno di essere
travestita da inferenza.

## Governance: l'emendamento necessario **[DECISIONE UTENTE, BLOCCANTE]**

`.specify/memory/constitution.md:96` dice: «Italian for spec files; English for
everything else (code, commits, plans, docstrings, README, whitepaper EN,
CLAUDE.md). **The whitepaper Italian mirror is the only exception where
translated technical prose is the deliverable.**»

La build map non è uno spec file, non è il whitepaper, non è codice: ricade in
"everything else". Questa feature crea quindi una **seconda** eccezione a una
frase che dice «the only exception». La costituzione è autorità superiore a
`CLAUDE.md` e il suo Governance esige, per un emendamento: approvazione
esplicita, voce nella memoria di riferimento, version bump e migration guidance.
**Nessuno dei quattro può essere deciso da chi scrive la spec.**

L'emendamento proposto, minimo e coerente col principio già presente:

> Italian for spec files **and for the build map**, which is the artifact the
> user must read and act on at every checkpoint and therefore belongs to the
> same class as the specs; English for everything else. Two deliverables carry
> translated technical prose: the whitepaper Italian mirror, whose normative
> text is the English one, and the build map, whose normative text is the
> Italian one.

Finché questo non è ratificato, la spec non è approvabile. È il primo rilievo
del round 1 ed è di governance, non di merito.

## Decisioni di design che il round 1 ha imposto

**D-1. Ogni blocco traducibile porta una chiave stabile.** La prima stesura non
diceva come si identifica un blocco, e da quell'omissione dipendeva tutto:
senza chiave, "esiste in una lingua sola" si può dedurre solo dall'identità del
testo, il che rende impossibile distinguere una traduzione mancante da un blocco
legittimamente identico. Con la chiave il predicato è decidibile.

**D-2. Lo stato si confronta sul token di classe, non sull'etichetta visibile.**
Il file già codifica lo stato strutturalmente: `class="pill done"` due volte,
`pill prog` due, `pill todo` undici, in parallelo con `phase s-done`, `s-prog`,
`s-todo`. La prima stesura pretendeva insieme che le etichette fossero tradotte
e che non divergessero, il che è contraddittorio: `In progress` e `In corso`
sono una divergenza per il secondo requisito e una traduzione dovuta per il
primo. Si confronta il token, che è indipendente dalla lingua. È la regola
«preferire il discriminante che il sistema già codifica».

**D-3. L'italiano è il testo normativo, l'inglese il mirror.** Senza una lingua
normativa dichiarata, il primo dei quattro passi della regola CRITICAL —
«verificare contro la realtà» — non dice contro quale dei due testi, e la
precedenza della mappa su memorie e handoff diventa ambigua quando i due testi
divergono. Il whitepaper ha già questa struttura, con l'inglese normativo; qui è
l'italiano, per la stessa ragione per cui le spec sono in italiano.

**D-4. Ogni blocco mirror porta l'impronta del blocco normativo da cui deriva.**
Questa è la risposta al rilievo più grave del round 1, e senza di essa la feature
non manterrebbe la sua promessa centrale. Chiave, stato e numeri non intercettano
**il caso più frequente di divergenza a un checkpoint: la prosa riscritta in una
lingua sola.** Quel caso ha entrambe le chiavi, lo stesso stato e gli stessi
numeri, e passerebbe ogni controllo — su un paragrafo che è 24 750 caratteri di
prosa pura. Con l'impronta, modificare il testo normativo senza aggiornare il
mirror rende l'impronta obsoleta e la guardia rossa. È il meccanismo che rende la
regola inderogabile davvero inderogabile, invece di dichiararla.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Leggere la mappa in italiano (P1)

L'utente apre la mappa, dall'artifact o da file locale, e la legge in italiano
senza fare nulla.

**Test di accettazione**:
1. Aperta senza scelta precedente, **ogni** blocco traducibile mostra la variante
   italiana e nessuna mostra quella inglese. Formulato in relazione e non in
   conteggi: la prima stesura diceva «i quindici blocchi e i tre paragrafi», veri
   al commit `f0e2582` e falsi alla prima fase aggiunta.
2. **[VERIFICA MANUALE, dichiarata]** che il testo italiano sia effettivamente
   italiano non è un predicato calcolabile, e la mappa italiana conterrà
   legittimamente termini inglesi — `wired`, `not wired`, `CONVERGED`, `merged`,
   `branch`, `tick loop`. La guardia verifica la *presenza e la freschezza* delle
   varianti, non la lingua del contenuto. Dichiararlo è obbligatorio su un
   progetto che ha appena finito di contare sedici criteri che passavano senza
   verificare nulla.

### User Story 2 — Passare all'inglese e tornare (P1)

**Test di accettazione**:
1. Attivato l'inglese, ogni blocco mostra la variante inglese e nessuna
   l'italiana.
2. La scelta persiste fra le visite **dove la persistenza è disponibile**.
   Dentro l'artifact potrebbe non esserlo — lo script già presente avvolge il
   proprio accesso in `try/catch` proprio per questo — e in quel caso si torna
   all'italiano, che è il comportamento voluto. La prima stesura affermava la
   persistenza come incondizionata e la contraddiceva nelle assunzioni.
3. **[VERIFICA MANUALE, dichiarata]** i punti 1 e 2 richiedono un browser, e il
   progetto non ha driver: `requirements/` non contiene né Playwright né
   Selenium, solo `beautifulsoup4`, che parsa l'HTML ma non carica una pagina.
   Sono verifiche manuali e vanno chiamate così.

### User Story 3 — Il meccanismo impedisce la divergenza (P1)

**Test di accettazione**, tutti automatici e tutti provati **per mutazione**:
1. Aggiunto un blocco con la sola variante inglese, la guardia fallisce e nomina
   la chiave scoperta.
2. Cambiato il token di stato di una fase in una lingua sola, la guardia
   fallisce.
3. Cambiato un numero in una lingua sola, la guardia fallisce.
4. **Riscritta la prosa di un blocco normativo senza toccare stati né numeri**, e
   senza aggiornare il mirror, la guardia fallisce perché l'impronta non
   corrisponde più. È il caso che la prima stesura prometteva di coprire e non
   copriva.

### Edge Cases

- **Il paragrafo maggiore**, 24 750 caratteri (**caratteri**, non byte: sono
  24 889 byte, e la prima stesura sbagliava l'unità — il numero giusto sotto
  l'unità sbagliata è il modo esatto in cui un dato falso sopravvive a una
  rilettura), va spezzato per lingua senza spezzarne il contenuto.
- **Gli identificatori tecnici non si traducono** e non sono blocchi chiavati:
  riferimenti di capitolo, percorsi di file, SHA, numeri di fase, nomi di modulo.
  Non essendo chiavati, nessun requisito pretende una loro traduzione, e la
  clausola che la prima stesura dedicava a questo è cancellata perché non
  vincolava nulla.
- **Un blocco identico nelle due lingue** ha comunque le due chiavi e la propria
  impronta: nessun caso speciale.
- **I numeri scritti a lettere.** Misurate 163 occorrenze nel testo visibile —
  `one` 37 volte, `two` 25, `five` 17, `three` 17, `eight` 16 — concentrate nella
  here-band, cioè nel testo che cambia a ogni checkpoint. Il confronto numerico
  non li copre, e va dichiarato nel limite sotto invece di essere scoperto dopo.
- **La guardia sulle citazioni scientifiche.** Misurato: la build map produce 53
  regioni, di cui **una sola** nomina la fonte, lunga 2 844 caratteri e con zero
  riferimenti di capitolo. Il rischio reale non è il numero di regioni ma la
  **co-locazione**: una ristrutturazione che finisca per mettere la menzione
  della fonte e un riferimento di capitolo nella stessa regione porta la guardia
  da zero offender a due. Il bilinguismo lo rende più probabile, perché
  «capitolo 8» è intercettato da `ANY_CHAPTER` e non è fra le forme sanzionate.
  Vincolo aggiuntivo taciuto dalla prima stesura: la build map deve **conservare**
  una menzione della fonte, perché un test esistente esige che il file sia fra
  quelli raggiunti dalla camminata.

## Requirements *(mandatory)*

- **FR-001**: contenuto in italiano e inglese in **un solo file**,
  `docs/build-map/epocha-build-map.html`, pubblicato sull'artifact URL esistente.
  Nessun secondo file, nessun secondo URL.
- **FR-002**: la lingua predefinita è l'italiano, ed è **lo stato a riposo del
  documento**, non il risultato di uno script. Con JavaScript non disponibile il
  lettore deve vedere l'italiano, non le due lingue impilate.
- **FR-003**: sono traducibili titoli, descrizioni, etichette di stato, testo
  della here-band e paragrafi narrativi. Non lo sono gli identificatori tecnici.
- **FR-004**: un comando visibile alterna le lingue senza ricaricare; la scelta
  persiste dove la persistenza è disponibile.
- **FR-005**: la pagina resta **self-contained**. Verificato che oggi lo sia:
  nessun `src=` o `href=` verso risorse esterne.
- **FR-006**: ogni blocco traducibile porta una **chiave stabile** presente in
  entrambe le lingue. La guardia fallisce se una chiave esiste in una lingua sola.
- **FR-007**: la guardia fallisce se le due lingue divergono sul **token di
  stato** o sui **numeri**.
- **FR-007a**: il confronto fra numeri avviene dopo **normalizzazione della
  notazione**: `16.6%` e `16,6%` sono lo stesso numero, `2 844` e `2,844` pure.
  Non è una clausola costruita: il file porta decimali veri — `48.8`, `95.8`,
  `220.5`, `12.43`, `0.5403`, `0.7122` — e un conteggio suite a quattro cifre.
- **FR-007b**: ogni blocco mirror porta l'**impronta** del blocco normativo da
  cui deriva. La guardia fallisce se il normativo è cambiato e l'impronta no.
- **FR-008**: la guardia **dichiara nel proprio docstring il limite** di ciò che
  non prende, come fa quella sulle citazioni. Alla stesura di questa spec il
  limite noto è: i numeri scritti a lettere non sono confrontati, e una modifica
  al mirror che non tocchi il normativo non è rilevata.
- **FR-009**: dopo la modifica, `test_citation_hygiene.py` resta a **zero
  offender** e la build map resta fra i file che la sua camminata raggiunge.
  Baseline verificata: 20 test verdi in 9,80 s.
- **FR-010**: la regola della build map in `CLAUDE.md` è estesa alle due lingue,
  **e la costituzione è emendata** come sopra. Una regola nuova senza il suo
  meccanismo sarebbe la diciassettesima proprietà dichiarata e non sorvegliata.

## Success Criteria *(mandatory)*

- **SC-001**: aperta senza scelta precedente, ogni blocco traducibile mostra la
  variante italiana. *(verifica manuale per la lingua del contenuto, automatica
  per la presenza delle varianti)*
- **SC-002**: cambiata lingua, ogni blocco mostra la variante inglese. *(manuale)*
- **SC-003**: copertura totale espressa **in relazione**: ogni blocco presente in
  una lingua è presente nell'altra, qualunque sia il conteggio del momento.
- **SC-004**: ognuno dei quattro modi di divergere di User Story 3 fa fallire la
  guardia, ciascuno provato per mutazione.
- **SC-005**: la suite intera resta verde e `test_citation_hygiene.py` resta a
  zero offender. *(Il tetto del 2% della prima stesura è cancellato: non era un
  tetto stabilito da nessuno ma un esito misurato al round 7 del work item
  precedente, e come criterio non poteva fallire — leggere un file solo costa
  0,09 ms contro i 9,71 s delle tre camminate della guardia sulle citazioni, tre
  ordini di grandezza sotto la soglia qualunque cosa faccia l'implementazione.)*
- **SC-006**: la pagina si apre senza rete e senza server. *(manuale)*

## Assumptions

- Le lingue sono due e restano due: nessun sistema di localizzazione generico,
  che sarebbe un'astrazione con una sola implementazione.
- La traduzione la produce chi lavora al progetto insieme al contenuto.
- Il peso passa da circa 60 kB a circa 120 kB, irrilevante per l'artifact.

## Non-goals

- Non si traducono whitepaper, README, spec o relazioni d'audit.
- Nessun framework di i18n, nessuna dipendenza nuova.
- Non si serve la pagina da Django: valutato e respinto il 2026-07-17.

## Il costo, dichiarato

**Una tantum**: la traduzione della prosa e la ristrutturazione dei blocchi, più
la guardia e i suoi test provati per mutazione.

**Ricorrente, ed è quello che conta**: da qui in avanti **ogni checkpoint della
build map costa il doppio in scrittura**, più l'aggiornamento delle impronte. La
sola sessione di oggi ne avrebbe richiesti cinque. Non è riducibile: ridurlo
rinviando una lingua ricrea il problema che la feature chiude. La guardia rende
quel costo **inevitabile invece che facoltativo**, il che è il punto, e va
soppesato prima di approvare — su un artefatto il cui modo tipico di guastarsi è
proprio «non viene aggiornato abbastanza spesso».

## Misure di riferimento

Fotografia al commit `f0e2582`, **non soglie**: 60 670 byte su 629 righe; quindici
blocchi con titolo, descrizione e pill; tredici etichette `needs`; 37 tag di cui
34 identificatori tecnici e 3 di prosa; tre paragrafi narrativi, il maggiore da
24 750 caratteri (24 889 byte); 53 regioni di citazione, una sola delle quali
nomina la fonte, lunga 2 844 caratteri con zero riferimenti di capitolo; 163
occorrenze di numeri scritti a lettere. *(Il conteggio di caratteri e parole del
testo visibile che la prima stesura riportava è rimosso: quattro metodi di
estrazione ovvi danno quattro coppie diverse e nessuna coincideva con quella
pubblicata, quindi non era riproducibile.)*

## Rischi dichiarati

- **Che la guardia diventi il difetto**, come è successo a quella sulle
  citazioni, cresciuta da 167 a 543 righe prima di essere tagliata. Le due regole
  di processo valgono qui dal primo giorno: si estende solo per una divergenza
  **osservata**, mai per una costruita; e quando cambia un payload o una costante
  la batteria di mutazioni si rilancia anche contro la versione precedente.
- **La traduzione stessa**: prosa densa, dove si perdono le sfumature dei numeri
  misurati. È per questo che FR-007 li mette sotto guardia invece di affidarli
  alla rilettura, e per questo il limite di FR-008 dice a voce alta quali numeri
  restano fuori.

# Feature Specification: Build map bilingue in un solo file

**Branch**: `20260812-143706-bilingual-build-map`
**Creata**: 2026-08-12
**Revisione**: 8 — la serie dei round sta nel registro, `checklists/requirements.md`, unica sede
**Stato**: bozza. L'emendamento alla costituzione **e' stato ratificato dall'utente il 2026-08-12** ed e' in vigore come versione 1.1.0.

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
meccanismo che rende visibile la loro divergenza** — visibile, non impossibile:
vedi D-4, nessun checksum sa distinguere una traduzione da un bump pigro.

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

## Governance: l'emendamento, ratificato

Prima dell'emendamento `.specify/memory/constitution.md` diceva che il mirror
italiano del whitepaper era **l'unica** eccezione alla regola per cui tutto cio'
che non e' una spec sta in inglese, e questa feature ne creava una seconda. Il
round 1 lo ha rilevato come bloccante di governance, che chi redige la spec non
puo' chiudere.

**Ratificato dall'utente il 2026-08-12**, costituzione alla versione **1.1.0**,
con i quattro adempimenti che il suo Governance esige: approvazione esplicita,
voce in `feedback_canonical_workflow.md`, version bump con data, migration
guidance. La build map sta ora dal lato italiano, per la stessa ragione per cui
ci stanno le spec.

Il round 2 ha poi trovato che l'emendamento **contraddiceva se stesso**: vietava
l'allineamento affidato alla sola prosa e nella riga dopo citava come meccanismo
la doc-sync rule dei whitepaper, che e' una checklist di PR — zero hook attivi
nel repository, e `feedback_whitepaper_doc_sync.md:49` dice espressamente di non
costruirne. Corretto: la costituzione ora **dichiara l'asimmetria** invece di
nasconderla, e dice che promuovere il doc-sync a meccanismo e' un work item
separato, non una frase.

Le citazioni `file:riga` di questa sezione nella revisione 2 puntavano a
`constitution.md:96` per un testo che quella riga, dopo la ratifica, non porta
piu': un verbale di gate che poggiava su una citazione verificabilmente falsa.
E' il motivo per cui questa sezione e' riscritta al passato.

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
numeri, e passerebbe ogni controllo — su un paragrafo il cui HTML interno è 24 750 caratteri, di cui fra
23 976 e 23 988 di testo una volta tolta la marcatura, secondo che le entità
siano risolte o no. Con l'impronta, modificare il testo normativo senza aggiornare il
mirror rende l'impronta obsoleta e la guardia rossa.

**Il limite di questo meccanismo, dichiarato invece che taciuto, ed e' il rilievo
principale del round 2.** Nessuna impronta distingue una traduzione da un bump
pigro: chi ha fretta puo' ricalcolare l'impronta e incollarla, e comprare il
verde con l'edit di un token. Non e' un difetto dell'implementazione, e' un
limite teorico di ogni checksum — un'impronta prova che qualcuno ha *toccato*
qualcosa, non che l'abbia tradotto. Quindi la parola «inderogabile» e' ritirata
da qui: cio' che il meccanismo garantisce e' che l'omissione diventi **un atto
deliberato e visibile nel diff** invece di una dimenticanza silenziosa, e la
classe di guasto che questa feature deve chiudere e' la dimenticanza, non il
sabotaggio. Per rendere l'aggiramento leggibile in revisione, si registrano le
impronte di **entrambi** i testi: chi bumpa solo quella del normativo lascia una
traccia che un lettore del diff vede.

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
   Dentro l'artifact potrebbe non esserlo — lo script già presente
   avvolge in `try/catch` il proprio accesso all'URL e a `postMessage`, cioè
   proprio le vie che un iframe può negare — la revisione 2 attribuiva quel
   `try/catch` a un accesso allo storage che nel file non c'è — e in quel caso si torna
   all'italiano, che è il comportamento voluto. La prima stesura affermava la
   persistenza come incondizionata e la contraddiceva nelle assunzioni.
3. **Automatizzabile, e va automatizzato**: FR-002 definisce il default come *lo
   stato a riposo del documento*, che è statico e quindi verificabile parsando
   l'HTML con `beautifulsoup4>=4.12`, già in `requirements/base.txt:27`. La
   revisione 2 mandava al banco manuale anche questo. **L'elenco dei criteri
   manuali sta in un posto solo**, in coda ai Success Criteria, e questa riga non
   lo ripete: rienumerarlo qui è ciò che lo ha fatto divergere per tre round di
   fila. Un criterio spedito al manuale quando è automatizzabile sembra coperto e
   non lo è, che è la forma dei sedici già contati.

### User Story 3 — Il meccanismo rende visibile la divergenza (P1)

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

- **Il paragrafo maggiore**: 24 750 caratteri di HTML interno, 24 889 byte,
  fra 23 976 e 23 988 caratteri di solo testo, secondo il metodo. La prima stesura diceva «byte» dove erano
  caratteri e la seconda chiamava «prosa pura» una grandezza che includeva 762
  caratteri di marcatura. Il numero giusto sotto la grandezza sbagliata è il modo
  esatto in cui un dato falso sopravvive a una rilettura. Va spezzato per lingua
  senza spezzarne il contenuto.
- **Gli identificatori tecnici non si traducono** e non sono blocchi chiavati:
  riferimenti di capitolo, percorsi di file, SHA, numeri di fase, nomi di modulo.
  Non essendo chiavati, nessun requisito pretende una loro traduzione, e la
  clausola che la prima stesura dedicava a questo è cancellata perché non
  vincolava nulla.
- **Un blocco identico nelle due lingue** ha comunque le due chiavi e la propria
  impronta: nessun caso speciale.
- **I numeri scritti a lettere.** Fra 163 e 179 occorrenze nel testo visibile
  **a seconda del metodo di conteggio** — confine di parola case-sensitive 163,
  case-insensitive 179, delimitazione sui soli spazi, trattini conservati, 170 — concentrate nella
  here-band, cioè nel testo che cambia a ogni checkpoint. La revisione 2 dava un
  totale preso da un metodo e una ripartizione presa da un altro, che è lo stesso
  cambio di unità a metà frase che questa spec rimprovera altrove: qui il metodo
  è dichiarato e l'intervallo pubblicato al posto di una cifra secca. Il confronto numerico
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

> Questa sezione porta **solo il normativo**. Il perché di ogni scelta sta in
> «Decisioni di design»; il registro dei round sta in
> `checklists/requirements.md` e i rilievi nei messaggi di commit. La separazione è la correzione del
> difetto che i round 3 e 4 hanno colto quattro volte: un requisito che racconta
> la propria storia offre alla revisione successiva una superficie che non è il
> requisito, e ogni contraddizione fra la storia e il testo diventa un rilievo.

- **FR-001**: il contenuto sta in italiano e in inglese in **un solo file**,
  `docs/build-map/epocha-build-map.html`, pubblicato sull'artifact URL esistente.
  Nessun secondo file, nessun secondo URL.
- **FR-002**: la lingua predefinita è l'italiano ed è **lo stato a riposo del
  documento**, non il risultato di uno script. Senza JavaScript il lettore vede
  l'italiano, non le due lingue impilate.
- **FR-003**: è traducibile **tutto il testo visibile della pagina**, tranne le
  esenzioni di FR-003a. L'esenzione è per **elenco chiuso**, mai per
  enumerazione di ciò che è incluso.
- **FR-003a**: sono esenti riferimenti di capitolo, percorsi di file, SHA,
  numeri di fase, nomi di modulo, nomi di branch e citazioni autore-anno.
  L'esenzione è **dichiarata per singolo elemento**, mai dedotta dall'aspetto.
- **FR-004**: un comando visibile alterna le lingue senza ricaricare; la scelta
  persiste dove la persistenza è disponibile.
- **FR-005**: la pagina resta **self-contained**: nessuna risorsa esterna,
  nessuna chiamata di rete.
- **FR-006**: ogni blocco traducibile porta una **chiave stabile** presente in
  entrambe le lingue. La guardia fallisce se una chiave esiste in una lingua sola.
- **FR-007**: la guardia fallisce se le due lingue divergono sul **token di
  stato** o sui **numeri**.
- **FR-007a**: i numeri si confrontano dopo **normalizzazione della notazione**:
  `16.6%` e `16,6%` sono lo stesso numero, `2 844` e `2,844` pure.
- **FR-007b**: ogni blocco registra l'**impronta di entrambi i testi**, normativo
  e mirror. La guardia fallisce se un testo è cambiato e la sua impronta no.
- **FR-008**: la guardia **dichiara nel proprio docstring i limiti** di ciò che
  non prende. Sono **quattro** ed è questa l'unica sede che li enumera: (a) i
  numeri scritti a lettere non sono confrontati; (b) una traduzione presente ma
  sbagliata passa; (c) ricalcolare l'impronta senza tradurre compra il verde;
  (d) la lingua effettiva del contenuto non è un predicato calcolabile — la
  guardia verifica presenza e freschezza delle varianti, non che siano scritte
  nella lingua giusta.
- **FR-009**: `test_citation_hygiene.py` resta a **zero offender** e la build map
  resta fra i file che la sua camminata raggiunge. Baseline: 20 test verdi.
  Nessun tempo di parete entra nel requisito.
- **FR-009a**: la guardia è **un test eseguito dalla suite**, non uno script che
  qualcuno ricorda di lanciare.
- **FR-010**: la regola della build map è estesa alle due lingue **in ogni sede
  che la porta**. Sono otto: `CLAUDE.md`, la costituzione,
  `feedback_build_map_source_of_truth.md`, `project_roadmap_post_mvp.md`,
  l'indice `MEMORY.md` — le ultime tre con il rispettivo backup —, `README.md`,
  `README.it.md`, e **la mappa stessa**, la cui riga «It is mandatory to update
  it — it is not a snapshot» enuncia la regola dentro l'artefatto che governa.

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

**Elenco autoritativo dei criteri manuali, unica sede.** Sono quattro: la lingua
effettiva del contenuto (SC-001, in parte), il comportamento del comando di
alternanza (SC-002), la persistenza della scelta (User Story 2, test 2 — non ha
un SC proprio), l'apertura da file locale (SC-006). Nessun altro punto del
documento li rienumera né li conta: ogni altra sede rinvia qui.

Il rilievo «conteggio dato in due modi» è stato chiuso e riprodotto per tre
round consecutivi, ogni volta perché la correzione aggiungeva una sede invece
di eliminarne. Il rimedio non è contare meglio, è **avere un posto solo**.

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
rinviando una lingua ricrea il problema che la feature chiude. La guardia non rende quel
costo inevitabile — D-4 dice perché non può — ma rende **visibile chi non lo
paga**, il che è quanto un meccanismo può dare, e va
soppesato prima di approvare — su un artefatto il cui modo tipico di guastarsi è
proprio «non viene aggiornato abbastanza spesso».

## Misure di riferimento

Fotografia al commit `f0e2582`, **non soglie**: 60 670 byte su 629 righe; quindici
blocchi con titolo, descrizione e pill; tredici etichette `needs`; 37 tag di cui
34 identificatori tecnici e 3 di prosa; tre paragrafi narrativi, il maggiore da
24 750 caratteri (24 889 byte); 53 regioni di citazione, una sola delle quali
nomina la fonte, lunga 2 844 caratteri con zero riferimenti di capitolo; fra 163 e 179
occorrenze di numeri scritti a lettere secondo il metodo, come all'edge case. *(Il conteggio di caratteri e parole del
testo visibile che la prima stesura riportava è rimosso: quattro metodi di
estrazione ovvi danno quattro coppie diverse e nessuna coincideva con quella
pubblicata, quindi non era riproducibile.)*

## Rischi dichiarati

- **Che la guardia diventi il difetto**, come è successo a quella sulle
  citazioni, cresciuta da 167 a 543 righe prima di essere tagliata. Le regole di
  processo che governano una guardia strutturale valgono qui dal primo giorno, e
  stanno in una sede sola, `checklists/requirements.md`: riformularle qui è
  ciò che le farebbe divergere.
- **La traduzione stessa**: prosa densa, dove si perdono le sfumature dei numeri
  misurati. È per questo che FR-007 li mette sotto guardia invece di affidarli
  alla rilettura, e per questo il limite di FR-008 dice a voce alta quali numeri
  restano fuori.


## FAQ

La regola CRITICAL «Every Spec Includes a FAQ Section» la rende obbligatoria, e
la revisione 2 non ce l'aveva — rilievo bloccante del round 2, con la casella
«All mandatory sections completed» spuntata sopra la sua assenza.

**Perché un file solo e non due?** Due file sono due artifact URL, cioè il fork
della fonte di verità che la regola della build map vieta per nome, e la
sincronia sarebbe una promessa in prosa. Con un file solo c'è un checkpoint, un
URL, e una guardia che può pretendere entrambe le lingue.

**Perché l'italiano normativo, quando il whitepaper ha l'inglese?** Perché sono
due classi diverse. Il whitepaper punta a una pubblicazione in inglese; la build
map è l'artefatto che l'utente deve leggere e approvare a ogni checkpoint, cioè
la stessa classe delle spec, che il progetto ha già deciso stiano in italiano.

**Perché non un framework di i18n?** Sarebbe un'astrazione con una sola
implementazione per due lingue che non aumenteranno. L'onere della prova sta su
chi aggiunge.

**L'impronta garantisce che la traduzione ci sia?** No, e va detto: nessun
checksum distingue una traduzione da un bump pigro. Garantisce che l'omissione
sia un atto deliberato e visibile nel diff invece di una dimenticanza. La classe
di guasto da chiudere è la dimenticanza.

**Che cosa resta scoperto?** Quattro cose, enumerate in FR-008 e in nessun
altro posto: un elenco chiuso ripetuto in due sedi diverge, ed e' divergito
qui — fino alla revisione 7 questa risposta ne elencava tre e FR-008 tre, ma
non gli stessi tre. Vivranno nel docstring della guardia, come fa quella
sulle citazioni.

**Che cosa costa?** Ogni checkpoint della build map costerà il doppio in
scrittura più l'aggiornamento delle impronte, per sempre. È il prezzo di mettere la
regola sotto un meccanismo che ne rende visibile la violazione, invece di
lasciarla un'intenzione. Non è il prezzo dell'inderogabilità, che nessun
checksum sa dare: vedi la risposta sopra.

**Perché non serve la mappa da Django, così da avere una sola sorgente?**
Valutato e respinto il 2026-07-17: metterebbe il board dietro un login e
farebbe dipendere la documentazione di progetto dalla UI di simulazione, con la
dipendenza nella direzione sbagliata.

**Rischio di sicurezza?** Nullo in senso stretto: la pagina resta statica,
self-contained e senza input. Il rischio reale è di integrità — una mappa che
afferma il falso in una delle due lingue viene creduta, ed è esattamente ciò che
la guardia esiste per impedire.

**È riproducibile?** Le misure di riferimento portano il commit a cui si
riferiscono e il metodo di conteggio quando ne esiste più d'uno; sono fotografie
e non soglie, e la spec dice di rimisurarle invece di ricopiarle.

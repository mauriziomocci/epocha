# Feature Specification: Build map bilingue in un solo file

**Branch**: `20260812-143706-bilingual-build-map`
**Creata**: 2026-08-12
**Revisione**: 3, dopo il round 2 del gate pesante (round 1: 13 rilievi, 4 bloccanti; round 2: 16, 5 bloccanti)
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
   revisione 2 mandava al banco manuale anche questo. Resta davvero manuale solo
   il **comportamento del comando di alternanza** e la **persistenza**, che
   richiedono un browser che il progetto non ha. Un criterio spedito al manuale
   quando è automatizzabile sembra coperto e non lo è, che è la forma dei sedici
   già contati.

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

- **FR-001**: contenuto in italiano e inglese in **un solo file**,
  `docs/build-map/epocha-build-map.html`, pubblicato sull'artifact URL esistente.
  Nessun secondo file, nessun secondo URL.
- **FR-002**: la lingua predefinita è l'italiano, ed è **lo stato a riposo del
  documento**, non il risultato di uno script. Con JavaScript non disponibile il
  lettore deve vedere l'italiano, non le due lingue impilate.
- **FR-003**: è traducibile **tutto il testo visibile della pagina**, e non lo
  sono soltanto gli identificatori tecnici elencati sotto. La revisione 2
  enumerava cinque categorie e lasciava fuori dell'altro testo visibile —
  misurati oltre tremila caratteri — 3 252 fra note, deck, legenda, etichette di blocco,
  intestazioni di colonna e il pannello delle regole — e fra quel testo c'era la
  riga che enuncia la regola della mappa stessa, «It is mandatory to update it —
  it is not a snapshot», che il lettore italiano avrebbe letto in inglese senza
  che alcun test fallisse. L'enumerazione per categorie è la forma sbagliata:
  ogni categoria dimenticata è un buco silenzioso, mentre l'esenzione per elenco
  chiuso rende visibile ciò che si sottrae.
- **FR-003a**: sono esenti gli identificatori tecnici — riferimenti di capitolo,
  percorsi di file, SHA, numeri di fase, nomi di modulo, **nomi di branch**
  (`20260806-112409-demography-design-defects` compare nel file) e **citazioni
  autore-anno** (`Sjaastad 1962`, `Harris & Todaro 1970`), che il Principio I
  vieta di alterare — e l'esenzione è
  **dichiarata per singolo elemento**, non dedotta dal suo aspetto. Un tag ibrido
  come `wired · engine.py:394` porta insieme uno stato e un percorso, e nessuna
  euristica lo classifica correttamente. Il caso che lo dimostra è `not wired`,
  che è uno stato — quello che la regola CRITICAL impone di verificare grepando
  il tick engine — e che la revisione 2 lasciava fuori sia da FR-003 sia dal
  confronto sui token di FR-007.
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
- **FR-007b**: ogni blocco registra l'**impronta di entrambi i testi**, normativo
  e mirror. La guardia fallisce se un testo è cambiato e la sua impronta no. La
  simmetria non aggiunge un componente, applica due volte lo stesso, e serve
  perché l'inglese è la lingua riflessa di chiunque editi questo repository —
  `CLAUDE.md` impone l'inglese per codice, commit, test, README e memorie — quindi
  una modifica al solo mirror è almeno tanto probabile quanto una al normativo.
- **FR-008**: la guardia **dichiara nel proprio docstring il limite** di ciò che
  non prende, come fa quella sulle citazioni. Alla stesura di questa spec il
  limite noto è: i numeri scritti a lettere non sono confrontati, e una modifica
  al mirror che non tocchi il normativo non è rilevata.
- **FR-009**: dopo la modifica, `test_citation_hygiene.py` resta a **zero
  offender** e la build map resta fra i file che la sua camminata raggiunge.
  Baseline verificata: **20 test verdi**. Il tempo di parete non entra nel
  requisito — tre esecuzioni nel container danno 12,28 s, 8,85 s e 7,24 s, una
  dispersione del 69,6% sul minimo, e una quarta esecuzione a 14,47 s la porta
  al 100% — per la stessa ragione per cui SC-005 ha
  cancellato il tetto del 2%: un criterio su un tempo di parete non può fallire
  in modo affidabile.
- **FR-009a**: la guardia è **un test eseguito dalla suite**, altrimenti FR-006,
  FR-007 e FR-007b non hanno un momento in cui fallire. Dove collocarla è materia
  del piano, non della spec, ma la spec vincola che non sia uno script che
  qualcuno ricorda di lanciare: l'unico precedente, `test_citation_hygiene.py`,
  vive dentro `demography` per ragioni storiche e cammina su tutto il repository,
  e quel precedente non va imitato senza pensarci.
- **FR-010**: la regola della build map è estesa alle due lingue **in tutte le
  sedi che la portano**, non solo in `CLAUDE.md`: la costituzione, la memoria
  `feedback_build_map_source_of_truth.md` con il suo backup, la roadmap
  `project_roadmap_post_mvp.md`, e i due README che la descrivono senza dire che
  è bilingue né quale testo è normativo; l'indice `MEMORY.md` con il suo backup,
  che porta la regola in prima riga; e **la mappa stessa**, la cui riga «It is
  mandatory to update it — it is not a snapshot» enuncia la regola dentro
  l'artefatto che la regola governa. Il progetto tratta già altrove le copie
  multiple come un insieme che cambia insieme, e la memoria rimasta 94 giorni
  stale è il precedente che ha generato l'intera regola. Il testo originale di
  questo requisito nominava due sedi su cinque,
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

**I criteri manuali sono quattro, ed è l'elenco che vale**: la lingua effettiva
del contenuto, il comportamento del comando di alternanza, la persistenza della
scelta, e l'apertura da file locale. La revisione 3 ne dichiarava due nel
verbale e ne marcava quattro qui, cioè ha chiuso il rilievo «conteggio dato in
due modi» riproducendolo. Un conteggio derivato in due sedi diverge; un elenco
enumerato una volta sola no, ed è per questo che qui c'è l'elenco.

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
  citazioni, cresciuta da 167 a 543 righe prima di essere tagliata. Le due regole
  di processo valgono qui dal primo giorno: si estende solo per una divergenza
  **osservata**, mai per una costruita; e quando cambia un payload o una costante
  la batteria di mutazioni si rilancia anche contro la versione precedente.
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

**Che cosa resta scoperto, in tutto?** I numeri scritti a lettere non sono
confrontati; una traduzione sbagliata ma presente passa; la lingua effettiva del
contenuto non è un predicato calcolabile. I tre limiti vivranno nel docstring
della guardia, come fa quella sulle citazioni.

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

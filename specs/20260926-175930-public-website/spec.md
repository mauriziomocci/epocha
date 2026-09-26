# Feature Specification: Sito pubblico divulgativo di Epocha

**Branch**: `20260926-175930-public-website`
**Creata**: 2026-09-26
**Revisione**: 6 — la serie dei round di audit sta nel registro, `checklists/requirements.md`, unica sede
**Stato**: bozza, gate pesante di fase 2 in corso
**Base dei fatti**: ogni affermazione su codice, README, build map e whitepaper è verificata su `develop` al commit `2223968`, salvo dove è indicato un altro riferimento. Il merge del Plan 4 ne renderà false alcune; «Sequenza e dipendenze» dice come la spec lo gestisce.
**Input**: richiesta dell'utente del 2026-09-26: un sito pubblico e divulgativo che presenti Epocha a chi non è sviluppatore, «un po' come MiroFish», con il link a GitHub, capace di reggere modifiche continue fino a quando il progetto diventerà prodotto e oltre.

## Il problema

Epocha oggi si presenta al mondo soltanto dal repository GitHub. Chi non è
sviluppatore arriva su un README tecnico, e da lì al whitepaper (3.740 righe in
inglese, 3.554 in italiano) o alla build map, che è una lavagna interna scritta
per chi lavora al progetto. Manca una pagina che spieghi in pochi minuti che
cos'è Epocha, perché è interessante e a che punto è davvero.

L'utente vuole una vetrina pubblica: bella, comprensibile, pensata per il
pubblico generale, con i ricercatori e i contributori come strati successivi.
Il riferimento di forma è la landing di MiroFish consultata il 2026-09-26 a
`mirofish.ink` (il repository `666ghj/MiroFish` dichiara invece come homepage
`mirofish.ai`): una sola pagina che scorre da un titolo forte, attraverso
catture del prodotto in funzione e un flusso di lavoro in passi, fino a domande
frequenti e link al codice.

Il riferimento vale per la forma e **non per le promesse**. MiroFish si
presenta come motore che «predice qualsiasi cosa», e la memoria
`reference_mirofish_comparison.md` registra che, alla verifica del 2026-04-15,
MiroFish non aveva i moduli di civiltà che il suo marketing lasciava intendere e
che l'utente gli aveva attribuito. Epocha è un progetto scientifico il cui
whitepaper dichiara che la validazione storica non è mai stata eseguita (§7.5)
e che le decisioni degli agenti e la generazione del mondo, guidate da un
modello linguistico, non sono riproducibili dal seme (Abstract, §3.4,
Appendice B). Un sito che promettesse più di così danneggerebbe proprio la
credibilità su cui il progetto si regge.

C'è un secondo problema, emerso verificando il README prima di progettare. A
`2223968` il README pubblico fa già affermazioni che il sito non potrebbe fare.
La Vision dice che «hundreds of autonomous agents» vivono dentro «audited
demographic and economic dynamics» e che il motore «scales from a medieval
village to a galactic federation»: le centinaia di agenti e la scala galattica
sono obiettivi di progetto mai misurati (la memoria
`project_scalability_analysis.md` contiene solo stime), e la demografia è
auditata ma non è chiamata dal ciclo dei turni (in
`epocha/apps/simulation/engine.py` il modulo demografico è importato solo per
gestire l'azione `avoid_conception`, tramite `set_avoid_conception_flag` e
`load_template`). La tabella Status dà il Plan 3 della demografia come «not
yet», mentre `inheritance.py` e `migration.py` sono in `develop` e la build map
lo registra. La tabella Status è una seconda copia dello stato del progetto, e
si è staccata dalla build map esattamente come la regola CRITICAL della build
map prevede che accada a ogni copia.

## Decisioni di design

**D-1. Sito statico generato dal repository, non un CMS.** L'utente aveva
proposto WordPress e l'ha riproposto due volte con ragioni legittime: poter
fare migliorie, raccontare gli avanzamenti, ottenere visibilità. Nessuna delle
tre dipende dal CMS. La visibilità dipende dall'HTML servito, dalla velocità,
dai metadati e dai link in entrata, e un sito statico su dominio proprio li
produce tutti. Gli avanzamenti li racconta già la build map; una notizia, quando
servirà, è un file di testo che si scrive anche dall'editor web di GitHub. Le
migliorie di tipo blog, newsletter o commenti si aggiungono a un sito statico
con servizi esterni. WordPress aggiungerebbe un database, un hosting a
pagamento, aggiornamenti di sicurezza continui, un plugin per il bilinguismo e,
soprattutto, un luogo in cui il testo sfugge a qualunque guardia della suite.
La decisione è dell'utente e l'ha presa: sito statico. Le condizioni che la
riaprirebbero sono scritte in «Quando riconsiderare questa scelta».

**D-2. Hugo come generatore, scelto dopo aver scartato MkDocs, Astro e l'HTML
scritto a mano.** La prima raccomandazione, data nella conversazione che ha
richiesto il work item, era MkDocs su GitHub Pages. La verifica del 2026-09-26
l'ha smentita: l'ultima release di MkDocs 1.x è la 1.6.1 del 2024-08-30, circa
venticinque mesi fa; MkDocs 2.0 è una riscrittura in pre-release che rimuove il
sistema di plugin; Material for MkDocs è in manutenzione con fine vita al
2027-05-05; il successore Zensical annuncia la versione 0.1.0 per il
2026-11-05. L'HTML scritto a mano è stato proposto e poi ritirato quando
l'utente ha precisato che il sito dovrà reggere modifiche continue fino al
prodotto e oltre: su più pagine ripete intestazione, menu, piè di pagina e
avvertenza in ogni file, cioè crea copie che divergono. Astro è scartato perché
porta l'ecosistema Node e npm dentro un progetto Python e ha rilasciato la 6.0
a marzo 2026 con API rimosse e Node 22 obbligatorio. Hugo è un unico eseguibile
senza dipendenze, in sviluppo attivo dal 2013 (ultima versione stabile 0.166.0
del 2026-09-09), con il multilingua integrato. L'utente, che non conosceva
Hugo, l'ha confermato dopo aver visto una bozza grafica della landing: Hugo
compone le pagine, l'aspetto lo decide il design. Il prezzo di Hugo è dichiarato
in «Il costo»: è ancora in versione 0.x e rompe la compatibilità anche nelle
versioni minori.

**D-3. La landing è il prodotto; whitepaper e build map sono strati di
approfondimento.** Il pubblico primario è il pubblico generale, con ricercatori
e contributori come strati successivi (risposta dell'utente del 2026-09-26). Il
whitepaper resta dove vive e la landing lo raggiunge con un link a GitHub, che
lo mostra già formattato. La build map si pubblica sul sito come copia intatta
del file, perché GitHub mostra i file HTML come sorgente e l'artifact è privato
per impostazione.

**D-4. Lo stato di avanzamento ha una sola fonte, e la landing non lo ripete.**
La landing non contiene affermazioni sull'avanzamento del progetto (conteggi,
percentuali, date, stati di audit, fasi o piani fatti, in corso o prossimi),
oltre alle tre dell'avvertenza (sviluppo, validazione, riproducibilità) e al
rimando alla build map. Una landing che scrivesse «otto moduli auditati» o «il
Plan 4 è chiuso» sarebbe falsa al primo merge, lo stesso guasto che ha lasciato
la roadmap ferma per 94 giorni e la tabella Status del README indietro di un
piano. Le tre affermazioni dell'avvertenza sono ammesse perché sono ancorate a
capitoli del whitepaper e la loro revisione è legata a quei capitoli (FR-006).
Le descrizioni di ciò che Epocha fa, per esempio che cosa succede in un turno,
non sono affermazioni di avanzamento: le governa FR-004, che ammette solo quelle
vere al commit pubblicato.

**D-5. L'avvertenza è garantita per costruzione; la verità della prosa è
garantita dalla revisione, e la spec lo dice.** L'avvertenza sta nel modello
comune delle pagine, e una guardia sull'HTML generato fallisce se una pagina
pubblicata non la porta. Una lista di parole vietate («validated», «validato»,
«riproducibile») è stata valutata e scartata: l'avvertenza stessa deve dire
«non validato», quindi la lista avrebbe bisogno di eccezioni, e una parafrasi la
aggirerebbe. Darebbe un verde che non garantisce niente, che è peggio di nessun
controllo. La verità del testo libero è affidata alla revisione dell'autore e
all'audit avversariale di fase 6, come la costituzione dichiara per il
whitepaper.

**D-6. Inglese normativo, italiano mirror, un indirizzo per lingua.** La
costituzione (versione 1.1.0, Development Workflow) assegna l'italiano alle
sole spec e build map e l'inglese a tutto il resto, README compreso; il sito
appartiene al resto, quindi il suo testo normativo è l'inglese e l'italiano è
il mirror. La scelta è dell'utente, presa il 2026-09-26 dopo il round 1. La
stessa sezione della costituzione enumera però in forma chiusa **due**
deliverable con prosa tecnica tradotta, whitepaper e build map, e chiede a
ciascuno di dichiarare il testo normativo e come le lingue restano allineate:
il sito è un terzo, e anche il README, già bilingue, manca da quell'elenco.
FR-022 chiede l'emendamento. L'inglese sta alla radice del sito e l'italiano
sotto `/it/`, perché i motori di ricerca indicizzano meglio una lingua per
indirizzo e la visibilità è uno degli obiettivi dichiarati. Il sito non
reindirizza automaticamente in base alla lingua del browser, che è la pratica
raccomandata dalla guida di Google sui siti multilingue.

**D-7. Si mostra il vero Epocha.** Le immagini della landing sono catture reali
del cruscotto dell'operatore, prese da una simulazione di prova, e non
illustrazioni (scelta dell'utente del 2026-09-26). Ogni cattura dichiara che
cosa mostra, da quale commit e in quale data, e che la simulazione è di prova e
non validata. Se le catture risultano poco presentabili, il rimedio va nel
cruscotto con un work item dedicato; il sito non ritocca le immagini.

**D-8. Pubblicazione da `develop` su GitHub Pages, con un workflow dedicato,
controlli su ogni PR e messa online attivata dall'utente.** `main` è fermo allo
scaffold iniziale del 2026-03-23 (`df5ccfd`), 586 commit dietro `develop`, e il
branch di default è `develop`: il sito si pubblica da lì. Il workflow è
dedicato perché `ci.yml` scatta solo su `main` e quindi non gira su nessuna PR
verso `develop` (difetto preesistente, fuori perimetro). Le guardie girano anche
sulle PR verso `develop`, senza pubblicare, così un errore si vede prima del
merge e non dopo. La prima messa online non parte da sola al merge: la attiva
l'utente, dopo aver abilitato Pages e verificato le precondizioni di FR-020.

**D-9. Il dominio è un parametro.** L'utente non ha ancora un dominio. Il sito
nasce all'indirizzo di progetto di GitHub Pages
(`mauriziomocci.github.io/epocha/`) e passa al dominio proprio cambiando un solo
valore di configurazione più le impostazioni che l'utente fa su GitHub e sul
registrar. La raccomandazione data all'utente è `epocha.app`, libero al
2026-09-26 secondo il registro (RDAP), con listino Porkbun di 8,75 dollari il
primo anno e 14,93 dal rinnovo; la scelta e l'acquisto sono dell'utente.

**D-10. I sorgenti del sito vivono in una cartella propria alla radice del
repository, fuori dal codice Django.** Il sito ha una responsabilità sola,
presentare il progetto, diversa da quella di ogni app Django. La dipendenza
punta in una sola direzione: il sito legge `docs/build-map/`, nessun modulo del
codice conosce il sito, e il simulatore ne ignora l'esistenza; i documenti
(README, `CLAUDE.md`, costituzione) lo nominano, come nominano la build map. Servirlo da
Django è stato escluso per la build map il 2026-07-17 (`CLAUDE.md`, «Why it is
not served by Django») e le stesse ragioni valgono qui.

**D-11. Due classi di guardie, separate per ciò che leggono.** Le guardie sui
**sorgenti** leggono i file del repository, girano prima della generazione,
stanno nella suite del progetto e non richiedono Hugo. Le guardie
sull'**output** leggono l'HTML generato, girano dopo la generazione e prima
della pubblicazione, e stanno solo nel workflow, perché richiedono Hugo. FR-012
dice quale requisito sta in quale classe. La prima stesura le chiedeva tutte
«prima di generare» e tutte «nella suite», il che era impossibile per quelle
sull'output.

## Sequenza e dipendenze

Il ramo `20260826-144432-demography-plan4-wiring` è al gate di fase 6 e, al
merge, cablerà la demografia nel ciclo dei turni (in
`epocha/apps/simulation/tasks.py`, con attivazione per simulazione tramite il
flag `demography_enabled`, spento per default) e riscriverà Status e Roadmap
dei README, la build map e `CLAUDE.md`. La sessione del Plan 4 ha chiesto, il
2026-09-26, di non toccare build map e container finché il suo gate è aperto.
Da qui l'ordine:

1. Questo work item si ferma al gate di fase 2 finché il Plan 4 non è mergiato
   in `develop`.
2. La fase 3 parte da `develop` aggiornato con il Plan 4. Prima di pianificare,
   ogni affermazione fattuale di questa spec che il merge tocca («Il problema»,
   passo 2 punto 4, passo 3 punto 1, FR-004, FR-006, FR-017, FR-019, FR-020,
   FR-021, FR-024, «Problemi trovati e non risolti qui») si riverifica e si
   corregge; la correzione è un emendamento alla spec, non una deviazione
   silenziosa. Il Plan 4 riscrive l'Abstract del whitepaper, §7.5 e la tabella
   di doc-sync di `CLAUDE.md`, cioè proprio i testi che FR-006 e FR-019 citano.
3. FR-020 è a carico di questo work item, in fase 5: al merge il Plan 4 si
   chiude, e con lui cade la ragione per cui oggi la build map non va toccata da
   qui.

## Processo di design in tre passi

Il passo 1 è la proposta costruita con l'utente nel brainstorming del
2026-09-26, cambiata quattro volte mentre l'utente precisava lo scopo: da sito
di documentazione generato con MkDocs, a sito di documentazione generato con
Pandoc, a landing divulgativa in HTML scritto a mano, a landing divulgativa
generata con Hugo.

**Passo 2, prima autorevisione.** Ha trovato quattro difetti gravi.

1. *L'avvertenza «su ogni pagina» contraddiceva la build map «pubblicata
   intatta».* Corretto delimitando il requisito alle pagine generate dal
   modello (FR-006) e dichiarando il limite (FR-021).
2. *Due rappresentazioni della build map con stati diversi.* L'artifact si
   ripubblica a ogni checkpoint, anche da branch non ancora mergiati; il sito la
   ripubblica solo al merge in `develop`. Corretto dichiarando i ruoli: il file
   in `develop` è la fonte, il sito ne mostra lo stato mergiato, l'artifact è lo
   specchio di lavoro che può anticiparlo (FR-019). Il 2026-09-26 la situazione
   si è presentata dal vivo: l'artifact portava lo stato del ramo Plan 4, più
   avanti di `develop`, e l'apertura di questo work item è stata applicata sopra
   quella versione toccando la sola chiave `13.desc`, invece di ripubblicare il
   file di `develop`, che avrebbe cancellato lo stato del Plan 4.
3. *Le guardie non avrebbero fermato niente.* `ci.yml` non gira su `develop`.
   Corretto chiedendo che le guardie blocchino la pubblicazione e girino sulle
   PR (FR-011, FR-012).
4. *Descrivere che cosa simula Epocha è già una dichiarazione di stato.* Dire che
   Epocha «simula la demografia» è falso a `2223968` e diventerà vero con il
   Plan 4, e solo per le simulazioni che attivano il flag. Corretto con D-4 e
   FR-004: la landing afferma che un modello partecipa alla simulazione solo se
   il percorso di produzione del turno lo raggiunge al commit pubblicato, e dice
   sotto quale condizione; ciò che il percorso non raggiunge si dice
   progettato. Il round 3 ha mostrato che una regola più rigida, «chiamato senza
   condizioni», avrebbe vietato di dire il vero anche sull'economia: il modello
   auditato del §4.8 gira solo se la simulazione ha valute inizializzate,
   altrimenti ne gira uno precedente (`run_economy` in `engine.py`).

Ha trovato inoltre cinque difetti importanti: le catture potevano mostrare
credenziali o dati personali (FR-009); un video nel repository resta nella
storia git per sempre (FR-010); i caratteri tipografici caricati da un server
esterno contraddicevano «nessun tracciamento» (FR-015); il README si
correggeva solo in parte (FR-017); le condizioni d'uso di GitHub Pages escludono
i siti rivolti principalmente a transazioni commerciali o a software commerciale
come servizio («Quando riconsiderare questa scelta»).

**Passo 3, seconda autorevisione sulle correzioni.** Ha trovato tre problemi.

1. La correzione del punto 2 lascia pubblica una mappa che oggi contiene
   affermazioni superate. In `develop` il paragrafo con chiave `hb.p1` apre
   dicendo che il work item sui difetti di design è «APERTO», mentre quel ramo è
   mergiato in `develop` con `fb893f5`. Sul ramo Plan 4 l'italiano era già
   corretto, mentre per un certo tempo il mirror inglese ha descritto ancora la
   deliberazione 0.1a come «under way» e sulla «logit latent scale», con
   l'impronta aggiornata, e la guardia bilingue passava: è il limite dichiarato
   di quella guardia osservato dal vivo. La sessione del Plan 4, informata, l'ha
   corretto con il commit `91b9599` del 2026-09-26. Resta invece, sul ramo Plan 4,
   il paragrafo `hb.p0`, che descrive il Plan 4 come
   «initialization + engine wiring + historical validation», mentre il §9 del
   whitepaper dello stesso ramo dice che la campagna di validazione storica non
   ne fa parte: una mappa pubblicata che desse per fatto un Plan 4 «con
   validazione» suggerirebbe al pubblico una validazione eseguita. Risolto come
   precondizione della messa online a carico di questo work item (FR-020), non
   come modifica da qui mentre il gate del Plan 4 è aperto.
2. La correzione del punto 3 porta le guardie fuori dalla suite Django. Risolto
   dal round 1 dell'audit con D-11.
3. Il meccanismo a coppie della build map non si trasferisce a Hugo. Si riusa il
   principio (il mirror porta l'impronta del normativo), non il codice (FR-008).

Gli audit avversariali hanno poi trovato diciannove rilievi al round 1, quattordici al round 2, otto al round 3, cinque al round 4 e tre al round 5, chiusi nelle revisioni successive; il registro sta in `checklists/requirements.md`.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Capire che cos'è Epocha e che cosa non è (Priorità: P1)

Una persona che non programma arriva sulla landing da un link condiviso o da un
motore di ricerca. In pochi minuti capisce che Epocha è un simulatore di civiltà
open source in cui abitanti artificiali con un carattere e una memoria vivono
in un mondo regolato da modelli scientifici, vede il cruscotto vero in
funzione, e capisce senza doverlo cercare che il progetto è in sviluppo, non è
validato contro dati storici e non è riproducibile.

**Perché questa priorità**: è la ragione per cui il sito esiste.

**Test indipendente**: si pubblica la sola landing e la si fa leggere a persone
che non sviluppano software.

**Acceptance Scenarios**:

1. **Given** la landing in una delle due lingue, **When** la pagina si apre su
   uno schermo da computer o da telefono, **Then** l'avvertenza è visibile senza
   scorrere.
2. **Given** la landing, **When** il lettore la percorre fino in fondo, **Then**
   trova che cos'è Epocha, come funziona un turno, quali fonti scientifiche usa,
   la sezione «a che punto è» con le tre affermazioni dell'avvertenza e il
   rimando alla build map, le domande frequenti e i link a GitHub, whitepaper e
   build map.
3. **Given** una cattura del cruscotto, **When** il lettore ne legge la
   didascalia, **Then** trova che cosa mostra, il commit e la data da cui viene,
   e che la simulazione è di prova e non validata.

### User Story 2 — Pubblicare una modifica con un merge (Priorità: P1)

Chi mantiene il progetto modifica un testo della landing su un branch, lo vede
in anteprima in locale, apre una PR verso `develop` e vede le guardie girare;
al merge il sito pubblico si aggiorna da solo. Se una modifica rompe una regola
del sito, la PR lo mostra prima del merge, e la pubblicazione non parte.

**Perché questa priorità**: l'utente ha chiesto un sito che regga modifiche
continue fino al prodotto e oltre; un sito che si aggiorna a mano è un sito che
invecchia.

**Test indipendente**: si apre una PR che modifica solo un testo e si verifica
che, dopo il merge, il sito online cambi; si apre una PR che toglie l'avvertenza
dal modello e si verifica che le guardie la segnino rossa.

**Acceptance Scenarios**:

1. **Given** una PR verso `develop` che tocca i sorgenti del sito o la build
   map, **When** la PR si apre o si aggiorna, **Then** girano le guardie e la
   generazione, senza pubblicare.
2. **Given** un merge in `develop` che tocca i sorgenti del sito o la build map,
   con la messa online attivata, **When** il workflow termina, **Then** il sito
   pubblico mostra la modifica.
3. **Given** una modifica che fa fallire una guardia, **When** il workflow gira,
   **Then** non pubblica, il sito online resta quello precedente, e il log dice
   quale guardia è fallita e perché.
4. **Given** un merge che non tocca né il sito né la build map, **When** entra
   in `develop`, **Then** il sito non viene ripubblicato.
5. **Given** un branch con modifiche al sito, **When** chi mantiene il progetto
   avvia l'anteprima locale, **Then** vede il sito com'è sul branch, senza
   installare il generatore sulla propria macchina.

### User Story 3 — Leggere nella propria lingua (Priorità: P2)

Una persona legge la landing in inglese o in italiano, passa all'altra lingua e
ritrova lo stesso contenuto.

**Perché questa priorità**: il progetto è bilingue per scelta e il pubblico è
internazionale.

**Test indipendente**: si confrontano le due pagine sezione per sezione.

**Acceptance Scenarios**:

1. **Given** la landing in una lingua, **When** il lettore sceglie l'altra,
   **Then** arriva alla pagina corrispondente, all'indirizzo di quella lingua.
2. **Given** un testo inglese modificato senza aggiornare l'italiano, **When**
   girano le guardie, **Then** falliscono indicando quale testo è rimasto
   indietro.

### User Story 4 — Essere trovati e condivisi bene (Priorità: P2)

Una persona condivide il link della landing su un social o in una chat, e
l'anteprima mostra titolo, descrizione e un'immagine sensati. Un motore di
ricerca trova entrambe le lingue e sa che sono la stessa pagina tradotta.

**Test indipendente**: si ispezionano i metadati delle pagine generate e la
mappa del sito per i motori di ricerca.

**Acceptance Scenarios**:

1. **Given** una pagina generata dal modello, esclusa la 404, **When** se ne leggono i
   metadati, **Then** ha titolo e descrizione propri, un'immagine di anteprima,
   l'indirizzo canonico e il collegamento alla gemella nell'altra lingua.
2. **Given** il sito pubblicato, **When** si legge la mappa del sito per i
   motori di ricerca, **Then** elenca entrambe le lingue con i collegamenti fra
   gemelle.
3. **Given** il sito sul dominio proprio, **When** un crawler legge
   `/robots.txt` alla radice, **Then** trova le istruzioni e il rimando alla
   mappa del sito. Finché il sito vive sotto `/epocha/`, `robots.txt` non ha
   effetto (RFC 9309 lo cerca solo alla radice dell'host) e la mappa del sito si
   segnala ai motori di ricerca dai loro strumenti per i gestori di siti.

### User Story 5 — Passare al dominio proprio (Priorità: P3)

Quando l'utente registra il dominio, il sito passa al nuovo indirizzo con una
sola modifica di configurazione più le impostazioni che l'utente fa su GitHub e
sul registrar.

**Test indipendente**: si esegue la procedura documentata e si verifica che il
sito risponda sul dominio con HTTPS.

**Acceptance Scenarios**:

1. **Given** un dominio registrato, **When** si cambia l'indirizzo del sito
   nella configurazione e l'utente completa i passi su GitHub e sul registrar,
   **Then** il sito risponde sul dominio con HTTPS, tutti i metadati puntano al
   dominio nuovo, e `robots.txt` è servito alla radice.

### Edge Cases

- **La pubblicazione fallisce a metà** (rete, servizio GitHub non disponibile):
  resta online la versione precedente; il merge successivo o un avvio manuale
  del workflow da `develop` ripubblica.
- **Due merge ravvicinati**: le pubblicazioni non si sovrappongono; vince
  l'ultima.
- **Avvio manuale da un branch diverso da `develop`**: genera e controlla, ma
  non pubblica (FR-013).
- **Messa online non ancora attivata**: il workflow genera e controlla, e il
  job di pubblicazione non parte (FR-011).
- **Il cruscotto cambia aspetto**: le catture restano, perché sono datate e
  dichiarano il commit da cui vengono. Si sostituiscono quando chi mantiene il
  progetto lo decide.
- **La build map è superata al momento della pubblicazione**: il sito la
  pubblica così com'è in `develop`. La sua esattezza la governa la regola
  CRITICAL della build map, non il sito (FR-020, FR-021).
- **Un indirizzo che non esiste**: il visitatore vede una pagina 404 in entrambe
  le lingue, con l'avvertenza e il ritorno alla landing (FR-023).
- **JavaScript disattivato**: la landing resta leggibile per intero e il cambio
  lingua funziona, perché è un link e non uno script.
- **Il visitatore chiede di ridurre le animazioni**: le animazioni si fermano e
  il video non parte da solo (FR-024).
- **Una traduzione manca del tutto**: la guardia fallisce e la pubblicazione non
  parte (FR-008).
- **Una pagina generata non usa il modello base** (una pagina di servizio, un
  feed): la guardia sull'output la trova senza avvertenza e fallisce, oppure
  quel tipo di output è disattivato (FR-007).

## Requirements *(mandatory)*

### Functional Requirements

**Contenuto**

- **FR-001**: Il sito MUST avere una landing divulgativa in una sola pagina,
  in due lingue, con queste sezioni nell'ordine: avvertenza; titolo e
  sottotitolo con richiamo a GitHub e al whitepaper; che cos'è Epocha; come
  funziona un turno; catture del cruscotto; la scienza, con le fonti citate per
  autore e anno; a che punto è; domande frequenti; piè di pagina. La bozza
  grafica approvata dall'utente il 2026-09-26 fissa la direzione visiva e non è
  normativa nei dettagli; è privata e non entra nel repository.
- **FR-002**: La landing MUST NOT contenere affermazioni sull'avanzamento del
  progetto, in numeri o in prosa (conteggi di moduli, test, audit, task o
  round; percentuali; date di completamento; stati di audit; fasi o piani fatti,
  in corso o prossimi), a eccezione delle tre affermazioni dell'avvertenza. Anni
  e autori delle citazioni scientifiche non sono affermazioni di avanzamento; le
  descrizioni di ciò che Epocha fa le governa FR-004. Il rispetto è affidato
  alla revisione (D-5).
- **FR-003**: La sezione «a che punto è» MUST contenere soltanto le tre
  affermazioni dell'avvertenza, spiegate in linguaggio comune, e il rimando
  alla build map per tutto il resto.
- **FR-004**: Il riferimento per le affermazioni sulle capacità è il percorso di
  produzione del turno, che il codice stesso dichiara tale: `run_simulation_loop`
  (economia, poi un turno per agente) → `process_agent_turn` →
  `finalize_tick`, in `epocha/apps/simulation/tasks.py` ed
  `epocha/apps/agents/tasks.py`, con le funzioni che chiamano. Il percorso
  sincrono (il task `run_tick`, che il suo docstring in
  `epocha/apps/simulation/tasks.py` dice «legacy/fallback», e
  `SimulationEngine.run_tick`), che fuori dai test nessuno chiama, non conta. La landing MAY dire che un modello partecipa
  alla simulazione quando, al commit pubblicato, il percorso di produzione lo
  raggiunge, e MUST dire in parole comuni sotto quale condizione lo raggiunge
  quando ce n'è una: un flag della simulazione, dati inizializzati, l'azione
  scelta da un agente, il tipo di regime. Un modello che il percorso di
  produzione non raggiunge mai MUST essere descritto come progettato. Il
  rispetto è affidato alla revisione, che confronta ogni frase con quel
  percorso al commit pubblicato.
- **FR-005**: La sezione «domande frequenti» MUST rispondere almeno a: se Epocha
  prevede il futuro (risposta: no); se è validato; perché non è riproducibile;
  come provarlo; con quale licenza è distribuito.

**Onestà per costruzione**

- **FR-006**: Ogni pagina generata dal modello del sito MUST mostrare
  l'avvertenza nella propria lingua. L'avvertenza dice tre cose, con rimando
  alla sezione «a che punto è»: che Epocha è in sviluppo; che nessun risultato è
  validato contro dati storici (whitepaper §7.5, «Validation experiments are
  specified, not yet executed»); che le decisioni degli agenti e la generazione
  del mondo, guidate da un modello linguistico, non sono riproducibili dal seme
  (whitepaper, Abstract, §3.4 e Appendice B). Il testo dell'avvertenza MUST
  essere rivisto da ogni PR che modifica l'Abstract, §3.4, §7.5, §11 (che porta
  un limite di riproducibilità anche della parte seminata: il seme si combina
  con la chiave primaria della simulazione) o l'Appendice B del whitepaper. È una regola di revisione, dichiarata come pratica manuale e
  non come meccanismo, scritta in `CLAUDE.md` come voce propria (FR-019): la
  tabella di doc-sync esistente scatta nella direzione opposta, dal codice al
  capitolo, e non può portarla.
- **FR-007**: Una guardia sull'output MUST fallire se una pagina HTML generata,
  esclusa la build map, non contiene l'avvertenza nella lingua della pagina;
  sulla pagina 404, che è bilingue (FR-023), l'avvertenza MUST esserci in
  entrambe le lingue. I
  tipi di output che non passano dal modello base (feed, pagine di
  reindirizzamento, tassonomie) MUST essere disattivati oppure coperti dalla
  stessa guardia. La guardia MUST essere dimostrata per mutazione, cioè
  togliendo l'avvertenza apposta e osservando il fallimento prima di
  ripristinarla. Che l'avvertenza sia visibile senza scorrere lo verifica la
  revisione (SC-002), non la guardia.

**Bilinguismo**

- **FR-008**: Ogni unità di testo traducibile del sito MUST esistere in
  entrambe le lingue, con l'inglese normativo e l'italiano mirror. Sono unità
  di testo: ogni blocco di contenuto della landing (titolo, paragrafo, voce di
  elenco, domanda e risposta), ogni stringa del modello (avvertenza, menu, piè
  di pagina, pagina 404), ogni didascalia e testo alternativo delle catture, e
  titolo e descrizione di ogni pagina. Una guardia sui sorgenti MUST fallire se
  un'unità manca in una lingua. Ogni unità italiana MUST portare un'impronta
  dell'unità inglese da cui è tradotta, e una guardia sui sorgenti MUST fallire
  quando l'inglese cambia senza che l'impronta dell'italiano venga aggiornata.
  Il limite è lo stesso della build map e va dichiarato: l'impronta rende
  visibile una traduzione dimenticata, non distingue una traduzione vera da un
  aggiornamento pigro dell'impronta.

**Catture**

- **FR-009**: Ogni cattura del cruscotto MUST venire da una simulazione di prova
  in un ambiente locale, eseguita sul percorso di produzione del turno di
  FR-004, così che ciò che le catture mostrano e ciò che la landing descrive
  siano lo stesso percorso; MUST NOT mostrare credenziali, chiavi, indirizzi email o
  altri dati personali, e MUST avere una didascalia in entrambe le lingue con che
  cosa mostra, il commit abbreviato, la data e la dicitura «simulazione di prova,
  non validata». Ogni immagine MUST avere un testo alternativo in entrambe le
  lingue; il video MUST avere una descrizione testuale equivalente in entrambe
  le lingue.
- **FR-010**: I file multimediali MUST restare entro questi tetti, proposti come
  euristiche regolabili e non come valori derivati: ogni immagine al massimo
  500 kB, un solo video al massimo 5 MB, senza audio, il totale dei file
  multimediali presenti al massimo 15 MB. Una guardia sui sorgenti MUST fallire
  se un tetto è superato. La ragione è che ogni versione di un file binario
  resta nella storia git e pesa su ogni clone; i limiti di GitHub Pages (1 GB
  per il sito pubblicato, 100 GB al mese di banda come limite morbido) sono
  lontani. Il limite va dichiarato: la guardia misura i file presenti, non la
  storia, quindi sostituzioni ripetute di un file restano entro il tetto e
  accumulano comunque peso; lo si governa sostituendo le catture di rado, per
  decisione di chi mantiene il progetto.

**Pubblicazione**

- **FR-011**: Il sito MUST essere generato e controllato da un workflow dedicato
  che parte (a) a ogni PR verso `develop` che tocca i sorgenti del sito, la build
  map o il workflow stesso, senza pubblicare; (b) a ogni push su `develop` che
  tocca gli stessi percorsi; (c) su avvio manuale. La pubblicazione MUST partire
  solo nei casi (b) e (c), solo da `develop`, e solo quando la messa online è
  stata attivata dall'utente con un'impostazione del repository. Due
  pubblicazioni MUST NOT sovrapporsi.
- **FR-012**: Le guardie sui sorgenti (FR-008, FR-010, FR-025, la presenza
  dell'avvertenza in entrambe le lingue del modello) MUST girare prima della
  generazione, MUST far parte della suite del progetto e MUST NOT richiedere il
  generatore. Le guardie sull'output (FR-007, FR-015, la presenza dei metadati
  di FR-016) MUST girare dopo la generazione e prima della pubblicazione, nel
  workflow. Nessuna pubblicazione MUST partire se una guardia fallisce. Il costo
  di eseguire le guardie sui sorgenti nel workflow, con la configurazione di
  test del progetto (che in `pyproject.toml` impone le impostazioni Django a
  ogni esecuzione di pytest), va misurato e dichiarato in fase di piano.
- **FR-013**: La versione del generatore e lo SHA-256 atteso del suo binario
  MUST stare in un solo file del repository, letto sia dal workflow sia
  dall'anteprima locale; il workflow MUST rifiutare un binario il cui SHA-256 non
  coincide. Le azioni di terze parti MUST essere fissate a un commit. I permessi
  MUST essere dichiarati per job: generazione e guardie con la sola
  `contents: read`; pubblicazione con `pages: write` e `id-token: write`,
  nell'ambiente di pubblicazione di GitHub Pages. Il workflow MUST NOT
  conservare le credenziali del checkout e MUST NOT usare l'evento
  `pull_request_target`. Il vincolo «si pubblica solo da `develop`» lo fa
  rispettare la regola di protezione dell'ambiente di pubblicazione impostata
  dall'utente (FR-018); il controllo sul riferimento dentro il workflow è una
  difesa secondaria, perché su una PR gira il workflow della PR stessa, che
  potrebbe toglierlo.
- **FR-014**: MUST esistere un'anteprima locale che non richiede di installare
  il generatore sulla macchina di chi mantiene il progetto, che usa la versione
  e il checksum di FR-013 e, se passa da un'immagine container, la fissa per
  digest.

**Privacy, visibilità, accessibilità**

- **FR-015**: Il codice del sito MUST NOT caricare risorse da server esterni
  (caratteri tipografici, script, fogli di stile, analitiche, video incorporati)
  e MUST NOT impostare cookie. I caratteri tipografici, se non di sistema, MUST
  essere incorporati e distribuiti con una licenza che lo consente. Una guardia
  sull'output MUST fallire se una pagina generata richiama un indirizzo esterno
  come risorsa; i link di navigazione verso siti esterni sono ammessi. Il sito
  MUST dichiarare nel piè di pagina ciò che non controlla: l'hosting (GitHub
  Pages) registra gli indirizzi IP dei visitatori secondo le condizioni di
  GitHub, e la build map ricorda la lingua scelta nella memoria locale del
  browser senza trasmetterla.
- **FR-016**: Ogni pagina generata dal modello MUST avere titolo e descrizione
  propri, metadati di anteprima per la condivisione con un'immagine,
  l'indirizzo canonico e il collegamento alla gemella nell'altra lingua. Il sito
  MUST pubblicare la mappa per i motori di ricerca con entrambe le lingue.
  L'indirizzo base del sito MUST essere un solo valore di configurazione (D-9).
  `robots.txt` MUST essere pubblicato alla radice dell'host dal momento del
  passaggio al dominio proprio. Due eccezioni sono dichiarate. La build map ha
  un solo indirizzo per le due lingue, nessun collegamento a gemelle ed è
  elencata una volta nella mappa del sito. La pagina 404 non ha indirizzo
  canonico né gemella, chiede ai motori di ricerca di non indicizzarla ed è
  fuori dalla mappa del sito; la guardia sui metadati la tratta di conseguenza.
- **FR-024**: La landing e la pagina 404 MUST rispettare il livello AA delle
  WCAG 2.1. Il video MUST NOT partire da solo, MUST avere i controlli di
  riproduzione e MUST NOT animarsi quando il visitatore chiede di ridurre il
  movimento; ogni altra animazione MUST fermarsi nello stesso caso. La build
  map pubblicata è un'eccezione dichiarata, come in FR-021: il file non porta
  l'attributo di lingua del documento né le indicazioni per gli schermi da
  telefono (verificato su `develop` a `2223968`), e il sito non lo modifica.

**Documenti del progetto e governance**

- **FR-017**: `README.md` e `README.it.md` MUST perdere l'intera sezione Status
  (tabella e paragrafo che la segue), le parti della sezione Roadmap che
  ripetono lo stato e le annotazioni di audit nell'albero delle cartelle (per
  esempio «(audited)»), sostituite da un rimando alla build map; la qualifica
  dei metodi nell'elenco della documentazione («all audited to convergence» in
  inglese, «tutti convergenti all'audit» in italiano) MUST diventare un rimando
  alla build map. La Vision MUST essere riformulata in modo che scala e
  numero di agenti siano presentati come obiettivi di progetto e non come
  capacità, e che non affermi che dinamiche auditate governano la simulazione.
  Il badge «MVP in development» resta, perché dice la stessa cosa
  dell'avvertenza. Entrambi i README MUST linkare il sito. Il requisito si
  applica ai README come saranno dopo il merge del Plan 4.
- **FR-018**: La procedura per passare al dominio proprio e i passi che spettano
  all'utente (attivazione di Pages, attivazione della messa online, regola di
  protezione dell'ambiente di pubblicazione limitata a `develop`, dominio,
  record DNS, HTTPS, segnalazione della mappa del sito ai motori di ricerca)
  MUST essere documentati nel repository.
- **FR-019**: `CLAUDE.md` MUST essere aggiornato in due punti. La regola
  CRITICAL della build map MUST dichiarare il sito come terza rappresentazione
  dello stesso file, con i ruoli del passo 2, punto 2: il file in `develop` è la
  fonte, il sito ne mostra lo stato mergiato, l'artifact è lo specchio di lavoro
  che può anticiparlo. Una voce propria, distinta dalla tabella di doc-sync e
  dichiarata pratica manuale, MUST dire due cose: una PR che modifica
  l'Abstract, §3.4, §7.5, §11 o l'Appendice B del whitepaper rivede
  l'avvertenza del sito (FR-006); una PR che modifica il percorso di produzione
  del turno di FR-004, o i flag e le condizioni che decidono se un modello vi
  entra, rivede le frasi della landing sulle capacità. Le altre sedi in cui vive
  la regola della build map (la costituzione, la memoria
  `feedback_build_map_source_of_truth.md` con la sua copia di backup, l'indice
  `MEMORY.md` con la sua copia, i due README, elencate nel commit `a73927e`)
  MUST dire la stessa cosa sulle tre rappresentazioni, oppure rimandare a
  `CLAUDE.md` come unica sede normativa.
- **FR-020**: Prima che l'utente attivi la messa online, la build map in
  `develop` MUST essere verificata contro il codice e il whitepaper secondo il
  passo 1 della sua procedura, e ogni affermazione superata ancora presente dopo
  il merge del Plan 4 MUST essere corretta da questo work item in fase 5, come
  aggiornamento della build map secondo la sua regola CRITICAL (italiano e
  inglese insieme, impronte ricalcolate, ripubblicazione sullo stesso URL). Al
  2026-09-26 è noto il paragrafo `hb.p0`, che sul ramo Plan 4 colloca la
  validazione storica dentro il Plan 4 mentre il §9 del whitepaper dello stesso
  ramo la esclude; `hb.p1`, superato in `develop`, è corretto in entrambe le
  lingue sul ramo Plan 4 dal commit `91b9599` (passo 3, punto 1). L'elenco si
  riverifica dopo il merge («Sequenza e dipendenze»). Nella stessa
  ripubblicazione va corretta anche la voce `13.desc` aggiunta all'apertura di
  questo work item, che nell'artifact dice «su ogni pagina» mentre FR-021
  esclude la build map.
- **FR-021**: Il sito MUST pubblicare la build map intatta, senza modifiche al
  contenuto, e MUST NOT aggiungervi l'avvertenza. Il limite va dichiarato: chi
  arriva direttamente alla build map da un motore di ricerca non vede
  l'avvertenza del sito, e la mappa non porta un'avvertenza esplicita su
  validazione e riproducibilità (verificato su `develop` a `2223968`). Che la
  mappa non suggerisca una validazione eseguita è compito di FR-020 prima della
  messa online e della sua regola CRITICAL dopo.
- **FR-022**: La costituzione MUST essere emendata (versione 1.2.0) nella
  sezione Development Workflow, perché elenchi fra i deliverable con prosa
  tecnica tradotta anche il sito (inglese normativo, italiano mirror,
  allineamento sorvegliato da una guardia strutturale, FR-008, non garantito:
  l'impronta rende visibile una traduzione dimenticata, non ne certifica la
  correttezza) e il README, già bilingue e oggi
  assente dall'elenco (inglese normativo, italiano companion, allineamento
  affidato alla revisione). L'emendamento segue la procedura di Governance:
  approvazione esplicita dell'utente, voce nella memoria
  `feedback_canonical_workflow.md`, aumento di versione con data, indicazioni per
  i work item in corso. La regola sulla lingua non cambia: il sito sta con
  «tutto il resto».
- **FR-023**: Il sito MUST avere una pagina 404 con entrambe le lingue,
  l'avvertenza e il collegamento alla landing in ciascuna lingua.
- **FR-025**: Una guardia sui sorgenti MUST leggere il file del workflow e
  fallire in ciascuno di questi casi, senza dover classificare quali job o step
  siano «di guardia». (a) Un job del workflow diverso da quello di
  pubblicazione non compare fra le dipendenze dirette (`needs`) del job di
  pubblicazione: la regola è a mondo chiuso, quindi un job nuovo aggiunto senza
  aggiornare `needs` la fa fallire. Ne segue un vincolo per il piano: ogni job
  diverso dalla pubblicazione deve girare anche sui push e sugli avvii manuali
  da `develop`, perché un job saltato fa saltare in silenzio la pubblicazione. (b) Un job diverso da quello di
  pubblicazione, o uno dei suoi step, dichiara `continue-on-error`. (c) La
  condizione di avvio (`if`) del job di pubblicazione contiene una qualunque
  delle quattro funzioni di stato di GitHub Actions (`success()`, `always()`,
  `failure()`, `cancelled()`). Senza funzioni di stato vale il `success()`
  implicito, che è esattamente il comportamento voluto; scritte in modo
  esplicito, anche `success()` dentro una disgiunzione, permettono di partire
  dopo un fallimento. La guardia
  MUST essere dimostrata per mutazione su quattro casi: togliere una
  dipendenza, aggiungere un job nuovo senza aggiornare `needs`, aggiungere
  `continue-on-error`, aggiungere `always()`, osservando ogni volta il
  fallimento prima di ripristinare. Il
  limite va dichiarato: nessuna guardia strutturale vede un comando di guardia
  che ingoia il proprio codice di uscita (per esempio `|| true`), né la
  rimozione di un job di guardia insieme alla sua voce in `needs`, che lo fa
  uscire dall'insieme controllato; li copre la revisione del workflow. Un avvio reale a messa online spenta non
  darebbe questa prova, perché il job di pubblicazione non parte in nessun caso
  (SC-005b). Leggere il workflow richiede un parser YAML; se la dipendenza
  manca dai requirements, il piano la dichiara.

### Key Entities

- **Landing**: la pagina divulgativa, un testo normativo inglese e un mirror
  italiano, pubblicati a due indirizzi.
- **Avvertenza**: il testo fisso su sviluppo, validazione e riproducibilità,
  parte del modello comune, ancorato ai capitoli del whitepaper di FR-006.
- **Unità di testo**: la granularità a cui si misura l'allineamento fra le
  lingue (FR-008).
- **Cattura**: un'immagine o un video del cruscotto, con didascalia e testo
  alternativo bilingui, commit e data.
- **Build map pubblicata**: la copia intatta di `docs/build-map/epocha-build-map.html`
  allo stato di `develop`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Tre persone che non sviluppano software, dopo aver letto solo la
  landing, sanno dire con parole proprie che cos'è Epocha e che i suoi risultati
  non sono validati. Il criterio si considera raggiunto con tre su tre; se una
  persona fallisce, si corregge il testo e si ripete con una persona nuova.
- **SC-002**: L'avvertenza è visibile senza scorrere su entrambe le pagine, a
  390 pixel di larghezza (telefono) e a 1440 (computer), verificato in
  revisione con catture dello schermo.
- **SC-003**: Caricando la landing con il registro di rete aperto, zero
  richieste vanno a domini diversi da quello del sito e zero cookie vengono
  impostati.
- **SC-004**: Un merge in `develop` che modifica un testo della landing, con la
  messa online attivata, è pubblicato alla fine del workflow senza passi
  manuali, e visibile ai visitatori entro la scadenza della cache di GitHub
  Pages (10 minuti, misurati il 2026-09-26 sull'intestazione `cache-control`).
- **SC-005a**: Una PR che rimuove l'avvertenza dal modello fa fallire le
  guardie; dimostrato una volta sul repository reale prima della chiusura.
- **SC-005b**: La guardia strutturale sul file del workflow (FR-025) va rossa
  in ciascuna delle quattro mutazioni (dipendenza tolta, job nuovo fuori da
  `needs`, `continue-on-error` aggiunto, `always()` aggiunto) e verde sul
  workflow reale. Un avvio reale non
  potrebbe dimostrarlo: a messa online spenta il job di pubblicazione non parte
  comunque, che una guardia fallisca o no, quindi l'osservazione non distingue i
  due casi.
- **SC-006**: Un controllo automatico di accessibilità secondo WCAG 2.1 AA sulla
  landing nelle due lingue e sulla pagina 404 non riporta violazioni; lo
  strumento lo sceglie il piano. Un controllo automatico copre solo una parte
  dei criteri WCAG, quindi tastiera, ordine del focus e contrasto delle catture
  si verificano anche in revisione.
- **SC-007**: I due README, dopo il merge di questo work item, non contengono
  la sezione Status, stati di avanzamento nella Roadmap, annotazioni di audit
  nell'albero delle cartelle o la qualifica dei metodi («all audited to
  convergence», «tutti convergenti all'audit»); la Vision non presenta scala e
  numero di agenti come capacità e non afferma che dinamiche auditate governano
  la simulazione; entrambi linkano il sito.
- **SC-008**: Ogni cattura pubblicata ha didascalia bilingue con commit e data,
  e testo alternativo o descrizione bilingue.

## Assumptions

- Le lingue sono due e restano due.
- L'attivazione di GitHub Pages, l'attivazione della messa online, la regola di
  protezione dell'ambiente di pubblicazione, la registrazione del dominio, i
  record DNS, l'attivazione di HTTPS e la segnalazione della mappa del sito ai
  motori di ricerca li fa l'utente: sono impostazioni di account.
- Le catture si prendono dal cruscotto esistente su una simulazione di prova
  eseguita in locale, con le chiavi del fornitore di modelli linguistici già
  configurate per lo sviluppo, quando il gate del Plan 4 è chiuso e i container
  sono liberi.
- Il sito è pubblico come il repository; nessun contenuto del sito è riservato.
- Il testo definitivo della landing lo scrive chi lavora al progetto e lo
  approva l'utente in fase 5; questa spec ne fissa struttura e vincoli, non la
  prosa.

## Non-goals

- Il whitepaper non si rende sul sito: resta su GitHub e la landing lo linka.
- Nessuna sezione notizie nella prima uscita. Si aggiungerà quando ci sarà la
  prima notizia da scrivere; Hugo la rende un'aggiunta, non una riscrittura.
- Nessuna guida per contributori sul sito: resta nel README e in `CLAUDE.md`.
- Nessuna ricerca interna, nessun commento, nessuna newsletter, nessuna
  analitica.
- Nessuna modifica al cruscotto dell'operatore.
- Non si corregge `ci.yml` (vedi «Problemi trovati e non risolti qui»).

## Quando riconsiderare questa scelta

La scelta di un sito statico su GitHub Pages va riaperta, con un work item
dedicato, se si verifica almeno una di queste condizioni:

- a scrivere i contenuti sono persone che non usano GitHub;
- il sito diventa prevalentemente editoriale: molti articoli, eventi, una
  comunità da moderare;
- servono funzioni da prodotto sul sito stesso (account, pagamenti, area
  riservata), che però di norma appartengono all'applicazione e non alla
  vetrina;
- Epocha diventa un prodotto commerciale: le condizioni d'uso di GitHub Pages
  escludono i siti rivolti principalmente a transazioni commerciali o a software
  commerciale come servizio. In quel caso il sito statico si sposta su un altro
  servizio di hosting statico senza cambiare tecnologia.

## Il costo, dichiarato

**Una tantum**: il modello grafico della landing, i testi in due lingue, le
catture, il workflow, le due classi di guardie con le loro prove per mutazione,
l'anteprima locale, la correzione del README, gli aggiornamenti di `CLAUDE.md`
e l'emendamento della costituzione.

**Ricorrente**: ogni modifica di un testo della landing costa il doppio in
scrittura, più l'aggiornamento dell'impronta; ogni nuova cattura aggiunge peso
permanente alla storia git; il dominio costa circa 15 dollari l'anno se
l'utente sceglie `epocha.app`.

**Dipendenza nuova**: Hugo, presente solo nel workflow e nell'anteprima locale,
non nei requisiti Python del progetto. Il suo prezzo va detto: Hugo è ancora in
versione 0.x, quindi non promette compatibilità fra versioni minori; la 0.146.0
del 2025-04-10, per esempio, ha rinnovato il sistema dei modelli chiedendo
esplicitamente di ritestare i siti. Ogni aggiornamento di versione va quindi
trattato come una modifica da verificare, non come una routine.
È lo stesso argomento usato contro Astro, applicato anche a Hugo; lo si accetta
perché la versione è fissata (FR-013) e il costo di sostituirlo è contenuto: i
testi sono file di testo e il modello grafico è HTML e CSS.

## Rischi dichiarati

- **Che la landing prometta più del progetto.** È il rischio principale e
  nessun meccanismo lo elimina. Lo riducono FR-002, FR-003, FR-004 e l'audit di
  fase 6, che verifica ogni affermazione della landing contro il codice e il
  whitepaper.
- **Che le catture non siano presentabili.** Il grafo sociale del cruscotto è
  già annotato come da migliorare (memoria `feedback_graph_improvement.md`). Se
  succede, lo si dice all'utente e si apre un work item sul cruscotto.
- **Che il sito pubblichi una build map superata.** Il sito la ripubblica a ogni
  merge, ma non può renderla esatta. FR-020 copre la prima pubblicazione; dopo,
  vale la regola CRITICAL della build map.
- **Che il nome sia ambiguo.** «Epocha» è anche il nome di un periodico ceco di
  divulgazione scientifica pubblicato dal 2005, e somiglia a Epoch AI. Lo si
  affronta con i contenuti e con i link dal repository, non con il nome del
  dominio.
- **Che l'indirizzo GitHub Pages non reindirizzi al dominio proprio.** La
  documentazione di GitHub consultata il 2026-09-26 non lo dice in modo esplicito
  per i siti di progetto. Va verificato quando l'utente attiva il dominio; se non
  reindirizza, i link condivisi prima del cambio vanno aggiornati a mano.
- **Che il merge del Plan 4 cambi i fatti sotto la spec.** Gestito da «Sequenza e
  dipendenze».

## Problemi trovati e non risolti qui

Emersi durante il brainstorming e l'audit, segnalati all'utente, fuori dal
perimetro:

- `ci.yml` scatta solo su push e PR verso `main`, quindi lint e test non girano
  su nessuna PR verso `develop`. Va aperto un work item dedicato; FR-011 copre
  soltanto il sito.
- La build map: `hb.p1` in `develop` dice «APERTO» un work item mergiato con
  `fb893f5`, ed è già corretto in entrambe le lingue sul ramo Plan 4
  (`91b9599`); `hb.p0` sul ramo Plan 4 colloca la validazione storica dentro il
  Plan 4, contro il §9 del whitepaper dello stesso ramo. Ciò che resta dopo il
  merge lo corregge questo work item (FR-020).
- Il cruscotto e l'API avviano le simulazioni sul percorso di produzione
  (`simulation_play_view` in `epocha/apps/dashboard/views.py` e l'azione `play`
  in `epocha/apps/simulation/views.py` chiamano `run_simulation_loop`).
  `SimulationEngine.run_tick` lo chiamano i test
  (`tests/test_integration.py` ed `epocha/apps/simulation/tests/test_engine.py`)
  e il task `run_tick`, che a sua volta non chiama nessuno; sul ramo Plan 4 quel percorso non
  contiene il blocco demografico per turno, quindi quei test verificano un
  percorso che la produzione non usa. Due docstring sono superati dal codice:
  quello di `SimulationEngine` («For synchronous execution (tests,
  dashboard)») e quello del task `run_tick` («Kept for backward compatibility
  with the dashboard's synchronous tick execution»). Non sono difetti del sito,
  ma vanno tracciati come work item del simulatore.

## FAQ

**Perché non WordPress, visto che l'utente l'ha chiesto due volte?** Perché le
tre ragioni date (migliorie, avanzamenti, visibilità) non dipendono dal CMS, e
WordPress aggiungerebbe database, hosting a pagamento, aggiornamenti di
sicurezza e un luogo in cui il testo sfugge alle guardie. La decisione resta
dell'utente, che ha scelto il sito statico dopo il confronto; le condizioni per
riaprirla sono scritte sopra.

**Perché non MkDocs, che era la prima raccomandazione?** Perché la verifica del
2026-09-26 ha trovato l'ecosistema in transizione: ultima release 1.x di circa
venticinque mesi fa, 2.0 incompatibile con il tema, tema in fine vita a maggio
2027, successore in alpha. Per un sito nuovo sarebbe una migrazione obbligata
già in calendario.

**Perché Hugo e non l'HTML scritto a mano, che è più semplice?** Per una pagina
sola lo sarebbe. L'utente ha chiesto un sito che cresca per anni; su più pagine
l'HTML a mano ripete intestazione, menu, piè di pagina e avvertenza in ogni
file, e ogni ripetizione è una copia che diverge. Hugo scrive quelle parti una
volta sola.

**Perché non Astro, se anche Hugo rompe la compatibilità?** Perché i due costi
non sono uguali. Astro porta Node e npm, cioè centinaia di pacchetti di terzi
da aggiornare in un progetto Python; Hugo è un solo binario, con versione e
checksum fissati nel repository, che si aggiorna quando lo si decide.

**Hugo decide l'aspetto del sito?** No. Hugo compone le pagine a partire dal
modello grafico e dai testi; l'aspetto è quello del modello. L'utente l'ha visto
nella bozza grafica del 2026-09-26.

**Perché l'inglese è normativo se l'utente scrive in italiano?** Perché la
costituzione mette l'italiano solo su spec e build map e l'inglese su tutto il
resto, README compreso, e il sito ha lo stesso pubblico del README. L'utente
l'ha scelto dopo il round 1. Normativo vuol dire che, se le due versioni
divergono, si corregge l'italiano; l'utente approva comunque entrambe prima
della pubblicazione.

**Perché serve un emendamento della costituzione per una questione di lingua?**
Perché la costituzione elenca in forma chiusa i deliverable bilingui e chiede a
ciascuno di dichiarare come le lingue restano allineate. Un terzo deliverable
fuori elenco è esattamente la prosa che promette più del meccanismo, e il
README è già un caso non dichiarato.

**Perché non una lista di parole vietate per garantire l'onestà?** Perché
l'avvertenza deve contenere proprio quelle parole in forma negata, quindi la
lista avrebbe bisogno di eccezioni, e basterebbe una parafrasi per aggirarla. Un
controllo che si aggira con una parafrasi dà una falsa sicurezza.

**Perché la landing non dice quanti moduli sono auditati? È un'informazione
utile.** Lo è, e sta nella build map, che si aggiorna a ogni checkpoint. Scritta
nella landing diventerebbe falsa al primo merge.

**Perché la build map non porta l'avvertenza del sito?** Perché aggiungerla
vorrebbe dire modificare la fonte di verità a ogni pubblicazione. Il prezzo è
reale: chi arriva direttamente alla mappa non legge l'avvertenza, e la mappa non
la contiene in forma esplicita. Il limite è scritto in FR-021.

**Il sito e l'artifact della build map possono mostrare cose diverse?** Sì, per
il tempo che passa fra un checkpoint su un branch e il suo merge; è successo il
giorno stesso in cui questa spec è stata scritta. La spec lo dichiara invece di
negarlo (FR-019).

**Perché le guardie sono divise in due classi?** Perché alcune leggono i
sorgenti e possono girare ovunque, anche nella suite, mentre altre leggono
l'HTML generato e richiedono Hugo. Chiederle tutte nello stesso posto era
impossibile per costruzione (D-11).

**Perché la prima messa online non parte da sola al merge?** Perché la sua
precondizione, una build map verificata (FR-020), si può soddisfare solo dopo il
merge del Plan 4, e perché attivare Pages è un'impostazione dell'utente. Un'impostazione esplicita
del repository rende la messa online una decisione, non un effetto collaterale
del merge.

**Che cosa è deterministico?** La generazione del sito: stesso commit e stessa
versione fissata del generatore producono le stesse pagine. Non lo sono le
catture, che vengono da simulazioni guidate da un modello linguistico senza
seme; per questo portano commit e data e non vengono rigenerate.

**Come si torna indietro da una pubblicazione sbagliata?** Con un revert in
`develop`: il workflow ripubblica la versione precedente. Non ci sono database
né server da ripristinare.

**Qual è la superficie di attacco?** Un sito statico senza moduli, senza
account e senza script di terze parti non ha input da validare. Restano la
catena di pubblicazione e le catture. La catena è coperta da FR-013: versione e
SHA-256 del binario fissati nel repository, azioni fissate a un commit, permessi
per job (la generazione legge soltanto; solo la pubblicazione scrive su Pages),
credenziali del checkout non conservate, nessun `pull_request_target`. Il
vincolo di pubblicare solo da `develop` lo fa rispettare la regola di
protezione dell'ambiente che l'utente imposta (FR-018); il controllo sul
riferimento dentro il workflow è solo una difesa secondaria, perché una PR
esegue il proprio workflow e potrebbe toglierlo. Un checksum preso dalla stessa release del binario
proteggerebbe solo dalla corruzione, non da una release compromessa: per questo
l'hash atteso sta nel repository. Le catture, che potrebbero esporre dati, sono
coperte da FR-009. GitHub Pages non permette intestazioni HTTP personalizzate:
una politica di sicurezza dei contenuti, se utile, si può dichiarare solo dentro
la pagina.

**Il sito traccia i visitatori?** Il codice del sito no: niente cookie, niente
analitiche, niente risorse esterne. L'hosting sì, nel senso che GitHub registra
gli indirizzi IP dei visitatori; il sito lo dichiara invece di promettere
«nessun tracciamento» (FR-015).

**Quanto costa tenerlo in piedi?** Zero per hosting e pubblicazione, perché il
repository è pubblico. Il dominio, a scelta dell'utente, circa 15 dollari l'anno
per `epocha.app`. Il resto è tempo di scrittura, dichiarato in «Il costo».

**Che cosa succede quando Epocha diventa prodotto?** Lo schema abituale separa
la vetrina statica dall'applicazione, e le funzioni da prodotto vivono
nell'applicazione Django. La vetrina resta com'è, salvo le condizioni scritte in
«Quando riconsiderare questa scelta», tra cui le condizioni d'uso di GitHub
Pages per i prodotti commerciali.

# Fase 0 — Le deliberazioni scientifiche

**Branch**: `20260806-112409-demography-design-defects` | **Spec**: [spec.md](./spec.md) | **Piano**: [plan.md](./plan.md)

Questo documento raccoglie le tre deliberazioni che la fase 0 del piano richiede, ciascuna svolta col processo in tre passi imposto dal principio IV della costituzione: proposta iniziale, prima autocritica, seconda autocritica e consolidamento. Il materiale di partenza per la prima è in [research/0.1a-distributional-family-INPUT.md](./research/0.1a-distributional-family-INPUT.md), che è dichiaratamente un input non deliberato: le sue conclusioni sono state riverificate qui una per una, e **due dei costi che dichiarava non reggono alla misura**.

Tutte le cifre di questo documento sono misurate, non ereditate. Lo strumento di misura è descritto nella sezione seguente ed è stato tarato prima dell'uso.

---

## Lo strumento di misura, e perché è tarato prima di misurare

Ogni cifra sulle famiglie distribuzionali viene da un banco Monte Carlo che ri-trascrive il kernel poligenico invece di importarlo da `epocha/apps/demography/inheritance.py`. La trascrizione è deliberata: se il banco importasse il modulo, una divergenza fra ciò che il modulo fa e ciò che credo faccia si annullerebbe da entrambi i lati e resterebbe invisibile.

Prima di misurare qualunque candidato, il banco deve ritrovare un numero già noto per via analitica. Sotto accoppiamento casuale, con coefficiente `a` applicato al valore medio dei genitori, la varianza stazionaria soddisfa `V = a²·V/2 + (1−a)²·σ²`, quindi la dispersione realizzata vale `σ·√((1−a)²/(1−a²/2))`. Su 60.000 agenti per quindici generazioni:

| ereditabilità dichiarata | misurato | analitico |
|---|---|---|
| 0,22 | 79,1% | 79,0% |
| 0,30 | 71,8% | 71,6% |
| 0,44 | 59,0% | 58,9% |
| 0,55 | **48,9%** | **48,8%** |

Il banco ritrova il 48,8% che la spec dichiara, entro un decimo di punto, su quattro ereditabilità e non su una. Da qui in avanti le cifre che produce su configurazioni ignote sono utilizzabili.

Si noti già qui un fatto che serve più avanti: la perdita di dispersione **non è un caso limite dell'ereditabilità più alta**. I cinque template dichiarano ereditabilità fra 0,22 e 0,55 per tredici tratti, e su tutto quell'intervallo il kernel attuale perde fra il 21% e il 51% della dispersione dichiarata.

---

## Deliberazione 0.1a — La famiglia distribuzionale

> **AVVERTENZA — LA CONCLUSIONE DI QUESTA DELIBERAZIONE È STATA RIBALTATA.** Il testo che segue documenta la deliberazione come fu svolta, e la sua conclusione era **la scala latente logit**. Il **secondo giro del gate avversariale l'ha demolita**: l'argomento a favore del logit poggiava sullo spazio dei parametri che la deliberazione 0.2 avrebbe aperto, e 0.2 — scritta con i numeri dentro, come il primo giro imponeva — dichiara medie che **chiudono** quello spazio. Alle due coppie effettivamente dichiarate le due famiglie misurano quasi identico, e l'onere della prova non è assolto.
>
> **La decisione vigente è nell'emendamento**, sezione A1 di `docs/superpowers/specs/2026-04-18-demography-design-it.md`: **famiglia normale con troncamento e residuo riscalato per ramo**, con la scala latente logit come via di migrazione dichiarata e attivata da un controllo di caricamento. Anche la scala di `σ_clark` di 0.2 è superata: non si legge dall'identità ma si **risolve** numericamente, perché arrotondamento e clamp sono non lineari.
>
> Questo documento è conservato come **registro del processo**, non come fonte della decisione. Dove diverge dall'emendamento, prevale l'emendamento.


### Il problema, riformulato con precisione

I caratteri trasmessi vivono su `[0,1]`. Il kernel li campiona da una normale non limitata e poi tronca il risultato con `max(lo, min(hi, result))` ([inheritance.py:441](../../epocha/apps/demography/inheritance.py:441)). La deliberazione era stata aperta sul troncamento; la ricerca preliminare sosteneva che il difetto vero fosse invece la scala del residuo. **Entrambe le formulazioni sono incomplete**, e la prima autocritica mostra perché.

Va separato subito ciò che la deliberazione decide da ciò che non decide. La **scala del residuo** non è una scelta: discende dall'identità di varianza appena si dichiari che l'ampiezza realizzata debba eguagliare quella dichiarata. Con `a` il coefficiente applicato alla deviazione dei genitori dalla media, e imponendo `V = σ²`:

- due genitori, coefficiente `a` sul valore medio: `V = a²·V/2 + c²σ²` → **`c = √(1 − a²/2)`**
- un genitore, coefficiente `a/2`: `V = (a²/4)·V + c²σ²` → **`c = √(1 − a²/4)`**
- nessun genitore, nessun segnale: → **`c = 1`**

A `a = 0,55` valgono 0,9213, 0,9614 e 1. Applicando ovunque il primo si ottiene 95,8% nel ramo a un genitore e 92,1% in quello senza: sono le due cifre che SC-013 riporta come misurate, ritrovate qui per via indipendente. La correzione di FR-003 è quindi **determinata**, e resta valida qualunque famiglia si scelga. Ciò che la deliberazione decide davvero è soltanto **su quale scala** applicare questa aritmetica.

### Passo 1 — Proposta iniziale

Tre candidati, come il piano prescrive.

**Normale ricalibrata.** Si tiene la famiglia attuale e si corregge la sola scala del residuo, ramo per ramo. Costo di implementazione: tre righe. Nessun parametro nuovo, nessuna migrazione, nessuna reinterpretazione dei template.

**Scala latente logit.** Si porta il carattere su scala logit, si fa la genetica additiva lì con la stessa identità di varianza, e si espone `[0,1]` come immagine dell'inversa logistica. È il dispositivo classico della genetica quantitativa per caratteri la cui scala osservata non è quella su cui gli effetti sono additivi. Costo: una soluzione numerica per era e per tratto, perché la logit-normale non ha momenti in forma chiusa, più la reinterpretazione dell'ereditabilità come quantità di scala latente.

**Beta.** Supporto naturale su `[0,1]`, due parametri. Respinta già in proposta, e non per comodità: la varianza di una Beta è strutturalmente vincolata dalla media, quindi la proprietà "ampiezza dichiarata = ampiezza realizzata" è soddisfacibile solo dentro una regione dipendente dalla media; e la famiglia non è chiusa sotto le operazioni della genetica additiva, quindi `a·midparent + c·rumore` non è una Beta e non ha distribuzione stazionaria in forma chiusa. In letteratura la Beta compare per le frequenze alleliche, non per i fenotipi: citarla per la trasmissione fenotipica sarebbe la stessa attribuzione approssimativa che la User Story 2 esiste per correggere.

La proposta iniziale raccomandava il **logit**, sulla base della premessa ereditata dal brief: che la normale troncata fallisse SC-013 e che il cambio di famiglia fosse quindi obbligato.

### Passo 2 — Prima autocritica: la premessa è falsa

La regola per cui l'onere della prova sta su chi aggiunge impone di chiedere dove la normale ricalibrata **rompa davvero**, invece di assumere che rompa. Misurato, a `h² = 0,55`, ampiezza dichiarata 0,15, ramo a due genitori:

| media d'era | normale: ampiezza realizzata | massa sul bordo | media realizzata | logit: ampiezza realizzata | massa sul bordo |
|---|---|---|---|---|---|
| 0,50 | 100,1% | 0,07% | 0,5004 | 100,1% | 0,00% |
| 0,60 | 99,7% | 0,42% | 0,6000 | 100,0% | 0,00% |
| 0,70 | 97,8% | 2,37% | 0,6977 | 99,8% | 0,00% |
| 0,80 | **91,8%** | **8,23%** | 0,7882 | 99,6% | 0,00% |
| 0,85 | 86,8% | 13,79% | 0,8281 | 99,4% | 0,00% |
| 0,90 | 80,5% | 20,52% | 0,8631 | 99,1% | 0,00% |

**La premessa del brief non regge.** Il valore dell'86,4% che circolava per il ramo senza genitori descrive un modello in cui FR-003 è corretto solo a metà, cioè in cui il coefficiente del ramo a due genitori è applicato anche al ramo che non ne ha. Correggendo il residuo per ramo, come FR-003 impone, la normale a media 0,80 misura **91,8%** e a 0,85 misura 86,8%: la soglia del 90% di SC-002 non viene attraversata a 0,80 ma **fra 0,80 e 0,85**. La normale troncata **passa** il criterio che si riteneva la escludesse. Stabilità: su tre semi diversi il valore a media 0,80 è 91,8% / 91,7% / 91,7%, e su quattro ereditabilità fra 0,22 e 0,55 resta fra 92,5% e 92,7%, quindi non è un artefatto di un seme né di un'ereditabilità.

Se avessi accettato la premessa avrei ratificato la decisione giusta con una motivazione falsa — che è esattamente il difetto che questo work item corregge altrove, e che nel gate di fase 2 si è ripetuto cinque volte.

**Ma la prima autocritica trova anche il vero criterio.** A media 0,80 la normale supera SC-002 mentre inchioda **l'8,23% della popolazione esattamente su 1,0**: un carattere dichiarato continuo diventa, per un dodicesimo della popolazione, una costante; e la media realizzata scivola a 0,788 invece di 0,800, perché il troncamento taglia da un lato solo. SC-002 promuove un modello visibilmente rotto. È la stessa patologia che la spec ha già dovuto correggere due volte — un criterio che non fallisce dove il requisito è falso — e questa volta si presenta al centro della deliberazione.

C'è un secondo modo di rompere che non dipende dalla media. Al centro esatto, facendo crescere l'ampiezza dichiarata:

| ampiezza dichiarata | normale realizzata | massa sul bordo | logit realizzata |
|---|---|---|---|
| 0,15 | 99,3% | 0,07% | 99,5% |
| 0,20 | 98,1% | 1,11% | 99,5% |
| 0,25 | 94,9% | 4,31% | 99,6% |
| 0,30 | 90,2% | 8,80% | 99,7% |

La normale non può esprimere ampiezze che i template sono oggi liberi di dichiarare, e la degradazione è silenziosa: nessun errore, solo un numero che non è quello scritto.

### Passo 3 — Seconda autocritica: due dei costi dichiarati non esistono

La prima autocritica lascia il logit in vantaggio. La seconda deve chiedere se i suoi costi lo annullino. Il materiale di ricerca ne dichiarava tre; misurati, **due sono spuri**.

**L'attenuazione della pendenza osservata non è un costo del logit.** Il materiale la presentava come il baratto da accettare: sulla scala latente la regressione figlio-genitori recupera `h²` per costruzione, sulla scala osservata no. Vero, ma misurando la stessa pendenza per **entrambe** le famiglie:

| media | h² dichiarato | normale: pendenza osservata | logit: pendenza osservata |
|---|---|---|---|
| 0,50 | 0,55 | 0,5529 (100,5%) | 0,5518 (100,3%) |
| 0,65 | 0,55 | 0,5491 (99,8%) | 0,5437 (98,9%) |
| 0,80 | 0,55 | 0,5120 (93,1%) | 0,5059 (92,0%) |
| 0,80 | 0,30 | 0,2770 (92,3%) | 0,2725 (90,8%) |

L'attenuazione fuori centro è dell'ordine del 7-9% **in entrambe le famiglie**, con poco più di un punto di differenza. Non è la tassa del logit: è una proprietà di qualunque scala limitata, e la normale la paga quasi identica pur pagando **in più** il collasso di ampiezza e la massa di bordo. Il costo va dichiarato come limite del modello, non come prezzo di questa scelta.

**Il supporto aperto sopravvive alla doppia precisione, con margine.** L'obiezione seria al logit è che `expit` in virgola mobile restituisce esattamente 1,0 oltre una certa soglia, e allora "mai esattamente 0 o 1" sarebbe una dichiarazione falsa nel codice. Misurato: la saturazione comincia fra 36,7 e 37,0. Alla media d'era 0,50 i parametri latenti sono `μ = 0,0000`, `σ = 0,6578`, e servirebbero 55,8 deviazioni standard; a media 0,80 sono `μ = 1,6643`, `σ = 1,0307`, e ne servirebbero 34,0. In una simulazione reale su 40.000 agenti per quindici generazioni l'agente più lontano dista **4,25** deviazioni standard, e i saturati sono zero su 40.000 a entrambe le medie. Il margine è di circa trenta deviazioni standard: la proprietà regge, e adesso è dichiarabile con la sua misura invece che per fede.

**L'accoppiamento assortativo non discrimina, e non fa quel che ci si aspetta.** Entrambe le famiglie poggiano su `Var(midparent) = V/2`, che richiede genitori scorrelati; FR-013 avverte che riparare l'istruzione risveglierà l'omogamia. Misurato nel caso peggiore possibile — ordinamento perfetto degli accoppiamenti sul tratto trasmesso stesso:

> **SUPERATO (2026-08-11, fase 2.4).** La frase che seguiva — «che in Epocha non può accadere perché il punteggio di omogamia pesa classe, istruzione, età e sentimento e non i tratti ereditabili» — è **falsa**. `couple.py:87-88` legge `education_level` e `couple.py:103` lo pesa con `w_edu` fino a 0,40, e l'istruzione **è** un carattere trasmesso: `_regress_education_level` delega a `inherit_trait` con `ρ` al posto di `h²`. L'omogamia ordina direttamente sul carattere trasmesso. Il caso che questo passaggio escludeva è esattamente quello che A4 esiste per trattare. Va inoltre letto sapendo che questa deliberazione concludeva per la scala logit, decisione poi ribaltata: la famiglia adottata è la normale troncata, quindi la tabella qui sotto confronta due famiglie di cui una non è in vigore. Le misure valide sull'accoppiamento assortativo sono quelle di A4, rigenerate sulla convenzione di copula gaussiana lì dichiarata.

| ordinamento | normale | logit |
|---|---|---|
| 0% | 99,8% | 99,9% |
| 25% | 104,2% | 102,5% |
| 50% | 101,3% | 99,4% |
| 100% | 110,0% | 108,5% |

L'effetto è **gonfiare** la varianza, non comprimerla, e al massimo di un decimo nel caso peggiore, in modo praticamente identico nelle due famiglie. FR-013 resta una limitazione da dichiarare, non un criterio di scelta, e la direzione del suo effetto va scritta correttamente: la spec oggi lascia intendere che l'assortativo minacci l'obiettivo di varianza dal basso, e non è così.

**Un costo reale resta, e va dichiarato.** L'ereditabilità dei template diventa una quantità di scala latente. I valori spediti provengono da studi su gemelli che stimano ereditabilità di scala osservata; la distinzione è priva di differenza misurabile per un carattere centrato — misurato sopra: 100,3% a media 0,50 — e diventa reale fuori centro, dove la scala osservata ne recupera il 92%. Va nel testo del whitepaper, non silenziosamente nel codice. Il secondo costo reale è la soluzione numerica dei parametri latenti per era e per tratto, che va risolta una volta al caricamento del template e messa in cache, non a ogni nascita.

### Decisione

**Si adotta la scala latente logit.** La genetica additiva si fa su scala logit; `[0,1]` resta la scala di presentazione, immagine dell'inversa logistica; il troncamento sparisce perché non serve più.

Con `μ` e `σ` i parametri latenti per era e per tratto, e `a` l'ereditabilità:

- due genitori noti: `x_f = μ + a·((x_m + x_p)/2 − μ) + e`, con `e ~ N(0, σ²(1 − a²/2))`
- un genitore noto: `x_f = μ + (a/2)·(x_g − μ) + e`, con `e ~ N(0, σ²(1 − a²/4))`
- nessun genitore noto: `x_f = μ + e`, con `e ~ N(0, σ²)`

poi `p_f = expit(x_f)`.

**La motivazione è una sola e va scritta per quella che è**: non che la normale fallisca SC-002 — non lo fa fino a media 0,85 — ma che la normale realizza l'ampiezza dichiarata **solo vicino al centro e solo per ampiezze strette**, degradando in silenzio altrove e accumulando massa su un bordo che un carattere continuo non dovrebbe avere. FR-002 chiede che l'ampiezza dichiarata sia quella realizzata; una famiglia la cui fedeltà dipende da dove cade la media non soddisfa quella proprietà, la soddisfa per caso nella configurazione odierna.

E la configurazione odierna non è quella di domani **dentro questo stesso work item**: FR-004 impone di risolvere le medie per era e per tratto, ed è precisamente ciò che porterà le medie fuori dal centro. Non si sta comprando generalità speculativa per un futuro che nessuno ha chiesto; si sta scegliendo la famiglia che regge lo spazio dei parametri che la fase 2.2 aprirà due passi più avanti.

**Risposta alla domanda che FR-002 pone esplicitamente** — se l'ampiezza dichiarata sia quella del rumore ambientale o quella fenotipica della popolazione: con questa forma è **l'ampiezza fenotipica della popolazione sulla scala osservata**, e i parametri latenti `(μ, σ)` sono ciò che si risolve numericamente per realizzarla. È la lettura che rende la dichiarazione verificabile su una popolazione, quindi quella che un criterio di accettazione può misurare.

**Sul vincolo `[0,1]` stesso**, per onestà: è una comodità di simulazione, non un fatto biologico, e la soluzione più pulita sarebbe toglierlo. È fuori ambito perché `[0,1]` è portante su `Agent.personality`, sui domini delle formule derivate, sul termine di merito della regola meritocratica e sulla superficie dei prompt. La scelta del logit **è quell'opzione in altra forma**: fa la genetica su scala non limitata e tiene `[0,1]` come presentazione.

### La trappola di implementazione, misurata

Se la variabile di codice contiene già `h²` — come `h2` oggi in `inherit_trait` — allora il termine `a²` delle formule sopra è `h2**2`, **non** `h2**4`. Scrivere `1 - h2**4/2` produce un kernel che gonfia la varianza. Misurato: **+5,92%** a `h2 = 0,55` e **+2,09%** a `h2 = 0,30`. Ne segue un vincolo sui test della fase 2.1: serve un'asserzione sulla **stazionarietà della varianza**, non sulla sola pendenza, perché la pendenza è corretta in entrambe le scritture e non distingue.

### Ciò che NON è verificato, e va chiuso prima del whitepaper

- **Falconer & Mackay (1996), pagine**: il libro non è stato aperto. RETTIFICA DEL 2026-08-11: questo punto attribuiva un titolo di capitolo a questa fonte, ed era sbagliato. Il progetto cita ora l'intervallo di capitoli 8-10 e **omette deliberatamente i titoli**, perché quattro round consecutivi del gate di fase 6 ne hanno colto uno sbagliato ciascuno, e una guardia strutturale ora lo impone meccanicamente. I numeri sono verificati sull'indice della quarta edizione, le pagine no, e A1 non vi poggia.
- **Il coefficiente `a/2` per il genitore singolo** non è stato ricondotto a una citazione primaria verbatim. È derivabile da `Cov(P_figlio, P_genitore) = ½·V_A` ed è confermato per via Monte Carlo, ma la derivazione non sostituisce la fonte.
- **de Villemereuil, Schielzeth, Nakagawa & Morrissey (2016)**, *General Methods for Evolutionary Quantitative Genetic Inference from Generalized Mixed Models*, Genetics 204(3):1281–1294, DOI 10.1534/genetics.115.186536: **verificato** contro la pagina dell'editore — titolo, autori, rivista, anno, volume, fascicolo e pagine coincidono, e l'articolo distingue davvero ereditabilità di scala latente da quella di scala osservata, riportando la seconda più bassa (0,111 contro 0,047 nell'esempio delle pecore di Soay).
- **Warton & Hui (2011)**, *The arcsine is asinine: the analysis of proportions in ecology*, Ecology 92(1):3–10: **verificato**, e raccomanda effettivamente il logit in alternativa all'arcoseno.
- **Lynch & Walsh (1998)**, **Fisher (1918)**, **Aitchison & Shen (1980)**: non verificate, quindi nulla è attribuito loro. L'assenza di momenti in forma chiusa per la logit-normale è stabilita per via computazionale in questo documento, non per citazione.

---

## Deliberazione 0.1b — L'orizzonte di pianificazione della migrazione

Stato del difetto, verificato sul codice: [migration.py:453](../../epocha/apps/demography/migration.py:453) calcola `(1 − u_j)·w_j − w_corrente − costo_distanza_j`, dove i primi due termini sono una moneta per tick e il terzo un conteggio di tick. Il modulo **dichiara già** l'incoerenza nel proprio docstring e registra il giudizio del round 1 dell'audit senza applicarlo. La spec ha verificato che quel giudizio non risolve: monetizzare il costo produce una moneta contro due tassi.

### La fonte risolve la questione, e il modulo cita quella sbagliata

La verifica delle fonti primarie ha prodotto un risultato che cambia il problema. **Harris & Todaro (1970)**, *American Economic Review* 60(1):126–142 — la fonte che [migration.py:374](../../epocha/apps/demography/migration.py:374) cita — **è un'uguaglianza di salario atteso a un solo periodo**: la sua condizione di equilibrio è `W_u · E_u/L_u = W_R`, e non contiene orizzonte, né sconto, né alcun termine di costo. Citare Harris-Todaro per un orizzonte di pianificazione sarebbe una misattribuzione netta.

**Todaro (1969)**, *American Economic Review* 59(1):138–148, è invece esattamente il modello che serve, e la sua struttura è quella che il difetto viola. Todaro lo ri-enuncia di propria mano nel 1980 (*Internal Migration in Developing Countries: A Survey*, in Easterlin (a cura di), *Population and Economic Change in Developing Countries*, NBER/University of Chicago Press, pp. 361–402), a p. 368, citando la nota 8 di p. 142 dell'originale:

> `V(0) = Σ_{t=0..n} [p(t)·Y_u(t) − Y_r(t)]·e^{−it} − C(0)`
>
> dove `n` è **il numero di periodi nell'orizzonte di pianificazione del migrante**, `i` **il tasso di sconto che riflette la sua preferenza temporale**, e **`C(0)` rappresenta il costo della migrazione**.

Il punto portante è la posizione di `C(0)`: **è un esborso una tantum al tempo zero, sottratto a un flusso scontato.** Non è compensato contro un tasso. La struttura corretta era nella fonte fin dall'inizio.

**Una precisazione che va fatta perché è comodo sbagliarla**: Todaro **non** definisce `n` come la vita lavorativa residua. Dice soltanto "il numero di periodi nell'orizzonte di pianificazione". La convenzione della vita lavorativa residua è di **Sjaastad (1962)**, *The Costs and Returns of Human Migration*, Journal of Political Economy 70(5, parte 2):80–93, che a p. 89 la rende concreta — pensionamento a 65-70 anni, quindi circa 45 anni residui per chi migra fra i 15 e i 19 e 40 per chi migra fra i 20 e i 24. Attribuire quella convenzione a Todaro sarebbe la stessa approssimazione che la User Story 2 esiste per correggere.

Sjaastad fornisce anche la definizione del costo, e specifica ciò che serve qui (p. 84): *"i primi costi non monetari da considerare sono i costi opportunità — i guadagni cui si rinuncia mentre si viaggia, si cerca e si impara un lavoro nuovo. Parte di questi guadagni mancati sarà funzione della distanza della migrazione."* La monetizzazione del costo distanza come reddito mancato — il giudizio del round 1 — è quindi **corretta come definizione del costo** e sbagliata solo su dove collocarlo: va contro un valore attuale, non contro un tasso. Sjaastad lo dice a p. 84 in termini quasi letterali, confrontando il costo con *"il valore attuale del differenziale di guadagno"*.

### La forma emendata

Con `a(H, r) = (1 − e^{−rH})/r` il fattore di annualità che Sjaastad calcola alla nota 29 di p. 92:

    E[guadagno_j] = a(H, r) · [ (1 − u_j)·w_j − w_corrente ] − costo_distanza_ticks_j · w_corrente

Tutti i termini sono moneta. Il primo è il valore attuale del differenziale di flusso sull'orizzonte; il secondo è l'esborso una tantum, che è `C(0)` di Todaro istanziato secondo la definizione di costo di Sjaastad.

**Taratura dell'aritmetica sulla fonte**: con `r = 0,10` annuo e orizzonti di 45 e 40 anni, `a` vale 9,89 e 9,82 per unità di reddito annuo — esattamente i due valori che Sjaastad stampa a p. 89. Il calcolo è quindi verificato contro la fonte e non solo contro se stesso. (Si noti, per completezza, che la fonte stampa 9,89 a p. 89 e 9,90 alla nota 29 per lo stesso integrale a 45 anni: è un'incoerenza di arrotondamento dell'originale, riportata anziché appianata.)

### I due parametri, e perché uno solo è tarabile

`H` **è derivato, non libero**: la convenzione di Sjaastad è la vita lavorativa residua, e va istanziata sull'età dell'agente anziché fissata a un numero. Questo soddisfa l'obbligo di FR-006, che vieta esplicitamente di trattare l'orizzonte come parametro libero da nominare.

`r` **è tarabile e va dichiarato tale.** Sjaastad usa il 10% annuo e lo enuncia come **assunzione**, non come stima: a p. 92 scrive che il tasso "è assunto" al 10%, alla nota 23 di p. 90 lavora un esempio a tasso inferiore, e alla nota 26 di p. 91 avverte che il tasso appropriato "può essere molto alto" per imperfezioni del mercato dei capitali. Todaro non fornisce alcun valore numerico né per `i` né per `n`, in nessuna delle due esposizioni: chi cita "il tasso di sconto di Todaro" lo sta inventando. Si dichiara quindi `r` parametro di progetto tarabile, ancorato al 10% annuo di Sjaastad con la citazione della sua natura di assunzione.

### L'effetto sulla soglia migratoria, misurato — ed è drastico

Lo scenario di accettazione 2 della User Story 3 richiede che l'effetto della scelta sulla soglia sia dichiarato. Con cadenza di tick giornaliera, `a` espresso in tick e il differenziale di flusso dell'esempio della Sezione 6 — `(1 − 0,08)·90 − 78 = +4,8` LVR/tick:

| orizzonte | `a` in tick | valore attuale del guadagno | costo distanza di pareggio, in tick |
|---|---|---|---|
| 30 tick | 30,0 | 143 | 1,8 |
| 1 anno | 347 | 1.667 | 21,4 |
| 10 anni | 2.307 | 11.075 | 142,0 |
| 40 anni | 3.583 | 17.199 | **220,5** |

Oggi la formula non corretta annulla quel guadagno a un costo distanza di **4,8 tick**, e il design spedisce costi di 0, 3 e 5 tick. Sotto l'orizzonte di Sjaastad il pareggio si sposta a 220 tick: **il costo distanza cessa di fatto di mordere**, e la soglia migratoria si allarga di circa un fattore quarantacinque.

È una conseguenza del modello citato, non un errore di implementazione, ed è economicamente corretta: un viaggio di tre giorni è trascurabile contro quarant'anni di differenziale di reddito. **Va però dichiarata come limite, e la fonte stessa lo fa**: Sjaastad osserva a p. 84 che i costi marginali per miglio "dovrebbero essere davvero alti" per conciliare l'effetto negativo della distanza osservato nei dati con il valore attuale del differenziale, "anche a tassi di sconto molto elevati". Il modello di investimento **sotto-predice l'attrito della distanza, e il suo autore lo scrive.** La spec emendata deve riportare questa limitazione, non nasconderla dietro il bilanciamento dimensionale riparato.

### Conseguenze da propagare

Il blocco informativo di migrazione cambia unità: da LVR/tick a LVR di valore attuale. L'esempio numerico "+4,8 LVR/tick" della Sezione 6 non è più il valore prodotto e va riscritto, insieme alla dichiarazione della sua unità. La citazione di [migration.py:374](../../epocha/apps/demography/migration.py:374) va corretta: Harris & Todaro (1970) resta la fonte del **salario atteso pesato per la probabilità di impiego**, mentre la struttura a valore attuale è di Todaro (1969) e la definizione del costo di Sjaastad (1962). E SC-005 resta soddisfatto: `a(H, r)` è adimensionale rispetto alla valuta e il costo è monetizzato, quindi la decisione resta invariante alla scala della valuta.

## Deliberazione 0.1c — L'orizzonte di sussistenza

### Che cosa fa oggi il codice, verificato sui due consumatori

La riga 153 del design prescrive `agent.wealth < N * subsistence_threshold` e definisce `N` in due modi incompatibili nella stessa frase: la glossa lo dice "il numero di tick che l'agente può sopravvivere con i risparmi attuali", il che renderebbe la condizione `ricchezza < ricchezza`; la parentesi lo dice parametro globale con default 30.

I due consumatori, letti nel codice:

- **Fuga d'emergenza**, [migration.py:1122](../../epocha/apps/demography/migration.py:1122): `if agent.wealth >= subsistence_threshold: return` — nessun `N`, cioè `N = 1`. Ma la condizione di fuga **non è quella sola**: ne servono tre simultanee, e la seconda è `consecutive_ticks_under_subsistence >= flight_trigger_ticks`, con `flight_trigger_ticks` a 30.
- **Fertilità**, [fertility.py:107](../../epocha/apps/demography/fertility.py:107): `wealth_signal = log(max(wealth / max(subsistence, 1e-6), 0.1))` — nessuna soglia affatto: il rapporto entra come segnale continuo nella modulazione alla Becker.

### La diagnosi che nessuna stesura aveva formulato

La riga 153 non è incoerente perché sceglie male fra due valori di `N`. **È incoerente perché confonde una grandezza con una soglia su quella grandezza.** Il rapporto `ricchezza / soglia_di_sussistenza` è un numero puro che vale esattamente quanto la glossa descrive: il numero di tick di sussistenza che i risparmi coprono. Quello è l'**orizzonte di sopravvivenza**, ed è una quantità, non un parametro. La parentesi cerca invece di farne una soglia globale, e le due cose non possono stare nello stesso simbolo.

Vista così, i due consumatori **applicano già la stessa convenzione**, e non se ne erano accorti: la fertilità usa l'orizzonte in forma continua, la fuga vi applica una soglia a 1. Ciò che manca non è l'allineamento, è la definizione che li accomuna.

### La scelta fra test di fame e test di risparmio precauzionale

FR-008 chiede di scegliere esplicitamente. **Si sceglie il test di fame**, e le ragioni sono tre.

La prima è che l'orizzonte, nella condizione di fuga, **c'è già e sta altrove**: `flight_trigger_ticks` a 30 impone che la destituzione duri un mese. Un agente sotto la soglia per un tick solo non fugge. Mettere `N = 30` anche sul livello significherebbe scrivere "sotto un mese di risparmi, per un mese di fila" — lo stesso mese contato due volte, con la seconda occorrenza priva di fonte.

La seconda è di attribuzione. Il risparmio precauzionale è un modello di **consumo e accumulazione** — è la letteratura del buffer stock — non un modello di innesco migratorio. La condizione di fuga è citata a O'Rourke (1994) e a Simon (1955): il secondo fornisce il satisficing, cioè il fatto che si agisca al superamento di una soglia di insoddisfazione anziché ottimizzando, e non fissa il livello di quella soglia; nessuno dei due fornisce una soglia di scorta precauzionale. Importare qui un meccanismo dalla letteratura sbagliata sarebbe la stessa attribuzione approssimativa che la User Story 2 esiste per correggere.

La terza è che `wealth < subsistence_threshold` ha un significato letterale e verificabile: l'agente non può permettersi gli essenziali **nemmeno per un tick**. È destituzione osservata, non prevista, ed è ciò che l'espressione "fuga d'emergenza" denota.

**Questa conclusione contraddice la prosa della User Story 5**, che presenta come difetto il fatto che "un agente con trenta tick di risparmi è trattato come uno che ne ha uno solo". Sotto un test di fame quel trattamento è corretto e voluto: chi ha trenta tick di risparmi non sta morendo di fame. Il requisito però — FR-008 — è formulato neutralmente e impone di scegliere, non di scegliere il precauzionale; la scelta qui è motivata e la motivazione è scritta. La prosa della user story va letta come motivazione del gate, non come suo esito predeterminato.

### La riscrittura della riga 153

> L'**orizzonte di sopravvivenza** di un agente è il rapporto `agent.wealth / subsistence_threshold(simulation, zone)`, un numero puro che esprime quanti tick di sussistenza i risparmi correnti coprono. È una grandezza derivata, non un parametro: non esiste alcun `N` globale. Ogni consumatore che ne richieda una soglia la dichiara per sé, con la propria fonte. La condizione di fuga d'emergenza vi applica la soglia **1** — destituzione osservata, incapacità di coprire anche un solo tick — e affida la persistenza al proprio `flight_trigger_ticks`, che vale 30 tick; la modulazione della fertilità non applica soglia e consuma l'orizzonte in forma logaritmica continua.

### Conseguenza sul codice, dichiarata perché è scomoda

**Nessuno dei due consumatori cambia.** La correzione di FR-008 è interamente nella spec di design e nella documentazione dei due moduli, che oggi non nominano l'orizzonte come grandezza comune. Un esito "nessuna riga di codice cambia" merita sospetto e va detto per intero anziché nascosto: la verifica è che i due comportamenti misurati corrispondano alla convenzione appena scritta, non che la convenzione sia stata piegata su ciò che il codice già fa. Le due letture del codice sopra sono la prova, e sono citate a riga.

### **SC-014 non discrimina sotto questa scelta, ed è un rilievo per il gate**

SC-014 chiede che "due agenti con pari ricchezza corrente ma orizzonti di sopravvivenza diversi ricevano esiti diversi", affermando che oggi ricevono lo stesso. **Verificato: non è vero.** La soglia di sussistenza è calcolata per zona ([migration.py:1118](../../epocha/apps/demography/migration.py:1118)), quindi due agenti con pari ricchezza in zone dai prezzi diversi hanno già oggi orizzonti diversi e possono già oggi ricevere esiti diversi — basta che i loro orizzonti stiano a cavallo di 1.

Il criterio fallisce oggi **solo sotto la lettura precauzionale**, quella in cui "orizzonte diverso" significa due agenti entrambi sopra la soglia di fame ma con scorte diverse. SC-014 non è quindi un criterio neutro che misura una proprietà: **presuppone l'esito della deliberazione che dovrebbe verificare**, ed è la quinta occorrenza in questo work item della stessa patologia — un criterio che non fallisce dove il requisito è falso, qui aggravata dal fatto che non fallisce perché dà per deciso ciò che è in discussione.

Il rilievo va al gate di fase 0, che deve ruolare su una delle due: riformulare SC-014 perché misuri la proprietà effettivamente scelta — che i due consumatori dichiarino e applichino la stessa definizione di orizzonte, verificabile per mutazione cambiando la definizione in un consumatore solo — oppure respingere la scelta del test di fame con una motivazione scientifica, non con l'esistenza del criterio. **Non si riscrive un criterio per farlo passare**: si dichiara che non discrimina e si lascia decidere.

---

## Deliberazione 0.3 — L'attribuzione a Chetty, verificata prima di diventare bersaglio

FR-009 impone di verificare l'attribuzione **prima** che 0,35 diventi il bersaglio dell'allineamento dei template. La verifica è stata fatta sui testi completi, non sugli abstract, ed è il risultato più grave di tutta la fase 0.

### Il fatto

**L'attribuzione della riga 721 — `modern: 0.35 (Chetty et al. 2014)` — non ha fonte. Chetty et al. (2014) non riporta alcun coefficiente di persistenza intergenerazionale dell'istruzione, di nessun valore.**

Ci sono due lavori distinti che rispondono a "Chetty et al. (2014)", e la spec non li distingue mai:

- Chetty, Hendren, Kline & Saez, *Where is the Land of Opportunity? The Geography of Intergenerational Mobility in the United States*, **Quarterly Journal of Economics** 129(4):1553–1623, DOI 10.1093/qje/qju022;
- Chetty, Hendren, Kline, Saez & Turner, *Is the United States Still a Land of Opportunity? Recent Trends in Intergenerational Mobility*, **American Economic Review** 104(5):141–147, DOI 10.1257/aer.104.5.141.

Il testo completo di entrambi è stato estratto e cercato. Nel primo l'istruzione dei genitori compare **solo** come strumento di imputazione del reddito nel lavoro di Mazumder, mai come regressore di un'istruzione filiale; la stringa "0,35" vi compare per tutt'altro, come pendenza rank-rank di robustezza a quindici anni di reddito. Il secondo misura un *college attendance gradient* che è per costruzione un gradiente rispetto al **rango di reddito** dei genitori, non alla loro istruzione, e i valori che riporta sono 74,5% e 69,2%. Non esiste alcun 0,35 di persistenza dell'istruzione da nessuna parte.

### Il secondo difetto, nella stessa citazione

La riga 709 attribuisce a Chetty un intervallo di elasticità del reddito "0,3–0,5". **Anche questo è scorretto, e in modo istruttivo**: non è l'intervallo che il paper riporta — i suoi valori misurati sono 0,344 di base, 0,452 restringendo a p10–p90, 0,618 e 0,413 sotto due ricodifiche dei redditi nulli, e da 0,264 a 0,697 fra sottocampioni — e soprattutto **la tesi di quella sezione è che l'elasticità è inaffidabile**, perché la distribuzione dei redditi non è ben approssimata da una log-normale bivariata. Citare Chetty come autorità per un intervallo ordinato di elasticità **inverte la sua conclusione**. La grandezza che quel paper effettivamente raccomanda è la pendenza rank-rank, 0,341.

Anche la metà Solon (1999) di quella citazione resta **non verificata**: il capitolo è dietro paywall e non è stato letto, quindi non è confermato che enunci l'intervallo 0,3–0,5. Il capitolo successore, Black & Devereux (2011), riporta una banda di consenso intorno a 0,4–0,6, non 0,3–0,5.

### Che cosa si può mettere al suo posto

Per un coefficiente di regressione dell'istruzione filiale su quella dei genitori — che è la forma funzionale del modello — la fonte difendibile è **Black & Devereux (2011)**, *Recent Developments in Intergenerational Mobility*, Handbook of Labor Economics 4B, cap. 16, pp. 1487–1541, la cui Tabella 3 riporta coefficienti OLS su anni di scolarità per campioni statunitensi: Sacerdote (2000) padre 0,28 e madre 0,35; Plug (2004) padre 0,39 e madre 0,54, che controllando congiuntamente entrambi i genitori diventano 0,30 e 0,30.

**Una trappola va nominata perché è vistosa**: il coefficiente materno di Sacerdote vale 0,35, esattamente il numero orfano della spec. È un coefficiente **a genitore singolo**, non su valore medio dei genitori, e non è Chetty. Non si deve lasciare che 0,35 sopravviva trovandogli una casa nuova dopo il fatto: sarebbe la stessa attribuzione a posteriori che questo work item esiste per eliminare.

Hertz et al. (2008), *The Inheritance of Educational Inequality*, B.E. Journal of Economic Analysis & Policy 7(2) art. 10, DOI 10.2202/1935-1682.1775, riporta una **correlazione** media globale stabile intorno a 0,4 su cinquant'anni — verificata solo a livello di abstract, il testo completo non è stato raggiunto. Va usata con una cautela che la letteratura stessa segnala: correlazione e coefficiente di regressione sono grandezze diverse e hanno avuto andamenti diversi nel tempo, quindi la 0,4 di Hertz è utilizzabile per il `ρ` del modello **solo se l'istruzione è standardizzata**, e altrimenti è uno scambio di categoria.

### Conseguenza su FR-009 e SC-007

Il bersaglio dell'allineamento **non è 0,35**. FR-009 va soddisfatto nell'altro modo che esso stesso prevede: dichiarando la divergenza con la sua ragione. Nello specifico, la riga 721 va spogliata dell'attribuzione inventata, e il valore dell'era moderna va o ricondotto a Black & Devereux (2011) con la forma funzionale dichiarata, o dichiarato euristica tarabile.

E c'è un residuo che nessuna stesura aveva sollevato: **i valori pre-industriale 0,5, industriale 0,42 e sci-fi 0,25 non portano alcuna citazione nella spec di design**. Sono euristiche non documentate, e sotto la regola del progetto vanno dichiarate tali con la loro giustificazione. Il difetto di FR-009 è quindi più esteso di come la User Story 6 lo descriveva: non sono tre template divergenti da un bersaglio corretto, è un bersaglio inesistente e quattro valori su quattro senza fonte verificata.

---

## Deliberazione 0.2 — Le magnitudini dei parametri nuovi

> **AVVERTENZA — DUE CONCLUSIONI DI QUESTA DELIBERAZIONE SONO STATE RIBALTATE.** Il testo che segue porta l'istruzione sulla scala latente logit e dichiara l'ampiezza di Clark **derivata** dall'identità, cioè `σ_rank·√(1 − 0,7²)`. L'emendamento rovescia entrambe: l'istruzione resta sulla **famiglia normale con troncamento** (A1, A3), e `σ_clark` **non si legge dall'identità ma si risolve numericamente**, perché arrotondamento e clamp sono non lineari — leggere la formula dà il 102,26% del bersaglio contro la radice vera 0,68896. Anche l'inquadramento di `b = 0,7` è superato: A3 stabilisce che `θ` non è calcolabile in questo modello, quindi `b` è euristica dichiarata e **non attribuita a Clark**, invece che una deviazione da dichiarare.
>
> **Una terza affermazione è semplicemente falsa, e va corretta qui perché l'emendamento non la contiene e quindi non può prevalerci sopra.** Il testo chiude sostenendo che "la correlazione realizzata non scende mai sotto 0,7 ... è un pavimento, non un tetto". Risolta per via esatta, la correlazione di rango genitore-figlio **scende sotto 0,7 a `σ ≈ 0,49`** e vale **0,683** alla radice adottata `σ_clark = 0,688956`. Non c'è alcun pavimento a 0,7: la correlazione decresce monotonicamente al crescere dell'innovazione, e l'argomento "un'innovazione ampia non annega il segnale della fonte" non regge nella forma in cui è scritto. Ciò che regge è che alla radice adottata la correlazione resta alta, 0,683, cioè vicina al peso di persistenza — ma è una constatazione, non un limite garantito.
>
> Le **magnitudini** che questa deliberazione fissa restano valide e sono quelle che A2 adotta. Dove il testo diverge dall'emendamento, prevale l'emendamento.


Il piano chiedeva di fissare due ampiezze di innovazione, quella dell'istruzione e quella di Clark, prendendo a modello `_BECKER_TOMES_RANK_NOISE_SD`, che è dichiarato parametro tarabile non sorgente. **Nessuna delle due si risolve così, e per ragioni diverse.**

**L'istruzione non ha un parametro nuovo.** La decisione 0.1a la porta sulla scala latente logit insieme ai tratti, e allora l'ampiezza dell'innovazione è determinata dall'identità di varianza: `σ_edu·√(1 − ρ²/2)`. Ciò che va dichiarato non è un rumore ma `σ_edu`, cioè la **dispersione stazionaria dell'istruzione nella popolazione**, che è una grandezza osservabile e va in `era_noise` come per ogni altro carattere. Nessun grado di libertà nuovo.

**Clark non è tarabile, contrariamente a quanto la prima stesura dell'emendamento aveva scritto.** Il precedente di Becker-Tomes vale perché Solon e Chetty pubblicano un'elasticità senza termine di varianza residua. **Clark il termine lo pubblica**: il modello formale in Clark, Cummins, Hao & Diaz Vidal è `x_t = b·x_{t-1} + e_t` con osservazione `y_t = x_t + u_t`, e la stessa fonte enuncia `σ² = b²σ² + σ²_e`. L'ampiezza è quindi `σ_rank·√(1 − 0,7²) = σ_rank·0,7141`, derivata.

Questo cambia anche la natura del difetto. L'implementazione deterministica **non è una semplificazione del modello di Clark**: è un modello con il comportamento asintotico opposto, che spinge ogni lignaggio verso la media azzerando la varianza trasversale — nessuna mobilità e nessuna stratificazione — mentre Clark tiene la varianza costante e produce rimescolamento continuo. La bassa mobilità di Clark è regressione lenta, non congelamento.

**Due cose da non scrivere.** L'intervallo del libro è **0,7–0,9**, non 0,7–0,8, che è il riassunto dei recensori. E 0,75 vale per lo **status latente**: una scala di classe a cinque ranghi è un indicatore osservabile singolo, per il quale Clark stesso riporta 0,15–0,65 sui guadagni, 0,3–0,65 sulla scolarità e 0,43 contro 0,74 sulla ricchezza inglese a seconda del metodo. Il peso 0,7 su un osservabile sovrastima la persistenza del fattore `θ` che Clark ha scritto un libro per identificare, e la deviazione va dichiarata anziché lasciata implicita.

**Misura, tarata sul difetto noto**: la regressione di Clark oggi produce mobilità **0,0000** e correlazione di rango genitore-figlio **1,0000** dalla seconda generazione, con due dei cinque ranghi vuoti — l'immobilità perfetta che SC-012 riporta. Ai valori candidati, su 40.000 agenti per dieci generazioni: 0,0467 di mobilità a σ 0,20 (correlazione 0,8936), 0,0845 a 0,25 (0,8150), 0,1404 a 0,30 (0,7624), 0,2617 a 0,40 (0,7137). Stabile su tre semi. **La correlazione realizzata non scende mai sotto 0,7**, che è il peso di persistenza: è un pavimento, non un tetto, quindi un'innovazione ampia non annega il segnale della fonte.

**Un avvertimento sull'aritmetica**: `σ_rank` va risolto sulla distribuzione realizzata **dopo** arrotondamento a etichette intere e clamp ai due estremi, non assumendo che la gaussiana latente li attraversi indenne — l'effetto è già documentato per `becker_tomes_elasticity_0.4`, dove il clamp accumula sui bordi la massa che cadrebbe fuori scala.

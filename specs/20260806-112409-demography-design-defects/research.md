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

**L'accoppiamento assortativo non discrimina, e non fa quel che ci si aspetta.** Entrambe le famiglie poggiano su `Var(midparent) = V/2`, che richiede genitori scorrelati; FR-013 avverte che riparare l'istruzione risveglierà l'omogamia. Misurato nel caso peggiore possibile — ordinamento perfetto degli accoppiamenti sul tratto trasmesso stesso, che in Epocha non può accadere perché il punteggio di omogamia pesa classe, istruzione, età e sentimento e non i tratti ereditabili:

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

- **Falconer & Mackay (1996), capitolo e pagine**: il libro non è stato aperto. Il modulo cita oggi il capitolo 8; la somiglianza fra parenti è materia del capitolo 10. La discrepanza va risolta su una copia del testo prima che la citazione entri nel whitepaper.
- **Il coefficiente `a/2` per il genitore singolo** non è stato ricondotto a una citazione primaria verbatim. È derivabile da `Cov(P_figlio, P_genitore) = ½·V_A` ed è confermato per via Monte Carlo, ma la derivazione non sostituisce la fonte.
- **de Villemereuil, Schielzeth, Nakagawa & Morrissey (2016)**, *General Methods for Evolutionary Quantitative Genetic Inference from Generalized Mixed Models*, Genetics 204(3):1281–1294, DOI 10.1534/genetics.115.186536: **verificato** contro la pagina dell'editore — titolo, autori, rivista, anno, volume, fascicolo e pagine coincidono, e l'articolo distingue davvero ereditabilità di scala latente da quella di scala osservata, riportando la seconda più bassa (0,111 contro 0,047 nell'esempio delle pecore di Soay).
- **Warton & Hui (2011)**, *The arcsine is asinine: the analysis of proportions in ecology*, Ecology 92(1):3–10: **verificato**, e raccomanda effettivamente il logit in alternativa all'arcoseno.
- **Lynch & Walsh (1998)**, **Fisher (1918)**, **Aitchison & Shen (1980)**: non verificate, quindi nulla è attribuito loro. L'assenza di momenti in forma chiusa per la logit-normale è stabilita per via computazionale in questo documento, non per citazione.

---

## Deliberazione 0.1b — L'orizzonte di pianificazione della migrazione

*In corso. La verifica delle fonti primarie (Todaro 1969, Harris & Todaro 1970, Sjaastad 1962) è in esecuzione; la deliberazione in tre passi si svolge sul suo esito.*

Stato del difetto, verificato sul codice: [migration.py:453](../../epocha/apps/demography/migration.py:453) calcola `(1 − u_j)·w_j − w_corrente − costo_distanza_j`, dove i primi due termini sono una moneta per tick e il terzo un conteggio di tick. Il modulo **dichiara già** l'incoerenza nel proprio docstring e registra il giudizio del round 1 dell'audit senza applicarlo. La spec di questo work item ha verificato che quel giudizio non risolve: monetizzare il costo produce una moneta contro due tassi.

## Deliberazione 0.1c — L'orizzonte di sussistenza

*Da svolgere. La riga 153 del design va riscritta comunque, perché la sua glossa e la sua parentesi definiscono due oggetti incompatibili.*

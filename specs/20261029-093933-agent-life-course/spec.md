# Feature Specification: comportamento degli agenti lungo il corso della vita

**Feature Branch**: `20261029-093933-agent-life-course`

**Created**: 2026-10-29

**Status**: Draft (fase 2). Perimetro ridotto dalla decisione D-29-5 della Trinità. Audit avversariale **CONVERGED al round 8** (2026-10-29); emendata dopo il piano con la decisione D-29-35 (sezione «Chiarimenti»), con l'audit del delta **CONVERGED al round 2** in `checklists/delta-audit-d29-35.md`; resta l'approvazione del gate di fase 2 da parte della Trinità sotto la deroga D-29-3, con rapporto all'utente.

**Input**: User description: "Comportamento degli agenti in base all'età lungo tutto il corso della vita, dal neonato all'anziano"

**Contratto API**: **contratto invariato**. Nessuna rotta, nessun campo di risposta, nessun valore di enum, nessuno stato HTTP cambia; lo stadio di vita non è esposto dalle API (FR-014).

**Modello dati**: nessun campo e nessuna migrazione nuovi; nessuna chiave nuova nei template d'era.

## Perché questo work item esiste

Il Plan 4 della demografia (`20260826-144432-demography-plan4-wiring`, non ancora mergiato in `develop` al 2026-10-29) fa nascere agenti dentro la run e dà loro un'età canonica, `demography.orchestrator.age_in_years`, calcolata su `birth_tick`. Il resto del simulatore però non legge quell'età. Ho verificato sul ramo del Plan 4 tre conseguenze concrete:

1. **Il ciclo decisionale fa deliberare i neonati come adulti.** Il percorso sequenziale (`simulation/engine.py`, `SimulationEngine.run_tick`, passo 2) e il percorso Celery (`simulation/tasks.py`, `run_simulation_loop`, che costruisce un chord di `process_agent_turn` per ogni agente vivo) chiamano l'LLM per **ogni** agente vivo, senza filtro d'età. Il vocabolario d'azione di `agents/decision.py` (`_BASE_ACTIONS`) offre a un neonato `borrow`, `buy_property`, `move_to` e `crime`.
2. **L'economia fa produrre i neonati.** L'orchestratore delle nascite crea il neonato con `role="child"`; `economy/production.py` (`compute_agent_output`) non trova `child` nella mappa dei ruoli e ricade nel ramo di fallback, che dà a ogni ruolo non mappato un input di lavoro `skill_weight = 0.8` nella funzione CES. Un neonato produce quindi **esattamente quanto un adulto con un ruolo non mappato**.
3. **La chat parla con un neonato come con un adulto.** I tre costruttori di prompt della chat, la chat privata e la chat di gruppo di `dashboard/views.py` e `chat/consumers.py`, danno all'LLM solo nome e ruolo; un agente di dieci mesi ha risposto a un abbraccio come un adulto. Il prompt della dashboard vieta inoltre le didascalie non verbali, che sono l'unico registro possibile per un lattante; quello di `chat/consumers.py` non ha regole di conversazione.

Le tre conseguenze descrivono il ramo del Plan 4 com'era quando ho scritto la prima stesura. Oggi il Plan 4 porta la guardia D-29-4: il merge `c1e8569` esclude dal ciclo decisionale chi è sotto `migration.adulthood_age` e dichiara l'età nella chat privata; il commit `02a1d47` la aggiunge alla chat di gruppo; il commit `430dfa6` sposta `describe_speaker` nella demografia e la aggiunge alla chat WebSocket. Sulla testa del Plan 4 tutti e tre i prompt di chat aprono quindi con `describe_speaker`, che dichiara l'età ma senza un registro per età. La sezione «Relazione con la guardia del Plan 4» dice che cosa questa spec ne cambia.

## Perimetro dopo la decisione D-29-5

Il 2026-10-29 la Trinità ha deciso le domande aperte della prima stesura (Domenico, sotto la deroga dell'utente D-29-3; registro `decisioni.md` del 2026-10-29, voce D-29-5, marcata DECISIONE-RIFATTA). **Questa spec consegna età e stadi di vita**: niente deliberazione né produzione sotto i 10 anni, capacità ristrette per l'adolescente con la sanificazione dell'azione prima del `DecisionLog`, il frammento d'età condiviso dai tre prompt di chat (chat privata e chat di gruppo della dashboard, chat WebSocket; perimetro esteso alla chat di gruppo dalla decisione D-29-35), e una sola funzione di selezione degli agenti deliberanti con il filtro d'età in database e un numero di query costante.

Tre parti della prima stesura **escono** e vanno in work item separati:

- **Formazione delle coppie a regole e limite dei protagonisti** (domande T-0 e T-1 della prima stesura). Dopo l'inizializzazione le coppie nascono solo da intenti LLM (`run_couple_formation_step` chiama `resolve_pair_bond_intents`, che legge i `DecisionLog`), e tre template su cinque richiedono la coppia per nascere: un limite K agli agenti che deliberano farebbe crollare la natalità oltre K. Il meccanismo K, la scelta dei protagonisti e la formazione delle coppie secondo Coale e McNeil (1972) sul `stable_matching` esistente vanno insieme in un work item prerequisito. **È una decisione rifatta contro la mia raccomandazione**: io proponevo di consegnare qui il meccanismo K spento per impostazione predefinita; Domenico ha obiettato che un meccanismo spedito spento è una configurazione che nessuno imposta, e che K deve uscire solo insieme alle coppie a regole.
- **Chiavi d'era per l'età d'inizio del lavoro e per la pensione** (T-2 e T-3): work item «chiavi del lavoro per era». Qui resta solo la produzione nulla sotto i 10 anni come euristica dichiarata; fra 10 anni e l'età adulta il comportamento resta quello di oggi.
- Per la **soglia adulta** (T-4) resta una sola soglia, `migration.adulthood_age`, con la ricerca di una fonte per era fatta prima della chiusura del gate; l'esito è nella sezione «La soglia adulta per era».

Il vincolo di scala dell'utente (mondi di milioni e miliardi di agenti, LLM riservato a un sottoinsieme limitato) **non è soddisfatto da questa spec** e la spec non lo afferma: il ciclo decisionale costa al più K chiamate LLM per tick, con K = `max_protagonists` introdotto dal work item prerequisito, ma questa spec non misura né dimostra quel limite. Questa spec garantisce solo che il comportamento per età non aggiunga costo per agente, e che la selezione degli agenti deliberanti costi un numero di query costante.

## Fondamenti scientifici

Ogni regola di questa spec porta una fonte che ho verificato il 2026-10-29; dove la verifica è passata solo da fonti secondarie o è mancata, lo dico. Le fonti scartate restano elencate, perché un audit deve poter vedere ciò che ho rifiutato.

| Fonte | Affermazione specifica usata | Stato della verifica | Dove pesa |
|---|---|---|---|
| Elder, G. H. Jr. (1998). *The Life Course as Developmental Theory*. Child Development, 69(1), 1-12 (PMID 9499552) | Le vite sono plasmate da un contesto storico in mutamento e lo sviluppo va letto sull'intero arco di vita | Verificate citazione e abstract su PubMed; l'elenco dei principi viene da fonti secondarie che non concordano sul numero | Inquadramento: perché la soglia adulta dipende dall'era |
| Organizzazione Mondiale della Sanità, *Adolescent health and development*: adolescenti come «individuals in the 10-19 years age group» | Inizio dell'adolescenza a 10 anni | Verificata sulla pagina OMS | Soglia di 10 anni |
| Sawyer, S. M., Azzopardi, P. S., Wickremarathne, D., Patton, G. C. (2018). *The age of adolescence*. Lancet Child & Adolescent Health, 2(3), 223-228 | Propone 10-24 anni e conferma l'inizio a 10 | Verificata (abstract) | Conferma della soglia di 10 anni |
| Zubler, J. M. et al. (2022). *Evidence-Informed Milestones for Developmental Surveillance Tools*. Pediatrics, 149(3), e2021052138 | Tappe raggiunte da almeno il 75% dei bambini: 9 mesi lallazione di sillabe ripetute; 12 mesi chiama un genitore con un nome; 15 mesi una o due parole oltre «mamma» e «papà»; 18 mesi almeno tre parole; 24 mesi due parole insieme; 30 mesi circa 50 parole; 4 anni frasi di almeno quattro parole | Verificata sul testo (manoscritto CDC, tabella delle tappe linguistiche) | Solo le bande linguistiche della chat fino a 4 anni (FR-009) |
| Rogers, A., Castro, L. J. (1981). *Model Migration Schedules*. IIASA RR-81-30 | Il profilo per età della migrazione ha una componente pre-lavorativa decrescente legata ai genitori, con uno scarto d'età parentale; la forma originale a 11 parametri include un picco di pensionamento, quella a 13 una risalita post-pensionamento | Verificata tramite la pagina IUSSP; il PDF IIASA primario non era raggiungibile (filtro anti-bot). L'impatto è contenuto: qui giustifica solo una regola qualitativa | FR-005 (`move_to` escluso sotto l'età adulta) |
| Family Law Reform Act 1969 (Inghilterra e Galles), sez. 1(1) | La maggiore età si raggiunge a 18 anni «instead of on attaining the age of twenty-one» | Verificata su legislation.gov.uk (estensione della sezione: Inghilterra e Galles; la pagina non riporta la data di entrata in vigore, che non ho verificato) | Fonte statutaria del 18 e prova che prima della sezione la maggiore età era 21 (T-4) |
| Blackstone, W. (1765). *Commentaries on the Laws of England*, libro I, cap. 17 «Of Guardian and Ward» | «So that full age in male or female, is twenty one years» | Verificata sul testo primario (Avalon Project, Yale) | La maggiore età inglese del Settecento era 21, contro il 16 del template `pre_industrial_christian` (T-4) |
| Convenzione ONU sui diritti dell'infanzia (1989), art. 1 | Ai fini della Convenzione è bambino ogni essere umano sotto i 18 anni, salvo che la legge applicabile fissi prima la maggiore età | Verificata sul testo UNICEF | Solo contesto: definisce «bambino» per la Convenzione, non fissa una maggiore età |
| *Bulugh* e *rushd* nel diritto islamico | Nella scuola sciita ja'fari l'opinione maggioritaria è 15 anni lunari per i maschi e 9 per le femmine, con giuristi che indicano età diverse; per compiere atti patrimoniali serve inoltre il *rushd*, capacità mentale distinta dalla pubertà | Verificata **solo su una fonte secondaria** (WikiShia); le età delle scuole sunnite non le ho verificate | Solo come motivo per dichiarare euristica la soglia del template islamico (T-4) |
| Humphries, J. (2010). *Childhood and Child Labour in the British Industrial Revolution*. Cambridge University Press | Gli anni 1790-1850 mostrano un'impennata del lavoro minorile | Verificata solo l'affermazione qualitativa; l'età media d'inizio non l'ho verificata | Motivo per cui lo zero sotto i 10 anni è un'euristica |
| Nazioni Unite, Divisione Popolazione (comunicato SOC/4473, 1998) | Le persone anziane sono quelle di 60 anni e oltre | Verificata sul comunicato | Soglia dello stadio anziano, definito e non cablato |
| Steinberg (2008); Hirschi e Gottfredson (1983); Britt (1992); Costa (1998); Skirbekk (2004); Coale e McNeil (1972); ILOSTAT | Rischio adolescenziale, curva età-crimine, pensionamento, produttività in età anziana, primo matrimonio, età lavorativa | Verificate nella prima stesura (dettaglio nell'audit del round 1) | **Nessuna regola in questa spec**: servono ai work item separati e ai rinvii |
| Piaget (stadi cognitivi); WHO MGRS (2006) | — | Scartate: non sostengono alcuna regola del modello | Nessuna |

### Riferimenti con URL e data di lettura

Ho letto tutte le pagine elencate il 2026-10-29; dove ho letto solo una fonte secondaria lo scrivo.

| Fonte | URL consultato | Che cosa ho letto |
|---|---|---|
| Elder (1998) | https://pubmed.ncbi.nlm.nih.gov/9499552/ | Scheda e abstract |
| OMS, adolescenza | https://www.who.int/india/health-topics/adolescent-health-and-development | Pagina primaria |
| Sawyer et al. (2018) | https://eres.library.adelaide.edu.au/dspace/handle/2440/124427 | Scheda e abstract |
| Zubler et al. (2022), doi:10.1542/peds.2021-052138 | https://stacks.cdc.gov/view/cdc/122643 | Manoscritto completo |
| Rogers e Castro (1981) | https://demographicestimation.iussp.org/node/92 (secondaria); https://pure.iiasa.ac.at/1543 (primaria, non raggiungibile) | Pagina IUSSP |
| Convenzione ONU sui diritti dell'infanzia | https://www.unicef.org/child-rights-convention/convention-text | Art. 1 |
| Family Law Reform Act 1969 | https://www.legislation.gov.uk/ukpga/1969/46/section/1 | Sez. 1(1) |
| Blackstone (1765), libro I, cap. 17 | https://avalon.law.yale.edu/18th_century/blackstone_bk1ch17.asp | Testo primario del capitolo |
| *Bulugh* e *rushd* | https://en.wikishia.net/view/Bulugh | Voce enciclopedica secondaria |
| Humphries (2010) | https://impact.ref.ac.uk/casestudies/CaseStudy.aspx?Id=8857 | Scheda d'impatto REF |
| Nazioni Unite (1998) | https://press.un.org/en/1998/19980928.soc4473.html | Comunicato |
| Steinberg (2008) | https://pmc.ncbi.nlm.nih.gov/articles/PMC2396566/ | Testo, prima metà |
| Britt (1992) | https://www.ojp.gov/ncjrs/virtual-library/abstracts/constancy-and-change-us-age-distribution-crime-test-invariance | Abstract |
| Costa (1998), cap. 1 | https://www.nber.org/chapters/c6107.pdf | Testo del capitolo |
| Skirbekk (2004) | https://econpapers.repec.org/RePEc:vid:yearbk:v:2:y:2004:i:1:p:133-154 | Abstract |
| Coale e McNeil (1972) | https://u.demog.berkeley.edu/~jrw/Biblio/Eprints/126grad/Coale/Extras/coale.mcneil.1972_first.marriage_JASA.pdf | Solo l'abstract riportato dai risultati di ricerca |
| ILOSTAT e licenza dei dati ILO | https://ilostat.ilo.org/glossary/population; https://www.ilo.org/node/9321 | Glossario; condizioni d'uso |
| Pacchetto R `migest` | https://cran.r-project.org/package=migest | Campo licenza (GPL-3) |

### Licenze e attribuzione

La regola del progetto, posta dall'utente il 2026-10-29, è che in Epocha entri solo materiale con licenza compatibile con Apache-2.0, mai materiale con licenza non libera e mai codice copyleft; le idee si usano e si citano. **Questo work item non incorpora alcun materiale altrui**: usa soglie e risultati, che sono fatti e idee, e li cita; i testi dei prompt sono scritti con parole nostre e non riprendono la formulazione delle tappe di Zubler et al. (2022) né di altre fonti (FR-015). Nessun dataset è usato.

Per il materiale che i work item separati potrebbero voler incorporare ho verificato questo. I dati ILOSTAT sono sotto CC BY 4.0 dal 3 maggio 2023 secondo la pagina ILO dei diritti, quindi compatibili con attribuzione; i dataset precedenti vanno controllati uno per uno («licenza da verificare prima dell'uso»). Il pacchetto R `migest` è GPL-3, cioè copyleft: né il suo codice né i suoi oggetti dati (come `rc_model_fund`) possono entrare nel repository. Le tabelle del rapporto IIASA di Rogers e Castro hanno una licenza che non ho verificato («licenza da verificare prima dell'uso»), mentre la forma funzionale del modello è un'idea e si implementa citandola; lo stesso vale per il modello di Coale e McNeil, il cui articolo è sotto copyright dell'editore. I libri di Humphries e Costa e gli articoli citati sono opere sotto copyright: se ne citano risultati e numeri, non se ne riproducono tabelle o testo.

## Gli stadi di vita

Uno stadio esiste nel codice solo se almeno una regola lo distingue dagli altri; lo stadio è sempre **derivato**, mai memorizzato, confrontando `birth_tick` con i limiti che FR-001b ricava dalle soglie; l'età canonica `age_in_years` resta quella mostrata nei prompt. Le bande linguistiche della chat sono una funzione separata, perché cambiano a 12 mesi, 24 mesi e 4 anni dentro uno stesso stadio.

| Stadio | Intervallo (anni compiuti) | Fonte della soglia inferiore | Deliberazione LLM | Lavoro | Mobilità | Coppia | Chat |
|---|---|---|---|---|---|---|---|
| Infanzia e fanciullezza | [0, 10) | — | No | No (euristica regolabile, FR-007) | Solo con il nucleo | No | Bande di Zubler et al. 2022 (FR-009) |
| Adolescenza | [10, `adulthood_age`) | OMS (10-19); Sawyer et al. 2018 | Sì, con vocabolario ristretto | Come oggi (rinviato) | Solo con il nucleo | Dalla `min_marriage_age` dell'era (regola esistente) | Registro esistente, età dichiarata |
| Età adulta | [`adulthood_age`, ∞) | Template d'era, `migration.adulthood_age` (vedi «La soglia adulta per era») | Sì | Sì | Sì | Dalla `min_marriage_age` dell'era (regola esistente; in `industrial` quella maschile è 18, sopra la soglia adulta di 16) | Invariata, età dichiarata |
| Anzianità (definita, **non cablata**) | [60, ∞) | Nazioni Unite 1998 | Come adulto | Come adulto; pensione rinviata | Come adulto | Come adulto | Età dichiarata |

La soglia di 10 anni è uguale in tutte le ere, perché viene da una definizione sanitaria dell'adolescenza; va detto con chiarezza che quella definizione è una banda statistica, non una misura della capacità decisionale, e la uso come il confine documentato più vicino fra «nessuna deliberazione» e «deliberazione con capacità ristrette», non come una sua prova.

## La soglia adulta per era

La decisione D-29-5 chiede una sola soglia adulta, con una fonte per era trovata prima della chiusura del gate, oppure dichiarata euristica regolabile. Oggi `migration.adulthood_age` vale 16 in `pre_industrial_christian`, `pre_industrial_islamic` e `industrial`, e 18 in `modern_democracy` e `sci_fi`; il whitepaper (§4.1.5, tabella 4.12) la documenta come «design parameter; boundary for tied-mover minors», cioè senza fonte. L'esito della ricerca è il seguente, era per era.

Il diritto di confronto scelto per ciascuna era è una **scelta rappresentativa dichiarata**, non una conseguenza della calibrazione. La scelta è guidata dalla calibrazione dove questa è inglese: il whitepaper (§4.1, tabella dei parametri di Heligman-Pollard) calibra `pre_industrial_christian` su Wrigley e Schofield (1981), Inghilterra 1700-1749, e `industrial` sulle tavole HMD di Inghilterra e Galles 1841-1900, quindi per queste due ere confronto con il diritto inglese. Non vale per le altre due: `pre_industrial_islamic` condivide la calibrazione inglese della mortalità ma rappresenta un'era islamica, quindi la confronto con il diritto islamico; `modern_democracy` è calibrato sugli USA del 2019, e uso come esempio statutario Inghilterra e Galles.

Per `modern_democracy` il valore 18 ha una **fonte statutaria per Inghilterra e Galles**, il Family Law Reform Act 1969, sez. 1(1); estenderlo all'era moderna in generale è una scelta rappresentativa dichiarata, coerente con il limite di 18 anni con cui la Convenzione ONU sui diritti dell'infanzia definisce il bambino, che però non fissa una maggiore età. Il template calibra la mortalità sugli USA del 2019, dove la maggiore età è fissata dai singoli stati; non l'ho verificata. Per `sci_fi`, che è un'era immaginaria, il 18 è un'**euristica regolabile** per analogia con l'era moderna. Per `pre_industrial_christian` e `industrial` le fonti **contraddicono** il valore: Blackstone (1765) dà la maggiore età inglese a 21 anni per entrambi i sessi, e lo stesso Family Law Reform Act mostra che era ancora 21 quando la sostituì con 18, mentre i due template dicono 16; il 16 resta quindi un'euristica regolabile e, usato come soglia della capacità contrattuale, la anticipa di cinque anni rispetto al diritto inglese. Per `pre_industrial_islamic` la fonte che ho letto mostra che nemmeno i giuristi sciiti concordano sull'età della pubertà legale (*bulugh*), con età diverse per maschi e femmine, e che per gli atti patrimoniali serve una capacità distinta (*rushd*); le età delle scuole sunnite non le ho verificate: nessun numero unico la rappresenta, e il 16 resta un'euristica regolabile.

La conseguenza sulla spec è che la soglia adulta resta una sola, `migration.adulthood_age`, con fonte statutaria per l'era moderna e dichiarata **euristica regolabile per era** altrove (FR-001a). Correggere i valori dei template non è compito di questa spec: la chiave appartiene alla demografia auditata, che la usa per i minori che migrano col nucleo, e cambiarla toccherebbe §4.1.5; la discrepanza con il 21 inglese di `pre_industrial_christian` e `industrial` va segnalata ai proprietari della demografia.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Un bambino sotto i 10 anni non delibera e non lavora (Priority: P1)

Un ricercatore avvia una simulazione con la demografia attiva. Nascono agenti durante la run. Nessuno di loro, finché resta sotto i 10 anni, riceve una chiamata LLM di decisione o scrive un `DecisionLog`, e nessuno produce beni nell'economia.

**Why this priority**: è il difetto che ha aperto il work item; con la demografia cablata colpisce ogni run.

**Independent Test**: una simulazione di fixture con un adulto e un neonato nella stessa zona, LLM sostituito da un doppio che conta le chiamate; un tick sul percorso Celery (`run_simulation_loop`).

**Acceptance Scenarios**:

1. **Given** un neonato nato al tick 50 e un adulto, entrambi vivi, **When** gira il tick 51, **Then** l'LLM di decisione è chiamato solo per l'adulto e non esiste alcun `DecisionLog` del neonato.
2. **Given** un agente di 9 anni e uno di 30 nella stessa zona con lo stesso ruolo non mappato, **When** gira il passo di produzione, **Then** l'agente di 9 anni produce 0 e non genera righe `EconomicLedger` di produzione, mentre la produzione dell'agente di 30 anni è identica a quella di prima della modifica.
3. **Given** un agente che compie 10 anni fra il tick t e il tick t+1, **When** gira il tick t+1, **Then** l'agente delibera.

---

### User Story 2 - Un adolescente ha capacità ristrette (Priority: P2)

Un adolescente delibera, ma non può contrarre prestiti, comprare o vendere proprietà, né trasferirsi da solo; può formare una coppia solo dalla soglia matrimoniale della sua era.

**Why this priority**: il prompt da solo non basta, perché l'LLM può scegliere un'azione non offerta, e alcune azioni producono effetti al tick successivo leggendo il `DecisionLog`.

**Independent Test**: prompt, `DecisionLog` e tick successivo per un agente di 14 anni in un'era con `adulthood_age = 16`.

**Acceptance Scenarios**:

1. **Given** un agente di 14 anni, **When** si costruisce il prompt di decisione, **Then** il vocabolario non contiene `borrow`, `sell_property`, `buy_property`, `move_to`, e contiene l'età in anni e lo stadio.
2. **Given** lo stesso agente e una risposta LLM `{"action": "buy_property"}`, **When** si scrive il `DecisionLog` e gira il tick successivo con il passo economico, **Then** il `DecisionLog` registra `rest`, nessuna `Property` cambia proprietario, nessun prestito è creato, e il rifiuto è nel log con agente, azione e stadio.
3. **Given** una quindicenne in un'era con `min_marriage_age_female = 14`, **When** si costruisce il prompt, **Then** `pair_bond` è offerta; a 13 anni non lo è.

---

### User Story 3 - La chat risponde secondo l'età (Priority: P2)

L'utente apre la chat con un agente di dieci mesi e lo abbraccia. La risposta è fatta di suoni e reazioni di un lattante, senza parole. Con un bambino di tre anni la risposta è fatta di combinazioni di poche parole; con un adulto la chat resta com'è, ma l'agente conosce la propria età.

**Why this priority**: è il secondo sintomo osservato dall'utente; costa un numero di query costante per messaggio.

**Independent Test**: il prompt di sistema per agenti di 10 mesi, 18 mesi, 3 anni, 7 anni, 14 anni e 40 anni, da tutti e tre i prompt di chat (chat privata e chat di gruppo della dashboard, chat WebSocket); più una verifica manuale nell'ambiente reale.

**Acceptance Scenarios**:

1. **Given** un agente di 10 mesi, **When** si costruisce il prompt di chat, **Then** il prompt dichiara l'età in mesi, impone di rispondere solo con vocalizzi e reazioni non verbali, e dichiara che questa istruzione prevale su ogni altra regola del prompt sul numero di frasi o sulle didascalie.
2. **Given** lo stesso agente, **When** il prompt è costruito dalla chat privata della dashboard (`_build_chat_system_prompt`), dalla chat di gruppo della dashboard (`group_chat_view`) e da `chat/consumers.py`, **Then** il frammento d'età è identico nei tre prompt.
3. **Given** un agente nato nella run con `role="child"` che oggi ha 30 anni, **When** si costruisce un prompt di chat o di decisione, **Then** il prompt non lo presenta come «a child».

### Edge Cases

- **`birth_tick` nullo.** Con la demografia disattivata gli agenti possono avere `birth_tick` nullo; `age_in_years` ricade sulla colonna `age`. La selezione applica la stessa ricaduta, altrimenti in una simulazione senza demografia nessuno delibererebbe più. Il filtro della finestra fertile del Plan 4 (`_fertile_window_filter`) esclude invece i nulli, e copiarlo così com'è sarebbe un difetto.
- **Percorso sequenziale.** `SimulationEngine.run_tick` non chiama `run_demography_tick`: su quel percorso non ci sono nascite e la colonna `age` non viene aggiornata. Per questo la selezione legge `birth_tick` e non `age` (FR-003).
- **Template non risolvibile.** Se il template d'era non si carica, la soglia adulta è ignota. Il comportamento è restrittivo: la soglia è presa uguale al massimo di `adulthood_age` fra i template distribuiti, cioè 18, e l'errore è registrato da `_load_simulation_template` a ogni risoluzione fallita, cioè una volta per ogni agente deliberante, una volta per tick dalla selezione degli agenti deliberanti e una dal blocco demografico quando è attivo, e una per ogni chiamata dell'economia e della chat, perché la cache del caricatore non memorizza le eccezioni; non lo deduplico, perché un template guasto è un errore di configurazione che deve restare rumoroso. Non è il comportamento attuale di `decision._build_system_prompt`, che con il file mancante tiene tutte le azioni senza registrare nulla e con il template non valido le toglie registrando una volta per agente: è un comportamento nuovo, scelto perché un guasto non deve dare capacità contrattuali a un minore. Con il template non risolvibile il prompt di decisione non offre inoltre **nessuna** delle tre azioni demografiche (`pair_bond`, `separate`, `avoid_conception`), perché `pair_bond` dipende da `meets_marriage_age`, che senza template non si può valutare, e le altre due dipendono da chiavi del template; oggi un file mancante le lascia tutte e tre senza registrare nulla. Ogni prompt costruito così registra un avviso (livello WARNING) che nomina il template configurato e dice che le azioni demografiche sono state tolte (FR-005, decisione D-29-35): l'avviso del caricatore dice la causa, «template non trovato» o «non valido», questo dice la conseguenza sul prompt. Una simulazione senza demografia risolve il template predefinito `pre_industrial_christian` (soglia 16), come già fa `decision.py`.
- **Agente generato sotto i 10 anni.** `world/generator.py` chiede all'LLM un'età libera. Un bambino generato non delibera; senza demografia la sua età non avanza (limite preesistente), quindi resta non deliberante per tutta la run.
- **Capo di stato bambino.** Un capo di stato sotto i 10 anni non delibera; la reggenza non è modellata.
- **Accelerazione diversa da 1.** Le soglie in anni si convertono in `birth_tick` con la stessa formula di `age_in_years`.
- **Minore sposato.** Nelle ere preindustriali `min_marriage_age_female = 14` e `adulthood_age = 16`: una quindicenne può essere in coppia e restare adolescente, con i limiti contrattuali e di mobilità dell'adolescenza, coerentemente con `household_keys`, dove la coppia prevale sulla catena del tutore.

## Requirements *(mandatory)*

### Relazione con la guardia del Plan 4 (decisione D-29-4)

La decisione D-29-4 dello stesso giorno ha stabilito che il Plan 4 escluda dal ciclo decisionale chi è **sotto `migration.adulthood_age`** e dia l'età alla chat. Il codice è nato sul ramo `20261029-wpd-minors-decision-loop` (commit `7e9c9c6`, `a7d21a5`, `6c21973`) ed è integrato nel ramo del Plan 4 dal merge `c1e8569`: `demography.orchestrator.minor_agent_ids` restituisce gli id dei minori, che `engine.py` e `tasks.py` sottraggono con `exclude(id__in=...)`. Sulla testa del Plan 4, dopo i commit successivi `02a1d47` (chat di gruppo) e `430dfa6` (chat WebSocket e spostamento nella demografia), `describe_speaker`, attraverso `describe_age` e `current_age_in_years`, apre con l'età tutti e tre i prompt di chat; `_age_clock` e `_load_simulation_template` risolvono durata del tick, accelerazione e template.

Questo work item **sostituisce quella guardia, non la affianca**, e ne cambia tre comportamenti in modo dichiarato. Primo, la soglia di esclusione scende da `adulthood_age` a 10 anni, perché fra 10 anni e l'età adulta l'agente delibera con le capacità ristrette di FR-005 e FR-006. Secondo, `minor_agent_ids` legge tutti i vivi e filtra in Python; FR-003 la sostituisce con un filtro in SQL, che legge solo le righe degli agenti che deliberano. Terzo, `minor_agent_ids` restituisce un insieme vuoto, cioè non esclude nessuno, sia quando la demografia è disattivata sia quando il template non si carica; FR-003 rovescia entrambi i casi: senza demografia la regola d'età si applica comunque sulla colonna `age` (SC-007), e con il template guasto la soglia adulta diventa 18 (caso limite «Template non risolvibile»). Restano riusati `_age_clock`, `_load_simulation_template`, `current_age_in_years` e `describe_speaker`: il frammento d'età che `describe_speaker` già dà ai tre prompt di chat diventa il frammento di FR-009, esteso con i registri; nessun prompt di chat va collegato di nuovo, perché tutti e tre lo chiamano già. Nessun secondo controllo d'età resta nel ciclo decisionale e nessun secondo frammento d'età resta nella chat; i test della guardia vengono adattati, non duplicati.

### Functional Requirements

Ogni requisito dichiara il proprio costo per tick in funzione della popolazione viva N.

- **FR-001**: esiste **una sola** funzione pura che restituisce lo stadio di vita di un agente a un tick, calcolato confrontando `birth_tick` con i limiti di FR-001b derivati dalle soglie della tabella degli stadi, con la soglia adulta letta da `migration.adulthood_age` del template d'era. Riceve la durata del tick e l'accelerazione già risolte dal chiamante. La durata del tick viene dal `World` **già caricato** dal chiamante, mai da una lettura per agente: `_age_clock` oggi chiama `_tick_duration_hours`, che esegue `World.objects.filter(...).first()` a ogni chiamata, quindi va esteso perché accetti un `World` già caricato (o la durata del tick), e solo in quella forma lo usano i chiamanti per agente. L'accelerazione vale quella del template demografico, 1,0 quando il template manca, come in `_age_clock`; il template si risolve con `_load_simulation_template`, che legge un file con cache e non il database. Ogni chiamante, economia compresa, usa il template demografico, non quello economico. Sul ciclo decisionale il `World` è già disponibile (`world_state`, passato a `process_agent_decision`). *Costo della funzione*: zero query; il costo di procurarsi il `World` è dichiarato da ciascun requisito chiamante.
- **FR-001b**: dentro questo work item, ogni soglia d'età che decide una regola (10 anni e `adulthood_age`) si confronta **in un solo modo**: si converte una volta in un limite su `birth_tick` con la conversione di `_fertile_window_filter`, e sia il filtro SQL di FR-003 sia la funzione dello stadio confrontano `birth_tick` con quel limite; per gli agenti con `birth_tick` nullo entrambi confrontano la colonna intera `age`. `age_in_years`, un numero in virgola mobile, resta per l'età mostrata nei prompt e nella chat e per le bande linguistiche sotto i 10 anni di FR-009, mai per decidere le soglie dei 10 anni e di `adulthood_age`: due confronti diversi sulla stessa soglia, uno sulla lettura in virgola mobile e uno sul limite intero, concordano solo finché l'età e la ricerca del limite usano la stessa aritmetica, e altrimenti potrebbero selezionare un agente che lo stadio dichiara ancora bambino. Sul ramo del Plan 4 oggi la usano: dal round 15 del gate di fase 6, `age_in_years` passa per `_years_elapsed` (`elapsed * tick_duration_hours * acceleration / 8760`, una sola divisione finale) e `_fewest_ticks_to_reach` corregge il limite proprio su `_years_elapsed`. Il docstring di `age_in_years` registra che la forma precedente, a due divisioni, leggeva 62,999... per 63 a 3285 tick settimanali; ho ricalcolato il 2026-10-29 che la forma attuale legge esattamente 63,0 e che il limite per 63 anni vale 3285 tick (decisione D-29-35). La garanzia di FR-001b resta strutturale e non numerica: il confronto unico non dipende da quella coincidenza fra due funzioni, e SC-010 fissa con valori letterali il comportamento attuale, così che un ritorno alla vecchia aritmetica si veda. La misura dell'audit del round 6 (nessuna divergenza per 10, 16 e 18 anni a nessuna durata intera del tick fra 1 e 8760 ore con accelerazione 1, divergenza a 63 anni sul mondo settimanale) descrive l'aritmetica a due divisioni, perché la divergenza a 63 anni è esattamente il caso che il round 15 del Plan 4 ha tolto; non descrive più il codice del Plan 4. Restano come sono, perché appartengono alla demografia auditata e sono fuori perimetro, i confronti di `adulthood_age` in `household_keys` (`demography/context.py`, sull'età in virgola mobile) e in `inheritance.py` (sulla colonna `age`).
- **FR-001a**: ogni soglia ha nel docstring autore, anno, titolo e URL della propria fonte; la soglia adulta è documentata con la fonte per l'era moderna e come euristica regolabile per le altre ere, con la discrepanza inglese della sezione «La soglia adulta per era».
- **FR-002**: un agente sotto i 10 anni non riceve mai una chiamata LLM di decisione e non scrive mai un `DecisionLog`, in entrambi i percorsi del ciclo decisionale. *Costo*: incluso in FR-003.
- **FR-003**: gli agenti che deliberano in un tick sono scelti da **una sola funzione**, usata da entrambi i percorsi, con il filtro d'età applicato **in database** e un numero di query **costante**, indipendente da N. Il filtro si esprime come intervallo su `birth_tick`, riusando la conversione di `_fertile_window_filter`, e include gli agenti con `birth_tick` nullo tramite la colonna `age`. La colonna `age`, che il passo di mortalità del Plan 4 aggiorna a ogni tick, sarebbe un filtro più semplice ed esatto sul percorso Celery, dove la demografia gira prima del chord; è scartata perché sul percorso sequenziale nessuno la aggiorna. La funzione è `select_deliberating_agents` di `agents/deliberation.py`, che appartiene al work item prerequisito delle coppie a regole: questa spec la estende, sostituendo `minor_agent_ids` e l'`exclude(id__in=...)` con il filtro SQL su `birth_tick` e aggiungendo il parametro `World`. L'ordine dei risultati è quello di priorità di `select_deliberating_agents` (capo di Stato, capi dei gruppi, poi gli altri, a parità per id) e non è per id. Riceve dal chiamante il `World` (o la durata del tick) e non lo legge da sé: il percorso sequenziale lo ha già (`self.simulation.world` in `run_tick`), mentre `run_simulation_loop` lo prende da `simulation.world` prima della selezione. `World.simulation` è un campo uno-a-uno, e il passo economico, che gira prima sullo stesso oggetto `simulation`, di solito ha già letto e messo in cache quel `World`; la lettura costa una query solo quando il passo economico non l'ha fatta. *Costo*: O(1) query nella funzione, più al più una query per tick sul percorso Celery per il `World`; le righe lette sono quelle degli agenti che deliberano, O(N) come oggi.
- **FR-005**: il prompt di decisione contiene l'età in anni compiuti e lo stadio, e un vocabolario filtrato per stadio: sotto `adulthood_age` mancano `borrow`, `sell_property`, `buy_property` (capacità contrattuale) e `move_to` (i minori migrano con il nucleo, coerentemente con la componente pre-lavorativa di Rogers e Castro 1981 e con `coordinate_family_migration`); `pair_bond` compare solo se `couple.meets_marriage_age` è vero. Se il template d'era non si carica, il prompt non offre nessuna delle tre azioni demografiche (`pair_bond`, `separate`, `avoid_conception`) e il logger dell'applicazione registra, per ogni prompt costruito così, un avviso di livello WARNING che contiene il nome del template configurato (`demography_template` della configurazione della simulazione, con lo stesso valore predefinito di `_load_simulation_template`) e dice che le azioni demografiche sono state tolte (decisione D-29-35; caso limite «Template non risolvibile»). Il prompt non contiene aggettivi comportamentali per età. *Costo*: zero query aggiuntive (il mondo è già passato a `process_agent_decision`); i token aggiunti al prompt si misurano in fase 5 e non sono stimati qui.
- **FR-006**: l'azione restituita dall'LLM è **sanificata dentro `process_agent_decision`, prima di scrivere il `DecisionLog`**: un'azione vietata allo stadio dell'agente è sostituita **per intero** da un'azione `rest` con un motivo fisso, così che `output_decision` non contenga in nessun campo il nome dell'azione vietata, e il rifiuto va nel logger dell'applicazione con agente, azione e stadio, non nel `DecisionLog`. Il punto è obbligato, perché `buy_property` (`economy/property_market.py`) e gli intenti di coppia vengono letti dal `DecisionLog` al tick successivo, e i lettori filtrano prima per sottostringa sul JSON memorizzato. *Costo*: zero query.
- **FR-007**: in `economy/production.py`, un agente sotto i 10 anni produce 0. È un'**euristica regolabile**, non una regola con fonte: nessuna fonte verificata fissa un'età a cui la produzione è nulla in ogni era, e Humphries (2010) documenta lavoro minorile nel 1790-1850. La regola corregge il difetto di oggi, un neonato che produce come un adulto; il valore della soglia è uno dei temi del work item «chiavi del lavoro per era». *Costo*: la durata del tick viene dal `World`, che `process_economy_tick_new` legge già una volta per tick (`world = simulation.world`, nel passo 8c sull'inflazione); la lettura si sposta prima del ciclo sulle zone e viene riusata, quindi nessuna query nuova. Oggi quella lettura sta dentro un `try/except Exception: pass`; spostata, sta **fuori** da quell'except cieco, e se il `World` manca (l'accesso a `simulation.world` solleva `World.DoesNotExist`, che è l'unica eccezione catturata) oppure la sua durata del tick è nulla o zero, la durata ricade su 24,0 ore, lo stesso valore di riserva di `_tick_duration_hours`, con un avviso nel log. L'except cieco che resta intorno all'aggiornamento della stabilità è preesistente e fuori perimetro (rinvio 10). Le query di produzione diminuiscono, perché un agente con produzione 0 non salva l'inventario e non scrive righe `EconomicLedger`.
- **FR-007a**: il percorso economico legacy (`world/economy.py`, usato quando non esiste una `Currency`) è escluso: è deprecato e continua a pagare un reddito per ruolo anche ai bambini, come dichiarato fra i limiti noti.
- **FR-009**: il prompt di chat contiene un **frammento d'età prodotto da una sola funzione**, `describe_speaker` della demografia, usata da tutti e tre i prompt di chat: la chat privata della dashboard (`dashboard/views.py`, `_build_chat_system_prompt`), la chat di gruppo della dashboard (`dashboard/views.py`, `group_chat_view`, sia per l'agente interpellato sia per chi ascolta con la risposta breve da 80 token) e la chat WebSocket (`chat/consumers.py`, `ChatConsumer._generate_response`). La chat di gruppo è nel perimetro per la decisione D-29-35: una sola funzione serve già i tre prompt, e lasciarne fuori uno vorrebbe dire una seconda funzione o un parametro che la spegne. Il frammento dichiara l'età (in mesi sotto i 2 anni, in anni sopra) e il registro: sotto i 12 mesi solo vocalizzi, lallazione di sillabe e reazioni non verbali, senza parole; fra 12 e 24 mesi al più parole singole; fra 2 e 4 anni combinazioni di poche parole, che si allungano verso frasi di quattro parole; fra 4 e 10 anni linguaggio semplice di un bambino; dai 10 anni in su il registro esistente con l'età dichiarata. Il passaggio al registro esistente si decide con la funzione dello stadio di FR-001 (stadio diverso da infanzia e fanciullezza), non con l'età mostrata; `age_in_years` serve solo a mostrare l'età e a scegliere le bande sotto i 10 anni; dentro lo stadio infanzia e fanciullezza, un'età mostrata di 4 anni o più cade nella banda 4-10 anni anche se la lettura in virgola mobile arriva a 10. Simmetricamente, dentro lo stadio adolescenza l'età mostrata è almeno 10 anni anche se la lettura in virgola mobile dà 9,999. Le bande fino a 4 anni seguono Zubler et al. (2022), che indicano l'età entro cui almeno il 75% dei bambini raggiunge la tappa (lallazione a 9 mesi, un nome per il genitore a 12, parole a 15-18, due parole insieme a 24, frasi di quattro parole a 4 anni): sono bande prudenti, non mediane. La banda 4-10 anni e il passaggio al registro esistente a 10 anni non hanno una fonte linguistica e sono **euristiche regolabili**: il 10 è la soglia sanitaria dell'adolescenza, riusata per non introdurre un secondo confine. *Costo*: nella chat privata e nella chat WebSocket al più due query per messaggio (la simulazione dell'agente e il suo `World`, se la vista non li ha già caricati); nella chat di gruppo l'orologio dell'età si legge una volta per richiesta (`current_age_clock`, come oggi) e si passa a ogni `describe_speaker`, che con l'orologio non esegue query, quindi il frammento non aggiunge query per agente del gruppo; indipendente da N.
- **FR-010**: per i registri sotto i 4 anni il frammento è un'istruzione autosufficiente che dichiara di prevalere su ogni altra regola del prompt sul numero di frasi o sulle didascalie non verbali; non nomina regole specifiche, perché il prompt di `chat/consumers.py` non le contiene e quello della chat di gruppo ne contiene altre (la risposta `*ascolta in silenzio*` di chi ascolta).
- **FR-011**: quando il ruolo è il segnaposto di nascita `child` e lo stadio è adolescenza o età adulta, i prompt di decisione e di chat omettono il ruolo invece di dire «a child». La regola vale per l'agente stesso e per gli altri agenti che il contesto di decisione elenca come «nome (ruolo)», cioè la lista degli agenti vivi e quella dei membri della fazione in `decision.py`; per entrambe `birth_tick` e `age` si aggiungono al `.only("name", "role")` delle due query esistenti, così il numero di query non cambia.
- **FR-012**: la chat resta disponibile per ogni agente vivo, di qualunque età.
- **FR-013**: nello stesso commit del codice, in entrambe le lingue: il whitepaper §3.1 e §3.2 (che oggi dice «Each living agent goes through a four-stage pipeline») descrivono il filtro d'età e la sanificazione; §3.6 e §4.8 documentano FR-007 (`economy/production.py` è nella tabella del doc-sync); §3.8 descrive il frammento d'età della chat; §3.3 (contratti di integrazione fra moduli) aggiunge la funzione dello stadio, che `agents`, `economy` e la chat chiamano dalla demografia; una nuova sottosezione del §8 (audit in corso) documenta stadi, soglie e fonti. I README citano gli stadi nell'architettura se descrivono la pipeline decisionale. La build map viene aggiornata all'apertura del work item e a ogni checkpoint.
- **FR-014**: nessun serializer, nessuna rotta e nessun template HTML espone lo stadio.
- **FR-016**: il docstring di `coordinate_family_migration` in `demography/migration.py` diventa falso in due punti quando gli adolescenti deliberano: l'intestazione «MINORS ARE NOT CALLED TO THE DECISION LOOP», e la frase che attribuisce all'orchestratore del Plan 4 il compito di non presentare `move_to` ai minori, compito che dopo questo work item spetta alla pipeline decisionale di `agents` (FR-005 e FR-006). Questo work item riscrive entrambi nello stesso commit del codice; la garanzia che il docstring dichiara testata, l'assenza di artefatti decisionali per i membri spostati, resta vera. Per la regola del doc-sync il commit dichiara che il §4.1.5 del whitepaper resta vero (vi si dice che nessun minore riceve un `DecisionLog` per uno spostamento che non ha scelto, e FR-005 lo garantisce). Ogni modifica a `demography/orchestrator.py`, che la tabella del doc-sync lega al §4.1.0, porta lo stesso obbligo: l'estensione di `_age_clock`, la rimozione di `minor_agent_ids` e l'eventuale collocazione lì della funzione dello stadio; il commit aggiorna il §4.1.0 dove ne descrive qualcosa, altrimenti dichiara perché non lo tocca.
- **FR-015**: codice, prompt e documentazione non incorporano testo, tabelle, dati o codice di terzi; i prompt descrivono i registri con parole nostre. Qualsiasi dataset proposto in seguito porta nella spec la propria licenza, o la dicitura «licenza da verificare prima dell'uso», e niente sotto licenza non libera o copyleft entra nel repository.

I numeri FR-004 e FR-008 della prima stesura non sono riassegnati: appartengono ai work item separati.

### Costo per tick, riepilogo

Oggi il passo decisionale costa N chiamate LLM e circa q query per agente. Con il limite K del work item prerequisito costa al più K chiamate LLM per tick, con K = `max_protagonists`, e circa q query per ciascuno degli agenti che deliberano, più un numero costante di query per la selezione. Questa spec non aggiunge costo per agente. La produzione resta O(N) query, con una costante più bassa. La chat costa per messaggio.

### Key Entities

- **Stadio di vita**: valore derivato, mai memorizzato. Tre valori cablati (infanzia e fanciullezza, adolescenza, età adulta); l'anzianità è definita ma non cablata.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001 (costo della selezione)**: la funzione di selezione di FR-003 esegue lo stesso numero di query su una fixture con 5 agenti vivi e su una con 55, a parità di zone, e in entrambe **la somma delle righe restituite dalle sue query è uguale al numero di agenti che deliberano**, con il `World` passato dal test, misurata con un wrapper di esecuzione sulla connessione (`connection.execute_wrapper`) che dopo ogni `execute` legge `context["cursor"].rowcount`, verifica che non valga -1 e somma, e con un controllo incrociato fra quella somma e la lunghezza del risultato della funzione, su fixture che contengono anche agenti sotto i 10 anni. Inoltre, sul percorso decisionale, il numero di query per agente deliberante non cambia rispetto a prima della modifica. Una selezione che legga l'età agente per agente fallisce la prima condizione; una che legga tutti i vivi e filtri in Python, come `minor_agent_ids`, fallisce la seconda. La forma «raddoppiando la popolazione il conteggio non raddoppia» è vietata, perché passa anche su un costo per agente.
- **SC-002**: in una run end-to-end sul percorso Celery, con la demografia attiva e almeno una nascita, il numero di `DecisionLog` scritti da agenti sotto i 10 anni è 0 su tutti i tick misurati. Il percorso sequenziale, che non ha nascite, è coperto da un test della selezione con un agente di 5 anni costruito a mano.
- **SC-003**: nella fixture della User Story 1 la produzione dell'agente di 9 anni è 0, quella dell'adulto è uguale al valore di prima della modifica entro 1e-9, e il numero di query del passo economico, a popolazione fissa, non supera quello di prima.
- **SC-004**: per un agente di 14 anni con `adulthood_age = 16` le quattro azioni contrattuali e di mobilità mancano dal prompt. Il test chiama **direttamente** `process_agent_decision` con il doppio LLM che risponde `buy_property`, non un tick completo (dove la guardia di D-29-4 escluderebbe già il quattordicenne e il test passerebbe sul codice di oggi), e poi chiama `process_property_listings(simulation, tick + 1)`. La fixture rende l'acquisto **realizzabile**: una `Currency` primaria; una `PropertyListing` con stato `"listed"` e `listed_at_tick > tick - 9`, perché la scadenza (`listed_at_tick <= tick - 10`) è valutata al tick successivo, nella zona dell'agente, di un proprietario diverso, senza vincoli attivi o in default sulla proprietà; un `AgentInventory` dell'agente con contante sufficiente nella valuta primaria. Un caso di controllo con lo stesso `DecisionLog` non sanificato completa l'acquisto, e prova che la fixture è realizzabile. Con la modifica, l'`output_decision` non contiene la stringa `buy_property` in nessun campo, nessuna `Property` cambia proprietario, e il logger dell'applicazione contiene il rifiuto. L'asserzione che nessun prestito sia creato resta solo come guardia di regressione, perché il mercato immobiliare oggi non concede prestiti.
- **SC-005**: il frammento d'età di chat per 10 mesi, 18 mesi, 3 anni, 7 anni, 14 anni e 40 anni contiene ciascuno il registro di FR-009, ed è identico byte per byte fra i tre prompt di chat (chat privata e chat di gruppo della dashboard, chat WebSocket); nella chat di gruppo il test copre sia l'agente interpellato sia chi ascolta.
- **SC-006 (ambiente reale)**: in una simulazione locale con un agente di 10 mesi invio 5 volte il messaggio «ti prendo in braccio e ti abbraccio» nella lingua dell'interfaccia; il criterio è superato solo se **5 risposte su 5** non contengono parole lessicali della lingua (sono ammesse sillabe di lallazione come «mamama»). Il risultato si riporta come «verificato in ambiente locale», con le risposte allegate.
- **SC-007**: in una simulazione senza demografia con 20 agenti, di cui uno di 8 anni, deliberano esattamente i 19 agenti dai 10 anni in su, e il bambino non delibera in nessun tick.
- **SC-008**: suite intera verde, `test_citation_hygiene.py` e `test_build_map_bilingual.py` compresi.
- **SC-009 (contratto API)**: un test confronta l'insieme dei campi dei serializer degli agenti (`AgentSerializer` usa `fields="__all__"`, quindi un campo di modello nuovo cambierebbe la risposta) con un elenco di riferimento congelato nel test e scritto prima della modifica, e li trova identici. Il progetto non genera uno schema OpenAPI, quindi il confronto è sui campi.
- **SC-010 (confine delle soglie)**: su un mondo settimanale (`tick_duration_hours = 168`), dove il limite dei 10 anni cade a 521,43 tick e nessun `birth_tick` intero lo tocca esattamente, per ciascuna soglia (10 anni e `adulthood_age`) il test usa agenti con `birth_tick` alla distanza floor(L) - 1, floor(L), ceil(L) e ceil(L) + 1 tick dal tick corrente, dove L è il limite in tick; la selezione di FR-003 e la funzione dello stadio di FR-001 concordano in ogni caso, cioè un agente è selezionato se e solo se il suo stadio non è infanzia e fanciullezza, e il vocabolario ristretto cade esattamente sotto `adulthood_age`. Su un mondo settimanale i limiti non sono interi, quindi `<` e `<=` danno lo stesso verdetto e quei punti provano solo l'accordo fra selezione e stadio. Per questo il test ha una seconda parte su un mondo giornaliero (`tick_duration_hours = 24`), dove i limiti sono interi (3650, 5840 e 6570 tick per 10, 16 e 18 anni) e i punti a distanza L - 1, L e L + 1 distinguono `<` da `<=`. Il test deve poter fallire: in fase 5 lo si verifica una volta con la mutazione di un carattere (`<` al posto di `<=`) in uno dei due confronti, che la parte giornaliera deve rilevare. Un secondo test sulla conversione condivisa fissa il comportamento attuale nel caso che motiva FR-001b, a 63 anni su un mondo settimanale con accelerazione 1,0: `age_in_years` con `birth_tick = 0` al tick 3285 vale **esattamente** 63,0 (uguaglianza, non approssimazione), e il limite su `birth_tick` per 63 anni, `_fewest_ticks_to_reach(63, 168, 1.0)`, vale 3285; il test asserisce i due valori letterali e non solo il loro accordo. La mutazione nominata è il ritorno di `_years_elapsed` alla forma a due divisioni precedente al round 15 del Plan 4, `elapsed_ticks / (HOURS_PER_YEAR / tick_duration_hours) * acceleration`: sotto quella mutazione l'età vale 62,99999999999999 e il limite 3286, quindi i due restano d'accordo fra loro, ed è per questo che il test asserisce i letterali. In fase 5 la mutazione si applica una volta e il test deve diventare rosso su entrambe le asserzioni.

## Assumptions

- Il Plan 4, con la guardia di D-29-4, è mergiato in `develop` prima che questo work item passi alla fase 5; il ramo di questo work item, creato da `develop` (`2223968`), andrà riallineato dopo il merge.
- La soglia di 10 anni vale per tutte le ere; la pubertà è arrivata storicamente più tardi in molte popolazioni, e non ho verificato una fonte che lo quantifichi.
- Le bande di Zubler et al. (2022) descrivono bambini contemporanei; le applico a ogni era come ipotesi dichiarata.
- **Segnalazione al Plan 4**: i docstring di `age_in_years` e `_fertile_window_filter` dicono che `Agent.age` non viene mai aggiornata, mentre `run_mortality_step` la aggiorna a ogni tick; la contraddizione è del Plan 4.

## Rinvii espliciti (cosa NON fa questa versione)

1. **Work item prerequisito «coppie a regole e protagonisti»**: formazione e separazione delle coppie a regole per chi non delibera (Coale e McNeil 1972 sul `stable_matching` esistente), limite K agli agenti che deliberano, scelta dei protagonisti, misura di scala con un numero di chiamate LLM indipendente da N.
2. **Work item «chiavi del lavoro per era»**: età d'inizio del lavoro per era (ILOSTAT per le ere moderne, Humphries 2010 per l'industriale, da verificare), partecipazione al lavoro fra 10 anni e l'età adulta, età della pensione e calo della produttività in età anziana (Costa 1998; Skirbekk 2004).
3. **Regole statistiche per età** su rischio e crimine (Steinberg 2008; Hirschi e Gottfredson 1983, con la cautela di Britt 1992): nessun modulo a regole oggi le consumerebbe.
4. **Migrazione volontaria per età** (Rogers e Castro 1981): la migrazione volontaria non è cablata nel ciclo decisionale.
5. **Dipendenza degli anziani dai figli**, **assegnazione di un mestiere all'età adulta** per gli agenti nati con `role="child"`, **unificazione delle regole di conversazione** dei tre prompt di chat, **visualizzazione dello stadio** nella dashboard.
6. **Correzione dei valori di `adulthood_age` nei template**, che appartiene alla demografia.
7. **Età di voto per era** nelle elezioni (`world/election.py`), che oggi contano anche i neonati come elettori; richiede la propria fonte per era.
8. **Riconoscimento di `hoard` per sottostringa** in `economy/engine.py` (`_get_hoarding_agent_ids`), difetto preesistente.
9. **Ruolo `child` negli altri prompt**: i fondatori di fazione in `agents/factions.py` e il `__str__` di `Agent` mostrano ancora «nome (ruolo)», quindi «(child)» per un adulto nato nella run.

10. **Except cieco** intorno all'aggiornamento della stabilità del mondo in `economy/engine.py` (passo 8c), preesistente.

Le voci 7, 8, 9 e 10 non hanno ancora un riferimento di tracciamento: vanno aperte come work item sulla build map, che è il registro dei work item del progetto, insieme ai due work item separati di D-29-5.

## Known Limitations

- La soglia adulta ha una fonte statutaria solo per l'era moderna, e per Inghilterra e Galles; nelle altre ere è un'euristica regolabile, e nei template `pre_industrial_christian` e `industrial` anticipa di cinque anni la maggiore età inglese di 21 anni (Blackstone 1765; Family Law Reform Act 1969).
- Le elezioni (`world/election.py`, raccolta degli elettori) contano come elettore ogni agente vivo, neonati compresi (rinvio 7).
- Preesistente, fuori perimetro: `economy/engine.py` (`_get_hoarding_agent_ids`) riconosce `hoard` cercando la sottostringa `"hoard"` in tutto il JSON del `DecisionLog`, senza controllare il campo `action` (rinvio 8).
- La soglia di 10 anni viene da una definizione sanitaria dell'adolescenza, non da una misura di capacità decisionale o produttiva.
- Fra 10 anni e l'età adulta la produzione resta quella di oggi: un adolescente produce come un adulto con lo stesso ruolo, in ogni era, anche dove l'età lavorativa armonizzata dell'ILO è 15 anni.
- Lo stadio di anzianità non ha regole: un agente di 85 anni lavora e produce come uno di 40.
- Il ciclo decisionale costa al più K chiamate LLM per tick, con K = `max_protagonists`; il limite e la sua misura di scala sono del work item prerequisito, non di questa spec.
- La lista dei nomi di agenti vivi nel contesto di decisione (`decision.py`, al più 20) può includere bambini come bersagli di `argue` o `crime`; filtrarli toglierebbe anche bersagli legittimi come i propri figli.
- Il percorso economico legacy paga ancora un reddito ai bambini (FR-007a).
- La reggenza di un capo di stato minore non è modellata.
- Il registro della chat dipende dal rispetto del prompt da parte dell'LLM; SC-006 lo misura, non lo garantisce.

## Architettura e collocazione

Ho cercato in `demography/orchestrator.py` (`age_in_years`, `_fertile_window_filter`), `demography/couple.py` (`meets_marriage_age`), `demography/context.py` (`household_keys`), `agents/decision.py` (`_build_system_prompt`) e nei tre prompt di chat (chat privata e chat di gruppo della dashboard, chat WebSocket). **Trovo e riuso**: `age_in_years` come unica fonte d'età, la conversione età-`birth_tick` di `_fertile_window_filter` (estesa ai nulli), `meets_marriage_age` per `pair_bond`, lo schema di filtro del vocabolario di `_build_system_prompt`, e il predicato e il frammento d'età (`describe_speaker`, già chiamato dai tre prompt) che il Plan 4 ha introdotto con D-29-4. **Costruisco nuovo** solo ciò che nulla fa già: la funzione dello stadio (come generalizzazione del predicato del Plan 4), la selezione con il filtro in database, la sanificazione dell'azione e i registri della chat.

La funzione dello stadio vive nell'app `demography`, che possiede già l'età canonica e le soglie d'era, in un modulo piccolo (per esempio `demography/life_course.py`) oppure dove il Plan 4 avrà messo il proprio predicato, purché sia uno solo; `agents` è scartato perché anche `economy` e la chat consumano lo stadio. La selezione e la sanificazione vivono nell'app `agents`, accanto al ciclo decisionale. Le dipendenze puntano in un solo verso: `agents`, `economy`, `dashboard` e `chat` **usano** `demography`, mai il contrario.

## Log del design

### Passo 1 — Proposta iniziale

Sette stadi su Piaget e sugli stadi psicosociali; un campo `life_stage` aggiornato a ogni tick; deliberazione LLM per tutti con vocabolario per stadio; aggettivi comportamentali nel prompt (adolescenti «inclini al rischio», anziani «prudenti»); moltiplicatori numerici per crimine, migrazione e produttività; pensione a 65 anni; età nel prompt della chat.

### Passo 2 — Primo self-review critico

- **K1, campo memorizzato: ucciso.** Seconda copia di `birth_tick`, e N scritture per tick.
- **K2, LLM per tutti: ucciso** come obiettivo; nasce il limite K, poi trasferito al work item prerequisito da D-29-5.
- **K3, moltiplicatori di crimine e migrazione: uccisi.** Il crimine è una scelta dell'LLM e la migrazione volontaria non è cablata; Britt (1992) mostra che i parametri della curva età-crimine cambiano nel tempo.
- **K4, aggettivi comportamentali: uccisi.** Effetto non misurabile; un aggettivo non è un modello calibrato.
- **K5, stadi di Piaget: uccisi.** Non corrispondono alle capacità d'azione del modello.
- **K6, pensione universale a 65: uccisa.** Costa (1998) la smentisce come costante storica.
- **Trovato mancante**: la produzione dei neonati (FR-007).

### Passo 3 — Secondo self-review e consolidamento

Selezione con filtro in database (S1); ricaduta per i `birth_tick` nulli (S2); il prompt non è una guardia, quindi la sanificazione (S3, poi spostata dall'audit prima del `DecisionLog`); il registro preverbale contro il divieto di didascalie (S4); una sola funzione per i due prompt di chat (S5); il ruolo `child` che resta in età adulta (S6); `adulthood_age` senza fonte (S7, poi risolto in «La soglia adulta per era»); `max_protagonists` corretto da parametro scientifico a budget (K7); stadio anziano senza regole tolto dal codice (K8).

### Dopo il round 1 e la decisione D-29-5

L'audit ha fuso infanzia e fanciullezza, che non differivano in nessuna regola, e ha trovato il difetto delle coppie formate solo da intenti LLM. La Trinità ha poi ridotto il perimetro come descritto in «Perimetro dopo la decisione D-29-5».

## FAQ

**Perché lo stadio è derivato e non un campo?** Perché l'età canonica esiste già (`birth_tick` più `age_in_years`) e una seconda copia di una grandezza diverge, come il gate del Plan 4 ha misurato più volte. Un campo richiederebbe anche N scritture per tick. Il calcolo è aritmetica su dati già in memoria.

**Perché questa spec non consegna il limite dei protagonisti?** Perché il limite, da solo, farebbe crollare la natalità in tre ere su cinque: le coppie nascono solo da intenti LLM, e chi non delibera non ne produce. Proponevo di consegnarlo spento; la Trinità ha deciso (D-29-5) che un meccanismo spedito spento è una configurazione che nessuno imposta, e che esca solo insieme alla formazione delle coppie a regole, in un work item prerequisito.

**Perché 10 anni e non 12, che è l'apertura della finestra fertile nel codice?** La soglia di 10 anni viene dalla definizione OMS dell'adolescenza (10-19), confermata da Sawyer et al. (2018); i 12 anni di `FERTILE_AGE_MIN` sono il limite inferiore di un modello di fecondità, e legare i due numeri inventerebbe una dipendenza che nessuna fonte dichiara. La definizione OMS è una banda sanitaria, non una misura di capacità, e la spec lo dice.

**Perché i bambini sotto i 10 anni non deliberano, se Elder parla di agency?** Il principio di agency di Elder (1998) descrive persone che costruiscono il proprio corso di vita dentro vincoli storici e sociali, non bambini che prendono decisioni economiche indipendenti. Il vocabolario d'azione del modello è fatto quasi solo di azioni adulte, e le restanti hanno solo effetti su umore e relazioni. È un rinvio dichiarato per costo, non una tesi sulla psicologia infantile.

**Perché l'adolescente delibera, se il Plan 4 (D-29-4) esclude tutti i minori?** La guardia del Plan 4 è la versione minima decisa per chiudere un invariante rotto, con l'agency dei minori rinviata espressamente a questo work item. Qui l'adolescente delibera con capacità ristrette, e la sanificazione prima del `DecisionLog` impedisce gli atti contrattuali e gli spostamenti in solitaria che la guardia del Plan 4 voleva evitare. Il predicato resta uno solo, nella demografia, con la soglia più bassa.

**Come si collegano le fonti all'implementazione?** L'OMS e Sawyer et al. (2018) fissano i 10 anni; il Family Law Reform Act 1969 dà la fonte statutaria del 18 dell'era moderna, mentre nelle altre ere la soglia è un'euristica dichiarata, e Blackstone (1765) mostra che nelle ere inglesi la contraddice; Zubler et al. (2022) fissano le bande della chat fino a 4 anni; Rogers e Castro (1981) giustificano che i minori migrino con il nucleo. Le altre fonti verificate non producono regole qui: servono ai work item separati.

**Come interagisce con la demografia e con l'economia?** Riusa `age_in_years`, la conversione età-`birth_tick` e `meets_marriage_age`, e non cambia il comportamento di nessun modulo auditato della demografia, ma ne riformula un docstring di `migration.py` (FR-016) estende `_age_clock` perché accetti un `World` già caricato e sostituisce `minor_agent_ids` (FR-016); segnala però ai suoi proprietari la discrepanza di `adulthood_age` con il 21 inglese. In economia cambia una sola regola: sotto i 10 anni la produzione è 0; il bambino non riceve salario e la sua sopravvivenza dipende dal nucleo tramite `household_keys`. La sanificazione protegge anche l'azione economica letta al tick successivo, `buy_property`.

**Quanto costa per tick e come scala?** La selezione costa un numero di query costante (SC-001), la funzione dello stadio nessuna, la sanificazione nessuna, la produzione nessuna query in più, il percorso Celery al più una query per tick per il `World`, la chat al più due per messaggio. Le chiamate LLM del ciclo decisionale sono al più K per tick, con K = `max_protagonists` del work item prerequisito.

**Questo basta per mondi di miliardi di agenti?** No, e la spec non lo afferma. Il passo più costoso, la deliberazione LLM, diventa indipendente da N solo con il limite K del work item prerequisito; produzione, mortalità, decadimento delle memorie, `broadcast_tick` e propagazione dell'informazione restano lineari in N, e vanno riprogettati per aggregati, probabilmente con gli agenti a livelli della memoria `project_multilevel_agents.md`. Questa spec garantisce solo che il comportamento per età non aggiunga costo per agente.

**Che cosa è deterministico?** Lo stadio è una funzione pura dell'età e del template, e la selezione è deterministica dato lo stato del database, nell'ordine di priorità di `select_deliberating_agents` (a parità per id). Le risposte LLM restano non deterministiche come oggi; questo work item non peggiora la riproducibilità.

**Perché non usare una libreria di simulazione del corso di vita?** Non ne conosco una che si integri con il tick di Epocha e con i suoi template d'era senza riscrivere l'età canonica. Le regole di questa spec sono due soglie, un filtro e una sanificazione; una dipendenza esterna aggiungerebbe una seconda nozione d'età, e per la regola delle licenze dovrebbe anche essere compatibile con Apache-2.0, cosa che il pacchetto `migest`, per esempio, non è.

**Che cosa succede se il template non si carica?** La soglia adulta diventa 18, il massimo fra i template distribuiti, e l'errore è registrato a ogni risoluzione fallita, quindi più volte per tick. Il prompt di decisione non offre nessuna azione demografica e registra un avviso che nomina il template (D-29-35). È un comportamento nuovo e restrittivo, diverso da quello attuale di `decision._build_system_prompt`, che con il file mancante tiene tutte e tre le azioni demografiche, scelto perché un guasto di configurazione non deve dare capacità contrattuali a un minore né offrire una coppia di cui non si può verificare l'età matrimoniale. Togliere le azioni demografiche costa poco: senza template `run_demography_tick` ritorna prima di ogni passo, quindi nessuno risolve gli intenti di coppia e la fecondità non gira.

**Come si rispettano licenze e attribuzione?** Questa spec usa solo fatti e idee delle fonti, citati con autore, anno, titolo, URL e data di lettura, e i prompt sono scritti con parole nostre. Nessun dataset è incorporato; per quelli futuri la sezione «Licenze e attribuzione» fissa l'esito: i dati ILOSTAT sotto CC BY 4.0 sono compatibili con attribuzione, il pacchetto `migest` è GPL-3 e non può entrare nel repository, e un materiale con licenza non verificata non si incorpora finché la verifica non è scritta nella spec.

**C'è un rischio di privacy o di sicurezza?** Non entrano dati personali nuovi: età e stadio sono attributi di agenti simulati. Il frammento d'età è costruito dal server con numeri e testo fisso, non con testo dell'utente, quindi non apre una via di prompt injection nuova. La sanificazione chiude inoltre una via con cui una risposta LLM poteva far compiere a un minore atti contrattuali.

**Perché il registro preverbale della chat non è garantito?** Perché la chat delega la risposta all'LLM e il prompt è un'istruzione, non un vincolo. SC-006 misura il rispetto su 5 prove nell'ambiente reale; un filtro di post-elaborazione è una decisione di prodotto da prendere dopo aver visto quel risultato.

## Decisioni della Trinità (D-29-5)

Le domande aperte della prima stesura sono state decise il 2026-10-29 da Domenico, sotto la deroga D-29-3, con stato provvisorio fino al ritorno dell'utente.

- **T-0 e T-1 (coppie a regole, protagonisti)**: work item prerequisito separato, che porta con sé il limite K. **Decisione rifatta contro la mia raccomandazione**, che era consegnare K spento qui.
- **T-2 e T-3 (età d'inizio del lavoro, pensione)**: work item «chiavi del lavoro per era»; qui resta FR-007.
- **T-4 (soglia adulta)**: una sola soglia; fonte trovata per l'era moderna, euristica regolabile per le altre (sezione dedicata).

Non restano domande aperte dentro il perimetro di questa spec.

## Audit avversariale, round 1

Il 2026-10-29 il `critical-analyzer`, come revisore ostile, ha esaminato la prima stesura con accesso al codice del Plan 4 e al whitepaper. **Verdetto: NOT CONVERGED** (5 INCORRECT, 5 UNJUSTIFIED, il resto INCONSISTENT o MISSING). Ho verificato io stesso i rilievi bloccanti prima di correggerli.

| # | Classe | Rilievo | Correzione |
|---|---|---|---|
| 1 | INCORRECT | La FAQ affermava che chi non delibera forma coppie con un matcher a regole; le coppie nascono solo da intenti LLM, e tre template su cinque richiedono la coppia per nascere | Affermazione tolta; il limite K esce dalla spec con D-29-5 |
| 2 | INCORRECT | Il rifiuto in `apply_agent_action` non fermava `buy_property` e `hoard`, letti dal `DecisionLog` | FR-006 sanifica prima del `DecisionLog`; SC-004 verifica il tick successivo |
| 3 | UNJUSTIFIED | Zero produzione sotto i 10 anni con una citazione presa in prestito | FR-007 dichiarato euristica regolabile |
| 4 | INCORRECT | «Le simulazioni generate deliberano come prima»: il generatore crea anche bambini | Affermazione tolta; caso limite; SC-007 con un bambino generato |
| 5 | INCORRECT | Il degrado per template mancante citava un precedente inesistente | Comportamento nuovo e restrittivo, descritto senza precedente |
| 6 | INCORRECT | «L'80% di un adulto»: 0,8 è un input CES | Frase riscritta |
| 7 | INCORRECT | Picco di pensionamento attribuito all'estensione a 13 parametri | Corretto dopo una nuova lettura della pagina IUSSP |
| 8 | INCONSISTENT | Il frammento «sospendeva» regole assenti in `chat/consumers.py` | FR-010 autosufficiente |
| 9 | INCONSISTENT | Infanzia e fanciullezza senza regole diverse | Fuse |
| 10 | MISSING | La colonna `age` non scartata esplicitamente | Motivazione in FR-003; segnalazione al Plan 4 |
| 11 | MISSING | Il percorso sequenziale non chiama la demografia | Caso limite; SC-002 |
| 12 | UNJUSTIFIED | «Zero query» dove serve il `World` | Costi riscritti |
| 13 | MISSING | Doc-sync incompleto | FR-013 esteso |
| 14 | UNJUSTIFIED | OMS citata solo da fonti secondarie | Pagina OMS primaria |
| 15 | UNJUSTIFIED | «78% nel 1880» assente dal testo di Costa | Cifre lette nel capitolo 1 |
| 16 | UNJUSTIFIED | Finestra motoria OMS senza regola | Scartata |
| 17-20 | MISSING | Invarianti di SC-001, percorso legacy, bambini come bersagli, PDF IIASA | Invarianti in SC-001; FR-007a; limite noto; lacuna dichiarata |

## Audit avversariale, round 2

Il 2026-10-29 il `critical-analyzer` ha riesaminato la spec ridotta da D-29-5. **Verdetto: NOT CONVERGED** (2 INCORRECT, 3 UNJUSTIFIED, il resto INCONSISTENT o MISSING). Dei rilievi del round 1 ha trovato risolti tutti tranne il 12, parzialmente (accelerazione), e il 7, non più rilevante perché non sostiene alcuna regola. Ho verificato io stesso sul codice il rilievo più grave, il 6, e le fonti nuove, prima di correggere.

| # | Classe | Rilievo | Correzione |
|---|---|---|---|
| 1 | INCORRECT | `hoard` citato come protetto dalla sanificazione, ma nessuno stadio lo vieta | Tolto da FR-006 e dalla FAQ |
| 2 | INCORRECT | Family Law Reform Act attribuito al Regno Unito; la sezione vale per Inghilterra e Galles | Corretto ovunque |
| 3 | UNJUSTIFIED | Il 18 moderno «sostenuto» dalla Convenzione ONU, che definisce il bambino ma non fissa una maggiore età | Fonte statutaria: Family Law Reform Act 1969; la Convenzione solo come contesto; generalizzazione dichiarata |
| 4 | UNJUSTIFIED | Bande della chat: nessuna tappa a 12 mesi nella tabella, banda 4-10 e passaggio a 10 senza fonte, «frasi brevi» oltre la fonte | Ho riletto la tabella delle tappe: a 9 mesi la lallazione, a 12 un nome per il genitore; bande riscritte; 4-10 e il 10 dichiarati euristiche |
| 5 | UNJUSTIFIED | «Circa 15 token» mai misurati | Tolto; si misura in fase 5 |
| 6 | INCONSISTENT | La guardia D-29-4 esiste su `20261029-wpd-minors-decision-loop`, filtra in Python e non esclude nessuno senza demografia o con template guasto | Verificato sul ramo; la sezione sulla guardia nomina ramo, commit e funzioni e dichiara i tre comportamenti cambiati |
| 7 | INCONSISTENT | SC-001 contava solo le query e accettava un filtro in Python | SC-001 misura anche le righe lette |
| 8 | MISSING | Il rifiuto dentro `output_decision` poteva essere letto da un lettore per sottostringa | FR-006: azione sostituita per intero, rifiuto nel logger; SC-004 lo verifica |
| 9 | MISSING | SC-004 passava anche sul codice di oggi senza un acquisto realizzabile | La fixture ha una `PropertyListing` attiva e contante sufficiente |
| 10 | MISSING | Nessuna ricaduta per l'accelerazione, né la sua sorgente nel passo economico | FR-001: `_age_clock` (1,0 senza template) e `_load_simulation_template` per ogni chiamante |
| 11 | MISSING | Gli altri agenti compaiono come «(child)» nel contesto di decisione | FR-011 esteso, con `birth_tick` e `age` aggiunti al `.only` esistente |
| 12 | INCONSISTENT | La discrepanza col 21 inglese vale anche per `pre_industrial_christian`, calibrato sull'Inghilterra 1700-1749 | Blackstone (1765) verificato sul testo primario (Avalon Project); calibrazioni citate; discrepanza estesa |
| 13 | INCONSISTENT | «15 anni lunari» presentato come unica posizione | Le scuole non concordano; WikiShia letta e citata |
| 14 | MISSING | URL generici per la riga sul *bulugh* | URL esatto nella tabella dei riferimenti |
| 15 | INCONSISTENT | «Coppia: Sì» per l'adulto, mentre in `industrial` l'età matrimoniale maschile è 18 | Cella corretta |
| 16 | MISSING | FR-014 senza criterio né test | SC-009 sul confronto dello schema API |

Rilievo segnalato fuori perimetro: il riconoscimento di `hoard` per sottostringa in `economy/engine.py` è un difetto preesistente, registrato fra i limiti noti.

## Audit avversariale, round 3

Il 2026-10-29 il `critical-analyzer` ha riesaminato la spec dopo il round 2, rileggendo di persona Blackstone, il Family Law Reform Act, WikiShia, la tabella di Zubler e le calibrazioni del whitepaper, e il codice del ramo `20261029-wpd-minors-decision-loop`. **Verdetto: NOT CONVERGED** (2 INCORRECT, 1 UNJUSTIFIED di peso basso, il resto INCONSISTENT o MISSING). Dei rilievi del round 2 ha trovato risolti 1, 2, 3, 5, 6, 8, 12-15, e parzialmente 4, 7, 9, 10, 11, 16; le parti mancanti sono i rilievi qui sotto. Ho verificato sul codice il rilievo 1 (`_tick_duration_hours` chiama `_world_of`, che esegue una query) e il rilievo 11 (`world/election.py` raccoglie come elettori tutti i vivi).

| # | Classe | Rilievo | Correzione |
|---|---|---|---|
| 1 | INCORRECT | `_age_clock` legge il `World` a ogni chiamata: usato per agente, aggiunge una query per agente e per tick | FR-001: la durata del tick viene dal `World` già caricato; `_age_clock` va esteso per accettarlo; SC-001 verifica che le query per agente non cambino |
| 2 | INCORRECT | «Registrato una volta per tick»: `_load_simulation_template` registra a ogni risoluzione fallita | Caso limite e FAQ descrivono il comportamento reale, con la ragione per non deduplicare |
| 3 | UNJUSTIFIED | Date «dal 1970» e «fino al 1969» non presenti nella fonte | Date tolte; resta ciò che la sezione dice |
| 4 | INCONSISTENT | La premessa «inglese perché calibrato sull'Inghilterra» non vale per l'era islamica né per quella moderna | Il diritto di confronto è dichiarato scelta rappresentativa per era, con la ragione per ciascuna |
| 5 | MISSING | La fixture di SC-004 non elencava tutti i requisiti di `process_property_listings`, e un tick completo passerebbe per via della guardia D-29-4 | SC-004 chiama direttamente le due funzioni, elenca i requisiti e aggiunge un caso di controllo |
| 6 | MISSING | SC-001 senza metodo per contare le righe | Righe restituite contate con `connection.execute_wrapper` |
| 7 | INCONSISTENT | FR-011 copriva una sola delle due query «nome (ruolo)» | Coperte entrambe |
| 8 | INCONSISTENT | La User Story della chat diceva ancora «frasi brevi» | Allineata a FR-009 |
| 9 | INCONSISTENT | Costo della chat sottostimato | Al più due query per messaggio |
| 10 | MISSING | SC-009 presupponeva uno schema OpenAPI che il progetto non genera | Confronto con un elenco di campi congelato nel test |
| 11 | MISSING | Le elezioni contano i neonati come elettori | Limite noto, rinviato |
| 12 | INCONSISTENT | La fonte sul *bulugh* mostra disaccordo fra giuristi sciiti, non fra scuole | Formulazione ristretta a ciò che la fonte dice |


## Audit avversariale, round 4

Il 2026-10-29 il `critical-analyzer` ha riesaminato i passaggi corretti nel round 3. **Verdetto: NOT CONVERGED** (1 INCORRECT, 0 UNJUSTIFIED). Ha trovato risolti tutti e dodici i rilievi del round 3, con tre residui ripresi qui sotto. Ho verificato sul codice il rilievo 1 (`economy/engine.py`, passo 8c: `world = simulation.world`) e il rilievo 4 (`demography/migration.py`, intestazione del docstring di `coordinate_family_migration`).

| # | Classe | Rilievo | Correzione |
|---|---|---|---|
| 1 | INCORRECT | FR-007 diceva che il passo economico non carica il `World`, e ne stimava una query in più; lo carica già una volta per tick | FR-007: la lettura si sposta prima del ciclo sulle zone, nessuna query nuova; SC-003 «non supera quello di prima» |
| 2 | INCONSISTENT | Sul percorso Celery la selezione non ha un `World`, e leggerlo dentro la funzione rompe l'uguaglianza delle righe di SC-001 | FR-003: il `World` è passato dal chiamante; `run_simulation_loop` lo legge una volta per tick, con il costo dichiarato |
| 3 | MISSING | Metodo per contare le righe non documentato | SC-001: `context["cursor"].rowcount` diverso da -1, con controllo incrociato sulla lunghezza del risultato |
| 4 | INCONSISTENT | Il docstring «MINORS ARE NOT CALLED TO THE DECISION LOOP» di `migration.py` diventa falso nell'intestazione | Nuovo FR-016: intestazione riformulata, §4.1.5 dichiarato invariato; anche l'estensione di `_age_clock` porta l'obbligo del doc-sync per il §4.1.0; FAQ corretta |
| 5 | MISSING | Elezioni e `hoard` senza voce di rinvio né riferimento | Rinvii 7 e 8, da aprire sulla build map |
| 6 | MISSING | Il ruolo «(child)» resta nei prompt delle fazioni e nel `__str__` di `Agent` | Rinvio 9 |
| 7 | INCONSISTENT | Scadenza delle `PropertyListing` sbagliata di un tick nella fixture; asserzione sui prestiti vacua | SC-004: `listed_at_tick > tick - 9`; prestiti solo come guardia di regressione |

## Audit avversariale, round 5

Il 2026-10-29 il `critical-analyzer` ha riesaminato i passaggi corretti nel round 4. **Verdetto: NOT CONVERGED** (1 INCORRECT, 0 UNJUSTIFIED). Ha trovato risolti i rilievi 1, 2, 3, 5, 6 e 7 del round 4 e parzialmente il 4; ha confermato che `rowcount` è affidabile per le SELECT con psycopg 3 e Django 5.1. Ho verificato sul codice i rilievi 1 (docstring di `coordinate_family_migration`) e 3 (`try/except Exception: pass` intorno a `world = simulation.world`).

| # | Classe | Rilievo | Correzione |
|---|---|---|---|
| 1 | INCORRECT | Anche il corpo del docstring di `migration.py` diventa falso: attribuisce all'orchestratore il compito di non offrire `move_to` ai minori | FR-016 riscrive intestazione e frase sul responsabile |
| 2 | MISSING | La soglia dei 10 anni calcolata due volte (filtro SQL e `age_in_years` in virgola mobile) può dare verdetti diversi al confine | Nuovo FR-001b: un solo confronto su `birth_tick`; `age_in_years` solo per mostrare l'età; nuovo SC-010 su un mondo settimanale |
| 3 | MISSING | Spostare la lettura del `World` nell'economia fuori dall'except cieco senza dire che cosa succede se manca | FR-007: ricaduta su 24,0 ore con avviso, fuori dall'except; except preesistente nel rinvio 10 |
| 4 | INCONSISTENT | Sul percorso Celery il `World` è di solito già in cache dopo il passo economico | FR-003: al più una query per tick, con il caso che la paga |
| 5 | INCONSISTENT | La rimozione di `minor_agent_ids` da `orchestrator.py` non portava l'obbligo del doc-sync per il §4.1.0 | FR-016 copre ogni modifica a `orchestrator.py`; FAQ corretta |
| 6 | MISSING | §3.3 del whitepaper (contratti fra moduli) non era nel doc-sync | FR-013 aggiunge §3.3 |

## Audit avversariale, round 6

Il 2026-10-29 il `critical-analyzer` ha riesaminato i passaggi corretti nel round 5. **Verdetto: NOT CONVERGED** (1 INCORRECT, 0 UNJUSTIFIED). Ha trovato risolti i rilievi 1, 3, 4, 5 e 6 del round 5 e parzialmente il 2; ha confermato che `World.simulation` è uno-a-uno e che il passo economico legge `simulation.world` sullo stesso oggetto prima della selezione. Ha misurato che, con le soglie distribuite, il confronto in virgola mobile e quello su `birth_tick` non divergono, e divergono a 63 anni su un mondo settimanale; non ho ripetuto la misura e la riporto come sua.

| # | Classe | Rilievo | Correzione |
|---|---|---|---|
| 1 | INCORRECT | SC-010 chiedeva di far fallire il test calcolando lo stadio con `age_in_years`, che con le soglie distribuite non diverge mai: il controllo non poteva fallire | SC-010: mutazione di un carattere (`<` al posto di `<=`) rilevata dai punti a ±1 tick; un secondo test fissa il caso dei 63 anni; FR-001b motivato come garanzia strutturale, con la misura riportata |
| 2 | INCONSISTENT | La sezione sugli stadi diceva lo stadio derivato da `age_in_years` | Riscritta: limiti su `birth_tick` |
| 3 | INCONSISTENT | «In un solo modo» smentito da `household_keys` e `inheritance.py` | FR-001b limitato a questo work item; i due confronti della demografia dichiarati fuori perimetro |
| 4 | INCONSISTENT | La chat passava al registro esistente a 10 anni con l'età mostrata | FR-009: il passaggio si decide con la funzione dello stadio |
| 5 | MISSING | Nessun `birth_tick` intero cade esattamente sul limite in un mondo settimanale | Punti di prova floor(L) - 1, floor(L), ceil(L), ceil(L) + 1 |
| 6 | MISSING | L'eccezione della ricaduta su 24,0 ore non era nominata, né il caso di durata nulla o zero | FR-007: solo `World.DoesNotExist`; durata nulla o zero ricade anch'essa |

Ho anche corretto il riferimento al «62,999 per 63»: il passaggio è nel §4.1.0 del ramo `20261029-wpd-minors-decision-loop`, non ancora nel whitepaper di questo ramo.

## Audit avversariale, round 7

Il 2026-10-29 il `critical-analyzer` ha riesaminato i passaggi corretti nel round 6. **Verdetto: NOT CONVERGED** (1 INCORRECT, 0 UNJUSTIFIED). Ha trovato risolti i rilievi 2, 3, 4, 5 e 6 del round 6; ha ripetuto la misura del round 6 e confermato il caso dei 63 anni sul mondo settimanale.

| # | Classe | Rilievo | Correzione |
|---|---|---|---|
| 1 | INCORRECT | Su un mondo settimanale i limiti in tick non sono interi, quindi la mutazione `<` al posto di `<=` è equivalente e il test non poteva fallire | SC-010: parte giornaliera con limiti interi (3650, 5840, 6570 tick) che rileva la mutazione; la parte settimanale resta come prova d'accordo |
| 2 | INCONSISTENT | FR-001b escludeva `age_in_years` da ogni soglia, mentre FR-009 lo usa per le bande sotto i 10 anni | FR-001b ristretto alle soglie dei 10 anni e di `adulthood_age` |
| 3 | MISSING | Banda della chat indefinita se lo stadio è ancora infanzia ma l'età mostrata arriva a 10 | FR-009: dentro lo stadio, da 4 anni in su vale la banda 4-10 |

## Audit avversariale, round 8

Il 2026-10-29 il `critical-analyzer` ha verificato le tre correzioni del round 7 e ha ripetuto i calcoli: su un mondo giornaliero i limiti sono esattamente 3650, 5840 e 6570 tick e il punto a distanza L distingue `<` da `<=` per tutte e tre le soglie; su un mondo settimanale i limiti non sono interi; il caso dei 63 anni regge; la misura del round 6 non trova divergenze per 10, 16 e 18 anni a nessuna durata intera del tick fra 1 e 8760 ore. **Verdetto: CONVERGED**: nessun INCORRECT e nessun UNJUSTIFIED.

Ha segnalato un solo rilievo INCONSISTENT minore, non bloccante: la regola delle bande copriva lo stadio infanzia con un'età mostrata di 10, ma non il caso simmetrico di un adolescente con un'età mostrata di 9,999. L'ho chiuso con una frase in FR-009; la correzione non introduce regole nuove e non è stata ri-auditata.

## Chiarimenti

### D-29-22 — il prerequisito possiede la funzione di selezione

Il 2026-10-29 ho chiarito tre punti dopo la stesura della spec delle coppie a regole, senza cambiare il modello. Primo, la funzione che FR-003 chiama «una sola funzione» è `select_deliberating_agents` di `agents/deliberation.py`, creata dal work item prerequisito: questa spec la estende (sostituisce `minor_agent_ids` con il filtro SQL su `birth_tick` e aggiunge il parametro `World`) e non ne crea una seconda. Secondo, la selezione mantiene l'ordine di priorità di quella funzione e non l'ordine per id (FR-003 e FAQ sul determinismo). Terzo, le affermazioni di O(N) chiamate LLM erano vere solo senza il limite: con il prerequisito consegnato sono al più K per tick, con K = `max_protagonists` (perimetro, costo, Known Limitations e FAQ sul costo).

### D-29-35 — emendamento dopo il piano

Il 2026-10-29, scrivendo il piano, ho trovato quattro punti in cui la spec non corrispondeva al codice del Plan 4 o lasciava una scelta aperta (domande Q-1, Q-2, Q-3 e Q-4 di `plan.md`). La Trinità li ha decisi con la decisione D-29-35, provvisoria fino al ritorno dell'utente.

- **Q-1, seconda parte di SC-010.** La premessa era falsa: dal round 15 del gate di fase 6 del Plan 4 `age_in_years` legge esattamente 63,0 a 3285 tick settimanali, non 62,999.... Ho ricalcolato il valore (63,0, con il limite per 63 anni a 3285 tick; con la vecchia forma a due divisioni 62,99999999999999 e 3286) e ho riscritto la seconda parte di SC-010 perché asserisca il comportamento attuale con valori letterali e fallisca sotto la mutazione nominata; FR-001b è riallineato.
- **Q-2, template non risolvibile.** Resta la lettura del piano (PD-10): nessuna azione demografica nel prompt, più un avviso nel log che nomina il template (FR-005 e caso limite).
- **Q-3, chat di gruppo.** Nel perimetro: `describe_speaker` serve già tre prompt, compreso quello della chat di gruppo (perimetro, User Story 3, FR-009, FR-010, SC-005).
- **Q-4, frase superata.** Il frammento d'età è già in `chat/consumers.py` dal commit `430dfa6` del Plan 4 (nella chat di gruppo dal `02a1d47`), e la guardia D-29-4 è integrata nel ramo del Plan 4 dal merge `c1e8569`: ho corretto la sezione «Relazione con la guardia del Plan 4» e la premessa del «Perché».

Nessuna delle quattro correzioni cambia il modello scientifico, le soglie o le fonti. L'audit avversariale del delta è registrato in `checklists/delta-audit-d29-35.md`: NOT CONVERGED al round 1 (quattro INCORRECT, tutti corretti), **CONVERGED al round 2**.

## Stato del gate

L'audit avversariale di fase 2 è **CONVERGED in 8 round**. Il gate di fase 2 si chiude con l'approvazione della Trinità sotto la deroga D-29-3 e il rapporto all'utente al ritorno. Prima della fase 5 restano tre condizioni: il merge del Plan 4 con la guardia di D-29-4, il riallineamento del ramo, e l'apertura sulla build map dei due work item separati di D-29-5 e dei rinvii 7-10.

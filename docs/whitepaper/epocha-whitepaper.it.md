---
title: "Epocha — Un Simulatore di Civiltà Scientificamente Fondato"
authors: ["Maurizio Mocci"]
affiliation: "Independent project"
date: "2026-04-26"
version: "0.1"
frozen-at-commit: "8a2bc714477f445b46cd610725df40c93fce1557"
license: "Apache 2.0"
---

# Epocha — Un Simulatore di Civiltà Scientificamente Fondato

## Abstract

Epocha è un simulatore di civiltà open-source che combina la modellazione ad
agenti su larga scala con una cognizione guidata da LLM, sotto l'ambizione
multi-scala e di lungo orizzonte della psicostoriografia di Asimov. Il
progetto affronta un divario fra due tradizioni di ricerca contigue: i
microsimulatori demografici ed economici consolidati supportano popolazioni
di milioni di individui su decenni ma si basano su agenti rule-based privi
di personalità persistente, memoria episodica e deliberazione in linguaggio
naturale, mentre le recenti simulazioni con agenti LLM dotano gli agenti di
cognizione ricca ma operano su piccoli gruppi, orizzonti brevi e ambienti
stilizzati senza un sostrato demografico o economico sottostante. Il
whitepaper documenta l'architettura del sistema (motore di tick, pipeline di
decisione dell'agente, strategia RNG, adattatore di provider LLM, sostrato
economico, modello di persistenza, dashboard e strato di chat), i moduli
scientifici auditati — mortalità di Heligman-Pollard, fertilità Hadwiger
con Becker, formazione di coppia Gale-Shapley con Goode 1963, aspettative
adattive Cagan-Nerlove, credito e banca Diamond-Dybvig, mercato
immobiliare ancorato a Gordon, reputazione Castelfranchi-Conte-Paolucci,
propagazione del passaparola Bartlett-Allport-Postman (information flow,
distortion, belief filter, affinity), il cluster delle istituzioni
politiche (government, government_types, institutions, stratification,
election), il movimento e le fazioni — un layer base dell'economia
auditato che copre la produzione CES, il clearing con tâtonnement
Walrasiano, una partizione conservativa dei redditi da fattori e la
diagnostica di conservazione di Fisher — e un sottosistema implementato
in codice ma in attesa dell'audit scientifico avversariale
(knowledge graph). Ogni formula, parametro e
algoritmo nei capitoli auditati è citato a una fonte primaria; le tabelle
di calibrazione sono presentate per template di era e consolidate
nell'Appendice A; la metodologia di validazione specifica dataset, metriche
e soglie di accettazione contro cui il Plan 4 eseguirà la campagna
empirica. L'infrastruttura di riproducibilità si fonda su template di era,
stream RNG seedati per fase, riferimenti frozen-at-commit e un whitepaper
scientifico bilingue mantenuto come documento vivente. Il progetto è
rilasciato sotto Apache 2.0, con un workflow di sviluppo canonico in sette
fasi e audit avversariali obbligatori che gattano ogni merge sul branch di
sviluppo.

## Parole chiave

modellazione ad agenti, scienze sociali computazionali, microsimulazione
demografica, modelli economici ad agenti, large language models,
simulazione sociale, psicostoriografia, sistemi di reputazione

## Struttura del documento e legenda di stato

Questo documento distingue tre livelli di maturità per ciascun sottosistema:

- **Auditato (CONVERGENTE)** — capitoli in §4 Metodi. L'audit scientifico
  avversariale ha raggiunto la convergenza sulla spec o sul codice
  sottostante. Per ogni modulo sono forniti background, modello, equazioni,
  parametri con citazioni a fonti primarie, algoritmo, semplificazioni e un
  header di stato.
- **Implementato, audit pendente** — capitoli in §8 Sottosistemi
  Progettati. Il modulo esiste nel codice ma non ha ancora completato il
  ciclo di convergenza della policy di audit avversariale del progetto.
  Ogni voce è un paragrafo di 5-10 frasi con il link alla spec di design.
- **Specificato o pianificato** — elencato in §9 Roadmap come bullet breve.

Gli header di stato in §4 usano la forma:
> Stato: implementato a partire dal commit `<hash>`, audit della spec CONVERGENTE `<data>`.

---

## Indice

1. Introduzione
2. Background e lavori correlati
3. Architettura del sistema
4. Metodi — Moduli auditati
5. Implementazione
6. Calibrazione
7. Metodologia di validazione
8. Sottosistemi progettati (implementati, audit pendente)
9. Roadmap
10. Discussione
11. Limitazioni note
12. Conclusioni
13. Riferimenti
14. Appendici

---

# 1. Introduzione

## 1.1 Contesto

Questo documento introduce Epocha, un simulatore di civiltà open-source che
combina la modellazione ad agenti su larga scala con il decision-making
guidato da LLM, modelli demografici ed economici fondati sulla letteratura
pubblicata e uno strato di interazione multi-livello. La nozione di
*psicostoriografia* — una scienza quantitativa capace di prevedere la
traiettoria di grandi popolazioni anche quando il comportamento individuale
resta imprevedibile — è stata introdotta come concetto di finzione da
Asimov nella saga della *Fondazione* (Asimov 1951). È rimasta un'idea
romanzesca, ma l'intuizione sottostante — che le dinamiche sociali
aggregate ammettano un trattamento formale — è stata perseguita per
decenni da tradizioni di ricerca complementari nelle scienze sociali
computazionali. I modelli di segregazione di Schelling hanno mostrato che
pattern macroscopici molto netti possono emergere da regole individuali
strettamente locali (Schelling 1971). La modellazione ad agenti è maturata
come metodologia con il lavoro Sugarscape di Epstein e Axtell, che ha
inquadrato le scienze sociali "dal basso verso l'alto" facendo crescere
società artificiali all'interno di un sostrato computazionale controllato
(Epstein e Axtell 1996). Sei anni dopo, Bonabeau ha consolidato la
modellazione ad agenti come tecnica generale per la simulazione di sistemi
umani e ha tracciato le condizioni in cui aggiunge valore rispetto agli
approcci basati su equazioni (Bonabeau 2002).

Una seconda linea di lavoro, più recente, è emersa con i large language
model. Dotando gli agenti di cognizione guidata da LLM, studi recenti hanno
dimostrato che popolazioni sintetiche possono riprodurre pattern
comportamentali non banali osservati in campioni umani (Argyle et al. 2023)
e che piccole comunità di agenti generativi possono esibire dinamiche
sociali credibili — formazione di memoria, riflessione, pianificazione e
coordinamento inter-agente — su orizzonti simulati brevi (Park et al.
2023). Epocha si colloca all'intersezione di queste due linee: eredita
l'ambizione multi-scala e di lungo orizzonte della simulazione sociale ad
agenti classica e adotta la cognizione guidata da LLM per arricchire il
decision-making degli agenti con personalità, memoria e deliberazione in
linguaggio naturale.

## 1.2 Gap di ricerca affrontato

Le simulazioni ad agenti guidate da LLM esistenti si concentrano su piccoli
gruppi di agenti su orizzonti simulati brevi (giorni o settimane di tempo
simulato, al massimo decine di agenti), e operano tipicamente in ambienti
deliberatamente stilizzati senza un sostrato demografico o economico
sottostante. Viceversa, i microsimulatori demografici ed economici
consolidati supportano popolazioni di milioni di individui su decenni o
secoli, ma i loro agenti sono rule-based: mancano di personalità
persistente, memoria episodica e capacità di ragionamento in forma libera
che distingue il decision-making umano. Epocha mira al divario fra queste
due tradizioni. Il suo obiettivo è la simulazione multi-scala e di lungo
orizzonte di popolazioni i cui agenti individuali combinano dinamiche
demografiche ed economiche pubblicate con cognizione guidata da LLM ricca
di personalità, restando al contempo auditabile, riproducibile e fondata
su fonti scientifiche primarie.

## 1.3 Contributi

Questo whitepaper e la codebase open-source che lo accompagna contribuiscono
quanto segue:

- Un simulatore di civiltà open-source end-to-end che integra la
  microsimulazione demografica ed economica con la cognizione guidata da
  LLM degli agenti sotto una licenza permissiva.
- Un whitepaper scientifico bilingue (inglese e italiano) mantenuto come
  documento vivente e congelato a ogni merge sul branch di sviluppo, con
  ogni formula, parametro e algoritmo citato a una fonte primaria.
- Un workflow di sviluppo canonico in sette fasi con audit scientifici
  avversariali obbligatori che devono raggiungere convergenza esplicita
  prima che qualunque modulo scientifico sia mergiato.
- Un'infrastruttura di riproducibilità costruita su template di era,
  generazione pseudo-casuale di numeri seedata e riferimenti
  frozen-at-commit, in modo che ogni risultato riportato possa essere
  rigenerato da uno stato noto.
- Un'architettura modulare in cui moduli auditati (attualmente mortalità,
  fertilità e formazione di coppia demografiche) e moduli
  progettati-ma-non-auditati coesistono dietro header di stato espliciti,
  permettendo al lettore di distinguere la scienza convergente dal lavoro
  in corso.

## 1.4 Struttura del documento e legenda di stato

Questo whitepaper completa la legenda di maturità introdotta nel
frontespizio (cfr. *Struttura del documento e legenda di stato* sopra) con
riferimenti incrociati espliciti in ciascun capitolo. Il Capitolo 2 passa
in rassegna i lavori correlati nella modellazione ad agenti, nella
simulazione guidata da LLM, nella microsimulazione demografica, nei
modelli economici ad agenti e nella reputazione e diffusione
dell'informazione. Il Capitolo 3 descrive l'architettura del sistema:
motore di tick, pipeline di decisione dell'agente, contratti di
integrazione cross-modulo, strategia RNG, adattatore di provider LLM,
sostrato economico, modello di persistenza e strato di interazione. Il
Capitolo 4 contiene i metodi auditati, con una sezione per ciascun modulo
convergente. Il Capitolo 5 documenta l'implementazione — layout del
repository, mappatura modulo-spec, dettagli di persistenza. Il Capitolo 6
copre la calibrazione (tabelle di parametri, template di era, procedure di
fitting) e il Capitolo 7 la metodologia di validazione (dataset target,
metriche di confronto, soglie di accettazione, comandi di riproducibilità,
stato). Il Capitolo 8 elenca l'unico sottosistema che è implementato ma
il cui audit avversariale è ancora pendente. Il Capitolo 9 espone la roadmap,
il Capitolo 10 discute scope e scelte di design, il Capitolo 11 cataloga
le limitazioni note, il Capitolo 12 conclude. Il Capitolo 13 raccoglie
tutti i riferimenti e il Capitolo 14 contiene le appendici (tabelle di
parametri, istruzioni di riproducibilità, schema dei template di era).

---

# 2. Background e lavori correlati

## 2.1 Modellazione ad agenti delle società

La genealogia della modellazione ad agenti sociale (ABM) precede il termine
stesso. Schelling ha dimostrato che lievi preferenze individuali sulla
composizione del vicinato si aggregano in una netta segregazione
residenziale, un primo esempio di pattern sociale macroscopico che emerge
da regole di interazione locali (Schelling 1971). I tornei di Axelrod sul
Dilemma del Prigioniero iterato hanno mostrato che strategie cooperative
possono essere evolutivamente stabili in popolazioni di agenti egoisti,
stabilendo la simulazione come strumento legittimo di indagine
teorico-sociale accanto alla dimostrazione formale e all'osservazione
empirica (Axelrod 1984). Con Sugarscape, Epstein e Axtell hanno
argomentato a favore di una metodologia generativa — "se non l'hai fatta
crescere, non l'hai spiegata" — e hanno prodotto la prima dimostrazione
ampiamente citata che demografia, commercio, conflitto e trasmissione
culturale potessero essere studiati all'interno di un'unica società
artificiale (Epstein e Axtell 1996). Bonabeau ha poi consolidato la
metodologia e identificato le condizioni in cui l'ABM aggiunge valore
rispetto agli approcci basati su equazioni: agenti eterogenei,
non-linearità e struttura spaziale o di rete esplicita (Bonabeau 2002).

La maturazione dell'ABM come disciplina è coincisa con la comparsa di
piattaforme di modellazione di uso generale. NetLogo è diventato uno
standard de facto per la didattica e i modelli di piccola e media scala
grazie al suo linguaggio accessibile e all'estesa libreria di modelli
(Wilensky 1999). Mesa ha portato un workflow comparabile nello stack
scientifico Python ed è sempre più usato dove i modelli devono
interoperare con librerie statistiche e di machine learning (Masad e
Kazil 2015). Repast HPC ha esteso la famiglia Repast a cluster a memoria
distribuita, abilitando popolazioni abbastanza grandi da avvicinarsi a
domande di scala demografica (Collier e North 2013). Queste piattaforme,
tuttavia, condividono un'assunzione implicita secondo cui il
decision-making degli agenti è rule-based — un insieme finito di
condizioni e azioni, possibilmente stocastiche, ma in ultima analisi
leggibili come codice. Epocha si colloca come simulatore ad agenti
multi-scala e di lungo orizzonte che mantiene questa impalcatura
rule-based per le dinamiche demografiche ed economiche e inserisce un
modulo di decisione guidato da LLM dove personalità, deliberazione
narrativa e ragionamento in forma libera sono essenziali.

## 2.2 Simulazioni guidate da LLM e ruolo della personalità

Una seconda linea di lavoro, molto più recente, usa i large language model
come sostrato cognitivo di agenti simulati. Park e colleghi hanno
introdotto agenti generativi nell'ambiente di Smallville, in cui 25
personaggi guidati da LLM mantenevano memory stream, riflessioni periodiche
e piani, e sono stati osservati coordinarsi localmente su brevi orizzonti
simulati come l'organizzazione di una festa di San Valentino (Park et al.
2023). Argyle et al. hanno proposto di trattare gli LLM come un "campione
di silicio" di rispondenti umani, mostrando che, opportunamente
condizionati su backstory demografiche, GPT-3 riproduce distribuzioni di
risposta non banali tratte dai sondaggi degli American National Election
Studies (Argyle et al. 2023). Aher, Arriaga e Kalai hanno generalizzato
l'approccio con la nozione di Turing Experiment, un protocollo empirico in
cui un LLM è chiamato a replicare il lato del partecipante in studi
psicologici noti; i loro risultati indicano che diversi effetti classici
(offerte nel gioco dell'ultimatum, pattern di obbedienza alla Milgram,
aggregazione Wisdom-of-Crowds) sono recuperati in misura misurabile (Aher
et al. 2023). In tutti questi studi il ruolo della *personalità* —
veicolata via persona suggerita, backstory demografica o vettore esplicito
di tratti psicometrici — appare come una leva primaria sulla diversità e
plausibilità del comportamento dell'agente. Il condizionamento sui tratti
Big Five è la scelta più diffusa, sia per la sua standardizzazione in
psicologia sia per la sua compattezza come input a cinque dimensioni.

Gli stessi studi mettono in luce i limiti della simulazione guidata da LLM.
La cognizione eredita le tendenze all'allucinazione e la sensibilità al
prompt del modello sottostante; la qualità del ragionamento degrada con la
lunghezza del contesto; il costo scala con la dimensione della popolazione
e l'orizzonte simulato, rendendo proibitive economicamente run di un
secolo a scala di popolazione senza un caching aggressivo. La
riproducibilità è anche fragile, dato che le versioni dei modelli
evolvono e la stocasticità di campionamento è raramente controllabile in
modo completo. Epocha mitiga questi vincoli con un'architettura in cui le
chiamate LLM sono confinate alle decisioni circoscritte in cui il
ragionamento in forma libera è genuinamente richiesto, mentre le
transizioni demografiche, la contabilità economica e il matching sono
gestite da servizi rule-based auditati descritti nel Capitolo 4. Una cache
di reputazione e memoria (Castelfranchi et al. 1998) riduce la deriva di
contesto attraverso i tick fornendo agli agenti un sostrato episodico
strutturato a cui possono fare riferimento invece di ri-derivare da zero
le informazioni sociali. La riproducibilità è imposta al confine della
simulazione attraverso generazione pseudo-casuale di numeri seedata,
template di era congelati al commit e logging delle chiamate a livello di
provider documentato nel Capitolo 3.

## 2.3 Microsimulazione demografica

La modellazione demografica spazia su tre registri metodologici. La
macro-demografia opera su coorti aggregate via equazioni alle differenze o
tavole di vita e rimane il cavallo di battaglia degli uffici nazionali di
statistica. La microsimulazione segue gli individui attraverso eventi di
vita campionati da intensità di transizione stimate ed è emersa nel tardo
ventesimo secolo come risposta naturale a domande — reti di parentela,
composizione familiare, disuguaglianza longitudinale — a cui i modelli
aggregati non possono rispondere (van Imhoff e Post 1998; Spielauer
2011). La linea SOCSIM di Berkeley ha aperto il campo con uno studio di
microsimulazione sui tabù dell'incesto e ha dimostrato che la modellazione
stocastica a livello individuale poteva fornire risultati demografici
sostanziali (Hammel et al. 1979); successive implementazioni open-source
come MicSim hanno portato la microsimulazione a tempo continuo
nell'ecosistema R e codificato un workflow generico di event-history (Zinn
2013). La demografia ad agenti, il terzo registro, incorpora le stesse
transizioni a livello individuale all'interno di un sostrato
comportamentale dove le decisioni su unione, fertilità e migrazione
co-evolvono col resto della società simulata invece di essere estratte da
schedule esogene. La genealogia delle forme funzionali sottostanti è ben
stabilita: Gompertz ha introdotto la legge esponenziale della mortalità in
età adulta (Gompertz 1825), Heligman e Pollard hanno poi proposto una
decomposizione additiva a otto parametri che cattura componenti infantili,
del picco da incidenti e senescenti in un'unica schedule (Heligman e
Pollard 1980), Coale e Trussell hanno formalizzato schedule di fertilità
modello indicizzate dal comportamento di spaziatura e di interruzione
(Coale e Trussell 1974), Hadwiger aveva precedentemente offerto una
forma analitica compatta per i tassi di fertilità per età (Hadwiger 1940),
e Hajnal ha caratterizzato il pattern di matrimonio europeo che motiva
gran parte della ricerca contemporanea sulla nuzialità (Hajnal 1965).

Epocha si colloca nel registro ad agenti. La mortalità è implementata
attraverso la schedule auditata di Heligman-Pollard con parametri specifici
per era, la fertilità usa un tasso per età di Hadwiger modulato da
trade-off quantità-qualità alla Becker e da un soffitto malthusiano di
capacità portante, e la formazione di coppia usa un matching di
Gale-Shapley con funzioni di preferenza alla Goode (cfr. Capitolo 4 per
la specifica completa dei Metodi). La letteratura sulla microsimulazione
fornisce gli obiettivi di validazione — residui delle tavole di vita,
total fertility rate per coorte, distribuzioni dell'età al primo matrimonio
— contro cui i moduli auditati sono calibrati, mentre l'inquadramento ad
agenti fornisce l'integrazione con lo stato economico e comportamentale
che i microsimulatori puramente demografici non offrono.

## 2.4 Modelli economici ad agenti

La modellazione macroeconomica ad agenti è maturata negli anni 2000 come
risposta ai limiti percepiti dei modelli dynamic stochastic general
equilibrium ad agente rappresentativo. EURACE ha assemblato una
piattaforma ad agenti eterogenei a scala continentale con popolazioni
esplicite di famiglie, imprese, banche e governo, progettata per studiare
canali di credito e trasmissione di policy senza imporre l'equilibrio ex
ante (Deissenberg et al. 2008). JAMEL ha introdotto esperimenti di
flessibilità salariale all'interno di un modello ad agenti con creazione
di moneta endogena, fornendo un controesempio numerico all'affermazione
classica secondo cui la flessibilità salariale stabilizza incondizionatamente
l'occupazione (Seppecher 2012). La famiglia Mark0 di modelli macroeconomici
stilizzati, al contrario, ha deliberatamente spogliato il dettaglio
istituzionale per esporre tipping point e transizioni di fase nel
comportamento economico collettivo, trattando la macroeconomia come un
sistema complesso nel senso della fisica statistica (Gualdi et al. 2015).
La forza di queste piattaforme è la capacità di generare dinamiche
fuori-equilibrio — cicli economici endogeni, recessioni di bilancio,
comportamenti di coda distributiva — da interazioni eterogenee; la
debolezza ricorrente è la calibrazione e l'identificazione, dato che lo
spazio dei parametri è vasto e le serie storiche macroeconomiche
disponibili sono brevi rispetto alla ricchezza comportamentale offerta.

L'economia comportamentale fornisce primitive complementari che si sono
rivelate abbastanza durature da essere riutilizzate fra famiglie di
modelli. Le aspettative adattive di Cagan rimangono il modo non banale
più semplice di dare agli agenti una previsione backward-looking che
converge sotto regimi stabili e amplifica gli shock altrimenti (Cagan
1956). Il modello Diamond-Dybvig di banca sotto sequential service espone
l'equilibrio di run che le passività liquide a breve termine che finanziano
asset illiquidi non possono evitare senza un dispositivo esterno di
commitment, e motiva la modellazione esplicita delle garanzie sui depositi
e del comportamento di prestatore di ultima istanza (Diamond e Dybvig
1983). L'ipotesi di instabilità finanziaria di Minsky inquadra
l'accumulo endogeno di fragilità durante le espansioni tranquille
prolungate ed è il riferimento canonico per la modellazione del credito
sensibile al ciclo (Minsky 1986). Lo strato economico del Plan 2 di
Epocha si posiziona all'interno di questa genealogia: riusa l'impegno
EURACE/JAMEL verso bilanci eterogenei e clearing fuori-equilibrio, adotta
le aspettative adattive di Cagan per la previsione dell'inflazione,
istanzia un nucleo bancario Diamond-Dybvig con riserve frazionarie ed è
strutturato per ammettere indicatori di ciclo alla Minsky come
estensione. La specifica completa dei Metodi per l'integrazione
comportamentale è nel Capitolo 4.

## 2.5 Reputazione e diffusione dell'informazione nei MAS

La reputazione è il costrutto socio-cognitivo che permette agli agenti di
agire su informazioni di seconda mano riguardo a partner con cui non
hanno interagito direttamente, ed è fondante per la cooperazione nei
sistemi multi-agente aperti. Conte e Paolucci hanno fornito il trattamento
teorico consolidato, distinguendo l'immagine (una credenza valutativa
privata) dalla reputazione (l'oggetto sociale che circola attraverso il
gossip e che sostiene l'enforcement delle norme) (Conte e Paolucci 2002).
La precedente formulazione di Castelfranchi, Conte e Paolucci ha
analizzato come la reputazione normativa abbassi il costo della
conformità e fornisca un meccanismo endogeno di ordine sociale
(Castelfranchi et al. 1998). La diffusione dell'informazione è adiacente
alla reputazione, e i suoi fondamenti empirici precedono la letteratura
multi-agente: Allport e Postman hanno stabilito la dinamica
embedding-leveling-sharpening della trasmissione delle voci e identificato
la legge di base che lega l'intensità della voce al prodotto di importanza
e ambiguità (Allport e Postman 1947), mentre gli esperimenti di
serial-reproduction di Bartlett hanno mostrato che successive narrazioni
di una storia convergono verso schemi culturalmente familiari piuttosto
che preservare il contenuto della fonte (Bartlett 1932). Il modulo di
reputazione di Epocha implementa il modello normativo
Castelfranchi-Conte-Paolucci ed è documentato come contenuto Metodi
auditato nel Capitolo 4.3 a seguito della convergenza dell'audit Round 2
del 2026-05-12; i cluster di voci e flusso informativo che attingono alla
tradizione Allport-Postman e Bartlett sono documentati come contenuto
Metodi auditato nel Capitolo 4.4 a seguito della convergenza dell'audit
Round 2 del 2026-05-16.

---

# 3. Architettura del sistema

## 3.1 Motore di tick e scale temporali

La simulazione avanza in tick discreti. Ogni tick è interpretato dal
template di era configurato come un mese, anno o decennio di calendario —
le costanti di calibrazione dei moduli di demografia ed economia sono esse
stesse espresse rispetto a questo passo nominale, per cui cambiare la
scala temporale cambia il set di parametri piuttosto che il motore. Un
tick è atomico: l'orchestratore esegue prima l'aggiornamento dell'economia,
poi un chord Celery distribuisce un task `process_agent_turn` per ciascun
agente vivente in parallelo, poi la callback del chord `finalize_tick`
esegue il flusso di informazione, le dinamiche di fazione, il ciclo
politico, il decadimento di relazioni e memoria, cattura uno snapshot,
rileva crisi epocali, avanza il contatore di tick, fa il broadcast ai
client WebSocket connessi e infine ri-accoda `run_simulation_loop` con un
countdown derivato dal moltiplicatore di velocità di simulazione (cfr.
`epocha/apps/simulation/tasks.py`). Ri-accodare invece di fare long-polling
mantiene ogni tick un task fresco la cui vita coincide col suo lavoro, il
che permette al broker di sopravvivere a riavvii dei worker senza perdere
la simulazione. All'interno di un tick l'ordine degli agenti è
deterministico — l'header del chord è costruito da
`Agent.objects.filter(...).values_list("id", flat=True)`, il cui ordering è
la sequenza di chiave primaria di default del modello — per cui ogni
non-determinismo proviene dalla chiamata LLM e dagli stream RNG seedati
per tick documentati in §3.4, mai dallo scheduling. Un design real-time
event-driven è stato rifiutato perché i tick discreti sono la granularità
naturale della letteratura demografica ed economica da cui la calibrazione
attinge (Heligman e Pollard 1980, Hadwiger 1940), perché la riproducibilità
per tick è il contratto su cui dipende la suite di validazione del
Capitolo 7, e perché il parallelismo basato su chord scala orizzontalmente
sui worker Celery senza lockare stato condiviso.

```
tick N      pre-snapshot ──> economy tick ──> chord(process_agent_turn × N agents)
                                                            │
                                                            ▼
                                              finalize_tick callback
                                                            │
                                                            ▼
            information flow ──> factions ──> politics ──> relationship/memory decay
                                                            │
                                                            ▼
            post-snapshot + crisis detection ──> tick counter ++ ──> WebSocket broadcast
                                                            │
                                                            ▼
                                              re-enqueue run_simulation_loop (tick N+1)
```

## 3.2 Pipeline di decisione dell'agente (Big Five + memoria + LLM)

Ogni agente vivente attraversa una pipeline a quattro stadi implementata
in `epocha/apps/agents/decision.py::process_agent_decision`. Il primo
stadio raccoglie il contesto: le top-k memorie rilevanti (ordinate per
peso emotivo decrescente, poi per recency decrescente, in
`epocha/apps/agents/memory.py::get_relevant_memories`), le relazioni in
uscita dell'agente, gli eventi iniettati di recente, la lista enumerata
dei target di interazione validi, e blocchi di contesto opzionali su
fazione, politica, reputazione, zona ed economia. Il secondo stadio
assembla il prompt utente da questi frammenti. Il terzo stadio costruisce
il prompt di sistema concatenando la descrizione di personalità Big Five
prodotta da
`epocha/apps/agents/personality.py::build_personality_prompt` con il
vocabolario di azione filtrato per era restituito da `_build_system_prompt`;
i valori dei tratti Big Five mappano su descrittori in linguaggio
naturale usando soglie a 0.3 e 0.7, seguendo il modello dei cinque
fattori validato attraverso strumenti e osservatori (McCrae e Costa
1987). Il quarto stadio chiama l'LLM attraverso l'adattatore agnostico
rispetto al provider (Capitolo 3.5), rimuove i fence markdown dalla
risposta, parsifica l'azione JSON con un fallback a `{"action": "rest",
"reason": "confused"}` quando l'LLM restituisce output malformato, e
persiste l'intero contesto di input e l'azione parsificata in una riga
`DecisionLog` per replay e audit offline.

Le memorie sono scritte da `apply_agent_action` con un peso emotivo
estratto da una tabella di lookup per azione (per esempio 0.8 per
`betray`, 0.7 per `pair_bond`, 0.05 per `rest`); le memorie ad alto peso
sopravvivono molto più a lungo perché la routine di decadimento in
`memory.py::decay_memories` smorza il rate di forgetting di
`1 + 5 × emotional_weight` ed esenta del tutto dal decadimento le memorie
con peso ≥ 0.6, modellando l'effetto di consolidamento che Brown e Kulik
hanno chiamato flashbulb memories (Brown e Kulik 1977). La descrizione
sopra colloca la pipeline di decisione, il modulo di personalità e il
modulo di memoria in questo capitolo invece che nel Capitolo 4 perché le
loro implementazioni non hanno ancora completato il Round 2 dell'audit
avversariale della spec richiesto dalla regola di metodo scientifico del
progetto. Saranno promossi a Metodi (Capitolo 4) quando quell'audit
convergerà; la descrizione architetturale qui è sufficiente per seguire il
resto del documento ma non è di livello Metodi.

## 3.3 Contratti di integrazione cross-modulo (treasury, subsistence, outlook)

Tre funzioni esplicite formano la superficie di contratto fra demografia e
i sottosistemi economia/mondo. Sono state estratte da mutazioni inline e
lookup ad hoc durante il Plan 1 di Demografia per rendere i confini di
integrazione testabili in isolamento e auditabili come un singolo punto
di dipendenza fra sottosistemi. I global impliciti sono stati rifiutati
perché nascondono l'accoppiamento e rendono il modulo di demografia
impossibile da testare senza avviare un'economia completa.

| Contratto | Firma | Semantica | Caller / Implementer |
|----------|-----------|-----------|----------------------|
| Treasury credit | `add_to_treasury(government, currency_code, amount)` in `epocha/apps/world/government.py` | Aggiunge `amount` di `currency_code` a `government.government_treasury` (una mappa JSON da codice di valuta a saldo) e persiste la riga. | Chiamato da `epocha/apps/economy/engine.py` (tassazione), da `epocha/apps/economy/property_market.py` (ricavo della vendita di una proprietà governativa/pubblica senza proprietario agente) e dalla logica di eredità/imposta di successione nel sottosistema demografico; implementato in `world/government.py`. |
| Subsistence threshold | `compute_subsistence_threshold(simulation, zone)` in `epocha/apps/demography/context.py` | Restituisce il flusso di ricchezza per agente per tick necessario a consumare beni essenziali ai prezzi correnti del mercato della zona, usando `GoodCategory.is_essential` e la costante `SUBSISTENCE_NEED_PER_AGENT` da `economy/market.py`. | Chiamato da `demography/fertility.py::becker_modulation`; implementato in `demography/context.py`. |
| Aggregate outlook | `compute_aggregate_outlook(agent)` in `epocha/apps/demography/context.py` | Restituisce uno scalare in `[-1, 1]` che riassume la percezione economica dell'agente come media equiponderata di umore dell'agente, fiducia bancaria e stabilità governativa, ciascuno riscalato da `[0, 1]` a `[-1, 1]`. Documentato come euristica di design tunabile, non derivata da Jones e Tertilt (2008). | Chiamato da `demography/fertility.py::becker_modulation`; implementato in `demography/context.py`. |

## 3.4 Strategia RNG e riproducibilità

Tutte le decisioni stocastiche nel sottosistema di demografia attingono da
generatori di numeri casuali seedati per stream piuttosto che dal
`random.random` a livello di processo. L'helper
`epocha/apps/demography/rng.py::get_seeded_rng(simulation, tick, phase)`
restituisce un `random.Random` fresco il cui seed è dato dai primi otto
byte di `sha256(f"{simulation.id}:{simulation.seed}:{tick}:{phase}")`.
L'etichetta di fase deve appartenere a un insieme chiuso (`mortality`,
`fertility`, `couple`, `migration`, `inheritance`, `initialization`); una
label sconosciuta solleva `ValueError` per prevenire collisioni silenziose
di stream. L'isolamento per stream è deliberato: riordinare o sopprimere la
routine di mortalità in un refactor non deve spostare la sequenza casuale
che fertilità, formazione di coppia o eredità vedono allo stesso tick,
altrimenti la riproducibilità fra refactor collassa. Dato l'hash del commit
della codebase, il `simulation.seed` e lo stato iniziale del database, ogni
tick di una run è deterministico e riproducibile fra macchine. Un debito
noto è tracciato come A-5 per il Plan 4: quando sia `simulation.seed` sia
`simulation.id` sono `None`, l'helper RNG ricade su `0` per entrambi, per
cui due simulazioni non salvate senza seed esplicito che eseguono lo
stesso tick attingono stream identici. La condizione è rara in pratica
(`simulation.id` è `None` solo fra l'istanziazione di `Simulation()` e
`.save()`), ma il fix è richiedere un seed esplicito al momento della
creazione della simulazione.

## 3.5 Adattatore provider LLM e rate limiting

L'adattatore espone una singola interfaccia `BaseLLMProvider`
(`epocha/apps/llm_adapter/providers/base.py`) implementata da un
`OpenAIProvider` (`providers/openai.py`) che punta a qualsiasi endpoint che
onori lo schema OpenAI chat completions. La stessa classe serve perciò
OpenAI propriamente detto, Google Gemini, Groq, OpenRouter, Together AI,
Mistral e runner ospitati localmente come LM Studio e Ollama: cambiano
solo `base_url`, identificatore del modello e key. La configurazione vive
in `config/settings/base.py` sotto `EPOCHA_DEFAULT_LLM_PROVIDER`,
`EPOCHA_LLM_API_KEY`, `EPOCHA_LLM_MODEL` e `EPOCHA_LLM_BASE_URL`, con un
set parallelo `EPOCHA_CHAT_LLM_*` usato da `get_chat_llm_client()` per le
conversazioni con gli agenti; quando il provider di chat è configurato è
incapsulato in un `FallbackProvider` che fa rollover trasparente sul
provider principale in caso di fallimento. Due difese complementari
proteggono dall'esaurimento della quota. All'interno di `OpenAIProvider`,
`EPOCHA_LLM_API_KEY` accetta una lista separata da virgole di key:
quando un `RateLimitError` (HTTP 429) esaurisce il budget di retry
in-call (tre retry con exponential backoff a base due secondi, cfr.
`_MAX_RETRIES` e `_RETRY_BASE_DELAY_SECONDS`) il provider ruota alla key
successiva prima di ri-sollevare. Questo è il meccanismo attualmente usato
per distribuire il carico fra più key Groq free-tier, ma la rotazione è
generica e supporta qualsiasi numero di key. A livello di processo,
`epocha/apps/llm_adapter/rate_limiter.py` fornisce un counter sliding
window basato su Redis (TTL di un minuto, default 50 richieste al minuto
per provider) utilizzabile dal codice di orchestrazione che ha bisogno di
fare throttling prima del limite del provider stesso. La contabilità per
chiamata è persistita nel modello `LLMRequest` (provider, modello, token
count, costo USD, latenza, flag di successo, `simulation_id` opzionale);
il pricing è derivato da una tabella per modello in `providers/openai.py`
con un default conservativo per i modelli non listati.

## 3.6 Sostrato economico (produzione, monetario, market clearing, distribuzione)

L'app economy sotto `epocha/apps/economy/` raccoglie i moduli che
trasformano l'attività degli agenti in produzione, prezzi, moneta e flussi
di reddito. `production.py` implementa una funzione di produzione Constant
Elasticity of Substitution (CES) nella forma
`Q = A · [Σ αᵢ Xᵢ^ρ]^(1/ρ)` con `ρ = (σ-1)/σ` e ricade sulla forma
log Cobb-Douglas vicino a `σ = 1` e su un minimo Leontief vicino a
`σ = 0` per evitare la singolarità numerica. La forma CES è la
generalizzazione classica introdotta da Arrow et al. (1961), con
l'estensione multi-fattore che segue la pratica standard di CGE applicata
(Shoven e Whalley 1992). `market.py` chiude ogni mercato locale di zona
attraverso il tâtonnement walrasiano (Walras 1874): data offerta, domanda
e prezzi correnti, i prezzi sono spinti proporzionalmente alla domanda in
eccesso fino a che l'eccesso relativo cade sotto una soglia di
convergenza o si raggiunge un cap di iterazioni configurabile. Il cap è
la rete di sicurezza esplicita per il regime ben noto di
non-convergenza con tre o più beni (Scarf 1960). I moduli rimanenti
coprono il resto del sostrato: `monetary.py` mantiene un counter di
velocità e una verifica dell'identità di Fisher usata come diagnostica
piuttosto che come regola di prezzo; `distribution.py` deriva la rendita
in modo ricardiano semplificato più un flusso piatto di salari e tasse;
`banking.py` e `credit.py` incapsulano un singolo settore bancario
aggregato che aggiusta il tasso base attraverso un feedback wickselliano
(Wicksell 1898) e traccia i default sui prestiti con propagazione a
cascata in breadth-first (Minsky 1986; Stiglitz e Weiss 1981);
`expectations.py`, `political_feedback.py` e `property_market.py`
collegano l'economia agli agenti e al loop politico.

Il sostrato qui riassunto ha completato il suo audit scientifico
avversariale (dodici round, convergenza 2026-07-16) ed è documentato a
livello Metodi in §4.8, dove ogni formula porta la citazione alla sua
fonte primaria e ogni costante è citata o marcata come parametro di
design regolabile. Lo strato auditato che siede sopra questo sostrato è
l'integrazione comportamentale descritta in §4.2: quell'integrazione
consuma i prezzi, gli scambi e i flussi di reddito prodotti dal sostrato
e aggiunge le aspettative adattive, il satisficing e il feedback
politico.

## 3.7 Modello di persistenza

Lo stato è mantenuto in PostgreSQL con PostGIS già installato
(`django.contrib.gis` è in `INSTALLED_APPS` e le geometrie di zona sono
memorizzate come `PolygonField`/`PointField` WGS84 a partire dalla
migrazione `world.0003_zone_postgis_geometry`). Le convenzioni sugli
identificatori seguono il default Django di chiavi primarie intere
auto-incrementanti a 64 bit, configurate globalmente via
`DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"` in
`config/settings/base.py`, senza chiavi primarie UUID al momento della
scrittura; le foreign key in tutte le app portano perciò riferimenti
interi. L'unica deviazione notevole dal "tutti interi positivi" è la
colonna `birth_tick` su `agents.Agent` introdotta dal Plan 1 della spec
di demografia: è un `BigIntegerField` invece di `PositiveIntegerField`
proprio perché agenti pre-esistenti la cui età precede l'inizio della
simulazione possano portare un birth tick negativo, mantenendo valida la
formula canonica dell'età `age = (current_tick − birth_tick) /
ticks_per_year` attraverso i backfill. Le richieste atomiche sono
abilitate per database (`ATOMIC_REQUESTS = True`) per mantenere gli
handler API e di tick transazionali per default. Il piano di migrazione
oltre l'MVP (tracciato in
`docs/memory-backup/project_roadmap_post_mvp.md`) è di estendere l'uso di
PostGIS oltre la geometria di zona alle traiettorie degli agenti e alle
query di distanza routata.

## 3.8 Strato di interazione (Dashboard, Chat WebSocket)

L'osservazione real-time passa attraverso Django Channels su Redis. Sono
esposte due route WebSocket: `ws/simulation/<simulation_id>/` è servita da
`epocha/apps/simulation/consumers.py:SimulationConsumer` e spinge lo stato
tick per tick a chiunque stia osservando una simulazione, mentre
`ws/chat/<agent_id>/` è servita da
`epocha/apps/chat/consumers.py:ChatConsumer` e veicola la conversazione
sincrona fra un utente umano e uno specifico agente (i pattern URL in
`epocha/apps/{simulation,chat}/routing.py`, ID interi perché le chiavi
primarie sono `BigAutoField`; cfr. §3.7). La dashboard stessa
(`epocha/apps/dashboard/`) è intenzionalmente un'applicazione Django a
template renderizzati lato server invece di una single-page app: il
template di base `dashboard/base.html` carica Alpine.js da una CDN per
piccoli arricchimenti lato client come toggle e contatori live, il che
mantiene il footprint JavaScript e la complessità operativa proporzionale
al focus di ricerca del progetto. Le pagine coprono la lista delle
simulazioni, dettaglio, analytics, grafo e viste di report, più le
superfici di chat e group-chat, tutte che colpiscono le stesse view
Django e ORM che supportano l'API.

---

# 4. Metodi — Moduli auditati

## 4.1 Demografia

> Stato: implementato a partire dal commit `8a2bc714477f445b46cd610725df40c93fce1557`, audit della spec CONVERGENTE 2026-04-18 round 4.

Il modulo demografia copre le tre transizioni del corso di vita per le quali Epocha esegue attualmente un modello scientifico auditato: mortalità, fertilità e formazione delle coppie. La specifica autoritativa è `docs/superpowers/specs/2026-04-18-demography-design.md`, i cui quattro round di revisione adversariale sono convergiti il 2026-04-18; le scelte di design e la mappatura esplicita di ogni parametro a una fonte primaria vivono lì, mentre questo capitolo riformula le formule, le tabelle di calibrazione e gli algoritmi per-tick in forma di pubblicazione. L'implementazione vive sotto `epocha/apps/demography/`, dove i tre sottosistemi sono separati in `mortality.py`, `fertility.py` e `couple.py`, con preoccupazioni condivise fattorizzate in `template_loader.py` (caricamento e validazione JSON delle ere), `rng.py` (stream seedati per fase discussi nel Capitolo 3.4), `context.py` (helper di integrazione verso l'economia) e `models.py` (lo stato demografico persistito). L'intento progettuale è che all'interno di ogni tick i tre sottosistemi vengano eseguiti nell'ordine mortalità → fertilità → formazione delle coppie, ciascuno attingendo dal proprio stream RNG seedato — questa orchestrazione è obiettivo dell'integrazione del Plan 4; vedere la nota di stato sotto. La mortalità materna al parto è l'unico accoppiamento inter-sottosistema ed è risolta congiuntamente tra mortalità e fertilità prima che entrambi registrino il loro esito, come dettagliato in §4.1.2. A partire dal commit fissato nel front matter, i modelli di mortalità e fertilità e l'infrastruttura delle coppie sono implementati e unit-testati in isolamento; la loro orchestrazione nel ciclo di tick della simulazione live in `epocha/apps/simulation/engine.py` è tracciata come deliverable del Plan 4 (Inizializzazione, integrazione del motore e validazione storica) e non è ancora attiva nel codice di produzione.

### 4.1.1 Modello di mortalità (Heligman-Pollard)

> Stato: implementato a partire dal commit `8a2bc714477f445b46cd610725df40c93fce1557`, audit della spec CONVERGENTE 2026-04-18 round 4.

**Background.** La mortalità in Epocha è una scheda di hazard specifica per età piuttosto che un tasso costante, perché ogni indicatore demografico downstream che la suite di validazione del Capitolo 7 prende come target — aspettativa di vita alla nascita, rapporto di mortalità infantile, curva di sopravvivenza — dipende dalla forma della scheda lungo l'età, non dalla sua media. Sono state considerate e respinte due alternative più semplici. Una pura legge di Gompertz (Gompertz 1825) cattura solo l'esponenziale senescente e sottostima la mortalità infantile e dei giovani adulti di ordini di grandezza nei regimi pre-industriali, dove la mortalità infantile guida la maggior parte dell'aspettativa di vita persa. Lee-Carter (Lee e Carter 1992) è un modello di forecasting su log-rate di coorte che opera su popolazioni aggregate e una baseline storica stazionaria; non è progettato per fornire l'hazard età-condizionale per-agente di cui un microsimulatore ha bisogno a ogni tick, e applicarlo alla scala dell'agente richiederebbe uno step di bridging extra senza guadagno scientifico rispetto al valutare direttamente la scheda analitica. La decomposizione additiva a otto parametri di Heligman-Pollard (1980) è stata mantenuta perché esprime i tre regimi osservati — declino infantile, gobba degli incidenti dei giovani adulti, ascesa senescente — in una singola espressione in forma chiusa che può essere valutata per qualunque età dell'agente in tempo costante e che ammette ricalibrazione per-era sostituendo otto numeri.

**Modello.** Heligman e Pollard (1980) parametrizzano gli odds di morte all'età `x` come somma di tre componenti:

```
q(x) / p(x) = A^((x + B)^C)                      (4.1)
            + D · exp(-E · (ln(x/F))^2)
            + G · H^x
```

dove `q(x)` è la probabilità annuale di morte all'età esatta `x` e `p(x) = 1 − q(x)` è la corrispondente probabilità di sopravvivenza. Il primo termine, controllato da `A`, `B`, `C`, cattura il rapido declino della mortalità infantile con l'età. Il secondo termine, controllato da `D`, `E`, `F`, cattura la cosiddetta gobba degli incidenti centrata all'età `F` con ampiezza di picco `D` e larghezza determinata da `E`, ed è interpretato storicamente come l'eccesso di mortalità da incidenti, violenza e (per le donne) cause materne tra i giovani adulti. Il terzo termine, controllato da `G` e `H`, è la legge esponenziale di Gompertz che domina la mortalità senescente alle età avanzate. L'equazione (4.1) è la forma canonica del 1980 (vedi Heligman e Pollard 1980, formula 5); l'equivalenza algebrica `(ln(x/F))² ≡ (ln x − ln F)²` è usata in `epocha/apps/demography/mortality.py:_hp_components()` per mantenere l'implementazione una trascrizione diretta riga-per-riga dell'espressione del manuale. Poiché l'equazione (4.1) restituisce gli odds `q/p`, l'implementazione converte in probabilità tramite `q = (q/p) / (1 + q/p)` in `annual_mortality_probability()` (mortality.py:45), e clampa il risultato a `0.999` per mantenere `(1 − q)` strettamente positivo per lo scaling geometrico per-tick descritto sotto Algoritmo.

**Parametri.** Gli otto parametri HP portano i ruoli semantici riassunti nella Tabella 4.1.

Tabella 4.1 — Parametri di Heligman-Pollard: semantica e intervalli ammissibili.

| Simbolo | Componente      | Ruolo semantico                                                  | Intervallo ammissibile usato in calibrazione |
|---------|-----------------|------------------------------------------------------------------|---------------------------------------------|
| `A`     | infanzia        | livello di mortalità all'età 1                                   | `[0, 0.1]`                                  |
| `B`     | infanzia        | mortalità all'età 0 relativa all'età 1 (intercetta dell'infanzia) | `[0, 0.5]`                                  |
| `C`     | infanzia        | tasso di declino della mortalità infantile con l'età             | `[0, 1.0]`                                  |
| `D`     | gobba incidenti | ampiezza di picco dell'eccesso di mortalità giovani adulti       | `[0, 0.05]`                                 |
| `E`     | gobba incidenti | larghezza inversa (acutezza) della gobba degli incidenti         | `[0.1, 50]`                                 |
| `F`     | gobba incidenti | età alla quale è centrata la gobba degli incidenti (anni)        | `[1.0, 50]`                                 |
| `G`     | senescenza      | livello di mortalità senescente all'età 0 (intercetta Gompertz)  | `[0, 0.001]`                                |
| `H`     | senescenza      | tasso di incremento esponenziale della mortalità senescente      | `[1.0, 1.5]`                                |

Gli intervalli ammissibili sono i bound imposti da `fit_heligman_pollard()` in `mortality.py:148-149` quando si rifitta la scheda contro una tavola di vita esterna, e sono coerenti con i vicinati di parametri riportati nella letteratura attuariale sul modello HP (Heligman e Pollard 1980; survey successive in Tabeau, van den Berg Jeths e Heathcote 2001 sono citate via la spec). I valori per-era sono caricati da template JSON sotto `epocha/apps/demography/templates/`. La Tabella 4.2 elenca i valori spediti con ciascuno dei cinque template rilasciati nel Plan 1 del lavoro di demografia; i valori per `pre_industrial_christian.json` e `pre_industrial_islamic.json` sono identici (solo i campi non-mortalità differiscono tra le due varianti pre-industriali). I valori MVP sono seed provvisori dell'ordine di grandezza dei loro target di calibrazione; il fitting numerico contro i target citati è documentato nella spec di demografia e nelle note di chiusura del Plan 1 come valori seed provvisori, con la procedura di fit (`fit_heligman_pollard()`) riservata alla calibrazione del Plan 4 contro dati storici di mortalità. Il template `sci_fi.json` è documentato nel file sorgente come speculativo e non ha target empirico.

Tabella 4.2 — Valori dei parametri HP per-era (template spediti nel Plan 1).

| Template di era                               | `A`      | `B`   | `C`   | `D`      | `E`   | `F`   | `G`        | `H`   | Target di calibrazione                                            |
|-----------------------------------------------|----------|-------|-------|----------|-------|-------|------------|-------|-------------------------------------------------------------------|
| `pre_industrial_christian` / `pre_industrial_islamic` | 0.00491  | 0.017 | 0.102 | 0.00080  | 9.9   | 22.4  | 0.0000383  | 1.101 | Wrigley e Schofield (1981) tabelle A3.1–A3.3, Inghilterra 1700–1749 |
| `industrial`                                  | 0.00223  | 0.022 | 0.115 | 0.00057  | 10.8  | 25.1  | 0.0000198  | 1.104 | Tavole di vita HMD Inghilterra e Galles, pooled 1841–1900         |
| `modern_democracy`                            | 0.00054  | 0.017 | 0.125 | 0.00013  | 18.3  | 19.6  | 0.0000123  | 1.101 | Tavola di vita HMD USA 2019 (baseline pre-COVID)                  |
| `sci_fi`                                      | 0.00002  | 0.017 | 0.125 | 0.00001  | 18.3  | 19.6  | 0.0000018  | 1.089 | Estrapolazione speculativa; nessuna base empirica                 |

**Algoritmo.** Per ogni agente vivo, ad ogni tick, il modulo di mortalità valuta l'equazione (4.1) all'età corrente dell'agente, converte gli odds risultanti nella probabilità annuale `q(age, params)`, la scala all'intervallo del tick e estrae contro una variata uniforme dallo stream RNG seedato. Lo scaling per-tick è implementato in `mortality.py:tick_mortality_probability()` (riga 56) ed è condizionale alla dimensione di `q`: quando la probabilità annuale è sotto 0.1 viene usata l'approssimazione lineare `q · dt` (il suo errore rispetto alla forma geometrica esatta è sotto lo 0.5% in questo regime), e quando `q` supera 0.1 — come fa per gli infanti sotto il template pre-industriale — viene usata la conversione geometrica esatta `1 − (1 − q)^dt`, dove `dt = (tick_duration_hours / 8760) · demography_acceleration` è la lunghezza del tick espressa in anni e riscalata dal fattore di clock demografico per-template. La variata uniforme è estratta da un `random.Random` restituito da `epocha.apps.demography.rng.get_seeded_rng(simulation, tick, phase="mortality")`; la signature dell'helper è `(simulation, tick, phase)`, e l'insieme chiuso di label di fase ammessi — `mortality`, `fertility`, `couple`, `migration`, `inheritance`, `initialization` — garantisce che aggiungere o rimuovere un sottosistema in un refactor non sposti la sequenza casuale che gli altri vedono allo stesso tick (il Capitolo 3.4 copre il razionale di design). Quando una morte si attiva, la causa è campionata da `mortality.py:sample_death_cause()` (riga 77), che valuta le tre componenti HP all'età della morte e seleziona uno dei tre label `early_life_mortality`, `external_cause`, `natural_senescence` con probabilità proporzionale alla magnitudine della componente corrispondente; i label sono convenzioni analitiche per il reporting della dashboard, non eziologia medica, e mappano uno-a-uno sui tre termini dell'equazione (4.1). A partire dal commit fissato, questa valutazione per-tick è esercitata dalla suite di unit test della demografia (`epocha/apps/demography/tests/test_mortality.py`) ma non è ancora invocata da `epocha/apps/simulation/engine.py` o `tasks.py`. L'integrazione nel ciclo di tick live è tracciata come deliverable del Plan 4.

**Semplificazioni.** L'implementazione attuale omette deliberatamente tre raffinamenti che la letteratura demografica tratta come estensioni proprie piuttosto che correzioni della scheda baseline. Primo, non vengono modellati effetti di coorte: ogni agente è esposto al template di era attivo al tick di simulazione piuttosto che al regime di mortalità in vigore alla nascita dell'agente, quindi shock specifici di coorte (guerra, epidemia, carestia) non possono persistere come firma residua di coorte nella vita successiva. Secondo, `sample_death_cause()` seleziona un singolo label grossolano dalle tre componenti HP piuttosto che decomporre la mortalità in una tassonomia completa di cause di morte; i tre label sono sufficienti per le analytics della dashboard ma non sono una classificazione medica, e qualunque analisi che richieda tassi di mortalità causa-specifici dovrebbe estendere il sampler. Terzo, non è fornita estrapolazione oltre l'età 110: la scheda HP è valutata all'età corrente dell'agente senza un modello di coda esplicito per i super-centenari, e il cap di `0.999` sulla probabilità annuale di mortalità garantisce che la probabilità di sopravvivenza resti strettamente positiva per la conversione geometrica per-tick, ma questo è un guardrail numerico piuttosto che un modello sostantivo dei plateau di mortalità tardiva.

### 4.1.2 Modello di fertilità (ASFR di Hadwiger + modulazione di Becker + soffitto Malthusiano)

> Stato: implementato a partire dal commit `8a2bc714477f445b46cd610725df40c93fce1557`, audit della spec CONVERGENTE 2026-04-18 round 4.

**Background.** La fertilità in Epocha è costruita come una composizione a tre strati piuttosto che come una singola scheda in forma chiusa perché le tre forze che deve rappresentare operano su scale temporali incommensurabili e su canali causali distinti. Il substrato biologico — la curva a campana della fecondità femminile specifica per età sulla finestra fertile, con picco a metà dei vent'anni e coda fino a fine quarant'anni — è ben catturato da una scheda analitica e cambia solo su scale temporali evolutive. La modulazione economica e culturale della fertilità completata — la differenza tra cinque figli per donna in un'economia agraria pre-industriale e uno e mezzo in una democrazia moderna — opera sulla scala temporale delle generazioni ed è guidata da reddito, istruzione e costo opportunità della maternità piuttosto che dalla biologia. Il soffitto aggregato — il cap soft che impedisce alla popolazione simulata di esplodere in condizioni in cui i tassi analitici da soli genererebbero crescita esponenziale — non è né biologico né culturale ma un vincolo di ingegneria che deve tuttavia preservare la forma qualitativa del controllo preventivo Malthusiano. Sono state considerate e respinte due alternative a strato singolo. Le model fertility schedule di Coale e Trussell del 1974 esprimono la fertilità specifica per età come prodotto di una scheda di fertilità naturale, un parametro `M` per il livello e un parametro `m` per il comportamento di spacing/stopping, e hanno decenni di validazione empirica alle spalle. La formulazione Coale-Trussell, tuttavia, incorpora il proprio contenuto socio-economico dentro il parametro `m`, che mescola due effetti (timing dello stopping e intensità della contraccezione) che Epocha deve far variare indipendentemente per l'integrazione comportamentale con lo strato di decisione guidato da LLM; calibrare `m` su un livello target di fertilità completata perde la maniglia esplicita sul meccanismo economico. La forma analitica a tre parametri di Hadwiger del 1940, al contrario, è una pura forma per età con un tasso totale di fertilità normalizzato `H` fattorizzato fuori dall'integrale, il che ci permette di moltiplicare per una funzione di modulazione esterna senza rompere la proprietà di integrazione della scheda. Il framework quantità-qualità di Becker del 1991 fornisce il vocabolario giusto per quella funzione di modulazione — il valore marginale di un figlio aggiuntivo come funzione del reddito familiare, della partecipazione femminile alla forza lavoro e dell'istruzione genitoriale — ma non prescrive di per sé una forma funzionale specifica su una probabilità per-tick, quindi lo strato di modulazione è implementato come fattore di scaling log-lineare ispirato al framework di Becker piuttosto che come modello letterale di Becker. Il soffitto Malthusiano è aggiunto in cima perché Hadwiger × Becker da solo non ha un feedback di densità di popolazione, e i template pre-industriali con `H = 5.0` genererebbero tassi di crescita incompatibili con la capacità di carico della griglia di simulazione; il soffitto è l'intuizione del controllo preventivo di Ashraf e Galor (2011) implementata come scaling a tratti sulla probabilità di nascita per-tick piuttosto che come formalismo a tempo continuo sul reddito pro capite.

**Modello.** La probabilità per-tick che una madre eleggibile partorisca al tick corrente è il prodotto di tre strati, ognuno implementato come funzione separata in `epocha/apps/demography/fertility.py` così che gli strati possano essere sostituiti o auditati indipendentemente:

```
f_HW(a; H, R, T) = (H · T / (R · √π)) · (R / a)^1.5
                 · exp(−T² · (R / a + a / R − 2))                    (4.2)

m_BK(agent; β) = clip(exp(β₀ + β₁ · w + β₂ · e + β₃ · φ + β₄ · ω),
                      0.05, 3.0)                                     (4.3)

c_MT(p, n, n_max, ρ) = p                              if n < 0.8 · n_max
                     = p · max(0, 1 − (n − 0.8·n_max) / (0.2·n_max))
                                                       if n < n_max
                     = p · ρ                           if n ≥ n_max  (4.4)

P_tick(agent, env) = c_MT( f_HW(a; H, R, T) · m_BK(agent; β),
                            n, n_max, ρ )  ·  Δt                     (4.5)
```

L'equazione (4.2) è il tasso di fertilità specifico per età di Hadwiger canonico nella forma normalizzata discussa in Chandola, Coleman e Hiorns (1999) e Schmertmann (2003), dove `H` è il tasso totale di fertilità target (l'integrale di `f_HW` sulla finestra fertile), `R` è un parametro di forma legato all'età di picco della fertilità, e `T` controlla la dispersione della distribuzione; l'implementazione in `fertility.py:hadwiger_asfr()` (riga 19) restituisce 0 fuori dalla finestra biologicamente fertile `[12, 50]` e a età non positive. L'equazione (4.3) è lo strato di modulazione di Becker in `fertility.py:becker_modulation()` (riga 85): `w = log(max(wealth / max(subsistence, 1e-6), 0.1))` è il segnale di log-ricchezza relativo alla soglia di sussistenza, `e` è il livello di istruzione dell'agente, `φ` è la proxy di partecipazione femminile alla forza lavoro nella zona dell'agente (calcolata in `_female_role_employment_fraction()` da transazioni salariali a un tick verso destinatari femminili), e `ω` è il segnale di outlook aggregato calcolato in `epocha.apps.demography.context.compute_aggregate_outlook()`; il risultato è esponenziato e clampato a `[0.05, 3.0]` per mantenere il fattore di modulazione limitato sotto input estremi. L'equazione (4.4) è il soffitto soft Malthusiano implementato in `fertility.py:malthusian_soft_ceiling()` (riga 118): sotto l'80% del `max_population` per-template il fattore moltiplicativo è uno, tra l'80% e il 100% scende linearmente a zero, e sopra il 100% collassa a un floor `ρ` (`malthusian_floor_ratio` nel template di era) così che le popolazioni non smettano interamente di riprodursi (a meno che il template di era imposti esplicitamente `malthusian_floor_ratio = 0`, come in `sci_fi`). L'equazione (4.5) è il combinato `tick_birth_probability(mother, params_era, current_pop, tick_duration_hours, demography_acceleration, current_tick)` in `fertility.py:152`, che compone i tre strati, moltiplica per `Δt = (tick_duration_hours / 8760) · demography_acceleration` per convertire il tasso annuale all'intervallo del tick, e restituisce 0 incondizionatamente quando l'era richiede l'appartenenza a una coppia e la madre non è in una coppia attiva, oppure quando il flag `avoid_conception` è stato impostato al tick precedente (leggere un flag impostato al tick `T−1` durante il tick `T` rende la contraccezione un'azione regolata a tick+1, coerente con la semantica del mercato immobiliare introdotta nel Capitolo 4.2.3).

**Parametri.** I tre parametri di Hadwiger portano i ruoli semantici `H` = TFR target, `R` = parametro di forma del picco di fertilità, `T` = dispersione; i valori per-era sono caricati da template JSON sotto `epocha/apps/demography/templates/`. La Tabella 4.3 elenca i valori di Hadwiger spediti con ciascuno dei cinque template del Plan 1. I valori di `H` seguono livelli di fertilità completata storicamente attestati — cinque figli per donna per i template pre-industriali, quattro per la transizione industriale, leggermente sotto il rimpiazzo per il template della democrazia moderna, e attorno al rimpiazzo per il template speculativo `sci_fi` — mentre `R` e `T` spostano il picco verso destra e ampliano la distribuzione mentre le società transitano verso prime nascite più tardive e spacing più stretti.

Tabella 4.3 — Valori dei parametri Hadwiger per-era (template spediti nel Plan 1).

| Template di era              | `H` (TFR target) | `R` (forma del picco) | `T` (dispersione) | `max_population` | `malthusian_floor_ratio` (`ρ`) |
|------------------------------|------------------|------------------------|--------------------|------------------|--------------------------------|
| `pre_industrial_christian`   | 5.0              | 26                     | 3.5                | 500              | 0.10                           |
| `pre_industrial_islamic`     | 5.0              | 26                     | 3.5                | 500              | 0.10                           |
| `industrial`                 | 4.0              | 27                     | 3.8                | 500              | 0.05                           |
| `modern_democracy`           | 1.8              | 30                     | 4.2                | 500              | 0.01                           |
| `sci_fi`                     | 2.1              | 32                     | 4.0                | 500              | 0.00                           |

I cinque coefficienti di Becker portano i ruoli `β₀` = baseline (centrato sulla scheda biologica dell'era), `β₁` = elasticità alla log-ricchezza (positivo: maggiore ricchezza relativa alza la fertilità desiderata all'estremità agraria dello spettro), `β₂` = penalità di istruzione (negativo: il costo opportunità della maternità sale con l'istruzione genitoriale), `β₃` = penalità di partecipazione femminile alla forza lavoro (negativo: maggiore occupazione femminile a livello di zona deprime la fertilità), `β₄` = elasticità all'outlook aggregato (positivo: ottimismo sul futuro alza il fattore di modulazione). A partire dal commit fissato, i cinque coefficienti sono seedati con gli stessi valori in tutti e cinque i template — `β₀ = 0.0`, `β₁ = 0.1`, `β₂ = −0.05`, `β₃ = −0.1`, `β₄ = 0.2` — in attesa di calibrazione per-era, e questa omogeneità è tracciata nel log di risoluzione audit della spec come debito B2-07 e assegnata al Plan 4 (calibrazione contro test sintetici di shock). La Tabella 4.4 registra i valori seed esplicitamente così che l'omogeneità sia visibile al lettore piuttosto che sepolta nei JSON per-era.

Tabella 4.4 — Coefficienti di modulazione di Becker (identici in tutti e cinque i template in attesa della calibrazione del Plan 4; tracciati come debito B2-07 nella spec).

| Coefficiente | Valore seed | Ruolo semantico                                                |
|--------------|------------:|----------------------------------------------------------------|
| `β₀`         |        0.0  | Log-shift di baseline sul fattore di modulazione                |
| `β₁`         |        0.1  | Elasticità alla log-ricchezza relativa alla sussistenza         |
| `β₂`         |       −0.05 | Penalità per unità di istruzione genitoriale                    |
| `β₃`         |       −0.1  | Penalità per unità di partecipazione femminile alla forza lavoro nella zona |
| `β₄`         |        0.2  | Elasticità al segnale macro di outlook aggregato                |

I cinque coefficienti sono descritti in `becker_modulation()` (fertility.py:85–111) come "valori seed provvisori" con calibrazione "rinviata al Plan 4 usando test sintetici di shock"; sono ispirati al framework di Becker piuttosto che stimati da una specifica regressione di economia familiare in stile Becker, e il whitepaper li registra come parametri tunabili dell'implementazione Epocha piuttosto che come costanti derivate da Becker. Il floor Malthusiano `ρ` è il campo `malthusian_floor_ratio` sul blocco `fertility` per-template; quando omesso, `tick_birth_probability` ha come default `0.1` (`fertility.py:204`), che è il valore usato nel testo della spec e nei due template pre-industriali.

**Algoritmo.** Per ogni agente femminile vivo nella finestra fertile `[12, 50]`, ad ogni tick, il modulo di fertilità prima controlla le precondizioni di gating in `tick_birth_probability()` (righe 180–191): se il template di era richiede appartenenza a una coppia e la madre non è in una coppia attiva (`is_in_active_couple()`), o se il flag `avoid_conception` su `AgentFertilityState` è stato impostato al tick `T−1` (`is_avoid_conception_active_this_tick()`, riga 262), la funzione restituisce 0 e nessuna nascita può attivarsi questo tick. Altrimenti i tre strati sono valutati in sequenza: `hadwiger_asfr()` viene chiamata sull'età dell'agente in anni (calcolata in `_effective_age_in_years()` da `birth_tick` e dal `current_tick` autoritativo per evitare la staleness della FK-cache segnalata dal finding B2-04 dell'audit), il risultato è moltiplicato per `becker_modulation()` valutato contro la ricchezza, l'istruzione, la zona e l'outlook dell'agente, il prodotto è passato attraverso `malthusian_soft_ceiling()` contro la popolazione corrente e `max_population`, e il tasso annuale risultante è moltiplicato per `Δt` per dare la probabilità per-tick. Il chiamante estrae una variata uniforme da un `random.Random` restituito da `epocha.apps.demography.rng.get_seeded_rng(simulation, tick, phase="fertility")` — lo stesso contratto di stream seedato documentato per la mortalità in §4.1.1, con `phase="fertility"` selezionato dal set di fasi chiuso così che l'estrazione di fertilità non sposti mai la sequenza casuale che l'estrazione di mortalità allo stesso tick ha consumato. Quando una nascita si attiva e si applica la mortalità materna, il fix C-1 della §1 della spec richiede che i due eventi siano risolti congiuntamente piuttosto che sequenzialmente: `resolve_childbirth_event(mother, params_era, tick, rng)` (`fertility.py:295`) estrae contro `mortality.maternal_mortality_rate_per_birth` per l'evento di morte materna e, condizionalmente alla morte della madre, contro `mortality.neonatal_survival_when_mother_dies` per la sopravvivenza del neonato; l'helper è un risolutore probabilistico puro e restituisce un dict `{mother_died, newborn_survived, death_cause}` con `death_cause = "childbirth"` quando viene selezionata la morte materna, lasciando la persistenza (record di morte della madre, creazione del neonato) al chiamante. La risoluzione congiunta evita il bias che sorgerebbe risolvendo la mortalità generica per prima e la mortalità da parto per seconda sulla stessa madre nello stesso tick. A partire dal commit fissato, questa valutazione di fertilità per-tick è esercitata dalla suite di unit test della demografia (`epocha/apps/demography/tests/test_fertility.py`) ma non è ancora invocata da `epocha/apps/simulation/engine.py` o `tasks.py`; l'unica menzione di `tick_birth_probability` fuori da `demography/` è un commento in `engine.py:276` che descrive la semantica di gating del flag `avoid_conception`. Una funzione demografica è già invocata dal motore di simulazione: `set_avoid_conception_flag()` (`fertility.py:262-288`) viene chiamata dal gestore della decisione `avoid_conception` in `engine.py:280-310` per registrare il flag per-agente al tick T-1, a supporto dell'azione risolta al tick+1. Il resto dell'orchestrazione demografica (mortalità, fertilità e risoluzione delle coppie per-tick) rimane in attesa dell'integrazione del Plan 4. L'integrazione nel ciclo di tick live è tracciata, accanto al gap di mortalità equivalente notato in §4.1.1, come deliverable del Plan 4 (Inizializzazione, integrazione del motore e validazione storica).

**Semplificazioni.** L'implementazione attuale omette deliberatamente quattro raffinamenti che la letteratura demografica tratta come estensioni proprie piuttosto che correzioni della scheda baseline. Primo, la scheda specifica per età di Hadwiger è valutata deterministicamente sull'età dell'agente, senza eterogeneità inter-individuale nella fecondità biologica sottostante oltre i flag binari portati da `AgentFertilityState`; modellare eterogeneità lognormale nel time-to-conception (la letteratura sui determinanti prossimali rivista nella spec di demografia) è rinviato. Secondo, le nascite gemellari e di ordine superiore non sono modellate: ogni evento di nascita riuscita crea esattamente un neonato, indipendentemente dai tassi storici di nascite multiple che variano da circa l'1% nell'Europa pre-industriale a oltre il 3% in alcune popolazioni moderne. Terzo, i coefficienti di modulazione di Becker sono omogenei in tutti e cinque i template di era, come documentato nella Tabella 4.4 e tracciato come debito di audit B2-07; la calibrazione per-era è il deliverable centrale del Plan 4 e sostituirà i valori seed con stime era-specifiche da test sintetici di shock contro la baseline di Wrigley e Schofield (1981) e i riferimenti aggiuntivi sul declino della fertilità catalogati nella spec di demografia. Quarto, il soffitto soft Malthusiano è una euristica di ingegneria piuttosto che un'implementazione letterale del formalismo del controllo preventivo di Ashraf e Galor (2011), che opera in tempo continuo sul reddito pro capite; il soffitto Epocha è uno scaling discreto basato sul tick sulla probabilità di nascita per-madre che preserva la forma qualitativa del controllo preventivo (libero sotto l'80% del cap, rampa a zero tra l'80% e il 100%, floor sopra il cap) senza pretendere di riprodurre le dinamiche di reddito di Ashraf-Galor. La scelta è documentata nel docstring di `malthusian_soft_ceiling()` (`fertility.py:118–145`) ed è coerente con l'intento di design di dare alla simulazione un feedback di densità di popolazione che protegge il budget computazionale per-tick rimanendo interpretabile in termini Malthusiani. L'helper `_zone_mean_wage()` (`fertility.py:70-82`) è definito come scaffolding per un futuro raffinamento di Becker che userebbe i salari medi per zona come segnale di ricchezza, ma non è invocato da `becker_modulation()` a partire dal commit fissato; il segnale di ricchezza usa attualmente la ricchezza dell'agente normalizzata dalla soglia di sussistenza.

### 4.1.3 Formazione e dissoluzione delle coppie (Gale-Shapley + Goode 1963)

> Stato: implementato a partire dal commit `8a2bc714477f445b46cd610725df40c93fce1557`, audit della spec CONVERGENTE 2026-04-18 round 4.

**Background.** La formazione delle coppie in Epocha gira su due meccanismi distinti perché il modulo di genealogia ha due workload distinti con semantiche incompatibili. All'inizializzazione della simulazione il modulo deve popolare una popolazione fondatrice sintetica con una distribuzione congiunta plausibile di adulti accoppiati e non accoppiati: ogni adulto eleggibile vede ogni altro adulto eleggibile una volta, e l'abbinamento deve essere stabile nel senso di Gale e Shapley (1962) così che nessuna coppia di agenti non abbinati si preferirebbe reciprocamente ai partner assegnati — altrimenti la popolazione fondatrice parte in uno stato di non-equilibrio che le dinamiche per-tick dovrebbero poi annullare. A runtime, al contrario, le coppie si formano una o due alla volta mentre gli agenti prendono decisioni individuali attraverso la pipeline LLM, e la primitiva appropriata non è un abbinamento globale ma un risolutore di intenti regolato a tick+1, nella stessa famiglia del pattern di settlement del mercato immobiliare documentato nel Capitolo 4.2.3: un agente dichiara l'intento di pair-bond con un target nominato al tick `T`, il risolutore gira all'inizio del tick `T+1`, e una coppia viene creata quando entrambe le estremità dell'arco hanno dichiarato l'intento l'una verso l'altra (o quando il template di era autorizza il consenso implicito). Un design a meccanismo singolo è stato respinto. Eseguire Gale-Shapley a ogni tick ri-stabilizzerebbe l'intero mercato delle relazioni a ogni iterazione, dissolvendo e ri-accoppiando le coppie esistenti mentre i punteggi relativi derivano, il che è sociologicamente implausibile (le coppie reali hanno costi di switching) e computazionalmente `O(n²)` per tick. Eseguire pura risoluzione di intenti all'inizializzazione lascerebbe la popolazione fondatrice statisticamente arbitraria, con coppie formate da qualunque agente capitasse di essere processato per primo piuttosto che da preferenza reciproca. Il design ibrido — abbinamento stabile una volta a `t = 0`, settlement guidato dall'intento successivamente — ottiene gli invarianti giusti da ciascun regime. Il matrimonio combinato è stratificato sopra il meccanismo di runtime piuttosto che implementato come percorso di codice separato. Goode (1963) descrive il matrimonio combinato come un sistema in cui il proponente è un genitore che agisce per conto di un figlio non sposato, e il figlio mantiene un diritto di veto strutturalmente più debole ma non zero; Epocha rappresenta questo con un'estensione a due passaggi della stessa azione `pair_bond`, dove il Pass A raccoglie intenti diretti scritti dall'agente stessa e il Pass B raccoglie intenti parentali `for_child` che sono onorati solo quando il figlio non ha già dichiarato un intento diretto nel Pass A. L'ordinamento a due passaggi preserva l'asimmetria di Goode — il genitore può iniziare, ma la dichiarazione propria del figlio vince sempre — senza introdurre un'azione `arranged_pair_bond` separata che gonfierebbe lo spazio di azione dell'LLM. L'invariante canonico di ordinamento `agent_a.id < agent_b.id` è imposto al livello del modello da una `CheckConstraint`, non come convenzione soft, perché due righe che rappresentano la stessa coppia con FK scambiate corromperebbero silenziosamente la risoluzione di eredità e doppierebbero il conteggio delle coppie attive nello snapshot di popolazione; un singolo helper `_ordered_pair()` è l'unico percorso attraverso cui si raggiunge `Couple.objects.create()`.

**Modello.** Il punteggio di compatibilità tra due partner candidati segue il framework di omogamia di Kalmijn (1998), che decompone l'accoppiamento assortativo in un piccolo numero di dimensioni socio-economiche pesate per la loro salienza culturale nell'era in studio. Il punteggio pesato in Epocha prende quattro componenti — similarità di classe, prossimità di istruzione, prossimità di età e sentimento relazionale esistente — ognuno normalizzato a `[0, 1]` prima della pesatura:

```
hg(a, b; w, τ) = w_class · 1[class(a) = class(b)]
               + w_edu   · exp(-|e(a) - e(b)|)
               + w_age   · exp(-|age(a) - age(b)| / τ)
               + w_rel   · ((sent(a, b) + 1) / 2)            (4.6)
```

L'equazione (4.6) è l'implementazione di `homogamy_score(a, b, weights, age_tolerance_years=10.0)` in `epocha/apps/demography/couple.py:60-95`. I quattro pesi `w_class`, `w_edu`, `w_age`, `w_rel` sommano a uno in ciascun template di era e spostano l'importanza relativa delle dimensioni strutturali rispetto a quelle affettive tra le ere (Tabella 4.5). Il termine relazionale legge `Relationship.sentiment ∈ [-1, 1]` dallo strato agente e lo piega in `[0, 1]` con la mappa affine standard; quando non esiste una riga `Relationship` il termine ha come default `0.5` (neutro), così il punteggio resta ben definito per candidati precedentemente sconosciuti. Il kernel esponenziale sulla prossimità di età usa `τ = 10.0` anni come tolleranza di default, corrispondendo all'ordine di grandezza delle distribuzioni di age-gap attestate nella letteratura demografica; `τ` è un argomento di funzione piuttosto che un campo per-era a partire dal commit fissato ed è mantenuto costante tra i template in attesa della calibrazione del Plan 4.

Il meccanismo di inizializzazione applica l'accettazione differita di Gale-Shapley sulla funzione punteggio (4.6). Con la popolazione maschile eleggibile come lato proponente e la popolazione femminile eleggibile come lato rispondente (o viceversa — l'algoritmo è simmetrico in correttezza, asimmetrico solo nella ben nota proprietà proposer-optimal che Gale e Shapley 1962 dimostrano), l'algoritmo gira:

```
function stable_matching(P, R, score_fn):                     (4.7)
    rank[p] = sort(R, key=lambda r: -score_fn(p, r))     ∀ p ∈ P
    score[r][p] = score_fn(p, r)                          ∀ r ∈ R, p ∈ P
    free = list(P)
    engaged = {}                                          # respondent → proposer
    next_idx = {p: 0 for p in P}
    while free:
        p = free.pop(0)
        if next_idx[p] >= len(rank[p]): continue
        r = rank[p][next_idx[p]]; next_idx[p] += 1
        if r not in engaged:
            engaged[r] = p
        elif score[r][p] > score[r][engaged[r]]:
            free.append(engaged[r]); engaged[r] = p
        else:
            free.append(p)
    return [(p, r) for r, p in engaged.items()]
```

L'equazione (4.7) è l'algoritmo canonico di accettazione differita di Gale e Shapley (1962, Teoremi 1 e 2): l'esistenza di un abbinamento stabile è garantita, il risultato è proposer-optimal, e la complessità è `O(|P|·|R|)` nel caso peggiore. L'implementazione in `couple.py:98-150` è una trascrizione diretta della forma da manuale, con un adattamento Epocha-specifico: quando `|P| ≠ |R|`, il lato più piccolo è completamente abbinato e il lato più grande ha un residuo non abbinato, che è l'esito demograficamente realistico (alcuni adulti restano single).

Il meccanismo di runtime è un risolutore tick+1 sulle entry `DecisionLog` scritte al tick precedente. La struttura a due passaggi richiesta dalla semantica del matrimonio combinato di Goode (1963) è:

```
function resolve_pair_bond_intents(simulation, tick, rng):    (4.8)
    template = load_template(simulation.config.demography_template)
    consent  = template.couple.implicit_mutual_consent
    entries  = DecisionLog.filter(sim, tick-1, contains '"pair_bond"')
    direct, arranged = {}, []
    # Pass A: direct intents (agent acts on her own behalf)
    for e in entries:
        d = json.loads(e.output_decision); if d.action ≠ 'pair_bond': continue
        if d.target.for_child: arranged.append((child_id, match_id)); continue
        direct[e.agent.id].append(match_id)
    # Pass B: arranged intents only where child has no direct intent
    for (child_id, match_id) in sorted(arranged):
        if child_id in direct: continue          # child's own choice wins
        direct[child_id].append(match_id)
    # Resolution: deterministic ordering, mutual or implicit consent
    used = set(); formed = []
    with transaction.atomic():
        for proposer_id in sorted(direct):
            if proposer_id in used: continue
            for target_id in direct[proposer_id]:
                if target_id in used: continue
                mutual = (proposer_id in direct.get(target_id, []))
                if not mutual and not consent: continue
                formed.append(form_couple(proposer, target, formed_at_tick=tick))
                used.update({proposer_id, target_id}); break
    return formed
```

L'equazione (4.8) è l'implementazione di `resolve_pair_bond_intents()` in `couple.py:178-316`. Pass A e Pass B sono il fix di risoluzione audit B2-06 che dà all'asimmetria di Goode il suo significato operativo (il genitore propone, il figlio può sovrascrivere dichiarando il proprio intento). Il `sorted()` deterministico sugli id dei proponenti e sulle tuple combinate è il fix di risoluzione audit B2-03: due esecuzioni con lo stesso seed RNG devono produrre lo stesso abbinamento, il che richiede che l'ordine di iterazione sia chiave-id piuttosto che dipendente dall'ordine di inserimento. Il JSON `output_decision` malformato è loggato a livello WARNING (fix audit B2-02) piuttosto che saltato silenziosamente, così che un bug di parsing non possa far sparire intenti senza traccia. L'intero risolutore gira all'interno di un singolo blocco `transaction.atomic()`: o tutte le coppie per il tick vengono committate, o nessuna, il che preserva l'invariante della Population Snapshot che `couples_active(tick)` è il conteggio dopo un passo di settlement completo. Gli oggetti Couple sono sempre creati attraverso `form_couple(agent_x, agent_y, formed_at_tick, couple_type='monogamous')` in `couple.py:153-175`, che a sua volta chiama l'helper `_ordered_pair()` che impone l'invariante di ordinamento canonico prima di delegare a `Couple.objects.create()`.

**Parametri.** I parametri di formazione delle coppie per-era sono caricati dagli stessi template JSON di mortalità e fertilità, sotto la chiave `couple`. La Tabella 4.5 elenca i valori spediti con i cinque template del Plan 1. Il campo `marriage_market_type` seleziona tra `autonomous` (l'agente stessa scrive l'intento `pair_bond`) e `arranged` (un agente genitore scrive l'intento per conto di un figlio non sposato via il payload `for_child`); lo stesso set di cinque template porta `arranged` solo su `pre_industrial_islamic`, con gli altri quattro template impostati a `autonomous`. Il flag `implicit_mutual_consent` governa se il risolutore richiede che entrambe le estremità dell'arco abbiano dichiarato l'intento (`false`) o onora una dichiarazione unilaterale finché il target è eleggibile (`true`); tutti e cinque i template del Plan 1 spediscono con `implicit_mutual_consent: true` e il campo è registrato nella Tabella 4.5 come valore uniforme piuttosto che come differenziatore per-era. Il flag `divorce_enabled` regola `resolve_separate_intents()`: quando `false`, il risolutore restituisce immediatamente una lista vuota senza scansionare `DecisionLog`, il che modella il regime canonico cattolico di indissolubilità del matrimonio portato da `pre_industrial_christian`; quando `true`, gli intenti separate dichiarati al tick `T-1` dissolvono la coppia attiva al tick `T` con `dissolution_reason = 'separate'`.

Tabella 4.5 — Parametri di formazione delle coppie per-era (template spediti nel Plan 1).

| Template di era              | `marriage_market_type` | `divorce_enabled` | `min_age` (M / F) | `mourning_ticks` | `marriage_market_radius` |
|------------------------------|------------------------|-------------------|-------------------|------------------|--------------------------|
| `pre_industrial_christian`   | `autonomous`           | false             | 16 / 14           | 365              | `same_zone`              |
| `pre_industrial_islamic`     | `arranged`             | true              | 16 / 14           | 365              | `same_zone`              |
| `industrial`                 | `autonomous`           | true              | 18 / 16           | 180              | `adjacent_zones`         |
| `modern_democracy`           | `autonomous`           | true              | 18 / 18           | 90               | `world`                  |
| `sci_fi`                     | `autonomous`           | true              | 18 / 18           | 30               | `world`                  |

Tutti e cinque i template spediscono con `allowed_types = ["monogamous", "arranged"]`, `default_type = "monogamous"` e `implicit_mutual_consent = true`. I pesi di omogamia variano tra le ere per riflettere la salienza culturale di ciascuna dimensione di Kalmijn (1998) sotto regimi storici diversi (Tabella 4.6): i due template pre-industriali e il template industriale mettono peso sostanziale sulla classe sociale, che perde terreno nel template della democrazia moderna a favore della prossimità di istruzione, e il template speculativo `sci_fi` declassa la classe quasi interamente a favore del sentimento relazionale.

Tabella 4.6 — Pesi di omogamia per-era per l'equazione (4.6).

| Template di era              | `w_class` | `w_edu` | `w_age` | `w_rel` |
|------------------------------|----------:|--------:|--------:|--------:|
| `pre_industrial_christian`   | 0.40      | 0.25    | 0.20    | 0.15    |
| `pre_industrial_islamic`     | 0.40      | 0.25    | 0.20    | 0.15    |
| `industrial`                 | 0.35      | 0.30    | 0.20    | 0.15    |
| `modern_democracy`           | 0.20      | 0.40    | 0.20    | 0.20    |
| `sci_fi`                     | 0.10      | 0.30    | 0.20    | 0.40    |

Nota: la chiave del template JSON è scritta `w_relationship`; il simbolo `w_rel` nell'equazione (4.6) e nella Tabella 4.6 è il nome matematico abbreviato.

Il parametro `age_tolerance_years` `τ` dell'equazione (4.6) è mantenuto al valore di default `10.0` in tutti i template, come argomento di funzione di `homogamy_score()` piuttosto che come campo per-template; sollevarlo nello schema del template è documentato come deliverable di calibrazione del Plan 4.

**Algoritmo.** Tre operazioni coordinate compongono il ciclo di vita della coppia. All'inizializzazione, il builder della popolazione fondatrice chiama `stable_matching(proposers, respondents, score_fn)` una volta con `score_fn = lambda p, r: homogamy_score(p, r, era_weights)` e le sottopopolazioni adulte eleggibili come i due lati; ogni coppia `(p, r)` restituita viene poi instradata attraverso `form_couple()` per materializzare la riga del database con l'invariante di ordinamento canonico imposto. A runtime, lo step di demografia chiama `resolve_pair_bond_intents(simulation, tick, rng)` una volta per tick, che legge le entry `DecisionLog` scritte al tick `T-1` con il pre-filtro SQL `__contains` `'"pair_bond"'` e verifica ogni match con `json.loads()`, esegue l'ingestione a due passaggi (intenti diretti nel Pass A, intenti combinati `for_child` nel Pass B con override di priorità del figlio), e crea coppie in ordine deterministico ordinato per id sotto un singolo `transaction.atomic()`. Una coppia in cui uno dei partner è già in una coppia attiva — controllato da `is_in_active_couple()` contro il vincolo unique-active-couple che il fix B2-01 ha aggiunto — viene saltata, così le coppie attive duplicate non possono essere create anche sotto invocazioni ripetute del risolutore o chord worker. Il risolutore companion `resolve_separate_intents(simulation, tick)` legge le entry `DecisionLog` `'"separate"'` dal tick `T-1` con lo stesso pattern JSON, restituisce immediatamente quando il template di era ha `divorce_enabled: false`, e altrimenti marca la coppia attiva di ogni dichiarante come `dissolved_at_tick = tick`, `dissolution_reason = 'separate'`. La terza operazione, `dissolve_on_death(deceased_agent, tick)` in `couple.py:369-392`, è invocata dal percorso di risoluzione della mortalità quando muore un agente accoppiato: annulla la FK appropriata (`agent_a` o `agent_b` a seconda del lato in cui era il deceduto), cattura il nome del deceduto nel campo `*_name_snapshot` corrispondente così che il record genealogico sopravviva al cascade FK, imposta `dissolution_reason = 'death'`, e persiste con un singolo save `update_fields=[...]`. A partire dal commit fissato, questo percorso di dissoluzione è una normale chiamata di funzione piuttosto che un signal handler Django — la spec ha considerato un segnale `agents.Agent` `post_save` in ascolto sulle transizioni `is_alive` e l'ha respinto sulla base che i segnali aggiungono accoppiamento nascosto e sono più difficili da auditare di un'invocazione esplicita dal modulo di mortalità. Il ciclo di vita della coppia è esercitato dalla suite di unit test della demografia (`epocha/apps/demography/tests/test_couple.py`) ma, coerentemente con il gap notato in §4.1.1 e §4.1.2, nessuna di `stable_matching()`, `resolve_pair_bond_intents()`, `resolve_separate_intents()` o `dissolve_on_death()` è invocata da `epocha/apps/simulation/engine.py` o `epocha/apps/simulation/tasks.py` a partire dal commit fissato (un `grep` per i nomi delle funzioni fuori da `epocha/apps/demography/` restituisce solo commenti in `engine.py:265-272` che descrivono la semantica di risoluzione tick+1 e il ruolo dell'azione `pair_bond` nella pipeline di decisione). L'integrazione nel ciclo di tick live è tracciata accanto ai gap equivalenti di mortalità e fertilità come deliverable del Plan 4 (Inizializzazione, integrazione del motore e validazione storica).

**Semplificazioni.** L'implementazione attuale omette deliberatamente quattro raffinamenti che la letteratura di demografia familiare tratta come estensioni proprie piuttosto che correzioni del meccanismo baseline. Primo, sono rappresentabili solo coppie monogamiche: il modello `Couple` porta esattamente due foreign key, e la spec registra i tipi di coppia poliginici e poliandrici come rinviati (fix audit MISS-8) perché supportare più di due partner richiederebbe di rilassare il vincolo `unique_active_couple` e rilavorare il percorso di risoluzione di eredità; l'enum `couple_type` espone `monogamous` e `arranged` come i due valori canonici, con `arranged` che indica il percorso di formazione (mediato dai genitori) piuttosto che una distinzione sul numero dei partner. Secondo, lo strato agente porta tre valori di genere (`male`, `female`, `non_binary`) e quattro valori di orientamento sessuale (`heterosexual`, `homosexual`, `bisexual`, `asexual`) in `agents/models.py:11-20`, ma il punteggio di omogamia e l'algoritmo di abbinamento stabile delle equazioni (4.6) e (4.7) non consumano questi campi a partire dal commit fissato: il filtraggio dei candidati per genere e orientamento è responsabilità del chiamante che costruisce le liste `proposers` e `respondents`, e il builder della popolazione fondatrice che esegue quel filtraggio per configurazioni non eterosessuali o non binarie è esso stesso parte del deliverable di inizializzazione del Plan 4. Terzo, nessun cooldown di rimaritamento è imposto oltre il campo per-era `mourning_ticks` riportato nella Tabella 4.5: il campo è caricato dal template ma non ancora consumato da alcun percorso di codice, quindi un agente vedovo può in principio ri-accoppiarsi al tick successivo alla morte del partner; cablare `mourning_ticks` nel controllo di eleggibilità di `resolve_pair_bond_intents()` è una modifica di una riga riservata al Plan 4. Quarto, Gale-Shapley è applicato solo all'inizializzazione, non come fallback a runtime quando si accumula una grande coorte non abbinata: il meccanismo per-tick è esclusivamente guidato dall'intento, sull'assunzione che gli agenti LLM dichiareranno intenti `pair_bond` a un tasso coerente con il mercato matrimoniale della popolazione; se la suite di validazione del Capitolo 7 rivela una sotto-formazione sistematica, una riapplicazione periodica della primitiva di abbinamento sugli adulti eleggibili non abbinati è l'estensione naturale ed è documentata nella spec di demografia sotto la voce Limitazioni note.



## 4.2 Economia — Integrazione comportamentale

> Stato: implementato a partire dal commit `8a2bc714477f445b46cd610725df40c93fce1557`, audit della spec CONVERGENTE 2026-04-15.

Il Capitolo 4.2 documenta lo strato comportamentale che si appoggia sul substrato economico di §3.6. Il substrato di §3.6 è la parte del modello che non dipende dalla psicologia dell'agente: possiede la tecnologia di produzione, gli aggregati monetari, il clearing Walrasiano dei mercati a tick singolo e la distribuzione per-tick dell'output in salari, rendite e tasse. Tre famiglie di comportamento — aspettative di prezzo backward-looking, dinamiche intertemporali di credito e bilancio bancario, e mercato immobiliare ancorato a Gordon — sono state specificate nel design economy-behavioral-integration del 2026-04-15 e auditate fino a convergenza sotto quel documento. Ogni famiglia è implementata in un singolo modulo Python sotto `epocha/apps/economy/`: `expectations.py` per il motore di aspettative adattive di Nerlove (1958) descritto in §4.2.1, `credit.py` e `banking.py` per la macchina credito-e-banca a riserva frazionaria di Diamond-Dybvig (1983) descritta in §4.2.2, e `property_market.py` per il mercato immobiliare con valutazione Gordon e settlement a tick `T+1` descritto in §4.2.3. I tre moduli sono cablati nel tick economico canonico orchestrato da `epocha/apps/economy/engine.py:process_economy_tick_new()`, che è esso stesso dispatched dal ciclo di tick della simulazione in `epocha/apps/simulation/engine.py:394` ogniqualvolta la simulazione ha il nuovo data layer economico inizializzato; di conseguenza, a differenza dei moduli di demografia di §4.1.x, l'economia comportamentale descritta in questo capitolo è genuinamente live nella pipeline per-tick a partire dal commit fissato, e gli header `Stato` portati da §4.2.1–§4.2.3 registrano solo la data di convergenza dell'audit della spec piuttosto che un caveat di integrazione pendente.

### 4.2.1 Aspettative adattive (Cagan 1956)

> Stato: implementato a partire dal commit `8a2bc714477f445b46cd610725df40c93fce1557`, audit della spec CONVERGENTE 2026-04-15.

**Background.** Le aspettative adattive entrano nella pipeline di tick di Epocha perché lo strato di decisione guidato da LLM ha bisogno di un forecast per-agente dei prezzi del prossimo tick per ogni bene scambiabile, e la famiglia di forecast che il modello richiede deve essere esprimibile in tre proprietà concrete: deve essere locale — ogni agente ha il proprio forecast, persistito tra i tick — così che personalità e storia possano spostarlo; deve essere definita sotto razionalità limitata — gli agenti non conoscono il vero processo che genera i dati — così che il forecast possa essere sbagliato in modi che il modello può studiare piuttosto che imporre coerenza con aspettative razionali per costruzione; e deve essere computabile in `O(n_agents · n_goods)` per tick senza risolvere un punto fisso, dato che la pipeline di tick porta già il tatonnement Walrasiano di §3.6 e una seconda ottimizzazione annidata dominerebbe il costo. L'alternativa canonica delle aspettative razionali Muthiane (1961) è stata respinta sul secondo e terzo conto: richiede che ogni agente conosca il processo stocastico congiunto di tutti i prezzi e internalizzi il modello che il modellatore sta usando, cosa che né l'LLM né la pipeline di decisione modulata dalla personalità di §3.2 possono fornire, e richiederebbe una risoluzione di punto fisso per-tick su credenze eterogenee che è incompatibile con l'inviluppo di costo. La famiglia delle aspettative adattive — formalizzata per la prima volta da Cagan (1956) per il forecasting dell'iperinflazione e indipendentemente da Nerlove (1958) nella letteratura del modello cobweb per l'offerta agricola — risolve tutti e tre i vincoli con un singolo aggiornamento ricorsivo parametrizzato da un tasso di adattamento `λ ∈ (0, 1)`: i forecast sono locali perché ogni agente porta il proprio stato, bounded-rational perché la regola di aggiornamento non richiede di conoscere il vero processo, e `O(1)` per agente per bene per tick perché la ricorsione sostituisce l'ottimizzazione. L'implementazione fissata trascrive la forma di Nerlove della ricorsione (l'espressione del manuale che appare nelle derivazioni del teorema cobweb) e accredita Nerlove (1958) nel docstring del modulo di `epocha/apps/economy/expectations.py:1-23`; la genealogia di Cagan (1956) è riconosciuta in §2.4 di questo whitepaper e rimane l'ancora più vecchia per l'interpretazione di forecasting dell'inflazione della stessa ricorsione. I due paper descrivono la stessa regola di aggiornamento sottostante espressa in forme equivalenti, e la scelta di attribuzione a livello di commento di codice riflette l'applicazione in stile cobweb (forecast prezzo-per-bene) piuttosto che un disaccordo sostantivo con la formulazione di Cagan.

**Modello.** Ogni agente mantiene, per ogni categoria di bene nella simulazione, una riga del modello `AgentExpectation` dichiarato in `epocha/apps/economy/models.py:527-585` che porta un `expected_price`, una categoria `trend_direction ∈ {rising, falling, stable}`, uno scalare `confidence ∈ [0, 1]`, e il `lambda_rate` per-agente effettivamente usato per l'aggiornamento al tick precedente (così che il valore sia auditabile piuttosto che ricomputato on demand). La ricorsione che aggiorna `expected_price` tra i tick è la regola canonica delle aspettative adattive:

```
E_{t+1}[p] = λ · p_t + (1 − λ) · E_t[p]                         (4.9)
```

L'equazione (4.9) è l'implementazione dell'espressione interna in `update_agent_expectations()` a `epocha/apps/economy/expectations.py:209-211`, dove `p_t` è il prezzo di mercato effettivo al tick `t` per il bene nella zona dell'agente (letto da `ZoneEconomy.market_prices` popolato dal tick precedente del substrato di §3.6) e `E_t[p]` è il prezzo atteso precedente dell'agente per lo stesso bene. Il paper sull'iperinflazione di Cagan (1956) scrive lo stesso aggiornamento nella forma equivalente di correzione dell'errore `E_{t+1}[π] = E_t[π] + λ · (π_t − E_t[π])`, che è algebricamente identica alla (4.9) dopo un riarrangiamento di una riga; l'implementazione ha scelto la forma a combinazione convessa perché non richiede di materializzare l'errore di previsione come variabile intermedia. Il tasso di adattamento `λ` per-agente è esso stesso una funzione del vettore di personalità Big Five dell'agente piuttosto che un singolo scalare fissato sulla popolazione, che è l'estensione sostantiva di Epocha della ricorsione da manuale. La modulazione di personalità, implementata in `compute_lambda_from_personality()` (`expectations.py:43-80`), è una deviazione lineare dal `λ_base` del template di era centrata sulla media di popolazione di 0.5 per ogni tratto:

```
λ(agent) = clip( λ_base
               + (N(agent) − 0.5) · n_mod
               + (O(agent) − 0.5) · o_mod
               − (C(agent) − 0.5) · c_mod ,
               0.05, 0.95 )                                     (4.10)
```

L'equazione (4.10) legge `N`, `O`, `C` come i punteggi di Neuroticismo, Apertura e Coscienziosità dell'agente dal vettore di personalità (con default alla media di popolazione di 0.5 quando il tratto è mancante) e applica i tre coefficienti di modulazione `n_mod`, `o_mod`, `c_mod` dal blocco `expectations_config` del template di era. I segni dei tre contributi seguono Costa e McCrae (1992): alto Neuroticismo aumenta la reattività ai nuovi segnali di prezzo (contributo positivo), alta Apertura aumenta la ricettività al cambiamento (contributo positivo), e alta Coscienziosità ancora il forecast all'aspettativa precedente (contributo negativo). Il clip a `[0.05, 0.95]` dichiarato come costanti strutturali `_LAMBDA_MIN` e `_LAMBDA_MAX` a `expectations.py:39-40` è documentato nel modulo come bound strutturale non-tunable piuttosto che come parametro libero: a `λ = 0.05` il forecast è essenzialmente statico (l'aspettativa precedente è preservata con peso trascurabile sulla nuova osservazione), e a `λ = 0.95` il forecast collassa a un'aspettativa naive (il prezzo del prossimo tick uguale al prezzo dell'ultimo tick); entrambi gli estremi sono degeneri come aspettative adattive e il clip impedisce a una sfortunata combinazione di punteggi di personalità e coefficienti di modulazione di portare un agente in uno dei due limiti. Il campo `trend_direction` è aggiornato dall'helper `detect_trend(expected, actual, threshold)` (`expectations.py:83-107`), che classifica il movimento da `expected` ad `actual` come `rising` quando `actual > expected · (1 + threshold)`, come `falling` quando `actual < expected · (1 − threshold)`, e come `stable` altrimenti; la soglia è il campo `trend_threshold` dell'`expectations_config` del template di era (default `0.05`, identico in tutti e cinque i template del Plan 1), ed è un parametro di design tunabile piuttosto che un valore derivato da uno specifico studio empirico. Il campo `confidence` è incrementato di `+0.05` quando l'aspettativa precedente dell'agente era entro `trend_threshold` dal prezzo realizzato e decrementato di `−0.05` altrimenti, clampato a `[0, 1]` (`expectations.py:215-226`); lo step `±0.05` è anch'esso un parametro di design tunabile ed è documentato inline come tale.

**Parametri.** Tutti e cinque i template di era spediti con il Plan 2 portano lo stesso blocco `expectations_config`, popolato da `_behavioral_config()` in `epocha/apps/economy/template_loader.py:179-196`. I valori sono seedati da una singola fonte nel loader piuttosto che inscritti ridondantemente in cinque file JSON perché nessuna delle evidenze di calibrazione del Plan 2 auditate ha motivato una differenziazione era-specifica al momento in cui i template sono stati congelati; la differenziazione per-era di `λ_base` e dei coefficienti di modulazione è un deliverable di calibrazione del Plan 4. La Tabella 4.7 registra i valori seed esplicitamente così che l'omogeneità sia visibile al lettore.

Tabella 4.7 — Parametri delle aspettative adattive seedati da `_behavioral_config()` (identici in tutti e cinque i template del Plan 1 in attesa della calibrazione del Plan 4).

| Parametro             | Valore seed | Ruolo semantico                                                            |
|-----------------------|------------:|----------------------------------------------------------------------------|
| `lambda_base`         |        0.30 | Tasso di adattamento di baseline prima della modulazione di personalità    |
| `neuroticism_mod`     |        0.15 | Magnitudine del contributo positivo del Neuroticismo al `λ` per-agente     |
| `openness_mod`        |        0.10 | Magnitudine del contributo positivo dell'Apertura al `λ` per-agente        |
| `conscientiousness_mod` |      0.10 | Magnitudine del contributo negativo della Coscienziosità al `λ` per-agente |
| `trend_threshold`     |        0.05 | Deviazione frazionale da `expected_price` richiesta per cambiare `trend_direction` |

I bound strutturali `_LAMBDA_MIN = 0.05` e `_LAMBDA_MAX = 0.95` sull'output per-agente di (4.10) non sono nella Tabella 4.7 perché sono codificati come costanti in `expectations.py:39-40` piuttosto che come campi del template, sulla base che un bound strutturale che impedisce forecast degeneri è una proprietà del modello piuttosto che una scelta di calibrazione.

**Algoritmo.** Ad ogni tick, l'orchestratore dell'economia invoca `update_agent_expectations(simulation, tick)` (`expectations.py:110-251`) prima del market clearing, così che i forecast per-agente che il substrato di §3.6 consulta durante il clearing riflettano i prezzi realizzati del tick precedente piuttosto che i prezzi che vengono calcolati al tick corrente. La funzione legge l'`expectations_config` a livello di simulazione popolato al tempo del caricamento del template, materializza la mappa di prezzi effettivi aggregando `ZoneEconomy.market_prices` su tutte le zone con la media cross-zona non pesata (`aggregate_system_prices`, la stessa aggregazione che l'orchestratore usa per gli snapshot di prezzo di sistema; documentata inline come target di raffinamento multi-zone), e fa bulk-fetch delle righe `AgentExpectation` esistenti per la simulazione in un singolo dizionario chiavato per `(agent_id, good_code)` così che il loop per-agente giri senza query N+1. Per ogni agente vivo il `λ` per-tick è calcolato una volta dalla personalità dell'agente e dai coefficienti di modulazione dell'era, poi per ogni bene con un prezzo effettivo la funzione o crea una nuova `AgentExpectation` inizializzata al prezzo realizzato con `confidence = 0.5` e `trend_direction = "stable"` (prima osservazione) o aggiorna una riga esistente applicando la (4.9) con il `λ` per-agente, chiamando `detect_trend()` contro l'aspettativa precedente e il nuovo prezzo realizzato, e aggiustando `confidence` con la regola di errore di previsione. Le righe appena create e aggiornate sono flushate in due chiamate terminali `bulk_create` e `bulk_update` così che l'intera passata sia due scritture per tick indipendentemente dal conteggio degli agenti. Lo step dell'orchestratore in `engine.py:210-214` registra la chiamata nel ciclo economico canonico a 9 step come `STEP 0: EXPECTATIONS UPDATE (Nerlove adaptive)`, e il call site è raggiunto incondizionatamente ogniqualvolta `process_economy_tick_new()` è dispatched dal motore di simulazione, che esso stesso è dispatched ogniqualvolta la simulazione ha i record `Currency` che marcano il nuovo data layer economico come inizializzato (`epocha/apps/simulation/engine.py:380-398`). Di conseguenza, in contrasto con i moduli di demografia di §4.1.x, il motore di aspettative adattive descritto qui è genuinamente attivo nel ciclo di tick live a partire dal commit fissato, e le righe `AgentExpectation` per-tick che produce sono consumate downstream dal context builder dell'LLM in `epocha/apps/economy/context.py:170-208` per renderizzare il blocco di valutazione dei prezzi dell'agente al momento della decisione.

**Semplificazioni.** L'implementazione attuale omette deliberatamente quattro raffinamenti che la letteratura sulle aspettative adattive tratta come estensioni proprie piuttosto che correzioni della ricorsione baseline. Primo, viene fatto forecast solo del livello di prezzo per ogni bene; la ricorsione è single-variable per bene, e non c'è un forecast congiunto tra beni, nessun forecast di inflazione come variabile separata distinta dal forecast di prezzo per-bene, e nessun forecast di secondo momento (volatilità, dispersione). L'applicazione originale di Cagan (1956) all'iperinflazione fa forecast del tasso di inflazione `π` piuttosto che del livello di prezzo `p`, e l'implementazione Epocha potrebbe essere estesa a un forecast di inflazione derivato avvolgendo la ricorsione di prezzo per-bene in una log-differenza tick-su-tick; la spec registra questo come raffinamento rinviato sotto il log di risoluzione audit del documento di design del 2026-04-15. Secondo, il `λ` per-agente è omogeneo tra i beni all'interno di un singolo agente: lo stesso `λ` modulato dalla personalità è applicato a ogni riga `AgentExpectation` posseduta dall'agente, senza differenziazione bene-specifica. Un agente più ricco che alloca più attenzione cognitiva ai beni ad alto impatto potrebbe in principio portare un `λ` più alto per i beni che dominano il budget familiare e un `λ` più basso per i beni marginali; la spec lascia questo come raffinamento futuro e l'implementazione tratta l'omogeneità come scelta deliberata di scope per l'economia del Plan 2. Terzo, il tasso di adattamento `λ` non è esso stesso appreso: la modulazione Big Five in (4.10) è una mappatura statica dalla personalità a `λ`, senza meccanismo per cui un agente i cui forecast sono stati sistematicamente sbagliati aggiorni il proprio `λ` verso l'alto (per reagire di più alle sorprese) o verso il basso (per ancorare di più sul precedente). Le estensioni di apprendimento Bayesiano delle aspettative adattive (Evans e Honkapohja 2001) forniscono il formalismo canonico per `λ` come parametro appreso; l'implementazione Epocha traccia l'accuratezza di previsione attraverso il campo `confidence` ma non riporta `confidence` in `λ` nel commit fissato, sulla base che farlo richiederebbe una calibrazione di secondo ordine non consegnata nel Plan 2. Quarto, l'aggregazione di prezzo multi-zone è implementata come media cross-zona non pesata di `ZoneEconomy.market_prices` via `aggregate_system_prices` (in sostituzione di un precedente merge last-write-wins il cui risultato dipendeva dall'ordine di ritorno delle zone dal database) piuttosto che come forecast per-zona per ogni agente: un agente nella zona A vede lo stesso prezzo effettivo per un bene di un agente nella zona B anche quando le due zone si sono cleared a prezzi diversi nel tick precedente. L'aggregazione è documentata inline come semplificazione MVP (`expectations.py:146-159`) e la differenziazione per-zona è l'estensione naturale una volta che l'economia multi-zone di §3.6 è esercitata dalla suite di validazione del Capitolo 7.

### 4.2.2 Credito e banca (Diamond-Dybvig 1983, riserva frazionaria)

> Stato: implementato a partire dal commit `8a2bc714477f445b46cd610725df40c93fce1557`, audit della spec CONVERGENTE 2026-04-15.

**Background.** Lo strato credito-e-banca entra nella pipeline di tick di Epocha perché lo spazio di decisione dell'agente documentato in §3.2 porta un'azione esplicita `request_loan` e una dipendenza implicita su un aggregato monetario stabile, e nessuno dei due può essere soddisfatto dal substrato di §3.6 in isolamento: il substrato esegue il clearing dei mercati di beni a tick singolo e distribuisce salari e rendite, ma non rappresenta i contratti intertemporali che connettono una decisione di prestito al tick `T` all'obbligazione di rimborso al tick `T+k` che vincola la cassa futura del debitore, né porta gli aggregati di bilancio bancario il cui deterioramento produce i segnali di rischio sistemico che il context builder dell'LLM di §3.5 ha bisogno di alimentare nella pipeline di decisione. Diamond e Dybvig (1983) è il riferimento canonico per la banca a riserva frazionaria sotto dinamiche di fiducia dei depositanti: una singola banca prende depositi, presta una frazione di essi, tiene il resto come riserve, ed è esposta a un equilibrio self-fulfilling di corsa agli sportelli quando la fiducia dei depositanti scende sotto una soglia e i depositanti ritirano più velocemente di quanto i prestiti in maturazione possano essere liquidati. L'implementazione Epocha trascrive la dinamica qualitativa — la fiducia si erode quando le riserve scendono sotto il rapporto richiesto, l'erosione si trasmette come memorie di preoccupazione a livello di agente, e la trasmissione stessa accelera l'erosione attraverso la pipeline di decisione mediata dall'LLM — ma omette deliberatamente due elementi quantitativi del modello originale di Diamond-Dybvig. Primo, il modello è una singola banca aggregata per simulazione piuttosto che una popolazione di banche concorrenti (il mercato interbancario che modella il contagio nella letteratura empirica sulle corse agli sportelli è rinviato), e di conseguenza non c'è canale di prestito interbancario e nessun prestatore di ultima istanza della banca centrale. Secondo, la condizione originale di corsa agli sportelli di Diamond-Dybvig accoppia bassa fiducia con insolvenza attraverso un gioco di coordinamento sui tipi di ritiro dei depositanti; la convergenza dell'audit del 2026-04-15 (fix audit C-3) ha sostituito la condizione accoppiata con il trigger più semplice `confidence_index < 0.5` valutato indipendentemente dallo stato di solvibilità, sulla base che la popolazione guidata dall'LLM è completamente eterogenea nel suo stato informativo e l'equivalenza game-theoretic originale non vale puntualmente attraverso un set di agenti LLM. Il pricing dei prestiti segue Stiglitz e Weiss (1981) — i tassi di interesse portano un risk premium proporzionale alla leva del debitore come rappresentazione in forma ridotta dell'incapacità del prestatore di osservare perfettamente il rischio del debitore — e i cascade di default usano il meccanismo di contagio breadth-first di Allen e Gale (2000) cappato a una profondità configurabile.

**Modello.** Lo stato del sistema bancario è una singola riga `BankingState` per simulazione dichiarata in `epocha/apps/economy/models.py:588` e porta `total_deposits`, `total_loans_outstanding`, `reserve_ratio`, `base_interest_rate`, un booleano `is_solvent` e un `confidence_index ∈ [0, 1]`. I prestiti sono righe `Loan` individuali (`models.py:378-482`) con `lender`, `borrower`, `principal`, `interest_rate`, `remaining_balance`, una foreign key opzionale `collateral` a `Property` con `related_name="collateralized_loans"`, un `issued_at_tick`, un `due_at_tick` opzionale, un contatore `times_rolled_over` e uno `status ∈ {active, repaid, rolled_over, defaulted, default_settled}` -- `defaulted` è lo stato da-processare e `default_settled` lo stato terminale che un prestito raggiunge una volta che il suo default è stato gestito, così che un default venga processato esattamente una volta. Il trigger di corsa agli sportelli che guida la trasmissione di memorie di preoccupazione bancaria sotto il fix audit C-3 è la semplice diseguaglianza sul confidence index:

```
broadcast_concern_at_tick(t)  ⇔  BankingState.confidence_index < 0.5     (4.11)
```

L'equazione (4.11) è implementata in `broadcast_banking_concern()` a `epocha/apps/economy/banking.py:337-424`, con la soglia `0.5` dichiarata come costante a livello di modulo `_CONCERN_CONFIDENCE_THRESHOLD` a `banking.py:334`. La condizione è valutata incondizionatamente rispetto a `is_solvent`, che è il cambiamento sostantivo introdotto dal fix audit C-3: il gioco di coordinamento originale di Diamond-Dybvig (1983) prevede una corsa agli sportelli quando sia la fiducia è bassa *sia* la banca è insolvente, ma nella pipeline Epocha la dinamica della fiducia stessa guida `is_solvent` verso `False` nel tempo (`check_solvency()` decrementa `confidence_index` di `0.1` per tick ogniqualvolta le riserve sono insufficienti), quindi la condizione auditata attiva la trasmissione di preoccupazione allo stadio di *paura* piuttosto che solo dopo il fallimento realizzato, che è il pattern empirico documentato nella letteratura sulle corse agli sportelli rivista nella spec. La trasmissione stessa crea una riga `Memory` con `emotional_weight = 0.6` e `source_type = "public"` per un campione casuale di `_CONCERN_BROADCAST_RATIO = 0.5` della popolazione vivente di agenti (`banking.py:381-410`), con una finestra di deduplicazione di `_CONCERN_DEDUP_TICKS = 3` tick allineata alla costante di deduplicazione delle memorie del motore di agenti in `simulation/engine.py`.

La condizione di emissione del prestito combina il cap di garanzia loan-to-value della teoria di razionamento del credito di Stiglitz e Weiss (1981) con una precondizione di solvibilità della banca:

```
approve_loan(borrower, amount, collateral)
  ⇔  collateral.value · LTV ≥ existing_debt(borrower) + amount
  ∧  BankingState.is_solvent                                              (4.12)
```

L'equazione (4.12) è implementata in `evaluate_credit_request()` a `credit.py:172-255`. L'aggregato del debito esistente somma `remaining_balance` sui prestiti attivi del debitore; il rapporto LTV è `credit_config.loan_to_value`, che differisce per template di era. Quando entrambe le condizioni sono soddisfatte, la funzione restituisce il tasso di interesse per-tick calcolato dalla regola di pricing del rischio di Stiglitz-Weiss (1981)

```
r = base_rate · (1 + risk_premium · debt_ratio)
debt_ratio = (existing_debt + amount) / max(borrower.wealth, 1.0)         (4.13)
```

con `base_rate` letto da `BankingState.base_interest_rate`, `risk_premium` di default a `0.5` da `credit_config.risk_premium`, e la leva clampata sul lato della ricchezza per evitare divisione per zero per agenti neonati o indigenti. La forma funzionale è un'approssimazione linearizzata in forma ridotta del modello di selezione avversa di Stiglitz-Weiss — l'originale prevede una relazione non lineare — scelta per trasparenza e per mantenere il costo per-tick della valutazione del credito `O(1)` per richiesta. La logica di pegno della garanzia che seleziona quale proprietà il debitore offre come collaterale è implementata in `find_best_unpledged_property()` ed esclude le proprietà già pegnate a un prestito attivo O in default pendente (`collateralized_loans__status__in=["active", "defaulted"]`): questo estende il fix audit M-6 della convergenza del 2026-04-15, che impedisce alla stessa proprietà di essere doppia-pegnata su due prestiti simultanei (una violazione della semantica di garanzia di Stiglitz-Weiss che l'implementazione pre-audit consentiva), alla finestra di default pendente (R6-COLL-1). Il pegno porta con sé anche un VINCOLO (lien, R6-PROP-1, re-audit Round 6): una proprietà che collateralizza un prestito attivo o in default pendente non può essere messa in vendita né abbinata nel mercato immobiliare di §4.2.3 -- la proprietà può lasciare il debitore solo attraverso il sequestro della pipeline del credito sul default, mai attraverso una vendita di mercato che spoglierebbe il prestatore della sua garanzia.

**Parametri.** Tutti e quattro i template di era spediti con l'app economia portano blocchi `credit_config` e `banking_config` differenziati, popolati da `_behavioral_config()` in `epocha/apps/economy/template_loader.py:144-198`. La differenziazione di era è calibrata contro Homer e Sylla (2005), *A History of Interest Rates*, che cataloga i tassi storici osservati per epoca — il prestito pre-moderno operava al 5-10% per periodo, la transizione industriale del XIX secolo al 4-8%, e le economie moderne ancorate dalla banca centrale all'1-3% — e contro la convenzione del rapporto di riserva di Basilea III che distingue il regime moderno regolato dalla pratica informale precedente. La Tabella 4.8 registra i valori era-specifici esplicitamente così che la differenziazione comparativa tra i template sia visibile al lettore, e la Tabella 4.9 registra i parametri che sono uniformi su tutti e quattro i template perché la convergenza dell'audit del 2026-04-15 non ha trovato evidenza di calibrazione che motivasse una differenziazione per-era allo stadio della spec; la differenziazione per-era di `risk_premium`, `max_rollover` e `default_loan_duration_ticks` è un deliverable di calibrazione del Plan 4.

Tabella 4.8 — Parametri di credito e banca per-era seedati da `_behavioral_config()` in `template_loader.py:144-198`.

| Template          | `loan_to_value` | `base_interest_rate` | `initial_deposits` | `reserve_ratio` |
|-------------------|----------------:|---------------------:|-------------------:|----------------:|
| `pre_industrial`  |            0.50 |                 0.08 |             5 000  |            0.10 |
| `industrial`      |            0.60 |                 0.06 |            20 000  |            0.10 |
| `modern`          |            0.80 |                 0.03 |           100 000  |            0.05 |
| `sci_fi`          |            0.90 |                 0.02 |           500 000  |            0.03 |

Tabella 4.9 — Parametri di credito e banca uniformi su tutti e quattro i template di era in attesa della calibrazione del Plan 4.

| Parametro                          | Valore seed | Ruolo semantico                                                                |
|------------------------------------|------------:|--------------------------------------------------------------------------------|
| `risk_premium`                     |        0.50 | Coefficiente sullo spread di leva del debitore in (4.13); default uniforme codificato a `credit.py:219` (nessun campo del template a partire dal commit fissato; differenziazione per-era in attesa della calibrazione del Plan 4) |
| `max_rollover`                     |           3 | Numero massimo di volte in cui un prestito in maturazione può essere rinnovato prima del default |
| `default_loan_duration_ticks`      |          20 | Durata di default del prestito assegnata da `issue_loan()` quando il chiamante non ne passa una |
| `_CONCERN_CONFIDENCE_THRESHOLD`    |        0.50 | Soglia di (4.11) sotto la quale sono trasmesse le memorie di preoccupazione bancaria |
| `_CONCERN_BROADCAST_RATIO`         |        0.50 | Frazione della popolazione vivente che riceve la trasmissione di preoccupazione per-tick |
| `CASCADE_LOSS_THRESHOLD`           |        0.50 | Frazione della ricchezza del prestatore sopra la quale una perdita per default si propaga al prestatore |

Le costanti strutturali `_CONCERN_CONFIDENCE_THRESHOLD`, `_CONCERN_BROADCAST_RATIO` e `CASCADE_LOSS_THRESHOLD` sono codificate come costanti a livello di modulo in `banking.py:334` e `credit.py:54` piuttosto che come campi del template, sulla base che codificano la forma qualitativa della dinamica di corsa agli sportelli (una profezia auto-avverante ha bisogno di una soglia sotto la quale la paura diventa contagiosa) piuttosto che scelte di calibrazione che variano per era storica. Il valore di `risk_premium` di `0.5` è una scelta di design piuttosto che una misurazione empirica — Stiglitz e Weiss (1981) prevedono che la pendenza del pricing del rischio sia positiva e crescente nella leva ma non forniscono un coefficiente numerico — ed è documentato inline come parametro di design tunabile a `credit.py:215-219`.

**Algoritmo.** Ad ogni tick, l'orchestratore dell'economia invoca lo step del mercato del credito esattamente una volta (regolato da un flag `credit_processed` così che non venga eseguito per-zona) a `epocha/apps/economy/engine.py:445-503`, con la seguente sequenza ordinata di chiamate. Primo, `default_dead_agent_loans(simulation)` (`credit.py:865-893`) manda in default tutti i prestiti attivi il cui debitore ha `is_alive = False`: questo è il fix audit M-3 della convergenza del 2026-04-15, che chiude il gap dell'amnistia silente del debito per cui l'implementazione pre-audit lasciava i prestiti del debitore deceduto in stato `active` indefinitamente, permettendo agli eredi del debitore di ereditare una proprietà ancora gravata da un debito che il sistema non avrebbe mai riscosso. Secondo, `service_loans(simulation, tick)` (`credit.py:377-464`) raccoglie gli interessi per-tick su ogni prestito attivo non ancora giunto a maturità (i prestiti il cui `due_at_tick` è pari o precedente al tick corrente sono esclusi e gestiti interamente dallo step di maturità, così che l'interesse di un periodo sia addebitato esattamente una volta per prestito-tick -- fix R6-NEW-1, esteso a `due_at_tick <= tick` dal catch-up R8-NEW-5) deducendo `remaining_balance · interest_rate` dalla cassa del debitore e accreditandolo al prestatore quando `lender_type = "agent"` (per un prestito del sistema bancario l'interesse è dedotto dal debitore ma NON ri-accreditato ad alcuna controparte, quindi contrae la M misurata ad ogni tick per scelta di modello -- cfr. §4.8 e la disclosure R5-DISC-1 in `monetary.py`); i debitori che non possono pagare gli interessi sono restituiti in una lista che l'orchestratore marca `defaulted` immediatamente, così che il default da interessi mancati sia gestito da `process_defaults` nello STESSO tick (fix R5-CRED-3; pre-fix la lista restituita era scartata e l'interesse mancato non aveva conseguenze fino alla maturità). Terzo, `process_maturity(simulation, tick)` (`credit.py:467-669`) gestisce i prestiti il cui `due_at_tick` è pari o precedente al tick corrente -- una passata di catch-up (R8-NEW-5) così che un prestito giunto a scadenza in un tick in cui il blocco del credito è stato saltato (un tick interamente privo di agenti vivi) sia regolato al tick eseguito successivo invece che rimanere abbandonato -- con tre esiti per prestito: rimborso completo quando il debitore ha abbastanza cassa per coprire `remaining_balance · (1 + interest_rate)` -- il periodo finale matura anche sul rimborso, con il principale a ledger come `loan_repayment` e l'interesse come `loan_interest` (fix R7-NEW-1), un rollover in stile Minsky strettamente quando il debitore può pagare la porzione di interessi ma non il principale e il contatore `times_rolled_over` è sotto `max_rollover` (un interesse non sostenibile ora ricade nel default -- fix R6-ROLL-1) (un nuovo prestito è creato a `interest_rate · 1.10` riflettendo l'aggiustamento di rischio del prestatore, con `times_rolled_over += 1`), e default quando nessuna delle due condizioni è soddisfatta. Quarto, `process_defaults(simulation, tick)` (`credit.py:672-803`) sequestra il collaterale trasferendo `Property.owner` al prestatore (o al governo per i prestiti del sistema bancario), azzera il `remaining_balance` del prestito, muove il prestito allo stato terminale `default_settled` (così che il sequestro del collaterale, il write-off bancario e il danno reputazionale scattino esattamente una volta per default invece di essere ri-applicati a ogni tick successivo), e crea una memoria di reputazione negativa per il debitore con `action_sentiment = -0.7` (osservatori della zona) e `-0.9` (il prestatore direttamente) via il sistema di reputazione di §4.3. Inoltre, viene creata una memoria auto-consapevole per il debitore con `emotional_weight = 0.8` (`credit.py:806-862`) cosicché la pipeline di decisione del debitore stesso conservi la consapevolezza del default nei tick successivi. Quinto, `process_default_cascade(simulation, tick, max_depth=3, loss_records=...)` (`credit.py:930-1085`) esegue una passata di contagio breadth-first sul grafo del debito, seminata dai loss record restituiti da `process_defaults` per il tick CORRENTE (le perdite nette dopo che il collaterale è stato scomputato, non una ri-query sulla storia dei default di tutti i tempi): per ogni prestatore la cui perdita aggregata dai default di questo tick supera `CASCADE_LOSS_THRESHOLD = 0.5` della sua ricchezza, i prestiti attivi del prestatore stesso sono marcati defaulted (flaggati `cascade_origin`, così che i loro record di settlement non ri-seminino una cascata successiva: un evento di perdita è valutato contro la soglia esattamente una volta -- fix R6-CASC-1), i livelli interni accumulano la stessa misura di perdita al netto del collaterale del livello seed (fix R6-NEW-2), e il contagio si propaga ai loro prestatori a turno finché o non si verifica nessun ulteriore breach di soglia o si raggiunge `max_depth = 3` (il cap previene la propagazione infinita ed è calibrato contro il diametro tipico di 3-5 link delle reti empiriche riportato da Allen e Gale 2000). Sesto, `adjust_interest_rate(simulation, tick)` (`banking.py:115-206`) applica l'aggiustamento Wickselliano `r_{t+1} = r_t · (1 + adj_rate · (demand − supply) / max(supply, 0.001))` al tasso di base e clampa il risultato a `[0.005, 0.50]`. Settimo, `check_solvency(simulation)` (`banking.py:209-266`) valuta `reserves = total_deposits − total_loans_outstanding` contro `required = total_deposits · reserve_ratio` e aggiorna `confidence_index` di `−0.1` per tick di insolvenza o `+0.05` per tick di recupero (l'asimmetria codifica l'osservazione di asimmetria della fiducia che la fiducia è più facile da perdere che da ricostruire). Ottavo e ultimo, `broadcast_banking_concern(simulation, tick)` (`banking.py:337-424`) valuta la (4.11) e crea le memorie di preoccupazione. La sequenza a otto step è deterministica dato il seed casuale della simulazione (lo step di trasmissione campiona da un RNG derivato dal seed della simulazione e dal tick, indipendente dallo stream globale del modulo `random`), e l'intero step di credito scrive un numero limitato di righe del database per tick — limitato dal conteggio degli agenti vivi per la trasmissione e dal conteggio dei prestiti attivi per il servicing e la maturità — quindi il costo per-tick è `O(n_agents + n_active_loans)`.

**Semplificazioni.** L'implementazione attuale omette deliberatamente quattro raffinamenti che la letteratura su credito-e-banca tratta come estensioni proprie piuttosto che correzioni del meccanismo baseline. Primo, il settore bancario è una singola banca aggregata per simulazione piuttosto che una popolazione di banche concorrenti: la riga `BankingState` è uno-a-uno con `Simulation`, e non c'è mercato di prestito interbancario, nessun grafo di esposizione interbancaria, e nessun prestatore di ultima istanza della banca centrale. Il meccanismo di contagio di Allen-Gale (2000) è quindi implementato solo sul grafo del debito agente-a-agente (`process_default_cascade`), non su un grafo di rete bancaria; un raffinamento multi-banca è registrato nella spec come estensione rinviata e richiederebbe l'introduzione di un modello `Bank` con bilanci per-banca e un grafo di passività interbancarie. Secondo, l'assicurazione sui depositi è astratta: il flag `BankingState.is_solvent` impedisce l'emissione di nuovi prestiti mentre insolvente (via la precondizione in (4.12)), ma non c'è un fondo di assicurazione sui depositi esplicito contro cui i depositanti possano rivalersi, e i depositanti non possono "ritirare" la loro cassa dalla banca nel senso letterale perché il campo cassa di AgentInventory rappresenta già la cassa a portata piuttosto che un saldo depositato — il modello tratta tutta la cassa dell'agente come implicitamente depositata (`recalculate_deposits()` a `banking.py:293-320`). Un raffinamento futuro spaccherebbe `AgentInventory.cash` in una frazione depositata e una frazione accumulata, permettendo alla dinamica di corsa agli sportelli di essere espressa come pressione di ritiro piuttosto che come voce mediata dalla fiducia. Terzo, la negoziazione del prestito è single-round prendi-o-lascia: il debitore presenta un'azione `request_loan` con un importo target e un collaterale candidato, `evaluate_credit_request()` o approva al tasso di Stiglitz-Weiss o respinge con una ragione dichiarata, e non c'è un secondo round in cui il debitore potrebbe contro-proporre un importo più piccolo, un collaterale diverso, o una durata più lunga per portare la richiesta dentro l'inviluppo LTV. La negoziazione multi-round è registrata come raffinamento rinviato sotto il log di risoluzione audit del documento di design del 2026-04-15, sulla base che interagirebbe con il budget di contesto LLM e la pipeline di decisione per-tick in modi che hanno bisogno di una passata di calibrazione separata. Quarto, l'incremento del tasso di interesse del rollover è fissato a `1.10` per rollover (`credit.py:636`) piuttosto che essere una funzione della leva del debitore al momento del rollover o del segnale di stress macroeconomico portato dall'indice di fiducia bancaria; una regola di repricing del rollover più sofisticata che risponda al rischio sistemico è l'estensione naturale una volta che la suite di validazione del Capitolo 7 esercita la classificazione di stadio di Minsky (`classify_minsky_stage` a `credit.py:118-169`) contro la tassonomia canonica hedge-speculative-Ponzi di Minsky (1986).

### 4.2.3 Mercato immobiliare

> Stato: implementato a partire dal commit `8a2bc714477f445b46cd610725df40c93fce1557`, audit della spec CONVERGENTE 2026-04-15.

**Background.** Il mercato immobiliare entra nella pipeline di tick di Epocha perché lo spazio di decisione dell'agente documentato in §3.2 porta un'azione `buy_property` e un'azione `sell_property` la cui semantica non può essere ridotta al clearing di mercato di beni a tick singolo del tipo posseduto dal substrato di §3.6: una proprietà cambia mano una volta e resta con l'acquirente per il resto della simulazione, il prezzo richiesto diverge sistematicamente dal rendimento da affitto fondamentale perché i venditori si ancorano ad aspettative modulate dalla personalità, e l'intento dell'acquirente dichiarato al tick `T` non può essere regolato all'interno dello stesso tick perché la pipeline di decisione guidata dall'LLM ha già prodotto i suoi output al momento in cui l'orchestratore dell'economia viene invocato. L'implementazione trascrive un meccanismo zone-locale di annunci-e-abbinamento che preserva le tre proprietà sostantive: le proprietà sono annunciate dai loro proprietari con un prezzo richiesto, gli annunci vivono nella zona corrente dell'acquirente, e l'abbinamento si regola al tick `T+1` contro gli intenti `buy_property` dichiarati al tick `T`. Il benchmark di valore fondamentale contro cui venditori e acquirenti confrontano il prezzo richiesto è la valutazione del modello di crescita di Gordon (1959) `V = R / (r − g)`, che dà il valore intrinseco di un asset il cui flusso di cassa è una perpetuità che cresce al tasso `g` scontata al tasso `r`; l'implementazione Epocha calcola questo benchmark per proprietà e lo memorizza nel campo `fundamental_value` dell'annuncio insieme all'`asking_price` del venditore, così che la divergenza tra prezzo e valore sia osservabile alle analytics downstream e sia l'analogo Epocha naturale della divergenza prezzo-fondamentali che Shiller (2000) identifica come la firma empirica delle bolle speculative. Due semplificazioni concrete sono registrate inline: non c'è negoziazione multi-round tra acquirente e venditore (il prezzo richiesto è prendi-o-lascia) e non c'è abbinamento inter-zona (un acquirente nella zona A non può abbinare un annuncio nella zona B, anche a un prezzo più basso, perché l'assunzione di zone-località è la struttura spaziale che il mercato immobiliare eredita dal movimento di §3.4). Il mercato immobiliare porta anche un canale laterale di cambio di regime implementato in `process_expropriation()` che ridistribuisce le proprietà sulle transizioni di governo seguendo Acemoglu e Robinson (2006); il canale laterale è documentato nel modulo del mercato immobiliare perché opera sulle stesse righe `Property` ma è invocato dal sottosistema politico piuttosto che dall'orchestratore dell'economia per-tick, quindi questa sottosezione lo tratta solo come la sorgente dell'effetto laterale di conversione del collaterale sui prestiti in essere.

**Modello.** La condizione di abbinamento che trasferisce una proprietà da un venditore `s` a un acquirente `b` al tick `T` legge contro la tabella `PropertyListing` e la zona corrente dell'acquirente:

```
match(b, ℓ) at tick T  ⇔  ℓ.status = "listed"
                       ∧  ℓ.property.zone = b.zone        (zone at matching time)
                       ∧  ℓ.property.owner ≠ b            (no self-purchase)
                       ∧  buyer_cash(b) ≥ ℓ.asking_price
                       ∧  buy_property ∈ DecisionLog(b, T−1)            (4.14)
```

L'equazione (4.14) è implementata in `process_property_listings()` a `epocha/apps/economy/property_market.py:202-379`, con i quattro congiunti valutati nell'ordine elencato così che l'annuncio qualificante più economico sia selezionato via `order_by("asking_price").first()`. Il congiunto zone-at-matching-time è il cambiamento sostantivo introdotto dal fix audit M-4 della convergenza del 2026-04-15: l'implementazione pre-audit leggeva la zona dell'acquirente dal contesto di decisione al tick `T−1`, che produceva abbinamenti spuri quando l'acquirente si muoveva tra i tick `T−1` e `T`, e la forma auditata legge `buyer.zone_id` direttamente alla chiamata di abbinamento così che un acquirente che ha attraversato un confine di zona perda la capacità di abbinare un annuncio nella zona precedente. L'esclusione del self-purchase è il cambiamento sostantivo introdotto dal fix audit M-5 della stessa convergenza: l'implementazione pre-audit consentiva all'intento `buy_property` di un venditore di abbinare il proprio annuncio (una transazione no-op che tuttavia consumava un tick del budget di intenti dell'acquirente e gonfiava il conteggio degli abbinati), e la forma auditata esclude le proprietà dell'acquirente dal candidate set via `.exclude(property__owner=buyer)`. La precondizione di prestito che regola il controllo della cassa non fa parte della condizione di abbinamento stessa: un acquirente con cassa insufficiente semplicemente fallisce l'abbinamento, e la spec registra questo come fix audit A-5 — il design pre-audit emetteva automaticamente un prestito per coprire il deficit, il che contraddiceva il principio architettonico che tutto il prestito è un'azione esplicita guidata dall'LLM documentata in §3.2, e la forma auditata rimuove il percorso auto-prestito così che un acquirente che ha bisogno di credito debba dichiarare un'azione `borrow` in un tick precedente e poi ridichiarare `buy_property` una volta che la cassa è in mano.

La condizione di conversione del collaterale che trasferisce una proprietà da un debitore in default al prestatore al momento del default del prestito legge contro la foreign key `Loan.collateral` stabilita all'emissione:

```
on default of loan L at tick T:
    if L.collateral ≠ ∅ :
        L.collateral.owner ← L.lender         (or government if lender = banking)
        L.lender_loss     ← max(0, L.remaining_balance − L.collateral.value)        (4.15)
```

L'equazione (4.15) è implementata in `process_defaults()` a `epocha/apps/economy/credit.py:672-803`, con la perdita residua calcolata dopo che il valore del collaterale è netto e propagata alla passata di contagio breadth-first di Allen-Gale (2000) descritta sotto l'Algoritmo di §4.2.2 quando supera `CASCADE_LOSS_THRESHOLD = 0.5` della ricchezza del prestatore. La conversione del collaterale è il ponte tra il sottosistema di credito di §4.2.2 e il mercato immobiliare di questa sottosezione: una proprietà pegnata come collaterale via la chiamata `find_best_unpledged_property()` di (4.12) è bloccata da nuovi pegni di collaterale dal fix audit M-6, e la sua conversione in default produce un cambio immediato di proprietà che i tick successivi del mercato immobiliare osservano attraverso il campo standard `property.owner`. La conversione non genera un `PropertyListing` per il prestatore — il prestatore prende la proprietà direttamente in possesso e può o meno annunciarla in vendita in un tick futuro a seconda delle proprie decisioni guidate dall'LLM — e di conseguenza non appare nel conteggio degli abbinati per-tick di `process_property_listings()`.

**Parametri.** Il mercato immobiliare non porta un proprio blocco di configurazione era-specifico; i parametri che governano il comportamento di abbinamento sono ereditati dalla configurazione del credito di §4.2.2 (loan-to-value per il percorso di prestito, tasso di interesse di base come tasso di sconto `r` nella valutazione di Gordon) e dalla configurazione delle aspettative di §4.2.1 (la `trend_threshold = 0.05` del fix audit C-5 che classifica l'ancoraggio del venditore come rising, falling, o stable). I due parametri di design del mercato immobiliare codificati fuori dai template di era sono la finestra di scadenza degli annunci e la guard band di valutazione di Gordon: gli annunci stantii sono ritirati dopo `10` tick (`property_market.py:235`), riflettendo l'assunzione che i mercati immobiliari nelle economie dal pre-industriale al moderno operano su scale temporali multi-periodo e che un annuncio invenduto oltre quell'orizzonte è più probabilmente un prezzo stantio che un'offerta vitale; il denominatore della valutazione di Gordon è floored a `0.01` per impedire la divisione per zero quando `r ≈ g`, e la valutazione risultante è clampata a `[0.1 · property.value, 10 · property.value]` per evitare che il fondamentale degeneri a zero su collassi transitori dell'affitto o esploda all'infinito su impennate transitorie dell'affitto (`property_market.py:121-128`). Il cap di valutazione di `10×` valore di libro è riconosciuto nel log di risoluzione audit della spec come il vincolo binding sulla magnitudine delle bolle speculative che la simulazione può esprimere: le bolle reali possono superare questo multiplo, e il cap è documentato come parametro di design tunabile piuttosto che bound strutturale. I quattro template di era ereditano i valori base per-proprietà da `_PROPERTIES_BASE` in `template_loader.py:66-85` (terreno agricolo 200, officina 150, negozio 100 in unità di valuta primaria), con il template industriale che aggiunge una fabbrica al valore base 500, il template moderno che aggiunge una fabbrica a 500 e un ufficio a 300, e il template sci-fi che aggiunge una fabbrica automatizzata a 1 000 e un laboratorio di ricerca a 800; la differenziazione per-era è qualitativa (quali tipi di proprietà sono disponibili piuttosto che quali sono i loro parametri) e l'omogeneità dei valori base tra le ere è un deliverable di calibrazione del Plan 4 piuttosto che una scelta di design sostantiva.

**Algoritmo.** Ad ogni tick, l'orchestratore dell'economia invoca `process_property_listings(simulation, tick)` esattamente una volta, regolato dallo stesso flag `credit_processed` che protegge lo step del credito a `epocha/apps/economy/engine.py:445-503`, e con la nota di ordinamento esplicita che il mercato immobiliare gira *prima* dello step del credito così che la cassa dalla vendita di proprietà accreditata ai venditori possa prevenire i default di prestiti che altrimenti si attiverebbero allo step del credito all'interno dello stesso tick. La funzione esegue cinque passate ordinate. Primo, una bulk update con singola query marca tutti gli annunci più vecchi di `tick − 10` come `withdrawn`, sostituendo l'iterazione per-annuncio con una chiamata `.update()` che è `O(1)` nel numero di annunci stantii. Secondo, la funzione legge le righe `DecisionLog` del tick precedente il cui JSON `output_decision` contiene la sottostringa `"buy_property"` e parsa ogni riga con `json.loads()` per recuperare il campo `action`; le righe con JSON malformato sono saltate silenziosamente, sulla base che l'LLM occasionalmente produce JSON non valido e un fallimento duro al parse propagherebbe un fallimento dell'LLM in un fallimento della pipeline di tick. Terzo, per ogni acquirente parsato la funzione controlla i quattro congiunti di (4.14) in ordine e seleziona l'annuncio qualificante più economico via `order_by("asking_price", "id").first()` (il tiebreak sull'id fissa deterministicamente gli annunci a pari prezzo, e gli acquirenti sono processati in ordine di id agente, entrambi per la riproducibilità seeded); il congiunto di zone-località è imposto dal filtro `property__zone_id=buyer.zone_id`, l'esclusione del self-purchase da `.exclude(property__owner=buyer)`, e il controllo della cassa leggendo `AgentInventory.cash[currency_code]` contro il prezzo richiesto dell'annuncio. Quarto, quando tutti i congiunti valgono, la funzione esegue il settlement a quattro step in un ordine deterministico: la cassa è dedotta dall'`AgentInventory.cash` dell'acquirente, accreditata all'`AgentInventory.cash` del venditore (creando una riga di inventario per il venditore se mancante), -- oppure, quando la proprietà in vendita non ha un proprietario agente (terra governativa o pubblica), il prezzo di vendita è accreditato alla tesoreria del governo via `add_to_treasury`, e la vendita è saltata prima di qualsiasi addebito se non esiste un Government, così che l'addebito dell'acquirente abbia sempre un accredito corrispondente -- i campi `owner` e `owner_type` della proprietà sono riassegnati all'acquirente, e lo `status` dell'annuncio è impostato a `"sold"`; le quattro scritture sono chiamate `save(update_fields=[...])` indipendenti piuttosto che una singola transazione perché il tick di simulazione circostante è avvolto in una transazione a livello del motore di simulazione (`epocha/apps/simulation/engine.py`), non dell'orchestratore dell'economia. Quinto, una riga `EconomicLedger` è creata con `transaction_type="property_sale"` (aggiunto a `TRANSACTION_TYPES` dalla stessa convergenza del 2026-04-15) che registra il flusso di cassa da acquirente a venditore. La funzione restituisce un dizionario `{"matched": M, "expired": E, "failed": F}` che l'orchestratore logga a livello `INFO` per osservabilità per-tick. La passata è `O(n_buyers · log n_listings)` per tick perché il piano di query per-acquirente usa l'ordinamento `(zone, status, asking_price)` piuttosto che un full table scan, e l'intero costo per-tick è limitato superiormente dal conteggio degli agenti vivi per l'enumerazione degli acquirenti e dal conteggio degli annunci attivi per l'abbinamento per-acquirente.

**Semplificazioni.** L'implementazione attuale omette deliberatamente quattro raffinamenti che la letteratura del mercato immobiliare tratta come estensioni proprie piuttosto che correzioni del meccanismo baseline. Primo, gli annunci sono abbinati una volta per tick in un singolo round: un acquirente che ha la cassa per un annuncio ma perde contro un altro acquirente ordinato prima nell'iterazione non riceve una seconda possibilità all'interno dello stesso tick, e un acquirente il cui unico annuncio vitale nella zona corrente è appena sopra il suo budget non può controfferire a un prezzo più basso. La negoziazione multi-round con convergenza bid-ask è registrata nella spec come raffinamento rinviato, sulla base che interagirebbe con il budget di contesto LLM di §3.5 in modi che hanno bisogno di una passata di calibrazione separata. Secondo, gli annunci non persistono il loro ordinamento originale attraverso la finestra di scadenza degli annunci: un annuncio postato al tick `T` compete con un annuncio postato al tick `T+5` puramente sul prezzo, quindi un annuncio postato presto non riceve priorità per essere stato sul mercato più a lungo; un raffinamento di priorità temporale (FIFO sugli annunci allo stesso prezzo) è registrato come estensione rinviata. Terzo, l'intento dell'acquirente è binario piuttosto che parametrizzato: un'azione `buy_property` non porta un tipo target o un prezzo massimo, e la passata di abbinamento seleziona l'annuncio più economico nella zona dell'acquirente indipendentemente dalla compatibilità tra il `production_bonus` della proprietà e il ruolo dell'acquirente; un intento tipizzato per target che filtri gli annunci per tipo di proprietà o per allineamento al production-bonus è l'estensione naturale una volta che la grammatica delle azioni LLM di §3.2 è ampliata per supportare parametri tipizzati. Quarto, la regola di formazione del prezzo richiesto che produce la divergenza tra `asking_price` e `fundamental_value` è documentata nell'azione `sell_property` allo strato di decisione LLM di §3.2 piuttosto che allo strato del mercato immobiliare, e di conseguenza questa sottosezione tratta il prezzo richiesto come input esogeno alla condizione di abbinamento (4.14); la logica di ancoraggio speculativo e modulazione di personalità che produce la divergenza è oggetto della pipeline di decisione lato venditore ed è documentata in §3.2.

## 4.3 Reputazione

> Stato: implementato a partire dal commit `c196281d706f63d6a9270c9b26e5c9044067d785`, audit del codice CONVERGENTE 2026-05-12 round 2.

### Background

La reputazione in Epocha implementa la distinzione tra immagine e
reputazione introdotta da Castelfranchi, Conte e Paolucci (1998).
L'immagine è la valutazione di prima mano che il portatore ha del
target, aggiornata dall'osservazione diretta. La reputazione è la
valutazione propagata socialmente che il portatore ha del target,
aggiornata da hearsay proveniente dalla propagazione del flusso
informativo (capitolo 4.4) e pesata dall'affidabilità della sorgente.
L'asimmetria tra le magnitudini di aggiornamento dell'immagine
negative e positive è qualitativamente ispirata al principio del
negativity bias (Baumeister et al. 2001) senza pretendere alcun
rapporto quantitativo specifico da quella meta-review. La scala
numerica `[-1, 1]` è una decisione implementativa tipica dei sistemi
computazionali di reputazione (es. ReGreT — Sabater e Sierra 2002) e
non prescritta da Castelfranchi et al. (1998).

### Modello

Due campi scalari sono mantenuti per ogni coppia (portatore, target):
- Immagine: limitata a [-1, 1], aggiornata solo dall'osservazione diretta
- Reputazione: limitata a [-1, 1], aggiornata solo da hearsay con dampening della reliability

Un punteggio combinato di trustworthiness è esposto ai consumatori a valle
(es. la pipeline decisionale dell'agente in `agents/decision.py`) attraverso
una singola fonte di verità in `agents/reputation.py`.

### Equazioni

Equazione (4.16) — Aggiornamento dell'immagine sull'azione osservata di tipo a:

  image_{t+1} = clip(image_t + Δ_image[a], -1, 1)

dove Δ_image[a] è un delta per-azione regolabile (positivo per azioni
prosociali, negativo per azioni antisociali; magnitudini per azioni negative
deliberatamente più grandi che per azioni positive per codificare il
negativity bias).

Equazione (4.17) — Aggiornamento della reputazione su hearsay con sentimento s e affidabilità r:

  reputation_{t+1} = clip(reputation_t + s · r · ζ, -1, 1)

dove ζ = 0.5 è un fattore di dampening che impedisce a un singolo evento
di hearsay con sentimento massimo proveniente da una sorgente perfettamente
affidabile di muovere la reputazione di più di 0.5 (regolabile, nessuna
fonte empirica).

Equazione (4.18) — Punteggio combinato di trustworthiness:

  combined = w_I · image + w_R · reputation

dove w_I = 0.6 e w_R = 0.4 sono pesi regolabili che esprimono la primazia
qualitativa dell'esperienza diretta sull'hearsay (Castelfranchi et al.
1998 per la distinzione concettuale; il rapporto specifico 0.6/0.4 è una
scelta di design).

### Parametri

| Parametro | Simbolo | Valore | Sorgente/Stato |
|---|---|---|---|
| Delta immagine su `help` | Δ_image[help] | +0.15 | design regolabile |
| Delta immagine su `socialize` | Δ_image[socialize] | +0.10 | design regolabile |
| Delta immagine su `betray` | Δ_image[betray] | -0.80 | design regolabile |
| Delta immagine su `crime` | Δ_image[crime] | -0.60 | design regolabile |
| Delta immagine su `argue` | Δ_image[argue] | -0.20 | design regolabile |
| (altri tipi di azione) | vari | vari | design regolabile (tabella completa in `agents/reputation.py:43-89` _IMAGE_DELTAS) |
| Dampening della reputazione | ζ | 0.5 | design regolabile (`agents/reputation.py:_DAMPENING_FACTOR`-equivalente inline) |
| Peso immagine combinato | w_I | 0.6 | design regolabile (`agents/reputation.py:_WEIGHT_IMAGE`) |
| Peso reputazione combinato | w_R | 0.4 | design regolabile (`agents/reputation.py:_WEIGHT_REPUTATION`) |
| Sentimento osservatori su default prestito | — | -0.7 | design regolabile (`agents/reputation.py:_LOAN_DEFAULT_OBSERVER_SENTIMENT`); ispirato dalla letteratura di sociologia economica sulle sanzioni reputazionali (Diamond 1989; Greif 1993; Karlan 2005) |
| Sentimento prestatore su default prestito | — | -0.9 | design regolabile (`agents/reputation.py:_LOAN_DEFAULT_LENDER_SENTIMENT`) |

### Algoritmo

Quando un agente osserva un target eseguire un'azione, viene chiamata `update_image(holder, target, action_type, tick)` (`agents/reputation.py:update_image`). La funzione utilizza `transaction.atomic()` con `select_for_update()` sulla riga ReputationScore per prevenire race condition di lost-update durante l'esecuzione concorrente di worker Celery. Se `action_type` è sconosciuto alla tabella `_IMAGE_DELTAS`, viene emesso un log a livello WARNING e l'immagine resta invariata.

Quando un agente riceve hearsay riguardo a un target, viene chiamata `update_reputation(holder, target, action_sentiment, reliability, tick)` (`agents/reputation.py:update_reputation`) con la stessa protezione di concorrenza. Il sentimento dell'hearsay è o estratto dal contenuto a testo libero via `extract_action_sentiment` (euristica rule-based placeholder) o fornito direttamente dal modulo di dominio chiamante (es. `economy/credit.py` chiama con `_LOAN_DEFAULT_OBSERVER_SENTIMENT` e `_LOAN_DEFAULT_LENDER_SENTIMENT` per gli eventi di default prestito).

L'estrattore a parole-chiave `extract_action_sentiment` usa un'euristica loudest-keyword-wins con tabelle placeholder di parole-chiave positive e negative; è documentata come semplificazione nota in attesa di sostituzione da parte di un classificatore di sentiment basato su embedding o LLM.

### Semplificazioni

1. **Nessun decadimento temporale**: immagine e reputazione si accumulano indefinitamente. Le vecchie osservazioni dal tick 1 portano lo stesso peso delle osservazioni dal tick 1000. Castelfranchi et al. (1998) discute la manutenzione continua attraverso la comunicazione sociale, che non è implementata; un meccanismo di pesatura per recency è rinviato a un'iterazione futura.

2. **Clamp immediato vs. aggregazione cumulativa**: immagine e reputazione sono clampate a [-1, 1] dopo ogni aggiornamento. Questo causa saturazione: approssimativamente 1/Δ osservazioni dello stesso tipo di azione saturano completamente il campo, dopo le quali le osservazioni successive non hanno effetto. Schemi di aggregazione alternativi (media mobile, posteriore beta — Beta Reputation System, Jøsang e Ismail 2002 — aggiornamento bayesiano) eviterebbero l'effetto di saturazione al costo di stato aggiuntivo per osservazione. Questo trade-off è accettato per l'implementazione corrente.

3. **Limitazioni dell'estrazione del sentiment**: l'euristica `extract_action_sentiment` restituisce la parola-chiave con il valore assoluto più alto (loudest-keyword-wins). Non gestisce la negazione ("did not help" continua a produrre uno score positivo per "help"), non aggrega tra match di parole-chiave (una frase contenente sia parole-chiave prosociali sia antisociali restituisce solo la più forte), e non esegue analisi di sentiment a livello di frase. Queste limitazioni biasano la reputazione derivata da hearsay verso il polo di sentiment lessicalmente più intenso nelle tabelle di parole-chiave.

4. **Nessuna reputazione contestuale**: viene mantenuto un singolo punteggio globale di reputazione per coppia (portatore, target). I ruoli (es. trader vs amico) non sono differenziati.

5. **Copertura del vocabolario di azioni**: `_IMAGE_DELTAS` copre 17 tipi di azione emessi dal motore di simulazione. I tipi di azione non in tabella producono zero variazione di immagine con un log WARNING; questo è imposto dal log di tipo di azione sconosciuto per impedire drift silenzioso tra il motore e la tabella di reputazione.



## 4.4 Propagazione del passaparola

> Stato: implementato a partire dal commit `a0ea07556ce8b32cea89ad543660fcb81be06b6e`, audit del codice CONVERGENTE 2026-05-16 round 2.

Il cluster di propagazione del passaparola trascrive Bartlett (1932) sulla riproduzione seriale e Allport e Postman (1947) sull'assimilazione (parziale — solo il meccanismo di assimilazione è implementato; leveling e sharpening sono documentati come Limitazioni note) in una pipeline a quattro stadi. Il primo stadio, `agents/information_flow.py`, propaga le memorie lungo i grafi di relazioni degli agenti fino a tre hop per tick. Il secondo stadio, `agents/distortion.py`, applica trasformazioni testuali modulate dalla personalità guidate dal vettore Big Five di chi ridice il messaggio prima che esso raggiunga il prossimo destinatario. Il terzo stadio, `agents/belief.py`, filtra l'accettazione attraverso uno score pesato che combina affidabilità dell'informazione, fiducia relazionale, personalità del ricevente e reputazione del trasmettitore. Il quarto stadio, `agents/affinity.py`, contribuisce lo score di similarità di personalità Big Five che il filtro di credenza consuma attraverso la componente di fiducia relazionale e che le fazioni a valle consumano durante la formazione di coalizioni.

Granovetter (1973) sul ruolo strutturale dei legami deboli è citato in `information_flow.py` come framing concettuale per il bridging tra cluster ma NON è implementato a livello di propagazione: le memorie propagano in modo uguale indipendentemente dalla forza del legame, senza alcuna pesatura weak-tie sulla probabilità di propagazione. La pesatura weak-tie è documentata come Limitazione nota e tracciata per un'iterazione futura; il riferimento citato è preservato come citation-without-implementation per la chiusura IF-1 dell'audit Round 2.

### 4.4.1 Flusso di informazioni

> Stato: implementato a partire dal commit `a0ea07556ce8b32cea89ad543660fcb81be06b6e`, audit del codice CONVERGENTE 2026-05-16 round 2.

#### Background

Il flusso di informazioni operazionalizza Bartlett (1932) sulla riproduzione seriale: una memoria passata agente-per-agente perde fedeltà a ogni hop. Bartlett documenta il degrado qualitativamente piuttosto che come una legge geometrica specifica; il decadimento geometrico di affidabilità adottato dall'implementazione è un parametro di design regolabile inscritto nel template per epoca e non è rivendicato come risultato diretto di Bartlett. Granovetter (1973) sulla forza dei legami deboli è citato come frame concettuale per il ruolo di bridging tra cluster delle relazioni a bassa intensità ma NON è implementato a livello di propagazione (vedere l'intro del capitolo).

#### Modello

Ad ogni tick, il propagatore esegue quattro fasi sullo store delle memorie della simulazione. La Fase 1 seleziona le memorie dirette create al tick corrente il cui `emotional_weight` supera la soglia di propagazione e le trasmette ai vicini sociali dell'agente come hearsay (hop 1). La Fase 2 prende l'hearsay creato al tick precedente e lo inoltra come rumour (hop 2). La Fase 3 prende i rumour creati al tick precedente e li inoltra come ulteriori rumour finché l'hop count stimato è sotto il cap. La Fase 4 trasmette gli eventi pubblici del tick a tutti gli agenti vivi indipendentemente dalla distanza sociale. Il filtraggio di credenza in ciascun ricevente decide se la memoria in arrivo diventi una memoria completa al peso emotivo del ricevente o un rumour debole a peso smorzato che propaga comunque a valle senza influenzare le decisioni.

#### Equazioni

Equazione (4.19) — Decadimento dell'affidabilità tra hop di propagazione:

  reliability_{h+1} = reliability_h · δ

con δ = `EPOCHA_INFO_FLOW_RELIABILITY_DECAY` = 0.7 per default. La forma di composizione produce 0.7^3 ≈ 0.34 dopo tre hop e 0.7^5 ≈ 0.17 dopo cinque hop.

Equazione (4.20) — Stima dell'hop invertendo la relazione di decadimento:

  hop = round( log(reliability) / log(δ) )

Lo stimatore assume affidabilità iniziale = 1.0; le memorie che originano con reliability < 1.0 sono sovrastimate nel conteggio di hop (Limitazione nota IF-4).

Equazione (4.21) — Parametri downstream di rumour debole quando il filtro di credenza rigetta:

  emotional_weight_weak = w_weak
  reliability_weak     = reliability_h · δ · d_weak

con w_weak = `EPOCHA_INFO_FLOW_WEAK_RUMOR_WEIGHT` = 0.1 e d_weak = `EPOCHA_INFO_FLOW_WEAK_RUMOR_DAMP` = 0.3.

#### Parametri

| Parametro | Simbolo | Valore | Sorgente/Stato |
|---|---|---|---|
| Soglia di propagazione | — | 0.3 | design regolabile (`EPOCHA_INFO_FLOW_PROPAGATION_THRESHOLD`); impedisce a osservazioni triviali di inondare la rete |
| Decadimento di affidabilità per hop | δ | 0.7 | design regolabile (`EPOCHA_INFO_FLOW_RELIABILITY_DECAY`); Bartlett (1932) documenta il degrado qualitativamente senza prescrivere un tasso |
| Numero massimo di hop di propagazione | — | 3 | design regolabile (`EPOCHA_INFO_FLOW_MAX_HOPS`) |
| Destinatari per step di propagazione | — | 20 | design regolabile (`EPOCHA_INFO_FLOW_MAX_RECIPIENTS`); limita il fan-out per memoria |
| Peso emotivo del rumour debole | w_weak | 0.1 | design regolabile (`EPOCHA_INFO_FLOW_WEAK_RUMOR_WEIGHT`) |
| Smorzamento di affidabilità del rumour debole | d_weak | 0.3 | design regolabile (`EPOCHA_INFO_FLOW_WEAK_RUMOR_DAMP`) |

#### Algoritmo

`propagate_information(simulation, tick)` in `agents/information_flow.py:39-181` esegue il passaggio a quattro fasi. La Fase 1 (`information_flow.py:71-90`) legge le memorie dirette di questo tick sopra la soglia e chiama `_propagate_memory()` con `target_source_type = HEARSAY`. La Fase 2 (`information_flow.py:103-121`) legge l'hearsay del tick precedente e chiama lo stesso helper con `target_source_type = RUMOR`; la soglia di propagazione NON è deliberatamente imposta a questa fase, modellando la proprietà del gossip secondo cui gli agenti a valle ritrasmettono quanto già udito indipendentemente dalla salienza personale (chiusura del finding N-9 dell'audit Round 2). La Fase 3 (`information_flow.py:124-145`) legge i rumour del tick precedente, stima l'hop corrente via equazione (4.20) e propaga ulteriormente solo quando sotto `max_hops`. La Fase 4 (`information_flow.py:148-170`) trasmette gli eventi pubblici con `Memory.objects.get_or_create()` chiavato su `(agent, source_type=PUBLIC, tick_created, origin_agent=None, content=content)` — il campo `content` è parte del lookup in modo che due eventi pubblici distinti che si attivano sullo stesso tick producano due memorie per agente piuttosto che coalescere (chiusura del finding IF-5 dell'audit Round 2). L'helper per-memoria `_propagate_memory()` (`information_flow.py:184-341`) estrae il sentiment dal contenuto sorgente non distorto (finding N-3 Round 2: distorcere prima permetterebbe ai trasmettitori ad alta nevroticità di gonfiare il sentiment negativo), distorce il contenuto per il destinatario via `distort_information()`, aggiorna sempre la reputazione del destinatario verso l'agente di origine, interroga `get_combined_score()` per il segnale di reputazione del trasmettitore e chiama `should_believe()` per decidere se creare una memoria completa o un rumour debole a valle.

#### Semplificazioni

1. **IF-1 — Pesatura weak-tie di Granovetter non implementata**: la probabilità di propagazione non dipende dalla forza del legame. Il riferimento citato è preservato come frame concettuale; l'implementazione operativa è rimandata a un'iterazione futura. Documentato come Limitazione nota.

2. **IF-4 — Sovrastima dell'hop quando l'affidabilità iniziale < 1.0**: l'equazione (4.20) inverte `reliability = δ^hop` sotto l'assunzione di affidabilità iniziale 1.0. Una memoria originata da un evento pubblico con severità < 1.0 inizia con reliability < 1.0 e viene quindi conteggiata come se avesse già attraversato hop fantasma, causando terminazione prematura della propagazione. La fix comportamentale richiederebbe un `hop_count` `PositiveSmallIntegerField` sul modello Memory con una migrazione di backfill; rimandato.

3. **IF-5 — Deduplicazione degli eventi pubblici chiavata sul content**: affrontato nel round 2 2026-05-16 — il lookup `get_or_create()` in `information_flow.py:160-170` include il campo `content` così che due eventi pubblici distinti che si attivano sullo stesso tick producano due memorie per agente. La forma pre-audit coalesceva eventi pubblici dello stesso tick in un singolo record.

4. **N-9 — Asimmetria di soglia in Fase 2**: la Fase 2 (hearsay → rumour) NON impone deliberatamente `emotional_weight >= EPOCHA_INFO_FLOW_PROPAGATION_THRESHOLD`. La soglia gate l'ingresso nella rete dei rumour all'hop 1; una volta che una memoria è stata ritenuta degna di trasmissione a monte, gli agenti a valle ritrasmettono indipendentemente dalla salienza personale. Questa è la proprietà del gossip ed è documentata inline in `information_flow.py:93-102`. Se l'asimmetria non è desiderata, imporre la soglia coerentemente tra le fasi.

### 4.4.2 Distorsione

> Stato: implementato a partire dal commit `a0ea07556ce8b32cea89ad543660fcb81be06b6e`, audit del codice CONVERGENTE 2026-05-16 round 2.

#### Background

La distorsione implementa il meccanismo di assimilazione di Allport e Postman (1947), *The Psychology of Rumor*: le forti attitudini preesistenti di chi ridice agiscono come un filtro che piega il rumour verso quelle attitudini. Allport e Postman descrivono tre meccanismi — leveling (perdita progressiva di dettaglio), sharpening (enfasi selettiva) e assimilation (rimodellamento verso lo schema di chi ridice). Solo l'assimilazione è implementata nel modulo corrente; leveling e sharpening sono documentati come Limitazioni note. La base di personalità è il modello a cinque fattori di Costa e McCrae (1992), con l'estremità del tratto Big Five che seleziona quale pattern di assimilazione si attivi.

#### Modello

Il distorsore ispeziona il vettore Big Five di chi ridice e seleziona fino a `_MAX_ACTIVE_TRAITS = 2` tratti il cui valore supera le soglie di estremità. Per ciascun tratto attivo, un insieme graduato di sostituzioni regex viene applicato a una di tre bande di intensità (mild, moderate, strong) determinata dalla distanza dalla soglia. Il primo match di ciascun pattern vince (source-order deliberato, chiusura N-4 dell'audit Round 2); i pattern successivi all'interno dello stesso tratto non si attivano, modellando l'osservazione che un singolo bias dominante tipicamente rimodella l'elemento più saliente di un messaggio piuttosto che ogni parola simultaneamente.

#### Equazioni

Equazione (4.22) — Mappatura della soglia di estremità del tratto:

  active(t) = 1 se value(t) ≥ θ_high OPPURE value(t) ≤ θ_low; altrimenti 0

con θ_high = `_HIGH_THRESHOLD` = 0.7 e θ_low = `_LOW_THRESHOLD` = 0.3. L'indice di intensità 0/1/2 (mild/moderate/strong) è computato partizionando la distanza dalla soglia in tre bande uguali; derivazione completa in `distortion.py:148-185`.

#### Parametri

| Parametro | Simbolo | Valore | Sorgente/Stato |
|---|---|---|---|
| Soglia di alta estremità | θ_high | 0.7 | design regolabile (`distortion.py:_HIGH_THRESHOLD`); Allport e Postman (1947) non prescrivono un cutoff numerico |
| Soglia di bassa estremità | θ_low | 0.3 | design regolabile (`distortion.py:_LOW_THRESHOLD`); controparte simmetrica di θ_high |
| Numero massimo di tratti attivi concorrenti | — | 2 | design regolabile (`distortion.py:_MAX_ACTIVE_TRAITS`); valori superiori producono testo che diverge troppo rapidamente attraverso gli hop |

#### Algoritmo

`distort_information(content, personality)` in `distortion.py:270-306` è una funzione pura: nessun I/O, nessun accesso al database. `_select_active_traits()` (`distortion.py:188-215`) ordina i tratti Big Five per `abs(value - 0.5)` e restituisce i primi due che superano le soglie di estremità. Per ciascun tratto attivo, `_TRAIT_PATTERNS[trait]` produce una tupla (high_patterns, low_patterns) e il lato appropriato è selezionato dalla direzione del tratto. `_apply_patterns()` (`distortion.py:218-257`) itera la lista di pattern in ordine di dichiarazione, applica il primo match alla banda di intensità selezionata via `pattern.sub(replacement, content, count=1)` e si ferma. I due tratti attivi sono applicati sequenzialmente così che la sostituzione del primo tratto possa consumare il token che il secondo tratto avrebbe matchato; questo è il comportamento corretto per un modello di reframe dominante. Le tabelle di pattern high-neuroticism, low-neuroticism, high-agreeableness, low-agreeableness, high-openness, low-openness, high-extraversion, low-extraversion, high-conscientiousness e low-conscientiousness sono inline in `distortion.py:63-145`.

#### Semplificazioni

1. **D-1 — Sharpening e leveling non implementati**: Allport e Postman (1947) descrivono tre meccanismi di riproduzione seriale (leveling, sharpening, assimilation); solo l'assimilazione è implementata. Il leveling sarebbe modellato come troncamento progressivo di frasi attraverso gli hop di propagazione; lo sharpening sarebbe modellato come enfasi o ripetizione di parole-chiave per termini contestualmente salienti. Rimandato; documentato come Limitazione nota.

2. **D-4 — Accumulazione del pattern high-openness multi-hop**: il pattern high-openness (`_HIGH_OPENNESS_PATTERNS` in `distortion.py:99-107`) inserisce una clausola speculativa (" -- perhaps for a reason. ") dopo ogni confine punto-spazio nell'input. Attraverso multiple hop di propagazione con re-narratori ad alta openness, input di tre frasi accumulano tre qualificatori speculativi, poi nove dopo un altro hop, poi ventisette. L'accumulazione è patologica. Lavoro futuro potrebbe restringere l'inserimento al primo o ultimo confine di frase, o limitare per conteggio di trasmettitori. Documentato come Limitazione nota; nessun cambio di codice nell'iterazione corrente.

3. **D-5 — L'anonimizzazione di nomi propri low-conscientiousness è troppo ampia**: il pattern low-conscientiousness (`_LOW_CONSCIENTIOUSNESS_PATTERNS` in `distortion.py:137-145`) rimpiazza tutte le parole capitalizzate a metà frase con "somebody" / "someone" / "this person". Questo distrugge nomi propri non-personali (nomi di città, nomi di luoghi, titoli), non solo nomi di persona. Un pre-pass NER o un pattern ristretto per posizione (es. solo dopo verbi relazionali "with X", "to X") risolverebbe il problema. Documentato come Limitazione nota; nessun cambio di codice nell'iterazione corrente.

4. **N-4 — Source-order first-match-wins è deliberato**: le liste di pattern sono valutate in ordine di dichiarazione e il primo pattern che matcha vince. I pattern sono elencati in ordine di priorità linguistica intenzionale all'interno di ciascun blocco di personalità (es. il blocco high-neuroticism elenca `argued`, `disagreed`, `criticized`, `disappointed`, `went wrong` in modo che le sostituzioni di `argued` abbiano precedenza sulle sostituzioni di `disagreed` quando entrambe potrebbero matchare lo stesso input). Chiude il finding N-4 del Round 2 documentando l'assunzione di source-order come deliberata piuttosto che rifattorizzando a uno schema match-all-pick-strongest.

### 4.4.3 Filtro di credenza

> Stato: implementato a partire dal commit `a0ea07556ce8b32cea89ad543660fcb81be06b6e`, audit del codice CONVERGENTE 2026-05-16 round 2.

#### Background

Il filtro di credenza decide se il ricevente accetti un'informazione in arrivo come memoria completa o la declassi a rumour debole. La struttura è liberamente ispirata da Mayer, Davis e Schoorman (1995), *An Integrative Model of Organizational Trust*, che decompone la fiducia in ability, benevolence e integrity; l'implementazione non rivendica di operazionalizzare quei costrutti e adotta uno score pesato a quattro componenti i cui componenti sono operativi piuttosto che psicometrici. Il contributo di personalità è fondato su Graziano e Tobin (2002), che legano l'agreeableness al processing cooperativo di informazione; il contributo dell'openness al fattore personalità è una scelta di design Epocha senza supporto empirico specifico da quel paper. Il contributo della reputazione di rete è supportato da Castelfranchi, Falcone e Tan (2001), *The Role of Trust and Deception in Virtual Societies* (HICSS-34), che stabilisce il principio di usare la reputazione a livello di rete come segnale di credibilità nei sistemi multi-agente.

#### Modello

Lo score di accettazione è una combinazione convessa di quattro segnali: affidabilità dell'informazione (dopo il decadimento per hop), fiducia relazionale tra ricevente e trasmettitore, personalità del ricevente e reputazione del trasmettitore come percepita dalla rete più ampia. Il ricevente accetta la memoria quando lo score di accettazione supera la soglia configurata; altrimenti genera il rumour debole a valle dell'equazione (4.21).

#### Equazioni

Equazione (4.23) — Score di accettazione:

  acceptance = w_r · reliability + w_t · trust + w_p · personality + w_rep · reputation_norm

con pesi w_r = 0.3, w_t = 0.2, w_p = 0.2, w_rep = 0.3. I componenti sono definiti come segue. Trust = (relationship_strength + max(0, relationship_sentiment)) / 2. Personality = 0.6 · agreeableness + 0.4 · openness. reputation_norm normalizza lo score combinato immagine+reputazione da [-1, 1] a [0, 1] attraverso la singola fonte di verità in `reputation.py:_normalize_reputation()` (chiusura N-5 Round 2). L'accettazione è `acceptance ≥ τ_b` con τ_b = `EPOCHA_INFO_FLOW_BELIEF_THRESHOLD` = 0.4.

#### Parametri

| Parametro | Simbolo | Valore | Sorgente/Stato |
|---|---|---|---|
| Peso affidabilità | w_r | 0.3 | design regolabile (`belief.py:89-94`) |
| Peso fiducia relazionale | w_t | 0.2 | design regolabile (`belief.py:89-94`) |
| Peso personalità | w_p | 0.2 | design regolabile (`belief.py:89-94`) |
| Peso reputazione | w_rep | 0.3 | design regolabile (`belief.py:89-94`) |
| Contributo agreeableness alla personalità | — | 0.6 | Graziano e Tobin (2002) legano l'agreeableness al processing cooperativo di informazione |
| Contributo openness alla personalità | — | 0.4 | design regolabile (`belief.py:79`); non supportato dal paper Graziano e Tobin (2002) |
| Soglia di accettazione | τ_b | 0.4 | design regolabile (`EPOCHA_INFO_FLOW_BELIEF_THRESHOLD`); input neutri 0.5 producono accettazione, favorendo la propagazione dell'informazione sullo scetticismo |

#### Algoritmo

`should_believe(reliability, receiver_personality, relationship_strength, relationship_sentiment, transmitter_reputation)` in `belief.py:28-101` valuta l'equazione (4.23) e restituisce la decisione booleana di accettazione. Il `relationship_sentiment` negativo è clampato a zero nel componente di fiducia: la sfiducia non aumenta la fiducia (`belief.py:68-69`). La normalizzazione della reputazione delega a `reputation._normalize_reputation()` via lazy import per evitare la dipendenza circolare tra `belief.py` e `reputation.py` (chiusura N-5 Round 2). Il `transmitter_reputation = 0.0` di default mappa a un fattore reputazione neutro di 0.5, preservando la retrocompatibilità per i caller che non forniscono ancora l'argomento.

#### Semplificazioni

1. **Mayer (1995) liberamente ispirato, non strettamente implementato**: il filtro di credenza prende in prestito l'idea concettuale di decomporre la fiducia in più componenti ma non implementa i costrutti ability/benevolence/integrity del framework originale o i loro metodi di misurazione. Lo score a quattro componenti è operativo piuttosto che psicometrico. Riconosciuto inline nel docstring del modulo.

2. **Il contributo di openness al fattore personalità è una scelta di design**: Graziano e Tobin (2002) supportano il contributo di agreeableness ma non si estendono all'openness. Il peso di 0.4 sull'openness nel fattore personalità è giustificato dall'argomento qualitativo che individui aperti possano essere più ricettivi a informazione nuova; è documentato come scelta di design senza supporto empirico specifico ed esposto come parametro regolabile.

3. **La soglia di accettazione favorisce la propagazione sullo scetticismo**: con tutti gli input neutri (0.5), lo score di accettazione è 0.5, che supera la soglia 0.4 — gli agenti neutri accettano l'informazione per default. Questa è una scelta di design intenzionale. Impostare τ_b sopra 0.5 invertirebbe il bias a favorire lo scetticismo.

### 4.4.4 Affinità

> Stato: implementato a partire dal commit `a0ea07556ce8b32cea89ad543660fcb81be06b6e`, audit del codice CONVERGENTE 2026-05-16 round 2.

#### Background

L'affinità è lo score per-coppia che quantifica quanto è probabile che due agenti formino o si uniscano alla stessa fazione, ed è consumato a valle dal modulo delle fazioni e dal componente di fiducia relazionale del filtro di credenza. La similarità di personalità è fondata su McCrae e Costa (2003), *Personality in Adulthood* (2ª ed., Guilford Press): il modello a cinque fattori è il framework standard per misurare la similarità di personalità inter-individuale. La componente di circostanza è ispirata da Olson (1965), *The Logic of Collective Action*: i gruppi si formano attorno a condizioni materiali condivise, non solo all'affinità di personalità. L'euristica rivalità-come-affinità nello score relazionale attinge da Axelrod (1984), *The Evolution of Cooperation*, per le dinamiche di reciprocità da interazione ripetuta che rendono coalizionalmente rilevanti anche le relazioni ostili (chiusura N-8 Round 2).

#### Modello

Lo score di affinità è una media pesata di tre dimensioni ortogonali: similarità di personalità (distanza Euclidea Big Five), qualità relazionale (forza più sentiment positivo) e allineamento di circostanze (classe, mood, memoria di crisi condivisa, quartile di ricchezza, ruolo occupazionale). I pesi (0.3 / 0.3 / 0.4) riflettono il giudizio qualitativo che le fazioni si formano principalmente attorno a circostanze materiali condivise piuttosto che a match di personalità.

#### Equazioni

Equazione (4.24) — Similarità di personalità Big Five:

  similarity = 1 − ( sqrt( Σ_t (a_t − b_t)² ) / sqrt(5) )

dove la sommatoria scorre sui cinque tratti Big Five e il denominatore sqrt(5) è la distanza Euclidea massima quando ciascun tratto è in [0, 1]. I tratti mancanti hanno default 0.5 (il punto medio di [0, 1] — una prior neutra non informativa); il comportamento asimmetrico quando solo un agente è privo di un tratto è documentato come semplificazione N-7.

Equazione (4.25) — Score di affinità composito:

  affinity = w_P · similarity + w_R · relationship + w_C · circumstance

con w_P = 0.3, w_R = 0.3, w_C = 0.4. La componente relazionale è (strength + max(0, sentiment)) / 2; la componente di circostanza somma fattori additivi limitati a 1.0 (vedere la tabella Parametri).

#### Parametri

| Parametro | Simbolo | Valore | Sorgente/Stato |
|---|---|---|---|
| Peso personalità | w_P | 0.3 | design regolabile (`affinity.py:_W_PERSONALITY`); McCrae e Costa (2003) per la base Big Five |
| Peso relazionale | w_R | 0.3 | design regolabile (`affinity.py:_W_RELATIONSHIP`) |
| Peso circostanze | w_C | 0.4 | design regolabile (`affinity.py:_W_CIRCUMSTANCE`); Olson (1965) per il framing della primazia delle circostanze |
| Valore di default per tratto mancante | — | 0.5 | design regolabile (`affinity.py:_TRAIT_DEFAULT`); prior neutra non informativa |
| Finestra di recency per memoria condivisa | — | 10 tick | design regolabile (`affinity.py:_SHARED_MEMORY_WINDOW`) |
| Bonus additivo stessa classe sociale | — | +0.30 | design regolabile |
| Bonus additivo entrambi mood < 0.4 | — | +0.20 | design regolabile |
| Bonus memoria pubblica recente condivisa | — | +0.20 | design regolabile |
| Bonus stesso quartile di ricchezza | — | +0.15 | design regolabile (soglia: `abs(w_a - w_b) / max(w_a, w_b) < 0.25`) |
| Bonus stesso ruolo occupazionale | — | +0.15 | design regolabile |

#### Algoritmo

`compute_affinity(agent_a, agent_b, tick)` in `affinity.py:61-91` orchestra le tre componenti e restituisce uno score simmetrico clampato a [0.0, 1.0]. La similarità di personalità usa `_personality_similarity()` (`affinity.py:94-126`), che implementa l'equazione (4.24) con l'imputazione di default-to-midpoint del tratto (la chiusura N-7 Round 2 documenta il comportamento asimmetrico quando solo un agente è privo di un tratto). Lo score relazionale usa `_relationship_score()` (`affinity.py:129-176`), che esegue un lookup bidirezionale `Relationship.objects.get()` e ricade sul record più forte su `MultipleObjectsReturned`; l'euristica rivalità-come-affinità (solo il sentiment positivo aumenta lo score; il sentiment negativo non lo riduce sotto la baseline di strength) è giustificata dalla reciprocità da interazione ripetuta di Axelrod (1984) e dall'osservazione più ampia che anche le relazioni ostili coinvolgono alta interdipendenza (chiusura N-8 Round 2). Lo score di circostanza usa `_circumstance_score()` (`affinity.py:179-250`), che valuta i cinque bonus additivi rispetto a query PostgreSQL-backed su memorie e agenti con la finestra di memoria condivisa imposta via `tick_created__gte=tick - _SHARED_MEMORY_WINDOW`. Il guard `max_wealth > 0.0` previene la divisione per zero quando entrambi gli agenti hanno ricchezza zero (trattati come stesso quartile per definizione).

#### Semplificazioni

1. **N-7 — Imputazione asimmetrica del tratto mancante**: quando entrambi gli agenti sono privi di un tratto Big Five, la dimensione contribuisce zero distanza; quando solo un agente è privo del tratto, il valore presente è confrontato con 0.5, producendo una distanza non-zero proporzionale a quanto il valore presente sia lontano dal neutro. Questo comportamento asimmetrico è una limitazione nota dell'imputazione default-to-midpoint ed è documentato inline. Un approccio più principiato (es. imputazione multipla, o salto esplicito della dimensione su mancanza di un lato) è rimandato.

2. **N-8 — Euristica rivalità-come-affinità**: lo score relazionale prende (strength + max(0, sentiment)) / 2 — il sentiment negativo non sottrae dallo score sotto la baseline di strength. L'euristica è giustificata dalla reciprocità da interazione ripetuta di Axelrod (1984) e da Coleman (1990) sulla stabilità di coalizione sotto rivalità (Coleman 1990 è referenziato inline ma NON in §13 References del whitepaper); la rivalità concentra l'attenzione sociale e produce una dinamica coalizionale che la pura simpatia non può catturare. La scelta è documentata; uno schema alternativo che penalizzi la rivalità è aperto alla futura calibrazione.

3. **La soglia di quartile di ricchezza è relativa**: il bonus stesso-quartile usa `abs(w_a - w_b) / max(w_a, w_b) < 0.25` piuttosto che una differenza assoluta di ricchezza. La forma relativa scala naturalmente attraverso template per epoca con distribuzioni di ricchezza assoluta diverse; la soglia 0.25 è un parametro di design regolabile.

## 4.5 Istituzioni politiche

> Stato: implementato al commit `dfeb709218727c1efbca8cbee5e0dc6e974923fe`, audit del codice CONVERGENTE 2026-05-16 round 2.

Il cluster delle istituzioni politiche copre le dinamiche di regime, lo
scoring elettorale, l'accumulo e il decadimento istituzionale, e la
stratificazione (classe sociale + corruzione). Cinque moduli sotto
`epocha/apps/world/`:

1. `government.py` — tipi di regime, transizioni, colpi di stato, legittimità, stabilità
2. `government_types.py` — 12 template di regime con effetti istituzionali
3. `institutions.py` — accumulo di salute per tipo di istituzione
4. `stratification.py` — Gini, classi sociali, meccaniche di corruzione
5. `election.py` — modello di voto con personalità, reputazione, economia, carisma

Acemoglu e Robinson (2006); Bueno de Mesquita et al. (2003); Geddes (1999);
Polity 5 (Marshall e Gurr 2020); Powell e Thyne (2011); Freedom House;
più la letteratura sulla tipologia di regime e sul voto censita in §13 References.

### 4.5.1 Governo (regime + colpo di stato)

> Stato: implementato al commit `dfeb709218727c1efbca8cbee5e0dc6e974923fe`, audit del codice CONVERGENTE 2026-05-16 round 2.

#### Background

`government.py` orchestra il ciclo politico per tick: transizioni di regime,
risoluzione di colpo di stato, bookkeeping di legittimità e stabilità, e
gli aggiornamenti di indicatori che alimentano lo scoring elettorale a
valle e il feedback politico dell'economia. La tipologia di regime copre
i 12 archetipi dichiarati in `government_types.py` ed attinge da Geddes
(1999) per la forma empirica della sopravvivenza di regime, dal dataset
Polity 5 (Marshall e Gurr 2020) per la spina dorsale della classificazione
di regime, e dai report annuali di Freedom House per la traiettoria
qualitativa dell'erosione istituzionale nelle democrazie in declino.

#### Modello

Le transizioni di regime seguono l'inquadramento di meccanismi endogeni
di Acemoglu e Robinson (2006) e la struttura di hazard della sopravvivenza
di regime di Geddes (1999): il motore valuta condizioni trigger per tipo
di regime e passa al successore configurato quando il trigger scatta. La
decisione di colpo di stato è stocastica — il coup-score calcolato è
interpretato come probabilità di successo confrontata con un draw di
`random.random()` — calibrata sul tasso empirico di successo del ~50% di
tutti i tentativi riportato da Powell e Thyne (2011); la forma legacy a
soglia deterministica è registrata come finding G-2 del Round 2 e
chiusa esplicitamente. La stabilità è ricalcolata ogni ciclo come
combinazione convessa di componenti di economia, legittimità e lealtà
militare i cui pesi sono letti per-regime da `government_types.py`.

#### Equazioni

Equazione (4.26) — Score di probabilità di colpo di stato:

  coup_probability = 0.4·cohesion + 0.3·leader_charisma + 0.3·(1 − military_loyalty)

Lo score è consumato come probabilità di successo confrontata con
`random.random() < coup_probability`. La forma a tripla ponderazione segue
l'osservazione narrativa secondo cui i colpi di stato richiedono coesione
interna organizzata, un leader focale e un militare non impegnato con
l'incumbent; i pesi esatti sono parametri di design regolabili.

Equazione (4.27) — Indice di stabilità:

  stability = w_economy·economy + w_legitimacy·legitimacy + w_military·military_loyalty

con pesi per-regime `(w_economy, w_legitimacy, w_military)` letti da
`GOVERNMENT_TYPES[regime].stability_weights` (es. democrazia pesa
fortemente economia e legittimità; regimi militari pesano fortemente la
lealtà).

#### Parametri

| Parametro | Simbolo | Valore | Fonte/Stato |
|---|---|---|---|
| Decadimento di trust istituzionale per ciclo | — | 0.05 | design regolabile (`government.py:_TRUST_DECAY`); qualitativamente consistente con i report annuali di Freedom House |
| Tasso di drift di repressione per ciclo | — | 0.10 | design regolabile (`government.py:_REPRESSION_DRIFT_RATE`) |
| Peso di legittimità su salute | — | 0.20 | design regolabile (`government.py:_LEGITIMACY_W_HEALTH`) |
| Peso di legittimità su istruzione | — | 0.15 | design regolabile (`government.py:_LEGITIMACY_W_EDUCATION`) |
| Peso di legittimità su economia | — | 0.35 | design regolabile (`government.py:_LEGITIMACY_W_ECONOMY`) |
| Peso di legittimità su media | — | 0.30 | design regolabile (`government.py:_LEGITIMACY_W_MEDIA`) |
| Soglia di indipendenza dei media per inflazione di propaganda | — | 0.30 | design regolabile (`government.py:_MEDIA_INDEPENDENCE_THRESHOLD`) |
| Fattore di inflazione di propaganda sulla legittimità riportata | — | +0.30 | design regolabile (`government.py:_PROPAGANDA_FACTOR`) |
| Pesi di stabilità per-regime | — | per `GOVERNMENT_TYPES` | design regolabile (`government_types.py`) |
| Target di tasso base di colpo di stato | — | ~0.50 | ancoraggio empirico Powell e Thyne (2011) |

#### Algoritmo

`process_political_cycle(world, tick)` in `government.py` è wrappato in
`@transaction.atomic` e acquisisce `select_for_update()` sulla riga
`Government` per prevenire la race di tick concorrenti che il finding N-6
del Round 2 ha identificato tra la mutazione di corruzione in
`stratification.py:process_corruption` (step 3 del ciclo politico) e
l'aggiornamento di indicatori in `government.py:update_government_indicators`
(step 4). La pipeline a 8 step è: (1) aggiornamento di salute delle
istituzioni; (2) ricalcolo di Gini e classi sociali; (3) skim di corruzione
(wealth-conserving, da `stratification.py`); (4) aggiornamento di
indicatori (institutional_trust, popular_legitimacy, military_loyalty,
repression_level, con inflazione di propaganda quando l'indipendenza dei
media è bassa); (5) valutazione di transizione di regime; (6) scheduling
elettorale; (7) risoluzione di colpo di stato (stocastica per equazione
(4.26)); (8) snapshot di storia. Lo step 7 seleziona al più un colpo di
stato per ciclo; quando più gruppi soddisfano la soglia trigger, il gruppo
con lo score più alto è quello che tenta. La scelta single-attempt-per-cycle
è registrata come finding N-13 del Round 2 ed è documentata inline in
`government.py` come bias di selezione deliberato.

#### Semplificazioni

1. **G-1 — I pesi di legittimità sono parametri di design regolabili**: i
   quattro pesi `(_LEGITIMACY_W_HEALTH, _LEGITIMACY_W_EDUCATION,
   _LEGITIMACY_W_ECONOMY, _LEGITIMACY_W_MEDIA) = (0.20, 0.15, 0.35, 0.30)`
   riflettono l'importanza relativa assunta dei domini istituzionali
   piuttosto che un fit empirico. Chiusa nel Round 2 da documentazione
   inline.

2. **G-2 — La decisione di colpo di stato è stocastica, non
   deterministica**: pre-Round 2 la decisione era una soglia deterministica
   sullo score; l'implementazione corrente valuta
   `random.random() < coup_probability`, consistente con il tasso base
   empirico di successo dei colpi di stato di Powell e Thyne (2011). La
   costante legacy `_COUP_SUCCESS_THRESHOLD` è deprecata.

3. **G-3 — Il tasso di decadimento del trust istituzionale è regolabile**:
   il decadimento 0.05/ciclo è una scelta di design ed è esposta per
   calibrazione per epoca. I report di Freedom House documentano il
   pattern qualitativo di erosione istituzionale nelle democrazie in
   declino ma non pubblicano un tasso di decadimento per-periodo.

4. **G-6 — `stability_index` è usato come proxy economia**: le funzioni
   `_update_stability()` e `update_government_indicators()` consumano
   `World.stability_index` come input "economia"; il campo è calcolato
   dal modulo economy come segnale di umore medio piuttosto che come un
   indicatore economico reale. La fix comportamentale instraderebbe la
   funzione attraverso un indicatore economico dedicato quando uno
   diventa disponibile; il comportamento corrente è documentato inline in
   `government.py`.

5. **N-13 — Bias di selezione del colpo di stato verso il gruppo con score
   più alto**: al più un colpo di stato è risolto per ciclo; quando più
   gruppi soddisfano la soglia trigger, viene selezionato quello con lo
   score di colpo di stato più alto. Questo bias la simulazione verso il
   contendente singolo più forte per ciclo piuttosto che modellare
   tentativi simultanei; la scelta è documentata inline.

### 4.5.2 Tipi di governo

> Stato: implementato al commit `dfeb709218727c1efbca8cbee5e0dc6e974923fe`, audit del codice CONVERGENTE 2026-05-16 round 2.

#### Background

`government_types.py` dichiara i 12 archetipi di regime che `government.py`
consuma: democrazia, democrazia illiberale, autocrazia, monarchia,
oligarchia, teocrazia, totalitarismo, regime terrorista, anarchia,
federazione, cleptocrazia, giunta. Ciascun archetipo è un dizionario di
quattro gruppi di attributi — `repression_tendency`, `corruption_resistance`,
`institution_effects`, `stability_weights` — che guidano gli aggiornamenti
di indicatori per ciclo di §4.5.1. La tipologia e la differenziazione di
attributi per-regime sono ispirate alla classificazione di regime Polity 5
(Marshall e Gurr 2020), alla metodologia di misurazione di Freedom House,
e al framework della selectorate theory di Bueno de Mesquita et al. (2003).

#### Modello

Ciascun template di regime porta quattro gruppi di attributi.
`repression_tendency` imposta l'asintoto verso cui `Government.repression_level`
deriva ogni ciclo in §4.5.1. `corruption_resistance` modula la magnitudo
dello skim di corruzione che `stratification.py:process_corruption` applica.
`institution_effects` dichiara delta per-tipo-di-istituzione che aumentano
o attenuano la salute istituzionale in §4.5.3. `stability_weights` è la
tripla `(w_economy, w_legitimacy, w_military)` consumata dall'equazione
(4.27).

#### Equazioni

Equazione (4.28) — Effetto di istituzione sotto un regime:

  institution_effect = base_value + regime_effect · INSTITUTION_EFFECT_SCALE

con `INSTITUTION_EFFECT_SCALE = 20.0` (da `institutions.py`, vedere
§4.5.3 Parametri). `regime_effect` è l'entry per-(regime, tipo-istituzione)
del template di regime; `base_value` è il delta di salute standalone
dell'istituzione prima della modulazione di regime.

#### Parametri

Il set completo di parametri per-regime è abbastanza grande da appartenere
all'Appendice A; la vista in-capitolo è quella strutturale — 12 regimi × 4
gruppi di attributi (`repression_tendency` scalare,
`corruption_resistance` scalare, `institution_effects` dict,
`stability_weights` tripla). Gli ancoraggi di letteratura sono Polity 5
(Marshall e Gurr 2020) per la spina dorsale della classificazione di
regime, Freedom House per la metodologia che informa l'ordinamento
per-regime, Bueno de Mesquita et al. (2003) per l'intuizione di
selectorate dietro i pesi di stabilità per-regime, e Acemoglu e Robinson
(2006) per la forma della transizione endogena.

#### Algoritmo

Un lookup per nome di regime restituisce il dizionario di configurazione
che `government.py` consuma durante il ciclo politico. Il modulo è
data-only e non porta logica per-tick propria.

#### Semplificazioni

1. **GT-1 — Tutti i valori sono parametri di design, non derivati dalle
   fonti citate**: i quattro gruppi di attributi attraverso tutti i 12
   regimi sono parametri di design regolabili ispirati alla letteratura
   citata piuttosto che fit empirici. Polity 5 pubblica una
   classificazione di regime ma non la quintupla per-regime
   `(_TRUST_SCALE, repression_tendency, corruption_resistance,
   institution_effects, stability_weights)` nella forma che Epocha
   consuma. Il disclaimer a livello di modulo documenta questo
   esplicitamente; chiusa dal Round 2.

### 4.5.3 Istituzioni

> Stato: implementato al commit `dfeb709218727c1efbca8cbee5e0dc6e974923fe`, audit del codice CONVERGENTE 2026-05-16 round 2.

#### Background

`institutions.py` porta le dinamiche di salute per-istituzione che il
ciclo politico consuma. Il modello è qualitativamente ispirato al
framework di disuguaglianza delle istituzioni di Acemoglu e Robinson
(2012), *Why Nations Fail*, e al trattamento della capacità statale di
Besley e Persson (2011), *Pillars of Prosperity*. Ciascuna istituzione
porta uno scalare `health ∈ [0, 1]` che decade a un tasso di entropia
configurabile, è aumentato dai finanziamenti, ed è modulato dagli effetti
istituzionali per-regime di §4.5.2.

#### Modello

Ogni ciclo, la salute di ciascuna istituzione è aggiornata da tre
contributi additivi: finanziamento (proporzionale al `funding_level`
dell'istituzione), modulazione di regime (l'entry `regime_effect` di
§4.5.2 moltiplicato per il fattore di scala), ed entropia (una costante
negativa). La nuova salute è clippata a [0, 1].

#### Equazioni

Equazione (4.29) — Aggiornamento di salute di istituzione per ciclo:

  health_{t+1} = clip( health_t + funding_delta + regime_effect_delta + entropy , 0, 1 )

con `funding_delta = funding_level · FUNDING_EFFECT_RATE`,
`regime_effect_delta = regime_effect · INSTITUTION_EFFECT_SCALE`, ed
`entropy = ENTROPY_PER_TICK`.

#### Parametri

| Parametro | Simbolo | Valore | Fonte/Stato |
|---|---|---|---|
| Scala di effetto istituzionale | — | 20.0 | design regolabile (`institutions.py:INSTITUTION_EFFECT_SCALE`); calibrato in modo che una forte modulazione di regime raggiunga il quasi-picco in ~33 cicli (~2-3 anni alla mappatura tick standard) |
| Tasso di effetto del finanziamento per ciclo | — | 0.04 | design regolabile (`institutions.py:FUNDING_EFFECT_RATE`) |
| Entropia per tick (decadimento lineare) | — | -0.005 | design regolabile (`institutions.py:ENTROPY_PER_TICK`); decadimento lineare che raggiunge il 50% dopo 100 tick di investimento zero — NON half-life esponenziale |

#### Algoritmo

`update_institutions(world, tick)` in `institutions.py` itera tutte le
istituzioni del mondo e applica l'equazione (4.29). Dopo il finding N-12
del Round 2, il `save()` per-riga è stato sostituito con `bulk_update()`
sui valori di salute raccolti, riducendo i round-trip DB per ciclo
proporzionalmente al numero di istituzioni.

#### Semplificazioni

1. **I-1 — La calibrazione della timescale è guidata dal design**:
   l'`INSTITUTION_EFFECT_SCALE = 20.0` è impostata in modo che una forte
   modulazione di regime raggiunga il quasi-picco in circa 33 cicli (~2-3
   anni alla mappatura tick-anno standard). La mappatura stessa è
   regolabile; la scala scelta è un'euristica piuttosto che un fit
   empirico.

2. **I-2 — Il tasso di finanziamento è regolabile**:
   `FUNDING_EFFECT_RATE = 0.04` è una scelta di design che non traccia né
   un dataset di finanza pubblica specifico né uno studio ROI per-dominio;
   è esposto per calibrazione per epoca.

3. **I-3 — Il decadimento è lineare, non esponenziale**: il termine di
   entropia applica un costante `-0.005` per ciclo, producendo un
   decadimento lineare che raggiunge il 50% dopo 100 tick di investimento
   zero. Il docstring pre-Round 2 usava il linguaggio "half-life"; il
   docstring corrente corregge in "decadimento lineare che raggiunge il
   50% dopo 100 tick di investimento zero" (chiusura del finding I-3 del
   Round 2).

### 4.5.4 Stratificazione

> Stato: implementato al commit `dfeb709218727c1efbca8cbee5e0dc6e974923fe`, audit del codice CONVERGENTE 2026-05-16 round 2.

#### Background

`stratification.py` calcola il Gini per-mondo, assegna gli agenti a classi
sociali dalla distribuzione di ricchezza, ed esegue lo skim di corruzione
per ciclo che devia ricchezza dal pool comune del mondo al capo dello
stato. Il coefficiente Gini segue Gini (1912); la semplificazione della
struttura di classe a cinque classi è una coarse-graining dello schema a
sei classi di Gilbert (2011); l'inquadramento della corruzione attinge a
Acemoglu e Robinson (2006); i pesi asimmetrici di mobilità modulati dalla
personalità sono ancorati al rapporto di loss-aversion di Kahneman e
Tversky (1979).

#### Modello

Il Gini è calcolato dal vettore di ricchezza degli agenti; l'assegnazione
di classe usa soglie di quintile di ricchezza fisse; lo skim di
corruzione è wealth-conserving — l'ammontare rimosso da
`world.global_wealth` è esattamente l'ammontare accreditato a
`agent.wealth` del capo di stato corrotto. La logica di mobilità applica
un rapporto di peso asimmetrico tra transizioni verso l'alto e verso il
basso, riflettendo il principio di loss-aversion secondo cui i movimenti
verso il basso sono percepiti più fortemente di equivalenti movimenti
verso l'alto.

#### Equazioni

Equazione (4.30) — Coefficiente Gini (Gini 1912):

  Gini = (1 / (n · μ)) · Σᵢ (2i − n − 1) · xᵢ

con i valori di ricchezza degli agenti `xᵢ` ordinati ascendenti, `n` il
conteggio degli agenti, e `μ` la ricchezza media.

Equazione (4.31) — Assegnazione di classe da quintili di ricchezza:

  class(agent) =
    UPPER          if w(agent) ≥ q80
    UPPER_MIDDLE   if q50 ≤ w(agent) < q80
    MIDDLE         if q15 ≤ w(agent) < q50
    WORKING        if q5 ≤ w(agent) < q15
    LOWER          if w(agent) < q5

con i cutpoint di percentile `q5, q15, q50, q80` calcolati dalla
distribuzione di ricchezza degli agenti.

Equazione (4.32) — Skim di corruzione wealth-conserving:

  skim_amount  = corruption_susceptibility · _CORRUPTION_SKIM_RATE · world.global_wealth
  world.global_wealth ← world.global_wealth − skim_amount
  head_of_state.wealth ← head_of_state.wealth + skim_amount

Lo skim è wrappato in `@transaction.atomic` in modo che le due scritture
applichino entrambe o nessuna; questo è la chiusura del finding N-3 del
Round 2 (pre-Round 2 le due scritture erano non protette e potevano
produrre ricchezza libera sotto esecuzione concorrente).

#### Parametri

| Parametro | Simbolo | Valore | Fonte/Stato |
|---|---|---|---|
| Soglie di classe (quintili) | — | 5 / 15 / 50 / 80 | Gilbert (2011) ispira lo schema di classe; gli specifici cutpoint di percentile sono scelte di design regolabili |
| Tasso di skim di corruzione | — | 0.02 | design regolabile (`stratification.py:_CORRUPTION_SKIM_RATE`); riferimento qualitativo a Transparency International CPI per l'ordinamento relativo attraverso i tipi di regime |
| Soglia di conscientiousness per suscettibilità alla corruzione | — | 0.4 | design regolabile; Miller e Lynam (2001) ispirano il legame tra bassa conscientiousness e devianza dalle norme, ma il cutoff stesso è una scelta di design |
| Rapporto di loss-aversion (peso mobilità verso il basso : verso l'alto) | — | 1.75 : 1 | design regolabile che approssima il rapporto ~2 : 1 di Kahneman e Tversky (1979) |

#### Algoritmo

`compute_gini(world)` valuta l'equazione (4.30) sul vettore di ricchezza
per-agente. `update_social_classes(world)` valuta l'equazione (4.31) e
scrive la classe assegnata su ciascun agente. `process_corruption(world,
tick)` implementa l'equazione (4.32) sotto `@transaction.atomic` in modo
che il decremento di `world.global_wealth` e l'incremento di
`agent.wealth` siano atomici rispetto all'esecuzione concorrente di tick;
questo chiude il finding N-3 del Round 2.

#### Semplificazioni

1. **S-1 — Cinque classi vs lo schema a sei classi di Gilbert (2011)**:
   Epocha coarse-grain lo schema a sei classi di Gilbert (2011) a cinque
   classi fondendo le classi "capitalist" e "upper" in una singola classe
   UPPER. La semplificazione è documentata inline; le percentuali di
   soglia di classe sono esposte per ricalibrazione per epoca.

2. **S-2 — Conservazione della ricchezza imposta**: lo skim di corruzione
   è wealth-conserving per costruzione (equazione (4.32)); il wrapping
   `@transaction.atomic` previene artefatti di ricchezza libera sotto
   esecuzione concorrente. Chiusura del finding N-3 del Round 2.

3. **S-3 — La soglia di conscientiousness è una scelta di design
   regolabile**: la soglia `conscientiousness < 0.4` è ispirata al legame
   Miller e Lynam (2001) tra bassa conscientiousness e devianza dalle
   norme, ma il cutoff stesso non è derivato da quel paper. La citazione
   pre-Round 2 ad Acemoglu e Robinson (2006) è stata rimossa (Acemoglu e
   Robinson discutono vincoli istituzionali, non cutoff di personalità).

4. **S-4 — I pesi emozionali/di mobilità sono regolabili**: le magnitudo
   di mobilità verso l'alto/basso (0.4 e 0.7) preservano il rapporto
   ~2:1 di loss-aversion di Kahneman e Tversky (1979) ma le specifiche
   magnitudo stesse sono scelte di design; l'ancoraggio principiato è il
   rapporto, non i valori assoluti.

### 4.5.5 Elezioni

> Stato: implementato al commit `dfeb709218727c1efbca8cbee5e0dc6e974923fe`, audit del codice CONVERGENTE 2026-05-16 round 2.

#### Background

`election.py` implementa il modello di voto per-elezione che il ciclo
politico usa per eleggere un nuovo capo di stato quando scatta un trigger
elettorale. Lo score di voto è una combinazione convessa pesata di cinque
componenti — relazione, personalità, economia, reputazione, carisma —
ancorata alla letteratura di psicologia politica: Caprara et al. (2006)
per la base di personalità, Huckfeldt e Sprague (1987) per la componente
di rete-relazione, Lewis-Beck e Stegmaier (2000) per la componente di
voto economico, Lodge, Steenbergen e Brau (1995) per l'operazionalizzazione
della valutazione del candidato, e Bass (1985), Weber (1922) e Merolla e
Zechmeister (2011) per la componente di carisma.

#### Modello

Per ciascun votante e candidato, lo score è calcolato come somma pesata
delle cinque componenti; il candidato con lo score più alto vince la
scheda del votante. Il bonus di manipolazione è poi applicato al conteggio
cumulativo per-candidato (il bonus è un modificatore di
corruzione-o-clientelismo per-candidato regolabile).

#### Equazioni

Equazione (4.33) — Score di voto per-votante:

  vote_score = w_rel·relationship + w_pers·personality + w_econ·economic + w_rep·reputation + w_char·charisma

con pesi `(w_rel, w_pers, w_econ, w_rep, w_char) = (0.25, 0.15, 0.20, 0.25, 0.15)`.

Equazione (4.34) — Normalizzazione del fattore di reputazione:

  reputation_factor = _normalize_reputation(reputation_raw)

dove `_normalize_reputation()` è l'helper centralizzato importato da
`agents/reputation.py` (chiusura del finding N-5 del Round 2 — pre-Round
2 il modulo election portava una normalizzazione locale che divergeva
dalla single source of truth `reputation.py` usata dal belief filter di
§4.4.3).

#### Parametri

| Parametro | Simbolo | Valore | Fonte/Stato |
|---|---|---|---|
| Peso relazione | w_rel | 0.25 | design regolabile (`election.py`); Huckfeldt e Sprague (1987) per la base concettuale |
| Peso personalità | w_pers | 0.15 | design regolabile; Caprara et al. (2006) per la base di personalità |
| Peso economico | w_econ | 0.20 | design regolabile; Lewis-Beck e Stegmaier (2000) per la base di voto economico |
| Peso reputazione | w_rep | 0.25 | design regolabile; fattore di reputazione normalizzato tramite l'helper centralizzato di `reputation.py` |
| Peso carisma | w_char | 0.15 | design regolabile; Bass (1985), Weber (1922), Merolla e Zechmeister (2011) per la base di carisma |
| Costante di saturazione di ricchezza | — | 100.0 | design regolabile (`election.py:_WEALTH_SATURATION`); legata al default `Agent.wealth = 50.0` in modo che la funzione saturante raggiunga half-max alla baseline della popolazione |

#### Algoritmo

La lista dei votanti è materializzata una sola volta in
`voter_list = list(...)` e il conteggio dei votanti è catturato tramite
`voter_count = len(voter_list)` per il loop del bonus di manipolazione
(chiusura dei finding N-5 e E-5 del Round 2 — pre-Round 2 il loop
rivalutava `voters.count()` o `len(list(voters))` su ciascuna iterazione).
Il bonus di manipolazione è applicato al conteggio cumulativo di ciascun
candidato; il candidato con il conteggio più alto vince l'elezione ed è
riscritto come nuovo capo dello stato.

#### Semplificazioni

1. **E-3 — I pesi di voto sono scelte di design regolabili**: la
   cinque-tupla `(0.25, 0.15, 0.20, 0.25, 0.15)` è il default corrente ed
   è esposta per calibrazione per epoca; la letteratura citata supporta
   la *presenza* di ciascuna componente piuttosto che la *magnitudo* del
   suo peso.

2. **E-4 — La saturazione di ricchezza è legata alla scala interna di
   ricchezza**: `_WEALTH_SATURATION = 100.0` è legata al default
   `Agent.wealth` di 50.0 in modo che la funzione saturante raggiunga
   half-max alla baseline della popolazione; il valore assoluto è
   significativo solo all'interno della scala interna di ricchezza di
   Epocha.

3. **E-5 — La valutazione della query è cacheata**: il QuerySet dei
   votanti è materializzato una sola volta e la sua lunghezza catturata
   in una locale prima del loop del bonus di manipolazione; la
   ri-valutazione per-iterazione è rimossa. Chiusura del finding E-5 del
   Round 2.

## 4.6 Movimento

> Stato: implementato al commit `c543c102a4af9f44c35fd25988c471e0f97632cd`, audit del codice CONVERGENTE 2026-05-16 round 2.

### Background

Il modulo movimento governa la rilocazione per tick degli agenti tra zone sotto tre classi di intento: migrazione economica volontaria (azione `move_to_zone`), migrazione sociale volontaria (attrazione relazionale verso partner/genitore/leader di fazione) e movimento involontario (distruzione/espulsione dalla zona). Le velocità di viaggio sono calibrate contro Chandler (1966) *The Campaigns of Napoleon* per i ritmi militari (fanteria sostenuta 20-35 km/giorno; cavalleria 60 km/giorno; carrozza con relais 60-80 km/giorno) e Braudel (1979) *Civiltà materiale, economia e capitalismo* per i ritmi civili pre-industriali (mercanti a piedi ~25 km/giorno; barche fluviali/su canali ~50 km/giorno). L'implementazione usa il punto medio civile dove possibile: a piedi=25 (Braudel), a cavallo=60 (Chandler cavalleria militare — borderline usato come default), carrozza=60 (Chandler estremo basso senza relais), barca=50 (Braudel).

### Modello

La distanza di viaggio per tick è una funzione moltiplicativa di: velocità base della modalità di trasporto, salute dell'agente (fattore salute con floor 0.1), qualità della strada (moltiplicatore per terreno), repressione politica (1 - regime.repression_tendency per regimi non democratici) e stabilità mondiale (1 + (stability - 0.5)·0.2). Il risultato è il massimo di km che l'agente può coprire in questo tick; il movimento effettivo è limitato dalla distanza in unità di griglia in linea retta al target moltiplicata per `World.distance_scale` per convertire unità di griglia in km. Il movimento parziale interpola linearmente verso il target in unità di griglia; il movimento completo posiziona l'agente al centroide della zona target più un offset di dispersione di arrivo.

### Equazioni

Equazione (4.35) distanza massima per tick:

  max_distance_km = TRAVEL_SPEEDS[mode] · health_factor · terrain_factor · repression_factor · stability_factor · tick_duration_days

dove `health_factor = max(0.1, health)`, `repression_factor = 1 - regime.repression_tendency` (clamped non negativo), `stability_factor = 1 + (world.stability - 0.5) · 0.2`.

Equazione (4.36) vettore di movimento parziale:

  new_location = current_location + (target_location - current_location) · (max_distance_km / required_km)

dove `required_km = euclidean_distance(current, target) · World.distance_scale / 1000`.

Equazione (4.37) dispersione di arrivo (ramo di movimento completo):

  arrival_location = target_centroid + uniform(-ARRIVAL_SCATTER_RANGE, +ARRIVAL_SCATTER_RANGE)·2

con `_ARRIVAL_SCATTER_RANGE = 40.0` unità di griglia (assume confine di zona di 100 unità).

### Parametri

| Parametro | Valore | Fonte | Stato |
|---|---|---|---|
| velocità a piedi | 25 km/giorno | Braudel 1979 (mercante civile) | verificato |
| velocità a cavallo | 60 km/giorno | Chandler 1966 (cavalleria militare, usato come default) | regolabile |
| velocità carrozza | 60 km/giorno | Chandler 1966 (floor civile senza relais) | regolabile |
| velocità barca | 50 km/giorno | Braudel 1979 (fluviale/canale) | verificato |
| ROLE_TRANSPORT default | dict per ruolo | linguaggio degli scenari di simulazione | regolabile |
| fattori di terreno {urban, commercial, industrial, rural, wilderness} | {1.0, 1.0, 0.9, 0.7, 0.5} | ordinamento qualitativo Braudel 1979 (qualità della strada); magnitudini regolabili | regolabile |
| _MOOD_COST_PER_MOVEMENT | piccola costante | parametro di design regolabile | regolabile |
| _HEALTH_COST_EXHAUSTING_TRAVEL | piccola costante | parametro di design regolabile | regolabile |
| _EXHAUSTION_THRESHOLD | 0.5 | parametro di design regolabile | regolabile |
| _ARRIVAL_SCATTER_RANGE | 40.0 unità di griglia | assume confine di zona di 100 unità | regolabile |

### Algoritmo

1. `calculate_max_distance(agent, world)` restituisce il budget di movimento per tick in km.
2. `execute_movement(agent, target_zone, world)` o: (a) completa il viaggio se max_distance ≥ required_km, posizionando l'agente al target_centroid + arrival_scatter, applicando il costo pieno di umore/salute; oppure (b) muove parzialmente l'agente lungo la linea verso il target di max_distance/required_km, applicando il costo parziale di umore.
3. Gli aggiornamenti di umore e salute sono clamped a [0, 1].
4. Il logger registra gli eventi di movimento per osservabilità.

### Semplificazioni

- **Convenzione delle coordinate (N-1)**: le coordinate agente/zona sono unità di griglia astratte nonostante i campi PostGIS dichiarino SRID 4326. `World.distance_scale` (default 133 m/unità di griglia) converte in km reali. Documentato nel docstring del modulo `movement.py`. La fix comportamentale (coordinate proiettate) è rimandata scope-positive.
- **Grafo inter-zona (R1 riconosciuto)**: il routing usa il grafo astratto delle zone di `world/models.py` non la geometria effettiva delle zone. Geometria PostGIS disponibile ma layer di routing rimandato alla roadmap PostGIS più ampia.
- **Riproducibilità RNG (N-8)**: `random.uniform` usa l'RNG globale di Python, non il `get_seeded_rng` seedato dalla simulazione. Due esecuzioni con seed identico producono offset di dispersione di arrivo differenti. Lavoro futuro: passare l'RNG della simulazione al movimento.
- **Assunzione dimensione zona per la dispersione di arrivo (M-5)**: `_ARRIVAL_SCATTER_RANGE = 40.0` assume un confine di zona di 100 unità non imposto. Lavoro futuro: relativo al bounding box effettivo della zona.
- **Bare except nel chiamante (N-3)**: `simulation/engine.py:168` avvolge `execute_movement` in `try/except Exception`. Concern cross-modulo; tracciato per un futuro audit del cluster simulation.

### Stato

> Stato: implementato al commit `c543c102a4af9f44c35fd25988c471e0f97632cd`, audit del codice CONVERGENTE 2026-05-16 round 2.

---

## 4.7 Fazioni

> Stato: implementato a partire dal commit `5406b95a74d3281bc98665923818d7e708745120`, audit del codice CONVERGENTE 2026-05-16 round 2.

### Background

Il modulo delle fazioni governa le dinamiche intra-fazione dei gruppi di agenti lungo il loro ciclo di vita: aggiornamento della coesione per tick, scoring dell'emergenza di leadership, legittimità e successione della leadership, dissoluzione sotto una soglia di viabilità, scissione di una sotto-cricca ostile in un gruppo splinter, e formazione bottom-up di nuove fazioni da agenti non affiliati. Il frame concettuale è Olson (1965), *The Logic of Collective Action*, per la soglia di viabilità dell'azione collettiva sotto la quale un gruppo si disgrega, e Festinger et al. (1950), *Social Pressures in Informal Groups*, per il trattamento della coesione come quantità mantenuta dall'interazione cooperativa ed erosa dal conflitto interno. L'emergenza di leadership è ancorata alla meta-analisi tratti-leadership di Judge et al. (2002); la direzione del bias di negatività dell'asimmetria di coesione segue Baumeister et al. (2001). Il meccanismo dei beni di club di Iannaccone (1992) (coesione attraverso il sacrificio di segnale costoso, marcatori di confine escludenti, rilevamento dei free-rider) NON è implementato ed è registrato come estensione rimandata.

### Modello

La coesione di gruppo evolve a ogni intervallo per un delta che premia le azioni cooperative dei membri, penalizza quelle conflittuali con un peso maggiore (bias di negatività), sottrae una penalità di costo di coordinamento che cresce con la membership oltre una soglia di piccolo gruppo, e aggiunge un termine di efficacia del leader legato alla legittimità del leader. L'emergenza di leadership è una somma pesata a cinque componenti del carisma, intelligenza, rank di ricchezza relativa, sentiment medio intra-gruppo e anzianità di un agente. La legittimità della leadership è una somma pesata a tre componenti di coesione di gruppo, sentiment medio del leader dai membri e rank di leadership-score del leader; una legittimità sotto soglia innesca la successione. La scissione partiziona un gruppo quando il sentiment medio di una sotto-cricca verso il resto scende sotto una soglia di ostilità, seedando un gruppo splinter a coesione iniziale ridotta. Tutti i pesi scalari, le soglie e i coefficienti sono parametri di design regolabili, attribuiti alla direzione qualitativa della letteratura citata ma non derivati da essa.

### Equazioni

Equazione (4.38) delta di coesione per intervallo:

  cohesion_delta = cooperation_ratio · 0.10 − conflict_ratio · 0.15 − size_penalty · 0.02 + leader_effectiveness · 0.05

dove `cooperation_ratio` e `conflict_ratio` sono le frazioni di azioni cooperative (help, socialize) e conflittuali (argue, betray) dei membri sull'intervallo, `size_penalty = max(0, member_count − 5)`, e `leader_effectiveness = legitimacy − 0.5`.

Equazione (4.39) score di emergenza di leadership:

  leadership_score = charisma · 0.30 + intelligence · 0.20 + wealth_rank · 0.15 + internal_sentiment · 0.20 + seniority · 0.15

dove `internal_sentiment` è il sentiment medio di relazione dell'agente con gli altri membri mappato da [−1, 1] a [0, 1], `wealth_rank` è la posizione economica relativa dell'agente nel gruppo, e `seniority = min((tick − join_tick) / group_age, 1.0)`.

Equazione (4.40) legittimità della leadership:

  legitimacy = group_cohesion · 0.40 + leader_sentiment · 0.40 + score_rank · 0.20

dove `leader_sentiment` è il sentiment medio del leader dai membri mappato a [0, 1] e `score_rank ∈ [0, 1]` ordina il leadership_score del leader rispetto a tutti i membri.

Equazione (4.41) innesco di scissione: una sotto-cricca candidata (costruita greedy da un agente seme, aggiungendo membri il cui sentiment reciproco supera `_ALLY_SENTIMENT_THRESHOLD = 0.2`) si stacca quando il suo sentiment medio verso il resto non appartenente alla cricca scende sotto `_SCHISM_OUTWARD_SENTIMENT_THRESHOLD = −0.2`.

### Parametri

| Parametro | Valore | Fonte | Stato |
|---|---|---|---|
| coefficiente cooperazione | 0.10 | budget di calibrazione; Baumeister 2001 ancora solo la direzione dell'asimmetria | regolabile |
| coefficiente conflitto | 0.15 | budget di calibrazione; 1.5:1 vs cooperazione è direzione di bias di negatività (Baumeister 2001), non il rapporto | regolabile |
| coefficiente penalità di taglia | 0.02 | budget di calibrazione | regolabile |
| coefficiente efficacia leader | 0.05 | budget di calibrazione | regolabile |
| soglia penalità di taglia | 5 | regolabile; principio generico di piccolo gruppo Hackman 2002; NON Dunbar 1992 (~150) né Zhou et al. 2005 (strato cricca intima) | regolabile |
| pesi leadership {carisma, intelligenza, wealth_rank, internal_sentiment, anzianità} | {0.30, 0.20, 0.15, 0.20, 0.15} | regolabile; coerente con direzione effect-size Judge 2002, non derivato; carisma per Weber 1922 + Antonakis et al. 2016 | regolabile |
| pesi legittimità {coesione, leader_sentiment, score_rank} | {0.40, 0.40, 0.20} | budget di calibrazione | regolabile |
| soglia sentiment alleato | +0.2 | budget di calibrazione (simmetrica) | regolabile |
| soglia sentiment esterno di scissione | −0.2 | budget di calibrazione (simmetrica) | regolabile |
| fallback sentiment senza relazione | 0.3 (normalizzato = raw −0.4) | default conservativo regolabile | regolabile |
| coesione seme splinter | 0.5 | regolabile; sotto nuova-fazione 0.6 (porta conflitto del genitore) | regolabile |
| coesione seme nuova-fazione | 0.6 | regolabile | regolabile |
| soglie dissoluzione / legittimità / affinità | 0.2 / 0.3 / 0.5 | default di settings, budget di calibrazione | regolabile |
| grading Memory.emotional_weight | 0.2 / 0.3 / 0.4 | minore / moderato / significativo, regolabile | regolabile |

### Algoritmo

1. `process_faction_dynamics(simulation, tick)` gira ogni `EPOCHA_FACTION_DYNAMICS_INTERVAL` tick e orchestra la pipeline.
2. Per ciascun gruppo attivo: `update_group_cohesion` applica l'equazione (4.38); `update_group_leadership` ricalcola `compute_leadership_score` (4.39) e `compute_legitimacy` (4.40), sostituendo il leader su un deficit di legittimità; `_check_dissolution` rilascia i membri quando coesione o membership scende sotto la soglia di viabilità; `_check_schism` applica l'equazione (4.41) e genera uno splinter.
3. `_detect_and_propose_factions` raggruppa greedy gli agenti non affiliati per affinità a coppie e propone nuove fazioni; `_check_join_existing_groups` suggerisce adesioni; `_process_formation_decisions` realizza gli intenti di formazione degli agenti.
4. `_generate_faction_identity` richiede nome/obiettivo a un LLM con un fallback deterministico che non blocca mai la creazione della fazione.

### Semplificazioni

- **Pesi di leadership come scelte di design (F-1)**: la tupla (0.30/0.20/0.15/0.20/0.15) è coerente con la direzione degli effect size di Judge et al. (2002) (Estroversione la più forte, poi Coscienziosità, Apertura, Nevroticismo inverso) ma non è derivata dalle correlazioni meta-analitiche; Stogdill (1948) supporta il principio del tratto-correlato ma non ha proposto alcuna formula a somma pesata; il carisma è weberiano (Weber 1922, Antonakis et al. 2016), non un tratto di Stogdill.
- **Soglia penalità di taglia come scelta di design (F-2)**: il valore 5 è un parametro regolabile ancorato al principio generico di costo di coordinamento di piccolo gruppo (Hackman 2002), esplicitamente NON a Dunbar 1992 (limite cognitivo ~150) né allo strato "5" di cricca intima di Zhou et al. (2005).
- **Coefficienti di coesione come budget di calibrazione (F-3)**: i quattro coefficienti e il rapporto 1.5:1 conflitto-cooperazione sono regolabili; Baumeister et al. (2001) ancora solo la direzione qualitativa del bias di negatività, non le magnitudini.
- **Clustering greedy order-dependent (F-4)**: il rilevamento di scissione e cluster seeda dal primo agente nel queryset, rendendo la partizione dipendente dall'ordine; una risoluzione basata su componenti connesse / clustering gerarchico su grafo è rimandata a un futuro work item "robust faction clustering".
- **Beni di club non implementati**: il meccanismo di coesione a segnale costoso di Iannaccone (1992) è assente e rimandato.
- **Relazioni fazione-fazione non modellate**: le dinamiche inter-fazione di alleanza/rivalità sono fuori scope per il modulo attuale.
- **Generazione di identità LLM**: la generazione di nome/obiettivo via adapter LLM è coperta dall'audit llm-adapter separato; la creazione della fazione non è mai bloccata dall'indisponibilità dell'LLM.
- **Hardening comportamentale risolto (Round 3, 2026-07-15)**: i quattro finding rimandati all'audit Round 2 sono chiusi dal work item factions Round 3 hardening — il bias di campionamento dei membri (uno slice di queryset non ordinato, implementation-defined su PostgreSQL; la caratterizzazione originale "ordinamento per chiave primaria" era imprecisa) è sostituito dalla media di affinità su tutti i membri vivi con un contesto prefetched, le scritture multi-riga dei quattro percorsi di mutazione sono avvolte in blocchi `transaction.atomic` per-mutazione, la disciplina di scrittura della migrazione degli agenti è unificata su `update()` di queryset sotto una precondizione no-segnali verificata, e i pattern di query N+1 nei percorsi di suggerimento-adesione, rilevamento cluster, leadership ed elezione dei fondatori sono rimossi con regression test a budget di query fissato. Il tie-break sulla forza delle relazioni è ora deterministico (chiave secondaria id). L'elezione dei fondatori prima valutava i candidati contro il nuovo gruppo ancora vuoto (degenere: vinceva sempre il primo fondatore) e ora valuta l'effettiva membership fondativa.

### Stato

> Stato: implementato a partire dal commit `5406b95a74d3281bc98665923818d7e708745120`, audit del codice CONVERGENTE 2026-05-16 round 2.

---

## 4.8 Layer base dell'economia

> Stato: implementato a partire dal commit `7ec65484dea8a97236af2912b613d26ed428bb7c`, audit del codice CONVERGENTE 2026-07-16 round 12.

### Background

Il layer base dell'economia è il substrato che trasforma l'attività degli agenti in produzione, prezzi, moneta e flussi di reddito per tick; l'integrazione comportamentale di §4.2 (aspettative adattive, credito e banca, mercato immobiliare) consuma i prezzi, gli scambi e i redditi da fattori che questo layer produce. Il substrato è composto da cinque moduli. La produzione segue la famiglia a Elasticità di Sostituzione Costante di Arrow, Chenery, Minhas e Solow (1961), con l'estensione multi-fattore della pratica applicata di equilibrio economico generale computabile (Shoven e Whalley 1992). Il clearing di mercato è il tâtonnement Walrasiano (Walras 1874) sotto l'esplicito caveat di non-convergenza di Scarf (1960) per tre o più beni. La distribuzione del reddito implementa l'identità tripartita classica dei redditi da fattori di Ricardo (1817) — il prodotto di un periodo è ripartito tra terra (rendita), lavoro (salari) e capitale (profitto), mai pagato per intero a ciascun fattore indipendentemente — riformulata in termini moderni dall'approccio del reddito alla contabilità nazionale. Il modulo monetario porta l'equazione degli scambi di Fisher (1911) come diagnostica di conservazione, non come regola di prezzo, e l'accoppiamento con l'umore segue il plateau di sazietà del reddito di Kahneman e Deaton (2010). L'inizializzazione semina il bilancio per epoca dai template economici di §6.2. Il layer ha attraversato dodici round di audit avversariale (primo audit 2026-07-15, convergenza 2026-07-16) che hanno riscritto il nucleo di conservazione: l'implementazione pre-audit iniettava più del doppio del valore prodotto per tick come cassa nuova, fabbricava beni al settlement e lasciava l'aggregato monetario scollegato dalla cassa circolante.

### Modello

Ad ogni tick, ogni zona esegue un ciclo a nove step: aggiornamento delle aspettative (§4.2.1), produzione CES per agente, clearing tâtonnement del mercato zonale, lo step del credito (§4.2.2), la partizione conservativa dei redditi da fattori (rendita, salari, profitto), la tassazione piatta sul reddito verso il tesoro, il consumo essenziale, la passata massa monetaria/ricchezza/umore, e il ricalcolo dei depositi. La produzione converte gli input fattoriali specifici del ruolo di ciascun agente in una quantità di bene attraverso l'aggregatore CES con parametri per bene da template (scala `A`, elasticità di sostituzione `σ`, pesi fattoriali normalizzati `αᵢ`). Il mercato zonale raccoglie l'offerta (scorte sopra la riserva di sussistenza) e la domanda (gap di sussistenza, più una domanda discrezionale vincolata dal budget di cassa per i beni non essenziali), aggiusta i prezzi proporzionalmente all'eccesso relativo di domanda, e regola gli scambi con razionamento proporzionale sul lato corto e una guardia di affordability, beni essenziali per primi, in ordine deterministico. Il valore dell'output della zona `V` — la produzione valorizzata ai prezzi di equilibrio della zona stessa — è poi ripartito in redditi da fattori che sommano esattamente a `V` e accreditati come unica iniezione monetaria del tick; la tassazione e tutte le vendite sono puri trasferimenti. L'aggregato monetario `M` è ricalcolato ogni tick come cassa circolante degli agenti vivi, e l'identità di Fisher è valutata come diagnostica confrontando il reddito da fattori iniettato con il valore nominale dell'output.

### Equazioni

Equazione (4.42) funzione di produzione CES (Arrow et al. 1961), per agente e bene, con `ρ = (σ − 1)/σ`:

  Q = A · [Σᵢ αᵢ · Xᵢ^ρ]^(1/ρ)

valutata in forma logaritmica vicino alla singolarità Cobb-Douglas (`0.95 < σ < 1.05`, `Q = A · Πᵢ Xᵢ^αᵢ`) e col suo limite Leontief sotto `σ = 0.05` (`Q = A · min(Xᵢ)`: i pesi distributivi normalizzati svaniscono nel limite della media di potenza, quindi il limite è il minimo degli input, non `min(αᵢXᵢ)`); il piccolo seam numerico positivo alla soglia di branch è limitato sotto l'1% relativo e fissato da un regression test.

Equazione (4.43) aggiornamento di prezzo del tâtonnement (Walras 1874; Shoven e Whalley 1992), iterato fino a convergenza o al cap di iterazioni:

  P⁽ᵏ⁺¹⁾_g = P⁽ᵏ⁾_g · (1 + λ · (D_g − S_g) / max(S_g, ε))

con tasso di aggiustamento `λ = 0.03`, variazione per iterazione limitata a ±50%, un floor assoluto di `0.01` e un ceiling di `100 ×` il prezzo base del template che ancora la deriva cross-tick; il cap di iterazioni (100) è la rete di sicurezza esplicita per il regime di non-convergenza di Scarf (1960).

Equazione (4.44) partizione conservativa dei redditi da fattori (Ricardo 1817; approccio del reddito alla contabilità nazionale), per zona e tick:

  V_z = Σ_g q_zg · p_zg    e    V_z = R_z + W_z + Π_z

con quota di rendita `0.15` (allocata ai proprietari in proporzione al loro bonus di produzione), quota salari `0.6` (allocata ai produttori in proporzione al valore del loro stesso output), e profitto residuo `0.25` (ai proprietari che forniscono capitale, o trattenuto dai produttori per i beni senza claim di proprietà, assorbendo la quota di rendita non reclamata così che la partizione sommi a `V_z` bene per bene). I proprietari morti sono esclusi e la loro quota si rinormalizza ai claimant superstiti o ricade sui produttori.

Equazione (4.45) diagnostica di conservazione di Fisher (Fisher 1911), valutata ogni tick con warning sopra il 20% di divergenza:

  MV = Σ (reddito da fattori accreditato)    vs    PQ = Σ_z V_z ,    divergenza = |MV − PQ| / max(MV, PQ, 1)

dove la velocità passata al check è la velocità del reddito (reddito da fattori / M), così che l'identità non sia tautologica: la divergenza segnala reddito iniettato fuori proporzione rispetto al valore prodotto — la classe di difetti di conservazione che l'audit ha trovato e corretto — mentre la velocità di turnover misurata resta una metrica riportata sulla valuta.

### Parametri

| Parametro | Valore | Fonte | Stato |
|---|---|---|---|
| elasticità CES di default `σ` | 0.5 | default di template; forma Arrow et al. 1961 | tunable |
| scala CES di default `A` | 2.0 | calibrazione template (5.0 documentato come non fisico per mercati a 4 agenti) | tunable |
| baseline fattoriali CES (capitale, risorse naturali, conoscenza) | 0.5 | parametro di design | tunable |
| soglie di branch Leontief / Cobb-Douglas | 0.05 / 0.95–1.05 | guardie di stabilità numerica | tunable |
| tasso / iterazioni / convergenza tâtonnement | 0.03 / 100 / 0.01 | pratica CGE applicata (Shoven e Whalley 1992) | tunable |
| cap variazione per iterazione / floor / ceiling di prezzo | ±50% / 0.01 / 100× prezzo base | guardie di stabilità | tunable |
| quote salari / rendita / profitto | 0.6 / 0.15 / 0.25 (residuo) | identità di partizione Ricardo 1817; valori da budget di calibrazione | tunable |
| frazione di spesa discrezionale / cap per bene | 0.1 della cassa / 5 unità | euristica di domanda (Deaton e Muellbauer 1980 è il modello pieno che approssima) | tunable |
| fabbisogno di sussistenza per agente per tick | 1.0 | contratto condiviso con la demografia (§4.1) | tunable |
| sanity cap sui salari | 100 × salario mediano (floor 100) | guardia defense-in-depth; quando binding, iniezione < V by design | tunable |
| soglie di umore | 0.5 × / 1.5 × ricchezza mediana | convenzione OECD di povertà relativa; plateau di Kahneman e Deaton (2010) | tunable |
| soglia di warning Fisher | 20% di divergenza | sensibilità diagnostica | heuristic |
| indice di inflazione | media aritmetica non pesata (forma di Carli) | semplificazione dichiarata vs forme pesate/Jevons (CPI Manual 2004) | heuristic |

### Algoritmo

1. `process_economy_tick_new(simulation, tick)` (`epocha/apps/economy/engine.py`) orchestra i nove step; ogni ordine di iterazione che alimenta stato sensibile all'ordine è fissato (queryset ordinati per id, beni in ordine alfabetico, sort stabile degli scambi essenziali-prima, RNG derivato dal seed della simulazione e dal tick), così che run con seed identico riproducano stato bit-identico.
2. Per zona: `compute_agent_output` (equazione 4.42) aggiunge la produzione agli inventari e al ledger; `collect_supply_and_demand` + `tatonnement_prices` (4.43) fanno il clearing del mercato; `execute_trades` raziona proporzionalmente il lato corto con running totals e l'engine regola per primi i beni essenziali sotto una guardia di affordability sulla cassa del compratore.
3. `partition_output_value` (4.44) calcola rendita, salari e profitto che sommano a `V_z`; l'engine accredita i beneficiari risolti a livello di simulazione (inclusi i proprietari vivi fuori zona, esclusi i morti) e registra a ledger ciascun reddito da fattori; la tassazione addebita i percettori e accredita il tesoro con il totale corrente effettivamente riscosso, solo quando esiste un Government.
4. Lo step 8 ricalcola `M` dalla cassa circolante degli agenti vivi, valuta la diagnostica di Fisher (4.45), aggiorna la ricchezza e le soglie di umore relative alla mediana, e il layer bancario ricalcola i depositi (§4.2.2).

### Semplificazioni

- **Indice di inflazione di Carli**: l'inflazione è la media aritmetica non pesata dei rapporti di prezzo, con il bias verso l'alto documentato rispetto alle forme pesate per spesa o geometriche (Jevons) (CPI Manual 2004); la simulazione non porta dati di quote di spesa con cui pesare, quindi la forma è dichiarata invece che sostituita.
- **Aggregazione di prezzo cross-zona non pesata**: i prezzi di sistema per inflazione, valorizzazione della ricchezza e aspettative sono medie non pesate tra le zone che quotano un bene; una media pesata per attività è il raffinamento. Il lato PQ di Fisher deliberatamente NON usa questo aggregato — somma i valori nominali per-zona, così la diagnostica è esatta anche con dispersione di prezzo multi-zona.
- **Rendita proporzionale al bonus**: la rendita è proporzionale al bonus di produzione della proprietà anziché un surplus differenziale sulla terra marginale (la costruzione completa di Ricardo 1817); il comportamento qualitativo (la terra produttiva rende di più) è preservato.
- **Il reddito della terra pubblica o senza proprietario va ai produttori**: la proprietà non posseduta da un agente vivo è esclusa dalla partizione e la sua quota terra/capitale raggiunge gli agenti produttori attraverso il fallback no-landlord; instradarla al tesoro sarebbe una scelta di politica fiscale deliberata.
- **Iniezione ≤ V sotto il wage cap**: il sanity cap defense-in-depth sui salari può tagliare il totale accreditato strettamente sotto `V`; il residuo tagliato deliberatamente non viene ridistribuito (mai binding nei template calibrati).
- **Funzioni a gradino dell'umore**: la penalità di povertà è piatta (non scalata con la profondità) e il boost per tick raddoppia esattamente alla soglia di sazietà prima di decadere — una semplificazione a tratti dichiarata del plateau di Kahneman-Deaton.
- **Euristica di domanda**: la domanda discrezionale alloca una frazione fissa della cassa tra i beni non essenziali con pesi a elasticità inversa — un'euristica vincolata dal budget che approssima un sistema di domanda proprio (Deaton e Muellbauer 1980); gli agenti non domandano beni che stanno essi stessi offrendo (esclusione dei wash trade).
- **Mercato a valuta singola**: dimensionamento della domanda e settlement operano sulla sola valuta primaria; lo scambio multi-valuta non è modellato.
- **Scope di M**: la moneta misurata copre solo la cassa degli agenti vivi — il tesoro governativo, la cassa degli agenti morti e gli interessi del sistema bancario stanno fuori dalla circolazione by design, e l'emissione/rimborso di prestiti banking-type è inside money in stile Diamond-Dybvig dichiarata (§4.2.2).

### Stato

> Stato: implementato a partire dal commit `7ec65484dea8a97236af2912b613d26ed428bb7c`, audit del codice CONVERGENTE 2026-07-16 round 12. Attivo nella pipeline per tick (dispatched da `epocha/apps/simulation/engine.py` per le simulazioni con il data layer economico inizializzato).

---

# 5. Implementazione

Il Capitolo 5 documenta come l'architettura astratta del Capitolo 3 e i modelli auditati del Capitolo 4 vengano disposti su disco. L'intento è che un lettore che abbia interiorizzato i capitoli precedenti possa navigare il codebase senza dover prima fare reverse-engineering dell'albero delle directory, e che la mappatura tra ciascun modulo implementato e la sua spec di design sia esplicita anziché implicita. Il capitolo è deliberatamente compatto: punta alla fonte di verità invece di ri-narrare ciò che la fonte stessa già dichiara.

## 5.1 Struttura del repository

Il repository è organizzato in quattro directory di primo livello sotto la radice del progetto:

```
epocha/
├── config/                     Pacchetto del progetto Django (settings, ASGI, Celery, URL radice)
│   ├── settings/               Settings divisi: base, local, production
│   ├── asgi.py                 Entry point ASGI per HTTP e WebSocket
│   ├── celery.py               Dichiarazione dell'app Celery e autodiscovery dei task
│   └── urls.py                 Configurazione URL radice che monta i router per app
├── epocha/
│   ├── apps/                   App Django, una per sottosistema di simulazione
│   │   ├── agents/             Personalità Big Five, memoria, pipeline decisionale,
│   │   │                       reputazione, flusso informativo, fazioni, movimento,
│   │   │                       relazioni, grafo sociale
│   │   ├── chat/               Layer di conversazione WebSocket con gli agenti
│   │   ├── dashboard/          UI dell'operatore, panoramica della simulazione, rendering del grafo
│   │   ├── demography/         Mortalità, fertilità, formazione delle coppie,
│   │   │                       eredità, struttura per età
│   │   ├── economy/            Produzione, monetario, market clearing, credito,
│   │   │                       sistema bancario, aspettative, mercato immobiliare,
│   │   │                       distribuzione, feedback politico
│   │   ├── knowledge/          Grafo della conoscenza e archivio strutturato dei fatti
│   │   ├── llm_adapter/        Astrazione dei provider, rotazione delle chiavi, rate limiter,
│   │   │                       contabilità per chiamata (`LLMRequest`)
│   │   ├── simulation/         Tick engine, loop Celery, ciclo di vita della simulazione,
│   │   │                       gestione di seed e RNG
│   │   ├── users/              Autenticazione e account operatore (boilerplate)
│   │   └── world/              Geografia, zone, governo, istituzioni,
│   │                            stratificazione, parsing documenti, generatori
│   └── common/                 Utility condivise: paginazione, permessi,
│                                eccezioni, mixin, helper generici
├── compose/                    Dockerfile ed entrypoint per local e prod
├── requirements/               Set di dipendenze pinnate: base, local, production
└── docs/                       Spec, plan, backup di memoria, whitepaper
```

La separazione tra `config/` ed `epocha/` segue la convenzione django-cookiecutter: `config/` porta il wiring di livello progetto indipendente dal dominio, mentre `epocha/` porta il dominio stesso. Le app sotto `epocha/apps/` sono intenzionalmente strette: ciascuna possiede un insieme chiuso di responsabilità ed espone la propria superficie pubblica attraverso `models.py`, `serializers.py`, `views.py`, `urls.py` e un insieme per dominio di moduli di servizio i cui nomi rispecchiano i confini dei modelli di §4 (`mortality.py`, `fertility.py`, `couple.py`, `expectations.py`, `credit.py`, `property_market.py` e così via). La comunicazione tra app passa attraverso le foreign key dei modelli e attraverso l'orchestratore per tick in `simulation/`, mai tramite import ad-hoc tra moduli di dominio; questa è la regola strutturale che mantiene aciclico il grafo delle dipendenze e che rende trattabile il testing per app.

## 5.2 Mappatura moduli-spec

La Tabella 5.1 registra la spec di design o le spec che governano ciascuna app Django sotto `epocha/apps/`. Le spec sono memorizzate sotto `docs/superpowers/specs/` in forma kebab-case con prefisso di data; più spec contro la stessa app riflettono la storia di design a fasi di quel sottosistema (una spec di design iniziale seguita da revisioni comportamentali o di integrazione). Le app contrassegnate "n/d — boilerplate" non portano logica di dominio propria oltre i default di Django e quindi non hanno alcuna spec di design associata.

Tabella 5.1 — Mappatura da `epocha/apps/<app>` alla spec di design che la governa.

| App | Spec di design sotto `docs/superpowers/specs/` |
|---|---|
| `agents` | `2026-04-05-information-flow-design.md` (flusso informativo), `2026-04-05-factions-leadership-design.md` (fazioni e leadership), `2026-04-06-reputation-model-design.md` (reputazione), `2026-04-06-social-graph-design.md` (relazioni e grafo sociale), `2026-04-07-movement-system-design.md` (movimento) |
| `chat` | `2026-03-30-integrated-dashboard-chat-design.md` |
| `dashboard` | `2026-03-30-integrated-dashboard-chat-design.md`, `2026-04-06-analytics-psicostoriografia-design.md` |
| `demography` | `2026-04-18-demography-design.md` |
| `economy` | `2026-04-12-economy-base-design.md`, `2026-04-13-economy-behavioral-design.md`, `2026-04-15-economy-behavioral-integration-design.md` |
| `knowledge` | `2026-04-11-knowledge-graph-design.md` |
| `llm_adapter` | `2026-03-22-epocha-design.md` (spec master, §3.5) |
| `simulation` | `2026-03-22-epocha-design.md` (spec master, §3.1, §3.4) |
| `users` | n/d — boilerplate |
| `world` | `2026-04-05-government-institutions-stratification-design.md` (governo, istituzioni, stratificazione), `2026-04-06-postgis-geodjango-design.md` (substrato geografico) |

La spec master `2026-03-22-epocha-design.md` copre le preoccupazioni trasversali (tick engine, strategia RNG, contratto dell'adapter LLM, convenzioni di persistenza) che non sono di proprietà di nessuna singola app di dominio e a cui ogni altra spec fa riferimento. La companion italiana `2026-04-18-demography-design-it.md` affianca il design demografico come artefatto leggibile usato durante il gate di approvazione della spec; per la policy bilingue del CLAUDE.md master, è la versione singola autoritativa per quel sottosistema.

## 5.3 Adapter di provider LLM e rate limiting

Il puntatore di implementazione per l'adapter descritto in §3.5 è `epocha/apps/llm_adapter/providers/`, con `base.py` che definisce l'interfaccia astratta `BaseLLMProvider` e `openai.py` che fornisce l'implementazione concreta OpenAI-compatible che mira a ogni endpoint supportato (OpenAI vero e proprio, Groq, Google Gemini, OpenRouter, Together AI, Mistral, LM Studio, Ollama). Cambiare provider è una modifica di settings piuttosto che di codice: `EPOCHA_LLM_BASE_URL`, `EPOCHA_LLM_MODEL` ed `EPOCHA_LLM_API_KEY` in `config/settings/base.py` selezionano l'endpoint, e la stessa terna ha un parallelo `EPOCHA_CHAT_LLM_*` per il provider lato chat che `get_chat_llm_client()` avvolge in un `FallbackProvider`. Le esecuzioni locali con LM Studio sono configurate esattamente come gli endpoint remoti: il `base_url` punta a `http://localhost:1234/v1` (l'URL di default del server LM Studio), `EPOCHA_LLM_API_KEY` viene lasciato non impostato o impostato a un placeholder, e l'identificatore del modello corrisponde al modello caricato nell'UI di LM Studio. Il pattern di rotazione delle chiavi Groq che fa da paracadute al free tier è implementato dentro `OpenAIProvider`: `EPOCHA_LLM_API_KEY` accetta una lista di chiavi separate da virgola, e su `RateLimitError` il provider ruota alla chiave successiva dopo aver esaurito il budget di retry intra-chiamata. Il limiter sliding-window backed da Redis a livello di processo in `epocha/apps/llm_adapter/rate_limiter.py` è la seconda linea di difesa ed è invocato dal codice di orchestrazione che ha bisogno di throttle-are prima del limite del provider stesso. La contabilità per chiamata scrive nel modello `LLMRequest` in modo che l'uso di token e il costo in USD siano osservabili per simulazione nella dashboard.

## 5.4 Dettagli del modello di persistenza

PostgreSQL è lo store canonico, con PostGIS già abilitato a livello Django: `django.contrib.gis` è in `INSTALLED_APPS` (`config/settings/base.py:33`) e l'app `world` memorizza le geometrie delle zone come `PolygonField`/`PointField` WGS84 a partire dalla migrazione `world.0003_zone_postgis_geometry`. La chiave primaria di default è l'auto-increment intero a 64 bit di Django (`DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"`); nessuna colonna UUID è usata al commit pinnato, e le foreign key in tutte le app portano dunque riferimenti interi. Le transazioni atomiche per richiesta sono abilitate (`ATOMIC_REQUESTS = True`) in modo che gli handler di API e di tick eseguano dentro una transazione di default.

La disciplina delle migrazioni segue la regola di progetto secondo cui nessuna migrazione viene applicata a `develop` senza che la modifica di modello corrispondente sia mergiata nello stesso commit; le migrazioni sotto `epocha/apps/<app>/migrations/` sono lineari e mai squashate tra release, sul presupposto che la simulazione stessa sia la fonte di verità e che il rollback di una migrazione debba restare un'operazione a livello git. Due convenzioni del modello di persistenza, entrambe formalizzate durante l'audit del Plan 1 di demografia, meritano menzione esplicita perché attraversano più app. Primo, ogni saldo monetario è memorizzato come `JSONField` con chiave codice valuta in stile ISO-4217 piuttosto che come singolo `DecimalField`: `AgentInventory.cash` (`epocha/apps/economy/models.py:208`) e i campi di tesoreria analoghi sulle entità di governo e bancarie portano tutti dizionari per valuta in modo che i saldi multi-valuta e le analitiche per valuta siano preservati senza migrazioni di schema quando una nuova valuta viene introdotta da un template sci-fi o moderno. Secondo, la colonna `Agent.birth_tick` su `agents.Agent` è un `BigIntegerField` piuttosto che un `PositiveIntegerField` (`epocha/apps/agents/models.py:88`); il tipo signed è richiesto perché gli agenti pre-esistenti la cui età precede l'inizio della simulazione portano un birth tick negativo, e la formula canonica dell'età `age = (current_tick − birth_tick) / ticks_per_year` perderebbe altrimenti validità al confine della popolazione fondatrice. La traccia di migrazioni in `agents.0009_agent_birth_tick_*` e `agents.0010_alter_agent_birth_tick_*` registra l'introduzione del campo e la sua successiva ritipizzazione durante il loop di convergenza del Plan 1.

---

# 6. Calibrazione

Il Capitolo 6 documenta la superficie di calibrazione dei moduli auditati e la macchineria dei template per epoca che porta i valori di parametro per epoca nella simulazione. Mentre il Capitolo 4 narra ciascun modello e presenta la sua tabella di parametri inline accanto alle equazioni che parametrizza, il Capitolo 6 prende la vista complementare: consolida i puntatori di calibrazione in un unico posto, descrive le due convenzioni di schema distinte usate per i template di demografia ed economia, e registra quali fit sono implementati oggi e quali sono rimandati al Plan 4.

## 6.1 Tabelle di parametri per modulo auditato

Le tabelle di parametri per modulo sono presentate inline nel Capitolo 4 accanto alle equazioni che governano, secondo il principio che un parametro è più leggibile quando sta accanto al suo modello piuttosto che in un'appendice di fine libro. La Tabella 6.1 sottostante è quindi un indice, non un duplicato.

Tabella 6.1 — Indice delle tabelle di parametri inline per modulo auditato.

| Modulo auditato | Tabelle inline nel Capitolo 4 |
|---|---|
| Mortalità (Heligman-Pollard) | Tabelle 4.1 (semantica e range ammissibili dei parametri HP) e 4.2 (valori HP per epoca tra i cinque template del Plan 1) |
| Fertilità (Hadwiger ASFR + modulazione Becker) | Tabelle 4.3 (valori Hadwiger per epoca) e 4.4 (coefficienti di modulazione Becker, attualmente omogenei tra tutti e cinque i template per debito B2-07) |
| Formazione delle coppie (Gale-Shapley + Goode 1963) | Tabelle 4.5 (parametri di formazione coppie per epoca) e 4.6 (pesi di omogamia per epoca per l'equazione (4.6)) |
| Aspettative adattive (Cagan 1956) | Tabella 4.7 (parametri seedati da `_behavioral_config()`, identici tra tutti e quattro i template di economia in attesa della calibrazione del Plan 4) |
| Credito e sistema bancario (Diamond-Dybvig + riserva frazionaria) | Tabelle 4.8 (parametri di credito e sistema bancario per epoca) e 4.9 (parametri uniformi tra tutti e quattro i template in attesa del Plan 4) |
| Layer base dell'economia (produzione CES, tâtonnement, partizione dei redditi da fattori, diagnostica di Fisher) | Tabella di parametri inline in §4.8 (default e soglie di branch CES, tasso/cap del tâtonnement, quote salari/rendita/profitto, euristica di domanda, wage sanity cap, soglie di umore, soglie diagnostiche) |
| Mercato immobiliare | Nessuna tabella autonoma — i parametri ereditano dalla configurazione del credito di §4.2.2 (loan-to-value, tasso di interesse base come tasso di sconto `r`) e dalla configurazione delle aspettative di §4.2.1 (la `trend_threshold = 0.05` per la classificazione del prezzo richiesto). Due parametri di design specifici del mercato immobiliare sono codificati al di fuori dei template e documentati inline in §4.2.3: la finestra di scadenza degli annunci di `10` tick (`property_market.py:235`) e la banda di guardia della valutazione Gordon che pavimenta il denominatore a `0.01` e clippa la valutazione risultante a `[0.1 · property.value, 10 · property.value]` (`property_market.py:121-128`). |

Il template `sci_fi.json` è documentato nel suo file sorgente come speculativo e non porta alcun target di calibrazione empirico per nessuno dei moduli auditati.

## 6.2 Template per epoca ed euristiche regolabili

La simulazione supporta due sistemi di template paralleli che hanno avuto origine da decisioni di design indipendenti nelle spec di demografia ed economia. La discrepanza in forma e numero è un effetto collaterale deliberato della storia di design a fasi piuttosto che un intento strutturale, ed è registrata esplicitamente qui perché i due sistemi convergeranno alla fine durante il Plan 4.

I template di demografia sono cinque file JSON sotto `epocha/apps/demography/templates/`: `pre_industrial_christian.json`, `pre_industrial_islamic.json`, `industrial.json`, `modern_democracy.json` e `sci_fi.json`. Ciascun file porta un dizionario piatto con tre chiavi di primo livello (`mortality`, `fertility`, `couple`), ognuna che contiene i valori di parametro consumati dal modello corrispondente di §4.1. La coppia pre-industriale è una scissione deliberata: i due file condividono blocchi di mortalità e fertilità identici (perché il record storico empirico non giustifica una differenziazione per confessione negli schedule biologici sottostanti) e differiscono solo nel blocco `couple`, dove `pre_industrial_islamic.json` porta `marriage_market_type: arranged` contro il regime autonomo di tutti gli altri template e `pre_industrial_christian.json` porta `divorce_enabled: false` per modellare il regime canonico cattolico di indissolubilità del matrimonio. Lo schema JSON è intenzionalmente stretto: ogni chiave è consumata da un modello specifico in §4.1, nessun campo di estensione non tipizzato è accettato, e una chiave sconosciuta in fase di caricamento solleva un errore di validazione anziché essere silenziosamente ignorata.

I template di economia sono quattro funzioni factory Python in `epocha/apps/economy/template_loader.py`: `_pre_industrial_template()`, `_industrial_template()`, `_modern_template()` e `_sci_fi_template()`. Ciascuna funzione restituisce un dizionario annidato che il loader passa a `EconomyTemplate.objects.get_or_create()`, e la differenziazione per epoca è realizzata variando un piccolo insieme di input (tabella valute, elasticità dei beni, stock dei fattori, configurazione comportamentale) piuttosto che mantenendo quattro file JSON indipendenti. Il blocco comportamentale in particolare è costruito una sola volta da `_behavioral_config()` (`template_loader.py:144-198`) ed è identico tra tutti e quattro i template al commit pinnato, sul presupposto che le evidenze di calibrazione auditate del Plan 2 non motivassero una differenziazione per epoca al momento della spec. La differenziazione per epoca di `λ_base`, dei coefficienti di modulazione Becker, di `risk_premium`, `max_rollover` e `default_loan_duration_ticks` è il debito di calibrazione esplicito assegnato al Plan 4. I due sistemi usano numeri diversi (cinque per demografia, quattro per economia) perché la spec di demografia richiedeva di separare i due regimi confessionali pre-industriali per supportare la distinzione di mercato matrimoniale e regime di divorzio, mentre la spec di economia non ha trovato alcuna distinzione strutturale analoga al livello prezzo-e-credito che giustificasse un quinto template.

Oltre ai valori di parametro per template, i moduli auditati portano un piccolo numero di costanti strutturali che sono codificate nel sorgente piuttosto che nei template perché sono proprietà del modello piuttosto che scelte di calibrazione. I limiti delle aspettative `_LAMBDA_MIN = 0.05` e `_LAMBDA_MAX = 0.95` (`expectations.py:39-40`) prevengono previsioni degeneri e sono documentati in §4.2.1; il `CASCADE_LOSS_THRESHOLD = 0.5` del passaggio di contagio Allen-Gale e la corrispondente finestra di scadenza degli annunci di `10` tick sono documentati rispettivamente in §4.2.2 e §4.2.3. Queste sono euristiche regolabili nel senso che ammettono revisione sotto evidenze di calibrazione future, ma non sono campi di template e la differenziazione per epoca non è un deliverable del Plan 4 per esse.

## 6.3 Procedure di fit

Il modulo di mortalità include un helper di fit funzionante, `fit_heligman_pollard()` in `epocha/apps/demography/mortality.py:103-158`, che avvolge `scipy.optimize.curve_fit` contro la forma funzionale HP a otto parametri. La funzione prende una lista di età e le corrispondenti probabilità annue di mortalità osservate `q(x)` e restituisce un dizionario con chiave i nomi degli otto parametri HP (`A`-`H`). Le condizioni iniziali di default sono l'array `p0 = [0.005, 0.02, 0.1, 0.001, 10.0, 22.0, 0.00005, 1.1]` riportato nel sorgente, e i bound dei parametri sono imposti tramite l'argomento `bounds=(lower, upper)` con `lower = [0.0, 0.0, 0.0, 0.0, 0.1, 1.0, 0.0, 1.0]` e `upper = [0.1, 0.5, 1.0, 0.05, 50.0, 50.0, 0.001, 1.5]`. I bound corrispondono ai range ammissibili riportati inline nella Tabella 4.1 e sono gli stessi bound che validano i valori per epoca contenuti nei cinque template del Plan 1. Una guard di input degenere rifiuta gli schedule di mortalità che siano uniformemente nulli prima di passarli all'ottimizzatore, in modo che la funzione fallisca rapidamente con un `RuntimeError` descrittivo piuttosto che lasciare che `curve_fit` minimizzi silenziosamente verso un confine dello spazio dei parametri. I bound stessi sono oggetto del debito di audit B-5 della spec di demografia: i valori attuali sono coerenti con la letteratura attuariale sul modello HP (Heligman e Pollard 1980; Tabeau, van den Berg Jeths e Heathcote 2001) ma la catena di giustificazione per ciascun bound è riservata alla calibrazione del Plan 4, insieme al primo fit end-to-end dell'helper contro una vera life table dello Human Mortality Database.

Il modulo di fertilità non include ancora un helper di fit corrispondente per la Hadwiger ASFR. L'implementazione attuale in `epocha/apps/demography/fertility.py` valuta solo la formula canonica all'età dell'agente contro i valori `H`, `R` e `T` per epoca caricati dai template JSON: una `fit_hadwiger()` che invertirebbe la formula contro un profilo ASFR osservato è registrata come deliverable del Plan 4. La ragione dell'asimmetria è che lo scope di fertilità del Plan 1 si limitava esplicitamente al passaggio di valutazione per tick e alla modulazione Becker che lo avvolge; il loop di calibrazione che consumerebbe profili ASFR storici (record parrocchiali dell'Inghilterra pre-industriale via Wrigley e Schofield (1981); serie ASFR moderne via Eurostat o HMD) è il deliverable centrale del Plan 4 e rispecchierà la struttura di `fit_heligman_pollard()` una volta implementato. I coefficienti di modulazione Becker della Tabella 4.4 ugualmente non sono attualmente fittati: sono seedati con gli stessi cinque valori in tutti e cinque i template e la calibrazione per epoca è il deliverable centrale del debito B2-07 nel Plan 4. I parametri di credito, sistema bancario e mercato immobiliare delle Tabelle 4.8-4.9 sono calibrati qualitativamente contro Homer e Sylla (2005) per i range di tasso di interesse per epoca e contro la convenzione di Basel III per il rapporto di riserva moderno, ma nessuna procedura di fit automatica è implementata per essi: la differenziazione per epoca dei parametri uniformi della Tabella 4.9 e dei valori base del mercato immobiliare è riservata al Plan 4 insieme ai fit di demografia.

---

# 7. Metodologia di validazione

> Stato: esperimenti di validazione specificati, non ancora eseguiti. L'esecuzione è tracciata come follow-up separato (vedere la memoria di progetto `project_validation_experiments_pending.md`).

Il Capitolo 7 espone la metodologia di validazione per i moduli auditati del Capitolo 4. Il capitolo descrive quali target empirici o quasi-empirici ciascun modello deve riprodurre, le metriche con cui viene eseguito il confronto, le soglie di accettazione che decidono se un set di parametri candidato passa, e i comandi tramite i quali la suite di validazione sarà riproducibile da un checkout pulito. Il capitolo è metodologico piuttosto che evidenziale: la campagna sperimentale che consuma la metodologia è il deliverable centrale del Plan 4 ed è esplicitamente fuori dallo scope della presente revisione del whitepaper.

## 7.1 Dataset di riferimento per modulo auditato

I cinque modelli auditati del Capitolo 4 sono validati contro i dataset della Tabella 7.1. Ciascun dataset è abbinato a una citazione già catalogata in §13 (o aggiunta a §13 dalla presente revisione nel caso di Mokyr 1985) e con lo scope del confronto che il dataset abilita. La campagna di calibrazione del Plan 4 procurerà le serie di dati effettive dai repository citati e le porrà sotto una futura directory `data/` il cui percorso non è ancora fissato.

Tabella 7.1 — Dataset di riferimento per i moduli auditati.

| Modulo | Dataset | Citazione in §13 | Fonte / DOI | Scope |
|---|---|---|---|---|
| Mortalità (fit Heligman-Pollard) | Life table Inghilterra e Galles 1851-1900; life table Svezia 1751-1900 | Human Mortality Database (HMD) (2024) | https://www.mortality.org | Inversione degli otto parametri HP dalle colonne `q(x)` osservate; calibrazione per epoca dei blocchi di mortalità di `pre_industrial_*` e `industrial.json` di §6.2 |
| Fertilità (fit Hadwiger ASFR) | Profili ASFR ricostruiti da record parrocchiali per l'Inghilterra pre-industriale | Wrigley e Schofield (1981) | ISBN 978-0-521-35688-6 | Inversione di `H`, `R`, `T` contro un ASFR osservato; calibrazione per epoca della Tabella 4.3 |
| Mortalità di crisi (benchmark di morti in eccesso) | Serie di decessi a livello di contea della Carestia Irlandese 1845-1851 | Mokyr (1985) | ISBN 978-0-04-941011-7 | Riproduzione dell'ordine di grandezza di uno shock di mortalità in eccesso come benchmark per la componente "external_cause" Heligman-Pollard innescata da eventi di carestia, guerra o epidemia |
| Formazione delle coppie (European marriage pattern) | Singulate Mean Age at Marriage (SMAM) e serie della frazione mai-sposata per l'Europa Occidentale early-modern | Hajnal (1965) | https://doi.org/10.4324/9781315127019 | Validazione dell'implementazione Gale-Shapley + Goode 1963 di §4.1.3 contro la firma empirica del marriage pattern |
| Economia (layer base, §4.8) | Nessuno al commit pinnato | n/d | n/d | Calibrazione rimandata al Plan 4: i target candidati sono le stime di lungo periodo dell'elasticità CES per la funzione di produzione, serie storiche di dispersione dei prezzi per il regime di tâtonnement, e le serie di quote fattoriali della contabilità nazionale (lavoro ~0.55-0.65 nelle economie moderne) contro i default di partizione 0.6/0.15/0.25 |
| Economia (integrazione comportamentale) | Nessuno al commit pinnato | n/d | n/d | Calibrazione rimandata al Plan 4: profili λ di Cagan (1956) saranno cercati contro episodi inflazionari post-WWII; soglie di bank run di Diamond-Dybvig (1983) saranno cercate contro i cataloghi di crisi bancarie di Reinhart e Rogoff (2009); il confronto Gordon-Shiller del mercato immobiliare sarà cercato contro la serie di lungo periodo dei prezzi delle case di Shiller |

## 7.2 Metriche di confronto

Tre metriche sono usate congiuntamente tra i moduli auditati, con la scelta di quale applicare per esperimento guidata dalla forma del dataset di riferimento.

L'errore quadratico medio (RMSE) sui tassi per età è la metrica primaria per i fit di mortalità e fertilità, calcolata contro lo schedule osservato sulla stessa griglia di età: `RMSE = sqrt(mean((q_fit(x) − q_obs(x))^2))` per la mortalità e l'espressione analoga su `f(x)` per la fertilità. L'RMSE sui tassi è preferito all'RMSE su quantità cumulative perché la struttura per età di entrambi gli schedule è ciò che porta l'informazione demografica; un fit che corrisponde alla quantità cumulativa ma distorce la struttura per età non è un buon fit. Il test Kolmogorov-Smirnov (KS) a due campioni sulle distribuzioni di età al matrimonio e di età al primo parto è la metrica primaria per gli esperimenti di formazione coppie, sul presupposto che la firma di Hajnal (1965) sia una claim distributiva piuttosto che basata sui momenti. La log-likelihood dello schedule osservato sotto i parametri fittati è la diagnostica primaria per la decisione di goodness-of-fit quando il fit è eseguito tramite massima verosimiglianza piuttosto che tramite minimi quadrati; per il path `scipy.optimize.curve_fit` di `fit_heligman_pollard()` la log-likelihood è calcolata post hoc come check secondario.

## 7.3 Soglie di accettazione

Le soglie di accettazione per modulo della Tabella 7.2 sono conservative: codificano "il fit cattura la firma qualitativamente ed entro un ordine di grandezza che la letteratura demografica tratta come lo stesso regime", non "il fit è statisticamente indistinguibile dal target". Quest'ultima richiederebbe assunzioni di sample size che le popolazioni seed sintetiche per epoca dell'ordine di `10^4` agenti non supportano.

Tabella 7.2 — Soglie di accettazione per modulo auditato.

| Modulo | Soglia | Razionale |
|---|---|---|
| Mortalità (fit HP) | RMSE su `q(x)` annua per classe di età single-year strettamente minore di `0.005`, e la curva fittata riproduce qualitativamente i tre regimi HP (declino early-life, accident hump, salita senescente) piuttosto che collassare a una monotona Gompertz | La soglia corrisponde all'ordine di grandezza dei residui riportati in Heligman e Pollard (1980) per i loro fit australiani originali |
| Fertilità (fit Hadwiger) | Total Fertility Rate `TFR ∈ [4.5, 6.5]` per l'epoca pre-industriale dopo il fit di `H`, `R`, `T` contro il profilo ASFR di Wrigley-Schofield | L'intervallo racchiude il range TFR storicamente attestato per l'Inghilterra early-modern (Wrigley e Schofield 1981) |
| Mortalità di crisi (analogo Carestia Irlandese) | Mortalità in eccesso coerente con circa il `12%` cumulativo su cinque anni quando la simulazione è forzata con uno shock di carestia di magnitudine comparabile | La cifra del `12%` è l'ordine di grandezza della perdita di popolazione riportata da Mokyr (1985) per la Carestia Irlandese del 1846-1851 combinando morti in eccesso ed emigrazione forzata |
| Formazione delle coppie (European marriage pattern) | Singulate Mean Age at Marriage `SMAM ∈ [25, 28]` anni e frazione mai-sposata all'età 50 in `[10%, 20%]` dopo l'esecuzione del builder di popolazione fondatrice e l'invecchiamento della coorte | I due intervalli sono la firma canonica dell'European Marriage Pattern riportata in Hajnal (1965) |
| Economia (layer base, §4.8) | Criteri di accettazione rimandati al Plan 4 insieme alla selezione dei dataset di §7.1; gli invarianti auditati (iniezione di reddito da fattori uguale a V, conservazione dei beni, simmetria di trasferimento della tassa, determinismo seedato) sono presidiati dalla suite di regressione anziché da soglie empiriche | Nessun dataset target empirico è stato specificato al momento della scrittura |
| Economia (integrazione comportamentale) | Criteri di accettazione rimandati al Plan 4 insieme alla selezione dei dataset di §7.1 | Nessun dataset target empirico è stato specificato al momento della scrittura |

Un fit che fallisce la sua soglia non invalida il modello; innesca un loop di debug che esamina prima i valori seed del template per epoca, poi i bound dell'helper di fit, e solo infine la formulazione del modello stessa. L'ordine è quello standard per qualsiasi loop di calibrazione: il modo di fallimento più probabile è un template mal-seedato, il successivo è un bound troppo stretto o troppo largo, e il meno probabile è un difetto strutturale del modello che ha già passato l'audit scientifico avversariale alla fase di spec.

## 7.4 Comandi di riproducibilità

La suite di unit test che esercita i moduli auditati a livello di algoritmo è oggi riproducibile tramite le invocazioni standard di pytest dichiarate nel quickstart del progetto:

```bash
pytest --cov=epocha -v                                  # suite completa
pytest epocha/apps/demography/ -v                       # solo demografia
pytest epocha/apps/economy/ -v                          # solo economia
pytest epocha/apps/demography/tests/test_mortality.py   # un singolo modulo
```

La suite di validazione vera e propria — la campagna che consuma i dataset di §7.1, esegue le metriche di §7.2 e decide contro le soglie di §7.3 — non è ancora implementata. Il Plan 4 introdurrà una directory `validation/` alla radice del repository con uno script Python per modulo auditato (`validation/validate_mortality.py`, `validation/validate_fertility.py`, `validation/validate_couple.py` e così via); ciascuno script caricherà il proprio dataset, eseguirà il fit o farà avanzare la simulazione, calcolerà le metriche e produrrà un report pass/fail contro la soglia. Gli script saranno invocabili individualmente per il debug e collettivamente tramite un target Makefile in modo che la campagna completa di validazione si riduca a un singolo comando su un checkout pulito. I nomi esatti degli script e il target Makefile sono rimandati alla fase di design del Plan 4 e non sono impegnati nel presente capitolo.

## 7.5 Stato

Gli esperimenti di validazione sono specificati, non ancora eseguiti. L'esecuzione completa della campagna descritta in questo capitolo — acquisizione dei dataset, implementazione degli script, calcolo delle metriche e valutazione delle soglie — è tracciata come follow-up sotto la nota di memoria `project_validation_experiments_pending.md` ed è il deliverable centrale del Plan 4.

---

# 8. Sottosistemi progettati (implementati, audit pendente)

Il Capitolo 8 copre l'unico cluster Epocha rimanente che è implementato nel codice ed esercitato da unit test ma non ha ancora completato l'audit scientifico avversariale che funge da gate alla promozione allo stato di Capitolo 4. L'audit batch del 2026-04-12 (`docs/scientific-audit-2026-04-12.md`) ha aperto una lista di finding INCORRECT, UNJUSTIFIED, INCONSISTENT e MISSING contro otto dei moduli sottostanti; la reputazione è convergente sul round 2 (2026-05-12) ed è stata promossa al §4.3, il cluster di propagazione del passaparola (information flow, distortion, belief filter, più affinity per la fix IF-1 dell'audit) è convergente sul round 2 (2026-05-16) ed è stato promosso al §4.4, il cluster delle istituzioni politiche (government, government_types, institutions, stratification, election) è convergente sul round 2 (2026-05-16) ed è stato promosso al §4.5, e il movimento è convergente sul round 2 (2026-05-16) ed è stato promosso al §4.6, le fazioni sono convergenti sul round 2 (2026-05-16) e promosse al §4.7, e il layer base dell'economia — che NON era in quel batch — è convergente sul round 12 del suo primo audit (2026-07-16) ed è stato promosso al §4.8, lasciando il Knowledge Graph come unico modulo in questo capitolo in attesa. Il suo audit è tracciato come l'item di priorità più alta della roadmap del Capitolo 9. La sottosezione quindi riformula lo scope del cluster, i puntatori di letteratura portati dalla spec e dai docstring del modulo, e il code path, poi chiude con una riga di stato che nomina la spec sotto la quale l'audit riprenderà. I puntatori di letteratura in questo capitolo sono attribuzioni registrate dalla spec o dal sorgente piuttosto che citazioni Methods-grade verificate da fonte primaria del tipo del Capitolo 4.

## 8.1 Grafo della conoscenza

Il cluster del Grafo della Conoscenza implementa la memoria di lungo orizzonte della simulazione: il grafo per simulazione di entità, relazioni ed eventi che il context builder LLM di §3.5 interroga per ancorare la decisione per tick di ciascun agente nella storia precedente della simulazione piuttosto che ri-leggere l'intero log eventi raw. Il cluster è suddiviso in nove moduli sotto `epocha/apps/knowledge/`: `chunking.py` affetta il log eventi raw in passaggi dimensionati per LLM, `extraction.py` esegue l'estrattore di entità e relazioni guidato da LLM su ciascun chunk, `embedding.py` produce le rappresentazioni vettoriali dense di ogni chunk e di ogni nodo (il modello multilingual-e5-large è il default attuale per spec), `merge.py` deduplica i nodi estratti contro il grafo esistente, `normalizer.py` canonicalizza le forme superficiali delle entità alle loro etichette preferite, `materialization.py` riscrive il grafo consolidato sul layer di persistenza, `ontology.py` dichiara il sistema di tipi di entità e relazione, `prompts.py` raccoglie i prompt LLM per estrazione e merge, e `api.py` espone il grafo alla vista grafo della dashboard. I puntatori di letteratura nella spec sono il framework Retrieval-Augmented Generation di Lewis et al. (2020) per l'architettura più ampia retrieve-then-generate, la famiglia di sentence-embedding di Reimers e Gurevych (2019) per le rappresentazioni dense (multilingual-e5-large è la scelta di produzione attuale per la sua copertura di 100+ lingue e per le proprietà di riproducibilità), e la più ampia letteratura di ragionamento su grafi di conoscenza per la tipologia entità-relazione. La spec contrasta l'approccio Epocha con GraphRAG e con MiroFish nella sua sezione FAQ e registra la scelta di materializzare il grafo per simulazione piuttosto che attraverso simulazioni come una scelta di scope deliberata per l'MVP. Code path: `epocha/apps/knowledge/{ingestion,extraction,embedding,merge,normalizer,materialization,ontology,chunking,prompts,api}.py`.

> Stato: implementato nel codice, audit Round 2 pendente. Vedere `docs/superpowers/specs/2026-04-11-knowledge-graph-design.md`.

---

# 9. Roadmap

La roadmap è ordinata per priorità piuttosto che per cronologia: l'audit sull'unico modulo ancora pendente in §8 (la reputazione è convergente sul round 2 nel 2026-05-12 ed è stata promossa al §4.3; il cluster di propagazione del passaparola — information flow, distortion, belief filter, più affinity — è convergente sul round 2 nel 2026-05-16 ed è stato promosso al §4.4; il cluster delle istituzioni politiche è convergente sul round 2 nel 2026-05-16 ed è stato promosso al §4.5; il movimento è convergente sul round 2 nel 2026-05-16 ed è stato promosso al §4.6; le fazioni sono convergenti sul round 2 nel 2026-05-16 e promosse al §4.7; il layer base dell'economia è convergente sul round 12 del suo primo audit nel 2026-07-16 ed è stato promosso al §4.8) è l'item gating perché ogni successivo sforzo di calibrazione e validazione dipende dal sottoinsieme auditato che venga chiuso prima. Gli item rimanenti sono elencati in un ordine grossolano di sforzo atteso e sono tracciati nel backup di memoria di lungo formato sotto `docs/memory-backup/`; i cross-reference alla nota di memoria rilevante sono inline dove esistono.

- **PRIORITÀ ALTA — audit avversariale del Knowledge Graph.** Il Knowledge Graph è l'unico modulo rimasto in §8 pendente del suo primo passaggio di audit scientifico. Sei cluster sono già convergenti e promossi: la reputazione sul round 2 (2026-05-12) al §4.3, il cluster di propagazione del passaparola (information flow, distortion, belief filter, più affinity) sul round 2 (2026-05-16) al §4.4, il cluster delle istituzioni politiche (government, government_types, institutions, stratification, election) sul round 2 (2026-05-16) al §4.5, il movimento sul round 2 (2026-05-16) al §4.6, le fazioni sul round 2 (2026-05-16) al §4.7, e il layer base dell'economia sul round 12 del suo primo audit (2026-07-16) al §4.8. L'audit del Knowledge Graph è l'item gating prima che possa essere promosso da §8 allo stato §4, prima che i suoi parametri possano essere aggiunti alle tabelle di parametri di §6, e prima che possa entrare nella campagna di validazione di §7.
- **Demografia Plan 3 (Eredità + Migrazione).** La spec di demografia di §4.1 copre mortalità, fertilità e formazione delle coppie; il Plan 3 estende la stessa metodologia audit-first all'eredità (trasferimento di proprietà e debito ai parenti superstiti alla morte di un agente) e alla migrazione demografica (la migrazione zona-zona di lungo orizzonte che complementa il movimento per tick di §4.6 con un flusso a scala generazionale). La spec è la sezione Plan 3 di `docs/superpowers/specs/2026-04-18-demography-design.md`.
- **Demografia Plan 4 (Inizializzazione, integrazione Engine, validazione storica).** Il Plan 4 collega i moduli di demografia di §4.1 — attualmente implementati e unit-testati in isolamento — al ciclo di tick live di `epocha/apps/simulation/engine.py`, fornisce la procedura di inizializzazione che seed-a una popolazione di partenza dal template per epoca, ed esegue la campagna di validazione storica di §7 contro i target Wrigley-Schofield (1981) e Human Mortality Database. Questo è il deliverable centrale che chiude la disclosure di gap di implementazione portata da §4.1 e risolve il caveat validation-pending portato da §7.5.
- **Mercati finanziari dell'economia (Spec 3 da scrivere).** L'integrazione comportamentale di §4.2 copre aspettative adattive, credito e sistema bancario, e mercato immobiliare; la prossima spec di economia estende a mercati obbligazionari ed azionari, contagio dei prezzi degli asset attraverso più banche, e il canale di prestito interbancario rimandato sotto le semplificazioni di §4.2.2. La spec non è ancora redatta; l'item di lavoro è registrato nella memoria di roadmap di lungo formato.
- **Esecuzione degli esperimenti di validazione.** La campagna specificata nel Capitolo 7 — acquisizione dei dataset, implementazione degli script, calcolo delle metriche e valutazione delle soglie — è il deliverable centrale tracciato in `docs/memory-backup/project_validation_experiments_pending.md`. L'esecuzione è legata al Plan 4 della roadmap di demografia sopra (che fornisce l'integrazione del ciclo di tick live richiesta dalla validazione) e all'audit del modulo §8 rimanente (il Knowledge Graph).
- **Evoluzione del Knowledge Graph (aggiornamenti live dalla simulazione).** Il cluster Knowledge Graph di §8.1 attualmente materializza il grafo dal log della simulazione in passaggi batch; l'item di lavoro di evoluzione sostituisce il passaggio batch con un aggiornamento live che estrae incrementalmente entità e relazioni da ciascun tick e le fonde nel grafo esistente senza una ri-estrazione completa. La modifica mantiene il grafo aggiornato entro un ritardo limitato dal tick live piuttosto che a granularità fine-corsa, che è il prerequisito per il contesto LLM ancorato al grafo nello step di decisione per tick di §3.2.
- **Analytics psicostoriografia.** La spec di analytics in `docs/superpowers/specs/2026-04-06-analytics-psicostoriografia-design.md` copre il layer di analisi post-hoc che fa emergere pattern emergenti da una simulazione completata: traiettorie nello spazio delle fasi, confronti di coorte a livello di zona, attribuzione delle cascate di eventi, ed export di plot publication-grade necessari per il paper scientifico del deliverable finale del progetto. La spec è redatta; l'implementazione è rimandata dietro il rifacimento audit e il Plan 4.
- **Adozione PostGIS più ampia.** PostGIS è già abilitato per §3.6 con le geometrie delle zone memorizzate come poligoni WGS84; l'item di lavoro di adozione più ampia estende la superficie geospaziale alle traiettorie degli agenti (storia di posizione per tick con indici spaziali), query di distanza routata tra zone (sostituendo la distanza astratta del grafo zone di §4.6 con il calcolo di shortest-path contro la geometria effettiva), e analisi di catchment per zona per i moduli di economia e demografia.
- **Agenti multi-livello (organizzazioni, stati, coalizioni).** La popolazione Epocha attuale è un insieme piatto di agenti individuali; l'item di lavoro multi-livello estende l'ontologia degli agenti ad attori corporativi che hanno le proprie pipeline decisionali, le proprie memorie e i propri spazi di azione, con gli agenti individuali come membri e con i layer di stato e coalizione sopra il layer di organizzazione. Il frame concettuale e gli ancoraggi di letteratura sono registrati in `docs/memory-backup/project_multilevel_agents.md`; la spec non è ancora redatta.
- **Generatore narrativo.** L'item di lavoro generatore narrativo produce un romanzo storico-scientifico di forma lunga dalla simulazione completata — gli archi per zona, per coorte, per personaggio intrecciati in una narrativa publication-grade nella lingua di output scelta con citazioni complete agli eventi sottostanti della simulazione. Il frame concettuale è registrato in `docs/memory-backup/project_narrative_generator.md`; l'item di lavoro è legato alla spec di analytics sopra (che produce il materiale strutturato che il generatore intreccia) e all'item di evoluzione del Knowledge Graph (che fornisce il catalogo di entità a cui la narrativa fa riferimento).
- **Layer media (giornali, social feed).** L'item di lavoro layer media materializza la stampa in-simulazione: edizioni di giornale per tick i cui articoli sono generati dagli eventi della simulazione attraverso una pipeline editoriale LLM, analoghi di social feed per i template moderni, e l'incrocio della copertura mediatica indietro nel cluster di propagazione del passaparola di §4.4 come sottotipo speciale di evento informativo. Il frame concettuale è registrato in `docs/memory-backup/project_media_layer.md`; l'item di lavoro è legato all'item di evoluzione del Knowledge Graph sopra.

---

# 10. Discussione

Ogni scelta documentata nei capitoli precedenti porta un compromesso che vale la pena dichiarare apertamente piuttosto che nascondere dietro il verdetto di convergenza dell'audit. Il più consequenziale è il costo della cognizione LLM relativo al realismo che compra: un tick che esercita la pipeline decisionale completa dell'agente di §3.2 porta un costo di token per agente che scala con i blocchi di personalità, memoria e contesto che il prompt deve includere, e l'envelope di budget per tick quindi limita la popolazione che il simulatore può portare su un dato tier hardware piuttosto che emergere da una proprietà strutturale del modello. I moduli auditati del Plan 1 e Plan 2 accettano diverse semplificazioni deliberate per mantenere il costo per tick limitato sotto questo envelope. La Hadwiger ASFR di §4.1.2 è valutata deterministicamente all'età dell'agente piuttosto che estratta da un modello stocastico per madre del tempo-al-concepimento; i coefficienti di modulazione Becker della Tabella 4.4 sono omogenei tra tutti e cinque i template di demografia in attesa della calibrazione del Plan 4; la macchineria di credito-e-sistema-bancario Diamond-Dybvig di §4.2.2 porta una singola banca aggregata piuttosto che una popolazione di banche concorrenti con un canale di prestito interbancario; la liquidazione del mercato immobiliare di §4.2.3 è single-round take-it-or-leave-it piuttosto che una convergenza multi-round bid-ask. Nessuna di queste semplificazioni è un difetto in senso auditato — ciascuna è documentata inline nel corrispondente paragrafo di Semplificazioni di §4.x e tracciata come deliverable di calibrazione del Plan 4 — ma il loro effetto cumulativo è che il layer scientifico auditato è più snello di quanto la letteratura censita in §2 supporterebbe in linea di principio. Un secondo compromesso visibile è il gap di integrazione con l'engine che §4.1 porta: mortalità, fertilità e formazione delle coppie sono implementate e unit-testate in isolamento, ma la loro orchestrazione nel ciclo di tick live in `epocha/apps/simulation/engine.py` è il deliverable centrale del Plan 4 e non è ancora attiva nel codice di produzione, in contrasto con i moduli di economia di §4.2 che sono genuinamente live nella pipeline per tick. Infine, la campagna di validazione del Capitolo 7 è metodologica piuttosto che evidenziale al commit pinnato: target, metriche e soglie di accettazione sono specificate, ma gli esperimenti che le consumano sono tracciati sotto `project_validation_experiments_pending.md` e legati allo stesso deliverable del Plan 4.

I limiti scientifici del lavoro presente vanno oltre le semplificazioni dentro il sottoinsieme auditato. Un modulo — il Knowledge Graph (§8.1) — è implementato nel codice ed esercitato da unit test ma non ha ancora completato l'audit avversariale che funge da gate alla promozione allo stato di Capitolo 4; i finding aperti INCORRECT, UNJUSTIFIED, INCONSISTENT e MISSING dal batch di audit del 2026-04-12 sono catalogati in `docs/scientific-audit-2026-04-12.md` e tracciati sotto `project_audit_repass_batch_2026_04_12_pending.md`. Dentro il sottoinsieme auditato, diversi valori di parametro sono seedati come euristiche di calibrazione piuttosto che derivati da una misurazione di fonte primaria: i coefficienti di modulazione Becker `β₀..β₄` dell'equazione (4.3), i coefficienti di modulazione del tasso di adattamento per agente `n_mod`, `o_mod`, `c_mod` dell'equazione (4.10), il `risk_premium = 0.5` di Stiglitz-Weiss dell'equazione (4.13) e il `CASCADE_LOSS_THRESHOLD = 0.5` di Allen-Gale del passaggio di contagio sono tutti documentati inline come parametri di design regolabili con la differenziazione per epoca rimandata al Plan 4. Lo schema a tick discreti è di per sé una scelta di modellizzazione sostanziale: gli eventi che occorrono dentro lo stesso tick — morti multiple, nascite simultanee, una vendita di proprietà e un default di prestito sullo stesso agente — sono risolti sequenzialmente all'interno dell'orchestratore per tick piuttosto che trattati come genuinamente concorrenti, che è la granularità appropriata per l'envelope di costo per tick ma che sopprime ogni interazione intra-tick che la letteratura del tempo continuo esporrebbe. Il resolver congiunto di mortalità materna di §4.1.2 è l'unico posto dove l'accoppiamento intra-tick è trattato esplicitamente, ed è trattato così precisamente perché risolvere la mortalità generica per prima e la mortalità da parto in seconda sulla stessa madre nello stesso tick produrrebbe un bias misurabile.

Dove Epocha si colloca nel paesaggio più ampio si legge meglio rispetto a tre tradizioni vicine. Le piattaforme ABM puramente rule-based (NetLogo, Mesa, Repast HPC, EURACE) eccellono nella scalabilità a popolazioni di milioni di agenti sotto regole individuali pienamente specificate, sulla forza di decenni di lavoro di ottimizzazione e una toolchain matura; il costo di quella scala è che la cognizione del singolo agente è vincolata a tutto ciò che la grammatica delle regole può esprimere, e il comportamento emergente che richiederebbe ragionamento in linguaggio naturale, memoria narrativa o deliberazione modulata dalla personalità deve essere approssimato da euristiche tarate a mano. Le simulazioni di agenti puramente LLM (Park et al. 2023 e la famiglia di esperimenti di agenti generativi che ne sono seguiti) eccellono all'estremo opposto: dozzine di agenti in un ambiente stilizzato possono esibire dinamiche sociali credibili senza alcuna grammatica comportamentale tarata a mano, sulla forza della cognizione in linguaggio naturale dell'LLM; il costo è che i substrati demografici ed economici che questi esperimenti ereditano dall'ambiente circostante sono troppo sottili per portare orizzonti pluridecennali o statistiche a livello di popolazione che la letteratura delle scienze sociali riconoscerebbe come ben formate. Il contributo di Epocha è l'ibrido: un substrato rule-based (engine economico di §3.6, engine demografico di §4.1, integrazione comportamentale di §4.2) che porta le dinamiche di popolazione sui timescale su cui la letteratura demografica ed economica opera, con la cognizione LLM stratificata in cima al substrato allo step di decisione per agente (§3.2) dove personalità, memoria e deliberazione in linguaggio naturale portano il peso esplicativo. L'ibrido paga un costo in token LLM per tick che le piattaforme puramente rule-based non pagano, ed eredita un costo in disciplina di audit che le piattaforme puramente LLM storicamente non hanno sostenuto, ma in cambio rende esplicita l'aggregazione multi-scala (individuo, fazione, stato) e ammette esperimenti di lungo orizzonte che nessuno dei due vicini può eseguire con un ancoraggio scientifico comparabile.

La classe di domande di ricerca che Epocha è progettata per abilitare segue direttamente dall'ibrido. Esperimenti di emergenza di lungo orizzonte — uno specifico assetto istituzionale, uno specifico pattern di shock, o una specifica distribuzione di personalità producono le traiettorie qualitative che il record storico esibisce nei secoli — diventano trattabili perché il substrato demografico ed economico auditato porta le dinamiche pluridecennali mentre il layer di cognizione LLM porta la variazione per agente. Esperimenti controfattuali e di intervento — cosa sarebbe successo se la Carestia Irlandese di §7.1 avesse innescato una risposta istituzionale anteriore, cosa sarebbe successo se il crollo del mercato immobiliare di §4.2.3 fosse stato preceduto da una traiettoria di confidenza bancaria differente — diventano trattabili perché la macchineria dei template per epoca rende esplicito l'intervento di parametro e l'RNG seedato di §3.4 rende l'esecuzione riproducibile. L'aggregazione multi-scala — dalla cognizione individuale attraverso il coordinamento a livello di fazione alla policy a livello di stato — diventa trattabile perché il modello di persistenza di §3.7 porta sia le righe individuali di agente sia le righe istituzionali come entità di prima classe piuttosto che come aggregati derivati. E la riproducibilità narrativa tra esecuzioni — lo stesso scenario rieseguito con lo stesso seed produce lo stesso log di decisione per agente e lo stesso arco narrativo emergente — diventa la base per il paper scientifico publication-grade che la roadmap del progetto del Capitolo 9 nomina come deliverable finale.

---

# 11. Limitazioni note

Il seguente catalogo raggruppa le limitazioni aperte per modulo. Ogni voce è deliberatamente breve — il contesto sostanziale vive nel corrispondente paragrafo di Semplificazioni di §4 o nella riga di stato di §8 — ed esiste qui come singolo inventario autoritativo per il lettore che ha bisogno della vista a livello di progetto in un unico posto. Due follow-up trasversali sottendono la maggior parte delle voci: l'audit sull'unico modulo rimasto in §8 (il Knowledge Graph) tracciato sotto `project_audit_repass_batch_2026_04_12_pending.md` e la campagna di validazione tracciata sotto `project_validation_experiments_pending.md`.

**Mortalità (§4.1.1).**
- Nessun effetto di coorte: ogni agente è esposto al template per epoca attivo al tick di simulazione piuttosto che al regime di mortalità in vigore alla nascita dell'agente.
- Etichette grezze di causa di morte (`early_life_mortality`, `external_cause`, `natural_senescence`) riflettono le tre componenti HP piuttosto che un'eziologia medica.
- Nessun modello di coda esplicito oltre l'estremo biologico: il cap di `0.999` sulla probabilità annua di mortalità è una guard numerica per la conversione geometrica al tick, non un sostanziale plateau di mortalità tarda.
- La valutazione per tick è esercitata dalla suite di unit test ma non è ancora invocata dal ciclo di tick live in `epocha/apps/simulation/engine.py`; l'integrazione è il deliverable centrale del Plan 4 di demografia.

**Fertilità (§4.1.2).**
- La Hadwiger ASFR è valutata deterministicamente all'età dell'agente senza alcuna eterogeneità inter-individuale nella fecondità biologica, in contrasto con l'estensione di apprendimento bayesiano che lascerebbe a ciascun agente apprendere il proprio parametro `T` dagli intervalli inter-nascita realizzati.
- Gemelli e nascite multiple di ordine superiore non sono modellate: ogni evento di nascita riuscito crea esattamente un neonato.
- I coefficienti di modulazione Becker della Tabella 4.4 sono omogenei tra tutti e cinque i template di demografia, tracciati come debito di audit B2-07 e assegnati alla calibrazione del Plan 4.
- Integrazione tick-loop rimandata al Plan 4 di demografia.

**Formazione delle coppie (§4.1.3).**
- Solo coppie monogame sono rappresentabili; configurazioni poligine e poliandriche sono rimandate (audit fix MISS-8).
- Schema a due generi per le primitive di matching: sebbene il layer agente porti `male`, `female`, `non_binary`, lo score di omogamia e l'algoritmo di stable matching non consumano i campi di genere o orientamento sessuale al commit pinnato.
- Nessun cooldown per le seconde nozze: il campo `mourning_ticks` per template è caricato ma non ancora consumato dal check di idoneità, quindi un agente vedovo può in linea di principio ri-accoppiarsi al tick successivo alla morte del partner.
- Gale-Shapley è applicato solo all'inizializzazione, non come fallback runtime quando una grande coorte non accoppiata si accumula.
- Integrazione tick-loop rimandata al Plan 4 di demografia.

**Aspettative adattive (§4.2.1).**
- Singola variabile per bene: solo il livello di prezzo è previsto, senza alcuna previsione congiunta cross-bene, alcuna previsione separata del tasso di inflazione, e alcuna previsione del secondo momento.
- Il `λ` per agente è omogeneo tra i beni dentro un singolo agente; una differenziazione goods-specific è un raffinamento futuro.
- Il tasso di adattamento non è esso stesso appreso: la modulazione di personalità dell'equazione (4.10) è statica, senza alcun meccanismo per cui un agente le cui previsioni siano state sistematicamente sbagliate aggiorni il proprio `λ`.
- L'aggregazione di prezzi multi-zona è la media cross-zona non pesata di `ZoneEconomy.market_prices` piuttosto che una previsione per zona per agente.

**Credito e sistema bancario (§4.2.2).**
- Singola banca aggregata per simulazione: nessun mercato di prestiti interbancari, nessun grafo di esposizione interbancario, nessuna banca centrale come prestatore di ultima istanza.
- L'assicurazione sui depositi è astratta: `BankingState.is_solvent` regola l'emissione di nuovi prestiti ma nessun fondo esplicito di assicurazione sui depositi esiste, e i depositanti non possono letteralmente ritirare depositi perché `AgentInventory.cash` rappresenta già il contante a portata di mano.
- La negoziazione del prestito è single-round take-it-or-leave-it; controproposte multi-round su importo, garanzia o durata sono rimandate.
- L'incremento del tasso di interesse al rollover è fisso a `1.10` per rollover piuttosto che essere una funzione della leva del mutuatario o del segnale di stress macroeconomico portato dall'indice di confidenza bancaria.

**Mercato immobiliare (§4.2.3).**
- Matching single-round per tick: un acquirente che perde contro un altro acquirente ordinato prima nell'iterazione non riceve alcuna seconda chance dentro lo stesso tick.
- Gli annunci si resettano per tick dopo la finestra di scadenza di `10` tick senza alcun fallback di priorità temporale a parità di prezzo.
- L'intento dell'acquirente è binario: `buy_property` non porta un tipo target o un prezzo massimo, e il passaggio di matching seleziona l'annuncio più economico nella zona dell'acquirente indipendentemente dal fit tra il tipo di proprietà e il ruolo dell'acquirente.
- La formazione del prezzo richiesto del venditore è di proprietà del layer di decisione LLM di §3.2 piuttosto che del mercato immobiliare stesso; questa sottosezione tratta il prezzo richiesto come esogeno.

**Sottosistemi progettati in attesa di audit (§8).** Un modulo attende ancora il suo audit avversariale: il Knowledge Graph. Cinque cluster del batch originale del 2026-04-12 sono convergenti e promossi — la reputazione sul round 2 (2026-05-12) al §4.3, il cluster di propagazione del passaparola (information flow, distortion, belief filter, più affinity) sul round 2 (2026-05-16) al §4.4, il cluster delle istituzioni politiche (government, government_types, institutions, stratification, election) sul round 2 (2026-05-16) al §4.5, il movimento sul round 2 (2026-05-16) al §4.6, e le fazioni sul round 2 (2026-05-16) al §4.7 — e il layer base dell'economia, che non era in quel batch, è convergente sul round 12 del suo primo audit (2026-07-16) ed è stato promosso al §4.8. L'audit del Knowledge Graph è tracciato sotto `project_audit_repass_batch_2026_04_12_pending.md` e funge da gate alla sua promozione da §8 allo stato §4, all'inclusione dei suoi parametri nelle tabelle di calibrazione di §6 e al suo ingresso nella campagna di validazione di §7.

**Esperimenti di validazione (Capitolo 7).** La metodologia — dataset, metriche e soglie di accettazione — è specificata attraverso §7.1 a §7.3, ma la campagna sperimentale che consuma la metodologia è legata al Plan 4 ed è tracciata sotto `project_validation_experiments_pending.md`.

**Knowledge Graph (§8.1).** Il grafo è attualmente materializzato in passaggi batch dal log della simulazione; l'aggiornamento live da una simulazione in esecuzione, che è il prerequisito per il contesto LLM ancorato al grafo nello step di decisione per tick, è l'item di lavoro dedicato della roadmap del Capitolo 9.

**Limitazioni trasversali.** Le dinamiche spaziali oltre il grafo astratto delle zone non sono esercitate: PostGIS è abilitato e le geometrie delle zone sono memorizzate come poligoni WGS84 per §3.6, ma le query di distanza routata tra zone, la memorizzazione per tick di traiettorie degli agenti con indici spaziali e l'analisi di catchment per zona per i moduli di economia e demografia sono rimandate all'item di lavoro PostGIS più ampio del Capitolo 9. Lo schema a tick discreti di §3.1 risolve gli eventi intra-tick sequenzialmente all'interno dell'orchestratore per tick piuttosto che trattarli come concorrenti, con il resolver congiunto di mortalità materna di §4.1.2 come unico posto dove l'accoppiamento intra-tick è trattato esplicitamente. La gestione di eventi in tempo reale tra tick non è supportata.

---

# 12. Conclusioni

Epocha come documentato al commit pinnato spedisce un substrato demografico auditato che copre mortalità Heligman-Pollard, fertilità Hadwiger-con-Becker e formazione delle coppie Gale-Shapley con Goode 1963 (§4.1), un'economia comportamentale auditata che copre aspettative adattive Cagan-Nerlove, credito e sistema bancario Diamond-Dybvig e un mercato immobiliare ancorato a Gordon (§4.2), una pipeline decisionale di agenti guidata da LLM che consuma lo stato per tick del substrato e riscrive nel layer di persistenza (§3.2), un layer base dell'economia auditato che copre la produzione CES, il clearing con tâtonnement, la partizione conservativa dei redditi da fattori e la diagnostica di conservazione di Fisher (§4.8), e un sottosistema implementato-ma-pre-audit (§8): il Knowledge Graph. L'infrastruttura runtime copre un tick engine con loop Celery auto-enqueuing, una strategia RNG seedata per fase che rende ogni esecuzione riproducibile attraverso macchine dall'hash di commit, dal seed e dallo stato iniziale del database (§3.4), un adapter di provider LLM che astrae su OpenAI vero e proprio, Groq, Gemini, OpenRouter, Together AI, Mistral, LM Studio e Ollama con rotazione delle chiavi e un limiter sliding-window backed da Redis (§3.5), e una dashboard più un layer di chat WebSocket che esponendo lo stato di simulazione live e la superficie di conversazione agente-per-agente all'operatore (§3.8).

Ciò che distingue questo codebase dal paesaggio circostante è meno i moduli individuali — la maggior parte ha antecedenti ben noti nella letteratura censita in §2 — e più la disciplina che li produce e li mantiene. Il whitepaper bilingue di §1 è un documento vivente congelato a ogni merge sul branch di sviluppo, con la companion italiana pubblicata accanto all'originale inglese; ogni formula, parametro e algoritmo nei capitoli auditati cita una fonte primaria, e le asserzioni non verificate sono segnalate inline piuttosto che presentate come fatto. Il workflow canonico a sette fasi che governa ogni sottosistema (ideazione, requisiti, plan, task breakdown, implementazione, test generale, chiusura) porta due gate pesanti e due leggeri con approvazione umana esplicita a ciascuno, e la policy di audit avversariale obbligatoria attiva il revisore `critical-analyzer` sia in fase di spec sia in fase di codice con un loop di convergenza che non chiude su "abbastanza vicino". La riproducibilità è incorporata piuttosto che retrofittata: i template per epoca portano i valori di parametro per epoca fuori dal codice sorgente e in artefatti auditabili, gli stream RNG seedati sono partizionati per simulazione, tick e fase in modo che un refactor non possa silenziosamente spostare la sequenza casuale che un sottosistema vede, e l'Appendice B registra i comandi esatti tramite i quali ogni risultato riportato può essere rigenerato da un checkout pulito pinnato all'hash di commit congelato.

Il codebase è open source sotto licenza Apache 2.0 a https://github.com/mauriziomocci/epocha, e i contributi sono benvenuti attraverso il workflow canonico a sette fasi descritto in questo paper. I lettori che desiderano estendere un modulo auditato in §4 dovrebbero aspettarsi un percorso di contribuzione spec-first con audit scientifico avversariale obbligatorio prima che qualsiasi codice venga mergiato; i lettori che desiderano avanzare il modulo rimanente di §8 (il Knowledge Graph) attraverso il suo audit troveranno i finding aperti catalogati in `docs/scientific-audit-2026-04-12.md` e tracciati sotto `project_audit_repass_batch_2026_04_12_pending.md`. La roadmap del Capitolo 9 nomina le priorità immediate — l'audit del Knowledge Graph, demografia Plan 3 (eredità e migrazione), demografia Plan 4 (integrazione engine e validazione storica) e la prossima spec di economia che estende §4.2 a mercati obbligazionari ed azionari — e funge da entry point per i nuovi contributori che cercano un item di lavoro ben definito.

---

# 13. Riferimenti

- Acemoglu, D., and Robinson, J. A. (2006). *Economic Origins of
  Dictatorship and Democracy*. Cambridge University Press,
  Cambridge. ISBN 978-0-521-85526-6.
  https://doi.org/10.1017/CBO9780511510809
- Aher, G. V., Arriaga, R. I., and Kalai, A. T. (2023). Using large
  language models to simulate multiple humans and replicate human
  subject studies. In *Proceedings of the 40th International Conference
  on Machine Learning (ICML 2023)*, PMLR, 202, 337–371.
  https://proceedings.mlr.press/v202/aher23a.html
- Alesina, A., and Perotti, R. (1996). Income distribution, political
  instability, and investment. *European Economic Review*, 40(6),
  1203–1228. https://doi.org/10.1016/0014-2921(95)00030-5
- Allen, F., and Gale, D. (2000). Financial contagion. *Journal of
  Political Economy*, 108(1), 1–33. https://doi.org/10.1086/262109
- Allport, G. W., and Postman, L. (1947). *The Psychology of Rumor*.
  Henry Holt and Company, New York, xiv+247 pp. (Pre-ISBN
  monograph; reviewed in Zeller 1948, *The Annals of the American
  Academy of Political and Social Science*, 257(1), 145–146,
  https://doi.org/10.1177/000271624825700169.)
- Arendt, H. (1951). *The Origins of Totalitarianism*. Schocken Books,
  New York. Reissued by Harcourt Brace, 1973.
  ISBN 978-0-15-670153-2 (Harcourt 1973 paperback).
- Argyle, L. P., Busby, E. C., Fulda, N., Gubler, J. R., Rytting, C., and
  Wingate, D. (2023). Out of one, many: using language models to simulate
  human samples. *Political Analysis*, 31(3), 337–351.
  https://doi.org/10.1017/pan.2023.2
- Antonakis, J., Bastardoz, N., Jacquart, P., and Shamir, B. (2016).
  Charisma: an ill-defined and ill-measured gift. *Annual Review of
  Organizational Psychology and Organizational Behavior*, 3, 293–319.
  https://doi.org/10.1146/annurev-orgpsych-041015-062305
- Arrow, K. J., Chenery, H. B., Minhas, B. S., and Solow, R. M. (1961).
  Capital-labor substitution and economic efficiency. *The Review of
  Economics and Statistics*, 43(3), 225–250.
  https://doi.org/10.2307/1927286
- Ashraf, Q., and Galor, O. (2011). Dynamics and stagnation in the
  Malthusian epoch. *American Economic Review*, 101(5), 2003–2041.
  https://doi.org/10.1257/aer.101.5.2003
- Asimov, I. (1951). *Foundation*. Gnome Press, New York. (Fix-up
  novel collecting four short stories originally published in
  *Astounding Science-Fiction* between May 1942 and January 1950,
  preceded by a new introductory chapter, "The Psychohistorians",
  written for the Gnome Press edition.)
- Axelrod, R. (1984). *The Evolution of Cooperation*. Basic Books, New
  York. ISBN 978-0-465-02121-5.
- Bartlett, F. C. (1932). *Remembering: A Study in Experimental and
  Social Psychology*. Cambridge University Press, Cambridge.
  (Pre-ISBN monograph; reissued by Cambridge University Press in
  1995 with ISBN 978-0-521-48356-8.)
- Bass, B. M. (1985). *Leadership and Performance Beyond Expectations*.
  Free Press, New York. ISBN 978-0-02-901810-7.
- Baumeister, R. F., Bratslavsky, E., Finkenauer, C., and Vohs, K. D.
  (2001). Bad is stronger than good. *Review of General Psychology*,
  5(4), 323–370. https://doi.org/10.1037/1089-2680.5.4.323
- Becker, G. S. (1991). *A Treatise on the Family*, enlarged edition.
  Harvard University Press, Cambridge, MA. ISBN 978-0-674-90698-3.
- Besley, T., and Persson, T. (2011). *Pillars of Prosperity: The
  Political Economics of Development Clusters*. Princeton University
  Press, Princeton, NJ. ISBN 978-0-691-15268-4.
- Bonabeau, E. (2002). Agent-based modeling: methods and techniques for
  simulating human systems. *Proceedings of the National Academy of
  Sciences*, 99(Suppl. 3), 7280–7287.
  https://doi.org/10.1073/pnas.082080899
- Braudel, F. (1979). *Civilisation matérielle, économie et capitalisme,
  XVe-XVIIIe siècle*. Three volumes. Armand Colin, Paris. English
  translation (1981–1984), *Civilization and Capitalism, 15th–18th
  Century*, by Siân Reynolds. University of California Press, Berkeley.
- Brown, R., and Kulik, J. (1977). Flashbulb memories. *Cognition*, 5(1),
  73–99. https://doi.org/10.1016/0010-0277(77)90018-X
- Bueno de Mesquita, B., Smith, A., Siverson, R. M., and Morrow, J. D.
  (2003). *The Logic of Political Survival*. MIT Press, Cambridge, MA.
  ISBN 978-0-262-02546-1.
- Cagan, P. (1956). The monetary dynamics of hyperinflation. In M.
  Friedman (ed.), *Studies in the Quantity Theory of Money*. University
  of Chicago Press, Chicago, 25–117.
- Caprara, G. V., Schwartz, S., Capanna, C., Vecchione, M., and
  Barbaranelli, C. (2006). Personality and politics: values, traits,
  and political choice. *Political Psychology*, 27(1), 1–28.
  https://doi.org/10.1111/j.1467-9221.2006.00447.x
- Castelfranchi, C., Conte, R., and Paolucci, M. (1998). Normative
  reputation and the costs of compliance. *Journal of Artificial
  Societies and Social Simulation*, 1(3).
  https://www.jasss.org/1/3/3.html
- Castelfranchi, C., Falcone, R., and Tan, Y.-H. (2001). The role of
  trust and deception in virtual societies. In *Proceedings of the
  34th Annual Hawaii International Conference on System Sciences
  (HICSS-34)*. IEEE. https://doi.org/10.1109/hicss.2001.927042
- Chandler, D. G. (1966). *The Campaigns of Napoleon*. Weidenfeld and
  Nicolson, London, xliii + 1172 pp. (Pre-ISBN trade edition; Macmillan
  reprint 1973, ISBN 978-0-02-523660-8. Source for the per-mode sustained
  travel rates of §4.6.)
- Chandola, T., Coleman, D. A., and Hiorns, R. W. (1999). Recent European
  fertility patterns: fitting curves to "distorted" distributions.
  *Population Studies*, 53(3), 317–329.
  https://doi.org/10.1080/00324720308089
- Coale, A. J., and Trussell, T. J. (1974). Model fertility schedules:
  variations in the age structure of childbearing in human populations.
  *Population Index*, 40(2), 185–258.
  https://doi.org/10.2307/2733910
- Collier, N., and North, M. J. (2013). Parallel agent-based simulation
  with Repast for High Performance Computing. *SIMULATION*, 89(10),
  1215–1235. https://doi.org/10.1177/0037549712462620
- Conte, R., and Paolucci, M. (2002). *Reputation in Artificial Societies:
  Social Beliefs for Social Order*. Multiagent Systems, Artificial
  Societies, and Simulated Organizations, vol. 6. Kluwer Academic
  Publishers, Dordrecht. ISBN 978-1-4020-7186-7.
  https://doi.org/10.1007/978-1-4615-1159-5
- Costa, P. T., and McCrae, R. R. (1992). *Revised NEO Personality
  Inventory (NEO PI-R) and NEO Five-Factor Inventory (NEO-FFI)
  Professional Manual*. Psychological Assessment Resources, Odessa, FL.
- Cronin, A. K. (2009). *How Terrorism Ends: Understanding the Decline
  and Demise of Terrorist Campaigns*. Princeton University Press,
  Princeton, NJ. ISBN 978-0-691-13948-7.
- Deaton, A., and Muellbauer, J. (1980). *Economics and Consumer
  Behavior*. Cambridge University Press, Cambridge.
  https://doi.org/10.1017/CBO9780511805653
- Deissenberg, C., van der Hoog, S., and Dawid, H. (2008). EURACE: a
  massively parallel agent-based model of the European economy.
  *Applied Mathematics and Computation*, 204(2), 541–552.
  https://doi.org/10.1016/j.amc.2008.05.116
- Diamond, D. W. (1989). Reputation acquisition in debt markets.
  *Journal of Political Economy*, 97(4), 828–862.
  https://doi.org/10.1086/261630
- Diamond, D. W., and Dybvig, P. H. (1983). Bank runs, deposit insurance,
  and liquidity. *Journal of Political Economy*, 91(3), 401–419.
  https://doi.org/10.1086/261155
- Dunbar, R. I. M. (1992). Neocortex size as a constraint on group size in
  primates. *Journal of Human Evolution*, 22(6), 469–493.
  https://doi.org/10.1016/0047-2484(92)90081-J
- Epstein, J. M., and Axtell, R. (1996). *Growing Artificial Societies:
  Social Science from the Bottom Up*. Brookings Institution Press /
  MIT Press, Washington, DC and Cambridge, MA. ISBN 978-0-262-55025-3.
- Evans, G. W., and Honkapohja, S. (2001). *Learning and Expectations
  in Macroeconomics*. Frontiers of Economic Research. Princeton
  University Press, Princeton, NJ. ISBN 978-0-691-04921-2.
- Festinger, L., Schachter, S., and Back, K. (1950). *Social Pressures in
  Informal Groups: A Study of Human Factors in Housing*. Harper and
  Brothers, New York.
- Finer, S. E. (1962). *The Man on Horseback: The Role of the Military
  in Politics*. Pall Mall Press, London.
  ISBN 978-1-138-52538-7 (Routledge 2017 reissue).
- Fish, M. S. (2002). Islam and authoritarianism. *World Politics*,
  55(1), 4–37. https://doi.org/10.1353/wp.2003.0004
- Fisher, I. (1911). *The Purchasing Power of Money: Its Determination
  and Relation to Credit, Interest and Crises*. Macmillan, New York.
  https://archive.org/details/purchasingpowerm00fishuoft
- Freedom House (2024). *Freedom in the World*. Annual report series.
  Freedom House, Washington, DC.
  https://freedomhouse.org/report/freedom-world
- Gale, D., and Shapley, L. S. (1962). College admissions and the
  stability of marriage. *The American Mathematical Monthly*, 69(1),
  9-15. https://doi.org/10.2307/2312726
- Geddes, B. (1999). What do we know about democratization after twenty
  years? *Annual Review of Political Science*, 2, 115–144.
  https://doi.org/10.1146/annurev.polisci.2.1.115
- Gilbert, D. (2011). *The American Class Structure in an Age of Growing
  Inequality* (8th ed.). Pine Forge Press / SAGE, Thousand Oaks, CA.
  ISBN 978-1-4129-7965-7.
- Gompertz, B. (1825). On the nature of the function expressive of the
  law of human mortality, and on a new mode of determining the value of
  life contingencies. *Philosophical Transactions of the Royal Society
  of London*, 115, 513–583. https://doi.org/10.1098/rstl.1825.0026
- Goode, W. J. (1963). *World Revolution and Family Patterns*. The Free
  Press of Glencoe, New York. (Pre-ISBN monograph; Free Press / Macmillan
  edition, xii+432 pp. Source for the arranged-marriage typology and the
  parent-child asymmetry adopted in §4.1.3.)
- Gordon, M. J. (1959). Dividends, earnings, and stock prices.
  *The Review of Economics and Statistics*, 41(2), 99–105.
  https://doi.org/10.2307/1927792
- Granovetter, M. S. (1973). The strength of weak ties. *American
  Journal of Sociology*, 78(6), 1360–1380.
  https://doi.org/10.1086/225469
- Graziano, W. G., and Tobin, R. M. (2002). Agreeableness: dimension
  of personality or social desirability artifact? *Journal of
  Personality*, 70(5), 695-728. https://doi.org/10.1111/1467-6494.05021
- Greif, A. (1993). Contract enforceability and economic institutions in
  early trade: the Maghribi traders' coalition. *American Economic
  Review*, 83(3), 525–548. JSTOR 2117532.
- Gualdi, S., Tarzia, M., Zamponi, F., and Bouchaud, J.-P. (2015).
  Tipping points in macroeconomic agent-based models. *Journal of
  Economic Dynamics and Control*, 50, 29–61.
  https://doi.org/10.1016/j.jedc.2014.08.003
- Hackman, J. R. (2002). *Leading Teams: Setting the Stage for Great
  Performances*. Harvard Business School Press, Boston.
  ISBN 978-1-57851-333-1.
- Hadwiger, H. (1940). Eine analytische Reproduktionsfunktion für
  biologische Gesamtheiten. *Skandinavisk Aktuarietidskrift*, 1940
  (issues 3–4), 101–113.
  https://doi.org/10.1080/03461238.1940.10404802
- Hajnal, J. (1965). European marriage patterns in perspective. In D. V.
  Glass and D. E. C. Eversley (eds.), *Population in History: Essays in
  Historical Demography*. Edward Arnold, London, 101–143. (Co-edition
  by Aldine Publishing Company, Chicago, 1965; reprint in *Population
  in History*, Routledge, 2017, https://doi.org/10.4324/9781315127019.)
- Hammel, E. A., McDaniel, C. K., and Wachter, K. W. (1979). Demographic
  consequences of incest tabus: a microsimulation analysis. *Science*,
  205(4410), 972–977. https://doi.org/10.1126/science.205.4410.972
- Heligman, L., and Pollard, J. H. (1980). The age pattern of mortality.
  *Journal of the Institute of Actuaries*, 107(1), 49–80.
  https://doi.org/10.1017/S0020268100040257
- Hobbes, T. (1651/1996). *Leviathan* (R. Tuck, ed.). Cambridge Texts
  in the History of Political Thought. Cambridge University Press,
  Cambridge. ISBN 978-0-521-56797-8 (1996 critical edition of the 1651
  original).
- Homer, S., and Sylla, R. (2005). *A History of Interest Rates*, fourth
  edition. Wiley Finance. John Wiley and Sons, Hoboken, NJ.
  ISBN 978-0-471-73283-9.
- Huckfeldt, R., and Sprague, J. (1987). Networks in context: the
  social flow of political information. *American Political Science
  Review*, 81(4), 1197–1216. https://doi.org/10.2307/1962585
- Human Mortality Database (HMD) (2024). University of California,
  Berkeley (USA) and Max Planck Institute for Demographic Research
  (Germany). https://www.mortality.org
- Iannaccone, L. R. (1992). Sacrifice and stigma: reducing free-riding
  in cults, communes, and other collectives. *Journal of Political
  Economy*, 100(2), 271-291. https://doi.org/10.1086/261818
- ILO, IMF, OECD, UNECE, Eurostat, and World Bank (2004). *Consumer
  Price Index Manual: Theory and Practice*. International Labour
  Office, Ginevra. ISBN 92-2-113699-X.
- Jones, L. E., and Tertilt, M. (2008). An economic history of fertility
  in the United States: 1826-1960. In *Frontiers of Family Economics*
  (Population Economics, vol. 1), 165-230. Emerald Group Publishing.
  https://doi.org/10.1016/S1574-0129(08)00005-7
- Judge, T. A., Bono, J. E., Ilies, R., and Gerhardt, M. W. (2002).
  Personality and leadership: a qualitative and quantitative review.
  *Journal of Applied Psychology*, 87(4), 765–780.
  https://doi.org/10.1037/0021-9010.87.4.765
- Jøsang, A., and Ismail, R. (2002). The beta reputation system. In
  *Proceedings of the 15th Bled Electronic Commerce Conference (Bled
  2002)*, 41–55. https://aisel.aisnet.org/bled2002/41/
- Kahneman, D., and Deaton, A. (2010). High income improves evaluation
  of life but not emotional well-being. *Proceedings of the National
  Academy of Sciences*, 107(38), 16489-16493.
  https://doi.org/10.1073/pnas.1011492107
- Kalmijn, M. (1998). Intermarriage and homogamy: causes, patterns,
  trends. *Annual Review of Sociology*, 24, 395-421.
  https://doi.org/10.1146/annurev.soc.24.1.395
- Kalyvas, S. N. (2006). *The Logic of Violence in Civil War*. Cambridge
  University Press, Cambridge. ISBN 978-0-521-67004-2.
  https://doi.org/10.1017/CBO9780511818462
- Karlan, D. S. (2005). Using experimental economics to measure social
  capital and predict financial decisions. *American Economic Review*,
  95(5), 1688–1699. https://doi.org/10.1257/000282805775014407
- Lee, R. D., and Carter, L. R. (1992). Modeling and forecasting U.S.
  mortality. *Journal of the American Statistical Association*, 87(419),
  659–671. https://doi.org/10.1080/01621459.1992.10475265
- Levitsky, S., and Way, L. A. (2010). *Competitive Authoritarianism:
  Hybrid Regimes after the Cold War*. Cambridge University Press,
  Cambridge. ISBN 978-0-521-70915-5.
- Lewis, P., Perez, E., Piktus, A., Petroni, F., Karpukhin, V., Goyal,
  N., Küttler, H., Lewis, M., Yih, W., Rocktäschel, T., Riedel, S., and
  Kiela, D. (2020). Retrieval-augmented generation for knowledge-intensive
  NLP tasks. In *Advances in Neural Information Processing Systems
  (NeurIPS 2020)*, 33, 9459–9474. Preprint: arXiv:2005.11401.
  https://arxiv.org/abs/2005.11401
- Lewis-Beck, M. S., and Stegmaier, M. (2000). Economic determinants
  of electoral outcomes. *Annual Review of Political Science*, 3,
  183–219. https://doi.org/10.1146/annurev.polisci.3.1.183
- Linz, J. J. (2000). *Totalitarian and Authoritarian Regimes*. Lynne
  Rienner Publishers, Boulder, CO. ISBN 978-1-55587-890-0.
- Lodge, M., Steenbergen, M. R., and Brau, S. (1995). The responsive
  voter: campaign information and the dynamics of candidate evaluation.
  *American Political Science Review*, 89(2), 309–326.
  https://doi.org/10.2307/2082427
- Marshall, M. G., and Gurr, T. R. (2020). *Polity 5: Political Regime
  Characteristics and Transitions, 1800–2018. Dataset Users' Manual*.
  Center for Systemic Peace, Vienna, VA.
  https://www.systemicpeace.org/polityproject.html
- Masad, D., and Kazil, J. (2015). Mesa: an agent-based modeling framework.
  In *Proceedings of the 14th Python in Science Conference (SciPy 2015)*,
  51–58. https://doi.org/10.25080/Majora-7b98e3ed-009
- Mayer, R. C., Davis, J. H., and Schoorman, F. D. (1995). An
  integrative model of organizational trust. *Academy of Management
  Review*, 20(3), 709-734. https://doi.org/10.2307/258792
- McCrae, R. R., and Costa, P. T. (1987). Validation of the five-factor
  model of personality across instruments and observers. *Journal of
  Personality and Social Psychology*, 52(1), 81–90.
  https://doi.org/10.1037/0022-3514.52.1.81
- McCrae, R. R., and Costa, P. T. (2003). *Personality in Adulthood:
  A Five-Factor Theory Perspective* (2nd ed.). Guilford Press, New York.
  ISBN 978-1-57230-827-2.
- Merolla, J. L., and Zechmeister, E. J. (2011). The nature, determinants,
  and consequences of Chávez's charisma: evidence from a study of
  Venezuelan public opinion. *Comparative Political Studies*, 44(1),
  28–54. https://doi.org/10.1177/0010414010381076
- Miller, J. D., and Lynam, D. (2001). Structural models of personality
  and their relation to antisocial behavior: a meta-analytic review.
  *Criminology*, 39(4), 765–798.
  https://doi.org/10.1111/j.1745-9125.2001.tb00940.x
- Minsky, H. P. (1986). *Stabilizing an Unstable Economy*. A Twentieth
  Century Fund Report. Yale University Press, New Haven.
  ISBN 978-0-300-03386-1.
- Mokyr, J. (1985). *Why Ireland Starved: A Quantitative and Analytical
  History of the Irish Economy 1800-1850*, second edition. George Allen
  and Unwin, London. ISBN 978-0-04-941011-7.
- Muth, J. F. (1961). Rational expectations and the theory of price
  movements. *Econometrica*, 29(3), 315–335.
  https://doi.org/10.2307/1909635
- Nerlove, M. (1958). Adaptive expectations and cobweb phenomena.
  *Quarterly Journal of Economics*, 72(2), 227–240.
  https://doi.org/10.2307/1880597
- Olson, M. (1965). *The Logic of Collective Action: Public Goods and the
  Theory of Groups*. Harvard Economic Studies, vol. 124. Harvard
  University Press, Cambridge, MA. (Pre-ISBN; revised edition with new
  preface, 1971, ISBN 978-0-674-53751-4.)
- Park, J. S., O'Brien, J. C., Cai, C. J., Morris, M. R., Liang, P., and
  Bernstein, M. S. (2023). Generative agents: interactive simulacra of
  human behavior. In *Proceedings of the 36th Annual ACM Symposium on
  User Interface Software and Technology (UIST '23)*. ACM.
  https://doi.org/10.1145/3586183.3606763
- Powell, J. M., and Thyne, C. L. (2011). Global instances of coups from
  1950 to 2010: a new dataset. *Journal of Peace Research*, 48(2),
  249–259. https://doi.org/10.1177/0022343310397436
- Reimers, N., and Gurevych, I. (2019). Sentence-BERT: sentence embeddings
  using siamese BERT-networks. In *Proceedings of the 2019 Conference on
  Empirical Methods in Natural Language Processing and the 9th International
  Joint Conference on Natural Language Processing (EMNLP-IJCNLP)*, Hong Kong,
  3980–3990. https://doi.org/10.18653/v1/D19-1410
- Reinhart, C. M., and Rogoff, K. S. (2009). *This Time Is Different:
  Eight Centuries of Financial Folly*. Princeton University Press,
  Princeton, NJ. ISBN 978-0-691-14216-6.
- Ricardo, D. (1817). *On the Principles of Political Economy and
  Taxation*. John Murray, Londra. (Ristampato in Sraffa, P. (a cura
  di), *The Works and Correspondence of David Ricardo*, vol. I,
  Cambridge University Press, 1951.)
- Riker, W. H. (1962). *The Theory of Political Coalitions*. Yale
  University Press, New Haven. ISBN 978-0-300-00139-6.
- Rose-Ackerman, S., and Palifka, B. J. (2016). *Corruption and
  Government: Causes, Consequences, and Reform* (2nd ed.). Cambridge
  University Press, Cambridge. ISBN 978-1-107-08120-7.
- Sabater, J., and Sierra, C. (2002). REGRET: reputation in gregarious
  societies. In *Proceedings of the 5th International Conference on
  Autonomous Agents (AGENTS '01)*, 194–195. ACM.
  https://doi.org/10.1145/375735.376110
- Scarf, H. (1960). Some examples of global instability of the
  competitive equilibrium. *International Economic Review*, 1(3),
  157–172. https://doi.org/10.2307/2556215
- Schelling, T. C. (1971). Dynamic models of segregation. *Journal of
  Mathematical Sociology*, 1(2), 143–186.
  https://doi.org/10.1080/0022250X.1971.9989794
- Schmertmann, C. P. (2003). A system of model fertility schedules with
  graphically intuitive parameters. *Demographic Research*, 9, 81–110.
  https://doi.org/10.4054/DemRes.2003.9.5
- Seppecher, P. (2012). Flexibility of wages and macroeconomic
  instability in an agent-based computational model with endogenous
  money. *Macroeconomic Dynamics*, 16(S2), 284–297.
  https://doi.org/10.1017/S1365100511000447
- Shiller, R. J. (2000). *Irrational Exuberance*. Princeton University
  Press, Princeton, NJ. ISBN 978-0-691-05062-6.
- Shoven, J. B., and Whalley, J. (1992). *Applying General Equilibrium*.
  Cambridge Surveys of Economic Literature. Cambridge University Press,
  Cambridge. ISBN 978-0-521-31986-7.
- Spielauer, M. (2011). What is social science microsimulation?
  *Social Science Computer Review*, 29(1), 9–20.
  https://doi.org/10.1177/0894439310370085
- Stiglitz, J. E., and Weiss, A. (1981). Credit rationing in markets
  with imperfect information. *American Economic Review*, 71(3),
  393–410. https://www.jstor.org/stable/1802787
- Stogdill, R. M. (1948). Personal factors associated with leadership:
  a survey of the literature. *Journal of Psychology*, 25(1), 35–71.
  https://doi.org/10.1080/00223980.1948.9917362
- Tabeau, E., van den Berg Jeths, A., and Heathcote, C. (eds.) (2001).
  *Forecasting Mortality in Developed Countries: Insights from a
  Statistical, Demographic and Epidemiological Perspective*. European
  Studies of Population, vol. 9. Kluwer Academic Publishers, Dordrecht.
  https://doi.org/10.1007/0-306-47562-6
- van Imhoff, E., and Post, W. (1998). Microsimulation methods for
  population projection. *Population: An English Selection*, 10(1),
  97–138. (English-language counterpart of the article in *Population*,
  53(HS1), 97–136, December 1998.)
- Walras, L. (1874). *Éléments d'économie politique pure, ou théorie de
  la richesse sociale*. L. Corbaz et Cie., Lausanne (part I, 1874;
  part II issued 1877). Definitive (fourth) edition published by
  F. Pichon, Paris, 1900. English translation from the 1926 definitive
  edition by W. Jaffé (1954), *Elements of Pure Economics, or the
  Theory of Social Wealth*. George Allen and Unwin, London, for the
  American Economic Association and the Royal Economic Society.
- Weber, M. (1922/1978). *Economy and Society* (G. Roth and C. Wittich,
  eds. and trans.). University of California Press, Berkeley.
  ISBN 978-0-520-03500-3 (1978 English edition of the original German
  1922 *Wirtschaft und Gesellschaft*).
- Wicksell, K. (1898). *Geldzins und Güterpreise: Eine Studie über
  die den Tauschwert des Geldes bestimmenden Ursachen*. Gustav Fischer,
  Jena. English translation by R. F. Kahn (1936), *Interest and Prices:
  A Study of the Causes Regulating the Value of Money*, with an
  introduction by Bertil Ohlin. Macmillan, London, for the Royal
  Economic Society.
- Wilensky, U. (1999). NetLogo. Center for Connected Learning and
  Computer-Based Modeling, Northwestern University, Evanston, IL.
  http://ccl.northwestern.edu/netlogo/
- Winters, J. A. (2011). *Oligarchy*. Cambridge University Press,
  Cambridge. ISBN 978-1-107-00528-0.
- Wrigley, E. A., and Schofield, R. S. (1981). *The Population History
  of England, 1541-1871: A Reconstruction*. Edward Arnold, London.
  Reissued by Cambridge University Press, 1989. ISBN 978-0-521-35688-6.
- Zhou, W.-X., Sornette, D., Hill, R. A., and Dunbar, R. I. M. (2005).
  Discrete hierarchical organization of social group sizes. *Proceedings
  of the Royal Society B*, 272(1561), 439–444.
  https://doi.org/10.1098/rspb.2004.2970
- Zinn, S. (2013). The MicSim package of R: an entry-level toolkit for
  continuous-time microsimulation. *International Journal of
  Microsimulation*, 7(3), 3–32.
  https://doi.org/10.34196/ijm.00105

---

# 14. Appendici

## Appendice A — Tabelle complete dei parametri

L'Appendice A è l'inventario consolidato canonico di ogni parametro
consumato dai capitoli auditati di Methods di §4.1 (demografia) e §4.2
(integrazione comportamentale dell'economia). Ogni riga registra il nome
del parametro come dichiarato nel sorgente, il suo significato semantico,
l'intervallo ammissibile, il valore o i valori per template di era, la
citazione della fonte primaria già presente in §13 e lo stato di
calibrazione — `verified` quando il valore è preso da una fonte primaria
citata, `tunable` quando il valore è un'euristica di calibrazione
rinviata al Plan 4, `heuristic` quando il valore codifica un vincolo
strutturale codificato fuori dai template. Le tabelle inline di §4.x
restano in posizione come riassunti introduttivi; questa appendice è il
riferimento autoritativo per la vista consolidata.

**A.1 — Mortalità di Heligman-Pollard (§4.1.1).** Gli otto parametri HP
sono definiti per equazione (4.1). Gli intervalli ammissibili coincidono
con i bound imposti da `fit_heligman_pollard()` in `mortality.py:148-149`
e sono coerenti con la letteratura attuariale sul modello HP; i valori
per era sono i valori seed spediti con i template del Plan 1 e sono
provvisori in attesa della campagna di fitting del Plan 4 contro i
target citati. Pre-industriale cristiano e pre-industriale islamico
condividono blocchi di mortalità identici.

| Parametro | Significato | Intervallo ammissibile | Pre-industriale (Cristiano/Islamico) | Industriale | Democrazia moderna | Sci-fi | Fonte | Stato |
|---|---|---|---|---|---|---|---|---|
| `A` | Livello di mortalità all'età 1 (componente infantile) | `[0, 0.1]` | 0.00491 | 0.00223 | 0.00054 | 0.00002 | Heligman and Pollard (1980) | tunable |
| `B` | Mortalità all'età 0 relativa all'età 1 (intercetta neonatale) | `[0, 0.5]` | 0.017 | 0.022 | 0.017 | 0.017 | Heligman and Pollard (1980) | tunable |
| `C` | Tasso di decadimento della mortalità infantile con l'età | `[0, 1.0]` | 0.102 | 0.115 | 0.125 | 0.125 | Heligman and Pollard (1980) | tunable |
| `D` | Ampiezza di picco della gobba di incidenti del giovane adulto | `[0, 0.05]` | 0.00080 | 0.00057 | 0.00013 | 0.00001 | Heligman and Pollard (1980) | tunable |
| `E` | Ampiezza inversa (acutezza) della gobba di incidenti | `[0.1, 50]` | 9.9 | 10.8 | 18.3 | 18.3 | Heligman and Pollard (1980) | tunable |
| `F` | Età su cui è centrata la gobba di incidenti (anni) | `[1.0, 50]` | 22.4 | 25.1 | 19.6 | 19.6 | Heligman and Pollard (1980) | tunable |
| `G` | Mortalità senescente all'età 0 (intercetta di Gompertz) | `[0, 0.001]` | 0.0000383 | 0.0000198 | 0.0000123 | 0.0000018 | Heligman and Pollard (1980); Gompertz (1825) | tunable |
| `H` | Tasso di crescita esponenziale della mortalità senescente con l'età | `[1.0, 1.5]` | 1.101 | 1.104 | 1.101 | 1.089 | Heligman and Pollard (1980); Gompertz (1825) | tunable |

Target di calibrazione per template: la coppia pre-industriale contro
Wrigley e Schofield (1981) tabelle A3.1-A3.3 (Inghilterra 1700-1749);
industriale contro le tavole di vita HMD pooled di Inghilterra e Galles
1841-1900; democrazia moderna contro la tavola di vita HMD USA 2019
(baseline pre-COVID); sci-fi come estrapolazione speculativa senza base
empirica (`sci_fi.json`).

**A.2 — Schedule di fertilità di Hadwiger e ceiling (§4.1.2).** I tre
parametri di Hadwiger sono definiti per equazione (4.2); i parametri del
soft ceiling malthusiano dell'equazione (4.4) portano la stessa
specifica per template.

| Parametro | Significato | Intervallo ammissibile | Pre-industriale (Cristiano/Islamico) | Industriale | Democrazia moderna | Sci-fi | Fonte | Stato |
|---|---|---|---|---|---|---|---|---|
| `H` | Total Fertility Rate target (integrale di `f_HW` sulla finestra fertile) | `[0, ~10]` | 5.0 | 4.0 | 1.8 | 2.1 | Hadwiger (1940); Wrigley and Schofield (1981) | tunable |
| `R` | Parametro di forma della fertilità di picco | `[15, 40]` | 26 | 27 | 30 | 32 | Hadwiger (1940); Chandola, Coleman and Hiorns (1999) | tunable |
| `T` | Dispersione della distribuzione di fertilità per età | `[1, 10]` | 3.5 | 3.8 | 4.2 | 4.0 | Hadwiger (1940); Chandola, Coleman and Hiorns (1999) | tunable |
| `max_population` | Cap di popolazione per il ceiling malthusiano | strutturale | 500 | 500 | 500 | 500 | Vincolo ingegneristico (budget per tick); Ashraf and Galor (2011) | heuristic |
| `malthusian_floor_ratio` (`ρ`) | Moltiplicatore del floor sulla probabilità di nascita per tick sopra il cap | `[0, 1]` | 0.10 | 0.05 | 0.01 | 0.00 | Euristica ingegneristica; Ashraf and Galor (2011) forma qualitativa | heuristic |

**A.3 — Coefficienti di modulazione di Becker per la fertilità (§4.1.2,
equazione 4.3).** I cinque coefficienti sono seedati con valori
identici su tutti e cinque i template demografici in attesa della
calibrazione del Plan 4; tracciati come debito di audit B2-07.

| Coefficiente | Significato | Valore seed (tutti i template) | Intervallo ammissibile | Fonte | Stato |
|---|---|---:|---|---|---|
| `β₀` | Shift logaritmico di base sul fattore di modulazione | 0.0 | illimitato | Ispirato da Becker (1991); scelta implementativa di Epocha | tunable |
| `β₁` | Elasticità al log-ricchezza relativa alla sussistenza | 0.10 | segno positivo | Ispirato da Becker (1991) | tunable |
| `β₂` | Penalità per unità di istruzione genitoriale | −0.05 | segno negativo | Ispirato da Becker (1991) | tunable |
| `β₃` | Penalità per unità di partecipazione femminile alla forza lavoro di zona | −0.10 | segno negativo | Ispirato da Becker (1991) | tunable |
| `β₄` | Elasticità al segnale aggregato di outlook macro | 0.20 | segno positivo | Estensione Epocha; outlook calcolato in `context.compute_aggregate_outlook()` | tunable |
| modulation clip | Bound di output su `m_BK` dopo l'esponenziazione | `[0.05, 3.0]` | strutturale | Guardia implementativa contro input degeneri | heuristic |

**A.4 — Mortalità materna al parto (§4.1.2, joint resolver).** I due
coefficienti consumati da `resolve_childbirth_event()` sono campi del
template sotto `mortality.maternal_mortality_rate_per_birth` e
`mortality.neonatal_survival_when_mother_dies`; i valori riflettono gli
intervalli storici target discussi nella spec di demografia.

| Parametro | Significato | Pre-industriale (Cristiano/Islamico) | Industriale | Democrazia moderna | Sci-fi | Fonte | Stato |
|---|---|---:|---:|---:|---:|---|---|
| `maternal_mortality_rate_per_birth` | Probabilità di morte materna per nato vivo | 0.012 | 0.005 | 0.0001 | 0.00001 | Spec di demografia (seed per template); calibrazione pendente al Plan 4 | tunable |
| `neonatal_survival_when_mother_dies` | Probabilità che il neonato sopravviva quando la madre muore al parto | 0.30 | 0.50 | 0.95 | 0.99 | Spec di demografia (seed per template); calibrazione pendente al Plan 4 | tunable |

**A.5 — Parametri di formazione delle coppie (§4.1.3).** Valori per
template per il resolver runtime e per i pesi di omogamia di Kalmijn
(1998) dell'equazione (4.6).

| Parametro | Significato | Pre-industriale Cristiano | Pre-industriale Islamico | Industriale | Democrazia moderna | Sci-fi | Fonte | Stato |
|---|---|---|---|---|---|---|---|---|
| `marriage_market_type` | `autonomous` vs `arranged` (mediato dal genitore sotto Goode 1963 Pass B) | `autonomous` | `arranged` | `autonomous` | `autonomous` | `autonomous` | Goode (1963); spec di demografia | tunable |
| `divorce_enabled` | Apre `resolve_separate_intents()` | false | true | true | true | true | Spec di demografia; indissolubilità del matrimonio cattolico per il template Cristiano | tunable |
| `implicit_mutual_consent` | Una dichiarazione unilaterale è sufficiente quando true | true | true | true | true | true | Spec di demografia | tunable |
| `min_age` (M / F) | Età minima per il check di eleggibilità (anni) | 16 / 14 | 16 / 14 | 18 / 16 | 18 / 18 | 18 / 18 | Spec di demografia; ordine di grandezza dell'attestazione storica | tunable |
| `mourning_ticks` | Cooldown dopo la morte del partner (caricato ma non ancora consumato) | 365 | 365 | 180 | 90 | 30 | Spec di demografia | tunable |
| `marriage_market_radius` | Estensione spaziale della pool di candidati | `same_zone` | `same_zone` | `adjacent_zones` | `world` | `world` | Spec di demografia; struttura spaziale ereditata da §3.6 | tunable |
| `w_class` | Peso di similarità di classe nell'equazione (4.6) | 0.40 | 0.40 | 0.35 | 0.20 | 0.10 | Kalmijn (1998); calibrazione di salienza culturale per era | tunable |
| `w_edu` | Peso di prossimità di istruzione | 0.25 | 0.25 | 0.30 | 0.40 | 0.30 | Kalmijn (1998) | tunable |
| `w_age` | Peso di prossimità d'età | 0.20 | 0.20 | 0.20 | 0.20 | 0.20 | Kalmijn (1998) | tunable |
| `w_rel` | Peso del sentimento relazionale esistente | 0.15 | 0.15 | 0.15 | 0.20 | 0.40 | Kalmijn (1998); estensione Epocha tramite `Relationship.sentiment` | tunable |
| `age_tolerance_years` (`τ`) | Scala di decadimento del kernel esponenziale di età (argomento di funzione) | 10.0 | 10.0 | 10.0 | 10.0 | 10.0 | Ordine di grandezza della letteratura demografica; promozione a campo per template riservata al Plan 4 | heuristic |

**A.6 — Parametri delle aspettative adattive (§4.2.1).** Il blocco di
configurazione delle aspettative è popolato da `_behavioral_config()` in
`template_loader.py:179-196` ed è identico in tutti e quattro i template
di economia in attesa della calibrazione del Plan 4. I bound strutturali
sono codificati come costanti di modulo in `expectations.py:39-40`.

| Parametro | Significato | Valore seed (tutti i template di economia) | Intervallo ammissibile | Fonte | Stato |
|---|---|---:|---|---|---|
| `lambda_base` | Tasso di adattamento di base prima della modulazione di personalità | 0.30 | `(0, 1)` | Cagan (1956); Nerlove (1958) | tunable |
| `neuroticism_mod` | Magnitudine del contributo positivo del Nevroticismo al `λ` per agente | 0.15 | `≥ 0` | Costa and McCrae (1992); estensione Epocha | tunable |
| `openness_mod` | Magnitudine del contributo positivo dell'Apertura al `λ` per agente | 0.10 | `≥ 0` | Costa and McCrae (1992); estensione Epocha | tunable |
| `conscientiousness_mod` | Magnitudine del contributo negativo della Coscienziosità al `λ` per agente | 0.10 | `≥ 0` | Costa and McCrae (1992); estensione Epocha | tunable |
| `trend_threshold` | Deviazione frazionaria da `expected_price` richiesta per cambiare `trend_direction` | 0.05 | `(0, 1)` | Scelta di design Epocha; tunable | tunable |
| `_LAMBDA_MIN` (strutturale) | Bound inferiore sul `λ` per agente dopo l'equazione (4.10) | 0.05 | strutturale | Guardia implementativa contro la previsione statica | heuristic |
| `_LAMBDA_MAX` (strutturale) | Bound superiore sul `λ` per agente dopo l'equazione (4.10) | 0.95 | strutturale | Guardia implementativa contro l'aspettativa naïve | heuristic |
| confidence step | Incremento/decremento per tick su `AgentExpectation.confidence` | ±0.05 | `(0, 1)` | Scelta di design Epocha; tunable | tunable |

**A.7 — Credito e sistema bancario, per era (§4.2.2).** I quattro
template di economia spediti con la app economy — pre-industriale,
industriale, modern, sci-fi — portano blocchi `credit_config` e
`banking_config` differenziati e calibrati qualitativamente contro
Homer e Sylla (2005) e la convenzione del reserve ratio di Basel III.

| Parametro | Significato | Pre-industriale | Industriale | Moderno | Sci-fi | Fonte | Stato |
|---|---|---:|---:|---:|---:|---|---|
| `loan_to_value` | Rapporto massimo prestito-valore-collaterale in (4.12) | 0.50 | 0.60 | 0.80 | 0.90 | Stiglitz and Weiss (1981); Homer and Sylla (2005) range qualitativi | tunable |
| `base_interest_rate` | Tasso di base iniziale prima dell'aggiustamento Wickselliano | 0.08 | 0.06 | 0.03 | 0.02 | Homer and Sylla (2005); Wicksell (1898) per la legge di aggiustamento | tunable |
| `initial_deposits` | Depositi seed del sistema bancario in unità di valuta primaria | 5 000 | 20 000 | 100 000 | 500 000 | Seed ingegneristico scalato per offerta monetaria di era | tunable |
| `reserve_ratio` | Riserva obbligatoria (convenzione Basel III per il moderno) | 0.10 | 0.10 | 0.05 | 0.03 | Basel III; Diamond and Dybvig (1983) | tunable |

**A.8 — Credito e sistema bancario, strutturali e uniformi (§4.2.2).**
Parametri uniformi su tutti e quattro i template in attesa della
calibrazione del Plan 4, oppure codificati come costanti a livello di
modulo perché codificano la forma qualitativa della dinamica di bank run
piuttosto che scelte di calibrazione.

| Parametro | Significato | Valore | Dove codificato | Fonte | Stato |
|---|---|---:|---|---|---|
| `risk_premium` | Coefficiente sullo spread di leverage del debitore in (4.13) | 0.50 | `credit.py:215-219`; `credit_config.risk_premium` | Stiglitz and Weiss (1981) qualitativo; magnitudine è design Epocha | tunable |
| `max_rollover` | Numero massimo di volte che un prestito a scadenza può essere rinnovato | 3 | `credit_config.max_rollover` | Minsky (1986) qualitativo; magnitudine è design Epocha | tunable |
| `default_loan_duration_ticks` | Durata di default del prestito quando il chiamante non ne passa una | 20 | `credit_config.default_loan_duration_ticks` | Scelta di design Epocha | tunable |
| `_CONCERN_CONFIDENCE_THRESHOLD` | Soglia di (4.11) sotto la quale le memorie di banking-concern sono trasmesse | 0.50 | `banking.py:334` | Diamond and Dybvig (1983) qualitativo; soglia è design Epocha | heuristic |
| `_CONCERN_BROADCAST_RATIO` | Frazione della popolazione vivente che riceve il broadcast di concern per tick | 0.50 | `banking.py:329` | Scelta ingegneristica per il budget di scrittura memoria | heuristic |
| `_CONCERN_DEDUP_TICKS` | Finestra di deduplicazione allineata al dedup memoria dell'agent engine | 3 | `banking.py:325` | Scelta ingegneristica; allineata con la costante `simulation/engine.py` | heuristic |
| `CASCADE_LOSS_THRESHOLD` | Frazione della ricchezza del prestatore sopra la quale una perdita per default si propaga | 0.50 | `credit.py:54` | Allen and Gale (2000) qualitativo | heuristic |
| cascade `max_depth` | Cap BFS sulla propagazione della cascata di default | 3 | argomento di `process_default_cascade()` | Allen and Gale (2000) diametro empirico di rete (3-5 link) | heuristic |
| rollover repricing factor | Moltiplicatore del tasso di interesse per rollover | 1.10 | `credit.py:636` | Scelta di design Epocha; raffinamento rinviato sotto §4.2.2 | tunable |
| solvency confidence step | Decremento di `confidence_index` per tick di insolvenza | −0.10 | `banking.py` `check_solvency()` | Design Epocha; osservazione di asimmetria di fiducia | heuristic |
| solvency recovery step | Incremento di `confidence_index` per tick di recupero | +0.05 | `banking.py` `check_solvency()` | Design Epocha; osservazione di asimmetria di fiducia | heuristic |
| base-rate clamp | Clamp inferiore e superiore su `base_interest_rate` dopo l'aggiustamento Wickselliano | `[0.005, 0.50]` | `banking.py:115-206` | Guardia implementativa | heuristic |

**A.9 — Mercato immobiliare (§4.2.3).** Nessun blocco di configurazione
di template per era stand-alone; i valori sono ereditati dai config di
credito e aspettative e due parametri di design del mercato immobiliare
sono codificati fuori dai template.

| Parametro | Significato | Valore | Dove codificato | Fonte | Stato |
|---|---|---:|---|---|---|
| `trend_threshold` | Deviazione frazionaria che classifica il prezzo richiesto come crescente/calante/stabile | 0.05 | ereditato da `expectations_config.trend_threshold` | Audit fix C-5 della convergenza del 2026-04-15 | tunable |
| `listing_expiration_ticks` | I listing stantii sono ritirati dopo questo numero di tick | 10 | `property_market.py:235` | Scelta di design Epocha; timescale di mercato multi-periodo | heuristic |
| Gordon denominator floor | Floor su `(r − g)` in `V = R / (r − g)` per prevenire la divisione per zero | 0.01 | `property_market.py:121-128` | Guardia implementativa contro `r ≈ g` | heuristic |
| Gordon valuation lower clip | Bound inferiore su `fundamental_value` come multiplo di `property.value` | 0.1× | `property_market.py:121-128` | Guardia implementativa contro collassi transitori dei canoni | heuristic |
| Gordon valuation upper clip | Bound superiore su `fundamental_value` come multiplo di `property.value` | 10× | `property_market.py:121-128` | Guardia implementativa; vincolo binding sulla magnitudine della bolla per log di audit della spec | heuristic |

## Appendice B — Riproducibilità

L'Appendice B registra i passi operativi tramite i quali ogni risultato
riportato in questo whitepaper può essere rigenerato da un checkout
pulito. Il riferimento che pinna lo stato del codebase per la presente
revisione è il valore del campo `frozen-at-commit` nel front matter,
popolato al momento del merge sotto la fase 7 del workflow canonico;
l'esecuzione su un commit diverso produrrà risultati che possono
differire nel dettaglio numerico anche quando il comportamento
qualitativo è preservato.

**Repository.** Il sorgente canonico è
https://github.com/mauriziomocci/epocha, mirrorato in nessun'altra
locazione pubblica. Il branch `develop` porta l'integrazione del lavoro
che ha superato tutti i gate del workflow canonico a sette fasi e la
sincronizzazione periodica del backup di memoria descritta nel CLAUDE.md
del progetto; il branch `main` è riservato alle release.

**Commit pinnato.** Il valore del campo `frozen-at-commit` in cima a
questo documento — attualmente `8a2bc714477f445b46cd610725df40c93fce1557` e risolto al merge
nello SHA del commit di integrazione — è il riferimento canonico di
riproduzione. Lo stesso placeholder appare su ciascun header `Status` in
§4 ed è popolato atomicamente alla chiusura della fase 7.

**Ambiente di runtime.** Python 3.12 con il set di dipendenze pinnato in
`requirements/base.txt` (set transitivo di baseline produzione),
`requirements/local.txt` (estensioni di sviluppo incluse pytest e
strumenti di debug), e `requirements/production.txt` (override di
produzione). PostgreSQL diretto con estensione PostGIS è richiesto per i
campi spaziali abilitati in `world.0003_zone_postgis_geometry`; Redis è
richiesto per il broker Celery e per il rate limiter LLM; il file Docker
compose `docker-compose.local.yml` impacchetta Postgres+PostGIS, Redis,
l'applicazione Django, il worker Celery e lo scheduler Celery beat con
il wiring di servizio corretto.

**Avvio dello stack da un checkout pulito.**

```bash
git clone https://github.com/mauriziomocci/epocha.git
cd epocha
git checkout <frozen-at-commit>
docker compose -f docker-compose.local.yml up --build
```

La prima invocazione costruisce l'immagine dell'applicazione ed esegue
la trail di migrazioni sotto `epocha/apps/<app>/migrations/`, applicate
linearmente senza squashing per regola di progetto. La dashboard è
esposta sulla porta host dichiarata nel file compose; le credenziali del
provider LLM devono essere configurate tramite le impostazioni
`EPOCHA_LLM_BASE_URL`, `EPOCHA_LLM_MODEL` ed `EPOCHA_LLM_API_KEY` di
`config/settings/base.py` (e i paralleli `EPOCHA_CHAT_LLM_*` per il
provider lato chat) prima che la pipeline di decisione degli agenti di
§3.2 possa dispatchare un tick.

**Invocazione dei test.**

```bash
docker compose -f docker-compose.local.yml exec web \
    pytest --cov=epocha -v
```

La suite completa copre i moduli auditati di §4.1 e §4.2 a livello di
algoritmo, i path di integrazione cross-modulo esercitati da
`epocha/apps/economy/engine.py:process_economy_tick_new()` e il
machinery a livello Django di model e serializer di ogni app sotto
`epocha/apps/`. I sottoinsiemi per modulo sono indirizzabili per path
di directory: `pytest epocha/apps/demography/ -v` per i moduli di §4.1,
`pytest epocha/apps/economy/ -v` per i moduli di §4.2.

**RNG seedato.** Per §3.4, ogni decisione stocastica nel sottosistema di
demografia attinge da uno stream `random.Random` seedato per fase
restituito da
`epocha.apps.demography.rng.get_seeded_rng(simulation, tick, phase)`,
dove `phase` è uno dell'insieme chiuso `mortality`, `fertility`,
`couple`, `migration`, `inheritance`, `initialization`. Il seed è
derivato come i primi otto byte di
`sha256(f"{simulation.id}:{simulation.seed}:{tick}:{phase}")`, così che
due esecuzioni con gli stessi `simulation.id`, `simulation.seed` e
revisione di codice producano draw per tick identici per tutta la vita
della simulazione. Riordinare o sopprimere un sottosistema in un
refactor non sposta la sequenza casuale che gli altri vedono allo stesso
tick, che è la proprietà che rende possibile la riproducibilità stabile
sotto refactor. Il debito noto A-5 documentato in §3.4 — un fallback a
`0` quando entrambi `simulation.seed` e `simulation.id` sono `None` — è
raro in pratica ed è tracciato per il Plan 4.

**Caricamento dei template di era.** Per Appendice C, i template di
demografia sono cinque file JSON sotto
`epocha/apps/demography/templates/` e i template di economia sono quattro
funzioni factory Python in `epocha/apps/economy/template_loader.py`. Il
loader di demografia (`template_loader.py`) valida ciascun file JSON
contro lo schema implicito definito dai consumatori in §4.1 — ogni
chiave è consumata da uno specifico modello e le chiavi sconosciute
sollevano un errore di validazione invece di essere silenziosamente
ignorate. Le factory di economia restituiscono un dizionario annidato
che il loader passa a `EconomyTemplate.objects.get_or_create()`; il
blocco comportamentale è costruito una sola volta da
`_behavioral_config()` ed è identico in tutti e quattro i template in
attesa della calibrazione del Plan 4. Per eseguire una simulazione sotto
uno specifico template di era, impostare i campi `Simulation.config`
corrispondenti (`demography_template`, `economy_template`) alla
creazione della simulazione tramite la dashboard o l'API di management.

**Esperimenti di validazione.** La metodologia del Capitolo 7 specifica
i dataset target (§7.1), le metriche di confronto (§7.2) e le soglie di
accettazione (§7.3); la campagna sperimentale che li consuma è
tracciata sotto
`docs/memory-backup/project_validation_experiments_pending.md` ed è
legata al Plan 4 di demografia. Il deliverable del Plan 4 introdurrà una
directory `validation/` alla radice del repository con uno script Python
per ciascun modulo auditato e un target Makefile che esegue l'intera
campagna sotto un singolo comando su un checkout pulito.

## Appendice C — Schema JSON dei template di era e sorgente

La simulazione supporta due sistemi di template paralleli la cui
esistenza è documentata in §6.2. L'Appendice C descrive la forma
on-disk di ciascun sistema senza gonfiare il documento col contenuto
JSON completo; i payload autoritativi vivono nell'albero del sorgente
ai path registrati sotto.

**C.1 — Template di demografia (JSON, cinque file).** Ciascun file sotto
`epocha/apps/demography/templates/` porta un dizionario flat con tre
blocchi top-level (`mortality`, `fertility`, `couple`) consumati dai
modelli auditati di §4.1. Lo schema implicito è stretto: ogni chiave è
consumata da una specifica funzione in `mortality.py`, `fertility.py` o
`couple.py`, e le chiavi sconosciute al load time sollevano un errore di
validazione invece di essere silenziosamente ignorate.

Il blocco `mortality` porta gli otto parametri di Heligman-Pollard
definiti per equazione (4.1) più i coefficienti di mortalità materna
consumati dal joint resolver di §4.1.2:

- `A`, `B`, `C` — parametri del decadimento infantile dell'equazione (4.1)
- `D`, `E`, `F` — parametri della gobba di incidenti
- `G`, `H` — parametri della crescita senescente di Gompertz
- `maternal_mortality_rate_per_birth` — probabilità di morte materna per
  nato vivo
- `neonatal_survival_when_mother_dies` — probabilità che il neonato
  sopravviva quando la madre muore al parto

Il blocco `fertility` porta i tre parametri di Hadwiger dell'equazione
(4.2), i cinque coefficienti di modulazione di Becker dell'equazione
(4.3) e i parametri del ceiling malthusiano dell'equazione (4.4):

- `H`, `R`, `T` — schedule di Hadwiger dell'equazione (4.2)
- `becker_beta_0` fino a `becker_beta_4` — coefficienti di Becker
- `malthusian_floor_ratio` (`ρ`) — moltiplicatore del floor del soft
  ceiling
- `max_population` — cap del ceiling malthusiano

Il blocco `couple` porta i campi del resolver runtime e i pesi di
omogamia di Kalmijn dell'equazione (4.6):

- `marriage_market_type` — `autonomous` o `arranged`
- `divorce_enabled` — apre `resolve_separate_intents()`
- `implicit_mutual_consent` — una dichiarazione unilaterale è
  sufficiente quando true
- `min_age_male`, `min_age_female` — minimi di eleggibilità in anni
- `mourning_ticks` — cooldown dopo la morte del partner (caricato ma non
  ancora consumato)
- `marriage_market_radius` — `same_zone`, `adjacent_zones` o `world`
- `homogamy_weights` — sub-blocco che porta `w_class`, `w_edu`, `w_age`,
  `w_rel` la cui somma è uno
- `allowed_types`, `default_type` — tipologia di coppia

I cinque file spediti col Plan 1 sono riassunti nella Tabella C.1.

Tabella C.1 — Template di demografia spediti col Plan 1.

| Nome del template | Path del file | Scopo di era |
|---|---|---|
| `pre_industrial_christian` | `epocha/apps/demography/templates/pre_industrial_christian.json` | Cristianità occidentale pre-industriale; target di calibrazione Wrigley and Schofield (1981) Inghilterra 1700-1749; porta l'indissolubilità del matrimonio cattolico (`divorce_enabled: false`); blocchi di mortalità e fertilità identici a `pre_industrial_islamic`, differisce solo nel blocco couple |
| `pre_industrial_islamic` | `epocha/apps/demography/templates/pre_industrial_islamic.json` | Mondo islamico pre-industriale; stesse schedule biologiche di `pre_industrial_christian`; porta il regime di matrimonio combinato (`marriage_market_type: arranged`) sotto la semantica del Pass B di Goode (1963) |
| `industrial` | `epocha/apps/demography/templates/industrial.json` | Transizione industriale; target di calibrazione HMD Inghilterra e Galles pooled 1841-1900; raggio del mercato matrimoniale ampliato a `adjacent_zones` riflettendo l'urbanizzazione |
| `modern_democracy` | `epocha/apps/demography/templates/modern_democracy.json` | Democrazia liberale moderna; target di calibrazione HMD USA 2019 (baseline pre-COVID); raggio del mercato matrimoniale `world` riflettendo la mobilità moderna |
| `sci_fi` | `epocha/apps/demography/templates/sci_fi.json` | Template speculativo di lontano futuro; nessun target empirico di calibrazione; documentato inline nel sorgente come speculativo |

**C.2 — Template di economia (factory Python, quattro funzioni).** Ogni
factory sotto `epocha/apps/economy/template_loader.py` restituisce un
dizionario annidato che il loader passa a
`EconomyTemplate.objects.get_or_create()`. Il pattern factory è stato
scelto rispetto a file JSON per template sulla base del fatto che la
differenziazione per era si riduce a un piccolo insieme di input
(tabella valuta, elasticità di beni, stock di fattori, configurazione
comportamentale) e la factory Python espone questi input come argomenti
denominati in modo più leggibile di quanto farebbero quattro file JSON
paralleli. Il blocco comportamentale è costruito una sola volta da
`_behavioral_config()` ed è identico in tutti e quattro i template in
attesa della calibrazione del Plan 4.

Tabella C.2 — Template di economia spediti con la app economy.

| Nome del template | Funzione factory | Scopo |
|---|---|---|
| `pre_industrial` | `_pre_industrial_template()` (`epocha/apps/economy/template_loader.py`) | Economia agraria pre-industriale; porta la tipologia canonica di proprietà farmland-workshop-shop, basso loan-to-value di 0.50, tasso di interesse di base 0.08 calibrato contro Homer and Sylla (2005) per il range pre-moderno |
| `industrial` | `_industrial_template()` | Transizione industriale; aggiunge il tipo di proprietà factory a base value 500; loan-to-value 0.60; tasso di interesse di base 0.06 |
| `modern` | `_modern_template()` | Economia moderna ancorata alla banca centrale; aggiunge il tipo di proprietà office a base value 300; loan-to-value 0.80; tasso di interesse di base 0.03; reserve ratio 0.05 calibrato contro la convenzione Basel III |
| `sci_fi` | `_sci_fi_template()` | Template speculativo di lontano futuro; aggiunge automated factory a base value 1 000 e research lab a base value 800; loan-to-value 0.90; tasso di interesse di base 0.02; reserve ratio 0.03 |

Il blocco condiviso `_behavioral_config()` a `template_loader.py:144-198`
popola i sub-blocchi `expectations_config`, `credit_config` e
`banking_config` consumati dai moduli auditati di §4.2. La
differenziazione per era di `λ_base`, dei coefficienti di modulazione di
Becker, di `risk_premium`, `max_rollover` e
`default_loan_duration_ticks` è il debito esplicito di calibrazione
assegnato al Plan 4. La discrepanza nel conteggio fra cinque template di
demografia e quattro template di economia è documentata in §6.2: la
spec di demografia ha richiesto di separare i due regimi confessionali
pre-industriali per supportare la distinzione di mercato matrimoniale e
regime di divorzio, mentre la spec di economia non ha trovato analoga
distinzione strutturale al layer di prezzo e credito.

**C.3 — Caricamento e validazione.** Entrambi i sistemi di template sono
caricati al tempo di creazione della simulazione attraverso i moduli
`template_loader.py` nelle rispettive app. Il loader di demografia
valida il JSON contro lo schema implicito tentando di costruire ciascun
oggetto parametri del modello e rifiutando il caricamento con un
`ValueError` descrittivo quando un campo richiesto è mancante o un
valore cade fuori dall'intervallo ammissibile documentato in Appendice
A. Il loader di economia svolge lo stesso ruolo per l'output della
factory Python, con la differenza che la factory stessa controlla il
dizionario prodotto e un output di factory malformato indica un bug
nella factory piuttosto che un file JSON corrotto. La disciplina di
validazione stretta è la proprietà che rende auditabile la
differenziazione per era: un typo in un campo di template è catturato
alla creazione della simulazione invece di produrre comportamento
silenziosamente scorretto per tick a valle.

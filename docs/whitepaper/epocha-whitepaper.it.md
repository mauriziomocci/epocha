---
title: "Epocha — Un Simulatore di Civiltà Scientificamente Fondato"
authors: ["Maurizio Mocci"]
affiliation: "Independent project"
date: "2026-04-26"
version: "0.1"
frozen-at-commit: "<filled-on-merge>"
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
economico, modello di persistenza, dashboard e strato di chat), sei moduli
scientifici auditati — mortalità di Heligman-Pollard, fertilità Hadwiger
con Becker, formazione di coppia Gale-Shapley con Goode 1963, aspettative
adattive Cagan-Nerlove, credito e banca Diamond-Dybvig e mercato
immobiliare ancorato a Gordon — e otto sottosistemi implementati in codice
ma in attesa dell'audit scientifico avversariale di Round 2 (propagazione
delle voci, istituzioni politiche, movimento, fazioni, reputazione,
knowledge graph, layer economico di base). Ogni formula, parametro e
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
stato). Il Capitolo 8 elenca i sottosistemi che sono implementati ma il
cui audit avversariale è ancora pendente. Il Capitolo 9 espone la roadmap,
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
Castelfranchi-Conte-Paolucci ed è trattato come voce dei Metodi differita
in attesa dell'audit di Round 2; è documentato nel Capitolo 8.5 insieme
ai cluster di voci e flusso informativo che attingono alla tradizione
Allport-Postman e Bartlett.

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
| Treasury credit | `add_to_treasury(government, currency_code, amount)` in `epocha/apps/world/government.py` | Aggiunge `amount` di `currency_code` a `government.government_treasury` (una mappa JSON da codice di valuta a saldo) e persiste la riga. | Chiamato da `epocha/apps/economy/engine.py` (tassazione) e dalla logica di eredità/imposta di successione nel sottosistema demografico; implementato in `world/government.py`. |
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

Questo sottosistema è documentato in questo capitolo e non in §4 Metodi
perché non ha ancora completato un audit scientifico avversariale di
Round 2. I puntatori alla letteratura sopra sono descrittivi delle
famiglie di modelli implementati e delle citazioni delle fonti registrate
all'interno dei moduli stessi, non asserzioni di fedeltà verificata di
livello Metodi: diverse costanti sono esplicitamente etichettate come
parametri di design tunabili nel sorgente (il rate di aggiustamento del
tâtonnement, il rapporto massimo di prezzo, il cap discrezionale di
domanda, le soglie di sazietà dell'umore, la profondità di cascata di
default) e i loro valori numerici non hanno ancora la catena di citazioni
linea per linea richiesta dallo stato §4. Lo strato auditato che siede
sopra questo sostrato è l'integrazione comportamentale descritta in §4.2:
quell'integrazione consuma i prezzi, gli scambi e i flussi di reddito
prodotti dal sostrato e aggiunge le aspettative adattive, il
satisficing e il feedback politico che hanno passato il Round 2.

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

<da tradurre nel Task 33>

---

# 5. Implementazione

<da tradurre nel Task 34>

---

# 6. Calibrazione

<da tradurre nel Task 34>

---

# 7. Metodologia di validazione

<da tradurre nel Task 34>

---

# 8. Sottosistemi progettati (implementati, audit pendente)

<da tradurre nel Task 35>

---

# 9. Roadmap

<da tradurre nel Task 35>

---

# 10. Discussione

<da tradurre nel Task 36>

---

# 11. Limitazioni note

<da tradurre nel Task 36>

---

# 12. Conclusioni

<da tradurre nel Task 36>

---

# 13. Riferimenti

<da tradurre nel Task 37 — mirror verbatim della §13 del whitepaper inglese>

---

# 14. Appendici

<da tradurre nel Task 37>

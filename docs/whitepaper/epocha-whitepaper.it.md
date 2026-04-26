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

## 4.1 Demografia

> Stato: implementato a partire dal commit `<filled-on-merge>`, audit della spec CONVERGENTE 2026-04-18 round 4.

Il modulo demografia copre le tre transizioni del corso di vita per le quali Epocha esegue attualmente un modello scientifico auditato: mortalità, fertilità e formazione delle coppie. La specifica autoritativa è `docs/superpowers/specs/2026-04-18-demography-design.md`, i cui quattro round di revisione adversariale sono convergiti il 2026-04-18; le scelte di design e la mappatura esplicita di ogni parametro a una fonte primaria vivono lì, mentre questo capitolo riformula le formule, le tabelle di calibrazione e gli algoritmi per-tick in forma di pubblicazione. L'implementazione vive sotto `epocha/apps/demography/`, dove i tre sottosistemi sono separati in `mortality.py`, `fertility.py` e `couple.py`, con preoccupazioni condivise fattorizzate in `template_loader.py` (caricamento e validazione JSON delle ere), `rng.py` (stream seedati per fase discussi nel Capitolo 3.4), `context.py` (helper di integrazione verso l'economia) e `models.py` (lo stato demografico persistito). L'intento di design è che all'interno di ogni tick i tre sottosistemi vengano eseguiti nell'ordine mortalità → fertilità → formazione delle coppie, ognuno attingendo dal proprio stream RNG seedato così che l'ordine possa essere ragionato senza accoppiamento alla sequenza casuale; la mortalità materna al parto è l'unico accoppiamento inter-sottosistema ed è risolta congiuntamente tra mortalità e fertilità prima che entrambi registrino il loro esito, come dettagliato in §4.1.2. A partire dal commit fissato nel front matter, i modelli di mortalità e fertilità e l'infrastruttura delle coppie sono implementati e unit-testati in isolamento; la loro orchestrazione nel ciclo di tick della simulazione live in `epocha/apps/simulation/engine.py` è tracciata come deliverable del Plan 4 (Inizializzazione, integrazione del motore e validazione storica) e non è ancora attiva nel codice di produzione.

### 4.1.1 Modello di mortalità (Heligman-Pollard)

> Stato: implementato a partire dal commit `<filled-on-merge>`, audit della spec CONVERGENTE 2026-04-18 round 4.

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

> Stato: implementato a partire dal commit `<filled-on-merge>`, audit della spec CONVERGENTE 2026-04-18 round 4.

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

**Algoritmo.** Per ogni agente femminile vivo nella finestra fertile `[12, 50]`, ad ogni tick, il modulo di fertilità prima controlla le precondizioni di gating in `tick_birth_probability()` (righe 180–191): se il template di era richiede appartenenza a una coppia e la madre non è in una coppia attiva (`is_in_active_couple()`), o se il flag `avoid_conception` su `AgentFertilityState` è stato impostato al tick `T−1` (`is_avoid_conception_active_this_tick()`, riga 262), la funzione restituisce 0 e nessuna nascita può attivarsi questo tick. Altrimenti i tre strati sono valutati in sequenza: `hadwiger_asfr()` viene chiamata sull'età dell'agente in anni (calcolata in `_effective_age_in_years()` da `birth_tick` e dal `current_tick` autoritativo per evitare la staleness della FK-cache segnalata dal finding B2-04 dell'audit), il risultato è moltiplicato per `becker_modulation()` valutato contro la ricchezza, l'istruzione, la zona e l'outlook dell'agente, il prodotto è passato attraverso `malthusian_soft_ceiling()` contro la popolazione corrente e `max_population`, e il tasso annuale risultante è moltiplicato per `Δt` per dare la probabilità per-tick. Il chiamante estrae una variata uniforme da un `random.Random` restituito da `epocha.apps.demography.rng.get_seeded_rng(simulation, tick, phase="fertility")` — lo stesso contratto di stream seedato documentato per la mortalità in §4.1.1, con `phase="fertility"` selezionato dal set di fasi chiuso così che l'estrazione di fertilità non sposti mai la sequenza casuale che l'estrazione di mortalità allo stesso tick ha consumato. Quando una nascita si attiva e si applica la mortalità materna, il fix C-1 della §1 della spec richiede che i due eventi siano risolti congiuntamente piuttosto che sequenzialmente: `resolve_childbirth_event(mother, params_era, tick, rng)` (`fertility.py:295`) estrae contro `mortality.maternal_mortality_rate_per_birth` per l'evento di morte materna e, condizionalmente alla morte della madre, contro `mortality.neonatal_survival_when_mother_dies` per la sopravvivenza del neonato; l'helper è un risolutore probabilistico puro e restituisce un dict `{mother_died, newborn_survived, death_cause}` con `death_cause = "childbirth"` quando viene selezionata la morte materna, lasciando la persistenza (record di morte della madre, creazione del neonato) al chiamante. La risoluzione congiunta evita il bias che sorgerebbe risolvendo la mortalità generica per prima e la mortalità da parto per seconda sulla stessa madre nello stesso tick. A partire dal commit fissato, questa valutazione di fertilità per-tick è esercitata dalla suite di unit test della demografia (`epocha/apps/demography/tests/test_fertility.py`) ma non è ancora invocata da `epocha/apps/simulation/engine.py` o `tasks.py`; l'unica menzione di `tick_birth_probability` fuori da `demography/` è un commento in `engine.py:276` che descrive la semantica di gating del flag `avoid_conception`. L'integrazione nel ciclo di tick live è tracciata, accanto al gap di mortalità equivalente notato in §4.1.1, come deliverable del Plan 4 (Inizializzazione, integrazione del motore e validazione storica).

**Semplificazioni.** L'implementazione attuale omette deliberatamente quattro raffinamenti che la letteratura demografica tratta come estensioni proprie piuttosto che correzioni della scheda baseline. Primo, la scheda specifica per età di Hadwiger è valutata deterministicamente sull'età dell'agente, senza eterogeneità inter-individuale nella fecondità biologica sottostante oltre i flag binari portati da `AgentFertilityState`; modellare eterogeneità lognormale nel time-to-conception (la letteratura sui determinanti prossimali rivista nella spec di demografia) è rinviato. Secondo, le nascite gemellari e di ordine superiore non sono modellate: ogni evento di nascita riuscita crea esattamente un neonato, indipendentemente dai tassi storici di nascite multiple che variano da circa l'1% nell'Europa pre-industriale a oltre il 3% in alcune popolazioni moderne. Terzo, i coefficienti di modulazione di Becker sono omogenei in tutti e cinque i template di era, come documentato nella Tabella 4.4 e tracciato come debito di audit B2-07; la calibrazione per-era è il deliverable centrale del Plan 4 e sostituirà i valori seed con stime era-specifiche da test sintetici di shock contro la baseline di Wrigley e Schofield (1981) e i riferimenti aggiuntivi sul declino della fertilità catalogati nella spec di demografia. Quarto, il soffitto soft Malthusiano è una euristica di ingegneria piuttosto che un'implementazione letterale del formalismo del controllo preventivo di Ashraf e Galor (2011), che opera in tempo continuo sul reddito pro capite; il soffitto Epocha è uno scaling discreto basato sul tick sulla probabilità di nascita per-madre che preserva la forma qualitativa del controllo preventivo (libero sotto l'80% del cap, rampa a zero tra l'80% e il 100%, floor sopra il cap) senza pretendere di riprodurre le dinamiche di reddito di Ashraf-Galor. La scelta è documentata nel docstring di `malthusian_soft_ceiling()` (`fertility.py:118–145`) ed è coerente con l'intento di design di dare alla simulazione un feedback di densità di popolazione che protegge il budget computazionale per-tick rimanendo interpretabile in termini Malthusiani.

### 4.1.3 Formazione e dissoluzione delle coppie (Gale-Shapley + Goode 1963)

> Stato: implementato a partire dal commit `<filled-on-merge>`, audit della spec CONVERGENTE 2026-04-18 round 4.

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

Il parametro `age_tolerance_years` `τ` dell'equazione (4.6) è mantenuto al valore di default `10.0` in tutti i template, come argomento di funzione di `homogamy_score()` piuttosto che come campo per-template; sollevarlo nello schema del template è documentato come deliverable di calibrazione del Plan 4.

**Algoritmo.** Tre operazioni coordinate compongono il ciclo di vita della coppia. All'inizializzazione, il builder della popolazione fondatrice chiama `stable_matching(proposers, respondents, score_fn)` una volta con `score_fn = lambda p, r: homogamy_score(p, r, era_weights)` e le sottopopolazioni adulte eleggibili come i due lati; ogni coppia `(p, r)` restituita viene poi instradata attraverso `form_couple()` per materializzare la riga del database con l'invariante di ordinamento canonico imposto. A runtime, lo step di demografia chiama `resolve_pair_bond_intents(simulation, tick, rng)` una volta per tick, che legge le entry `DecisionLog` scritte al tick `T-1` con il pre-filtro SQL `__contains` `'"pair_bond"'` e verifica ogni match con `json.loads()`, esegue l'ingestione a due passaggi (intenti diretti nel Pass A, intenti combinati `for_child` nel Pass B con override di priorità del figlio), e crea coppie in ordine deterministico ordinato per id sotto un singolo `transaction.atomic()`. Una coppia in cui uno dei partner è già in una coppia attiva — controllato da `is_in_active_couple()` contro il vincolo unique-active-couple che il fix B2-01 ha aggiunto — viene saltata, così le coppie attive duplicate non possono essere create anche sotto invocazioni ripetute del risolutore o chord worker. Il risolutore companion `resolve_separate_intents(simulation, tick)` legge le entry `DecisionLog` `'"separate"'` dal tick `T-1` con lo stesso pattern JSON, restituisce immediatamente quando il template di era ha `divorce_enabled: false`, e altrimenti marca la coppia attiva di ogni dichiarante come `dissolved_at_tick = tick`, `dissolution_reason = 'separate'`. La terza operazione, `dissolve_on_death(deceased_agent, tick)` in `couple.py:369-392`, è invocata dal percorso di risoluzione della mortalità quando muore un agente accoppiato: annulla la FK appropriata (`agent_a` o `agent_b` a seconda del lato in cui era il deceduto), cattura il nome del deceduto nel campo `*_name_snapshot` corrispondente così che il record genealogico sopravviva al cascade FK, imposta `dissolution_reason = 'death'`, e persiste con un singolo save `update_fields=[...]`. A partire dal commit fissato, questo percorso di dissoluzione è una normale chiamata di funzione piuttosto che un signal handler Django — la spec ha considerato un segnale `agents.Agent` `post_save` in ascolto sulle transizioni `is_alive` e l'ha respinto sulla base che i segnali aggiungono accoppiamento nascosto e sono più difficili da auditare di un'invocazione esplicita dal modulo di mortalità. Il ciclo di vita della coppia è esercitato dalla suite di unit test della demografia (`epocha/apps/demography/tests/test_couple.py`) ma, coerentemente con il gap notato in §4.1.1 e §4.1.2, nessuna di `stable_matching()`, `resolve_pair_bond_intents()`, `resolve_separate_intents()` o `dissolve_on_death()` è invocata da `epocha/apps/simulation/engine.py` o `epocha/apps/simulation/tasks.py` a partire dal commit fissato (un `grep` per i nomi delle funzioni fuori da `epocha/apps/demography/` restituisce solo commenti in `engine.py:265-272` che descrivono la semantica di risoluzione tick+1 e il ruolo dell'azione `pair_bond` nella pipeline di decisione). L'integrazione nel ciclo di tick live è tracciata accanto ai gap equivalenti di mortalità e fertilità come deliverable del Plan 4 (Inizializzazione, integrazione del motore e validazione storica).

**Semplificazioni.** L'implementazione attuale omette deliberatamente quattro raffinamenti che la letteratura di demografia familiare tratta come estensioni proprie piuttosto che correzioni del meccanismo baseline. Primo, sono rappresentabili solo coppie monogamiche: il modello `Couple` porta esattamente due foreign key, e la spec registra i tipi di coppia poliginici e poliandrici come rinviati (fix audit MISS-8) perché supportare più di due partner richiederebbe di rilassare il vincolo `unique_active_couple` e rilavorare il percorso di risoluzione di eredità; l'enum `couple_type` espone `monogamous` e `arranged` come i due valori canonici, con `arranged` che indica il percorso di formazione (mediato dai genitori) piuttosto che una distinzione sul numero dei partner. Secondo, lo strato agente porta tre valori di genere (`male`, `female`, `non_binary`) e quattro valori di orientamento sessuale (`heterosexual`, `homosexual`, `bisexual`, `asexual`) in `agents/models.py:11-20`, ma il punteggio di omogamia e l'algoritmo di abbinamento stabile delle equazioni (4.6) e (4.7) non consumano questi campi a partire dal commit fissato: il filtraggio dei candidati per genere e orientamento è responsabilità del chiamante che costruisce le liste `proposers` e `respondents`, e il builder della popolazione fondatrice che esegue quel filtraggio per configurazioni non eterosessuali o non binarie è esso stesso parte del deliverable di inizializzazione del Plan 4. Terzo, nessun cooldown di rimaritamento è imposto oltre il campo per-era `mourning_ticks` riportato nella Tabella 4.5: il campo è caricato dal template ma non ancora consumato da alcun percorso di codice, quindi un agente vedovo può in principio ri-accoppiarsi al tick successivo alla morte del partner; cablare `mourning_ticks` nel controllo di eleggibilità di `resolve_pair_bond_intents()` è una modifica di una riga riservata al Plan 4. Quarto, Gale-Shapley è applicato solo all'inizializzazione, non come fallback a runtime quando si accumula una grande coorte non abbinata: il meccanismo per-tick è esclusivamente guidato dall'intento, sull'assunzione che gli agenti LLM dichiareranno intenti `pair_bond` a un tasso coerente con il mercato matrimoniale della popolazione; se la suite di validazione del Capitolo 7 rivela una sotto-formazione sistematica, una riapplicazione periodica della primitiva di abbinamento sugli adulti eleggibili non abbinati è l'estensione naturale ed è documentata nella spec di demografia sotto la voce Limitazioni note.



## 4.2 Economia — Integrazione comportamentale

> Stato: implementato a partire dal commit `<filled-on-merge>`, audit della spec CONVERGENTE 2026-04-15.

Il Capitolo 4.2 documenta lo strato comportamentale che si appoggia sul substrato economico di §3.6. Il substrato di §3.6 è la parte del modello che non dipende dalla psicologia dell'agente: possiede la tecnologia di produzione, gli aggregati monetari, il clearing Walrasiano dei mercati a tick singolo e la distribuzione per-tick dell'output in salari, rendite e tasse. Tre famiglie di comportamento — aspettative di prezzo backward-looking, dinamiche intertemporali di credito e bilancio bancario, e mercato immobiliare ancorato a Gordon — sono state specificate nel design economy-behavioral-integration del 2026-04-15 e auditate fino a convergenza sotto quel documento. Ogni famiglia è implementata in un singolo modulo Python sotto `epocha/apps/economy/`: `expectations.py` per il motore di aspettative adattive di Nerlove (1958) descritto in §4.2.1, `credit.py` e `banking.py` per la macchina credito-e-banca a riserva frazionaria di Diamond-Dybvig (1983) descritta in §4.2.2, e `property_market.py` per il mercato immobiliare con valutazione Gordon e settlement a tick `T+1` descritto in §4.2.3. I tre moduli sono cablati nel tick economico canonico orchestrato da `epocha/apps/economy/engine.py:process_economy_tick_new()`, che è esso stesso dispatched dal ciclo di tick della simulazione in `epocha/apps/simulation/engine.py:354` ogniqualvolta la simulazione ha il nuovo data layer economico inizializzato; di conseguenza, a differenza dei moduli di demografia di §4.1.x, l'economia comportamentale descritta in questo capitolo è genuinamente live nella pipeline per-tick a partire dal commit fissato, e gli header `Stato` portati da §4.2.1–§4.2.3 registrano solo la data di convergenza dell'audit della spec piuttosto che un caveat di integrazione pendente.

### 4.2.1 Aspettative adattive (Cagan 1956)

> Stato: implementato a partire dal commit `<filled-on-merge>`, audit della spec CONVERGENTE 2026-04-15.

**Background.** Le aspettative adattive entrano nella pipeline di tick di Epocha perché lo strato di decisione guidato da LLM ha bisogno di un forecast per-agente dei prezzi del prossimo tick per ogni bene scambiabile, e la famiglia di forecast che il modello richiede deve essere esprimibile in tre proprietà concrete: deve essere locale — ogni agente ha il proprio forecast, persistito tra i tick — così che personalità e storia possano spostarlo; deve essere definita sotto razionalità limitata — gli agenti non conoscono il vero processo che genera i dati — così che il forecast possa essere sbagliato in modi che il modello può studiare piuttosto che imporre coerenza con aspettative razionali per costruzione; e deve essere computabile in `O(n_agents · n_goods)` per tick senza risolvere un punto fisso, dato che la pipeline di tick porta già il tatonnement Walrasiano di §3.6 e una seconda ottimizzazione annidata dominerebbe il costo. L'alternativa canonica delle aspettative razionali Muthiane (1961) è stata respinta sul secondo e terzo conto: richiede che ogni agente conosca il processo stocastico congiunto di tutti i prezzi e internalizzi il modello che il modellatore sta usando, cosa che né l'LLM né la pipeline di decisione modulata dalla personalità di §3.2 possono fornire, e richiederebbe una risoluzione di punto fisso per-tick su credenze eterogenee che è incompatibile con l'inviluppo di costo. La famiglia delle aspettative adattive — formalizzata per la prima volta da Cagan (1956) per il forecasting dell'iperinflazione e indipendentemente da Nerlove (1958) nella letteratura del modello cobweb per l'offerta agricola — risolve tutti e tre i vincoli con un singolo aggiornamento ricorsivo parametrizzato da un tasso di adattamento `λ ∈ (0, 1)`: i forecast sono locali perché ogni agente porta il proprio stato, bounded-rational perché la regola di aggiornamento non richiede di conoscere il vero processo, e `O(1)` per agente per bene per tick perché la ricorsione sostituisce l'ottimizzazione. L'implementazione fissata trascrive la forma di Nerlove della ricorsione (l'espressione del manuale che appare nelle derivazioni del teorema cobweb) e accredita Nerlove (1958) nel docstring del modulo di `epocha/apps/economy/expectations.py:1-23`; la genealogia di Cagan (1956) è riconosciuta in §2.4 di questo whitepaper e rimane l'ancora più vecchia per l'interpretazione di forecasting dell'inflazione della stessa ricorsione. I due paper descrivono la stessa regola di aggiornamento sottostante espressa in forme equivalenti, e la scelta di attribuzione a livello di commento di codice riflette l'applicazione in stile cobweb (forecast prezzo-per-bene) piuttosto che un disaccordo sostantivo con la formulazione di Cagan.

**Modello.** Ogni agente mantiene, per ogni categoria di bene nella simulazione, una riga del modello `AgentExpectation` dichiarato in `epocha/apps/economy/models.py:506-559` che porta un `expected_price`, una categoria `trend_direction ∈ {rising, falling, stable}`, uno scalare `confidence ∈ [0, 1]`, e il `lambda_rate` per-agente effettivamente usato per l'aggiornamento al tick precedente (così che il valore sia auditabile piuttosto che ricomputato on demand). La ricorsione che aggiorna `expected_price` tra i tick è la regola canonica delle aspettative adattive:

```
E_{t+1}[p] = λ · p_t + (1 − λ) · E_t[p]                         (4.9)
```

L'equazione (4.9) è l'implementazione dell'espressione interna in `update_agent_expectations()` a `epocha/apps/economy/expectations.py:205-207`, dove `p_t` è il prezzo di mercato effettivo al tick `t` per il bene nella zona dell'agente (letto da `ZoneEconomy.market_prices` popolato dal tick precedente del substrato di §3.6) e `E_t[p]` è il prezzo atteso precedente dell'agente per lo stesso bene. Il paper sull'iperinflazione di Cagan (1956) scrive lo stesso aggiornamento nella forma equivalente di correzione dell'errore `E_{t+1}[π] = E_t[π] + λ · (π_t − E_t[π])`, che è algebricamente identica alla (4.9) dopo un riarrangiamento di una riga; l'implementazione ha scelto la forma a combinazione convessa perché non richiede di materializzare l'errore di previsione come variabile intermedia. Il tasso di adattamento `λ` per-agente è esso stesso una funzione del vettore di personalità Big Five dell'agente piuttosto che un singolo scalare fissato sulla popolazione, che è l'estensione sostantiva di Epocha della ricorsione da manuale. La modulazione di personalità, implementata in `compute_lambda_from_personality()` (`expectations.py:42-79`), è una deviazione lineare dal `λ_base` del template di era centrata sulla media di popolazione di 0.5 per ogni tratto:

```
λ(agent) = clip( λ_base
               + (N(agent) − 0.5) · n_mod
               + (O(agent) − 0.5) · o_mod
               − (C(agent) − 0.5) · c_mod ,
               0.05, 0.95 )                                     (4.10)
```

L'equazione (4.10) legge `N`, `O`, `C` come i punteggi di Neuroticismo, Apertura e Coscienziosità dell'agente dal vettore di personalità (con default alla media di popolazione di 0.5 quando il tratto è mancante) e applica i tre coefficienti di modulazione `n_mod`, `o_mod`, `c_mod` dal blocco `expectations_config` del template di era. I segni dei tre contributi seguono Costa e McCrae (1992): alto Neuroticismo aumenta la reattività ai nuovi segnali di prezzo (contributo positivo), alta Apertura aumenta la ricettività al cambiamento (contributo positivo), e alta Coscienziosità ancora il forecast all'aspettativa precedente (contributo negativo). Il clip a `[0.05, 0.95]` dichiarato come costanti strutturali `_LAMBDA_MIN` e `_LAMBDA_MAX` a `expectations.py:38-39` è documentato nel modulo come bound strutturale non-tunable piuttosto che come parametro libero: a `λ = 0.05` il forecast è essenzialmente statico (l'aspettativa precedente è preservata con peso trascurabile sulla nuova osservazione), e a `λ = 0.95` il forecast collassa a un'aspettativa naive (il prezzo del prossimo tick uguale al prezzo dell'ultimo tick); entrambi gli estremi sono degeneri come aspettative adattive e il clip impedisce a una sfortunata combinazione di punteggi di personalità e coefficienti di modulazione di portare un agente in uno dei due limiti. Il campo `trend_direction` è aggiornato dall'helper `detect_trend(expected, actual, threshold)` (`expectations.py:82-106`), che classifica il movimento da `expected` ad `actual` come `rising` quando `actual > expected · (1 + threshold)`, come `falling` quando `actual < expected · (1 − threshold)`, e come `stable` altrimenti; la soglia è il campo `trend_threshold` dell'`expectations_config` del template di era (default `0.05`, identico in tutti e cinque i template del Plan 1), ed è un parametro di design tunabile piuttosto che un valore derivato da uno specifico studio empirico. Il campo `confidence` è incrementato di `+0.05` quando l'aspettativa precedente dell'agente era entro `trend_threshold` dal prezzo realizzato e decrementato di `−0.05` altrimenti, clampato a `[0, 1]` (`expectations.py:213-224`); lo step `±0.05` è anch'esso un parametro di design tunabile ed è documentato inline come tale.

**Parametri.** Tutti e cinque i template di era spediti con il Plan 2 portano lo stesso blocco `expectations_config`, popolato da `_behavioral_config()` in `epocha/apps/economy/template_loader.py:179-196`. I valori sono seedati da una singola fonte nel loader piuttosto che inscritti ridondantemente in cinque file JSON perché nessuna delle evidenze di calibrazione del Plan 2 auditate ha motivato una differenziazione era-specifica al momento in cui i template sono stati congelati; la differenziazione per-era di `λ_base` e dei coefficienti di modulazione è un deliverable di calibrazione del Plan 4. La Tabella 4.7 registra i valori seed esplicitamente così che l'omogeneità sia visibile al lettore.

Tabella 4.7 — Parametri delle aspettative adattive seedati da `_behavioral_config()` (identici in tutti e cinque i template del Plan 1 in attesa della calibrazione del Plan 4).

| Parametro             | Valore seed | Ruolo semantico                                                            |
|-----------------------|------------:|----------------------------------------------------------------------------|
| `lambda_base`         |        0.30 | Tasso di adattamento di baseline prima della modulazione di personalità    |
| `neuroticism_mod`     |        0.15 | Magnitudine del contributo positivo del Neuroticismo al `λ` per-agente     |
| `openness_mod`        |        0.10 | Magnitudine del contributo positivo dell'Apertura al `λ` per-agente        |
| `conscientiousness_mod` |      0.10 | Magnitudine del contributo negativo della Coscienziosità al `λ` per-agente |
| `trend_threshold`     |        0.05 | Deviazione frazionale da `expected_price` richiesta per cambiare `trend_direction` |

I bound strutturali `_LAMBDA_MIN = 0.05` e `_LAMBDA_MAX = 0.95` sull'output per-agente di (4.10) non sono nella Tabella 4.7 perché sono codificati come costanti in `expectations.py:38-39` piuttosto che come campi del template, sulla base che un bound strutturale che impedisce forecast degeneri è una proprietà del modello piuttosto che una scelta di calibrazione.

**Algoritmo.** Ad ogni tick, l'orchestratore dell'economia invoca `update_agent_expectations(simulation, tick)` (`expectations.py:109-249`) prima del market clearing, così che i forecast per-agente che il substrato di §3.6 consulta durante il clearing riflettano i prezzi realizzati del tick precedente piuttosto che i prezzi che vengono calcolati al tick corrente. La funzione legge l'`expectations_config` a livello di simulazione popolato al tempo del caricamento del template, materializza la mappa di prezzi effettivi aggregando `ZoneEconomy.market_prices` su tutte le zone con un merge last-write-wins (una semplificazione single-zone documentata inline come target di raffinamento multi-zone), e fa bulk-fetch delle righe `AgentExpectation` esistenti per la simulazione in un singolo dizionario chiavato per `(agent_id, good_code)` così che il loop per-agente giri senza query N+1. Per ogni agente vivo il `λ` per-tick è calcolato una volta dalla personalità dell'agente e dai coefficienti di modulazione dell'era, poi per ogni bene con un prezzo effettivo la funzione o crea una nuova `AgentExpectation` inizializzata al prezzo realizzato con `confidence = 0.5` e `trend_direction = "stable"` (prima osservazione) o aggiorna una riga esistente applicando la (4.9) con il `λ` per-agente, chiamando `detect_trend()` contro l'aspettativa precedente e il nuovo prezzo realizzato, e aggiustando `confidence` con la regola di errore di previsione. Le righe appena create e aggiornate sono flushate in due chiamate terminali `bulk_create` e `bulk_update` così che l'intera passata sia due scritture per tick indipendentemente dal conteggio degli agenti. Lo step dell'orchestratore in `engine.py:152-156` registra la chiamata nel ciclo economico canonico a 9 step come `STEP 0: EXPECTATIONS UPDATE (Nerlove adaptive)`, e il call site è raggiunto incondizionatamente ogniqualvolta `process_economy_tick_new()` è dispatched dal motore di simulazione, che esso stesso è dispatched ogniqualvolta la simulazione ha i record `Currency` che marcano il nuovo data layer economico come inizializzato (`epocha/apps/simulation/engine.py:350-358`). Di conseguenza, in contrasto con i moduli di demografia di §4.1.x, il motore di aspettative adattive descritto qui è genuinamente attivo nel ciclo di tick live a partire dal commit fissato, e le righe `AgentExpectation` per-tick che produce sono consumate downstream dal context builder dell'LLM in `epocha/apps/economy/context.py:162-188` per renderizzare il blocco di valutazione dei prezzi dell'agente al momento della decisione.

**Semplificazioni.** L'implementazione attuale omette deliberatamente quattro raffinamenti che la letteratura sulle aspettative adattive tratta come estensioni proprie piuttosto che correzioni della ricorsione baseline. Primo, viene fatto forecast solo del livello di prezzo per ogni bene; la ricorsione è single-variable per bene, e non c'è un forecast congiunto tra beni, nessun forecast di inflazione come variabile separata distinta dal forecast di prezzo per-bene, e nessun forecast di secondo momento (volatilità, dispersione). L'applicazione originale di Cagan (1956) all'iperinflazione fa forecast del tasso di inflazione `π` piuttosto che del livello di prezzo `p`, e l'implementazione Epocha potrebbe essere estesa a un forecast di inflazione derivato avvolgendo la ricorsione di prezzo per-bene in una log-differenza tick-su-tick; la spec registra questo come raffinamento rinviato sotto il log di risoluzione audit del documento di design del 2026-04-15. Secondo, il `λ` per-agente è omogeneo tra i beni all'interno di un singolo agente: lo stesso `λ` modulato dalla personalità è applicato a ogni riga `AgentExpectation` posseduta dall'agente, senza differenziazione bene-specifica. Un agente più ricco che alloca più attenzione cognitiva ai beni ad alto impatto potrebbe in principio portare un `λ` più alto per i beni che dominano il budget familiare e un `λ` più basso per i beni marginali; la spec lascia questo come raffinamento futuro e l'implementazione tratta l'omogeneità come scelta deliberata di scope per l'economia del Plan 2. Terzo, il tasso di adattamento `λ` non è esso stesso appreso: la modulazione Big Five in (4.10) è una mappatura statica dalla personalità a `λ`, senza meccanismo per cui un agente i cui forecast sono stati sistematicamente sbagliati aggiorni il proprio `λ` verso l'alto (per reagire di più alle sorprese) o verso il basso (per ancorare di più sul precedente). Le estensioni di apprendimento Bayesiano delle aspettative adattive (Evans e Honkapohja 2001) forniscono il formalismo canonico per `λ` come parametro appreso; l'implementazione Epocha traccia l'accuratezza di previsione attraverso il campo `confidence` ma non riporta `confidence` in `λ` nel commit fissato, sulla base che farlo richiederebbe una calibrazione di secondo ordine non consegnata nel Plan 2. Quarto, l'aggregazione di prezzo multi-zone è implementata come merge last-write-wins di `ZoneEconomy.market_prices` su tutte le zone piuttosto che come forecast per-zona per ogni agente: un agente nella zona A vede lo stesso prezzo effettivo per un bene di un agente nella zona B anche quando le due zone si sono cleared a prezzi diversi nel tick precedente. Il merge è documentato inline come semplificazione MVP (`expectations.py:144-153`) e la differenziazione per-zona è l'estensione naturale una volta che l'economia multi-zone di §3.6 è esercitata dalla suite di validazione del Capitolo 7.

### 4.2.2 Credito e banca (Diamond-Dybvig 1983, riserva frazionaria)

> Stato: implementato a partire dal commit `<filled-on-merge>`, audit della spec CONVERGENTE 2026-04-15.

**Background.** Lo strato credito-e-banca entra nella pipeline di tick di Epocha perché lo spazio di decisione dell'agente documentato in §3.2 porta un'azione esplicita `request_loan` e una dipendenza implicita su un aggregato monetario stabile, e nessuno dei due può essere soddisfatto dal substrato di §3.6 in isolamento: il substrato esegue il clearing dei mercati di beni a tick singolo e distribuisce salari e rendite, ma non rappresenta i contratti intertemporali che connettono una decisione di prestito al tick `T` all'obbligazione di rimborso al tick `T+k` che vincola la cassa futura del debitore, né porta gli aggregati di bilancio bancario il cui deterioramento produce i segnali di rischio sistemico che il context builder dell'LLM di §3.5 ha bisogno di alimentare nella pipeline di decisione. Diamond e Dybvig (1983) è il riferimento canonico per la banca a riserva frazionaria sotto dinamiche di fiducia dei depositanti: una singola banca prende depositi, presta una frazione di essi, tiene il resto come riserve, ed è esposta a un equilibrio self-fulfilling di corsa agli sportelli quando la fiducia dei depositanti scende sotto una soglia e i depositanti ritirano più velocemente di quanto i prestiti in maturazione possano essere liquidati. L'implementazione Epocha trascrive la dinamica qualitativa — la fiducia si erode quando le riserve scendono sotto il rapporto richiesto, l'erosione si trasmette come memorie di preoccupazione a livello di agente, e la trasmissione stessa accelera l'erosione attraverso la pipeline di decisione mediata dall'LLM — ma omette deliberatamente due elementi quantitativi del modello originale di Diamond-Dybvig. Primo, il modello è una singola banca aggregata per simulazione piuttosto che una popolazione di banche concorrenti (il mercato interbancario che modella il contagio nella letteratura empirica sulle corse agli sportelli è rinviato), e di conseguenza non c'è canale di prestito interbancario e nessun prestatore di ultima istanza della banca centrale. Secondo, la condizione originale di corsa agli sportelli di Diamond-Dybvig accoppia bassa fiducia con insolvenza attraverso un gioco di coordinamento sui tipi di ritiro dei depositanti; la convergenza dell'audit del 2026-04-15 (fix audit C-3) ha sostituito la condizione accoppiata con il trigger più semplice `confidence_index < 0.5` valutato indipendentemente dallo stato di solvibilità, sulla base che la popolazione guidata dall'LLM è completamente eterogenea nel suo stato informativo e l'equivalenza game-theoretic originale non vale puntualmente attraverso un set di agenti LLM. Il pricing dei prestiti segue Stiglitz e Weiss (1981) — i tassi di interesse portano un risk premium proporzionale alla leva del debitore come rappresentazione in forma ridotta dell'incapacità del prestatore di osservare perfettamente il rischio del debitore — e i cascade di default usano il meccanismo di contagio breadth-first di Allen e Gale (2000) cappato a una profondità configurabile.

**Modello.** Lo stato del sistema bancario è una singola riga `BankingState` per simulazione dichiarata in `epocha/apps/economy/models.py:568` e porta `total_deposits`, `total_loans_outstanding`, `reserve_ratio`, `base_interest_rate`, un booleano `is_solvent` e un `confidence_index ∈ [0, 1]`. I prestiti sono righe `Loan` individuali (`models.py:371-432`) con `lender`, `borrower`, `principal`, `interest_rate`, `remaining_balance`, una foreign key opzionale `collateral` a `Property` con `related_name="collateralized_loans"`, un `issued_at_tick`, un `due_at_tick` opzionale, un contatore `times_rolled_over` e uno `status ∈ {active, repaid, rolled_over, defaulted}`. Il trigger di corsa agli sportelli che guida la trasmissione di memorie di preoccupazione bancaria sotto il fix audit C-3 è la semplice diseguaglianza sul confidence index:

```
broadcast_concern_at_tick(t)  ⇔  BankingState.confidence_index < 0.5     (4.11)
```

L'equazione (4.11) è implementata in `broadcast_banking_concern()` a `epocha/apps/economy/banking.py:322-398`, con la soglia `0.5` dichiarata come costante a livello di modulo `_CONCERN_CONFIDENCE_THRESHOLD` a `banking.py:319`. La condizione è valutata incondizionatamente rispetto a `is_solvent`, che è il cambiamento sostantivo introdotto dal fix audit C-3: il gioco di coordinamento originale di Diamond-Dybvig (1983) prevede una corsa agli sportelli quando sia la fiducia è bassa *sia* la banca è insolvente, ma nella pipeline Epocha la dinamica della fiducia stessa guida `is_solvent` verso `False` nel tempo (`check_solvency()` decrementa `confidence_index` di `0.1` per tick ogniqualvolta le riserve sono insufficienti), quindi la condizione auditata attiva la trasmissione di preoccupazione allo stadio di *paura* piuttosto che solo dopo il fallimento realizzato, che è il pattern empirico documentato nella letteratura sulle corse agli sportelli rivista nella spec. La trasmissione stessa crea una riga `Memory` con `emotional_weight = 0.6` e `source_type = "public"` per un campione casuale di `_CONCERN_BROADCAST_RATIO = 0.5` della popolazione vivente di agenti (`banking.py:354-385`), con una finestra di deduplicazione di `_CONCERN_DEDUP_TICKS = 3` tick allineata alla costante di deduplicazione delle memorie del motore di agenti in `simulation/engine.py`.

La condizione di emissione del prestito combina il cap di garanzia loan-to-value della teoria di razionamento del credito di Stiglitz e Weiss (1981) con una precondizione di solvibilità della banca:

```
approve_loan(borrower, amount, collateral)
  ⇔  collateral.value · LTV ≥ existing_debt(borrower) + amount
  ∧  BankingState.is_solvent                                              (4.12)
```

L'equazione (4.12) è implementata in `evaluate_credit_request()` a `credit.py:158-224`. L'aggregato del debito esistente somma `remaining_balance` sui prestiti attivi del debitore; il rapporto LTV è `credit_config.loan_to_value`, che differisce per template di era. Quando entrambe le condizioni sono soddisfatte, la funzione restituisce il tasso di interesse per-tick calcolato dalla regola di pricing del rischio di Stiglitz-Weiss (1981)

```
r = base_rate · (1 + risk_premium · debt_ratio)
debt_ratio = (existing_debt + amount) / max(borrower.wealth, 1.0)         (4.13)
```

con `base_rate` letto da `BankingState.base_interest_rate`, `risk_premium` di default a `0.5` da `credit_config.risk_premium`, e la leva clampata sul lato della ricchezza per evitare divisione per zero per agenti neonati o indigenti. La forma funzionale è un'approssimazione linearizzata in forma ridotta del modello di selezione avversa di Stiglitz-Weiss — l'originale prevede una relazione non lineare — scelta per trasparenza e per mantenere il costo per-tick della valutazione del credito `O(1)` per richiesta. La logica di pegno della garanzia che seleziona quale proprietà il debitore offre come collaterale è implementata in `find_best_unpledged_property()` a `credit.py:733-751` ed esclude esplicitamente le proprietà già usate come garanzia per un prestito attivo via la clausola di esclusione `collateralized_loans__status="active"`: questo è il fix audit M-6 della convergenza del 2026-04-15, che impedisce alla stessa proprietà di essere doppia-pegnata su due prestiti simultanei (una violazione della semantica di garanzia di Stiglitz-Weiss che l'implementazione pre-audit consentiva).

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
| `risk_premium`                     |        0.50 | Coefficiente sullo spread di leva del debitore in (4.13)                       |
| `max_rollover`                     |           3 | Numero massimo di volte in cui un prestito in maturazione può essere rinnovato prima del default |
| `default_loan_duration_ticks`      |          20 | Durata di default del prestito assegnata da `issue_loan()` quando il chiamante non ne passa una |
| `_CONCERN_CONFIDENCE_THRESHOLD`    |        0.50 | Soglia di (4.11) sotto la quale sono trasmesse le memorie di preoccupazione bancaria |
| `_CONCERN_BROADCAST_RATIO`         |        0.50 | Frazione della popolazione vivente che riceve la trasmissione di preoccupazione per-tick |
| `CASCADE_LOSS_THRESHOLD`           |        0.50 | Frazione della ricchezza del prestatore sopra la quale una perdita per default si propaga al prestatore |

Le costanti strutturali `_CONCERN_CONFIDENCE_THRESHOLD`, `_CONCERN_BROADCAST_RATIO` e `CASCADE_LOSS_THRESHOLD` sono codificate come costanti a livello di modulo in `banking.py:319` e `credit.py:50` piuttosto che come campi del template, sulla base che codificano la forma qualitativa della dinamica di corsa agli sportelli (una profezia auto-avverante ha bisogno di una soglia sotto la quale la paura diventa contagiosa) piuttosto che scelte di calibrazione che variano per era storica. Il valore di `risk_premium` di `0.5` è una scelta di design piuttosto che una misurazione empirica — Stiglitz e Weiss (1981) prevedono che la pendenza del pricing del rischio sia positiva e crescente nella leva ma non forniscono un coefficiente numerico — ed è documentato inline come parametro di design tunabile a `credit.py:189-194`.

**Algoritmo.** Ad ogni tick, l'orchestratore dell'economia invoca lo step del mercato del credito esattamente una volta (regolato da un flag `credit_processed` così che non venga eseguito per-zona) a `epocha/apps/economy/engine.py:333-348`, con la seguente sequenza ordinata di chiamate. Primo, `default_dead_agent_loans(simulation)` (`credit.py:703-730`) manda in default tutti i prestiti attivi il cui debitore ha `is_alive = False`: questo è il fix audit M-3 della convergenza del 2026-04-15, che chiude il gap dell'amnistia silente del debito per cui l'implementazione pre-audit lasciava i prestiti del debitore deceduto in stato `active` indefinitamente, permettendo agli eredi del debitore di ereditare una proprietà ancora gravata da un debito che il sistema non avrebbe mai riscosso. Secondo, `service_loans(simulation, tick)` (`credit.py:328-398`) raccoglie gli interessi per-tick su ogni prestito attivo deducendo `remaining_balance · interest_rate` dalla cassa del debitore e accreditandolo al prestatore (o all'aggregato del sistema bancario quando `lender_type = "banking"`); i debitori che non possono pagare gli interessi sono restituiti in una lista per lo step di maturità per il default. Terzo, `process_maturity(simulation, tick)` (`credit.py:401-536`) gestisce i prestiti il cui `due_at_tick` uguaglia il tick corrente, con tre esiti per prestito: rimborso completo quando il debitore ha abbastanza cassa per coprire `remaining_balance`, un rollover in stile Minsky quando il debitore può pagare la porzione di interessi ma non il principale e il contatore `times_rolled_over` è sotto `max_rollover` (un nuovo prestito è creato a `interest_rate · 1.10` riflettendo l'aggiustamento di rischio del prestatore, con `times_rolled_over += 1`), e default quando nessuna delle due condizioni è soddisfatta. Quarto, `process_defaults(simulation, tick)` (`credit.py:539-645`) sequestra il collaterale trasferendo `Property.owner` al prestatore (o al governo per i prestiti del sistema bancario), azzera il `remaining_balance` del prestito, e crea una memoria di reputazione negativa per il debitore con `action_sentiment = -0.7` (osservatori della zona) e `-0.9` (il prestatore direttamente) via il sistema di reputazione di §4.x. Quinto, `process_default_cascade(simulation, tick, max_depth=3)` (`credit.py:754-858`) esegue una passata di contagio breadth-first sul grafo del debito: per ogni prestatore la cui perdita aggregata dai default di questo tick supera `CASCADE_LOSS_THRESHOLD = 0.5` della sua ricchezza, i prestiti attivi del prestatore stesso sono marcati defaulted, e il contagio si propaga ai loro prestatori a turno finché o non si verifica nessun ulteriore breach di soglia o si raggiunge `max_depth = 3` (il cap previene la propagazione infinita ed è calibrato contro il diametro tipico di 3-5 link delle reti empiriche riportato da Allen e Gale 2000). Sesto, `adjust_interest_rate(simulation, tick)` (`banking.py:112-194`) applica l'aggiustamento Wickselliano `r_{t+1} = r_t · (1 + adj_rate · (demand − supply) / max(supply, 0.001))` al tasso di base e clampa il risultato a `[0.005, 0.50]`. Settimo, `check_solvency(simulation)` (`banking.py:197-254`) valuta `reserves = total_deposits − total_loans_outstanding` contro `required = total_deposits · reserve_ratio` e aggiorna `confidence_index` di `−0.1` per tick di insolvenza o `+0.05` per tick di recupero (l'asimmetria codifica l'osservazione di asimmetria della fiducia che la fiducia è più facile da perdere che da ricostruire). Ottavo e ultimo, `broadcast_banking_concern(simulation, tick)` (`banking.py:322-398`) valuta la (4.11) e crea le memorie di preoccupazione. La sequenza a otto step è deterministica dato il seed casuale della simulazione (la chiamata `random.sample()` nello step di trasmissione consuma il modulo `random` seedato), e l'intero step di credito scrive un numero limitato di righe del database per tick — limitato dal conteggio degli agenti vivi per la trasmissione e dal conteggio dei prestiti attivi per il servicing e la maturità — quindi il costo per-tick è `O(n_agents + n_active_loans)`.

**Semplificazioni.** L'implementazione attuale omette deliberatamente quattro raffinamenti che la letteratura su credito-e-banca tratta come estensioni proprie piuttosto che correzioni del meccanismo baseline. Primo, il settore bancario è una singola banca aggregata per simulazione piuttosto che una popolazione di banche concorrenti: la riga `BankingState` è uno-a-uno con `Simulation`, e non c'è mercato di prestito interbancario, nessun grafo di esposizione interbancaria, e nessun prestatore di ultima istanza della banca centrale. Il meccanismo di contagio di Allen-Gale (2000) è quindi implementato solo sul grafo del debito agente-a-agente (`process_default_cascade`), non su un grafo di rete bancaria; un raffinamento multi-banca è registrato nella spec come estensione rinviata e richiederebbe l'introduzione di un modello `Bank` con bilanci per-banca e un grafo di passività interbancarie. Secondo, l'assicurazione sui depositi è astratta: il flag `BankingState.is_solvent` impedisce l'emissione di nuovi prestiti mentre insolvente (via la precondizione in (4.12)), ma non c'è un fondo di assicurazione sui depositi esplicito contro cui i depositanti possano rivalersi, e i depositanti non possono "ritirare" la loro cassa dalla banca nel senso letterale perché il campo cassa di AgentInventory rappresenta già la cassa a portata piuttosto che un saldo depositato — il modello tratta tutta la cassa dell'agente come implicitamente depositata (`recalculate_deposits()` a `banking.py:281-305`). Un raffinamento futuro spaccherebbe `AgentInventory.cash` in una frazione depositata e una frazione accumulata, permettendo alla dinamica di corsa agli sportelli di essere espressa come pressione di ritiro piuttosto che come voce mediata dalla fiducia. Terzo, la negoziazione del prestito è single-round prendi-o-lascia: il debitore presenta un'azione `request_loan` con un importo target e un collaterale candidato, `evaluate_credit_request()` o approva al tasso di Stiglitz-Weiss o respinge con una ragione dichiarata, e non c'è un secondo round in cui il debitore potrebbe contro-proporre un importo più piccolo, un collaterale diverso, o una durata più lunga per portare la richiesta dentro l'inviluppo LTV. La negoziazione multi-round è registrata come raffinamento rinviato sotto il log di risoluzione audit del documento di design del 2026-04-15, sulla base che interagirebbe con il budget di contesto LLM e la pipeline di decisione per-tick in modi che hanno bisogno di una passata di calibrazione separata. Quarto, l'incremento del tasso di interesse del rollover è fissato a `1.10` per rollover (`credit.py:504`) piuttosto che essere una funzione della leva del debitore al momento del rollover o del segnale di stress macroeconomico portato dall'indice di fiducia bancaria; una regola di repricing del rollover più sofisticata che risponda al rischio sistemico è l'estensione naturale una volta che la suite di validazione del Capitolo 7 esercita la classificazione di stadio di Minsky (`classify_minsky_stage` a `credit.py:104-155`) contro la tassonomia canonica hedge-speculative-Ponzi di Minsky (1986).

### 4.2.3 Mercato immobiliare

> Stato: implementato a partire dal commit `<filled-on-merge>`, audit della spec CONVERGENTE 2026-04-15.

**Background.** Il mercato immobiliare entra nella pipeline di tick di Epocha perché lo spazio di decisione dell'agente documentato in §3.2 porta un'azione `buy_property` e un'azione `sell_property` la cui semantica non può essere ridotta al clearing di mercato di beni a tick singolo del tipo posseduto dal substrato di §3.6: una proprietà cambia mano una volta e resta con l'acquirente per il resto della simulazione, il prezzo richiesto diverge sistematicamente dal rendimento da affitto fondamentale perché i venditori si ancorano ad aspettative modulate dalla personalità, e l'intento dell'acquirente dichiarato al tick `T` non può essere regolato all'interno dello stesso tick perché la pipeline di decisione guidata dall'LLM ha già prodotto i suoi output al momento in cui l'orchestratore dell'economia viene invocato. L'implementazione trascrive un meccanismo zone-locale di annunci-e-abbinamento che preserva le tre proprietà sostantive: le proprietà sono annunciate dai loro proprietari con un prezzo richiesto, gli annunci vivono nella zona corrente dell'acquirente, e l'abbinamento si regola al tick `T+1` contro gli intenti `buy_property` dichiarati al tick `T`. Il benchmark di valore fondamentale contro cui venditori e acquirenti confrontano il prezzo richiesto è la valutazione del modello di crescita di Gordon (1959) `V = R / (r − g)`, che dà il valore intrinseco di un asset il cui flusso di cassa è una perpetuità che cresce al tasso `g` scontata al tasso `r`; l'implementazione Epocha calcola questo benchmark per proprietà e lo memorizza nel campo `fundamental_value` dell'annuncio insieme all'`asking_price` del venditore, così che la divergenza tra prezzo e valore sia osservabile alle analytics downstream e sia l'analogo Epocha naturale della divergenza prezzo-fondamentali che Shiller (2000) identifica come la firma empirica delle bolle speculative. Due semplificazioni concrete sono registrate inline: non c'è negoziazione multi-round tra acquirente e venditore (il prezzo richiesto è prendi-o-lascia) e non c'è abbinamento inter-zona (un acquirente nella zona A non può abbinare un annuncio nella zona B, anche a un prezzo più basso, perché l'assunzione di zone-località è la struttura spaziale che il mercato immobiliare eredita dal movimento di §3.4). Il mercato immobiliare porta anche un canale laterale di cambio di regime implementato in `process_expropriation()` che ridistribuisce le proprietà sulle transizioni di governo seguendo Acemoglu e Robinson (2006); il canale laterale è documentato nel modulo del mercato immobiliare perché opera sulle stesse righe `Property` ma è invocato dal sottosistema politico piuttosto che dall'orchestratore dell'economia per-tick, quindi questa sottosezione lo tratta solo come la sorgente dell'effetto laterale di conversione del collaterale sui prestiti in essere.

**Modello.** La condizione di abbinamento che trasferisce una proprietà da un venditore `s` a un acquirente `b` al tick `T` legge contro la tabella `PropertyListing` e la zona corrente dell'acquirente:

```
match(b, ℓ) at tick T  ⇔  ℓ.status = "listed"
                       ∧  ℓ.property.zone = b.zone        (zone at matching time)
                       ∧  ℓ.property.owner ≠ b            (no self-purchase)
                       ∧  buyer_cash(b) ≥ ℓ.asking_price
                       ∧  buy_property ∈ DecisionLog(b, T−1)            (4.14)
```

L'equazione (4.14) è implementata in `process_property_listings()` a `epocha/apps/economy/property_market.py:188-332`, con i quattro congiunti valutati nell'ordine elencato così che l'annuncio qualificante più economico sia selezionato via `order_by("asking_price").first()`. Il congiunto zone-at-matching-time è il cambiamento sostantivo introdotto dal fix audit M-4 della convergenza del 2026-04-15: l'implementazione pre-audit leggeva la zona dell'acquirente dal contesto di decisione al tick `T−1`, che produceva abbinamenti spuri quando l'acquirente si muoveva tra i tick `T−1` e `T`, e la forma auditata legge `buyer.zone_id` direttamente alla chiamata di abbinamento così che un acquirente che ha attraversato un confine di zona perda la capacità di abbinare un annuncio nella zona precedente. L'esclusione del self-purchase è il cambiamento sostantivo introdotto dal fix audit M-5 della stessa convergenza: l'implementazione pre-audit consentiva all'intento `buy_property` di un venditore di abbinare il proprio annuncio (una transazione no-op che tuttavia consumava un tick del budget di intenti dell'acquirente e gonfiava il conteggio degli abbinati), e la forma auditata esclude le proprietà dell'acquirente dal candidate set via `.exclude(property__owner=buyer)`. La precondizione di prestito che regola il controllo della cassa non fa parte della condizione di abbinamento stessa: un acquirente con cassa insufficiente semplicemente fallisce l'abbinamento, e la spec registra questo come fix audit A-5 — il design pre-audit emetteva automaticamente un prestito per coprire il deficit, il che contraddiceva il principio architettonico che tutto il prestito è un'azione esplicita guidata dall'LLM documentata in §3.2, e la forma auditata rimuove il percorso auto-prestito così che un acquirente che ha bisogno di credito debba dichiarare un'azione `borrow` in un tick precedente e poi ridichiarare `buy_property` una volta che la cassa è in mano.

La condizione di conversione del collaterale che trasferisce una proprietà da un debitore in default al prestatore al momento del default del prestito legge contro la foreign key `Loan.collateral` stabilita all'emissione:

```
on default of loan L at tick T:
    if L.collateral ≠ ∅ :
        L.collateral.owner ← L.lender         (or government if lender = banking)
        L.lender_loss     ← max(0, L.remaining_balance − L.collateral.value)        (4.15)
```

L'equazione (4.15) è implementata in `process_defaults()` a `epocha/apps/economy/credit.py:539-645`, con la perdita residua calcolata dopo che il valore del collaterale è netto e propagata alla passata di contagio breadth-first di Allen-Gale (2000) descritta sotto l'Algoritmo di §4.2.2 quando supera `CASCADE_LOSS_THRESHOLD = 0.5` della ricchezza del prestatore. La conversione del collaterale è il ponte tra il sottosistema di credito di §4.2.2 e il mercato immobiliare di questa sottosezione: una proprietà pegnata come collaterale via la chiamata `find_best_unpledged_property()` di (4.12) è bloccata da nuovi pegni di collaterale dal fix audit M-6, e la sua conversione in default produce un cambio immediato di proprietà che i tick successivi del mercato immobiliare osservano attraverso il campo standard `property.owner`. La conversione non genera un `PropertyListing` per il prestatore — il prestatore prende la proprietà direttamente in possesso e può o meno annunciarla in vendita in un tick futuro a seconda delle proprie decisioni guidate dall'LLM — e di conseguenza non appare nel conteggio degli abbinati per-tick di `process_property_listings()`.

**Parametri.** Il mercato immobiliare non porta un proprio blocco di configurazione era-specifico; i parametri che governano il comportamento di abbinamento sono ereditati dalla configurazione del credito di §4.2.2 (loan-to-value per il percorso di prestito, tasso di interesse di base come tasso di sconto `r` nella valutazione di Gordon) e dalla configurazione delle aspettative di §4.2.1 (la `trend_threshold = 0.05` del fix audit C-5 che classifica l'ancoraggio del venditore come rising, falling, o stable). I due parametri di design del mercato immobiliare codificati fuori dai template di era sono la finestra di scadenza degli annunci e la guard band di valutazione di Gordon: gli annunci stantii sono ritirati dopo `10` tick (`property_market.py:222`), riflettendo l'assunzione che i mercati immobiliari nelle economie dal pre-industriale al moderno operano su scale temporali multi-periodo e che un annuncio invenduto oltre quell'orizzonte è più probabilmente un prezzo stantio che un'offerta vitale; il denominatore della valutazione di Gordon è floored a `0.01` per impedire la divisione per zero quando `r ≈ g`, e la valutazione risultante è clampata a `[0.1 · property.value, 10 · property.value]` per evitare che il fondamentale degeneri a zero su collassi transitori dell'affitto o esploda all'infinito su impennate transitorie dell'affitto (`property_market.py:114-121`). Il cap di valutazione di `10×` valore di libro è riconosciuto nel log di risoluzione audit della spec come il vincolo binding sulla magnitudine delle bolle speculative che la simulazione può esprimere: le bolle reali possono superare questo multiplo, e il cap è documentato come parametro di design tunabile piuttosto che bound strutturale. I quattro template di era ereditano i valori base per-proprietà da `_PROPERTIES_BASE` in `template_loader.py:66-85` (terreno agricolo 200, officina 150, negozio 100 in unità di valuta primaria), con il template industriale che aggiunge una fabbrica al valore base 500, il template moderno che aggiunge una fabbrica a 500 e un ufficio a 300, e il template sci-fi che aggiunge una fabbrica automatizzata a 1 000 e un laboratorio di ricerca a 800; la differenziazione per-era è qualitativa (quali tipi di proprietà sono disponibili piuttosto che quali sono i loro parametri) e l'omogeneità dei valori base tra le ere è un deliverable di calibrazione del Plan 4 piuttosto che una scelta di design sostantiva.

**Algoritmo.** Ad ogni tick, l'orchestratore dell'economia invoca `process_property_listings(simulation, tick)` esattamente una volta, regolato dallo stesso flag `credit_processed` che protegge lo step del credito a `epocha/apps/economy/engine.py:333-348`, e con la nota di ordinamento esplicita che il mercato immobiliare gira *prima* dello step del credito così che la cassa dalla vendita di proprietà accreditata ai venditori possa prevenire i default di prestiti che altrimenti si attiverebbero allo step del credito all'interno dello stesso tick. La funzione esegue cinque passate ordinate. Primo, una bulk update con singola query marca tutti gli annunci più vecchi di `tick − 10` come `withdrawn`, sostituendo l'iterazione per-annuncio con una chiamata `.update()` che è `O(1)` nel numero di annunci stantii. Secondo, la funzione legge le righe `DecisionLog` del tick precedente il cui JSON `output_decision` contiene la sottostringa `"buy_property"` e parsa ogni riga con `json.loads()` per recuperare il campo `action`; le righe con JSON malformato sono saltate silenziosamente, sulla base che l'LLM occasionalmente produce JSON non valido e un fallimento duro al parse propagherebbe un fallimento dell'LLM in un fallimento della pipeline di tick. Terzo, per ogni acquirente parsato la funzione controlla i quattro congiunti di (4.14) in ordine e seleziona l'annuncio qualificante più economico via `order_by("asking_price").first()`; il congiunto di zone-località è imposto dal filtro `property__zone_id=buyer.zone_id`, l'esclusione del self-purchase da `.exclude(property__owner=buyer)`, e il controllo della cassa leggendo `AgentInventory.cash[currency_code]` contro il prezzo richiesto dell'annuncio. Quarto, quando tutti i congiunti valgono, la funzione esegue il settlement a quattro step in un ordine deterministico: la cassa è dedotta dall'`AgentInventory.cash` dell'acquirente, accreditata all'`AgentInventory.cash` del venditore (creando una riga di inventario per il venditore se mancante), i campi `owner` e `owner_type` della proprietà sono riassegnati all'acquirente, e lo `status` dell'annuncio è impostato a `"sold"`; le quattro scritture sono chiamate `save(update_fields=[...])` indipendenti piuttosto che una singola transazione perché il tick di economia esistente è già avvolto in una transazione al livello dell'orchestratore. Quinto, una riga `EconomicLedger` è creata con `transaction_type="property_sale"` (aggiunto a `TRANSACTION_TYPES` dalla stessa convergenza del 2026-04-15) che registra il flusso di cassa da acquirente a venditore. La funzione restituisce un dizionario `{"matched": M, "expired": E, "failed": F}` che l'orchestratore logga a livello `INFO` per osservabilità per-tick. La passata è `O(n_buyers · log n_listings)` per tick perché il piano di query per-acquirente usa l'ordinamento `(zone, status, asking_price)` piuttosto che un full table scan, e l'intero costo per-tick è limitato superiormente dal conteggio degli agenti vivi per l'enumerazione degli acquirenti e dal conteggio degli annunci attivi per l'abbinamento per-acquirente.

**Semplificazioni.** L'implementazione attuale omette deliberatamente quattro raffinamenti che la letteratura del mercato immobiliare tratta come estensioni proprie piuttosto che correzioni del meccanismo baseline. Primo, gli annunci sono abbinati una volta per tick in un singolo round: un acquirente che ha la cassa per un annuncio ma perde contro un altro acquirente ordinato prima nell'iterazione non riceve una seconda possibilità all'interno dello stesso tick, e un acquirente il cui unico annuncio vitale nella zona corrente è appena sopra il suo budget non può controfferire a un prezzo più basso. La negoziazione multi-round con convergenza bid-ask è registrata nella spec come raffinamento rinviato, sulla base che interagirebbe con il budget di contesto LLM di §3.5 in modi che hanno bisogno di una passata di calibrazione separata. Secondo, gli annunci non persistono il loro ordinamento originale attraverso la finestra di scadenza degli annunci: un annuncio postato al tick `T` compete con un annuncio postato al tick `T+5` puramente sul prezzo, quindi un annuncio postato presto non riceve priorità per essere stato sul mercato più a lungo; un raffinamento di priorità temporale (FIFO sugli annunci allo stesso prezzo) è registrato come estensione rinviata. Terzo, l'intento dell'acquirente è binario piuttosto che parametrizzato: un'azione `buy_property` non porta un tipo target o un prezzo massimo, e la passata di abbinamento seleziona l'annuncio più economico nella zona dell'acquirente indipendentemente dalla compatibilità tra il `production_bonus` della proprietà e il ruolo dell'acquirente; un intento tipizzato per target che filtri gli annunci per tipo di proprietà o per allineamento al production-bonus è l'estensione naturale una volta che la grammatica delle azioni LLM di §3.2 è ampliata per supportare parametri tipizzati. Quarto, la regola di formazione del prezzo richiesto che produce la divergenza tra `asking_price` e `fundamental_value` è documentata nell'azione `sell_property` allo strato di decisione LLM di §3.2 piuttosto che allo strato del mercato immobiliare, e di conseguenza questa sottosezione tratta il prezzo richiesto come input esogeno alla condizione di abbinamento (4.14); la logica di ancoraggio speculativo e modulazione di personalità che produce la divergenza è oggetto della pipeline di decisione lato venditore ed è documentata in §3.2.



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

La disciplina delle migrazioni segue la regola di progetto secondo cui nessuna migrazione viene applicata a `develop` senza che la modifica di modello corrispondente sia mergiata nello stesso commit; le migrazioni sotto `epocha/apps/<app>/migrations/` sono lineari e mai squashate tra release, sul presupposto che la simulazione stessa sia la fonte di verità e che il rollback di una migrazione debba restare un'operazione a livello git. Due convenzioni del modello di persistenza, entrambe formalizzate durante l'audit del Plan 1 di demografia, meritano menzione esplicita perché attraversano più app. Primo, ogni saldo monetario è memorizzato come `JSONField` con chiave codice valuta in stile ISO-4217 piuttosto che come singolo `DecimalField`: `AgentInventory.cash` (`epocha/apps/economy/models.py:203`) e i campi di tesoreria analoghi sulle entità di governo e bancarie portano tutti dizionari per valuta in modo che i saldi multi-valuta e le analitiche per valuta siano preservati senza migrazioni di schema quando una nuova valuta viene introdotta da un template sci-fi o moderno. Secondo, la colonna `Agent.birth_tick` su `agents.Agent` è un `BigIntegerField` piuttosto che un `PositiveIntegerField` (`epocha/apps/agents/models.py:88`); il tipo signed è richiesto perché gli agenti pre-esistenti la cui età precede l'inizio della simulazione portano un birth tick negativo, e la formula canonica dell'età `age = (current_tick − birth_tick) / ticks_per_year` perderebbe altrimenti validità al confine della popolazione fondatrice. La traccia di migrazioni in `agents.0009_agent_birth_tick_*` e `agents.0010_alter_agent_birth_tick_*` registra l'introduzione del campo e la sua successiva ritipizzazione durante il loop di convergenza del Plan 1.

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
| Mercato immobiliare | Nessuna tabella autonoma — i parametri ereditano dalla configurazione del credito di §4.2.2 (loan-to-value, tasso di interesse base come tasso di sconto `r`) e dalla configurazione delle aspettative di §4.2.1 (la `trend_threshold = 0.05` per la classificazione del prezzo richiesto). Due parametri di design specifici del mercato immobiliare sono codificati al di fuori dei template e documentati inline in §4.2.3: la finestra di scadenza degli annunci di `10` tick (`property_market.py:222`) e la banda di guardia della valutazione Gordon che pavimenta il denominatore a `0.01` e clippa la valutazione risultante a `[0.1 · property.value, 10 · property.value]` (`property_market.py:114-121`). |

Il template `sci_fi.json` è documentato nel suo file sorgente come speculativo e non porta alcun target di calibrazione empirico per nessuno dei moduli auditati.

## 6.2 Template per epoca ed euristiche regolabili

La simulazione supporta due sistemi di template paralleli che hanno avuto origine da decisioni di design indipendenti nelle spec di demografia ed economia. La discrepanza in forma e numero è un effetto collaterale deliberato della storia di design a fasi piuttosto che un intento strutturale, ed è registrata esplicitamente qui perché i due sistemi convergeranno alla fine durante il Plan 4.

I template di demografia sono cinque file JSON sotto `epocha/apps/demography/templates/`: `pre_industrial_christian.json`, `pre_industrial_islamic.json`, `industrial.json`, `modern_democracy.json` e `sci_fi.json`. Ciascun file porta un dizionario piatto con tre chiavi di primo livello (`mortality`, `fertility`, `couple`), ognuna che contiene i valori di parametro consumati dal modello corrispondente di §4.1. La coppia pre-industriale è una scissione deliberata: i due file condividono blocchi di mortalità e fertilità identici (perché il record storico empirico non giustifica una differenziazione per confessione negli schedule biologici sottostanti) e differiscono solo nel blocco `couple`, dove `pre_industrial_islamic.json` porta `marriage_market_type: arranged` contro il regime autonomo di tutti gli altri template e `pre_industrial_christian.json` porta `divorce_enabled: false` per modellare il regime canonico cattolico di indissolubilità del matrimonio. Lo schema JSON è intenzionalmente stretto: ogni chiave è consumata da un modello specifico in §4.1, nessun campo di estensione non tipizzato è accettato, e una chiave sconosciuta in fase di caricamento solleva un errore di validazione anziché essere silenziosamente ignorata.

I template di economia sono quattro funzioni factory Python in `epocha/apps/economy/template_loader.py`: `_pre_industrial_template()`, `_industrial_template()`, `_modern_template()` e `_sci_fi_template()`. Ciascuna funzione restituisce un dizionario annidato che il loader passa a `EconomyTemplate.objects.get_or_create()`, e la differenziazione per epoca è realizzata variando un piccolo insieme di input (tabella valute, elasticità dei beni, stock dei fattori, configurazione comportamentale) piuttosto che mantenendo quattro file JSON indipendenti. Il blocco comportamentale in particolare è costruito una sola volta da `_behavioral_config()` (`template_loader.py:144-198`) ed è identico tra tutti e quattro i template al commit pinnato, sul presupposto che le evidenze di calibrazione auditate del Plan 2 non motivassero una differenziazione per epoca al momento della spec. La differenziazione per epoca di `λ_base`, dei coefficienti di modulazione Becker, di `risk_premium`, `max_rollover` e `default_loan_duration_ticks` è il debito di calibrazione esplicito assegnato al Plan 4. I due sistemi usano numeri diversi (cinque per demografia, quattro per economia) perché la spec di demografia richiedeva di separare i due regimi confessionali pre-industriali per supportare la distinzione di mercato matrimoniale e regime di divorzio, mentre la spec di economia non ha trovato alcuna distinzione strutturale analoga al livello prezzo-e-credito che giustificasse un quinto template.

Oltre ai valori di parametro per template, i moduli auditati portano un piccolo numero di costanti strutturali che sono codificate nel sorgente piuttosto che nei template perché sono proprietà del modello piuttosto che scelte di calibrazione. I limiti delle aspettative `_LAMBDA_MIN = 0.05` e `_LAMBDA_MAX = 0.95` (`expectations.py:38-39`) prevengono previsioni degeneri e sono documentati in §4.2.1; il `CASCADE_LOSS_THRESHOLD = 0.5` del passaggio di contagio Allen-Gale e la corrispondente finestra di scadenza degli annunci di `10` tick sono documentati rispettivamente in §4.2.2 e §4.2.3. Queste sono euristiche regolabili nel senso che ammettono revisione sotto evidenze di calibrazione future, ma non sono campi di template e la differenziazione per epoca non è un deliverable del Plan 4 per esse.

## 6.3 Procedure di fit

Il modulo di mortalità include un helper di fit funzionante, `fit_heligman_pollard()` in `epocha/apps/demography/mortality.py:103-158`, che avvolge `scipy.optimize.curve_fit` contro la forma funzionale HP a otto parametri. La funzione prende una lista di età e le corrispondenti probabilità annue di mortalità osservate `q(x)` e restituisce un dizionario con chiave i nomi degli otto parametri HP (`A`-`H`). Le condizioni iniziali di default sono l'array `p0 = [0.005, 0.02, 0.1, 0.001, 10.0, 22.0, 0.00005, 1.1]` riportato nel sorgente, e i bound dei parametri sono imposti tramite l'argomento `bounds=(lower, upper)` con `lower = [0.0, 0.0, 0.0, 0.0, 0.1, 1.0, 0.0, 1.0]` e `upper = [0.1, 0.5, 1.0, 0.05, 50.0, 50.0, 0.001, 1.5]`. I bound corrispondono ai range ammissibili riportati inline nella Tabella 4.1 e sono gli stessi bound che validano i valori per epoca contenuti nei cinque template del Plan 1. Una guard di input degenere rifiuta gli schedule di mortalità che siano uniformemente nulli prima di passarli all'ottimizzatore, in modo che la funzione fallisca rapidamente con un `RuntimeError` descrittivo piuttosto che lasciare che `curve_fit` minimizzi silenziosamente verso un confine dello spazio dei parametri. I bound stessi sono oggetto del debito di audit B-5 della spec di demografia: i valori attuali sono coerenti con la letteratura attuariale sul modello HP (Heligman e Pollard 1980; Tabeau, van den Berg Jeths e Heathcote 2001) ma la catena di giustificazione per ciascun bound è riservata alla calibrazione del Plan 4, insieme al primo fit end-to-end dell'helper contro una vera life table dello Human Mortality Database.

Il modulo di fertilità non include ancora un helper di fit corrispondente per la Hadwiger ASFR. L'implementazione attuale in `epocha/apps/demography/fertility.py` valuta solo la formula canonica all'età dell'agente contro i valori `H`, `R` e `T` per epoca caricati dai template JSON: una `fit_hadwiger()` che invertirebbe la formula contro un profilo ASFR osservato è registrata come deliverable del Plan 4. La ragione dell'asimmetria è che lo scope di fertilità del Plan 1 si limitava esplicitamente al passaggio di valutazione per tick e alla modulazione Becker che lo avvolge; il loop di calibrazione che consumerebbe profili ASFR storici (record parrocchiali dell'Inghilterra pre-industriale via Wrigley e Schofield 1981; serie ASFR moderne via Eurostat o HMD) è il deliverable centrale del Plan 4 e rispecchierà la struttura di `fit_heligman_pollard()` una volta implementato. I coefficienti di modulazione Becker della Tabella 4.4 ugualmente non sono attualmente fittati: sono seedati con gli stessi cinque valori in tutti e cinque i template e la calibrazione per epoca è il deliverable centrale del debito B2-07 nel Plan 4. I parametri di credito, sistema bancario e mercato immobiliare delle Tabelle 4.8-4.9 sono calibrati qualitativamente contro Homer e Sylla (2005) per i range di tasso di interesse per epoca e contro la convenzione di Basel III per il rapporto di riserva moderno, ma nessuna procedura di fit automatica è implementata per essi: la differenziazione per epoca dei parametri uniformi della Tabella 4.9 e dei valori base del mercato immobiliare è riservata al Plan 4 insieme ai fit di demografia.

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

Il Capitolo 8 copre i sette cluster Epocha che sono implementati nel codice ed esercitati da unit test ma non hanno ancora completato l'audit scientifico avversariale di Round 2 che funge da gate alla promozione allo stato di Capitolo 4. L'audit batch del 2026-04-12 (`docs/scientific-audit-2026-04-12.md`) ha aperto una lista di finding INCORRECT, UNJUSTIFIED, INCONSISTENT e MISSING contro otto dei moduli sottostanti; il passaggio di risoluzione e il rifacimento audit di convergenza sono tracciati come l'item di priorità più alta della roadmap del Capitolo 9. Ciascuna sottosezione quindi riformula lo scope del cluster, i puntatori di letteratura portati dalla spec e dai docstring del modulo, e il code path, poi chiude con una riga di stato che nomina la spec sotto la quale l'audit riprenderà. I puntatori di letteratura in questo capitolo sono attribuzioni registrate dalla spec o dal sorgente piuttosto che citazioni Methods-grade verificate da fonte primaria del tipo del Capitolo 4.

## 8.1 Cluster: Propagazione del passaparola (Information Flow + Distortion + Belief Filter)

Il cluster di propagazione del passaparola copre i tre moduli che spostano un rumour dalla memoria di un singolo agente attraverso la rete sociale e nello stato di credenza dell'agente ricevente: `information_flow.py` seleziona quali agenti vengono esposti al rumour a ciascun hop di propagazione, `distortion.py` rimodella il contenuto del rumour sotto la personalità di chi lo ridice a ciascun hop, e `belief.py` filtra il rumour in arrivo attraverso le credenze a priori del ricevente e produce la credenza aggiornata che i moduli decisionali a valle leggono. L'implementazione trascrive tre famiglie di letteratura: Allport e Postman (1947) sul levelling/sharpening/assimilation della riproduzione seriale, che `distortion.py` implementa come regole di cancellazione, esagerazione e rimodellamento modulate dalla personalità; Bartlett (1932) sulla riproduzione seriale più in generale, che `information_flow.py` cita come razionale per ri-applicare la distorsione a ogni hop piuttosto che trattare il rumour come un payload fisso che propaga inalterato; e Granovetter (1973) sul ruolo strutturale dei legami deboli nella diffusione informativa, citato nel docstring di `information_flow.py` come frame concettuale per il bridging tra cluster ma non implementato come pesatura della forza del legame nella probabilità di propagazione — il batch di audit del 2026-04-12 ha segnalato questa lacuna come una citation-without-implementation (il docstring riconosce l'omissione inline). Code path: `epocha/apps/agents/information_flow.py`, `epocha/apps/agents/distortion.py`, `epocha/apps/agents/belief.py`.

> Stato: implementato nel codice, audit Round 2 pendente. Vedere `docs/superpowers/specs/2026-04-05-information-flow-design.md`.

## 8.2 Cluster: Istituzioni politiche (Government + Institutions + Stratification)

Il cluster delle istituzioni politiche copre i quattro moduli che trasformano l'azione politica a livello di agente in dinamiche a livello di regime: `government.py` implementa lo step di governo per tick (decadimento di legittimità, scheduling delle elezioni, successione alla morte di un titolare e risoluzione del tentativo di golpe), `government_types.py` dichiara i sette archetipi di regime (democrazia piena, semi-democrazia, monarchia tradizionale, autocrazia parziale, regime totalitario, teocrazia, anarchia) con i loro tassi di decadimento di legittimità per archetipo e le regole elettorali, `institutions.py` porta lo stato istituzionale di orizzonte più lungo (protezioni costituzionali, struttura partitica, crisi di successione) che incrocia lo step di governo, e `stratification.py` calcola il Gini per zona e la risposta di probabilità di rivolta che retroagisce nella legittimità del governo. I puntatori di letteratura portati dal sorgente sono Acemoglu e Robinson (2006) sul legame disuguaglianza-instabilità (già in §13) — la spec usa la loro probabilità di rivolta basata su soglia Gini come forma qualitativa della risposta di `stratification.py` — Powell e Thyne (2011) sul tasso base empirico degli esiti dei colpi di stato (citato in `government.py` per il tasso di successo del ~50% dei tentativi di golpe), il progetto Polity IV (Marshall e Gurr 2020, citato in `government_types.py`) per la calibrazione della tipologia di regime dei tassi di decadimento di legittimità e delle regole elettorali per archetipo, e Alesina e Perotti (1996) sulla correlazione qualitativa tra distribuzione del reddito e instabilità politica (citato in `political_feedback.py` dell'app economy per il bridge cross-modulo dallo stato economico di §3.6 alla legittimità di governo). Code path: `epocha/apps/world/government.py`, `epocha/apps/world/government_types.py`, `epocha/apps/world/institutions.py`, `epocha/apps/world/stratification.py`.

> Stato: implementato nel codice, audit Round 2 pendente. Vedere `docs/superpowers/specs/2026-04-05-government-institutions-stratification-design.md`.

## 8.3 Movimento

Il modulo di movimento governa la rilocazione per tick degli agenti tra zone sotto tre classi di intento: migrazione economica volontaria guidata dall'azione `move_to_zone` dell'agente, migrazione sociale volontaria guidata dall'attrazione relazionale (un partner, un genitore o un leader di fazione in un'altra zona), e movimento involontario guidato dalla distruzione o espulsione dalla zona. L'implementazione porta una tabella di velocità di viaggio per modalità (a piedi 25 km/giorno, a cavallo 60 km/giorno, in carrozza 60 km/giorno su buone strade, su barca fluviale 50 km/giorno) calibrata da David Chandler (1966), *The Campaigns of Napoleon* — una fonte di storia militare per i ritmi di marcia civili e di cavalleria sostenuti che includono le soste — e da Braudel (1979) per la forma qualitativa della geografia delle rotte commerciali pre-industriali, con il moltiplicatore di qualità della strada lasciato come parametro di design regolabile inscritto nel template per epoca piuttosto che come fit empirico a una specifica rete stradale storica. Il batch di audit del 2026-04-12 ha segnalato due preoccupazioni di calibrazione contro questo modulo: il ritmo di 25 km/giorno a piedi è all'estremo alto del range empirico per il viaggio civile non militare (un rifugiato, un commerciante a piedi o un contadino che si muove tra villaggi tipicamente fa una media di 15-20 km/giorno secondo la stessa fonte Chandler tenendo conto del terreno e del carico), e il grafo inter-zona che lo step di movimento attraversa è il grafo astratto delle zone di `world/models.py` piuttosto che un calcolo di distanza routata contro la geometria effettiva delle zone (la geometria è già memorizzata in PostGIS per §3.6 ma il layer di routing è rimandato all'item di lavoro PostGIS più ampio della roadmap del Capitolo 9). Code path: `epocha/apps/agents/movement.py`.

> Stato: implementato nel codice, audit Round 2 pendente. Vedere `docs/superpowers/specs/2026-04-07-movement-system-design.md`.

## 8.4 Fazioni

Il modulo delle fazioni copre le tre fasi del ciclo di vita di una fazione Epocha: formazione (un agente dichiara l'intento di fondare una fazione e altri agenti scelgono di unirsi sotto regole di lamentela condivisa e affinità di personalità), mantenimento (aggiornamento di coesione per tick, successione di leadership alla morte o defezione del fondatore, disciplina interna contro membri le cui azioni divergono dalla piattaforma dichiarata della fazione) e dissoluzione (una fazione la cui coesione scende sotto la soglia, o la cui membership scende sotto il minimo, viene dissolta e i suoi membri rilasciati). L'implementazione cita Olson (1965), *The Logic of Collective Action*, come frame concettuale per la formazione delle fazioni: la spec sottolinea che le lamentele condivise e le circostanze condivise (zona, occupazione, esposizione allo stesso evento) guidano la formazione del gruppo in modo più affidabile della similarità di personalità, e la regola di formazione in `factions.py` pesa le memorie di lamentela condivisa al di sopra dell'affinità di personalità nello score di valutazione del candidato. L'asimmetria del bias di negatività nell'aggiornamento di coesione (un'azione divergente costa −0.15 di coesione contro una ricompensa di +0.10 per un'azione allineata) è attribuita inline a Baumeister et al. (2001) "Bad is stronger than good." La letteratura Iannaccone (1992) sui beni di club sulla coesione di culti e comuni attraverso il sacrificio di segnale costoso *non* è implementata nel modulo attuale — non c'è alcun rito di iniziazione di segnale costoso, alcun marcatore di confine escludente oltre la semplice membership, e alcun meccanismo di rilevamento del free-rider — e la spec registra questo come un'estensione rimandata piuttosto che come una citazione attuale. Code path: `epocha/apps/agents/factions.py`.

> Stato: implementato nel codice, audit Round 2 pendente. Vedere `docs/superpowers/specs/2026-04-05-factions-leadership-design.md`.

## 8.5 Reputazione (Castelfranchi-Conte-Paolucci 1998)

Il modulo di reputazione implementa il modello normativo di reputazione di Castelfranchi, Conte e Paolucci (1998) — già in §13 — esteso con l'asimmetria del bias di negatività di Baumeister et al. (2001) sul peso relativo delle valutazioni negative rispetto a quelle positive. Il modello distingue immagine (la credenza in prima persona del valutatore sul carattere del target) da reputazione (la credenza del valutatore su ciò che gli altri credono), in modo che un agente possa agire su un target di alta reputazione/bassa immagine in modo diverso da uno di bassa reputazione/alta immagine e in modo che la propagazione della reputazione attraverso il gossip possa essere tracciata separatamente dalla propagazione dell'esperienza diretta. L'implementazione porta righe di reputazione per agente con chiave la coppia (valutatore, target), aggiornate dall'osservatore di azione quando il target esegue un'azione il cui `action_sentiment` è non nullo, con l'asimmetria del bias di negatività codificata come uno step assoluto più grande sulle azioni negative che su quelle positive (le esatte magnitudini degli step sono il debito di calibrazione che l'audit del 2026-04-12 ha segnalato: i valori sono inscritti nel modulo come costanti e citati come "ispirati a" Baumeister et al. 2001 piuttosto che derivati da una specifica misurazione empirica della dimensione dell'effetto, e il log di risoluzione audit registra questo come item centrale di convergenza per il prossimo passaggio). Il modulo `reputation.py` produce anche il payload di gossip che il cluster di propagazione del passaparola di §8.1 porta come sottotipo speciale di memoria: un aggiornamento di reputazione trasmesso a un osservatore terzo è un evento informativo la cui distorsione sotto §8.1 produce un aggiornamento di reputazione derivato al ricevente, che è la realizzazione operativa della distinzione di Castelfranchi-Conte-Paolucci tra immagine e reputazione in una simulazione multi-agente. Code path: `epocha/apps/agents/reputation.py`.

> Stato: implementato nel codice, audit Round 2 pendente. Vedere `docs/superpowers/specs/2026-04-06-reputation-model-design.md`.

## 8.6 Grafo della conoscenza

Il cluster del Grafo della Conoscenza implementa la memoria di lungo orizzonte della simulazione: il grafo per simulazione di entità, relazioni ed eventi che il context builder LLM di §3.5 interroga per ancorare la decisione per tick di ciascun agente nella storia precedente della simulazione piuttosto che ri-leggere l'intero log eventi raw. Il cluster è suddiviso in nove moduli sotto `epocha/apps/knowledge/`: `chunking.py` affetta il log eventi raw in passaggi dimensionati per LLM, `extraction.py` esegue l'estrattore di entità e relazioni guidato da LLM su ciascun chunk, `embedding.py` produce le rappresentazioni vettoriali dense di ogni chunk e di ogni nodo (il modello multilingual-e5-large è il default attuale per spec), `merge.py` deduplica i nodi estratti contro il grafo esistente, `normalizer.py` canonicalizza le forme superficiali delle entità alle loro etichette preferite, `materialization.py` riscrive il grafo consolidato sul layer di persistenza, `ontology.py` dichiara il sistema di tipi di entità e relazione, `prompts.py` raccoglie i prompt LLM per estrazione e merge, e `api.py` espone il grafo alla vista grafo della dashboard. I puntatori di letteratura nella spec sono il framework Retrieval-Augmented Generation di Lewis et al. (2020) per l'architettura più ampia retrieve-then-generate, la famiglia di sentence-embedding di Reimers e Gurevych (2019) per le rappresentazioni dense (multilingual-e5-large è la scelta di produzione attuale per la sua copertura di 100+ lingue e per le proprietà di riproducibilità), e la più ampia letteratura di ragionamento su grafi di conoscenza per la tipologia entità-relazione. La spec contrasta l'approccio Epocha con GraphRAG e con MiroFish nella sua sezione FAQ e registra la scelta di materializzare il grafo per simulazione piuttosto che attraverso simulazioni come una scelta di scope deliberata per l'MVP. Code path: `epocha/apps/knowledge/{ingestion,extraction,embedding,merge,normalizer,materialization,ontology,chunking,prompts,api}.py`.

> Stato: implementato nel codice, audit Round 2 pendente. Vedere `docs/superpowers/specs/2026-04-11-knowledge-graph-design.md`.

## 8.7 Layer base dell'economia

Il layer base dell'economia è il substrato che trasforma l'attività degli agenti in produzione, prezzi, denaro e flussi di reddito per tick; è descritto in forma narrativa sotto §3.6 di questo whitepaper e la presente sottosezione registra solo lo stato di audit e la spec sotto la quale l'audit riprenderà. Il layer base copre `production.py` (la funzione di produzione CES di Arrow et al. 1961), `monetary.py` (la diagnostica dell'identità di Fisher e il contatore di velocità), `market.py` (il tâtonnement walrasiano per Walras 1874 con il cap di iterazioni che affronta il regime di non convergenza di Scarf 1960), `distribution.py` (la decomposizione semplificata della rendita ricardiana e il flusso di salari e tasse per tick) e `initialization.py` (il seeding per template del bilancio base). Tutte e cinque le citazioni in questa lista sono già presenti in §13. L'integrazione comportamentale che si poggia su questo substrato (aspettative adattive, credito e sistema bancario, mercato immobiliare) ha completato il suo audit Round 2 ed è documentata sotto §4.2 di questo whitepaper; il substrato qui documentato no, e la narrazione di §3.6 disclaima esplicitamente lo stato Methods-grade in attesa del passaggio di audit. Code path: `epocha/apps/economy/{production,monetary,market,distribution,initialization}.py`.

> Stato: implementato nel codice, audit Round 2 pendente. Vedere `docs/superpowers/specs/2026-04-12-economy-base-design.md`.

---

# 9. Roadmap

La roadmap è ordinata per priorità piuttosto che per cronologia: il rifacimento audit sugli otto moduli emersi dal batch del 2026-04-12 è l'item gating perché ogni successivo sforzo di calibrazione e validazione dipende dal sottoinsieme auditato che venga chiuso prima. Gli item rimanenti sono elencati in un ordine grossolano di sforzo atteso e sono tracciati nel backup di memoria di lungo formato sotto `docs/memory-backup/`; i cross-reference alla nota di memoria rilevante sono inline dove esistono.

- **PRIORITÀ ALTA — Rifacimento audit avversariale Round 2 sul batch del 2026-04-12.** Gli otto moduli attualmente in §8 (cluster propagazione del passaparola: information flow, distortion, belief filter; cluster politico: government, institutions, stratification; movimento; fazioni; reputazione) portano finding aperti INCORRECT, UNJUSTIFIED, INCONSISTENT e MISSING dal batch di audit del 2026-04-12. Risoluzione e rifacimento audit di convergenza sono l'item gating prima che uno qualunque di questi moduli possa essere promosso da §8 allo stato §4, prima che i loro parametri possano essere aggiunti alle tabelle di parametri di §6, e prima che possano entrare nella campagna di validazione di §7.
- **Demografia Plan 3 (Eredità + Migrazione).** La spec di demografia di §4.1 copre mortalità, fertilità e formazione delle coppie; il Plan 3 estende la stessa metodologia audit-first all'eredità (trasferimento di proprietà e debito ai parenti superstiti alla morte di un agente) e alla migrazione demografica (la migrazione zona-zona di lungo orizzonte che complementa il movimento per tick di §8.3 con un flusso a scala generazionale). La spec è la sezione Plan 3 di `docs/superpowers/specs/2026-04-18-demography-design.md`.
- **Demografia Plan 4 (Inizializzazione, integrazione Engine, validazione storica).** Il Plan 4 collega i moduli di demografia di §4.1 — attualmente implementati e unit-testati in isolamento — al ciclo di tick live di `epocha/apps/simulation/engine.py`, fornisce la procedura di inizializzazione che seed-a una popolazione di partenza dal template per epoca, ed esegue la campagna di validazione storica di §7 contro i target Wrigley-Schofield (1981) e Human Mortality Database. Questo è il deliverable centrale che chiude la disclosure di gap di implementazione portata da §4.1 e risolve il caveat validation-pending portato da §7.5.
- **Mercati finanziari dell'economia (Spec 3 da scrivere).** L'integrazione comportamentale di §4.2 copre aspettative adattive, credito e sistema bancario, e mercato immobiliare; la prossima spec di economia estende a mercati obbligazionari ed azionari, contagio dei prezzi degli asset attraverso più banche, e il canale di prestito interbancario rimandato sotto le semplificazioni di §4.2.2. La spec non è ancora redatta; l'item di lavoro è registrato nella memoria di roadmap di lungo formato.
- **Esecuzione degli esperimenti di validazione.** La campagna specificata nel Capitolo 7 — acquisizione dei dataset, implementazione degli script, calcolo delle metriche e valutazione delle soglie — è il deliverable centrale tracciato in `docs/memory-backup/project_validation_experiments_pending.md`. L'esecuzione è legata al Plan 4 della roadmap di demografia sopra (che fornisce l'integrazione del ciclo di tick live richiesta dalla validazione) e al rifacimento audit del batch §8 (che estende la superficie di validazione ai moduli politico e di movimento).
- **Evoluzione del Knowledge Graph (aggiornamenti live dalla simulazione).** Il cluster Knowledge Graph di §8.6 attualmente materializza il grafo dal log della simulazione in passaggi batch; l'item di lavoro di evoluzione sostituisce il passaggio batch con un aggiornamento live che estrae incrementalmente entità e relazioni da ciascun tick e le fonde nel grafo esistente senza una ri-estrazione completa. La modifica mantiene il grafo aggiornato entro un ritardo limitato dal tick live piuttosto che a granularità fine-corsa, che è il prerequisito per il contesto LLM ancorato al grafo nello step di decisione per tick di §3.2.
- **Analytics psicostoriografia.** La spec di analytics in `docs/superpowers/specs/2026-04-06-analytics-psicostoriografia-design.md` copre il layer di analisi post-hoc che fa emergere pattern emergenti da una simulazione completata: traiettorie nello spazio delle fasi, confronti di coorte a livello di zona, attribuzione delle cascate di eventi, ed export di plot publication-grade necessari per il paper scientifico del deliverable finale del progetto. La spec è redatta; l'implementazione è rimandata dietro il rifacimento audit e il Plan 4.
- **Adozione PostGIS più ampia.** PostGIS è già abilitato per §3.6 con le geometrie delle zone memorizzate come poligoni WGS84; l'item di lavoro di adozione più ampia estende la superficie geospaziale alle traiettorie degli agenti (storia di posizione per tick con indici spaziali), query di distanza routata tra zone (sostituendo la distanza astratta del grafo zone di §8.3 con il calcolo di shortest-path contro la geometria effettiva), e analisi di catchment per zona per i moduli di economia e demografia.
- **Agenti multi-livello (organizzazioni, stati, coalizioni).** La popolazione Epocha attuale è un insieme piatto di agenti individuali; l'item di lavoro multi-livello estende l'ontologia degli agenti ad attori corporativi che hanno le proprie pipeline decisionali, le proprie memorie e i propri spazi di azione, con gli agenti individuali come membri e con i layer di stato e coalizione sopra il layer di organizzazione. Il frame concettuale e gli ancoraggi di letteratura sono registrati in `docs/memory-backup/project_multilevel_agents.md`; la spec non è ancora redatta.
- **Generatore narrativo.** L'item di lavoro generatore narrativo produce un romanzo storico-scientifico di forma lunga dalla simulazione completata — gli archi per zona, per coorte, per personaggio intrecciati in una narrativa publication-grade nella lingua di output scelta con citazioni complete agli eventi sottostanti della simulazione. Il frame concettuale è registrato in `docs/memory-backup/project_narrative_generator.md`; l'item di lavoro è legato alla spec di analytics sopra (che produce il materiale strutturato che il generatore intreccia) e all'item di evoluzione del Knowledge Graph (che fornisce il catalogo di entità a cui la narrativa fa riferimento).
- **Layer media (giornali, social feed).** L'item di lavoro layer media materializza la stampa in-simulazione: edizioni di giornale per tick i cui articoli sono generati dagli eventi della simulazione attraverso una pipeline editoriale LLM, analoghi di social feed per i template moderni, e l'incrocio della copertura mediatica indietro nel cluster di propagazione del passaparola di §8.1 come sottotipo speciale di evento informativo. Il frame concettuale è registrato in `docs/memory-backup/project_media_layer.md`; l'item di lavoro è legato all'item di evoluzione del Knowledge Graph sopra.

---

# 10. Discussione

Ogni scelta documentata nei capitoli precedenti porta un compromesso che vale la pena dichiarare apertamente piuttosto che nascondere dietro il verdetto di convergenza dell'audit. Il più consequenziale è il costo della cognizione LLM relativo al realismo che compra: un tick che esercita la pipeline decisionale completa dell'agente di §3.2 porta un costo di token per agente che scala con i blocchi di personalità, memoria e contesto che il prompt deve includere, e l'envelope di budget per tick quindi limita la popolazione che il simulatore può portare su un dato tier hardware piuttosto che emergere da una proprietà strutturale del modello. I moduli auditati del Plan 1 e Plan 2 accettano diverse semplificazioni deliberate per mantenere il costo per tick limitato sotto questo envelope. La Hadwiger ASFR di §4.1.2 è valutata deterministicamente all'età dell'agente piuttosto che estratta da un modello stocastico per madre del tempo-al-concepimento; i coefficienti di modulazione Becker della Tabella 4.4 sono omogenei tra tutti e cinque i template di demografia in attesa della calibrazione del Plan 4; la macchineria di credito-e-sistema-bancario Diamond-Dybvig di §4.2.2 porta una singola banca aggregata piuttosto che una popolazione di banche concorrenti con un canale di prestito interbancario; la liquidazione del mercato immobiliare di §4.2.3 è single-round take-it-or-leave-it piuttosto che una convergenza multi-round bid-ask. Nessuna di queste semplificazioni è un difetto in senso auditato — ciascuna è documentata inline nel corrispondente paragrafo di Semplificazioni di §4.x e tracciata come deliverable di calibrazione del Plan 4 — ma il loro effetto cumulativo è che il layer scientifico auditato è più snello di quanto la letteratura censita in §2 supporterebbe in linea di principio. Un secondo compromesso visibile è il gap di integrazione con l'engine che §4.1 porta: mortalità, fertilità e formazione delle coppie sono implementate e unit-testate in isolamento, ma la loro orchestrazione nel ciclo di tick live in `epocha/apps/simulation/engine.py` è il deliverable centrale del Plan 4 e non è ancora attiva nel codice di produzione, in contrasto con i moduli di economia di §4.2 che sono genuinamente live nella pipeline per tick. Infine, la campagna di validazione del Capitolo 7 è metodologica piuttosto che evidenziale al commit pinnato: target, metriche e soglie di accettazione sono specificate, ma gli esperimenti che le consumano sono tracciati sotto `project_validation_experiments_pending.md` e legati allo stesso deliverable del Plan 4.

I limiti scientifici del lavoro presente vanno oltre le semplificazioni dentro il sottoinsieme auditato. Otto moduli — il cluster di propagazione del passaparola di §8.1, il cluster delle istituzioni politiche di §8.2, movimento (§8.3), fazioni (§8.4), reputazione (§8.5), il Knowledge Graph (§8.6) e il layer base dell'economia (§8.7) — sono implementati nel codice ed esercitati da unit test ma non hanno ancora completato l'audit avversariale Round 2 che funge da gate alla promozione allo stato di Capitolo 4; i finding aperti INCORRECT, UNJUSTIFIED, INCONSISTENT e MISSING dal batch di audit del 2026-04-12 sono catalogati in `docs/scientific-audit-2026-04-12.md` e tracciati sotto `project_audit_repass_batch_2026_04_12_pending.md`. Dentro il sottoinsieme auditato, diversi valori di parametro sono seedati come euristiche di calibrazione piuttosto che derivati da una misurazione di fonte primaria: i coefficienti di modulazione Becker `β₀..β₄` dell'equazione (4.3), i coefficienti di modulazione del tasso di adattamento per agente `n_mod`, `o_mod`, `c_mod` dell'equazione (4.10), il `risk_premium = 0.5` di Stiglitz-Weiss dell'equazione (4.13) e il `CASCADE_LOSS_THRESHOLD = 0.5` di Allen-Gale del passaggio di contagio sono tutti documentati inline come parametri di design regolabili con la differenziazione per epoca rimandata al Plan 4. Lo schema a tick discreti è di per sé una scelta di modellizzazione sostanziale: gli eventi che occorrono dentro lo stesso tick — morti multiple, nascite simultanee, una vendita di proprietà e un default di prestito sullo stesso agente — sono risolti sequenzialmente all'interno dell'orchestratore per tick piuttosto che trattati come genuinamente concorrenti, che è la granularità appropriata per l'envelope di costo per tick ma che sopprime ogni interazione intra-tick che la letteratura del tempo continuo esporrebbe. Il resolver congiunto di mortalità materna di §4.1.2 è l'unico posto dove l'accoppiamento intra-tick è trattato esplicitamente, ed è trattato così precisamente perché risolvere la mortalità generica per prima e la mortalità da parto in seconda sulla stessa madre nello stesso tick produrrebbe un bias misurabile.

Dove Epocha si colloca nel paesaggio più ampio si legge meglio rispetto a tre tradizioni vicine. Le piattaforme ABM puramente rule-based (NetLogo, Mesa, Repast HPC, EURACE) eccellono nella scalabilità a popolazioni di milioni di agenti sotto regole individuali pienamente specificate, sulla forza di decenni di lavoro di ottimizzazione e una toolchain matura; il costo di quella scala è che la cognizione del singolo agente è vincolata a tutto ciò che la grammatica delle regole può esprimere, e il comportamento emergente che richiederebbe ragionamento in linguaggio naturale, memoria narrativa o deliberazione modulata dalla personalità deve essere approssimato da euristiche tarate a mano. Le simulazioni di agenti puramente LLM (Park et al. 2023 e la famiglia di esperimenti di agenti generativi che ne sono seguiti) eccellono all'estremo opposto: dozzine di agenti in un ambiente stilizzato possono esibire dinamiche sociali credibili senza alcuna grammatica comportamentale tarata a mano, sulla forza della cognizione in linguaggio naturale dell'LLM; il costo è che i substrati demografici ed economici che questi esperimenti ereditano dall'ambiente circostante sono troppo sottili per portare orizzonti pluridecennali o statistiche a livello di popolazione che la letteratura delle scienze sociali riconoscerebbe come ben formate. Il contributo di Epocha è l'ibrido: un substrato rule-based (engine economico di §3.6, engine demografico di §4.1, integrazione comportamentale di §4.2) che porta le dinamiche di popolazione sui timescale su cui la letteratura demografica ed economica opera, con la cognizione LLM stratificata in cima al substrato allo step di decisione per agente (§3.2) dove personalità, memoria e deliberazione in linguaggio naturale portano il peso esplicativo. L'ibrido paga un costo in token LLM per tick che le piattaforme puramente rule-based non pagano, ed eredita un costo in disciplina di audit che le piattaforme puramente LLM storicamente non hanno sostenuto, ma in cambio rende esplicita l'aggregazione multi-scala (individuo, fazione, stato) e ammette esperimenti di lungo orizzonte che nessuno dei due vicini può eseguire con un ancoraggio scientifico comparabile.

La classe di domande di ricerca che Epocha è progettata per abilitare segue direttamente dall'ibrido. Esperimenti di emergenza di lungo orizzonte — uno specifico assetto istituzionale, uno specifico pattern di shock, o una specifica distribuzione di personalità producono le traiettorie qualitative che il record storico esibisce nei secoli — diventano trattabili perché il substrato demografico ed economico auditato porta le dinamiche pluridecennali mentre il layer di cognizione LLM porta la variazione per agente. Esperimenti controfattuali e di intervento — cosa sarebbe successo se la Carestia Irlandese di §7.1 avesse innescato una risposta istituzionale anteriore, cosa sarebbe successo se il crollo del mercato immobiliare di §4.2.3 fosse stato preceduto da una traiettoria di confidenza bancaria differente — diventano trattabili perché la macchineria dei template per epoca rende esplicito l'intervento di parametro e l'RNG seedato di §3.4 rende l'esecuzione riproducibile. L'aggregazione multi-scala — dalla cognizione individuale attraverso il coordinamento a livello di fazione alla policy a livello di stato — diventa trattabile perché il modello di persistenza di §3.7 porta sia le righe individuali di agente sia le righe istituzionali come entità di prima classe piuttosto che come aggregati derivati. E la riproducibilità narrativa tra esecuzioni — lo stesso scenario rieseguito con lo stesso seed produce lo stesso log di decisione per agente e lo stesso arco narrativo emergente — diventa la base per il paper scientifico publication-grade che la roadmap del progetto del Capitolo 9 nomina come deliverable finale.

---

# 11. Limitazioni note

Il seguente catalogo raggruppa le limitazioni aperte per modulo. Ogni voce è deliberatamente breve — il contesto sostanziale vive nel corrispondente paragrafo di Semplificazioni di §4 o nella riga di stato di §8 — ed esiste qui come singolo inventario autoritativo per il lettore che ha bisogno della vista a livello di progetto in un unico posto. Due follow-up trasversali sottendono la maggior parte delle voci: il rifacimento audit sugli otto moduli di §8 tracciato sotto `project_audit_repass_batch_2026_04_12_pending.md` e la campagna di validazione tracciata sotto `project_validation_experiments_pending.md`.

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
- L'aggregazione di prezzi multi-zona è un merge last-write-wins di `ZoneEconomy.market_prices` piuttosto che una previsione per zona per agente.

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

**Sottosistemi progettati in attesa di audit Round 2 (§8).** Otto moduli attraverso cinque cluster portano finding aperti INCORRECT, UNJUSTIFIED, INCONSISTENT e MISSING dal batch di audit del 2026-04-12: propagazione del passaparola (information flow, distortion, belief filter); istituzioni politiche (government, institutions, stratification); movimento; fazioni; reputazione; il Knowledge Graph; il layer base dell'economia. Risoluzione e rifacimento audit di convergenza sono tracciati sotto `project_audit_repass_batch_2026_04_12_pending.md` e fungono da gate alla promozione di questi moduli da §8 allo stato §4, all'inclusione dei loro parametri nelle tabelle di calibrazione di §6 e al loro ingresso nella campagna di validazione di §7.

**Esperimenti di validazione (Capitolo 7).** La metodologia — dataset, metriche e soglie di accettazione — è specificata attraverso §7.1 a §7.3, ma la campagna sperimentale che consuma la metodologia è legata al Plan 4 ed è tracciata sotto `project_validation_experiments_pending.md`.

**Knowledge Graph (§8.6).** Il grafo è attualmente materializzato in passaggi batch dal log della simulazione; l'aggiornamento live da una simulazione in esecuzione, che è il prerequisito per il contesto LLM ancorato al grafo nello step di decisione per tick, è l'item di lavoro dedicato della roadmap del Capitolo 9.

**Limitazioni trasversali.** Le dinamiche spaziali oltre il grafo astratto delle zone non sono esercitate: PostGIS è abilitato e le geometrie delle zone sono memorizzate come poligoni WGS84 per §3.6, ma le query di distanza routata tra zone, la memorizzazione per tick di traiettorie degli agenti con indici spaziali e l'analisi di catchment per zona per i moduli di economia e demografia sono rimandate all'item di lavoro PostGIS più ampio del Capitolo 9. Lo schema a tick discreti di §3.1 risolve gli eventi intra-tick sequenzialmente all'interno dell'orchestratore per tick piuttosto che trattarli come concorrenti, con il resolver congiunto di mortalità materna di §4.1.2 come unico posto dove l'accoppiamento intra-tick è trattato esplicitamente. La gestione di eventi in tempo reale tra tick non è supportata.

---

# 12. Conclusioni

Epocha come documentato al commit pinnato spedisce un substrato demografico auditato che copre mortalità Heligman-Pollard, fertilità Hadwiger-con-Becker e formazione delle coppie Gale-Shapley con Goode 1963 (§4.1), un'economia comportamentale auditata che copre aspettative adattive Cagan-Nerlove, credito e sistema bancario Diamond-Dybvig e un mercato immobiliare ancorato a Gordon (§4.2), una pipeline decisionale di agenti guidata da LLM che consuma lo stato per tick del substrato e riscrive nel layer di persistenza (§3.2), e otto sottosistemi implementati-ma-pre-audit (§8) che coprono propagazione del passaparola, istituzioni politiche, movimento, fazioni, reputazione, il Knowledge Graph e il layer base dell'economia. L'infrastruttura runtime copre un tick engine con loop Celery auto-enqueuing, una strategia RNG seedata per fase che rende ogni esecuzione riproducibile attraverso macchine dall'hash di commit, dal seed e dallo stato iniziale del database (§3.4), un adapter di provider LLM che astrae su OpenAI vero e proprio, Groq, Gemini, OpenRouter, Together AI, Mistral, LM Studio e Ollama con rotazione delle chiavi e un limiter sliding-window backed da Redis (§3.5), e una dashboard più un layer di chat WebSocket che esponendo lo stato di simulazione live e la superficie di conversazione agente-per-agente all'operatore (§3.8).

Ciò che distingue questo codebase dal paesaggio circostante è meno i moduli individuali — la maggior parte ha antecedenti ben noti nella letteratura censita in §2 — e più la disciplina che li produce e li mantiene. Il whitepaper bilingue di §1 è un documento vivente congelato a ogni merge sul branch di sviluppo, con la companion italiana pubblicata accanto all'originale inglese; ogni formula, parametro e algoritmo nei capitoli auditati cita una fonte primaria, e le asserzioni non verificate sono segnalate inline piuttosto che presentate come fatto. Il workflow canonico a sette fasi che governa ogni sottosistema (ideazione, requisiti, plan, task breakdown, implementazione, test generale, chiusura) porta due gate pesanti e due leggeri con approvazione umana esplicita a ciascuno, e la policy di audit avversariale obbligatoria attiva il revisore `critical-analyzer` sia in fase di spec sia in fase di codice con un loop di convergenza che non chiude su "abbastanza vicino". La riproducibilità è incorporata piuttosto che retrofittata: i template per epoca portano i valori di parametro per epoca fuori dal codice sorgente e in artefatti auditabili, gli stream RNG seedati sono partizionati per simulazione, tick e fase in modo che un refactor non possa silenziosamente spostare la sequenza casuale che un sottosistema vede, e l'Appendice B registra i comandi esatti tramite i quali ogni risultato riportato può essere rigenerato da un checkout pulito pinnato all'hash di commit congelato.

Il codebase è open source sotto licenza Apache 2.0 a https://github.com/mauriziomocci/epocha, e i contributi sono benvenuti attraverso il workflow canonico a sette fasi descritto in questo paper. I lettori che desiderano estendere un modulo auditato in §4 dovrebbero aspettarsi un percorso di contribuzione spec-first con audit scientifico avversariale obbligatorio prima che qualsiasi codice venga mergiato; i lettori che desiderano avanzare uno dei moduli di §8 attraverso l'audit Round 2 troveranno i finding aperti catalogati in `docs/scientific-audit-2026-04-12.md` e tracciati sotto `project_audit_repass_batch_2026_04_12_pending.md`. La roadmap del Capitolo 9 nomina le priorità immediate — il rifacimento audit sul batch del 2026-04-12, demografia Plan 3 (eredità e migrazione), demografia Plan 4 (integrazione engine e validazione storica) e la prossima spec di economia che estende §4.2 a mercati obbligazionari ed azionari — e funge da entry point per i nuovi contributori che cercano un item di lavoro ben definito.

---

# 13. Riferimenti

<da tradurre nel Task 37 — mirror verbatim della §13 del whitepaper inglese>

---

# 14. Appendici

<da tradurre nel Task 37>

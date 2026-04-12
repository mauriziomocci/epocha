# Letture consigliate per il progetto Epocha

Risorse organizzate per area tematica, utili per chiunque voglia contribuire al progetto o approfondire i concetti alla base di Epocha.

---

## Architettura Software

| Titolo | Autore | Lingua | Note |
|--------|--------|--------|------|
| Designing Data-Intensive Applications | Martin Kleppmann | EN | Il riferimento per database, sistemi distribuiti, messaggistica. Essenziale per capire le scelte architetturali di Epocha |
| Architettura pulita (Clean Architecture) | Robert C. Martin | IT | Come strutturare software in moduli con confini chiari, dipendenze e separazione delle responsabilità |
| System Design Interview (Vol. 1 e 2) | Alex Xu | EN | Esercizi pratici di design di sistemi reali. Ottimo per allenarsi sui trade-off |
| Building Microservices | Sam Newman | EN | Riferimento per architetture a microservizi, utile per l'evoluzione futura di Epocha |

**Video:** Canale YouTube [ByteByteGo](https://www.youtube.com/@ByteByteGo) (Alex Xu) — Spiegazioni visive di architetture reali in 10-15 minuti.

---

## Product Management e MVP

| Titolo | Autore | Lingua | Note |
|--------|--------|--------|------|
| Partire leggeri (The Lean Startup) | Eric Ries | IT | Pensare in MVP, validare ipotesi prima di costruire tutto |
| Shape Up | Basecamp (Ryan Singer) | EN (gratuito online) | Come definire lo scope di un progetto e tagliarlo in modo intelligente. [basecamp.com/shapeup](https://basecamp.com/shapeup) |

---

## Sistemi complessi e simulazione

| Titolo | Autore | Lingua | Note |
|--------|--------|--------|------|
| Pensare in sistemi (Thinking in Systems) | Donella Meadows | IT | Feedback loop, punti di leva, comportamenti emergenti. Fondamentale per progettare la simulazione di Epocha |
| Complexity: A Guided Tour | Melanie Mitchell | EN | Introduzione accessibile ai sistemi complessi, reti, evoluzione, computazione |
| The Model Thinker | Scott E. Page | EN | Come usare modelli multipli per comprendere fenomeni complessi. Direttamente applicabile ai modelli scientifici di Epocha |

---

## Simulazione sociale e modelli ad agenti

| Titolo | Autore | Lingua | Note |
|--------|--------|--------|------|
| Simulazione sociale: tecniche, esempi e riflessioni | Mario Paolucci (ISTC/CNR) | IT | [Slide](https://www.cs.unibo.it/~paolucci/files/lezioSimulazioneSiena.pdf). Panoramica su simulazione sociale ad agenti, reputazione normativa, gossip come meccanismo sociale. Direttamente rilevante per information flow e belief filter di Epocha |
| Normative reputation and the costs of compliance | Castelfranchi, Conte & Paolucci (1998) | EN | Journal of Artificial Societies and Social Simulation, vol. 1 no. 3. Modello di reputazione normativa: come la reputazione influenza il costo della conformita' alle norme. Fondamento scientifico per il sistema di reputazione emergente di Epocha |
| What is the use of Gossip? A sensitivity analysis of the spreading of respectful reputation | Paolucci, Marsero & Conte (2000) | EN | In Tools and Techniques for Social Science Simulation, Physica, Heidelberg, 302-314. Analisi della propagazione del gossip nella rete sociale e il suo effetto sulla reputazione. Fonte per il distortion engine e l'information flow |
| The Psychology of Rumor | Allport & Postman (1947) | EN | Henry Holt and Company. Identificazione dei tre processi di trasmissione seriale: leveling (perdita di dettagli), sharpening (enfasi selettiva), assimilation (distorsione verso le aspettative). Fondamento del distortion engine di Epocha |
| Remembering: A Study in Experimental and Social Psychology | Bartlett (1932) | EN | Cambridge University Press. Esperimenti di riproduzione seriale che dimostrano la perdita del ~30% dei dettagli ad ogni passaggio nella catena di comunicazione. Fonte per il fattore di decay 0.7 nell'information flow |
| The Strength of Weak Ties | Granovetter (1973) | EN | American Journal of Sociology, 78(6), 1360-1380. I legami deboli sono piu' efficaci dei legami forti per la diffusione delle informazioni nella rete sociale. Rilevante per il modello di propagazione dell'information flow |
| An Integrative Model of Organizational Trust | Mayer, Davis & Schoorman (1995) | EN | Academy of Management Review, 20(3), 709-734. Modello di fiducia interpersonale: competenza, benevolenza e integrita' come fattori. Fondamento del belief filter di Epocha |
| Agreeableness: Dimension of Personality or Social Desirability Artifact? | Graziano & Tobin (2002) | EN | Journal of Personality, 70(5), 695-728. L'influenza dell'agreeableness sulla credulita' e la tendenza ad accettare informazioni. Fonte per il peso della personalita' nel belief filter |

### Economia e disuguaglianza

| Titolo | Autore | Lingua | Note |
|--------|--------|--------|------|
| Income Distribution, Political Instability, and Investment | Alesina & Perotti (1996) | EN | European Economic Review, 40(6), 1203-1228. Correlazione tra disuguaglianza (Gini), instabilita' politica e investimenti. Fonte per le soglie delle Epochal Crisis |
| Economic Origins of Dictatorship and Democracy | Acemoglu & Robinson (2006) | EN | Cambridge University Press. Modello di transizioni tra democrazia e dittatura basato su disuguaglianza e minaccia di rivoluzione. Fondamento per il sistema di transizioni di governo di Epocha |
| Why Nations Fail | Acemoglu & Robinson (2012) | EN | Crown Publishers. Istituzioni inclusive vs estrattive come determinanti del successo delle nazioni. Fondamento per il sistema di salute istituzionale |
| Corruption and Government | Rose-Ackerman & Palifka (2016) | EN | Cambridge University Press. Cause e conseguenze della corruzione sistemica. Fonte per le soglie di corruzione nelle Epochal Crisis |
| The Logic of Collective Action | Olson (1965) | EN | Harvard University Press. Perche' i gruppi si formano e come i beni pubblici vengono forniti. Fondamento per il sistema di formazione delle fazioni |
| High income improves evaluation of life but not emotional well-being | Kahneman & Deaton (2010) | EN | PNAS, 107(38), 16489-16493. Il benessere emotivo raggiunge un plateau sopra una soglia di reddito. Implementato nel sistema economico con curva di saturazione esponenziale |
| Capital-labor substitution and economic efficiency | Arrow, Chenery, Minhas & Solow (1961) | EN | Review of Economics and Statistics, 43(3), 225-250. Funzione di produzione CES con elasticita' di sostituzione. Fondamento del motore di produzione dell'economia base |
| Elements of Pure Economics | Walras (1874) | FR/EN | Tatonnement: aggiustamento iterativo dei prezzi verso l'equilibrio di mercato. Meccanismo di clearing nel modulo economico |
| The Purchasing Power of Money | Fisher (1911) | EN | Macmillan. Equazione dello scambio MV=PQ. La velocita' della moneta come variabile emergente nel modulo monetario |
| On the Principles of Political Economy and Taxation | Ricardo (1817) | EN | John Murray. Teoria della rendita fondiaria differenziale. Fondamento per la rendita emergente nel sistema di proprieta' |
| This Time Is Different: Eight Centuries of Financial Folly | Reinhart & Rogoff (2009) | EN | Princeton University Press. Crisi finanziarie, debito sovrano, bancarotta dei governi. Riferimento per la spec 2 (credito/debito) e il trigger di crisi politica da bancarotta |
| Applying General Equilibrium | Shoven & Whalley (1992) | EN | Cambridge University Press. Riferimento per l'implementazione computazionale dei modelli CGE, estensioni CES multi-fattore, algoritmi di tatonnement |
| Consumer Demand in the United States | Houthakker & Taylor (1970) | EN | Harvard University Press. Stime empiriche di elasticita' della domanda al prezzo per categorie di beni. Fonte per i valori di elasticita' nei template economici |
| Prospect Theory: An Analysis of Decision under Risk | Kahneman & Tversky (1979) | EN | Econometrica, 47(2), 263-291. Avversione alla perdita, distorsione delle decisioni sotto rischio. Fondamento per la spec 2 (distorsione economica Big Five) e per il rapporto asimmetrico nelle mobilita' di classe |
| Stabilizing an Unstable Economy | Minsky (1986) | EN | Yale University Press. Ipotesi di instabilita' finanziaria: cicli di debito che generano fragilita' sistemica. Fondamento per la spec 2 (credito/debito) e la spec 3 (crisi finanziarie) |
| Irrational Exuberance | Shiller (2000) | EN | Princeton University Press. Bolle speculative, euforia irrazionale dei mercati. Riferimento per la spec 3 (mercati finanziari) |
| Agent-based Computational Finance | LeBaron (2006) | EN | In Handbook of Computational Economics, Vol. 2. Modelli agent-based per i mercati finanziari. Riferimento per la spec 3 |
| Geography and Trade | Krugman (1991) | EN | MIT Press. Modelli gravitazionali del commercio, effetti della distanza. Riferimento per la spec 2 (commercio multi-zona con friction) |
| The Oxford History of the French Revolution | Doyle (1989) | EN | Oxford University Press. La crisi fiscale dell'Ancien Regime come trigger della Rivoluzione. Fonte per il meccanismo bancarotta-governo → crisi politica |
| Growing Artificial Societies: Social Science from the Bottom Up | Epstein & Axtell (1996) | EN | MIT Press. Fondamento per l'approccio agent-based alla simulazione economica, inclusa la distribuzione iniziale di ricchezza |

### Scienza politica e stabilita'

| Titolo | Autore | Lingua | Note |
|--------|--------|--------|------|
| Global Instances of Coups from 1950 to 2010 | Powell & Thyne (2011) | EN | Journal of Peace Research, 48(2), 249-259. Dataset e analisi dei colpi di stato nel mondo. Fonte per le condizioni di coup nel governo engine |
| Personality in Adulthood: A Five-Factor Theory Perspective | McCrae & Costa (2003) | EN | Guilford Press. Il modello Big Five della personalita'. La distanza euclidea sui Big Five e' la metrica standard per la similarita' di personalita'. Fondamento del sistema di personalita' degli agenti e del calcolo di affinita' |
| Coevolution of Neocortical Size, Group Size and Language in Humans | Dunbar (1993) | EN | Behavioral and Brain Sciences, 16(4), 681-735. Il numero di Dunbar e la struttura a livelli dei gruppi sociali. Fonte per il size penalty nella coesione delle fazioni |

---

## Database e modellazione dati

| Titolo | Autore | Lingua | Note |
|--------|--------|--------|------|
| Basi di dati | Atzeni, Ceri, Paraboschi, Torlone | IT | Il testo universitario italiano di riferimento, rigoroso e completo |
| The Art of PostgreSQL | Dimitri Fontana | EN | Specifico per PostgreSQL, molto pratico: schema, query, indici, JSONB |
| PostGIS in Action | Obe, Hsu | EN | Riferimento per PostGIS, query spaziali, GIS — direttamente utile per il World Module |

---

## Django e Python

| Titolo | Autore | Lingua | Note |
|--------|--------|--------|------|
| Two Scoops of Django | Feldman, Greenfeld | EN | Best practice per progetti Django reali: organizzazione app, settings, API |
| Django for Professionals | William S. Vincent | EN | Django con Docker, PostgreSQL, sicurezza — molto vicino allo stack di Epocha |
| Test-Driven Development with Python | Harry Percival | EN (gratuito online) | TDD specifico per Django. [obeythetestinggoat.com](https://www.obeythetestinggoat.com/) |

---

## Agenti AI e LLM

| Titolo | Autore | Lingua | Note |
|--------|--------|--------|------|
| Documentazione Claude Agent SDK | Anthropic | EN | [platform.claude.com/docs](https://platform.claude.com/docs/en/agent-sdk/overview) |
| Documentazione OpenAI Agents SDK | OpenAI | EN | [openai.github.io/openai-agents-python](https://openai.github.io/openai-agents-python/) |
| Building LLM Powered Applications | Valentina Alto | EN | Come costruire applicazioni basate su LLM, prompt engineering, RAG |
| Documentazione MCP | Anthropic | EN | Model Context Protocol per l'integrazione MCP di Epocha |

**Repository da seguire:**
- [MiroFish](https://github.com/666ghj/MiroFish) — Motore di simulazione multi-agente, riferimento diretto per Epocha
- [OASIS (camel-ai)](https://github.com/camel-ai/oasis) — Framework di simulazione sociale scalabile fino a 1M agenti
- [LangChain](https://github.com/langchain-ai/langchain) — Framework per applicazioni LLM
- [CrewAI](https://github.com/crewAIInc/crewAI) — Framework per agenti AI collaborativi

---

## Sicurezza

| Titolo | Autore | Lingua | Note |
|--------|--------|--------|------|
| OWASP Top 10 | OWASP Foundation | EN/IT | Le 10 vulnerabilità più comuni nelle web app. [owasp.org](https://owasp.org/www-project-top-ten/) |
| OWASP API Security Top 10 | OWASP Foundation | EN | Specifico per la sicurezza delle API REST |

---

## Ispirazione concettuale

### Fantascienza

| Titolo | Autore | Lingua | Perché leggerlo |
|--------|--------|--------|----------------|
| Ciclo della Fondazione | Isaac Asimov | IT | L'ispirazione principale di Epocha: psicostoriografia, Piano Seldon, Crisi Seldon, Seconda Fondazione, Gaia, Enciclopedia Galattica |
| Dune | Frank Herbert | IT | Monopolio di risorse, culture forgiate dall'ambiente, politica galattica, ecologia planetaria |
| The Expanse (serie) | James S.A. Corey | IT (parziale) | Divergenza biologica umana, Core vs Periferia, politica interplanetaria realistica |
| Neuromante | William Gibson | IT | Cyberpunk, mondi virtuali, megacorporazioni, identità digitale |
| Blade Runner / Do Androids Dream of Electric Sheep? | Philip K. Dick | IT | Cosa significa essere umani, bioingegneria, distopia |
| 1984 | George Orwell | IT | Sorveglianza, controllo sociale, propaganda, totalitarismo |
| Il mondo nuovo (Brave New World) | Aldous Huxley | IT | Ingegneria sociale, caste genetiche, controllo tramite piacere |

### Storia e sociologia

| Titolo | Autore | Lingua | Perché leggerlo |
|--------|--------|--------|----------------|
| La Muqaddima | Ibn Khaldun | IT | Cicli delle civiltà, asabiyyah (coesione sociale), nascita e caduta degli imperi |
| Armi, acciaio e malattie | Jared Diamond | IT | Perché alcune civiltà hanno dominato e altre no. Geografia, risorse, epidemie come motori della storia |
| Ascesa e declino delle grandi potenze | Paul Kennedy | IT | Pattern di sovra-estensione imperiale, cicli di potere, economia e militarismo |
| Sapiens: Da animali a dèi | Yuval Noah Harari | IT | Storia dell'umanità dalle origini a oggi, rivoluzioni cognitive, agricole, scientifiche |
| Il Principe | Niccolò Machiavelli | IT | Politica, potere, leadership — scritto 500 anni fa, ancora attualissimo |
| La ricchezza delle nazioni | Adam Smith | IT | Fondamenti dell'economia moderna, divisione del lavoro, mercati |
| Il Capitale | Karl Marx | IT | Critica del capitalismo, classi sociali, disuguaglianza — l'altra faccia della medaglia |

### Futurologia

| Titolo | Autore | Lingua | Perché leggerlo |
|--------|--------|--------|----------------|
| Il futuro dell'umanità | Michio Kaku | IT | Colonizzazione spaziale, scala di Kardashev, terraforming, basato su scienza reale |
| Homo Deus | Yuval Noah Harari | IT | Il futuro dell'umanità: AI, bioingegneria, immortalità, dataismo |
| La singolarità è vicina | Ray Kurzweil | IT | Singolarità tecnologica, convergenza AI-biotech-nanotech |

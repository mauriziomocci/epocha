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

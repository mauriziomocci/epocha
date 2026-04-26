# Spec di design — Catchup di README e Whitepaper bilingue

**Data**: 2026-04-26
**Branch**: `feature/readme-and-whitepaper-catchup`
**Base commit**: `3202800` (su `develop`)
**Status**: in fase 2 (Requirements) — heavy gate dopo approvazione utente

---

## 1. Problema

Due artefatti di documentazione del progetto Epocha sono fuori sincrono rispetto allo stato corrente del codice in `develop`:

1. `README.md` e `README.it.md` (493 e 493 righe) sono fermi a febbraio 2026, prima dell'introduzione di Knowledge Graph, Economy base+behavioral, Demography Plan 1+2, e prima della formalizzazione del workflow canonico a 7 fasi e delle nuove regole permanenti (model selection policy, italian-specs, whitepaper bilingue).
2. I whitepaper scientifici bilingue, richiesti dalla regola permanente `feedback_whitepaper_bilingual.md`, **non esistono**: non c'è alcuna directory `docs/whitepaper/`.

La regola di progetto impone che entrambi siano aggiornati e coerenti col codice mergiato in `develop` prima di intraprendere il prossimo subsystem rilevante (Demography Plan 3 — Inheritance + Migration).

Questa branch produce entrambi gli artefatti in un'unica iterazione coordinata, evitando divergenze di framing tra i due documenti.

## 2. Soluzione proposta

Strutturare la branch come una mini-iterazione del workflow canonico (fasi 1-7) con due deliverable: il whitepaper bilingue (autoritativo) e il README bilingue (entry-point operativo distillato dal whitepaper). L'ordine è: **whitepaper EN → whitepaper IT → README EN → README IT**, perché un singolo framing autoritativo deciso una volta sola elimina il rischio di divergenza tra documenti.

Sette decisioni architetturali sono state ratificate in fase 2 di brainstorming (vedi sezione 7 più sotto).

## 3. Architettura del whitepaper

### 3.1 Struttura — hybrid stratificato

Il whitepaper distingue tre livelli di maturità per ogni sottosistema descritto:

| Livello | Cap. whitepaper | Criterio | Trattamento |
|---|---|---|---|
| **Audited** (CONVERGED) | §4 Methods | Adversarial scientific audit CONVERGED su spec o codice | Background → Model → Equations (numerate) → Parameters (con citazione primary-source verificata) → Algorithm → Simplifications → Status header |
| **Implemented, audit pending** | §8 Designed Subsystems | Codice in `develop` ma audit non eseguito o solo Round 1 senza re-audit | Paragrafo 5-10 frasi + link a spec + status esplicito |
| **Specified or planned** | §9 Roadmap | Solo design o solo idea | Voce in lista breve |

### 3.2 Indice analitico

```
Frontmatter: Title / Authors / Affiliation / Date / Version / Frozen-at-commit
Abstract (200-300 parole)
Keywords (5-8)

1. Introduction
   1.1 Context (psychohistory computazionale, agent-based social simulation)
   1.2 Research gap addressed
   1.3 Contributions
   1.4 Document structure & status legend

2. Background and Related Work
   2.1 Agent-based modeling of societies
   2.2 LLM-driven simulations e ruolo della personalita'
   2.3 Demographic micro-simulation
   2.4 Economic agent-based models
   2.5 Reputation e information diffusion in MAS

3. System Architecture
   3.1 Tick engine and time scales
   3.2 Agent decision pipeline (Big Five + memory + LLM)
   3.3 Cross-module integration contracts (treasury, subsistence, outlook)
   3.4 RNG strategy and reproducibility
   3.5 LLM provider adapter and rate limiting
   3.6 Economic substrate (production CES, monetary, market clearing, distribution)
       — descrizione implementativa con literature pointer, NO Methods-grade claim
   3.7 Persistence model
   3.8 Interaction layer (Dashboard, Chat WebSocket)

4. Methods — Audited Modules
   4.1 Demography (single chapter, 3 sub-sections)
       Status header: spec audit CONVERGED 2026-04-18 round 4, code Plan 1+2 implemented
       4.1.1 Mortality model (Heligman-Pollard 1980 + scipy fitting)
       4.1.2 Fertility model (Hadwiger 1940 ASFR + Becker 1960 modulation + Malthusian ceiling Ashraf-Galor 2011)
       4.1.3 Couple formation & dissolution (Gale-Shapley 1962 + Goode 1963 arranged marriage)
   4.2 Economy — Behavioral integration (single chapter, 3 sub-sections)
       Status header: spec audit CONVERGED 2026-04-15, code implemented
       4.2.1 Adaptive expectations (Cagan 1956)
       4.2.2 Credit & banking (Diamond-Dybvig 1983, fractional reserve)
       4.2.3 Property market (zone-based listings, mortgage logic)

5. Implementation
   5.1 Repository layout (mappa app Django)
   5.2 Module-to-spec mapping (tabella)
   5.3 LLM provider adapter and rate limiting (link al setup LM Studio)
   5.4 Persistence model details

6. Calibration
   6.1 Parameter tables per modulo audited (consolidate da §4)
   6.2 Era templates e tunable heuristics (5 file JSON)
   6.3 Fitting procedures (es. scipy.curve_fit per Heligman-Pollard)

7. Validation Methodology
   7.1 Target datasets per modulo audited (HMD, Wrigley-Schofield, Mokyr, Hajnal, con DOI)
   7.2 Comparison metrics (RMSE, KS test, log-likelihood)
   7.3 Acceptance thresholds
   7.4 Reproducibility commands
   7.5 Status: validation experiments specified, not yet executed
       (riferimento a future companion paper / appendice D)

8. Designed Subsystems (implemented, audit pending o nessun audit)
   Per ognuno: 5-10 frasi + link a spec + status esplicito.
   8.1 Cluster "Rumor propagation": Information Flow + Distortion + Belief Filter
       (audit batch 2026-04-12 + remediation, Round 2 pending)
   8.2 Cluster "Political institutions": Government + Institutions + Stratification
       (audit batch 2026-04-12 + remediation, Round 2 pending)
   8.3 Movement (audit batch 2026-04-12 + remediation, Round 2 pending)
   8.4 Factions (audit batch 2026-04-12 + remediation, Round 2 pending)
   8.5 Reputation (Castelfranchi-Conte-Paolucci 1998)
       (audit batch 2026-04-12 + remediation, Round 2 pending)
   8.6 Knowledge Graph (RAG + ontology + chunking + embedding) — no audit yet
   8.7 Economy base layer (production CES, monetary, market, distribution)
       — descrizione gia' presente in §3.6, qui solo riferimento + lista citation
       da auditare. No formal audit yet.

9. Roadmap (planned, not yet specified or in design)
   - Demography Plan 3 (Inheritance + Migration)
   - Demography Plan 4 (Init + Engine + Validation execution)
   - Re-audit pass on 2026-04-12 batch (8 modules) — HIGH PRIORITY
   - Economy financial markets (Spec 3 da scrivere)
   - Analytics psicostoriografia
   - PostGIS migration
   - Multi-level agents (individui, organizzazioni, stati)
   - Narrative generator
   - Media layer (giornali, social feed, cronaca)

10. Discussion (general trade-offs, scientific limits)

11. Known Limitations (consolidated)

12. Conclusions

13. References (Author-Date, DOI/URL)

14. Appendices
    A. Full parameter tables (con provenance)
    B. Reproducibility (commit hash, dependencies pinned, seed list, exact commands)
    C. Era templates JSON schema e i 5 file in source form
```

### 3.3 Versioning come living document

Header globale del whitepaper indica `Version 0.X — frozen at commit <hash>`. Inoltre **ogni capitolo `4.x`** ha un mini-header `> Status: <implemented|specified|planned> as of commit <hash>, audit <CONVERGED date|pending>`. Quando il codice di un modulo cambia in `develop`, lo stesso commit aggiorna il capitolo (vedi regola di doc-sync §6).

### 3.4 Politica di citazione

Tutte le citazioni in §4 (Methods) sono **primary-source strict**: per ogni formula, parametro, algoritmo, la fonte primaria (paper originale, libro originale) è citata con autore-anno-DOI. Le spec interne **non** sono accettate come fonte: se la spec cita Hadwiger 1940, il whitepaper cita Hadwiger 1940 direttamente, dopo verifica diretta.

Per §3 (Architecture, descrittivo) e §8 (paragrafi brevi) le citazioni sono "literature pointer" — riferimento bibliografico canonico anche da textbook/enciclopedia, senza claim di fidelity verificata.

Un adversarial bibliography audit (§5.4) verifica ogni citazione di §4 contro la fonte reale prima del merge.

### 3.5 Validation methodology only

§7 documenta come validare ogni modulo (dataset target con DOI, metriche, threshold, comando esatto), ma **non** esegue i benchmark. Status dichiarato esplicitamente: "validation experiments specified, not yet executed". L'esecuzione è tracked come follow-up dedicato (vedi `project_validation_experiments_pending.md`), pre-requisito alla submission paper.

### 3.6 Output bilingue

Due file:
- `docs/whitepaper/epocha-whitepaper.md` (EN, autoritativo)
- `docs/whitepaper/epocha-whitepaper.it.md` (IT, traduzione 1:1)

Stessa numerazione capitoli, stesse equazioni, stessa bibliografia (References è identico). Adversarial EN-IT consistency audit verifica che la traduzione non introduca/perda contenuti scientifici.

## 4. Architettura del README

### 4.1 Filosofia

README diventa **entry-point tecnico/developer**, non documento "che dice tutto". Deepfeatures e narrativa migrano nel whitepaper. Il README rimanda al whitepaper per le risposte autorevoli.

### 4.2 Struttura target (~200 righe ciascuno, oggi 493)

```
# Epocha
[language switch] | [badges]

> One-line tagline.

[banner image / screenshot — placeholder]

## Vision (4-5 frasi compatte: psychohistory computazionale,
   agenti LLM con personalita', crisi emergenti, multiscala)

## Authoritative documentation
- Whitepaper (EN): docs/whitepaper/epocha-whitepaper.md
- Whitepaper (IT): docs/whitepaper/epocha-whitepaper.it.md
- Project conventions: CLAUDE.md
- Recommended reading: docs/letture-consigliate.md

## Quickstart
   Prerequisites — Run locally — Run tests — LLM provider

## Project Structure (mappa app Django compatta)

## Status (tabella sintetica)
   Module                    Implemented   Audited
   Demography (Plan 1+2)     yes           yes (CONVERGED)
   Economy behavioral        yes           yes (CONVERGED)
   Economy base              yes           pending
   Reputation                yes           pending (Round 2)
   Other modules (...)       yes           pending (Round 2)
   Demography Plan 3+4       no            n/a

## Roadmap (3-5 righe + link al cap. 9 del whitepaper)

## Contributing
   - Workflow: 7-phase canonical (link CLAUDE.md)
   - Branch naming: feature/* fix/* refactor/*
   - Commits: Conventional Commits, no AI attribution, no emoji
   - Code style: ruff
   - Tests: pytest --cov=epocha -v
   - Whitepaper-code doc sync rule (link CLAUDE.md)

## License
   Apache 2.0

## Citing Epocha
   BibTeX snippet che punta al whitepaper
```

`README.it.md` è traduzione 1:1 con stesse sezioni, link al whitepaper IT.

## 5. Workflow operativo

### 5.1 Branch e fasi

Branch: `feature/readme-and-whitepaper-catchup` (creata da `develop` a `3202800`).

Mappatura alle fasi canoniche:

- Fase 1 Ideation: chat
- Fase 2 Requirements: questo documento (heavy gate al termine)
- Fase 3 Architectural Plan: piano dei blocchi (sotto-sezione 5.2)
- Fase 4 Task Breakdown: file `docs/superpowers/plans/2026-04-26-readme-and-whitepaper-catchup-plan.md` con checkbox
- Fase 5 Implementation: esecuzione task-per-task
- Fase 6 General Test + 3 adversarial audits (heavy gate)
- Fase 7 Closure (merge no-ff, sync memorie, schedule follow-up)

### 5.2 Blocchi di implementazione (fase 5)

| Blocco | Contenuto | Modello consigliato | Task stimati |
|---|---|---|---|
| **W1 Whitepaper foundation** | Frontmatter + scaffold tutti i capitoli con header e placeholder + cap. 1 Introduction + cap. 2 Background + cap. 3 System Architecture + cap. 13 References iniziale | Opus 4.7 | ~7-10 |
| **W2 Methods per modulo audited** | §4.1 Demography (3 sub-sections) + §4.2 Economy Behavioral (3 sub-sections), ogni sub-section: draft + review 8-point + bibliography micro-check | Sonnet draft + Opus su decisioni scientifiche | ~12-18 |
| **W3 Whitepaper completion** | §5 Implementation + §6 Calibration + §7 Validation Methodology + §8 Designed Subsystems + §9 Roadmap + §10-12 Discussion/Limitations/Conclusions + §14 Appendices | Opus 4.7 (Discussion, Limitations); Sonnet (Appendices meccaniche) | ~10-14 |
| **W4 Translation IT** | Traduzione 1:1 di tutto il whitepaper EN in `epocha-whitepaper.it.md` | Sonnet 4.6 con review consistenza Opus a fine blocco | ~8-12 |
| **R README** | Riscrittura `README.md` (EN) + `README.it.md` (IT) seguendo skeleton §4.2, link cross-pubblicati | Sonnet 4.6 + review consistenza Opus | ~4-6 |

Totale stimato: 41-60 task di fase 5.

### 5.3 Audit di fase 6 (heavy gate)

Tre adversarial audit indipendenti, dispatched come subagent `critical-analyzer`:

1. **Bibliography audit del whitepaper EN** — mandato di verificare ogni citazione (autore, anno, titolo, claim attribuito) contro fonte primaria reale. Output: tabella INCORRECT/UNJUSTIFIED/INCONSISTENT/MISSING/VERIFIED. Loop fino a CONVERGED.
2. **Scientific consistency audit** — verifica che ogni capitolo §4 sia coerente col codice implementato (capitolo afferma X, codice fa X). Loop fino a CONVERGED.
3. **EN ↔ IT consistency audit** — verifica che la traduzione italiana non introduca/perda contenuti scientifici, formule, parametri.

Solo dopo i 3 audit CONVERGED → heavy gate umano (utente).

### 5.4 Closure (fase 7)

- Sync memoria backup (`docs/memory-backup/`) — copia tutti i `.md` da memoria live
- Merge `feature/readme-and-whitepaper-catchup` → `develop` con `--no-ff`
- Push develop
- Aggiornamento memorie progetto (whitepaper + README sincronizzati al commit X)
- Aggiornamento del frontmatter del whitepaper con commit hash effettivo del merge
- Verifica che il follow-up "Validation experiments execution" sia loggato come priorità (memoria già esistente)
- Verifica che il follow-up "Re-audit pass batch 2026-04-12" sia loggato come priorità alta post-Plan 3 (memoria già esistente)
- Sync e ripristino della rotta verso Plan 3 Demography (Inheritance + Migration)

## 6. Regole operative introdotte da questa branch

### 6.1 Whitepaper-code doc-sync rule

Ogni PR che modifica codice di un modulo descritto in `§4.x` del whitepaper deve aggiornare il rispettivo capitolo nello stesso commit, oppure giustificare in PR description perche' non serve. Mapping iniziale:

| Path codice | Capitolo whitepaper |
|---|---|
| `epocha/apps/demography/` | §4.1 (EN + IT) |
| `epocha/apps/economy/{expectations,credit,banking,property_market}.py` | §4.2 (EN + IT) |

Enforce iniziale: PR review checklist + sezione "Contributing" del README + linea in CLAUDE.md sotto Documentation Sync. NO pre-commit hook (YAGNI per mapping di 2 entry e developer singolo).

Promozione a hook quando: mapping cresce a 6-8 entry (post re-audit batch 2026-04-12), oppure si aggiungono contributor esterni.

Memoria di riferimento: `feedback_whitepaper_doc_sync.md`.

### 6.2 Whitepaper promotion pipeline

Quando un modulo del cap. 8 raggiunge audit CONVERGED, segue procedura standard documentata in `project_whitepaper_promotion_pipeline.md` per essere promosso a `4.x`. Branch dedicato `whitepaper-promote/<modulo>`, aggiornamento di whitepaper EN+IT, README EN+IT status table, mapping doc-sync, e adversarial audit pass sulla nuova sotto-sezione.

## 7. Decisioni architetturali ratificate (Three-Step Design log)

Durante la fase 2 di brainstorming sono state ratificate sette decisioni di scope, ognuna con alternative considerate.

| ID | Decisione | Opzione scelta | Alternative considerate | Motivazione |
|---|---|---|---|---|
| D1 | Scope whitepaper | Hybrid stratificato (§4 audited + §8 implementati ma audit pending + §9 planned) | (A) Solo implementati e auditati; (B) Vision-grounded full architecture | Rispetta rule "no formula without verified source" su §4; non butta via il design lavoro su §8; Roadmap onesta su §9 |
| D2 | Politica citazione | Primary-source strict + adversarial bibliography audit | (B) Spec-as-bridge; (C) Tiered | Publication-grade requirement; eredita errori (Chandra 1999) se accettiamo bridge |
| D3 | Validation | Methodology only + follow-up scheduled per execution | (A) Full validation now; (C) Partial opportunistic | Evita scope creep di giorni nella branch; mantiene rigore metodologico |
| D4 | Scope README | Technical entry-point + Vision block 4-5 frasi | (A) Vetrina aggiornata; (C) Hybrid | Whitepaper diventa il documento autorevole, README non duplica |
| D5 | Versioning whitepaper | Snapshot per sezione + doc-sync rule per merge | (B) Versione globale + changelog; (C) Hybrid | L'unico modello che rende verificabile la regola "always in sync" |
| D6 | Ordine di lavoro | Whitepaper prima, README distillato dopo | (A) README prima; (C) Parallelo per sezione | Singolo framing autoritativo deciso una volta sola; branch non e' pubblica durante il lavoro |
| D7 | Scope §4 Methods | Solo Demography + Economy Behavioral (CONVERGED) | (A) Tutto il codice; (C) Tier intermedio per non-auditati | Dopo verifica: nessun altro modulo e' formalmente CONVERGED. Reputation/altri 2026-04-12 hanno remediation senza Round 2 |

### 7.1 Critical self-review (Step 2)

Cinque difetti rilevati nella prima proposta e corretti:

1. **Asimmetria di granularità**: 3 sub-cap per Demography vs 2 per 7 modelli Economy → ricomposta in 1 cap. con sub-sections per modulo.
2. **Audit Economy base in W2 = scope creep**: rischio 50+ findings, settimane di slittamento → spostato in §3.6 (descrizione architetturale senza claim Methods-grade).
3. **Reputation rimpallata all'utente**: verificata direttamente — audit batch 2026-04-12 + 3 commit remediation MA nessun Round 2 → NON CONVERGED → §8.5.
4. **Cap. 8 conteneva infrastruttura** (Dashboard, Chat, LLM Adapter, Sim Engine) → spostati in §3 (Architecture) o §5 (Implementation); cap. 8 contiene solo modelli scientifici implementati ma non auditati.
5. **Doc-sync senza enforcement** → introdotta regola §6.1 con escalation graduale (checklist → script diagnostico → hook).

### 7.2 Second self-review (Step 3)

Re-lettura delle correzioni step 2: nessuna ha introdotto nuovi gap. Lo scope ridotto di §4 (2 capitoli invece di 6) non lascia content "orfano" perche' tutto il resto trova posto in §3 (substrate descrittivo) o §8 (paragrafi brevi). La doc-sync rule incrementale è coerente con YAGNI.

## 8. Trade-off accettati e known limitations

- **Whitepaper inizialmente "piccolo"** rispetto al codebase (solo 2 capitoli §4 con depth completa). Trade-off accettato: la regola publication-grade non ammette mezze misure; la struttura è forward-compatible — i moduli del cap. 8 si promuovono naturalmente a `4.x` dopo re-audit.
- **Validation experiments deferiti**: il whitepaper non è "publication-ready paper" senza esperimenti eseguiti, ma è "publication-grade documentation". Il follow-up dedicato è loggato.
- **README rimane obsoleto durante il lavoro**: la branch non è pubblica, l'utente esterno vede solo il merge finale. Non-problema operativo.
- **Doc-sync via discipline-based**: dipende dalla disciplina del developer singolo. Promozione a hook prevista quando il mapping cresce o si aggiungono contributor.
- **Bilingue richiede sync dopo ogni cambio**: la traduzione IT può divergere se non aggiornata insieme all'EN. Mitigazione: EN-IT consistency audit di fase 6 + regola doc-sync.

## 9. Alternative considerate

- **Skip whitepaper, fare solo README**: viola la regola permanente `feedback_whitepaper_bilingual.md`. Scartata.
- **Whitepaper monolingua EN, IT solo a fine progetto**: viola la regola permanente. Scartata.
- **Affidare il whitepaper interamente a Sonnet**: viola la model selection policy per un documento scientifico ad alta criticità. Mantenuto Opus per W1, W3 e tutti gli audit; Sonnet solo per draft Methods atomici e traduzione IT con review Opus.
- **Bundling con Plan 3 Demography**: aumenta il diff del PR finale, peggiora la review. Scartata: branch separata permette merge incrementale.

## 10. FAQ

**Q: Perche' il whitepaper e' bilingue mentre il SPEC e' solo italiano?**
A: La regola `feedback_italian_specs.md` (specs in italiano per approvazione, niente sync bilingue) si applica ai documenti di design **interni** che servono al workflow. Il whitepaper invece e' un artefatto pubblico, scientifico, destinato anche a community/peer review internazionali — quindi entrambe le lingue sono necessarie. EN e' autoritativo (citabile in venue scientifici), IT e' traduzione fedele per accesso locale.

**Q: Cosa succede se durante la scrittura del whitepaper scopriamo che un capitolo Methods non regge per via di errori nel codice?**
A: Escalation a Opus. Si valuta caso per caso:
1. Errore minore di citazione → fix immediato nel commit del capitolo, no impatto su codice.
2. Errore di formula con codice corretto → fix nel capitolo, no impatto su codice.
3. Errore di formula con codice sbagliato → STOP scrittura whitepaper, apri branch fix sul codice, audit, merge in develop, RIPRENDI whitepaper. Il whitepaper non documenta cose false.

**Q: Come gestiamo le immagini/diagrammi/plot del whitepaper?**
A: In questa iterazione il whitepaper è text-first. Diagrammi schematici (architecture, pipeline) possono essere aggiunti come ASCII art o come TODO con placeholder; plot validation arrivano col follow-up "Validation experiments execution". Path raccomandato per assets: `docs/whitepaper/figures/` (creato solo quando il primo asset viene aggiunto).

**Q: Il README ha link al whitepaper, ma la branch non ha ancora il whitepaper merged. Come evitiamo placeholder pubblicati?**
A: Whitepaper-first è esattamente la risposta: il README si scrive solo dopo che il whitepaper esiste nel filesystem (anche solo nella branch), quindi i link puntano a file reali. Quando la branch si merge, entrambi diventano live insieme.

**Q: Quanto effort totale stima questa branch?**
A: 41-60 task di fase 5 + 3 round audit di fase 6 (loop fino a CONVERGED) + closure. Con pacing tipico Demography (2-3 task/giorno per Sonnet, 1-2 per Opus) → 3-5 settimane di calendario. Critico mantenere disciplina del task-per-task per non sforare.

**Q: Cosa succede se un re-audit del cap. 8 ha luogo durante la branch?**
A: Improbabile per come è organizzato il roadmap (re-audit batch 2026-04-12 e' post-Plan 3, quindi dopo questa branch). Se accade comunque, il modulo si promuove a `4.x` con la procedura standard `project_whitepaper_promotion_pipeline.md`, aggiunta in fondo alla branch corrente.

**Q: Cosa fare se l'utente cambia idea su una decisione D1-D7 a meta' branch?**
A: Stop work, riapri brainstorming sulla decisione modificata, propaga alle decisioni dipendenti, aggiorna questa spec, ripeti heavy gate fase 2. Solo dopo riprendi.

**Q: Il follow-up "Validation experiments execution" come si lega a questa branch?**
A: E' indipendente. La memoria `project_validation_experiments_pending.md` lo logga come pre-requisito di submission paper, non blocco di sviluppo simulativo. Priorita' media. Lo schedule effettivo è discrezione utente.

## 11. Bibliografia preliminare (verra' espansa in §13 del whitepaper, qui solo seed)

Le seguenti citazioni sono attese nel whitepaper §4 e §13 (verifica primary-source obbligatoria in audit di fase 6):

- Heligman, L., Pollard, J.H. (1980). The age pattern of mortality. *Journal of the Institute of Actuaries* 107(1), 49-80.
- Hadwiger, H. (1940). Eine analytische Reproduktionsfunktion für biologische Gesamtheiten. *Skandinavisk Aktuarietidskrift* 23, 101-113.
- Becker, G.S. (1960). An economic analysis of fertility. In *Demographic and Economic Change in Developed Countries*, NBER, 209-240.
- Ashraf, Q., Galor, O. (2011). Dynamics and stagnation in the Malthusian epoch. *American Economic Review* 101(5), 2003-2041.
- Gale, D., Shapley, L.S. (1962). College admissions and the stability of marriage. *American Mathematical Monthly* 69(1), 9-15.
- Goode, W.J. (1963). *World Revolution and Family Patterns*. Free Press.
- Cagan, P. (1956). The monetary dynamics of hyperinflation. In M. Friedman (ed.) *Studies in the Quantity Theory of Money*. University of Chicago Press, 25-117.
- Diamond, D.W., Dybvig, P.H. (1983). Bank runs, deposit insurance, and liquidity. *Journal of Political Economy* 91(3), 401-419.
- Castelfranchi, C., Conte, R., Paolucci, M. (1998). Normative reputation and the costs of compliance. *JASSS* 1(3) — limitato a §8 perche' attualmente NON CONVERGED.
- Wrigley, E.A., Schofield, R.S. (1981). *The Population History of England 1541-1871*. Cambridge UP — citato in §7 Validation methodology.
- Mokyr, J. (1985). *Why Ireland Starved: A Quantitative and Analytical History of the Irish Economy 1800-1850*. Allen & Unwin — citato in §7.
- Hajnal, J. (1965). European marriage patterns in perspective. In D.V. Glass, D.E.C. Eversley (eds.) *Population in History*, Edward Arnold — citato in §7.
- Falconer, D.S. (1996). *Introduction to Quantitative Genetics* (4th ed.) — citato per Demography Plan 1 inheritance, qui §3.

# Feature Specification: Economy base layer — primo audit scientifico avversariale e promozione §8.2 → §4

**Feature Branch**: `20260715-132752-economy-base-layer-audit`

**Created**: 2026-07-15

**Status**: Draft (findings in attesa dell'output del workflow di audit)

**Input**: chiudere il debito di audit del substrato economico (whitepaper §8.2 "Economy base layer"), uno dei due moduli residui in §8 in attesa del PRIMO audit scientifico avversariale (l'altro è §8.1 Knowledge Graph). Portare i cinque moduli del substrato a CONVERGED e promuoverli da §8.2 a un capitolo §4 Methods.

## Contesto e problema

Il substrato economico vive in `epocha/apps/economy/` e trasforma l'attività degli agenti in produzione, prezzi, moneta e flussi di reddito per-tick. È descritto in forma narrativa nel whitepaper §3.6 e catalogato in §8.2 con stato "audit pendente". A differenza dei cluster della campagna F-CAMPAIGN (che erano re-pass Round 2 di moduli già auditati nel batch 2026-04-12), questo substrato NON era nel batch 2026-04-12: è quindi al suo PRIMO audit scientifico, non a un re-pass. Il §9 del whitepaper lo conferma: "pending their first scientific audit pass".

Il layer comportamentale che gli sta sopra — aspettative adattive, credito e banca, mercato immobiliare — è già §4.2 CONVERGED. Il substrato che quel layer consuma no: i suoi prezzi, trade e flussi di reddito alimentano §4.2 ma non hanno ancora superato la catena di citazione line-by-line richiesta per lo stato §4.

Cinque moduli in scope (1110 righe totali), con le formule e le fonti dichiarate:

1. `production.py` (211 righe) — funzione di produzione CES `Q = A·[Σ αᵢ Xᵢ^ρ]^(1/ρ)`, `ρ = (σ-1)/σ`, fallback Cobb-Douglas vicino a `σ=1` e Leontief vicino a `σ=0`. Fonti: Arrow, Chenery, Minhas & Solow (1961); estensione multi-fattore Shoven & Whalley (1992).
2. `monetary.py` (148 righe) — identità di Fisher come diagnostica (non regola di prezzo) + contatore di velocità. Fonte: Fisher (1911).
3. `market.py` (332 righe) — tâtonnement Walrasiano (Walras 1874), prezzi aggiustati proporzionalmente all'eccesso di domanda con cap di iterazione per il regime di non-convergenza a 3+ beni (Scarf 1960).
4. `distribution.py` (137 righe) — rendita Ricardiana semplificata (Ricardo 1817) + flusso piatto di salari e tasse.
5. `initialization.py` (282 righe) — seeding del bilancio di base per template d'era.

## Procedura (campaign audit-first, adattata al primo audit)

Segue la procedura standard di audit del progetto (constitution, Adversarial Scientific Audit + Mandatory convergence loop), con la variante che questo è un Round 1, non un Round 2:

1. **Audit Round 1** (questo branch, fase 2): audit avversariale multi-agente modulo-per-modulo contro le fonti citate; ogni finding verificato in modo avversariale su due lenti (accuratezza-fonte e materialità); sintesi cross-modulo con verdetto per-modulo. Output = report categorizzato INCORRECT/UNJUSTIFIED/INCONSISTENT/MISSING/VERIFIED. **Materializzato dal workflow `audit-workflow.js` di questo branch.**
2. **Fix**: risolvere ogni INCORRECT e UNJUSTIFIED; documentare o risolvere INCONSISTENT e MISSING. Test-first dove il fix è comportamentale; per correzioni di sole citazioni/parametri, aggiornare docstring con la fonte o il tag "tunable heuristic".
3. **Re-audit Round 2**: verificare che ogni finding sia risolto e cercare nuovi problemi introdotti dai fix. Loop fino a CONVERGED.
4. **Promozione whitepaper**: promuovere il substrato da §8.2 a un nuovo capitolo §4.x Methods (EN + IT speculari), con le formule numerate, i parametri nelle tabelle di calibrazione §6, e l'ingresso nella superficie di validazione §7. Procedura in [[project_whitepaper_promotion_pipeline]].
5. **README + tracking**: aggiornare la status table dei README se rilevante; aggiornare la memoria tracker §8 residuo (resta il solo §8.1 Knowledge Graph dopo questa promozione); frozen-pin al merge.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Substrato scientificamente difendibile (Priority: P1)

Un revisore in peer review che legge il futuro §4.x del substrato deve trovare ogni formula con la sua fonte primaria verificata, ogni costante giustificata o dichiarata tunable, ogni semplificazione documentata con cosa si perde.

**Why this priority**: è l'intero scopo dell'audit e la precondizione per la promozione da §8 a §4.

**Independent Test**: il report di audit Round 2 dichiara CONVERGED per tutti e cinque i moduli; zero INCORRECT/UNJUSTIFIED residui.

**Acceptance Scenarios**:

1. **Given** il modulo `production.py`, **When** auditato contro Arrow et al. (1961), **Then** la forma CES, gli esponenti, e i confini dei fallback Cobb-Douglas/Leontief corrispondono alla fonte o le divergenze sono documentate come scelte esplicite.
2. **Given** ciascuno dei cinque moduli, **When** completato il loop di convergenza, **Then** ogni costante è citata o taggata tunable e ogni semplificazione è documentata.

### User Story 2 - Comportamento invariato dai fix di citazione (Priority: P1)

I fix che sono correzioni di sole citazioni/documentazione non devono cambiare il comportamento numerico del substrato; i fix comportamentali (se un INCORRECT è nel codice, non nel commento) devono avere regression test.

**Why this priority**: il layer §4.2 comportamentale consuma questo substrato; una regressione silenziosa si propagherebbe a un modulo già CONVERGED.

**Acceptance Scenarios**:

1. **Given** la suite pytest completa, **When** eseguita dopo i fix, **Then** verde (baseline corrente), zero regressioni sui test del substrato e su `test_economy` del layer §4.2.
2. **Given** un fix comportamentale su una formula, **When** applicato, **Then** ha un regression test RED-first che fissa il nuovo contratto e cita la fonte corretta.

### User Story 3 - Promozione documentale coerente (Priority: P2)

Dopo CONVERGED, il substrato passa da §8.2 a §4.x con EN/IT speculari, e il §8 residuo si riduce al solo Knowledge Graph in modo coerente in tutto il whitepaper (lezione della sessione precedente: i conteggi §8 vanno riconciliati ovunque, non solo nella sezione promossa).

**Acceptance Scenarios**:

1. **Given** whitepaper EN e IT dopo la promozione, **Then** il substrato è §4.x Methods, §8.2 rimossa, ogni conteggio "moduli §8 pendenti" dice uno (solo Knowledge Graph), con grep di coerenza globale su entrambe le lingue.

### Edge Cases

- Se l'audit Round 1 trova un modulo già pulito (zero INCORRECT/UNJUSTIFIED), quel modulo è CONVERGED al Round 1 e non richiede fix, solo la promozione documentale.
- Se un fix su una formula del substrato cambia i valori consumati da §4.2, la regola whitepaper-doc-sync impone di verificare §4.2 nello stesso branch e, se il modello §4.2 cambia, di aggiornarne il capitolo.
- Determinismo: il tâtonnement e il seeding non devono introdurre nondeterminismo (nessun RNG non seedato); se un finding lo rileva, rientra nello scope.

## Requirements *(mandatory)*

Le FR di dettaglio sui fix saranno derivate dai findings del workflow di audit (sezione "Findings" sotto, da popolare). Le FR di processo, valide a prescindere dai findings:

- **FR-P1**: ogni finding INCORRECT e UNJUSTIFIED sopravvissuto alla verifica avversariale a due lenti DEVE essere risolto (fix di codice o di citazione/documentazione) prima del merge.
- **FR-P2**: ogni finding INCONSISTENT e MISSING DEVE essere risolto o documentato esplicitamente con rationale.
- **FR-P3**: un re-audit Round 2 DEVE confermare CONVERGED per tutti e cinque i moduli prima della promozione.
- **FR-P4**: i fix comportamentali DEVONO avere regression test RED-first; i fix di sola documentazione NON devono cambiare il comportamento (verificato dalla suite invariata).
- **FR-P5**: la promozione whitepaper §8.2 → §4.x DEVE essere EN/IT speculare, con riconciliazione globale del conteggio §8 residuo (solo Knowledge Graph), e frozen-pin al merge.
- **FR-P6**: `ruff check .` e `ruff format --check .` exit 0; suite pytest completa verde.

### Findings — Round 1 audit (workflow `audit-workflow.js`, 66 agenti, 2026-07-15)

Report completo: [round1-audit-report.md](./round1-audit-report.md). Verdetto: **NOT CONVERGED**. 10 findings confermati dopo verifica avversariale a due lenti (accuratezza-fonte + materialità, sopravvivenza congiuntiva), 20 rigettati dai verificatori, 6 VERIFIED.

**Difetti gravi (bloccano la promozione, cambiano flussi consumati da §4.2):**

1. **CM-1 / distribution PROD-2 (INCORRECT, high) — non-conservazione di moneta e valore**. `compute_rent` distribuisce l'INTERO valore prodotto della zona come rendita; `compute_wages` distribuisce indipendentemente lo STESSO valore di nuovo (proprietari il 100%, lavoratori `wage_share·value`); l'engine accredita entrambi come cassa NUOVA (`from_agent=None`, `engine.py:357-371` rendita e `387-402` salari) senza addebito a un'entità produttrice. Ogni tick inietta più moneta del valore prodotto. L'identità classica è rendita+salari+profitto = UN valore prodotto (partizione), non ciascuno = valore. NON documentabile: va riscritto partizionando un valore in quote che sommano a 1 e regolando come trasferimenti.
2. **MKT-2 / CM-3 (INCORRECT, high) — beni creati dal nulla al settlement**. `execute_trades` calcola `traded=min(supply,demand)` ma non lo usa mai: il doppio loop compratori×venditori non decrementa `actual_buy`/`actual_sell`, quindi il volume aggregato scala con N·M. L'engine floora le scorte del venditore a 0 ma accredita a ogni compratore la quantità piena → i venditori sono pagati per unità mai possedute. Fix: razionamento sul lato corto con running total, `sum(buy)=sum(sell)=min(supply,demand)`.
3. **PROD-1 (INCORRECT, high) — limite Leontief CES sbagliato**. Il ramo `σ→0` ritorna `A·min(αᵢ·Xᵢ)` invece di `A·min(Xᵢ)` verso cui il suo stesso aggregatore normalizzato converge (i pesi svaniscono nel limite del power mean). Errore 10x con discontinuità a σ=0.05. Fix: `A·min(Xᵢ)` (o `A·min(Xᵢ/aᵢ)` sotto normalizzazione Leontief esplicita e documentata).
4. **CM-2 (INCONSISTENT, high) — aggregato monetario M scollegato dalla cassa circolante**. `Currency.total_supply` fissato una volta all'init dal template e mai aggiornato, mentre la cassa agenti è indipendente e rendita/salari iniettano cassa illimitata. `check_fisher_consistency` (la diagnostica MV=PQ che catturerebbe la creazione di moneta di CM-1) è definita ma MAI chiamata. Un secondo aggregato (banking `total_deposits`) è ricalcolato in parallelo ogni tick, quindi i due divergono per costruzione.
5. **init PROD-1/PROD-2 / CM-4 (INCONSISTENT, high/medium) — scala di produzione sbagliata**. `default_good_production` hardcoda `scale=5.0` per ogni bene; `production.py` legge `good_prod.get('scale', default_scale)` e 'scale' è sempre presente → il fallback `default_scale` è codice morto. `initialize_economy` non scrive `default_scale` → `engine.py:138` fallback a 1.0. `template_loader.py` documenta esplicitamente che `scale=5.0` inonda un mercato a 4 agenti ed è unphysical, e calibra `default_scale=2.0`. Entrambi i percorsi che porterebbero il 2.0 sono morti → il seed spedisce esattamente il valore documentato come unphysical. Fix una riga: seedare 2.0.

**Difetti minori (fix di documentazione/parametro, no cambio di modello):**

6. **MKT-5 (UNJUSTIFIED, high)** — domanda discrezionale `min(5.0, cash·0.1/(price·elasticity))` usa l'elasticità (adimensionale) come divisore di quantità, frazione di spesa 0.1 non citata, nessun vincolo di budget cross-bene (domanda totale può raggiungere `0.1·K·cash > cash`). Fix: regola vincolata `Σ pᵢqᵢ ≤ cash` o documentare come euristica con il modello che approssima.
7. **MKT-6 (INCONSISTENT, low)** — il tetto `MAX_PRICE_RATIO` usa `initial_prices` nel ramo zero-supply e `base_prices` nel ramo principale. Un solo anchor.
8. **monetary PROD-3 (INCONSISTENT, medium)** — docstring dice "linear mood penalty" ma il codice ritorna un gradino costante -0.05. Allineare docstring o rendere lineare.
9. **monetary PROD-4 (MISSING, medium)** — `compute_inflation` è media aritmetica non pesata di price relatives (indice di Carli, bias verso l'alto documentato vs Jevons geometrico adottato dagli istituti statistici); simplification non documentata.
10. **production PROD-4 (UNJUSTIFIED, low)** — baseline 0.5 per capital/natural_resources/knowledge alimentano l'aggregatore CES senza fonte né tag tunable (a differenza dei default labor/scale correttamente taggati).

**Altri cross-module (INCONSISTENT):** CM-5 inflazione/price-level calcolati su dict last-zone-wins, non su aggregati di sistema; CM-6 soglie di umore (povertà 10, sazietà 100) non riconciliate con la scala di ricchezza inizializzata (property base_value 100, cash elite 300-500 → ogni proprietario parte oltre la sazietà, banda di povertà irraggiungibile).

**Cosa è risultato SOLIDO (VERIFIED / rigettati):** il loop di prezzi tâtonnement con i suoi cap di stabilità (ben documentati, tunable); i rami CES general e Cobb-Douglas (corretti e citati); la costante di sussistenza (1.0) condivisa coerentemente; trade e tasse muovono moneta in modo conservativo; velocità onestamente inquadrata come misurata non asserita. La verifica a due lenti ha rigettato 20 findings: tra questi il misread della rendita differenziale ricardiana (PROD-1 distribution, scartato a favore del più profondo CM-1), l'omissione del numéraire/legge di Walras (scartato — il tâtonnement è difendibile), la continuità dei branch-threshold CES.

### Punti-decisione per il gate di fase 2 (richiedono ratifica)

I difetti 1-4 sono cambi di modello economico, non fix meccanici, e toccano i flussi di moneta/beni che il layer §4.2 (già CONVERGED) consuma. Prima di implementare serve ratifica dell'APPROCCIO:

- **D1 (conservazione, CM-1)**: come partizionare il valore prodotto? Opzione A: introdurre un'entità produttrice (il proprietario/firm della zona) che viene addebitata del valore prodotto, poi distribuito in rendita+salari+(profitto residuo) che sommano a 1. Opzione B: modello a puro trasferimento senza entità firm, dove l'output è accreditato una volta al produttore e rendita/salari sono ridistribuzioni di quella singola posta. Raccomando A (più vicino alla partizione classica e coerente col futuro §4.x). Impatta `distribution.py` + `engine.py` money flow.
- **D2 (trade rationing, MKT-2)**: razionamento proporzionale sul lato corto con running total — approccio standard, poco ambiguo. Serve solo conferma che il razionamento proporzionale (vs priorità per prezzo/ordine) è la regola voluta.
- **D3 (aggregato M, CM-2)**: rendere `Currency.total_supply` un aggregato vivo (somma della cassa circolante + depositi) aggiornato per tick, e chiamare `check_fisher_consistency` come gate diagnostico. Conferma che M deve tracciare la cassa reale.
- **D4 (scala 2.0)**: fix una riga, nessuna ambiguità — propago `default_scale=2.0`.

Il resto (5-10, CM-5/6) sono fix di documentazione/parametro/coerenza applicabili senza decisione di modello.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: report di audit Round 2 con verdetto CONVERGED per tutti e cinque i moduli del substrato; zero INCORRECT/UNJUSTIFIED residui.
- **SC-002**: suite pytest completa verde (baseline corrente + eventuali regression test nuovi); zero regressioni su `test_economy` §4.2 e sui test del substrato.
- **SC-003**: `ruff check .` e `ruff format --check .` exit 0.
- **SC-004**: whitepaper EN/IT: substrato promosso a §4.x, §8.2 rimossa, conteggio §8 residuo = uno (solo Knowledge Graph) coerente in tutto il documento (grep globale).
- **SC-005**: ogni formula del futuro §4.x ha citazione a fonte primaria verificata; ogni parametro citato o taggato tunable.

## Assumptions

- Primo audit (Round 1), non re-pass: il substrato non era nel batch 2026-04-12. La procedura di convergenza è identica; cambia solo che non esiste un Round 1 precedente da verificare.
- Il substrato è live nella pipeline per-tick (a differenza della demografia): `process_economy_tick_new` è dispatched da `simulation/engine.py` quando la simulazione ha il data layer economico inizializzato. Quindi i fix comportamentali sono verificabili end-to-end, non solo in isolamento.
- La promozione riduce il §8 residuo al solo §8.1 Knowledge Graph: la memoria tracker va aggiornata di conseguenza a chiusura.
- L'audit del Knowledge Graph (§8.1) resta un work item separato successivo (9+ moduli, più grande).

## FAQ

**Perché il substrato è al primo audit se il layer sopra è già §4.2 CONVERGED?**
Perché sono stati auditati in tempi e scope diversi. Il layer comportamentale (expectations, credit, banking, property market) ha avuto il suo audit dedicato (economy-behavioral-integration, CONVERGED 2026-04-15 → §4.2). Il substrato che gli sta sotto (production, monetary, market, distribution, initialization) è stato costruito ma mai sottoposto ad audit avversariale: §3.6 lo descrive e §8.2 lo cataloga come pendente, e §3.6 disclaima esplicitamente lo stato Methods-grade.

**Perché un workflow multi-agente invece di un singolo critical-analyzer?**
Perché il substrato ha cinque moduli con formule indipendenti e fonti distinte, e la verifica avversariale a due lenti (accuratezza-fonte + materialità) per ogni finding riduce sia i falsi negativi (un solo auditor può perdere un errore) sia i falsi positivi (un finding pedante o basato su una lettura errata della fonte viene rigettato prima di diventare un fix). La sintesi cross-modulo cattura le incoerenze di unità e definizioni che nessun auditor mono-modulo vede.

**Cosa succede se l'audit trova pochi o nessun difetto?**
Tanto meglio: significa che il substrato è già scientificamente solido e serve solo la promozione documentale a §4.x. Il primo audit è comunque obbligatorio dal GOLDEN RULE prima della promozione — la sua assenza, non la sua conclusione, è il debito.

**La promozione tocca §4.2, che è già CONVERGED?**
Solo se un fix del substrato cambia i valori che §4.2 consuma. In quel caso la regola whitepaper-doc-sync impone di verificare e, se serve, aggiornare §4.2 nello stesso branch. Se i fix sono di sola citazione/documentazione, §4.2 non è toccato.

**Perché non auditare Knowledge Graph e substrato insieme?**
Perché il Knowledge Graph è molto più grande (9+ moduli: chunking, extraction, embedding, merge, normalizer, materialization, ontology, prompts, api) e con fonti diverse (RAG/Lewis 2020, embeddings/Reimers-Gurevych 2019). Auditarli separatamente tiene ogni branch delimitato e ogni gate pesante leggibile.

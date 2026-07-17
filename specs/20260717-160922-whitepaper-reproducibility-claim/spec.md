# Feature Specification: Correzione delle affermazioni di riproducibilità nei whitepaper

**Feature Branch**: `20260717-160922-whitepaper-reproducibility-claim`

**Created**: 2026-07-17

**Status**: Draft

**Input**: I due whitepaper (`docs/whitepaper/epocha-whitepaper.md` EN e `.it.md` IT) affermano in più punti che una run è riproducibile bit-identica dal seme. È falso per costruzione: il seme copre la sola parte non-LLM, come dichiara il codice stesso. Il paper va corretto per dire la verità, non per promettere una capacità che il sistema non ha.

## Contesto e problema

Il campo del modello lo dichiara senza ambiguità: `simulation.seed = BigIntegerField(help_text="Seed for reproducibility (non-LLM part)")` (`epocha/apps/simulation/models.py:35`). Il seme governa gli stream RNG delle parti deterministiche — demografia ed economia, che adottano `get_seeded_rng` derivato da `seed`+`tick`. Non governa nulla di ciò che passa dall'LLM, e non governa gli usi residui del RNG globale di Python.

Tre fatti di codice, verificati alla sorgente il 2026-07-17, decidono ogni verdetto:

1. **Ogni decisione d'agente, a ogni tick, è una chiamata LLM non seminata a `temperature=0.7`**: `epocha/apps/agents/decision.py:381-386` (`client.complete(prompt=..., temperature=0.7, max_tokens=150)`).
2. **Il mondo e la popolazione iniziale nascono da una chiamata LLM non seminata a `temperature=0.8`**: `epocha/apps/world/generator.py:101-107`.
3. **Il layer LLM non espone alcun seme**: `grep -rn seed epocha/apps/llm_adapter/` è vuoto. Il progetto lo dichiara nel proprio modello (`simulation/models.py:35`, sopra).

In più, il RNG globale di Python è usato non seminato nel percorso vivo in almeno due punti: l'esito del colpo di stato (`random.random()` in `epocha/apps/world/government.py:618`) e lo scatter di arrivo delle posizioni (`random.uniform(...)` in `epocha/apps/agents/movement.py:245-246`). Il secondo è già dichiarato come semplificazione N-8 in §4.6; il primo non è dichiarato da nessuna parte.

La conseguenza è un paper internamente contraddittorio. §3.1 ammette che «any non-determinism comes from the LLM call»; cinque affermazioni altrove promettono riproducibilità piena dal seme. §4.6 N-8 dichiara che «two runs with identical seed produce different arrival-scatter offsets», che è la negazione operativa di «identically-seeded runs reproduce bit-identical state» di §4.8. Un revisore che legge il paper trova entrambe le tesi e non sa quale credere. Per un progetto la cui prima regola è il metodo scientifico, è un difetto di integrità del paper, non un abbellimento.

## Base di evidenza

L'enumerazione avversariale completa è in `research/enumeration-reproducibility-claims.md`, prodotta dal `critical-analyzer` in modalità ostile il 2026-07-17, con ogni affermazione verificata contro il codice e ogni claim EN riscontrata una-a-una contro la controparte IT (non per offset di riga). Inventario: 19 affermazioni totali, di cui **5 FALSE certe**, **1 borderline FALSE**, **7 SCOPED-BUT-AMBIGUOUS** da qualificare, **3 anchor corretti** da usare come modello e non toccare. La parità EN-IT è uno-a-uno su tutti i punti.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Un revisore non trova più affermazioni false di riproducibilità (Priority: P1)

Un revisore scientifico legge i due whitepaper cercando affermazioni di riproducibilità. Dopo la correzione, ogni volta che il paper dice «riproducibile dal seme» il testo delimita che ciò vale per la parte non-LLM (demografia ed economia seminate), mentre le decisioni per-agente, la generazione del mondo e gli usi del RNG globale in movement/government non lo sono. Nessuna affermazione promette la riproducibilità bit-identica dell'intera run o del decision log.

**Why this priority**: è integrità del paper. Una singola affermazione falsa vista da un revisore mina la credibilità di tutto il resto, incluse le parti auditate e corrette.

**Independent Test**: `grep` sui due file delle cinque frasi FALSE non restituisce più la forma non qualificata; ogni locus corretto nomina esplicitamente la parte LLM come non riproducibile.

**Acceptance Scenarios**:

1. **Given** il whitepaper EN, **When** cerco «every tick of a run is deterministic and reproducible across machines» (§3.4), **Then** la frase è stata sostituita da una che limita il determinismo alla parte non-LLM e nomina la decisione LLM a temperatura come fonte di non-riproducibilità.
2. **Given** il whitepaper EN §10, **When** leggo l'affermazione sul «same per-agent decision log» riprodotto dallo stesso seme, **Then** non esiste più: il decision log è la trascrizione dell'output LLM a 0.7 senza seme, ed è l'artefatto meno riproducibile di tutti.
3. **Given** entrambe le lingue, **When** confronto ogni locus corretto con la sua controparte, **Then** dicono la stessa cosa (parità EN-IT preservata).

### User Story 2 - Le affermazioni ambigue diventano inequivocabili (Priority: P2)

Le sette affermazioni SCOPED-BUT-AMBIGUOUS (Abstract, §1.2, §1.3, §3.1 contract, §7.3 Tab.7.2, §12 partitioning, App. B intro) parlano di «reproducibility infrastructure» o «reproducible» senza delimitare a cosa si applica. Non sono false, ma un lettore le può leggere come promessa di riproducibilità totale. Dopo la correzione ognuna porta la qualificazione «della parte non-LLM» o equivalente.

**Why this priority**: chiudono la porta a interpretazioni errate. P2 perché non affermano il falso; lo lasciano solo intendere.

**Independent Test**: ciascuno dei sette loci, in entrambe le lingue, contiene la delimitazione esplicita del perimetro (parte non-LLM / stream RNG seminati / comandi che rigenerano le sole parti seminate).

**Acceptance Scenarios**:

1. **Given** l'Abstract EN, **When** leggo «reproducibility infrastructure rests on ... per-phase seeded RNG streams», **Then** il testo chiarisce che l'infrastruttura copre la parte non-LLM e non le decisioni d'agente.

### User Story 3 - Il difetto RNG del colpo di stato è dichiarato (Priority: P3)

Il RNG globale non seminato di `government.py:618` (esito del coup) è lo stesso difetto di §4.6 N-8 ma non è dichiarato in nessun punto del paper. Dopo la correzione compare come nota di semplificazione gemella in §4.5 (istituzioni politiche), con causa, meccanismo, conseguenza osservabile e lavoro futuro, sullo stesso modello di N-8.

**Why this priority**: completa l'onestà del paper. P3 perché è un'aggiunta, non la correzione di un falso.

**Independent Test**: §4.5, in entrambe le lingue, contiene una nota che dichiara l'uso del RNG globale per l'esito del coup e la sua non-riproducibilità dal seme.

**Acceptance Scenarios**:

1. **Given** §4.5 EN, **When** cerco la dichiarazione sul RNG del coup, **Then** esiste e cita `government.py` con la stessa struttura della nota N-8.

### Edge Cases

- **I tre anchor corretti non vanno toccati.** §3.1 (EN:404-407), §4.6 N-8 (EN:1795), App. B RNG (EN:3098-3106) sono già corretti e sono il modello di riscrittura. Modificarli sarebbe una regressione.
- **Le righe si spostano man mano che si edita.** Ogni edit sopra un locus successivo ne sposta il numero di riga. Gli edit vanno applicati per contenuto (stringa esatta), non per numero di riga, oppure dal fondo del file verso l'alto.
- **La semantica di «draws» in App. B RNG è corretta e va preservata.** App. B afferma solo «identical per-tick draws» (estrazioni RNG), non stato né decisioni: è vera e ancora.
- **Il claim borderline S2.2 «enforced» (EN:267)** va portato alla stessa qualificazione degli altri: «enforced ... through seeded PRNG» va delimitato alla parte non-LLM, o l'affermazione contraddice §2.2:259 che otto righe sopra ammette che «sampling stochasticity is rarely fully controllable».

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Le cinque affermazioni FALSE (§3.4 EN:501, §4.8 EN:1940, §10 EN:2278, §10 EN:2282-2284, §12 EN:2434-2435) DEVONO essere riscritte in modo che, ogni volta che è affermata la riproducibilità dal seme, il testo delimiti che vale per la parte non-LLM e nomini le decisioni d'agente (LLM a temperatura), la generazione del mondo e gli usi del RNG globale come NON riproducibili dal seme. Le controparti IT (§3.4 IT:534-536, §4.8 IT:2007, §10 IT:2248 ×2, §12 IT:2305) DEVONO essere corrette in modo speculare.
- **FR-002**: L'affermazione più grave (§10 EN:2282-2284: «the same scenario re-run with the same seed produces the same per-agent decision log») DEVE essere eliminata o riscritta per dire l'opposto: il decision log è la trascrizione dell'output LLM non seminato e NON è riproducibile dal seme. Vale per entrambe le lingue.
- **FR-003**: Le sette affermazioni SCOPED-BUT-AMBIGUOUS (Abstract EN:43-45, §1.2 EN:143, §1.3 EN:160-162, §3.1 contract EN:411, §7.3 Tab.7.2 EN:2119, §12 partitioning EN:2455-2458, App. B intro EN:3033-3037) DEVONO ricevere la delimitazione esplicita del perimetro (parte non-LLM), in entrambe le lingue.
- **FR-004**: Il claim borderline §2.2 «enforced» (EN:267-270, IT:287-290) DEVE essere qualificato in modo da non contraddire §2.2 poche righe sopra.
- **FR-005**: Una nota di semplificazione DEVE essere aggiunta a §4.5 (in entrambe le lingue) che dichiara l'uso del RNG globale non seminato per l'esito del coup in `government.py:618`, con la struttura di §4.6 N-8 (causa, meccanismo, conseguenza osservabile, lavoro futuro).
- **FR-006**: I tre anchor corretti (§3.1 EN:404-407, §4.6 N-8 EN:1795, App. B RNG EN:3098-3106) NON DEVONO essere modificati.
- **FR-007**: La parità EN-IT DEVE essere preservata: ogni locus corretto in una lingua ha la controparte corretta nell'altra con lo stesso significato.
- **FR-008**: Le correzioni NON DEVONO introdurre nuove affermazioni non verificabili contro il codice. Ogni delimitazione DEVE corrispondere a ciò che il codice fa (seme per demografia+economia; niente seme per LLM e per il RNG globale di movement/government).

### Key Entities

- **Affermazione di riproducibilità**: un locus di testo nel whitepaper che afferma o implica riproducibilità/determinismo. Attributi: sezione, righe EN, righe IT, verdetto (FALSE / SCOPED-BUT-AMBIGUOUS / anchor), load-bearing.
- **Perimetro del seme**: la parte non-LLM del sistema (demografia ed economia seminate). È ciò che `models.py:35` chiama «non-LLM part» e l'unica cosa che il seme rende riproducibile.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Zero affermazioni non qualificate di riproducibilità bit-identica dell'intera run o del decision log in entrambi i file. Verificabile per `grep` delle cinque frasi FALSE.
- **SC-002**: Tutti e 12 i loci per lingua (5 FALSE + 7 ambigue) più il borderline S2.2 sono corretti, per un totale di 24-26 modifiche, con parità EN-IT verificata locus per locus.
- **SC-003**: §4.5 dichiara il difetto RNG del coup in entrambe le lingue.
- **SC-004**: I tre anchor sono invariati (`git diff` non li tocca).
- **SC-005**: Nessuna delle correzioni contraddice il codice verificato: seme = parte non-LLM.

## Assumptions

- La posizione del progetto sulla riproducibilità è quella dichiarata dal codice e ratificata dall'utente: il seme copre la parte non-LLM; le decisioni d'agente, la generazione del mondo e il RNG globale in movement/government non sono riproducibili dal seme. Il paper va allineato a questa verità, non viceversa.
- L'enumerazione in `research/enumeration-reproducibility-claims.md` è la base autorevole dei loci; i suoi numeri di riga sono stati riscontrati contro il file corrente del worktree.
- Questo è un lavoro di sola documentazione: nessun cambiamento di codice, nessun modello scientifico modificato. Non richiede aggiornamento di codice né migrazione.
- I frozen-pin degli anchor non-economia (§4.1, §4.6, §5.4) restano pinnati ai loro commit e non vanno rinfrescati da questo branch.

## FAQ

**Perché correggere invece di implementare la riproducibilità piena?** Perché la riproducibilità piena dal seme è incompatibile con un'architettura LLM-driven a temperatura > 0: la stocasticità di campionamento dell'LLM non è governabile da un seme lato applicazione, e il layer LLM non ne espone uno. Rendere il mondo e le decisioni riproducibili richiederebbe `temperature=0` più un provider che garantisca determinismo bit-identico, che non è l'obiettivo del progetto (la varietà delle decisioni d'agente è una feature, non un bug). Correggere il paper è l'unica mossa onesta.

**Perché lasciare in piedi le affermazioni sulla parte seminata?** Perché sono vere: demografia ed economia usano `get_seeded_rng` e sono deterministiche dato seme+tick. La correzione non nega la riproducibilità, la delimita al suo perimetro reale.

**Perché §10 EN:2282-2284 è «la più grave»?** Perché afferma la riproducibilità dal seme proprio dell'artefatto che è puro campionamento LLM: il decision log per-agente. È l'affermazione più direttamente contraddetta dal codice (`decision.py:381` non passa alcun seme e usa `temperature=0.7`), e la più visibile perché presentata come capacità di ricerca («narrative reproducibility»).

**Perché aggiungere il difetto del coup RNG ora?** Perché la verifica dell'enumerazione l'ha trovato: è lo stesso difetto di N-8 (RNG globale non seminato) ma non dichiarato. Lasciarlo fuori mentre si dichiara N-8 sarebbe incoerente — o si dichiarano entrambi, o il paper è selettivamente onesto. La regola No-Bug-Left-Behind impone di dichiararlo nella stessa sessione in cui è emerso.

**Come si preserva la parità EN-IT?** Ogni locus è stato mappato uno-a-uno EN↔IT nell'enumerazione. Le correzioni si applicano a coppie e si verifica, locus per locus, che le due lingue dicano la stessa cosa. La verifica non è per offset di riga (le due lingue divergono nei numeri) ma per contenuto.

**Questo tocca un capitolo §4 auditato?** Sì: §4.8 (economia base) e §4.6 (movimento) sono capitoli auditati. Ma la correzione non tocca il modello scientifico né il codice: rende onesta un'affermazione di riproducibilità che li sovrastimava. La doc-sync bilingue è rispettata perché entrambe le lingue si correggono insieme. Il frozen-pin di §4.8 non cambia perché non cambia il codice del capitolo.

**Cosa NON copre questo spec?** Non corregge i due difetti RNG globali nel codice (movement e government): sono deferiti al work item di determinismo trasversale già aperto sulla build map. Qui si dichiarano nel paper, non si risolvono nel codice.

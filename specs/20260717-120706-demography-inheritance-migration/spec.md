# Feature Specification: Demografia Plan 3 — Ereditarietà e Migrazione

**Feature Branch**: `20260717-120706-demography-inheritance-migration`

**Created**: 2026-07-17

**Status**: Draft (in attesa del gate leggero sul piano)

**Input**: implementare i due moduli comportamentali residui del sottosistema Demografia — `inheritance.py` e `migration.py` — esattamente come specificati nelle sezioni 4, 5 e 6 della spec di design già CONVERGED. È il Plan 3 della decomposizione in quattro piani, e il prerequisito che sblocca il Plan 4 (inizializzazione, orchestrazione nel tick, validazione storica).

## Contesto e problema

Il sottosistema Demografia vive in `epocha/apps/demography/` ed è decomposto in quattro piani sequenziali. I primi due sono mergiati in `develop`: il Plan 1 (fondamenta, modelli, mortalità Heligman-Pollard, template loader, RNG) e il Plan 2 (fertilità Hadwiger, formazione di coppia Gale-Shapley, azioni LLM). Il loro audit è CONVERGED e sono documentati nel whitepaper §4.1.

Il problema è che quella scienza non gira. Il tick loop in `epocha/apps/simulation/engine.py` non chiama mai mortalità, fertilità o coppia: l'unico aggancio è `set_avoid_conception_flag`, un helper di flag per un'azione LLM. I modelli sono auditati e testati in isolamento, ma nella simulazione dal vivo la demografia non esiste. Chiudere questo divario è il Plan 4, che costruisce l'orchestratore `process_demography_tick` e lo aggancia al tick.

Il Plan 4 però non è avviabile. Due dei sei passi canonici del suo orchestratore chiamano moduli che nascono nel Plan 3: il passo 3 (assegnazione del caretaker agli orfani) vive in `inheritance.py`, il passo 5 (emergency flight) vive in `migration.py`. Nessuno dei due file esiste. Il Plan 3 è quindi il collo di bottiglia dell'intera frontiera demografica, ed è questo work item.

La scienza di questi due moduli non è da progettare: è già stata progettata e sottoposta ad audit avversariale. La spec `docs/superpowers/specs/2026-04-18-demography-design-it.md` (italiana, autoritativa, CONVERGED dopo 4 round) copre l'ereditarietà dei tratti nella sezione 4, l'ereditarietà sociale ed economica nella sezione 5, e la migrazione nella sezione 6, inclusi i fix ratificati durante l'audit (I-1, I-5, C-3, MISS-1, MISS-3, MISS-4, MISS-5). Il gate pesante di fase 2 è già pagato. **Questo work item non riapre il design: lo esegue.**

### Substrato verificato contro il source tree (2026-07-17)

Il Plan 3 non richiede né migrazioni di schema né modifiche ai template. Tutto ciò che consuma esiste già:

| Dipendenza | Stato | Dove |
|---|---|---|
| `add_to_treasury(government, currency_code, amount)` | esiste | `epocha/apps/world/government.py:840` |
| `compute_subsistence_threshold(simulation, zone)` | esiste | `epocha/apps/demography/context.py:15` |
| `compute_aggregate_outlook(agent)` | esiste | `epocha/apps/demography/context.py:35` |
| `TRAVEL_SPEEDS` | esiste | `epocha/apps/agents/movement.py:62` |
| `propagate_information(simulation, tick)` | esiste | `epocha/apps/agents/information_flow.py:40` |
| `SUBSISTENCE_NEED_PER_AGENT` | esiste | `epocha/apps/economy/market.py:50` |
| Campi `Agent`: `birth_tick`, `death_tick`, `death_cause`, `other_parent_agent`, `caretaker_agent` | esistono (Plan 1) | `epocha/apps/agents/models.py` |
| Campi `Couple`: `agent_a_name_snapshot`, `agent_b_name_snapshot`, `dissolved_at_tick`, `dissolution_reason` | esistono (Plan 2, fix MISS-4 già consegnato) | `epocha/apps/demography/models.py:52-56` |
| Event type `MIGRATION`, `INHERITANCE_TRANSFER`, `MASS_FLIGHT`, `TRAPPED_CRISIS` | esistono (Plan 1) | `epocha/apps/demography/models.py:116-119` |
| Chiavi template `trait_inheritance`, `social_inheritance`, `economic_inheritance`, `migration` | esistono in tutti e 5 i template d'era | `epocha/apps/demography/templates/*.json` |

Il Plan 3 è quindi **logica pura più test**: due nuovi moduli che leggono uno schema di template completo e un data layer completo.

## Ambito

**In scope**: `epocha/apps/demography/inheritance.py`, `epocha/apps/demography/migration.py`, i loro test unitari, l'estensione del capitolo §4.1 di entrambi i whitepaper e della tabella di doc-sync.

**Fuori scope**: il Plan 4 per intero — `initialization.py`, l'orchestratore `engine.py`, l'hook in `simulation/engine.py`, la validazione storica contro Wrigley-Schofield e HMD, e il benchmark di performance. Fuori scope anche l'adozione (deferita dal design) e il salario del settore informale nella variante Harris-Todaro (deferito e documentato come tunable).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Un neonato eredita dai genitori (Priority: P1)

Alla nascita, un agente riceve tratti biologici, classe sociale e livello di istruzione derivati dai genitori secondo le regole dell'era in cui vive, invece di essere generato da zero. Un figlio di genitori intelligenti e istruiti in un'era pre-industriale rigida resta nella classe del padre; lo stesso figlio in uno scenario sci-fi meritocratico può risalire.

**Why this priority**: è il ramo di nascita di `inheritance.py` e metà della ragione d'essere del modulo. Senza, la genealogia esiste come FK ma non trasmette nulla, e la simulazione non produce dinastie.

**Independent Test**: creare due genitori con tratti noti, far nascere un figlio con RNG seedato, verificare che ogni tratto rispetti `child_T = h²·midparent + (1-h²)·ε` e che classe ed istruzione seguano la regola dell'era caricata.

**Acceptance Scenarios**:

1. **Given** due genitori con `intelligence` 0.8 e 0.6 e h² = 0.55, **When** nasce un figlio, **Then** il valore atteso del tratto è `0.55·0.7 + 0.45·ε` con `ε ~ N(era_mean, era_sd)`, e il risultato è clampato nel range del tratto.
2. **Given** un template `pre_industrial_christian`, **When** nasce un figlio, **Then** la sua `social_class` è identica a quella del padre (patrilineale rigido).
3. **Given** un template `modern_democracy`, **When** nasce un figlio, **Then** la sua classe è campionata con elasticità intergenerazionale 0.4, non copiata.
4. **Given** una coppia dove è risolto un solo genitore, **When** nasce un figlio, **Then** si applica il fallback `child_T = h²·parent_T + (1-h²)·ε` (fix I-1) senza errori.
5. **Given** il template definisce `derived_trait_formulas` per `cunning`, **When** nasce un figlio, **Then** `cunning` è calcolato dalla formula sui tratti appena ereditati, non ereditato biologicamente.

---

### User Story 2 - Alla morte il patrimonio passa agli eredi (Priority: P1)

Quando un agente muore, il suo patrimonio — contante, proprietà e prestiti in cui era creditore — passa agli eredi secondo la regola successoria dell'era, al netto dell'imposta di successione che finisce nel tesoro del governo. Nulla si crea e nulla si distrugge.

**Why this priority**: è il ramo di morte di `inheritance.py`, ed è l'unico punto del Plan 3 che muove moneta. Una perdita di conservazione qui contaminerebbe il layer economico §4.2 e §4.8, entrambi già CONVERGED, dove la conservazione è un invariante duramente conquistato in dodici round di audit.

**Independent Test**: uccidere un agente con patrimonio noto in una simulazione seedata e verificare che la somma del contante degli eredi più l'imposta versata al tesoro sia esattamente uguale al patrimonio iniziale.

**Acceptance Scenarios**:

1. **Given** un defunto con coniuge e tre figli e regola `primogeniture`, **When** l'eredità viene liquidata, **Then** il figlio maschio maggiore sopravvissuto riceve il 100% al netto dell'imposta.
2. **Given** regola `equal_split`, **When** l'eredità viene liquidata, **Then** contante e proprietà sono divisi equamente tra figli sopravvissuti e coniuge, che riceve quota pari a quella di un figlio.
3. **Given** regola `shari'a` con coniuge e figli, **When** l'eredità viene liquidata, **Then** il coniuge riceve 1/8 e ogni figlio maschio il doppio della quota di una figlia.
4. **Given** un defunto senza alcun erede, **When** l'eredità viene liquidata, **Then** contante e proprietà vanno al tesoro del governo tramite `add_to_treasury`.
5. **Given** un'era con `estate_tax_rate` 0.40, **When** l'eredità viene liquidata, **Then** il tesoro cresce esattamente del 40% del patrimonio e gli eredi ricevono il 60%.
6. **Given** più agenti che muoiono nello stesso tick, **When** le eredità vengono liquidate, **Then** sono processate in batch ordinato per età decrescente (fix C-3) e l'imposta è applicata una sola volta per trasferimento.
7. **Given** un defunto creditore di prestiti attivi senza eredi umani, **When** l'eredità viene liquidata, **Then** i prestiti passano al sistema bancario (`lender=None`, `lender_type="banking"`) e continuano a essere serviti.

---

### User Story 3 - Gli orfani vengono presi in carico e la morte lascia un segno (Priority: P2)

Un minore che perde entrambi i genitori viene affidato al parente vivente più vicino, o allo stato se non ne ha. Chi era legato al defunto ne conserva memoria, e quel lutto si propaga nella società come qualsiasi altra informazione.

**Why this priority**: è il passo 3 dell'orchestratore del Plan 4, quindi è bloccante, ma è comportamentale e non muove moneta come la US2.

**Independent Test**: uccidere entrambi i genitori di un minore e verificare l'assegnazione del caretaker secondo la priorità; verificare che coniuge, figli e relazioni forti ricevano memorie con peso 0.9.

**Acceptance Scenarios**:

1. **Given** un minore con entrambi i genitori morti e un fratello vivente nella stessa zona, **When** l'eredità viene liquidata, **Then** il fratello diventa `caretaker_agent` (fix MISS-1).
2. **Given** un minore orfano senza alcun parente vivente, **When** l'eredità viene liquidata, **Then** `caretaker_agent` resta `None`, l'orfano è flaggato e il tesoro ne copre la sussistenza.
3. **Given** un orfano con caretaker, **When** riceve l'eredità, **Then** gli asset sono intestati all'orfano; il caretaker amministra ma non possiede.
4. **Given** un defunto con coniuge, figli e relazioni con `strength > 0.6`, **When** muore, **Then** ciascuno riceve una memoria con `emotional_weight = 0.9` che si propaga tramite `propagate_information`.
5. **Given** entrambi i partner di una coppia morti nello stesso tick, **When** l'eredità viene liquidata, **Then** la coppia è marcata `dissolution_reason = "death"`, i FK sono azzerati e gli snapshot dei nomi preservano il linkage di audit (fix MISS-4).

---

### User Story 4 - Un agente decide dove migrare con informazioni economiche (Priority: P2)

Quando un agente valuta un trasferimento, il prompt gli presenta il quadro economico delle zone raggiungibili — differenziale salariale, disoccupazione, costo in tick, stabilità — e il guadagno atteso. Se si sposta, la sua famiglia lo segue.

**Why this priority**: è il ramo volontario di `migration.py`. Dà sostanza economica a un'azione `move_to` che oggi è cieca, ma non è un passo dell'orchestratore, quindi non blocca il Plan 4 come la US5.

**Independent Test**: costruire due zone con salari e disoccupazione noti, verificare che il blocco `migration_outlook` riporti i numeri attesi e che il guadagno Harris-Todaro segua la variante operativa dichiarata.

**Acceptance Scenarios**:

1. **Given** due zone con salari medi noti sugli ultimi 5 tick, **When** un agente riceve il contesto, **Then** il blocco `migration_outlook` riporta differenziale, disoccupazione, costo distanza e stabilità per ciascuna.
2. **Given** una zona destinazione con disoccupazione 8% e salario 12, **When** si calcola il guadagno atteso, **Then** vale `(1 - unemployment)·wage_j - wage_current - distance_cost_j`.
3. **Given** un agente in coppia con due figli minorenni, **When** decide `move_to`, **Then** partner e minori migrano nello stesso tick, viene emesso un singolo `DemographyEvent` con gli `household_members`, e i minori non sono chiamati al decision loop (Mincer 1978).
4. **Given** un figlio adulto nello stesso household, **When** il genitore migra, **Then** il figlio adulto decide indipendentemente e non viene trascinato.

---

### User Story 5 - Chi muore di fame fugge, chi non può fuggire genera una crisi (Priority: P3)

Un agente sotto la soglia di sussistenza da troppo tempo abbandona la zona d'istinto, senza passare dall'LLM. Se nessuna zona offre di meglio, resta intrappolato e la sua crisi diventa visibile a chi gli sta intorno.

**Why this priority**: è il passo 5 dell'orchestratore del Plan 4, quindi bloccante, ma dipende dal contesto costruito nella US4 ed è il più raro dei percorsi.

**Independent Test**: portare un agente sotto sussistenza per più di `flight_trigger_ticks` con una zona migliore disponibile e verificare la fuga automatica; ripetere senza zone migliori e verificare `trapped_crisis` e la sua propagazione.

**Acceptance Scenarios**:

1. **Given** un agente sotto sussistenza da 30 tick consecutivi con almeno una zona a guadagno atteso positivo, **When** si valuta la fuga, **Then** migra automaticamente alla zona col guadagno più alto bypassando l'LLM, con memoria di peso 0.85.
2. **Given** un agente sotto sussistenza da 30 tick ma nessuna zona a guadagno positivo, **When** si valuta la fuga, **Then** NON migra (fix I-5), resta intrappolato ed è emesso `trapped_crisis`.
3. **Given** un `trapped_crisis` emesso, **When** si propaga, **Then** tutti gli agenti co-zone ricevono una memoria con `emotional_weight = 0.95` e `source_type = "public"` (fix MISS-3).
4. **Given** oltre il 30% della popolazione vivente di una zona in fuga entro `flight_trigger_ticks`, **When** si valuta il broadcast, **Then** è emesso `mass_flight` con l'elenco degli agenti.
5. **Given** una fuga d'emergenza di un agente in coppia con minori, **When** avviene, **Then** il coordinamento familiare si applica come nella US4.

---

### Edge Cases

- Neonato con un solo genitore risolto: fallback a metà del segnale genetico (fix I-1).
- Tratti in `Agent.personality` JSONB privi di h² pubblicato: h² di default 0.30, marcato come parametro di design tunable.
- Catena multi-generazionale: un nonno non può lasciare in eredità a un padre già morto da tick precedenti; l'estate segue la catena degli eredi di ciascun defunto al proprio tick di morte, e l'imposta non viene ri-applicata sui trasferimenti successivi (fix MISS-5).
- Zona con popolazione zero: guardia esplicita, nessuna divisione per zero nel calcolo di disoccupazione e salario medio.
- Prestiti agent-to-agent senza eredi: cancellati silenziosamente a MVP, limitazione documentata.
- Eredi non-binary: trattati secondo le regole documentate per ciascuna regola successoria (con le femmine in `primogeniture`, quota figlia in `shari'a`, quota equa in `equal_split`).
- Agente che muore nello stesso tick in cui era destinato a migrare: l'ordine dei passi lo risolve nel Plan 4; il Plan 3 espone funzioni pure che non assumono un ordine.

## Requirements *(mandatory)*

### Functional Requirements

**Ereditarietà biologica (`inheritance.py`, spec di design §4)**

- **FR-001**: il modulo MUST implementare l'ereditarietà polygenic additive `child_T = h²_T · (mother_T + father_T)/2 + (1 - h²_T) · ε_T` con `ε_T ~ N(era_mean_T, era_sd_T)`, secondo Falconer & Mackay (1996), applicando i valori di h² della tabella per-tratto della spec di design con le loro fonti primarie citate nel docstring.
- **FR-002**: il modulo MUST clampare ogni tratto risultante nel range del tratto.
- **FR-003**: il modulo MUST applicare il fallback single-parent `child_T = h²·parent_T + (1-h²)·ε` quando un solo genitore è risolto (fix I-1).
- **FR-004**: il modulo MUST valutare `trait_inheritance.derived_trait_formulas` dopo aver applicato l'ereditarietà a tutti i tratti ereditabili, tramite un evaluator ristretto ad aritmetica e riferimenti ai tratti. L'evaluator MUST NOT permettere esecuzione di codice arbitrario; l'insieme di simboli referenziabili MUST essere limitato alle chiavi del dict `heritability`.
- **FR-005**: il modulo MUST ereditare i tratti privi di h² pubblicato con h² di default 0.30, documentato come parametro di design tunable.
- **FR-006**: il modulo MUST risolvere il genere alla nascita da `sex_ratio_at_birth` e l'orientamento dalla distribuzione d'era.

**Ereditarietà sociale (`inheritance.py`, spec di design §5)**

- **FR-007**: il modulo MUST applicare la regola di classe sociale dell'era fra le quattro previste (patrilineale rigido; 70/30 con regressione verso la media di zona per Clark 2014; elasticità 0.4 per Solon 1999 e Chetty et al. 2014; 20/80 meritocratico per sci-fi).
- **FR-008**: il modulo MUST applicare la regressione intergenerazionale dell'istruzione `child.education = ρ·(mother.edu + father.edu)/2 + (1-ρ)·era_mean_edu` con `ρ` letto da `social_inheritance.education_regression_rho`.
- **FR-009**: il modulo MUST assegnare al neonato `wealth = 0` e `zone = mother.zone`.

**Successione economica (`inheritance.py`, spec di design §5)**

- **FR-010**: il modulo MUST risolvere gli eredi secondo la priorità configurata in `economic_inheritance.heir_priority`, con default coniuge, figli, fratelli, famiglia estesa fino a due generazioni, tesoro.
- **FR-011**: il modulo MUST implementare le cinque regole di distribuzione `primogeniture`, `equal_split`, `shari'a`, `matrilineal`, `nationalized` con le fonti citate nella spec di design.
- **FR-012**: il modulo MUST instradare l'imposta di successione al tesoro tramite l'helper esistente `add_to_treasury`, applicandola una sola volta per trasferimento effettivo.
- **FR-013**: il modulo MUST processare le morti simultanee in batch ordinato per età decrescente come tiebreak deterministico (fix C-3).
- **FR-014**: il modulo MUST NOT ri-applicare l'imposta quando gli asset si muovono attraverso ulteriori eventi di successione in tick successivi (fix MISS-5).
- **FR-015**: il modulo MUST assegnare un `caretaker_agent` ai minori con entrambi i genitori morti secondo la priorità parente co-zona, parente ovunque, `None`; con `None` il minore è flaggato e la sua sussistenza è coperta dal tesoro. L'orfano MUST restare intestatario dei propri asset (fix MISS-1).
- **FR-016**: il modulo MUST marcare la coppia come dissolta per morte quando entrambi i partner muoiono nello stesso tick, azzerando i FK e preservando gli snapshot dei nomi (fix MISS-4).
- **FR-017**: il modulo MUST trasferire agli eredi i prestiti in cui il defunto era creditore, e in assenza di eredi umani MUST trasferirli al sistema bancario mantenendoli serviti.
- **FR-018**: il modulo MUST generare memorie di lutto con `emotional_weight = 0.9` per coniuge, figli e relazioni con `strength > 0.6`, propagate tramite `propagate_information`.
- **FR-019**: la successione MUST conservare il valore: la somma di quanto ricevuto dagli eredi e di quanto versato al tesoro MUST essere esattamente pari al patrimonio del defunto, senza creazione né distruzione di moneta.

**Migrazione (`migration.py`, spec di design §6)**

- **FR-020**: il modulo MUST costruire il blocco di contesto `migration_outlook` con differenziale salariale medio a 5 tick, disoccupazione, costo distanza in tick, stabilità di zona e guadagno atteso per ciascuna zona raggiungibile.
- **FR-021**: il modulo MUST calcolare il guadagno atteso con la variante operativa dichiarata di Harris & Todaro (1970), `E[gain_j] = (1 - unemployment_j)·wage_j - wage_current - distance_cost_j`, documentando nel docstring che il salario del settore informale è posto a zero e che la semplificazione è tunable.
- **FR-022**: il modulo MUST calcolare il costo distanza come `ceil(distance_km / (walking_speed_km_per_day · tick_duration_days))` usando `World.distance_scale` e `TRAVEL_SPEEDS`.
- **FR-023**: il modulo MUST far migrare partner e figli sotto `adulthood_age` nello stesso tick del decisore, emettendo un singolo `DemographyEvent` con gli `household_members`, e MUST NOT chiamare i minori al decision loop per quella migrazione (Mincer 1978). I figli adulti MUST decidere indipendentemente.
- **FR-024**: il modulo MUST attivare la fuga d'emergenza solo quando tutte e tre le condizioni sono simultaneamente vere: patrimonio sotto la soglia di sussistenza, `consecutive_ticks_under_subsistence >= flight_trigger_ticks`, e almeno una zona con guadagno atteso positivo (fix I-5).
- **FR-025**: la fuga d'emergenza MUST bypassare l'LLM, applicare il coordinamento familiare e generare una memoria con `emotional_weight = 0.85`.
- **FR-026**: il modulo MUST emettere `trapped_crisis` quando le condizioni di fuga sono soddisfatte ma nessuna zona offre guadagno positivo, e MUST propagarlo come memoria agent-visible con `emotional_weight = 0.95` e `source_type = "public"` a tutti gli agenti co-zone (fix MISS-3).
- **FR-027**: il modulo MUST emettere `mass_flight` quando oltre il 30% della popolazione vivente di una zona fugge entro `flight_trigger_ticks`.
- **FR-028**: entrambi i moduli MUST guardarsi da zone a popolazione zero senza sollevare divisioni per zero.

**Riproducibilità, qualità e documentazione**

- **FR-029**: ogni pescata casuale MUST derivare dagli stream seedati di `rng.py`, così che run con lo stesso seed producano stato identico.
- **FR-030**: ogni formula, costante e parametro MUST citare la propria fonte nel docstring, e ogni semplificazione MUST dichiarare cosa perde, secondo la GOLDEN RULE del progetto.
- **FR-031**: entrambi i moduli MUST avere copertura unitaria completa inclusi gli edge case elencati sopra, su PostgreSQL.
- **FR-032**: la chiusura MUST estendere il capitolo §4.1 di entrambi i whitepaper con i modelli di ereditarietà e migrazione, e MUST aggiungere `inheritance.py` e `migration.py` alla tabella di doc-sync nelle sue quattro copie.

### Key Entities

- **Agent**: acquisisce significato genealogico. `parent_agent` e `other_parent_agent` diventano i canali di trasmissione dei tratti; `caretaker_agent` viene popolato per gli orfani; `death_tick` e `death_cause` innescano la successione.
- **Couple**: unità di analisi per la successione (coniuge erede) e per il coordinamento familiare nella migrazione.
- **DemographyEvent**: registra `migration`, `inheritance_transfer`, `mass_flight`, `trapped_crisis` con i payload documentati nella spec di design.
- **Memory**: veicolo del lutto e della crisi; alimenta il sistema di propagazione esistente.
- **Loan**: cambia creditore alla morte del lender.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: la suite completa passa senza fallimenti e senza xfail, eseguita nel container (`docker compose -f docker-compose.local.yml exec -T web pytest -q`), e `ruff check .` è pulito.
- **SC-002**: la conservazione della successione è verificata da un test dedicato: per ogni regola successoria, contante degli eredi più imposta al tesoro è esattamente uguale al patrimonio iniziale, con tolleranza documentata sui decimali.
- **SC-003**: due run con lo stesso seed producono stato demografico identico, verificato da un test di riproducibilità.
- **SC-004**: tutti e cinque i template d'era caricano e producono ereditarietà e migrazione senza errori, con una regola successoria diversa esercitata per ciascuno.
- **SC-005**: nessuna migrazione di schema è prodotta dal Plan 3; `makemigrations --check --dry-run` resta pulito.
- **SC-006**: l'evaluator delle formule derivate rifiuta l'esecuzione di codice arbitrario, verificato da test che tentano import, chiamate a funzione e accesso ai dunder e si aspettano un rifiuto.
- **SC-007**: l'audit avversariale finale sul codice (gate pesante di fase 6, `critical-analyzer`) dichiara CONVERGED, con zero INCORRECT e zero UNJUSTIFIED residui.
- **SC-008**: al termine, i sei passi dell'orchestratore del Plan 4 hanno tutte le loro dipendenze disponibili: `inheritance.py` espone l'assegnazione del caretaker e `migration.py` espone la fuga d'emergenza.

## Assumptions

- Il design è CONVERGED e non viene riaperto. Le sezioni 4, 5 e 6 della spec `2026-04-18-demography-design-it.md` sono autoritative; i fix I-1, I-5, C-3, MISS-1, MISS-3, MISS-4 e MISS-5 sono già ratificati e vanno implementati come scritti, non ridiscussi. Se l'implementazione rivela una lacuna reale nel design, si escala invece di inventare, secondo il protocollo di escalation di fase 5.
- Plan 1 e Plan 2 sono mergiati e il loro substrato è completo: verificato contro il source tree il 2026-07-17 e riassunto nella tabella del Contesto. Nessuna migrazione di schema né modifica ai template è attesa.
- I moduli sono funzioni pure orchestrabili: il Plan 3 non decide l'ordine dei passi nel tick, che è responsabilità del Plan 4. Le firme devono quindi essere chiamabili dall'orchestratore senza assumere uno stato globale.
- La spec di design è la fonte per formule e costanti; i valori di heritability provengono dagli studi primari trait-specifici citati per tratto, mentre Polderman et al. (2015) resta citato come backbone metodologico e non come fonte dei singoli h².
- Il branch nasce da `develop` a `07aecaa`. Il lavoro segue Spec Kit: questo `spec.md`, poi `/speckit-plan`, poi `/speckit-tasks`. Il gate pesante di fase 2 è già assolto dal design CONVERGED; restano i gate leggeri su piano e task e il gate pesante di fase 6 sul codice.
- L'implementazione per-task va a Sonnet secondo la policy dei modelli, con escalation a Opus per qualsiasi decisione strategica.

## FAQ

**Perché questo work item non rifà il gate pesante di fase 2?**
Perché è già stato pagato. La spec di design della demografia è CONVERGED dopo quattro round di audit avversariale conclusi il 2026-04-18, e copre ereditarietà e migrazione nelle sezioni 4, 5 e 6 con formule, fonti, tabelle di parametri e i fix ratificati. Rifare il gate significherebbe ri-litigare un design approvato, che è esattamente ciò che le regole del progetto vietano. Il gate pesante che resta è quello di fase 6, sul codice.

**Perché il Plan 3 prima del Plan 4, se è il Plan 4 che fa girare la demografia?**
Perché il Plan 4 non è avviabile senza. Due dei sei passi del suo orchestratore chiamano moduli del Plan 3: l'assegnazione del caretaker agli orfani sta in `inheritance.py`, la fuga d'emergenza sta in `migration.py`. L'overview dei piani dichiara la dipendenza `Plan 1 + 2 + 3 merged` e la sequenzialità stretta. La build map è stata corretta il 2026-07-17 perché indicava il Plan 4 come frontiera immediata, omettendo questo vincolo.

**L'evaluator delle formule derivate non è un rischio di sicurezza?**
Lo sarebbe se valutasse stringhe arbitrarie con `eval`. Il design lo vieta esplicitamente: l'evaluator è ristretto ad aritmetica e a riferimenti ai tratti, e l'insieme dei simboli referenziabili è limitato alle chiavi del dict `heritability`. Le formule arrivano dai template d'era, che sono file versionati e non input utente, ma il vincolo resta perché la superficie non va aperta comunque. SC-006 lo verifica con test che tentano import, chiamate e accesso ai dunder e si aspettano un rifiuto.

**Perché la successione deve conservare il valore in modo così rigido?**
Perché il layer economico che le sta accanto ha pagato dodici round di audit proprio su questo. L'audit del layer base ha scoperto che l'implementazione pre-audit iniettava più del doppio del valore prodotto per tick come contante nuovo e fabbricava beni al settlement. La successione muove contante e proprietà: se creasse o distruggesse valore, romperebbe l'invariante di conservazione di §4.8 e contaminerebbe §4.2, entrambi CONVERGED. Da qui SC-002 con un test dedicato per ogni regola.

**Perché il trattamento degli eredi non-binary è codificato in modo diverso per ogni regola?**
Perché le regole successorie modellate sono istituzioni storiche che non avevano una categoria per identità non-binary, e fingere il contrario sarebbe una falsificazione. Il design sceglie una semplificazione pragmatica per ciascuna e la documenta apertamente: con le femmine nell'ordinamento di `primogeniture`, quota figlia in `shari'a`, quota equa in `equal_split`, parentela biologica in `matrilineal`. È una scelta dichiarata, non un default silenzioso.

**Perché Harris-Todaro in variante semplificata invece della forma canonica?**
La forma canonica confronta il reddito urbano atteso `p·w_urban + (1-p)·w_informal` contro quello rurale. Epocha non modella un settore informale per zona, quindi il design pone quel salario a zero e aggiunge un costo di distanza esplicito, ottenendo `E[gain_j] = (1 - unemployment_j)·wage_j - wage_current - distance_cost_j`. La semplificazione è dichiarata nel docstring e il salario informale resta un parametro di zona aggiungibile in futuro, fuori dallo scope di questo work item.

**Perché la fuga d'emergenza bypassa l'LLM?**
Perché sotto la soglia di sopravvivenza la deliberazione non è il modello giusto. Il design cita la razionalità limitata di Simon (1955): un agente che muore di fame da trenta tick non fa un'analisi costi-benefici, scappa. Il fix I-5 aggiunge però un vincolo che evita l'assurdo: se nessuna zona offre un guadagno atteso positivo, l'agente non fugge a caso, resta intrappolato e la cosa diventa un evento osservabile dagli altri.

**Come si integra questo lavoro col whitepaper?**
Il §4.1 oggi descrive mortalità, fertilità e formazione di coppia. Ereditarietà e migrazione sono due modelli scientifici nuovi con la loro catena di citazioni, quindi il capitolo va esteso in entrambe le lingue alla chiusura, e i due moduli vanno aggiunti alla tabella di doc-sync nelle sue quattro copie sincrone (`CLAUDE.md`, i due README, la memoria e il suo backup). Vedi FR-032. Senza, i moduli resterebbero scienza non documentata, e la regola di doc-sync non li coprirebbe per le modifiche future.

**Cosa succede se durante l'implementazione emerge un caso non previsto dal design?**
Si escala, non si inventa. Il protocollo di fase 5 è esplicito: se un task richiede una decisione strategica anziché un'esecuzione specificata, l'implementatore si ferma e la questione torna a Opus, che rivede spec o piano prima che il lavoro riprenda. Un design CONVERGED dopo quattro round rende questo caso improbabile ma non impossibile, e il costo di un aggiramento silenzioso è molto più alto di quello di una pausa.

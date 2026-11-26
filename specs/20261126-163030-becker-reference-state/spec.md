# Feature Specification: stato di riferimento del fattore di Becker nelle ere che richiedono la coppia

**Feature Branch**: `20261126-163030-becker-reference-state`

**Created**: 2026-11-26

**Status**: Draft (fase 2). Disegno in tre passi fatto; audit avversariale non ancora iniziato.

**Input**: decisione dell'utente del 2026-11-26 sulla strada (a) di D-MF-09 della spec `20261029-185654-marital-fertility` («Procedi con la strada (a)»): normalizzare il fattore di Becker nelle ere che richiedono una coppia, come work item a sé.

**Contratto API: invariato.** Nessuna route, nessun serializer, nessun campo di risposta è toccato; il cambiamento è interno al passo di fecondità del motore e al caricatore dei template.

## Perché questo work item esiste

Il livello coniugale delle ere con coppia, `T_m` (`fertility.marital.total_marital_fertility_20_49`), è un dato pubblicato: 6,7 per le due ere preindustriali (Alter, Newton e Oeppen 2020), 6,22 per `industrial` (euristica). La spec coniugale lo definisce come il livello «a fattore di Becker 1» e chiama `ρ_BK` il rapporto fra il livello realizzato e `T_m` (sua sezione (N1a)). Il fattore di Becker (equazione 4.3 del whitepaper) vale 1 solo nel punto in cui tutte le covariate sono zero, cioè per una donna con risparmi pari a un solo tick di sussistenza, istruzione zero, nessuna donna salariata nella zona e prospettive neutre (`fertility.py:338-345`). Quel punto non è la popolazione che ha prodotto il dato pubblicato.

La misura SC-006 della spec coniugale, configurazione B (2.000 fondatori, 360 tick mensili, economia distribuita, un seme), ha dato `ρ_BK` = 1,6162, intervallo al 95% [1,5657, 1,6668] condizionato al seme, fuori dalla banda [0,90, 1,10]; i decili del fattore vanno da 1,399 a 1,816, cioè tutta la distribuzione sta sopra 1 (`specs/20261029-185654-marital-fertility/tasks.md`, T051). La scomposizione dei termini su 72 tick dello stesso scenario (diario del 2026-11-26, `misura-termini.md`) mostra che il fattore medio sale da 1,392 (tick 1-12) a 1,582 (tick 61-72), e che la salita viene dal termine di ricchezza (da +0,356 a +0,441) e da quello di prospettiva (da +0,070 a +0,143). Un livello citato che la simulazione non realizza è un difetto del modello, non della calibrazione: questo work item lo corregge senza toccare le elasticità.

Il work item della fecondità coniugale è fermo al suo T051 e riprende dalla configurazione B di SC-006 dopo la chiusura di questo (FR-012).

## Perimetro

Dentro: il riferimento del fattore di Becker nelle tre ere la cui sezione `fertility` ha il blocco `marital` (`pre_industrial_christian`, `pre_industrial_islamic`, `industrial`); la guardia del caricatore su `beta_0` in quelle ere; la scomposizione dei termini come script versionato; il §4.1.2 dei due whitepaper e i limiti noti che parlano di Becker.

Fuori, e nominato come tale: i valori e i segni di β1..β4 (debito B2-07, riformulato sotto); le ere con il blocco `hadwiger` (`modern_democracy`, `sci_fi`), il cui fattore resta identico a oggi; l'anomalia dell'economia osservata nella misura (sussistenza a 0,01 dal tick 2, ricchezza mediana da 18,3 a 0,10 fra i tick 3 e 5), diagnosticata in un lavoro separato; un riferimento lento con memoria fra tick (rinvio 1).

## Fondamenti scientifici

Le fonti, verificate o no, sono quelle del file di stadio 1 (`Diario/2026/11/2026-11-26/epocha-becker-riferimento/fonti-e-sistema.md`), con lo stesso stato; nessuna è promossa qui.

1. **La struttura moltiplicativa ha un riferimento.** In un modello `b(a)·exp(β·x)` il calendario di base vale nello stato in cui il fattore è 1. Cox (1972), JRSS B 34(2), 187-202, doi:10.1111/j.2517-6161.1972.tb00899.x: VERIFICATO solo sul sommario depositato su Crossref (rischio = funzione delle covariate per una funzione del tempo arbitraria). La prassi di riferire la base alla media delle covariate del campione invece che allo zero: documentazione del pacchetto R `survival`, `basehaz`, argomento `centered` (VERIFICATO sulla pagina; licenza non mostrata; solo l'idea, nessun codice).
2. **Il livello pubblicato è una media di popolazione nelle sue condizioni ordinarie.** Il TMFR 20-49 delle ricostituzioni (Alter, Newton e Oeppen 2020, verificato nella spec coniugale) è un livello su anni-persona di molte famiglie, ricche e povere. Il gradiente di ricchezza misurato in una popolazione preindustriale sta attorno a quella media: Clark e Hamilton (2006), J. Econ. Hist. 66(3), 707-736, doi:10.1017/S0022050706000301, VERIFICATO sul working paper UC Davis n. 229: i testatori più ricchi lasciano circa il doppio dei figli sopravvissuti dei più poveri, e gli autori attribuiscono la differenza più alla sopravvivenza dei figli che alle nascite (sez. VI). L'inferenza «quindi il riferimento è la popolazione» è mia, non degli autori.
3. **Le risposte preindustriali misurate sono a scarti dalle condizioni ordinarie.** Bengtsson e Dribe (2006), Demography 43(4), 727-746, doi:10.1353/dem.2006.0030, VERIFICATO sul sommario: in una popolazione a fecondità naturale le famiglie senza terra rispondono a variazioni di breve periodo dei prezzi del cibo. Galloway (1988), Population Studies 42(2), 275-303: metadati VERIFICATI, testo NON letto; il numero «un raddoppio dei prezzi riduce la fecondità di meno del 15%» (p. 303) lo conosco solo tramite Clark e Hamilton. Lee (1981), cap. 9 di Wrigley e Schofield: NON VERIFICATO.
4. **Il segno di β1 non ha appoggio sicuro.** Becker (1960), NBER c2387, VERIFICATO solo a p. 231: il reddito alza la fecondità **desiderata**, e quella effettiva può restare sotto. Becker e Lewis (1973), JPE 81(2), S279-S288, VERIFICATO sulla ristampa NBER c2963: l'elasticità osservata della quantità può essere negativa con quella «vera» positiva; nessun reddito di riferimento. Jones e Tertilt (2008), doi:10.1016/S1574-0129(08)00005-7, VERIFICATO sul NBER WP 12796: elasticità al reddito occupazionale assoluto **−0,38**, negativa in ogni coorte USA 1826-1960, segno opposto a β1 = +0,1. Easterlin (1966): metadati verificati, contenuto solo tramite MacDonald e Rindfuss (1976), che non trovano effetto del reddito relativo nei microdati. Becker (1991): NON VERIFICATO.

Da 1 e 2 segue la scelta di questa spec: nelle ere a fecondità naturale il riferimento del fattore è la popolazione delle donne a cui il livello pubblicato si riferisce. Da 3 segue ciò che la scelta perde (sezione «Che cosa si perde»). Da 4 segue che i valori di β1..β4 restano un debito, non un risultato.

### Licenze e attribuzione

Solo idee e numeri pubblicati, citati; nessun codice, testo o tabella copiati. La documentazione di `survival` è usata per un'idea di metodo, senza codice.

## Il modello

### Esponente e fattore (B1)

L'esponente lineare resta quello di oggi, con le stesse covariate e gli stessi coefficienti:

```
η_i = β0 + β1·w_i + β2·e_i + β3·φ_z(i) + β4·ω_i                                         (B1)
w_i = ln(max(wealth_i / max(s_z(i), 1e-6), 0,1))
```

con `s_z` la soglia di sussistenza per tick della zona (`context.compute_subsistence_threshold`), `e_i` = `education_level`, `φ_z` la proxy di partecipazione femminile della zona, `ω_i` le prospettive aggregate (`context.compute_aggregate_outlook`). Fonte della forma: la (4.3) del whitepaper, euristica ispirata a Becker (1991, NON VERIFICATO); nessun valore cambia.

### Riferimento di popolazione nelle ere con coppia (B2)

Nelle ere la cui sezione `fertility` ha il blocco `marital` il fattore è

```
m_BK,i = clip(exp(η_i − L_t), 0,05, 3,0)                                                 (B2)
L_t    = ln( Σ_{j∈C_t} r_j·exp(η_j) / Σ_{j∈C_t} r_j )                                    (B2a)
```

dove `C_t` è l'insieme delle **candidate idonee del tick in tutta la simulazione**: le donne vive nella finestra fertile dell'orchestratore che passano i cancelli della probabilità (in coppia attiva, senza `avoid_conception` attivo al tick, tasso di base positivo), e `r_j` = r(a_j) è il loro tasso coniugale annuo (N1) della spec coniugale. Se `C_t` è vuoto non c'è nessun fattore da calcolare. `L_t` si calcola con la forma log-sum-exp (si sottrae il massimo degli η prima di esponenziare), che dà lo stesso numero senza overflow.

Nelle ere con il blocco `hadwiger` il fattore resta `clip(exp(η_i), 0,05, 3,0)`, cioè `L_t = 0`, identico a oggi.

### Proprietà che ne seguono (B3)

1. **Invarianza delle nascite attese.** Se nessun fattore del tick è tagliato dal clip, Σ_{i∈C_t} r_i·m_BK,i = Σ_{i∈C_t} r_i: le nascite attese del tick prima del soffitto malthusiano sono quelle a fattore 1. È la definizione di «livello a fattore di Becker 1» della (N1a) coniugale portata a ogni tick, non un risultato empirico.
2. **Cancellazione dei termini comuni.** Ogni addendo uguale per tutte le candidate del tick si cancella fra η_i e L_t: β0, i due termini di prospettiva di simulazione (fiducia bancaria e stabilità del governo), un fattore comune su tutte le soglie di sussistenza o su tutte le ricchezze, e quindi la **durata del tick**, che moltiplica tutti gli orizzonti per la stessa costante.
3. **Differenze fra donne invariate.** Il rapporto fra i fattori di due candidate dello stesso tick è exp(η_i − η_j), identico a oggi (salvo clip): le elasticità β1..β4 continuano a ordinare le donne come prima.
4. **Ere Hadwiger invariate.** Per gli stessi ingressi il fattore è identico bit per bit a quello di oggi.

### Che cosa si perde

Con un riferimento che si muove con la popolazione a ogni tick, nelle ere con coppia le nascite attese del tick non rispondono più alle condizioni economiche **comuni** a tutta la popolazione: un anno di prezzi alti che abbassa gli orizzonti di tutte nella stessa proporzione non cambia le nascite attese. Resta la risposta delle differenze fra donne e fra zone (proprietà 3): uno shock che colpisce più le povere sposta nascite dalle povere alle ricche senza cambiarne il totale. La letteratura dice che una risposta aggregata di breve periodo esisteva ed era piccola: meno del 15% per un raddoppio dei prezzi (Galloway 1988 tramite Clark e Hamilton; testo primario non letto), deliberata e concentrata nelle famiglie senza terra (Bengtsson e Dribe 2006, sommario). Oggi quella risposta nel modello c'è ma con un livello sbagliato del 62% e con un'economia che ha un'anomalia non diagnosticata; dopo questo work item non c'è. Un riferimento lento che la conservi è il rinvio 1.

## Parametri per era

Nessun valore di template cambia. I cinque template hanno β0 = 0,0, β1 = 0,1, β2 = −0,05, β3 = −0,1, β4 = 0,2 (Tabella 4.4 del whitepaper, tunable heuristic, debito B2-07). Nelle tre ere con coppia β0 non ha effetto (B3, proprietà 2) e il caricatore richiede che valga 0 (FR-006). I bound del clip, 0,05 e 3,0, restano euristiche di guardia (Appendice A.3 del whitepaper).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Il livello coniugale realizzato è quello pubblicato (Priority: P1)

Chi usa un'era con coppia vuole che il TMFR realizzato fra 20 e 49 anni sia `T_m`, comunque si muova l'economia.

**Why this priority**: è la ragione del work item e sblocca la chiusura del work item coniugale.

**Independent Test**: test unitario dell'invarianza (SC-001) e run di SC-007.

**Acceptance Scenarios**:

1. **Given** tre candidate idonee di un'era con coppia di 22, 30 e 41 anni con ricchezze diverse e coefficienti di seme, **When** calcolo i loro fattori nello stesso tick, **Then** Σ r_i·m_i = Σ r_i entro 1e-12 in valore relativo.
2. **Given** le stesse candidate con tutte le ricchezze moltiplicate per 7, **When** ricalcolo, **Then** ogni fattore è uguale a prima entro 1e-12.
3. **Given** la run di SC-007, **When** misuro `ρ_BK` su 360 tick e su tre finestre decennali, **Then** ogni stima puntuale sta in [0,90, 1,10].

### User Story 2 - Le differenze economiche fra donne restano (Priority: P1)

Chi studia il modello vuole che una donna con più risorse continui ad avere un fattore più alto di una con meno, con le elasticità di oggi.

**Independent Test**: SC-002.

**Acceptance Scenarios**:

1. **Given** due candidate dello stesso tick con orizzonti in rapporto e (numero di Eulero) e il resto uguale, **When** calcolo i fattori, **Then** il loro rapporto è exp(β1) entro 1e-12.

### User Story 3 - Le ere senza coppia non cambiano (Priority: P1)

**Independent Test**: SC-003.

**Acceptance Scenarios**:

1. **Given** un agente di `modern_democracy` e uno di `sci_fi` con ingressi fissati, **When** calcolo il fattore prima e dopo il work item, **Then** i valori sono identici bit per bit.

### User Story 4 - Un template incoerente è rifiutato (Priority: P2)

**Acceptance Scenarios**:

1. **Given** una copia di `pre_industrial_christian` con `beta_0 = 0.3`, **When** la carico, **Then** il caricatore solleva l'errore di validazione con il percorso `fertility.becker_coefficients.beta_0`.
2. **Given** `modern_democracy` con `beta_0 = 0.3`, **When** la carico, **Then** si carica (nelle ere Hadwiger β0 ha effetto).

### Edge Cases

- **Nessuna candidata idonea nel tick**: nessun fattore da calcolare; il passo non calcola `L_t`.
- **Una sola candidata idonea**: il suo fattore è 1 (exp(η − η)); Becker non ha effetto con una popolazione di una.
- **Chiamata ad hoc senza `zone_context`** in un'era con coppia (test, script): la popolazione di riferimento è la sola madre, fattore 1 (FR-004).
- **`zone_context` passato senza riferimento** in un'era con coppia: errore tipizzato (FR-004), mai il riferimento x = 0 in silenzio.
- **Fattore tagliato dal clip**: l'invarianza (B3.1) vale solo per i tick senza tagli; la misura riporta la quota di tagli (SC-006).
- **Zone miste, con e senza `ZoneEconomy`**: le zone senza hanno soglia 0 e orizzonti divisi per 1e-6, η più alto di circa 0,92 a parità di ricchezza; la normalizzazione abbassa le candidate delle altre zone. Il caso esiste solo con l'economia legacy deprecata; limite noto.
- **Popolazione oltre lo 0,8·`max_population`**: il soffitto malthusiano moltiplica dopo il fattore, come oggi; l'invarianza vale prima del soffitto.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: `fertility.py` espone `eligible_base_rate(mother, fertility_cfg, tick_duration_hours, demography_acceleration, *, current_tick, partnered_agent_ids)` che applica, nell'ordine di oggi, il cancello della coppia, `avoid_conception`, l'età e il calendario di base, e restituisce r(a) oppure 0,0. `tick_birth_probability` la usa al posto dei propri cancelli; nessun altro punto del codice decide quali candidate sono idonee.
- **FR-002**: `fertility.py` espone `becker_exponent(agent, coeffs, *, zone_context)` che restituisce η (B1) senza clip; `becker_modulation` la usa. È l'unico punto che somma i termini.
- **FR-003**: `fertility.py` espone `becker_log_reference(candidates, fertility_cfg, zone_contexts, ...)`, funzione pura sugli oggetti già caricati, che calcola `L_t` (B2a) con log-sum-exp sulle candidate con `eligible_base_rate` positivo, pesi r_j; restituisce `None` se nessuna è idonea. Non esegue query e non consuma numeri casuali.
- **FR-004**: `becker_modulation(agent, coeffs, *, zone_context=None, log_reference=...)` applica (B2) quando riceve un riferimento e la forma di oggi (`L = 0`) nelle ere Hadwiger. Il riferimento arriva dentro il `zone_context` con la chiave `becker_log_reference`, che `build_zone_fertility_context` riceve come argomento; `tick_birth_probability` lo passa solo nelle ere con coppia. In un'era con coppia: con `zone_context` assente, la funzione usa come popolazione la sola madre (fattore exp(0) = 1, salvo clip); con `zone_context` presente e chiave assente, solleva `BeckerReferenceMissing`, sottoclasse di `ValueError`. Il fattore normalizzato è calcolato dentro `becker_modulation`, così chi la avvolge (lo script di SC-006) registra il fattore applicato.
- **FR-005**: `orchestrator.run_fertility_step`, nelle ere con coppia, costruisce i contesti di zona per le zone delle candidate prima del ciclo, calcola `L_t` una volta con FR-003 sugli stessi candidati ordinati per id, lo inserisce nei contesti e poi esegue il ciclo di oggi. Nelle ere Hadwiger il passo non calcola `L_t`. Il numero di query del passo resta quello di oggi (FR-016 e FR-016a del Plan 4).
- **FR-006**: il caricatore (`template_loader.validate_template`) rifiuta una sezione `fertility` con il blocco `marital` e `beta_0` ≠ 0, con un errore di validazione che nomina il percorso `fertility.becker_coefficients.beta_0`. I cinque template distribuiti si caricano.
- **FR-007**: lo script `scripts/measure_becker_terms.py` (versione versionata della scomposizione del 2026-11-26) riusa il mondo e il registratore di `scripts/measure_marital_schedule_run.py`, ricalcola per ogni chiamata i cinque termini, `L_t` e il fattore applicato, verifica l'uguaglianza con il fattore restituito entro 1e-9, e riporta per blocchi di 12 tick: fattore medio semplice e pesato con r, media di ciascun termine, percentili dell'orizzonte, quota di clip, quota di guardie 0,1, e la soglia di sussistenza per zona. Accetta il numero di tick e di fondatori da ambiente, come lo script di SC-006.
- **FR-008**: lo script di SC-006 della spec coniugale (`scripts/measure_marital_schedule_run.py`) riporta, oltre a `ρ_BK` su tutta la run, `ρ_BK` e il suo intervallo al 95% per tre finestre di 120 tick, e la quota di fattori tagliati dal clip; la condizione di fallimento si estende alle finestre (SC-007).
- **FR-009**: docstring di `becker_modulation`, `becker_exponent`, `becker_log_reference`, `eligible_base_rate`, `build_zone_fertility_context` e `run_fertility_step` aggiornati: fonti, il significato di `L_t`, le quattro proprietà (B3), la perdita della risposta aggregata. Il docstring di `becker_modulation` smette di dire «Scale baseline ASFR» e «calibration deferred to Plan 4».
- **FR-010**: nello stesso commit del codice, in entrambe le lingue (`docs/whitepaper/epocha-whitepaper.md` e `.it.md`), il §4.1.2 aggiorna: le equazioni (B2)-(B2a) accanto alla (4.3); il paragrafo dei ruoli dei coefficienti, dove «`β₀` = baseline (centred at the era's biological schedule)» diventa vero per costruzione solo nelle ere con coppia e va riscritto per era, e «higher relative wealth» va riscritto come ricchezza relativa alla sussistenza nelle ere Hadwiger e relativa alla popolazione del tick nelle ere con coppia; la Tabella 4.4 e l'Appendice A.3 (β0 senza effetto e vincolato a 0 nelle ere con coppia); le Semplificazioni e i Limiti noti che citano `T_m·ρ_BK`, i casi 1,79 e 3,0 e B2-07; la perdita della risposta aggregata; i riferimenti di riga ormai sbagliati del §4.1.2 (`fertility.py` «line 85», «line 118», «line 19», `fertility.py:204`, `:118-145`, `:70-82`). Le voci Cox (1972), Clark e Hamilton (2006), Bengtsson e Dribe (2006), Becker e Lewis (1973) entrano in bibliografia con lo stato di verifica di questa spec.
- **FR-011**: il debito B2-07 è riformulato nel whitepaper e nella spec coniugale con i fatti dello stadio 1: coefficienti omogenei fra le ere; segno di β1 positivo contro l'elasticità negativa di Jones e Tertilt (che il docstring cita); gradiente preindustriale di Clark e Hamilton sui figli sopravvissuti e non sulle nascite; Becker (1960) sulla fecondità desiderata; Easterlin con verifica empirica negativa; dipendenza dalla durata del tick nelle ere Hadwiger.
- **FR-012**: alla chiusura di questo work item, il work item `20261029-185654-marital-fertility` riprende dal suo T051, configurazione B, con lo script di FR-008; la sua spec registra il nuovo esito.
- **FR-013**: la build map (`docs/build-map/epocha-build-map.html`, italiano e inglese insieme) registra l'apertura di questo work item e, alla chiusura, il nuovo stato del §4.1.2, ripubblicata sullo stesso URL.

### Costo per tick, riepilogo

Zero query in più: il pre-passaggio usa candidate già caricate con `fertility_state` selezionato, il tick passato esplicitamente e i contesti di zona che il ciclo costruirebbe comunque per le stesse zone. Calcolo aggiuntivo: una valutazione di η, un esponenziale e una somma per candidata, e lo stesso cancello valutato due volte (una nel pre-passaggio, una nella probabilità). Nelle ere Hadwiger nessun costo.

### Test che si muovono e perché

- `tests/test_subsistence_horizon.py:140-149` (fattore 1 a ricchezza = soglia): usa coefficienti propri e nessun `zone_context`; resta valido se chiamato come era Hadwiger o ad hoc; va riletto perché il suo scopo (accordo fra soglia di fecondità e di fuga) resti espresso dopo il cambio.
- `tests/test_subsistence_horizon.py:137-138` (rapporto exp(β1)): invariato, ed è il test della proprietà B3.3.
- `tests/test_fertility.py:224-272` (segno del fattore rispetto a 1 con ricchezza alta e bassa): restano veri con riferimento x = 0 (chiamate ad hoc senza era); il loro significato va dichiarato nel docstring.
- `tests/test_fertility.py` (4 chiamate di `tick_birth_probability`), `tests/test_fertility_zone_context.py` (4 chiamate, `pre_industrial_christian` con `zone_context` costruito dal test) e `tests/test_integration_plan2.py` (3): in un'era con coppia passano un `zone_context` senza riferimento e, per FR-004, solleverebbero `BeckerReferenceMissing`; vanno aggiornati a passare il riferimento. Con coefficienti tutti zero il riferimento è 0 e i valori attesi non cambiano.
- `tests/test_marital_schedule_run_harness.py`: verifica che il registratore raggiunga `becker_modulation` come globale del modulo; deve restare vero (FR-004).
- `tests/test_demography_cost.py` e il test di costo di `test_fertility_zone_context.py`: conteggi invariati (FR-005).
- `scripts/measure_marital_schedule_run.py:187-188` (azzeramento dei coefficienti per A): invariato; con i coefficienti a zero L_t = 0.

### Key Entities

Nessun modello nuovo e nessuna migrazione. `L_t` è un numero calcolato e scartato a ogni tick, mai salvato.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001 (invarianza delle nascite attese)**: test unitario su un insieme di candidate di un'era con coppia senza clip: |Σ r_i·m_i − Σ r_i| / Σ r_i < 1e-12. Fallisce altrimenti. Prova di guardia: con la normalizzazione disattivata (mutazione nominata, poi annullata) il test fallisce.
- **SC-002 (termini comuni e differenze)**: test unitari: (a) moltiplicare per 7 tutte le ricchezze, oppure dividere per 7 tutte le soglie di sussistenza (che è ciò che un tick più lungo fa all'orizzonte, perché la soglia è per tick), lascia ogni fattore uguale entro 1e-12; (b) cambiare β0 da 0 a 0,3 su un dizionario di coefficienti passato direttamente lascia ogni fattore uguale entro 1e-12; (c) il rapporto fra due candidate con orizzonti in rapporto e vale exp(β1) entro 1e-12. Fallisce se uno dei tre non vale.
- **SC-003 (ere Hadwiger ferme)**: per un insieme fissato di ingressi di `modern_democracy` e `sci_fi`, il fattore è uguale bit per bit al valore calcolato con la formula di oggi. Fallisce a qualunque differenza.
- **SC-004 (costo)**: i test di costo del passo di fecondità passano con i conteggi di oggi, nessun numero modificato. Fallisce se un conteggio cambia.
- **SC-005 (caricatore)**: gli scenari della User Story 4 e il caricamento dei cinque template. Fallisce se uno dei due scenari dà l'esito opposto.
- **SC-006 (scomposizione riproducibile)**: lo script di FR-007 su 2.000 fondatori e 72 tick mensili, economia `pre_industrial`, un seme, completa con l'uguaglianza entro 1e-9 a ogni chiamata e riporta, per ogni blocco, una media del fattore pesata con r che sta entro 1e-9 da 1 nei tick senza clip. Fallisce se una delle due condizioni non vale. Riporta anche la quota di clip e la soglia di sussistenza per zona, come dato.
- **SC-007 (livello realizzato, 360 tick)**: la configurazione B di SC-006 della spec coniugale, rifatta con lo script di FR-008 nella configurazione di quella spec (2.000 fondatori, 360 tick mensili, `max_population` 10⁶, economia `pre_industrial`, un seme): la stima puntuale di `ρ_BK` su tutta la run e su ciascuna delle tre finestre di 120 tick sta in [0,90, 1,10]. Fallisce se una delle quattro stime esce. Gli intervalli al 95% sono riportati, condizionati al seme, e non decidono. La banda è l'euristica della Trinità di D-MF-09, non una grandezza demografica.

## Assumptions

- Il livello pubblicato `T_m` descrive la popolazione nelle sue condizioni economiche ordinarie, e la popolazione delle candidate idonee della simulazione nel tick è il suo analogo. È un'inferenza dalle fonti 1-2, non un'affermazione di un autore.
- La popolazione di riferimento è quella della simulazione intera, non della zona: `T_m` è un livello di popolazione, e un riferimento di zona cancellerebbe le differenze economiche fra zone.
- Le donne fuori coppia non entrano nel riferimento: nelle ere con coppia il loro tasso è zero e il fattore non si applica a loro.
- Il clip resta dopo la normalizzazione; nella misura del 2026-11-26 nessuna chiamata è tagliata su 19.934, quindi l'invarianza vale in quella configurazione. In altre configurazioni non è misurata.
- La scelta non dipende dal livello dei prezzi né dall'anomalia dell'economia (B3.2: un fattore comune si cancella); dipende dalla **dispersione** dentro il tick, che quell'anomalia può influenzare. Nella misura la dispersione è grande nel primo anno (orizzonte p10 8,4, mediana 12,4, p90 1.577) e piccola dopo (p10 76,5 e p90 87,6 negli ultimi 12 tick).

## Rinvii espliciti (cosa NON fa questa versione)

1. **Riferimento lento con memoria.** Un `L` mediato su una finestra di anni conserverebbe la risposta aggregata di breve periodo, cioè lo scarto dal trend che Galloway e Lee misurano. Richiede stato persistente fra tick, una finestra con fonte (Lee 1981 non letto) e un percorso economico diagnosticato. Work item separato.
2. **β1..β4**: valori, segni e omogeneità restano nel debito B2-07 (FR-011).
3. **Ere Hadwiger**: riferimento x = 0 e dipendenza dalla durata del tick restano come oggi, dichiarati in B2-07.
4. **Anomalia dell'economia** (sussistenza a 0,01 dal tick 2, che leggo come il pavimento `MIN_PRICE = 0.01` di `economy/market.py:40` su un solo bene essenziale, inferenza non verificata; ricchezza mediana da 18,3 a 0,10 fra i tick 3 e 5): diagnosi separata. Questa spec ne registra solo i numeri.

## Known Limitations

- Nelle ere con coppia le nascite attese del tick non rispondono alle condizioni economiche comuni a tutta la popolazione (sezione «Che cosa si perde»).
- L'invarianza fissa le nascite totali del tick, non la media del fattore in ogni gruppo d'età: se il fattore cresce con l'età, `ρ_BK` differisce da 1 per un termine di secondo ordine, che SC-007 misura.
- Una candidata può ancora avere fattore 3,0, cioè tre volte la media del tick; a 20-24 anni con T_m 6,7 il tasso sarebbe 1,03 nascite per anno. Nella misura nessuna chiamata arriva al clip.
- Con zone miste con e senza `ZoneEconomy` il riferimento è distorto (Edge Cases).
- Con una popolazione piccola il riferimento è rumoroso; con una sola candidata Becker non ha effetto.
- Un seme solo nella misura e in SC-007.

## Architettura e collocazione

Tutto resta in `epocha/apps/demography`: le tre funzioni in `fertility.py`, proprietario del fattore; il pre-passaggio in `orchestrator.run_fertility_step`, che già possiede i candidati del tick e i contesti di zona; la guardia in `template_loader.py`. Nessuna dipendenza nuova, nessun import verso l'alto. Alternative di collocazione scartate: calcolare `L_t` dentro `build_zone_fertility_context` (è per zona, il riferimento è di simulazione); un modulo nuovo (un solo chiamante, una funzione).

## Registro del design

Le tre fasi complete sono nel diario (`Diario/2026/11/2026-11-26/epocha-becker-riferimento/disegno-tre-passi.md`); qui la sintesi.

### Passo 1 — Proposta iniziale

Covariate centrate sulle medie della zona a ogni tick, con una query aggregata per zona in `build_zone_fertility_context`.

### Passo 2 — Primo self-review critico (Matteo)

Critici: la query aggregata interroga un insieme diverso da quello a cui il fattore si applica e duplica la selezione dei candidati (C1); centrare le covariate lascia lo scarto di Jensen (0,9974 nel primo blocco, calcolato offline) e impone una scelta fra media del logaritmo e logaritmo della media (C2); il riferimento di zona cancella le differenze economiche fra zone (C3). Importanti: β0 diventa inerte (I1), si perde la risposta aggregata (I2), la media non era pesata con il tasso (I3), chiamate senza riferimento (I4), ordine fra clip e normalizzazione (I5). Ucciso: query aggregata, centramento delle covariate, riferimento di zona.

### Passo 3 — Secondo self-review e consolidamento

Le correzioni hanno introdotto: un secondo cancello di idoneità (risolto con `eligible_base_rate`, FR-001); il rischio che il pre-passaggio sia registrato dallo script come una seconda chiamata (risolto separando `becker_exponent`, FR-002); il caso delle zone miste (limite); la tentazione del riferimento lento (rinviato); il secondo ordine fra pesi per tasso e ρ_BK (misurato da SC-007); i test che passano un contesto senza riferimento (elencati). Scartata anche la regola unica per tutte le ere (D-BK-04).

### Cronaca

- 2026-11-26: T051 della spec coniugale fallisce in configurazione B (`ρ_BK` = 1,6162); l'utente sceglie la strada (a) di D-MF-09; stadio 1 (sistema e fonti); scomposizione dei termini su 72 tick (fattore medio 1,4535, ipotesi offline 0,9865 e 0,9996); cornice di Domenico D-26-E-7; disegno in tre passi e questa spec.

## Alternative considerate

- **Centrare le covariate** sulle medie del tick (prassi `centered = TRUE`): approssima la media 1 (0,9996 offline su 72 tick, 0,9974 nel primo blocco) e chiede quattro medie con scelte di forma; la normalizzazione del moltiplicatore dà 1 esatto con un numero.
- **Centrare solo la ricchezza sulla mediana del tick**: 0,9865 offline, da 0,952 a 1,018 per blocco; lascia la deriva della prospettiva.
- **Riferimento fisso** (media al tick 1 o ai primi anni): la misura mostra il fattore che sale di 0,19 in sei anni con la ricchezza accumulata; fallirebbe sulla run lunga.
- **Riferimento di zona**: cancella le differenze fra zone (C3).
- **Media non pesata**: non fissa le nascite attese (I3).
- **Strada (b) di D-MF-09**, cioè dichiarare `ρ_BK` = 1,62: scartata dall'utente.
- **β = 0 nelle ere con coppia**: toglierebbe anche le differenze fra donne; la cornice chiede di non toccare le elasticità.

## Decisioni provvisorie della Trinità

- **D-BK-01, normalizzare il moltiplicatore o centrare le covariate.** A (Matteo): moltiplicatore, media esatta, un numero, cancella β0 e la durata del tick. B: covariate centrate, prassi dei rischi proporzionali, conserva un significato di β0. Evidenza: offline 0,9996 contro 1 per costruzione; quattro scelte di forma contro nessuna. **Scelta: A.**
- **D-BK-02, popolazione e momento del riferimento.** A: candidate idonee di tutta la simulazione, a ogni tick, pesate con r. B: riferimento lento (finestra di anni). C: zona. Evidenza: deriva misurata del fattore (da 1,392 a 1,582), C cancella le zone, B chiede stato e una finestra senza fonte. Costi: A nessuna query e nessuno stato; B un modello o un campo e una migrazione. Perdita di A: la risposta aggregata (dichiarata). **Scelta: A**, B rinviato.
- **D-BK-03, β0 nelle ere con coppia.** A: il caricatore richiede 0. B: solo documentazione. Un parametro senza effetto che un template può impostare è una trappola; la guardia è validazione. **Scelta: A.**
- **D-BK-04, solo ere con coppia o tutte.** A: solo ere con coppia, discriminatore esistente. B: tutte, senza ramo. B sposta il TFR realizzato di `modern_democracy` e `sci_fi` e toglie alle ere moderne la risposta aggregata al reddito, canale della transizione nei dati di Jones e Tertilt. **Scelta: A.**
- **D-BK-05, chiamata senza riferimento.** A: errore tipizzato con contesto senza chiave, popolazione di una senza contesto. B: riferimento 0 in silenzio. B riproduce il difetto che il work item corregge. **Scelta: A.**

Tutte provvisorie, in attesa della conferma dell'utente al gate di fase 2.

## FAQ

**Perché normalizzare il moltiplicatore e non centrare le covariate, che è la prassi dei modelli a rischi proporzionali?** Nei rischi proporzionali il centramento serve a stimare e a leggere una curva di base; qui il livello di base è un dato pubblicato e il requisito è che la media del fattore sia 1 sulla popolazione a cui il dato si riferisce. Il centramento lo ottiene solo a meno dello scarto di Jensen e di una scelta fra media del logaritmo e logaritmo della media; la normalizzazione lo ottiene per costruzione con un solo numero. I rapporti fra donne sono gli stessi nei due casi.

**Perché pesare con il tasso di base?** Perché così la somma delle probabilità del tick, cioè le nascite attese, resta quella a fattore 1, che è il significato di `T_m` nella spec coniugale. Una media semplice darebbe lo stesso peso a una donna di 47 anni (tasso 0,018) e a una di 22 (0,343).

**Perché la simulazione e non la zona?** Le ricostituzioni che danno `T_m` coprono molte parrocchie; la zona di Epocha non ha un livello pubblicato suo. Un riferimento di zona cancellerebbe le differenze di sussistenza e di lavoro femminile fra zone.

**Che cosa resta di Becker nelle ere con coppia?** La differenza fra donne: a parità del resto, un orizzonte di sopravvivenza e volte più lungo dà un fattore exp(0,1) = 1,105 volte più alto, come oggi. Non resta l'effetto delle condizioni comuni.

**Le fonti sostengono la perdita della risposta aggregata?** No, la sostengono come esistente: Galloway (letto solo tramite Clark e Hamilton) dà meno del 15% per un raddoppio dei prezzi, Bengtsson e Dribe una risposta deliberata delle famiglie povere. Questa spec la toglie e lo dichiara, perché oggi la risposta aggregata del modello è dominata da un livello sbagliato del 62% e da un'economia con un'anomalia non diagnosticata; il riferimento lento è il rinvio 1.

**Il segno di β1 è giusto?** Non lo so, ed è per questo che resta nel debito B2-07. Jones e Tertilt, citati dal codice, trovano −0,38 sul reddito assoluto negli Stati Uniti 1826-1960; Clark e Hamilton trovano un gradiente positivo sui figli sopravvissuti nell'Inghilterra 1585-1638, attribuito più alla sopravvivenza che alle nascite; Becker (1960) parla di fecondità desiderata.

**Come si integra con il soffitto malthusiano e con `avoid_conception`?** Il soffitto moltiplica dopo il fattore, come oggi; l'invarianza vale prima del soffitto. `avoid_conception` è uno dei cancelli di `eligible_base_rate`: una donna che lo ha attivo non entra nel riferimento e non ha fattore.

**E con lo script di SC-006?** Il fattore normalizzato nasce dentro `becker_modulation`, che lo script avvolge; il pre-passaggio usa `becker_exponent`, che lo script non conta. Il registratore vede una chiamata per candidata con il fattore applicato.

**Quanto costa?** Zero query in più per tick; un esponenziale e una somma per candidata. I test di costo restano con i conteggi di oggi.

**È deterministico?** Sì: la somma segue l'ordine per id dei candidati, che la query già impone, e il pre-passaggio non consuma numeri casuali, quindi il flusso `fertility` estrae gli stessi numeri nello stesso ordine. Con lo stesso seme la run si ripete; le nascite differiscono da quelle di prima perché cambiano le probabilità.

**Che cosa succede con la durata del tick?** Nelle ere con coppia non conta più: moltiplica tutti gli orizzonti per la stessa costante, che si cancella. Nelle ere Hadwiger conta come oggi (circa un fattore 1,16 fra tick settimanali e mensili con β1 = 0,1, dedotto dal codice e non misurato).

**Perché non un modulo nuovo o un modello per salvare `L_t`?** Una funzione con un chiamante non giustifica un modulo, e `L_t` si ricalcola dagli stessi dati a ogni tick: salvarlo creerebbe uno stato che può divergere dai dati.

**Quali sono i modi di guasto?** Un template con β0 ≠ 0 in un'era con coppia fallisce al caricamento; un contesto senza riferimento in un'era con coppia solleva `BeckerReferenceMissing`; zone miste con e senza economia distorcono il riferimento senza errore (limite noto).

**Sicurezza e privacy?** Nessuna superficie nuova: nessun ingresso esterno, nessuna API, nessun dato personale; il caricatore guadagna una validazione.

**Confronto con librerie esistenti?** Nessuna libreria di simulazione demografica usata da Epocha fornisce questa normalizzazione; è un'operazione di una riga su dati già in memoria, e una dipendenza non si giustifica.

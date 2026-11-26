# Feature Specification: stato di riferimento del fattore di Becker nelle ere a fecondità naturale

**Feature Branch**: `20261126-163030-becker-reference-state`

**Created**: 2026-11-26

**Status**: Draft (fase 2), **non approvabile**. Audit avversariale round 1 **NOT CONVERGED** (2 INCORRECT, 4 UNJUSTIFIED, 2 INCONSISTENT, 4 MISSING), registro in `checklists/audit.md`. La scelta del riferimento (sezione «La scelta aperta») è **bloccata** fino alla correzione dell'economia del mondo di prova (voce di build map `spine2.n20`, nessun branch ancora; decisione provvisoria della coordinazione D-26-E-9): i dati disponibili vengono da un'economia degenere e non possono decidere.

**Input**: decisione dell'utente del 2026-11-26 sulla strada (a) di D-MF-09 della spec `20261029-185654-marital-fertility` («Procedi con la strada (a)»): normalizzare il fattore di Becker nelle ere che richiedono una coppia, come work item a sé.

**Contratto API: invariato.** Nessuna route, nessun serializer, nessun campo di risposta è toccato; il cambiamento è interno al passo di fecondità del motore, ai template e al caricatore.

## Perché questo work item esiste

Il livello coniugale `T_m` (`fertility.marital.total_marital_fertility_20_49`) è definito dalla spec coniugale come il livello «a fattore di Becker 1» (sua sezione (N1a)). Il fattore di Becker (equazione 4.3 del whitepaper) vale 1 solo dove tutte le covariate sono zero (`fertility.py:338-345`): risparmi pari a un solo tick di sussistenza, istruzione zero, nessuna donna salariata nella zona, prospettive neutre. Quel punto non è la popolazione a cui un livello di fecondità naturale pubblicato si riferisce. È un difetto di **definizione** del modello, visibile dalla lettura del codice e indipendente da qualunque run: il livello che il template cita e il livello che il modello realizza coincidono solo per caso.

La misura SC-006 della spec coniugale, configurazione B, ha dato `ρ_BK` = 1,6162 (T051). La diagnosi dell'economia dello stesso mondo di prova (diario del 2026-11-26, `diagnosi-economia.md`) mostra che quel mondo è degenere: il prezzo dell'unico bene essenziale scende al pavimento `MIN_PRICE` = 0,01 dal tick 2 per un ciclo di prezzo che itera a quantità fisse (`economy/market.py:105-166`), i neonati con ruolo `child` producono lusso dalla nascita (`economy/production.py:186-190`), la massa monetaria raddoppia al tick 3 e la ricchezza crolla ai tick 3-5. Dal tick 2 il segnale di ricchezza di Becker misura il pavimento dei prezzi. Quindi 1,6162 e la scomposizione dei termini su 72 tick (`misura-termini.md`) sono numeri veri di un mondo degenere: provano che il difetto di definizione produce un livello sbagliato, non quanto sbagliato in un'economia sana, né quale correzione sia migliore.

Il work item coniugale è fermo al suo T051 e riprende dalla configurazione B di SC-006 dopo la chiusura di questo (FR-011).

## Perimetro

**Dentro**: le due ere il cui `T_m` è un livello di fecondità naturale preindustriale, `pre_industrial_christian` (6,7, dato provvisorio di Alter, Newton e Oeppen 2020, TMFR 20-49 del campione di riferimento delle ricostituzioni inglesi, anni-persona 1575-1849; spec coniugale, tabella «Parametri per era») e `pre_industrial_islamic` (6,7, euristica regolabile che adotta lo stesso livello naturale, whitepaper §6.2). Per entrambe il template dichiara un livello naturale di una popolazione nelle sue condizioni ordinarie, ed è a quella dichiarazione che il riferimento si lega, qualunque ne sia l'origine.

**Fuori**, e nominato come tale:

- `industrial`: il suo `T_m` = 6,22 è un'euristica scelta per tenere il TFR₀ dell'era a 3,997 contro il vecchio `H = 4` (spec coniugale, riga di `industrial`; whitepaper §4.1.2, Tabella 4.3b), non un livello pubblicato; l'era è quella della transizione, in cui la risposta della fecondità al reddito è il fenomeno da rappresentare (Jones e Tertilt 2008, coorti USA 1826-1960). Il suo fattore resta identico a oggi; il suo livello realizzato resta `T_m·ρ_BK` e lo dichiaro nei limiti.
- Le ere con il blocco `hadwiger` (`modern_democracy`, `sci_fi`): fattore identico a oggi.
- I valori e i segni di β1..β4 nelle ere fuori perimetro (debito B2-07, FR-010).
- La correzione dell'economia (`spine2.n20`): prerequisito, non parte di questo work item.

Il discriminatore del perimetro non è la presenza del blocco `marital`, che vale anche per `industrial`: è un dato del template (FR-001).

## Fondamenti scientifici

Le fonti hanno lo stato di verifica del file di stadio 1 (`Diario/2026/11/2026-11-26/epocha-becker-riferimento/fonti-e-sistema.md`); nessuna è promossa qui.

1. **Una struttura moltiplicativa ha un riferimento.** In `b(a)·exp(β·x)` il calendario di base vale nello stato in cui il fattore è 1. Cox (1972), JRSS B 34(2), 187-202, doi:10.1111/j.2517-6161.1972.tb00899.x: VERIFICATO solo sul sommario depositato su Crossref. La prassi di riferire la base alla media delle covariate del campione invece che allo zero: documentazione del pacchetto R `survival`, `basehaz`, argomento `centered` (VERIFICATO sulla pagina; licenza non mostrata; solo l'idea).
2. **Il livello pubblicato è una media di popolazione e di lungo periodo.** Il TMFR 20-49 di Alter, Newton e Oeppen (2020) è una media sugli anni-persona 1575-1849 di molte famiglie, ricche e povere, anni buoni e cattivi compresi. Il gradiente di ricchezza misurato in una popolazione preindustriale sta attorno a quella media: Clark e Hamilton (2006), J. Econ. Hist. 66(3), 707-736, doi:10.1017/S0022050706000301, VERIFICATO sul working paper UC Davis n. 229 (testo letto da me, sezione VI, pp. 21-22): i testatori più ricchi lasciano circa il doppio dei figli **sopravvissuti**, e gli autori attribuiscono la differenza più alla sopravvivenza dei figli che alle nascite.
3. **Una risposta aggregata di breve periodo esisteva.** Bengtsson e Dribe (2006), Demography 43(4), 727-746, doi:10.1353/dem.2006.0030, VERIFICATO sul sommario: in una popolazione a fecondità naturale le famiglie senza terra rispondono in modo deliberato a variazioni di breve periodo dei prezzi del cibo; dimensioni non lette. Galloway (1988), Population Studies 42(2), 275-303: metadati VERIFICATI, testo NON letto; il numero «un raddoppio dei prezzi riduce la fecondità di meno del 15%» (p. 303) lo conosco solo tramite Clark e Hamilton, e misura le **nascite totali**, nuzialità compresa, non la fecondità coniugale. Lee (1981): NON VERIFICATO.
4. **β1..β4 non hanno appoggio sicuro nelle nascite coniugali preindustriali.** Becker (1960), NBER c2387, VERIFICATO solo a p. 231: il reddito alza la fecondità desiderata, e quella effettiva può restare sotto. Becker e Lewis (1973), JPE 81(2), S279-S288, VERIFICATO sulla ristampa NBER c2963: l'elasticità osservata della quantità può essere negativa con quella «vera» positiva. Jones e Tertilt (2008), doi:10.1016/S1574-0129(08)00005-7, VERIFICATO sul NBER WP 12796: elasticità al reddito occupazionale assoluto −0,38, negativa in ogni coorte USA 1826-1960, segno opposto a β1 = +0,1. Easterlin (1966): solo metadati; MacDonald e Rindfuss (1976) non trovano effetto del reddito relativo nei microdati. Becker (1991): NON VERIFICATO. Uno studio successivo sulla European Review of Economic History che attribuirebbe la fecondità dei ricchi all'età al matrimonio è stato visto dal revisore solo in risultati di ricerca: NON VERIFICATO.

Che cosa le fonti fondano e che cosa no. Le fonti 1-2 fondano un riferimento **di popolazione**: il fattore deve valere 1 in media sulla popolazione e sul periodo a cui il livello si riferisce. Non fondano il **passo temporale** del riferimento: il livello è una media di lungo periodo, e la fonte 3 dice che attorno a quella media le nascite oscillavano con le condizioni comuni. Un riferimento che si aggiorna a ogni tick toglie quelle oscillazioni ed è una scelta di modello che contraddice la fonte 3; un riferimento lento le conserva; azzerare i coefficienti nelle ere naturali le toglie tutte e toglie anche le differenze fra donne, che la fonte 4 non sostiene nelle nascite coniugali. La sezione «La scelta aperta» mette le tre strade a confronto.

### Licenze e attribuzione

Solo idee e numeri pubblicati, citati; nessun codice, testo o tabella copiati.

## Il modello

### Esponente (B1), invariato

```
η_i = β0 + β1·w_i + β2·e_i + β3·φ_z(i) + β4·ω_i                                         (B1)
w_i = ln(max(wealth_i / max(s_z(i), 1e-6), 0,1))
```

con `s_z` la soglia di sussistenza per tick della zona (`context.compute_subsistence_threshold`), `e_i` = `education_level`, `φ_z` la proxy di partecipazione femminile della zona, `ω_i` le prospettive aggregate (`context.compute_aggregate_outlook`). È la (4.3) del whitepaper, euristica ispirata a Becker (1991, NON VERIFICATO). Nessun valore cambia.

### Forma del fattore con un riferimento (B2)

Nelle ere del perimetro, se la strada scelta usa un riferimento:

```
m_BK,i = clip(exp(η_i − L), 0,05, 3,0)                                                   (B2)
```

dove `L` è il logaritmo del riferimento. Fuori dal perimetro, `L` non esiste e il fattore è `clip(exp(η_i), 0,05, 3,0)`, identico a oggi. Che cosa sia `L` dipende dalla strada (sezione «La scelta aperta»):

- **Strada A, riferimento per tick**: `L_t = ln( Σ_{j∈C_t} r_j·exp(η_j) / Σ_{j∈C_t} r_j )` (B2a), con `C_t` le candidate idonee del tick in tutta la simulazione (vive, in coppia attiva, senza `avoid_conception` attivo, tasso di base positivo) e `r_j` il loro tasso coniugale (N1); log-sum-exp per evitare overflow.
- **Strada B, riferimento lento**: `L` è una media mobile di `L_t` su una finestra di W anni, con stato persistente fra tick; W senza fonte verificata.
- **Strada C, coefficienti a zero**: nessun `L`; β0..β4 = 0 nei due template del perimetro, fattore 1 esatto.

### Proprietà della strada A (B3), con le loro condizioni

1. **Invarianza delle nascite attese.** Se nessun fattore del tick è tagliato dal clip, Σ_{i∈C_t} r_i·m_BK,i = Σ_{i∈C_t} r_i. Il soffitto malthusiano è comune a tutte le candidate del tick (`fertility.py:483-491`), quindi l'identità vale anche dopo il soffitto.
2. **Cancellazione dei termini comuni.** Si cancella ogni addendo uguale per tutte le candidate del tick: β0 e i due termini di prospettiva di simulazione (lineari, `context.py:118`). Un fattore moltiplicativo comune su tutte le ricchezze o su tutte le soglie si cancella **solo se** nessuna candidata del tick è alla guardia (W/s < 0,1, ricchezza nulla o negativa compresa) e tutte le soglie superano 1e-6: una candidata alla guardia non sposta il suo η quando le altre lo spostano.
3. **Differenze fra donne invariate.** Il rapporto fra i fattori di due candidate dello stesso tick è exp(η_i − η_j), come oggi, salvo clip.

La durata del tick non entra nella soglia nel codice: `SUBSISTENCE_NEED_PER_AGENT = 1,0` è per tick (`economy/market.py:46-50`) e nessun file di `economy/` legge la durata del tick. Se il fabbisogno per tick scalasse con la durata, la soglia si moltiplicherebbe per una costante comune e, sotto le condizioni di B3.2, la strada A ne cancellerebbe l'effetto; oggi è un esperimento mentale, non una proprietà del codice.

### Che cosa si perde, strada per strada

Nelle due ere del perimetro `fertility_agency` è `biological` (`templates/pre_industrial_*.json`), quindi `avoid_conception` non scatta (spec coniugale, (N1a)): Becker è l'unico canale economico della fecondità coniugale. Il whitepaper (§4.1.2, Background) dice invece che «the behavioural channel stays the Becker modulation and `avoid_conception`».

- **Strada A**: nessun canale economico **aggregato** resta. Le nascite attese del tick non rispondono alle condizioni comuni; resta la redistribuzione fra donne e fra zone. Il limite superiore della risposta persa, secondo l'unico numero disponibile, è meno del 15% delle nascite **totali** per un raddoppio dei prezzi (Galloway tramite Clark e Hamilton), nuzialità compresa. La calibrazione di B2-07 «con shock sintetici contro la baseline di Wrigley e Schofield (1981)» (whitepaper §4.1.2) non è più possibile nelle ere del perimetro, perché uno shock comune non muove le nascite; lo stesso vale per una validazione storica che misuri la risposta delle nascite ai salari reali.
- **Strada B**: conserva la risposta aggregata di breve periodo e corregge il livello di lungo periodo; perde la risposta di periodo più lungo della finestra. Costa stato persistente, una migrazione e una finestra senza fonte.
- **Strada C**: nessun canale economico, né aggregato né fra donne. Nessun codice nuovo; `ρ_BK` = 1 per costruzione.

## Parametri per era

Nessun valore di template cambia con le strade A e B. Con la strada C, β0..β4 diventano 0 nei due template del perimetro. I bound del clip, 0,05 e 3,0, restano euristiche di guardia (Appendice A.3 del whitepaper).

## La scelta aperta

### Le tre strade e il loro costo scientifico

| Strada | Livello di lungo periodo | Risposta aggregata di breve periodo | Differenze fra donne | Costo nel codice |
|---|---|---|---|---|
| A, riferimento per tick | `T_m` (salvo clip e secondo ordine fra età) | persa (contro la fonte 3) | conservate con β1..β4 non sostenuti (fonte 4) | tre funzioni, un argomento, un errore tipizzato, una chiave di template, guardia |
| B, riferimento lento | `T_m` in media sulla finestra | conservata entro la finestra | conservate | come A, più stato persistente, migrazione, finestra W senza fonte |
| C, coefficienti a zero | `T_m` esatto | persa | perse (coerente con la fonte 4) | solo dati: dieci numeri in due template |

### Confronto preregistrato

Lo eseguo solo dopo la correzione dell'economia (`spine2.n20`); prima non decide niente.

- **Run**: il mondo della configurazione B di SC-006 della spec coniugale (2.000 fondatori, 360 tick mensili, `max_population` 10⁶, economia `pre_industrial` con `initialize_economy`, coefficienti di seme), sul codice con l'economia corretta, con lo script di FR-006; un seme, dichiarato.
- **Numeri**, calcolati offline dai record della run con Becker come oggi:
  - D, dispersione fra donne: la mediana sui tick del rapporto fra il 90° e il 10° percentile di exp(η) fra le candidate del tick;
  - G, deriva aggregata: la differenza fra il massimo e il minimo, sulle tre finestre di 120 tick, della media pesata con r del fattore normalizzato con un riferimento fisso (la media del primo anno);
  - per ciascuna strada, `ρ_BK` su 360 tick e sulle tre finestre, ricalcolato applicando la strada ai record.
- **Criterio, in quest'ordine**:
  1. se D < 1,02, scelgo **C**: le differenze fra donne sono sotto il 2% e non giustificano codice nuovo;
  2. altrimenti, se G < 0,10, scelgo **B con finestra infinita**, cioè il riferimento fisso del primo anno: il livello non deriva e la risposta aggregata resta;
  3. altrimenti, scelgo **B** se a quel momento ho una fonte verificata per la finestra, **A** se non ce l'ho.
- 1,02 e 0,10 sono euristiche della Trinità, non grandezze demografiche; 0,10 è la stessa banda di D-MF-09.

Questo confronto non giudica β1..β4: misura soltanto se, con i coefficienti di oggi in un'economia sana, il loro effetto fra donne è rilevante e se il loro effetto aggregato deriva.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Il livello coniugale realizzato è quello pubblicato (Priority: P1)

Chi usa un'era del perimetro vuole che il TMFR realizzato fra 20 e 49 anni sia `T_m` nelle condizioni ordinarie della run.

**Independent Test**: SC-001 (strade A e B), SC-007.

**Acceptance Scenarios**:

1. **Given** (strada A) tre candidate idonee di `pre_industrial_christian` di 22, 30 e 41 anni lontane dalla guardia, con coefficienti di seme, **When** calcolo i loro fattori nello stesso tick, **Then** Σ r_i·m_i = Σ r_i entro 1e-12 in valore relativo.
2. **Given** la run di SC-007, **When** misuro `ρ_BK` su 360 tick e su tre finestre di 120 tick, **Then** ogni stima puntuale sta in [0,90, 1,10].

### User Story 2 - Le ere fuori perimetro non cambiano (Priority: P1)

**Independent Test**: SC-003.

**Acceptance Scenarios**:

1. **Given** agenti di `industrial`, `modern_democracy` e `sci_fi` con ingressi fissati, **When** calcolo il fattore prima e dopo il work item, **Then** i valori sono identici bit per bit.

### User Story 3 - Le differenze fra donne restano, se la strada le conserva (Priority: P2)

Vale solo per le strade A e B.

**Acceptance Scenarios**:

1. **Given** due candidate dello stesso tick lontane dalla guardia, con orizzonti in rapporto e e il resto uguale, **When** calcolo i fattori, **Then** il loro rapporto è exp(β1) entro 1e-12.

### User Story 4 - Un template incoerente è rifiutato (Priority: P2)

Vale per le strade A e B.

**Acceptance Scenarios**:

1. **Given** una copia di `pre_industrial_christian` con `beta_0 = 0.3`, **When** la carico, **Then** il caricatore solleva l'errore di validazione con il percorso `fertility.becker_coefficients.beta_0`.
2. **Given** `industrial` o `modern_democracy` con `beta_0 = 0.3`, **When** la carico, **Then** si carica.

### Edge Cases

Per le strade A e B:

- **Nessuna candidata idonea nel tick**: nessun fattore da calcolare; `L_t` non è calcolato.
- **Una sola candidata idonea**: fattore 1 (strada A).
- **Candidata alla guardia 0,1** (ricchezza nulla, negativa o sotto un decimo della soglia): il suo η non segue gli spostamenti comuni; B3.2 non vale per il tick.
- **Fattore tagliato dal clip**: B3.1 non vale esattamente per il tick; se una minoranza sta molto sopra la media, il clip a 3,0 ne taglia l'eccesso e la somma pesata scende sotto Σ r. Non ho un limite numerico; la misura riporta la quota di tagli.
- **Zone senza `ZoneEconomy`** (economia legacy, o zone miste): soglia 0, divisione per 1e-6, η più alto delle candidate delle altre zone di 0,1·ln(s/1e-6) a parità di ricchezza; nella strada A abbassa le altre. Il valore dipende dalla soglia delle zone con economia e non lo fisso qui.
- **Candidata con `zone` nullo**: `build_zone_fertility_context` con `zone=None` cade nel ramo senza `ZoneEconomy` (`context.py:80-83`, lettura del revisore che ho seguito nel codice) e la tratta come sopra.
- **Chiamata di `becker_modulation` senza riferimento**: forma di oggi, `L` = 0 (FR-003).
- **Chiamata di `tick_birth_probability` in un'era del perimetro senza riferimento**: errore tipizzato `BeckerReferenceMissing` (FR-004); mai il riferimento di oggi in silenzio.

## Requirements *(mandatory)*

I requisiti FR-001..FR-005 valgono per le strade A e B; con la strada C sono sostituiti da FR-002c.

### Functional Requirements

- **FR-001**: il blocco `fertility` di un template porta il discriminatore del perimetro come dato, `becker_reference`, con valore `"population"` nei due template preindustriali; la sua assenza significa il riferimento di oggi. Il caricatore lo valida (un solo valore ammesso, e solo in una sezione con il blocco `marital`). Nessuna funzione decide il perimetro dalla presenza di `marital` o dal nome del template.
- **FR-002**: `fertility.py` espone `becker_exponent(agent, coeffs, *, zone_context=None) -> float`, la somma (B1) senza clip; `becker_modulation` la usa, ed è l'unico punto che somma i termini. Espone anche `eligible_base_rate(mother, fertility_cfg, tick_duration_hours, demography_acceleration, *, current_tick, partnered_agent_ids)`, che applica nell'ordine di oggi il cancello della coppia, `avoid_conception`, l'età e il calendario di base e restituisce r(a) o 0,0; `tick_birth_probability` la usa al posto dei propri cancelli.
- **FR-002c** (solo strada C): β0..β4 = 0 nei due template del perimetro; nessun codice; FR-001 e FR-003..FR-005 non si applicano.
- **FR-003**: `becker_modulation(agent, coeffs, *, zone_context=None, log_reference: float | None = None)`. Con `log_reference=None` restituisce la forma di oggi; con un numero applica (B2). È l'unico canale del riferimento: `build_zone_fertility_context` non cambia e il `zone_context` resta un pacchetto di zona che cambia il costo e non il valore. Il fattore con il riferimento nasce dentro `becker_modulation`, così chi la avvolge (lo script di SC-006) registra il fattore applicato.
- **FR-004**: `tick_birth_probability(..., *, becker_log_reference: float | None = None)` passa il riferimento a `becker_modulation`. Se il template ha `becker_reference` (FR-001) e il riferimento manca, solleva `BeckerReferenceMissing`, sottoclasse di `ValueError`, prima di valutare Becker; fuori perimetro l'argomento è ignorato e non c'è percorso d'errore.
- **FR-005**: `orchestrator.run_fertility_step`, se il template ha `becker_reference`, prima del ciclo costruisce i contesti di zona per tutte le zone delle candidate (lo stesso insieme di zone che il ciclo costruirebbe), poi calcola il riferimento con `becker_log_reference(candidates, fertility_cfg, zone_contexts, ...)` di `fertility.py`, funzione pura sugli oggetti già caricati che usa `eligible_base_rate` e `becker_exponent`, non esegue query e non consuma numeri casuali, e lo passa a ogni chiamata di `tick_birth_probability`. Fuori perimetro il passo è identico a oggi. Il numero di query del passo resta quello di oggi.
- **FR-006**: lo script `scripts/measure_becker_terms.py` registra per ogni candidata e tick i cinque termini, η, la soglia, l'orizzonte, il fattore applicato e il tasso r(a), e verifica che il fattore ricalcolato sia uguale a quello restituito entro 1e-9. È lo strumento del confronto preregistrato: dà D, G e i `ρ_BK` per strada dai record, che SC-001 (un test unitario su dati costruiti) e FR-007 (solo `ρ_BK` della run) non danno. Riusa mondo e registratore di `scripts/measure_marital_schedule_run.py`.
- **FR-007**: lo script di SC-006 della spec coniugale riporta, oltre a `ρ_BK` su tutta la run, `ρ_BK` e il suo intervallo al 95% per tre finestre di 120 tick, e la quota di fattori tagliati dal clip; la condizione di fallimento si estende alle finestre.
- **FR-008**: docstring aggiornati di `becker_modulation`, `becker_exponent`, `becker_log_reference`, `eligible_base_rate`, `tick_birth_probability` e `run_fertility_step`: fonti, il significato del riferimento, le proprietà con le loro condizioni, che cosa si perde. Il docstring di `becker_modulation` smette di dire «Scale baseline ASFR» e «calibration deferred to Plan 4».
- **FR-009**: nello stesso commit del codice, in entrambe le lingue (`docs/whitepaper/epocha-whitepaper.md` e `.it.md`, sezioni omologhe), il §4.1.2 aggiorna:
  - il Background (EN :831, IT :875): la frase sul canale comportamentale («the behavioural channel stays the Becker modulation and `avoid_conception`») e quella sulla «economic ... modulation of completed fertility», che nelle ere del perimetro non valgono più come scritte;
  - il paragrafo dei ruoli dei coefficienti (EN :882, IT :926): «`β₀` = baseline (centred at the era's biological schedule)» è falso nel codice di oggi e va riscritto per era; «higher relative wealth» va riscritto come ricchezza relativa alla sussistenza fuori perimetro e, con le strade A e B, relativa alla popolazione nel perimetro;
  - la Tabella 4.4 e l'Appendice A.3 (β0 senza effetto e vincolato a 0 nel perimetro con A e B; coefficienti a zero con C);
  - le Semplificazioni (EN :898, IT :942): la calibrazione di B2-07 con shock sintetici contro Wrigley e Schofield, chiusa nel perimetro con A e C; il livello `T_m·ρ_BK`, che resta vero solo per `industrial`;
  - i Limiti noti (EN :2808-2846, IT :2757-2765) che citano `T_m·ρ_BK`, i casi 1,79 e 3,0 e B2-07;
  - i riferimenti di riga sbagliati del §4.1.2 (`fertility.py` «line 85», «line 118», «line 19», `fertility.py:204`, `:118-145`, `:70-82`);
  - la bibliografia: Cox (1972), Clark e Hamilton (2006), Bengtsson e Dribe (2006), Becker e Lewis (1973), con lo stato di verifica di questa spec.
- **FR-010**: il debito B2-07 è riformulato nel whitepaper e nella spec coniugale: coefficienti omogenei fra le ere; segno di β1 positivo contro −0,38 di Jones e Tertilt (che il docstring cita); gradiente preindustriale di Clark e Hamilton sui figli sopravvissuti e non sulle nascite; Becker (1960) sulla fecondità desiderata; Easterlin con verifica empirica negativa; nelle ere del perimetro, con A o C, nessuna calibrazione possibile con shock aggregati.
- **FR-011**: alla chiusura di questo work item il work item `20261029-185654-marital-fertility` riprende dal suo T051, configurazione B, con lo script di FR-007, e la sua spec registra il nuovo esito e, con A o C, che SC-006 B è diventato una verifica di coerenza (SC-007).
- **FR-012**: la build map (`docs/build-map/epocha-build-map.html`, italiano e inglese insieme) registra l'apertura di questo work item, la sua dipendenza da `spine2.n20` e, alla chiusura, il nuovo stato del §4.1.2, ripubblicata sullo stesso URL.

### Costo per tick, riepilogo

Strade A e B: zero query in più. Il pre-passaggio usa candidate già caricate con `fertility_state` selezionato (`orchestrator.py:349-358`) e il tick passato esplicitamente; i contesti di zona sono già costruiti oggi per tutte le zone delle candidate (`orchestrator.py:405-409`), quindi costruirli prima del ciclo non cambia il conteggio. Calcolo aggiuntivo: η, un esponenziale e una somma per candidata, e il cancello valutato due volte. La strada B aggiunge una lettura e una scrittura dello stato del riferimento per tick, non per candidata. La strada C non costa niente.

### Test che si muovono e perché

Ricavati dal codice (`grep tick_birth_probability(` sotto `epocha/apps/demography/tests/`).

- `test_fertility_zone_context.py:229-260` (`test_the_injected_context_reproduces_every_probability_exactly`), `:276-300` (costo zero query per candidata), `:352-390`: usano `pre_industrial_christian` con i coefficienti di seme. Con A o B devono passare `becker_log_reference`, lo stesso valore alle due chiamate del primo test, che così continua a provare che il contesto cambia il costo e non il valore. Con C i valori attesi restano, perché il fattore diventa 1 senza riferimento.
- `test_fertility.py:456-470` (helper con coefficienti azzerati) usato da `:473` (`pre_industrial_christian`): con A o B deve passare il riferimento, 0,0 perché con coefficienti zero `L_t` = ln(Σ r·1 / Σ r) = 0; il valore atteso non cambia. `:486` (`modern_democracy`) non cambia.
- `test_fertility.py:376`, `:405`, `:643` usano `_ERA_PARAMS_WITH_COUPLE_REQUIRED` (`:329`), un dizionario senza `becker_reference`: fuori perimetro, non cambiano.
- `test_fertility.py:199-272` chiamano `becker_modulation` direttamente senza riferimento: forma di oggi, non cambiano.
- `test_subsistence_horizon.py:137-149` chiamano `becker_modulation` senza riferimento: non cambiano.
- `test_marital_schedule_run_harness.py:51-60` chiama `tick_birth_probability` con `run_script.TEMPLATE_NAME` (`pre_industrial_christian`): con A o B deve passare il riferimento.
- `test_integration_plan2.py` usa `modern_democracy` (righe 82 e 181): fuori perimetro, non cambia.
- `test_demography_cost.py` e il test di costo di `test_fertility_zone_context.py`: conteggi invariati (SC-004).
- `scripts/measure_marital_schedule_run.py:187-188` (azzeramento per la configurazione A): invariato.

### Key Entities

Strade A e C: nessun modello nuovo e nessuna migrazione. Strada B: uno stato persistente del riferimento per simulazione, da progettare se il confronto la sceglie.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001 (strada A, invarianza)**: test unitario su candidate di `pre_industrial_christian` lontane dalla guardia e senza clip: |Σ r_i·m_i − Σ r_i| / Σ r_i < 1e-12. Fallisce altrimenti. Prova di guardia: con la normalizzazione disattivata (mutazione nominata, poi annullata) il test fallisce.
- **SC-002 (strade A e B, termini comuni e differenze)**: (a) con candidate lontane dalla guardia, moltiplicare per 7 tutte le ricchezze lascia ogni fattore uguale entro 1e-12, e un caso con una candidata alla guardia mostra che l'uguaglianza non vale (la condizione di B3.2 è provata, non solo scritta); (b) cambiare β0 su un dizionario di coefficienti passato direttamente lascia ogni fattore uguale entro 1e-12; (c) il rapporto fra due candidate con orizzonti in rapporto e vale exp(β1) entro 1e-12. Fallisce se uno dei tre non vale.
- **SC-003 (fuori perimetro fermo)**: per un insieme fissato di ingressi di `industrial`, `modern_democracy` e `sci_fi`, fattore e probabilità uguali bit per bit ai valori con il codice di oggi. Fallisce a qualunque differenza.
- **SC-004 (costo)**: i test di costo del passo di fecondità passano con i conteggi di oggi. Fallisce se un conteggio cambia.
- **SC-005 (caricatore)**: gli scenari della User Story 4, un template con `becker_reference` senza `marital` rifiutato, un valore diverso da `"population"` rifiutato, i cinque template caricati. Fallisce se uno dà l'esito opposto.
- **SC-006 (confronto preregistrato)**: eseguito dopo `spine2.n20` con lo script di FR-006, riporta D, G e i `ρ_BK` per strada, e applica il criterio della sezione «La scelta aperta». Fallisce se il ricalcolo del fattore differisce dal fattore restituito oltre 1e-9 in una chiamata; l'esito del criterio è una decisione, registrata come D-BK con le due posizioni.
- **SC-007 (livello realizzato, 360 tick)**: la configurazione B di SC-006 della spec coniugale, rifatta dopo `spine2.n20` con lo script di FR-007: la stima puntuale di `ρ_BK` su tutta la run e su ciascuna finestra di 120 tick sta in [0,90, 1,10]. Fallisce se una delle quattro esce. Con le strade A e C è una **verifica di coerenza** dell'implementazione, non una validazione del modello: `ρ_BK` si scosta da 1 solo per clip e per il secondo ordine fra pesi per età (ricalcolo offline del revisore sui record del mondo degenere: 1,00009 con la strada A). Con la strada B è una misura vera.

## Assumptions

- Il livello `T_m` delle due ere del perimetro descrive la popolazione nelle sue condizioni ordinarie, mediate sul lungo periodo; la popolazione delle candidate idonee della simulazione è il suo analogo.
- La popolazione di riferimento delle strade A e B è quella della simulazione intera, non della zona: `T_m` è un livello di popolazione e un riferimento di zona cancellerebbe le differenze economiche fra zone.
- Le donne fuori coppia non entrano nel riferimento: nelle ere del perimetro il loro tasso è zero.
- Il clip resta dopo la normalizzazione.
- La scelta fra le strade **dipende** dall'economia: dalla dispersione fra donne (D) e dalla deriva (G) in una run con l'economia corretta. Nessun numero misurato fino a oggi la decide.

## Dipendenze

- **`spine2.n20`, correzione dell'economia** (voce di build map indicata dalla coordinazione, nessun branch ancora; non presente nella build map di questo branch): prerequisito di SC-006 e SC-007, quindi della scelta e della chiusura. La diagnosi del 2026-11-26 indica tre difetti: il ciclo di prezzo a quantità fisse (`economy/market.py:105-166`), la produzione dei neonati per ripiego (`economy/production.py:186-190`), e l'effetto della guardia di solvibilità che lascia spendere tutto il contante (`economy/engine.py:414-419` al commit di prova `dfbff71`, guardia MKT-7, decisione ratificata).
- **Work item coniugale**: aspetta questo (FR-011).

## Numeri da un mondo degenere

Restano per quello che sono: misure corrette di un'economia degenere (pavimento dei prezzi dal tick 2, crollo della ricchezza ai tick 3-5), mai argomenti per la scelta.

- `ρ_BK` = 1,6162, intervallo [1,5657, 1,6668], decili del fattore 1,399-1,816 (T051, 360 tick).
- Fattore medio 1,4535 su 72 tick, da 1,392 a 1,582; termine di ricchezza da +0,356 a +0,441, di prospettiva da +0,070 a +0,143 (`misura-termini.md`).
- Ipotesi offline sui record: 0,9865 con la ricchezza centrata sulla mediana del tick, 0,9996 con tutti gli ingressi centrati; strada A ricalcolata dal revisore: invarianza a 1,75e-15, `ρ_BK` 1,00009, fattore normalizzato fra 0,981 e 1,006 dopo il tick 12.

## Rinvii espliciti (cosa NON fa questa versione)

1. La scelta fra A, B e C, fino al confronto preregistrato.
2. β1..β4 fuori perimetro e il loro segno: debito B2-07 (FR-010).
3. `industrial`: livello realizzato `T_m·ρ_BK`, fattore di oggi; un riferimento per la transizione richiede una fonte per il livello coniugale dell'era (la spec coniugale indica le serie Ig di Woods 2000, non lette).
4. Ere Hadwiger: riferimento di oggi.
5. La correzione dell'economia (`spine2.n20`).

## Known Limitations

- Con A e C nessun canale economico aggregato resta nella fecondità coniugale delle ere del perimetro; con C nemmeno quello fra donne.
- Con A l'invarianza fissa le nascite del tick, non la media del fattore per gruppo d'età.
- Con A e B una candidata può ancora avere fattore 3,0, tre volte il riferimento: a 20-24 anni con `T_m` 6,7 un tasso di 1,03 nascite per anno.
- Zone senza `ZoneEconomy` o `zone` nullo distorcono il riferimento delle strade A e B (Edge Cases).
- `industrial` resta con il livello realizzato `T_m·ρ_BK`.
- Un seme solo nel confronto e in SC-007.

## Architettura e collocazione

Tutto resta in `epocha/apps/demography`: le funzioni in `fertility.py`, proprietario del fattore; il pre-passaggio in `orchestrator.run_fertility_step`, che possiede i candidati e i contesti; la validazione in `template_loader.py`. Il riferimento è un argomento esplicito, non una chiave del pacchetto di zona, perché è un numero di simulazione e il pacchetto resta di zona (`fertility.py:243-260`). Nessuna dipendenza nuova.

## Registro del design

Le fasi complete sono nel diario (`Diario/2026/11/2026-11-26/epocha-becker-riferimento/disegno-tre-passi.md`).

### Passo 1 — Proposta iniziale

Covariate centrate sulle medie di zona a ogni tick, con una query aggregata per zona.

### Passo 2 — Primo self-review critico (Matteo)

Uccisi: la query aggregata (insieme diverso da quello a cui il fattore si applica), il centramento delle covariate (scarto di Jensen, scelta di forma), il riferimento di zona (cancella le differenze fra zone). Aggiunti: β0 inerte con una guardia, pesi per tasso, ordine clip-normalizzazione.

### Passo 3 — Secondo self-review e consolidamento

Un solo cancello di idoneità (`eligible_base_rate`), `becker_exponent` separato perché lo script registri il fattore applicato, riferimento lento rinviato, regola unica per tutte le ere scartata.

### Round 1 dell'audit

Ha ucciso: `industrial` nel perimetro (R1-01); l'interfaccia a due canali e il pacchetto di zona come veicolo (R1-02); la difesa del riferimento per tick, che poggiava sulla convenienza e sull'economia degenere (R1-04, R1-05); lo scarto senza numeri della strada C (R1-06); la proprietà B3.2 senza condizioni e la frase sulla durata del tick (R1-07). Insieme alla diagnosi dell'economia ha trasformato la scelta in un confronto preregistrato. Registro in `checklists/audit.md`.

### Cronaca

- 2026-11-26: T051 della spec coniugale fallisce in configurazione B; l'utente sceglie la strada (a) di D-MF-09; stadio 1 (sistema e fonti); scomposizione dei termini su 72 tick; disegno in tre passi e prima versione della spec (`7277619`); audit round 1 NOT CONVERGED; diagnosi dell'economia del mondo di prova; decisione D-26-E-9 della coordinazione; questa revisione.

## Alternative considerate

- **Centrare le covariate**: media 1 solo a meno dello scarto di Jensen, e quattro scelte di forma; la forma (B2) dà il riferimento con un numero.
- **Riferimento di zona**: cancella le differenze fra zone.
- **Media non pesata**: non fissa le nascite attese del tick.
- **Strada (b) di D-MF-09**, dichiarare `ρ_BK`: scartata dall'utente.
- **Regola unica per tutte le ere**: sposterebbe `industrial` e le ere Hadwiger e toglierebbe la risposta al reddito proprio nell'era della transizione.
- **Discriminare con la presenza di `marital`**: include `industrial` senza fonte (R1-01).

## Decisioni provvisorie della Trinità

- **D-BK-01, forma del fattore con riferimento.** Normalizzare il moltiplicatore (B2) invece di centrare le covariate: media esatta con un numero. Vale per A e B. Provvisoria.
- **D-BK-02, quale strada.** **Aperta**: A, B o C si decide con il confronto preregistrato dopo `spine2.n20` (D-26-E-9).
- **D-BK-03, β0 nel perimetro con A e B.** Il caricatore richiede 0: un parametro senza effetto è una trappola. Provvisoria.
- **D-BK-04, perimetro.** Le due ere preindustriali, discriminate da un dato del template; `industrial` e le ere Hadwiger fuori. Provvisoria.
- **D-BK-05, canale del riferimento.** Un argomento esplicito di `becker_modulation` e di `tick_birth_probability`; errore tipizzato solo in `tick_birth_probability` e solo nel perimetro. Provvisoria.

## FAQ

**Perché solo le due ere preindustriali e non `industrial`?** Perché il riferimento di popolazione si giustifica con un livello naturale pubblicato di una popolazione nelle sue condizioni ordinarie. Il `T_m` di `industrial` è un'euristica scelta per tenere il TFR₀ a 3,997, e la sua era è la transizione, in cui la risposta della fecondità al reddito (Jones e Tertilt: −0,38) è il fenomeno; normalizzarla lo cancellerebbe.

**Perché `pre_industrial_islamic`, il cui 6,7 non è pubblicato per quella popolazione?** Perché il template adotta lo stesso livello naturale dell'era cristiana come euristica dichiarata (whitepaper §6.2): il riferimento si lega a ciò che il livello significa, non alla sua origine. Se un giorno l'era avrà un livello suo, il riferimento resta valido.

**Perché un dato del template e non la presenza di `marital`?** Perché `marital` dice che le nascite richiedono una coppia, non che il livello sia naturale; `industrial` ha `marital` e un livello euristico.

**Perché non si sceglie adesso?** Perché le tre strade differiscono per quanto conta la dispersione fra donne e per quanto deriva l'aggregato, e tutte e due le grandezze, nei dati che ho, sono prodotte da un'economia con i prezzi al pavimento e un crollo della ricchezza. Un criterio scritto prima della misura impedisce di scegliere la strada e poi trovarle una ragione.

**Perché la strada C è un'opzione seria?** Perché è la più piccola (solo dati), dà `T_m` esatto, e le fonti non sostengono un gradiente di ricchezza delle nascite coniugali preindustriali: Clark e Hamilton lo attribuiscono più alla sopravvivenza dei figli. Perde ogni canale economico nella fecondità coniugale di quelle ere, ed è questo che il confronto pesa.

**Che cosa perde la strada A, in numeri?** La risposta delle nascite alle condizioni comuni. L'unico numero che ho è un limite superiore di seconda mano: meno del 15% delle nascite totali, nuzialità compresa, per un raddoppio dei prezzi (Galloway 1988, p. 303, tramite Clark e Hamilton).

**Come arriva il riferimento a `becker_modulation`?** Come argomento esplicito `log_reference`, passato da `tick_birth_probability`, che lo riceve dall'orchestratore. Senza argomento la funzione fa ciò che fa oggi, quindi le ere fuori perimetro non hanno nessun percorso d'errore; nel perimetro un riferimento mancante è un errore tipizzato in `tick_birth_probability`.

**Il pacchetto di zona cambia?** No. Resta un pacchetto di zona che cambia il costo e non il valore; il test che lo prova continua a valere passando lo stesso riferimento alle due chiamate.

**Come si integra con il soffitto malthusiano e con `avoid_conception`?** Il soffitto moltiplica dopo il fattore ed è comune a tutte le candidate del tick, quindi l'invarianza della strada A vale anche dopo. `avoid_conception` è un cancello di `eligible_base_rate`: chi lo ha attivo non entra nel riferimento; nelle ere del perimetro non scatta.

**E con lo script di SC-006?** Il fattore con il riferimento nasce dentro `becker_modulation`, che lo script avvolge; il pre-passaggio usa `becker_exponent`, che lo script non conta.

**Quanto costa?** Strade A e B: zero query in più per candidata (B una lettura e una scrittura per tick); strada C nulla.

**È deterministico?** Sì: la somma del riferimento segue l'ordine per id dei candidati (`orchestrator.py:357`) e il pre-passaggio non consuma numeri casuali. Con lo stesso seme la run si ripete.

**Che cosa succede con la durata del tick?** Nel codice la durata non entra nella soglia di sussistenza. Se un giorno ci entrasse come fattore comune, la strada A la cancellerebbe, alle condizioni di B3.2.

**Confronto con librerie esistenti?** Nessuna libreria usata da Epocha fornisce questa normalizzazione; è un'operazione su dati già in memoria.

**Sicurezza e privacy?** Nessuna superficie nuova: nessun ingresso esterno, nessuna API, nessun dato personale; il caricatore guadagna una validazione.

**Quali sono i modi di guasto?** Un template con `becker_reference` e β0 ≠ 0, o con un valore non ammesso, fallisce al caricamento; un riferimento mancante nel perimetro solleva `BeckerReferenceMissing`; zone senza economia distorcono il riferimento senza errore (limite noto).

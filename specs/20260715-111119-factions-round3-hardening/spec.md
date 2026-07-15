# Feature Specification: Factions Round 3 hardening

**Feature Branch**: `20260715-111119-factions-round3-hardening`

**Created**: 2026-07-15

**Status**: Draft

**Input**: chiusura dei 5 finding behavioral deferred a valle del Round 2 factions (2026-05-16): NEW-1, NEW-7, NEW-8, NEW-10, NEW-12/13. Dossier di investigazione verificato: memoria `project_factions_round3_dossier` (2026-07-15).

## Contesto e problema

Il modulo `epocha/apps/agents/factions.py` (997 righe, entry point `process_faction_dynamics` invocato da `simulation/engine.py:490`) è CONVERGED al Round 2 e promosso a §4.7 del whitepaper, ma con 5 finding behavioral esplicitamente deferred, catalogati nel Known Limitations del modulo e nel bullet "Deferred behavioral hardening" di §4.7. La verifica sul codice corrente (2026-07-15) conferma che tutti e 5 sono ancora presenti:

1. **NEW-1** — `_check_join_existing_groups` (`factions.py:753`): campione di 5 membri da queryset NON ordinato (`Agent` non ha `Meta.ordering`): su PostgreSQL l'ordine dello slice `[:5]` è implementation-defined, quindi il campione è sia non rappresentativo sia potenzialmente instabile tra esecuzioni. (La caratterizzazione "primi 5 per PK, stabile" dell'audit originale era imprecisa: il difetto è più grave di quanto catalogato.)
2. **NEW-7** — `_check_schism` (mutazioni righe 603-644) e `_create_faction` (889-930): scritture multi-tabella (Group, Agent, Memory) senza `transaction.atomic`; un fallimento a metà lascia stato incoerente (analogo a reputation N-11).
3. **NEW-8** — disciplina di migrazione incoerente: `_check_dissolution:515` usa `Agent.objects.filter(group=group).update(group=None)` (bulk) mentre `_check_schism:618`, `_create_faction:908`, `_process_formation_decisions:827` usano `agent.save(update_fields=["group"])` per-agente.
4. **NEW-10** — docstring di `_check_join_existing_groups` (735-744) dice "average affinity with the first 5 group members": "first" non corrisponde ad alcun ordinamento definito (vedi NEW-1), quindi la docstring descrive un comportamento che il codice non garantisce.
5. **NEW-12/13** — N+1: `compute_affinity` (`affinity.py:62`) fa ~3 query per coppia (1 `Relationship` in `_relationship_score`, 4 nel caso `MultipleObjectsReturned`, + 2 `Memory` in `_circumstance_score` con filtri `source_type=PUBLIC`, `is_active=True`, `tick_created__gte=tick-10`) ed è chiamata in loop annidati in `_check_join_existing_groups:756` (più la query `has_positive_rel` per coppia agente-gruppo, il fetch membri RIPETUTO per ogni agente ungrouped, la exists di dedup `already_suggested` per agente qualificato e la `Memory.create` per suggerimento) e in `_detect_and_propose_factions:700`; `compute_legitimacy:310` chiama `compute_leadership_score` per membro e `compute_leadership_score:209` ri-fetcha TUTTI i membri a ogni chiamata (N+1 su Agent, più Relationship e Memory per membro). Stima verificata con 50 ungrouped × 5 gruppi: ~3750 query/tick di sole chiamate `compute_affinity` (1250 coppie × 3), più ~250 refetch membri e ~250 exists → totale worst case ≈ 4250 nel solo join-check (la stima originale dell'audit, 1250, contava le computazioni, non le query).

Fatti architetturali verificati che vincolano il design:

- `factions.py` NON usa alcun RNG, ma il determinismo attuale NON è comunque garantito: due sorgenti di nondeterminismo verificate sono (a) gli slice/iterazioni su queryset non ordinati (`Agent` e `Group` non hanno `Meta.ordering`; Postgres non garantisce l'ordine senza `ORDER BY`; fa eccezione `_detect_and_propose_factions:679` che ordina già per `name` — ma `Agent.name` non è unique, quindi le collisioni di nome restano nondeterministiche) e (b) il tie-break di `_relationship_score` (`affinity.py:166-174`): su `MultipleObjectsReturned` sceglie `.order_by("-strength").first()`, e con `strength` a pari valore (default 0.5, caso comune per coppie con più `relation_type` o entrambe le direzioni) la riga scelta è arbitraria → `sentiment` diverso → score diverso tra esecuzioni. L'engine NON seeda il modulo `random` globale; l'unico RNG seedato per-fase è `epocha/apps/demography/rng.py:get_seeded_rng` con set chiuso di fasi demografiche.
- Su `Agent` non esistono né segnali Django né override di `save()` (verificato repo-wide); `Agent.group` è FK nullable con `on_delete=SET_NULL`, `related_name="members"`. La differenza bulk-update vs save() per-agente è quindi SOLO di numero di query, non di comportamento.
- `pytest-django>=4.9` è in `requirements/local.txt`: la fixture `django_assert_num_queries` è disponibile. Nel repo non esiste ancora alcun test con assertion sul numero di query: questo branch introduce il precedente.
- `Relationship` ha `unique_together (agent_from, agent_to, relation_type)` e semantica bidirezionale gestita con Q-objects; `_circumstance_score` legge `Memory` con `source_type=PUBLIC`, `is_active=True` e `tick_created__gte=tick-10` per entrambi gli agenti della coppia.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Suggerimenti di adesione non distorti e a costo costante (Priority: P1)

Un operatore che esegue una simulazione con gruppi longevi e molti agenti liberi deve ottenere suggerimenti di adesione basati sull'affinità con il gruppo REALE (tutti i membri vivi), non con un campione di 5 estratto da un queryset non ordinato (ordine implementation-defined), e senza esplosione di query al crescere della popolazione.

**Why this priority**: NEW-1/10/12 insieme sono il cluster più impattante — distorcono il comportamento sociale emergente (bias di campionamento) e dominano il costo per tick (~3750 query). La stessa rifattorizzazione li chiude tutti e tre.

**Independent Test**: test unitari su `_check_join_existing_groups`: (a) equivalenza numerica dell'affinità con e senza dati prefetched; (b) media calcolata su tutti i membri vivi; (c) budget di query per tick costante rispetto al numero di coppie (assertion `django_assert_num_queries`).

**Acceptance Scenarios**:

1. **Given** un gruppo con 10 membri vivi di affinità eterogenea, **When** gira il join-check per un agente libero, **Then** la media di affinità è calcolata su tutti e 10 i membri (non su un campione di 5 a ordine non definito) e il risultato numerico per ciascuna coppia è identico a quello di `compute_affinity` chiamata singolarmente.
2. **Given** 20 agenti liberi e 4 gruppi attivi, **When** gira `_check_join_existing_groups`, **Then** il numero di query è limitato e indipendente dal numero di coppie (fetch membri una volta per gruppo per tick, relationship e memorie prefetched in query aggregate), verificato con `django_assert_num_queries`.
3. **Given** la docstring della funzione, **When** letta, **Then** descrive esattamente il comportamento implementato (media su tutti i membri vivi, dati prefetched, nessun campione).

### User Story 2 - Mutazioni di gruppo atomiche e disciplina di migrazione unificata (Priority: P1)

Un operatore la cui simulazione subisce un errore a metà di uno schism o di una creazione di fazione deve ritrovare il database nello stato precedente alla mutazione (rollback completo), e ogni percorso che sposta agenti tra gruppi deve usare la stessa disciplina di scrittura documentata.

**Why this priority**: NEW-7 è High severity (integrità dati); NEW-8 è la sua faccia di coerenza di policy. Insieme definiscono il contratto di scrittura del modulo.

**Independent Test**: test di rollback (eccezione simulata a metà mutazione → nessuna riga scritta) e test di policy (dopo dissoluzione/schism/creazione, lo stato `group` di tutti gli agenti coinvolti è coerente).

**Acceptance Scenarios**:

1. **Given** uno schism in corso, **When** un'eccezione viene sollevata dopo la creazione del gruppo splinter ma prima dell'aggiornamento degli alleati (simulata nel test), **Then** nessun gruppo splinter esiste nel database e nessun agente ha cambiato gruppo.
2. **Given** una creazione di fazione in corso, **When** un'eccezione interrompe la mutazione (simulata), **Then** nessun Group, nessun cambio di `Agent.group` e nessuna Memory della mutazione persistono.
3. **Given** i quattro percorsi di mutazione della membership (dissoluzione, schism, creazione, formation decisions), **When** ispezionati, **Then** tutti spostano gli agenti con la stessa disciplina (bulk `update()` su queryset) dentro un blocco atomico, e la policy è documentata nel docstring di modulo con il suo presupposto verificato (nessun segnale né `save()` override su `Agent`).

### User Story 3 - Leadership senza N+1 (Priority: P2)

La valutazione di legittimità e successione della leadership non deve rifetchare i membri del gruppo per ogni membro né fare query Relationship/Memory per membro.

**Why this priority**: NEW-13 — costo per gruppo per tick; meno critico del cluster US1 perché il numero di gruppi è piccolo, ma stessa classe di difetto.

**Independent Test**: test su `compute_legitimacy`/`update_group_leadership` con `django_assert_num_queries`: budget costante rispetto al numero di membri.

**Acceptance Scenarios**:

1. **Given** un gruppo con N membri, **When** `compute_legitimacy` valuta il leader, **Then** i membri sono fetchati una sola volta e passati a `compute_leadership_score`, che non esegue il proprio fetch quando li riceve.
2. **Given** lo stesso gruppo, **When** i punteggi di leadership sono calcolati per la successione, **Then** i valori numerici sono identici a quelli della versione precedente (equivalenza testata) con budget di query costante.

### User Story 4 - Documentazione sincronizzata (Priority: P3)

Chi legge il whitepaper §4.7 e il Known Limitations del modulo deve trovare lo stato aggiornato: il debito "Deferred behavioral hardening" risolto e rimosso, senza modifiche alle equazioni (4.38)-(4.41).

**Why this priority**: factions è modulo capitolo 4 — la regola doc-sync della constitution impone l'aggiornamento nello stesso branch. Solo documentale.

**Acceptance Scenarios**:

1. **Given** whitepaper §4.7 (EN e IT), **When** il branch è chiuso, **Then** il bullet Known Limitations "Deferred behavioral hardening" è rimosso o riscritto come risolto (con data), le equazioni e i paragrafi Algorithm restano intatti salvo dove descrivono i dettagli implementativi cambiati, e EN/IT sono speculari.
2. **Given** il docstring Known Limitations di `factions.py`, **When** letto, **Then** il bullet (f) dei deferred è aggiornato allo stato risolto e la policy di scrittura membership è documentata.

### Edge Cases

- Gruppo senza membri vivi durante il join-check: salta il gruppo (comportamento attuale preservato).
- Gruppi molto grandi: la media su tutti i membri sposta il costo da query a CPU (similarità di personalità in-memory); il costo per coppia senza query è trascurabile alla scala corrente (≤ centinaia di membri). Nessun cap reintrodotto; se una scala futura lo richiedesse, andrà reintrodotto come campione DETERMINISTICO documentato, non come default silenzioso.
- `transaction.atomic` e il loop di tick: `process_faction_dynamics` gira dentro il task Celery del tick; i blocchi atomici sono per-mutazione (per gruppo/fazione), non per l'intera fase, per non allargare la finestra di lock.
- Cambio comportamentale dichiarato: la media su tutti i membri (vs campione di 5 a ordine implementation-defined) può cambiare quali suggerimenti di adesione vengono generati in simulazioni esistenti. È il comportamento INTESO dalla docstring originale e corregge il bias; i test di regressione fissano il nuovo contratto.
- Equivalenza numerica: il batching non deve cambiare alcun valore di affinità o di leadership score — solo il modo in cui i dati arrivano alle formule. Test di equivalenza obbligatori.
- Determinismo: nessun RNG introdotto; gli ordinamenti espliciti (`order_by("id")` su tutte le iterazioni delle funzioni toccate) e il tie-break deterministico di FR-011 eliminano ENTRAMBE le sorgenti di nondeterminismo verificate (slice non ordinato e pareggi di strength). Il test di determinismo di FR-007 è verificabile solo a valle di entrambi.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001** (NEW-12 infra): `epocha/apps/agents/affinity.py` DEVE esporre un meccanismo di prefetch per il calcolo di affinità su insiemi di coppie: una struttura di contesto costruita con query aggregate (una per le `Relationship` di tutte le coppie coinvolte, una/due per le `Memory` con `source_type=PUBLIC`, `is_active=True`, `tick_created__gte=tick-10` di tutti gli agenti coinvolti). Meccanismo DRY obbligato: i due helper DB-coupled (`_relationship_score`, `_circumstance_score`) vengono estesi con un parametro opzionale di dati prefetched (iniezione dati) e restano l'unica sede della logica di scoring — NESSUNA funzione gemella che riscriva le formule. I content-set delle memorie per agente vengono costruiti UNA volta per agente nel contesto (memoizzazione), non per coppia. Senza contesto, il comportamento resta quello attuale. I valori calcolati DEVONO essere numericamente identici al percorso non-batched a parità di tie-break (FR-011).
- **FR-002** (NEW-1 + NEW-10 + NEW-12 join): `_check_join_existing_groups` DEVE (a) fetchare i membri vivi di ciascun gruppo UNA volta per tick (fuori dal loop sugli agenti liberi), (b) calcolare la media di affinità su TUTTI i membri vivi del gruppo usando il contesto prefetched, (c) risolvere `has_positive_rel` dai dati prefetched senza query per coppia, (d) risolvere la dedup `already_suggested` (`factions.py:762`) con UNA query aggregata per tick che carica TUTTE le memorie recenti (finestra `tick_created >= tick-5`, QUALSIASI contenuto, nessun pre-filtro di tipo) degli agenti liberi, replicando in-memory l'esatta semantica corrente `content__contains=group.name` come substring case-sensitive per coppia (agente, gruppo) — il filtro attuale matcha qualsiasi memoria contenente il nome del gruppo (adesioni, dissoluzioni, schism, broadcast), non solo i suggerimenti, e questa semantica broad va preservata identica, incluso il quirk preesistente dei nomi di gruppo che si contengono l'un l'altro, (e) creare le memorie di suggerimento con `bulk_create` invece di una `create` per suggerimento, (f) avere docstring allineata al comportamento reale. Il cap di 5 membri e lo slice non ordinato sono rimossi.
- **FR-003** (NEW-12 detect): `_detect_and_propose_factions` DEVE usare lo stesso contesto prefetched per il loop di clustering (`factions.py:700`), senza query per coppia.
- **FR-004** (NEW-13): `compute_leadership_score` DEVE accettare un parametro opzionale con i membri del gruppo già fetchati (default: fetch autonomo, comportamento attuale) e dati relazionali prefetched; `compute_legitimacy` e `update_group_leadership`/`_elect_new_leader` DEVONO passare i membri fetchati una sola volta. Budget di query per gruppo costante rispetto al numero di membri. Valori numerici invariati (equivalenza testata).
- **FR-005** (NEW-7): le quattro vie di mutazione multi-riga DEVONO eseguire le loro scritture dentro `transaction.atomic` con unità di atomicità definite così: `_check_schism` per-schism (blocco creazione splinter + migrazione alleati + memorie), `_create_faction` per-fazione (l'intera funzione), `_check_dissolution` per-dissoluzione, `_process_formation_decisions` per-decisione per il ramo join (`factions.py:820-836`) — dove una decisione è un singolo agente che aderisce: l'atomic copre lo spostamento di `group` di QUEL agente, la sua `Memory` di adesione (`factions.py:828-834`) e il decremento di cohesion del gruppo target (`factions.py:835`), e la disciplina FR-006 vi si applica come queryset `update()` che in questo ramo tocca una riga sola (coerenza di disciplina, non di cardinalità) — mentre il ramo form si affida all'atomic interno di `_create_faction` (chiamata a `factions.py:863`) senza wrap esterno; nessun atomic annidato intenzionale; se un wrap esterno emergesse in fase di piano, l'annidamento (savepoint) va dichiarato. Un'eccezione a metà mutazione non lascia righe parziali.
- **FR-006** (NEW-8): la disciplina di migrazione DEVE essere unificata su bulk `update()` di queryset per lo spostamento di `Agent.group` in tutti e quattro i percorsi, con la policy e il suo presupposto (nessun segnale né `save()` override su `Agent`, verificato 2026-07-15) documentati nel docstring di modulo. Se in futuro verranno aggiunti segnali su `Agent.group`, la policy va rivista (nota esplicita nel docstring).
- **FR-007** (test, test-first): ogni fix behavioral DEVE avere regression test scritti RED-first dove il rosso è osservabile (equivalenza numerica batched/non-batched; media su tutti i membri; rollback atomico con eccezione iniettata; coerenza membership post-mutazione; budget di query con `django_assert_num_queries` — primo uso nel repo; determinismo: due esecuzioni identiche producono gli stessi suggerimenti). I test esistenti non vengono indeboliti.
- **FR-008** (whitepaper doc-sync): §4.7 EN e IT DEVONO essere aggiornati nello stesso branch. Superficie verificata: l'UNICA prosa di §4.7 che descrive i difetti è il bullet Known Limitations "Deferred behavioral hardening" (EN riga ~1877, IT riga ~1944); il paragrafo Algorithm non menziona campioni né query e non va toccato. Il bullet viene riscritto come risolto (con data e riferimento al branch); nessuna equazione (4.38)-(4.41) cambia. Il docstring Known Limitations di `factions.py` DEVE riflettere lo stato risolto e correggere la caratterizzazione del campione (queryset non ordinato, non "PK-stabile").
- **FR-009** (gate): suite pytest completa verde (baseline 810 + nuovi test), `ruff check .` e `ruff format --check .` exit 0 (container authority), zero xfail, zero skip nuovi senza rationale.
- **FR-010** (tracking): memoria di sessione e session resume aggiornate a chiusura; frozen-at-commit pin aggiornato al merge SHA (whitepaper toccato, procedura fase 7).
- **FR-011** (determinismo, estensione di scope dichiarata): il tie-break di `_relationship_score` DEVE diventare deterministico — `order_by("-strength", "id")` nel percorso query e stessa chiave `(-strength, id)` nella selezione dal contesto prefetched — e le iterazioni delle funzioni toccate DEVONO usare ordinamenti espliciti e STABILI che preservano l'ordine esistente dove già definito: `order_by("id")` su agenti liberi, gruppi e membri (oggi non ordinati); `order_by("name", "id")` sui seed di `_detect_and_propose_factions`, che oggi ordina già per `name` (`factions.py:679`) — si aggiunge SOLO il tiebreak `id` per le collisioni di nome (`Agent.name` non è unique), senza cambiare l'ordine dei seed e quindi senza toccare il clustering greedy order-dependent, che resta il work item F-4 fuori scope. FR-011 tocca `_relationship_score` (una riga di ordering, formule intatte) ed è un fix behavioral dichiarato: nei casi di pareggio la relazione scelta può cambiare rispetto a prima, ma prima era arbitraria. Senza FR-011, né SC-003 (equivalenza esatta) né il test di determinismo di FR-007 sono verificabili.

### Key Entities

- **`factions.py`**: modulo behavioral §4.7; formule (4.38)-(4.41) INTOCCATE.
- **`affinity.py`**: `compute_affinity` + helper `_relationship_score` (1 query/coppia) e `_circumstance_score` (2 query/coppia); usato anche fuori da factions — il percorso non-batched resta il default per gli altri caller.
- **`Agent.group`**: FK nullable `SET_NULL`, `related_name="members"`; nessun segnale, nessun `save()` override (presupposto della policy FR-006).
- **`Relationship`**: bidirezionale via Q-objects, `unique_together (agent_from, agent_to, relation_type)` — il prefetch deve gestire entrambe le direzioni e relazioni multiple per coppia con la semantica di `_relationship_score` resa deterministica da FR-011: la più forte, e a pari strength quella con `id` minore.
- **`Memory`**: filtro `source_type=PUBLIC`, `is_active=True`, `tick_created__gte=tick-10` per l'affinità; finestra `tick-5` senza filtro di tipo per la dedup suggerimenti — il prefetch replica esattamente i filtri correnti di ciascun uso.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: per lo scenario 20 agenti liberi × 4 gruppi × 10 membri, il numero di query di `_check_join_existing_groups` misurato nei test è INDIPENDENTE dal numero di coppie e dal numero di suggerimenti generati (fetch membri per gruppo, contesto affinità aggregato, dedup aggregata, `bulk_create`): il budget esatto viene fissato dal test con `django_assert_num_queries` e non cresce raddoppiando agenti liberi o membri. Oggi lo stesso scenario costa O(coppie) (≥3 query per coppia, più fetch membri, exists relazione positiva e dedup per coppia/agente).
- **SC-002**: `compute_legitimacy` + successione su un gruppo di N membri esegue un budget costante di query (nessun termine proporzionale a N oltre al fetch unico dei membri), verificato nei test.
- **SC-003**: test di equivalenza numerica: affinità e leadership score identici (uguaglianza float esatta, stessi input e stessa aritmetica) tra percorso batched e non-batched, A VALLE di FR-011 (tie-break deterministico in entrambi i percorsi — senza FR-011 l'equivalenza non è definibile nei casi di pareggio).
- **SC-004**: test di rollback: eccezione iniettata a metà di schism e creazione → zero righe residue (Group, Agent.group, Memory).
- **SC-005**: suite completa verde (810 baseline + nuovi), ruff pulito, zero regressioni sui test esistenti dell'area (8 in `test_factions.py` + 7 in `test_affinity.py`, conteggio verificato) senza modifiche di assertion, eccetto dove il contratto corretto di FR-002/FR-011 richiede aggiornamento dichiarato del fixture/expected: ogni modifica di test esistente va motivata nel commit.
- **SC-006**: whitepaper §4.7 EN/IT speculari, bullet deferred risolto, zero modifiche alle equazioni; grep `Deferred behavioral hardening` sul whitepaper → stato risolto/riscritto.

## Assumptions

- La media su tutti i membri vivi è il comportamento inteso dalla docstring originale; il cambio di dinamica emergente rispetto al campione biased è una correzione, non una regressione. Nessun esperimento di validazione pubblicato dipende dal comportamento biased (le validazioni §7 sono pendenti).
- Nessun RNG viene introdotto: rappresentatività ottenuta eliminando il campionamento, non randomizzandolo. Il set chiuso di fasi di `demography/rng.py` resta intatto.
- La policy bulk-update è sicura perché su `Agent` non esistono segnali né `save()` override (verificato repo-wide 2026-07-15); la policy è documentata con questo presupposto e con l'obbligo di revisione se il presupposto cade.
- `transaction.atomic` per-mutazione (non per-fase) è sufficiente per l'integrità: le mutazioni di gruppi diversi sono indipendenti; il loop Celery del tick è single-worker per simulazione.
- L'estensione di `affinity.py` è il punto DRY corretto: la logica di scoring resta negli helper esistenti; il batching cambia solo l'approvvigionamento dei dati.

## FAQ

**Perché eliminare il campione di 5 invece di renderlo casuale seedato?**
Perché il campione esisteva solo per contenere il costo N+1 di `compute_affinity`. Con il prefetch il costo per coppia diventa CPU pura (similarità Big Five in-memory e matching su liste già caricate), quindi la media su tutti i membri — il comportamento che la docstring dichiarava — è calcolabile senza cap. Un random seedato avrebbe richiesto di estendere il set chiuso di fasi RNG documentato in §3.4 (o un nuovo stream), aggiungendo complessità per approssimare ciò che ora si calcola esattamente.

**Il cambio da 5 membri a tutti i membri non altera le simulazioni esistenti?**
Sì, può alterare quali suggerimenti di adesione emergono: è un fix behavioral dichiarato (Round 3 è "behavioral hardening" proprio per questo) e corregge un campionamento a ordine non definito (né rappresentativo né garantito stabile). Le validazioni scientifiche di §7 non sono ancora state eseguite, quindi nessun risultato pubblicato dipende dal comportamento biased. I nuovi regression test fissano il contratto corretto.

**Perché bulk `update()` e non `save()` per-agente come disciplina unificata?**
Su `Agent` non esistono segnali né override di `save()` (verificato): i due percorsi sono comportamentalmente identici e bulk costa 1 query invece di N. La direzione opposta (tutto per-agente) avrebbe solo aggiunto query senza beneficio. Il presupposto è documentato nel docstring di modulo con obbligo di revisione se qualcuno aggiungerà segnali su `Agent.group`.

**Perché `transaction.atomic` anche su `_check_dissolution` e `_process_formation_decisions` se l'audit citava solo schism e creazione?**
Perché sono le altre due vie di mutazione multi-riga della stessa classe (membership + Memory): applicare l'atomicità solo a due delle quattro lascerebbe la stessa vulnerabilità dove l'audit non ha guardato. Exhaustive Bug Analysis: si correggono tutte le occorrenze della classe, non solo quelle citate.

**Come si testa il rollback senza concorrenza reale?**
Iniettando un'eccezione a metà mutazione (mock/monkeypatch su una funzione interna chiamata dopo le prime scritture) e verificando che il database non contenga nessuna riga della mutazione. Non si testa la concorrenza vera (fuori scope, richiederebbe multi-processo): si testa il contratto di atomicità che la concorrenza presuppone.

**L'equivalenza numerica batched/non-batched è davvero esatta o "quasi uguale"?**
Esatta, ma solo grazie a FR-011: oggi `_relationship_score` sceglie `.order_by("-strength").first()` e con strength a pari valore (default 0.5, caso comune) la riga scelta è arbitraria — un gemello batched non può "replicare esattamente" una selezione arbitraria. Con il tie-break deterministico `(-strength, id)` in entrambi i percorsi, la selezione è definita e il batching cambia solo come i dati arrivano, non l'aritmetica. I test usano uguaglianza esatta, non tolleranze.

**FR-011 cambia il comportamento di `_relationship_score` per tutti i caller, non solo per factions?**
Sì: l'ordering diventa deterministico ovunque. Nei casi di pareggio la relazione scelta può differire da una specifica esecuzione passata, ma la scelta precedente era arbitraria (dipendente dall'ordine di Postgres), quindi nessun comportamento definito viene rotto — ne viene definito uno dove prima non c'era. È un'estensione di scope dichiarata, una riga di ordering, formule intatte.

**Impatto sul whitepaper: cambia qualche equazione?**
No. (4.38)-(4.41) e tutti i parametri restano intatti. Cambia SOLO il bullet Known Limitations "Deferred behavioral hardening" (deferred → risolto): verificato che il paragrafo Algorithm di §4.7 non menziona né il campione di membri né le query, quindi non va toccato. EN e IT speculari; frozen-pin aggiornato al merge come da procedura fase 7.

**Cosa resta fuori scope?**
Il clustering order-dependent (F-4, "robust faction clustering", già tracciato come work item separato in §4.7), il meccanismo club-goods di Iannaccone (deferred dichiarato), qualsiasi ottimizzazione di `compute_affinity` per caller non-factions (il percorso non-batched resta default), e l'introduzione di RNG seedato in factions.

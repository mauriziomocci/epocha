---
name: determinism-enumeration-pending
description: "Dossier 2026-07-17: i difetti di determinismo REALI di agents/world (~23 siti noti, 3 classi) piu' la scoperta che la riproducibilita' e' architetturalmente irraggiungibile (generazione LLM senza seme). Evidenza gia' raccolta con file:riga, da 3 round di audit avversariale. Il RISCHIO PAPER e' stato CORRETTO (PR#16, pending merge): restano aperti i due difetti di CODICE (RNG globale non seminato + ~23 pin di tiebreak)."
metadata: 
  node_type: memory
  type: project
  originSessionId: 1b65a5a6-008a-426a-8e70-1cff4da20b33
---

# Determinismo agents/world -- enumerazione da rifare, e la domanda che la sovrasta

Prodotto chiudendo [[economy-ratified-decisions]] su R12-DET-1, che era un **non-difetto**. Tre round di audit avversariale indipendenti hanno demolito tre enumerazioni successive. Questo file conserva l'evidenza perche' il prossimo tentativo non riparta da zero.

## La lezione di metodo (vale piu' dell'elenco)

Tre delimitazioni, tre fallimenti, **sempre la stessa forma**: il criterio che decide DOVE guardare era piu' stretto di quanto l'analisi stessa sapesse essere vero.

1. Cercavo `icontains` + `.first()` non ordinato = esattamente i casi che l'ORM **protegge**.
2. Cercavo `.first()` con `order_by` **esplicito**, avendo dichiarato due righe prima che `Meta.ordering` e' ugualmente causale. Ha nascosto `factions.py:1247`, dentro una funzione gia' enumerata.
3. Definivo il troncamento come *"slice `[:N]`"* (forma sintattica), mancando `information_flow.py:247-249` che tronca con un `break`. E fondavo la chiave di pin sulla seed-stabilita' di `agent_id`, mai verificata e falsa.

Popolazione dichiarata: 3 -> 13 -> ~23. Ogni volta l'ha trovato l'audit, mai il grep. **Non rifare l'enumerazione con un grep**: serve indagine avversariale multi-agente.

## I predicati corretti (semantici, non sintattici)

1. `.first()`/`.last()` su queryset con `self.ordered == True` (per `order_by` **o** `Meta.ordering`) e **chiave finale non unica**. Nota: `.first()` su queryset NON ordinato e' **sano** -- Django applica `order_by("pk")`.
2. **Troncamento a N senza ordine totale**: slice `[:N]`, `break` a contatore, `islice`. Non solo `[:N]`.
3. Iterazione order-sensitive su ordine parziale, incluse iterazioni su `set`/`dict` di stringhe (PYTHONHASHSEED).
4. Riduzione float order-sensitive (somma non associativa che alimenta un `max`).

Inventario `Meta.ordering` **parziali** (ogni `.first()` su questi perde il tiebreak): `Memory` `["-emotional_weight","-tick_created"]` (`agents/models.py:221`); `DecisionLog` `["tick"]` (`:279`); `EconomicTransaction` `["-tick"]` (`world/models.py:75`); `GovernmentHistory` `["-from_tick"]` (`:137`); `Event` `["tick"]` (`simulation/models.py:87`). **NON** `SimulationSnapshot`: ha `unique_together = ["simulation","tick"]` (`simulation/models.py:132-134`), quindi sotto `filter(simulation=X)` l'ordine e' totale.

## Siti noti (~23, NON esaustivi -- e' il punto)

**Classe 1**: `factions.py:1247-1251` (Memory `.first()`, `proposal.content` decide il clustering); `election.py:245` (`.order_by("-strength").first()`, gemello non corretto di `affinity.py:265` gia' fixato sotto FR-011; persiste su `Government.head_of_state`).

**Classe 2**: `memory.py:43-45` (`[:max_memories]` -> **quali memorie entrano nel contesto LLM di OGNI decisione**); `decision.py:238`, `:242-244`, `:246-251`, `:258-261`; `report.py:49` e `:66`; `serializers.py:22` e `:25`; **`information_flow.py:218-220` + `:247-249`** (`break` a `max_recipients` su `Relationship` non ordinato -> quali 20 vicini ricevono ogni voce di ogni tick; il piu' consequenziale).

**Classe 3**: `factions.py:1183-1187` (DecisionLog, ordine parziale -> composizione fazioni); `factions.py:1204`/`:1207` (dict `joiners`); `stratification.py:142-145` (`-wealth` non unico -> `enumerate` -> `social_class` persistita); `stratification.py:265-274`+`:288` (`process_corruption`: il tetto 1% e' ricalcolato su `global_wealth` che DECRESCE nel ciclo -> ordine causale); `factions.py:1286-1288` (`next(iter(roles))`); `factions.py:1419-1420`+`:1427-1428` (`join` di set **nel prompt LLM** -- percorso primario, non fallback); `information_flow.py:72-82`, `:101-116`, `:119-137` (fasi 1/2/3; le fasi 2-3 hanno pareggio **garantito** su entrambe le chiavi perche' `_propagate_memory` copia `emotional_weight` invariato a `:302` e l'origin a `:306`/`:325`).

**Classe 4**: `election.py:162-164`+`:171` (somma float dei tally) -> `election.py:180` `max(candidates, ...)` su queryset **non ordinato** (`:147-155`) = capo di stato scelto per ordine di scansione a parita' di tally.

**Verificati SANI** (non ri-sollevare): `engine.py:149`/`:168`/`factions.py:1208` (R12-DET-1); `engine.py:280` (`good_code` unico sotto `filter(agent=)`, `unique_together` a `economy/models.py:579`); `engine.py:362`; `factions.py:446` (legge solo la chiave d'ordinamento); `factions.py:581` (conta, commutativo); `factions.py:821` (set per `not in`); `affinity.py:413`, `factions.py:986`/`:1123` (values_list per test sottostringa); `affinity.py:265` (gia' fixato); `government.py:475`/`:637` (bulk update); `memory.py:66` (decay indipendente); `movement.py:271-274`; `property_market.py:248`, `couple.py:228` (gia' pinnati); `economy/engine.py:114` (set); `couple.py:355` (scritture identiche).

## LA DOMANDA CHE SOVRASTA TUTTO: Epocha e' riproducibile?

**No, e nessun pin lo cambia.** Tre cause indipendenti:

1. **Il mondo e gli agenti nascono da un LLM senza seme.** `generator.py:102-107` chiama `client.complete(..., temperature=0.8)`; `grep seed epocha/apps/llm_adapter/` = **vuoto**. Il progetto lo dichiara nel proprio modello: `seed = models.BigIntegerField(help_text="Seed for reproducibility (non-LLM part)")` (`simulation/models.py:35`). Due run identicamente seminate **non hanno gli stessi agenti**. Corollario: nessun `agent_id` e' seed-stabile.
2. **RNG globale non seminato in agents/world**: `government.py:618` `random.random()` decide il successo di un **colpo di stato**; `movement.py:245-246` lo scatter; `generator.py:172`/`:391` il piazzamento. `random.seed(` non esiste nel progetto; `random.Random(` solo in `economy/rng.py:56` e `demography/rng.py:45`. Il rimedio esiste gia': `get_seeded_rng` (`economy/rng.py:31`, `demography/rng.py:25`).
3. **Il chord Celery e' parallelo** (`simulation/tasks.py:59-62`): `DecisionLog`, `Memory`, `Relationship` nascono in ordine deciso dallo scheduling, non dal seed.

**Implicazione sul paper -- CORRETTA il 2026-07-17 (PR#16, branch `20260717-160922-whitepaper-reproducibility-claim`, commit `11b18b3`, pending merge/ratifica).** Era la voce prioritaria di questo dossier: il whitepaper affermava in piu' punti *"identically-seeded runs reproduce bit-identical state"* e, il piu' grave, che lo stesso seme riproduce lo stesso *decision log* per-agente. Un'enumerazione avversariale (`specs/20260717-160922-.../research/enumeration-reproducibility-claims.md`) ha classificato 19 affermazioni: 5 FALSE, 1 borderline, 7 ambigue, 3 anchor corretti. Corrette 13 loci per lingua (EN+IT in lockstep): ogni affermazione di riproducibilita' ora e' delimitata alla parte non-LLM; il decision log e' dichiarato **auditabile, non riproducibile**; la nota mancante sul RNG del coup (`government.py:618`) e' aggiunta a §4.5 sul modello di N-8; i 3 anchor (§3.1, §4.6 N-8, App.B "draws") intatti. Nessun codice toccato, frozen-pin §4.8 invariato. **Restano aperti i due difetti di CODICE sotto** -- il paper ora dice la verita' su di essi, ma non li risolve.

## Altri work item emersi (tracciati, non risolti)

- **Le memorie del ciclo politico non si propagano MAI**: `stratification.py:186`/`:317` e `property_market.py:521` creano memorie dirette **dopo** `propagate_information` nello stesso tick, e al tick dopo la fase 1 filtra `tick_created=tick`. Difetto di **modello**, non di determinismo.
- `abs(sentiment)` vs `strength` in `election.py`: docstring (`:222-223`) e codice (`:245`) divergono **dal commit originale** `ead87fa` -- divergenza **nativa**, non stale. Nessuno dei due criteri e' scientificamente giustificato (`affinity.py:225` dichiara il proprio "tunable heuristic ... not derived from a cited source").
- Gruppo a coesione nulla scartato **dopo** la selezione (`factions.py:1209-1210`).
- Invariante di non-sovrapposizione delle zone: ne' vincolata a DB ne' documentata (`generator.py:146-151`).
- Preferenza `iexact` sul match del frammento nei resolver LLM (questione di modello, non di determinismo).

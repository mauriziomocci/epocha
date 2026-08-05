---
name: economy-ratified-decisions
description: "Decisioni di modello RATIFICATE dall'utente durante l'audit dell'economy base layer (12 round, CONVERGED 2026-07-16, merge 368e972, whitepaper 4.8). NON rilitigare -- se un audit futuro le ri-solleva, sono scelte deliberate, non difetti."
metadata: 
  node_type: memory
  type: project
  originSessionId: 04c1bad8-c5e3-4aa6-a6fc-12ef535f744c
---

Decisioni ratificate durante il primo audit avversariale dell'economy base layer (Round 1-12, 2026-07-15/16, merge `368e972`, promosso a whitepaper §4.8). Estratte dall'handoff di sessione prima della sua rimozione: l'handoff era untracked e queste erano la sua unica copia consolidata. La spec `specs/20260715-132752-economy-base-layer-audit/spec.md` copre solo i punti-decisione D1-D4 del gate di fase 2; il resto viveva solo qui.

**Se un audit futuro ri-solleva uno di questi punti: sono scelte deliberate e ratificate, non difetti.**

## Conservazione e flussi

- **Approccio A per la conservazione** (D1, ratificato): il valore prodotto V e' partizionato in quote che sommano a 1 -- wage 0.6 / rent 0.15 / profit 0.25 residuo, tunable da template d'epoca. NON si paga ogni fattore indipendentemente (era il difetto pre-audit: iniettava piu' del doppio di V come cassa nuova).
- **Depositi FUORI da M**: `banking.py` ricalcola i depositi dalla stessa cassa circolante; sommarli a M sarebbe doppio conteggio. M = cassa circolante.
- **Tassazione solo con Government**: nessun Government = nessuna tassa. Il tesoro e' accreditato con la somma dei debiti EFFETTIVI (non con il nominale di `compute_taxes`).
- **Vendita ownerless -> tesoro**: trasferimento, mai distruzione di valore.
- **Domanda dimensionata sulla sola valuta primaria**.
- **Interesse su prestito bancario = SINK**: dedotto dal debitore e NON ri-accreditato ad alcuna controparte, quindi contrae M per scelta di modello (disclosure R5-DISC-1 in `monetary.py`, doc-sync in §4.2.2).

## Mercato e prezzi

- **Razionamento proporzionale sul lato corto** (D2) con running total.
- **Priorita' essenziali-prima al settlement**: sort stabile, non lotteria hash. Il test `test_settlement_prioritizes_essentials_...` patcha `execute_trades` con ordine avversario luxury-first: **quel test e' il contratto**, se si tocca il sort si rompe.
- **Indice di Carli documentato, NON sostituito**: mancano i pesi di spesa per un indice migliore (Laspeyres/Paasche). Il bias e' dichiarato, non corretto.
- **Fisher con income-velocity** (non tautologica su M, cosi' M si cancella) e **PQ = somma dei V_z per-zona** ai prezzi di equilibrio di ciascuna zona, non alla media cross-zona.

## Credito

- **Default settlato UNA SOLA VOLTA**: stato terminale `default_settled`, cosi' sequestro collaterale, write-off bancario e danno reputazionale scattano una volta sola.
- **Cascade netto del collaterale**, seminata dai loss record del tick CORRENTE, con flag `cascade_origin` perche' un evento di perdita sia valutato contro soglia una volta sola.
- **Lien sul collaterale**: property pegnata non vendibile ne' matchabile. Enforced a 4 gate con la coppia `["active","defaulted"]`.
- **Boundary LLM validato**: amount finito e > 0 (`math.isfinite`).
- **R8-NEW-5 -- premessa REFUTATA ma fix tenuto**: il finding sosteneva "loan serviti come interest-only per sempre"; falso, `default_dead_agent_loans` spazza i loan dei debitori morti e il blocco credito salta solo a estinzione totale. Il catch-up `due_at_tick__lte` e' stato tenuto lo stesso perche' chiude la fragilita' dell'uguaglianza esatta a costo nullo, percorso normale invariato.

## Determinismo

- **Pinnato ovunque** nel package economy (tiebreak stabile su ogni selettore ordine-sensibile; RNG derivato da seed+tick con namespace `economy:`).
- **Test di determinismo**: per i bug di ordine-DB un RED affidabile e' spesso impossibile, e i test **pinnano il contratto** invece di riprodurre il non-determinismo (dichiarato in docstring). Eccezione: `test_sell_property_asking_price_deterministic_on_expectation` e' un RED reale. **La ragione originariamente scritta qui era sbagliata** (2026-07-17): non e' che "Postgres restituisce i pari-merito in ordine di inserimento". E' che `QuerySet.first()` applica **lui** `order_by("pk")` quando `self.ordered` e' False -- vedi il bullet R12-DET-1 sotto. Un `.first()` nudo e' gia' pinnato sull'id: per questo pre-fix e post-fix danno la stessa riga e il rosso non si materializza.
- **R12-DET-1 e' un NON-DIFETTO** (chiuso 2026-07-17, tre round di audit avversariale indipendenti concordi). Era ratificato qui come "difetto reale rinviato": **era un errore di diagnosi**. I resolver a `simulation/engine.py:148-171` (e `agents/factions.py:1208`) usano `.first()` su queryset **non ordinato**, e Django in quel caso applica da se' `order_by("pk")` (`django/db/models/query.py`, `first()`: `if self.ordered: ... else: queryset = self.order_by("pk")`). `Agent`, `Zone` e `Group` non dichiarano `Meta.ordering`, quindi i tre siti **gia' emettono** `ORDER BY id ASC LIMIT 1` -- verificato sull'SQL reale. Il fix proposto avrebbe emesso SQL identico: un no-op. **Inversione da ricordare**: e' l'ASSENZA di `Meta.ordering` a far scattare il tiebreak protettivo; e' la sua PRESENZA su chiave non unica a sopprimerlo (quello si' e' il difetto vero, e ne esistono ~23 istanze in agents/world -- work item separato, vedi la build map).

## Convenzioni documentali

- **Anchor dei capitoli NON-economia** (§4.1 demografia, §4.6 movimento, §5.4 persistenza): pinnati ai **LORO** commit, non a HEAD. Risultano "stale vs HEAD" ed **e' corretto cosi'** -- non refresharli da un branch economia.
- **`DeprecationWarning` da `epocha.apps.world.economy`** nei test e' **INTENZIONALE** (PR#12, path B).
- Nella fixture di `test_engine.py` il merchant produce "services" senza GoodCategory (prezzo 0, fuori dal PQ) e la sua property reclama "luxury" non prodotto: **preesistente, non un bug**.

## Note aperte (non bloccanti)

- `except Exception: pass` preesistente nello step 8c di `engine.py` (stability feedback): fuori scope, candidato a cleanup futuro.

Correlate: [[build-map-source-of-truth]], [[audit-repass-batch-2026-04-12-pending]].

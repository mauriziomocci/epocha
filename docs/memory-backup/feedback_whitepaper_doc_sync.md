---
name: whitepaper-doc-sync-rule
description: REGOLA PERMANENTE -- ogni PR che modifica codice di un modulo descritto in cap. 4 del whitepaper deve aggiornare il rispettivo capitolo nello stesso commit
type: feedback
originSessionId: b165274d-a708-4e8c-abed-b28a018c163f
---
# Whitepaper-code doc sync rule

Ogni PR che modifica codice di un modulo descritto nel cap. 4 del whitepaper bilingue (`docs/whitepaper/epocha-whitepaper.md` + `.it.md`) deve aggiornare il rispettivo capitolo nello stesso commit, oppure giustificare in PR description perche' non serve (es. fix puramente refactor che non cambia il modello scientifico).

## Mapping moduli -> capitoli (vivo, da aggiornare quando moduli si promuovono)

| Modulo (path) | Capitolo whitepaper EN | Capitolo whitepaper IT |
|---|---|---|
| `epocha/apps/demography/` | §4.1 (Mortality, Fertility, Couple, Inheritance, Migration) | §4.1 |
| `epocha/apps/economy/expectations.py`, `credit.py`, `banking.py`, `property_market.py` | §4.2 (Expectations, Credit, Property) | §4.2 |
| `epocha/apps/agents/reputation.py` | §4.3 (EN) | §4.3 (IT) |
| `epocha/apps/agents/information_flow.py` | §4.4.1 (EN) | §4.4.1 (IT) |
| `epocha/apps/agents/distortion.py` | §4.4.2 (EN) | §4.4.2 (IT) |
| `epocha/apps/agents/belief.py` | §4.4.3 (EN) | §4.4.3 (IT) |
| `epocha/apps/agents/affinity.py` | §4.4.4 (EN) | §4.4.4 (IT) |
| `epocha/apps/world/government.py` | §4.5.1 (EN) | §4.5.1 (IT) |
| `epocha/apps/world/government_types.py` | §4.5.2 (EN) | §4.5.2 (IT) |
| `epocha/apps/world/institutions.py` | §4.5.3 (EN) | §4.5.3 (IT) |
| `epocha/apps/world/stratification.py` | §4.5.4 (EN) | §4.5.4 (IT) |
| `epocha/apps/world/election.py` | §4.5.5 (EN) | §4.5.5 (IT) |
| `epocha/apps/agents/movement.py` | §4.6 (EN) | §4.6 (IT) |
| `epocha/apps/agents/factions.py` | §4.7 (EN) | §4.7 (IT) |
| `epocha/apps/economy/production.py`, `market.py`, `distribution.py`, `monetary.py`, `initialization.py`, `engine.py` | §4.8 (EN) | §4.8 (IT) |

Quando un modulo del cap. 8 viene promosso a cap. 4 dopo re-audit CONVERGED, aggiungerlo a questa tabella. Residuo: solo il Knowledge Graph (§8.1).

Due trappole verificate contro il source tree il 2026-07-17, da non "correggere" a intuito: il belief filter del §4.4.3 sta in `agents/belief.py`, non `belief_filter.py`; il Movement del §4.6 sta in `agents/movement.py`, non sotto `world/`.

La tabella vive in quattro copie che cambiano insieme: questa memoria, `docs/memory-backup/feedback_whitepaper_doc_sync.md`, la sezione Documentation Sync del `CLAUDE.md` di progetto, e la sezione Contributing di `README.md` + `README.it.md`.

## Why

La regola Documentation Sync del CLAUDE.md gia' stabilisce che docstring/README/whitepaper devono aggiornarsi insieme al codice. Questa regola ne e' l'applicazione operativa al whitepaper, con la rule "stesso commit" che evita drift.

Il versioning per-sezione del whitepaper ha header `> Status: implemented as of commit <hash>`. Senza questa rule l'header diverge silenziosamente dal codice e perde valore.

## How to apply

- **Ora (2026-07-17, mapping a 8 capitoli / ~20 moduli)**: enforce via PR review checklist + sezione "Contributing" dei README + tabella in CLAUDE.md sotto "Documentation Sync".
- **La soglia dello script diagnostico e' stata superata.** La versione precedente di questa memoria diceva "quando il mapping cresce a 6-8 entry (dopo re-audit batch 2026-04-12): introdurre `make whitepaper-staleness`". Il batch e' chiuso e il mapping copre tutti gli 8 capitoli del par. 4: il trigger e' scattato, lo script non esiste ancora. E' un work item aperto, non un rinvio implicito -- va via Spec Kit come tutto il resto. Lo script dovrebbe listare i moduli il cui ultimo commit e' piu' recente del commit pinnato nell'header `> Status: implemented as of commit <hash>` della loro sezione.
- **Quando si aggiungono contributor esterni**: promuovere a pre-commit hook bloccante.

NON costruire il hook ora -- YAGNI finche' il developer e' singolo. Lo script diagnostico invece non e' piu' YAGNI: quattro copie della tabella e otto capitoli sono oltre quello che una checklist manuale regge.

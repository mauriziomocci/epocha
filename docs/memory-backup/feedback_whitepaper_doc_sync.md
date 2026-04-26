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
| `epocha/apps/demography/` | §4.1 (Mortality, Fertility, Couple) | §4.1 |
| `epocha/apps/economy/expectations.py`, `credit.py`, `banking.py`, `property_market.py` | §4.2 (Expectations, Credit, Property) | §4.2 |

Quando un modulo del cap. 8 viene promosso a cap. 4 dopo re-audit CONVERGED, aggiungerlo a questa tabella.

## Why

La regola Documentation Sync del CLAUDE.md gia' stabilisce che docstring/README/whitepaper devono aggiornarsi insieme al codice. Questa regola ne e' l'applicazione operativa al whitepaper, con la rule "stesso commit" che evita drift.

Il versioning per-sezione del whitepaper ha header `> Status: implemented as of commit <hash>`. Senza questa rule l'header diverge silenziosamente dal codice e perde valore.

## How to apply

- **Ora (2 mapping)**: enforce via PR review checklist + sezione "Contributing" del README. Una riga in CLAUDE.md sotto "Documentation Sync".
- **Quando il mapping cresce a 6-8 entry** (dopo re-audit batch 2026-04-12): introdurre script diagnostico `make whitepaper-staleness` o equivalente che lista moduli con commit piu' recenti del whitepaper section.
- **Quando si aggiungono contributor esterni**: promuovere a pre-commit hook bloccante.

NON costruire il hook ora -- YAGNI per un mapping di 2 entry e developer singolo.

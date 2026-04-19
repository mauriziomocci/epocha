---
name: readme-rewrite-todo
description: FOLLOW-UP da eseguire al termine del Plan 2 demografia: riscrivere README.md e README.it.md (molto obsoleti secondo utente)
type: project
originSessionId: f9bc7a55-71c4-45ed-9602-f5e328a6175e
---
# README rewrite — follow-up

**Stato**: pendente, da eseguire al termine del Plan 2 demografia o in una finestra dedicata subito dopo.

**Richiesta dell'utente** (2026-04-19): sia `README.md` (inglese) che `README.it.md` (italiano) sono molto obsoleti e vanno riscritti.

**Perche' ora e' diventato rilevante**: Economy Spec 2 (Parts 1-3) e ora Demography Plan 1 hanno aggiunto moduli, modelli, regole di progetto, apps, pattern scientifici e policy di workflow che NON sono riflessi nei due README attuali.

**Scope della riscrittura** (proposto):
- Aggiornare architettura: app `epocha.apps.demography` aggiunta, modelli principali, integration contracts helpers (`add_to_treasury`, `SUBSISTENCE_NEED_PER_AGENT`), RNG seeded per-sottosistema
- Aggiornare stack tecnico: scipy come dipendenza runtime
- Aggiornare regole di progetto: canonical 7-phase workflow, task-breakdown mandatory, model selection policy Opus/Sonnet, italian-specs rule
- Aggiornare roadmap / stato: Economy Spec 1+2 done, Demography Plan 1 done, Plan 2 in corso, Demografia totale scope
- Validation benchmarks attesi (Wrigley-Schofield, Irish Famine) documentati in README
- Visione paper scientifico come outcome del progetto
- Istruzioni di setup aggiornate (docker-compose, test.py fix, pytest --ds default)

**Non in scope** (per non esplodere):
- Full API docs (esistono altrove)
- Screenshot e media

**Stili**:
- README.md primario, inglese, publication-ready (puo' essere linkato in pubblicazioni / paper)
- README.it.md in sync ma in italiano per contributors italofoni

**Quando triggerare il task**: subito dopo il merge di Plan 2 a develop. Registrata come memoria persistente per non dimenticarla.

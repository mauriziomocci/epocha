---
name: scalability-analysis
description: Analisi di scalabilita' da 15 agenti (Versailles) a 500 agenti (crisi globale) con stime di performance e costo
type: project
originSessionId: 0a27799c-3d4b-4995-b144-424ee45e5764
---
Analisi fatta il 2026-04-12. L'architettura scala senza limiti
fondamentali. Il vincolo e' operativo (LLM call speed/cost).

## Stime per scenario globale (200-500 agenti)

- DB: triviale (200K righe, PostgreSQL gestisce milioni)
- Economia CES/tatonnement: pura matematica, millisecondi
- Information flow: O(N*R) lineare, gestibile
- PostGIS: progettato per dati planetari

## Collo di bottiglia: LLM

500 agenti LLM full = ~4 min/tick, ~7 ore per 100 tick.
Soluzione: tiered agents (50 LLM + 450 rules) = ~30 sec/tick.
Costo: ~$5 per simulazione completa di 100 tick.

## Approccio tiered agents

- Leader chiave (30-50): decisioni via LLM full, alta qualita'
- Organizzazioni (15-20): meccanismo consenso/voto tra membri LLM
- Stati minori (50+): regole parametriche da personalita'/interessi
- Opinione pubblica (30+): regole aggregate, no LLM individuale

Da implementare come parte del sistema multi-level agents.

## Update 2026-10-29 (user): the purpose, and what scale means

Epocha's purpose is the scientific simulation of civilizations of thousands,
millions and billions of people. Behaviour, age-dependent included (see
[[project-life-course-behavior]]), is modelled with rules and distributions
grounded in the literature, at a bounded cost per tick, never with one LLM
call per person. Small populations with individual or group chats are
possible, but secondary: interaction must exist, it is not the engine of the
simulation. As it stands, with every agent deciding through the LLM, Epocha is
"più o meno un giocattolo" (user). Every spec states its cost per tick and how
it scales with population. Take inspiration from MiroFish
([[mirofish-comparison]]) while staying original and going beyond it: Epocha
is meant to be unique in its kind.

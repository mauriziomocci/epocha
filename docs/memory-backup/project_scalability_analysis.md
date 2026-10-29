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

## Billions: a future feasibility study, not a feature (user, 2026-10-29)

The user wants billions of individuals in a future development, "in maniera
rigorosa, funzionale, fattibile", to be studied first. Agreed approach: a
separate feasibility-study work item, AFTER the first historical validation
([[project-agreed-order-2026-10-29]]), not opened yet. Direction to study:
multi-resolution modelling (individuals only where needed — protagonists, a
region under observation, a critical event — weighted groups or cohorts
elsewhere, e.g. Scheffer et al. 1995 super-individuals). Four questions:
(1) which techniques exist, with sources and licences; (2) how to prove the
grouped model gives the same results as the individual one (equivalence tests,
weight invariance); (3) the real cost per tick, MEASURED on prototypes at 10^4,
10^5 and 10^6 people, extrapolated to 10^9; (4) what changes in Epocha's
architecture. A motivated "no" for some combinations is an acceptable outcome.

## Two thresholds, not one (2026-10-29)

User: even 100 LLM agents simulating 100 people is neither feasible nor
economical. Agreed for the LLM: 100 agents x 365 daily ticks = 36,500 calls per
simulated year, so no per-person LLM anywhere in the engine, even at a hundred
people. NOT agreed that grouping is needed at hundreds: the cost comes from
the LLM, not from the individual. A rule-driven individual is cheap (measured
the same day: one simulated year of 12 people, demography ticks only, 15 s,
no LLM call; Plan 4's demography cost per tick does not grow with the
population). So: (1) per-person LLM: never in the engine; LLM only for a few
protagonists, group archetypes and chats; (2) grouping individuals
(super-individuals, cohorts): only where memory and compute force it,
plausibly from 10^5-10^6 up, subject of the feasibility study. Rule-based
couples and life-course behaviour stay individual-level, good from hundreds to
tens of thousands, and are the rigorous choice for historical validation
(demographic microsimulation is individual-level).

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

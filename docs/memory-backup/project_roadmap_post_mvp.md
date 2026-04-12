---
name: post-mvp-roadmap
description: Full roadmap after MVP -- 3 phases, 7 features (React frontend excluded by user request)
type: project
originSessionId: 0a27799c-3d4b-4995-b144-424ee45e5764
---
Roadmap post-MVP concordata con l'utente il 2026-04-05.

**Fase 1 -- Profondita' di simulazione**
1. Information Flow -- passaparolo, voci, distorsione (DONE 2026-04-05)
2a. Fazioni e leadership -- formazione, coesione, leadership emergente (DONE 2026-04-05)
2b. Sistema di governo -- 12 tipi, transizioni, elezioni, colpi di stato (DONE 2026-04-05)
2c. Istituzioni -- 7 tipi con health dynamics (DONE 2026-04-05, incluso in 2b)
2d. Stratificazione -- Gini, classi dinamiche, corruzione (DONE 2026-04-05, incluso in 2b)
3a. **Modello economico realistico** -- economia reale + mercati finanziari (ASAP dopo KG, confermato 2026-04-12)
3b. Modelli scientifici -- epidemie (SIR), demografia, tecnologia

**Fase 2 -- Visualizzazione e analisi**
4. Grafo sociale -- Sigma.js su template Django (DONE 2026-04-06)
5. Analytics / Psicostoriografia -- snapshot, Epochal Crisis, charts (DONE 2026-04-06)
6. Mappa 2D -- Pixi.js per zone e posizioni agenti

**Fase 3 -- Piattaforma**
7. Branching (what-if) -- checkpoint + fork simulazione

**Why:** Le fasi sono ordinate per dipendenze: prima i dati ricchi (fase 1),
poi gli strumenti per capirli (fase 2), poi le feature avanzate (fase 3).
Il sistema politico dipende da information flow. Analytics ha senso solo
con comportamenti emergenti ricchi.

**How to apply:** Seguire l'ordine. Ogni feature ha il suo ciclo
spec -> plan -> implementation. Il frontend React e' stato escluso
dalla roadmap su richiesta dell'utente.

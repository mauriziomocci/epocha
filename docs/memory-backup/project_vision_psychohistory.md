---
name: project-vision-psychohistory
description: The origin and long-term goal of Epocha -- Asimov's psychohistory (Foundation trilogy), pursued scientifically as probabilistic, population-scale simulation; real-world anchor is cliodynamics / structural-demographic theory.
metadata:
  type: project
---

The user (2026-10-29): the idea of Epocha was born reading Asimov's
Foundation trilogy, "una sorta di psicostoriografia"; that is the goal, "se
possibile e utile".

**Why it matters:** it explains the scale direction decided the same day.
Psychohistory rests on two axioms: a population large enough that its
statistical behaviour is predictable though individuals are not, and a
population unaware of the predictions. A per-agent-LLM Epocha can never be
that; a statistical Epocha with a few LLM protagonists can approach it.

**How to apply:**
- Aim at the probabilistic version, never point prediction: many seeded runs
  from the same initial conditions, distributions of outcomes, mechanisms
  that push or brake a crisis, interventions that shift the distribution.
  Point prediction is out of reach (sensitivity to initial conditions,
  reflexivity), and the docs must say so.
- Real-world scientific anchor: cliodynamics (Peter Turchin) and
  structural-demographic theory (Goldstone 1991, "Revolution and Rebellion in
  the Early Modern World"; Turchin & Nefedov 2009, "Secular Cycles"), which
  Epocha's demography, economy, institutions, factions and stratification
  already map onto. The Seshat Global History Databank is a candidate
  validation source: verify details and data licence before use
  ([[feedback-ethics-first]]).
- Prerequisites in order: scale ([[project-scalability-analysis]]),
  reproducibility from the seed (core out of the LLM,
  [[project-determinism-enumeration-pending]]), historical validation
  ([[project-validation-experiments-pending]]); then a structural-demographic
  model and ensemble runs.

## Product principle (user, 2026-10-29)

"Dobbiamo renderlo facilmente utilizzabile e comprensibile, ovviamente con
parti di grande rigore scientifico ma anche narrativo." Epocha must be easy to
use and to understand, with parts of great scientific rigour AND narrative
parts. Read as layers of one product, never two products: a narrative layer
anyone can read (one trajectory told as a story, every fact traceable to a
recorded event), and a rigorous layer for whoever wants to check (ensemble
distributions, uncertainty, methods, sources, reproducibility), reachable
from the narrative by progressive disclosure. Usability is a requirement on
the same level as rigour: the risk to avoid is an excellent scientific engine
nobody can use. MiroFish is the reference for ease of use (documents -> world
-> run -> report -> interview), taken as ideas and credited
([[feedback-mirofish-ethics]]). Related: [[project-dashboard-redesign]],
[[project-narrative-generator]].

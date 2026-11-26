---
name: reference-related-work-2026-10-29
description: Survey of projects and papers related to Epocha (2026-10-29), with licences; full text in the Diario day folder.
metadata:
  type: reference
---

Full survey: `~/Documents/workspace/Diario/2026/10/2026-10-29/epocha-related-work-survey.md`
(MiroFish comparison: `epocha-mirofish-comparison.md`, same folder). Every item
there carries its licence and is IDEAS ONLY ([[feedback-ethics-first]]).

The five sources judged most valuable for Epocha's scale goal:
1. Chopra et al., LLM archetypes / Large Population Models (arXiv 2409.10568,
   2507.09901): one LLM query per group of similar agents, 8.4M people in NYC;
   stated limit: households deciding jointly. Code AGPL: ideas only.
2. Scheffer et al. 1995, super-individuals (Ecological Modelling 80): one
   weighted row stands for many people; weight-invariance test as acceptance.
3. Event-driven scheduling from demographic microsimulation (MicSim, SOCSIM):
   process only the events that fall in a tick. Their code is GPL: ideas only.
4. OASIS (arXiv 2411.11581, Apache-2.0): idle agents per a measured activity
   profile; measured cost of one call per agent: 18 h per step at 1M agents.
5. Grimm's ODD protocol (2020) and pattern-oriented modelling (2005), with
   Rogers-Castro 1981 and the age-crime curve as age patterns to validate.
Copyleft or unlicensed, never code: AgentTorch, FLAME GPU 2 (AGPL), NetLogo
(GPL-2.0), LIAM2, MicSim, rsocsim (GPL), JAS-mine (EUPL), Project Sid and
GenSim (no licence). World Values Survey data may not be redistributed.

Verified in code the same day: the engine calls the LLM once per living agent
per tick (`simulation/engine.py` ~505), contradicting whitepaper §2.2 ("LLM
calls are confined to the narrow decisions..."). Related:
[[project-scalability-analysis]], [[mirofish-comparison]].

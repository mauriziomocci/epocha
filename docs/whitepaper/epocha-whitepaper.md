---
title: "Epocha — A Scientifically Grounded Civilization Simulator"
authors: ["Maurizio Mocci"]
affiliation: "Independent project"
date: "2026-04-26"
version: "0.1"
frozen-at-commit: "<filled-on-merge>"
license: "Apache 2.0"
---

# Epocha — A Scientifically Grounded Civilization Simulator

## Abstract

<placeholder — written at end of W3 once Methods and Validation chapters are in place>

## Keywords

agent-based modeling, computational social science, demographic micro-simulation,
economic agent-based models, large language models, social simulation,
psychohistory, reputation systems

## Document structure and status legend

This document distinguishes three levels of maturity for each subsystem:

- **Audited (CONVERGED)** — chapters in §4 Methods. Adversarial scientific
  audit has reached convergence on the underlying spec or code. Background,
  model, equations, parameters with primary-source citations, algorithm,
  simplifications, and a status header are provided for each module.
- **Implemented, audit pending** — chapters in §8 Designed Subsystems. The
  module exists in the codebase but has not yet completed the convergence
  loop of the project's adversarial audit policy. Each entry is a 5-10
  sentence paragraph linking to the design spec.
- **Specified or planned** — listed in §9 Roadmap as a short bullet.

Status headers in §4 use the form:
> Status: implemented as of commit `<hash>`, spec audit CONVERGED `<date>`.

---

## Table of contents

1. Introduction
2. Background and Related Work
3. System Architecture
4. Methods — Audited Modules
5. Implementation
6. Calibration
7. Validation Methodology
8. Designed Subsystems (implemented, audit pending)
9. Roadmap
10. Discussion
11. Known Limitations
12. Conclusions
13. References
14. Appendices

---

# 1. Introduction

## 1.1 Context

This paper introduces Epocha, an open-source civilization simulator that
combines large-scale agent-based modeling with LLM-driven decision-making,
demographic and economic models grounded in the published literature, and
a multi-tier interaction layer. The notion of *psychohistory* — a
quantitative science capable of predicting the trajectory of large
populations even when individual behavior remains unpredictable — was
introduced as a fictional concept by Asimov in the *Foundation* saga
(Asimov 1951). It has remained fictional, but the underlying
intuition — that aggregate social dynamics admit a formal treatment — has been
pursued for decades by complementary research traditions in computational social
science. Schelling's segregation models showed that strong macroscopic
patterns can emerge from very local individual rules (Schelling 1971).
Agent-based modeling matured into a methodology with the Sugarscape work of
Epstein and Axtell, which framed social science "from the bottom up" by
growing artificial societies inside a controlled computational substrate
(Epstein and Axtell 1996). Six years later, Bonabeau consolidated agent-based
modeling as a general technique for simulating human systems and outlined the
conditions under which it adds value over equation-based approaches (Bonabeau
2002).

A second, more recent line of work has emerged with large language models. By
endowing agents with LLM-driven cognition, recent studies have demonstrated
that synthetic populations can reproduce non-trivial behavioral patterns
observed in human samples (Argyle et al. 2023) and that small communities of
generative agents can exhibit credible social dynamics — memory formation,
reflection, planning, and inter-agent coordination — over short simulated
horizons (Park et al. 2023). Epocha sits at the intersection of these two
lines: it inherits the long-horizon, multi-scale ambition of classical
agent-based social simulation, and it adopts LLM-driven cognition to enrich
agent decision-making with personality, memory, and natural-language
deliberation.

## 1.2 Research gap addressed

Existing LLM-driven agent simulations concentrate on small groups of agents
over short simulated horizons (days to weeks of simulated time, dozens of
agents at most), and they typically operate in deliberately stylized
environments without an underlying demographic or economic substrate.
Conversely, established demographic and economic micro-simulators support
populations of millions over decades or centuries, but their agents are
rule-based: they lack persistent personality, episodic memory, and the
capacity for free-form reasoning that distinguishes human decision-making.
Epocha targets the gap between these two traditions. Its objective is
long-horizon, multi-scale simulation of populations whose individual agents
combine published demographic and economic dynamics with LLM-driven
personality-rich cognition, while remaining auditable, reproducible, and
grounded in primary scientific sources.

## 1.3 Contributions

This whitepaper and the accompanying open-source codebase contribute the
following:

- An end-to-end open-source civilization simulator that integrates demographic
  and economic micro-simulation with LLM-driven agent cognition under a
  permissive license.
- A bilingual scientific whitepaper (English and Italian) maintained as a
  living document and frozen at each merge to the development branch, with
  every formula, parameter, and algorithm cited to a primary source.
- A canonical seven-phase development workflow with mandatory adversarial
  scientific audits that must reach explicit convergence before any
  scientific module is merged.
- A reproducibility infrastructure built on era templates, seeded
  pseudo-random number generation, and frozen-at-commit references, so that
  any reported result can be regenerated from a known state.
- A modular architecture in which audited modules (currently demographic
  mortality, fertility, and couple formation) and designed-but-unaudited
  modules coexist behind explicit status headers, allowing readers to
  distinguish converged science from work in progress.

## 1.4 Document structure and status legend

This whitepaper complements the maturity legend introduced in the front
matter (see *Document structure and status legend* above) with explicit
cross-references in each chapter. Chapter 2 reviews related work in
agent-based modeling, LLM-driven simulation, demographic micro-simulation,
economic agent-based models, and reputation and information diffusion.
Chapter 3 describes the system architecture: tick engine, agent decision
pipeline, cross-module integration contracts, RNG strategy, LLM provider
adapter, the economic substrate, the persistence model, and the interaction
layer. Chapter 4 contains the audited methods, with one section per
converged module. Chapter 5 documents the implementation — repository
layout, module-to-spec mapping, persistence details. Chapter 6 covers
calibration (parameter tables, era templates, fitting procedures) and
Chapter 7 the validation methodology (target datasets, comparison metrics,
acceptance thresholds, reproducibility commands, status). Chapter 8 lists
subsystems that are implemented but whose adversarial audit is still
pending. Chapter 9 sets out the roadmap, Chapter 10 discusses scope and
design choices, Chapter 11 catalogues known limitations, Chapter 12
concludes. Chapter 13 collects all references and Chapter 14 holds the
appendices (parameter tables, reproducibility instructions, era template
schema).

---

# 2. Background and Related Work

## 2.1 Agent-based modeling of societies

The lineage of social agent-based modeling (ABM) predates the term itself.
Schelling demonstrated that mild individual preferences over neighborhood
composition aggregate into sharp residential segregation, an early example
of macroscopic social pattern emerging from local interaction rules
(Schelling 1971). Axelrod's tournaments on the iterated Prisoner's Dilemma
showed that cooperative strategies can be evolutionarily stable in
populations of self-interested agents, establishing simulation as a
legitimate instrument for social-theoretical inquiry alongside formal proof
and empirical observation (Axelrod 1984). With Sugarscape, Epstein and
Axtell argued for a generative methodology — "if you didn't grow it, you
didn't explain it" — and produced the first widely cited demonstration that
demography, trade, conflict, and cultural transmission could be studied
inside a single artificial society (Epstein and Axtell 1996). Bonabeau later
consolidated the methodology and identified the conditions under which ABM
adds value over equation-based approaches: heterogeneous agents,
non-linearity, and explicit spatial or network structure (Bonabeau 2002).

The maturation of ABM as a discipline coincided with the appearance of
general-purpose modeling platforms. NetLogo became a de facto standard for
pedagogy and small-to-medium models thanks to its accessible language and
extensive model library (Wilensky 1999). Mesa brought a comparable workflow
to the Python scientific stack and is increasingly used where models must
interoperate with statistical and machine-learning libraries (Masad and
Kazil 2015). Repast HPC extended the Repast family to distributed-memory
clusters, enabling populations large enough to approach demographic-scale
questions (Collier and North 2013). These platforms, however, share an
implicit assumption that agent decision-making is rule-based — a finite set
of conditions and actions, possibly stochastic, but ultimately legible as
code. Epocha is positioned as a long-horizon, multi-scale agent-based
simulator that retains this rule-based scaffolding for demographic and
economic dynamics and inserts an LLM-driven decision module where
personality, narrative deliberation, and free-form reasoning are essential.

## 2.2 LLM-driven simulations and the role of personality

A second line of work, much more recent, uses large language models as the
cognitive substrate of simulated agents. Park and colleagues introduced
generative agents in the Smallville environment, in which 25 LLM-driven
characters maintained memory streams, periodic reflections, and plans, and
were observed to coordinate locally over short simulated horizons such as
organizing a Valentine's Day party (Park et al. 2023). Argyle et al.
proposed treating LLMs as a "silicon sample" of human respondents,
showing that, when carefully conditioned on demographic backstories, GPT-3
reproduces non-trivial response distributions from American National
Election Studies surveys (Argyle et al. 2023). Aher, Arriaga, and Kalai
generalized the approach with the notion of a Turing Experiment, an
empirical protocol in which an LLM is asked to replicate the participant
side of well-known psychological studies; their findings indicate that
several classic effects (ultimatum-game offers, Milgram-style obedience
patterns, Wisdom-of-Crowds aggregation) are recovered to a measurable
extent (Aher et al. 2023). Across these studies the role of *personality* —
conveyed via prompted persona, demographic backstory, or explicit
psychometric trait vector — appears to be a primary lever on the diversity
and plausibility of agent behavior. Big Five trait conditioning is the most
widespread choice, both for its standardization in psychology and its
compactness as a five-dimensional input.

The same studies expose the limits of LLM-driven simulation. Cognition
inherits the hallucination tendencies and prompt sensitivity of the
underlying model; reasoning quality degrades with context length; cost
scales with population size and simulated horizon, making century-long
runs at population scale economically prohibitive without aggressive
caching. Reproducibility is also fragile, since model versions evolve and
sampling stochasticity is rarely fully controllable. Epocha mitigates these
constraints with an architecture in which LLM calls are confined to the
narrow decisions where free-form reasoning is genuinely required, while
demographic transitions, economic accounting, and matching are handled by
audited rule-based services described in Chapter 4. A reputation and memory
cache (Castelfranchi et al. 1998) reduces context drift across ticks by
giving agents a structured episodic substrate they can reference instead
of re-deriving social information from scratch. Reproducibility is enforced
at the simulation boundary through seeded pseudo-random number generation,
era templates frozen at commit, and provider-level call logging documented
in Chapter 3.

## 2.3 Demographic micro-simulation

Demographic modeling spans three methodological registers. Macro-demography
operates on aggregate cohorts via difference equations or life tables and
remains the workhorse of national statistical offices. Micro-simulation
follows individuals through life events sampled from estimated transition
intensities and emerged in the late twentieth century as the natural
response to questions — kin networks, household composition, longitudinal
inequality — that aggregate models cannot answer (van Imhoff and Post
1998; Spielauer 2011). The Berkeley SOCSIM line opened the field with a
microsimulation study of incest taboos and demonstrated that
individual-level stochastic modeling could deliver substantive demographic
results (Hammel et al. 1979); subsequent open-source implementations such
as MicSim brought continuous-time microsimulation into the R ecosystem
and codified a generic event-history workflow (Zinn 2013). Agent-based
demography, the third register, embeds the same individual-level
transitions inside a behavioral substrate where decisions on partnership,
fertility, and migration co-evolve with the rest of the simulated society
rather than being drawn from exogenous schedules. The lineage of the
underlying functional forms is well established: Gompertz introduced the
exponential law of mortality at adult ages (Gompertz 1825), Heligman and
Pollard later proposed an eight-parameter additive decomposition that
captures infant, accident-hump, and senescent components in a single
schedule (Heligman and Pollard 1980), Coale and Trussell formalized model
fertility schedules indexed by spacing and stopping behavior (Coale and
Trussell 1974), Hadwiger had earlier offered a compact analytic shape for
age-specific fertility rates (Hadwiger 1940), and Hajnal characterized the
European marriage pattern that motivates much of contemporary nuptiality
research (Hajnal 1965).

Epocha sits in the agent-based register. Mortality is implemented through
the audited Heligman-Pollard schedule with era-specific parameters,
fertility uses a Hadwiger age-specific rate modulated by Becker-style
quantity-quality trade-offs and a Malthusian carrying-capacity ceiling,
and couple formation uses a Gale-Shapley matching with Goode-style
preference functions (see Chapter 4 for the full Methods specification).
The microsimulation literature provides the validation targets — life
table residuals, total fertility rate by cohort, age-at-first-marriage
distributions — against which the audited modules are calibrated, while
the agent-based framing supplies the integration with economic and
behavioral state that purely demographic micro-simulators do not offer.

## 2.4 Economic agent-based models

Macroeconomic agent-based modeling matured in the 2000s as a response to
the perceived limits of representative-agent dynamic stochastic general
equilibrium models. EURACE assembled a continental-scale heterogeneous
agent platform with explicit household, firm, bank, and government
populations, designed to study credit channels and policy transmission
without imposing equilibrium ex ante (Deissenberg et al. 2008). JAMEL
introduced wage-flexibility experiments inside an agent-based model with
endogenous money creation, providing a numerical counter-example to the
classical claim that wage flexibility unconditionally stabilizes
employment (Seppecher 2012). The Mark0 family of stylized macroeconomic
models, by contrast, deliberately stripped the institutional detail to
expose tipping points and phase transitions in collective economic
behavior, treating the macroeconomy as a complex system in the
statistical-physics sense (Gualdi et al. 2015). The strength of these
platforms is the ability to generate out-of-equilibrium dynamics —
endogenous business cycles, balance-sheet recessions, distributional
tail behavior — from heterogeneous interactions; the recurring weakness
is calibration and identification, since the parameter space is large and
the available macroeconomic time series are short relative to the
behavioral richness on offer.

Behavioral economics provides complementary primitives that have proven
durable enough to be reused across model families. Cagan's adaptive
expectations remain the simplest non-trivial way to give agents a
backward-looking forecast that converges under stable regimes and
amplifies shocks otherwise (Cagan 1956). The Diamond-Dybvig model of
banking under sequential service exposes the run equilibrium that
short-term liquid liabilities financing illiquid assets cannot avoid
without an external commitment device, and motivates the explicit modeling
of deposit guarantees and lender-of-last-resort behavior (Diamond and
Dybvig 1983). Minsky's financial-instability hypothesis frames the
endogenous build-up of fragility during prolonged tranquil expansions and
is the canonical reference for cycle-aware credit modeling (Minsky 1986).
Epocha's Plan 2 economic layer is positioned within this lineage: it
reuses the EURACE/JAMEL commitment to heterogeneous balance sheets and
out-of-equilibrium clearing, adopts Cagan adaptive expectations for
inflation forecasting, instantiates a Diamond-Dybvig banking core with
fractional reserves, and is structured to admit Minsky-style cycle
indicators as an extension. The complete Methods specification for the
behavioral integration is in Chapter 4.

## 2.5 Reputation and information diffusion in MAS

Reputation is the social-cognitive construct that lets agents act on
secondhand information about partners they have not directly interacted
with, and it is foundational for cooperation in open multi-agent systems.
Conte and Paolucci provided the consolidated theoretical treatment,
distinguishing image (a private evaluative belief) from reputation (the
social object that circulates through gossip and underwrites norm
enforcement) (Conte and Paolucci 2002). The earlier Castelfranchi, Conte,
and Paolucci formulation analyzed how normative reputation lowers the
cost of compliance and supplies an endogenous mechanism for social order
(Castelfranchi et al. 1998). Information diffusion sits adjacent to
reputation, and its empirical foundations predate the multi-agent
literature: Allport and Postman established the embedding-leveling-
sharpening dynamic of rumor transmission and identified the basic law
relating rumor intensity to the product of importance and ambiguity
(Allport and Postman 1947), while Bartlett's serial-reproduction
experiments showed that successive retellings of a narrative converge
toward culturally familiar schemas rather than preserving source content
(Bartlett 1932). Epocha's reputation module implements the
Castelfranchi-Conte-Paolucci normative model and is treated as a
deferred-Methods item pending Round 2 audit; it is documented in
Chapter 8.5 alongside the rumor and information-flow clusters that draw
on the Allport-Postman and Bartlett tradition.

---

# 3. System Architecture

## 3.1 Tick engine and time scales

<draft in Task 5>

## 3.2 Agent decision pipeline (Big Five + memory + LLM)

<draft in Task 5>

## 3.3 Cross-module integration contracts (treasury, subsistence, outlook)

<draft in Task 5>

## 3.4 RNG strategy and reproducibility

<draft in Task 5>

## 3.5 LLM provider adapter and rate limiting

<draft in Task 6>

## 3.6 Economic substrate (production, monetary, market clearing, distribution)

<draft in Task 6 — note: descriptive, NOT Methods-grade>

## 3.7 Persistence model

<draft in Task 6>

## 3.8 Interaction layer (Dashboard, Chat WebSocket)

<draft in Task 6>

---

# 4. Methods — Audited Modules

## 4.1 Demography

> Status: implemented as of commit `<filled-on-merge>`, spec audit CONVERGED 2026-04-18 round 4.

<draft in Tasks 8-13>

### 4.1.1 Mortality model (Heligman-Pollard)

<draft in Task 8>

### 4.1.2 Fertility model (Hadwiger ASFR + Becker modulation + Malthusian ceiling)

<draft in Task 10>

### 4.1.3 Couple formation and dissolution (Gale-Shapley + Goode 1963)

<draft in Task 12>

## 4.2 Economy — Behavioral integration

> Status: implemented as of commit `<filled-on-merge>`, spec audit CONVERGED 2026-04-15.

<draft in Tasks 14-19>

### 4.2.1 Adaptive expectations (Cagan 1956)

<draft in Task 14>

### 4.2.2 Credit and banking (Diamond-Dybvig 1983, fractional reserve)

<draft in Task 16>

### 4.2.3 Property market

<draft in Task 18>

---

# 5. Implementation

<draft in Task 20>

## 5.1 Repository layout

<draft in Task 20>

## 5.2 Module-to-spec mapping

<draft in Task 20>

## 5.3 LLM provider adapter and rate limiting

<draft in Task 20>

## 5.4 Persistence model details

<draft in Task 20>

---

# 6. Calibration

<draft in Task 21>

## 6.1 Parameter tables per audited module

<draft in Task 21>

## 6.2 Era templates and tunable heuristics

<draft in Task 21>

## 6.3 Fitting procedures

<draft in Task 21>

---

# 7. Validation Methodology

> Status: validation experiments specified, not yet executed. Execution is tracked as a separate follow-up (see project memory `project_validation_experiments_pending.md`).

<draft in Task 22>

## 7.1 Target datasets per audited module

<draft in Task 22>

## 7.2 Comparison metrics

<draft in Task 22>

## 7.3 Acceptance thresholds

<draft in Task 22>

## 7.4 Reproducibility commands

<draft in Task 22>

## 7.5 Status

<draft in Task 22>

---

# 8. Designed Subsystems (implemented, audit pending)

<draft in Task 23>

## 8.1 Cluster: Rumor propagation (Information Flow + Distortion + Belief Filter)

<draft in Task 23>

## 8.2 Cluster: Political institutions (Government + Institutions + Stratification)

<draft in Task 23>

## 8.3 Movement

<draft in Task 23>

## 8.4 Factions

<draft in Task 23>

## 8.5 Reputation (Castelfranchi et al. 1998)

<draft in Task 23>

## 8.6 Knowledge Graph

<draft in Task 23>

## 8.7 Economy base layer

<draft in Task 23>

---

# 9. Roadmap

<draft in Task 24>

---

# 10. Discussion

<draft in Task 25>

---

# 11. Known Limitations

<draft in Task 26>

---

# 12. Conclusions

<draft in Task 27>

---

# 13. References

- Aher, G. V., Arriaga, R. I., and Kalai, A. T. (2023). Using large
  language models to simulate multiple humans and replicate human
  subject studies. In *Proceedings of the 40th International Conference
  on Machine Learning (ICML 2023)*, PMLR, 202, 337–371.
  https://proceedings.mlr.press/v202/aher23a.html
<!-- VERIFICATION PENDING: ISBN of the 1947 Henry Holt & Co. first edition not verified against a primary source (Worldcat blocked, Crossref has no record for the monograph). Task 7 to reconcile. -->
- Allport, G. W., and Postman, L. (1947). *The Psychology of Rumor*.
  Henry Holt and Company, New York.
- Argyle, L. P., Busby, E. C., Fulda, N., Gubler, J. R., Rytting, C., and
  Wingate, D. (2023). Out of one, many: using language models to simulate
  human samples. *Political Analysis*, 31(3), 337–351.
  https://doi.org/10.1017/pan.2023.2
<!-- VERIFICATION PENDING: 1951 Gnome Press fix-up vs original 1942 Astounding Science Fiction story (May 1942 issue, "Foundation"). Task 7 to reconcile -->
- Asimov, I. (1951). *Foundation*. Gnome Press, New York.
- Axelrod, R. (1984). *The Evolution of Cooperation*. Basic Books, New
  York. ISBN 978-0-465-02121-5.
<!-- VERIFICATION PENDING: ISBN of the 1932 Cambridge University Press first edition not verified against a primary source (Worldcat blocked, Crossref has no record for the monograph). Task 7 to reconcile. -->
- Bartlett, F. C. (1932). *Remembering: A Study in Experimental and
  Social Psychology*. Cambridge University Press, Cambridge.
- Bonabeau, E. (2002). Agent-based modeling: methods and techniques for
  simulating human systems. *Proceedings of the National Academy of
  Sciences*, 99(Suppl. 3), 7280–7287.
  https://doi.org/10.1073/pnas.082080899
<!-- VERIFICATION PENDING: chapter pagination in the Friedman 1956 edited volume not verified (no DOI for the chapter). Task 7 to reconcile. -->
- Cagan, P. (1956). The monetary dynamics of hyperinflation. In M.
  Friedman (ed.), *Studies in the Quantity Theory of Money*. University
  of Chicago Press, Chicago, 25–117.
- Castelfranchi, C., Conte, R., and Paolucci, M. (1998). Normative
  reputation and the costs of compliance. *Journal of Artificial
  Societies and Social Simulation*, 1(3).
  https://www.jasss.org/1/3/3.html
- Coale, A. J., and Trussell, T. J. (1974). Model fertility schedules:
  variations in the age structure of childbearing in human populations.
  *Population Index*, 40(2), 185–258.
  https://doi.org/10.2307/2733910
- Collier, N., and North, M. J. (2013). Parallel agent-based simulation
  with Repast for High Performance Computing. *SIMULATION*, 89(10),
  1215–1235. https://doi.org/10.1177/0037549712462620
<!-- VERIFICATION PENDING: ISBN of the 2002 Kluwer Academic Publishers edition not verified against a primary source (Springer/Worldcat lookup failed). Task 7 to reconcile. -->
- Conte, R., and Paolucci, M. (2002). *Reputation in Artificial Societies:
  Social Beliefs for Social Order*. Kluwer Academic Publishers, Boston.
- Deissenberg, C., van der Hoog, S., and Dawid, H. (2008). EURACE: a
  massively parallel agent-based model of the European economy.
  *Applied Mathematics and Computation*, 204(2), 541–552.
  https://doi.org/10.1016/j.amc.2008.05.116
- Diamond, D. W., and Dybvig, P. H. (1983). Bank runs, deposit insurance,
  and liquidity. *Journal of Political Economy*, 91(3), 401–419.
  https://doi.org/10.1086/261155
- Epstein, J. M., and Axtell, R. (1996). *Growing Artificial Societies:
  Social Science from the Bottom Up*. Brookings Institution Press /
  MIT Press, Washington, DC and Cambridge, MA. ISBN 978-0-262-55025-3.
- Gompertz, B. (1825). On the nature of the function expressive of the
  law of human mortality, and on a new mode of determining the value of
  life contingencies. *Philosophical Transactions of the Royal Society
  of London*, 115, 513–583. https://doi.org/10.1098/rstl.1825.0026
- Gualdi, S., Tarzia, M., Zamponi, F., and Bouchaud, J.-P. (2015).
  Tipping points in macroeconomic agent-based models. *Journal of
  Economic Dynamics and Control*, 50, 29–61.
  https://doi.org/10.1016/j.jedc.2014.08.003
<!-- VERIFICATION PENDING: original German title and pagination in Skandinavisk Aktuarietidskrift 23 (1940) not verified against a primary source. Task 7 to reconcile. -->
- Hadwiger, H. (1940). Eine analytische Reproduktionsfunktion für
  biologische Gesamtheiten. *Skandinavisk Aktuarietidskrift*, 23,
  101–113.
<!-- VERIFICATION PENDING: chapter pagination in Glass and Eversley (eds.) Population in History (1965) not verified against a primary source. Task 7 to reconcile. -->
- Hajnal, J. (1965). European marriage patterns in perspective. In D. V.
  Glass and D. E. C. Eversley (eds.), *Population in History: Essays in
  Historical Demography*. Edward Arnold, London, 101–143.
- Hammel, E. A., McDaniel, C. K., and Wachter, K. W. (1979). Demographic
  consequences of incest tabus: a microsimulation analysis. *Science*,
  205(4410), 972–977. https://doi.org/10.1126/science.205.4410.972
- Heligman, L., and Pollard, J. H. (1980). The age pattern of mortality.
  *Journal of the Institute of Actuaries*, 107(1), 49–80.
  https://doi.org/10.1017/S0020268100040257
- Masad, D., and Kazil, J. (2015). Mesa: an agent-based modeling framework.
  In *Proceedings of the 14th Python in Science Conference (SciPy 2015)*,
  51–58. https://doi.org/10.25080/Majora-7b98e3ed-009
<!-- VERIFICATION PENDING: ISBN of the 1986 Yale University Press first edition not verified against a primary source (Worldcat blocked). Task 7 to reconcile. -->
- Minsky, H. P. (1986). *Stabilizing an Unstable Economy*. Yale
  University Press, New Haven.
- Park, J. S., O'Brien, J. C., Cai, C. J., Morris, M. R., Liang, P., and
  Bernstein, M. S. (2023). Generative agents: interactive simulacra of
  human behavior. In *Proceedings of the 36th Annual ACM Symposium on
  User Interface Software and Technology (UIST '23)*. ACM.
  https://doi.org/10.1145/3586183.3606763
- Schelling, T. C. (1971). Dynamic models of segregation. *Journal of
  Mathematical Sociology*, 1(2), 143–186.
  https://doi.org/10.1080/0022250X.1971.9989794
- Seppecher, P. (2012). Flexibility of wages and macroeconomic
  instability in an agent-based computational model with endogenous
  money. *Macroeconomic Dynamics*, 16(S2), 284–297.
  https://doi.org/10.1017/S1365100511000447
- Spielauer, M. (2011). What is social science microsimulation?
  *Social Science Computer Review*, 29(1), 9–20.
  https://doi.org/10.1177/0894439310370085
<!-- VERIFICATION PENDING: Population: An English Selection vol/pages and JSTOR identifier not verified directly; the publication is confirmed (Population, vol. 53, HS1, 97–136, December 1998) but the canonical English-Selection variant pages should be reconciled in Task 7. -->
- van Imhoff, E., and Post, W. (1998). Microsimulation methods for
  population projection. *Population: An English Selection*, 10, 97–138.
- Wilensky, U. (1999). NetLogo. Center for Connected Learning and
  Computer-Based Modeling, Northwestern University, Evanston, IL.
  http://ccl.northwestern.edu/netlogo/
- Zinn, S. (2013). The MicSim package of R: an entry-level toolkit for
  continuous-time microsimulation. *International Journal of
  Microsimulation*, 7(3), 3–32.
  https://doi.org/10.34196/ijm.00105

---

# 14. Appendices

## Appendix A — Full parameter tables

<draft in Task 28>

## Appendix B — Reproducibility

<draft in Task 29>

## Appendix C — Era templates JSON schema and source

<draft in Task 29>

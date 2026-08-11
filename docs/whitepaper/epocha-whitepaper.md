---
title: "Epocha — A Scientifically Grounded Civilization Simulator"
authors: ["Maurizio Mocci"]
affiliation: "Independent project"
date: "2026-04-26"
version: "0.1"
frozen-at-commit: "1cdcfa4fe23138727c16a2e92234e4eb962d9ae7"
license: "Apache 2.0"
---

# Epocha — A Scientifically Grounded Civilization Simulator

## Abstract

Epocha is an open-source civilization simulator that combines large-scale
agent-based modeling with LLM-driven cognition under the long-horizon,
multi-scale ambition of Asimov's psychohistory. The project addresses a gap
between two adjacent research traditions: established demographic and
economic micro-simulators support populations of millions over decades but
rely on rule-based agents that lack persistent personality, episodic memory,
and natural-language deliberation, while recent LLM agent simulations
endow agents with rich cognition but operate over small groups, short
horizons, and stylised environments without an underlying demographic or
economic substrate. The whitepaper documents the system architecture (tick
engine, agent decision pipeline, RNG strategy, LLM provider adapter,
economic substrate, persistence model, dashboard and chat layer), the
audited scientific modules — Heligman-Pollard mortality, Hadwiger-with-Becker
fertility, Gale-Shapley with Goode 1963 couple formation, Cagan-Nerlove
adaptive expectations, Diamond-Dybvig credit and banking, a
Gordon-anchored property market, Castelfranchi-Conte-Paolucci reputation,
Bartlett-Allport-Postman rumor propagation (information flow, distortion,
belief filter, affinity), the political-institutions cluster
(government, government_types, institutions, stratification, election),
movement, and factions —
an audited economy base layer covering CES production, Walrasian
tâtonnement clearing, a conserved factor-income partition, and the
Fisher conservation diagnostic,
and one subsystem implemented in code but awaiting adversarial
scientific audit (knowledge graph). Every formula, parameter, and algorithm in the audited
chapters is cited to a primary source; calibration tables are presented per
era template and consolidated in Appendix A; the validation methodology
specifies datasets, metrics, and acceptance thresholds against which Plan 4
will execute the empirical campaign. Reproducibility infrastructure covers the
non-LLM part of the system — era templates, per-phase seeded RNG streams for
the demographic and economic services, frozen-at-commit references, and a
bilingual scientific whitepaper maintained as a living document; the
LLM-driven agent decisions and world generation are not seed-reproducible.
The project is released under Apache 2.0, with a canonical seven-phase
development workflow and mandatory adversarial audits gating every merge to
the development branch.

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
personality-rich cognition, while remaining auditable, reproducible in its
non-LLM part, and grounded in primary scientific sources.

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
  pseudo-random number generation for the non-LLM services, and
  frozen-at-commit references, so that any reported result that depends
  only on the seeded part can be regenerated from a known state; results
  that depend on LLM agent decisions or world generation are not
  seed-reproducible.
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
the one subsystem that is implemented but whose adversarial audit is still
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
of re-deriving social information from scratch. Reproducibility of the non-LLM
part is enforced at the simulation boundary through seeded pseudo-random
number generation, era templates frozen at commit, and provider-level call
logging documented in Chapter 3; the LLM decisions themselves, sampled at
non-zero temperature without a seed, remain the fragile part noted above.

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
Castelfranchi-Conte-Paolucci normative model and is documented as audited
Methods content in Chapter 4.3 following Round 2 audit convergence on
2026-05-12; the rumor and information-flow clusters that draw on the
Allport-Postman and Bartlett tradition are documented as audited Methods
content in Chapter 4.4 following Round 2 audit convergence on 2026-05-16.

---

# 3. System Architecture

## 3.1 Tick engine and time scales

The simulation advances in discrete ticks. Each tick is interpreted by the
configured era template as one calendar month, year, or decade — the
calibration constants of the demography and economy modules are themselves
expressed against this nominal step, so changing the time scale changes the
parameter set rather than the engine. A tick is atomic: the orchestrator
runs the economy update first, then a Celery chord dispatches one
`process_agent_turn` task per living agent in parallel, then the chord
callback `finalize_tick` runs information flow, faction dynamics, the
political cycle, relationship and memory decay, captures a snapshot,
detects epochal crises, advances the tick counter, broadcasts to connected
WebSocket clients, and finally re-enqueues `run_simulation_loop` with a
countdown derived from the simulation speed multiplier (see
`epocha/apps/simulation/tasks.py`). Re-enqueuing rather than long-polling
keeps every tick a fresh task whose lifetime matches its work, which lets
the broker survive worker restarts without losing the simulation. Within a
tick the order of agents is deterministic — the chord header is built from
`Agent.objects.filter(...).values_list("id", flat=True)`, whose ordering is
the model's default primary key sequence — so any non-determinism comes
from the LLM call and the per-tick seeded RNG streams documented in §3.4,
never from scheduling. A real-time event-driven design was rejected because
discrete ticks are the natural granularity of the demographic and economic
literature the calibration draws on (Heligman and Pollard 1980, Hadwiger
1940), because per-tick reproducibility of the non-LLM services is the contract the
validation suite of Chapter 7 depends on, and because chord-based parallelism scales
horizontally on Celery workers without locking shared state.

```
tick N      pre-snapshot ──> economy tick ──> chord(process_agent_turn × N agents)
                                                            │
                                                            ▼
                                              finalize_tick callback
                                                            │
                                                            ▼
            information flow ──> factions ──> politics ──> relationship/memory decay
                                                            │
                                                            ▼
            post-snapshot + crisis detection ──> tick counter ++ ──> WebSocket broadcast
                                                            │
                                                            ▼
                                              re-enqueue run_simulation_loop (tick N+1)
```

## 3.2 Agent decision pipeline (Big Five + memory + LLM)

Each living agent goes through a four-stage pipeline implemented in
`epocha/apps/agents/decision.py::process_agent_decision`. Stage one
gathers context: the top-k relevant memories (ranked by emotional weight
descending, then recency descending, in
`epocha/apps/agents/memory.py::get_relevant_memories`), the agent's outgoing
relationships, recent injected events, the enumerated list of valid
interaction targets, and optional faction, political, reputation, zone, and
economic context blocks. Stage two assembles the user prompt from these
fragments. Stage three builds the system prompt by concatenating the
Big Five personality description produced by
`epocha/apps/agents/personality.py::build_personality_prompt` with the
era-filtered action vocabulary returned by `_build_system_prompt`; the Big
Five trait values map to natural-language descriptors using cutoffs at 0.3
and 0.7, following the five-factor model validated across instruments and
observers (McCrae and Costa 1987). Stage four calls the LLM through the
provider-agnostic adapter (Chapter 3.5), strips markdown fences from the
response, parses the JSON action with a fallback to `{"action": "rest",
"reason": "confused"}` when the LLM returns malformed output, and persists
the full input context and parsed action to a `DecisionLog` row for replay
and offline auditing.

Memories are written by `apply_agent_action` with an emotional weight drawn
from a per-action lookup table (for example 0.8 for `betray`, 0.7 for
`pair_bond`, 0.05 for `rest`); high-weight memories survive much longer
because the decay routine in `memory.py::decay_memories` dampens the
forgetting rate by `1 + 5 × emotional_weight` and exempts memories with
weight ≥ 0.6 from decay entirely, modeling the consolidation effect that
Brown and Kulik called flashbulb memories (Brown and Kulik 1977). The
description above places the decision pipeline, the personality module, and
the memory module in this chapter rather than in Chapter 4 because their
implementations have not yet completed Round 2 of the adversarial spec
audit demanded by the project's scientific-method rule. They will be
promoted to Methods (Chapter 4) when that audit converges; the architecture
description here is sufficient to follow the rest of the document but is
not Methods-grade.

## 3.3 Cross-module integration contracts (treasury, subsistence, outlook)

Three explicit functions form the contract surface between demography and
the economy/world subsystems. They were extracted from inline mutations and
ad hoc lookups during Demography Plan 1 to make integration boundaries
testable in isolation and auditable as a single point of dependency
between subsystems. Implicit globals were rejected because they hide the
coupling and make the demography module impossible to test without booting
a full economy.

| Contract | Signature | Semantics | Caller / Implementer |
|----------|-----------|-----------|----------------------|
| Treasury credit | `add_to_treasury(government, currency_code, amount)` in `epocha/apps/world/government.py` | Adds `amount` of `currency_code` to `government.government_treasury` (a JSON map from currency code to balance) and persists the row. | Called from `epocha/apps/economy/engine.py` (taxation), from `epocha/apps/economy/property_market.py` (sale proceeds of an ownerless government/public property), and from inheritance/estate-tax logic in the demography subsystem; implemented in `world/government.py`. |
| Subsistence threshold | `compute_subsistence_threshold(simulation, zone)` in `epocha/apps/demography/context.py` | Returns the per-agent per-tick wealth flow needed to consume essential goods at the zone's current market prices, using `GoodCategory.is_essential` and the `SUBSISTENCE_NEED_PER_AGENT` constant from `economy/market.py`. | Called by `demography/fertility.py::becker_modulation`; implemented in `demography/context.py`. |
| Aggregate outlook | `compute_aggregate_outlook(agent)` in `epocha/apps/demography/context.py` | Returns a scalar in `[-1, 1]` summarizing the agent's economic perception as the equally-weighted average of agent mood, banking confidence, and government stability, each rescaled from `[0, 1]` to `[-1, 1]`. Documented as a tunable design heuristic, not derived from Jones and Tertilt (2008). | Called by `demography/fertility.py::becker_modulation`; implemented in `demography/context.py`. |

## 3.4 RNG strategy and reproducibility

All stochastic decisions in the demography subsystem draw from per-stream
seeded random number generators rather than the process-wide
`random.random`. The helper
`epocha/apps/demography/rng.py::get_seeded_rng(simulation, tick, phase)`
returns a fresh `random.Random` whose seed is the first eight bytes of
`sha256(f"{simulation.id}:{simulation.seed}:{tick}:{phase}")`. The phase
label must belong to a closed set (`mortality`, `fertility`, `couple`,
`migration`, `inheritance`, `initialization`); an unknown label raises
`ValueError` to prevent silent stream collisions. Per-stream isolation is
deliberate: reordering or suppressing the mortality routine in a refactor
must not shift the random sequence that fertility, couple formation, or
inheritance see at the same tick, otherwise reproducibility across
refactors collapses. Given the commit hash of the codebase, the
`simulation.seed`, and the initial state of the database, the non-LLM part
of every tick — the seeded demographic and economic services — is
deterministic and reproducible across machines. The per-agent decisions are
not: each is an LLM call at `temperature=0.7` with no seed
(`agents/decision.py:381`), so the decision an agent takes on a given tick
is not reproducible even from an identical seed and database state. The
seed governs what `simulation/models.py:35` names the "non-LLM part", not
the LLM sampling. One known debt is
tracked as A-5 for Plan 4: when both `simulation.seed` and `simulation.id`
are `None`, the RNG helper falls back to `0` for both, so two unsaved
simulations with no explicit seed running the same tick draw identical
streams. The condition is rare in practice (`simulation.id` is `None` only
between `Simulation()` instantiation and `.save()`), but the fix is to
require an explicit seed at simulation creation time.

## 3.5 LLM provider adapter and rate limiting

The adapter exposes a single `BaseLLMProvider` interface
(`epocha/apps/llm_adapter/providers/base.py`) implemented by an
`OpenAIProvider` (`providers/openai.py`) that targets any endpoint
honoring the OpenAI chat completions schema. The same class therefore
serves OpenAI proper, Google Gemini, Groq, OpenRouter, Together AI,
Mistral, and locally hosted runners such as LM Studio and Ollama: only
the `base_url`, model identifier, and key change. Configuration lives
in `config/settings/base.py` under `EPOCHA_DEFAULT_LLM_PROVIDER`,
`EPOCHA_LLM_API_KEY`, `EPOCHA_LLM_MODEL`, and `EPOCHA_LLM_BASE_URL`,
with a parallel `EPOCHA_CHAT_LLM_*` set used by `get_chat_llm_client()`
for agent conversations; when the chat provider is configured it is
wrapped in a `FallbackProvider` that transparently rolls over to the
main provider on failure. Two complementary defenses guard against
quota exhaustion. Inside `OpenAIProvider`, `EPOCHA_LLM_API_KEY` accepts
a comma-separated list of keys: when a `RateLimitError` (HTTP 429)
exhausts the in-call retry budget (three retries with exponential
backoff at base two seconds, see `_MAX_RETRIES` and
`_RETRY_BASE_DELAY_SECONDS`) the provider rotates to the next key
before re-raising. This is the mechanism currently used to spread
load across multiple Groq free-tier keys, but the rotation is generic
and supports any number of keys. At the process level,
`epocha/apps/llm_adapter/rate_limiter.py` provides a Redis-backed
sliding window counter (one minute TTL, default 50 requests per
minute per provider) usable by orchestration code that needs to throttle
ahead of the provider's own limit. Per-call accounting is persisted in
the `LLMRequest` model (provider, model, token counts, USD cost,
latency, success flag, optional `simulation_id`); pricing is derived
from a per-model table in `providers/openai.py` with a conservative
default for unlisted models.

## 3.6 Economic substrate (production, monetary, market clearing, distribution)

The economy app under `epocha/apps/economy/` collects the modules that
turn agent activity into production, prices, money, and income flows.
`production.py` implements a Constant Elasticity of Substitution (CES)
production function in the form
`Q = A · [Σ αᵢ Xᵢ^ρ]^(1/ρ)` with `ρ = (σ-1)/σ` and falls back to the
Cobb-Douglas log form near `σ = 1` and to a Leontief minimum near
`σ = 0` to avoid the numerical singularity. The CES form is the
classical generalization introduced by Arrow et al. (1961), with the
multi-factor extension following standard applied CGE practice
(Shoven and Whalley 1992). `market.py` clears each zone-local market
through Walrasian tâtonnement (Walras 1874): given supply, demand,
and current prices, prices are nudged proportionally to excess demand
until either the relative excess falls below a convergence threshold
or a configurable iteration cap is reached. The cap is the explicit
safety net for the well-known non-convergence regime with three or
more goods (Scarf 1960). The remaining modules cover the rest of the
substrate: `monetary.py` keeps a velocity counter and a Fisher
identity check used as a diagnostic rather than as a price rule;
`distribution.py` derives rent in a simplified Ricardian fashion plus
a flat wage and tax flow; `banking.py` and `credit.py` wrap a single
aggregate banking sector that adjusts the base rate through a
Wicksellian feedback (Wicksell 1898) and tracks loan defaults with
breadth-first cascade propagation (Minsky 1986; Stiglitz and Weiss
1981); `expectations.py`, `political_feedback.py`, and
`property_market.py` connect the economy to agents and to the
political loop.

The substrate summarized here completed its adversarial scientific
audit (twelve rounds, converged 2026-07-16) and is documented at
Methods grade in §4.8, where every formula carries its primary-source
citation and every constant is cited or tagged as a tunable design
parameter. The audited layer that sits on top of this substrate is
the behavioral integration described in §4.2: that integration
consumes the prices, trades, and income flows produced by the
substrate and adds the adaptive expectations, satisficing, and
political feedback.

## 3.7 Persistence model

State is held in PostgreSQL with PostGIS already installed
(`django.contrib.gis` is in `INSTALLED_APPS` and zone geometries are
stored as WGS84 `PolygonField`/`PointField` since migration
`world.0003_zone_postgis_geometry`). Identifier conventions follow
the Django default of 64-bit auto-incrementing integer primary keys,
configured globally via `DEFAULT_AUTO_FIELD =
"django.db.models.BigAutoField"` in `config/settings/base.py`, with
no UUID primary keys at the time of writing; foreign keys throughout
the apps therefore carry integer references. The one notable
deviation from "all positive integers" is the `birth_tick` column on
`agents.Agent` introduced by Plan 1 of the demography spec: it is a
`BigIntegerField` rather than `PositiveIntegerField` precisely so
that pre-existing agents whose age predates the simulation start can
carry a negative birth tick, keeping the canonical age formula
`age = (current_tick − birth_tick) / ticks_per_year` valid across
backfills. Atomic requests are enabled per-database
(`ATOMIC_REQUESTS = True`) to keep API and tick handlers transactional
by default. The migration plan beyond MVP (tracked in
`docs/memory-backup/project_roadmap_post_mvp.md`) is to broaden
PostGIS use beyond zone geometry into agent trajectories and routed
distance queries.

## 3.8 Interaction layer (Dashboard, Chat WebSocket)

Real-time observation goes through Django Channels over Redis. Two
WebSocket routes are exposed:
`ws/simulation/<simulation_id>/` is served by
`epocha/apps/simulation/consumers.py:SimulationConsumer` and pushes
tick-by-tick state to whoever is watching a simulation, while
`ws/chat/<agent_id>/` is served by
`epocha/apps/chat/consumers.py:ChatConsumer` and carries the
synchronous conversation between a human user and one specific agent
(URL patterns in `epocha/apps/{simulation,chat}/routing.py`, integer
IDs because primary keys are `BigAutoField`; see §3.7). The dashboard
itself (`epocha/apps/dashboard/`) is intentionally a server-rendered
Django templates application rather than a single-page app: the base
template `dashboard/base.html` loads Alpine.js from a CDN for small
client-side enrichments such as toggles and live counters, which keeps
the JavaScript footprint and operational complexity proportional to
the project's research focus. Pages cover the simulation list,
detail, analytics, graph, and report views, plus the chat and
group-chat surfaces, all hitting the same Django views and ORM that
back the API.

---

# 4. Methods — Audited Modules

## 4.1 Demography

> Status: implemented as of commit `1cdcfa4fe23138727c16a2e92234e4eb962d9ae7`, spec audit CONVERGED 2026-04-18 round 4.

The demography module covers the five life-course mechanisms for which Epocha currently runs an audited scientific model: mortality, fertility, couple formation, inheritance, and migration. The authoritative specification is `docs/superpowers/specs/2026-04-18-demography-design.md`, whose four rounds of adversarial review converged on 2026-04-18; the design choices and the explicit mapping of every parameter to a primary source live there, while this chapter restates the formulas, the calibration tables, and the per-tick algorithms in publication form. The implementation lives under `epocha/apps/demography/`, where the five subsystems are split into `mortality.py`, `fertility.py`, `couple.py`, `inheritance.py`, and `migration.py`, with shared concerns factored into `template_loader.py` (era JSON loading and validation), `rng.py` (seeded per-phase streams discussed in Chapter 3.4), `context.py` (integration helpers towards the economy), and `models.py` (the persisted demographic state). The design intent is that within each tick the subsystems run in the order mortality → fertility → couple formation, with inheritance settling on the death event and migration running as its own step, each drawing from its own seeded RNG stream so that the order can be reasoned about without coupling to the random sequence — this orchestration is targeted for Plan 4 integration; see status note below. Maternal mortality at childbirth is the one inter-subsystem coupling and is resolved jointly between mortality and fertility before either records its outcome, as detailed in §4.1.2. The first three subsystems were specified and audited together in demography Plans 1 and 2; inheritance and migration were built under Plan 3 and carried their own four-round phase-6 adversarial code audit, which converged on 2026-08-05 over the code as scoped while explicitly leaving eight design-level defects open — those are stated in the Simplifications paragraphs of §4.1.4 and §4.1.5 rather than deferred to a later revision of this chapter. As of the commit pinned in the front matter, all five subsystems are implemented and unit-tested in isolation; their orchestration into the live simulation tick loop in `epocha/apps/simulation/engine.py` is tracked as a Plan 4 deliverable (Initialization, Engine integration, and Historical validation) and is not yet active in production code.

### 4.1.1 Mortality model (Heligman-Pollard)

> Status: implemented as of commit `1cdcfa4fe23138727c16a2e92234e4eb962d9ae7`, spec audit CONVERGED 2026-04-18 round 4.

**Background.** Mortality in Epocha is an age-specific hazard schedule rather than a constant rate, because every downstream demographic indicator the validation suite of Chapter 7 targets — life expectancy at birth, infant-mortality ratio, the survival curve — depends on the shape of the schedule across age, not on its mean. Two simpler alternatives were considered and rejected. A pure Gompertz law (Gompertz 1825) captures only the senescent exponential and underestimates infant and young-adult mortality by orders of magnitude in pre-industrial regimes, where infant mortality drives most of the lost life expectancy. Lee-Carter (Lee and Carter 1992) is a forecasting model on cohort log-rates that operates on aggregate populations and a stationary historical baseline; it is not designed to deliver the per-agent age-conditional hazard a microsimulation tick needs, and applying it at agent scale would require an extra bridging step with no scientific gain over directly evaluating the analytic schedule. The Heligman-Pollard (1980) eight-parameter additive decomposition was retained because it expresses the three observed regimes — childhood decline, young-adult accident hump, senescent rise — in a single closed-form expression that can be evaluated for any agent age in constant time and that admits per-era recalibration by replacing eight numbers.

**Model.** Heligman and Pollard (1980) parameterize the odds of dying at age `x` as the sum of three components:

```
q(x) / p(x) = A^((x + B)^C)                      (4.1)
            + D · exp(-E · (ln(x/F))^2)
            + G · H^x
```

where `q(x)` is the annual probability of death at exact age `x` and `p(x) = 1 − q(x)` is the corresponding survival probability. The first term, controlled by `A`, `B`, `C`, captures the rapid decline of childhood mortality with age. The second term, controlled by `D`, `E`, `F`, captures the so-called accident hump centered at age `F` with peak amplitude `D` and width set by `E`, and is interpreted historically as the excess mortality from accidents, violence, and (for women) maternal causes among young adults. The third term, controlled by `G` and `H`, is the Gompertz exponential law that dominates senescent mortality at older ages. Equation (4.1) is the canonical 1980 form (see Heligman and Pollard 1980, formula 5); the `(ln(x/F))² ≡ (ln x − ln F)²` algebraic equivalence is used in `epocha/apps/demography/mortality.py:_hp_components()` to keep the implementation a direct line-by-line transcription of the textbook expression. Since equation (4.1) returns the odds `q/p`, the implementation converts to a probability by `q = (q/p) / (1 + q/p)` in `annual_mortality_probability()` (mortality.py:45), and clamps the result at `0.999` to keep `(1 − q)` strictly positive for the geometric tick scaling described under Algorithm below.

**Parameters.** The eight HP parameters carry the semantic roles summarized in Table 4.1.

Table 4.1 — Heligman-Pollard parameters: semantics and admissible ranges.

| Symbol | Component       | Semantic role                                                    | Admissible range used in calibration |
|--------|-----------------|------------------------------------------------------------------|--------------------------------------|
| `A`    | childhood       | level of mortality at age 1                                      | `[0, 0.1]`                            |
| `B`    | childhood       | mortality at age 0 relative to age 1 (infancy intercept)         | `[0, 0.5]`                            |
| `C`    | childhood       | rate of decline of childhood mortality with age                  | `[0, 1.0]`                            |
| `D`    | accident hump   | peak amplitude of the young-adult excess mortality               | `[0, 0.05]`                           |
| `E`    | accident hump   | inverse width (sharpness) of the accident hump                   | `[0.1, 50]`                           |
| `F`    | accident hump   | age at which the accident hump is centered (years)               | `[1.0, 50]`                           |
| `G`    | senescence      | level of senescent mortality at age 0 (Gompertz intercept)       | `[0, 0.001]`                          |
| `H`    | senescence      | rate of exponential increase of senescent mortality with age     | `[1.0, 1.5]`                          |

The admissible ranges are the bounds enforced by `fit_heligman_pollard()` in `mortality.py:148-149` when refitting the schedule against an external life table, and they are consistent with the parameter neighborhoods reported in the actuarial literature on the HP model (Heligman and Pollard 1980; subsequent surveys in Tabeau, van den Berg Jeths, and Heathcote 2001 are cited via the spec). Per-era values are loaded from JSON templates under `epocha/apps/demography/templates/`. Table 4.2 lists the values shipped with each of the five templates released in Plan 1 of the demography work; values for `pre_industrial_christian.json` and `pre_industrial_islamic.json` are identical (only non-mortality fields differ between the two pre-industrial variants). The MVP values are provisional seeds in the order of magnitude of their calibration targets; numerical fitting against the cited targets is documented in the demography spec and in the Plan 1 closure notes as provisional seed values, with the fit procedure (`fit_heligman_pollard()`) reserved for Plan 4 calibration against historical mortality data. The `sci_fi.json` template is documented in the source file as speculative and has no empirical target.

Table 4.2 — Per-era HP parameter values (templates shipped in Plan 1).

| Era template                                  | `A`      | `B`   | `C`   | `D`      | `E`   | `F`   | `G`        | `H`   | Calibration target                                                |
|-----------------------------------------------|----------|-------|-------|----------|-------|-------|------------|-------|-------------------------------------------------------------------|
| `pre_industrial_christian` / `pre_industrial_islamic` | 0.00491  | 0.017 | 0.102 | 0.00080  | 9.9   | 22.4  | 0.0000383  | 1.101 | Wrigley and Schofield (1981) tables A3.1–A3.3, England 1700–1749 |
| `industrial`                                  | 0.00223  | 0.022 | 0.115 | 0.00057  | 10.8  | 25.1  | 0.0000198  | 1.104 | HMD England and Wales life tables, pooled 1841–1900               |
| `modern_democracy`                            | 0.00054  | 0.017 | 0.125 | 0.00013  | 18.3  | 19.6  | 0.0000123  | 1.101 | HMD USA life table 2019 (pre-COVID baseline)                      |
| `sci_fi`                                      | 0.00002  | 0.017 | 0.125 | 0.00001  | 18.3  | 19.6  | 0.0000018  | 1.089 | Speculative extrapolation; no empirical basis                     |

**Algorithm.** For each living agent, on every tick, the mortality module evaluates equation (4.1) at the agent's current age, converts the resulting odds into the annual probability `q(age, params)`, scales it to the tick interval, and draws against a uniform variate from the seeded RNG stream. The tick scaling is implemented in `mortality.py:tick_mortality_probability()` (line 56) and is conditional on the size of `q`: when the annual probability is below 0.1 the linear approximation `q · dt` is used (its error against the exact geometric form is below 0.5% in this regime), and when `q` exceeds 0.1 — as it does for infants under the pre-industrial template — the exact geometric conversion `1 − (1 − q)^dt` is used, where `dt = (tick_duration_hours / 8760) · demography_acceleration` is the tick length expressed in years and rescaled by the per-template demographic clock factor. The uniform variate is drawn from a `random.Random` returned by `epocha.apps.demography.rng.get_seeded_rng(simulation, tick, phase="mortality")`; the helper signature is `(simulation, tick, phase)`, and the closed set of allowed phase labels — `mortality`, `fertility`, `couple`, `migration`, `inheritance`, `initialization` — guarantees that adding or removing a subsystem in a refactor does not shift the random sequence the others see at the same tick (Chapter 3.4 covers the design rationale). When a death fires, the cause is sampled by `mortality.py:sample_death_cause()` (line 77), which evaluates the three HP components at the age of death and selects one of the three labels `early_life_mortality`, `external_cause`, `natural_senescence` with probability proportional to the corresponding component magnitude; the labels are analytic conventions for dashboard reporting, not medical etiology, and they map one-to-one onto the three terms of equation (4.1). As of the pinned commit, this per-tick evaluation is exercised by the demography unit-test suite (`epocha/apps/demography/tests/test_mortality.py`) but is not yet invoked from `epocha/apps/simulation/engine.py` or `tasks.py`. The integration into the live tick loop is tracked as a Plan 4 deliverable.

**Simplifications.** The current implementation deliberately omits three refinements that the demographic literature treats as proper extensions rather than corrections of the baseline schedule. First, no cohort effects are modeled: every agent is exposed to the era template active at the simulation tick rather than to the mortality regime in force at the agent's birth, so cohort-specific shocks (war, epidemic, famine) cannot persist as a residual cohort signature into later life. Second, `sample_death_cause()` selects a single coarse label from the three HP components rather than decomposing mortality into a full cause-of-death taxonomy; the three labels are sufficient for dashboard analytics but are not a medical classification, and any analysis that requires cause-specific mortality rates would need to extend the sampler. Third, no extrapolation beyond age 110 is provided: the HP schedule is evaluated at the agent's current age without an explicit tail model for super-centenarians, and the `0.999` cap on annual mortality probability ensures that the survival probability stays strictly positive for the geometric tick conversion, but this is a numerical guard rather than a substantive model of late-life mortality plateaus.

### 4.1.2 Fertility model (Hadwiger ASFR + Becker modulation + Malthusian ceiling)

> Status: implemented as of commit `1cdcfa4fe23138727c16a2e92234e4eb962d9ae7`, spec audit CONVERGED 2026-04-18 round 4.

**Background.** Fertility in Epocha is built as a three-layer composition rather than as a single closed-form schedule because the three forces it has to represent operate on incommensurable timescales and on distinct causal channels. The biological substrate — the bell-shaped curve of female age-specific fecundity over the fertile window, peaking in the mid-twenties and tailing off into the late forties — is well captured by an analytic schedule and changes only on evolutionary timescales. The economic and cultural modulation of completed fertility — the difference between five children per woman in a pre-industrial agrarian economy and one and a half in a modern democracy — operates at the timescale of generations and is driven by income, education, and the opportunity cost of childbearing rather than by biology. The aggregate ceiling — the soft cap that prevents the simulated population from running away under conditions where the analytic rates alone would generate exponential growth — is neither biological nor cultural but an engineering constraint that must nevertheless preserve the qualitative shape of the Malthusian preventive check. Two single-layer alternatives were considered and rejected. Coale and Trussell's 1974 model fertility schedules express age-specific fertility as the product of a natural-fertility schedule, an `M` parameter for the level, and an `m` parameter for spacing/stopping behavior, and have decades of empirical validation behind them. The Coale-Trussell formulation, however, embeds its socioeconomic content inside the `m` parameter, which conflates two effects (timing of stopping and intensity of contraception) that Epocha needs to vary independently for behavioral integration with the LLM-driven decision layer; calibrating `m` to a target completed fertility level loses the explicit handle on the economic mechanism. Hadwiger's 1940 three-parameter analytic form, by contrast, is a pure age-shape with a normalized total fertility rate `H` factored out of the integral, which lets us multiply by an external modulation function without breaking the integration property of the schedule. Becker's 1991 quantity-quality framework supplies the right vocabulary for that modulation function — the marginal value of an additional child as a function of household income, female labor force participation, and parental education — but does not itself prescribe a specific functional form on a per-tick probability, so the modulation layer is implemented as a log-linear scaling factor inspired by the Becker framework rather than as a literal Becker model. The Malthusian ceiling is added on top because Hadwiger × Becker on its own does not have a population-density feedback, and pre-industrial templates with `H = 5.0` would generate growth rates incompatible with the carrying capacity of the simulation grid; the ceiling is the Ashraf and Galor (2011) preventive-check intuition implemented as a piecewise scaling on the per-tick birth probability rather than as a continuous-time formalism on income per capita.

**Model.** The per-tick probability that an eligible mother gives birth at the current tick is the product of three layers, each implemented as a separate function in `epocha/apps/demography/fertility.py` so the layers can be replaced or audited independently:

```
f_HW(a; H, R, T) = (H · T / (R · √π)) · (R / a)^1.5
                 · exp(−T² · (R / a + a / R − 2))                    (4.2)

m_BK(agent; β) = clip(exp(β₀ + β₁ · w + β₂ · e + β₃ · φ + β₄ · ω),
                      0.05, 3.0)                                     (4.3)

c_MT(p, n, n_max, ρ) = p                              if n < 0.8 · n_max
                     = p · max(0, 1 − (n − 0.8·n_max) / (0.2·n_max))
                                                       if n < n_max
                     = p · ρ                           if n ≥ n_max  (4.4)

P_tick(agent, env) = c_MT( f_HW(a; H, R, T) · m_BK(agent; β),
                            n, n_max, ρ )  ·  Δt                     (4.5)
```

Equation (4.2) is the canonical Hadwiger age-specific fertility rate in the normalized form discussed in Chandola, Coleman and Hiorns (1999) and Schmertmann (2003), where `H` is the target total fertility rate (the integral of `f_HW` over the fertile window), `R` is a shape parameter related to the peak fertility age, and `T` controls the spread of the distribution; the implementation in `fertility.py:hadwiger_asfr()` (line 19) returns 0 outside the biologically fertile window `[12, 50]` and at non-positive ages. Equation (4.3) is the Becker modulation layer in `fertility.py:becker_modulation()` (line 85): `w = log(max(wealth / max(subsistence, 1e-6), 0.1))` is the log-wealth signal relative to the subsistence threshold, `e` is the agent's education level, `φ` is the female labor-force-participation proxy in the agent's zone (computed in `_female_role_employment_fraction()` from one-tick wage transactions to female recipients), and `ω` is the aggregate-outlook signal computed in `epocha.apps.demography.context.compute_aggregate_outlook()`; the result is exponentiated and clipped to `[0.05, 3.0]` to keep the modulation factor bounded under extreme inputs. Equation (4.4) is the Malthusian soft ceiling implemented in `fertility.py:malthusian_soft_ceiling()` (line 118): below 80% of the per-template `max_population` the multiplicative factor is one, between 80% and 100% it ramps linearly to zero, and above 100% it collapses to a floor `ρ` (`malthusian_floor_ratio` in the era template) so that populations do not stop reproducing entirely (unless the era template explicitly sets `malthusian_floor_ratio = 0`, as in `sci_fi`). Equation (4.5) is the combined `tick_birth_probability(mother, params_era, current_pop, tick_duration_hours, demography_acceleration, current_tick)` in `fertility.py:152`, which composes the three layers, multiplies by `Δt = (tick_duration_hours / 8760) · demography_acceleration` to convert the annual rate to the tick interval, and returns 0 unconditionally when the era requires couple membership and the mother is not in an active couple, or when the `avoid_conception` flag was set at the previous tick (reading a flag set at tick `T−1` during tick `T` makes contraception a tick+1-settled action, consistent with the property-market semantics introduced in Chapter 4.2.3).

**Parameters.** The three Hadwiger parameters carry the semantic roles `H` = target TFR, `R` = peak-fertility shape parameter, `T` = spread; per-era values are loaded from JSON templates under `epocha/apps/demography/templates/`. Table 4.3 lists the Hadwiger values shipped with each of the five Plan 1 templates. The `H` values track historically attested completed fertility levels — five children per woman for the pre-industrial templates, four for the industrial transition, slightly below replacement for the modern-democracy template, and around replacement for the speculative `sci_fi` template — while `R` and `T` shift the peak rightward and broaden the distribution as societies transition to later first births and tighter spacing.

Table 4.3 — Per-era Hadwiger parameter values (templates shipped in Plan 1).

| Era template                 | `H` (target TFR) | `R` (peak shape) | `T` (spread) | `max_population` | `malthusian_floor_ratio` (`ρ`) |
|------------------------------|------------------|------------------|--------------|------------------|--------------------------------|
| `pre_industrial_christian`   | 5.0              | 26               | 3.5          | 500              | 0.10                           |
| `pre_industrial_islamic`     | 5.0              | 26               | 3.5          | 500              | 0.10                           |
| `industrial`                 | 4.0              | 27               | 3.8          | 500              | 0.05                           |
| `modern_democracy`           | 1.8              | 30               | 4.2          | 500              | 0.01                           |
| `sci_fi`                     | 2.1              | 32               | 4.0          | 500              | 0.00                           |

The five Becker coefficients carry the roles `β₀` = baseline (centred at the era's biological schedule), `β₁` = log-wealth elasticity (positive: higher relative wealth raises desired fertility at the agrarian end of the spectrum), `β₂` = education penalty (negative: opportunity cost of childbearing rises with parental education), `β₃` = female labor-force-participation penalty (negative: higher zone-level female employment depresses fertility), `β₄` = aggregate-outlook elasticity (positive: optimism about the future raises the modulation factor). As of the pinned commit, the five coefficients are seeded with the same values across all five templates — `β₀ = 0.0`, `β₁ = 0.1`, `β₂ = −0.05`, `β₃ = −0.1`, `β₄ = 0.2` — pending per-era calibration, and this homogeneity is tracked in the spec's audit-resolution log as debt B2-07 and assigned to Plan 4 (calibration against synthetic shock tests). Table 4.4 records the seed values explicitly so that the homogeneity is visible to the reader rather than buried in the per-era JSONs.

Table 4.4 — Becker modulation coefficients (identical across all five templates pending Plan 4 calibration; tracked as debt B2-07 in the spec).

| Coefficient | Seed value | Semantic role                                           |
|-------------|-----------:|---------------------------------------------------------|
| `β₀`        |       0.0  | Baseline log-shift on the modulation factor              |
| `β₁`        |       0.1  | Elasticity to log-wealth relative to subsistence         |
| `β₂`        |      −0.05 | Penalty per unit of parental education                   |
| `β₃`        |      −0.1  | Penalty per unit of zone female labor-force participation |
| `β₄`        |       0.2  | Elasticity to aggregate macro-outlook signal             |

The five coefficients are described in `becker_modulation()` (fertility.py:85–111) as "provisional seed values" with calibration "deferred to Plan 4 using synthetic shock tests"; they are inspired by the Becker framework rather than estimated from a specific Becker-style household-economics regression, and the whitepaper records them as tunable parameters of the Epocha implementation rather than as Becker-derived constants. The Malthusian floor `ρ` is the `malthusian_floor_ratio` field on the per-template `fertility` block; when omitted, `tick_birth_probability` defaults to `0.1` (`fertility.py:204`), which is the value used in the spec text and in the two pre-industrial templates.

**Algorithm.** For each living female agent in the fertile window `[12, 50]`, on every tick, the fertility module first checks the gating preconditions in `tick_birth_probability()` (lines 180–191): if the era template requires couple membership and the mother is not in an active couple (`is_in_active_couple()`), or if the `avoid_conception` flag on `AgentFertilityState` was set at tick `T−1` (`is_avoid_conception_active_this_tick()`, line 262), the function returns 0 and no birth can fire this tick. Otherwise the three layers are evaluated in sequence: `hadwiger_asfr()` is called at the agent's age in years (computed in `_effective_age_in_years()` from `birth_tick` and the authoritative `current_tick` to avoid the FK-cache staleness flagged in audit finding B2-04), the result is multiplied by `becker_modulation()` evaluated against the agent's wealth, education, zone, and outlook, the product is passed through `malthusian_soft_ceiling()` against the current population and `max_population`, and the resulting annual rate is multiplied by `Δt` to give the per-tick probability. The caller draws a uniform variate from a `random.Random` returned by `epocha.apps.demography.rng.get_seeded_rng(simulation, tick, phase="fertility")` — the same seeded-stream contract documented for mortality in §4.1.1, with `phase="fertility"` selected from the closed phase set so the fertility draw never shifts the random sequence the mortality draw at the same tick has consumed. When a birth fires and maternal mortality applies, the spec §1 C-1 fix requires the two events to be resolved jointly rather than sequentially: `resolve_childbirth_event(mother, params_era, tick, rng)` (`fertility.py:295`) draws against `mortality.maternal_mortality_rate_per_birth` for the maternal-death event and, conditional on the mother dying, against `mortality.neonatal_survival_when_mother_dies` for the newborn's survival; the helper is a pure probabilistic resolver and returns a dict `{mother_died, newborn_survived, death_cause}` with `death_cause = "childbirth"` when maternal death is selected, leaving persistence (mother's death record, newborn creation) to the caller. The joint resolution avoids the bias that would arise from resolving generic mortality first and childbirth mortality second on the same mother in the same tick. As of the pinned commit, this per-tick fertility evaluation is exercised by the demography unit-test suite (`epocha/apps/demography/tests/test_fertility.py`) but is not yet invoked from `epocha/apps/simulation/engine.py` or `tasks.py`; the only mention of `tick_birth_probability` outside `demography/` is a comment in `engine.py:276` describing the gating semantics of the `avoid_conception` flag. One demography function is already invoked from the simulation engine: `set_avoid_conception_flag()` (`fertility.py:262-288`) is called from the `avoid_conception` decision-handler at `engine.py:280-310` to register the per-agent flag at tick T-1, in support of the tick+1-settled action. The remainder of the demography orchestration (per-tick mortality, fertility, and couple resolution) remains pending Plan 4 integration. The integration into the live tick loop is tracked, alongside the equivalent mortality gap noted in §4.1.1, as a Plan 4 deliverable (Initialization, Engine integration, and Historical validation).

**Simplifications.** The current implementation deliberately omits four refinements that the demographic literature treats as proper extensions rather than corrections of the baseline schedule. First, the Hadwiger age-specific schedule is evaluated deterministically at the agent's age, with no inter-individual heterogeneity in the underlying biological fecundity beyond the binary flags carried by `AgentFertilityState`; modeling lognormal heterogeneity in time-to-conception (the proximate-determinants literature reviewed in the demography spec) is deferred. Second, twin and higher-order multiple births are not modeled: each successful birth event creates exactly one newborn, regardless of historical multiple-birth rates that range from roughly 1% in pre-industrial Europe to over 3% in some modern populations. Third, the Becker modulation coefficients are homogeneous across all five era templates, as documented in Table 4.4 and tracked as audit debt B2-07; per-era calibration is the central deliverable of Plan 4 and will replace the seed values with era-specific estimates from synthetic shock tests against the Wrigley and Schofield (1981) baseline and the additional fertility-decline references catalogued in the demography spec. Fourth, the Malthusian soft ceiling is an engineering heuristic rather than a literal implementation of the Ashraf and Galor (2011) preventive-check formalism, which operates in continuous time on income per capita; the Epocha ceiling is a discrete tick-based scaling on the per-mother birth probability that preserves the qualitative shape of the preventive check (free below 80% of cap, ramp to zero between 80% and 100%, floor above the cap) without claiming to reproduce the Ashraf-Galor income dynamics. The choice is documented in the `malthusian_soft_ceiling()` docstring (`fertility.py:118–145`) and is consistent with the design intent of giving the simulation a population-density feedback that protects the per-tick computational budget while remaining interpretable in Malthusian terms. The helper `_zone_mean_wage()` (`fertility.py:70-82`) is defined as scaffolding for a future Becker refinement that would use zone-level mean wages as a wealth signal, but it is not invoked by `becker_modulation()` as of the pinned commit; the wealth signal currently uses the agent's own wealth normalised by the subsistence threshold.

### 4.1.3 Couple formation and dissolution (Gale-Shapley + Goode 1963)

> Status: implemented as of commit `1cdcfa4fe23138727c16a2e92234e4eb962d9ae7`, spec audit CONVERGED 2026-04-18 round 4.

**Background.** Couple formation in Epocha runs on two distinct mechanisms because the genealogy module has two distinct workloads with incompatible semantics. At simulation initialization the module has to populate a synthetic founder population with a plausible joint distribution of partnered and unpartnered adults: every eligible adult sees every other eligible adult once, and the matching has to be stable in the Gale and Shapley (1962) sense so that no two unmatched agents would prefer each other to their assigned partners — otherwise the founder population starts in a non-equilibrium state that the per-tick dynamics would then have to undo. At runtime, by contrast, couples form one or two at a time as agents make individual decisions through the LLM pipeline, and the appropriate primitive is not a global matching but a tick+1-settled intent resolver, in the same family as the property-market settlement pattern documented in Chapter 4.2.3: an agent declares the intent to pair-bond with a named target on tick `T`, the resolver runs at the start of tick `T+1`, and a couple is created when both ends of the edge declared the intent toward each other (or when the era template authorizes implicit consent). A single-mechanism design was rejected. Running Gale-Shapley on every tick would re-stabilize the entire dating market on each iteration, dissolving and re-pairing existing couples as relative scores drift, which is sociologically implausible (real couples have switching costs) and computationally `O(n²)` per tick. Running pure intent resolution at initialization would leave the founder population statistically arbitrary, with couples formed by whichever agent happened to be processed first rather than by mutual preference. The hybrid design — stable matching once at `t = 0`, intent-driven settlement thereafter — gets the right invariants from each regime. Arranged marriage is layered on top of the runtime mechanism rather than implemented as a separate code path. Goode (1963) describes arranged marriage as a system in which the proposer is a parent acting on behalf of an unmarried child, and the child retains a structurally weaker but non-zero veto right; Epocha represents this with a two-pass extension of the same `pair_bond` action, where Pass A collects direct intents authored by the agent herself and Pass B collects parental `for_child` intents that are honored only when the child has not already declared a direct intent in Pass A. The two-pass ordering preserves Goode's asymmetry — the parent can initiate, but the child's own declaration always wins — without introducing a separate `arranged_pair_bond` action that would inflate the LLM action space. The canonical `agent_a.id < agent_b.id` ordering invariant is enforced at the model layer by a `CheckConstraint`, not as a soft convention, because two rows representing the same pair with swapped foreign keys would silently corrupt heir resolution and double-count active couples in the population snapshot; a single `_ordered_pair()` helper is the only path through which `Couple.objects.create()` is reached.

**Model.** The compatibility score between two candidate partners follows Kalmijn's (1998) homogamy framework, which decomposes assortative mating into a small number of socio-economic dimensions weighted by their cultural salience in the era under study. The weighted score in Epocha takes four components — class similarity, education proximity, age proximity, and existing relational sentiment — each normalized to `[0, 1]` before weighting:

```
hg(a, b; w, τ) = w_class · 1[class(a) = class(b)]
               + w_edu   · exp(-|e(a) - e(b)|)
               + w_age   · exp(-|age(a) - age(b)| / τ)
               + w_rel   · ((sent(a, b) + 1) / 2)            (4.6)
```

Equation (4.6) is the implementation of `homogamy_score(a, b, weights, age_tolerance_years=10.0)` in `epocha/apps/demography/couple.py:60-95`. The four weights `w_class`, `w_edu`, `w_age`, `w_rel` sum to one in each era template and shift the relative importance of structural versus affective dimensions across eras (Table 4.5). The relational term reads `Relationship.sentiment ∈ [-1, 1]` from the agent layer and folds it into `[0, 1]` with the standard affine map; when no `Relationship` row exists the term defaults to `0.5` (neutral), so the score remains well-defined for previously unacquainted candidates. The exponential kernel on age proximity uses `τ = 10.0` years as the default tolerance, matching the order of magnitude of attested age-gap distributions in the demographic literature; `τ` is a function argument rather than a per-era field as of the pinned commit and is held constant across templates pending Plan 4 calibration.

The initialization mechanism applies Gale-Shapley deferred acceptance over the score function (4.6). With the eligible male population as the proposing side and the eligible female population as the responding side (or the reverse — the algorithm is symmetric in correctness, asymmetric only in the well-known proposer-optimal property that Gale and Shapley 1962 prove), the algorithm runs:

```
function stable_matching(P, R, score_fn):                     (4.7)
    rank[p] = sort(R, key=lambda r: -score_fn(p, r))     ∀ p ∈ P
    score[r][p] = score_fn(p, r)                          ∀ r ∈ R, p ∈ P
    free = list(P)
    engaged = {}                                          # respondent → proposer
    next_idx = {p: 0 for p in P}
    while free:
        p = free.pop(0)
        if next_idx[p] >= len(rank[p]): continue
        r = rank[p][next_idx[p]]; next_idx[p] += 1
        if r not in engaged:
            engaged[r] = p
        elif score[r][p] > score[r][engaged[r]]:
            free.append(engaged[r]); engaged[r] = p
        else:
            free.append(p)
    return [(p, r) for r, p in engaged.items()]
```

Equation (4.7) is the canonical deferred-acceptance algorithm of Gale and Shapley (1962, Theorems 1 and 2): existence of a stable matching is guaranteed, the result is proposer-optimal, and complexity is `O(|P|·|R|)` in the worst case. The implementation in `couple.py:98-150` is a direct transcription of the textbook form, with one Epocha-specific adaptation: when `|P| ≠ |R|`, the smaller side is fully matched and the larger side has an unmatched residual, which is the demographically realistic outcome (some adults remain single).

The runtime mechanism is a tick+1 resolver over `DecisionLog` entries authored at the previous tick. The two-pass structure required by the Goode (1963) arranged-marriage semantics is:

```
function resolve_pair_bond_intents(simulation, tick, rng):    (4.8)
    template = load_template(simulation.config.demography_template)
    consent  = template.couple.implicit_mutual_consent
    entries  = DecisionLog.filter(sim, tick-1, contains '"pair_bond"')
    direct, arranged = {}, []
    # Pass A: direct intents (agent acts on her own behalf)
    for e in entries:
        d = json.loads(e.output_decision); if d.action ≠ 'pair_bond': continue
        if d.target.for_child: arranged.append((child_id, match_id)); continue
        direct[e.agent.id].append(match_id)
    # Pass B: arranged intents only where child has no direct intent
    for (child_id, match_id) in sorted(arranged):
        if child_id in direct: continue          # child's own choice wins
        direct[child_id].append(match_id)
    # Resolution: deterministic ordering, mutual or implicit consent
    used = set(); formed = []
    with transaction.atomic():
        for proposer_id in sorted(direct):
            if proposer_id in used: continue
            for target_id in direct[proposer_id]:
                if target_id in used: continue
                mutual = (proposer_id in direct.get(target_id, []))
                if not mutual and not consent: continue
                formed.append(form_couple(proposer, target, formed_at_tick=tick))
                used.update({proposer_id, target_id}); break
    return formed
```

Equation (4.8) is the implementation of `resolve_pair_bond_intents()` in `couple.py:178-316`. Pass A and Pass B are the audit-resolution fix B2-06 that gives Goode's asymmetry its operational meaning (parent proposes, child can override by declaring her own intent). The deterministic `sorted()` over proposer ids and over arranged tuples is the audit-resolution fix B2-03: two runs with the same RNG seed must produce the same matching, which requires iteration order to be id-keyed rather than insertion-order-dependent. Malformed `output_decision` JSON is logged at WARNING level (audit fix B2-02) rather than silently skipped, so a parsing bug cannot cause intents to disappear without trace. The whole resolver runs inside a single `transaction.atomic()` block: either all couples for the tick are committed, or none, which preserves the Population Snapshot invariant that `couples_active(tick)` is the count after a complete settlement step. Couple objects are always created through `form_couple(agent_x, agent_y, formed_at_tick, couple_type='monogamous')` in `couple.py:153-175`, which in turn calls the `_ordered_pair()` helper that enforces the canonical ordering invariant before delegating to `Couple.objects.create()`.

**Parameters.** Per-era couple-formation parameters are loaded from the same JSON templates as mortality and fertility, under the `couple` key. Table 4.5 lists the values shipped with the five Plan 1 templates. The `marriage_market_type` field selects between `autonomous` (the agent herself authors the `pair_bond` intent) and `arranged` (a parent agent authors the intent on behalf of an unmarried child via the `for_child` payload); the same five-template set carries `arranged` only on `pre_industrial_islamic`, with the four other templates set to `autonomous`. The `implicit_mutual_consent` flag governs whether the resolver requires both ends of the edge to have declared the intent (`false`) or honors a one-sided declaration as long as the target is eligible (`true`); all five Plan 1 templates ship with `implicit_mutual_consent: true` and the field is recorded in Table 4.5 as a uniform value rather than as a per-era differentiator. The `divorce_enabled` flag gates `resolve_separate_intents()`: when `false`, the resolver returns an empty list immediately without scanning `DecisionLog`, which models the canonical Catholic-marriage indissolubility regime carried by `pre_industrial_christian`; when `true`, separate intents declared at tick `T-1` dissolve the active couple at tick `T` with `dissolution_reason = 'separate'`.

Table 4.5 — Per-era couple-formation parameters (templates shipped in Plan 1).

| Era template                 | `marriage_market_type` | `divorce_enabled` | `min_age` (M / F) | `mourning_ticks` | `marriage_market_radius` |
|------------------------------|------------------------|-------------------|-------------------|------------------|--------------------------|
| `pre_industrial_christian`   | `autonomous`           | false             | 16 / 14           | 365              | `same_zone`              |
| `pre_industrial_islamic`     | `arranged`             | true              | 16 / 14           | 365              | `same_zone`              |
| `industrial`                 | `autonomous`           | true              | 18 / 16           | 180              | `adjacent_zones`         |
| `modern_democracy`           | `autonomous`           | true              | 18 / 18           | 90               | `world`                  |
| `sci_fi`                     | `autonomous`           | true              | 18 / 18           | 30               | `world`                  |

All five templates ship with `allowed_types = ["monogamous", "arranged"]`, `default_type = "monogamous"`, and `implicit_mutual_consent = true`. The homogamy weights vary across eras to reflect the cultural salience of each Kalmijn (1998) dimension under different historical regimes (Table 4.6): the two pre-industrial templates and the industrial template put substantial weight on social class, which loses ground in the modern-democracy template in favor of education proximity, and the speculative `sci_fi` template demotes class almost entirely in favor of relational sentiment.

Table 4.6 — Per-era homogamy weights for equation (4.6).

| Era template                 | `w_class` | `w_edu` | `w_age` | `w_rel` |
|------------------------------|----------:|--------:|--------:|--------:|
| `pre_industrial_christian`   | 0.40      | 0.25    | 0.20    | 0.15    |
| `pre_industrial_islamic`     | 0.40      | 0.25    | 0.20    | 0.15    |
| `industrial`                 | 0.35      | 0.30    | 0.20    | 0.15    |
| `modern_democracy`           | 0.20      | 0.40    | 0.20    | 0.20    |
| `sci_fi`                     | 0.10      | 0.30    | 0.20    | 0.40    |

Note: the JSON template key is spelled `w_relationship`; the symbol `w_rel` in equation (4.6) and Table 4.6 is the abbreviated mathematical name.

The `age_tolerance_years` parameter `τ` of equation (4.6) is held at the default value `10.0` across all templates, as a function argument to `homogamy_score()` rather than a per-template field; lifting it into the template schema is documented as a Plan 4 calibration deliverable.

**Algorithm.** Three coordinated operations make up the couple lifecycle. At initialization, the founder-population builder calls `stable_matching(proposers, respondents, score_fn)` once with `score_fn = lambda p, r: homogamy_score(p, r, era_weights)` and the eligible adult subpopulations as the two sides; each returned `(p, r)` pair is then routed through `form_couple()` to materialize the database row with the canonical-ordering invariant enforced. At runtime, the demography step calls `resolve_pair_bond_intents(simulation, tick, rng)` once per tick, which reads `DecisionLog` entries authored at tick `T-1` with the SQL `__contains` pre-filter `'"pair_bond"'` and verifies each match by `json.loads()`, runs the two-pass ingestion (direct intents in Pass A, arranged `for_child` intents in Pass B with child-priority override), and creates couples in deterministic id-sorted order under a single `transaction.atomic()`. A pair where either partner is already in an active couple — checked by `is_in_active_couple()` against the unique-active-couple constraint that fix B2-01 added — is skipped, so duplicate active couples cannot be created even under repeated resolver invocations or chord workers. The companion resolver `resolve_separate_intents(simulation, tick)` reads `'"separate"'` `DecisionLog` entries from tick `T-1` with the same JSON pattern, returns immediately when the era template has `divorce_enabled: false`, and otherwise marks the active couple of each declarant as `dissolved_at_tick = tick`, `dissolution_reason = 'separate'`. The third operation, `dissolve_on_death(deceased_agent, tick)` in `couple.py:402-463`, is invoked from the mortality-resolution path when a partnered agent dies: it nulls the appropriate FK (`agent_a` or `agent_b` depending on which side the deceased was), captures the deceased's name into the corresponding `*_name_snapshot` field so the genealogical record survives the FK cascade, sets `dissolution_reason = 'death'`, and persists with a single `update_fields=[...]` save. The contract is idempotent **per partner rather than once per couple**, which is the design's fix MISS-4 and is what makes the both-partners-die-in-the-same-tick case correct rather than lossy. On the second call, `active_couple_for()` no longer finds the row — it was dissolved earlier in the same tick and therefore fails the `dissolved_at_tick__isnull=True` filter — so the function falls back to a couple already dissolved *at this same tick* in which the deceased is still a non-null partner, and completes that partner's name-snapshot capture and FK nulling without touching `dissolved_at_tick` or `dissolution_reason`, which the first call already set. Both name snapshots are therefore captured, and the genealogical record of a couple that died together survives intact. Resolving "dissolved at this same tick" needs only `deceased_agent` and `tick`, both already parameters, so no batch state has to be threaded from the caller — the rejected alternative in design decision D1. This is what lets `process_inheritance_batch()` (§4.1.4) call it unconditionally for every deceased in the batch with no special-casing of the double-death case. As of the pinned commit, this dissolution path is a regular function call rather than a Django signal handler — the spec considered an `agents.Agent` `post_save` signal listening for `is_alive` transitions and rejected it on the grounds that signals add hidden coupling and are harder to audit than an explicit invocation from the mortality module. The couple lifecycle is exercised by the demography unit-test suite (`epocha/apps/demography/tests/test_couple.py`) but, consistent with the gap noted in §4.1.1 and §4.1.2, none of `stable_matching()`, `resolve_pair_bond_intents()`, `resolve_separate_intents()`, or `dissolve_on_death()` is invoked from `epocha/apps/simulation/engine.py` or `epocha/apps/simulation/tasks.py` as of the pinned commit (a `grep` for the function names outside `epocha/apps/demography/` returns only commentary at `engine.py:265-272` describing the tick+1 resolution semantics and the `pair_bond` action's role in the decision pipeline). The integration into the live tick loop is tracked alongside the equivalent mortality and fertility gaps as a Plan 4 deliverable (Initialization, Engine integration, and Historical validation).

**Simplifications.** The current implementation deliberately omits four refinements that the family-demography literature treats as proper extensions rather than corrections of the baseline mechanism. First, only monogamous couples are representable: the `Couple` model carries exactly two foreign keys, and the spec records polygynous and polyandrous couple types as deferred (audit fix MISS-8) because supporting more than two partners would require relaxing the `unique_active_couple` constraint and reworking the heir-resolution path; the `couple_type` enum exposes `monogamous` and `arranged` as the two canonical values, with `arranged` indicating the formation pathway (parent-mediated) rather than a partner-count distinction. Second, the agent layer carries three gender values (`male`, `female`, `non_binary`) and four sexual-orientation values (`heterosexual`, `homosexual`, `bisexual`, `asexual`) in `agents/models.py:11-20`, but the homogamy score and the stable-matching algorithm of equations (4.6) and (4.7) do not consume these fields as of the pinned commit: candidate filtering on gender and orientation is the responsibility of the caller that builds the `proposers` and `respondents` lists, and the founder-population builder that performs that filtering for non-heterosexual or non-binary configurations is itself part of the Plan 4 initialization deliverable. Third, no remarriage cooldown is enforced beyond the per-era `mourning_ticks` field reported in Table 4.5: the field is loaded from the template but not yet consumed by any code path, so a widowed agent can in principle re-pair on the tick following the death of a partner; wiring `mourning_ticks` into the eligibility check of `resolve_pair_bond_intents()` is a one-line change reserved for Plan 4. Fourth, Gale-Shapley is applied at initialization only, not as a fallback at runtime when a large unmatched cohort accumulates: the per-tick mechanism is exclusively intent-driven, on the assumption that the LLM agents will declare `pair_bond` intents at a rate consistent with the population's marriage market; if the validation suite of Chapter 7 reveals systematic underformation, a periodic re-application of the matching primitive over unmatched eligible adults is the natural extension and is documented in the demography spec under the Known Limitations heading.

### 4.1.4 Inheritance (polygenic kernel, social transmission, succession)

> Status: implemented as of commit `1cdcfa4fe23138727c16a2e92234e4eb962d9ae7`, spec audit CONVERGED 2026-04-18 round 4, code audit CONVERGED 2026-08-05 round 4 **as scoped**. The code audit explicitly did not cover eight design-level defects that remain open and are stated in full under Simplifications below.

**Note on numbering.** Equations (4.46) onward and Tables 4.10 onward are appended at the end of the Chapter 4 sequence rather than inserted after (4.8) and Table 4.6, because renumbering the equations and tables of §4.2 through §4.8 would churn seven chapters whose audits have already converged, for no scientific gain. The reader should treat the numbering as an identifier, not as a reading order.

**Background.** Inheritance in Epocha is not one mechanism but three, bound together only by the two events that trigger them — a birth and a death — and kept separate in `epocha/apps/demography/inheritance.py` because they answer three different questions with three different literatures behind them. The first question is biological: what fraction of a newborn's phenotype is predicted by its parents' phenotypes, and what fraction is environmental residual? That is quantitative genetics, and the standard answer is the polygenic additive model of Falconer and Mackay (1996, ch. 8), parameterized by the narrow-sense heritability `h² = V_A / V_P`. The second question is social: what predicts a newborn's class and education given its parents' class and education? The intergenerational-mobility literature offers no single model but a family of era-specific regimes — rigid patrilineal transmission in a stratified agrarian society (Goody 1976; Wrigley and Schofield 1981), a persistent but regressive signal in an industrializing one (Clark 2014), an income-elasticity regime in a modern one (Becker and Tomes 1979 for the theoretical framework, Solon 1999 and Chetty et al. 2014 for the ≈0.4 elasticity value), and a speculative merit regime carried by the `sci_fi` template with no citation at all. The third question is legal: when an agent dies, who receives the estate, in what shares, and what becomes of the debts owed to the deceased? That is comparative inheritance law, and Epocha implements five named systems behind a single dispatch — primogeniture (Blackstone 1765), equal split (Code civil des Français 1804), the Quranic fixed-share-plus-residuary structure (Powers 1986), schematic matrilineal succession (Schneider and Gough 1961), and Soviet-style nationalization (Nove 1969). The three mechanisms are never merged into one call: the module's "Responsibility contract" (design spec Sezione 4 and Sezione 5) fixes trait inheritance and derived-trait evaluation as one strictly ordered pass, social-class and education transmission as a second, and estate settlement as a third that runs on an entirely different event. The separation is what makes each auditable against its own source rather than against a composite nobody published.

One structural choice deserves stating before the equations, because it is a security decision rather than a scientific one. Derived traits — currently only `cunning`, the Machiavellism proxy `0.4·(1 − agreeableness) + 0.3·neuroticism + 0.3·intelligence`, identical across all five templates — are declared as formula *strings* inside the era-template JSON, which makes the template a data file that computes. `evaluate_derived_formula()` (`inheritance.py:149`) therefore refuses `eval()` outright and runs a three-stage restricted evaluator instead: a pre-parse length bound of 500 characters (`_MAX_FORMULA_EXPRESSION_LENGTH`, `inheritance.py:146`), because a pathologically long expression makes CPython's own parser raise a bare `MemoryError` before any later check can fire; an iterative breadth-first walk that enforces both a node-type whitelist and a nesting bound of 50 (`_MAX_FORMULA_TREE_DEPTH`, `inheritance.py:123`) in a single pass; and a recursive evaluator that dispatches only over that whitelist. `ast.Pow` and `ast.Mod` were removed from the whitelist during the audit: `9**9**9` is right-associative and produces an integer with over 369 million digits, and no per-node check can see the danger because every individual node is well-formed — the hazard lives in the combination. The real `cunning` formula is 58 characters and nests roughly six levels, leaving 442 characters and 44 levels of margin. The audit attacked the parse stage with 46 families of pathological strings sized to the length bound and the evaluator with 45 more payloads, and found no escape from `FormulaError` and no code-execution bypass.

**Model.** The polygenic kernel is `inherit_trait()` (`inheritance.py:328`), whose body is four lines (`inheritance.py:430-441`):

```
child_T = h²_T · midparent_T + (1 − h²_T) · ε_T                (4.46)
ε_T ~ N(era_mean_T, era_sd_T)

midparent_T = (mother_T + father_T) / 2   both parents resolved
            = mother_T                    mother only
            = father_T                    father only
            = era_mean_T                  neither
```

The result is clamped to `[lo, hi]`, default `[0, 1]`. The noise draw is taken exactly once per call and always *after* the midparent branch, so the RNG sequence this function consumes does not depend on which branch ran — a deliberate reproducibility property, not an accident of statement order.

Equation (4.46) is the formula the design spec specifies at its Sezione 4, and the implementation is a faithful transcription of it. It is **not** the Falconer and Mackay decomposition it cites, and the difference is measurable rather than interpretive. Under (4.46), with random mating and independent parents, offspring variance obeys the recursion

```
Var(child) = h⁴ · Var(midparent) + (1 − h²)² · era_sd²
           = (h⁴ / 2) · Var(parent) + (1 − h²)² · era_sd²      (4.47)

fixed point:  Var* = (1 − h²)² · era_sd² / (1 − h⁴ / 2)
```

because `Var(midparent) = Var(parent) / 2`, where `h⁴` denotes `(h²)²`, the square of the heritability, on the standard quantitative-genetics convention that `h²` is itself the parameter. For the modal trait configuration of the shipped templates — `h² = 0.55` (intelligence and strength) against `era_sd = 0.15` — equation (4.47) gives `sd* = 0.0733`, that is **48.8% of the era standard deviation the model claims to sample from**. The audit measured exactly this by simulating 4,000 agents over eight generations: the spread collapsed from 0.150 to a fixed point of 0.0733 and stayed there. The variance-preserving form the cited source calls for keeps the same conditional mean — `μ + h²·(midparent − μ)` is algebraically identical to `h²·midparent + (1 − h²)·μ` — and differs only in how the residual is scaled:

```
Falconer & Mackay (1996, ch. 8), variance-preserving form:
  child_T = μ_T + h²_T · (midparent_T − μ_T) + e_T             (4.48)
  Var(e_T) = V_P · (1 − h⁴_T / 2)     so that Var(child) = V_P
  single-parent regression coefficient is h²_T / 2, not h²_T
```

At `h² = 0.55` and `era_sd = 0.15`, (4.48) requires a residual standard deviation of `0.15 · √(1 − 0.55⁴/2) = 0.1382`, where (4.46) supplies `(1 − 0.55) · 0.15 = 0.0675` — slightly less than half. The single-parent line of (4.48) is the second discrepancy: (4.46)'s single-parent branch applies the full `h²` to the one known parent, so the implemented parent-offspring regression coefficient is `h²` where the cited source gives `h²/2`. Both departures are stated again, with their consequences, under Simplifications; they are recorded here because a chapter that presented (4.46) under a Falconer and Mackay heading without (4.47) and (4.48) beside it would be citing a source that does not support it.

Social transmission runs two steps, in a fixed order that the audit corrected: education regression first, then the class rule. The four class rules are (`inheritance.py:879-958`):

```
patrilineal_rigid : child.class = father.class   (string copy, no rank round-trip)
                                 ← mother.class ← "working"     (fallbacks)

clark_regression  : rank = 0.7 · parent_rank + 0.3 · zone_class_mean   (4.49)

becker_tomes      : rank = 0.4 · parent_rank + 0.6 · zone_class_mean
                          + N(0, 0.75)

meritocratic      : merit = (child.intelligence + child.education) / 2
                    rank  = 0.2 · parent_rank
                          + 0.8 · (1 − merit) · 4
```

where `parent_rank` is the *father's* rank on the ladder `elite=0 … poor=4, enslaved=5`, falling back to the mother's and then to `working` (`_resolve_parent_rank()`, `inheritance.py:859`), `zone_class_mean` is the mean rank of the living population of the mother's zone, and every sampled rule's output is clamped to `[0, 4]` before rounding to a label. That output ceiling is an audit fix: before it, ordinary weighted-average-plus-noise arithmetic under `becker_tomes` rounded to rank 5 — `enslaved` — for **25.25%** of children of two `poor` parents in an all-`poor` zone, in `modern_democracy`, the one era in which chattel slavery must never appear. `enslaved` survives as an *input* rank and reaches a child by exactly one route: `patrilineal_rigid`'s verbatim string copy from an already-enslaved father, which never passes through the rounding at all. Education regression is (`inheritance.py:961`):

```
child.education = ρ · midparent_education + (1 − ρ) · era_mean_education   (4.50)
```

clamped to `[0, 1]`, with the same four-way midparent fallback as (4.46) and `era_mean_education = 0.3` (`DEFAULT_ERA_MEAN_EDUCATION`, `inheritance.py:831`) because no template declares the key. It runs before the class dispatch so that `meritocratic` — the only rule reading `child.education_level` — sees the regressed value rather than the `Agent` field default; running it second understated merit by 0.06 and the final rank by 0.19 at two parents of education 0.9 under `sci_fi`, enough to demote a child a full class.

Estate settlement decomposes into a tax step and an allocation step:

```
tax_revenue = total_estate · rate                              (4.51)
inheritable = total_estate · (1 − rate)
```

with `rate` clamped into `[0, 1]` and a non-positive estate short-circuited to a zero return before any treasury credit (`apply_estate_tax()`, `inheritance.py:1583`). The heir ladder is `["spouse", "children", "siblings", "extended_family", "government"]` in all five templates; `resolve_heirs()` (`inheritance.py:1488`) returns living occupants of the first four in `(birth_tick, id)` order and represents `government` structurally, as every other category being empty, rather than as a key. Extended family is bounded to the deceased's grandparents walked down two generations — aunts, uncles, first cousins — which caps the traversal at three queries independently of family size. The five succession rules then distribute `inheritable` (`inheritance.py:1839-2136`):

```
primogeniture : 100% to eldest son → eldest daughter/non-binary
                → spouse → eldest brother → eldest sister      (4.52)
equal_split   : inheritable / (n_children + n_spouse), deduplicated by id
shari'a       : spouse_fraction = 1/8 with children, 1/4 without
                residual split 2:1 male:non-male over children,
                else over siblings, else the spouse absorbs it (radd)
matrilineal   : inheritable / n, equally among the living children
                of the deceased's sisters
nationalized  : {} — the entire estate is state property
```

Every rule that resolves at least one heir routes its shares through `_allocate_with_exact_remainder()` (`inheritance.py:1699`), which assigns each heir its raw share except the last in deterministic order, which receives `total − running_sum`. The guarantee this buys is narrow and is stated precisely because the audit found the previous statement of it overstated:

```
running_sum + (total − running_sum) == total                   (4.53)
where running_sum is accumulated by the same left-to-right += used above
```

Equation (4.53) held over 12,730 adversarial allocations spanning the smallest denormal `5e-324` to `1.7e308`, every power of two from 2⁻⁶⁰ to 2⁶⁰, and 1 to 1000 heirs, with zero failures. The broader property a caller would naturally check — `sum(allocation.values()) == inheritable`, re-summed with Python's builtin `sum()` — fails for 45.0% of that same adversarial population at ~1e-16 relative error, because CPython 3.12's `sum()` uses compensated Neumaier summation and computes the true mathematical sum, which differs from `total` by exactly the rounding the last heir absorbed. No production caller checks conservation that way; only tests do.

**Parameters.** Table 4.10 lists the heritability table, identical across all five templates, with the primary source of each value. Table 4.11 lists the per-era social and economic inheritance parameters. The three module constants that are not template fields are `_BECKER_TOMES_RANK_NOISE_SD = 0.75` (`inheritance.py:809`), `MOURNING_MEMORY_WEIGHT = 0.9` and `MOURNING_TIE_STRENGTH_THRESHOLD = 0.6` (`inheritance.py:2756`, `2773`).

Table 4.10 — Per-trait heritability `h²` shipped by all five era templates, with the primary study each value comes from.

| Trait | `h²` | Primary source |
|---|---:|---|
| `openness` | 0.41 | Jang, Livesley, and Vernon (1996) |
| `conscientiousness` | 0.44 | Jang, Livesley, and Vernon (1996) |
| `extraversion` | 0.54 | Jang, Livesley, and Vernon (1996) |
| `agreeableness` | 0.42 | Jang, Livesley, and Vernon (1996) |
| `neuroticism` | 0.48 | Jang, Livesley, and Vernon (1996) |
| `intelligence` | 0.55 | Plomin and Deary (2015) |
| `emotional_intelligence` | 0.40 | Vernon, Petrides, Bratko, and Schermer (2008) |
| `creativity` | 0.22 | Nichols (1978) |
| `strength` | 0.55 | Zempo et al. (2017) |
| `stamina` | 0.52 | Miyamoto-Mikami et al. (2018) |
| `agility` | 0.45 | Thomis et al. (1998) |
| `fertility` | 0.50 | Zietsch, Kuja-Halkola, Walum, and Verweij (2014) |
| `mental_health` | 0.40 | No trait-specific study: a design heuristic seeded from the Polderman et al. (2015) cross-trait aggregate of 0.49 and adjusted downward |
| `default` | 0.30 | Tunable design default for any `Agent.personality` key with no published `h²` (for example `humor_style`, `attachment_style`) |

Polderman et al. (2015) is cited as the methodological backbone corroborating polygenic additive inheritance across trait domains — a mean `h² ≈ 0.49` over 17,804 traits — and is never the source of an individual trait's value except for the `mental_health` heuristic, which says so explicitly. `cunning` carries no `h²` and is never drawn from the kernel; it is the derived-formula output described under Background. The name of the `mental_health` key is itself an audit fix: all five templates previously declared `mental_health_baseline`, which is not an `Agent` field, so the inherited value landed in `Agent.personality["mental_health_baseline"]`, which nothing reads, while `Agent.mental_health` kept its field default forever.

Table 4.11 — Per-era social and economic inheritance parameters (all five shipped templates).

| Era template | `class_rule` | `education_regression_rho` (ρ) | `rule` (succession) | `estate_tax_rate` |
|---|---|---:|---|---:|
| `pre_industrial_christian` | `patrilineal_rigid` | 0.5 | `primogeniture` | 0.00 |
| `pre_industrial_islamic` | `patrilineal_rigid` | 0.5 | `shari'a` | 0.00 |
| `industrial` | `clark_regression` | 0.4 | `equal_split` | 0.15 |
| `modern_democracy` | `becker_tomes_elasticity_0.4` | 0.4 | `equal_split` | 0.40 |
| `sci_fi` | `meritocratic` | 0.2 | `equal_split` | 0.00 |

Two facts about Table 4.11 must not be misread. First, the shipped templates exercise only three of the five implemented succession rules: `primogeniture` once, `shari'a` once, and `equal_split` three times. `matrilineal` and `nationalized` are implemented, separately tested, and declared by no template; they exist for future custom templates and for completeness of the five documented systems. Second, the ρ column disagrees with the design spec for three of the five templates, and the disagreement is not a rounding convention — it is recorded under Simplifications as an open finding. The `modern_democracy` estate-tax rate of 0.40 corresponds to the top-bracket historical estate and inheritance tax rates documented in Piketty (2014, tables 14.1–14.2); the pre-industrial 0.00 is not a claim that pre-industrial elites paid no death duties, but a scoping statement — feudal relief payments and analogous transfer-of-power levies belong to the economy layer, not to this line item.

**Algorithm.** The birth path is `apply_inheritance_at_birth(child, mother, father, simulation, tick)` (`inheritance.py:1115`). It loads the era template, computes `zone_class_mean` over the mother's zone in one `values_list` query, draws a single `random.Random` from `get_seeded_rng(simulation, tick, phase="inheritance")`, and runs three steps against that one shared stream in a fixed order: `apply_trait_inheritance()` walks the heritable traits in a deterministic order (heritability-dict order first, then any parent-only personality keys sorted lexicographically, never a bare `set`, because `rng.gauss` is drawn once per trait and an unordered iteration would make the draw sequence depend on the interpreter's per-process string hash seed); `resolve_birth_attributes()` consumes exactly two `rng.random()` draws for gender and sexual orientation, gender from the secondary sex ratio via `p_male = ratio / (1 + ratio)` (1.05 in every template except `sci_fi`'s 1.0, and structurally incapable of producing `non_binary`, since the secondary sex ratio is a birth-sex statistic and not a gender-identity distribution), orientation by a cumulative walk over the template's own `sexual_orientation_distribution` in JSON insertion order, whose modern default — heterosexual 0.955, bisexual 0.030, homosexual 0.015 — comes from Chandra et al. (2011) and is carried as a tunable design parameter for eras where no comparable survey exists rather than as a claim of universality; and `apply_social_inheritance()` runs (4.50) then dispatches (4.49). The child's `wealth` is set to 0.0 unconditionally and `zone` to the mother's. Nothing is saved: the function mutates `child` and only `child`, leaving persistence to the Plan 4 birth orchestrator.

The death path is `process_inheritance_batch(simulation, tick, deceased_agents)` (`inheritance.py:2959`). The batch is normalized to a list and sorted `age` descending, `id` ascending — oldest first — the Simultaneous Death Act convention the design spec adopts as a deterministic tiebreak (`inheritance.py:3210`). The simulation's primary currency is resolved once for the whole batch, falling back to the literal `"USD"` only when the simulation has no `Currency` row at all; before that fix the code credited a hardcoded `"USD"` unconditionally, which under `modern_democracy` sequestered 40% of every estate plus every unclaimed estate in a treasury key no spending path reads. Then, per deceased, inside one `transaction.atomic()`: resolve heirs; apply (4.51); distribute per (4.52); accumulate the transfer into a batch-wide pending-credit ledger rather than crediting immediately, since the same living heir may inherit from a second decedent later in the same batch; transfer the lender-side loans; generate mourning memories; and only then dissolve the couple. That last ordering is load-bearing and was corrected during implementation: both `_resolve_spouse_heirs()` and `generate_mourning_memories()` reach the surviving partner through `active_couple_for()`, which only sees a couple with `dissolved_at_tick IS NULL`, so dissolving first would silently discard a living spouse's inheritance *and* their mourning memory.

`transfer_loans_as_lender()` (`inheritance.py:2263`) reassigns the deceased's active lender-side loans — money owed *to* them — round-robin across exactly the ids the cash allocation just paid, `heir_index = loan_index mod n`, in one `SELECT` and one `bulk_update` regardless of loan-book size. Taking the cash allocation as the eligible set rather than re-deriving heirs is what makes `nationalized` fall out for free: an empty allocation routes every loan to `lender=None, lender_type="banking"`, where it continues to be serviced. Under `matrilineal` the allocation ids are nieces and nephews, which `resolve_heirs()` structurally cannot reach, so the orchestrator resolves that list once and threads it into both `distribute_estate()` and this function; an id that stays unresolvable even then is dropped with a `WARNING` rather than raising. Orphan assignment runs last, after every death in the batch is settled, so that a minor orphaned by the final death is still caught and the "does a parent survive?" test sees the batch's final aliveness state. `assign_orphan_caretaker()` (`inheritance.py:2573`) walks a two-stage ladder: sibling, then grandparent, then aunt or uncle *within the minor's own zone*, and only if that stage finds nobody does it repeat the same kinship order across every zone — so a same-zone aunt outranks an other-zone sibling, the spec's own priority of physical proximity over kinship closeness once wardship is being decided. A minor with no living relative anywhere keeps `caretaker_agent = None`, the state-wardship flag. Finally, `generate_mourning_memories()` (`inheritance.py:2776`) writes one first-hand `Memory` at emotional weight 0.9, `source_type=DIRECT`, `reliability=1.0`, `origin_agent=deceased`, to the surviving spouse, every surviving child by either parentage foreign key, and every living agent tied to the deceased by a `Relationship` with `strength > 0.6` in either direction — recipients deduplicated by id, so someone qualifying under two categories still receives exactly one memory. The threshold gates `Relationship.strength`, the social bond, never `Agent.strength`, the inherited physical trait of Table 4.10; filtering on the latter would deliver grief to muscular strangers instead of close friends, and the module records the trap verbatim because the two fields differ by one qualifier.

**Simplifications.** Four rounds of adversarial code audit converged on 2026-08-05 over `inheritance.py`, `migration.py`, and the `couple.py` change of §4.1.3. That verdict covers the code as scoped and explicitly does not cover the design-level defects below, which were deliberately deferred to a separate work item with its own phase-2 requirements gate. They are stated here as things currently true of the model, not as future work.

*The polygenic kernel is not variance-preserving.* Equation (4.46) computes a convex combination, not the Falconer and Mackay decomposition of (4.48), whose residual is scaled so that offspring variance reproduces parental variance — a stable `h² = V_A/V_P` being the entire point of the model. The consequence is measured, not conjectured: trait spread collapses to 48.8% of the declared era distribution within roughly three generations and stays there, so every simulated society drifts toward homogeneity on all thirteen heritable traits of Table 4.10, and realized heritability stops matching the cited figures after the first generation. The citation to Falconer and Mackay describes the model the design intended; it does not describe the implementation, and no result derived from trait variance in a multi-generation run should be read as if it did.

*The single-parent fallback does not halve the genetic signal.* The design spec and the function docstring both claim it does. It does not: replayed on identical RNG state, two parents at 0.9 and mother-only at 0.9 return a bit-identical 0.806952. Against (4.48) the single-parent regression coefficient should be `h²/2`, so at `h² = 0.55` with a parent at 0.9 and `era_mean` 0.5 the correct conditional expectation is 0.610 where the implementation gives 0.720 — the implemented resemblance is twice the cited model's.

*The shari'a spouse fraction is gender-blind.* Q4:12 as documented by Powers (1986) is asymmetric: the widower takes 1/2 without a child and 1/4 with, the widow 1/4 and 1/8. The implementation applies the widow's schedule to both partners (`spouse_fraction = 0.125 if children else 0.25`, `inheritance.py:2005`), so a surviving husband receives half his classical entitlement in both branches. Powers is cited correctly for the surrounding fixed-share-plus-residuary structure and for the 2:1 male-to-non-male ratio of Q4:11, both of which were verified correct; he is not a source for the gender-blind spouse share, and this chapter does not claim he is.

*Estate tax and remainder are computed as two independent products.* Equation (4.51) multiplies twice rather than deriving the remainder by subtraction, so exact conservation `tax + remainder == total` fails for 18.8% of random pairs at a worst absolute error of 1.16e-10; writing `remainder = total − tax` would cut the failure rate to 4.9%. The drift is negligible in magnitude and inconsistent in principle: the heir allocation fifty lines away goes to considerable trouble, in (4.53), to be exact.

*Three templates carry `education_regression_rho` values that contradict the design's cited figures.* The spec gives 0.5 / 0.42 / 0.35 / 0.25 across pre-industrial, industrial, modern, and sci-fi, attributing the modern value to Chetty et al. (2014); the templates of Table 4.11 ship 0.5 / 0.4 / 0.4 / 0.2. Only the pre-industrial pair matches. The modern value in particular is attributed to a source that gives 0.35 and ships at 0.4, with no citation for the shipped number.

*The era-noise parameters are placeholders that are in practice the parameters.* `DEFAULT_ERA_MEAN = 0.5` and `DEFAULT_ERA_SD = 0.15` (`inheritance.py:460-461`) are documented as an interim substitute for the per-trait `era_mean_T` / `era_sd_T` the design calls for, to be estimated from the tick-0 population and frozen. No template declares an `era_noise` section, so these two numbers govern every trait, every era, and every birth. Combined with the variance collapse above they set the fixed point the population converges to. One visible consequence: `Agent.mental_health` and `Agent.fertility` both carry a field default of 0.8 while regressing toward 0.5, so newborns start around 0.62 and the population drifts to 0.5 over generations.

Beyond the deferred defects, four properties of the implementation bear on reproducibility claims made elsewhere in this document and are recorded here rather than left for a reader to discover. First, `get_seeded_rng()` (`rng.py:42`) mixes the simulation's *database primary key* into the seed material alongside `simulation.seed`, so re-running a published seed against a fresh database yields different random streams; the per-phase stream separation of Chapter 3.4 holds, but seed portability across databases does not. Second, representation *per stirpes* is absent from the heir ladder: `_resolve_children_heirs()` finds only living children, and the extended-family traversal walks *upward* to grandparents and back down to cousins, never downward through a predeceased child, so grandchildren cannot inherit when their parent died first. Third, all five templates declare the identical five-entry `heir_priority` ladder `["spouse", "children", "siblings", "extended_family", "government"]`, so the per-era differentiation of succession is carried entirely by the `rule` field of Table 4.11. Fourth, the module is not wired into the tick loop: `epocha/apps/simulation/engine.py` is untouched by this work, and integration is a Plan 4 deliverable, exactly as §4.1.1, §4.1.2, and §4.1.3 already record for mortality, fertility, and couple formation.

Three further simplifications are deliberate design scope rather than defects. `_split_two_to_one()` treats a non-binary heir as non-male, receiving a daughter's single unit, and `_eldest_male_then_female()` orders non-binary heirs together with female heirs; classical Islamic jurisprudence and pre-modern common law recognized no non-binary status, and the module records the choice explicitly rather than defaulting silently. The `shari'a` residuary cascade falls back to siblings under the same 2:1 ratio, standing in for the fuller classical `'asaba` hierarchy that this MVP does not model. And `primogeniture` extends Blackstone's lineal-descent rule to the collateral line — eldest brother, then eldest sister — rather than stranding the estate when the deceased leaves neither children nor a spouse but does leave siblings.

### 4.1.5 Migration (Harris-Todaro context, household coordination, forced flight)

> Status: implemented as of commit `1cdcfa4fe23138727c16a2e92234e4eb962d9ae7`, spec audit CONVERGED 2026-04-18 round 4, code audit CONVERGED 2026-08-05 round 4 **as scoped**; the deferred design defects are stated under Simplifications below.

**Background.** Migration in Epocha is split between two modules for a reason worth stating, because a reader arriving from §4.6 will otherwise expect one. `epocha/apps/agents/movement.py`, documented in §4.6, answers "how does *this agent* physically get from A to B?" — partial journeys, arrival scattering, terrain and health costs. `epocha/apps/demography/migration.py`, documented here, answers the demographic questions instead: what does a zone's labor market look like from outside, who moves when one person decides to, and what happens when an agent has to leave regardless of what any decision loop would have chosen. The three questions carry three literatures. The comparison an economically rational migrant makes is Harris and Todaro's (1970) expected-income model, whose central insight is that a migrant weighs the destination wage by the probability of actually finding work there rather than comparing raw wages — which is why the module computes a per-zone wage level and a per-zone unemployment rate rather than a wage differential alone. The unit of decision is Mincer's (1978): migration is a household choice, and a "tied mover" relocates even against their own narrow interest because the family's joint gain is positive. And the limiting case, where no comparison happens at all, is grounded in two sources at once — O'Rourke (1994) supplies the empirical shape of forced, survival-driven migration under acute economic collapse, with the Irish Famine as the calibration target, and Simon (1955) supplies the reason the deliberation is bypassed rather than merely resolved quickly: below a survival threshold, bounded rationality does not run a cost-benefit analysis.

**Model.** The two labor-market aggregates are per-tick, per-capita figures over explicitly declared half-open windows (`migration.py:108` and `:200`):

```
wage(z, t) = Σ{ ledger.total_amount : type = "wage",
                to_agent.zone = z,
                t − W_w < tick ≤ t }  /  (pop(z) · W_w)         (4.54)

unemployment(z, t) = |{ a ∈ z : a.role ≠ "" ,
                        no wage credit in (t − W_u, t] }|
                     / |{ a ∈ z : a.role ≠ "" }|                (4.55)
```

with `W_w = ZONE_WAGE_WINDOW_TICKS = 5` and `W_u = ZONE_UNEMPLOYMENT_WINDOW_TICKS = 3` (`migration.py:73`, `:105`), both design parameters rather than values derived from a cited source: Harris and Todaro motivate why a wage level drives migration, not how many ticks of history should smooth a noisy signal. Both windows are half-open, and the divisor of (4.54) matches the number of tick values the filter admits one for one. That alignment is an audit fix worth recording because the error it corrects was purely arithmetic and systematically biased: the filter was previously a closed interval spanning `W + 1` ticks against a divisor of `W`, overstating the true per-tick wage by 20% at the default window, 33% at window 3, and 100% at window 1 — and, worse, overstating it *in proportion to how evenly wage activity spread across the window*, so steadily employed zones were inflated and burst-paid zones were not. Wage rows carry no zone of their own and are attributed to the *worker's* current zone through `to_agent__zone`, never the payer's. Unemployment measures joblessness among the nominally employed — an agent with no `role` at all is excluded from both numerator and denominator, the way official statistics exclude those not seeking work — and both denominators return 0.0 rather than dividing by zero.

Travel cost is a whole number of ticks (`compute_distance_cost()`, `migration.py:287`):

```
d_grid = hypot(Δx, Δy)                     zone centers, abstract grid
d_km   = d_grid · World.distance_scale / 1000                   (4.56)
km_per_tick = TRAVEL_SPEEDS["foot"] · (World.tick_duration_hours / 24)
cost   = ceil(d_km / km_per_tick)
```

`World.distance_scale` is meters per grid unit (default 133.0) and `TRAVEL_SPEEDS["foot"]` is 25.0 km/day (Chandler 1966; Braudel 1979, already cited in §4.6). Equation (4.56) is the exact inverse of `calculate_max_distance()` in `agents/movement.py`, reusing only the arithmetic and none of the agent-specific health, stability, and terrain factors, since a zone-to-zone cost has no traveler assigned yet. A partial day's walk costs a whole tick, and a zero-distance move costs exactly 0 rather than being rounded up to 1. The Harris-Todaro comparison itself is the operational variant the design spec declares (`compute_expected_gain()`, `migration.py:366`):

```
E[gain_j] = (1 − unemployment_j) · wage_j − wage_current − distance_cost_j   (4.57)
```

Two departures from the canonical model are documented rather than silent. Harris and Todaro compare `p · w_urban + (1 − p) · w_informal` against origin income; equation (4.57) sets the informal-sector wage to zero, so an agent who fails to find formal work at the destination is modeled as earning nothing there. And it adds a distance term the two-sector model does not carry. The second of these is dimensionally inconsistent, and the inconsistency is not hidden by the design's own worked example only because that example computes a destination whose distance cost is zero; it is stated in full under Simplifications.

`build_migration_outlook()` (`migration.py:456`) assembles the per-agent prompt block from a once-per-tick `zone_stats` bundle, issuing zero database queries of its own. Every reachable zone — defined as every zone of the world other than the agent's own, with no radius bound, because the schema carries no maximum-travel-range concept and (4.56) already prices distance — receives an entry carrying `wage_differential`, `unemployment`, `distance_cost`, `zone_stability`, and `expected_gain`. Household coordination is `coordinate_family_migration()` (`migration.py:681`): the deciding agent's living partner and every living child below the era's `adulthood_age` are moved into the target zone in the same tick, with `location` written alongside `zone` in one `bulk_update`, and one `DemographyEvent` of type `migration` is emitted for the whole household rather than one per member. Adult children are deliberately excluded — they decide independently — and no minor ever receives a `DecisionLog` row for a move they did not choose.

Forced flight fires on three conditions simultaneously (`_resolve_flight_decision()`, `migration.py:1064`):

```
(1) agent.wealth < subsistence_threshold(simulation, agent.zone)
(2) consecutive_ticks_under_subsistence ≥ flight_trigger_ticks   (4.58)
(3) max over reachable zones of E[gain_j] > 0
```

The third condition is what keeps flight and entrapment distinct. An agent satisfying (1) and (2) with nowhere better to go must *not* flee: that is the trapped case, and if the trigger fired on the first two conditions alone every trapped agent would be silently reclassified as a fleeing one, and the trapped-crisis phenomenon the design names explicitly would never be observable at all. `consecutive_ticks_under_subsistence` is an explicit argument rather than a field: the counter exists nowhere in the schema, `Agent.wealth` holds only a current value with no history, and every storage option available under this plan's zero-migration constraint was worse than passing it in. Plan 4 owns creating that storage; until it does, emergency flight cannot fire in a live run.

`process_emergency_flight()` (`migration.py:1145`) drives the whole tick inside one transaction, iterating living agents by ascending id from one shared `get_seeded_rng(simulation, tick, phase="migration")` stream. A fleeing agent's household moves first — before `agent.zone` is mutated, or the event's `from_zone` and `to_zone` collapse — and the agent writes a first-hand `Memory` at weight 0.85. Household members moved for an earlier agent are recorded and skipped when the loop reaches them, because their in-memory instance still shows the old zone and evaluating starvation in a zone they have already left would evaluate a state that no longer holds. A trapped agent is never relocated; it emits a `TRAPPED_CRISIS` event and enters a batched co-zone propagation pass that writes one aggregate `Memory` per witness per zone at weight 0.95, `source_type=PUBLIC`, with `origin_agent` set to the lowest-id trapped agent of that zone as a deterministic representative. The three memory weights form a deliberate ordering across two modules — emergency flight 0.85 below mourning 0.9 below trapped crisis 0.95 — on the reasoning that witnessing a neighbor trapped by starvation with nowhere to go is an ongoing unresolved crisis rather than a single completed event. Both the aggregation and the absence of any witness exclusion are audit corrections. The pre-aggregation shape wrote one memory per (victim, witness) pair, which in the module's own calibration scenario — where the trapped count approaches the zone population — meant roughly 500 × 499 ≈ 250,000 `Memory` rows in a single tick at the templates' `max_population`; and the first attempt to bound that volume widened a witness exclusion until a zone whose entire population was trapped produced six `TRAPPED_CRISIS` events and *zero* memories, the exact Irish Famine case the mechanism exists for. Requirement FR-026 and its acceptance scenario both say the memory reaches "tutti gli agenti co-zone" with no carve-out, so a sole trapped agent alone in a zone receives a self-referential memory; that is the specified outcome, not a residual bug. Mass flight fires when

```
|fled(z)| / population_at_window_start(z) > 0.30                (4.59)
```

strictly, with the numerator spanning the half-open window `(t − flight_trigger_ticks, t]` — historical `emergency_flight` events plus this tick's own departures — and the denominator reconstructed as the zone's current living population plus everyone historically known to have fled it during the window. Pairing a windowed numerator with a point-in-time denominator, as the first implementation did, double-penalizes each departure: the agent stays in the numerator while leaving the denominator, so at a constant departure rate the fraction climbs monotonically and can exceed 1.0. The reconstruction has two acknowledged limits: agents who died in the zone during the window understate the baseline, inflating the fraction slightly under concurrent mortality; agents who arrived during the window overstate it, deflating the fraction slightly in a zone receiving migrants.

**Parameters.** Table 4.12 lists the per-era migration fields and the module-level constants.

Table 4.12 — Migration parameters: per-era template fields and module constants.

| Parameter | Value | Where | Basis |
|---|---|---|---|
| `flight_trigger_ticks` | 30 / 30 / 20 / 10 / 5 | template `migration` block, in template order of Table 4.11 | Design parameter; the design spec's own default is 30 |
| `adulthood_age` | 16 / 16 / 16 / 18 / 18 | template `migration` block | Design parameter; boundary for tied-mover minors |
| `ZONE_WAGE_WINDOW_TICKS` | 5 | `migration.py:73` | Smoothing choice, not derived from Harris and Todaro |
| `ZONE_UNEMPLOYMENT_WINDOW_TICKS` | 3 | `migration.py:105` | Deliberately shorter than the wage window: a faster-moving, noisier signal |
| `TRAVEL_SPEEDS["foot"]` | 25.0 km/day | `agents/movement.py`, reused | Chandler (1966); Braudel (1979) — see §4.6 |
| `World.distance_scale` | 133.0 m/grid unit | `world/models.py` field default | Grid-to-metric conversion, shared with §4.6 |
| `EMERGENCY_FLIGHT_MEMORY_WEIGHT` | 0.85 | `migration.py:917` | Design ordering, below mourning |
| `TRAPPED_CRISIS_MEMORY_WEIGHT` | 0.95 | `migration.py:931` | Design ordering, above mourning |
| `MASS_FLIGHT_THRESHOLD_FRACTION` | 0.30 | `migration.py:938` | Design parameter, strict `>`; not from a cited empirical source |

**Simplifications.** Two design-level defects of the migration module were left open by the converged code audit and belong to the same deferred work item as those of §4.1.4.

*The flight trigger compares a wealth stock against a per-tick subsistence flow.* Condition (1) of (4.58) tests `agent.wealth`, an accumulated balance, against `compute_subsistence_threshold()`, which returns — by its own docstring — the per-agent *per-tick* subsistence cost. The comparison is defensible read as "cannot afford this tick's food", and it is what the design specifies, but it silently fixes the survival horizon at exactly one tick and treats an agent with thirty ticks of savings identically to one with a single tick's worth.

*The Harris-Todaro variant is dimensionally inconsistent.* In (4.57), `(1 − unemployment_j) · wage_j` and `wage_current` are per-tick currency rates — the design's own worked example reports them in LVR/tick — while `distance_cost_j` is a raw count of ticks. Subtracting a tick count from a currency rate does not balance. The design's worked example does not expose it because it computes the Paris case, whose distance cost is 0: `(1 − 0.08) · 90 − 78 − 0 = 4.8`, matching the stated `+4.8 LVR/tick` with the third term simply absent. The audit ruled that the cost should be monetized as forgone earnings, `distance_cost_ticks · wage_current`, which restores dimensional balance, reproduces the Paris example unchanged, and means something economically — wages lost while walking; the alternative of an explicit one-currency-unit-per-tick scaling constant was ruled strictly worse, because it would make the migration threshold depend on the arbitrary scale of the currency. **That ruling is recorded and deliberately not applied.** Equation (4.57) as documented above is what the code computes.

Two further properties are recorded because they affect how the outlook block should be read. "Zone stability" in `build_migration_outlook()` is a simulation-wide scalar reported identically for every reachable zone: `Government` is a `OneToOneField` to `Simulation`, so exactly one government exists per simulation and there is no per-zone stability anywhere in the schema, even though the design's own worked example shows stability differing by zone. The audit ruled that the model does need a genuine per-zone signal — a constant reported per zone carries no information and actively misleads an LLM consumer into believing it is comparing zones on a dimension where they are identical — while also ruling that refusing to invent an unvalidated proxy under this plan's constraints was correct; the prescribed remedy, either dropping the field from the per-zone block or labeling it simulation-wide in the prompt text, is not applied, and the same conflation already exists in merged code in `demography/context.py`. And a migrating household arrives instantly while the deciding agent may still be in transit for several ticks: household members are teleported by `coordinate_family_migration()` because the design requires them to move "nello stesso tick", whereas the decider's own journey goes through `execute_movement()` of §4.6, which supports multi-tick partial movement. A family can therefore be resident in the destination zone while its decision-maker is still on the road.

Finally, and as for every other subsystem of §4.1, neither `evaluate_emergency_flight()` nor `process_emergency_flight()` nor any other function of this module is invoked from `epocha/apps/simulation/engine.py` or `tasks.py` as of the pinned commit. Wiring is a Plan 4 deliverable, and until Plan 4 also builds storage for `consecutive_ticks_under_subsistence`, `process_emergency_flight()` called with the default empty mapping is a well-defined no-op that produces zero events.

## 4.2 Economy — Behavioral integration

> Status: implemented as of commit `1cdcfa4fe23138727c16a2e92234e4eb962d9ae7`, spec audit CONVERGED 2026-04-15.

Chapter 4.2 documents the behavioral layer that sits on top of the economic substrate of §3.6. The substrate of §3.6 is the part of the model that does not depend on agent psychology: it owns the production technology, the monetary aggregates, the Walrasian clearing of single-tick markets, and the per-tick distribution of output into wages, rents, and taxes. Three families of behavior — backward-looking price expectations, intertemporal credit and bank-balance-sheet dynamics, and the Gordon-anchored property market — were specified in the 2026-04-15 economy-behavioral-integration design and audited to convergence under that document. Each family is implemented in a single Python module under `epocha/apps/economy/`: `expectations.py` for the Nerlove (1958) adaptive-expectations engine described in §4.2.1, `credit.py` and `banking.py` for the Diamond-Dybvig (1983) fractional-reserve credit-and-banking machinery described in §4.2.2, and `property_market.py` for the tick-`T+1`-settled Gordon-valuation property market described in §4.2.3. The three modules are wired into the canonical economic tick orchestrated by `epocha/apps/economy/engine.py:process_economy_tick_new()`, which is itself dispatched from the simulation tick loop in `epocha/apps/simulation/engine.py:394` whenever the simulation has the new economy data layer initialized; consequently, unlike the demography modules of §4.1.x, the behavioral economy described in this chapter is genuinely live in the per-tick pipeline as of the pinned commit, and the `Status` headers carried by §4.2.1–§4.2.3 record only the spec-audit convergence date rather than an integration-pending caveat.

### 4.2.1 Adaptive expectations (Cagan 1956)

> Status: implemented as of commit `1cdcfa4fe23138727c16a2e92234e4eb962d9ae7`, spec audit CONVERGED 2026-04-15.

**Background.** Adaptive expectations enter the Epocha tick pipeline because the LLM-driven decision layer needs a per-agent forecast of next-tick prices for each tradable good, and the family of forecasts the model requires must be expressible in three concrete properties: it must be local — each agent has its own forecast, persisted between ticks — so that personality and history can shift it; it must be defined under bounded rationality — agents do not know the true data-generating process — so that the forecast can be wrong in ways the model can study rather than imposing rational-expectations consistency by construction; and it must be computable in `O(n_agents · n_goods)` per tick without solving a fixed point, since the tick pipeline already carries the Walrasian tatonnement of §3.6 and a second nested optimization would dominate the cost. The canonical Muthian (1961) rational-expectations alternative was rejected on the second and third counts: it requires every agent to know the joint stochastic process of all prices and to internalize the model the modeler is using, which neither the LLM nor the personality-modulated decision pipeline of §3.2 can provide, and it would require a per-tick fixed-point solve over heterogeneous beliefs that is incompatible with the cost envelope. The adaptive-expectations family — first formalized by Cagan (1956) for hyperinflation forecasting and independently by Nerlove (1958) in the cobweb-model literature for agricultural supply — solves all three constraints with a single recursive update parameterized by an adaptation rate `λ ∈ (0, 1)`: forecasts are local because each agent carries its own state, bounded-rational because the update rule does not require knowing the true process, and `O(1)` per agent per good per tick because the recursion replaces optimization. The pinned implementation transcribes the Nerlove form of the recursion (the textbook expression that appears in cobweb-theorem derivations) and credits Nerlove (1958) in the module docstring of `epocha/apps/economy/expectations.py:1-23`; the Cagan (1956) lineage is acknowledged in §2.4 of this whitepaper and remains the older anchor for the inflation-forecasting interpretation of the same recursion. The two papers describe the same underlying update rule expressed in equivalent forms, and the choice of attribution at the code-comment level reflects the cobweb-style application (price-by-good forecasts) rather than a substantive disagreement with the Cagan formulation.

**Model.** Each agent maintains, for each good category in the simulation, a row of the `AgentExpectation` model declared in `epocha/apps/economy/models.py:527-585` carrying an `expected_price`, a categorical `trend_direction ∈ {rising, falling, stable}`, a scalar `confidence ∈ [0, 1]`, and the per-agent `lambda_rate` actually used for the update at the previous tick (so the value is auditable rather than recomputed on demand). The recursion that updates `expected_price` between ticks is the canonical adaptive-expectations rule:

```
E_{t+1}[p] = λ · p_t + (1 − λ) · E_t[p]                         (4.9)
```

Equation (4.9) is the implementation of the inner expression in `update_agent_expectations()` at `epocha/apps/economy/expectations.py:209-211`, where `p_t` is the actual tick-`t` market price for the good in the agent's zone (read from `ZoneEconomy.market_prices` populated by the previous tick of the substrate of §3.6) and `E_t[p]` is the agent's previous expected price for the same good. The Cagan (1956) hyperinflation paper writes the same update in the equivalent error-correction form `E_{t+1}[π] = E_t[π] + λ · (π_t − E_t[π])`, which is algebraically identical to (4.9) after a one-line rearrangement; the implementation chose the convex-combination form because it does not require materializing the prediction error as an intermediate variable. The per-agent adaptation rate `λ` is itself a function of the agent's Big Five personality vector rather than a single scalar fixed across the population, which is the substantive Epocha extension of the textbook recursion. The personality modulation, implemented in `compute_lambda_from_personality()` (`expectations.py:43-80`), is a linear deviation from the era-template `λ_base` centered on the population mean of 0.5 for each trait:

```
λ(agent) = clip( λ_base
               + (N(agent) − 0.5) · n_mod
               + (O(agent) − 0.5) · o_mod
               − (C(agent) − 0.5) · c_mod ,
               0.05, 0.95 )                                     (4.10)
```

Equation (4.10) reads `N`, `O`, `C` as the agent's Neuroticism, Openness, and Conscientiousness scores from the personality vector (defaulting to the population mean of 0.5 when the trait is missing) and applies the three modulation coefficients `n_mod`, `o_mod`, `c_mod` from the era-template `expectations_config` block. The signs of the three contributions follow Costa and McCrae (1992): high Neuroticism increases reactivity to new price signals (positive contribution), high Openness increases receptivity to change (positive contribution), and high Conscientiousness anchors the forecast to the prior expectation (negative contribution). The clip to `[0.05, 0.95]` declared as the structural constants `_LAMBDA_MIN` and `_LAMBDA_MAX` at `expectations.py:39-40` is documented in the module as a non-tunable structural bound rather than a free parameter: at `λ = 0.05` the forecast is essentially static (the previous expectation is preserved with negligible weight on the new observation), and at `λ = 0.95` the forecast collapses to a naive expectation (next tick's price equals last tick's price); both extremes are degenerate as adaptive expectations and the clip prevents an unfortunate combination of personality scores and modulation coefficients from driving an agent into either limit. The `trend_direction` field is updated by the helper `detect_trend(expected, actual, threshold)` (`expectations.py:83-107`), which classifies the move from `expected` to `actual` as `rising` when `actual > expected · (1 + threshold)`, as `falling` when `actual < expected · (1 − threshold)`, and as `stable` otherwise; the threshold is the `trend_threshold` field of the era-template `expectations_config` (default `0.05`, identical across all five Plan 1 templates), and is a tunable design parameter rather than a value derived from a specific empirical study. The `confidence` field is incremented by `+0.05` when the agent's previous expectation was within `trend_threshold` of the realized price and decremented by `−0.05` otherwise, clipped to `[0, 1]` (`expectations.py:215-226`); the `±0.05` step is also a tunable design parameter and is documented inline as such.

**Parameters.** All five era templates shipped with Plan 2 carry the same `expectations_config` block, populated by `_behavioral_config()` in `epocha/apps/economy/template_loader.py:179-196`. The values are seeded from a single source in the loader rather than redundantly inscribed in five JSON files because none of the audited Plan 2 calibration evidence motivated era-specific differentiation at the time the templates were frozen; per-era differentiation of `λ_base` and the modulation coefficients is a Plan 4 calibration deliverable. Table 4.7 records the seed values explicitly so the homogeneity is visible to the reader.

Table 4.7 — Adaptive-expectations parameters seeded by `_behavioral_config()` (identical across all five Plan 1 templates pending Plan 4 calibration).

| Parameter             | Seed value | Semantic role                                                              |
|-----------------------|-----------:|----------------------------------------------------------------------------|
| `lambda_base`         |       0.30 | Baseline adaptation rate before personality modulation                      |
| `neuroticism_mod`     |       0.15 | Magnitude of the positive Neuroticism contribution to per-agent `λ`        |
| `openness_mod`        |       0.10 | Magnitude of the positive Openness contribution to per-agent `λ`           |
| `conscientiousness_mod` |     0.10 | Magnitude of the negative Conscientiousness contribution to per-agent `λ`  |
| `trend_threshold`     |       0.05 | Fractional deviation from `expected_price` required to change `trend_direction` |

The structural bounds `_LAMBDA_MIN = 0.05` and `_LAMBDA_MAX = 0.95` on the per-agent output of (4.10) are not in Table 4.7 because they are coded as constants in `expectations.py:39-40` rather than as template fields, on the grounds that a structural bound that prevents degenerate forecasts is a property of the model rather than a calibration choice.

**Algorithm.** On every tick, the economy orchestrator invokes `update_agent_expectations(simulation, tick)` (`expectations.py:110-251`) before market clearing, so that the per-agent forecasts the §3.6 substrate consults during clearing reflect the previous tick's realized prices rather than the prices being computed at the current tick. The function reads the simulation-level `expectations_config` populated at template-loading time, materializes the actual price map by aggregating `ZoneEconomy.market_prices` across all zones with the unweighted cross-zone mean (`aggregate_system_prices`, the same aggregation the orchestrator uses for the system price snapshots; documented inline as a multi-zone refinement target), and bulk-fetches the existing `AgentExpectation` rows for the simulation in a single keyed-by-`(agent_id, good_code)` dictionary so the per-agent loop runs without N+1 queries. For each living agent the per-tick `λ` is computed once from the agent's personality and the era's modulation coefficients, then for each good with an actual price the function either creates a new `AgentExpectation` initialized to the realized price with `confidence = 0.5` and `trend_direction = "stable"` (first observation) or updates an existing row by applying (4.9) with the per-agent `λ`, calling `detect_trend()` against the previous expectation and the new realized price, and adjusting `confidence` by the prediction-error rule. Newly-created and updated rows are flushed in two terminal `bulk_create` and `bulk_update` calls so the entire pass is two writes per tick regardless of the agent count. The orchestrator step in `engine.py:210-214` records the call in the canonical 9-step economic cycle as `STEP 0: EXPECTATIONS UPDATE (Nerlove adaptive)`, and the call site is reached unconditionally whenever `process_economy_tick_new()` is dispatched from the simulation engine, which itself is dispatched whenever the simulation has the `Currency` records that mark the new economy data layer as initialized (`epocha/apps/simulation/engine.py:380-398`). Consequently, in contrast to the demography modules of §4.1.x, the adaptive-expectations engine described here is genuinely active in the live tick loop as of the pinned commit, and the per-tick `AgentExpectation` rows it produces are consumed downstream by the LLM context builder in `epocha/apps/economy/context.py:170-208` to render the agent's price assessment block at decision time.

**Simplifications.** The current implementation deliberately omits four refinements that the adaptive-expectations literature treats as proper extensions rather than corrections of the baseline recursion. First, only the price level for each good is forecast; the recursion is single-variable per good, and there is no joint forecast across goods, no inflation forecast as a separate variable distinct from the per-good price forecast, and no second-moment forecast (volatility, dispersion). Cagan's original (1956) application to hyperinflation forecasts the inflation rate `π` rather than the price level `p`, and the Epocha implementation could be extended to a derived inflation forecast by wrapping the per-good price recursion in a tick-over-tick log-difference; the spec records this as a deferred refinement under the audit-resolution log of the 2026-04-15 design document. Second, the per-agent `λ` is homogeneous across goods within a single agent: the same personality-modulated `λ` is applied to every `AgentExpectation` row owned by the agent, with no good-specific differentiation. A wealthier agent that allocates more cognitive attention to high-impact goods could in principle carry a higher `λ` for the goods that dominate the household budget and a lower `λ` for marginal goods; the spec leaves this as a future refinement and the implementation treats the homogeneity as a deliberate scope choice for the Plan 2 economy. Third, the adaptation rate `λ` is not itself learned: the Big Five modulation in (4.10) is a static mapping from personality to `λ`, with no mechanism by which an agent whose forecasts have been systematically wrong updates its own `λ` upward (to react more to surprises) or downward (to anchor more on the prior). Bayesian-learning extensions of adaptive expectations (Evans and Honkapohja 2001) provide the canonical formalism for `λ` itself being a learned parameter; the Epocha implementation tracks prediction accuracy through the `confidence` field but does not feed `confidence` back into `λ` in the pinned commit, on the grounds that doing so would require a second-order calibration not delivered in Plan 2. Fourth, the multi-zone price aggregation is implemented as the unweighted cross-zone mean of `ZoneEconomy.market_prices` via `aggregate_system_prices` (replacing an earlier last-write-wins merge whose result depended on the database's zone return order) rather than as a per-zone forecast for each agent: an agent in zone A sees the same actual price for a good as an agent in zone B even when the two zones cleared at different prices in the previous tick. The aggregation is documented inline as an MVP simplification (`expectations.py:146-159`) and the per-zone differentiation is the natural extension once the multi-zone economy of §3.6 is exercised by the validation suite of Chapter 7.

### 4.2.2 Credit and banking (Diamond-Dybvig 1983, fractional reserve)

> Status: implemented as of commit `1cdcfa4fe23138727c16a2e92234e4eb962d9ae7`, spec audit CONVERGED 2026-04-15.

**Background.** The credit-and-banking layer enters the Epocha tick pipeline because the agent decision space documented in §3.2 carries an explicit `request_loan` action and an implicit dependency on a stable monetary aggregate, and neither can be satisfied by the substrate of §3.6 in isolation: the substrate clears single-tick goods markets and distributes wages and rents, but it does not represent the intertemporal contracts that connect a tick-`T` borrowing decision to the tick-`T+k` repayment obligation that constrains the borrower's future cash, nor does it carry the bank-balance-sheet aggregates whose deterioration produces the systemic-risk signals the LLM context builder of §3.5 needs to feed into the decision pipeline. Diamond and Dybvig (1983) is the canonical reference for fractional-reserve banking under depositor-confidence dynamics: a single bank takes deposits, lends a fraction of them out, holds the rest as reserves, and is exposed to a self-fulfilling bank-run equilibrium when depositor confidence falls below a threshold and depositors withdraw faster than maturing loans can be liquidated. The Epocha implementation transcribes the qualitative dynamic — confidence erodes when reserves fall short of the required ratio, the erosion broadcasts as agent-level concern memories, and the broadcast itself accelerates the erosion through the LLM-mediated decision pipeline — but deliberately omits two quantitative elements of the original Diamond-Dybvig model. First, the model is a single aggregate bank per simulation rather than a population of competing banks (the inter-bank market that shapes contagion in the empirical bank-run literature is deferred), and consequently there is no inter-bank lending channel and no central-bank lender of last resort. Second, the original Diamond-Dybvig bank-run condition couples low confidence with insolvency through a coordination game on depositor withdrawal types; the audit convergence of 2026-04-15 (audit fix C-3) replaced the coupled condition with the simpler trigger `confidence_index < 0.5` evaluated regardless of solvency status, on the grounds that the LLM-driven population is fully heterogeneous in its information state and the original game-theoretic equivalence does not hold pointwise across an LLM agent set. Loan pricing follows Stiglitz and Weiss (1981) — interest rates carry a risk premium proportional to borrower leverage as a reduced-form representation of the lender's inability to perfectly observe borrower risk — and default cascades use the breadth-first contagion mechanism of Allen and Gale (2000) capped at a configurable depth.

**Model.** The banking-system state is a single `BankingState` row per simulation declared in `epocha/apps/economy/models.py:588` and carries `total_deposits`, `total_loans_outstanding`, `reserve_ratio`, `base_interest_rate`, an `is_solvent` boolean, and a `confidence_index ∈ [0, 1]`. Loans are individual `Loan` rows (`models.py:378-482`) with `lender`, `borrower`, `principal`, `interest_rate`, `remaining_balance`, an optional `collateral` foreign key to `Property` with `related_name="collateralized_loans"`, an `issued_at_tick`, an optional `due_at_tick`, a `times_rolled_over` counter, and a `status ∈ {active, repaid, rolled_over, defaulted, default_settled}` -- `defaulted` is the to-be-processed state and `default_settled` the terminal state a loan reaches once its default has been handled, so a default is processed exactly once. The bank-run trigger that drives the broadcast of banking-concern memories under audit fix C-3 is the simple inequality on the confidence index:

```
broadcast_concern_at_tick(t)  ⇔  BankingState.confidence_index < 0.5     (4.11)
```

Equation (4.11) is implemented in `broadcast_banking_concern()` at `epocha/apps/economy/banking.py:337-424`, with the threshold `0.5` declared as the module-level constant `_CONCERN_CONFIDENCE_THRESHOLD` at `banking.py:334`. The condition is evaluated unconditionally with respect to `is_solvent`, which is the substantive change introduced by audit fix C-3: the original Diamond-Dybvig (1983) coordination game predicts a bank run when both confidence is low *and* the bank is insolvent, but in the Epocha pipeline the confidence dynamic itself drives `is_solvent` toward `False` over time (`check_solvency()` decrements `confidence_index` by `0.1` per tick whenever reserves are short), so the audited condition triggers concern broadcast at the *fear* stage rather than only after the realized failure, which is the empirical pattern documented in the bank-run literature surveyed in the spec. The broadcast itself creates a `Memory` row with `emotional_weight = 0.6` and `source_type = "public"` for a random sample of `_CONCERN_BROADCAST_RATIO = 0.5` of the living agent population (`banking.py:381-410`), with a deduplication window of `_CONCERN_DEDUP_TICKS = 3` ticks aligned to the agent-engine memory deduplication constant in `simulation/engine.py`.

The loan-issuance condition combines the loan-to-value collateral cap of Stiglitz and Weiss (1981) credit-rationing theory with a bank-solvency precondition:

```
approve_loan(borrower, amount, collateral)
  ⇔  collateral.value · LTV ≥ existing_debt(borrower) + amount
  ∧  BankingState.is_solvent                                              (4.12)
```

Equation (4.12) is implemented in `evaluate_credit_request()` at `credit.py:172-255`. The existing-debt aggregate sums `remaining_balance` over the borrower's active loans; the LTV ratio is `credit_config.loan_to_value`, which differs by era template. When both conditions are satisfied, the function returns the per-tick interest rate computed by the Stiglitz-Weiss (1981) risk-pricing rule

```
r = base_rate · (1 + risk_premium · debt_ratio)
debt_ratio = (existing_debt + amount) / max(borrower.wealth, 1.0)         (4.13)
```

with `base_rate` read from `BankingState.base_interest_rate`, `risk_premium` defaulting to `0.5` from `credit_config.risk_premium`, and the leverage clipped on the wealth side to avoid division by zero for newborn or destitute agents. The functional form is a linearized reduced-form approximation of the Stiglitz-Weiss adverse-selection model — the original predicts a non-linear relationship — chosen for transparency and to keep the per-tick cost of credit evaluation `O(1)` per request. The collateral-pledge logic that selects which property the borrower offers as collateral is implemented in `find_best_unpledged_property()` and excludes properties already pledged to an active OR pending-default loan (`collateralized_loans__status__in=["active", "defaulted"]`): this extends audit fix M-6 from the 2026-04-15 convergence, which prevents the same property from being double-pledged across two simultaneous loans (a violation of the Stiglitz-Weiss collateral semantics that the pre-audit implementation allowed), to the pending-default window (R6-COLL-1). The pledge also carries a LIEN (R6-PROP-1, Round 6 re-audit): a property collateralizing an active or pending-default loan cannot be listed or matched in the property market of §4.2.3 -- ownership can leave the borrower only through the credit pipeline's seizure on default, never through a market sale that would strip the lender's security.

**Parameters.** All four era templates shipped with the economy app carry differentiated `credit_config` and `banking_config` blocks, populated by `_behavioral_config()` in `epocha/apps/economy/template_loader.py:144-198`. The era differentiation is calibrated against Homer and Sylla (2005), *A History of Interest Rates*, which catalogues observed historical rates by epoch — pre-modern lending operated at 5-10% per period, the 19th century industrial transition at 4-8%, and modern central-bank-anchored economies at 1-3% — and against the Basel III reserve-ratio convention that distinguishes the modern regulated regime from earlier informal practice. Table 4.8 records the era-specific values explicitly so that the comparative differentiation across templates is visible to the reader, and Table 4.9 records the parameters that are uniform across all four templates because the audit convergence of 2026-04-15 found no calibration evidence to motivate per-era differentiation at the spec stage; per-era differentiation of `risk_premium`, `max_rollover`, and `default_loan_duration_ticks` is a Plan 4 calibration deliverable.

Table 4.8 — Per-era credit and banking parameters seeded by `_behavioral_config()` in `template_loader.py:144-198`.

| Template          | `loan_to_value` | `base_interest_rate` | `initial_deposits` | `reserve_ratio` |
|-------------------|----------------:|---------------------:|-------------------:|----------------:|
| `pre_industrial`  |            0.50 |                 0.08 |             5 000  |            0.10 |
| `industrial`      |            0.60 |                 0.06 |            20 000  |            0.10 |
| `modern`          |            0.80 |                 0.03 |           100 000  |            0.05 |
| `sci_fi`          |            0.90 |                 0.02 |           500 000  |            0.03 |

Table 4.9 — Credit-and-banking parameters that are uniform across all four era templates pending Plan 4 calibration.

| Parameter                          | Seed value | Semantic role                                                                 |
|------------------------------------|-----------:|-------------------------------------------------------------------------------|
| `risk_premium`                     |       0.50 | Coefficient on the borrower-leverage spread in (4.13); uniform default coded at `credit.py:219` (no template field as of the pinned commit; per-era differentiation pending Plan 4 calibration) |
| `max_rollover`                     |          3 | Maximum number of times a maturing loan may be rolled over before default     |
| `default_loan_duration_ticks`      |         20 | Default loan duration assigned by `issue_loan()` when the caller passes none  |
| `_CONCERN_CONFIDENCE_THRESHOLD`    |       0.50 | Threshold of (4.11) below which banking-concern memories are broadcast        |
| `_CONCERN_BROADCAST_RATIO`         |       0.50 | Fraction of the living population that receives the per-tick concern broadcast |
| `CASCADE_LOSS_THRESHOLD`           |       0.50 | Fraction of lender wealth above which a default loss propagates to the lender |

The structural constants `_CONCERN_CONFIDENCE_THRESHOLD`, `_CONCERN_BROADCAST_RATIO`, and `CASCADE_LOSS_THRESHOLD` are coded as module-level constants in `banking.py:334` and `credit.py:54` rather than as template fields, on the grounds that they encode the qualitative shape of the bank-run dynamic (a self-fulfilling prophecy needs a threshold below which fear becomes contagious) rather than calibration choices that vary by historical era. The `risk_premium` value of `0.5` is a design choice rather than an empirical measurement — Stiglitz and Weiss (1981) predict that the risk-pricing slope is positive and increasing in leverage but do not provide a numeric coefficient — and is documented inline as a tunable design parameter at `credit.py:215-219`.

**Algorithm.** On every tick, the economy orchestrator invokes the credit-market step exactly once (gated by a `credit_processed` flag so it does not execute per-zone) at `epocha/apps/economy/engine.py:445-503`, with the following ordered sequence of calls. First, `default_dead_agent_loans(simulation)` (`credit.py:865-893`) defaults all active loans whose borrower has `is_alive = False`: this is audit fix M-3 from the 2026-04-15 convergence, which closes the silent-debt-amnesty gap whereby the pre-audit implementation left dead-borrower loans in `active` status indefinitely, allowing the borrower's heirs to inherit a property still encumbered by a debt the system would never collect. Second, `service_loans(simulation, tick)` (`credit.py:377-464`) collects per-tick interest on every active loan not yet matured (loans whose `due_at_tick` is at or before the current tick are excluded and handled entirely by the maturity step, so one period's interest is charged exactly once per loan-tick -- R6-NEW-1 fix, extended to `due_at_tick <= tick` by the R8-NEW-5 catch-up) by deducting `remaining_balance · interest_rate` from the borrower's cash and crediting it to the lender when `lender_type = "agent"` (for a banking-system loan the interest is deducted from the borrower but NOT re-credited to any counterparty, so it contracts measured M each tick by design -- see §4.8 and the R5-DISC-1 disclosure at `monetary.py`); borrowers who cannot pay interest are returned in a list that the orchestrator marks `defaulted` immediately, so the missed-interest default is handled by `process_defaults` in the SAME tick (R5-CRED-3 fix; pre-fix the returned list was discarded and missed interest had no consequence until maturity). Third, `process_maturity(simulation, tick)` (`credit.py:467-669`) handles loans whose `due_at_tick` is at or before the current tick -- a catch-up sweep (R8-NEW-5) so a loan that fell due on a tick where the credit block was skipped (a fully agent-empty tick) is settled at the next executed tick rather than stranded -- with three outcomes per loan: full repayment when the borrower has enough cash to cover `remaining_balance · (1 + interest_rate)` -- the final period accrues on repayment too, with the principal ledgered as `loan_repayment` and the interest as `loan_interest` (R7-NEW-1 fix), a Minsky-style rollover strictly when the borrower can pay the interest portion but not the principal and the `times_rolled_over` counter is below `max_rollover` (an unaffordable interest now falls through to default -- R6-ROLL-1 fix) (a new loan is created at `interest_rate · 1.10` reflecting the lender's risk adjustment, with `times_rolled_over += 1`), and default when neither condition is satisfied. Fourth, `process_defaults(simulation, tick)` (`credit.py:672-803`) seizes the collateral by transferring `Property.owner` to the lender (or to the government for banking-system loans), zeroes the loan's `remaining_balance`, moves the loan to the terminal `default_settled` status (so collateral seizure, the banking write-off, and the reputation damage each fire exactly once per default rather than being re-applied on every subsequent tick), and creates a negative reputation memory for the borrower with `action_sentiment = -0.7` (zone observers) and `-0.9` (the lender directly) via the reputation system of §4.3. Additionally, a self-aware memory is created for the borrower with `emotional_weight = 0.8` (`credit.py:806-862`) so that the borrower's own decision pipeline retains awareness of the default in subsequent ticks. Fifth, `process_default_cascade(simulation, tick, max_depth=3, loss_records=...)` (`credit.py:930-1085`) runs a breadth-first contagion pass over the debt graph, seeded from the loss records returned by `process_defaults` for the CURRENT tick (the net losses after collateral is netted out, not a re-query over the all-time default history): for each lender whose aggregate loss from this tick's defaults exceeds `CASCADE_LOSS_THRESHOLD = 0.5` of their wealth, the lender's own active loans are marked defaulted (flagged `cascade_origin`, so their settlement records do not re-seed a later cascade: one loss event is threshold-evaluated exactly once -- R6-CASC-1 fix), interior levels accumulate the same net-of-collateral loss measure as the seed level (R6-NEW-2 fix), and the contagion propagates to their lenders in turn until either no further threshold breach occurs or `max_depth = 3` is reached (the cap prevents infinite propagation and is calibrated against the typical empirical-network diameter of 3-5 links reported by Allen and Gale 2000). Sixth, `adjust_interest_rate(simulation, tick)` (`banking.py:115-206`) applies the Wicksellian adjustment `r_{t+1} = r_t · (1 + adj_rate · (demand − supply) / max(supply, 0.001))` to the base rate and clamps the result to `[0.005, 0.50]`. Seventh, `check_solvency(simulation)` (`banking.py:209-266`) evaluates `reserves = total_deposits − total_loans_outstanding` against `required = total_deposits · reserve_ratio` and updates `confidence_index` by `−0.1` per tick of insolvency or `+0.05` per tick of recovery (the asymmetry encodes the trust-asymmetry observation that confidence is easier to lose than to rebuild). Eighth and last, `broadcast_banking_concern(simulation, tick)` (`banking.py:337-424`) evaluates (4.11) and creates the concern memories. The eight-step sequence is deterministic given the simulation random seed (the broadcast step samples from an RNG derived from the simulation seed and the tick, independent of the module-global `random` stream), and the entire credit step writes a bounded number of database rows per tick — bounded by the live agent count for the broadcast and by the active-loan count for servicing and maturity — so the per-tick cost is `O(n_agents + n_active_loans)`.

**Simplifications.** The current implementation deliberately omits four refinements that the credit-and-banking literature treats as proper extensions rather than corrections of the baseline mechanism. First, the banking sector is a single aggregate bank per simulation rather than a population of competing banks: the `BankingState` row is one-to-one with `Simulation`, and there is no inter-bank lending market, no inter-bank exposure graph, and no central-bank lender of last resort. The Allen-Gale (2000) contagion mechanism is therefore implemented only over the agent-to-agent debt graph (`process_default_cascade`), not over a banking-network graph; a multi-bank refinement is recorded in the spec as a deferred extension and would require introducing a `Bank` model with per-bank balance sheets and an inter-bank liability graph. Second, deposit insurance is abstract: the `BankingState.is_solvent` flag prevents new loan issuance while insolvent (via the precondition in (4.12)), but there is no explicit deposit-insurance fund that depositors can claim against, and depositors cannot "withdraw" their cash from the bank in the literal sense because the AgentInventory cash field already represents on-hand cash rather than a deposited balance — the model treats all agent cash as implicitly deposited (`recalculate_deposits()` at `banking.py:293-320`). A future refinement would split `AgentInventory.cash` into a deposited fraction and a hoarded fraction, allowing the bank-run dynamic to be expressed as withdrawal pressure rather than as confidence-mediated rumor. Third, loan negotiation is single-round take-it-or-leave-it: the borrower presents a `request_loan` action with a target amount and a candidate collateral, `evaluate_credit_request()` either approves at the Stiglitz-Weiss rate or rejects with a stated reason, and there is no second round in which the borrower could counter-propose a smaller amount, a different collateral, or a longer duration to bring the request inside the LTV envelope. Multi-round negotiation is recorded as a deferred refinement under the audit-resolution log of the 2026-04-15 design document, on the grounds that it would interact with the LLM context budget and the per-tick decision pipeline in ways that need a separate calibration pass. Fourth, the rollover interest-rate increment is fixed at `1.10` per rollover (`credit.py:636`) rather than being a function of the borrower's leverage at the rollover instant or of the macroeconomic stress signal carried by the banking confidence index; a more sophisticated rollover repricing rule that responds to systemic risk is the natural extension once the validation suite of Chapter 7 exercises the Minsky-stage classification (`classify_minsky_stage` at `credit.py:118-169`) against the canonical Minsky (1986) hedge-speculative-Ponzi taxonomy.

### 4.2.3 Property market

> Status: implemented as of commit `1cdcfa4fe23138727c16a2e92234e4eb962d9ae7`, spec audit CONVERGED 2026-04-15.

**Background.** The property market enters the Epocha tick pipeline because the agent decision space documented in §3.2 carries a `buy_property` action and a `sell_property` action whose semantics cannot be reduced to a single-tick goods-market clearing of the kind owned by the substrate of §3.6: a property changes hands once and stays with the buyer for the rest of the simulation, the asking price diverges systematically from the fundamental rental yield because sellers anchor on personality-modulated expectations, and the buyer's intent declared at tick `T` cannot settle within the same tick because the LLM-driven decision pipeline has already produced its outputs by the time the economy orchestrator is invoked. The implementation transcribes a zone-local listing-and-matching mechanism that preserves the three substantive properties: properties are listed by their owners with an asking price, the listings live in the buyer's current zone, and the matching settles at tick `T+1` against the `buy_property` intents declared at tick `T`. The fundamental-value benchmark against which sellers and buyers compare the asking price is the Gordon (1959) growth-model valuation `V = R / (r − g)`, which gives the intrinsic value of an asset whose cash flow is a perpetuity growing at rate `g` discounted at rate `r`; the Epocha implementation computes this benchmark per property and stores it in the `fundamental_value` field of the listing alongside the seller's `asking_price`, so that the divergence between price and value is observable to downstream analytics and is the natural Epocha analogue of the price-to-fundamentals divergence that Shiller (2000) identifies as the empirical signature of speculative bubbles. Two concrete simplifications are recorded inline: there is no multi-round negotiation between buyer and seller (the asking price is take-it-or-leave-it) and there is no inter-zone matching (a buyer in zone A cannot match a listing in zone B, even at a lower price, because the zone-locality assumption is the spatial structure that the property market inherits from §3.4 movement). The property market also carries a regime-change side-channel implemented in `process_expropriation()` that redistributes properties on government transitions following Acemoglu and Robinson (2006); the side-channel is documented in the property-market module because it operates on the same `Property` rows but it is invoked from the political subsystem rather than from the per-tick economy orchestrator, so the present subsection treats it only as the source of the collateral-conversion side effect on outstanding loans.

**Model.** The matching condition that transfers a property from a seller `s` to a buyer `b` at tick `T` reads against the `PropertyListing` table and the buyer's current zone:

```
match(b, ℓ) at tick T  ⇔  ℓ.status = "listed"
                       ∧  ℓ.property.zone = b.zone        (zone at matching time)
                       ∧  ℓ.property.owner ≠ b            (no self-purchase)
                       ∧  buyer_cash(b) ≥ ℓ.asking_price
                       ∧  buy_property ∈ DecisionLog(b, T−1)            (4.14)
```

Equation (4.14) is implemented in `process_property_listings()` at `epocha/apps/economy/property_market.py:202-379`, with the four conjuncts evaluated in the listed order so that the cheapest qualifying listing is selected via `order_by("asking_price").first()`. The zone-at-matching-time conjunct is the substantive change introduced by audit fix M-4 of the 2026-04-15 convergence: the pre-audit implementation read the buyer's zone from the decision context at tick `T−1`, which produced spurious matches when the buyer moved between ticks `T−1` and `T`, and the audited form reads `buyer.zone_id` directly at the matching call so that a buyer who has crossed a zone boundary loses the ability to match a listing in the previous zone. The self-purchase exclusion is the substantive change introduced by audit fix M-5 of the same convergence: the pre-audit implementation allowed a seller's own `buy_property` intent to match the seller's own listing (a no-op transaction that nonetheless consumed a tick of the buyer's intent budget and inflated the matched count), and the audited form excludes the buyer's own properties from the candidate set via `.exclude(property__owner=buyer)`. The borrowing precondition that gates the cash check is not part of the matching condition itself: a buyer with insufficient cash simply fails the match, and the spec records this as audit fix A-5 — the pre-audit design auto-issued a loan to cover the shortfall, which contradicted the architectural principle that all borrowing is an explicit LLM-driven action documented in §3.2, and the audited form removes the auto-loan path so that a buyer who needs credit must declare a `borrow` action in a previous tick and then redeclare `buy_property` once the cash is in hand.

The collateral-conversion condition that transfers a property from a defaulting borrower to the lender at the moment of loan default reads against the `Loan.collateral` foreign key established at issuance:

```
on default of loan L at tick T:
    if L.collateral ≠ ∅ :
        L.collateral.owner ← L.lender         (or government if lender = banking)
        L.lender_loss     ← max(0, L.remaining_balance − L.collateral.value)        (4.15)
```

Equation (4.15) is implemented in `process_defaults()` at `epocha/apps/economy/credit.py:672-803`, with the residual loss computed after the collateral value is netted out and propagated to the Allen-Gale (2000) breadth-first contagion pass described under the Algorithm of §4.2.2 when it exceeds `CASCADE_LOSS_THRESHOLD = 0.5` of the lender's wealth. The collateral conversion is the bridge between the credit subsystem of §4.2.2 and the property market of this subsection: a property pledged as collateral via the `find_best_unpledged_property()` call of (4.12) is locked out of new collateral pledges by audit fix M-6, and its conversion on default produces an immediate change of ownership that subsequent property-market ticks observe through the standard `property.owner` field. The conversion does not generate a `PropertyListing` for the lender — the lender takes the property directly into ownership and may or may not list it for sale in a future tick depending on its own LLM-driven decisions — and consequently does not appear in the per-tick `process_property_listings()` matched count.

**Parameters.** The property market does not carry an era-specific configuration block of its own; the parameters that govern matching behavior are inherited from the credit configuration of §4.2.2 (loan-to-value for the borrowing path, base interest rate as the discount rate `r` in Gordon valuation) and from the expectations configuration of §4.2.1 (the `trend_threshold = 0.05` of audit fix C-5 that classifies seller anchoring as rising, falling, or stable). The two property-market design parameters that are coded outside the era templates are the listing-expiration window and the Gordon-valuation guard band: stale listings are withdrawn after `10` ticks (`property_market.py:235`), reflecting the assumption that property markets in pre-industrial through modern economies operate on multi-period timescales and that an unsold listing past that horizon is more likely to be a stale price than a viable offer; the Gordon-valuation denominator is floored at `0.01` to prevent division by zero when `r ≈ g`, and the resulting valuation is clipped to `[0.1 · property.value, 10 · property.value]` to keep the fundamental from degenerating to zero on transient rent collapses or running away to infinity on transient rent surges (`property_market.py:121-128`). The valuation cap of `10×` book value is acknowledged in the spec's audit-resolution log as the binding constraint on the magnitude of speculative bubbles the simulation can express: real bubbles can exceed this multiple, and the cap is documented as a tunable design parameter rather than a structural bound. The four era templates inherit the per-property base values from `_PROPERTIES_BASE` in `template_loader.py:66-85` (farmland 200, workshop 150, shop 100 in primary-currency units), with the industrial template adding a factory at base value 500, the modern template adding a factory at 500 and an office at 300, and the sci-fi template adding an automated factory at 1 000 and a research lab at 800; the per-era differentiation is qualitative (which property types are available rather than what their parameters are) and the homogeneity of base values across eras is a Plan 4 calibration deliverable rather than a substantive design choice.

**Algorithm.** On every tick, the economy orchestrator invokes `process_property_listings(simulation, tick)` exactly once, gated by the same `credit_processed` flag that protects the credit step at `epocha/apps/economy/engine.py:445-503`, and with the explicit ordering note that the property market runs *before* the credit step so that property-sale cash credited to sellers can prevent loan defaults that would otherwise fire at the credit step within the same tick. The function executes five ordered passes. First, a single-query bulk update marks all listings older than `tick − 10` as `withdrawn`, replacing the per-listing iteration with a `.update()` call that is `O(1)` in the number of stale listings. Second, the function reads the previous tick's `DecisionLog` rows whose `output_decision` JSON contains the substring `"buy_property"` and parses each row with `json.loads()` to recover the `action` field; rows with malformed JSON are silently skipped, on the grounds that the LLM occasionally produces invalid JSON and a hard failure on parse would propagate an LLM failure into a tick-pipeline failure. Third, for each parsed buyer the function checks the four conjuncts of (4.14) in order and selects the cheapest qualifying listing via `order_by("asking_price", "id").first()` (the id tiebreak pins equal-priced listings deterministically, and buyers are processed in agent-id order, both for seeded reproducibility); the zone-locality conjunct is enforced by the `property__zone_id=buyer.zone_id` filter, the self-purchase exclusion by `.exclude(property__owner=buyer)`, and the cash check by reading `AgentInventory.cash[currency_code]` against the listing's asking price. Fourth, when all conjuncts hold, the function executes the four-step settlement in a deterministic order: cash is deducted from the buyer's `AgentInventory.cash`, credited to the seller's `AgentInventory.cash` (creating an inventory row for the seller if missing), -- or, when the listed property has no agent owner (government or public land), the sale price is credited to the government treasury via `add_to_treasury`, and the sale is skipped before any debit if no Government exists, so the buyer's debit always has a matching credit -- the property's `owner` and `owner_type` fields are reassigned to the buyer, and the listing's `status` is set to `"sold"`; the four writes are independent `save(update_fields=[...])` calls rather than a single transaction because the surrounding simulation tick is wrapped in a transaction at the simulation engine level (`epocha/apps/simulation/engine.py`), not the economy orchestrator. Fifth, an `EconomicLedger` row is created with `transaction_type="property_sale"` (added to `TRANSACTION_TYPES` by the same 2026-04-15 convergence) recording the cash flow from buyer to seller. The function returns a `{"matched": M, "expired": E, "failed": F}` dictionary that the orchestrator logs at `INFO` level for per-tick observability. The pass is `O(n_buyers · log n_listings)` per tick because the per-buyer query plan uses the `(zone, status, asking_price)` ordering rather than a full table scan, and the entire per-tick cost is bounded above by the live agent count for the buyer enumeration and by the active listing count for the per-buyer matching.

**Simplifications.** The current implementation deliberately omits four refinements that the property-market literature treats as proper extensions rather than corrections of the baseline mechanism. First, listings are matched once per tick in a single round: a buyer who has the cash for a listing but loses to another buyer ordered earlier in the iteration receives no second chance within the same tick, and a buyer whose only viable listing in the current zone is just above its budget cannot counter-offer at a lower price. Multi-round negotiation with bid-ask convergence is recorded in the spec as a deferred refinement, on the grounds that it would interact with the LLM context budget of §3.5 in ways that need a separate calibration pass. Second, listings do not persist their original ordering across the listing-expiration window: a listing posted at tick `T` competes with a listing posted at tick `T+5` purely on price, so an early-posted listing receives no priority for being on the market longer; a time-priority refinement (FIFO across listings at the same price) is recorded as a deferred extension. Third, the buyer's intent is binary rather than parameterized: a `buy_property` action does not carry a target type or a maximum price, and the matching pass selects the cheapest listing in the buyer's zone regardless of fit between the property's `production_bonus` and the buyer's role; a target-typed intent that filters listings by property type or by production-bonus alignment is the natural extension once the LLM action grammar of §3.2 is broadened to support typed parameters. Fourth, the asking-price formation rule that produces the divergence between `asking_price` and `fundamental_value` is documented in the `sell_property` action at the LLM-decision layer of §3.2 rather than at the property-market layer, and consequently this subsection treats the asking price as an exogenous input to the matching condition (4.14); the speculative-anchoring and personality-modulation logic that produces the divergence is the subject of the seller-side decision pipeline and is documented in §3.2.

## 4.3 Reputation

> Status: implemented as of commit `c196281d706f63d6a9270c9b26e5c9044067d785`, code audit CONVERGED 2026-05-12 round 2.

### Background

Reputation in Epocha implements the image/reputation distinction introduced
by Castelfranchi, Conte and Paolucci (1998). Image is the holder's
first-hand assessment of a target, updated by direct observation. Reputation
is the holder's socially propagated assessment, updated by hearsay from
information-flow propagation (chapter 4.4) and weighted by source reliability.
The asymmetry between negative and positive image-update magnitudes is
qualitatively inspired by the negativity-bias principle (Baumeister et al.
2001) without claiming any specific quantitative ratio from that meta-review.
The numerical scale `[-1, 1]` is an implementation decision typical of
computational reputation systems (e.g. ReGreT — Sabater and Sierra 2002) and
not prescribed by Castelfranchi et al. (1998).

### Model

Two scalar fields are maintained per (holder, target) pair:
- Image: bounded in [-1, 1], updated by direct observation only
- Reputation: bounded in [-1, 1], updated by hearsay only with reliability dampening

A combined trustworthiness score is exposed for downstream consumers (e.g. the
agent decision pipeline at `agents/decision.py`) via a single source of truth
in `agents/reputation.py`.

### Equations

Equation (4.16) — Image update on observed action of type a:

  image_{t+1} = clip(image_t + Δ_image[a], -1, 1)

where Δ_image[a] is a tunable per-action delta (positive for prosocial actions,
negative for antisocial actions; magnitudes for negative actions deliberately
larger than for positive actions to encode the negativity bias).

Equation (4.17) — Reputation update on hearsay with sentiment s and reliability r:

  reputation_{t+1} = clip(reputation_t + s · r · ζ, -1, 1)

where ζ = 0.5 is a dampening factor that prevents a single hearsay event of
maximum sentiment from a perfectly reliable source from moving reputation by
more than 0.5 (tunable, no empirical source).

Equation (4.18) — Combined trustworthiness score:

  combined = w_I · image + w_R · reputation

where w_I = 0.6 and w_R = 0.4 are tunable weights expressing the qualitative
primacy of direct experience over hearsay (Castelfranchi et al. 1998 for the
conceptual distinction; the specific 0.6/0.4 ratio is a design choice).

### Parameters

| Parameter | Symbol | Value | Source/Status |
|---|---|---|---|
| Image delta on `help` | Δ_image[help] | +0.15 | tunable design |
| Image delta on `socialize` | Δ_image[socialize] | +0.10 | tunable design |
| Image delta on `betray` | Δ_image[betray] | -0.80 | tunable design |
| Image delta on `crime` | Δ_image[crime] | -0.60 | tunable design |
| Image delta on `argue` | Δ_image[argue] | -0.20 | tunable design |
| (other action types) | various | various | tunable design (full table at `agents/reputation.py:43-89` _IMAGE_DELTAS) |
| Reputation dampening | ζ | 0.5 | tunable design (`agents/reputation.py:_DAMPENING_FACTOR`-equivalent inline) |
| Combined image weight | w_I | 0.6 | tunable design (`agents/reputation.py:_WEIGHT_IMAGE`) |
| Combined reputation weight | w_R | 0.4 | tunable design (`agents/reputation.py:_WEIGHT_REPUTATION`) |
| Loan default observer sentiment | — | -0.7 | tunable design (`agents/reputation.py:_LOAN_DEFAULT_OBSERVER_SENTIMENT`); inspired by economic-sociology literature on reputational sanctions (Diamond 1989; Greif 1993; Karlan 2005) |
| Loan default lender sentiment | — | -0.9 | tunable design (`agents/reputation.py:_LOAN_DEFAULT_LENDER_SENTIMENT`) |

### Algorithm

When an agent observes a target performing an action, `update_image(holder, target, action_type, tick)` is called (`agents/reputation.py:update_image`). The function uses `transaction.atomic()` with `select_for_update()` on the ReputationScore row to prevent lost-update races under concurrent Celery worker execution. If `action_type` is unknown to the `_IMAGE_DELTAS` table, a WARNING-level log is emitted and the image is left unchanged.

When an agent receives hearsay about a target, `update_reputation(holder, target, action_sentiment, reliability, tick)` is called (`agents/reputation.py:update_reputation`) with the same concurrency protection. The hearsay sentiment is either extracted from free-text content via `extract_action_sentiment` (placeholder rule-based heuristic) or supplied directly by the calling domain module (e.g. `economy/credit.py` calls with `_LOAN_DEFAULT_OBSERVER_SENTIMENT` and `_LOAN_DEFAULT_LENDER_SENTIMENT` for loan default events).

The `extract_action_sentiment` keyword extractor uses a loudest-keyword-wins heuristic with placeholder positive and negative keyword tables; it is documented as a known simplification pending replacement by an embedding-based or LLM-based sentiment classifier.

### Simplifications

1. **No temporal decay**: image and reputation accumulate indefinitely. Old observations from tick 1 carry the same weight as observations from tick 1000. Castelfranchi et al. (1998) discusses ongoing maintenance through social communication, which is not implemented; a recency-weighting mechanism is deferred to a future iteration.

2. **Immediate clamp vs. cumulative aggregation**: image and reputation are clamped to [-1, 1] after every update. This causes saturation: roughly 1/Δ observations of the same action type fully saturate the field, after which subsequent observations have no effect. Alternative aggregation schemes (running average, beta-distribution posterior — Beta Reputation System, Jøsang and Ismail 2002 — Bayesian update) would avoid the saturation effect at the cost of additional state per observation. This trade-off is accepted for the current implementation.

3. **Sentiment extraction limitations**: the `extract_action_sentiment` heuristic returns the keyword with the highest absolute value (loudest-keyword-wins). It does not handle negation ("did not help" still scores positively for "help"), does not aggregate across keyword matches (a sentence containing both prosocial and antisocial keywords returns only the strongest), and does not perform sentence-level sentiment analysis. These limitations bias hearsay-derived reputation toward whichever sentiment pole is most lexically intense in the keyword tables.

4. **No contextual reputation**: a single global reputation score is maintained per (holder, target) pair. Roles (e.g. trader vs friend) are not differentiated.

5. **Action vocabulary coverage**: `_IMAGE_DELTAS` covers 17 action types emitted by the simulation engine. Action types not in the table produce zero image change with a WARNING log; this is enforced by the unknown-action_type log to prevent silent drift between engine and reputation table.



## 4.4 Rumor propagation

> Status: implemented as of commit `a0ea07556ce8b32cea89ad543660fcb81be06b6e`, code audit CONVERGED 2026-05-16 round 2.

The rumor propagation cluster transcribes Bartlett (1932) on serial reproduction and Allport and Postman (1947) on assimilation (partial — only the assimilation mechanism is implemented; leveling and sharpening are documented Known Limitations) into a four-stage pipeline. The first stage, `agents/information_flow.py`, propagates memories along agent relationship graphs over up to three hops per tick. The second stage, `agents/distortion.py`, applies personality-modulated text transformations driven by the reteller's Big Five vector before the message reaches the next recipient. The third stage, `agents/belief.py`, filters acceptance via a weighted score that combines information reliability, relationship trust, receiver personality, and transmitter reputation. The fourth stage, `agents/affinity.py`, contributes the Big Five personality similarity score that the belief filter consumes through the relationship trust component and that downstream factions consume during coalition formation.

Granovetter (1973) on the structural role of weak ties is cited in `information_flow.py` as the conceptual framing for cross-cluster bridging but is explicitly NOT implemented at the propagation layer: memories propagate equally regardless of tie strength, with no weak-tie weighting on propagation probability. The weak-tie weighting is documented as a Known Limitation and tracked for a future iteration; the cited reference is preserved as a citation-without-implementation per the Round 2 audit's IF-1 closure.

### 4.4.1 Information flow

> Status: implemented as of commit `a0ea07556ce8b32cea89ad543660fcb81be06b6e`, code audit CONVERGED 2026-05-16 round 2.

#### Background

Information flow operationalises Bartlett (1932) on serial reproduction: a memory passed agent-to-agent loses fidelity at every hop. Bartlett documents the degradation qualitatively rather than as a specific geometric law; the geometric reliability decay adopted by the implementation is a tunable design parameter inscribed in the era template and is not claimed as a direct Bartlett result. Granovetter (1973) on the strength of weak ties is cited as the conceptual frame for the cross-cluster bridging role of low-strength relationships but is explicitly NOT implemented at the propagation layer (see chapter intro).

#### Model

Each tick, the propagator runs four phases against the simulation's memory store. Phase 1 selects direct memories created at the current tick whose `emotional_weight` exceeds the propagation threshold and transmits them to the agent's social neighbours as hearsay (hop 1). Phase 2 takes the hearsay created at the previous tick and forwards it as rumor (hop 2). Phase 3 takes the rumors created at the previous tick and forwards them as further rumors as long as the estimated hop count is below the cap. Phase 4 broadcasts the tick's public events to every living agent regardless of social distance. Belief filtering at each receiver decides whether the incoming memory becomes a full memory at the receiver's emotional weight or a weak rumor at a damped weight that still propagates downstream without influencing decisions.

#### Equations

Equation (4.19) — Reliability decay across propagation hops:

  reliability_{h+1} = reliability_h · δ

with δ = `EPOCHA_INFO_FLOW_RELIABILITY_DECAY` = 0.7 by default. The compounding form yields 0.7^3 ≈ 0.34 after three hops and 0.7^5 ≈ 0.17 after five hops.

Equation (4.20) — Hop estimation by inverting the decay relation:

  hop = round( log(reliability) / log(δ) )

The estimator assumes initial reliability = 1.0; memories that originate with reliability < 1.0 are overestimated in hop count (Known Limitation IF-4).

Equation (4.21) — Weak-rumor downstream parameters when the belief filter rejects:

  emotional_weight_weak = w_weak
  reliability_weak     = reliability_h · δ · d_weak

with w_weak = `EPOCHA_INFO_FLOW_WEAK_RUMOR_WEIGHT` = 0.1 and d_weak = `EPOCHA_INFO_FLOW_WEAK_RUMOR_DAMP` = 0.3.

#### Parameters

| Parameter | Symbol | Value | Source/Status |
|---|---|---|---|
| Propagation threshold | — | 0.3 | tunable design (`EPOCHA_INFO_FLOW_PROPAGATION_THRESHOLD`); prevents trivial observations from flooding the network |
| Per-hop reliability decay | δ | 0.7 | tunable design (`EPOCHA_INFO_FLOW_RELIABILITY_DECAY`); Bartlett (1932) documents degradation qualitatively without prescribing a rate |
| Maximum propagation hops | — | 3 | tunable design (`EPOCHA_INFO_FLOW_MAX_HOPS`) |
| Recipients per propagation step | — | 20 | tunable design (`EPOCHA_INFO_FLOW_MAX_RECIPIENTS`); caps fan-out per memory |
| Weak-rumor emotional weight | w_weak | 0.1 | tunable design (`EPOCHA_INFO_FLOW_WEAK_RUMOR_WEIGHT`) |
| Weak-rumor reliability damping | d_weak | 0.3 | tunable design (`EPOCHA_INFO_FLOW_WEAK_RUMOR_DAMP`) |

#### Algorithm

`propagate_information(simulation, tick)` at `agents/information_flow.py:39-181` runs the four-phase pass. Phase 1 (`information_flow.py:71-90`) reads direct memories from this tick above the threshold and calls `_propagate_memory()` with `target_source_type = HEARSAY`. Phase 2 (`information_flow.py:103-121`) reads hearsay from the previous tick and calls the same helper with `target_source_type = RUMOR`; the propagation threshold is deliberately NOT enforced at this phase, modelling the gossip property that downstream agents retransmit what they have already heard regardless of personal salience (Round 2 audit finding N-9 closure). Phase 3 (`information_flow.py:124-145`) reads rumors from the previous tick, estimates the current hop via equation (4.20), and propagates further only when below `max_hops`. Phase 4 (`information_flow.py:148-170`) broadcasts public events with `Memory.objects.get_or_create()` keyed on `(agent, source_type=PUBLIC, tick_created, origin_agent=None, content=content)` — the `content` field is part of the lookup so that two distinct public events firing on the same tick produce two memories per agent rather than coalescing (Round 2 audit finding IF-5 closure). The per-memory helper `_propagate_memory()` (`information_flow.py:184-341`) extracts sentiment from the undistorted source content (Round 2 finding N-3: distorting first would let high-neuroticism transmitters inflate negative sentiment), distorts the content for the recipient via `distort_information()`, always updates the recipient's reputation toward the origin agent, queries `get_combined_score()` for the transmitter reputation signal, and calls `should_believe()` to decide whether to create a full memory or a weak-rumor downstream.

#### Simplifications

1. **IF-1 — Granovetter weak-tie weighting not implemented**: propagation probability does not depend on tie strength. The cited reference is preserved as a conceptual frame; the operational implementation is deferred to a future iteration. Documented as Known Limitation.

2. **IF-4 — Hop overestimation when initial reliability < 1.0**: equation (4.20) inverts `reliability = δ^hop` under the assumption of initial reliability 1.0. A memory originating from a public event with severity < 1.0 begins with reliability < 1.0 and is therefore counted as already having traversed phantom hops, causing premature propagation termination. The behavioral fix would require a `hop_count` `PositiveSmallIntegerField` on the Memory model with a backfill migration; deferred.

3. **IF-5 — Public-event deduplication keys on content**: addressed in 2026-05-16 round 2 — the `get_or_create()` lookup at `information_flow.py:160-170` includes the `content` field so that two distinct public events firing on the same tick produce two memories per agent. The pre-audit form coalesced same-tick public events into a single record.

4. **N-9 — Phase 2 threshold asymmetry**: Phase 2 (hearsay → rumor) deliberately does NOT enforce `emotional_weight >= EPOCHA_INFO_FLOW_PROPAGATION_THRESHOLD`. The threshold gates entry into the rumor network at hop 1; once a memory has been deemed worth transmitting upstream, downstream agents retransmit regardless of personal salience. This is the gossip property and is documented inline at `information_flow.py:93-102`. If this asymmetry is undesired, enforce the threshold consistently across phases.

### 4.4.2 Distortion

> Status: implemented as of commit `a0ea07556ce8b32cea89ad543660fcb81be06b6e`, code audit CONVERGED 2026-05-16 round 2.

#### Background

Distortion implements the assimilation mechanism of Allport and Postman (1947), *The Psychology of Rumor*: the reteller's strong pre-existing attitudes act as a filter that bends the rumor toward those attitudes. Allport and Postman describe three mechanisms — leveling (progressive detail loss), sharpening (selective emphasis), and assimilation (reshaping toward the reteller's schema). Only assimilation is implemented in the current module; leveling and sharpening are documented as Known Limitations. The personality basis is the five-factor model of Costa and McCrae (1992), with Big Five trait extremity selecting which assimilation pattern fires.

#### Model

The distorter inspects the reteller's Big Five vector and selects up to `_MAX_ACTIVE_TRAITS = 2` traits whose value crosses the extreme thresholds. For each active trait, a graduated set of regex substitutions is applied at one of three strength bands (mild, moderate, strong) determined by the distance from the threshold. Each pattern's first match wins (source-order deliberate, Round 2 audit N-4 closure); subsequent patterns within the same trait do not fire, modelling the observation that a single dominant bias typically reshapes the most salient element of a message rather than every word simultaneously.

#### Equations

Equation (4.22) — Trait extremity threshold mapping:

  active(t) = 1 if value(t) ≥ θ_high OR value(t) ≤ θ_low; else 0

with θ_high = `_HIGH_THRESHOLD` = 0.7 and θ_low = `_LOW_THRESHOLD` = 0.3. The strength index 0/1/2 (mild/moderate/strong) is computed by partitioning the distance from the threshold into three equal bands; full derivation at `distortion.py:148-185`.

#### Parameters

| Parameter | Symbol | Value | Source/Status |
|---|---|---|---|
| High-extremity threshold | θ_high | 0.7 | tunable design (`distortion.py:_HIGH_THRESHOLD`); Allport and Postman (1947) do not prescribe a numeric cutoff |
| Low-extremity threshold | θ_low | 0.3 | tunable design (`distortion.py:_LOW_THRESHOLD`); symmetric counterpart of θ_high |
| Maximum concurrent active traits | — | 2 | tunable design (`distortion.py:_MAX_ACTIVE_TRAITS`); higher values produce text that diverges too rapidly across hops |

#### Algorithm

`distort_information(content, personality)` at `distortion.py:270-306` is a pure function: no I/O, no database access. `_select_active_traits()` (`distortion.py:188-215`) ranks Big Five traits by `abs(value - 0.5)` and returns the top two crossing the extremity thresholds. For each active trait, `_TRAIT_PATTERNS[trait]` yields a (high_patterns, low_patterns) tuple and the appropriate side is selected by trait direction. `_apply_patterns()` (`distortion.py:218-257`) iterates the pattern list in declaration order, applies the first match at the selected strength band via `pattern.sub(replacement, content, count=1)`, and stops. The two active traits are applied sequentially so the first trait's substitution may consume the token the second trait would have matched; this is correct behaviour for a dominant-reframe model. The high-neuroticism, low-neuroticism, high-agreeableness, low-agreeableness, high-openness, low-openness, high-extraversion, low-extraversion, high-conscientiousness, and low-conscientiousness pattern tables are inlined at `distortion.py:63-145`.

#### Simplifications

1. **D-1 — Sharpening and leveling not implemented**: Allport and Postman (1947) describe three serial-reproduction mechanisms (leveling, sharpening, assimilation); only assimilation is implemented. Leveling would be modeled as progressive sentence truncation across propagation hops; sharpening would be modeled as keyword emphasis or repetition for contextually salient terms. Deferred; documented as Known Limitation.

2. **D-4 — High-openness multi-hop pattern accumulation**: the high-openness pattern (`_HIGH_OPENNESS_PATTERNS` at `distortion.py:99-107`) inserts a speculative clause (" -- perhaps for a reason. ") after every period-space boundary in the input. Across multiple propagation hops with high-openness retellers, three-sentence inputs accumulate three speculative qualifiers, then nine after another hop, then twenty-seven. The accumulation is pathological. Future work could restrict insertion to the first or last sentence boundary, or cap by transmitter count. Documented as Known Limitation; no code change in current iteration.

3. **D-5 — Low-conscientiousness proper-noun anonymization is over-broad**: the low-conscientiousness pattern (`_LOW_CONSCIENTIOUSNESS_PATTERNS` at `distortion.py:137-145`) replaces all mid-sentence capitalized words with "somebody" / "someone" / "this person". This destroys non-person proper nouns (city names, place names, titles), not just person names. A NER pre-pass or a position-restricted pattern (e.g. only after relational verbs "with X", "to X") would fix it. Documented as Known Limitation; no code change in current iteration.

4. **N-4 — Source-order first-match-wins is deliberate**: pattern lists are evaluated in declaration order and the first matching pattern wins. Patterns are listed in order of intended linguistic priority within each personality block (e.g. the high-neuroticism block lists `argued`, `disagreed`, `criticized`, `disappointed`, `went wrong` so that `argued` substitutions take precedence over `disagreed` substitutions when both could match the same input). Closes Round 2 finding N-4 by documenting the source-order assumption as deliberate rather than refactoring to a match-all-pick-strongest scheme.

### 4.4.3 Belief filter

> Status: implemented as of commit `a0ea07556ce8b32cea89ad543660fcb81be06b6e`, code audit CONVERGED 2026-05-16 round 2.

#### Background

The belief filter decides whether the receiver accepts an incoming piece of information as a full memory or downgrades it to a weak rumor. The structure is loosely inspired by Mayer, Davis and Schoorman (1995), *An Integrative Model of Organizational Trust*, which decomposes trust into ability, benevolence, and integrity; the implementation does not claim to operationalise those constructs and adopts a four-component weighted score whose components are operational rather than psychometric. The personality contribution is grounded in Graziano and Tobin (2002), who link agreeableness to cooperative information processing; the openness contribution to the personality factor is an Epocha design choice without specific empirical support from that paper. The network-reputation contribution is supported by Castelfranchi, Falcone and Tan (2001), *The Role of Trust and Deception in Virtual Societies* (HICSS-34), which establishes the principle of using network-level reputation as a credibility signal in multi-agent systems.

#### Model

The acceptance score is a convex combination of four signals: information reliability (after per-hop decay), relationship trust between receiver and transmitter, receiver personality, and the transmitter's reputation as perceived by the wider network. The receiver accepts the memory when the acceptance score crosses the configured threshold; otherwise it generates the weak-rumor downstream of equation (4.21).

#### Equations

Equation (4.23) — Acceptance score:

  acceptance = w_r · reliability + w_t · trust + w_p · personality + w_rep · reputation_norm

with weights w_r = 0.3, w_t = 0.2, w_p = 0.2, w_rep = 0.3. The components are defined as follows. Trust = (relationship_strength + max(0, relationship_sentiment)) / 2. Personality = 0.6 · agreeableness + 0.4 · openness. reputation_norm normalises the combined image+reputation score from [-1, 1] to [0, 1] via the single source of truth at `reputation.py:_normalize_reputation()` (Round 2 finding N-5 closure). Acceptance is `acceptance ≥ τ_b` with τ_b = `EPOCHA_INFO_FLOW_BELIEF_THRESHOLD` = 0.4.

#### Parameters

| Parameter | Symbol | Value | Source/Status |
|---|---|---|---|
| Reliability weight | w_r | 0.3 | tunable design (`belief.py:89-94`) |
| Relationship trust weight | w_t | 0.2 | tunable design (`belief.py:89-94`) |
| Personality weight | w_p | 0.2 | tunable design (`belief.py:89-94`) |
| Reputation weight | w_rep | 0.3 | tunable design (`belief.py:89-94`) |
| Agreeableness contribution to personality | — | 0.6 | Graziano and Tobin (2002) link agreeableness to cooperative information processing |
| Openness contribution to personality | — | 0.4 | tunable design (`belief.py:79`); not supported by the Graziano and Tobin (2002) paper |
| Acceptance threshold | τ_b | 0.4 | tunable design (`EPOCHA_INFO_FLOW_BELIEF_THRESHOLD`); neutral 0.5 inputs yield acceptance, favouring information propagation over skepticism |

#### Algorithm

`should_believe(reliability, receiver_personality, relationship_strength, relationship_sentiment, transmitter_reputation)` at `belief.py:28-101` evaluates equation (4.23) and returns the boolean acceptance decision. Negative `relationship_sentiment` is clamped to zero in the trust component: distrust does not increase trust (`belief.py:68-69`). The reputation normalisation delegates to `reputation._normalize_reputation()` via lazy import to avoid the circular dependency between `belief.py` and `reputation.py` (Round 2 finding N-5 closure). The default `transmitter_reputation = 0.0` maps to a neutral reputation factor of 0.5, preserving backward compatibility for callers that do not yet supply the argument.

#### Simplifications

1. **Mayer (1995) loosely inspired, not strictly implemented**: the belief filter borrows the conceptual idea of decomposing trust into multiple components but does not implement the ability/benevolence/integrity constructs of the original framework or their measurement methods. The four-component score is operational rather than psychometric. Acknowledged inline in the module docstring.

2. **Openness contribution to personality factor is a design choice**: Graziano and Tobin (2002) support the agreeableness contribution but do not extend to openness. The 0.4 weight on openness in the personality factor is justified by the qualitative argument that open individuals may be more receptive to novel information; it is documented as a design choice without specific empirical support and is exposed as a tunable parameter.

3. **Acceptance threshold favours propagation over skepticism**: with all neutral inputs (0.5), the acceptance score is 0.5, which exceeds the 0.4 threshold — neutral agents accept information by default. This is an intentional design choice. Setting τ_b above 0.5 would invert the bias to favour skepticism.

### 4.4.4 Affinity

> Status: implemented as of commit `a0ea07556ce8b32cea89ad543660fcb81be06b6e`, code audit CONVERGED 2026-05-16 round 2.

#### Background

Affinity is the pairwise score that quantifies how likely two agents are to form or join the same faction, and is consumed downstream by the factions module and by the relationship-trust component of the belief filter. Personality similarity is grounded in McCrae and Costa (2003), *Personality in Adulthood* (2nd ed., Guilford Press): the five-factor model is the standard framework for measuring inter-individual personality similarity. The circumstance component is inspired by Olson (1965), *The Logic of Collective Action*: groups form around shared material conditions, not just personality fit. The rivalry-as-affinity heuristic in the relationship score draws on Axelrod (1984), *The Evolution of Cooperation*, for the repeated-interaction reciprocity dynamics that make even hostile relationships coalitionally relevant (Round 2 finding N-8 closure).

#### Model

The affinity score is a weighted average of three orthogonal dimensions: personality similarity (Big Five Euclidean distance), relationship quality (strength plus positive sentiment), and circumstance alignment (class, mood, shared crisis memory, wealth quartile, occupational role). The weights (0.3 / 0.3 / 0.4) reflect the qualitative judgment that factions form primarily around shared material circumstances rather than personality match.

#### Equations

Equation (4.24) — Big Five personality similarity:

  similarity = 1 − ( sqrt( Σ_t (a_t − b_t)² ) / sqrt(5) )

where the sum runs over the five Big Five traits and the denominator sqrt(5) is the maximum Euclidean distance when each trait is in [0, 1]. Missing traits default to 0.5 (the midpoint of [0, 1] — a neutral uninformative prior); the asymmetric behaviour when only one agent is missing a trait is documented as N-7 simplification.

Equation (4.25) — Composite affinity score:

  affinity = w_P · similarity + w_R · relationship + w_C · circumstance

with w_P = 0.3, w_R = 0.3, w_C = 0.4. The relationship component is (strength + max(0, sentiment)) / 2; the circumstance component sums additive factors capped at 1.0 (see Parameters table).

#### Parameters

| Parameter | Symbol | Value | Source/Status |
|---|---|---|---|
| Personality weight | w_P | 0.3 | tunable design (`affinity.py:_W_PERSONALITY`); McCrae and Costa (2003) for the Big Five basis |
| Relationship weight | w_R | 0.3 | tunable design (`affinity.py:_W_RELATIONSHIP`) |
| Circumstance weight | w_C | 0.4 | tunable design (`affinity.py:_W_CIRCUMSTANCE`); Olson (1965) for the primacy-of-circumstances framing |
| Default missing trait value | — | 0.5 | tunable design (`affinity.py:_TRAIT_DEFAULT`); neutral uninformative prior |
| Shared-memory recency window | — | 10 ticks | tunable design (`affinity.py:_SHARED_MEMORY_WINDOW`) |
| Same social class additive bonus | — | +0.30 | tunable design |
| Both mood < 0.4 additive bonus | — | +0.20 | tunable design |
| Shared recent public memory bonus | — | +0.20 | tunable design |
| Same wealth quartile bonus | — | +0.15 | tunable design (threshold: `abs(w_a - w_b) / max(w_a, w_b) < 0.25`) |
| Same occupational role bonus | — | +0.15 | tunable design |

#### Algorithm

`compute_affinity(agent_a, agent_b, tick)` at `affinity.py:61-91` orchestrates the three components and returns a symmetric score clamped to [0.0, 1.0]. Personality similarity uses `_personality_similarity()` (`affinity.py:94-126`), which implements equation (4.24) with the default-to-midpoint trait imputation (Round 2 finding N-7 closure documents the asymmetric behaviour when only one agent is missing a trait). The relationship score uses `_relationship_score()` (`affinity.py:129-176`), which performs a bidirectional `Relationship.objects.get()` lookup and falls back to the strongest record on `MultipleObjectsReturned`; the rivalry-as-affinity heuristic (only positive sentiment boosts the score; negative sentiment does not reduce it below the strength baseline) is justified by Axelrod (1984) repeated-interaction reciprocity and the broader observation that even hostile relationships involve high interdependence (Round 2 finding N-8 closure). The circumstance score uses `_circumstance_score()` (`affinity.py:179-250`), which evaluates the five additive bonuses against PostgreSQL-backed memory and agent queries with the shared-memory window enforced via `tick_created__gte=tick - _SHARED_MEMORY_WINDOW`. The `max_wealth > 0.0` guard prevents division by zero when both agents have zero wealth (treated as same quartile by definition).

#### Simplifications

1. **N-7 — Asymmetric missing-trait imputation**: when both agents are missing a Big Five trait, the dimension contributes zero distance; when only one agent is missing the trait, the present value is compared against 0.5, producing a non-zero distance proportional to how far the present value is from neutral. This asymmetric behaviour is a known limitation of the default-to-midpoint imputation and is documented inline. A more principled approach (e.g. multiple imputation, or explicitly skipping the dimension on either-side missingness) is deferred.

2. **N-8 — Rivalry-as-affinity heuristic**: the relationship score takes (strength + max(0, sentiment)) / 2 — negative sentiment does not subtract from the score below the strength baseline. The heuristic is justified by Axelrod (1984) repeated-interaction reciprocity and Coleman (1990) on coalition stability under rivalry (Coleman 1990 is referenced inline but NOT in whitepaper §13 References); rivalry concentrates social attention and produces a coalitional dynamic that pure liking cannot capture. The choice is documented; an alternative scheme that penalises rivalry is open for future calibration.

3. **Wealth quartile threshold is relative**: the same-quartile bonus uses `abs(w_a - w_b) / max(w_a, w_b) < 0.25` rather than an absolute wealth difference. The relative form scales naturally across era templates with different absolute wealth distributions; the 0.25 threshold is a tunable design parameter.

## 4.5 Political institutions

> Status: implemented as of commit `dfeb709218727c1efbca8cbee5e0dc6e974923fe`, code audit CONVERGED 2026-05-16 round 2.

The political institutions cluster covers regime dynamics, election scoring,
institutional accumulation/decay, and stratification (social class + corruption).
Five modules under `epocha/apps/world/`:

1. `government.py` — regime types, transitions, coups, legitimacy, stability
2. `government_types.py` — 12 regime templates with institution effects
3. `institutions.py` — health accumulation per institution type
4. `stratification.py` — Gini, social classes, corruption mechanics
5. `election.py` — voting model with personality, reputation, economy, charisma

Acemoglu and Robinson (2006); Bueno de Mesquita et al. (2003); Geddes (1999);
Polity 5 (Marshall and Gurr 2020); Powell and Thyne (2011); Freedom House;
plus the regime typology and voting literature surveyed in §13 References.

### 4.5.1 Government (regime + coup)

> Status: implemented as of commit `dfeb709218727c1efbca8cbee5e0dc6e974923fe`, code audit CONVERGED 2026-05-16 round 2.

#### Background

`government.py` orchestrates the per-tick political cycle: regime transitions,
coup resolution, legitimacy and stability bookkeeping, and the indicator
updates that feed downstream election scoring and economy political feedback.
The regime typology covers the 12 archetypes declared in `government_types.py`
and draws on Geddes (1999) for the empirical regime-survival shape, on the
Polity 5 dataset (Marshall and Gurr 2020) for the regime-classification spine,
and on Freedom House annual reports for the qualitative trajectory of
institutional erosion in declining democracies.

#### Model

Regime transitions follow the endogenous-mechanism framing of
Acemoglu and Robinson (2006) and the regime-survival hazard structure of
Geddes (1999): the engine evaluates trigger conditions per regime type and
flips to the configured successor when the trigger fires. The coup decision
is stochastic — the computed coup-score is interpreted as a success
probability against a `random.random()` draw — calibrated against the
empirical ~50% all-attempts success rate reported by Powell and Thyne (2011);
the legacy deterministic-threshold form is recorded as Round 2 finding G-2
and explicitly closed. Stability is recomputed each cycle as a convex
combination of economy, legitimacy and military-loyalty components whose
weights are pulled per-regime from `government_types.py`.

#### Equations

Equation (4.26) — Coup probability score:

  coup_probability = 0.4·cohesion + 0.3·leader_charisma + 0.3·(1 − military_loyalty)

The score is consumed as a success probability against
`random.random() < coup_probability`. The triple-weight form follows the
narrative observation that coups require organised internal cohesion, a
focal leader, and a military that is not committed to the incumbent; the
exact weights are tunable design parameters.

**RNG reproducibility (sibling of §4.6 finding N-8)**: the
`random.random()` draw at `government.py:618` uses Python's global RNG, not
the simulation-seeded `get_seeded_rng`. As with the movement arrival-scatter
of §4.6, the coup outcome is therefore not reproducible from the simulation
seed — two identically-seeded runs can differ on whether a coup succeeds.
Future work: thread the simulation RNG into `government.py`.

Equation (4.27) — Stability index:

  stability = w_economy·economy + w_legitimacy·legitimacy + w_military·military_loyalty

with per-regime weights `(w_economy, w_legitimacy, w_military)` read from
`GOVERNMENT_TYPES[regime].stability_weights` (e.g. democracy weights economy
and legitimacy heavily; military regimes weight loyalty heavily).

#### Parameters

| Parameter | Symbol | Value | Source/Status |
|---|---|---|---|
| Institutional trust decay per cycle | — | 0.05 | tunable design (`government.py:_TRUST_DECAY`); qualitatively consistent with Freedom House annual reports |
| Repression drift rate per cycle | — | 0.10 | tunable design (`government.py:_REPRESSION_DRIFT_RATE`) |
| Legitimacy weight on health | — | 0.20 | tunable design (`government.py:_LEGITIMACY_W_HEALTH`) |
| Legitimacy weight on education | — | 0.15 | tunable design (`government.py:_LEGITIMACY_W_EDUCATION`) |
| Legitimacy weight on economy | — | 0.35 | tunable design (`government.py:_LEGITIMACY_W_ECONOMY`) |
| Legitimacy weight on media | — | 0.30 | tunable design (`government.py:_LEGITIMACY_W_MEDIA`) |
| Media independence threshold for propaganda inflation | — | 0.30 | tunable design (`government.py:_MEDIA_INDEPENDENCE_THRESHOLD`) |
| Propaganda inflation factor on reported legitimacy | — | +0.30 | tunable design (`government.py:_PROPAGANDA_FACTOR`) |
| Per-regime stability weights | — | per `GOVERNMENT_TYPES` | tunable design (`government_types.py`) |
| Coup base-rate target | — | ~0.50 | Powell and Thyne (2011) empirical anchor |

#### Algorithm

`process_political_cycle(world, tick)` at `government.py` is wrapped in
`@transaction.atomic` and acquires `select_for_update()` on the `Government`
row to prevent the concurrent-tick race that Round 2 audit finding N-6
identified between corruption mutation in `stratification.py:process_corruption`
(political-cycle step 3) and the indicator update in
`government.py:update_government_indicators` (step 4). The 8-step pipeline
is: (1) institution health update; (2) Gini and social-class recomputation;
(3) corruption skim (wealth-conserving, per `stratification.py`); (4)
indicator update (institutional_trust, popular_legitimacy, military_loyalty,
repression_level, with propaganda inflation when media independence is low);
(5) regime-transition evaluation; (6) election scheduling; (7) coup
resolution (stochastic per equation (4.26)); (8) history snapshot. Step 7
selects at most one coup per cycle; when multiple groups satisfy the trigger
threshold, the highest-score group is the one that attempts. The
single-attempt-per-cycle choice is recorded as Round 2 audit finding N-13 and
is documented inline at `government.py` as a deliberate selection bias.

#### Simplifications

1. **G-1 — Legitimacy weights are tunable design parameters**: the four
   weights `(_LEGITIMACY_W_HEALTH, _LEGITIMACY_W_EDUCATION,
   _LEGITIMACY_W_ECONOMY, _LEGITIMACY_W_MEDIA) = (0.20, 0.15, 0.35, 0.30)`
   reflect the assumed relative importance of institutional domains rather
   than an empirical fit. Closed in Round 2 by inline documentation.

2. **G-2 — Coup decision is stochastic, not deterministic**: pre-Round 2 the
   coup decision was a deterministic threshold against the coup score; the
   current implementation evaluates `random.random() < coup_probability`,
   consistent with the Powell and Thyne (2011) empirical base rate of coup
   success. The legacy `_COUP_SUCCESS_THRESHOLD` constant is deprecated.

3. **G-3 — Institutional trust decay rate is tunable**: the 0.05/cycle decay
   is a design choice and is exposed for per-era calibration. Freedom House
   reports document the qualitative pattern of institutional erosion in
   declining democracies but do not publish a per-period decay rate.

4. **G-6 — `stability_index` is used as the economy proxy**: the
   `_update_stability()` and `update_government_indicators()` functions
   consume `World.stability_index` as their "economy" input; the field is
   computed by the economy module as an average-mood signal rather than a
   real economic indicator. The behavioural fix would route the function
   through a dedicated economic indicator once one becomes available; the
   current behaviour is documented inline at `government.py`.

5. **N-13 — Coup selection bias toward highest-score group**: at most one
   coup is resolved per cycle; when multiple groups satisfy the trigger
   threshold, the one with the highest coup score is selected. This biases
   the simulation toward the strongest single contender per cycle rather
   than modelling simultaneous attempts; the choice is documented inline.

### 4.5.2 Government types

> Status: implemented as of commit `dfeb709218727c1efbca8cbee5e0dc6e974923fe`, code audit CONVERGED 2026-05-16 round 2.

#### Background

`government_types.py` declares the 12 regime archetypes that `government.py`
consumes: democracy, illiberal democracy, autocracy, monarchy, oligarchy,
theocracy, totalitarian, terrorist regime, anarchy, federation, kleptocracy,
junta. Each archetype is a dictionary of four attribute groups —
`repression_tendency`, `corruption_resistance`, `institution_effects`,
`stability_weights` — that drive the per-cycle indicator updates of §4.5.1.
The typology and the per-regime attribute differentiation are inspired by
the Polity 5 regime classification (Marshall and Gurr 2020), the Freedom
House measurement methodology, and the selectorate framework of
Bueno de Mesquita et al. (2003).

#### Model

Each regime template carries four attribute groups. `repression_tendency`
sets the asymptote toward which `Government.repression_level` drifts each
cycle in §4.5.1. `corruption_resistance` modulates the corruption-skim
magnitude that `stratification.py:process_corruption` applies.
`institution_effects` declares per-institution-type deltas that augment or
attenuate institutional health in §4.5.3. `stability_weights` is the
`(w_economy, w_legitimacy, w_military)` triple consumed by equation (4.27).

#### Equations

Equation (4.28) — Institution effect under a regime:

  institution_effect = base_value + regime_effect · INSTITUTION_EFFECT_SCALE

with `INSTITUTION_EFFECT_SCALE = 20.0` (from `institutions.py`, see §4.5.3
Parameters). `regime_effect` is the per-(regime, institution-type) entry of
the regime template; `base_value` is the institution's standalone health
delta before regime modulation.

#### Parameters

The full per-regime parameter set is large enough to belong to the
Appendix A parameter dump; the in-chapter view is the structural one — 12
regimes × 4 attribute groups (`repression_tendency` scalar,
`corruption_resistance` scalar, `institution_effects` dict, `stability_weights`
triple). The literature anchors are Polity 5 (Marshall and Gurr 2020) for the
regime classification spine, Freedom House for the methodology that informs
the per-regime ordering, Bueno de Mesquita et al. (2003) for the selectorate
intuition behind the per-regime stability weights, and Acemoglu and Robinson
(2006) for the endogenous-transition shape.

#### Algorithm

A lookup by regime name returns the configuration dictionary that
`government.py` consumes during the political cycle. The module is
data-only and carries no per-tick logic of its own.

#### Simplifications

1. **GT-1 — All values are design parameters, not derived from cited
   sources**: the four attribute groups across all 12 regimes are tunable
   design parameters inspired by the cited literature rather than empirical
   fits. Polity 5 publishes a regime classification but not the per-regime
   `(_TRUST_SCALE, repression_tendency, corruption_resistance,
   institution_effects, stability_weights)` quintuple in the form Epocha
   consumes. The module-level disclaimer documents this explicitly; closed
   by Round 2 audit.

### 4.5.3 Institutions

> Status: implemented as of commit `dfeb709218727c1efbca8cbee5e0dc6e974923fe`, code audit CONVERGED 2026-05-16 round 2.

#### Background

`institutions.py` carries the per-institution health dynamics that the
political cycle consumes. The model is qualitatively inspired by the
inequality-of-institutions framework of Acemoglu and Robinson (2012),
*Why Nations Fail*, and by the state-capacity treatment of Besley and
Persson (2011), *Pillars of Prosperity*. Each institution carries a scalar
`health ∈ [0, 1]` that decays at a configurable entropy rate, is augmented
by funding, and is modulated by the per-regime institution effects of
§4.5.2.

#### Model

Each cycle, every institution's health is updated by three additive
contributions: funding (proportional to the institution's `funding_level`),
regime modulation (the `regime_effect` entry of §4.5.2 multiplied by the
scale factor), and entropy (a negative constant). The new health is clipped
to [0, 1].

#### Equations

Equation (4.29) — Per-cycle institution health update:

  health_{t+1} = clip( health_t + funding_delta + regime_effect_delta + entropy , 0, 1 )

with `funding_delta = funding_level · FUNDING_EFFECT_RATE`,
`regime_effect_delta = regime_effect · INSTITUTION_EFFECT_SCALE`, and
`entropy = ENTROPY_PER_TICK`.

#### Parameters

| Parameter | Symbol | Value | Source/Status |
|---|---|---|---|
| Institution effect scale | — | 20.0 | tunable design (`institutions.py:INSTITUTION_EFFECT_SCALE`); calibrated so that a strong regime modulation reaches near-peak in ~33 cycles (~2-3 years at the standard tick mapping) |
| Funding effect rate per cycle | — | 0.04 | tunable design (`institutions.py:FUNDING_EFFECT_RATE`) |
| Entropy per tick (linear decay) | — | -0.005 | tunable design (`institutions.py:ENTROPY_PER_TICK`); linear decay reaching 50% after 100 ticks of zero investment — NOT exponential half-life |

#### Algorithm

`update_institutions(world, tick)` at `institutions.py` iterates all
institutions of the world and applies equation (4.29). After Round 2 audit
finding N-12, the per-row `save()` was replaced with `bulk_update()` on the
collected health values, reducing per-cycle DB round-trips proportionally
to institution count.

#### Simplifications

1. **I-1 — Timescale calibration is design-driven**: the
   `INSTITUTION_EFFECT_SCALE = 20.0` is set so that strong regime modulation
   reaches near-peak in roughly 33 cycles (~2-3 years at the standard
   tick-to-year mapping). The mapping itself is tunable; the chosen scale
   is a heuristic rather than an empirical fit.

2. **I-2 — Funding rate is tunable**: `FUNDING_EFFECT_RATE = 0.04` is a
   design choice tracking neither a specific public-finance dataset nor a
   per-domain ROI study; it is exposed for per-era calibration.

3. **I-3 — Decay is linear, not exponential**: the entropy term applies a
   constant `-0.005` per cycle, producing a linear decay that reaches 50%
   after 100 ticks of zero investment. The pre-Round 2 docstring used
   "half-life" language; the current docstring corrects to "linear decay
   reaching 50% after 100 ticks of zero investment" (Round 2 audit
   finding I-3 closure).

### 4.5.4 Stratification

> Status: implemented as of commit `dfeb709218727c1efbca8cbee5e0dc6e974923fe`, code audit CONVERGED 2026-05-16 round 2.

#### Background

`stratification.py` computes per-world Gini, assigns agents to social
classes from the wealth distribution, and runs the per-cycle corruption
skim that diverts wealth from the world common pool to the head of state.
The Gini coefficient follows Gini (1912); the class-structure simplification
to five classes is a coarsening of the six-class scheme of Gilbert (2011);
the corruption framing draws on Acemoglu and Robinson (2006); the
personality-modulated asymmetric mobility weights are anchored on the
loss-aversion ratio of Kahneman and Tversky (1979).

#### Model

Gini is computed from the agent wealth vector; class assignment uses fixed
wealth-quintile thresholds; the corruption skim is wealth-conserving — the
amount removed from `world.global_wealth` is exactly the amount credited to
`agent.wealth` of the corrupt head of state. The mobility logic applies an
asymmetric weight ratio between upward and downward transitions, reflecting
the loss-aversion principle that downward moves are perceived more strongly
than equivalent upward moves.

#### Equations

Equation (4.30) — Gini coefficient (Gini 1912):

  Gini = (1 / (n · μ)) · Σᵢ (2i − n − 1) · xᵢ

with the agent wealth values `xᵢ` sorted ascending, `n` the agent count,
and `μ` the mean wealth.

Equation (4.31) — Class assignment from wealth quintiles:

  class(agent) =
    UPPER          if w(agent) ≥ q80
    UPPER_MIDDLE   if q50 ≤ w(agent) < q80
    MIDDLE         if q15 ≤ w(agent) < q50
    WORKING        if q5 ≤ w(agent) < q15
    LOWER          if w(agent) < q5

with the percentile cutpoints `q5, q15, q50, q80` computed from the agent
wealth distribution.

Equation (4.32) — Wealth-conserving corruption skim:

  skim_amount  = corruption_susceptibility · _CORRUPTION_SKIM_RATE · world.global_wealth
  world.global_wealth ← world.global_wealth − skim_amount
  head_of_state.wealth ← head_of_state.wealth + skim_amount

The skim is wrapped in `@transaction.atomic` so that the two updates either
both apply or neither does; this is Round 2 audit finding N-3 closure
(pre-Round 2 the two writes were unprotected and could produce free wealth
under concurrent execution).

#### Parameters

| Parameter | Symbol | Value | Source/Status |
|---|---|---|---|
| Class thresholds (quintiles) | — | 5 / 15 / 50 / 80 | Gilbert (2011) inspires the class scheme; the specific percentile cutpoints are tunable design choices |
| Corruption skim rate | — | 0.02 | tunable design (`stratification.py:_CORRUPTION_SKIM_RATE`); qualitative reference to Transparency International CPI for the relative ordering across regime types |
| Conscientiousness threshold for corruption susceptibility | — | 0.4 | tunable design; Miller and Lynam (2001) inspire the link between low conscientiousness and norm-deviance, but the cutoff itself is a design choice |
| Loss-aversion ratio (downward : upward mobility weight) | — | 1.75 : 1 | tunable design approximating the ~2 : 1 ratio of Kahneman and Tversky (1979) |

#### Algorithm

`compute_gini(world)` evaluates equation (4.30) on the per-agent wealth
vector. `update_social_classes(world)` evaluates equation (4.31) and writes
the assigned class back to each agent. `process_corruption(world, tick)`
implements equation (4.32) under `@transaction.atomic` so that the
`world.global_wealth` decrement and the `agent.wealth` increment are atomic
with respect to concurrent tick execution; this closes Round 2 audit
finding N-3.

#### Simplifications

1. **S-1 — Five classes vs the six-class Gilbert (2011) scheme**: Epocha
   coarsens the Gilbert (2011) six-class scheme to five classes by merging
   the "capitalist" and "upper" classes into a single UPPER class. The
   simplification is documented inline; the class threshold percentiles
   are exposed for per-era recalibration.

2. **S-2 — Wealth conservation enforced**: the corruption skim is
   wealth-conserving by construction (equation (4.32)); the
   `@transaction.atomic` wrapping prevents free-wealth artefacts under
   concurrent execution. Round 2 audit finding N-3 closure.

3. **S-3 — Conscientiousness threshold is a tunable design choice**:
   the `conscientiousness < 0.4` threshold is inspired by the Miller and
   Lynam (2001) link between low conscientiousness and norm-deviance, but
   the cutoff itself is not derived from that paper. The pre-Round 2
   citation to Acemoglu and Robinson (2006) was removed (Acemoglu and
   Robinson discuss institutional constraints, not personality cutoffs).

4. **S-4 — Emotional/mobility weights are tunable**: the upward/downward
   mobility magnitudes (0.4 and 0.7) preserve the ~2:1 loss-aversion ratio
   of Kahneman and Tversky (1979) but the specific magnitudes themselves
   are design choices; the principled anchor is the ratio, not the
   absolute values.

### 4.5.5 Election

> Status: implemented as of commit `dfeb709218727c1efbca8cbee5e0dc6e974923fe`, code audit CONVERGED 2026-05-16 round 2.

#### Background

`election.py` implements the per-election vote model used by the political
cycle to elect a new head of state when an election trigger fires. The
vote-score is a weighted convex combination of five components — relationship,
personality, economy, reputation, charisma — anchored to the political-
psychology literature: Caprara et al. (2006) for the personality basis,
Huckfeldt and Sprague (1987) for the network-relationship component,
Lewis-Beck and Stegmaier (2000) for the economic-voting component,
Lodge, Steenbergen and Brau (1995) for the candidate-evaluation
operationalisation, and Bass (1985), Weber (1922) and Merolla and
Zechmeister (2011) for the charisma component.

#### Model

For each voter and candidate, the score is computed as a weighted sum of
the five components; the candidate with the highest score wins the voter's
ballot. The manipulation bonus is then applied to the cumulative tally per
candidate (the bonus is a tunable per-candidate corruption-or-clientelism
modifier).

#### Equations

Equation (4.33) — Per-voter vote score:

  vote_score = w_rel·relationship + w_pers·personality + w_econ·economic + w_rep·reputation + w_char·charisma

with weights `(w_rel, w_pers, w_econ, w_rep, w_char) = (0.25, 0.15, 0.20, 0.25, 0.15)`.

Equation (4.34) — Reputation factor normalisation:

  reputation_factor = _normalize_reputation(reputation_raw)

where `_normalize_reputation()` is the centralised helper imported from
`agents/reputation.py` (Round 2 audit finding N-5 closure — pre-Round 2 the
election module carried a local normalisation that diverged from the
`reputation.py` single source of truth used by the belief filter of §4.4.3).

#### Parameters

| Parameter | Symbol | Value | Source/Status |
|---|---|---|---|
| Relationship weight | w_rel | 0.25 | tunable design (`election.py`); Huckfeldt and Sprague (1987) for the conceptual basis |
| Personality weight | w_pers | 0.15 | tunable design; Caprara et al. (2006) for the personality basis |
| Economic weight | w_econ | 0.20 | tunable design; Lewis-Beck and Stegmaier (2000) for the economic-voting basis |
| Reputation weight | w_rep | 0.25 | tunable design; reputation factor normalised via the centralised helper of `reputation.py` |
| Charisma weight | w_char | 0.15 | tunable design; Bass (1985), Weber (1922), Merolla and Zechmeister (2011) for the charisma basis |
| Wealth saturation constant | — | 100.0 | tunable design (`election.py:_WEALTH_SATURATION`); tied to the `Agent.wealth` default of 50.0 so that the saturating function reaches half-max at the population baseline |

#### Algorithm

The voter list is materialised once into `voter_list = list(...)` and the
voter count is captured via `voter_count = len(voter_list)` for the
manipulation-bonus loop (Round 2 audit findings N-5 and E-5 closure —
pre-Round 2 the loop re-evaluated `voters.count()` or `len(list(voters))`
on each iteration). The manipulation bonus is applied to each candidate's
cumulative tally; the highest-tally candidate wins the election and is
written back as the new head of state.

#### Simplifications

1. **E-3 — Vote weights are tunable design choices**: the five-tuple
   `(0.25, 0.15, 0.20, 0.25, 0.15)` is the current default and is exposed
   for per-era calibration; the cited literature supports the
   *presence* of each component rather than the *magnitude* of its weight.

2. **E-4 — Wealth saturation is tied to the internal wealth scale**:
   `_WEALTH_SATURATION = 100.0` is tied to the `Agent.wealth` default of
   50.0 so that the saturating function reaches half-max at the population
   baseline; the absolute value is meaningful only within Epocha's
   internal wealth scale.

3. **E-5 — Query evaluation is cached**: the voter QuerySet is materialised
   once and its length captured into a local before the manipulation-bonus
   loop; per-iteration re-evaluation is removed. Round 2 audit finding E-5
   closure.

## 4.6 Movement

> Status: implemented as of commit `c543c102a4af9f44c35fd25988c471e0f97632cd`, code audit CONVERGED 2026-05-16 round 2.

### Background

The movement module governs per-tick relocation of agents between zones under three intent classes: voluntary economic migration (`move_to_zone` action), voluntary social migration (relationship pull toward partner/parent/faction leader), and involuntary movement (zone destruction/expulsion). Travel speeds are calibrated against Chandler (1966) *The Campaigns of Napoleon* for military rates (infantry sustained 20-35 km/day; cavalry 60 km/day; carriage with relay 60-80 km/day) and Braudel (1979) *Civilization and Capitalism* for civilian pre-industrial rates (merchants on foot ~25 km/day; river/canal boats ~50 km/day). The implementation uses the civilian midpoint where possible: foot=25 (Braudel), horse=60 (Chandler military cavalry — borderline used as a default), carriage=60 (Chandler low-end no-relay), boat=50 (Braudel).

### Model

Travel distance per tick is a multiplicative function of: transport mode base speed, agent health (health factor with floor 0.1), road quality (per-terrain multiplier), political repression (1 - regime.repression_tendency for non-democratic regimes), and world stability (1 + (stability - 0.5)·0.2). The result is the maximum km the agent can cover in this tick; the actual movement is bounded by the straight-line grid-unit distance to target multiplied by `World.distance_scale` to convert grid units to km. Partial movement interpolates linearly toward the target in grid units; full movement places the agent at target zone centroid plus arrival-scatter offset.

### Equations

Equation (4.35) maximum distance per tick:

  max_distance_km = TRAVEL_SPEEDS[mode] · health_factor · terrain_factor · repression_factor · stability_factor · tick_duration_days

where `health_factor = max(0.1, health)`, `repression_factor = 1 - regime.repression_tendency` (clamped non-negative), `stability_factor = 1 + (world.stability - 0.5) · 0.2`.

Equation (4.36) partial-movement vector:

  new_location = current_location + (target_location - current_location) · (max_distance_km / required_km)

where `required_km = euclidean_distance(current, target) · World.distance_scale / 1000`.

Equation (4.37) arrival scatter (full-movement arm):

  arrival_location = target_centroid + uniform(-ARRIVAL_SCATTER_RANGE, +ARRIVAL_SCATTER_RANGE)·2

with `_ARRIVAL_SCATTER_RANGE = 40.0` grid units (assumes 100-unit zone boundary).

### Parameters

| Parameter | Value | Source | Status |
|---|---|---|---|
| foot speed | 25 km/day | Braudel 1979 (civilian merchant) | verified |
| horse speed | 60 km/day | Chandler 1966 (military cavalry, used as default) | tunable |
| carriage speed | 60 km/day | Chandler 1966 (no-relay civilian floor) | tunable |
| boat speed | 50 km/day | Braudel 1979 (river/canal) | verified |
| ROLE_TRANSPORT defaults | per-role dict | simulation scenario language | tunable |
| terrain factors {urban, commercial, industrial, rural, wilderness} | {1.0, 1.0, 0.9, 0.7, 0.5} | qualitative ordering Braudel 1979 (road quality); magnitudes tunable | tunable |
| _MOOD_COST_PER_MOVEMENT | small constant | tunable design parameter | tunable |
| _HEALTH_COST_EXHAUSTING_TRAVEL | small constant | tunable design parameter | tunable |
| _EXHAUSTION_THRESHOLD | 0.5 | tunable design parameter | tunable |
| _ARRIVAL_SCATTER_RANGE | 40.0 grid units | assumes 100-unit zone boundary | tunable |

### Algorithm

1. `calculate_max_distance(agent, world)` returns the per-tick movement budget in km.
2. `execute_movement(agent, target_zone, world)` either: (a) completes the trip if max_distance ≥ required_km, placing the agent at target_centroid + arrival_scatter, applying full mood/health cost; or (b) partial-moves the agent along the line toward target by max_distance/required_km, applying partial mood cost.
3. Mood and health updates clamp to [0, 1].
4. Logger records movement events for observability.

### Simplifications

- **Coordinate convention (N-1)**: agent/zone coordinates are abstract grid units despite PostGIS fields declaring SRID 4326. `World.distance_scale` (default 133 m/grid-unit) converts to real-world km. Documented in `movement.py` module docstring. Behavioral fix (projected coordinates) is scope-positive deferred.
- **Inter-zone graph (R1 acknowledged)**: routing uses the abstract zone graph of `world/models.py` not actual zone geometry. PostGIS geometry available but routing layer deferred to broader-PostGIS roadmap.
- **RNG reproducibility (N-8)**: `random.uniform` uses Python's global RNG, not the simulation-seeded `get_seeded_rng`. Two runs with identical seed produce different arrival-scatter offsets. Future work: thread simulation RNG into movement.
- **Arrival scatter zone-size assumption (M-5)**: `_ARRIVAL_SCATTER_RANGE = 40.0` assumes 100-unit zone boundary not enforced. Future work: relative to actual zone bounding box.
- **Bare except in caller (N-3)**: `simulation/engine.py:168` wraps `execute_movement` in `try/except Exception`. Cross-module concern; tracked for future simulation cluster audit.

### Status

> Status: implemented as of commit `c543c102a4af9f44c35fd25988c471e0f97632cd`, code audit CONVERGED 2026-05-16 round 2.

---

## 4.7 Factions

> Status: implemented as of commit `5406b95a74d3281bc98665923818d7e708745120`, code audit CONVERGED 2026-05-16 round 2.

### Background

The factions module governs the intra-faction dynamics of agent groups across their life cycle: per-tick cohesion update, leadership emergence scoring, leadership legitimacy and succession, dissolution below a viability floor, schism of a hostile sub-clique into a splinter group, and bottom-up formation of new factions from unaffiliated agents. The conceptual frame is Olson (1965), *The Logic of Collective Action*, for the collective-action viability threshold below which a group disintegrates, and Festinger et al. (1950), *Social Pressures in Informal Groups*, for the treatment of cohesion as a quantity maintained by cooperative interaction and eroded by internal conflict. Leadership emergence is grounded in the trait-leadership meta-analysis of Judge et al. (2002); the negativity-bias direction of the cohesion asymmetry follows Baumeister et al. (2001). The Iannaccone (1992) club-goods mechanism (cohesion through costly-signal sacrifice, exclusionary boundary markers, free-rider detection) is explicitly NOT implemented and is recorded as a deferred extension.

### Model

Group cohesion evolves each interval by a delta that rewards cooperative member actions, penalises conflictual ones with a stronger weight (negativity bias), subtracts a coordination-cost penalty that grows with membership above a small-group threshold, and adds a leader-effectiveness term keyed to the leader's legitimacy. Leadership emergence is a five-component weighted sum of an agent's charisma, intelligence, relative wealth rank, average in-group sentiment, and seniority. Leadership legitimacy is a three-component weighted sum of group cohesion, the leader's average sentiment from members, and the leader's leadership-score rank; legitimacy below a threshold triggers succession. Schism partitions a group when a sub-clique's average sentiment toward the rest falls below a hostility threshold, seeding a splinter group at reduced initial cohesion. All scalar weights, thresholds, and coefficients are tunable design parameters, sourced to the qualitative direction of the cited literature but not derived from it.

### Equations

Equation (4.38) cohesion delta per interval:

  cohesion_delta = cooperation_ratio · 0.10 − conflict_ratio · 0.15 − size_penalty · 0.02 + leader_effectiveness · 0.05

where `cooperation_ratio` and `conflict_ratio` are the fractions of cooperative (help, socialize) and conflictual (argue, betray) member actions over the interval, `size_penalty = max(0, member_count − 5)`, and `leader_effectiveness = legitimacy − 0.5`.

Equation (4.39) leadership emergence score:

  leadership_score = charisma · 0.30 + intelligence · 0.20 + wealth_rank · 0.15 + internal_sentiment · 0.20 + seniority · 0.15

where `internal_sentiment` is the agent's average relationship sentiment with other members mapped from [−1, 1] to [0, 1], `wealth_rank` is the agent's relative economic standing within the group, and `seniority = min((tick − join_tick) / group_age, 1.0)`.

Equation (4.40) leadership legitimacy:

  legitimacy = group_cohesion · 0.40 + leader_sentiment · 0.40 + score_rank · 0.20

where `leader_sentiment` is the leader's average sentiment from members mapped to [0, 1] and `score_rank ∈ [0, 1]` ranks the leader's leadership_score against all members.

Equation (4.41) schism trigger: a candidate sub-clique (built greedily from a seed agent, adding members whose mutual sentiment exceeds `_ALLY_SENTIMENT_THRESHOLD = 0.2`) splits off when its average sentiment toward the non-clique remainder falls below `_SCHISM_OUTWARD_SENTIMENT_THRESHOLD = −0.2`.

### Parameters

| Parameter | Value | Source | Status |
|---|---|---|---|
| cooperation coefficient | 0.10 | calibration budget; Baumeister 2001 grounds asymmetry direction only | tunable |
| conflict coefficient | 0.15 | calibration budget; 1.5:1 vs cooperation is negativity-bias direction (Baumeister 2001), not the ratio | tunable |
| size-penalty coefficient | 0.02 | calibration budget | tunable |
| leader-effectiveness coefficient | 0.05 | calibration budget | tunable |
| size-penalty threshold | 5 | tunable; Hackman 2002 generic small-group principle; NOT Dunbar 1992 (~150) nor Zhou et al. 2005 (intimate-clique stratum) | tunable |
| leadership weights {charisma, intelligence, wealth_rank, internal_sentiment, seniority} | {0.30, 0.20, 0.15, 0.20, 0.15} | tunable; consistent with Judge 2002 effect-size direction, not derived; charisma per Weber 1922 + Antonakis et al. 2016 | tunable |
| legitimacy weights {cohesion, leader_sentiment, score_rank} | {0.40, 0.40, 0.20} | calibration budget | tunable |
| ally sentiment threshold | +0.2 | calibration budget (symmetric) | tunable |
| schism outward sentiment threshold | −0.2 | calibration budget (symmetric) | tunable |
| no-relationship sentiment fallback | 0.3 (normalized = raw −0.4) | conservative tunable default | tunable |
| splinter seed cohesion | 0.5 | tunable; below new-faction 0.6 (carries parent conflict) | tunable |
| new-faction seed cohesion | 0.6 | tunable | tunable |
| dissolution / legitimacy / affinity thresholds | 0.2 / 0.3 / 0.5 | settings defaults, calibration budget | tunable |
| Memory.emotional_weight grading | 0.2 / 0.3 / 0.4 | minor / moderate / significant, tunable | tunable |

### Algorithm

1. `process_faction_dynamics(simulation, tick)` runs every `EPOCHA_FACTION_DYNAMICS_INTERVAL` ticks and orchestrates the pipeline.
2. For each active group: `update_group_cohesion` applies equation (4.38); `update_group_leadership` recomputes `compute_leadership_score` (4.39) and `compute_legitimacy` (4.40), replacing the leader on a legitimacy shortfall; `_check_dissolution` releases members when cohesion or membership falls below the viability floor; `_check_schism` applies equation (4.41) and spawns a splinter.
3. `_detect_and_propose_factions` greedily clusters unaffiliated agents by pairwise affinity and proposes new factions; `_check_join_existing_groups` suggests joins; `_process_formation_decisions` realises agent formation intents.
4. `_generate_faction_identity` requests an LLM name/objective with a deterministic fallback that never blocks faction creation.

### Simplifications

- **Leadership weights as design choices (F-1)**: the (0.30/0.20/0.15/0.20/0.15) tuple is consistent with the direction of Judge et al. (2002) effect sizes (Extraversion strongest, then Conscientiousness, Openness, inverse Neuroticism) but is not derived from the meta-analytic correlations; Stogdill (1948) supports the trait-correlate principle but proposed no weighted-sum formula; charisma is Weberian (Weber 1922, Antonakis et al. 2016), not a Stogdill trait.
- **Size-penalty threshold as design choice (F-2)**: the value 5 is a tunable parameter anchored to the generic small-group coordination-cost principle (Hackman 2002), explicitly NOT to Dunbar 1992 (cognitive limit ~150) nor to the intimate-clique "5" stratum of Zhou et al. (2005).
- **Cohesion coefficients as calibration budget (F-3)**: the four coefficients and the 1.5:1 conflict-to-cooperation ratio are tunable; Baumeister et al. (2001) grounds only the qualitative negativity-bias direction, not the magnitudes.
- **Order-dependent greedy clustering (F-4)**: schism and cluster detection seed from the first agent in the queryset, making the partition order-dependent; a graph-based connected-components / hierarchical-clustering resolution is deferred to a future "robust faction clustering" work item.
- **Club-goods not implemented**: the Iannaccone (1992) costly-signal cohesion mechanism is absent and deferred.
- **Faction-to-faction relations not modeled**: inter-faction alliance/rivalry dynamics are out of scope for the current module.
- **LLM identity generation**: name/objective generation via the LLM adapter is covered by the separate llm-adapter audit; faction creation is never blocked by LLM unavailability.
- **Behavioral hardening resolved (Round 3, 2026-07-15)**: the four findings deferred at the Round 2 audit are closed by the factions Round 3 hardening work item — the member-sampling bias (an unordered queryset slice, implementation-defined on PostgreSQL; the original "primary-key ordering" characterization was imprecise) is replaced by averaging affinity over all living members with a prefetched context, the multi-row writes of all four mutation paths are wrapped in per-mutation `transaction.atomic` blocks, the agent-migration write discipline is unified on queryset `update()` under a verified no-signals precondition, and the N+1 query patterns in the join-suggestion, cluster-detection, leadership and founder-election paths are removed with pinned query-budget regression tests. The relationship-strength tie-break is now deterministic (id secondary key). The founder election previously scored candidates against the still-empty new group (degenerate: the first founder always won) and now scores the actual founding membership.

### Status

> Status: implemented as of commit `5406b95a74d3281bc98665923818d7e708745120`, code audit CONVERGED 2026-05-16 round 2.

---

## 4.8 Economy base layer

> Status: implemented as of commit `1cdcfa4fe23138727c16a2e92234e4eb962d9ae7`, code audit CONVERGED 2026-07-16 round 12.

### Background

The economy base layer is the substrate that turns agent activity into production, prices, money, and per-tick income flows; the behavioral integration of §4.2 (adaptive expectations, credit and banking, property market) consumes the prices, trades, and factor incomes this layer produces. Five modules make up the substrate. Production follows the Constant Elasticity of Substitution family of Arrow, Chenery, Minhas and Solow (1961), with the multi-factor extension of applied computable-general-equilibrium practice (Shoven and Whalley 1992). Market clearing is Walrasian tâtonnement (Walras 1874) under the explicit non-convergence caveat of Scarf (1960) for three or more goods. Income distribution implements the classical tripartite factor-income identity of Ricardo (1817) — the produce of a period is partitioned among land (rent), labour (wages), and capital (profit), never paid in full to each factor independently — restated in modern terms by the income approach to national accounts. The monetary module carries Fisher's (1911) equation of exchange as a conservation diagnostic, not as a price rule, and the mood coupling follows the income-satiation plateau of Kahneman and Deaton (2010). Initialization seeds the per-era balance sheet from the economy templates of §6.2. The layer went through twelve adversarial audit rounds (first audit 2026-07-15, convergence 2026-07-16) that rewrote the conservation core: the pre-audit implementation injected more than twice the produced value per tick as new cash, fabricated goods at settlement, and left the money aggregate disconnected from circulating cash.

### Model

Each tick, every zone runs a nine-step cycle: expectations update (§4.2.1), CES production per agent, tâtonnement clearing of the zone market, the credit step (§4.2.2), the conserved factor-income partition (rent, wages, profit), flat income taxation into the treasury, essential consumption, the money-supply/wealth/mood pass, and deposit recalculation. Production converts each agent's role-specific factor inputs into a good quantity through the CES aggregator with per-good template parameters (scale `A`, elasticity of substitution `σ`, normalized factor weights `αᵢ`). The zone market collects supply (holdings above the subsistence reserve) and demand (subsistence gaps, plus a cash-budgeted discretionary demand for non-essential goods), adjusts prices proportionally to relative excess demand, and settles trades under short-side proportional rationing with an affordability guard, essential goods first, in a deterministic order. The zone output value `V` — production valued at the zone's own equilibrium prices — is then partitioned into factor incomes that sum to exactly `V` and credited as the tick's only money injection; taxation and all sales are pure transfers. The money aggregate `M` is recomputed every tick as the circulating cash of living agents, and the Fisher identity is evaluated as a diagnostic comparing the injected factor income against the nominal output value.

### Equations

Equation (4.42) CES production function (Arrow et al. 1961), per agent and good, with `ρ = (σ − 1)/σ`:

  Q = A · [Σᵢ αᵢ · Xᵢ^ρ]^(1/ρ)

evaluated in log-form near the Cobb-Douglas singularity (`0.95 < σ < 1.05`, `Q = A · Πᵢ Xᵢ^αᵢ`) and by its Leontief limit below `σ = 0.05` (`Q = A · min(Xᵢ)`: the normalized distribution weights vanish in the power-mean limit, so the limit is the minimum of the inputs, not `min(αᵢXᵢ)`); the small positive numerical seam at the branch threshold is bounded below 1% relative and pinned by a regression test.

Equation (4.43) tâtonnement price update (Walras 1874; Shoven and Whalley 1992), iterated to convergence or an iteration cap:

  P⁽ᵏ⁺¹⁾_g = P⁽ᵏ⁾_g · (1 + λ · (D_g − S_g) / max(S_g, ε))

with adjustment rate `λ = 0.03`, per-iteration change capped at ±50%, an absolute floor of `0.01`, and a ceiling of `100 ×` the template base price anchoring cross-tick drift; the iteration cap (100) is the explicit safety net for the Scarf (1960) non-convergence regime.

Equation (4.44) conserved factor-income partition (Ricardo 1817; income approach to national accounts), per zone and tick:

  V_z = Σ_g q_zg · p_zg    and    V_z = R_z + W_z + Π_z

with rent share `0.15` (allocated to property owners proportionally to their production bonus), wage share `0.6` (allocated to producers proportionally to their own output value), and profit the residual `0.25` (to the capital-supplying owners, or retained by producers for goods with no property claim, absorbing the unclaimed rent share so the partition sums to `V_z` good by good). Dead owners are excluded and their share renormalizes to surviving claimants or falls through to producers.

Equation (4.45) Fisher conservation diagnostic (Fisher 1911), evaluated each tick and logging above 20% divergence:

  MV = Σ (factor income credited)    vs    PQ = Σ_z V_z ,    divergence = |MV − PQ| / max(MV, PQ, 1)

where the velocity passed to the check is the income velocity (factor income / M), so the identity is non-tautological: divergence signals income injected out of proportion to produced value — the conservation-defect class the audit found and fixed — while the measured turnover velocity remains a reported metric on the currency.

### Parameters

| Parameter | Value | Source | Status |
|---|---|---|---|
| CES default elasticity `σ` | 0.5 | template default; Arrow et al. 1961 form | tunable |
| CES default scale `A` | 2.0 | template calibration (5.0 documented as unphysical for 4-agent markets) | tunable |
| CES factor baselines (capital, natural resources, knowledge) | 0.5 | design parameter | tunable |
| Leontief / Cobb-Douglas branch thresholds | 0.05 / 0.95–1.05 | numerical-stability guards | tunable |
| tâtonnement rate / iterations / convergence | 0.03 / 100 / 0.01 | applied CGE practice (Shoven and Whalley 1992) | tunable |
| per-iteration change cap / price floor / price ceiling | ±50% / 0.01 / 100× base price | stability guards | tunable |
| wage / rent / profit shares | 0.6 / 0.15 / 0.25 (residual) | Ricardo 1817 partition identity; values calibration budget | tunable |
| discretionary spend fraction / per-good cap | 0.1 of cash / 5 units | demand heuristic (Deaton and Muellbauer 1980 is the full model it approximates) | tunable |
| subsistence need per agent per tick | 1.0 | shared demography contract (§4.1) | tunable |
| wage sanity cap | 100 × median wage (floor 100) | defense-in-depth guard; when binding, injection < V by design | tunable |
| mood thresholds | 0.5 × / 1.5 × median wealth | OECD relative-poverty convention; Kahneman and Deaton (2010) plateau | tunable |
| Fisher warning threshold | 20% divergence | diagnostic sensitivity | heuristic |
| inflation index | unweighted arithmetic mean (Carli form) | disclosed simplification vs weighted/Jevons (CPI Manual 2004) | heuristic |

### Algorithm

1. `process_economy_tick_new(simulation, tick)` (`epocha/apps/economy/engine.py`) orchestrates the nine steps; every iteration order feeding order-sensitive state is pinned (id-ordered querysets, sorted goods, stable essential-first trade sort, RNG derived from the simulation seed and tick), so the economic step is deterministic given its inputs. Those inputs include agent decisions and the LLM-derived wealth and zone assignments they produce, which are not seed-reproducible (§3.4); two identically-seeded runs therefore do not reproduce bit-identical state — only bit-identical economic arithmetic over whatever inputs each run's LLM decisions generated.
2. Per zone: `compute_agent_output` (equation 4.42) adds production to inventories and the ledger; `collect_supply_and_demand` + `tatonnement_prices` (4.43) clear the market; `execute_trades` rations the short side proportionally with running totals and the engine settles essential goods first under a buyer-cash affordability guard.
3. `partition_output_value` (4.44) computes rent, wages, and profit summing to `V_z`; the engine credits payees resolved simulation-wide (living out-of-zone owners included, dead owners excluded) and ledgers each factor income; taxation debits earners and credits the treasury with the running total actually collected, only when a Government exists.
4. Step 8 recomputes `M` from living agents' circulating cash, evaluates the Fisher diagnostic (4.45), updates wealth and the median-relative mood thresholds, and the banking layer recalculates deposits (§4.2.2).

### Simplifications

- **Carli inflation index**: inflation is the unweighted arithmetic mean of price relatives, with the documented upward bias versus expenditure-weighted or geometric (Jevons) forms (CPI Manual 2004); the simulation carries no expenditure-share data to weight with, so the form is disclosed rather than replaced.
- **Unweighted cross-zone price aggregation**: system prices for inflation, wealth valuation, and expectations are unweighted means across zones quoting a good; an activity-weighted mean is the refinement. The Fisher PQ side deliberately does NOT use this aggregate — it sums per-zone nominal values, so the diagnostic is exact under multi-zone price dispersion.
- **Proportional-to-bonus rent**: rent is proportional to a property's production bonus rather than a differential surplus over marginal land (Ricardo 1817's full construction); qualitative behavior (productive land earns more rent) is preserved.
- **Public and ownerless land income accrues to producers**: property not owned by a living agent is excluded from the partition and its land/capital share reaches the producing agents through the no-landlord fallback; routing it to the treasury would be a deliberate fiscal-policy change.
- **Injection ≤ V under the wage cap**: the defense-in-depth wage sanity cap can clip the credited total strictly below `V`; the clipped remainder is deliberately not redistributed (never binding in the calibrated templates).
- **Mood step functions**: the poverty penalty is flat (not scaled by depth) and the per-tick boost doubles exactly at the satiation threshold before decaying — a disclosed piecewise simplification of the Kahneman-Deaton plateau.
- **Demand heuristic**: discretionary demand allocates a fixed cash fraction across non-essential goods by inverse-elasticity weights — a budget-constrained heuristic approximating a proper demand system (Deaton and Muellbauer 1980); agents do not demand goods they are themselves offering (wash-trade exclusion).
- **Single-currency market**: demand sizing and settlement operate on the primary currency only; multi-currency trading is not modeled.
- **M scope**: measured money covers living agents' cash only — the government treasury, dead agents' cash, and banking-system interest sit outside circulation by design, and banking-type loan issuance/repayment is disclosed Diamond-Dybvig-style inside money (§4.2.2).

### Status

> Status: implemented as of commit `1cdcfa4fe23138727c16a2e92234e4eb962d9ae7`, code audit CONVERGED 2026-07-16 round 12. Live in the per-tick pipeline (dispatched by `epocha/apps/simulation/engine.py` for simulations with the economy data layer initialized).

---

# 5. Implementation

Chapter 5 documents how the abstract architecture of Chapter 3 and the audited models of Chapter 4 are laid down on disk. The intent is that a reader who has internalized the previous chapters can navigate the codebase without first reverse-engineering the directory tree, and that the mapping between each implemented module and its design spec is explicit rather than implicit. The chapter is deliberately compact: it points at the source of truth rather than re-narrating what the source already states.

## 5.1 Repository layout

The repository is organized into four top-level directories under the project root:

```
epocha/
├── config/                     Django project package (settings, ASGI, Celery, root URL)
│   ├── settings/               Split settings: base, local, production
│   ├── asgi.py                 ASGI entry point for HTTP and WebSocket
│   ├── celery.py               Celery app declaration and task autodiscovery
│   └── urls.py                 Root URL configuration mounting per-app routers
├── epocha/
│   ├── apps/                   Django apps, one per simulation subsystem
│   │   ├── agents/             Big Five personality, memory, decision pipeline,
│   │   │                       reputation, information flow, factions, movement,
│   │   │                       relationships, social graph
│   │   ├── chat/               WebSocket conversation layer with agents
│   │   ├── dashboard/          Operator UI, simulation overview, graph rendering
│   │   ├── demography/         Mortality, fertility, couple formation,
│   │   │                       inheritance, age structure
│   │   ├── economy/            Production, monetary, market clearing, credit,
│   │   │                       banking, expectations, property market,
│   │   │                       distribution, political feedback
│   │   ├── knowledge/          Knowledge graph and structured fact store
│   │   ├── llm_adapter/        Provider abstraction, key rotation, rate limiter,
│   │   │                       per-call accounting (`LLMRequest`)
│   │   ├── simulation/         Tick engine, Celery loop, simulation lifecycle,
│   │   │                       seed and RNG bookkeeping
│   │   ├── users/              Authentication and operator accounts (boilerplate)
│   │   └── world/              Geography, zones, government, institutions,
│   │                            stratification, document parsing, generators
│   └── common/                 Shared utilities: pagination, permissions,
│                                exceptions, mixins, generic helpers
├── compose/                    Dockerfiles and entrypoints for local and prod
├── requirements/               Pinned dependency sets: base, local, production
└── docs/                       Specs, plans, memory backup, whitepapers
```

The split between `config/` and `epocha/` follows the django-cookiecutter convention: `config/` carries the project-level wiring that is independent of the domain, while `epocha/` carries the domain itself. Apps under `epocha/apps/` are intentionally narrow: each one owns a closed set of concerns and exposes its public surface through `models.py`, `serializers.py`, `views.py`, `urls.py`, and a per-domain set of service modules whose names match the §4 model boundaries (`mortality.py`, `fertility.py`, `couple.py`, `expectations.py`, `credit.py`, `property_market.py`, and so on). Cross-app communication goes through model foreign keys and through the per-tick orchestrator in `simulation/`, never through ad-hoc imports between domain modules; this is the structural rule that keeps the dependency graph acyclic and that makes per-app testing tractable.

## 5.2 Module-to-spec mapping

Table 5.1 records the design spec or specs that govern each Django app under `epocha/apps/`. Specs are stored under `docs/superpowers/specs/` in date-prefixed kebab-case form; multiple specs against the same app reflect the staged design history of that subsystem (an initial design spec followed by behavioral or integration revisions). Apps tagged "n/a — boilerplate" carry no domain logic of their own beyond Django defaults and therefore have no companion design spec.

Table 5.1 — Mapping from `epocha/apps/<app>` to the governing design spec.

| App | Design spec(s) under `docs/superpowers/specs/` |
|---|---|
| `agents` | `2026-04-05-information-flow-design.md` (information flow), `2026-04-05-factions-leadership-design.md` (factions and leadership), `2026-04-06-reputation-model-design.md` (reputation), `2026-04-06-social-graph-design.md` (relationships and social graph), `2026-04-07-movement-system-design.md` (movement) |
| `chat` | `2026-03-30-integrated-dashboard-chat-design.md` |
| `dashboard` | `2026-03-30-integrated-dashboard-chat-design.md`, `2026-04-06-analytics-psicostoriografia-design.md` |
| `demography` | `2026-04-18-demography-design.md` |
| `economy` | `2026-04-12-economy-base-design.md`, `2026-04-13-economy-behavioral-design.md`, `2026-04-15-economy-behavioral-integration-design.md` |
| `knowledge` | `2026-04-11-knowledge-graph-design.md` |
| `llm_adapter` | `2026-03-22-epocha-design.md` (master spec, §3.5) |
| `simulation` | `2026-03-22-epocha-design.md` (master spec, §3.1, §3.4) |
| `users` | n/a — boilerplate |
| `world` | `2026-04-05-government-institutions-stratification-design.md` (government, institutions, stratification), `2026-04-06-postgis-geodjango-design.md` (geographic substrate) |

The master spec `2026-03-22-epocha-design.md` covers cross-cutting concerns (tick engine, RNG strategy, LLM adapter contract, persistence conventions) that are not owned by any single domain app and are referenced by every other spec. The Italian companion `2026-04-18-demography-design-it.md` shadows the demography design as the human-readable artifact used during the spec-approval gate; per the bilingual policy of the master CLAUDE.md it is the authoritative single version for that subsystem.

## 5.3 LLM provider adapter and rate limiting

The implementation pointer for the adapter described in §3.5 is `epocha/apps/llm_adapter/providers/`, with `base.py` defining the abstract `BaseLLMProvider` interface and `openai.py` providing the concrete OpenAI-compatible implementation that targets every supported endpoint (OpenAI proper, Groq, Google Gemini, OpenRouter, Together AI, Mistral, LM Studio, Ollama). Switching providers is a settings change rather than a code change: `EPOCHA_LLM_BASE_URL`, `EPOCHA_LLM_MODEL`, and `EPOCHA_LLM_API_KEY` in `config/settings/base.py` select the endpoint, and the same triple has a `EPOCHA_CHAT_LLM_*` parallel for the chat-side provider that `get_chat_llm_client()` wraps in a `FallbackProvider`. Local LM Studio runs are configured exactly like remote endpoints: the `base_url` points at `http://localhost:1234/v1` (the default LM Studio server URL), `EPOCHA_LLM_API_KEY` is left unset or set to a placeholder, and the model identifier matches the model loaded in the LM Studio UI. The Groq key-rotation pattern that backstops the free tier is implemented inside `OpenAIProvider`: `EPOCHA_LLM_API_KEY` accepts a comma-separated list of keys, and on `RateLimitError` the provider rotates to the next key after exhausting the in-call retry budget. The process-level Redis-backed sliding-window limiter in `epocha/apps/llm_adapter/rate_limiter.py` is the second line of defense and is invoked by orchestration code that needs to throttle ahead of the provider's own limit. Per-call accounting writes to the `LLMRequest` model so that token usage and USD cost are observable per simulation in the dashboard.

## 5.4 Persistence model details

PostgreSQL is the canonical store, with PostGIS already enabled at the Django level: `django.contrib.gis` is in `INSTALLED_APPS` (`config/settings/base.py:33`) and the `world` app stores zone geometries as WGS84 `PolygonField`/`PointField` from migration `world.0003_zone_postgis_geometry` onward. The default primary key is the Django 64-bit auto-increment integer (`DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"`); no UUID columns are used as of the pinned commit, and foreign keys throughout the apps therefore carry integer references. Atomic per-request transactions are enabled (`ATOMIC_REQUESTS = True`) so that API and tick handlers run inside a transaction by default.

Migration discipline follows the project rule that no migration is applied to `develop` without the corresponding model change being merged in the same commit; migrations under `epocha/apps/<app>/migrations/` are linear and never squashed across releases, on the grounds that the simulation itself is the source of truth and rolling back a migration must remain a git-level operation. Two persistence-model conventions, both formalized during the demography Plan 1 audit, deserve explicit mention because they cross multiple apps. First, every monetary balance is stored as a `JSONField` keyed by ISO-4217-style currency code rather than as a single `DecimalField`: `AgentInventory.cash` (`epocha/apps/economy/models.py:208`) and the analogous treasury fields on government and banking entities all carry per-currency dictionaries so that multi-currency balances and per-currency analytics are preserved without schema migrations when a new currency is introduced by a sci-fi or modern template. Second, the `Agent.birth_tick` column on `agents.Agent` is a `BigIntegerField` rather than a `PositiveIntegerField` (`epocha/apps/agents/models.py:88`); the signed type is required because pre-existing agents whose age predates the simulation start carry a negative birth tick, and the canonical age formula `age = (current_tick − birth_tick) / ticks_per_year` would otherwise lose validity at the founder-population boundary. The migration trail at `agents.0009_agent_birth_tick_*` and `agents.0010_alter_agent_birth_tick_*` records the introduction of the field and its subsequent retyping during the Plan 1 convergence loop.

---

# 6. Calibration

Chapter 6 documents the calibration surface of the audited modules and the era-template machinery that carries the per-epoch parameter values into the simulation. Where Chapter 4 narrates each model and presents its parameter table inline alongside the equations it parameterizes, Chapter 6 takes the complementary view: it consolidates the calibration pointers in a single place, describes the two distinct schema conventions used for demography and economy templates, and records which fits are implemented today and which are deferred to Plan 4.

## 6.1 Parameter tables per audited module

The per-module parameter tables are presented inline in Chapter 4 next to the equations they govern, on the principle that a parameter is most legible when it sits beside its model rather than in a back-of-book appendix. Table 6.1 below is therefore an index, not a duplicate.

Table 6.1 — Index of inline parameter tables by audited module.

| Audited module | Inline tables in Chapter 4 |
|---|---|
| Mortality (Heligman-Pollard) | Tables 4.1 (HP parameter semantics and admissible ranges) and 4.2 (per-era HP values across the five Plan 1 templates) |
| Fertility (Hadwiger ASFR + Becker modulation) | Tables 4.3 (per-era Hadwiger values) and 4.4 (Becker modulation coefficients, currently homogeneous across all five templates per debt B2-07) |
| Couple formation (Gale-Shapley + Goode 1963) | Tables 4.5 (per-era couple-formation parameters) and 4.6 (per-era homogamy weights for equation (4.6)) |
| Inheritance (polygenic kernel + social transmission + succession) | Tables 4.10 (per-trait heritability with primary sources) and 4.11 (per-era class rule, education-regression ρ, succession rule, estate-tax rate). Three module constants sit outside the templates and are documented inline in §4.1.4: `_BECKER_TOMES_RANK_NOISE_SD = 0.75`, `MOURNING_MEMORY_WEIGHT = 0.9`, `MOURNING_TIE_STRENGTH_THRESHOLD = 0.6`. The era-noise priors `DEFAULT_ERA_MEAN = 0.5` and `DEFAULT_ERA_SD = 0.15` are nominally placeholders but are in practice the parameters, since no template declares an `era_noise` section — see the Simplifications paragraph of §4.1.4. |
| Migration (Harris-Todaro context + Mincer household coordination + forced flight) | Table 4.12 (per-era `flight_trigger_ticks` and `adulthood_age`, plus the module constants for both trailing windows, the three memory weights, and the mass-flight threshold) |
| Adaptive expectations (Cagan 1956) | Table 4.7 (parameters seeded by `_behavioral_config()`, identical across all four economy templates pending Plan 4 calibration) |
| Credit and banking (Diamond-Dybvig + fractional reserve) | Tables 4.8 (per-era credit and banking parameters) and 4.9 (parameters uniform across all four templates pending Plan 4) |
| Economy base layer (CES production, tâtonnement, factor-income partition, Fisher diagnostic) | Inline parameter table in §4.8 (CES defaults and branch thresholds, tâtonnement rate/caps, wage/rent/profit shares, demand heuristic, wage sanity cap, mood thresholds, diagnostic thresholds) |
| Property market | No standalone table — parameters inherit from the credit configuration of §4.2.2 (loan-to-value, base interest rate as the discount rate `r`) and from the expectations configuration of §4.2.1 (the `trend_threshold = 0.05` for asking-price classification). Two property-market-specific design parameters are coded outside the templates and documented inline in §4.2.3: the listing-expiration window of `10` ticks (`property_market.py:235`) and the Gordon-valuation guard band that floors the denominator at `0.01` and clips the resulting valuation to `[0.1 · property.value, 10 · property.value]` (`property_market.py:121-128`). |

The `sci_fi.json` template is documented in its own source file as speculative and carries no empirical calibration target across any of the audited modules.

## 6.2 Era templates and tunable heuristics

The simulation supports two parallel template systems that originated from independent design decisions in the demography and economy specs. The discrepancy in shape and count is a deliberate side effect of the staged spec history rather than a structural intent, and it is recorded explicitly here because the two systems will eventually converge during Plan 4.

The demography templates are five JSON files under `epocha/apps/demography/templates/`: `pre_industrial_christian.json`, `pre_industrial_islamic.json`, `industrial.json`, `modern_democracy.json`, and `sci_fi.json`. Each file carries a flat dictionary whose keys are consumed by a specific model of §4.1: `mortality`, `fertility`, and `couple` for §4.1.1-§4.1.3, `trait_inheritance`, `social_inheritance`, and `economic_inheritance` for §4.1.4 — the first two each carrying an `era_noise` subsection that declares, per era and per character, the mean and amplitude of the observed distribution the transmission kernel must realize — `migration` for §4.1.5, plus the simulation-level `acceleration`, `max_population`, `fertility_agency`, `age_pyramid`, `sex_ratio_at_birth`, and `sexual_orientation_distribution` entries shared across models. The pre-industrial pair is a deliberate split: the two files share identical mortality and fertility blocks (because the empirical historical record does not justify per-confession differentiation in the underlying biological schedules) and differ only in the `couple` block, where `pre_industrial_islamic.json` carries `marriage_market_type: arranged` against the autonomous regime of all the other templates and `pre_industrial_christian.json` carries `divorce_enabled: false` to model the canonical Catholic-marriage indissolubility regime. The JSON schema is narrow, and the loader enforces six clauses at load time (`template_loader.py:validate_template`). It rejects: any unknown key, at any nesting depth; any out-of-range value, with rates, heritabilities and regression coefficients confined to `[0, 1]` and amplitudes required strictly positive; any missing mandatory nested section, `trait_inheritance.era_noise` and `social_inheritance.era_noise` among them; any missing entry, so that every key of `trait_inheritance.heritability` carries its own entry in `trait_inheritance.era_noise` and a section present but incomplete is refused naming what is absent; any declared `(era_mean, era_sd)` pair falling outside the admissible region of the transmission kernel, computed by the deterministic grid fixed point described in §4.1.4; and any inconsistency between `heritability` and `era_noise` in either direction. Each rejection names the offending field by its full path and, where one applies, the admitted interval. Exactly one untyped field is permitted and never consumed: an optional `_note` carrying free text for the reader, which two of the five templates use.

**This paragraph previously asserted that property and the assertion was false, which is worth stating rather than quietly correcting.** Verified by running the validator against a single crafted template: it accepted an invented top-level key, an `era_noize` section with a typo, an `estate_tax_rate` of 40 rather than 0.40, a heritability of 5.0 and a negative education-regression coefficient — all five at once and without protest. No unknown-key, type or range check existed anywhere in the loader. The contract above was specified by clause A9 of the design-spec amendment of 2026-08-07 and implemented on the branch carrying that amendment. **The frozen-at-commit pin of this whitepaper still points at the pre-amendment state**, so a reader who checks out the pinned commit will find the loader without these checks; the pin is re-resolved when the amendment branch merges.

The economy templates are four Python factory functions in `epocha/apps/economy/template_loader.py`: `_pre_industrial_template()`, `_industrial_template()`, `_modern_template()`, and `_sci_fi_template()`. Each function returns a nested dictionary that the loader passes to `EconomyTemplate.objects.get_or_create()`, and the per-era differentiation is realized by varying a small set of inputs (currency table, goods elasticities, factor stocks, behavioral configuration) rather than by maintaining four independent JSON files. The behavioral block specifically is built once by `_behavioral_config()` (`template_loader.py:144-198`) and is identical across all four templates as of the pinned commit, on the grounds that the audited Plan 2 calibration evidence did not motivate per-era differentiation at spec time. Per-era differentiation of `λ_base`, the Becker modulation coefficients, `risk_premium`, `max_rollover`, and `default_loan_duration_ticks` is the explicit calibration debt assigned to Plan 4. The two systems use different counts (five for demography, four for economy) because the demography spec required separating the two pre-industrial confessional regimes to support the marriage-market and divorce-regime distinction, while the economy spec found no analogous structural distinction at the price-and-credit layer that would justify a fifth template.

Beyond the per-template parameter values, the audited modules carry a small number of structural constants that are coded in the source rather than in the templates because they are properties of the model rather than calibration choices. The expectations bounds `_LAMBDA_MIN = 0.05` and `_LAMBDA_MAX = 0.95` (`expectations.py:39-40`) prevent degenerate forecasts and are documented in §4.2.1; the `CASCADE_LOSS_THRESHOLD = 0.5` of the Allen-Gale contagion pass and the matching listing-expiration window of `10` ticks are documented in §4.2.2 and §4.2.3 respectively. These are tunable heuristics in the sense that they admit revision under future calibration evidence, but they are not template fields and per-era differentiation is not a Plan 4 deliverable for them.

## 6.3 Fitting procedures

The mortality module ships with a working fitting helper, `fit_heligman_pollard()` in `epocha/apps/demography/mortality.py:103-158`, that wraps `scipy.optimize.curve_fit` against the eight-parameter HP functional form. The function takes a list of ages and the corresponding observed annual mortality probabilities `q(x)` and returns a dictionary keyed by the eight HP parameter names (`A`-`H`). Initial conditions default to the array `p0 = [0.005, 0.02, 0.1, 0.001, 10.0, 22.0, 0.00005, 1.1]` reported in the source, and parameter bounds are enforced via the `bounds=(lower, upper)` argument with `lower = [0.0, 0.0, 0.0, 0.0, 0.1, 1.0, 0.0, 1.0]` and `upper = [0.1, 0.5, 1.0, 0.05, 50.0, 50.0, 0.001, 1.5]`. The bounds match the admissible ranges reported inline in Table 4.1 and are the same bounds that gate the per-era values shipped in the five Plan 1 templates. A degenerate-input guard rejects mortality schedules that are uniformly zero before passing them to the optimizer, so the function fails fast with a descriptive `RuntimeError` rather than letting `curve_fit` silently minimize to a parameter-space boundary. The bounds themselves are the subject of audit debt B-5 of the demography spec: the current values are coherent with the actuarial literature on the HP model (Heligman and Pollard 1980; Tabeau, van den Berg Jeths, and Heathcote 2001) but the per-bound justification chain is reserved for Plan 4 calibration, alongside the first end-to-end fit of the helper against a real life table from the Human Mortality Database.

The fertility module does not yet ship a counterpart fitting helper for the Hadwiger ASFR. The current implementation in `epocha/apps/demography/fertility.py` only evaluates the canonical formula at the agent's age against the per-era `H`, `R`, and `T` values loaded from the JSON templates: a `fit_hadwiger()` that would invert the formula against an observed ASFR profile is recorded as a Plan 4 deliverable. The reason for the asymmetry is that the Plan 1 fertility scope explicitly limited itself to the per-tick evaluation pass and to the Becker modulation that wraps it; the calibration loop that would consume historical ASFR profiles (parish records pre-industrial England via Wrigley and Schofield (1981); modern ASFR series via Eurostat or HMD) is the central deliverable of Plan 4 and will mirror the structure of `fit_heligman_pollard()` once implemented. The Becker modulation coefficients of Table 4.4 are likewise not currently fitted: they are seeded with the same five values across all five templates and the per-era calibration is the central deliverable of debt B2-07 in Plan 4. The credit, banking, and property-market parameters of Tables 4.8-4.9 are calibrated qualitatively against Homer and Sylla (2005) for the per-era interest-rate ranges and against the Basel III convention for the modern reserve ratio, but no automated fitting procedure is implemented for them: per-era differentiation of the uniform parameters of Table 4.9 and of the property-market base values is reserved for Plan 4 alongside the demography fits.

---

# 7. Validation Methodology

> Status: validation experiments specified, not yet executed. Execution is tracked as a separate follow-up (see project memory `project_validation_experiments_pending.md`).

Chapter 7 lays out the validation methodology for the audited modules of Chapter 4. The chapter describes which empirical or quasi-empirical targets each model is meant to reproduce, the metrics against which the comparison is run, the acceptance thresholds that decide whether a candidate parameter set passes, and the commands by which the validation suite will be reproducible from a clean checkout. The chapter is methodological rather than evidential: the experimental campaign that consumes the methodology is the central deliverable of Plan 4 and is explicitly outside the scope of the present whitepaper revision.

## 7.1 Target datasets per audited module

The five audited models of Chapter 4 are validated against the datasets of Table 7.1. Each dataset is paired with a citation already catalogued in §13 (or added to §13 by the present revision in the case of Mokyr 1985) and with the scope of the comparison the dataset enables. The Plan 4 calibration campaign will source the actual data series from the cited repositories and stage them under a future `data/` directory whose path is not yet fixed.

Table 7.1 — Target datasets for the audited modules.

| Module | Dataset | Citation in §13 | Source / DOI | Scope |
|---|---|---|---|---|
| Mortality (Heligman-Pollard fit) | England and Wales 1851-1900 life tables; Sweden 1751-1900 life tables | Human Mortality Database (HMD) (2024) | https://www.mortality.org | Inversion of the eight HP parameters from observed `q(x)` columns; per-era calibration of the `pre_industrial_*` and `industrial.json` mortality blocks of §6.2 |
| Fertility (Hadwiger ASFR fit) | Reconstructed parish-records ASFR profiles for pre-industrial England | Wrigley and Schofield (1981) | ISBN 978-0-521-35688-6 | Inversion of `H`, `R`, `T` against an observed ASFR; per-era calibration of Table 4.3 |
| Crisis mortality (excess-deaths benchmark) | Irish Famine 1845-1851 county-level death series | Mokyr (1985) | ISBN 978-0-04-941011-7 | Reproduction of the order of magnitude of an excess-mortality shock as a benchmark for the Heligman-Pollard "external_cause" component triggered by famine, war, or epidemic events |
| Couple formation (European marriage pattern) | Singulate Mean Age at Marriage (SMAM) and never-married fraction series for early-modern Western Europe | Hajnal (1965) | https://doi.org/10.4324/9781315127019 | Validation of the Gale-Shapley + Goode 1963 implementation of §4.1.3 against the empirical marriage-pattern signature |
| Economy (base layer, §4.8) | None as of the pinned commit | n/a | n/a | Calibration deferred to Plan 4: candidate targets are long-run CES elasticity estimates for the production function, historical price-dispersion series for the tâtonnement regime, and national-accounts factor-share series (labour ~0.55-0.65 in modern economies) against the 0.6/0.15/0.25 partition defaults |
| Economy (behavioral integration) | None as of the pinned commit | n/a | n/a | Calibration deferred to Plan 4: Cagan (1956) λ profiles will be sought against post-WWII inflationary episodes; Diamond-Dybvig (1983) bank-run thresholds will be sought against Reinhart and Rogoff (2009) banking-crisis catalogues; the property-market Gordon-Shiller comparison will be sought against Shiller's long-horizon housing series |

## 7.2 Comparison metrics

Three metrics are used jointly across the audited modules, with the choice of which to apply per-experiment driven by the shape of the target dataset.

The root mean squared error (RMSE) on per-age rates is the primary metric for the mortality and fertility fits, computed against the observed schedule on the same age grid: `RMSE = sqrt(mean((q_fit(x) − q_obs(x))^2))` for mortality and the analogous expression on `f(x)` for fertility. RMSE on rates is preferred over RMSE on cumulative quantities because the per-age structure of both schedules is what carries the demographic information; a fit that matches the cumulative quantity but distorts the age structure is not a good fit. The Kolmogorov-Smirnov (KS) two-sample test on age-at-marriage and age-at-first-birth distributions is the primary metric for the couple-formation experiments, on the grounds that the Hajnal (1965) signature is a distributional claim rather than a moment-based one. The log-likelihood of the observed schedule under the fitted parameters is the primary diagnostic for the goodness-of-fit decision when the fit is performed via maximum likelihood rather than via least squares; for the `scipy.optimize.curve_fit` path of `fit_heligman_pollard()` the log-likelihood is computed post hoc as a secondary check.

## 7.3 Acceptance thresholds

The per-module acceptance thresholds of Table 7.2 are conservative: they encode "the fit captures the signature qualitatively and within an order of magnitude that the demographic literature treats as the same regime", not "the fit is statistically indistinguishable from the target". The latter would require sample-size assumptions that synthetic per-era seed populations of the order of `10^4` agents do not support.

Table 7.2 — Acceptance thresholds per audited module.

| Module | Threshold | Rationale |
|---|---|---|
| Mortality (HP fit) | RMSE on annual `q(x)` per single-year age class strictly less than `0.005`, and the fitted curve reproduces the three HP regimes (early-life decline, accident hump, senescent rise) qualitatively rather than collapsing to a Gompertz monotone | The threshold matches the order of magnitude of the residuals reported in Heligman and Pollard (1980) for their original Australian fits |
| Fertility (Hadwiger fit) | Total Fertility Rate `TFR ∈ [4.5, 6.5]` for the pre-industrial era after fitting `H`, `R`, `T` against the Wrigley-Schofield ASFR profile | The interval brackets the historically attested TFR range for early-modern England (Wrigley and Schofield 1981) |
| Crisis mortality (Irish Famine analog) | Excess mortality consistent with approximately `12%` cumulative over five years when the simulation is forced with a famine shock of comparable magnitude | The `12%` figure is the order of magnitude of the population loss reported by Mokyr (1985) for the 1846-1851 Irish Famine combining excess deaths and forced emigration |
| Couple formation (European marriage pattern) | Singulate Mean Age at Marriage `SMAM ∈ [25, 28]` years and never-married fraction at age 50 in `[10%, 20%]` after running the founder-population builder and aging the cohort | The two intervals are the canonical signature of the European Marriage Pattern reported in Hajnal (1965) |
| Economy (base layer, §4.8) | Acceptance criteria deferred to Plan 4 alongside the dataset selection of §7.1; the audited invariants (factor-income injection equals V, goods conservation, tax transfer symmetry, seeded determinism of the non-LLM economic step) are enforced by the regression suite rather than by empirical thresholds | No empirical target dataset has been specified at the time of writing |
| Economy (behavioral integration) | Acceptance criteria deferred to Plan 4 alongside the dataset selection of §7.1 | No empirical target dataset has been specified at the time of writing |

A fit that fails its threshold does not invalidate the model; it triggers a debugging loop that examines first the seed values of the per-era template, then the bounds of the fitting helper, and only finally the model formulation itself. The order is the standard one for any calibration loop: the most likely failure mode is a poorly-seeded template, the next-most-likely is a too-tight or too-loose bound, and the least-likely is a structural defect of the model that has already passed adversarial scientific audit at the spec stage.

## 7.4 Reproducibility commands

The unit-test suite that exercises the audited modules at the algorithm level is reproducible today via the standard pytest invocations declared in the project quickstart:

```bash
pytest --cov=epocha -v                                  # full suite
pytest epocha/apps/demography/ -v                       # demography only
pytest epocha/apps/economy/ -v                          # economy only
pytest epocha/apps/demography/tests/test_mortality.py   # one module
```

The validation suite proper — the campaign that consumes the datasets of §7.1, runs the metrics of §7.2, and decides against the thresholds of §7.3 — is not yet implemented. Plan 4 will introduce a `validation/` directory at the repository root with one Python script per audited module (`validation/validate_mortality.py`, `validation/validate_fertility.py`, `validation/validate_couple.py`, and so on); each script will load its dataset, run the fit or the simulation forward, compute the metrics, and emit a pass/fail report against the threshold. The scripts will be invocable individually for debugging and collectively via a Makefile target so that the full validation campaign reduces to a single command on a clean checkout. The exact script names and the Makefile target are deferred to the Plan 4 design phase and are not committed to in the present chapter.

## 7.5 Status

Validation experiments are specified, not yet executed. The full execution of the campaign described in this chapter — dataset acquisition, script implementation, metric computation, and threshold evaluation — is tracked as a follow-up under the memory note `project_validation_experiments_pending.md` and is the central deliverable of Plan 4.

---

# 8. Designed Subsystems (implemented, audit pending)

Chapter 8 covers the one remaining Epocha cluster that is implemented in code and exercised by unit tests but has not yet completed the adversarial scientific audit that gates promotion to Chapter 4 status. The 2026-04-12 batch audit (`docs/scientific-audit-2026-04-12.md`) opened a list of INCORRECT, UNJUSTIFIED, INCONSISTENT, and MISSING findings against eight of the modules below; reputation converged on round 2 (2026-05-12) and was promoted to §4.3, the rumor-propagation cluster (information flow, distortion, belief filter, plus affinity per the audit's IF-1 fix) converged on round 2 (2026-05-16) and was promoted to §4.4, the political-institutions cluster (government, government_types, institutions, stratification, election) converged on round 2 (2026-05-16) and was promoted to §4.5, and movement converged on round 2 (2026-05-16) and was promoted to §4.6, factions converged on round 2 (2026-05-16) and was promoted to §4.7, and the economy base layer — which was NOT in that batch — converged on round 12 of its first audit (2026-07-16) and was promoted to §4.8, leaving the Knowledge Graph as the single module in this chapter pending. Its audit is tracked as the highest-priority item of the roadmap of Chapter 9. The subsection therefore restates the cluster scope, the literature pointers carried by the spec and the module docstrings, and the code path, then closes with a status line that names the spec under which the audit will resume. Literature pointers in this chapter are attributions recorded by the spec or the source rather than primary-source-verified Methods-grade citations of the Chapter 4 kind.

## 8.1 Knowledge Graph

The Knowledge Graph cluster implements the simulation's long-horizon memory: the per-simulation graph of entities, relations, and events that the LLM context builder of §3.5 queries to ground each agent's per-tick decision in the simulation's prior history rather than re-reading the entire raw event log. The cluster is split across nine modules under `epocha/apps/knowledge/`: `chunking.py` slices the raw event log into LLM-sized passages, `extraction.py` runs the LLM-driven entity-and-relation extractor over each chunk, `embedding.py` produces the dense vector representations of every chunk and every node (the multilingual-e5-large model is the current default per the spec), `merge.py` deduplicates extracted nodes against the existing graph, `normalizer.py` canonicalises entity surface forms to their preferred labels, `materialization.py` writes the consolidated graph back to the persistence layer, `ontology.py` declares the entity and relation type system, `prompts.py` collects the LLM prompts for extraction and merge, and `api.py` exposes the graph to the dashboard graph view. The literature pointers in the spec are the Retrieval-Augmented Generation framework of Lewis et al. (2020) for the broader retrieve-then-generate architecture, the sentence-embedding family of Reimers and Gurevych (2019) for the dense-vector representations (multilingual-e5-large is the current production choice for its 100+ language coverage and reproducibility properties), and the broader knowledge-graph reasoning literature for the entity-relation typology. The spec contrasts the Epocha approach with GraphRAG and with MiroFish in its FAQ section and records the choice to materialise the graph per-simulation rather than across simulations as a deliberate scope choice for the MVP. Code paths: `epocha/apps/knowledge/{ingestion,extraction,embedding,merge,normalizer,materialization,ontology,chunking,prompts,api}.py`.

> Status: implemented in code, Round 2 audit pending. See `docs/superpowers/specs/2026-04-11-knowledge-graph-design.md`.

---

# 9. Roadmap

The roadmap is ordered by priority rather than by chronology: the audit on the one module still pending in §8 (reputation converged on round 2 in 2026-05-12 and was promoted to §4.3; the rumor-propagation cluster — information flow, distortion, belief filter, plus affinity — converged on round 2 in 2026-05-16 and was promoted to §4.4; the political-institutions cluster converged on round 2 in 2026-05-16 and was promoted to §4.5; movement converged on round 2 in 2026-05-16 and was promoted to §4.6; factions converged on round 2 in 2026-05-16 and was promoted to §4.7; the economy base layer converged on round 12 of its first audit in 2026-07-16 and was promoted to §4.8) is the gating item because every subsequent calibration and validation effort depends on the audited subset being closed first. The remaining items are listed in a coarse expected-effort order and are tracked in the long-form memory backup under `docs/memory-backup/`; cross-references to the relevant memory note are inlined where they exist.

- **HIGH PRIORITY — adversarial audit of the Knowledge Graph.** The Knowledge Graph is the single module remaining in §8 pending its first scientific audit pass. Six clusters have already converged and been promoted: reputation on round 2 (2026-05-12) to §4.3, the rumor-propagation cluster (information flow, distortion, belief filter, plus affinity) on round 2 (2026-05-16) to §4.4, the political-institutions cluster (government, government_types, institutions, stratification, election) on round 2 (2026-05-16) to §4.5, movement on round 2 (2026-05-16) to §4.6, factions on round 2 (2026-05-16) to §4.7, and the economy base layer on round 12 of its first audit (2026-07-16) to §4.8. The Knowledge Graph audit is the gating item before it can be promoted from §8 to §4 status, before its parameters can be added to the parameter tables of §6, and before it can enter the validation campaign of §7.
- **Demography Plan 3 residual work item (deferred design defects).** Plan 3 itself is built: inheritance and migration are implemented, unit-tested, and documented in §4.1.4 and §4.1.5, and their phase-6 adversarial code audit converged on 2026-08-05 over the code as scoped. What remains is the work item that audit explicitly deferred: eight design-level defects, each requiring a phase-2 requirements gate of its own rather than a code patch. The two with the widest consequences are the non-variance-preserving polygenic kernel (trait spread collapses to 48.8% of the declared era distribution within three generations) and the gender-blind shari'a spouse share. The full list, with measured magnitudes, is in the Simplifications paragraphs of §4.1.4 and §4.1.5 and is inventoried in §11.
- **Demography Plan 4 (Initialisation, Engine integration, Historical validation).** Plan 4 wires the demography modules of §4.1 — currently implemented and unit-tested in isolation — into the live tick loop of `epocha/apps/simulation/engine.py`, supplies the initialisation procedure that seeds a starting population from the era template, and runs the historical-validation campaign of §7 against the Wrigley-Schofield (1981) and Human Mortality Database targets. This is the central deliverable that closes the implementation-gap disclosure carried by §4.1 and resolves the validation-pending caveat carried by §7.5.
- **Economy financial markets (Spec 3 to write).** The behavioral integration of §4.2 covers adaptive expectations, credit and banking, and the property market; the next economy spec extends to bond and equity markets, asset-price contagion across multiple banks, and the inter-bank lending channel deferred under the simplifications of §4.2.2. The spec is not yet drafted; the work item is recorded in the long-form roadmap memory.
- **Validation experiments execution.** The campaign specified in Chapter 7 — dataset acquisition, script implementation, metric computation, and threshold evaluation — is the central deliverable tracked in `docs/memory-backup/project_validation_experiments_pending.md`. Execution is bound to Plan 4 of the demography roadmap above (which provides the live tick-loop integration the validation requires) and to the audit of the remaining §8 module (the Knowledge Graph).
- **Knowledge Graph evolution (live updates from simulation).** The Knowledge Graph cluster of §8.1 currently materialises the graph from the simulation log in batch passes; the evolution work item replaces the batch pass with a live update that incrementally extracts entities and relations from each tick and merges them into the existing graph without a full re-extraction. The change keeps the graph current within a bounded delay of the live tick rather than at end-of-run granularity, which is the prerequisite for graph-grounded LLM context at the per-tick decision step of §3.2.
- **Analytics psicostoriografia.** The analytics spec at `docs/superpowers/specs/2026-04-06-analytics-psicostoriografia-design.md` covers the post-hoc analysis layer that surfaces emergent patterns from a completed simulation: phase-space trajectories, zone-level cohort comparisons, event-cascade attribution, and the publication-grade plot exports needed for the scientific paper of the project's final deliverable. The spec is drafted; implementation is deferred behind the audit re-pass and Plan 4.
- **Broader PostGIS adoption.** PostGIS is already enabled per §3.6 with zone geometries stored as WGS84 polygons; the broader-adoption work item extends the geospatial surface to agent trajectories (per-tick location history with spatial indices), routed-distance queries between zones (replacing the abstract zone-graph distance of §4.6 with shortest-path computation against the actual geometry), and per-zone catchment analysis for the economy and demography modules.
- **Multi-level agents (organisations, states, coalitions).** The current Epocha population is a flat set of individual agents; the multi-level work item extends the agent ontology to corporate actors that have their own decision pipelines, their own memory, and their own action space, with the individual agents as members and with state and coalition layers above the organisation layer. The conceptual frame and the literature anchors are recorded in `docs/memory-backup/project_multilevel_agents.md`; the spec is not yet drafted.
- **Narrative generator.** The narrative-generator work item produces a long-form scientific-historical novel from the completed simulation — the per-zone, per-cohort, per-character arcs woven into a publication-grade narrative in the chosen output language with full citations to the underlying simulation events. The conceptual frame is recorded in `docs/memory-backup/project_narrative_generator.md`; the work item is bound to the analytics spec above (which produces the structured material the generator weaves) and to the Knowledge Graph evolution item (which provides the entity catalog the narrative references).
- **Media layer (newspapers, social feed).** The media-layer work item materialises the in-simulation press: per-tick newspaper editions whose articles are generated from the simulation events through an LLM editorial pipeline, social-feed analogues for the modern-era templates, and the cross-pollination of media coverage back into the rumor-propagation cluster of §4.4 as a special information-event subtype. The conceptual frame is recorded in `docs/memory-backup/project_media_layer.md`; the work item is bound to the Knowledge Graph evolution item above.

---

# 10. Discussion

Every choice documented in the preceding chapters carries a trade-off that
is worth stating in the open rather than hiding behind the convergence
verdict of the audit. The most consequential is the cost of LLM cognition
relative to the realism it buys: a tick that exercises the full agent
decision pipeline of §3.2 carries a token cost per agent that scales with
the personality, memory, and contextual blocks the prompt must include, and
the per-tick budget envelope therefore caps the population the simulator
can carry on a given hardware tier rather than emerging from a structural
property of the model. The Plan 1 and Plan 2 audited modules accept several
deliberate simplifications to keep the per-tick cost bounded under this
envelope. The Hadwiger ASFR of §4.1.2 is evaluated deterministically at the
agent's age rather than drawn from a per-mother stochastic model of
time-to-conception; the Becker modulation coefficients of Table 4.4 are
homogeneous across all five demography templates pending Plan 4 calibration;
the Diamond-Dybvig credit-and-banking machinery of §4.2.2 carries a single
aggregate bank rather than a population of competing banks with an
inter-bank lending channel; the property-market settlement of §4.2.3 is
single-round take-it-or-leave-it rather than a multi-round bid-ask
convergence. None of these simplifications is a defect in the audited
sense — each is documented inline in the corresponding §4.x Simplifications
paragraph and tracked as a Plan 4 calibration deliverable — but their
cumulative effect is that the audited scientific layer is leaner than the
literature surveyed in §2 would in principle support. A second visible
trade-off is the engine-integration gap that §4.1 carries: mortality,
fertility, and couple formation are implemented and unit-tested in
isolation, but their orchestration into the live tick loop in
`epocha/apps/simulation/engine.py` is the central deliverable of Plan 4
and is not yet active in production code, in contrast to the §4.2 economy
modules that are genuinely live in the per-tick pipeline. Finally, the
validation campaign of Chapter 7 is methodological rather than evidential
as of the pinned commit: the targets, metrics, and acceptance thresholds
are specified, but the experiments that consume them are tracked under
`project_validation_experiments_pending.md` and bound to the same Plan 4
deliverable.

The scientific limits of the present work go beyond the simplifications
inside the audited subset. One module — the Knowledge Graph (§8.1) — is
implemented in code and exercised by unit tests but has not yet completed
the adversarial audit that gates promotion to Chapter 4 status;
the open INCORRECT, UNJUSTIFIED, INCONSISTENT, and MISSING findings from
the 2026-04-12 batch audit are catalogued in
`docs/scientific-audit-2026-04-12.md` and tracked under
`project_audit_repass_batch_2026_04_12_pending.md`. Within the audited
subset, several parameter values are seeded as calibration heuristics rather
than derived from a primary-source measurement: the Becker modulation
coefficients `β₀..β₄` of equation (4.3), the per-agent adaptation-rate
modulation coefficients `n_mod`, `o_mod`, `c_mod` of equation (4.10), the
Stiglitz-Weiss `risk_premium = 0.5` of equation (4.13), and the Allen-Gale
`CASCADE_LOSS_THRESHOLD = 0.5` of the contagion pass are all documented
inline as tunable design parameters with the per-era differentiation
deferred to Plan 4. The discrete-time tick scheme is itself a substantive
modelling choice: events that occur within the same tick — multiple deaths,
simultaneous births, a property sale and a loan default on the same agent —
are resolved sequentially within the per-tick orchestrator rather than
treated as genuinely concurrent, which is the appropriate granularity for
the per-tick cost envelope but which suppresses any intra-tick interaction
the continuous-time literature would expose. The joint maternal-mortality
resolver of §4.1.2 is the one place where intra-tick coupling is treated
explicitly, and it is treated that way precisely because resolving generic
mortality first and childbirth mortality second on the same mother in the
same tick would produce a measurable bias.

Where Epocha sits in the broader landscape is best read against three
neighboring traditions. Pure rule-based ABM platforms (NetLogo, Mesa,
Repast HPC, EURACE) excel at scaling to populations of millions of agents
under fully specified individual rules, on the strength of decades of
optimisation work and a mature toolchain; the cost of that scale is that
individual-agent cognition is constrained to whatever the rule grammar can
express, and emergent behavior that would require natural-language
reasoning, narrative memory, or personality-modulated deliberation has to
be approximated by hand-tuned heuristics. Pure LLM agent simulations
(Park et al. 2023 and the family of generative-agent experiments that
followed) excel at the opposite end: dozens of agents in a stylised
environment can exhibit credible social dynamics with no hand-tuned
behavioral grammar, on the strength of the LLM's natural-language
cognition; the cost is that the demographic and economic substrates these
experiments inherit from the surrounding environment are too thin to carry
multi-decade horizons or population-level statistics that the social-science
literature would recognise as well-formed. Epocha's contribution is the
hybrid: a rule-based substrate (§3.6 economic engine, §4.1 demographic
engine, §4.2 behavioral integration) that carries the population dynamics
on the timescales the demographic and economic literature operates on, with
LLM cognition layered on top of the substrate at the per-agent decision
step (§3.2) where personality, memory, and natural-language deliberation
carry the explanatory weight. The hybrid pays a cost in per-tick LLM tokens
that pure rule-based platforms do not, and inherits a cost in audit
discipline that pure LLM platforms have not historically borne, but in
exchange it makes the multi-scale aggregation explicit (individual to
faction to state) and admits long-horizon experiments that neither neighbor
can run with comparable scientific grounding.

The class of research questions Epocha is designed to enable follows
directly from the hybrid. Long-horizon emergence experiments — does a
specific institutional arrangement, a specific shock pattern, or a specific
personality distribution produce the qualitative trajectories the historical
record exhibits over centuries — become tractable because the audited
demographic and economic substrate carries the multi-decade dynamics while
the LLM-cognition layer carries the per-agent variation. Counterfactual and
intervention experiments — what would have happened if the Irish Famine of
§7.1 had triggered an earlier institutional response, what would have
happened if the property-market crash of §4.2.3 had been preceded by a
different banking-confidence trajectory — become tractable because the
era-template machinery makes the parameter intervention explicit and the
seeded RNG of §3.4 makes the non-LLM part of the run reproducible. Multi-scale aggregation —
from individual cognition through faction-level coordination to state-level
policy — becomes tractable because the persistence model of §3.7 carries
both the individual-agent rows and the institutional rows as first-class
entities rather than as derived aggregates. And full auditability of a run —
each per-agent decision and the emergent narrative arc it produces is
completely logged and can be traced back to the simulation state that drove
it — becomes the basis for the publication-grade scientific paper that the
project's roadmap of Chapter 9 names as its final deliverable. The decision
trail is auditable, not reproducible: because each decision is LLM output at
non-zero temperature without a seed, re-running the same scenario with the
same seed does not reproduce the same per-agent decision log.

---

# 11. Known Limitations

The following catalogue groups the open limitations by module. Each entry is
deliberately short — the substantive context lives in the corresponding §4
Simplifications paragraph or §8 status line — and exists here as a single
authoritative inventory for the reader who needs the project-wide view in
one place. Two cross-cutting follow-ups underlie most of the entries: the
audit on the one §8 module still pending (the Knowledge Graph) tracked under
`project_audit_repass_batch_2026_04_12_pending.md` and the validation
campaign tracked under `project_validation_experiments_pending.md`.

**Mortality (§4.1.1).**
- No cohort effects: every agent is exposed to the era template active at
  the simulation tick rather than to the mortality regime in force at the
  agent's birth.
- Coarse cause-of-death labels (`early_life_mortality`, `external_cause`,
  `natural_senescence`) reflect the three HP components rather than a
  medical aetiology.
- No explicit tail model beyond the biological extreme: the `0.999` cap on
  annual mortality probability is a numerical guard for the geometric tick
  conversion, not a substantive late-life-mortality plateau.
- Per-tick evaluation is exercised by the unit-test suite but is not yet
  invoked from the live tick loop in `epocha/apps/simulation/engine.py`;
  integration is the central deliverable of demography Plan 4.

**Fertility (§4.1.2).**
- Hadwiger ASFR is evaluated deterministically at the agent's age with no
  inter-individual heterogeneity in biological fecundity, in contrast to
  the Bayesian-learning extension that would let each agent learn its own
  `T` parameter from realised inter-birth intervals.
- Twin and higher-order multiple births are not modelled: each successful
  birth event creates exactly one newborn.
- Becker modulation coefficients of Table 4.4 are homogeneous across all
  five demography templates, tracked as audit debt B2-07 and assigned to
  Plan 4 calibration.
- Tick-loop integration deferred to demography Plan 4.

**Couple formation (§4.1.3).**
- Only monogamous couples are representable; polygynous and polyandrous
  configurations are deferred (audit fix MISS-8).
- Two-gender schema for the matching primitives: although the agent layer
  carries `male`, `female`, `non_binary`, the homogamy score and the
  stable-matching algorithm do not consume gender or sexual orientation
  fields as of the pinned commit.
- No remarriage cooldown: the per-template `mourning_ticks` field is
  loaded but not yet consumed by the eligibility check, so a widowed
  agent can in principle re-pair on the tick following the partner's
  death.
- Gale-Shapley is applied at initialisation only, not as a runtime
  fallback when a large unmatched cohort accumulates.
- Tick-loop integration deferred to demography Plan 4.

**Inheritance (§4.1.4).** The first six entries are design-level defects
that the converged phase-6 code audit explicitly did not cover; they are
deferred to a separate work item with its own phase-2 gate and are open
as of the pinned commit.
- The polygenic kernel is not variance-preserving. Equation (4.46) is a
  convex combination rather than the Falconer and Mackay decomposition
  of (4.48): measured trait spread collapses to 48.8% of the declared
  era distribution within roughly three generations and stays there, so
  every simulated society drifts toward homogeneity on all thirteen
  heritable traits and realised heritability stops matching the cited
  figures after the first generation.
- The single-parent fallback does not halve the genetic signal despite
  the spec and the docstring claiming it does: the implemented parent-
  offspring regression coefficient is `h²` where Falconer gives `h²/2`,
  so the implemented resemblance is twice the cited model's.
- The shari'a spouse fraction is gender-blind. Q4:12 as documented by
  Powers (1986) gives the widower 1/2 without a child and 1/4 with, the
  widow 1/4 and 1/8; the implementation applies the widow's schedule to
  both partners.
- Estate tax and remainder are two independent products, so exact
  conservation fails for 18.8% of random pairs at a worst absolute error
  of 1.16e-10, while the heir allocation fifty lines away is exact by
  construction.
- Three templates carry `education_regression_rho` values that
  contradict the design's cited figures (0.4 / 0.4 / 0.2 against
  0.42 / 0.35 / 0.25); the modern value is attributed to Chetty et al.
  (2014) at 0.35 and ships at 0.4.
- The era-noise priors `DEFAULT_ERA_MEAN = 0.5` and
  `DEFAULT_ERA_SD = 0.15` are documented placeholders that are in
  practice the parameters, since no template declares an `era_noise`
  section; combined with the variance collapse above they set the fixed
  point the population converges to.
- `get_seeded_rng()` mixes the simulation's database primary key into
  the seed material, so re-running a published seed against a fresh
  database yields different random streams.
- Representation *per stirpes* is absent from the heir ladder:
  grandchildren cannot inherit when their own parent predeceased the
  deceased.
- Of the five implemented succession rules, the shipped templates
  exercise only three; `matrilineal` and `nationalized` are declared by
  no template.
- Non-binary heirs are treated as non-male under `shari'a` and are
  ordered with female heirs under `primogeniture`; the `shari'a`
  residuary cascade stands in for the fuller classical `'asaba`
  hierarchy. Both are documented design scope, not defects.
- Tick-loop integration deferred to demography Plan 4.

**Migration (§4.1.5).** The first two entries are design-level defects
deferred with those of §4.1.4.
- The flight trigger compares a wealth stock against a per-tick
  subsistence flow, which silently fixes the survival horizon at exactly
  one tick and treats an agent with thirty ticks of savings identically
  to one with a single tick's worth.
- The Harris-Todaro variant of equation (4.57) is dimensionally
  inconsistent: it subtracts a count of ticks from a per-tick currency
  rate. The audit ruled that the cost should be monetised as forgone
  earnings, `distance_cost_ticks · wage_current`; that ruling is
  recorded and deliberately not applied.
- "Zone stability" in the migration outlook is a simulation-wide scalar
  reported identically for every zone, because `Government` is a
  `OneToOneField` to `Simulation` and no per-zone stability exists in the
  schema.
- A migrating household arrives instantly while the deciding agent may
  still be in transit for several ticks, since household members bypass
  the multi-tick partial movement of §4.6.
- The informal-sector wage of the canonical Harris-Todaro model is set
  to zero: an agent who fails to find formal work at the destination is
  modelled as earning nothing there.
- The mass-flight denominator is a reconstruction, not a measurement:
  agents who died in the zone during the window understate it, agents
  who arrived during the window overstate it.
- Tick-loop integration deferred to demography Plan 4, which also owns
  the storage for `consecutive_ticks_under_subsistence`; until it
  exists, emergency flight cannot fire in a live run.

**Adaptive expectations (§4.2.1).**
- Single-variable per good: only the price level is forecast, with no
  joint cross-good forecast, no separate inflation-rate forecast, and no
  second-moment forecast.
- Per-agent `λ` is homogeneous across goods within a single agent; a
  goods-specific differentiation is a future refinement.
- The adaptation rate is not itself learned: the personality modulation
  of equation (4.10) is static, with no mechanism by which an agent whose
  forecasts have been systematically wrong updates its own `λ`.
- Multi-zone price aggregation is the unweighted cross-zone mean of
  `ZoneEconomy.market_prices` rather than a per-zone forecast per agent.

**Credit and banking (§4.2.2).**
- Single aggregate bank per simulation: no inter-bank lending market, no
  inter-bank exposure graph, no central-bank lender of last resort.
- Deposit insurance is abstract: `BankingState.is_solvent` gates new loan
  issuance but no explicit deposit-insurance fund exists, and depositors
  cannot literally withdraw deposits because `AgentInventory.cash`
  represents on-hand cash already.
- Loan negotiation is single-round take-it-or-leave-it; multi-round
  counter-proposals on amount, collateral, or duration are deferred.
- Rollover interest-rate increment is fixed at `1.10` per rollover rather
  than being a function of borrower leverage or the macroeconomic stress
  signal carried by the banking-confidence index.

**Property market (§4.2.3).**
- Single-round matching per tick: a buyer who loses to another buyer
  ordered earlier in the iteration receives no second chance within the
  same tick.
- Listings reset per tick after the `10`-tick expiration window with no
  time-priority fallback at equal price.
- Buyer intent is binary: `buy_property` does not carry a target type or
  a maximum price, and the matching pass selects the cheapest listing in
  the buyer's zone regardless of fit between property type and buyer
  role.
- Seller asking-price formation is owned by the LLM-decision layer of
  §3.2 rather than by the property market itself; this subsection treats
  the asking price as exogenous.

**Designed subsystems pending audit (§8).** One module still awaits its
adversarial audit: the Knowledge Graph. Five clusters from the original
2026-04-12 batch have converged and been promoted — reputation on round 2
(2026-05-12) to §4.3, the rumor-propagation cluster (information flow,
distortion, belief filter, plus affinity) on round 2 (2026-05-16) to
§4.4, the political-institutions cluster (government, government_types,
institutions, stratification, election) on round 2 (2026-05-16) to §4.5,
movement on round 2 (2026-05-16) to §4.6, and factions on round 2
(2026-05-16) to §4.7 — and the economy base layer, which was not in that
batch, converged on round 12 of its first audit (2026-07-16) and was
promoted to §4.8. The Knowledge Graph audit is tracked under
`project_audit_repass_batch_2026_04_12_pending.md` and gates its
promotion from §8 to §4 status, the inclusion of its parameters in §6
calibration tables, and its entry into the §7 validation campaign.

**Validation experiments (Chapter 7).** The methodology — datasets,
metrics, and acceptance thresholds — is specified across §7.1 to §7.3, but
the experimental campaign that consumes the methodology is bound to Plan 4
and is tracked under `project_validation_experiments_pending.md`.

**Knowledge Graph (§8.1).** The graph is currently materialised in batch
passes from the simulation log; live update from a running simulation,
which is the prerequisite for graph-grounded LLM context at the per-tick
decision step, is the dedicated work item of the roadmap of Chapter 9.

**Cross-cutting limitations.** Spatial dynamics beyond the abstract zone
graph are not exercised: PostGIS is enabled and zone geometries are stored
as WGS84 polygons per §3.6, but routed-distance queries between zones,
per-tick agent trajectory storage with spatial indices, and per-zone
catchment analysis for the economy and demography modules are deferred to
the broader-PostGIS work item of Chapter 9. The discrete-time tick scheme
of §3.1 resolves intra-tick events sequentially within the per-tick
orchestrator rather than treating them as concurrent, with the joint
maternal-mortality resolver of §4.1.2 the one place where intra-tick
coupling is treated explicitly. Real-time event handling between ticks is
not supported.

---

# 12. Conclusions

Epocha as documented at the pinned commit ships an audited demographic
substrate covering Heligman-Pollard mortality, Hadwiger-with-Becker
fertility, and Gale-Shapley with Goode 1963 couple formation (§4.1), an
audited behavioral economy covering Cagan-Nerlove adaptive expectations,
Diamond-Dybvig credit and banking, and a Gordon-anchored property market
(§4.2), an LLM-driven agent decision pipeline that consumes the
substrate's per-tick state and writes back into the persistence layer
(§3.2), an audited economy base layer covering CES production,
tâtonnement clearing, the conserved factor-income partition, and the
Fisher conservation diagnostic (§4.8), and one
implemented-but-pre-audit subsystem (§8): the Knowledge Graph. The runtime infrastructure
covers a tick engine with self-enqueuing Celery loop, a per-phase seeded
RNG strategy that makes the non-LLM part of every run reproducible across
machines from the commit hash, the seed, and the initial database state —
the LLM agent decisions and world generation are not seed-reproducible
(§3.4) — an
LLM-provider adapter that abstracts over OpenAI proper, Groq, Gemini,
OpenRouter, Together AI, Mistral, LM Studio, and Ollama with key rotation
and a Redis-backed sliding-window limiter (§3.5), and a dashboard plus
WebSocket chat layer that exposes the live simulation state and
agent-by-agent conversation surface to the operator (§3.8).

What distinguishes this codebase from the surrounding landscape is less
the individual modules — most have well-known antecedents in the
literature surveyed in §2 — and more the discipline that produces and
maintains them. The bilingual whitepaper of §1 is a living document
frozen at every merge to the development branch, with the Italian
companion published alongside the English original; every formula,
parameter, and algorithm in the audited chapters cites a primary source,
and unverified assertions are flagged inline rather than presented as
fact. The seven-phase canonical workflow that governs every subsystem
(ideation, requirements, plan, task breakdown, implementation, general
test, closure) carries two heavy and two light gates with explicit human
approval at each, and the mandatory adversarial-audit policy fires the
`critical-analyzer` reviewer at both spec time and code time with a
convergence loop that does not close on "close enough". Reproducibility
is built in rather than retrofitted: era templates carry the per-epoch
parameter values out of the source code and into auditable artefacts,
seeded RNG streams are partitioned by simulation, tick, and phase so
that a refactor cannot silently shift the random sequence one subsystem
sees, and Appendix B records the exact commands by which any reported
result that depends only on the seeded non-LLM part can be regenerated
from a clean checkout pinned at the frozen-at-commit hash.

The codebase is open source under the Apache 2.0 licence at
https://github.com/mauriziomocci/epocha, and contributions are welcome
through the canonical seven-phase workflow described in this paper.
Readers who wish to extend an audited module in §4 should expect a
spec-first contribution path with mandatory adversarial scientific audit
before any code is merged; readers who wish to advance the remaining §8
module (the Knowledge Graph) through its audit will find the open findings catalogued in
`docs/scientific-audit-2026-04-12.md` and tracked under
`project_audit_repass_batch_2026_04_12_pending.md`. The roadmap of
Chapter 9 names the immediate priorities — the Knowledge Graph audit,
demography Plan 3 (inheritance and migration),
demography Plan 4 (engine integration and historical validation), and
the next economy spec extending §4.2 to bond and equity markets — and
serves as the entry point for new contributors looking for a well-scoped
work item.

---

# 13. References

- Acemoglu, D., and Robinson, J. A. (2006). *Economic Origins of
  Dictatorship and Democracy*. Cambridge University Press,
  Cambridge. ISBN 978-0-521-85526-6.
  https://doi.org/10.1017/CBO9780511510809
- Aher, G. V., Arriaga, R. I., and Kalai, A. T. (2023). Using large
  language models to simulate multiple humans and replicate human
  subject studies. In *Proceedings of the 40th International Conference
  on Machine Learning (ICML 2023)*, PMLR, 202, 337–371.
  https://proceedings.mlr.press/v202/aher23a.html
- Alesina, A., and Perotti, R. (1996). Income distribution, political
  instability, and investment. *European Economic Review*, 40(6),
  1203–1228. https://doi.org/10.1016/0014-2921(95)00030-5
- Allen, F., and Gale, D. (2000). Financial contagion. *Journal of
  Political Economy*, 108(1), 1–33. https://doi.org/10.1086/262109
- Allport, G. W., and Postman, L. (1947). *The Psychology of Rumor*.
  Henry Holt and Company, New York, xiv+247 pp. (Pre-ISBN
  monograph; reviewed in Zeller 1948, *The Annals of the American
  Academy of Political and Social Science*, 257(1), 145–146,
  https://doi.org/10.1177/000271624825700169.)
- Antonakis, J., Bastardoz, N., Jacquart, P., and Shamir, B. (2016). Charisma: an ill-defined and ill-measured gift. *Annual Review of Organizational Psychology and Organizational Behavior*, 3, 293–319. https://doi.org/10.1146/annurev-orgpsych-041015-062305
- Arendt, H. (1951). *The Origins of Totalitarianism*. Schocken Books,
  New York. Reissued by Harcourt Brace, 1973.
  ISBN 978-0-15-670153-2 (Harcourt 1973 paperback).
- Argyle, L. P., Busby, E. C., Fulda, N., Gubler, J. R., Rytting, C., and
  Wingate, D. (2023). Out of one, many: using language models to simulate
  human samples. *Political Analysis*, 31(3), 337–351.
  https://doi.org/10.1017/pan.2023.2
- Arrow, K. J., Chenery, H. B., Minhas, B. S., and Solow, R. M. (1961).
  Capital-labor substitution and economic efficiency. *The Review of
  Economics and Statistics*, 43(3), 225–250.
  https://doi.org/10.2307/1927286
- Ashraf, Q., and Galor, O. (2011). Dynamics and stagnation in the
  Malthusian epoch. *American Economic Review*, 101(5), 2003–2041.
  https://doi.org/10.1257/aer.101.5.2003
- Asimov, I. (1951). *Foundation*. Gnome Press, New York. (Fix-up
  novel collecting four short stories originally published in
  *Astounding Science-Fiction* between May 1942 and January 1950,
  preceded by a new introductory chapter, "The Psychohistorians",
  written for the Gnome Press edition.)
- Axelrod, R. (1984). *The Evolution of Cooperation*. Basic Books, New
  York. ISBN 978-0-465-02121-5.
- Bartlett, F. C. (1932). *Remembering: A Study in Experimental and
  Social Psychology*. Cambridge University Press, Cambridge.
  (Pre-ISBN monograph; reissued by Cambridge University Press in
  1995 with ISBN 978-0-521-48356-8.)
- Bass, B. M. (1985). *Leadership and Performance Beyond Expectations*.
  Free Press, New York. ISBN 978-0-02-901810-7.
- Baumeister, R. F., Bratslavsky, E., Finkenauer, C., and Vohs, K. D.
  (2001). Bad is stronger than good. *Review of General Psychology*,
  5(4), 323–370. https://doi.org/10.1037/1089-2680.5.4.323
- Becker, G. S. (1991). *A Treatise on the Family*, enlarged edition.
  Harvard University Press, Cambridge, MA. ISBN 978-0-674-90698-3.
- Becker, G. S., and Tomes, N. (1979). An equilibrium theory of the
  distribution of income and intergenerational mobility. *Journal of
  Political Economy*, 87(6), 1153–1189. https://doi.org/10.1086/260831
- Besley, T., and Persson, T. (2011). *Pillars of Prosperity: The
  Political Economics of Development Clusters*. Princeton University
  Press, Princeton, NJ. ISBN 978-0-691-15268-4.
- Blackstone, W. (1765–1769). *Commentaries on the Laws of England*.
  Four volumes. Clarendon Press, Oxford. (Pre-ISBN. Source of the
  lineal-descent rule implemented as `primogeniture` in §4.1.4; the
  collateral-line extension implemented there is not Blackstone's and is
  documented as such.)
- Bonabeau, E. (2002). Agent-based modeling: methods and techniques for
  simulating human systems. *Proceedings of the National Academy of
  Sciences*, 99(Suppl. 3), 7280–7287.
  https://doi.org/10.1073/pnas.082080899
- Braudel, F. (1979). *Civilisation matérielle, économie et capitalisme,
  XVe-XVIIIe siècle*. Three volumes. Armand Colin, Paris. English
  translation (1981–1984), *Civilization and Capitalism, 15th–18th
  Century*, by Siân Reynolds. University of California Press, Berkeley.
- Brown, R., and Kulik, J. (1977). Flashbulb memories. *Cognition*, 5(1),
  73–99. https://doi.org/10.1016/0010-0277(77)90018-X
- Bueno de Mesquita, B., Smith, A., Siverson, R. M., and Morrow, J. D.
  (2003). *The Logic of Political Survival*. MIT Press, Cambridge, MA.
  ISBN 978-0-262-02546-1.
- Cagan, P. (1956). The monetary dynamics of hyperinflation. In M.
  Friedman (ed.), *Studies in the Quantity Theory of Money*. University
  of Chicago Press, Chicago, 25–117.
- Caprara, G. V., Schwartz, S., Capanna, C., Vecchione, M., and
  Barbaranelli, C. (2006). Personality and politics: values, traits,
  and political choice. *Political Psychology*, 27(1), 1–28.
  https://doi.org/10.1111/j.1467-9221.2006.00447.x
- Castelfranchi, C., Conte, R., and Paolucci, M. (1998). Normative
  reputation and the costs of compliance. *Journal of Artificial
  Societies and Social Simulation*, 1(3).
  https://www.jasss.org/1/3/3.html
- Castelfranchi, C., Falcone, R., and Tan, Y.-H. (2001). The role of
  trust and deception in virtual societies. In *Proceedings of the
  34th Annual Hawaii International Conference on System Sciences
  (HICSS-34)*. IEEE. https://doi.org/10.1109/hicss.2001.927042
- Chandler, D. G. (1966). *The Campaigns of Napoleon*. Weidenfeld and
  Nicolson, London, xliii + 1172 pp. (Pre-ISBN trade edition; Macmillan
  reprint 1973, ISBN 978-0-02-523660-8. Source for the per-mode sustained
  travel rates of §4.6.)
- Chandola, T., Coleman, D. A., and Hiorns, R. W. (1999). Recent European
  fertility patterns: fitting curves to "distorted" distributions.
  *Population Studies*, 53(3), 317–329.
  https://doi.org/10.1080/00324720308089
- Chandra, A., Mosher, W. D., Copen, C., and Sionean, C. (2011). Sexual
  behavior, sexual attraction, and sexual identity in the United States:
  data from the 2006–2008 National Survey of Family Growth. *National
  Health Statistics Reports*, 36. National Center for Health Statistics,
  Hyattsville, MD. https://www.cdc.gov/nchs/data/nhsr/nhsr036.pdf
- Chetty, R., Hendren, N., Kline, P., Saez, E., and Turner, N. (2014).
  Is the United States still a land of opportunity? Recent trends in
  intergenerational mobility. *American Economic Review*, 104(5),
  141–147. https://doi.org/10.1257/aer.104.5.141
- Clark, G. (2014). *The Son Also Rises: Surnames and the History of
  Social Mobility*. The Princeton Economic History of the Western World.
  Princeton University Press, Princeton, NJ. ISBN 978-0-691-16254-6.
- Coale, A. J., and Trussell, T. J. (1974). Model fertility schedules:
  variations in the age structure of childbearing in human populations.
  *Population Index*, 40(2), 185–258.
  https://doi.org/10.2307/2733910
- Code civil des Français (1804). Imprimerie de la République, Paris.
  (The Napoleonic Code; source of the equal-division rule implemented as
  `equal_split` in §4.1.4.)
- Collier, N., and North, M. J. (2013). Parallel agent-based simulation
  with Repast for High Performance Computing. *SIMULATION*, 89(10),
  1215–1235. https://doi.org/10.1177/0037549712462620
- Conte, R., and Paolucci, M. (2002). *Reputation in Artificial Societies:
  Social Beliefs for Social Order*. Multiagent Systems, Artificial
  Societies, and Simulated Organizations, vol. 6. Kluwer Academic
  Publishers, Dordrecht. ISBN 978-1-4020-7186-7.
  https://doi.org/10.1007/978-1-4615-1159-5
- Costa, P. T., and McCrae, R. R. (1992). *Revised NEO Personality
  Inventory (NEO PI-R) and NEO Five-Factor Inventory (NEO-FFI)
  Professional Manual*. Psychological Assessment Resources, Odessa, FL.
- Cronin, A. K. (2009). *How Terrorism Ends: Understanding the Decline
  and Demise of Terrorist Campaigns*. Princeton University Press,
  Princeton, NJ. ISBN 978-0-691-13948-7.
- Deaton, A., and Muellbauer, J. (1980). *Economics and Consumer
  Behavior*. Cambridge University Press, Cambridge.
  https://doi.org/10.1017/CBO9780511805653
- Deissenberg, C., van der Hoog, S., and Dawid, H. (2008). EURACE: a
  massively parallel agent-based model of the European economy.
  *Applied Mathematics and Computation*, 204(2), 541–552.
  https://doi.org/10.1016/j.amc.2008.05.116
- Diamond, D. W. (1989). Reputation acquisition in debt markets.
  *Journal of Political Economy*, 97(4), 828–862.
  https://doi.org/10.1086/261630
- Diamond, D. W., and Dybvig, P. H. (1983). Bank runs, deposit insurance,
  and liquidity. *Journal of Political Economy*, 91(3), 401–419.
  https://doi.org/10.1086/261155
- Dunbar, R. I. M. (1992). Neocortex size as a constraint on group size in primates. *Journal of Human Evolution*, 22(6), 469–493. https://doi.org/10.1016/0047-2484(92)90081-J
- Epstein, J. M., and Axtell, R. (1996). *Growing Artificial Societies:
  Social Science from the Bottom Up*. Brookings Institution Press /
  MIT Press, Washington, DC and Cambridge, MA. ISBN 978-0-262-55025-3.
- Evans, G. W., and Honkapohja, S. (2001). *Learning and Expectations
  in Macroeconomics*. Frontiers of Economic Research. Princeton
  University Press, Princeton, NJ. ISBN 978-0-691-04921-2.
- Falconer, D. S., and Mackay, T. F. C. (1996). *Introduction to
  Quantitative Genetics*, 4th edition. Longman, Harlow, xv+464 pp.
  ISBN 978-0-582-24302-6. (Chapter 8: the polygenic additive model and
  the offspring-midparent regression. See §4.1.4, equations (4.46)–(4.48),
  for the documented departure between this source and the
  implementation.)
- Festinger, L., Schachter, S., and Back, K. (1950). *Social Pressures in Informal Groups: A Study of Human Factors in Housing*. Harper and Brothers, New York.
- Finer, S. E. (1962). *The Man on Horseback: The Role of the Military
  in Politics*. Pall Mall Press, London.
  ISBN 978-1-138-52538-7 (Routledge 2017 reissue).
- Fish, M. S. (2002). Islam and authoritarianism. *World Politics*,
  55(1), 4–37. https://doi.org/10.1353/wp.2003.0004
- Fisher, I. (1911). *The Purchasing Power of Money: Its Determination
  and Relation to Credit, Interest and Crises*. Macmillan, New York.
  https://archive.org/details/purchasingpowerm00fishuoft
- Freedom House (2024). *Freedom in the World*. Annual report series.
  Freedom House, Washington, DC.
  https://freedomhouse.org/report/freedom-world
- Gale, D., and Shapley, L. S. (1962). College admissions and the
  stability of marriage. *The American Mathematical Monthly*, 69(1),
  9-15. https://doi.org/10.2307/2312726
- Geddes, B. (1999). What do we know about democratization after twenty
  years? *Annual Review of Political Science*, 2, 115–144.
  https://doi.org/10.1146/annurev.polisci.2.1.115
- Gilbert, D. (2011). *The American Class Structure in an Age of Growing
  Inequality* (8th ed.). Pine Forge Press / SAGE, Thousand Oaks, CA.
  ISBN 978-1-4129-7965-7.
- Gompertz, B. (1825). On the nature of the function expressive of the
  law of human mortality, and on a new mode of determining the value of
  life contingencies. *Philosophical Transactions of the Royal Society
  of London*, 115, 513–583. https://doi.org/10.1098/rstl.1825.0026
- Goode, W. J. (1963). *World Revolution and Family Patterns*. The Free
  Press of Glencoe, New York. (Pre-ISBN monograph; Free Press / Macmillan
  edition, xii+432 pp. Source for the arranged-marriage typology and the
  parent-child asymmetry adopted in §4.1.3.)
- Goody, J. (1976). *Production and Reproduction: A Comparative Study of
  the Domestic Domain*. Cambridge Studies in Social Anthropology, vol. 17.
  Cambridge University Press, Cambridge, xiii+157 pp.
  ISBN 978-0-521-29088-3.
- Gordon, M. J. (1959). Dividends, earnings, and stock prices.
  *The Review of Economics and Statistics*, 41(2), 99–105.
  https://doi.org/10.2307/1927792
- Granovetter, M. S. (1973). The strength of weak ties. *American
  Journal of Sociology*, 78(6), 1360–1380.
  https://doi.org/10.1086/225469
- Graziano, W. G., and Tobin, R. M. (2002). Agreeableness: dimension
  of personality or social desirability artifact? *Journal of
  Personality*, 70(5), 695-728. https://doi.org/10.1111/1467-6494.05021
- Greif, A. (1993). Contract enforceability and economic institutions in
  early trade: the Maghribi traders' coalition. *American Economic
  Review*, 83(3), 525–548. JSTOR 2117532.
- Gualdi, S., Tarzia, M., Zamponi, F., and Bouchaud, J.-P. (2015).
  Tipping points in macroeconomic agent-based models. *Journal of
  Economic Dynamics and Control*, 50, 29–61.
  https://doi.org/10.1016/j.jedc.2014.08.003
- Hackman, J. R. (2002). *Leading Teams: Setting the Stage for Great Performances*. Harvard Business School Press, Boston. ISBN 978-1-57851-333-1.
- Hadwiger, H. (1940). Eine analytische Reproduktionsfunktion für
  biologische Gesamtheiten. *Skandinavisk Aktuarietidskrift*, 1940
  (issues 3–4), 101–113.
  https://doi.org/10.1080/03461238.1940.10404802
- Hajnal, J. (1965). European marriage patterns in perspective. In D. V.
  Glass and D. E. C. Eversley (eds.), *Population in History: Essays in
  Historical Demography*. Edward Arnold, London, 101–143. (Co-edition
  by Aldine Publishing Company, Chicago, 1965; reprint in *Population
  in History*, Routledge, 2017, https://doi.org/10.4324/9781315127019.)
- Hammel, E. A., McDaniel, C. K., and Wachter, K. W. (1979). Demographic
  consequences of incest tabus: a microsimulation analysis. *Science*,
  205(4410), 972–977. https://doi.org/10.1126/science.205.4410.972
- Harris, J. R., and Todaro, M. P. (1970). Migration, unemployment and
  development: a two-sector analysis. *American Economic Review*, 60(1),
  126–142. https://www.jstor.org/stable/1807860
- Heligman, L., and Pollard, J. H. (1980). The age pattern of mortality.
  *Journal of the Institute of Actuaries*, 107(1), 49–80.
  https://doi.org/10.1017/S0020268100040257
- Hobbes, T. (1651/1996). *Leviathan* (R. Tuck, ed.). Cambridge Texts
  in the History of Political Thought. Cambridge University Press,
  Cambridge. ISBN 978-0-521-56797-8 (1996 critical edition of the 1651
  original).
- Homer, S., and Sylla, R. (2005). *A History of Interest Rates*, fourth
  edition. Wiley Finance. John Wiley and Sons, Hoboken, NJ.
  ISBN 978-0-471-73283-9.
- Huckfeldt, R., and Sprague, J. (1987). Networks in context: the
  social flow of political information. *American Political Science
  Review*, 81(4), 1197–1216. https://doi.org/10.2307/1962585
- Human Mortality Database (HMD) (2024). University of California,
  Berkeley (USA) and Max Planck Institute for Demographic Research
  (Germany). https://www.mortality.org
- Iannaccone, L. R. (1992). Sacrifice and stigma: reducing free-riding
  in cults, communes, and other collectives. *Journal of Political
  Economy*, 100(2), 271-291. https://doi.org/10.1086/261818
- ILO, IMF, OECD, UNECE, Eurostat, and World Bank (2004). *Consumer
  Price Index Manual: Theory and Practice*. International Labour
  Office, Geneva. ISBN 92-2-113699-X.
- Jang, K. L., Livesley, W. J., and Vernon, P. A. (1996). Heritability of
  the big five personality dimensions and their facets: a twin study.
  *Journal of Personality*, 64(3), 577–591.
  https://doi.org/10.1111/j.1467-6494.1996.tb00522.x
- Jones, L. E., and Tertilt, M. (2008). An economic history of fertility
  in the United States: 1826-1960. In *Frontiers of Family Economics*
  (Population Economics, vol. 1), 165-230. Emerald Group Publishing.
  https://doi.org/10.1016/S1574-0129(08)00005-7
- Jøsang, A., and Ismail, R. (2002). The beta reputation system. In
  *Proceedings of the 15th Bled Electronic Commerce Conference (Bled
  2002)*, 41–55. https://aisel.aisnet.org/bled2002/41/
- Judge, T. A., Bono, J. E., Ilies, R., and Gerhardt, M. W. (2002). Personality and leadership: a qualitative and quantitative review. *Journal of Applied Psychology*, 87(4), 765–780. https://doi.org/10.1037/0021-9010.87.4.765
- Kahneman, D., and Deaton, A. (2010). High income improves evaluation
  of life but not emotional well-being. *Proceedings of the National
  Academy of Sciences*, 107(38), 16489-16493.
  https://doi.org/10.1073/pnas.1011492107
- Kalmijn, M. (1998). Intermarriage and homogamy: causes, patterns,
  trends. *Annual Review of Sociology*, 24, 395-421.
  https://doi.org/10.1146/annurev.soc.24.1.395
- Kalyvas, S. N. (2006). *The Logic of Violence in Civil War*. Cambridge
  University Press, Cambridge. ISBN 978-0-521-67004-2.
  https://doi.org/10.1017/CBO9780511818462
- Karlan, D. S. (2005). Using experimental economics to measure social
  capital and predict financial decisions. *American Economic Review*,
  95(5), 1688–1699. https://doi.org/10.1257/000282805775014407
- Lee, R. D., and Carter, L. R. (1992). Modeling and forecasting U.S.
  mortality. *Journal of the American Statistical Association*, 87(419),
  659–671. https://doi.org/10.1080/01621459.1992.10475265
- Levitsky, S., and Way, L. A. (2010). *Competitive Authoritarianism:
  Hybrid Regimes after the Cold War*. Cambridge University Press,
  Cambridge. ISBN 978-0-521-70915-5.
- Lewis, P., Perez, E., Piktus, A., Petroni, F., Karpukhin, V., Goyal,
  N., Küttler, H., Lewis, M., Yih, W., Rocktäschel, T., Riedel, S., and
  Kiela, D. (2020). Retrieval-augmented generation for knowledge-intensive
  NLP tasks. In *Advances in Neural Information Processing Systems
  (NeurIPS 2020)*, 33, 9459–9474. Preprint: arXiv:2005.11401.
  https://arxiv.org/abs/2005.11401
- Lewis-Beck, M. S., and Stegmaier, M. (2000). Economic determinants
  of electoral outcomes. *Annual Review of Political Science*, 3,
  183–219. https://doi.org/10.1146/annurev.polisci.3.1.183
- Linz, J. J. (2000). *Totalitarian and Authoritarian Regimes*. Lynne
  Rienner Publishers, Boulder, CO. ISBN 978-1-55587-890-0.
- Lodge, M., Steenbergen, M. R., and Brau, S. (1995). The responsive
  voter: campaign information and the dynamics of candidate evaluation.
  *American Political Science Review*, 89(2), 309–326.
  https://doi.org/10.2307/2082427
- Marshall, M. G., and Gurr, T. R. (2020). *Polity 5: Political Regime
  Characteristics and Transitions, 1800–2018. Dataset Users' Manual*.
  Center for Systemic Peace, Vienna, VA.
  https://www.systemicpeace.org/polityproject.html
- Masad, D., and Kazil, J. (2015). Mesa: an agent-based modeling framework.
  In *Proceedings of the 14th Python in Science Conference (SciPy 2015)*,
  51–58. https://doi.org/10.25080/Majora-7b98e3ed-009
- Mayer, R. C., Davis, J. H., and Schoorman, F. D. (1995). An
  integrative model of organizational trust. *Academy of Management
  Review*, 20(3), 709-734. https://doi.org/10.2307/258792
- McCrae, R. R., and Costa, P. T. (1987). Validation of the five-factor
  model of personality across instruments and observers. *Journal of
  Personality and Social Psychology*, 52(1), 81–90.
  https://doi.org/10.1037/0022-3514.52.1.81
- McCrae, R. R., and Costa, P. T. (2003). *Personality in Adulthood:
  A Five-Factor Theory Perspective* (2nd ed.). Guilford Press, New York.
  ISBN 978-1-57230-827-2.
- Merolla, J. L., and Zechmeister, E. J. (2011). The nature, determinants,
  and consequences of Chávez's charisma: evidence from a study of
  Venezuelan public opinion. *Comparative Political Studies*, 44(1),
  28–54. https://doi.org/10.1177/0010414010381076
- Miller, J. D., and Lynam, D. (2001). Structural models of personality
  and their relation to antisocial behavior: a meta-analytic review.
  *Criminology*, 39(4), 765–798.
  https://doi.org/10.1111/j.1745-9125.2001.tb00940.x
- Mincer, J. (1978). Family migration decisions. *Journal of Political
  Economy*, 86(5), 749–773. https://doi.org/10.1086/260710
- Minsky, H. P. (1986). *Stabilizing an Unstable Economy*. A Twentieth
  Century Fund Report. Yale University Press, New Haven.
  ISBN 978-0-300-03386-1.
- Miyamoto-Mikami, E., Zempo, H., Fuku, N., Kikuchi, N., Miyachi, M., and
  Murakami, H. (2018). Heritability estimates of endurance-related
  phenotypes: a systematic review and meta-analysis. *Scandinavian
  Journal of Medicine & Science in Sports*, 28(3), 834–845.
  https://doi.org/10.1111/sms.12958
- Mokyr, J. (1985). *Why Ireland Starved: A Quantitative and Analytical
  History of the Irish Economy 1800-1850*, second edition. George Allen
  and Unwin, London. ISBN 978-0-04-941011-7.
- Muth, J. F. (1961). Rational expectations and the theory of price
  movements. *Econometrica*, 29(3), 315–335.
  https://doi.org/10.2307/1909635
- Nerlove, M. (1958). Adaptive expectations and cobweb phenomena.
  *Quarterly Journal of Economics*, 72(2), 227–240.
  https://doi.org/10.2307/1880597
- Nichols, R. C. (1978). Twin studies of ability, personality and
  interests. *Homo*, 29, 158–173.
- Nove, A. (1969). *An Economic History of the U.S.S.R.* Allen Lane, The
  Penguin Press, London, 416 pp. ISBN 978-0-7139-0069-9.
- Olson, M. (1965). *The Logic of Collective Action: Public Goods and the
  Theory of Groups*. Harvard Economic Studies, vol. 124. Harvard
  University Press, Cambridge, MA. (Pre-ISBN; revised edition with new
  preface, 1971, ISBN 978-0-674-53751-4.)
- O'Rourke, K. H. (1994). The economic impact of the famine in the short
  and long run. *American Economic Review*, 84(2), 309–313. (Papers and
  Proceedings. Note: the module docstring of
  `epocha/apps/demography/migration.py` records this paper's venue as
  *European Review of Economic History* 1(1), 3–22; that attribution is
  incorrect and the venue above is the one verified for this document.)
- Park, J. S., O'Brien, J. C., Cai, C. J., Morris, M. R., Liang, P., and
  Bernstein, M. S. (2023). Generative agents: interactive simulacra of
  human behavior. In *Proceedings of the 36th Annual ACM Symposium on
  User Interface Software and Technology (UIST '23)*. ACM.
  https://doi.org/10.1145/3586183.3606763
- Piketty, T. (2014). *Capital in the Twenty-First Century*. Translated
  by A. Goldhammer. Belknap Press of Harvard University Press,
  Cambridge, MA. ISBN 978-0-674-43000-6. (Tables 14.1–14.2: top marginal
  estate and inheritance tax rates across France, the United Kingdom,
  the United States and Germany over the twentieth century.)
- Plomin, R., and Deary, I. J. (2015). Genetics and intelligence
  differences: five special findings. *Molecular Psychiatry*, 20(1),
  98–108. https://doi.org/10.1038/mp.2014.105
- Polderman, T. J. C., Benyamin, B., de Leeuw, C. A., Sullivan, P. F.,
  van Bochoven, A., Visscher, P. M., and Posthuma, D. (2015).
  Meta-analysis of the heritability of human traits based on fifty years
  of twin studies. *Nature Genetics*, 47(7), 702–709.
  https://doi.org/10.1038/ng.3285
- Powell, J. M., and Thyne, C. L. (2011). Global instances of coups from
  1950 to 2010: a new dataset. *Journal of Peace Research*, 48(2),
  249–259. https://doi.org/10.1177/0022343310397436
- Powers, D. S. (1986). *Studies in Qur'an and Hadith: The Formation of
  the Islamic Law of Inheritance*. University of California Press,
  Berkeley and Los Angeles, xiii+263 pp. ISBN 978-0-520-05558-2.
- Reimers, N., and Gurevych, I. (2019). Sentence-BERT: sentence embeddings
  using siamese BERT-networks. In *Proceedings of the 2019 Conference on
  Empirical Methods in Natural Language Processing and the 9th International
  Joint Conference on Natural Language Processing (EMNLP-IJCNLP)*, Hong Kong,
  3980–3990. https://doi.org/10.18653/v1/D19-1410
- Reinhart, C. M., and Rogoff, K. S. (2009). *This Time Is Different:
  Eight Centuries of Financial Folly*. Princeton University Press,
  Princeton, NJ. ISBN 978-0-691-14216-6.
- Ricardo, D. (1817). *On the Principles of Political Economy and
  Taxation*. John Murray, London. (Reprinted in Sraffa, P. (ed.),
  *The Works and Correspondence of David Ricardo*, vol. I, Cambridge
  University Press, 1951.)
- Riker, W. H. (1962). *The Theory of Political Coalitions*. Yale
  University Press, New Haven. ISBN 978-0-300-00139-6.
- Rose-Ackerman, S., and Palifka, B. J. (2016). *Corruption and
  Government: Causes, Consequences, and Reform* (2nd ed.). Cambridge
  University Press, Cambridge. ISBN 978-1-107-08120-7.
- Sabater, J., and Sierra, C. (2002). REGRET: reputation in gregarious
  societies. In *Proceedings of the 5th International Conference on
  Autonomous Agents (AGENTS '01)*, 194–195. ACM.
  https://doi.org/10.1145/375735.376110
- Scarf, H. (1960). Some examples of global instability of the
  competitive equilibrium. *International Economic Review*, 1(3),
  157–172. https://doi.org/10.2307/2556215
- Schelling, T. C. (1971). Dynamic models of segregation. *Journal of
  Mathematical Sociology*, 1(2), 143–186.
  https://doi.org/10.1080/0022250X.1971.9989794
- Schmertmann, C. P. (2003). A system of model fertility schedules with
  graphically intuitive parameters. *Demographic Research*, 9, 81–110.
  https://doi.org/10.4054/DemRes.2003.9.5
- Schneider, D. M., and Gough, K. (eds.) (1961). *Matrilineal Kinship*.
  University of California Press, Berkeley and Los Angeles, xx+761 pp.
  (Pre-ISBN monograph.)
- Seppecher, P. (2012). Flexibility of wages and macroeconomic
  instability in an agent-based computational model with endogenous
  money. *Macroeconomic Dynamics*, 16(S2), 284–297.
  https://doi.org/10.1017/S1365100511000447
- Shiller, R. J. (2000). *Irrational Exuberance*. Princeton University
  Press, Princeton, NJ. ISBN 978-0-691-05062-6.
- Shoven, J. B., and Whalley, J. (1992). *Applying General Equilibrium*.
  Cambridge Surveys of Economic Literature. Cambridge University Press,
  Cambridge. ISBN 978-0-521-31986-7.
- Simon, H. A. (1955). A behavioral model of rational choice. *The
  Quarterly Journal of Economics*, 69(1), 99–118.
  https://doi.org/10.2307/1884852
- Solon, G. (1999). Intergenerational mobility in the labor market. In
  O. Ashenfelter and D. Card (eds.), *Handbook of Labor Economics*,
  vol. 3A, ch. 29, 1761–1800. Elsevier, Amsterdam.
  https://doi.org/10.1016/S1573-4463(99)03010-2
- Spielauer, M. (2011). What is social science microsimulation?
  *Social Science Computer Review*, 29(1), 9–20.
  https://doi.org/10.1177/0894439310370085
- Stiglitz, J. E., and Weiss, A. (1981). Credit rationing in markets
  with imperfect information. *American Economic Review*, 71(3),
  393–410. https://www.jstor.org/stable/1802787
- Stogdill, R. M. (1948). Personal factors associated with leadership: a survey of the literature. *Journal of Psychology*, 25(1), 35–71. https://doi.org/10.1080/00223980.1948.9917362
- Tabeau, E., van den Berg Jeths, A., and Heathcote, C. (eds.) (2001).
  *Forecasting Mortality in Developed Countries: Insights from a
  Statistical, Demographic and Epidemiological Perspective*. European
  Studies of Population, vol. 9. Kluwer Academic Publishers, Dordrecht.
  https://doi.org/10.1007/0-306-47562-6
- Thomis, M. A., Beunen, G. P., Maes, H. H., Blimkie, C. J., Van
  Leemputte, M., Claessens, A. L., Marchal, G., Willems, E., and
  Vlietinck, R. F. (1998). Strength training: importance of genetic
  factors. *Medicine & Science in Sports & Exercise*, 30(5), 724–731.
  https://doi.org/10.1097/00005768-199805000-00013
- van Imhoff, E., and Post, W. (1998). Microsimulation methods for
  population projection. *Population: An English Selection*, 10(1),
  97–138. (English-language counterpart of the article in *Population*,
  53(HS1), 97–136, December 1998.)
- Vernon, P. A., Petrides, K. V., Bratko, D., and Schermer, J. A. (2008).
  A behavioral genetic study of trait emotional intelligence. *Emotion*,
  8(5), 635–642. https://doi.org/10.1037/a0013439
- Walras, L. (1874). *Éléments d'économie politique pure, ou théorie de
  la richesse sociale*. L. Corbaz et Cie., Lausanne (part I, 1874;
  part II issued 1877). Definitive (fourth) edition published by
  F. Pichon, Paris, 1900. English translation from the 1926 definitive
  edition by W. Jaffé (1954), *Elements of Pure Economics, or the
  Theory of Social Wealth*. George Allen and Unwin, London, for the
  American Economic Association and the Royal Economic Society.
- Weber, M. (1922/1978). *Economy and Society* (G. Roth and C. Wittich,
  eds. and trans.). University of California Press, Berkeley.
  ISBN 978-0-520-03500-3 (1978 English edition of the original German
  1922 *Wirtschaft und Gesellschaft*).
- Wicksell, K. (1898). *Geldzins und Güterpreise: Eine Studie über
  die den Tauschwert des Geldes bestimmenden Ursachen*. Gustav Fischer,
  Jena. English translation by R. F. Kahn (1936), *Interest and Prices:
  A Study of the Causes Regulating the Value of Money*, with an
  introduction by Bertil Ohlin. Macmillan, London, for the Royal
  Economic Society.
- Wilensky, U. (1999). NetLogo. Center for Connected Learning and
  Computer-Based Modeling, Northwestern University, Evanston, IL.
  http://ccl.northwestern.edu/netlogo/
- Winters, J. A. (2011). *Oligarchy*. Cambridge University Press,
  Cambridge. ISBN 978-1-107-00528-0.
- Wrigley, E. A., and Schofield, R. S. (1981). *The Population History
  of England, 1541-1871: A Reconstruction*. Edward Arnold, London.
  Reissued by Cambridge University Press, 1989. ISBN 978-0-521-35688-6.
- Zempo, H., Miyamoto-Mikami, E., Kikuchi, N., Fuku, N., Miyachi, M., and
  Murakami, H. (2017). Heritability estimates of muscle strength-related
  phenotypes: a systematic review and meta-analysis. *Scandinavian
  Journal of Medicine & Science in Sports*, 27(12), 1537–1546.
  https://doi.org/10.1111/sms.12804
- Zhou, W.-X., Sornette, D., Hill, R. A., and Dunbar, R. I. M. (2005). Discrete hierarchical organization of social group sizes. *Proceedings of the Royal Society B*, 272(1561), 439–444. https://doi.org/10.1098/rspb.2004.2970
- Zietsch, B. P., Kuja-Halkola, R., Walum, H., and Verweij, K. J. H.
  (2014). Perfect genetic correlation between number of offspring and
  grandoffspring in an industrialized human population. *Proceedings of
  the National Academy of Sciences*, 111(3), 1032–1036.
  https://doi.org/10.1073/pnas.1310058111
- Zinn, S. (2013). The MicSim package of R: an entry-level toolkit for
  continuous-time microsimulation. *International Journal of
  Microsimulation*, 7(3), 3–32.
  https://doi.org/10.34196/ijm.00105

---

# 14. Appendices

## Appendix A — Full parameter tables

Appendix A is the canonical consolidated inventory of every parameter
consumed by the audited Methods chapters of §4.1 (demography) and §4.2
(economy behavioral integration). Each row records the parameter name as
declared in the source, its semantic meaning, the admissible range, the
value(s) per era template, the primary-source citation already present in
§13, and the calibration status — `verified` when the value is taken
from a cited primary source, `tunable` when the value is a calibration
heuristic deferred to Plan 4, `heuristic` when the value encodes a
structural bound coded outside the templates. The §4.x inline tables
remain in place as introductory summaries; this appendix is the
authoritative reference for the consolidated view.

**A.1 — Heligman-Pollard mortality (§4.1.1).** The eight HP parameters are
defined per equation (4.1). Admissible ranges match the bounds enforced by
`fit_heligman_pollard()` in `mortality.py:148-149` and are coherent with
the actuarial literature on the HP model; per-era values are the seed
values shipped with the Plan 1 templates and are provisional pending the
Plan 4 fitting campaign against the cited targets. Pre-industrial Christian
and pre-industrial Islamic share identical mortality blocks.

| Parameter | Meaning | Admissible range | Pre-industrial (Christian/Islamic) | Industrial | Modern democracy | Sci-fi | Source | Status |
|---|---|---|---|---|---|---|---|---|
| `A` | Level of mortality at age 1 (childhood component) | `[0, 0.1]` | 0.00491 | 0.00223 | 0.00054 | 0.00002 | Heligman and Pollard (1980) | tunable |
| `B` | Mortality at age 0 relative to age 1 (infancy intercept) | `[0, 0.5]` | 0.017 | 0.022 | 0.017 | 0.017 | Heligman and Pollard (1980) | tunable |
| `C` | Rate of decline of childhood mortality with age | `[0, 1.0]` | 0.102 | 0.115 | 0.125 | 0.125 | Heligman and Pollard (1980) | tunable |
| `D` | Peak amplitude of the young-adult accident hump | `[0, 0.05]` | 0.00080 | 0.00057 | 0.00013 | 0.00001 | Heligman and Pollard (1980) | tunable |
| `E` | Inverse width (sharpness) of the accident hump | `[0.1, 50]` | 9.9 | 10.8 | 18.3 | 18.3 | Heligman and Pollard (1980) | tunable |
| `F` | Age at which the accident hump is centred (years) | `[1.0, 50]` | 22.4 | 25.1 | 19.6 | 19.6 | Heligman and Pollard (1980) | tunable |
| `G` | Senescent mortality at age 0 (Gompertz intercept) | `[0, 0.001]` | 0.0000383 | 0.0000198 | 0.0000123 | 0.0000018 | Heligman and Pollard (1980); Gompertz (1825) | tunable |
| `H` | Rate of exponential increase of senescent mortality with age | `[1.0, 1.5]` | 1.101 | 1.104 | 1.101 | 1.089 | Heligman and Pollard (1980); Gompertz (1825) | tunable |

Calibration targets per template: pre-industrial pair against Wrigley and
Schofield (1981) tables A3.1-A3.3 (England 1700-1749); industrial against
HMD England and Wales pooled life tables 1841-1900; modern democracy
against HMD USA life table 2019 (pre-COVID baseline); sci-fi as
speculative extrapolation with no empirical basis (`sci_fi.json`).

**A.2 — Hadwiger fertility schedule and ceiling (§4.1.2).** The three
Hadwiger parameters are defined per equation (4.2); the Malthusian soft
ceiling parameters of equation (4.4) carry the same per-template
specification.

| Parameter | Meaning | Admissible range | Pre-industrial (Christian/Islamic) | Industrial | Modern democracy | Sci-fi | Source | Status |
|---|---|---|---|---|---|---|---|---|
| `H` | Target Total Fertility Rate (integral of `f_HW` over fertile window) | `[0, ~10]` | 5.0 | 4.0 | 1.8 | 2.1 | Hadwiger (1940); Wrigley and Schofield (1981) | tunable |
| `R` | Peak-fertility shape parameter | `[15, 40]` | 26 | 27 | 30 | 32 | Hadwiger (1940); Chandola, Coleman and Hiorns (1999) | tunable |
| `T` | Spread of the age-specific fertility distribution | `[1, 10]` | 3.5 | 3.8 | 4.2 | 4.0 | Hadwiger (1940); Chandola, Coleman and Hiorns (1999) | tunable |
| `max_population` | Population cap for the Malthusian ceiling | structural | 500 | 500 | 500 | 500 | Engineering constraint (per-tick budget); Ashraf and Galor (2011) | heuristic |
| `malthusian_floor_ratio` (`ρ`) | Floor multiplier on per-tick birth probability above the cap | `[0, 1]` | 0.10 | 0.05 | 0.01 | 0.00 | Engineering heuristic; Ashraf and Galor (2011) qualitative shape | heuristic |

**A.3 — Becker fertility-modulation coefficients (§4.1.2, equation 4.3).**
The five coefficients are seeded with identical values across all five
demography templates pending Plan 4 calibration; tracked as audit debt
B2-07.

| Coefficient | Meaning | Seed value (all templates) | Admissible range | Source | Status |
|---|---|---:|---|---|---|
| `β₀` | Baseline log-shift on the modulation factor | 0.0 | unbounded | Inspired by Becker (1991); Epocha implementation choice | tunable |
| `β₁` | Elasticity to log-wealth relative to subsistence | 0.10 | sign positive | Inspired by Becker (1991) | tunable |
| `β₂` | Penalty per unit of parental education | −0.05 | sign negative | Inspired by Becker (1991) | tunable |
| `β₃` | Penalty per unit of zone female labour-force participation | −0.10 | sign negative | Inspired by Becker (1991) | tunable |
| `β₄` | Elasticity to aggregate macro-outlook signal | 0.20 | sign positive | Epocha extension; outlook computed in `context.compute_aggregate_outlook()` | tunable |
| modulation clip | Output bound on `m_BK` after exponentiation | `[0.05, 3.0]` | structural | Implementation guard against degenerate inputs | heuristic |

**A.4 — Maternal mortality at childbirth (§4.1.2, joint resolver).** The
two coefficients consumed by `resolve_childbirth_event()` are template
fields under `mortality.maternal_mortality_rate_per_birth` and
`mortality.neonatal_survival_when_mother_dies`; values reflect the
historical-target ranges discussed in the demography spec.

| Parameter | Meaning | Pre-industrial (Christian/Islamic) | Industrial | Modern democracy | Sci-fi | Source | Status |
|---|---|---:|---:|---:|---:|---|---|
| `maternal_mortality_rate_per_birth` | Probability of maternal death per live birth | 0.012 | 0.005 | 0.0001 | 0.00001 | Demography spec (per-template seed); calibration pending Plan 4 | tunable |
| `neonatal_survival_when_mother_dies` | Probability the newborn survives when the mother dies in childbirth | 0.30 | 0.50 | 0.95 | 0.99 | Demography spec (per-template seed); calibration pending Plan 4 | tunable |

**A.5 — Couple-formation parameters (§4.1.3).** Per-template values for
the runtime resolver and for the Kalmijn (1998) homogamy weights of
equation (4.6).

| Parameter | Meaning | Pre-industrial Christian | Pre-industrial Islamic | Industrial | Modern democracy | Sci-fi | Source | Status |
|---|---|---|---|---|---|---|---|---|
| `marriage_market_type` | `autonomous` vs `arranged` (parent-mediated under Goode 1963 Pass B) | `autonomous` | `arranged` | `autonomous` | `autonomous` | `autonomous` | Goode (1963); demography spec | tunable |
| `divorce_enabled` | Gates `resolve_separate_intents()` | false | true | true | true | true | Demography spec; Catholic-marriage indissolubility for Christian template | tunable |
| `implicit_mutual_consent` | One-sided declaration suffices when true | true | true | true | true | true | Demography spec | tunable |
| `min_age` (M / F) | Minimum age for the eligibility check (years) | 16 / 14 | 16 / 14 | 18 / 16 | 18 / 18 | 18 / 18 | Demography spec; historical-attestation order of magnitude | tunable |
| `mourning_ticks` | Cooldown after partner's death (loaded but not yet consumed) | 365 | 365 | 180 | 90 | 30 | Demography spec | tunable |
| `marriage_market_radius` | Spatial scope of candidate pool | `same_zone` | `same_zone` | `adjacent_zones` | `world` | `world` | Demography spec; spatial structure inherited from §3.6 | tunable |
| `w_class` | Class similarity weight in equation (4.6) | 0.40 | 0.40 | 0.35 | 0.20 | 0.10 | Kalmijn (1998); per-era cultural-salience calibration | tunable |
| `w_edu` | Education proximity weight | 0.25 | 0.25 | 0.30 | 0.40 | 0.30 | Kalmijn (1998) | tunable |
| `w_age` | Age proximity weight | 0.20 | 0.20 | 0.20 | 0.20 | 0.20 | Kalmijn (1998) | tunable |
| `w_rel` | Existing relational sentiment weight | 0.15 | 0.15 | 0.15 | 0.20 | 0.40 | Kalmijn (1998); Epocha extension via `Relationship.sentiment` | tunable |
| `age_tolerance_years` (`τ`) | Decay scale of the exponential age kernel (function argument) | 10.0 | 10.0 | 10.0 | 10.0 | 10.0 | Demographic-literature order of magnitude; promotion to per-template field reserved for Plan 4 | heuristic |

**A.6 — Adaptive-expectations parameters (§4.2.1).** The expectations
config block is populated by `_behavioral_config()` in
`template_loader.py:179-196` and is identical across all four economy
templates pending Plan 4 calibration. Structural bounds are coded as
module constants in `expectations.py:39-40`.

| Parameter | Meaning | Seed value (all economy templates) | Admissible range | Source | Status |
|---|---|---:|---|---|---|
| `lambda_base` | Baseline adaptation rate before personality modulation | 0.30 | `(0, 1)` | Cagan (1956); Nerlove (1958) | tunable |
| `neuroticism_mod` | Magnitude of positive Neuroticism contribution to per-agent `λ` | 0.15 | `≥ 0` | Costa and McCrae (1992); Epocha extension | tunable |
| `openness_mod` | Magnitude of positive Openness contribution to per-agent `λ` | 0.10 | `≥ 0` | Costa and McCrae (1992); Epocha extension | tunable |
| `conscientiousness_mod` | Magnitude of negative Conscientiousness contribution to per-agent `λ` | 0.10 | `≥ 0` | Costa and McCrae (1992); Epocha extension | tunable |
| `trend_threshold` | Fractional deviation from `expected_price` required to change `trend_direction` | 0.05 | `(0, 1)` | Epocha design choice; tunable | tunable |
| `_LAMBDA_MIN` (structural) | Lower bound on per-agent `λ` after equation (4.10) | 0.05 | structural | Implementation guard against static forecast | heuristic |
| `_LAMBDA_MAX` (structural) | Upper bound on per-agent `λ` after equation (4.10) | 0.95 | structural | Implementation guard against naive expectation | heuristic |
| confidence step | Per-tick increment/decrement on `AgentExpectation.confidence` | ±0.05 | `(0, 1)` | Epocha design choice; tunable | tunable |

**A.7 — Credit and banking, per-era (§4.2.2).** The four economy templates
shipped with the economy app — pre-industrial, industrial, modern, sci-fi —
carry differentiated `credit_config` and `banking_config` blocks
calibrated qualitatively against Homer and Sylla (2005) and the Basel III
reserve-ratio convention.

| Parameter | Meaning | Pre-industrial | Industrial | Modern | Sci-fi | Source | Status |
|---|---|---:|---:|---:|---:|---|---|
| `loan_to_value` | Maximum loan-to-collateral-value ratio in (4.12) | 0.50 | 0.60 | 0.80 | 0.90 | Stiglitz and Weiss (1981); Homer and Sylla (2005) qualitative ranges | tunable |
| `base_interest_rate` | Initial base rate before Wicksellian adjustment | 0.08 | 0.06 | 0.03 | 0.02 | Homer and Sylla (2005); Wicksell (1898) for the adjustment law | tunable |
| `initial_deposits` | Banking-system seed deposits in primary-currency units | 5 000 | 20 000 | 100 000 | 500 000 | Engineering seed scaled by era money supply | tunable |
| `reserve_ratio` | Required reserve ratio (Basel III convention for modern) | 0.10 | 0.10 | 0.05 | 0.03 | Basel III; Diamond and Dybvig (1983) | tunable |

**A.8 — Credit and banking, structural and uniform (§4.2.2).** Parameters
that are uniform across all four templates pending Plan 4 calibration, or
that are coded as module-level constants because they encode the
qualitative shape of the bank-run dynamic rather than calibration choices.

| Parameter | Meaning | Value | Where coded | Source | Status |
|---|---|---:|---|---|---|
| `risk_premium` | Coefficient on the borrower-leverage spread in (4.13) | 0.50 | `credit.py:215-219`; `credit_config.risk_premium` | Stiglitz and Weiss (1981) qualitative; magnitude is Epocha design | tunable |
| `max_rollover` | Maximum number of times a maturing loan may be rolled over | 3 | `credit_config.max_rollover` | Minsky (1986) qualitative; magnitude is Epocha design | tunable |
| `default_loan_duration_ticks` | Default loan duration when caller passes none | 20 | `credit_config.default_loan_duration_ticks` | Epocha design choice | tunable |
| `_CONCERN_CONFIDENCE_THRESHOLD` | Threshold of (4.11) below which banking-concern memories are broadcast | 0.50 | `banking.py:334` | Diamond and Dybvig (1983) qualitative; threshold is Epocha design | heuristic |
| `_CONCERN_BROADCAST_RATIO` | Fraction of living population that receives the per-tick concern broadcast | 0.50 | `banking.py:329` | Engineering choice for memory-write budget | heuristic |
| `_CONCERN_DEDUP_TICKS` | Deduplication window aligned to agent-engine memory dedup | 3 | `banking.py:325` | Engineering choice; aligned with `simulation/engine.py` constant | heuristic |
| `CASCADE_LOSS_THRESHOLD` | Fraction of lender wealth above which a default loss propagates | 0.50 | `credit.py:54` | Allen and Gale (2000) qualitative | heuristic |
| cascade `max_depth` | BFS cap on default-cascade propagation | 3 | `process_default_cascade()` argument | Allen and Gale (2000) empirical-network diameter (3-5 links) | heuristic |
| rollover repricing factor | Per-rollover interest-rate multiplier | 1.10 | `credit.py:636` | Epocha design choice; deferred refinement under §4.2.2 | tunable |
| solvency confidence step | `confidence_index` decrement per tick of insolvency | −0.10 | `banking.py` `check_solvency()` | Epocha design; trust-asymmetry observation | heuristic |
| solvency recovery step | `confidence_index` increment per tick of recovery | +0.05 | `banking.py` `check_solvency()` | Epocha design; trust-asymmetry observation | heuristic |
| base-rate clamp | Lower and upper clamp on `base_interest_rate` after Wicksellian adjustment | `[0.005, 0.50]` | `banking.py:115-206` | Implementation guard | heuristic |

**A.9 — Property market (§4.2.3).** No standalone era-template config
block; values are inherited from the credit and expectations configs and
two property-market design parameters are coded outside the templates.

| Parameter | Meaning | Value | Where coded | Source | Status |
|---|---|---:|---|---|---|
| `trend_threshold` | Fractional deviation classifying asking price as rising/falling/stable | 0.05 | inherited from `expectations_config.trend_threshold` | Audit fix C-5 of 2026-04-15 convergence | tunable |
| `listing_expiration_ticks` | Stale listings withdrawn after this many ticks | 10 | `property_market.py:235` | Epocha design choice; multi-period market timescale | heuristic |
| Gordon denominator floor | Floor on `(r − g)` in `V = R / (r − g)` to prevent division by zero | 0.01 | `property_market.py:121-128` | Implementation guard against `r ≈ g` | heuristic |
| Gordon valuation lower clip | Lower bound on `fundamental_value` as multiple of `property.value` | 0.1× | `property_market.py:121-128` | Implementation guard against transient rent collapses | heuristic |
| Gordon valuation upper clip | Upper bound on `fundamental_value` as multiple of `property.value` | 10× | `property_market.py:121-128` | Implementation guard; binding constraint on bubble magnitude per spec audit log | heuristic |

## Appendix B — Reproducibility

Appendix B records the operational steps by which any result reported in
this whitepaper that depends only on the seeded non-LLM part can be
regenerated from a clean checkout; results that depend on LLM agent
decisions or world generation are not seed-reproducible and can be
re-observed but not regenerated identically. The reference
that pins the codebase state for the present revision is the value of the
`frozen-at-commit` field in the front matter, populated at merge time
under phase 7 of the canonical workflow; running on a different commit
will produce results that may differ in numeric detail even when the
qualitative behavior is preserved.

**Repository.** The canonical source is
https://github.com/mauriziomocci/epocha, mirrored to no other public
location. The `develop` branch carries the integration of work that has
passed all gates of the canonical seven-phase workflow and the periodic
memory-backup sync described in the project CLAUDE.md; the `main` branch
is reserved for releases.

**Pinned commit.** The value of the `frozen-at-commit` field at the top
of this document — currently `1cdcfa4fe23138727c16a2e92234e4eb962d9ae7` and resolved at merge to
the SHA of the integrating commit — is the canonical reproduction
reference. The same placeholder appears on each `Status` header in §4 and
is filled atomically at phase 7 closure.

**Runtime environment.** Python 3.12 with the dependency set pinned in
`requirements/base.txt` (production-baseline transitive set),
`requirements/local.txt` (development extensions including pytest and
debug tooling), and `requirements/production.txt` (production overrides).
Direct PostgreSQL with PostGIS extension is required for the spatial
fields enabled in `world.0003_zone_postgis_geometry`; Redis is required
for Celery broker and the LLM rate limiter; the Docker compose file
`docker-compose.local.yml` packages Postgres+PostGIS, Redis, the Django
application, the Celery worker, and the Celery beat scheduler with the
correct service wiring.

**Bringing up the stack from a clean checkout.**

```bash
git clone https://github.com/mauriziomocci/epocha.git
cd epocha
git checkout <frozen-at-commit>
docker compose -f docker-compose.local.yml up --build
```

The first invocation builds the application image and runs the migration
trail under `epocha/apps/<app>/migrations/`, applied linearly without
squashing per the project rule. The dashboard is exposed at the host port
declared in the compose file; LLM-provider credentials must be configured
through the `EPOCHA_LLM_BASE_URL`, `EPOCHA_LLM_MODEL`, and
`EPOCHA_LLM_API_KEY` settings of `config/settings/base.py` (and the
`EPOCHA_CHAT_LLM_*` parallel for the chat-side provider) before the agent
decision pipeline of §3.2 can dispatch a tick.

**Test invocation.**

```bash
docker compose -f docker-compose.local.yml exec web \
    pytest --cov=epocha -v
```

The full suite covers the audited modules of §4.1 and §4.2 at the
algorithm level, the cross-module integration paths exercised by
`epocha/apps/economy/engine.py:process_economy_tick_new()`, and the
Django-level model and serializer machinery of every app under
`epocha/apps/`. Per-module subsets are addressable by directory path:
`pytest epocha/apps/demography/ -v` for the §4.1 modules,
`pytest epocha/apps/economy/ -v` for the §4.2 modules.

**Seeded RNG.** Per §3.4, every stochastic decision in the demography
subsystem draws from a per-stream seeded `random.Random` returned by
`epocha.apps.demography.rng.get_seeded_rng(simulation, tick, phase)`,
where `phase` is one of the closed set `mortality`, `fertility`,
`couple`, `migration`, `inheritance`, `initialization`. The seed is
derived as the first eight bytes of
`sha256(f"{simulation.id}:{simulation.seed}:{tick}:{phase}")`, so two
runs with the same `simulation.id`, `simulation.seed`, and code revision
produce identical per-tick draws across the lifetime of the simulation.
Reordering or suppressing one subsystem in a refactor does not shift the
random sequence the others see at the same tick, which is the property
that makes refactor-stable reproducibility possible. The known debt A-5
documented in §3.4 — a fallback to `0` when both `simulation.seed` and
`simulation.id` are `None` — is rare in practice and tracked for Plan 4.

**Era template loading.** Per Appendix C, the demography templates are
five JSON files under `epocha/apps/demography/templates/` and the
economy templates are four Python factory functions in
`epocha/apps/economy/template_loader.py`. The demography loader
(`template_loader.py`) validates each JSON file against the implicit
schema defined by the consumers in §4.1 — every key is consumed by a
specific model and unknown keys raise a validation error rather than
being silently ignored. The economy factories return a nested dictionary
that the loader passes to `EconomyTemplate.objects.get_or_create()`; the
behavioral block is built once by `_behavioral_config()` and is identical
across all four templates pending Plan 4 calibration. To run a simulation
under a specific era template, set the corresponding `Simulation.config`
fields (`demography_template`, `economy_template`) at simulation creation
through the dashboard or the management API.

**Validation experiments.** The methodology of Chapter 7 specifies the
target datasets (§7.1), comparison metrics (§7.2), and acceptance
thresholds (§7.3); the experimental campaign that consumes them is
tracked under `docs/memory-backup/project_validation_experiments_pending.md`
and is bound to demography Plan 4. The Plan 4 deliverable will introduce
a `validation/` directory at the repository root with one Python script
per audited module and a Makefile target that runs the entire campaign
under a single command on a clean checkout.

## Appendix C — Era templates JSON schema and source

The simulation supports two parallel template systems whose existence is
documented in §6.2. Appendix C describes the on-disk shape of each system
without inflating the document with the full JSON content; the
authoritative payloads live in the source tree at the paths recorded
below.

**C.1 — Demography templates (JSON, five files).** Each file under
`epocha/apps/demography/templates/` carries a flat dictionary with three
top-level blocks (`mortality`, `fertility`, `couple`) consumed by the
audited models of §4.1. The implicit schema is narrow: every key is
consumed by a specific function in `mortality.py`, `fertility.py`, or
`couple.py`, and unknown keys at load time raise a validation error
rather than being silently ignored.

The `mortality` block carries the eight Heligman-Pollard parameters
defined per equation (4.1) plus the maternal-mortality coefficients
consumed by the joint resolver of §4.1.2:

- `A`, `B`, `C` — childhood-decline parameters of equation (4.1)
- `D`, `E`, `F` — accident-hump parameters
- `G`, `H` — Gompertz senescent-rise parameters
- `maternal_mortality_rate_per_birth` — probability of maternal death per
  live birth
- `neonatal_survival_when_mother_dies` — probability the newborn
  survives when the mother dies in childbirth

The `fertility` block carries the three Hadwiger parameters of equation
(4.2), the five Becker modulation coefficients of equation (4.3), and
the Malthusian-ceiling parameters of equation (4.4):

- `H`, `R`, `T` — Hadwiger schedule of equation (4.2)
- `becker_beta_0` through `becker_beta_4` — Becker coefficients
- `malthusian_floor_ratio` (`ρ`) — soft-ceiling floor multiplier
- `max_population` — Malthusian-ceiling cap

The `couple` block carries the runtime-resolver fields and the Kalmijn
homogamy weights of equation (4.6):

- `marriage_market_type` — `autonomous` or `arranged`
- `divorce_enabled` — gates `resolve_separate_intents()`
- `implicit_mutual_consent` — one-sided declaration suffices when true
- `min_age_male`, `min_age_female` — eligibility minimums in years
- `mourning_ticks` — cooldown after partner's death (loaded but not yet
  consumed)
- `marriage_market_radius` — `same_zone`, `adjacent_zones`, or `world`
- `homogamy_weights` — sub-block carrying `w_class`, `w_edu`, `w_age`,
  `w_rel` summing to one
- `allowed_types`, `default_type` — couple typology

The five files shipped with Plan 1 are summarised in Table C.1.

Table C.1 — Demography templates shipped with Plan 1.

| Template name | File path | Era scope |
|---|---|---|
| `pre_industrial_christian` | `epocha/apps/demography/templates/pre_industrial_christian.json` | Pre-industrial Western Christendom; calibration target Wrigley and Schofield (1981) England 1700-1749; carries Catholic-marriage indissolubility (`divorce_enabled: false`); identical mortality and fertility blocks to `pre_industrial_islamic`, differs only in the couple block |
| `pre_industrial_islamic` | `epocha/apps/demography/templates/pre_industrial_islamic.json` | Pre-industrial Islamic world; same biological schedules as `pre_industrial_christian`; carries arranged-marriage regime (`marriage_market_type: arranged`) under Goode (1963) Pass B semantics |
| `industrial` | `epocha/apps/demography/templates/industrial.json` | Industrial transition; calibration target HMD England and Wales pooled 1841-1900; broadened marriage-market radius to `adjacent_zones` reflecting urbanisation |
| `modern_democracy` | `epocha/apps/demography/templates/modern_democracy.json` | Modern liberal democracy; calibration target HMD USA 2019 (pre-COVID baseline); marriage-market radius `world` reflecting modern mobility |
| `sci_fi` | `epocha/apps/demography/templates/sci_fi.json` | Speculative far-future template; no empirical calibration target; documented inline in the source as speculative |

**C.2 — Economy templates (Python factories, four functions).** Each
factory under `epocha/apps/economy/template_loader.py` returns a nested
dictionary that the loader passes to
`EconomyTemplate.objects.get_or_create()`. The factory pattern was chosen
over per-template JSON files on the grounds that the per-era
differentiation reduces to a small set of inputs (currency table, goods
elasticities, factor stocks, behavioral configuration) and the Python
factory exposes those inputs as named arguments more legibly than four
parallel JSON files would. The behavioral block is built once by
`_behavioral_config()` and is identical across all four templates pending
Plan 4 calibration.

Table C.2 — Economy templates shipped with the economy app.

| Template name | Factory function | Scope |
|---|---|---|
| `pre_industrial` | `_pre_industrial_template()` (`epocha/apps/economy/template_loader.py`) | Pre-industrial agrarian economy; carries the canonical farmland-workshop-shop property typology, low loan-to-value of 0.50, base interest rate 0.08 calibrated against Homer and Sylla (2005) for the pre-modern range |
| `industrial` | `_industrial_template()` | Industrial transition; adds the factory property type at base value 500; loan-to-value 0.60; base interest rate 0.06 |
| `modern` | `_modern_template()` | Modern central-bank-anchored economy; adds the office property type at base value 300; loan-to-value 0.80; base interest rate 0.03; reserve ratio 0.05 calibrated against the Basel III convention |
| `sci_fi` | `_sci_fi_template()` | Speculative far-future template; adds automated factory at base value 1 000 and research lab at base value 800; loan-to-value 0.90; base interest rate 0.02; reserve ratio 0.03 |

The `_behavioral_config()` shared block at `template_loader.py:144-198`
populates the `expectations_config`, `credit_config`, and `banking_config`
sub-blocks consumed by the audited modules of §4.2. The per-era
differentiation of `λ_base`, the Becker modulation coefficients,
`risk_premium`, `max_rollover`, and `default_loan_duration_ticks` is the
explicit calibration debt assigned to Plan 4. The discrepancy in count
between five demography templates and four economy templates is
documented in §6.2: the demography spec required separating the two
pre-industrial confessional regimes to support the marriage-market and
divorce-regime distinction, while the economy spec found no analogous
structural distinction at the price-and-credit layer.

**C.3 — Loading and validation.** Both template systems are loaded at
simulation creation time through `template_loader.py` modules in their
respective apps. The demography loader validates the JSON against the
implicit schema by attempting to construct each model's parameter object
and rejecting the load with a descriptive `ValueError` when any required
field is missing or any value falls outside the admissible range
documented in Appendix A. The economy loader performs the same role for
the Python-factory output, with the difference that the factory itself
controls the produced dictionary and a malformed factory output indicates
a bug in the factory rather than a corrupted JSON file. The strict
validation discipline is the property that makes the per-era
differentiation auditable: a typo in a template field is caught at
simulation creation rather than producing silently incorrect per-tick
behavior downstream.

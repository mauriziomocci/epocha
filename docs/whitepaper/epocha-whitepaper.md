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
1940), because per-tick reproducibility is the contract the validation
suite of Chapter 7 depends on, and because chord-based parallelism scales
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
| Treasury credit | `add_to_treasury(government, currency_code, amount)` in `epocha/apps/world/government.py` | Adds `amount` of `currency_code` to `government.government_treasury` (a JSON map from currency code to balance) and persists the row. | Called from `epocha/apps/economy/engine.py` (taxation) and from inheritance/estate-tax logic in the demography subsystem; implemented in `world/government.py`. |
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
`simulation.seed`, and the initial state of the database, every tick of a
run is deterministic and reproducible across machines. One known debt is
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

This subsystem is documented in this chapter rather than in §4 Methods
because it has not yet completed a Round 2 adversarial scientific
audit. The literature pointers above are descriptive of the families
of models implemented and of the source citations recorded inside the
modules themselves, not assertions of Methods-grade verified fidelity:
several constants are explicitly tagged as tunable design parameters
in the source (the tâtonnement adjustment rate, the maximum price
ratio, the discretionary demand cap, the mood satiation thresholds,
the default cascade depth) and their numerical values do not yet have
the line-by-line citation chain required for the §4 status. The
audited layer that sits on top of this substrate is the behavioral
integration described in §4.2: that integration consumes the prices,
trades, and income flows produced by the substrate and adds the
adaptive expectations, satisficing, and political feedback that have
passed Round 2.

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

> Status: implemented as of commit `<filled-on-merge>`, spec audit CONVERGED 2026-04-18 round 4.

The demography module covers the three life-course transitions for which Epocha currently runs an audited scientific model: mortality, fertility, and couple formation. The authoritative specification is `docs/superpowers/specs/2026-04-18-demography-design.md`, whose four rounds of adversarial review converged on 2026-04-18; the design choices and the explicit mapping of every parameter to a primary source live there, while this chapter restates the formulas, the calibration tables, and the per-tick algorithms in publication form. The implementation lives under `epocha/apps/demography/`, where the three subsystems are split into `mortality.py`, `fertility.py`, and `couple.py`, with shared concerns factored into `template_loader.py` (era JSON loading and validation), `rng.py` (seeded per-phase streams discussed in Chapter 3.4), `context.py` (integration helpers towards the economy), and `models.py` (the persisted demographic state). The design intent is that within each tick the three subsystems run in the order mortality → fertility → couple formation, each drawing from its own seeded RNG stream so that the order can be reasoned about without coupling to the random sequence; maternal mortality at childbirth is the one inter-subsystem coupling and is resolved jointly between mortality and fertility before either records its outcome, as detailed in §4.1.2. As of the commit pinned in the front matter, the mortality and fertility models and the couple infrastructure are implemented and unit-tested in isolation; their orchestration into the live simulation tick loop in `epocha/apps/simulation/engine.py` is tracked as a Plan 4 deliverable (Initialization, Engine integration, and Historical validation) and is not yet active in production code.

### 4.1.1 Mortality model (Heligman-Pollard)

> Status: implemented as of commit `<filled-on-merge>`, spec audit CONVERGED 2026-04-18 round 4.

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

> Status: implemented as of commit `<filled-on-merge>`, spec audit CONVERGED 2026-04-18 round 4.

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

**Algorithm.** For each living female agent in the fertile window `[12, 50]`, on every tick, the fertility module first checks the gating preconditions in `tick_birth_probability()` (lines 180–191): if the era template requires couple membership and the mother is not in an active couple (`is_in_active_couple()`), or if the `avoid_conception` flag on `AgentFertilityState` was set at tick `T−1` (`is_avoid_conception_active_this_tick()`, line 262), the function returns 0 and no birth can fire this tick. Otherwise the three layers are evaluated in sequence: `hadwiger_asfr()` is called at the agent's age in years (computed in `_effective_age_in_years()` from `birth_tick` and the authoritative `current_tick` to avoid the FK-cache staleness flagged in audit finding B2-04), the result is multiplied by `becker_modulation()` evaluated against the agent's wealth, education, zone, and outlook, the product is passed through `malthusian_soft_ceiling()` against the current population and `max_population`, and the resulting annual rate is multiplied by `Δt` to give the per-tick probability. The caller draws a uniform variate from a `random.Random` returned by `epocha.apps.demography.rng.get_seeded_rng(simulation, tick, phase="fertility")` — the same seeded-stream contract documented for mortality in §4.1.1, with `phase="fertility"` selected from the closed phase set so the fertility draw never shifts the random sequence the mortality draw at the same tick has consumed. When a birth fires and maternal mortality applies, the spec §1 C-1 fix requires the two events to be resolved jointly rather than sequentially: `resolve_childbirth_event(mother, params_era, tick, rng)` (`fertility.py:295`) draws against `mortality.maternal_mortality_rate_per_birth` for the maternal-death event and, conditional on the mother dying, against `mortality.neonatal_survival_when_mother_dies` for the newborn's survival; the helper is a pure probabilistic resolver and returns a dict `{mother_died, newborn_survived, death_cause}` with `death_cause = "childbirth"` when maternal death is selected, leaving persistence (mother's death record, newborn creation) to the caller. The joint resolution avoids the bias that would arise from resolving generic mortality first and childbirth mortality second on the same mother in the same tick. As of the pinned commit, this per-tick fertility evaluation is exercised by the demography unit-test suite (`epocha/apps/demography/tests/test_fertility.py`) but is not yet invoked from `epocha/apps/simulation/engine.py` or `tasks.py`; the only mention of `tick_birth_probability` outside `demography/` is a comment in `engine.py:276` describing the gating semantics of the `avoid_conception` flag. The integration into the live tick loop is tracked, alongside the equivalent mortality gap noted in §4.1.1, as a Plan 4 deliverable (Initialization, Engine integration, and Historical validation).

**Simplifications.** The current implementation deliberately omits four refinements that the demographic literature treats as proper extensions rather than corrections of the baseline schedule. First, the Hadwiger age-specific schedule is evaluated deterministically at the agent's age, with no inter-individual heterogeneity in the underlying biological fecundity beyond the binary flags carried by `AgentFertilityState`; modeling lognormal heterogeneity in time-to-conception (the proximate-determinants literature reviewed in the demography spec) is deferred. Second, twin and higher-order multiple births are not modeled: each successful birth event creates exactly one newborn, regardless of historical multiple-birth rates that range from roughly 1% in pre-industrial Europe to over 3% in some modern populations. Third, the Becker modulation coefficients are homogeneous across all five era templates, as documented in Table 4.4 and tracked as audit debt B2-07; per-era calibration is the central deliverable of Plan 4 and will replace the seed values with era-specific estimates from synthetic shock tests against the Wrigley and Schofield (1981) baseline and the additional fertility-decline references catalogued in the demography spec. Fourth, the Malthusian soft ceiling is an engineering heuristic rather than a literal implementation of the Ashraf and Galor (2011) preventive-check formalism, which operates in continuous time on income per capita; the Epocha ceiling is a discrete tick-based scaling on the per-mother birth probability that preserves the qualitative shape of the preventive check (free below 80% of cap, ramp to zero between 80% and 100%, floor above the cap) without claiming to reproduce the Ashraf-Galor income dynamics. The choice is documented in the `malthusian_soft_ceiling()` docstring (`fertility.py:118–145`) and is consistent with the design intent of giving the simulation a population-density feedback that protects the per-tick computational budget while remaining interpretable in Malthusian terms.

### 4.1.3 Couple formation and dissolution (Gale-Shapley + Goode 1963)

> Status: implemented as of commit `<filled-on-merge>`, spec audit CONVERGED 2026-04-18 round 4.

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

The `age_tolerance_years` parameter `τ` of equation (4.6) is held at the default value `10.0` across all templates, as a function argument to `homogamy_score()` rather than a per-template field; lifting it into the template schema is documented as a Plan 4 calibration deliverable.

**Algorithm.** Three coordinated operations make up the couple lifecycle. At initialization, the founder-population builder calls `stable_matching(proposers, respondents, score_fn)` once with `score_fn = lambda p, r: homogamy_score(p, r, era_weights)` and the eligible adult subpopulations as the two sides; each returned `(p, r)` pair is then routed through `form_couple()` to materialize the database row with the canonical-ordering invariant enforced. At runtime, the demography step calls `resolve_pair_bond_intents(simulation, tick, rng)` once per tick, which reads `DecisionLog` entries authored at tick `T-1` with the SQL `__contains` pre-filter `'"pair_bond"'` and verifies each match by `json.loads()`, runs the two-pass ingestion (direct intents in Pass A, arranged `for_child` intents in Pass B with child-priority override), and creates couples in deterministic id-sorted order under a single `transaction.atomic()`. A pair where either partner is already in an active couple — checked by `is_in_active_couple()` against the unique-active-couple constraint that fix B2-01 added — is skipped, so duplicate active couples cannot be created even under repeated resolver invocations or chord workers. The companion resolver `resolve_separate_intents(simulation, tick)` reads `'"separate"'` `DecisionLog` entries from tick `T-1` with the same JSON pattern, returns immediately when the era template has `divorce_enabled: false`, and otherwise marks the active couple of each declarant as `dissolved_at_tick = tick`, `dissolution_reason = 'separate'`. The third operation, `dissolve_on_death(deceased_agent, tick)` in `couple.py:369-392`, is invoked from the mortality-resolution path when a partnered agent dies: it nulls the appropriate FK (`agent_a` or `agent_b` depending on which side the deceased was), captures the deceased's name into the corresponding `*_name_snapshot` field so the genealogical record survives the FK cascade, sets `dissolution_reason = 'death'`, and persists with a single `update_fields=[...]` save. As of the pinned commit, this dissolution path is a regular function call rather than a Django signal handler — the spec considered an `agents.Agent` `post_save` signal listening for `is_alive` transitions and rejected it on the grounds that signals add hidden coupling and are harder to audit than an explicit invocation from the mortality module. The couple lifecycle is exercised by the demography unit-test suite (`epocha/apps/demography/tests/test_couple.py`) but, consistent with the gap noted in §4.1.1 and §4.1.2, none of `stable_matching()`, `resolve_pair_bond_intents()`, `resolve_separate_intents()`, or `dissolve_on_death()` is invoked from `epocha/apps/simulation/engine.py` or `epocha/apps/simulation/tasks.py` as of the pinned commit (a `grep` for the function names outside `epocha/apps/demography/` returns only commentary at `engine.py:265-272` describing the tick+1 resolution semantics and the `pair_bond` action's role in the decision pipeline). The integration into the live tick loop is tracked alongside the equivalent mortality and fertility gaps as a Plan 4 deliverable (Initialization, Engine integration, and Historical validation).

**Simplifications.** The current implementation deliberately omits four refinements that the family-demography literature treats as proper extensions rather than corrections of the baseline mechanism. First, only monogamous couples are representable: the `Couple` model carries exactly two foreign keys, and the spec records polygynous and polyandrous couple types as deferred (audit fix MISS-8) because supporting more than two partners would require relaxing the `unique_active_couple` constraint and reworking the heir-resolution path; the `couple_type` enum exposes `monogamous` and `arranged` as the two canonical values, with `arranged` indicating the formation pathway (parent-mediated) rather than a partner-count distinction. Second, the agent layer carries three gender values (`male`, `female`, `non_binary`) and four sexual-orientation values (`heterosexual`, `homosexual`, `bisexual`, `asexual`) in `agents/models.py:11-20`, but the homogamy score and the stable-matching algorithm of equations (4.6) and (4.7) do not consume these fields as of the pinned commit: candidate filtering on gender and orientation is the responsibility of the caller that builds the `proposers` and `respondents` lists, and the founder-population builder that performs that filtering for non-heterosexual or non-binary configurations is itself part of the Plan 4 initialization deliverable. Third, no remarriage cooldown is enforced beyond the per-era `mourning_ticks` field reported in Table 4.5: the field is loaded from the template but not yet consumed by any code path, so a widowed agent can in principle re-pair on the tick following the death of a partner; wiring `mourning_ticks` into the eligibility check of `resolve_pair_bond_intents()` is a one-line change reserved for Plan 4. Fourth, Gale-Shapley is applied at initialization only, not as a fallback at runtime when a large unmatched cohort accumulates: the per-tick mechanism is exclusively intent-driven, on the assumption that the LLM agents will declare `pair_bond` intents at a rate consistent with the population's marriage market; if the validation suite of Chapter 7 reveals systematic underformation, a periodic re-application of the matching primitive over unmatched eligible adults is the natural extension and is documented in the demography spec under the Known Limitations heading.



## 4.2 Economy — Behavioral integration

> Status: implemented as of commit `<filled-on-merge>`, spec audit CONVERGED 2026-04-15.

Chapter 4.2 documents the behavioral layer that sits on top of the economic substrate of §3.6. The substrate of §3.6 is the part of the model that does not depend on agent psychology: it owns the production technology, the monetary aggregates, the Walrasian clearing of single-tick markets, and the per-tick distribution of output into wages, rents, and taxes. Three families of behavior — backward-looking price expectations, intertemporal credit and bank-balance-sheet dynamics, and the Gordon-anchored property market — were specified in the 2026-04-15 economy-behavioral-integration design and audited to convergence under that document. Each family is implemented in a single Python module under `epocha/apps/economy/`: `expectations.py` for the Nerlove (1958) adaptive-expectations engine described in §4.2.1, `credit.py` and `banking.py` for the Diamond-Dybvig (1983) fractional-reserve credit-and-banking machinery described in §4.2.2, and `property_market.py` for the tick-`T+1`-settled Gordon-valuation property market described in §4.2.3. The three modules are wired into the canonical economic tick orchestrated by `epocha/apps/economy/engine.py:process_economy_tick_new()`, which is itself dispatched from the simulation tick loop in `epocha/apps/simulation/engine.py:354` whenever the simulation has the new economy data layer initialized; consequently, unlike the demography modules of §4.1.x, the behavioral economy described in this chapter is genuinely live in the per-tick pipeline as of the pinned commit, and the `Status` headers carried by §4.2.1–§4.2.3 record only the spec-audit convergence date rather than an integration-pending caveat.

### 4.2.1 Adaptive expectations (Cagan 1956)

> Status: implemented as of commit `<filled-on-merge>`, spec audit CONVERGED 2026-04-15.

**Background.** Adaptive expectations enter the Epocha tick pipeline because the LLM-driven decision layer needs a per-agent forecast of next-tick prices for each tradable good, and the family of forecasts the model requires must be expressible in three concrete properties: it must be local — each agent has its own forecast, persisted between ticks — so that personality and history can shift it; it must be defined under bounded rationality — agents do not know the true data-generating process — so that the forecast can be wrong in ways the model can study rather than imposing rational-expectations consistency by construction; and it must be computable in `O(n_agents · n_goods)` per tick without solving a fixed point, since the tick pipeline already carries the Walrasian tatonnement of §3.6 and a second nested optimization would dominate the cost. The canonical Muthian (1961) rational-expectations alternative was rejected on the second and third counts: it requires every agent to know the joint stochastic process of all prices and to internalize the model the modeler is using, which neither the LLM nor the personality-modulated decision pipeline of §3.2 can provide, and it would require a per-tick fixed-point solve over heterogeneous beliefs that is incompatible with the cost envelope. The adaptive-expectations family — first formalized by Cagan (1956) for hyperinflation forecasting and independently by Nerlove (1958) in the cobweb-model literature for agricultural supply — solves all three constraints with a single recursive update parameterized by an adaptation rate `λ ∈ (0, 1)`: forecasts are local because each agent carries its own state, bounded-rational because the update rule does not require knowing the true process, and `O(1)` per agent per good per tick because the recursion replaces optimization. The pinned implementation transcribes the Nerlove form of the recursion (the textbook expression that appears in cobweb-theorem derivations) and credits Nerlove (1958) in the module docstring of `epocha/apps/economy/expectations.py:1-23`; the Cagan (1956) lineage is acknowledged in §2.4 of this whitepaper and remains the older anchor for the inflation-forecasting interpretation of the same recursion. The two papers describe the same underlying update rule expressed in equivalent forms, and the choice of attribution at the code-comment level reflects the cobweb-style application (price-by-good forecasts) rather than a substantive disagreement with the Cagan formulation.

**Model.** Each agent maintains, for each good category in the simulation, a row of the `AgentExpectation` model declared in `epocha/apps/economy/models.py:506-559` carrying an `expected_price`, a categorical `trend_direction ∈ {rising, falling, stable}`, a scalar `confidence ∈ [0, 1]`, and the per-agent `lambda_rate` actually used for the update at the previous tick (so the value is auditable rather than recomputed on demand). The recursion that updates `expected_price` between ticks is the canonical adaptive-expectations rule:

```
E_{t+1}[p] = λ · p_t + (1 − λ) · E_t[p]                         (4.9)
```

Equation (4.9) is the implementation of the inner expression in `update_agent_expectations()` at `epocha/apps/economy/expectations.py:205-207`, where `p_t` is the actual tick-`t` market price for the good in the agent's zone (read from `ZoneEconomy.market_prices` populated by the previous tick of the substrate of §3.6) and `E_t[p]` is the agent's previous expected price for the same good. The Cagan (1956) hyperinflation paper writes the same update in the equivalent error-correction form `E_{t+1}[π] = E_t[π] + λ · (π_t − E_t[π])`, which is algebraically identical to (4.9) after a one-line rearrangement; the implementation chose the convex-combination form because it does not require materializing the prediction error as an intermediate variable. The per-agent adaptation rate `λ` is itself a function of the agent's Big Five personality vector rather than a single scalar fixed across the population, which is the substantive Epocha extension of the textbook recursion. The personality modulation, implemented in `compute_lambda_from_personality()` (`expectations.py:42-79`), is a linear deviation from the era-template `λ_base` centered on the population mean of 0.5 for each trait:

```
λ(agent) = clip( λ_base
               + (N(agent) − 0.5) · n_mod
               + (O(agent) − 0.5) · o_mod
               − (C(agent) − 0.5) · c_mod ,
               0.05, 0.95 )                                     (4.10)
```

Equation (4.10) reads `N`, `O`, `C` as the agent's Neuroticism, Openness, and Conscientiousness scores from the personality vector (defaulting to the population mean of 0.5 when the trait is missing) and applies the three modulation coefficients `n_mod`, `o_mod`, `c_mod` from the era-template `expectations_config` block. The signs of the three contributions follow Costa and McCrae (1992): high Neuroticism increases reactivity to new price signals (positive contribution), high Openness increases receptivity to change (positive contribution), and high Conscientiousness anchors the forecast to the prior expectation (negative contribution). The clip to `[0.05, 0.95]` declared as the structural constants `_LAMBDA_MIN` and `_LAMBDA_MAX` at `expectations.py:38-39` is documented in the module as a non-tunable structural bound rather than a free parameter: at `λ = 0.05` the forecast is essentially static (the previous expectation is preserved with negligible weight on the new observation), and at `λ = 0.95` the forecast collapses to a naive expectation (next tick's price equals last tick's price); both extremes are degenerate as adaptive expectations and the clip prevents an unfortunate combination of personality scores and modulation coefficients from driving an agent into either limit. The `trend_direction` field is updated by the helper `detect_trend(expected, actual, threshold)` (`expectations.py:82-106`), which classifies the move from `expected` to `actual` as `rising` when `actual > expected · (1 + threshold)`, as `falling` when `actual < expected · (1 − threshold)`, and as `stable` otherwise; the threshold is the `trend_threshold` field of the era-template `expectations_config` (default `0.05`, identical across all five Plan 1 templates), and is a tunable design parameter rather than a value derived from a specific empirical study. The `confidence` field is incremented by `+0.05` when the agent's previous expectation was within `trend_threshold` of the realized price and decremented by `−0.05` otherwise, clipped to `[0, 1]` (`expectations.py:213-224`); the `±0.05` step is also a tunable design parameter and is documented inline as such.

**Parameters.** All five era templates shipped with Plan 2 carry the same `expectations_config` block, populated by `_behavioral_config()` in `epocha/apps/economy/template_loader.py:179-196`. The values are seeded from a single source in the loader rather than redundantly inscribed in five JSON files because none of the audited Plan 2 calibration evidence motivated era-specific differentiation at the time the templates were frozen; per-era differentiation of `λ_base` and the modulation coefficients is a Plan 4 calibration deliverable. Table 4.7 records the seed values explicitly so the homogeneity is visible to the reader.

Table 4.7 — Adaptive-expectations parameters seeded by `_behavioral_config()` (identical across all five Plan 1 templates pending Plan 4 calibration).

| Parameter             | Seed value | Semantic role                                                              |
|-----------------------|-----------:|----------------------------------------------------------------------------|
| `lambda_base`         |       0.30 | Baseline adaptation rate before personality modulation                      |
| `neuroticism_mod`     |       0.15 | Magnitude of the positive Neuroticism contribution to per-agent `λ`        |
| `openness_mod`        |       0.10 | Magnitude of the positive Openness contribution to per-agent `λ`           |
| `conscientiousness_mod` |     0.10 | Magnitude of the negative Conscientiousness contribution to per-agent `λ`  |
| `trend_threshold`     |       0.05 | Fractional deviation from `expected_price` required to change `trend_direction` |

The structural bounds `_LAMBDA_MIN = 0.05` and `_LAMBDA_MAX = 0.95` on the per-agent output of (4.10) are not in Table 4.7 because they are coded as constants in `expectations.py:38-39` rather than as template fields, on the grounds that a structural bound that prevents degenerate forecasts is a property of the model rather than a calibration choice.

**Algorithm.** On every tick, the economy orchestrator invokes `update_agent_expectations(simulation, tick)` (`expectations.py:109-249`) before market clearing, so that the per-agent forecasts the §3.6 substrate consults during clearing reflect the previous tick's realized prices rather than the prices being computed at the current tick. The function reads the simulation-level `expectations_config` populated at template-loading time, materializes the actual price map by aggregating `ZoneEconomy.market_prices` across all zones with a last-write-wins merge (a single-zone simplification documented inline as a multi-zone refinement target), and bulk-fetches the existing `AgentExpectation` rows for the simulation in a single keyed-by-`(agent_id, good_code)` dictionary so the per-agent loop runs without N+1 queries. For each living agent the per-tick `λ` is computed once from the agent's personality and the era's modulation coefficients, then for each good with an actual price the function either creates a new `AgentExpectation` initialized to the realized price with `confidence = 0.5` and `trend_direction = "stable"` (first observation) or updates an existing row by applying (4.9) with the per-agent `λ`, calling `detect_trend()` against the previous expectation and the new realized price, and adjusting `confidence` by the prediction-error rule. Newly-created and updated rows are flushed in two terminal `bulk_create` and `bulk_update` calls so the entire pass is two writes per tick regardless of the agent count. The orchestrator step in `engine.py:152-156` records the call in the canonical 9-step economic cycle as `STEP 0: EXPECTATIONS UPDATE (Nerlove adaptive)`, and the call site is reached unconditionally whenever `process_economy_tick_new()` is dispatched from the simulation engine, which itself is dispatched whenever the simulation has the `Currency` records that mark the new economy data layer as initialized (`epocha/apps/simulation/engine.py:350-358`). Consequently, in contrast to the demography modules of §4.1.x, the adaptive-expectations engine described here is genuinely active in the live tick loop as of the pinned commit, and the per-tick `AgentExpectation` rows it produces are consumed downstream by the LLM context builder in `epocha/apps/economy/context.py:162-188` to render the agent's price assessment block at decision time.

**Simplifications.** The current implementation deliberately omits four refinements that the adaptive-expectations literature treats as proper extensions rather than corrections of the baseline recursion. First, only the price level for each good is forecast; the recursion is single-variable per good, and there is no joint forecast across goods, no inflation forecast as a separate variable distinct from the per-good price forecast, and no second-moment forecast (volatility, dispersion). Cagan's original (1956) application to hyperinflation forecasts the inflation rate `π` rather than the price level `p`, and the Epocha implementation could be extended to a derived inflation forecast by wrapping the per-good price recursion in a tick-over-tick log-difference; the spec records this as a deferred refinement under the audit-resolution log of the 2026-04-15 design document. Second, the per-agent `λ` is homogeneous across goods within a single agent: the same personality-modulated `λ` is applied to every `AgentExpectation` row owned by the agent, with no good-specific differentiation. A wealthier agent that allocates more cognitive attention to high-impact goods could in principle carry a higher `λ` for the goods that dominate the household budget and a lower `λ` for marginal goods; the spec leaves this as a future refinement and the implementation treats the homogeneity as a deliberate scope choice for the Plan 2 economy. Third, the adaptation rate `λ` is not itself learned: the Big Five modulation in (4.10) is a static mapping from personality to `λ`, with no mechanism by which an agent whose forecasts have been systematically wrong updates its own `λ` upward (to react more to surprises) or downward (to anchor more on the prior). Bayesian-learning extensions of adaptive expectations (Evans and Honkapohja 2001) provide the canonical formalism for `λ` itself being a learned parameter; the Epocha implementation tracks prediction accuracy through the `confidence` field but does not feed `confidence` back into `λ` in the pinned commit, on the grounds that doing so would require a second-order calibration not delivered in Plan 2. Fourth, the multi-zone price aggregation is implemented as a last-write-wins merge of `ZoneEconomy.market_prices` across all zones rather than as a per-zone forecast for each agent: an agent in zone A sees the same actual price for a good as an agent in zone B even when the two zones cleared at different prices in the previous tick. The merge is documented inline as an MVP simplification (`expectations.py:144-153`) and the per-zone differentiation is the natural extension once the multi-zone economy of §3.6 is exercised by the validation suite of Chapter 7.

### 4.2.2 Credit and banking (Diamond-Dybvig 1983, fractional reserve)

> Status: implemented as of commit `<filled-on-merge>`, spec audit CONVERGED 2026-04-15.

**Background.** The credit-and-banking layer enters the Epocha tick pipeline because the agent decision space documented in §3.2 carries an explicit `request_loan` action and an implicit dependency on a stable monetary aggregate, and neither can be satisfied by the substrate of §3.6 in isolation: the substrate clears single-tick goods markets and distributes wages and rents, but it does not represent the intertemporal contracts that connect a tick-`T` borrowing decision to the tick-`T+k` repayment obligation that constrains the borrower's future cash, nor does it carry the bank-balance-sheet aggregates whose deterioration produces the systemic-risk signals the LLM context builder of §3.5 needs to feed into the decision pipeline. Diamond and Dybvig (1983) is the canonical reference for fractional-reserve banking under depositor-confidence dynamics: a single bank takes deposits, lends a fraction of them out, holds the rest as reserves, and is exposed to a self-fulfilling bank-run equilibrium when depositor confidence falls below a threshold and depositors withdraw faster than maturing loans can be liquidated. The Epocha implementation transcribes the qualitative dynamic — confidence erodes when reserves fall short of the required ratio, the erosion broadcasts as agent-level concern memories, and the broadcast itself accelerates the erosion through the LLM-mediated decision pipeline — but deliberately omits two quantitative elements of the original Diamond-Dybvig model. First, the model is a single aggregate bank per simulation rather than a population of competing banks (the inter-bank market that shapes contagion in the empirical bank-run literature is deferred), and consequently there is no inter-bank lending channel and no central-bank lender of last resort. Second, the original Diamond-Dybvig bank-run condition couples low confidence with insolvency through a coordination game on depositor withdrawal types; the audit convergence of 2026-04-15 (audit fix C-3) replaced the coupled condition with the simpler trigger `confidence_index < 0.5` evaluated regardless of solvency status, on the grounds that the LLM-driven population is fully heterogeneous in its information state and the original game-theoretic equivalence does not hold pointwise across an LLM agent set. Loan pricing follows Stiglitz and Weiss (1981) — interest rates carry a risk premium proportional to borrower leverage as a reduced-form representation of the lender's inability to perfectly observe borrower risk — and default cascades use the breadth-first contagion mechanism of Allen and Gale (2000) capped at a configurable depth.

**Model.** The banking-system state is a single `BankingState` row per simulation declared in `epocha/apps/economy/models.py:568` and carries `total_deposits`, `total_loans_outstanding`, `reserve_ratio`, `base_interest_rate`, an `is_solvent` boolean, and a `confidence_index ∈ [0, 1]`. Loans are individual `Loan` rows (`models.py:371-432`) with `lender`, `borrower`, `principal`, `interest_rate`, `remaining_balance`, an optional `collateral` foreign key to `Property` with `related_name="collateralized_loans"`, an `issued_at_tick`, an optional `due_at_tick`, a `times_rolled_over` counter, and a `status ∈ {active, repaid, rolled_over, defaulted}`. The bank-run trigger that drives the broadcast of banking-concern memories under audit fix C-3 is the simple inequality on the confidence index:

```
broadcast_concern_at_tick(t)  ⇔  BankingState.confidence_index < 0.5     (4.11)
```

Equation (4.11) is implemented in `broadcast_banking_concern()` at `epocha/apps/economy/banking.py:322-398`, with the threshold `0.5` declared as the module-level constant `_CONCERN_CONFIDENCE_THRESHOLD` at `banking.py:319`. The condition is evaluated unconditionally with respect to `is_solvent`, which is the substantive change introduced by audit fix C-3: the original Diamond-Dybvig (1983) coordination game predicts a bank run when both confidence is low *and* the bank is insolvent, but in the Epocha pipeline the confidence dynamic itself drives `is_solvent` toward `False` over time (`check_solvency()` decrements `confidence_index` by `0.1` per tick whenever reserves are short), so the audited condition triggers concern broadcast at the *fear* stage rather than only after the realized failure, which is the empirical pattern documented in the bank-run literature surveyed in the spec. The broadcast itself creates a `Memory` row with `emotional_weight = 0.6` and `source_type = "public"` for a random sample of `_CONCERN_BROADCAST_RATIO = 0.5` of the living agent population (`banking.py:354-385`), with a deduplication window of `_CONCERN_DEDUP_TICKS = 3` ticks aligned to the agent-engine memory deduplication constant in `simulation/engine.py`.

The loan-issuance condition combines the loan-to-value collateral cap of Stiglitz and Weiss (1981) credit-rationing theory with a bank-solvency precondition:

```
approve_loan(borrower, amount, collateral)
  ⇔  collateral.value · LTV ≥ existing_debt(borrower) + amount
  ∧  BankingState.is_solvent                                              (4.12)
```

Equation (4.12) is implemented in `evaluate_credit_request()` at `credit.py:158-224`. The existing-debt aggregate sums `remaining_balance` over the borrower's active loans; the LTV ratio is `credit_config.loan_to_value`, which differs by era template. When both conditions are satisfied, the function returns the per-tick interest rate computed by the Stiglitz-Weiss (1981) risk-pricing rule

```
r = base_rate · (1 + risk_premium · debt_ratio)
debt_ratio = (existing_debt + amount) / max(borrower.wealth, 1.0)         (4.13)
```

with `base_rate` read from `BankingState.base_interest_rate`, `risk_premium` defaulting to `0.5` from `credit_config.risk_premium`, and the leverage clipped on the wealth side to avoid division by zero for newborn or destitute agents. The functional form is a linearized reduced-form approximation of the Stiglitz-Weiss adverse-selection model — the original predicts a non-linear relationship — chosen for transparency and to keep the per-tick cost of credit evaluation `O(1)` per request. The collateral-pledge logic that selects which property the borrower offers as collateral is implemented in `find_best_unpledged_property()` at `credit.py:733-751` and explicitly excludes properties already used as collateral for an active loan via the `collateralized_loans__status="active"` exclusion clause: this is audit fix M-6 from the 2026-04-15 convergence, which prevents the same property from being double-pledged across two simultaneous loans (a violation of the Stiglitz-Weiss collateral semantics that the pre-audit implementation allowed).

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
| `risk_premium`                     |       0.50 | Coefficient on the borrower-leverage spread in (4.13)                         |
| `max_rollover`                     |          3 | Maximum number of times a maturing loan may be rolled over before default     |
| `default_loan_duration_ticks`      |         20 | Default loan duration assigned by `issue_loan()` when the caller passes none  |
| `_CONCERN_CONFIDENCE_THRESHOLD`    |       0.50 | Threshold of (4.11) below which banking-concern memories are broadcast        |
| `_CONCERN_BROADCAST_RATIO`         |       0.50 | Fraction of the living population that receives the per-tick concern broadcast |
| `CASCADE_LOSS_THRESHOLD`           |       0.50 | Fraction of lender wealth above which a default loss propagates to the lender |

The structural constants `_CONCERN_CONFIDENCE_THRESHOLD`, `_CONCERN_BROADCAST_RATIO`, and `CASCADE_LOSS_THRESHOLD` are coded as module-level constants in `banking.py:319` and `credit.py:50` rather than as template fields, on the grounds that they encode the qualitative shape of the bank-run dynamic (a self-fulfilling prophecy needs a threshold below which fear becomes contagious) rather than calibration choices that vary by historical era. The `risk_premium` value of `0.5` is a design choice rather than an empirical measurement — Stiglitz and Weiss (1981) predict that the risk-pricing slope is positive and increasing in leverage but do not provide a numeric coefficient — and is documented inline as a tunable design parameter at `credit.py:189-194`.

**Algorithm.** On every tick, the economy orchestrator invokes the credit-market step exactly once (gated by a `credit_processed` flag so it does not execute per-zone) at `epocha/apps/economy/engine.py:333-348`, with the following ordered sequence of calls. First, `default_dead_agent_loans(simulation)` (`credit.py:703-730`) defaults all active loans whose borrower has `is_alive = False`: this is audit fix M-3 from the 2026-04-15 convergence, which closes the silent-debt-amnesty gap whereby the pre-audit implementation left dead-borrower loans in `active` status indefinitely, allowing the borrower's heirs to inherit a property still encumbered by a debt the system would never collect. Second, `service_loans(simulation, tick)` (`credit.py:328-398`) collects per-tick interest on every active loan by deducting `remaining_balance · interest_rate` from the borrower's cash and crediting it to the lender (or to the banking system aggregate when `lender_type = "banking"`); borrowers who cannot pay interest are returned in a list for the maturity step to default. Third, `process_maturity(simulation, tick)` (`credit.py:401-536`) handles loans whose `due_at_tick` equals the current tick, with three outcomes per loan: full repayment when the borrower has enough cash to cover `remaining_balance`, a Minsky-style rollover when the borrower can pay the interest portion but not the principal and the `times_rolled_over` counter is below `max_rollover` (a new loan is created at `interest_rate · 1.10` reflecting the lender's risk adjustment, with `times_rolled_over += 1`), and default when neither condition is satisfied. Fourth, `process_defaults(simulation, tick)` (`credit.py:539-645`) seizes the collateral by transferring `Property.owner` to the lender (or to the government for banking-system loans), zeroes the loan's `remaining_balance`, and creates a negative reputation memory for the borrower with `action_sentiment = -0.7` (zone observers) and `-0.9` (the lender directly) via the reputation system of §4.x. Fifth, `process_default_cascade(simulation, tick, max_depth=3)` (`credit.py:754-858`) runs a breadth-first contagion pass over the debt graph: for each lender whose aggregate loss from this tick's defaults exceeds `CASCADE_LOSS_THRESHOLD = 0.5` of their wealth, the lender's own active loans are marked defaulted, and the contagion propagates to their lenders in turn until either no further threshold breach occurs or `max_depth = 3` is reached (the cap prevents infinite propagation and is calibrated against the typical empirical-network diameter of 3-5 links reported by Allen and Gale 2000). Sixth, `adjust_interest_rate(simulation, tick)` (`banking.py:112-194`) applies the Wicksellian adjustment `r_{t+1} = r_t · (1 + adj_rate · (demand − supply) / max(supply, 0.001))` to the base rate and clamps the result to `[0.005, 0.50]`. Seventh, `check_solvency(simulation)` (`banking.py:197-254`) evaluates `reserves = total_deposits − total_loans_outstanding` against `required = total_deposits · reserve_ratio` and updates `confidence_index` by `−0.1` per tick of insolvency or `+0.05` per tick of recovery (the asymmetry encodes the trust-asymmetry observation that confidence is easier to lose than to rebuild). Eighth and last, `broadcast_banking_concern(simulation, tick)` (`banking.py:322-398`) evaluates (4.11) and creates the concern memories. The eight-step sequence is deterministic given the simulation random seed (the `random.sample()` call in the broadcast step consumes the seeded `random` module), and the entire credit step writes a bounded number of database rows per tick — bounded by the live agent count for the broadcast and by the active-loan count for servicing and maturity — so the per-tick cost is `O(n_agents + n_active_loans)`.

**Simplifications.** The current implementation deliberately omits four refinements that the credit-and-banking literature treats as proper extensions rather than corrections of the baseline mechanism. First, the banking sector is a single aggregate bank per simulation rather than a population of competing banks: the `BankingState` row is one-to-one with `Simulation`, and there is no inter-bank lending market, no inter-bank exposure graph, and no central-bank lender of last resort. The Allen-Gale (2000) contagion mechanism is therefore implemented only over the agent-to-agent debt graph (`process_default_cascade`), not over a banking-network graph; a multi-bank refinement is recorded in the spec as a deferred extension and would require introducing a `Bank` model with per-bank balance sheets and an inter-bank liability graph. Second, deposit insurance is abstract: the `BankingState.is_solvent` flag prevents new loan issuance while insolvent (via the precondition in (4.12)), but there is no explicit deposit-insurance fund that depositors can claim against, and depositors cannot "withdraw" their cash from the bank in the literal sense because the AgentInventory cash field already represents on-hand cash rather than a deposited balance — the model treats all agent cash as implicitly deposited (`recalculate_deposits()` at `banking.py:281-305`). A future refinement would split `AgentInventory.cash` into a deposited fraction and a hoarded fraction, allowing the bank-run dynamic to be expressed as withdrawal pressure rather than as confidence-mediated rumor. Third, loan negotiation is single-round take-it-or-leave-it: the borrower presents a `request_loan` action with a target amount and a candidate collateral, `evaluate_credit_request()` either approves at the Stiglitz-Weiss rate or rejects with a stated reason, and there is no second round in which the borrower could counter-propose a smaller amount, a different collateral, or a longer duration to bring the request inside the LTV envelope. Multi-round negotiation is recorded as a deferred refinement under the audit-resolution log of the 2026-04-15 design document, on the grounds that it would interact with the LLM context budget and the per-tick decision pipeline in ways that need a separate calibration pass. Fourth, the rollover interest-rate increment is fixed at `1.10` per rollover (`credit.py:504`) rather than being a function of the borrower's leverage at the rollover instant or of the macroeconomic stress signal carried by the banking confidence index; a more sophisticated rollover repricing rule that responds to systemic risk is the natural extension once the validation suite of Chapter 7 exercises the Minsky-stage classification (`classify_minsky_stage` at `credit.py:104-155`) against the canonical Minsky (1986) hedge-speculative-Ponzi taxonomy.

### 4.2.3 Property market

> Status: implemented as of commit `<filled-on-merge>`, spec audit CONVERGED 2026-04-15.

**Background.** The property market enters the Epocha tick pipeline because the agent decision space documented in §3.2 carries a `buy_property` action and a `sell_property` action whose semantics cannot be reduced to a single-tick goods-market clearing of the kind owned by the substrate of §3.6: a property changes hands once and stays with the buyer for the rest of the simulation, the asking price diverges systematically from the fundamental rental yield because sellers anchor on personality-modulated expectations, and the buyer's intent declared at tick `T` cannot settle within the same tick because the LLM-driven decision pipeline has already produced its outputs by the time the economy orchestrator is invoked. The implementation transcribes a zone-local listing-and-matching mechanism that preserves the three substantive properties: properties are listed by their owners with an asking price, the listings live in the buyer's current zone, and the matching settles at tick `T+1` against the `buy_property` intents declared at tick `T`. The fundamental-value benchmark against which sellers and buyers compare the asking price is the Gordon (1959) growth-model valuation `V = R / (r − g)`, which gives the intrinsic value of an asset whose cash flow is a perpetuity growing at rate `g` discounted at rate `r`; the Epocha implementation computes this benchmark per property and stores it in the `fundamental_value` field of the listing alongside the seller's `asking_price`, so that the divergence between price and value is observable to downstream analytics and is the natural Epocha analogue of the price-to-fundamentals divergence that Shiller (2000) identifies as the empirical signature of speculative bubbles. Two concrete simplifications are recorded inline: there is no multi-round negotiation between buyer and seller (the asking price is take-it-or-leave-it) and there is no inter-zone matching (a buyer in zone A cannot match a listing in zone B, even at a lower price, because the zone-locality assumption is the spatial structure that the property market inherits from §3.4 movement). The property market also carries a regime-change side-channel implemented in `process_expropriation()` that redistributes properties on government transitions following Acemoglu and Robinson (2006); the side-channel is documented in the property-market module because it operates on the same `Property` rows but it is invoked from the political subsystem rather than from the per-tick economy orchestrator, so the present subsection treats it only as the source of the collateral-conversion side effect on outstanding loans.

**Model.** The matching condition that transfers a property from a seller `s` to a buyer `b` at tick `T` reads against the `PropertyListing` table and the buyer's current zone:

```
match(b, ℓ) at tick T  ⇔  ℓ.status = "listed"
                       ∧  ℓ.property.zone = b.zone        (zone at matching time)
                       ∧  ℓ.property.owner ≠ b            (no self-purchase)
                       ∧  buyer_cash(b) ≥ ℓ.asking_price
                       ∧  buy_property ∈ DecisionLog(b, T−1)            (4.14)
```

Equation (4.14) is implemented in `process_property_listings()` at `epocha/apps/economy/property_market.py:188-332`, with the four conjuncts evaluated in the listed order so that the cheapest qualifying listing is selected via `order_by("asking_price").first()`. The zone-at-matching-time conjunct is the substantive change introduced by audit fix M-4 of the 2026-04-15 convergence: the pre-audit implementation read the buyer's zone from the decision context at tick `T−1`, which produced spurious matches when the buyer moved between ticks `T−1` and `T`, and the audited form reads `buyer.zone_id` directly at the matching call so that a buyer who has crossed a zone boundary loses the ability to match a listing in the previous zone. The self-purchase exclusion is the substantive change introduced by audit fix M-5 of the same convergence: the pre-audit implementation allowed a seller's own `buy_property` intent to match the seller's own listing (a no-op transaction that nonetheless consumed a tick of the buyer's intent budget and inflated the matched count), and the audited form excludes the buyer's own properties from the candidate set via `.exclude(property__owner=buyer)`. The borrowing precondition that gates the cash check is not part of the matching condition itself: a buyer with insufficient cash simply fails the match, and the spec records this as audit fix A-5 — the pre-audit design auto-issued a loan to cover the shortfall, which contradicted the architectural principle that all borrowing is an explicit LLM-driven action documented in §3.2, and the audited form removes the auto-loan path so that a buyer who needs credit must declare a `borrow` action in a previous tick and then redeclare `buy_property` once the cash is in hand.

The collateral-conversion condition that transfers a property from a defaulting borrower to the lender at the moment of loan default reads against the `Loan.collateral` foreign key established at issuance:

```
on default of loan L at tick T:
    if L.collateral ≠ ∅ :
        L.collateral.owner ← L.lender         (or government if lender = banking)
        L.lender_loss     ← max(0, L.remaining_balance − L.collateral.value)        (4.15)
```

Equation (4.15) is implemented in `process_defaults()` at `epocha/apps/economy/credit.py:539-645`, with the residual loss computed after the collateral value is netted out and propagated to the Allen-Gale (2000) breadth-first contagion pass described under the Algorithm of §4.2.2 when it exceeds `CASCADE_LOSS_THRESHOLD = 0.5` of the lender's wealth. The collateral conversion is the bridge between the credit subsystem of §4.2.2 and the property market of this subsection: a property pledged as collateral via the `find_best_unpledged_property()` call of (4.12) is locked out of new collateral pledges by audit fix M-6, and its conversion on default produces an immediate change of ownership that subsequent property-market ticks observe through the standard `property.owner` field. The conversion does not generate a `PropertyListing` for the lender — the lender takes the property directly into ownership and may or may not list it for sale in a future tick depending on its own LLM-driven decisions — and consequently does not appear in the per-tick `process_property_listings()` matched count.

**Parameters.** The property market does not carry an era-specific configuration block of its own; the parameters that govern matching behavior are inherited from the credit configuration of §4.2.2 (loan-to-value for the borrowing path, base interest rate as the discount rate `r` in Gordon valuation) and from the expectations configuration of §4.2.1 (the `trend_threshold = 0.05` of audit fix C-5 that classifies seller anchoring as rising, falling, or stable). The two property-market design parameters that are coded outside the era templates are the listing-expiration window and the Gordon-valuation guard band: stale listings are withdrawn after `10` ticks (`property_market.py:222`), reflecting the assumption that property markets in pre-industrial through modern economies operate on multi-period timescales and that an unsold listing past that horizon is more likely to be a stale price than a viable offer; the Gordon-valuation denominator is floored at `0.01` to prevent division by zero when `r ≈ g`, and the resulting valuation is clipped to `[0.1 · property.value, 10 · property.value]` to keep the fundamental from degenerating to zero on transient rent collapses or running away to infinity on transient rent surges (`property_market.py:114-121`). The valuation cap of `10×` book value is acknowledged in the spec's audit-resolution log as the binding constraint on the magnitude of speculative bubbles the simulation can express: real bubbles can exceed this multiple, and the cap is documented as a tunable design parameter rather than a structural bound. The four era templates inherit the per-property base values from `_PROPERTIES_BASE` in `template_loader.py:66-85` (farmland 200, workshop 150, shop 100 in primary-currency units), with the industrial template adding a factory at base value 500, the modern template adding a factory at 500 and an office at 300, and the sci-fi template adding an automated factory at 1 000 and a research lab at 800; the per-era differentiation is qualitative (which property types are available rather than what their parameters are) and the homogeneity of base values across eras is a Plan 4 calibration deliverable rather than a substantive design choice.

**Algorithm.** On every tick, the economy orchestrator invokes `process_property_listings(simulation, tick)` exactly once, gated by the same `credit_processed` flag that protects the credit step at `epocha/apps/economy/engine.py:333-348`, and with the explicit ordering note that the property market runs *before* the credit step so that property-sale cash credited to sellers can prevent loan defaults that would otherwise fire at the credit step within the same tick. The function executes five ordered passes. First, a single-query bulk update marks all listings older than `tick − 10` as `withdrawn`, replacing the per-listing iteration with a `.update()` call that is `O(1)` in the number of stale listings. Second, the function reads the previous tick's `DecisionLog` rows whose `output_decision` JSON contains the substring `"buy_property"` and parses each row with `json.loads()` to recover the `action` field; rows with malformed JSON are silently skipped, on the grounds that the LLM occasionally produces invalid JSON and a hard failure on parse would propagate an LLM failure into a tick-pipeline failure. Third, for each parsed buyer the function checks the four conjuncts of (4.14) in order and selects the cheapest qualifying listing via `order_by("asking_price").first()`; the zone-locality conjunct is enforced by the `property__zone_id=buyer.zone_id` filter, the self-purchase exclusion by `.exclude(property__owner=buyer)`, and the cash check by reading `AgentInventory.cash[currency_code]` against the listing's asking price. Fourth, when all conjuncts hold, the function executes the four-step settlement in a deterministic order: cash is deducted from the buyer's `AgentInventory.cash`, credited to the seller's `AgentInventory.cash` (creating an inventory row for the seller if missing), the property's `owner` and `owner_type` fields are reassigned to the buyer, and the listing's `status` is set to `"sold"`; the four writes are independent `save(update_fields=[...])` calls rather than a single transaction because the existing economy tick is already wrapped in a transaction at the orchestrator level. Fifth, an `EconomicLedger` row is created with `transaction_type="property_sale"` (added to `TRANSACTION_TYPES` by the same 2026-04-15 convergence) recording the cash flow from buyer to seller. The function returns a `{"matched": M, "expired": E, "failed": F}` dictionary that the orchestrator logs at `INFO` level for per-tick observability. The pass is `O(n_buyers · log n_listings)` per tick because the per-buyer query plan uses the `(zone, status, asking_price)` ordering rather than a full table scan, and the entire per-tick cost is bounded above by the live agent count for the buyer enumeration and by the active listing count for the per-buyer matching.

**Simplifications.** The current implementation deliberately omits four refinements that the property-market literature treats as proper extensions rather than corrections of the baseline mechanism. First, listings are matched once per tick in a single round: a buyer who has the cash for a listing but loses to another buyer ordered earlier in the iteration receives no second chance within the same tick, and a buyer whose only viable listing in the current zone is just above its budget cannot counter-offer at a lower price. Multi-round negotiation with bid-ask convergence is recorded in the spec as a deferred refinement, on the grounds that it would interact with the LLM context budget of §3.5 in ways that need a separate calibration pass. Second, listings do not persist their original ordering across the listing-expiration window: a listing posted at tick `T` competes with a listing posted at tick `T+5` purely on price, so an early-posted listing receives no priority for being on the market longer; a time-priority refinement (FIFO across listings at the same price) is recorded as a deferred extension. Third, the buyer's intent is binary rather than parameterized: a `buy_property` action does not carry a target type or a maximum price, and the matching pass selects the cheapest listing in the buyer's zone regardless of fit between the property's `production_bonus` and the buyer's role; a target-typed intent that filters listings by property type or by production-bonus alignment is the natural extension once the LLM action grammar of §3.2 is broadened to support typed parameters. Fourth, the asking-price formation rule that produces the divergence between `asking_price` and `fundamental_value` is documented in the `sell_property` action at the LLM-decision layer of §3.2 rather than at the property-market layer, and consequently this subsection treats the asking price as an exogenous input to the matching condition (4.14); the speculative-anchoring and personality-modulation logic that produces the divergence is the subject of the seller-side decision pipeline and is documented in §3.2.



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

- Acemoglu, D., and Robinson, J. A. (2006). *Economic Origins of
  Dictatorship and Democracy*. Cambridge University Press,
  Cambridge. ISBN 978-0-521-85526-6.
  https://doi.org/10.1017/CBO9780511510809
- Aher, G. V., Arriaga, R. I., and Kalai, A. T. (2023). Using large
  language models to simulate multiple humans and replicate human
  subject studies. In *Proceedings of the 40th International Conference
  on Machine Learning (ICML 2023)*, PMLR, 202, 337–371.
  https://proceedings.mlr.press/v202/aher23a.html
- Allen, F., and Gale, D. (2000). Financial contagion. *Journal of
  Political Economy*, 108(1), 1–33. https://doi.org/10.1086/262109
- Allport, G. W., and Postman, L. (1947). *The Psychology of Rumor*.
  Henry Holt and Company, New York, xiv+247 pp. (Pre-ISBN
  monograph; reviewed in Zeller 1948, *The Annals of the American
  Academy of Political and Social Science*, 257(1), 145–146,
  https://doi.org/10.1177/000271624825700169.)
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
- Becker, G. S. (1991). *A Treatise on the Family*, enlarged edition.
  Harvard University Press, Cambridge, MA. ISBN 978-0-674-90698-3.
- Bonabeau, E. (2002). Agent-based modeling: methods and techniques for
  simulating human systems. *Proceedings of the National Academy of
  Sciences*, 99(Suppl. 3), 7280–7287.
  https://doi.org/10.1073/pnas.082080899
- Brown, R., and Kulik, J. (1977). Flashbulb memories. *Cognition*, 5(1),
  73–99. https://doi.org/10.1016/0010-0277(77)90018-X
- Cagan, P. (1956). The monetary dynamics of hyperinflation. In M.
  Friedman (ed.), *Studies in the Quantity Theory of Money*. University
  of Chicago Press, Chicago, 25–117.
- Castelfranchi, C., Conte, R., and Paolucci, M. (1998). Normative
  reputation and the costs of compliance. *Journal of Artificial
  Societies and Social Simulation*, 1(3).
  https://www.jasss.org/1/3/3.html
- Chandola, T., Coleman, D. A., and Hiorns, R. W. (1999). Recent European
  fertility patterns: fitting curves to "distorted" distributions.
  *Population Studies*, 53(3), 317–329.
  https://doi.org/10.1080/00324720308089
- Coale, A. J., and Trussell, T. J. (1974). Model fertility schedules:
  variations in the age structure of childbearing in human populations.
  *Population Index*, 40(2), 185–258.
  https://doi.org/10.2307/2733910
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
- Evans, G. W., and Honkapohja, S. (2001). *Learning and Expectations
  in Macroeconomics*. Frontiers of Economic Research. Princeton
  University Press, Princeton, NJ. ISBN 978-0-691-04921-2.
- Gale, D., and Shapley, L. S. (1962). College admissions and the
  stability of marriage. *The American Mathematical Monthly*, 69(1),
  9-15. https://doi.org/10.2307/2312726
- Gompertz, B. (1825). On the nature of the function expressive of the
  law of human mortality, and on a new mode of determining the value of
  life contingencies. *Philosophical Transactions of the Royal Society
  of London*, 115, 513–583. https://doi.org/10.1098/rstl.1825.0026
- Goode, W. J. (1963). *World Revolution and Family Patterns*. The Free
  Press of Glencoe, New York. (Pre-ISBN monograph; Free Press / Macmillan
  edition, xii+432 pp. Source for the arranged-marriage typology and the
  parent-child asymmetry adopted in §4.1.3.)
- Gordon, M. J. (1959). Dividends, earnings, and stock prices.
  *The Review of Economics and Statistics*, 41(2), 99–105.
  https://doi.org/10.2307/1927792
- Gualdi, S., Tarzia, M., Zamponi, F., and Bouchaud, J.-P. (2015).
  Tipping points in macroeconomic agent-based models. *Journal of
  Economic Dynamics and Control*, 50, 29–61.
  https://doi.org/10.1016/j.jedc.2014.08.003
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
- Heligman, L., and Pollard, J. H. (1980). The age pattern of mortality.
  *Journal of the Institute of Actuaries*, 107(1), 49–80.
  https://doi.org/10.1017/S0020268100040257
- Homer, S., and Sylla, R. (2005). *A History of Interest Rates*, fourth
  edition. Wiley Finance. John Wiley and Sons, Hoboken, NJ.
  ISBN 978-0-471-73283-9.
- Human Mortality Database (HMD) (2024). University of California,
  Berkeley (USA) and Max Planck Institute for Demographic Research
  (Germany). https://www.mortality.org
- Kalmijn, M. (1998). Intermarriage and homogamy: causes, patterns,
  trends. *Annual Review of Sociology*, 24, 395-421.
  https://doi.org/10.1146/annurev.soc.24.1.395
- Lee, R. D., and Carter, L. R. (1992). Modeling and forecasting U.S.
  mortality. *Journal of the American Statistical Association*, 87(419),
  659–671. https://doi.org/10.1080/01621459.1992.10475265
- Masad, D., and Kazil, J. (2015). Mesa: an agent-based modeling framework.
  In *Proceedings of the 14th Python in Science Conference (SciPy 2015)*,
  51–58. https://doi.org/10.25080/Majora-7b98e3ed-009
- McCrae, R. R., and Costa, P. T. (1987). Validation of the five-factor
  model of personality across instruments and observers. *Journal of
  Personality and Social Psychology*, 52(1), 81–90.
  https://doi.org/10.1037/0022-3514.52.1.81
- Minsky, H. P. (1986). *Stabilizing an Unstable Economy*. A Twentieth
  Century Fund Report. Yale University Press, New Haven.
  ISBN 978-0-300-03386-1.
- Muth, J. F. (1961). Rational expectations and the theory of price
  movements. *Econometrica*, 29(3), 315–335.
  https://doi.org/10.2307/1909635
- Nerlove, M. (1958). Adaptive expectations and cobweb phenomena.
  *Quarterly Journal of Economics*, 72(2), 227–240.
  https://doi.org/10.2307/1880597
- Park, J. S., O'Brien, J. C., Cai, C. J., Morris, M. R., Liang, P., and
  Bernstein, M. S. (2023). Generative agents: interactive simulacra of
  human behavior. In *Proceedings of the 36th Annual ACM Symposium on
  User Interface Software and Technology (UIST '23)*. ACM.
  https://doi.org/10.1145/3586183.3606763
- Scarf, H. (1960). Some examples of global instability of the
  competitive equilibrium. *International Economic Review*, 1(3),
  157–172. https://doi.org/10.2307/2556215
- Schelling, T. C. (1971). Dynamic models of segregation. *Journal of
  Mathematical Sociology*, 1(2), 143–186.
  https://doi.org/10.1080/0022250X.1971.9989794
- Schmertmann, C. P. (2003). A system of model fertility schedules with
  graphically intuitive parameters. *Demographic Research*, 9, 81–110.
  https://doi.org/10.4054/DemRes.2003.9.5
- Seppecher, P. (2012). Flexibility of wages and macroeconomic
  instability in an agent-based computational model with endogenous
  money. *Macroeconomic Dynamics*, 16(S2), 284–297.
  https://doi.org/10.1017/S1365100511000447
- Shiller, R. J. (2000). *Irrational Exuberance*. Princeton University
  Press, Princeton, NJ. ISBN 978-0-691-05062-6.
- Shoven, J. B., and Whalley, J. (1992). *Applying General Equilibrium*.
  Cambridge Surveys of Economic Literature. Cambridge University Press,
  Cambridge. ISBN 978-0-521-31986-7.
- Spielauer, M. (2011). What is social science microsimulation?
  *Social Science Computer Review*, 29(1), 9–20.
  https://doi.org/10.1177/0894439310370085
- Stiglitz, J. E., and Weiss, A. (1981). Credit rationing in markets
  with imperfect information. *American Economic Review*, 71(3),
  393–410. https://www.jstor.org/stable/1802787
- Tabeau, E., van den Berg Jeths, A., and Heathcote, C. (eds.) (2001).
  *Forecasting Mortality in Developed Countries: Insights from a
  Statistical, Demographic and Epidemiological Perspective*. European
  Studies of Population, vol. 9. Kluwer Academic Publishers, Dordrecht.
  https://doi.org/10.1007/0-306-47562-6
- van Imhoff, E., and Post, W. (1998). Microsimulation methods for
  population projection. *Population: An English Selection*, 10(1),
  97–138. (English-language counterpart of the article in *Population*,
  53(HS1), 97–136, December 1998.)
- Walras, L. (1874). *Éléments d'économie politique pure, ou théorie de
  la richesse sociale*. L. Corbaz et Cie., Lausanne (part I, 1874;
  part II issued 1877). Definitive (fourth) edition published by
  F. Pichon, Paris, 1900. English translation from the 1926 definitive
  edition by W. Jaffé (1954), *Elements of Pure Economics, or the
  Theory of Social Wealth*. George Allen and Unwin, London, for the
  American Economic Association and the Royal Economic Society.
- Wicksell, K. (1898). *Geldzins und Güterpreise: Eine Studie über
  die den Tauschwert des Geldes bestimmenden Ursachen*. Gustav Fischer,
  Jena. English translation by R. F. Kahn (1936), *Interest and Prices:
  A Study of the Causes Regulating the Value of Money*, with an
  introduction by Bertil Ohlin. Macmillan, London, for the Royal
  Economic Society.
- Wilensky, U. (1999). NetLogo. Center for Connected Learning and
  Computer-Based Modeling, Northwestern University, Evanston, IL.
  http://ccl.northwestern.edu/netlogo/
- Wrigley, E. A., and Schofield, R. S. (1981). *The Population History
  of England, 1541-1871: A Reconstruction*. Edward Arnold, London.
  Reissued by Cambridge University Press, 1989. ISBN 978-0-521-35688-6.
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

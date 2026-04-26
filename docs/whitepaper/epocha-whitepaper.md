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
- Human Mortality Database (HMD) (2024). University of California,
  Berkeley (USA) and Max Planck Institute for Demographic Research
  (Germany). https://www.mortality.org
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

# Government, Institutions, and Social Stratification -- Design Spec

## Goal

Implement a complete political system where governments function as living mechanisms (not labels), institutions have health that affects society, social classes shift dynamically, and inequality drives conflict. The 12 government types from the design doc are fully implemented as a data-driven configuration. Elections, coups, revolutions, corruption, and crime emerge from agent interactions and systemic pressures.

## Architecture

Three tightly coupled subsystems sharing a single processing phase in the tick engine:

1. **Government engine** -- 12 parameterized government types, indicator evolution, transitions, elections, coups
2. **Institutions** -- 7 institution types with health, feeding government indicators
3. **Social stratification** -- dynamic class mobility, Gini coefficient, crime, corruption

All three run in a single `process_political_cycle(simulation, tick)` call every N ticks (default 10), after faction dynamics and before memory decay. The order within the cycle: update institutions -> update stratification -> update government indicators -> check transitions -> run elections/coups.

## Models

All models go in `epocha/apps/world/models.py` (political structures belong to the world, not to agents).

### Government

```python
class Government(models.Model):
    simulation = models.OneToOneField(Simulation, on_delete=models.CASCADE, related_name="government")
    government_type = models.CharField(max_length=30, default="democracy")
    stability = models.FloatField(default=0.5, help_text="0.0 = collapsing, 1.0 = rock solid")
    ruling_faction = models.ForeignKey("agents.Group", null=True, blank=True, on_delete=models.SET_NULL,
                                        related_name="ruled_governments")
    head_of_state = models.ForeignKey("agents.Agent", null=True, blank=True, on_delete=models.SET_NULL,
                                       related_name="headed_governments")

    # Political indicators (0.0-1.0)
    institutional_trust = models.FloatField(default=0.5)
    repression_level = models.FloatField(default=0.1)
    corruption = models.FloatField(default=0.2)
    popular_legitimacy = models.FloatField(default=0.5)
    military_loyalty = models.FloatField(default=0.5)

    # Electoral tracking
    last_election_tick = models.PositiveIntegerField(default=0)

    formed_at_tick = models.PositiveIntegerField(default=0)
```

### GovernmentHistory

```python
class GovernmentHistory(models.Model):
    simulation = models.ForeignKey(Simulation, on_delete=models.CASCADE, related_name="government_history")
    government_type = models.CharField(max_length=30)
    head_of_state_name = models.CharField(max_length=255, blank=True)
    ruling_faction_name = models.CharField(max_length=255, blank=True)
    from_tick = models.PositiveIntegerField()
    to_tick = models.PositiveIntegerField(null=True, blank=True)
    transition_cause = models.CharField(max_length=50)

    class Meta:
        ordering = ["-from_tick"]
```

### Institution

```python
class Institution(models.Model):
    class InstitutionType(models.TextChoices):
        JUSTICE = "justice", "Justice"
        EDUCATION = "education", "Education"
        HEALTH = "health", "Health"
        MILITARY = "military", "Military"
        MEDIA = "media", "Media"
        RELIGION = "religion", "Religion"
        BUREAUCRACY = "bureaucracy", "Bureaucracy"

    simulation = models.ForeignKey(Simulation, on_delete=models.CASCADE, related_name="institutions")
    institution_type = models.CharField(max_length=20, choices=InstitutionType.choices)
    health = models.FloatField(default=0.5, help_text="0.0 = failed, 1.0 = thriving")
    independence = models.FloatField(default=0.5, help_text="0.0 = fully controlled by government, 1.0 = fully independent")
    funding = models.FloatField(default=0.5, help_text="0.0 = defunded, 1.0 = well funded")

    class Meta:
        unique_together = ["simulation", "institution_type"]
```

## The 12 Government Types -- Data-Driven Configuration

Each type is a dictionary of parameters consumed by the same engine. Adding a 13th type is adding a dictionary entry.

### Parameter schema

```python
{
    "label": str,                        # Display name
    "power_source": str,                 # "election" | "manipulated_election" | "force" | "inheritance" |
                                         # "wealth" | "religious_authority" | "military" | "none"
    "legitimacy_base": str,              # "popular" | "facade_popular" | "fear" | "dynasty" | "wealth" |
                                         # "divine" | "terror" | "none" | "mutual_benefit" | "theft"
    "repression_tendency": float,        # 0.0-1.0, natural drift of repression_level
    "corruption_resistance": float,      # 0.0-1.0, how much institutions resist corruption
    "election_enabled": bool,            # Whether elections happen
    "election_manipulated": bool,        # Whether elections are rigged (ruling faction bonus)
    "election_interval_ticks": int,      # Ticks between elections (if enabled)
    "succession": str,                   # "election" | "manipulated_election" | "strongest_faction" |
                                         # "inheritance" | "richest" | "religious_leader" | "military_leader" | "none"
    "stability_weights": {               # What contributes to stability
        "economy": float,
        "legitimacy": float,
        "military": float,
    },
    "institution_effects": {             # How government type affects each institution
        "justice": float,                # -1.0 to 1.0 (negative = degrades, positive = strengthens)
        "education": float,
        "health": float,
        "military": float,
        "media": float,
        "religion": float,
        "bureaucracy": float,
    },
    "transitions": {                     # Conditions for transitioning to another type
        "target_type": {
            "condition_name": threshold_value,  # e.g. "trust_below": 0.3
            ...
        },
    },
}
```

### The 12 types

**Democracy**: power from elections, legitimacy from popular support, low repression, high corruption resistance, stable when economy and trust are high. Degrades to illiberal_democracy when trust falls and repression rises.

**Illiberal Democracy (Democratura)**: elections exist but are manipulated (ruling faction bonus +0.3 in vote score). Media independence drops. Facade of democracy. Degrades to autocracy under pressure, can restore to democracy if popular legitimacy surges.

**Autocracy**: power by force, legitimacy from fear and loyalty, high repression, low corruption resistance. Military loyalty is critical. Falls when military loyalty drops or popular revolt erupts. Can degrade to totalitarian.

**Monarchy**: power by inheritance, legitimacy from dynasty and tradition. Succession goes to the heir (leader's child agent if exists, or highest charisma in ruling faction). Relatively stable but brittle -- incompetent heir triggers crisis.

**Oligarchy**: power from wealth concentration, legitimacy from economic control. Ruling faction is the wealthiest agents. High corruption, low popular legitimacy. Falls when internal oligarch conflict erupts or populist revolt.

**Theocracy**: power from religious authority, legitimacy from divine mandate. Religion institution is fused with government (independence = 0). Education is controlled. Falls when secularization spreads (agents losing faith over generations).

**Totalitarian**: power from total control, legitimacy from terror and propaganda. All institutions controlled (independence near 0). Maximum repression. Very stable short-term, brittle long-term -- death of leader triggers crisis. Can only transition from autocracy.

**Terrorist Regime**: power from systematic terror. Like totalitarian but less stable. Unsustainable -- naturally transitions to either autocracy (institutionalization) or anarchy (collapse).

**Anarchy**: absence of government. No head of state, no ruling faction. Institutions degrade rapidly without funding. Naturally unstable -- the strongest faction or most charismatic leader fills the vacuum. Transitions to any authoritarian type when someone seizes power.

**Federation**: mutual agreement among factions. Requires 2+ factions with positive sentiment. Government stability depends on inter-faction cooperation. Loose -- falls apart when factions diverge.

**Kleptocracy**: power from corruption. Ruling faction enriches itself. Corruption is systemic (resistance near 0). Economy degrades as wealth is siphoned. Falls when economic collapse triggers revolt.

**Military Junta**: military seizes power. Military loyalty is everything. Can only emerge from a coup when military institution is strong but military loyalty to government is low. Transitions to autocracy (personalization) or democracy (transition negotiated).

### Transition graph

Key transition paths (matching the design doc):

```
democracy -> illiberal_democracy -> autocracy -> totalitarian
                                                     |
monarchy -> revolution -> democracy OR autocracy     |
                                                     v
anarchy <---> autocracy <---> junta            terrorist_regime
   ^              |
   |              v
   +--- oligarchy / kleptocracy
   
theocracy -> secularization -> democracy
federation -> divergence -> anarchy or autocracy
```

Each transition has explicit conditions checked against government indicators. Multiple transitions can be eligible simultaneously -- the one with the most conditions satisfied wins. If tied, the more dramatic transition wins (revolution > gradual erosion).

## Institution Health Dynamics

Each institution's health evolves every political cycle based on:

**Government type influence**: each type has an `institution_effects` dict. An autocracy has `"justice": -0.02, "media": -0.03, "military": 0.02` -- justice and media degrade each cycle, military strengthens.

**Funding**: institutions with `funding > 0.5` slowly recover health; below 0.5 they degrade. Government type determines base funding (democracies fund broadly, autocracies fund military disproportionately).

**Independence**: institutions with low independence are controlled by the government. Controlled media can't report corruption, controlled justice can't prosecute the powerful. Independence drifts toward the government type's natural level.

### Institution -> Government indicator mapping

| Institution | Primary indicator affected | Mechanism |
|------------|--------------------------|-----------|
| Justice | institutional_trust, corruption | Healthy justice reduces corruption, builds trust |
| Education | (long-term) popular_legitimacy | Educated population is harder to manipulate |
| Health | popular_legitimacy | Population health affects satisfaction |
| Military | military_loyalty | Strong military with high independence = coup risk; low independence = loyal tool |
| Media | popular_legitimacy, institutional_trust | Free media exposes corruption, builds trust. Controlled media inflates legitimacy artificially. |
| Religion | popular_legitimacy (in theocracies), stability | Strong religion stabilizes theocracies, can destabilize secular governments |
| Bureaucracy | corruption, institutional_trust | Healthy bureaucracy reduces corruption. Corrupt bureaucracy amplifies it. |

**Aggregation formula** (runs each political cycle):

```
institutional_trust += (justice.health * 0.3 + media.health * media.independence * 0.3
                       + bureaucracy.health * 0.2 + education.health * 0.1 + health_inst.health * 0.1) * 0.1 - 0.05

corruption += (1.0 - justice.health * 0.4 - bureaucracy.health * 0.3 - media.health * media.independence * 0.3)
              * type.corruption_resistance * -0.05

popular_legitimacy += (health_inst.health * 0.2 + education.health * 0.15 + economy_factor * 0.35
                      + media_reported_legitimacy * 0.3) * 0.1 - 0.05

military_loyalty += (military.health * 0.4 + military.funding * 0.3 + head_charisma * 0.3) * 0.1 - 0.05
```

All indicators are clamped to [0.0, 1.0] after each update.

## Social Stratification

### Dynamic class mobility

`Agent.social_class` evolves every political cycle. The class is determined by the agent's wealth position relative to the simulation's wealth distribution:

```
wealth_percentile = agent's rank / total agents

elite:    top 5%
wealthy:  5-15%
middle:   15-50%
working:  50-80%
poor:     80-95%
enslaved: bottom 5% (only in certain government types that allow it)
```

These thresholds are configurable. The `enslaved` class only exists in government types with `allows_slavery: True` (autocracy, totalitarian, monarchy with low justice health). Otherwise bottom 5% is `poor`.

### Gini coefficient

Computed each political cycle from the wealth distribution of all living agents:

```python
def compute_gini(wealths: list[float]) -> float:
    """Gini coefficient: 0.0 = perfect equality, 1.0 = perfect inequality."""
    n = len(wealths)
    if n < 2:
        return 0.0
    sorted_w = sorted(wealths)
    cumulative = sum((2 * i - n + 1) * w for i, w in enumerate(sorted_w))
    return cumulative / (n * sum(sorted_w)) if sum(sorted_w) > 0 else 0.0
```

Source: Gini, C. (1912). "Variabilita e mutabilita." This is the standard formula used in economics for wealth inequality measurement.

**Effect**: when Gini > 0.6, revolt probability increases exponentially. When Gini > 0.7, revolution becomes almost inevitable (historical pattern: most revolutions occur at Gini 0.6-0.8). Source: Acemoglu, D. & Robinson, J. A. (2006). "Economic Origins of Dictatorship and Democracy." Cambridge University Press.

### Crime

New agent action: `"crime"`. An agent may choose crime when:
- `mood < 0.3` AND `wealth` in bottom 20% AND `agreeableness < 0.4`
- OR `conscientiousness < 0.3` AND `wealth` in bottom 30%

The decision is made by the LLM naturally -- the agent's desperate circumstances and personality make crime a rational choice. We add "crime" to the action list and let the LLM decide. No hardcoded triggers.

Crime effects:
- Perpetrator: wealth += small random amount (theft), mood += 0.05 (short-term relief)
- Victim (target agent): wealth -= same amount, mood -= 0.1
- Creates memory for both agents
- If caught (probability based on justice institution health): perpetrator mood -= 0.2, reputation damaged

**Organized crime**: emerges naturally from the faction system. When 3+ agents with crime history form a faction, the faction objective becomes criminal. This is already handled by the existing faction formation -- criminal agents cluster by circumstance (shared poverty, low agreeableness).

### Corruption

Corruption is an agent behavior, not just a government indicator. Agents in positions of power (head_of_state, faction leaders, agents with high wealth) with low conscientiousness tend to extract wealth from the system:

- Each political cycle, agents in power positions with `conscientiousness < 0.4` have a chance to skim wealth
- The corruption indicator on Government reflects the aggregate level
- Institution health degrades when corruption is high
- Corruption spreads via information flow: agents learn about corruption through hearsay, affecting their trust and vote intentions

## Elections

### Vote scoring formula

Each living agent produces a score for each candidate:

```
vote_score(agent, candidate) =
    relationship_sentiment(agent, candidate) * 0.25 +
    personality_alignment(agent, candidate) * 0.15 +
    economic_satisfaction(agent) * 0.20 +
    memory_influence(agent, candidate) * 0.25 +
    charisma_effect(candidate) * 0.15
```

Where:
- `relationship_sentiment`: from Relationship model, normalized to 0-1. Default 0.5 if no relationship.
- `personality_alignment`: personality similarity from `compute_affinity._personality_similarity` (reused from affinity.py).
- `economic_satisfaction`: `(agent.mood + min(agent.wealth / 100, 1.0)) / 2`. Agents with good mood and reasonable wealth are satisfied with the status quo.
- `memory_influence`: scan agent's memories from the last 20 ticks for mentions of the candidate's name. Count positive vs negative memories. Normalize to 0-1. This is where information flow becomes propaganda.
- `charisma_effect`: `candidate.charisma`. Pure attribute appeal.

**Candidates**: leader of each faction + current head_of_state (if running). Factionless agents cannot be candidates.

**Manipulated elections**: in illiberal_democracy, the ruling faction's candidate gets a bonus of +0.3 to their vote score (media manipulation, ballot stuffing).

**Result**: candidate with highest total score wins. New head_of_state is set. Ruling faction becomes the winner's faction. Memory created for all agents: "[candidate] won the election" (public).

### Succession (non-electoral)

For government types without elections:
- **inheritance**: leader's child agent (if exists via parent_agent FK), or highest charisma in ruling faction
- **strongest_faction**: faction with highest cohesion * member_count
- **military_leader**: agent with highest leadership_score in military-aligned faction
- **richest**: wealthiest agent
- **religious_leader**: leader of faction with most "religion"-related memories

## Coups and Revolutions

### Coup d'etat

A faction can attempt a coup when:
1. Faction cohesion > 0.6
2. Faction leader charisma > 0.5
3. Government military_loyalty < 0.4 (military won't defend the government)
4. Government stability < 0.3

Success probability: `faction_cohesion * 0.4 + leader_charisma * 0.3 + (1 - military_loyalty) * 0.3`

If success > 0.5: coup succeeds. Government transitions to autocracy or junta (depending on whether the faction is military-aligned). Head of state becomes faction leader. Old head of state loses power (memory for all agents).

If fails: faction cohesion drops by 0.2, leader may be "removed" (is_alive = False if repression is high).

### Popular revolution

Triggered when:
1. Gini > 0.6
2. popular_legitimacy < 0.3
3. At least one faction with objective containing grievance keywords AND cohesion > 0.5

The revolution succeeds if the combined strength of revolting factions exceeds the military loyalty * stability. On success: government transitions to anarchy (temporary) then the strongest revolting faction takes over.

## Effects on Existing Systems

### Decision pipeline context

`_build_context` enriched with:

```
Government: Democracy (stability: moderate)
Leader: Marco, ruling faction: The Guild
Society: middle class inequality is rising (Gini: 0.58)
Institutional trust: declining. Free media. Justice system is struggling.
```

### Information flow interaction

- In governments with `repression_level > 0.5`: public events created by agents critical of the government have a chance of being suppressed (not broadcast as "public", only spread as "rumor")
- In governments with controlled media (media.independence < 0.3): government can inject propaganda memories (positive hearsay about the head of state)

### Economy interaction

- Government type affects tax rate (agent wealth drain per tick). Democracies tax moderately, kleptocracies heavily, anarchies not at all.
- Corruption siphons wealth from poor to powerful agents

### New agent actions

- `"crime"`: steal from a target agent
- `"protest"`: express dissatisfaction publicly (creates public memory, affects popular_legitimacy)
- `"campaign"`: during election periods, increases the agent's vote score if they're a candidate

## Settings

```python
# --- Government and Political System ---
EPOCHA_GOVERNMENT_CYCLE_INTERVAL = env.int("EPOCHA_GOVERNMENT_CYCLE_INTERVAL", default=10)
EPOCHA_GOVERNMENT_ELECTION_INTERVAL = env.int("EPOCHA_GOVERNMENT_ELECTION_INTERVAL", default=50)
EPOCHA_GOVERNMENT_GINI_REVOLT_THRESHOLD = env.float("EPOCHA_GOVERNMENT_GINI_REVOLT_THRESHOLD", default=0.6)
EPOCHA_GOVERNMENT_COUP_STABILITY_THRESHOLD = env.float("EPOCHA_GOVERNMENT_COUP_STABILITY_THRESHOLD", default=0.3)
```

## Files

**New files:**

| File | Responsibility |
|------|---------------|
| `epocha/apps/world/government_types.py` | Data-driven config for 12 government types |
| `epocha/apps/world/government.py` | Government engine: indicators, transitions, coups |
| `epocha/apps/world/institutions.py` | Institution health dynamics |
| `epocha/apps/world/stratification.py` | Class mobility, Gini, crime, corruption |
| `epocha/apps/world/election.py` | Deterministic election system |
| `epocha/apps/world/tests/test_government.py` | Government engine tests |
| `epocha/apps/world/tests/test_institutions.py` | Institution tests |
| `epocha/apps/world/tests/test_stratification.py` | Stratification tests |
| `epocha/apps/world/tests/test_election.py` | Election tests |

**Modified files:**

| File | Change |
|------|--------|
| `epocha/apps/world/models.py` | Add Government, GovernmentHistory, Institution models |
| `epocha/apps/agents/decision.py` | Context enrichment with political info |
| `epocha/apps/simulation/engine.py` | Add process_political_cycle call + new action weights |
| `epocha/apps/simulation/tasks.py` | Add process_political_cycle in Celery path |
| `epocha/apps/dashboard/formatters.py` | Verbs for crime, protest, campaign |
| `config/settings/base.py` | Add EPOCHA_GOVERNMENT_* settings |

## Integration into Tick Engine

```
1. Economy
2. Agent decisions
3. Information flow
4. Faction dynamics (every 5 ticks)
5. >>> Political cycle (every 10 ticks) <<<
6. Memory decay
7. Advance tick
8. Broadcast
```

## Government Initialization

When a simulation starts, the world generator creates a Government with a type based on the simulation context (historical setting -> appropriate type, or default to "democracy"). All 7 institutions are created with health based on the government type defaults. This happens in the existing world generation pipeline.

## Computational Cost

With 20 agents, 4 factions, every 10 ticks:
- Institution health update: 7 institutions * simple formula = trivial
- Stratification: 1 Gini calculation + 20 class updates = trivial
- Indicator update: 5 indicators * formula = trivial
- Transition check: scan ~3-4 possible transitions = trivial
- Election (every 50 ticks): 20 agents * 4 candidates * score formula = ~80 calculations, no LLM
- Coup check: 1-2 checks per eligible faction = trivial
- Total: negligible compared to the 20 LLM calls for agent decisions

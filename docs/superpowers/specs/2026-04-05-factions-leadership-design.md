# Factions and Emergent Leadership -- Design Spec

## Goal

Activate the dormant Group model so that factions form organically from agent interactions, leaders emerge based on traits and social standing, and group cohesion evolves dynamically. This transforms isolated agents into an organized society capable of collective action.

## Architecture

A single new phase in the tick engine (`process_faction_dynamics`) runs every N ticks (default 5) and handles three responsibilities: cohesion updates, leadership verification, and new cluster detection. A separate affinity module computes pairwise agent similarity across personality, relationships, and circumstances.

No new models. The existing Group model (name, objective, cohesion, leader, parent_group) and Agent.group FK provide all the structure needed. One field added to Group: `formed_at_tick`.

## Faction Formation (Hybrid: Cluster Detection + LLM Context)

### Cluster Detection

Function `_detect_potential_factions(simulation, tick)` runs every faction dynamics tick for agents without a group.

**Affinity score** between two agents (computed in `affinity.py`):

```
affinity = personality_similarity * 0.3 + relationship_score * 0.3 + circumstance_score * 0.4
```

Where:

- **personality_similarity** (weight 0.3): 1 minus the normalized Euclidean distance of the Big Five traits (openness, conscientiousness, extraversion, agreeableness, neuroticism). If a trait is missing, default to 0.5.

```
distance = sqrt(sum((a[trait] - b[trait])^2 for trait in BIG_FIVE)) / sqrt(5)
similarity = 1.0 - distance
```

Source: the Euclidean distance on Big Five is a standard metric for personality similarity in personality psychology (McCrae & Costa, 2003. "Personality in Adulthood: A Five-Factor Theory Perspective." Guilford Press).

- **relationship_score** (weight 0.3): if a Relationship exists between the two agents, `(strength + max(0, sentiment)) / 2`. If no relationship exists, 0.0. Checked bidirectionally.

- **circumstance_score** (weight 0.4): sum of situational factors, capped at 1.0:
  - Same `social_class`: +0.3
  - Both have `mood < 0.4`: +0.2 (shared dissatisfaction is a strong binding force)
  - Share at least one "public" memory from the last 10 ticks: +0.2 (shared experience of the same event)
  - Both in the same wealth quartile within the simulation: +0.15
  - Remaining up to cap: +0.15 if both have the same `role`

Circumstances weigh more than personality because factions form around shared conditions, not shared temperaments. A desperate blacksmith and a desperate farmer have more reason to organize together than two cheerful people with similar personalities.

Source: collective action theory (Olson, 1965. "The Logic of Collective Action." Harvard University Press) emphasizes shared grievances and circumstances over personality similarity as drivers of group formation.

**Cluster identification**: a cluster forms when 3 or more groupless agents have pairwise affinity >= 0.5 (configurable via `EPOCHA_FACTION_AFFINITY_THRESHOLD`). The algorithm: for each ungrouped agent, find all ungrouped agents with affinity >= threshold. If 3+ form a connected subgraph (every pair has affinity >= threshold), they are a candidate cluster. Cap at 8 agents per cluster to keep factions manageable.

### Faction Activation

The system does not create the group directly. It adds a contextual note to the decision prompt of each agent in the detected cluster:

```
You share common ground with Elena (farmer) and Carlo (priest).
You have similar values and face similar circumstances.
You could organize together to pursue shared goals.
```

The agent decides in their next decision whether to choose "form_group" or "join_group". If at least 3 agents from the cluster choose one of these actions within the same tick, the Group is created.

### Group Creation

When the trigger fires:

- **name**: generated via a single LLM call, given the founders' roles, personalities, and circumstances. Example: "The Artisans' Guild" or "The Discontented".
- **objective**: generated in the same LLM call. Example: "Improve working conditions for craftsmen".
- **cohesion**: the average affinity of the founding cluster.
- **leader**: the founder with the highest leadership_score.
- **formed_at_tick**: the current tick.
- All founding agents get `Agent.group = new_group`.
- A "direct" memory is created for each founder: "I helped found [group name] with [other founders]."
- A "public" memory is broadcast to all agents in the simulation: "[Group name] has been formed by [founders], pursuing [objective]."

### Joining Existing Groups

Agents without a group can also join an already existing faction. Every faction dynamics tick, for each ungrouped agent, compute the average affinity with each existing group's members. If affinity >= threshold and the agent has at least one positive relationship (sentiment > 0) with a group member, the context suggests:

```
The [group name] shares your values and circumstances. [Member name] is a member.
You could join them by choosing "join_group".
```

If the agent chooses "join_group", they are added to the group. Their `Agent.group` is set, a memory is created ("I joined [group name]"), and group cohesion adjusts slightly downward (-0.02, new members need integration time).

## Emergent Leadership

### Leadership Score

Computed for every group member on each faction dynamics tick:

```
leadership_score = charisma * 0.3 + intelligence * 0.2 + wealth_rank * 0.15
                 + internal_sentiment * 0.2 + group_seniority * 0.15
```

Where:

- **charisma**: `Agent.charisma` (0.0-1.0), already present on the model.
- **intelligence**: `Agent.intelligence` (0.0-1.0), already present.
- **wealth_rank**: the agent's wealth position within the group, normalized to 0.0-1.0. The wealthiest member gets 1.0, the poorest gets 0.0.
- **internal_sentiment**: average sentiment of relationships with other group members. If no relationships exist with other members, defaults to 0.3.
- **group_seniority**: `(tick - agent_join_tick) / (tick - group.formed_at_tick)`, capped at 1.0. Founders have maximum seniority. This models the advantage of being there from the start.

For seniority tracking, we use the tick when the agent's group was assigned. Since Agent.group is a simple FK with no timestamp, we track join_tick via a memory: when an agent joins a group, a memory is created with the tick. The seniority calculation reads the earliest "founded" or "joined" memory for that group.

### Leadership Contestation

The leader maintains their position as long as their legitimacy stays above 0.3:

```
legitimacy = group_cohesion * 0.4 + leader_internal_sentiment * 0.4 + leader_score_rank * 0.2
```

Where:

- **group_cohesion**: the Group.cohesion field (0.0-1.0).
- **leader_internal_sentiment**: average sentiment of relationships between the leader and other members.
- **leader_score_rank**: 1.0 if the leader has the highest leadership_score, decreasing proportionally if others rank higher. Specifically: `1.0 - (leader_rank - 1) / max(member_count - 1, 1)` where `leader_rank` is 1-indexed position by score.

If legitimacy drops below 0.3:
1. The member with the highest leadership_score becomes the new leader.
2. `Group.leader` is updated.
3. A memory is created for all members: "[Old leader] was replaced by [new leader] as leader of [group]."
4. Group cohesion drops by 0.05 (leadership transitions are destabilizing).

## Cohesion Dynamics

Every faction dynamics tick, cohesion evolves for each group:

```
delta_cohesion = (cooperation_ratio * 0.1) - (conflict_ratio * 0.15)
              - (size_penalty * 0.02) + (leader_effectiveness * 0.05)
```

Where:

- **cooperation_ratio**: proportion of "help" and "socialize" actions between group members out of all actions by group members in the last N ticks. Source: DecisionLog, filtered by agent pairs within the group.
- **conflict_ratio**: proportion of "argue" and "betray" actions between group members.
- **size_penalty**: `max(0, member_count - 5)`. Groups above 5 members lose cohesion faster. Source: Dunbar's layered social structure (Dunbar, 1993. "Coevolution of Neocortical Size, Group Size and Language in Humans." Behavioral and Brain Sciences, 16(4), 681-735) suggests that intimate group coordination degrades rapidly beyond 5-15 members.
- **leader_effectiveness**: `leader_legitimacy - 0.5`, so effective leaders stabilize (+) and ineffective ones destabilize (-).

Cohesion is clamped to [0.0, 1.0].

## Schism and Dissolution

### Dissolution

When `Group.cohesion < 0.2`:
- All members' `Agent.group` is set to None.
- The Group is kept in the database (historical record) but marked inactive (cohesion stays at the low value).
- A "public" memory is created for all members: "[Group name] has dissolved."

### Schism

Every faction dynamics tick, check for internal fractures:
1. For each group with 6+ members, compute the average sentiment between every pair of members.
2. If a subcluster of 3+ members has average sentiment toward the rest of the group below -0.2, and average sentiment within the subcluster above +0.2, a schism occurs.
3. A new Group is created with `parent_group` = the original group.
4. The new group's name and objective are generated via LLM (1 call).
5. Schism members move to the new group.
6. Original group's cohesion drops by 0.1.
7. Memories created for both groups.

## Decision Pipeline Integration

### New Actions

Add "form_group" and "join_group" to the possible actions in `_DECISION_SYSTEM_PROMPT`:

```
"action": "work|rest|socialize|explore|trade|argue|help|avoid|form_group|join_group",
```

"form_group" and "join_group" are treated as social actions with emotional_weight 0.3 (same as "help").

### Context Enrichment

`_build_context` in `decision.py` is enhanced with group information:

**If the agent has a group:**
```
Your faction: [name] (objective: [objective])
Leader: [leader name]
Members: [member names and roles]
Group cohesion: [cohesion level as word: strong/moderate/fragile]
```

**If the agent has no group but a cluster was detected:**
```
You share common ground with [names]. You have similar values and face similar circumstances.
You could organize together to pursue shared goals.
Available actions include "form_group" to organize with like-minded people.
```

### Action Consequences

In `apply_agent_action` (engine.py):
- "form_group" and "join_group" don't have immediate mechanical effects (mood/health). The faction dynamics phase handles the actual group creation.
- They create a memory: "I decided to form_group" / "I decided to join_group" with emotional_weight 0.3.

The faction dynamics phase reads these memories to determine which agents want to form/join groups.

## Integration into Tick Engine

```
1. Economy
2. Agent decisions + apply_agent_action
3. Information flow
4. >>> Faction dynamics (every N ticks) <<<
5. Memory decay
6. Advance tick
7. Broadcast
```

A single function call: `process_faction_dynamics(simulation, tick)`. Runs only when `tick % EPOCHA_FACTION_DYNAMICS_INTERVAL == 0` (default 5). On non-faction ticks, it is a no-op.

## Settings

```python
# --- Faction Dynamics ---
# How often faction dynamics run (every N ticks).
EPOCHA_FACTION_DYNAMICS_INTERVAL = env.int("EPOCHA_FACTION_DYNAMICS_INTERVAL", default=5)

# Minimum pairwise affinity for agents to be considered a potential faction cluster.
EPOCHA_FACTION_AFFINITY_THRESHOLD = env.float("EPOCHA_FACTION_AFFINITY_THRESHOLD", default=0.5)

# Minimum members required to form a faction.
EPOCHA_FACTION_MIN_MEMBERS = env.int("EPOCHA_FACTION_MIN_MEMBERS", default=3)

# Maximum members in a newly formed faction (prevents oversized initial groups).
EPOCHA_FACTION_MAX_INITIAL_MEMBERS = env.int("EPOCHA_FACTION_MAX_INITIAL_MEMBERS", default=8)

# Cohesion threshold below which a group dissolves.
EPOCHA_FACTION_DISSOLUTION_THRESHOLD = env.float("EPOCHA_FACTION_DISSOLUTION_THRESHOLD", default=0.2)

# Leadership legitimacy threshold below which the leader is replaced.
EPOCHA_FACTION_LEGITIMACY_THRESHOLD = env.float("EPOCHA_FACTION_LEGITIMACY_THRESHOLD", default=0.3)
```

## Files

**New files:**

| File | Responsibility |
|------|---------------|
| `epocha/apps/agents/factions.py` | process_faction_dynamics + cohesion, leadership, formation, schism |
| `epocha/apps/agents/affinity.py` | Pairwise affinity calculation (personality + relationships + circumstances) |
| `epocha/apps/agents/tests/test_factions.py` | Faction dynamics tests |
| `epocha/apps/agents/tests/test_affinity.py` | Affinity calculation tests |

**Modified files:**

| File | Change |
|------|--------|
| `epocha/apps/agents/models.py` | Add `formed_at_tick` to Group |
| `epocha/apps/agents/decision.py` | Enrich context with group info, add form_group/join_group actions |
| `epocha/apps/simulation/engine.py` | Add process_faction_dynamics call, add form_group/join_group to action weights and mood deltas |
| `epocha/apps/simulation/tasks.py` | Add process_faction_dynamics call in Celery path |
| `config/settings/base.py` | Add EPOCHA_FACTION_* settings |

## What This Does NOT Cover

- Government systems (spec 2b)
- Institutions (spec 2c)
- Dynamic social stratification (spec 2d) -- uses existing Agent.social_class as-is
- Formal elections -- leadership is by score, not by vote
- Inter-faction diplomacy -- factions exist independently for now

## Computational Cost

With 20 agents, ~4 groups, every 5 ticks:
- Affinity calculation for ungrouped agents: ~10 pairs * 3 lookups = ~30 queries
- Cohesion update: ~4 groups * ~10 decision log queries = ~40 queries
- Leadership score: ~4 groups * ~5 members = ~20 score calculations
- LLM calls: 0-1 per faction dynamics tick (only on group creation or schism)
- Negligible compared to the 20 LLM calls per regular tick

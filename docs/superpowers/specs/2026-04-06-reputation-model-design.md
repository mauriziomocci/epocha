# Reputation Model (Castelfranchi-Conte-Paolucci) -- Design Spec

## Goal

Implement a scientifically rigorous reputation system based on the Castelfranchi-Conte-Paolucci model, distinguishing between direct evaluation (image) and social evaluation (reputation). Gossip propagates reputation even when the transmitting agent does not believe it, modeling real-world rumor dynamics.

## Scientific Foundation

- Castelfranchi, C., Conte, R. & Paolucci, M. (1998). "Normative reputation and the costs of compliance." Journal of Artificial Societies and Social Simulation, vol. 1, no. 3.
- Paolucci, M., Marsero, M. & Conte, R. (2000). "What is the use of Gossip? A sensitivity analysis of the spreading of respectful reputation." In Tools and Techniques for Social Science Simulation, Physica, Heidelberg, 302-314.

### Key Distinctions from the Paper

1. **Image vs Reputation**: image is what I know from direct experience; reputation is what I hear from others. An agent can have a positive image of someone but negative reputation (or vice versa).
2. **Gossip without belief**: an agent can transmit reputation information without personally believing it. "I heard Marco betrayed Elena" does not mean "I believe Marco betrayed Elena."
3. **Reputation influences behavior**: agents avoid cooperating with agents who have bad reputation (the "tabu" function from the paper), and trust information more from agents with good reputation.

## Model

New model `ReputationScore` in `epocha/apps/agents/models.py`:

```python
class ReputationScore(models.Model):
    """Per-agent perception of another agent's trustworthiness.

    Implements the Castelfranchi-Conte-Paolucci (1998) distinction between
    image (direct experience) and reputation (social evaluation via gossip).

    Each holder-target pair has one record. Image is updated from direct
    interactions; reputation is updated from hearsay and rumors received
    through the information flow system.
    """

    holder = models.ForeignKey(Agent, on_delete=models.CASCADE, related_name="reputation_assessments")
    target = models.ForeignKey(Agent, on_delete=models.CASCADE, related_name="reputation_scores")
    image = models.FloatField(default=0.0, help_text="-1.0 = terrible, 0.0 = neutral, 1.0 = excellent (direct experience)")
    reputation = models.FloatField(default=0.0, help_text="-1.0 = terrible, 0.0 = neutral, 1.0 = excellent (social evaluation)")
    last_updated_tick = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ["holder", "target"]

    def __str__(self):
        return f"{self.holder.name}'s view of {self.target.name}: img={self.image:.2f} rep={self.reputation:.2f}"
```

## Reputation Operations

New module `epocha/apps/agents/reputation.py` with:

### update_image(holder, target, action_type, tick)

Called when `holder` directly interacts with `target` (in `apply_agent_action`). Updates the image component based on the interaction type.

```
image_deltas = {
    "help": +0.15,
    "socialize": +0.1,
    "trade": +0.05,
    "argue": -0.2,
    "betray": -0.8,
    "avoid": -0.05,
}
```

These deltas match `INTERACTION_EFFECTS` in `relationships.py` for consistency. Image is clamped to [-1.0, 1.0].

Source: the delta magnitudes follow the principle that negative events have stronger impact than positive ones (Baumeister et al., 2001. "Bad is Stronger than Good." Review of General Psychology, 5(4), 323-370).

### update_reputation(holder, target, action_sentiment, reliability, tick)

Called when `holder` receives hearsay/rumor about `target` via the information flow. Updates the reputation component.

```
delta = action_sentiment * reliability * 0.5
reputation = clamp(reputation + delta, -1.0, 1.0)
```

Where `action_sentiment` is derived from the action type mentioned in the hearsay content:
- "helped", "saved", "protected" -> +1.0
- "socialize", "traded" -> +0.5
- "argued" -> -0.5
- "betrayed", "attacked", "stole" -> -1.0

The `reliability` factor means that third-hand rumors (low reliability) have less impact on reputation than first-hand hearsay.

### get_combined_score(holder, target) -> float

Returns a combined score used by the belief filter and decisions:

```
combined = image * 0.6 + reputation * 0.4
```

Image weighs more because direct experience is more reliable than hearsay. Source: Castelfranchi et al. (1998) Section 4.2 discusses the primacy of direct experience over social evaluation.

## Information Flow Changes

### Propagation Without Belief

The `_propagate_memory` function in `information_flow.py` is modified to separate information propagation from belief:

**Current behavior:**
1. Distort content
2. Apply belief filter
3. If rejected -> stop (information dies)
4. If accepted -> create memory

**New behavior:**
1. Distort content
2. Extract target agent and action sentiment from content
3. Update reputation of target agent (always, regardless of belief)
4. Apply belief filter
5. If accepted -> create memory (full hearsay/rumor, as before)
6. If rejected -> create a "weak rumor" memory with `reliability = original * 0.3` and `emotional_weight = 0.1`

The weak rumor is too weak to appear in `get_relevant_memories` (which ranks by emotional_weight), so it does not influence the agent's decisions. But it exists in the database and can be picked up by the propagation engine in the next tick, allowing the gossip to continue spreading even through agents who don't believe it.

This models the paper's key insight: "I don't believe Marco betrayed Elena, but I'll tell Carlo what I heard."

### Extracting Action Sentiment from Content

A helper function `extract_action_sentiment(content: str) -> tuple[str | None, float]` scans the memory content for action keywords and returns (target_name, sentiment):

```python
_POSITIVE_ACTIONS = {"helped": 1.0, "saved": 1.0, "protected": 1.0, "socialized": 0.5, "traded": 0.5}
_NEGATIVE_ACTIONS = {"betrayed": -1.0, "attacked": -1.0, "stole": -1.0, "argued": -0.5, "fought": -0.7}
```

The target name is extracted from the `origin_agent` field on the memory (already tracked by the information flow system). This avoids fragile text parsing for the target.

## Belief Filter Changes

The belief filter formula in `belief.py` gains a new component: transmitter reputation.

**Current formula:**
```
score = reliability * 0.4 + relationship_trust * 0.3 + personality_factor * 0.3
```

**New formula:**
```
score = reliability * 0.3 + relationship_trust * 0.2 + personality_factor * 0.2 + transmitter_reputation * 0.3
```

Where `transmitter_reputation` is the combined score (image + reputation) that the receiver holds for the transmitter. If no ReputationScore exists, defaults to 0.5 (neutral).

The threshold remains 0.4.

Source: the weight of reputation in information evaluation is a core thesis of Castelfranchi et al. (1998) -- agents use the reputation of the source to evaluate the credibility of information.

## Decision Pipeline Changes

`_build_context` in `decision.py` adds reputation information to the agent's context:

```
Reputation in your community:
- Cesare Borgia: respected (others speak well of him)
- Cardinale Rivale: mistrusted (bad reputation among your contacts)
```

Only agents with extreme reputation (combined score > 0.3 or < -0.3) are listed, to avoid clutter. The reputation word is derived from the combined score:
- > 0.5: "highly respected"
- > 0.3: "respected"
- < -0.3: "mistrusted"
- < -0.5: "despised"

This is the "tabu" function from the paper: the agent sees who has good/bad reputation and can factor it into decisions. The LLM will naturally avoid cooperating with mistrusted agents and seek out respected ones.

## Election Changes

In `election.py`, replace `_memory_influence(voter, candidate, tick)` with reputation:

```
reputation_score = get_combined_score(voter, candidate)
# Normalize from [-1, 1] to [0, 1]
reputation_factor = (reputation_score + 1.0) / 2.0
```

This replaces the memory keyword scanning with a cleaner, pre-computed value. The weight in the vote formula stays at 0.25.

## Graph Visualization Changes

In `graph_data_view`, add `avg_reputation` to each node:

```python
# Average reputation score across all holders for this agent
from django.db.models import Avg
avg_rep = ReputationScore.objects.filter(target=agent).aggregate(avg=Avg("reputation"))
node["avg_reputation"] = round(avg_rep["avg"] or 0.0, 2)
```

In the graph template, the node border color reflects reputation:
- avg_reputation > 0.3: green border (#22c55e)
- avg_reputation < -0.3: red border (#ef4444)
- Otherwise: no special border (as now)

## Engine Integration

In `apply_agent_action` (engine.py), after the existing `update_relationship_from_interaction` call, add:

```python
if target_agent:
    from epocha.apps.agents.reputation import update_image
    update_image(agent, target_agent, action_type, tick)
```

No other engine changes needed -- the reputation from hearsay is updated inside the information flow propagation, which already runs every tick.

## Files

**New files:**

| File | Responsibility |
|------|---------------|
| `epocha/apps/agents/reputation.py` | update_image, update_reputation, get_combined_score, extract_action_sentiment |
| `epocha/apps/agents/tests/test_reputation.py` | Reputation model + operations tests |

**Modified files:**

| File | Change |
|------|--------|
| `epocha/apps/agents/models.py` | Add ReputationScore model |
| `epocha/apps/agents/belief.py` | Add transmitter_reputation to formula |
| `epocha/apps/agents/information_flow.py` | Propagation without belief + reputation update |
| `epocha/apps/agents/decision.py` | Add reputation context |
| `epocha/apps/world/election.py` | Replace _memory_influence with reputation |
| `epocha/apps/simulation/engine.py` | Add update_image call |
| `epocha/apps/dashboard/views.py` | Add avg_reputation to graph nodes |

## What Does NOT Change

- Distortion engine (distorts content text, not reputation scores)
- Faction system (uses affinity based on personality/relationships/circumstances)
- Government system (uses aggregate indicators, not individual reputation)
- Simulation snapshots (reputation is per-pair, not an aggregate KPI)
- Memory model (memories still exist; reputation is a separate cognitive layer)

## Performance

- ReputationScore: N*N records max (20 agents = 400, 50 = 2500). Created on demand (only when agents interact or hear about each other).
- update_reputation in propagation: one get_or_create per recipient per propagated memory. With ~15-30 propagations per tick, this is ~15-30 queries. Trivial.
- get_combined_score: single DB lookup. Cached per tick if needed (not needed at MVP scale).
- Graph avg_reputation: one aggregate query per node. For 20 nodes = 20 queries. Could be optimized to 1 query with annotation, but not needed at this scale.

# Reputation Model (Castelfranchi-Conte-Paolucci) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement a scientifically rigorous reputation system with image/reputation distinction, gossip propagation without belief, and integration into belief filter, decisions, elections, and graph visualization.

**Architecture:** Bottom-up: model + migration, then reputation operations module, then information flow refactor (propagation without belief + reputation updates), then belief filter update, then decision/election/graph integration. Each change is independently testable.

**Tech Stack:** Django ORM, pytest, no new dependencies

**Spec:** `docs/superpowers/specs/2026-04-06-reputation-model-design.md`

---

## File Structure

| File | Responsibility | New/Modify |
|------|---------------|------------|
| `epocha/apps/agents/models.py` | ReputationScore model | Modify |
| `epocha/apps/agents/reputation.py` | update_image, update_reputation, get_combined_score, extract_action_sentiment | New |
| `epocha/apps/agents/tests/test_reputation.py` | Reputation tests | New |
| `epocha/apps/agents/belief.py` | Add transmitter_reputation parameter | Modify |
| `epocha/apps/agents/tests/test_belief.py` | Update tests for new parameter | Modify |
| `epocha/apps/agents/information_flow.py` | Propagation without belief + reputation updates | Modify |
| `epocha/apps/agents/tests/test_information_flow.py` | Update/add tests | Modify |
| `epocha/apps/simulation/engine.py` | Add update_image call | Modify |
| `epocha/apps/agents/decision.py` | Add reputation context | Modify |
| `epocha/apps/world/election.py` | Replace _memory_influence with reputation | Modify |
| `epocha/apps/dashboard/views.py` | Add avg_reputation to graph nodes | Modify |

---

### Task 1: ReputationScore model + migration

**Files:**
- Modify: `epocha/apps/agents/models.py`
- Migration: `epocha/apps/agents/migrations/`

- [ ] **Step 1: Add ReputationScore model**

In `epocha/apps/agents/models.py`, after the DecisionLog class (end of file), add:

```python
class ReputationScore(models.Model):
    """Per-agent perception of another agent's trustworthiness.

    Implements the Castelfranchi-Conte-Paolucci (1998) distinction between
    image (direct experience) and reputation (social evaluation via gossip).

    Source: Castelfranchi, C., Conte, R. & Paolucci, M. (1998). "Normative
    reputation and the costs of compliance." Journal of Artificial Societies
    and Social Simulation, vol. 1, no. 3.
    """

    holder = models.ForeignKey(Agent, on_delete=models.CASCADE, related_name="reputation_assessments")
    target = models.ForeignKey(Agent, on_delete=models.CASCADE, related_name="reputation_scores")
    image = models.FloatField(default=0.0, help_text="-1.0 = terrible, 0.0 = neutral, 1.0 = excellent (direct experience)")
    reputation = models.FloatField(default=0.0, help_text="-1.0 = terrible, 0.0 = neutral, 1.0 = excellent (social evaluation)")
    last_updated_tick = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ["holder", "target"]
        indexes = [
            models.Index(fields=["holder", "target"], name="reputation_lookup_idx"),
        ]

    def __str__(self):
        return f"{self.holder.name}'s view of {self.target.name}: img={self.image:.2f} rep={self.reputation:.2f}"
```

- [ ] **Step 2: Generate and apply migration**

```bash
docker compose -f docker-compose.local.yml exec -T web python manage.py makemigrations agents --name reputation_score
docker compose -f docker-compose.local.yml exec -T web python manage.py migrate agents
```

- [ ] **Step 3: Run existing tests**

Run: `docker compose -f docker-compose.local.yml exec -T web pytest epocha/apps/agents/ -q`

- [ ] **Step 4: Commit**

```
feat(agents): add ReputationScore model for image/reputation distinction

CHANGE: Add ReputationScore model implementing the Castelfranchi-Conte-
Paolucci (1998) reputation framework. Each holder-target pair tracks
image (direct experience) and reputation (social evaluation) separately.
```

---

### Task 2: Reputation operations module

Pure functions for updating and querying reputation scores.

**Files:**
- Create: `epocha/apps/agents/reputation.py`
- Create: `epocha/apps/agents/tests/test_reputation.py`

- [ ] **Step 1: Write the failing tests**

Create `epocha/apps/agents/tests/test_reputation.py`:

```python
"""Tests for the reputation system (Castelfranchi-Conte-Paolucci model)."""
import pytest

from epocha.apps.agents.models import Agent, ReputationScore
from epocha.apps.agents.reputation import (
    extract_action_sentiment,
    get_combined_score,
    update_image,
    update_reputation,
)
from epocha.apps.simulation.models import Simulation
from epocha.apps.users.models import User
from epocha.apps.world.models import World


@pytest.fixture
def user(db):
    return User.objects.create_user(email="rep@epocha.dev", username="reptest", password="pass123")


@pytest.fixture
def simulation(user):
    return Simulation.objects.create(name="RepTest", seed=42, owner=user)


@pytest.fixture
def world(simulation):
    return World.objects.create(simulation=simulation)


@pytest.fixture
def marco(simulation):
    return Agent.objects.create(
        simulation=simulation, name="Marco", role="blacksmith",
        personality={"openness": 0.5, "conscientiousness": 0.5},
    )


@pytest.fixture
def elena(simulation):
    return Agent.objects.create(
        simulation=simulation, name="Elena", role="farmer",
        personality={"openness": 0.5, "conscientiousness": 0.5},
    )


@pytest.mark.django_db
class TestUpdateImage:
    def test_help_increases_image(self, marco, elena):
        update_image(holder=elena, target=marco, action_type="help", tick=5)
        score = ReputationScore.objects.get(holder=elena, target=marco)
        assert score.image > 0.0

    def test_betray_decreases_image(self, marco, elena):
        update_image(holder=elena, target=marco, action_type="betray", tick=5)
        score = ReputationScore.objects.get(holder=elena, target=marco)
        assert score.image < 0.0

    def test_image_clamped_to_range(self, marco, elena):
        for _ in range(20):
            update_image(holder=elena, target=marco, action_type="help", tick=5)
        score = ReputationScore.objects.get(holder=elena, target=marco)
        assert score.image <= 1.0

    def test_image_accumulates(self, marco, elena):
        update_image(holder=elena, target=marco, action_type="help", tick=5)
        update_image(holder=elena, target=marco, action_type="help", tick=6)
        score = ReputationScore.objects.get(holder=elena, target=marco)
        assert score.image > 0.15  # More than a single help delta


@pytest.mark.django_db
class TestUpdateReputation:
    def test_positive_hearsay_increases_reputation(self, marco, elena):
        update_reputation(holder=elena, target=marco, action_sentiment=1.0, reliability=0.7, tick=5)
        score = ReputationScore.objects.get(holder=elena, target=marco)
        assert score.reputation > 0.0

    def test_negative_hearsay_decreases_reputation(self, marco, elena):
        update_reputation(holder=elena, target=marco, action_sentiment=-1.0, reliability=0.7, tick=5)
        score = ReputationScore.objects.get(holder=elena, target=marco)
        assert score.reputation < 0.0

    def test_low_reliability_has_less_impact(self, marco, elena):
        update_reputation(holder=elena, target=marco, action_sentiment=-1.0, reliability=0.1, tick=5)
        score_low = ReputationScore.objects.get(holder=elena, target=marco)
        score_low.delete()
        update_reputation(holder=elena, target=marco, action_sentiment=-1.0, reliability=0.9, tick=5)
        score_high = ReputationScore.objects.get(holder=elena, target=marco)
        assert abs(score_high.reputation) > abs(score_low.reputation)

    def test_reputation_does_not_change_image(self, marco, elena):
        update_reputation(holder=elena, target=marco, action_sentiment=-1.0, reliability=0.7, tick=5)
        score = ReputationScore.objects.get(holder=elena, target=marco)
        assert score.image == 0.0  # Image unchanged by hearsay


@pytest.mark.django_db
class TestGetCombinedScore:
    def test_combines_image_and_reputation(self, marco, elena):
        ReputationScore.objects.create(holder=elena, target=marco, image=0.5, reputation=-0.5)
        combined = get_combined_score(elena, marco)
        # image * 0.6 + reputation * 0.4 = 0.5*0.6 + (-0.5)*0.4 = 0.3 - 0.2 = 0.1
        assert abs(combined - 0.1) < 0.01

    def test_no_score_returns_zero(self, marco, elena):
        combined = get_combined_score(elena, marco)
        assert combined == 0.0

    def test_range_is_minus_one_to_one(self, marco, elena):
        ReputationScore.objects.create(holder=elena, target=marco, image=1.0, reputation=1.0)
        assert -1.0 <= get_combined_score(elena, marco) <= 1.0


class TestExtractActionSentiment:
    def test_helped_is_positive(self):
        sentiment = extract_action_sentiment("I decided to help. saved the village")
        assert sentiment > 0

    def test_betrayed_is_negative(self):
        sentiment = extract_action_sentiment("I decided to betray. power grab")
        assert sentiment < 0

    def test_neutral_content_returns_zero(self):
        sentiment = extract_action_sentiment("I decided to rest. tired")
        assert sentiment == 0.0

    def test_argued_is_mildly_negative(self):
        sentiment = extract_action_sentiment("I decided to argue. angry")
        assert -1.0 < sentiment < 0.0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `docker compose -f docker-compose.local.yml exec -T web pytest epocha/apps/agents/tests/test_reputation.py -v`

- [ ] **Step 3: Implement reputation operations**

Create `epocha/apps/agents/reputation.py`:

```python
"""Reputation operations -- image/reputation updates and queries.

Implements the Castelfranchi-Conte-Paolucci (1998) reputation model.
Image tracks direct experience; reputation tracks social evaluation
received through gossip (information flow).

Source: Castelfranchi, C., Conte, R. & Paolucci, M. (1998). "Normative
reputation and the costs of compliance." JASSS, vol. 1, no. 3.

Source: Baumeister, R. F. et al. (2001). "Bad is Stronger than Good."
Review of General Psychology, 5(4), 323-370. (Negative events have
stronger impact on image than positive ones.)
"""
from __future__ import annotations

from .models import Agent, ReputationScore

# Image deltas from direct interactions.
# Aligned with INTERACTION_EFFECTS in relationships.py for consistency.
_IMAGE_DELTAS: dict[str, float] = {
    "help": 0.15,
    "socialize": 0.1,
    "trade": 0.05,
    "work": 0.03,
    "argue": -0.2,
    "betray": -0.8,
    "avoid": -0.05,
    "crime": -0.6,
}

# Keywords and their sentiment for extracting action tone from memory content.
_POSITIVE_KEYWORDS: dict[str, float] = {
    "helped": 1.0,
    "help": 1.0,
    "saved": 1.0,
    "protected": 1.0,
    "socialized": 0.5,
    "socialize": 0.5,
    "traded": 0.5,
    "trade": 0.5,
    "founded": 0.3,
    "built": 0.3,
    "united": 0.3,
}

_NEGATIVE_KEYWORDS: dict[str, float] = {
    "betrayed": -1.0,
    "betray": -1.0,
    "attacked": -1.0,
    "stole": -1.0,
    "crime": -0.8,
    "argued": -0.5,
    "argue": -0.5,
    "fought": -0.7,
    "exploited": -0.8,
    "oppressed": -0.8,
    "destroyed": -1.0,
}


def update_image(holder: Agent, target: Agent, action_type: str, tick: int) -> None:
    """Update the image component from a direct interaction.

    Called when the holder directly interacts with the target (e.g. help,
    argue, betray). Positive interactions increase image, negative decrease it.

    Args:
        holder: The agent whose perception is updated.
        target: The agent being evaluated.
        action_type: The type of action (help, argue, betray, etc.).
        tick: Current simulation tick.
    """
    delta = _IMAGE_DELTAS.get(action_type, 0.0)
    if delta == 0.0:
        return

    score, _ = ReputationScore.objects.get_or_create(
        holder=holder, target=target,
        defaults={"last_updated_tick": tick},
    )
    score.image = max(-1.0, min(1.0, score.image + delta))
    score.last_updated_tick = tick
    score.save(update_fields=["image", "last_updated_tick"])


def update_reputation(
    holder: Agent, target: Agent, action_sentiment: float, reliability: float, tick: int,
) -> None:
    """Update the reputation component from received gossip.

    Called when the holder receives hearsay or rumor about the target.
    The update magnitude depends on the sentiment of the reported action
    and the reliability of the information.

    This updates reputation but NOT image -- the holder did not witness
    the action directly.

    Args:
        holder: The agent whose perception is updated.
        target: The agent being evaluated.
        action_sentiment: Sentiment of the reported action (-1.0 to 1.0).
        reliability: Reliability of the information (0.0-1.0).
        tick: Current simulation tick.
    """
    delta = action_sentiment * reliability * 0.5
    if abs(delta) < 0.001:
        return

    score, _ = ReputationScore.objects.get_or_create(
        holder=holder, target=target,
        defaults={"last_updated_tick": tick},
    )
    score.reputation = max(-1.0, min(1.0, score.reputation + delta))
    score.last_updated_tick = tick
    score.save(update_fields=["reputation", "last_updated_tick"])


def get_combined_score(holder: Agent, target: Agent) -> float:
    """Return the combined image+reputation score.

    Image weighs 60% (direct experience is more trusted), reputation 40%.
    Returns 0.0 if no ReputationScore exists.

    Source: Castelfranchi et al. (1998) Section 4.2 discusses the primacy
    of direct experience over social evaluation.
    """
    try:
        score = ReputationScore.objects.get(holder=holder, target=target)
        return score.image * 0.6 + score.reputation * 0.4
    except ReputationScore.DoesNotExist:
        return 0.0


def extract_action_sentiment(content: str) -> float:
    """Extract the sentiment of an action from memory content.

    Scans the content for positive and negative action keywords and
    returns the strongest match. Returns 0.0 if no keywords match.

    Args:
        content: The memory content text.

    Returns:
        Sentiment value from -1.0 (very negative) to 1.0 (very positive).
    """
    content_lower = content.lower()
    best_sentiment = 0.0

    for keyword, sentiment in _NEGATIVE_KEYWORDS.items():
        if keyword in content_lower:
            if abs(sentiment) > abs(best_sentiment):
                best_sentiment = sentiment

    for keyword, sentiment in _POSITIVE_KEYWORDS.items():
        if keyword in content_lower:
            if abs(sentiment) > abs(best_sentiment):
                best_sentiment = sentiment

    return best_sentiment
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `docker compose -f docker-compose.local.yml exec -T web pytest epocha/apps/agents/tests/test_reputation.py -v`
Expected: All tests PASS.

- [ ] **Step 5: Commit**

```
feat(agents): add reputation operations module

CHANGE: Implement update_image (direct experience), update_reputation
(social evaluation from gossip), get_combined_score (weighted mix), and
extract_action_sentiment (keyword analysis). Image deltas aligned with
relationship interaction effects. Reputation updates weighted by
information reliability.
```

---

### Task 3: Belief filter -- add transmitter reputation

Update the belief filter to include the transmitter's reputation as a factor.

**Files:**
- Modify: `epocha/apps/agents/belief.py`
- Modify: `epocha/apps/agents/tests/test_belief.py`

- [ ] **Step 1: Update the belief filter function**

In `epocha/apps/agents/belief.py`, change the `should_believe` signature and formula:

```python
def should_believe(
    reliability: float,
    receiver_personality: dict,
    relationship_strength: float,
    relationship_sentiment: float,
    transmitter_reputation: float = 0.0,
) -> bool:
    """Determine whether an agent accepts a piece of incoming information.

    The acceptance score is a weighted sum of four factors:
    - Information reliability (30%): inherent quality of the information
    - Relationship trust (20%): how much the receiver trusts the transmitter
    - Personality factor (20%): receiver's disposition toward credulity
    - Transmitter reputation (30%): social evaluation of the transmitter

    Source: Castelfranchi, Conte & Paolucci (1998) -- reputation of the
    source is a key factor in information evaluation.

    Args:
        reliability: Information reliability (0.0-1.0), degrades per hop.
        receiver_personality: Big Five personality dict of the receiving agent.
        relationship_strength: Strength of the relationship (0.0-1.0).
        relationship_sentiment: Sentiment toward the transmitter (-1.0 to 1.0).
        transmitter_reputation: Combined reputation score of the transmitter
            as perceived by the receiver (-1.0 to 1.0). Normalized to 0-1
            internally. Defaults to 0.0 (neutral) when no score exists.

    Returns:
        True if the agent accepts the information, False if they discard it.
    """
    relationship_trust = (relationship_strength + max(0.0, relationship_sentiment)) / 2.0

    agreeableness = receiver_personality.get("agreeableness", 0.5)
    openness = receiver_personality.get("openness", 0.5)
    personality_factor = agreeableness * 0.6 + openness * 0.4

    # Normalize reputation from [-1, 1] to [0, 1]
    reputation_factor = (transmitter_reputation + 1.0) / 2.0

    acceptance_score = (
        reliability * 0.3
        + relationship_trust * 0.2
        + personality_factor * 0.2
        + reputation_factor * 0.3
    )

    threshold = getattr(settings, "EPOCHA_INFO_FLOW_BELIEF_THRESHOLD", 0.4)
    return acceptance_score >= threshold
```

Update the module docstring to include the Castelfranchi reference.

- [ ] **Step 2: Update existing tests**

In `epocha/apps/agents/tests/test_belief.py`, update the existing test values. The new formula has different weights so some test assertions will break. Recalculate:

For `test_trusted_friend_fresh_hearsay_accepted` (reliability=0.7, rel_strength=0.8, rel_sentiment=0.8, personality=0.5, transmitter_reputation default 0.0):
- rel_trust = (0.8 + 0.8) / 2 = 0.8
- personality = 0.5
- reputation_factor = (0.0 + 1.0) / 2 = 0.5
- score = 0.7*0.3 + 0.8*0.2 + 0.5*0.2 + 0.5*0.3 = 0.21 + 0.16 + 0.10 + 0.15 = 0.62
Still passes (> 0.4).

For `test_stranger_third_hand_rumor_rejected` (reliability=0.3, rel_strength=0.0, rel_sentiment=0.0, personality=0.5):
- rel_trust = 0.0
- reputation_factor = 0.5
- score = 0.3*0.3 + 0.0*0.2 + 0.5*0.2 + 0.5*0.3 = 0.09 + 0.0 + 0.10 + 0.15 = 0.34
Still fails (< 0.4).

Most existing tests should still pass with default `transmitter_reputation=0.0`. Add two new tests:

```python
    def test_good_reputation_transmitter_more_credible(self):
        """Good reputation of the transmitter increases acceptance."""
        result_neutral = should_believe(
            reliability=0.4,
            receiver_personality={"agreeableness": 0.5, "openness": 0.5},
            relationship_strength=0.3,
            relationship_sentiment=0.0,
            transmitter_reputation=0.0,
        )
        result_good = should_believe(
            reliability=0.4,
            receiver_personality={"agreeableness": 0.5, "openness": 0.5},
            relationship_strength=0.3,
            relationship_sentiment=0.0,
            transmitter_reputation=0.8,
        )
        # Good reputation should make acceptance more likely
        assert result_good is True or result_good != result_neutral

    def test_bad_reputation_transmitter_less_credible(self):
        """Bad reputation of the transmitter decreases acceptance."""
        result = should_believe(
            reliability=0.5,
            receiver_personality={"agreeableness": 0.5, "openness": 0.5},
            relationship_strength=0.3,
            relationship_sentiment=0.0,
            transmitter_reputation=-0.8,
        )
        # reputation_factor = (-0.8 + 1) / 2 = 0.1
        # score = 0.5*0.3 + 0.15*0.2 + 0.5*0.2 + 0.1*0.3 = 0.15 + 0.03 + 0.10 + 0.03 = 0.31
        assert result is False
```

Recalculate `test_exact_threshold_is_accepted` and fix the input values to still produce exactly 0.4 with the new formula. With transmitter_reputation=0.0:
- Need: reliability*0.3 + rel_trust*0.2 + personality*0.2 + 0.5*0.3 = 0.4
- So: reliability*0.3 + rel_trust*0.2 + personality*0.2 = 0.25
- With all equal value X: X*0.3 + X*0.2 + X*0.2 = 0.25 -> X*0.7 = 0.25 -> X = 0.357
- Use reliability=0.357, rel_strength=0.357, rel_sentiment=0.357, personality agreeableness=0.357, openness=0.357

The implementer should recalculate and fix any tests that break due to the new weights.

- [ ] **Step 3: Run tests**

Run: `docker compose -f docker-compose.local.yml exec -T web pytest epocha/apps/agents/tests/test_belief.py -v`
Expected: All tests PASS.

- [ ] **Step 4: Commit**

```
feat(agents): add transmitter reputation to belief filter

CHANGE: The belief filter now weighs the transmitter's reputation (30%)
alongside reliability (30%), relationship trust (20%), and personality
(20%). Agents with good reputation are more credible; agents with bad
reputation are less trusted. Based on Castelfranchi et al. (1998).
```

---

### Task 4: Information flow -- propagation without belief + reputation updates

The critical refactor: gossip propagates even when belief filter rejects it, and reputation is updated on every reception.

**Files:**
- Modify: `epocha/apps/agents/information_flow.py`
- Modify: `epocha/apps/agents/tests/test_information_flow.py`

- [ ] **Step 1: Write new tests**

Add to `epocha/apps/agents/tests/test_information_flow.py`:

```python
    def test_reputation_updated_on_hearsay(self, simulation, world, marco, elena):
        """Receiving hearsay about an agent should update reputation score."""
        from epocha.apps.agents.models import ReputationScore
        Relationship.objects.create(
            agent_from=marco, agent_to=elena,
            relation_type="friendship", strength=0.7, sentiment=0.6, since_tick=0,
        )
        Memory.objects.create(
            agent=marco, content="I decided to betray. power grab",
            emotional_weight=0.8, source_type="direct", tick_created=5,
            origin_agent=marco,
        )
        propagate_information(simulation, tick=5)

        # Elena should have a reputation score for Marco
        scores = ReputationScore.objects.filter(holder=elena, target=marco)
        assert scores.exists()
        assert scores.first().reputation < 0  # Betrayal = negative reputation

    def test_gossip_propagates_without_belief(self, simulation, world, marco, elena, carlo):
        """Even when belief filter rejects, a weak rumor should be created for propagation."""
        elena.personality = {
            "openness": 0.1, "agreeableness": 0.1,  # very skeptical
        }
        elena.save(update_fields=["personality"])
        Relationship.objects.create(
            agent_from=marco, agent_to=elena,
            relation_type="distrust", strength=0.2, sentiment=-0.5, since_tick=0,
        )
        Relationship.objects.create(
            agent_from=elena, agent_to=carlo,
            relation_type="friendship", strength=0.7, sentiment=0.5, since_tick=0,
        )
        Memory.objects.create(
            agent=marco, content="I decided to betray. power grab",
            emotional_weight=0.8, source_type="direct", tick_created=5,
            origin_agent=marco,
        )

        propagate_information(simulation, tick=5)

        # Elena should reject the hearsay (skeptical + bad relationship)
        # But a weak rumor should still exist for propagation
        elena_memories = Memory.objects.filter(agent=elena, source_type__in=["hearsay", "rumor"])
        # There should be at least a weak rumor (low reliability, low emotional weight)
        weak_rumors = elena_memories.filter(emotional_weight__lte=0.15)
        assert weak_rumors.exists() or elena_memories.exists()

        # Reputation should still be updated (even without belief)
        from epocha.apps.agents.models import ReputationScore
        rep = ReputationScore.objects.filter(holder=elena, target=marco)
        assert rep.exists()
```

- [ ] **Step 2: Modify _propagate_memory in information_flow.py**

The key change to the `_propagate_memory` function. After the distortion and before the belief filter check, add reputation update. Replace the belief filter block with:

```python
        # Extract action sentiment for reputation update
        from epocha.apps.agents.reputation import (
            extract_action_sentiment,
            get_combined_score,
            update_reputation,
        )

        action_sentiment = extract_action_sentiment(distorted_content)

        # Always update reputation (even if belief filter rejects)
        if origin and action_sentiment != 0.0:
            update_reputation(
                holder=recipient,
                target=origin,
                action_sentiment=action_sentiment,
                reliability=new_reliability,
                tick=tick,
            )

        # Get transmitter reputation for belief filter
        transmitter_rep = get_combined_score(recipient, transmitter)

        # Belief filter (now includes transmitter reputation)
        believed = should_believe(
            reliability=new_reliability,
            receiver_personality=recipient.personality,
            relationship_strength=rel_strength,
            relationship_sentiment=rel_sentiment,
            transmitter_reputation=transmitter_rep,
        )

        if believed:
            # Full memory creation (as before)
            Memory.objects.create(
                agent=recipient,
                content=distorted_content,
                emotional_weight=memory.emotional_weight,
                source_type=target_source_type,
                reliability=new_reliability,
                tick_created=tick,
                origin_agent=origin,
            )
        else:
            # Weak rumor: the agent does not believe it but may pass it on
            # Low emotional_weight ensures it does not influence decisions
            # Low reliability ensures it has minimal impact if propagated further
            Memory.objects.create(
                agent=recipient,
                content=distorted_content,
                emotional_weight=0.1,
                source_type=Memory.SourceType.RUMOR,
                reliability=new_reliability * 0.3,
                tick_created=tick,
                origin_agent=origin,
            )

        already_informed.add(recipient.pk)
        recipients_created += 1
```

Also update the import at the top of information_flow.py to remove the direct `should_believe` import and add the reputation imports.

- [ ] **Step 3: Run tests**

Run: `docker compose -f docker-compose.local.yml exec -T web pytest epocha/apps/agents/tests/test_information_flow.py -v`
Expected: All tests PASS.

- [ ] **Step 4: Run full test suite**

Run: `docker compose -f docker-compose.local.yml exec -T web pytest --reuse-db -q`
Expected: All pass (some existing belief filter tests may need adjustment due to new parameter).

- [ ] **Step 5: Commit**

```
feat(agents): propagation without belief and reputation updates in info flow

CHANGE: The information flow now updates reputation scores on every
reception (regardless of belief). When the belief filter rejects an
information, a weak rumor is still created for further propagation.
This models the Castelfranchi-Conte-Paolucci insight that agents
transmit gossip they do not personally believe.
```

---

### Task 5: Engine integration -- update_image on direct interaction

**Files:**
- Modify: `epocha/apps/simulation/engine.py`

- [ ] **Step 1: Add update_image call**

In `apply_agent_action` in engine.py, after the existing `update_relationship_from_interaction` call (line ~125), add:

```python
            from epocha.apps.agents.reputation import update_image
            update_image(holder=agent, target=target_agent, action_type=action_type, tick=tick)
```

The block becomes:
```python
        if target_agent:
            update_relationship_from_interaction(agent, target_agent, action_type, tick)
            from epocha.apps.agents.reputation import update_image
            update_image(holder=agent, target=target_agent, action_type=action_type, tick=tick)
```

- [ ] **Step 2: Run tests**

Run: `docker compose -f docker-compose.local.yml exec -T web pytest epocha/apps/simulation/tests/test_engine.py --reuse-db -v`

- [ ] **Step 3: Commit**

```
feat(simulation): update agent image on direct interactions

CHANGE: Call update_image in apply_agent_action when an action targets
another agent. This builds the direct experience (image) component of
the reputation model alongside the existing relationship update.
```

---

### Task 6: Decision context + election + graph integration

Add reputation info to decision context, replace memory-based vote scoring with reputation, and add avg_reputation to graph nodes.

**Files:**
- Modify: `epocha/apps/agents/decision.py`
- Modify: `epocha/apps/world/election.py`
- Modify: `epocha/apps/dashboard/views.py`

- [ ] **Step 1: Add reputation context to decisions**

In `epocha/apps/agents/decision.py`, in `process_agent_decision`, after the political_context block, add:

```python
    # Build reputation context
    reputation_context = None
    try:
        from epocha.apps.agents.reputation import get_combined_score
        from epocha.apps.agents.models import ReputationScore
        # Get agents with notable reputation from this agent's perspective
        notable = ReputationScore.objects.filter(
            holder=agent,
        ).select_related("target").exclude(target=agent)
        rep_lines = []
        for rep in notable:
            combined = rep.image * 0.6 + rep.reputation * 0.4
            if combined > 0.3:
                word = "highly respected" if combined > 0.5 else "respected"
                rep_lines.append(f"- {rep.target.name}: {word}")
            elif combined < -0.3:
                word = "despised" if combined < -0.5 else "mistrusted"
                rep_lines.append(f"- {rep.target.name}: {word}")
        if rep_lines:
            reputation_context = "Reputation in your community:\n" + "\n".join(rep_lines)
    except Exception:
        pass
```

Add `reputation_context=None` to `_build_context` signature (after `political_context`) and add the block:
```python
    # Reputation context
    if reputation_context:
        parts.append(f"\n{reputation_context}")
```

Pass `reputation_context` to `_build_context`.

- [ ] **Step 2: Update election vote scoring**

In `epocha/apps/world/election.py`, replace the `_memory_influence` call in `compute_vote_score` with reputation:

```python
    from epocha.apps.agents.reputation import get_combined_score
    reputation_raw = get_combined_score(voter, candidate)
    reputation_factor = (reputation_raw + 1.0) / 2.0  # Normalize to 0-1
```

Change the formula to use `reputation_factor` instead of `memory_score`:
```python
    score = (
        rel_score * 0.25
        + personality_score * 0.15
        + economy_score * 0.20
        + reputation_factor * 0.25
        + charisma_score * 0.15
    )
```

- [ ] **Step 3: Add avg_reputation to graph nodes**

In `epocha/apps/dashboard/views.py`, in `graph_data_view`, after building each node dict, add:

```python
from django.db.models import Avg
from epocha.apps.agents.models import ReputationScore
```

And in the node building loop, add:
```python
            avg_rep = ReputationScore.objects.filter(target=agent).aggregate(
                avg_rep=Avg("reputation")
            )["avg_rep"] or 0.0
```

Add to the node dict:
```python
            "avg_reputation": round(avg_rep, 2),
```

- [ ] **Step 4: Run all tests**

Run: `docker compose -f docker-compose.local.yml exec -T web pytest --reuse-db -q`

- [ ] **Step 5: Commit**

```
feat(agents): integrate reputation into decisions, elections, and graph

CHANGE: Decision context now shows notable reputations (respected/mistrusted).
Elections use reputation scores instead of memory keyword scanning.
Graph nodes include avg_reputation for visual reputation indicators.
```

---

### Task 7: Run full test suite + push

- [ ] **Step 1: Run full test suite**

Run: `docker compose -f docker-compose.local.yml exec -T web pytest --reuse-db -q`
Expected: All pass.

- [ ] **Step 2: Push**

```bash
git push origin develop
```

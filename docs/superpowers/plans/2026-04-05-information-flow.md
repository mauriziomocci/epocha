# Information Flow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the information flow system so that agent actions propagate through the social network with delay, rule-based distortion, and personality-based filtering.

**Architecture:** Three independent modules (belief filter, distortion engine, propagation engine) built bottom-up with TDD. The propagation engine runs once per tick after agent decisions, creating hearsay/rumor Memory objects that feed naturally into the existing decision pipeline. One new FK field on Memory (`origin_agent`) for deduplication.

**Tech Stack:** Django ORM, pytest, no new dependencies

**Spec:** `docs/superpowers/specs/2026-04-05-information-flow-design.md`

---

## File Structure

| File | Responsibility | New/Modify |
|------|---------------|------------|
| `epocha/apps/agents/belief.py` | Belief filter: should an agent accept information? | New |
| `epocha/apps/agents/distortion.py` | Rule-based distortion engine | New |
| `epocha/apps/agents/information_flow.py` | Propagation engine (1 hop per tick) | New |
| `epocha/apps/agents/tests/test_belief.py` | Belief filter tests | New |
| `epocha/apps/agents/tests/test_distortion.py` | Distortion engine tests | New |
| `epocha/apps/agents/tests/test_information_flow.py` | Propagation integration tests | New |
| `epocha/apps/agents/models.py:87-114` | Add `origin_agent` FK to Memory | Modify |
| `epocha/apps/simulation/engine.py:237-238` | Add propagation call in tick | Modify |
| `epocha/apps/simulation/tasks.py:97-98` | Add propagation call in Celery finalize_tick | Modify |
| `config/settings/base.py:148` | Add EPOCHA_INFO_FLOW_* settings | Modify |

---

### Task 1: Settings and Memory model migration

Add the information flow settings to `base.py` and the `origin_agent` FK to the Memory model.

**Files:**
- Modify: `config/settings/base.py:148`
- Modify: `epocha/apps/agents/models.py:87-114`
- Migration: `epocha/apps/agents/migrations/`

- [ ] **Step 1: Add settings to base.py**

At the end of `config/settings/base.py`, after `EPOCHA_DEFAULT_TICK_INTERVAL_SECONDS`, add:

```python
# --- Information Flow ---
# Minimum emotional weight for an action to propagate through the social network.
# Actions below this threshold are considered too mundane for gossip.
# Source: threshold aligns with _ACTION_EMOTIONAL_WEIGHT in engine.py where
# socialize=0.2 (excluded) and help=0.3 (included).
EPOCHA_INFO_FLOW_PROPAGATION_THRESHOLD = env.float("EPOCHA_INFO_FLOW_PROPAGATION_THRESHOLD", default=0.3)

# Reliability decay factor per hop in the communication chain.
# Source: Bartlett (1932) serial reproduction experiments show ~30% detail loss per step.
EPOCHA_INFO_FLOW_RELIABILITY_DECAY = env.float("EPOCHA_INFO_FLOW_RELIABILITY_DECAY", default=0.7)

# Maximum hops before information stops propagating.
EPOCHA_INFO_FLOW_MAX_HOPS = env.int("EPOCHA_INFO_FLOW_MAX_HOPS", default=3)

# Belief filter acceptance threshold (0.0-1.0).
EPOCHA_INFO_FLOW_BELIEF_THRESHOLD = env.float("EPOCHA_INFO_FLOW_BELIEF_THRESHOLD", default=0.4)

# Maximum recipients per memory per tick (prevents unbounded fan-out).
EPOCHA_INFO_FLOW_MAX_RECIPIENTS = env.int("EPOCHA_INFO_FLOW_MAX_RECIPIENTS", default=20)
```

- [ ] **Step 2: Add origin_agent FK to Memory model**

In `epocha/apps/agents/models.py`, in the Memory class, after the `is_active` field (line 102), add:

```python
    origin_agent = models.ForeignKey(
        "Agent", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="originated_memories",
        help_text="Agent who originally performed the action (for dedup and traceability)",
    )
```

Also add an index for the propagation dedup query. Update the Meta.indexes to:

```python
    class Meta:
        ordering = ["-emotional_weight", "-tick_created"]
        indexes = [
            models.Index(
                fields=["agent", "is_active", "-tick_created"],
                name="memory_dedup_idx",
            ),
            models.Index(
                fields=["origin_agent", "tick_created", "source_type"],
                name="memory_propagation_idx",
            ),
        ]
```

- [ ] **Step 3: Generate and apply migration**

Run:
```bash
docker compose -f docker-compose.local.yml exec -T web python manage.py makemigrations agents --name memory_origin_agent
docker compose -f docker-compose.local.yml exec -T web python manage.py migrate agents
```

Expected: migration created and applied successfully.

- [ ] **Step 4: Run existing tests to verify no breakage**

Run: `docker compose -f docker-compose.local.yml exec -T web pytest epocha/apps/agents/ epocha/apps/simulation/ -v`
Expected: All existing tests PASS (origin_agent is nullable, so no existing code breaks).

- [ ] **Step 5: Commit**

```
feat(agents): add origin_agent field and info flow settings

CHANGE: Add origin_agent FK to Memory for tracking who originally
performed an action across hearsay/rumor chains. Add EPOCHA_INFO_FLOW_*
settings for propagation threshold, reliability decay, max hops, belief
threshold, and max recipients per tick.
```

---

### Task 2: Belief Filter

Pure function that decides whether an agent accepts or discards incoming information. No DB access, no side effects.

**Files:**
- Create: `epocha/apps/agents/belief.py`
- Create: `epocha/apps/agents/tests/test_belief.py`

- [ ] **Step 1: Write the failing tests**

Create `epocha/apps/agents/tests/test_belief.py`:

```python
"""Tests for the belief filter — decides whether an agent accepts incoming information."""
from epocha.apps.agents.belief import should_believe


class TestShouldBelieve:
    def test_trusted_friend_fresh_hearsay_accepted(self):
        """High reliability + strong relationship + average personality = accept."""
        result = should_believe(
            reliability=0.7,
            receiver_personality={"agreeableness": 0.5, "openness": 0.5},
            relationship_strength=0.8,
            relationship_sentiment=0.8,
        )
        assert result is True

    def test_stranger_third_hand_rumor_rejected(self):
        """Low reliability + no relationship + average personality = reject."""
        result = should_believe(
            reliability=0.3,
            receiver_personality={"agreeableness": 0.5, "openness": 0.5},
            relationship_strength=0.0,
            relationship_sentiment=0.0,
        )
        assert result is False

    def test_weak_rumor_gullible_agent_accepted(self):
        """Low reliability but very agreeable/open agent = accept."""
        result = should_believe(
            reliability=0.3,
            receiver_personality={"agreeableness": 0.9, "openness": 0.9},
            relationship_strength=0.3,
            relationship_sentiment=0.3,
        )
        assert result is True

    def test_reliable_news_skeptical_agent_accepted(self):
        """High reliability overcomes low personality factor."""
        result = should_believe(
            reliability=0.7,
            receiver_personality={"agreeableness": 0.2, "openness": 0.2},
            relationship_strength=0.5,
            relationship_sentiment=0.5,
        )
        assert result is True

    def test_no_relationship_uses_default_trust(self):
        """When strength and sentiment are both 0, trust defaults to stranger level."""
        # stranger trust = (0.0 + max(0, 0.0)) / 2 = 0.0
        # This should still work -- the formula handles it
        result = should_believe(
            reliability=0.5,
            receiver_personality={"agreeableness": 0.5, "openness": 0.5},
            relationship_strength=0.0,
            relationship_sentiment=0.0,
        )
        # score = 0.5*0.4 + 0.0*0.3 + 0.5*0.3 = 0.20 + 0.0 + 0.15 = 0.35
        assert result is False

    def test_missing_personality_traits_use_defaults(self):
        """If personality dict is missing Big Five traits, defaults to 0.5."""
        result = should_believe(
            reliability=0.7,
            receiver_personality={},
            relationship_strength=0.5,
            relationship_sentiment=0.5,
        )
        # personality_factor = 0.5*0.6 + 0.5*0.4 = 0.5
        # rel_trust = (0.5 + 0.5) / 2 = 0.5
        # score = 0.7*0.4 + 0.5*0.3 + 0.5*0.3 = 0.28 + 0.15 + 0.15 = 0.58
        assert result is True

    def test_negative_sentiment_clamped_to_zero(self):
        """Negative sentiment should not increase trust (clamped to 0)."""
        result = should_believe(
            reliability=0.3,
            receiver_personality={"agreeableness": 0.5, "openness": 0.5},
            relationship_strength=0.5,
            relationship_sentiment=-0.8,
        )
        # rel_trust = (0.5 + max(0, -0.8)) / 2 = 0.5 / 2 = 0.25
        # score = 0.3*0.4 + 0.25*0.3 + 0.5*0.3 = 0.12 + 0.075 + 0.15 = 0.345
        assert result is False

    def test_exact_threshold_is_accepted(self):
        """Score exactly at threshold should be accepted (>=, not >)."""
        # We need score = 0.4 exactly
        # reliability=0.4, rel_trust=0.4, personality=0.4
        # score = 0.4*0.4 + 0.4*0.3 + 0.4*0.3 = 0.16 + 0.12 + 0.12 = 0.40
        result = should_believe(
            reliability=0.4,
            receiver_personality={"agreeableness": 0.4, "openness": 0.4},
            relationship_strength=0.4,
            relationship_sentiment=0.4,
        )
        assert result is True
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `docker compose -f docker-compose.local.yml exec -T web pytest epocha/apps/agents/tests/test_belief.py -v`
Expected: FAIL with ImportError.

- [ ] **Step 3: Implement the belief filter**

Create `epocha/apps/agents/belief.py`:

```python
"""Belief filter — decides whether an agent accepts incoming information.

Models the cognitive evaluation of information credibility based on three
factors: the inherent reliability of the information, the trust in the
transmitter (derived from relationship), and the receiver's personality
disposition toward believing new information.

Scientific basis:
- Interpersonal trust model: Mayer, Davis & Schoorman (1995). "An Integrative
  Model of Organizational Trust." Academy of Management Review, 20(3), 709-734.
- Agreeableness and credulity: Graziano & Tobin (2002). "Agreeableness:
  Dimension of Personality or Social Desirability Artifact?" Journal of
  Personality, 70(5), 695-728.
"""
from __future__ import annotations

from django.conf import settings


def should_believe(
    reliability: float,
    receiver_personality: dict,
    relationship_strength: float,
    relationship_sentiment: float,
) -> bool:
    """Determine whether an agent accepts a piece of incoming information.

    The acceptance score is a weighted sum of three factors:
    - Information reliability (40%): inherent quality of the information
    - Relationship trust (30%): how much the receiver trusts the transmitter
    - Personality factor (30%): receiver's disposition toward credulity

    Args:
        reliability: Information reliability (0.0-1.0), degrades per hop.
        receiver_personality: Big Five personality dict of the receiving agent.
        relationship_strength: Strength of the relationship (0.0-1.0).
        relationship_sentiment: Sentiment toward the transmitter (-1.0 to 1.0).

    Returns:
        True if the agent accepts the information, False if they discard it.
    """
    # Relationship trust: strength + positive sentiment, averaged.
    # Negative sentiment is clamped to 0 -- distrust does not increase trust.
    relationship_trust = (relationship_strength + max(0.0, relationship_sentiment)) / 2.0

    # Personality factor: agreeableness (credulity) and openness (receptivity).
    agreeableness = receiver_personality.get("agreeableness", 0.5)
    openness = receiver_personality.get("openness", 0.5)
    personality_factor = agreeableness * 0.6 + openness * 0.4

    acceptance_score = (
        reliability * 0.4
        + relationship_trust * 0.3
        + personality_factor * 0.3
    )

    threshold = getattr(settings, "EPOCHA_INFO_FLOW_BELIEF_THRESHOLD", 0.4)
    return acceptance_score >= threshold
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `docker compose -f docker-compose.local.yml exec -T web pytest epocha/apps/agents/tests/test_belief.py -v`
Expected: All 8 tests PASS.

- [ ] **Step 5: Commit**

```
feat(agents): add belief filter for information flow

CHANGE: Implement should_believe() which decides whether an agent
accepts incoming information based on reliability, relationship trust,
and personality (agreeableness, openness). Used by the propagation
engine to filter hearsay and rumors.
```

---

### Task 3: Distortion Engine (rule-based)

Pure function that alters information content based on the transmitter's personality. Deterministic, zero LLM calls.

**Files:**
- Create: `epocha/apps/agents/distortion.py`
- Create: `epocha/apps/agents/tests/test_distortion.py`

- [ ] **Step 1: Write the failing tests**

Create `epocha/apps/agents/tests/test_distortion.py`:

```python
"""Tests for the rule-based distortion engine."""
from epocha.apps.agents.distortion import distort_information


class TestDistortInformation:
    def test_neutral_personality_no_distortion(self):
        """Traits between 0.3-0.7 produce no distortion."""
        content = "Marco argued with Elena."
        personality = {
            "neuroticism": 0.5, "agreeableness": 0.5,
            "openness": 0.5, "extraversion": 0.5,
            "conscientiousness": 0.5,
        }
        result = distort_information(content, personality)
        assert result == content

    def test_high_neuroticism_amplifies_negativity(self):
        """High neuroticism amplifies negative language."""
        content = "Marco argued with Elena."
        personality = {"neuroticism": 0.9}
        result = distort_information(content, personality)
        assert result != content
        assert "argued" not in result  # Should be replaced with stronger word

    def test_low_neuroticism_minimizes(self):
        """Low neuroticism softens language."""
        content = "Marco fought bitterly with Elena."
        personality = {"neuroticism": 0.1}
        result = distort_information(content, personality)
        assert "fought bitterly" not in result

    def test_high_agreeableness_softens(self):
        """High agreeableness softens conflict language."""
        content = "Marco betrayed Elena."
        personality = {"agreeableness": 0.9}
        result = distort_information(content, personality)
        assert "betrayed" not in result

    def test_low_agreeableness_exaggerates_conflict(self):
        """Low agreeableness exaggerates conflict."""
        content = "Marco argued with Elena."
        personality = {"agreeableness": 0.1}
        result = distort_information(content, personality)
        assert "argued" not in result

    def test_high_extraversion_exaggerates_scale(self):
        """High extraversion exaggerates scope."""
        content = "Someone complained about the food."
        personality = {"extraversion": 0.9}
        result = distort_information(content, personality)
        assert "someone" not in result.lower()

    def test_max_two_traits_applied(self):
        """Only the 2 most extreme traits apply, even if more are extreme."""
        content = "Marco argued with Elena."
        personality = {
            "neuroticism": 0.95,     # most extreme
            "agreeableness": 0.05,   # second most extreme
            "openness": 0.9,         # third -- should NOT apply
            "extraversion": 0.5,
            "conscientiousness": 0.5,
        }
        result = distort_information(content, personality)
        # Neuroticism and agreeableness should apply, openness should not.
        # Openness would add speculation ("perhaps because...") -- check it's absent
        assert "perhaps" not in result.lower()

    def test_empty_personality_no_distortion(self):
        """Missing personality traits default to neutral (no distortion)."""
        content = "Marco helped Elena."
        result = distort_information(content, {})
        assert result == content

    def test_distortion_strength_proportional_to_extremity(self):
        """Trait at 0.75 should distort less than trait at 0.95."""
        content = "Marco argued with Elena."
        mild = distort_information(content, {"neuroticism": 0.75})
        extreme = distort_information(content, {"neuroticism": 0.95})
        # Both should differ from original, but extreme should use stronger words
        assert mild != content
        assert extreme != content
        # We can't test exact words, but we verify they're different from each other
        # (different distortion strength produces different output)
        assert mild != extreme
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `docker compose -f docker-compose.local.yml exec -T web pytest epocha/apps/agents/tests/test_distortion.py -v`
Expected: FAIL with ImportError.

- [ ] **Step 3: Implement the distortion engine**

Create `epocha/apps/agents/distortion.py`:

```python
"""Rule-based distortion engine for information flow.

Alters information content based on the transmitter's personality (Big Five).
Each extreme trait applies a specific transformation to the text, modeling
how people unconsciously filter and reshape information when retelling it.

Scientific basis: Allport & Postman (1947). "The Psychology of Rumor."
Henry Holt and Company. Identifies three processes in serial transmission:
leveling (loss of detail), sharpening (emphasis of select details), and
assimilation (distortion toward the transmitter's expectations).
"""
from __future__ import annotations

import re

# Activation thresholds: traits only distort when extreme.
_HIGH_THRESHOLD = 0.7
_LOW_THRESHOLD = 0.3

# Maximum number of traits applied per distortion pass.
# Prevents illegible compound distortions.
_MAX_ACTIVE_TRAITS = 2

# Substitution patterns indexed by distortion strength: low, medium, high.
# Strength is derived from distance to threshold.
# Each entry: (regex_pattern, [low_replacement, medium_replacement, high_replacement])
_HIGH_NEUROTICISM_PATTERNS = [
    (r"\bargued\b", ["quarreled", "fought bitterly", "attacked viciously"]),
    (r"\bdisagreed\b", ["clashed", "fought", "had a violent confrontation"]),
    (r"\bhelped\b", ["tried to help", "barely managed to help", "desperately tried to help"]),
    (r"\btalked\b", ["confronted", "had a tense exchange with", "clashed openly with"]),
]

_LOW_NEUROTICISM_PATTERNS = [
    (r"\bargued\b", ["disagreed", "had a small disagreement", "had a minor difference of opinion"]),
    (r"\bfought bitterly\b", ["argued", "had a disagreement", "had a brief exchange"]),
    (r"\bfought\b", ["argued", "had a disagreement", "had a brief exchange"]),
    (r"\bbetrayed\b", ["disappointed", "let down", "made a questionable choice regarding"]),
]

_HIGH_AGREEABLENESS_PATTERNS = [
    (r"\bbetrayed\b", ["disappointed", "let down", "failed to support"]),
    (r"\bargued\b", ["discussed heatedly", "had a misunderstanding with", "had a difference of opinion with"]),
    (r"\bfought\b", ["disagreed with", "had tension with", "had a difficult moment with"]),
    (r"\battacked\b", ["confronted", "challenged", "pushed back against"]),
]

_LOW_AGREEABLENESS_PATTERNS = [
    (r"\bargued\b", ["attacked", "went after", "turned against"]),
    (r"\bdisagreed\b", ["fought", "clashed violently", "had a bitter confrontation"]),
    (r"\bhelped\b", ["tried to manipulate", "used the pretense of helping", "only helped to gain favor with"]),
    (r"\bdiscussed\b", ["argued bitterly about", "fought over", "clashed about"]),
]

_HIGH_OPENNESS_PATTERNS = [
    # Adds speculation after the statement
    (r"(\.)$", [" -- perhaps for a reason.", " -- one wonders why.", " -- which raises interesting questions."]),
]

_LOW_OPENNESS_PATTERNS = [
    # Strips qualifiers and nuance
    (r"\bperhaps\s+", ["", "", ""]),
    (r"\bapparently\s+", ["", "", ""]),
    (r"\bseemingly\s+", ["", "", ""]),
]

_HIGH_EXTRAVERSION_PATTERNS = [
    (r"\bsomeone\b", ["several people", "many people", "everyone"]),
    (r"\ba few\b", ["many", "a great number of", "practically all"]),
    (r"\bsome people\b", ["many people", "most people", "everyone"]),
]

_LOW_EXTRAVERSION_PATTERNS = [
    (r"\beveryone\b", ["some people", "a few people", "someone"]),
    (r"\bmany\b", ["a few", "some", "a couple of"]),
    (r"\bmost people\b", ["some people", "a few people", "one or two people"]),
]

_HIGH_CONSCIENTIOUSNESS_PATTERNS = [
    # Adds precision
    (r"(\.)$", [" (reportedly).", " (according to what was said).", " (from what I understand precisely)."]),
]

_LOW_CONSCIENTIOUSNESS_PATTERNS = [
    # Vague-ifies
    (r"\b(\w+) argued with (\w+)\b", ["someone argued with someone", "there was some argument", "people were fighting"]),
    (r"\b(\w+) helped (\w+)\b", ["someone helped someone", "there was some help given", "people helped each other or something"]),
]

# Map trait name -> (high_patterns, low_patterns)
_TRAIT_PATTERNS: dict[str, tuple[list, list]] = {
    "neuroticism": (_HIGH_NEUROTICISM_PATTERNS, _LOW_NEUROTICISM_PATTERNS),
    "agreeableness": (_HIGH_AGREEABLENESS_PATTERNS, _LOW_AGREEABLENESS_PATTERNS),
    "openness": (_HIGH_OPENNESS_PATTERNS, _LOW_OPENNESS_PATTERNS),
    "extraversion": (_HIGH_EXTRAVERSION_PATTERNS, _LOW_EXTRAVERSION_PATTERNS),
    "conscientiousness": (_HIGH_CONSCIENTIOUSNESS_PATTERNS, _LOW_CONSCIENTIOUSNESS_PATTERNS),
}


def _get_strength_index(value: float) -> int:
    """Map trait extremity to substitution strength index (0=low, 1=medium, 2=high).

    Strength is proportional to distance from the activation threshold.
    A trait at 0.75 (distance 0.05 from 0.7) is low strength.
    A trait at 0.95 (distance 0.25 from 0.7) is high strength.
    """
    if value > _HIGH_THRESHOLD:
        distance = value - _HIGH_THRESHOLD
    elif value < _LOW_THRESHOLD:
        distance = _LOW_THRESHOLD - value
    else:
        return 0

    # Normalize: max distance is 0.3 (from 0.7 to 1.0 or from 0.3 to 0.0)
    normalized = min(distance / 0.3, 1.0)
    if normalized < 0.33:
        return 0  # low
    elif normalized < 0.66:
        return 1  # medium
    return 2  # high


def _select_active_traits(personality: dict) -> list[tuple[str, float]]:
    """Select up to _MAX_ACTIVE_TRAITS extreme traits, sorted by extremity.

    Returns list of (trait_name, trait_value) for traits outside the neutral zone,
    sorted by distance from the neutral center (0.5), descending.
    """
    extreme = []
    for trait_name in _TRAIT_PATTERNS:
        value = personality.get(trait_name, 0.5)
        if value > _HIGH_THRESHOLD or value < _LOW_THRESHOLD:
            distance = abs(value - 0.5)
            extreme.append((trait_name, value, distance))

    extreme.sort(key=lambda x: x[2], reverse=True)
    return [(name, value) for name, value, _ in extreme[:_MAX_ACTIVE_TRAITS]]


def distort_information(content: str, personality: dict) -> str:
    """Apply rule-based distortion to information content.

    The transmitter's personality filters reshape the content:
    - High neuroticism amplifies negativity
    - Low neuroticism minimizes conflict
    - High agreeableness softens harsh language
    - Low agreeableness exaggerates conflict
    - High openness adds speculation
    - Low openness strips nuance
    - High extraversion exaggerates scale
    - Low extraversion understates
    - High conscientiousness adds precision markers
    - Low conscientiousness vague-ifies (omits specific details)

    Only the 2 most extreme traits apply. Traits in the neutral zone
    (0.3-0.7) produce no distortion.

    Args:
        content: The information text to distort.
        personality: Big Five personality dict of the transmitter.

    Returns:
        Distorted content string (may be identical if no extreme traits).
    """
    active_traits = _select_active_traits(personality)
    if not active_traits:
        return content

    result = content
    for trait_name, value in active_traits:
        high_patterns, low_patterns = _TRAIT_PATTERNS[trait_name]
        strength_idx = _get_strength_index(value)

        if value > _HIGH_THRESHOLD:
            patterns = high_patterns
        else:
            patterns = low_patterns

        for pattern, replacements in patterns:
            replacement = replacements[strength_idx]
            result = re.sub(pattern, replacement, result, count=1)

    return result
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `docker compose -f docker-compose.local.yml exec -T web pytest epocha/apps/agents/tests/test_distortion.py -v`
Expected: All 9 tests PASS.

- [ ] **Step 5: Commit**

```
feat(agents): add rule-based distortion engine for information flow

CHANGE: Implement distort_information() which alters content based on
the transmitter's Big Five personality. High neuroticism amplifies
negativity, low agreeableness exaggerates conflict, etc. Maximum 2
extreme traits apply per distortion, with strength proportional to
trait extremity. Deterministic, zero LLM calls.
```

---

### Task 4: Propagation Engine

The core module. Runs once per tick, collects significant actions, and spreads them through the social network using the distortion engine and belief filter.

**Files:**
- Create: `epocha/apps/agents/information_flow.py`
- Create: `epocha/apps/agents/tests/test_information_flow.py`

- [ ] **Step 1: Write the failing tests**

Create `epocha/apps/agents/tests/test_information_flow.py`:

```python
"""Tests for the information flow propagation engine."""
import pytest

from epocha.apps.agents.information_flow import propagate_information
from epocha.apps.agents.models import Agent, Memory, Relationship
from epocha.apps.simulation.models import Event, Simulation
from epocha.apps.users.models import User
from epocha.apps.world.models import World


@pytest.fixture
def user(db):
    return User.objects.create_user(email="info@epocha.dev", username="infotest", password="pass123")


@pytest.fixture
def simulation(user):
    return Simulation.objects.create(name="InfoTest", seed=42, owner=user)


@pytest.fixture
def world(simulation):
    return World.objects.create(simulation=simulation)


@pytest.fixture
def marco(simulation):
    return Agent.objects.create(
        simulation=simulation, name="Marco", role="blacksmith",
        personality={
            "openness": 0.5, "conscientiousness": 0.5, "extraversion": 0.5,
            "agreeableness": 0.5, "neuroticism": 0.5,
        },
    )


@pytest.fixture
def elena(simulation):
    return Agent.objects.create(
        simulation=simulation, name="Elena", role="farmer",
        personality={
            "openness": 0.5, "conscientiousness": 0.5, "extraversion": 0.5,
            "agreeableness": 0.5, "neuroticism": 0.5,
        },
    )


@pytest.fixture
def carlo(simulation):
    return Agent.objects.create(
        simulation=simulation, name="Carlo", role="priest",
        personality={
            "openness": 0.5, "conscientiousness": 0.5, "extraversion": 0.5,
            "agreeableness": 0.5, "neuroticism": 0.5,
        },
    )


@pytest.mark.django_db
class TestPropagateInformation:
    def test_significant_action_creates_hearsay(self, simulation, world, marco, elena):
        """An action with emotional_weight >= threshold creates hearsay for connected agents."""
        Relationship.objects.create(
            agent_from=marco, agent_to=elena,
            relation_type="friendship", strength=0.7, sentiment=0.6, since_tick=0,
        )
        Memory.objects.create(
            agent=marco, content="I decided to argue. angry at the priest",
            emotional_weight=0.4, source_type="direct", tick_created=5,
            origin_agent=marco,
        )

        propagate_information(simulation, tick=5)

        elena_memories = Memory.objects.filter(agent=elena, source_type="hearsay")
        assert elena_memories.count() == 1
        hearsay = elena_memories.first()
        assert hearsay.origin_agent == marco
        assert hearsay.reliability < 1.0
        assert hearsay.tick_created == 5

    def test_low_weight_action_does_not_propagate(self, simulation, world, marco, elena):
        """Actions below the propagation threshold are too mundane for gossip."""
        Relationship.objects.create(
            agent_from=marco, agent_to=elena,
            relation_type="friendship", strength=0.7, sentiment=0.6, since_tick=0,
        )
        Memory.objects.create(
            agent=marco, content="I decided to rest. tired",
            emotional_weight=0.05, source_type="direct", tick_created=5,
            origin_agent=marco,
        )

        propagate_information(simulation, tick=5)

        assert Memory.objects.filter(agent=elena, source_type="hearsay").count() == 0

    def test_no_relationship_no_propagation(self, simulation, world, marco, elena):
        """Without a relationship, hearsay does not reach the agent."""
        Memory.objects.create(
            agent=marco, content="I decided to betray. power grab",
            emotional_weight=0.8, source_type="direct", tick_created=5,
            origin_agent=marco,
        )

        propagate_information(simulation, tick=5)

        assert Memory.objects.filter(agent=elena, source_type="hearsay").count() == 0

    def test_hearsay_becomes_rumor_on_second_hop(self, simulation, world, marco, elena, carlo):
        """Hearsay from tick N-1 propagates as rumor in tick N."""
        # Marco -> Elena relationship
        Relationship.objects.create(
            agent_from=marco, agent_to=elena,
            relation_type="friendship", strength=0.7, sentiment=0.6, since_tick=0,
        )
        # Elena -> Carlo relationship
        Relationship.objects.create(
            agent_from=elena, agent_to=carlo,
            relation_type="professional", strength=0.6, sentiment=0.3, since_tick=0,
        )

        # Tick 5: Marco's direct memory
        Memory.objects.create(
            agent=marco, content="I decided to betray. power grab",
            emotional_weight=0.8, source_type="direct", tick_created=5,
            origin_agent=marco,
        )
        propagate_information(simulation, tick=5)

        # Elena should have hearsay
        elena_hearsay = Memory.objects.filter(agent=elena, source_type="hearsay")
        assert elena_hearsay.count() == 1

        # Tick 6: propagate again -- Elena's hearsay should reach Carlo as rumor
        propagate_information(simulation, tick=6)

        carlo_rumors = Memory.objects.filter(agent=carlo, source_type="rumor")
        assert carlo_rumors.count() == 1
        rumor = carlo_rumors.first()
        assert rumor.origin_agent == marco
        # Rumor reliability should be lower than hearsay
        assert rumor.reliability < elena_hearsay.first().reliability

    def test_dead_agents_do_not_receive_information(self, simulation, world, marco, elena):
        """Dead agents are excluded from propagation."""
        elena.is_alive = False
        elena.save(update_fields=["is_alive"])
        Relationship.objects.create(
            agent_from=marco, agent_to=elena,
            relation_type="friendship", strength=0.7, sentiment=0.6, since_tick=0,
        )
        Memory.objects.create(
            agent=marco, content="I decided to argue. angry",
            emotional_weight=0.4, source_type="direct", tick_created=5,
            origin_agent=marco,
        )

        propagate_information(simulation, tick=5)

        assert Memory.objects.filter(agent=elena, source_type="hearsay").count() == 0

    def test_deduplication_prevents_same_info_twice(self, simulation, world, marco, elena, carlo):
        """An agent should not receive the same information from multiple sources."""
        # Both Marco and Carlo know Elena
        Relationship.objects.create(
            agent_from=marco, agent_to=elena,
            relation_type="friendship", strength=0.7, sentiment=0.6, since_tick=0,
        )
        Relationship.objects.create(
            agent_from=carlo, agent_to=elena,
            relation_type="professional", strength=0.5, sentiment=0.3, since_tick=0,
        )
        # Both Marco and Carlo did significant actions in the same tick
        Memory.objects.create(
            agent=marco, content="I decided to argue. angry",
            emotional_weight=0.4, source_type="direct", tick_created=5,
            origin_agent=marco,
        )

        propagate_information(simulation, tick=5)

        # Elena should receive only 1 hearsay about Marco, not 2
        elena_hearsays = Memory.objects.filter(
            agent=elena, source_type="hearsay", origin_agent=marco,
        )
        assert elena_hearsays.count() == 1

    def test_public_events_reach_all_agents(self, simulation, world, marco, elena, carlo):
        """Public events propagate instantly to all living agents."""
        Event.objects.create(
            simulation=simulation, title="Plague outbreak",
            description="A terrible plague has hit the city.",
            tick=5, severity=0.9,
        )

        propagate_information(simulation, tick=5)

        for agent in [marco, elena, carlo]:
            public_memories = Memory.objects.filter(agent=agent, source_type="public")
            assert public_memories.count() == 1
            mem = public_memories.first()
            assert mem.reliability == 1.0
            assert "plague" in mem.content.lower()

    def test_belief_filter_rejects_unreliable_info(self, simulation, world, marco, elena):
        """A skeptical agent rejects low-reliability information."""
        elena.personality = {
            "openness": 0.1, "agreeableness": 0.1,  # very skeptical
            "conscientiousness": 0.5, "extraversion": 0.5, "neuroticism": 0.5,
        }
        elena.save(update_fields=["personality"])
        # Weak relationship
        Relationship.objects.create(
            agent_from=marco, agent_to=elena,
            relation_type="distrust", strength=0.2, sentiment=-0.5, since_tick=0,
        )
        Memory.objects.create(
            agent=marco, content="I decided to argue. angry",
            emotional_weight=0.4, source_type="direct", tick_created=5,
            origin_agent=marco,
        )

        propagate_information(simulation, tick=5)

        # Elena should reject it: low reliability (0.7) + bad relationship + skeptical
        assert Memory.objects.filter(agent=elena, source_type="hearsay").count() == 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `docker compose -f docker-compose.local.yml exec -T web pytest epocha/apps/agents/tests/test_information_flow.py -v`
Expected: FAIL with ImportError.

- [ ] **Step 3: Implement the propagation engine**

Create `epocha/apps/agents/information_flow.py`:

```python
"""Information flow propagation engine.

Runs once per tick after agent decisions. Collects significant actions and
public events, then propagates them through the social network with delay
(1 hop per tick), distortion (rule-based), and filtering (belief-based).

Each tick:
1. Direct memories with high emotional weight -> hearsay to connected agents
2. Hearsay from previous tick -> rumor to next layer of connections
3. Public events -> instant broadcast to all living agents

Scientific basis for the propagation model:
- Serial reproduction and information degradation: Bartlett (1932).
  "Remembering: A Study in Experimental and Social Psychology."
  Cambridge University Press.
- Social network information diffusion: Granovetter (1973). "The Strength
  of Weak Ties." American Journal of Sociology, 78(6), 1360-1380.
"""
from __future__ import annotations

import logging

from django.conf import settings

from .belief import should_believe
from .distortion import distort_information
from .models import Agent, Memory, Relationship

logger = logging.getLogger(__name__)


def propagate_information(simulation, tick: int) -> None:
    """Propagate information through the social network for one tick.

    This is the main entry point, called once per tick from the engine.

    Args:
        simulation: The simulation instance.
        tick: The current tick number.
    """
    threshold = getattr(settings, "EPOCHA_INFO_FLOW_PROPAGATION_THRESHOLD", 0.3)
    max_recipients = getattr(settings, "EPOCHA_INFO_FLOW_MAX_RECIPIENTS", 20)

    # Phase 1: Propagate significant direct actions as hearsay
    direct_memories = Memory.objects.filter(
        agent__simulation=simulation,
        source_type="direct",
        tick_created=tick,
        emotional_weight__gte=threshold,
    ).select_related("agent")

    for memory in direct_memories:
        _propagate_memory(
            memory=memory,
            simulation=simulation,
            tick=tick,
            target_source_type="hearsay",
            max_recipients=max_recipients,
        )

    # Phase 2: Propagate previous tick's hearsay as rumor
    max_hops = getattr(settings, "EPOCHA_INFO_FLOW_MAX_HOPS", 3)
    if max_hops >= 2:
        hearsay_memories = Memory.objects.filter(
            agent__simulation=simulation,
            source_type="hearsay",
            tick_created=tick - 1,
        ).select_related("agent")

        for memory in hearsay_memories:
            _propagate_memory(
                memory=memory,
                simulation=simulation,
                tick=tick,
                target_source_type="rumor",
                max_recipients=max_recipients,
            )

    # Phase 3: Propagate previous tick's rumors (hop 3+) if within max_hops
    if max_hops >= 3:
        rumor_memories = Memory.objects.filter(
            agent__simulation=simulation,
            source_type="rumor",
            tick_created=tick - 1,
        ).select_related("agent")

        for memory in rumor_memories:
            # Calculate current hop from reliability degradation
            decay = getattr(settings, "EPOCHA_INFO_FLOW_RELIABILITY_DECAY", 0.7)
            current_hop = _estimate_hop(memory.reliability, decay)
            if current_hop < max_hops:
                _propagate_memory(
                    memory=memory,
                    simulation=simulation,
                    tick=tick,
                    target_source_type="rumor",
                    max_recipients=max_recipients,
                )

    # Phase 4: Broadcast public events to all living agents
    from epocha.apps.simulation.models import Event

    events = Event.objects.filter(simulation=simulation, tick=tick)
    if events.exists():
        living_agents = Agent.objects.filter(simulation=simulation, is_alive=True)
        for event in events:
            for agent in living_agents:
                # Dedup: skip if agent already has a public memory for this event
                if Memory.objects.filter(
                    agent=agent,
                    source_type="public",
                    tick_created=tick,
                    content__contains=event.title,
                ).exists():
                    continue
                Memory.objects.create(
                    agent=agent,
                    content=f"{event.title}: {event.description}",
                    emotional_weight=event.severity,
                    source_type="public",
                    reliability=1.0,
                    tick_created=tick,
                    origin_agent=None,
                )


def _propagate_memory(
    memory: Memory,
    simulation,
    tick: int,
    target_source_type: str,
    max_recipients: int,
) -> None:
    """Propagate a single memory to connected agents.

    Args:
        memory: The memory to propagate.
        simulation: The simulation instance.
        tick: Current tick number.
        target_source_type: "hearsay" or "rumor".
        max_recipients: Maximum number of recipients per memory.
    """
    decay = getattr(settings, "EPOCHA_INFO_FLOW_RELIABILITY_DECAY", 0.7)
    transmitter = memory.agent
    origin_agent = memory.origin_agent or transmitter

    # Find connected agents (relationships go both directions)
    connected_ids = set(
        Relationship.objects.filter(agent_from=transmitter)
        .values_list("agent_to_id", flat=True)
    ) | set(
        Relationship.objects.filter(agent_to=transmitter)
        .values_list("agent_from_id", flat=True)
    )

    if not connected_ids:
        return

    recipients = (
        Agent.objects.filter(id__in=connected_ids, is_alive=True)
        .exclude(id=origin_agent.id)  # Don't propagate back to the origin
        .select_related()[:max_recipients]
    )

    new_reliability = memory.reliability * decay

    for recipient in recipients:
        # Dedup: skip if recipient already knows about this from the same origin
        if Memory.objects.filter(
            agent=recipient,
            origin_agent=origin_agent,
            tick_created=tick,
            source_type__in=["hearsay", "rumor", "direct"],
        ).exists():
            continue

        # Distort content through transmitter's personality
        distorted_content = distort_information(memory.content, transmitter.personality)

        # Belief filter: does the recipient accept this information?
        relationship = Relationship.objects.filter(
            agent_from=recipient, agent_to=transmitter,
        ).first() or Relationship.objects.filter(
            agent_from=transmitter, agent_to=recipient,
        ).first()

        rel_strength = relationship.strength if relationship else 0.0
        rel_sentiment = relationship.sentiment if relationship else 0.0

        if not should_believe(
            reliability=new_reliability,
            receiver_personality=recipient.personality,
            relationship_strength=rel_strength,
            relationship_sentiment=rel_sentiment,
        ):
            continue

        Memory.objects.create(
            agent=recipient,
            content=distorted_content,
            emotional_weight=memory.emotional_weight,
            source_type=target_source_type,
            reliability=new_reliability,
            tick_created=tick,
            origin_agent=origin_agent,
        )


def _estimate_hop(reliability: float, decay: float) -> int:
    """Estimate the hop count from the current reliability.

    Since reliability = decay^hop, hop = log(reliability) / log(decay).
    Returns an integer estimate (rounded).
    """
    import math

    if reliability >= 1.0 or decay >= 1.0 or decay <= 0.0:
        return 0
    if reliability <= 0.0:
        return 99
    return round(math.log(reliability) / math.log(decay))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `docker compose -f docker-compose.local.yml exec -T web pytest epocha/apps/agents/tests/test_information_flow.py -v`
Expected: All 8 tests PASS.

- [ ] **Step 5: Commit**

```
feat(agents): add information flow propagation engine

CHANGE: Implement propagate_information() which spreads significant
actions through the social network as hearsay (hop 1) and rumor (hop 2+).
Integrates the distortion engine and belief filter. Public events
broadcast instantly to all living agents. Deduplication prevents
receiving the same information from multiple sources.
```

---

### Task 5: Integration into tick engine

Wire the propagation engine into the simulation tick -- both the synchronous engine and the Celery production path.

**Files:**
- Modify: `epocha/apps/simulation/engine.py:237-238`
- Modify: `epocha/apps/simulation/tasks.py:97-98`
- Modify: `epocha/apps/simulation/engine.py:118-124` (set origin_agent on direct memories)
- Test: `epocha/apps/simulation/tests/test_engine.py`

- [ ] **Step 1: Write the failing test**

Add to `epocha/apps/simulation/tests/test_engine.py`, inside `TestSimulationEngine`:

```python
@patch("epocha.apps.simulation.engine.process_agent_decision")
def test_information_flow_runs_after_decisions(self, mock_decision, sim_with_world):
    """Information flow should propagate after agent decisions."""
    Agent.objects.create(
        simulation=sim_with_world, name="Elena", role="farmer",
        personality={
            "openness": 0.5, "conscientiousness": 0.5, "extraversion": 0.5,
            "agreeableness": 0.5, "neuroticism": 0.5,
        },
    )
    Relationship.objects.create(
        agent_from=Agent.objects.get(name="Marco"),
        agent_to=Agent.objects.get(name="Elena"),
        relation_type="friendship", strength=0.7, sentiment=0.6, since_tick=0,
    )
    mock_decision.return_value = {"action": "argue", "reason": "angry at priest"}

    engine = SimulationEngine(sim_with_world)
    engine.run_tick()

    # Elena should have received hearsay about Marco's action
    elena = Agent.objects.get(name="Elena")
    hearsay = Memory.objects.filter(agent=elena, source_type="hearsay")
    assert hearsay.count() >= 1
```

Also add the `Relationship` import at the top of the test file:

```python
from epocha.apps.agents.models import Agent, Memory, Relationship
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker compose -f docker-compose.local.yml exec -T web pytest epocha/apps/simulation/tests/test_engine.py::TestSimulationEngine::test_information_flow_runs_after_decisions -v`
Expected: FAIL (no hearsay created because propagation is not called yet).

- [ ] **Step 3: Set origin_agent on direct memories in apply_agent_action**

In `epocha/apps/simulation/engine.py`, modify the `Memory.objects.create()` call inside `apply_agent_action` (around line 118) to include `origin_agent=agent`:

```python
        Memory.objects.create(
            agent=agent,
            content=f"I decided to {action_type}. {reason}".strip(),
            emotional_weight=emotional_weight,
            source_type="direct",
            tick_created=tick,
            origin_agent=agent,
        )
```

- [ ] **Step 4: Add propagation call to SimulationEngine.run_tick()**

In `epocha/apps/simulation/engine.py`, add the import at the top:

```python
from epocha.apps.agents.information_flow import propagate_information
```

In `run_tick()`, between the agent decisions loop and memory decay (between current lines 236 and 237), add:

```python
        # 3. Information flow (propagate hearsay and rumors)
        propagate_information(self.simulation, tick)

        # 4. Memory decay
```

Update the comment numbers accordingly (memory decay becomes 4, advance tick becomes 5, broadcast becomes 6).

- [ ] **Step 5: Add propagation call to Celery finalize_tick**

In `epocha/apps/simulation/tasks.py`, in `finalize_tick()`, before the memory decay line (line 98), add:

```python
    # Information flow (propagate hearsay and rumors)
    from epocha.apps.agents.information_flow import propagate_information
    propagate_information(simulation, tick)
```

- [ ] **Step 6: Run all tests**

Run: `docker compose -f docker-compose.local.yml exec -T web pytest epocha/apps/agents/ epocha/apps/simulation/ -v`
Expected: All tests PASS.

- [ ] **Step 7: Commit**

```
feat(simulation): integrate information flow into tick engine

CHANGE: Call propagate_information() after agent decisions in both the
synchronous engine and the Celery chord path. Set origin_agent on
direct memories created by apply_agent_action. Information now flows
through the social network: hearsay at hop 1, rumors at hop 2+.
```

---

### Task 6: Update engine docstring and module docstring

The tick engine docstring lists 6 steps but now has a 7th (information flow). Update documentation to reflect the new flow.

**Files:**
- Modify: `epocha/apps/simulation/engine.py:1-16`

- [ ] **Step 1: Update the module docstring**

Replace the module docstring at the top of `epocha/apps/simulation/engine.py`:

```python
"""Tick orchestrator: coordinates economy, agent decisions, information flow, memory, and events.

Each tick is a discrete time step where:
1. The economy updates (income, costs, mood effects)
2. Each living agent makes a decision via LLM
3. Decision consequences are applied (mood, health adjustments)
4. Memories are created from actions
5. Information propagates through the social network (hearsay, rumors)
6. Old memories decay periodically
7. The tick counter advances

Agent failures are isolated: if one agent's LLM call fails, the tick
continues for all other agents. This ensures simulation resilience.

Module-level functions (run_economy, run_memory_decay, broadcast_tick) are
used by both the SimulationEngine (synchronous path) and the Celery chord
tasks (production path). This avoids duplicating logic across execution modes.
"""
```

- [ ] **Step 2: Commit**

```
docs(simulation): update engine docstring with information flow step

CHANGE: Engine module docstring now reflects the 7-step tick flow
including the information flow propagation phase.
```

# Factions and Emergent Leadership Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Activate the dormant Group model so that factions form organically, leaders emerge based on traits and social standing, cohesion evolves dynamically, and groups can dissolve or split.

**Architecture:** Bottom-up: affinity calculator (pure function), then faction dynamics engine (cohesion, leadership, formation, schism), then decision pipeline integration (new actions + context enrichment), then tick engine wiring. Each module is independently testable.

**Tech Stack:** Django ORM, pytest, LLM client (for group name/objective generation only)

**Spec:** `docs/superpowers/specs/2026-04-05-factions-leadership-design.md`

---

## File Structure

| File | Responsibility | New/Modify |
|------|---------------|------------|
| `epocha/apps/agents/affinity.py` | Pairwise affinity calculation | New |
| `epocha/apps/agents/factions.py` | Faction dynamics engine | New |
| `epocha/apps/agents/tests/test_affinity.py` | Affinity tests | New |
| `epocha/apps/agents/tests/test_factions.py` | Faction dynamics tests | New |
| `epocha/apps/agents/models.py:73-85` | Add formed_at_tick to Group | Modify |
| `epocha/apps/agents/decision.py:22-31,42-98` | Add actions + group context | Modify |
| `epocha/apps/simulation/engine.py:34-57,209-253` | Add action weights + faction call | Modify |
| `epocha/apps/simulation/tasks.py:97-99` | Add faction call in Celery | Modify |
| `epocha/apps/dashboard/formatters.py:9-20` | Add form_group/join_group verbs | Modify |
| `config/settings/base.py:168` | Add EPOCHA_FACTION_* settings | Modify |

---

### Task 1: Settings and Group model migration

Add faction settings and `formed_at_tick` field to Group.

**Files:**
- Modify: `config/settings/base.py:168`
- Modify: `epocha/apps/agents/models.py:73-85`
- Migration: `epocha/apps/agents/migrations/`

- [ ] **Step 1: Add settings to base.py**

At the end of `config/settings/base.py`, after the last EPOCHA_INFO_FLOW setting (line ~168), add:

```python
# --- Faction Dynamics ---
# How often faction dynamics run (every N ticks).
EPOCHA_FACTION_DYNAMICS_INTERVAL = env.int("EPOCHA_FACTION_DYNAMICS_INTERVAL", default=5)

# Minimum pairwise affinity for agents to be considered a potential faction cluster.
# Source: calibrated so that agents sharing social class + positive relationship
# (circumstance_score ~0.5, relationship_score ~0.5) cross the threshold.
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

- [ ] **Step 2: Add formed_at_tick to Group model**

In `epocha/apps/agents/models.py`, in the Group class (around line 81), after `parent_group`, add:

```python
    formed_at_tick = models.PositiveIntegerField(default=0, help_text="Tick when the group was formed")
```

- [ ] **Step 3: Generate and apply migration**

Run:
```bash
docker compose -f docker-compose.local.yml exec -T web python manage.py makemigrations agents --name group_formed_at_tick
docker compose -f docker-compose.local.yml exec -T web python manage.py migrate agents
```

- [ ] **Step 4: Run existing tests**

Run: `docker compose -f docker-compose.local.yml exec -T web pytest epocha/apps/agents/ epocha/apps/simulation/ -q`
Expected: All pass.

- [ ] **Step 5: Commit**

```
feat(agents): add formed_at_tick to Group and faction settings

CHANGE: Add formed_at_tick field to Group model for tracking group age
and computing member seniority. Add EPOCHA_FACTION_* settings for
dynamics interval, affinity threshold, member limits, dissolution
threshold, and legitimacy threshold.
```

---

### Task 2: Affinity Calculator

Pure function that computes pairwise affinity between two agents based on personality, relationships, and circumstances.

**Files:**
- Create: `epocha/apps/agents/affinity.py`
- Create: `epocha/apps/agents/tests/test_affinity.py`

- [ ] **Step 1: Write the failing tests**

Create `epocha/apps/agents/tests/test_affinity.py`:

```python
"""Tests for agent pairwise affinity calculation."""
import math

import pytest

from epocha.apps.agents.affinity import compute_affinity
from epocha.apps.agents.models import Agent, Memory, Relationship
from epocha.apps.simulation.models import Simulation
from epocha.apps.users.models import User
from epocha.apps.world.models import World


@pytest.fixture
def user(db):
    return User.objects.create_user(email="aff@epocha.dev", username="afftest", password="pass123")


@pytest.fixture
def simulation(user):
    return Simulation.objects.create(name="AffTest", seed=42, owner=user)


@pytest.fixture
def world(simulation):
    return World.objects.create(simulation=simulation)


@pytest.fixture
def marco(simulation):
    return Agent.objects.create(
        simulation=simulation, name="Marco", role="blacksmith",
        social_class="working", mood=0.3, wealth=30.0,
        personality={
            "openness": 0.8, "conscientiousness": 0.6, "extraversion": 0.4,
            "agreeableness": 0.3, "neuroticism": 0.7,
        },
    )


@pytest.fixture
def elena(simulation):
    return Agent.objects.create(
        simulation=simulation, name="Elena", role="farmer",
        social_class="working", mood=0.3, wealth=35.0,
        personality={
            "openness": 0.7, "conscientiousness": 0.5, "extraversion": 0.5,
            "agreeableness": 0.4, "neuroticism": 0.6,
        },
    )


@pytest.fixture
def carlo(simulation):
    return Agent.objects.create(
        simulation=simulation, name="Carlo", role="priest",
        social_class="middle", mood=0.7, wealth=80.0,
        personality={
            "openness": 0.2, "conscientiousness": 0.9, "extraversion": 0.3,
            "agreeableness": 0.8, "neuroticism": 0.1,
        },
    )


@pytest.mark.django_db
class TestComputeAffinity:
    def test_similar_agents_high_affinity(self, simulation, world, marco, elena):
        """Agents with similar personality, same class, both low mood = high affinity."""
        Relationship.objects.create(
            agent_from=marco, agent_to=elena,
            relation_type="friendship", strength=0.7, sentiment=0.5, since_tick=0,
        )
        score = compute_affinity(marco, elena, tick=10)
        assert score > 0.5

    def test_dissimilar_agents_low_affinity(self, simulation, world, marco, carlo):
        """Agents with very different personality, different class, different mood."""
        score = compute_affinity(marco, carlo, tick=10)
        assert score < 0.4

    def test_no_relationship_zero_relationship_score(self, simulation, world, marco, elena):
        """Without a relationship, the relationship component is 0."""
        score_no_rel = compute_affinity(marco, elena, tick=10)
        Relationship.objects.create(
            agent_from=marco, agent_to=elena,
            relation_type="friendship", strength=0.8, sentiment=0.6, since_tick=0,
        )
        score_with_rel = compute_affinity(marco, elena, tick=10)
        assert score_with_rel > score_no_rel

    def test_shared_public_memory_increases_affinity(self, simulation, world, marco, elena):
        """Agents sharing a recent public memory have higher affinity."""
        score_before = compute_affinity(marco, elena, tick=10)
        Memory.objects.create(
            agent=marco, content="Plague outbreak: terrible plague",
            emotional_weight=0.9, source_type="public", tick_created=8,
        )
        Memory.objects.create(
            agent=elena, content="Plague outbreak: terrible plague",
            emotional_weight=0.9, source_type="public", tick_created=8,
        )
        score_after = compute_affinity(marco, elena, tick=10)
        assert score_after > score_before

    def test_same_role_increases_affinity(self, simulation, world, marco):
        """Two agents with the same role get a small boost."""
        marco2 = Agent.objects.create(
            simulation=simulation, name="Luigi", role="blacksmith",
            social_class="working", mood=0.5, wealth=40.0,
            personality={
                "openness": 0.3, "conscientiousness": 0.3, "extraversion": 0.3,
                "agreeableness": 0.3, "neuroticism": 0.3,
            },
        )
        score = compute_affinity(marco, marco2, tick=10)
        # Same class + same role should boost circumstance score
        marco2.role = "farmer"
        marco2.save(update_fields=["role"])
        score_diff_role = compute_affinity(marco, marco2, tick=10)
        assert score > score_diff_role

    def test_affinity_is_symmetric(self, simulation, world, marco, elena):
        """affinity(A, B) == affinity(B, A)."""
        Relationship.objects.create(
            agent_from=marco, agent_to=elena,
            relation_type="friendship", strength=0.6, sentiment=0.4, since_tick=0,
        )
        score_ab = compute_affinity(marco, elena, tick=10)
        score_ba = compute_affinity(elena, marco, tick=10)
        assert abs(score_ab - score_ba) < 0.01

    def test_affinity_range_zero_to_one(self, simulation, world, marco, carlo):
        """Affinity score must be between 0.0 and 1.0."""
        score = compute_affinity(marco, carlo, tick=10)
        assert 0.0 <= score <= 1.0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `docker compose -f docker-compose.local.yml exec -T web pytest epocha/apps/agents/tests/test_affinity.py -v`
Expected: FAIL with ImportError.

- [ ] **Step 3: Implement the affinity calculator**

Create `epocha/apps/agents/affinity.py`:

```python
"""Pairwise affinity calculation for faction formation.

Computes how likely two agents are to form or join a faction together,
based on personality similarity, relationship quality, and shared circumstances.

The affinity score is a weighted average of three components:
- Personality similarity (30%): Big Five Euclidean distance
- Relationship quality (30%): strength + sentiment of existing relationship
- Circumstance alignment (40%): shared class, mood, experiences, role

Circumstances weigh more because factions form around shared conditions,
not shared temperaments. A desperate blacksmith and a desperate farmer have
more reason to organize than two cheerful people with similar personalities.

Source: Olson, M. (1965). "The Logic of Collective Action." Harvard University
Press — emphasizes shared grievances as primary drivers of group formation.

Source: McCrae, R. R. & Costa, P. T. (2003). "Personality in Adulthood:
A Five-Factor Theory Perspective." Guilford Press — Euclidean distance on
Big Five as standard metric for personality similarity.
"""
from __future__ import annotations

import math

from django.db.models import Q

from .models import Agent, Memory, Relationship

_BIG_FIVE = ("openness", "conscientiousness", "extraversion", "agreeableness", "neuroticism")

# Low mood threshold: both agents below this are considered dissatisfied.
_LOW_MOOD_THRESHOLD = 0.4

# How far back to look for shared public memories (in ticks).
_SHARED_MEMORY_LOOKBACK = 10


def compute_affinity(agent_a: Agent, agent_b: Agent, tick: int) -> float:
    """Compute pairwise affinity between two agents.

    Args:
        agent_a: First agent.
        agent_b: Second agent.
        tick: Current simulation tick (for memory lookback).

    Returns:
        Affinity score between 0.0 and 1.0.
    """
    personality_sim = _personality_similarity(agent_a.personality, agent_b.personality)
    relationship_score = _relationship_score(agent_a, agent_b)
    circumstance_score = _circumstance_score(agent_a, agent_b, tick)

    affinity = personality_sim * 0.3 + relationship_score * 0.3 + circumstance_score * 0.4
    return max(0.0, min(1.0, affinity))


def _personality_similarity(personality_a: dict, personality_b: dict) -> float:
    """1 minus normalized Euclidean distance of Big Five traits."""
    squared_sum = 0.0
    for trait in _BIG_FIVE:
        val_a = personality_a.get(trait, 0.5)
        val_b = personality_b.get(trait, 0.5)
        if not isinstance(val_a, (int, float)):
            val_a = 0.5
        if not isinstance(val_b, (int, float)):
            val_b = 0.5
        squared_sum += (val_a - val_b) ** 2
    distance = math.sqrt(squared_sum) / math.sqrt(len(_BIG_FIVE))
    return 1.0 - distance


def _relationship_score(agent_a: Agent, agent_b: Agent) -> float:
    """Relationship quality between two agents (bidirectional lookup)."""
    rel = Relationship.objects.filter(
        Q(agent_from=agent_a, agent_to=agent_b)
        | Q(agent_from=agent_b, agent_to=agent_a)
    ).first()
    if not rel:
        return 0.0
    return (rel.strength + max(0.0, rel.sentiment)) / 2.0


def _circumstance_score(agent_a: Agent, agent_b: Agent, tick: int) -> float:
    """Circumstance alignment between two agents.

    Components (capped at 1.0):
    - Same social_class: +0.3
    - Both low mood (< 0.4): +0.2
    - Shared public memory in last 10 ticks: +0.2
    - Same wealth quartile: +0.15
    - Same role: +0.15
    """
    score = 0.0

    # Same social class
    if agent_a.social_class == agent_b.social_class:
        score += 0.3

    # Both dissatisfied
    if agent_a.mood < _LOW_MOOD_THRESHOLD and agent_b.mood < _LOW_MOOD_THRESHOLD:
        score += 0.2

    # Shared public memory
    min_tick = max(0, tick - _SHARED_MEMORY_LOOKBACK)
    a_public_contents = set(
        Memory.objects.filter(
            agent=agent_a, source_type="public", tick_created__gte=min_tick,
        ).values_list("content", flat=True)
    )
    if a_public_contents:
        b_has_shared = Memory.objects.filter(
            agent=agent_b, source_type="public", tick_created__gte=min_tick,
            content__in=a_public_contents,
        ).exists()
        if b_has_shared:
            score += 0.2

    # Same wealth quartile (approximate: compare relative position)
    wealth_diff = abs(agent_a.wealth - agent_b.wealth)
    max_wealth = max(agent_a.wealth, agent_b.wealth, 1.0)
    if wealth_diff / max_wealth < 0.25:
        score += 0.15

    # Same role
    if agent_a.role and agent_a.role == agent_b.role:
        score += 0.15

    return min(1.0, score)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `docker compose -f docker-compose.local.yml exec -T web pytest epocha/apps/agents/tests/test_affinity.py -v`
Expected: All 8 tests PASS.

- [ ] **Step 5: Commit**

```
feat(agents): add pairwise affinity calculator for faction formation

CHANGE: Implement compute_affinity() which measures how likely two agents
are to join the same faction based on personality similarity (Big Five
Euclidean distance), relationship quality, and circumstance alignment
(social class, mood, shared events, role). Circumstances weigh 40%
because factions form around shared conditions.
```

---

### Task 3: Faction Dynamics Engine -- Cohesion and Leadership

The core engine with cohesion updates and leadership management. Formation and schism are separate tasks to keep each task focused.

**Files:**
- Create: `epocha/apps/agents/factions.py`
- Create: `epocha/apps/agents/tests/test_factions.py`

- [ ] **Step 1: Write the failing tests**

Create `epocha/apps/agents/tests/test_factions.py`:

```python
"""Tests for the faction dynamics engine."""
import pytest

from epocha.apps.agents.factions import (
    compute_leadership_score,
    compute_legitimacy,
    update_group_cohesion,
    update_group_leadership,
)
from epocha.apps.agents.models import Agent, DecisionLog, Group, Memory, Relationship
from epocha.apps.simulation.models import Simulation
from epocha.apps.users.models import User
from epocha.apps.world.models import World


@pytest.fixture
def user(db):
    return User.objects.create_user(email="fac@epocha.dev", username="factest", password="pass123")


@pytest.fixture
def simulation(user):
    return Simulation.objects.create(name="FacTest", seed=42, owner=user)


@pytest.fixture
def world(simulation):
    return World.objects.create(simulation=simulation)


@pytest.fixture
def group_with_members(simulation):
    group = Group.objects.create(
        simulation=simulation, name="The Guild", objective="Protect artisans",
        cohesion=0.6, formed_at_tick=1,
    )
    marco = Agent.objects.create(
        simulation=simulation, name="Marco", role="blacksmith",
        personality={"openness": 0.5, "conscientiousness": 0.5, "extraversion": 0.5,
                     "agreeableness": 0.5, "neuroticism": 0.5},
        charisma=0.8, intelligence=0.7, wealth=60.0, group=group,
    )
    elena = Agent.objects.create(
        simulation=simulation, name="Elena", role="farmer",
        personality={"openness": 0.5, "conscientiousness": 0.5, "extraversion": 0.5,
                     "agreeableness": 0.5, "neuroticism": 0.5},
        charisma=0.4, intelligence=0.5, wealth=30.0, group=group,
    )
    carlo = Agent.objects.create(
        simulation=simulation, name="Carlo", role="priest",
        personality={"openness": 0.5, "conscientiousness": 0.5, "extraversion": 0.5,
                     "agreeableness": 0.5, "neuroticism": 0.5},
        charisma=0.6, intelligence=0.6, wealth=45.0, group=group,
    )
    group.leader = marco
    group.save(update_fields=["leader"])
    # Memories for seniority tracking
    Memory.objects.create(agent=marco, content="I helped found The Guild", emotional_weight=0.3,
                          source_type="direct", tick_created=1)
    Memory.objects.create(agent=elena, content="I helped found The Guild", emotional_weight=0.3,
                          source_type="direct", tick_created=1)
    Memory.objects.create(agent=carlo, content="I joined The Guild", emotional_weight=0.3,
                          source_type="direct", tick_created=5)
    return group, marco, elena, carlo


@pytest.mark.django_db
class TestLeadershipScore:
    def test_charismatic_wealthy_agent_scores_high(self, group_with_members):
        group, marco, elena, carlo = group_with_members
        Relationship.objects.create(agent_from=marco, agent_to=elena,
                                    relation_type="friendship", strength=0.7, sentiment=0.6, since_tick=0)
        Relationship.objects.create(agent_from=marco, agent_to=carlo,
                                    relation_type="professional", strength=0.5, sentiment=0.3, since_tick=0)
        score = compute_leadership_score(marco, group, tick=10)
        assert score > 0.5

    def test_low_charisma_agent_scores_low(self, group_with_members):
        group, marco, elena, carlo = group_with_members
        score = compute_leadership_score(elena, group, tick=10)
        assert score < compute_leadership_score(marco, group, tick=10)

    def test_score_range_zero_to_one(self, group_with_members):
        group, marco, elena, carlo = group_with_members
        for agent in [marco, elena, carlo]:
            score = compute_leadership_score(agent, group, tick=10)
            assert 0.0 <= score <= 1.0


@pytest.mark.django_db
class TestCohesionUpdate:
    def test_cooperation_increases_cohesion(self, simulation, world, group_with_members):
        group, marco, elena, carlo = group_with_members
        # Marco helps Elena (cooperation)
        DecisionLog.objects.create(
            simulation=simulation, agent=marco, tick=9,
            input_context="", output_decision='{"action": "help", "target": "Elena"}',
            llm_model="test",
        )
        initial_cohesion = group.cohesion
        update_group_cohesion(group, simulation, tick=10)
        group.refresh_from_db()
        assert group.cohesion > initial_cohesion

    def test_conflict_decreases_cohesion(self, simulation, world, group_with_members):
        group, marco, elena, carlo = group_with_members
        # Marco argues with Elena (conflict)
        DecisionLog.objects.create(
            simulation=simulation, agent=marco, tick=9,
            input_context="", output_decision='{"action": "argue", "target": "Elena"}',
            llm_model="test",
        )
        initial_cohesion = group.cohesion
        update_group_cohesion(group, simulation, tick=10)
        group.refresh_from_db()
        assert group.cohesion < initial_cohesion

    def test_cohesion_clamped_to_range(self, simulation, world, group_with_members):
        group, marco, elena, carlo = group_with_members
        group.cohesion = 0.99
        group.save(update_fields=["cohesion"])
        update_group_cohesion(group, simulation, tick=10)
        group.refresh_from_db()
        assert 0.0 <= group.cohesion <= 1.0


@pytest.mark.django_db
class TestLeadershipContestaton:
    def test_legitimate_leader_stays(self, simulation, world, group_with_members):
        group, marco, elena, carlo = group_with_members
        Relationship.objects.create(agent_from=marco, agent_to=elena,
                                    relation_type="friendship", strength=0.7, sentiment=0.6, since_tick=0)
        Relationship.objects.create(agent_from=marco, agent_to=carlo,
                                    relation_type="professional", strength=0.5, sentiment=0.3, since_tick=0)
        update_group_leadership(group, tick=10)
        group.refresh_from_db()
        assert group.leader == marco

    def test_unpopular_leader_replaced(self, simulation, world, group_with_members):
        group, marco, elena, carlo = group_with_members
        # Marco has terrible relationships with everyone
        Relationship.objects.create(agent_from=marco, agent_to=elena,
                                    relation_type="rivalry", strength=0.8, sentiment=-0.8, since_tick=0)
        Relationship.objects.create(agent_from=marco, agent_to=carlo,
                                    relation_type="distrust", strength=0.7, sentiment=-0.6, since_tick=0)
        # Lower group cohesion to make legitimacy very low
        group.cohesion = 0.2
        group.save(update_fields=["cohesion"])
        update_group_leadership(group, tick=10)
        group.refresh_from_db()
        assert group.leader != marco
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `docker compose -f docker-compose.local.yml exec -T web pytest epocha/apps/agents/tests/test_factions.py -v`
Expected: FAIL with ImportError.

- [ ] **Step 3: Implement the faction dynamics engine**

Create `epocha/apps/agents/factions.py`:

```python
"""Faction dynamics engine -- cohesion, leadership, formation, schism.

Runs every N ticks (configurable) after information flow. Manages the
lifecycle of agent groups: updates cohesion based on member interactions,
verifies leadership legitimacy, detects potential new factions, and
handles dissolution and schism.

The faction dynamics phase is slower than individual decisions because
political change happens on a longer timescale than personal actions.
"""
from __future__ import annotations

import json
import logging

from django.conf import settings
from django.db.models import Q

from epocha.apps.agents.affinity import compute_affinity

from .models import Agent, DecisionLog, Group, Memory, Relationship

logger = logging.getLogger(__name__)

# Actions considered cooperative (increase cohesion).
_COOPERATIVE_ACTIONS = {"help", "socialize"}

# Actions considered conflictual (decrease cohesion).
_CONFLICT_ACTIONS = {"argue", "betray"}


def process_faction_dynamics(simulation, tick: int) -> None:
    """Main entry point for faction dynamics. Runs every N ticks.

    Args:
        simulation: The simulation instance.
        tick: Current tick number.
    """
    interval = getattr(settings, "EPOCHA_FACTION_DYNAMICS_INTERVAL", 5)
    if tick % interval != 0:
        return

    groups = list(Group.objects.filter(simulation=simulation, cohesion__gt=0.0))
    for group in groups:
        update_group_cohesion(group, simulation, tick)
        update_group_leadership(group, tick)
        _check_dissolution(group, tick)
        _check_schism(group, simulation, tick)

    _detect_and_propose_factions(simulation, tick)
    _check_join_existing_groups(simulation, tick)
    _process_formation_decisions(simulation, tick)


def compute_leadership_score(agent: Agent, group: Group, tick: int) -> float:
    """Compute leadership score for an agent within their group.

    Formula:
        score = charisma * 0.3 + intelligence * 0.2 + wealth_rank * 0.15
              + internal_sentiment * 0.2 + seniority * 0.15

    Args:
        agent: The agent to score.
        group: The group context.
        tick: Current tick.

    Returns:
        Leadership score between 0.0 and 1.0.
    """
    members = list(Agent.objects.filter(group=group, is_alive=True))
    if not members:
        return 0.0

    # Wealth rank within group (0.0 = poorest, 1.0 = wealthiest)
    sorted_by_wealth = sorted(members, key=lambda a: a.wealth)
    wealth_rank = sorted_by_wealth.index(agent) / max(len(members) - 1, 1)

    # Internal sentiment: average sentiment of relationships with other members
    other_member_ids = [m.id for m in members if m.id != agent.id]
    relationships = Relationship.objects.filter(
        Q(agent_from=agent, agent_to_id__in=other_member_ids)
        | Q(agent_to=agent, agent_from_id__in=other_member_ids)
    )
    if relationships.exists():
        internal_sentiment = sum(r.sentiment for r in relationships) / relationships.count()
        internal_sentiment = (internal_sentiment + 1.0) / 2.0  # Normalize -1..1 to 0..1
    else:
        internal_sentiment = 0.3  # Default: slightly below neutral

    # Seniority: how long the agent has been in the group relative to the group age
    group_age = max(tick - group.formed_at_tick, 1)
    join_memory = (
        Memory.objects.filter(
            agent=agent, is_active=True,
            content__contains=group.name,
        )
        .order_by("tick_created")
        .first()
    )
    join_tick = join_memory.tick_created if join_memory else tick
    seniority = min((tick - join_tick) / group_age, 1.0)

    score = (
        agent.charisma * 0.3
        + agent.intelligence * 0.2
        + wealth_rank * 0.15
        + internal_sentiment * 0.2
        + seniority * 0.15
    )
    return max(0.0, min(1.0, score))


def compute_legitimacy(leader: Agent, group: Group, tick: int) -> float:
    """Compute leadership legitimacy.

    Formula:
        legitimacy = group_cohesion * 0.4 + leader_sentiment * 0.4 + score_rank * 0.2

    Returns:
        Legitimacy score between 0.0 and 1.0.
    """
    members = list(Agent.objects.filter(group=group, is_alive=True))
    if len(members) <= 1:
        return 1.0

    # Leader's internal sentiment
    other_ids = [m.id for m in members if m.id != leader.id]
    relationships = Relationship.objects.filter(
        Q(agent_from=leader, agent_to_id__in=other_ids)
        | Q(agent_to=leader, agent_from_id__in=other_ids)
    )
    if relationships.exists():
        leader_sentiment = sum(r.sentiment for r in relationships) / relationships.count()
        leader_sentiment = (leader_sentiment + 1.0) / 2.0
    else:
        leader_sentiment = 0.3

    # Score rank: 1.0 if leader has highest score, lower otherwise
    scores = [(m, compute_leadership_score(m, group, tick)) for m in members]
    scores.sort(key=lambda x: x[1], reverse=True)
    leader_rank = next((i for i, (m, _) in enumerate(scores) if m.id == leader.id), len(scores))
    score_rank = 1.0 - leader_rank / max(len(members) - 1, 1)

    legitimacy = group.cohesion * 0.4 + leader_sentiment * 0.4 + score_rank * 0.2
    return max(0.0, min(1.0, legitimacy))


def update_group_cohesion(group: Group, simulation, tick: int) -> None:
    """Update a group's cohesion based on member interactions.

    Args:
        group: The group to update.
        simulation: The simulation instance.
        tick: Current tick.
    """
    interval = getattr(settings, "EPOCHA_FACTION_DYNAMICS_INTERVAL", 5)
    members = list(Agent.objects.filter(group=group, is_alive=True))
    member_ids = [m.id for m in members]

    if len(members) < 2:
        return

    # Count cooperative and conflictual actions between members in the last interval
    recent_decisions = DecisionLog.objects.filter(
        simulation=simulation,
        agent_id__in=member_ids,
        tick__gt=max(0, tick - interval),
        tick__lte=tick,
    )

    cooperation_count = 0
    conflict_count = 0
    total_count = 0
    member_names = {m.id: m.name for m in members}

    for decision in recent_decisions:
        try:
            data = json.loads(decision.output_decision)
        except (json.JSONDecodeError, TypeError):
            continue
        action = data.get("action", "")
        target = data.get("target", "")
        # Check if target is another group member
        if target and any(target.lower() in name.lower() for name in member_names.values()):
            total_count += 1
            if action in _COOPERATIVE_ACTIONS:
                cooperation_count += 1
            elif action in _CONFLICT_ACTIONS:
                conflict_count += 1

    total_count = max(total_count, 1)
    cooperation_ratio = cooperation_count / total_count
    conflict_ratio = conflict_count / total_count

    # Size penalty: groups above 5 members lose cohesion faster
    size_penalty = max(0, len(members) - 5)

    # Leader effectiveness
    leader = group.leader
    if leader and leader.is_alive and leader.group_id == group.id:
        legitimacy = compute_legitimacy(leader, group, tick)
        leader_effectiveness = legitimacy - 0.5
    else:
        leader_effectiveness = -0.1  # Leaderless groups destabilize

    delta = (
        cooperation_ratio * 0.1
        - conflict_ratio * 0.15
        - size_penalty * 0.02
        + leader_effectiveness * 0.05
    )
    group.cohesion = max(0.0, min(1.0, group.cohesion + delta))
    group.save(update_fields=["cohesion"])


def update_group_leadership(group: Group, tick: int) -> None:
    """Verify leader legitimacy and replace if below threshold.

    Args:
        group: The group to check.
        tick: Current tick.
    """
    threshold = getattr(settings, "EPOCHA_FACTION_LEGITIMACY_THRESHOLD", 0.3)
    leader = group.leader

    if not leader or not leader.is_alive or leader.group_id != group.id:
        # Leader is gone -- find a new one
        _elect_new_leader(group, tick)
        return

    legitimacy = compute_legitimacy(leader, group, tick)
    if legitimacy < threshold:
        old_leader = leader
        _elect_new_leader(group, tick)
        if group.leader != old_leader:
            # Leadership transition penalty
            group.cohesion = max(0.0, group.cohesion - 0.05)
            group.save(update_fields=["cohesion"])
            # Create memories for all members
            members = Agent.objects.filter(group=group, is_alive=True)
            for member in members:
                Memory.objects.create(
                    agent=member,
                    content=f"{old_leader.name} was replaced by {group.leader.name} as leader of {group.name}.",
                    emotional_weight=0.4,
                    source_type="direct",
                    tick_created=tick,
                )


def _elect_new_leader(group: Group, tick: int) -> None:
    """Set the member with the highest leadership score as leader."""
    members = list(Agent.objects.filter(group=group, is_alive=True))
    if not members:
        return
    scores = [(m, compute_leadership_score(m, group, tick)) for m in members]
    scores.sort(key=lambda x: x[1], reverse=True)
    group.leader = scores[0][0]
    group.save(update_fields=["leader"])


def _check_dissolution(group: Group, tick: int) -> None:
    """Dissolve the group if cohesion is below threshold."""
    threshold = getattr(settings, "EPOCHA_FACTION_DISSOLUTION_THRESHOLD", 0.2)
    if group.cohesion >= threshold:
        return

    members = list(Agent.objects.filter(group=group, is_alive=True))
    Agent.objects.filter(group=group).update(group=None)
    for member in members:
        Memory.objects.create(
            agent=member,
            content=f"{group.name} has dissolved.",
            emotional_weight=0.3,
            source_type="direct",
            tick_created=tick,
        )
    logger.info("Group '%s' dissolved at tick %d (cohesion %.2f)", group.name, tick, group.cohesion)


def _check_schism(group: Group, simulation, tick: int) -> None:
    """Check for internal fractures that could split the group.

    A schism occurs when a subcluster of 3+ members has negative average
    sentiment toward the rest of the group but positive sentiment within
    the subcluster.
    """
    from epocha.apps.llm_adapter.client import get_llm_client

    min_members = getattr(settings, "EPOCHA_FACTION_MIN_MEMBERS", 3)
    members = list(Agent.objects.filter(group=group, is_alive=True))
    if len(members) < min_members * 2:
        # Group too small to split meaningfully
        return

    member_ids = {m.id for m in members}
    # Build sentiment matrix from relationships
    relationships = Relationship.objects.filter(
        agent_from_id__in=member_ids, agent_to_id__in=member_ids,
    )
    sentiment_map = {}
    for rel in relationships:
        sentiment_map[(rel.agent_from_id, rel.agent_to_id)] = rel.sentiment

    # Try to find a disaffected subcluster
    for i, seed in enumerate(members):
        # Find members who have negative sentiment toward the seed's "enemies"
        allies = [seed]
        for other in members:
            if other.id == seed.id:
                continue
            # Sentiment between seed and other
            sent = sentiment_map.get((seed.id, other.id),
                                     sentiment_map.get((other.id, seed.id), 0.0))
            if sent > 0.2:
                allies.append(other)

        if len(allies) < min_members:
            continue

        # Check: do allies have negative sentiment toward non-allies?
        non_allies = [m for m in members if m.id not in {a.id for a in allies}]
        if not non_allies:
            continue

        ally_ids = {a.id for a in allies}
        outward_sentiments = []
        for ally in allies:
            for non_ally in non_allies:
                sent = sentiment_map.get((ally.id, non_ally.id),
                                         sentiment_map.get((non_ally.id, ally.id), 0.0))
                outward_sentiments.append(sent)

        if not outward_sentiments:
            continue
        avg_outward = sum(outward_sentiments) / len(outward_sentiments)

        if avg_outward < -0.2:
            # Schism! Create a splinter group
            try:
                ally_desc = ", ".join(f"{a.name} ({a.role})" for a in allies)
                client = get_llm_client()
                prompt = (
                    f"A faction of {len(allies)} members is splitting from {group.name}. "
                    f"Splinter members: {ally_desc}. Original objective: {group.objective}. "
                    f"Generate a name and objective for the splinter faction. "
                    f"Respond ONLY with JSON: {{\"name\": \"...\", \"objective\": \"...\"}}"
                )
                raw = client.complete(prompt=prompt, system_prompt="You name factions.", max_tokens=80)
                from epocha.common.utils import clean_llm_json
                data = json.loads(clean_llm_json(raw))
                name = data.get("name", f"{group.name} - Dissidents")
                objective = data.get("objective", "Chart our own course")
            except Exception:
                name = f"{group.name} - Dissidents"
                objective = "Chart our own course"

            splinter = Group.objects.create(
                simulation=simulation, name=name, objective=objective,
                cohesion=0.5, formed_at_tick=tick, parent_group=group,
            )
            for ally in allies:
                ally.group = splinter
                ally.save(update_fields=["group"])
                Memory.objects.create(
                    agent=ally,
                    content=f"I left {group.name} and joined {name}.",
                    emotional_weight=0.4, source_type="direct", tick_created=tick,
                )

            # Elect leader for splinter
            scores = [(a, compute_leadership_score(a, splinter, tick)) for a in allies]
            scores.sort(key=lambda x: x[1], reverse=True)
            splinter.leader = scores[0][0]
            splinter.save(update_fields=["leader"])

            # Impact on original group
            group.cohesion = max(0.0, group.cohesion - 0.1)
            group.save(update_fields=["cohesion"])

            for member in members:
                if member.id not in ally_ids:
                    Memory.objects.create(
                        agent=member,
                        content=f"{name} has split from {group.name}.",
                        emotional_weight=0.3, source_type="direct", tick_created=tick,
                    )

            logger.info("Schism in '%s': '%s' formed with %d members at tick %d",
                        group.name, name, len(allies), tick)
            return  # Only one schism per tick per group


def _detect_and_propose_factions(simulation, tick: int) -> None:
    """Identify potential faction clusters among ungrouped agents.

    Stores faction proposals as memories with a special marker so the
    decision pipeline can include them in the context.
    """
    threshold = getattr(settings, "EPOCHA_FACTION_AFFINITY_THRESHOLD", 0.5)
    min_members = getattr(settings, "EPOCHA_FACTION_MIN_MEMBERS", 3)
    max_members = getattr(settings, "EPOCHA_FACTION_MAX_INITIAL_MEMBERS", 8)

    ungrouped = list(
        Agent.objects.filter(simulation=simulation, is_alive=True, group=None)
        .order_by("name")
    )
    if len(ungrouped) < min_members:
        return

    # Build affinity graph
    clusters = []
    visited = set()

    for i, agent_a in enumerate(ungrouped):
        if agent_a.id in visited:
            continue
        cluster = [agent_a]
        for agent_b in ungrouped[i + 1:]:
            if agent_b.id in visited:
                continue
            if len(cluster) >= max_members:
                break
            # Check affinity with ALL current cluster members
            affinities = [compute_affinity(agent_b, c, tick) for c in cluster]
            if all(a >= threshold for a in affinities):
                cluster.append(agent_b)

        if len(cluster) >= min_members:
            for agent in cluster:
                visited.add(agent.id)
                other_names = ", ".join(a.name for a in cluster if a.id != agent.id)
                # Check if agent already has a recent proposal memory
                has_proposal = Memory.objects.filter(
                    agent=agent, content__contains="share common ground",
                    tick_created__gte=max(0, tick - 5),
                ).exists()
                if not has_proposal:
                    Memory.objects.create(
                        agent=agent,
                        content=f"I share common ground with {other_names}. We face similar circumstances and could organize together.",
                        emotional_weight=0.2,
                        source_type="direct",
                        tick_created=tick,
                    )
            clusters.append(cluster)

    if clusters:
        logger.info("Detected %d potential faction cluster(s) at tick %d", len(clusters), tick)


def _check_join_existing_groups(simulation, tick: int) -> None:
    """Check if ungrouped agents should be suggested to join existing groups."""
    threshold = getattr(settings, "EPOCHA_FACTION_AFFINITY_THRESHOLD", 0.5)
    ungrouped = list(
        Agent.objects.filter(simulation=simulation, is_alive=True, group=None)
    )
    groups = list(Group.objects.filter(simulation=simulation, cohesion__gt=0.0))

    for agent in ungrouped:
        for group in groups:
            members = list(Agent.objects.filter(group=group, is_alive=True)[:5])
            if not members:
                continue
            avg_affinity = sum(compute_affinity(agent, m, tick) for m in members) / len(members)
            # Also require at least one positive relationship with a member
            has_positive_rel = Relationship.objects.filter(
                Q(agent_from=agent, agent_to__in=members, sentiment__gt=0)
                | Q(agent_to=agent, agent_from__in=members, sentiment__gt=0)
            ).exists()
            if avg_affinity >= threshold and has_positive_rel:
                has_suggestion = Memory.objects.filter(
                    agent=agent, content__contains=group.name,
                    tick_created__gte=max(0, tick - 5),
                ).exists()
                if not has_suggestion:
                    member_name = members[0].name
                    Memory.objects.create(
                        agent=agent,
                        content=f"The {group.name} shares my values. {member_name} is a member. I could join them.",
                        emotional_weight=0.2,
                        source_type="direct",
                        tick_created=tick,
                    )
                break  # Only suggest one group per agent


def _process_formation_decisions(simulation, tick: int) -> None:
    """Check if enough agents decided to form_group and create the group.

    Reads recent DecisionLog entries for "form_group" actions and groups
    agents who share a common proposal memory into a faction.
    """
    from epocha.apps.llm_adapter.client import get_llm_client

    interval = getattr(settings, "EPOCHA_FACTION_DYNAMICS_INTERVAL", 5)
    min_members = getattr(settings, "EPOCHA_FACTION_MIN_MEMBERS", 3)

    # Find agents who decided form_group or join_group recently
    recent_form_decisions = DecisionLog.objects.filter(
        simulation=simulation,
        tick__gt=max(0, tick - interval),
        tick__lte=tick,
    )

    formers = []
    joiners = {}  # group_name -> [agents]

    for decision in recent_form_decisions:
        try:
            data = json.loads(decision.output_decision)
        except (json.JSONDecodeError, TypeError):
            continue
        action = data.get("action", "")
        agent = decision.agent
        if action == "form_group" and agent.group is None:
            formers.append(agent)
        elif action == "join_group" and agent.group is None:
            target = data.get("target", "")
            if target:
                joiners.setdefault(target, []).append(agent)

    # Process join requests for existing groups
    for group_name, agents in joiners.items():
        group = Group.objects.filter(simulation=simulation, name__icontains=group_name).first()
        if group and group.cohesion > 0.0:
            for agent in agents:
                agent.group = group
                agent.save(update_fields=["group"])
                Memory.objects.create(
                    agent=agent,
                    content=f"I joined {group.name}.",
                    emotional_weight=0.3,
                    source_type="direct",
                    tick_created=tick,
                )
                # Slight cohesion drop for new member integration
                group.cohesion = max(0.0, group.cohesion - 0.02)
                group.save(update_fields=["cohesion"])

    # Process new group formation
    if len(formers) >= min_members:
        # Cluster formers by who shares a proposal memory
        # (they should have been in the same detected cluster)
        used = set()
        for i, agent_a in enumerate(formers):
            if agent_a.id in used:
                continue
            cluster = [agent_a]
            proposal = Memory.objects.filter(
                agent=agent_a, content__contains="share common ground",
                tick_created__gte=max(0, tick - interval * 2),
            ).first()
            if not proposal:
                continue
            for agent_b in formers[i + 1:]:
                if agent_b.id in used:
                    continue
                if agent_b.name in proposal.content:
                    cluster.append(agent_b)
                    used.add(agent_b.id)
            used.add(agent_a.id)

            if len(cluster) >= min_members:
                _create_faction(simulation, cluster, tick)


def _create_faction(simulation, founders: list[Agent], tick: int) -> None:
    """Create a new faction from a list of founding agents."""
    from epocha.apps.llm_adapter.client import get_llm_client

    founder_desc = ", ".join(f"{a.name} ({a.role})" for a in founders)
    classes = set(a.social_class for a in founders)
    roles = set(a.role for a in founders if a.role)

    # Generate name and objective via LLM
    try:
        client = get_llm_client()
        prompt = (
            f"A group of people have decided to organize together: {founder_desc}. "
            f"Social classes: {', '.join(classes)}. Occupations: {', '.join(roles)}. "
            f"Generate a faction name and one-sentence objective. "
            f"Respond ONLY with JSON: {{\"name\": \"...\", \"objective\": \"...\"}}"
        )
        raw = client.complete(prompt=prompt, system_prompt="You name factions.", max_tokens=80)
        from epocha.common.utils import clean_llm_json
        data = json.loads(clean_llm_json(raw))
        name = data.get("name", f"The {founders[0].role.title()} Alliance")
        objective = data.get("objective", "Pursue shared interests")
    except Exception:
        logger.warning("Failed to generate faction name via LLM, using fallback")
        name = f"The {founders[0].role.title()} Alliance"
        objective = "Pursue shared interests"

    group = Group.objects.create(
        simulation=simulation,
        name=name,
        objective=objective,
        cohesion=0.6,
        formed_at_tick=tick,
    )

    # Assign leader (highest leadership score)
    scores = [(a, compute_leadership_score(a, group, tick)) for a in founders]
    scores.sort(key=lambda x: x[1], reverse=True)
    group.leader = scores[0][0]
    group.save(update_fields=["leader"])

    # Assign all founders to group
    for agent in founders:
        agent.group = group
        agent.save(update_fields=["group"])
        Memory.objects.create(
            agent=agent,
            content=f"I helped found {name} with {', '.join(a.name for a in founders if a.id != agent.id)}.",
            emotional_weight=0.3,
            source_type="direct",
            tick_created=tick,
        )

    # Public announcement
    all_agents = Agent.objects.filter(simulation=simulation, is_alive=True)
    for agent in all_agents:
        if agent.group_id != group.id:
            Memory.objects.create(
                agent=agent,
                content=f"{name} has been formed by {founder_desc}, pursuing: {objective}.",
                emotional_weight=0.2,
                source_type="public",
                reliability=1.0,
                tick_created=tick,
            )

    logger.info("Faction '%s' created at tick %d with %d founders", name, tick, len(founders))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `docker compose -f docker-compose.local.yml exec -T web pytest epocha/apps/agents/tests/test_factions.py -v`
Expected: All tests PASS.

- [ ] **Step 5: Commit**

```
feat(agents): add faction dynamics engine with cohesion and leadership

CHANGE: Implement process_faction_dynamics() with cohesion updates based
on member interactions, leadership score computation, legitimacy-based
contestation, dissolution when cohesion falls below threshold, cluster
detection for new factions, and group creation with LLM-generated names.
```

---

### Task 4: Decision Pipeline Integration

Add form_group/join_group actions and enrich the agent context with group information.

**Files:**
- Modify: `epocha/apps/agents/decision.py:22-31` (system prompt)
- Modify: `epocha/apps/agents/decision.py:42-98` (`_build_context`)
- Modify: `epocha/apps/simulation/engine.py:34-57` (action weights and mood deltas)
- Modify: `epocha/apps/dashboard/formatters.py:9-20` (action verbs)
- Test: `epocha/apps/agents/tests/test_decision.py`

- [ ] **Step 1: Write the failing test**

Add to `epocha/apps/agents/tests/test_decision.py`, inside `TestProcessAgentDecision`:

```python
@patch("epocha.apps.agents.decision.get_llm_client")
def test_context_includes_group_info(self, mock_get_client, agent, world, simulation):
    """If the agent belongs to a group, the context should include group details."""
    group = Group.objects.create(
        simulation=simulation, name="The Guild", objective="Protect artisans",
        cohesion=0.7, formed_at_tick=1,
    )
    agent.group = group
    agent.save(update_fields=["group"])
    group.leader = agent
    group.save(update_fields=["leader"])

    mock_client = MagicMock()
    mock_client.complete.return_value = '{"action": "work", "reason": "busy"}'
    mock_client.get_model_name.return_value = "gpt-4o-mini"
    mock_get_client.return_value = mock_client

    process_agent_decision(agent, world, tick=5)

    call_args = mock_client.complete.call_args
    prompt = call_args.kwargs.get("prompt", call_args.args[0] if call_args.args else "")
    assert "The Guild" in prompt
    assert "Protect artisans" in prompt
```

Add `Group` to the imports at the top of the test file:

```python
from epocha.apps.agents.models import Agent, DecisionLog, Group, Memory
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker compose -f docker-compose.local.yml exec -T web pytest epocha/apps/agents/tests/test_decision.py::TestProcessAgentDecision::test_context_includes_group_info -v`
Expected: FAIL (group info not in prompt yet).

- [ ] **Step 3: Update the system prompt with new actions**

In `epocha/apps/agents/decision.py`, update `_DECISION_SYSTEM_PROMPT` (line 22):

```python
_DECISION_SYSTEM_PROMPT = """You are simulating a person in a world. Based on your personality,
memories, relationships, and current situation, decide what to do next.

Respond ONLY with a JSON object:
{
    "action": "work|rest|socialize|explore|trade|argue|help|avoid|form_group|join_group",
    "target": "who or what (optional)",
    "reason": "brief internal thought"
}
"""
```

- [ ] **Step 4: Add group context to _build_context**

In `epocha/apps/agents/decision.py`, update `_build_context` to accept a `group_context` parameter and add it to the prompt. Add after the `living_agents` section (line 74) and before the `recent_events` section:

Add the parameter to the signature:

```python
def _build_context(
    agent,
    world_state,
    tick: int,
    memories,
    relationships,
    recent_events=None,
    living_agents=None,
    group_context=None,
) -> str:
```

Add this block after the living_agents section:

```python
    # Group/faction context
    if group_context:
        parts.append(f"\n{group_context}")
```

- [ ] **Step 5: Build group context in process_agent_decision**

In `process_agent_decision`, after the `living_agents` query (line ~135), add:

```python
    # Build group context for the agent
    group_context = None
    if agent.group_id:
        group = agent.group
        members = list(
            Agent.objects.filter(group=group, is_alive=True)
            .exclude(id=agent.id)
            .only("name", "role")[:10]
        )
        member_list = ", ".join(f"{m.name} ({m.role})" for m in members)
        leader_name = group.leader.name if group.leader else "no leader"
        cohesion_word = "strong" if group.cohesion > 0.6 else "moderate" if group.cohesion > 0.3 else "fragile"
        group_context = (
            f"Your faction: {group.name} (objective: {group.objective})\n"
            f"Leader: {leader_name}\n"
            f"Members: {member_list}\n"
            f"Group cohesion: {cohesion_word}"
        )
```

Pass `group_context` to `_build_context`:

```python
    context = _build_context(
        agent, world_state, tick, memories, relationships, recent_events, living_agents, group_context
    )
```

- [ ] **Step 6: Add action weights and mood deltas for new actions**

In `epocha/apps/simulation/engine.py`, add to `_ACTION_EMOTIONAL_WEIGHT` dict:

```python
    "form_group": 0.3,
    "join_group": 0.3,
```

Add to `_ACTION_MOOD_DELTA` dict:

```python
    "form_group": 0.04,
    "join_group": 0.03,
```

- [ ] **Step 7: Add verbs to dashboard formatters**

In `epocha/apps/dashboard/formatters.py`, add to `_ACTION_VERBS` dict:

```python
    "form_group": "forms a group",
    "join_group": "joins a group",
```

- [ ] **Step 8: Run all tests**

Run: `docker compose -f docker-compose.local.yml exec -T web pytest epocha/apps/agents/ epocha/apps/simulation/ epocha/apps/dashboard/ -v`
Expected: All tests PASS.

- [ ] **Step 9: Commit**

```
feat(agents): integrate factions into decision pipeline

CHANGE: Add form_group and join_group as possible agent actions. Enrich
the decision context with faction info (name, objective, leader, members,
cohesion). Add emotional weights and mood deltas for the new actions.
Update dashboard formatters with group action verbs.
```

---

### Task 5: Tick Engine Integration

Wire `process_faction_dynamics` into both the synchronous engine and Celery path.

**Files:**
- Modify: `epocha/apps/simulation/engine.py:240-244`
- Modify: `epocha/apps/simulation/tasks.py:97-99`
- Test: `epocha/apps/simulation/tests/test_engine.py`

- [ ] **Step 1: Write the failing test**

Add to `epocha/apps/simulation/tests/test_engine.py`, inside `TestSimulationEngine`:

```python
@patch("epocha.apps.simulation.engine.process_agent_decision")
def test_faction_dynamics_runs_at_interval(self, mock_decision, sim_with_world):
    """Faction dynamics should run at the configured interval."""
    mock_decision.return_value = {"action": "work", "reason": "busy"}
    engine = SimulationEngine(sim_with_world)

    # Run 5 ticks (default interval)
    with patch("epocha.apps.simulation.engine.process_faction_dynamics") as mock_factions:
        for _ in range(5):
            engine.run_tick()
        # Should have been called once (at tick 5)
        assert mock_factions.call_count == 5  # Called every tick but no-op except at interval
```

Add the import at top of test file:

```python
from epocha.apps.agents.models import Agent, Memory, Relationship
```

(Relationship should already be imported from Task 5 of the previous plan.)

- [ ] **Step 2: Run test to verify it fails**

Run: `docker compose -f docker-compose.local.yml exec -T web pytest epocha/apps/simulation/tests/test_engine.py::TestSimulationEngine::test_faction_dynamics_runs_at_interval -v`
Expected: FAIL (process_faction_dynamics not called yet).

- [ ] **Step 3: Add faction dynamics call to engine**

In `epocha/apps/simulation/engine.py`, add the import at the top:

```python
from epocha.apps.agents.factions import process_faction_dynamics
```

In `run_tick()`, after the information flow call (line ~241) and before memory decay, add:

```python
        # 4. Faction dynamics (every N ticks)
        process_faction_dynamics(self.simulation, tick)
```

Renumber subsequent comments (memory decay becomes 5, advance tick becomes 6, broadcast becomes 7).

- [ ] **Step 4: Add faction dynamics call to Celery finalize_tick**

In `epocha/apps/simulation/tasks.py`, in `finalize_tick()`, after the information flow call and before memory decay, add:

```python
    # Faction dynamics (every N ticks)
    from epocha.apps.agents.factions import process_faction_dynamics
    process_faction_dynamics(simulation, tick)
```

- [ ] **Step 5: Run all tests**

Run: `docker compose -f docker-compose.local.yml exec -T web pytest -q`
Expected: All tests PASS.

- [ ] **Step 6: Commit**

```
feat(simulation): integrate faction dynamics into tick engine

CHANGE: Call process_faction_dynamics() after information flow in both
the synchronous engine and the Celery chord path. Faction dynamics run
every 5 ticks by default, handling cohesion updates, leadership
verification, cluster detection, and group formation.
```

---

### Task 6: Update engine docstring

**Files:**
- Modify: `epocha/apps/simulation/engine.py:1-17`

- [ ] **Step 1: Update module docstring**

Replace the module docstring:

```python
"""Tick orchestrator: coordinates economy, decisions, information flow, factions, memory, and events.

Each tick is a discrete time step where:
1. The economy updates (income, costs, mood effects)
2. Each living agent makes a decision via LLM
3. Decision consequences are applied (mood, health adjustments)
4. Memories are created from actions
5. Information propagates through the social network (hearsay, rumors)
6. Faction dynamics run periodically (cohesion, leadership, formation)
7. Old memories decay periodically
8. The tick counter advances

Agent failures are isolated: if one agent's LLM call fails, the tick
continues for all other agents. This ensures simulation resilience.

Module-level functions (run_economy, run_memory_decay, broadcast_tick) are
used by both the SimulationEngine (synchronous path) and the Celery chord
tasks (production path). This avoids duplicating logic across execution modes.
"""
```

- [ ] **Step 2: Commit**

```
docs(simulation): update engine docstring with faction dynamics step

CHANGE: Engine module docstring now reflects the 8-step tick flow
including faction dynamics phase.
```

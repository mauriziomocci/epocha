"""Pairwise affinity calculation between two agents.

Affinity measures how likely two agents are to form a coalition or join the
same faction. It is a weighted composite of three orthogonal dimensions:

1. Personality similarity (Big Five cosine-inspired distance)
   Based on: McCrae & Costa (2003) "Personality in Adulthood", 2nd ed.,
   Guilford Press. The five-factor model is the standard framework for
   measuring personality similarity between individuals.

2. Relationship quality (existing social bond)
   Captures established trust and sentiment from prior interactions.

3. Circumstance alignment (shared material and situational conditions)
   Inspired by: Olson (1965) "The Logic of Collective Action", Harvard
   University Press. Groups form around shared grievances and conditions,
   not just personality fit.

Weight rationale:
  - Circumstances weigh 40% because factions form primarily around shared
    material conditions (same class, same hardship, same crisis), not just
    personality match.
  - Personality and relationship each weigh 30%, reflecting that
    long-term group cohesion requires compatible temperament and
    established trust.
"""
from __future__ import annotations

import math

from django.db.models import Q

from .models import Agent, Memory, Relationship

# Big Five trait keys in a fixed, canonical order.
_BIG_FIVE: tuple[str, ...] = (
    "openness",
    "conscientiousness",
    "extraversion",
    "agreeableness",
    "neuroticism",
)

# Default value used when a trait is missing or non-numeric.
# 0.5 is the midpoint of [0, 1] — a neutral, uninformative prior.
_TRAIT_DEFAULT: float = 0.5

# Maximum Euclidean distance across all five traits when each ranges [0, 1].
# sqrt(5 * 1^2) = sqrt(5) ≈ 2.236
_MAX_BIG_FIVE_DISTANCE: float = math.sqrt(5)

# Number of ticks in the recent window used to detect shared crisis events.
_SHARED_MEMORY_WINDOW: int = 10

# Component weights — must sum to 1.0.
_W_PERSONALITY: float = 0.3
_W_RELATIONSHIP: float = 0.3
_W_CIRCUMSTANCE: float = 0.4


def compute_affinity(agent_a: Agent, agent_b: Agent, tick: int) -> float:
    """Return a [0.0, 1.0] affinity score between two agents at a given tick.

    Higher values indicate that the two agents are more likely to form or
    join the same faction together. The score is symmetric:
    compute_affinity(a, b, t) == compute_affinity(b, a, t).

    The score is a weighted average of three components:
      - personality similarity (Big Five Euclidean distance): 30%
      - relationship quality (strength + sentiment): 30%
      - circumstance alignment (class, mood, events, wealth, role): 40%

    Args:
        agent_a: First agent.
        agent_b: Second agent.
        tick: Current simulation tick (used for memory recency window).

    Returns:
        Float in [0.0, 1.0].
    """
    personality = _personality_similarity(agent_a.personality, agent_b.personality)
    relationship = _relationship_score(agent_a, agent_b)
    circumstance = _circumstance_score(agent_a, agent_b, tick)

    score = (
        _W_PERSONALITY * personality
        + _W_RELATIONSHIP * relationship
        + _W_CIRCUMSTANCE * circumstance
    )
    # Clamp to [0.0, 1.0] as a defensive guard against floating-point drift.
    return max(0.0, min(1.0, score))


def _personality_similarity(personality_a: dict, personality_b: dict) -> float:
    """Return personality similarity in [0.0, 1.0] using Big Five Euclidean distance.

    Similarity is 1 minus the normalized distance: two identical personalities
    yield 1.0; maximally opposite personalities yield 0.0.

    Non-numeric or missing traits are replaced with the neutral midpoint 0.5,
    which contributes zero to the distance for the missing dimension — an
    uninformative assumption consistent with treating unknown traits as average.

    Reference: McCrae & Costa (2003) "Personality in Adulthood", Guilford Press.

    Args:
        personality_a: Big Five dict for agent A.
        personality_b: Big Five dict for agent B.

    Returns:
        Float in [0.0, 1.0].
    """
    def _get_trait(personality: dict, trait: str) -> float:
        value = personality.get(trait, _TRAIT_DEFAULT)
        return value if isinstance(value, (int, float)) else _TRAIT_DEFAULT

    squared_sum = sum(
        (_get_trait(personality_a, trait) - _get_trait(personality_b, trait)) ** 2
        for trait in _BIG_FIVE
    )
    distance = math.sqrt(squared_sum)
    return 1.0 - (distance / _MAX_BIG_FIVE_DISTANCE)


def _relationship_score(agent_a: Agent, agent_b: Agent) -> float:
    """Return a [0.0, 1.0] score from the existing relationship between the agents.

    Checks both directions (A->B and B->A) so the result is symmetric even
    when only one agent has logged the relationship. If no relationship
    exists, returns 0.0 — no established bond means no contribution.

    Score formula: (strength + max(0, sentiment)) / 2
      - Strength is always non-negative and reflects how significant the
        bond is, regardless of valence.
      - Only positive sentiment boosts the score; negative sentiment
        (hatred, rivalry) does not reduce it below the strength baseline,
        because even hostile relationships involve high interdependence.

    Args:
        agent_a: First agent.
        agent_b: Second agent.

    Returns:
        Float in [0.0, 1.0].
    """
    try:
        rel = Relationship.objects.get(
            Q(agent_from=agent_a, agent_to=agent_b)
            | Q(agent_from=agent_b, agent_to=agent_a)
        )
    except Relationship.DoesNotExist:
        return 0.0
    except Relationship.MultipleObjectsReturned:
        # When both directions exist, take the stronger one.
        rel = (
            Relationship.objects.filter(
                Q(agent_from=agent_a, agent_to=agent_b)
                | Q(agent_from=agent_b, agent_to=agent_a)
            )
            .order_by("-strength")
            .first()
        )

    return (rel.strength + max(0.0, rel.sentiment)) / 2.0


def _circumstance_score(agent_a: Agent, agent_b: Agent, tick: int) -> float:
    """Return a [0.0, 1.0] score measuring shared situational conditions.

    Circumstances are the primary driver of faction formation (Olson, 1965):
    people band together because they face the same hardships, not just
    because they like each other.

    Additive factors (capped at 1.0):
      +0.30  same social_class  — structural solidarity (class consciousness)
      +0.20  both mood < 0.4   — shared grievance / discontent
      +0.20  shared public memory in last 10 ticks — common crisis experience
      +0.15  same wealth quartile (|wealth_a - wealth_b| / max_wealth < 0.25)
      +0.15  same role          — occupational solidarity

    Args:
        agent_a: First agent.
        agent_b: Second agent.
        tick: Current simulation tick.

    Returns:
        Float in [0.0, 1.0].
    """
    score = 0.0

    # Same social class: the strongest structural bond.
    if agent_a.social_class == agent_b.social_class:
        score += 0.30

    # Shared discontent: both agents are suffering (mood below 0.4).
    if agent_a.mood < 0.4 and agent_b.mood < 0.4:
        score += 0.20

    # Shared recent public memory: both witnessed the same crisis event.
    # Match on exact content string within the recency window.
    recent_tick = tick - _SHARED_MEMORY_WINDOW
    contents_a = set(
        Memory.objects.filter(
            agent=agent_a,
            source_type=Memory.SourceType.PUBLIC,
            tick_created__gte=recent_tick,
            is_active=True,
        ).values_list("content", flat=True)
    )
    contents_b = set(
        Memory.objects.filter(
            agent=agent_b,
            source_type=Memory.SourceType.PUBLIC,
            tick_created__gte=recent_tick,
            is_active=True,
        ).values_list("content", flat=True)
    )
    if contents_a & contents_b:
        score += 0.20

    # Same wealth quartile: economic proximity fosters solidarity.
    # Guard against division by zero when both agents have zero wealth.
    max_wealth = max(agent_a.wealth, agent_b.wealth)
    if max_wealth > 0.0:
        wealth_diff_ratio = abs(agent_a.wealth - agent_b.wealth) / max_wealth
        if wealth_diff_ratio < 0.25:
            score += 0.15
    else:
        # Both agents have zero wealth — same quartile by definition.
        score += 0.15

    # Same occupational role: professional solidarity.
    if agent_a.role and agent_b.role and agent_a.role == agent_b.role:
        score += 0.15

    return min(1.0, score)

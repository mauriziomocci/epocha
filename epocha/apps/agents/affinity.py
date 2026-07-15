"""Pairwise affinity calculation between two agents.

Affinity measures how likely two agents are to form a coalition or join the
same faction. It is a weighted composite of three orthogonal dimensions:

1. Personality similarity (Big Five Euclidean distance)
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

Prefetched context (Round 3 hardening, FR-001, FR-011):
  `_relationship_score` and `_circumstance_score` are the only two
  DB-coupled components of the score (personality similarity is pure
  computation on already-loaded fields). Both accept an optional
  `AffinityContext`, built once per tick by `build_affinity_context`, that
  replaces their per-pair Relationship/Memory queries with O(1) in-memory
  lookups. This is data injection, not logic duplication: the scoring
  formulas stay exactly where they are in these two functions -- the
  context only changes where their inputs come from. Without a context
  (default `None`), both functions behave exactly as before this change:
  one query path, one query per call.

  Determinism rationale: `_relationship_score` previously broke a strength
  tie between two Relationship rows with `.order_by("-strength").first()`,
  which has no secondary sort key -- on Postgres, without an explicit
  ORDER BY tiebreak, the row returned for equal `strength` values is
  implementation-defined and not guaranteed stable across query plans or
  table layout. FR-011 adds `id` as a secondary, always-unique sort key
  (`order_by("-strength", "id")`), and the context path replicates the
  identical `(-strength, id)` selection in-memory when grouping prefetched
  rows by pair. This makes the tie-break deterministic on BOTH paths, which
  is also the precondition for exact numeric equivalence between the
  batched and non-batched code paths (a tie with no defined winner cannot
  be reproduced identically by two independent selections).
"""

from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import dataclass

from django.db.models import Q

from .models import Agent, Memory, Relationship


@dataclass
class AffinityContext:
    """Prefetched Relationship/Memory data for batched affinity scoring.

    Built once per tick by `build_affinity_context` and threaded through
    `compute_affinity` (and its helpers `_relationship_score`,
    `_circumstance_score`) to replace their per-pair DB queries with
    in-memory lookups. See the module docstring's "Prefetched context"
    section for the data-injection rationale.

    Attributes:
        relationships: maps an unordered pair key
            (``frozenset({agent_from_id, agent_to_id})``) to the single
            Relationship row `_relationship_score` would select for that
            pair -- the strongest relationship, tie-broken by the lowest
            id (FR-011). A pair with no relationship at all is simply
            absent from the dict.
        memories: maps an agent id to the set of PUBLIC, active memory
            contents created within the shared-memory window
            (``tick - _SHARED_MEMORY_WINDOW``), matching exactly the
            filters `_circumstance_score` applies per agent. Built once
            per agent (memoization), not once per pair.
    """

    relationships: dict[frozenset[int], Relationship]
    memories: dict[int, set[str]]


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


def compute_affinity(
    agent_a: Agent, agent_b: Agent, tick: int, context: AffinityContext | None = None
) -> float:
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
        context: Optional prefetched `AffinityContext` (see
            `build_affinity_context`). When provided, the relationship and
            circumstance components are resolved from it with zero
            queries; the result is numerically identical to the default
            (`context=None`) query path -- see module docstring, section
            "Prefetched context".

    Returns:
        Float in [0.0, 1.0].
    """
    personality = _personality_similarity(agent_a.personality, agent_b.personality)
    relationship = _relationship_score(agent_a, agent_b, context=context)
    circumstance = _circumstance_score(agent_a, agent_b, tick, context=context)

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

    Non-numeric or missing traits default to 0.5 for that agent. If BOTH
    agents are missing the trait, that dimension contributes zero distance.
    If only ONE agent has the trait missing, the present trait value is
    compared against 0.5 — producing a non-zero distance proportional to
    how far the present value is from neutral. This asymmetric behavior is
    a known limitation of the default-to-midpoint imputation; closes
    Round 2 finding N-7.

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


def _relationship_score(
    agent_a: Agent, agent_b: Agent, context: AffinityContext | None = None
) -> float:
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

    Rival relationships contribute to coalition affinity through repeated-
    interaction reciprocity dynamics (Axelrod 1984 *The Evolution of
    Cooperation*, already in whitepaper §13; alternative: Coleman 1990
    *Foundations of Social Theory* on coalition stability under rivalry,
    NOT in whitepaper §13). Closes Round 2 finding N-8.

    Deterministic tie-break (Round 3 hardening, FR-011): when both
    directions and/or multiple `relation_type` rows exist for the same
    pair, the strongest relationship wins; on an exact strength tie, the
    row with the LOWEST id wins. Before this fix, the tie fell back to
    `.order_by("-strength").first()` with no secondary sort key, so on an
    exact tie (e.g. the 0.5 default `strength`, a common case for pairs
    with more than one `relation_type` or both directions logged) the row
    Postgres returned was implementation-defined. The `(-strength, id)`
    key is a tunable heuristic for WHICH record wins a tie (favoring the
    strongest record regardless of type, then the earliest-created one) —
    it is not itself derived from a cited source; what FR-011 fixes is
    that the choice is now reproducible rather than arbitrary. See the
    module docstring's "Prefetched context" section for why this matters
    for the batched/non-batched equivalence guarantee (SC-003).

    Args:
        agent_a: First agent.
        agent_b: Second agent.
        context: Optional prefetched `AffinityContext`. When provided, the
            relationship is resolved from `context.relationships` with
            zero queries, applying the identical `(-strength, id)`
            tie-break key used to build that dict. When `None` (default),
            behavior is unchanged: a query per call.

    Returns:
        Float in [0.0, 1.0].
    """
    if context is not None:
        rel = context.relationships.get(frozenset({agent_a.id, agent_b.id}))
        if rel is None:
            return 0.0
        return (rel.strength + max(0.0, rel.sentiment)) / 2.0

    try:
        rel = Relationship.objects.get(
            Q(agent_from=agent_a, agent_to=agent_b) | Q(agent_from=agent_b, agent_to=agent_a)
        )
    except Relationship.DoesNotExist:
        return 0.0
    except Relationship.MultipleObjectsReturned:
        # Deterministic tie-break (FR-011): strongest relationship first;
        # on an exact strength tie, the lowest id wins. `id` is the
        # secondary sort key that removes the Postgres scan-order
        # dependency of the previous `.order_by("-strength").first()`.
        rel = (
            Relationship.objects.filter(
                Q(agent_from=agent_a, agent_to=agent_b) | Q(agent_from=agent_b, agent_to=agent_a)
            )
            .order_by("-strength", "id")
            .first()
        )

    return (rel.strength + max(0.0, rel.sentiment)) / 2.0


def _circumstance_score(
    agent_a: Agent, agent_b: Agent, tick: int, context: AffinityContext | None = None
) -> float:
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
        context: Optional prefetched `AffinityContext`. When provided, the
            per-agent public-memory content sets are read from
            `context.memories` (built once per agent, not once per pair)
            instead of issuing two Memory queries. When `None` (default),
            behavior is unchanged: two queries per call.

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
    if context is not None:
        contents_a = context.memories.get(agent_a.id, set())
        contents_b = context.memories.get(agent_b.id, set())
    else:
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
    # Wealth similarity threshold (25% relative difference). Tunable design
    # parameter without empirical source.
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


def build_affinity_context(
    agents_a: Iterable[Agent], agents_b: Iterable[Agent], tick: int
) -> AffinityContext:
    """Prefetch Relationship and Memory data for every pair across two agent sets.

    Issues exactly two queries regardless of how many agents or pairs are
    involved, replacing the per-pair queries that `_relationship_score` and
    `_circumstance_score` would otherwise issue when called through
    `compute_affinity(..., context=...)`. This is the data-injection
    mechanism of Round 3 hardening (FR-001): `_relationship_score` and
    `_circumstance_score` remain the single home of the scoring formulas —
    this function only changes how their inputs are sourced, so there is no
    twin logic to keep in sync.

    The fetch is a SUPERSET over the union of `agents_a` and `agents_b`:
    both queries filter on the combined id set rather than on cross-pairs
    only, so the same context also answers lookups for pairs INSIDE
    `agents_a` or INSIDE `agents_b` (e.g. two group members' relationship
    to each other), not just between the two sets. Fetching a few rows the
    immediate caller does not need is harmless and cheaper than a second,
    narrower query per grouping.

    Args:
        agents_a: First set of agents (e.g. ungrouped candidates).
        agents_b: Second set of agents (e.g. a group's living members).
        tick: Current simulation tick (drives the Memory recency window).

    Returns:
        An `AffinityContext` ready to pass to `compute_affinity`.
    """
    ids = {a.id for a in agents_a} | {b.id for b in agents_b}

    # Query 1/2: every Relationship row between any two agents in `ids`,
    # both directions and every relation_type, in ONE query. Grouped
    # in-memory by unordered pair key, keeping only the winner of the
    # deterministic tie-break (-strength, id) per pair — the identical
    # selection `_relationship_score`'s query path applies via
    # `order_by("-strength", "id")` (FR-011). Rows are consumed in that
    # same order, so the first row seen for a given key is already the
    # winner and later rows for the same key must not overwrite it.
    relationships: dict[frozenset[int], Relationship] = {}
    ordered_relationships = Relationship.objects.filter(
        agent_from_id__in=ids, agent_to_id__in=ids
    ).order_by("-strength", "id")
    for rel in ordered_relationships:
        key = frozenset({rel.agent_from_id, rel.agent_to_id})
        if key not in relationships:
            relationships[key] = rel

    # Query 2/2: every PUBLIC, active Memory of any agent in `ids` created
    # within the shared-memory window, in ONE query. Filters mirror
    # `_circumstance_score` exactly: source_type=PUBLIC, is_active=True,
    # tick_created__gte=tick - _SHARED_MEMORY_WINDOW. Content sets are
    # built once per agent here (memoization), not once per pair.
    recent_tick = tick - _SHARED_MEMORY_WINDOW
    memories: dict[int, set[str]] = {agent_id: set() for agent_id in ids}
    memory_rows = Memory.objects.filter(
        agent_id__in=ids,
        source_type=Memory.SourceType.PUBLIC,
        is_active=True,
        tick_created__gte=recent_tick,
    ).values_list("agent_id", "content")
    for agent_id, content in memory_rows:
        memories[agent_id].add(content)

    return AffinityContext(relationships=relationships, memories=memories)

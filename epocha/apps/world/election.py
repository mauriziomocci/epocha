"""Deterministic election system for the Epocha simulator.

Agents vote based on five weighted factors that model real-world electoral behaviour:

1. Relationship sentiment (25%): direct social bonds are the strongest predictor
   of individual vote choice. Voters who know a candidate personally are strongly
   influenced by that relationship.
   Reference: Huckfeldt & Sprague (1987) "Networks in Context: The Social Flow
   of Political Information." American Political Science Review, 81(4), 1197-1216.

2. Personality alignment (15%): ideological and temperamental fit between voter
   and candidate, computed via Big Five Euclidean distance.
   Reference: Caprara et al. (2006) "Personality and Politics: Values,
   Traits, and Political Choice." Political Psychology, 27(1), 1-28.

3. Economic satisfaction (20%): voters penalise incumbents and reward challengers
   based on their own material well-being — the economic voting model.
   Reference: Lewis-Beck & Stegmaier (2000) "Economic Determinants of Electoral
   Outcomes." Annual Review of Political Science, 3, 183-219.

4. Reputation influence (25%): voters are affected by the direct experiences (image)
   and socially-transmitted opinions (reputation) they hold about the candidate.
   The combined score integrates first-hand observation with hearsay, making both
   propaganda and genuine track record politically consequential.
   Reference: Lodge, Steenbergen & Brau (1995) "The Responsive Voter: Campaign
   Information and the Dynamics of Candidate Evaluation." APSR, 89(2), 309-326.

5. Candidate charisma (15%): a baseline personal appeal factor independent of
   voter-specific considerations. Charisma's influence on electoral behavior is
   well-documented in political science (Weber 1922 for charismatic authority;
   Bass 1985 for transformational leadership). The specific weight in the vote
   score is a design parameter.

Manipulated elections add a +0.3 bonus to the ruling faction's candidate, modelling
the well-documented incumbency advantage under competitive authoritarianism.
Reference: Levitsky & Way (2010) "Competitive Authoritarianism." Cambridge
University Press.
"""
from __future__ import annotations

import math

from django.db.models import Q

from epocha.apps.agents.affinity import _personality_similarity
from epocha.apps.agents.models import Agent, Memory, Relationship
from epocha.apps.simulation.models import Simulation
from epocha.apps.world.government_types import GOVERNMENT_TYPES
from epocha.apps.world.models import Government

# Vote score component weights — must sum to 1.0.
# These are design parameters. The cited papers discuss the existence of each
# factor but do not provide relative weights. Lewis-Beck & Stegmaier (2000)
# suggest economic conditions are often the dominant predictor, potentially
# warranting higher economic weight in future empirical calibration.
_W_RELATIONSHIP: float = 0.25
_W_PERSONALITY: float = 0.15
_W_ECONOMIC: float = 0.20
_W_MEMORY: float = 0.25
_W_CHARISMA: float = 0.15

# Wealth normalisation ceiling: a voter with wealth >= 100 is fully satisfied.
# This maps to the simulation's internal wealth scale where Agent.wealth
# defaults to 50.0. Design parameter, not empirically derived.
_WEALTH_SATURATION: float = 100.0

# Score bonus applied to the ruling faction's candidate in a manipulated election.
# Derived from Levitsky & Way (2010): incumbents in competitive authoritarian regimes
# typically convert state resources into roughly 15-30% vote share advantage.
# We use 0.3 as a conservative upper bound within the [0, 1] scoring space.
_MANIPULATION_BONUS: float = 0.3

# Keywords used to classify the valence of a voter's memory about a candidate.
# Each match shifts the memory influence score by the keyword's weight.
# Classified as: positive (helpful acts) or negative (harmful acts).
_POSITIVE_KEYWORDS: frozenset[str] = frozenset({
    "helped", "reformed", "saved", "protected", "improved", "founded", "built", "united",
})
_NEGATIVE_KEYWORDS: frozenset[str] = frozenset({
    "betrayed", "stole", "corrupt", "attacked", "failed", "oppressed", "exploited", "destroyed",
})


def compute_vote_score(voter: Agent, candidate: Agent, tick: int) -> float:
    """Return a [0.0, 1.0] score representing how likely a voter is to vote for a candidate.

    The score is the weighted sum of five components:
      - relationship_sentiment (25%): normalised sentiment from any Relationship
        between voter and candidate, in either direction.
      - personality_alignment (15%): Big Five similarity between voter and candidate.
      - economic_satisfaction (20%): composite of voter mood and relative wealth.
      - reputation_factor (25%): combined image+reputation score the voter holds for the
        candidate, normalised from [-1, 1] to [0, 1]. Replaces the legacy keyword-based
        memory influence scan, which lacked causal grounding.
      - charisma_effect (15%): candidate's raw charisma attribute.

    Args:
        voter: The agent casting the vote.
        candidate: The agent being evaluated as a candidate.
        tick: Current simulation tick (unused here but accepted for API consistency
              with future memory recency filtering).

    Returns:
        Float in [0.0, 1.0].
    """
    relationship_sentiment = _relationship_sentiment_score(voter, candidate)
    personality_alignment = _personality_similarity(voter.personality, candidate.personality)
    economic_satisfaction = (voter.mood + min(voter.wealth / _WEALTH_SATURATION, 1.0)) / 2.0
    from epocha.apps.agents.reputation import get_combined_score
    reputation_raw = get_combined_score(voter, candidate)
    # Note: reputation normalization is also available via ReputationScore.get_combined_score_normalized().
    # This inline normalization is kept for backward compatibility but should migrate to the centralized method.
    reputation_factor = (reputation_raw + 1.0) / 2.0  # Normalize from [-1, 1] to [0, 1]
    charisma_effect = candidate.charisma

    score = (
        _W_RELATIONSHIP * relationship_sentiment
        + _W_PERSONALITY * personality_alignment
        + _W_ECONOMIC * economic_satisfaction
        + _W_MEMORY * reputation_factor
        + _W_CHARISMA * charisma_effect
    )
    return max(0.0, min(1.0, score))


def run_election(simulation: Simulation, tick: int) -> dict:
    """Run an election for the given simulation and update the government accordingly.

    Candidates are the leaders of all active groups in the simulation. All living
    agents without a leadership role act as voters and cast scored votes for every
    candidate. The candidate with the highest aggregate score wins.

    In government types with ``election_manipulated=True``, the current ruling
    faction's candidate receives a +0.3 score bonus before tallying, modelling
    resource advantages and state media bias.

    After the election:
      - ``government.head_of_state`` is set to the winning candidate.
      - ``government.ruling_faction`` is set to the winner's group.
      - ``government.last_election_tick`` is updated to ``tick``.
      - A public memory is written to every living agent announcing the result.

    Args:
        simulation: The simulation whose election to run.
        tick: The current simulation tick.

    Returns:
        A dict with keys ``winner`` (Agent), ``faction`` (Group), and
        ``tallies`` (dict mapping candidate pk to aggregate score).
    """
    government = Government.objects.select_related("ruling_faction").get(simulation=simulation)
    gov_config = GOVERNMENT_TYPES.get(government.government_type, {})
    is_manipulated = gov_config.get("election_manipulated", False)

    # Gather candidates: every group that has a designated leader.
    candidates: list[Agent] = list(
        Agent.objects.filter(
            simulation=simulation,
            is_alive=True,
            led_groups__simulation=simulation,
        ).select_related("group").distinct()
    )

    if not candidates:
        return {"winner": None, "faction": None, "tallies": {}}

    # Gather voters: all living agents in the simulation.
    # Evaluate to a list once so the queryset is not re-executed on len() below.
    voter_list = list(
        Agent.objects.filter(simulation=simulation, is_alive=True).select_related("group")
    )
    voter_count = len(voter_list)

    # Compute aggregate scores for each candidate.
    tallies: dict[int, float] = {candidate.pk: 0.0 for candidate in candidates}
    for voter in voter_list:
        for candidate in candidates:
            tallies[candidate.pk] += compute_vote_score(voter, candidate, tick)

    # Apply manipulation bonus to the ruling faction's candidate, if applicable.
    if is_manipulated and government.ruling_faction_id is not None:
        for candidate in candidates:
            if candidate.group_id == government.ruling_faction_id:
                tallies[candidate.pk] += _MANIPULATION_BONUS * voter_count

    # Determine the winner.
    winner = max(candidates, key=lambda c: tallies[c.pk])
    winning_faction = winner.group

    # Update government state.
    government.head_of_state = winner
    government.ruling_faction = winning_faction
    government.last_election_tick = tick
    government.save(update_fields=["head_of_state", "ruling_faction", "last_election_tick"])

    # Broadcast the election result as a public memory to all living agents.
    election_memory_content = (
        f"{winner.name} won the election and became head of state at tick {tick}."
    )
    all_agents = Agent.objects.filter(simulation=simulation, is_alive=True)
    Memory.objects.bulk_create([
        Memory(
            agent=agent,
            content=election_memory_content,
            emotional_weight=0.4,
            source_type=Memory.SourceType.PUBLIC,
            tick_created=tick,
        )
        for agent in all_agents
    ])

    return {
        "winner": winner,
        "faction": winning_faction,
        "tallies": tallies,
    }


def _relationship_sentiment_score(voter: Agent, candidate: Agent) -> float:
    """Return a [0.0, 1.0] normalised sentiment score from any relationship between voter and candidate.

    Checks both directions (voter -> candidate and candidate -> voter) so that
    unilateral relationships are captured. Normalises the raw sentiment from
    [-1.0, 1.0] to [0.0, 1.0] via (sentiment + 1) / 2.

    If multiple relationships exist (both directions recorded), uses the one
    with the highest absolute sentiment to capture the strongest signal.

    Returns 0.5 (neutral) when no relationship is found.

    Args:
        voter: The voting agent.
        candidate: The candidate agent.

    Returns:
        Float in [0.0, 1.0].
    """
    try:
        rel = Relationship.objects.get(
            Q(agent_from=voter, agent_to=candidate)
            | Q(agent_from=candidate, agent_to=voter)
        )
    except Relationship.DoesNotExist:
        return 0.5
    except Relationship.MultipleObjectsReturned:
        rel = (
            Relationship.objects.filter(
                Q(agent_from=voter, agent_to=candidate)
                | Q(agent_from=candidate, agent_to=voter)
            )
            .order_by("-strength")
            .first()
        )

    # Normalise [-1.0, 1.0] -> [0.0, 1.0].
    return (rel.sentiment + 1.0) / 2.0


# DEPRECATED: this function is not called. Vote scoring uses reputation.get_combined_score
# instead. Kept for reference; should be removed in a future cleanup.
def _memory_influence_score(voter: Agent, candidate: Agent) -> float:
    """Return a [0.0, 1.0] score from the voter's active memories about the candidate.

    DEPRECATED: this function is no longer called by compute_vote_score, which now uses
    the reputation-based score from get_combined_score instead. The function is retained
    for reference only and should be removed in a future cleanup pass.

    NOTE: the keyword set here (_POSITIVE_KEYWORDS, _NEGATIVE_KEYWORDS) differs from the
    keyword set in reputation.py:extract_action_sentiment. This function is deprecated and
    should be removed.

    Scans the voter's active memories for mentions of the candidate's name.
    For each matching memory:
      - Positive keyword matches increase the score.
      - Negative keyword matches decrease the score.
    Each keyword match is weighted by the memory's emotional_weight.

    The raw net score is mapped from [-total_weight, +total_weight] to [0.0, 1.0].
    If no memories mention the candidate, returns 0.5 (neutral baseline).

    Args:
        voter: The voting agent.
        candidate: The candidate agent.

    Returns:
        Float in [0.0, 1.0].
    """
    memories = Memory.objects.filter(
        agent=voter,
        is_active=True,
        content__icontains=candidate.name,
    )

    net_score = 0.0
    total_weight = 0.0

    for memory in memories:
        words = set(memory.content.lower().split())
        positive_hits = len(words & _POSITIVE_KEYWORDS)
        negative_hits = len(words & _NEGATIVE_KEYWORDS)
        net_valence = positive_hits - negative_hits
        if net_valence != 0:
            net_score += net_valence * memory.emotional_weight
            total_weight += memory.emotional_weight

    if total_weight == 0.0:
        return 0.5

    # Normalise: net_score / total_weight is in range [-max_keywords, +max_keywords].
    # We use tanh to squash this into (-1, 1) then map to (0, 1).
    normalised = math.tanh(net_score / total_weight)
    return (normalised + 1.0) / 2.0

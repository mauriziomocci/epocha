"""Faction dynamics engine -- cohesion, leadership, formation, schism.

Runs every N ticks (configurable via EPOCHA_FACTION_DYNAMICS_INTERVAL) after
information flow. Manages the full lifecycle of agent groups: updates cohesion
based on member interactions, verifies leadership legitimacy, detects potential
new factions, and handles dissolution and schism.

Faction dynamics operate on a slower timescale than individual decisions because
political change emerges from accumulated interactions, not single events.

Scientific basis:
  - Leadership emergence: the trait-based scoring approach is grounded in Judge,
    Bono, Ilies, and Gerhardt (2002), "Personality and leadership: A
    qualitative and quantitative review", Journal of Applied Psychology
    87(4):765-780, DOI 10.1037/0021-9010.87.4.765, which provides meta-analytic
    effect sizes for the Big Five trait-leadership relationship: Extraversion is
    the strongest correlate of leadership emergence (rho ~ 0.31),
    Conscientiousness (~ 0.28), Openness (~ 0.24), Neuroticism (~ -0.24).
    Stogdill (1948), "Personal factors associated with leadership: A survey of
    the literature", Journal of Psychology 25(1):35-71,
    DOI 10.1080/00223980.1948.9917362, supports the broader principle that
    personal traits correlate with leadership emergence but does NOT propose a
    weighted-sum formula. Charisma is a Weberian sociological concept
    (Weber 1922) rather than a Stogdill trait correlate; its modern
    operationalization draws on Antonakis, Bastardoz, Jacquart, and Shamir
    (2016), "Charisma: An ill-defined and ill-measured gift", Annual Review of
    Organizational Psychology and Organizational Behavior 3:293-319,
    DOI 10.1146/annurev-orgpsych-041015-062305. The specific weights in
    compute_leadership_score (0.30/0.20/0.15/0.20/0.15) are tunable design
    parameters consistent with the direction of Judge 2002 effect sizes but not
    derived from them; see Known Limitations (a).
  - Group cohesion: Festinger et al. (1950), "Social Pressures in Informal
    Groups." Cohesion is maintained through cooperative interaction and
    undermined by internal conflict.
  - Group cohesion size penalty: coordination cost above a small-group
    threshold is a generic principle in organizational psychology (see
    Hackman 2002, "Leading Teams: Setting the Stage for Great Performances",
    Harvard Business School Press, ISBN 978-1-57851-333-1, for the argument
    that teams of 4-6 are typically the upper bound for fully-cohesive
    collaborative units before coordination overhead dominates). The specific
    threshold value of 5 in update_group_cohesion is a tunable design
    parameter; NOT derived from Dunbar 1992 (Dunbar's number is approximately
    150 and addresses the cognitive limit on stable social relationships) nor
    from the nested-group hierarchy of Zhou, Sornette, Hill, and Dunbar (2005),
    "Discrete hierarchical organization of social group sizes", Proc R Soc B
    272(1561):439-444, DOI 10.1098/rspb.2004.2970, in which the "5" is the
    innermost intimate-clique stratum (closest emotional ties) rather than a
    coordination cost boundary. See Known Limitations (b).
  - Faction dissolution: Olson (1965), "The Logic of Collective Action."
    Below a critical collective-action threshold, groups disintegrate.

Known Limitations:
  (a) Leadership weights (0.30/0.20/0.15/0.20/0.15) in compute_leadership_score
      are tunable design parameters consistent with Judge 2002 effect-size
      direction, not derived from them. See compute_leadership_score docstring.
  (b) Size-penalty threshold of 5 in update_group_cohesion is a tunable design
      parameter; NOT derived from Dunbar 1992 (Dunbar's number is approximately
      150; the 5 in Zhou et al. 2005 is the intimate-clique stratum, NOT a
      coordination cost boundary). See update_group_cohesion docstring.
  (c) Cohesion delta coefficients (0.10 cooperation, 0.15 conflict, 0.02 size
      penalty, 0.05 leader effectiveness) are tunable design parameters;
      Baumeister 2001 grounds the qualitative DIRECTION of the
      conflict-over-cooperation asymmetry (negativity bias), NOT the specific
      1.5:1 ratio.
  (d) Multiple greedy seed-first iterations in this module (schism detection
      in _check_schism, the ally-grouping inner loop within it, and cluster
      detection in _detect_and_propose_factions) seed the candidate splinter /
      cluster from the first agent in the queryset, making the result
      order-dependent.
      Overlapping potential schisms/clusters may exist; which one is detected
      depends on iteration order. A robust resolution would use graph-based
      connected-components or hierarchical clustering on the sentiment matrix --
      bound to a future "robust faction clustering" work item.
  (e) Several scalar calibration parameters in this module are tunable design
      choices, not empirically derived: the no-relationship sentiment fallback
      (0.3 normalized = raw -0.4) in compute_leadership_score and
      compute_legitimacy; the symmetric schism/ally sentiment thresholds
      (+/-0.2); the splinter-vs-new-faction seed cohesion differential
      (0.5 vs 0.6); the dissolution / legitimacy / affinity settings defaults
      (0.2 / 0.3 / 0.5); and the Memory.emotional_weight grading (0.2 minor,
      0.3 moderate, 0.4 significant) applied to faction-event memories. All are
      part of the simulation's calibration budget tied to tick frequency and the
      desired group-formation timescale.
  (f) Deferred behavioral hardening (tracked for a future "factions Round 3
      hardening" work item, out of scope for this doc-only audit re-pass):
      member-sampling bias from default primary-key ordering in
      _check_join_existing_groups; missing @transaction.atomic around the
      multi-row writes in _check_schism and _create_faction; inconsistent agent
      migration discipline (.update(group=None) does not fire signals while
      per-agent .save() does); and N+1 query patterns in the
      _check_join_existing_groups affinity loop and in compute_legitimacy.
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
# Source: Axelrod (1984), "The Evolution of Cooperation" — cooperation
# reinforces group bonds through iterated positive exchange.
_COOPERATIVE_ACTIONS: frozenset[str] = frozenset({"help", "socialize"})

# Actions considered conflictual (decrease cohesion).
# Cohesion delta coefficients in update_group_cohesion (0.10 cooperation,
# 0.15 conflict, 0.02 size penalty, 0.05 leader effectiveness) are tunable
# design parameters. Baumeister, Bratslavski, Finkenauer, and Vohs (2001),
# "Bad is stronger than good", Review of General Psychology 5(4):323-370,
# DOI 10.1037/1089-2680.5.4.323, grounds the qualitative DIRECTION of the
# conflict-over-cooperation asymmetry (negative events have stronger
# psychological impact than positive events of equivalent magnitude). The
# specific 1.5:1 ratio between conflict and cooperation magnitudes, and the
# absolute values of all four coefficients, are NOT derived from Baumeister
# 2001 or any specific empirical fit; they are part of the simulation's
# calibration budget tied to tick frequency and the desired group-formation
# timescale. See module Known Limitations (c).
_CONFLICT_ACTIONS: frozenset[str] = frozenset({"argue", "betray"})

# Sentiment thresholds for schism / alliance detection. Both magnitudes are
# tunable design parameters; the symmetric +/-0.2 value is a calibration choice,
# not empirically derived. A negative outward sentiment below -0.2 is treated as
# genuine hostility (not mere indifference) and triggers schism; a mutual
# sentiment above +0.2 qualifies two agents as allies. See module Known
# Limitations (e).
_SCHISM_OUTWARD_SENTIMENT_THRESHOLD: float = -0.2
_ALLY_SENTIMENT_THRESHOLD: float = 0.2


def process_faction_dynamics(simulation, tick: int) -> None:
    """Main entry point for faction dynamics. Runs every N ticks.

    Orchestrates the full dynamics pipeline in order:
      1. Cohesion update for each active group
      2. Leadership legitimacy check
      3. Dissolution check
      4. Schism check
      5. Cluster detection for potential new factions
      6. Join suggestions for ungrouped agents
      7. Processing of formation decisions from agents

    Args:
        simulation: The Simulation instance.
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

    Formula (weights sum to 1.0):
        score = charisma * 0.30
              + intelligence * 0.20
              + wealth_rank * 0.15
              + internal_sentiment * 0.20
              + seniority * 0.15

    Components:
      - charisma: intrinsic social magnetism (trait value directly)
      - intelligence: strategic competence
      - wealth_rank: relative economic standing within group [0.0, 1.0]
      - internal_sentiment: average normalized sentiment of relationships with
        other members, where [-1, 1] is mapped to [0, 1]
      - seniority: (tick - join_tick) / group_age, capped at 1.0

    Leadership emergence score. The trait-based scoring approach is grounded in
    Judge et al. (2002) meta-analytic effect sizes for the Big Five
    trait-leadership relationship (see module docstring "Scientific basis").
    The five-component weighted formula (charisma 0.30, intelligence 0.20,
    wealth_rank 0.15, internal_sentiment 0.20, seniority 0.15) is consistent
    with the DIRECTION of those effect sizes (Extraversion strongest, then
    Conscientiousness, Openness, inverse Neuroticism) but the specific weights
    are tunable design parameters, not derived from the meta-analytic
    correlations. Stogdill (1948) is the original survey establishing the
    trait-correlate principle but did NOT propose a weighted-sum formula;
    charisma in particular is a Weberian concept (Weber 1922), not a Stogdill
    trait. See module Known Limitations (a).

    Args:
        agent: The agent to score.
        group: The group context.
        tick: Current tick.

    Returns:
        Leadership score in [0.0, 1.0].
    """
    members = list(Agent.objects.filter(group=group, is_alive=True))
    if not members:
        return 0.0

    # Wealth rank within group: 0.0 = poorest, 1.0 = wealthiest.
    sorted_by_wealth = sorted(members, key=lambda a: a.wealth)
    try:
        rank_index = sorted_by_wealth.index(agent)
    except ValueError:
        rank_index = 0
    wealth_rank = rank_index / max(len(members) - 1, 1)

    # Internal sentiment: average sentiment of relationships with other members,
    # normalized from [-1, 1] to [0, 1].
    other_member_ids = [m.id for m in members if m.id != agent.id]
    relationships = Relationship.objects.filter(
        Q(agent_from=agent, agent_to_id__in=other_member_ids)
        | Q(agent_to=agent, agent_from_id__in=other_member_ids)
    )
    if relationships.exists():
        total_sentiment = sum(r.sentiment for r in relationships)
        raw_sentiment = total_sentiment / relationships.count()
        internal_sentiment = (raw_sentiment + 1.0) / 2.0
    else:
        # No established relationships: default to a below-neutral internal
        # sentiment (0.3 normalized = raw sentiment -0.4). Conservative tunable
        # design parameter: an agent with no in-group ties is not presumed
        # well-integrated. See module Known Limitations (e).
        internal_sentiment = 0.3

    # Seniority: fraction of group lifetime the agent has been present.
    group_age = max(tick - group.formed_at_tick, 1)
    join_memory = (
        Memory.objects.filter(
            agent=agent,
            is_active=True,
            content__contains=group.name,
        )
        .order_by("tick_created")
        .first()
    )
    join_tick = join_memory.tick_created if join_memory else tick
    seniority = min((tick - join_tick) / group_age, 1.0)

    score = (
        agent.charisma * 0.30
        + agent.intelligence * 0.20
        + wealth_rank * 0.15
        + internal_sentiment * 0.20
        + seniority * 0.15
    )
    return max(0.0, min(1.0, score))


def compute_legitimacy(leader: Agent, group: Group, tick: int) -> float:
    """Compute the legitimacy of a leader within their group.

    Formula:
        legitimacy = group_cohesion * 0.40
                   + leader_sentiment * 0.40
                   + score_rank * 0.20

    Components:
      - group_cohesion: overall group health (from Group.cohesion)
      - leader_sentiment: normalized average sentiment toward the leader
        from other members
      - score_rank: 1.0 if leader has highest leadership_score, 0.0 if
        last; linear interpolation between

    A legitimacy below EPOCHA_FACTION_LEGITIMACY_THRESHOLD (default 0.3)
    triggers leadership replacement.

    Args:
        leader: The current group leader.
        group: The group instance.
        tick: Current tick.

    Returns:
        Legitimacy score in [0.0, 1.0].
    """
    members = list(Agent.objects.filter(group=group, is_alive=True))
    if len(members) <= 1:
        # Solo or empty group: leader is trivially legitimate.
        return 1.0

    # Leader's average sentiment from/to other members.
    other_ids = [m.id for m in members if m.id != leader.id]
    relationships = Relationship.objects.filter(
        Q(agent_from=leader, agent_to_id__in=other_ids)
        | Q(agent_to=leader, agent_from_id__in=other_ids)
    )
    if relationships.exists():
        raw = sum(r.sentiment for r in relationships) / relationships.count()
        leader_sentiment = (raw + 1.0) / 2.0
    else:
        # No established relationships: below-neutral fallback (0.3 normalized =
        # raw sentiment -0.4), same tunable convention as compute_leadership_score.
        # See module Known Limitations (e).
        leader_sentiment = 0.3

    # Score rank: how the leader compares to all members.
    scores = [(m, compute_leadership_score(m, group, tick)) for m in members]
    scores.sort(key=lambda x: x[1], reverse=True)
    leader_rank = next(
        (i for i, (m, _) in enumerate(scores) if m.id == leader.id),
        len(scores) - 1,
    )
    score_rank = 1.0 - leader_rank / max(len(members) - 1, 1)

    legitimacy = group.cohesion * 0.40 + leader_sentiment * 0.40 + score_rank * 0.20
    return max(0.0, min(1.0, legitimacy))


def update_group_cohesion(group: Group, simulation, tick: int) -> None:
    """Update a group's cohesion based on member interactions in the last interval.

    Reads DecisionLog entries for group members, counts cooperative (help,
    socialize) and conflictual (argue, betray) actions between members, then
    applies:

        delta = cooperation_ratio * 0.10
              - conflict_ratio * 0.15
              - size_penalty * 0.02
              + leader_effectiveness * 0.05

    where:
      - size_penalty = max(0, member_count - 5): coordination cost above a
        small-group threshold. The threshold value 5 is a tunable design parameter
        consistent with Hackman 2002 "Leading Teams" (teams of 4-6 as the upper
        bound for fully-cohesive collaborative units before coordination overhead
        dominates) but NOT derived from Dunbar 1992 (cognitive limit on stable
        social relationships is approximately 150) nor from the Zhou et al. 2005
        nested-hierarchy "5" stratum (intimate cliques, not coordination cost).
        See module Known Limitations (b).
      - leader_effectiveness = legitimacy - 0.5: positive if leader is well-liked.

    The asymmetry (conflict has 1.5x the effect of cooperation) is consistent
    with the qualitative DIRECTION documented by Baumeister et al. (2001),
    "Bad is stronger than good", which shows that negative events have stronger
    psychological impact than positive events of equivalent magnitude. The
    specific 1.5:1 ratio and the absolute coefficient values
    (0.10, 0.15, 0.02, 0.05) are tunable design parameters per the simulation's
    calibration budget, NOT derived from Baumeister or any specific empirical
    fit. See module Known Limitations (c).

    Args:
        group: The group to update.
        simulation: The Simulation instance.
        tick: Current tick.
    """
    interval = getattr(settings, "EPOCHA_FACTION_DYNAMICS_INTERVAL", 5)
    members = list(Agent.objects.filter(group=group, is_alive=True))
    if len(members) < 2:
        return

    member_ids = [m.id for m in members]
    member_names = {m.id: m.name for m in members}

    recent_decisions = DecisionLog.objects.filter(
        simulation=simulation,
        agent_id__in=member_ids,
        tick__gt=max(0, tick - interval),
        tick__lte=tick,
    )

    cooperation_count = 0
    conflict_count = 0
    total_count = 0

    for decision in recent_decisions:
        try:
            data = json.loads(decision.output_decision)
        except (json.JSONDecodeError, TypeError):
            continue
        action = data.get("action", "")
        target = data.get("target", "")
        # Check if target matches any group member's name (case-insensitive).
        target_is_member = target and any(
            target.lower() in name.lower() for name in member_names.values()
        )
        if not target_is_member:
            continue
        total_count += 1
        if action in _COOPERATIVE_ACTIONS:
            cooperation_count += 1
        elif action in _CONFLICT_ACTIONS:
            conflict_count += 1

    # Avoid division by zero: if no inter-member decisions, ratios are 0.
    effective_total = max(total_count, 1)
    cooperation_ratio = cooperation_count / effective_total
    conflict_ratio = conflict_count / effective_total

    # Size penalty: each member above 5 adds coordination friction.
    size_penalty = max(0, len(members) - 5)

    # Leader effectiveness: positive contribution if legitimacy > 0.5.
    leader = group.leader
    if leader and leader.is_alive and leader.group_id == group.id:
        legitimacy = compute_legitimacy(leader, group, tick)
        leader_effectiveness = legitimacy - 0.5
    else:
        leader_effectiveness = -0.1  # Leaderless groups destabilize.

    delta = (
        cooperation_ratio * 0.10
        - conflict_ratio * 0.15
        - size_penalty * 0.02
        + leader_effectiveness * 0.05
    )
    group.cohesion = max(0.0, min(1.0, group.cohesion + delta))
    group.save(update_fields=["cohesion"])


def update_group_leadership(group: Group, tick: int) -> None:
    """Verify leader legitimacy and replace if below threshold.

    If the current leader is missing, dead, or has left the group, elects a
    new one immediately. Otherwise computes legitimacy and replaces the leader
    if below EPOCHA_FACTION_LEGITIMACY_THRESHOLD.

    A leadership transition incurs a -0.05 cohesion penalty (power struggle
    cost) and creates memories for all members.

    Args:
        group: The group to check.
        tick: Current tick.
    """
    # Default 0.3 is a tunable design parameter (calibration budget), not
    # empirically derived. See module Known Limitations (e).
    threshold = getattr(settings, "EPOCHA_FACTION_LEGITIMACY_THRESHOLD", 0.3)
    leader = group.leader

    if not leader or not leader.is_alive or leader.group_id != group.id:
        _elect_new_leader(group, tick)
        return

    legitimacy = compute_legitimacy(leader, group, tick)
    if legitimacy < threshold:
        old_leader = leader
        # Elect excluding the failed leader: a leader who lost legitimacy
        # cannot immediately win re-election. This prevents the charisma/
        # intelligence components of leadership_score from overriding the
        # social rejection that triggered the election.
        _elect_new_leader(group, tick, exclude=old_leader)
        group.refresh_from_db()
        if group.leader_id != old_leader.id:
            # Leadership transition penalty.
            group.cohesion = max(0.0, group.cohesion - 0.05)
            group.save(update_fields=["cohesion"])
            members = Agent.objects.filter(group=group, is_alive=True)
            new_leader_name = group.leader.name if group.leader else "unknown"
            for member in members:
                Memory.objects.create(
                    agent=member,
                    content=(
                        f"{old_leader.name} was replaced by {new_leader_name}"
                        f" as leader of {group.name}."
                    ),
                    emotional_weight=0.4,
                    source_type=Memory.SourceType.DIRECT,
                    tick_created=tick,
                )


def _elect_new_leader(group: Group, tick: int, exclude: Agent | None = None) -> None:
    """Set the member with the highest leadership score as group leader.

    Skips the election if there are no eligible members.

    Args:
        group: The group to update.
        tick: Current tick (passed to compute_leadership_score).
        exclude: Optional agent to exclude from candidacy. Used when a leader
            has lost legitimacy — they cannot immediately win re-election,
            preventing charisma/intelligence from overriding social rejection.
    """
    members = list(Agent.objects.filter(group=group, is_alive=True))
    if exclude is not None:
        members = [m for m in members if m.id != exclude.id]
    if not members:
        return
    scores = [(m, compute_leadership_score(m, group, tick)) for m in members]
    scores.sort(key=lambda x: x[1], reverse=True)
    group.leader = scores[0][0]
    group.save(update_fields=["leader"])


def _check_dissolution(group: Group, tick: int) -> None:
    """Dissolve the group if cohesion falls below the dissolution threshold.

    All members are ungrouped and each receives a memory of the dissolution.
    The group record is left in the database for historical reference but no
    longer has active members.

    Args:
        group: The group to check.
        tick: Current tick.
    """
    # Default 0.2 is a tunable design parameter (calibration budget), not
    # empirically derived. See module Known Limitations (e).
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
            source_type=Memory.SourceType.DIRECT,
            tick_created=tick,
        )
    logger.info(
        "Group '%s' dissolved at tick %d (cohesion=%.2f)",
        group.name, tick, group.cohesion,
    )


def _check_schism(group: Group, simulation, tick: int) -> None:
    """Check for internal fractures that could split the group.

    A schism occurs when a subcluster of MIN_MEMBERS or more members has:
      - positive average internal sentiment (> ALLY_SENTIMENT_THRESHOLD) among
        themselves
      - negative average sentiment (< SCHISM_OUTWARD_SENTIMENT_THRESHOLD)
        toward the rest of the group

    The group must have at least 2 * MIN_MEMBERS to be splittable.

    The splinter faction name and objective are generated via LLM with a
    deterministic fallback.

    Args:
        group: The group to check.
        simulation: The Simulation instance.
        tick: Current tick.
    """
    min_members = getattr(settings, "EPOCHA_FACTION_MIN_MEMBERS", 3)
    members = list(Agent.objects.filter(group=group, is_alive=True))
    if len(members) < min_members * 2:
        return

    member_ids = {m.id for m in members}
    relationships = Relationship.objects.filter(
        agent_from_id__in=member_ids,
        agent_to_id__in=member_ids,
    )
    sentiment_map: dict[tuple[int, int], float] = {}
    for rel in relationships:
        sentiment_map[(rel.agent_from_id, rel.agent_to_id)] = rel.sentiment

    def _get_sentiment(a_id: int, b_id: int) -> float:
        return sentiment_map.get((a_id, b_id), sentiment_map.get((b_id, a_id), 0.0))

    # Schism detection seeds from the first agent in the queryset
    # (order-dependent). See module docstring "Known Limitations" (d).
    for seed in members:
        allies = [seed]
        for other in members:
            if other.id == seed.id:
                continue
            if _get_sentiment(seed.id, other.id) > _ALLY_SENTIMENT_THRESHOLD:
                allies.append(other)

        if len(allies) < min_members:
            continue

        non_allies = [m for m in members if m.id not in {a.id for a in allies}]
        if not non_allies:
            continue

        outward_sentiments = [
            _get_sentiment(ally.id, non_ally.id)
            for ally in allies
            for non_ally in non_allies
        ]
        if not outward_sentiments:
            continue

        avg_outward = sum(outward_sentiments) / len(outward_sentiments)
        if avg_outward >= _SCHISM_OUTWARD_SENTIMENT_THRESHOLD:
            continue

        # Schism condition met: create a splinter group.
        name, objective = _generate_faction_identity(
            founders=allies,
            context=f"splitting from {group.name}",
            fallback_name=f"{group.name} - Dissidents",
            fallback_objective="Chart our own course",
        )

        splinter = Group.objects.create(
            simulation=simulation,
            name=name,
            objective=objective,
            # Splinter seed cohesion 0.5: a breakaway group starts less cohesive
            # than a freshly self-organized faction (0.6 in _create_faction)
            # because it carries unresolved conflict from the parent. The 0.1
            # differential is a tunable design parameter. See Known Limitations (e).
            cohesion=0.5,
            formed_at_tick=tick,
            parent_group=group,
        )

        for ally in allies:
            ally.group = splinter
            ally.save(update_fields=["group"])
            Memory.objects.create(
                agent=ally,
                content=f"I left {group.name} and joined {name}.",
                emotional_weight=0.4,
                source_type=Memory.SourceType.DIRECT,
                tick_created=tick,
            )

        splinter_scores = [(a, compute_leadership_score(a, splinter, tick)) for a in allies]
        splinter_scores.sort(key=lambda x: x[1], reverse=True)
        splinter.leader = splinter_scores[0][0]
        splinter.save(update_fields=["leader"])

        group.cohesion = max(0.0, group.cohesion - 0.1)
        group.save(update_fields=["cohesion"])

        ally_ids = {a.id for a in allies}
        for member in members:
            if member.id not in ally_ids:
                Memory.objects.create(
                    agent=member,
                    content=f"{name} has split from {group.name}.",
                    emotional_weight=0.3,
                    source_type=Memory.SourceType.DIRECT,
                    tick_created=tick,
                )

        logger.info(
            "Schism in '%s': '%s' formed with %d members at tick %d",
            group.name, name, len(allies), tick,
        )
        return  # Only one schism per tick per group.


def _detect_and_propose_factions(simulation, tick: int) -> None:
    """Identify potential faction clusters among ungrouped agents.

    For each cluster of MIN_MEMBERS or more ungrouped agents where ALL pairwise
    affinities are above EPOCHA_FACTION_AFFINITY_THRESHOLD, creates a memory
    for each cluster member noting the shared opportunity. The memory acts as
    a signal to the decision pipeline: agents who see it can decide to
    form_group.

    Cluster formation uses a clique-style algorithm (all pairs must exceed the
    threshold), capped at MAX_INITIAL_MEMBERS to keep factions manageable.

    Args:
        simulation: The Simulation instance.
        tick: Current tick.
    """
    # Default 0.5 is a tunable design parameter (calibration budget), not
    # empirically derived. See module Known Limitations (e).
    threshold = getattr(settings, "EPOCHA_FACTION_AFFINITY_THRESHOLD", 0.5)
    min_members = getattr(settings, "EPOCHA_FACTION_MIN_MEMBERS", 3)
    max_members = getattr(settings, "EPOCHA_FACTION_MAX_INITIAL_MEMBERS", 8)

    ungrouped = list(
        Agent.objects.filter(simulation=simulation, is_alive=True, group=None).order_by("name")
    )
    if len(ungrouped) < min_members:
        return

    clusters: list[list[Agent]] = []
    visited: set[int] = set()

    # Cluster detection seeds from the first agent in the queryset
    # (order-dependent), same limitation as _check_schism. See module
    # docstring "Known Limitations" (d).
    for i, agent_a in enumerate(ungrouped):
        if agent_a.id in visited:
            continue
        cluster: list[Agent] = [agent_a]
        for agent_b in ungrouped[i + 1:]:
            if agent_b.id in visited:
                continue
            if len(cluster) >= max_members:
                break
            # Require affinity above threshold with every current cluster member.
            affinities = [compute_affinity(agent_b, c, tick) for c in cluster]
            if all(a >= threshold for a in affinities):
                cluster.append(agent_b)

        if len(cluster) >= min_members:
            for agent in cluster:
                visited.add(agent.id)
                other_names = ", ".join(a.name for a in cluster if a.id != agent.id)
                already_proposed = Memory.objects.filter(
                    agent=agent,
                    content__contains="share common ground",
                    tick_created__gte=max(0, tick - 5),
                ).exists()
                if not already_proposed:
                    Memory.objects.create(
                        agent=agent,
                        content=(
                            f"I share common ground with {other_names}. "
                            "We face similar circumstances and could organize together."
                        ),
                        emotional_weight=0.2,
                        source_type=Memory.SourceType.DIRECT,
                        tick_created=tick,
                    )
            clusters.append(cluster)

    if clusters:
        logger.info(
            "Detected %d potential faction cluster(s) at tick %d",
            len(clusters), tick,
        )


def _check_join_existing_groups(simulation, tick: int) -> None:
    """Suggest existing groups to ungrouped agents with high affinity.

    For each ungrouped agent, checks all active groups. If the agent's average
    affinity with the first 5 group members is above threshold AND the agent
    has at least one positive relationship with a member, creates a memory
    suggestion. Only one suggestion per agent per 5-tick window.

    Args:
        simulation: The Simulation instance.
        tick: Current tick.
    """
    threshold = getattr(settings, "EPOCHA_FACTION_AFFINITY_THRESHOLD", 0.5)
    ungrouped = list(Agent.objects.filter(simulation=simulation, is_alive=True, group=None))
    groups = list(Group.objects.filter(simulation=simulation, cohesion__gt=0.0))

    for agent in ungrouped:
        for group in groups:
            # Sample up to 5 members for affinity estimation to avoid N+1 cost.
            members = list(Agent.objects.filter(group=group, is_alive=True)[:5])
            if not members:
                continue
            avg_affinity = sum(compute_affinity(agent, m, tick) for m in members) / len(members)
            has_positive_rel = Relationship.objects.filter(
                Q(agent_from=agent, agent_to__in=members, sentiment__gt=0)
                | Q(agent_to=agent, agent_from__in=members, sentiment__gt=0)
            ).exists()
            if avg_affinity >= threshold and has_positive_rel:
                already_suggested = Memory.objects.filter(
                    agent=agent,
                    content__contains=group.name,
                    tick_created__gte=max(0, tick - 5),
                ).exists()
                if not already_suggested:
                    Memory.objects.create(
                        agent=agent,
                        content=(
                            f"The {group.name} shares my values. "
                            f"{members[0].name} is a member. I could join them."
                        ),
                        emotional_weight=0.2,
                        source_type=Memory.SourceType.DIRECT,
                        tick_created=tick,
                    )
                break  # Only one join suggestion per agent per cycle.


def _process_formation_decisions(simulation, tick: int) -> None:
    """Process form_group and join_group decisions from the recent DecisionLog.

    Reads DecisionLog entries from the last EPOCHA_FACTION_DYNAMICS_INTERVAL
    ticks. Agents with "form_group" action who share a proposal memory are
    clustered and a faction is created if the cluster reaches MIN_MEMBERS.
    Agents with "join_group" action targeting an existing group name are
    added to that group.

    Args:
        simulation: The Simulation instance.
        tick: Current tick.
    """
    interval = getattr(settings, "EPOCHA_FACTION_DYNAMICS_INTERVAL", 5)
    min_members = getattr(settings, "EPOCHA_FACTION_MIN_MEMBERS", 3)

    recent_decisions = DecisionLog.objects.filter(
        simulation=simulation,
        tick__gt=max(0, tick - interval),
        tick__lte=tick,
    ).select_related("agent")

    formers: list[Agent] = []
    joiners: dict[str, list[Agent]] = {}

    for decision in recent_decisions:
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

    # Process join requests for existing groups.
    for group_name, agents in joiners.items():
        group = Group.objects.filter(simulation=simulation, name__icontains=group_name).first()
        if not group or group.cohesion <= 0.0:
            continue
        for agent in agents:
            agent.group = group
            agent.save(update_fields=["group"])
            Memory.objects.create(
                agent=agent,
                content=f"I joined {group.name}.",
                emotional_weight=0.3,
                source_type=Memory.SourceType.DIRECT,
                tick_created=tick,
            )
            group.cohesion = max(0.0, group.cohesion - 0.02)
            group.save(update_fields=["cohesion"])

    # Process new group formation: cluster formers by shared proposal memory.
    if len(formers) < min_members:
        return

    used: set[int] = set()
    for i, agent_a in enumerate(formers):
        if agent_a.id in used:
            continue
        cluster: list[Agent] = [agent_a]
        proposal = Memory.objects.filter(
            agent=agent_a,
            content__contains="share common ground",
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
    """Create a new faction from a list of founding agents.

    Generates a name and objective via LLM (with deterministic fallback),
    assigns the agent with the highest leadership score as leader, moves all
    founders into the group, and broadcasts a public memory to all agents.

    Args:
        simulation: The Simulation instance.
        founders: List of agents who are founding the faction.
        tick: Current tick.
    """
    roles = {a.role for a in founders if a.role}
    classes = {a.social_class for a in founders}
    founder_desc = ", ".join(f"{a.name} ({a.role})" for a in founders)
    fallback_name = f"The {next(iter(roles), 'Citizens').title()} Alliance"

    name, objective = _generate_faction_identity(
        founders=founders,
        context=f"organized together: {founder_desc}",
        fallback_name=fallback_name,
        fallback_objective="Pursue shared interests",
    )

    group = Group.objects.create(
        simulation=simulation,
        name=name,
        objective=objective,
        # New-faction seed cohesion 0.6: self-organized factions start more
        # cohesive than schism splinters (0.5). Tunable design parameter.
        # See Known Limitations (e).
        cohesion=0.6,
        formed_at_tick=tick,
    )

    scores = [(a, compute_leadership_score(a, group, tick)) for a in founders]
    scores.sort(key=lambda x: x[1], reverse=True)
    group.leader = scores[0][0]
    group.save(update_fields=["leader"])

    other_names_map = {
        a.id: ", ".join(f.name for f in founders if f.id != a.id)
        for a in founders
    }
    for agent in founders:
        agent.group = group
        agent.save(update_fields=["group"])
        Memory.objects.create(
            agent=agent,
            content=f"I helped found {name} with {other_names_map[agent.id]}.",
            emotional_weight=0.3,
            source_type=Memory.SourceType.DIRECT,
            tick_created=tick,
        )

    # Public announcement to all living non-members.
    outsiders = Agent.objects.filter(simulation=simulation, is_alive=True).exclude(group=group)
    public_memories = [
        Memory(
            agent=outsider,
            content=f"{name} has been formed by {founder_desc}, pursuing: {objective}.",
            emotional_weight=0.2,
            source_type=Memory.SourceType.PUBLIC,
            reliability=1.0,
            tick_created=tick,
        )
        for outsider in outsiders
    ]
    Memory.objects.bulk_create(public_memories)

    logger.info("Faction '%s' created at tick %d with %d founders", name, tick, len(founders))


def _generate_faction_identity(
    founders: list[Agent],
    context: str,
    fallback_name: str,
    fallback_objective: str,
) -> tuple[str, str]:
    """Generate a faction name and objective via LLM with deterministic fallback.

    Makes a single LLM call requesting JSON with "name" and "objective" keys.
    If the call fails for any reason (API error, malformed JSON, missing keys),
    the fallback values are returned without propagating the exception, so
    faction creation is never blocked by LLM unavailability.

    Args:
        founders: List of founding agents (for context).
        context: Short string describing the formation context for the prompt.
        fallback_name: Name to use if LLM call fails.
        fallback_objective: Objective to use if LLM call fails.

    Returns:
        Tuple of (name, objective).
    """
    # Lazy imports: kept function-scoped to avoid circular imports at module
    # load time. Moved outside the try so ImportError surfaces instead of being
    # silently swallowed by the broad except below.
    from epocha.apps.llm_adapter.client import get_llm_client
    from epocha.common.utils import clean_llm_json

    classes = {a.social_class for a in founders}
    roles = {a.role for a in founders if a.role}
    founder_desc = ", ".join(f"{a.name} ({a.role})" for a in founders)

    client = get_llm_client()
    prompt = (
        f"A group of people have {context}. "
        f"Members: {founder_desc}. "
        f"Social classes: {', '.join(classes)}. "
        f"Occupations: {', '.join(roles) if roles else 'various'}. "
        "Generate a faction name and one-sentence objective. "
        'Respond ONLY with JSON: {"name": "...", "objective": "..."}'
    )
    try:
        raw = client.complete(
            prompt=prompt,
            system_prompt="You name factions. Respond only with JSON.",
            max_tokens=80,
        )
        data = json.loads(clean_llm_json(raw))
        name = data.get("name") or fallback_name
        objective = data.get("objective") or fallback_objective
        return name, objective
    # Broad catch is deliberate: get_llm_client().complete() re-raises raw,
    # un-normalized provider/network exceptions (openai.* errors are not
    # wrapped in LLMError), and faction creation must never be blocked by LLM
    # unavailability (see docstring). Narrowing would require provider-level
    # exception normalization, deferred to a future hardening work item.
    except Exception as exc:
        logger.warning(
            "Failed to generate faction identity via LLM, using fallback '%s': %s",
            fallback_name,
            exc,
        )
        return fallback_name, fallback_objective

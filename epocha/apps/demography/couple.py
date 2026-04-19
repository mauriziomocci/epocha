"""Couple formation infrastructure for demography: Gale-Shapley stable
matching, homogamy scoring (Kalmijn 1998), and runtime pair_bond /
separate intent handling with canonical ordering enforcement.

Sources:
- Gale, D. & Shapley, L.S. (1962). College admissions and the stability
  of marriage. American Mathematical Monthly 69(1), 9-15.
- Kalmijn, M. (1998). Intermarriage and homogamy. Annual Review of
  Sociology 24, 395-421.
- Goode, W.J. (1963). World Revolution and Family Patterns (arranged
  marriage patterns).
"""
from __future__ import annotations

from typing import Iterable

from django.db.models import Q


def _ordered_pair(agent_a, agent_b) -> tuple:
    """Return (lower_id_agent, higher_id_agent) for Couple canonical ordering.

    The Couple model enforces agent_a.id < agent_b.id via CheckConstraint.
    Every caller that creates a Couple must route both partners through
    this helper to avoid IntegrityError.
    """
    if agent_a.id is None or agent_b.id is None:
        raise ValueError(
            "Both agents must be saved (have a primary key) before forming a Couple"
        )
    if agent_a.id == agent_b.id:
        raise ValueError("Cannot form a Couple between an agent and itself")
    if agent_a.id < agent_b.id:
        return agent_a, agent_b
    return agent_b, agent_a


def is_in_active_couple(agent) -> bool:
    """True when the agent is one of the partners in an undissolved Couple."""
    from epocha.apps.demography.models import Couple

    return Couple.objects.filter(
        Q(agent_a=agent) | Q(agent_b=agent),
        dissolved_at_tick__isnull=True,
    ).exists()


def active_couple_for(agent):
    """Return the agent's active Couple (or None)."""
    from epocha.apps.demography.models import Couple

    return Couple.objects.filter(
        Q(agent_a=agent) | Q(agent_b=agent),
        dissolved_at_tick__isnull=True,
    ).first()


def homogamy_score(
    a, b, weights: dict, age_tolerance_years: float = 10.0,
) -> float:
    """Kalmijn-inspired compatibility score between two candidate partners.

    Components (all in [0, 1] before weighting):
    - class similarity: 1.0 if same social_class, 0.0 otherwise
    - education proximity: exp(-|e_a - e_b|)
    - age proximity: exp(-|age_a - age_b| / age_tolerance)
    - relationship: existing Relationship.sentiment in [-1, 1] mapped to [0, 1]

    Returns the weighted sum. Weights come from the era template and are
    design heuristics (see spec §Sezione 3).
    """
    import math
    same_class = 1.0 if a.social_class == b.social_class else 0.0
    edu_diff = abs(float(a.education_level or 0.0) - float(b.education_level or 0.0))
    edu_prox = math.exp(-edu_diff)
    age_diff = abs(float(a.age or 0) - float(b.age or 0))
    age_prox = math.exp(-age_diff / max(1e-9, age_tolerance_years))

    relationship_score = 0.5
    from epocha.apps.agents.models import Relationship

    rel = Relationship.objects.filter(
        Q(agent_from=a, agent_to=b) | Q(agent_from=b, agent_to=a)
    ).first()
    if rel is not None:
        relationship_score = (rel.sentiment + 1.0) / 2.0

    return (
        float(weights.get("w_class", 0.4)) * same_class
        + float(weights.get("w_edu", 0.25)) * edu_prox
        + float(weights.get("w_age", 0.20)) * age_prox
        + float(weights.get("w_relationship", 0.15)) * relationship_score
    )


def stable_matching(
    proposers: list,
    respondents: list,
    score_fn,
) -> list[tuple]:
    """Gale-Shapley stable matching.

    Returns a list of (proposer, respondent) pairs. Both sides must rank
    each other via score_fn(proposer, respondent) -> float. Higher score
    is preferred.

    Complexity: O(n * m) total proposals for n proposers and m respondents.
    Gale & Shapley (1962) prove existence and stability.

    When len(proposers) != len(respondents), the smaller side is fully
    matched and the larger side has unmatched members.
    """
    # Build preference lists: each proposer sorts respondents by descending score
    proposer_prefs = {
        p: sorted(
            respondents,
            key=lambda r: score_fn(p, r),
            reverse=True,
        )
        for p in proposers
    }
    respondent_prefs = {
        r: {p: score_fn(p, r) for p in proposers}
        for r in respondents
    }

    free_proposers = list(proposers)
    engagements: dict = {}
    next_proposal_index: dict = {p: 0 for p in proposers}

    while free_proposers:
        p = free_proposers.pop(0)
        pref_list = proposer_prefs[p]
        if next_proposal_index[p] >= len(pref_list):
            continue
        r = pref_list[next_proposal_index[p]]
        next_proposal_index[p] += 1

        current = engagements.get(r)
        if current is None:
            engagements[r] = p
        elif respondent_prefs[r][p] > respondent_prefs[r][current]:
            engagements[r] = p
            free_proposers.append(current)
        else:
            free_proposers.append(p)

    return [(p, r) for r, p in engagements.items()]


def form_couple(
    agent_x,
    agent_y,
    formed_at_tick: int,
    couple_type: str = "monogamous",
) -> "Couple":
    """Create a Couple with canonical ordering enforced.

    Raises ValueError when the agents are the same or one of them is
    unsaved. Raises IntegrityError upstream if a duplicate active couple
    already exists between the pair (prevented by business logic in
    handlers, not by a unique constraint).
    """
    from epocha.apps.demography.models import Couple

    a, b = _ordered_pair(agent_x, agent_y)
    return Couple.objects.create(
        simulation=a.simulation,
        agent_a=a,
        agent_b=b,
        formed_at_tick=formed_at_tick,
        couple_type=couple_type,
    )


def resolve_pair_bond_intents(simulation, tick: int, rng) -> list["Couple"]:
    """Process pair_bond intents from tick - 1, form couples where mutual.

    Reads DecisionLog.output_decision (TextField, JSON blob). Pre-filters
    with __contains then parses each match via json.loads to extract the
    action and payload. The resolver:
    1. Collects pair_bond DecisionLog entries from tick - 1.
    2. Builds a graph of directed intents (proposer -> target agent id).
    3. Forms a couple when both ends of an edge pair_bonded each other,
       or when the era template sets implicit_mutual_consent=True.
    4. Skips pairs where either agent is already in an active couple.
    5. Handles arranged marriage: when the payload contains for_child,
       the intent is reattributed to the named child toward the match.

    Sources:
    - Tick+1 settlement pattern from Economy Spec 2 Plan 3b (property market).
    - Arranged marriage reattribution follows Goode (1963) §7.
    """
    import json
    from epocha.apps.agents.models import Agent, DecisionLog
    from epocha.apps.demography.template_loader import load_template

    sim_config = simulation.config or {}
    template_name = sim_config.get("demography_template", "pre_industrial_christian")
    template = load_template(template_name)
    couple_cfg = template["couple"]
    implicit_consent = bool(couple_cfg.get("implicit_mutual_consent", True))

    entries = DecisionLog.objects.filter(
        simulation=simulation,
        tick=tick - 1,
        output_decision__contains='"pair_bond"',
    ).select_related("agent")

    intents: dict[int, set[int]] = {}
    by_id: dict[int, Agent] = {}

    for entry in entries:
        try:
            decision = json.loads(entry.output_decision)
        except (json.JSONDecodeError, TypeError):
            continue
        if decision.get("action") != "pair_bond":
            continue
        proposer = entry.agent
        # Arranged marriage: extract child from payload and reattribute intent
        target_payload = decision.get("target")
        match_name: str | None = None
        if isinstance(target_payload, dict):
            child_name = target_payload.get("for_child")
            if child_name:
                child = Agent.objects.filter(
                    simulation=simulation, name=child_name, is_alive=True,
                ).first()
                if child is None:
                    continue
                proposer = child
            match_name = target_payload.get("match")
        elif isinstance(target_payload, str):
            match_name = target_payload
        if not match_name:
            continue
        match = Agent.objects.filter(
            simulation=simulation, name=match_name, is_alive=True,
        ).first()
        if match is None:
            continue
        by_id[proposer.id] = proposer
        intents.setdefault(proposer.id, set()).add(match.id)

    formed: list = []
    used: set[int] = set()
    for proposer_id, targets in intents.items():
        if proposer_id in used:
            continue
        proposer = by_id[proposer_id]
        if is_in_active_couple(proposer):
            continue
        for target_id in targets:
            if target_id in used:
                continue
            target = Agent.objects.filter(id=target_id, is_alive=True).first()
            if target is None or is_in_active_couple(target):
                continue
            mutual = proposer_id in intents.get(target_id, set())
            if not mutual and not implicit_consent:
                continue
            couple = form_couple(
                proposer,
                target,
                formed_at_tick=tick,
                couple_type=couple_cfg.get("default_type", "monogamous"),
            )
            formed.append(couple)
            used.add(proposer_id)
            used.add(target_id)
            break
    return formed


def resolve_separate_intents(simulation, tick: int) -> list["Couple"]:
    """Process separate intents from tick - 1, dissolve active couples.

    Reads DecisionLog.output_decision (JSON blob) with __contains pre-filter
    and json.loads verification, same pattern as resolve_pair_bond_intents.

    Skips entirely when the era template has divorce_enabled=False.
    Returns the list of dissolved Couples.
    """
    import json
    from epocha.apps.agents.models import DecisionLog
    from epocha.apps.demography.template_loader import load_template

    sim_config = simulation.config or {}
    template_name = sim_config.get("demography_template", "pre_industrial_christian")
    template = load_template(template_name)
    if not bool(template["couple"].get("divorce_enabled", False)):
        return []

    entries = DecisionLog.objects.filter(
        simulation=simulation,
        tick=tick - 1,
        output_decision__contains='"separate"',
    ).select_related("agent")

    dissolved: list = []
    for entry in entries:
        try:
            decision = json.loads(entry.output_decision)
        except (json.JSONDecodeError, TypeError):
            continue
        if decision.get("action") != "separate":
            continue
        couple = active_couple_for(entry.agent)
        if couple is None:
            continue
        couple.dissolved_at_tick = tick
        couple.dissolution_reason = "separate"
        couple.save(update_fields=["dissolved_at_tick", "dissolution_reason"])
        dissolved.append(couple)
    return dissolved


def dissolve_on_death(deceased_agent, tick: int) -> "Couple | None":
    """Dissolve any active Couple where the deceased is a partner.

    Captures the deceased's name into the appropriate *_name_snapshot
    field before nulling the FK, so the genealogical record survives
    the delete cascade.
    """
    couple = active_couple_for(deceased_agent)
    if couple is None:
        return None
    if couple.agent_a_id == deceased_agent.id:
        couple.agent_a_name_snapshot = deceased_agent.name
        couple.agent_a = None
    else:
        couple.agent_b_name_snapshot = deceased_agent.name
        couple.agent_b = None
    couple.dissolved_at_tick = tick
    couple.dissolution_reason = "death"
    couple.save(update_fields=[
        "agent_a", "agent_b",
        "agent_a_name_snapshot", "agent_b_name_snapshot",
        "dissolved_at_tick", "dissolution_reason",
    ])
    return couple

"""Agent decision pipeline: context -> personality prompt -> LLM -> parsed action.

Each tick, every agent goes through this pipeline to decide what to do.
The LLM receives the agent's personality, recent memories, relationships,
and world state, then produces a structured JSON action.
"""
from __future__ import annotations

import json
import logging
import math

from epocha.apps.llm_adapter.client import get_llm_client
from epocha.common.utils import clean_llm_json

from .memory import get_relevant_memories
from .models import Agent, DecisionLog, Group, Relationship
from .personality import build_personality_prompt

logger = logging.getLogger(__name__)

# Base action vocabulary for the LLM decision prompt.
# Era-aware actions (pair_bond, separate, avoid_conception) are appended by
# _build_system_prompt() after filtering unavailable options for the current era.
_BASE_ACTIONS = (
    "work|rest|socialize|explore|trade|argue|help|avoid|form_group|join_group"
    "|crime|protest|campaign|move_to|hoard|borrow|sell_property|buy_property"
)

# Demography actions and their LLM-facing descriptions.
# pair_bond: always available (no era restriction).
# separate: filtered out when divorce_enabled is False for the agent's era.
# avoid_conception: filtered out when fertility_agency != "planned".
_DEMOGRAPHY_ACTION_DESCRIPTIONS = {
    "pair_bond": "form a committed romantic partnership with a named person",
    "separate": "end your current partnership and part ways",
    "avoid_conception": "consciously choose to delay having children this season",
}


def _build_system_prompt(agent) -> str:
    """Compose the full system prompt for the decision LLM, including the
    era-filtered demography action vocabulary.

    Reads the demography template attached to the agent's simulation config
    (key: ``demography_template``) to decide which couple/fertility actions
    are available. Falls back gracefully to all three if the template cannot
    be loaded (e.g. economy-only simulations without demography data).

    Args:
        agent: The Agent instance making a decision this tick.

    Returns:
        The complete system prompt string: personality + base actions +
        era-available demography actions.
    """
    personality_prompt = build_personality_prompt(agent.personality)

    # Build the era-filtered action list.
    available_demo_actions = list(_DEMOGRAPHY_ACTION_DESCRIPTIONS.keys())
    try:
        from epocha.apps.demography.template_loader import load_template

        template_name = agent.simulation.config.get("demography_template", "pre_industrial_christian")
        template = load_template(template_name)

        # Remove 'separate' when the era forbids divorce.
        if not template.get("couple", {}).get("divorce_enabled", True):
            available_demo_actions = [a for a in available_demo_actions if a != "separate"]

        # Remove 'avoid_conception' when fertility is purely biological (no agency).
        if template.get("fertility_agency") != "planned":
            available_demo_actions = [a for a in available_demo_actions if a != "avoid_conception"]

    except Exception:
        # Fallback: keep all three actions (legacy economy-only simulations).
        pass

    action_vocab = _BASE_ACTIONS
    if available_demo_actions:
        action_vocab += "|" + "|".join(available_demo_actions)

    # Build the demography action description block (only for available actions).
    demo_lines = "\n".join(
        f'  "{action}": {desc}'
        for action, desc in _DEMOGRAPHY_ACTION_DESCRIPTIONS.items()
        if action in available_demo_actions
    )
    demo_section = f"\nDemography actions:\n{demo_lines}" if demo_lines else ""

    system_prompt_body = (
        f"You are simulating a person in a world. Based on your personality,\n"
        f"memories, relationships, and current situation, decide what to do next.\n"
        f"\nRespond ONLY with a JSON object:\n"
        f'{{\n'
        f'    "action": "{action_vocab}",\n'
        f'    "target": "who or what (optional)",\n'
        f'    "reason": "brief internal thought"\n'
        f"}}"
        f"{demo_section}"
    )

    return f"{personality_prompt}\n\n{system_prompt_body}"

# Fallback action when the LLM response cannot be parsed as JSON.
_FALLBACK_ACTION = {"action": "rest", "reason": "confused"}

# Maximum number of other living agents listed in the decision context.
# Keeps prompt length bounded while providing enough social awareness.
# At 20 agents with ~30 chars each, this adds ~600 chars to the prompt.
_MAX_CONTEXT_AGENTS = 20


def _build_context(
    agent,
    world_state,
    tick: int,
    memories,
    relationships,
    recent_events=None,
    living_agents=None,
    group_context=None,
    political_context=None,
    reputation_context=None,
    zone_context=None,
    economic_context=None,
) -> str:
    """Assemble the situational context string sent as the LLM user prompt.

    Args:
        agent: The agent making the decision.
        world_state: Current world state object.
        tick: Current simulation tick.
        memories: List of relevant Memory objects for this agent.
        relationships: List of Relationship objects for this agent.
        recent_events: Optional list of recent Event objects to react to.
        living_agents: Optional list of other living Agent objects in the
            simulation. When provided, the prompt explicitly enumerates valid
            interaction targets to prevent the LLM from hallucinating names.
        group_context: Optional pre-formatted string describing the agent's
            faction (name, objective, leader, members, cohesion). None when
            the agent does not belong to any group.
        political_context: Optional pre-formatted string describing the current
            government type, stability, head of state, institutional trust, and
            corruption level. None when no government exists for the simulation.
        reputation_context: Optional pre-formatted string summarising how the
            agent perceives the standing of notable peers (respected or mistrusted).
            None when no reputation data is available.
        zone_context: Optional pre-formatted string listing available zones with
            distances and reachability for the current tick. None when zone data
            is unavailable.
        economic_context: Optional pre-formatted string describing the agent's
            cash, inventory, properties, and local market prices. None when the
            economy app is not initialized for this simulation.
    """
    parts = [
        f"You are {agent.name}, a {agent.role}.",
        f"Tick: {tick}. Health: {agent.health:.1f}, wealth: {agent.wealth:.1f}, mood: {agent.mood:.1f}.",
        f"World stability: {world_state.stability_index:.1f}.",
    ]

    if living_agents:
        parts.append("\nOther people in your world:")
        for a in living_agents:
            parts.append(f"- {a.name} ({a.role})")
        parts.append("You can ONLY interact with people listed above. Do not invent names.")

    # Group/faction context
    if group_context:
        parts.append(f"\n{group_context}")

    # Political context
    if political_context:
        parts.append(f"\n{political_context}")

    # Reputation context
    if reputation_context:
        parts.append(f"\n{reputation_context}")

    # Zone context (available destinations)
    if zone_context:
        parts.append(f"\n{zone_context}")

    # Economic context
    if economic_context:
        parts.append(f"\n{economic_context}")

    # Injected events that the agent should react to
    if recent_events:
        parts.append("\nIMPORTANT - Recent events that happened in your world:")
        for event in recent_events:
            parts.append(f"- {event.title}: {event.description}")
        parts.append("React to these events based on your personality and situation.")

    if memories:
        parts.append("\nYour recent memories:")
        for m in memories:
            source_label = f" ({m.source_type})" if m.source_type != "direct" else ""
            parts.append(f"- {m.content}{source_label}")

    if relationships:
        parts.append("\nYour relationships:")
        for rel in relationships:
            sentiment_word = "positively" if rel.sentiment > 0 else "negatively"
            parts.append(
                f"- {rel.agent_to.name} ({rel.relation_type}, "
                f"you feel {sentiment_word}, strength: {rel.strength:.1f})"
            )

    return "\n".join(parts)


def process_agent_decision(agent, world_state, tick: int) -> dict:
    """Execute the full decision pipeline for one agent at one tick.

    Steps:
    1. Retrieve relevant memories and relationships
    2. Build situational context (user prompt)
    3. Build personality prompt (system prompt)
    4. Call LLM
    5. Parse JSON response (with fallback)
    6. Log decision for replay/debugging

    Returns the parsed action dict.
    """
    client = get_llm_client()

    # 1. Gather context
    from epocha.apps.simulation.models import Event

    memories = get_relevant_memories(agent, current_tick=tick, max_memories=5)
    relationships = list(
        Relationship.objects.filter(agent_from=agent)
        .select_related("agent_to")[:10]
    )
    # Include recent events (injected by user or system) from last 5 ticks
    recent_events = list(
        Event.objects.filter(simulation=agent.simulation, tick__gte=max(0, tick - 5))
        .order_by("-tick")[:5]
    )
    # Enumerate living agents so the LLM only references real characters
    living_agents = list(
        Agent.objects.filter(simulation=agent.simulation, is_alive=True)
        .exclude(id=agent.id)
        .only("name", "role")
        .order_by("name")[:_MAX_CONTEXT_AGENTS]
    )

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

    # Build political context (government is reused by zone context below)
    political_context = None
    government = None
    try:
        from epocha.apps.world.models import Government
        government = Government.objects.get(simulation=agent.simulation)
        from epocha.apps.world.government_types import GOVERNMENT_TYPES
        type_label = GOVERNMENT_TYPES.get(government.government_type, {}).get("label", government.government_type)
        stability_word = "stable" if government.stability > 0.6 else "moderate" if government.stability > 0.3 else "unstable"
        head_name = government.head_of_state.name if government.head_of_state else "none"
        political_context = (
            f"Government: {type_label} ({stability_word})\n"
            f"Head of state: {head_name}\n"
            f"Trust: {'high' if government.institutional_trust > 0.6 else 'low' if government.institutional_trust < 0.3 else 'moderate'}. "
            f"Corruption: {'high' if government.corruption > 0.6 else 'low' if government.corruption < 0.3 else 'moderate'}."
        )
    except Exception:
        pass

    # Build reputation context
    reputation_context = None
    try:
        from epocha.apps.agents.models import ReputationScore
        notable = ReputationScore.objects.filter(holder=agent).select_related("target").exclude(target=agent)
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

    # Build economic context
    economic_context = None
    try:
        from epocha.apps.economy.context import build_economic_context
        economic_context = build_economic_context(agent, tick)
    except Exception:
        pass

    # Build zone context (reuses world_state from caller and government from political context)
    zone_context = None
    try:
        from epocha.apps.world.models import Zone
        from epocha.apps.agents.movement import calculate_max_distance, get_transport_type

        zones = Zone.objects.filter(world=world_state)
        gov = government
        transport = get_transport_type(agent)
        max_dist = calculate_max_distance(transport, agent.health, world_state, gov)
        zone_lines = []
        for z in zones:
            if agent.zone and z.id == agent.zone_id:
                zone_lines.append(f"- {z.name} ({z.zone_type}, your current zone)")
            elif z.center and agent.location:
                dist_grid = math.hypot(z.center.x - agent.location.x, z.center.y - agent.location.y)
                dist_km = dist_grid * world_state.distance_scale / 1000.0
                reachable = "reachable" if dist_grid <= max_dist else "too far this tick"
                zone_lines.append(f"- {z.name} ({z.zone_type}, ~{dist_km:.0f} km, {reachable})")
            else:
                zone_lines.append(f"- {z.name} ({z.zone_type})")
        if zone_lines:
            zone_context = "Available zones:\n" + "\n".join(zone_lines)
    except Exception:
        logger.debug("Failed to build zone context for %s", agent.name, exc_info=True)

    context = _build_context(
        agent, world_state, tick, memories, relationships, recent_events, living_agents, group_context,
        political_context, reputation_context, zone_context, economic_context,
    )

    # 2. Build system prompt with personality and era-filtered action vocabulary
    system_prompt = _build_system_prompt(agent)

    # 3. Call LLM (/no_think disables Qwen3 reasoning for faster responses)
    raw_response = client.complete(
        prompt=f"{context} /no_think",
        system_prompt=system_prompt,
        temperature=0.7,
        max_tokens=150,
    )

    # 4. Parse response (strip markdown fences if present)
    cleaned = clean_llm_json(raw_response)

    try:
        action = json.loads(cleaned)
    except json.JSONDecodeError:
        logger.warning("Agent %s returned non-JSON at tick %d: %s", agent.name, tick, raw_response[:100])
        action = {**_FALLBACK_ACTION, "raw": raw_response}

    # 5. Log decision
    DecisionLog.objects.create(
        simulation=agent.simulation,
        agent=agent,
        tick=tick,
        input_context=context,
        output_decision=json.dumps(action),
        llm_model=client.get_model_name(),
    )

    return action

"""Agent decision pipeline: context -> personality prompt -> LLM -> parsed action.

Each tick, every agent goes through this pipeline to decide what to do.
The LLM receives the agent's personality, recent memories, relationships,
and world state, then produces a structured JSON action.
"""
from __future__ import annotations

import json
import logging

from epocha.apps.llm_adapter.client import get_llm_client
from epocha.common.utils import clean_llm_json

from .memory import get_relevant_memories
from .models import Agent, DecisionLog, Group, Relationship
from .personality import build_personality_prompt

logger = logging.getLogger(__name__)

# System prompt instructing the LLM to produce a structured JSON decision.
_DECISION_SYSTEM_PROMPT = """You are simulating a person in a world. Based on your personality,
memories, relationships, and current situation, decide what to do next.

Respond ONLY with a JSON object:
{
    "action": "work|rest|socialize|explore|trade|argue|help|avoid|form_group|join_group|crime|protest|campaign",
    "target": "who or what (optional)",
    "reason": "brief internal thought"
}
"""

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

    # Build political context
    political_context = None
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

    context = _build_context(
        agent, world_state, tick, memories, relationships, recent_events, living_agents, group_context,
        political_context,
    )

    # 2. Build system prompt with personality
    personality_prompt = build_personality_prompt(agent.personality)
    system_prompt = f"{personality_prompt}\n\n{_DECISION_SYSTEM_PROMPT}"

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

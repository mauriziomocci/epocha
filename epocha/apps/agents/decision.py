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
from .models import DecisionLog, Relationship
from .personality import build_personality_prompt

logger = logging.getLogger(__name__)

# System prompt instructing the LLM to produce a structured JSON decision.
_DECISION_SYSTEM_PROMPT = """You are simulating a person in a world. Based on your personality,
memories, relationships, and current situation, decide what to do next.

Respond ONLY with a JSON object:
{
    "action": "work|rest|socialize|explore|trade|argue|help|avoid",
    "target": "who or what (optional)",
    "reason": "brief internal thought"
}
"""

# Fallback action when the LLM response cannot be parsed as JSON.
_FALLBACK_ACTION = {"action": "rest", "reason": "confused"}


def _build_context(agent, world_state, tick: int, memories, relationships, recent_events=None) -> str:
    """Assemble the situational context string sent as the LLM user prompt."""
    parts = [
        f"You are {agent.name}, a {agent.role}.",
        f"Tick: {tick}. Health: {agent.health:.1f}, wealth: {agent.wealth:.1f}, mood: {agent.mood:.1f}.",
        f"World stability: {world_state.stability_index:.1f}.",
    ]

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
    context = _build_context(agent, world_state, tick, memories, relationships, recent_events)

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

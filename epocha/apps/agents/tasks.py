"""Celery tasks for parallel agent processing.

Each agent's turn is a separate Celery task, enabling parallel execution
across workers. The task returns a result dict that the finalize_tick
callback aggregates for WebSocket broadcast.
"""

from __future__ import annotations

import logging

from config.celery import app

logger = logging.getLogger(__name__)

_FALLBACK_RESULT = {
    "action": "rest",
    "reason": "error in decision pipeline",
    "error": True,
}


@app.task(bind=True, acks_late=True, max_retries=0)
def process_agent_turn(self, agent_id: int, simulation_id: int, tick: int) -> dict:
    """Process a single agent's decision, apply consequences, return result.

    Designed to run as part of a Celery chord. Returns a dict with the
    action taken and optional event data for the WebSocket feed.

    Args:
        agent_id: Primary key of the agent.
        simulation_id: Primary key of the simulation (used to fetch world).
        tick: Current simulation tick number.

    Returns:
        Dict with keys: action, reason, agent_name, and optionally event/error/skipped.
    """
    from epocha.apps.agents.decision import process_agent_decision
    from epocha.apps.agents.models import Agent
    from epocha.apps.simulation.engine import (
        _ACTION_EMOTIONAL_WEIGHT,
        apply_agent_action,
    )
    from epocha.apps.world.models import World

    try:
        agent = Agent.objects.get(id=agent_id)
    except Agent.DoesNotExist:
        logger.error("Agent %d not found at tick %d", agent_id, tick)
        return {**_FALLBACK_RESULT, "agent_name": "unknown", "error": True}

    if not agent.is_alive:
        return {"action": "none", "agent_name": agent.name, "skipped": True}

    try:
        world = World.objects.get(simulation_id=simulation_id)
        action = process_agent_decision(agent, world, tick)
        apply_agent_action(agent, action, tick)

        action_type = action.get("action", "rest")
        result = {
            "action": action_type,
            "reason": action.get("reason", ""),
            "agent_name": agent.name,
        }

        if action_type not in ("rest", "work"):
            result["event"] = {
                "title": f"{agent.name} decided to {action_type}",
                "severity": _ACTION_EMOTIONAL_WEIGHT.get(action_type, 0.1),
                "agent": agent.name,
                "reason": action.get("reason", ""),
            }

        return result

    except Exception:
        logger.exception("Agent %s failed at tick %d", agent.name, tick)
        return {**_FALLBACK_RESULT, "agent_name": agent.name}

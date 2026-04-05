"""Tick orchestrator: coordinates economy, agent decisions, memory, and events.

Each tick is a discrete time step where:
1. The economy updates (income, costs, mood effects)
2. Each living agent makes a decision via LLM
3. Decision consequences are applied (mood, health adjustments)
4. Memories are created from actions
5. Old memories decay periodically
6. The tick counter advances

Agent failures are isolated: if one agent's LLM call fails, the tick
continues for all other agents. This ensures simulation resilience.

Module-level functions (run_economy, run_memory_decay, broadcast_tick) are
used by both the SimulationEngine (synchronous path) and the Celery chord
tasks (production path). This avoids duplicating logic across execution modes.
"""

from __future__ import annotations

import logging

from epocha.apps.agents.decision import process_agent_decision
from epocha.apps.agents.memory import decay_memories
from epocha.apps.agents.models import Agent, Memory
from epocha.apps.world.economy import process_economy_tick

logger = logging.getLogger(__name__)

# Emotional weight assigned to action memories.
# Conflictual actions (argue, help) leave stronger impressions.
_ACTION_EMOTIONAL_WEIGHT: dict[str, float] = {
    "argue": 0.4,
    "help": 0.3,
    "betray": 0.8,
    "socialize": 0.2,
    "explore": 0.2,
    "trade": 0.15,
    "work": 0.1,
    "rest": 0.05,
    "avoid": 0.15,
}
_DEFAULT_EMOTIONAL_WEIGHT = 0.1

# Mood adjustments from different action types.
_ACTION_MOOD_DELTA: dict[str, float] = {
    "work": 0.01,
    "rest": 0.02,
    "socialize": 0.03,
    "help": 0.03,
    "argue": -0.05,
    "avoid": -0.02,
    "explore": 0.02,
    "trade": 0.01,
}

# Memory decay runs every N ticks to reduce DB writes.
_MEMORY_DECAY_INTERVAL = 10

# Number of recent ticks to check for duplicate memories.
# If the agent performed the same action within this window, skip memory creation.
_MEMORY_DEDUP_TICKS = 3


def apply_agent_action(agent: Agent, action: dict, tick: int) -> None:
    """Apply consequences of an agent's action and create a memory.

    Extracted as a standalone function so it can be called from both
    the SimulationEngine and the process_agent_turn Celery task.

    Args:
        agent: The agent performing the action.
        action: Dict with at least "action" key (e.g. "work", "rest", "argue")
            and optionally "reason".
        tick: Current simulation tick number.
    """
    action_type = action.get("action", "rest")

    # Mood adjustment
    mood_delta = _ACTION_MOOD_DELTA.get(action_type, 0.0)
    agent.mood = max(0.0, min(1.0, agent.mood + mood_delta))

    # Rest restores a small amount of health
    if action_type == "rest":
        agent.health = min(1.0, agent.health + 0.02)

    agent.save(update_fields=["mood", "health"])

    # Create memory of the action (skip if a duplicate of the same action type
    # was the most recent memory created within the dedup window).
    # Using the last-created memory avoids suppressing the same action after
    # a different action has interrupted the streak.
    dedup_prefix = f"I decided to {action_type}."
    last_memory = (
        Memory.objects.filter(
            agent=agent,
            is_active=True,
            tick_created__gte=max(0, tick - _MEMORY_DEDUP_TICKS),
        )
        .order_by("-tick_created", "-id")
        .first()
    )
    recent_duplicate = last_memory is not None and last_memory.content.startswith(dedup_prefix)

    if not recent_duplicate:
        emotional_weight = _ACTION_EMOTIONAL_WEIGHT.get(
            action_type, _DEFAULT_EMOTIONAL_WEIGHT
        )
        reason = action.get("reason", "")
        Memory.objects.create(
            agent=agent,
            content=f"I decided to {action_type}. {reason}".strip(),
            emotional_weight=emotional_weight,
            source_type="direct",
            tick_created=tick,
        )


def run_economy(simulation) -> None:
    """Run the economy tick for a simulation's world."""
    world = simulation.world
    process_economy_tick(world, simulation.current_tick + 1)


def run_memory_decay(simulation, tick: int) -> None:
    """Decay memories for all living agents if at the decay interval.

    Memory decay runs every _MEMORY_DECAY_INTERVAL ticks to reduce the
    number of DB writes. On non-decay ticks this is a no-op.

    Args:
        simulation: The simulation instance.
        tick: The current tick number (decay runs when tick % interval == 0).
    """
    if tick % _MEMORY_DECAY_INTERVAL != 0:
        return
    agents = Agent.objects.filter(simulation=simulation, is_alive=True)
    for agent in agents:
        decay_memories(agent, tick)


def broadcast_tick(simulation, tick: int, events: list) -> None:
    """Send tick update to all connected WebSocket clients.

    Broadcasts events, agent summary, and world state via the Channels
    layer. Clients subscribed to the simulation group receive real-time
    updates. Failures are logged but never crash the simulation.

    Args:
        simulation: The simulation instance.
        tick: The tick number to broadcast.
        events: List of event dicts from agent actions.
    """
    try:
        from asgiref.sync import async_to_sync
        from channels.layers import get_channel_layer

        channel_layer = get_channel_layer()
        if channel_layer is None:
            return

        agents = list(Agent.objects.filter(simulation=simulation, is_alive=True))
        agent_count = len(agents)
        world = simulation.world
        data = {
            "tick": tick,
            "events": events,
            "agents_summary": {
                "alive": agent_count,
                "avg_mood": round(sum(a.mood for a in agents) / max(agent_count, 1), 2),
                "avg_wealth": round(
                    sum(a.wealth for a in agents) / max(agent_count, 1), 2
                ),
            },
            "world": {
                "stability": round(world.stability_index, 2),
            },
        }

        async_to_sync(channel_layer.group_send)(
            f"simulation_{simulation.id}",
            {"type": "simulation_update", "data": data},
        )
    except Exception:
        logger.exception("Failed to broadcast tick %d", tick)


class SimulationEngine:
    """Orchestrates one tick of the simulation.

    For synchronous execution (tests, dashboard). The Celery-based
    production path uses run_simulation_loop which launches a chord.
    """

    def __init__(self, simulation):
        self.simulation = simulation

    def run_tick(self) -> None:
        """Execute a single simulation tick synchronously."""
        tick = self.simulation.current_tick + 1
        world = self.simulation.world

        logger.info("Simulation %d: running tick %d", self.simulation.id, tick)

        # 1. Economy
        process_economy_tick(world, tick)

        # 2. Agent decisions (sequential fallback)
        agents = list(Agent.objects.filter(simulation=self.simulation, is_alive=True))
        tick_events = []
        for agent in agents:
            agent.refresh_from_db()
            try:
                action = process_agent_decision(agent, world, tick)
                apply_agent_action(agent, action, tick)
                action_type = action.get("action", "rest")
                if action_type not in ("rest", "work"):
                    tick_events.append(
                        {
                            "title": f"{agent.name} decided to {action_type}",
                            "severity": _ACTION_EMOTIONAL_WEIGHT.get(action_type, 0.1),
                            "agent": agent.name,
                            "reason": action.get("reason", ""),
                        }
                    )
            except Exception:
                logger.exception("Agent %s failed at tick %d", agent.name, tick)

        # 3. Memory decay
        run_memory_decay(self.simulation, tick)

        # 4. Advance tick
        self.simulation.current_tick = tick
        self.simulation.save(update_fields=["current_tick", "updated_at"])

        # 5. Broadcast
        broadcast_tick(self.simulation, tick, tick_events)

        logger.info("Simulation %d: tick %d complete", self.simulation.id, tick)

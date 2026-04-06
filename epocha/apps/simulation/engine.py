"""Tick orchestrator: coordinates economy, decisions, information, factions, politics, analytics, and events.

Each tick is a discrete time step where:
1. The economy updates (income, costs, mood effects)
2. Each living agent makes a decision via LLM
3. Decision consequences are applied (mood, health adjustments)
4. Memories are created from actions
5. Information propagates through the social network (hearsay, rumors)
6. Faction dynamics run periodically (cohesion, leadership, formation)
7. Political cycle runs periodically (institutions, stratification, transitions, elections)
8. Old memories decay periodically
9. Snapshot captured and Epochal Crises detected
10. The tick counter advances

Agent failures are isolated: if one agent's LLM call fails, the tick
continues for all other agents. This ensures simulation resilience.

Module-level functions (run_economy, run_memory_decay, broadcast_tick) are
used by both the SimulationEngine (synchronous path) and the Celery chord
tasks (production path). This avoids duplicating logic across execution modes.
"""

from __future__ import annotations

import logging

from epocha.apps.agents.decision import process_agent_decision
from epocha.apps.agents.factions import process_faction_dynamics
from epocha.apps.agents.information_flow import propagate_information
from epocha.apps.agents.memory import decay_memories
from epocha.apps.agents.models import Agent, Memory
from epocha.apps.agents.relationships import evolve_relationships, update_relationship_from_interaction
from epocha.apps.simulation.snapshot import capture_and_detect
from epocha.apps.world.economy import process_economy_tick
from epocha.apps.world.government import process_political_cycle

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
    "form_group": 0.3,
    "join_group": 0.3,
    "crime": 0.6,
    "protest": 0.4,
    "campaign": 0.2,
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
    "form_group": 0.04,
    "join_group": 0.03,
    "crime": -0.03,
    "protest": -0.02,
    "campaign": 0.02,
}

# Memory decay runs every N ticks to reduce DB writes.
_MEMORY_DECAY_INTERVAL = 10

# Number of recent ticks to check for duplicate memories.
# If the agent performed the same action within this window, skip memory creation.
# Value of 3 chosen as pragmatic balance: short enough that intentional repetition
# (e.g. an agent who argues for 5+ ticks) eventually creates new memories,
# long enough to suppress the common case of 2-3 tick stutters.
# No empirical source -- tunable based on observed simulation behavior.
_MEMORY_DEDUP_TICKS = 3


def apply_agent_action(agent: Agent, action: dict, tick: int) -> None:
    """Apply consequences of an agent's action and create a memory.

    Extracted as a standalone function so it can be called from both
    the SimulationEngine and the process_agent_turn Celery task.

    Memory deduplication: if the agent already has an active memory for
    the same action type within the last _MEMORY_DEDUP_TICKS ticks,
    skip creation to prevent context saturation from repetitive behavior.

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

    # Update relationship if the action targets another agent
    target_name = action.get("target", "")
    if target_name and action_type not in ("rest", "work", "explore"):
        target_agent = (
            Agent.objects.filter(simulation=agent.simulation, is_alive=True, name__icontains=target_name)
            .exclude(id=agent.id)
            .first()
        )
        if target_agent:
            update_relationship_from_interaction(agent, target_agent, action_type, tick)

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
            origin_agent=agent,
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

        # 3. Information flow (propagate hearsay and rumors)
        propagate_information(self.simulation, tick)

        # 4. Faction dynamics (every N ticks)
        process_faction_dynamics(self.simulation, tick)

        # 5. Political cycle (every N ticks)
        process_political_cycle(self.simulation, tick)

        # 6. Relationship decay
        evolve_relationships(self.simulation, tick)

        # 7. Memory decay
        run_memory_decay(self.simulation, tick)

        # 8. Capture snapshot + detect crises
        capture_and_detect(self.simulation, tick)

        # 9. Advance tick
        self.simulation.current_tick = tick
        self.simulation.save(update_fields=["current_tick", "updated_at"])

        # 10. Broadcast
        broadcast_tick(self.simulation, tick, tick_events)

        logger.info("Simulation %d: tick %d complete", self.simulation.id, tick)

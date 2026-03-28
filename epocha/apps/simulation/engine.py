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


class SimulationEngine:
    """Orchestrates one tick of the simulation.

    Usage:
        engine = SimulationEngine(simulation)
        engine.run_tick()  # advances by one tick
    """

    def __init__(self, simulation):
        self.simulation = simulation

    def run_tick(self) -> None:
        """Execute a single simulation tick."""
        tick = self.simulation.current_tick + 1
        world = self.simulation.world

        logger.info("Simulation %d: running tick %d", self.simulation.id, tick)

        # 1. Economy (updates wealth, mood, health, stability)
        process_economy_tick(world, tick)

        # 2. Agent decisions (re-fetch from DB after economy changes)
        agents = list(
            Agent.objects.filter(simulation=self.simulation, is_alive=True)
        )
        for agent in agents:
            agent.refresh_from_db()
            try:
                action = process_agent_decision(agent, world, tick)
                self._apply_action(agent, action, tick)
            except Exception:
                logger.exception("Agent %s failed at tick %d", agent.name, tick)

        # 3. Memory decay (periodic, to reduce DB writes)
        if tick % _MEMORY_DECAY_INTERVAL == 0:
            for agent in agents:
                decay_memories(agent, tick)

        # 4. Advance tick counter
        self.simulation.current_tick = tick
        self.simulation.save(update_fields=["current_tick", "updated_at"])

        logger.info("Simulation %d: tick %d complete", self.simulation.id, tick)

    def _apply_action(self, agent: Agent, action: dict, tick: int) -> None:
        """Apply consequences of an agent's action and create a memory."""
        action_type = action.get("action", "rest")

        # Mood adjustment
        mood_delta = _ACTION_MOOD_DELTA.get(action_type, 0.0)
        agent.mood = max(0.0, min(1.0, agent.mood + mood_delta))

        # Rest restores a small amount of health
        if action_type == "rest":
            agent.health = min(1.0, agent.health + 0.02)

        agent.save(update_fields=["mood", "health"])

        # Create memory of the action
        emotional_weight = _ACTION_EMOTIONAL_WEIGHT.get(action_type, _DEFAULT_EMOTIONAL_WEIGHT)
        reason = action.get("reason", "")
        Memory.objects.create(
            agent=agent,
            content=f"I decided to {action_type}. {reason}".strip(),
            emotional_weight=emotional_weight,
            source_type="direct",
            tick_created=tick,
        )

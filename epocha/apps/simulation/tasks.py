"""Celery tasks for the simulation tick loop.

Production path: run_simulation_loop runs the economy tick, then launches
a Celery chord of process_agent_turn tasks (one per living agent). When
all agent tasks complete, the finalize_tick callback advances the tick,
decays memories, broadcasts via WebSocket, and re-enqueues the loop.

The chord pattern ensures no worker blocks waiting for others. Each
agent task runs independently and in parallel across available workers.
"""

from __future__ import annotations

import logging

from celery import chord

from config.celery import app

logger = logging.getLogger(__name__)


@app.task
def run_simulation_loop(simulation_id: int) -> None:
    """Execute one tick: economy + parallel agent chord + finalize callback.

    Steps:
    1. Verify simulation is still running
    2. Run economy tick (synchronous, fast)
    3. Launch chord: one process_agent_turn per living agent
    4. Chord callback (finalize_tick) handles the rest
    """
    from epocha.apps.agents.models import Agent
    from epocha.apps.simulation.engine import run_economy
    from epocha.apps.simulation.models import Simulation

    simulation = Simulation.objects.get(id=simulation_id)
    if simulation.status != Simulation.Status.RUNNING:
        logger.info("Simulation %d no longer running, stopping loop", simulation_id)
        return

    tick = simulation.current_tick + 1
    logger.info("Simulation %d: starting tick %d (chord)", simulation_id, tick)

    # 1. Economy tick (fast, synchronous)
    run_economy(simulation)

    # 2. Build chord of agent tasks
    from epocha.apps.agents.tasks import process_agent_turn

    agent_ids = list(
        Agent.objects.filter(simulation=simulation, is_alive=True).values_list(
            "id", flat=True
        )
    )

    if not agent_ids:
        finalize_tick([], simulation_id, tick)
        return

    header = [
        process_agent_turn.s(agent_id, simulation_id, tick) for agent_id in agent_ids
    ]
    callback = finalize_tick.s(simulation_id, tick)

    chord(header)(callback)


@app.task
def finalize_tick(agent_results: list, simulation_id: int, tick: int) -> None:
    """Chord callback: runs after all agent tasks complete.

    Collects events from agent results, decays memories, advances the
    tick counter, broadcasts to WebSocket, and re-enqueues the loop
    if the simulation is still running.

    Args:
        agent_results: List of dicts returned by each process_agent_turn task.
        simulation_id: Primary key of the simulation.
        tick: The tick number that was just processed.
    """
    from django.conf import settings

    from epocha.apps.simulation.engine import broadcast_tick, run_memory_decay
    from epocha.apps.simulation.models import Simulation

    simulation = Simulation.objects.get(id=simulation_id)

    # Collect events from agent results
    events = []
    for result in agent_results:
        if result is None:
            continue
        if "event" in result:
            events.append(result["event"])

    # Information flow (propagate hearsay and rumors)
    from epocha.apps.agents.information_flow import propagate_information
    propagate_information(simulation, tick)

    # Faction dynamics (every N ticks)
    from epocha.apps.agents.factions import process_faction_dynamics
    process_faction_dynamics(simulation, tick)

    # Political cycle (every N ticks)
    from epocha.apps.world.government import process_political_cycle
    process_political_cycle(simulation, tick)

    # Relationship decay
    from epocha.apps.agents.relationships import evolve_relationships
    evolve_relationships(simulation, tick)

    # Memory decay (periodic)
    run_memory_decay(simulation, tick)

    # Capture snapshot + detect crises
    from epocha.apps.simulation.snapshot import capture_and_detect
    capture_and_detect(simulation, tick)

    # Advance tick counter
    simulation.current_tick = tick
    simulation.save(update_fields=["current_tick", "updated_at"])

    # Broadcast to WebSocket
    broadcast_tick(simulation, tick, events)

    logger.info("Simulation %d: tick %d complete (chord)", simulation_id, tick)

    # Re-enqueue if still running
    simulation.refresh_from_db()
    if simulation.status == Simulation.Status.RUNNING:
        tick_interval = settings.EPOCHA_DEFAULT_TICK_INTERVAL_SECONDS
        countdown = tick_interval / max(simulation.speed, 0.1)
        run_simulation_loop.apply_async(args=[simulation_id], countdown=countdown)
    else:
        logger.info("Simulation %d paused/stopped, not re-enqueuing", simulation_id)


@app.task(bind=True, acks_late=True)
def run_tick(self, simulation_id: int) -> None:
    """Execute a single simulation tick synchronously (legacy/fallback).

    Kept for backward compatibility with the dashboard's synchronous
    tick execution. Production path uses run_simulation_loop + chord.
    """
    from .engine import SimulationEngine
    from .models import Simulation

    simulation = Simulation.objects.get(id=simulation_id)
    if simulation.status != Simulation.Status.RUNNING:
        return

    engine = SimulationEngine(simulation)
    engine.run_tick()

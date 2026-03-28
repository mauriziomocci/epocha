"""Celery tasks for the simulation tick loop.

Uses a self-enqueuing pattern instead of while-True + sleep to avoid
blocking a Celery worker indefinitely. Each invocation of
run_simulation_loop executes one tick, then re-enqueues itself with
a countdown delay based on the simulation speed.

The run_tick task uses acks_late=True so if the worker dies mid-tick,
the task will be re-delivered and the tick re-executed from the start
(the previous tick's state is already persisted in PostgreSQL).
"""
from __future__ import annotations

import logging

from config.celery import app

logger = logging.getLogger(__name__)


@app.task(bind=True, acks_late=True)
def run_tick(self, simulation_id: int) -> None:
    """Execute a single simulation tick in background.

    Safe for re-delivery: if the worker crashes, the tick restarts
    from the last persisted state.
    """
    from .engine import SimulationEngine
    from .models import Simulation

    simulation = Simulation.objects.get(id=simulation_id)
    if simulation.status != Simulation.Status.RUNNING:
        return

    engine = SimulationEngine(simulation)
    engine.run_tick()


@app.task
def run_simulation_loop(simulation_id: int) -> None:
    """Execute one tick and re-enqueue self if simulation is still running.

    Uses apply_async with countdown instead of blocking sleep to free
    the Celery worker between ticks. This allows the worker to process
    other tasks (agent decisions, chat responses) between simulation ticks.
    """
    from django.conf import settings

    from .engine import SimulationEngine
    from .models import Simulation

    simulation = Simulation.objects.get(id=simulation_id)
    if simulation.status != Simulation.Status.RUNNING:
        logger.info("Simulation %d no longer running, stopping loop", simulation_id)
        return

    # Execute tick
    engine = SimulationEngine(simulation)
    engine.run_tick()

    # Re-enqueue with delay based on speed
    tick_interval = settings.EPOCHA_DEFAULT_TICK_INTERVAL_SECONDS
    countdown = tick_interval / max(simulation.speed, 0.1)
    run_simulation_loop.apply_async(args=[simulation_id], countdown=countdown)

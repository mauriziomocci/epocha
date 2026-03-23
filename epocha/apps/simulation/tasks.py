"""Celery tasks for the simulation."""
from config.celery import app


@app.task(bind=True)
def run_tick(self, simulation_id):
    """Execute a simulation tick in background."""
    raise NotImplementedError("To be implemented in MVP")


@app.task
def run_simulation_loop(simulation_id):
    """Continuous loop: execute ticks while the simulation is in RUNNING state."""
    raise NotImplementedError("To be implemented in MVP")

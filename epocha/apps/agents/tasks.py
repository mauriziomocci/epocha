"""Celery tasks for agent processing."""
from config.celery import app


@app.task
def process_agent_turn(agent_id, tick):
    """Process a single agent's turn."""
    raise NotImplementedError("To be implemented in MVP")

"""Celery tasks for agent response generation."""
from config.celery import app


@app.task
def generate_agent_response(session_id, user_message):
    """Generate the agent response in background via LLM."""
    raise NotImplementedError("To be implemented in MVP")

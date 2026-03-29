"""Generate narrative report at end of simulation.

Produces a structured report summarizing the simulation's history, notable
events, key agents, and final state. Written in an encyclopedic style
inspired by Asimov's Galactic Encyclopedia.
"""
from __future__ import annotations

import logging

from epocha.apps.agents.models import Agent, DecisionLog
from epocha.apps.llm_adapter.client import get_llm_client

from .models import Event

logger = logging.getLogger(__name__)

_REPORT_SYSTEM_PROMPT = """You are a historian writing an encyclopedia entry about a simulated civilization.
Based on the data provided (events, agents, economic state), write a structured narrative report.

Structure:
1. Overview: period covered, population, key statistics
2. Major Events: the most significant events and their consequences
3. Notable Individuals: agents who had the greatest impact
4. Patterns: recurring cycles or trends observed
5. Final State: how the civilization ended up

Write in a scholarly, engaging tone. Be specific — reference actual events and agents by name.
Do not invent events that are not in the data."""


def generate_simulation_report(simulation) -> str:
    """Generate and save a narrative report for the simulation.

    Gathers events, agents, and decision logs, builds a context prompt,
    and calls the LLM to produce the report. The result is saved to
    the simulation's report field.

    Returns the generated report text.
    """
    client = get_llm_client()

    # Gather data
    events = Event.objects.filter(simulation=simulation).order_by("tick")[:50]
    agents = Agent.objects.filter(simulation=simulation)
    world = simulation.world
    total_decisions = DecisionLog.objects.filter(simulation=simulation).count()

    # Build context
    events_text = "\n".join(
        f"- [Tick {e.tick}] {e.title} (severity: {e.severity}): {e.description}"
        for e in events
    ) or "No significant events recorded."

    agents_text = "\n".join(
        f"- {a.name} ({a.role}): wealth={a.wealth:.0f}, health={a.health:.1f}, "
        f"mood={a.mood:.1f}, alive={a.is_alive}"
        for a in agents[:30]
    ) or "No agents."

    context = (
        f"Simulation: {simulation.name}\n"
        f"Period: tick 0 to tick {simulation.current_tick}\n"
        f"World stability: {world.stability_index:.2f}\n"
        f"Total agents: {agents.count()} ({agents.filter(is_alive=True).count()} alive)\n"
        f"Total decisions logged: {total_decisions}\n\n"
        f"EVENTS:\n{events_text}\n\n"
        f"AGENTS (final state):\n{agents_text}"
    )

    # Generate report
    report = client.complete(
        prompt=context,
        system_prompt=_REPORT_SYSTEM_PROMPT,
        temperature=0.6,
        max_tokens=2000,
        simulation_id=simulation.id,
    )

    # Save to simulation
    simulation.report = report
    simulation.save(update_fields=["report"])

    logger.info("Report generated for simulation %d", simulation.id)
    return report

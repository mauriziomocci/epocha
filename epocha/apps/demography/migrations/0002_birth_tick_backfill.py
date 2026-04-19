"""Populate Agent.birth_tick from existing Agent.age for all agents.

This is a one-shot backfill run when the demography app is first added.
The formula uses the simulation's current_tick and tick_duration_hours
to convert age in years to a birth_tick value consistent with the new
canonical age source.
"""
from django.db import migrations


def backfill_birth_tick(apps, schema_editor):
    Agent = apps.get_model("agents", "Agent")
    for agent in Agent.objects.select_related("simulation__world").iterator():
        simulation = agent.simulation
        if simulation is None:
            continue
        tick_duration_hours = 24.0
        world = getattr(simulation, "world", None)
        if world is not None and getattr(world, "tick_duration_hours", None):
            tick_duration_hours = float(world.tick_duration_hours)
        ticks_per_year = 8760.0 / tick_duration_hours
        current_tick = simulation.current_tick or 0
        age_in_ticks = int(round(agent.age * ticks_per_year))
        # Negative birth_tick is valid for agents born before simulation start
        # (Agent.birth_tick is a signed BigIntegerField). The previous clamp to 0
        # silently lost generational information for every pre-existing agent.
        agent.birth_tick = current_tick - age_in_ticks
        agent.save(update_fields=["birth_tick"])


def noop_reverse(apps, schema_editor):
    """Reverse is a no-op: resetting birth_tick to NULL is handled by schema."""


class Migration(migrations.Migration):
    dependencies = [
        ("demography", "0001_initial"),
        ("agents", "0009_agent_birth_tick_agent_caretaker_agent_and_more"),
    ]
    operations = [
        migrations.RunPython(backfill_birth_tick, noop_reverse),
    ]

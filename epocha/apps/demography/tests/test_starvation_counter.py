"""Tests for the persisted starvation counter (spec FR-011, FR-012, SC-003).

`evaluate_emergency_flight` takes `consecutive_ticks_under_subsistence` as an
explicit argument because no such field existed in the schema; Plan 3 left the
obligation in writing. Without that storage the emergency-flight module is dead
code in a live run: with the default empty mapping every agent evaluates to
"does not meet preconditions" and the path never fires.

This module covers the storage itself. The step that maintains it inside the
tick, and its position in the declared order, are covered where the
orchestrator is tested.
"""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model

from epocha.apps.agents.models import Agent
from epocha.apps.simulation.models import Simulation

User = get_user_model()


@pytest.fixture
def simulation(db):
    user = User.objects.create_user(
        email="starvation@epocha.dev",
        username="starvationuser",
        password="pass1234",
    )
    return Simulation.objects.create(
        name="StarvationCounterTest",
        seed=2026,
        owner=user,
        current_tick=10,
    )


def test_new_agent_starts_at_zero(simulation):
    """A fresh agent has never been under subsistence."""
    agent = Agent.objects.create(simulation=simulation, name="Chiara", age=30)

    agent.refresh_from_db()

    assert agent.consecutive_ticks_under_subsistence == 0


def test_counter_persists_across_reload(simulation):
    """The counter has to survive the process: the tick loop is a set of
    Celery tasks and in-memory state does not outlive one of them."""
    agent = Agent.objects.create(simulation=simulation, name="Nicola", age=41)

    Agent.objects.filter(pk=agent.pk).update(consecutive_ticks_under_subsistence=3)

    assert Agent.objects.get(pk=agent.pk).consecutive_ticks_under_subsistence == 3

"""Tests for hoard-expectations link.

Verifies that agents who chose 'hoard' in the previous tick are
identified by _get_hoarding_agent_ids, which feeds is_hoarding=True
into the market pipeline.
"""
import json

import pytest

from epocha.apps.agents.models import Agent, DecisionLog
from epocha.apps.economy.engine import _get_hoarding_agent_ids
from epocha.apps.simulation.models import Simulation


@pytest.mark.django_db
class TestHoardingAgentIds:
    def test_detects_hoard_from_decision_log(self):
        sim = Simulation.objects.create(name="hoard_test", config={})
        agent = Agent.objects.create(
            simulation=sim, name="Hoarder", role="merchant",
            personality={}, wealth=100.0, mood=0.5, health=1.0,
        )
        DecisionLog.objects.create(
            simulation=sim, agent=agent, tick=5,
            input_context="test", llm_model="test",
            output_decision=json.dumps({"action": "hoard", "reason": "prices rising"}),
        )
        result = _get_hoarding_agent_ids(sim, tick=6)
        assert agent.id in result

    def test_ignores_non_hoard_actions(self):
        sim = Simulation.objects.create(name="hoard_test2", config={})
        agent = Agent.objects.create(
            simulation=sim, name="Worker", role="farmer",
            personality={}, wealth=100.0, mood=0.5, health=1.0,
        )
        DecisionLog.objects.create(
            simulation=sim, agent=agent, tick=5,
            input_context="test", llm_model="test",
            output_decision=json.dumps({"action": "work", "reason": "need money"}),
        )
        result = _get_hoarding_agent_ids(sim, tick=6)
        assert agent.id not in result

    def test_only_reads_previous_tick(self):
        sim = Simulation.objects.create(name="hoard_test3", config={})
        agent = Agent.objects.create(
            simulation=sim, name="OldHoarder", role="merchant",
            personality={}, wealth=100.0, mood=0.5, health=1.0,
        )
        DecisionLog.objects.create(
            simulation=sim, agent=agent, tick=3,
            input_context="test", llm_model="test",
            output_decision=json.dumps({"action": "hoard", "reason": "old"}),
        )
        result = _get_hoarding_agent_ids(sim, tick=6)
        assert agent.id not in result

    def test_returns_empty_set_at_tick_zero(self):
        sim = Simulation.objects.create(name="hoard_test4", config={})
        result = _get_hoarding_agent_ids(sim, tick=0)
        assert result == set()

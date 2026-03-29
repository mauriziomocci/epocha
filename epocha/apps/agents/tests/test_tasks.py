"""Tests for agent Celery tasks."""

from unittest.mock import patch

import pytest

from epocha.apps.agents.models import Agent, Memory
from epocha.apps.agents.tasks import process_agent_turn
from epocha.apps.simulation.models import Simulation
from epocha.apps.users.models import User
from epocha.apps.world.models import World, Zone


@pytest.fixture
def user(db):
    return User.objects.create_user(
        email="task@epocha.dev", username="tasktest", password="pass123"
    )


@pytest.fixture
def simulation(user):
    return Simulation.objects.create(
        name="TaskTest", seed=42, owner=user, status="running"
    )


@pytest.fixture
def world(simulation):
    w = World.objects.create(simulation=simulation)
    Zone.objects.create(world=w, name="Village", zone_type="urban")
    return w


@pytest.fixture
def agent(simulation):
    return Agent.objects.create(
        simulation=simulation,
        name="Marco",
        role="blacksmith",
        personality={
            "openness": 0.5,
            "conscientiousness": 0.5,
            "extraversion": 0.5,
            "agreeableness": 0.5,
            "neuroticism": 0.5,
            "background": "A blacksmith",
        },
    )


@pytest.mark.django_db
class TestProcessAgentTurn:
    @patch("epocha.apps.agents.decision.process_agent_decision")
    def test_processes_decision_and_applies_action(self, mock_decision, agent, world):
        """The task should call the decision pipeline and apply the resulting action."""
        mock_decision.return_value = {"action": "work", "reason": "busy"}

        result = process_agent_turn(agent.id, agent.simulation_id, 1)

        mock_decision.assert_called_once()
        assert result["action"] == "work"

    @patch("epocha.apps.agents.decision.process_agent_decision")
    def test_creates_memory(self, mock_decision, agent, world):
        """The task should create a memory from the action."""
        mock_decision.return_value = {"action": "argue", "reason": "angry at priest"}

        process_agent_turn(agent.id, agent.simulation_id, 1)

        assert Memory.objects.filter(agent=agent).exists()
        memory = Memory.objects.filter(agent=agent).first()
        assert "argue" in memory.content

    @patch("epocha.apps.agents.decision.process_agent_decision")
    def test_returns_fallback_on_failure(self, mock_decision, agent, world):
        """If the decision pipeline fails, return a fallback rest action."""
        mock_decision.side_effect = Exception("LLM timeout")

        result = process_agent_turn(agent.id, agent.simulation_id, 1)

        assert result["action"] == "rest"
        assert result["error"] is True

    @patch("epocha.apps.agents.decision.process_agent_decision")
    def test_skips_dead_agent(self, mock_decision, agent, world):
        """Dead agents should be skipped entirely."""
        agent.is_alive = False
        agent.save()

        result = process_agent_turn(agent.id, agent.simulation_id, 1)

        mock_decision.assert_not_called()
        assert result["skipped"] is True

    @patch("epocha.apps.agents.decision.process_agent_decision")
    def test_returns_event_data_for_notable_actions(self, mock_decision, agent, world):
        """Notable actions (not rest/work) should include event data in the result."""
        mock_decision.return_value = {"action": "argue", "reason": "angry"}

        result = process_agent_turn(agent.id, agent.simulation_id, 1)

        assert "event" in result
        assert result["event"]["agent"] == "Marco"

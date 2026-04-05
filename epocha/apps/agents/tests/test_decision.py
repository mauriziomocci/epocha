"""Tests for the agent decision pipeline."""
from unittest.mock import MagicMock, patch

import pytest

from epocha.apps.agents.decision import process_agent_decision
from epocha.apps.agents.models import Agent, DecisionLog, Memory
from epocha.apps.simulation.models import Simulation
from epocha.apps.users.models import User
from epocha.apps.world.models import World


@pytest.fixture
def user(db):
    return User.objects.create_user(email="dec@epocha.dev", username="dectest", password="pass123")


@pytest.fixture
def simulation(user):
    return Simulation.objects.create(name="DecTest", seed=42, owner=user)


@pytest.fixture
def world(simulation):
    return World.objects.create(simulation=simulation)


@pytest.fixture
def agent(simulation):
    return Agent.objects.create(
        simulation=simulation,
        name="Marco",
        role="blacksmith",
        personality={
            "openness": 0.8,
            "conscientiousness": 0.6,
            "extraversion": 0.4,
            "agreeableness": 0.3,
            "neuroticism": 0.5,
            "background": "A skilled blacksmith with ambitions",
        },
    )


@pytest.mark.django_db
class TestProcessAgentDecision:
    @patch("epocha.apps.agents.decision.get_llm_client")
    def test_returns_action_dict(self, mock_get_client, agent, world):
        """The pipeline should return a parsed action dictionary."""
        mock_client = MagicMock()
        mock_client.complete.return_value = '{"action": "work", "target": "forge", "reason": "Need to earn money"}'
        mock_client.get_model_name.return_value = "gpt-4o-mini"
        mock_get_client.return_value = mock_client

        result = process_agent_decision(agent, world, tick=1)

        assert isinstance(result, dict)
        assert "action" in result
        assert result["action"] == "work"

    @patch("epocha.apps.agents.decision.get_llm_client")
    def test_creates_decision_log(self, mock_get_client, agent, world):
        """Every decision must be logged for replay and debugging."""
        mock_client = MagicMock()
        mock_client.complete.return_value = '{"action": "rest", "reason": "Tired"}'
        mock_client.get_model_name.return_value = "gpt-4o-mini"
        mock_get_client.return_value = mock_client

        process_agent_decision(agent, world, tick=5)

        log = DecisionLog.objects.get(agent=agent, tick=5)
        assert log.llm_model == "gpt-4o-mini"
        assert "rest" in log.output_decision

    @patch("epocha.apps.agents.decision.get_llm_client")
    def test_handles_non_json_response_gracefully(self, mock_get_client, agent, world):
        """If the LLM returns non-JSON, the pipeline should not crash."""
        mock_client = MagicMock()
        mock_client.complete.return_value = "I think I should rest for a while."
        mock_client.get_model_name.return_value = "gpt-4o-mini"
        mock_get_client.return_value = mock_client

        result = process_agent_decision(agent, world, tick=1)

        assert isinstance(result, dict)
        assert result["action"] == "rest"  # Fallback action

    @patch("epocha.apps.agents.decision.get_llm_client")
    def test_includes_memories_in_context(self, mock_get_client, agent, world):
        """Agent memories should be included in the LLM prompt context."""
        Memory.objects.create(
            agent=agent, content="The priest insulted me yesterday",
            emotional_weight=0.7, tick_created=1,
        )
        mock_client = MagicMock()
        mock_client.complete.return_value = '{"action": "argue", "reason": "Still angry"}'
        mock_client.get_model_name.return_value = "gpt-4o-mini"
        mock_get_client.return_value = mock_client

        process_agent_decision(agent, world, tick=5)

        # Verify the memory was included in the prompt sent to the LLM
        call_args = mock_client.complete.call_args
        prompt = call_args.kwargs.get("prompt", call_args.args[0] if call_args.args else "")
        assert "priest insulted" in prompt.lower()

    @patch("epocha.apps.agents.decision.get_llm_client")
    def test_system_prompt_includes_personality(self, mock_get_client, agent, world):
        """The system prompt must contain personality traits."""
        mock_client = MagicMock()
        mock_client.complete.return_value = '{"action": "work"}'
        mock_client.get_model_name.return_value = "gpt-4o-mini"
        mock_get_client.return_value = mock_client

        process_agent_decision(agent, world, tick=1)

        call_args = mock_client.complete.call_args
        system_prompt = call_args.kwargs.get("system_prompt", "")
        assert "blacksmith" in system_prompt.lower() or "personality" in system_prompt.lower()

    @patch("epocha.apps.agents.decision.get_llm_client")
    def test_context_includes_living_agents_list(self, mock_get_client, agent, world, simulation):
        """The LLM prompt must list living agents so the agent only targets real people."""
        Agent.objects.create(
            simulation=simulation, name="Elena", role="farmer",
            personality={"openness": 0.5},
        )
        Agent.objects.create(
            simulation=simulation, name="Ghost", role="priest",
            personality={"openness": 0.5}, is_alive=False,
        )
        mock_client = MagicMock()
        mock_client.complete.return_value = '{"action": "socialize", "target": "Elena"}'
        mock_client.get_model_name.return_value = "gpt-4o-mini"
        mock_get_client.return_value = mock_client

        process_agent_decision(agent, world, tick=1)

        call_args = mock_client.complete.call_args
        prompt = call_args.kwargs.get("prompt", call_args.args[0] if call_args.args else "")
        # Living agent Elena must appear in the prompt
        assert "Elena" in prompt
        assert "farmer" in prompt
        # Dead agent Ghost must NOT appear
        assert "Ghost" not in prompt
        # The agent itself must NOT appear in its own list
        assert prompt.count("Marco") == 1  # Only the "You are Marco" line
        # Must include constraint
        assert "ONLY" in prompt

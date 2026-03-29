"""Tests for the agent biography enrichment pipeline."""

import json
from unittest.mock import MagicMock, patch

import pytest

from epocha.apps.agents.enrichment import (
    classify_historical_agents,
    enrich_agent_profile,
    enrich_simulation_agents,
)
from epocha.apps.agents.models import Agent
from epocha.apps.simulation.models import Simulation
from epocha.apps.users.models import User
from epocha.apps.world.models import World, Zone


@pytest.fixture
def user(db):
    return User.objects.create_user(
        email="enrich@epocha.dev", username="enrichtest", password="pass123"
    )


@pytest.fixture
def simulation(user):
    sim = Simulation.objects.create(name="EnrichTest", seed=42, owner=user)
    world = World.objects.create(simulation=sim)
    Zone.objects.create(world=world, name="Roma", zone_type="urban")
    return sim


@pytest.fixture
def agents(simulation):
    lucrezia = Agent.objects.create(
        simulation=simulation,
        name="Lucrezia Borgia",
        role="Duchessa",
        personality={"openness": 0.8, "background": "Figlia del Papa"},
    )
    marco = Agent.objects.create(
        simulation=simulation,
        name="Marco il Fabbro",
        role="Fabbro",
        personality={"openness": 0.5, "background": "A blacksmith"},
    )
    cesare = Agent.objects.create(
        simulation=simulation,
        name="Cesare Borgia",
        role="Condottiero",
        personality={"openness": 0.4, "background": "Figlio del Papa"},
    )
    return [lucrezia, marco, cesare]


class TestClassifyHistoricalAgents:
    @patch("epocha.apps.agents.enrichment.get_llm_client")
    def test_identifies_historical_figures(self, mock_get_client, agents):
        """The classifier should return names of historical/real figures."""
        mock_client = MagicMock()
        mock_client.complete.return_value = '["Lucrezia Borgia", "Cesare Borgia"]'
        mock_client.get_model_name.return_value = "test-model"
        mock_get_client.return_value = mock_client

        result = classify_historical_agents(agents)

        assert "Lucrezia Borgia" in result
        assert "Cesare Borgia" in result
        assert "Marco il Fabbro" not in result

    @patch("epocha.apps.agents.enrichment.get_llm_client")
    def test_returns_empty_list_on_parse_error(self, mock_get_client, agents):
        """If LLM returns invalid JSON, return empty list."""
        mock_client = MagicMock()
        mock_client.complete.return_value = "I think Lucrezia is historical"
        mock_client.get_model_name.return_value = "test-model"
        mock_get_client.return_value = mock_client

        result = classify_historical_agents(agents)

        assert result == []


@pytest.mark.django_db
class TestEnrichAgentProfile:
    @patch("epocha.apps.agents.enrichment.get_llm_client")
    def test_updates_personality_with_research(self, mock_get_client, agents):
        """enrich_agent_profile should update the agent's personality dict."""
        mock_client = MagicMock()
        mock_client.complete.return_value = json.dumps(
            {
                "openness": 0.7,
                "conscientiousness": 0.6,
                "extraversion": 0.7,
                "agreeableness": 0.3,
                "neuroticism": 0.6,
                "background": "Daughter of Pope Alexander VI",
                "ambitions": "Political independence",
                "weaknesses": "Loyalty to a corrupt family",
                "values": "Family, survival, culture",
                "fears": "Being used as a political pawn",
                "beliefs": "Power through intelligence",
            }
        )
        mock_client.get_model_name.return_value = "test-model"
        mock_get_client.return_value = mock_client

        lucrezia = agents[0]
        enrich_agent_profile(lucrezia, "Lucrezia Borgia was an Italian noblewoman...")

        lucrezia.refresh_from_db()
        assert "Pope Alexander VI" in lucrezia.personality["background"]
        assert lucrezia.personality.get("fears") is not None

    @patch("epocha.apps.agents.enrichment.get_llm_client")
    def test_preserves_agent_on_llm_failure(self, mock_get_client, agents):
        """If LLM enrichment fails, the agent should keep the original profile."""
        mock_client = MagicMock()
        mock_client.complete.side_effect = Exception("LLM error")
        mock_client.get_model_name.return_value = "test-model"
        mock_get_client.return_value = mock_client

        lucrezia = agents[0]
        original_bg = lucrezia.personality.get("background")

        enrich_agent_profile(lucrezia, "Some bio text")

        lucrezia.refresh_from_db()
        assert lucrezia.personality.get("background") == original_bg


@pytest.mark.django_db
class TestEnrichSimulationAgents:
    @patch("epocha.apps.agents.enrichment.research_person")
    @patch("epocha.apps.agents.enrichment.classify_historical_agents")
    @patch("epocha.apps.agents.enrichment.get_llm_client")
    def test_enriches_identified_historical_agents(
        self, mock_get_client, mock_classify, mock_research, simulation, agents
    ):
        """The full pipeline should research and enrich historical agents only."""
        mock_classify.return_value = ["Lucrezia Borgia"]
        mock_research.return_value = (
            "Lucrezia Borgia was a noblewoman and alleged poisoner."
        )

        mock_client = MagicMock()
        mock_client.complete.return_value = json.dumps(
            {
                "openness": 0.7,
                "conscientiousness": 0.5,
                "extraversion": 0.6,
                "agreeableness": 0.3,
                "neuroticism": 0.6,
                "background": "Italian noblewoman and alleged poisoner",
                "ambitions": "Independence",
                "values": "Family, power",
            }
        )
        mock_client.get_model_name.return_value = "test-model"
        mock_get_client.return_value = mock_client

        stats = enrich_simulation_agents(simulation)

        assert stats["researched"] == 1
        assert stats["enriched"] == 1
        mock_research.assert_called_once_with("Lucrezia Borgia", language="en")

    @patch("epocha.apps.agents.enrichment.research_person")
    @patch("epocha.apps.agents.enrichment.classify_historical_agents")
    @patch("epocha.apps.agents.enrichment.get_llm_client")
    def test_skips_agents_with_no_research_results(
        self, mock_get_client, mock_classify, mock_research, simulation, agents
    ):
        """Agents with no research results should be skipped."""
        mock_classify.return_value = ["Lucrezia Borgia"]
        mock_research.return_value = None

        mock_client = MagicMock()
        mock_client.get_model_name.return_value = "test-model"
        mock_get_client.return_value = mock_client

        stats = enrich_simulation_agents(simulation)

        assert stats["researched"] == 0
        assert stats["enriched"] == 0

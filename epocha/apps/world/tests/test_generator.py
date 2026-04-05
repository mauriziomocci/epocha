"""Tests for world generation from text prompt (Express mode)."""
import json
from unittest.mock import MagicMock, patch

import pytest

from epocha.apps.agents.models import Agent
from epocha.apps.simulation.models import Simulation
from epocha.apps.users.models import User
from epocha.apps.world.generator import generate_world_from_prompt
from epocha.apps.world.models import Government, Institution, World, Zone

MOCK_LLM_RESPONSE = json.dumps({
    "world": {
        "economy_level": "base",
        "stability_index": 0.6,
    },
    "zones": [
        {"name": "Village Center", "type": "urban", "x": 50, "y": 50, "resources": {"food": 100, "wood": 50}},
        {"name": "Farm Fields", "type": "rural", "x": 20, "y": 30, "resources": {"food": 300}},
        {"name": "Forest", "type": "wilderness", "x": 80, "y": 70, "resources": {"wood": 200, "game": 100}},
    ],
    "agents": [
        {
            "name": "Marco",
            "age": 35,
            "role": "blacksmith",
            "gender": "male",
            "personality": {
                "openness": 0.8, "conscientiousness": 0.6, "extraversion": 0.4,
                "agreeableness": 0.3, "neuroticism": 0.5, "background": "A skilled blacksmith",
            },
        },
        {
            "name": "Elena",
            "age": 28,
            "role": "farmer",
            "gender": "female",
            "personality": {
                "openness": 0.4, "conscientiousness": 0.8, "extraversion": 0.6,
                "agreeableness": 0.7, "neuroticism": 0.3, "background": "A hardworking farmer",
            },
        },
        {
            "name": "Padre Luca",
            "age": 55,
            "role": "priest",
            "gender": "male",
            "personality": {
                "openness": 0.3, "conscientiousness": 0.5, "extraversion": 0.7,
                "agreeableness": 0.6, "neuroticism": 0.4, "background": "A corrupt priest",
            },
        },
    ],
})


@pytest.fixture
def user(db):
    return User.objects.create_user(email="gen@epocha.dev", username="gentest", password="pass123")


@pytest.fixture
def simulation(user):
    return Simulation.objects.create(name="GenTest", seed=42, owner=user)


@pytest.mark.django_db
class TestGenerateWorldFromPrompt:
    @patch("epocha.apps.world.generator.get_llm_client")
    def test_creates_world_zones_and_agents(self, mock_get_client, simulation):
        """Express generation should create World, Zones, and Agents from LLM output."""
        mock_client = MagicMock()
        mock_client.complete.return_value = MOCK_LLM_RESPONSE
        mock_get_client.return_value = mock_client

        result = generate_world_from_prompt(
            prompt="A medieval village with a blacksmith, a farmer, and a corrupt priest",
            simulation=simulation,
        )

        assert World.objects.filter(simulation=simulation).exists()
        assert Zone.objects.filter(world__simulation=simulation).count() == 3
        assert Agent.objects.filter(simulation=simulation).count() == 3
        assert result["zones"] == 3
        assert result["agents"] == 3

    @patch("epocha.apps.world.generator.get_llm_client")
    def test_world_has_correct_economy_level(self, mock_get_client, simulation):
        """The generated World should reflect the LLM's economy level choice."""
        mock_client = MagicMock()
        mock_client.complete.return_value = MOCK_LLM_RESPONSE
        mock_get_client.return_value = mock_client

        generate_world_from_prompt(prompt="A village", simulation=simulation)

        world = World.objects.get(simulation=simulation)
        assert world.economy_level == "base"

    @patch("epocha.apps.world.generator.get_llm_client")
    def test_agents_have_personality(self, mock_get_client, simulation):
        """Generated agents must have personality data from the LLM."""
        mock_client = MagicMock()
        mock_client.complete.return_value = MOCK_LLM_RESPONSE
        mock_get_client.return_value = mock_client

        generate_world_from_prompt(prompt="A village", simulation=simulation)

        marco = Agent.objects.get(simulation=simulation, name="Marco")
        assert "openness" in marco.personality
        assert marco.role == "blacksmith"

    @patch("epocha.apps.world.generator.get_llm_client")
    def test_invalid_json_raises(self, mock_get_client, simulation):
        """Non-JSON LLM response should raise a clear error."""
        mock_client = MagicMock()
        mock_client.complete.return_value = "This is not JSON at all"
        mock_get_client.return_value = mock_client

        with pytest.raises(ValueError, match="invalid JSON"):
            generate_world_from_prompt(prompt="A village", simulation=simulation)

    @patch("epocha.apps.world.generator.get_llm_client")
    def test_returns_summary_dict(self, mock_get_client, simulation):
        """The result should contain world_id, zone count, and agent count."""
        mock_client = MagicMock()
        mock_client.complete.return_value = MOCK_LLM_RESPONSE
        mock_get_client.return_value = mock_client

        result = generate_world_from_prompt(prompt="A village", simulation=simulation)

        assert "world_id" in result
        assert isinstance(result["world_id"], int)
        assert "zones" in result
        assert "agents" in result

    @patch("epocha.apps.world.generator.get_llm_client")
    def test_creates_government_and_institutions(self, mock_get_client, simulation):
        """World generation must create a default Government and all 7 Institutions."""
        mock_client = MagicMock()
        mock_client.complete.return_value = MOCK_LLM_RESPONSE
        mock_get_client.return_value = mock_client

        generate_world_from_prompt(prompt="A village", simulation=simulation)

        assert Government.objects.filter(simulation=simulation).exists()
        government = Government.objects.get(simulation=simulation)
        assert government.government_type == "democracy"
        assert government.formed_at_tick == 0

        assert Institution.objects.filter(simulation=simulation).count() == 7
        institution_types = set(
            Institution.objects.filter(simulation=simulation).values_list("institution_type", flat=True)
        )
        assert institution_types == set(Institution.InstitutionType.values)

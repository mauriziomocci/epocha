"""Integration test: full MVP flow from Express creation to running ticks."""
import json
from unittest.mock import MagicMock, patch

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from epocha.apps.agents.models import Agent, DecisionLog, Memory
from epocha.apps.simulation.models import Simulation
from epocha.apps.users.models import User
from epocha.apps.world.models import World, Zone

MOCK_WORLD_RESPONSE = json.dumps({
    "world": {"economy_level": "base", "stability_index": 0.7},
    "zones": [
        {"name": "Village", "type": "urban", "x": 50, "y": 50, "resources": {"food": 200}},
    ],
    "agents": [
        {
            "name": "Marco", "age": 30, "role": "blacksmith", "gender": "male",
            "personality": {
                "openness": 0.8, "conscientiousness": 0.6, "extraversion": 0.4,
                "agreeableness": 0.3, "neuroticism": 0.5, "background": "A blacksmith",
            },
        },
        {
            "name": "Elena", "age": 25, "role": "farmer", "gender": "female",
            "personality": {
                "openness": 0.4, "conscientiousness": 0.8, "extraversion": 0.6,
                "agreeableness": 0.7, "neuroticism": 0.3, "background": "A farmer",
            },
        },
    ],
})


@pytest.fixture
def user(db):
    return User.objects.create_user(email="integ@epocha.dev", username="integtest", password="pass123")


@pytest.fixture
def authenticated_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.mark.django_db
class TestFullMVPFlow:
    @patch("epocha.apps.world.generator.get_llm_client")
    def test_express_create_and_run(self, mock_get_client, authenticated_client):
        """Full flow: Express create -> world generated -> run ticks -> agents have memories."""
        # Mock LLM for world generation
        mock_client = MagicMock()
        mock_client.complete.return_value = MOCK_WORLD_RESPONSE
        mock_client.get_model_name.return_value = "gpt-4o-mini"
        mock_get_client.return_value = mock_client

        # 1. Create simulation via Express
        response = authenticated_client.post("/api/v1/simulations/express/", {
            "prompt": "A medieval village with a blacksmith and a farmer",
        }, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        sim_id = response.data["simulation_id"]

        # 2. Verify world was created
        sim = Simulation.objects.get(id=sim_id)
        assert World.objects.filter(simulation=sim).exists()
        assert Agent.objects.filter(simulation=sim).count() == 2
        assert Zone.objects.filter(world__simulation=sim).count() == 1

        # 3. Run a tick manually (mocking agent decisions)
        mock_client.complete.return_value = '{"action": "work", "target": "forge", "reason": "Need to earn money"}'

        from epocha.apps.simulation.engine import SimulationEngine

        with patch("epocha.apps.agents.decision.get_llm_client", return_value=mock_client):
            engine = SimulationEngine(sim)
            engine.run_tick()

        # 4. Verify tick advanced
        sim.refresh_from_db()
        assert sim.current_tick == 1

        # 5. Verify agents have decision logs and memories
        assert DecisionLog.objects.filter(simulation=sim).count() == 2
        assert Memory.objects.filter(agent__simulation=sim).count() == 2

    @patch("epocha.apps.world.generator.get_llm_client")
    def test_multiple_ticks_produce_history(self, mock_get_client, authenticated_client):
        """Running multiple ticks should produce a growing history of decisions."""
        mock_client = MagicMock()
        mock_client.complete.return_value = MOCK_WORLD_RESPONSE
        mock_client.get_model_name.return_value = "gpt-4o-mini"
        mock_get_client.return_value = mock_client

        # Create world
        response = authenticated_client.post("/api/v1/simulations/express/", {
            "prompt": "A village",
        }, format="json")
        sim = Simulation.objects.get(id=response.data["simulation_id"])

        # Run 3 ticks
        mock_client.complete.return_value = '{"action": "socialize", "reason": "feeling social"}'
        from epocha.apps.simulation.engine import SimulationEngine

        with patch("epocha.apps.agents.decision.get_llm_client", return_value=mock_client):
            engine = SimulationEngine(sim)
            for _ in range(3):
                engine.run_tick()

        sim.refresh_from_db()
        assert sim.current_tick == 3
        # 2 agents * 3 ticks = 6 decision logs
        assert DecisionLog.objects.filter(simulation=sim).count() == 6
        # 2 agents * 3 ticks = 6 memories
        assert Memory.objects.filter(agent__simulation=sim).count() == 6

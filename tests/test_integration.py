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

MOCK_WORLD_RESPONSE = json.dumps(
    {
        "world": {"economy_level": "base", "stability_index": 0.7},
        "zones": [
            {"name": "Village", "type": "urban", "x": 50, "y": 50, "resources": {"food": 200}},
        ],
        "agents": [
            {
                "name": "Marco",
                "age": 30,
                "role": "blacksmith",
                "gender": "male",
                "personality": {
                    "openness": 0.8,
                    "conscientiousness": 0.6,
                    "extraversion": 0.4,
                    "agreeableness": 0.3,
                    "neuroticism": 0.5,
                    "background": "A blacksmith",
                },
            },
            {
                "name": "Elena",
                "age": 25,
                "role": "farmer",
                "gender": "female",
                "personality": {
                    "openness": 0.4,
                    "conscientiousness": 0.8,
                    "extraversion": 0.6,
                    "agreeableness": 0.7,
                    "neuroticism": 0.3,
                    "background": "A farmer",
                },
            },
        ],
    }
)


@pytest.fixture
def user(db):
    return User.objects.create_user(
        email="integ@epocha.dev", username="integtest", password="pass123"
    )


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
        response = authenticated_client.post(
            "/api/v1/simulations/express/",
            {
                "prompt": "A medieval village with a blacksmith and a farmer",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED
        sim_id = response.data["simulation_id"]

        # 2. Verify world was created
        sim = Simulation.objects.get(id=sim_id)
        assert World.objects.filter(simulation=sim).exists()
        assert Agent.objects.filter(simulation=sim).count() == 2
        assert Zone.objects.filter(world__simulation=sim).count() == 1

        # 3. Run a tick manually (mocking agent decisions)
        mock_client.complete.return_value = (
            '{"action": "work", "target": "forge", "reason": "Need to earn money"}'
        )

        from epocha.apps.simulation.engine import SimulationEngine

        with patch("epocha.apps.agents.decision.get_llm_client", return_value=mock_client):
            engine = SimulationEngine(sim)
            engine.run_tick()

        # 4. Verify tick advanced
        sim.refresh_from_db()
        assert sim.current_tick == 1

        # 5. Verify agents have decision logs and memories
        assert DecisionLog.objects.filter(simulation=sim).count() == 2
        # Count only decision memories; political cycle may create stratification memories too.
        assert (
            Memory.objects.filter(agent__simulation=sim, content__startswith="I decided to").count()
            == 2
        )

    @patch("epocha.apps.world.generator.get_llm_client")
    def test_multiple_ticks_produce_history(self, mock_get_client, authenticated_client):
        """Running multiple ticks should produce a growing history of decisions."""
        mock_client = MagicMock()
        mock_client.complete.return_value = MOCK_WORLD_RESPONSE
        mock_client.get_model_name.return_value = "gpt-4o-mini"
        mock_get_client.return_value = mock_client

        # Create world
        response = authenticated_client.post(
            "/api/v1/simulations/express/",
            {
                "prompt": "A village",
            },
            format="json",
        )
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
        # Dedup is active: a decision memory is suppressed when the agent's
        # MOST RECENT memory inside the window already records the same
        # action (engine.py, `recent_duplicate`). Three ticks of "socialize"
        # therefore collapse to fewer than one memory per tick per agent.
        decision_memories = Memory.objects.filter(
            agent__simulation=sim, content__startswith="I decided to"
        )
        assert decision_memories.count() < 6, "dedup suppressed nothing"

        # The exact surviving count is NOT 2 in general, and asserting it was
        # a latent flake this branch tripped: `world/generator.py:172` places
        # agents with the UNSEEDED GLOBAL `random`, so agent positions -- and
        # through the economy, the wealth ORDER -- depend on how much
        # randomness the rest of the suite consumed first. When the order
        # flips, `update_social_classes` writes a mobility memory that
        # legitimately interrupts an agent's streak and a further decision
        # memory is correctly created. Merely adding a test file elsewhere in
        # the suite was enough to flip it. What dedup actually guarantees,
        # and what survives any placement, is that no agent ever holds two
        # ADJACENT memories recording the same action.
        for agent in Agent.objects.filter(simulation=sim):
            contents = list(
                Memory.objects.filter(agent=agent)
                .order_by("tick_created", "id")
                .values_list("content", flat=True)
            )
            for earlier, later in zip(contents, contents[1:]):
                if not later.startswith("I decided to"):
                    continue
                prefix = later.split(".")[0] + "."
                assert not earlier.startswith(prefix), (
                    f"{agent.name} holds adjacent duplicate memories of "
                    f"{prefix!r}: dedup did not fire"
                )

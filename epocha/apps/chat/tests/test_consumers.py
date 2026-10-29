"""Tests for the chat WebSocket consumer."""

from unittest.mock import MagicMock, patch

import pytest
from channels.routing import URLRouter
from channels.testing import WebsocketCommunicator

from epocha.apps.agents.models import Agent
from epocha.apps.chat.routing import websocket_urlpatterns
from epocha.apps.simulation.models import Simulation
from epocha.apps.users.models import User


@pytest.fixture
def user(db):
    return User.objects.create_user(
        email="chat@epocha.dev", username="chattest", password="pass123"
    )


@pytest.fixture
def simulation(user):
    return Simulation.objects.create(name="ChatTest", seed=42, owner=user)


@pytest.fixture
def agent(simulation):
    return Agent.objects.create(
        simulation=simulation,
        name="Marco",
        role="blacksmith",
        personality={"openness": 0.8, "background": "A skilled blacksmith"},
    )


def _make_communicator(agent_id):
    """Create a WebsocketCommunicator with proper URL routing."""
    application = URLRouter(websocket_urlpatterns)
    return WebsocketCommunicator(application, f"/ws/chat/{agent_id}/")


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
class TestChatConsumer:
    @patch("epocha.apps.llm_adapter.client.get_chat_llm_client")
    async def test_connect_and_receive_response(self, mock_get_client, agent):
        """User sends a message, receives an in-character agent response.

        The consumer calls `get_chat_llm_client`, so that is the factory to
        patch. Round 16 of the Plan 4 phase-6 gate found this test patching
        `get_llm_client` instead: the chat factory then built the real chat
        provider and sent a paid request on every suite run. A real provider
        writes an `LLMRequest` row for every call, failed ones included, so
        an empty table proves that none was reached.
        """
        from asgiref.sync import sync_to_async

        from epocha.apps.llm_adapter.models import LLMRequest

        mock_client = MagicMock()
        mock_client.complete.return_value = "Aye, I am Marco the blacksmith."
        mock_get_client.return_value = mock_client

        communicator = _make_communicator(agent.id)
        connected, _ = await communicator.connect()
        assert connected

        await communicator.send_json_to({"message": "Hello blacksmith!"})
        response = await communicator.receive_json_from(timeout=10)

        assert response["role"] == "agent"
        assert response["content"] == "Aye, I am Marco the blacksmith."
        assert await sync_to_async(LLMRequest.objects.count)() == 0

        await communicator.disconnect()

    async def test_empty_message_returns_system_message(self, agent):
        """Empty messages should be handled gracefully."""
        communicator = _make_communicator(agent.id)
        connected, _ = await communicator.connect()
        assert connected

        await communicator.send_json_to({"message": ""})
        response = await communicator.receive_json_from(timeout=5)

        assert response["role"] == "system"

        await communicator.disconnect()


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_the_websocket_prompt_states_the_agents_age(simulation):
    """The third chat channel says the same thing about the speaker as the
    private and the group chat of the dashboard: who the agent is and how
    old, from demography's canonical age (`birth_tick`), never the frozen
    `Agent.age` column. Round 12 of the phase-6 gate found this channel
    still opening with name and role only, so a newborn answered like an
    adult here."""
    from asgiref.sync import sync_to_async

    from epocha.apps.world.models import World

    await sync_to_async(World.objects.create)(simulation=simulation)
    simulation.current_tick = 5000
    await sync_to_async(simulation.save)(update_fields=["current_tick"])
    infant = await sync_to_async(Agent.objects.create)(
        simulation=simulation,
        name="Pietro",
        role="child",
        age=30,
        birth_tick=5000 - 330,
        personality={},
    )
    llm = MagicMock()
    llm.complete.return_value = "..."

    with patch("epocha.apps.llm_adapter.client.get_chat_llm_client", return_value=llm):
        communicator = _make_communicator(infant.id)
        connected, _ = await communicator.connect()
        assert connected
        await communicator.send_json_to({"message": "Hello"})
        await communicator.receive_json_from(timeout=10)
        await communicator.disconnect()

    system_prompt = llm.complete.call_args.kwargs["system_prompt"]
    assert "You are Pietro, a child, 10 months old." in system_prompt
    assert "as a person of that age would" in system_prompt

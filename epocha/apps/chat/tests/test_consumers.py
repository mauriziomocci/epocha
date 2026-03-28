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
    return User.objects.create_user(email="chat@epocha.dev", username="chattest", password="pass123")


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
    @patch("epocha.apps.llm_adapter.client.get_llm_client")
    async def test_connect_and_receive_response(self, mock_get_client, agent):
        """User sends a message, receives an in-character agent response."""
        mock_client = MagicMock()
        mock_client.complete.return_value = "Aye, I am Marco the blacksmith."
        mock_get_client.return_value = mock_client

        communicator = _make_communicator(agent.id)
        connected, _ = await communicator.connect()
        assert connected

        await communicator.send_json_to({"message": "Hello blacksmith!"})
        response = await communicator.receive_json_from(timeout=10)

        assert response["role"] == "agent"
        assert len(response["content"]) > 0

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

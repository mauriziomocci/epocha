"""The private chat re-reads its own recent replies whole.

The local model runs in an 8,192-token context. A reply cut to 50 characters
made it lose what it had just said, so it repeated itself; the history now
carries 9 prior messages of up to 600 characters each (about 1,500 tokens).
These tests pin the three numbers through the system prompt the model sees,
on both endpoints that send a message: the chat page's own POST and the JSON
endpoint of the dashboard panel. Round 15 of the Plan 4 phase-6 gate found the
two carrying a copy each of the reply path, so the limits held on the page
only because the copy happened to match.
"""

from __future__ import annotations

import json
from datetime import timedelta
from unittest.mock import MagicMock, patch

import pytest
from django.contrib.gis.geos import Point
from django.test import Client
from django.utils import timezone

from epocha.apps.agents.models import Agent
from epocha.apps.chat.models import ChatMessage, ChatSession
from epocha.apps.simulation.models import Simulation
from epocha.apps.users.models import User
from epocha.apps.world.models import World

# The chat page answers its POST only when it comes from its own script.
SEND_ENDPOINTS = {
    "send-api": ("/simulations/{sim}/chat/{agent}/send/", {}),
    "chat-page": ("/simulations/{sim}/chat/{agent}/", {"HTTP_X_REQUESTED_WITH": "XMLHttpRequest"}),
}


@pytest.fixture(params=sorted(SEND_ENDPOINTS))
def chat(request, db):
    """A logged-in owner, one agent and its chat session, on each endpoint."""
    user = User.objects.create_user(email="hist@epocha.dev", username="histuser", password="pw1234")
    simulation = Simulation.objects.create(name="ChatHistory", seed=1, owner=user, current_tick=10)
    World.objects.create(simulation=simulation)
    agent = Agent.objects.create(
        simulation=simulation, name="Anselmo", role="farmer", location=Point(1, 1), age=30
    )
    session = ChatSession.objects.create(simulation=simulation, user=user, agent=agent)
    client = Client()
    client.force_login(user)
    return SimpleChat(client, simulation, agent, session, SEND_ENDPOINTS[request.param])


class SimpleChat:
    def __init__(self, client, simulation, agent, session, endpoint):
        self.client = client
        self.simulation = simulation
        self.agent = agent
        self.session = session
        self.endpoint = endpoint

    def add_prior(self, role, content, minutes_ago):
        message = ChatMessage.objects.create(
            session=self.session, role=role, content=content, tick_at=1
        )
        ChatMessage.objects.filter(pk=message.pk).update(
            created_at=timezone.now() - timedelta(minutes=minutes_ago)
        )

    def system_prompt_after_sending(self, text="Hello"):
        llm = MagicMock()
        llm.complete.return_value = "ok"
        llm.get_provider_info.return_value = "fake"
        with patch("epocha.apps.llm_adapter.client.get_chat_llm_client", return_value=llm):
            path, headers = self.endpoint
            response = self.client.post(
                path.format(sim=self.simulation.id, agent=self.agent.id),
                data=json.dumps({"message": text}),
                content_type="application/json",
                **headers,
            )
        assert response.status_code == 200
        return llm.complete.call_args.kwargs["system_prompt"]


def test_an_agent_reply_of_500_characters_reaches_the_prompt_whole(chat):
    reply = "a" * 500
    chat.add_prior("agent", reply, minutes_ago=5)

    system_prompt = chat.system_prompt_after_sending()

    assert f"You said: {reply}" in system_prompt
    assert f"You said: {reply}..." not in system_prompt


def test_an_agent_reply_of_700_characters_is_cut_at_600_with_ellipsis(chat):
    chat.add_prior("agent", "b" * 700, minutes_ago=5)

    system_prompt = chat.system_prompt_after_sending()

    assert f"You said: {'b' * 600}..." in system_prompt
    assert "b" * 601 not in system_prompt


def test_a_user_message_of_700_characters_is_cut_at_600_with_ellipsis(chat):
    chat.add_prior("user", "c" * 700, minutes_ago=5)

    system_prompt = chat.system_prompt_after_sending()

    assert f"Visitor: {'c' * 600}..." in system_prompt
    assert "c" * 601 not in system_prompt


def test_the_history_holds_the_nine_most_recent_prior_messages(chat):
    for index in range(1, 13):
        chat.add_prior("user", f"MARKER-{index:02d}", minutes_ago=100 - index)

    system_prompt = chat.system_prompt_after_sending(text="CURRENT-ONE")

    for index in range(4, 13):
        assert f"MARKER-{index:02d}" in system_prompt
    for index in range(1, 4):
        assert f"MARKER-{index:02d}" not in system_prompt


@pytest.mark.parametrize(
    ("upload", "in_prompt"),
    [
        (("map.png", b"\x89PNG"), "The visitor shows you an image: map.png"),
        (("letter.txt", b"Meet me at the mill."), "Its content is:]\nMeet me at the mill."),
    ],
)
def test_the_chat_page_hands_an_attachment_to_the_model(db, upload, in_prompt):
    """The one thing the chat page does that the JSON endpoint does not: an
    attachment, even with no text, reaches the prompt and is recorded on the
    visitor's message. A document is read from a temporary file, which is
    removed afterwards."""
    from django.core.files.uploadedfile import SimpleUploadedFile

    user = User.objects.create_user(email="att@epocha.dev", username="attuser", password="pw1234")
    simulation = Simulation.objects.create(name="ChatAttach", seed=1, owner=user, current_tick=3)
    World.objects.create(simulation=simulation)
    agent = Agent.objects.create(
        simulation=simulation, name="Brunilde", role="farmer", location=Point(1, 1), age=30
    )
    client = Client()
    client.force_login(user)
    llm = MagicMock()
    llm.complete.return_value = "ok"
    llm.get_provider_info.return_value = "fake"

    with patch("epocha.apps.llm_adapter.client.get_chat_llm_client", return_value=llm):
        response = client.post(
            f"/simulations/{simulation.id}/chat/{agent.id}/",
            data={"message": "", "file": SimpleUploadedFile(*upload)},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

    assert response.status_code == 200
    assert response.json()["role"] == "agent"
    assert in_prompt in llm.complete.call_args.kwargs["prompt"]
    visitor = ChatMessage.objects.get(session__agent=agent, role="user")
    assert visitor.content == f" [Attached: {upload[0]}]"

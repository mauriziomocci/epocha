"""WebSocket consumer for real-time chat with simulation agents.

The user sends a message, the consumer retrieves the agent's personality
and memories, calls the LLM to generate an in-character response, and
sends it back via WebSocket.

This runs synchronously via database_sync_to_async since the LLM call
and DB access are blocking operations.
"""
from __future__ import annotations

import json
import logging

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

logger = logging.getLogger(__name__)


class ChatConsumer(AsyncWebsocketConsumer):
    """WebSocket handler for 1-on-1 chat with an agent."""

    async def connect(self):
        self.agent_id = self.scope["url_route"]["kwargs"]["agent_id"]
        await self.accept()

    async def disconnect(self, close_code):
        pass

    async def receive(self, text_data):
        """Receive user message and respond in character as the agent."""
        data = json.loads(text_data)
        user_message = data.get("message", "")

        if not user_message.strip():
            await self.send(text_data=json.dumps({
                "role": "system",
                "content": "Empty message received.",
            }))
            return

        response_content = await self._generate_response(user_message)

        await self.send(text_data=json.dumps({
            "role": "agent",
            "content": response_content,
        }))

    @database_sync_to_async
    def _generate_response(self, user_message: str) -> str:
        """Generate an in-character agent response via LLM.

        Retrieves the agent's personality, recent memories, and simulation
        context, then calls the LLM to produce a response consistent with
        the agent's character.
        """
        from epocha.apps.agents.memory import get_relevant_memories
        from epocha.apps.agents.models import Agent
        from epocha.apps.agents.personality import build_personality_prompt
        from epocha.apps.llm_adapter.client import get_llm_client

        try:
            agent = Agent.objects.select_related("simulation").get(id=self.agent_id)
        except Agent.DoesNotExist:
            return "Agent not found."

        client = get_llm_client()

        # Build personality context
        personality_prompt = build_personality_prompt(agent.personality)

        # Gather recent memories
        memories = get_relevant_memories(agent, current_tick=agent.simulation.current_tick)
        memory_text = ""
        if memories:
            memory_text = "\n\nYour recent memories:\n" + "\n".join(
                f"- {m.content}" for m in memories[:5]
            )

        system_prompt = (
            f"{personality_prompt}\n\n"
            f"You are {agent.name}, a {agent.role}. "
            f"Someone is talking to you. Respond in character, "
            f"consistently with your personality and memories."
            f"{memory_text}"
        )

        return client.complete(
            prompt=user_message,
            system_prompt=system_prompt,
            temperature=0.8,
            max_tokens=300,
        )

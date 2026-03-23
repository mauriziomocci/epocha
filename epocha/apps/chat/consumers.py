"""WebSocket consumer for chatting with agents."""
import json

from channels.generic.websocket import AsyncWebsocketConsumer


class ChatConsumer(AsyncWebsocketConsumer):
    """Handles real-time chat between user and agent."""

    async def connect(self):
        self.agent_id = self.scope["url_route"]["kwargs"]["agent_id"]
        await self.accept()

    async def disconnect(self, close_code):
        pass

    async def receive(self, text_data):
        """Receives message from user, generates agent response via LLM."""
        data = json.loads(text_data)
        user_message = data.get("message", "")

        # TODO: generate agent response via Celery task
        await self.send(text_data=json.dumps({
            "role": "agent",
            "content": f"[TODO] Agent {self.agent_id} response to: {user_message}",
        }))

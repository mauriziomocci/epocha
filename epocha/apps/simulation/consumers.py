"""WebSocket consumer: stream simulation state in real time."""
import json

from channels.generic.websocket import AsyncWebsocketConsumer


class SimulationConsumer(AsyncWebsocketConsumer):
    """Sends real-time updates on the simulation state."""

    async def connect(self):
        self.simulation_id = self.scope["url_route"]["kwargs"]["simulation_id"]
        self.group_name = f"simulation_{self.simulation_id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def simulation_update(self, event):
        """Receives update from the Simulation Engine and sends it to the client."""
        await self.send(text_data=json.dumps(event["data"]))

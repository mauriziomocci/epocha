"""WebSocket URL patterns for the simulation."""
from django.urls import re_path

from . import consumers

websocket_urlpatterns = [
    re_path(r"ws/simulation/(?P<simulation_id>\d+)/$", consumers.SimulationConsumer.as_asgi()),
]

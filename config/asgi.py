"""ASGI entry point — combines Django HTTP + Channels WebSocket."""
import os

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")

django_asgi_app = get_asgi_application()

from epocha.apps.chat.routing import websocket_urlpatterns as chat_ws  # noqa: E402
from epocha.apps.simulation.routing import websocket_urlpatterns as sim_ws  # noqa: E402

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": AuthMiddlewareStack(
            URLRouter(sim_ws + chat_ws),
        ),
    }
)

"""URL root: aggregates routes from all apps."""
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    # Dashboard (web UI)
    path("", include("epocha.apps.dashboard.urls")),
    # Admin
    path("admin/", admin.site.urls),
    # API v1
    path("api/v1/users/", include("epocha.apps.users.urls")),
    path("api/v1/simulations/", include("epocha.apps.simulation.urls")),
    path("api/v1/agents/", include("epocha.apps.agents.urls")),
    path("api/v1/worlds/", include("epocha.apps.world.urls")),
    path("api/v1/chat/", include("epocha.apps.chat.urls")),
    path("api/v1/knowledge/", include("epocha.apps.knowledge.urls")),
]

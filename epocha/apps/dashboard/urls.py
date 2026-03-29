"""Dashboard URL configuration."""
from django.urls import path

from . import views

app_name = "dashboard"

urlpatterns = [
    # Auth
    path("register/", views.register_view, name="register"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),

    # Settings
    path("set-language/", views.set_language_view, name="set-language"),

    # Simulations
    path("", views.simulation_list_view, name="home"),
    path("simulations/create/", views.simulation_create_view, name="simulation-create"),
    path("simulations/<int:sim_id>/", views.simulation_detail_view, name="simulation-detail"),
    path("simulations/<int:sim_id>/feed/", views.simulation_feed_api, name="simulation-feed"),
    path("simulations/<int:sim_id>/play/", views.simulation_play_view, name="simulation-play"),
    path("simulations/<int:sim_id>/pause/", views.simulation_pause_view, name="simulation-pause"),
    path("simulations/<int:sim_id>/report/", views.simulation_report_view, name="simulation-report"),
    path("simulations/<int:sim_id>/inject/", views.inject_event_view, name="inject-event"),
    path("simulations/<int:sim_id>/chat/<int:agent_id>/", views.chat_view, name="chat"),
    path("simulations/<int:sim_id>/group-chat/", views.group_chat_view, name="group-chat"),
]

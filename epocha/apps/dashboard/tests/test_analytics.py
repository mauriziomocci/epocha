"""Tests for the analytics data endpoint."""
import pytest
from django.test import Client

from epocha.apps.simulation.models import Event, Simulation, SimulationSnapshot
from epocha.apps.users.models import User
from epocha.apps.world.models import GovernmentHistory, World


@pytest.fixture
def user(db):
    return User.objects.create_user(email="anal@epocha.dev", username="analtest", password="pass123")

@pytest.fixture
def logged_in_client(user):
    client = Client()
    client.login(email="anal@epocha.dev", password="pass123")
    return client

@pytest.fixture
def simulation(user):
    return Simulation.objects.create(name="AnalTest", seed=42, owner=user)

@pytest.fixture
def world(simulation):
    return World.objects.create(simulation=simulation)

@pytest.fixture
def snapshots(simulation):
    return [
        SimulationSnapshot.objects.create(
            simulation=simulation, tick=i,
            gini_coefficient=0.3 + i * 0.01,
            government_stability=0.6, avg_mood=0.5, avg_wealth=50.0,
            population_alive=20, population_dead=0,
            faction_count=2, government_type="democracy",
        )
        for i in range(1, 6)
    ]


@pytest.mark.django_db
class TestAnalyticsDataEndpoint:
    def test_returns_snapshots(self, logged_in_client, simulation, world, snapshots):
        response = logged_in_client.get(f"/simulations/{simulation.id}/analytics/data/")
        assert response.status_code == 200
        data = response.json()
        assert len(data["snapshots"]) == 5

    def test_returns_crises(self, logged_in_client, simulation, world, snapshots):
        Event.objects.create(
            simulation=simulation, tick=3, event_type="political",
            title="[EPOCHAL CRISIS] Inequality Crisis",
            description="Test crisis", severity=0.7,
        )
        response = logged_in_client.get(f"/simulations/{simulation.id}/analytics/data/")
        data = response.json()
        assert len(data["crises"]) == 1
        assert data["crises"][0]["label"] == "Inequality Crisis"

    def test_returns_transitions(self, logged_in_client, simulation, world, snapshots):
        GovernmentHistory.objects.create(
            simulation=simulation, government_type="democracy",
            from_tick=0, to_tick=10, transition_cause="transition",
        )
        GovernmentHistory.objects.create(
            simulation=simulation, government_type="illiberal_democracy",
            from_tick=10, transition_cause="transition",
        )
        response = logged_in_client.get(f"/simulations/{simulation.id}/analytics/data/")
        data = response.json()
        assert len(data["transitions"]) >= 1

    def test_requires_authentication(self, simulation, world, snapshots):
        client = Client()
        response = client.get(f"/simulations/{simulation.id}/analytics/data/")
        assert response.status_code in (302, 403)

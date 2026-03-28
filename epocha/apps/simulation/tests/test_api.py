"""Tests for the simulation REST API and Express endpoint."""
from unittest.mock import patch

import pytest
from rest_framework import status

from epocha.apps.simulation.models import Simulation
from epocha.apps.users.models import User


@pytest.fixture
def user(db):
    return User.objects.create_user(email="api@epocha.dev", username="apitest", password="pass123")


@pytest.fixture
def api_client():
    from rest_framework.test import APIClient

    return APIClient()


@pytest.fixture
def authenticated_client(api_client, user):
    api_client.force_authenticate(user=user)
    return api_client


@pytest.mark.django_db
class TestSimulationCRUD:
    def test_create_simulation(self, authenticated_client):
        """Creating a simulation should return 201 with the simulation data."""
        response = authenticated_client.post("/api/v1/simulations/", {
            "name": "Test Sim",
            "seed": 42,
            "config": {},
        }, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["name"] == "Test Sim"
        assert response.data["status"] == "created"

    def test_list_simulations(self, authenticated_client):
        """Users should see only their own simulations."""
        authenticated_client.post("/api/v1/simulations/", {
            "name": "Sim1", "seed": 1, "config": {},
        }, format="json")
        response = authenticated_client.get("/api/v1/simulations/")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 1

    def test_other_user_cannot_see_simulations(self, authenticated_client, api_client):
        """Simulations are private to their owner."""
        authenticated_client.post("/api/v1/simulations/", {
            "name": "Private", "seed": 1, "config": {},
        }, format="json")

        other_user = User.objects.create_user(
            email="other@epocha.dev", username="other", password="pass123",
        )
        api_client.force_authenticate(user=other_user)
        response = api_client.get("/api/v1/simulations/")
        assert len(response.data["results"]) == 0

    def test_unauthenticated_request_rejected(self, api_client):
        """Unauthenticated requests should return 401."""
        response = api_client.get("/api/v1/simulations/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestExpressEndpoint:
    @patch("epocha.apps.simulation.views.generate_world_from_prompt")
    def test_express_creates_simulation(self, mock_gen, authenticated_client):
        """Express endpoint should create a simulation and generate a world."""
        mock_gen.return_value = {"world_id": 1, "zones": 3, "agents": 10}

        response = authenticated_client.post("/api/v1/simulations/express/", {
            "prompt": "A medieval village with 20 people",
        }, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert "simulation_id" in response.data
        assert response.data["status"] == "ready"

    @patch("epocha.apps.simulation.views.generate_world_from_prompt")
    def test_express_sets_description_from_prompt(self, mock_gen, authenticated_client):
        """The simulation description should contain the user's prompt."""
        mock_gen.return_value = {"world_id": 1, "zones": 3, "agents": 10}

        authenticated_client.post("/api/v1/simulations/express/", {
            "prompt": "Ancient Rome under Trajan",
        }, format="json")

        sim = Simulation.objects.first()
        assert "Ancient Rome" in sim.description

    @patch("epocha.apps.simulation.views.generate_world_from_prompt")
    def test_express_without_prompt_returns_400(self, mock_gen, authenticated_client):
        """Express endpoint must require a prompt."""
        response = authenticated_client.post("/api/v1/simulations/express/", {}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @patch("epocha.apps.simulation.views.generate_world_from_prompt")
    def test_express_handles_generation_error(self, mock_gen, authenticated_client):
        """If world generation fails, the simulation should be marked as error."""
        mock_gen.side_effect = ValueError("LLM returned invalid JSON")

        response = authenticated_client.post("/api/v1/simulations/express/", {
            "prompt": "A broken world",
        }, format="json")

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        sim = Simulation.objects.first()
        assert sim.status == "error"

"""Tests for the social graph data endpoints."""
import pytest
from django.test import Client

from epocha.apps.agents.models import Agent, Group, Memory, Relationship
from epocha.apps.simulation.models import Simulation
from epocha.apps.users.models import User
from epocha.apps.world.models import Government, World


@pytest.fixture
def user(db):
    return User.objects.create_user(email="graph@epocha.dev", username="graphtest", password="pass123")


@pytest.fixture
def logged_in_client(user):
    client = Client()
    client.login(email="graph@epocha.dev", password="pass123")
    return client


@pytest.fixture
def simulation(user):
    return Simulation.objects.create(name="GraphTest", seed=42, owner=user)


@pytest.fixture
def world(simulation):
    return World.objects.create(simulation=simulation)


@pytest.fixture
def setup_graph_data(simulation):
    faction = Group.objects.create(
        simulation=simulation,
        name="The Guild",
        objective="Protect",
        cohesion=0.7,
        formed_at_tick=1,
    )
    marco = Agent.objects.create(
        simulation=simulation,
        name="Marco",
        role="blacksmith",
        charisma=0.8,
        mood=0.6,
        social_class="middle",
        group=faction,
        personality={"openness": 0.5},
    )
    elena = Agent.objects.create(
        simulation=simulation,
        name="Elena",
        role="farmer",
        charisma=0.5,
        mood=0.4,
        social_class="working",
        group=faction,
        personality={"openness": 0.5},
    )
    faction.leader = marco
    faction.save(update_fields=["leader"])
    Relationship.objects.create(
        agent_from=marco,
        agent_to=elena,
        relation_type="friendship",
        strength=0.7,
        sentiment=0.5,
        since_tick=0,
    )
    government = Government.objects.create(
        simulation=simulation,
        government_type="democracy",
        head_of_state=marco,
        ruling_faction=faction,
        stability=0.6,
    )
    return marco, elena, faction, government


class TestGraphDataEndpoint:
    """Tests for the /simulations/<id>/graph/data/ endpoint."""

    def test_returns_nodes_and_edges(self, logged_in_client, simulation, setup_graph_data):
        response = logged_in_client.get(f"/simulations/{simulation.id}/graph/data/")
        assert response.status_code == 200
        data = response.json()
        assert len(data["nodes"]) == 2
        assert len(data["edges"]) == 1
        assert data["government"]["type"] == "democracy"

    def test_nodes_have_required_fields(self, logged_in_client, simulation, setup_graph_data):
        response = logged_in_client.get(f"/simulations/{simulation.id}/graph/data/")
        assert response.status_code == 200
        data = response.json()
        required = {"id", "label", "role", "faction", "faction_color", "is_leader", "is_head_of_state",
                    "charisma", "mood", "social_class", "is_alive"}
        for node in data["nodes"]:
            assert required <= set(node.keys()), f"Node {node.get('label')} missing fields"

    def test_edges_have_required_fields(self, logged_in_client, simulation, setup_graph_data):
        response = logged_in_client.get(f"/simulations/{simulation.id}/graph/data/")
        assert response.status_code == 200
        data = response.json()
        edge = data["edges"][0]
        assert {"source", "target", "type", "strength", "sentiment"} <= set(edge.keys())

    def test_power_flow_lines_present(self, logged_in_client, simulation, setup_graph_data):
        # setup_graph_data creates elena as a faction member without leader role,
        # so the chain should produce at least one power flow line (marco -> elena).
        response = logged_in_client.get(f"/simulations/{simulation.id}/graph/data/")
        assert response.status_code == 200
        data = response.json()
        assert "power_flow" in data
        assert len(data["power_flow"]) >= 1

    def test_faction_color_is_consistent(self, logged_in_client, simulation, setup_graph_data):
        r1 = logged_in_client.get(f"/simulations/{simulation.id}/graph/data/")
        r2 = logged_in_client.get(f"/simulations/{simulation.id}/graph/data/")
        nodes1 = {n["label"]: n["faction_color"] for n in r1.json()["nodes"]}
        nodes2 = {n["label"]: n["faction_color"] for n in r2.json()["nodes"]}
        assert nodes1 == nodes2

    def test_requires_authentication(self, simulation, setup_graph_data):
        client = Client()
        response = client.get(f"/simulations/{simulation.id}/graph/data/")
        assert response.status_code == 302


class TestGraphAgentDetailEndpoint:
    """Tests for the /simulations/<id>/graph/agent/<agent_id>/ endpoint."""

    def test_returns_agent_details(self, logged_in_client, simulation, setup_graph_data):
        marco, elena, faction, government = setup_graph_data
        response = logged_in_client.get(f"/simulations/{simulation.id}/graph/agent/{marco.id}/")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Marco"
        assert data["role"] == "blacksmith"
        assert "relationships" in data
        assert "recent_memories" in data

    def test_includes_relationships(self, logged_in_client, simulation, setup_graph_data):
        marco, elena, faction, government = setup_graph_data
        response = logged_in_client.get(f"/simulations/{simulation.id}/graph/agent/{marco.id}/")
        assert response.status_code == 200
        data = response.json()
        assert len(data["relationships"]) >= 1
        rel = data["relationships"][0]
        assert {"agent", "type", "sentiment"} <= set(rel.keys())

    def test_includes_recent_memories(self, logged_in_client, simulation, setup_graph_data):
        marco, elena, faction, government = setup_graph_data
        Memory.objects.create(
            agent=marco,
            content="Marco remembers Elena's help during the harvest.",
            emotional_weight=0.7,
            tick_created=5,
        )
        response = logged_in_client.get(f"/simulations/{simulation.id}/graph/agent/{marco.id}/")
        assert response.status_code == 200
        data = response.json()
        assert len(data["recent_memories"]) >= 1
        assert any("Elena" in m["content"] for m in data["recent_memories"])

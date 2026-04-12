"""Tests for the Knowledge Graph API endpoints.

Covers the graph data, upload, and status endpoints with authentication,
filtering, pagination, and error cases.
"""
from __future__ import annotations

from unittest.mock import patch

import pytest
from django.test import override_settings
from rest_framework.test import APIClient

from epocha.apps.knowledge.models import (
    ExtractionCache,
    KnowledgeDocument,
    KnowledgeGraph,
    KnowledgeNode,
    KnowledgeRelation,
)
from epocha.apps.simulation.models import Simulation
from epocha.apps.users.models import User


@pytest.fixture
def user(db):
    return User.objects.create_user(email="api@epocha.dev", username="apiuser", password="pass1234")


@pytest.fixture
def other_user(db):
    return User.objects.create_user(email="other@epocha.dev", username="otheruser", password="pass1234")


@pytest.fixture
def api_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def unauthenticated_client():
    return APIClient()


@pytest.fixture
def simulation(user):
    return Simulation.objects.create(name="APITest", seed=42, owner=user)


@pytest.fixture
def cache_entry(db):
    return ExtractionCache.objects.create(
        cache_key="a" * 64,
        documents_hash="b" * 64,
        ontology_version="v1",
        extraction_prompt_version="v1",
        llm_model="test-model",
        extracted_data={"nodes": [], "relations": []},
        stats={"chunks_processed": 1},
    )


@pytest.fixture
def document(db):
    return KnowledgeDocument.objects.create(
        title="Test Doc",
        mime_type="text/plain",
        content_hash="c" * 64,
        normalized_text="some text",
        char_count=9,
    )


@pytest.fixture
def graph(simulation, cache_entry, document):
    g = KnowledgeGraph.objects.create(
        simulation=simulation,
        extraction_cache=cache_entry,
        status="ready",
    )
    g.documents.add(document)
    return g


@pytest.fixture
def nodes(graph):
    """Create a small set of nodes for testing."""
    person = KnowledgeNode.objects.create(
        graph=graph, entity_type="person",
        name="Robespierre", canonical_name="robespierre",
        description="A revolutionary leader",
        source_type="document", confidence=0.95, mention_count=5,
        embedding=[0.1] * 1024,
    )
    place = KnowledgeNode.objects.create(
        graph=graph, entity_type="place",
        name="Paris", canonical_name="paris",
        description="Capital of France",
        source_type="document", confidence=0.90, mention_count=3,
        embedding=[0.2] * 1024,
    )
    event = KnowledgeNode.objects.create(
        graph=graph, entity_type="event",
        name="Storming of the Bastille", canonical_name="storming of the bastille",
        description="Key event of the Revolution",
        source_type="document", confidence=0.85, mention_count=2,
        embedding=[0.3] * 1024,
    )
    return person, place, event


@pytest.fixture
def edges(graph, nodes):
    """Create edges between nodes."""
    person, place, event = nodes
    e1 = KnowledgeRelation.objects.create(
        graph=graph, source_node=person, target_node=place,
        relation_type="located_in", source_type="document",
        confidence=0.8, weight=1.0,
    )
    e2 = KnowledgeRelation.objects.create(
        graph=graph, source_node=person, target_node=event,
        relation_type="participated_in", source_type="document",
        confidence=0.9, weight=1.5,
    )
    return e1, e2


# ---------------------------------------------------------------------------
# KnowledgeGraphDataView
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestKnowledgeGraphDataView:

    def test_returns_nodes_and_edges(self, api_client, simulation, graph, nodes, edges):
        response = api_client.get(f"/api/v1/knowledge/{simulation.id}/graph/")
        assert response.status_code == 200
        data = response.json()
        assert len(data["nodes"]) == 3
        assert len(data["edges"]) == 2
        assert data["stats"]["total_nodes"] == 3
        assert data["stats"]["returned_nodes"] == 3
        assert data["stats"]["has_more"] is False

    def test_entity_type_filter(self, api_client, simulation, graph, nodes, edges):
        response = api_client.get(
            f"/api/v1/knowledge/{simulation.id}/graph/",
            {"entity_types": "person"},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["nodes"]) == 1
        assert data["nodes"][0]["entity_type"] == "person"
        # Edges require both endpoints in node set; person-place edge excluded
        # because place is not in the result.
        assert len(data["edges"]) == 0

    def test_limit_and_offset(self, api_client, simulation, graph, nodes, edges):
        response = api_client.get(
            f"/api/v1/knowledge/{simulation.id}/graph/",
            {"limit": "2", "offset": "0"},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["nodes"]) == 2
        assert data["stats"]["has_more"] is True

    def test_404_when_no_graph(self, api_client, simulation):
        response = api_client.get(f"/api/v1/knowledge/{simulation.id}/graph/")
        assert response.status_code == 404

    def test_404_when_graph_not_ready(self, api_client, simulation, cache_entry):
        KnowledgeGraph.objects.create(
            simulation=simulation,
            extraction_cache=cache_entry,
            status="building",
        )
        response = api_client.get(f"/api/v1/knowledge/{simulation.id}/graph/")
        assert response.status_code == 404

    def test_auth_required(self, unauthenticated_client, simulation):
        response = unauthenticated_client.get(f"/api/v1/knowledge/{simulation.id}/graph/")
        assert response.status_code in (401, 403)

    def test_other_user_cannot_access(self, other_user, simulation, graph, nodes):
        client = APIClient()
        client.force_authenticate(user=other_user)
        response = client.get(f"/api/v1/knowledge/{simulation.id}/graph/")
        assert response.status_code == 404

    def test_node_linked_field(self, api_client, simulation, graph):
        """Verify the linked field serializes correctly when a FK is set."""
        from epocha.apps.agents.models import Agent
        agent = Agent.objects.create(
            simulation=simulation, name="TestAgent", role="citizen",
            personality={}, age=30, social_class="middle",
        )
        node = KnowledgeNode.objects.create(
            graph=graph, entity_type="person",
            name="Test", canonical_name="test",
            source_type="document", confidence=0.9,
            embedding=[0.1] * 1024,
            linked_agent=agent,
        )
        response = api_client.get(f"/api/v1/knowledge/{simulation.id}/graph/")
        data = response.json()
        node_data = next(n for n in data["nodes"] if n["id"] == node.id)
        assert node_data["linked"] == {"kind": "agent", "id": agent.id}

    def test_edge_category_field(self, api_client, simulation, graph, nodes, edges):
        """Verify edges include the correct category from the ontology."""
        response = api_client.get(f"/api/v1/knowledge/{simulation.id}/graph/")
        data = response.json()
        categories = {e["category"] for e in data["edges"]}
        assert "spatial" in categories
        assert "participation" in categories


# ---------------------------------------------------------------------------
# KnowledgeGraphStatusView
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestKnowledgeGraphStatusView:

    def test_ready_graph(self, api_client, simulation, graph, nodes):
        response = api_client.get(f"/api/v1/knowledge/{simulation.id}/status/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
        assert data["nodes"] == 3
        assert data["error"] == ""

    def test_no_graph(self, api_client, simulation):
        response = api_client.get(f"/api/v1/knowledge/{simulation.id}/status/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "no_graph"
        assert data["nodes"] == 0

    def test_auth_required(self, unauthenticated_client, simulation):
        response = unauthenticated_client.get(f"/api/v1/knowledge/{simulation.id}/status/")
        assert response.status_code in (401, 403)


# ---------------------------------------------------------------------------
# KnowledgeGraphUploadView
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestKnowledgeGraphUploadView:

    @patch("epocha.apps.knowledge.tasks.extract_and_generate")
    @patch("epocha.apps.world.document_parser.extract_text")
    def test_upload_creates_simulation_and_returns_202(
        self, mock_extract_text, mock_pipeline, api_client,
    ):
        mock_extract_text.return_value = "The French Revolution began in 1789."
        mock_pipeline.return_value = {
            "status": "ready",
            "graph_id": 1,
            "nodes": 5,
            "relations": 3,
        }

        from django.core.files.uploadedfile import SimpleUploadedFile
        doc = SimpleUploadedFile("test.txt", b"Revolution content", content_type="text/plain")
        response = api_client.post(
            "/api/v1/knowledge/upload/",
            {"name": "Upload Test", "documents": [doc]},
            format="multipart",
        )
        assert response.status_code == 202
        data = response.json()
        assert data["status"] == "ready"
        assert data["simulation_id"] is not None
        assert data["nodes"] == 5

        # Verify a simulation was created
        sim = Simulation.objects.get(pk=data["simulation_id"])
        assert sim.name == "Upload Test"

        # Verify pipeline was called with correct args
        mock_pipeline.assert_called_once()
        call_kwargs = mock_pipeline.call_args[1]
        assert call_kwargs["simulation_id"] == sim.id
        assert len(call_kwargs["documents_data"]) == 1

    def test_upload_requires_name(self, api_client):
        from django.core.files.uploadedfile import SimpleUploadedFile
        doc = SimpleUploadedFile("test.txt", b"content", content_type="text/plain")
        response = api_client.post(
            "/api/v1/knowledge/upload/",
            {"documents": [doc]},
            format="multipart",
        )
        assert response.status_code == 400

    def test_upload_requires_documents(self, api_client):
        response = api_client.post(
            "/api/v1/knowledge/upload/",
            {"name": "No Docs"},
            format="multipart",
        )
        assert response.status_code == 400

    def test_upload_auth_required(self, unauthenticated_client):
        response = unauthenticated_client.post("/api/v1/knowledge/upload/", {"name": "X"})
        assert response.status_code in (401, 403)

"""Tests for the Knowledge Graph dashboard views.

Covers the knowledge graph template rendering, authentication redirect,
and 404 on missing graph.
"""
from __future__ import annotations

import pytest
from django.test import Client

from epocha.apps.knowledge.models import (
    ExtractionCache,
    KnowledgeDocument,
    KnowledgeGraph,
    KnowledgeNode,
)
from epocha.apps.simulation.models import Simulation
from epocha.apps.users.models import User


@pytest.fixture
def user(db):
    return User.objects.create_user(email="view@epocha.dev", username="viewuser", password="pass1234")


@pytest.fixture
def simulation(user):
    return Simulation.objects.create(name="ViewTest", seed=42, owner=user)


@pytest.fixture
def cache_entry(db):
    return ExtractionCache.objects.create(
        cache_key="v" * 64,
        documents_hash="w" * 64,
        ontology_version="v1",
        extraction_prompt_version="v1",
        llm_model="test-model",
        extracted_data={"nodes": [], "relations": []},
        stats={"chunks_processed": 1},
    )


@pytest.fixture
def document(db):
    return KnowledgeDocument.objects.create(
        title="View Doc",
        mime_type="text/plain",
        content_hash="x" * 64,
        normalized_text="text",
        char_count=4,
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
def node(graph):
    return KnowledgeNode.objects.create(
        graph=graph, entity_type="person",
        name="Danton", canonical_name="danton",
        source_type="document", confidence=0.9,
        embedding=[0.1] * 1024,
    )


@pytest.fixture
def logged_in_client(user):
    client = Client()
    client.login(email="view@epocha.dev", password="pass1234")
    return client


@pytest.mark.django_db
class TestKnowledgeGraphView:

    def test_returns_200_with_graph(self, logged_in_client, simulation, graph, node):
        response = logged_in_client.get(f"/simulations/{simulation.id}/knowledge-graph/")
        assert response.status_code == 200

    def test_contains_sigma_script(self, logged_in_client, simulation, graph, node):
        response = logged_in_client.get(f"/simulations/{simulation.id}/knowledge-graph/")
        content = response.content.decode()
        assert "sigma" in content.lower()

    def test_contains_simulation_name(self, logged_in_client, simulation, graph, node):
        response = logged_in_client.get(f"/simulations/{simulation.id}/knowledge-graph/")
        content = response.content.decode()
        assert simulation.name in content

    def test_contains_knowledge_graph_title(self, logged_in_client, simulation, graph, node):
        response = logged_in_client.get(f"/simulations/{simulation.id}/knowledge-graph/")
        content = response.content.decode()
        assert "Knowledge Graph" in content

    def test_auth_redirect(self, simulation, graph):
        client = Client()
        response = client.get(f"/simulations/{simulation.id}/knowledge-graph/")
        assert response.status_code == 302
        assert "/login/" in response.url

    def test_404_no_graph(self, logged_in_client, simulation):
        response = logged_in_client.get(f"/simulations/{simulation.id}/knowledge-graph/")
        assert response.status_code == 404

    def test_404_other_user(self, simulation, graph, node):
        other = User.objects.create_user(email="x@x.dev", username="xuser", password="pass1234")
        client = Client()
        client.login(email="x@x.dev", password="pass1234")
        response = client.get(f"/simulations/{simulation.id}/knowledge-graph/")
        assert response.status_code == 404

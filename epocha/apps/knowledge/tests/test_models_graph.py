"""Tests for the graph-tier models."""
import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from epocha.apps.knowledge.models import (
    ExtractionCache,
    KnowledgeChunk,
    KnowledgeDocument,
    KnowledgeGraph,
    KnowledgeNode,
    KnowledgeNodeCitation,
    KnowledgeRelation,
    KnowledgeRelationCitation,
)
from epocha.apps.simulation.models import Simulation
from epocha.apps.users.models import User


@pytest.fixture
def user(db):
    return User.objects.create_user(email="graph@epocha.dev", username="graphuser", password="pass1234")

@pytest.fixture
def simulation(user):
    return Simulation.objects.create(name="GraphTest", seed=42, owner=user)

@pytest.fixture
def document(db):
    return KnowledgeDocument.objects.create(
        title="Test Doc", mime_type="text/plain",
        content_hash="g" * 64, normalized_text="some text", char_count=9,
    )

@pytest.fixture
def chunk(document):
    return KnowledgeChunk.objects.create(
        document=document, chunk_index=0,
        text="some text", start_char=0, end_char=9,
        embedding=[0.1] * 1024,
    )

@pytest.fixture
def cache_entry(db):
    return ExtractionCache.objects.create(
        cache_key="h" * 64, documents_hash="g" * 64,
        ontology_version="v1", extraction_prompt_version="v1",
        llm_model="test-model",
        extracted_data={"nodes": [], "relations": []},
        stats={"chunks_processed": 1},
    )

@pytest.fixture
def graph(simulation, document, cache_entry):
    g = KnowledgeGraph.objects.create(
        simulation=simulation, extraction_cache=cache_entry, status="ready",
    )
    g.documents.add(document)
    return g

@pytest.fixture
def node(graph):
    return KnowledgeNode.objects.create(
        graph=graph, entity_type="person",
        name="Robespierre", canonical_name="robespierre",
        description="A revolutionary leader",
        source_type="document", confidence=0.9, mention_count=3,
        embedding=[0.1] * 1024,
    )


@pytest.mark.django_db
class TestKnowledgeGraph:
    def test_create_graph(self, graph):
        assert graph.status == "ready"
        assert graph.simulation is not None
        assert graph.documents.count() == 1

    def test_one_graph_per_simulation(self, simulation, cache_entry):
        KnowledgeGraph.objects.create(
            simulation=simulation, extraction_cache=cache_entry, status="ready",
        )
        with pytest.raises(IntegrityError):
            KnowledgeGraph.objects.create(
                simulation=simulation, extraction_cache=cache_entry, status="ready",
            )

    def test_cache_protected_from_deletion(self, graph, cache_entry):
        from django.db.models import ProtectedError
        with pytest.raises(ProtectedError):
            cache_entry.delete()


@pytest.mark.django_db
class TestKnowledgeNode:
    def test_create_node(self, node):
        assert node.entity_type == "person"
        assert node.canonical_name == "robespierre"
        assert len(node.embedding) == 1024

    def test_unique_together_entity_type_canonical(self, graph):
        KnowledgeNode.objects.create(
            graph=graph, entity_type="person",
            name="Danton", canonical_name="danton",
            source_type="document", confidence=0.9, mention_count=1,
            embedding=[0.2] * 1024,
        )
        with pytest.raises(IntegrityError):
            KnowledgeNode.objects.create(
                graph=graph, entity_type="person",
                name="Georges Danton", canonical_name="danton",
                source_type="document", confidence=0.9, mention_count=1,
                embedding=[0.3] * 1024,
            )

    def test_same_canonical_different_type_allowed(self, graph):
        KnowledgeNode.objects.create(
            graph=graph, entity_type="place", name="Paris", canonical_name="paris",
            source_type="document", confidence=0.9, mention_count=1, embedding=[0.2] * 1024,
        )
        KnowledgeNode.objects.create(
            graph=graph, entity_type="concept", name="Paris", canonical_name="paris",
            source_type="document_inferred", confidence=0.5, mention_count=1, embedding=[0.3] * 1024,
        )
        assert KnowledgeNode.objects.filter(graph=graph, canonical_name="paris").count() == 2

    def test_linked_agent_nullable(self, node):
        assert node.linked_agent is None


@pytest.mark.django_db
class TestKnowledgeRelation:
    def test_create_relation(self, graph, node):
        target = KnowledgeNode.objects.create(
            graph=graph, entity_type="institution",
            name="Jacobin Club", canonical_name="jacobin club",
            source_type="document", confidence=0.9, mention_count=2,
            embedding=[0.5] * 1024,
        )
        rel = KnowledgeRelation.objects.create(
            graph=graph, source_node=node, target_node=target,
            relation_type="member_of", description="was a member",
            source_type="document", confidence=0.9, weight=0.8,
            temporal_start_iso="1789", temporal_start_year=1789,
        )
        assert rel.source_node == node
        assert rel.target_node == target
        assert rel.temporal_start_year == 1789

    def test_cross_graph_validation(self, graph, node, simulation, cache_entry):
        other_sim = Simulation.objects.create(name="Other", seed=99, owner=simulation.owner)
        other_graph = KnowledgeGraph.objects.create(
            simulation=other_sim, extraction_cache=cache_entry, status="ready",
        )
        other_node = KnowledgeNode.objects.create(
            graph=other_graph, entity_type="person",
            name="Danton", canonical_name="danton",
            source_type="document", confidence=0.9, mention_count=1,
            embedding=[0.2] * 1024,
        )
        rel = KnowledgeRelation(
            graph=graph, source_node=node, target_node=other_node,
            relation_type="ally_of", source_type="document",
            confidence=0.9, weight=0.5,
        )
        with pytest.raises(ValidationError):
            rel.clean()


@pytest.mark.django_db
class TestCitations:
    def test_node_citation(self, node, chunk):
        citation = KnowledgeNodeCitation.objects.create(
            node=node, chunk=chunk,
            passage_excerpt="Robespierre was a member of the Jacobin Club.",
        )
        assert citation.node == node
        assert citation.chunk == chunk

    def test_node_citation_unique(self, node, chunk):
        KnowledgeNodeCitation.objects.create(node=node, chunk=chunk, passage_excerpt="first")
        with pytest.raises(IntegrityError):
            KnowledgeNodeCitation.objects.create(node=node, chunk=chunk, passage_excerpt="second")

    def test_relation_citation(self, graph, node, chunk):
        target = KnowledgeNode.objects.create(
            graph=graph, entity_type="institution",
            name="Assembly", canonical_name="assembly",
            source_type="document", confidence=0.9, mention_count=1,
            embedding=[0.5] * 1024,
        )
        rel = KnowledgeRelation.objects.create(
            graph=graph, source_node=node, target_node=target,
            relation_type="member_of", source_type="document",
            confidence=0.9, weight=0.5,
        )
        citation = KnowledgeRelationCitation.objects.create(
            relation=rel, chunk=chunk,
            passage_excerpt="Robespierre was elected to the Assembly.",
        )
        assert citation.relation == rel

"""Tests for graph materialization from cached extraction data."""

import pytest

from epocha.apps.knowledge.materialization import materialize_graph
from epocha.apps.knowledge.models import (
    ExtractionCache,
    KnowledgeChunk,
    KnowledgeDocument,
    KnowledgeGraph,
)
from epocha.apps.simulation.models import Simulation
from epocha.apps.users.models import User


@pytest.fixture
def user(db):
    return User.objects.create_user(
        email="mat@epocha.dev",
        username="matuser",
        password="pass1234",
    )


@pytest.fixture
def simulation(user):
    return Simulation.objects.create(name="MatTest", seed=42, owner=user)


@pytest.fixture
def document(db):
    return KnowledgeDocument.objects.create(
        title="Test Doc",
        mime_type="text/plain",
        content_hash="m" * 64,
        normalized_text="some text about Robespierre",
        char_count=27,
    )


@pytest.fixture
def chunk(document):
    return KnowledgeChunk.objects.create(
        document=document,
        chunk_index=0,
        text="Robespierre was a member of the Jacobin Club.",
        start_char=0,
        end_char=46,
        embedding=[0.1] * 1024,
    )


@pytest.fixture
def extracted_data(chunk):
    return {
        "nodes": [
            {
                "entity_type": "person",
                "name": "Robespierre",
                "canonical_name": "robespierre",
                "description": "A revolutionary leader",
                "source_type": "document",
                "confidence": 0.9,
                "mention_count": 3,
                "attributes": {"role": "deputy"},
                "chunk_ids": [chunk.chunk_index],
                "embedding": [0.1] * 1024,
                "passage_excerpts": {
                    str(chunk.chunk_index): "Robespierre was a member",
                },
            },
            {
                "entity_type": "institution",
                "name": "Jacobin Club",
                "canonical_name": "jacobin club",
                "description": "A political society",
                "source_type": "document",
                "confidence": 0.85,
                "mention_count": 2,
                "attributes": {},
                "chunk_ids": [chunk.chunk_index],
                "embedding": [0.2] * 1024,
                "passage_excerpts": {
                    str(chunk.chunk_index): "the Jacobin Club",
                },
            },
        ],
        "relations": [
            {
                "source_entity_type": "person",
                "source_canonical_name": "robespierre",
                "target_entity_type": "institution",
                "target_canonical_name": "jacobin club",
                "relation_type": "member_of",
                "description": "was a member",
                "source_type": "document",
                "confidence": 0.9,
                "weight": 0.8,
                "temporal_start_iso": "1789",
                "temporal_start_year": 1789,
                "temporal_end_iso": "",
                "temporal_end_year": None,
                "chunk_ids": [chunk.chunk_index],
                "passage_excerpts": {
                    str(chunk.chunk_index): (
                        "Robespierre was a member of the Jacobin Club."
                    ),
                },
            },
        ],
        "unrecognized_entities": [],
        "unrecognized_relations": [],
        "stats": {
            "chunks_processed": 1,
            "nodes_before_merge": 2,
            "nodes_after_merge": 2,
        },
    }


@pytest.fixture
def cache_entry(extracted_data):
    return ExtractionCache.objects.create(
        cache_key="mat" + "0" * 61,
        documents_hash="m" * 64,
        ontology_version="v1",
        extraction_prompt_version="v1",
        llm_model="test-model",
        extracted_data=extracted_data,
        stats=extracted_data["stats"],
    )


@pytest.mark.django_db
class TestMaterializeGraph:
    """Verify that materialize_graph correctly creates graph-tier rows
    from cached extraction data and handles edge cases gracefully.
    """

    def test_creates_graph_with_nodes_and_relations(
        self,
        simulation,
        document,
        cache_entry,
        chunk,
    ):
        graph = materialize_graph(
            simulation=simulation,
            documents=[document],
            cache_entry=cache_entry,
        )
        assert graph.status == "ready"
        assert graph.nodes.count() == 2
        assert graph.relations.count() == 1

    def test_nodes_have_correct_attributes(
        self,
        simulation,
        document,
        cache_entry,
        chunk,
    ):
        graph = materialize_graph(
            simulation=simulation,
            documents=[document],
            cache_entry=cache_entry,
        )
        rob = graph.nodes.get(canonical_name="robespierre")
        assert rob.entity_type == "person"
        assert rob.mention_count == 3
        assert rob.confidence == 0.9
        assert len(rob.embedding) == 1024

    def test_node_attributes_stored(
        self,
        simulation,
        document,
        cache_entry,
        chunk,
    ):
        graph = materialize_graph(
            simulation=simulation,
            documents=[document],
            cache_entry=cache_entry,
        )
        rob = graph.nodes.get(canonical_name="robespierre")
        assert rob.attributes == {"role": "deputy"}

    def test_relation_endpoints_resolved(
        self,
        simulation,
        document,
        cache_entry,
        chunk,
    ):
        graph = materialize_graph(
            simulation=simulation,
            documents=[document],
            cache_entry=cache_entry,
        )
        rel = graph.relations.first()
        assert rel.source_node.canonical_name == "robespierre"
        assert rel.target_node.canonical_name == "jacobin club"
        assert rel.temporal_start_year == 1789

    def test_node_citations_created(
        self,
        simulation,
        document,
        cache_entry,
        chunk,
    ):
        graph = materialize_graph(
            simulation=simulation,
            documents=[document],
            cache_entry=cache_entry,
        )
        rob = graph.nodes.get(canonical_name="robespierre")
        assert rob.citations.count() == 1
        citation = rob.citations.first()
        assert citation.chunk == chunk
        assert citation.passage_excerpt == "Robespierre was a member"

    def test_relation_citations_created(
        self,
        simulation,
        document,
        cache_entry,
        chunk,
    ):
        graph = materialize_graph(
            simulation=simulation,
            documents=[document],
            cache_entry=cache_entry,
        )
        rel = graph.relations.first()
        assert rel.citations.count() == 1
        citation = rel.citations.first()
        assert citation.chunk == chunk
        assert citation.passage_excerpt == (
            "Robespierre was a member of the Jacobin Club."
        )

    def test_graph_linked_to_documents(
        self,
        simulation,
        document,
        cache_entry,
        chunk,
    ):
        graph = materialize_graph(
            simulation=simulation,
            documents=[document],
            cache_entry=cache_entry,
        )
        assert document in graph.documents.all()

    def test_materialized_at_set(
        self,
        simulation,
        document,
        cache_entry,
        chunk,
    ):
        graph = materialize_graph(
            simulation=simulation,
            documents=[document],
            cache_entry=cache_entry,
        )
        assert graph.materialized_at is not None

    def test_unresolved_relation_endpoints_dropped(
        self,
        simulation,
        document,
        chunk,
    ):
        """Relations referencing nodes that do not exist in the extracted
        data should be silently dropped without failing the transaction.
        """
        bad_data = {
            "nodes": [
                {
                    "entity_type": "person",
                    "name": "Robespierre",
                    "canonical_name": "robespierre",
                    "description": "",
                    "source_type": "document",
                    "confidence": 0.9,
                    "mention_count": 1,
                    "attributes": {},
                    "chunk_ids": [0],
                    "embedding": [0.1] * 1024,
                    "passage_excerpts": {},
                },
            ],
            "relations": [
                {
                    "source_entity_type": "person",
                    "source_canonical_name": "robespierre",
                    "target_entity_type": "institution",
                    "target_canonical_name": "nonexistent club",
                    "relation_type": "member_of",
                    "description": "",
                    "source_type": "document",
                    "confidence": 0.9,
                    "weight": 0.5,
                    "temporal_start_iso": "",
                    "temporal_start_year": None,
                    "temporal_end_iso": "",
                    "temporal_end_year": None,
                    "chunk_ids": [0],
                    "passage_excerpts": {},
                },
            ],
            "unrecognized_entities": [],
            "unrecognized_relations": [],
            "stats": {},
        }
        cache = ExtractionCache.objects.create(
            cache_key="bad" + "0" * 61,
            documents_hash="m" * 64,
            ontology_version="v1",
            extraction_prompt_version="v1",
            llm_model="test",
            extracted_data=bad_data,
            stats={},
        )
        graph = materialize_graph(
            simulation=simulation,
            documents=[document],
            cache_entry=cache,
        )
        assert graph.nodes.count() == 1
        assert graph.relations.count() == 0

    def test_atomicity_on_failure(self, simulation, document, chunk):
        """If materialization fails mid-transaction, no partial rows
        should remain in the database.
        """
        broken_data = {
            "nodes": [
                {
                    "entity_type": "person",
                    "name": "Robespierre",
                    "canonical_name": "robespierre",
                    "description": "",
                    "source_type": "document",
                    "confidence": 0.9,
                    "mention_count": 1,
                    "attributes": {},
                    "chunk_ids": [0],
                    "embedding": [0.1] * 1024,
                    "passage_excerpts": {},
                },
                {
                    # Duplicate (entity_type, canonical_name)
                    # -- violates unique_together
                    "entity_type": "person",
                    "name": "Robespierre Again",
                    "canonical_name": "robespierre",
                    "description": "",
                    "source_type": "document",
                    "confidence": 0.8,
                    "mention_count": 1,
                    "attributes": {},
                    "chunk_ids": [0],
                    "embedding": [0.1] * 1024,
                    "passage_excerpts": {},
                },
            ],
            "relations": [],
            "unrecognized_entities": [],
            "unrecognized_relations": [],
            "stats": {},
        }
        cache = ExtractionCache.objects.create(
            cache_key="brk" + "0" * 61,
            documents_hash="m" * 64,
            ontology_version="v1",
            extraction_prompt_version="v1",
            llm_model="test",
            extracted_data=broken_data,
            stats={},
        )
        with pytest.raises(Exception):
            materialize_graph(
                simulation=simulation,
                documents=[document],
                cache_entry=cache,
            )
        # No graph should have been persisted
        assert KnowledgeGraph.objects.filter(simulation=simulation).count() == 0

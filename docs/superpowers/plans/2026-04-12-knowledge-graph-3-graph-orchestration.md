# Knowledge Graph Implementation Plan — Part 3: Graph, Materialization, Orchestration

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the per-simulation graph models (KnowledgeGraph, KnowledgeNode, KnowledgeRelation, citations), the materialization logic that turns cached extraction data into queryable rows, the Celery orchestration task that wires stages 1-8 together, and the world generator integration that produces agents from the graph. After this plan, the full extraction-to-generation pipeline is functional end-to-end.

**Architecture:** The graph-tier models live in `knowledge/models.py` alongside the shared-tier models from Part 1. Materialization reads from ExtractionCache and writes isolated rows per simulation. The Celery task orchestrates ingestion -> chunking -> embedding -> cache check -> extraction -> merge -> cache persist -> materialize -> generate. The world generator gains a `_generate_from_knowledge_graph` path that builds the LLM prompt from structured graph data.

**Tech Stack:** Django ORM, pgvector, Celery, existing LLM adapter.

**Spec:** `docs/superpowers/specs/2026-04-11-knowledge-graph-design.md` (Stages 7-9 + World Generation Integration)

**Depends on:** Part 1 (Foundations) + Part 2 (Extraction pipeline) — both completed.

**Follow-up:** Part 4 — API, dashboard, visualization, housekeeping.

---

## File Structure (Part 3 scope)

| File | Responsibility | New/Modify |
|------|---------------|------------|
| `epocha/apps/knowledge/models.py` | Add KnowledgeGraph, KnowledgeNode, KnowledgeRelation, KnowledgeNodeCitation, KnowledgeRelationCitation | Modify |
| `epocha/apps/knowledge/migrations/0004_graph_models.py` | Migration for graph-tier models | New (auto) |
| `epocha/apps/knowledge/materialization.py` | Turn cached extraction data into per-simulation rows | New |
| `epocha/apps/knowledge/tasks.py` | Celery task orchestrating the full pipeline | New |
| `epocha/apps/world/generator.py` | Add _generate_from_knowledge_graph + extend signature | Modify |
| `epocha/apps/knowledge/tests/test_models_graph.py` | Tests for graph-tier models | New |
| `epocha/apps/knowledge/tests/test_materialization.py` | Tests for materialization | New |
| `epocha/apps/knowledge/tests/test_tasks.py` | Tests for Celery orchestration | New |
| `epocha/apps/world/tests/test_generator_kg.py` | Tests for knowledge-graph-based generation | New |

---

## Tasks summary (Part 3 scope)

9. **Graph-tier models** — KnowledgeGraph, KnowledgeNode, KnowledgeRelation, citations + migration
10. **Materialization** — materialize_graph function turning cached data into DB rows
11. **Celery orchestration** — extract_and_generate task wiring the full pipeline
12. **World generator integration** — _generate_from_knowledge_graph function

---

### Task 9: Graph-tier models

**Files:**
- Modify: `epocha/apps/knowledge/models.py` (append 5 new models)
- New: `epocha/apps/knowledge/migrations/0004_graph_models.py` (auto-generated)
- New: `epocha/apps/knowledge/tests/test_models_graph.py`

- [ ] **Step 1: Write the failing tests**

Create `epocha/apps/knowledge/tests/test_models_graph.py`:

```python
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
            graph=graph, entity_type="place",
            name="Paris", canonical_name="paris",
            source_type="document", confidence=0.9, mention_count=1,
            embedding=[0.2] * 1024,
        )
        KnowledgeNode.objects.create(
            graph=graph, entity_type="concept",
            name="Paris", canonical_name="paris",
            source_type="document_inferred", confidence=0.5, mention_count=1,
            embedding=[0.3] * 1024,
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
        KnowledgeNodeCitation.objects.create(
            node=node, chunk=chunk, passage_excerpt="first",
        )
        with pytest.raises(IntegrityError):
            KnowledgeNodeCitation.objects.create(
                node=node, chunk=chunk, passage_excerpt="second",
            )

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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `docker compose -f docker-compose.local.yml run --rm web pytest epocha/apps/knowledge/tests/test_models_graph.py -v`

Expected: ImportError (KnowledgeGraph not in models).

- [ ] **Step 3: Append graph-tier models to models.py**

APPEND the following five models to `epocha/apps/knowledge/models.py` after the ExtractionCache class. Also add the needed import at the top: `from django.utils import timezone`.

```python
class KnowledgeGraph(models.Model):
    """Materialized knowledge graph for a single simulation."""

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("extracting", "Extracting"),
        ("materializing", "Materializing"),
        ("ready", "Ready"),
        ("failed", "Failed"),
    ]

    simulation = models.OneToOneField(
        "simulation.Simulation", on_delete=models.CASCADE,
        related_name="knowledge_graph",
    )
    documents = models.ManyToManyField(KnowledgeDocument, related_name="graphs")
    extraction_cache = models.ForeignKey(
        ExtractionCache, on_delete=models.PROTECT, related_name="graphs",
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    materialized_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"KnowledgeGraph for {self.simulation.name} ({self.status})"


class KnowledgeNode(models.Model):
    """A single entity in the knowledge graph."""

    ENTITY_TYPES = [
        ("person", "Person"),
        ("group", "Group"),
        ("place", "Geographic Place"),
        ("institution", "Institution"),
        ("event", "Historical Event"),
        ("concept", "Abstract Concept"),
        ("ideology", "Ideology"),
        ("object", "Material Object"),
        ("norm", "Norm or Law"),
        ("value", "Cultural Value"),
    ]

    SOURCE_TYPES = [
        ("document", "Document (literal)"),
        ("document_inferred", "Document inferred"),
    ]

    graph = models.ForeignKey(
        KnowledgeGraph, on_delete=models.CASCADE, related_name="nodes",
    )
    entity_type = models.CharField(max_length=20, choices=ENTITY_TYPES)
    name = models.CharField(max_length=255)
    canonical_name = models.CharField(max_length=255, db_index=True)
    description = models.TextField(blank=True)
    attributes = models.JSONField(default=dict)
    source_type = models.CharField(max_length=20, choices=SOURCE_TYPES)
    confidence = models.FloatField(default=1.0)
    mention_count = models.PositiveIntegerField(default=1)
    embedding = VectorField(dimensions=EMBEDDING_DIM)

    linked_agent = models.ForeignKey(
        "agents.Agent", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="knowledge_nodes",
    )
    linked_group = models.ForeignKey(
        "agents.Group", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="knowledge_nodes",
    )
    linked_zone = models.ForeignKey(
        "world.Zone", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="knowledge_nodes",
    )
    linked_event = models.ForeignKey(
        "simulation.Event", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="knowledge_nodes",
    )
    linked_institution = models.ForeignKey(
        "world.Institution", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="knowledge_nodes",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("graph", "entity_type", "canonical_name")
        indexes = [
            models.Index(fields=["graph", "entity_type"]),
            HnswIndex(
                name="node_embedding_hnsw",
                fields=["embedding"],
                m=16,
                ef_construction=64,
                opclasses=["vector_cosine_ops"],
            ),
        ]


class KnowledgeRelation(models.Model):
    """A directed relation between two nodes with optional temporal scope."""

    RELATION_TYPES = [
        ("member_of", "member of"),
        ("founder_of", "founder of"),
        ("leader_of", "leader of"),
        ("located_in", "located in"),
        ("occurred_in", "occurred in"),
        ("occurred_during", "occurred during"),
        ("believes_in", "believes in"),
        ("opposes", "opposes"),
        ("supports", "supports"),
        ("ally_of", "ally of"),
        ("enemy_of", "enemy of"),
        ("influences", "influences"),
        ("married_to", "married to"),
        ("parent_of", "parent of"),
        ("sibling_of", "sibling of"),
        ("caused_by", "caused by"),
        ("led_to", "led to"),
        ("participated_in", "participated in"),
        ("authored", "authored"),
        ("enacted", "enacted"),
    ]

    graph = models.ForeignKey(
        KnowledgeGraph, on_delete=models.CASCADE, related_name="relations",
    )
    source_node = models.ForeignKey(
        KnowledgeNode, on_delete=models.CASCADE, related_name="outgoing_relations",
    )
    target_node = models.ForeignKey(
        KnowledgeNode, on_delete=models.CASCADE, related_name="incoming_relations",
    )
    relation_type = models.CharField(max_length=30, choices=RELATION_TYPES)
    description = models.TextField(blank=True)
    source_type = models.CharField(max_length=20, choices=KnowledgeNode.SOURCE_TYPES)
    confidence = models.FloatField(default=1.0)
    weight = models.FloatField(default=0.5)

    temporal_start_iso = models.CharField(max_length=20, blank=True)
    temporal_start_year = models.IntegerField(null=True, blank=True, db_index=True)
    temporal_end_iso = models.CharField(max_length=20, blank=True)
    temporal_end_year = models.IntegerField(null=True, blank=True, db_index=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["graph", "source_node"]),
            models.Index(fields=["graph", "target_node"]),
            models.Index(fields=["graph", "relation_type"]),
            models.Index(fields=["graph", "temporal_start_year", "temporal_end_year"]),
        ]

    def clean(self):
        """Validate that both endpoints belong to the same graph."""
        from django.core.exceptions import ValidationError
        if self.source_node_id and self.source_node.graph_id != self.graph_id:
            raise ValidationError("source_node must belong to the same graph")
        if self.target_node_id and self.target_node.graph_id != self.graph_id:
            raise ValidationError("target_node must belong to the same graph")


class KnowledgeNodeCitation(models.Model):
    """Citation linking a node back to a specific chunk."""

    node = models.ForeignKey(
        KnowledgeNode, on_delete=models.CASCADE, related_name="citations",
    )
    chunk = models.ForeignKey(
        KnowledgeChunk, on_delete=models.CASCADE, related_name="node_citations",
    )
    passage_excerpt = models.TextField()

    class Meta:
        unique_together = ("node", "chunk")


class KnowledgeRelationCitation(models.Model):
    """Citation linking a relation back to a specific chunk."""

    relation = models.ForeignKey(
        KnowledgeRelation, on_delete=models.CASCADE, related_name="citations",
    )
    chunk = models.ForeignKey(
        KnowledgeChunk, on_delete=models.CASCADE, related_name="relation_citations",
    )
    passage_excerpt = models.TextField()

    class Meta:
        unique_together = ("relation", "chunk")
```

- [ ] **Step 4: Generate and apply migration**

Run:
```bash
docker compose -f docker-compose.local.yml run --rm web python manage.py makemigrations knowledge --name graph_models
docker compose -f docker-compose.local.yml run --rm web python manage.py migrate knowledge
```

- [ ] **Step 5: Run graph model tests**

Run: `docker compose -f docker-compose.local.yml run --rm web pytest epocha/apps/knowledge/tests/test_models_graph.py -v`

Expected: all PASS.

- [ ] **Step 6: Run full suite**

Run: `docker compose -f docker-compose.local.yml run --rm web pytest -q -m "not slow"`

Expected: all tests pass.

- [ ] **Step 7: Commit**

```
feat(knowledge): add graph-tier models with citations and cross-graph validation

CHANGE: Add KnowledgeGraph (OneToOne to Simulation with status tracking),
KnowledgeNode (10 entity types, pgvector embedding, linked FKs to Agent/
Zone/Group/Event/Institution), KnowledgeRelation (20 relation types with
temporal scope and cross-graph validation), KnowledgeNodeCitation and
KnowledgeRelationCitation linking back to source chunks. ExtractionCache
is PROTECT-ed from deletion when active graphs reference it.
```

---

### Task 10: Materialization

**Files:**
- New: `epocha/apps/knowledge/materialization.py`
- New: `epocha/apps/knowledge/tests/test_materialization.py`

- [ ] **Step 1: Write the failing tests**

Create `epocha/apps/knowledge/tests/test_materialization.py`:

```python
"""Tests for graph materialization from cached extraction data."""
import pytest

from epocha.apps.knowledge.materialization import materialize_graph
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
    return User.objects.create_user(email="mat@epocha.dev", username="matuser", password="pass1234")


@pytest.fixture
def simulation(user):
    return Simulation.objects.create(name="MatTest", seed=42, owner=user)


@pytest.fixture
def document(db):
    return KnowledgeDocument.objects.create(
        title="Test Doc", mime_type="text/plain",
        content_hash="m" * 64, normalized_text="some text about Robespierre", char_count=27,
    )


@pytest.fixture
def chunk(document):
    return KnowledgeChunk.objects.create(
        document=document, chunk_index=0,
        text="Robespierre was a member of the Jacobin Club.",
        start_char=0, end_char=46,
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
                "passage_excerpts": {str(chunk.chunk_index): "Robespierre was a member"},
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
                "passage_excerpts": {str(chunk.chunk_index): "the Jacobin Club"},
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
                "passage_excerpts": {str(chunk.chunk_index): "Robespierre was a member of the Jacobin Club."},
            },
        ],
        "unrecognized_entities": [],
        "unrecognized_relations": [],
        "stats": {"chunks_processed": 1, "nodes_before_merge": 2, "nodes_after_merge": 2},
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
    def test_creates_graph_with_nodes_and_relations(
        self, simulation, document, cache_entry, chunk
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
        self, simulation, document, cache_entry, chunk
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

    def test_relation_endpoints_resolved(
        self, simulation, document, cache_entry, chunk
    ):
        graph = materialize_graph(
            simulation=simulation,
            documents=[document],
            cache_entry=cache_entry,
        )
        rel = graph.relations.first()
        assert rel.source_node.canonical_name == "robespierre"
        assert rel.target_node.canonical_name == "jacobin club"
        assert rel.relation_type == "member_of"
        assert rel.temporal_start_year == 1789

    def test_citations_created(
        self, simulation, document, cache_entry, chunk
    ):
        graph = materialize_graph(
            simulation=simulation,
            documents=[document],
            cache_entry=cache_entry,
        )
        rob = graph.nodes.get(canonical_name="robespierre")
        assert rob.citations.count() == 1
        assert rob.citations.first().chunk == chunk

    def test_graph_linked_to_documents(
        self, simulation, document, cache_entry, chunk
    ):
        graph = materialize_graph(
            simulation=simulation,
            documents=[document],
            cache_entry=cache_entry,
        )
        assert document in graph.documents.all()

    def test_materialized_at_set(
        self, simulation, document, cache_entry, chunk
    ):
        graph = materialize_graph(
            simulation=simulation,
            documents=[document],
            cache_entry=cache_entry,
        )
        assert graph.materialized_at is not None

    def test_unresolved_relation_endpoints_dropped(
        self, simulation, document, chunk
    ):
        bad_data = {
            "nodes": [{
                "entity_type": "person", "name": "Robespierre",
                "canonical_name": "robespierre", "description": "",
                "source_type": "document", "confidence": 0.9,
                "mention_count": 1, "attributes": {},
                "chunk_ids": [0], "embedding": [0.1] * 1024,
                "passage_excerpts": {},
            }],
            "relations": [{
                "source_entity_type": "person",
                "source_canonical_name": "robespierre",
                "target_entity_type": "institution",
                "target_canonical_name": "nonexistent club",
                "relation_type": "member_of",
                "description": "", "source_type": "document",
                "confidence": 0.9, "weight": 0.5,
                "temporal_start_iso": "", "temporal_start_year": None,
                "temporal_end_iso": "", "temporal_end_year": None,
                "chunk_ids": [0], "passage_excerpts": {},
            }],
            "unrecognized_entities": [], "unrecognized_relations": [],
            "stats": {},
        }
        cache = ExtractionCache.objects.create(
            cache_key="bad" + "0" * 61, documents_hash="m" * 64,
            ontology_version="v1", extraction_prompt_version="v1",
            llm_model="test", extracted_data=bad_data, stats={},
        )
        graph = materialize_graph(
            simulation=simulation, documents=[document], cache_entry=cache,
        )
        assert graph.nodes.count() == 1
        assert graph.relations.count() == 0  # dropped because target not found
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `docker compose -f docker-compose.local.yml run --rm web pytest epocha/apps/knowledge/tests/test_materialization.py -v`

Expected: ImportError.

- [ ] **Step 3: Implement materialization.py**

Create `epocha/apps/knowledge/materialization.py`:

```python
"""Graph materialization — turn cached extraction data into per-simulation rows.

The materialization step reads the JSON payload from ExtractionCache and
creates KnowledgeGraph, KnowledgeNode, KnowledgeRelation, and citation
rows scoped to a single simulation. Each simulation gets its own isolated
copy; the cache only holds the raw LLM extraction output.

The function runs inside a database transaction so the graph is either
fully created or not at all.
"""
from __future__ import annotations

import logging

from django.db import transaction
from django.utils import timezone

from .models import (
    ExtractionCache,
    KnowledgeChunk,
    KnowledgeDocument,
    KnowledgeGraph,
    KnowledgeNode,
    KnowledgeNodeCitation,
    KnowledgeRelation,
    KnowledgeRelationCitation,
)

logger = logging.getLogger(__name__)


def materialize_graph(
    *,
    simulation,
    documents: list[KnowledgeDocument],
    cache_entry: ExtractionCache,
) -> KnowledgeGraph:
    """Materialize a knowledge graph from cached extraction data.

    Creates all nodes, relations, and citations in a single atomic
    transaction. Nodes are indexed by (entity_type, canonical_name) to
    resolve relation endpoints without cross-type collisions.

    Relations with unresolved endpoints (source or target node not found)
    are logged and dropped rather than failing the transaction.
    """
    extracted_data = cache_entry.extracted_data

    with transaction.atomic():
        graph = KnowledgeGraph.objects.create(
            simulation=simulation,
            extraction_cache=cache_entry,
            status="materializing",
        )
        graph.documents.set(documents)

        # Build a chunk lookup for citations: {(document_id, chunk_index): chunk}
        doc_ids = [d.id for d in documents]
        chunks_by_index: dict[int, KnowledgeChunk] = {}
        for chunk in KnowledgeChunk.objects.filter(document_id__in=doc_ids):
            chunks_by_index[chunk.chunk_index] = chunk

        # Pass 1: create nodes
        node_index: dict[tuple[str, str], KnowledgeNode] = {}
        for node_data in extracted_data.get("nodes", []):
            node = KnowledgeNode.objects.create(
                graph=graph,
                entity_type=node_data["entity_type"],
                name=node_data["name"],
                canonical_name=node_data["canonical_name"],
                description=node_data.get("description", ""),
                attributes=node_data.get("attributes", {}),
                source_type=node_data["source_type"],
                confidence=node_data["confidence"],
                mention_count=node_data["mention_count"],
                embedding=node_data.get("embedding", [0.0] * 1024),
            )
            node_index[(node.entity_type, node.canonical_name)] = node

            # Create node citations
            for chunk_idx_str, excerpt in node_data.get("passage_excerpts", {}).items():
                chunk = chunks_by_index.get(int(chunk_idx_str))
                if chunk:
                    KnowledgeNodeCitation.objects.create(
                        node=node, chunk=chunk, passage_excerpt=excerpt,
                    )

        # Pass 2: create relations
        for rel_data in extracted_data.get("relations", []):
            source_key = (rel_data["source_entity_type"], rel_data["source_canonical_name"])
            target_key = (rel_data["target_entity_type"], rel_data["target_canonical_name"])
            source = node_index.get(source_key)
            target = node_index.get(target_key)

            if source is None or target is None:
                logger.warning(
                    "Dropping relation with unresolved endpoint: %s -> %s",
                    source_key, target_key,
                )
                continue

            rel = KnowledgeRelation.objects.create(
                graph=graph,
                source_node=source,
                target_node=target,
                relation_type=rel_data["relation_type"],
                description=rel_data.get("description", ""),
                source_type=rel_data["source_type"],
                confidence=rel_data["confidence"],
                weight=rel_data["weight"],
                temporal_start_iso=rel_data.get("temporal_start_iso", ""),
                temporal_start_year=rel_data.get("temporal_start_year"),
                temporal_end_iso=rel_data.get("temporal_end_iso", ""),
                temporal_end_year=rel_data.get("temporal_end_year"),
            )

            # Create relation citations
            for chunk_idx_str, excerpt in rel_data.get("passage_excerpts", {}).items():
                chunk = chunks_by_index.get(int(chunk_idx_str))
                if chunk:
                    KnowledgeRelationCitation.objects.create(
                        relation=rel, chunk=chunk, passage_excerpt=excerpt,
                    )

        graph.status = "ready"
        graph.materialized_at = timezone.now()
        graph.save(update_fields=["status", "materialized_at"])

    return graph
```

- [ ] **Step 4: Run materialization tests**

Run: `docker compose -f docker-compose.local.yml run --rm web pytest epocha/apps/knowledge/tests/test_materialization.py -v`

Expected: all PASS.

- [ ] **Step 5: Run full suite**

Run: `docker compose -f docker-compose.local.yml run --rm web pytest -q -m "not slow"`

Expected: all tests pass.

- [ ] **Step 6: Commit**

```
feat(knowledge): add graph materialization from cached extraction data

CHANGE: Add materialization.py that creates KnowledgeGraph, nodes,
relations, and citations in a single atomic transaction from the JSON
payload in ExtractionCache. Nodes are indexed by (entity_type,
canonical_name) to prevent cross-type collisions when resolving relation
endpoints. Unresolved endpoints are logged and dropped.
```

---

### Task 11: Celery orchestration task

**Files:**
- New: `epocha/apps/knowledge/tasks.py`
- New: `epocha/apps/knowledge/tests/test_tasks.py`

- [ ] **Step 1: Write the failing tests**

Create `epocha/apps/knowledge/tests/test_tasks.py`:

```python
"""Tests for the Celery orchestration task.

All external calls (LLM, embeddings) are mocked. The test verifies that
the task wires the pipeline stages together correctly.
"""
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from epocha.apps.knowledge.models import (
    ExtractionCache,
    KnowledgeDocument,
    KnowledgeGraph,
)
from epocha.apps.knowledge.tasks import extract_and_generate
from epocha.apps.simulation.models import Simulation
from epocha.apps.users.models import User

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "small_french_rev.txt"


@pytest.fixture
def user(db):
    return User.objects.create_user(email="task@epocha.dev", username="taskuser", password="pass1234")


@pytest.fixture
def simulation(user):
    return Simulation.objects.create(name="TaskTest", seed=42, owner=user)


@pytest.fixture
def mock_llm_and_embed():
    """Mock both LLM and embedding to avoid real API calls."""
    import json
    extraction_response = json.dumps({
        "entities": [{
            "entity_type": "person",
            "name": "Robespierre",
            "description": "A revolutionary",
            "passage_excerpt": "Robespierre was a member of the Jacobin Club.",
            "confidence": 0.9,
            "attributes": {"role": "deputy"},
        }],
        "relations": [],
    })

    with patch("epocha.apps.knowledge.extraction.get_llm_client") as mock_llm, \
         patch("epocha.apps.knowledge.merge.embed_texts") as mock_embed, \
         patch("epocha.apps.knowledge.embedding.get_embedding_model") as mock_model:

        client = MagicMock()
        client.complete.return_value = extraction_response
        client.get_model_name.return_value = "test-model"
        mock_llm.return_value = client

        mock_embed.return_value = [[0.1] * 1024]

        model = MagicMock()
        model.embed.return_value = iter([[0.1] * 1024])
        mock_model.return_value = model

        yield client


@pytest.mark.django_db(transaction=True)
class TestExtractAndGenerate:
    def test_full_pipeline_creates_graph(self, simulation, user, mock_llm_and_embed):
        raw_text = FIXTURE_PATH.read_text(encoding="utf-8")
        doc_data = [{
            "raw_text": raw_text,
            "title": "French Revolution",
            "mime_type": "text/plain",
            "original_filename": "test.txt",
        }]

        result = extract_and_generate(
            simulation_id=simulation.id,
            user_id=user.id,
            documents_data=doc_data,
            prompt="French Revolution 1789",
        )

        assert result["status"] == "ready"
        graph = KnowledgeGraph.objects.get(simulation=simulation)
        assert graph.status == "ready"
        assert graph.nodes.count() > 0

    def test_cache_hit_skips_extraction(self, simulation, user, mock_llm_and_embed):
        raw_text = "Some unique text for cache test."
        doc_data = [{
            "raw_text": raw_text,
            "title": "Cache Test",
            "mime_type": "text/plain",
            "original_filename": "cache.txt",
        }]

        # First run: extraction happens
        extract_and_generate(
            simulation_id=simulation.id,
            user_id=user.id,
            documents_data=doc_data,
            prompt="test",
        )
        call_count_first = mock_llm_and_embed.complete.call_count

        # Second run: same content, should hit cache
        sim2 = Simulation.objects.create(name="CacheTest2", seed=99, owner=user)
        extract_and_generate(
            simulation_id=sim2.id,
            user_id=user.id,
            documents_data=doc_data,
            prompt="test",
        )
        call_count_second = mock_llm_and_embed.complete.call_count

        # LLM should NOT have been called again
        assert call_count_second == call_count_first

    def test_error_sets_failed_status(self, simulation, user):
        with patch("epocha.apps.knowledge.tasks._run_ingestion") as mock_ingest:
            mock_ingest.side_effect = RuntimeError("ingestion failed")
            result = extract_and_generate(
                simulation_id=simulation.id,
                user_id=user.id,
                documents_data=[{"raw_text": "x", "title": "t", "mime_type": "text/plain", "original_filename": "f"}],
                prompt="test",
            )
        assert result["status"] == "failed"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `docker compose -f docker-compose.local.yml run --rm web pytest epocha/apps/knowledge/tests/test_tasks.py -v`

Expected: ImportError.

- [ ] **Step 3: Implement tasks.py**

Create `epocha/apps/knowledge/tasks.py`:

```python
"""Celery orchestration for the Knowledge Graph extraction pipeline.

The extract_and_generate function wires together all pipeline stages:
ingestion -> chunking -> embedding -> cache check -> extraction ->
merge -> cache persist -> materialize. It is designed to be called
both as a Celery task and synchronously (for testing).
"""
from __future__ import annotations

import logging
import time

from django.utils import timezone

from epocha.apps.llm_adapter.client import get_llm_client

from .cache import compute_cache_key, compute_documents_hash
from .chunking import split_text_into_chunks
from .embedding import embed_texts
from .extraction import extract_from_chunk
from .ingestion import ingest_document
from .materialization import materialize_graph
from .merge import merge_extraction_results
from .models import ExtractionCache, KnowledgeChunk, KnowledgeGraph
from .versions import (
    EXTRACTION_PROMPT_VERSION,
    ONTOLOGY_VERSION,
)

logger = logging.getLogger(__name__)


def _run_ingestion(user, documents_data):
    """Stage 1: ingest documents and return KnowledgeDocument instances."""
    docs = []
    for doc_data in documents_data:
        doc, _ = ingest_document(
            user=user,
            raw_text=doc_data["raw_text"],
            title=doc_data["title"],
            mime_type=doc_data["mime_type"],
            original_filename=doc_data["original_filename"],
        )
        docs.append(doc)
    return docs


def _run_chunking_and_embedding(documents):
    """Stages 2-3: chunk documents and embed chunks (idempotent)."""
    for doc in documents:
        if doc.chunks.exists():
            continue
        chunks = split_text_into_chunks(doc.normalized_text)
        if not chunks:
            continue
        texts = [c.text for c in chunks]
        vectors = embed_texts(texts)
        for chunk_result, vector in zip(chunks, vectors):
            KnowledgeChunk.objects.create(
                document=doc,
                chunk_index=chunk_result.chunk_index,
                text=chunk_result.text,
                start_char=chunk_result.start_char,
                end_char=chunk_result.end_char,
                embedding=vector,
            )


def _check_cache(documents):
    """Stage 4: check extraction cache. Returns (cache_key, cache_entry_or_None)."""
    docs_hash = compute_documents_hash([d.content_hash for d in documents])
    llm_model = get_llm_client().get_model_name()
    cache_key = compute_cache_key(
        documents_hash=docs_hash,
        ontology_version=ONTOLOGY_VERSION,
        extraction_prompt_version=EXTRACTION_PROMPT_VERSION,
        llm_model=llm_model,
    )
    entry = ExtractionCache.objects.filter(pk=cache_key).first()
    if entry:
        entry.hit_count += 1
        entry.last_hit_at = timezone.now()
        entry.save(update_fields=["hit_count", "last_hit_at"])
        logger.info("Extraction cache hit: %s", cache_key[:12])
    return cache_key, docs_hash, llm_model, entry


def _run_extraction(documents):
    """Stages 5-6: extract from all chunks and merge."""
    all_chunks = list(
        KnowledgeChunk.objects.filter(
            document__in=documents,
        ).order_by("document_id", "chunk_index")
    )
    results = []
    for chunk in all_chunks:
        result = extract_from_chunk(
            chunk_text=chunk.text,
            chunk_id=chunk.chunk_index,
        )
        results.append(result)

    return merge_extraction_results(results)


def _persist_cache(cache_key, docs_hash, llm_model, merged_data, elapsed):
    """Stage 7: persist extraction results to cache."""
    stats = merged_data.get("stats", {})
    stats["elapsed_seconds"] = round(elapsed, 1)
    ExtractionCache.objects.create(
        cache_key=cache_key,
        documents_hash=docs_hash,
        ontology_version=ONTOLOGY_VERSION,
        extraction_prompt_version=EXTRACTION_PROMPT_VERSION,
        llm_model=llm_model,
        extracted_data=merged_data,
        stats=stats,
    )
    return ExtractionCache.objects.get(pk=cache_key)


def extract_and_generate(
    *,
    simulation_id: int,
    user_id: int,
    documents_data: list[dict],
    prompt: str = "",
) -> dict:
    """Run the full extraction pipeline for a simulation.

    This function is the main entry point for the Knowledge Graph
    pipeline. It can be called directly (synchronous, for testing) or
    wrapped in a Celery task.

    Args:
        simulation_id: ID of the target Simulation.
        user_id: ID of the uploading User.
        documents_data: List of dicts with keys: raw_text, title,
            mime_type, original_filename.
        prompt: Optional free-text scenario hint for the world generator.

    Returns:
        Dict with "status" key ("ready" or "failed") and details.
    """
    from epocha.apps.simulation.models import Simulation
    from epocha.apps.users.models import User

    simulation = Simulation.objects.get(pk=simulation_id)
    user = User.objects.get(pk=user_id)

    try:
        # Stage 1: ingest
        documents = _run_ingestion(user, documents_data)

        # Stages 2-3: chunk and embed
        _run_chunking_and_embedding(documents)

        # Stage 4: cache check
        cache_key, docs_hash, llm_model, cache_entry = _check_cache(documents)

        if cache_entry is None:
            # Stages 5-6: extract and merge
            start_time = time.monotonic()
            merged_data = _run_extraction(documents)
            elapsed = time.monotonic() - start_time

            # Stage 7: persist to cache
            cache_entry = _persist_cache(
                cache_key, docs_hash, llm_model, merged_data, elapsed,
            )

        # Stage 8: materialize
        graph = materialize_graph(
            simulation=simulation,
            documents=documents,
            cache_entry=cache_entry,
        )

        logger.info(
            "Knowledge graph ready for simulation %d: %d nodes, %d relations",
            simulation.id, graph.nodes.count(), graph.relations.count(),
        )

        return {
            "status": "ready",
            "graph_id": graph.id,
            "nodes": graph.nodes.count(),
            "relations": graph.relations.count(),
        }

    except Exception as exc:
        logger.exception(
            "Knowledge graph extraction failed for simulation %d", simulation_id,
        )
        # Try to record the failure on the graph if one was created
        try:
            graph = KnowledgeGraph.objects.get(simulation=simulation)
            graph.status = "failed"
            graph.error_message = str(exc)
            graph.save(update_fields=["status", "error_message"])
        except KnowledgeGraph.DoesNotExist:
            pass

        return {"status": "failed", "error": str(exc)}
```

- [ ] **Step 4: Run task tests**

Run: `docker compose -f docker-compose.local.yml run --rm web pytest epocha/apps/knowledge/tests/test_tasks.py -v`

Expected: all PASS.

- [ ] **Step 5: Run full suite**

Run: `docker compose -f docker-compose.local.yml run --rm web pytest -q -m "not slow"`

Expected: all tests pass.

- [ ] **Step 6: Commit**

```
feat(knowledge): add Celery orchestration for extraction pipeline

CHANGE: Add tasks.py wiring all pipeline stages: ingestion, chunking,
embedding, cache check, per-chunk extraction, merge, cache persist,
and materialization. The extract_and_generate function is callable both
synchronously (tests) and as a Celery task (production). Cache hits
skip extraction entirely. Errors are captured in KnowledgeGraph.status
and error_message.
```

---

### Task 12: World generator integration

**Files:**
- Modify: `epocha/apps/world/generator.py`
- New: `epocha/apps/world/tests/test_generator_kg.py`

- [ ] **Step 1: Write the failing tests**

Create `epocha/apps/world/tests/test_generator_kg.py`:

```python
"""Tests for knowledge-graph-based world generation."""
import json
from unittest.mock import MagicMock, patch

import pytest
from django.contrib.gis.geos import Point, Polygon

from epocha.apps.agents.models import Agent
from epocha.apps.knowledge.models import (
    ExtractionCache,
    KnowledgeDocument,
    KnowledgeGraph,
    KnowledgeNode,
)
from epocha.apps.simulation.models import Simulation
from epocha.apps.users.models import User
from epocha.apps.world.generator import generate_world_from_prompt
from epocha.apps.world.models import Government, World, Zone


@pytest.fixture
def user(db):
    return User.objects.create_user(email="gen@epocha.dev", username="genuser", password="pass1234")


@pytest.fixture
def simulation(user):
    return Simulation.objects.create(name="GenTest", seed=42, owner=user)


@pytest.fixture
def knowledge_graph(simulation):
    cache = ExtractionCache.objects.create(
        cache_key="gen" + "0" * 61,
        documents_hash="gen" + "0" * 61,
        ontology_version="v1",
        extraction_prompt_version="v1",
        llm_model="test",
        extracted_data={},
        stats={},
    )
    graph = KnowledgeGraph.objects.create(
        simulation=simulation,
        extraction_cache=cache,
        status="ready",
    )
    # Add person nodes
    KnowledgeNode.objects.create(
        graph=graph, entity_type="person",
        name="Robespierre", canonical_name="robespierre",
        description="Leader of the Jacobins",
        source_type="document", confidence=0.9, mention_count=5,
        attributes={"role": "deputy"},
        embedding=[0.1] * 1024,
    )
    KnowledgeNode.objects.create(
        graph=graph, entity_type="person",
        name="Louis XVI", canonical_name="louis xvi",
        description="King of France",
        source_type="document", confidence=0.9, mention_count=3,
        attributes={"role": "king"},
        embedding=[0.2] * 1024,
    )
    # Add place nodes
    KnowledgeNode.objects.create(
        graph=graph, entity_type="place",
        name="Paris", canonical_name="paris",
        description="Capital of France",
        source_type="document", confidence=0.9, mention_count=4,
        attributes={},
        embedding=[0.3] * 1024,
    )
    # Add institution node
    KnowledgeNode.objects.create(
        graph=graph, entity_type="institution",
        name="National Assembly", canonical_name="national assembly",
        description="Legislative body",
        source_type="document", confidence=0.9, mention_count=2,
        attributes={},
        embedding=[0.4] * 1024,
    )
    # Add ideology node
    KnowledgeNode.objects.create(
        graph=graph, entity_type="ideology",
        name="Jacobinism", canonical_name="jacobinism",
        description="Radical revolutionary ideology",
        source_type="document", confidence=0.8, mention_count=2,
        attributes={},
        embedding=[0.5] * 1024,
    )
    return graph


@pytest.fixture
def mock_llm():
    with patch("epocha.apps.world.generator.get_llm_client") as mock:
        client = MagicMock()
        mock.return_value = client
        yield client


@pytest.mark.django_db
class TestGenerateFromKnowledgeGraph:
    def test_creates_agents_from_person_nodes(self, simulation, knowledge_graph, mock_llm):
        mock_llm.complete.return_value = json.dumps({
            "world": {"economy_level": "base", "stability_index": 0.5},
            "zones": [
                {"name": "Paris", "type": "urban", "resources": {}},
            ],
            "agents": [
                {
                    "name": "Robespierre",
                    "age": 31,
                    "role": "deputy",
                    "gender": "male",
                    "personality": {
                        "openness": 0.7,
                        "conscientiousness": 0.8,
                        "extraversion": 0.4,
                        "agreeableness": 0.3,
                        "neuroticism": 0.6,
                    },
                },
                {
                    "name": "Louis XVI",
                    "age": 35,
                    "role": "king",
                    "gender": "male",
                    "personality": {
                        "openness": 0.3,
                        "conscientiousness": 0.5,
                        "extraversion": 0.3,
                        "agreeableness": 0.6,
                        "neuroticism": 0.7,
                    },
                },
            ],
        })

        result = generate_world_from_prompt(
            "French Revolution 1789", simulation, knowledge_graph=knowledge_graph,
        )

        assert result["agents"] >= 2
        assert result["zones"] >= 1
        agents = Agent.objects.filter(simulation=simulation)
        assert agents.filter(name="Robespierre").exists()
        assert agents.filter(name="Louis XVI").exists()

    def test_prompt_contains_person_nodes(self, simulation, knowledge_graph, mock_llm):
        mock_llm.complete.return_value = json.dumps({
            "world": {"economy_level": "base", "stability_index": 0.5},
            "zones": [], "agents": [],
        })

        generate_world_from_prompt(
            "test", simulation, knowledge_graph=knowledge_graph,
        )

        call_args = mock_llm.complete.call_args
        prompt_text = call_args.kwargs.get("prompt", call_args.args[0] if call_args.args else "")
        assert "Robespierre" in prompt_text
        assert "Louis XVI" in prompt_text

    def test_links_person_nodes_to_agents(self, simulation, knowledge_graph, mock_llm):
        mock_llm.complete.return_value = json.dumps({
            "world": {"economy_level": "base", "stability_index": 0.5},
            "zones": [{"name": "Paris", "type": "urban", "resources": {}}],
            "agents": [
                {"name": "Robespierre", "age": 31, "role": "deputy", "gender": "male",
                 "personality": {"openness": 0.7}},
            ],
        })

        generate_world_from_prompt(
            "test", simulation, knowledge_graph=knowledge_graph,
        )

        rob_node = knowledge_graph.nodes.get(canonical_name="robespierre")
        rob_node.refresh_from_db()
        assert rob_node.linked_agent is not None
        assert rob_node.linked_agent.name == "Robespierre"

    def test_existing_flow_still_works_without_graph(self, simulation, mock_llm):
        mock_llm.complete.return_value = json.dumps({
            "world": {"economy_level": "base", "stability_index": 0.7},
            "zones": [{"name": "Village", "type": "rural", "resources": {}}],
            "agents": [
                {"name": "Farmer", "age": 30, "role": "farmer", "gender": "male",
                 "personality": {"openness": 0.5}},
            ],
        })

        result = generate_world_from_prompt("A small village", simulation)

        assert result["agents"] >= 1
        assert result["zones"] >= 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `docker compose -f docker-compose.local.yml run --rm web pytest epocha/apps/world/tests/test_generator_kg.py -v`

Expected: TypeError or similar (generate_world_from_prompt doesn't accept knowledge_graph yet).

- [ ] **Step 3: Modify generator.py**

In `epocha/apps/world/generator.py`:

1. Add `knowledge_graph=None` parameter to `generate_world_from_prompt`:

Change:
```python
def generate_world_from_prompt(prompt: str, simulation) -> dict:
```
to:
```python
def generate_world_from_prompt(prompt: str, simulation, knowledge_graph=None) -> dict:
```

2. Add the dispatch logic at the top of the function body:

```python
    if knowledge_graph is not None:
        return _generate_from_knowledge_graph(simulation, knowledge_graph, hint_prompt=prompt)
```

3. Rename the existing function body to `_generate_from_prompt_only` (extract into a private function) and call it from the main function when no graph is provided. OR, simpler: just add the `if` check at the top and leave the rest of the function as the fallback path.

4. Add the `_generate_from_knowledge_graph` function at the end of the file:

```python
def _generate_from_knowledge_graph(simulation, knowledge_graph, hint_prompt=""):
    """Generate a world using structured data from a knowledge graph.

    Builds the LLM prompt from the graph's nodes (persons, places,
    institutions, ideologies, events) and asks the LLM to generate
    personality profiles and zone configurations consistent with the
    historical context.

    After the LLM produces agents, links person nodes back to the
    created Agent instances.
    """
    client = get_llm_client()

    # Build structured context from graph nodes
    persons = list(knowledge_graph.nodes.filter(entity_type="person").order_by("-mention_count"))
    places = list(knowledge_graph.nodes.filter(entity_type="place").order_by("-mention_count"))
    institutions = list(knowledge_graph.nodes.filter(entity_type="institution").order_by("-mention_count"))
    ideologies = list(knowledge_graph.nodes.filter(entity_type="ideology").order_by("-mention_count"))
    events = list(knowledge_graph.nodes.filter(entity_type="event").order_by("-mention_count"))

    context_parts = []

    if persons:
        context_parts.append("PERSONS (will become agents):")
        for p in persons:
            role = p.attributes.get("role", "citizen")
            context_parts.append(f"- {p.name} (role: {role}): {p.description}")

    if places:
        context_parts.append("\nPLACES (will become zones):")
        for p in places:
            context_parts.append(f"- {p.name}: {p.description}")

    if institutions:
        context_parts.append("\nINSTITUTIONS:")
        for i in institutions:
            context_parts.append(f"- {i.name}: {i.description}")

    if ideologies:
        context_parts.append("\nIDEOLOGIES:")
        for i in ideologies:
            context_parts.append(f"- {i.name}: {i.description}")

    if events:
        context_parts.append("\nEVENTS:")
        for e in events:
            date = e.attributes.get("date", "")
            date_str = f" ({date})" if date else ""
            context_parts.append(f"- {e.name}{date_str}: {e.description}")

    graph_context = "\n".join(context_parts)

    user_prompt = f"""Based on the following historical knowledge graph, create a world for a civilization simulation.

{graph_context}

{f'Additional context: {hint_prompt}' if hint_prompt else ''}

{_WORLD_GENERATION_PROMPT}"""

    raw = client.complete(
        prompt=user_prompt,
        system_prompt="You are generating a world for a civilization simulation based on structured historical data.",
        temperature=0.8,
        max_tokens=4000,
    )

    try:
        data = json.loads(clean_llm_json(raw))
    except json.JSONDecodeError:
        logger.error("World generation from KG returned invalid JSON: %s", raw[:200])
        raise ValueError("LLM returned invalid JSON for world generation")

    # Create World
    world_data = data.get("world", {})
    world = World.objects.create(
        simulation=simulation,
        economy_level=world_data.get("economy_level", "base"),
        stability_index=world_data.get("stability_index", 0.7),
        global_wealth=1000.0,
        distance_scale=133.0,
        tick_duration_hours=24.0,
    )

    # Create Government
    Government.objects.create(
        simulation=simulation,
        government_type="democracy",
        formed_at_tick=0,
    )

    # Create Institutions
    from .models import Institution
    for inst_type in Institution.InstitutionType.values:
        Institution.objects.create(
            simulation=simulation,
            institution_type=inst_type,
            health=0.5, independence=0.5, funding=0.5,
        )

    # Create Zones
    zones_created = 0
    for idx, zone_data in enumerate(data.get("zones", [])):
        col = idx % 3
        row = idx // 3
        x_offset = col * 120
        y_offset = row * 120
        boundary = Polygon.from_bbox((x_offset, y_offset, x_offset + 100, y_offset + 100))
        center = Point(x_offset + 50, y_offset + 50)

        Zone.objects.create(
            world=world,
            name=zone_data["name"],
            zone_type=zone_data.get("type", "urban"),
            boundary=boundary,
            center=center,
            resources=zone_data.get("resources", {}),
        )
        zones_created += 1

    # Create Agents and link to person nodes
    agents_created = 0
    zones = list(Zone.objects.filter(world=world))
    person_node_lookup = {p.name.lower(): p for p in persons}

    for idx, agent_data in enumerate(data.get("agents", [])):
        agent_zone = zones[idx % len(zones)] if zones else None
        if agent_zone and agent_zone.center:
            cx, cy = agent_zone.center.x, agent_zone.center.y
            loc = Point(cx + random.uniform(-40, 40), cy + random.uniform(-40, 40))
        else:
            loc = None

        agent = Agent.objects.create(
            simulation=simulation,
            name=agent_data["name"],
            age=agent_data.get("age", 25),
            role=agent_data.get("role", "citizen"),
            gender=agent_data.get("gender", "male"),
            personality=agent_data.get("personality", {}),
            location=loc,
            zone=agent_zone,
        )
        agents_created += 1

        # Link person node to agent
        person_node = person_node_lookup.get(agent.name.lower())
        if person_node:
            person_node.linked_agent = agent
            person_node.save(update_fields=["linked_agent"])

    # Enrich agents
    from epocha.apps.agents.enrichment import enrich_simulation_agents
    enrichment_stats = enrich_simulation_agents(simulation)

    logger.info(
        "World generated from KG for simulation %d: %d zones, %d agents (%d enriched)",
        simulation.id, zones_created, agents_created, enrichment_stats["enriched"],
    )

    return {
        "world_id": world.id,
        "zones": zones_created,
        "agents": agents_created,
        "enriched": enrichment_stats["enriched"],
    }
```

- [ ] **Step 4: Run generator KG tests**

Run: `docker compose -f docker-compose.local.yml run --rm web pytest epocha/apps/world/tests/test_generator_kg.py -v`

Expected: all PASS.

- [ ] **Step 5: Run full test suite**

Run: `docker compose -f docker-compose.local.yml run --rm web pytest -q -m "not slow"`

Expected: all tests pass, including the existing generator tests (backward compatible).

- [ ] **Step 6: Commit**

```
feat(world): integrate knowledge graph into world generation

CHANGE: Extend generate_world_from_prompt with an optional
knowledge_graph parameter. When provided, the LLM prompt is built from
structured graph nodes (persons with roles, places, institutions,
ideologies, events) instead of raw text. After agent creation, person
nodes are linked back to their Agent instances via the linked_agent FK.
The existing prompt-only flow is unchanged when no graph is provided.
```

---

## Self-Review Summary

After completing Tasks 9-12 in this plan:

- 5 new graph-tier models with cross-graph validation and citation tracking
- Materialization logic creating isolated per-simulation rows from cached data
- Celery-callable orchestration wiring all 8 pipeline stages
- World generator extended with knowledge-graph-aware generation path
- Person nodes linked back to created Agents

**The full extraction-to-generation pipeline is now functional end-to-end:**
documents -> chunk -> embed -> cache check -> extract -> merge -> cache -> materialize -> generate agents

**What remains (Part 4):**
- Upload and status API endpoints
- Visualization JSON API
- Dashboard view with Sigma.js
- Cache cleanup management command

"""Knowledge Graph models -- shared tier.

The shared-tier models persist documents, chunks, and extraction cache
entries deduplicated across simulations and users. The per-simulation
graph-tier models (KnowledgeGraph, KnowledgeNode, KnowledgeRelation,
and their citation tables) are added in a later phase.
"""

from __future__ import annotations

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from pgvector.django import HnswIndex, VectorField

from epocha.apps.knowledge.versions import EMBEDDING_DIM


class KnowledgeDocument(models.Model):
    """Uploaded source document, deduplicated across users and simulations
    by content hash.

    Ownership and access control are decoupled from the document entity
    itself: two users uploading the same content share a single row via
    content_hash uniqueness, and their access is tracked through
    KnowledgeDocumentAccess.
    """

    title = models.CharField(max_length=255)
    mime_type = models.CharField(max_length=50)
    content_hash = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
        help_text="SHA-256 of normalized text content",
    )
    normalized_text = models.TextField()
    char_count = models.PositiveIntegerField()
    first_uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} ({self.char_count} chars)"


class KnowledgeDocumentAccess(models.Model):
    """Tracks which users have uploaded or accessed a specific document."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="knowledge_document_accesses",
    )
    document = models.ForeignKey(
        KnowledgeDocument,
        on_delete=models.CASCADE,
        related_name="accesses",
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)
    original_filename = models.CharField(max_length=255, blank=True)

    class Meta:
        unique_together = ("user", "document")
        indexes = [models.Index(fields=["user", "document"])]


class KnowledgeChunk(models.Model):
    """A text chunk of a document with its embedding, reused across graphs.

    Chunks are created once per document and persisted with their
    embedding. Re-running the pipeline on the same document is a no-op
    because chunks already exist (idempotent chunking).
    """

    document = models.ForeignKey(
        KnowledgeDocument, on_delete=models.CASCADE, related_name="chunks",
    )
    chunk_index = models.PositiveIntegerField()
    text = models.TextField()
    start_char = models.PositiveIntegerField()
    end_char = models.PositiveIntegerField()
    embedding = VectorField(dimensions=EMBEDDING_DIM)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("document", "chunk_index")
        ordering = ["document", "chunk_index"]
        indexes = [
            HnswIndex(
                name="chunk_embedding_hnsw",
                fields=["embedding"],
                m=16,
                ef_construction=64,
                opclasses=["vector_cosine_ops"],
            ),
        ]


class ExtractionCache(models.Model):
    """Cache of the expensive LLM extraction step.

    Keyed by the composite of documents hash, ontology version, extraction
    prompt version, and LLM model. Any change to these invalidates the
    cache automatically, preventing stale results from contaminating new
    simulations.
    """

    cache_key = models.CharField(max_length=64, primary_key=True)
    documents_hash = models.CharField(max_length=64, db_index=True)
    ontology_version = models.CharField(max_length=20)
    extraction_prompt_version = models.CharField(max_length=20)
    llm_model = models.CharField(max_length=100)
    extracted_data = models.JSONField(
        help_text="Raw extraction output: {nodes, relations, unrecognized_relations, ...}",
    )
    stats = models.JSONField(
        help_text="chunks_processed, llm_calls, elapsed_seconds, token counts",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    hit_count = models.PositiveIntegerField(default=0)
    last_hit_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"ExtractionCache[{self.cache_key[:12]}...] hits={self.hit_count}"


# ---------------------------------------------------------------------------
# Graph-tier models (per-simulation)
# ---------------------------------------------------------------------------


class KnowledgeGraph(models.Model):
    """Per-simulation knowledge graph built from extracted data.

    Each simulation has at most one active knowledge graph (enforced by
    the OneToOneField on simulation). The graph references the
    ExtractionCache entry it was built from, allowing cache reuse across
    simulations that share the same source documents and extraction
    parameters.

    The ``documents`` M2M tracks which KnowledgeDocument rows contributed
    to this graph, enabling provenance queries.
    """

    STATUS_CHOICES = [
        ("building", "Building"),
        ("ready", "Ready"),
        ("error", "Error"),
        ("stale", "Stale"),
    ]

    simulation = models.OneToOneField(
        "simulation.Simulation",
        on_delete=models.CASCADE,
        related_name="knowledge_graph",
    )
    extraction_cache = models.ForeignKey(
        ExtractionCache,
        on_delete=models.PROTECT,
        related_name="graphs",
        help_text="Cache entry this graph was materialised from",
    )
    documents = models.ManyToManyField(
        KnowledgeDocument,
        related_name="graphs",
        blank=True,
    )
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="building")
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    materialized_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when materialization completed successfully",
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"KnowledgeGraph[sim={self.simulation_id}, status={self.status}]"


class KnowledgeNode(models.Model):
    """A named entity in a knowledge graph.

    Nodes are typed (person, place, institution, etc.) and carry a
    vector embedding for semantic similarity search. The
    ``unique_together`` constraint on (graph, entity_type, canonical_name)
    prevents duplicate entities within the same graph while allowing the
    same canonical name to appear under different types (e.g. "Paris" as
    both a place and a concept).

    Optional ``linked_*`` foreign keys connect knowledge-graph entities to
    their simulation-model counterparts once the simulation is running.
    These are nullable because linking happens after graph construction.
    """

    ENTITY_TYPE_CHOICES = [
        ("person", "Person"),
        ("group", "Group"),
        ("institution", "Institution"),
        ("place", "Place"),
        ("event", "Event"),
        ("concept", "Concept"),
        ("resource", "Resource"),
        ("technology", "Technology"),
        ("law", "Law"),
        ("artifact", "Artifact"),
    ]

    SOURCE_TYPE_CHOICES = [
        ("document", "Extracted from document"),
        ("document_inferred", "Inferred from document context"),
    ]

    graph = models.ForeignKey(
        KnowledgeGraph,
        on_delete=models.CASCADE,
        related_name="nodes",
    )
    entity_type = models.CharField(max_length=20, choices=ENTITY_TYPE_CHOICES)
    name = models.CharField(max_length=255, help_text="Display name as found in source")
    canonical_name = models.CharField(
        max_length=255,
        db_index=True,
        help_text="Lowercased, deduplicated canonical form",
    )
    description = models.TextField(blank=True)
    aliases = models.JSONField(
        default=list,
        blank=True,
        help_text="Alternative names encountered in source documents",
    )
    attributes = models.JSONField(
        default=dict,
        blank=True,
        help_text="Structured attributes extracted from text (dates, roles, etc.)",
    )
    source_type = models.CharField(max_length=30, choices=SOURCE_TYPE_CHOICES)
    confidence = models.FloatField(
        help_text="Extraction confidence score, 0.0 to 1.0",
    )
    mention_count = models.PositiveIntegerField(
        default=1,
        help_text="Number of distinct mentions across chunks",
    )
    embedding = VectorField(dimensions=EMBEDDING_DIM)
    created_at = models.DateTimeField(auto_now_add=True)

    # Optional links to simulation-model entities (set after graph build)
    linked_agent = models.ForeignKey(
        "agents.Agent",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="knowledge_nodes",
    )
    linked_group = models.ForeignKey(
        "agents.Group",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="knowledge_nodes",
    )
    linked_zone = models.ForeignKey(
        "world.Zone",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="knowledge_nodes",
    )
    linked_institution = models.ForeignKey(
        "world.Institution",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="knowledge_nodes",
    )
    linked_event = models.ForeignKey(
        "simulation.Event",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="knowledge_nodes",
    )

    class Meta:
        unique_together = ("graph", "entity_type", "canonical_name")
        ordering = ["-confidence", "canonical_name"]
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

    def __str__(self):
        return f"{self.entity_type}:{self.canonical_name}"


class KnowledgeRelation(models.Model):
    """A directed, typed edge between two KnowledgeNode instances.

    Relations belong to a single graph. The ``clean()`` method enforces
    that both source and target nodes belong to the same graph, preventing
    cross-graph edges that would violate data isolation between
    simulations.

    Temporal fields are optional and record when a relation was active
    in the historical timeline described by the source documents. The ISO
    string preserves the original textual reference (e.g. "summer 1789")
    while the year integer enables range queries.
    """

    RELATION_TYPE_CHOICES = [
        ("ally_of", "Ally of"),
        ("rival_of", "Rival of"),
        ("member_of", "Member of"),
        ("leader_of", "Leader of"),
        ("located_in", "Located in"),
        ("born_in", "Born in"),
        ("died_in", "Died in"),
        ("participated_in", "Participated in"),
        ("caused", "Caused"),
        ("resulted_in", "Resulted in"),
        ("preceded", "Preceded"),
        ("succeeded", "Succeeded"),
        ("influenced", "Influenced"),
        ("opposed", "Opposed"),
        ("traded_with", "Traded with"),
        ("governed", "Governed"),
        ("created", "Created"),
        ("destroyed", "Destroyed"),
        ("related_to", "Related to"),
        ("unknown", "Unknown"),
    ]

    SOURCE_TYPE_CHOICES = [
        ("document", "Extracted from document"),
        ("document_inferred", "Inferred from document context"),
    ]

    graph = models.ForeignKey(
        KnowledgeGraph,
        on_delete=models.CASCADE,
        related_name="relations",
    )
    source_node = models.ForeignKey(
        KnowledgeNode,
        on_delete=models.CASCADE,
        related_name="outgoing_relations",
    )
    target_node = models.ForeignKey(
        KnowledgeNode,
        on_delete=models.CASCADE,
        related_name="incoming_relations",
    )
    relation_type = models.CharField(max_length=30, choices=RELATION_TYPE_CHOICES)
    description = models.TextField(blank=True)
    source_type = models.CharField(max_length=30, choices=SOURCE_TYPE_CHOICES)
    confidence = models.FloatField(
        help_text="Extraction confidence score, 0.0 to 1.0",
    )
    weight = models.FloatField(
        default=1.0,
        help_text="Edge weight for graph algorithms (higher = stronger relationship)",
    )

    # Temporal bounds (optional)
    temporal_start_iso = models.CharField(
        max_length=100,
        blank=True,
        help_text="Original temporal reference for start (e.g. 'summer 1789')",
    )
    temporal_start_year = models.IntegerField(
        null=True,
        blank=True,
        help_text="Parsed start year for range queries",
    )
    temporal_end_iso = models.CharField(
        max_length=100,
        blank=True,
        help_text="Original temporal reference for end",
    )
    temporal_end_year = models.IntegerField(
        null=True,
        blank=True,
        help_text="Parsed end year for range queries",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-confidence"]
        indexes = [
            models.Index(fields=["graph", "relation_type"]),
            models.Index(fields=["source_node", "target_node"]),
            models.Index(fields=["temporal_start_year", "temporal_end_year"]),
        ]

    def clean(self):
        """Validate that both nodes belong to the same graph as this relation."""
        super().clean()
        errors = {}
        if self.source_node_id and self.source_node.graph_id != self.graph_id:
            errors["source_node"] = "Source node belongs to a different graph."
        if self.target_node_id and self.target_node.graph_id != self.graph_id:
            errors["target_node"] = "Target node belongs to a different graph."
        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return f"{self.source_node} --[{self.relation_type}]--> {self.target_node}"


class KnowledgeNodeCitation(models.Model):
    """Links a KnowledgeNode to the KnowledgeChunk that supports it.

    Each (node, chunk) pair is unique: a node can cite many chunks, and
    a chunk can support many nodes, but the same pair appears only once.
    The ``passage_excerpt`` stores the relevant text fragment for display.
    """

    node = models.ForeignKey(
        KnowledgeNode,
        on_delete=models.CASCADE,
        related_name="citations",
    )
    chunk = models.ForeignKey(
        KnowledgeChunk,
        on_delete=models.CASCADE,
        related_name="node_citations",
    )
    passage_excerpt = models.TextField(
        help_text="Relevant text fragment from the chunk",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("node", "chunk")

    def __str__(self):
        return f"Citation[node={self.node_id}, chunk={self.chunk_id}]"


class KnowledgeRelationCitation(models.Model):
    """Links a KnowledgeRelation to the KnowledgeChunk that supports it.

    Same pattern as KnowledgeNodeCitation but for relations. A relation
    may be supported by multiple chunks, each storing its own excerpt.
    """

    relation = models.ForeignKey(
        KnowledgeRelation,
        on_delete=models.CASCADE,
        related_name="citations",
    )
    chunk = models.ForeignKey(
        KnowledgeChunk,
        on_delete=models.CASCADE,
        related_name="relation_citations",
    )
    passage_excerpt = models.TextField(
        help_text="Relevant text fragment from the chunk",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("relation", "chunk")

    def __str__(self):
        return f"Citation[relation={self.relation_id}, chunk={self.chunk_id}]"

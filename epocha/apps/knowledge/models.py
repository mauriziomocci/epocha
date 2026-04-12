"""Knowledge Graph models -- shared tier.

The shared-tier models persist documents, chunks, and extraction cache
entries deduplicated across simulations and users. The per-simulation
graph-tier models (KnowledgeGraph, KnowledgeNode, KnowledgeRelation,
and their citation tables) are added in a later phase.
"""

from __future__ import annotations

from django.conf import settings
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

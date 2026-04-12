"""Knowledge Graph models -- shared tier.

The shared-tier models persist documents, chunks, and extraction cache
entries deduplicated across simulations and users. The per-simulation
graph-tier models (KnowledgeGraph, KnowledgeNode, KnowledgeRelation,
and their citation tables) are added in a later phase.
"""

from __future__ import annotations

from django.conf import settings
from django.db import models


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

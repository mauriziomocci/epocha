"""Document ingestion service.

Responsible for Stage 1 of the extraction pipeline: text normalization,
hashing, deduplicated persistence, and access tracking.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from .models import KnowledgeDocument, KnowledgeDocumentAccess

_WHITESPACE_RE = re.compile(r"\s+")


def normalize_text(raw: str) -> str:
    """Normalize document text for hashing and storage.

    Steps: strip BOM, Unicode NFC, collapse whitespace to single spaces,
    trim. Normalization must be deterministic so the content hash is
    stable across uploads.
    """
    if not raw:
        return ""
    text = raw.lstrip("\ufeff")
    text = unicodedata.normalize("NFC", text)
    text = _WHITESPACE_RE.sub(" ", text)
    return text.strip()


def compute_content_hash(normalized: str) -> str:
    """Compute the SHA-256 hex digest of normalized text."""
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def ingest_document(
    *,
    user,
    raw_text: str,
    title: str,
    mime_type: str,
    original_filename: str,
) -> tuple[KnowledgeDocument, KnowledgeDocumentAccess]:
    """Ingest a document: normalize, hash, deduplicate, track access.

    Returns a tuple of (document, access). If another user has already
    uploaded the same content, the existing document is reused and a new
    access row is created for the current user.

    Raises:
        ValidationError: if the document exceeds the size cap.
    """
    normalized = normalize_text(raw_text)

    max_chars = getattr(settings, "EPOCHA_KG_MAX_DOCUMENT_CHARS", 500_000)
    if len(normalized) > max_chars:
        raise ValidationError(
            f"Document is too large: {len(normalized)} characters exceeds "
            f"the limit of {max_chars}."
        )

    content_hash = compute_content_hash(normalized)

    with transaction.atomic():
        try:
            with transaction.atomic():
                document = KnowledgeDocument.objects.create(
                    title=title,
                    mime_type=mime_type,
                    content_hash=content_hash,
                    normalized_text=normalized,
                    char_count=len(normalized),
                )
        except IntegrityError:
            document = KnowledgeDocument.objects.get(content_hash=content_hash)

        access, _ = KnowledgeDocumentAccess.objects.get_or_create(
            user=user,
            document=document,
            defaults={"original_filename": original_filename},
        )

    return document, access

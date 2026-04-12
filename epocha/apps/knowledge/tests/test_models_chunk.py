"""Tests for the KnowledgeChunk model."""
import pytest
from django.db import IntegrityError

from epocha.apps.knowledge.models import KnowledgeChunk, KnowledgeDocument


@pytest.fixture
def document(db):
    return KnowledgeDocument.objects.create(
        title="Test", mime_type="text/plain",
        content_hash="b" * 64,
        normalized_text="The Bastille was stormed on July 14, 1789.",
        char_count=42,
    )


@pytest.mark.django_db
class TestKnowledgeChunk:
    def test_create_chunk(self, document):
        embedding = [0.1] * 1024
        chunk = KnowledgeChunk.objects.create(
            document=document,
            chunk_index=0,
            text="The Bastille was stormed on July 14, 1789.",
            start_char=0,
            end_char=42,
            embedding=embedding,
        )
        assert chunk.document == document
        assert chunk.chunk_index == 0
        assert len(chunk.embedding) == 1024

    def test_chunk_index_unique_per_document(self, document):
        KnowledgeChunk.objects.create(
            document=document, chunk_index=0,
            text="a", start_char=0, end_char=1,
            embedding=[0.0] * 1024,
        )
        with pytest.raises(IntegrityError):
            KnowledgeChunk.objects.create(
                document=document, chunk_index=0,
                text="b", start_char=1, end_char=2,
                embedding=[0.0] * 1024,
            )

    def test_chunks_ordered_by_index(self, document):
        for i in range(3):
            KnowledgeChunk.objects.create(
                document=document, chunk_index=i,
                text=f"chunk {i}", start_char=i * 10, end_char=(i + 1) * 10,
                embedding=[float(i)] * 1024,
            )
        chunks = list(document.chunks.order_by("chunk_index"))
        assert [c.chunk_index for c in chunks] == [0, 1, 2]

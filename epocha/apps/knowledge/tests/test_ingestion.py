"""Tests for the ingestion service."""

from pathlib import Path

import pytest
from django.core.exceptions import ValidationError

from epocha.apps.knowledge.ingestion import (
    compute_content_hash,
    ingest_document,
    normalize_text,
)
from epocha.apps.knowledge.models import KnowledgeDocumentAccess
from epocha.apps.users.models import User

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "small_french_rev.txt"


@pytest.fixture
def user(db):
    return User.objects.create_user(
        email="ing@epocha.dev", username="inguser", password="pass1234"
    )


@pytest.fixture
def other_user(db):
    return User.objects.create_user(
        email="ing2@epocha.dev", username="inguser2", password="pass1234"
    )


class TestNormalizeText:
    def test_strips_bom(self):
        assert normalize_text("\ufeffhello") == "hello"

    def test_collapses_whitespace(self):
        assert normalize_text("hello   world\n\nfoo") == "hello world foo"

    def test_unicode_nfc(self):
        nfd = "cafe\u0301"
        result = normalize_text(nfd)
        assert result == "caf\u00e9"

    def test_trims(self):
        assert normalize_text("  hello  ") == "hello"


class TestComputeContentHash:
    def test_deterministic(self):
        h1 = compute_content_hash("hello world")
        h2 = compute_content_hash("hello world")
        assert h1 == h2

    def test_is_sha256_hex(self):
        h = compute_content_hash("hello")
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)

    def test_different_inputs_different_hashes(self):
        assert compute_content_hash("a") != compute_content_hash("b")


@pytest.mark.django_db
class TestIngestDocument:
    def test_ingest_fixture(self, user):
        raw_text = FIXTURE_PATH.read_text(encoding="utf-8")
        doc, access = ingest_document(
            user=user,
            raw_text=raw_text,
            title="French Revolution sample",
            mime_type="text/plain",
            original_filename="small_french_rev.txt",
        )
        assert doc.char_count > 0
        assert doc.content_hash is not None
        assert access.user == user
        assert access.document == doc

    def test_same_content_shared_across_users(self, user, other_user):
        raw_text = "some content"
        doc1, _ = ingest_document(
            user=user,
            raw_text=raw_text,
            title="doc",
            mime_type="text/plain",
            original_filename="a.txt",
        )
        doc2, _ = ingest_document(
            user=other_user,
            raw_text=raw_text,
            title="doc",
            mime_type="text/plain",
            original_filename="b.txt",
        )
        assert doc1.pk == doc2.pk
        assert KnowledgeDocumentAccess.objects.filter(document=doc1).count() == 2

    def test_document_size_limit(self, user, settings):
        settings.EPOCHA_KG_MAX_DOCUMENT_CHARS = 100
        oversized = "a" * 200
        with pytest.raises(ValidationError):
            ingest_document(
                user=user,
                raw_text=oversized,
                title="big",
                mime_type="text/plain",
                original_filename="big.txt",
            )

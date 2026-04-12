"""Tests for KnowledgeDocument and KnowledgeDocumentAccess models."""

import pytest
from django.db import IntegrityError

from epocha.apps.knowledge.models import (
    KnowledgeDocument,
    KnowledgeDocumentAccess,
)
from epocha.apps.users.models import User


@pytest.fixture
def user(db):
    return User.objects.create_user(
        email="kg@epocha.dev", username="kguser", password="pass1234"
    )


@pytest.fixture
def other_user(db):
    return User.objects.create_user(
        email="kg2@epocha.dev", username="kguser2", password="pass1234"
    )


@pytest.fixture
def document(db):
    return KnowledgeDocument.objects.create(
        title="Test Document",
        mime_type="text/plain",
        content_hash="a" * 64,
        normalized_text="some content",
        char_count=12,
    )


@pytest.mark.django_db
class TestKnowledgeDocument:
    def test_create_document(self, document):
        assert document.title == "Test Document"
        assert document.char_count == 12
        assert document.first_uploaded_at is not None

    def test_content_hash_unique(self, document):
        with pytest.raises(IntegrityError):
            KnowledgeDocument.objects.create(
                title="Duplicate",
                mime_type="text/plain",
                content_hash="a" * 64,
                normalized_text="different content",
                char_count=17,
            )

    def test_str_representation(self, document):
        assert "Test Document" in str(document)
        assert "12 chars" in str(document)


@pytest.mark.django_db
class TestKnowledgeDocumentAccess:
    def test_create_access(self, user, document):
        access = KnowledgeDocumentAccess.objects.create(
            user=user, document=document, original_filename="test.txt"
        )
        assert access.user == user
        assert access.document == document
        assert access.uploaded_at is not None

    def test_user_document_unique(self, user, document):
        KnowledgeDocumentAccess.objects.create(
            user=user, document=document, original_filename="test.txt"
        )
        with pytest.raises(IntegrityError):
            KnowledgeDocumentAccess.objects.create(
                user=user, document=document, original_filename="again.txt"
            )

    def test_two_users_share_one_document(self, user, other_user, document):
        KnowledgeDocumentAccess.objects.create(user=user, document=document)
        KnowledgeDocumentAccess.objects.create(user=other_user, document=document)
        assert KnowledgeDocumentAccess.objects.filter(document=document).count() == 2

    def test_document_survives_user_deletion(self, user, other_user, document):
        KnowledgeDocumentAccess.objects.create(user=user, document=document)
        KnowledgeDocumentAccess.objects.create(user=other_user, document=document)
        user_pk = user.pk
        user.delete()
        assert KnowledgeDocument.objects.filter(pk=document.pk).exists()
        assert KnowledgeDocumentAccess.objects.filter(
            document=document, user=other_user
        ).exists()
        assert not KnowledgeDocumentAccess.objects.filter(user_id=user_pk).exists()

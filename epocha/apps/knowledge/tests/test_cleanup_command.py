"""Tests for the cleanup_extraction_cache management command.

Verifies that stale, unused cache entries are deleted while recent
entries and entries referenced by active graphs are preserved.
"""
from __future__ import annotations

from datetime import timedelta
from io import StringIO

import pytest
from django.core.management import call_command
from django.utils import timezone

from epocha.apps.knowledge.models import ExtractionCache, KnowledgeGraph
from epocha.apps.simulation.models import Simulation
from epocha.apps.users.models import User


def _make_cache_entry(key_prefix, created_at=None, hit_count=0):
    """Helper to create an ExtractionCache entry with a specific age."""
    entry = ExtractionCache.objects.create(
        cache_key=(key_prefix * 64)[:64],
        documents_hash=("d" * 64),
        ontology_version="v1",
        extraction_prompt_version="v1",
        llm_model="test-model",
        extracted_data={"nodes": [], "relations": []},
        stats={"chunks_processed": 1},
        hit_count=hit_count,
    )
    if created_at is not None:
        # Update created_at directly (auto_now_add prevents normal assignment)
        ExtractionCache.objects.filter(pk=entry.pk).update(created_at=created_at)
        entry.refresh_from_db()
    return entry


@pytest.fixture
def user(db):
    return User.objects.create_user(email="cmd@epocha.dev", username="cmduser", password="pass1234")


@pytest.fixture
def simulation(user):
    return Simulation.objects.create(name="CmdTest", seed=42, owner=user)


@pytest.mark.django_db
class TestCleanupExtractionCache:

    def test_deletes_old_unused_entries(self, db):
        old_date = timezone.now() - timedelta(days=60)
        _make_cache_entry("old1", created_at=old_date, hit_count=0)

        out = StringIO()
        call_command("cleanup_extraction_cache", "--min-age-days=30", stdout=out)
        assert ExtractionCache.objects.count() == 0
        assert "Deleted 1" in out.getvalue()

    def test_keeps_recent_entries(self, db):
        # Entry created just now -- should not be deleted
        _make_cache_entry("new1")

        out = StringIO()
        call_command("cleanup_extraction_cache", "--min-age-days=30", stdout=out)
        assert ExtractionCache.objects.count() == 1
        assert "Deleted 0" in out.getvalue()

    def test_keeps_entries_with_high_hit_count(self, db):
        old_date = timezone.now() - timedelta(days=60)
        _make_cache_entry("pop1", created_at=old_date, hit_count=5)

        out = StringIO()
        call_command("cleanup_extraction_cache", "--min-age-days=30", "--max-hit-count=0", stdout=out)
        assert ExtractionCache.objects.count() == 1

    def test_keeps_entries_with_active_graphs(self, simulation):
        old_date = timezone.now() - timedelta(days=60)
        entry = _make_cache_entry("ref1", created_at=old_date, hit_count=0)
        KnowledgeGraph.objects.create(
            simulation=simulation,
            extraction_cache=entry,
            status="ready",
        )

        out = StringIO()
        call_command("cleanup_extraction_cache", "--min-age-days=30", stdout=out)
        assert ExtractionCache.objects.count() == 1

    def test_dry_run_does_not_delete(self, db):
        old_date = timezone.now() - timedelta(days=60)
        _make_cache_entry("dry1", created_at=old_date, hit_count=0)

        out = StringIO()
        call_command("cleanup_extraction_cache", "--min-age-days=30", "--dry-run", stdout=out)
        assert ExtractionCache.objects.count() == 1
        assert "Dry run" in out.getvalue()
        assert "1" in out.getvalue()

    def test_max_hit_count_parameter(self, db):
        old_date = timezone.now() - timedelta(days=60)
        _make_cache_entry("hc1", created_at=old_date, hit_count=2)

        out = StringIO()
        # Allow up to 3 hits for deletion
        call_command("cleanup_extraction_cache", "--min-age-days=30", "--max-hit-count=3", stdout=out)
        assert ExtractionCache.objects.count() == 0

"""Tests for the ExtractionCache model."""
import pytest
from django.db import IntegrityError

from epocha.apps.knowledge.models import ExtractionCache


@pytest.mark.django_db
class TestExtractionCache:
    def test_create_cache_entry(self):
        entry = ExtractionCache.objects.create(
            cache_key="c" * 64,
            documents_hash="d" * 64,
            ontology_version="v1",
            extraction_prompt_version="v1",
            llm_model="llama-3.3-70b-versatile",
            extracted_data={"nodes": [], "relations": []},
            stats={"chunks_processed": 0},
        )
        assert entry.cache_key == "c" * 64
        assert entry.hit_count == 0
        assert entry.last_hit_at is None

    def test_cache_key_primary_key(self):
        ExtractionCache.objects.create(
            cache_key="e" * 64,
            documents_hash="d" * 64,
            ontology_version="v1",
            extraction_prompt_version="v1",
            llm_model="m",
            extracted_data={},
            stats={},
        )
        with pytest.raises(IntegrityError):
            ExtractionCache.objects.create(
                cache_key="e" * 64,
                documents_hash="d" * 64,
                ontology_version="v2",
                extraction_prompt_version="v1",
                llm_model="m",
                extracted_data={},
                stats={},
            )

    def test_str_representation(self):
        entry = ExtractionCache.objects.create(
            cache_key="f" * 64,
            documents_hash="d" * 64,
            ontology_version="v1",
            extraction_prompt_version="v1",
            llm_model="m",
            extracted_data={},
            stats={},
        )
        assert "f" * 12 in str(entry)
        assert "hits=0" in str(entry)

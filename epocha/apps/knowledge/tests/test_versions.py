"""Smoke tests for the versions module."""
from epocha.apps.knowledge import versions


def test_ontology_version_is_string():
    assert isinstance(versions.ONTOLOGY_VERSION, str)
    assert versions.ONTOLOGY_VERSION != ""


def test_embedding_dim_is_1024():
    assert versions.EMBEDDING_DIM == 1024


def test_chunk_params_are_positive():
    assert versions.CHUNK_SIZE_TOKENS > 0
    assert versions.CHUNK_OVERLAP_TOKENS >= 0
    assert versions.CHUNK_OVERLAP_TOKENS < versions.CHUNK_SIZE_TOKENS


def test_dedup_threshold_in_range():
    assert 0.0 < versions.DEDUP_SIMILARITY_THRESHOLD < 1.0

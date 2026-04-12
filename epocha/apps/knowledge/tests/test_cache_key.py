"""Tests for the cache key builder."""
from epocha.apps.knowledge.cache import compute_documents_hash, compute_cache_key


class TestComputeDocumentsHash:
    def test_deterministic(self):
        hashes = ["a" * 64, "b" * 64]
        assert compute_documents_hash(hashes) == compute_documents_hash(hashes)

    def test_order_independent(self):
        h1 = compute_documents_hash(["a" * 64, "b" * 64])
        h2 = compute_documents_hash(["b" * 64, "a" * 64])
        assert h1 == h2

    def test_is_sha256(self):
        result = compute_documents_hash(["a" * 64])
        assert len(result) == 64
        assert all(c in "0123456789abcdef" for c in result)

    def test_empty_input(self):
        result = compute_documents_hash([])
        assert len(result) == 64


class TestComputeCacheKey:
    def test_deterministic(self):
        key1 = compute_cache_key(
            documents_hash="d" * 64,
            ontology_version="v1",
            extraction_prompt_version="v1",
            llm_model="llama-3.3-70b",
        )
        key2 = compute_cache_key(
            documents_hash="d" * 64,
            ontology_version="v1",
            extraction_prompt_version="v1",
            llm_model="llama-3.3-70b",
        )
        assert key1 == key2

    def test_changes_with_ontology_version(self):
        base = dict(documents_hash="d" * 64, extraction_prompt_version="v1", llm_model="m")
        k1 = compute_cache_key(ontology_version="v1", **base)
        k2 = compute_cache_key(ontology_version="v2", **base)
        assert k1 != k2

    def test_changes_with_prompt_version(self):
        base = dict(documents_hash="d" * 64, ontology_version="v1", llm_model="m")
        k1 = compute_cache_key(extraction_prompt_version="v1", **base)
        k2 = compute_cache_key(extraction_prompt_version="v2", **base)
        assert k1 != k2

    def test_changes_with_llm_model(self):
        base = dict(documents_hash="d" * 64, ontology_version="v1", extraction_prompt_version="v1")
        k1 = compute_cache_key(llm_model="m1", **base)
        k2 = compute_cache_key(llm_model="m2", **base)
        assert k1 != k2

    def test_changes_with_documents_hash(self):
        base = dict(ontology_version="v1", extraction_prompt_version="v1", llm_model="m")
        k1 = compute_cache_key(documents_hash="a" * 64, **base)
        k2 = compute_cache_key(documents_hash="b" * 64, **base)
        assert k1 != k2

    def test_is_sha256_hex(self):
        key = compute_cache_key(
            documents_hash="d" * 64, ontology_version="v1",
            extraction_prompt_version="v1", llm_model="m",
        )
        assert len(key) == 64
        assert all(c in "0123456789abcdef" for c in key)

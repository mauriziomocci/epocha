"""Extraction cache key builder.

The cache key is the SHA-256 of a deterministic composition of:
- documents_hash (itself the SHA-256 of the sorted document content hashes)
- ontology_version
- extraction_prompt_version
- llm_model

Any change to any of these fields invalidates the cache automatically.
"""
from __future__ import annotations

import hashlib
from typing import Iterable


def compute_documents_hash(content_hashes: Iterable[str]) -> str:
    """Compute the deterministic hash of a set of document content hashes.

    Input order is ignored: sorting guarantees that the same set of
    documents always produces the same aggregated hash.
    """
    sorted_hashes = sorted(content_hashes)
    joined = "\n".join(sorted_hashes)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()


def compute_cache_key(
    *,
    documents_hash: str,
    ontology_version: str,
    extraction_prompt_version: str,
    llm_model: str,
) -> str:
    """Compute the composite cache key from its four components."""
    key_material = (
        f"{documents_hash}|{ontology_version}|"
        f"{extraction_prompt_version}|{llm_model}"
    )
    return hashlib.sha256(key_material.encode("utf-8")).hexdigest()

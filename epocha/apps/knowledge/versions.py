"""Versioning constants for the Knowledge Graph extraction pipeline.

Any change to ONTOLOGY_VERSION, EXTRACTION_PROMPT_VERSION, or
EMBEDDING_MODEL invalidates the extraction cache automatically because
these values compose the cache key. Other constants affect behavior but
not cache identity.
"""
from __future__ import annotations

ONTOLOGY_VERSION = "v1"
EXTRACTION_PROMPT_VERSION = "v1"

EMBEDDING_MODEL = "BAAI/bge-m3"
EMBEDDING_DIM = 1024

CHUNK_SIZE_TOKENS = 800
CHUNK_OVERLAP_TOKENS = 150
CHUNK_CHARS_PER_TOKEN = 4

DEDUP_SIMILARITY_THRESHOLD = 0.85
EXTRACTION_TEMPERATURE = 0.1

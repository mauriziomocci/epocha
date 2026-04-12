"""Celery orchestration for the Knowledge Graph extraction pipeline.

Orchestrates the full extraction pipeline as a single callable function:
ingestion -> chunking -> embedding -> cache check -> extraction -> merge
-> cache persist -> materialize. Designed to be called synchronously in
tests or dispatched as a Celery task in production.

Each step is factored into a private helper so the main function reads
as a linear pipeline and individual stages are independently testable.
"""

from __future__ import annotations

import logging
import time

from django.utils import timezone

from epocha.apps.llm_adapter.client import get_llm_client

from .cache import compute_cache_key, compute_documents_hash
from .chunking import split_text_into_chunks
from .embedding import embed_texts
from .extraction import extract_from_chunk
from .ingestion import ingest_document
from .materialization import materialize_graph
from .merge import merge_extraction_results
from .models import ExtractionCache, KnowledgeChunk, KnowledgeGraph
from .versions import EXTRACTION_PROMPT_VERSION, ONTOLOGY_VERSION

logger = logging.getLogger(__name__)


def _run_ingestion(user, documents_data):
    """Ingest each raw document, deduplicating by content hash.

    Returns the list of KnowledgeDocument instances created or reused.
    """
    docs = []
    for doc_data in documents_data:
        doc, _ = ingest_document(
            user=user,
            raw_text=doc_data["raw_text"],
            title=doc_data["title"],
            mime_type=doc_data["mime_type"],
            original_filename=doc_data["original_filename"],
        )
        docs.append(doc)
    return docs


def _run_chunking_and_embedding(documents):
    """Split each document into chunks and compute embeddings.

    Idempotent: skips documents that already have chunks persisted.
    """
    for doc in documents:
        if doc.chunks.exists():
            continue
        chunks = split_text_into_chunks(doc.normalized_text)
        if not chunks:
            continue
        texts = [c.text for c in chunks]
        vectors = embed_texts(texts)
        for chunk_result, vector in zip(chunks, vectors):
            KnowledgeChunk.objects.create(
                document=doc,
                chunk_index=chunk_result.chunk_index,
                text=chunk_result.text,
                start_char=chunk_result.start_char,
                end_char=chunk_result.end_char,
                embedding=vector,
            )


def _check_cache(documents):
    """Check if extraction results are already cached.

    Computes the composite cache key from document hashes, ontology
    version, prompt version, and LLM model. If a cache entry exists,
    increments hit_count and returns it; otherwise returns None.

    Returns:
        Tuple of (cache_key, docs_hash, llm_model, cache_entry_or_None).
    """
    docs_hash = compute_documents_hash([d.content_hash for d in documents])
    llm_model = get_llm_client().get_model_name()
    cache_key = compute_cache_key(
        documents_hash=docs_hash,
        ontology_version=ONTOLOGY_VERSION,
        extraction_prompt_version=EXTRACTION_PROMPT_VERSION,
        llm_model=llm_model,
    )
    entry = ExtractionCache.objects.filter(pk=cache_key).first()
    if entry:
        entry.hit_count += 1
        entry.last_hit_at = timezone.now()
        entry.save(update_fields=["hit_count", "last_hit_at"])
        logger.info("Extraction cache hit: %s", cache_key[:12])
    return cache_key, docs_hash, llm_model, entry


def _run_extraction(documents):
    """Run per-chunk LLM extraction and merge results across all chunks.

    Processes chunks in document order, then merges and deduplicates
    entities and relations across the entire document set.
    """
    all_chunks = list(
        KnowledgeChunk.objects.filter(document__in=documents).order_by(
            "document_id", "chunk_index"
        )
    )
    results = []
    for chunk in all_chunks:
        result = extract_from_chunk(chunk_text=chunk.text, chunk_id=chunk.chunk_index)
        results.append(result)
    return merge_extraction_results(results)


def _persist_cache(cache_key, docs_hash, llm_model, merged_data, elapsed):
    """Persist merged extraction results to the cache.

    Stores the merged data, pipeline versions, and timing statistics
    so future runs with the same inputs skip extraction entirely.
    """
    stats = merged_data.get("stats", {})
    stats["elapsed_seconds"] = round(elapsed, 1)
    ExtractionCache.objects.create(
        cache_key=cache_key,
        documents_hash=docs_hash,
        ontology_version=ONTOLOGY_VERSION,
        extraction_prompt_version=EXTRACTION_PROMPT_VERSION,
        llm_model=llm_model,
        extracted_data=merged_data,
        stats=stats,
    )
    return ExtractionCache.objects.get(pk=cache_key)


def extract_and_generate(
    *,
    simulation_id: int,
    user_id: int,
    documents_data: list[dict],
    prompt: str = "",
) -> dict:
    """Run the full extraction pipeline for a simulation.

    Callable synchronously in tests or wrapped as a Celery task in
    production. The pipeline is idempotent at each stage: re-uploading
    the same document reuses the existing row, re-chunking is skipped
    if chunks exist, and re-extracting is skipped on cache hit.

    Args:
        simulation_id: Primary key of the target Simulation.
        user_id: Primary key of the user initiating the extraction.
        documents_data: List of dicts, each with keys "raw_text",
            "title", "mime_type", "original_filename".
        prompt: Optional user prompt (reserved for future use).

    Returns:
        Dict with "status" ("ready" or "failed") and graph metadata.
    """
    from epocha.apps.simulation.models import Simulation
    from epocha.apps.users.models import User

    simulation = Simulation.objects.get(pk=simulation_id)
    user = User.objects.get(pk=user_id)

    try:
        documents = _run_ingestion(user, documents_data)
        _run_chunking_and_embedding(documents)
        cache_key, docs_hash, llm_model, cache_entry = _check_cache(documents)

        if cache_entry is None:
            start_time = time.monotonic()
            merged_data = _run_extraction(documents)
            elapsed = time.monotonic() - start_time
            cache_entry = _persist_cache(
                cache_key,
                docs_hash,
                llm_model,
                merged_data,
                elapsed,
            )

        graph = materialize_graph(
            simulation=simulation,
            documents=documents,
            cache_entry=cache_entry,
        )

        logger.info(
            "Knowledge graph ready for simulation %d: %d nodes, %d relations",
            simulation.id,
            graph.nodes.count(),
            graph.relations.count(),
        )

        return {
            "status": "ready",
            "graph_id": graph.id,
            "nodes": graph.nodes.count(),
            "relations": graph.relations.count(),
        }

    except Exception as exc:
        logger.exception(
            "Knowledge graph extraction failed for simulation %d",
            simulation_id,
        )
        try:
            graph = KnowledgeGraph.objects.get(simulation=simulation)
            graph.status = "failed"
            graph.error_message = str(exc)
            graph.save(update_fields=["status", "error_message"])
        except KnowledgeGraph.DoesNotExist:
            pass
        return {"status": "failed", "error": str(exc)}

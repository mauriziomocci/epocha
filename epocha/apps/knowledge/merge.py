"""Cross-chunk merge and deduplication of extracted entities and relations.

After per-chunk LLM extraction, entities that refer to the same real-world
referent may appear in multiple chunks under slightly different surface forms.
This module resolves those duplicates through a two-stage process:

1. Exact canonical match: entities sharing entity_type and canonical_name
   are grouped together.
2. Embedding similarity: within each canonical group, embedding cosine
   similarity with single-linkage clustering merges entities above the
   DEDUP_SIMILARITY_THRESHOLD.

Merge rules for entity clusters follow a deterministic precedence:
- Name: highest mention_count, tie-break by longest name then alphabetical.
- Description: concatenation of unique descriptions (max 2000 chars).
- Confidence: maximum across cluster members.
- Mention count: sum across cluster members.
- Source type: "document" wins over "document_inferred".
- Attributes: merged by highest-confidence entity last (overwrites).
- Chunk IDs: union of all contributing chunks.

Relations are deduplicated by identity tuple (source, target, type, temporal
bounds), keeping maximum confidence and weight.
"""
from __future__ import annotations

import logging
import math
from collections import defaultdict

from .embedding import embed_texts
from .extraction import ExtractionResult
from .normalizer import normalize_canonical_name
from .versions import DEDUP_SIMILARITY_THRESHOLD

logger = logging.getLogger(__name__)

_MAX_DESCRIPTION_LENGTH = 2000


def _build_cosine_similarity_matrix(vectors: list[list[float]]) -> list[list[float]]:
    """Build an NxN cosine similarity matrix from a list of vectors.

    Pre-computes vector norms to avoid redundant sqrt calls. The matrix
    is symmetric, so only the upper triangle is computed explicitly.

    Args:
        vectors: list of N embedding vectors, each of dimension D.

    Returns:
        NxN matrix where element [i][j] is the cosine similarity between
        vectors[i] and vectors[j]. Diagonal elements are 1.0.
    """
    n = len(vectors)
    matrix = [[0.0] * n for _ in range(n)]
    norms = []
    for v in vectors:
        norm = math.sqrt(sum(x * x for x in v))
        norms.append(norm if norm > 0 else 1e-10)
    for i in range(n):
        matrix[i][i] = 1.0
        for j in range(i + 1, n):
            dot = sum(a * b for a, b in zip(vectors[i], vectors[j]))
            sim = dot / (norms[i] * norms[j])
            matrix[i][j] = sim
            matrix[j][i] = sim
    return matrix


def _single_linkage_clusters(similarity_matrix: list[list[float]], threshold: float) -> list[list[int]]:
    """Cluster indices using single-linkage on a similarity matrix.

    Uses union-find with path compression. Two indices are merged if their
    pairwise similarity meets or exceeds the threshold. Because single-linkage
    is transitive, A--B and B--C above threshold implies A, B, C in one cluster.

    Args:
        similarity_matrix: NxN symmetric cosine similarity matrix.
        threshold: minimum similarity to merge two indices.

    Returns:
        List of clusters, where each cluster is a list of integer indices.
    """
    n = len(similarity_matrix)
    parent = list(range(n))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x: int, y: int) -> None:
        rx, ry = find(x), find(y)
        if rx != ry:
            parent[rx] = ry

    for i in range(n):
        for j in range(i + 1, n):
            if similarity_matrix[i][j] >= threshold:
                union(i, j)

    clusters: dict[int, list[int]] = defaultdict(list)
    for i in range(n):
        clusters[find(i)].append(i)
    return list(clusters.values())


def _merge_entity_cluster(entities: list[dict]) -> dict:
    """Merge a cluster of entities representing the same real-world referent.

    Merge rules (deterministic):
    - name: entity with highest mention_count; ties broken by longest
      name, then alphabetical order.
    - description: unique descriptions concatenated with " | ", truncated
      to _MAX_DESCRIPTION_LENGTH characters.
    - confidence: maximum across all entities in the cluster.
    - mention_count: sum across all entities.
    - source_type: "document" wins if any entity has it.
    - attributes: merged dict, higher-confidence entity values overwrite.
    - chunk_ids: union of all contributing chunk IDs.

    Args:
        entities: list of entity dicts belonging to the same cluster.

    Returns:
        Single merged entity dict with a "chunk_ids" list replacing "chunk_id".
    """
    if len(entities) == 1:
        entity = entities[0]
        entity["chunk_ids"] = [entity.pop("chunk_id", 0)]
        return entity

    sorted_entities = sorted(entities, key=lambda e: (-e["mention_count"], -len(e["name"]), e["name"]))
    chosen = sorted_entities[0]

    seen_descriptions: set[str] = set()
    description_parts: list[str] = []
    for e in entities:
        desc = e.get("description", "").strip()
        if desc and desc not in seen_descriptions:
            seen_descriptions.add(desc)
            description_parts.append(desc)
    merged_description = " | ".join(description_parts)
    if len(merged_description) > _MAX_DESCRIPTION_LENGTH:
        merged_description = merged_description[:_MAX_DESCRIPTION_LENGTH]

    # Attributes merged so that higher-confidence entities overwrite lower ones.
    # Reverse-sort by confidence so the highest-confidence entity is applied last.
    entities_by_confidence = sorted(entities, key=lambda e: -e["confidence"])
    merged_attributes: dict = {}
    for e in reversed(entities_by_confidence):
        merged_attributes.update(e.get("attributes", {}))

    source_type = "document_inferred"
    if any(e["source_type"] == "document" for e in entities):
        source_type = "document"

    return {
        "entity_type": chosen["entity_type"],
        "name": chosen["name"],
        "canonical_name": normalize_canonical_name(chosen["name"]),
        "description": merged_description,
        "source_type": source_type,
        "confidence": max(e["confidence"] for e in entities),
        "mention_count": sum(e["mention_count"] for e in entities),
        "attributes": merged_attributes,
        "chunk_ids": list({e.get("chunk_id", 0) for e in entities}),
    }


def _deduplicate_relations(relations: list[dict]) -> list[dict]:
    """Deduplicate relations by identity tuple.

    Relations sharing the same (source_canonical_name, source_entity_type,
    target_canonical_name, target_entity_type, relation_type, temporal_start_year,
    temporal_end_year) are considered duplicates. The surviving relation keeps
    the maximum confidence and weight, and collects all chunk IDs.

    Args:
        relations: list of relation dicts, each with a "chunk_id" field.

    Returns:
        Deduplicated list of relation dicts, each with "chunk_ids" replacing "chunk_id".
    """
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for rel in relations:
        key = (
            rel["source_canonical_name"], rel["source_entity_type"],
            rel["target_canonical_name"], rel["target_entity_type"],
            rel["relation_type"],
            rel.get("temporal_start_year"), rel.get("temporal_end_year"),
        )
        groups[key].append(rel)

    deduped = []
    for group in groups.values():
        best = max(group, key=lambda r: r["confidence"])
        best["confidence"] = max(r["confidence"] for r in group)
        best["weight"] = max(r["weight"] for r in group)
        best["chunk_ids"] = list({r.get("chunk_id", 0) for r in group})
        deduped.append(best)
    return deduped


def merge_extraction_results(results: list[ExtractionResult]) -> dict:
    """Merge multiple per-chunk extraction results into a single knowledge graph.

    Processing pipeline:
    1. Collect all entities, relations, and unrecognized items from all chunks.
    2. Group entities by entity_type, then by canonical_name.
    3. For canonical groups with multiple members, compute embedding similarity
       and cluster with single-linkage at DEDUP_SIMILARITY_THRESHOLD.
    4. Merge each cluster into a single entity node.
    5. Deduplicate relations by identity tuple.
    6. Package results with merge statistics.

    Args:
        results: list of ExtractionResult from per-chunk extraction.

    Returns:
        Dict with keys: "nodes", "relations", "unrecognized_entities",
        "unrecognized_relations", "stats".
    """
    all_entities: list[dict] = []
    all_relations: list[dict] = []
    all_unrecognized_entities: list[dict] = []
    all_unrecognized_relations: list[dict] = []

    for result in results:
        all_entities.extend(result.entities)
        all_relations.extend(result.relations)
        all_unrecognized_entities.extend(result.unrecognized_entities)
        all_unrecognized_relations.extend(result.unrecognized_relations)

    nodes_before_merge = len(all_entities)
    relations_before_merge = len(all_relations)

    by_type: dict[str, list[dict]] = defaultdict(list)
    for entity in all_entities:
        by_type[entity["entity_type"]].append(entity)

    merged_nodes: list[dict] = []

    for entity_type, entities in by_type.items():
        if len(entities) <= 1:
            for e in entities:
                e["chunk_ids"] = [e.pop("chunk_id", 0)]
            merged_nodes.extend(entities)
            continue

        by_canonical: dict[str, list[dict]] = defaultdict(list)
        for e in entities:
            by_canonical[e["canonical_name"]].append(e)

        for canonical_name, group in by_canonical.items():
            if len(group) == 1:
                merged_nodes.append(_merge_entity_cluster(group))
                continue

            texts = [f"{e['name']} {e['description']}" for e in group]
            vectors = embed_texts(texts)

            if not vectors or len(vectors) != len(group):
                for e in group:
                    merged_nodes.append(_merge_entity_cluster([e]))
                continue

            sim_matrix = _build_cosine_similarity_matrix(vectors)
            clusters = _single_linkage_clusters(sim_matrix, DEDUP_SIMILARITY_THRESHOLD)

            for cluster_indices in clusters:
                cluster_entities = [group[i] for i in cluster_indices]
                merged_nodes.append(_merge_entity_cluster(cluster_entities))

    merged_relations = _deduplicate_relations(all_relations)

    return {
        "nodes": merged_nodes,
        "relations": merged_relations,
        "unrecognized_entities": all_unrecognized_entities,
        "unrecognized_relations": all_unrecognized_relations,
        "stats": {
            "chunks_processed": len(results),
            "nodes_before_merge": nodes_before_merge,
            "nodes_after_merge": len(merged_nodes),
            "relations_before_merge": relations_before_merge,
            "relations_after_merge": len(merged_relations),
        },
    }

"""Graph materialization -- turn cached extraction data into per-simulation rows.

Reads the JSON payload stored in an ExtractionCache entry and creates
KnowledgeGraph, KnowledgeNode, KnowledgeRelation, and their citation
rows, all scoped to a single simulation. The entire operation runs
inside an atomic transaction for all-or-nothing semantics.

Nodes are indexed by (entity_type, canonical_name) to resolve relation
endpoints without cross-type collisions (e.g. "paris" can exist as both
a place and a concept). Relations whose source or target cannot be
resolved are logged and silently dropped.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from django.db import transaction
from django.utils import timezone

from epocha.apps.knowledge.models import (
    ExtractionCache,
    KnowledgeChunk,
    KnowledgeDocument,
    KnowledgeGraph,
    KnowledgeNode,
    KnowledgeNodeCitation,
    KnowledgeRelation,
    KnowledgeRelationCitation,
)

if TYPE_CHECKING:
    from epocha.apps.simulation.models import Simulation

logger = logging.getLogger(__name__)


def materialize_graph(
    *,
    simulation: Simulation,
    documents: list[KnowledgeDocument],
    cache_entry: ExtractionCache,
) -> KnowledgeGraph:
    """Materialize a knowledge graph from cached extraction data.

    Creates graph-tier rows (KnowledgeGraph, KnowledgeNode,
    KnowledgeRelation, and their citations) from the JSON payload in
    *cache_entry*. All writes happen inside a single atomic transaction;
    if any step fails, the entire operation is rolled back.

    Args:
        simulation: The simulation this graph belongs to.
        documents: Source KnowledgeDocument instances that contributed
            to the extraction. Used for document M2M and chunk lookup.
        cache_entry: The ExtractionCache row whose ``extracted_data``
            contains the nodes, relations, and passage excerpts to
            materialize.

    Returns:
        The newly created KnowledgeGraph with status "ready".

    Raises:
        IntegrityError: If the extracted data contains duplicate
            (entity_type, canonical_name) pairs, violating the
            unique_together constraint. The transaction is rolled back.
    """
    extracted_data = cache_entry.extracted_data

    with transaction.atomic():
        graph = KnowledgeGraph.objects.create(
            simulation=simulation,
            extraction_cache=cache_entry,
            status="building",
        )
        graph.documents.set(documents)

        # Build chunk lookup keyed by (document_id, chunk_index) so that
        # citations can reference the correct chunk row. When documents
        # share chunk indices, the document_id qualifier prevents
        # collisions.
        doc_ids = [d.pk for d in documents]
        chunks_qs = KnowledgeChunk.objects.filter(document_id__in=doc_ids)
        chunks_by_index: dict[int, KnowledgeChunk] = {
            c.chunk_index: c for c in chunks_qs
        }

        # -- Pass 1: create nodes ----------------------------------------
        node_index: dict[tuple[str, str], KnowledgeNode] = {}

        for node_data in extracted_data.get("nodes", []):
            node = KnowledgeNode.objects.create(
                graph=graph,
                entity_type=node_data["entity_type"],
                name=node_data["name"],
                canonical_name=node_data["canonical_name"],
                description=node_data.get("description", ""),
                attributes=node_data.get("attributes", {}),
                source_type=node_data["source_type"],
                confidence=node_data["confidence"],
                mention_count=node_data["mention_count"],
                embedding=node_data.get("embedding", [0.0] * 1024),
            )
            node_index[(node.entity_type, node.canonical_name)] = node

            _create_node_citations(node, node_data, chunks_by_index)

        # -- Pass 2: create relations ------------------------------------
        for rel_data in extracted_data.get("relations", []):
            source_key = (
                rel_data["source_entity_type"],
                rel_data["source_canonical_name"],
            )
            target_key = (
                rel_data["target_entity_type"],
                rel_data["target_canonical_name"],
            )
            source_node = node_index.get(source_key)
            target_node = node_index.get(target_key)

            if source_node is None or target_node is None:
                logger.warning(
                    "Dropping relation '%s' with unresolved endpoint: "
                    "source=%s (found=%s), target=%s (found=%s)",
                    rel_data.get("relation_type", "unknown"),
                    source_key,
                    source_node is not None,
                    target_key,
                    target_node is not None,
                )
                continue

            relation = KnowledgeRelation.objects.create(
                graph=graph,
                source_node=source_node,
                target_node=target_node,
                relation_type=rel_data["relation_type"],
                description=rel_data.get("description", ""),
                source_type=rel_data["source_type"],
                confidence=rel_data["confidence"],
                weight=rel_data["weight"],
                temporal_start_iso=rel_data.get("temporal_start_iso", ""),
                temporal_start_year=rel_data.get("temporal_start_year"),
                temporal_end_iso=rel_data.get("temporal_end_iso", ""),
                temporal_end_year=rel_data.get("temporal_end_year"),
            )

            _create_relation_citations(relation, rel_data, chunks_by_index)

        # -- Finalize ---------------------------------------------------
        graph.status = "ready"
        graph.materialized_at = timezone.now()
        graph.save(update_fields=["status", "materialized_at"])

    return graph


def _create_node_citations(
    node: KnowledgeNode,
    node_data: dict,
    chunks_by_index: dict[int, KnowledgeChunk],
) -> None:
    """Create KnowledgeNodeCitation rows linking *node* to its source chunks."""
    for chunk_idx_str, excerpt in node_data.get("passage_excerpts", {}).items():
        chunk = chunks_by_index.get(int(chunk_idx_str))
        if chunk is None:
            logger.warning(
                "Node '%s': chunk index %s not found, skipping citation",
                node.canonical_name,
                chunk_idx_str,
            )
            continue
        KnowledgeNodeCitation.objects.create(
            node=node,
            chunk=chunk,
            passage_excerpt=excerpt,
        )


def _create_relation_citations(
    relation: KnowledgeRelation,
    rel_data: dict,
    chunks_by_index: dict[int, KnowledgeChunk],
) -> None:
    """Create KnowledgeRelationCitation rows linking *relation* to its source chunks."""
    for chunk_idx_str, excerpt in rel_data.get("passage_excerpts", {}).items():
        chunk = chunks_by_index.get(int(chunk_idx_str))
        if chunk is None:
            logger.warning(
                "Relation '%s': chunk index %s not found, skipping citation",
                relation.relation_type,
                chunk_idx_str,
            )
            continue
        KnowledgeRelationCitation.objects.create(
            relation=relation,
            chunk=chunk,
            passage_excerpt=excerpt,
        )

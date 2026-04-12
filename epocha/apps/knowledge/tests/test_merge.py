"""Tests for the merge and deduplication logic."""
from unittest.mock import patch

import pytest

from epocha.apps.knowledge.merge import (
    merge_extraction_results,
    _merge_entity_cluster,
    _deduplicate_relations,
    _build_cosine_similarity_matrix,
    _single_linkage_clusters,
)
from epocha.apps.knowledge.extraction import ExtractionResult


def _entity(name, entity_type="person", description="", confidence=0.9, mention_count=1,
            source_type="document", chunk_id=0, passage_excerpt="passage", attributes=None):
    from epocha.apps.knowledge.normalizer import normalize_canonical_name
    return {
        "entity_type": entity_type, "name": name,
        "canonical_name": normalize_canonical_name(name),
        "description": description, "passage_excerpt": passage_excerpt,
        "source_type": source_type, "confidence": confidence,
        "mention_count": mention_count, "attributes": attributes or {},
        "chunk_id": chunk_id,
    }


def _relation(source, target, rel_type="member_of", source_type="person",
              target_type="institution", chunk_id=0, confidence=0.9, weight=0.5):
    from epocha.apps.knowledge.normalizer import normalize_canonical_name
    return {
        "source_name": source, "source_entity_type": source_type,
        "source_canonical_name": normalize_canonical_name(source),
        "target_name": target, "target_entity_type": target_type,
        "target_canonical_name": normalize_canonical_name(target),
        "relation_type": rel_type, "description": "",
        "passage_excerpt": f"{source} and {target}",
        "source_type": "document", "confidence": confidence, "weight": weight,
        "temporal_start_iso": "", "temporal_start_year": None,
        "temporal_end_iso": "", "temporal_end_year": None,
        "chunk_id": chunk_id,
    }


class TestBuildCosineSimilarityMatrix:
    def test_identical_vectors_similarity_one(self):
        vectors = [[1.0, 0.0, 0.0], [1.0, 0.0, 0.0]]
        matrix = _build_cosine_similarity_matrix(vectors)
        assert abs(matrix[0][1] - 1.0) < 0.001

    def test_orthogonal_vectors_similarity_zero(self):
        vectors = [[1.0, 0.0], [0.0, 1.0]]
        matrix = _build_cosine_similarity_matrix(vectors)
        assert abs(matrix[0][1]) < 0.001

    def test_matrix_is_symmetric(self):
        vectors = [[1.0, 0.5], [0.5, 1.0], [0.3, 0.7]]
        matrix = _build_cosine_similarity_matrix(vectors)
        for i in range(3):
            for j in range(3):
                assert abs(matrix[i][j] - matrix[j][i]) < 0.001


class TestSingleLinkageClusters:
    def test_above_threshold_merged(self):
        matrix = [[1.0, 0.95, 0.1], [0.95, 1.0, 0.1], [0.1, 0.1, 1.0]]
        clusters = _single_linkage_clusters(matrix, threshold=0.85)
        assert len(clusters) == 2
        merged = [c for c in clusters if len(c) > 1]
        assert len(merged) == 1
        assert set(merged[0]) == {0, 1}

    def test_below_threshold_separate(self):
        matrix = [[1.0, 0.5], [0.5, 1.0]]
        clusters = _single_linkage_clusters(matrix, threshold=0.85)
        assert len(clusters) == 2

    def test_transitive_merge(self):
        matrix = [[1.0, 0.90, 0.5], [0.90, 1.0, 0.90], [0.5, 0.90, 1.0]]
        clusters = _single_linkage_clusters(matrix, threshold=0.85)
        assert len(clusters) == 1
        assert set(clusters[0]) == {0, 1, 2}


class TestMergeEntityCluster:
    def test_picks_highest_mention_count_name(self):
        entities = [
            _entity("M. Robespierre", mention_count=1),
            _entity("Maximilien Robespierre", mention_count=5),
            _entity("Robespierre", mention_count=3),
        ]
        merged = _merge_entity_cluster(entities)
        assert merged["name"] == "Maximilien Robespierre"

    def test_tie_break_by_longest_name(self):
        entities = [
            _entity("Robespierre", mention_count=3),
            _entity("Maximilien Robespierre", mention_count=3),
        ]
        merged = _merge_entity_cluster(entities)
        assert merged["name"] == "Maximilien Robespierre"

    def test_sums_mention_counts(self):
        entities = [_entity("Robespierre", mention_count=3), _entity("M. Robespierre", mention_count=2)]
        merged = _merge_entity_cluster(entities)
        assert merged["mention_count"] == 5

    def test_takes_max_confidence(self):
        entities = [_entity("Robespierre", confidence=0.7), _entity("Robespierre", confidence=0.95)]
        merged = _merge_entity_cluster(entities)
        assert merged["confidence"] == 0.95

    def test_document_source_type_wins(self):
        entities = [
            _entity("Robespierre", source_type="document_inferred"),
            _entity("Robespierre", source_type="document"),
        ]
        merged = _merge_entity_cluster(entities)
        assert merged["source_type"] == "document"

    def test_collects_all_chunk_ids(self):
        entities = [_entity("Robespierre", chunk_id=0), _entity("Robespierre", chunk_id=3), _entity("Robespierre", chunk_id=7)]
        merged = _merge_entity_cluster(entities)
        assert set(merged["chunk_ids"]) == {0, 3, 7}

    def test_concatenates_descriptions(self):
        entities = [_entity("Robespierre", description="A deputy"), _entity("Robespierre", description="Leader of the Jacobins")]
        merged = _merge_entity_cluster(entities)
        assert "A deputy" in merged["description"]
        assert "Leader of the Jacobins" in merged["description"]


class TestDeduplicateRelations:
    def test_identical_relations_merged(self):
        relations = [
            _relation("Robespierre", "Jacobin Club", confidence=0.8, weight=0.5),
            _relation("Robespierre", "Jacobin Club", confidence=0.9, weight=0.7),
        ]
        deduped = _deduplicate_relations(relations)
        assert len(deduped) == 1
        assert deduped[0]["confidence"] == 0.9
        assert deduped[0]["weight"] == 0.7

    def test_different_relation_types_kept_separate(self):
        relations = [
            _relation("Robespierre", "Jacobin Club", rel_type="member_of"),
            _relation("Robespierre", "Jacobin Club", rel_type="leader_of"),
        ]
        deduped = _deduplicate_relations(relations)
        assert len(deduped) == 2

    def test_different_targets_kept_separate(self):
        relations = [
            _relation("Robespierre", "Jacobin Club"),
            _relation("Robespierre", "National Assembly"),
        ]
        deduped = _deduplicate_relations(relations)
        assert len(deduped) == 2

    def test_collects_chunk_ids(self):
        relations = [
            _relation("Robespierre", "Jacobin Club", chunk_id=0),
            _relation("Robespierre", "Jacobin Club", chunk_id=5),
        ]
        deduped = _deduplicate_relations(relations)
        assert set(deduped[0]["chunk_ids"]) == {0, 5}


class TestMergeExtractionResults:
    @patch("epocha.apps.knowledge.merge.embed_texts")
    def test_merges_duplicate_entities_across_chunks(self, mock_embed):
        mock_embed.return_value = [[0.9] * 1024, [0.9] * 1024]
        results = [
            ExtractionResult(chunk_id=0, entities=[_entity("Robespierre", chunk_id=0, description="a deputy")], relations=[]),
            ExtractionResult(chunk_id=1, entities=[_entity("Robespierre", chunk_id=1, description="Jacobin leader")], relations=[]),
        ]
        merged = merge_extraction_results(results)
        person_nodes = [n for n in merged["nodes"] if n["entity_type"] == "person"]
        assert len(person_nodes) == 1
        assert person_nodes[0]["mention_count"] == 2

    @patch("epocha.apps.knowledge.merge.embed_texts")
    def test_different_entities_not_merged(self, mock_embed):
        mock_embed.return_value = [[0.9] * 1024, [0.1] * 1024]
        results = [
            ExtractionResult(chunk_id=0, entities=[_entity("Robespierre", chunk_id=0)], relations=[]),
            ExtractionResult(chunk_id=1, entities=[_entity("Danton", chunk_id=1)], relations=[]),
        ]
        merged = merge_extraction_results(results)
        person_nodes = [n for n in merged["nodes"] if n["entity_type"] == "person"]
        assert len(person_nodes) == 2

    @patch("epocha.apps.knowledge.merge.embed_texts")
    def test_collects_unrecognized(self, mock_embed):
        mock_embed.return_value = []
        results = [
            ExtractionResult(chunk_id=0, entities=[], relations=[],
                           unrecognized_entities=[{"entity_type": "dragon", "name": "Smaug"}],
                           unrecognized_relations=[{"relation_type": "breathes_fire"}]),
        ]
        merged = merge_extraction_results(results)
        assert len(merged["unrecognized_entities"]) == 1
        assert len(merged["unrecognized_relations"]) == 1

    @patch("epocha.apps.knowledge.merge.embed_texts")
    def test_output_has_expected_keys(self, mock_embed):
        mock_embed.return_value = [[0.5] * 1024]
        results = [
            ExtractionResult(chunk_id=0,
                           entities=[_entity("Robespierre", chunk_id=0)],
                           relations=[_relation("Robespierre", "Jacobin Club", chunk_id=0)]),
        ]
        merged = merge_extraction_results(results)
        assert "nodes" in merged
        assert "relations" in merged
        assert "unrecognized_entities" in merged
        assert "unrecognized_relations" in merged
        assert "stats" in merged
        assert "nodes_before_merge" in merged["stats"]
        assert "nodes_after_merge" in merged["stats"]

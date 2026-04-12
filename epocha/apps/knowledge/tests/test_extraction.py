"""Tests for per-chunk extraction with validation."""
import json
from unittest.mock import MagicMock, patch

import pytest

from epocha.apps.knowledge.extraction import (
    ExtractionResult,
    assign_source_type,
    extract_from_chunk,
    validate_extracted_entities,
    validate_extracted_relations,
)


def _make_llm_response(entities=None, relations=None):
    return json.dumps({
        "entities": entities or [],
        "relations": relations or [],
    })


@pytest.fixture
def mock_llm():
    with patch("epocha.apps.knowledge.extraction.get_llm_client") as mock:
        client = MagicMock()
        client.get_model_name.return_value = "llama-3.3-70b-versatile"
        mock.return_value = client
        yield client


class TestAssignSourceType:
    def test_name_literally_in_passage(self):
        assert assign_source_type("Robespierre", "Robespierre spoke to the assembly.") == "document"

    def test_name_not_literally_in_passage(self):
        assert assign_source_type("Maximilien", "Robespierre spoke to the assembly.") == "document_inferred"

    def test_accent_insensitive(self):
        assert assign_source_type("Declaration", "The declaration was read aloud.") == "document"

    def test_case_insensitive(self):
        assert assign_source_type("ROBESPIERRE", "Robespierre spoke.") == "document"

    def test_empty_passage_returns_none(self):
        assert assign_source_type("Robespierre", "") is None

    def test_empty_name_returns_none(self):
        assert assign_source_type("", "some passage") is None


class TestValidateExtractedEntities:
    def test_valid_entity_passes(self):
        entities = [{
            "entity_type": "person", "name": "Robespierre",
            "description": "A revolutionary leader",
            "passage_excerpt": "Robespierre was a member of the Jacobin Club.",
            "confidence": 0.9, "attributes": {},
        }]
        valid, unrecognized = validate_extracted_entities(entities)
        assert len(valid) == 1
        assert len(unrecognized) == 0
        assert valid[0]["source_type"] == "document"

    def test_unknown_entity_type_dropped(self):
        entities = [{
            "entity_type": "animal", "name": "Horse",
            "description": "A horse",
            "passage_excerpt": "The horse carried the rider.",
            "confidence": 0.5, "attributes": {},
        }]
        valid, unrecognized = validate_extracted_entities(entities)
        assert len(valid) == 0
        assert len(unrecognized) == 1

    def test_missing_passage_excerpt_dropped(self):
        entities = [{
            "entity_type": "person", "name": "Danton",
            "description": "A revolutionary",
            "passage_excerpt": "", "confidence": 0.8, "attributes": {},
        }]
        valid, unrecognized = validate_extracted_entities(entities)
        assert len(valid) == 0

    def test_source_type_document_inferred(self):
        entities = [{
            "entity_type": "person", "name": "Maximilien de Robespierre",
            "description": "The incorruptible",
            "passage_excerpt": "The deputy spoke fervently about virtue.",
            "confidence": 0.7, "attributes": {},
        }]
        valid, _ = validate_extracted_entities(entities)
        assert len(valid) == 1
        assert valid[0]["source_type"] == "document_inferred"


class TestValidateExtractedRelations:
    def test_valid_relation_passes(self):
        relations = [{
            "source_name": "Robespierre", "source_entity_type": "person",
            "target_name": "Jacobin Club", "target_entity_type": "institution",
            "relation_type": "member_of", "description": "Robespierre was a member",
            "passage_excerpt": "Robespierre was a member of the Jacobin Club.",
            "confidence": 0.9, "weight": 0.8,
            "temporal_start": "1789", "temporal_end": "",
        }]
        valid, unrecognized = validate_extracted_relations(relations)
        assert len(valid) == 1
        assert len(unrecognized) == 0

    def test_unknown_relation_type_dropped(self):
        relations = [{
            "source_name": "A", "source_entity_type": "person",
            "target_name": "B", "target_entity_type": "person",
            "relation_type": "friends_with", "description": "They are friends",
            "passage_excerpt": "A and B were close friends.",
            "confidence": 0.5, "weight": 0.5,
            "temporal_start": "", "temporal_end": "",
        }]
        valid, unrecognized = validate_extracted_relations(relations)
        assert len(valid) == 0
        assert len(unrecognized) == 1

    def test_missing_passage_excerpt_dropped(self):
        relations = [{
            "source_name": "A", "source_entity_type": "person",
            "target_name": "B", "target_entity_type": "group",
            "relation_type": "member_of", "description": "A is member of B",
            "passage_excerpt": "", "confidence": 0.8, "weight": 0.5,
            "temporal_start": "", "temporal_end": "",
        }]
        valid, _ = validate_extracted_relations(relations)
        assert len(valid) == 0

    def test_temporal_year_parsed(self):
        relations = [{
            "source_name": "Robespierre", "source_entity_type": "person",
            "target_name": "Jacobin Club", "target_entity_type": "institution",
            "relation_type": "member_of", "description": "member since 1789",
            "passage_excerpt": "Robespierre joined the Jacobins in 1789.",
            "confidence": 0.9, "weight": 0.8,
            "temporal_start": "1789-07", "temporal_end": "1794",
        }]
        valid, _ = validate_extracted_relations(relations)
        assert valid[0]["temporal_start_year"] == 1789
        assert valid[0]["temporal_end_year"] == 1794


class TestExtractFromChunk:
    def test_returns_extraction_result(self, mock_llm):
        mock_llm.complete.return_value = _make_llm_response(
            entities=[{
                "entity_type": "person", "name": "Robespierre",
                "description": "A revolutionary",
                "passage_excerpt": "Robespierre was a member of the Jacobin Club.",
                "confidence": 0.9, "attributes": {"role": "deputy"},
            }],
            relations=[{
                "source_name": "Robespierre", "source_entity_type": "person",
                "target_name": "Jacobin Club", "target_entity_type": "institution",
                "relation_type": "member_of", "description": "was a member",
                "passage_excerpt": "Robespierre was a member of the Jacobin Club.",
                "confidence": 0.9, "weight": 0.8,
                "temporal_start": "1789", "temporal_end": "",
            }],
        )
        result = extract_from_chunk(chunk_text="Robespierre was a member of the Jacobin Club.", chunk_id=0)
        assert isinstance(result, ExtractionResult)
        assert len(result.entities) == 1
        assert len(result.relations) == 1
        assert result.entities[0]["source_type"] == "document"
        assert result.entities[0]["chunk_id"] == 0

    def test_invalid_json_returns_empty(self, mock_llm):
        mock_llm.complete.return_value = "This is not JSON at all."
        result = extract_from_chunk(chunk_text="some text", chunk_id=5)
        assert len(result.entities) == 0
        assert len(result.relations) == 0

    def test_filters_invalid_entities(self, mock_llm):
        mock_llm.complete.return_value = _make_llm_response(
            entities=[
                {"entity_type": "person", "name": "Robespierre", "description": "valid",
                 "passage_excerpt": "Robespierre spoke.", "confidence": 0.9, "attributes": {}},
                {"entity_type": "dragon", "name": "Smaug", "description": "invalid type",
                 "passage_excerpt": "A dragon appeared.", "confidence": 0.5, "attributes": {}},
            ],
        )
        result = extract_from_chunk(chunk_text="Robespierre spoke.", chunk_id=0)
        assert len(result.entities) == 1
        assert len(result.unrecognized_entities) == 1

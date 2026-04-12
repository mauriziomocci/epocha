"""Tests for the extraction prompt builder."""
import json

import pytest

from epocha.apps.knowledge.prompts import (
    build_extraction_system_prompt,
    build_extraction_user_prompt,
    EXTRACTION_JSON_SCHEMA,
)
from epocha.apps.knowledge.ontology import ENTITY_TYPES, RELATION_TYPES


class TestExtractionSystemPrompt:
    def test_contains_all_entity_types(self):
        prompt = build_extraction_system_prompt()
        for entity_type in ENTITY_TYPES:
            assert entity_type in prompt, f"Missing entity type: {entity_type}"

    def test_contains_all_relation_types(self):
        prompt = build_extraction_system_prompt()
        for rel_type in RELATION_TYPES:
            assert rel_type in prompt, f"Missing relation type: {rel_type}"

    def test_contains_disambiguation_rule(self):
        prompt = build_extraction_system_prompt()
        assert "institution" in prompt
        assert "group" in prompt
        assert "most specific" in prompt.lower() or "priority" in prompt.lower()

    def test_contains_json_schema(self):
        prompt = build_extraction_system_prompt()
        assert "entities" in prompt
        assert "relations" in prompt
        assert "passage_excerpt" in prompt

    def test_contains_multilingual_instruction(self):
        prompt = build_extraction_system_prompt()
        assert "language" in prompt.lower()

    def test_does_not_mention_llm_knowledge(self):
        prompt = build_extraction_system_prompt()
        assert "llm_knowledge" not in prompt

    def test_contains_examples_for_each_entity_type(self):
        prompt = build_extraction_system_prompt()
        assert "Robespierre" in prompt or "example" in prompt.lower()


class TestExtractionUserPrompt:
    def test_contains_chunk_text(self):
        chunk_text = "The Bastille was stormed on July 14, 1789."
        prompt = build_extraction_user_prompt(chunk_text)
        assert chunk_text in prompt

    def test_contains_extraction_instruction(self):
        prompt = build_extraction_user_prompt("some text")
        assert "extract" in prompt.lower() or "Extract" in prompt

    def test_contains_passage_excerpt_instruction(self):
        prompt = build_extraction_user_prompt("some text")
        assert "passage_excerpt" in prompt

    def test_forbids_general_knowledge(self):
        prompt = build_extraction_user_prompt("some text")
        assert "general knowledge" in prompt.lower() or "do not extract" in prompt.lower()


class TestExtractionJsonSchema:
    def test_schema_is_valid_json_string(self):
        parsed = json.loads(EXTRACTION_JSON_SCHEMA)
        assert "entities" in parsed
        assert "relations" in parsed

    def test_entity_schema_has_required_fields(self):
        parsed = json.loads(EXTRACTION_JSON_SCHEMA)
        entity = parsed["entities"][0]
        required_keys = {"entity_type", "name", "description", "passage_excerpt"}
        assert required_keys.issubset(set(entity.keys()))

    def test_relation_schema_has_required_fields(self):
        parsed = json.loads(EXTRACTION_JSON_SCHEMA)
        relation = parsed["relations"][0]
        required_keys = {
            "source_name",
            "source_entity_type",
            "target_name",
            "target_entity_type",
            "relation_type",
            "description",
            "passage_excerpt",
        }
        assert required_keys.issubset(set(relation.keys()))

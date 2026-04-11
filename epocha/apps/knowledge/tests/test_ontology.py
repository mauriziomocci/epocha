"""Tests for the ontology validators and vocabularies."""
import pytest

from epocha.apps.knowledge.ontology import (
    ENTITY_TYPES,
    RELATION_TYPES,
    SOURCE_TYPES,
    is_valid_entity_type,
    is_valid_relation_type,
    is_valid_source_type,
)


class TestEntityTypes:
    def test_exactly_ten_entity_types(self):
        assert len(ENTITY_TYPES) == 10

    def test_contains_expected_types(self):
        expected = {
            "person", "group", "place", "institution", "event",
            "concept", "ideology", "object", "norm", "value",
        }
        assert set(ENTITY_TYPES) == expected

    def test_is_valid_accepts_all_known(self):
        for t in ENTITY_TYPES:
            assert is_valid_entity_type(t) is True

    def test_is_valid_rejects_unknown(self):
        assert is_valid_entity_type("unknown") is False
        assert is_valid_entity_type("") is False
        assert is_valid_entity_type("PERSON") is False  # case sensitive


class TestRelationTypes:
    def test_exactly_twenty_relation_types(self):
        assert len(RELATION_TYPES) == 20

    def test_contains_kinship_relations(self):
        assert "married_to" in RELATION_TYPES
        assert "parent_of" in RELATION_TYPES
        assert "sibling_of" in RELATION_TYPES

    def test_no_kin_of_umbrella(self):
        assert "kin_of" not in RELATION_TYPES

    def test_is_valid_accepts_all_known(self):
        for t in RELATION_TYPES:
            assert is_valid_relation_type(t) is True

    def test_is_valid_rejects_unknown(self):
        assert is_valid_relation_type("friend_of") is False
        assert is_valid_relation_type("") is False


class TestSourceTypes:
    def test_exactly_two_source_types(self):
        assert len(SOURCE_TYPES) == 2

    def test_no_llm_knowledge_in_mvp(self):
        assert "llm_knowledge" not in SOURCE_TYPES

    def test_is_valid(self):
        assert is_valid_source_type("document") is True
        assert is_valid_source_type("document_inferred") is True
        assert is_valid_source_type("llm_knowledge") is False

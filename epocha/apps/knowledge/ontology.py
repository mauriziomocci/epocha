"""Ontology definitions for the Knowledge Graph.

The entity type vocabulary follows Searle (1995) for the brute/
institutional distinction, CIDOC-CRM (ISO 21127:2014) for event and
object modeling, and Freeden (1996) for the concept/ideology/value/norm
distinction. The relation vocabulary is a controlled set of 20 types
chosen for operational distinguishability by an LLM.
"""
from __future__ import annotations

# Entity type vocabulary (10 types)
ENTITY_TYPES: tuple[str, ...] = (
    "person",
    "group",
    "place",
    "institution",
    "event",
    "concept",
    "ideology",
    "object",
    "norm",
    "value",
)

# Relation type vocabulary (20 types, grouped by category)
RELATION_TYPES: tuple[str, ...] = (
    # Membership
    "member_of", "founder_of", "leader_of",
    # Spatial
    "located_in", "occurred_in",
    # Temporal
    "occurred_during",
    # Belief
    "believes_in", "opposes", "supports",
    # Social
    "ally_of", "enemy_of", "influences",
    # Kinship
    "married_to", "parent_of", "sibling_of",
    # Causal
    "caused_by", "led_to",
    # Participation
    "participated_in",
    # Production
    "authored", "enacted",
)

# Source type vocabulary (2 types; llm_knowledge excluded from MVP)
SOURCE_TYPES: tuple[str, ...] = (
    "document",
    "document_inferred",
)

# Category mapping for relation colors in visualization
RELATION_CATEGORIES: dict[str, str] = {
    "member_of": "membership",
    "founder_of": "membership",
    "leader_of": "membership",
    "located_in": "spatial",
    "occurred_in": "spatial",
    "occurred_during": "temporal",
    "believes_in": "belief",
    "opposes": "belief",
    "supports": "belief",
    "ally_of": "social",
    "enemy_of": "social",
    "influences": "social",
    "married_to": "kinship",
    "parent_of": "kinship",
    "sibling_of": "kinship",
    "caused_by": "causal",
    "led_to": "causal",
    "participated_in": "participation",
    "authored": "production",
    "enacted": "production",
}


def is_valid_entity_type(value: str) -> bool:
    """Return True if value is a recognized entity type code."""
    return value in ENTITY_TYPES


def is_valid_relation_type(value: str) -> bool:
    """Return True if value is a recognized relation type code."""
    return value in RELATION_TYPES


def is_valid_source_type(value: str) -> bool:
    """Return True if value is a recognized source type code."""
    return value in SOURCE_TYPES

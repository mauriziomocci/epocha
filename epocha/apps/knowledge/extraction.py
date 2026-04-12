"""Per-chunk LLM extraction with validation and source_type assignment.

Calls the LLM once per chunk, parses the JSON response, validates each
entity and relation against the ontology vocabulary, assigns source_type
mechanically (not by LLM), and extracts temporal year integers from
partial ISO date strings.

References:
    - Ontology vocabulary: epocha.apps.knowledge.ontology
    - Source_type assignment rule: if the entity name appears in the
      passage_excerpt (accent/case insensitive) the source_type is
      "document"; otherwise "document_inferred".
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field

from epocha.apps.llm_adapter.client import get_llm_client
from epocha.common.utils import clean_llm_json

from .normalizer import name_contained_in_passage, normalize_canonical_name
from .ontology import is_valid_entity_type, is_valid_relation_type
from .prompts import build_extraction_system_prompt, build_extraction_user_prompt
from .versions import EXTRACTION_TEMPERATURE

logger = logging.getLogger(__name__)

_YEAR_RE = re.compile(r"(\d{4})")


@dataclass
class ExtractionResult:
    """Result of extracting entities and relations from a single chunk."""

    chunk_id: int
    entities: list[dict] = field(default_factory=list)
    relations: list[dict] = field(default_factory=list)
    unrecognized_entities: list[dict] = field(default_factory=list)
    unrecognized_relations: list[dict] = field(default_factory=list)


def assign_source_type(name: str, passage_excerpt: str) -> str | None:
    """Assign source_type mechanically based on passage content.

    Returns "document" when the entity name appears literally in the
    passage (accent/case insensitive), "document_inferred" when it does
    not, or None when either argument is empty (indicating the entity
    should be dropped).
    """
    if not name or not passage_excerpt:
        return None
    if name_contained_in_passage(name, passage_excerpt):
        return "document"
    return "document_inferred"


def _parse_temporal_year(iso_str: str) -> int | None:
    """Extract the four-digit year from a partial ISO date string.

    Accepts formats like "1789", "1789-07", "1789-07-14". Returns None
    for empty strings or strings without a four-digit sequence.
    """
    if not iso_str:
        return None
    match = _YEAR_RE.search(iso_str)
    return int(match.group(1)) if match else None


def validate_extracted_entities(raw_entities: list[dict]) -> tuple[list[dict], list[dict]]:
    """Validate extracted entities against the ontology.

    Each entity must have a recognized entity_type and a non-empty
    passage_excerpt. Entities with unrecognized types are collected
    separately for diagnostics. Entities with empty passage_excerpt
    are silently dropped (they violate the extraction contract).

    Returns:
        A tuple of (valid_entities, unrecognized_entities).
    """
    valid: list[dict] = []
    unrecognized: list[dict] = []
    for entity in raw_entities:
        entity_type = entity.get("entity_type", "")
        name = entity.get("name", "")
        passage = entity.get("passage_excerpt", "")
        if not is_valid_entity_type(entity_type):
            unrecognized.append(entity)
            continue
        if not passage:
            logger.debug("Dropping entity '%s' with empty passage_excerpt", name)
            continue
        source_type = assign_source_type(name, passage)
        if source_type is None:
            continue
        valid.append({
            "entity_type": entity_type,
            "name": name,
            "canonical_name": normalize_canonical_name(name),
            "description": entity.get("description", ""),
            "passage_excerpt": passage,
            "source_type": source_type,
            "confidence": float(entity.get("confidence", 0.5)),
            "mention_count": 1,
            "attributes": entity.get("attributes", {}),
        })
    return valid, unrecognized


def validate_extracted_relations(raw_relations: list[dict]) -> tuple[list[dict], list[dict]]:
    """Validate extracted relations against the relation vocabulary.

    Each relation must have a recognized relation_type and a non-empty
    passage_excerpt. Temporal start/end strings are parsed into integer
    years for downstream filtering.

    Returns:
        A tuple of (valid_relations, unrecognized_relations).
    """
    valid: list[dict] = []
    unrecognized: list[dict] = []
    for relation in raw_relations:
        rel_type = relation.get("relation_type", "")
        passage = relation.get("passage_excerpt", "")
        if not is_valid_relation_type(rel_type):
            unrecognized.append(relation)
            continue
        if not passage:
            logger.debug("Dropping relation '%s' with empty passage_excerpt", rel_type)
            continue
        temporal_start = relation.get("temporal_start", "")
        temporal_end = relation.get("temporal_end", "")
        valid.append({
            "source_name": relation.get("source_name", ""),
            "source_entity_type": relation.get("source_entity_type", ""),
            "source_canonical_name": normalize_canonical_name(relation.get("source_name", "")),
            "target_name": relation.get("target_name", ""),
            "target_entity_type": relation.get("target_entity_type", ""),
            "target_canonical_name": normalize_canonical_name(relation.get("target_name", "")),
            "relation_type": rel_type,
            "description": relation.get("description", ""),
            "passage_excerpt": passage,
            "source_type": assign_source_type(relation.get("source_name", ""), passage) or "document_inferred",
            "confidence": float(relation.get("confidence", 0.5)),
            "weight": float(relation.get("weight", 0.5)),
            "temporal_start_iso": temporal_start,
            "temporal_start_year": _parse_temporal_year(temporal_start),
            "temporal_end_iso": temporal_end,
            "temporal_end_year": _parse_temporal_year(temporal_end),
        })
    return valid, unrecognized


def extract_from_chunk(*, chunk_text: str, chunk_id: int) -> ExtractionResult:
    """Extract entities and relations from a single text chunk via LLM.

    Calls the configured LLM provider with the extraction system/user
    prompts, parses the JSON response, validates all items against the
    ontology, and assigns source_type and chunk_id to each valid item.

    Returns an ExtractionResult even on failure (with empty lists), so
    callers never need to handle None.
    """
    client = get_llm_client()
    system_prompt = build_extraction_system_prompt()
    user_prompt = build_extraction_user_prompt(chunk_text)
    try:
        raw_response = client.complete(
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=EXTRACTION_TEMPERATURE,
            max_tokens=4000,
        )
    except Exception:
        logger.exception("LLM call failed for chunk %d", chunk_id)
        return ExtractionResult(chunk_id=chunk_id)

    try:
        data = json.loads(clean_llm_json(raw_response))
    except (json.JSONDecodeError, TypeError):
        logger.warning("Chunk %d returned invalid JSON: %s", chunk_id, raw_response[:200])
        return ExtractionResult(chunk_id=chunk_id)

    valid_entities, unrec_entities = validate_extracted_entities(data.get("entities", []))
    valid_relations, unrec_relations = validate_extracted_relations(data.get("relations", []))

    for entity in valid_entities:
        entity["chunk_id"] = chunk_id
    for relation in valid_relations:
        relation["chunk_id"] = chunk_id

    return ExtractionResult(
        chunk_id=chunk_id,
        entities=valid_entities,
        relations=valid_relations,
        unrecognized_entities=unrec_entities,
        unrecognized_relations=unrec_relations,
    )

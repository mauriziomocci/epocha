# Knowledge Graph Implementation Plan — Part 2: Extraction Pipeline

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the LLM-based entity and relation extraction pipeline: the structured extraction prompt with ontology definitions and examples, per-chunk extraction with validation and mechanical source_type assignment, and the merge/deduplication logic that produces a clean set of entities and relations ready for cache persistence. After this plan is complete, the system can take chunked + embedded documents and produce a deduplicated, validated extraction result stored in ExtractionCache.

**Architecture:** Three new modules in `epocha.apps.knowledge`: `prompts.py` (extraction system prompt), `extraction.py` (per-chunk extraction with validation), `merge.py` (cross-chunk dedup and merge). All LLM calls go through the existing `epocha.apps.llm_adapter.client`. Tests mock the LLM for deterministic verification.

**Tech Stack:** Django, existing LLM adapter (Groq llama-3.3-70b), fastembed (for dedup embeddings), pytest with LLM mocks.

**Spec:** `docs/superpowers/specs/2026-04-11-knowledge-graph-design.md` (Stages 4-7)

**Depends on:** Part 1 (Foundations) — completed. Models, normalizer, ontology, embedding, chunking, cache key all exist.

**Follow-up plans:**
- Part 3 — Graph models, materialization, Celery orchestration, world generator integration
- Part 4 — API, dashboard, visualization, housekeeping

---

## File Structure (Part 2 scope)

| File | Responsibility | New/Modify |
|------|---------------|------------|
| `epocha/apps/knowledge/prompts.py` | Extraction system prompt with ontology, examples, JSON schema | New |
| `epocha/apps/knowledge/extraction.py` | Per-chunk LLM extraction, validation, source_type assignment | New |
| `epocha/apps/knowledge/merge.py` | Cross-chunk dedup (embedding similarity), merge rules, relation dedup | New |
| `epocha/apps/knowledge/tests/test_prompts.py` | Tests for prompt structure | New |
| `epocha/apps/knowledge/tests/test_extraction.py` | Tests for extraction with mocked LLM | New |
| `epocha/apps/knowledge/tests/test_merge.py` | Tests for merge and dedup logic | New |

---

## Tasks summary (Part 2 scope)

6. **Extraction prompt** — prompts.py with the full system prompt, JSON schema, and ontology examples
7. **Per-chunk extraction with validation** — extraction.py parsing LLM output, validating against ontology, assigning source_type mechanically
8. **Merge and deduplication** — merge.py with canonical name grouping, embedding-based clustering, merge rules, relation dedup, cache persistence

---

### Task 6: Extraction prompt

**Files:**
- Create: `epocha/apps/knowledge/prompts.py`
- Create: `epocha/apps/knowledge/tests/test_prompts.py`

- [ ] **Step 1: Write the failing tests for the prompt module**

Create `epocha/apps/knowledge/tests/test_prompts.py`:

```python
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
        # At least the word "example" or a concrete named entity
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
        required_keys = {"source_name", "source_entity_type", "target_name", "target_entity_type", "relation_type", "description", "passage_excerpt"}
        assert required_keys.issubset(set(relation.keys()))
```

- [ ] **Step 2: Run prompt tests to verify they fail**

Run: `docker compose -f docker-compose.local.yml run --rm web pytest epocha/apps/knowledge/tests/test_prompts.py -v`

Expected: ImportError for `epocha.apps.knowledge.prompts`.

- [ ] **Step 3: Implement the prompt module**

Create `epocha/apps/knowledge/prompts.py`:

```python
"""Extraction prompt builder for the Knowledge Graph pipeline.

Builds the system and user prompts for per-chunk entity and relation
extraction. The system prompt encodes the full ontology (10 entity types,
20 relation types), operational classification criteria, disambiguation
rules, and a strict JSON output schema. The user prompt wraps the chunk
text with extraction instructions.

The prompt design follows the principle that the LLM should extract only
what the passage supports, never adding facts from its general knowledge.
Source type assignment is done mechanically after extraction, not by
the LLM (see extraction.py).
"""
from __future__ import annotations

import json

from .ontology import ENTITY_TYPES, RELATION_TYPES

# JSON schema example that the LLM must follow exactly.
EXTRACTION_JSON_SCHEMA = json.dumps(
    {
        "entities": [
            {
                "entity_type": "person|group|place|institution|event|concept|ideology|object|norm|value",
                "name": "Entity name in the original language of the document",
                "description": "Brief description based on the passage (1-2 sentences)",
                "passage_excerpt": "Exact quote from the passage that supports this entity",
                "confidence": 0.9,
                "attributes": {
                    "date": "ISO date if applicable (e.g. 1789-07-14)",
                    "role": "Social role if person (e.g. deputy, king, merchant)",
                },
            }
        ],
        "relations": [
            {
                "source_name": "Name of the source entity",
                "source_entity_type": "Entity type of the source",
                "target_name": "Name of the target entity",
                "target_entity_type": "Entity type of the target",
                "relation_type": "member_of|founder_of|leader_of|located_in|occurred_in|occurred_during|believes_in|opposes|supports|ally_of|enemy_of|influences|married_to|parent_of|sibling_of|caused_by|led_to|participated_in|authored|enacted",
                "description": "Brief description of the relation",
                "passage_excerpt": "Exact quote from the passage that supports this relation",
                "confidence": 0.8,
                "weight": 0.5,
                "temporal_start": "ISO partial date if applicable (e.g. 1789)",
                "temporal_end": "ISO partial date if applicable, or empty",
            }
        ],
    },
    indent=2,
)

_ENTITY_TYPE_DEFINITIONS = """Entity types (pick exactly one per entity):

- person: An individually identifiable historical human.
  Examples: Robespierre, Louis XVI, Marie Antoinette, Danton, Marat.

- group: An informal social aggregate or movement without formalized roles or procedures.
  Examples: Sans-culottes, Girondins, the Third Estate as a social class.

- place: A physical geographic location with potential coordinates.
  Examples: Versailles, Paris, Faubourg Saint-Antoine, the Bastille fortress.

- institution: A formalized organization with defined roles, procedures, and continuity.
  Examples: National Assembly, Committee of Public Safety, Jacobin Club, the French Monarchy.
  Note: if an entity has formal membership rules, leadership positions, and documented procedures, classify it as institution, not group.

- event: A datable occurrence with actors and a location.
  Examples: Storming of the Bastille, Reign of Terror, Flight to Varennes, Tennis Court Oath.

- concept: A political or philosophical idea usable as a building block for ideologies.
  Test: "Can you combine this with other concepts to form a coherent political system?" If yes, it is a concept.
  Examples: Liberty, Equality, Popular sovereignty, Reason, Virtue, Natural rights.

- ideology: A coherent political system that configures concepts into a vision for society.
  Test: "Is this already a complete political system?" If yes, it is an ideology.
  Examples: Jacobinism, Liberal monarchism, Girondism, Absolutism, Republicanism.

- object: A physically existing artifact with historical significance.
  Examples: Guillotine, Phrygian cap, tricolor cockade, the Bastille keys.

- norm: A codified rule, law, or explicit decree.
  Examples: Declaration of the Rights of Man, Law of Suspects, Constitution of 1791, Civil Constitution of the Clergy.

- value: A cultural commitment of everyday life, not a political system.
  Test: "Is this something people live by daily rather than a system they argue for politically?" If yes, it is a value.
  Examples: Noble honor, piety, frugality, Fraternite as lived value, patriotism as daily sentiment.

DISAMBIGUATION RULE: When an entity fits multiple types, pick the most specific formalization level:
  Priority order (high to low): institution > group > concept/ideology.
  Example: "Jacobin Club" -> institution (has formal membership and procedures), not group."""

_RELATION_TYPE_DEFINITIONS = """Relation types (pick exactly one per relation):

Membership: member_of, founder_of, leader_of
Spatial: located_in, occurred_in
Temporal: occurred_during
Belief: believes_in, opposes, supports
Social: ally_of, enemy_of, influences
Kinship: married_to, parent_of, sibling_of
Causal: caused_by, led_to
Participation: participated_in
Production: authored, enacted

Use ONLY these exact codes. If a relation does not fit any of these types, do NOT include it."""


def build_extraction_system_prompt() -> str:
    """Build the system prompt for entity and relation extraction."""
    return f"""You are an expert knowledge graph extractor for historical and social simulation documents.

Your task: extract entities and relations from text passages, classifying each entity into exactly one of the defined types and each relation into exactly one of the defined relation types.

{_ENTITY_TYPE_DEFINITIONS}

{_RELATION_TYPE_DEFINITIONS}

LANGUAGE: The document may be in any European language. Keep entity name values in the original language of the document. Provide the description and passage_excerpt in the original language as well, without translation.

OUTPUT FORMAT: Respond ONLY with a JSON object following this exact schema:

{EXTRACTION_JSON_SCHEMA}

RULES:
1. Extract ONLY entities and relations that are present in or directly inferable from the passage provided.
2. Do NOT add facts from your general knowledge that are not supported by the passage text.
3. Every entity MUST include a passage_excerpt: an exact quote from the passage that supports its existence.
4. Every relation MUST include a passage_excerpt: an exact quote from the passage that supports the relation.
5. If no entities or relations can be extracted, return {{"entities": [], "relations": []}}.
6. confidence: 0.0 to 1.0, how confident you are this entity/relation is correctly extracted.
7. weight: 0.0 to 1.0 for relations, how strong/important the relation is.
8. temporal_start and temporal_end: partial ISO dates (e.g. "1789", "1789-07", "1789-07-14") or empty string if not applicable."""


def build_extraction_user_prompt(chunk_text: str) -> str:
    """Build the user prompt wrapping a specific chunk of text."""
    return f"""Extract all entities and relations from the following passage.

Cite the exact passage_excerpt from the text below that supports each extracted item. Do NOT extract facts from your general knowledge that are not supported by the passage.

---
{chunk_text}
---

Respond with a JSON object containing "entities" and "relations" arrays."""
```

- [ ] **Step 4: Run prompt tests to verify they pass**

Run: `docker compose -f docker-compose.local.yml run --rm web pytest epocha/apps/knowledge/tests/test_prompts.py -v`

Expected: all PASS.

- [ ] **Step 5: Commit**

```
feat(knowledge): add extraction prompt with ontology and JSON schema

CHANGE: Add prompts.py with the structured extraction system prompt
encoding 10 entity types with operational criteria and examples,
20 relation types with categories, disambiguation rule, multilingual
instruction, and strict JSON output schema. The prompt enforces
passage-evidence-only extraction with no general knowledge leakage.
```

---

### Task 7: Per-chunk extraction with validation

**Files:**
- Create: `epocha/apps/knowledge/extraction.py`
- Create: `epocha/apps/knowledge/tests/test_extraction.py`

- [ ] **Step 1: Write the failing tests for the extraction service**

Create `epocha/apps/knowledge/tests/test_extraction.py`:

```python
"""Tests for per-chunk extraction with validation.

All tests mock the LLM client to ensure deterministic results.
"""
import json
from unittest.mock import MagicMock, patch

import pytest

from epocha.apps.knowledge.extraction import (
    extract_from_chunk,
    validate_extracted_entities,
    validate_extracted_relations,
    assign_source_type,
    ExtractionResult,
)


def _make_llm_response(entities=None, relations=None):
    """Build a valid JSON string as the LLM would return."""
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
        result = assign_source_type("Robespierre", "Robespierre spoke to the assembly.")
        assert result == "document"

    def test_name_not_literally_in_passage(self):
        result = assign_source_type("Maximilien", "Robespierre spoke to the assembly.")
        assert result == "document_inferred"

    def test_accent_insensitive(self):
        result = assign_source_type("Déclaration", "The declaration was read aloud.")
        assert result == "document"

    def test_case_insensitive(self):
        result = assign_source_type("ROBESPIERRE", "Robespierre spoke.")
        assert result == "document"

    def test_empty_passage_returns_none(self):
        result = assign_source_type("Robespierre", "")
        assert result is None

    def test_empty_name_returns_none(self):
        result = assign_source_type("", "some passage")
        assert result is None


class TestValidateExtractedEntities:
    def test_valid_entity_passes(self):
        entities = [{
            "entity_type": "person",
            "name": "Robespierre",
            "description": "A revolutionary leader",
            "passage_excerpt": "Robespierre was a member of the Jacobin Club.",
            "confidence": 0.9,
            "attributes": {},
        }]
        valid, unrecognized = validate_extracted_entities(entities)
        assert len(valid) == 1
        assert len(unrecognized) == 0
        assert valid[0]["source_type"] == "document"

    def test_unknown_entity_type_dropped(self):
        entities = [{
            "entity_type": "animal",
            "name": "Horse",
            "description": "A horse",
            "passage_excerpt": "The horse carried the rider.",
            "confidence": 0.5,
            "attributes": {},
        }]
        valid, unrecognized = validate_extracted_entities(entities)
        assert len(valid) == 0
        assert len(unrecognized) == 1

    def test_missing_passage_excerpt_dropped(self):
        entities = [{
            "entity_type": "person",
            "name": "Danton",
            "description": "A revolutionary",
            "passage_excerpt": "",
            "confidence": 0.8,
            "attributes": {},
        }]
        valid, unrecognized = validate_extracted_entities(entities)
        assert len(valid) == 0

    def test_source_type_document_inferred(self):
        entities = [{
            "entity_type": "person",
            "name": "Maximilien de Robespierre",
            "description": "The incorruptible",
            "passage_excerpt": "The deputy spoke fervently about virtue.",
            "confidence": 0.7,
            "attributes": {},
        }]
        valid, _ = validate_extracted_entities(entities)
        assert len(valid) == 1
        assert valid[0]["source_type"] == "document_inferred"


class TestValidateExtractedRelations:
    def test_valid_relation_passes(self):
        relations = [{
            "source_name": "Robespierre",
            "source_entity_type": "person",
            "target_name": "Jacobin Club",
            "target_entity_type": "institution",
            "relation_type": "member_of",
            "description": "Robespierre was a member",
            "passage_excerpt": "Robespierre was a member of the Jacobin Club.",
            "confidence": 0.9,
            "weight": 0.8,
            "temporal_start": "1789",
            "temporal_end": "",
        }]
        valid, unrecognized = validate_extracted_relations(relations)
        assert len(valid) == 1
        assert len(unrecognized) == 0

    def test_unknown_relation_type_dropped(self):
        relations = [{
            "source_name": "A",
            "source_entity_type": "person",
            "target_name": "B",
            "target_entity_type": "person",
            "relation_type": "friends_with",
            "description": "They are friends",
            "passage_excerpt": "A and B were close friends.",
            "confidence": 0.5,
            "weight": 0.5,
            "temporal_start": "",
            "temporal_end": "",
        }]
        valid, unrecognized = validate_extracted_relations(relations)
        assert len(valid) == 0
        assert len(unrecognized) == 1

    def test_missing_passage_excerpt_dropped(self):
        relations = [{
            "source_name": "A",
            "source_entity_type": "person",
            "target_name": "B",
            "target_entity_type": "group",
            "relation_type": "member_of",
            "description": "A is member of B",
            "passage_excerpt": "",
            "confidence": 0.8,
            "weight": 0.5,
            "temporal_start": "",
            "temporal_end": "",
        }]
        valid, unrecognized = validate_extracted_relations(relations)
        assert len(valid) == 0

    def test_temporal_year_parsed(self):
        relations = [{
            "source_name": "Robespierre",
            "source_entity_type": "person",
            "target_name": "Jacobin Club",
            "target_entity_type": "institution",
            "relation_type": "member_of",
            "description": "member since 1789",
            "passage_excerpt": "Robespierre joined the Jacobins in 1789.",
            "confidence": 0.9,
            "weight": 0.8,
            "temporal_start": "1789-07",
            "temporal_end": "1794",
        }]
        valid, _ = validate_extracted_relations(relations)
        assert valid[0]["temporal_start_year"] == 1789
        assert valid[0]["temporal_end_year"] == 1794


class TestExtractFromChunk:
    def test_returns_extraction_result(self, mock_llm):
        mock_llm.complete.return_value = _make_llm_response(
            entities=[{
                "entity_type": "person",
                "name": "Robespierre",
                "description": "A revolutionary",
                "passage_excerpt": "Robespierre was a member of the Jacobin Club.",
                "confidence": 0.9,
                "attributes": {"role": "deputy"},
            }],
            relations=[{
                "source_name": "Robespierre",
                "source_entity_type": "person",
                "target_name": "Jacobin Club",
                "target_entity_type": "institution",
                "relation_type": "member_of",
                "description": "was a member",
                "passage_excerpt": "Robespierre was a member of the Jacobin Club.",
                "confidence": 0.9,
                "weight": 0.8,
                "temporal_start": "1789",
                "temporal_end": "",
            }],
        )

        result = extract_from_chunk(
            chunk_text="Robespierre was a member of the Jacobin Club.",
            chunk_id=0,
        )

        assert isinstance(result, ExtractionResult)
        assert len(result.entities) == 1
        assert len(result.relations) == 1
        assert result.entities[0]["source_type"] == "document"
        assert result.entities[0]["chunk_id"] == 0
        assert result.chunk_id == 0

    def test_invalid_json_returns_empty(self, mock_llm):
        mock_llm.complete.return_value = "This is not JSON at all."

        result = extract_from_chunk(chunk_text="some text", chunk_id=5)

        assert len(result.entities) == 0
        assert len(result.relations) == 0

    def test_filters_invalid_entities(self, mock_llm):
        mock_llm.complete.return_value = _make_llm_response(
            entities=[
                {
                    "entity_type": "person",
                    "name": "Robespierre",
                    "description": "valid",
                    "passage_excerpt": "Robespierre spoke.",
                    "confidence": 0.9,
                    "attributes": {},
                },
                {
                    "entity_type": "dragon",
                    "name": "Smaug",
                    "description": "invalid type",
                    "passage_excerpt": "A dragon appeared.",
                    "confidence": 0.5,
                    "attributes": {},
                },
            ],
        )

        result = extract_from_chunk(chunk_text="Robespierre spoke.", chunk_id=0)

        assert len(result.entities) == 1
        assert len(result.unrecognized_entities) == 1
        assert result.entities[0]["name"] == "Robespierre"
```

- [ ] **Step 2: Run extraction tests to verify they fail**

Run: `docker compose -f docker-compose.local.yml run --rm web pytest epocha/apps/knowledge/tests/test_extraction.py -v`

Expected: ImportError for `epocha.apps.knowledge.extraction`.

- [ ] **Step 3: Implement the extraction service**

Create `epocha/apps/knowledge/extraction.py`:

```python
"""Per-chunk LLM extraction with validation and source_type assignment.

Each chunk of text is sent to the LLM with a structured extraction prompt.
The raw JSON output is parsed, validated against the ontology vocabulary,
and enriched with mechanical source_type assignment. Invalid items are
separated into unrecognized lists for logging and vocabulary review.
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

    Returns "document" if the entity name appears literally in the passage
    (accent/case insensitive), "document_inferred" if the passage exists
    but does not contain the name, or None if the passage is empty.
    """
    if not name or not passage_excerpt:
        return None
    if name_contained_in_passage(name, passage_excerpt):
        return "document"
    return "document_inferred"


def _parse_temporal_year(iso_str: str) -> int | None:
    """Extract the four-digit year from a partial ISO date string."""
    if not iso_str:
        return None
    match = _YEAR_RE.search(iso_str)
    return int(match.group(1)) if match else None


def validate_extracted_entities(
    raw_entities: list[dict],
) -> tuple[list[dict], list[dict]]:
    """Validate extracted entities against the ontology.

    Returns (valid_entities, unrecognized_entities). Each valid entity is
    enriched with canonical_name, source_type, and mention_count.
    """
    valid = []
    unrecognized = []

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


def validate_extracted_relations(
    raw_relations: list[dict],
) -> tuple[list[dict], list[dict]]:
    """Validate extracted relations against the relation vocabulary.

    Returns (valid_relations, unrecognized_relations). Each valid relation
    is enriched with canonical names and parsed temporal years.
    """
    valid = []
    unrecognized = []

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
            "source_type": assign_source_type(
                relation.get("source_name", ""), passage
            ) or "document_inferred",
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

    Calls the LLM with the extraction prompt, parses JSON output, validates
    against the ontology, and assigns source_type mechanically.
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

    raw_entities = data.get("entities", [])
    raw_relations = data.get("relations", [])

    valid_entities, unrecognized_entities = validate_extracted_entities(raw_entities)
    valid_relations, unrecognized_relations = validate_extracted_relations(raw_relations)

    # Tag each item with the chunk_id for citation tracking
    for entity in valid_entities:
        entity["chunk_id"] = chunk_id
    for relation in valid_relations:
        relation["chunk_id"] = chunk_id

    return ExtractionResult(
        chunk_id=chunk_id,
        entities=valid_entities,
        relations=valid_relations,
        unrecognized_entities=unrecognized_entities,
        unrecognized_relations=unrecognized_relations,
    )
```

- [ ] **Step 4: Run extraction tests to verify they pass**

Run: `docker compose -f docker-compose.local.yml run --rm web pytest epocha/apps/knowledge/tests/test_extraction.py -v`

Expected: all PASS.

- [ ] **Step 5: Run full knowledge suite**

Run: `docker compose -f docker-compose.local.yml run --rm web pytest epocha/apps/knowledge/ -v -m "not slow"`

Expected: all PASS.

- [ ] **Step 6: Commit**

```
feat(knowledge): add per-chunk extraction with validation

CHANGE: Add extraction.py with LLM-based entity and relation extraction
from text chunks, validation against the controlled ontology vocabulary,
mechanical source_type assignment (name-in-passage check instead of LLM
self-report), temporal year parsing, and canonical name enrichment.
Invalid items are separated into unrecognized lists for vocabulary
review. All LLM interactions go through the existing adapter.
```

---

### Task 8: Merge and deduplication

**Files:**
- Create: `epocha/apps/knowledge/merge.py`
- Create: `epocha/apps/knowledge/tests/test_merge.py`

- [ ] **Step 1: Write the failing tests for the merge module**

Create `epocha/apps/knowledge/tests/test_merge.py`:

```python
"""Tests for the merge and deduplication logic.

Tests use mocked embeddings to avoid downloading the real model.
"""
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
    """Helper to build an entity dict matching extraction output."""
    from epocha.apps.knowledge.normalizer import normalize_canonical_name
    return {
        "entity_type": entity_type,
        "name": name,
        "canonical_name": normalize_canonical_name(name),
        "description": description,
        "passage_excerpt": passage_excerpt,
        "source_type": source_type,
        "confidence": confidence,
        "mention_count": mention_count,
        "attributes": attributes or {},
        "chunk_id": chunk_id,
    }


def _relation(source, target, rel_type="member_of", source_type="person",
              target_type="institution", chunk_id=0, confidence=0.9, weight=0.5):
    from epocha.apps.knowledge.normalizer import normalize_canonical_name
    return {
        "source_name": source,
        "source_entity_type": source_type,
        "source_canonical_name": normalize_canonical_name(source),
        "target_name": target,
        "target_entity_type": target_type,
        "target_canonical_name": normalize_canonical_name(target),
        "relation_type": rel_type,
        "description": "",
        "passage_excerpt": f"{source} and {target}",
        "source_type": "document",
        "confidence": confidence,
        "weight": weight,
        "temporal_start_iso": "",
        "temporal_start_year": None,
        "temporal_end_iso": "",
        "temporal_end_year": None,
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
        # Similarity matrix: entities 0 and 1 are very similar
        matrix = [[1.0, 0.95, 0.1], [0.95, 1.0, 0.1], [0.1, 0.1, 1.0]]
        clusters = _single_linkage_clusters(matrix, threshold=0.85)
        assert len(clusters) == 2  # {0,1} and {2}
        merged = [c for c in clusters if len(c) > 1]
        assert len(merged) == 1
        assert set(merged[0]) == {0, 1}

    def test_below_threshold_separate(self):
        matrix = [[1.0, 0.5], [0.5, 1.0]]
        clusters = _single_linkage_clusters(matrix, threshold=0.85)
        assert len(clusters) == 2

    def test_transitive_merge(self):
        # 0-1 similar, 1-2 similar, but 0-2 not directly similar
        # Single linkage should merge all three
        matrix = [
            [1.0, 0.90, 0.5],
            [0.90, 1.0, 0.90],
            [0.5, 0.90, 1.0],
        ]
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
        entities = [
            _entity("Robespierre", mention_count=3),
            _entity("M. Robespierre", mention_count=2),
        ]
        merged = _merge_entity_cluster(entities)
        assert merged["mention_count"] == 5

    def test_takes_max_confidence(self):
        entities = [
            _entity("Robespierre", confidence=0.7),
            _entity("Robespierre", confidence=0.95),
        ]
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
        entities = [
            _entity("Robespierre", chunk_id=0),
            _entity("Robespierre", chunk_id=3),
            _entity("Robespierre", chunk_id=7),
        ]
        merged = _merge_entity_cluster(entities)
        assert set(merged["chunk_ids"]) == {0, 3, 7}

    def test_concatenates_descriptions(self):
        entities = [
            _entity("Robespierre", description="A deputy"),
            _entity("Robespierre", description="Leader of the Jacobins"),
        ]
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
        # Two chunks extracted "Robespierre" independently
        mock_embed.return_value = [[0.9] * 1024, [0.9] * 1024]

        results = [
            ExtractionResult(
                chunk_id=0,
                entities=[_entity("Robespierre", chunk_id=0, description="a deputy")],
                relations=[],
            ),
            ExtractionResult(
                chunk_id=1,
                entities=[_entity("Robespierre", chunk_id=1, description="Jacobin leader")],
                relations=[],
            ),
        ]

        merged = merge_extraction_results(results)
        person_nodes = [n for n in merged["nodes"] if n["entity_type"] == "person"]
        assert len(person_nodes) == 1
        assert person_nodes[0]["mention_count"] == 2

    @patch("epocha.apps.knowledge.merge.embed_texts")
    def test_different_entities_not_merged(self, mock_embed):
        # Two different people
        mock_embed.return_value = [[0.9] * 1024, [0.1] * 1024]

        results = [
            ExtractionResult(
                chunk_id=0,
                entities=[_entity("Robespierre", chunk_id=0)],
                relations=[],
            ),
            ExtractionResult(
                chunk_id=1,
                entities=[_entity("Danton", chunk_id=1)],
                relations=[],
            ),
        ]

        merged = merge_extraction_results(results)
        person_nodes = [n for n in merged["nodes"] if n["entity_type"] == "person"]
        assert len(person_nodes) == 2

    @patch("epocha.apps.knowledge.merge.embed_texts")
    def test_collects_unrecognized(self, mock_embed):
        mock_embed.return_value = []
        results = [
            ExtractionResult(
                chunk_id=0,
                entities=[],
                relations=[],
                unrecognized_entities=[{"entity_type": "dragon", "name": "Smaug"}],
                unrecognized_relations=[{"relation_type": "breathes_fire"}],
            ),
        ]

        merged = merge_extraction_results(results)
        assert len(merged["unrecognized_entities"]) == 1
        assert len(merged["unrecognized_relations"]) == 1

    @patch("epocha.apps.knowledge.merge.embed_texts")
    def test_output_has_expected_keys(self, mock_embed):
        mock_embed.return_value = [[0.5] * 1024]
        results = [
            ExtractionResult(
                chunk_id=0,
                entities=[_entity("Robespierre", chunk_id=0)],
                relations=[_relation("Robespierre", "Jacobin Club", chunk_id=0)],
            ),
        ]

        merged = merge_extraction_results(results)
        assert "nodes" in merged
        assert "relations" in merged
        assert "unrecognized_entities" in merged
        assert "unrecognized_relations" in merged
        assert "stats" in merged
        assert "nodes_before_merge" in merged["stats"]
        assert "nodes_after_merge" in merged["stats"]
```

- [ ] **Step 2: Run merge tests to verify they fail**

Run: `docker compose -f docker-compose.local.yml run --rm web pytest epocha/apps/knowledge/tests/test_merge.py -v`

Expected: ImportError for `epocha.apps.knowledge.merge`.

- [ ] **Step 3: Implement the merge module**

Create `epocha/apps/knowledge/merge.py`:

```python
"""Cross-chunk merge and deduplication of extracted entities and relations.

After per-chunk extraction (extraction.py), entities may appear in multiple
chunks with slight name variations. This module normalizes canonical names,
groups entities by type, detects duplicates via embedding cosine similarity,
and merges clusters according to explicit rules documented in the spec.

The merge result is a JSON-serializable dict ready for ExtractionCache
persistence.
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
    """Compute an NxN cosine similarity matrix from a list of vectors."""
    n = len(vectors)
    matrix = [[0.0] * n for _ in range(n)]

    # Pre-compute norms
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


def _single_linkage_clusters(
    similarity_matrix: list[list[float]], threshold: float
) -> list[list[int]]:
    """Perform single-linkage clustering on a similarity matrix.

    Pairs with similarity above the threshold are merged transitively:
    if A~B and B~C, then {A,B,C} form one cluster even if A and C
    are not directly similar above the threshold.
    """
    n = len(similarity_matrix)
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x, y):
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
    """Merge a cluster of duplicate entities into a single entity.

    Merge rules (from spec):
    - name: entity with the highest mention_count; tie-break by longest, then alpha
    - canonical_name: normalized form of the chosen name
    - description: concatenation of unique non-empty descriptions, truncated
    - source_type: "document" if any member has it, else "document_inferred"
    - confidence: max across members
    - mention_count: sum across members
    - attributes: dict-merge, key collision resolved by highest-confidence member
    - chunk_ids: union of all chunk_ids for citation tracking
    """
    if len(entities) == 1:
        entity = entities[0]
        entity["chunk_ids"] = [entity.pop("chunk_id", 0)]
        return entity

    # Sort for name selection: highest mention_count, then longest name, then alpha
    sorted_entities = sorted(
        entities,
        key=lambda e: (-e["mention_count"], -len(e["name"]), e["name"]),
    )
    chosen = sorted_entities[0]

    # Merge descriptions
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

    # Merge attributes (highest confidence wins on collision)
    entities_by_confidence = sorted(entities, key=lambda e: -e["confidence"])
    merged_attributes: dict = {}
    for e in reversed(entities_by_confidence):
        merged_attributes.update(e.get("attributes", {}))

    # Determine source_type
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
    """Deduplicate relations by their identity tuple.

    Identity = (source_canonical_name, source_entity_type, target_canonical_name,
    target_entity_type, relation_type, temporal_start_year, temporal_end_year).
    """
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for rel in relations:
        key = (
            rel["source_canonical_name"],
            rel["source_entity_type"],
            rel["target_canonical_name"],
            rel["target_entity_type"],
            rel["relation_type"],
            rel.get("temporal_start_year"),
            rel.get("temporal_end_year"),
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
    """Merge extraction results from multiple chunks into a single output.

    Steps:
    1. Collect all entities and relations from all chunks
    2. Group entities by (entity_type, canonical_name) for exact-match dedup
    3. Within each type group, compute embedding similarity and cluster
    4. Merge each cluster using the explicit merge rules
    5. Deduplicate relations
    6. Package for cache persistence
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

    # Group by entity_type
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

        # First pass: exact canonical name match (fast, no embedding needed)
        by_canonical: dict[str, list[dict]] = defaultdict(list)
        for e in entities:
            by_canonical[e["canonical_name"]].append(e)

        for canonical_name, group in by_canonical.items():
            if len(group) == 1:
                merged_nodes.append(_merge_entity_cluster(group))
                continue

            # Second pass: embedding-based similarity for the group
            texts = [f"{e['name']} {e['description']}" for e in group]
            vectors = embed_texts(texts)

            if not vectors or len(vectors) != len(group):
                # Fallback: treat each as separate
                for e in group:
                    merged_nodes.append(_merge_entity_cluster([e]))
                continue

            sim_matrix = _build_cosine_similarity_matrix(vectors)
            clusters = _single_linkage_clusters(sim_matrix, DEDUP_SIMILARITY_THRESHOLD)

            for cluster_indices in clusters:
                cluster_entities = [group[i] for i in cluster_indices]
                merged_nodes.append(_merge_entity_cluster(cluster_entities))

    # Deduplicate relations
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
```

- [ ] **Step 4: Run merge tests to verify they pass**

Run: `docker compose -f docker-compose.local.yml run --rm web pytest epocha/apps/knowledge/tests/test_merge.py -v`

Expected: all PASS.

- [ ] **Step 5: Run the full knowledge test suite (excluding slow)**

Run: `docker compose -f docker-compose.local.yml run --rm web pytest epocha/apps/knowledge/ -v -m "not slow"`

Expected: all PASS.

- [ ] **Step 6: Run the full project test suite**

Run: `docker compose -f docker-compose.local.yml run --rm web pytest -q -m "not slow"`

Expected: all tests pass.

- [ ] **Step 7: Commit**

```
feat(knowledge): add merge and deduplication for cross-chunk extraction

CHANGE: Add merge.py with cosine similarity matrix computation,
single-linkage clustering for entity deduplication, explicit merge
rules (name by mention count, description concatenation, source_type
priority, confidence max, mention_count sum, attribute merge by
confidence), and relation deduplication by identity tuple. The merge
output is a JSON-serializable dict ready for ExtractionCache.
```

---

## Self-Review Summary

After completing Tasks 6-8 in this plan, the extraction pipeline can:

1. Build a structured extraction prompt with the full ontology (10 types, 20 relations, examples, disambiguation rules, JSON schema)
2. Send each chunk to the LLM, parse the JSON output, validate against the vocabulary, assign source_type mechanically
3. Merge entities across chunks using exact canonical name grouping + embedding-based similarity clustering
4. Deduplicate relations by their identity tuple
5. Package the clean result for cache persistence

**What is NOT yet in place:**
- KnowledgeGraph, KnowledgeNode, KnowledgeRelation models (Part 3)
- Graph materialization from cache to per-simulation rows (Part 3)
- Celery orchestration tying stages 1-8 together (Part 3)
- World generator integration (Part 3)
- API endpoints and dashboard (Part 4)

**Transition:** After Part 2 is complete and reviewed, proceed to write Part 3 (Graph models, materialization, orchestration, world generator integration).

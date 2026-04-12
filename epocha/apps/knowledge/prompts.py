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
                "relation_type": (
                    "member_of|founder_of|leader_of|located_in|occurred_in|occurred_during"
                    "|believes_in|opposes|supports|ally_of|enemy_of|influences"
                    "|married_to|parent_of|sibling_of|caused_by|led_to|participated_in|authored|enacted"
                ),
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
  Note: if an entity has formal membership rules, leadership positions, and documented procedures,
  classify it as institution, not group.

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
  Examples: Declaration of the Rights of Man, Law of Suspects, Constitution of 1791,
  Civil Constitution of the Clergy.

- value: A cultural commitment of everyday life, not a political system.
  Test: "Is this something people live by daily rather than a system they argue for politically?"
  If yes, it is a value.
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
    """Build the system prompt for entity and relation extraction.

    Returns a fully self-contained prompt string encoding:
    - 10 entity type definitions with operational criteria and named examples
    - 20 relation type definitions grouped by category
    - Disambiguation rule with explicit priority order
    - Multilingual instruction (European documents, original language names)
    - Strict JSON output schema (EXTRACTION_JSON_SCHEMA)
    - Extraction rules prohibiting general knowledge addition
    """
    return f"""You are an expert knowledge graph extractor for historical and social simulation documents.

Your task: extract entities and relations from text passages, classifying each entity into exactly one \
of the defined types and each relation into exactly one of the defined relation types.

{_ENTITY_TYPE_DEFINITIONS}

{_RELATION_TYPE_DEFINITIONS}

LANGUAGE: The document may be in any European language. Keep entity name values in the original language \
of the document. Provide the description and passage_excerpt in the original language as well, without translation.

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
8. temporal_start and temporal_end: partial ISO dates (e.g. "1789", "1789-07", "1789-07-14") \
or empty string if not applicable."""


def build_extraction_user_prompt(chunk_text: str) -> str:
    """Build the user prompt wrapping a specific chunk of text.

    Args:
        chunk_text: The raw text of a single document chunk to extract from.

    Returns:
        A prompt string that instructs the LLM to extract entities and relations
        exclusively from the provided chunk, citing passage_excerpt for each item.
    """
    return f"""Extract all entities and relations from the following passage.

Cite the exact passage_excerpt from the text below that supports each extracted item. \
Do NOT extract facts from your general knowledge that are not supported by the passage.

---
{chunk_text}
---

Respond with a JSON object containing "entities" and "relations" arrays."""

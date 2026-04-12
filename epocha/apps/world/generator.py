"""Generate a complete world from a text prompt (Express mode).

The user provides a free-text description and the system builds an entire
simulation world: geographic zones with resources, and agents with
diverse personalities, roles, and backgrounds.

Supports two paths:
- **Prompt-only** (default): the user provides a free-text description
  and the LLM generates everything from scratch.
- **Knowledge-graph**: when a KnowledgeGraph is supplied, the generator
  builds a structured LLM prompt from graph nodes (persons, places,
  institutions, concepts, events) and links person nodes back to the
  created Agent instances after generation.

The LLM is asked to produce a structured JSON response which is then
parsed into Django model instances.
"""
from __future__ import annotations

import json
import logging
import random

from django.contrib.gis.geos import Point, Polygon

from epocha.apps.agents.enrichment import enrich_simulation_agents
from epocha.apps.agents.models import Agent
from epocha.apps.llm_adapter.client import get_llm_client
from epocha.common.utils import clean_llm_json

from .models import Government, Institution, World, Zone

logger = logging.getLogger(__name__)


_WORLD_GENERATION_PROMPT = """Based on the user's description, generate a world for a civilization simulation.

Respond ONLY with a JSON object with this exact structure:
{
    "world": {
        "economy_level": "simplified|base|full",
        "stability_index": 0.0-1.0
    },
    "zones": [
        {
            "name": "Zone Name",
            "type": "urban|rural|wilderness|commercial|industrial",
            "x": 0-100,
            "y": 0-100,
            "resources": {"food": N, "wood": N, "stone": N, "gold": N}
        }
    ],
    "agents": [
        {
            "name": "Full Name",
            "age": N,
            "role": "role in society",
            "gender": "male|female|non_binary",
            "personality": {
                "openness": 0.0-1.0,
                "conscientiousness": 0.0-1.0,
                "extraversion": 0.0-1.0,
                "agreeableness": 0.0-1.0,
                "neuroticism": 0.0-1.0,
                "background": "backstory",
                "ambitions": "goals",
                "weaknesses": "flaws",
                "values": "core beliefs"
            }
        }
    ]
}

Generate 3-5 zones and 10-30 agents with diverse personalities, roles, and relationships.
Make the world interesting with potential for conflict and cooperation.
"""


def generate_world_from_prompt(prompt: str, simulation, knowledge_graph=None) -> dict:
    """Build a complete world from a free-text prompt via LLM.

    When *knowledge_graph* is provided (a ``KnowledgeGraph`` instance),
    the prompt is built from graph nodes instead of using the raw user
    text alone, and person nodes are linked back to created agents.
    Without a graph the original prompt-only flow runs unchanged.

    Returns a summary dict with world_id, zone count, agent count, and
    enriched count.  Raises ``ValueError`` if the LLM returns unparsable
    output.
    """
    if knowledge_graph is not None:
        return _generate_from_knowledge_graph(
            simulation, knowledge_graph, hint_prompt=prompt,
        )

    client = get_llm_client()

    raw = client.complete(
        prompt=f"Create a world based on this description:\n\n{prompt}",
        system_prompt=_WORLD_GENERATION_PROMPT,
        temperature=0.8,
        max_tokens=4000,
    )

    try:
        data = json.loads(clean_llm_json(raw))
    except json.JSONDecodeError:
        logger.error("World generation returned invalid JSON: %s", raw[:200])
        raise ValueError("LLM returned invalid JSON for world generation")

    # Create World
    world_data = data.get("world", {})
    world = World.objects.create(
        simulation=simulation,
        economy_level=world_data.get("economy_level", "base"),
        stability_index=world_data.get("stability_index", 0.7),
        global_wealth=1000.0,
        distance_scale=133.0,
        tick_duration_hours=24.0,
    )

    # Create Government (default: democracy, neutral indicators)
    Government.objects.create(
        simulation=simulation,
        government_type="democracy",
        formed_at_tick=0,
    )

    # Create all 7 Institutions with neutral defaults
    for inst_type in Institution.InstitutionType.values:
        Institution.objects.create(
            simulation=simulation,
            institution_type=inst_type,
            health=0.5,
            independence=0.5,
            funding=0.5,
        )

    # Create Zones
    zones_created = 0
    for idx, zone_data in enumerate(data.get("zones", [])):
        # Generate zone geometry: rectangular boundary on an abstract grid
        col = idx % 3
        row = idx // 3
        x_offset = col * 120
        y_offset = row * 120
        boundary = Polygon.from_bbox((x_offset, y_offset, x_offset + 100, y_offset + 100))
        center = Point(x_offset + 50, y_offset + 50)

        Zone.objects.create(
            world=world,
            name=zone_data["name"],
            zone_type=zone_data.get("type", "urban"),
            boundary=boundary,
            center=center,
            resources=zone_data.get("resources", {}),
        )
        zones_created += 1

    # Create Agents
    agents_created = 0
    zones = list(Zone.objects.filter(world=world))
    for idx, agent_data in enumerate(data.get("agents", [])):
        # Place agent in a random position within a zone
        agent_zone = zones[idx % len(zones)] if zones else None
        if agent_zone and agent_zone.center:
            cx, cy = agent_zone.center.x, agent_zone.center.y
            loc = Point(cx + random.uniform(-40, 40), cy + random.uniform(-40, 40))
        else:
            loc = None

        Agent.objects.create(
            simulation=simulation,
            name=agent_data["name"],
            age=agent_data.get("age", 25),
            role=agent_data.get("role", "villager"),
            gender=agent_data.get("gender", "male"),
            personality=agent_data.get("personality", {}),
            location=loc,
            zone=agent_zone,
        )
        agents_created += 1

    # Enrich historical/real agents with biographical research
    enrichment_stats = enrich_simulation_agents(simulation)

    logger.info(
        "World generated for simulation %d: %d zones, %d agents (%d enriched)",
        simulation.id, zones_created, agents_created, enrichment_stats["enriched"],
    )

    return {
        "world_id": world.id,
        "zones": zones_created,
        "agents": agents_created,
        "enriched": enrichment_stats["enriched"],
    }


# ---------------------------------------------------------------------------
# Knowledge-graph path
# ---------------------------------------------------------------------------


def _build_kg_prompt_context(knowledge_graph) -> str:
    """Build a structured text block from knowledge graph nodes.

    Queries person, place, institution, concept, and event nodes ordered
    by mention_count (most prominent first) and formats them into labeled
    sections the LLM can use as grounding context.
    """
    persons = list(
        knowledge_graph.nodes.filter(entity_type="person").order_by("-mention_count"),
    )
    places = list(
        knowledge_graph.nodes.filter(entity_type="place").order_by("-mention_count"),
    )
    institutions = list(
        knowledge_graph.nodes.filter(entity_type="institution").order_by("-mention_count"),
    )
    ideologies = list(
        knowledge_graph.nodes.filter(entity_type="ideology").order_by("-mention_count"),
    )
    concepts = list(
        knowledge_graph.nodes.filter(entity_type="concept").order_by("-mention_count"),
    )
    events = list(
        knowledge_graph.nodes.filter(entity_type="event").order_by("-mention_count"),
    )

    parts: list[str] = []

    if persons:
        parts.append("PERSONS (will become agents):")
        for p in persons:
            role = p.attributes.get("role", "citizen")
            parts.append(f"- {p.name} (role: {role}): {p.description}")

    if places:
        parts.append("\nPLACES (will become zones):")
        for p in places:
            parts.append(f"- {p.name}: {p.description}")

    if institutions:
        parts.append("\nINSTITUTIONS:")
        for inst in institutions:
            parts.append(f"- {inst.name}: {inst.description}")

    if ideologies:
        parts.append("\nIDEOLOGIES:")
        for i in ideologies:
            parts.append(f"- {i.name}: {i.description}")

    if concepts:
        parts.append("\nCONCEPTS:")
        for c in concepts:
            parts.append(f"- {c.name}: {c.description}")

    if events:
        parts.append("\nEVENTS:")
        for ev in events:
            date = ev.attributes.get("date", "")
            date_str = f" ({date})" if date else ""
            parts.append(f"- {ev.name}{date_str}: {ev.description}")

    return "\n".join(parts)


def _generate_from_knowledge_graph(simulation, knowledge_graph, hint_prompt=""):
    """Generate a world using structured data from a knowledge graph.

    Builds an LLM prompt from graph nodes, parses the JSON response, and
    creates World / Zone / Agent instances. Person nodes whose name
    matches a created agent (case-insensitive) are linked via
    ``KnowledgeNode.linked_agent``.

    The optional *hint_prompt* is appended as additional context so the
    user can steer generation beyond what the graph alone provides.
    """
    client = get_llm_client()

    graph_context = _build_kg_prompt_context(knowledge_graph)

    additional = f"\nAdditional context: {hint_prompt}" if hint_prompt else ""

    user_prompt = (
        "Based on the following historical knowledge graph, create a world "
        "for a civilization simulation.\n\n"
        f"{graph_context}"
        f"{additional}\n\n"
        f"{_WORLD_GENERATION_PROMPT}"
    )

    raw = client.complete(
        prompt=user_prompt,
        system_prompt=(
            "You are generating a world for a civilization simulation "
            "based on structured historical data."
        ),
        temperature=0.8,
        max_tokens=4000,
    )

    try:
        data = json.loads(clean_llm_json(raw))
    except json.JSONDecodeError:
        logger.error("World generation from KG returned invalid JSON: %s", raw[:200])
        raise ValueError("LLM returned invalid JSON for world generation")

    # -- Create World --------------------------------------------------------
    world_data = data.get("world", {})
    world = World.objects.create(
        simulation=simulation,
        economy_level=world_data.get("economy_level", "base"),
        stability_index=world_data.get("stability_index", 0.7),
        global_wealth=1000.0,
        distance_scale=133.0,
        tick_duration_hours=24.0,
    )

    # -- Government (default) ------------------------------------------------
    Government.objects.create(
        simulation=simulation, government_type="democracy", formed_at_tick=0,
    )

    # -- Institutions (all 7 with neutral defaults) --------------------------
    for inst_type in Institution.InstitutionType.values:
        Institution.objects.create(
            simulation=simulation, institution_type=inst_type,
            health=0.5, independence=0.5, funding=0.5,
        )

    # -- Zones ---------------------------------------------------------------
    zones_created = 0
    for idx, zone_data in enumerate(data.get("zones", [])):
        col = idx % 3
        row = idx // 3
        x_offset = col * 120
        y_offset = row * 120
        boundary = Polygon.from_bbox((
            x_offset, y_offset, x_offset + 100, y_offset + 100,
        ))
        center = Point(x_offset + 50, y_offset + 50)
        Zone.objects.create(
            world=world, name=zone_data["name"],
            zone_type=zone_data.get("type", "urban"),
            boundary=boundary, center=center,
            resources=zone_data.get("resources", {}),
        )
        zones_created += 1

    # -- Agents and person-node linking --------------------------------------
    agents_created = 0
    zones = list(Zone.objects.filter(world=world))
    person_nodes = list(
        knowledge_graph.nodes.filter(entity_type="person"),
    )
    person_node_lookup = {p.name.lower(): p for p in person_nodes}

    for idx, agent_data in enumerate(data.get("agents", [])):
        agent_zone = zones[idx % len(zones)] if zones else None
        if agent_zone and agent_zone.center:
            cx, cy = agent_zone.center.x, agent_zone.center.y
            loc = Point(cx + random.uniform(-40, 40), cy + random.uniform(-40, 40))
        else:
            loc = None

        agent = Agent.objects.create(
            simulation=simulation,
            name=agent_data["name"],
            age=agent_data.get("age", 25),
            role=agent_data.get("role", "citizen"),
            gender=agent_data.get("gender", "male"),
            personality=agent_data.get("personality", {}),
            location=loc,
            zone=agent_zone,
        )
        agents_created += 1

        # Link person node to the newly created agent
        person_node = person_node_lookup.get(agent.name.lower())
        if person_node:
            person_node.linked_agent = agent
            person_node.save(update_fields=["linked_agent"])

    # -- Enrichment ----------------------------------------------------------
    enrichment_stats = enrich_simulation_agents(simulation)

    logger.info(
        "World generated from KG for simulation %d: %d zones, %d agents (%d enriched)",
        simulation.id, zones_created, agents_created, enrichment_stats["enriched"],
    )

    return {
        "world_id": world.id,
        "zones": zones_created,
        "agents": agents_created,
        "enriched": enrichment_stats["enriched"],
    }

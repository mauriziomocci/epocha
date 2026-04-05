"""Generate a complete world from a text prompt (Express mode).

The user provides a free-text description and the system builds an entire
simulation world: geographic zones with resources, and agents with
diverse personalities, roles, and backgrounds.

The LLM is asked to produce a structured JSON response which is then
parsed into Django model instances.
"""
from __future__ import annotations

import json
import logging

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


def generate_world_from_prompt(prompt: str, simulation) -> dict:
    """Build a complete world from a free-text prompt via LLM.

    Calls the configured LLM provider with a structured generation prompt,
    parses the JSON response, and creates World, Zone, and Agent instances
    in the database.

    Returns a summary dict with world_id, zone count, and agent count.
    Raises ValueError if the LLM returns unparsable output.
    """
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
    for zone_data in data.get("zones", []):
        Zone.objects.create(
            world=world,
            name=zone_data["name"],
            zone_type=zone_data.get("type", "rural"),
            position_x=zone_data.get("x", 0),
            position_y=zone_data.get("y", 0),
            resources=zone_data.get("resources", {}),
        )
        zones_created += 1

    # Create Agents
    agents_created = 0
    for agent_data in data.get("agents", []):
        Agent.objects.create(
            simulation=simulation,
            name=agent_data["name"],
            age=agent_data.get("age", 25),
            role=agent_data.get("role", "villager"),
            gender=agent_data.get("gender", "male"),
            personality=agent_data.get("personality", {}),
            position_x=agent_data.get("x", 50),
            position_y=agent_data.get("y", 50),
        )
        agents_created += 1

    # Enrich historical/real agents with biographical research
    from epocha.apps.agents.enrichment import enrich_simulation_agents

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

"""Agent biography enrichment pipeline.

When a simulation generates agents based on historical, real, or living
persons, this pipeline researches them via Wikipedia/web search and
enriches their personality profiles with historically accurate details.

Pipeline steps:
1. classify_historical_agents -- LLM identifies which agents are real
2. research_person -- Wikipedia + DuckDuckGo lookup per agent
3. enrich_agent_profile -- LLM rewrites personality using research data
4. enrich_simulation_agents -- orchestrates the full pipeline

The pipeline is called automatically during world generation and can
also be invoked on existing simulations via enrich_simulation_agents().
"""

from __future__ import annotations

import json
import logging

from epocha.apps.llm_adapter.client import get_llm_client
from epocha.common.utils import clean_llm_json

from .research import research_person

logger = logging.getLogger(__name__)


_CLASSIFY_PROMPT = """\
You are a historian. Given the following list of character names \
and roles from a simulation, identify which ones are based on \
real historical figures, living public figures, or otherwise \
documented real people.

Characters:
{agent_list}

Respond ONLY with a JSON array of names that are real/historical.
Example: ["Napoleon Bonaparte", "Cleopatra"]
If none are real people, respond with: []
"""

_ENRICH_PROMPT = """\
You are a historian and psychologist. Given biographical research \
about a real historical/public figure, create an accurate \
personality profile for use in a civilization simulation.

Character name: {name}
Character role: {role}
Current profile: {current_profile}

Biographical research:
{biography}

Based on the research, produce an accurate personality profile. \
Adjust the Big Five scores to reflect the person's documented \
temperament. Write detailed background, ambitions, weaknesses, \
values, fears, and beliefs based on historical evidence.

Respond ONLY with a JSON object:
{{
    "openness": 0.0-1.0,
    "conscientiousness": 0.0-1.0,
    "extraversion": 0.0-1.0,
    "agreeableness": 0.0-1.0,
    "neuroticism": 0.0-1.0,
    "background": "Detailed historical background (2-3 sentences)",
    "ambitions": "Known historical ambitions and goals",
    "weaknesses": "Documented flaws, vices, vulnerabilities",
    "values": "Core values based on historical actions",
    "fears": "Known fears or anxieties",
    "beliefs": "Religious, political, philosophical beliefs"
}}
"""


def classify_historical_agents(agents: list) -> list[str]:
    """Identify which agents are based on real historical/living people.

    Makes a single LLM call with all agent names and roles. Returns
    a list of names identified as real people.

    Args:
        agents: List of Agent model instances.

    Returns:
        List of agent name strings identified as historical/real.
    """
    client = get_llm_client()

    agent_list = "\n".join(f"- {a.name} ({a.role})" for a in agents)
    prompt = _CLASSIFY_PROMPT.format(agent_list=agent_list)

    try:
        raw = client.complete(
            prompt=prompt,
            system_prompt="You are a historian. Respond only with JSON.",
            temperature=0.1,
            max_tokens=500,
        )

        cleaned = clean_llm_json(raw)
        names = json.loads(cleaned)
        if isinstance(names, list):
            return [str(n) for n in names]
        return []

    except (json.JSONDecodeError, Exception):
        logger.exception("Failed to classify historical agents")
        return []


def enrich_agent_profile(agent, biography: str) -> bool:
    """Enrich an agent's personality profile using biographical research.

    Makes an LLM call to rewrite the personality dict with historically
    accurate details. Updates the agent in the database.

    Args:
        agent: Agent model instance.
        biography: Biographical text from research.

    Returns:
        True if the profile was updated, False on failure.
    """
    client = get_llm_client()

    prompt = _ENRICH_PROMPT.format(
        name=agent.name,
        role=agent.role,
        current_profile=json.dumps(agent.personality, indent=2),
        biography=biography,
    )

    try:
        raw = client.complete(
            prompt=prompt,
            system_prompt=("You are a historian. Respond only with JSON."),
            temperature=0.3,
            max_tokens=800,
        )

        cleaned = clean_llm_json(raw)
        new_personality = json.loads(cleaned)
        if not isinstance(new_personality, dict):
            logger.warning(
                "Enrichment returned non-dict for %s",
                agent.name,
            )
            return False

        agent.personality = new_personality
        agent.save(update_fields=["personality"])
        logger.info("Enriched profile for: %s", agent.name)
        return True

    except Exception:
        logger.exception(
            "Failed to enrich profile for %s",
            agent.name,
        )
        return False


def enrich_simulation_agents(
    simulation,
    language: str = "en",
) -> dict:
    """Run the full enrichment pipeline on a simulation's agents.

    Steps:
    1. Classify which agents are historical/real people
    2. Research each identified agent via Wikipedia/DuckDuckGo
    3. Enrich their personality profiles via LLM

    Can be called during world generation or on existing simulations.

    Args:
        simulation: Simulation model instance.
        language: Preferred Wikipedia language for research.

    Returns:
        Stats dict with keys: classified, researched, enriched.
    """
    from .models import Agent

    agents = list(Agent.objects.filter(simulation=simulation, is_alive=True))
    if not agents:
        return {"classified": 0, "researched": 0, "enriched": 0}

    logger.info(
        "Enrichment pipeline starting for simulation %d (%d agents)",
        simulation.id,
        len(agents),
    )

    # 1. Classify
    historical_names = classify_historical_agents(agents)
    logger.info(
        "Identified %d historical/real figures: %s",
        len(historical_names),
        historical_names,
    )

    # 2. Research and enrich each historical agent
    researched = 0
    enriched = 0
    agent_by_name = {a.name: a for a in agents}

    for name in historical_names:
        agent = agent_by_name.get(name)
        if not agent:
            logger.warning(
                "Classified name '%s' not found in agents",
                name,
            )
            continue

        biography = research_person(name, language=language)
        if not biography:
            logger.info("No research results for: %s", name)
            continue

        researched += 1

        if enrich_agent_profile(agent, biography):
            enriched += 1

    logger.info(
        "Enrichment complete for simulation %d: "
        "%d classified, %d researched, %d enriched",
        simulation.id,
        len(historical_names),
        researched,
        enriched,
    )

    return {
        "classified": len(historical_names),
        "researched": researched,
        "enriched": enriched,
    }

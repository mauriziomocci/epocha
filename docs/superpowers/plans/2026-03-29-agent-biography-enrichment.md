# Agent Biography Enrichment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Automatically research historical/real figures via Wikipedia and web search during world generation, producing rich biographical personality profiles instead of generic ones.

**Architecture:** A new `enrichment.py` module in the agents app provides the pipeline: classify which agents are real people (LLM call), research each via Wikipedia REST API (with DuckDuckGo fallback), then enrich their personality profiles with a second LLM call that incorporates the research. The pipeline hooks into `generator.py` after agent creation, and is also callable standalone for existing simulations.

**Tech Stack:** Wikipedia REST API, DuckDuckGo HTML search, `requests` (already in dependencies), OpenAI-compatible LLM

---

## File Map

| File | Action | Responsibility |
|------|--------|---------------|
| `epocha/apps/agents/enrichment.py` | Create | Full enrichment pipeline: classify, research, enrich, update |
| `epocha/apps/agents/research.py` | Create | Wikipedia + DuckDuckGo search functions (pure I/O, no LLM) |
| `epocha/apps/agents/tests/test_research.py` | Create | Tests for Wikipedia/DuckDuckGo search |
| `epocha/apps/agents/tests/test_enrichment.py` | Create | Tests for enrichment pipeline |
| `epocha/apps/world/generator.py` | Modify | Call enrichment after agent creation |

---

## Task 1: Wikipedia and Web Search Module

Build the research layer that fetches biographical data from Wikipedia and DuckDuckGo.

**Files:**
- Create: `epocha/apps/agents/research.py`
- Create: `epocha/apps/agents/tests/test_research.py`

- [ ] **Step 1: Write the failing tests**

Create `epocha/apps/agents/tests/test_research.py`:

```python
"""Tests for biographical research via Wikipedia and web search."""
from unittest.mock import patch, MagicMock

import pytest

from epocha.apps.agents.research import search_wikipedia, search_duckduckgo, research_person


class TestSearchWikipedia:
    @patch("epocha.apps.agents.research.requests.get")
    def test_returns_summary_for_known_person(self, mock_get):
        """Wikipedia search should return a biographical summary."""
        # Mock search response
        search_response = MagicMock()
        search_response.status_code = 200
        search_response.json.return_value = {
            "pages": [{"key": "Lucrezia_Borgia", "title": "Lucrezia Borgia"}]
        }

        # Mock summary response
        summary_response = MagicMock()
        summary_response.status_code = 200
        summary_response.json.return_value = {
            "title": "Lucrezia Borgia",
            "extract": "Lucrezia Borgia was an Italian noblewoman of the House of Borgia.",
        }

        mock_get.side_effect = [search_response, summary_response]

        result = search_wikipedia("Lucrezia Borgia")

        assert result is not None
        assert "Borgia" in result

    @patch("epocha.apps.agents.research.requests.get")
    def test_returns_none_for_unknown_person(self, mock_get):
        """Wikipedia search should return None if no results found."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"pages": []}
        mock_get.return_value = mock_response

        result = search_wikipedia("Zxqwerty Nonexistent Person")

        assert result is None

    @patch("epocha.apps.agents.research.requests.get")
    def test_handles_api_error_gracefully(self, mock_get):
        """Wikipedia search should return None on API errors."""
        mock_get.side_effect = Exception("Connection timeout")

        result = search_wikipedia("Lucrezia Borgia")

        assert result is None

    @patch("epocha.apps.agents.research.requests.get")
    def test_tries_english_fallback(self, mock_get):
        """If the first language returns no results, try English."""
        # First call (Italian): no results
        empty_response = MagicMock()
        empty_response.status_code = 200
        empty_response.json.return_value = {"pages": []}

        # Second call (English search): found
        search_response = MagicMock()
        search_response.status_code = 200
        search_response.json.return_value = {
            "pages": [{"key": "Lucrezia_Borgia", "title": "Lucrezia Borgia"}]
        }

        # Third call (English summary)
        summary_response = MagicMock()
        summary_response.status_code = 200
        summary_response.json.return_value = {
            "title": "Lucrezia Borgia",
            "extract": "Lucrezia Borgia was a noblewoman.",
        }

        mock_get.side_effect = [empty_response, search_response, summary_response]

        result = search_wikipedia("Lucrezia Borgia", language="it")

        assert result is not None


class TestSearchDuckDuckGo:
    @patch("epocha.apps.agents.research.requests.get")
    def test_returns_biography_snippet(self, mock_get):
        """DuckDuckGo should return an abstract text for known people."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "Abstract": "Lucrezia Borgia was a duchess and political pawn.",
            "RelatedTopics": [
                {"Text": "Known for alleged poisonings at the papal court."}
            ],
        }
        mock_get.return_value = mock_response

        result = search_duckduckgo("Lucrezia Borgia biography")

        assert result is not None
        assert "Borgia" in result

    @patch("epocha.apps.agents.research.requests.get")
    def test_returns_none_on_empty_result(self, mock_get):
        """DuckDuckGo should return None if no useful data found."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"Abstract": "", "RelatedTopics": []}
        mock_get.return_value = mock_response

        result = search_duckduckgo("Zxqwerty Nonexistent Person")

        assert result is None


class TestResearchPerson:
    @patch("epocha.apps.agents.research.search_duckduckgo")
    @patch("epocha.apps.agents.research.search_wikipedia")
    def test_uses_wikipedia_first(self, mock_wiki, mock_ddg):
        """research_person should prefer Wikipedia over DuckDuckGo."""
        mock_wiki.return_value = "Wikipedia bio text"

        result = research_person("Lucrezia Borgia")

        assert result == "Wikipedia bio text"
        mock_ddg.assert_not_called()

    @patch("epocha.apps.agents.research.search_duckduckgo")
    @patch("epocha.apps.agents.research.search_wikipedia")
    def test_falls_back_to_duckduckgo(self, mock_wiki, mock_ddg):
        """If Wikipedia returns nothing, fall back to DuckDuckGo."""
        mock_wiki.return_value = None
        mock_ddg.return_value = "DuckDuckGo bio text"

        result = research_person("Lucrezia Borgia")

        assert result == "DuckDuckGo bio text"

    @patch("epocha.apps.agents.research.search_duckduckgo")
    @patch("epocha.apps.agents.research.search_wikipedia")
    def test_returns_none_when_both_fail(self, mock_wiki, mock_ddg):
        """If both sources fail, return None."""
        mock_wiki.return_value = None
        mock_ddg.return_value = None

        result = research_person("Completely Unknown Person")

        assert result is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest epocha/apps/agents/tests/test_research.py -v`
Expected: FAIL (module not found)

- [ ] **Step 3: Implement the research module**

Create `epocha/apps/agents/research.py`:

```python
"""Biographical research via Wikipedia and web search.

Provides functions to look up information about historical, real, or
living persons. Used by the enrichment pipeline to build accurate
agent personality profiles.

Search strategy:
1. Wikipedia REST API (search + page summary)
2. DuckDuckGo Instant Answer API (fallback)

Both sources are free, require no API keys, and return structured data.
"""
from __future__ import annotations

import logging

import requests

logger = logging.getLogger(__name__)

_WIKIPEDIA_SEARCH_URL = "https://{lang}.wikipedia.org/w/rest.php/v1/search/page"
_WIKIPEDIA_SUMMARY_URL = "https://{lang}.wikipedia.org/api/rest_v1/page/summary/{title}"
_DUCKDUCKGO_API_URL = "https://api.duckduckgo.com/"

_REQUEST_TIMEOUT = 10
_USER_AGENT = "Epocha/1.0 (civilization simulator; research for agent profiles)"

# Maximum length of biographical text to return (characters).
# Keeps LLM context manageable while providing enough detail.
_MAX_BIO_LENGTH = 3000


def search_wikipedia(name: str, language: str = "en") -> str | None:
    """Search Wikipedia for a person and return their page summary.

    Tries the specified language first, then falls back to English.
    Returns the extract text or None if not found.

    Args:
        name: Full name of the person to search for.
        language: ISO 639-1 language code for the initial search.
    """
    headers = {"User-Agent": _USER_AGENT}

    # Try specified language first, then English as fallback
    languages = [language, "en"] if language != "en" else ["en"]

    for lang in languages:
        try:
            search_url = _WIKIPEDIA_SEARCH_URL.format(lang=lang)
            search_resp = requests.get(
                search_url,
                params={"q": name, "limit": 1},
                headers=headers,
                timeout=_REQUEST_TIMEOUT,
            )
            search_resp.raise_for_status()
            pages = search_resp.json().get("pages", [])

            if not pages:
                continue

            page_key = pages[0]["key"]
            summary_url = _WIKIPEDIA_SUMMARY_URL.format(lang=lang, title=page_key)
            summary_resp = requests.get(
                summary_url,
                headers=headers,
                timeout=_REQUEST_TIMEOUT,
            )
            summary_resp.raise_for_status()
            extract = summary_resp.json().get("extract", "")

            if extract:
                logger.info("Wikipedia (%s) found bio for: %s", lang, name)
                return extract[:_MAX_BIO_LENGTH]

        except Exception:
            logger.warning("Wikipedia search failed for '%s' (lang=%s)", name, lang)

    return None


def search_duckduckgo(query: str) -> str | None:
    """Search DuckDuckGo Instant Answer API for biographical information.

    Returns the abstract and first few related topics as a single text,
    or None if no useful data is found.

    Args:
        query: Search query (typically "Name biography").
    """
    try:
        resp = requests.get(
            _DUCKDUCKGO_API_URL,
            params={"q": query, "format": "json", "no_html": 1, "skip_disambig": 1},
            headers={"User-Agent": _USER_AGENT},
            timeout=_REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()

        parts = []
        abstract = data.get("Abstract", "")
        if abstract:
            parts.append(abstract)

        for topic in data.get("RelatedTopics", [])[:5]:
            text = topic.get("Text", "")
            if text:
                parts.append(text)

        if not parts:
            return None

        result = "\n".join(parts)
        logger.info("DuckDuckGo found bio for: %s", query)
        return result[:_MAX_BIO_LENGTH]

    except Exception:
        logger.warning("DuckDuckGo search failed for '%s'", query)
        return None


def research_person(name: str, language: str = "en") -> str | None:
    """Research a person using Wikipedia first, DuckDuckGo as fallback.

    Args:
        name: Full name of the person.
        language: Preferred Wikipedia language for the initial search.

    Returns:
        Biographical text or None if nothing found.
    """
    result = search_wikipedia(name, language=language)
    if result:
        return result

    return search_duckduckgo(f"{name} biography")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest epocha/apps/agents/tests/test_research.py -v`
Expected: All 9 tests PASS

- [ ] **Step 5: Commit**

```
feat(agents): add Wikipedia and DuckDuckGo biographical research module

CHANGE: New research module provides biographical lookup for agent
profile enrichment. Searches Wikipedia REST API first (with language
fallback), then DuckDuckGo Instant Answer API. Used during world
generation to identify and research historical/real figures.
```

---

## Task 2: Enrichment Pipeline

Build the enrichment pipeline that classifies agents, researches them, and enriches their profiles via LLM.

**Files:**
- Create: `epocha/apps/agents/enrichment.py`
- Create: `epocha/apps/agents/tests/test_enrichment.py`

- [ ] **Step 1: Write the failing tests**

Create `epocha/apps/agents/tests/test_enrichment.py`:

```python
"""Tests for the agent biography enrichment pipeline."""
from unittest.mock import patch, MagicMock

import pytest

from epocha.apps.agents.enrichment import (
    classify_historical_agents,
    enrich_agent_profile,
    enrich_simulation_agents,
)
from epocha.apps.agents.models import Agent
from epocha.apps.simulation.models import Simulation
from epocha.apps.users.models import User
from epocha.apps.world.models import World, Zone


@pytest.fixture
def user(db):
    return User.objects.create_user(
        email="enrich@epocha.dev", username="enrichtest", password="pass123"
    )


@pytest.fixture
def simulation(user):
    sim = Simulation.objects.create(name="EnrichTest", seed=42, owner=user)
    world = World.objects.create(simulation=sim)
    Zone.objects.create(world=world, name="Roma", zone_type="urban")
    return sim


@pytest.fixture
def agents(simulation):
    lucrezia = Agent.objects.create(
        simulation=simulation, name="Lucrezia Borgia", role="Duchessa",
        personality={"openness": 0.8, "background": "Figlia del Papa"},
    )
    marco = Agent.objects.create(
        simulation=simulation, name="Marco il Fabbro", role="Fabbro",
        personality={"openness": 0.5, "background": "A blacksmith"},
    )
    cesare = Agent.objects.create(
        simulation=simulation, name="Cesare Borgia", role="Condottiero",
        personality={"openness": 0.4, "background": "Figlio del Papa"},
    )
    return [lucrezia, marco, cesare]


class TestClassifyHistoricalAgents:
    @patch("epocha.apps.agents.enrichment.get_llm_client")
    def test_identifies_historical_figures(self, mock_get_client, agents):
        """The classifier should return names of historical/real figures."""
        mock_client = MagicMock()
        mock_client.complete.return_value = '["Lucrezia Borgia", "Cesare Borgia"]'
        mock_client.get_model_name.return_value = "test-model"
        mock_get_client.return_value = mock_client

        result = classify_historical_agents(agents)

        assert "Lucrezia Borgia" in result
        assert "Cesare Borgia" in result
        assert "Marco il Fabbro" not in result

    @patch("epocha.apps.agents.enrichment.get_llm_client")
    def test_returns_empty_list_on_parse_error(self, mock_get_client, agents):
        """If LLM returns invalid JSON, return empty list."""
        mock_client = MagicMock()
        mock_client.complete.return_value = "I think Lucrezia is historical"
        mock_client.get_model_name.return_value = "test-model"
        mock_get_client.return_value = mock_client

        result = classify_historical_agents(agents)

        assert result == []


@pytest.mark.django_db
class TestEnrichAgentProfile:
    @patch("epocha.apps.agents.enrichment.get_llm_client")
    def test_updates_personality_with_research(self, mock_get_client, agents):
        """enrich_agent_profile should update the agent's personality dict."""
        mock_client = MagicMock()
        mock_client.complete.return_value = """{
            "openness": 0.7,
            "conscientiousness": 0.6,
            "extraversion": 0.7,
            "agreeableness": 0.3,
            "neuroticism": 0.6,
            "background": "Daughter of Pope Alexander VI, renowned for her political marriages.",
            "ambitions": "Political independence from her family",
            "weaknesses": "Loyalty to a corrupt family",
            "values": "Family, survival, culture",
            "fears": "Being used as a political pawn",
            "beliefs": "Power through intelligence rather than force"
        }"""
        mock_client.get_model_name.return_value = "test-model"
        mock_get_client.return_value = mock_client

        lucrezia = agents[0]
        enrich_agent_profile(lucrezia, "Lucrezia Borgia was an Italian noblewoman...")

        lucrezia.refresh_from_db()
        assert "Pope Alexander VI" in lucrezia.personality.get("background", "")
        assert lucrezia.personality.get("fears") is not None

    @patch("epocha.apps.agents.enrichment.get_llm_client")
    def test_preserves_agent_on_llm_failure(self, mock_get_client, agents):
        """If LLM enrichment fails, the agent should keep the original profile."""
        mock_client = MagicMock()
        mock_client.complete.side_effect = Exception("LLM error")
        mock_client.get_model_name.return_value = "test-model"
        mock_get_client.return_value = mock_client

        lucrezia = agents[0]
        original_bg = lucrezia.personality.get("background")

        enrich_agent_profile(lucrezia, "Some bio text")

        lucrezia.refresh_from_db()
        assert lucrezia.personality.get("background") == original_bg


@pytest.mark.django_db
class TestEnrichSimulationAgents:
    @patch("epocha.apps.agents.enrichment.research_person")
    @patch("epocha.apps.agents.enrichment.classify_historical_agents")
    @patch("epocha.apps.agents.enrichment.get_llm_client")
    def test_enriches_identified_historical_agents(
        self, mock_get_client, mock_classify, mock_research, simulation, agents
    ):
        """The full pipeline should research and enrich historical agents only."""
        mock_classify.return_value = ["Lucrezia Borgia"]
        mock_research.return_value = "Lucrezia Borgia was a noblewoman and alleged poisoner."

        mock_client = MagicMock()
        mock_client.complete.return_value = """{
            "openness": 0.7,
            "conscientiousness": 0.5,
            "extraversion": 0.6,
            "agreeableness": 0.3,
            "neuroticism": 0.6,
            "background": "Italian noblewoman and alleged poisoner",
            "ambitions": "Independence",
            "values": "Family, power"
        }"""
        mock_client.get_model_name.return_value = "test-model"
        mock_get_client.return_value = mock_client

        stats = enrich_simulation_agents(simulation)

        assert stats["researched"] == 1
        assert stats["enriched"] == 1
        # Marco (fictional) should NOT have been researched
        mock_research.assert_called_once_with("Lucrezia Borgia", language="en")

    @patch("epocha.apps.agents.enrichment.research_person")
    @patch("epocha.apps.agents.enrichment.classify_historical_agents")
    @patch("epocha.apps.agents.enrichment.get_llm_client")
    def test_skips_agents_with_no_research_results(
        self, mock_get_client, mock_classify, mock_research, simulation, agents
    ):
        """Agents with no research results should be skipped."""
        mock_classify.return_value = ["Lucrezia Borgia"]
        mock_research.return_value = None

        mock_client = MagicMock()
        mock_client.get_model_name.return_value = "test-model"
        mock_get_client.return_value = mock_client

        stats = enrich_simulation_agents(simulation)

        assert stats["researched"] == 0
        assert stats["enriched"] == 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest epocha/apps/agents/tests/test_enrichment.py -v`
Expected: FAIL (module not found)

- [ ] **Step 3: Implement the enrichment pipeline**

Create `epocha/apps/agents/enrichment.py`:

```python
"""Agent biography enrichment pipeline.

When a simulation generates agents based on historical, real, or living
persons, this pipeline researches them via Wikipedia/web search and
enriches their personality profiles with historically accurate details.

Pipeline steps:
1. classify_historical_agents -- LLM identifies which agents are real people
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

from .research import research_person

logger = logging.getLogger(__name__)


_CLASSIFY_PROMPT = """You are a historian. Given the following list of character names and roles
from a simulation, identify which ones are based on real historical figures,
living public figures, or otherwise documented real people.

Characters:
{agent_list}

Respond ONLY with a JSON array of names that are real/historical people.
Example: ["Napoleon Bonaparte", "Cleopatra"]
If none are real people, respond with: []
"""

_ENRICH_PROMPT = """You are a historian and psychologist. Given biographical research about a real
historical/public figure, create an accurate personality profile for use in a
civilization simulation.

Character name: {name}
Character role: {role}
Current profile: {current_profile}

Biographical research:
{biography}

Based on the research, produce an accurate personality profile. Adjust the Big Five
scores to reflect the person's documented temperament. Write detailed background,
ambitions, weaknesses, values, fears, and beliefs based on historical evidence.

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

        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned[cleaned.index("\n") + 1:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

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
            system_prompt="You are a historian. Respond only with JSON.",
            temperature=0.3,
            max_tokens=800,
        )

        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned[cleaned.index("\n") + 1:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        new_personality = json.loads(cleaned)
        if not isinstance(new_personality, dict):
            logger.warning("Enrichment returned non-dict for %s", agent.name)
            return False

        agent.personality = new_personality
        agent.save(update_fields=["personality"])
        logger.info("Enriched profile for: %s", agent.name)
        return True

    except Exception:
        logger.exception("Failed to enrich profile for %s", agent.name)
        return False


def enrich_simulation_agents(simulation, language: str = "en") -> dict:
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
        simulation.id, len(agents),
    )

    # 1. Classify
    historical_names = classify_historical_agents(agents)
    logger.info("Identified %d historical/real figures: %s", len(historical_names), historical_names)

    # 2. Research and enrich each historical agent
    researched = 0
    enriched = 0
    agent_by_name = {a.name: a for a in agents}

    for name in historical_names:
        agent = agent_by_name.get(name)
        if not agent:
            logger.warning("Classified name '%s' not found in agents", name)
            continue

        biography = research_person(name, language=language)
        if not biography:
            logger.info("No research results for: %s", name)
            continue

        researched += 1

        if enrich_agent_profile(agent, biography):
            enriched += 1

    logger.info(
        "Enrichment complete for simulation %d: %d classified, %d researched, %d enriched",
        simulation.id, len(historical_names), researched, enriched,
    )

    return {
        "classified": len(historical_names),
        "researched": researched,
        "enriched": enriched,
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest epocha/apps/agents/tests/test_enrichment.py -v`
Expected: All 7 tests PASS

- [ ] **Step 5: Commit**

```
feat(agents): add biography enrichment pipeline for historical figures

CHANGE: New enrichment module classifies which agents are real
historical/living people (via LLM), researches them via Wikipedia
and DuckDuckGo, then enriches their personality profiles with
historically accurate details. Can run during world generation
or on existing simulations.
```

---

## Task 3: Wire Enrichment Into World Generator and Update Existing Agents

Hook the enrichment pipeline into `generator.py` so it runs automatically after agent creation. Also update the existing Borgia simulation agents.

**Files:**
- Modify: `epocha/apps/world/generator.py`

- [ ] **Step 1: Add enrichment call to `generate_world_from_prompt`**

In `epocha/apps/world/generator.py`, after the agent creation loop, add the enrichment call. The modified section of `generate_world_from_prompt` (after line 141 `agents_created += 1`):

```python
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
```

Remove the existing `logger.info` and `return` block that this replaces (lines 143-152).

- [ ] **Step 2: Run existing world generator tests**

Run: `pytest epocha/apps/world/tests/test_generator.py -v`
Expected: All tests PASS (the enrichment call is mocked transitively since tests mock the LLM client)

- [ ] **Step 3: Run full test suite**

Run: `pytest --cov=epocha -v`
Expected: All tests PASS

- [ ] **Step 4: Commit**

```
feat(world): auto-enrich historical agents during world generation

CHANGE: World generator now calls the enrichment pipeline after
creating agents. Historical and real figures are automatically
researched via Wikipedia/DuckDuckGo and their personality profiles
are enriched with accurate biographical details.
```

- [ ] **Step 5: Update existing Borgia simulation agents**

Run the enrichment pipeline on the existing simulation (ID 1) via Django shell:

```bash
docker compose -f docker-compose.local.yml exec web python manage.py shell -c "
from epocha.apps.simulation.models import Simulation
from epocha.apps.agents.enrichment import enrich_simulation_agents
sim = Simulation.objects.get(id=1)
stats = enrich_simulation_agents(sim, language='it')
print(f'Results: {stats}')
"
```

Verify Lucrezia's profile was enriched:

```bash
docker compose -f docker-compose.local.yml exec web python manage.py shell -c "
from epocha.apps.agents.models import Agent
a = Agent.objects.get(name='Lucrezia Borgia')
import json
print(json.dumps(a.personality, indent=2, ensure_ascii=False))
"
```

---

## Summary

| Task | What it builds |
|------|---------------|
| 1 | Wikipedia + DuckDuckGo research module (`research.py`) |
| 2 | Enrichment pipeline: classify, research, enrich (`enrichment.py`) |
| 3 | Wire into generator + update existing Borgia agents |

After completion:
- Every new simulation automatically researches historical/real agents
- Wikipedia is tried first (with language fallback), DuckDuckGo as backup
- One LLM call classifies all agents, one LLM call per historical agent enriches the profile
- Existing simulations can be enriched via `enrich_simulation_agents(simulation)`
- Fictional agents are untouched

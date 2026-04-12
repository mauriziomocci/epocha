"""Tests for knowledge-graph-based world generation.

When a KnowledgeGraph is available, the generator should build the LLM
prompt from graph nodes (persons, places, institutions, concepts, events)
and link person nodes back to the created Agent instances.
"""
import json
from unittest.mock import MagicMock, patch

import pytest

from epocha.apps.agents.models import Agent
from epocha.apps.knowledge.models import (
    ExtractionCache,
    KnowledgeGraph,
    KnowledgeNode,
)
from epocha.apps.simulation.models import Simulation
from epocha.apps.users.models import User
from epocha.apps.world.generator import generate_world_from_prompt


@pytest.fixture
def user(db):
    return User.objects.create_user(
        email="gen@epocha.dev", username="genuser", password="pass1234",
    )


@pytest.fixture
def simulation(user):
    return Simulation.objects.create(name="GenTest", seed=42, owner=user)


@pytest.fixture
def knowledge_graph(simulation):
    cache = ExtractionCache.objects.create(
        cache_key="gen" + "0" * 61,
        documents_hash="gen" + "0" * 61,
        ontology_version="v1",
        extraction_prompt_version="v1",
        llm_model="test",
        extracted_data={},
        stats={},
    )
    graph = KnowledgeGraph.objects.create(
        simulation=simulation, extraction_cache=cache, status="ready",
    )
    KnowledgeNode.objects.create(
        graph=graph, entity_type="person",
        name="Robespierre", canonical_name="robespierre",
        description="Leader of the Jacobins",
        source_type="document", confidence=0.9, mention_count=5,
        attributes={"role": "deputy"}, embedding=[0.1] * 1024,
    )
    KnowledgeNode.objects.create(
        graph=graph, entity_type="person",
        name="Louis XVI", canonical_name="louis xvi",
        description="King of France",
        source_type="document", confidence=0.9, mention_count=3,
        attributes={"role": "king"}, embedding=[0.2] * 1024,
    )
    KnowledgeNode.objects.create(
        graph=graph, entity_type="place",
        name="Paris", canonical_name="paris",
        description="Capital of France",
        source_type="document", confidence=0.9, mention_count=4,
        attributes={}, embedding=[0.3] * 1024,
    )
    KnowledgeNode.objects.create(
        graph=graph, entity_type="institution",
        name="National Assembly", canonical_name="national assembly",
        description="Legislative body",
        source_type="document", confidence=0.9, mention_count=2,
        attributes={}, embedding=[0.4] * 1024,
    )
    KnowledgeNode.objects.create(
        graph=graph, entity_type="ideology",
        name="Jacobinism", canonical_name="jacobinism",
        description="Radical revolutionary ideology",
        source_type="document", confidence=0.8, mention_count=2,
        attributes={}, embedding=[0.5] * 1024,
    )
    KnowledgeNode.objects.create(
        graph=graph, entity_type="event",
        name="Storming of the Bastille", canonical_name="storming of the bastille",
        description="Uprising that marked the start of the Revolution",
        source_type="document", confidence=0.95, mention_count=6,
        attributes={"date": "14 July 1789"}, embedding=[0.6] * 1024,
    )
    return graph


@pytest.fixture
def mock_llm():
    with patch("epocha.apps.world.generator.get_llm_client") as mock:
        client = MagicMock()
        mock.return_value = client
        yield client


@pytest.fixture
def mock_enrichment():
    with patch("epocha.apps.world.generator.enrich_simulation_agents") as mock:
        mock.return_value = {"enriched": 0, "skipped": 0, "errors": 0}
        yield mock


@pytest.mark.django_db
class TestGenerateFromKnowledgeGraph:
    """Tests for the knowledge-graph dispatch path in generate_world_from_prompt."""

    def test_creates_agents_from_person_nodes(
        self, simulation, knowledge_graph, mock_llm, mock_enrichment,
    ):
        """Person nodes in the graph should become Agent instances."""
        mock_llm.complete.return_value = json.dumps({
            "world": {"economy_level": "base", "stability_index": 0.5},
            "zones": [{"name": "Paris", "type": "urban", "resources": {}}],
            "agents": [
                {
                    "name": "Robespierre", "age": 31, "role": "deputy",
                    "gender": "male",
                    "personality": {
                        "openness": 0.7, "conscientiousness": 0.8,
                        "extraversion": 0.4, "agreeableness": 0.3,
                        "neuroticism": 0.6,
                    },
                },
                {
                    "name": "Louis XVI", "age": 35, "role": "king",
                    "gender": "male",
                    "personality": {
                        "openness": 0.3, "conscientiousness": 0.5,
                        "extraversion": 0.3, "agreeableness": 0.6,
                        "neuroticism": 0.7,
                    },
                },
            ],
        })

        result = generate_world_from_prompt(
            "French Revolution 1789", simulation, knowledge_graph=knowledge_graph,
        )

        assert result["agents"] >= 2
        assert result["zones"] >= 1
        assert Agent.objects.filter(simulation=simulation, name="Robespierre").exists()
        assert Agent.objects.filter(simulation=simulation, name="Louis XVI").exists()

    def test_prompt_contains_person_nodes(
        self, simulation, knowledge_graph, mock_llm, mock_enrichment,
    ):
        """The LLM prompt must include person node names from the graph."""
        mock_llm.complete.return_value = json.dumps({
            "world": {"economy_level": "base", "stability_index": 0.5},
            "zones": [], "agents": [],
        })

        generate_world_from_prompt(
            "test", simulation, knowledge_graph=knowledge_graph,
        )

        call_args = mock_llm.complete.call_args
        prompt_text = call_args.kwargs.get("prompt", "")
        assert "Robespierre" in prompt_text
        assert "Louis XVI" in prompt_text

    def test_prompt_contains_places_and_institutions(
        self, simulation, knowledge_graph, mock_llm, mock_enrichment,
    ):
        """The LLM prompt must include place and institution nodes."""
        mock_llm.complete.return_value = json.dumps({
            "world": {"economy_level": "base", "stability_index": 0.5},
            "zones": [], "agents": [],
        })

        generate_world_from_prompt(
            "test", simulation, knowledge_graph=knowledge_graph,
        )

        call_args = mock_llm.complete.call_args
        prompt_text = call_args.kwargs.get("prompt", "")
        assert "Paris" in prompt_text
        assert "National Assembly" in prompt_text

    def test_prompt_contains_concepts_and_events(
        self, simulation, knowledge_graph, mock_llm, mock_enrichment,
    ):
        """The LLM prompt must include concept and event nodes."""
        mock_llm.complete.return_value = json.dumps({
            "world": {"economy_level": "base", "stability_index": 0.5},
            "zones": [], "agents": [],
        })

        generate_world_from_prompt(
            "test", simulation, knowledge_graph=knowledge_graph,
        )

        call_args = mock_llm.complete.call_args
        prompt_text = call_args.kwargs.get("prompt", "")
        assert "Jacobinism" in prompt_text
        assert "Storming of the Bastille" in prompt_text
        assert "14 July 1789" in prompt_text

    def test_links_person_nodes_to_agents(
        self, simulation, knowledge_graph, mock_llm, mock_enrichment,
    ):
        """Person nodes should be linked to their Agent via linked_agent."""
        mock_llm.complete.return_value = json.dumps({
            "world": {"economy_level": "base", "stability_index": 0.5},
            "zones": [{"name": "Paris", "type": "urban", "resources": {}}],
            "agents": [
                {
                    "name": "Robespierre", "age": 31, "role": "deputy",
                    "gender": "male", "personality": {"openness": 0.7},
                },
            ],
        })

        generate_world_from_prompt(
            "test", simulation, knowledge_graph=knowledge_graph,
        )

        rob_node = knowledge_graph.nodes.get(canonical_name="robespierre")
        rob_node.refresh_from_db()
        assert rob_node.linked_agent is not None
        assert rob_node.linked_agent.name == "Robespierre"

    def test_unmatched_person_nodes_not_linked(
        self, simulation, knowledge_graph, mock_llm, mock_enrichment,
    ):
        """Person nodes without a matching agent should remain unlinked."""
        mock_llm.complete.return_value = json.dumps({
            "world": {"economy_level": "base", "stability_index": 0.5},
            "zones": [{"name": "Paris", "type": "urban", "resources": {}}],
            "agents": [
                {
                    "name": "Robespierre", "age": 31, "role": "deputy",
                    "gender": "male", "personality": {"openness": 0.7},
                },
            ],
        })

        generate_world_from_prompt(
            "test", simulation, knowledge_graph=knowledge_graph,
        )

        louis_node = knowledge_graph.nodes.get(canonical_name="louis xvi")
        louis_node.refresh_from_db()
        assert louis_node.linked_agent is None

    def test_existing_flow_still_works_without_graph(
        self, simulation, mock_llm, mock_enrichment,
    ):
        """Without a knowledge_graph argument, the original prompt flow runs."""
        mock_llm.complete.return_value = json.dumps({
            "world": {"economy_level": "base", "stability_index": 0.7},
            "zones": [{"name": "Village", "type": "rural", "resources": {}}],
            "agents": [
                {
                    "name": "Farmer", "age": 30, "role": "farmer",
                    "gender": "male", "personality": {"openness": 0.5},
                },
            ],
        })

        result = generate_world_from_prompt("A small village", simulation)

        assert result["agents"] >= 1
        assert result["zones"] >= 1
        # Verify the prompt does NOT contain KG-specific formatting
        call_args = mock_llm.complete.call_args
        prompt_text = call_args.kwargs.get("prompt", "")
        assert "PERSONS (will become agents):" not in prompt_text

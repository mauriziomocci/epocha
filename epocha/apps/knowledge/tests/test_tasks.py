"""Tests for the Celery orchestration task.

Verifies the full extraction pipeline (ingestion -> chunking -> embedding
-> cache check -> extraction -> merge -> cache persist -> materialize)
works end-to-end with mocked LLM and embedding dependencies.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from epocha.apps.knowledge.models import ExtractionCache, KnowledgeGraph
from epocha.apps.knowledge.tasks import extract_and_generate
from epocha.apps.simulation.models import Simulation
from epocha.apps.users.models import User

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "small_french_rev.txt"


@pytest.fixture
def user(db):
    return User.objects.create_user(
        email="task@epocha.dev",
        username="taskuser",
        password="pass1234",
    )


@pytest.fixture
def simulation(user):
    return Simulation.objects.create(name="TaskTest", seed=42, owner=user)


@pytest.fixture
def mock_llm_and_embed():
    """Mock all external dependencies: LLM client and embedding model.

    Patches four import paths:
    - extraction.get_llm_client: used by extract_from_chunk for LLM calls
    - tasks.get_llm_client: used by _check_cache for get_model_name()
    - merge.embed_texts: used during entity deduplication
    - embedding.get_embedding_model: used during chunk embedding
    """
    extraction_response = json.dumps(
        {
            "entities": [
                {
                    "entity_type": "person",
                    "name": "Robespierre",
                    "description": "A revolutionary",
                    "passage_excerpt": "Robespierre was a member of the Jacobin Club.",
                    "confidence": 0.9,
                    "attributes": {"role": "deputy"},
                }
            ],
            "relations": [],
        }
    )

    with (
        patch("epocha.apps.knowledge.extraction.get_llm_client") as mock_extraction_llm,
        patch("epocha.apps.knowledge.tasks.get_llm_client") as mock_tasks_llm,
        patch("epocha.apps.knowledge.merge.embed_texts") as mock_merge_embed,
        patch("epocha.apps.knowledge.embedding.get_embedding_model") as mock_model,
    ):
        # Both LLM client mocks share the same underlying mock so
        # call_count is tracked consistently across extraction and cache.
        client = MagicMock()
        client.complete.return_value = extraction_response
        client.get_model_name.return_value = "test-model"
        mock_extraction_llm.return_value = client
        mock_tasks_llm.return_value = client

        mock_merge_embed.return_value = [[0.1] * 1024]

        model = MagicMock()
        model.embed.return_value = iter([[0.1] * 1024])
        mock_model.return_value = model

        yield client


@pytest.mark.django_db(transaction=True)
class TestExtractAndGenerate:
    """End-to-end tests for the extract_and_generate pipeline."""

    def test_full_pipeline_creates_graph(self, simulation, user, mock_llm_and_embed):
        """The pipeline should ingest, chunk, extract, merge, cache,
        and materialize a knowledge graph with status 'ready'.
        """
        raw_text = FIXTURE_PATH.read_text(encoding="utf-8")
        doc_data = [
            {
                "raw_text": raw_text,
                "title": "French Revolution",
                "mime_type": "text/plain",
                "original_filename": "test.txt",
            }
        ]
        result = extract_and_generate(
            simulation_id=simulation.id,
            user_id=user.id,
            documents_data=doc_data,
            prompt="French Revolution 1789",
        )
        assert result["status"] == "ready"
        graph = KnowledgeGraph.objects.get(simulation=simulation)
        assert graph.status == "ready"
        assert graph.nodes.count() > 0

    def test_cache_hit_skips_extraction(self, simulation, user, mock_llm_and_embed):
        """When extraction results are already cached, the pipeline
        should reuse them without making additional LLM calls.
        """
        raw_text = "Some unique text for cache test."
        doc_data = [
            {
                "raw_text": raw_text,
                "title": "Cache Test",
                "mime_type": "text/plain",
                "original_filename": "cache.txt",
            }
        ]

        extract_and_generate(
            simulation_id=simulation.id,
            user_id=user.id,
            documents_data=doc_data,
            prompt="test",
        )
        call_count_first = mock_llm_and_embed.complete.call_count

        sim2 = Simulation.objects.create(name="CacheTest2", seed=99, owner=user)
        extract_and_generate(
            simulation_id=sim2.id,
            user_id=user.id,
            documents_data=doc_data,
            prompt="test",
        )
        call_count_second = mock_llm_and_embed.complete.call_count

        assert call_count_second == call_count_first
        assert ExtractionCache.objects.count() == 1
        cache_entry = ExtractionCache.objects.first()
        assert cache_entry.hit_count == 1

    def test_error_sets_failed_status(self, simulation, user):
        """When an internal error occurs, the pipeline should return
        status 'failed' and, if a graph exists, mark it accordingly.
        """
        with patch("epocha.apps.knowledge.tasks._run_ingestion") as mock_ingest:
            mock_ingest.side_effect = RuntimeError("ingestion failed")
            result = extract_and_generate(
                simulation_id=simulation.id,
                user_id=user.id,
                documents_data=[
                    {
                        "raw_text": "x",
                        "title": "t",
                        "mime_type": "text/plain",
                        "original_filename": "f",
                    }
                ],
                prompt="test",
            )
        assert result["status"] == "failed"
        assert "ingestion failed" in result["error"]

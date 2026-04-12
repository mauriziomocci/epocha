"""Tests for the embedding service."""
from unittest.mock import MagicMock, patch

import pytest

from epocha.apps.knowledge.embedding import EMBEDDING_DIM, embed_texts


class TestEmbedTextsMocked:
    def test_returns_list_of_vectors(self):
        with patch("epocha.apps.knowledge.embedding.get_embedding_model") as mock:
            mock_model = MagicMock()
            mock_model.embed.return_value = iter([[0.1] * EMBEDDING_DIM] * 3)
            mock.return_value = mock_model

            texts = ["first", "second", "third"]
            results = embed_texts(texts)

            assert len(results) == 3
            assert all(len(v) == EMBEDDING_DIM for v in results)

    def test_empty_input_returns_empty(self):
        results = embed_texts([])
        assert results == []


@pytest.mark.slow
class TestEmbedTextsReal:
    def test_real_model_produces_1024_dim_vectors(self):
        texts = ["The storming of the Bastille was a pivotal event."]
        results = embed_texts(texts)
        assert len(results) == 1
        assert len(results[0]) == EMBEDDING_DIM

    def test_real_model_is_deterministic(self):
        text = "Robespierre was a leader of the Jacobins."
        v1 = embed_texts([text])[0]
        v2 = embed_texts([text])[0]
        assert v1 == v2

    def test_real_model_multilingual(self):
        texts = [
            "The Bastille fell on July 14.",
            "La Bastille tomba le 14 juillet.",
            "La Bastiglia cadde il 14 luglio.",
        ]
        results = embed_texts(texts)
        assert len(results) == 3
        assert all(len(v) == EMBEDDING_DIM for v in results)

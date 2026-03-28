"""Tests for the LLM adapter client and OpenAI-compatible provider."""
from unittest.mock import MagicMock, patch

import pytest

from epocha.apps.llm_adapter.client import get_llm_client
from epocha.apps.llm_adapter.providers.openai import OpenAIProvider


class TestOpenAIProvider:
    def test_complete_returns_string(self):
        """Provider.complete() should return a string response."""
        provider = OpenAIProvider(api_key="test-key", model="gpt-4o-mini")

        with patch.object(provider, "_call_api") as mock_api:
            mock_api.return_value = {
                "content": "Hello, I am an AI.",
                "input_tokens": 10,
                "output_tokens": 5,
            }
            result = provider.complete(
                prompt="Say hello",
                system_prompt="You are helpful",
            )

        assert isinstance(result, str)
        assert result == "Hello, I am an AI."

    def test_get_cost_calculates_correctly(self):
        """Cost should be calculated from token counts."""
        provider = OpenAIProvider(api_key="test-key", model="gpt-4o-mini")
        cost = provider.get_cost(input_tokens=1000, output_tokens=500)
        assert cost > 0
        assert isinstance(cost, float)

    def test_get_model_name(self):
        provider = OpenAIProvider(api_key="test-key", model="gpt-4o-mini")
        assert provider.get_model_name() == "gpt-4o-mini"

    def test_base_url_passed_to_client(self):
        """Custom base_url should be forwarded to the OpenAI client."""
        with patch("openai.OpenAI") as mock_cls:
            OpenAIProvider(
                api_key="test-key",
                model="qwen3-8b",
                base_url="http://localhost:1234/v1",
            )
            mock_cls.assert_called_once_with(
                api_key="test-key",
                base_url="http://localhost:1234/v1",
            )

    def test_unknown_model_uses_default_pricing(self):
        """Unknown models should fall back to default pricing, not crash."""
        provider = OpenAIProvider(api_key="test-key", model="some-unknown-model")
        cost = provider.get_cost(input_tokens=1_000_000, output_tokens=1_000_000)
        assert cost > 0


class TestGetLLMClient:
    @pytest.mark.django_db
    def test_returns_openai_provider(self, settings):
        settings.EPOCHA_DEFAULT_LLM_PROVIDER = "openai"
        settings.EPOCHA_LLM_API_KEY = "test-key"
        settings.EPOCHA_LLM_MODEL = "gpt-4o-mini"
        settings.EPOCHA_LLM_BASE_URL = ""

        client = get_llm_client()
        assert isinstance(client, OpenAIProvider)

    @pytest.mark.django_db
    def test_returns_provider_with_base_url(self, settings):
        settings.EPOCHA_DEFAULT_LLM_PROVIDER = "openai"
        settings.EPOCHA_LLM_API_KEY = "test-key"
        settings.EPOCHA_LLM_MODEL = "qwen3-8b"
        settings.EPOCHA_LLM_BASE_URL = "http://localhost:1234/v1"

        client = get_llm_client()
        assert isinstance(client, OpenAIProvider)
        assert client.base_url == "http://localhost:1234/v1"

    @pytest.mark.django_db
    def test_unknown_provider_raises(self, settings):
        settings.EPOCHA_DEFAULT_LLM_PROVIDER = "unknown"

        with pytest.raises(ValueError, match="Unknown LLM provider"):
            get_llm_client()

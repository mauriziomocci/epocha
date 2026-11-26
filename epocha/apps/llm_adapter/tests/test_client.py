"""Tests for the LLM adapter client and OpenAI-compatible provider."""

from unittest.mock import patch

import pytest

from epocha.apps.llm_adapter.client import get_llm_client
from epocha.apps.llm_adapter.providers.openai import OpenAIProvider


@pytest.mark.django_db
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
    def test_chat_client_falls_back_to_main(self, settings):
        """Chat client should fall back to main provider when not configured."""
        from epocha.apps.llm_adapter.client import get_chat_llm_client

        settings.EPOCHA_DEFAULT_LLM_PROVIDER = "openai"
        settings.EPOCHA_LLM_API_KEY = "test-key"
        settings.EPOCHA_LLM_MODEL = "gpt-4o-mini"
        settings.EPOCHA_LLM_BASE_URL = ""
        settings.EPOCHA_CHAT_LLM_API_KEY = ""
        settings.EPOCHA_CHAT_LLM_MODEL = ""
        settings.EPOCHA_CHAT_LLM_BASE_URL = ""

        client = get_chat_llm_client()
        assert isinstance(client, OpenAIProvider)
        assert client.model == "gpt-4o-mini"  # Fell back to main


# Every provider the factories above can build, as (key setting, base URL
# setting). A new provider added to `client.py` belongs here too.
_LLM_PROVIDER_SETTINGS = [
    ("EPOCHA_LLM_API_KEY", "EPOCHA_LLM_BASE_URL"),
    ("EPOCHA_CHAT_LLM_API_KEY", "EPOCHA_CHAT_LLM_BASE_URL"),
]


@pytest.mark.parametrize(("key_setting", "base_url_setting"), _LLM_PROVIDER_SETTINGS)
def test_the_test_settings_configure_no_reachable_llm_provider(key_setting, base_url_setting):
    """No test can reach a real LLM endpoint through the factories.

    `config/settings/test.py` blanks every key and base URL, so a test that
    forgets to patch a factory fails at construction (`OpenAIProvider` with
    no key) instead of sending a paid request with the developer's own key.
    Round 16 of the Plan 4 phase-6 gate found a chat consumer test patching
    the wrong factory and calling the real chat provider on every suite run.
    The `settings` fixture of the tests above sets values and restores them;
    this test reads the module-level configuration the whole suite runs on.

    The comparison is reduced to a boolean before the assertion on purpose:
    pytest prints the operands of a failed comparison, and the operand here
    would be a real key.
    """
    from django.conf import settings

    key_is_blank = getattr(settings, key_setting) == ""
    base_url_is_blank = getattr(settings, base_url_setting) == ""
    assert key_is_blank, f"{key_setting} is set in the test settings"
    assert base_url_is_blank, f"{base_url_setting} is set in the test settings"

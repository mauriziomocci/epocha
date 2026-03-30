"""Unified client: single interface for calling any LLM.

Two providers can be configured:
- Main provider: for ticks, world generation, reports, event classification
- Chat provider: for conversations with agents (can be a smarter model)

If the chat provider is not configured, it falls back to the main provider.
If the chat provider hits rate limits, it falls back to the main provider
automatically via FallbackProvider.
"""
import logging

from django.conf import settings

from .providers.base import BaseLLMProvider
from .providers.openai import OpenAIProvider

logger = logging.getLogger(__name__)


class FallbackProvider(BaseLLMProvider):
    """Wraps a primary and fallback provider.

    Tries the primary provider first. If it raises any exception (typically
    rate limit errors after all retries are exhausted), falls back to the
    secondary provider transparently.
    """

    def __init__(self, primary: BaseLLMProvider, fallback: BaseLLMProvider):
        self._primary = primary
        self._fallback = fallback
        self._last_used = primary

    def complete(self, prompt, system_prompt="", temperature=0.7, max_tokens=1000, simulation_id=None):
        try:
            result = self._primary.complete(
                prompt=prompt, system_prompt=system_prompt,
                temperature=temperature, max_tokens=max_tokens,
                simulation_id=simulation_id,
            )
            self._last_used = self._primary
            return result
        except Exception:
            logger.warning(
                "Chat provider %s failed, falling back to %s",
                self._primary.get_model_name(), self._fallback.get_model_name(),
            )
            result = self._fallback.complete(
                prompt=prompt, system_prompt=system_prompt,
                temperature=temperature, max_tokens=max_tokens,
                simulation_id=simulation_id,
            )
            self._last_used = self._fallback
            return result

    def get_model_name(self):
        return self._last_used.get_model_name()

    def get_cost(self, input_tokens, output_tokens):
        return self._last_used.get_cost(input_tokens, output_tokens)

    def get_provider_info(self) -> dict:
        """Return info about which provider actually served the last request."""
        return self._last_used.get_provider_info()


def get_llm_client() -> BaseLLMProvider:
    """Factory: returns the main LLM provider (ticks, generation, reports)."""
    return OpenAIProvider(
        api_key=settings.EPOCHA_LLM_API_KEY,
        model=settings.EPOCHA_LLM_MODEL,
        base_url=settings.EPOCHA_LLM_BASE_URL or None,
    )


def get_chat_llm_client() -> BaseLLMProvider:
    """Factory: returns the chat-specific LLM provider.

    If a chat-specific provider is configured, wraps it in a FallbackProvider
    that falls back to the main provider on failure (e.g. rate limit).
    If no chat provider is configured, returns the main provider directly.
    """
    if settings.EPOCHA_CHAT_LLM_API_KEY and settings.EPOCHA_CHAT_LLM_MODEL:
        primary = OpenAIProvider(
            api_key=settings.EPOCHA_CHAT_LLM_API_KEY,
            model=settings.EPOCHA_CHAT_LLM_MODEL,
            base_url=settings.EPOCHA_CHAT_LLM_BASE_URL or None,
        )
        fallback = get_llm_client()
        return FallbackProvider(primary, fallback)
    return get_llm_client()

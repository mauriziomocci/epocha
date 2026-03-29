"""Unified client: single interface for calling any LLM.

Two providers can be configured:
- Main provider: for ticks, world generation, reports, event classification
- Chat provider: for conversations with agents (can be a smarter model)

If the chat provider is not configured, it falls back to the main provider.
"""
from django.conf import settings

from .providers.base import BaseLLMProvider
from .providers.openai import OpenAIProvider


def get_llm_client() -> BaseLLMProvider:
    """Factory: returns the main LLM provider (ticks, generation, reports)."""
    return OpenAIProvider(
        api_key=settings.EPOCHA_LLM_API_KEY,
        model=settings.EPOCHA_LLM_MODEL,
        base_url=settings.EPOCHA_LLM_BASE_URL or None,
    )


def get_chat_llm_client() -> BaseLLMProvider:
    """Factory: returns the chat-specific LLM provider.

    Falls back to the main provider if no chat-specific config is set.
    Use a smarter model here for better conversation quality.
    """
    if settings.EPOCHA_CHAT_LLM_API_KEY and settings.EPOCHA_CHAT_LLM_MODEL:
        return OpenAIProvider(
            api_key=settings.EPOCHA_CHAT_LLM_API_KEY,
            model=settings.EPOCHA_CHAT_LLM_MODEL,
            base_url=settings.EPOCHA_CHAT_LLM_BASE_URL or None,
        )
    return get_llm_client()

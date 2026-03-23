"""Unified client: single interface for calling any LLM."""
from django.conf import settings

from .providers.base import BaseLLMProvider
from .providers.openai import OpenAIProvider


def get_llm_client() -> BaseLLMProvider:
    """Factory: returns the configured LLM provider."""
    provider_name = settings.EPOCHA_DEFAULT_LLM_PROVIDER

    if provider_name == "openai":
        return OpenAIProvider(
            api_key=settings.EPOCHA_LLM_API_KEY,
            model=settings.EPOCHA_LLM_MODEL,
        )

    raise ValueError(f"Unknown LLM provider: {provider_name}")

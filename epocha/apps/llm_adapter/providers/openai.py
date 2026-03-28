"""OpenAI-compatible provider supporting any provider with the OpenAI API format.

Supports OpenAI, Google Gemini, Groq, OpenRouter, Together AI, Mistral,
LM Studio, Ollama, and any other provider exposing an OpenAI-compatible
chat completions endpoint via configurable base_url.
"""
from __future__ import annotations

import openai

from .base import BaseLLMProvider

# Pricing per 1M tokens. Used for cost estimation.
# Source: provider pricing pages as of March 2026. Update as needed.
# Models not listed here fall back to DEFAULT_PRICING.
MODEL_PRICING: dict[str, dict[str, float]] = {
    # OpenAI
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4.1": {"input": 2.00, "output": 8.00},
    # Google Gemini
    "gemini-2.5-flash-lite": {"input": 0.10, "output": 0.40},
    "gemini-2.5-flash": {"input": 0.30, "output": 2.50},
    "gemini-2.5-pro": {"input": 1.25, "output": 10.00},
    # Anthropic (via OpenRouter)
    "claude-haiku-4-5": {"input": 1.00, "output": 5.00},
    "claude-sonnet-4-6": {"input": 3.00, "output": 15.00},
}

# Fallback pricing for unlisted models (conservative estimate)
DEFAULT_PRICING: dict[str, float] = {"input": 1.00, "output": 5.00}


class OpenAIProvider(BaseLLMProvider):
    """OpenAI-compatible LLM provider.

    Connects to any provider that implements the OpenAI chat completions API.
    The base_url parameter determines the target:

    - None or "": OpenAI (default)
    - "https://generativelanguage.googleapis.com/v1beta/openai/": Gemini
    - "http://localhost:1234/v1": LM Studio
    - "http://localhost:11434/v1": Ollama
    - "https://api.groq.com/openai/v1": Groq
    """

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o-mini",
        base_url: str | None = None,
    ):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self._client = openai.OpenAI(api_key=api_key, base_url=base_url)

    def complete(
        self,
        prompt: str,
        system_prompt: str = "",
        temperature: float = 0.7,
        max_tokens: int = 1000,
        simulation_id: int | None = None,
    ) -> str:
        """Send a chat completion request, log cost, and return response text."""
        import time

        from epocha.apps.llm_adapter.models import LLMRequest

        start = time.monotonic()
        try:
            result = self._call_api(prompt, system_prompt, temperature, max_tokens)
            latency = int((time.monotonic() - start) * 1000)

            LLMRequest.objects.create(
                provider="openai",
                model=self.model,
                input_tokens=result["input_tokens"],
                output_tokens=result["output_tokens"],
                cost_usd=self.get_cost(result["input_tokens"], result["output_tokens"]),
                latency_ms=latency,
                success=True,
                simulation_id=simulation_id,
            )

            return result["content"]

        except Exception as e:
            latency = int((time.monotonic() - start) * 1000)
            LLMRequest.objects.create(
                provider="openai",
                model=self.model,
                input_tokens=0,
                output_tokens=0,
                cost_usd=0,
                latency_ms=latency,
                success=False,
                error_message=str(e),
                simulation_id=simulation_id,
            )
            raise

    def _call_api(
        self,
        prompt: str,
        system_prompt: str,
        temperature: float,
        max_tokens: int,
    ) -> dict:
        """Call the OpenAI-compatible chat completions endpoint.

        Returns a dict with content, input_tokens, and output_tokens.
        Separated from complete() to allow easy mocking in tests.
        """
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = self._client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        choice = response.choices[0]
        usage = response.usage

        return {
            "content": choice.message.content,
            "input_tokens": usage.prompt_tokens if usage else 0,
            "output_tokens": usage.completion_tokens if usage else 0,
        }

    def get_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate estimated cost in USD based on token counts.

        Uses MODEL_PRICING for known models, DEFAULT_PRICING otherwise.
        Pricing is per 1M tokens; we divide accordingly.
        """
        pricing = MODEL_PRICING.get(self.model, DEFAULT_PRICING)
        return (
            input_tokens * pricing["input"] + output_tokens * pricing["output"]
        ) / 1_000_000

    def get_model_name(self) -> str:
        return self.model

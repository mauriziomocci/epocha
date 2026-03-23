"""OpenAI provider — first provider for the MVP."""
from .base import BaseLLMProvider


class OpenAIProvider(BaseLLMProvider):
    """OpenAI implementation via SDK."""

    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        self.api_key = api_key
        self.model = model

    def complete(self, prompt: str, system_prompt: str = "", temperature: float = 0.7, max_tokens: int = 1000) -> str:
        raise NotImplementedError("To be implemented in MVP")

    def get_cost(self, input_tokens: int, output_tokens: int) -> float:
        raise NotImplementedError("To be implemented in MVP")

    def get_model_name(self) -> str:
        return self.model

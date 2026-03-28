"""Base interface for all LLM providers."""
from abc import ABC, abstractmethod


class BaseLLMProvider(ABC):
    """Common interface for all LLM providers."""

    @abstractmethod
    def complete(
        self,
        prompt: str,
        system_prompt: str = "",
        temperature: float = 0.7,
        max_tokens: int = 1000,
        simulation_id: int | None = None,
    ) -> str:
        """Generate a response from the model.

        Args:
            simulation_id: Optional simulation ID for cost tracking.
        """
        ...

    @abstractmethod
    def get_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate the cost in USD for a call."""
        ...

    @abstractmethod
    def get_model_name(self) -> str:
        """Return the name of the model in use."""
        ...

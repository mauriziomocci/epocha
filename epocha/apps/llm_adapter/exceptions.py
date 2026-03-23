"""Exceptions specific to the LLM Adapter."""


class LLMError(Exception):
    """Base error for all LLM errors."""


class LLMRateLimitError(LLMError):
    """Rate limit reached by the provider."""


class LLMProviderError(LLMError):
    """Generic provider error (timeout, 500, etc.)."""


class LLMIncoherentResponseError(LLMError):
    """The LLM response is not coherent with the context."""


class LLMBudgetExhaustedError(LLMError):
    """Maximum budget reached for the simulation."""

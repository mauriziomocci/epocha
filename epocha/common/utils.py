"""Shared utility functions used across Epocha apps."""


def clean_llm_json(raw: str) -> str:
    """Strip markdown code fences from LLM output.

    Many models wrap JSON responses in ```json ... ``` blocks. This extracts
    the content between the fences, or returns the raw string if no fences
    are found.

    Args:
        raw: Raw LLM output string, possibly wrapped in markdown fences.

    Returns:
        Cleaned string with fences removed and whitespace trimmed.
    """
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        first_newline = cleaned.index("\n")
        cleaned = cleaned[first_newline + 1 :]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    return cleaned.strip()

"""Build personality prompts from the Big Five model and extended traits.

The Big Five personality model (OCEAN) is the most widely validated framework
in personality psychology for describing individual differences.

Source: Costa & McCrae (1992). "Revised NEO Personality Inventory (NEO-PI-R)
and NEO Five-Factor Inventory (NEO-FFI) professional manual."
Psychological Assessment Resources.
"""
from __future__ import annotations

# Big Five trait descriptors mapped to high (>= 0.7) and low (<= 0.3) values.
# Middle values (0.3-0.7) get a neutral description.
_BIG_FIVE: dict[str, dict[str, str]] = {
    "openness": {
        "high": "curious, creative, and open to new experiences",
        "low": "practical, conventional, and prefers routine",
    },
    "conscientiousness": {
        "high": "organized, disciplined, and reliable",
        "low": "spontaneous, flexible, and sometimes careless",
    },
    "extraversion": {
        "high": "outgoing, energetic, and talkative",
        "low": "reserved, introspective, and prefers solitude",
    },
    "agreeableness": {
        "high": "cooperative, trusting, and empathetic",
        "low": "competitive, skeptical, and challenging",
    },
    "neuroticism": {
        "high": "anxious, emotionally reactive, and prone to worry",
        "low": "calm, emotionally stable, and resilient",
    },
}


def _describe_trait(trait_name: str, value: float) -> str:
    """Convert a 0.0-1.0 trait value into a natural language description."""
    descriptors = _BIG_FIVE.get(trait_name, {})
    if value >= 0.7:
        return f"You are {descriptors.get('high', 'notable in ' + trait_name)}."
    if value <= 0.3:
        return f"You are {descriptors.get('low', 'low in ' + trait_name)}."
    return f"You are moderate in {trait_name}."


def build_personality_prompt(personality_data: dict) -> str:
    """Build a system prompt describing the agent's personality.

    Accepts a dict with Big Five trait scores (0.0-1.0) and optional extended
    fields (background, ambitions, weaknesses, values, fears, beliefs).

    Returns a multi-line string suitable as an LLM system prompt.
    """
    parts: list[str] = ["You are a person with the following personality:\n"]

    # Big Five traits (core personality)
    for trait in ("openness", "conscientiousness", "extraversion", "agreeableness", "neuroticism"):
        value = personality_data.get(trait, 0.5)
        parts.append(f"- {_describe_trait(trait, value)}")

    # Extended personality fields (optional, free-text)
    _optional_fields = (
        ("background", "Your background"),
        ("ambitions", "Your ambitions"),
        ("weaknesses", "Your weaknesses"),
        ("values", "Your core values"),
        ("fears", "Your deepest fears"),
        ("beliefs", "Your beliefs"),
    )
    for field, label in _optional_fields:
        text = personality_data.get(field, "")
        if text:
            parts.append(f"\n{label}: {text}")

    parts.append("\nAlways act consistently with your personality. Never break character.")

    return "\n".join(parts)

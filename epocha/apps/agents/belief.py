"""Belief filter -- decides whether an agent accepts incoming information.

Models the cognitive evaluation of information credibility based on three
factors: the inherent reliability of the information, the trust in the
transmitter (derived from relationship), and the receiver's personality
disposition toward believing new information.

Scientific basis:
- Interpersonal trust model: Mayer, Davis & Schoorman (1995). "An Integrative
  Model of Organizational Trust." Academy of Management Review, 20(3), 709-734.
- Agreeableness and credulity: Graziano & Tobin (2002). "Agreeableness:
  Dimension of Personality or Social Desirability Artifact?" Journal of
  Personality, 70(5), 695-728.
"""
from __future__ import annotations

from django.conf import settings


def should_believe(
    reliability: float,
    receiver_personality: dict,
    relationship_strength: float,
    relationship_sentiment: float,
) -> bool:
    """Determine whether an agent accepts a piece of incoming information.

    The acceptance score is a weighted sum of three factors:
    - Information reliability (40%): inherent quality of the information
    - Relationship trust (30%): how much the receiver trusts the transmitter
    - Personality factor (30%): receiver's disposition toward credulity

    Args:
        reliability: Information reliability (0.0-1.0), degrades per hop.
        receiver_personality: Big Five personality dict of the receiving agent.
        relationship_strength: Strength of the relationship (0.0-1.0).
        relationship_sentiment: Sentiment toward the transmitter (-1.0 to 1.0).

    Returns:
        True if the agent accepts the information, False if they discard it.
    """
    # Relationship trust: strength + positive sentiment, averaged.
    # Negative sentiment is clamped to 0 -- distrust does not increase trust.
    relationship_trust = (relationship_strength + max(0.0, relationship_sentiment)) / 2.0

    # Personality factor: agreeableness (credulity) and openness (receptivity).
    agreeableness = receiver_personality.get("agreeableness", 0.5)
    openness = receiver_personality.get("openness", 0.5)
    personality_factor = agreeableness * 0.6 + openness * 0.4

    acceptance_score = (
        reliability * 0.4
        + relationship_trust * 0.3
        + personality_factor * 0.3
    )

    threshold = getattr(settings, "EPOCHA_INFO_FLOW_BELIEF_THRESHOLD", 0.4)
    return acceptance_score >= threshold

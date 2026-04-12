"""Belief filter -- decides whether an agent accepts incoming information.

Models the cognitive evaluation of information credibility based on four
factors: the inherent reliability of the information, the trust in the
transmitter (derived from relationship), the receiver's personality
disposition toward believing new information, and the transmitter's
reputation as perceived by the wider social network.

Scientific references:
- Mayer, Davis & Schoorman (1995). "An Integrative Model of Organizational
  Trust." Academy of Management Review, 20(3), 709-734. Used as a conceptual
  framework for thinking about trust components; the acceptance score computed
  here is loosely inspired by that work but does NOT implement Mayer's
  constructs (ability, benevolence, integrity) or their measurement methods.
- Graziano & Tobin (2002). "Agreeableness: Dimension of Personality or Social
  Desirability Artifact?" Journal of Personality, 70(5), 695-728. Supports the
  role of agreeableness in cooperative information processing.
- Castelfranchi, C., Falcone, R., & Tan, Y. H. (1998). "The Role of Trust and
  Deception in Virtual Societies." Proceedings of the 31st Hawaii International
  Conference on System Sciences. Supports using network-level reputation as a
  credibility signal.
"""
from __future__ import annotations

from django.conf import settings


def should_believe(
    reliability: float,
    receiver_personality: dict,
    relationship_strength: float,
    relationship_sentiment: float,
    transmitter_reputation: float = 0.0,
) -> bool:
    """Determine whether an agent accepts a piece of incoming information.

    The acceptance score is a weighted sum of four components. While inspired
    by trust models in the literature (Mayer et al. 1995 for the conceptual
    framework), it does not implement any specific trust model's constructs.
    The weights are tunable design parameters:

    - Information reliability (30%): inherent quality of the information
    - Relationship trust (20%): how much the receiver trusts the transmitter
    - Personality factor (20%): receiver's disposition toward credulity
    - Transmitter reputation (30%): the transmitter's standing in the social network

    Weight distribution (reliability 0.3, relationship 0.2, personality 0.2,
    reputation 0.3) is a design choice balancing information quality with
    social factors. No empirical derivation.

    The default transmitter_reputation of 0.0 maps to a neutral reputation
    factor of 0.5, preserving backward compatibility for callers that do not
    yet supply this argument.

    Args:
        reliability: Information reliability (0.0-1.0), degrades per hop.
        receiver_personality: Big Five personality dict of the receiving agent.
        relationship_strength: Strength of the relationship (0.0-1.0).
        relationship_sentiment: Sentiment toward the transmitter (-1.0 to 1.0).
        transmitter_reputation: Reputation of the transmitter (-1.0 to 1.0).
            Negative values reduce credibility; positive values increase it.
            Defaults to 0.0 (neutral).

    Returns:
        True if the agent accepts the information, False if they discard it.
    """
    # Relationship trust: strength + positive sentiment, averaged.
    # Negative sentiment is clamped to 0 -- distrust does not increase trust.
    relationship_trust = (relationship_strength + max(0.0, relationship_sentiment)) / 2.0

    # Personality factor: agreeableness (credulity) and openness (receptivity).
    # Agreeableness contribution (weight 0.6) is supported by Graziano & Tobin
    # (2002), who link agreeableness to cooperative information processing.
    # Openness contribution (weight 0.4) is a design choice -- open individuals
    # may be more receptive to novel information -- without specific empirical
    # support from that paper.
    agreeableness = receiver_personality.get("agreeableness", 0.5)
    openness = receiver_personality.get("openness", 0.5)
    personality_factor = agreeableness * 0.6 + openness * 0.4

    # Normalize reputation from [-1, 1] to [0, 1].
    # 0.0 (neutral) maps to 0.5, -1.0 (worst) to 0.0, +1.0 (best) to 1.0.
    reputation_factor = (transmitter_reputation + 1.0) / 2.0

    acceptance_score = (
        reliability * 0.3
        + relationship_trust * 0.2
        + personality_factor * 0.2
        + reputation_factor * 0.3
    )

    # Threshold 0.4 is a design parameter. With all neutral inputs (0.5), the
    # acceptance score is 0.5, which exceeds 0.4 -- meaning neutral agents
    # accept information by default. This is an intentional design choice
    # favoring information propagation over skepticism.
    threshold = getattr(settings, "EPOCHA_INFO_FLOW_BELIEF_THRESHOLD", 0.4)
    return acceptance_score >= threshold

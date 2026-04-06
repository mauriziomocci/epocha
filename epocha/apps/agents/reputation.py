"""Reputation operations for the Castelfranchi-Conte-Paolucci model.

This module implements the image/reputation distinction introduced in:

  Castelfranchi, C., Conte, R. & Paolucci, M. (1998). "Normative reputation
  and the costs of compliance." Journal of Artificial Societies and Social
  Simulation, vol. 1, no. 3.

  - Image: a holder's first-hand assessment of a target, updated by direct
    interaction (observation of the target's actions).
  - Reputation: a holder's socially propagated assessment, updated by hearsay
    weighted by the reliability of the information source.

The negativity-bias asymmetry in the delta magnitudes (e.g. betray >> help)
is grounded in:

  Baumeister, R.F., Bratslavsky, E., Finkenauer, C. & Vohs, K.D. (2001).
  "Bad is stronger than good." Review of General Psychology, 5(4), 323-370.
  doi:10.1037/1089-2680.5.4.323
"""

from __future__ import annotations

from epocha.apps.agents.models import Agent, ReputationScore

# ---------------------------------------------------------------------------
# Image delta table
# ---------------------------------------------------------------------------
# Magnitudes reflect real social-psychology findings on the asymmetric impact
# of harmful vs. helpful acts (Baumeister et al., 2001).  The unit represents
# a single observation increment on the [-1, 1] image scale.
#
# Positive deltas — prosocial actions
# Negative deltas — antisocial actions (magnitudes deliberately larger)
_IMAGE_DELTAS: dict[str, float] = {
    "help": 0.15,
    "socialize": 0.10,
    "trade": 0.05,
    "work": 0.03,
    "argue": -0.20,
    "betray": -0.80,
    "avoid": -0.05,
    "crime": -0.60,
}

# ---------------------------------------------------------------------------
# Sentiment keyword tables for extract_action_sentiment
# ---------------------------------------------------------------------------
# Used to derive a sentiment signal from free-text decision content when no
# structured action_type is available (e.g. LLM narrative output).

_POSITIVE_KEYWORDS: dict[str, float] = {
    "helped": 1.0,
    "help": 1.0,
    "saved": 1.0,
    "protected": 1.0,
    "socialized": 0.5,
    "traded": 0.5,
    "founded": 0.3,
    "built": 0.3,
    "united": 0.3,
}

_NEGATIVE_KEYWORDS: dict[str, float] = {
    "betrayed": -1.0,
    "betray": -1.0,
    "attacked": -1.0,
    "stole": -1.0,
    "crime": -0.8,
    "argued": -0.5,
    "argue": -0.5,
    "fought": -0.7,
    "exploited": -0.8,
    "oppressed": -0.8,
    "destroyed": -1.0,
}

_ALL_SENTIMENT_KEYWORDS: dict[str, float] = {**_POSITIVE_KEYWORDS, **_NEGATIVE_KEYWORDS}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def update_image(holder: Agent, target: Agent, action_type: str, tick: int) -> ReputationScore:
    """Update the direct-experience image the holder has of the target.

    The holder has personally observed the target performing action_type.
    The image field is incremented by the delta mapped in _IMAGE_DELTAS and
    then clamped to [-1.0, 1.0].

    If the action_type is unknown the image is left unchanged and the record
    is still created/retrieved so callers receive a valid object.

    Args:
        holder: The agent whose perception is updated.
        target: The agent who performed the action.
        action_type: A key from _IMAGE_DELTAS (e.g. "help", "betray").
        tick: The simulation tick at which the observation occurred.

    Returns:
        The updated (or newly created) ReputationScore instance.
    """
    score, _ = ReputationScore.objects.get_or_create(holder=holder, target=target)
    delta = _IMAGE_DELTAS.get(action_type, 0.0)
    score.image = _clamp(score.image + delta)
    score.last_updated_tick = tick
    score.save(update_fields=["image", "last_updated_tick"])
    return score


def update_reputation(
    holder: Agent,
    target: Agent,
    action_sentiment: float,
    reliability: float,
    tick: int,
) -> ReputationScore:
    """Update the socially propagated reputation the holder has of the target.

    Called when the holder receives hearsay about the target's actions.  The
    update is weighted by the reliability of the information source so that
    gossip from a trusted agent has more impact than from an unknown one.

    delta = action_sentiment * reliability * 0.5

    The 0.5 dampening factor ensures that a single hearsay event of maximum
    sentiment (±1.0) from a perfectly reliable source (1.0) cannot move the
    reputation more than 0.5 — preserving the primacy of direct experience
    (image) while still allowing social information to accumulate over time.

    This function never modifies image; image is updated exclusively by
    direct observation via update_image.

    Args:
        holder: The agent whose perception is updated.
        target: The subject of the hearsay.
        action_sentiment: Signed sentiment of the reported action in [-1, 1].
        reliability: Reliability of the information source in [0, 1].
        tick: The simulation tick at which the hearsay was received.

    Returns:
        The updated (or newly created) ReputationScore instance.
    """
    score, _ = ReputationScore.objects.get_or_create(holder=holder, target=target)
    delta = action_sentiment * reliability * 0.5
    score.reputation = _clamp(score.reputation + delta)
    score.last_updated_tick = tick
    score.save(update_fields=["reputation", "last_updated_tick"])
    return score


def get_combined_score(holder: Agent, target: Agent) -> float:
    """Return a single trustworthiness score combining image and reputation.

    Weights:
      - image (direct experience): 0.6
      - reputation (social evaluation): 0.4

    The heavier weight on image reflects the empirical finding that first-hand
    experience is generally more reliable and resistant to manipulation than
    socially propagated information (Castelfranchi et al., 1998).

    Returns 0.0 (neutral) if no ReputationScore record exists for this pair.

    Args:
        holder: The agent whose perception is queried.
        target: The agent being evaluated.

    Returns:
        Combined score in [-1.0, 1.0], or 0.0 if no record exists.
    """
    try:
        score = ReputationScore.objects.get(holder=holder, target=target)
    except ReputationScore.DoesNotExist:
        return 0.0
    return score.image * 0.6 + score.reputation * 0.4


def extract_action_sentiment(content: str) -> float:
    """Derive a sentiment signal from free-text action content.

    Scans the lowercased content for known positive and negative keywords and
    returns the value of the strongest match found.  If multiple keywords
    match, the one with the highest absolute value takes precedence.  Returns
    0.0 when no keyword is found.

    This is intentionally a lightweight heuristic — it is used to translate
    LLM narrative output (which lacks structured action_type tags) into a
    numeric signal suitable for update_reputation.

    Args:
        content: Free-text description of an action or decision.

    Returns:
        Sentiment in [-1.0, 1.0], or 0.0 if content is neutral/unrecognised.
    """
    lowered = content.lower()
    best: float = 0.0
    for keyword, value in _ALL_SENTIMENT_KEYWORDS.items():
        if keyword in lowered and abs(value) > abs(best):
            best = value
    return best


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _clamp(value: float, lo: float = -1.0, hi: float = 1.0) -> float:
    """Clamp value to [lo, hi]."""
    return max(lo, min(hi, value))

"""Reputation operations for the Castelfranchi-Conte-Paolucci model.

This module implements the image/reputation distinction introduced in:

  Castelfranchi, C., Conte, R. & Paolucci, M. (1998). "Normative reputation
  and the costs of compliance." Journal of Artificial Societies and Social
  Simulation, vol. 1, no. 3.

  - Image: a holder's first-hand assessment of a target, updated by direct
    interaction (observation of the target's actions).
  - Reputation: a holder's socially propagated assessment, updated by hearsay
    weighted by the reliability of the information source.

The numerical scale [-1, 1] is an implementation decision typical of
computational reputation systems (e.g. ReGreT -- Sabater & Sierra 2002)
and not prescribed by Castelfranchi et al. (1998) which describes image
and reputation as cognitive constructs without committing to a specific
numerical encoding.

Image and reputation are updated by additive deltas immediately clamped
to [-1, 1]. This is a known simplification: in saturation regime (e.g.
20 consecutive `help` observations), the image saturates after roughly
1/delta observations and subsequent observations have zero effect.
Alternative aggregation schemes -- running average, beta-distribution
posterior (Beta Reputation System, Josang & Ismail 2002), Bayesian update --
would avoid the saturation effect at the cost of additional state per
observation. This trade-off is accepted for the current implementation.

The negativity-bias asymmetry in the delta magnitudes (e.g. betray >> help)
is inspired by:

  Baumeister, R.F., Bratslavsky, E., Finkenauer, C. & Vohs, K.D. (2001).
  "Bad is stronger than good." Review of General Psychology, 5(4), 323-370.
  doi:10.1037/1089-2680.5.4.323

Known limitation: no temporal decay of image or reputation values.
Observations from early ticks carry the same weight as recent ones. Future
versions should implement recency weighting (Castelfranchi et al. 1998
discuss reputation maintenance through ongoing social communication).
"""

from __future__ import annotations

import logging
import re

from django.db import transaction

from epocha.apps.agents.models import Agent, ReputationScore

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Combined-score weights -- single source of truth
# ---------------------------------------------------------------------------
# Tunable design parameters; image weighted more heavily than reputation
# to reflect the qualitative primacy of direct experience over hearsay
# (Castelfranchi et al. 1998 conceptual distinction; specific 0.6/0.4
# ratio is a design choice without empirical derivation).
_WEIGHT_IMAGE: float = 0.6
_WEIGHT_REPUTATION: float = 0.4


def _normalize_reputation(raw: float) -> float:
    """Normalize a combined reputation score from [-1, 1] to [0, 1].

    Single source of truth for the [-1, 1] -> [0, 1] mapping used by
    downstream modules that need a non-negative scale (belief filter,
    election scoring, dashboards). Neutral 0.0 maps to 0.5.

    Tunable design: the linear mapping `(raw + 1) / 2` is the simplest
    invariant-preserving transform. Alternative would be a sigmoid for
    stronger emphasis near the extremes.

    Args:
        raw: Combined reputation score in [-1.0, 1.0].

    Returns:
        Normalized score in [0.0, 1.0].
    """
    return (raw + 1.0) / 2.0


# ---------------------------------------------------------------------------
# Domain-specific sentiment magnitudes for non-keyword-extracted events
# ---------------------------------------------------------------------------
# Used by domain modules (e.g. credit.py) that bypass the keyword pipeline
# and call update_reputation directly with a known sentiment magnitude.
#
# Loan default magnitudes inspired by the economic-sociology literature on
# reputational sanctions for credit default (Diamond 1989; Greif 1993 on
# Maghribi traders; Karlan 2005 on social-collateral microfinance) which
# qualitatively support strong negative sentiment toward defaulters from
# both observers and the lender, with the lender's sentiment more negative
# than third-party observers'. Specific magnitudes are tunable.
_LOAN_DEFAULT_OBSERVER_SENTIMENT: float = -0.7
_LOAN_DEFAULT_LENDER_SENTIMENT: float = -0.9

# ---------------------------------------------------------------------------
# Image delta table
# ---------------------------------------------------------------------------
# Tunable design parameters with no literature anchor for the specific
# magnitudes. The asymmetry between negative and positive deltas is
# inspired by the negativity-bias principle (Baumeister et al. 2001 --
# "bad is stronger than good") which establishes the qualitative
# direction but does NOT prescribe specific quantitative ratios. The
# values below are free design parameters intended to make antisocial
# observations more salient than prosocial ones; they should be
# calibrated against simulated outcomes (e.g. couple/faction stability
# under varying ratios) in a future calibration pass.
# The unit represents a single observation increment on the [-1, 1] image scale.
#
# Positive deltas -- prosocial actions
# Negative deltas -- antisocial actions (magnitudes deliberately larger)
_IMAGE_DELTAS: dict[str, float] = {
    # Core prosocial / antisocial pairs
    "help": 0.15,
    "socialize": 0.10,
    "trade": 0.05,
    "work": 0.03,
    "argue": -0.20,
    "betray": -0.80,
    "avoid": -0.05,
    "crime": -0.60,
    # Group / political vocabulary emitted by engine.py
    # form_group: mild prosocial -- group creation signals cooperative intent.
    # join_group: very mild prosocial -- joining an existing collective effort.
    "form_group": 0.05,
    "join_group": 0.03,
    # protest: mild antisocial as observed by power-holders; the coarse
    # aggregation here cannot distinguish observer political alignment.
    "protest": -0.05,
    # campaign: politically neutral observation at the dyadic level.
    "campaign": 0.0,
    # Economic vocabulary
    # hoard: mild antisocial -- withholding from community.
    "hoard": -0.10,
    # borrow / sell_property / buy_property: transactional, sentiment is
    # determined later by repayment outcome (see credit.py loan-default path).
    "borrow": 0.0,
    "sell_property": 0.0,
    "buy_property": 0.0,
    # Logistical / personal vocabulary -- deliberately neutral
    "move_to": 0.0,
    "explore": 0.0,
    "rest": 0.0,
    # Demography vocabulary (Plan 2)
    # pair_bond: mild prosocial signal -- public commitment to a partner
    # (whitepaper chapter 4.1.3 demography rationale).
    # separate: mild antisocial signal -- breaks an existing public bond.
    # avoid_conception: private decision, neutral observation.
    "pair_bond": 0.05,
    "separate": -0.05,
    "avoid_conception": 0.0,
}

# ---------------------------------------------------------------------------
# Sentiment keyword tables for extract_action_sentiment
# ---------------------------------------------------------------------------
# Used to derive a sentiment signal from free-text decision content when no
# structured action_type is available (e.g. LLM narrative output).
#
# These tables are placeholder rule-based heuristics with values assigned by
# inspection of typical narrative phrasing in early simulations. They are NOT
# anchored to a published sentiment lexicon (VADER, AFINN, NRC) and they are
# scheduled for replacement by an embedding-based or LLM-based sentiment
# classifier in a future iteration. Treat the magnitudes as ordinal indicators
# of strength rather than calibrated weights.
#
# The action_type literals (e.g. "socialize", "form_group", "hoard") are
# present alongside the natural-language forms so that the hearsay path in
# information_flow._propagate_memory recognises the structured tokens emitted
# by simulation/engine.py when it builds memory content via
# f"I decided to {action_type}. {reason}". The set is aligned with the
# non-zero entries of _IMAGE_DELTAS to guarantee that the direct-observation
# (image) and hearsay (reputation) tracks of the Castelfranchi-Conte-Paolucci
# model agree on which actions are prosocial vs antisocial. See Round 2
# audit finding N-1 closure.

_POSITIVE_KEYWORDS: dict[str, float] = {
    "helped": 1.0,
    "help": 1.0,
    "saved": 1.0,
    "protected": 1.0,
    "socialized": 0.5,
    "socialize": 0.5,
    "traded": 0.5,
    "trade": 0.5,
    "work": 0.5,
    "founded": 0.3,
    "built": 0.3,
    "united": 0.3,
    # Aligned with _IMAGE_DELTAS prosocial action types (N-1 closure)
    "form_group": 0.5,
    "join_group": 0.5,
    "pair_bond": 0.5,
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
    "avoid": -0.5,
    # Aligned with _IMAGE_DELTAS antisocial action types (N-1 closure)
    "protest": -0.5,
    "hoard": -0.5,
    "separate": -0.5,
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
    is still created/retrieved so callers receive a valid object. A WARNING
    log is emitted to surface drift between the engine action vocabulary and
    this table.

    Concurrency: the read-modify-write on ReputationScore is wrapped in a
    transaction.atomic() block with select_for_update() to avoid lost-update
    races when two ticks attempt to update the same (holder, target) pair
    concurrently (e.g. parallel Celery workers).

    Args:
        holder: The agent whose perception is updated.
        target: The agent who performed the action.
        action_type: A key from _IMAGE_DELTAS (e.g. "help", "betray").
        tick: The simulation tick at which the observation occurred.

    Returns:
        The updated (or newly created) ReputationScore instance.
    """
    with transaction.atomic():
        score, _ = ReputationScore.objects.select_for_update().get_or_create(
            holder=holder,
            target=target,
        )
        delta = _IMAGE_DELTAS.get(action_type, 0.0)
        if delta == 0.0 and action_type not in _IMAGE_DELTAS:
            logger.warning(
                "update_image called with unknown action_type=%s; image unchanged. "
                "Either add to _IMAGE_DELTAS or document as deliberately neutral.",
                action_type,
            )
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

    Dampening factor 0.5 prevents a single hearsay event of maximum sentiment
    (+/-1.0) from a perfectly reliable source (1.0) from moving reputation more
    than 0.5. Tunable parameter, no empirical source.

    This function never modifies image; image is updated exclusively by
    direct observation via update_image.

    Concurrency: the read-modify-write on ReputationScore is wrapped in a
    transaction.atomic() block with select_for_update() to avoid lost-update
    races when two ticks attempt to update the same (holder, target) pair
    concurrently (e.g. parallel Celery workers).

    Args:
        holder: The agent whose perception is updated.
        target: The subject of the hearsay.
        action_sentiment: Signed sentiment of the reported action in [-1, 1].
        reliability: Reliability of the information source in [0, 1].
        tick: The simulation tick at which the hearsay was received.

    Returns:
        The updated (or newly created) ReputationScore instance.
    """
    with transaction.atomic():
        score, _ = ReputationScore.objects.select_for_update().get_or_create(
            holder=holder,
            target=target,
        )
        delta = action_sentiment * reliability * 0.5
        score.reputation = _clamp(score.reputation + delta)
        score.last_updated_tick = tick
        score.save(update_fields=["reputation", "last_updated_tick"])
        return score


def get_combined_score(holder: Agent, target: Agent) -> float:
    """Return a single trustworthiness score combining image and reputation.

    Weights:
      - image (direct experience): _WEIGHT_IMAGE (0.6)
      - reputation (social evaluation): _WEIGHT_REPUTATION (0.4)

    Design choice: image weighted 60% over reputation 40%. The primacy of
    direct experience over hearsay is a well-established principle in social
    psychology (Castelfranchi et al. 1998 for the conceptual distinction), but
    the specific 60/40 ratio is a tunable parameter without empirical
    derivation.

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
    return score.image * _WEIGHT_IMAGE + score.reputation * _WEIGHT_REPUTATION


def extract_action_sentiment(content: str) -> float:
    """Derive a sentiment signal from free-text action content.

    Scans the lowercased content for known positive and negative keywords and
    returns the value of the strongest match found. If multiple keywords
    match, the one with the highest absolute value takes precedence. Returns
    0.0 when no keyword is found.

    This is intentionally a lightweight heuristic -- it is used to translate
    LLM narrative output (which lacks structured action_type tags) into a
    numeric signal suitable for update_reputation.

    Limitations:
    - Loudest-keyword-wins: a sentence describing both prosocial and
      antisocial behavior with comparable intensity returns only the
      single highest-magnitude keyword. Example: "I helped but later
      attacked them" returns -1.0 (the antisocial pole), ignoring the
      prosocial qualifier. This systematically biases hearsay-derived
      reputation toward whichever pole is most lexically intense in the
      keyword tables.
    - No negation handling: "I did not help" still scores +1.0 for "help".
    - No sentence-level aggregation: a long narrative is reduced to one
      keyword.

    These limitations are accepted for the current placeholder
    implementation and are documented under Future Work in the whitepaper
    chapter 4 reputation Simplifications subsection.

    Args:
        content: Free-text description of an action or decision.

    Returns:
        Sentiment in [-1.0, 1.0], or 0.0 if content is neutral/unrecognised.
    """
    lowered = content.lower()
    best: float = 0.0
    # Word-boundary match prevents substring collisions (e.g. `avoid` keyword
    # would otherwise spuriously match `avoid_conception` content because
    # Python's \b treats `_` as a word character, so `\bavoid\b` correctly
    # does NOT match inside `avoid_conception`). Closes Round 2 finding N-1
    # follow-up regression discovered during US1 implementation.
    for keyword, value in _ALL_SENTIMENT_KEYWORDS.items():
        if re.search(rf"\b{re.escape(keyword)}\b", lowered) and abs(value) > abs(best):
            best = value
    return best


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _clamp(value: float, lo: float = -1.0, hi: float = 1.0) -> float:
    """Clamp value to [lo, hi]."""
    return max(lo, min(hi, value))

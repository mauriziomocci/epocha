"""
Rule-based distortion engine for information propagation.

Models how agents unconsciously reshape information when retelling it,
following Allport & Postman (1947) "The Psychology of Rumor" which
identified three key mechanisms:
  - Leveling: detail is lost, content simplifies over retellings
  - Sharpening: selective emphasis on certain details
  - Assimilation: content is altered to fit the transmitter's attitudes and expectations

This module implements Assimilation as personality-driven substitution rules derived
from the Big Five (OCEAN) model. Each trait with an extreme value (above _HIGH_THRESHOLD
or below _LOW_THRESHOLD) applies a set of regex substitutions whose strength scales
with the degree of extremity.

References:
  - Allport, G. W., & Postman, L. (1947). The Psychology of Rumor. Henry Holt and Co.
  - Costa, P. T., & McCrae, R. R. (1992). NEO PI-R professional manual. PAR.
"""

import re
from typing import Optional

# Big Five thresholds defining when a trait is "extreme enough" to produce distortion.
# Allport & Postman (1947) found that assimilation effects are non-linear: they
# emerge only when the reteller's attitude is sufficiently strong.
_HIGH_THRESHOLD: float = 0.7
_LOW_THRESHOLD: float = 0.3

# Maximum number of traits that actively distort a single message. Cognitive load
# research (Miller, 1956) suggests that simultaneous application of many biases
# would produce unrealistic distortion; cap at 2 dominant traits per transmission.
_MAX_ACTIVE_TRAITS: int = 2

# Each entry in a pattern list is (compiled_regex, [low_replacement, mid_replacement, high_replacement]).
# Replacement index maps to _get_strength_index() output: 0=mild, 1=moderate, 2=strong.
# The lists encode graduated intensity so distortion scales continuously with trait extremity.

_HIGH_NEUROTICISM_PATTERNS: list[tuple[re.Pattern, list[str]]] = [
    # Allport & Postman: sharpening of negative affect in high-anxiety retellers
    (re.compile(r"\bargued\b", re.IGNORECASE), ["quarreled", "fought bitterly", "attacked viciously"]),
    (re.compile(r"\bdisagreed\b", re.IGNORECASE), ["clashed", "argued fiercely", "erupted into conflict"]),
    (re.compile(r"\bcritici[sz]ed\b", re.IGNORECASE), ["attacked", "viciously mocked", "verbally assaulted"]),
    (re.compile(r"\bdisappointed\b", re.IGNORECASE), ["let down", "betrayed", "devastated"]),
    (re.compile(r"\bwent wrong\b", re.IGNORECASE), ["failed badly", "collapsed", "turned into a disaster"]),
]

_LOW_NEUROTICISM_PATTERNS: list[tuple[re.Pattern, list[str]]] = [
    # Leveling: emotionally stable retellers downplay conflict
    (re.compile(r"\bfought bitterly\b", re.IGNORECASE), ["argued", "had a disagreement", "had a brief exchange"]),
    (re.compile(r"\battacked\b", re.IGNORECASE), ["criticized", "challenged", "disagreed with"]),
    (re.compile(r"\berupted\b", re.IGNORECASE), ["started", "began", "developed"]),
    (re.compile(r"\bbetrayed\b", re.IGNORECASE), ["disappointed", "let down", "differed from"]),
    (re.compile(r"\bdisaster\b", re.IGNORECASE), ["setback", "difficulty", "issue"]),
]

_HIGH_AGREEABLENESS_PATTERNS: list[tuple[re.Pattern, list[str]]] = [
    # High agreeableness: reteller softens interpersonal conflict to preserve harmony
    (re.compile(r"\bbetrayed\b", re.IGNORECASE), ["disappointed", "let down", "failed to support"]),
    (re.compile(r"\battacked\b", re.IGNORECASE), ["disagreed with", "pushed back on", "challenged"]),
    (re.compile(r"\bfought\b", re.IGNORECASE), ["disagreed", "had a discussion", "talked through"]),
    (re.compile(r"\bargued\b", re.IGNORECASE), ["discussed", "raised a concern with", "spoke with"]),
    (re.compile(r"\bconflict\b", re.IGNORECASE), ["disagreement", "misunderstanding", "difference"]),
]

_LOW_AGREEABLENESS_PATTERNS: list[tuple[re.Pattern, list[str]]] = [
    # Low agreeableness: reteller frames events as more adversarial than they were
    (re.compile(r"\bargued\b", re.IGNORECASE), ["attacked", "went after", "turned against"]),
    (re.compile(r"\bdisagreed\b", re.IGNORECASE), ["fought with", "confronted", "turned on"]),
    (re.compile(r"\bdiscussed\b", re.IGNORECASE), ["argued about", "clashed over", "fought over"]),
    (re.compile(r"\bdisappointed\b", re.IGNORECASE), ["let down", "betrayed", "stabbed in the back"]),
    (re.compile(r"\bhelped\b", re.IGNORECASE), ["claimed to help", "manipulated", "used"]),
]

_HIGH_OPENNESS_PATTERNS: list[tuple[re.Pattern, list[str]]] = [
    # High openness: reteller adds speculation and interpretive context
    # Applied as a sentence-level suffix after a period-space boundary
    (re.compile(r"\.\s"), [" -- possibly for a reason. ", " -- perhaps because of something deeper. ", " -- perhaps for a reason. "]),
]

_LOW_OPENNESS_PATTERNS: list[tuple[re.Pattern, list[str]]] = [
    # Low openness: reteller strips hedging and uncertainty markers
    (re.compile(r"\bperhaps\b", re.IGNORECASE), ["", "clearly", "obviously"]),
    (re.compile(r"\bapparently\b", re.IGNORECASE), ["", "clearly", "obviously"]),
    (re.compile(r"\bseemingly\b", re.IGNORECASE), ["", "clearly", "obviously"]),
    (re.compile(r"\bpossibly\b", re.IGNORECASE), ["", "clearly", "obviously"]),
]

_HIGH_EXTRAVERSION_PATTERNS: list[tuple[re.Pattern, list[str]]] = [
    # High extraversion: reteller exaggerates social scope (Allport & Postman: sharpening of social salience)
    (re.compile(r"\bsomeone\b", re.IGNORECASE), ["several people", "many people", "everyone"]),
    (re.compile(r"\ba person\b", re.IGNORECASE), ["some people", "many people", "a crowd"]),
    (re.compile(r"\bone person\b", re.IGNORECASE), ["some people", "a group", "many people"]),
    (re.compile(r"\boccasionally\b", re.IGNORECASE), ["often", "frequently", "constantly"]),
]

_LOW_EXTRAVERSION_PATTERNS: list[tuple[re.Pattern, list[str]]] = [
    # Low extraversion: reteller minimizes social scope
    (re.compile(r"\beveryone\b", re.IGNORECASE), ["many people", "some people", "someone"]),
    (re.compile(r"\bthe whole group\b", re.IGNORECASE), ["several people", "some people", "someone"]),
    (re.compile(r"\ball\b", re.IGNORECASE), ["many", "some", "a few"]),
]

_HIGH_CONSCIENTIOUSNESS_PATTERNS: list[tuple[re.Pattern, list[str]]] = [
    # High conscientiousness: reteller adds precision and causal attribution
    (re.compile(r"\.\s*$"), [" -- exactly as it happened.", " -- precisely as documented.", " -- according to the established facts."]),
]

_LOW_CONSCIENTIOUSNESS_PATTERNS: list[tuple[re.Pattern, list[str]]] = [
    # Low conscientiousness: reteller vague-ifies specific names (Allport & Postman: leveling of detail).
    # The lookbehind (?<= ) ensures only mid-sentence capitalized words are matched, not sentence starters.
    (re.compile(r"(?<= )\b[A-Z][a-z]+\b"), ["somebody", "someone", "this person"]),
]


def _get_strength_index(value: float, threshold: float) -> int:
    """
    Map trait extremity to a replacement strength index in {0, 1, 2}.

    The distance from the neutral zone (0.3-0.7) is divided into three equal bands:
      - Band 0 (mild):     just past threshold, up to 1/3 of the remaining range
      - Band 1 (moderate): between 1/3 and 2/3 of the remaining range
      - Band 2 (strong):   outer third of the range (most extreme values)

    This linear bucketing is a simplification; real cognitive biases are likely
    non-linear, but no well-calibrated empirical function is available at this stage.

    Args:
        value:     the raw trait value (0.0 to 1.0)
        threshold: _HIGH_THRESHOLD or _LOW_THRESHOLD depending on direction

    Returns:
        Integer index 0, 1, or 2 for use as replacement list index.
    """
    if threshold >= 0.5:
        # High direction: distance from high threshold toward 1.0
        max_range = 1.0 - threshold
        distance = value - threshold
    else:
        # Low direction: distance from low threshold toward 0.0
        max_range = threshold
        distance = threshold - value

    if max_range == 0:
        return 2

    ratio = distance / max_range
    if ratio < 1 / 3:
        return 0
    elif ratio < 2 / 3:
        return 1
    else:
        return 2


def _select_active_traits(personality: dict[str, float]) -> list[tuple[str, float, bool]]:
    """
    Select up to _MAX_ACTIVE_TRAITS traits for distortion, ranked by extremity.

    Extremity is measured as distance from 0.5 (the perfectly neutral midpoint).
    Only traits that cross _HIGH_THRESHOLD or _LOW_THRESHOLD are eligible.

    Args:
        personality: mapping of Big Five trait names to float values in [0.0, 1.0].
                     Missing traits default to 0.5 (neutral -- no distortion).

    Returns:
        List of (trait_name, value, is_high) tuples for the most extreme eligible traits,
        sorted by descending extremity. Length is at most _MAX_ACTIVE_TRAITS.
    """
    candidates: list[tuple[float, str, float, bool]] = []

    for trait, value in personality.items():
        if not isinstance(value, (int, float)):
            continue
        extremity = abs(value - 0.5)
        is_high = value > 0.5

        if value >= _HIGH_THRESHOLD or value <= _LOW_THRESHOLD:
            candidates.append((extremity, trait, value, is_high))

    candidates.sort(key=lambda x: x[0], reverse=True)
    return [(trait, value, is_high) for _, trait, value, is_high in candidates[:_MAX_ACTIVE_TRAITS]]


def _apply_patterns(
    content: str,
    patterns: list[tuple[re.Pattern, list[str]]],
    strength_index: int,
) -> str:
    """
    Apply a list of regex patterns to content, using the replacement at strength_index.

    Each pattern is tried in order; only the first matching pattern is applied
    (count=1 to avoid cascading substitutions within the same trait). This mirrors
    the observation that a single dominant bias typically alters the most salient
    element in a message, not every word simultaneously.

    Args:
        content:        the text to distort
        patterns:       list of (compiled_regex, [low, mid, high] replacements)
        strength_index: 0, 1, or 2 -- selects which replacement to use

    Returns:
        Distorted content string.
    """
    for pattern, replacements in patterns:
        if pattern.search(content):
            replacement = replacements[strength_index]
            content = pattern.sub(replacement, content, count=1)
            break
    return content


# Map from trait name to (high_patterns, low_patterns)
_TRAIT_PATTERNS: dict[str, tuple[list, list]] = {
    "neuroticism": (_HIGH_NEUROTICISM_PATTERNS, _LOW_NEUROTICISM_PATTERNS),
    "agreeableness": (_HIGH_AGREEABLENESS_PATTERNS, _LOW_AGREEABLENESS_PATTERNS),
    "openness": (_HIGH_OPENNESS_PATTERNS, _LOW_OPENNESS_PATTERNS),
    "extraversion": (_HIGH_EXTRAVERSION_PATTERNS, _LOW_EXTRAVERSION_PATTERNS),
    "conscientiousness": (_HIGH_CONSCIENTIOUSNESS_PATTERNS, _LOW_CONSCIENTIOUSNESS_PATTERNS),
}


def distort_information(content: str, personality: dict[str, float]) -> str:
    """
    Apply personality-driven distortion to an information string.

    This is a pure function: no I/O, no database access, no LLM calls.
    Called once per (information, recipient) pair during tick propagation.

    The distortion model follows Allport & Postman (1947): the reteller's dominant
    personality traits act as assimilation filters that bend content toward their
    attitudinal expectations. The two most extreme active traits are applied
    sequentially; the first trait's substitution may prevent the second from
    matching the same token (correct behavior -- one dominant reframe per message).

    Args:
        content:     the original information string to distort
        personality: Big Five trait values as floats in [0.0, 1.0]. Any trait
                     between _LOW_THRESHOLD and _HIGH_THRESHOLD produces no effect.
                     Missing traits are treated as 0.5 (neutral).

    Returns:
        The distorted content string. Returns content unchanged if no trait
        is extreme enough to trigger distortion.
    """
    active_traits = _select_active_traits(personality)

    for trait_name, value, is_high in active_traits:
        if trait_name not in _TRAIT_PATTERNS:
            continue

        high_patterns, low_patterns = _TRAIT_PATTERNS[trait_name]
        patterns = high_patterns if is_high else low_patterns
        threshold = _HIGH_THRESHOLD if is_high else _LOW_THRESHOLD
        strength_index = _get_strength_index(value, threshold)

        content = _apply_patterns(content, patterns, strength_index)

    return content

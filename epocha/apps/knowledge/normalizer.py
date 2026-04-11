"""Canonical name normalization and passage containment checks.

Normalization is used for deduplication (two mentions with minor
orthographic differences collapse to the same canonical form) and for
the mechanical source_type assignment (is the name contained in the
passage?).
"""
from __future__ import annotations

import re
import unicodedata

# Honorific prefixes stripped during normalization. Order matters: longer
# forms must come before shorter ones to avoid partial matches.
_HONORIFICS: tuple[str, ...] = (
    "citoyenne",
    "citoyen",
    "madame",
    "monsieur",
    "mme.",
    "mme",
    "mlle.",
    "mlle",
    "mrs.",
    "mrs",
    "mr.",
    "mr",
    "ms.",
    "ms",
    "dr.",
    "dr",
    "prof.",
    "prof",
    "m.",
)

_WHITESPACE_RE = re.compile(r"\s+")


def _strip_accents(text: str) -> str:
    """Return text with combining marks removed via Unicode NFD decomposition."""
    decomposed = unicodedata.normalize("NFD", text)
    return "".join(c for c in decomposed if not unicodedata.combining(c))


def _strip_honorifics(text: str) -> str:
    """Remove leading honorific tokens (iteratively)."""
    result = text
    changed = True
    while changed:
        changed = False
        for honorific in _HONORIFICS:
            if result.startswith(honorific + " "):
                result = result[len(honorific) + 1:]
                changed = True
                break
            if result == honorific:
                return ""
    return result


def normalize_canonical_name(name: str) -> str:
    """Normalize an entity name into its canonical form.

    Steps: lowercase, strip accents, strip honorific prefixes, collapse
    whitespace, trim. Empty or whitespace-only input returns an empty string.
    """
    if not name:
        return ""
    text = _strip_accents(name).lower().strip()
    text = _WHITESPACE_RE.sub(" ", text)
    text = _strip_honorifics(text)
    text = _WHITESPACE_RE.sub(" ", text).strip()
    return text


def name_contained_in_passage(name: str, passage: str) -> bool:
    """Return True if name appears in passage (accent/case insensitive).

    Substring match: "Paris" is considered contained in "Parisian". This
    is intentional because LLM excerpts often use inflected forms; the
    trade-off accepts rare false positives for broader recall.
    """
    if not name or not passage:
        return False
    normalized_name = _strip_accents(name).lower()
    normalized_passage = _strip_accents(passage).lower()
    return normalized_name in normalized_passage

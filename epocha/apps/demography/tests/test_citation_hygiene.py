"""A structural guard on one citation, because four audit rounds could not
close it by hand.

The phase-6 gate caught a wrong Falconer & Mackay chapter reference in four
consecutive rounds, and each remediation corrected the occurrences its author
remembered rather than the ones that exist:

  round 1  the module cited chapter 8 alone; the fix wrote "chapter 10 --
           resemblance between relatives", which is chapter 9's title
  round 2  the fix wrote "8 Components of variance", which is a section
           heading inside chapter 8, and published it in five files under a
           sentence certifying it verified against the index
  round 3  the fix removed the titles from five artifacts and missed three
  round 4  the fix reached those three and missed an eighth, plus two
           occurrences inside the very module that wrote the no-titles rule

Four hand passes, four escapes. What a hand pass cannot do and a test can is
look at every line. The rule this file enforces is deliberately mechanical
and slightly blunt: any line naming a chapter of this source must use the
form "chapters 8-10" or "capp. 8-10", and no line anywhere may pair the
source with one of the chapter titles.

Titles are omitted on purpose. The chapter NUMBERS are verified against the
fourth edition's table of contents; the book has not been opened, no claim in
the project rests on a page, and amendment A1 derives every coefficient in
full so that nothing has to. A number can be checked against an index. A
title written from memory is how this defect kept coming back.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]

# Where the source may legitimately be named. Everything else is scanned too;
# these are only the roots walked.
SCANNED = (
    "epocha",
    "docs/whitepaper",
    "docs/superpowers/specs",
    "specs",
    "README.md",
    "README.it.md",
)

SKIP_DIRS = {".git", "__pycache__", "node_modules", ".ruff_cache", ".pytest_cache", "staticfiles"}
TEXT_SUFFIXES = {".py", ".md", ".json", ".html", ".txt"}

SOURCE = re.compile(r"Falconer", re.IGNORECASE)

# The three chapter titles that were wrongly attached to this source, plus the
# section heading promoted to a chapter title. Matched near a mention of the
# source, so ordinary uses of these words elsewhere are untouched.
FORBIDDEN_TITLES = (
    "components of variance",
    "resemblance between relatives",
    "somiglianza fra parenti",
    "componenti della varianza",
)

# A chapter reference that is NOT the sanctioned range.
BAD_CHAPTER = re.compile(
    r"\b(?:chapters?|chs?\.|capp?\.|capitolo|capitoli)\s*(?!8\s*[-–]\s*10\b)(\d+)",
    re.IGNORECASE,
)

SANCTIONED = re.compile(
    r"\b(?:chapters?|chs?\.|capp?\.|capitoli)\s*8\s*(?:[-–]|to|a)\s*10\b", re.IGNORECASE
)


def _files():
    for entry in SCANNED:
        target = REPO_ROOT / entry
        if target.is_file():
            yield target
            continue
        if not target.is_dir():
            continue
        for path in target.rglob("*"):
            if not path.is_file() or path.suffix not in TEXT_SUFFIXES:
                continue
            if any(part in SKIP_DIRS for part in path.parts):
                continue
            if path.name == Path(__file__).name:
                continue  # this file quotes the forbidden strings on purpose
            yield path


def _lines_mentioning_the_source():
    """(path, line number, text) for every line naming the source.

    A mention is resolved on its own line plus the two after it, since the
    citation is often wrapped -- the chapter frequently lands on the next
    line, which is exactly how a hand grep missed occurrences.
    """
    for path in _files():
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (UnicodeDecodeError, OSError):
            continue
        for index, line in enumerate(lines):
            if SOURCE.search(line):
                window = " ".join(lines[index : index + 3])
                yield path.relative_to(REPO_ROOT), index + 1, window


def test_the_source_is_named_somewhere_at_all():
    """A guard that matches nothing passes for the wrong reason."""
    mentions = list(_lines_mentioning_the_source())
    assert len(mentions) >= 5, (
        f"expected the source to be cited across the project; found {len(mentions)}"
    )


def test_no_chapter_title_is_attached_to_the_source():
    offenders = [
        (str(path), number, title)
        for path, number, window in _lines_mentioning_the_source()
        for title in FORBIDDEN_TITLES
        if title in window.lower()
    ]
    assert not offenders, (
        "a chapter title is attached to Falconer & Mackay. Titles are omitted "
        "project-wide: four audit rounds each caught a wrong one, and the "
        "numbers alone are what the table of contents verifies.\n"
        + "\n".join(f"  {p}:{n} -> {t!r}" for p, n, t in offenders)
    )


def test_every_chapter_reference_uses_the_sanctioned_range():
    offenders = []
    for path, number, window in _lines_mentioning_the_source():
        if SANCTIONED.search(window):
            continue
        match = BAD_CHAPTER.search(window)
        if match:
            offenders.append((str(path), number, match.group(0)))
    assert not offenders, (
        "a chapter of Falconer & Mackay is cited outside the sanctioned "
        '"8-10" range. The module cited chapter 8 alone until 2026-08-11; the '
        "material used spans 8 to 10 and the range is what the index "
        "verifies.\n" + "\n".join(f"  {p}:{n} -> {c!r}" for p, n, c in offenders)
    )


@pytest.mark.parametrize(
    "injected",
    [
        "Falconer & Mackay (1996), chapter 8, components of variance",
        "Falconer e Mackay (1996), capitolo 10 -- somiglianza fra parenti",
    ],
)
def test_the_guard_would_catch_an_injected_violation(injected):
    """The guard proved by injection rather than by reading it.

    Both strings are of the exact shape the four escaped remediations
    produced. Neither may pass either check.
    """
    lowered = injected.lower()
    assert any(title in lowered for title in FORBIDDEN_TITLES)
    assert not SANCTIONED.search(injected)
    assert BAD_CHAPTER.search(injected) is not None

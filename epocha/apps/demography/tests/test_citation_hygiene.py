"""A structural guard on one citation, because hand passes could not close it.

The phase-6 gate caught a wrong Falconer & Mackay chapter reference in four
consecutive rounds, and each remediation corrected the occurrences its author
remembered rather than the ones that exist:

  round 1  the module cited one chapter alone; the fix attached one chapter's
           title to a different chapter
  round 2  the fix promoted a section heading to its chapter's title and
           published it in five files, under a sentence certifying it
           verified against the index
  round 3  the fix removed the titles from five artifacts and missed three
  round 4  the fix reached those three and missed an eighth, plus two
           occurrences inside the very module that wrote the no-titles rule

Four hand passes, four escapes, which is what a test is for.

THE FIRST VERSION OF THIS GUARD DID NOT CATCH THE DEFECT IT WAS BUILT FOR,
and round 5 proved it by restoring the broken file into a scanned root and
watching the guard pass. Three separate holes, each sufficient on its own,
and all three are closed here because a guard is worth nothing until it has
been seen catching the thing it names:

  * it short-circuited on the whole window as soon as ONE sanctioned range
    appeared in it, so `"chapters 8-10; see chapter 3 for the pedigree"`
    passed -- and both bibliographies open with the sanctioned range, making
    the files where the defect actually recurred the least protected in the
    repository
  * its window was three lines, and the offending strings sat four and six
    lines below the mention
  * it walked six roots while its own comment claimed it read everything, so
    the build map -- a file the project rewrites by hand at every checkpoint,
    and which cites this source today -- was outside it

THE RULE. Near any mention of this source, every chapter reference must be
the sanctioned range 8-10, and no chapter title may appear. Each reference is
judged on its own; the presence of a correct one nearby excuses nothing.

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

SKIP_DIRS = {
    ".git",
    # Worktrees are checkouts of this same repository under a different
    # commit. Scanning them makes the guard report another branch's text as
    # if it were this one's, which is noise, not coverage.
    ".claude",
    "__pycache__",
    "node_modules",
    ".ruff_cache",
    ".pytest_cache",
    ".mypy_cache",
    "staticfiles",
    "htmlcov",
    ".venv",
    "venv",
}
TEXT_SUFFIXES = {".py", ".md", ".json", ".html", ".txt", ".rst", ".yml", ".yaml"}

SOURCE = re.compile(r"Falconer", re.IGNORECASE)

# The titles that were wrongly attached to this source across the four rounds.
FORBIDDEN_TITLES = (
    "components of variance",
    "resemblance between relatives",
    "somiglianza fra parenti",
    "componenti della varianza",
)

# Any chapter reference at all. Whether a given one is acceptable is decided
# by SANCTIONED_REFERENCE below, applied to THAT match -- never to the window.
ANY_CHAPTER = re.compile(
    r"\b(?:chapters?|chs?\.|capp?\.|capitolo|capitoli)\s*\d+(?:\s*(?:[-–]|to|a)\s*\d+)?",
    re.IGNORECASE,
)
SANCTIONED_REFERENCE = re.compile(
    r"\b(?:chapters?|chs?\.|capp?\.|capitoli)\s*8\s*(?:[-–]|to|a)\s*10\b", re.IGNORECASE
)

# Lines after the mention that still belong to the same citation. Six, because
# the wrapped bibliography entries in both whitepapers put the chapter four
# lines below the author name and the round-4 defect sat six below.
WINDOW_LINES = 7

# Files whose whole purpose is to talk ABOUT the defect. Only this one: a
# broad allowlist would be the hole all over again.
SELF = Path(__file__).name


def _text_files() -> list[Path]:
    """Every text file in the repository, minus build and cache directories.

    The whole repository, not a list of roots. The previous version walked six
    roots while claiming to read everything, and the build map -- which cites
    this source and is rewritten by hand at every checkpoint -- fell outside.
    """
    files = []
    for path in REPO_ROOT.rglob("*"):
        if not path.is_file() or path.suffix not in TEXT_SUFFIXES:
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.name == SELF:
            continue  # this file quotes the forbidden strings on purpose
        files.append(path)
    return files


def _windows(files: list[Path] | None = None):
    """(relative path, line number, window text) per mention of the source."""
    for path in files if files is not None else _text_files():
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (UnicodeDecodeError, OSError):
            continue
        for index, line in enumerate(lines):
            if SOURCE.search(line):
                window = " ".join(lines[index : index + WINDOW_LINES])
                yield path.relative_to(REPO_ROOT), index + 1, window


def _title_offenders(files: list[Path] | None = None):
    return [
        (str(path), number, title)
        for path, number, window in _windows(files)
        for title in FORBIDDEN_TITLES
        if title in window.lower()
    ]


def _chapter_offenders(files: list[Path] | None = None):
    """Every chapter reference near the source that is not the sanctioned one.

    EACH match is judged, not the window. The previous version skipped the
    entire window as soon as one sanctioned range appeared in it, which is
    precisely the shape every real citation has.
    """
    offenders = []
    for path, number, window in _windows(files):
        for match in ANY_CHAPTER.finditer(window):
            if SANCTIONED_REFERENCE.fullmatch(match.group(0).strip()):
                continue
            offenders.append((str(path), number, match.group(0)))
    return offenders


# ---------------------------------------------------------------------------
# The guard
# ---------------------------------------------------------------------------


def test_no_chapter_title_is_attached_to_the_source():
    offenders = _title_offenders()
    assert not offenders, (
        "a chapter title is attached to Falconer & Mackay. Titles are omitted "
        "project-wide: four audit rounds each caught a wrong one, and the "
        "numbers alone are what the table of contents verifies.\n"
        + "\n".join(f"  {p}:{n} -> {t!r}" for p, n, t in offenders)
    )


def test_every_chapter_reference_uses_the_sanctioned_range():
    offenders = _chapter_offenders()
    assert not offenders, (
        "a chapter of Falconer & Mackay is cited outside the sanctioned "
        '"8-10" range. The module cited chapter 8 alone until 2026-08-11; the '
        "material used spans 8 to 10 and the range is what the index "
        "verifies.\n" + "\n".join(f"  {p}:{n} -> {c!r}" for p, n, c in offenders)
    )


# ---------------------------------------------------------------------------
# The guard on the guard
# ---------------------------------------------------------------------------


def test_the_walk_reaches_the_files_that_actually_carry_the_citation():
    """A count alone cannot see a disarmed guard.

    The previous canary demanded five mentions where the repository has
    fifty-one, so dropping the three roots holding forty-three of them --
    every artifact where the defect really recurred -- left it green. These
    are the files by NAME, so removing one from the walk fails here.
    """
    reached = {str(path) for path, _, _ in _windows()}
    required = {
        "epocha/apps/demography/inheritance.py",
        "docs/whitepaper/epocha-whitepaper.md",
        "docs/whitepaper/epocha-whitepaper.it.md",
        "docs/superpowers/specs/2026-04-18-demography-design-it.md",
        "docs/build-map/epocha-build-map.html",
    }
    missing = required - reached
    assert not missing, f"the walk no longer reaches {sorted(missing)}"
    assert len(reached) >= 8, f"only {len(reached)} files mention the source; expected many more"


@pytest.mark.parametrize(
    ("relative", "payload"),
    [
        # A .py under the application root.
        (
            "epocha/apps/demography/_citation_probe.py",
            '"""Falconer & Mackay (1996), chapter 8 -- components of variance."""\n',
        ),
        # A .md under the whitepapers, wrapped the way the real entries are,
        # with the offence SIX lines below the author name and a sanctioned
        # range in between. Both holes round 5 found, in one probe.
        (
            "docs/whitepaper/_citation_probe.md",
            "- Falconer, D. S., and Mackay, T. F. C. (1996). *Introduction to\n"
            "  Quantitative Genetics*, 4th edition. Longman, Harlow.\n"
            "  Chapters 8-10, numbers verified against the table of contents.\n"
            "  Filler line to push the offence out of a short window.\n"
            "  Another filler line.\n"
            "  (See chapter 3 for the pedigree method, and chapter 9 --\n"
            "  resemblance between relatives -- for the covariance algebra.)\n",
        ),
        # The build map, which the previous walk did not reach at all.
        (
            "docs/build-map/_citation_probe.html",
            "<p>Falconer &amp; Mackay 1996, capitolo 10 -- somiglianza fra parenti.</p>\n",
        ),
    ],
)
def test_the_guard_catches_a_violation_injected_into_a_real_file(relative, payload):
    """END TO END: write the offence to disk, run the walk, expect it caught.

    This is the test the previous version lacked. Its injected-violation check
    applied the regexes to a string and never exercised `_text_files`, the
    window, or the offender assembly -- which is where all three holes were.
    """
    probe = REPO_ROOT / relative
    assert not probe.exists(), f"{relative} already exists; refusing to overwrite"
    probe.write_text(payload, encoding="utf-8")
    try:
        caught = _title_offenders() + _chapter_offenders()
        offending_paths = {entry[0] for entry in caught}
        assert relative in offending_paths, (
            f"the guard did not catch the violation injected into {relative}. "
            f"It reported: {caught!r}"
        )
    finally:
        probe.unlink()

    # And the repository is clean again once the probe is gone.
    assert not _title_offenders()
    assert not _chapter_offenders()


def test_a_sanctioned_reference_beside_a_wrong_one_does_not_excuse_it():
    """The short-circuit that made the whole guard inert, as a unit case."""
    window = "Falconer & Mackay (1996), chapters 8-10; see chapter 3 for pedigrees."
    matches = [m.group(0) for m in ANY_CHAPTER.finditer(window)]
    assert len(matches) == 2, matches
    assert sum(bool(SANCTIONED_REFERENCE.fullmatch(m.strip())) for m in matches) == 1


@pytest.mark.parametrize("spelling", ["chapters 8-10", "chapters 8 to 10", "capp. 8-10"])
def test_the_sanctioned_spellings_are_accepted(spelling):
    """A guard that rejects the correct form is a guard nobody keeps."""
    assert SANCTIONED_REFERENCE.fullmatch(spelling.strip()) is not None

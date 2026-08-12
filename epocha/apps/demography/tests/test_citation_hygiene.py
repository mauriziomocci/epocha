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

THREE VERSIONS OF THIS GUARD WERE WRONG BEFORE THIS ONE, and each was proved
wrong by injection rather than by reading:

  round 5  it short-circuited a whole window as soon as ONE sanctioned range
           appeared in it -- and every real citation contains one, so the
           bibliographies were the least protected text in the repository.
           Its window was three lines; it walked six roots while claiming to
           read everything
  round 6  the window, now seven lines, was defeated five more ways: an
           offence further below, an offence ABOVE the mention, a title
           broken by wrapping, `&nbsp;` hiding a space, and the correct
           citation with an em dash reported as a violation
  round 7  the paragraph rule manufactured false positives wherever there
           are no list items to split on -- in HTML a "paragraph" is one
           22 kB run of non-blank lines -- and its list split cut a canonical
           author-date entry in half at the year

THE RULE, as it now stands. A citation region is a paragraph or a list item.
Inside one, a chapter reference or a forbidden title offends if it lies
within PROXIMITY_CHARS of the source's name. Each reference is judged on its
own; a correct one nearby excuses nothing. The bound is on PROXIMITY, not on
formatting: line counts were guesses about how someone wraps text and were
defeated five separate ways.

THE DECLARED LIMIT. A citation whose name and chapter sit in different
paragraphs, or more than PROXIMITY_CHARS apart, is out of reach. Widening to
whole files was measured and rejected -- 138 violations against 0, mostly
the whitepaper's references to its own chapters. The amendment states this
scope and a test ties the two together, because twice the prose promised
coverage the walk did not have and nothing failed.

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
    # NOT the whole of `.claude`: `.claude/skills/` is tracked in git and
    # could carry the citation tomorrow. Only the worktrees are skipped, and
    # only because they are checkouts of this same repository under other
    # commits -- reporting another branch's text as this one's is noise.
    "worktrees",
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
# Widened after round 6: the project is aiming at a paper, so the most likely
# future home of this bibliography entry is a .bib or .tex file.
TEXT_SUFFIXES = {
    ".py",
    ".md",
    ".mdx",
    ".json",
    ".html",
    ".txt",
    ".rst",
    ".yml",
    ".yaml",
    ".tex",
    ".bib",
    ".toml",
    ".cfg",
    ".ini",
    ".ipynb",
}

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
    r"\b(?:chapters?|chaps?\.?|chs?\.?|capp?\.?|capitolo|capitoli)\s*\d+"
    r"(?:\s*(?:[-–—]|to|a)\s*\d+)?",
    re.IGNORECASE,
)
SANCTIONED_REFERENCE = re.compile(
    r"\b(?:chapters?|chaps?\.?|chs?\.?|capp?\.?|capitoli)\s*8\s*(?:[-–—]|to|a)\s*10\b",
    re.IGNORECASE,
)

# A CITATION REGION, not a window of N lines below the mention. Round 6 broke
# the window three ways -- an offence eight lines below, an offence ABOVE the
# mention, and a citation split so the name and the chapter never shared a
# window -- and each was a symptom of the same thing: the bound was tuned to
# the last case seen rather than derived from how citations are written.
#
# A region is a contiguous run of non-blank lines, further split wherever a
# list item starts. The paragraph is what a citation actually occupies, in a
# docstring and in prose alike; the list split is what keeps a bibliography's
# neighbouring entry from being swept in, which matters because the
# whitepapers' reference lists have no blank line between entries and Solon
# (1999) legitimately cites a chapter 29 two entries away.
# Bullet markers only. A numbered-item pattern also matched a continuation
# line beginning with a year -- "1996. Introduction to Quantitative
# Genetics..." -- which split the canonical author-date bibliography entry in
# half and dropped its chapter out of the region entirely.
LIST_ITEM = re.compile(r"^(\s*)[-*+]\s")

# A chapter reference offends only if it sits within this many characters of
# the source's name INSIDE the region. Regions are paragraphs in prose, but
# in HTML they are whatever the author's line wrapping produced: the build
# map's here-band is one 22 kB region, and without a proximity bound its
# ordinary talk of "chapter 8" -- meaning a chapter of the whitepaper --
# is reported as a Falconer violation. The same shape appears in Markdown
# tables and JSON blocks, which have no list items to split on.
#
# This is a bound on PROXIMITY, not on line count. The distinction is the
# whole lesson of rounds 5 and 6: a line count is a guess about formatting
# and was defeated five ways, while "near the name" is what the rule
# actually means.
PROXIMITY_CHARS = 300

# Text is normalised before matching. `&nbsp;` in the build map -- an HTML
# file this project rewrites by hand at every checkpoint -- defeated the
# whitespace class, and a title broken across two lines by wrapping never
# matched the flat string it is compared against.
HTML_ENTITIES = {"&nbsp;": " ", "&amp;": "&", "&#160;": " ", "&ndash;": "-", "&mdash;": "-"}

# Files whose whole purpose is to talk ABOUT the defect. Only this one: a
# broad allowlist would be the hole all over again.
SELF = Path(__file__).name


def _probe_path(relative: str) -> Path:
    """A probe path unique to this process.

    The probes write into the real working tree, so a fixed name collides
    when two pytest processes run at once -- which happened during the round
    7 audit -- and a kill between the write and the unlink would leave a file
    naming the source with a wrong chapter, turning the guard red on its own
    debris. The pid does not remove the second risk; it removes the first and
    makes the debris identifiable.
    """
    import os

    path = Path(relative)
    probe = REPO_ROOT / path.parent / f"{path.stem}_{os.getpid()}{path.suffix}"
    assert not probe.exists(), f"{probe} already exists; refusing to overwrite"
    return probe


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


def _normalise(text: str) -> str:
    for entity, replacement in HTML_ENTITIES.items():
        text = text.replace(entity, replacement)
    return " ".join(text.split())


def _regions(lines: list[str]):
    """(first line number, text) for each citation region of a file.

    A region ends at a blank line or at the start of the next list item, and
    its text is normalised and flattened, so a title broken across two lines
    by wrapping matches and `&nbsp;` does not hide a chapter number.
    """
    start = 0
    indent = 0
    current: list[str] = []
    for index, line in enumerate(lines):
        if not line.strip():
            if current:
                yield start + 1, _normalise(" ".join(current))
                current = []
            continue
        match = LIST_ITEM.match(line)
        if current and match and len(match.group(1)) <= indent:
            yield start + 1, _normalise(" ".join(current))
            current = []
            indent = len(match.group(1))
        elif not current and match:
            indent = len(match.group(1))
        if not current:
            start = index
        current.append(line)
    if current:
        yield start + 1, _normalise(" ".join(current))


def _windows(files: list[Path] | None = None):
    """(relative path, line number, region text) per region naming the source."""
    for path in files if files is not None else _text_files():
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (UnicodeDecodeError, OSError):
            continue
        for number, region in _regions(lines):
            if SOURCE.search(region):
                yield path.relative_to(REPO_ROOT), number, region


def _title_offenders(files: list[Path] | None = None):
    offenders = []
    for path, number, window in _windows(files):
        lowered = window.lower()
        mentions = [m.start() for m in SOURCE.finditer(window)]
        for title in FORBIDDEN_TITLES:
            for match in re.finditer(re.escape(title), lowered):
                if any(abs(match.start() - at) <= PROXIMITY_CHARS for at in mentions):
                    offenders.append((str(path), number, title))
                    break
    return offenders


def _chapter_offenders(files: list[Path] | None = None):
    """Every chapter reference near the source that is not the sanctioned one.

    EACH match is judged, not the window. The previous version skipped the
    entire window as soon as one sanctioned range appeared in it, which is
    precisely the shape every real citation has.
    """
    offenders = []
    for path, number, window in _windows(files):
        mentions = [m.start() for m in SOURCE.finditer(window)]
        for match in ANY_CHAPTER.finditer(window):
            if SANCTIONED_REFERENCE.fullmatch(match.group(0).strip()):
                continue
            if not any(abs(match.start() - at) <= PROXIMITY_CHARS for at in mentions):
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
        "epocha/apps/demography/tests/test_inheritance.py",
        "docs/whitepaper/epocha-whitepaper.md",
        "docs/whitepaper/epocha-whitepaper.it.md",
        "docs/superpowers/specs/2026-04-18-demography-design-it.md",
        "docs/superpowers/specs/2026-04-18-demography-design.md",
        "docs/build-map/epocha-build-map.html",
    }
    missing = required - reached
    assert not missing, f"the walk no longer reaches {sorted(missing)}"
    # The floor is set just under the measured 20, not at an arbitrary small
    # number. The previous canary demanded five where the repository had
    # fifty-one mentions, so dropping the three roots holding forty-three of
    # them stayed green; the version after it demanded eight, which `specs/`
    # alone could absorb. A floor that a whole directory can be removed
    # under is not a floor.
    assert len(reached) >= 18, f"only {len(reached)} files mention the source; the walk has shrunk"


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
    probe = _probe_path(relative)
    probe.write_text(payload, encoding="utf-8")
    try:
        # SCOPED to the probe. `files` has existed on all three helpers since
        # the guard was written and no call ever passed it -- a parameter
        # always given the same value, which is the smell, except here the
        # unused value is the fix: nine probes walking the whole repository
        # twice each cost 55s, sixteen per cent of the suite.
        caught = _title_offenders([probe]) + _chapter_offenders([probe])
        assert caught, f"the guard did not catch the violation injected into {relative}"
    finally:
        probe.unlink()


@pytest.mark.parametrize(
    ("label", "payload", "expect_caught"),
    [
        (
            "eight lines below the mention, same paragraph",
            "- Falconer, D. S., and Mackay, T. F. C. (1996). Introduction to\n"
            + "".join(f"  Filler line {i}.\n" for i in range(8))
            + "  See chapter 3 for the pedigree method.\n",
            True,
        ),
        (
            "ABOVE the mention",
            "- The section on chapter 9 covers the covariance algebra.\n"
            "  Falconer, D. S., and Mackay, T. F. C. (1996), chapters 8-10.\n",
            True,
        ),
        (
            "title broken across two lines by wrapping",
            "- Falconer, D. S., and Mackay (1996). The section on resemblance\n"
            "  between relatives gives the covariance algebra.\n",
            True,
        ),
        (
            "HTML entity hiding the space",
            "<p>Falconer &amp; Mackay 1996, chapter&nbsp;8.</p>\n",
            True,
        ),
        (
            "em dash in the sanctioned range is NOT a violation",
            "- Falconer, D. S., and Mackay (1996), chapters 8\u201410.\n",
            False,
        ),
        (
            "a sub-list item is a continuation, not a new citation",
            "- Falconer, D. S., and Mackay (1996), chapters 8-10.\n"
            "  - chapter 3 gives the pedigree method.\n",
            True,
        ),
        (
            "an author-date continuation line beginning with the year",
            "- Falconer, D. S., and Mackay, T. F. C.\n"
            "  1996. Introduction to Quantitative Genetics, 4th ed., chapter 3.\n",
            True,
        ),
        (
            "a chapter written without the abbreviating period",
            "- Falconer, D. S., and Mackay (1996), Ch 3.\n",
            True,
        ),
        (
            "prose about the whitepaper's own chapter 8, far from the name",
            "<p>Falconer &amp; Mackay 1996, chapters 8-10.</p>\n"
            "<p>" + "Filler about the model. " * 30 + "See chapter 8 of this paper.</p>\n",
            False,
        ),
        (
            "a neighbouring bibliography entry's own chapter is not swept in",
            "- Falconer, D. S., and Mackay (1996), chapters 8-10.\n"
            "- Solon, G. (1999). Handbook of Labor Economics, vol. 3A, ch. 29.\n",
            False,
        ),
    ],
)
def test_the_shapes_round_six_used_to_defeat_the_guard(label, payload, expect_caught):
    """Six evasions, five of which worked against the window version.

    The window was seven lines BELOW a mention, so an offence further down,
    an offence above, or a citation whose title wrapped all escaped; `&nbsp;`
    defeated the whitespace class in the one HTML file the walk had just been
    widened to reach; and the sanctioned range written with an em dash was
    reported as a violation, which is the kind of false positive that gets a
    guard switched off. The last case is the price of the fix: regions must
    split at list items or a neighbour's legitimate chapter is swept in.
    """
    probe = _probe_path("docs/whitepaper/_evasion_probe.md")
    probe.write_text(payload, encoding="utf-8")
    try:
        caught = _title_offenders([probe]) + _chapter_offenders([probe])
    finally:
        probe.unlink()
    if expect_caught:
        assert caught, f"the guard missed: {label}"
    else:
        assert not caught, f"false positive on: {label} -> {caught!r}"


def test_the_amendment_describes_the_scope_the_guard_actually_has():
    """The prose and the code, tied together.

    Round 7 objected -- rightly -- that asserting the guard does NOT catch a
    cross-paragraph citation pins the weakness in place: whoever widened the
    scope later would see a red indistinguishable from a regression. So the
    assertion moved to where the mismatch actually hurts. The amendment must
    describe the scope in the terms the code implements; if the code grows to
    span paragraphs, this fails and the sentence has to be rewritten with it,
    which is the outcome wanted. Twice now the prose has promised a coverage
    the walk did not have, and both times nothing failed.
    """
    amendment = (REPO_ROOT / "docs/superpowers/specs/2026-04-18-demography-design-it.md").read_text(
        encoding="utf-8"
    )
    claim = [line for line in amendment.splitlines() if "test_citation_hygiene" in line]
    assert claim, "the amendment no longer describes the guard at all"
    sentence = " ".join(claim).lower()
    assert "regione" in sentence, (
        "the amendment must describe the guard's scope as a REGION, which is "
        f"what the code implements. It says: {sentence!r}"
    )
    assert "riga qualunque" not in sentence, (
        "the amendment claims line-wide coverage the guard does not have"
    )


def test_the_region_rule_does_not_span_paragraphs_today():
    """The limit as a MEASUREMENT, kept separate from the contract above.

    Widening to whole files was measured and rejected: 138 violations against
    0, most of them the whitepaper's references to its own chapters, plus
    Solon (1999) chapter 29 two bibliography entries from Falconer.
    """
    probe = _probe_path("docs/whitepaper/_split_probe.md")
    probe.write_text(
        "- Falconer, D. S., and Mackay (1996), chapters 8-10.\n"
        "\n"
        "A paragraph in between.\n"
        "\n"
        "That source's chapter 3 covers the pedigree method.\n",
        encoding="utf-8",
    )
    try:
        caught = _title_offenders([probe]) + _chapter_offenders([probe])
    finally:
        probe.unlink()
    assert not caught, (
        "the region rule now spans paragraphs -- an improvement, but the "
        "amendment's wording has to be rewritten with it, and the test above "
        "is what enforces that"
    )


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

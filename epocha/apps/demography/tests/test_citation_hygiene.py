"""A structural guard on one citation, because hand passes could not close it.

The phase-6 gate caught a wrong Falconer & Mackay chapter reference in four
consecutive rounds, and each remediation corrected the occurrences its author
remembered rather than the ones that exist. On its first run this guard found
seven more, including both whitepaper bibliographies and an English design
spec nobody had opened. A rule four authors have already broken is not a rule,
it is a wish.

THE RULE. A citation region is a paragraph or a list item, with HTML entities
resolved and whitespace flattened. If a region names this source, every
chapter reference in it must be the sanctioned range 8-10, and no forbidden
title may appear. Each reference is judged on its own; a correct one nearby
excuses nothing, which is the hole that made the first version inert.

THE DECLARED LIMIT. A citation whose name and chapter sit in different
paragraphs is out of reach. Widening to whole files was measured and rejected:
138 violations against 0, mostly the whitepaper's references to its own
chapters, plus Solon (1999) chapter 29 two bibliography entries away.

THE PROCESS RULE, which is the real product of rounds 5 to 8 and is written
here because it cost four of them. THIS GUARD IS EXTENDED ONLY FOR A
VIOLATION OBSERVED IN THE REPOSITORY, never for one an auditor constructs.
Rounds 6, 7 and 8 all ran the same loop -- a reviewer invents a shape, the
author adds a case and a constant, the next round beats the constant with
another invented shape -- and that loop has no fixed point, because the space
of constructible inputs is infinite and the set of real citations here has
twenty members. Round 8 measured the cost of ignoring this: the file had
grown from 167 lines to 543, and the last layer added a `PROXIMITY_CHARS`
bound that suppressed a false positive WHICH DOES NOT EXIST -- removing the
bound leaves the repository at zero offenders -- while opening a real blind
spot at 812 characters, two false positives on numbered and nested
bibliographies, and two branches with no witness.

THE SIZE, counted rather than asserted, because round 9 caught this file
publishing an unverified figure about ITSELF in four artifacts at once. The
series, all in total lines: 167 at birth, 543 at round 8's peak, 453 after
the cut. Round 8's cut was 16.6%, not "to a third" as the commit that made
it says, and "back under 300" was true only of code lines -- 305 to 255 --
while the two numbers it followed were total lines. Switching units
mid-sentence is how a false series survives four reviews. No current line
count is stated here: round 9 stated one and round 10 found it wrong within
a day, because a figure describing the file that carries it is invalidated
by every edit to that file. Count it, do not read it.

THE SECOND PROCESS RULE, from round 10, and the counterpart to the one
above. WHEN A PAYLOAD OR A CONSTANT CHANGES, RUN THE MUTATION BATTERY
AGAINST THE PREVIOUS VERSION TOO. Twice running, a repair destroyed a
witness while adding one: round 8 deleted a constant together with the two
tests that bound it, and round 9 capitalised the wrap-broken title payload
-- correctly, to give the case-fold a witness -- and moved the break out of
the title in the same edit, silently retiring the only witness whitespace
flattening had. Both times the property lost was one this docstring
asserts. A fix is not judged by the mutants it kills but by the ones it
stops killing, and that is a difference, not a reading.
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
# Bullets only. The numbered form was restored at round 8 to protect a
# numbered bibliography from sweeping in its neighbour's legitimate chapter,
# and round 9 measured that no such bibliography exists here: with and
# without it the repository yields the same 53 regions naming the source
# across the same 20 files and the same zero offenders, and no test fails
# when it goes. It was an extension for a constructed case, which is exactly
# what the process rule above forbids. Restore it when a numbered
# bibliography appears -- with the file and line that carries it.
LIST_ITEM = re.compile(r"^(\s*)[-*+]\s")


# Text is normalised before matching. `&nbsp;` in the build map -- an HTML
# file this project rewrites by hand at every checkpoint -- defeated the
# whitespace class, and a title broken across two lines by wrapping never
# matched the flat string it is compared against.
#
# `&#160;`, `&ndash;` and `&mdash;` were here too and are gone: round 10
# counted them at ZERO occurrences in the repository and no test failed when
# they went, so they were extensions for constructed cases -- the same
# measurement that removed the numbered-list marker, applied to the entry the
# same round left standing. `&amp;` stays on the other side of that line: it
# is measured at 12 real occurrences, and although the guard does not depend
# on it today -- `SOURCE` matches the surname alone -- it normalises an
# entity the surveyed text actually contains, which a constructed case does
# not.
HTML_ENTITIES = {"&nbsp;": " ", "&amp;": "&"}

# Files whose whole purpose is to talk ABOUT the defect. Only this one: a
# broad allowlist would be the hole all over again.
SELF = Path(__file__).name


def _probe_path(tmp_path: Path, relative: str) -> Path:
    """A probe file OUTSIDE the working tree.

    The probes used to write into the repository, which put them in the path
    of the two whole-repository walks: a second pytest process running a
    probe made the first go red on a file that was not its own, and a kill
    between the write and the unlink would have left a wrong citation on disk
    for the guard to trip over. Writing under pytest's `tmp_path` and passing
    the file explicitly -- the scope parameter the helpers have always taken
    -- removes both, and is why the probes no longer walk the repository at
    all.
    """
    path = Path(relative)
    probe = tmp_path / path.name
    probe.parent.mkdir(parents=True, exist_ok=True)
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
                try:
                    label = path.relative_to(REPO_ROOT)
                except ValueError:
                    # A probe under pytest's tmp_path, outside the tree.
                    label = path
                yield label, number, region


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


# Named rather than inlined into the parametrize, so the completeness test
# below can read the same list instead of reaching into pytest's marks.
INJECTION_CASES = [
    # A .py under the application root.
    (
        "epocha/apps/demography/_citation_probe.py",
        '"""Falconer & Mackay (1996), chapter 8 -- components of variance."""\n',
        "components of variance",
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
        "resemblance between relatives",
    ),
    # The build map, which the previous walk did not reach at all.
    (
        "docs/build-map/_citation_probe.html",
        "<p>Falconer &amp; Mackay 1996, capitolo 10 -- somiglianza fra parenti.</p>\n",
        "somiglianza fra parenti",
    ),
    # The fourth forbidden title had no witness until round 10: three
    # payloads cannot testify for four strings while the assertion only
    # checks that SOMETHING was caught. The form is the one the Italian
    # whitepaper carried at commit 5a2713e, `epocha-whitepaper.it.md:901`,
    # reduced to the single title so it testifies for that one alone.
    (
        "docs/whitepaper/_citation_probe.it.md",
        "Falconer & Mackay 1996, cap. 8 -- componenti della varianza.\n",
        "componenti della varianza",
    ),
]


@pytest.mark.parametrize(("relative", "payload", "expected_title"), INJECTION_CASES)
def test_the_guard_catches_a_violation_injected_into_a_real_file(
    relative, payload, expected_title, tmp_path
):
    """Write the offence to disk, read it back, expect BOTH guards to fire.

    Each payload carries a forbidden title AND a chapter outside the range, so
    the two are asserted SEPARATELY. Summing them first is what made this test
    unable to fail: with the union, deleting the Italian titles, deleting
    `components of variance`, or dropping `capitolo` from the chapter pattern
    each left all eighteen tests green, because the other branch of the same
    payload still fired.

    Separating them was not enough, and round 10 measured why: `assert titles`
    checks that SOMETHING was caught, so three payloads could not testify for
    four forbidden strings and `componenti della varianza` could be deleted
    with the suite still green. The assertion therefore names WHICH title it
    expects, and `test_every_forbidden_title_has_a_witness` below refuses to
    let a fifth string be added without one.

    The probes no longer walk the repository -- `files=[probe]` scopes both
    helpers -- so what this exercises is region assembly and offender
    assembly, not `_text_files`. The walk itself is covered by
    `test_the_walk_reaches_the_files_that_actually_carry_the_citation`.
    """
    probe = _probe_path(tmp_path, relative)
    probe.write_text(payload, encoding="utf-8")
    try:
        # SCOPED to the probe. `files` has existed on all three helpers since
        # the guard was written and no call ever passed it -- a parameter
        # always given the same value, which is the smell, except here the
        # unused value is the fix: nine probes walking the whole repository
        # twice each cost 55s, sixteen per cent of the suite.
        titles = _title_offenders([probe])
        chapters = _chapter_offenders([probe])
    finally:
        probe.unlink(missing_ok=True)
    assert {title for _, _, title in titles} == {expected_title}, (
        f"the title guard did not report exactly {expected_title!r} for {relative}: {titles!r}"
    )
    assert chapters, f"the chapter guard missed the violation injected into {relative}"


def test_every_forbidden_title_has_a_witness():
    """No forbidden string may be added without a payload that testifies for it.

    This is the structural half of round 10's second blocking finding. The
    first half -- naming the expected title above -- fixes the four strings
    that exist; this one fixes the class, by failing the moment a fifth is
    added with no probe behind it. Without it the next entry is silently
    deletable, which is exactly how the fourth one got here.
    """
    covered = {
        expected
        for _, _, expected in (
            test_the_guard_catches_a_violation_injected_into_a_real_file.pytestmark[0].args[1]
        )
    }
    assert covered == set(FORBIDDEN_TITLES), (
        f"forbidden titles with no witness: {sorted(set(FORBIDDEN_TITLES) - covered)}"
    )


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
            # Capitalised the way the offence was actually written: the index
            # entry it came from is a chapter title, so every real occurrence
            # -- `2026-04-18-demography-design-it.md:1893` and
            # `inheritance.py:6` at commit 5a2713e -- carried initial capitals.
            # Lower-casing before the comparison is therefore load-bearing, and
            # until this payload was capitalised nothing failed when it went.
            # The break falls INSIDE the title, which is the whole point: round
            # 9 capitalised this payload to give `.lower()` a witness and moved
            # the break out of the title in the same edit, which silently
            # retired the witness for whitespace flattening. Both properties
            # ride on this one payload; changing either without re-running the
            # mutation battery against the PREVIOUS version loses the other.
            "title broken across two lines by wrapping",
            "- Falconer, D. S., and Mackay (1996). The index gives 9 *Resemblance\n"
            "  between Relatives* for the covariance algebra.\n",
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
            "a chapter written without the abbreviating period",
            "- Falconer, D. S., and Mackay (1996), Ch 3.\n",
            True,
        ),
        (
            "a neighbouring bibliography entry's own chapter is not swept in",
            "- Falconer, D. S., and Mackay (1996), chapters 8-10.\n"
            "- Solon, G. (1999). Handbook of Labor Economics, vol. 3A, ch. 29.\n",
            False,
        ),
    ],
)
def test_the_shapes_that_once_defeated_the_guard(label, payload, expect_caught, tmp_path):
    """Every shape that beat an earlier version, and two that must NOT fire.

    All of these were live escapes, not hypotheticals: each defeated the
    guard as it stood when it was found. The window version missed an offence
    below its bound, an offence above the mention, a title broken by
    wrapping, and `&nbsp;` hiding a space; the paragraph version cut a
    sub-list item into a region that no longer named the source.

    The two `False` cases are the price of the fix rather than the fix: a
    region must split at list items or a neighbour's legitimate chapter is
    swept in, and the sanctioned range written with an em dash must not be
    reported, because a false positive on a correct citation is how a guard
    gets switched off.

    Cases whose only provenance was an auditor's imagination were removed
    with the constant they justified -- see the module docstring's process
    rule.
    """
    probe = _probe_path(tmp_path, "evasion_probe.md")
    probe.write_text(payload, encoding="utf-8")
    try:
        caught = _title_offenders([probe]) + _chapter_offenders([probe])
    finally:
        probe.unlink(missing_ok=True)
    if expect_caught:
        assert caught, f"the guard missed: {label}"
    else:
        assert not caught, f"false positive on: {label} -> {caught!r}"


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

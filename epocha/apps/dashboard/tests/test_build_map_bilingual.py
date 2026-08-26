"""Structural guard on the bilingual build map.

`docs/build-map/epocha-build-map.html` is the project's source of truth for
build status, and since amendment 1.1.0 of the constitution it carries both
languages in one file: Italian normative, English mirror. The rule the user
called inderogabile is that the two never drift apart.

A rule four rounds of review could not hold by prose is not a rule, it is a
wish -- the citation guard in `demography` cost eleven audit rounds to learn
that. So the alignment is held by this file instead of by intention. It
enforces the spec at `specs/20260812-143706-bilingual-build-map/spec.md`:

  FR-003b  no visible text outside the declared exemptions may be unkeyed
  FR-006   every key exists in both languages
  FR-007   the two languages agree on status tokens and on numbers
  FR-007a  numbers compare after notation is normalised (16.6% == 16,6%)
  FR-007b  each text carries a fingerprint; a stale one fails

THE DECLARED LIMITS live in FR-008 of the spec and are enumerated THERE and
nowhere else. This docstring used to repeat them, promising in the same breath
that "the two enumerations cannot diverge" -- and they had already diverged: it
listed five where FR-008 said four, dropped the one about content language, and
added two FR-008 did not carry. A closed list in two places diverges. That is
the fifth process rule of this project, and the sentence claiming immunity from
it was the violation.

What the guard does NOT catch, in one line each, as a pointer rather than an
enumeration: numbers written as words, a translation present but wrong, a
fingerprint recomputed without translating, the actual language of the content,
and decimals. Read FR-008 for the authoritative text.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest
from bs4 import BeautifulSoup, Comment

MAP = Path(__file__).resolve().parents[4] / "docs/build-map/epocha-build-map.html"

# Digest and key helpers live in the maintenance script, so the value the guard
# compares against and the value the tooling writes cannot drift apart -- one
# implementation, two callers.
sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "scripts"))
from build_map_i18n import digest  # noqa: E402

LANGS = ("it", "en")
NORMATIVE = "it"

# FR-003a, closed list. Everything else visible must be keyed.
EXEMPT_CLASSES = {"num", "tag", "ev", "found-ref", "val", "swatch", "lang-switch"}

STATUS_TOKENS = ("s-done", "s-prog", "s-todo", "done", "prog", "todo")

# INTEGERS ONLY, and the limit is declared rather than engineered around.
# A decimal's notation depends on the language -- 48,85 against 48.85 -- and a
# bilingual normaliser has to tell a decimal mark from a thousands mark from a
# chapter reference from a phase id. Three successive attempts each fixed one
# shape and broke another, which is the loop the first process rule forbids:
# a guard is extended for a violation OBSERVED, never for one its author
# invents while chasing the previous case. Integers carry the figures that
# actually diverge here -- counts of findings, rounds, tasks, tests -- and they
# read the same in both languages.
INTEGER = re.compile(r"(?<![\d.,§])\d+(?![.,]?\d)")

# Identifiers that look like numbers and are exempt under FR-003a.
IDENTIFIER = re.compile(
    r"§\s*\d+(?:\.\d+)*"
    r"|\b\d+e-\d+\b"
    r"|\b\d{4}-\d{2}-\d{2}\b"
    r"|(?:fase|phase|deliberazione|deliberation|plan|round)[\s‑-]*\d+(?:\.\d+)*[a-z]?",
    re.IGNORECASE,
)


def comparable_text(el) -> str:
    """Element text with exempt identifiers removed.

    <code> spans go whole: they carry paths, SHAs and symbols, exempt under
    FR-003a and identical in both twins anyway.
    """
    clone = BeautifulSoup(str(el), "html.parser")
    for code in clone.select("code"):
        code.decompose()
    return IDENTIFIER.sub(" ", clone.get_text())


def integers_in(el) -> set[str]:
    """WHICH integers appear, not how many times each.

    A figure present in one language and absent in the other is a real
    divergence. The same figure cited twice instead of three times, in prose of
    27000 characters, is not -- comparing multisets reports it as one and the
    reader learns to ignore the guard.
    """
    return set(INTEGER.findall(comparable_text(el)))


@pytest.fixture(scope="module")
def soup() -> BeautifulSoup:
    return BeautifulSoup(MAP.read_text(encoding="utf-8"), "html.parser")


@pytest.fixture(scope="module")
def pairs(soup) -> dict:
    out: dict[str, dict[str, object]] = {}
    for el in soup.select("[data-k]"):
        out.setdefault(el["data-k"], {})[el.get("data-lang", "?")] = el
    return out


def test_every_key_exists_in_both_languages(pairs):
    """FR-006. The predicate the whole feature rests on."""
    missing = {
        key: sorted(set(LANGS) - set(langs))
        for key, langs in pairs.items()
        if set(langs) != set(LANGS)
    }
    assert not missing, f"chiavi presenti in una lingua sola: {missing}"


def test_the_page_actually_carries_pairs(pairs):
    """A floor, because every other test here passes vacuously on an empty set.

    Not an arbitrary small number: the page carries 111 pairs, and a floor a
    whole section could be deleted under is not a floor. The citation guard
    learned this the expensive way -- its first canary demanded five mentions
    where the repository had fifty-one.
    """
    assert len(pairs) >= 100, f"solo {len(pairs)} coppie: la chiavatura si e' ristretta"


def test_no_visible_text_escapes_the_keying(soup):
    """FR-003b, and the hole round 7 of the spec gate found.

    Without this the guard compares keys, so a block added with NO key in one
    language violates nothing and passes every other test in this file. It is
    the likeliest failure of the real workflow: at a checkpoint one adds prose,
    not keys.
    """
    unkeyed = []
    for el in soup.select(".wrap")[0].find_all(True):
        if el.get("data-k") or el.find_parent(attrs={"data-k": True}):
            continue
        if el.name in ("script", "style", "button"):
            continue
        classes = set(el.get("class") or [])
        if classes & EXEMPT_CLASSES:
            continue
        # Its OWN text, not its descendants': an element with children can still
        # carry bare text beside them. That is how the legend escaped -- each
        # <li> holds an empty exempt <span class="swatch"> plus untranslated
        # text, and a predicate that skipped any element with a child never
        # looked at it.
        own = "".join(
            s
            for s in el.find_all(string=True, recursive=False)
            if not isinstance(s, Comment)  # a comment is not visible text
        ).strip()
        if own:
            unkeyed.append(f"<{el.name} class={sorted(classes)}> {own[:60]!r}")
    assert not unkeyed, "testo visibile non chiavato e non esente:\n  " + "\n  ".join(unkeyed)


# Blocks that are legitimately identical in both languages. A closed list, and
# short on purpose: every entry is a place the guard cannot help, so each one
# must be worth its exemption.
IDENTICAL_BY_DESIGN = {"rule.paper.k", "rule.rng.k"}


def test_no_block_is_left_untranslated(pairs):
    """The predicate whose absence let the largest block on the board ship in English.

    Key, status, integers and fingerprints were all satisfied by a pair whose
    Italian slot held 2316 characters of verbatim English -- the description of
    phase 2, the frontier the map itself declares. Every other test passed,
    because none of them asked the one question that matters: are the two texts
    actually different?

    The limits declared in the module docstring say a translation that is
    present but wrong slips through. That stays true. This test closes the
    narrower and far commoner case: a translation that was never made at all.
    """
    untranslated = [
        key
        for key, langs in pairs.items()
        if key not in IDENTICAL_BY_DESIGN
        and len(langs) == 2
        and langs["it"].get_text().strip() == langs["en"].get_text().strip()
    ]
    assert not untranslated, (
        "blocchi identici nelle due lingue, cioe' mai tradotti: "
        f"{sorted(untranslated)}\n"
        "Se un blocco e' legittimamente identico, va messo in IDENTICAL_BY_DESIGN "
        "con la ragione, non lasciato passare in silenzio."
    )


def test_status_tokens_agree_between_languages(pairs):
    """FR-007.

    The status is compared on the CLASS TOKEN, never on the visible label:
    `In progress` and `In corso` are a correct translation and would read as a
    divergence. It is the rule about preferring the discriminator the system
    already encodes.
    """
    bad = []
    for key, langs in pairs.items():
        seen = {
            lang: sorted(t for t in (el.get("class") or []) if t in STATUS_TOKENS)
            for lang, el in langs.items()
        }
        if len(set(map(tuple, seen.values()))) > 1:
            bad.append(f"{key}: {seen}")
    assert not bad, "token di stato divergenti fra le lingue:\n  " + "\n  ".join(bad)


def test_integers_agree_between_languages(pairs):
    """FR-007. Limits (a) and (e) apply: numbers as words, and decimals, escape."""
    bad = []
    for key, langs in pairs.items():
        if len(langs) < 2:
            continue
        seen = {lang: integers_in(el) for lang, el in langs.items()}
        shared = set.intersection(*seen.values())
        only = {lang: sorted(v - shared) for lang, v in seen.items() if v - shared}
        if only:
            bad.append(f"{key}: presenti in una lingua sola -> {only}")
    assert not bad, "interi divergenti fra le lingue:\n  " + "\n  ".join(bad)


def test_no_fingerprint_is_stale(pairs):
    """FR-007b, and the answer to the gravest finding of the spec gate.

    Key, status and numbers all miss the commonest divergence at a checkpoint:
    prose rewritten in one language only. That case has both keys, the same
    status and the same numbers. The fingerprint catches it -- subject to
    limit (c), which is why the docstring above states it rather than promising
    what no checksum can give.
    """
    stale = []
    for key, langs in pairs.items():
        if len(langs) < 2:
            continue
        for lang, el in langs.items():
            recorded = el.get("data-fp-self")
            actual = digest(el.get_text())
            if recorded != actual:
                stale.append(f"{key} [{lang}]: registrata {recorded}, calcolata {actual}")
        mirror = langs.get("en")
        if mirror is not None:
            expected = digest(langs[NORMATIVE].get_text())
            if mirror.get("data-fp") != expected:
                stale.append(
                    f"{key}: impronta del normativo {mirror.get('data-fp')}, attesa {expected} "
                    "-- il testo italiano e' cambiato e la traduzione inglese no"
                )
    assert not stale, "impronte obsolete:\n  " + "\n  ".join(stale)


def test_italian_is_the_resting_state(soup):
    """FR-002. Without JavaScript the reader sees Italian, not both stacked.

    So the default must live in CSS. Asserting on the stylesheet is the only
    way to witness it: a test that only checked the script would pass on a page
    that shows both languages to anyone with JS disabled.
    """
    css = soup.select_one("style").get_text()
    # Asserted with `!important`, and that is the point of this test rather than
    # a detail of it. The first version checked only that the two rules EXISTED,
    # and a rule that exists can still lose: `.count-row .lab` scores (0,2,0)
    # against `[data-lang="en"]` at (0,1,0), so three labels rendered in BOTH
    # languages at rest while this test stayed green.
    for rule in (
        '[data-lang="en"] { display: none !important; }',
        '[data-lang-sel="en"] [data-lang="en"] { display: revert !important; }',
        '[data-lang-sel="en"] [data-lang="it"] { display: none !important; }',
    ):
        assert rule in css, f"regola mancante o senza !important: {rule}"


def test_the_page_stays_self_contained(soup):
    """FR-005. The artifact publishes under a CSP that blocks every external host."""
    external = [
        str(el)[:80]
        for el in soup.find_all(True)
        if any(
            str(el.get(a, "")).startswith(("http://", "https://", "//")) for a in ("src", "href")
        )
    ]
    assert not external, f"risorse esterne nella pagina: {external}"

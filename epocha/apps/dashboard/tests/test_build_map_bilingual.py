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

THE FOUR DECLARED LIMITS, which FR-008 requires be stated here and which are
enumerated in FR-008 and nowhere else, so that the two enumerations cannot
diverge the way five earlier counts in this work item did:

  (a) numbers written as words are not compared -- "three" against "tre"
      would need a bilingual numeral vocabulary, and the page carries between
      163 and 179 of them depending on the counting method;
  (b) a translation that is present but WRONG passes -- no mechanical check
      reads meaning;
  (c) recomputing a fingerprint without translating buys green. A checksum
      proves someone TOUCHED a text, never that they translated it. What the
      mechanism guarantees is that an omission becomes a deliberate,
      diff-visible act instead of a silent one, and the failure this feature
      exists to close is forgetfulness, not sabotage;
  (d) the document `<title>` carries the normative language alone. A document
      has exactly one title, so it cannot hold switchable twins;
  (e) only INTEGERS are compared. A decimal's notation depends on the language,
      and three attempts at a bilingual normaliser each fixed one shape and
      broke another -- the loop the first process rule forbids. Integers carry
      the figures that diverge in practice: counts of findings, rounds, tasks.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest
from bs4 import BeautifulSoup

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
        if el.find(True) or el.get("data-k"):
            continue
        if el.find_parent(attrs={"data-k": True}):
            continue
        if el.name in ("script", "style", "button"):
            continue
        classes = set(el.get("class") or [])
        if classes & EXEMPT_CLASSES:
            continue
        text = el.get_text(strip=True)
        if text:
            unkeyed.append(f"<{el.name} class={sorted(classes)}> {text[:60]!r}")
    assert not unkeyed, "testo visibile non chiavato e non esente:\n  " + "\n  ".join(unkeyed)


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
    assert '[data-lang="en"] { display: none; }' in css, (
        "il default italiano non e' nello stato a riposo del documento"
    )
    assert '[data-lang-sel="en"] [data-lang="it"] { display: none; }' in css, (
        "manca la regola che nasconde l'italiano quando si sceglie l'inglese"
    )


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

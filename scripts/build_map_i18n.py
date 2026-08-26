"""Tooling for the bilingual build map.

The build map carries both languages in one file (spec
`specs/20260812-143706-bilingual-build-map/spec.md`, FR-001). Every
translatable element exists twice, as twin elements sharing a stable
`data-k` key and distinguished by `data-lang`; Italian is normative and
English is the mirror (D-3).

This module is maintenance tooling, not a runtime dependency of anything.
It has two jobs:

  extract  -- dump the translatable inventory as JSON, keyed
  fingerprint -- recompute `data-fp` (normative digest, carried by the
                 mirror) and `data-fp-self` (the element's own digest)

The guard that enforces the invariants lives in
`epocha/apps/dashboard/tests/test_build_map_bilingual.py`. This file
computes; that file judges.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

from bs4 import BeautifulSoup

MAP = Path(__file__).resolve().parents[1] / "docs/build-map/epocha-build-map.html"

# Selectors of translatable containers. An element matches by class, or by
# being one of the named tags inside the page body. Technical identifiers
# (chapter refs, paths, SHAs, phase numbers, module names, branch names,
# author-year citations) are NOT keyed -- FR-003a -- and they survive inside
# the kept inner markup of each twin, identical in both languages.
TRANSLATABLE = (
    "title",
    "desc",
    "pill",
    "needs",
    "col-h",
    "block-label",
    "note",
    "warn",
    "eyebrow",
    "dek",
    "here-tag",
    "rule-k",
    "rule-v",
    "lab",
    "found-name",
    "legend-item",
    "mast-meta-label",
)
# `num` is a phase number, `tag` is overwhelmingly technical: both exempt.


def digest(text: str) -> str:
    """Twelve hex chars of SHA-256 over normalised text.

    Normalised means entities already resolved by the parser and whitespace
    flattened, so a reflow that changes only line breaks does not invalidate
    a fingerprint -- otherwise every wrap would read as a content change.
    """
    flat = " ".join(text.split())
    return hashlib.sha256(flat.encode("utf-8")).hexdigest()[:12]


def soup_of(path: Path = MAP) -> BeautifulSoup:
    return BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")


def twins(soup: BeautifulSoup):
    """(key, {lang: element}) for every keyed pair in the document."""
    pairs: dict[str, dict[str, object]] = {}
    for el in soup.select("[data-k]"):
        pairs.setdefault(el["data-k"], {})[el.get("data-lang", "?")] = el
    return pairs


def fingerprint(path: Path = MAP) -> int:
    """Rewrite every mirror's `data-fp` and every element's `data-fp-self`."""
    soup = soup_of(path)
    changed = 0
    for key, langs in twins(soup).items():
        it, en = langs.get("it"), langs.get("en")
        if it is None or en is None:
            continue
        for el in (it, en):
            own = digest(el.get_text())
            if el.get("data-fp-self") != own:
                el["data-fp-self"] = own
                changed += 1
        normative = digest(it.get_text())
        if en.get("data-fp") != normative:
            en["data-fp"] = normative
            changed += 1
    path.write_text(str(soup), encoding="utf-8")
    return changed


def extract(path: Path = MAP) -> dict:
    return {
        key: {lang: el.decode_contents() for lang, el in langs.items()}
        for key, langs in twins(soup_of(path)).items()
    }


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "extract"
    if cmd == "fingerprint":
        print(f"{fingerprint()} attributes rewritten")
    else:
        json.dump(extract(), sys.stdout, ensure_ascii=False, indent=1)

"""Tests for the demography template loader."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from epocha.apps.demography import template_loader

# Resolved once, from the module's own location: the tests below monkeypatch
# `template_loader.TEMPLATES_DIR` to a tmp_path, so reading that attribute to
# find the shipped templates would resolve to the patched directory.
_SHIPPED_TEMPLATES = Path(template_loader.__file__).parent / "templates"


def test_all_default_templates_load():
    names = template_loader.list_available_templates()
    assert "pre_industrial_christian" in names
    assert "pre_industrial_islamic" in names
    assert "industrial" in names
    assert "modern_democracy" in names
    assert "sci_fi" in names
    for name in names:
        assert template_loader.load_template(name) is not None


def test_pre_industrial_hadwiger_values():
    tpl = template_loader.load_template("pre_industrial_christian")
    hp = tpl["mortality"]["heligman_pollard"]
    assert set(hp.keys()) == set("ABCDEFGH")
    hadwiger = tpl["fertility"]["hadwiger"]
    assert 4.0 <= hadwiger["H"] <= 6.0
    assert 24 <= hadwiger["R"] <= 30


def test_missing_file_raises(tmp_path, monkeypatch):
    monkeypatch.setattr(template_loader, "TEMPLATES_DIR", tmp_path)
    with pytest.raises(FileNotFoundError):
        template_loader.load_template("does_not_exist")


def test_missing_required_key_raises(tmp_path, monkeypatch):
    monkeypatch.setattr(template_loader, "TEMPLATES_DIR", tmp_path)
    (tmp_path / "broken.json").write_text(json.dumps({"acceleration": 1.0}))
    with pytest.raises(ValueError):
        template_loader.load_template("broken")


def test_invalid_fertility_agency_raises(tmp_path, monkeypatch):
    monkeypatch.setattr(template_loader, "TEMPLATES_DIR", tmp_path)
    # Build a minimal valid shape except for fertility_agency
    minimal = _minimal_template()
    minimal["fertility_agency"] = "WRONG"
    (tmp_path / "bad_agency.json").write_text(json.dumps(minimal))
    with pytest.raises(ValueError):
        template_loader.load_template("bad_agency")


def test_names_section_is_accepted(tmp_path, monkeypatch):
    """The `names` section is part of the contract (spec FR-001a).

    A newborn's name comes from a per-era pool rather than from the LLM,
    because an LLM-generated name would make birth non-reproducible from
    the seed. The pool has to live in the template, so the loader's closed
    schema has to admit it.
    """
    monkeypatch.setattr(template_loader, "TEMPLATES_DIR", tmp_path)
    tpl = _minimal_template()
    (tmp_path / "with_names.json").write_text(json.dumps(tpl))

    loaded = template_loader.load_template("with_names")

    assert loaded["names"]["male"]
    assert loaded["names"]["female"]


def test_names_section_is_mandatory(tmp_path, monkeypatch):
    """Omitting the pool must fail at load time, not at the first birth."""
    monkeypatch.setattr(template_loader, "TEMPLATES_DIR", tmp_path)
    tpl = _minimal_template()
    del tpl["names"]
    (tmp_path / "no_names.json").write_text(json.dumps(tpl))

    with pytest.raises(ValueError):
        template_loader.load_template("no_names")


@pytest.mark.parametrize("missing", ["male", "female"])
def test_each_names_pool_is_mandatory_on_its_own(missing, tmp_path, monkeypatch):
    """Deleting the whole section is not the same as deleting one pool.

    The mandatory-section test above removes `names` entirely, so making a
    single pool optional in the schema left every one of these tests green
    while a template shipping only male names would load and then raise a
    `KeyError` at the first female birth -- which is exactly the "fail at
    load time, not at the first birth" this contract promises.
    """
    monkeypatch.setattr(template_loader, "TEMPLATES_DIR", tmp_path)
    tpl = _minimal_template()
    del tpl["names"][missing]
    (tmp_path / f"no_{missing}_names.json").write_text(json.dumps(tpl))

    with pytest.raises(ValueError):
        template_loader.load_template(f"no_{missing}_names")


def test_names_pool_must_be_a_list(tmp_path, monkeypatch):
    monkeypatch.setattr(template_loader, "TEMPLATES_DIR", tmp_path)
    tpl = _minimal_template()
    tpl["names"]["male"] = "Giovanni"
    (tmp_path / "scalar_pool.json").write_text(json.dumps(tpl))

    with pytest.raises(ValueError):
        template_loader.load_template("scalar_pool")


def test_unknown_key_beside_names_is_still_rejected(tmp_path, monkeypatch):
    """Extending the contract must not weaken the guard it extends.

    The loader rejects every unknown key at any nesting level. Adding a
    section is an extension of the contract; it must leave that rejection
    exactly as strict, inside the new section as everywhere else.
    """
    monkeypatch.setattr(template_loader, "TEMPLATES_DIR", tmp_path)
    tpl = _minimal_template()
    tpl["names"]["neuter"] = ["Robin"]
    (tmp_path / "unknown_in_names.json").write_text(json.dumps(tpl))

    with pytest.raises(ValueError):
        template_loader.load_template("unknown_in_names")

    tpl = _minimal_template()
    tpl["invented_section"] = {"anything": 1}
    (tmp_path / "unknown_top.json").write_text(json.dumps(tpl))

    with pytest.raises(ValueError):
        template_loader.load_template("unknown_top")


def _minimal_template() -> dict:
    """Return a template that the loader actually accepts.

    Reads a shipped era template from disk instead of hand-listing keys.
    The hand-written version this replaced was missing whole mandatory
    sections (`fertility.hadwiger` among them), so every test that asserted
    `pytest.raises(ValueError)` on a deliberately broken copy was passing on
    the missing sections rather than on the defect it meant to exercise --
    a criterion that could not fail. Building the fixture from a real
    template keeps the negative tests honest and keeps the scientific values
    in one place.
    """
    source = _SHIPPED_TEMPLATES / "pre_industrial_christian.json"
    return json.loads(source.read_text())

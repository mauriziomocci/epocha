"""Tests for the demography template loader."""
from __future__ import annotations

import json

import pytest

from epocha.apps.demography import template_loader


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


def _minimal_template() -> dict:
    return {
        "acceleration": 1.0,
        "max_population": 10,
        "fertility_agency": "biological",
        "mortality": {
            "heligman_pollard": {k: 0.01 for k in "ABCDEFGH"},
            "maternal_mortality_rate_per_birth": 0.01,
            "neonatal_survival_when_mother_dies": 0.3,
        },
        "fertility": {},
        "age_pyramid": [],
        "sex_ratio_at_birth": 1.05,
        "couple": {},
        "trait_inheritance": {},
        "social_inheritance": {},
        "economic_inheritance": {},
        "migration": {},
    }

"""Era template loading and validation for the demography subsystem.

Templates are JSON fixtures stored in epocha/apps/demography/templates/.
Each template declares the parameters for a single era/scenario. The
loader validates the schema at load time and raises on missing or
malformed fields. Real calibration of numerical parameters (HP, Hadwiger)
happens in Plan 4 against historical life tables.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

TEMPLATES_DIR = Path(__file__).parent / "templates"

REQUIRED_TOP_LEVEL_KEYS = {
    "acceleration",
    "max_population",
    "fertility_agency",
    "mortality",
    "fertility",
    "age_pyramid",
    "sex_ratio_at_birth",
    "couple",
    "trait_inheritance",
    "social_inheritance",
    "economic_inheritance",
    "migration",
}

REQUIRED_MORTALITY_KEYS = {
    "heligman_pollard",
    "maternal_mortality_rate_per_birth",
    "neonatal_survival_when_mother_dies",
}

REQUIRED_HP_KEYS = set("ABCDEFGH")

ALLOWED_FERTILITY_AGENCY = {"biological", "planned"}


def load_template(name: str) -> dict[str, Any]:
    """Load a demography template by name and validate it.

    Args:
        name: the template file name without the .json extension.

    Raises:
        FileNotFoundError: template file does not exist.
        ValueError: template is missing required fields.
    """
    path = TEMPLATES_DIR / f"{name}.json"
    if not path.exists():
        raise FileNotFoundError(f"Demography template not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    _validate_template(data, source=str(path))
    return data


def _validate_template(data: dict[str, Any], source: str) -> None:
    missing = REQUIRED_TOP_LEVEL_KEYS - data.keys()
    if missing:
        raise ValueError(f"Template {source} missing keys: {sorted(missing)}")

    mortality = data["mortality"]
    missing_mort = REQUIRED_MORTALITY_KEYS - mortality.keys()
    if missing_mort:
        raise ValueError(
            f"Template {source} mortality missing keys: {sorted(missing_mort)}"
        )
    hp = mortality["heligman_pollard"]
    missing_hp = REQUIRED_HP_KEYS - hp.keys()
    if missing_hp:
        raise ValueError(
            f"Template {source} heligman_pollard missing parameters: {sorted(missing_hp)}"
        )

    if data["fertility_agency"] not in ALLOWED_FERTILITY_AGENCY:
        raise ValueError(
            f"Template {source} fertility_agency must be one of "
            f"{sorted(ALLOWED_FERTILITY_AGENCY)}"
        )


def list_available_templates() -> list[str]:
    """Return the list of template names available on disk."""
    return sorted(p.stem for p in TEMPLATES_DIR.glob("*.json"))

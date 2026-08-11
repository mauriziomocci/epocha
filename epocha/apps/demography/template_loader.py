"""Era template loading and validation for the demography subsystem.

Templates are JSON fixtures stored in epocha/apps/demography/templates/.
Each template declares the parameters for a single era/scenario.

VALIDATION CONTRACT (design-spec amendment A9, 2026-08-07). Whitepaper
section 6.2 published, before that amendment, that "the JSON schema is
deliberately narrow: every key is consumed by a specific model, no
untyped extension field is accepted, and an unknown key at load time
raises a validation error rather than being silently ignored". That was
false: running the validator against a template carrying an invented
top-level key, an `era_noize` section with a typo, an `estate_tax_rate`
of 40, a heritability of 5.0 and a negative regression coefficient
accepted all five at once. A9 is the contract that makes the published
claim true, and its six clauses are implemented here:

1. every unknown key, at any nesting level;
2. every out-of-range value: rates and heritabilities in [0, 1],
   regression coefficients in [0, 1], amplitudes strictly positive;
3. every missing mandatory nested section, `trait_inheritance.era_noise`
   and `social_inheritance.era_noise` above all -- it is the identity of
   the section that discriminates, not its depth, since several nested
   absences were already rejected before the amendment;
4. every missing entry: each key of `trait_inheritance.heritability` must
   have its own entry in `trait_inheritance.era_noise`, and the social
   section must declare the education moments and the rank dispersion. A
   section present but empty is rejected naming what is absent;
5. every declared `(era_mean, era_sd)` pair outside the admissible region
   of A1, computed by the deterministic fixed point in `truncated_moments`;
   the class-rank target dispersion is exempt and carries its own bound;
6. every cross-section inconsistency between `heritability` and
   `trait_inheritance.era_noise`, in that pair of sections only.

Every rejection names the field, its full path, and where applicable the
admitted interval: an error that says only that something is wrong sends
the author hunting through a two-hundred-line file, which is how a typo
survives in the first place.

Real calibration of the numerical parameters (Heligman-Pollard, Hadwiger)
against historical life tables remains Plan 4's work; this module checks
shape and admissibility, not realism.
"""

from __future__ import annotations

import json
import logging
from collections import defaultdict
from pathlib import Path
from typing import Any

from epocha.apps.demography.truncated_moments import (
    AdmissibleRegionResult,
    FixedPointNotConvergedError,
    check_admissible_region,
    check_rank_dispersion,
)

logger = logging.getLogger(__name__)

TEMPLATES_DIR = Path(__file__).parent / "templates"

# --- schema vocabulary -------------------------------------------------------
#
# A leaf is (python_type, interval_or_None). `UNIT` is the closed [0, 1] that
# A9 names for rates, heritabilities and regression coefficients; `POSITIVE`
# is the open (0, inf) it names for amplitudes.

UNIT = (0.0, 1.0)
POSITIVE = (0.0, None)

_NUMBER = (float, int)


class _Mapping:
    """A section whose keys are data, not schema -- one entry per character."""

    def __init__(self, value_schema: Any) -> None:
        self.value_schema = value_schema


class _Optional:
    """A key the schema permits but does not require."""

    def __init__(self, schema: Any) -> None:
        self.schema = schema


_MOMENTS = {
    "era_mean": (_NUMBER, None),  # range is checked by the admissible region
    "era_sd": (_NUMBER, POSITIVE),
}

SCHEMA: dict[str, Any] = {
    "acceleration": (_NUMBER, POSITIVE),
    "max_population": (int, None),
    "fertility_agency": (str, None),
    "mortality": {
        "heligman_pollard": {letter: (_NUMBER, None) for letter in "ABCDEFGH"},
        "maternal_mortality_rate_per_birth": (_NUMBER, UNIT),
        "neonatal_survival_when_mother_dies": (_NUMBER, UNIT),
    },
    "fertility": {
        "hadwiger": {"H": (_NUMBER, None), "R": (_NUMBER, None), "T": (_NUMBER, None)},
        "becker_coefficients": {f"beta_{i}": (_NUMBER, None) for i in range(5)},
        "require_couple_for_birth": (bool, None),
        "malthusian_floor_ratio": (_NUMBER, UNIT),
    },
    "age_pyramid": (list, None),
    "sex_ratio_at_birth": (_NUMBER, POSITIVE),
    "sexual_orientation_distribution": {
        "heterosexual": (_NUMBER, UNIT),
        "bisexual": (_NUMBER, UNIT),
        "homosexual": (_NUMBER, UNIT),
    },
    "couple": {
        "min_marriage_age_male": (int, None),
        "min_marriage_age_female": (int, None),
        "allowed_types": (list, None),
        "default_type": (str, None),
        "divorce_enabled": (bool, None),
        "marriage_market_type": (str, None),
        "marriage_market_radius": (str, None),
        "implicit_mutual_consent": (bool, None),
        "mourning_ticks": (int, None),
        "homogamy_weights": {
            "w_class": (_NUMBER, UNIT),
            "w_edu": (_NUMBER, UNIT),
            "w_age": (_NUMBER, UNIT),
            "w_relationship": (_NUMBER, UNIT),
        },
    },
    "trait_inheritance": {
        "heritability": _Mapping((_NUMBER, UNIT)),
        "era_noise": _Mapping(_MOMENTS),
        "derived_trait_formulas": _Mapping(
            {
                "description": (str, None),
                "formula": (str, None),
                "range": (list, None),
            }
        ),
    },
    "social_inheritance": {
        "class_rule": (str, None),
        "education_regression_rho": (_NUMBER, UNIT),
        "era_noise": {
            "education": _MOMENTS,
            "class_rank": {"target_dispersion": (_NUMBER, POSITIVE)},
        },
    },
    "economic_inheritance": {
        "rule": (str, None),
        "heir_priority": (list, None),
        "estate_tax_rate": (_NUMBER, UNIT),
    },
    "migration": {
        "flight_trigger_ticks": (int, None),
        "adulthood_age": (int, None),
    },
    # Free-text annotation two templates carry. Permitted and never consumed;
    # rejecting it would have made the contract fail against what ships.
    "_note": _Optional((str, None)),
}

ALLOWED_FERTILITY_AGENCY = {"biological", "planned"}


def load_template(name: str) -> dict[str, Any]:
    """Load a demography template by name and validate it against A9.

    Args:
        name: the template file name without the .json extension.

    Raises:
        FileNotFoundError: template file does not exist.
        ValueError: the template violates any clause of the A9 contract.
    """
    path = TEMPLATES_DIR / f"{name}.json"
    if not path.exists():
        raise FileNotFoundError(f"Demography template not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    validate_template(data, source=str(path))
    return data


def _fail(source: str, message: str) -> None:
    raise ValueError(f"Template {source}: {message}")


def _interval_text(interval: tuple[float, float | None]) -> str:
    low, high = interval
    return f"[{low:g}, {high:g}]" if high is not None else f"greater than {low:g}"


def _check_leaf(value: Any, spec: tuple, path: str, source: str) -> None:
    expected_type, interval = spec
    if isinstance(expected_type, tuple):
        # bool is a subclass of int; a flag where a number belongs is a defect
        if isinstance(value, bool) or not isinstance(value, expected_type):
            _fail(source, f"{path} must be numeric, found {type(value).__name__}")
    elif not isinstance(value, expected_type):
        _fail(
            source,
            f"{path} must be of type {expected_type.__name__}, found {type(value).__name__}",
        )
    if interval is None:
        return
    low, high = interval
    if high is None:
        if not value > low:
            _fail(
                source,
                f"{path} = {value} out of range: must be {_interval_text(interval)}",
            )
    elif not low <= value <= high:
        _fail(source, f"{path} = {value} outside the admitted range {_interval_text(interval)}")


def _walk(data: Any, schema: Any, path: str, source: str) -> None:
    """Clauses 1, 2, 3 and the entry half of 4, recursively."""
    if isinstance(schema, _Mapping):
        if not isinstance(data, dict):
            _fail(source, f"{path} must be a section")
        # No emptiness check here. For `era_noise` and `heritability` clauses 4
        # and 6 already reject an empty section, naming the characters that are
        # missing -- a generic guard would be dead code before them. And for
        # `derived_trait_formulas` emptiness is legitimate: A9 requires an entry
        # per transmitted character, and a derived trait is not one.
        for key, value in data.items():
            _walk(value, schema.value_schema, f"{path}.{key}", source)
        return

    if isinstance(schema, dict):
        if not isinstance(data, dict):
            _fail(source, f"{path} must be a section")
        allowed = set(schema)
        unknown = sorted(set(data) - allowed)
        if unknown:
            where = path or "top level"
            _fail(source, f"unknown key in {where}: {', '.join(unknown)}")
        for key, sub in schema.items():
            sub_path = f"{path}.{key}" if path else key
            if isinstance(sub, _Optional):
                if key in data:
                    _walk(data[key], sub.schema, sub_path, source)
                continue
            if key not in data:
                _fail(source, f"mandatory section or field missing: {sub_path}")
            _walk(data[key], sub, sub_path, source)
        return

    _check_leaf(data, schema, path, source)


def _check_transmitted_characters(data: dict[str, Any], source: str) -> None:
    """Clauses 4 and 6, on the pair of sections A9 names and no other."""
    trait = data["trait_inheritance"]
    declared = set(trait["heritability"])
    with_noise = set(trait["era_noise"])

    # Both empty is the one arrangement the symmetric difference cannot see:
    # it is zero, and the admissible-region pass then iterates nothing, so a
    # template declaring no transmitted character at all would be accepted
    # whole. A model that transmits nothing is not a valid era.
    if not declared and not with_noise:
        _fail(
            source,
            "trait_inheritance declares no transmitted character: both "
            "heritability and era_noise are empty",
        )

    if "default" in declared:
        _fail(
            source,
            "trait_inheritance.heritability.default has been removed from the "
            "schema: every declared trait carries its own coefficient",
        )
    missing_noise = sorted(declared - with_noise)
    if missing_noise:
        _fail(
            source,
            "trait_inheritance.era_noise does not declare the characters "
            f"{', '.join(missing_noise)}, which are present in heritability",
        )
    orphan_noise = sorted(with_noise - declared)
    if orphan_noise:
        _fail(
            source,
            "trait_inheritance.era_noise declares the characters "
            f"{', '.join(orphan_noise)}, which are absent from heritability",
        )


def _admissible_or_fail(
    era_mean: float,
    era_sd: float,
    coefficients: tuple[float, ...],
    label: str,
    source: str,
) -> AdmissibleRegionResult:
    """Run A1's check, converting both failure modes into the documented one.

    `load_template` promises `ValueError` for any A9 violation. The fixed
    point can also fail to settle, which raises `FixedPointNotConvergedError`
    -- a RuntimeError naming neither the template nor the field. A1 requires
    the load to fail naming the pair, so it is translated here.
    """
    try:
        result = check_admissible_region(era_mean, era_sd, coefficients)
    except FixedPointNotConvergedError as exc:
        _fail(source, f"{label}: admissible-region fixed point did not settle ({exc})")
        raise  # unreachable; _fail always raises
    if not result.accepted:
        _fail(source, f"{label}: {result.reason}")
    return result


def _report(label: str, era_mean: float, era_sd: float, result: AdmissibleRegionResult) -> None:
    """A1 requires the boundary mass to be reported at load, naming its branch.

    It is an observable, not a gate: no source fixes how much boundary mass a
    bounded phenotypic character may tolerate, so A1 declines to invent a
    ceiling and lets the amplitude check bound it instead. Reporting it keeps
    the quantity visible to whoever calibrates a future era.
    """
    logger.info(
        "demography template %s at (era_mean=%.4f, era_sd=%.4f): realized amplitude "
        "%.2f%% of declared on the worst branch, boundary mass %.2f%% on the %s branch",
        label,
        era_mean,
        era_sd,
        result.realized_ratio * 100.0,
        result.boundary_mass * 100.0,
        result.boundary_mass_branch,
    )


def _check_admissible_pairs(data: dict[str, Any], source: str) -> None:
    """Clause 5: A1's admissible region per declared pair, plus the rank bound.

    Pairs are grouped so the fixed point runs once per distinct
    `(era_mean, era_sd)` rather than once per character, and each group is
    evaluated at the largest coefficient it carries -- the least favourable.
    """
    trait = data["trait_inheritance"]
    groups: dict[tuple[float, float], list[str]] = defaultdict(list)
    for name, moments in trait["era_noise"].items():
        groups[(moments["era_mean"], moments["era_sd"])].append(name)

    for (era_mean, era_sd), names in groups.items():
        coefficients = tuple(trait["heritability"][name] for name in names)
        label = f"trait_inheritance.era_noise ({', '.join(sorted(names))})"
        result = _admissible_or_fail(era_mean, era_sd, coefficients, label, source)
        _report(label, era_mean, era_sd, result)

    social = data["social_inheritance"]
    education = social["era_noise"]["education"]
    label = "social_inheritance.era_noise.education"
    result = _admissible_or_fail(
        education["era_mean"],
        education["era_sd"],
        (social["education_regression_rho"],),
        label,
        source,
    )
    _report(label, education["era_mean"], education["era_sd"], result)

    rank = check_rank_dispersion(social["era_noise"]["class_rank"]["target_dispersion"])
    if not rank.accepted:
        _fail(
            source,
            f"social_inheritance.era_noise.class_rank.target_dispersion: {rank.reason}",
        )


def validate_template(data: dict[str, Any], source: str) -> None:
    """Apply the six clauses of the A9 contract. Raises ValueError on any."""
    if not isinstance(data, dict):
        _fail(source, "the document is not a JSON object")
    _walk(data, SCHEMA, "", source)

    if data["fertility_agency"] not in ALLOWED_FERTILITY_AGENCY:
        _fail(
            source,
            f"fertility_agency = {data['fertility_agency']!r} not admitted: "
            f"must be one of {sorted(ALLOWED_FERTILITY_AGENCY)}",
        )

    _check_transmitted_characters(data, source)
    _check_admissible_pairs(data, source)


def list_available_templates() -> list[str]:
    """Return the list of template names available on disk."""
    return sorted(p.stem for p in TEMPLATES_DIR.glob("*.json"))

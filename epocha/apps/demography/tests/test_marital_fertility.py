"""Tests for the marital fertility schedule of the eras that require a couple.

The schedule is the Coale and Trussell (1974) model of marital fertility with
no fertility control (m = 0): r(a) = M * n(a), where n(a) is the natural
fertility schedule they derived from the populations Henry (1961) defined as
natural, and M the level relative to it. The six five-year values of n(a) and
the 9 children per woman they imply between 20 and 49 were read on the IUSSP
Population Analysis for Planners page (PAPP103, session 3, "The
Coale-Trussell model"); the primary source was not read.

These tests prove the shape (piecewise constant on the published groups,
non-increasing from 25, zero outside [15, 50)) and the level
(M = T_m / 8.995, with 8.995 computed from the six values, never written by
hand), and the single dispatch point (N4) that chooses the base schedule
from the block a `fertility` section carries. All tests are pure: no database, no Django models.
"""

import pytest

from epocha.apps.demography.fertility import (
    HENRY_NATURAL_FERTILITY,
    HENRY_TMFR_20_49,
    FertilityScheduleError,
    annual_base_rate,
    hadwiger_asfr,
    marital_fertility_rate,
    requires_couple_for_birth,
)

# The English level of the spec, the marital TMFR 20-49 that the Christian
# template declares (spec, table "Parametri per era").
MARITAL_BLOCK = {"total_marital_fertility_20_49": 6.7}

# The six published values of n(a), one per group 20-24 ... 45-49, restated
# here so that a change of the production tuple is caught by the tests below.
PUBLISHED_GROUP_VALUES = (
    (22.0, 0.460),
    (27.0, 0.431),
    (32.0, 0.395),
    (37.0, 0.322),
    (42.0, 0.167),
    (47.0, 0.024),
)
# (N1a) recomputed from the restated values, independent of the production
# constant: a test comparing the level with `HENRY_TMFR_20_49` itself would
# stay green if that constant were replaced by a rounded literal.
TMFR_OF_THE_PUBLISHED_VALUES = 5 * sum(value for _, value in PUBLISHED_GROUP_VALUES)


def test_henry_tmfr_is_five_times_the_six_groups_20_49():
    assert pytest.approx(8.995, abs=1e-12) == HENRY_TMFR_20_49
    assert HENRY_TMFR_20_49 == 5 * sum(value for _, value in HENRY_NATURAL_FERTILITY)


@pytest.mark.parametrize(("age", "natural_value"), PUBLISHED_GROUP_VALUES)
def test_rate_at_an_inner_age_of_each_group(age, natural_value):
    expected = (6.7 / 8.995) * natural_value
    assert marital_fertility_rate(age, MARITAL_BLOCK) == pytest.approx(expected, abs=1e-12)


@pytest.mark.parametrize("age", [15.0, 17.5, 19.999])
def test_ages_15_to_20_take_the_20_24_value(age):
    assert marital_fertility_rate(age, MARITAL_BLOCK) == marital_fertility_rate(22.0, MARITAL_BLOCK)


@pytest.mark.parametrize("age", [14.99, 14.999, 50.0, 60.0, 0.0, -1.0])
def test_rate_is_zero_outside_15_to_50(age):
    assert marital_fertility_rate(age, MARITAL_BLOCK) == 0.0


def test_rate_is_non_increasing_from_25_to_50():
    ages = [25.0 + step / 100.0 for step in range(2500)]  # 25.00 ... 49.99
    rates = [marital_fertility_rate(age, MARITAL_BLOCK) for age in ages]
    for younger, older in zip(rates, rates[1:], strict=False):
        assert older <= younger


def test_level_is_t_m_over_henry_tmfr():
    level = marital_fertility_rate(22.0, MARITAL_BLOCK) / 0.460
    assert level == pytest.approx(6.7 / TMFR_OF_THE_PUBLISHED_VALUES, abs=1e-6)

    industrial_level = marital_fertility_rate(22.0, {"total_marital_fertility_20_49": 6.22}) / 0.460
    assert industrial_level == pytest.approx(0.69150, abs=1e-5)


# --- One dispatch point (FR-002, US3 scenario 4, plan PD-02 and PD-03) ---

BECKER_ZERO = {f"beta_{i}": 0.0 for i in range(5)}
HADWIGER_BLOCK = {"H": 1.8, "R": 30, "T": 4.2}
MARITAL_SECTION = {"marital": MARITAL_BLOCK, "becker_coefficients": BECKER_ZERO}
HADWIGER_SECTION = {"hadwiger": HADWIGER_BLOCK, "becker_coefficients": BECKER_ZERO}
BOTH_BLOCKS = {"marital": MARITAL_BLOCK, "hadwiger": HADWIGER_BLOCK}
NO_BLOCK = {"becker_coefficients": BECKER_ZERO}
# The message must name both paths, so a template author sees which block to
# add or remove (FR-003).
BOTH_PATHS_NAMED = r"fertility\.marital.*fertility\.hadwiger"


def test_requires_couple_iff_marital_block():
    assert requires_couple_for_birth(MARITAL_SECTION) is True
    assert requires_couple_for_birth(HADWIGER_SECTION) is False


def test_annual_base_rate_uses_the_marital_rate_with_the_marital_block():
    assert annual_base_rate(25.0, MARITAL_SECTION) == marital_fertility_rate(25.0, MARITAL_BLOCK)


def test_annual_base_rate_uses_hadwiger_with_the_hadwiger_block():
    assert annual_base_rate(25.0, HADWIGER_SECTION) == hadwiger_asfr(25.0, HADWIGER_BLOCK)


_DISPATCHERS = [
    pytest.param(lambda cfg: annual_base_rate(25.0, cfg), id="annual_base_rate"),
    pytest.param(requires_couple_for_birth, id="requires_couple_for_birth"),
]


@pytest.mark.parametrize("dispatch", _DISPATCHERS)
def test_both_blocks_raise(dispatch):
    with pytest.raises(FertilityScheduleError, match=BOTH_PATHS_NAMED):
        dispatch(BOTH_BLOCKS)


@pytest.mark.parametrize("dispatch", _DISPATCHERS)
def test_no_block_raises(dispatch):
    with pytest.raises(FertilityScheduleError, match=BOTH_PATHS_NAMED):
        dispatch(NO_BLOCK)


def test_schedule_error_is_a_value_error():
    assert issubclass(FertilityScheduleError, ValueError)

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
One test also ties the configuration-A reference of the SC-005 measurement
script (`scripts/measure_nuptiality_fertility.py`) to the SC-002 propagation
of this file.
"""

import pytest
from scipy.integrate import quad

from epocha.apps.demography.fertility import (
    HENRY_NATURAL_FERTILITY,
    HENRY_TMFR_20_49,
    FertilityScheduleError,
    annual_base_rate,
    hadwiger_asfr,
    marital_fertility_rate,
    requires_couple_for_birth,
)
from epocha.apps.demography.nuptiality import first_marriage_schedule
from epocha.apps.demography.template_loader import load_template
from scripts.measure_nuptiality_fertility import (
    TEMPLATE_NAME,
    build_context,
    propagated_reference_tfr,
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


# (lower edge of a group, n of that group, n just below the edge): each group
# is closed on the left, [a, a + 5). Below 20 the 20-24 value extends to 15.
GROUP_LOWER_EDGES = [
    (20.0, 0.460, 0.460),
    (25.0, 0.431, 0.460),
    (30.0, 0.395, 0.431),
    (35.0, 0.322, 0.395),
    (40.0, 0.167, 0.322),
    (45.0, 0.024, 0.167),
]


@pytest.mark.parametrize(("edge", "value_at_edge", "value_below"), GROUP_LOWER_EDGES)
def test_each_group_starts_at_its_lower_edge(edge, value_at_edge, value_below):
    level = 6.7 / TMFR_OF_THE_PUBLISHED_VALUES
    assert marital_fertility_rate(edge, MARITAL_BLOCK) == pytest.approx(
        level * value_at_edge, abs=1e-12
    )
    assert marital_fertility_rate(edge - 0.001, MARITAL_BLOCK) == pytest.approx(
        level * value_below, abs=1e-12
    )


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


# --- The shipped templates give a possible marital rate (SC-003) ---

# Spec, table "Parametri per era": T_m and the rate at 20, 30 and 40 of each
# era that requires a couple.
SHIPPED_COUPLE_ERAS = [
    pytest.param("pre_industrial_christian", 6.7, (0.343, 0.294, 0.124), id="christian"),
    pytest.param("pre_industrial_islamic", 6.7, (0.343, 0.294, 0.124), id="islamic"),
    pytest.param("industrial", 6.22, (0.318, 0.273, 0.115), id="industrial"),
]


@pytest.mark.parametrize(("name", "t_m", "rates_at_20_30_40"), SHIPPED_COUPLE_ERAS)
def test_shipped_couple_templates_give_a_possible_marital_rate(name, t_m, rates_at_20_30_40):
    """Through the loader and the shipped files, not a hand-built section: a
    template carrying another level, or a dispatcher choosing the wrong
    schedule, fails here. Under (4.2) the Christian era gave 0.241 at 20 and
    0.398 on the grid, above the marital maximum (spec SC-003)."""
    cfg = load_template(name)["fertility"]
    grid = [12.0 + step / 100.0 for step in range(3801)]  # 12.00 ... 50.00
    highest = max(annual_base_rate(age, cfg) for age in grid)

    assert highest == pytest.approx((t_m / 8.995) * 0.460, abs=1e-12)
    assert highest < 1.0
    for age, expected in zip((20.0, 30.0, 40.0), rates_at_20_30_40, strict=True):
        assert annual_base_rate(age, cfg) == pytest.approx(expected, abs=1e-3)
    assert requires_couple_for_birth(cfg) is True


# --- The era TFR is born of nuptiality and marital fertility (SC-002) ---

MONTHLY_DT = 1.0 / 12.0
COHORT_START_AGE = 12.0
COHORT_TICKS = 456  # 12 to 50 at monthly ticks
SC002_TOLERANCE = 0.002
# Group boundaries of n(a): quad is told where the integrand jumps.
MARITAL_GROUP_EDGES = [15.0, 20.0, 25.0, 30.0, 35.0, 40.0, 45.0]
# The Christian Hadwiger parameters before this work item (template
# `pre_industrial_christian.json` on the couples head 2282ed8), kept only as
# the SC-002 mutation sentinel: no shipped template carries them any more.
CHRISTIAN_HADWIGER_BEFORE = {"H": 5.0, "R": 26, "T": 3.5}


def _monthly_cohort_tfr(base_rate, schedule):
    """Deterministic TFR of a cohort without mortality, monthly ticks 12 to 50.

    The engine's step order (`orchestrator.DEMOGRAPHY_STEPS`): couple
    formation runs before fertility in the same tick, so the never-married
    share is reduced first and the births of the tick count the share married
    after the market; both read the age at the start of the tick,
    a = 12 + t * dt. Both choices are part of the test: fertility before the
    market, one tick late, gives 4.283, and the marriage hazard at mid-tick
    gives 4.318, both outside the SC-002 tolerance of 4.306.
    """
    never_married = 1.0
    tfr = 0.0
    for tick in range(COHORT_TICKS):
        age = COHORT_START_AGE + tick * MONTHLY_DT
        never_married -= never_married * schedule.tick_probability(age, MONTHLY_DT)
        tfr += base_rate(age) * (1.0 - never_married) * MONTHLY_DT
    return tfr


@pytest.fixture
def christian_era():
    template = load_template("pre_industrial_christian")
    return template["fertility"], first_marriage_schedule(template["couple"])


def test_monthly_cohort_tfr_without_mortality(christian_era):
    fertility_cfg, schedule = christian_era
    tfr = _monthly_cohort_tfr(lambda age: annual_base_rate(age, fertility_cfg), schedule)
    assert tfr == pytest.approx(4.306, abs=SC002_TOLERANCE)


def test_the_measurement_script_reference_is_the_sc002_propagation(christian_era):
    """The configuration-A reference of the SC-005 script and the SC-002
    propagation of this file are one quantity computed twice; this ties them,
    so neither can drift from the engine's step order alone."""
    fertility_cfg, schedule = christian_era
    expected = _monthly_cohort_tfr(lambda age: annual_base_rate(age, fertility_cfg), schedule)
    reference = propagated_reference_tfr(build_context(load_template(TEMPLATE_NAME)))
    assert reference == pytest.approx(expected, abs=SC002_TOLERANCE)
    assert reference == pytest.approx(4.306, abs=SC002_TOLERANCE)


def test_continuous_tfr_without_mortality(christian_era):
    """(N3): TFR0 = M * integral of n(a) * F*(a) over [m, 50]."""
    fertility_cfg, schedule = christian_era
    tfr, _ = quad(
        lambda age: annual_base_rate(age, fertility_cfg) * schedule.conditional_cdf(age),
        schedule.min_age,
        50.0,
        points=MARITAL_GROUP_EDGES,
    )
    assert tfr == pytest.approx(4.306, abs=SC002_TOLERANCE)


def test_the_hadwiger_schedule_misses_sc002(christian_era):
    """Permanent mutation sentinel of SC-002: (4.2) in the same propagation
    gives 2.384, the couples SC-007 reference without mortality after
    D-05-E-12, not the 4.306 of the marital schedule."""
    _, schedule = christian_era
    tfr = _monthly_cohort_tfr(lambda age: hadwiger_asfr(age, CHRISTIAN_HADWIGER_BEFORE), schedule)
    assert tfr == pytest.approx(2.384, abs=SC002_TOLERANCE)
    assert abs(tfr - 4.306) > SC002_TOLERANCE

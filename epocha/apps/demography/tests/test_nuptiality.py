"""Tests for the first-marriage schedule (Coale-McNeil, Kaneko form).

All tests are pure: no database, no Django models.
"""

import math
import random

import pytest
from scipy.integrate import quad

from epocha.apps.demography import nuptiality
from epocha.apps.demography.nuptiality import (
    FirstMarriageSchedule,
    _standard_lower,
    first_marriage_schedule,
    location_from_observed_mean,
    standard_cdf,
    standard_density,
    truncated_mean,
)

# Integration window for the standardized density: the left tail is below
# 1e-12 at z = -6 and the right tail below 1e-9 at z = 20, so the window
# holds the whole mass to far better than the tolerances asserted below.
_LOW, _HIGH = -6.0, 20.0


class TestStandardDensity:
    def test_the_density_integrates_to_one(self):
        total, _ = quad(standard_density, _LOW, _HIGH)
        assert total == pytest.approx(1.0, abs=1e-4)

    def test_the_density_has_mean_zero(self):
        mean, _ = quad(lambda z: z * standard_density(z), _LOW, _HIGH)
        assert mean == pytest.approx(0.0, abs=1e-3)

    def test_the_density_has_variance_one(self):
        variance, _ = quad(lambda z: z * z * standard_density(z), _LOW, _HIGH)
        assert variance == pytest.approx(1.0, abs=2e-3)

    def test_the_normalizing_constant_matches_the_published_value(self):
        constant = nuptiality.STANDARD_BETA / math.gamma(
            nuptiality.STANDARD_ALPHA / nuptiality.STANDARD_BETA
        )
        assert constant == pytest.approx(1.2813, abs=1e-3)

    def test_far_left_of_the_support_the_density_is_zero_without_overflow(self):
        assert standard_density(-50.0) == 0.0


class TestStandardCdf:
    # 20 points evenly spaced on [-3, 6], the range where the schedule has mass.
    _POINTS = [-3.0 + 9.0 * i / 19 for i in range(20)]

    def test_the_closed_form_matches_the_numerical_integral_of_the_density(self):
        for z in self._POINTS:
            numerical, _ = quad(standard_density, _LOW, z)
            assert standard_cdf(z) == pytest.approx(numerical, abs=1e-5)

    def test_the_upper_and_lower_incomplete_gamma_sum_to_one(self):
        for z in self._POINTS:
            assert standard_cdf(z) + _standard_lower(z) == pytest.approx(1.0, abs=1e-12)

    def test_far_left_of_the_support_the_cdf_is_zero_and_the_lower_part_one(self):
        assert standard_cdf(-50.0) == 0.0
        assert _standard_lower(-50.0) == 1.0


class TestFirstMarriageSchedule:
    # Christian values of the spec: location u, scale b, proportion C, minimum age m.
    schedule = FirstMarriageSchedule(25.5, 5.5, 0.88, 14)

    def test_the_density_integrates_to_the_proportion_ever_married(self):
        total, _ = quad(self.schedule.density, 0, 80)
        assert total == pytest.approx(0.88, abs=1e-4)

    def test_the_cdf_reaches_the_proportion_ever_married(self):
        # The right tail of the shape decays as exp(-alpha z): the mass beyond
        # age 80 is 4.63e-6 (C times 5.26e-6, integrated independently with
        # quad), so a tolerance tighter than 1e-5 cannot hold for any correct CDF.
        assert self.schedule.cdf(80) == pytest.approx(0.88, abs=1e-5)

    def test_almost_no_mass_lies_below_the_minimum_age(self):
        assert self.schedule.cdf(14) < 1e-5

    def test_the_hazard_is_the_density_over_the_survival(self):
        density = self.schedule.density(25)
        survival = 1 - self.schedule.cdf(25)
        assert self.schedule.hazard(25) == pytest.approx(density / survival, abs=1e-9)

    def test_the_hazard_tends_to_alpha_over_scale_in_the_far_right_tail(self):
        # With C = 1 both the density and the survival vanish, but their
        # ratio does not: the tail decays as exp(-alpha z), so h -> alpha / b.
        # The lower-incomplete-gamma survival keeps it finite at age 200.
        everyone_marries = FirstMarriageSchedule(25.5, 5.5, 1.0, 14)
        assert everyone_marries.hazard(200.0) == pytest.approx(
            nuptiality.STANDARD_ALPHA / 5.5, abs=1e-6
        )

    def test_the_hazard_is_zero_without_a_zero_division_when_the_survival_underflows(self):
        # At age 5000 exp(-beta (z - mu)) underflows to 0, so the survival of
        # an everyone-marries schedule is exactly 0.0 (FR-002).
        everyone_marries = FirstMarriageSchedule(25.5, 5.5, 1.0, 14)
        assert everyone_marries.hazard(5000.0) == 0.0


class TestConditioningOnTheMinimumAge:
    christian = FirstMarriageSchedule(25.580, 5.5, 0.88, 14)
    islamic = FirstMarriageSchedule(18.639, 4.0, 0.97, 14)

    def test_the_conditional_cdf_at_50_is_the_christian_realized_share(self):
        assert self.christian.conditional_cdf(50) == pytest.approx(0.8776, abs=1e-3)

    def test_the_conditional_cdf_is_zero_below_the_minimum_age(self):
        assert self.christian.conditional_cdf(13.9) == 0.0

    def test_no_marriage_is_drawn_below_the_minimum_age(self):
        assert self.christian.tick_probability(13.9, 168 / 8760) == 0.0

    def test_the_conditional_cdf_reaches_the_islamic_realized_share(self):
        # C* = (C - F(m)) / (1 - F(m)) of the spec: 0.968 where F(14) is 0.062.
        assert self.islamic.conditional_cdf(80) == pytest.approx(0.968, abs=1e-3)

    def test_the_tick_probability_is_one_minus_exp_of_the_hazard(self):
        dt = 168 / 8760
        expected = 1 - math.exp(-self.christian.hazard(25) * dt)
        assert self.christian.tick_probability(25, dt) == pytest.approx(expected, abs=1e-12)


class TestTruncatedMean:
    def test_the_observed_window_mean_is_below_the_location(self):
        # With u = 25.5 the mean of the schedule on [14, 50] is 25.42, not 25.5
        # (spec, section "Dal valore storico a u"): the left tail cut at 14
        # weighs more than the right tail cut at 50.
        assert truncated_mean(25.5, 5.5, 14) == pytest.approx(25.421, abs=1e-3)


class TestLocationFromObservedMean:
    @pytest.mark.parametrize(
        ("observed_mean", "scale", "min_age", "expected_location"),
        [
            (25.5, 5.5, 14, 25.580),  # pre_industrial_christian
            (19.0, 4.0, 14, 18.639),  # pre_industrial_islamic
            (25.5, 5.5, 16, 25.571),  # industrial
            (28.0, 6.0, 18, 28.172),  # modern_democracy and sci_fi
        ],
    )
    def test_the_location_matches_the_values_computed_for_the_eras(
        self, observed_mean, scale, min_age, expected_location
    ):
        location = location_from_observed_mean(observed_mean, scale, min_age)
        assert location == pytest.approx(expected_location, abs=1e-3)

    def test_the_location_reproduces_the_observed_mean(self):
        location = location_from_observed_mean(25.5, 5.5, 14)
        assert truncated_mean(location, 5.5, 14) == pytest.approx(25.5, abs=1e-5)

    def test_an_unreachable_mean_is_rejected_with_the_reachable_interval(self):
        with pytest.raises(ValueError, match=r"18\.78"):
            location_from_observed_mean(18.5, 5.5, 14)


class TestSchedulePerEra:
    christian_config = {
        "min_marriage_age_female": 14,
        "first_marriage": {
            "mean_age_female": 25.5,
            "sd_age_female": 5.5,
            "proportion_ever_married_female": 0.88,
        },
    }

    def test_the_schedule_of_an_era_has_the_location_derived_from_the_observed_mean(self):
        schedule = first_marriage_schedule(self.christian_config)
        assert schedule.location == pytest.approx(25.580, abs=1e-3)
        assert (schedule.scale, schedule.proportion, schedule.min_age) == (5.5, 0.88, 14)

    def test_two_calls_with_equal_inputs_share_one_schedule_object(self):
        assert first_marriage_schedule(self.christian_config) is first_marriage_schedule(
            dict(self.christian_config)
        )


_WEEKLY_YEARS = 168 / 8760
_FIRST_AGE, _LAST_AGE = 12.0, 50.0


def _propagate_never_married(schedule):
    """Propagate the never-married fraction tick by tick, with no random draw.

    Age is taken at the start of each tick: married = S * p(age).
    Returns (mean age of the marriages, share married at the last age).
    """
    never_married = 1.0
    weighted_age = married_total = 0.0
    age = _FIRST_AGE
    while age < _LAST_AGE:
        married = never_married * schedule.tick_probability(age, _WEEKLY_YEARS)
        weighted_age += married * age
        married_total += married
        never_married -= married
        age += _WEEKLY_YEARS
    return weighted_age / married_total, 1.0 - never_married


class TestRealizedCalendar:
    config = TestSchedulePerEra.christian_config

    def test_the_weekly_propagation_realizes_the_observed_mean(self):
        schedule = first_marriage_schedule(self.config)
        mean_age, share_married = _propagate_never_married(schedule)
        # Targets computed here: the mean is the template value, the share is
        # the conditioned CDF (R4) at the end of the window.
        assert mean_age == pytest.approx(25.50, abs=0.02)
        assert share_married == pytest.approx(schedule.conditional_cdf(50), abs=0.002)
        assert share_married == pytest.approx(0.8776, abs=0.002)

    def test_using_the_template_mean_as_location_misses_the_target(self):
        # Mutation proof of SC-002: skipping (R5) and using 25.5 as u gives a
        # realized mean of about 25.42, further than the 0.02 tolerance.
        mean_age, _ = _propagate_never_married(FirstMarriageSchedule(25.5, 5.5, 0.88, 14))
        assert abs(mean_age - 25.50) > 0.02


class TestSeededCohort:
    def test_a_seeded_cohort_realizes_the_calendar(self):
        # User Story 1, scenario 1: 20,000 never-married women aged 12, weekly
        # ticks to 50, candidates always available and no mortality. Every
        # woman still single marries with the tick probability; all share one
        # age per tick, so p is computed once per tick.
        schedule = first_marriage_schedule(TestSchedulePerEra.christian_config)
        rng = random.Random(20261029)
        cohort_size = 20_000
        single = cohort_size
        weighted_age = 0.0
        age = _FIRST_AGE
        while age < _LAST_AGE:
            p = schedule.tick_probability(age, _WEEKLY_YEARS)
            married = sum(rng.random() < p for _ in range(single))
            weighted_age += married * age
            single -= married
            age += _WEEKLY_YEARS
        ever_married = cohort_size - single
        # Three standard errors (spec SC-002): b / sqrt(n C) = 0.042 years on
        # the mean, sqrt(0.88 * 0.12 / n) = 0.0023 on the share.
        assert weighted_age / ever_married == pytest.approx(25.50, abs=0.13)
        assert ever_married / cohort_size == pytest.approx(0.878, abs=0.007)

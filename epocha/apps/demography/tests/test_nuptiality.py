"""Tests for the first-marriage schedule (Coale-McNeil, Kaneko form).

All tests are pure: no database, no Django models.
"""

import math

import pytest
from scipy.integrate import quad

from epocha.apps.demography import nuptiality
from epocha.apps.demography.nuptiality import _standard_lower, standard_cdf, standard_density

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

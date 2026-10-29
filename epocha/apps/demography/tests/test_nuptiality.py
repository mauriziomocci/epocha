"""Tests for the first-marriage schedule (Coale-McNeil, Kaneko form).

All tests are pure: no database, no Django models.
"""

import math

import pytest
from scipy.integrate import quad

from epocha.apps.demography import nuptiality
from epocha.apps.demography.nuptiality import standard_density

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

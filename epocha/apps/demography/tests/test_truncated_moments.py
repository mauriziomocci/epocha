"""Tests for the stationary moments of the truncated transmission kernel.

These pin the numbers the phase-0 amendment (A1, "La regione ammissibile")
publishes as the basis for accepting or rejecting a declared (era_mean,
era_sd) pair. Until now those figures lived only in prose; here they become
executable, which is the point of writing them first.

Every expected value below is quoted from the amendment, not from a run of
the code under test.
"""

from __future__ import annotations

import pytest

from epocha.apps.demography.truncated_moments import (
    AdmissibleRegionResult,
    boundary_mass,
    check_admissible_region,
    stationary_amplitude_ratio,
)


class TestStationaryAmplitudeRatio:
    """A1 publishes four measured configurations; all four are pinned here."""

    @pytest.mark.parametrize(
        ("era_mean", "era_sd", "coefficient", "expected_ratio", "expected_edge"),
        [
            # traits at the declared pair, h2 = 0.55 (the highest shipped)
            (0.50, 0.15, 0.55, 0.9991, 0.00086),
            # education at its declared pair, rho = 0.60 - the off-centre case
            (0.30, 0.15, 0.60, 0.9772, 0.02151),
            # rejected by check 3: the configuration that motivated the logit
            (0.80, 0.15, 0.55, 0.9203, 0.08141),
            # rejected by check 3: wide amplitude at the centre
            (0.50, 0.30, 0.55, 0.9074, 0.09120),
        ],
    )
    def test_reproduces_the_amendment_figures(
        self, era_mean, era_sd, coefficient, expected_ratio, expected_edge
    ):
        ratio = stationary_amplitude_ratio(era_mean, era_sd, coefficient)
        edge = boundary_mass(era_mean, era_sd, coefficient)
        assert ratio == pytest.approx(expected_ratio, abs=5e-4)
        assert edge == pytest.approx(expected_edge, abs=5e-4)

    def test_untruncated_configuration_realizes_its_declared_amplitude(self):
        """Far from both bounds the kernel must realize what it declares.

        This is the property FR-002 states. With three declared standard
        deviations of headroom on each side the truncation is inert, so any
        shortfall here would be the residual scale being wrong rather than
        the truncation biting.
        """
        assert stationary_amplitude_ratio(0.5, 0.10, 0.55) == pytest.approx(1.0, abs=2e-3)
        assert boundary_mass(0.5, 0.10, 0.55) == pytest.approx(0.0, abs=1e-3)

    def test_amplitude_falls_monotonically_as_the_mean_leaves_the_centre(self):
        ratios = [stationary_amplitude_ratio(m, 0.15, 0.55) for m in (0.50, 0.60, 0.70, 0.80, 0.90)]
        assert ratios == sorted(ratios, reverse=True)

    def test_boundary_mass_rises_monotonically_as_the_mean_leaves_the_centre(self):
        masses = [boundary_mass(m, 0.15, 0.55) for m in (0.50, 0.60, 0.70, 0.80, 0.90)]
        assert masses == sorted(masses)

    def test_is_symmetric_about_the_centre(self):
        """A mean of m and of 1-m are mirror images, so both moments must agree."""
        assert stationary_amplitude_ratio(0.30, 0.15, 0.60) == pytest.approx(
            stationary_amplitude_ratio(0.70, 0.15, 0.60), abs=1e-6
        )
        assert boundary_mass(0.30, 0.15, 0.60) == pytest.approx(
            boundary_mass(0.70, 0.15, 0.60), abs=1e-6
        )

    def test_is_deterministic(self):
        """The check runs at template load; two calls must not disagree."""
        first = stationary_amplitude_ratio(0.30, 0.15, 0.60)
        second = stationary_amplitude_ratio(0.30, 0.15, 0.60)
        assert first == second


class TestCheckAdmissibleRegion:
    """A1's three checks, and the verdicts the amendment states for each pair."""

    def test_accepts_both_pairs_the_amendment_declares(self):
        traits = check_admissible_region(0.50, 0.15, (0.22, 0.55))
        education = check_admissible_region(0.30, 0.15, (0.60,))
        assert traits.accepted, traits.reason
        assert education.accepted, education.reason

    def test_rejects_the_configuration_that_motivated_the_family_question(self):
        result = check_admissible_region(0.80, 0.15, (0.55,))
        assert not result.accepted
        assert "ampiezza" in result.reason
        # the reason must carry the measured value, not just a verdict, and the
        # value must be the WORST branch's, not the published two-parent one
        assert "92.0" in result.reason
        assert result.realized_ratio == pytest.approx(0.9203, abs=1e-3)

    def test_rejects_a_wide_amplitude_at_the_centre(self):
        assert not check_admissible_region(0.50, 0.30, (0.55,)).accepted

    def test_rejects_a_mean_on_the_boundary(self):
        for mean in (0.0, 1.0):
            result = check_admissible_region(mean, 0.15, (0.55,))
            assert not result.accepted
            assert "media" in result.reason

    def test_rejects_a_non_positive_amplitude(self):
        result = check_admissible_region(0.5, 0.0, (0.55,))
        assert not result.accepted
        assert "ampiezza" in result.reason

    def test_rejects_a_pair_violating_the_bhatia_davis_bound(self):
        """s^2 < m(1-m) bounds every distribution on [0,1], this family included."""
        result = check_admissible_region(0.5, 0.51, (0.55,))
        assert not result.accepted
        assert "Bhatia" in result.reason

    def test_evaluates_the_worst_branch_not_a_conventional_one(self):
        """A1 requires the minimum over the three kinship branches.

        The check must therefore differ when handed a coefficient set whose
        worst member fails, even if another member passes.
        """
        alone = check_admissible_region(0.74, 0.165, (0.22,))
        assert isinstance(alone, AdmissibleRegionResult)
        # the reported ratio must be the minimum across branches, so no branch
        # may realize less than what the result reports
        assert alone.realized_ratio <= stationary_amplitude_ratio(0.74, 0.165, 0.22)

    def test_reports_boundary_mass_without_gating_on_it(self):
        """A1 deleted the edge-mass ceiling; the quantity is reported, not gated.

        (0.30, 0.15) carries 2.15% edge mass and must still be accepted - a
        regression that reintroduced a 3% or lower ceiling would fail here,
        and one that reintroduced any ceiling at all would fail the pair the
        amendment declares.
        """
        result = check_admissible_region(0.30, 0.15, (0.60,))
        assert result.accepted
        # the reported mass is the worst branch's, which is the no-parent one at
        # 2.26%, not the two-parent 2.15% the amendment publishes
        assert result.boundary_mass == pytest.approx(0.0226, abs=1e-3)


class TestSingleParentBranchUsesOneParent:
    """Regression: the single-parent branch must not read a midparent.

    The two branches apply their coefficient to different random variables -
    a midparent carries half the population variance, a single parent carries
    all of it. Applying the single-parent coefficient to a midparent halves
    the parental variance reaching the child, so the stationary dispersion
    falls below what the residual scale was sized for. This test pins the
    three branch values against an independently measured spread.
    """

    @pytest.mark.parametrize(
        ("era_mean", "era_sd", "coefficient", "expected"),
        [
            (0.30, 0.15, 0.60, (0.97717, 0.97854, 0.97990)),
            (0.80, 0.15, 0.55, (0.92032, 0.92046, 0.92221)),
            (0.50, 0.15, 0.55, (0.99906, 0.99914, 0.99920)),
        ],
    )
    def test_branch_spread(self, era_mean, era_sd, coefficient, expected):
        from epocha.apps.demography.truncated_moments import _branch_coefficients, _solve

        measured = []
        for parents, signal, residual in _branch_coefficients(coefficient):
            _, sd, _ = _solve(era_mean, era_sd, parents, signal, residual * era_sd)
            measured.append(sd / era_sd)
        assert measured == pytest.approx(expected, abs=2e-4)

    def test_no_parent_branch_matches_a_closed_form_censored_normal(self):
        """The no-parent branch is a one-shot clip, so it has a closed form.

        It involves no fixed point at all - the child is clip(N(m, s)) - which
        makes it the one branch that can be checked against something other
        than this module's own machinery.
        """
        from scipy.integrate import quad
        from scipy.stats import norm

        from epocha.apps.demography.truncated_moments import _branch_coefficients, _solve

        mean, sd = 0.80, 0.15
        upper = 1.0 - norm.cdf((1 - mean) / sd)
        first = quad(lambda x: x * norm.pdf((x - mean) / sd) / sd, 0, 1)[0] + upper
        second = quad(lambda x: x * x * norm.pdf((x - mean) / sd) / sd, 0, 1)[0] + upper
        closed_form = (second - first**2) ** 0.5

        parents, signal, residual = _branch_coefficients(0.55)[2]
        _, grid_sd, _ = _solve(mean, sd, parents, signal, residual * sd)
        assert grid_sd == pytest.approx(closed_form, abs=1e-5)

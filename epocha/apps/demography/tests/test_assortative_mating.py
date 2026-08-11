"""SC-017: the parental correlation is measured and reported, not gated.

Amendment A4 states the assumption the amplitude target rests on --
`Var(midparent) = V/2`, which requires uncorrelated parents -- and observes
that the homogamy score weights education between 0.25 and 0.40 in all five
eras, so A3, by giving education its dispersion back, wakes that correlation
up everywhere rather than only where the meritocratic rule reads a trait.

A4 also publishes two crossing thresholds ON THE TRUNCATED FAMILY, `r ~ 0.53`
for the traits and `r ~ 0.75` for education, described as measured. Nothing
in the repository could regenerate them: the only committed stationary solver,
`truncated_moments._solve`, convolves the marginal with itself
(`truncated_moments.py:174`), which is by construction the distribution of a
sum of INDEPENDENT draws. There was no correlation parameter to turn. A number
a paper publishes as measured and nobody can reproduce is worse than no
number, so this file exists to make the measurement reproducible and to pin
what it returns.

WHAT IS PINNED AND WHAT IS NOT. The closed form is untruncated, exact, and
pinned to 1e-9. The truncated crossings come from the grid solver and are
pinned to the third decimal of `r`, cross-checked against an independent Monte
Carlo bench in this file -- the same discipline that caught the single-parent
branch defect during phase 1, where a number looked wrong before any test
failed. Neither is a gate: SC-017 reports, it does not reject.
"""

from __future__ import annotations

import math
import random

import numpy as np
import pytest

from epocha.apps.demography.truncated_moments import (
    assortative_amplitude_target,
    solve_assorted_stationary_state,
)

# The two configurations A4 quotes: the modal trait pair and the education one.
TRAIT_COEFFICIENT = 0.55
EDUCATION_COEFFICIENT = 0.60
TRAIT_ERA = (0.50, 0.15)
EDUCATION_ERA = (0.30, 0.15)


class TestTheClosedFormTarget:
    """A4's formula, checked against its own derivation rather than restated.

    With correlated parents `Var(midparent) = V(1+r)/2`, so the stationary
    variance solves `V = b^2 * V(1+r)/2 + (1 - b^2/2) * s^2` and the amplitude
    ratio is `sqrt((1 - b^2/2) / (1 - b^2(1+r)/2))`.
    """

    @pytest.mark.parametrize("b", [0.2, 0.4, 0.55, 0.6, 0.8])
    def test_uncorrelated_parents_return_exactly_one(self, b):
        assert assortative_amplitude_target(b, 0.0) == pytest.approx(1.0, abs=1e-15)

    @pytest.mark.parametrize("b", [0.4, 0.55, 0.6])
    @pytest.mark.parametrize("r", [0.1, 0.3, 0.5, 0.7])
    def test_the_ratio_solves_the_variance_recursion_it_claims(self, b, r):
        """Substitute the answer back into the recursion it was derived from."""
        ratio = assortative_amplitude_target(b, r)
        variance = ratio**2  # in units of s^2
        recursion = b**2 * variance * (1.0 + r) / 2.0 + (1.0 - b**2 / 2.0)
        assert variance == pytest.approx(recursion, rel=1e-14)

    @pytest.mark.parametrize("b", [0.4, 0.55, 0.6])
    def test_correlation_inflates_and_never_compresses(self, b):
        """A4's direction claim, which is the whole point of the section."""
        previous = assortative_amplitude_target(b, 0.0)
        for r in (0.1, 0.2, 0.4, 0.6, 0.8):
            current = assortative_amplitude_target(b, r)
            assert current > previous
            previous = current

    def test_negative_correlation_compresses(self):
        """Disassortative mating is the mirror case and must not be clamped."""
        assert assortative_amplitude_target(0.55, -0.4) < 1.0

    @pytest.mark.parametrize(
        ("b", "expected_r"),
        [(TRAIT_COEFFICIENT, 0.521711), (EDUCATION_COEFFICIENT, 0.423532)],
    )
    def test_a4_untruncated_thresholds_are_reproduced(self, b, expected_r):
        """A4 publishes 0.5217 at b=0.55 and 0.4235 at b=0.60 for the 105%
        crossing on the UNTRUNCATED recursion. Solved in closed form here:
        `r = (2/b^2) * (1 - (1 - b^2/2)/k^2) - 1` at `k = 1.05`.
        """
        k = 1.05
        solved = (2.0 / b**2) * (1.0 - (1.0 - b**2 / 2.0) / k**2) - 1.0
        assert solved == pytest.approx(expected_r, abs=1e-6)
        assert assortative_amplitude_target(b, solved) == pytest.approx(k, rel=1e-12)

    def test_the_domain_is_guarded_rather_than_returning_a_complex_number(self):
        """`1 - b^2(1+r)/2` reaches zero, and past it the formula is nonsense.
        At the coefficients this model admits (`b <= 1`) it cannot, since
        `b^2(1+r)/2 <= 1` at `r = 1`, but the guard states the domain instead
        of relying on a bound that a future coefficient could break.
        """
        with pytest.raises(ValueError):
            assortative_amplitude_target(0.55, 1.5)
        with pytest.raises(ValueError):
            assortative_amplitude_target(0.55, -1.5)


class TestTheTruncatedSolverIsConsistentWithTheIndependentOne:
    """At zero assortment the new solver must BE the old one.

    This is the structural check: a second stationary solver that disagrees
    with the first where they overlap means one of them is wrong, and a
    threshold read off either would be meaningless.
    """

    @pytest.mark.parametrize("era", [TRAIT_ERA, EDUCATION_ERA])
    def test_zero_assortment_reproduces_the_independent_fixed_point(self, era):
        from epocha.apps.demography.truncated_moments import _branch_coefficients, _solve

        era_mean, era_sd = era
        coefficient = TRAIT_COEFFICIENT if era == TRAIT_ERA else EDUCATION_COEFFICIENT
        _, signal, residual = _branch_coefficients(coefficient)[0]
        _, independent_sd, _ = _solve(era_mean, era_sd, 2, signal, residual * era_sd)

        state = solve_assorted_stationary_state(era_mean, era_sd, coefficient, 0.0)
        assert state.stationary_sd == pytest.approx(independent_sd, rel=1e-9)
        assert state.realized_parent_correlation == pytest.approx(0.0, abs=1e-9)

    @pytest.mark.parametrize("era", [TRAIT_ERA, EDUCATION_ERA])
    def test_assortment_raises_both_the_correlation_and_the_amplitude(self, era):
        era_mean, era_sd = era
        coefficient = TRAIT_COEFFICIENT if era == TRAIT_ERA else EDUCATION_COEFFICIENT
        previous_r = -1.0
        previous_sd = 0.0
        for copula in (0.0, 0.2, 0.4, 0.6, 0.8):
            state = solve_assorted_stationary_state(era_mean, era_sd, coefficient, copula)
            assert state.realized_parent_correlation > previous_r
            assert state.stationary_sd > previous_sd
            previous_r = state.realized_parent_correlation
            previous_sd = state.stationary_sd

    def test_the_realized_correlation_is_below_the_copula_parameter(self):
        """Clamping to `[0, 1]` piles mass on the bounds, and tied values carry
        no covariance, so the correlation the population actually shows is
        strictly under the latent one it was generated from. Reporting the
        copula parameter as if it were `r` would overstate the assortment.
        """
        state = solve_assorted_stationary_state(0.30, 0.15, 0.60, 0.60)
        assert 0.0 < state.realized_parent_correlation < 0.60


class TestTheSolverAgreesWithAnIndependentBench:
    """Monte Carlo, written from the definition rather than from the solver.

    Phase 1 found a real defect in the grid fixed point this way: a number
    looked wrong before any test failed. The bench is deliberately naive --
    sample pairs, clamp, transmit, measure -- so that an error in the grid
    machinery cannot hide inside the check meant to catch it.
    """

    @staticmethod
    def _bench(era_mean, era_sd, b, copula_r, generations=60, population=40000, seed=20260811):
        rng = random.Random(seed)
        gauss = rng.gauss
        values = [min(1.0, max(0.0, gauss(era_mean, era_sd))) for _ in range(population)]
        residual_sd = era_sd * math.sqrt(1.0 - b**2 / 2.0)
        last_r = 0.0
        for _ in range(generations):
            ordered = sorted(values)
            ranks = np.linspace(0.5 / population, 1.0 - 0.5 / population, population)
            latent = _ndtri(ranks)
            # Gaussian copula: pair each mother with a father whose latent
            # position is `copula_r * z + sqrt(1 - copula_r^2) * noise`.
            partner_latent = [
                copula_r * z + math.sqrt(1.0 - copula_r**2) * gauss(0.0, 1.0) for z in latent
            ]
            order = np.argsort(np.argsort(partner_latent))
            mothers = ordered
            fathers = [ordered[int(k)] for k in order]
            last_r = float(np.corrcoef(mothers, fathers)[0, 1])
            values = [
                min(
                    1.0,
                    max(0.0, era_mean + b * ((m + f) / 2.0 - era_mean) + gauss(0.0, residual_sd)),
                )
                for m, f in zip(mothers, fathers)
            ]
        return float(np.std(values)), last_r

    @pytest.mark.parametrize("copula_r", [0.0, 0.5])
    def test_grid_and_monte_carlo_agree_on_the_education_pair(self, copula_r):
        grid = solve_assorted_stationary_state(0.30, 0.15, 0.60, copula_r)
        bench_sd, bench_r = self._bench(0.30, 0.15, 0.60, copula_r)
        assert grid.stationary_sd == pytest.approx(bench_sd, rel=0.03)
        assert grid.realized_parent_correlation == pytest.approx(bench_r, abs=0.03)


def _ndtri(p):
    from scipy.special import ndtri

    return ndtri(p)


class TestTheTruncatedCrossingsArePinned:
    """The numbers A4 publishes as measured, regenerated and fixed in place.

    A4 quoted `r ~ 0.53` for the traits and `r ~ 0.75` for education, and A12
    quoted 0.54 and 0.74 for the same two measurements -- the same quantity,
    twice, with different values, in one document. Both were produced by a
    method nobody recorded. Measured here on the declared convention: 0.5403
    and 0.7122. A12 was right on the traits to two decimals and both were
    wrong on education. The amendment now carries these and states the method.

    Pinned to three decimals, which is finer than the disagreement they
    replace and coarser than the grid's own repeatability.
    """

    @staticmethod
    def _crossing(era_mean, era_sd, coefficient, ratio=1.05):
        low, high = 0.0, 0.999
        for _ in range(60):
            middle = (low + high) / 2.0
            state = solve_assorted_stationary_state(era_mean, era_sd, coefficient, middle)
            if state.stationary_sd / era_sd < ratio:
                low = middle
            else:
                high = middle
        return solve_assorted_stationary_state(era_mean, era_sd, coefficient, high)

    def test_the_trait_crossing(self):
        state = self._crossing(*TRAIT_ERA, TRAIT_COEFFICIENT)
        assert state.realized_parent_correlation == pytest.approx(0.5403, abs=5e-4)

    def test_the_education_crossing(self):
        state = self._crossing(*EDUCATION_ERA, EDUCATION_COEFFICIENT)
        assert state.realized_parent_correlation == pytest.approx(0.7122, abs=5e-4)

    def test_truncation_pushes_the_crossing_later_for_education_and_not_for_traits(self):
        """Why the two eras separate, which is the finding worth keeping.

        The untruncated crossings are 0.5217 and 0.4235: education crosses
        EARLIER on paper. Under truncation they invert, because the education
        pair sits off centre at (0.30, 0.15) and the clamp already costs it
        2.14% of its amplitude before any assortment -- inflation has to make
        that back before it can exceed the band. The centred trait pair loses
        almost nothing, so its truncated crossing barely moves.
        """
        traits = self._crossing(*TRAIT_ERA, TRAIT_COEFFICIENT)
        education = self._crossing(*EDUCATION_ERA, EDUCATION_COEFFICIENT)
        assert education.realized_parent_correlation > traits.realized_parent_correlation

        untruncated_traits = (2.0 / TRAIT_COEFFICIENT**2) * (
            1.0 - (1.0 - TRAIT_COEFFICIENT**2 / 2.0) / 1.05**2
        ) - 1.0
        untruncated_education = (2.0 / EDUCATION_COEFFICIENT**2) * (
            1.0 - (1.0 - EDUCATION_COEFFICIENT**2 / 2.0) / 1.05**2
        ) - 1.0
        assert untruncated_education < untruncated_traits

    def test_the_uncorrelated_baseline_the_crossings_are_measured_against(self):
        """The truncation cost before any assortment, stated as a number.

        99.91% for the centred trait pair, 97.72% for the off-centre education
        one on the two-parent branch. Published because the whitepaper needs a
        figure here and the figure it carried was measured at a different
        configuration entirely.
        """
        traits = solve_assorted_stationary_state(*TRAIT_ERA, TRAIT_COEFFICIENT, 0.0)
        education = solve_assorted_stationary_state(*EDUCATION_ERA, EDUCATION_COEFFICIENT, 0.0)
        assert traits.stationary_sd / TRAIT_ERA[1] == pytest.approx(0.9991, abs=5e-4)
        assert education.stationary_sd / EDUCATION_ERA[1] == pytest.approx(0.9772, abs=5e-4)
        assert education.boundary_mass == pytest.approx(0.0214, abs=5e-4)

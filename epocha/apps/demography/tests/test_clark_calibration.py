"""Calibration of the Clark innovation amplitude (amendment A3).

Clark's rule was implemented as a deterministic weighted average. That is not
a simplification of his model, it is a model with the OPPOSITE asymptotic
behaviour: the formal statement in Clark, Cummins, Hao & Diaz Vidal is an
AR(1) WITH an innovation term, `x_t = b*x_{t-1} + e_t`, plus an observation
error, and the same source writes the stationary identity
`sigma^2 = b^2*sigma^2 + sigma_e^2`. Without the innovation every lineage
walks monotonically to the mean and the cross-sectional variance vanishes --
no mobility AND no stratification -- while Clark's model holds the variance
constant and reshuffles continuously. His low mobility is slow regression,
not freezing.

Measured on the rule as it shipped: intergenerational mobility EXACTLY
0.0000 and a parent-child rank correlation of EXACTLY 1.0000 from the second
generation, on a partition with two of the five ranks empty.

WHY THE AMPLITUDE IS SOLVED AND NOT READ. The identity fixes the amplitude on
a continuous scale, but the rule rounds to integer labels and clamps at both
ends, and neither operation is linear. Reading `s_rank * sqrt(1 - b^2)`
straight out of the identity lands at 102.26% of the target. The value is
therefore derived from the identity and then SOLVED numerically against the
realized post-rounding distribution.
"""

from __future__ import annotations

import pytest

from epocha.apps.demography.clark_calibration import (
    CLARK_PERSISTENCE,
    S_RANK_MAX,
    S_RANK_MIN,
    ClarkCalibrationError,
    realized_rank_dispersion,
    solve_clark_innovation,
    stationary_rank_distribution,
)


class TestTheDefectItReplaces:
    """The deterministic rule, reproduced so the correction has a baseline."""

    def test_zero_innovation_freezes_the_partition(self):
        """From a uniform founding population the map sends {0..4} to {1,1,2,3,3}.

        Two ranks go empty in ONE generation and the partition is then
        bit-identical forever: dispersion sqrt(0.8), which is 63.2% of the
        founding population's own sqrt(2), and mobility exactly zero.
        """
        distribution = stationary_rank_distribution(0.0)
        assert distribution[0] == pytest.approx(0.0, abs=1e-12)
        assert distribution[4] == pytest.approx(0.0, abs=1e-12)
        assert realized_rank_dispersion(0.0) == pytest.approx(0.894427, abs=1e-5)

    def test_the_frozen_dispersion_is_632_percent_of_the_founding_one(self):
        """Not the 90.8% a superseded draft of the spec reported.

        The maximum dispersion attainable on a three-rank support with mean 2
        is 1.0, i.e. 70.7% of sqrt(2), so 90.8% was arithmetically unreachable.
        """
        founding = 2.0**0.5
        assert realized_rank_dispersion(0.0) / founding == pytest.approx(0.632, abs=1e-3)


class TestTheMapIsNotMonotone:
    """The amendment's well-posedness conditions, verified rather than trusted.

    They exist because a bisection needs a bracket in which the root is
    unique, and this map does not provide one over its whole domain.
    """

    def test_dispersion_collapses_before_it_rises(self):
        """Near sigma = 0.075 the map dips to almost nothing.

        Ranks 1 and 3 leak into 2 far faster than 2 leaks back out, so the
        distribution concentrates before the innovation is strong enough to
        spread it. A bisection bracketed below this dip has no sign change
        while two roots sit inside it.
        """
        at_zero = realized_rank_dispersion(0.0)
        at_dip = realized_rank_dispersion(0.075)
        at_top = realized_rank_dispersion(S_RANK_MAX)
        assert at_dip < 0.01
        assert at_zero > 0.5
        assert at_top > at_dip

    def test_it_rises_monotonically_above_the_dip(self):
        sigmas = [0.10, 0.30, 0.50, 0.70, 0.90, 1.10, 1.30, 1.4142]
        values = [realized_rank_dispersion(s) for s in sigmas]
        assert values == sorted(values)

    def test_the_declared_unique_root_interval_is_reachable(self):
        """Both endpoints of [S_RANK_MIN, S_RANK_MAX] must have a root."""
        for target in (S_RANK_MIN, S_RANK_MAX):
            sigma = solve_clark_innovation(target)
            assert realized_rank_dispersion(sigma) == pytest.approx(target, abs=1e-9)


class TestSolveClarkInnovation:
    """SC-012a: the amplitude equals the root, to 1e-12, not to a band."""

    def test_the_root_at_the_declared_target(self):
        """s_rank = 1.0 is what every template declares."""
        assert solve_clark_innovation(1.0) == pytest.approx(0.688956, abs=1e-5)

    def test_the_solved_value_hits_the_target_exactly(self):
        sigma = solve_clark_innovation(1.0)
        assert realized_rank_dispersion(sigma) == pytest.approx(1.0, abs=1e-9)

    def test_reading_the_identity_instead_of_solving_misses(self):
        """`s_rank * sqrt(1 - b^2)` is the continuous-scale answer.

        On the rounded, clamped scale it lands at 102.26% of the target -- a
        band of five percent would have admitted it, which is why SC-012a is
        exact.
        """
        naive = 1.0 * (1.0 - CLARK_PERSISTENCE**2) ** 0.5
        assert realized_rank_dispersion(naive) == pytest.approx(1.0226, abs=2e-3)
        assert naive != pytest.approx(solve_clark_innovation(1.0), rel=1e-3)

    def test_mobility_is_strictly_positive_at_the_solved_amplitude(self):
        """The sanity check, not the criterion: any positive amplitude passes
        it, which is why the criterion is the root instead."""
        from epocha.apps.demography.clark_calibration import realized_mobility

        assert realized_mobility(solve_clark_innovation(1.0)) > 0.0
        assert realized_mobility(0.0) == pytest.approx(0.0, abs=1e-12)

    def test_is_deterministic_and_cached(self):
        assert solve_clark_innovation(1.0) == solve_clark_innovation(1.0)

    @pytest.mark.parametrize("target", [0.5, 0.9, 1.40, 1.5])
    def test_targets_outside_the_unique_root_interval_are_refused(self, target):
        """Outside [0.95, 1.39] the bracket has no sign change or two roots.

        Returning an answer anyway would mean a bisection converging on
        whichever side it happened to start from.
        """
        with pytest.raises(ClarkCalibrationError, match="unique"):
            solve_clark_innovation(target)


class TestTheFixedPointIsWellPosed:
    """A3 fixes the initial vector because the fixed point is not unique.

    The transition matrix depends on the mean of the distribution being
    solved for, so this is a mean-field problem, not a linear stationary
    vector: at small amplitudes a population starting concentrated on one
    rank stays there, and that is a genuine fixed point too.
    """

    def test_a_concentrated_start_is_also_a_fixed_point_at_small_amplitude(self):
        concentrated = [0.0, 0.0, 1.0, 0.0, 0.0]
        settled = stationary_rank_distribution(0.001, initial=concentrated)
        assert settled[2] == pytest.approx(1.0, abs=1e-6)

    def test_the_declared_uniform_start_reaches_the_published_value(self):
        """Which is why the initial vector is part of the specification."""
        assert realized_rank_dispersion(0.001) == pytest.approx(0.894427, abs=1e-3)

    def test_the_extended_input_rank_is_accepted(self):
        """The ladder admits `enslaved` at rank 5 on INPUT; only the output is
        capped at 4. A founding population carrying it must not raise."""
        settled = stationary_rank_distribution(0.5, initial=[0.0] * 5 + [1.0])
        assert len(settled) == 5
        assert sum(settled) == pytest.approx(1.0, abs=1e-9)


class TestThePersistenceIsTheDeclaredHeuristic:
    """`b = 0.7` is a declared design heuristic, NOT Clark's 0.75.

    His constant applies to a LATENT status this model does not possess --
    here the ladder IS the state variable, not a noisy observation of
    something underlying it -- so his attenuation factor cannot be computed
    and cannot be applied. The numerical closeness of 0.7 to 0.75 is
    meaningless, and a future edit "correcting" it toward his figure would be
    exactly the misattribution the amendment forbids. Without this test that
    edit passes silently: every other test here is satisfied by either value.
    """

    def test_the_persistence_is_the_declared_value(self):
        assert CLARK_PERSISTENCE == 0.7

    def test_it_is_not_clarks_latent_constant(self):
        assert CLARK_PERSISTENCE != 0.75, (
            "0.75 is Clark's LATENT-status constant and does not belong on an "
            "observable five-rank ladder"
        )

    def test_the_persistence_actually_enters_the_map(self):
        """A constant nobody reads is not a parameter.

        Measured at a fixed innovation inside the bracket: raising the
        persistence pulls each child closer to its parent, so the stationary
        dispersion rises. An implementation that hardcoded a different value,
        or ignored the constant, gives the same number for both.
        """
        from epocha.apps.demography import clark_calibration

        original = clark_calibration.CLARK_PERSISTENCE
        probe_sigma = 0.688956
        try:
            baseline = realized_rank_dispersion(probe_sigma)
            clark_calibration.CLARK_PERSISTENCE = 0.75
            raised = realized_rank_dispersion(probe_sigma)
        finally:
            clark_calibration.CLARK_PERSISTENCE = original
        assert raised != pytest.approx(baseline, rel=1e-6)


class TestTheZoneMeanIsSolvedForNotAssumed:
    """The transition matrix depends on the distribution being solved for.

    That is what makes this a mean-field problem rather than a linear
    stationary-vector one, and it is invisible on a symmetric ladder: a
    uniform start has mean 2, the ladder is symmetric about 2, and the fixed
    point stays there, so an implementation that hardcoded 2.0 would agree
    with every symmetric test. These start ASYMMETRIC, where a frozen mean
    and a solved one part company.
    """

    def test_an_asymmetric_start_settles_away_from_the_ladder_centre(self):
        skewed = [0.7, 0.3, 0.0, 0.0, 0.0]
        settled = stationary_rank_distribution(0.30, initial=skewed)
        mean = sum(p * k for k, p in enumerate(settled))
        assert mean < 1.5, "a population starting low must not be pulled to the centre"

    def test_two_asymmetric_starts_settle_at_different_means(self):
        """A frozen zone mean drags both to the same place; a solved one does
        not, because each population is its own reference."""
        low = stationary_rank_distribution(0.30, initial=[0.7, 0.3, 0.0, 0.0, 0.0])
        high = stationary_rank_distribution(0.30, initial=[0.0, 0.0, 0.0, 0.3, 0.7])
        low_mean = sum(p * k for k, p in enumerate(low))
        high_mean = sum(p * k for k, p in enumerate(high))
        assert high_mean - low_mean > 1.0


class TestTheBracketIsWhereTheSolverCanWork:
    """Why the bisection is bracketed above the collapse.

    Two independent reasons, and both are measured rather than asserted.

    First, no admitted target has a root down there: at the bracket's lower
    endpoint the dispersion is already far below the smallest admitted target,
    and the map is monotone above it, so the non-monotone stretch is
    unreachable for any question the solver is allowed to be asked.

    Second, and this is the one that would otherwise be discovered in
    production: the mean-field iteration does not CONVERGE below the bracket.
    Measured from the uniform start, it settles in 40 steps at the operating
    amplitude, 19 at the top of the bracket, and 9,763 at its lower endpoint --
    but 1,409,260 at 0.05, and at 0.03 it does not settle at all within three
    million, because the innovation is too weak to move mass across a
    half-unit rounding cell and the distribution creeps forever. The iteration
    cap is therefore sized for the bracket, and refusing outside it is correct
    behaviour rather than a missing feature.
    """

    def test_the_lower_endpoint_is_already_below_the_smallest_target(self):
        assert realized_rank_dispersion(0.075) < S_RANK_MIN

    def test_the_iteration_settles_quickly_across_the_whole_bracket(self):
        """If this ever slows down, the cap is the thing to re-measure."""
        for sigma in (0.075, 0.1, 0.3, 0.688956, 1.0, 1.39):
            assert realized_rank_dispersion(sigma) >= 0.0  # must not raise

    def test_below_the_bracket_the_solver_refuses_rather_than_guessing(self):
        """An unconverged dispersion returned as if settled would silently
        mis-calibrate every era using this rule."""
        with pytest.raises(ClarkCalibrationError, match="did not settle"):
            realized_rank_dispersion(0.05)

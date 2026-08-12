"""SC-002a and SC-013 against the polygenic transmission kernel.

The defect this work item exists for: `inherit_trait` writes the residual as
`(1 - h2) * noise`, a weighted-average convention whose two coefficients sum
to one, rather than the scale the variance identity of amendment A1 fixes.
Measured, the stationary dispersion settles at 48.85% of the declared era
amplitude at h2 = 0.55, and the loss runs from 21% to 51% across the range the
five templates ship.

WHY THESE TESTS ARE EXACT AND NOT SAMPLED. A1's own criterion (SC-002a) is a
two-point probe, and the reason is recorded in the amendment: no band on the
realized amplitude separates the correct model from the defective one. On the
single-parent branch the defective model measures 95.82% of the declared
amplitude and lands inside any tolerance wide enough to admit Monte Carlo
noise -- at every one of the thirteen distinct coefficients the templates
ship. So the
criterion is asserted on the coefficients themselves, which are closed forms
of the transmission coefficient, to 1e-12.

The probe has two halves and both are load-bearing. Fixing the signal and
varying the DRAW pins the residual scale; fixing the draw and varying the
PARENTS pins the signal coefficient in absolute value. Without the second
half nothing constrains it: a kernel shipping `b = k*h2` on two parents and
`k*h2/2` on one, with exact residual scales, passes the first half untouched
and passes the branch-ratio criterion too, since that ratio is invariant to a
uniform rescale. At k = 0 that kernel realizes exactly the 92.13% the
amendment reports for a two-parent residual with no signal at all.
"""

from __future__ import annotations

import math

import pytest

from epocha.apps.demography.inheritance import inherit_trait

# Every DISTINCT transmission coefficient the five era templates ship: the
# eleven distinct heritability values across their thirteen heritable
# characters, plus the two education-regression coefficients the same kernel
# governs after amendment A3 (0.30 for sci-fi, 0.60 for the other four).
# Counted from the templates rather than asserted -- an earlier version of
# this comment said "thirteen coefficients plus the education one" and listed
# twelve numbers, missing sci-fi's 0.30 entirely.
SHIPPED_COEFFICIENTS = [
    0.22,
    0.30,
    0.40,
    0.41,
    0.42,
    0.44,
    0.45,
    0.48,
    0.50,
    0.52,
    0.54,
    0.55,
    0.60,
]

ERA_MEAN = 0.5
ERA_SD = 0.15
PROBE_TOLERANCE = 1e-12


class _FixedDraw:
    """An rng whose `gauss` returns a caller-chosen number of sigmas.

    `inherit_trait` scales the draw by the branch residual, so the stub
    returns `sigma * z` and the probe recovers the scale exactly.
    """

    def __init__(self, z: float) -> None:
        self.z = z
        self.calls = 0

    def gauss(self, mu: float, sigma: float) -> float:
        self.calls += 1
        return mu + sigma * self.z


def _residual_scale(coefficient: float, parents: int) -> float:
    """The closed forms A1 derives from `V = b^2*Var(parents) + c^2*s^2`."""
    if parents == 2:
        return math.sqrt(1.0 - coefficient**2 / 2.0)
    if parents == 1:
        return math.sqrt(1.0 - coefficient**2 / 4.0)
    return 1.0


def _signal_coefficient(coefficient: float, parents: int) -> float:
    """`h2` on the midparent, `h2/2` on a single parent, nothing on neither."""
    if parents == 2:
        return coefficient
    if parents == 1:
        return coefficient / 2.0
    return 0.0


def _call(coefficient: float, parents: int, parent_value: float, z: float) -> float:
    rng = _FixedDraw(z)
    if parents == 2:
        result = inherit_trait(parent_value, parent_value, coefficient, ERA_MEAN, ERA_SD, rng)
    elif parents == 1:
        result = inherit_trait(parent_value, None, coefficient, ERA_MEAN, ERA_SD, rng)
    else:
        result = inherit_trait(None, None, coefficient, ERA_MEAN, ERA_SD, rng)
    assert rng.calls == 1, "the kernel must draw exactly once per call"
    return result


class TestResidualAxisProbe:
    """SC-002a, first half: signal fixed, draws varied. Pins the residual."""

    @pytest.mark.parametrize("coefficient", SHIPPED_COEFFICIENTS)
    @pytest.mark.parametrize("parents", [2, 1, 0])
    def test_effective_residual_coefficient(self, coefficient, parents):
        z1, z2 = 1.0, -1.0  # separation 2, well above the required 1
        first = _call(coefficient, parents, ERA_MEAN, z1)
        second = _call(coefficient, parents, ERA_MEAN, z2)
        assert 0.0 < first < 1.0 and 0.0 < second < 1.0, "probe must stay interior"

        measured = (first - second) / ((z1 - z2) * ERA_SD)
        expected = _residual_scale(coefficient, parents)
        assert measured == pytest.approx(expected, rel=PROBE_TOLERANCE)

    @pytest.mark.parametrize("parents", [2, 1, 0])
    def test_todays_writing_is_rejected_on_every_branch(self, parents):
        """`(1 - h2)` is what the kernel wrote before the amendment.

        REBUILT after the phase-6 audit. The previous version compared
        `_residual_scale(0.55, parents)` -- this file's own helper -- against
        the literal `1 - 0.55` and never called `inherit_trait` at all. It
        was an assertion about Python arithmetic: a kernel still shipping the
        old scale passed it. The measurement below goes through the KERNEL,
        which is the only thing that can reject an implementation.
        """
        z1, z2 = 1.0, -1.0
        first = _call(0.55, parents, ERA_MEAN, z1)
        second = _call(0.55, parents, ERA_MEAN, z2)
        assert 0.0 < first < 1.0 and 0.0 < second < 1.0, "probe must stay interior"
        measured = (first - second) / ((z1 - z2) * ERA_SD)
        assert not math.isclose(measured, 1 - 0.55, rel_tol=1e-6), (
            f"branch {parents}: the kernel's residual scale measures "
            f"{measured!r}, which is the pre-amendment (1 - h2) writing"
        )

    @pytest.mark.parametrize("coefficient", SHIPPED_COEFFICIENTS)
    @pytest.mark.parametrize("parents", [2, 1])
    def test_the_h2_to_the_fourth_trap_is_rejected(self, coefficient, parents):
        """`1 - h2**4/2` where `1 - h2**2/2` belongs.

        REBUILT for the same reason. The previous version compared two
        closed forms to each other and asserted the GAP was large -- true of
        the mathematics regardless of what the kernel does, so `h2**4` in
        the implementation passed it. The trap is real and invisible to a
        slope test (identical slope, standard deviation inflated 6.03% at
        h2 = 0.55), so the criterion has to measure the kernel's own
        residual and reject the wrong exponent's value.
        """
        z1, z2 = 1.0, -1.0
        first = _call(coefficient, parents, ERA_MEAN, z1)
        second = _call(coefficient, parents, ERA_MEAN, z2)
        assert 0.0 < first < 1.0 and 0.0 < second < 1.0, "probe must stay interior"
        measured = (first - second) / ((z1 - z2) * ERA_SD)

        divisor = 2.0 if parents == 2 else 4.0
        wrong = math.sqrt(1 - coefficient**4 / divisor)
        assert not math.isclose(measured, wrong, rel_tol=1e-6), (
            f"coefficient {coefficient}, branch {parents}: the kernel measures "
            f"{measured!r}, which is the h2**4 writing"
        )
        assert measured == pytest.approx(_residual_scale(coefficient, parents), rel=PROBE_TOLERANCE)


class TestSignalAxisProbe:
    """SC-002a, second half: draw fixed, parents varied. Pins the signal.

    Without this half a uniformly mis-scaled kernel passes everything.
    """

    @pytest.mark.parametrize("coefficient", SHIPPED_COEFFICIENTS)
    @pytest.mark.parametrize("parents", [2, 1])
    def test_effective_signal_coefficient(self, coefficient, parents):
        p1, p2 = 0.7, 0.3  # separation 0.4, above the required 0.1
        first = _call(coefficient, parents, p1, z=0.0)
        second = _call(coefficient, parents, p2, z=0.0)
        assert 0.0 < first < 1.0 and 0.0 < second < 1.0, "probe must stay interior"

        measured = (first - second) / (p1 - p2)
        expected = _signal_coefficient(coefficient, parents)
        assert measured == pytest.approx(expected, rel=PROBE_TOLERANCE)

    @pytest.mark.parametrize("coefficient", SHIPPED_COEFFICIENTS)
    def test_no_parent_branch_resolves_to_the_declared_era_mean(self, coefficient):
        """With neither parent the child sits exactly at the era mean.

        REPLACED after the phase-6 audit. The previous test passed 0.9 and
        0.1 as "parent values" to a branch whose helper calls
        `inherit_trait(None, None, ...)`: neither value ever reached the
        function, so the two calls were identical BY CONSTRUCTION and the
        assertion held for any implementation whatsoever. A12 exempts this
        branch from the signal probe for exactly that reason. What IS
        assertable here is the LEVEL: with a zero draw the child must land on
        the declared era mean. The probe is run at an OFF-CENTRE mean, not at
        this file's own 0.5, because 0.5 is the midpoint of the clamp range
        and a kernel that ignored the declared mean entirely would still
        produce it.
        """
        off_centre = 0.28
        rng = _FixedDraw(0.0)
        result = inherit_trait(None, None, coefficient, off_centre, ERA_SD, rng)
        assert rng.calls == 1, "the kernel must draw exactly once per call"
        assert result == pytest.approx(off_centre, abs=1e-12)
        # The same call at this file's own centred mean must also land on it:
        # two declared means, two different answers, so an implementation
        # returning a constant fails one of them whichever constant it picks.
        # (A third line asserting the two differ was removed: it followed from
        # the two above and could not fail.)
        centred = inherit_trait(None, None, coefficient, ERA_MEAN, ERA_SD, _FixedDraw(0.0))
        assert centred == pytest.approx(ERA_MEAN, abs=1e-12)

    @pytest.mark.parametrize("coefficient", SHIPPED_COEFFICIENTS)
    def test_single_parent_signal_is_half_the_two_parent_one(self, coefficient):
        """SC-013, retained: it is exact and it discriminates.

        It does not, on its own, pin either coefficient in absolute value --
        the ratio survives any uniform rescale -- which is why the signal-axis
        probe above exists alongside it.
        """
        p1, p2 = 0.7, 0.3
        two = (_call(coefficient, 2, p1, 0.0) - _call(coefficient, 2, p2, 0.0)) / (p1 - p2)
        one = (_call(coefficient, 1, p1, 0.0) - _call(coefficient, 1, p2, 0.0)) / (p1 - p2)
        assert one == pytest.approx(two / 2.0, rel=PROBE_TOLERANCE)


class TestKernelInvariants:
    """Properties the amendment does not change and a rewrite could break."""

    @pytest.mark.parametrize("parents", [2, 1, 0])
    def test_draws_exactly_once_regardless_of_branch(self, parents):
        """The RNG stream a tick consumes must not depend on which branch ran.

        A branch that skipped its draw would shift every later draw in the
        tick for that agent, which is the determinism trap this work item has
        to watch.
        """
        rng = _FixedDraw(0.5)
        args = {2: (0.6, 0.4), 1: (0.6, None), 0: (None, None)}[parents]
        inherit_trait(args[0], args[1], 0.55, ERA_MEAN, ERA_SD, rng)
        assert rng.calls == 1

    def test_result_is_clamped_to_the_declared_range(self):
        far_above = _call(0.55, 2, 1.0, z=40.0)
        far_below = _call(0.55, 2, 0.0, z=-40.0)
        assert far_above == 1.0
        assert far_below == 0.0

    def test_a_centred_population_stays_centred(self):
        """Parents at the era mean and a zero draw must reproduce the mean.

        A signal written against the raw parent value rather than its
        deviation from the mean would fail this on every branch but the one
        where the coefficients happen to sum to one.
        """
        for parents in (2, 1, 0):
            assert _call(0.55, parents, ERA_MEAN, z=0.0) == pytest.approx(ERA_MEAN, abs=1e-15)

    def test_off_centre_era_mean_is_reproduced(self):
        """The same property away from the centre, where a weighted-average
        writing and a deviation writing stop agreeing."""
        rng = _FixedDraw(0.0)
        assert inherit_trait(0.3, 0.3, 0.55, 0.3, 0.15, rng) == pytest.approx(0.3, abs=1e-15)


class TestStationaryDispersionIsRealized:
    """The integration check: FR-002's property, measured on a population.

    Reported as a check, not as the discriminator -- SC-002a is that. Here it
    confirms that the exact coefficients compose into the behaviour the
    amendment promises, which no single-call probe can show.
    """

    @pytest.mark.parametrize("coefficient", [0.22, 0.44, 0.55])
    def test_dispersion_matches_the_grid_prediction(self, coefficient):
        import random
        import statistics

        from epocha.apps.demography.truncated_moments import _branch_coefficients, _solve

        parents_count, signal, residual = _branch_coefficients(coefficient)[0]
        _, predicted_sd, _ = _solve(ERA_MEAN, ERA_SD, parents_count, signal, residual * ERA_SD)

        rng = random.Random(4242)
        population = [min(1.0, max(0.0, rng.gauss(ERA_MEAN, ERA_SD))) for _ in range(20000)]
        for _ in range(12):
            shuffled = list(population)
            rng.shuffle(shuffled)
            half = len(shuffled) // 2
            children = [
                inherit_trait(m, f, coefficient, ERA_MEAN, ERA_SD, rng)
                for m, f in zip(shuffled[:half], shuffled[half : 2 * half])
            ]
            population = children * 2

        measured_sd = statistics.pstdev(population)
        assert measured_sd == pytest.approx(predicted_sd, rel=0.02)
        # and the whole point: it must be near the DECLARED amplitude, where
        # the pre-amendment kernel settled at 48.85% of it
        assert measured_sd / ERA_SD > 0.95

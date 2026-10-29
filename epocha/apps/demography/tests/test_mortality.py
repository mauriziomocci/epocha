"""Unit tests for demography/mortality.py.

Covers:
- annual_mortality_probability: finiteness, monotonicity over old ages
- tick_mortality_probability: scaling branch (linear vs geometric)
- sample_death_cause: valid label, cause distribution by age cohort
- fit_heligman_pollard: round-trip recovery on clean synthetic data,
  convergence failure on degenerate input, bound compliance

Scientific reference: Heligman, L. & Pollard, J.H. (1980). The age
pattern of mortality. Journal of the Institute of Actuaries 107(1), 49-80.
"""

from __future__ import annotations

import math
import random

import pytest

from epocha.apps.demography.mortality import (
    HP_PARAM_KEYS,
    UnderdeterminedFitError,
    annual_mortality_probability,
    fit_heligman_pollard,
    sample_death_cause,
    tick_mortality_probability,
)

# Pre-industrial Christian era seed values from
# epocha/apps/demography/templates/pre_industrial_christian.json.
# These are calibrated from Wrigley-Schofield (1981) English historical
# life tables (plan 4 will validate against the full table).
PRE_INDUSTRIAL_PARAMS: dict[str, float] = {
    "A": 0.00491,
    "B": 0.017,
    "C": 0.102,
    "D": 0.00080,
    "E": 9.9,
    "F": 22.4,
    "G": 0.0000383,
    "H": 1.101,
}

VALID_CAUSES = frozenset({"early_life_mortality", "external_cause", "natural_senescence"})


# ---------------------------------------------------------------------------
# Task 23: annual_mortality_probability
# ---------------------------------------------------------------------------


class TestAnnualMortalityProbability:
    """annual_mortality_probability correctness, finiteness, and monotonicity."""

    def test_finite_at_key_ages(self):
        """Returns a finite probability in (0, 1) for the benchmark ages."""
        for age in (0, 1, 25, 50, 80):
            q = annual_mortality_probability(age, PRE_INDUSTRIAL_PARAMS)
            assert math.isfinite(q), f"non-finite at age {age}"
            assert 0.0 < q < 1.0, f"probability out of bounds at age {age}: {q}"

    def test_monotone_old_ages(self):
        """Gompertz component dominates at old ages: q(40) < q(60) < q(80).

        In the HP model the senescence term G*H^x grows exponentially and
        overwhelms the other two components beyond age ~35, producing a
        strictly increasing death rate for ages 40+.
        """
        q40 = annual_mortality_probability(40, PRE_INDUSTRIAL_PARAMS)
        q60 = annual_mortality_probability(60, PRE_INDUSTRIAL_PARAMS)
        q80 = annual_mortality_probability(80, PRE_INDUSTRIAL_PARAMS)
        assert q40 < q60, f"q(60)={q60} not > q(40)={q40}"
        assert q60 < q80, f"q(80)={q80} not > q(60)={q60}"

    def test_q_is_held_over_each_year_of_age(self):
        """`q_x` belongs to the completed age, so it does not move within a year.

        HP `q_x` is the probability of dying between exact ages `x` and
        `x + 1` (gate decision D-29-20): a newborn of three months and one of
        eleven carry the same `q_0`, and the step to `q_1` happens at the
        first birthday, not before.
        """
        for whole_age in (0, 1, 30):
            q = annual_mortality_probability(whole_age, PRE_INDUSTRIAL_PARAMS)
            for fraction in (0.25, 0.5, 0.999):
                assert annual_mortality_probability(
                    whole_age + fraction, PRE_INDUSTRIAL_PARAMS
                ) == pytest.approx(q, rel=1e-12), f"q moved inside year {whole_age}"

    def test_q0_is_the_formula_at_exact_age_zero(self):
        """`q_0` is HP at `x = 0`, the hump term at its limit zero.

        The odds are `A ** (B ** C) + D * 0 + G * H ** 0`. The former guard
        `max(age, 0.01)` evaluated the infancy term at 0.01 instead, which
        with `B = 0.017` gave 0.0247 instead of 0.0291.
        """
        p = PRE_INDUSTRIAL_PARAMS
        odds = p["A"] ** (p["B"] ** p["C"]) + p["G"]
        assert annual_mortality_probability(0, p) == pytest.approx(odds / (1.0 + odds), rel=1e-12)
        assert annual_mortality_probability(0, p) == pytest.approx(0.0291, abs=5e-5)


# ---------------------------------------------------------------------------
# Task 23: tick_mortality_probability
# ---------------------------------------------------------------------------


class TestTickMortalityProbability:
    """tick_mortality_probability scaling and branch selection."""

    def test_tick_less_than_annual_for_sub_year_dt(self):
        """Tick probability < annual probability whenever dt < 1 year.

        Both branches (linear and geometric) produce a value strictly below
        the annual probability for a sub-year tick.
        """
        for age in (1, 25, 50, 80):
            annual_q = annual_mortality_probability(age, PRE_INDUSTRIAL_PARAMS)
            # tick = 4380 hours = 0.5 years
            tick_q = tick_mortality_probability(
                age, PRE_INDUSTRIAL_PARAMS, tick_duration_hours=4380
            )
            assert tick_q < annual_q, f"tick_q={tick_q} not < annual_q={annual_q} at age {age}"

    def test_the_tick_probability_is_the_exact_geometric_conversion_at_every_age(self):
        """No linear branch: `1 - (1 - q)^dt` at every age, for a daily tick.

        Found by round 11 of the demography Plan 4 phase-6 gate. Below
        `q = 0.1` the function used the linear `q * dt`, whose relative error
        against the geometric form is about `q / 2`: measured with these
        parameters up to 4.71% at 82, against an error the docstring and
        whitepaper section 4.1.1 declared "better than 0.5%". The branch also
        made the hazard jump by about 5% between 82 and 83, where `q`
        crosses 0.1. Every age from 0 to 100 is checked, so the regression
        cannot hide in the ages a sparser grid would skip.
        """
        dt = 24.0 / 8760.0
        for age in range(0, 101):
            annual_q = annual_mortality_probability(age, PRE_INDUSTRIAL_PARAMS)
            tick_q = tick_mortality_probability(age, PRE_INDUSTRIAL_PARAMS, tick_duration_hours=24)
            expected = 1.0 - (1.0 - annual_q) ** dt
            assert tick_q == pytest.approx(expected, rel=1e-12), (
                f"age {age}: tick probability {tick_q} is not the geometric "
                f"conversion {expected} of the annual {annual_q}"
            )

    def test_geometric_branch_dt_one(self):
        """With annual_q=0.25 and dt=1.0 the geometric branch returns exactly 0.25.

        1 - (1 - 0.25)^1 = 0.25. This verifies that the branch is triggered
        for q > 0.1 and applies the correct formula.
        """
        # Craft custom params that produce exactly annual_q = 0.25.
        # annual_q = qop / (1 + qop); 0.25 = qop / (1.25) => qop = 1/3.
        # We use an effective param set that yields qop ≈ 1/3 via c1 alone.
        # Simplest: A^((x+B)^C) ≈ 1/3 with x=50, B=0, C=1 -> A^50 = 1/3
        # But that is hard to control. Instead we test the branch condition
        # indirectly by using age=0 where pre-industrial infant mortality is
        # large enough to activate it.
        #
        # Direct approach: we call tick_mortality_probability with dt exactly
        # 8760 hours (1 year). For annual_q = q_annual:
        # geometric: 1 - (1 - q_annual)^1 = q_annual.
        # So tick output must equal annual output when dt==1.
        for age in (0, 1):
            annual_q = annual_mortality_probability(age, PRE_INDUSTRIAL_PARAMS)
            tick_q = tick_mortality_probability(
                age, PRE_INDUSTRIAL_PARAMS, tick_duration_hours=8760
            )
            # Both branches collapse to annual_q when dt=1
            assert abs(tick_q - annual_q) < 1e-9, (
                f"tick_q={tick_q} != annual_q={annual_q} at age {age} with dt=1"
            )

    def test_geometric_branch_half_year(self):
        """With annual_q=0.25 (q>=0.1) and dt=0.5 geometric branch gives 1-(0.75)^0.5.

        Expected: 1 - sqrt(0.75) ≈ 0.13397...
        Uses a controlled custom parameter set that produces exactly
        annual_q = 0.25 (by construction: A=1/3, B=0, C=1, D=G=0), so the
        geometric branch is guaranteed to trigger. This isolates branch
        selection from the specific calibrated parameter values.
        """
        # Custom params constructed to produce annual_q = 0.25 at age 1.
        # A^((1+0)^1) = 1/3; q_over_p = 1/3; q = (1/3)/(4/3) = 0.25.
        custom_params = {
            "A": 1.0 / 3.0,
            "B": 0.0,
            "C": 1.0,
            "D": 0.0,
            "E": 10.0,
            "F": 22.0,
            "G": 0.0,
            "H": 1.0,
        }
        annual_q = annual_mortality_probability(1, custom_params)
        # Confirm branch condition is met
        assert annual_q >= 0.1, f"Expected annual_q >= 0.1 for geometric branch, got {annual_q}"

        tick_q = tick_mortality_probability(1, custom_params, tick_duration_hours=4380)
        expected = 1.0 - (1.0 - annual_q) ** 0.5
        assert abs(tick_q - expected) < 1e-12, (
            f"Geometric half-year: tick_q={tick_q}, expected={expected}"
        )

    def test_known_q25_dt05(self):
        """Sanity check for a known large-q scenario: annual_q=0.25, dt=0.5.

        Expected: 1 - (0.75)^0.5 ≈ 0.1340. Tests the exact numeric result
        described in the plan specification.
        """
        # To get annual_q = 0.25 via HP we need qop = 1/3.
        # Use parameter set where only c1 is non-negligible: at x=1,
        # A^((1+B)^C) = 1/3. We pick B=0, C=1 then A^1 = 1/3, i.e. A=1/3.
        # D=0 (zero hump), G=0 (zero senescence).
        custom_params = {
            "A": 1.0 / 3.0,
            "B": 0.0,
            "C": 1.0,
            "D": 0.0,
            "E": 10.0,
            "F": 22.0,
            "G": 0.0,
            "H": 1.0,
        }
        # age=1, c1 = (1/3)^((1+0)^1) = 1/3; c2≈0; c3=0
        # q_over_p = 1/3; q = (1/3)/(1 + 1/3) = (1/3)/(4/3) = 1/4 = 0.25
        annual_q = annual_mortality_probability(1, custom_params)
        assert abs(annual_q - 0.25) < 1e-10, f"Expected annual_q=0.25, got {annual_q}"

        # dt = 0.5 years = 4380 hours
        tick_q = tick_mortality_probability(1, custom_params, tick_duration_hours=4380)
        expected = 1.0 - (1.0 - 0.25) ** 0.5
        assert abs(tick_q - expected) < 1e-12, f"tick_q={tick_q}, expected={expected}"
        # Approximately 0.134
        assert abs(tick_q - 0.13397459) < 1e-6, f"Expected ~0.1340, got {tick_q}"


# ---------------------------------------------------------------------------
# Task 23: sample_death_cause
# ---------------------------------------------------------------------------


class TestSampleDeathCause:
    """sample_death_cause label validity and age-stratified distribution."""

    def test_valid_label(self):
        """sample_death_cause always returns one of the three canonical labels."""
        rng = random.Random(42)
        for age in (0, 1, 5, 25, 50, 75, 80):
            label = sample_death_cause(age, PRE_INDUSTRIAL_PARAMS, rng)
            assert label in VALID_CAUSES, f"Unexpected cause label '{label}' at age {age}"

    def test_cause_distribution_age_2_skews_early_life(self):
        """At age 2 (child), >80% of sampled causes are early_life_mortality.

        Component c1 = A^((2+B)^C) >> c2, c3 for pre-industrial params:
        c1 ~ 0.004, c2 ~ 0 (accident hump peaks at ~22), c3 ~ 0.00005.
        """
        rng = random.Random(12345)
        n = 10_000
        counts: dict[str, int] = {label: 0 for label in VALID_CAUSES}
        for _ in range(n):
            label = sample_death_cause(2, PRE_INDUSTRIAL_PARAMS, rng)
            counts[label] += 1
        early_fraction = counts["early_life_mortality"] / n
        assert early_fraction > 0.80, (
            f"Expected >80% early_life_mortality at age 2, got {early_fraction:.1%}. "
            f"Distribution: {counts}"
        )

    def test_cause_distribution_age_75_skews_senescence(self):
        """At age 75 (elderly), >80% of sampled causes are natural_senescence.

        Component c3 = G*H^75 = 3.83e-5 * 1.101^75 >> c1, c2 for
        pre-industrial params: c3 ~ 0.052, c1 ~ 0.0003, c2 ~ 0.
        """
        rng = random.Random(99999)
        n = 10_000
        counts: dict[str, int] = {label: 0 for label in VALID_CAUSES}
        for _ in range(n):
            label = sample_death_cause(75, PRE_INDUSTRIAL_PARAMS, rng)
            counts[label] += 1
        senescence_fraction = counts["natural_senescence"] / n
        assert senescence_fraction > 0.80, (
            f"Expected >80% natural_senescence at age 75, got {senescence_fraction:.1%}. "
            f"Distribution: {counts}"
        )


# ---------------------------------------------------------------------------
# Task 24: fit_heligman_pollard
# ---------------------------------------------------------------------------


class TestFitHeligmanPollard:
    """fit_heligman_pollard round-trip accuracy, bound compliance, error handling."""

    # Ages used for fitting: 0..80, integer years
    FIT_AGES = list(range(0, 81))

    @pytest.fixture
    def synthetic_q(self):
        """Clean (noise-free) q(x) vector computed from the pre-industrial params."""
        return [annual_mortality_probability(age, PRE_INDUSTRIAL_PARAMS) for age in self.FIT_AGES]

    def test_round_trip_within_5pct(self, synthetic_q):
        """Recovered parameters are within 5% relative error of the true values.

        The fit uses the exact synthetic q(x) (no noise), initial guess
        equal to the true values to guarantee convergence in the test context.
        Relative tolerance: |fitted - true| / true < 0.05.

        Note: parameters close to their bound (like A=0.00491 approaching 0)
        can be harder to recover; the 5% tolerance accounts for that.
        """
        fitted = fit_heligman_pollard(
            self.FIT_AGES,
            synthetic_q,
            initial_guess=PRE_INDUSTRIAL_PARAMS,
        )
        for key in HP_PARAM_KEYS:
            true_val = PRE_INDUSTRIAL_PARAMS[key]
            fitted_val = fitted[key]
            # Relative tolerance: 5%
            rel_err = abs(fitted_val - true_val) / max(abs(true_val), 1e-12)
            assert rel_err < 0.05, (
                f"Parameter {key}: true={true_val}, fitted={fitted_val}, "
                f"relative error={rel_err:.2%} > 5%"
            )

    @pytest.mark.parametrize(
        "template_name",
        [
            "pre_industrial_christian",
            "pre_industrial_islamic",
            "industrial",
            "modern_democracy",
            "sci_fi",
        ],
    )
    def test_the_default_start_recovers_every_shipped_schedule(self, template_name):
        """From the default `p0`, each shipped template's own `q(x)` comes back.

        `sci_fi` carries `q` between 4.3e-6 and 8.3e-3 over ages 0-99. An unweighted fit of the
        absolute residuals stops as soon as they are small in absolute
        terms, which at those magnitudes is before the young ages fit at all:
        round 15 of the Plan 4 phase-6 gate measured a maximum relative error
        of 0.57 there, and 1.1e-5 under `modern_democracy`. The fit now
        minimises the relative deviations `q_hat / q - 1`, which weigh every
        age by its own magnitude.
        """
        from epocha.apps.demography.template_loader import load_template

        params = load_template(template_name)["mortality"]["heligman_pollard"]
        ages = list(range(0, 100))
        observed = [annual_mortality_probability(age, params) for age in ages]

        fitted = fit_heligman_pollard(ages, observed)

        worst = max(
            abs(annual_mortality_probability(age, fitted) - q) / q
            for age, q in zip(ages, observed, strict=True)
        )
        assert worst < 1e-6, f"{template_name}: max relative error {worst:.2e}"

    def test_a_zero_schedule_is_the_extreme_underdetermined_case(self):
        """A schedule of zeros leaves no age with `q > 0` in the fit.

        It is the limit of the case below, zero equations for eight unknowns,
        and §6.3 documents one error for it. A separate guard used to raise
        `RuntimeError` "did not converge" first, although no fit was ever
        attempted (scoped review of the round-16 closure).
        """
        with pytest.raises(UnderdeterminedFitError, match="got 0 ages"):
            fit_heligman_pollard(
                self.FIT_AGES,
                [0.0] * len(self.FIT_AGES),
            )

    @pytest.mark.parametrize("positive_ages", [1, 7])
    def test_fewer_positive_ages_than_parameters_raise(self, positive_ages):
        """Eight parameters need at least eight observed ages.

        The ages observed at `q = 0` are left out of the fit, so a schedule
        with fewer than eight positive values reaches `curve_fit` with more
        unknowns than equations. With bounds it uses the trust-region solver,
        which does not refuse that: round 16 of the Plan 4 phase-6 gate found
        it returning an underdetermined parameter set as if it were a fit.
        Seven positives is the edge; the other ages, at zero, keep the input
        as long as a real schedule.
        """
        observed = [0.0] * len(self.FIT_AGES)
        for age in range(positive_ages):
            observed[age] = annual_mortality_probability(age, PRE_INDUSTRIAL_PARAMS)

        with pytest.raises(UnderdeterminedFitError, match=f"{positive_ages} ages"):
            fit_heligman_pollard(self.FIT_AGES, observed)

    def test_eight_positive_ages_are_enough_to_fit(self):
        """The edge of the guard: eight observed ages are fitted, not refused.

        With as many ages as parameters the fit has no residual degree of
        freedom, so scipy cannot estimate the covariance and says so; the
        warning is the expected companion of the edge, not a defect.
        """
        from scipy.optimize import OptimizeWarning

        observed = [0.0] * len(self.FIT_AGES)
        for age in range(len(HP_PARAM_KEYS)):
            observed[age] = annual_mortality_probability(age, PRE_INDUSTRIAL_PARAMS)

        with pytest.warns(OptimizeWarning, match="Covariance"):
            fitted = fit_heligman_pollard(self.FIT_AGES, observed)

        assert set(fitted) == set(HP_PARAM_KEYS)

    def test_fitted_params_within_bounds(self, synthetic_q):
        """Fitted parameters satisfy the documented bounds: A>=0, H>=1.0.

        Bounds enforced by curve_fit: A in [0, 0.1], H in [1.0, 1.5].
        """
        fitted = fit_heligman_pollard(
            self.FIT_AGES,
            synthetic_q,
            initial_guess=PRE_INDUSTRIAL_PARAMS,
        )
        assert fitted["A"] >= 0.0, f"A must be >= 0, got {fitted['A']}"
        assert fitted["H"] >= 1.0, f"H must be >= 1.0, got {fitted['H']}"
        # Additional bound checks consistent with curve_fit lower/upper
        assert fitted["D"] >= 0.0, f"D must be >= 0, got {fitted['D']}"
        assert fitted["G"] >= 0.0, f"G must be >= 0, got {fitted['G']}"


# ---------------------------------------------------------------------------
# The domain of the per-tick conversion: a tick of at most one simulated year
# ---------------------------------------------------------------------------


class TestTickLongerThanAYear:
    """`dt` above one simulated year is rejected, not silently mis-compounded.

    With `q` held over each year of age, the ticks of one year compound back
    to exactly `q(x)` only while a tick fits inside a year of age: a tick of
    `dt > 1` years spans two ages and charges both at the first one's `q`.
    Round 15 of the Plan 4 phase-6 gate measured it: at yearly ticks under
    acceleration 2, `l(2)` came out 0.9426 against the life table's 0.9662.
    """

    def test_a_tick_of_two_simulated_years_is_rejected(self):
        from epocha.apps.demography.orchestrator import TickLongerThanAYearError

        with pytest.raises(TickLongerThanAYearError, match="2.0"):
            tick_mortality_probability(
                30, PRE_INDUSTRIAL_PARAMS, tick_duration_hours=8760, demography_acceleration=2.0
            )

    def test_a_tick_one_hour_longer_than_a_year_is_rejected(self):
        from epocha.apps.demography.orchestrator import TickLongerThanAYearError

        with pytest.raises(TickLongerThanAYearError):
            tick_mortality_probability(30, PRE_INDUSTRIAL_PARAMS, tick_duration_hours=8761)

    def test_a_tick_of_exactly_one_simulated_year_is_admitted(self):
        """The boundary belongs to the domain: half-year ticks at acceleration 2."""
        tick_q = tick_mortality_probability(
            30, PRE_INDUSTRIAL_PARAMS, tick_duration_hours=4380, demography_acceleration=2.0
        )

        assert tick_q == pytest.approx(annual_mortality_probability(30, PRE_INDUSTRIAL_PARAMS))

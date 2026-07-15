"""Tests for the CES production function.

The CES (Constant Elasticity of Substitution) function was introduced by
Arrow, Chenery, Minhas & Solow (1961). It generalizes Cobb-Douglas
(sigma=1) and Leontief (sigma->0) as special cases.
"""

from epocha.apps.economy.production import ces_production


class TestCESProduction:
    def test_zero_inputs_zero_output(self):
        # No inputs = no production
        result = ces_production(
            scale=10.0,
            sigma=0.5,
            factor_weights={"labor": 0.5, "capital": 0.5},
            factor_inputs={"labor": 0.0, "capital": 0.0},
        )
        assert result == 0.0

    def test_positive_output_with_inputs(self):
        result = ces_production(
            scale=10.0,
            sigma=0.5,
            factor_weights={"labor": 0.6, "capital": 0.4},
            factor_inputs={"labor": 1.0, "capital": 1.0},
        )
        assert result > 0.0

    def test_scale_parameter_multiplies_output(self):
        # Doubling A should double Q
        base = {"labor": 0.6, "capital": 0.4}
        inputs = {"labor": 1.0, "capital": 1.0}
        q1 = ces_production(
            scale=10.0,
            sigma=0.5,
            factor_weights=base,
            factor_inputs=inputs,
        )
        q2 = ces_production(
            scale=20.0,
            sigma=0.5,
            factor_weights=base,
            factor_inputs=inputs,
        )
        assert abs(q2 / q1 - 2.0) < 0.01

    def test_sigma_one_approximates_cobb_douglas(self):
        # At sigma=1, CES converges to Cobb-Douglas
        weights = {"labor": 0.6, "capital": 0.4}
        inputs = {"labor": 2.0, "capital": 3.0}
        ces_result = ces_production(
            scale=1.0,
            sigma=0.999,
            factor_weights=weights,
            factor_inputs=inputs,
        )
        # Cobb-Douglas: 1.0 * 2.0^0.6 * 3.0^0.4
        cd_result = 1.0 * (2.0**0.6) * (3.0**0.4)
        assert abs(ces_result - cd_result) / cd_result < 0.05

    def test_low_sigma_approaches_leontief(self):
        # At sigma->0, output limited by scarcest factor
        weights = {"labor": 0.5, "capital": 0.5}
        inputs_balanced = {"labor": 1.0, "capital": 1.0}
        inputs_unbalanced = {"labor": 1.0, "capital": 0.1}
        q_balanced = ces_production(
            scale=1.0,
            sigma=0.01,
            factor_weights=weights,
            factor_inputs=inputs_balanced,
        )
        q_unbalanced = ces_production(
            scale=1.0,
            sigma=0.01,
            factor_weights=weights,
            factor_inputs=inputs_unbalanced,
        )
        assert q_unbalanced < q_balanced * 0.5

    def test_weights_are_normalized(self):
        # Unnormalized weights should produce same result
        w_unnorm = {"labor": 3.0, "capital": 2.0}
        w_norm = {"labor": 0.6, "capital": 0.4}
        inputs = {"labor": 1.0, "capital": 1.0}
        q1 = ces_production(
            scale=10.0,
            sigma=0.5,
            factor_weights=w_unnorm,
            factor_inputs=inputs,
        )
        q2 = ces_production(
            scale=10.0,
            sigma=0.5,
            factor_weights=w_norm,
            factor_inputs=inputs,
        )
        assert abs(q1 - q2) < 0.01

    def test_three_factors(self):
        # CES works with 3+ factors (Arrow et al. 1961)
        weights = {"labor": 0.4, "capital": 0.3, "resources": 0.3}
        inputs = {"labor": 2.0, "capital": 1.5, "resources": 1.0}
        result = ces_production(
            scale=5.0,
            sigma=0.5,
            factor_weights=weights,
            factor_inputs=inputs,
        )
        assert result > 0.0

    def test_missing_factor_treated_as_zero(self):
        weights = {"labor": 0.6, "capital": 0.4}
        inputs = {"labor": 1.0}  # capital missing
        result = ces_production(
            scale=10.0,
            sigma=0.5,
            factor_weights=weights,
            factor_inputs=inputs,
        )
        # With one factor at zero, output depends on sigma
        assert result >= 0.0


class TestCESLeontiefLimit:
    """Regression tests for the Round 1 audit finding production/PROD-1.

    The general CES branch (lines 104-122) implements the normalized
    weighted-power-mean form Q = A * [sum(alpha_i * X_i^rho)]^(1/rho) with
    alpha_i normalized to sum to 1. As rho -> -inf (sigma -> 0), a weighted
    power mean converges to min(X_i): the distribution weights alpha_i only
    need to be positive, they vanish from the limit itself (Arrow, Chenery,
    Minhas & Solow 1961). The pre-fix Leontief branch instead returned
    A * min(alpha_i * X_i), which is neither this limit nor the standard
    fixed-coefficients Leontief form A * min(X_i / a_i); it introduced a
    10x discontinuity at sigma=_LEONTIEF_THRESHOLD for skewed weights.
    """

    def test_ces_leontief_limit_continuity(self):
        # alpha=[0.9, 0.1], X=[1.0, 1.0]: since every X_i == 1.0, X_i^rho == 1.0
        # for any rho, so the general branch collapses to scale * 1.0
        # regardless of sigma or the alpha weights. The Leontief branch must
        # agree with this value (continuity across sigma=_LEONTIEF_THRESHOLD)
        # and both must equal min(X_i)=1.0, not min(alpha_i * X_i)=0.1.
        weights = {"a": 0.9, "b": 0.1}
        inputs = {"a": 1.0, "b": 1.0}
        scale = 1.0
        epsilon = 1e-6

        general_branch = ces_production(
            scale=scale,
            sigma=0.06,  # just above _LEONTIEF_THRESHOLD (0.05): general CES
            factor_weights=weights,
            factor_inputs=inputs,
        )
        leontief_branch = ces_production(
            scale=scale,
            sigma=0.04,  # just below _LEONTIEF_THRESHOLD (0.05): Leontief limit
            factor_weights=weights,
            factor_inputs=inputs,
        )

        assert abs(general_branch - leontief_branch) < epsilon
        assert abs(general_branch - 1.0) < epsilon
        assert abs(leontief_branch - 1.0) < epsilon
        # Explicitly rule out the pre-fix bug value min(alpha_i * X_i) = 0.1.
        assert abs(leontief_branch - 0.1) > epsilon

    def test_ces_leontief_equals_min_inputs(self):
        # The Leontief branch must return A * min(X_i), independent of the
        # alpha weights: two very different weightings over the same inputs
        # must produce the identical result.
        inputs = {"a": 2.0, "b": 5.0}
        scale = 3.0
        sigma = 0.01  # below _LEONTIEF_THRESHOLD
        expected = scale * min(inputs.values())

        result_skewed_to_a = ces_production(
            scale=scale,
            sigma=sigma,
            factor_weights={"a": 0.9, "b": 0.1},
            factor_inputs=inputs,
        )
        result_skewed_to_b = ces_production(
            scale=scale,
            sigma=sigma,
            factor_weights={"a": 0.1, "b": 0.9},
            factor_inputs=inputs,
        )

        assert abs(result_skewed_to_a - expected) < 1e-9
        assert abs(result_skewed_to_b - expected) < 1e-9


class TestLeontiefSeamBound:
    """Round 3 re-audit finding R3-DIST-1 (run wf_af84ed13-dc3): the
    degenerate-point continuity test above (all X_i == 1.0) cannot
    measure the real branch seam, because every weighted power mean
    equals min(X_i) identically at that point. This test bounds the
    ACTUAL seam with heterogeneous inputs: the general CES evaluated
    just above _LEONTIEF_THRESHOLD (rho = (sigma-1)/sigma = -19 at the
    threshold sigma = 0.05 itself; -15.67 at the sigma = 0.06 used here)
    approaches min(X_i) from above, so the branch switch introduces a
    small positive discontinuity that must stay within a realistic
    tolerance (documented in production.py's Leontief-branch comment)."""

    def test_ces_leontief_seam_bounded_for_heterogeneous_inputs(self):
        weights = {"a": 0.9, "b": 0.1}
        inputs = {"a": 2.0, "b": 5.0}
        scale = 1.0

        general_branch = ces_production(
            scale=scale,
            sigma=0.06,
            factor_weights=weights,
            factor_inputs=inputs,
        )
        leontief_branch = ces_production(
            scale=scale,
            sigma=0.04,
            factor_weights=weights,
            factor_inputs=inputs,
        )

        assert leontief_branch == 2.0  # exact min(X_i)
        # Power mean converges to the min from above: seam is positive...
        assert general_branch >= leontief_branch
        # ...and bounded: below 1% relative at the current threshold.
        assert (general_branch - leontief_branch) / leontief_branch < 0.01

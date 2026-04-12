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
            scale=10.0, sigma=0.5,
            factor_weights={"labor": 0.5, "capital": 0.5},
            factor_inputs={"labor": 0.0, "capital": 0.0},
        )
        assert result == 0.0

    def test_positive_output_with_inputs(self):
        result = ces_production(
            scale=10.0, sigma=0.5,
            factor_weights={"labor": 0.6, "capital": 0.4},
            factor_inputs={"labor": 1.0, "capital": 1.0},
        )
        assert result > 0.0

    def test_scale_parameter_multiplies_output(self):
        # Doubling A should double Q
        base = {"labor": 0.6, "capital": 0.4}
        inputs = {"labor": 1.0, "capital": 1.0}
        q1 = ces_production(
            scale=10.0, sigma=0.5,
            factor_weights=base, factor_inputs=inputs,
        )
        q2 = ces_production(
            scale=20.0, sigma=0.5,
            factor_weights=base, factor_inputs=inputs,
        )
        assert abs(q2 / q1 - 2.0) < 0.01

    def test_sigma_one_approximates_cobb_douglas(self):
        # At sigma=1, CES converges to Cobb-Douglas
        weights = {"labor": 0.6, "capital": 0.4}
        inputs = {"labor": 2.0, "capital": 3.0}
        ces_result = ces_production(
            scale=1.0, sigma=0.999,
            factor_weights=weights, factor_inputs=inputs,
        )
        # Cobb-Douglas: 1.0 * 2.0^0.6 * 3.0^0.4
        cd_result = 1.0 * (2.0 ** 0.6) * (3.0 ** 0.4)
        assert abs(ces_result - cd_result) / cd_result < 0.05

    def test_low_sigma_approaches_leontief(self):
        # At sigma->0, output limited by scarcest factor
        weights = {"labor": 0.5, "capital": 0.5}
        inputs_balanced = {"labor": 1.0, "capital": 1.0}
        inputs_unbalanced = {"labor": 1.0, "capital": 0.1}
        q_balanced = ces_production(
            scale=1.0, sigma=0.01,
            factor_weights=weights,
            factor_inputs=inputs_balanced,
        )
        q_unbalanced = ces_production(
            scale=1.0, sigma=0.01,
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
            scale=10.0, sigma=0.5,
            factor_weights=w_unnorm, factor_inputs=inputs,
        )
        q2 = ces_production(
            scale=10.0, sigma=0.5,
            factor_weights=w_norm, factor_inputs=inputs,
        )
        assert abs(q1 - q2) < 0.01

    def test_three_factors(self):
        # CES works with 3+ factors (Arrow et al. 1961)
        weights = {"labor": 0.4, "capital": 0.3, "resources": 0.3}
        inputs = {"labor": 2.0, "capital": 1.5, "resources": 1.0}
        result = ces_production(
            scale=5.0, sigma=0.5,
            factor_weights=weights, factor_inputs=inputs,
        )
        assert result > 0.0

    def test_missing_factor_treated_as_zero(self):
        weights = {"labor": 0.6, "capital": 0.4}
        inputs = {"labor": 1.0}  # capital missing
        result = ces_production(
            scale=10.0, sigma=0.5,
            factor_weights=weights, factor_inputs=inputs,
        )
        # With one factor at zero, output depends on sigma
        assert result >= 0.0

"""Tests for monetary velocity update and wealth/mood feedback."""

from epocha.apps.economy.monetary import (
    _MOOD_BOOST_BASE,
    _POVERTY_THRESHOLD,
    aggregate_system_prices,
    compute_circulating_money_supply,
    compute_inflation,
    compute_mood_delta,
    compute_velocity,
    derive_mood_thresholds,
)


class TestComputeVelocity:
    def test_velocity_from_transaction_volume(self):
        # V = transaction_volume / M
        v = compute_velocity(transaction_volume=5000.0, money_supply=50000.0)
        assert abs(v - 0.1) < 0.001

    def test_zero_supply_returns_zero(self):
        v = compute_velocity(transaction_volume=100.0, money_supply=0.0)
        assert v == 0.0

    def test_zero_transactions_returns_zero(self):
        v = compute_velocity(transaction_volume=0.0, money_supply=50000.0)
        assert v == 0.0


class TestComputeInflation:
    def test_positive_inflation(self):
        # Prices went up
        old = {"subsistence": 3.0, "luxury": 50.0}
        new = {"subsistence": 3.3, "luxury": 55.0}
        rate = compute_inflation(old, new)
        assert rate > 0.0

    def test_deflation(self):
        old = {"subsistence": 3.0}
        new = {"subsistence": 2.7}
        rate = compute_inflation(old, new)
        assert rate < 0.0

    def test_stable_prices_zero_inflation(self):
        prices = {"subsistence": 3.0, "luxury": 50.0}
        rate = compute_inflation(prices, prices)
        assert abs(rate) < 0.001

    def test_empty_prices(self):
        rate = compute_inflation({}, {})
        assert rate == 0.0


class TestComputeMoodDelta:
    def test_wealthy_agent_small_boost(self):
        # Kahneman & Deaton (2010): diminishing returns above satiation
        delta = compute_mood_delta(wealth=200.0, satiation_threshold=100.0)
        assert delta > 0.0
        assert delta < 0.02  # should be small (diminishing)

    def test_very_wealthy_near_zero_boost(self):
        delta = compute_mood_delta(wealth=1000.0, satiation_threshold=100.0)
        assert delta > 0.0
        assert delta < 0.005  # almost zero (plateau)

    def test_poor_agent_penalty(self):
        delta = compute_mood_delta(wealth=5.0, satiation_threshold=100.0)
        assert delta < 0.0

    def test_destitute_agent_severe_penalty(self):
        delta = compute_mood_delta(wealth=-10.0, satiation_threshold=100.0)
        assert delta < -0.05

    def test_moderate_wealth_no_change(self):
        delta = compute_mood_delta(wealth=50.0, satiation_threshold=100.0)
        # Moderate wealth: slight positive or near zero
        assert abs(delta) < 0.05

    def test_poverty_threshold_is_a_parameter(self):
        # CM-6 fix: poverty_threshold must be overridable like
        # satiation_threshold, not hardcoded to the module constant,
        # so callers can pass a wealth-scale-reconciled value.
        delta_below_custom_threshold = compute_mood_delta(
            wealth=40.0,
            satiation_threshold=1000.0,
            poverty_threshold=50.0,
        )
        assert delta_below_custom_threshold < 0.0

        delta_above_custom_threshold = compute_mood_delta(
            wealth=40.0,
            satiation_threshold=1000.0,
            poverty_threshold=10.0,
        )
        assert delta_above_custom_threshold >= 0.0


class TestComputeCirculatingMoneySupply:
    """CM-2 fix: live money supply M is the aggregate of circulating
    cash across agents in one currency, not a static template constant
    (Round 1 audit report, cross-module CM-2)."""

    def test_sums_cash_for_given_currency_only(self):
        balances = [
            {"LVR": 100.0, "GBP": 999.0},
            {"LVR": 50.0},
            {},
        ]
        total = compute_circulating_money_supply(balances, "LVR")
        assert abs(total - 150.0) < 1e-9

    def test_ignores_other_currencies(self):
        balances = [{"GBP": 500.0}]
        total = compute_circulating_money_supply(balances, "LVR")
        assert total == 0.0

    def test_empty_list_returns_zero(self):
        assert compute_circulating_money_supply([], "LVR") == 0.0


class TestAggregateSystemPrices:
    """CM-5 fix: system prices are a genuine cross-zone aggregate, not
    a last-zone-wins dict.update() merge (Round 1 audit report,
    cross-module CM-5)."""

    def test_averages_across_zones_not_last_zone_wins(self):
        zone_prices = [
            {"subsistence": 3.0, "luxury": 50.0},
            {"subsistence": 9.0},
        ]
        result = aggregate_system_prices(zone_prices)
        # Mean of 3.0 and 9.0 = 6.0. A last-zone-wins merge would
        # instead return 9.0 (or 3.0, depending on iteration order).
        assert abs(result["subsistence"] - 6.0) < 1e-9
        assert abs(result["luxury"] - 50.0) < 1e-9

    def test_empty_list_returns_empty_dict(self):
        assert aggregate_system_prices([]) == {}

    def test_single_zone_returns_that_zones_price(self):
        result = aggregate_system_prices([{"subsistence": 4.0}])
        assert result == {"subsistence": 4.0}


class TestDeriveMoodThresholds:
    """CM-6 fix: poverty/satiation thresholds are derived from the
    population's median wealth instead of fixed absolute constants
    disconnected from the template's wealth scale (Round 1 audit
    report, monetary+initialization cross-module finding)."""

    def test_thresholds_bracket_the_median(self):
        # By construction (poverty = 0.5*median, satiation =
        # 1.5*median) the median wealth itself always falls strictly
        # between the two thresholds, for any positive median.
        poverty, satiation = derive_mood_thresholds(median_wealth=200.0)
        assert poverty < 200.0 < satiation

    def test_mid_wealth_agent_neither_satiated_nor_poor(self):
        median_wealth = 200.0
        poverty, satiation = derive_mood_thresholds(median_wealth)
        delta = compute_mood_delta(
            wealth=median_wealth,
            satiation_threshold=satiation,
            poverty_threshold=poverty,
        )
        # Moderate-wealth band: the fixed small positive delta, not
        # the poverty penalty and not the satiation-plateau boost.
        assert delta == _MOOD_BOOST_BASE * 0.5

    def test_thresholds_scale_with_template_wealth(self):
        # A sci-fi-scale economy (median wealth in the thousands) must
        # not inherit the pre-industrial-scale absolute satiation=100:
        # that would auto-satiate every agent regardless of their
        # relative position in the population.
        _, satiation_small = derive_mood_thresholds(median_wealth=50.0)
        _, satiation_large = derive_mood_thresholds(median_wealth=5000.0)
        assert satiation_large > satiation_small

    def test_degenerate_zero_median_falls_back_to_defaults(self):
        poverty, satiation = derive_mood_thresholds(median_wealth=0.0)
        assert poverty == _POVERTY_THRESHOLD
        assert satiation == 100.0

    def test_negative_median_falls_back_to_defaults(self):
        poverty, satiation = derive_mood_thresholds(median_wealth=-5.0)
        assert poverty == _POVERTY_THRESHOLD
        assert satiation == 100.0

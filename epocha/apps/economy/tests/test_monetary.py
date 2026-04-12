"""Tests for monetary velocity update and wealth/mood feedback."""

from epocha.apps.economy.monetary import (
    compute_inflation,
    compute_mood_delta,
    compute_velocity,
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

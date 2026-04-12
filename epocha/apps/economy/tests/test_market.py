"""Tests for Walrasian tatonnement market clearing.

Source: Walras (1874) for the mechanism. Scarf (1960) for the
non-convergence caveat. Shoven & Whalley (1992) ch. 4 for applied
CGE practice.
"""

from epocha.apps.economy.market import (
    tatonnement_prices,
)


class TestTatonnementPrices:
    def test_excess_demand_raises_price(self):
        prices = {"subsistence": 3.0}
        supply = {"subsistence": 100.0}
        demand = {"subsistence": 150.0}
        new_prices, converged = tatonnement_prices(prices, supply, demand)
        assert new_prices["subsistence"] > 3.0

    def test_excess_supply_lowers_price(self):
        prices = {"subsistence": 3.0}
        supply = {"subsistence": 150.0}
        demand = {"subsistence": 100.0}
        new_prices, converged = tatonnement_prices(prices, supply, demand)
        assert new_prices["subsistence"] < 3.0

    def test_balanced_market_converges(self):
        prices = {"subsistence": 3.0}
        supply = {"subsistence": 100.0}
        demand = {"subsistence": 100.0}
        new_prices, converged = tatonnement_prices(prices, supply, demand)
        assert converged is True
        assert abs(new_prices["subsistence"] - 3.0) < 0.01

    def test_multiple_goods(self):
        prices = {"subsistence": 3.0, "luxury": 50.0}
        supply = {"subsistence": 100.0, "luxury": 10.0}
        demand = {"subsistence": 120.0, "luxury": 5.0}
        new_prices, converged = tatonnement_prices(prices, supply, demand)
        assert new_prices["subsistence"] > 3.0  # excess demand
        assert new_prices["luxury"] < 50.0  # excess supply

    def test_zero_supply_uses_epsilon_floor(self):
        prices = {"subsistence": 3.0}
        supply = {"subsistence": 0.0}
        demand = {"subsistence": 50.0}
        new_prices, converged = tatonnement_prices(prices, supply, demand)
        # Price should rise significantly but not to infinity
        assert new_prices["subsistence"] > 3.0
        assert new_prices["subsistence"] < 10000.0

    def test_prices_never_negative(self):
        prices = {"subsistence": 0.1}
        supply = {"subsistence": 1000.0}
        demand = {"subsistence": 1.0}
        new_prices, _ = tatonnement_prices(prices, supply, demand)
        assert new_prices["subsistence"] > 0.0

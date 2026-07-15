"""Tests for Walrasian tatonnement market clearing.

Source: Walras (1874) for the mechanism. Scarf (1960) for the
non-convergence caveat. Shoven & Whalley (1992) ch. 4 for applied
CGE practice.
"""

from epocha.apps.economy import market
from epocha.apps.economy.market import (
    collect_supply_and_demand,
    execute_trades,
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

    def test_zero_supply_price_ceiling_uses_base_prices_anchor(self):
        """MKT-6: the zero-supply branch must anchor MAX_PRICE_RATIO to the
        same reference as the main branch (base_prices when supplied), not
        to this tick's already-inflated starting price.

        current_prices is deliberately set high (150.0) to simulate a prior
        tick's inflated price, while base_prices (the template's calibrated
        reference) is low (1.0). Anchoring to base_prices caps the single
        1.1x bump at base_prices*MAX_PRICE_RATIO = 100.0. Anchoring to
        initial_prices (the pre-fix behavior) would allow up to
        150.0*MAX_PRICE_RATIO = 15000.0, so the bumped price 165.0 would
        pass through uncapped -- the two anchors are only distinguishable
        because the ceiling actually binds in this scenario.
        """
        prices = {"rare": 150.0}
        base_prices = {"rare": 1.0}
        supply = {"rare": 0.0}
        demand = {"rare": 50.0}
        new_prices, _ = tatonnement_prices(prices, supply, demand, base_prices=base_prices)
        assert abs(new_prices["rare"] - 100.0) < 0.01


class TestExecuteTrades:
    """MKT-2: realized trade volume must conserve quantity.

    Source: in any market-clearing model (Walras 1874; Shoven & Whalley
    1992), realized trade of a good equals min(aggregate supply, aggregate
    demand), rationed across the short side so that sum(buyer purchases) ==
    sum(seller sales) == the cleared quantity. Pre-fix, execute_trades
    matched every buyer against every seller without decrementing running
    totals, so aggregate matched volume scaled with N*M instead of being
    capped at min(supply, demand).
    """

    def test_execute_trades_conserves_quantity(self):
        agent_orders = [
            {"agent_id": "b1", "offers": {}, "wants": {"wheat": 10.0}},
            {"agent_id": "b2", "offers": {}, "wants": {"wheat": 20.0}},
            {"agent_id": "b3", "offers": {}, "wants": {"wheat": 5.0}},
            {"agent_id": "s1", "offers": {"wheat": 15.0}, "wants": {}},
            {"agent_id": "s2", "offers": {"wheat": 10.0}, "wants": {}},
        ]
        total_supply = {"wheat": 25.0}
        total_demand = {"wheat": 35.0}
        equilibrium_prices = {"wheat": 2.0}

        trades = execute_trades(agent_orders, equilibrium_prices, total_supply, total_demand)

        total_traded = sum(t["quantity"] for t in trades)
        assert abs(total_traded - min(25.0, 35.0)) < 0.01

        sold_per_seller: dict[str, float] = {}
        bought_per_buyer: dict[str, float] = {}
        for t in trades:
            seller_id, buyer_id, qty = t["seller_id"], t["buyer_id"], t["quantity"]
            sold_per_seller[seller_id] = sold_per_seller.get(seller_id, 0.0) + qty
            bought_per_buyer[buyer_id] = bought_per_buyer.get(buyer_id, 0.0) + qty

        # No seller sells more than it offered.
        assert sold_per_seller.get("s1", 0.0) <= 15.0 + 1e-6
        assert sold_per_seller.get("s2", 0.0) <= 10.0 + 1e-6
        # No buyer buys more than it wanted.
        assert bought_per_buyer.get("b1", 0.0) <= 10.0 + 1e-6
        assert bought_per_buyer.get("b2", 0.0) <= 20.0 + 1e-6
        assert bought_per_buyer.get("b3", 0.0) <= 5.0 + 1e-6

    def test_execute_trades_short_side_rationing(self):
        """Excess demand rations every buyer to demand_ratio of its want;
        excess supply rations every seller to supply_ratio of its offer.

        Two sellers (and two buyers) per good are required to expose the
        pre-fix N*M duplication: with only one seller, the buggy double
        loop degenerates to N*1 and accidentally matches the correct
        target, hiding the defect (verified while designing this test).
        With two counterparties per side, running-totals matching is the
        only way to hit the exact target volumes below.
        """
        agent_orders = [
            {"agent_id": "b1", "offers": {}, "wants": {"wheat": 10.0, "wine": 4.0}},
            {"agent_id": "b2", "offers": {}, "wants": {"wheat": 30.0, "wine": 4.0}},
            {"agent_id": "s1", "offers": {"wheat": 12.0, "wine": 6.0}, "wants": {}},
            {"agent_id": "s2", "offers": {"wheat": 8.0, "wine": 4.0}, "wants": {}},
        ]
        total_supply = {"wheat": 20.0, "wine": 10.0}
        total_demand = {"wheat": 40.0, "wine": 8.0}
        equilibrium_prices = {"wheat": 1.0, "wine": 1.0}

        trades = execute_trades(agent_orders, equilibrium_prices, total_supply, total_demand)

        bought: dict[tuple[str, str], float] = {}
        sold: dict[tuple[str, str], float] = {}
        for t in trades:
            bought[(t["buyer_id"], t["good_code"])] = (
                bought.get((t["buyer_id"], t["good_code"]), 0.0) + t["quantity"]
            )
            sold[(t["seller_id"], t["good_code"])] = (
                sold.get((t["seller_id"], t["good_code"]), 0.0) + t["quantity"]
            )

        # wheat: demand(40) > supply(20) -> traded=20, demand_ratio=0.5,
        # supply_ratio=1.0. Each buyer keeps exactly half its want; each
        # seller sells its whole offer (sum of offers == supply == traded).
        assert abs(bought.get(("b1", "wheat"), 0.0) - 5.0) < 0.01
        assert abs(bought.get(("b2", "wheat"), 0.0) - 15.0) < 0.01
        assert abs(sold.get(("s1", "wheat"), 0.0) - 12.0) < 0.01
        assert abs(sold.get(("s2", "wheat"), 0.0) - 8.0) < 0.01

        # wine: supply(10) > demand(8) -> traded=8, demand_ratio=1.0,
        # supply_ratio=0.8. Both buyers are fully served; each seller
        # sells exactly 80% of its offer.
        assert abs(bought.get(("b1", "wine"), 0.0) - 4.0) < 0.01
        assert abs(bought.get(("b2", "wine"), 0.0) - 4.0) < 0.01
        assert abs(sold.get(("s1", "wine"), 0.0) - 4.8) < 0.01
        assert abs(sold.get(("s2", "wine"), 0.0) - 3.2) < 0.01


class TestCollectSupplyAndDemandDiscretionary:
    """MKT-5: discretionary (non-essential) demand must be budget-constrained.

    Source: price elasticity of demand is the dimensionless response
    dQ/dP * P/Q (e.g. constant-elasticity demand Q = A*P^(-e)); it is not
    a divisor on quantity. Pre-fix, discretionary demand was computed
    independently per non-essential good on the agent's FULL cash, so total
    spend across K non-essential goods could reach ~0.1*K*cash, exceeding
    cash with no cross-good budget constraint.
    """

    def test_discretionary_demand_respects_budget(self):
        good_categories = [
            {"code": "wine", "is_essential": False, "price_elasticity": 0.5},
            {"code": "jewelry", "is_essential": False, "price_elasticity": 2.0},
            {"code": "art", "is_essential": False, "price_elasticity": 5.0},
        ]
        agent_inventories = [
            {
                "agent_id": 1,
                "holdings": {},
                "cash_amount": 1000.0,
                "is_hoarding": False,
            }
        ]
        market_prices = {"wine": 10.0, "jewelry": 50.0, "art": 200.0}

        _, _, agent_orders = collect_supply_and_demand(
            agent_inventories, good_categories, market_prices
        )

        wants = agent_orders[0]["wants"]
        total_spend = sum(qty * market_prices[code] for code, qty in wants.items())
        budget = 1000.0 * market._DISCRETIONARY_SPEND_FRACTION
        assert total_spend <= budget + 1e-6

"""Tests for rent, wage, and tax distribution."""

from epocha.apps.economy.distribution import (
    compute_profit,
    compute_rent,
    compute_taxes,
    compute_wages,
    partition_output_value,
)


class TestComputeRent:
    def test_rent_proportional_to_bonus(self):
        # Property with 1.5x bonus gets 1.5x share
        zone_production = {"subsistence": 100.0}
        properties = [
            {"owner_id": 1, "production_bonus": {"subsistence": 1.5}},
            {"owner_id": 2, "production_bonus": {"subsistence": 1.0}},
        ]
        prices = {"subsistence": 3.0}
        rents = compute_rent(zone_production, properties, prices)
        assert rents[1] > rents[2]
        # Owner 1: 60% (1.5/2.5), Owner 2: 40% (1.0/2.5)
        total = rents[1] + rents[2]
        assert abs(rents[1] / total - 0.6) < 0.01

    def test_no_properties_no_rent(self):
        rents = compute_rent(
            {"subsistence": 100.0},
            [],
            {"subsistence": 3.0},
        )
        assert rents == {}

    def test_zero_production_zero_rent(self):
        properties = [
            {"owner_id": 1, "production_bonus": {"subsistence": 1.5}},
        ]
        rents = compute_rent(
            {"subsistence": 0.0},
            properties,
            {"subsistence": 3.0},
        )
        assert rents.get(1, 0.0) == 0.0


class TestComputeWages:
    def test_wage_is_share_of_output_value(self):
        agent_outputs = [
            {
                "agent_id": 1,
                "good_code": "subsistence",
                "quantity": 10.0,
                "owns_property": False,
            }
        ]
        prices = {"subsistence": 3.0}
        wages = compute_wages(agent_outputs, prices, wage_share=0.6)
        # 10 * 3.0 * 0.6 = 18.0
        assert abs(wages[1] - 18.0) < 0.01

    def test_property_owner_gets_wage_share_not_full_value(self):
        # CM-1 / distribution PROD-2 fix: paying a property owner the
        # FULL output value as "wage" on top of a separate rent share
        # double-counted the same output value (Round 1 audit report,
        # distribution/PROD-2). compute_wages no longer special-cases
        # owners: everyone earns wage_share of their own output value;
        # an owner's land/capital income comes from compute_rent /
        # compute_profit instead, not from wages.
        agent_outputs = [
            {
                "agent_id": 1,
                "good_code": "subsistence",
                "quantity": 10.0,
                "owns_property": True,
            }
        ]
        prices = {"subsistence": 3.0}
        wages = compute_wages(agent_outputs, prices, wage_share=0.6)
        # Labor share only: 10 * 3.0 * 0.6 = 18.0, not the full 30.0.
        assert abs(wages[1] - 18.0) < 0.01
        assert wages[1] < 10.0 * 3.0

    def test_zero_output_zero_wage(self):
        agent_outputs = [
            {
                "agent_id": 1,
                "good_code": "subsistence",
                "quantity": 0.0,
                "owns_property": False,
            }
        ]
        wages = compute_wages(
            agent_outputs,
            {"subsistence": 3.0},
            wage_share=0.6,
        )
        assert wages.get(1, 0.0) == 0.0


class TestFactorSharesConservation:
    """Approach A conservation rewrite (CM-1 / distribution PROD-2).

    Classical/national-accounting identity: a zone's output value V
    is PARTITIONED among rent + wages + profit (Ricardo 1817), not
    paid out in full to each factor independently. Round 1 audit
    report, distribution/PROD-2 and cross-module CM-1: the previous
    implementation credited compute_rent's full output value AND
    compute_wages' (owner: full value, worker: wage_share*value) as
    two independent brand-new-cash injections, strictly exceeding V
    every tick.
    """

    def test_factor_shares_partition_output_value(self):
        # Two goods: "subsistence" has a property owner claiming its
        # full production_bonus (exercises the owner-proportional
        # branch of rent/profit); "luxury" has no property claiming
        # it at all (exercises the no-landlord fallback branch, where
        # profit absorbs the otherwise-unclaimed rent_share too).
        zone_production = {"subsistence": 100.0, "luxury": 20.0}
        prices = {"subsistence": 3.0, "luxury": 50.0}
        properties = [
            {"owner_id": 10, "production_bonus": {"subsistence": 1.0}},
        ]
        agent_outputs = [
            {"agent_id": 1, "good_code": "subsistence", "quantity": 60.0},
            {"agent_id": 10, "good_code": "subsistence", "quantity": 40.0},
            {"agent_id": 2, "good_code": "luxury", "quantity": 20.0},
        ]
        wage_share, rent_share, profit_share = 0.6, 0.15, 0.25

        shares = partition_output_value(
            zone_production,
            properties,
            agent_outputs,
            prices,
            wage_share=wage_share,
            rent_share=rent_share,
            profit_share=profit_share,
        )

        subsistence_value = zone_production["subsistence"] * prices["subsistence"]
        output_value = sum(zone_production[g] * prices[g] for g in zone_production)
        total_rent = sum(shares["rent"].values())
        total_wages = sum(shares["wages"].values())
        total_profit = sum(shares["profit"].values())

        # Wages apply uniformly to every good's producers regardless of
        # ownership, so total wages scale with the FULL output value V.
        assert abs(total_wages - wage_share * output_value) < 1e-6
        # Rent only exists for goods a property claims (subsistence);
        # "luxury" has no landlord, so rent does NOT scale with V.
        assert abs(total_rent - rent_share * subsistence_value) < 1e-6
        # The three legs still partition the FULL V exactly (they do
        # NOT each independently equal V, which was the CM-1 symptom).
        assert abs((total_rent + total_wages + total_profit) - output_value) < 1e-6
        # None of the three legs alone reaches V (the old double-payment
        # symptom: e.g. rent alone used to equal the full V).
        assert total_rent < output_value
        assert total_wages < output_value
        assert total_profit < output_value

    def test_owner_not_double_paid(self):
        # A producing owner must not receive both the full output
        # value as "wage" AND a separate rent/profit share on the same
        # output (the CM-1 symptom). Their total factor income across
        # rent + wages + profit is bounded by the legitimate per-factor
        # shares of V, never by the full value twice over.
        zone_production = {"subsistence": 100.0}
        prices = {"subsistence": 3.0}
        properties = [
            {"owner_id": 10, "production_bonus": {"subsistence": 1.0}},
        ]
        agent_outputs = [
            {"agent_id": 10, "good_code": "subsistence", "quantity": 40.0},
        ]
        wage_share, rent_share, profit_share = 0.6, 0.15, 0.25

        shares = partition_output_value(
            zone_production,
            properties,
            agent_outputs,
            prices,
            wage_share=wage_share,
            rent_share=rent_share,
            profit_share=profit_share,
        )
        owner_total = (
            shares["rent"].get(10, 0.0)
            + shares["wages"].get(10, 0.0)
            + shares["profit"].get(10, 0.0)
        )

        output_value = zone_production["subsistence"] * prices["subsistence"]
        own_output_value = 40.0 * 3.0
        # Old buggy formula: full own_output_value (as "wage") + full
        # output_value (as sole owner's rent) = 120.0 + 300.0 = 420.0.
        old_buggy_total = own_output_value + output_value
        assert owner_total < old_buggy_total
        # Owner is sole property owner (100% bonus share), so they
        # collect the full rent_share*V + profit_share*V, plus their
        # own wage_share*own_output_value:
        # 0.15*300 + 0.25*300 + 0.6*120 = 45 + 75 + 72 = 192.0.
        assert abs(owner_total - 192.0) < 1e-6

    def test_compute_profit_no_owner_absorbs_full_residual(self):
        # A good with no property claiming a production_bonus has no
        # capital owner: the producing agent retains BOTH the profit
        # share and the otherwise-unclaimed rent share for that good.
        zone_production = {"luxury": 20.0}
        prices = {"luxury": 50.0}
        agent_outputs = [
            {"agent_id": 2, "good_code": "luxury", "quantity": 20.0},
        ]
        profit = compute_profit(
            zone_production,
            properties=[],
            agent_outputs=agent_outputs,
            prices=prices,
            profit_share=0.25,
            rent_share=0.15,
        )
        # (rent_share + profit_share) * V = 0.40 * 1000.0 = 400.0
        assert abs(profit[2] - 400.0) < 1e-6

    def test_partition_clamps_when_shares_exceed_one(self):
        # A misconfigured template where wage_share + rent_share already
        # reaches or exceeds 1 leaves no room for a positive profit
        # share. partition_output_value clamps rent_share down to the
        # residual (1 - wage_share) and profit_share to 0 rather than
        # crediting more than V (logs a warning; does not raise).
        zone_production = {"subsistence": 100.0}
        prices = {"subsistence": 3.0}
        properties = [
            {"owner_id": 10, "production_bonus": {"subsistence": 1.0}},
        ]
        agent_outputs = [
            {"agent_id": 10, "good_code": "subsistence", "quantity": 100.0},
        ]

        shares = partition_output_value(
            zone_production,
            properties,
            agent_outputs,
            prices,
            wage_share=0.7,
            rent_share=0.5,  # 0.7 + 0.5 = 1.2 > 1.0
        )

        output_value = zone_production["subsistence"] * prices["subsistence"]
        total_rent = sum(shares["rent"].values())
        total_wages = sum(shares["wages"].values())
        total_profit = sum(shares["profit"].values())

        assert total_profit == 0.0
        # Clamped rent_share = 1 - 0.7 = 0.3, so total = V exactly still.
        assert abs((total_rent + total_wages + total_profit) - output_value) < 1e-6


class TestComputeTaxes:
    def test_tax_is_rate_times_income(self):
        agent_incomes = {1: 100.0, 2: 50.0}
        taxes = compute_taxes(agent_incomes, tax_rate=0.15)
        assert abs(taxes["agent_taxes"][1] - 15.0) < 0.01
        assert abs(taxes["agent_taxes"][2] - 7.5) < 0.01
        assert abs(taxes["total_revenue"] - 22.5) < 0.01

    def test_zero_rate_zero_tax(self):
        taxes = compute_taxes({1: 100.0}, tax_rate=0.0)
        assert taxes["agent_taxes"][1] == 0.0
        assert taxes["total_revenue"] == 0.0

    def test_no_agents_no_tax(self):
        taxes = compute_taxes({}, tax_rate=0.15)
        assert taxes["total_revenue"] == 0.0

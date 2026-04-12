"""Tests for rent, wage, and tax distribution."""

from epocha.apps.economy.distribution import (
    compute_rent,
    compute_taxes,
    compute_wages,
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
            {"subsistence": 100.0}, [], {"subsistence": 3.0},
        )
        assert rents == {}

    def test_zero_production_zero_rent(self):
        properties = [
            {"owner_id": 1, "production_bonus": {"subsistence": 1.5}},
        ]
        rents = compute_rent(
            {"subsistence": 0.0}, properties, {"subsistence": 3.0},
        )
        assert rents.get(1, 0.0) == 0.0


class TestComputeWages:
    def test_wage_is_share_of_output_value(self):
        agent_outputs = [{
            "agent_id": 1, "good_code": "subsistence",
            "quantity": 10.0, "owns_property": False,
        }]
        prices = {"subsistence": 3.0}
        wages = compute_wages(agent_outputs, prices, wage_share=0.6)
        # 10 * 3.0 * 0.6 = 18.0
        assert abs(wages[1] - 18.0) < 0.01

    def test_property_owner_gets_full_value(self):
        agent_outputs = [{
            "agent_id": 1, "good_code": "subsistence",
            "quantity": 10.0, "owns_property": True,
        }]
        prices = {"subsistence": 3.0}
        wages = compute_wages(agent_outputs, prices, wage_share=0.6)
        # Owner keeps full value: 10 * 3.0 = 30.0
        assert abs(wages[1] - 30.0) < 0.01

    def test_zero_output_zero_wage(self):
        agent_outputs = [{
            "agent_id": 1, "good_code": "subsistence",
            "quantity": 0.0, "owns_property": False,
        }]
        wages = compute_wages(
            agent_outputs, {"subsistence": 3.0}, wage_share=0.6,
        )
        assert wages.get(1, 0.0) == 0.0


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

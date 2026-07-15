"""Integration tests for the economy tick pipeline.

Tests the full 7-step pipeline on a minimal scenario with real
DB models.
"""

from unittest.mock import patch

import pytest
from django.contrib.gis.geos import Point, Polygon

import epocha.apps.economy.engine as engine_module
from epocha.apps.agents.models import Agent
from epocha.apps.economy.engine import process_economy_tick_new
from epocha.apps.economy.models import (
    AgentInventory,
    Currency,
    EconomicLedger,
    GoodCategory,
    PriceHistory,
    ProductionFactor,
    Property,
    TaxPolicy,
    ZoneEconomy,
)
from epocha.apps.simulation.models import Simulation
from epocha.apps.users.models import User
from epocha.apps.world.models import Government, World, Zone


@pytest.fixture
def user(db):
    return User.objects.create_user(
        email="eng@epocha.dev",
        username="enguser",
        password="pass1234",
    )


@pytest.fixture
def simulation(user):
    return Simulation.objects.create(
        name="EngineTest",
        seed=42,
        owner=user,
    )


@pytest.fixture
def setup_economy(simulation):
    """Create a minimal but complete economic scenario."""
    world = World.objects.create(
        simulation=simulation,
        distance_scale=133.0,
        tick_duration_hours=24.0,
    )
    gov = Government.objects.create(
        simulation=simulation,
        government_type="monarchy",
        government_treasury={},
    )

    # Currency
    currency = Currency.objects.create(
        simulation=simulation,
        code="LVR",
        name="Livre",
        symbol="L",
        is_primary=True,
        total_supply=10000.0,
    )

    # Goods
    subsistence = GoodCategory.objects.create(
        simulation=simulation,
        code="subsistence",
        name="Subsistence",
        is_essential=True,
        base_price=3.0,
        price_elasticity=0.3,
    )
    luxury = GoodCategory.objects.create(
        simulation=simulation,
        code="luxury",
        name="Luxury",
        is_essential=False,
        base_price=50.0,
        price_elasticity=2.0,
    )

    # Factors
    ProductionFactor.objects.create(
        simulation=simulation,
        code="labor",
        name="Labor",
    )
    ProductionFactor.objects.create(
        simulation=simulation,
        code="capital",
        name="Capital",
    )

    # Tax
    TaxPolicy.objects.create(
        simulation=simulation,
        income_tax_rate=0.15,
    )

    # Zone
    zone = Zone.objects.create(
        world=world,
        name="Paris",
        zone_type="urban",
        boundary=Polygon.from_bbox((0, 0, 100, 100)),
        center=Point(50, 50),
    )
    sub_factors = {"labor": 0.6, "capital": 0.4}
    lux_factors = {"labor": 0.3, "capital": 0.7}
    ze = ZoneEconomy.objects.create(
        zone=zone,
        natural_resources={
            "labor": 1.0,
            "capital": 0.5,
            "natural_resources": 0.3,
        },
        production_config={
            "subsistence": {
                "scale": 5.0,
                "sigma": 0.5,
                "factors": sub_factors,
            },
            "luxury": {
                "scale": 2.0,
                "sigma": 0.5,
                "factors": lux_factors,
            },
        },
        market_prices={
            "subsistence": 3.0,
            "luxury": 50.0,
        },
    )

    # Agents
    farmer = Agent.objects.create(
        simulation=simulation,
        name="Farmer",
        role="farmer",
        personality={"openness": 0.5},
        location=Point(50, 50),
        zone=zone,
        health=1.0,
        wealth=50.0,
    )
    merchant = Agent.objects.create(
        simulation=simulation,
        name="Merchant",
        role="merchant",
        personality={"openness": 0.7},
        location=Point(50, 50),
        zone=zone,
        health=1.0,
        wealth=200.0,
    )

    # Inventories
    AgentInventory.objects.create(
        agent=farmer,
        holdings={"subsistence": 5.0},
        cash={"LVR": 50.0},
    )
    AgentInventory.objects.create(
        agent=merchant,
        holdings={"subsistence": 2.0, "luxury": 1.0},
        cash={"LVR": 200.0},
    )

    # Property (merchant owns a shop)
    Property.objects.create(
        simulation=simulation,
        owner=merchant,
        owner_type="agent",
        zone=zone,
        property_type="shop",
        name="Merchant Shop",
        value=100.0,
        production_bonus={"luxury": 1.2},
    )

    return {
        "world": world,
        "government": gov,
        "currency": currency,
        "zone": zone,
        "zone_economy": ze,
        "farmer": farmer,
        "merchant": merchant,
        "subsistence": subsistence,
        "luxury": luxury,
    }


@pytest.mark.django_db
class TestProcessEconomyTick:
    def test_full_tick_runs_without_error(
        self,
        simulation,
        setup_economy,
    ):
        process_economy_tick_new(simulation, tick=1)

    def test_prices_recorded_in_history(
        self,
        simulation,
        setup_economy,
    ):
        process_economy_tick_new(simulation, tick=1)
        ze = setup_economy["zone_economy"]
        assert PriceHistory.objects.filter(
            zone_economy=ze,
            tick=1,
        ).exists()

    def test_transactions_recorded_in_ledger(
        self,
        simulation,
        setup_economy,
    ):
        process_economy_tick_new(simulation, tick=1)
        assert EconomicLedger.objects.filter(
            simulation=simulation,
            tick=1,
        ).exists()

    def test_agent_wealth_updated(
        self,
        simulation,
        setup_economy,
    ):
        old_wealth = setup_economy["farmer"].wealth
        process_economy_tick_new(simulation, tick=1)
        setup_economy["farmer"].refresh_from_db()
        assert setup_economy["farmer"].wealth != old_wealth

    def test_government_treasury_receives_tax(
        self,
        simulation,
        setup_economy,
    ):
        process_economy_tick_new(simulation, tick=1)
        setup_economy["government"].refresh_from_db()
        treasury = setup_economy["government"].government_treasury
        assert treasury.get("LVR", 0.0) > 0.0

    def test_currency_velocity_updated(
        self,
        simulation,
        setup_economy,
    ):
        process_economy_tick_new(simulation, tick=1)
        setup_economy["currency"].refresh_from_db()
        assert setup_economy["currency"].cached_velocity >= 0.0


@pytest.mark.django_db
class TestConservationOfOutputValue:
    """CM-1 / distribution PROD-2 conservation rewrite (approach A).

    Round 1 audit report: compute_rent credited the FULL zone output
    value V as rent, and compute_wages independently credited output
    value again (full value to owners, wage_share*value to workers),
    both as brand-new cash (from_agent=None) with no offsetting debit.
    Every tick therefore injected strictly more money than the output
    actually produced. The fix partitions V into rent + wages + profit
    shares that sum to exactly V (Ricardo 1817 / national-accounting
    factor-income identity), so the net cash injected by the
    rent/wage/profit steps must equal V, not exceed it.
    """

    def test_tick_money_injection_equals_output_value(
        self,
        simulation,
        setup_economy,
    ):
        process_economy_tick_new(simulation, tick=1)

        ze = setup_economy["zone_economy"]
        ze.refresh_from_db()
        # equilibrium_prices used by the rent/wage/profit steps this
        # tick are exactly what engine.py persists as market_prices at
        # the end of the zone loop (engine.py: `ze.market_prices =
        # equilibrium_prices`, written after the factor-income step).
        prices = ze.market_prices

        production_entries = EconomicLedger.objects.filter(
            simulation=simulation,
            tick=1,
            transaction_type="production",
        )
        output_value = sum(
            entry.quantity * prices.get(entry.good_category.code, 0.0)
            for entry in production_entries
            if entry.good_category is not None
        )

        factor_income_credits = EconomicLedger.objects.filter(
            simulation=simulation,
            tick=1,
            from_agent__isnull=True,
            transaction_type__in=["rent", "wage", "profit"],
        )
        total_injected = sum(entry.total_amount for entry in factor_income_credits)

        assert abs(total_injected - output_value) < 1e-6


@pytest.fixture
def setup_two_zone_economy(simulation):
    """Two zones both quoting 'subsistence', seeded with DIFFERENT
    market_prices (3.0 and 9.0).

    Built to exercise the CM-5 system-price aggregation fix: with the
    pre-fix dict.update() merge, the system-wide price dict kept only
    whichever zone was processed last. The fix aggregates across zones
    (mean), so the system price for 'subsistence' must be 6.0
    regardless of zone processing order.
    """
    world = World.objects.create(
        simulation=simulation,
        distance_scale=133.0,
        tick_duration_hours=24.0,
    )
    Government.objects.create(
        simulation=simulation,
        government_type="monarchy",
        government_treasury={},
    )
    currency = Currency.objects.create(
        simulation=simulation,
        code="LVR",
        name="Livre",
        symbol="L",
        is_primary=True,
        total_supply=10000.0,
    )
    GoodCategory.objects.create(
        simulation=simulation,
        code="subsistence",
        name="Subsistence",
        is_essential=True,
        base_price=3.0,
        price_elasticity=0.3,
    )
    ProductionFactor.objects.create(simulation=simulation, code="labor", name="Labor")
    ProductionFactor.objects.create(simulation=simulation, code="capital", name="Capital")
    TaxPolicy.objects.create(simulation=simulation, income_tax_rate=0.15)

    for idx, price in enumerate([3.0, 9.0], start=1):
        zone = Zone.objects.create(
            world=world,
            name=f"Zone{idx}",
            zone_type="urban",
            boundary=Polygon.from_bbox((idx * 100, 0, idx * 100 + 100, 100)),
            center=Point(idx * 100 + 50, 50),
        )
        ZoneEconomy.objects.create(
            zone=zone,
            natural_resources={"labor": 1.0, "capital": 0.5},
            production_config={
                "subsistence": {
                    "scale": 2.0,
                    "sigma": 0.5,
                    "factors": {"labor": 0.6, "capital": 0.4},
                },
            },
            market_prices={"subsistence": price},
        )
        agent = Agent.objects.create(
            simulation=simulation,
            name=f"Farmer{idx}",
            role="farmer",
            personality={"openness": 0.5},
            location=Point(idx * 100 + 50, 50),
            zone=zone,
            health=1.0,
            wealth=50.0,
        )
        AgentInventory.objects.create(
            agent=agent,
            holdings={"subsistence": 3.0},
            cash={"LVR": 50.0},
        )

    return {"currency": currency}


@pytest.mark.django_db
class TestSystemPriceAggregation:
    """CM-5 fix (Round 1 audit report, cross-module CM-5): old_prices_all
    and new_prices_all must be genuine cross-zone aggregates fed into
    compute_inflation, not the last-processed zone's prices."""

    def test_inflation_uses_aggregated_system_prices_not_last_zone(
        self,
        simulation,
        setup_two_zone_economy,
    ):
        with patch(
            "epocha.apps.economy.engine.compute_inflation",
            wraps=engine_module.compute_inflation,
        ) as mock_inflation:
            process_economy_tick_new(simulation, tick=1)

        mock_inflation.assert_called_once()
        old_prices_arg = mock_inflation.call_args.args[0]
        # Mean of the seeded 3.0 and 9.0 == 6.0. A last-zone-wins
        # dict.update() merge would instead yield 9.0 (or 3.0).
        assert abs(old_prices_arg["subsistence"] - 6.0) < 1e-6


@pytest.mark.django_db
class TestLiveMoneySupply:
    """CM-2 fix (Round 1 audit report, cross-module CM-2): Currency.
    total_supply is a live per-tick aggregate of circulating cash, not
    the static template constant set once at initialization; and the
    Fisher MV=PQ diagnostic (defined but never invoked pre-fix) is
    wired into the tick."""

    def test_money_supply_tracks_circulating_cash(
        self,
        simulation,
        setup_economy,
    ):
        process_economy_tick_new(simulation, tick=1)

        currency = setup_economy["currency"]
        currency.refresh_from_db()

        living_agents = Agent.objects.filter(simulation=simulation, is_alive=True)
        circulating_cash = sum(agent.inventory.cash.get("LVR", 0.0) for agent in living_agents)

        assert abs(currency.total_supply - circulating_cash) < 1e-6
        # The fixture seeds total_supply=10000.0, wildly disconnected
        # from the ~250 in agent cash at genesis. After a tick moves
        # money around (rent/wages/profit/taxes/trades), the live
        # aggregate must have moved away from the stale template
        # constant.
        assert abs(currency.total_supply - 10000.0) > 1e-6

    def test_fisher_consistency_called(
        self,
        simulation,
        setup_economy,
    ):
        with patch(
            "epocha.apps.economy.engine.check_fisher_consistency",
            wraps=engine_module.check_fisher_consistency,
        ) as mock_fisher:
            process_economy_tick_new(simulation, tick=1)

        mock_fisher.assert_called_once()


@pytest.mark.django_db
class TestMoodThresholdReconciliation:
    """CM-6 fix (Round 1 audit report, monetary+initialization
    cross-module finding): mood thresholds are derived from the living
    population's median wealth each tick, not fixed absolute
    constants disconnected from the template's wealth scale."""

    def test_mood_thresholds_derived_from_population_median(
        self,
        simulation,
        setup_economy,
    ):
        with patch(
            "epocha.apps.economy.engine.derive_mood_thresholds",
            wraps=engine_module.derive_mood_thresholds,
        ) as mock_derive:
            process_economy_tick_new(simulation, tick=1)

        mock_derive.assert_called_once()
        median_wealth_arg = mock_derive.call_args.args[0]
        assert median_wealth_arg > 0.0

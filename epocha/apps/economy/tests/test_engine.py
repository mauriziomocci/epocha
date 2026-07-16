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


@pytest.mark.django_db
class TestAbsentOwnerFactorIncomeAndTaxSymmetry:
    """Round 2 re-audit findings CM-TAX-1, CM-TAX-2 and NEW-3.

    Shared root cause: the zone loop resolves factor-income payees
    through inv_cache, built only from agents that are alive AND
    resident in the zone being processed, while Property.owner_id can
    point to an agent who is dead or lives in another zone. That
    asymmetry (a) silently drops rent/profit owed to living
    out-of-zone owners (NEW-3), (b) lets the taxation step credit the
    treasury for income that was never debited from anyone (CM-TAX-1,
    money creation), and (c) with no Government, debits agents without
    crediting any treasury (CM-TAX-2, money destruction).
    """

    def _output_value(self, simulation, prices):
        production_entries = EconomicLedger.objects.filter(
            simulation=simulation,
            tick=1,
            transaction_type="production",
        )
        return sum(
            entry.quantity * prices.get(entry.good_category.code, 0.0)
            for entry in production_entries
            if entry.good_category is not None
        )

    def _factor_income_injected(self, simulation):
        credits = EconomicLedger.objects.filter(
            simulation=simulation,
            tick=1,
            from_agent__isnull=True,
            transaction_type__in=["rent", "wage", "profit"],
        )
        return sum(entry.total_amount for entry in credits)

    def test_out_of_zone_owner_receives_rent(
        self,
        simulation,
        setup_economy,
    ):
        # A living landlord resident in a zone WITHOUT a ZoneEconomy
        # owns the only property claiming a bonus on the good actually
        # produced in the economic zone. Their rent must be credited,
        # not silently dropped by the zone-local payee lookup (NEW-3).
        other_zone = Zone.objects.create(
            world=setup_economy["world"],
            name="Countryside",
            zone_type="rural",
            boundary=Polygon.from_bbox((200, 0, 300, 100)),
            center=Point(250, 50),
        )
        landlord = Agent.objects.create(
            simulation=simulation,
            name="AbsenteeLandlord",
            role="noble",
            personality={"openness": 0.5},
            location=Point(250, 50),
            zone=other_zone,
            health=1.0,
            wealth=100.0,
        )
        AgentInventory.objects.create(
            agent=landlord,
            holdings={},
            cash={"LVR": 100.0},
        )
        Property.objects.create(
            simulation=simulation,
            owner=landlord,
            owner_type="agent",
            zone=setup_economy["zone"],
            property_type="farm",
            name="Absentee Farm",
            value=100.0,
            production_bonus={"subsistence": 1.0},
        )

        process_economy_tick_new(simulation, tick=1)

        rent_entries = EconomicLedger.objects.filter(
            simulation=simulation,
            tick=1,
            transaction_type="rent",
            to_agent=landlord,
        )
        assert rent_entries.exists()

        # The full factor-income partition must still sum to the zone
        # output value V: the absentee owner's slice is paid out, not
        # dropped from the injection.
        ze = setup_economy["zone_economy"]
        ze.refresh_from_db()
        output_value = self._output_value(simulation, ze.market_prices)
        injected = self._factor_income_injected(simulation)
        assert abs(injected - output_value) < 1e-6

    def test_dead_owner_share_reallocated_not_dropped(
        self,
        simulation,
        setup_economy,
    ):
        # A dead agent still recorded as owner of the only property
        # claiming the produced good: the partition must exclude the
        # dead owner (no rent/profit credited to a corpse) and
        # reallocate that share so the injection still equals V.
        dead_owner = Agent.objects.create(
            simulation=simulation,
            name="DeadLandlord",
            role="noble",
            personality={"openness": 0.5},
            location=Point(50, 50),
            zone=setup_economy["zone"],
            health=0.0,
            wealth=100.0,
            is_alive=False,
        )
        AgentInventory.objects.create(
            agent=dead_owner,
            holdings={},
            cash={"LVR": 100.0},
        )
        Property.objects.create(
            simulation=simulation,
            owner=dead_owner,
            owner_type="agent",
            zone=setup_economy["zone"],
            property_type="farm",
            name="Estate of the Deceased",
            value=100.0,
            production_bonus={"subsistence": 1.0},
        )

        process_economy_tick_new(simulation, tick=1)

        assert not EconomicLedger.objects.filter(
            simulation=simulation,
            tick=1,
            transaction_type__in=["rent", "profit"],
            to_agent=dead_owner,
        ).exists()

        ze = setup_economy["zone_economy"]
        ze.refresh_from_db()
        output_value = self._output_value(simulation, ze.market_prices)
        injected = self._factor_income_injected(simulation)
        assert abs(injected - output_value) < 1e-6

    def test_dead_owner_share_renormalizes_to_surviving_claimant(
        self,
        simulation,
        setup_economy,
    ):
        # R3-ENG-1 coverage (Round 3 re-audit): when a LIVING property
        # also claims the same good, a dead owner's share does NOT go
        # through the no-landlord fallback -- it renormalizes to the
        # surviving claimant(s) inside _distribute_proportional_to_bonus.
        # The partition must still sum to V and the survivor must
        # receive rent.
        landlord = Agent.objects.create(
            simulation=simulation,
            name="SurvivingLandlord",
            role="noble",
            personality={"openness": 0.5},
            location=Point(50, 50),
            zone=setup_economy["zone"],
            health=1.0,
            wealth=100.0,
        )
        AgentInventory.objects.create(
            agent=landlord,
            holdings={},
            cash={"LVR": 100.0},
        )
        Property.objects.create(
            simulation=simulation,
            owner=landlord,
            owner_type="agent",
            zone=setup_economy["zone"],
            property_type="farm",
            name="Surviving Farm",
            value=100.0,
            production_bonus={"subsistence": 1.0},
        )
        dead_owner = Agent.objects.create(
            simulation=simulation,
            name="DeadCoOwner",
            role="noble",
            personality={"openness": 0.5},
            location=Point(50, 50),
            zone=setup_economy["zone"],
            health=0.0,
            wealth=100.0,
            is_alive=False,
        )
        Property.objects.create(
            simulation=simulation,
            owner=dead_owner,
            owner_type="agent",
            zone=setup_economy["zone"],
            property_type="farm",
            name="Dead Co-Owner Farm",
            value=100.0,
            production_bonus={"subsistence": 2.0},
        )

        process_economy_tick_new(simulation, tick=1)

        # The survivor collects rent (the whole rent slice for the
        # good, since the dead co-owner's bonus renormalized away).
        assert EconomicLedger.objects.filter(
            simulation=simulation,
            tick=1,
            transaction_type="rent",
            to_agent=landlord,
        ).exists()
        assert not EconomicLedger.objects.filter(
            simulation=simulation,
            tick=1,
            transaction_type__in=["rent", "profit"],
            to_agent=dead_owner,
        ).exists()

        ze = setup_economy["zone_economy"]
        ze.refresh_from_db()
        output_value = self._output_value(simulation, ze.market_prices)
        injected = self._factor_income_injected(simulation)
        assert abs(injected - output_value) < 1e-6

    def test_treasury_credit_equals_agent_tax_debits(
        self,
        simulation,
        setup_economy,
    ):
        # CM-TAX-1: the treasury must receive exactly the sum of the
        # taxes actually debited from agents, never compute_taxes'
        # nominal total over incomes whose earner could not be debited.
        # The dead-owner property reproduces the pre-fix leak: the dead
        # owner's rent was taxed into the treasury with no counterpart
        # agent debit, creating money.
        dead_owner = Agent.objects.create(
            simulation=simulation,
            name="DeadLandlord",
            role="noble",
            personality={"openness": 0.5},
            location=Point(50, 50),
            zone=setup_economy["zone"],
            health=0.0,
            wealth=100.0,
            is_alive=False,
        )
        Property.objects.create(
            simulation=simulation,
            owner=dead_owner,
            owner_type="agent",
            zone=setup_economy["zone"],
            property_type="farm",
            name="Estate of the Deceased",
            value=100.0,
            production_bonus={"subsistence": 1.0},
        )

        process_economy_tick_new(simulation, tick=1)

        setup_economy["government"].refresh_from_db()
        treasury = setup_economy["government"].government_treasury.get("LVR", 0.0)
        debited = sum(
            entry.total_amount
            for entry in EconomicLedger.objects.filter(
                simulation=simulation,
                tick=1,
                transaction_type="tax",
            )
        )
        assert abs(treasury - debited) < 1e-6

    def test_no_government_skips_taxation(
        self,
        simulation,
        setup_economy,
    ):
        # CM-TAX-2: with a TaxPolicy but no Government, the pre-fix
        # loop still debited every earner's cash while the treasury
        # credit was skipped, destroying money. Without a fiscal
        # authority the taxation step must not run at all.
        setup_economy["government"].delete()

        process_economy_tick_new(simulation, tick=1)

        assert not EconomicLedger.objects.filter(
            simulation=simulation,
            tick=1,
            transaction_type="tax",
        ).exists()


@pytest.mark.django_db
class TestSettlementAffordability:
    """Round 2 re-audit finding MKT-7 (run wf_da2305bc-4cd).

    Wants are sized at pre-clearing prices (and essential needs are not
    cash-sized at all), while trades settle at equilibrium prices with
    no guard on the buyer's cash: realized spend could exceed the
    buyer's cash and drive it negative. The settlement must scale each
    trade down to what the buyer can actually pay.
    """

    def test_buyer_trade_spend_bounded_by_cash(
        self,
        simulation,
        setup_economy,
    ):
        # A near-broke buyer with an essential-good gap: their demand
        # (1 unit of subsistence, not sized by cash) settles at an
        # equilibrium price several times their cash on hand.
        merchant = setup_economy["merchant"]
        merchant_inv = merchant.inventory
        merchant_inv.holdings = {}
        merchant_inv.cash = {"LVR": 0.5}
        merchant_inv.save(update_fields=["holdings", "cash"])

        initial_cash = 0.5

        # Pin the equilibrium price above the buyer's cash so the test
        # exercises the settlement guard deterministically instead of
        # depending on tatonnement dynamics (with the fixture's excess
        # supply the price would fall below the buyer's cash and never
        # trigger the overspend).
        with patch(
            "epocha.apps.economy.engine.tatonnement_prices",
            return_value=({"subsistence": 5.0, "luxury": 50.0}, True),
        ):
            process_economy_tick_new(simulation, tick=1)

        trade_spend = sum(
            entry.total_amount
            for entry in EconomicLedger.objects.filter(
                simulation=simulation,
                tick=1,
                transaction_type="trade",
                from_agent=merchant,
            )
        )
        assert trade_spend <= initial_cash + 1e-9

        merchant_inv.refresh_from_db()
        assert merchant_inv.cash.get("LVR", 0.0) >= -1e-9


@pytest.mark.django_db
class TestSettlementDeterminismAndPriority:
    """Round 3 re-audit findings R3-MON-NEW-1 / R3-MKT-8 / R3-MKT-9
    (run wf_af84ed13-dc3).

    The MKT-7 affordability guard makes final allocations depend on the
    order trades are applied, and that order was hash-seed
    nondeterministic (goods iterated via an unordered set, agents via
    an unordered queryset): identically-seeded runs could diverge, and
    a cash-constrained buyer's access to the essential subsistence good
    was a hash-order lottery. Settlement must be deterministic and give
    essential goods explicit priority. Demand sizing must also count
    only the primary currency that settlement actually debits (R3-MKT-9).
    """

    def test_settlement_prioritizes_essentials_for_cash_constrained_buyer(
        self,
        simulation,
        setup_economy,
    ):
        merchant = setup_economy["merchant"]
        farmer = setup_economy["farmer"]
        merchant_inv = merchant.inventory
        merchant_inv.holdings = {}
        merchant_inv.cash = {"LVR": 3.0}
        merchant_inv.save(update_fields=["holdings", "cash"])

        # Force an adversarial application order: the non-essential
        # luxury trade arrives FIRST and would consume the buyer's
        # whole cash before the essential subsistence trade settles.
        adversarial_trades = [
            {
                "buyer_id": merchant.id,
                "seller_id": farmer.id,
                "good_code": "luxury",
                "quantity": 1.0,
                "price": 50.0,
                "total": 50.0,
            },
            {
                "buyer_id": merchant.id,
                "seller_id": farmer.id,
                "good_code": "subsistence",
                "quantity": 1.0,
                "price": 3.0,
                "total": 3.0,
            },
        ]
        with patch(
            "epocha.apps.economy.engine.execute_trades",
            return_value=adversarial_trades,
        ):
            process_economy_tick_new(simulation, tick=1)

        # The essential subsistence trade must have settled in full:
        # settlement re-orders trades essentials-first, so the 3.0 cash
        # buys 1 unit of subsistence and the luxury trade gets whatever
        # remains (nothing), not the other way around.
        subsistence_trades = EconomicLedger.objects.filter(
            simulation=simulation,
            tick=1,
            transaction_type="trade",
            from_agent=merchant,
            good_category=setup_economy["subsistence"],
        )
        assert subsistence_trades.exists()
        assert abs(sum(e.total_amount for e in subsistence_trades) - 3.0) < 1e-9

    def test_demand_sized_on_primary_currency_cash(
        self,
        simulation,
        setup_economy,
    ):
        # R3-MKT-9: demand was sized on the sum of ALL currencies while
        # settlement debits only the primary one -- an agent holding
        # only secondary-currency cash projected demand it could never
        # settle, distorting the price signal.
        merchant = setup_economy["merchant"]
        merchant_inv = merchant.inventory
        merchant_inv.cash = {"GLD": 200.0}
        merchant_inv.save(update_fields=["cash"])

        with patch(
            "epocha.apps.economy.engine.collect_supply_and_demand",
            wraps=engine_module.collect_supply_and_demand,
        ) as mock_collect:
            process_economy_tick_new(simulation, tick=1)

        agent_inventories = mock_collect.call_args.args[0]
        merchant_entry = next(e for e in agent_inventories if e["agent_id"] == merchant.id)
        assert merchant_entry["cash_amount"] == 0.0


@pytest.mark.django_db
class TestFisherDiagnosticAggregation:
    """Round 3 re-audit finding R3-5 (run wf_af84ed13-dc3): the Fisher
    PQ side used the unweighted mean price times the summed
    heterogeneous physical quantities, conflating aggregation error
    with monetary inconsistency. PQ must be the output-weighted nominal
    value sum(p_g * q_g)."""

    def test_fisher_pq_is_output_weighted_nominal_value(
        self,
        simulation,
        setup_economy,
    ):
        with patch(
            "epocha.apps.economy.engine.check_fisher_consistency",
            wraps=engine_module.check_fisher_consistency,
        ) as mock_fisher:
            process_economy_tick_new(simulation, tick=1)

        kwargs = mock_fisher.call_args.kwargs
        realized_pq = kwargs["price_level"] * kwargs["output_level"]

        ze = setup_economy["zone_economy"]
        ze.refresh_from_db()
        prices = ze.market_prices
        expected_pq = sum(
            entry.quantity * prices.get(entry.good_category.code, 0.0)
            for entry in EconomicLedger.objects.filter(
                simulation=simulation,
                tick=1,
                transaction_type="production",
            )
            if entry.good_category is not None
        )
        assert abs(realized_pq - expected_pq) < 1e-6

    def test_fisher_mv_equals_factor_income_injection(
        self,
        simulation,
        setup_economy,
    ):
        # R4-FISH-1 (Round 4 re-audit, run wf_9fb030e4-8a1): with a
        # measured velocity the identity MV = volume is tautological in
        # M, and the pre-fix wiring passed the TURNOVER velocity
        # (trades + factor incomes) against the income-form PQ, firing
        # spurious warnings in a conserved economy. The check must now
        # compare the factor-income injection (MV side) against nominal
        # output (PQ side): in this conserved fixture the two are equal,
        # so the diagnostic reads ~zero divergence.
        with patch(
            "epocha.apps.economy.engine.check_fisher_consistency",
            wraps=engine_module.check_fisher_consistency,
        ) as mock_fisher:
            process_economy_tick_new(simulation, tick=1)

        kwargs = mock_fisher.call_args.kwargs
        mv = kwargs["money_supply"] * kwargs["velocity"]
        pq = kwargs["price_level"] * kwargs["output_level"]
        assert abs(mv - pq) < 1e-6


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
class TestFisherMultiZoneAggregation:
    """Round 5 re-audit finding R5-FISH-2 (run wf_62d071a6-289): the
    rewired Fisher diagnostic valued MV at per-zone equilibrium prices
    but PQ at the unweighted cross-zone MEAN price, so a perfectly
    conserved multi-zone economy with price dispersion produced
    spurious divergence. PQ must be the sum of the per-zone nominal
    output values V_z -- the same quantities the factor-income
    partition injects -- so divergence signals a genuine
    conservation defect in every regime."""

    def test_fisher_pq_sums_per_zone_nominal_output(
        self,
        simulation,
        setup_two_zone_economy,
    ):
        # Make output ASYMMETRIC across the two zones (extra farmers in
        # Zone1): with symmetric output the mean-price form coincides
        # with the per-zone sum by algebraic accident and the defect is
        # invisible. Asymmetry + price dispersion is the auditor's
        # counterexample regime.
        zone1 = Zone.objects.get(world__simulation=simulation, name="Zone1")
        for idx in range(3):
            extra = Agent.objects.create(
                simulation=simulation,
                name=f"ExtraFarmer{idx}",
                role="farmer",
                personality={"openness": 0.5},
                location=Point(150, 50),
                zone=zone1,
                health=1.0,
                wealth=50.0,
            )
            AgentInventory.objects.create(
                agent=extra,
                holdings={"subsistence": 3.0},
                cash={"LVR": 50.0},
            )

        with patch(
            "epocha.apps.economy.engine.check_fisher_consistency",
            wraps=engine_module.check_fisher_consistency,
        ) as mock_fisher:
            process_economy_tick_new(simulation, tick=1)

        kwargs = mock_fisher.call_args.kwargs
        realized_pq = kwargs["price_level"] * kwargs["output_level"]

        expected_pq = 0.0
        for ze in ZoneEconomy.objects.filter(zone__world__simulation=simulation):
            prices = ze.market_prices
            for entry in EconomicLedger.objects.filter(
                simulation=simulation,
                tick=1,
                transaction_type="production",
                to_agent__zone=ze.zone,
            ):
                if entry.good_category is not None:
                    expected_pq += entry.quantity * prices.get(entry.good_category.code, 0.0)

        assert abs(realized_pq - expected_pq) < 1e-6


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

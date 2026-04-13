"""Tests for the economy data models."""

import pytest
from django.contrib.gis.geos import Point, Polygon
from django.db import IntegrityError

from epocha.apps.agents.models import Agent
from epocha.apps.economy.models import (
    AgentExpectation,
    AgentInventory,
    BankingState,
    Currency,
    EconomicLedger,
    GoodCategory,
    Loan,
    PriceHistory,
    ProductionFactor,
    Property,
    PropertyListing,
    TaxPolicy,
    ZoneEconomy,
)
from epocha.apps.simulation.models import Simulation
from epocha.apps.users.models import User
from epocha.apps.world.models import Government, World, Zone


@pytest.fixture
def user(db):
    return User.objects.create_user(
        email="econ@epocha.dev",
        username="econuser",
        password="pass1234",
    )


@pytest.fixture
def simulation(user):
    return Simulation.objects.create(name="EconTest", seed=42, owner=user)


@pytest.mark.django_db
class TestCurrency:
    def test_create_currency(self, simulation):
        c = Currency.objects.create(
            simulation=simulation,
            code="LVR",
            name="Livre tournois",
            symbol="L",
            is_primary=True,
            total_supply=50000.0,
        )
        assert c.code == "LVR"
        assert c.cached_velocity == 1.0  # default
        assert c.total_supply == 50000.0

    def test_currency_code_unique_per_simulation(self, simulation):
        Currency.objects.create(
            simulation=simulation,
            code="LVR",
            name="Livre",
            symbol="L",
            is_primary=True,
            total_supply=1000.0,
        )
        with pytest.raises(IntegrityError):
            Currency.objects.create(
                simulation=simulation,
                code="LVR",
                name="Another Livre",
                symbol="L2",
                is_primary=False,
                total_supply=500.0,
            )

    def test_two_simulations_same_code(self, user):
        sim1 = Simulation.objects.create(name="Sim1", seed=1, owner=user)
        sim2 = Simulation.objects.create(name="Sim2", seed=2, owner=user)
        Currency.objects.create(
            simulation=sim1,
            code="USD",
            name="Dollar",
            symbol="$",
            total_supply=1000.0,
        )
        Currency.objects.create(
            simulation=sim2,
            code="USD",
            name="Dollar",
            symbol="$",
            total_supply=2000.0,
        )
        assert Currency.objects.filter(code="USD").count() == 2


@pytest.mark.django_db
class TestGoodCategory:
    def test_create_good(self, simulation):
        g = GoodCategory.objects.create(
            simulation=simulation,
            code="subsistence",
            name="Subsistence goods",
            is_essential=True,
            base_price=3.0,
            price_elasticity=0.3,
        )
        assert g.is_essential is True
        assert g.price_elasticity == 0.3

    def test_good_code_unique_per_simulation(self, simulation):
        GoodCategory.objects.create(
            simulation=simulation,
            code="luxury",
            name="Luxury",
            base_price=50.0,
            price_elasticity=2.0,
        )
        with pytest.raises(IntegrityError):
            GoodCategory.objects.create(
                simulation=simulation,
                code="luxury",
                name="Other Luxury",
                base_price=60.0,
                price_elasticity=1.8,
            )


@pytest.mark.django_db
class TestProductionFactor:
    def test_create_factor(self, simulation):
        f = ProductionFactor.objects.create(
            simulation=simulation,
            code="labor",
            name="Labor",
            description="Human work hours",
        )
        assert f.code == "labor"

    def test_factor_code_unique_per_simulation(self, simulation):
        ProductionFactor.objects.create(
            simulation=simulation,
            code="capital",
            name="Capital",
        )
        with pytest.raises(IntegrityError):
            ProductionFactor.objects.create(
                simulation=simulation,
                code="capital",
                name="Other Capital",
            )


# -- Task 3 fixtures and tests: ZoneEconomy, PriceHistory, AgentInventory --


@pytest.fixture
def world(simulation):
    return World.objects.create(
        simulation=simulation,
        distance_scale=133.0,
        tick_duration_hours=24.0,
    )


@pytest.fixture
def zone(world):
    return Zone.objects.create(
        world=world,
        name="Paris",
        zone_type="urban",
        boundary=Polygon.from_bbox((0, 0, 100, 100)),
        center=Point(50, 50),
    )


@pytest.fixture
def agent(simulation, zone):
    return Agent.objects.create(
        simulation=simulation,
        name="TestAgent",
        role="merchant",
        personality={"openness": 0.5},
        location=Point(50, 50),
        zone=zone,
    )


@pytest.mark.django_db
class TestZoneEconomy:
    def test_create_zone_economy(self, zone):
        ze = ZoneEconomy.objects.create(
            zone=zone,
            natural_resources={"labor": 1.0, "capital": 0.5},
            production_config={"subsistence": {"scale": 10.0, "sigma": 0.5}},
            market_prices={"subsistence": 3.0},
        )
        assert ze.zone == zone
        assert ze.natural_resources["labor"] == 1.0

    def test_one_economy_per_zone(self, zone):
        ZoneEconomy.objects.create(zone=zone)
        with pytest.raises(IntegrityError):
            ZoneEconomy.objects.create(zone=zone)


@pytest.mark.django_db
class TestPriceHistory:
    def test_create_price_history(self, zone):
        ze = ZoneEconomy.objects.create(zone=zone)
        ph = PriceHistory.objects.create(
            zone_economy=ze,
            good_code="subsistence",
            tick=1,
            price=3.2,
            supply=100.0,
            demand=120.0,
        )
        assert ph.price == 3.2
        assert ph.tick == 1

    def test_unique_per_zone_good_tick(self, zone):
        ze = ZoneEconomy.objects.create(zone=zone)
        PriceHistory.objects.create(
            zone_economy=ze,
            good_code="subsistence",
            tick=1,
            price=3.0,
            supply=100.0,
            demand=100.0,
        )
        with pytest.raises(IntegrityError):
            PriceHistory.objects.create(
                zone_economy=ze,
                good_code="subsistence",
                tick=1,
                price=3.5,
                supply=90.0,
                demand=110.0,
            )


@pytest.mark.django_db
class TestAgentInventory:
    def test_create_inventory(self, agent):
        inv = AgentInventory.objects.create(
            agent=agent,
            holdings={"subsistence": 10.0, "materials": 5.0},
            cash={"LVR": 100.0},
        )
        assert inv.holdings["subsistence"] == 10.0
        assert inv.cash["LVR"] == 100.0

    def test_one_inventory_per_agent(self, agent):
        AgentInventory.objects.create(agent=agent)
        with pytest.raises(IntegrityError):
            AgentInventory.objects.create(agent=agent)


# -- Task 4: Property, TaxPolicy, EconomicLedger, treasury --


@pytest.fixture
def currency(simulation):
    return Currency.objects.create(
        simulation=simulation,
        code="LVR",
        name="Livre",
        symbol="L",
        is_primary=True,
        total_supply=50000.0,
    )


@pytest.mark.django_db
class TestProperty:
    def test_create_agent_property(self, simulation, agent, zone):
        p = Property.objects.create(
            simulation=simulation,
            owner=agent,
            owner_type="agent",
            zone=zone,
            property_type="land",
            name="Small Farm",
            value=200.0,
            production_bonus={"subsistence": 1.5},
        )
        assert p.owner == agent
        assert p.owner_type == "agent"
        assert p.production_bonus["subsistence"] == 1.5

    def test_create_government_property(self, simulation, zone):
        p = Property.objects.create(
            simulation=simulation,
            owner=None,
            owner_type="government",
            zone=zone,
            property_type="land",
            name="Royal Estate",
            value=1000.0,
        )
        assert p.owner is None
        assert p.owner_type == "government"

    def test_create_commons(self, simulation, zone):
        p = Property.objects.create(
            simulation=simulation,
            owner=None,
            owner_type="commons",
            zone=zone,
            property_type="land",
            name="Common Land",
            value=0.0,
        )
        assert p.owner_type == "commons"


@pytest.mark.django_db
class TestTaxPolicy:
    def test_create_tax_policy(self, simulation):
        tp = TaxPolicy.objects.create(
            simulation=simulation,
            income_tax_rate=0.15,
        )
        assert tp.income_tax_rate == 0.15

    def test_one_policy_per_simulation(self, simulation):
        TaxPolicy.objects.create(simulation=simulation, income_tax_rate=0.10)
        with pytest.raises(IntegrityError):
            TaxPolicy.objects.create(simulation=simulation, income_tax_rate=0.20)


@pytest.mark.django_db
class TestEconomicLedger:
    def test_create_trade_transaction(self, simulation, agent, currency):
        tx = EconomicLedger.objects.create(
            simulation=simulation,
            tick=1,
            from_agent=agent,
            to_agent=None,
            currency=currency,
            quantity=10.0,
            unit_price=3.0,
            total_amount=30.0,
            transaction_type="trade",
        )
        assert tx.total_amount == 30.0
        assert tx.transaction_type == "trade"

    def test_create_tax_transaction(self, simulation, agent, currency):
        tx = EconomicLedger.objects.create(
            simulation=simulation,
            tick=1,
            from_agent=agent,
            to_agent=None,
            currency=currency,
            total_amount=5.0,
            transaction_type="tax",
        )
        assert tx.transaction_type == "tax"


@pytest.mark.django_db
class TestGovernmentTreasury:
    def test_government_has_treasury(self, simulation):
        gov = Government.objects.create(
            simulation=simulation,
            government_type="monarchy",
        )
        assert gov.government_treasury == {}
        gov.government_treasury = {"LVR": 1000.0}
        gov.save(update_fields=["government_treasury"])
        gov.refresh_from_db()
        assert gov.government_treasury["LVR"] == 1000.0


# -- Behavioral economy models (Spec 2, Part 1) --


@pytest.mark.django_db
class TestLoan:
    def test_create_banking_loan(self, simulation, agent):
        loan = Loan.objects.create(
            simulation=simulation,
            lender=None,
            borrower=agent,
            lender_type="banking",
            principal=500.0,
            interest_rate=0.05,
            remaining_balance=500.0,
            issued_at_tick=1,
            due_at_tick=10,
        )
        assert loan.principal == 500.0
        assert loan.lender_type == "banking"
        assert loan.status == "active"
        assert loan.times_rolled_over == 0
        assert loan.lender is None

    def test_create_agent_loan(self, simulation, agent, zone):
        lender = Agent.objects.create(
            simulation=simulation,
            name="Lender",
            role="merchant",
            personality={"openness": 0.6},
            location=Point(50, 50),
            zone=zone,
        )
        loan = Loan.objects.create(
            simulation=simulation,
            lender=lender,
            borrower=agent,
            lender_type="agent",
            principal=200.0,
            interest_rate=0.08,
            remaining_balance=200.0,
            issued_at_tick=5,
        )
        assert loan.lender == lender
        assert loan.lender_type == "agent"
        assert loan.due_at_tick is None

    def test_loan_with_collateral(self, simulation, agent, zone):
        prop = Property.objects.create(
            simulation=simulation,
            owner=agent,
            owner_type="agent",
            zone=zone,
            property_type="land",
            name="Collateral Farm",
            value=300.0,
        )
        loan = Loan.objects.create(
            simulation=simulation,
            borrower=agent,
            lender_type="banking",
            principal=150.0,
            interest_rate=0.06,
            remaining_balance=150.0,
            collateral=prop,
            issued_at_tick=1,
        )
        assert loan.collateral == prop

    def test_loan_status_choices(self, simulation, agent):
        for status in ("active", "repaid", "defaulted", "rolled_over"):
            loan = Loan.objects.create(
                simulation=simulation,
                borrower=agent,
                lender_type="banking",
                principal=100.0,
                interest_rate=0.05,
                remaining_balance=100.0,
                issued_at_tick=1,
                status=status,
            )
            assert loan.status == status


@pytest.mark.django_db
class TestPropertyListing:
    def test_create_listing(self, simulation, agent, zone):
        prop = Property.objects.create(
            simulation=simulation,
            owner=agent,
            owner_type="agent",
            zone=zone,
            property_type="land",
            name="Listed Farm",
            value=200.0,
        )
        listing = PropertyListing.objects.create(
            property=prop,
            asking_price=250.0,
            fundamental_value=200.0,
            listed_at_tick=3,
        )
        assert listing.asking_price == 250.0
        assert listing.fundamental_value == 200.0
        assert listing.status == "listed"

    def test_one_listing_per_property(self, simulation, agent, zone):
        prop = Property.objects.create(
            simulation=simulation,
            owner=agent,
            owner_type="agent",
            zone=zone,
            property_type="land",
            name="Unique Farm",
            value=200.0,
        )
        PropertyListing.objects.create(
            property=prop,
            asking_price=250.0,
            fundamental_value=200.0,
            listed_at_tick=1,
        )
        with pytest.raises(IntegrityError):
            PropertyListing.objects.create(
                property=prop,
                asking_price=300.0,
                fundamental_value=220.0,
                listed_at_tick=2,
            )

    def test_listing_status_choices(self, simulation, agent, zone):
        for i, status in enumerate(("listed", "sold", "withdrawn")):
            prop = Property.objects.create(
                simulation=simulation,
                owner=agent,
                owner_type="agent",
                zone=zone,
                property_type="land",
                name=f"Farm {status}",
                value=100.0,
            )
            listing = PropertyListing.objects.create(
                property=prop,
                asking_price=120.0,
                fundamental_value=100.0,
                listed_at_tick=i,
                status=status,
            )
            assert listing.status == status


@pytest.mark.django_db
class TestAgentExpectation:
    def test_create_expectation(self, agent):
        exp = AgentExpectation.objects.create(
            agent=agent,
            good_code="subsistence",
            expected_price=3.5,
            trend_direction="rising",
            confidence=0.6,
            lambda_rate=0.3,
            updated_at_tick=1,
        )
        assert exp.expected_price == 3.5
        assert exp.trend_direction == "rising"
        assert exp.confidence == 0.6
        assert exp.lambda_rate == 0.3

    def test_default_confidence(self, agent):
        exp = AgentExpectation.objects.create(
            agent=agent,
            good_code="luxury",
            expected_price=50.0,
            lambda_rate=0.25,
            updated_at_tick=1,
        )
        assert exp.confidence == 0.5
        assert exp.trend_direction == "stable"

    def test_unique_agent_good(self, agent):
        AgentExpectation.objects.create(
            agent=agent,
            good_code="subsistence",
            expected_price=3.0,
            lambda_rate=0.3,
            updated_at_tick=1,
        )
        with pytest.raises(IntegrityError):
            AgentExpectation.objects.create(
                agent=agent,
                good_code="subsistence",
                expected_price=3.5,
                lambda_rate=0.4,
                updated_at_tick=2,
            )

    def test_different_goods_same_agent(self, agent):
        AgentExpectation.objects.create(
            agent=agent,
            good_code="subsistence",
            expected_price=3.0,
            lambda_rate=0.3,
            updated_at_tick=1,
        )
        exp2 = AgentExpectation.objects.create(
            agent=agent,
            good_code="luxury",
            expected_price=50.0,
            lambda_rate=0.25,
            updated_at_tick=1,
        )
        assert exp2.good_code == "luxury"
        assert AgentExpectation.objects.filter(agent=agent).count() == 2


@pytest.mark.django_db
class TestBankingState:
    def test_create_banking_state(self, simulation):
        bs = BankingState.objects.create(
            simulation=simulation,
            reserve_ratio=0.10,
            base_interest_rate=0.05,
        )
        assert bs.total_deposits == 0.0
        assert bs.total_loans_outstanding == 0.0
        assert bs.is_solvent is True
        assert bs.confidence_index == 1.0

    def test_one_banking_state_per_simulation(self, simulation):
        BankingState.objects.create(
            simulation=simulation,
            reserve_ratio=0.10,
            base_interest_rate=0.05,
        )
        with pytest.raises(IntegrityError):
            BankingState.objects.create(
                simulation=simulation,
                reserve_ratio=0.15,
                base_interest_rate=0.06,
            )

    def test_banking_state_with_data(self, simulation):
        bs = BankingState.objects.create(
            simulation=simulation,
            total_deposits=50000.0,
            total_loans_outstanding=35000.0,
            reserve_ratio=0.10,
            base_interest_rate=0.05,
            is_solvent=True,
            confidence_index=0.85,
        )
        assert bs.total_deposits == 50000.0
        assert bs.total_loans_outstanding == 35000.0
        assert bs.confidence_index == 0.85

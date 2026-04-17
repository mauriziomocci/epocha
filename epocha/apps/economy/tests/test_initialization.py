"""Tests for economy initialization from templates."""
import pytest
from django.contrib.gis.geos import Point, Polygon

from epocha.apps.agents.models import Agent
from epocha.apps.economy.initialization import initialize_economy
from epocha.apps.economy.models import (
    AgentInventory,
    Currency,
    GoodCategory,
    PriceHistory,
    ProductionFactor,
    Property,
    TaxPolicy,
    ZoneEconomy,
)
from epocha.apps.simulation.models import Simulation
from epocha.apps.users.models import User
from epocha.apps.world.models import World, Zone


@pytest.fixture
def user(db):
    return User.objects.create_user(
        email="init@epocha.dev",
        username="inituser",
        password="pass1234",
    )


@pytest.fixture
def simulation(user):
    return Simulation.objects.create(
        name="InitTest", seed=42, owner=user,
    )


@pytest.fixture
def world_with_agents(simulation):
    """Create a world with 2 zones and 4 agents of different classes."""
    world = World.objects.create(
        simulation=simulation,
        distance_scale=133.0,
        tick_duration_hours=24.0,
    )
    z1 = Zone.objects.create(
        world=world, name="Paris", zone_type="urban",
        boundary=Polygon.from_bbox((0, 0, 100, 100)),
        center=Point(50, 50),
    )
    z2 = Zone.objects.create(
        world=world, name="Countryside", zone_type="rural",
        boundary=Polygon.from_bbox((120, 0, 220, 100)),
        center=Point(170, 50),
    )

    elite = Agent.objects.create(
        simulation=simulation, name="Lord", role="merchant",
        social_class="elite", zone=z1,
        personality={"openness": 0.5}, location=Point(50, 50),
    )
    middle = Agent.objects.create(
        simulation=simulation, name="Artisan", role="craftsman",
        social_class="middle", zone=z1,
        personality={"openness": 0.5}, location=Point(50, 50),
    )
    worker = Agent.objects.create(
        simulation=simulation, name="Farmer", role="farmer",
        social_class="working", zone=z2,
        personality={"openness": 0.5}, location=Point(170, 50),
    )
    poor = Agent.objects.create(
        simulation=simulation, name="Beggar", role="farmer",
        social_class="poor", zone=z2,
        personality={"openness": 0.5}, location=Point(170, 50),
    )

    return {
        "world": world,
        "zones": [z1, z2],
        "agents": [elite, middle, worker, poor],
    }


@pytest.mark.django_db
class TestInitializeEconomy:
    def test_creates_currencies(self, simulation, world_with_agents):
        result = initialize_economy(simulation)
        assert result["currencies"] == 1
        assert Currency.objects.filter(simulation=simulation).count() == 1

    def test_creates_goods(self, simulation, world_with_agents):
        initialize_economy(simulation)
        goods = GoodCategory.objects.filter(simulation=simulation)
        assert goods.count() == 5
        assert goods.filter(is_essential=True).exists()

    def test_creates_factors(self, simulation, world_with_agents):
        initialize_economy(simulation)
        assert ProductionFactor.objects.filter(simulation=simulation).count() == 4

    def test_creates_tax_policy(self, simulation, world_with_agents):
        initialize_economy(simulation)
        tax = TaxPolicy.objects.get(simulation=simulation)
        assert 0.0 < tax.income_tax_rate < 1.0

    def test_creates_zone_economies(self, simulation, world_with_agents):
        initialize_economy(simulation)
        ze_count = ZoneEconomy.objects.filter(
            zone__world__simulation=simulation,
        ).count()
        assert ze_count == 2

    def test_zone_economy_has_prices(self, simulation, world_with_agents):
        initialize_economy(simulation)
        ze = ZoneEconomy.objects.filter(
            zone__world__simulation=simulation,
        ).first()
        assert len(ze.market_prices) == 5
        assert all(p > 0 for p in ze.market_prices.values())

    def test_zone_economy_has_natural_resources(self, simulation, world_with_agents):
        initialize_economy(simulation)
        urban_ze = ZoneEconomy.objects.get(zone__name="Paris")
        # Urban zones should have capital and knowledge resources
        assert "capital" in urban_ze.natural_resources

    def test_creates_inventories(self, simulation, world_with_agents):
        initialize_economy(simulation)
        assert AgentInventory.objects.filter(
            agent__simulation=simulation,
        ).count() == 4

    def test_inventory_has_cash(self, simulation, world_with_agents):
        initialize_economy(simulation)
        inv = AgentInventory.objects.filter(
            agent__simulation=simulation,
        ).first()
        total_cash = sum(inv.cash.values())
        assert total_cash > 0

    def test_inventory_has_essential_goods(self, simulation, world_with_agents):
        initialize_economy(simulation)
        inv = AgentInventory.objects.filter(
            agent__simulation=simulation,
        ).first()
        assert inv.holdings.get("subsistence", 0) == 2.0

    def test_elite_gets_more_cash_than_poor(self, simulation, world_with_agents):
        initialize_economy(simulation)
        elite_inv = AgentInventory.objects.get(agent__name="Lord")
        poor_inv = AgentInventory.objects.get(agent__name="Beggar")
        elite_cash = sum(elite_inv.cash.values())
        poor_cash = sum(poor_inv.cash.values())
        # Elite range [300,500] vs poor range [5,30]
        assert elite_cash > poor_cash

    def test_creates_properties_for_elite(self, simulation, world_with_agents):
        initialize_economy(simulation)
        props = Property.objects.filter(
            simulation=simulation, owner__name="Lord",
        )
        assert props.count() > 0

    def test_no_properties_for_poor(self, simulation, world_with_agents):
        initialize_economy(simulation)
        props = Property.objects.filter(
            simulation=simulation, owner__name="Beggar",
        )
        assert props.count() == 0

    def test_price_history_at_tick_zero(self, simulation, world_with_agents):
        initialize_economy(simulation)
        ph = PriceHistory.objects.filter(
            zone_economy__zone__world__simulation=simulation, tick=0,
        )
        assert ph.count() > 0

    def test_agent_wealth_updated(self, simulation, world_with_agents):
        initialize_economy(simulation)
        elite = Agent.objects.get(name="Lord")
        # Wealth should include cash + holdings value
        assert elite.wealth > 0

    def test_simulation_config_updated(self, simulation, world_with_agents):
        initialize_economy(simulation)
        simulation.refresh_from_db()
        prod_cfg = simulation.config.get("production_config", {})
        assert "default_sigma" in prod_cfg
        assert "role_production" in prod_cfg

    def test_overrides_applied(self, simulation, world_with_agents):
        overrides = {
            "tax_config": {"income_tax_rate": 0.40},
        }
        initialize_economy(simulation, overrides=overrides)
        tax = TaxPolicy.objects.get(simulation=simulation)
        assert tax.income_tax_rate == 0.40

    def test_industrial_template(self, simulation, world_with_agents):
        result = initialize_economy(simulation, template_name="industrial")
        assert result["currencies"] == 1
        currency = Currency.objects.get(simulation=simulation)
        assert currency.code == "GBP"


@pytest.fixture
def simulation_with_economy(db):
    """Simulation fully initialized with economy (pre_industrial template).

    Creates a minimal world (2 zones, 4 agents) and calls initialize_economy
    so tests can assert on the resulting simulation.config and related models.
    """
    from django.contrib.gis.geos import Point, Polygon

    from epocha.apps.simulation.models import Simulation
    from epocha.apps.users.models import User
    from epocha.apps.world.models import World, Zone

    user = User.objects.create_user(
        email="behav@epocha.dev",
        username="behavuser",
        password="pass1234",
    )
    sim = Simulation.objects.create(name="BehavTest", seed=99, owner=user)
    world = World.objects.create(
        simulation=sim,
        distance_scale=133.0,
        tick_duration_hours=24.0,
    )
    z1 = Zone.objects.create(
        world=world,
        name="BehavCity",
        zone_type="urban",
        boundary=Polygon.from_bbox((0, 0, 100, 100)),
        center=Point(50, 50),
    )
    z2 = Zone.objects.create(
        world=world,
        name="BehavRural",
        zone_type="rural",
        boundary=Polygon.from_bbox((120, 0, 220, 100)),
        center=Point(170, 50),
    )
    Agent.objects.create(
        simulation=sim,
        name="Lord2",
        role="merchant",
        social_class="elite",
        zone=z1,
        personality={"openness": 0.5},
        location=Point(50, 50),
    )
    Agent.objects.create(
        simulation=sim,
        name="Worker2",
        role="farmer",
        social_class="working",
        zone=z2,
        personality={"openness": 0.5},
        location=Point(170, 50),
    )
    initialize_economy(sim, "pre_industrial")
    return sim


@pytest.mark.django_db
class TestInitializationBehavioralConfig:
    """Test that initialize_economy saves behavioral configs to simulation.config."""

    def test_saves_credit_config(self, simulation_with_economy):
        sim = simulation_with_economy
        sim.refresh_from_db()
        sim_config = sim.config or {}
        assert "credit_config" in sim_config
        assert "loan_to_value" in sim_config["credit_config"]

    def test_saves_banking_config(self, simulation_with_economy):
        sim = simulation_with_economy
        sim.refresh_from_db()
        sim_config = sim.config or {}
        assert "banking_config" in sim_config
        assert "base_interest_rate" in sim_config["banking_config"]

    def test_saves_expectations_config(self, simulation_with_economy):
        sim = simulation_with_economy
        sim.refresh_from_db()
        sim_config = sim.config or {}
        assert "expectations_config" in sim_config
        assert "lambda_base" in sim_config["expectations_config"]

    def test_saves_expropriation_policies(self, simulation_with_economy):
        sim = simulation_with_economy
        sim.refresh_from_db()
        sim_config = sim.config or {}
        assert "expropriation_policies" in sim_config
        assert "democracy" in sim_config["expropriation_policies"]

    def test_banking_state_created(self, simulation_with_economy):
        from epocha.apps.economy.models import BankingState
        sim = simulation_with_economy
        assert BankingState.objects.filter(simulation=sim).exists()

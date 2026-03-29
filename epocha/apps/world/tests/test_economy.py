"""Tests for the basic economy tick processing."""
import pytest

from epocha.apps.agents.models import Agent
from epocha.apps.simulation.models import Simulation
from epocha.apps.users.models import User
from epocha.apps.world.economy import process_economy_tick
from epocha.apps.world.models import World


@pytest.fixture
def user(db):
    return User.objects.create_user(email="eco@epocha.dev", username="ecotest", password="pass123")


@pytest.fixture
def simulation(user):
    return Simulation.objects.create(name="EcoTest", seed=42, owner=user)


@pytest.fixture
def world(simulation):
    return World.objects.create(simulation=simulation, economy_level="base", global_wealth=1000)


@pytest.fixture
def farmer(simulation):
    return Agent.objects.create(simulation=simulation, name="Farmer", role="farmer", wealth=50)


@pytest.fixture
def blacksmith(simulation):
    return Agent.objects.create(simulation=simulation, name="Smith", role="blacksmith", wealth=50)


@pytest.mark.django_db
class TestProcessEconomyTick:
    def test_working_agent_earns_income(self, world, farmer):
        """Agents should earn income based on their role."""
        process_economy_tick(world, tick=1)
        farmer.refresh_from_db()
        assert farmer.wealth > 50  # Started at 50, should have earned income minus costs

    def test_different_roles_earn_differently(self, world, farmer, blacksmith):
        """A blacksmith should earn more than a farmer per tick."""
        process_economy_tick(world, tick=1)
        farmer.refresh_from_db()
        blacksmith.refresh_from_db()
        assert blacksmith.wealth > farmer.wealth

    def test_negative_wealth_decreases_health(self, world, simulation):
        """Agents with negative wealth should lose health (starvation)."""
        poor = Agent.objects.create(simulation=simulation, name="Poor", role="beggar", wealth=-10)
        process_economy_tick(world, tick=1)
        poor.refresh_from_db()
        assert poor.health < 1.0

    def test_negative_wealth_decreases_mood(self, world, simulation):
        """Agents with negative wealth should have very low mood."""
        poor = Agent.objects.create(simulation=simulation, name="Poor", role="beggar", wealth=-10)
        process_economy_tick(world, tick=1)
        poor.refresh_from_db()
        assert poor.mood < 0.5

    def test_rich_agent_mood_increases(self, world, simulation):
        """Wealthy agents should experience mood improvement."""
        rich = Agent.objects.create(simulation=simulation, name="Rich", role="merchant", wealth=200)
        process_economy_tick(world, tick=1)
        rich.refresh_from_db()
        assert rich.mood > 0.5

    def test_world_stability_updates(self, world, farmer):
        """World stability should reflect average agent mood."""
        process_economy_tick(world, tick=1)
        world.refresh_from_db()
        assert isinstance(world.stability_index, float)

    def test_dead_agents_are_skipped(self, world, simulation):
        """Dead agents should not earn income or affect stability."""
        dead = Agent.objects.create(simulation=simulation, name="Ghost", role="farmer", wealth=50, is_alive=False)
        process_economy_tick(world, tick=1)
        dead.refresh_from_db()
        assert dead.wealth == 50  # Unchanged

    def test_empty_simulation_does_not_crash(self, world):
        """A world with no agents should process without error."""
        process_economy_tick(world, tick=1)
        world.refresh_from_db()
        assert isinstance(world.stability_index, float)

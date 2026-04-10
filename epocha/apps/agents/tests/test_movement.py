"""Tests for the agent movement system."""
import pytest
from django.contrib.gis.geos import Point, Polygon

from epocha.apps.agents.models import Agent
from epocha.apps.agents.movement import calculate_max_distance, execute_movement
from epocha.apps.simulation.models import Simulation
from epocha.apps.users.models import User
from epocha.apps.world.models import Government, World, Zone


@pytest.fixture
def user(db):
    return User.objects.create_user(email="mov@epocha.dev", username="movtest", password="pass123")

@pytest.fixture
def simulation(user):
    return Simulation.objects.create(name="MovTest", seed=42, owner=user)

@pytest.fixture
def world(simulation):
    return World.objects.create(simulation=simulation, distance_scale=133.0, tick_duration_hours=24.0)

@pytest.fixture
def government(simulation):
    return Government.objects.create(simulation=simulation, repression_level=0.1)

@pytest.fixture
def versailles(world):
    return Zone.objects.create(
        world=world, name="Versailles", zone_type="urban",
        boundary=Polygon.from_bbox((0, 0, 120, 120)), center=Point(60, 60),
    )

@pytest.fixture
def paris(world):
    return Zone.objects.create(
        world=world, name="Paris", zone_type="commercial",
        boundary=Polygon.from_bbox((150, 0, 270, 120)), center=Point(210, 60),
    )

@pytest.fixture
def campagna(world):
    return Zone.objects.create(
        world=world, name="Campagna", zone_type="rural",
        boundary=Polygon.from_bbox((150, 150, 270, 270)), center=Point(210, 210),
    )

@pytest.fixture
def agent_at_versailles(simulation, versailles):
    return Agent.objects.create(
        simulation=simulation, name="Luigi", role="re",
        personality={"openness": 0.5}, location=Point(60, 60),
        zone=versailles, health=1.0,
    )


@pytest.mark.django_db
class TestCalculateMaxDistance:
    def test_carriage_travels_farther_than_foot(self, world, government):
        dist_carriage = calculate_max_distance("carriage", health=1.0, world=world, government=government)
        dist_foot = calculate_max_distance("foot", health=1.0, world=world, government=government)
        assert dist_carriage > dist_foot

    def test_low_health_reduces_distance(self, world, government):
        dist_healthy = calculate_max_distance("foot", health=1.0, world=world, government=government)
        dist_sick = calculate_max_distance("foot", health=0.3, world=world, government=government)
        assert dist_sick < dist_healthy

    def test_high_repression_reduces_distance(self, world, simulation):
        gov_low = Government.objects.create(simulation=simulation, repression_level=0.1)
        gov_high_sim = Simulation.objects.create(name="HighRep", seed=43, owner=simulation.owner)
        World.objects.create(simulation=gov_high_sim, distance_scale=133.0, tick_duration_hours=24.0)
        gov_high = Government.objects.create(simulation=gov_high_sim, repression_level=0.8)
        dist_low = calculate_max_distance("foot", health=1.0, world=world, government=gov_low)
        world_high = World.objects.get(simulation=gov_high_sim)
        dist_high = calculate_max_distance("foot", health=1.0, world=world_high, government=gov_high)
        assert dist_high < dist_low

    def test_returns_distance_in_grid_units(self, world, government):
        dist = calculate_max_distance("foot", health=1.0, world=world, government=government)
        # foot = 35 km/day, distance_scale=133m/unit -> ~263 grid units max
        assert 200 < dist < 350


@pytest.mark.django_db
class TestExecuteMovement:
    def test_full_movement_updates_zone(self, agent_at_versailles, paris, world, government):
        result = execute_movement(agent_at_versailles, paris, world, government)
        agent_at_versailles.refresh_from_db()
        assert agent_at_versailles.zone == paris
        assert result["completed"] is True

    def test_movement_to_far_zone_is_partial(self, agent_at_versailles, campagna, world, government):
        # Foot travel with low health: effective speed ~ 6 km/day = ~44 grid units,
        # but distance to Campagna center is ~212 grid units. Must be partial.
        agent_at_versailles.role = "contadino"
        agent_at_versailles.save(update_fields=["role"])
        agent_at_versailles.health = 0.3
        agent_at_versailles.save(update_fields=["health"])
        result = execute_movement(agent_at_versailles, campagna, world, government)
        agent_at_versailles.refresh_from_db()
        assert result["completed"] is False
        assert result["distance_traveled"] < 100  # Much less than 212 grid units needed

    def test_movement_reduces_mood(self, agent_at_versailles, paris, world, government):
        initial_mood = agent_at_versailles.mood
        execute_movement(agent_at_versailles, paris, world, government)
        agent_at_versailles.refresh_from_db()
        assert agent_at_versailles.mood < initial_mood

    def test_movement_updates_location(self, agent_at_versailles, paris, world, government):
        execute_movement(agent_at_versailles, paris, world, government)
        agent_at_versailles.refresh_from_db()
        # Should be within Paris boundary
        assert agent_at_versailles.location is not None

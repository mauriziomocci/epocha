"""Tests for per-tick snapshot capture."""
import pytest

from epocha.apps.agents.models import Agent, Group
from epocha.apps.simulation.models import Simulation, SimulationSnapshot
from epocha.apps.simulation.snapshot import capture_snapshot
from epocha.apps.users.models import User
from epocha.apps.world.models import Government, World


@pytest.fixture
def user(db):
    return User.objects.create_user(email="snap@epocha.dev", username="snaptest", password="pass123")


@pytest.fixture
def simulation(user):
    return Simulation.objects.create(name="SnapTest", seed=42, owner=user)


@pytest.fixture
def world(simulation):
    return World.objects.create(simulation=simulation)


@pytest.fixture
def government(simulation):
    return Government.objects.create(
        simulation=simulation, government_type="democracy",
        stability=0.6, institutional_trust=0.5, repression_level=0.1,
        corruption=0.2, popular_legitimacy=0.5, military_loyalty=0.5,
    )


@pytest.fixture
def agents(simulation):
    agents = []
    for name, wealth, mood, social_class in [
        ("Rich", 200.0, 0.8, "wealthy"),
        ("Mid", 80.0, 0.5, "middle"),
        ("Poor", 10.0, 0.2, "poor"),
    ]:
        agents.append(Agent.objects.create(
            simulation=simulation, name=name, role="citizen",
            wealth=wealth, mood=mood, social_class=social_class,
            personality={"openness": 0.5},
        ))
    return agents


@pytest.fixture
def faction(simulation):
    return Group.objects.create(simulation=simulation, name="The Guild", cohesion=0.7, formed_at_tick=1)


@pytest.mark.django_db
class TestCaptureSnapshot:
    def test_creates_snapshot_record(self, simulation, world, government, agents):
        capture_snapshot(simulation, tick=5)
        assert SimulationSnapshot.objects.filter(simulation=simulation, tick=5).exists()

    def test_captures_population(self, simulation, world, government, agents):
        agents[2].is_alive = False
        agents[2].save(update_fields=["is_alive"])
        capture_snapshot(simulation, tick=5)
        snap = SimulationSnapshot.objects.get(simulation=simulation, tick=5)
        assert snap.population_alive == 2
        assert snap.population_dead == 1

    def test_captures_economy(self, simulation, world, government, agents):
        capture_snapshot(simulation, tick=5)
        snap = SimulationSnapshot.objects.get(simulation=simulation, tick=5)
        assert snap.avg_wealth > 0
        assert 0.0 <= snap.gini_coefficient <= 1.0

    def test_captures_mood(self, simulation, world, government, agents):
        capture_snapshot(simulation, tick=5)
        snap = SimulationSnapshot.objects.get(simulation=simulation, tick=5)
        assert snap.avg_mood == pytest.approx(0.5, abs=0.1)

    def test_captures_government_indicators(self, simulation, world, government, agents):
        capture_snapshot(simulation, tick=5)
        snap = SimulationSnapshot.objects.get(simulation=simulation, tick=5)
        assert snap.government_type == "democracy"
        assert snap.government_stability == pytest.approx(0.6)
        assert snap.institutional_trust == pytest.approx(0.5)

    def test_captures_faction_count(self, simulation, world, government, agents, faction):
        capture_snapshot(simulation, tick=5)
        snap = SimulationSnapshot.objects.get(simulation=simulation, tick=5)
        assert snap.faction_count == 1

    def test_captures_class_distribution(self, simulation, world, government, agents):
        capture_snapshot(simulation, tick=5)
        snap = SimulationSnapshot.objects.get(simulation=simulation, tick=5)
        total = (
            snap.class_elite_pct + snap.class_wealthy_pct + snap.class_middle_pct
            + snap.class_working_pct + snap.class_poor_pct
        )
        assert abs(total - 1.0) < 0.01

    def test_no_government_still_works(self, simulation, world, agents):
        capture_snapshot(simulation, tick=5)
        snap = SimulationSnapshot.objects.get(simulation=simulation, tick=5)
        assert snap.government_type == ""
        assert snap.government_stability == 0.0

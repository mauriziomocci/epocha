"""Tests for Epochal Crisis detection."""
import pytest

from epocha.apps.agents.models import Agent, Group, Memory
from epocha.apps.simulation.crisis import detect_crises
from epocha.apps.simulation.models import Event, Simulation, SimulationSnapshot
from epocha.apps.users.models import User
from epocha.apps.world.models import Government, World


@pytest.fixture
def user(db):
    return User.objects.create_user(email="crisis@epocha.dev", username="crisistest", password="pass123")

@pytest.fixture
def simulation(user):
    return Simulation.objects.create(name="CrisisTest", seed=42, owner=user)

@pytest.fixture
def world(simulation):
    return World.objects.create(simulation=simulation)

@pytest.fixture
def government(simulation):
    return Government.objects.create(simulation=simulation, government_type="democracy")

@pytest.fixture
def snapshot_inequality(simulation):
    return SimulationSnapshot.objects.create(
        simulation=simulation, tick=10,
        gini_coefficient=0.7, government_stability=0.3,
        avg_mood=0.5, institutional_trust=0.5, corruption=0.2,
        popular_legitimacy=0.5, military_loyalty=0.5, population_alive=20,
    )

@pytest.fixture
def snapshot_stable(simulation):
    return SimulationSnapshot.objects.create(
        simulation=simulation, tick=10,
        gini_coefficient=0.3, government_stability=0.7,
        avg_mood=0.6, institutional_trust=0.6, corruption=0.2,
        popular_legitimacy=0.6, military_loyalty=0.6, population_alive=20,
    )


@pytest.mark.django_db
class TestDetectCrises:
    def test_detects_inequality_crisis(self, simulation, world, government, snapshot_inequality):
        crises = detect_crises(simulation, snapshot_inequality)
        types = [c["type"] for c in crises]
        assert "inequality_crisis" in types

    def test_no_crisis_when_stable(self, simulation, world, government, snapshot_stable):
        crises = detect_crises(simulation, snapshot_stable)
        assert len(crises) == 0

    def test_creates_event_on_crisis(self, simulation, world, government, snapshot_inequality):
        detect_crises(simulation, snapshot_inequality)
        events = Event.objects.filter(simulation=simulation, title__startswith="[EPOCHAL CRISIS]")
        assert events.count() >= 1

    def test_creates_public_memory_on_crisis(self, simulation, world, government, snapshot_inequality):
        Agent.objects.create(simulation=simulation, name="Marco", role="citizen", personality={"openness": 0.5})
        detect_crises(simulation, snapshot_inequality)
        memories = Memory.objects.filter(source_type="public", content__contains="EPOCHAL CRISIS")
        assert memories.count() >= 1

    def test_cooldown_prevents_duplicate_crisis(self, simulation, world, government, snapshot_inequality):
        detect_crises(simulation, snapshot_inequality)
        snap2 = SimulationSnapshot.objects.create(
            simulation=simulation, tick=12,
            gini_coefficient=0.7, government_stability=0.3,
            avg_mood=0.5, institutional_trust=0.5, corruption=0.2,
            popular_legitimacy=0.5, military_loyalty=0.5, population_alive=20,
        )
        crises = detect_crises(simulation, snap2)
        types = [c["type"] for c in crises]
        assert "inequality_crisis" not in types

    def test_detects_institutional_collapse(self, simulation, world, government):
        snap = SimulationSnapshot.objects.create(
            simulation=simulation, tick=10,
            gini_coefficient=0.3, government_stability=0.5,
            avg_mood=0.5, institutional_trust=0.15, corruption=0.7,
            popular_legitimacy=0.5, military_loyalty=0.5, population_alive=20,
        )
        crises = detect_crises(simulation, snap)
        types = [c["type"] for c in crises]
        assert "institutional_collapse" in types

    def test_multiple_crises_can_fire_simultaneously(self, simulation, world, government):
        snap = SimulationSnapshot.objects.create(
            simulation=simulation, tick=10,
            gini_coefficient=0.7, government_stability=0.2,
            avg_mood=0.2, institutional_trust=0.15, corruption=0.7,
            popular_legitimacy=0.15, military_loyalty=0.5, population_alive=20,
        )
        crises = detect_crises(simulation, snap)
        assert len(crises) >= 2

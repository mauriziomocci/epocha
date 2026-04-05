"""Tests for social stratification dynamics."""
import pytest

from epocha.apps.agents.models import Agent
from epocha.apps.simulation.models import Simulation
from epocha.apps.users.models import User
from epocha.apps.world.models import World
from epocha.apps.world.stratification import compute_gini, update_social_classes


@pytest.fixture
def user(db):
    return User.objects.create_user(email="strat@epocha.dev", username="strattest", password="pass123")

@pytest.fixture
def simulation(user):
    return Simulation.objects.create(name="StratTest", seed=42, owner=user)

@pytest.fixture
def world(simulation):
    return World.objects.create(simulation=simulation)

@pytest.fixture
def agents_with_wealth(simulation):
    agents = []
    for i, (name, wealth) in enumerate([
        ("Ultra", 1000.0), ("Rich", 500.0), ("Upper", 200.0),
        ("Mid1", 100.0), ("Mid2", 90.0), ("Mid3", 80.0),
        ("Work1", 50.0), ("Work2", 40.0),
        ("Poor1", 10.0), ("Poor2", 5.0),
    ]):
        agents.append(Agent.objects.create(
            simulation=simulation, name=name, role="citizen", wealth=wealth,
            social_class="working",
            personality={"openness": 0.5, "conscientiousness": 0.5, "extraversion": 0.5,
                         "agreeableness": 0.5, "neuroticism": 0.5},
        ))
    return agents


class TestComputeGini:
    def test_perfect_equality(self):
        gini = compute_gini([50.0, 50.0, 50.0, 50.0])
        assert abs(gini) < 0.01

    def test_high_inequality(self):
        gini = compute_gini([0.0, 0.0, 0.0, 1000.0])
        assert gini > 0.7

    def test_moderate_inequality(self):
        gini = compute_gini([10.0, 30.0, 50.0, 80.0, 200.0])
        assert 0.2 < gini < 0.6

    def test_single_agent(self):
        gini = compute_gini([100.0])
        assert gini == 0.0

    def test_empty_list(self):
        gini = compute_gini([])
        assert gini == 0.0


@pytest.mark.django_db
class TestUpdateSocialClasses:
    def test_wealthiest_becomes_elite(self, simulation, world, agents_with_wealth):
        update_social_classes(simulation)
        ultra = Agent.objects.get(name="Ultra")
        assert ultra.social_class == "elite"

    def test_poorest_becomes_poor(self, simulation, world, agents_with_wealth):
        update_social_classes(simulation)
        poor = Agent.objects.get(name="Poor2")
        assert poor.social_class == "poor"

    def test_middle_agents_classified_correctly(self, simulation, world, agents_with_wealth):
        update_social_classes(simulation)
        mid = Agent.objects.get(name="Mid2")
        assert mid.social_class in ("middle", "working")

    def test_classes_cover_all_agents(self, simulation, world, agents_with_wealth):
        update_social_classes(simulation)
        valid = {"elite", "wealthy", "middle", "working", "poor"}
        for agent in Agent.objects.filter(simulation=simulation):
            assert agent.social_class in valid

"""Tests for the government engine."""
import pytest

from epocha.apps.agents.models import Agent, Group, Memory
from epocha.apps.simulation.models import Simulation
from epocha.apps.users.models import User
from epocha.apps.world.government import (
    check_transitions,
    process_political_cycle,
    update_government_indicators,
)
from epocha.apps.world.models import Government, GovernmentHistory, Institution, World


@pytest.fixture
def user(db):
    return User.objects.create_user(email="gov@epocha.dev", username="govtest", password="pass123")

@pytest.fixture
def simulation(user):
    return Simulation.objects.create(name="GovTest", seed=42, owner=user)

@pytest.fixture
def world(simulation):
    return World.objects.create(simulation=simulation)

@pytest.fixture
def government(simulation):
    return Government.objects.create(
        simulation=simulation, government_type="democracy", stability=0.5,
        institutional_trust=0.5, repression_level=0.1, corruption=0.2,
        popular_legitimacy=0.5, military_loyalty=0.5,
    )

@pytest.fixture
def all_institutions(simulation):
    types = ["justice", "education", "health", "military", "media", "religion", "bureaucracy"]
    return [Institution.objects.create(simulation=simulation, institution_type=t, health=0.5, independence=0.5, funding=0.5) for t in types]

@pytest.fixture
def faction_with_leader(simulation):
    group = Group.objects.create(simulation=simulation, name="Rebels", objective="Overthrow", cohesion=0.8, formed_at_tick=1)
    leader = Agent.objects.create(
        simulation=simulation, name="Che", role="revolutionary", charisma=0.9,
        intelligence=0.7, wealth=20.0, group=group,
        personality={"openness": 0.8, "conscientiousness": 0.5, "extraversion": 0.8, "agreeableness": 0.3, "neuroticism": 0.6},
    )
    group.leader = leader
    group.save(update_fields=["leader"])
    return group, leader


@pytest.mark.django_db
class TestUpdateIndicators:
    def test_indicators_change_after_update(self, simulation, world, government, all_institutions):
        update_government_indicators(simulation)
        government.refresh_from_db()
        assert isinstance(government.institutional_trust, float)

    def test_indicators_clamped_to_range(self, simulation, world, government, all_institutions):
        government.institutional_trust = 0.99
        government.corruption = 0.01
        government.save(update_fields=["institutional_trust", "corruption"])
        update_government_indicators(simulation)
        government.refresh_from_db()
        for field in ["institutional_trust", "repression_level", "corruption", "popular_legitimacy", "military_loyalty"]:
            val = getattr(government, field)
            assert 0.0 <= val <= 1.0, f"{field} = {val}"

    def test_repression_drifts_toward_type_tendency(self, simulation, world, government, all_institutions):
        government.government_type = "autocracy"
        government.repression_level = 0.1
        government.save(update_fields=["government_type", "repression_level"])
        update_government_indicators(simulation)
        government.refresh_from_db()
        assert government.repression_level > 0.1


@pytest.mark.django_db
class TestTransitions:
    def test_democracy_to_illiberal_on_low_trust_high_repression(self, simulation, world, government, all_institutions):
        government.institutional_trust = 0.2
        government.repression_level = 0.4
        government.save(update_fields=["institutional_trust", "repression_level"])
        result = check_transitions(simulation)
        assert result is not None
        government.refresh_from_db()
        assert government.government_type == "illiberal_democracy"

    def test_no_transition_when_stable(self, simulation, world, government, all_institutions):
        government.institutional_trust = 0.7
        government.popular_legitimacy = 0.6
        government.repression_level = 0.05
        government.save(update_fields=["institutional_trust", "popular_legitimacy", "repression_level"])
        result = check_transitions(simulation)
        assert result is None
        government.refresh_from_db()
        assert government.government_type == "democracy"

    def test_transition_creates_history_record(self, simulation, world, government, all_institutions):
        government.institutional_trust = 0.2
        government.repression_level = 0.4
        government.save(update_fields=["institutional_trust", "repression_level"])
        check_transitions(simulation)
        assert GovernmentHistory.objects.filter(simulation=simulation).count() >= 1

    def test_coup_succeeds_when_conditions_met(self, simulation, world, government, all_institutions, faction_with_leader):
        """Coup evaluation is stochastic. We seed the RNG so the test is deterministic."""
        import random
        government.military_loyalty = 0.2
        government.stability = 0.2
        government.save(update_fields=["military_loyalty", "stability"])
        group, leader = faction_with_leader
        for i in range(3):
            Agent.objects.create(
                simulation=simulation, name=f"Rebel{i}", role="fighter", charisma=0.3, group=group,
                personality={"openness": 0.5, "conscientiousness": 0.5, "extraversion": 0.5, "agreeableness": 0.5, "neuroticism": 0.5},
            )
        from epocha.apps.world.government import check_coups
        # Seed produces a low first random.random() value, ensuring the coup
        # succeeds given the high success_probability (~0.80).
        random.seed(42)
        result = check_coups(simulation, tick=20)
        assert result is not None, "Coup should succeed with seeded RNG (seed=42, P~0.80)"
        government.refresh_from_db()
        assert government.head_of_state == leader

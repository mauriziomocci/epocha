"""Tests for the faction dynamics engine."""
import pytest

from epocha.apps.agents.factions import (
    compute_leadership_score,
    compute_legitimacy,
    update_group_cohesion,
    update_group_leadership,
)
from epocha.apps.agents.models import Agent, DecisionLog, Group, Memory, Relationship
from epocha.apps.simulation.models import Simulation
from epocha.apps.users.models import User
from epocha.apps.world.models import World


@pytest.fixture
def user(db):
    return User.objects.create_user(email="fac@epocha.dev", username="factest", password="pass123")


@pytest.fixture
def simulation(user):
    return Simulation.objects.create(name="FacTest", seed=42, owner=user)


@pytest.fixture
def world(simulation):
    return World.objects.create(simulation=simulation)


@pytest.fixture
def group_with_members(simulation):
    group = Group.objects.create(
        simulation=simulation, name="The Guild", objective="Protect artisans",
        cohesion=0.6, formed_at_tick=1,
    )
    marco = Agent.objects.create(
        simulation=simulation, name="Marco", role="blacksmith",
        personality={"openness": 0.5, "conscientiousness": 0.5, "extraversion": 0.5,
                     "agreeableness": 0.5, "neuroticism": 0.5},
        charisma=0.8, intelligence=0.7, wealth=60.0, group=group,
    )
    elena = Agent.objects.create(
        simulation=simulation, name="Elena", role="farmer",
        personality={"openness": 0.5, "conscientiousness": 0.5, "extraversion": 0.5,
                     "agreeableness": 0.5, "neuroticism": 0.5},
        charisma=0.4, intelligence=0.5, wealth=30.0, group=group,
    )
    carlo = Agent.objects.create(
        simulation=simulation, name="Carlo", role="priest",
        personality={"openness": 0.5, "conscientiousness": 0.5, "extraversion": 0.5,
                     "agreeableness": 0.5, "neuroticism": 0.5},
        charisma=0.6, intelligence=0.6, wealth=45.0, group=group,
    )
    group.leader = marco
    group.save(update_fields=["leader"])
    # Memories for seniority tracking
    Memory.objects.create(agent=marco, content="I helped found The Guild", emotional_weight=0.3,
                          source_type="direct", tick_created=1)
    Memory.objects.create(agent=elena, content="I helped found The Guild", emotional_weight=0.3,
                          source_type="direct", tick_created=1)
    Memory.objects.create(agent=carlo, content="I joined The Guild", emotional_weight=0.3,
                          source_type="direct", tick_created=5)
    return group, marco, elena, carlo


@pytest.mark.django_db
class TestLeadershipScore:
    def test_charismatic_wealthy_agent_scores_high(self, group_with_members):
        group, marco, elena, carlo = group_with_members
        Relationship.objects.create(agent_from=marco, agent_to=elena,
                                    relation_type="friendship", strength=0.7, sentiment=0.6, since_tick=0)
        Relationship.objects.create(agent_from=marco, agent_to=carlo,
                                    relation_type="professional", strength=0.5, sentiment=0.3, since_tick=0)
        score = compute_leadership_score(marco, group, tick=10)
        assert score > 0.5

    def test_low_charisma_agent_scores_low(self, group_with_members):
        group, marco, elena, carlo = group_with_members
        score = compute_leadership_score(elena, group, tick=10)
        assert score < compute_leadership_score(marco, group, tick=10)

    def test_score_range_zero_to_one(self, group_with_members):
        group, marco, elena, carlo = group_with_members
        for agent in [marco, elena, carlo]:
            score = compute_leadership_score(agent, group, tick=10)
            assert 0.0 <= score <= 1.0


@pytest.mark.django_db
class TestCohesionUpdate:
    def test_cooperation_increases_cohesion(self, simulation, world, group_with_members):
        group, marco, elena, carlo = group_with_members
        # Marco helps Elena (cooperation)
        DecisionLog.objects.create(
            simulation=simulation, agent=marco, tick=9,
            input_context="", output_decision='{"action": "help", "target": "Elena"}',
            llm_model="test",
        )
        initial_cohesion = group.cohesion
        update_group_cohesion(group, simulation, tick=10)
        group.refresh_from_db()
        assert group.cohesion > initial_cohesion

    def test_conflict_decreases_cohesion(self, simulation, world, group_with_members):
        group, marco, elena, carlo = group_with_members
        # Marco argues with Elena (conflict)
        DecisionLog.objects.create(
            simulation=simulation, agent=marco, tick=9,
            input_context="", output_decision='{"action": "argue", "target": "Elena"}',
            llm_model="test",
        )
        initial_cohesion = group.cohesion
        update_group_cohesion(group, simulation, tick=10)
        group.refresh_from_db()
        assert group.cohesion < initial_cohesion

    def test_cohesion_clamped_to_range(self, simulation, world, group_with_members):
        group, marco, elena, carlo = group_with_members
        group.cohesion = 0.99
        group.save(update_fields=["cohesion"])
        update_group_cohesion(group, simulation, tick=10)
        group.refresh_from_db()
        assert 0.0 <= group.cohesion <= 1.0


@pytest.mark.django_db
class TestLeadershipContestaton:
    def test_legitimate_leader_stays(self, simulation, world, group_with_members):
        group, marco, elena, carlo = group_with_members
        Relationship.objects.create(agent_from=marco, agent_to=elena,
                                    relation_type="friendship", strength=0.7, sentiment=0.6, since_tick=0)
        Relationship.objects.create(agent_from=marco, agent_to=carlo,
                                    relation_type="professional", strength=0.5, sentiment=0.3, since_tick=0)
        update_group_leadership(group, tick=10)
        group.refresh_from_db()
        assert group.leader == marco

    def test_unpopular_leader_replaced(self, simulation, world, group_with_members):
        group, marco, elena, carlo = group_with_members
        # Marco has terrible relationships with everyone
        Relationship.objects.create(agent_from=marco, agent_to=elena,
                                    relation_type="rivalry", strength=0.8, sentiment=-0.8, since_tick=0)
        Relationship.objects.create(agent_from=marco, agent_to=carlo,
                                    relation_type="distrust", strength=0.7, sentiment=-0.6, since_tick=0)
        # Lower group cohesion enough that legitimacy falls below the 0.3 threshold.
        # With cohesion=0.05, leader_sentiment=0.15 (from avg normalized -0.7),
        # score_rank=1.0: legitimacy = 0.05*0.4 + 0.15*0.4 + 1.0*0.2 = 0.28 < 0.3.
        group.cohesion = 0.05
        group.save(update_fields=["cohesion"])
        update_group_leadership(group, tick=10)
        group.refresh_from_db()
        assert group.leader != marco

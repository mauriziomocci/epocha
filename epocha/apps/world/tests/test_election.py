"""Tests for the deterministic election system."""
import pytest

from epocha.apps.agents.models import Agent, Group, Memory, Relationship
from epocha.apps.simulation.models import Simulation
from epocha.apps.users.models import User
from epocha.apps.world.election import compute_vote_score, run_election
from epocha.apps.world.models import Government, World


@pytest.fixture
def user(db):
    return User.objects.create_user(email="elec@epocha.dev", username="electest", password="pass123")

@pytest.fixture
def simulation(user):
    return Simulation.objects.create(name="ElecTest", seed=42, owner=user)

@pytest.fixture
def world(simulation):
    return World.objects.create(simulation=simulation)

@pytest.fixture
def government(simulation):
    return Government.objects.create(simulation=simulation, government_type="democracy", last_election_tick=0)

@pytest.fixture
def factions_and_agents(simulation):
    faction_a = Group.objects.create(simulation=simulation, name="Reformers", objective="Reform", cohesion=0.7, formed_at_tick=1)
    faction_b = Group.objects.create(simulation=simulation, name="Traditionalists", objective="Preserve", cohesion=0.6, formed_at_tick=1)
    leader_a = Agent.objects.create(
        simulation=simulation, name="Anna", role="politician",
        charisma=0.8, intelligence=0.7, wealth=100.0, group=faction_a,
        personality={"openness": 0.8, "conscientiousness": 0.6, "extraversion": 0.7, "agreeableness": 0.5, "neuroticism": 0.3},
    )
    leader_b = Agent.objects.create(
        simulation=simulation, name="Bruno", role="general",
        charisma=0.5, intelligence=0.6, wealth=80.0, group=faction_b,
        personality={"openness": 0.3, "conscientiousness": 0.7, "extraversion": 0.4, "agreeableness": 0.4, "neuroticism": 0.5},
    )
    faction_a.leader = leader_a
    faction_a.save(update_fields=["leader"])
    faction_b.leader = leader_b
    faction_b.save(update_fields=["leader"])
    voter = Agent.objects.create(
        simulation=simulation, name="Citizen", role="farmer",
        charisma=0.3, intelligence=0.5, wealth=50.0, mood=0.5,
        personality={"openness": 0.6, "conscientiousness": 0.5, "extraversion": 0.5, "agreeableness": 0.5, "neuroticism": 0.5},
    )
    return faction_a, faction_b, leader_a, leader_b, voter


@pytest.mark.django_db
class TestComputeVoteScore:
    def test_charismatic_candidate_scores_higher(self, simulation, world, factions_and_agents):
        _, _, leader_a, leader_b, voter = factions_and_agents
        score_a = compute_vote_score(voter, leader_a, tick=50)
        score_b = compute_vote_score(voter, leader_b, tick=50)
        assert score_a > score_b

    def test_positive_memory_boosts_score(self, simulation, world, factions_and_agents):
        _, _, leader_a, _, voter = factions_and_agents
        score_before = compute_vote_score(voter, leader_a, tick=50)
        Memory.objects.create(agent=voter, content="Anna helped the poor and reformed the tax system.",
                              emotional_weight=0.5, source_type="hearsay", tick_created=45)
        score_after = compute_vote_score(voter, leader_a, tick=50)
        assert score_after > score_before

    def test_negative_memory_reduces_score(self, simulation, world, factions_and_agents):
        _, _, leader_a, _, voter = factions_and_agents
        score_before = compute_vote_score(voter, leader_a, tick=50)
        Memory.objects.create(agent=voter, content="Anna betrayed the people and stole from the treasury.",
                              emotional_weight=0.7, source_type="rumor", tick_created=45)
        score_after = compute_vote_score(voter, leader_a, tick=50)
        assert score_after < score_before

    def test_relationship_influences_vote(self, simulation, world, factions_and_agents):
        _, _, leader_a, _, voter = factions_and_agents
        score_no_rel = compute_vote_score(voter, leader_a, tick=50)
        Relationship.objects.create(agent_from=voter, agent_to=leader_a,
                                    relation_type="friendship", strength=0.8, sentiment=0.7, since_tick=0)
        score_with_rel = compute_vote_score(voter, leader_a, tick=50)
        assert score_with_rel > score_no_rel


@pytest.mark.django_db
class TestRunElection:
    def test_election_sets_head_of_state(self, simulation, world, government, factions_and_agents):
        _, _, leader_a, leader_b, voter = factions_and_agents
        run_election(simulation, tick=50)
        government.refresh_from_db()
        assert government.head_of_state in (leader_a, leader_b)
        assert government.ruling_faction is not None
        assert government.last_election_tick == 50

    def test_election_creates_public_memory(self, simulation, world, government, factions_and_agents):
        run_election(simulation, tick=50)
        for agent in Agent.objects.filter(simulation=simulation, is_alive=True):
            assert Memory.objects.filter(agent=agent, source_type="public", content__contains="won the election").count() >= 1

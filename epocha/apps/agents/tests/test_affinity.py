"""Tests for agent pairwise affinity calculation."""
import math

import pytest

from epocha.apps.agents.affinity import compute_affinity
from epocha.apps.agents.models import Agent, Memory, Relationship
from epocha.apps.simulation.models import Simulation
from epocha.apps.users.models import User
from epocha.apps.world.models import World


@pytest.fixture
def user(db):
    return User.objects.create_user(email="aff@epocha.dev", username="afftest", password="pass123")


@pytest.fixture
def simulation(user):
    return Simulation.objects.create(name="AffTest", seed=42, owner=user)


@pytest.fixture
def world(simulation):
    return World.objects.create(simulation=simulation)


@pytest.fixture
def marco(simulation):
    return Agent.objects.create(
        simulation=simulation, name="Marco", role="blacksmith",
        social_class="working", mood=0.3, wealth=30.0,
        personality={
            "openness": 0.8, "conscientiousness": 0.6, "extraversion": 0.4,
            "agreeableness": 0.3, "neuroticism": 0.7,
        },
    )


@pytest.fixture
def elena(simulation):
    return Agent.objects.create(
        simulation=simulation, name="Elena", role="farmer",
        social_class="working", mood=0.3, wealth=35.0,
        personality={
            "openness": 0.7, "conscientiousness": 0.5, "extraversion": 0.5,
            "agreeableness": 0.4, "neuroticism": 0.6,
        },
    )


@pytest.fixture
def carlo(simulation):
    return Agent.objects.create(
        simulation=simulation, name="Carlo", role="priest",
        social_class="middle", mood=0.7, wealth=80.0,
        personality={
            "openness": 0.2, "conscientiousness": 0.9, "extraversion": 0.3,
            "agreeableness": 0.8, "neuroticism": 0.1,
        },
    )


@pytest.mark.django_db
class TestComputeAffinity:
    def test_similar_agents_high_affinity(self, simulation, world, marco, elena):
        """Agents with similar personality, same class, both low mood = high affinity."""
        Relationship.objects.create(
            agent_from=marco, agent_to=elena,
            relation_type="friendship", strength=0.7, sentiment=0.5, since_tick=0,
        )
        score = compute_affinity(marco, elena, tick=10)
        assert score > 0.5

    def test_dissimilar_agents_low_affinity(self, simulation, world, marco, carlo):
        """Agents with very different personality, different class, different mood."""
        score = compute_affinity(marco, carlo, tick=10)
        assert score < 0.4

    def test_no_relationship_zero_relationship_score(self, simulation, world, marco, elena):
        """Without a relationship, the relationship component is 0."""
        score_no_rel = compute_affinity(marco, elena, tick=10)
        Relationship.objects.create(
            agent_from=marco, agent_to=elena,
            relation_type="friendship", strength=0.8, sentiment=0.6, since_tick=0,
        )
        score_with_rel = compute_affinity(marco, elena, tick=10)
        assert score_with_rel > score_no_rel

    def test_shared_public_memory_increases_affinity(self, simulation, world, marco, elena):
        """Agents sharing a recent public memory have higher affinity."""
        score_before = compute_affinity(marco, elena, tick=10)
        Memory.objects.create(
            agent=marco, content="Plague outbreak: terrible plague",
            emotional_weight=0.9, source_type="public", tick_created=8,
        )
        Memory.objects.create(
            agent=elena, content="Plague outbreak: terrible plague",
            emotional_weight=0.9, source_type="public", tick_created=8,
        )
        score_after = compute_affinity(marco, elena, tick=10)
        assert score_after > score_before

    def test_same_role_increases_affinity(self, simulation, world, marco):
        """Two agents with the same role get a small boost."""
        marco2 = Agent.objects.create(
            simulation=simulation, name="Luigi", role="blacksmith",
            social_class="working", mood=0.5, wealth=40.0,
            personality={
                "openness": 0.3, "conscientiousness": 0.3, "extraversion": 0.3,
                "agreeableness": 0.3, "neuroticism": 0.3,
            },
        )
        score = compute_affinity(marco, marco2, tick=10)
        marco2.role = "farmer"
        marco2.save(update_fields=["role"])
        score_diff_role = compute_affinity(marco, marco2, tick=10)
        assert score > score_diff_role

    def test_affinity_is_symmetric(self, simulation, world, marco, elena):
        """affinity(A, B) == affinity(B, A)."""
        Relationship.objects.create(
            agent_from=marco, agent_to=elena,
            relation_type="friendship", strength=0.6, sentiment=0.4, since_tick=0,
        )
        score_ab = compute_affinity(marco, elena, tick=10)
        score_ba = compute_affinity(elena, marco, tick=10)
        assert abs(score_ab - score_ba) < 0.01

    def test_affinity_range_zero_to_one(self, simulation, world, marco, carlo):
        """Affinity score must be between 0.0 and 1.0."""
        score = compute_affinity(marco, carlo, tick=10)
        assert 0.0 <= score <= 1.0

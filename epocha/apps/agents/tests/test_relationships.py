"""Tests for the living relationships system."""
import pytest
from django.contrib.gis.geos import Point

from epocha.apps.agents.models import Agent, Relationship
from epocha.apps.agents.relationships import (
    evolve_relationships,
    find_potential_relationships,
    update_relationship_from_interaction,
)
from epocha.apps.simulation.models import Simulation
from epocha.apps.users.models import User


@pytest.fixture
def user(db):
    return User.objects.create_user(email="rel@epocha.dev", username="reltest", password="pass123")


@pytest.fixture
def simulation(user):
    return Simulation.objects.create(name="RelTest", seed=42, owner=user)


@pytest.mark.django_db
class TestFindPotentialRelationships:
    def test_nearby_agents_are_candidates(self, simulation):
        # Use SRID 4326 (lat/lon). Points ~10m apart are "near"; points far away are excluded.
        # At the equator, 0.0001 degrees longitude ≈ 11m, so threshold=20 meters should include
        # a point 0.0001 deg away but exclude one 10 degrees away.
        a1 = Agent.objects.create(
            simulation=simulation, name="Marco",
            location=Point(0.0, 0.0, srid=4326), personality={},
        )
        Agent.objects.create(
            simulation=simulation, name="Elena",
            location=Point(0.0001, 0.0, srid=4326), personality={},
        )
        Agent.objects.create(
            simulation=simulation, name="Luca",
            location=Point(10.0, 10.0, srid=4326), personality={},
        )

        candidates = find_potential_relationships(a1, proximity_threshold=20)
        names = [a.name for a in candidates]
        assert "Elena" in names
        assert "Luca" not in names

    def test_existing_relationships_excluded(self, simulation):
        a1 = Agent.objects.create(
            simulation=simulation, name="Marco",
            location=Point(0.0, 0.0, srid=4326), personality={},
        )
        a2 = Agent.objects.create(
            simulation=simulation, name="Elena",
            location=Point(0.0001, 0.0, srid=4326), personality={},
        )
        Relationship.objects.create(agent_from=a1, agent_to=a2, relation_type="friendship", strength=0.5, sentiment=0.5, since_tick=1)

        candidates = find_potential_relationships(a1, proximity_threshold=20)
        assert len(candidates) == 0


@pytest.mark.django_db
class TestUpdateRelationshipFromInteraction:
    @pytest.fixture
    def two_agents(self, simulation):
        a1 = Agent.objects.create(simulation=simulation, name="Marco", personality={})
        a2 = Agent.objects.create(simulation=simulation, name="Elena", personality={})
        return a1, a2

    def test_positive_interaction_creates_friendship(self, two_agents):
        marco, elena = two_agents
        update_relationship_from_interaction(marco, elena, "help", tick=5)

        rel = Relationship.objects.get(agent_from=marco, agent_to=elena)
        assert rel.relation_type == "friendship"
        assert rel.sentiment > 0

    def test_negative_interaction_creates_rivalry(self, two_agents):
        marco, elena = two_agents
        update_relationship_from_interaction(marco, elena, "argue", tick=5)

        rel = Relationship.objects.get(agent_from=marco, agent_to=elena)
        assert rel.relation_type == "rivalry"
        assert rel.sentiment < 0

    def test_repeated_interactions_strengthen(self, two_agents):
        marco, elena = two_agents
        update_relationship_from_interaction(marco, elena, "help", tick=1)
        s1 = Relationship.objects.get(agent_from=marco, agent_to=elena).strength

        update_relationship_from_interaction(marco, elena, "help", tick=5)
        s2 = Relationship.objects.get(agent_from=marco, agent_to=elena).strength
        assert s2 > s1

    def test_betrayal_flips_friendship_to_rivalry(self, two_agents):
        marco, elena = two_agents
        Relationship.objects.create(
            agent_from=marco, agent_to=elena,
            relation_type="friendship", strength=0.6, sentiment=0.7, since_tick=1,
        )
        update_relationship_from_interaction(marco, elena, "betray", tick=10)

        rel = Relationship.objects.get(agent_from=marco, agent_to=elena)
        assert rel.relation_type == "rivalry"
        assert rel.sentiment < 0


@pytest.mark.django_db
class TestEvolveRelationships:
    def test_weak_old_relationships_decay(self, simulation):
        a1 = Agent.objects.create(simulation=simulation, name="Marco", personality={})
        a2 = Agent.objects.create(simulation=simulation, name="Elena", personality={})
        Relationship.objects.create(
            agent_from=a1, agent_to=a2,
            relation_type="friendship", strength=0.3, sentiment=0.3, since_tick=1,
        )
        evolve_relationships(simulation, current_tick=200)

        rel = Relationship.objects.get(agent_from=a1, agent_to=a2)
        assert rel.strength < 0.3

    def test_strong_emotion_resists_decay(self, simulation):
        a1 = Agent.objects.create(simulation=simulation, name="Marco", personality={})
        a2 = Agent.objects.create(simulation=simulation, name="Elena", personality={})
        Relationship.objects.create(
            agent_from=a1, agent_to=a2,
            relation_type="rivalry", strength=0.5, sentiment=-0.9, since_tick=1,
        )
        evolve_relationships(simulation, current_tick=200)

        rel = Relationship.objects.get(agent_from=a1, agent_to=a2)
        # Strong hatred resists decay — strength should barely change
        assert rel.strength > 0.45

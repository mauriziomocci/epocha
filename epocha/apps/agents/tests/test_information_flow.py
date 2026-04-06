"""Tests for the information flow propagation engine."""
import pytest

from epocha.apps.agents.information_flow import propagate_information
from epocha.apps.agents.models import Agent, Memory, Relationship
from epocha.apps.simulation.models import Event, Simulation
from epocha.apps.users.models import User
from epocha.apps.world.models import World


@pytest.fixture
def user(db):
    return User.objects.create_user(email="info@epocha.dev", username="infotest", password="pass123")


@pytest.fixture
def simulation(user):
    return Simulation.objects.create(name="InfoTest", seed=42, owner=user)


@pytest.fixture
def world(simulation):
    return World.objects.create(simulation=simulation)


@pytest.fixture
def marco(simulation):
    return Agent.objects.create(
        simulation=simulation, name="Marco", role="blacksmith",
        personality={
            "openness": 0.5, "conscientiousness": 0.5, "extraversion": 0.5,
            "agreeableness": 0.5, "neuroticism": 0.5,
        },
    )


@pytest.fixture
def elena(simulation):
    return Agent.objects.create(
        simulation=simulation, name="Elena", role="farmer",
        personality={
            "openness": 0.5, "conscientiousness": 0.5, "extraversion": 0.5,
            "agreeableness": 0.5, "neuroticism": 0.5,
        },
    )


@pytest.fixture
def carlo(simulation):
    return Agent.objects.create(
        simulation=simulation, name="Carlo", role="priest",
        personality={
            "openness": 0.5, "conscientiousness": 0.5, "extraversion": 0.5,
            "agreeableness": 0.5, "neuroticism": 0.5,
        },
    )


@pytest.mark.django_db
class TestPropagateInformation:
    def test_significant_action_creates_hearsay(self, simulation, world, marco, elena):
        """An action with emotional_weight >= threshold creates hearsay for connected agents."""
        Relationship.objects.create(
            agent_from=marco, agent_to=elena,
            relation_type="friendship", strength=0.7, sentiment=0.6, since_tick=0,
        )
        Memory.objects.create(
            agent=marco, content="I decided to argue. angry at the priest",
            emotional_weight=0.4, source_type="direct", tick_created=5,
            origin_agent=marco,
        )

        propagate_information(simulation, tick=5)

        elena_memories = Memory.objects.filter(agent=elena, source_type="hearsay")
        assert elena_memories.count() == 1
        hearsay = elena_memories.first()
        assert hearsay.origin_agent == marco
        assert hearsay.reliability < 1.0
        assert hearsay.tick_created == 5

    def test_low_weight_action_does_not_propagate(self, simulation, world, marco, elena):
        """Actions below the propagation threshold are too mundane for gossip."""
        Relationship.objects.create(
            agent_from=marco, agent_to=elena,
            relation_type="friendship", strength=0.7, sentiment=0.6, since_tick=0,
        )
        Memory.objects.create(
            agent=marco, content="I decided to rest. tired",
            emotional_weight=0.05, source_type="direct", tick_created=5,
            origin_agent=marco,
        )

        propagate_information(simulation, tick=5)

        assert Memory.objects.filter(agent=elena, source_type="hearsay").count() == 0

    def test_no_relationship_no_propagation(self, simulation, world, marco, elena):
        """Without a relationship, hearsay does not reach the agent."""
        Memory.objects.create(
            agent=marco, content="I decided to betray. power grab",
            emotional_weight=0.8, source_type="direct", tick_created=5,
            origin_agent=marco,
        )

        propagate_information(simulation, tick=5)

        assert Memory.objects.filter(agent=elena, source_type="hearsay").count() == 0

    def test_hearsay_becomes_rumor_on_second_hop(self, simulation, world, marco, elena, carlo):
        """Hearsay from tick N-1 propagates as rumor in tick N."""
        Relationship.objects.create(
            agent_from=marco, agent_to=elena,
            relation_type="friendship", strength=0.7, sentiment=0.6, since_tick=0,
        )
        Relationship.objects.create(
            agent_from=elena, agent_to=carlo,
            relation_type="professional", strength=0.6, sentiment=0.3, since_tick=0,
        )

        # Tick 5: Marco's direct memory
        Memory.objects.create(
            agent=marco, content="I decided to betray. power grab",
            emotional_weight=0.8, source_type="direct", tick_created=5,
            origin_agent=marco,
        )
        propagate_information(simulation, tick=5)

        # Elena should have hearsay
        elena_hearsay = Memory.objects.filter(agent=elena, source_type="hearsay")
        assert elena_hearsay.count() == 1

        # Tick 6: propagate again -- Elena's hearsay should reach Carlo as rumor
        propagate_information(simulation, tick=6)

        carlo_rumors = Memory.objects.filter(agent=carlo, source_type="rumor")
        assert carlo_rumors.count() == 1
        rumor = carlo_rumors.first()
        assert rumor.origin_agent == marco
        assert rumor.reliability < elena_hearsay.first().reliability

    def test_dead_agents_do_not_receive_information(self, simulation, world, marco, elena):
        """Dead agents are excluded from propagation."""
        elena.is_alive = False
        elena.save(update_fields=["is_alive"])
        Relationship.objects.create(
            agent_from=marco, agent_to=elena,
            relation_type="friendship", strength=0.7, sentiment=0.6, since_tick=0,
        )
        Memory.objects.create(
            agent=marco, content="I decided to argue. angry",
            emotional_weight=0.4, source_type="direct", tick_created=5,
            origin_agent=marco,
        )

        propagate_information(simulation, tick=5)

        assert Memory.objects.filter(agent=elena, source_type="hearsay").count() == 0

    def test_deduplication_prevents_same_info_twice(self, simulation, world, marco, elena, carlo):
        """An agent should not receive the same information from multiple sources."""
        Relationship.objects.create(
            agent_from=marco, agent_to=elena,
            relation_type="friendship", strength=0.7, sentiment=0.6, since_tick=0,
        )
        Relationship.objects.create(
            agent_from=carlo, agent_to=elena,
            relation_type="professional", strength=0.5, sentiment=0.3, since_tick=0,
        )
        Memory.objects.create(
            agent=marco, content="I decided to argue. angry",
            emotional_weight=0.4, source_type="direct", tick_created=5,
            origin_agent=marco,
        )

        propagate_information(simulation, tick=5)

        elena_hearsays = Memory.objects.filter(
            agent=elena, source_type="hearsay", origin_agent=marco,
        )
        assert elena_hearsays.count() == 1

    def test_public_events_reach_all_agents(self, simulation, world, marco, elena, carlo):
        """Public events propagate instantly to all living agents."""
        Event.objects.create(
            simulation=simulation, title="Plague outbreak",
            description="A terrible plague has hit the city.",
            tick=5, severity=0.9,
        )

        propagate_information(simulation, tick=5)

        for agent in [marco, elena, carlo]:
            public_memories = Memory.objects.filter(agent=agent, source_type="public")
            assert public_memories.count() == 1
            mem = public_memories.first()
            assert mem.reliability == 1.0
            assert "plague" in mem.content.lower()

    def test_belief_filter_rejects_unreliable_info(self, simulation, world, marco, elena):
        """A highly skeptical agent rejects information from a distrusted source."""
        elena.personality = {
            "openness": 0.0, "agreeableness": 0.0,
            "conscientiousness": 0.5, "extraversion": 0.5, "neuroticism": 0.5,
        }
        elena.save(update_fields=["personality"])
        Relationship.objects.create(
            agent_from=marco, agent_to=elena,
            relation_type="distrust", strength=0.2, sentiment=-0.5, since_tick=0,
        )
        Memory.objects.create(
            agent=marco, content="I decided to argue. angry",
            emotional_weight=0.4, source_type="direct", tick_created=5,
            origin_agent=marco,
        )

        propagate_information(simulation, tick=5)

        assert Memory.objects.filter(agent=elena, source_type="hearsay").count() == 0

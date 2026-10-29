"""Tests for the information flow propagation engine."""

import os
import subprocess
import sys
from pathlib import Path

import pytest

from epocha.apps.agents.information_flow import propagate_information
from epocha.apps.agents.models import Agent, Memory, Relationship
from epocha.apps.simulation.models import Event, Simulation
from epocha.apps.users.models import User
from epocha.apps.world.models import World

# Repository root, the working directory from which `config.settings` imports.
_REPO_ROOT = Path(__file__).resolve().parents[4]


@pytest.fixture
def user(db):
    return User.objects.create_user(
        email="info@epocha.dev", username="infotest", password="pass123"
    )


@pytest.fixture
def simulation(user):
    return Simulation.objects.create(name="InfoTest", seed=42, owner=user)


@pytest.fixture
def world(simulation):
    return World.objects.create(simulation=simulation)


@pytest.fixture
def marco(simulation):
    return Agent.objects.create(
        simulation=simulation,
        name="Marco",
        role="blacksmith",
        personality={
            "openness": 0.5,
            "conscientiousness": 0.5,
            "extraversion": 0.5,
            "agreeableness": 0.5,
            "neuroticism": 0.5,
        },
    )


@pytest.fixture
def elena(simulation):
    return Agent.objects.create(
        simulation=simulation,
        name="Elena",
        role="farmer",
        personality={
            "openness": 0.5,
            "conscientiousness": 0.5,
            "extraversion": 0.5,
            "agreeableness": 0.5,
            "neuroticism": 0.5,
        },
    )


@pytest.fixture
def carlo(simulation):
    return Agent.objects.create(
        simulation=simulation,
        name="Carlo",
        role="priest",
        personality={
            "openness": 0.5,
            "conscientiousness": 0.5,
            "extraversion": 0.5,
            "agreeableness": 0.5,
            "neuroticism": 0.5,
        },
    )


@pytest.mark.django_db
class TestPropagateInformation:
    def test_significant_action_creates_hearsay(self, simulation, world, marco, elena):
        """An action with emotional_weight >= threshold creates hearsay for connected agents."""
        Relationship.objects.create(
            agent_from=marco,
            agent_to=elena,
            relation_type="friendship",
            strength=0.7,
            sentiment=0.6,
            since_tick=0,
        )
        Memory.objects.create(
            agent=marco,
            content="I decided to argue. angry at the priest",
            emotional_weight=0.4,
            source_type="direct",
            tick_created=5,
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
            agent_from=marco,
            agent_to=elena,
            relation_type="friendship",
            strength=0.7,
            sentiment=0.6,
            since_tick=0,
        )
        Memory.objects.create(
            agent=marco,
            content="I decided to rest. tired",
            emotional_weight=0.05,
            source_type="direct",
            tick_created=5,
            origin_agent=marco,
        )

        propagate_information(simulation, tick=5)

        assert Memory.objects.filter(agent=elena, source_type="hearsay").count() == 0

    def test_no_relationship_no_propagation(self, simulation, world, marco, elena):
        """Without a relationship, hearsay does not reach the agent."""
        Memory.objects.create(
            agent=marco,
            content="I decided to betray. power grab",
            emotional_weight=0.8,
            source_type="direct",
            tick_created=5,
            origin_agent=marco,
        )

        propagate_information(simulation, tick=5)

        assert Memory.objects.filter(agent=elena, source_type="hearsay").count() == 0

    def test_hearsay_becomes_rumor_on_second_hop(self, simulation, world, marco, elena, carlo):
        """Hearsay from tick N-1 propagates as rumor in tick N."""
        Relationship.objects.create(
            agent_from=marco,
            agent_to=elena,
            relation_type="friendship",
            strength=0.7,
            sentiment=0.6,
            since_tick=0,
        )
        Relationship.objects.create(
            agent_from=elena,
            agent_to=carlo,
            relation_type="professional",
            strength=0.6,
            sentiment=0.3,
            since_tick=0,
        )

        # Tick 5: Marco's direct memory
        Memory.objects.create(
            agent=marco,
            content="I decided to betray. power grab",
            emotional_weight=0.8,
            source_type="direct",
            tick_created=5,
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
            agent_from=marco,
            agent_to=elena,
            relation_type="friendship",
            strength=0.7,
            sentiment=0.6,
            since_tick=0,
        )
        Memory.objects.create(
            agent=marco,
            content="I decided to argue. angry",
            emotional_weight=0.4,
            source_type="direct",
            tick_created=5,
            origin_agent=marco,
        )

        propagate_information(simulation, tick=5)

        assert Memory.objects.filter(agent=elena, source_type="hearsay").count() == 0

    def test_deduplication_prevents_same_info_twice(self, simulation, world, marco, elena, carlo):
        """An agent should not receive the same information from multiple sources."""
        Relationship.objects.create(
            agent_from=marco,
            agent_to=elena,
            relation_type="friendship",
            strength=0.7,
            sentiment=0.6,
            since_tick=0,
        )
        Relationship.objects.create(
            agent_from=carlo,
            agent_to=elena,
            relation_type="professional",
            strength=0.5,
            sentiment=0.3,
            since_tick=0,
        )
        Memory.objects.create(
            agent=marco,
            content="I decided to argue. angry",
            emotional_weight=0.4,
            source_type="direct",
            tick_created=5,
            origin_agent=marco,
        )

        propagate_information(simulation, tick=5)

        elena_hearsays = Memory.objects.filter(
            agent=elena,
            source_type="hearsay",
            origin_agent=marco,
        )
        assert elena_hearsays.count() == 1

    def test_public_events_reach_all_agents(self, simulation, world, marco, elena, carlo):
        """Public events propagate instantly to all living agents."""
        Event.objects.create(
            simulation=simulation,
            title="Plague outbreak",
            description="A terrible plague has hit the city.",
            tick=5,
            severity=0.9,
        )

        propagate_information(simulation, tick=5)

        for agent in [marco, elena, carlo]:
            public_memories = Memory.objects.filter(agent=agent, source_type="public")
            assert public_memories.count() == 1
            mem = public_memories.first()
            assert mem.reliability == 1.0
            assert "plague" in mem.content.lower()

    def test_distinct_public_events_same_tick_produce_two_memories(self, simulation, world, marco):
        """Two distinct public events firing at the same tick must each yield
        a memory for every living agent. Closes Round 2 finding IF-5: prior
        get_or_create lookup omitted content and silently dropped the second
        event into the same memory slot.
        """
        Event.objects.create(
            simulation=simulation,
            title="Plague outbreak",
            description="A terrible plague has hit the city.",
            tick=5,
            severity=0.9,
        )
        Event.objects.create(
            simulation=simulation,
            title="Market crash",
            description="Grain prices collapsed overnight.",
            tick=5,
            severity=0.7,
        )

        propagate_information(simulation, tick=5)

        public_memories = Memory.objects.filter(
            agent=marco,
            source_type=Memory.SourceType.PUBLIC,
            tick_created=5,
        )
        assert public_memories.count() == 2
        contents = {m.content for m in public_memories}
        assert any("plague" in c.lower() for c in contents)
        assert any("market crash" in c.lower() for c in contents)

    def test_belief_filter_rejects_unreliable_info(self, simulation, world, marco, elena):
        """A highly skeptical agent rejects information from a distrusted source.

        The belief filter will reject the hearsay (source_type="hearsay" count stays 0)
        but a weak rumor (source_type="rumor") is still created for further propagation.
        """
        elena.personality = {
            "openness": 0.0,
            "agreeableness": 0.0,
            "conscientiousness": 0.5,
            "extraversion": 0.5,
            "neuroticism": 0.5,
        }
        elena.save(update_fields=["personality"])
        Relationship.objects.create(
            agent_from=marco,
            agent_to=elena,
            relation_type="distrust",
            strength=0.2,
            sentiment=-0.5,
            since_tick=0,
        )
        Memory.objects.create(
            agent=marco,
            content="I decided to argue. angry",
            emotional_weight=0.4,
            source_type="direct",
            tick_created=5,
            origin_agent=marco,
        )

        propagate_information(simulation, tick=5)

        assert Memory.objects.filter(agent=elena, source_type="hearsay").count() == 0

    def test_reputation_updated_on_hearsay(self, simulation, world, marco, elena):
        """Receiving hearsay about an agent should update the recipient's reputation score."""
        from epocha.apps.agents.models import ReputationScore

        Relationship.objects.create(
            agent_from=marco,
            agent_to=elena,
            relation_type="friendship",
            strength=0.7,
            sentiment=0.6,
            since_tick=0,
        )
        Memory.objects.create(
            agent=marco,
            content="I decided to betray. power grab",
            emotional_weight=0.8,
            source_type="direct",
            tick_created=5,
            origin_agent=marco,
        )

        propagate_information(simulation, tick=5)

        scores = ReputationScore.objects.filter(holder=elena, target=marco)
        assert scores.exists()
        assert scores.first().reputation < 0

    def test_gossip_propagates_without_belief(self, simulation, world, marco, elena, carlo):
        """Even when the belief filter rejects, a weak rumor is created for further propagation."""
        from epocha.apps.agents.models import ReputationScore

        elena.personality = {
            "openness": 0.0,
            "agreeableness": 0.0,
            "conscientiousness": 0.5,
            "extraversion": 0.5,
            "neuroticism": 0.5,
        }
        elena.save(update_fields=["personality"])
        Relationship.objects.create(
            agent_from=marco,
            agent_to=elena,
            relation_type="distrust",
            strength=0.2,
            sentiment=-0.5,
            since_tick=0,
        )
        Relationship.objects.create(
            agent_from=elena,
            agent_to=carlo,
            relation_type="friendship",
            strength=0.7,
            sentiment=0.5,
            since_tick=0,
        )
        Memory.objects.create(
            agent=marco,
            content="I decided to betray. power grab",
            emotional_weight=0.8,
            source_type="direct",
            tick_created=5,
            origin_agent=marco,
        )

        propagate_information(simulation, tick=5)

        # Elena should have a weak rumor (not a full hearsay)
        elena_memories = Memory.objects.filter(agent=elena, source_type__in=["hearsay", "rumor"])
        assert elena_memories.exists()
        rumor = elena_memories.filter(source_type="rumor").first()
        assert rumor is not None
        assert rumor.emotional_weight == 0.1

        # Reputation must be updated even though Elena did not believe the information
        rep = ReputationScore.objects.filter(holder=elena, target=marco)
        assert rep.exists()
        assert rep.first().reputation < 0


def _personable(simulation, name):
    return Agent.objects.create(
        simulation=simulation,
        name=name,
        role="farmer",
        personality={trait: 0.5 for trait in ("openness", "agreeableness")},
    )


def _close_friends(one, other):
    Relationship.objects.create(
        agent_from=one,
        agent_to=other,
        relation_type="friendship",
        strength=0.9,
        sentiment=0.9,
        since_tick=0,
    )


@pytest.mark.django_db
class TestFirstHandMemoriesAndTheLifetimeOfTheNews:
    """A first-hand memory suppresses hearsay of the same origin for as long
    as news of that origin can still be travelling, and no longer.

    Round 13 of the demography Plan 4 phase-6 gate (R13-1): the first-hand
    kind matched on the current tick only, so a fleeing partner or a widow,
    whose first-hand memory names someone else as origin, was told of her
    own flight or loss one hop later. The window is the lifetime of the
    news, which these tests measure rather than assume.
    """

    @pytest.mark.parametrize(("max_hops", "last_tick"), [(1, 51), (3, 52), (5, 54)])
    def test_news_of_a_first_hand_event_stops_travelling_where_the_window_ends(
        self, simulation, world, settings, max_hops, last_tick
    ):
        """Phase 1 retells at the event's tick, phase 2 at the next one
        whatever `max_hops` says, phase 3 while the hop is below `max_hops`:
        a tick-50 event is last retold at 50 + max(max_hops, 2) - 1. Along a
        chain long enough never to run out of listeners, that tick is
        measured, so the suppression window cannot drift from it unseen."""
        settings.EPOCHA_INFO_FLOW_MAX_HOPS = max_hops
        chain = [_personable(simulation, f"Anello{i}") for i in range(10)]
        for one, other in zip(chain, chain[1:], strict=False):
            _close_friends(one, other)
        Memory.objects.create(
            agent=chain[0],
            content="I travelled to the coast.",
            emotional_weight=0.8,
            source_type="direct",
            tick_created=50,
            origin_agent=chain[0],
        )

        for tick in range(50, 60):
            propagate_information(simulation, tick=tick)

        retold_at = Memory.objects.filter(
            origin_agent=chain[0], source_type__in=["hearsay", "rumor"]
        ).values_list("tick_created", flat=True)
        assert max(retold_at) == last_tick

    @pytest.mark.parametrize(("max_hops", "oldest_suppressing_tick"), [(1, 49), (3, 48), (5, 46)])
    def test_a_first_hand_memory_suppresses_hearsay_exactly_over_the_window(
        self, simulation, world, marco, settings, max_hops, oldest_suppressing_tick
    ):
        """Inside the window the holder is already informed; one tick older,
        her first-hand memory belongs to news that has stopped travelling,
        and fresh news of the same origin reaches her."""
        settings.EPOCHA_INFO_FLOW_MAX_HOPS = max_hops
        inside = _personable(simulation, "Dentro")
        outside = _personable(simulation, "Fuori")
        for holder, tick_created in (
            (inside, oldest_suppressing_tick),
            (outside, oldest_suppressing_tick - 1),
        ):
            _close_friends(marco, holder)
            Memory.objects.create(
                agent=holder,
                content="Marco took me along to the coast.",
                emotional_weight=0.8,
                source_type="direct",
                tick_created=tick_created,
                origin_agent=marco,
            )
        Memory.objects.create(
            agent=marco,
            content="I travelled to the coast.",
            emotional_weight=0.8,
            source_type="direct",
            tick_created=50,
            origin_agent=marco,
        )

        propagate_information(simulation, tick=50)

        heard = Memory.objects.filter(origin_agent=marco, source_type="hearsay")
        assert list(heard.values_list("agent__name", flat=True)) == ["Fuori"]


def _boot_settings_with_decay(decay: str) -> subprocess.CompletedProcess:
    """Import the shared settings in a fresh interpreter, as every web and
    worker process does at boot, with the decay set in the environment."""
    return subprocess.run(
        [sys.executable, "-c", "import config.settings.base"],
        cwd=_REPO_ROOT,
        env={**os.environ, "EPOCHA_INFO_FLOW_RELIABILITY_DECAY": decay},
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )


@pytest.mark.django_db
class TestReliabilityDecayDomain:
    """The per-hop reliability decay is read from the environment, and the
    hop estimate that bounds phase 3 is defined only for 0 < decay < 1: at
    1.0 `_estimate_hop` returns 0 for every rumour, phase 3 never stops and
    the first-hand suppression window, derived from the three phases, no
    longer covers the life of the news (round 14 of the demography Plan 4
    phase-6 gate, NB-1). A decay outside the open interval is a
    configuration error, refused by the settings where the environment is
    read, so that a bad value stops every web and worker process at boot,
    before any tick and any paid LLM call."""

    @pytest.mark.parametrize("decay", ["1.0", "0.0", "1.5", "-0.1"])
    def test_a_decay_outside_the_open_unit_interval_stops_the_boot(self, decay):
        booted = _boot_settings_with_decay(decay)

        assert booted.returncode != 0
        assert "ImproperlyConfigured" in booted.stderr
        assert "EPOCHA_INFO_FLOW_RELIABILITY_DECAY" in booted.stderr

    def test_a_decay_inside_the_open_unit_interval_boots(self):
        booted = _boot_settings_with_decay("0.7")

        assert booted.returncode == 0, booted.stderr

    def test_the_default_decay_propagates_and_decays_reliability(
        self, simulation, world, marco, elena, settings
    ):
        settings.EPOCHA_INFO_FLOW_RELIABILITY_DECAY = 0.7
        _close_friends(marco, elena)
        Memory.objects.create(
            agent=marco,
            content="I travelled to the coast.",
            emotional_weight=0.8,
            source_type="direct",
            tick_created=1,
            origin_agent=marco,
        )

        propagate_information(simulation, tick=1)

        heard = Memory.objects.get(agent=elena, origin_agent=marco)
        assert heard.reliability == pytest.approx(0.7)

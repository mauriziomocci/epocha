"""Tests for agent memory retrieval and decay."""
import pytest

from epocha.apps.agents.memory import decay_memories, get_relevant_memories
from epocha.apps.agents.models import Agent, Memory
from epocha.apps.simulation.models import Simulation


@pytest.fixture
def simulation(db):
    from epocha.apps.users.models import User

    user = User.objects.create_user(email="mem@epocha.dev", username="memtest", password="pass123")
    return Simulation.objects.create(name="MemTest", seed=42, owner=user)


@pytest.fixture
def agent(simulation):
    return Agent.objects.create(
        simulation=simulation,
        name="TestAgent",
        personality={"openness": 0.5},
    )


@pytest.mark.django_db
class TestGetRelevantMemories:
    def test_returns_most_relevant_by_emotional_weight(self, agent):
        """High emotional weight memories should rank first."""
        Memory.objects.create(agent=agent, content="Saw a bird", emotional_weight=0.1, tick_created=1)
        Memory.objects.create(agent=agent, content="House burned down", emotional_weight=0.9, tick_created=2)
        Memory.objects.create(agent=agent, content="Had lunch", emotional_weight=0.2, tick_created=3)

        memories = get_relevant_memories(agent, current_tick=10, max_memories=2)
        assert len(memories) == 2
        assert memories[0].content == "House burned down"

    def test_respects_max_memories_limit(self, agent):
        """Should return at most max_memories entries."""
        for i in range(20):
            Memory.objects.create(agent=agent, content=f"Event {i}", emotional_weight=0.5, tick_created=i)

        memories = get_relevant_memories(agent, current_tick=50, max_memories=5)
        assert len(memories) == 5

    def test_excludes_inactive_memories(self, agent):
        """Faded memories (is_active=False) must not appear."""
        Memory.objects.create(agent=agent, content="Old memory", emotional_weight=0.5, tick_created=1, is_active=False)
        Memory.objects.create(agent=agent, content="Active memory", emotional_weight=0.5, tick_created=2)

        memories = get_relevant_memories(agent, current_tick=10)
        assert all(m.is_active for m in memories)
        assert len(memories) == 1

    def test_returns_empty_list_when_no_memories(self, agent):
        """An agent with no memories should get an empty list, not an error."""
        memories = get_relevant_memories(agent, current_tick=10)
        assert memories == []


@pytest.mark.django_db
class TestDecayMemories:
    def test_old_low_weight_memories_decay(self, agent):
        """Trivial memories older than the threshold should be deactivated."""
        Memory.objects.create(agent=agent, content="Trivial", emotional_weight=0.1, tick_created=1)
        decay_memories(agent, current_tick=100)

        memory = Memory.objects.get(content="Trivial")
        assert memory.is_active is False

    def test_high_weight_memories_persist(self, agent):
        """Emotionally significant memories must resist decay."""
        Memory.objects.create(agent=agent, content="Trauma", emotional_weight=0.9, tick_created=1)
        decay_memories(agent, current_tick=100)

        memory = Memory.objects.get(content="Trauma")
        assert memory.is_active is True

    def test_recent_memories_not_decayed(self, agent):
        """Memories younger than the decay threshold should never decay."""
        Memory.objects.create(agent=agent, content="Recent", emotional_weight=0.1, tick_created=95)
        decay_memories(agent, current_tick=100)

        memory = Memory.objects.get(content="Recent")
        assert memory.is_active is True

    def test_medium_weight_survives_moderate_age(self, agent):
        """Medium emotional weight should survive moderate aging."""
        Memory.objects.create(agent=agent, content="Medium", emotional_weight=0.5, tick_created=40)
        decay_memories(agent, current_tick=80)

        memory = Memory.objects.get(content="Medium")
        # At age 40 with weight 0.5, the decay factor should not exceed 1.0
        assert memory.is_active is True

    def test_no_memories_does_not_crash(self, agent):
        """Decay on an agent with no memories should be a no-op."""
        decay_memories(agent, current_tick=100)  # Should not raise

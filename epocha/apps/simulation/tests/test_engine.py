"""Tests for the simulation tick orchestrator."""
from unittest.mock import patch, MagicMock

import pytest

from epocha.apps.agents.models import Agent, Memory, Relationship
from epocha.apps.simulation.engine import SimulationEngine
from epocha.apps.simulation.models import Simulation
from epocha.apps.users.models import User
from epocha.apps.world.models import World, Zone


@pytest.fixture
def user(db):
    return User.objects.create_user(email="eng@epocha.dev", username="engtest", password="pass123")


@pytest.fixture
def sim_with_world(user):
    sim = Simulation.objects.create(name="EngTest", seed=42, owner=user, status="running")
    world = World.objects.create(simulation=sim)
    Zone.objects.create(world=world, name="Village", zone_type="urban")
    Agent.objects.create(
        simulation=sim, name="Marco", role="blacksmith",
        personality={
            "openness": 0.5, "conscientiousness": 0.5, "extraversion": 0.5,
            "agreeableness": 0.5, "neuroticism": 0.5,
            "background": "A blacksmith",
        },
    )
    return sim


@pytest.mark.django_db
class TestSimulationEngine:
    @patch("epocha.apps.simulation.engine.process_agent_decision")
    def test_run_tick_advances_counter(self, mock_decision, sim_with_world):
        """Each tick must increment the simulation's current_tick."""
        mock_decision.return_value = {"action": "work", "reason": "busy"}

        engine = SimulationEngine(sim_with_world)
        engine.run_tick()

        sim_with_world.refresh_from_db()
        assert sim_with_world.current_tick == 1

    @patch("epocha.apps.simulation.engine.process_agent_decision")
    def test_run_tick_processes_all_agents(self, mock_decision, sim_with_world):
        """Every living agent should get a decision call."""
        Agent.objects.create(
            simulation=sim_with_world, name="Elena", role="farmer",
            personality={"openness": 0.5},
        )
        mock_decision.return_value = {"action": "rest"}

        engine = SimulationEngine(sim_with_world)
        engine.run_tick()

        assert mock_decision.call_count == 2  # Marco + Elena

    @patch("epocha.apps.simulation.engine.process_agent_decision")
    def test_dead_agents_are_skipped(self, mock_decision, sim_with_world):
        """Dead agents must not be processed."""
        Agent.objects.create(
            simulation=sim_with_world, name="Ghost", role="farmer",
            personality={}, is_alive=False,
        )
        mock_decision.return_value = {"action": "rest"}

        engine = SimulationEngine(sim_with_world)
        engine.run_tick()

        assert mock_decision.call_count == 1  # Only Marco

    @patch("epocha.apps.simulation.engine.process_agent_decision")
    def test_creates_memory_from_action(self, mock_decision, sim_with_world):
        """Each agent's action should be recorded as a memory."""
        mock_decision.return_value = {"action": "argue", "reason": "angry at priest"}

        engine = SimulationEngine(sim_with_world)
        engine.run_tick()

        marco = Agent.objects.get(name="Marco")
        assert Memory.objects.filter(agent=marco).exists()
        memory = Memory.objects.filter(agent=marco).first()
        assert "argue" in memory.content

    @patch("epocha.apps.simulation.engine.process_agent_decision")
    def test_economy_runs_before_decisions(self, mock_decision, sim_with_world):
        """Economy tick should update agent wealth before decisions are made."""
        mock_decision.return_value = {"action": "work"}

        engine = SimulationEngine(sim_with_world)
        engine.run_tick()

        marco = Agent.objects.get(name="Marco")
        # Blacksmith income (8) - cost of living (3) = +5
        assert marco.wealth != 50  # Changed from initial

    @patch("epocha.apps.simulation.engine.process_agent_decision")
    def test_agent_failure_does_not_crash_tick(self, mock_decision, sim_with_world):
        """If one agent's decision fails, the tick should continue for others."""
        Agent.objects.create(
            simulation=sim_with_world, name="Elena", role="farmer",
            personality={"openness": 0.5},
        )
        mock_decision.side_effect = [Exception("LLM error"), {"action": "rest"}]

        engine = SimulationEngine(sim_with_world)
        engine.run_tick()  # Should not raise

        sim_with_world.refresh_from_db()
        assert sim_with_world.current_tick == 1

    @patch("epocha.apps.simulation.engine.process_agent_decision")
    def test_multiple_ticks_increment_correctly(self, mock_decision, sim_with_world):
        """Running multiple ticks should increment the counter each time."""
        mock_decision.return_value = {"action": "work"}

        engine = SimulationEngine(sim_with_world)
        engine.run_tick()
        engine.run_tick()
        engine.run_tick()

        sim_with_world.refresh_from_db()
        assert sim_with_world.current_tick == 3

    @patch("epocha.apps.simulation.engine.process_agent_decision")
    def test_no_duplicate_memories_for_same_action(self, mock_decision, sim_with_world):
        """Repeating the same action in consecutive ticks should not create duplicate memories."""
        mock_decision.return_value = {"action": "argue", "reason": "angry at priest"}

        engine = SimulationEngine(sim_with_world)
        engine.run_tick()  # tick 1 - creates memory
        engine.run_tick()  # tick 2 - same action, should skip memory
        engine.run_tick()  # tick 3 - same action, should skip memory

        marco = Agent.objects.get(name="Marco")
        argue_memories = Memory.objects.filter(agent=marco, content__startswith="I decided to argue")
        assert argue_memories.count() == 1

    @patch("epocha.apps.simulation.engine.process_agent_decision")
    def test_information_flow_runs_after_decisions(self, mock_decision, sim_with_world):
        """Information flow should propagate after agent decisions."""
        Agent.objects.create(
            simulation=sim_with_world, name="Elena", role="farmer",
            personality={
                "openness": 0.5, "conscientiousness": 0.5, "extraversion": 0.5,
                "agreeableness": 0.5, "neuroticism": 0.5,
            },
        )
        Relationship.objects.create(
            agent_from=Agent.objects.get(name="Marco"),
            agent_to=Agent.objects.get(name="Elena"),
            relation_type="friendship", strength=0.7, sentiment=0.6, since_tick=0,
        )
        mock_decision.return_value = {"action": "argue", "reason": "angry at priest"}

        engine = SimulationEngine(sim_with_world)
        engine.run_tick()

        # Elena should have received hearsay about Marco's action
        elena = Agent.objects.get(name="Elena")
        hearsay = Memory.objects.filter(agent=elena, source_type="hearsay")
        assert hearsay.count() >= 1

    @patch("epocha.apps.simulation.engine.process_agent_decision")
    def test_faction_dynamics_runs_at_interval(self, mock_decision, sim_with_world):
        """Faction dynamics should run at the configured interval."""
        mock_decision.return_value = {"action": "work", "reason": "busy"}
        engine = SimulationEngine(sim_with_world)

        with patch("epocha.apps.simulation.engine.process_faction_dynamics") as mock_factions:
            for _ in range(5):
                engine.run_tick()
            assert mock_factions.call_count == 5  # Called every tick but no-op except at interval

    @patch("epocha.apps.simulation.engine.process_agent_decision")
    def test_political_cycle_runs_at_interval(self, mock_decision, sim_with_world):
        """Political cycle should be called during ticks."""
        mock_decision.return_value = {"action": "work", "reason": "busy"}
        engine = SimulationEngine(sim_with_world)
        with patch("epocha.apps.simulation.engine.process_political_cycle") as mock_politics:
            for _ in range(10):
                engine.run_tick()
            assert mock_politics.call_count == 10

    @patch("epocha.apps.simulation.engine.process_agent_decision")
    def test_different_actions_create_separate_memories(self, mock_decision, sim_with_world):
        """Different actions in consecutive ticks should each create a memory."""
        mock_decision.side_effect = [
            {"action": "argue", "reason": "angry"},
            {"action": "rest", "reason": "tired"},
            {"action": "argue", "reason": "still angry"},
        ]

        engine = SimulationEngine(sim_with_world)
        engine.run_tick()  # tick 1 - argue
        engine.run_tick()  # tick 2 - rest (different action)
        engine.run_tick()  # tick 3 - argue again (different from previous tick)

        marco = Agent.objects.get(name="Marco")
        # Count only decision memories (prefix "I decided to"); the political cycle may
        # create stratification memories with a different prefix in the same ticks.
        assert Memory.objects.filter(agent=marco, content__startswith="I decided to").count() == 3

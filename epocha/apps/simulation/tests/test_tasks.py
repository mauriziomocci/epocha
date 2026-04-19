"""Tests for simulation Celery tasks (chord-based tick loop)."""

from unittest.mock import patch

import pytest

from epocha.apps.agents.models import Agent
from epocha.apps.simulation.models import Simulation
from epocha.apps.simulation.tasks import finalize_tick, run_simulation_loop
from epocha.apps.users.models import User
from epocha.apps.world.models import World, Zone


@pytest.fixture
def user(db):
    return User.objects.create_user(
        email="simtask@epocha.dev", username="simtask", password="pass123"
    )


@pytest.fixture
def sim_with_agents(user):
    # Default status is paused so finalize_tick does not attempt to
    # re-enqueue run_simulation_loop via apply_async. Tests that want to
    # exercise the re-enqueue path flip the status to running explicitly
    # after patching run_simulation_loop. This prevents chord-in-eager
    # mode from attempting to contact the Celery result backend.
    sim = Simulation.objects.create(
        name="ChordTest", seed=42, owner=user, status=Simulation.Status.PAUSED
    )
    world = World.objects.create(simulation=sim)
    Zone.objects.create(world=world, name="Village", zone_type="urban")
    Agent.objects.create(
        simulation=sim,
        name="Marco",
        role="blacksmith",
        personality={
            "openness": 0.5,
            "conscientiousness": 0.5,
            "extraversion": 0.5,
            "agreeableness": 0.5,
            "neuroticism": 0.5,
            "background": "A blacksmith",
        },
    )
    Agent.objects.create(
        simulation=sim,
        name="Elena",
        role="farmer",
        personality={
            "openness": 0.6,
            "conscientiousness": 0.7,
            "extraversion": 0.3,
            "agreeableness": 0.8,
            "neuroticism": 0.4,
            "background": "A farmer",
        },
    )
    return sim


@pytest.mark.django_db
class TestFinalizeTick:
    def test_advances_tick_counter(self, sim_with_agents):
        """finalize_tick must increment the simulation's current_tick."""
        agent_results = [
            {"action": "work", "agent_name": "Marco"},
            {"action": "rest", "agent_name": "Elena"},
        ]

        finalize_tick(agent_results, sim_with_agents.id, 1)

        sim_with_agents.refresh_from_db()
        assert sim_with_agents.current_tick == 1

    def test_collects_events_from_results(self, sim_with_agents):
        """Events from notable actions should be collected and broadcast."""
        agent_results = [
            {
                "action": "argue",
                "agent_name": "Marco",
                "event": {
                    "title": "Marco decided to argue",
                    "severity": 0.4,
                    "agent": "Marco",
                    "reason": "angry",
                },
            },
            {"action": "rest", "agent_name": "Elena"},
        ]

        with patch("epocha.apps.simulation.engine.broadcast_tick") as mock_broadcast:
            finalize_tick(agent_results, sim_with_agents.id, 1)
            mock_broadcast.assert_called_once()
            call_args = mock_broadcast.call_args
            events = call_args[0][2]
            assert len(events) == 1
            assert events[0]["agent"] == "Marco"

    def test_handles_none_results_gracefully(self, sim_with_agents):
        """If a chord member returns None (Celery edge case), skip it."""
        agent_results = [
            {"action": "work", "agent_name": "Marco"},
            None,
        ]

        finalize_tick(agent_results, sim_with_agents.id, 1)

        sim_with_agents.refresh_from_db()
        assert sim_with_agents.current_tick == 1

    def test_does_not_reenqueue_if_paused(self, sim_with_agents):
        """If simulation was paused during the tick, do not re-enqueue."""
        sim_with_agents.status = Simulation.Status.PAUSED
        sim_with_agents.save()

        with patch("epocha.apps.simulation.tasks.run_simulation_loop") as mock_loop:
            finalize_tick([], sim_with_agents.id, 1)
            mock_loop.apply_async.assert_not_called()

    def test_reenqueues_if_still_running(self, sim_with_agents):
        """If simulation is still running, re-enqueue the loop."""
        sim_with_agents.status = Simulation.Status.RUNNING
        sim_with_agents.save()
        with patch("epocha.apps.simulation.tasks.run_simulation_loop") as mock_loop:
            finalize_tick([], sim_with_agents.id, 1)
            mock_loop.apply_async.assert_called_once()


@pytest.mark.django_db
class TestRunSimulationLoopChord:
    @patch("epocha.apps.simulation.tasks.chord")
    def test_dispatches_chord_for_all_agents(self, mock_chord, sim_with_agents):
        """The loop should build a chord with one task per living agent."""
        sim_with_agents.status = Simulation.Status.RUNNING
        sim_with_agents.save()
        run_simulation_loop(sim_with_agents.id)

        # chord() was called with a list of task signatures
        mock_chord.assert_called_once()
        header = mock_chord.call_args[0][0]
        assert len(header) == 2  # Marco + Elena

    @patch("epocha.apps.simulation.tasks.chord")
    def test_runs_economy_before_chord(self, mock_chord, sim_with_agents):
        """Economy tick must run before the agent chord is dispatched."""
        from epocha.apps.agents.models import Agent

        sim_with_agents.status = Simulation.Status.RUNNING
        sim_with_agents.save()
        run_simulation_loop(sim_with_agents.id)

        # Economy ran: agents' wealth should have changed from initial 50
        marco = Agent.objects.get(name="Marco")
        assert marco.wealth != 50

    @patch("epocha.apps.agents.decision.process_agent_decision")
    def test_stops_if_not_running(self, mock_decision, sim_with_agents):
        """If simulation is paused, the loop should exit immediately."""
        sim_with_agents.status = Simulation.Status.PAUSED
        sim_with_agents.save()

        run_simulation_loop(sim_with_agents.id)

        mock_decision.assert_not_called()
        sim_with_agents.refresh_from_db()
        assert sim_with_agents.current_tick == 0

    def test_no_agents_calls_finalize_directly(self, sim_with_agents):
        """With no living agents, finalize_tick should be called directly."""
        from epocha.apps.agents.models import Agent

        sim_with_agents.status = Simulation.Status.RUNNING
        sim_with_agents.save()
        Agent.objects.filter(simulation=sim_with_agents).update(is_alive=False)

        with patch("epocha.apps.simulation.tasks.finalize_tick") as mock_finalize:
            run_simulation_loop(sim_with_agents.id)
            mock_finalize.assert_called_once_with([], sim_with_agents.id, 1)

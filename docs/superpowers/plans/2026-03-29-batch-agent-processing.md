# Batch Agent Processing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the sequential agent processing loop in `SimulationEngine` with parallel Celery tasks using chord, so all agents in a tick are processed concurrently.

**Architecture:** Each tick splits into two phases: (1) economy + launch parallel agent tasks via `celery.chord`, (2) a callback task (`finalize_tick`) that runs after all agents complete, handling memory decay, tick advancement, and WebSocket broadcast. The self-enqueuing loop (`run_simulation_loop`) launches the chord instead of calling `engine.run_tick()` directly.

**Tech Stack:** Celery 5.4+ (chord, group), Django, PostgreSQL, Redis (broker + result backend)

---

## File Map

| File | Action | Responsibility |
|------|--------|---------------|
| `epocha/apps/agents/tasks.py` | Rewrite | `process_agent_turn` -- full agent decision + apply action for one agent |
| `epocha/apps/simulation/engine.py` | Modify | Extract `_apply_action` to standalone function, remove sequential loop, add `finalize_tick` logic |
| `epocha/apps/simulation/tasks.py` | Modify | `run_simulation_loop` launches chord instead of calling `engine.run_tick()` |
| `epocha/apps/agents/tests/test_tasks.py` | Create | Tests for `process_agent_turn` task |
| `epocha/apps/simulation/tests/test_engine.py` | Modify | Update tests for new chord-based flow |
| `epocha/apps/simulation/tests/test_tasks.py` | Create | Tests for `run_simulation_loop` and `finalize_tick` |

---

## Task 1: Implement `process_agent_turn` as a real Celery task

The stub in `agents/tasks.py` currently raises `NotImplementedError`. Replace it with a task that processes one agent: decision, apply action, create memory. This is the unit of parallelism.

**Files:**
- Create: `epocha/apps/agents/tests/test_tasks.py`
- Modify: `epocha/apps/agents/tasks.py`
- Modify: `epocha/apps/simulation/engine.py` (extract `_apply_action` to module-level function)

- [ ] **Step 1: Extract `_apply_action` from `SimulationEngine` to a module-level function**

Move the action-application logic out of the class so it can be called from the Celery task without instantiating `SimulationEngine`. In `epocha/apps/simulation/engine.py`, add a standalone function `apply_agent_action` above the class, and have the class method delegate to it:

```python
def apply_agent_action(agent: Agent, action: dict, tick: int) -> None:
    """Apply consequences of an agent's action and create a memory.

    Extracted as a standalone function so it can be called from both
    the SimulationEngine and the process_agent_turn Celery task.
    """
    action_type = action.get("action", "rest")

    # Mood adjustment
    mood_delta = _ACTION_MOOD_DELTA.get(action_type, 0.0)
    agent.mood = max(0.0, min(1.0, agent.mood + mood_delta))

    # Rest restores a small amount of health
    if action_type == "rest":
        agent.health = min(1.0, agent.health + 0.02)

    agent.save(update_fields=["mood", "health"])

    # Create memory of the action
    emotional_weight = _ACTION_EMOTIONAL_WEIGHT.get(action_type, _DEFAULT_EMOTIONAL_WEIGHT)
    reason = action.get("reason", "")
    Memory.objects.create(
        agent=agent,
        content=f"I decided to {action_type}. {reason}".strip(),
        emotional_weight=emotional_weight,
        source_type="direct",
        tick_created=tick,
    )
```

Update `SimulationEngine._apply_action` to delegate:

```python
def _apply_action(self, agent: Agent, action: dict, tick: int) -> None:
    """Apply consequences of an agent's action and create a memory."""
    apply_agent_action(agent, action, tick)
```

- [ ] **Step 2: Write the failing test for `process_agent_turn`**

Create `epocha/apps/agents/tests/test_tasks.py`:

```python
"""Tests for agent Celery tasks."""
from unittest.mock import MagicMock, patch

import pytest

from epocha.apps.agents.models import Agent, DecisionLog, Memory
from epocha.apps.agents.tasks import process_agent_turn
from epocha.apps.simulation.models import Simulation
from epocha.apps.users.models import User
from epocha.apps.world.models import World, Zone


@pytest.fixture
def user(db):
    return User.objects.create_user(
        email="task@epocha.dev", username="tasktest", password="pass123"
    )


@pytest.fixture
def simulation(user):
    return Simulation.objects.create(name="TaskTest", seed=42, owner=user, status="running")


@pytest.fixture
def world(simulation):
    w = World.objects.create(simulation=simulation)
    Zone.objects.create(world=w, name="Village", zone_type="urban")
    return w


@pytest.fixture
def agent(simulation):
    return Agent.objects.create(
        simulation=simulation,
        name="Marco",
        role="blacksmith",
        personality={
            "openness": 0.5, "conscientiousness": 0.5, "extraversion": 0.5,
            "agreeableness": 0.5, "neuroticism": 0.5,
            "background": "A blacksmith",
        },
    )


@pytest.mark.django_db
class TestProcessAgentTurn:
    @patch("epocha.apps.agents.tasks.process_agent_decision")
    def test_processes_decision_and_applies_action(self, mock_decision, agent, world):
        """The task should call the decision pipeline and apply the resulting action."""
        mock_decision.return_value = {"action": "work", "reason": "busy"}

        result = process_agent_turn(agent.id, agent.simulation_id, 1)

        mock_decision.assert_called_once()
        assert result["action"] == "work"

    @patch("epocha.apps.agents.tasks.process_agent_decision")
    def test_creates_memory(self, mock_decision, agent, world):
        """The task should create a memory from the action."""
        mock_decision.return_value = {"action": "argue", "reason": "angry at priest"}

        process_agent_turn(agent.id, agent.simulation_id, 1)

        assert Memory.objects.filter(agent=agent).exists()
        memory = Memory.objects.filter(agent=agent).first()
        assert "argue" in memory.content

    @patch("epocha.apps.agents.tasks.process_agent_decision")
    def test_returns_fallback_on_failure(self, mock_decision, agent, world):
        """If the decision pipeline fails, return a fallback rest action."""
        mock_decision.side_effect = Exception("LLM timeout")

        result = process_agent_turn(agent.id, agent.simulation_id, 1)

        assert result["action"] == "rest"
        assert result["error"] is True

    @patch("epocha.apps.agents.tasks.process_agent_decision")
    def test_skips_dead_agent(self, mock_decision, agent, world):
        """Dead agents should be skipped entirely."""
        agent.is_alive = False
        agent.save()

        result = process_agent_turn(agent.id, agent.simulation_id, 1)

        mock_decision.assert_not_called()
        assert result["skipped"] is True

    @patch("epocha.apps.agents.tasks.process_agent_decision")
    def test_returns_event_data_for_notable_actions(self, mock_decision, agent, world):
        """Notable actions (not rest/work) should include event data in the result."""
        mock_decision.return_value = {"action": "argue", "reason": "angry"}

        result = process_agent_turn(agent.id, agent.simulation_id, 1)

        assert "event" in result
        assert result["event"]["agent"] == "Marco"
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `pytest epocha/apps/agents/tests/test_tasks.py -v`
Expected: FAIL (process_agent_turn still raises NotImplementedError)

- [ ] **Step 4: Implement `process_agent_turn`**

Replace the contents of `epocha/apps/agents/tasks.py`:

```python
"""Celery tasks for parallel agent processing.

Each agent's turn is a separate Celery task, enabling parallel execution
across workers. The task returns a result dict that the finalize_tick
callback aggregates for WebSocket broadcast.
"""
from __future__ import annotations

import logging

from config.celery import app

logger = logging.getLogger(__name__)

# Fallback when an agent's decision pipeline fails.
_FALLBACK_RESULT = {"action": "rest", "reason": "error in decision pipeline", "error": True}


@app.task(bind=True, acks_late=True, max_retries=0)
def process_agent_turn(self, agent_id: int, simulation_id: int, tick: int) -> dict:
    """Process a single agent's decision, apply consequences, return result.

    Designed to run as part of a Celery chord. Returns a dict with the
    action taken and optional event data for the WebSocket feed.

    Args:
        agent_id: Primary key of the agent.
        simulation_id: Primary key of the simulation (used to fetch world).
        tick: Current simulation tick number.

    Returns:
        Dict with keys: action, reason, agent_name, and optionally event/error/skipped.
    """
    from epocha.apps.agents.decision import process_agent_decision
    from epocha.apps.agents.models import Agent
    from epocha.apps.simulation.engine import apply_agent_action, _ACTION_EMOTIONAL_WEIGHT
    from epocha.apps.world.models import World

    try:
        agent = Agent.objects.get(id=agent_id)
    except Agent.DoesNotExist:
        logger.error("Agent %d not found at tick %d", agent_id, tick)
        return {**_FALLBACK_RESULT, "agent_name": "unknown", "error": True}

    # Skip dead agents
    if not agent.is_alive:
        return {"action": "none", "agent_name": agent.name, "skipped": True}

    try:
        world = World.objects.get(simulation_id=simulation_id)
        action = process_agent_decision(agent, world, tick)
        apply_agent_action(agent, action, tick)

        # Build result
        action_type = action.get("action", "rest")
        result = {
            "action": action_type,
            "reason": action.get("reason", ""),
            "agent_name": agent.name,
        }

        # Include event data for notable actions (not rest/work)
        if action_type not in ("rest", "work"):
            result["event"] = {
                "title": f"{agent.name} decided to {action_type}",
                "severity": _ACTION_EMOTIONAL_WEIGHT.get(action_type, 0.1),
                "agent": agent.name,
                "reason": action.get("reason", ""),
            }

        return result

    except Exception:
        logger.exception("Agent %s failed at tick %d", agent.name, tick)
        return {**_FALLBACK_RESULT, "agent_name": agent.name}
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest epocha/apps/agents/tests/test_tasks.py -v`
Expected: All 5 tests PASS

- [ ] **Step 6: Commit**

```
feat(agents): implement process_agent_turn Celery task

CHANGE: Replace NotImplementedError stub with full implementation.
Each agent's turn runs as an independent Celery task: decision
pipeline, action application, memory creation. Returns structured
result for chord aggregation. Extract apply_agent_action from
SimulationEngine to enable reuse from the task.
```

---

## Task 2: Implement `finalize_tick` and refactor `run_simulation_loop` to use chord

The simulation loop currently calls `engine.run_tick()` synchronously. Refactor it to: (1) run economy, (2) launch a chord of agent tasks, (3) finalize in the callback. The callback handles memory decay, tick advancement, broadcast, and re-enqueuing.

**Files:**
- Modify: `epocha/apps/simulation/tasks.py`
- Modify: `epocha/apps/simulation/engine.py` (extract economy + broadcast + decay into standalone functions)
- Create: `epocha/apps/simulation/tests/test_tasks.py`

- [ ] **Step 1: Refactor `engine.py` to expose standalone functions**

The chord needs to call economy, decay, and broadcast from tasks without instantiating `SimulationEngine`. Add these module-level functions to `epocha/apps/simulation/engine.py`:

```python
def run_economy(simulation) -> None:
    """Run the economy tick for a simulation's world."""
    world = simulation.world
    process_economy_tick(world, simulation.current_tick + 1)


def run_memory_decay(simulation, tick: int) -> None:
    """Decay memories for all living agents if at the decay interval."""
    if tick % _MEMORY_DECAY_INTERVAL != 0:
        return
    agents = Agent.objects.filter(simulation=simulation, is_alive=True)
    for agent in agents:
        decay_memories(agent, tick)


def broadcast_tick(simulation, tick: int, events: list) -> None:
    """Send tick update to all connected WebSocket clients."""
    try:
        from asgiref.sync import async_to_sync
        from channels.layers import get_channel_layer

        channel_layer = get_channel_layer()
        if channel_layer is None:
            return

        agents = list(Agent.objects.filter(simulation=simulation, is_alive=True))
        agent_count = len(agents)
        world = simulation.world
        data = {
            "tick": tick,
            "events": events,
            "agents_summary": {
                "alive": agent_count,
                "avg_mood": round(sum(a.mood for a in agents) / max(agent_count, 1), 2),
                "avg_wealth": round(sum(a.wealth for a in agents) / max(agent_count, 1), 2),
            },
            "world": {
                "stability": round(world.stability_index, 2),
            },
        }

        async_to_sync(channel_layer.group_send)(
            f"simulation_{simulation.id}",
            {"type": "simulation_update", "data": data},
        )
    except Exception:
        logger.exception("Failed to broadcast tick %d", tick)
```

Keep `SimulationEngine` intact as a convenience wrapper (the dashboard and tests still use it), but have its `run_tick` delegate to these functions:

```python
class SimulationEngine:
    """Orchestrates one tick of the simulation.

    For synchronous execution (tests, dashboard). The Celery-based
    production path uses run_simulation_loop which launches a chord.
    """

    def __init__(self, simulation):
        self.simulation = simulation

    def run_tick(self) -> None:
        """Execute a single simulation tick synchronously."""
        tick = self.simulation.current_tick + 1
        world = self.simulation.world

        logger.info("Simulation %d: running tick %d", self.simulation.id, tick)

        # 1. Economy
        process_economy_tick(world, tick)

        # 2. Agent decisions (sequential fallback)
        agents = list(
            Agent.objects.filter(simulation=self.simulation, is_alive=True)
        )
        tick_events = []
        for agent in agents:
            agent.refresh_from_db()
            try:
                action = process_agent_decision(agent, world, tick)
                apply_agent_action(agent, action, tick)
                action_type = action.get("action", "rest")
                if action_type not in ("rest", "work"):
                    tick_events.append({
                        "title": f"{agent.name} decided to {action_type}",
                        "severity": _ACTION_EMOTIONAL_WEIGHT.get(action_type, 0.1),
                        "agent": agent.name,
                        "reason": action.get("reason", ""),
                    })
            except Exception:
                logger.exception("Agent %s failed at tick %d", agent.name, tick)

        # 3. Memory decay
        run_memory_decay(self.simulation, tick)

        # 4. Advance tick
        self.simulation.current_tick = tick
        self.simulation.save(update_fields=["current_tick", "updated_at"])

        # 5. Broadcast
        broadcast_tick(self.simulation, tick, tick_events)

        logger.info("Simulation %d: tick %d complete", self.simulation.id, tick)
```

- [ ] **Step 2: Write the failing test for `finalize_tick` and chord-based loop**

Create `epocha/apps/simulation/tests/test_tasks.py`:

```python
"""Tests for simulation Celery tasks (chord-based tick loop)."""
from unittest.mock import patch, MagicMock

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
    sim = Simulation.objects.create(name="ChordTest", seed=42, owner=user, status="running")
    world = World.objects.create(simulation=sim)
    Zone.objects.create(world=world, name="Village", zone_type="urban")
    Agent.objects.create(
        simulation=sim, name="Marco", role="blacksmith",
        personality={"openness": 0.5, "conscientiousness": 0.5, "extraversion": 0.5,
                     "agreeableness": 0.5, "neuroticism": 0.5, "background": "A blacksmith"},
    )
    Agent.objects.create(
        simulation=sim, name="Elena", role="farmer",
        personality={"openness": 0.6, "conscientiousness": 0.7, "extraversion": 0.3,
                     "agreeableness": 0.8, "neuroticism": 0.4, "background": "A farmer"},
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
            {"action": "argue", "agent_name": "Marco",
             "event": {"title": "Marco decided to argue", "severity": 0.4,
                       "agent": "Marco", "reason": "angry"}},
            {"action": "rest", "agent_name": "Elena"},
        ]

        with patch("epocha.apps.simulation.tasks.broadcast_tick") as mock_broadcast:
            finalize_tick(agent_results, sim_with_agents.id, 1)
            mock_broadcast.assert_called_once()
            call_args = mock_broadcast.call_args
            events = call_args[0][2]  # third positional arg
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
        with patch("epocha.apps.simulation.tasks.run_simulation_loop") as mock_loop:
            finalize_tick([], sim_with_agents.id, 1)
            mock_loop.apply_async.assert_called_once()


@pytest.mark.django_db
class TestRunSimulationLoopChord:
    @patch("epocha.apps.agents.tasks.process_agent_decision")
    def test_processes_all_agents(self, mock_decision, sim_with_agents):
        """The chord should dispatch a task for each living agent."""
        mock_decision.return_value = {"action": "work", "reason": "busy"}

        run_simulation_loop(sim_with_agents.id)

        sim_with_agents.refresh_from_db()
        assert sim_with_agents.current_tick == 1
        # Both agents should have been processed
        assert mock_decision.call_count == 2

    @patch("epocha.apps.agents.tasks.process_agent_decision")
    def test_stops_if_not_running(self, mock_decision, sim_with_agents):
        """If simulation is paused, the loop should exit immediately."""
        sim_with_agents.status = Simulation.Status.PAUSED
        sim_with_agents.save()

        run_simulation_loop(sim_with_agents.id)

        mock_decision.assert_not_called()
        sim_with_agents.refresh_from_db()
        assert sim_with_agents.current_tick == 0
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `pytest epocha/apps/simulation/tests/test_tasks.py -v`
Expected: FAIL (finalize_tick does not exist yet)

- [ ] **Step 4: Implement chord-based `run_simulation_loop` and `finalize_tick`**

Replace the contents of `epocha/apps/simulation/tasks.py`:

```python
"""Celery tasks for the simulation tick loop.

Production path: run_simulation_loop runs the economy tick, then launches
a Celery chord of process_agent_turn tasks (one per living agent). When
all agent tasks complete, the finalize_tick callback advances the tick,
decays memories, broadcasts via WebSocket, and re-enqueues the loop.

The chord pattern ensures no worker blocks waiting for others. Each
agent task runs independently and in parallel across available workers.
"""
from __future__ import annotations

import logging

from celery import chord

from config.celery import app

logger = logging.getLogger(__name__)


@app.task
def run_simulation_loop(simulation_id: int) -> None:
    """Execute one tick: economy + parallel agent chord + finalize callback.

    Steps:
    1. Verify simulation is still running
    2. Run economy tick (synchronous, fast)
    3. Launch chord: one process_agent_turn per living agent
    4. Chord callback (finalize_tick) handles the rest
    """
    from epocha.apps.agents.models import Agent
    from epocha.apps.simulation.engine import run_economy
    from epocha.apps.simulation.models import Simulation

    simulation = Simulation.objects.get(id=simulation_id)
    if simulation.status != Simulation.Status.RUNNING:
        logger.info("Simulation %d no longer running, stopping loop", simulation_id)
        return

    tick = simulation.current_tick + 1
    logger.info("Simulation %d: starting tick %d (chord)", simulation_id, tick)

    # 1. Economy tick (fast, synchronous)
    run_economy(simulation)

    # 2. Build chord of agent tasks
    from epocha.apps.agents.tasks import process_agent_turn

    agent_ids = list(
        Agent.objects.filter(simulation=simulation, is_alive=True)
        .values_list("id", flat=True)
    )

    if not agent_ids:
        # No living agents -- finalize immediately
        finalize_tick([], simulation_id, tick)
        return

    header = [
        process_agent_turn.s(agent_id, simulation_id, tick)
        for agent_id in agent_ids
    ]
    callback = finalize_tick.s(simulation_id, tick)

    chord(header)(callback)


@app.task
def finalize_tick(agent_results: list, simulation_id: int, tick: int) -> None:
    """Chord callback: runs after all agent tasks complete.

    Collects events from agent results, decays memories, advances the
    tick counter, broadcasts to WebSocket, and re-enqueues the loop
    if the simulation is still running.

    Args:
        agent_results: List of dicts returned by each process_agent_turn task.
        simulation_id: Primary key of the simulation.
        tick: The tick number that was just processed.
    """
    from django.conf import settings

    from epocha.apps.simulation.engine import broadcast_tick, run_memory_decay
    from epocha.apps.simulation.models import Simulation

    simulation = Simulation.objects.get(id=simulation_id)

    # Collect events from agent results
    events = []
    for result in agent_results:
        if result is None:
            continue
        if "event" in result:
            events.append(result["event"])

    # Memory decay (periodic)
    run_memory_decay(simulation, tick)

    # Advance tick counter
    simulation.current_tick = tick
    simulation.save(update_fields=["current_tick", "updated_at"])

    # Broadcast to WebSocket
    broadcast_tick(simulation, tick, events)

    logger.info("Simulation %d: tick %d complete (chord)", simulation_id, tick)

    # Re-enqueue if still running
    simulation.refresh_from_db()
    if simulation.status == Simulation.Status.RUNNING:
        tick_interval = settings.EPOCHA_DEFAULT_TICK_INTERVAL_SECONDS
        countdown = tick_interval / max(simulation.speed, 0.1)
        run_simulation_loop.apply_async(args=[simulation_id], countdown=countdown)
    else:
        logger.info("Simulation %d paused/stopped, not re-enqueuing", simulation_id)


@app.task(bind=True, acks_late=True)
def run_tick(self, simulation_id: int) -> None:
    """Execute a single simulation tick synchronously (legacy/fallback).

    Kept for backward compatibility with the dashboard's synchronous
    tick execution. Production path uses run_simulation_loop + chord.
    """
    from .engine import SimulationEngine
    from .models import Simulation

    simulation = Simulation.objects.get(id=simulation_id)
    if simulation.status != Simulation.Status.RUNNING:
        return

    engine = SimulationEngine(simulation)
    engine.run_tick()
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest epocha/apps/simulation/tests/test_tasks.py epocha/apps/agents/tests/test_tasks.py -v`
Expected: All tests PASS

- [ ] **Step 6: Commit**

```
feat(simulation): parallel agent processing via Celery chord

CHANGE: Replace sequential agent loop with Celery chord pattern.
run_simulation_loop now launches economy tick, then dispatches one
process_agent_turn task per living agent in parallel. finalize_tick
callback handles memory decay, tick advancement, WebSocket broadcast,
and loop re-enqueue. SimulationEngine kept as synchronous fallback
for dashboard and tests.
```

---

## Task 3: Update existing tests and run full suite

Existing tests in `test_engine.py` mock `process_agent_decision` at the engine level. These should still pass since `SimulationEngine.run_tick()` is preserved as the synchronous path. Verify everything works together.

**Files:**
- Modify: `epocha/apps/simulation/tests/test_engine.py` (if needed)

- [ ] **Step 1: Run the full test suite**

Run: `pytest --cov=epocha -v`
Expected: All tests PASS. If any fail, fix them before proceeding.

- [ ] **Step 2: Verify existing engine tests still pass unchanged**

Run: `pytest epocha/apps/simulation/tests/test_engine.py -v`
Expected: All 6 tests PASS without modification (SimulationEngine.run_tick is preserved).

- [ ] **Step 3: Run agent tests**

Run: `pytest epocha/apps/agents/ -v`
Expected: All agent tests PASS.

- [ ] **Step 4: Commit (only if test fixes were needed)**

```
fix(simulation): adjust tests for chord-based agent processing

CHANGE: <describe what was fixed>.
```

---

## Summary

| Task | What it builds |
|------|---------------|
| 1 | `process_agent_turn` Celery task + extract `apply_agent_action` |
| 2 | `finalize_tick` callback + chord-based `run_simulation_loop` |
| 3 | Full test suite verification |

After completion:
- Each tick processes agents in parallel via Celery chord
- Agent failures are isolated (one failing agent does not block others)
- SimulationEngine preserved as synchronous fallback for dashboard/tests
- WebSocket broadcast includes events from all parallel agent results
- Self-enqueuing loop re-schedules from the finalize_tick callback

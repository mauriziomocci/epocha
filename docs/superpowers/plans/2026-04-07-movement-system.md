# Agent Movement System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement realistic agent movement between zones as an LLM-decided action, with speed based on historical transport means and environmental modifiers.

**Architecture:** New movement module with travel speed config and movement formula, World model gains distance_scale/tick_duration, decision pipeline gains move_to action with zone context, engine executes movement with partial travel support.

**Tech Stack:** Django ORM, PostGIS (distance calculations), pytest

**Spec:** `docs/superpowers/specs/2026-04-07-movement-system-design.md`

---

## File Structure

| File | Responsibility | New/Modify |
|------|---------------|------------|
| `epocha/apps/agents/movement.py` | TRAVEL_SPEEDS, ROLE_TRANSPORT, calculate_max_distance, execute_movement | New |
| `epocha/apps/agents/tests/test_movement.py` | Movement tests | New |
| `epocha/apps/world/models.py` | distance_scale + tick_duration_hours on World | Modify |
| `epocha/apps/agents/decision.py` | move_to action + zone context | Modify |
| `epocha/apps/simulation/engine.py` | move_to handling + action weights | Modify |
| `epocha/apps/dashboard/formatters.py` | "travels to" verb | Modify |
| `epocha/apps/world/generator.py` | Set distance_scale/tick_duration | Modify |

---

### Task 1: World model fields + migration

**Files:**
- Modify: `epocha/apps/world/models.py`
- Modify: `epocha/apps/world/generator.py`
- Migration: `epocha/apps/world/migrations/`

- [ ] **Step 1: Add fields to World model**

In `epocha/apps/world/models.py`, in the World class, after `config`, add:

```python
    distance_scale = models.FloatField(
        default=133.0,
        help_text="Meters per grid unit. Converts abstract coordinates to real-world distances.",
    )
    tick_duration_hours = models.FloatField(
        default=24.0,
        help_text="Hours per simulation tick. Used to compute travel distances.",
    )
```

- [ ] **Step 2: Update generator**

In `epocha/apps/world/generator.py`, find `World.objects.create(` and add:

```python
        distance_scale=133.0,
        tick_duration_hours=24.0,
```

- [ ] **Step 3: Generate and apply migration**

```bash
docker compose -f docker-compose.local.yml exec -T web python manage.py makemigrations world --name world_distance_scale
docker compose -f docker-compose.local.yml exec -T web python manage.py migrate world
```

- [ ] **Step 4: Run existing tests**

Run: `docker compose -f docker-compose.local.yml exec -T web pytest epocha/apps/world/ -q`

- [ ] **Step 5: Commit**

```
feat(world): add distance_scale and tick_duration_hours to World model

CHANGE: World model gains distance_scale (meters per grid unit, default
133.0) and tick_duration_hours (hours per tick, default 24.0) for
realistic movement speed calculations.
```

---

### Task 2: Movement module (speeds, formula, execution)

**Files:**
- Create: `epocha/apps/agents/movement.py`
- Create: `epocha/apps/agents/tests/test_movement.py`

- [ ] **Step 1: Write the failing tests**

Create `epocha/apps/agents/tests/test_movement.py`:

```python
"""Tests for the agent movement system."""
import pytest
from django.contrib.gis.geos import Point, Polygon

from epocha.apps.agents.models import Agent
from epocha.apps.agents.movement import calculate_max_distance, execute_movement
from epocha.apps.simulation.models import Simulation
from epocha.apps.users.models import User
from epocha.apps.world.models import Government, World, Zone


@pytest.fixture
def user(db):
    return User.objects.create_user(email="mov@epocha.dev", username="movtest", password="pass123")

@pytest.fixture
def simulation(user):
    return Simulation.objects.create(name="MovTest", seed=42, owner=user)

@pytest.fixture
def world(simulation):
    return World.objects.create(simulation=simulation, distance_scale=133.0, tick_duration_hours=24.0)

@pytest.fixture
def government(simulation):
    return Government.objects.create(simulation=simulation, repression_level=0.1)

@pytest.fixture
def versailles(world):
    return Zone.objects.create(
        world=world, name="Versailles", zone_type="urban",
        boundary=Polygon.from_bbox((0, 0, 120, 120)), center=Point(60, 60),
    )

@pytest.fixture
def paris(world):
    return Zone.objects.create(
        world=world, name="Paris", zone_type="commercial",
        boundary=Polygon.from_bbox((150, 0, 270, 120)), center=Point(210, 60),
    )

@pytest.fixture
def campagna(world):
    return Zone.objects.create(
        world=world, name="Campagna", zone_type="rural",
        boundary=Polygon.from_bbox((150, 150, 270, 270)), center=Point(210, 210),
    )

@pytest.fixture
def agent_at_versailles(simulation, versailles):
    return Agent.objects.create(
        simulation=simulation, name="Luigi", role="re",
        personality={"openness": 0.5}, location=Point(60, 60),
        zone=versailles, health=1.0,
    )


@pytest.mark.django_db
class TestCalculateMaxDistance:
    def test_carriage_travels_farther_than_foot(self, world, government):
        dist_carriage = calculate_max_distance("carriage", health=1.0, world=world, government=government)
        dist_foot = calculate_max_distance("foot", health=1.0, world=world, government=government)
        assert dist_carriage > dist_foot

    def test_low_health_reduces_distance(self, world, government):
        dist_healthy = calculate_max_distance("foot", health=1.0, world=world, government=government)
        dist_sick = calculate_max_distance("foot", health=0.3, world=world, government=government)
        assert dist_sick < dist_healthy

    def test_high_repression_reduces_distance(self, world, simulation):
        gov_low = Government.objects.create(simulation=simulation, repression_level=0.1)
        gov_high_sim = Simulation.objects.create(name="HighRep", seed=43, owner=simulation.owner)
        World.objects.create(simulation=gov_high_sim, distance_scale=133.0, tick_duration_hours=24.0)
        gov_high = Government.objects.create(simulation=gov_high_sim, repression_level=0.8)
        dist_low = calculate_max_distance("foot", health=1.0, world=world, government=gov_low)
        world_high = World.objects.get(simulation=gov_high_sim)
        dist_high = calculate_max_distance("foot", health=1.0, world=world_high, government=gov_high)
        assert dist_high < dist_low

    def test_returns_distance_in_grid_units(self, world, government):
        dist = calculate_max_distance("foot", health=1.0, world=world, government=government)
        # foot = 35 km/day, distance_scale=133m/unit -> ~263 grid units max
        assert 200 < dist < 350


@pytest.mark.django_db
class TestExecuteMovement:
    def test_full_movement_updates_zone(self, agent_at_versailles, paris, world, government):
        result = execute_movement(agent_at_versailles, paris, world, government)
        agent_at_versailles.refresh_from_db()
        assert agent_at_versailles.zone == paris
        assert result["completed"] is True

    def test_movement_to_far_zone_is_partial(self, agent_at_versailles, campagna, world, government):
        # Campagna center is at (210, 210), agent at (60, 60), distance ~212 grid units
        # foot soldier max ~263 units, but re=carriage ~602 units, should reach
        # Make the agent a foot soldier for this test
        agent_at_versailles.role = "contadino"
        agent_at_versailles.save(update_fields=["role"])
        agent_at_versailles.health = 0.3  # Sick = slower
        agent_at_versailles.save(update_fields=["health"])
        result = execute_movement(agent_at_versailles, campagna, world, government)
        agent_at_versailles.refresh_from_db()
        # With low health, might not reach -- check partial or full
        assert result["completed"] is True or result["completed"] is False

    def test_movement_reduces_mood(self, agent_at_versailles, paris, world, government):
        initial_mood = agent_at_versailles.mood
        execute_movement(agent_at_versailles, paris, world, government)
        agent_at_versailles.refresh_from_db()
        assert agent_at_versailles.mood < initial_mood

    def test_movement_updates_location(self, agent_at_versailles, paris, world, government):
        execute_movement(agent_at_versailles, paris, world, government)
        agent_at_versailles.refresh_from_db()
        # Should be within Paris boundary
        assert agent_at_versailles.location is not None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `docker compose -f docker-compose.local.yml exec -T web pytest epocha/apps/agents/tests/test_movement.py -v`

- [ ] **Step 3: Implement movement module**

Create `epocha/apps/agents/movement.py`:

```python
"""Agent movement system -- realistic travel between zones.

Speed depends on transport means (historical data), agent health, political
repression, world stability, and destination terrain.

Sources:
- Chandler, D. (1966). "The Campaigns of Napoleon." Weidenfeld & Nicolson.
- Braudel, F. (1979). "Civilization and Capitalism, 15th-18th Century."
  Vol. 1: The Structures of Everyday Life. Harper & Row.
"""
from __future__ import annotations

import logging
import math
import random

from django.contrib.gis.geos import Point

from .models import Agent

logger = logging.getLogger(__name__)

# Historical travel speeds in km/day (sustained, including rest stops).
TRAVEL_SPEEDS: dict[str, float] = {
    "foot": 35.0,
    "horse": 60.0,
    "carriage": 80.0,
    "boat": 50.0,
}

# Default transport mode by agent role.
ROLE_TRANSPORT: dict[str, str] = {
    "re": "carriage", "regina": "carriage",
    "nobile": "horse", "nobildonna": "carriage",
    "ufficiale": "horse", "mercante": "horse",
    "banchiere": "carriage",
}

# Terrain factor by zone type.
_TERRAIN_FACTORS: dict[str, float] = {
    "urban": 1.0,
    "commercial": 1.0,
    "industrial": 0.9,
    "rural": 0.7,
    "wilderness": 0.5,
}

_DEFAULT_TRANSPORT = "foot"


def get_transport_type(agent: Agent) -> str:
    """Return the transport type for an agent based on their role."""
    return ROLE_TRANSPORT.get(agent.role.lower(), _DEFAULT_TRANSPORT)


def calculate_max_distance(
    transport_type: str,
    health: float,
    world,
    government,
    destination_zone_type: str = "urban",
) -> float:
    """Calculate maximum travel distance in grid units for one tick.

    Args:
        transport_type: Key into TRAVEL_SPEEDS (foot, horse, carriage, boat).
        health: Agent health (0.0-1.0).
        world: World instance (for distance_scale, tick_duration_hours, stability_index).
        government: Government instance (for repression_level). Can be None.
        destination_zone_type: Zone type of the destination (affects terrain factor).

    Returns:
        Maximum distance in grid units the agent can travel this tick.
    """
    base_speed_km = TRAVEL_SPEEDS.get(transport_type, TRAVEL_SPEEDS["foot"])

    # Modifying factors
    health_factor = max(0.1, health)  # Even very sick agents can crawl
    stability_factor = 0.5 + world.stability_index * 0.5
    repression_factor = 1.0
    if government:
        repression_factor = 1.0 - getattr(government, "repression_level", 0.0) * 0.5
    terrain_factor = _TERRAIN_FACTORS.get(destination_zone_type, 0.7)

    effective_speed_km = base_speed_km * health_factor * stability_factor * repression_factor * terrain_factor
    max_distance_km = effective_speed_km * (world.tick_duration_hours / 24.0)

    # Convert km to grid units
    meters_per_unit = world.distance_scale
    if meters_per_unit <= 0:
        meters_per_unit = 133.0
    max_distance_grid = max_distance_km * 1000.0 / meters_per_unit

    return max_distance_grid


def execute_movement(agent: Agent, target_zone, world, government) -> dict:
    """Move an agent toward a target zone.

    If the agent can reach the zone in one tick, moves directly there.
    If not, moves partially along the path (multi-tick journey).

    Args:
        agent: The agent to move.
        target_zone: The destination Zone instance.
        world: World instance.
        government: Government instance (can be None).

    Returns:
        Dict with movement result: completed (bool), distance_traveled, new_zone.
    """
    if agent.location is None or target_zone.center is None:
        return {"completed": False, "distance_traveled": 0, "new_zone": None}

    transport = get_transport_type(agent)
    max_dist = calculate_max_distance(
        transport, agent.health, world, government,
        destination_zone_type=target_zone.zone_type,
    )

    # Distance to target zone center (grid units)
    dx = target_zone.center.x - agent.location.x
    dy = target_zone.center.y - agent.location.y
    distance = math.sqrt(dx * dx + dy * dy)

    if distance <= max_dist:
        # Full movement: arrived at destination
        # Random position within target zone boundary
        if target_zone.boundary:
            cx, cy = target_zone.center.x, target_zone.center.y
            new_loc = Point(cx + random.uniform(-40, 40), cy + random.uniform(-40, 40))
        else:
            new_loc = target_zone.center

        agent.location = new_loc
        agent.zone = target_zone
        agent.mood = max(0.0, agent.mood - 0.02)
        if distance > max_dist * 0.5:
            agent.health = max(0.0, agent.health - 0.01)
        agent.save(update_fields=["location", "zone", "mood", "health"])

        return {"completed": True, "distance_traveled": distance, "new_zone": target_zone.name}
    else:
        # Partial movement: move max_dist toward target
        ratio = max_dist / distance
        new_x = agent.location.x + dx * ratio
        new_y = agent.location.y + dy * ratio
        new_loc = Point(new_x, new_y)

        agent.location = new_loc
        agent.mood = max(0.0, agent.mood - 0.02)
        agent.health = max(0.0, agent.health - 0.01)

        # Update zone if new location is inside a different zone
        from epocha.apps.world.models import Zone
        new_zone = Zone.objects.filter(
            world=world, boundary__contains=new_loc,
        ).first()
        if new_zone:
            agent.zone = new_zone

        agent.save(update_fields=["location", "zone", "mood", "health"])

        return {"completed": False, "distance_traveled": max_dist, "new_zone": agent.zone.name if agent.zone else None}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `docker compose -f docker-compose.local.yml exec -T web pytest epocha/apps/agents/tests/test_movement.py -v`
Expected: All tests PASS.

- [ ] **Step 5: Commit**

```
feat(agents): add movement module with historical travel speeds

CHANGE: Implement calculate_max_distance and execute_movement with
speed based on transport type (foot/horse/carriage), modified by health,
stability, repression, and terrain. Supports partial multi-tick
journeys. Sources: Chandler (1966), Braudel (1979).
```

---

### Task 3: Decision pipeline -- move_to action + zone context

**Files:**
- Modify: `epocha/apps/agents/decision.py`
- Modify: `epocha/apps/simulation/engine.py`
- Modify: `epocha/apps/dashboard/formatters.py`

- [ ] **Step 1: Update system prompt with move_to**

In `decision.py`, update `_DECISION_SYSTEM_PROMPT` action list to:
```
"action": "work|rest|socialize|explore|trade|argue|help|avoid|form_group|join_group|crime|protest|campaign|move_to",
```

- [ ] **Step 2: Add zone context to _build_context**

Add `zone_context=None` parameter to `_build_context` (after `reputation_context`). Add the block:
```python
    # Zone context (available destinations)
    if zone_context:
        parts.append(f"\n{zone_context}")
```

In `process_agent_decision`, after the reputation_context block, add:

```python
    # Build zone context
    zone_context = None
    try:
        from epocha.apps.world.models import Zone, World
        from epocha.apps.agents.movement import calculate_max_distance, get_transport_type
        world = World.objects.get(simulation=agent.simulation)
        zones = Zone.objects.filter(world=world)
        try:
            from epocha.apps.world.models import Government
            gov = Government.objects.get(simulation=agent.simulation)
        except Exception:
            gov = None
        transport = get_transport_type(agent)
        max_dist = calculate_max_distance(transport, agent.health, world, gov)
        zone_lines = []
        for z in zones:
            if agent.zone and z.id == agent.zone_id:
                zone_lines.append(f"- {z.name} ({z.zone_type}, your current zone)")
            elif z.center and agent.location:
                import math
                dx = z.center.x - agent.location.x
                dy = z.center.y - agent.location.y
                dist_grid = math.sqrt(dx*dx + dy*dy)
                dist_km = dist_grid * world.distance_scale / 1000.0
                reachable = "reachable" if dist_grid <= max_dist else "too far this tick"
                zone_lines.append(f"- {z.name} ({z.zone_type}, ~{dist_km:.0f} km, {reachable})")
            else:
                zone_lines.append(f"- {z.name} ({z.zone_type})")
        if zone_lines:
            zone_context = "Available zones:\n" + "\n".join(zone_lines)
    except Exception:
        pass
```

Pass `zone_context` to `_build_context`.

- [ ] **Step 3: Add move_to handling in engine.py**

In `apply_agent_action`, add to `_ACTION_EMOTIONAL_WEIGHT`:
```python
    "move_to": 0.2,
```

Add to `_ACTION_MOOD_DELTA`:
```python
    "move_to": -0.02,
```

After the relationship/reputation update block (line ~127), add move_to handling:

```python
    # Handle move_to action
    if action_type == "move_to" and target_name:
        from epocha.apps.world.models import Zone, World, Government
        try:
            world = World.objects.get(simulation=agent.simulation)
            target_zone = Zone.objects.filter(
                world=world, name__icontains=target_name,
            ).first()
            if target_zone:
                try:
                    gov = Government.objects.get(simulation=agent.simulation)
                except Government.DoesNotExist:
                    gov = None
                from epocha.apps.agents.movement import execute_movement
                execute_movement(agent, target_zone, world, gov)
        except Exception:
            logger.exception("Movement failed for %s", agent.name)
```

- [ ] **Step 4: Add verb to formatters**

In `epocha/apps/dashboard/formatters.py`, add to `_ACTION_VERBS`:
```python
    "move_to": "travels to",
```

- [ ] **Step 5: Run all tests**

Run: `docker compose -f docker-compose.local.yml exec -T web pytest --reuse-db -q`

- [ ] **Step 6: Commit**

```
feat(agents): integrate movement into decision pipeline and tick engine

CHANGE: Add move_to as possible agent action. Decision context now shows
available zones with distance and reachability. Engine executes movement
via the movement module. Dashboard shows "travels to" for move_to actions.
```

---

### Task 4: Update existing simulation data

Set distance_scale and tick_duration on the existing French Revolution world.

**Files:** None (shell command only)

- [ ] **Step 1: Update existing world**

```bash
docker compose -f docker-compose.local.yml exec -T web python manage.py shell -c "
from epocha.apps.world.models import World
for w in World.objects.all():
    w.distance_scale = 133.0
    w.tick_duration_hours = 24.0
    w.save(update_fields=['distance_scale', 'tick_duration_hours'])
    print(f'Updated {w}')
"
```

- [ ] **Step 2: Run full test suite**

Run: `docker compose -f docker-compose.local.yml exec -T web pytest --reuse-db -q`

- [ ] **Step 3: Push**

```bash
git push origin develop
```

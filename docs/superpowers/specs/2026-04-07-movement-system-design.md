# Agent Movement System -- Design Spec

## Goal

Implement a realistic movement system where agents decide to travel between zones as an LLM action. Movement speed depends on historical transport means, agent health, political repression, world stability, and terrain. Migrations emerge naturally when circumstances push multiple agents in the same direction.

## Scientific Foundation

- Chandler, D. (1966). "The Campaigns of Napoleon." Weidenfeld & Nicolson. Infantry march rates, cavalry speeds, logistics of 18th-19th century movement.
- Braudel, F. (1979). "Civilization and Capitalism, 15th-18th Century." Vol. 1: The Structures of Everyday Life. Harper & Row. Pre-industrial travel speeds, road conditions, seasonal effects on mobility.

## Principle

Movement is an agent decision, not an automation. `move_to` is an action like `argue` or `help`. The LLM decides whether and where to move based on context (zone conditions, hearsay about other zones, personal goals). Mass migrations emerge naturally when circumstances (famine, war, epidemic) push multiple agents toward the same destination.

## Model Changes

### World -- two new fields

In `epocha/apps/world/models.py`, add to the World class:

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

With the current grid layout (zone spacing ~150 units) and `distance_scale=133`, 150 units = ~20 km (Versailles to Paris). One tick = 24 hours = 1 day.

## Travel Speed Configuration

Data-driven configuration in `epocha/apps/agents/movement.py`:

```python
# Historical travel speeds in km/day (sustained, including rest stops).
# Source: Chandler (1966) for military marches; Braudel (1979) for civilian travel.
TRAVEL_SPEEDS: dict[str, float] = {
    "foot": 35.0,       # Infantry march rate, ~4 km/h sustained over 8-9 hours
    "horse": 60.0,      # Cavalry at sustained pace, ~8 km/h over 7-8 hours
    "carriage": 80.0,   # Noble/royal carriage on main roads, ~10 km/h
    "boat": 50.0,       # River navigation, current-dependent
}

# Default transport mode by agent role.
# Can be overridden per simulation for different historical periods.
ROLE_TRANSPORT: dict[str, str] = {
    "re": "carriage",
    "regina": "carriage",
    "nobile": "horse",
    "nobildonna": "carriage",
    "ufficiale": "horse",
    "mercante": "horse",
    "banchiere": "carriage",
    # All unlisted roles default to "foot"
}
```

For different historical periods (modern, medieval, ancient), only the speed tables need to change. The formulas stay the same.

## Movement Formula

```
base_speed_km = TRAVEL_SPEEDS[transport_type]
effective_speed = base_speed_km * health_factor * stability_factor * repression_factor
max_distance_km = effective_speed * (tick_duration_hours / 24.0)
max_distance_grid = max_distance_km / (distance_scale / 1000.0)
can_reach = PostGIS_distance(agent.location, target_zone.center) <= max_distance_grid
```

### Modifying factors

| Factor | Formula | Range | Source |
|--------|---------|-------|--------|
| health_factor | `agent.health` | 0.0-1.0 | Linear: half health = half speed. Injuries and illness slow travel. |
| stability_factor | `0.5 + world.stability_index * 0.5` | 0.5-1.0 | Even in chaos people move, but slower (unsafe roads, checkpoints, refugees blocking paths). Source: Braudel (1979) on mobility during periods of instability. |
| repression_factor | `1.0 - government.repression_level * 0.5` | 0.5-1.0 | Repressive governments restrict movement (curfews, travel papers, checkpoints). Source: analogous to Freedom House civil liberties indicators where movement restriction correlates with authoritarianism. |
| terrain_factor | Per destination zone type | 0.5-1.0 | urban=1.0 (paved roads), commercial=1.0 (trade routes), industrial=0.9 (workers' paths), rural=0.7 (dirt roads), wilderness=0.5 (no roads). Source: Braudel (1979) Chapter 7 on road quality and travel times. |

All factors are clamped to their stated ranges. Future factors (weather, military blockades, seasonal roads) can be added as additional multipliers without changing the formula structure.

## Decision Pipeline Integration

### New action: move_to

Add to `_DECISION_SYSTEM_PROMPT` in `decision.py`:

```
"action": "work|rest|socialize|explore|trade|argue|help|avoid|form_group|join_group|crime|protest|campaign|move_to",
"target": "zone name (for move_to) or who/what (for others)",
```

### Zone context in _build_context

Add zone information to the agent's decision context:

```
Available zones:
- Versailles (urban, your current zone): wealthy area, royal court
- Parigi centro (commercial, ~20 km, reachable): trade hub, moderate wealth
- Faubourg Saint-Antoine (industrial, ~22 km, reachable): poor area, unrest
- Campagna francese (rural, ~100 km, too far this tick): farming, very poor
```

Each zone shows: name, type, approximate distance in km, reachability status, and a brief description derived from zone resources and the agents/factions present there.

Zones marked "too far this tick" signal to the LLM that multi-tick travel is required. The LLM can still choose `move_to` for a far zone -- the system will execute partial movement.

## Movement Execution

In `apply_agent_action` (engine.py), when `action_type == "move_to"`:

### Step 1: Find target zone

Match the target name against zones in the simulation (case-insensitive `icontains`).

### Step 2: Calculate reachability

```python
from django.contrib.gis.db.models.functions import Distance
distance_grid = agent.location.distance(target_zone.center)  # Grid units
distance_km = distance_grid * (world.distance_scale / 1000.0)
max_km = calculate_max_distance(agent, world, government)
can_reach = distance_km <= max_km
```

### Step 3a: Full movement (can reach)

If the agent can reach the target zone in this tick:
- Set `agent.location` to a random point within the target zone boundary
- Set `agent.zone` to the target zone
- Create memory: "I traveled to [zone name]."

### Step 3b: Partial movement (too far)

If the agent cannot reach in one tick:
- Calculate the direction vector from current location to target zone center
- Move the agent `max_distance_grid` units along that vector
- Update `agent.location` (new point along the path)
- Set `agent.zone` to whichever zone the new location falls within (PostGIS `ST_Within`), or keep current zone if between zones
- Create memory: "I started traveling toward [zone name]. Still on the road."

### Step 4: Movement costs

- Mood: `-0.02` for any movement (travel is tiring)
- Health: `-0.01` only if distance traveled > 50% of max (long, exhausting journey)

## Action Configuration

In `engine.py`, add to `_ACTION_EMOTIONAL_WEIGHT`:
```python
"move_to": 0.2,  # Movement is notable but not dramatic
```

Add to `_ACTION_MOOD_DELTA`:
```python
"move_to": -0.02,  # Travel is tiring
```

In `dashboard/formatters.py`, add to `_ACTION_VERBS`:
```python
"move_to": "travels to",
```

## World Generator Update

In `epocha/apps/world/generator.py`, when creating the World, set:

```python
world = World.objects.create(
    simulation=simulation,
    distance_scale=133.0,   # ~20 km between adjacent zones
    tick_duration_hours=24.0,  # 1 tick = 1 day
    ...
)
```

These values are appropriate for the 18th century French Revolution simulation. Different simulations can use different values.

## Files

**New files:**

| File | Responsibility |
|------|---------------|
| `epocha/apps/agents/movement.py` | TRAVEL_SPEEDS, ROLE_TRANSPORT, calculate_max_distance, execute_movement |
| `epocha/apps/agents/tests/test_movement.py` | Movement tests |

**Modified files:**

| File | Change |
|------|--------|
| `epocha/apps/world/models.py` | Add distance_scale + tick_duration_hours to World |
| `epocha/apps/agents/decision.py` | Add move_to to system prompt + zone context in _build_context |
| `epocha/apps/simulation/engine.py` | Handle move_to in apply_agent_action + action weights |
| `epocha/apps/dashboard/formatters.py` | Add "travels to" verb |
| `epocha/apps/world/generator.py` | Set distance_scale and tick_duration_hours |

## What This Does NOT Cover

- Weather system (future: rain/snow reduce terrain_factor further)
- Road/infrastructure network (future: roads as LineString geometries connecting zones)
- Military blockades (current proxy: repression_factor)
- Seasonal effects (future: winter reduces all movement)
- Collective transport (caravans, army marches -- future)
- Information flow proximity enhancement (future: agents in same zone share info more easily)
- Cost of travel (future: horse rental, inn stays deduct from wealth)

These are documented as future extensions. The formula structure (`effective_speed = base * factor1 * factor2 * ...`) makes adding new factors trivial.

## Performance

- Movement calculation: 1 distance computation + 1 formula evaluation per moving agent per tick. PostGIS distance is O(1). Negligible.
- Zone context in _build_context: 1 query for all zones (cached for the tick). Negligible.
- Partial movement: 1 point computation + 1 ST_Within query. Negligible.

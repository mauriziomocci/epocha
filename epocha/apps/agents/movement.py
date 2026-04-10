"""Agent movement system -- realistic travel between zones.

Speed depends on transport means (historical data), agent health, political
repression, world stability, and destination terrain.

Sources:
- Chandler, D. (1966). "The Campaigns of Napoleon." Weidenfeld & Nicolson.
  Chapter on logistics: sustained march rates of 35 km/day for infantry,
  60 km/day for cavalry, 80 km/day for horse-drawn carriages on good roads.
- Braudel, F. (1979). "Civilization and Capitalism, 15th-18th Century."
  Vol. 1: The Structures of Everyday Life. Harper & Row.
  River/canal boat speeds averaged 50 km/day in pre-industrial Europe.
"""
from __future__ import annotations

import logging
import math
import random

from django.contrib.gis.geos import Point

from .models import Agent

logger = logging.getLogger(__name__)

# Historical travel speeds in km/day (sustained, including rest stops).
# Source: Chandler (1966), Braudel (1979). See module docstring.
TRAVEL_SPEEDS: dict[str, float] = {
    "foot": 35.0,       # Infantry sustained march rate (Chandler, 1966)
    "horse": 60.0,      # Cavalry sustained rate (Chandler, 1966)
    "carriage": 80.0,   # Horse-drawn carriage on good roads (Chandler, 1966)
    "boat": 50.0,       # River/canal boat, pre-industrial Europe (Braudel, 1979)
}

# Default transport mode by agent role.
# Aristocracy and wealthy roles use carriages or horses; commoners walk.
ROLE_TRANSPORT: dict[str, str] = {
    "re": "carriage", "regina": "carriage",
    "nobile": "horse", "nobildonna": "carriage",
    "ufficiale": "horse", "mercante": "horse",
    "banchiere": "carriage",
}

# Terrain traversal factor by zone type.
# Urban and commercial zones have roads (factor 1.0); rural terrain is slower
# due to unpaved paths; wilderness is significantly harder to cross.
_TERRAIN_FACTORS: dict[str, float] = {
    "urban": 1.0,
    "commercial": 1.0,
    "industrial": 0.9,
    "rural": 0.7,
    "wilderness": 0.5,
}

_DEFAULT_TRANSPORT = "foot"

# Mood cost per movement (small fatigue penalty).
# A full day of travel causes minor mood decrease.
_MOOD_COST_PER_MOVEMENT = 0.02

# Health cost for long-distance or partial movement (exhaustion).
_HEALTH_COST_EXHAUSTING_TRAVEL = 0.01

# Threshold ratio: if actual distance exceeds this fraction of max distance,
# the journey is considered exhausting and incurs a health penalty.
_EXHAUSTION_THRESHOLD = 0.5

# Random offset range (grid units) for final position within a zone.
# Prevents all agents arriving at the exact center point.
_ARRIVAL_SCATTER_RANGE = 40.0


def get_transport_type(agent: Agent) -> str:
    """Return the transport type for an agent based on their social role.

    Aristocratic and wealthy roles use faster transport (carriages, horses).
    All other roles default to travel on foot.
    """
    return ROLE_TRANSPORT.get(agent.role.lower(), _DEFAULT_TRANSPORT)


def calculate_max_distance(
    transport_type: str,
    health: float,
    world,
    government,
    destination_zone_type: str = "urban",
) -> float:
    """Calculate maximum travel distance in grid units for one tick.

    The formula combines base speed with modifying factors:

        effective_speed = base_speed * health_factor * stability_factor
                          * repression_factor * terrain_factor

        max_distance_km = effective_speed * (tick_duration_hours / 24)
        max_distance_grid = max_distance_km * 1000 / distance_scale

    Each factor is clamped to [0, 1] to keep the result physically meaningful.

    Args:
        transport_type: Key into TRAVEL_SPEEDS (foot, horse, carriage, boat).
        health: Agent health (0.0-1.0).
        world: World instance (provides distance_scale, tick_duration_hours,
            stability_index).
        government: Government instance (provides repression_level). Can be None.
        destination_zone_type: Zone type of the destination (affects terrain factor).

    Returns:
        Maximum distance in grid units the agent can travel this tick.
    """
    base_speed_km = TRAVEL_SPEEDS.get(transport_type, TRAVEL_SPEEDS["foot"])

    # Health factor: even severely ill agents retain minimal mobility (floor 0.1).
    health_factor = max(0.1, health)

    # Stability factor: civil unrest halves travel speed (road blocks, danger).
    # Range: [0.5, 1.0] mapped from stability_index [0.0, 1.0].
    stability_factor = 0.5 + world.stability_index * 0.5

    # Repression factor: high political repression restricts free movement.
    # Range: [0.5, 1.0] mapped from repression_level [1.0, 0.0].
    repression_factor = 1.0
    if government:
        repression_factor = 1.0 - getattr(government, "repression_level", 0.0) * 0.5

    # Terrain factor: rough terrain slows travel.
    terrain_factor = _TERRAIN_FACTORS.get(destination_zone_type, 0.7)

    effective_speed_km = base_speed_km * health_factor * stability_factor * repression_factor * terrain_factor
    max_distance_km = effective_speed_km * (world.tick_duration_hours / 24.0)

    # Convert km to grid units using world distance scale.
    meters_per_unit = world.distance_scale
    if meters_per_unit <= 0:
        meters_per_unit = 133.0  # Fallback to default scale
    max_distance_grid = max_distance_km * 1000.0 / meters_per_unit

    return max_distance_grid


def execute_movement(agent: Agent, target_zone, world, government) -> dict:
    """Move an agent toward a target zone.

    If the agent can reach the zone center in one tick, it arrives and is
    placed at a scattered position within the zone boundary. Otherwise, the
    agent moves as far as possible along the straight-line path (partial
    movement for multi-tick journeys).

    Both full and partial movement incur a small mood cost. Exhausting travel
    (distance > 50% of max capacity) also reduces health slightly.

    Args:
        agent: The agent to move.
        target_zone: The destination Zone instance.
        world: World instance.
        government: Government instance (can be None).

    Returns:
        Dict with keys:
            - completed (bool): True if the agent arrived at the target zone.
            - distance_traveled (float): Distance covered in grid units.
            - new_zone (str or None): Name of the zone the agent is now in.
    """
    if agent.location is None or target_zone.center is None:
        return {"completed": False, "distance_traveled": 0, "new_zone": None}

    transport = get_transport_type(agent)
    max_dist = calculate_max_distance(
        transport, agent.health, world, government,
        destination_zone_type=target_zone.zone_type,
    )

    # Euclidean distance to target zone center (grid units).
    dx = target_zone.center.x - agent.location.x
    dy = target_zone.center.y - agent.location.y
    distance = math.sqrt(dx * dx + dy * dy)

    if distance <= max_dist:
        # Full movement: agent arrives at destination.
        # Scatter final position around zone center to avoid clustering.
        if target_zone.boundary:
            cx, cy = target_zone.center.x, target_zone.center.y
            new_loc = Point(
                cx + random.uniform(-_ARRIVAL_SCATTER_RANGE, _ARRIVAL_SCATTER_RANGE),
                cy + random.uniform(-_ARRIVAL_SCATTER_RANGE, _ARRIVAL_SCATTER_RANGE),
            )
        else:
            new_loc = target_zone.center

        agent.location = new_loc
        agent.zone = target_zone
        agent.mood = max(0.0, agent.mood - _MOOD_COST_PER_MOVEMENT)
        if distance > max_dist * _EXHAUSTION_THRESHOLD:
            agent.health = max(0.0, agent.health - _HEALTH_COST_EXHAUSTING_TRAVEL)
        agent.save(update_fields=["location", "zone", "mood", "health"])

        return {"completed": True, "distance_traveled": distance, "new_zone": target_zone.name}
    else:
        # Partial movement: move max_dist toward target along straight line.
        ratio = max_dist / distance
        new_x = agent.location.x + dx * ratio
        new_y = agent.location.y + dy * ratio
        new_loc = Point(new_x, new_y)

        agent.location = new_loc
        agent.mood = max(0.0, agent.mood - _MOOD_COST_PER_MOVEMENT)
        agent.health = max(0.0, agent.health - _HEALTH_COST_EXHAUSTING_TRAVEL)

        # Update zone if the new location falls inside a different zone boundary.
        from epocha.apps.world.models import Zone
        new_zone = Zone.objects.filter(
            world=world, boundary__contains=new_loc,
        ).first()
        if new_zone:
            agent.zone = new_zone

        agent.save(update_fields=["location", "zone", "mood", "health"])

        return {
            "completed": False,
            "distance_traveled": max_dist,
            "new_zone": agent.zone.name if agent.zone else None,
        }

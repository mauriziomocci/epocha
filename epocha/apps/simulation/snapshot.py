"""Per-tick snapshot capture for analytics.

capture_snapshot() collects all KPIs from the simulation state in a single
database round-trip where possible and writes one SimulationSnapshot record.
It is called by the tick engine after each tick completes so that the analytics
dashboard always has a consistent time-series to read from.
"""
from __future__ import annotations

import logging

from django.db.models import Avg, Count

from epocha.apps.agents.models import Agent, Group
from epocha.apps.world.models import Government
from epocha.apps.world.stratification import compute_gini

from .models import SimulationSnapshot

logger = logging.getLogger(__name__)

# Social-class labels recognised by this module, in canonical order.
# "enslaved" is treated as "poor" throughout (absorbed into class_poor_pct).
_CLASS_FIELDS: dict[str, str] = {
    "elite": "class_elite_pct",
    "wealthy": "class_wealthy_pct",
    "middle": "class_middle_pct",
    "working": "class_working_pct",
    "poor": "class_poor_pct",
}


def _collect_population(simulation) -> dict:
    """Return alive/dead agent counts for the simulation."""
    counts = (
        Agent.objects.filter(simulation=simulation)
        .values("is_alive")
        .annotate(c=Count("id"))
    )
    alive = 0
    dead = 0
    for row in counts:
        if row["is_alive"]:
            alive = row["c"]
        else:
            dead = row["c"]
    return {"population_alive": alive, "population_dead": dead}


def _collect_economy(simulation) -> dict:
    """Return average wealth and Gini coefficient for living agents.

    The Gini coefficient is computed from the full wealth distribution using
    the standard sorted-array formula implemented in world.stratification.
    Reference: Gini, C. (1912). "Variabilita e mutabilita."
    """
    agg = Agent.objects.filter(simulation=simulation, is_alive=True).aggregate(avg=Avg("wealth"))
    avg_wealth = round(agg["avg"] or 0.0, 4)

    wealths = list(
        Agent.objects.filter(simulation=simulation, is_alive=True).values_list("wealth", flat=True)
    )
    gini = round(compute_gini(wealths), 4)
    return {"avg_wealth": avg_wealth, "gini_coefficient": gini}


def _collect_social(simulation) -> dict:
    """Return average mood and faction count.

    Only groups with cohesion > 0 are counted as active factions, matching the
    semantic that a dissolved/inactive group has cohesion=0.
    """
    agg = Agent.objects.filter(simulation=simulation, is_alive=True).aggregate(avg=Avg("mood"))
    avg_mood = round(agg["avg"] or 0.0, 4)
    faction_count = Group.objects.filter(simulation=simulation, cohesion__gt=0).count()
    return {"avg_mood": avg_mood, "faction_count": faction_count}


def _collect_government(simulation) -> dict:
    """Return political indicators from the Government record, or safe defaults.

    Government is a OneToOne on Simulation. If the simulation has no government
    yet (DoesNotExist), all indicators default to 0 and government_type to "".
    """
    try:
        gov = Government.objects.get(simulation=simulation)
        return {
            "government_type": gov.government_type,
            "government_stability": round(gov.stability, 4),
            "institutional_trust": round(gov.institutional_trust, 4),
            "repression_level": round(gov.repression_level, 4),
            "corruption": round(gov.corruption, 4),
            "popular_legitimacy": round(gov.popular_legitimacy, 4),
            "military_loyalty": round(gov.military_loyalty, 4),
        }
    except Government.DoesNotExist:
        return {
            "government_type": "",
            "government_stability": 0.0,
            "institutional_trust": 0.0,
            "repression_level": 0.0,
            "corruption": 0.0,
            "popular_legitimacy": 0.0,
            "military_loyalty": 0.0,
        }


def _collect_class_distribution(simulation) -> dict:
    """Return social class distribution as fractions summing to 1.0.

    Agents with social_class "enslaved" are absorbed into the "poor" stratum.
    Dead agents are excluded so the distribution reflects the living population.
    """
    rows = (
        Agent.objects.filter(simulation=simulation, is_alive=True)
        .values("social_class")
        .annotate(c=Count("id"))
    )
    class_counts: dict[str, int] = {label: 0 for label in _CLASS_FIELDS}
    total = 0
    for row in rows:
        label = row["social_class"]
        count = row["c"]
        total += count
        # Absorb "enslaved" into "poor".
        if label == "enslaved":
            label = "poor"
        if label in class_counts:
            class_counts[label] += count
        else:
            # Unknown class label: treat as poor to avoid silent data loss.
            class_counts["poor"] += count

    if total == 0:
        return {field: 0.0 for field in _CLASS_FIELDS.values()}

    return {
        field: round(class_counts[label] / total, 4)
        for label, field in _CLASS_FIELDS.items()
    }


def capture_snapshot(simulation, tick: int) -> SimulationSnapshot:
    """Capture all KPIs for a simulation at a given tick into a SimulationSnapshot record.

    Collects population counts, economic indicators (wealth, Gini), social
    indicators (mood, faction count), government political indicators, and
    class distribution in separate focused queries, then writes a single
    SimulationSnapshot row.

    If a snapshot for (simulation, tick) already exists it is overwritten via
    update_or_create, making the function safe for re-runs on the same tick.

    Args:
        simulation: Simulation instance for which to capture the snapshot.
        tick: Tick number to tag this snapshot with.

    Returns:
        The created or updated SimulationSnapshot instance.
    """
    data: dict = {}
    data.update(_collect_population(simulation))
    data.update(_collect_economy(simulation))
    data.update(_collect_social(simulation))
    data.update(_collect_government(simulation))
    data.update(_collect_class_distribution(simulation))

    snapshot, created = SimulationSnapshot.objects.update_or_create(
        simulation=simulation,
        tick=tick,
        defaults=data,
    )

    logger.debug(
        "capture_snapshot: simulation=%d tick=%d created=%s alive=%d gini=%.4f",
        simulation.pk, tick, created,
        data["population_alive"], data["gini_coefficient"],
    )
    return snapshot


def capture_and_detect(simulation, tick: int) -> None:
    """Capture snapshot and detect crises in one call.

    The crisis detection step is optional: if the crisis module has not yet
    been implemented it is silently skipped so that this function remains safe
    to call from the tick engine at any stage of the feature rollout.
    """
    snapshot = capture_snapshot(simulation, tick)
    try:
        from .crisis import detect_crises
        detect_crises(simulation, snapshot)
    except ImportError:
        pass  # crisis module not yet implemented

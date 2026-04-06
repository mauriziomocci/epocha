# Analytics / Psychohistoriographic Dashboard -- Design Spec

## Goal

Add a dedicated analytics page that visualizes the simulation's historical trends as interactive time series charts, detects Epochal Crises from composite indicator thresholds, and provides a snapshot-based data pipeline to feed the charts. The dashboard transforms raw simulation data into actionable insight about the civilization's trajectory.

## Architecture

Three components: a snapshot capture system (writes one DB record per tick with all KPIs), an Epochal Crisis detector (evaluates composite threshold conditions), and an analytics page (Lightweight-charts for time series, Chart.js for composition charts, both CDN). A JSON data endpoint serves the chart data.

## SimulationSnapshot Model

New model in `epocha/apps/simulation/models.py`. One record per tick capturing all key performance indicators:

```python
class SimulationSnapshot(models.Model):
    """Per-tick snapshot of simulation KPIs for analytics charts."""

    simulation = models.ForeignKey(Simulation, on_delete=models.CASCADE, related_name="snapshots")
    tick = models.PositiveIntegerField()

    # Population
    population_alive = models.PositiveIntegerField(default=0)
    population_dead = models.PositiveIntegerField(default=0)

    # Economy
    avg_wealth = models.FloatField(default=0.0)
    gini_coefficient = models.FloatField(default=0.0)

    # Social
    avg_mood = models.FloatField(default=0.0)
    faction_count = models.PositiveIntegerField(default=0)

    # Political (from Government model)
    government_type = models.CharField(max_length=30, blank=True)
    government_stability = models.FloatField(default=0.0)
    institutional_trust = models.FloatField(default=0.0)
    repression_level = models.FloatField(default=0.0)
    corruption = models.FloatField(default=0.0)
    popular_legitimacy = models.FloatField(default=0.0)
    military_loyalty = models.FloatField(default=0.0)

    # Class distribution (percentages, 0.0-1.0)
    class_elite_pct = models.FloatField(default=0.0)
    class_wealthy_pct = models.FloatField(default=0.0)
    class_middle_pct = models.FloatField(default=0.0)
    class_working_pct = models.FloatField(default=0.0)
    class_poor_pct = models.FloatField(default=0.0)

    class Meta:
        unique_together = ["simulation", "tick"]
        ordering = ["tick"]
```

## Snapshot Capture

A function `capture_snapshot(simulation, tick)` in `epocha/apps/simulation/snapshot.py` collects all KPIs from the current simulation state and creates a SimulationSnapshot record.

Data sources:
- Population: `Agent.objects.filter(simulation=sim).aggregate(alive=Count(is_alive=True), dead=Count(is_alive=False))`
- Economy: average wealth from Agent queryset, Gini from `compute_gini()` (already implemented in `epocha/apps/world/stratification.py`)
- Social: average mood from Agent queryset, faction count from Group queryset
- Political: read directly from Government model fields
- Class distribution: count agents per social_class, divide by total

Called at the end of every tick, after memory decay and before advance tick. One INSERT per tick -- negligible cost.

## Epochal Crisis Detection

A module `epocha/apps/simulation/crisis.py` with data-driven crisis definitions and a detector function.

### Crisis Definitions

```python
CRISIS_DEFINITIONS = {
    "inequality_crisis": {
        "label": "Inequality Crisis",
        "description": "Extreme wealth gap threatening social stability",
        "conditions": {"gini_above": 0.6, "government_stability_below": 0.4},
        "severity": "high",
    },
    "coup_risk": {
        "label": "Coup Risk",
        "description": "Military disloyal and opposition factions are strong",
        "conditions": {"military_loyalty_below": 0.3, "max_faction_cohesion_above": 0.7},
        "severity": "critical",
    },
    "institutional_collapse": {
        "label": "Institutional Collapse",
        "description": "Trust eroded and corruption systemic",
        "conditions": {"institutional_trust_below": 0.2, "corruption_above": 0.6},
        "severity": "high",
    },
    "revolution_risk": {
        "label": "Revolution Risk",
        "description": "Population has lost faith in the government",
        "conditions": {"popular_legitimacy_below": 0.2, "gini_above": 0.5},
        "severity": "critical",
    },
    "social_despair": {
        "label": "Social Despair",
        "description": "Collective mood has collapsed",
        "conditions": {"avg_mood_below": 0.25, "government_stability_below": 0.3},
        "severity": "medium",
    },
}
```

Adding a new crisis type is adding a dictionary entry.

### Detector

`detect_crises(simulation, snapshot) -> list[dict]` checks each definition against the snapshot values. For conditions like `max_faction_cohesion_above`, it queries the DB directly (max cohesion of active factions). Returns a list of active crisis dicts with label, severity, conditions met.

When a crisis is detected:
1. An Event is created in the DB (for the event timeline and history)
2. A "public" memory is broadcast to all agents (so crises influence agent decisions)
3. The crisis appears as a marker on the analytics charts
4. A banner shows on the analytics page

Crises are checked every tick as part of the snapshot capture phase. A cooldown prevents the same crisis from firing multiple ticks in a row (configurable, default 10 ticks).

## Analytics Data Endpoint

**URL:** `/dashboard/simulation/<id>/analytics/data/` (JSON, login required)

**Response:**

```json
{
  "snapshots": [
    {
      "tick": 1,
      "gini_coefficient": 0.35,
      "government_stability": 0.6,
      "avg_mood": 0.5,
      "avg_wealth": 55.0,
      "population_alive": 20,
      "population_dead": 0,
      "faction_count": 2,
      "government_type": "democracy",
      "institutional_trust": 0.5,
      "repression_level": 0.1,
      "corruption": 0.2,
      "popular_legitimacy": 0.5,
      "military_loyalty": 0.5,
      "class_elite_pct": 0.05,
      "class_wealthy_pct": 0.1,
      "class_middle_pct": 0.35,
      "class_working_pct": 0.3,
      "class_poor_pct": 0.2
    }
  ],
  "crises": [
    {"tick": 15, "type": "inequality_crisis", "label": "Inequality Crisis", "severity": "high"}
  ],
  "transitions": [
    {"tick": 20, "from_type": "democracy", "to_type": "illiberal_democracy", "cause": "transition"}
  ],
  "factions": [
    {"name": "The Guild", "color": "#6366f1", "member_count": 5, "cohesion": 0.7}
  ]
}
```

- `snapshots`: all SimulationSnapshot records for this simulation, ordered by tick
- `crises`: Events with type containing "crisis" (from Event model)
- `transitions`: GovernmentHistory records
- `factions`: current active factions with colors (reusing `_faction_color` from graph views)

## Charts

### Lightweight-charts (time series)

| Chart | Data fields | Type | Notes |
|-------|------------|------|-------|
| Government Stability | government_stability | Line | Color changes with government_type. Markers for transitions. |
| Inequality (Gini) | gini_coefficient | Line | Red threshold line at 0.6. Markers for crises. |
| Collective Mood | avg_mood | Line | |
| Political Indicators | institutional_trust, corruption, popular_legitimacy, repression_level, military_loyalty | Multi-line (5 series) | Legend with toggle |
| Population | population_alive, population_dead | Stacked area | |

All charts share the same tick-based x-axis and support markers for Epochal Crises (red triangles) and government transitions (blue diamonds).

### Chart.js (composition)

| Chart | Data | Type | Notes |
|-------|------|------|-------|
| Social Classes | class_*_pct at current tick | Doughnut | Elite=gold, wealthy=indigo, middle=blue, working=gray, poor=red |
| Class Evolution | class_*_pct over time | Stacked area | Shows how class composition shifts |
| Faction Strengths | cohesion * member_count | Horizontal bar | Colored by faction |

## Page Layout

```
Header: simulation name + "Back to simulation" + "Refresh"

Epochal Crisis Banner (full width, conditionally shown)
  - Red/amber gradient background
  - Crisis name, description, severity badge
  - "Active since tick N"

Row 1: [Stability chart (55%)] [Gini chart (45%)]
Row 2: [Political indicators (55%)] [Social classes doughnut (45%)]
Row 3: [Collective mood (55%)] [Population (45%)]
Row 4: [Class evolution (100%)]

Event Timeline (bottom, scrollable)
  - Significant events: crises, transitions, faction formation/dissolution
  - Each event: tick number, icon by type, description
```

## Integration into Tick Engine

```
1. Economy
2. Agent decisions
3. Information flow
4. Faction dynamics
5. Political cycle
6. Memory decay
7. >>> Capture snapshot + detect crises <<<
8. Advance tick
9. Broadcast
```

`capture_snapshot()` and `detect_crises()` run together. In the synchronous engine (SimulationEngine.run_tick), after memory decay and before advance tick. Same in the Celery finalize_tick path.

## Mobile

Below 768px: charts stack vertically in single column. Lightweight-charts and Chart.js are both responsive. The doughnut chart collapses to a smaller size. The crisis banner stays full width.

## Files

**New files:**

| File | Responsibility |
|------|---------------|
| `epocha/apps/simulation/snapshot.py` | capture_snapshot() |
| `epocha/apps/simulation/crisis.py` | CRISIS_DEFINITIONS + detect_crises() |
| `epocha/apps/simulation/tests/test_snapshot.py` | Snapshot tests |
| `epocha/apps/simulation/tests/test_crisis.py` | Crisis detection tests |
| `epocha/apps/dashboard/templates/dashboard/simulation_analytics.html` | Analytics page template |

**Modified files:**

| File | Change |
|------|--------|
| `epocha/apps/simulation/models.py` | SimulationSnapshot model |
| `epocha/apps/simulation/engine.py` | snapshot + crisis capture call |
| `epocha/apps/simulation/tasks.py` | Same in Celery path |
| `epocha/apps/dashboard/views.py` | analytics_view + analytics_data_view |
| `epocha/apps/dashboard/urls.py` | 2 new routes |
| `epocha/apps/dashboard/templates/dashboard/simulation_detail.html` | "Analytics" button |

## What This Does NOT Cover (deferred, see memory)

- Branch comparison (requires branching system, phase 3)
- Automatic pattern detection across simulations
- Temporal zoom (days/months/years/decades/centuries)
- Data export (CSV/JSON/image)

These are documented in memory for future implementation.

## Performance

- SimulationSnapshot: 1 INSERT per tick, ~20 float fields = negligible
- Analytics data endpoint: single query on SimulationSnapshot (indexed by simulation + tick), plus small queries for crises, transitions, factions
- Crisis detection: 5 threshold checks against snapshot fields = trivial
- Charts: Lightweight-charts handles thousands of data points with WebGL. Chart.js handles hundreds easily.

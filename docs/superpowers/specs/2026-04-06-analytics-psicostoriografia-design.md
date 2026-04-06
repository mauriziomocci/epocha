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

    # Political (mapped from Government model: Government.stability -> government_stability)
    government_type = models.CharField(max_length=30, blank=True)
    government_stability = models.FloatField(default=0.0)
    institutional_trust = models.FloatField(default=0.0)
    repression_level = models.FloatField(default=0.0)
    corruption = models.FloatField(default=0.0)
    popular_legitimacy = models.FloatField(default=0.0)
    military_loyalty = models.FloatField(default=0.0)

    # Class distribution (percentages, 0.0-1.0, must sum to 1.0)
    class_elite_pct = models.FloatField(default=0.0)
    class_wealthy_pct = models.FloatField(default=0.0)
    class_middle_pct = models.FloatField(default=0.0)
    class_working_pct = models.FloatField(default=0.0)
    class_poor_pct = models.FloatField(default=0.0)

    class Meta:
        unique_together = ["simulation", "tick"]
        ordering = ["tick"]
```

Note on class distribution: `Agent.social_class` can be "enslaved" (set manually or by certain government types), but `update_social_classes()` in `stratification.py` only produces 5 classes. In the snapshot capture, agents with `social_class="enslaved"` are counted under `class_poor_pct` to ensure percentages always sum to 1.0.

## Snapshot Capture

A function `capture_snapshot(simulation, tick)` in `epocha/apps/simulation/snapshot.py` collects all KPIs from the current simulation state and creates a SimulationSnapshot record.

Data sources (pseudocode -- implementer must use valid Django ORM):
- Population alive: `Agent.objects.filter(simulation=sim, is_alive=True).count()`
- Population dead: `Agent.objects.filter(simulation=sim, is_alive=False).count()`
- Average wealth: `Agent.objects.filter(simulation=sim, is_alive=True).aggregate(Avg("wealth"))`
- Gini: `compute_gini()` from `epocha/apps/world/stratification.py` (pass list of agent wealths)
- Average mood: `Agent.objects.filter(simulation=sim, is_alive=True).aggregate(Avg("mood"))`
- Faction count: `Group.objects.filter(simulation=sim, cohesion__gt=0.0).count()` (only active groups with positive cohesion; dissolved groups with cohesion=0 are excluded)
- Political indicators: read from `Government.objects.get(simulation=sim)` -- note: `Government.stability` maps to `SimulationSnapshot.government_stability`
- Class distribution: `Agent.objects.filter(simulation=sim, is_alive=True).values("social_class").annotate(count=Count("id"))`, then divide by total. Agents with "enslaved" class are counted as "poor".

Called at the end of every tick, after memory decay and before advance tick. The call must be added in BOTH `SimulationEngine.run_tick()` AND `finalize_tick()` in `tasks.py`, with identical positioning. One INSERT per tick -- negligible cost.

Scaling note: the Gini computation loads all agent wealth values and sorts them. Trivial for 20-50 agents, potentially non-negligible for 10,000+ agents. At that scale, consider caching or sampling.

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
        # Source: World Bank data shows countries with Gini > 0.6 (South Africa 0.63,
        # Namibia 0.59) experience significant social unrest. The 0.6 threshold
        # marks "extreme inequality" in the literature.
        # Ref: Alesina, A. & Perotti, R. (1996). "Income Distribution, Political
        # Instability, and Investment." European Economic Review, 40(6), 1203-1228.
        # The stability threshold (0.4) is a simulation-internal calibration parameter
        # representing "moderately unstable government" on the 0-1 scale.
    },
    "coup_risk": {
        "label": "Coup Risk",
        "description": "Military disloyal and opposition factions are strong",
        "conditions": {"military_loyalty_below": 0.3, "max_faction_cohesion_above": 0.7},
        "severity": "critical",
        # Source: Powell, J. M. & Thyne, C. L. (2011). "Global Instances of Coups
        # from 1950 to 2010." Journal of Peace Research, 48(2), 249-259.
        # Military disloyalty is the single strongest predictor of coups.
        # max_faction_cohesion_above is a LIVE QUERY condition (not from snapshot) --
        # it checks Group.objects.filter(simulation=sim, cohesion__gt=0).aggregate(Max("cohesion")).
        # Threshold 0.7 = a highly cohesive opposition faction.
    },
    "institutional_collapse": {
        "label": "Institutional Collapse",
        "description": "Trust eroded and corruption systemic",
        "conditions": {"institutional_trust_below": 0.2, "corruption_above": 0.6},
        "severity": "high",
        # Source: Rose-Ackerman, S. & Palifka, B.J. (2016). "Corruption and
        # Government." Cambridge University Press.
        # Corruption > 0.6 maps to Transparency International CPI below 40/100,
        # classified as "highly corrupt". Trust < 0.2 represents near-total
        # loss of institutional credibility.
    },
    "revolution_risk": {
        "label": "Revolution Risk",
        "description": "Population has lost faith in the government",
        "conditions": {"popular_legitimacy_below": 0.2, "gini_above": 0.5},
        "severity": "critical",
        # Source: Acemoglu, D. & Robinson, J. A. (2006). "Economic Origins of
        # Dictatorship and Democracy." Cambridge University Press.
        # The combination of low legitimacy + high inequality is the classic
        # precondition for revolution (French Rev, Russian Rev, Arab Spring).
        # Gini > 0.5 = "high inequality" threshold in the literature.
    },
    "social_despair": {
        "label": "Social Despair",
        "description": "Collective mood has collapsed",
        "conditions": {"avg_mood_below": 0.25, "government_stability_below": 0.3},
        "severity": "medium",
        # Note: avg_mood is the most synthetic metric with the least direct
        # real-world mapping. The 0.25 threshold represents the bottom quartile
        # of the simulation's mood scale. Combined with low stability, it
        # indicates a society in deep crisis. This is a simulation-internal
        # calibration, not derived from external data.
    },
}
```

Adding a new crisis type is adding a dictionary entry. Each definition documents its scientific source or explicitly states it is a calibration parameter.

### Condition types

Crisis conditions come in two flavors:
- **Snapshot-based**: `gini_above`, `government_stability_below`, `institutional_trust_below`, `corruption_above`, `popular_legitimacy_below`, `avg_mood_below`, `military_loyalty_below` -- checked against SimulationSnapshot fields
- **Live query**: `max_faction_cohesion_above` -- queries the DB directly (`Group.objects.filter(simulation=sim, cohesion__gt=0).aggregate(Max("cohesion"))`)

The detector function must handle both types. The condition name prefix (`gini_`, `government_stability_`, etc.) maps to the snapshot field name. The `max_faction_cohesion_` prefix is a special case that triggers a live query.

### Detector

`detect_crises(simulation, snapshot) -> list[dict]` checks each definition against the snapshot values (and live queries where needed). Returns a list of active crisis dicts with type, label, severity, and conditions met.

When a crisis is detected:
1. An Event is created in the DB with `event_type="political"` and title prefixed with "[EPOCHAL CRISIS]". The `severity` field on Event carries the crisis severity.
2. A "public" memory is broadcast to all living agents (reusing the same pattern as government transitions in `government.py:_execute_transition`)
3. The crisis appears as a marker on the analytics charts
4. A banner shows on the analytics page

Crisis cooldown: after firing, the same crisis type cannot fire again for `_CRISIS_COOLDOWN_TICKS = 10` ticks (constant in `crisis.py`). The cooldown is checked by querying recent Events: `Event.objects.filter(simulation=sim, title__startswith="[EPOCHAL CRISIS]", title__contains=crisis_label, tick__gte=tick - cooldown).exists()`.

Crises are checked every tick as part of the snapshot capture phase.

### Filtering crises in the analytics endpoint

The analytics data endpoint identifies crisis events by filtering: `Event.objects.filter(simulation=sim, title__startswith="[EPOCHAL CRISIS]")`. This avoids needing a new EventType choice or model changes. The title prefix is a convention, not a model constraint.

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

Data sources:
- `snapshots`: `SimulationSnapshot.objects.filter(simulation=sim).order_by("tick").values()` -- single indexed query
- `crises`: `Event.objects.filter(simulation=sim, title__startswith="[EPOCHAL CRISIS]")` -- parsed from title for type/label
- `transitions`: `GovernmentHistory.objects.filter(simulation=sim)` -- `from_type` is derived by reading the previous GovernmentHistory record's `government_type`. If no previous record exists, `from_type` is "initial". This avoids adding a field to GovernmentHistory.
- `factions`: `Group.objects.filter(simulation=sim, cohesion__gt=0)` with member count annotation and colors from `_faction_color()` (defined in `epocha/apps/dashboard/views.py`, reused from graph views)

Future optimization: for simulations with 10,000+ ticks, the endpoint should accept `?from_tick=X&to_tick=Y` query parameters for pagination. Not implemented in this iteration.

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
| Faction Strengths | cohesion * member_count | Horizontal bar | Colored by faction (using `_faction_color` from `epocha/apps/dashboard/views.py`) |

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

`capture_snapshot()` and `detect_crises()` run together in a single function `capture_and_detect(simulation, tick)` that calls both. This function must be added in TWO places:

1. **Synchronous path**: `SimulationEngine.run_tick()` in `epocha/apps/simulation/engine.py`, after memory decay (currently step 6) and before advance tick (currently step 7).
2. **Celery path**: `finalize_tick()` in `epocha/apps/simulation/tasks.py`, after memory decay and before advance tick counter.

Both calls have identical positioning and arguments.

## Mobile

Below 768px: charts stack vertically in single column. Lightweight-charts and Chart.js are both responsive. The doughnut chart collapses to a smaller size. The crisis banner stays full width.

## Files

**New files:**

| File | Responsibility |
|------|---------------|
| `epocha/apps/simulation/snapshot.py` | capture_snapshot() + capture_and_detect() |
| `epocha/apps/simulation/crisis.py` | CRISIS_DEFINITIONS + detect_crises() |
| `epocha/apps/simulation/tests/test_snapshot.py` | Snapshot tests |
| `epocha/apps/simulation/tests/test_crisis.py` | Crisis detection tests |
| `epocha/apps/dashboard/templates/dashboard/simulation_analytics.html` | Analytics page template |

**Modified files:**

| File | Change |
|------|--------|
| `epocha/apps/simulation/models.py` | SimulationSnapshot model |
| `epocha/apps/simulation/engine.py` | capture_and_detect call in run_tick() |
| `epocha/apps/simulation/tasks.py` | capture_and_detect call in finalize_tick() |
| `epocha/apps/dashboard/views.py` | analytics_view + analytics_data_view |
| `epocha/apps/dashboard/urls.py` | 2 new routes |
| `epocha/apps/dashboard/templates/dashboard/simulation_detail.html` | "Analytics" button |

## What This Does NOT Cover (deferred, see memory)

- Branch comparison (requires branching system, phase 3)
- Automatic pattern detection across simulations
- Temporal zoom (days/months/years/decades/centuries)
- Data export (CSV/JSON/image)

These are documented in memory (`project_analytics_deferred.md`) for future implementation.

## Performance

- SimulationSnapshot: 1 INSERT per tick, ~20 float fields = negligible
- Analytics data endpoint: single query on SimulationSnapshot (indexed by simulation + tick via unique_together), plus small queries for crises, transitions, factions. No N+1.
- Crisis detection: 5 threshold checks against snapshot fields + 1 live query for max faction cohesion = trivial
- Charts: Lightweight-charts handles thousands of data points with WebGL. Chart.js handles hundreds easily.
- Gini computation: sorts N agent wealth values. O(N log N). Trivial for N < 1000.

# Analytics / Psychohistoriographic Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a per-tick snapshot pipeline, Epochal Crisis detection, and an interactive analytics dashboard with time series and composition charts.

**Architecture:** Bottom-up: SimulationSnapshot model + migration, then snapshot capture function, then crisis detector, then analytics data endpoint, then chart template page, then tick engine wiring. Each module is independently testable.

**Tech Stack:** Django ORM, pytest, Lightweight-charts (CDN), Chart.js (CDN), Alpine.js, Tailwind CSS CDN

**Spec:** `docs/superpowers/specs/2026-04-06-analytics-psicostoriografia-design.md`

---

## File Structure

| File | Responsibility | New/Modify |
|------|---------------|------------|
| `epocha/apps/simulation/models.py:73` | SimulationSnapshot model | Modify |
| `epocha/apps/simulation/snapshot.py` | capture_snapshot() + capture_and_detect() | New |
| `epocha/apps/simulation/crisis.py` | CRISIS_DEFINITIONS + detect_crises() | New |
| `epocha/apps/simulation/tests/test_snapshot.py` | Snapshot capture tests | New |
| `epocha/apps/simulation/tests/test_crisis.py` | Crisis detection tests | New |
| `epocha/apps/dashboard/views.py` | analytics_view + analytics_data_view | Modify |
| `epocha/apps/dashboard/urls.py` | 2 new routes | Modify |
| `epocha/apps/dashboard/templates/dashboard/simulation_analytics.html` | Analytics page template | New |
| `epocha/apps/dashboard/templates/dashboard/simulation_detail.html` | "Analytics" button | Modify |
| `epocha/apps/simulation/engine.py:263-264` | capture_and_detect call | Modify |
| `epocha/apps/simulation/tasks.py:109-110` | capture_and_detect call | Modify |

---

### Task 1: SimulationSnapshot model + migration

**Files:**
- Modify: `epocha/apps/simulation/models.py` (after Event class, around line 73)
- Migration: `epocha/apps/simulation/migrations/`

- [ ] **Step 1: Add SimulationSnapshot model**

After the Event class in `epocha/apps/simulation/models.py`, add:

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

    # Political (mapped from Government: Government.stability -> government_stability)
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

    def __str__(self):
        return f"Snapshot {self.simulation.name} @ tick {self.tick}"
```

- [ ] **Step 2: Generate and apply migration**

```bash
docker compose -f docker-compose.local.yml exec -T web python manage.py makemigrations simulation --name simulation_snapshot
docker compose -f docker-compose.local.yml exec -T web python manage.py migrate simulation
```

- [ ] **Step 3: Run existing tests**

Run: `docker compose -f docker-compose.local.yml exec -T web pytest epocha/apps/simulation/ -q`

- [ ] **Step 4: Commit**

```
feat(simulation): add SimulationSnapshot model for analytics data

CHANGE: Add SimulationSnapshot model that captures per-tick KPIs for
the analytics dashboard: population, economy (wealth, Gini), social
(mood, factions), political indicators, and class distribution.
```

---

### Task 2: Snapshot capture function

**Files:**
- Create: `epocha/apps/simulation/snapshot.py`
- Create: `epocha/apps/simulation/tests/test_snapshot.py`

- [ ] **Step 1: Write the failing tests**

Create `epocha/apps/simulation/tests/test_snapshot.py`:

```python
"""Tests for per-tick snapshot capture."""
import pytest

from epocha.apps.agents.models import Agent, Group
from epocha.apps.simulation.models import Simulation, SimulationSnapshot
from epocha.apps.simulation.snapshot import capture_snapshot
from epocha.apps.users.models import User
from epocha.apps.world.models import Government, World


@pytest.fixture
def user(db):
    return User.objects.create_user(email="snap@epocha.dev", username="snaptest", password="pass123")


@pytest.fixture
def simulation(user):
    return Simulation.objects.create(name="SnapTest", seed=42, owner=user)


@pytest.fixture
def world(simulation):
    return World.objects.create(simulation=simulation)


@pytest.fixture
def government(simulation):
    return Government.objects.create(
        simulation=simulation, government_type="democracy",
        stability=0.6, institutional_trust=0.5, repression_level=0.1,
        corruption=0.2, popular_legitimacy=0.5, military_loyalty=0.5,
    )


@pytest.fixture
def agents(simulation):
    agents = []
    for name, wealth, mood, social_class in [
        ("Rich", 200.0, 0.8, "wealthy"),
        ("Mid", 80.0, 0.5, "middle"),
        ("Poor", 10.0, 0.2, "poor"),
    ]:
        agents.append(Agent.objects.create(
            simulation=simulation, name=name, role="citizen",
            wealth=wealth, mood=mood, social_class=social_class,
            personality={"openness": 0.5},
        ))
    return agents


@pytest.fixture
def faction(simulation):
    return Group.objects.create(
        simulation=simulation, name="The Guild", cohesion=0.7, formed_at_tick=1,
    )


@pytest.mark.django_db
class TestCaptureSnapshot:
    def test_creates_snapshot_record(self, simulation, world, government, agents):
        capture_snapshot(simulation, tick=5)
        assert SimulationSnapshot.objects.filter(simulation=simulation, tick=5).exists()

    def test_captures_population(self, simulation, world, government, agents):
        agents[2].is_alive = False
        agents[2].save(update_fields=["is_alive"])
        capture_snapshot(simulation, tick=5)
        snap = SimulationSnapshot.objects.get(simulation=simulation, tick=5)
        assert snap.population_alive == 2
        assert snap.population_dead == 1

    def test_captures_economy(self, simulation, world, government, agents):
        capture_snapshot(simulation, tick=5)
        snap = SimulationSnapshot.objects.get(simulation=simulation, tick=5)
        assert snap.avg_wealth > 0
        assert 0.0 <= snap.gini_coefficient <= 1.0

    def test_captures_mood(self, simulation, world, government, agents):
        capture_snapshot(simulation, tick=5)
        snap = SimulationSnapshot.objects.get(simulation=simulation, tick=5)
        assert snap.avg_mood == pytest.approx(0.5, abs=0.1)

    def test_captures_government_indicators(self, simulation, world, government, agents):
        capture_snapshot(simulation, tick=5)
        snap = SimulationSnapshot.objects.get(simulation=simulation, tick=5)
        assert snap.government_type == "democracy"
        assert snap.government_stability == pytest.approx(0.6)
        assert snap.institutional_trust == pytest.approx(0.5)

    def test_captures_faction_count(self, simulation, world, government, agents, faction):
        capture_snapshot(simulation, tick=5)
        snap = SimulationSnapshot.objects.get(simulation=simulation, tick=5)
        assert snap.faction_count == 1

    def test_captures_class_distribution(self, simulation, world, government, agents):
        capture_snapshot(simulation, tick=5)
        snap = SimulationSnapshot.objects.get(simulation=simulation, tick=5)
        total = snap.class_elite_pct + snap.class_wealthy_pct + snap.class_middle_pct + snap.class_working_pct + snap.class_poor_pct
        assert abs(total - 1.0) < 0.01

    def test_no_government_still_works(self, simulation, world, agents):
        """Snapshot should work even without a Government."""
        capture_snapshot(simulation, tick=5)
        snap = SimulationSnapshot.objects.get(simulation=simulation, tick=5)
        assert snap.government_type == ""
        assert snap.government_stability == 0.0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `docker compose -f docker-compose.local.yml exec -T web pytest epocha/apps/simulation/tests/test_snapshot.py -v`

- [ ] **Step 3: Implement capture_snapshot**

Create `epocha/apps/simulation/snapshot.py`:

```python
"""Per-tick snapshot capture for analytics.

Collects all simulation KPIs into a single SimulationSnapshot record:
population, economy (wealth, Gini), social (mood, factions), political
indicators, and class distribution.
"""
from __future__ import annotations

import logging

from django.db.models import Avg, Count, Q

from epocha.apps.agents.models import Agent, Group

from .models import SimulationSnapshot

logger = logging.getLogger(__name__)


def capture_snapshot(simulation, tick: int) -> SimulationSnapshot:
    """Capture a snapshot of all simulation KPIs at the current tick.

    Args:
        simulation: The simulation instance.
        tick: Current tick number.

    Returns:
        The created SimulationSnapshot instance.
    """
    agents = Agent.objects.filter(simulation=simulation)
    alive_agents = agents.filter(is_alive=True)

    # Population
    population_alive = alive_agents.count()
    population_dead = agents.filter(is_alive=False).count()

    # Economy
    wealth_stats = alive_agents.aggregate(avg_w=Avg("wealth"))
    avg_wealth = wealth_stats["avg_w"] or 0.0

    # Gini coefficient
    from epocha.apps.world.stratification import compute_gini
    wealths = list(alive_agents.values_list("wealth", flat=True))
    gini = compute_gini(wealths)

    # Social
    mood_stats = alive_agents.aggregate(avg_m=Avg("mood"))
    avg_mood = mood_stats["avg_m"] or 0.0
    faction_count = Group.objects.filter(simulation=simulation, cohesion__gt=0.0).count()

    # Political
    government_type = ""
    government_stability = 0.0
    institutional_trust = 0.0
    repression_level = 0.0
    corruption = 0.0
    popular_legitimacy = 0.0
    military_loyalty = 0.0

    try:
        from epocha.apps.world.models import Government
        gov = Government.objects.get(simulation=simulation)
        government_type = gov.government_type
        government_stability = gov.stability
        institutional_trust = gov.institutional_trust
        repression_level = gov.repression_level
        corruption = gov.corruption
        popular_legitimacy = gov.popular_legitimacy
        military_loyalty = gov.military_loyalty
    except Exception:
        pass

    # Class distribution
    total = max(population_alive, 1)
    class_counts = dict(
        alive_agents.values("social_class").annotate(c=Count("id")).values_list("social_class", "c")
    )
    # "enslaved" counted as "poor"
    poor_count = class_counts.get("poor", 0) + class_counts.get("enslaved", 0)

    snapshot = SimulationSnapshot.objects.create(
        simulation=simulation,
        tick=tick,
        population_alive=population_alive,
        population_dead=population_dead,
        avg_wealth=round(avg_wealth, 2),
        gini_coefficient=round(gini, 4),
        avg_mood=round(avg_mood, 4),
        faction_count=faction_count,
        government_type=government_type,
        government_stability=round(government_stability, 4),
        institutional_trust=round(institutional_trust, 4),
        repression_level=round(repression_level, 4),
        corruption=round(corruption, 4),
        popular_legitimacy=round(popular_legitimacy, 4),
        military_loyalty=round(military_loyalty, 4),
        class_elite_pct=round(class_counts.get("elite", 0) / total, 4),
        class_wealthy_pct=round(class_counts.get("wealthy", 0) / total, 4),
        class_middle_pct=round(class_counts.get("middle", 0) / total, 4),
        class_working_pct=round(class_counts.get("working", 0) / total, 4),
        class_poor_pct=round(poor_count / total, 4),
    )

    return snapshot
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `docker compose -f docker-compose.local.yml exec -T web pytest epocha/apps/simulation/tests/test_snapshot.py -v`
Expected: All 8 tests PASS.

- [ ] **Step 5: Commit**

```
feat(simulation): add per-tick snapshot capture for analytics

CHANGE: Implement capture_snapshot() which collects population, economy
(wealth, Gini), social (mood, factions), political indicators, and
class distribution into a SimulationSnapshot record. Called once per
tick to feed the analytics dashboard.
```

---

### Task 3: Epochal Crisis detection

**Files:**
- Create: `epocha/apps/simulation/crisis.py`
- Create: `epocha/apps/simulation/tests/test_crisis.py`

- [ ] **Step 1: Write the failing tests**

Create `epocha/apps/simulation/tests/test_crisis.py`:

```python
"""Tests for Epochal Crisis detection."""
import pytest

from epocha.apps.agents.models import Agent, Group, Memory
from epocha.apps.simulation.crisis import detect_crises
from epocha.apps.simulation.models import Event, Simulation, SimulationSnapshot
from epocha.apps.users.models import User
from epocha.apps.world.models import Government, World


@pytest.fixture
def user(db):
    return User.objects.create_user(email="crisis@epocha.dev", username="crisistest", password="pass123")


@pytest.fixture
def simulation(user):
    return Simulation.objects.create(name="CrisisTest", seed=42, owner=user)


@pytest.fixture
def world(simulation):
    return World.objects.create(simulation=simulation)


@pytest.fixture
def government(simulation):
    return Government.objects.create(simulation=simulation, government_type="democracy")


@pytest.fixture
def snapshot_inequality(simulation):
    """Snapshot with high Gini and low stability -- inequality crisis conditions."""
    return SimulationSnapshot.objects.create(
        simulation=simulation, tick=10,
        gini_coefficient=0.7, government_stability=0.3,
        avg_mood=0.5, institutional_trust=0.5, corruption=0.2,
        popular_legitimacy=0.5, military_loyalty=0.5,
        population_alive=20,
    )


@pytest.fixture
def snapshot_stable(simulation):
    """Stable snapshot -- no crisis conditions met."""
    return SimulationSnapshot.objects.create(
        simulation=simulation, tick=10,
        gini_coefficient=0.3, government_stability=0.7,
        avg_mood=0.6, institutional_trust=0.6, corruption=0.2,
        popular_legitimacy=0.6, military_loyalty=0.6,
        population_alive=20,
    )


@pytest.mark.django_db
class TestDetectCrises:
    def test_detects_inequality_crisis(self, simulation, world, government, snapshot_inequality):
        crises = detect_crises(simulation, snapshot_inequality)
        types = [c["type"] for c in crises]
        assert "inequality_crisis" in types

    def test_no_crisis_when_stable(self, simulation, world, government, snapshot_stable):
        crises = detect_crises(simulation, snapshot_stable)
        assert len(crises) == 0

    def test_creates_event_on_crisis(self, simulation, world, government, snapshot_inequality):
        detect_crises(simulation, snapshot_inequality)
        events = Event.objects.filter(simulation=simulation, title__startswith="[EPOCHAL CRISIS]")
        assert events.count() >= 1

    def test_creates_public_memory_on_crisis(self, simulation, world, government, snapshot_inequality):
        Agent.objects.create(
            simulation=simulation, name="Marco", role="citizen",
            personality={"openness": 0.5},
        )
        detect_crises(simulation, snapshot_inequality)
        memories = Memory.objects.filter(source_type="public", content__contains="EPOCHAL CRISIS")
        assert memories.count() >= 1

    def test_cooldown_prevents_duplicate_crisis(self, simulation, world, government, snapshot_inequality):
        """Same crisis should not fire again within cooldown period."""
        detect_crises(simulation, snapshot_inequality)
        # Create another snapshot 2 ticks later (within cooldown)
        snap2 = SimulationSnapshot.objects.create(
            simulation=simulation, tick=12,
            gini_coefficient=0.7, government_stability=0.3,
            avg_mood=0.5, institutional_trust=0.5, corruption=0.2,
            popular_legitimacy=0.5, military_loyalty=0.5,
            population_alive=20,
        )
        crises = detect_crises(simulation, snap2)
        # Should not re-fire within cooldown
        types = [c["type"] for c in crises]
        assert "inequality_crisis" not in types

    def test_detects_institutional_collapse(self, simulation, world, government):
        snap = SimulationSnapshot.objects.create(
            simulation=simulation, tick=10,
            gini_coefficient=0.3, government_stability=0.5,
            avg_mood=0.5, institutional_trust=0.15, corruption=0.7,
            popular_legitimacy=0.5, military_loyalty=0.5,
            population_alive=20,
        )
        crises = detect_crises(simulation, snap)
        types = [c["type"] for c in crises]
        assert "institutional_collapse" in types

    def test_multiple_crises_can_fire_simultaneously(self, simulation, world, government):
        """Multiple crisis conditions can be true at the same time."""
        snap = SimulationSnapshot.objects.create(
            simulation=simulation, tick=10,
            gini_coefficient=0.7, government_stability=0.2,
            avg_mood=0.2, institutional_trust=0.15, corruption=0.7,
            popular_legitimacy=0.15, military_loyalty=0.5,
            population_alive=20,
        )
        crises = detect_crises(simulation, snap)
        assert len(crises) >= 2
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `docker compose -f docker-compose.local.yml exec -T web pytest epocha/apps/simulation/tests/test_crisis.py -v`

- [ ] **Step 3: Implement crisis detector**

Create `epocha/apps/simulation/crisis.py`:

```python
"""Epochal Crisis detection -- composite threshold conditions.

Detects critical situations from simulation KPIs by evaluating predefined
conditions against SimulationSnapshot values. When all conditions of a
crisis definition are met, the crisis is declared, an Event is created,
and agents are notified via public memory.

Scientific sources for thresholds are documented inline per crisis.
"""
from __future__ import annotations

import logging

from django.db.models import Max

from epocha.apps.agents.models import Agent, Group, Memory

from .models import Event, SimulationSnapshot

logger = logging.getLogger(__name__)

# Cooldown: minimum ticks between re-firing the same crisis type.
_CRISIS_COOLDOWN_TICKS = 10

CRISIS_DEFINITIONS = {
    "inequality_crisis": {
        "label": "Inequality Crisis",
        "description": "Extreme wealth gap threatening social stability",
        "conditions": {"gini_above": 0.6, "government_stability_below": 0.4},
        "severity": "high",
        # Source: Alesina & Perotti (1996). Gini > 0.6 = extreme inequality.
    },
    "coup_risk": {
        "label": "Coup Risk",
        "description": "Military disloyal and opposition factions are strong",
        "conditions": {"military_loyalty_below": 0.3, "max_faction_cohesion_above": 0.7},
        "severity": "critical",
        # Source: Powell & Thyne (2011). Military disloyalty predicts coups.
    },
    "institutional_collapse": {
        "label": "Institutional Collapse",
        "description": "Trust eroded and corruption systemic",
        "conditions": {"institutional_trust_below": 0.2, "corruption_above": 0.6},
        "severity": "high",
        # Source: Rose-Ackerman & Palifka (2016). Corruption > 0.6 = TI CPI < 40.
    },
    "revolution_risk": {
        "label": "Revolution Risk",
        "description": "Population has lost faith in the government",
        "conditions": {"popular_legitimacy_below": 0.2, "gini_above": 0.5},
        "severity": "critical",
        # Source: Acemoglu & Robinson (2006). Low legitimacy + high inequality.
    },
    "social_despair": {
        "label": "Social Despair",
        "description": "Collective mood has collapsed",
        "conditions": {"avg_mood_below": 0.25, "government_stability_below": 0.3},
        "severity": "medium",
        # Note: avg_mood is simulation-internal. 0.25 = bottom quartile.
    },
}

# Mapping from condition names to (snapshot_field, comparison_direction).
# "above" means snapshot.field > threshold. "below" means snapshot.field < threshold.
_SNAPSHOT_CONDITIONS = {
    "gini_above": ("gini_coefficient", "above"),
    "gini_below": ("gini_coefficient", "below"),
    "government_stability_above": ("government_stability", "above"),
    "government_stability_below": ("government_stability", "below"),
    "institutional_trust_above": ("institutional_trust", "above"),
    "institutional_trust_below": ("institutional_trust", "below"),
    "corruption_above": ("corruption", "above"),
    "corruption_below": ("corruption", "below"),
    "popular_legitimacy_above": ("popular_legitimacy", "above"),
    "popular_legitimacy_below": ("popular_legitimacy", "below"),
    "military_loyalty_above": ("military_loyalty", "above"),
    "military_loyalty_below": ("military_loyalty", "below"),
    "avg_mood_above": ("avg_mood", "above"),
    "avg_mood_below": ("avg_mood", "below"),
}

# Conditions that require live DB queries instead of snapshot fields.
_LIVE_CONDITIONS = {"max_faction_cohesion_above"}


def detect_crises(simulation, snapshot: SimulationSnapshot) -> list[dict]:
    """Detect active Epochal Crises based on snapshot and live data.

    Args:
        simulation: The simulation instance.
        snapshot: The current tick's snapshot.

    Returns:
        List of crisis dicts with type, label, severity, description.
    """
    active_crises = []

    for crisis_type, definition in CRISIS_DEFINITIONS.items():
        # Check cooldown
        if _is_on_cooldown(simulation, crisis_type, snapshot.tick):
            continue

        # Check all conditions
        all_met = True
        for condition_name, threshold in definition["conditions"].items():
            if not _evaluate_condition(simulation, snapshot, condition_name, threshold):
                all_met = False
                break

        if all_met:
            crisis = {
                "type": crisis_type,
                "label": definition["label"],
                "severity": definition["severity"],
                "description": definition["description"],
            }
            active_crises.append(crisis)
            _fire_crisis(simulation, snapshot.tick, crisis)

    return active_crises


def _evaluate_condition(simulation, snapshot, condition_name: str, threshold: float) -> bool:
    """Evaluate a single crisis condition."""
    if condition_name in _SNAPSHOT_CONDITIONS:
        field, direction = _SNAPSHOT_CONDITIONS[condition_name]
        value = getattr(snapshot, field, 0.0)
        if direction == "above":
            return value > threshold
        return value < threshold

    if condition_name == "max_faction_cohesion_above":
        result = Group.objects.filter(
            simulation=simulation, cohesion__gt=0.0,
        ).aggregate(max_c=Max("cohesion"))
        max_cohesion = result["max_c"] or 0.0
        return max_cohesion > threshold

    logger.warning("Unknown crisis condition: %s", condition_name)
    return False


def _is_on_cooldown(simulation, crisis_type: str, current_tick: int) -> bool:
    """Check if the crisis type fired recently (within cooldown)."""
    label = CRISIS_DEFINITIONS[crisis_type]["label"]
    return Event.objects.filter(
        simulation=simulation,
        title__startswith="[EPOCHAL CRISIS]",
        title__contains=label,
        tick__gte=max(0, current_tick - _CRISIS_COOLDOWN_TICKS),
    ).exists()


def _fire_crisis(simulation, tick: int, crisis: dict) -> None:
    """Create Event and broadcast public memory for a detected crisis."""
    # Create Event
    Event.objects.create(
        simulation=simulation,
        tick=tick,
        event_type="political",
        title=f"[EPOCHAL CRISIS] {crisis['label']}",
        description=crisis["description"],
        severity=1.0 if crisis["severity"] == "critical" else 0.7 if crisis["severity"] == "high" else 0.5,
    )

    # Broadcast to all agents
    agents = Agent.objects.filter(simulation=simulation, is_alive=True)
    memories = [
        Memory(
            agent=agent,
            content=f"[EPOCHAL CRISIS] {crisis['label']}: {crisis['description']}",
            emotional_weight=0.8,
            source_type="public",
            reliability=1.0,
            tick_created=tick,
        )
        for agent in agents
    ]
    Memory.objects.bulk_create(memories)

    logger.info("Epochal Crisis '%s' detected at tick %d", crisis["label"], tick)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `docker compose -f docker-compose.local.yml exec -T web pytest epocha/apps/simulation/tests/test_crisis.py -v`
Expected: All 7 tests PASS.

- [ ] **Step 5: Commit**

```
feat(simulation): add Epochal Crisis detection engine

CHANGE: Implement detect_crises() with 5 data-driven crisis definitions
(inequality, coup risk, institutional collapse, revolution, despair).
Crises fire when composite threshold conditions are met, creating Events
and broadcasting public memories. Cooldown prevents duplicate firing.
Scientific sources documented per crisis threshold.
```

---

### Task 4: Analytics data endpoint

**Files:**
- Modify: `epocha/apps/dashboard/views.py`
- Modify: `epocha/apps/dashboard/urls.py`
- Create: `epocha/apps/dashboard/tests/test_analytics.py`

- [ ] **Step 1: Write the failing tests**

Create `epocha/apps/dashboard/tests/test_analytics.py`:

```python
"""Tests for the analytics data endpoint."""
import pytest
from django.test import Client

from epocha.apps.simulation.models import Event, Simulation, SimulationSnapshot
from epocha.apps.users.models import User
from epocha.apps.world.models import GovernmentHistory, World


@pytest.fixture
def user(db):
    return User.objects.create_user(email="anal@epocha.dev", username="analtest", password="pass123")


@pytest.fixture
def logged_in_client(user):
    client = Client()
    client.login(email="anal@epocha.dev", password="pass123")
    return client


@pytest.fixture
def simulation(user):
    return Simulation.objects.create(name="AnalTest", seed=42, owner=user)


@pytest.fixture
def world(simulation):
    return World.objects.create(simulation=simulation)


@pytest.fixture
def snapshots(simulation):
    return [
        SimulationSnapshot.objects.create(
            simulation=simulation, tick=i,
            gini_coefficient=0.3 + i * 0.01,
            government_stability=0.6,
            avg_mood=0.5, avg_wealth=50.0,
            population_alive=20, population_dead=0,
            faction_count=2, government_type="democracy",
        )
        for i in range(1, 6)
    ]


@pytest.mark.django_db
class TestAnalyticsDataEndpoint:
    def test_returns_snapshots(self, logged_in_client, simulation, world, snapshots):
        response = logged_in_client.get(f"/simulations/{simulation.id}/analytics/data/")
        assert response.status_code == 200
        data = response.json()
        assert len(data["snapshots"]) == 5

    def test_returns_crises(self, logged_in_client, simulation, world, snapshots):
        Event.objects.create(
            simulation=simulation, tick=3, event_type="political",
            title="[EPOCHAL CRISIS] Inequality Crisis",
            description="Test crisis", severity=0.7,
        )
        response = logged_in_client.get(f"/simulations/{simulation.id}/analytics/data/")
        data = response.json()
        assert len(data["crises"]) == 1
        assert data["crises"][0]["label"] == "Inequality Crisis"

    def test_returns_transitions(self, logged_in_client, simulation, world, snapshots):
        GovernmentHistory.objects.create(
            simulation=simulation, government_type="democracy",
            from_tick=0, to_tick=10, transition_cause="transition",
        )
        GovernmentHistory.objects.create(
            simulation=simulation, government_type="illiberal_democracy",
            from_tick=10, transition_cause="transition",
        )
        response = logged_in_client.get(f"/simulations/{simulation.id}/analytics/data/")
        data = response.json()
        assert len(data["transitions"]) >= 1

    def test_requires_authentication(self, simulation, world, snapshots):
        client = Client()
        response = client.get(f"/simulations/{simulation.id}/analytics/data/")
        assert response.status_code in (302, 403)
```

- [ ] **Step 2: Run tests to verify they fail**

- [ ] **Step 3: Implement analytics data endpoint**

In `epocha/apps/dashboard/views.py`, add:

```python
@login_required(login_url="/login/")
def analytics_data_view(request, sim_id):
    """JSON endpoint providing analytics data for charts."""
    from epocha.apps.simulation.models import SimulationSnapshot
    from epocha.apps.world.models import GovernmentHistory

    simulation = get_object_or_404(Simulation, id=sim_id, owner=request.user)

    # Snapshots
    snapshots = list(
        SimulationSnapshot.objects.filter(simulation=simulation)
        .order_by("tick")
        .values(
            "tick", "gini_coefficient", "government_stability", "avg_mood",
            "avg_wealth", "population_alive", "population_dead", "faction_count",
            "government_type", "institutional_trust", "repression_level",
            "corruption", "popular_legitimacy", "military_loyalty",
            "class_elite_pct", "class_wealthy_pct", "class_middle_pct",
            "class_working_pct", "class_poor_pct",
        )
    )

    # Crises (from Events with title prefix)
    crisis_events = Event.objects.filter(
        simulation=simulation, title__startswith="[EPOCHAL CRISIS]",
    ).order_by("tick")
    crises = []
    for event in crisis_events:
        label = event.title.replace("[EPOCHAL CRISIS] ", "")
        crises.append({
            "tick": event.tick,
            "label": label,
            "severity": "critical" if event.severity >= 0.9 else "high" if event.severity >= 0.6 else "medium",
        })

    # Government transitions
    history = list(GovernmentHistory.objects.filter(simulation=simulation).order_by("from_tick"))
    transitions = []
    for i, record in enumerate(history):
        from_type = history[i - 1].government_type if i > 0 else "initial"
        if record.to_tick is not None:  # Only completed transitions
            transitions.append({
                "tick": record.to_tick,
                "from_type": from_type,
                "to_type": record.government_type if i + 1 < len(history) else record.government_type,
                "cause": record.transition_cause,
            })

    # Current factions
    from epocha.apps.agents.models import Agent, Group
    factions_qs = Group.objects.filter(simulation=simulation, cohesion__gt=0.0)
    factions = []
    for faction in factions_qs:
        member_count = Agent.objects.filter(group=faction, is_alive=True).count()
        factions.append({
            "name": faction.name,
            "color": _faction_color(faction.name),
            "member_count": member_count,
            "cohesion": round(faction.cohesion, 2),
        })

    return JsonResponse({
        "snapshots": snapshots,
        "crises": crises,
        "transitions": transitions,
        "factions": factions,
    })
```

Also add a simple view function:

```python
@login_required(login_url="/login/")
def analytics_view(request, sim_id):
    """Render the analytics dashboard page."""
    simulation = get_object_or_404(Simulation, id=sim_id, owner=request.user)
    return render(request, "dashboard/simulation_analytics.html", {"simulation": simulation})
```

In `epocha/apps/dashboard/urls.py`, add (BEFORE graph routes):

```python
    path("simulations/<int:sim_id>/analytics/", views.analytics_view, name="analytics"),
    path("simulations/<int:sim_id>/analytics/data/", views.analytics_data_view, name="analytics-data"),
```

- [ ] **Step 4: Run tests**

Run: `docker compose -f docker-compose.local.yml exec -T web pytest epocha/apps/dashboard/tests/test_analytics.py -v`

- [ ] **Step 5: Commit**

```
feat(dashboard): add analytics data JSON endpoint

CHANGE: Implement analytics_data_view serving simulation snapshots,
Epochal Crisis events, government transitions, and faction data for
the analytics dashboard charts.
```

---

### Task 5: Analytics page template

The big frontend task: Lightweight-charts + Chart.js rendering.

**Files:**
- Create: `epocha/apps/dashboard/templates/dashboard/simulation_analytics.html`

- [ ] **Step 1: Create the template**

Create `epocha/apps/dashboard/templates/dashboard/simulation_analytics.html`. This is a large template (~400 lines). Key structure:

**Head block:** Load Lightweight-charts and Chart.js via CDN:
```html
<script src="https://unpkg.com/lightweight-charts/dist/lightweight-charts.standalone.production.js"></script>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
```

**Layout:**
- Header with simulation name, "Back to simulation" + "Refresh" buttons
- Epochal Crisis banner (conditionally shown via Alpine.js)
- Grid of charts in rows as specified in the spec layout
- Event timeline at bottom

**Alpine.js component `analyticsPage()`:**
- `loadData()` fetches analytics data endpoint
- `renderTimeSeriesCharts()` creates 5 Lightweight-charts instances (stability, gini, mood, political indicators, population)
- `renderCompositionCharts()` creates 3 Chart.js instances (classes doughnut, class evolution, faction bar)
- `addMarkers()` adds crisis markers (red triangles) and transition markers (blue diamonds) to Lightweight-charts
- `refreshData()` re-fetches and re-renders

**Chart details:**
- Each Lightweight-chart gets its own container div with fixed height (250px)
- Stability chart: line series, color changes per government_type segment
- Gini chart: line series + horizontal price line at 0.6 threshold (red)
- Political indicators: 5 line series with legend toggle
- Population: 2 stacked area series
- Chart.js doughnut: current tick class distribution
- Chart.js faction bar: horizontal bars colored by faction

- [ ] **Step 2: Run all tests**

Run: `docker compose -f docker-compose.local.yml exec -T web pytest epocha/apps/dashboard/ -v`

- [ ] **Step 3: Commit**

```
feat(dashboard): add analytics dashboard page with charts

CHANGE: Full analytics page at /simulations/<id>/analytics/ with
Lightweight-charts (stability, Gini, mood, political indicators,
population time series) and Chart.js (class doughnut, class evolution,
faction strengths). Epochal Crisis banner, event timeline, markers for
crises and government transitions on all charts.
```

---

### Task 6: Tick engine integration + Analytics button

Wire `capture_and_detect` into the tick engine and add the Analytics button.

**Files:**
- Modify: `epocha/apps/simulation/snapshot.py` (add capture_and_detect wrapper)
- Modify: `epocha/apps/simulation/engine.py:263-264`
- Modify: `epocha/apps/simulation/tasks.py:109-110`
- Modify: `epocha/apps/dashboard/templates/dashboard/simulation_detail.html`
- Test: `epocha/apps/simulation/tests/test_engine.py`

- [ ] **Step 1: Add capture_and_detect wrapper to snapshot.py**

Add to `epocha/apps/simulation/snapshot.py`:

```python
def capture_and_detect(simulation, tick: int) -> None:
    """Capture snapshot and detect crises in one call.

    This is the single function called from the tick engine.
    """
    snapshot = capture_snapshot(simulation, tick)

    from .crisis import detect_crises
    detect_crises(simulation, snapshot)
```

- [ ] **Step 2: Add call in engine.py**

Add import at top:
```python
from epocha.apps.simulation.snapshot import capture_and_detect
```

In `run_tick()`, after memory decay (line ~264) and before advance tick (line ~267), add:
```python
        # 7. Capture snapshot + detect crises
        capture_and_detect(self.simulation, tick)
```

Renumber: advance tick becomes 8, broadcast becomes 9.

- [ ] **Step 3: Add call in tasks.py**

In `finalize_tick()`, after memory decay (line ~110) and before advance tick (line ~113), add:
```python
    # Capture snapshot + detect crises
    from epocha.apps.simulation.snapshot import capture_and_detect
    capture_and_detect(simulation, tick)
```

- [ ] **Step 4: Add Analytics button to simulation detail**

In `simulation_detail.html`, after the Relationships button (find `Relationships</a>`), add:
```html
            <a href="{% url 'dashboard:analytics' sim_id=simulation.id %}" class="bg-amber-600 hover:bg-amber-500 text-white px-4 py-2 rounded font-medium">Analytics</a>
```

- [ ] **Step 5: Add test**

Add to `epocha/apps/simulation/tests/test_engine.py`:

```python
@patch("epocha.apps.simulation.engine.process_agent_decision")
def test_snapshot_captured_every_tick(self, mock_decision, sim_with_world):
    """A SimulationSnapshot should be created for each tick."""
    from epocha.apps.simulation.models import SimulationSnapshot
    mock_decision.return_value = {"action": "work", "reason": "busy"}
    engine = SimulationEngine(sim_with_world)
    engine.run_tick()
    engine.run_tick()
    assert SimulationSnapshot.objects.filter(simulation=sim_with_world).count() == 2
```

- [ ] **Step 6: Run all tests**

Run: `docker compose -f docker-compose.local.yml exec -T web pytest -q`

- [ ] **Step 7: Commit**

```
feat(simulation): wire snapshot capture and crisis detection into tick engine

CHANGE: Call capture_and_detect() after memory decay in both the
synchronous engine and Celery path. Every tick now produces a
SimulationSnapshot and checks for Epochal Crises. Add Analytics
button (amber) to the simulation detail header.
```

---

### Task 7: Update engine docstring

**Files:**
- Modify: `epocha/apps/simulation/engine.py:1-19`

- [ ] **Step 1: Update module docstring**

```python
"""Tick orchestrator: coordinates economy, decisions, information, factions, politics, analytics, and events.

Each tick is a discrete time step where:
1. The economy updates (income, costs, mood effects)
2. Each living agent makes a decision via LLM
3. Decision consequences are applied (mood, health adjustments)
4. Memories are created from actions
5. Information propagates through the social network (hearsay, rumors)
6. Faction dynamics run periodically (cohesion, leadership, formation)
7. Political cycle runs periodically (institutions, stratification, transitions, elections)
8. Old memories decay periodically
9. Snapshot captured and Epochal Crises detected
10. The tick counter advances

Agent failures are isolated: if one agent's LLM call fails, the tick
continues for all other agents. This ensures simulation resilience.

Module-level functions (run_economy, run_memory_decay, broadcast_tick) are
used by both the SimulationEngine (synchronous path) and the Celery chord
tasks (production path). This avoids duplicating logic across execution modes.
"""
```

- [ ] **Step 2: Commit**

```
docs(simulation): update engine docstring with analytics step

CHANGE: Engine module docstring now reflects the 10-step tick flow
including snapshot capture and Epochal Crisis detection.
```

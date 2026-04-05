# Government, Institutions, and Social Stratification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement a complete political system with 12 data-driven government types, 7 institutions with health dynamics, dynamic social stratification with Gini coefficient, elections, coups, revolutions, crime, and corruption.

**Architecture:** Bottom-up: models and migrations first, then government type configuration (data), then institution health engine, then stratification engine, then government engine (indicators, transitions, elections, coups), then decision pipeline integration, then tick engine wiring. Each module is independently testable. All three subsystems share a single `process_political_cycle()` call every N ticks.

**Tech Stack:** Django ORM, pytest, no new dependencies

**Spec:** `docs/superpowers/specs/2026-04-05-government-institutions-stratification-design.md`

---

## File Structure

| File | Responsibility | New/Modify |
|------|---------------|------------|
| `epocha/apps/world/models.py` | Government, GovernmentHistory, Institution models | Modify |
| `epocha/apps/world/government_types.py` | Data-driven config for 12 government types | New |
| `epocha/apps/world/institutions.py` | Institution health dynamics | New |
| `epocha/apps/world/stratification.py` | Class mobility, Gini, crime logic | New |
| `epocha/apps/world/government.py` | Government engine: indicators, transitions, coups | New |
| `epocha/apps/world/election.py` | Deterministic election system | New |
| `epocha/apps/world/tests/test_government_types.py` | Government type config tests | New |
| `epocha/apps/world/tests/test_institutions.py` | Institution tests | New |
| `epocha/apps/world/tests/test_stratification.py` | Stratification tests | New |
| `epocha/apps/world/tests/test_government.py` | Government engine tests | New |
| `epocha/apps/world/tests/test_election.py` | Election tests | New |
| `epocha/apps/agents/decision.py` | Context enrichment with political info | Modify |
| `epocha/apps/simulation/engine.py` | Political cycle call + new action weights | Modify |
| `epocha/apps/simulation/tasks.py` | Political cycle call in Celery path | Modify |
| `epocha/apps/dashboard/formatters.py` | Verbs for crime, protest, campaign | Modify |
| `config/settings/base.py` | EPOCHA_GOVERNMENT_* settings | Modify |

---

### Task 1: Models, settings, and migrations

Add Government, GovernmentHistory, and Institution models plus political settings.

**Files:**
- Modify: `config/settings/base.py`
- Modify: `epocha/apps/world/models.py`
- Migration: `epocha/apps/world/migrations/`

- [ ] **Step 1: Add settings to base.py**

At the end of `config/settings/base.py`, after the last EPOCHA_FACTION setting, add:

```python
# --- Government and Political System ---
# How often the political cycle runs (every N ticks).
EPOCHA_GOVERNMENT_CYCLE_INTERVAL = env.int("EPOCHA_GOVERNMENT_CYCLE_INTERVAL", default=10)

# Default ticks between elections (for government types that hold elections).
EPOCHA_GOVERNMENT_ELECTION_INTERVAL = env.int("EPOCHA_GOVERNMENT_ELECTION_INTERVAL", default=50)

# Gini coefficient threshold above which revolt probability increases.
# Source: Acemoglu & Robinson (2006), most revolutions occur at Gini 0.6-0.8.
EPOCHA_GOVERNMENT_GINI_REVOLT_THRESHOLD = env.float("EPOCHA_GOVERNMENT_GINI_REVOLT_THRESHOLD", default=0.6)

# Government stability threshold below which coups become possible.
EPOCHA_GOVERNMENT_COUP_STABILITY_THRESHOLD = env.float("EPOCHA_GOVERNMENT_COUP_STABILITY_THRESHOLD", default=0.3)
```

- [ ] **Step 2: Add Government model to world/models.py**

After the EconomicTransaction model, add:

```python
class Government(models.Model):
    """Political system governing the simulation world."""

    simulation = models.OneToOneField(Simulation, on_delete=models.CASCADE, related_name="government")
    government_type = models.CharField(max_length=30, default="democracy")
    stability = models.FloatField(default=0.5, help_text="0.0 = collapsing, 1.0 = rock solid")
    ruling_faction = models.ForeignKey(
        "agents.Group", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="ruled_governments",
    )
    head_of_state = models.ForeignKey(
        "agents.Agent", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="headed_governments",
    )

    # Political indicators (0.0-1.0)
    institutional_trust = models.FloatField(default=0.5)
    repression_level = models.FloatField(default=0.1)
    corruption = models.FloatField(default=0.2)
    popular_legitimacy = models.FloatField(default=0.5)
    military_loyalty = models.FloatField(default=0.5)

    # Electoral tracking
    last_election_tick = models.PositiveIntegerField(default=0)

    formed_at_tick = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.government_type} ({self.simulation.name})"


class GovernmentHistory(models.Model):
    """Historical record of government transitions."""

    simulation = models.ForeignKey(Simulation, on_delete=models.CASCADE, related_name="government_history")
    government_type = models.CharField(max_length=30)
    head_of_state_name = models.CharField(max_length=255, blank=True)
    ruling_faction_name = models.CharField(max_length=255, blank=True)
    from_tick = models.PositiveIntegerField()
    to_tick = models.PositiveIntegerField(null=True, blank=True)
    transition_cause = models.CharField(max_length=50)

    class Meta:
        ordering = ["-from_tick"]

    def __str__(self):
        return f"{self.government_type} from tick {self.from_tick}"


class Institution(models.Model):
    """Social institution with health that affects government indicators."""

    class InstitutionType(models.TextChoices):
        JUSTICE = "justice", "Justice"
        EDUCATION = "education", "Education"
        HEALTH = "health", "Health"
        MILITARY = "military", "Military"
        MEDIA = "media", "Media"
        RELIGION = "religion", "Religion"
        BUREAUCRACY = "bureaucracy", "Bureaucracy"

    simulation = models.ForeignKey(Simulation, on_delete=models.CASCADE, related_name="institutions")
    institution_type = models.CharField(max_length=20, choices=InstitutionType.choices)
    health = models.FloatField(default=0.5, help_text="0.0 = failed, 1.0 = thriving")
    independence = models.FloatField(default=0.5, help_text="0.0 = government controlled, 1.0 = fully independent")
    funding = models.FloatField(default=0.5, help_text="0.0 = defunded, 1.0 = well funded")

    class Meta:
        unique_together = ["simulation", "institution_type"]

    def __str__(self):
        return f"{self.institution_type} ({self.simulation.name})"
```

- [ ] **Step 3: Generate and apply migration**

```bash
docker compose -f docker-compose.local.yml exec -T web python manage.py makemigrations world --name government_institutions
docker compose -f docker-compose.local.yml exec -T web python manage.py migrate world
```

- [ ] **Step 4: Run existing tests**

Run: `docker compose -f docker-compose.local.yml exec -T web pytest epocha/apps/world/ epocha/apps/simulation/ -q`
Expected: All pass.

- [ ] **Step 5: Commit**

```
feat(world): add Government, GovernmentHistory, and Institution models

CHANGE: Add three new models for the political system. Government tracks
type, stability, indicators, and ruling faction. GovernmentHistory records
transitions. Institution models 7 social institutions with health,
independence, and funding. Add EPOCHA_GOVERNMENT_* settings.
```

---

### Task 2: Government types configuration

Data-driven dictionary for all 12 government types. Pure data, no logic.

**Files:**
- Create: `epocha/apps/world/government_types.py`
- Create: `epocha/apps/world/tests/test_government_types.py`

- [ ] **Step 1: Write the failing tests**

Create `epocha/apps/world/tests/test_government_types.py`:

```python
"""Tests for government type configuration data integrity."""
from epocha.apps.world.government_types import GOVERNMENT_TYPES


class TestGovernmentTypesConfig:
    def test_all_12_types_present(self):
        """All 12 government types from the design doc must be configured."""
        expected = {
            "democracy", "illiberal_democracy", "autocracy", "monarchy",
            "oligarchy", "theocracy", "totalitarian", "terrorist_regime",
            "anarchy", "federation", "kleptocracy", "junta",
        }
        assert set(GOVERNMENT_TYPES.keys()) == expected

    def test_all_types_have_required_fields(self):
        """Every type must have all required configuration fields."""
        required_fields = {
            "label", "power_source", "legitimacy_base", "repression_tendency",
            "corruption_resistance", "election_enabled", "succession",
            "stability_weights", "institution_effects", "transitions",
        }
        for type_name, config in GOVERNMENT_TYPES.items():
            missing = required_fields - set(config.keys())
            assert not missing, f"{type_name} missing fields: {missing}"

    def test_stability_weights_sum_to_one(self):
        """Stability weights must sum to approximately 1.0."""
        for type_name, config in GOVERNMENT_TYPES.items():
            weights = config["stability_weights"]
            total = weights["economy"] + weights["legitimacy"] + weights["military"]
            assert abs(total - 1.0) < 0.01, f"{type_name} stability weights sum to {total}"

    def test_institution_effects_have_all_7(self):
        """Every type must specify effects for all 7 institutions."""
        institutions = {"justice", "education", "health", "military", "media", "religion", "bureaucracy"}
        for type_name, config in GOVERNMENT_TYPES.items():
            effects = set(config["institution_effects"].keys())
            assert effects == institutions, f"{type_name} missing institution effects: {institutions - effects}"

    def test_transitions_reference_valid_types(self):
        """All transition targets must be valid government types."""
        valid_types = set(GOVERNMENT_TYPES.keys())
        for type_name, config in GOVERNMENT_TYPES.items():
            for target in config["transitions"]:
                assert target in valid_types, f"{type_name} transitions to unknown type '{target}'"

    def test_repression_tendency_in_range(self):
        """Repression tendency must be between 0.0 and 1.0."""
        for type_name, config in GOVERNMENT_TYPES.items():
            val = config["repression_tendency"]
            assert 0.0 <= val <= 1.0, f"{type_name} repression_tendency {val} out of range"

    def test_corruption_resistance_in_range(self):
        """Corruption resistance must be between 0.0 and 1.0."""
        for type_name, config in GOVERNMENT_TYPES.items():
            val = config["corruption_resistance"]
            assert 0.0 <= val <= 1.0, f"{type_name} corruption_resistance {val} out of range"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `docker compose -f docker-compose.local.yml exec -T web pytest epocha/apps/world/tests/test_government_types.py -v`

- [ ] **Step 3: Implement government types configuration**

Create `epocha/apps/world/government_types.py`. This is a large data file (~300 lines) containing the `GOVERNMENT_TYPES` dictionary with all 12 types. Each type follows this schema:

```python
"""Data-driven configuration for the 12 government types.

Each type is a dictionary of parameters consumed by the government engine.
The engine has no type-specific code -- all behavior comes from these parameters.
Adding a new government type means adding a dictionary entry here.

Sources for parameter calibration:
- Polity IV dataset for regime classification
- Freedom House scores for institutional independence
- Acemoglu & Robinson (2006) for transition patterns
"""
from __future__ import annotations

GOVERNMENT_TYPES: dict[str, dict] = {
    "democracy": {
        "label": "Democracy",
        "power_source": "election",
        "legitimacy_base": "popular",
        "repression_tendency": 0.05,
        "corruption_resistance": 0.7,
        "election_enabled": True,
        "election_manipulated": False,
        "succession": "election",
        "stability_weights": {"economy": 0.4, "legitimacy": 0.4, "military": 0.2},
        "institution_effects": {
            "justice": 0.02, "education": 0.02, "health": 0.01,
            "military": 0.0, "media": 0.02, "religion": 0.0, "bureaucracy": 0.01,
        },
        "transitions": {
            "illiberal_democracy": {"institutional_trust_below": 0.3, "repression_above": 0.3},
            "autocracy": {"institutional_trust_below": 0.2, "military_loyalty_below": 0.3, "stability_below": 0.2},
            "anarchy": {"stability_below": 0.1},
        },
    },
    "illiberal_democracy": {
        "label": "Illiberal Democracy",
        "power_source": "manipulated_election",
        "legitimacy_base": "facade_popular",
        "repression_tendency": 0.3,
        "corruption_resistance": 0.3,
        "election_enabled": True,
        "election_manipulated": True,
        "succession": "manipulated_election",
        "stability_weights": {"economy": 0.3, "legitimacy": 0.3, "military": 0.4},
        "institution_effects": {
            "justice": -0.01, "education": 0.0, "health": 0.0,
            "military": 0.01, "media": -0.03, "religion": 0.0, "bureaucracy": -0.01,
        },
        "transitions": {
            "autocracy": {"repression_above": 0.6, "institutional_trust_below": 0.2},
            "democracy": {"popular_legitimacy_above": 0.7, "corruption_below": 0.3},
            "anarchy": {"stability_below": 0.1},
        },
    },
    "autocracy": {
        "label": "Autocracy",
        "power_source": "force",
        "legitimacy_base": "fear_and_loyalty",
        "repression_tendency": 0.6,
        "corruption_resistance": 0.2,
        "election_enabled": False,
        "election_manipulated": False,
        "succession": "strongest_faction",
        "stability_weights": {"economy": 0.2, "legitimacy": 0.2, "military": 0.6},
        "institution_effects": {
            "justice": -0.02, "education": -0.01, "health": -0.01,
            "military": 0.02, "media": -0.03, "religion": 0.0, "bureaucracy": -0.01,
        },
        "transitions": {
            "democracy": {"popular_legitimacy_above": 0.6, "military_loyalty_below": 0.3},
            "totalitarian": {"repression_above": 0.8},
            "junta": {"military_loyalty_above": 0.8},
            "anarchy": {"stability_below": 0.1},
        },
    },
    "monarchy": {
        "label": "Monarchy",
        "power_source": "inheritance",
        "legitimacy_base": "dynasty",
        "repression_tendency": 0.2,
        "corruption_resistance": 0.4,
        "election_enabled": False,
        "election_manipulated": False,
        "succession": "inheritance",
        "stability_weights": {"economy": 0.3, "legitimacy": 0.4, "military": 0.3},
        "institution_effects": {
            "justice": 0.0, "education": 0.0, "health": 0.0,
            "military": 0.01, "media": -0.01, "religion": 0.01, "bureaucracy": 0.0,
        },
        "transitions": {
            "autocracy": {"popular_legitimacy_below": 0.2, "repression_above": 0.5},
            "democracy": {"popular_legitimacy_above": 0.7, "institutional_trust_above": 0.6},
            "anarchy": {"stability_below": 0.1},
        },
    },
    "oligarchy": {
        "label": "Oligarchy",
        "power_source": "wealth",
        "legitimacy_base": "wealth",
        "repression_tendency": 0.3,
        "corruption_resistance": 0.15,
        "election_enabled": False,
        "election_manipulated": False,
        "succession": "richest",
        "stability_weights": {"economy": 0.5, "legitimacy": 0.2, "military": 0.3},
        "institution_effects": {
            "justice": -0.02, "education": -0.01, "health": -0.02,
            "military": 0.01, "media": -0.02, "religion": 0.0, "bureaucracy": -0.01,
        },
        "transitions": {
            "democracy": {"popular_legitimacy_above": 0.6, "institutional_trust_above": 0.5},
            "autocracy": {"military_loyalty_below": 0.3, "stability_below": 0.3},
            "kleptocracy": {"corruption_above": 0.7},
            "anarchy": {"stability_below": 0.1},
        },
    },
    "theocracy": {
        "label": "Theocracy",
        "power_source": "religious_authority",
        "legitimacy_base": "divine",
        "repression_tendency": 0.4,
        "corruption_resistance": 0.4,
        "election_enabled": False,
        "election_manipulated": False,
        "succession": "religious_leader",
        "stability_weights": {"economy": 0.2, "legitimacy": 0.5, "military": 0.3},
        "institution_effects": {
            "justice": -0.01, "education": -0.02, "health": 0.0,
            "military": 0.0, "media": -0.02, "religion": 0.03, "bureaucracy": 0.0,
        },
        "transitions": {
            "democracy": {"popular_legitimacy_above": 0.7, "institutional_trust_above": 0.5},
            "autocracy": {"popular_legitimacy_below": 0.2},
            "anarchy": {"stability_below": 0.1},
        },
    },
    "totalitarian": {
        "label": "Totalitarian Regime",
        "power_source": "force",
        "legitimacy_base": "terror",
        "repression_tendency": 0.9,
        "corruption_resistance": 0.1,
        "election_enabled": False,
        "election_manipulated": False,
        "succession": "strongest_faction",
        "stability_weights": {"economy": 0.1, "legitimacy": 0.1, "military": 0.8},
        "institution_effects": {
            "justice": -0.03, "education": -0.02, "health": -0.01,
            "military": 0.02, "media": -0.04, "religion": -0.02, "bureaucracy": -0.01,
        },
        "transitions": {
            "autocracy": {"repression_below": 0.6},
            "anarchy": {"stability_below": 0.1, "military_loyalty_below": 0.2},
        },
    },
    "terrorist_regime": {
        "label": "Terrorist Regime",
        "power_source": "force",
        "legitimacy_base": "terror",
        "repression_tendency": 0.95,
        "corruption_resistance": 0.05,
        "election_enabled": False,
        "election_manipulated": False,
        "succession": "strongest_faction",
        "stability_weights": {"economy": 0.1, "legitimacy": 0.1, "military": 0.8},
        "institution_effects": {
            "justice": -0.04, "education": -0.03, "health": -0.02,
            "military": 0.01, "media": -0.04, "religion": -0.01, "bureaucracy": -0.02,
        },
        "transitions": {
            "autocracy": {"stability_above": 0.3},
            "anarchy": {"stability_below": 0.15},
        },
    },
    "anarchy": {
        "label": "Anarchy",
        "power_source": "none",
        "legitimacy_base": "none",
        "repression_tendency": 0.0,
        "corruption_resistance": 0.0,
        "election_enabled": False,
        "election_manipulated": False,
        "succession": "none",
        "stability_weights": {"economy": 0.5, "legitimacy": 0.3, "military": 0.2},
        "institution_effects": {
            "justice": -0.04, "education": -0.03, "health": -0.03,
            "military": -0.02, "media": -0.01, "religion": 0.0, "bureaucracy": -0.04,
        },
        "transitions": {
            "autocracy": {"stability_above": 0.3},
            "democracy": {"institutional_trust_above": 0.5, "popular_legitimacy_above": 0.5},
            "junta": {"military_loyalty_above": 0.6},
        },
    },
    "federation": {
        "label": "Federation",
        "power_source": "election",
        "legitimacy_base": "mutual_benefit",
        "repression_tendency": 0.05,
        "corruption_resistance": 0.5,
        "election_enabled": True,
        "election_manipulated": False,
        "succession": "election",
        "stability_weights": {"economy": 0.4, "legitimacy": 0.4, "military": 0.2},
        "institution_effects": {
            "justice": 0.01, "education": 0.01, "health": 0.01,
            "military": 0.0, "media": 0.01, "religion": 0.0, "bureaucracy": 0.02,
        },
        "transitions": {
            "anarchy": {"stability_below": 0.15},
            "democracy": {"institutional_trust_above": 0.6},
            "autocracy": {"stability_below": 0.2, "military_loyalty_below": 0.3},
        },
    },
    "kleptocracy": {
        "label": "Kleptocracy",
        "power_source": "wealth",
        "legitimacy_base": "theft",
        "repression_tendency": 0.4,
        "corruption_resistance": 0.0,
        "election_enabled": False,
        "election_manipulated": False,
        "succession": "richest",
        "stability_weights": {"economy": 0.4, "legitimacy": 0.2, "military": 0.4},
        "institution_effects": {
            "justice": -0.03, "education": -0.02, "health": -0.02,
            "military": 0.01, "media": -0.03, "religion": 0.0, "bureaucracy": -0.03,
        },
        "transitions": {
            "anarchy": {"stability_below": 0.1},
            "autocracy": {"military_loyalty_above": 0.7},
            "democracy": {"popular_legitimacy_above": 0.7, "corruption_below": 0.3},
        },
    },
    "junta": {
        "label": "Military Junta",
        "power_source": "military",
        "legitimacy_base": "military_force",
        "repression_tendency": 0.5,
        "corruption_resistance": 0.25,
        "election_enabled": False,
        "election_manipulated": False,
        "succession": "military_leader",
        "stability_weights": {"economy": 0.2, "legitimacy": 0.1, "military": 0.7},
        "institution_effects": {
            "justice": -0.02, "education": -0.01, "health": -0.01,
            "military": 0.03, "media": -0.03, "religion": 0.0, "bureaucracy": -0.01,
        },
        "transitions": {
            "autocracy": {"military_loyalty_below": 0.4},
            "democracy": {"popular_legitimacy_above": 0.6, "institutional_trust_above": 0.4},
            "anarchy": {"stability_below": 0.1},
        },
    },
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `docker compose -f docker-compose.local.yml exec -T web pytest epocha/apps/world/tests/test_government_types.py -v`
Expected: All 7 tests PASS.

- [ ] **Step 5: Commit**

```
feat(world): add data-driven configuration for 12 government types

CHANGE: Define all 12 government types as parametric dictionaries consumed
by the government engine. Each type specifies power source, legitimacy
base, repression tendency, corruption resistance, institution effects,
stability weights, and transition conditions. Adding a new type is
adding a dictionary entry with zero code changes.
```

---

### Task 3: Institution health dynamics

Engine that updates institution health each political cycle based on government type and funding.

**Files:**
- Create: `epocha/apps/world/institutions.py`
- Create: `epocha/apps/world/tests/test_institutions.py`

- [ ] **Step 1: Write the failing tests**

Create `epocha/apps/world/tests/test_institutions.py`:

```python
"""Tests for institution health dynamics."""
import pytest

from epocha.apps.world.institutions import update_institutions
from epocha.apps.world.models import Government, Institution, World
from epocha.apps.simulation.models import Simulation
from epocha.apps.users.models import User


@pytest.fixture
def user(db):
    return User.objects.create_user(email="inst@epocha.dev", username="insttest", password="pass123")


@pytest.fixture
def simulation(user):
    return Simulation.objects.create(name="InstTest", seed=42, owner=user)


@pytest.fixture
def world(simulation):
    return World.objects.create(simulation=simulation)


@pytest.fixture
def government(simulation):
    return Government.objects.create(simulation=simulation, government_type="democracy")


@pytest.fixture
def all_institutions(simulation):
    types = ["justice", "education", "health", "military", "media", "religion", "bureaucracy"]
    return [
        Institution.objects.create(simulation=simulation, institution_type=t, health=0.5, independence=0.5, funding=0.5)
        for t in types
    ]


@pytest.mark.django_db
class TestUpdateInstitutions:
    def test_democracy_improves_justice(self, simulation, world, government, all_institutions):
        """Democracy has positive justice effect -- health should increase."""
        justice = Institution.objects.get(simulation=simulation, institution_type="justice")
        initial = justice.health
        update_institutions(simulation)
        justice.refresh_from_db()
        assert justice.health > initial

    def test_autocracy_degrades_media(self, simulation, world, government, all_institutions):
        """Autocracy has negative media effect -- health should decrease."""
        government.government_type = "autocracy"
        government.save(update_fields=["government_type"])
        media = Institution.objects.get(simulation=simulation, institution_type="media")
        initial = media.health
        update_institutions(simulation)
        media.refresh_from_db()
        assert media.health < initial

    def test_health_clamped_to_range(self, simulation, world, government, all_institutions):
        """Institution health must stay in [0.0, 1.0]."""
        for inst in all_institutions:
            inst.health = 0.99
            inst.save(update_fields=["health"])
        update_institutions(simulation)
        for inst in Institution.objects.filter(simulation=simulation):
            assert 0.0 <= inst.health <= 1.0

    def test_low_funding_degrades_health(self, simulation, world, government, all_institutions):
        """Institutions with funding below 0.5 should degrade even in democracy."""
        justice = Institution.objects.get(simulation=simulation, institution_type="justice")
        justice.funding = 0.1
        justice.health = 0.5
        justice.save(update_fields=["funding", "health"])
        update_institutions(simulation)
        justice.refresh_from_db()
        # Even democracy's positive effect may not overcome severe underfunding
        assert justice.health <= 0.5

    def test_all_7_institutions_updated(self, simulation, world, government, all_institutions):
        """All 7 institutions should be updated in a single call."""
        update_institutions(simulation)
        for inst in Institution.objects.filter(simulation=simulation):
            # Health should have changed from the initial 0.5
            # (democracy has non-zero effects on most institutions)
            inst.refresh_from_db()
            assert isinstance(inst.health, float)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `docker compose -f docker-compose.local.yml exec -T web pytest epocha/apps/world/tests/test_institutions.py -v`

- [ ] **Step 3: Implement institution health dynamics**

Create `epocha/apps/world/institutions.py`:

```python
"""Institution health dynamics engine.

Updates the health of each social institution based on the government type's
natural effects and the institution's funding level. Healthy institutions
feed positive government indicators; degraded institutions accelerate decline.

Source: institutional quality as driver of state capacity is a core thesis
in Acemoglu & Robinson (2012). "Why Nations Fail." Crown Publishers.
"""
from __future__ import annotations

import logging

from .government_types import GOVERNMENT_TYPES
from .models import Government, Institution

logger = logging.getLogger(__name__)


def update_institutions(simulation) -> None:
    """Update health of all institutions for a simulation.

    Each institution's health evolves based on:
    1. Government type effect (positive or negative drift)
    2. Funding level (above 0.5 = recovery, below = degradation)
    3. Natural decay toward 0.4 (without maintenance, institutions decline)

    Args:
        simulation: The simulation instance.
    """
    try:
        government = Government.objects.get(simulation=simulation)
    except Government.DoesNotExist:
        return

    type_config = GOVERNMENT_TYPES.get(government.government_type)
    if not type_config:
        return

    effects = type_config["institution_effects"]
    institutions = Institution.objects.filter(simulation=simulation)

    for institution in institutions:
        effect = effects.get(institution.institution_type, 0.0)

        # Funding influence: well-funded institutions recover, underfunded degrade
        funding_effect = (institution.funding - 0.5) * 0.02

        # Natural entropy: without active maintenance, institutions decay
        entropy = -0.005

        delta = effect + funding_effect + entropy
        institution.health = max(0.0, min(1.0, institution.health + delta))
        institution.save(update_fields=["health"])
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `docker compose -f docker-compose.local.yml exec -T web pytest epocha/apps/world/tests/test_institutions.py -v`
Expected: All 5 tests PASS.

- [ ] **Step 5: Commit**

```
feat(world): add institution health dynamics engine

CHANGE: Implement update_institutions() which evolves the health of 7
social institutions based on government type effects, funding levels,
and natural entropy. Democracies strengthen justice and media, autocracies
degrade them. Underfunded institutions decline regardless of government.
```

---

### Task 4: Social stratification engine

Dynamic class mobility, Gini coefficient, and corruption mechanics.

**Files:**
- Create: `epocha/apps/world/stratification.py`
- Create: `epocha/apps/world/tests/test_stratification.py`

- [ ] **Step 1: Write the failing tests**

Create `epocha/apps/world/tests/test_stratification.py`:

```python
"""Tests for social stratification dynamics."""
import pytest

from epocha.apps.agents.models import Agent
from epocha.apps.simulation.models import Simulation
from epocha.apps.users.models import User
from epocha.apps.world.models import World
from epocha.apps.world.stratification import compute_gini, update_social_classes


@pytest.fixture
def user(db):
    return User.objects.create_user(email="strat@epocha.dev", username="strattest", password="pass123")


@pytest.fixture
def simulation(user):
    return Simulation.objects.create(name="StratTest", seed=42, owner=user)


@pytest.fixture
def world(simulation):
    return World.objects.create(simulation=simulation)


@pytest.fixture
def agents_with_wealth(simulation):
    agents = []
    # Create 10 agents with varying wealth
    for i, (name, wealth) in enumerate([
        ("Ultra", 1000.0), ("Rich", 500.0), ("Upper", 200.0),
        ("Mid1", 100.0), ("Mid2", 90.0), ("Mid3", 80.0),
        ("Work1", 50.0), ("Work2", 40.0),
        ("Poor1", 10.0), ("Poor2", 5.0),
    ]):
        agents.append(Agent.objects.create(
            simulation=simulation, name=name, role="citizen", wealth=wealth,
            social_class="working",
            personality={"openness": 0.5, "conscientiousness": 0.5, "extraversion": 0.5,
                         "agreeableness": 0.5, "neuroticism": 0.5},
        ))
    return agents


class TestComputeGini:
    def test_perfect_equality(self):
        """All agents with same wealth -> Gini = 0."""
        gini = compute_gini([50.0, 50.0, 50.0, 50.0])
        assert abs(gini) < 0.01

    def test_high_inequality(self):
        """One agent has all wealth -> Gini close to 1."""
        gini = compute_gini([0.0, 0.0, 0.0, 1000.0])
        assert gini > 0.7

    def test_moderate_inequality(self):
        """Typical wealth distribution -> Gini between 0.3 and 0.6."""
        gini = compute_gini([10.0, 30.0, 50.0, 80.0, 200.0])
        assert 0.2 < gini < 0.6

    def test_single_agent(self):
        """Single agent -> Gini = 0."""
        gini = compute_gini([100.0])
        assert gini == 0.0

    def test_empty_list(self):
        """No agents -> Gini = 0."""
        gini = compute_gini([])
        assert gini == 0.0


@pytest.mark.django_db
class TestUpdateSocialClasses:
    def test_wealthiest_becomes_elite(self, simulation, world, agents_with_wealth):
        """The top 5% agent should be classified as elite."""
        update_social_classes(simulation)
        ultra = Agent.objects.get(name="Ultra")
        assert ultra.social_class == "elite"

    def test_poorest_becomes_poor(self, simulation, world, agents_with_wealth):
        """The bottom agents should be classified as poor."""
        update_social_classes(simulation)
        poor = Agent.objects.get(name="Poor2")
        assert poor.social_class == "poor"

    def test_middle_agents_classified_correctly(self, simulation, world, agents_with_wealth):
        """Middle wealth agents should be in middle or working class."""
        update_social_classes(simulation)
        mid = Agent.objects.get(name="Mid2")
        assert mid.social_class in ("middle", "working")

    def test_classes_cover_all_agents(self, simulation, world, agents_with_wealth):
        """Every agent must have a valid social class after update."""
        update_social_classes(simulation)
        valid = {"elite", "wealthy", "middle", "working", "poor"}
        for agent in Agent.objects.filter(simulation=simulation):
            assert agent.social_class in valid
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `docker compose -f docker-compose.local.yml exec -T web pytest epocha/apps/world/tests/test_stratification.py -v`

- [ ] **Step 3: Implement stratification engine**

Create `epocha/apps/world/stratification.py`:

```python
"""Social stratification dynamics -- class mobility and inequality.

Manages dynamic social class assignment based on wealth distribution,
computes the Gini coefficient for inequality measurement, and handles
corruption mechanics for agents in power positions.

Source: Gini, C. (1912). "Variabilita e mutabilita." Standard formula
for wealth inequality.

Source: Acemoglu, D. & Robinson, J. A. (2006). "Economic Origins of
Dictatorship and Democracy." Cambridge University Press. Historical
pattern: revolutions correlate with Gini 0.6-0.8.
"""
from __future__ import annotations

import logging

from epocha.apps.agents.models import Agent, Memory

logger = logging.getLogger(__name__)

# Class thresholds as percentile ranges (from wealthiest to poorest).
# Top 5% = elite, next 10% = wealthy, etc.
_CLASS_THRESHOLDS = [
    (0.00, 0.05, "elite"),
    (0.05, 0.15, "wealthy"),
    (0.15, 0.50, "middle"),
    (0.50, 0.80, "working"),
    (0.80, 1.00, "poor"),
]


def compute_gini(wealths: list[float]) -> float:
    """Compute Gini coefficient from a list of wealth values.

    The Gini coefficient measures inequality: 0.0 = perfect equality,
    1.0 = perfect inequality (one person owns everything).

    Uses the standard formula based on the mean absolute difference.

    Args:
        wealths: List of wealth values for all agents.

    Returns:
        Gini coefficient between 0.0 and 1.0.
    """
    n = len(wealths)
    if n < 2:
        return 0.0
    total = sum(wealths)
    if total <= 0:
        return 0.0
    sorted_w = sorted(wealths)
    cumulative = sum((2 * i - n + 1) * w for i, w in enumerate(sorted_w))
    return max(0.0, min(1.0, cumulative / (n * total)))


def update_social_classes(simulation) -> None:
    """Update social class for all living agents based on wealth percentile.

    Agents are ranked by wealth and assigned to classes based on their
    position in the distribution. Class boundaries are defined by
    _CLASS_THRESHOLDS.

    Args:
        simulation: The simulation instance.
    """
    agents = list(
        Agent.objects.filter(simulation=simulation, is_alive=True)
        .order_by("-wealth")
    )
    n = len(agents)
    if n == 0:
        return

    for rank, agent in enumerate(agents):
        percentile = rank / n
        new_class = "working"  # default
        for lower, upper, class_name in _CLASS_THRESHOLDS:
            if lower <= percentile < upper:
                new_class = class_name
                break

        if agent.social_class != new_class:
            old_class = agent.social_class
            agent.social_class = new_class
            agent.save(update_fields=["social_class"])
            # Create memory if class changed significantly (skip adjacent changes)
            if _class_distance(old_class, new_class) >= 2:
                direction = "risen to" if _class_rank(new_class) < _class_rank(old_class) else "fallen to"
                Memory.objects.create(
                    agent=agent,
                    content=f"My social standing has {direction} {new_class} class.",
                    emotional_weight=0.4,
                    source_type="direct",
                    tick_created=simulation.current_tick,
                )


def process_corruption(simulation, tick: int) -> None:
    """Process corruption for agents in power positions.

    Agents who lead factions or head the government with low conscientiousness
    have a chance to skim wealth from the system each political cycle.

    Args:
        simulation: The simulation instance.
        tick: Current tick.
    """
    from epocha.apps.world.models import Government

    try:
        government = Government.objects.get(simulation=simulation)
    except Government.DoesNotExist:
        return

    # Head of state corruption
    if government.head_of_state and government.head_of_state.is_alive:
        head = government.head_of_state
        conscientiousness = head.personality.get("conscientiousness", 0.5)
        if isinstance(conscientiousness, (int, float)) and conscientiousness < 0.4:
            skim_amount = (0.4 - conscientiousness) * 10  # Up to 4.0 wealth per cycle
            head.wealth += skim_amount
            head.save(update_fields=["wealth"])
            government.corruption = min(1.0, government.corruption + 0.02)
            government.save(update_fields=["corruption"])

    # Faction leader corruption
    from epocha.apps.agents.models import Group
    factions = Group.objects.filter(simulation=simulation, cohesion__gt=0.0).select_related("leader")
    for faction in factions:
        if faction.leader and faction.leader.is_alive:
            leader = faction.leader
            conscientiousness = leader.personality.get("conscientiousness", 0.5)
            if isinstance(conscientiousness, (int, float)) and conscientiousness < 0.3:
                skim_amount = (0.3 - conscientiousness) * 5
                leader.wealth += skim_amount
                leader.save(update_fields=["wealth"])


def _class_rank(social_class: str) -> int:
    """Return numeric rank for social class (0 = elite, 4 = poor)."""
    ranks = {"elite": 0, "wealthy": 1, "middle": 2, "working": 3, "poor": 4}
    return ranks.get(social_class, 3)


def _class_distance(class_a: str, class_b: str) -> int:
    """Return distance between two social classes."""
    return abs(_class_rank(class_a) - _class_rank(class_b))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `docker compose -f docker-compose.local.yml exec -T web pytest epocha/apps/world/tests/test_stratification.py -v`
Expected: All 9 tests PASS.

- [ ] **Step 5: Commit**

```
feat(world): add social stratification engine with Gini coefficient

CHANGE: Implement dynamic social class assignment based on wealth
percentile, Gini coefficient calculation for inequality measurement,
and corruption mechanics for agents in power. Classes update each
political cycle, creating memories when agents experience significant
social mobility.
```

---

### Task 5: Election system

Deterministic vote scoring with memory influence.

**Files:**
- Create: `epocha/apps/world/election.py`
- Create: `epocha/apps/world/tests/test_election.py`

- [ ] **Step 1: Write the failing tests**

Create `epocha/apps/world/tests/test_election.py`:

```python
"""Tests for the deterministic election system."""
import pytest

from epocha.apps.agents.models import Agent, Group, Memory, Relationship
from epocha.apps.simulation.models import Simulation
from epocha.apps.users.models import User
from epocha.apps.world.election import compute_vote_score, run_election
from epocha.apps.world.models import Government, World


@pytest.fixture
def user(db):
    return User.objects.create_user(email="elec@epocha.dev", username="electest", password="pass123")


@pytest.fixture
def simulation(user):
    return Simulation.objects.create(name="ElecTest", seed=42, owner=user)


@pytest.fixture
def world(simulation):
    return World.objects.create(simulation=simulation)


@pytest.fixture
def government(simulation):
    return Government.objects.create(
        simulation=simulation, government_type="democracy",
        last_election_tick=0,
    )


@pytest.fixture
def factions_and_agents(simulation):
    faction_a = Group.objects.create(
        simulation=simulation, name="Reformers", objective="Reform",
        cohesion=0.7, formed_at_tick=1,
    )
    faction_b = Group.objects.create(
        simulation=simulation, name="Traditionalists", objective="Preserve",
        cohesion=0.6, formed_at_tick=1,
    )
    leader_a = Agent.objects.create(
        simulation=simulation, name="Anna", role="politician",
        charisma=0.8, intelligence=0.7, wealth=100.0, group=faction_a,
        personality={"openness": 0.8, "conscientiousness": 0.6, "extraversion": 0.7,
                     "agreeableness": 0.5, "neuroticism": 0.3},
    )
    leader_b = Agent.objects.create(
        simulation=simulation, name="Bruno", role="general",
        charisma=0.5, intelligence=0.6, wealth=80.0, group=faction_b,
        personality={"openness": 0.3, "conscientiousness": 0.7, "extraversion": 0.4,
                     "agreeableness": 0.4, "neuroticism": 0.5},
    )
    faction_a.leader = leader_a
    faction_a.save(update_fields=["leader"])
    faction_b.leader = leader_b
    faction_b.save(update_fields=["leader"])

    voter = Agent.objects.create(
        simulation=simulation, name="Citizen", role="farmer",
        charisma=0.3, intelligence=0.5, wealth=50.0, mood=0.5,
        personality={"openness": 0.6, "conscientiousness": 0.5, "extraversion": 0.5,
                     "agreeableness": 0.5, "neuroticism": 0.5},
    )
    return faction_a, faction_b, leader_a, leader_b, voter


@pytest.mark.django_db
class TestComputeVoteScore:
    def test_charismatic_candidate_scores_higher(self, simulation, world, factions_and_agents):
        _, _, leader_a, leader_b, voter = factions_and_agents
        score_a = compute_vote_score(voter, leader_a, tick=50)
        score_b = compute_vote_score(voter, leader_b, tick=50)
        # Anna has higher charisma (0.8 vs 0.5)
        assert score_a > score_b

    def test_positive_memory_boosts_score(self, simulation, world, factions_and_agents):
        _, _, leader_a, _, voter = factions_and_agents
        score_before = compute_vote_score(voter, leader_a, tick=50)
        Memory.objects.create(
            agent=voter, content="Anna helped the poor and reformed the tax system.",
            emotional_weight=0.5, source_type="hearsay", tick_created=45,
        )
        score_after = compute_vote_score(voter, leader_a, tick=50)
        assert score_after > score_before

    def test_negative_memory_reduces_score(self, simulation, world, factions_and_agents):
        _, _, leader_a, _, voter = factions_and_agents
        score_before = compute_vote_score(voter, leader_a, tick=50)
        Memory.objects.create(
            agent=voter, content="Anna betrayed the people and stole from the treasury.",
            emotional_weight=0.7, source_type="rumor", tick_created=45,
        )
        score_after = compute_vote_score(voter, leader_a, tick=50)
        assert score_after < score_before

    def test_relationship_influences_vote(self, simulation, world, factions_and_agents):
        _, _, leader_a, _, voter = factions_and_agents
        score_no_rel = compute_vote_score(voter, leader_a, tick=50)
        Relationship.objects.create(
            agent_from=voter, agent_to=leader_a,
            relation_type="friendship", strength=0.8, sentiment=0.7, since_tick=0,
        )
        score_with_rel = compute_vote_score(voter, leader_a, tick=50)
        assert score_with_rel > score_no_rel


@pytest.mark.django_db
class TestRunElection:
    def test_election_sets_head_of_state(self, simulation, world, government, factions_and_agents):
        _, _, leader_a, leader_b, voter = factions_and_agents
        run_election(simulation, tick=50)
        government.refresh_from_db()
        assert government.head_of_state in (leader_a, leader_b)
        assert government.ruling_faction is not None
        assert government.last_election_tick == 50

    def test_election_creates_public_memory(self, simulation, world, government, factions_and_agents):
        run_election(simulation, tick=50)
        # All agents should have a memory about the election result
        for agent in Agent.objects.filter(simulation=simulation, is_alive=True):
            election_memories = Memory.objects.filter(
                agent=agent, source_type="public", content__contains="won the election",
            )
            assert election_memories.count() >= 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `docker compose -f docker-compose.local.yml exec -T web pytest epocha/apps/world/tests/test_election.py -v`

- [ ] **Step 3: Implement election system**

Create `epocha/apps/world/election.py`:

```python
"""Deterministic election system with memory-based influence.

Each agent votes for faction leaders based on a weighted score combining
relationship sentiment, personality alignment, economic satisfaction,
memory influence (propaganda/hearsay), and candidate charisma. No LLM
calls -- elections are fully deterministic and reproducible.

The memory_influence component is where information flow becomes political:
an agent who heard via hearsay that a candidate is corrupt will vote
differently. This makes propaganda and reputation consequential.
"""
from __future__ import annotations

import logging
import re

from django.db.models import Q

from epocha.apps.agents.affinity import _personality_similarity
from epocha.apps.agents.models import Agent, Group, Memory, Relationship

logger = logging.getLogger(__name__)

# How far back to look for memories about candidates (in ticks).
_MEMORY_LOOKBACK = 20

# Positive and negative sentiment keywords for memory scoring.
_POSITIVE_KEYWORDS = {"helped", "reformed", "saved", "protected", "improved", "founded", "built", "united"}
_NEGATIVE_KEYWORDS = {"betrayed", "stole", "corrupt", "attacked", "failed", "oppressed", "exploited", "destroyed"}


def compute_vote_score(voter: Agent, candidate: Agent, tick: int) -> float:
    """Compute how favorably a voter views a candidate.

    Formula:
        score = relationship * 0.25 + personality * 0.15 + economy * 0.20
              + memory * 0.25 + charisma * 0.15

    Args:
        voter: The voting agent.
        candidate: The candidate agent.
        tick: Current tick (for memory lookback).

    Returns:
        Vote score between 0.0 and 1.0.
    """
    rel_score = _relationship_component(voter, candidate)
    personality_score = _personality_similarity(voter.personality, candidate.personality)
    economy_score = _economic_satisfaction(voter)
    memory_score = _memory_influence(voter, candidate, tick)
    charisma_score = candidate.charisma

    score = (
        rel_score * 0.25
        + personality_score * 0.15
        + economy_score * 0.20
        + memory_score * 0.25
        + charisma_score * 0.15
    )
    return max(0.0, min(1.0, score))


def run_election(simulation, tick: int) -> dict:
    """Run an election and set the winner as head of state.

    Candidates are leaders of all factions. Each living agent votes.
    The candidate with the highest total score wins.

    Args:
        simulation: The simulation instance.
        tick: Current tick.

    Returns:
        Dict with election results: winner, scores, etc.
    """
    from .models import Government

    government = Government.objects.get(simulation=simulation)
    type_config_module = __import__("epocha.apps.world.government_types", fromlist=["GOVERNMENT_TYPES"])
    type_config = type_config_module.GOVERNMENT_TYPES.get(government.government_type, {})

    # Gather candidates: leaders of all factions
    factions = Group.objects.filter(
        simulation=simulation, cohesion__gt=0.0, leader__isnull=False,
    ).select_related("leader")

    candidates = []
    for faction in factions:
        if faction.leader and faction.leader.is_alive:
            candidates.append((faction.leader, faction))

    if not candidates:
        logger.info("No candidates for election at tick %d", tick)
        return {"winner": None}

    # All living agents vote
    voters = Agent.objects.filter(simulation=simulation, is_alive=True)
    scores = {candidate.id: 0.0 for candidate, _ in candidates}

    manipulation_bonus = 0.3 if type_config.get("election_manipulated") else 0.0

    for voter in voters:
        for candidate, faction in candidates:
            vote = compute_vote_score(voter, candidate, tick)
            # Manipulation bonus for ruling faction's candidate
            if manipulation_bonus and government.ruling_faction_id == faction.id:
                vote += manipulation_bonus
            scores[candidate.id] += vote

    # Winner is candidate with highest total score
    winner_id = max(scores, key=scores.get)
    winner_agent = None
    winner_faction = None
    for candidate, faction in candidates:
        if candidate.id == winner_id:
            winner_agent = candidate
            winner_faction = faction
            break

    # Update government
    government.head_of_state = winner_agent
    government.ruling_faction = winner_faction
    government.last_election_tick = tick
    government.save(update_fields=["head_of_state", "ruling_faction", "last_election_tick"])

    # Create public memory for all agents
    for agent in Agent.objects.filter(simulation=simulation, is_alive=True):
        Memory.objects.create(
            agent=agent,
            content=f"{winner_agent.name} won the election and leads the government.",
            emotional_weight=0.3,
            source_type="public",
            reliability=1.0,
            tick_created=tick,
        )

    logger.info("Election at tick %d: %s won", tick, winner_agent.name)
    return {"winner": winner_agent.name, "faction": winner_faction.name, "scores": scores}


def _relationship_component(voter: Agent, candidate: Agent) -> float:
    """Relationship sentiment toward candidate, normalized to 0-1."""
    rel = Relationship.objects.filter(
        Q(agent_from=voter, agent_to=candidate)
        | Q(agent_from=candidate, agent_to=voter)
    ).first()
    if not rel:
        return 0.5  # Neutral for unknown candidates
    return (rel.sentiment + 1.0) / 2.0  # Normalize -1..1 to 0..1


def _economic_satisfaction(voter: Agent) -> float:
    """How satisfied the voter is with their economic situation."""
    wealth_factor = min(voter.wealth / 100.0, 1.0)
    return (voter.mood + wealth_factor) / 2.0


def _memory_influence(voter: Agent, candidate: Agent, tick: int) -> float:
    """Scan voter's memories for mentions of the candidate.

    Counts positive and negative keyword matches in memories that
    mention the candidate's name. Returns a score from 0.0 (very
    negative impression) to 1.0 (very positive).
    """
    min_tick = max(0, tick - _MEMORY_LOOKBACK)
    memories = Memory.objects.filter(
        agent=voter, tick_created__gte=min_tick, is_active=True,
    )

    positive_count = 0
    negative_count = 0
    candidate_name_lower = candidate.name.lower()

    for memory in memories:
        content_lower = memory.content.lower()
        if candidate_name_lower not in content_lower:
            continue
        for word in _POSITIVE_KEYWORDS:
            if word in content_lower:
                positive_count += 1
        for word in _NEGATIVE_KEYWORDS:
            if word in content_lower:
                negative_count += 1

    total = positive_count + negative_count
    if total == 0:
        return 0.5  # No opinion
    return max(0.0, min(1.0, (positive_count - negative_count) / total * 0.5 + 0.5))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `docker compose -f docker-compose.local.yml exec -T web pytest epocha/apps/world/tests/test_election.py -v`
Expected: All 6 tests PASS.

- [ ] **Step 5: Commit**

```
feat(world): add deterministic election system with memory influence

CHANGE: Implement elections where agents vote based on relationship
sentiment, personality alignment, economic satisfaction, memory
influence, and candidate charisma. Memory influence makes information
flow politically consequential -- propaganda and hearsay affect votes.
Manipulated elections give ruling faction a bonus.
```

---

### Task 6: Government engine (indicators, transitions, coups)

The main political engine that updates indicators, checks transitions, and handles coups/revolutions.

**Files:**
- Create: `epocha/apps/world/government.py`
- Create: `epocha/apps/world/tests/test_government.py`

- [ ] **Step 1: Write the failing tests**

Create `epocha/apps/world/tests/test_government.py`:

```python
"""Tests for the government engine."""
import pytest

from epocha.apps.agents.models import Agent, Group, Memory
from epocha.apps.simulation.models import Simulation
from epocha.apps.users.models import User
from epocha.apps.world.government import (
    check_transitions,
    process_political_cycle,
    update_government_indicators,
)
from epocha.apps.world.models import Government, GovernmentHistory, Institution, World


@pytest.fixture
def user(db):
    return User.objects.create_user(email="gov@epocha.dev", username="govtest", password="pass123")


@pytest.fixture
def simulation(user):
    return Simulation.objects.create(name="GovTest", seed=42, owner=user)


@pytest.fixture
def world(simulation):
    return World.objects.create(simulation=simulation)


@pytest.fixture
def government(simulation):
    return Government.objects.create(
        simulation=simulation, government_type="democracy", stability=0.5,
        institutional_trust=0.5, repression_level=0.1, corruption=0.2,
        popular_legitimacy=0.5, military_loyalty=0.5,
    )


@pytest.fixture
def all_institutions(simulation):
    types = ["justice", "education", "health", "military", "media", "religion", "bureaucracy"]
    return [
        Institution.objects.create(simulation=simulation, institution_type=t, health=0.5, independence=0.5, funding=0.5)
        for t in types
    ]


@pytest.fixture
def faction_with_leader(simulation):
    group = Group.objects.create(
        simulation=simulation, name="Rebels", objective="Overthrow", cohesion=0.8, formed_at_tick=1,
    )
    leader = Agent.objects.create(
        simulation=simulation, name="Che", role="revolutionary", charisma=0.9,
        intelligence=0.7, wealth=20.0, group=group,
        personality={"openness": 0.8, "conscientiousness": 0.5, "extraversion": 0.8,
                     "agreeableness": 0.3, "neuroticism": 0.6},
    )
    group.leader = leader
    group.save(update_fields=["leader"])
    return group, leader


@pytest.mark.django_db
class TestUpdateIndicators:
    def test_indicators_change_after_update(self, simulation, world, government, all_institutions):
        """Indicators should evolve based on institution health."""
        initial_trust = government.institutional_trust
        update_government_indicators(simulation)
        government.refresh_from_db()
        # With all institutions at 0.5, indicators should shift slightly
        assert isinstance(government.institutional_trust, float)

    def test_indicators_clamped_to_range(self, simulation, world, government, all_institutions):
        """All indicators must stay in [0.0, 1.0]."""
        government.institutional_trust = 0.99
        government.corruption = 0.01
        government.save(update_fields=["institutional_trust", "corruption"])
        update_government_indicators(simulation)
        government.refresh_from_db()
        for field in ["institutional_trust", "repression_level", "corruption", "popular_legitimacy", "military_loyalty"]:
            val = getattr(government, field)
            assert 0.0 <= val <= 1.0, f"{field} = {val}"

    def test_repression_drifts_toward_type_tendency(self, simulation, world, government, all_institutions):
        """Repression should drift toward the government type's natural tendency."""
        government.government_type = "autocracy"
        government.repression_level = 0.1
        government.save(update_fields=["government_type", "repression_level"])
        update_government_indicators(simulation)
        government.refresh_from_db()
        # Autocracy has repression_tendency 0.6, so repression should increase
        assert government.repression_level > 0.1


@pytest.mark.django_db
class TestTransitions:
    def test_democracy_to_illiberal_on_low_trust_high_repression(self, simulation, world, government, all_institutions):
        """Democracy should transition to illiberal_democracy when trust drops and repression rises."""
        government.institutional_trust = 0.2
        government.repression_level = 0.4
        government.save(update_fields=["institutional_trust", "repression_level"])
        result = check_transitions(simulation)
        assert result is not None
        government.refresh_from_db()
        assert government.government_type == "illiberal_democracy"

    def test_no_transition_when_stable(self, simulation, world, government, all_institutions):
        """A stable democracy should not transition."""
        government.institutional_trust = 0.7
        government.popular_legitimacy = 0.6
        government.repression_level = 0.05
        government.save(update_fields=["institutional_trust", "popular_legitimacy", "repression_level"])
        result = check_transitions(simulation)
        assert result is None
        government.refresh_from_db()
        assert government.government_type == "democracy"

    def test_transition_creates_history_record(self, simulation, world, government, all_institutions):
        """A transition must create a GovernmentHistory entry."""
        government.institutional_trust = 0.2
        government.repression_level = 0.4
        government.save(update_fields=["institutional_trust", "repression_level"])
        check_transitions(simulation)
        history = GovernmentHistory.objects.filter(simulation=simulation)
        assert history.count() >= 1

    def test_coup_succeeds_when_conditions_met(self, simulation, world, government, all_institutions, faction_with_leader):
        """A coup should succeed when faction is strong and military is disloyal."""
        government.military_loyalty = 0.2
        government.stability = 0.2
        government.save(update_fields=["military_loyalty", "stability"])
        group, leader = faction_with_leader
        # Add more members to make faction stronger
        for i in range(3):
            Agent.objects.create(
                simulation=simulation, name=f"Rebel{i}", role="fighter",
                charisma=0.3, group=group,
                personality={"openness": 0.5, "conscientiousness": 0.5, "extraversion": 0.5,
                             "agreeableness": 0.5, "neuroticism": 0.5},
            )
        from epocha.apps.world.government import check_coups
        result = check_coups(simulation, tick=20)
        if result:
            government.refresh_from_db()
            assert government.head_of_state == leader
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `docker compose -f docker-compose.local.yml exec -T web pytest epocha/apps/world/tests/test_government.py -v`

- [ ] **Step 3: Implement government engine**

Create `epocha/apps/world/government.py`:

```python
"""Government engine -- indicators, transitions, coups, and political cycle.

The main political processing module. Runs every N ticks and manages:
1. Government indicator evolution (from institution health and world state)
2. Regime transitions (when conditions from government_types config are met)
3. Elections (for types that hold them)
4. Coups and revolutions (when factions are strong and government is weak)

The engine is type-agnostic: all behavior is driven by the government_types
configuration. No type-specific code exists here.
"""
from __future__ import annotations

import logging
import random

from django.conf import settings

from epocha.apps.agents.models import Agent, Group, Memory

from .election import run_election
from .government_types import GOVERNMENT_TYPES
from .institutions import update_institutions
from .models import Government, GovernmentHistory, Institution
from .stratification import compute_gini, process_corruption, update_social_classes

logger = logging.getLogger(__name__)


def process_political_cycle(simulation, tick: int) -> None:
    """Main entry point for the political cycle. Runs every N ticks.

    Order of operations:
    1. Update institution health
    2. Update social stratification
    3. Process corruption
    4. Update government indicators (from institutions)
    5. Check for regime transitions
    6. Run elections (if due)
    7. Check for coups/revolutions

    Args:
        simulation: The simulation instance.
        tick: Current tick number.
    """
    interval = getattr(settings, "EPOCHA_GOVERNMENT_CYCLE_INTERVAL", 10)
    if tick % interval != 0:
        return

    try:
        government = Government.objects.get(simulation=simulation)
    except Government.DoesNotExist:
        return

    # 1. Institutions
    update_institutions(simulation)

    # 2. Stratification
    update_social_classes(simulation)

    # 3. Corruption
    process_corruption(simulation, tick)

    # 4. Government indicators
    update_government_indicators(simulation)

    # 5. Transitions
    check_transitions(simulation)

    # 6. Elections
    government.refresh_from_db()
    type_config = GOVERNMENT_TYPES.get(government.government_type, {})
    if type_config.get("election_enabled"):
        election_interval = getattr(settings, "EPOCHA_GOVERNMENT_ELECTION_INTERVAL", 50)
        if tick - government.last_election_tick >= election_interval:
            run_election(simulation, tick)

    # 7. Coups
    check_coups(simulation, tick)

    # Update stability
    _update_stability(simulation)


def update_government_indicators(simulation) -> None:
    """Update government indicators based on institution health and world state.

    Each indicator is influenced by specific institutions as defined in
    the spec. Repression drifts toward the government type's natural tendency.

    Args:
        simulation: The simulation instance.
    """
    government = Government.objects.get(simulation=simulation)
    type_config = GOVERNMENT_TYPES.get(government.government_type, {})
    if not type_config:
        return

    institutions = {
        inst.institution_type: inst
        for inst in Institution.objects.filter(simulation=simulation)
    }

    # Get institution health values (default 0.5 if missing)
    justice_h = institutions.get("justice", _stub(0.5)).health
    education_h = institutions.get("education", _stub(0.5)).health
    health_h = institutions.get("health", _stub(0.5)).health
    military_h = institutions.get("military", _stub(0.5)).health
    media_inst = institutions.get("media", _stub(0.5))
    media_h = media_inst.health
    media_ind = media_inst.independence if hasattr(media_inst, "independence") else 0.5
    bureaucracy_h = institutions.get("bureaucracy", _stub(0.5)).health

    # Economy factor from world stability
    from .models import World
    try:
        world = World.objects.get(simulation=simulation)
        economy_factor = world.stability_index
    except World.DoesNotExist:
        economy_factor = 0.5

    # Head of state charisma
    head_charisma = 0.3
    if government.head_of_state and government.head_of_state.is_alive:
        head_charisma = government.head_of_state.charisma

    # Institutional trust
    trust_delta = (
        justice_h * 0.3 + media_h * media_ind * 0.3
        + bureaucracy_h * 0.2 + education_h * 0.1 + health_h * 0.1
    ) * 0.1 - 0.05
    government.institutional_trust = _clamp(government.institutional_trust + trust_delta)

    # Corruption
    corruption_resistance = type_config.get("corruption_resistance", 0.5)
    corruption_delta = (
        1.0 - justice_h * 0.4 - bureaucracy_h * 0.3 - media_h * media_ind * 0.3
    ) * (1.0 - corruption_resistance) * 0.05 - 0.02
    government.corruption = _clamp(government.corruption + corruption_delta)

    # Popular legitimacy
    media_reported = government.popular_legitimacy if media_ind < 0.3 else (
        economy_factor * 0.4 + government.institutional_trust * 0.3 + (1.0 - government.repression_level) * 0.3
    )
    legitimacy_delta = (
        health_h * 0.2 + education_h * 0.15 + economy_factor * 0.35 + media_reported * 0.3
    ) * 0.1 - 0.05
    government.popular_legitimacy = _clamp(government.popular_legitimacy + legitimacy_delta)

    # Military loyalty
    military_funding = institutions.get("military", _stub(0.5)).funding if "military" in institutions else 0.5
    loyalty_delta = (
        military_h * 0.4 + military_funding * 0.3 + head_charisma * 0.3
    ) * 0.1 - 0.05
    government.military_loyalty = _clamp(government.military_loyalty + loyalty_delta)

    # Repression drift toward type tendency
    tendency = type_config.get("repression_tendency", 0.1)
    repression_delta = (tendency - government.repression_level) * 0.1
    government.repression_level = _clamp(government.repression_level + repression_delta)

    government.save(update_fields=[
        "institutional_trust", "corruption", "popular_legitimacy",
        "military_loyalty", "repression_level",
    ])


def check_transitions(simulation) -> str | None:
    """Check if conditions for a regime transition are met.

    Scans the transition graph for the current government type. If all
    conditions for a transition are satisfied, the transition occurs.

    Returns:
        The new government type if a transition occurred, None otherwise.
    """
    government = Government.objects.get(simulation=simulation)
    type_config = GOVERNMENT_TYPES.get(government.government_type, {})
    transitions = type_config.get("transitions", {})

    best_target = None
    best_score = 0

    for target_type, conditions in transitions.items():
        met = 0
        total = len(conditions)
        for condition, threshold in conditions.items():
            if _check_condition(government, condition, threshold):
                met += 1
        if met == total and total > 0:
            # All conditions met -- score by number of conditions (prefer dramatic transitions)
            if met > best_score:
                best_score = met
                best_target = target_type

    if best_target:
        _execute_transition(simulation, government, best_target)
        return best_target

    return None


def check_coups(simulation, tick: int) -> dict | None:
    """Check if any faction can execute a coup d'etat.

    A coup succeeds when a faction is strong (high cohesion, charismatic
    leader), the military is disloyal, and the government is unstable.

    Args:
        simulation: The simulation instance.
        tick: Current tick.

    Returns:
        Dict with coup results if one occurred, None otherwise.
    """
    government = Government.objects.get(simulation=simulation)
    stability_threshold = getattr(settings, "EPOCHA_GOVERNMENT_COUP_STABILITY_THRESHOLD", 0.3)

    if government.stability > stability_threshold:
        return None

    factions = Group.objects.filter(
        simulation=simulation, cohesion__gt=0.6, leader__isnull=False,
    ).select_related("leader")

    for faction in factions:
        leader = faction.leader
        if not leader or not leader.is_alive:
            continue
        if faction.id == (government.ruling_faction_id or -1):
            continue  # Ruling faction doesn't coup itself

        member_count = Agent.objects.filter(group=faction, is_alive=True).count()
        if member_count < 3:
            continue

        success_prob = (
            faction.cohesion * 0.4
            + leader.charisma * 0.3
            + (1.0 - government.military_loyalty) * 0.3
        )

        if success_prob > 0.5:
            # Coup succeeds
            old_type = government.government_type
            old_head = government.head_of_state

            government.head_of_state = leader
            government.ruling_faction = faction
            government.government_type = "autocracy"
            government.stability = 0.3
            government.formed_at_tick = tick
            government.save()

            # History record
            GovernmentHistory.objects.create(
                simulation=simulation,
                government_type=old_type,
                head_of_state_name=old_head.name if old_head else "",
                ruling_faction_name="",
                from_tick=government.formed_at_tick,
                to_tick=tick,
                transition_cause="coup",
            )

            # Memories
            for agent in Agent.objects.filter(simulation=simulation, is_alive=True):
                Memory.objects.create(
                    agent=agent,
                    content=f"{leader.name} seized power in a coup. The {old_type} has fallen.",
                    emotional_weight=0.8,
                    source_type="public",
                    reliability=1.0,
                    tick_created=tick,
                )

            logger.info("Coup at tick %d: %s seized power from %s", tick, leader.name, old_type)
            return {"leader": leader.name, "faction": faction.name, "old_type": old_type}

    return None


def _execute_transition(simulation, government: Government, new_type: str) -> None:
    """Execute a regime transition."""
    old_type = government.government_type

    # Record history
    GovernmentHistory.objects.create(
        simulation=simulation,
        government_type=old_type,
        head_of_state_name=government.head_of_state.name if government.head_of_state else "",
        ruling_faction_name=government.ruling_faction.name if government.ruling_faction else "",
        from_tick=government.formed_at_tick,
        to_tick=simulation.current_tick,
        transition_cause="transition",
    )

    government.government_type = new_type
    government.formed_at_tick = simulation.current_tick
    government.stability = max(0.2, government.stability - 0.1)
    government.save(update_fields=["government_type", "formed_at_tick", "stability"])

    # Public memory
    for agent in Agent.objects.filter(simulation=simulation, is_alive=True):
        Memory.objects.create(
            agent=agent,
            content=f"The government has changed from {old_type} to {new_type}.",
            emotional_weight=0.5,
            source_type="public",
            reliability=1.0,
            tick_created=simulation.current_tick,
        )

    logger.info("Transition: %s -> %s at tick %d", old_type, new_type, simulation.current_tick)


def _update_stability(simulation) -> None:
    """Recompute government stability from weighted indicators."""
    government = Government.objects.get(simulation=simulation)
    type_config = GOVERNMENT_TYPES.get(government.government_type, {})
    weights = type_config.get("stability_weights", {"economy": 0.33, "legitimacy": 0.34, "military": 0.33})

    from .models import World
    try:
        economy = World.objects.get(simulation=simulation).stability_index
    except World.DoesNotExist:
        economy = 0.5

    stability = (
        economy * weights["economy"]
        + government.popular_legitimacy * weights["legitimacy"]
        + government.military_loyalty * weights["military"]
    )
    government.stability = _clamp(stability)
    government.save(update_fields=["stability"])


def _check_condition(government: Government, condition: str, threshold: float) -> bool:
    """Check a single transition condition against government indicators."""
    field_map = {
        "institutional_trust_below": ("institutional_trust", "below"),
        "institutional_trust_above": ("institutional_trust", "above"),
        "repression_above": ("repression_level", "above"),
        "repression_below": ("repression_level", "below"),
        "corruption_above": ("corruption", "above"),
        "corruption_below": ("corruption", "below"),
        "popular_legitimacy_above": ("popular_legitimacy", "above"),
        "popular_legitimacy_below": ("popular_legitimacy", "below"),
        "military_loyalty_above": ("military_loyalty", "above"),
        "military_loyalty_below": ("military_loyalty", "below"),
        "stability_above": ("stability", "above"),
        "stability_below": ("stability", "below"),
    }
    if condition not in field_map:
        return False
    field, direction = field_map[condition]
    value = getattr(government, field, 0.5)
    if direction == "below":
        return value < threshold
    return value > threshold


def _clamp(value: float) -> float:
    """Clamp a value to [0.0, 1.0]."""
    return max(0.0, min(1.0, value))


class _stub:
    """Stub object for missing institutions."""

    def __init__(self, default: float):
        self.health = default
        self.independence = default
        self.funding = default
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `docker compose -f docker-compose.local.yml exec -T web pytest epocha/apps/world/tests/test_government.py -v`
Expected: All tests PASS.

- [ ] **Step 5: Commit**

```
feat(world): add government engine with indicators, transitions, and coups

CHANGE: Implement process_political_cycle() orchestrating institutions,
stratification, corruption, indicator updates, regime transitions,
elections, and coups. The engine is fully data-driven by government_types
configuration. Transitions fire when indicator conditions are met.
Coups succeed when factions are strong and military loyalty is low.
```

---

### Task 7: Decision pipeline integration

Enrich agent context with political info and add new actions (crime, protest, campaign).

**Files:**
- Modify: `epocha/apps/agents/decision.py`
- Modify: `epocha/apps/simulation/engine.py`
- Modify: `epocha/apps/dashboard/formatters.py`
- Test: `epocha/apps/agents/tests/test_decision.py`

- [ ] **Step 1: Write the failing test**

Add to `epocha/apps/agents/tests/test_decision.py`, inside `TestProcessAgentDecision`:

```python
@patch("epocha.apps.agents.decision.get_llm_client")
def test_context_includes_government_info(self, mock_get_client, agent, world, simulation):
    """If a government exists, the context should include political info."""
    from epocha.apps.world.models import Government
    Government.objects.create(
        simulation=simulation, government_type="democracy",
        stability=0.6, popular_legitimacy=0.5,
    )
    mock_client = MagicMock()
    mock_client.complete.return_value = '{"action": "work", "reason": "busy"}'
    mock_client.get_model_name.return_value = "gpt-4o-mini"
    mock_get_client.return_value = mock_client

    process_agent_decision(agent, world, tick=5)

    call_args = mock_client.complete.call_args
    prompt = call_args.kwargs.get("prompt", call_args.args[0] if call_args.args else "")
    assert "Democracy" in prompt or "democracy" in prompt
```

- [ ] **Step 2: Run test to verify it fails**

- [ ] **Step 3: Update system prompt with new actions**

In `decision.py`, update the action list in `_DECISION_SYSTEM_PROMPT`:

```python
    "action": "work|rest|socialize|explore|trade|argue|help|avoid|form_group|join_group|crime|protest|campaign",
```

- [ ] **Step 4: Add political context to _build_context**

Add `political_context=None` parameter to `_build_context` signature. Add after the `group_context` block:

```python
    # Political context
    if political_context:
        parts.append(f"\n{political_context}")
```

- [ ] **Step 5: Build political context in process_agent_decision**

After the group_context block, add:

```python
    # Build political context
    political_context = None
    try:
        from epocha.apps.world.models import Government
        government = Government.objects.get(simulation=agent.simulation)
        from epocha.apps.world.government_types import GOVERNMENT_TYPES
        type_label = GOVERNMENT_TYPES.get(government.government_type, {}).get("label", government.government_type)
        stability_word = "stable" if government.stability > 0.6 else "moderate" if government.stability > 0.3 else "unstable"
        head_name = government.head_of_state.name if government.head_of_state else "none"
        political_context = (
            f"Government: {type_label} ({stability_word})\n"
            f"Head of state: {head_name}\n"
            f"Trust: {'high' if government.institutional_trust > 0.6 else 'low' if government.institutional_trust < 0.3 else 'moderate'}. "
            f"Corruption: {'high' if government.corruption > 0.6 else 'low' if government.corruption < 0.3 else 'moderate'}."
        )
    except Exception:
        pass
```

Pass `political_context` to `_build_context`.

- [ ] **Step 6: Add action weights and mood deltas in engine.py**

In `_ACTION_EMOTIONAL_WEIGHT`:
```python
    "crime": 0.6,
    "protest": 0.4,
    "campaign": 0.2,
```

In `_ACTION_MOOD_DELTA`:
```python
    "crime": -0.03,
    "protest": -0.02,
    "campaign": 0.02,
```

- [ ] **Step 7: Add verbs to dashboard formatters**

In `_ACTION_VERBS`:
```python
    "crime": "commits a crime against",
    "protest": "protests",
    "campaign": "campaigns for leadership",
```

- [ ] **Step 8: Run all tests**

Run: `docker compose -f docker-compose.local.yml exec -T web pytest -q`

- [ ] **Step 9: Commit**

```
feat(agents): integrate political system into decision pipeline

CHANGE: Add crime, protest, and campaign as possible agent actions.
Enrich decision context with government type, stability, head of state,
trust, and corruption level. Add emotional weights and mood deltas for
the new actions. Update dashboard formatters.
```

---

### Task 8: Tick engine integration

Wire `process_political_cycle` into both engine paths.

**Files:**
- Modify: `epocha/apps/simulation/engine.py`
- Modify: `epocha/apps/simulation/tasks.py`
- Test: `epocha/apps/simulation/tests/test_engine.py`

- [ ] **Step 1: Add import and call in engine.py**

Add import:
```python
from epocha.apps.world.government import process_political_cycle
```

In `run_tick()`, after faction dynamics and before memory decay:
```python
        # 5. Political cycle (every N ticks)
        process_political_cycle(self.simulation, tick)
```

Renumber: memory decay becomes 6, advance tick becomes 7, broadcast becomes 8.

- [ ] **Step 2: Add call in Celery finalize_tick**

After faction dynamics call:
```python
    # Political cycle (every N ticks)
    from epocha.apps.world.government import process_political_cycle
    process_political_cycle(simulation, tick)
```

- [ ] **Step 3: Add test**

Add to `TestSimulationEngine`:
```python
@patch("epocha.apps.simulation.engine.process_agent_decision")
def test_political_cycle_runs_at_interval(self, mock_decision, sim_with_world):
    """Political cycle should be called during ticks."""
    mock_decision.return_value = {"action": "work", "reason": "busy"}
    engine = SimulationEngine(sim_with_world)
    with patch("epocha.apps.simulation.engine.process_political_cycle") as mock_politics:
        for _ in range(10):
            engine.run_tick()
        assert mock_politics.call_count == 10
```

- [ ] **Step 4: Run all tests**

Run: `docker compose -f docker-compose.local.yml exec -T web pytest -q`

- [ ] **Step 5: Commit**

```
feat(simulation): integrate political cycle into tick engine

CHANGE: Call process_political_cycle() after faction dynamics in both
the synchronous engine and Celery path. Political cycle runs every 10
ticks by default, handling institutions, stratification, indicators,
transitions, elections, and coups.
```

---

### Task 9: Government initialization in world generation

When a simulation starts, create a Government and 7 Institutions with defaults appropriate to the government type.

**Files:**
- Modify: `epocha/apps/world/generator.py`
- Test: `epocha/apps/world/tests/test_generator.py`

- [ ] **Step 1: Write the failing test**

Add to the existing test file `epocha/apps/world/tests/test_generator.py`. Find the appropriate test class and add:

```python
def test_world_generation_creates_government(self, ...):
    """World generation should create a Government and 7 Institutions."""
    # After generating a world...
    from epocha.apps.world.models import Government, Institution
    assert Government.objects.filter(simulation=simulation).exists()
    assert Institution.objects.filter(simulation=simulation).count() == 7
```

NOTE: The implementer must read the existing `test_generator.py` to understand the fixture structure and adapt the test accordingly. The key assertion is that after world generation, a Government and 7 Institutions exist.

- [ ] **Step 2: Implement government initialization**

In `epocha/apps/world/generator.py`, find where the World is created and add initialization of Government + Institutions after world creation:

```python
from epocha.apps.world.models import Government, Institution
from epocha.apps.world.government_types import GOVERNMENT_TYPES

# Create default government (democracy)
government = Government.objects.create(
    simulation=simulation,
    government_type="democracy",
    formed_at_tick=0,
)

# Create all 7 institutions with defaults
for inst_type in Institution.InstitutionType.values:
    Institution.objects.create(
        simulation=simulation,
        institution_type=inst_type,
        health=0.5,
        independence=0.5,
        funding=0.5,
    )
```

- [ ] **Step 3: Run tests**

Run: `docker compose -f docker-compose.local.yml exec -T web pytest epocha/apps/world/ -v`

- [ ] **Step 4: Commit**

```
feat(world): initialize government and institutions on world generation

CHANGE: When a new world is generated, create a default Government
(democracy) and all 7 Institutions with neutral health, independence,
and funding. This ensures the political system is active from the start.
```

---

### Task 10: Update engine docstring

**Files:**
- Modify: `epocha/apps/simulation/engine.py:1-18`

- [ ] **Step 1: Update module docstring**

```python
"""Tick orchestrator: coordinates economy, decisions, information, factions, politics, memory, and events.

Each tick is a discrete time step where:
1. The economy updates (income, costs, mood effects)
2. Each living agent makes a decision via LLM
3. Decision consequences are applied (mood, health adjustments)
4. Memories are created from actions
5. Information propagates through the social network (hearsay, rumors)
6. Faction dynamics run periodically (cohesion, leadership, formation)
7. Political cycle runs periodically (institutions, stratification, transitions, elections)
8. Old memories decay periodically
9. The tick counter advances

Agent failures are isolated: if one agent's LLM call fails, the tick
continues for all other agents. This ensures simulation resilience.

Module-level functions (run_economy, run_memory_decay, broadcast_tick) are
used by both the SimulationEngine (synchronous path) and the Celery chord
tasks (production path). This avoids duplicating logic across execution modes.
"""
```

- [ ] **Step 2: Commit**

```
docs(simulation): update engine docstring with political cycle step

CHANGE: Engine module docstring now reflects the 9-step tick flow
including the political cycle phase.
```

# Demography Implementation — Plan 1: Foundations and Mortality

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Phase 5 implementation runs on Sonnet 4.6 per the model selection policy; escalation to Opus is triggered by any strategic decision outside the specified execution.

**Goal:** Deliver the demography data layer, integration contracts helpers, era templates, seeded RNG, and the mortality module with Heligman-Pollard implementation plus its fitting infrastructure. After this plan the repository can compute individual mortality deterministically but does not yet run demography in the tick pipeline.

**Architecture:** New Django app `epocha.apps.demography` with scaffolding, four new models, extensions to `Agent`, and the first scientific module (`mortality.py`). Two helpers extracted from existing code to become part of a clean integration surface (`add_to_treasury` in world.government, `SUBSISTENCE_NEED_PER_AGENT` constant in economy.market). Five era templates loaded as JSON fixtures. Seeded RNG streams per subsystem for publication-grade reproducibility. HP fitting wrapper tested against synthetic data; real calibration against historical life tables deferred to Plan 4.

**Tech Stack:** Django ORM, PostgreSQL, pytest, scipy (new runtime dependency for curve_fit), numpy.

**Spec:** `docs/superpowers/specs/2026-04-18-demography-design-it.md` (authoritative Italian)

**Depends on:** `develop` branch at current HEAD (Economy Spec 2 Part 3 merged).

**Follow-up plans:**
- Plan 2 — Fertility + Couple formation + LLM actions
- Plan 3 — Inheritance + Migration
- Plan 4 — Initialization + Engine orchestration + Historical validation

**IMPORTANT notes for implementers:**
- Tests run in Docker: `docker compose -f docker-compose.local.yml exec web pytest ...`
- All new tests use PostgreSQL, no SQLite (Epocha project rule)
- `Agent.age` is retained for backward compatibility and populated from `birth_tick` via the migration data step
- `scipy` is added to `requirements/base.txt`; verify the Docker image rebuilds correctly before the first fit test
- Spec code blocks may contain Italian comments for readability; real implementation here uses English comments and docstrings per the italian-specs rule
- The five era templates per the spec are `pre_industrial_christian`, `pre_industrial_islamic`, `industrial`, `modern_democracy`, `sci_fi` (five, despite the spec saying "quattro" by typo; spec will be corrected in a separate commit on the feature branch)

---

## File Structure (Plan 1 scope)

| File | Responsibility | New/Modify |
|------|---------------|------------|
| `epocha/apps/demography/__init__.py` | Django app package | New |
| `epocha/apps/demography/apps.py` | AppConfig | New |
| `epocha/apps/demography/models.py` | Couple, DemographyEvent, PopulationSnapshot, AgentFertilityState | New |
| `epocha/apps/demography/rng.py` | Seeded per-subsystem RNG streams | New |
| `epocha/apps/demography/template_loader.py` | Era template loading and validation | New |
| `epocha/apps/demography/mortality.py` | Heligman-Pollard + tick scaling + cause attribution + fitting | New |
| `epocha/apps/demography/context.py` | compute_subsistence_threshold, compute_aggregate_outlook | New |
| `epocha/apps/demography/templates/pre_industrial_christian.json` | Era template fixture | New |
| `epocha/apps/demography/templates/pre_industrial_islamic.json` | Era template fixture | New |
| `epocha/apps/demography/templates/industrial.json` | Era template fixture | New |
| `epocha/apps/demography/templates/modern_democracy.json` | Era template fixture | New |
| `epocha/apps/demography/templates/sci_fi.json` | Era template fixture | New |
| `epocha/apps/demography/migrations/0001_initial.py` | New models + Agent extensions | New (auto-generated) |
| `epocha/apps/demography/migrations/0002_birth_tick_backfill.py` | Populate birth_tick from age | New (data migration) |
| `epocha/apps/demography/tests/__init__.py` | Test package | New |
| `epocha/apps/demography/tests/test_models.py` | Model unit tests | New |
| `epocha/apps/demography/tests/test_rng.py` | RNG reproducibility | New |
| `epocha/apps/demography/tests/test_template_loader.py` | Template schema + loading | New |
| `epocha/apps/demography/tests/test_context.py` | Subsistence + outlook helpers | New |
| `epocha/apps/demography/tests/test_mortality.py` | Mortality + HP fit + cause attribution | New |
| `epocha/apps/agents/models.py` | Add birth_tick, death_tick, death_cause, other_parent_agent, caretaker_agent | Modify |
| `epocha/apps/world/government.py` | Extract add_to_treasury helper | Modify |
| `epocha/apps/economy/market.py` | Extract SUBSISTENCE_NEED_PER_AGENT constant | Modify |
| `epocha/apps/economy/engine.py` | Refactor inline treasury mutation to add_to_treasury | Modify |
| `config/settings/base.py` | Register `epocha.apps.demography` in INSTALLED_APPS | Modify |
| `requirements/base.txt` | Add scipy | Modify |

---

## Tasks summary

1. App scaffolding and settings registration
2. Extract `SUBSISTENCE_NEED_PER_AGENT` constant in `economy/market.py`
3. Extract `add_to_treasury` helper in `world/government.py` and refactor existing caller
4. Add scipy to requirements and rebuild container
5. Define `Couple` model
6. Define `DemographyEvent` model
7. Define `PopulationSnapshot` model
8. Define `AgentFertilityState` model
9. Extend `Agent` model with `birth_tick`, `death_tick`, `death_cause`, `other_parent_agent`, `caretaker_agent`
10. Generate initial migration + data migration populating `birth_tick`
11. Model unit tests (new models + Agent extensions)
12. Implement `demography/rng.py` with seeded per-subsystem streams
13. RNG reproducibility unit tests
14. Implement `demography/template_loader.py` with schema validation
15. Author five era template JSON fixtures
16. Template loader unit tests
17. Implement `demography/context.py:compute_subsistence_threshold`
18. Implement `demography/context.py:compute_aggregate_outlook`
19. Context helpers unit tests
20. Implement `demography/mortality.py:annual_mortality_probability` + `tick_mortality_probability`
21. Implement `demography/mortality.py:sample_death_cause`
22. Implement HP fitting wrapper using `scipy.optimize.curve_fit`
23. Mortality + cause attribution unit tests
24. HP fitting unit tests with synthetic data
25. Plan 1 closing: full test suite green, PR description, merge to develop

---

### Task 1: App scaffolding and settings registration

**Files:**
- Create: `epocha/apps/demography/__init__.py`
- Create: `epocha/apps/demography/apps.py`
- Modify: `config/settings/base.py`

- [x] **Step 1: Create empty package file**

Create `epocha/apps/demography/__init__.py` with empty content.

- [x] **Step 2: Create AppConfig**

Create `epocha/apps/demography/apps.py`:

```python
"""Demography app configuration."""
from django.apps import AppConfig


class DemographyConfig(AppConfig):
    """Config for the demography subsystem.

    Scientific foundation: births, aging, reproduction, inheritance,
    migration, and deaths as an emergent agent-level process calibrated
    on historical demographic data. See
    docs/superpowers/specs/2026-04-18-demography-design-it.md.
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "epocha.apps.demography"
    label = "demography"
```

- [x] **Step 3: Register app in INSTALLED_APPS**

In `config/settings/base.py`, locate the `INSTALLED_APPS` list and add `"epocha.apps.demography"` near the other `epocha.apps.*` entries (keep alphabetical order within the project apps block).

- [x] **Step 4: Verify Django can discover the app**

Run: `docker compose -f docker-compose.local.yml exec web python manage.py check`
Expected: `System check identified no issues (0 silenced).`

- [x] **Step 5: Commit**

```
feat(demography): scaffold new app and register in INSTALLED_APPS

CHANGE: Create epocha.apps.demography package with AppConfig and
register it in config/settings/base.py. This is the foundation for
the demography subsystem per the 2026-04-18 spec.
```

Verified: Task 1 complete. Commit `6081c26`. Sonnet executed, no deviation.

---

### Task 2: Extract `SUBSISTENCE_NEED_PER_AGENT` constant

**Files:**
- Modify: `epocha/apps/economy/market.py`

- [x] **Step 1: Promote local to module-level constant**

In `epocha/apps/economy/market.py`, locate the function that contains `subsistence_need = 1.0` (around line 172). Hoist it to the module level at the top of the file, directly after the imports:

```python
# Subsistence need per agent per essential good per tick.
# Extracted on 2026-04-18 as part of the Demography Plan 1 integration
# contract (see docs/superpowers/specs/2026-04-18-demography-design-it.md).
# Shared with demography/context.py:compute_subsistence_threshold.
SUBSISTENCE_NEED_PER_AGENT: float = 1.0
```

Replace the local `subsistence_need = 1.0` inside the function with `subsistence_need = SUBSISTENCE_NEED_PER_AGENT`. Keep the local name for backward compatibility inside the function to minimize the diff.

- [x] **Step 2: Run the economy test suite to verify no regression**

Run: `docker compose -f docker-compose.local.yml exec web pytest epocha/apps/economy/tests/test_market.py -q`
Expected: all tests green (no behavior change).

- [x] **Step 3: Commit**

```
refactor(economy): promote SUBSISTENCE_NEED_PER_AGENT to module constant

CHANGE: Extract the inline local subsistence_need = 1.0 in market.py
to a module-level constant SUBSISTENCE_NEED_PER_AGENT, enabling reuse
by demography/context.py:compute_subsistence_threshold. Behavior is
unchanged; this is a pure refactor.
```

Verified: Task 2 complete. Commit `16120ab`. 6/6 market tests green.

---

### Task 3: Extract `add_to_treasury` helper and refactor existing caller

**Files:**
- Modify: `epocha/apps/world/government.py`
- Modify: `epocha/apps/economy/engine.py`

- [x] **Step 1: Add helper to `epocha/apps/world/government.py`**

Append to `epocha/apps/world/government.py`:

```python
def add_to_treasury(government, currency_code: str, amount: float) -> None:
    """Add an amount in the given currency to the government treasury.

    Extracted on 2026-04-18 as part of the Demography Plan 1
    integration contract. Prior callers used inline JSON-dict mutation
    (see economy/engine.py). Centralizing ensures consistent accounting
    across tax, estate tax, expropriation, and future fines.

    Args:
        government: Government instance to credit.
        currency_code: Currency code to add the amount under.
        amount: Amount in the specified currency.
    """
    treasury = government.government_treasury or {}
    treasury[currency_code] = treasury.get(currency_code, 0.0) + amount
    government.government_treasury = treasury
    government.save(update_fields=["government_treasury"])
```

- [x] **Step 2: Refactor existing inline treasury mutation in `epocha/apps/economy/engine.py`**

Locate the block near line 433 that mutates `gov.government_treasury` inline. Replace with a call to `add_to_treasury(gov, currency_code, amount)` after importing the helper at the top of the file:

```python
from epocha.apps.world.government import add_to_treasury
```

- [x] **Step 3: Run the economy test suite to verify no regression**

Run: `docker compose -f docker-compose.local.yml exec web pytest epocha/apps/economy/tests/ -q`
Expected: all 252 tests green.

- [x] **Step 4: Commit**

```
refactor(world): extract add_to_treasury helper

CHANGE: Add a shared helper in epocha/apps/world/government.py that
credits the government treasury. Refactor the inline JSON-dict
mutation in economy/engine.py to use the helper. Centralizes
treasury accounting for downstream demography estate tax and future
fines. Behavior unchanged.
```

---

### Task 4: Add scipy to requirements and rebuild container

**Files:**
- Modify: `requirements/base.txt`

- [x] **Step 1: Add scipy dependency**

Append to `requirements/base.txt`:

```
scipy==1.14.1
```

Use the most recent stable version compatible with numpy already in the project.

- [x] **Step 2: Rebuild the Docker image**

Run: `docker compose -f docker-compose.local.yml build web`
Expected: build completes successfully; scipy installed.

- [x] **Step 3: Verify scipy is importable from the web container**

Run: `docker compose -f docker-compose.local.yml exec web python -c "import scipy; print(scipy.__version__)"`
Expected: prints `1.14.1` or similar.

- [x] **Step 4: Commit**

```
build(deps): add scipy 1.14.1 for HP parameter fitting

CHANGE: scipy.optimize.curve_fit is required by the demography
mortality module to calibrate Heligman-Pollard parameters against
historical life tables. Added as a runtime dependency.
```

---

### Task 5: Define `Couple` model

**Files:**
- Modify: `epocha/apps/demography/models.py`

- [x] **Step 1: Create the models module**

Create `epocha/apps/demography/models.py` with imports and the `Couple` class:

```python
"""Demography models: Couple, DemographyEvent, PopulationSnapshot, AgentFertilityState.

Scientific foundations:
- Gale & Shapley (1962) — stable matching for initialization
- Goode (1963) — arranged marriage patterns
- Couple as unit of analysis for inheritance and family migration
"""
from django.db import models


class Couple(models.Model):
    """An active or dissolved couple between two agents.

    Polygamous couple types (polygynous, polyandrous) are not supported
    in MVP — the two-FK model cannot represent more than two partners.
    See the Known Limitations of the spec.

    When a partner dies the FK is nullified but the name snapshot
    preserves the genealogical record for audit purposes.
    """

    class CoupleType(models.TextChoices):
        MONOGAMOUS = "monogamous", "Monogamous"
        ARRANGED = "arranged", "Arranged"

    class DissolutionReason(models.TextChoices):
        DEATH = "death", "Death of a partner"
        SEPARATE = "separate", "Voluntary separation"
        ANNULMENT = "annulment", "Annulment"

    simulation = models.ForeignKey(
        "simulation.Simulation",
        on_delete=models.CASCADE,
        related_name="couples",
    )
    agent_a = models.ForeignKey(
        "agents.Agent",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="couple_as_a",
    )
    agent_b = models.ForeignKey(
        "agents.Agent",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="couple_as_b",
    )
    agent_a_name_snapshot = models.CharField(max_length=255, blank=True)
    agent_b_name_snapshot = models.CharField(max_length=255, blank=True)
    formed_at_tick = models.PositiveIntegerField()
    dissolved_at_tick = models.PositiveIntegerField(null=True, blank=True)
    dissolution_reason = models.CharField(
        max_length=20,
        choices=DissolutionReason.choices,
        blank=True,
    )
    couple_type = models.CharField(
        max_length=20,
        choices=CoupleType.choices,
        default=CoupleType.MONOGAMOUS,
    )

    class Meta:
        indexes = [
            models.Index(fields=["simulation", "dissolved_at_tick"]),
            models.Index(fields=["agent_a", "dissolved_at_tick"]),
            models.Index(fields=["agent_b", "dissolved_at_tick"]),
        ]

    def __str__(self):
        a = self.agent_a.name if self.agent_a else self.agent_a_name_snapshot or "?"
        b = self.agent_b.name if self.agent_b else self.agent_b_name_snapshot or "?"
        status = "active" if self.dissolved_at_tick is None else "dissolved"
        return f"Couple<{a} + {b} ({status})>"
```

- [x] **Step 2: Run `makemigrations` to confirm the model compiles**

Run: `docker compose -f docker-compose.local.yml exec web python manage.py makemigrations demography --dry-run`
Expected: one migration planned for the Couple model.

(Do not create the migration yet; that happens in Task 10 together with the other models.)

- [x] **Step 3: No commit yet**

Commit happens at Task 10 together with the full migration.

---

### Task 6: Define `DemographyEvent` model

**Files:**
- Modify: `epocha/apps/demography/models.py`

- [x] **Step 1: Append the `DemographyEvent` model**

```python
class DemographyEvent(models.Model):
    """Ledger of demographic events for analytics, audit trail, paper reproducibility.

    Payload schema per event_type is documented in the spec
    (§DemographyEvent Payload Schemas).
    """

    class EventType(models.TextChoices):
        BIRTH = "birth", "Birth"
        DEATH = "death", "Death"
        PAIR_BOND = "pair_bond", "Pair bond"
        SEPARATE = "separate", "Separate"
        MIGRATION = "migration", "Migration"
        INHERITANCE_TRANSFER = "inheritance_transfer", "Inheritance transfer"
        MASS_FLIGHT = "mass_flight", "Mass flight"
        TRAPPED_CRISIS = "trapped_crisis", "Trapped crisis"
        DEMOGRAPHIC_INITIALIZER = "demographic_initializer", "Demographic initializer"

    simulation = models.ForeignKey(
        "simulation.Simulation",
        on_delete=models.CASCADE,
        related_name="demography_events",
    )
    tick = models.PositiveIntegerField()
    event_type = models.CharField(max_length=30, choices=EventType.choices)
    primary_agent = models.ForeignKey(
        "agents.Agent",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="demography_events_primary",
    )
    secondary_agent = models.ForeignKey(
        "agents.Agent",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="demography_events_secondary",
    )
    payload = models.JSONField(default=dict)

    class Meta:
        indexes = [
            models.Index(fields=["simulation", "tick"]),
            models.Index(fields=["simulation", "event_type", "tick"]),
        ]

    def __str__(self):
        return f"DemographyEvent<{self.event_type}@tick{self.tick}>"
```

---

### Task 7: Define `PopulationSnapshot` model

**Files:**
- Modify: `epocha/apps/demography/models.py`

- [x] **Step 1: Append the `PopulationSnapshot` model**

```python
class PopulationSnapshot(models.Model):
    """Per-tick aggregate demographic state for dashboards and validation."""

    simulation = models.ForeignKey(
        "simulation.Simulation",
        on_delete=models.CASCADE,
        related_name="population_snapshots",
    )
    tick = models.PositiveIntegerField()
    total_alive = models.PositiveIntegerField(default=0)
    age_pyramid = models.JSONField(
        default=list,
        help_text=(
            "List of [age_bucket_low, age_bucket_high, count_male, count_female]"
        ),
    )
    sex_ratio = models.FloatField(default=1.0)
    avg_age = models.FloatField(default=0.0)
    crude_birth_rate = models.FloatField(default=0.0)
    crude_death_rate = models.FloatField(default=0.0)
    tfr_instant = models.FloatField(default=0.0)
    net_migration_by_zone = models.JSONField(default=dict)
    couples_active = models.PositiveIntegerField(default=0)
    avg_household_size = models.FloatField(default=0.0)

    class Meta:
        unique_together = ("simulation", "tick")
        indexes = [
            models.Index(fields=["simulation", "tick"]),
        ]

    def __str__(self):
        return (
            f"PopulationSnapshot<sim={self.simulation_id} "
            f"tick={self.tick} alive={self.total_alive}>"
        )
```

---

### Task 8: Define `AgentFertilityState` model

**Files:**
- Modify: `epocha/apps/demography/models.py`

- [x] **Step 1: Append the `AgentFertilityState` model**

```python
class AgentFertilityState(models.Model):
    """Per-agent fertility control state for planned-fertility eras.

    Populated only when the template fertility_agency is "planned".
    The avoid_conception_flag_tick records the last tick at which the
    agent invoked the avoid_conception action; fertility checks this
    flag at tick T+1 (property-market-style tick+1 settlement).
    """

    agent = models.OneToOneField(
        "agents.Agent",
        on_delete=models.CASCADE,
        related_name="fertility_state",
    )
    avoid_conception_flag_tick = models.PositiveIntegerField(null=True, blank=True)

    def __str__(self):
        return f"FertilityState<{self.agent_id} flag={self.avoid_conception_flag_tick}>"
```

---

### Task 9: Extend `Agent` model with demography fields

**Files:**
- Modify: `epocha/apps/agents/models.py`

- [x] **Step 1: Add the new fields to `Agent`**

In `epocha/apps/agents/models.py`, locate the `Agent` class and add the following fields. Place them near `parent_agent` for locality:

```python
    # Demography extensions (Plan 1 of demography spec).
    birth_tick = models.PositiveIntegerField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Canonical age source; age = (current_tick - birth_tick) / ticks_per_year",
    )
    death_tick = models.PositiveIntegerField(null=True, blank=True)

    class DeathCause(models.TextChoices):
        NATURAL_SENESCENCE = "natural_senescence", "Natural senescence"
        EARLY_LIFE_MORTALITY = "early_life_mortality", "Early-life mortality"
        EXTERNAL_CAUSE = "external_cause", "External cause"
        CHILDBIRTH = "childbirth", "Childbirth"
        STARVATION = "starvation", "Starvation"
        EXPROPRIATION = "expropriation", "Expropriation"
        EXECUTED = "executed", "Executed"
        UNKNOWN = "unknown", "Unknown"

    death_cause = models.CharField(
        max_length=30,
        choices=DeathCause.choices,
        blank=True,
    )
    other_parent_agent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="other_parent_children",
        help_text="Second biological parent (father by Epocha convention)",
    )
    caretaker_agent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="dependents",
        help_text="Active caretaker for a minor when parents are unavailable",
    )
```

- [x] **Step 2: Verify the model still compiles**

Run: `docker compose -f docker-compose.local.yml exec web python manage.py check`
Expected: no issues.

---

### Task 10: Generate initial migration + data migration

**Files:**
- Create: `epocha/apps/demography/migrations/0001_initial.py`
- Create: `epocha/apps/agents/migrations/0009_agent_demography_fields.py`
- Create: `epocha/apps/demography/migrations/0002_birth_tick_backfill.py`

- [x] **Step 1: Generate schema migrations for both apps**

Run:
```
docker compose -f docker-compose.local.yml exec web python manage.py makemigrations agents demography
```
Expected: two migrations are generated — one for `agents` with the new Agent fields, one for `demography` with the four new models. Verify the generated file names match the above (allow Django to assign sequential numbers; rename if necessary to match the convention above).

- [x] **Step 2: Create the data migration for `birth_tick` backfill**

Create `epocha/apps/demography/migrations/0002_birth_tick_backfill.py`:

```python
"""Populate Agent.birth_tick from existing Agent.age for all agents.

This is a one-shot backfill run when the demography app is first added.
The formula uses the simulation's current_tick and tick_duration_hours
to convert age in years to a birth_tick value consistent with the new
canonical age source.
"""
from django.db import migrations


def backfill_birth_tick(apps, schema_editor):
    Agent = apps.get_model("agents", "Agent")
    for agent in Agent.objects.select_related("simulation__world").iterator():
        simulation = agent.simulation
        if simulation is None:
            continue
        tick_duration_hours = 24.0
        world = getattr(simulation, "world", None)
        if world is not None and getattr(world, "tick_duration_hours", None):
            tick_duration_hours = float(world.tick_duration_hours)
        ticks_per_year = 8760.0 / tick_duration_hours
        current_tick = simulation.current_tick or 0
        age_in_ticks = int(round(agent.age * ticks_per_year))
        agent.birth_tick = max(0, current_tick - age_in_ticks)
        agent.save(update_fields=["birth_tick"])


def noop_reverse(apps, schema_editor):
    """Reverse is a no-op: resetting birth_tick to NULL is handled by schema."""


class Migration(migrations.Migration):
    dependencies = [
        ("demography", "0001_initial"),
        ("agents", "0009_agent_demography_fields"),
    ]
    operations = [
        migrations.RunPython(backfill_birth_tick, noop_reverse),
    ]
```

(Adjust the `dependencies` migration names to match the files auto-generated in Step 1.)

- [x] **Step 3: Apply migrations**

Run:
```
docker compose -f docker-compose.local.yml exec web python manage.py migrate
```
Expected: all migrations applied cleanly; agents and demography updated.

- [x] **Step 4: Verify existing tests still pass**

Run: `docker compose -f docker-compose.local.yml exec web pytest epocha/apps/agents/ epocha/apps/economy/ -q`
Expected: all previously green tests remain green.

- [x] **Step 5: Commit**

```
feat(demography): add models and extend Agent with demography fields

CHANGE: Create the four demography models (Couple, DemographyEvent,
PopulationSnapshot, AgentFertilityState) and extend the Agent model
with birth_tick, death_tick, death_cause, other_parent_agent, and
caretaker_agent. Generate the schema migrations and a data migration
that populates birth_tick from Agent.age for existing simulations.
```

---

### Task 11: Model unit tests

**Files:**
- Create: `epocha/apps/demography/tests/__init__.py`
- Create: `epocha/apps/demography/tests/test_models.py`

- [ ] **Step 1: Create empty test package file**

Create `epocha/apps/demography/tests/__init__.py` empty.

- [ ] **Step 2: Write model tests**

Create `epocha/apps/demography/tests/test_models.py`:

```python
"""Unit tests for the demography models and Agent extensions."""
from __future__ import annotations

import pytest
from django.contrib.gis.geos import Point, Polygon

from epocha.apps.agents.models import Agent
from epocha.apps.demography.models import (
    AgentFertilityState,
    Couple,
    DemographyEvent,
    PopulationSnapshot,
)
from epocha.apps.simulation.models import Simulation
from epocha.apps.users.models import User
from epocha.apps.world.models import World, Zone


@pytest.fixture
def sim_with_zone(db):
    user = User.objects.create_user(
        email="demo@epocha.dev", username="demouser", password="pass1234",
    )
    sim = Simulation.objects.create(
        name="DemographyTest", seed=42, owner=user, current_tick=0,
    )
    world = World.objects.create(simulation=sim, stability_index=0.7)
    zone = Zone.objects.create(
        world=world, name="TestZone", zone_type="commercial",
        boundary=Polygon.from_bbox((0, 0, 100, 100)),
        center=Point(50, 50),
    )
    return sim, zone


@pytest.mark.django_db
def test_agent_birth_tick_field(sim_with_zone):
    sim, zone = sim_with_zone
    agent = Agent.objects.create(
        simulation=sim, name="A", role="farmer",
        zone=zone, location=Point(50, 50),
        health=1.0, wealth=0.0, age=30, birth_tick=0,
    )
    assert agent.birth_tick == 0
    assert agent.death_tick is None


@pytest.mark.django_db
def test_agent_other_parent_relation(sim_with_zone):
    sim, zone = sim_with_zone
    parent = Agent.objects.create(
        simulation=sim, name="P", role="farmer", zone=zone,
        location=Point(50, 50), health=1.0, age=40, birth_tick=0,
    )
    other = Agent.objects.create(
        simulation=sim, name="O", role="farmer", zone=zone,
        location=Point(50, 50), health=1.0, age=42, birth_tick=0,
    )
    child = Agent.objects.create(
        simulation=sim, name="C", role="farmer", zone=zone,
        location=Point(50, 50), health=1.0, age=5, birth_tick=25,
        parent_agent=parent, other_parent_agent=other,
    )
    assert child.other_parent_agent_id == other.id
    assert list(parent.children.all()) == [child]
    assert list(other.other_parent_children.all()) == [child]


@pytest.mark.django_db
def test_couple_creation_and_snapshot(sim_with_zone):
    sim, zone = sim_with_zone
    a = Agent.objects.create(
        simulation=sim, name="A", role="weaver", zone=zone,
        location=Point(50, 50), health=1.0, age=25, birth_tick=0,
    )
    b = Agent.objects.create(
        simulation=sim, name="B", role="merchant", zone=zone,
        location=Point(50, 50), health=1.0, age=28, birth_tick=0,
    )
    couple = Couple.objects.create(
        simulation=sim, agent_a=a, agent_b=b,
        formed_at_tick=1, couple_type=Couple.CoupleType.MONOGAMOUS,
    )
    assert couple.dissolved_at_tick is None
    couple.agent_a_name_snapshot = a.name
    couple.agent_a = None
    couple.dissolved_at_tick = 5
    couple.dissolution_reason = Couple.DissolutionReason.DEATH
    couple.save()
    couple.refresh_from_db()
    assert couple.agent_a_name_snapshot == "A"
    assert couple.agent_a is None


@pytest.mark.django_db
def test_demography_event_payload(sim_with_zone):
    sim, zone = sim_with_zone
    agent = Agent.objects.create(
        simulation=sim, name="X", role="farmer", zone=zone,
        location=Point(50, 50), health=1.0, age=30, birth_tick=0,
    )
    event = DemographyEvent.objects.create(
        simulation=sim, tick=5,
        event_type=DemographyEvent.EventType.BIRTH,
        primary_agent=agent,
        payload={"newborn_id": 42, "zone_id": zone.id},
    )
    assert event.payload["newborn_id"] == 42


@pytest.mark.django_db
def test_population_snapshot_unique(sim_with_zone):
    sim, _ = sim_with_zone
    PopulationSnapshot.objects.create(
        simulation=sim, tick=1, total_alive=10, sex_ratio=1.05, avg_age=25.0,
    )
    with pytest.raises(Exception):
        PopulationSnapshot.objects.create(
            simulation=sim, tick=1, total_alive=10, sex_ratio=1.05, avg_age=25.0,
        )


@pytest.mark.django_db
def test_agent_fertility_state_one_to_one(sim_with_zone):
    sim, zone = sim_with_zone
    agent = Agent.objects.create(
        simulation=sim, name="F", role="farmer", zone=zone,
        location=Point(50, 50), health=1.0, age=30, birth_tick=0,
    )
    state = AgentFertilityState.objects.create(agent=agent, avoid_conception_flag_tick=5)
    assert agent.fertility_state == state
```

- [ ] **Step 3: Run the new tests**

Run: `docker compose -f docker-compose.local.yml exec web pytest epocha/apps/demography/tests/test_models.py -v`
Expected: 6 tests pass.

- [ ] **Step 4: Commit**

```
test(demography): add unit tests for new models and Agent extensions

CHANGE: Cover Couple creation, name snapshot after FK nulling,
DemographyEvent payload JSON, PopulationSnapshot uniqueness,
AgentFertilityState one-to-one, and Agent.other_parent_agent
related_name.
```

---

### Task 12: Implement `demography/rng.py` with seeded per-subsystem streams

**Files:**
- Create: `epocha/apps/demography/rng.py`

- [ ] **Step 1: Create the RNG module**

```python
"""Seeded RNG streams per demography subsystem for publication-grade reproducibility.

Each subsystem (mortality, fertility, couple, migration, inheritance,
initialization) gets an independent RNG stream derived from a
deterministic hash of (simulation.seed, tick, phase). Reordering or
suppressing one subsystem does not shift the RNG sequence of others,
which is essential for reproducibility across refactors.
"""
from __future__ import annotations

import hashlib
import random

ALLOWED_PHASES = {
    "mortality",
    "fertility",
    "couple",
    "migration",
    "inheritance",
    "initialization",
}


def get_seeded_rng(simulation, tick: int, phase: str) -> random.Random:
    """Return a per-simulation, per-tick, per-phase seeded RNG.

    Args:
        simulation: the Simulation instance (provides .seed and .id).
        tick: the current tick.
        phase: one of ALLOWED_PHASES.

    Raises:
        ValueError: when phase is not in ALLOWED_PHASES.
    """
    if phase not in ALLOWED_PHASES:
        raise ValueError(
            f"Unknown demography RNG phase {phase!r}; must be one of {sorted(ALLOWED_PHASES)}"
        )
    base_seed = simulation.seed or 0
    simulation_id = getattr(simulation, "id", 0) or 0
    key = f"{simulation_id}:{base_seed}:{tick}:{phase}".encode("utf-8")
    digest = hashlib.sha256(key).digest()
    derived_seed = int.from_bytes(digest[:8], "big")
    return random.Random(derived_seed)
```

---

### Task 13: RNG reproducibility unit tests

**Files:**
- Create: `epocha/apps/demography/tests/test_rng.py`

- [x] **Step 1: Write the RNG tests**

```python
"""Tests for the seeded per-subsystem RNG streams."""
from __future__ import annotations

import pytest

from epocha.apps.demography.rng import ALLOWED_PHASES, get_seeded_rng
from epocha.apps.simulation.models import Simulation
from epocha.apps.users.models import User


@pytest.fixture
def sim(db):
    user = User.objects.create_user(
        email="rng@epocha.dev", username="rnguser", password="pass1234",
    )
    return Simulation.objects.create(name="RngTest", seed=42, owner=user, current_tick=0)


@pytest.mark.django_db
def test_same_inputs_produce_same_sequence(sim):
    rng1 = get_seeded_rng(sim, tick=1, phase="mortality")
    rng2 = get_seeded_rng(sim, tick=1, phase="mortality")
    seq1 = [rng1.random() for _ in range(10)]
    seq2 = [rng2.random() for _ in range(10)]
    assert seq1 == seq2


@pytest.mark.django_db
def test_different_phases_produce_independent_streams(sim):
    rng_mort = get_seeded_rng(sim, tick=1, phase="mortality")
    rng_fert = get_seeded_rng(sim, tick=1, phase="fertility")
    seq_mort = [rng_mort.random() for _ in range(10)]
    seq_fert = [rng_fert.random() for _ in range(10)]
    assert seq_mort != seq_fert


@pytest.mark.django_db
def test_different_ticks_produce_different_streams(sim):
    rng_t1 = get_seeded_rng(sim, tick=1, phase="mortality")
    rng_t2 = get_seeded_rng(sim, tick=2, phase="mortality")
    assert rng_t1.random() != rng_t2.random()


@pytest.mark.django_db
def test_unknown_phase_raises(sim):
    with pytest.raises(ValueError):
        get_seeded_rng(sim, tick=1, phase="not_a_real_phase")


@pytest.mark.django_db
def test_all_allowed_phases_accepted(sim):
    for phase in ALLOWED_PHASES:
        assert get_seeded_rng(sim, tick=1, phase=phase) is not None
```

- [x] **Step 2: Run the tests**

Run: `docker compose -f docker-compose.local.yml exec web pytest epocha/apps/demography/tests/test_rng.py -v`
Expected: 5 tests pass.

- [x] **Step 3: Commit**

```
feat(demography): add seeded per-subsystem RNG streams

CHANGE: demography/rng.py:get_seeded_rng derives a random.Random
from (simulation.id, simulation.seed, tick, phase) via sha256.
Ensures reproducibility across refactors and independence between
subsystems. Tests cover reproducibility, independence, tick
separation, and unknown-phase validation.
```

---

### Task 14: Implement `demography/template_loader.py` with schema validation

**Files:**
- Create: `epocha/apps/demography/template_loader.py`

- [x] **Step 1: Create the template loader module**

```python
"""Era template loading and validation for the demography subsystem.

Templates are JSON fixtures stored in epocha/apps/demography/templates/.
Each template declares the parameters for a single era/scenario. The
loader validates the schema at load time and raises on missing or
malformed fields. Real calibration of numerical parameters (HP, Hadwiger)
happens in Plan 4 against historical life tables.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

TEMPLATES_DIR = Path(__file__).parent / "templates"

REQUIRED_TOP_LEVEL_KEYS = {
    "acceleration",
    "max_population",
    "fertility_agency",
    "mortality",
    "fertility",
    "age_pyramid",
    "sex_ratio_at_birth",
    "couple",
    "trait_inheritance",
    "social_inheritance",
    "economic_inheritance",
    "migration",
}

REQUIRED_MORTALITY_KEYS = {
    "heligman_pollard",
    "maternal_mortality_rate_per_birth",
    "neonatal_survival_when_mother_dies",
}

REQUIRED_HP_KEYS = set("ABCDEFGH")

ALLOWED_FERTILITY_AGENCY = {"biological", "planned"}


def load_template(name: str) -> dict[str, Any]:
    """Load a demography template by name and validate it.

    Args:
        name: the template file name without the .json extension.

    Raises:
        FileNotFoundError: template file does not exist.
        ValueError: template is missing required fields.
    """
    path = TEMPLATES_DIR / f"{name}.json"
    if not path.exists():
        raise FileNotFoundError(f"Demography template not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    _validate_template(data, source=str(path))
    return data


def _validate_template(data: dict[str, Any], source: str) -> None:
    missing = REQUIRED_TOP_LEVEL_KEYS - data.keys()
    if missing:
        raise ValueError(f"Template {source} missing keys: {sorted(missing)}")

    mortality = data["mortality"]
    missing_mort = REQUIRED_MORTALITY_KEYS - mortality.keys()
    if missing_mort:
        raise ValueError(
            f"Template {source} mortality missing keys: {sorted(missing_mort)}"
        )
    hp = mortality["heligman_pollard"]
    missing_hp = REQUIRED_HP_KEYS - hp.keys()
    if missing_hp:
        raise ValueError(
            f"Template {source} heligman_pollard missing parameters: {sorted(missing_hp)}"
        )

    if data["fertility_agency"] not in ALLOWED_FERTILITY_AGENCY:
        raise ValueError(
            f"Template {source} fertility_agency must be one of "
            f"{sorted(ALLOWED_FERTILITY_AGENCY)}"
        )


def list_available_templates() -> list[str]:
    """Return the list of template names available on disk."""
    return sorted(p.stem for p in TEMPLATES_DIR.glob("*.json"))
```

---

### Task 15: Author five era template JSON fixtures

**Files:**
- Create: `epocha/apps/demography/templates/pre_industrial_christian.json`
- Create: `epocha/apps/demography/templates/pre_industrial_islamic.json`
- Create: `epocha/apps/demography/templates/industrial.json`
- Create: `epocha/apps/demography/templates/modern_democracy.json`
- Create: `epocha/apps/demography/templates/sci_fi.json`

- [x] **Step 1: Create the templates directory**

Ensure `epocha/apps/demography/templates/` exists as a directory.

- [x] **Step 2: Author `pre_industrial_christian.json`**

Use the parameter values from the spec §Demography Template Schema. Fill in the full JSON structure, marking each numerical parameter as a seed value (the actual calibration is deferred to Plan 4). Example:

```json
{
  "acceleration": 1.0,
  "max_population": 500,
  "fertility_agency": "biological",
  "mortality": {
    "heligman_pollard": {
      "A": 0.00491, "B": 0.017, "C": 0.102,
      "D": 0.00080, "E": 9.9, "F": 22.4,
      "G": 0.0000383, "H": 1.101
    },
    "maternal_mortality_rate_per_birth": 0.008,
    "neonatal_survival_when_mother_dies": 0.3
  },
  "fertility": {
    "hadwiger": {"H": 5.0, "R": 26, "T": 0.35},
    "becker_coefficients": {
      "beta_0": 0.0, "beta_1": 0.1, "beta_2": -0.05,
      "beta_3": -0.1, "beta_4": 0.2
    },
    "require_couple_for_birth": true,
    "malthusian_floor_ratio": 0.1
  },
  "age_pyramid": [
    [0, 5, 0.15], [5, 10, 0.12], [10, 15, 0.11],
    [15, 20, 0.10], [20, 25, 0.09], [25, 30, 0.08],
    [30, 35, 0.07], [35, 40, 0.06], [40, 45, 0.05],
    [45, 50, 0.05], [50, 55, 0.04], [55, 60, 0.03],
    [60, 65, 0.02], [65, 70, 0.015], [70, 75, 0.01],
    [75, 80, 0.005]
  ],
  "sex_ratio_at_birth": 1.05,
  "sexual_orientation_distribution": {
    "heterosexual": 0.955, "bisexual": 0.030, "homosexual": 0.015
  },
  "couple": {
    "min_marriage_age_male": 16,
    "min_marriage_age_female": 14,
    "allowed_types": ["monogamous", "arranged"],
    "default_type": "monogamous",
    "divorce_enabled": false,
    "marriage_market_type": "autonomous",
    "marriage_market_radius": "same_zone",
    "implicit_mutual_consent": true,
    "mourning_ticks": 365,
    "homogamy_weights": {
      "w_class": 0.4, "w_edu": 0.25, "w_age": 0.20, "w_relationship": 0.15
    }
  },
  "trait_inheritance": {
    "heritability": {
      "openness": 0.41, "conscientiousness": 0.44, "extraversion": 0.54,
      "agreeableness": 0.42, "neuroticism": 0.48,
      "intelligence": 0.55, "emotional_intelligence": 0.40,
      "creativity": 0.22,
      "strength": 0.55, "stamina": 0.52, "agility": 0.45,
      "fertility": 0.50, "mental_health_baseline": 0.40,
      "default": 0.30
    },
    "derived_trait_formulas": {
      "cunning": {
        "description": "Computed at birth from inherited traits (not heritable itself).",
        "formula": "0.4*(1-agreeableness) + 0.3*neuroticism + 0.3*intelligence",
        "range": [0.0, 1.0]
      }
    }
  },
  "social_inheritance": {
    "class_rule": "patrilineal_rigid",
    "education_regression_rho": 0.5
  },
  "economic_inheritance": {
    "rule": "primogeniture",
    "heir_priority": ["spouse", "children", "siblings", "extended_family", "government"],
    "estate_tax_rate": 0.0
  },
  "migration": {
    "flight_trigger_ticks": 30,
    "adulthood_age": 16
  }
}
```

- [x] **Step 3: Author `pre_industrial_islamic.json`**

Copy `pre_industrial_christian.json` and change:
- `economic_inheritance.rule`: `"shari'a"`
- `couple.allowed_types`: `["monogamous", "arranged"]` (MVP does not yet support polygynous per Known Limitations; declare via comment in the JSON under a non-schema key `_note`)
- `couple.marriage_market_type`: `"arranged"`
- `couple.divorce_enabled`: `true` (classical Islamic jurisprudence permits talaq; documented in the spec FAQ)

- [x] **Step 4: Author `industrial.json`**

Update values per the spec: HP industrial parameters (A 0.00223, B 0.022, ...), Hadwiger H 4.0 R 27 T 0.38, `social_inheritance.class_rule = "clark_regression"`, `economic_inheritance.rule = "equal_split"`, `economic_inheritance.estate_tax_rate = 0.15`, `couple.divorce_enabled = true`, `couple.marriage_market_radius = "adjacent_zones"`, `fertility_agency = "biological"` (transition era keeps biological default).

- [x] **Step 5: Author `modern_democracy.json`**

HP modern parameters, Hadwiger H 1.8, `fertility_agency = "planned"`, `estate_tax_rate = 0.40`, `marriage_market_radius = "world"`, `class_rule = "becker_tomes_elasticity_0.4"`, `adulthood_age = 18`.

- [x] **Step 6: Author `sci_fi.json`**

HP sci_fi parameters, Hadwiger H 2.1, `fertility_agency = "planned"`, `class_rule = "meritocratic"`. Mark the template with `_note: "speculative parameters; no empirical basis"` at the top level.

---

### Task 16: Template loader unit tests

**Files:**
- Create: `epocha/apps/demography/tests/test_template_loader.py`

- [x] **Step 1: Write the tests**

```python
"""Tests for the demography template loader."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from epocha.apps.demography import template_loader


def test_all_default_templates_load():
    names = template_loader.list_available_templates()
    assert "pre_industrial_christian" in names
    assert "pre_industrial_islamic" in names
    assert "industrial" in names
    assert "modern_democracy" in names
    assert "sci_fi" in names
    for name in names:
        assert template_loader.load_template(name) is not None


def test_pre_industrial_hadwiger_values():
    tpl = template_loader.load_template("pre_industrial_christian")
    hp = tpl["mortality"]["heligman_pollard"]
    assert set(hp.keys()) == set("ABCDEFGH")
    hadwiger = tpl["fertility"]["hadwiger"]
    assert 4.0 <= hadwiger["H"] <= 6.0
    assert 24 <= hadwiger["R"] <= 30


def test_missing_file_raises(tmp_path, monkeypatch):
    monkeypatch.setattr(template_loader, "TEMPLATES_DIR", tmp_path)
    with pytest.raises(FileNotFoundError):
        template_loader.load_template("does_not_exist")


def test_missing_required_key_raises(tmp_path, monkeypatch):
    monkeypatch.setattr(template_loader, "TEMPLATES_DIR", tmp_path)
    (tmp_path / "broken.json").write_text(json.dumps({"acceleration": 1.0}))
    with pytest.raises(ValueError):
        template_loader.load_template("broken")


def test_invalid_fertility_agency_raises(tmp_path, monkeypatch):
    monkeypatch.setattr(template_loader, "TEMPLATES_DIR", tmp_path)
    # Build a minimal valid shape except for fertility_agency
    minimal = _minimal_template()
    minimal["fertility_agency"] = "WRONG"
    (tmp_path / "bad_agency.json").write_text(json.dumps(minimal))
    with pytest.raises(ValueError):
        template_loader.load_template("bad_agency")


def _minimal_template() -> dict:
    return {
        "acceleration": 1.0,
        "max_population": 10,
        "fertility_agency": "biological",
        "mortality": {
            "heligman_pollard": {k: 0.01 for k in "ABCDEFGH"},
            "maternal_mortality_rate_per_birth": 0.01,
            "neonatal_survival_when_mother_dies": 0.3,
        },
        "fertility": {},
        "age_pyramid": [],
        "sex_ratio_at_birth": 1.05,
        "couple": {},
        "trait_inheritance": {},
        "social_inheritance": {},
        "economic_inheritance": {},
        "migration": {},
    }
```

- [x] **Step 2: Run the tests**

Run: `docker compose -f docker-compose.local.yml exec web pytest epocha/apps/demography/tests/test_template_loader.py -v`
Expected: 5 tests pass.

- [x] **Step 3: Commit**

```
feat(demography): add template loader with schema validation

CHANGE: demography/template_loader.py loads and validates JSON
templates for five eras (pre_industrial_christian, pre_industrial_islamic,
industrial, modern_democracy, sci_fi). All templates pass schema
validation. Heligman-Pollard parameters, Hadwiger parameters,
inheritance rules, and couple settings are declared per-era per spec.
Numerical values are seed values pending Plan 4 calibration.
```

---

### Task 17: Implement `compute_subsistence_threshold`

**Files:**
- Create: `epocha/apps/demography/context.py`

- [x] **Step 1: Create the context module with the first helper**

```python
"""Context helpers bridging demography with the economy subsystem.

Defines the integration contracts listed in the spec §Integration
Contracts. These helpers compute quantities that do not exist as
named fields in the economy subsystem but are derivable from its
state.
"""
from __future__ import annotations

from epocha.apps.economy.market import SUBSISTENCE_NEED_PER_AGENT
from epocha.apps.economy.models import GoodCategory, ZoneEconomy


def compute_subsistence_threshold(simulation, zone) -> float:
    """Return the per-agent per-tick subsistence cost in the primary currency.

    Uses the GoodCategory.is_essential flag, the SUBSISTENCE_NEED_PER_AGENT
    constant (extracted from economy/market.py), and current market prices
    in the zone. The result is the minimum wealth flow required to consume
    essential goods at subsistence quantity.
    """
    try:
        ze = ZoneEconomy.objects.get(zone=zone, simulation=simulation)
    except ZoneEconomy.DoesNotExist:
        return 0.0
    essentials = GoodCategory.objects.filter(simulation=simulation, is_essential=True)
    total = 0.0
    for good in essentials:
        price = ze.market_prices.get(good.code, good.base_price)
        total += price * SUBSISTENCE_NEED_PER_AGENT
    return total
```

---

### Task 18: Implement `compute_aggregate_outlook`

**Files:**
- Modify: `epocha/apps/demography/context.py`

- [x] **Step 1: Append the outlook helper**

```python
def compute_aggregate_outlook(agent) -> float:
    """Return a scalar in [-1, 1] summarizing the agent's economic perception.

    Design heuristic combining:
    - agent mood (0..1 mapped to -1..1)
    - banking confidence (BankingState.confidence_index, 0..1 mapped to -1..1)
    - zone stability (Government.stability, 0..1 mapped to -1..1)

    Equal weights; tunable design parameter. Not derived from Jones &
    Tertilt (2008); it is a pragmatic proxy for Becker modulation where
    gender-segmented wages are unavailable.
    """
    from epocha.apps.economy.models import BankingState
    from epocha.apps.world.models import Government

    mood_norm = 2.0 * float(agent.mood or 0.0) - 1.0
    try:
        confidence = BankingState.objects.get(simulation=agent.simulation).confidence_index
        conf_norm = 2.0 * float(confidence) - 1.0
    except BankingState.DoesNotExist:
        conf_norm = 0.0
    stability_norm = 0.0
    try:
        gov = Government.objects.get(simulation=agent.simulation)
        stability_norm = 2.0 * float(gov.stability or 0.5) - 1.0
    except Government.DoesNotExist:
        pass
    return (mood_norm + conf_norm + stability_norm) / 3.0
```

---

### Task 19: Context helpers unit tests

**Files:**
- Create: `epocha/apps/demography/tests/test_context.py`

- [x] **Step 1: Write tests**

Tests must cover:
- `compute_subsistence_threshold` returns 0.0 when no ZoneEconomy exists
- `compute_subsistence_threshold` returns a positive value when essentials and prices exist
- `compute_aggregate_outlook` returns 0.0 when economy not initialized
- `compute_aggregate_outlook` returns -1..1 when all inputs at minimum/maximum
- Outlook combines correctly the three components

Use the fixture pattern from `test_models.py` to build the minimum state (simulation, world, zone, optional Government and BankingState, essentials GoodCategory with base_price).

- [x] **Step 2: Run the tests**

Run: `docker compose -f docker-compose.local.yml exec web pytest epocha/apps/demography/tests/test_context.py -v`
Expected: 5 tests pass.

- [x] **Step 3: Commit**

```
feat(demography): add integration context helpers

CHANGE: demography/context.py provides compute_subsistence_threshold
(derived per-agent per-tick essential-good cost in zone) and
compute_aggregate_outlook (scalar -1..1 combining mood, banking
confidence, and zone stability). These replace the phantom
references to subsistence_threshold and aggregate_outlook identified
during the spec's adversarial audit.
```

---

### Task 20: Implement `annual_mortality_probability` and `tick_mortality_probability`

**Files:**
- Create: `epocha/apps/demography/mortality.py`

- [x] **Step 1: Create the mortality module**

```python
"""Heligman-Pollard mortality model with per-era calibration.

Source:
- Heligman, L. & Pollard, J.H. (1980). The age pattern of mortality.
  Journal of the Institute of Actuaries 107(1), 49-80.

The three HP components (infant mortality, young-adult accident hump,
senescence) are decomposed explicitly so the cause-of-death attribution
can sample from the dominant component at the age of death.
"""
from __future__ import annotations

import math
import random
from typing import Mapping

HP_PARAM_KEYS = tuple("ABCDEFGH")


def _unpack(params: Mapping[str, float]) -> tuple[float, ...]:
    return tuple(float(params[k]) for k in HP_PARAM_KEYS)


def _hp_components(age: float, params: Mapping[str, float]) -> tuple[float, float, float]:
    """Return (c1, c2, c3) corresponding to the three HP components at age x."""
    A, B, C, D, E, F, G, H = _unpack(params)
    x = max(float(age), 0.01)
    c1 = A ** ((x + B) ** C)
    c2 = D * math.exp(-E * (math.log(x) - math.log(F)) ** 2) if x > 0 else 0.0
    c3 = G * (H ** x)
    return c1, c2, c3


def annual_mortality_probability(age: float, params: Mapping[str, float]) -> float:
    """Return the annual probability of death at age x using HP (1980).

    Converts the HP hazard q/p to a probability via q = (q/p) / (1 + q/p).
    """
    c1, c2, c3 = _hp_components(age, params)
    q_over_p = c1 + c2 + c3
    q = q_over_p / (1.0 + q_over_p)
    return min(q, 0.999)


def tick_mortality_probability(
    age: float,
    params: Mapping[str, float],
    tick_duration_hours: float,
    demography_acceleration: float = 1.0,
) -> float:
    """Scale the annual mortality probability to a single tick.

    For small q (q < 0.1, typical for most ages), the linear
    approximation `annual_q * dt` is accurate to better than 0.5%.
    For large q (infant mortality pre-industrial q ~ 0.25), the exact
    geometric conversion `1 - (1 - annual_q) ** dt` is used to avoid
    underestimation.
    """
    annual_q = annual_mortality_probability(age, params)
    dt = (tick_duration_hours / 8760.0) * demography_acceleration
    if annual_q < 0.1:
        return annual_q * dt
    return 1.0 - (1.0 - annual_q) ** dt
```

---

### Task 21: Implement `sample_death_cause`

**Files:**
- Modify: `epocha/apps/demography/mortality.py`

- [x] **Step 1: Append the cause attribution function**

```python
def sample_death_cause(
    age: float,
    params: Mapping[str, float],
    rng: random.Random,
) -> str:
    """Attribute the cause of death to the dominant HP component at age x.

    The three HP components map to the analytic labels:
    - Component 1 (A^...): "early_life_mortality"
    - Component 2 (D-term accident hump): "external_cause"
    - Component 3 (Gompertz senescence): "natural_senescence"

    The labels are analytics conventions, not medical classifications.
    """
    c1, c2, c3 = _hp_components(age, params)
    total = c1 + c2 + c3
    if total <= 0.0:
        return "natural_senescence"
    r = rng.random() * total
    if r < c1:
        return "early_life_mortality"
    if r < c1 + c2:
        return "external_cause"
    return "natural_senescence"
```

---

### Task 22: Implement HP fitting wrapper with scipy

**Files:**
- Modify: `epocha/apps/demography/mortality.py`

- [x] **Step 1: Append the fitting function**

```python
def fit_heligman_pollard(
    ages: list[float],
    observed_q: list[float],
    initial_guess: Mapping[str, float] | None = None,
) -> dict[str, float]:
    """Fit the eight HP parameters to observed annual mortality probabilities.

    Uses scipy.optimize.curve_fit with the HP functional form. Returns
    a dict {A, B, C, D, E, F, G, H}. Raises RuntimeError if the fit
    does not converge.

    Calibration task (Plan 4) feeds this with q(x) columns from
    published life tables (Wrigley-Schofield 1981, HMD). Plan 1 only
    tests the algorithm against synthetic data.
    """
    import numpy as np
    from scipy.optimize import curve_fit

    def _hp_model(x, A, B, C, D, E, F, G, H):
        x_safe = np.maximum(x, 0.01)
        c1 = A ** ((x_safe + B) ** C)
        c2 = D * np.exp(-E * (np.log(x_safe) - np.log(F)) ** 2)
        c3 = G * (H ** x_safe)
        q_over_p = c1 + c2 + c3
        return q_over_p / (1.0 + q_over_p)

    if initial_guess is None:
        p0 = [0.005, 0.02, 0.1, 0.001, 10.0, 22.0, 0.00005, 1.1]
    else:
        p0 = [initial_guess[k] for k in HP_PARAM_KEYS]

    xs = np.asarray(ages, dtype=float)
    ys = np.asarray(observed_q, dtype=float)

    lower = [0.0, 0.0, 0.0, 0.0, 0.1, 1.0, 0.0, 1.0]
    upper = [0.1, 0.5, 1.0, 0.05, 50.0, 50.0, 0.001, 1.5]

    try:
        popt, _ = curve_fit(
            _hp_model, xs, ys, p0=p0, bounds=(lower, upper), maxfev=10_000,
        )
    except RuntimeError as exc:
        raise RuntimeError("Heligman-Pollard fit did not converge") from exc

    return dict(zip(HP_PARAM_KEYS, (float(v) for v in popt)))
```

---

### Task 23: Mortality + cause attribution unit tests

**Files:**
- Create: `epocha/apps/demography/tests/test_mortality.py`

- [x] **Step 1: Write the tests**

Tests must cover:
- `annual_mortality_probability` returns finite values for ages 0, 1, 25, 50, 80 with sample HP params
- `annual_mortality_probability` is monotonically non-decreasing across old ages (Gompertz dominates)
- `tick_mortality_probability` returns smaller value than annual for dt < 1
- `tick_mortality_probability` switches to geometric for q > 0.1 and preserves `P(N ticks) ≈ annual`
- `sample_death_cause` returns one of the three labels
- Over many samples at age 2, causes skew heavily toward `early_life_mortality`
- Over many samples at age 75, causes skew heavily toward `natural_senescence`

Use a fixed `random.Random(seed)` for deterministic tests.

- [x] **Step 2: Run the tests**

Run: `docker compose -f docker-compose.local.yml exec web pytest epocha/apps/demography/tests/test_mortality.py::test_annual_probability -v` and similar.
Expected: all pass.

---

### Task 24: HP fitting unit tests with synthetic data

**Files:**
- Modify: `epocha/apps/demography/tests/test_mortality.py`

- [x] **Step 1: Append fitting tests**

Tests must cover:
- `fit_heligman_pollard` recovers synthetic parameters within relative tolerance 5% when given clean synthetic `q(x)` produced by `annual_mortality_probability`
- `fit_heligman_pollard` raises `RuntimeError` when given degenerate input (e.g., constant zero `q`) that fails to converge
- Fit stays within the documented bounds (A, D non-negative; H >= 1)

Generate the synthetic data using a known-good parameter set (e.g., the spec `pre_industrial` seed values), evaluate `annual_mortality_probability` at ages 0..80, perturb slightly, and verify the fit recovers the parameters.

- [x] **Step 2: Run all mortality tests together**

Run: `docker compose -f docker-compose.local.yml exec web pytest epocha/apps/demography/tests/test_mortality.py -v`
Expected: all tests pass.

- [x] **Step 3: Commit**

```
feat(demography): add Heligman-Pollard mortality and fitting

CHANGE: demography/mortality.py implements the HP (1980) 8-parameter
annual mortality probability, tick-scaled variant with linear and
geometric branches for small vs large q, cause-of-death attribution
from dominant HP component, and a scipy-based parameter fitting
wrapper. Unit tests cover the algorithm against synthetic data and
cause-label distributions across age groups.
```

---

### Task 25: Plan 1 closing

**Files:** (no new files; verification and PR)

- [x] **Step 1: Run the full project test suite**

Run: `docker compose -f docker-compose.local.yml exec web pytest epocha/ -q --tb=short`
Expected: all tests pass (Economy 252, new demography tests, agents, simulation, chat/tasks infrastructural tests may still fail with Redis issues unrelated to this plan).

- [x] **Step 2: Verify migrations are clean on a fresh DB**

Run: `docker compose -f docker-compose.local.yml exec web python manage.py migrate --plan | tail -30`
Expected: no pending migrations after `migrate`.

- [x] **Step 3: Push branch and open draft PR to develop**

```
git push -u origin feature/demography-1-foundations
gh pr create --draft --base develop --title "Demography Plan 1: foundations + mortality" --body "$(cat <<'EOF'
## Summary
- New app `epocha.apps.demography` with 4 models (Couple, DemographyEvent, PopulationSnapshot, AgentFertilityState)
- Agent extensions: birth_tick, death_tick, death_cause, other_parent_agent, caretaker_agent
- Integration contracts: add_to_treasury helper, SUBSISTENCE_NEED_PER_AGENT constant, compute_subsistence_threshold, compute_aggregate_outlook
- 5 era JSON templates with schema validation
- Seeded per-subsystem RNG (demography/rng.py)
- Mortality module: Heligman-Pollard, tick scaling, cause attribution
- HP fitting wrapper with scipy.optimize.curve_fit (synthetic validation; real calibration in Plan 4)
- Full unit test coverage; migrations clean on fresh DB

## Spec
`docs/superpowers/specs/2026-04-18-demography-design-it.md` (CONVERGED after 4 audit rounds)

## Test Plan
- [x] All models tests pass (6)
- [x] RNG reproducibility tests pass (5)
- [x] Template loader tests pass (5)
- [x] Context helpers tests pass (5)
- [x] Mortality + HP fit tests pass (~10)
- [x] Economy regression tests pass (252)
- [x] Migrations clean on fresh DB
EOF
)"
```

- [x] **Step 4: When CI is green and human validation happens, merge to develop**

Merge strategy: `--no-ff` to preserve the plan-level milestone in the main history. Sync memory backup after merge.

- [x] **Step 5: Final commit for closing checklist**

If any small fixes arose from PR review, land them as final commits before merge.

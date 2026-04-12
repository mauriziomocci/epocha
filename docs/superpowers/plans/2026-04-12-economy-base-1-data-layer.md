# Economy Base Implementation Plan — Part 1: Data Layer

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create the `epocha.apps.economy` Django app with all 10 economic models, the Government treasury extension, and the pre-configured EconomyTemplate fixtures. After this plan, the full economic data schema exists and is ready to receive the production engine (Part 2).

**Architecture:** New app `epocha.apps.economy` with models for currency, goods, production factors, zone-level markets, agent inventories, property, taxation, transaction ledger, and era-based templates. All models use JSONField for extensibility. No business logic yet — only data layer and template loading.

**Tech Stack:** Django 5.x, PostgreSQL.

**Spec:** `docs/superpowers/specs/2026-04-12-economy-base-design.md`

**Follow-up plans:**
- Part 2 — Engine: CES production, market clearing, rent, wages, taxes, monetary update
- Part 3 — Integration: decision engine context, hoard action, political feedback, world generator initialization

---

## File Structure (Part 1 scope)

| File | Responsibility | New/Modify |
|------|---------------|------------|
| `epocha/apps/economy/__init__.py` | App init | New |
| `epocha/apps/economy/apps.py` | Django AppConfig | New |
| `epocha/apps/economy/models.py` | All 10 economic models | New |
| `epocha/apps/economy/migrations/0001_initial.py` | Initial migration | New |
| `epocha/apps/world/models.py` | Add government_treasury field to Government | Modify |
| `epocha/apps/world/migrations/0005_government_treasury.py` | Treasury migration | New |
| `epocha/apps/economy/template_loader.py` | Load EconomyTemplate from fixtures | New |
| `epocha/apps/economy/tests/__init__.py` | Test init | New |
| `epocha/apps/economy/tests/test_models.py` | Model tests | New |
| `epocha/apps/economy/tests/test_template_loader.py` | Template loader tests | New |
| `config/settings/base.py` | Register economy app | Modify |

---

## Tasks summary (Part 1 scope)

1. **App scaffold and settings** — create economy app, register in settings
2. **Core economic models** — Currency, GoodCategory, ProductionFactor with tests
3. **Zone and agent economic models** — ZoneEconomy, PriceHistory, AgentInventory with tests
4. **Property and fiscal models** — Property, TaxPolicy, EconomicLedger, Government treasury with tests
5. **EconomyTemplate model and fixture loader** — template model + 4 pre-configured era templates + loader function

---

### Task 1: App scaffold and settings

**Files:**
- Create: `epocha/apps/economy/__init__.py`
- Create: `epocha/apps/economy/apps.py`
- Create: `epocha/apps/economy/tests/__init__.py`
- Modify: `config/settings/base.py`

- [ ] **Step 1: Create the economy app skeleton**

Run:
```bash
mkdir -p epocha/apps/economy/migrations epocha/apps/economy/tests
touch epocha/apps/economy/__init__.py
touch epocha/apps/economy/migrations/__init__.py
touch epocha/apps/economy/tests/__init__.py
```

Create `epocha/apps/economy/apps.py`:

```python
"""Economy Django app — neoclassical general equilibrium model.

Implements CES production, Walrasian market clearing, multi-currency,
property ownership, and fiscal policy. Replaces the placeholder economy
in world/economy.py.

Scientific paradigm: neoclassical (Arrow et al. 1961, Walras 1874,
Fisher 1911, Ricardo 1817). See spec for full references.
"""
from django.apps import AppConfig


class EconomyConfig(AppConfig):
    """App configuration for the Economy module."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "epocha.apps.economy"
    label = "economy"
    verbose_name = "Economy"
```

- [ ] **Step 2: Register the app in settings**

In `config/settings/base.py`, find the `LOCAL_APPS` list and add `"epocha.apps.economy"` after `"epocha.apps.knowledge"`.

- [ ] **Step 3: Verify the app loads**

Run:
```bash
docker compose -f docker-compose.local.yml run --rm web python -c "from epocha.apps.economy.apps import EconomyConfig; print(EconomyConfig.name)"
```

Expected: `epocha.apps.economy`

- [ ] **Step 4: Run existing test suite**

Run: `docker compose -f docker-compose.local.yml run --rm web pytest -q -m "not slow"`

Expected: all existing tests pass.

- [ ] **Step 5: Commit**

```
chore(economy): scaffold economy app

CHANGE: Create the economy Django app skeleton and register it in
LOCAL_APPS. No models or business logic yet.
```

---

### Task 2: Core economic models (Currency, GoodCategory, ProductionFactor)

**Files:**
- Create: `epocha/apps/economy/models.py`
- Create: `epocha/apps/economy/tests/test_models.py`
- Create: `epocha/apps/economy/migrations/0001_initial.py` (auto-generated)

- [ ] **Step 1: Write the failing tests**

Create `epocha/apps/economy/tests/test_models.py`:

```python
"""Tests for the economy data models."""
import pytest
from django.db import IntegrityError

from epocha.apps.economy.models import Currency, GoodCategory, ProductionFactor
from epocha.apps.simulation.models import Simulation
from epocha.apps.users.models import User


@pytest.fixture
def user(db):
    return User.objects.create_user(email="econ@epocha.dev", username="econuser", password="pass1234")


@pytest.fixture
def simulation(user):
    return Simulation.objects.create(name="EconTest", seed=42, owner=user)


@pytest.mark.django_db
class TestCurrency:
    def test_create_currency(self, simulation):
        c = Currency.objects.create(
            simulation=simulation, code="LVR", name="Livre tournois",
            symbol="L", is_primary=True, total_supply=50000.0,
        )
        assert c.code == "LVR"
        assert c.cached_velocity == 1.0  # default
        assert c.total_supply == 50000.0

    def test_currency_code_unique_per_simulation(self, simulation):
        Currency.objects.create(
            simulation=simulation, code="LVR", name="Livre",
            symbol="L", is_primary=True, total_supply=1000.0,
        )
        with pytest.raises(IntegrityError):
            Currency.objects.create(
                simulation=simulation, code="LVR", name="Another Livre",
                symbol="L2", is_primary=False, total_supply=500.0,
            )

    def test_two_simulations_same_code(self, user):
        sim1 = Simulation.objects.create(name="Sim1", seed=1, owner=user)
        sim2 = Simulation.objects.create(name="Sim2", seed=2, owner=user)
        Currency.objects.create(simulation=sim1, code="USD", name="Dollar", symbol="$", total_supply=1000.0)
        Currency.objects.create(simulation=sim2, code="USD", name="Dollar", symbol="$", total_supply=2000.0)
        assert Currency.objects.filter(code="USD").count() == 2


@pytest.mark.django_db
class TestGoodCategory:
    def test_create_good(self, simulation):
        g = GoodCategory.objects.create(
            simulation=simulation, code="subsistence", name="Subsistence goods",
            is_essential=True, base_price=3.0, price_elasticity=0.3,
        )
        assert g.is_essential is True
        assert g.price_elasticity == 0.3

    def test_good_code_unique_per_simulation(self, simulation):
        GoodCategory.objects.create(
            simulation=simulation, code="luxury", name="Luxury",
            base_price=50.0, price_elasticity=2.0,
        )
        with pytest.raises(IntegrityError):
            GoodCategory.objects.create(
                simulation=simulation, code="luxury", name="Other Luxury",
                base_price=60.0, price_elasticity=1.8,
            )


@pytest.mark.django_db
class TestProductionFactor:
    def test_create_factor(self, simulation):
        f = ProductionFactor.objects.create(
            simulation=simulation, code="labor", name="Labor",
            description="Human work hours",
        )
        assert f.code == "labor"

    def test_factor_code_unique_per_simulation(self, simulation):
        ProductionFactor.objects.create(
            simulation=simulation, code="capital", name="Capital",
        )
        with pytest.raises(IntegrityError):
            ProductionFactor.objects.create(
                simulation=simulation, code="capital", name="Other Capital",
            )
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `docker compose -f docker-compose.local.yml run --rm web pytest epocha/apps/economy/tests/test_models.py -v`

Expected: ImportError.

- [ ] **Step 3: Implement the models**

Create `epocha/apps/economy/models.py`:

```python
"""Economy models — neoclassical general equilibrium data layer.

This module contains the data models for the economy system. The models
are per-simulation: each simulation has its own currencies, goods,
factors, markets, and properties. All numeric economic parameters are
stored in the database (not hardcoded) to support universal
configurability across eras and scenarios.

Scientific paradigm: neoclassical (Arrow et al. 1961, Walras 1874,
Fisher 1911, Ricardo 1817). See the spec for full references:
docs/superpowers/specs/2026-04-12-economy-base-design.md
"""
from __future__ import annotations

from django.db import models


class Currency(models.Model):
    """A monetary unit in the simulation.

    The total_supply field represents M in Fisher's equation MV=PQ
    (Fisher, I. 1911. The Purchasing Power of Money).
    The cached_velocity field is V, recomputed each tick from actual
    transaction volume -- it is NOT a stored constant. The equation
    is used as a diagnostic check, not as a price-determination
    mechanism: prices are set by Walrasian market clearing.
    """

    simulation = models.ForeignKey(
        "simulation.Simulation", on_delete=models.CASCADE,
        related_name="currencies",
    )
    code = models.CharField(max_length=10)
    name = models.CharField(max_length=100)
    symbol = models.CharField(max_length=5)
    is_primary = models.BooleanField(default=True)
    total_supply = models.FloatField(
        help_text="M in Fisher's MV=PQ: total money in circulation",
    )
    cached_velocity = models.FloatField(
        default=1.0,
        help_text="V in Fisher's MV=PQ: recomputed each tick from "
                  "transaction volume, NOT a stored constant",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("simulation", "code")

    def __str__(self):
        return f"{self.name} ({self.code})"


class GoodCategory(models.Model):
    """A category of economic goods in the simulation.

    Price elasticity uses the absolute value convention from standard
    economics: 0 = perfectly inelastic (demand unaffected by price),
    1 = unit elastic, >1 = elastic (demand highly sensitive to price).
    Essential goods (food) typically 0.2-0.5; luxury goods 1.5-2.5.

    Source for empirical values: Houthakker & Taylor (1970), updated
    by Andreyeva et al. (2010).
    """

    simulation = models.ForeignKey(
        "simulation.Simulation", on_delete=models.CASCADE,
        related_name="good_categories",
    )
    code = models.CharField(max_length=30)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    is_essential = models.BooleanField(
        default=False,
        help_text="Essential goods cause crisis when scarce",
    )
    base_price = models.FloatField(
        help_text="Initial price in the primary currency",
    )
    price_elasticity = models.FloatField(
        help_text="|Price elasticity of demand|: 0=inelastic, 1=unit, >1=elastic",
    )
    config = models.JSONField(default=dict)

    class Meta:
        unique_together = ("simulation", "code")

    def __str__(self):
        return f"{self.name} ({self.code})"


class ProductionFactor(models.Model):
    """A factor of production (labor, capital, natural resources, knowledge).

    Factors are inputs to the CES production function (Arrow et al. 1961).
    Each zone has different abundances of each factor, and each good
    category has different factor requirements.
    """

    simulation = models.ForeignKey(
        "simulation.Simulation", on_delete=models.CASCADE,
        related_name="production_factors",
    )
    code = models.CharField(max_length=30)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    config = models.JSONField(default=dict)

    class Meta:
        unique_together = ("simulation", "code")

    def __str__(self):
        return f"{self.name} ({self.code})"
```

- [ ] **Step 4: Generate and apply migration**

Run:
```bash
docker compose -f docker-compose.local.yml run --rm web python manage.py makemigrations economy --name initial
docker compose -f docker-compose.local.yml run --rm web python manage.py migrate economy
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `docker compose -f docker-compose.local.yml run --rm web pytest epocha/apps/economy/tests/test_models.py -v`

Expected: all PASS.

- [ ] **Step 6: Commit**

```
feat(economy): add Currency, GoodCategory, and ProductionFactor models

CHANGE: Add the three core economic entity models with per-simulation
uniqueness. Currency supports multi-currency with emergent velocity
(Fisher 1911). GoodCategory has price elasticity using standard
absolute-value convention (Houthakker & Taylor 1970). ProductionFactor
defines CES inputs (Arrow et al. 1961).
```

---

### Task 3: Zone and agent economic models (ZoneEconomy, PriceHistory, AgentInventory)

**Files:**
- Modify: `epocha/apps/economy/models.py` (append 3 models)
- Create: `epocha/apps/economy/migrations/0002_zone_agent.py` (auto-generated)
- Modify: `epocha/apps/economy/tests/test_models.py` (append tests)

- [ ] **Step 1: Write the failing tests**

Append to `epocha/apps/economy/tests/test_models.py`:

```python
from django.contrib.gis.geos import Point, Polygon

from epocha.apps.economy.models import (
    AgentInventory, Currency, GoodCategory, PriceHistory, ZoneEconomy,
)
from epocha.apps.agents.models import Agent
from epocha.apps.world.models import World, Zone


@pytest.fixture
def world(simulation):
    return World.objects.create(simulation=simulation, distance_scale=133.0, tick_duration_hours=24.0)


@pytest.fixture
def zone(world):
    return Zone.objects.create(
        world=world, name="Paris", zone_type="urban",
        boundary=Polygon.from_bbox((0, 0, 100, 100)),
        center=Point(50, 50),
    )


@pytest.fixture
def agent(simulation, zone):
    return Agent.objects.create(
        simulation=simulation, name="TestAgent", role="merchant",
        personality={"openness": 0.5}, location=Point(50, 50), zone=zone,
    )


@pytest.mark.django_db
class TestZoneEconomy:
    def test_create_zone_economy(self, zone):
        ze = ZoneEconomy.objects.create(
            zone=zone,
            natural_resources={"labor": 1.0, "capital": 0.5},
            production_config={"subsistence": {"scale": 10.0, "sigma": 0.5}},
            market_prices={"subsistence": 3.0},
        )
        assert ze.zone == zone
        assert ze.natural_resources["labor"] == 1.0

    def test_one_economy_per_zone(self, zone):
        ZoneEconomy.objects.create(zone=zone)
        with pytest.raises(IntegrityError):
            ZoneEconomy.objects.create(zone=zone)


@pytest.mark.django_db
class TestPriceHistory:
    def test_create_price_history(self, zone):
        ze = ZoneEconomy.objects.create(zone=zone)
        ph = PriceHistory.objects.create(
            zone_economy=ze, good_code="subsistence",
            tick=1, price=3.2, supply=100.0, demand=120.0,
        )
        assert ph.price == 3.2
        assert ph.tick == 1

    def test_unique_per_zone_good_tick(self, zone):
        ze = ZoneEconomy.objects.create(zone=zone)
        PriceHistory.objects.create(
            zone_economy=ze, good_code="subsistence",
            tick=1, price=3.0, supply=100.0, demand=100.0,
        )
        with pytest.raises(IntegrityError):
            PriceHistory.objects.create(
                zone_economy=ze, good_code="subsistence",
                tick=1, price=3.5, supply=90.0, demand=110.0,
            )


@pytest.mark.django_db
class TestAgentInventory:
    def test_create_inventory(self, agent):
        inv = AgentInventory.objects.create(
            agent=agent,
            holdings={"subsistence": 10.0, "materials": 5.0},
            cash={"LVR": 100.0},
        )
        assert inv.holdings["subsistence"] == 10.0
        assert inv.cash["LVR"] == 100.0

    def test_one_inventory_per_agent(self, agent):
        AgentInventory.objects.create(agent=agent)
        with pytest.raises(IntegrityError):
            AgentInventory.objects.create(agent=agent)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `docker compose -f docker-compose.local.yml run --rm web pytest epocha/apps/economy/tests/test_models.py::TestZoneEconomy -v`

Expected: ImportError.

- [ ] **Step 3: Append models to models.py**

APPEND to `epocha/apps/economy/models.py`:

```python
class ZoneEconomy(models.Model):
    """Economic state of a geographic zone.

    Each zone has its own market with local prices, supply, and demand.
    The production_config contains CES function parameters per good
    category. Natural resources are zone-specific endowments that affect
    production output.

    market_prices is a snapshot cache updated each tick for fast reads;
    the authoritative price history is in PriceHistory.
    """

    zone = models.OneToOneField(
        "world.Zone", on_delete=models.CASCADE,
        related_name="economy",
    )
    natural_resources = models.JSONField(
        default=dict,
        help_text="{factor_code: abundance_float}",
    )
    production_config = models.JSONField(
        default=dict,
        help_text="{good_code: {factors: {factor_code: exponent}, "
                  "scale: A, sigma: sigma_CES}}",
    )
    market_prices = models.JSONField(
        default=dict,
        help_text="{good_code: current_price} -- snapshot cache",
    )
    market_supply = models.JSONField(default=dict)
    market_demand = models.JSONField(default=dict)

    def __str__(self):
        return f"Economy of {self.zone.name}"


class PriceHistory(models.Model):
    """Historical price record per good per zone per tick.

    Used by the analytics/psychohistoriography system for inflation
    detection, crisis identification, and time-series visualization.
    """

    zone_economy = models.ForeignKey(
        ZoneEconomy, on_delete=models.CASCADE,
        related_name="price_history",
    )
    good_code = models.CharField(max_length=30)
    tick = models.PositiveIntegerField()
    price = models.FloatField()
    supply = models.FloatField()
    demand = models.FloatField()

    class Meta:
        unique_together = ("zone_economy", "good_code", "tick")
        indexes = [
            models.Index(fields=["zone_economy", "good_code", "tick"]),
        ]


class AgentInventory(models.Model):
    """An agent's economic holdings: goods and cash.

    Replaces the single Agent.wealth float with a structured inventory.
    Agent.wealth continues to exist as a computed summary (total value
    of all holdings + cash + property) for backward compatibility with
    existing modules that read it.
    """

    agent = models.OneToOneField(
        "agents.Agent", on_delete=models.CASCADE,
        related_name="inventory",
    )
    holdings = models.JSONField(
        default=dict,
        help_text="{good_code: quantity}",
    )
    cash = models.JSONField(
        default=dict,
        help_text="{currency_code: amount}",
    )

    def __str__(self):
        return f"Inventory of {self.agent.name}"
```

- [ ] **Step 4: Generate and apply migration**

Run:
```bash
docker compose -f docker-compose.local.yml run --rm web python manage.py makemigrations economy --name zone_agent
docker compose -f docker-compose.local.yml run --rm web python manage.py migrate economy
```

- [ ] **Step 5: Run tests**

Run: `docker compose -f docker-compose.local.yml run --rm web pytest epocha/apps/economy/tests/test_models.py -v`

Expected: all PASS.

- [ ] **Step 6: Commit**

```
feat(economy): add ZoneEconomy, PriceHistory, and AgentInventory models

CHANGE: Add per-zone market state model with CES production config and
price snapshots, price history for inflation detection and analytics,
and structured agent inventory replacing the single wealth float.
```

---

### Task 4: Property, fiscal, and ledger models

**Files:**
- Modify: `epocha/apps/economy/models.py` (append 3 models)
- Modify: `epocha/apps/world/models.py` (add government_treasury to Government)
- Create: `epocha/apps/economy/migrations/0003_property_fiscal.py` (auto)
- Create: `epocha/apps/world/migrations/0005_government_treasury.py` (auto)
- Modify: `epocha/apps/economy/tests/test_models.py` (append tests)

- [ ] **Step 1: Write the failing tests**

Append to `epocha/apps/economy/tests/test_models.py`:

```python
from epocha.apps.economy.models import (
    Currency, EconomicLedger, Property, TaxPolicy,
)
from epocha.apps.world.models import Government


@pytest.fixture
def currency(simulation):
    return Currency.objects.create(
        simulation=simulation, code="LVR", name="Livre",
        symbol="L", is_primary=True, total_supply=50000.0,
    )


@pytest.mark.django_db
class TestProperty:
    def test_create_agent_property(self, simulation, agent, zone):
        p = Property.objects.create(
            simulation=simulation, owner=agent, owner_type="agent",
            zone=zone, property_type="land", name="Small Farm",
            value=200.0, production_bonus={"subsistence": 1.5},
        )
        assert p.owner == agent
        assert p.owner_type == "agent"
        assert p.production_bonus["subsistence"] == 1.5

    def test_create_government_property(self, simulation, zone):
        p = Property.objects.create(
            simulation=simulation, owner=None, owner_type="government",
            zone=zone, property_type="land", name="Royal Estate",
            value=1000.0,
        )
        assert p.owner is None
        assert p.owner_type == "government"

    def test_create_commons(self, simulation, zone):
        p = Property.objects.create(
            simulation=simulation, owner=None, owner_type="commons",
            zone=zone, property_type="land", name="Common Land",
            value=0.0,
        )
        assert p.owner_type == "commons"


@pytest.mark.django_db
class TestTaxPolicy:
    def test_create_tax_policy(self, simulation):
        tp = TaxPolicy.objects.create(
            simulation=simulation, income_tax_rate=0.15,
        )
        assert tp.income_tax_rate == 0.15

    def test_one_policy_per_simulation(self, simulation):
        TaxPolicy.objects.create(simulation=simulation, income_tax_rate=0.10)
        with pytest.raises(IntegrityError):
            TaxPolicy.objects.create(simulation=simulation, income_tax_rate=0.20)


@pytest.mark.django_db
class TestEconomicLedger:
    def test_create_trade_transaction(self, simulation, agent, currency):
        tx = EconomicLedger.objects.create(
            simulation=simulation, tick=1,
            from_agent=agent, to_agent=None,
            currency=currency,
            quantity=10.0, unit_price=3.0, total_amount=30.0,
            transaction_type="trade",
        )
        assert tx.total_amount == 30.0
        assert tx.transaction_type == "trade"

    def test_create_tax_transaction(self, simulation, agent, currency):
        tx = EconomicLedger.objects.create(
            simulation=simulation, tick=1,
            from_agent=agent, to_agent=None,
            currency=currency,
            total_amount=5.0, transaction_type="tax",
        )
        assert tx.transaction_type == "tax"


@pytest.mark.django_db
class TestGovernmentTreasury:
    def test_government_has_treasury(self, simulation):
        gov = Government.objects.create(
            simulation=simulation, government_type="monarchy",
        )
        assert gov.government_treasury == {}
        gov.government_treasury = {"LVR": 1000.0}
        gov.save(update_fields=["government_treasury"])
        gov.refresh_from_db()
        assert gov.government_treasury["LVR"] == 1000.0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `docker compose -f docker-compose.local.yml run --rm web pytest epocha/apps/economy/tests/test_models.py::TestProperty -v`

Expected: ImportError.

- [ ] **Step 3: Append Property, TaxPolicy, EconomicLedger to models.py**

APPEND to `epocha/apps/economy/models.py`:

```python
class Property(models.Model):
    """An owned productive asset (land, workshop, factory, etc.).

    Rent is NOT a stored rate. It emerges from actual zone production
    multiplied by the property's production_bonus. This follows
    Ricardo's (1817) theory where rent is determined by differential
    land fertility, not by an arbitrary percentage.

    Simplification: the full Ricardian model computes rent as the
    surplus over the marginal (least fertile) land. This implementation
    uses proportional bonus as an approximation. The qualitative
    behavior is correct (fertile land yields more rent), but the
    quantitative derivation is simplified.
    """

    OWNER_TYPES = [
        ("agent", "Agent"),
        ("government", "Government"),
        ("commons", "Commons (unowned)"),
    ]

    simulation = models.ForeignKey(
        "simulation.Simulation", on_delete=models.CASCADE,
        related_name="properties",
    )
    owner = models.ForeignKey(
        "agents.Agent", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="owned_properties",
    )
    owner_type = models.CharField(max_length=20, choices=OWNER_TYPES)
    zone = models.ForeignKey(
        "world.Zone", on_delete=models.CASCADE,
        related_name="properties",
    )
    property_type = models.CharField(max_length=30)
    name = models.CharField(max_length=255)
    value = models.FloatField(
        help_text="Estimated value in primary currency",
    )
    production_bonus = models.JSONField(
        default=dict,
        help_text="{good_code: multiplier} -- how much this property "
                  "boosts production of each good in its zone",
    )
    config = models.JSONField(default=dict)

    class Meta:
        indexes = [
            models.Index(fields=["simulation", "owner_type"]),
            models.Index(fields=["simulation", "zone"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.property_type}, {self.owner_type})"


class TaxPolicy(models.Model):
    """Fiscal policy for the simulation.

    Spec 1 implements flat income tax only. Spec 2 will add progressive
    rates, property tax, and tariffs via the config JSONField.
    """

    simulation = models.OneToOneField(
        "simulation.Simulation", on_delete=models.CASCADE,
        related_name="tax_policy",
    )
    income_tax_rate = models.FloatField(
        help_text="Flat income tax rate (0.0-1.0). Applied to wages + rent.",
    )
    config = models.JSONField(
        default=dict,
        help_text="Extensible for spec 2: progressive rates, property tax, tariffs",
    )

    def __str__(self):
        return f"TaxPolicy ({self.income_tax_rate:.0%})"


class EconomicLedger(models.Model):
    """Record of economic transactions.

    Clean replacement for the legacy EconomicTransaction in
    world/models.py which used integer IDs instead of proper
    ForeignKeys. All new transactions use this model.
    """

    TRANSACTION_TYPES = [
        ("production", "Production"),
        ("trade", "Trade"),
        ("tax", "Tax"),
        ("rent", "Rent"),
        ("wage", "Wage"),
    ]

    simulation = models.ForeignKey(
        "simulation.Simulation", on_delete=models.CASCADE,
        related_name="economic_ledger",
    )
    tick = models.PositiveIntegerField()
    from_agent = models.ForeignKey(
        "agents.Agent", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="outgoing_transactions",
    )
    to_agent = models.ForeignKey(
        "agents.Agent", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="incoming_transactions",
    )
    currency = models.ForeignKey(
        Currency, on_delete=models.CASCADE,
    )
    good_category = models.ForeignKey(
        GoodCategory, null=True, blank=True,
        on_delete=models.SET_NULL,
    )
    quantity = models.FloatField(default=0.0)
    unit_price = models.FloatField(default=0.0)
    total_amount = models.FloatField()
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["simulation", "tick"]),
            models.Index(fields=["from_agent"]),
            models.Index(fields=["to_agent"]),
            models.Index(fields=["simulation", "transaction_type", "tick"]),
        ]
```

- [ ] **Step 4: Add government_treasury to Government model**

In `epocha/apps/world/models.py`, find the `Government` class and add after the `last_election_tick` field:

```python
    government_treasury = models.JSONField(
        default=dict,
        help_text="{currency_code: amount} -- tax revenue collected",
    )
```

- [ ] **Step 5: Generate and apply migrations**

Run:
```bash
docker compose -f docker-compose.local.yml run --rm web python manage.py makemigrations economy --name property_fiscal
docker compose -f docker-compose.local.yml run --rm web python manage.py makemigrations world --name government_treasury
docker compose -f docker-compose.local.yml run --rm web python manage.py migrate
```

- [ ] **Step 6: Run all economy tests**

Run: `docker compose -f docker-compose.local.yml run --rm web pytest epocha/apps/economy/tests/test_models.py -v`

Expected: all PASS.

- [ ] **Step 7: Run full suite**

Run: `docker compose -f docker-compose.local.yml run --rm web pytest -q -m "not slow"`

Expected: all tests pass.

- [ ] **Step 8: Commit**

```
feat(economy): add Property, TaxPolicy, EconomicLedger, and Government treasury

CHANGE: Add property ownership model with Ricardian emergent rent (not
stored rate), flat tax policy, clean transaction ledger replacing legacy
integer-FK model, and government_treasury JSONField on the existing
Government model for tax revenue tracking.
```

---

### Task 5: EconomyTemplate model and fixture loader

**Files:**
- Modify: `epocha/apps/economy/models.py` (append EconomyTemplate)
- Create: `epocha/apps/economy/migrations/0004_template.py` (auto)
- Create: `epocha/apps/economy/template_loader.py`
- Create: `epocha/apps/economy/tests/test_template_loader.py`

- [ ] **Step 1: Write the failing tests**

Create `epocha/apps/economy/tests/test_template_loader.py`:

```python
"""Tests for the economy template loader."""
import pytest

from epocha.apps.economy.models import EconomyTemplate
from epocha.apps.economy.template_loader import (
    get_template,
    load_default_templates,
    TEMPLATE_NAMES,
)


@pytest.mark.django_db
class TestLoadDefaultTemplates:
    def test_creates_four_templates(self):
        load_default_templates()
        assert EconomyTemplate.objects.count() == 4

    def test_template_names(self):
        load_default_templates()
        names = set(EconomyTemplate.objects.values_list("name", flat=True))
        assert names == {"pre_industrial", "industrial", "modern", "sci_fi"}

    def test_idempotent(self):
        load_default_templates()
        load_default_templates()
        assert EconomyTemplate.objects.count() == 4

    def test_pre_industrial_has_correct_sigma(self):
        load_default_templates()
        t = EconomyTemplate.objects.get(name="pre_industrial")
        # CES sigma for pre-industrial: 0.5 (Antras 2004)
        assert t.production_config["default_sigma"] == 0.5

    def test_pre_industrial_has_five_goods(self):
        load_default_templates()
        t = EconomyTemplate.objects.get(name="pre_industrial")
        assert len(t.goods_config) == 5

    def test_pre_industrial_has_currency(self):
        load_default_templates()
        t = EconomyTemplate.objects.get(name="pre_industrial")
        assert len(t.currencies_config) >= 1

    def test_modern_has_higher_sigma(self):
        load_default_templates()
        t = EconomyTemplate.objects.get(name="modern")
        assert t.production_config["default_sigma"] > 1.0


@pytest.mark.django_db
class TestGetTemplate:
    def test_get_existing_template(self):
        load_default_templates()
        t = get_template("pre_industrial")
        assert t.name == "pre_industrial"

    def test_get_nonexistent_raises(self):
        load_default_templates()
        with pytest.raises(EconomyTemplate.DoesNotExist):
            get_template("nonexistent")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `docker compose -f docker-compose.local.yml run --rm web pytest epocha/apps/economy/tests/test_template_loader.py -v`

Expected: ImportError.

- [ ] **Step 3: Append EconomyTemplate model**

APPEND to `epocha/apps/economy/models.py`:

```python
class EconomyTemplate(models.Model):
    """Pre-configured economic template for an era or scenario.

    Templates define the complete economic setup: goods, factors,
    currencies, production functions, tax policy, property types, and
    initial distribution. The user selects a template when creating a
    simulation and can override any field.

    Four default templates are provided: pre_industrial, industrial,
    modern, sci_fi. CES sigma values: pre-industrial 0.5 (Antras 2004),
    industrial 0.8, modern 1.2 (Karabarbounis & Neiman 2014), sci-fi
    1.5 (speculative extrapolation, no empirical basis).
    """

    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    era_label = models.CharField(max_length=100)
    version = models.CharField(max_length=10, default="1.0")
    goods_config = models.JSONField()
    factors_config = models.JSONField()
    currencies_config = models.JSONField()
    production_config = models.JSONField()
    tax_config = models.JSONField()
    properties_config = models.JSONField()
    initial_distribution = models.JSONField()
    config = models.JSONField(default=dict)

    def __str__(self):
        return f"{self.name} ({self.era_label})"
```

- [ ] **Step 4: Generate and apply migration**

Run:
```bash
docker compose -f docker-compose.local.yml run --rm web python manage.py makemigrations economy --name template
docker compose -f docker-compose.local.yml run --rm web python manage.py migrate economy
```

- [ ] **Step 5: Implement template_loader.py**

Create `epocha/apps/economy/template_loader.py`:

```python
"""Economy template loader with four pre-configured era templates.

Templates define the complete economic configuration for a simulation.
Each template is scientifically grounded for its era; see the inline
source citations for calibration notes.

The loader is idempotent: calling load_default_templates() multiple
times creates the templates once (via get_or_create).
"""
from __future__ import annotations

from .models import EconomyTemplate

TEMPLATE_NAMES = ("pre_industrial", "industrial", "modern", "sci_fi")

# Goods configuration shared across all templates (5 universal categories).
# The specific examples and elasticities vary by era.
_GOODS_BASE = [
    {
        "code": "subsistence",
        "name": "Subsistence goods",
        "is_essential": True,
        "price_elasticity": 0.3,
        # Source: Houthakker & Taylor (1970); food elasticity ~0.2-0.5
    },
    {
        "code": "materials",
        "name": "Raw materials",
        "is_essential": False,
        "price_elasticity": 0.7,
    },
    {
        "code": "manufacture",
        "name": "Manufactured goods",
        "is_essential": False,
        "price_elasticity": 1.2,
    },
    {
        "code": "luxury",
        "name": "Luxury goods",
        "is_essential": False,
        "price_elasticity": 2.0,
        # Source: Andreyeva et al. (2010); luxury elasticity ~1.5-2.5
    },
    {
        "code": "services",
        "name": "Services",
        "is_essential": False,
        "price_elasticity": 0.9,
    },
]

_FACTORS_BASE = [
    {"code": "labor", "name": "Labor"},
    {"code": "capital", "name": "Capital"},
    {"code": "natural_resources", "name": "Natural Resources"},
    {"code": "knowledge", "name": "Knowledge"},
]

_PROPERTIES_BASE = [
    {"code": "land", "name": "Farmland", "base_value": 200, "production_bonus": {"subsistence": 1.5}},
    {"code": "workshop", "name": "Workshop", "base_value": 150, "production_bonus": {"manufacture": 1.3}},
    {"code": "shop", "name": "Shop", "base_value": 100, "production_bonus": {"services": 1.2}},
]

_ZONE_TYPE_RESOURCES = {
    "rural": {"natural_resources": 1.5, "labor": 0.8},
    "urban": {"natural_resources": 0.3, "capital": 1.5, "knowledge": 1.2},
    "commercial": {"capital": 1.3, "knowledge": 1.0},
    "industrial": {"capital": 1.8, "natural_resources": 0.5},
    "wilderness": {"natural_resources": 2.0, "labor": 0.3},
}

_ROLE_PRODUCTION = {
    "farmer": {"good": "subsistence", "skill_weight": 1.2},
    "blacksmith": {"good": "materials", "skill_weight": 1.3},
    "craftsman": {"good": "manufacture", "skill_weight": 1.1},
    "merchant": {"good": "services", "skill_weight": 1.0},
    "priest": {"good": "services", "skill_weight": 0.8},
}


def _pre_industrial_template() -> dict:
    return {
        "description": "Agricultural economy with artisanal production, limited trade, feudal property.",
        "era_label": "Pre-Industrial (1400-1800)",
        "goods_config": [{**g, "base_price": p} for g, p in zip(
            _GOODS_BASE, [3.0, 5.0, 12.0, 50.0, 8.0]
        )],
        "factors_config": _FACTORS_BASE,
        "currencies_config": [
            {"code": "LVR", "name": "Livre tournois", "symbol": "L", "initial_supply": 50000.0},
        ],
        "production_config": {
            # CES sigma 0.5: low factor substitutability (Antras 2004)
            "default_sigma": 0.5,
            "role_production": _ROLE_PRODUCTION,
            "zone_type_resources": _ZONE_TYPE_RESOURCES,
        },
        "tax_config": {
            # Approximates the dime royale (~10-15% of agricultural output)
            "income_tax_rate": 0.15,
        },
        "properties_config": {"types": _PROPERTIES_BASE},
        "initial_distribution": {
            "wealth_range": {"elite": [300, 500], "middle": [50, 150], "poor": [5, 30]},
            "property_ownership": "class_based",
        },
    }


def _industrial_template() -> dict:
    return {
        "description": "Industrializing economy with factories, growing trade, emerging labor market.",
        "era_label": "Industrial (1800-1950)",
        "goods_config": [{**g, "base_price": p} for g, p in zip(
            _GOODS_BASE, [2.0, 4.0, 8.0, 30.0, 6.0]
        )],
        "factors_config": _FACTORS_BASE,
        "currencies_config": [
            {"code": "GBP", "name": "Pound sterling", "symbol": "£", "initial_supply": 100000.0},
        ],
        "production_config": {
            "default_sigma": 0.8,
            "role_production": _ROLE_PRODUCTION,
            "zone_type_resources": _ZONE_TYPE_RESOURCES,
        },
        "tax_config": {"income_tax_rate": 0.20},
        "properties_config": {
            "types": _PROPERTIES_BASE + [
                {"code": "factory", "name": "Factory", "base_value": 500, "production_bonus": {"manufacture": 2.0}},
            ],
        },
        "initial_distribution": {
            "wealth_range": {"elite": [500, 1000], "middle": [100, 300], "poor": [10, 50]},
            "property_ownership": "class_based",
        },
    }


def _modern_template() -> dict:
    return {
        "description": "Service-dominant economy with high technology, global trade, complex taxation.",
        "era_label": "Modern (1950-present)",
        "goods_config": [{**g, "base_price": p} for g, p in zip(
            _GOODS_BASE, [5.0, 10.0, 20.0, 100.0, 15.0]
        )],
        "factors_config": _FACTORS_BASE,
        "currencies_config": [
            {"code": "USD", "name": "US Dollar", "symbol": "$", "initial_supply": 500000.0},
        ],
        "production_config": {
            # CES sigma 1.2: high factor substitutability (Karabarbounis & Neiman 2014)
            "default_sigma": 1.2,
            "role_production": _ROLE_PRODUCTION,
            "zone_type_resources": _ZONE_TYPE_RESOURCES,
        },
        "tax_config": {"income_tax_rate": 0.30},
        "properties_config": {
            "types": _PROPERTIES_BASE + [
                {"code": "factory", "name": "Factory", "base_value": 500, "production_bonus": {"manufacture": 2.0}},
                {"code": "office", "name": "Office", "base_value": 300, "production_bonus": {"services": 1.5}},
            ],
        },
        "initial_distribution": {
            "wealth_range": {"elite": [1000, 5000], "middle": [200, 800], "poor": [20, 100]},
            "property_ownership": "class_based",
        },
    }


def _sci_fi_template() -> dict:
    return {
        "description": "Knowledge-dominant economy with advanced technology, interstellar trade potential.",
        "era_label": "Science Fiction / Future",
        "goods_config": [{**g, "base_price": p} for g, p in zip(
            _GOODS_BASE, [10.0, 20.0, 50.0, 200.0, 30.0]
        )],
        "factors_config": _FACTORS_BASE,
        "currencies_config": [
            {"code": "CRD", "name": "Galactic Credit", "symbol": "Cr", "initial_supply": 1000000.0},
        ],
        "production_config": {
            # CES sigma 1.5: speculative (extrapolation of historical trend, no empirical basis)
            "default_sigma": 1.5,
            "role_production": _ROLE_PRODUCTION,
            "zone_type_resources": _ZONE_TYPE_RESOURCES,
        },
        "tax_config": {"income_tax_rate": 0.25},
        "properties_config": {
            "types": _PROPERTIES_BASE + [
                {"code": "factory", "name": "Automated Factory", "base_value": 1000, "production_bonus": {"manufacture": 3.0}},
                {"code": "lab", "name": "Research Lab", "base_value": 800, "production_bonus": {"services": 2.0}},
            ],
        },
        "initial_distribution": {
            "wealth_range": {"elite": [5000, 20000], "middle": [500, 2000], "poor": [50, 300]},
            "property_ownership": "class_based",
        },
    }


_TEMPLATE_BUILDERS = {
    "pre_industrial": _pre_industrial_template,
    "industrial": _industrial_template,
    "modern": _modern_template,
    "sci_fi": _sci_fi_template,
}


def load_default_templates() -> None:
    """Load the four default economy templates into the database.

    Idempotent: existing templates are not overwritten. Call from a data
    migration or a management command.
    """
    for name, builder in _TEMPLATE_BUILDERS.items():
        data = builder()
        EconomyTemplate.objects.get_or_create(
            name=name,
            defaults={
                "description": data["description"],
                "era_label": data["era_label"],
                "goods_config": data["goods_config"],
                "factors_config": data["factors_config"],
                "currencies_config": data["currencies_config"],
                "production_config": data["production_config"],
                "tax_config": data["tax_config"],
                "properties_config": data["properties_config"],
                "initial_distribution": data["initial_distribution"],
            },
        )


def get_template(name: str) -> EconomyTemplate:
    """Retrieve a template by name. Raises DoesNotExist if not found."""
    return EconomyTemplate.objects.get(name=name)
```

- [ ] **Step 6: Run template loader tests**

Run: `docker compose -f docker-compose.local.yml run --rm web pytest epocha/apps/economy/tests/test_template_loader.py -v`

Expected: all PASS.

- [ ] **Step 7: Run full suite**

Run: `docker compose -f docker-compose.local.yml run --rm web pytest -q -m "not slow"`

Expected: all tests pass.

- [ ] **Step 8: Commit**

```
feat(economy): add EconomyTemplate model with four pre-configured era templates

CHANGE: Add the EconomyTemplate model for era-based economic
configuration and the template_loader module with four scientifically
calibrated defaults: pre_industrial (sigma 0.5, Antras 2004),
industrial (sigma 0.8), modern (sigma 1.2, Karabarbounis & Neiman
2014), sci_fi (sigma 1.5, speculative). Each template defines goods,
factors, currencies, CES production config, tax policy, property types,
and initial wealth distribution. Loader is idempotent via get_or_create.
```

---

## Self-Review Summary

After completing Tasks 1-5 in this plan:

- New `epocha.apps.economy` app with 10 models:
  - Currency (multi-currency with Fisher velocity)
  - GoodCategory (5 categories with empirical elasticities)
  - ProductionFactor (4 CES factors)
  - ZoneEconomy (per-zone market state)
  - PriceHistory (time series for analytics)
  - AgentInventory (structured holdings replacing wealth float)
  - Property (Ricardian emergent rent)
  - TaxPolicy (flat income tax)
  - EconomicLedger (clean transaction log)
  - EconomyTemplate (era configuration)
- Government.government_treasury added to existing model
- 4 pre-configured templates loaded

**What is NOT yet in place:**
- CES production function implementation (Part 2)
- Market clearing / tatonnement algorithm (Part 2)
- Rent, wages, and tax computation (Part 2)
- Monetary velocity update (Part 2)
- Mood and stability feedback (Part 2)
- Decision engine economic context (Part 3)
- Hoard action (Part 3)
- Political feedback from economic indicators (Part 3)
- World generator initialization (Part 3)
- Deprecation of world/economy.py (Part 3)

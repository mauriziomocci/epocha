# Economy Behavioral Plan — Part 1: Data Layer + Expectations

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the 4 new models for the behavioral economy (Loan, PropertyListing, AgentExpectation, BankingState), extend templates with credit/banking/expectations config, and implement the adaptive expectations engine (Nerlove 1958 with Big Five modulation). After this plan, agents form price expectations each tick and the data layer supports debt and property trading.

**Architecture:** 4 new models appended to `economy/models.py`, template extensions in `template_loader.py`, new `expectations.py` module with Nerlove adaptive expectations modulated by Big Five personality. The expectations engine integrates into the tick pipeline as step 2 (after production, before market clearing).

**Tech Stack:** Django ORM, math.

**Spec:** `docs/superpowers/specs/2026-04-13-economy-behavioral-design.md`

**Follow-up plans:**
- Part 2 — Credit system: loan lifecycle, rollover, default cascade, banking
- Part 3 — Property market + integration: trading, Gordon valuation, expropriation, engine wiring

---

## File Structure (Part 1 scope)

| File | Responsibility | New/Modify |
|------|---------------|------------|
| `epocha/apps/economy/models.py` | Append Loan, PropertyListing, AgentExpectation, BankingState | Modify |
| `epocha/apps/economy/migrations/0004_behavioral.py` | Migration for new models | New (auto) |
| `epocha/apps/economy/expectations.py` | Adaptive expectations engine | New |
| `epocha/apps/economy/template_loader.py` | Add credit_config, banking_config, expectations_config | Modify |
| `epocha/apps/economy/tests/test_models_behavioral.py` | Model tests | New |
| `epocha/apps/economy/tests/test_expectations.py` | Expectations engine tests | New |
| `epocha/apps/economy/tests/test_template_behavioral.py` | Template config tests | New |

---

## Tasks summary (Part 1 scope)

1. **Behavioral models** — Loan, PropertyListing, AgentExpectation, BankingState + migration + tests
2. **Template extensions** — credit/banking/expectations config in all 4 era templates
3. **Expectations engine** — Nerlove adaptive expectations with Big Five modulation + tick integration

---

### Task 1: Behavioral models

**Files:**
- Modify: `epocha/apps/economy/models.py` (append 4 models)
- New: `epocha/apps/economy/migrations/0004_behavioral.py` (auto)
- New: `epocha/apps/economy/tests/test_models_behavioral.py`

- [ ] **Step 1: Write the failing tests**

Create `epocha/apps/economy/tests/test_models_behavioral.py`:

```python
"""Tests for the behavioral economy models (Spec 2)."""
import pytest
from django.db import IntegrityError

from epocha.apps.economy.models import (
    AgentExpectation, BankingState, Currency, GoodCategory,
    Loan, Property, PropertyListing,
)
from epocha.apps.agents.models import Agent
from epocha.apps.simulation.models import Simulation
from epocha.apps.users.models import User
from epocha.apps.world.models import World, Zone
from django.contrib.gis.geos import Point, Polygon


@pytest.fixture
def user(db):
    return User.objects.create_user(email="beh@epocha.dev", username="behuser", password="pass1234")

@pytest.fixture
def simulation(user):
    return Simulation.objects.create(name="BehavioralTest", seed=42, owner=user)

@pytest.fixture
def world(simulation):
    return World.objects.create(simulation=simulation, distance_scale=133.0, tick_duration_hours=24.0)

@pytest.fixture
def zone(world):
    return Zone.objects.create(
        world=world, name="Paris", zone_type="urban",
        boundary=Polygon.from_bbox((0, 0, 100, 100)), center=Point(50, 50),
    )

@pytest.fixture
def lender(simulation, zone):
    return Agent.objects.create(
        simulation=simulation, name="Lender", role="merchant",
        personality={"openness": 0.5}, location=Point(50, 50),
        zone=zone, health=1.0, wealth=500.0,
    )

@pytest.fixture
def borrower(simulation, zone):
    return Agent.objects.create(
        simulation=simulation, name="Borrower", role="farmer",
        personality={"openness": 0.5}, location=Point(50, 50),
        zone=zone, health=1.0, wealth=50.0,
    )

@pytest.fixture
def property_obj(simulation, lender, zone):
    return Property.objects.create(
        simulation=simulation, owner=lender, owner_type="agent",
        zone=zone, property_type="land", name="Farm",
        value=200.0, production_bonus={"subsistence": 1.5},
    )

@pytest.fixture
def currency(simulation):
    return Currency.objects.create(
        simulation=simulation, code="LVR", name="Livre",
        symbol="L", is_primary=True, total_supply=50000.0,
    )


@pytest.mark.django_db
class TestLoan:
    def test_create_bilateral_loan(self, simulation, lender, borrower, property_obj):
        loan = Loan.objects.create(
            simulation=simulation, lender=lender, borrower=borrower,
            lender_type="agent", principal=100.0, interest_rate=0.05,
            remaining_balance=100.0, collateral=property_obj,
            issued_at_tick=1, due_at_tick=10,
        )
        assert loan.principal == 100.0
        assert loan.status == "active"
        assert loan.times_rolled_over == 0

    def test_create_banking_loan(self, simulation, borrower):
        loan = Loan.objects.create(
            simulation=simulation, lender=None, borrower=borrower,
            lender_type="banking", principal=200.0, interest_rate=0.08,
            remaining_balance=200.0, issued_at_tick=1, due_at_tick=20,
        )
        assert loan.lender is None
        assert loan.lender_type == "banking"

    def test_loan_statuses(self, simulation, lender, borrower):
        loan = Loan.objects.create(
            simulation=simulation, lender=lender, borrower=borrower,
            lender_type="agent", principal=50.0, interest_rate=0.03,
            remaining_balance=50.0, issued_at_tick=1, due_at_tick=5,
        )
        loan.status = "defaulted"
        loan.save(update_fields=["status"])
        loan.refresh_from_db()
        assert loan.status == "defaulted"

    def test_rollover_increments(self, simulation, lender, borrower):
        loan = Loan.objects.create(
            simulation=simulation, lender=lender, borrower=borrower,
            lender_type="agent", principal=100.0, interest_rate=0.05,
            remaining_balance=100.0, issued_at_tick=1, due_at_tick=10,
        )
        loan.times_rolled_over = 2
        loan.status = "rolled_over"
        loan.save(update_fields=["times_rolled_over", "status"])
        loan.refresh_from_db()
        assert loan.times_rolled_over == 2


@pytest.mark.django_db
class TestPropertyListing:
    def test_create_listing(self, property_obj):
        listing = PropertyListing.objects.create(
            property=property_obj, asking_price=250.0,
            fundamental_value=200.0, listed_at_tick=5,
        )
        assert listing.asking_price == 250.0
        assert listing.status == "listed"
        assert listing.asking_price > listing.fundamental_value  # speculation

    def test_one_listing_per_property(self, property_obj):
        PropertyListing.objects.create(
            property=property_obj, asking_price=200.0,
            fundamental_value=200.0, listed_at_tick=1,
        )
        with pytest.raises(IntegrityError):
            PropertyListing.objects.create(
                property=property_obj, asking_price=300.0,
                fundamental_value=200.0, listed_at_tick=2,
            )


@pytest.mark.django_db
class TestAgentExpectation:
    def test_create_expectation(self, borrower):
        exp = AgentExpectation.objects.create(
            agent=borrower, good_code="subsistence",
            expected_price=3.5, trend_direction="rising",
            confidence=0.7, lambda_rate=0.35, updated_at_tick=1,
        )
        assert exp.trend_direction == "rising"
        assert exp.lambda_rate == 0.35

    def test_unique_per_agent_good(self, borrower):
        AgentExpectation.objects.create(
            agent=borrower, good_code="subsistence",
            expected_price=3.0, trend_direction="stable",
            confidence=0.5, lambda_rate=0.3, updated_at_tick=1,
        )
        with pytest.raises(IntegrityError):
            AgentExpectation.objects.create(
                agent=borrower, good_code="subsistence",
                expected_price=4.0, trend_direction="rising",
                confidence=0.8, lambda_rate=0.4, updated_at_tick=2,
            )


@pytest.mark.django_db
class TestBankingState:
    def test_create_banking_state(self, simulation):
        bs = BankingState.objects.create(
            simulation=simulation, total_deposits=10000.0,
            total_loans_outstanding=5000.0, reserve_ratio=0.1,
            base_interest_rate=0.05,
        )
        assert bs.is_solvent is True
        assert bs.confidence_index == 1.0

    def test_one_per_simulation(self, simulation):
        BankingState.objects.create(
            simulation=simulation, reserve_ratio=0.1,
            base_interest_rate=0.05,
        )
        with pytest.raises(IntegrityError):
            BankingState.objects.create(
                simulation=simulation, reserve_ratio=0.2,
                base_interest_rate=0.06,
            )
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `docker compose -f docker-compose.local.yml run --rm web pytest epocha/apps/economy/tests/test_models_behavioral.py -v`

Expected: ImportError (Loan not in models).

- [ ] **Step 3: Append 4 models to models.py**

APPEND to `epocha/apps/economy/models.py` after EconomyTemplate:

```python
class Loan(models.Model):
    """A debt contract between two parties.

    Loans can be bilateral (agent-to-agent) or institutional (banking
    system to agent). The Minsky classification (hedge/speculative/Ponzi)
    is computed dynamically from the borrower's income vs debt service.

    Rollover: when a loan reaches due_at_tick and the borrower cannot
    repay the principal but CAN pay interest, the loan can be rolled
    over with potentially worse terms. This enables Minsky's speculative
    finance stage.

    Source: Minsky (1986) for the instability cycle.
    Source: Stiglitz & Weiss (1981) for credit rationing via collateral.
    """

    LENDER_TYPES = [
        ("agent", "Agent (bilateral)"),
        ("banking", "Banking institution"),
    ]

    STATUS_CHOICES = [
        ("active", "Active"),
        ("repaid", "Repaid"),
        ("defaulted", "Defaulted"),
        ("rolled_over", "Rolled over into new loan"),
    ]

    simulation = models.ForeignKey(
        "simulation.Simulation", on_delete=models.CASCADE,
        related_name="loans",
    )
    lender = models.ForeignKey(
        "agents.Agent", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="loans_given",
    )
    borrower = models.ForeignKey(
        "agents.Agent", on_delete=models.CASCADE,
        related_name="loans_taken",
    )
    lender_type = models.CharField(max_length=20, choices=LENDER_TYPES)
    principal = models.FloatField(
        help_text="Original loan amount in primary currency",
    )
    interest_rate = models.FloatField(
        help_text="Per-tick interest rate. Determined by credit market "
                  "equilibrium (Wicksell 1898) adjusted for borrower risk "
                  "(Stiglitz & Weiss 1981).",
    )
    remaining_balance = models.FloatField()
    collateral = models.ForeignKey(
        "economy.Property", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="securing_loans",
    )
    issued_at_tick = models.PositiveIntegerField()
    due_at_tick = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="Null for demand loans (callable at any time)",
    )
    times_rolled_over = models.PositiveIntegerField(
        default=0,
        help_text="Minsky: hedge=0 rollovers, speculative=1+, "
                  "Ponzi=cannot service interest.",
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")

    class Meta:
        indexes = [
            models.Index(fields=["simulation", "status"]),
            models.Index(fields=["borrower", "status"]),
            models.Index(fields=["lender", "status"]),
        ]

    def __str__(self):
        return f"Loan {self.principal} ({self.status}) {self.borrower}"


class PropertyListing(models.Model):
    """A property offered for sale on the market.

    Fundamental value computed via Gordon Growth Model (Gordon 1959):
    P = R / max(r - g, 0.01). The gap between asking_price and
    fundamental_value measures speculative excess (bubble component).

    Source: Gordon (1959) for the dividend discount model.
    """

    property = models.OneToOneField(
        "economy.Property", on_delete=models.CASCADE,
        related_name="listing",
    )
    asking_price = models.FloatField()
    fundamental_value = models.FloatField(
        help_text="Gordon model: R / max(r - g, 0.01)",
    )
    listed_at_tick = models.PositiveIntegerField()
    status = models.CharField(
        max_length=20,
        choices=[("listed", "Listed"), ("sold", "Sold"), ("withdrawn", "Withdrawn")],
        default="listed",
    )

    def __str__(self):
        return f"Listing {self.property.name} at {self.asking_price}"


class AgentExpectation(models.Model):
    """An agent's adaptive expectation about a future price.

    Updated each tick via Nerlove (1958):
        E(P_t+1) = lambda * P_t + (1 - lambda) * E(P_t)

    Lambda is modulated by Big Five personality (Costa & McCrae 1992):
    - Neuroticism: +0.15 per 0.5 deviation (overreacts)
    - Openness: +0.10 (embraces novelty)
    - Conscientiousness: -0.10 (cautious)

    These coefficients are tunable design parameters inspired by
    personality research but without direct empirical calibration.

    Source: Nerlove (1958), Simon (1955), Hommes (2011).
    """

    agent = models.ForeignKey(
        "agents.Agent", on_delete=models.CASCADE,
        related_name="expectations",
    )
    good_code = models.CharField(max_length=30)
    expected_price = models.FloatField()
    trend_direction = models.CharField(
        max_length=10,
        choices=[("rising", "Rising"), ("falling", "Falling"), ("stable", "Stable")],
    )
    confidence = models.FloatField(default=0.5)
    lambda_rate = models.FloatField(
        help_text="Adaptation speed from Big Five. Tunable.",
    )
    updated_at_tick = models.PositiveIntegerField()

    class Meta:
        unique_together = ("agent", "good_code")
        indexes = [models.Index(fields=["agent", "good_code"])]

    def __str__(self):
        return f"{self.agent.name} expects {self.good_code} {self.trend_direction}"


class BankingState(models.Model):
    """Aggregate state of the banking system for a simulation.

    Spec 2 models banking as a single institutional entity.
    Spec 3 will introduce multiple independent banks as agents.

    Fractional reserve: bank retains reserve_ratio of deposits, lends
    the rest. Theoretical multiplier = 1/reserve_ratio. ACTUAL multiplier
    is computed as total_loans/total_deposits and will be lower.
    The theoretical max is a cap, not a target.

    Source: Diamond & Dybvig (1983) for the fractional reserve model.
    """

    simulation = models.OneToOneField(
        "simulation.Simulation", on_delete=models.CASCADE,
        related_name="banking_state",
    )
    total_deposits = models.FloatField(default=0.0)
    total_loans_outstanding = models.FloatField(default=0.0)
    reserve_ratio = models.FloatField(
        help_text="Fraction of deposits held in reserve (default 0.1 = 10%)",
    )
    base_interest_rate = models.FloatField(
        help_text="Base lending rate. Adjusted by credit market each tick "
                  "(Wicksell 1898).",
    )
    is_solvent = models.BooleanField(default=True)
    confidence_index = models.FloatField(
        default=1.0,
        help_text="Public confidence (0-1). Drops trigger withdrawal "
                  "pressure via information flow (Diamond & Dybvig 1983).",
    )

    def __str__(self):
        return f"Banking ({self.simulation.name}): deposits={self.total_deposits:.0f}"
```

- [ ] **Step 4: Generate and apply migration**

Run:
```bash
docker compose -f docker-compose.local.yml run --rm web python manage.py makemigrations economy --name behavioral
docker compose -f docker-compose.local.yml run --rm web python manage.py migrate economy
```

- [ ] **Step 5: Run model tests**

Run: `docker compose -f docker-compose.local.yml run --rm web pytest epocha/apps/economy/tests/test_models_behavioral.py -v`

Expected: all PASS.

- [ ] **Step 6: Commit**

```
feat(economy): add Loan, PropertyListing, AgentExpectation, BankingState models

CHANGE: Add the 4 behavioral economy models: Loan with rollover support
for Minsky cycle (Minsky 1986), PropertyListing with Gordon fundamental
value (Gordon 1959), AgentExpectation with Nerlove adaptive formula
(Nerlove 1958) and Big Five lambda modulation, BankingState with
fractional reserve (Diamond & Dybvig 1983).
```

---

### Task 2: Template extensions

**Files:**
- Modify: `epocha/apps/economy/template_loader.py`
- New: `epocha/apps/economy/tests/test_template_behavioral.py`

- [ ] **Step 1: Write the failing tests**

Create `epocha/apps/economy/tests/test_template_behavioral.py`:

```python
"""Tests for behavioral economy template extensions."""
import pytest

from epocha.apps.economy.models import EconomyTemplate
from epocha.apps.economy.template_loader import load_default_templates, get_template


@pytest.mark.django_db
class TestBehavioralTemplateConfig:
    def test_pre_industrial_has_credit_config(self):
        load_default_templates()
        t = get_template("pre_industrial")
        assert "credit_config" in t.config
        assert "loan_to_value_ratio" in t.config["credit_config"]

    def test_pre_industrial_has_banking_config(self):
        load_default_templates()
        t = get_template("pre_industrial")
        assert "banking_config" in t.config
        assert "reserve_ratio" in t.config["banking_config"]

    def test_pre_industrial_has_expectations_config(self):
        load_default_templates()
        t = get_template("pre_industrial")
        assert "expectations_config" in t.config
        assert "lambda_base" in t.config["expectations_config"]

    def test_pre_industrial_conservative_credit(self):
        load_default_templates()
        t = get_template("pre_industrial")
        # Pre-industrial: conservative lending (0.5 LTV)
        assert t.config["credit_config"]["loan_to_value_ratio"] <= 0.6

    def test_modern_higher_credit(self):
        load_default_templates()
        t = get_template("modern")
        # Modern: more aggressive lending
        assert t.config["credit_config"]["loan_to_value_ratio"] >= 0.7

    def test_all_templates_have_behavioral_config(self):
        load_default_templates()
        for name in ["pre_industrial", "industrial", "modern", "sci_fi"]:
            t = get_template(name)
            assert "credit_config" in t.config, f"{name} missing credit_config"
            assert "banking_config" in t.config, f"{name} missing banking_config"
            assert "expectations_config" in t.config, f"{name} missing expectations_config"

    def test_has_expropriation_policies(self):
        load_default_templates()
        t = get_template("pre_industrial")
        assert "expropriation_policies" in t.config
        assert t.config["expropriation_policies"].get("democracy") == "none"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `docker compose -f docker-compose.local.yml run --rm web pytest epocha/apps/economy/tests/test_template_behavioral.py -v`

Expected: KeyError (no credit_config in template.config).

- [ ] **Step 3: Add behavioral config to templates**

In `epocha/apps/economy/template_loader.py`, update each template builder function to include behavioral config in the `config` field. The `config` JSONField on EconomyTemplate is the extensible catch-all.

Add a shared behavioral config builder at module level:

```python
def _behavioral_config(
    loan_to_value_ratio=0.6,
    base_interest_rate=0.05,
    risk_premium=1.0,
    max_loan_duration_ticks=20,
    credit_adj_rate=0.02,
    default_cascade_max_depth=3,
    reserve_ratio=0.1,
    initial_deposits=10000.0,
    lambda_base=0.3,
    neuroticism_modifier=0.3,
    openness_modifier=0.2,
    conscientiousness_modifier=0.2,
    trend_threshold=0.02,
):
    """Build behavioral economy config for a template.

    All values are tunable design parameters. See spec for scientific
    rationale of each parameter.
    """
    return {
        "credit_config": {
            "loan_to_value_ratio": loan_to_value_ratio,
            "base_interest_rate": base_interest_rate,
            "risk_premium": risk_premium,
            "max_loan_duration_ticks": max_loan_duration_ticks,
            "credit_adj_rate": credit_adj_rate,
            "default_cascade_max_depth": default_cascade_max_depth,
        },
        "banking_config": {
            "reserve_ratio": reserve_ratio,
            "initial_deposits": initial_deposits,
        },
        "expectations_config": {
            "lambda_base": lambda_base,
            "neuroticism_modifier": neuroticism_modifier,
            "openness_modifier": openness_modifier,
            "conscientiousness_modifier": conscientiousness_modifier,
            "trend_threshold": trend_threshold,
        },
        "expropriation_policies": {
            "democracy": "none",
            "illiberal_democracy": "none",
            "monarchy": "none",
            "autocracy": "elite_seizure",
            "oligarchy": "none",
            "theocracy": "none",
            "totalitarian": "nationalize_all",
            "terrorist_regime": "elite_seizure",
            "anarchy": "none",
            "federation": "none",
            "kleptocracy": "elite_seizure",
            "junta": "elite_seizure",
        },
    }
```

Then in each template builder, add the behavioral config to the returned dict's `config` field. For `_pre_industrial_template`, add at the end of the returned dict (inside the function, before `return`):

```python
    result = { ... existing template dict ... }
    result["config"] = _behavioral_config(
        loan_to_value_ratio=0.5,  # conservative pre-industrial lending
        base_interest_rate=0.08,  # high rates (usury common)
        initial_deposits=5000.0,  # small banking system
    )
    return result
```

For `_industrial_template`:
```python
    result["config"] = _behavioral_config(
        loan_to_value_ratio=0.6,
        base_interest_rate=0.06,
        initial_deposits=20000.0,
    )
```

For `_modern_template`:
```python
    result["config"] = _behavioral_config(
        loan_to_value_ratio=0.8,  # aggressive modern lending
        base_interest_rate=0.03,  # low modern rates
        initial_deposits=100000.0,
        reserve_ratio=0.05,  # lower modern reserves
    )
```

For `_sci_fi_template`:
```python
    result["config"] = _behavioral_config(
        loan_to_value_ratio=0.9,
        base_interest_rate=0.02,
        initial_deposits=500000.0,
        reserve_ratio=0.03,
    )
```

Also update the `load_default_templates` function: since templates use `get_or_create`, existing templates won't be updated. Add logic to update the `config` field of existing templates if it's empty:

```python
def load_default_templates() -> None:
    for name, builder in _TEMPLATE_BUILDERS.items():
        data = builder()
        template, created = EconomyTemplate.objects.get_or_create(
            name=name,
            defaults={ ... existing defaults ... },
        )
        # Update config for existing templates that lack behavioral config
        if not created and "credit_config" not in (template.config or {}):
            template.config = data.get("config", {})
            template.save(update_fields=["config"])
```

- [ ] **Step 4: Run template tests**

Run: `docker compose -f docker-compose.local.yml run --rm web pytest epocha/apps/economy/tests/test_template_behavioral.py -v`

Expected: all PASS.

- [ ] **Step 5: Commit**

```
feat(economy): add behavioral config to economy templates

CHANGE: Extend the 4 era templates with credit, banking, expectations,
and expropriation configuration. Pre-industrial has conservative lending
(0.5 LTV, 8% rate); modern has aggressive (0.8 LTV, 3% rate). Reserve
ratios decrease from 10% to 3% across eras. Expropriation policies map
all 12 government types.
```

---

### Task 3: Expectations engine

**Files:**
- Create: `epocha/apps/economy/expectations.py`
- Modify: `epocha/apps/economy/engine.py` (add expectations step)
- New: `epocha/apps/economy/tests/test_expectations.py`

- [ ] **Step 1: Write the failing tests**

Create `epocha/apps/economy/tests/test_expectations.py`:

```python
"""Tests for the adaptive expectations engine.

Source: Nerlove (1958) for the formula.
Source: Costa & McCrae (1992) for Big Five modulation.
"""
import pytest

from epocha.apps.economy.expectations import (
    compute_lambda_from_personality,
    update_agent_expectations,
    detect_trend,
)


class TestComputeLambda:
    def test_neutral_personality_base_lambda(self):
        personality = {"neuroticism": 0.5, "openness": 0.5, "conscientiousness": 0.5}
        lam = compute_lambda_from_personality(personality, lambda_base=0.3)
        assert abs(lam - 0.3) < 0.01

    def test_high_neuroticism_increases_lambda(self):
        high_n = {"neuroticism": 0.9, "openness": 0.5, "conscientiousness": 0.5}
        neutral = {"neuroticism": 0.5, "openness": 0.5, "conscientiousness": 0.5}
        lam_high = compute_lambda_from_personality(high_n, lambda_base=0.3)
        lam_neutral = compute_lambda_from_personality(neutral, lambda_base=0.3)
        assert lam_high > lam_neutral

    def test_high_conscientiousness_decreases_lambda(self):
        high_c = {"neuroticism": 0.5, "openness": 0.5, "conscientiousness": 0.9}
        neutral = {"neuroticism": 0.5, "openness": 0.5, "conscientiousness": 0.5}
        lam_high = compute_lambda_from_personality(high_c, lambda_base=0.3)
        lam_neutral = compute_lambda_from_personality(neutral, lambda_base=0.3)
        assert lam_high < lam_neutral

    def test_lambda_clamped_min(self):
        # Very low reactivity personality
        low_all = {"neuroticism": 0.0, "openness": 0.0, "conscientiousness": 1.0}
        lam = compute_lambda_from_personality(low_all, lambda_base=0.3)
        assert lam >= 0.05

    def test_lambda_clamped_max(self):
        # Very high reactivity personality
        high_all = {"neuroticism": 1.0, "openness": 1.0, "conscientiousness": 0.0}
        lam = compute_lambda_from_personality(high_all, lambda_base=0.3)
        assert lam <= 0.95


class TestDetectTrend:
    def test_rising(self):
        assert detect_trend(expected=3.5, actual=3.0, threshold=0.02) == "rising"

    def test_falling(self):
        assert detect_trend(expected=2.5, actual=3.0, threshold=0.02) == "falling"

    def test_stable(self):
        assert detect_trend(expected=3.01, actual=3.0, threshold=0.02) == "stable"


class TestNerloveUpdate:
    def test_price_increase_raises_expectation(self):
        # Nerlove: E_new = lambda * P_actual + (1-lambda) * E_old
        # With lambda=0.3, P=4.0, E_old=3.0: E_new = 0.3*4 + 0.7*3 = 3.3
        e_old = 3.0
        p_actual = 4.0
        lam = 0.3
        e_new = lam * p_actual + (1 - lam) * e_old
        assert abs(e_new - 3.3) < 0.01

    def test_stable_price_keeps_expectation(self):
        e_old = 3.0
        p_actual = 3.0
        lam = 0.3
        e_new = lam * p_actual + (1 - lam) * e_old
        assert abs(e_new - 3.0) < 0.01
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `docker compose -f docker-compose.local.yml run --rm web pytest epocha/apps/economy/tests/test_expectations.py -v`

Expected: ImportError.

- [ ] **Step 3: Implement expectations.py**

Create `epocha/apps/economy/expectations.py`:

```python
"""Adaptive expectations engine with Big Five personality modulation.

Agents form expectations about future prices by updating prior beliefs
with current observations. The adaptation speed (lambda) depends on
personality: neurotic agents overreact, conscientious agents are cautious.

Formula (Nerlove 1958):
    E(P_t+1) = lambda * P_t + (1 - lambda) * E(P_t)

Lambda modulation (inspired by Costa & McCrae 1992; specific coefficients
are tunable design parameters, not empirically calibrated):
    lambda = lambda_base
        + (neuroticism - 0.5) * neuroticism_modifier
        + (openness - 0.5) * openness_modifier
        - (conscientiousness - 0.5) * conscientiousness_modifier
    lambda = clamp(lambda, 0.05, 0.95)

Source: Nerlove (1958) "Adaptive Expectations and Cobweb Phenomena."
Source: Simon (1955) for bounded rationality justification.
Source: Hommes (2011) for empirical support of heterogeneous adaptive rules.
"""
from __future__ import annotations

import logging

from epocha.apps.economy.models import AgentExpectation, GoodCategory, ZoneEconomy

logger = logging.getLogger(__name__)

# Lambda bounds. Clamped to prevent extreme behavior.
# 0.05 = almost never updates (very rigid), 0.95 = almost ignores history.
# Tunable design parameters.
_LAMBDA_MIN = 0.05
_LAMBDA_MAX = 0.95

# Default personality modifiers if not provided by template.
# Tunable design parameters inspired by Costa & McCrae (1992) but
# without direct empirical calibration of these specific values.
_DEFAULT_NEUROTICISM_MOD = 0.3
_DEFAULT_OPENNESS_MOD = 0.2
_DEFAULT_CONSCIENTIOUSNESS_MOD = 0.2
_DEFAULT_TREND_THRESHOLD = 0.02


def compute_lambda_from_personality(
    personality: dict,
    lambda_base: float = 0.3,
    neuroticism_modifier: float = _DEFAULT_NEUROTICISM_MOD,
    openness_modifier: float = _DEFAULT_OPENNESS_MOD,
    conscientiousness_modifier: float = _DEFAULT_CONSCIENTIOUSNESS_MOD,
) -> float:
    """Compute adaptation speed from Big Five personality traits.

    Higher lambda = faster adaptation to new information (reactive).
    Lower lambda = slower adaptation (conservative, relies on history).

    The modifiers scale the deviation from the trait midpoint (0.5).
    A perfectly neutral agent (all traits at 0.5) gets lambda_base.
    """
    neuroticism = personality.get("neuroticism", 0.5)
    openness = personality.get("openness", 0.5)
    conscientiousness = personality.get("conscientiousness", 0.5)

    lam = lambda_base
    lam += (neuroticism - 0.5) * neuroticism_modifier
    lam += (openness - 0.5) * openness_modifier
    lam -= (conscientiousness - 0.5) * conscientiousness_modifier

    return max(_LAMBDA_MIN, min(_LAMBDA_MAX, lam))


def detect_trend(
    expected: float,
    actual: float,
    threshold: float = _DEFAULT_TREND_THRESHOLD,
) -> str:
    """Classify the price trend based on expectation vs actual.

    Returns "rising" if expected > actual * (1 + threshold),
    "falling" if expected < actual * (1 - threshold), else "stable".
    """
    if actual <= 0:
        return "stable"
    ratio = expected / actual
    if ratio > 1.0 + threshold:
        return "rising"
    elif ratio < 1.0 - threshold:
        return "falling"
    return "stable"


def update_agent_expectations(simulation, tick: int) -> None:
    """Update price expectations for all agents in the simulation.

    For each agent, for each good category, applies the Nerlove (1958)
    adaptive expectations formula with personality-modulated lambda.

    This function runs as step 2 in the tick pipeline, after production
    and before market clearing.
    """
    from epocha.apps.agents.models import Agent

    goods = list(GoodCategory.objects.filter(simulation=simulation))
    if not goods:
        return

    # Get expectations config from template (if available)
    try:
        from epocha.apps.economy.models import EconomyTemplate
        # Try to find config from any existing BankingState or template
        config = {}
        # Look for behavioral config in simulation's template
        # (stored in EconomyTemplate.config or simulation-level config)
        templates = EconomyTemplate.objects.all()
        for t in templates:
            if t.config and "expectations_config" in t.config:
                config = t.config["expectations_config"]
                break
    except Exception:
        config = {}

    lambda_base = config.get("lambda_base", 0.3)
    n_mod = config.get("neuroticism_modifier", _DEFAULT_NEUROTICISM_MOD)
    o_mod = config.get("openness_modifier", _DEFAULT_OPENNESS_MOD)
    c_mod = config.get("conscientiousness_modifier", _DEFAULT_CONSCIENTIOUSNESS_MOD)
    trend_threshold = config.get("trend_threshold", _DEFAULT_TREND_THRESHOLD)

    agents = Agent.objects.filter(simulation=simulation, is_alive=True)

    # Get current prices from zone economies
    zone_prices: dict[int, dict[str, float]] = {}
    for ze in ZoneEconomy.objects.filter(zone__world__simulation=simulation).select_related("zone"):
        zone_prices[ze.zone_id] = ze.market_prices

    for agent in agents:
        if not agent.zone_id or agent.zone_id not in zone_prices:
            continue

        current_prices = zone_prices[agent.zone_id]
        lam = compute_lambda_from_personality(
            agent.personality, lambda_base, n_mod, o_mod, c_mod,
        )

        for good in goods:
            actual_price = current_prices.get(good.code, good.base_price)

            # Get or create expectation
            exp, created = AgentExpectation.objects.get_or_create(
                agent=agent,
                good_code=good.code,
                defaults={
                    "expected_price": actual_price,
                    "trend_direction": "stable",
                    "confidence": 0.5,
                    "lambda_rate": lam,
                    "updated_at_tick": tick,
                },
            )

            if not created:
                # Nerlove (1958) adaptive expectations formula:
                # E(P_t+1) = lambda * P_actual + (1 - lambda) * E_old
                e_old = exp.expected_price
                e_new = lam * actual_price + (1.0 - lam) * e_old

                trend = detect_trend(e_new, actual_price, trend_threshold)

                # Confidence: higher when expectation is close to actual
                if actual_price > 0:
                    confidence = 1.0 - min(1.0, abs(e_new - actual_price) / actual_price)
                    confidence = max(0.1, confidence)
                else:
                    confidence = 0.5

                exp.expected_price = e_new
                exp.trend_direction = trend
                exp.confidence = confidence
                exp.lambda_rate = lam
                exp.updated_at_tick = tick
                exp.save(update_fields=[
                    "expected_price", "trend_direction", "confidence",
                    "lambda_rate", "updated_at_tick",
                ])
```

- [ ] **Step 4: Run expectations tests**

Run: `docker compose -f docker-compose.local.yml run --rm web pytest epocha/apps/economy/tests/test_expectations.py -v`

Expected: all PASS.

- [ ] **Step 5: Add expectations to engine pipeline**

In `epocha/apps/economy/engine.py`, add the expectations update call after production and before market clearing. Find the section comment `# === STEP 2: MARKET CLEARING` and insert before it:

```python
    # === STEP 2: EXPECTATIONS UPDATE (Nerlove 1958) ===
    from epocha.apps.economy.expectations import update_agent_expectations
    update_agent_expectations(simulation, tick)
```

- [ ] **Step 6: Run full test suite**

Run: `docker compose -f docker-compose.local.yml run --rm web pytest -q -m "not slow"`

Expected: all tests pass.

- [ ] **Step 7: Commit**

```
feat(economy): add adaptive expectations engine with Big Five modulation

CHANGE: Implement Nerlove (1958) adaptive expectations formula with
personality-modulated lambda (Costa & McCrae 1992 inspired, tunable).
Agents form expectations about future prices from trends, with
neuroticism increasing reactivity and conscientiousness decreasing it.
Integrated into the tick pipeline as step 2 (after production, before
market clearing).
```

---

## Self-Review Summary

After completing Tasks 1-3 in this plan:

- 4 new models: Loan (Minsky), PropertyListing (Gordon), AgentExpectation (Nerlove), BankingState (Diamond & Dybvig)
- Template extensions with credit, banking, expectations, and expropriation config for all 4 eras
- Expectations engine with Big Five personality modulation running each tick
- Agents now form adaptive price expectations that will drive speculation (Part 3)

**What is NOT yet in place:**
- Loan creation, interest, rollover, default, cascade (Part 2)
- Interest rate determination via credit market (Part 2)
- Banking fractional reserve mechanics (Part 2)
- Property listing, bidding, transfer, Gordon valuation (Part 3)
- Expropriation mechanism (Part 3)
- Decision prompt with debt/expectations context (Part 3)
- Bank run emergence via information flow (Part 3)

# Economy Behavioral Integration Plan -- Part 3a: Foundations

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire the behavioral economy prerequisites and context: save all template configs to simulation.config, add DecisionLog index and new transaction types, extend the economic context with expectations/debt/banking blocks, integrate hoard-expectations link, add banking initialization + deposit recalculation + concern broadcast, and handle dead agent loan defaults.

**Architecture:** Modifications to existing modules only (no new files except tests). The extended context gives agents full economic visibility; the hoard link creates the self-fulfilling prophecy loop; the banking subsystem becomes fully operational; dead agents' loans are properly handled.

**Tech Stack:** Django ORM, PostgreSQL.

**Spec:** `docs/superpowers/specs/2026-04-15-economy-behavioral-integration-design.md`

**Follow-up plans:**
- Part 3b -- Property market + new actions (borrow, sell_property, buy_property, expropriation)
- Part 3c -- End-to-end integration test

---

## File Structure (Part 3a scope)

| File | Responsibility | New/Modify |
|------|---------------|------------|
| `epocha/apps/economy/models.py` | Add new transaction types to EconomicLedger | Modify |
| `epocha/apps/agents/models.py` | Add composite index to DecisionLog | Modify |
| `epocha/apps/economy/initialization.py` | Save all template configs + call initialize_banking | Modify |
| `epocha/apps/economy/context.py` | Add expectations, debt, Minsky, banking blocks | Modify |
| `epocha/apps/economy/engine.py` | Hoard flag from DecisionLog, deposit recalc, banking concern | Modify |
| `epocha/apps/economy/banking.py` | Add broadcast_banking_concern, recalculate_deposits | Modify |
| `epocha/apps/economy/credit.py` | Dead agent loan default, double-pledge check helper | Modify |
| `epocha/apps/economy/tests/test_context_behavioral.py` | Tests for extended context | New |
| `epocha/apps/economy/tests/test_banking_behavioral.py` | Tests for deposits + concern broadcast | New |
| `epocha/apps/economy/tests/test_hoard_link.py` | Tests for hoard flag propagation | New |

---

## Tasks summary

1. **Model updates** -- new transaction types + DecisionLog index + migration
2. **Initialization fix** -- save all configs + call initialize_banking
3. **Extended economic context** -- expectations, debt, Minsky, banking blocks
4. **Hoard-expectations link** -- hoard flag from previous tick DecisionLog
5. **Banking: deposits + concern broadcast** -- dynamic deposits, banking concern
6. **Credit: dead agents + double-pledge** -- dead agent default, collateral check

---

### Task 1: Model updates

**Files:**
- Modify: `epocha/apps/economy/models.py`
- Modify: `epocha/apps/agents/models.py`
- New: migration (auto-generated)

- [ ] **Step 1: Add new transaction types to EconomicLedger**

In `epocha/apps/economy/models.py`, replace the TRANSACTION_TYPES list:

```python
    TRANSACTION_TYPES = [
        ("production", "Production"),
        ("trade", "Trade"),
        ("tax", "Tax"),
        ("rent", "Rent"),
        ("wage", "Wage"),
        ("property_sale", "Property Sale"),
        ("loan_issued", "Loan Issued"),
        ("loan_interest", "Loan Interest"),
        ("expropriation", "Expropriation"),
    ]
```

- [ ] **Step 2: Add composite index to DecisionLog**

In `epocha/apps/agents/models.py`, add `indexes` to DecisionLog.Meta:

```python
    class Meta:
        ordering = ["tick"]
        indexes = [
            models.Index(fields=["simulation", "tick"]),
        ]
```

- [ ] **Step 3: Generate and apply migration**

Run:
```bash
python manage.py makemigrations economy agents
python manage.py migrate
```

Expected: migration created and applied successfully.

- [ ] **Step 4: Verify existing tests still pass**

Run: `pytest epocha/apps/economy/tests/ epocha/apps/agents/ -x -q`
Expected: all existing tests pass (no behavior change, only schema additions).

- [ ] **Step 5: Commit**

```bash
git add epocha/apps/economy/models.py epocha/apps/agents/models.py epocha/apps/economy/migrations/ epocha/apps/agents/migrations/
git commit -m "feat(economy): add transaction types and DecisionLog index

CHANGE: Add property_sale, loan_issued, loan_interest, expropriation to
EconomicLedger.TRANSACTION_TYPES. Add composite index (simulation, tick)
to DecisionLog for efficient previous-tick queries."
```

---

### Task 2: Initialization fix

**Files:**
- Modify: `epocha/apps/economy/initialization.py`
- Modify: `epocha/apps/economy/tests/test_initialization.py`

- [ ] **Step 1: Write the failing test**

Add to `epocha/apps/economy/tests/test_initialization.py`:

```python
class TestInitializationBehavioralConfig:
    """Test that initialize_economy saves behavioral configs to simulation.config."""

    @pytest.mark.django_db
    def test_saves_credit_config(self, simulation_with_economy):
        """Credit config from template must be in simulation.config."""
        sim = simulation_with_economy
        sim_config = sim.config or {}
        assert "credit_config" in sim_config
        assert "loan_to_value" in sim_config["credit_config"]

    @pytest.mark.django_db
    def test_saves_banking_config(self, simulation_with_economy):
        """Banking config from template must be in simulation.config."""
        sim = simulation_with_economy
        sim_config = sim.config or {}
        assert "banking_config" in sim_config
        assert "base_interest_rate" in sim_config["banking_config"]

    @pytest.mark.django_db
    def test_saves_expectations_config(self, simulation_with_economy):
        """Expectations config from template must be in simulation.config."""
        sim = simulation_with_economy
        sim_config = sim.config or {}
        assert "expectations_config" in sim_config
        assert "lambda_base" in sim_config["expectations_config"]

    @pytest.mark.django_db
    def test_saves_expropriation_policies(self, simulation_with_economy):
        """Expropriation policies from template must be in simulation.config."""
        sim = simulation_with_economy
        sim_config = sim.config or {}
        assert "expropriation_policies" in sim_config
        assert "democracy" in sim_config["expropriation_policies"]

    @pytest.mark.django_db
    def test_banking_state_created(self, simulation_with_economy):
        """BankingState must be created during initialization."""
        from epocha.apps.economy.models import BankingState
        sim = simulation_with_economy
        assert BankingState.objects.filter(simulation=sim).exists()
```

Note: `simulation_with_economy` is the existing fixture in the test file that creates a simulation and calls `initialize_economy`. If it doesn't exist, create it by calling `initialize_economy(simulation, "pre_industrial")` in a fixture.

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest epocha/apps/economy/tests/test_initialization.py::TestInitializationBehavioralConfig -v`
Expected: FAIL -- `credit_config` not in sim.config, BankingState not created.

- [ ] **Step 3: Implement the fix in initialization.py**

In `epocha/apps/economy/initialization.py`, after the line `sim_config["production_config"] = {` block (around line 160-166), extend to save all configs:

```python
    # Store production config on simulation.config so the engine can
    # access template-level settings without re-reading the template.
    sim_config = simulation.config or {}
    sim_config["production_config"] = {
        "default_sigma": default_sigma,
        "role_production": role_production,
        "zone_type_resources": zone_type_resources,
    }

    # Save behavioral economy configs from the template so that
    # credit, banking, expectations, and expropriation subsystems
    # can read their parameters from simulation.config at runtime.
    # Without this, all behavioral lookups fall back to hardcoded
    # defaults, ignoring era-specific template calibration.
    template_behavioral = template.config or {}
    if template_behavioral.get("credit_config"):
        sim_config["credit_config"] = template_behavioral["credit_config"]
    if template_behavioral.get("banking_config"):
        sim_config["banking_config"] = template_behavioral["banking_config"]
    if template_behavioral.get("expectations_config"):
        sim_config["expectations_config"] = template_behavioral["expectations_config"]
    if template_behavioral.get("expropriation_policies"):
        sim_config["expropriation_policies"] = template_behavioral["expropriation_policies"]

    simulation.config = sim_config
    simulation.save(update_fields=["config"])
```

Then, at the end of `initialize_economy` (before the logger.info and return), add:

```python
    # 8. Banking system initialization
    from .banking import initialize_banking
    initialize_banking(simulation)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest epocha/apps/economy/tests/test_initialization.py -v`
Expected: all pass, including the new TestInitializationBehavioralConfig tests.

- [ ] **Step 5: Run full economy test suite**

Run: `pytest epocha/apps/economy/tests/ -x -q`
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add epocha/apps/economy/initialization.py epocha/apps/economy/tests/test_initialization.py
git commit -m "feat(economy): save behavioral configs and init banking

CHANGE: initialize_economy now saves credit_config, banking_config,
expectations_config, and expropriation_policies from the template into
simulation.config. Also calls initialize_banking to create BankingState."
```

---

### Task 3: Extended economic context

**Files:**
- Modify: `epocha/apps/economy/context.py`
- Create: `epocha/apps/economy/tests/test_context_behavioral.py`

- [ ] **Step 1: Write the failing tests**

Create `epocha/apps/economy/tests/test_context_behavioral.py`:

```python
"""Tests for the extended economic context (behavioral blocks).

Verifies that build_economic_context includes expectations, debt/Minsky
classification, and banking state information when the relevant data exists.
"""
import pytest
from django.test import TestCase

from epocha.apps.agents.models import Agent
from epocha.apps.economy.context import build_economic_context
from epocha.apps.economy.initialization import initialize_economy
from epocha.apps.economy.models import (
    AgentExpectation,
    BankingState,
    Currency,
    Loan,
    Property,
)
from epocha.apps.economy.template_loader import load_default_templates
from epocha.apps.simulation.models import Simulation
from epocha.apps.world.models import World, Zone


@pytest.fixture
def behavioral_context_setup(db):
    """Create a simulation with economy, expectations, loans, and banking."""
    sim = Simulation.objects.create(name="ctx_test", config={})
    world = World.objects.create(
        simulation=sim, name="ctx_world", stability_index=0.8,
    )
    zone = Zone.objects.create(
        world=world, name="Paris", zone_type="urban",
    )
    agent = Agent.objects.create(
        simulation=sim, name="Marie", role="merchant",
        personality={"neuroticism": 0.7, "openness": 0.5, "conscientiousness": 0.3},
        zone=zone, wealth=200.0, mood=0.6, health=0.9,
    )
    initialize_economy(sim, "pre_industrial")
    sim.refresh_from_db()
    return sim, agent, zone


@pytest.mark.django_db
class TestExpectationsBlock:
    def test_expectations_shown_when_present(self, behavioral_context_setup):
        sim, agent, zone = behavioral_context_setup
        AgentExpectation.objects.create(
            agent=agent, good_code="subsistence",
            expected_price=3.5, trend_direction="rising",
            confidence=0.8, lambda_rate=0.3, updated_at_tick=1,
        )
        result = build_economic_context(agent, tick=2)
        assert result is not None
        assert "Price expectations" in result
        assert "RISING" in result
        assert "subsistence" in result.lower()

    def test_no_expectations_block_when_none_exist(self, behavioral_context_setup):
        sim, agent, zone = behavioral_context_setup
        result = build_economic_context(agent, tick=1)
        assert result is not None
        # Should have basic context but no expectations block
        assert "Price expectations" not in result


@pytest.mark.django_db
class TestDebtBlock:
    def test_debt_shown_when_loans_exist(self, behavioral_context_setup):
        sim, agent, zone = behavioral_context_setup
        currency = Currency.objects.get(simulation=sim, is_primary=True)
        Loan.objects.create(
            simulation=sim, borrower=agent, lender_type="banking",
            principal=100.0, interest_rate=0.05, remaining_balance=100.0,
            issued_at_tick=0, due_at_tick=20, status="active",
        )
        result = build_economic_context(agent, tick=2)
        assert result is not None
        assert "debt" in result.lower() or "loan" in result.lower()
        assert "active" in result.lower() or "Active" in result

    def test_minsky_classification_shown(self, behavioral_context_setup):
        sim, agent, zone = behavioral_context_setup
        Loan.objects.create(
            simulation=sim, borrower=agent, lender_type="banking",
            principal=100.0, interest_rate=0.05, remaining_balance=100.0,
            issued_at_tick=0, due_at_tick=20, status="active",
        )
        result = build_economic_context(agent, tick=2)
        assert result is not None
        # Should contain one of the Minsky classifications
        assert any(word in result.lower() for word in ["hedge", "speculative", "ponzi"])

    def test_no_debt_block_when_no_loans(self, behavioral_context_setup):
        sim, agent, zone = behavioral_context_setup
        result = build_economic_context(agent, tick=1)
        assert result is not None
        assert "debt" not in result.lower() or "no active" in result.lower()


@pytest.mark.django_db
class TestBankingBlock:
    def test_banking_state_shown(self, behavioral_context_setup):
        sim, agent, zone = behavioral_context_setup
        # BankingState is created by initialize_economy -> initialize_banking
        result = build_economic_context(agent, tick=1)
        assert result is not None
        assert "Banking" in result or "banking" in result
        assert "rate" in result.lower()

    def test_insolvent_banking_flagged(self, behavioral_context_setup):
        sim, agent, zone = behavioral_context_setup
        bs = BankingState.objects.get(simulation=sim)
        bs.is_solvent = False
        bs.confidence_index = 0.2
        bs.save()
        result = build_economic_context(agent, tick=1)
        assert result is not None
        assert "INSOLVENT" in result or "insolvent" in result.lower()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest epocha/apps/economy/tests/test_context_behavioral.py -v`
Expected: FAIL -- "Price expectations" not in result, "debt" not in result, etc.

- [ ] **Step 3: Implement the extended context**

Replace `epocha/apps/economy/context.py` with the extended version. The key additions are three new helper functions and their integration into `build_economic_context`:

```python
"""Build economic context strings for agent decision prompts.

Provides each agent with a summary of their financial situation and
local market conditions so the LLM can make economically informed
decisions. Extended in Spec 2 Part 3 with expectations, debt/Minsky
classification, and banking system state.
"""
from __future__ import annotations

import logging

from django.db.models import Sum

from .models import (
    AgentExpectation,
    AgentInventory,
    BankingState,
    Currency,
    Loan,
    PriceHistory,
    Property,
    ZoneEconomy,
)

logger = logging.getLogger(__name__)


def _build_expectations_block(agent, tick: int) -> str | None:
    """Build the price expectations block for the agent's context.

    Shows the agent's adaptive expectations (Nerlove 1958) for each
    good, including trend direction, percentage deviation from actual
    price, and confidence level.

    Returns None if no expectations exist for this agent.
    """
    expectations = list(
        AgentExpectation.objects.filter(agent=agent)
    )
    if not expectations:
        return None

    lines = ["Price expectations (your assessment):"]
    for exp in expectations:
        # Confidence word
        if exp.confidence > 0.7:
            conf_word = "high"
        elif exp.confidence > 0.4:
            conf_word = "moderate"
        else:
            conf_word = "low"

        trend_upper = exp.trend_direction.upper()
        # Percentage deviation from actual
        pct = ""
        if exp.expected_price > 0:
            actual_price = exp.expected_price  # Best available approximation
            # Try to get actual market price for better % display
            try:
                if agent.zone_id:
                    ze = ZoneEconomy.objects.get(zone_id=agent.zone_id)
                    mp = (ze.market_prices or {}).get(exp.good_code)
                    if mp and mp > 0:
                        actual_price = mp
                        deviation = ((exp.expected_price - mp) / mp) * 100
                        pct = f" ({'+' if deviation > 0 else ''}{deviation:.0f}% expected)"
            except ZoneEconomy.DoesNotExist:
                pass

        lines.append(
            f"- {exp.good_code.capitalize()}: {trend_upper}{pct}, confidence: {conf_word}"
        )

    return "\n".join(lines)


def _build_debt_block(agent, simulation, tick: int) -> str | None:
    """Build the debt situation block for the agent's context.

    Shows active loans, interest due, debt-to-wealth ratio, Minsky
    classification (Minsky 1986), and credit availability.

    Returns None if the agent has no active loans and no borrowing capacity.
    """
    active_loans = list(
        Loan.objects.filter(
            simulation=simulation, borrower=agent, status="active",
        )
    )

    # Even with no loans, show credit availability if agent has property
    has_unpledged_property = Property.objects.filter(
        owner=agent, owner_type="agent",
    ).exclude(
        collateralized_loans__status="active",
    ).exists()

    if not active_loans and not has_unpledged_property:
        return None

    lines = ["Your debt situation:"]

    if active_loans:
        total_balance = sum(l.remaining_balance for l in active_loans)
        interest_due = sum(l.remaining_balance * l.interest_rate for l in active_loans)
        wealth = max(agent.wealth, 1.0)
        debt_ratio = total_balance / wealth

        # Debt-to-wealth word
        if debt_ratio < 0.3:
            ratio_word = "safe"
        elif debt_ratio < 0.6:
            ratio_word = "moderate"
        else:
            ratio_word = "dangerous"

        # Minsky classification
        from .credit import classify_minsky_stage
        minsky = classify_minsky_stage(agent, simulation, tick)
        minsky_descriptions = {
            "hedge": "fully covered, safe",
            "speculative": "can pay interest, will need to refinance",
            "ponzi": "cannot cover interest, critical",
        }
        minsky_desc = minsky_descriptions.get(minsky, minsky)

        lines.append(f"- Active loans: {len(active_loans)} (total balance: {total_balance:.0f})")
        lines.append(f"- Interest due this tick: {interest_due:.1f}")
        lines.append(f"- Debt-to-wealth ratio: {debt_ratio:.0%} ({ratio_word})")
        lines.append(f"- Financial position: {minsky} ({minsky_desc})")
    else:
        lines.append("- No active loans")

    # Credit availability (using highest-value unpledged property)
    if has_unpledged_property:
        best_property = (
            Property.objects.filter(owner=agent, owner_type="agent")
            .exclude(collateralized_loans__status="active")
            .order_by("-value")
            .first()
        )
        if best_property:
            from .credit import evaluate_credit_request
            approved, result = evaluate_credit_request(
                borrower=agent,
                amount=best_property.value * 0.5,  # Request half value as test
                collateral_property=best_property,
                simulation=simulation,
            )
            if approved:
                lines.append(
                    f"- Credit available: up to {best_property.value * 0.5:.0f} "
                    f"at {result:.1%} interest (secured by your {best_property.name})"
                )

    return "\n".join(lines)


def _build_banking_block(simulation) -> str | None:
    """Build the banking system state block.

    Shows solvency, confidence level, and base interest rate.

    Returns None if no BankingState exists for the simulation.
    """
    try:
        bs = BankingState.objects.get(simulation=simulation)
    except BankingState.DoesNotExist:
        return None

    # Confidence word
    if bs.confidence_index > 0.7:
        conf_word = "high"
    elif bs.confidence_index > 0.4:
        conf_word = "moderate"
    else:
        conf_word = "LOW"

    solvency_word = "solvent" if bs.is_solvent else "INSOLVENT"

    return (
        f"Banking system: {solvency_word}, confidence {conf_word}, "
        f"base rate {bs.base_interest_rate:.1%}"
    )


def build_economic_context(agent, tick: int) -> str | None:
    """Build a human-readable economic context string for an agent.

    Returns None if the simulation has no economy data (currencies not
    initialized), allowing the decision pipeline to skip the block.

    Queries:
    - AgentInventory (cash + holdings)
    - Property (agent's owned properties)
    - ZoneEconomy (local market prices)
    - PriceHistory (previous tick for % change computation)
    - Currency (symbol for display)
    - AgentExpectation (price expectations, Spec 2 Part 3)
    - Loan (debt situation, Spec 2 Part 3)
    - BankingState (banking system state, Spec 2 Part 3)

    The returned string is designed to be injected into the LLM prompt
    alongside other context blocks (political, zone, reputation).
    """
    simulation = agent.simulation

    # Get primary currency
    currency = (
        Currency.objects.filter(simulation=simulation, is_primary=True).first()
    )
    if not currency:
        return None

    symbol = currency.symbol

    # Get agent inventory
    try:
        inventory = agent.inventory
    except AgentInventory.DoesNotExist:
        return None

    cash_amount = sum(inventory.cash.values())

    # Holdings summary
    holdings_lines = []
    for good_code, qty in sorted(inventory.holdings.items()):
        if qty > 0:
            holdings_lines.append(f"{good_code} ({qty:.0f} units)")

    holdings_text = ", ".join(holdings_lines) if holdings_lines else "nothing"

    # Properties
    properties = list(
        Property.objects.filter(
            owner=agent, owner_type="agent",
        ).values_list("property_type", flat=True)
    )
    property_count = len(properties)
    property_text = f"{property_count} ({', '.join(properties)})" if properties else "none"

    # Total wealth (already computed on agent model)
    total_wealth = agent.wealth

    # Market prices in the agent's zone
    market_lines = []
    ze = None
    if agent.zone_id:
        try:
            ze = ZoneEconomy.objects.get(zone_id=agent.zone_id)
        except ZoneEconomy.DoesNotExist:
            ze = None

        if ze and ze.market_prices:
            # Get previous tick prices for % change
            prev_prices = {}
            if tick > 0:
                prev_records = PriceHistory.objects.filter(
                    zone_economy=ze, tick=tick - 1,
                )
                prev_prices = {ph.good_code: ph.price for ph in prev_records}

            for good_code, price in sorted(ze.market_prices.items()):
                prev = prev_prices.get(good_code)
                if prev and prev > 0:
                    pct_change = ((price - prev) / prev) * 100
                    if abs(pct_change) < 1.0:
                        trend = "stable"
                    elif pct_change > 0:
                        trend = f"up {pct_change:.0f}%"
                    else:
                        trend = f"down {abs(pct_change):.0f}%"
                else:
                    trend = "no prior data"

                market_lines.append(
                    f"- {good_code.capitalize()}: {price:.1f} {symbol}/unit ({trend})"
                )

    parts = [
        "Your economic situation:",
        f"- Cash: {cash_amount:.0f} {symbol}",
        f"- Inventory: {holdings_text}",
        f"- Properties: {property_text}",
        f"- Total wealth: {total_wealth:.0f} {symbol}",
    ]

    if market_lines:
        zone_label = ze.zone.name if ze and ze.zone else "your zone"
        parts.append(f"\nMarket in {zone_label}:")
        parts.extend(market_lines)

    # === Behavioral blocks (Spec 2 Part 3) ===

    expectations_block = _build_expectations_block(agent, tick)
    if expectations_block:
        parts.append(f"\n{expectations_block}")

    debt_block = _build_debt_block(agent, simulation, tick)
    if debt_block:
        parts.append(f"\n{debt_block}")

    banking_block = _build_banking_block(simulation)
    if banking_block:
        parts.append(f"\n{banking_block}")

    return "\n".join(parts)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest epocha/apps/economy/tests/test_context_behavioral.py -v`
Expected: all pass.

- [ ] **Step 5: Run full economy test suite to check for regressions**

Run: `pytest epocha/apps/economy/tests/ -x -q`
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add epocha/apps/economy/context.py epocha/apps/economy/tests/test_context_behavioral.py
git commit -m "feat(economy): extend context with expectations, debt, and banking

CHANGE: build_economic_context now includes three behavioral blocks:
price expectations (Nerlove adaptive), debt situation with Minsky
classification, and banking system state. Agents see their full
financial picture in the LLM decision prompt."
```

---

### Task 4: Hoard-expectations link

**Files:**
- Modify: `epocha/apps/economy/engine.py`
- Create: `epocha/apps/economy/tests/test_hoard_link.py`

- [ ] **Step 1: Write the failing test**

Create `epocha/apps/economy/tests/test_hoard_link.py`:

```python
"""Tests for hoard-expectations link.

Verifies that agents who chose 'hoard' in the previous tick have
is_hoarding=True in the market pipeline, reducing their supply
contribution.
"""
import json

import pytest

from epocha.apps.agents.models import Agent, DecisionLog
from epocha.apps.economy.engine import _get_hoarding_agent_ids
from epocha.apps.simulation.models import Simulation


@pytest.mark.django_db
class TestHoardingAgentIds:
    def test_detects_hoard_from_decision_log(self):
        sim = Simulation.objects.create(name="hoard_test", config={})
        agent = Agent.objects.create(
            simulation=sim, name="Hoarder", role="merchant",
            personality={}, wealth=100.0, mood=0.5, health=1.0,
        )
        DecisionLog.objects.create(
            simulation=sim, agent=agent, tick=5,
            input_context="test", llm_model="test",
            output_decision=json.dumps({"action": "hoard", "reason": "prices rising"}),
        )
        result = _get_hoarding_agent_ids(sim, tick=6)
        assert agent.id in result

    def test_ignores_non_hoard_actions(self):
        sim = Simulation.objects.create(name="hoard_test2", config={})
        agent = Agent.objects.create(
            simulation=sim, name="Worker", role="farmer",
            personality={}, wealth=100.0, mood=0.5, health=1.0,
        )
        DecisionLog.objects.create(
            simulation=sim, agent=agent, tick=5,
            input_context="test", llm_model="test",
            output_decision=json.dumps({"action": "work", "reason": "need money"}),
        )
        result = _get_hoarding_agent_ids(sim, tick=6)
        assert agent.id not in result

    def test_only_reads_previous_tick(self):
        sim = Simulation.objects.create(name="hoard_test3", config={})
        agent = Agent.objects.create(
            simulation=sim, name="OldHoarder", role="merchant",
            personality={}, wealth=100.0, mood=0.5, health=1.0,
        )
        # Hoard at tick 3 (not tick 5)
        DecisionLog.objects.create(
            simulation=sim, agent=agent, tick=3,
            input_context="test", llm_model="test",
            output_decision=json.dumps({"action": "hoard", "reason": "old"}),
        )
        result = _get_hoarding_agent_ids(sim, tick=6)
        assert agent.id not in result

    def test_returns_empty_set_at_tick_zero(self):
        sim = Simulation.objects.create(name="hoard_test4", config={})
        result = _get_hoarding_agent_ids(sim, tick=0)
        assert result == set()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest epocha/apps/economy/tests/test_hoard_link.py -v`
Expected: FAIL -- `_get_hoarding_agent_ids` not defined.

- [ ] **Step 3: Implement _get_hoarding_agent_ids and wire into engine**

In `epocha/apps/economy/engine.py`, add the helper function after the imports:

```python
def _get_hoarding_agent_ids(simulation, tick: int) -> set[int]:
    """Return IDs of agents who chose 'hoard' in the previous tick.

    Reads DecisionLog entries from tick-1 and checks if the JSON
    output_decision contains the "hoard" action. DecisionLog.output_decision
    is a TextField containing json.dumps() output, so __contains with
    '"hoard"' performs a PostgreSQL LIKE substring match.

    Returns an empty set at tick 0 (no previous tick to read).
    """
    if tick <= 0:
        return set()

    from epocha.apps.agents.models import DecisionLog

    hoarding_decisions = DecisionLog.objects.filter(
        simulation=simulation,
        tick=tick - 1,
        output_decision__contains='"hoard"',
    ).values_list("agent_id", flat=True)
    return set(hoarding_decisions)
```

Then in `process_economy_tick_new`, right after `update_agent_expectations(simulation, tick)` (around line 120), add:

```python
    # Get agents who hoarded at the previous tick.
    # Their goods will not be offered to the market (is_hoarding=True).
    hoarding_ids = _get_hoarding_agent_ids(simulation, tick)
```

And in the `agent_inventories` construction (around line 208), replace the hardcoded `False`:

```python
                    "is_hoarding": agent.id in hoarding_ids,
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest epocha/apps/economy/tests/test_hoard_link.py -v`
Expected: all pass.

- [ ] **Step 5: Run full economy test suite**

Run: `pytest epocha/apps/economy/tests/ -x -q`
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add epocha/apps/economy/engine.py epocha/apps/economy/tests/test_hoard_link.py
git commit -m "feat(economy): link hoard action to market supply reduction

CHANGE: Agents who chose 'hoard' at tick N-1 have is_hoarding=True at
tick N, preventing their goods from entering the tatonnement market.
This creates the self-fulfilling prophecy loop: expectations rising ->
hoard -> supply drops -> prices rise -> expectations confirmed."
```

---

### Task 5: Banking deposits recalculation and concern broadcast

**Files:**
- Modify: `epocha/apps/economy/banking.py`
- Modify: `epocha/apps/economy/engine.py`
- Create: `epocha/apps/economy/tests/test_banking_behavioral.py`

- [ ] **Step 1: Write the failing tests**

Create `epocha/apps/economy/tests/test_banking_behavioral.py`:

```python
"""Tests for dynamic deposits and banking concern broadcast.

Spec 2 Part 3: total_deposits is recalculated each tick as the sum
of all agent cash. Banking concern memories are created when
confidence drops below 0.5 (Diamond & Dybvig 1983).
"""
import pytest

from epocha.apps.agents.models import Agent, Memory
from epocha.apps.economy.banking import (
    broadcast_banking_concern,
    recalculate_deposits,
)
from epocha.apps.economy.initialization import initialize_economy
from epocha.apps.economy.models import AgentInventory, BankingState
from epocha.apps.simulation.models import Simulation
from epocha.apps.world.models import World, Zone


@pytest.fixture
def banking_sim(db):
    """Create a simulation with economy and multiple agents."""
    sim = Simulation.objects.create(name="bank_test", config={})
    world = World.objects.create(
        simulation=sim, name="bank_world", stability_index=0.8,
    )
    zone = Zone.objects.create(world=world, name="London", zone_type="urban")
    agents = []
    for i, name in enumerate(["Alice", "Bob", "Charlie", "Diana"]):
        agents.append(Agent.objects.create(
            simulation=sim, name=name, role="merchant",
            personality={"neuroticism": 0.5},
            zone=zone, wealth=100.0, mood=0.5, health=1.0,
        ))
    initialize_economy(sim, "pre_industrial")
    sim.refresh_from_db()
    return sim, agents, zone


@pytest.mark.django_db
class TestRecalculateDeposits:
    def test_deposits_equal_total_agent_cash(self, banking_sim):
        sim, agents, zone = banking_sim
        # Sum all agent cash
        total_cash = 0.0
        for agent in agents:
            agent.refresh_from_db()
            try:
                inv = agent.inventory
                total_cash += sum(inv.cash.values())
            except AgentInventory.DoesNotExist:
                pass

        recalculate_deposits(sim)
        bs = BankingState.objects.get(simulation=sim)
        assert abs(bs.total_deposits - total_cash) < 0.01

    def test_deposits_update_after_cash_change(self, banking_sim):
        sim, agents, zone = banking_sim
        # Manually change one agent's cash
        inv = agents[0].inventory
        inv.cash["LVR"] = inv.cash.get("LVR", 0.0) + 500.0
        inv.save(update_fields=["cash"])

        recalculate_deposits(sim)
        bs = BankingState.objects.get(simulation=sim)

        # Recalculate expected
        total_cash = 0.0
        for agent in agents:
            agent.refresh_from_db()
            try:
                agent_inv = agent.inventory
                total_cash += sum(agent_inv.cash.values())
            except AgentInventory.DoesNotExist:
                pass

        assert abs(bs.total_deposits - total_cash) < 0.01


@pytest.mark.django_db
class TestBroadcastBankingConcern:
    def test_broadcast_when_confidence_low(self, banking_sim):
        sim, agents, zone = banking_sim
        bs = BankingState.objects.get(simulation=sim)
        bs.confidence_index = 0.3
        bs.save()

        broadcast_banking_concern(sim, tick=5)
        # At least some agents should have received a banking concern memory
        concern_count = Memory.objects.filter(
            agent__simulation=sim,
            content__contains="banking system",
        ).count()
        assert concern_count > 0
        # Should be roughly 50% of agents (4 agents -> 2)
        assert concern_count <= len(agents)

    def test_no_broadcast_when_confidence_high(self, banking_sim):
        sim, agents, zone = banking_sim
        bs = BankingState.objects.get(simulation=sim)
        bs.confidence_index = 0.8
        bs.save()

        broadcast_banking_concern(sim, tick=5)
        concern_count = Memory.objects.filter(
            agent__simulation=sim,
            content__contains="banking system",
        ).count()
        assert concern_count == 0

    def test_broadcast_regardless_of_solvency(self, banking_sim):
        """Diamond & Dybvig (1983): fear triggers runs, not actual insolvency."""
        sim, agents, zone = banking_sim
        bs = BankingState.objects.get(simulation=sim)
        bs.confidence_index = 0.3
        bs.is_solvent = True  # Still solvent, but low confidence
        bs.save()

        broadcast_banking_concern(sim, tick=5)
        concern_count = Memory.objects.filter(
            agent__simulation=sim,
            content__contains="banking system",
        ).count()
        assert concern_count > 0

    def test_dedup_prevents_spam(self, banking_sim):
        sim, agents, zone = banking_sim
        bs = BankingState.objects.get(simulation=sim)
        bs.confidence_index = 0.3
        bs.save()

        broadcast_banking_concern(sim, tick=5)
        count_after_first = Memory.objects.filter(
            agent__simulation=sim,
            content__contains="banking system",
        ).count()

        broadcast_banking_concern(sim, tick=6)
        count_after_second = Memory.objects.filter(
            agent__simulation=sim,
            content__contains="banking system",
        ).count()
        # Dedup within 3 ticks: no new memories created
        assert count_after_second == count_after_first
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest epocha/apps/economy/tests/test_banking_behavioral.py -v`
Expected: FAIL -- `recalculate_deposits` and `broadcast_banking_concern` not importable.

- [ ] **Step 3: Implement recalculate_deposits and broadcast_banking_concern**

Add to `epocha/apps/economy/banking.py`:

```python
import random

from epocha.apps.agents.models import Agent, Memory

from .models import AgentInventory, BankingState


def recalculate_deposits(simulation) -> None:
    """Recalculate total_deposits as the sum of all living agents' cash.

    AgentInventory.cash is a JSONField ({currency_code: amount}), so
    aggregation requires Python iteration. This is consistent with the
    pattern used in context.py for individual agent cash summation.

    This approximation treats all agent cash as deposited. Without
    per-agent deposit tracking (Spec 3), this is the simplest model
    that gives the reserve ratio real economic meaning.
    """
    try:
        bs = BankingState.objects.get(simulation=simulation)
    except BankingState.DoesNotExist:
        return

    inventories = AgentInventory.objects.filter(
        agent__simulation=simulation,
        agent__is_alive=True,
    )
    total_cash = sum(
        sum(inv.cash.values()) for inv in inventories
    )
    bs.total_deposits = total_cash
    bs.save(update_fields=["total_deposits"])


# Banking concern broadcast: memory dedup window in ticks.
# Consistent with _MEMORY_DEDUP_TICKS = 3 in simulation/engine.py.
_CONCERN_DEDUP_TICKS = 3

# Fraction of living agents who receive the initial broadcast.
# Tunable design parameter modeling information asymmetry.
_CONCERN_BROADCAST_RATIO = 0.5

# Confidence threshold below which concern is broadcast.
# Tunable design parameter. Diamond & Dybvig (1983): the concern
# must precede the crisis to enable the self-fulfilling prophecy.
_CONCERN_CONFIDENCE_THRESHOLD = 0.5


def broadcast_banking_concern(simulation, tick: int) -> int:
    """Create banking concern memories when confidence is low.

    Trigger condition: BankingState.confidence_index < 0.5
    REGARDLESS of solvency status. This is essential for Diamond &
    Dybvig (1983): the bank run is triggered by the FEAR of insolvency,
    not by actual insolvency.

    Generates memories for a random sample of 50% of living agents.
    Dedup check prevents duplicate memories within 3 ticks.

    Args:
        simulation: The simulation instance.
        tick: Current simulation tick.

    Returns:
        Number of memories created.
    """
    try:
        bs = BankingState.objects.get(simulation=simulation)
    except BankingState.DoesNotExist:
        return 0

    if bs.confidence_index >= _CONCERN_CONFIDENCE_THRESHOLD:
        return 0

    agents = list(
        Agent.objects.filter(simulation=simulation, is_alive=True)
    )
    if not agents:
        return 0

    # Sample agents for broadcast
    sample_size = max(1, int(len(agents) * _CONCERN_BROADCAST_RATIO))
    sampled = random.sample(agents, min(sample_size, len(agents)))

    content = (
        "The banking system is under stress. Some depositors "
        "are worried about the safety of their savings."
    )

    created_count = 0
    dedup_min_tick = max(0, tick - _CONCERN_DEDUP_TICKS)

    for agent in sampled:
        # Dedup: skip if agent already has a banking concern memory
        # from the last _CONCERN_DEDUP_TICKS ticks.
        has_recent = Memory.objects.filter(
            agent=agent,
            content__contains="banking system",
            tick_created__gte=dedup_min_tick,
            is_active=True,
        ).exists()
        if has_recent:
            continue

        Memory.objects.create(
            agent=agent,
            content=content,
            emotional_weight=0.6,
            source_type="public",
            tick_created=tick,
        )
        created_count += 1

    if created_count > 0:
        logger.info(
            "Banking concern broadcast: simulation=%d tick=%d, "
            "confidence=%.2f, memories_created=%d/%d",
            simulation.id, tick, bs.confidence_index,
            created_count, len(sampled),
        )

    return created_count
```

- [ ] **Step 4: Wire into engine.py**

In `epocha/apps/economy/engine.py`, add imports:

```python
from .banking import adjust_interest_rate, broadcast_banking_concern, check_solvency, recalculate_deposits
```

In `process_economy_tick_new`, after `check_solvency(simulation)` (around line 299), add:

```python
            broadcast_banking_concern(simulation, tick)
```

And at the very end of `process_economy_tick_new`, before the final logger.info, add:

```python
    # === STEP 10: DEPOSIT RECALCULATION ===
    # Recalculate total_deposits from all agent cash after all economic
    # transactions are complete. This gives the reserve ratio and
    # solvency checks real economic meaning.
    recalculate_deposits(simulation)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest epocha/apps/economy/tests/test_banking_behavioral.py -v`
Expected: all pass.

- [ ] **Step 6: Run full economy test suite**

Run: `pytest epocha/apps/economy/tests/ -x -q`
Expected: all pass.

- [ ] **Step 7: Commit**

```bash
git add epocha/apps/economy/banking.py epocha/apps/economy/engine.py epocha/apps/economy/tests/test_banking_behavioral.py
git commit -m "feat(economy): add deposit recalculation and banking concern broadcast

CHANGE: total_deposits is recalculated each tick as the sum of all agent
cash (step 10 in pipeline). When banking confidence drops below 0.5,
concern memories are broadcast to 50% of agents via information flow.
Diamond & Dybvig (1983): concern triggers on fear, not actual insolvency."
```

---

### Task 6: Credit fixes -- dead agents and double-pledge

**Files:**
- Modify: `epocha/apps/economy/credit.py`
- Modify: `epocha/apps/economy/tests/test_credit.py` (or new test file)

- [ ] **Step 1: Write the failing tests**

Add to `epocha/apps/economy/tests/test_credit.py` (or create a new section):

```python
@pytest.mark.django_db
class TestDeadAgentLoanDefault:
    def test_dead_agent_loans_default(self):
        sim = Simulation.objects.create(name="dead_test", config={})
        agent = Agent.objects.create(
            simulation=sim, name="Ghost", role="farmer",
            personality={}, wealth=100.0, mood=0.5, health=0.0,
            is_alive=False,
        )
        AgentInventory.objects.create(agent=agent, holdings={}, cash={"LVR": 50.0})
        Loan.objects.create(
            simulation=sim, borrower=agent, lender_type="banking",
            principal=100.0, interest_rate=0.05, remaining_balance=80.0,
            issued_at_tick=0, due_at_tick=20, status="active",
        )
        from epocha.apps.economy.credit import default_dead_agent_loans
        count = default_dead_agent_loans(sim)
        assert count == 1
        loan = Loan.objects.get(simulation=sim)
        assert loan.status == "defaulted"

    def test_alive_agent_loans_unaffected(self):
        sim = Simulation.objects.create(name="alive_test", config={})
        agent = Agent.objects.create(
            simulation=sim, name="Alive", role="farmer",
            personality={}, wealth=100.0, mood=0.5, health=1.0,
            is_alive=True,
        )
        AgentInventory.objects.create(agent=agent, holdings={}, cash={"LVR": 50.0})
        Loan.objects.create(
            simulation=sim, borrower=agent, lender_type="banking",
            principal=100.0, interest_rate=0.05, remaining_balance=80.0,
            issued_at_tick=0, due_at_tick=20, status="active",
        )
        from epocha.apps.economy.credit import default_dead_agent_loans
        count = default_dead_agent_loans(sim)
        assert count == 0
        loan = Loan.objects.get(simulation=sim)
        assert loan.status == "active"


@pytest.mark.django_db
class TestDoublePledgeProtection:
    def test_find_unpledged_property(self):
        sim = Simulation.objects.create(name="pledge_test", config={})
        world = World.objects.create(simulation=sim, name="w", stability_index=0.8)
        zone = Zone.objects.create(world=world, name="z", zone_type="urban")
        agent = Agent.objects.create(
            simulation=sim, name="Owner", role="merchant",
            personality={}, zone=zone, wealth=500.0, mood=0.5, health=1.0,
        )
        AgentInventory.objects.create(agent=agent, holdings={}, cash={"LVR": 200.0})
        prop1 = Property.objects.create(
            simulation=sim, owner=agent, owner_type="agent", zone=zone,
            property_type="farmland", name="Farm A", value=200.0,
        )
        prop2 = Property.objects.create(
            simulation=sim, owner=agent, owner_type="agent", zone=zone,
            property_type="farmland", name="Farm B", value=300.0,
        )
        # Pledge prop2 as collateral
        Loan.objects.create(
            simulation=sim, borrower=agent, lender_type="banking",
            principal=100.0, interest_rate=0.05, remaining_balance=100.0,
            collateral=prop2, issued_at_tick=0, due_at_tick=20, status="active",
        )
        from epocha.apps.economy.credit import find_best_unpledged_property
        best = find_best_unpledged_property(agent)
        assert best is not None
        assert best.id == prop1.id  # prop2 is pledged, prop1 is free

    def test_no_unpledged_property(self):
        sim = Simulation.objects.create(name="pledge_test2", config={})
        world = World.objects.create(simulation=sim, name="w", stability_index=0.8)
        zone = Zone.objects.create(world=world, name="z", zone_type="urban")
        agent = Agent.objects.create(
            simulation=sim, name="Owner", role="merchant",
            personality={}, zone=zone, wealth=500.0, mood=0.5, health=1.0,
        )
        AgentInventory.objects.create(agent=agent, holdings={}, cash={"LVR": 200.0})
        prop = Property.objects.create(
            simulation=sim, owner=agent, owner_type="agent", zone=zone,
            property_type="farmland", name="Farm", value=200.0,
        )
        Loan.objects.create(
            simulation=sim, borrower=agent, lender_type="banking",
            principal=100.0, interest_rate=0.05, remaining_balance=100.0,
            collateral=prop, issued_at_tick=0, due_at_tick=20, status="active",
        )
        from epocha.apps.economy.credit import find_best_unpledged_property
        best = find_best_unpledged_property(agent)
        assert best is None
```

Note: Import `Property`, `Loan`, `AgentInventory` from economy models at the top of the test file. Import `World`, `Zone` from world models.

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest epocha/apps/economy/tests/test_credit.py::TestDeadAgentLoanDefault -v`
Run: `pytest epocha/apps/economy/tests/test_credit.py::TestDoublePledgeProtection -v`
Expected: FAIL -- functions not defined.

- [ ] **Step 3: Implement the functions**

Add to `epocha/apps/economy/credit.py`:

```python
def default_dead_agent_loans(simulation) -> int:
    """Default all active loans held by dead borrowers.

    Agents who die (is_alive=False) cannot earn income or repay debt.
    Their loans are defaulted immediately. Collateral seizure and
    cascade propagation follow the existing default pipeline.

    Called at the start of the credit market step, before service_loans.

    Args:
        simulation: The simulation instance.

    Returns:
        Number of loans defaulted.
    """
    dead_loans = Loan.objects.filter(
        simulation=simulation,
        status="active",
        borrower__is_alive=False,
    )
    count = dead_loans.count()
    if count > 0:
        dead_loans.update(status="defaulted")
        logger.info(
            "Defaulted %d loans from dead agents in simulation %d",
            count, simulation.id,
        )
    return count


def find_best_unpledged_property(agent: Agent) -> "Property | None":
    """Find the agent's highest-value property not already used as collateral.

    Excludes properties that are collateral for active loans to prevent
    double-pledging. Uses the related_name 'collateralized_loans' defined
    on Loan.collateral.

    Args:
        agent: The agent whose properties to search.

    Returns:
        The highest-value unpledged Property, or None if none available.
    """
    return (
        Property.objects.filter(owner=agent, owner_type="agent")
        .exclude(collateralized_loans__status="active")
        .order_by("-value")
        .first()
    )
```

- [ ] **Step 4: Wire default_dead_agent_loans into engine.py**

In `epocha/apps/economy/engine.py`, update the credit import:

```python
from .credit import (
    default_dead_agent_loans,
    process_default_cascade,
    process_defaults,
    process_maturity,
    service_loans,
)
```

In the credit processing block (inside `if not credit_processed:`), add before `service_loans`:

```python
            default_dead_agent_loans(simulation)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest epocha/apps/economy/tests/test_credit.py::TestDeadAgentLoanDefault epocha/apps/economy/tests/test_credit.py::TestDoublePledgeProtection -v`
Expected: all pass.

- [ ] **Step 6: Run full test suite**

Run: `pytest epocha/apps/economy/tests/ -x -q`
Expected: all pass.

- [ ] **Step 7: Run full project test suite**

Run: `pytest --tb=short -q`
Expected: all tests pass.

- [ ] **Step 8: Commit**

```bash
git add epocha/apps/economy/credit.py epocha/apps/economy/engine.py epocha/apps/economy/tests/test_credit.py
git commit -m "feat(economy): handle dead agent loans and prevent double-pledging

CHANGE: Loans held by dead agents (is_alive=False) are auto-defaulted at
the start of the credit market step. find_best_unpledged_property excludes
properties already used as collateral for active loans, preventing the
same asset from securing multiple debts."
```

# Economy Behavioral Integration Plan -- Part 3b: Property Market + Actions

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the property market module (Gordon valuation, listing/matching, expropriation), three new LLM-driven actions (borrow, sell_property, buy_property), expropriation hook on government transitions, and dashboard verb updates. After this plan, agents can borrow, trade property, and government transitions redistribute wealth.

**Architecture:** One new module (`property_market.py`), modifications to decision pipeline (`decision.py`, `simulation/engine.py`), government hook (`government.py`), and dashboard formatting. The property market runs as step 3 in the economy tick pipeline. Agent decisions use tick+1 settlement.

**Tech Stack:** Django ORM, PostgreSQL.

**Spec:** `docs/superpowers/specs/2026-04-15-economy-behavioral-integration-design.md` (Sections 2, 3, 6)

**Depends on:** Plan 3a (foundations) -- completed.

**IMPORTANT notes for implementers:**
- Simulation model requires `seed` (NOT NULL) and `owner` (FK NOT NULL to User) in test fixtures
- `World` model has NO `name` field -- only `simulation` (FK) and `stability_index`
- `PropertyListing.property` is OneToOneField: delete old listings before re-listing
- Loan.collateral related_name is `collateralized_loans`, NOT `securing_loans`
- Tests run in Docker: `docker compose -f docker-compose.local.yml exec web pytest ...`
- Use existing test fixture patterns from `epocha/apps/economy/tests/test_credit.py`

---

## File Structure (Part 3b scope)

| File | Responsibility | New/Modify |
|------|---------------|------------|
| `epocha/apps/economy/property_market.py` | Gordon valuation, listings, matching, expropriation | New |
| `epocha/apps/agents/decision.py` | Add borrow/sell_property/buy_property to system prompt | Modify |
| `epocha/apps/simulation/engine.py` | Action handlers + mood/weight for new actions | Modify |
| `epocha/apps/economy/engine.py` | Wire property market step into tick pipeline | Modify |
| `epocha/apps/world/government.py` | Expropriation hook after transitions and coups | Modify |
| `epocha/apps/dashboard/formatters.py` | New verb entries | Modify |
| `epocha/apps/economy/credit.py` | Update transaction_type from "trade" to specific types | Modify |
| `epocha/apps/economy/tests/test_property_market.py` | Property market tests | New |
| `epocha/apps/economy/tests/test_actions_behavioral.py` | Action handler tests | New |

---

## Tasks summary

7. **Property market module** -- Gordon valuation, process_property_listings, process_expropriation
8. **New actions in decision pipeline** -- system prompt + action handlers + dashboard verbs
9. **Pipeline and government integration** -- wire property market into engine, expropriation hook
10. **Update credit.py transaction types** -- replace "trade" with specific types in loan operations

---

### Task 7: Property market module

**Files:**
- Create: `epocha/apps/economy/property_market.py`
- Create: `epocha/apps/economy/tests/test_property_market.py`

- [ ] **Step 1: Write the test file**

Create `epocha/apps/economy/tests/test_property_market.py`:

```python
"""Tests for property market: Gordon valuation, listing/matching, expropriation.

Scientific references:
- Gordon, M. (1959). Dividends, Earnings, and Stock Prices.
- Acemoglu, D. & Robinson, J. (2006). Economic Origins of Dictatorship and Democracy.
"""
import json

import pytest
from django.contrib.gis.geos import Point, Polygon

from epocha.apps.agents.models import Agent, DecisionLog, Memory
from epocha.apps.economy.initialization import initialize_economy
from epocha.apps.economy.models import (
    AgentInventory,
    BankingState,
    Currency,
    EconomicLedger,
    Loan,
    Property,
    PropertyListing,
    ZoneEconomy,
)
from epocha.apps.economy.property_market import (
    compute_gordon_valuation,
    process_expropriation,
    process_property_listings,
)
from epocha.apps.simulation.models import Simulation
from epocha.apps.users.models import User
from epocha.apps.world.models import Government, World, Zone


@pytest.fixture
def property_market_setup(db):
    """Full economy setup for property market tests."""
    user = User.objects.create_user(
        email="propmarket@epocha.dev", username="propuser", password="pass1234",
    )
    sim = Simulation.objects.create(
        name="PropertyTest", seed=42, owner=user,
        config={
            "credit_config": {
                "loan_to_value": 0.8,
                "max_rollover": 3,
                "default_loan_duration_ticks": 10,
            },
            "banking_config": {
                "initial_deposits": 10000.0,
                "base_interest_rate": 0.05,
                "reserve_ratio": 0.10,
            },
            "expropriation_policies": {
                "democracy": "none",
                "totalitarian": "nationalize_all",
                "junta": "elite_seizure",
            },
        },
    )
    world = World.objects.create(simulation=sim, stability_index=0.8)
    zone = Zone.objects.create(
        world=world, name="Paris", zone_type="urban",
        boundary=Polygon.from_bbox((0, 0, 100, 100)),
        center=Point(50, 50),
    )
    initialize_economy(sim, "pre_industrial")
    sim.refresh_from_db()

    currency = Currency.objects.get(simulation=sim, is_primary=True)

    seller = Agent.objects.create(
        simulation=sim, name="Seller", role="merchant",
        personality={"neuroticism": 0.5, "openness": 0.5},
        zone=zone, wealth=500.0, mood=0.6, health=1.0,
        social_class="elite", location=Point(50, 50),
    )
    AgentInventory.objects.create(
        agent=seller, holdings={"subsistence": 5.0},
        cash={currency.code: 300.0},
    )

    buyer = Agent.objects.create(
        simulation=sim, name="Buyer", role="merchant",
        personality={"neuroticism": 0.3, "openness": 0.7},
        zone=zone, wealth=400.0, mood=0.6, health=1.0,
        social_class="middle", location=Point(50, 50),
    )
    AgentInventory.objects.create(
        agent=buyer, holdings={"subsistence": 5.0},
        cash={currency.code: 500.0},
    )

    prop = Property.objects.create(
        simulation=sim, owner=seller, owner_type="agent", zone=zone,
        property_type="farmland", name="Grand Farm",
        value=200.0, production_bonus={"subsistence": 0.2},
    )

    return {
        "sim": sim, "world": world, "zone": zone, "currency": currency,
        "seller": seller, "buyer": buyer, "prop": prop,
    }


@pytest.mark.django_db
class TestGordonValuation:
    def test_basic_valuation(self, property_market_setup):
        s = property_market_setup
        bs = BankingState.objects.get(simulation=s["sim"])
        bs.base_interest_rate = 0.10
        bs.save()
        # With R=20 (book value fallback), r=0.10, g=0 -> V = 20/0.10 = 200
        # But capped at property.value * 10 = 2000
        val = compute_gordon_valuation(s["prop"], s["sim"])
        assert val > 0
        assert val <= s["prop"].value * 10

    def test_floor_at_10_percent_book_value(self, property_market_setup):
        s = property_market_setup
        bs = BankingState.objects.get(simulation=s["sim"])
        bs.base_interest_rate = 0.99  # Very high rate -> very low valuation
        bs.save()
        val = compute_gordon_valuation(s["prop"], s["sim"])
        assert val >= s["prop"].value * 0.1

    def test_cap_at_10x_book_value(self, property_market_setup):
        s = property_market_setup
        bs = BankingState.objects.get(simulation=s["sim"])
        bs.base_interest_rate = 0.001  # Very low rate -> very high valuation
        bs.save()
        val = compute_gordon_valuation(s["prop"], s["sim"])
        assert val <= s["prop"].value * 10


@pytest.mark.django_db
class TestProcessPropertyListings:
    def test_match_buyer_seller(self, property_market_setup):
        s = property_market_setup
        # Create a listing
        val = compute_gordon_valuation(s["prop"], s["sim"])
        PropertyListing.objects.create(
            property=s["prop"], asking_price=val,
            fundamental_value=val, listed_at_tick=5,
        )
        # Create a buy intent in DecisionLog at tick 5
        DecisionLog.objects.create(
            simulation=s["sim"], agent=s["buyer"], tick=5,
            input_context="test", llm_model="test",
            output_decision=json.dumps({"action": "buy_property", "target": "farmland"}),
        )
        result = process_property_listings(s["sim"], tick=6)
        assert result["matched"] >= 1
        # Property should now belong to buyer
        s["prop"].refresh_from_db()
        assert s["prop"].owner_id == s["buyer"].id

    def test_no_match_when_no_listings(self, property_market_setup):
        s = property_market_setup
        DecisionLog.objects.create(
            simulation=s["sim"], agent=s["buyer"], tick=5,
            input_context="test", llm_model="test",
            output_decision=json.dumps({"action": "buy_property", "target": "farmland"}),
        )
        result = process_property_listings(s["sim"], tick=6)
        assert result["matched"] == 0

    def test_no_self_purchase(self, property_market_setup):
        s = property_market_setup
        val = compute_gordon_valuation(s["prop"], s["sim"])
        PropertyListing.objects.create(
            property=s["prop"], asking_price=val,
            fundamental_value=val, listed_at_tick=5,
        )
        # Seller tries to buy their own listing
        DecisionLog.objects.create(
            simulation=s["sim"], agent=s["seller"], tick=5,
            input_context="test", llm_model="test",
            output_decision=json.dumps({"action": "buy_property", "target": "farmland"}),
        )
        result = process_property_listings(s["sim"], tick=6)
        assert result["matched"] == 0
        s["prop"].refresh_from_db()
        assert s["prop"].owner_id == s["seller"].id  # Still seller's

    def test_insufficient_cash_fails(self, property_market_setup):
        s = property_market_setup
        # Set asking price higher than buyer's cash
        PropertyListing.objects.create(
            property=s["prop"], asking_price=99999.0,
            fundamental_value=200.0, listed_at_tick=5,
        )
        DecisionLog.objects.create(
            simulation=s["sim"], agent=s["buyer"], tick=5,
            input_context="test", llm_model="test",
            output_decision=json.dumps({"action": "buy_property", "target": "farmland"}),
        )
        result = process_property_listings(s["sim"], tick=6)
        assert result["matched"] == 0
        assert result["failed"] >= 1

    def test_expired_listings_withdrawn(self, property_market_setup):
        s = property_market_setup
        listing = PropertyListing.objects.create(
            property=s["prop"], asking_price=200.0,
            fundamental_value=200.0, listed_at_tick=1,
        )
        # Process at tick 12 (listing is 11 ticks old, > 10 tick expiry)
        result = process_property_listings(s["sim"], tick=12)
        assert result["expired"] >= 1
        listing.refresh_from_db()
        assert listing.status == "withdrawn"


@pytest.mark.django_db
class TestProcessExpropriation:
    def test_nationalize_all(self, property_market_setup):
        s = property_market_setup
        count = process_expropriation(s["sim"], "democracy", "totalitarian", tick=10)
        assert count >= 1
        s["prop"].refresh_from_db()
        assert s["prop"].owner_type == "government"

    def test_no_expropriation_for_democracy(self, property_market_setup):
        s = property_market_setup
        count = process_expropriation(s["sim"], "monarchy", "democracy", tick=10)
        assert count == 0
        s["prop"].refresh_from_db()
        assert s["prop"].owner_type == "agent"

    def test_elite_seizure(self, property_market_setup):
        s = property_market_setup
        count = process_expropriation(s["sim"], "democracy", "junta", tick=10)
        # Seller is elite, should be seized
        assert count >= 1
        s["prop"].refresh_from_db()
        assert s["prop"].owner_type == "government"

    def test_loans_on_expropriated_property_default(self, property_market_setup):
        s = property_market_setup
        loan = Loan.objects.create(
            simulation=s["sim"], borrower=s["seller"], lender_type="banking",
            principal=100.0, interest_rate=0.05, remaining_balance=100.0,
            collateral=s["prop"], issued_at_tick=0, due_at_tick=20, status="active",
        )
        process_expropriation(s["sim"], "democracy", "totalitarian", tick=10)
        loan.refresh_from_db()
        assert loan.status == "defaulted"

    def test_listing_withdrawn_on_expropriation(self, property_market_setup):
        s = property_market_setup
        listing = PropertyListing.objects.create(
            property=s["prop"], asking_price=200.0,
            fundamental_value=200.0, listed_at_tick=5,
        )
        process_expropriation(s["sim"], "democracy", "totalitarian", tick=10)
        listing.refresh_from_db()
        assert listing.status == "withdrawn"

    def test_affected_agents_get_negative_memory(self, property_market_setup):
        s = property_market_setup
        process_expropriation(s["sim"], "democracy", "totalitarian", tick=10)
        memories = Memory.objects.filter(
            agent=s["seller"],
            content__contains="expropriat",
        )
        assert memories.exists()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `docker compose -f docker-compose.local.yml exec web pytest epocha/apps/economy/tests/test_property_market.py -v --tb=short 2>&1 | tail -20`
Expected: FAIL -- `property_market` module does not exist.

- [ ] **Step 3: Implement property_market.py**

Create `epocha/apps/economy/property_market.py`:

```python
"""Property market: Gordon valuation, listing/matching, expropriation.

Implements three functions for the behavioral economy (Spec 2 Part 3):
1. compute_gordon_valuation -- fundamental value via Gordon (1959)
2. process_property_listings -- match buyers to sellers at tick+1
3. process_expropriation -- property redistribution on regime change

Scientific references:
- Gordon, M. (1959). Dividends, Earnings, and Stock Prices.
  Review of Economics and Statistics 41(2), 99-105.
- Acemoglu, D. & Robinson, J. (2006). Economic Origins of
  Dictatorship and Democracy. Cambridge University Press.
- Shiller, R.J. (2000). Irrational Exuberance. Princeton Univ. Press.
"""

from __future__ import annotations

import json
import logging

from django.db.models import Sum

from epocha.apps.agents.models import Agent, DecisionLog, Memory

from .models import (
    AgentInventory,
    BankingState,
    Currency,
    EconomicLedger,
    Loan,
    Property,
    PropertyListing,
    ZoneEconomy,
)

logger = logging.getLogger(__name__)

# Listing auto-expiry in ticks. Tunable design parameter representing
# the patience threshold of a seller in an illiquid market.
_LISTING_EXPIRY_TICKS = 10

# Gordon valuation bounds. Tunable design parameters.
# Floor prevents valuations from going to zero; cap prevents
# numerical instability from very low interest rates.
# The 10x cap also limits bubble magnitude (see Known Limitations).
_VALUATION_FLOOR_RATIO = 0.1  # 10% of book value
_VALUATION_CAP_RATIO = 10.0   # 10x book value


def compute_gordon_valuation(prop: Property, simulation) -> float:
    """Compute fundamental value using the Gordon Growth Model (1959).

    V = R / max(r - g, 0.01)

    where:
    - R = rental income from this property's zone in the last tick
      (from EconomicLedger rent transactions). Falls back to
      property.value as book value when no rent data exists.
    - r = current base interest rate (from BankingState)
    - g = trailing 5-tick average growth rate of total rent in the zone

    The 0.01 floor on (r - g) prevents division by zero when g >= r.
    When g approaches r, the valuation becomes very high, indicating
    the market is in speculative territory (Shiller 2000).

    Returns the fundamental value, floored at property.value * 0.1
    and capped at property.value * 10.
    """
    book_value = prop.value
    if book_value <= 0:
        return 0.0

    # Get current base interest rate
    try:
        bs = BankingState.objects.get(simulation=simulation)
        r = bs.base_interest_rate
    except BankingState.DoesNotExist:
        r = 0.05  # Conservative default

    # Get rental income from last tick for this zone
    current_tick = simulation.current_tick
    rent_agg = EconomicLedger.objects.filter(
        simulation=simulation,
        transaction_type="rent",
        tick=max(current_tick, 0),
    ).filter(
        to_agent__zone=prop.zone,
    ).aggregate(total=Sum("total_amount"))
    rent_income = rent_agg["total"] or 0.0

    # If no rent data, use book value as proxy for R
    if rent_income <= 0:
        rent_income = book_value * r  # Assume fair return at market rate

    # Trailing 5-tick average growth rate of rent
    g = 0.0
    if current_tick >= 5:
        old_rent_agg = EconomicLedger.objects.filter(
            simulation=simulation,
            transaction_type="rent",
            tick=current_tick - 5,
        ).filter(
            to_agent__zone=prop.zone,
        ).aggregate(total=Sum("total_amount"))
        old_rent = old_rent_agg["total"] or 0.0
        if old_rent > 0:
            g = (rent_income / old_rent) ** (1.0 / 5.0) - 1.0

    # Gordon formula: V = R / max(r - g, 0.01)
    denominator = max(r - g, 0.01)
    fundamental = rent_income / denominator

    # Apply floor and cap
    floor = book_value * _VALUATION_FLOOR_RATIO
    cap = book_value * _VALUATION_CAP_RATIO

    return max(floor, min(cap, fundamental))


def process_property_listings(simulation, tick: int) -> dict:
    """Process property market: expire old listings, match buyers with sellers.

    Called in the economy tick pipeline BEFORE credit market (step 3).

    Steps:
    1. Withdraw listings older than _LISTING_EXPIRY_TICKS
    2. Collect buy_property intents from previous tick's DecisionLog
    3. Match buyers to cheapest listing in their current zone
    4. Execute transfers for buyers with sufficient cash
    5. Record in EconomicLedger with transaction_type="property_sale"

    Returns dict: {"matched": N, "expired": M, "failed": K}
    """
    result = {"matched": 0, "expired": 0, "failed": 0}

    # Step 1: Expire old listings
    expired = PropertyListing.objects.filter(
        property__simulation=simulation,
        status="listed",
        listed_at_tick__lte=tick - _LISTING_EXPIRY_TICKS,
    )
    expired_count = expired.count()
    if expired_count > 0:
        expired.update(status="withdrawn")
        result["expired"] = expired_count
        logger.info(
            "Property market: expired %d listings in simulation %d",
            expired_count, simulation.id,
        )

    # Step 2: Collect buy intents from previous tick
    if tick <= 0:
        return result

    buy_intents = DecisionLog.objects.filter(
        simulation=simulation,
        tick=tick - 1,
        output_decision__contains='"buy_property"',
    ).select_related("agent")

    buyers = []
    for log in buy_intents:
        try:
            decision = json.loads(log.output_decision)
            if decision.get("action") == "buy_property":
                buyers.append(log.agent)
        except (json.JSONDecodeError, TypeError):
            continue

    if not buyers:
        return result

    # Get primary currency
    primary_currency = Currency.objects.filter(
        simulation=simulation, is_primary=True,
    ).first()
    if not primary_currency:
        return result
    cur_code = primary_currency.code

    # Step 3-5: Match and execute
    for buyer in buyers:
        # Find cheapest active listing in buyer's current zone
        listing = (
            PropertyListing.objects.filter(
                property__simulation=simulation,
                property__zone=buyer.zone,
                status="listed",
            )
            .exclude(property__owner=buyer)  # No self-purchase (M-5)
            .select_related("property", "property__owner")
            .order_by("asking_price")
            .first()
        )

        if not listing:
            continue

        # Check buyer has enough cash
        try:
            buyer_inv = buyer.inventory
        except AgentInventory.DoesNotExist:
            result["failed"] += 1
            continue

        buyer_cash = buyer_inv.cash.get(cur_code, 0.0)
        if buyer_cash < listing.asking_price:
            result["failed"] += 1
            continue

        # Execute transfer
        seller = listing.property.owner
        price = listing.asking_price

        # Deduct from buyer
        buyer_inv.cash[cur_code] = buyer_cash - price
        buyer_inv.save(update_fields=["cash"])

        # Credit seller
        if seller:
            try:
                seller_inv = seller.inventory
                seller_inv.cash[cur_code] = seller_inv.cash.get(cur_code, 0.0) + price
                seller_inv.save(update_fields=["cash"])
            except AgentInventory.DoesNotExist:
                pass

        # Transfer ownership
        prop = listing.property
        prop.owner = buyer
        prop.owner_type = "agent"
        prop.save(update_fields=["owner", "owner_type"])

        # Mark listing as sold
        listing.status = "sold"
        listing.save(update_fields=["status"])

        # Record in ledger
        EconomicLedger.objects.create(
            simulation=simulation,
            tick=tick,
            from_agent=buyer,
            to_agent=seller,
            currency=primary_currency,
            total_amount=price,
            transaction_type="property_sale",
        )

        result["matched"] += 1
        logger.info(
            "Property sold: %s -> %s for %.0f (%s)",
            seller.name if seller else "government",
            buyer.name,
            price,
            prop.name,
        )

    return result


def process_expropriation(
    simulation,
    old_type: str,
    new_type: str,
    tick: int,
) -> int:
    """Execute property redistribution on government transition.

    The expropriation policy is determined by the NEW government type.
    Reads expropriation_policies from simulation.config.

    Policies:
    - "none": no change
    - "elite_seizure": elite/wealthy agent properties -> government
    - "nationalize_all": ALL agent-owned properties -> government
    - "redistribute": above-median properties -> distributed to poor

    Side effects:
    - Active PropertyListings on expropriated properties are withdrawn
    - Loans collateralized by expropriated properties are defaulted
    - Affected agents receive negative memories (emotional_weight=0.8)

    Source: Acemoglu & Robinson (2006).

    Returns number of properties transferred.
    """
    sim_config = simulation.config or {}
    policies = sim_config.get("expropriation_policies", {})
    policy = policies.get(new_type, "none")

    if policy == "none":
        return 0

    # Select properties to expropriate based on policy
    if policy == "nationalize_all":
        target_properties = list(
            Property.objects.filter(
                simulation=simulation, owner_type="agent",
            ).select_related("owner")
        )
    elif policy == "elite_seizure":
        target_properties = list(
            Property.objects.filter(
                simulation=simulation, owner_type="agent",
                owner__social_class__in=["elite", "wealthy"],
            ).select_related("owner")
        )
    elif policy == "redistribute":
        # Properties above median value
        all_props = list(
            Property.objects.filter(
                simulation=simulation, owner_type="agent",
            ).select_related("owner").order_by("value")
        )
        if len(all_props) < 2:
            return 0
        median_idx = len(all_props) // 2
        median_value = all_props[median_idx].value
        target_properties = [p for p in all_props if p.value > median_value]
    else:
        logger.warning(
            "Unknown expropriation policy %r for %r", policy, new_type,
        )
        return 0

    if not target_properties:
        return 0

    affected_agents: set[int] = set()
    transferred = 0

    for prop in target_properties:
        previous_owner = prop.owner
        if previous_owner:
            affected_agents.add(previous_owner.id)

        # Withdraw active listing if any
        PropertyListing.objects.filter(
            property=prop, status="listed",
        ).update(status="withdrawn")

        # Default loans collateralized by this property
        Loan.objects.filter(
            collateral=prop, status="active",
        ).update(status="defaulted")

        # Transfer to government
        prop.owner = None
        prop.owner_type = "government"
        prop.save(update_fields=["owner", "owner_type"])

        transferred += 1

    # Create negative memories for affected agents
    for agent_id in affected_agents:
        try:
            agent = Agent.objects.get(id=agent_id)
        except Agent.DoesNotExist:
            continue

        Memory.objects.create(
            agent=agent,
            content=(
                f"The new {new_type} government has expropriated my property. "
                f"Everything I owned has been seized."
            ),
            emotional_weight=0.8,
            source_type="direct",
            tick_created=tick,
            origin_agent=agent,
        )

    if transferred > 0:
        logger.info(
            "Expropriation: simulation=%d tick=%d policy=%s, "
            "%d properties transferred, %d agents affected",
            simulation.id, tick, policy, transferred, len(affected_agents),
        )

    return transferred
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `docker compose -f docker-compose.local.yml exec web pytest epocha/apps/economy/tests/test_property_market.py -v --tb=short`
Expected: all pass.

- [ ] **Step 5: Run full economy test suite**

Run: `docker compose -f docker-compose.local.yml exec web pytest epocha/apps/economy/tests/ -x -q`
Expected: all pass.

- [ ] **Step 6: Commit**

```
feat(economy): add property market with Gordon valuation and expropriation

CHANGE: New property_market.py module with three functions:
compute_gordon_valuation (Gordon 1959), process_property_listings
(listing/matching with tick+1 settlement), and process_expropriation
(Acemoglu & Robinson 2006 property redistribution on regime change).
```

---

### Task 8: New actions in decision pipeline

**Files:**
- Modify: `epocha/apps/agents/decision.py`
- Modify: `epocha/apps/simulation/engine.py`
- Modify: `epocha/apps/dashboard/formatters.py`

- [ ] **Step 1: Update system prompt in decision.py**

In `epocha/apps/agents/decision.py`, update `_DECISION_SYSTEM_PROMPT` (around line 23). Replace the action list:

```python
_DECISION_SYSTEM_PROMPT = """You are simulating a person in a world. Based on your personality,
memories, relationships, and current situation, decide what to do next.

Respond ONLY with a JSON object:
{
    "action": "work|rest|socialize|explore|trade|argue|help|avoid|form_group|join_group|crime|protest|campaign|move_to|hoard|borrow|sell_property|buy_property",
    "target": "who or what (optional)",
    "reason": "brief internal thought"
}
"""
```

- [ ] **Step 2: Add mood deltas and emotional weights in simulation/engine.py**

In `epocha/apps/simulation/engine.py`, add to `_ACTION_EMOTIONAL_WEIGHT` dict:

```python
    "borrow": 0.2,
    "sell_property": 0.3,
    "buy_property": 0.3,
```

Add to `_ACTION_MOOD_DELTA` dict:

```python
    "borrow": -0.02,
    "sell_property": -0.01,
    "buy_property": 0.02,
```

- [ ] **Step 3: Add action handlers in apply_agent_action**

In `epocha/apps/simulation/engine.py`, in `apply_agent_action`, AFTER the `move_to` handler block (around line 149) and BEFORE the memory creation code, add:

```python
    # Handle borrow action
    if action_type == "borrow":
        try:
            from epocha.apps.economy.credit import (
                evaluate_credit_request,
                find_best_unpledged_property,
                issue_loan,
            )
            from epocha.apps.agents.models import Memory as BorrowMemory

            collateral = find_best_unpledged_property(agent)
            if collateral:
                target_str = action.get("target", "")
                try:
                    amount = float(target_str)
                except (ValueError, TypeError):
                    amount = collateral.value * 0.5

                approved, result = evaluate_credit_request(
                    borrower=agent,
                    amount=amount,
                    collateral_property=collateral,
                    simulation=agent.simulation,
                )
                if approved:
                    tick_num = agent.simulation.current_tick + 1
                    issue_loan(
                        simulation=agent.simulation,
                        lender=None,
                        borrower=agent,
                        amount=amount,
                        interest_rate=result,
                        collateral=collateral,
                        tick=tick_num,
                        lender_type="banking",
                    )
                else:
                    BorrowMemory.objects.create(
                        agent=agent,
                        content=f"Loan request denied: {result}",
                        emotional_weight=0.3,
                        source_type="direct",
                        tick_created=agent.simulation.current_tick + 1,
                        origin_agent=agent,
                    )
        except Exception:
            logger.exception("Borrow action failed for %s", agent.name)

    # Handle sell_property action
    if action_type == "sell_property":
        try:
            from epocha.apps.economy.models import Property, PropertyListing
            from epocha.apps.economy.property_market import compute_gordon_valuation
            from epocha.apps.economy.models import AgentExpectation

            target_type = action.get("target", "")
            props = Property.objects.filter(owner=agent, owner_type="agent")
            if target_type:
                props = props.filter(property_type__icontains=target_type)
            prop = props.first()

            if prop:
                # Skip if already actively listed
                if not PropertyListing.objects.filter(
                    property=prop, status="listed"
                ).exists():
                    # Delete old listings to avoid OneToOneField violation
                    PropertyListing.objects.filter(property=prop).exclude(
                        status="listed"
                    ).delete()

                    fundamental = compute_gordon_valuation(prop, agent.simulation)

                    # Expectation multiplier
                    multiplier = 1.0
                    exp = AgentExpectation.objects.filter(
                        agent=agent,
                    ).first()
                    if exp:
                        if exp.trend_direction == "rising":
                            multiplier = 1.1
                        elif exp.trend_direction == "falling":
                            multiplier = 0.9

                    asking = fundamental * multiplier
                    PropertyListing.objects.create(
                        property=prop,
                        asking_price=asking,
                        fundamental_value=fundamental,
                        listed_at_tick=agent.simulation.current_tick + 1,
                    )
        except Exception:
            logger.exception("Sell property action failed for %s", agent.name)

    # Handle buy_property -- intent only, matching at tick+1
    # The DecisionLog already captures the action; process_property_listings
    # reads it in the next tick's economy pipeline.
```

- [ ] **Step 4: Add dashboard verbs in formatters.py**

In `epocha/apps/dashboard/formatters.py`, add to `_ACTION_VERBS`:

```python
    "borrow": "takes out a loan",
    "sell_property": "lists property for sale",
    "buy_property": "wants to buy property",
```

- [ ] **Step 5: Run full test suite**

Run: `docker compose -f docker-compose.local.yml exec web pytest epocha/apps/economy/tests/ epocha/apps/agents/ -x -q`
Expected: all pass.

- [ ] **Step 6: Commit**

```
feat(economy): add borrow, sell_property, buy_property actions

CHANGE: Three new LLM-driven actions in the decision pipeline.
Borrow executes immediately via evaluate_credit_request + issue_loan.
Sell creates a PropertyListing with Gordon valuation. Buy records
intent for tick+1 matching. System prompt and dashboard verbs updated.
```

---

### Task 9: Pipeline and government integration

**Files:**
- Modify: `epocha/apps/economy/engine.py`
- Modify: `epocha/apps/world/government.py`

- [ ] **Step 1: Wire property market into economy engine**

In `epocha/apps/economy/engine.py`, add import:

```python
from .property_market import process_property_listings
```

In `process_economy_tick_new`, inside the `if not credit_processed:` block, BEFORE the credit calls (`service_loans`, etc.), add:

```python
            # === STEP 3: PROPERTY MARKET ===
            # Process listings and match buyers from previous tick.
            # Runs before credit so property sales generate cash that
            # may prevent loan defaults.
            process_property_listings(simulation, tick)
```

- [ ] **Step 2: Add expropriation hook to government.py**

In `epocha/apps/world/government.py`, in `check_transitions`, AFTER the memory broadcast block (around line 497, after `return target_type`), add the expropriation call. The hook must go BEFORE the return:

Find the block:
```python
    logger.info(
        "Regime transition: simulation=%d tick=%d %s -> %s",
        simulation.pk, current_tick, previous_type, target_type,
    )
    return target_type
```

Insert BEFORE the logger.info:
```python
    # Expropriation hook: redistribute property per new regime's policy.
    # Safe to call when economy is not initialized (no-op if config missing).
    try:
        from epocha.apps.economy.property_market import process_expropriation
        process_expropriation(simulation, previous_type, target_type, current_tick)
    except Exception:
        logger.debug("Expropriation skipped (economy not initialized or error)")
```

Also add the same hook in `attempt_coup`, after the coup succeeds. Find the coup success block where `government.government_type = new_type` is set. Add the same expropriation call after the memory broadcast.

- [ ] **Step 3: Run full test suite**

Run: `docker compose -f docker-compose.local.yml exec web pytest epocha/ -x -q --tb=short`
Expected: all pass.

- [ ] **Step 4: Commit**

```
feat(economy): wire property market and expropriation into pipeline

CHANGE: process_property_listings runs as step 3 in the economy tick,
before credit market. Expropriation hook added to check_transitions
and attempt_coup in government.py -- redistributes property per the
new regime's policy on every government transition.
```

---

### Task 10: Update credit.py transaction types

**Files:**
- Modify: `epocha/apps/economy/credit.py`

- [ ] **Step 1: Replace "trade" with specific transaction types**

In `epocha/apps/economy/credit.py`, find all `transaction_type="trade"` and replace:

1. In `issue_loan` (loan disbursement): replace `transaction_type="trade"` with `transaction_type="loan_issued"`

2. In `service_loans` (interest payment): replace `transaction_type="trade"` with `transaction_type="loan_interest"`

3. In `process_maturity` (loan repayment): replace `transaction_type="trade"` with `transaction_type="loan_interest"` for the repayment ledger entry

There should be 3 occurrences to replace.

- [ ] **Step 2: Run full test suite**

Run: `docker compose -f docker-compose.local.yml exec web pytest epocha/apps/economy/tests/ -x -q`
Expected: all pass (no tests assert on specific transaction_type values for loan operations).

- [ ] **Step 3: Commit**

```
refactor(economy): use specific transaction types for loan operations

CHANGE: Loan disbursements now use transaction_type="loan_issued",
interest payments use "loan_interest". Previously all used "trade",
making loan operations indistinguishable from goods trading in analytics.
```

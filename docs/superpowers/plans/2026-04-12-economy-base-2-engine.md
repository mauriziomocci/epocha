# Economy Base Implementation Plan — Part 2: Engine

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the economic engine that runs each tick: CES production, Walrasian market clearing with tatonnement, emergent Ricardian rent, wages, taxation with government treasury, monetary velocity update, and wealth/mood/stability feedback. After this plan, the economy produces real dynamics: prices change, agents accumulate wealth from production, rents emerge from property, taxes fund the government, and economic conditions affect political stability.

**Architecture:** Five new modules in `epocha.apps.economy`: `production.py` (CES function), `market.py` (tatonnement clearing), `distribution.py` (rent, wages, taxes), `monetary.py` (Fisher velocity), `engine.py` (tick pipeline orchestrator). Each module has a single responsibility and is independently testable.

**Tech Stack:** Django ORM, math (CES formula), no external deps.

**Spec:** `docs/superpowers/specs/2026-04-12-economy-base-design.md` (Production Engine, Market Clearing, Rent/Wages/Taxation sections)

**Depends on:** Part 1 (Data Layer) — completed. All 10 models exist, templates loaded.

**Follow-up:** Part 3 — Integration (decision engine context, hoard action, political feedback, initialization, old economy deprecation).

---

## File Structure (Part 2 scope)

| File | Responsibility | New/Modify |
|------|---------------|------------|
| `epocha/apps/economy/production.py` | CES production function + per-agent output | New |
| `epocha/apps/economy/market.py` | Walrasian tatonnement market clearing | New |
| `epocha/apps/economy/distribution.py` | Rent, wages, taxation | New |
| `epocha/apps/economy/monetary.py` | Fisher velocity update + diagnostics | New |
| `epocha/apps/economy/engine.py` | Tick pipeline orchestrator (7 steps) | New |
| `epocha/apps/economy/tests/test_production.py` | CES function tests | New |
| `epocha/apps/economy/tests/test_market.py` | Tatonnement tests | New |
| `epocha/apps/economy/tests/test_distribution.py` | Rent/wage/tax tests | New |
| `epocha/apps/economy/tests/test_monetary.py` | Velocity update tests | New |
| `epocha/apps/economy/tests/test_engine.py` | Integration test for full tick | New |

---

## Tasks summary (Part 2 scope)

6. **CES production function** — pure math function + per-agent production logic
7. **Market clearing** — tatonnement algorithm with supply/demand collection
8. **Distribution** — rent computation, wage payment, tax collection
9. **Monetary update + wealth feedback** — Fisher velocity, Agent.wealth sync, mood/stability
10. **Tick pipeline orchestrator** — engine.py wiring all steps together

---

### Task 6: CES production function

**Files:**
- Create: `epocha/apps/economy/production.py`
- Create: `epocha/apps/economy/tests/test_production.py`

- [ ] **Step 1: Write the failing tests**

Create `epocha/apps/economy/tests/test_production.py`:

```python
"""Tests for the CES production function.

The CES (Constant Elasticity of Substitution) function was introduced by
Arrow, Chenery, Minhas & Solow (1961). It generalizes Cobb-Douglas
(sigma=1) and Leontief (sigma->0) as special cases.
"""
import math

import pytest

from epocha.apps.economy.production import ces_production, compute_agent_output


class TestCESProduction:
    def test_zero_inputs_zero_output(self):
        # No inputs = no production
        result = ces_production(
            scale=10.0, sigma=0.5,
            factor_weights={"labor": 0.5, "capital": 0.5},
            factor_inputs={"labor": 0.0, "capital": 0.0},
        )
        assert result == 0.0

    def test_positive_output_with_inputs(self):
        result = ces_production(
            scale=10.0, sigma=0.5,
            factor_weights={"labor": 0.6, "capital": 0.4},
            factor_inputs={"labor": 1.0, "capital": 1.0},
        )
        assert result > 0.0

    def test_scale_parameter_multiplies_output(self):
        # Doubling A should double Q
        base = {"labor": 0.6, "capital": 0.4}
        inputs = {"labor": 1.0, "capital": 1.0}
        q1 = ces_production(scale=10.0, sigma=0.5, factor_weights=base, factor_inputs=inputs)
        q2 = ces_production(scale=20.0, sigma=0.5, factor_weights=base, factor_inputs=inputs)
        assert abs(q2 / q1 - 2.0) < 0.01

    def test_sigma_one_approximates_cobb_douglas(self):
        # At sigma=1, CES converges to Cobb-Douglas: Q = A * L^alpha * K^beta
        # With sigma very close to 1 (e.g. 0.999), result should approximate CD
        weights = {"labor": 0.6, "capital": 0.4}
        inputs = {"labor": 2.0, "capital": 3.0}
        ces_result = ces_production(scale=1.0, sigma=0.999, factor_weights=weights, factor_inputs=inputs)
        # Cobb-Douglas: 1.0 * 2.0^0.6 * 3.0^0.4
        cd_result = 1.0 * (2.0 ** 0.6) * (3.0 ** 0.4)
        assert abs(ces_result - cd_result) / cd_result < 0.05

    def test_low_sigma_approaches_leontief(self):
        # At sigma->0, CES approaches min(alpha_i * X_i) behavior
        # With very low sigma (0.01), output limited by scarcest factor
        weights = {"labor": 0.5, "capital": 0.5}
        inputs_balanced = {"labor": 1.0, "capital": 1.0}
        inputs_unbalanced = {"labor": 1.0, "capital": 0.1}
        q_balanced = ces_production(scale=1.0, sigma=0.01, factor_weights=weights, factor_inputs=inputs_balanced)
        q_unbalanced = ces_production(scale=1.0, sigma=0.01, factor_weights=weights, factor_inputs=inputs_unbalanced)
        # Unbalanced should produce much less than balanced
        assert q_unbalanced < q_balanced * 0.5

    def test_weights_are_normalized(self):
        # Unnormalized weights (sum != 1) should still work correctly
        weights_unnorm = {"labor": 3.0, "capital": 2.0}
        weights_norm = {"labor": 0.6, "capital": 0.4}
        inputs = {"labor": 1.0, "capital": 1.0}
        q1 = ces_production(scale=10.0, sigma=0.5, factor_weights=weights_unnorm, factor_inputs=inputs)
        q2 = ces_production(scale=10.0, sigma=0.5, factor_weights=weights_norm, factor_inputs=inputs)
        assert abs(q1 - q2) < 0.01

    def test_three_factors(self):
        # CES works with 3+ factors (Arrow et al. 1961 extension)
        weights = {"labor": 0.4, "capital": 0.3, "resources": 0.3}
        inputs = {"labor": 2.0, "capital": 1.5, "resources": 1.0}
        result = ces_production(scale=5.0, sigma=0.5, factor_weights=weights, factor_inputs=inputs)
        assert result > 0.0

    def test_missing_factor_treated_as_zero(self):
        weights = {"labor": 0.6, "capital": 0.4}
        inputs = {"labor": 1.0}  # capital missing
        result = ces_production(scale=10.0, sigma=0.5, factor_weights=weights, factor_inputs=inputs)
        # With one factor at zero, output should be reduced but not necessarily zero
        # (depends on sigma -- at high sigma, substitution is possible)
        assert result >= 0.0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `docker compose -f docker-compose.local.yml run --rm web pytest epocha/apps/economy/tests/test_production.py -v`

Expected: ImportError.

- [ ] **Step 3: Implement production.py**

Create `epocha/apps/economy/production.py`:

```python
"""CES production function and per-agent output computation.

The Constant Elasticity of Substitution (CES) production function
generalizes Cobb-Douglas (sigma=1) and Leontief (sigma->0):

    Q = A * [sum_i(alpha_i * X_i^rho)]^(1/rho)

    where rho = (sigma - 1) / sigma

Source: Arrow, K., Chenery, H., Minhas, B., & Solow, R. (1961).
"Capital-labor substitution and economic efficiency." Review of
Economics and Statistics. Extended to 3+ factors per Shoven & Whalley
(1992), chapter 3.

Factor weights are normalized to sum to 1 internally. This ensures
the weights control only the relative importance of factors, while
the scale parameter A controls the absolute output level. Standard
practice in applied CGE (Shoven & Whalley 1992).
"""
from __future__ import annotations

import logging
import math

logger = logging.getLogger(__name__)

# Sigma threshold below which we use the Leontief approximation
# to avoid numerical instability (rho approaches negative infinity).
_LEONTIEF_THRESHOLD = 0.05

# Sigma threshold above which we use the Cobb-Douglas log-form
# to avoid numerical issues (rho approaches zero).
_COBB_DOUGLAS_THRESHOLD = 0.95
_COBB_DOUGLAS_UPPER = 1.05


def ces_production(
    *,
    scale: float,
    sigma: float,
    factor_weights: dict[str, float],
    factor_inputs: dict[str, float],
) -> float:
    """Compute CES production output.

    Args:
        scale: Total factor productivity (A). Multiplies final output.
        sigma: Elasticity of substitution. Controls factor substitutability:
            sigma < 1: complements (hard to substitute, pre-industrial)
            sigma = 1: Cobb-Douglas (unit elasticity)
            sigma > 1: substitutes (easy to substitute, modern)
            Tunable per era via template. Antras (2004) estimates sigma < 1
            for historical economies; Karabarbounis & Neiman (2014) estimate
            sigma > 1 for modern economies.
        factor_weights: {factor_code: weight}. Normalized internally to
            sum to 1. Controls relative importance of each factor.
        factor_inputs: {factor_code: quantity}. Actual input amounts.
            Missing factors default to 0.

    Returns:
        Production output Q >= 0.
    """
    if not factor_weights or not factor_inputs:
        return 0.0

    # Normalize weights to sum to 1
    weight_sum = sum(factor_weights.values())
    if weight_sum <= 0:
        return 0.0
    weights = {k: v / weight_sum for k, v in factor_weights.items()}

    # Collect (weight, input) pairs for factors that have positive weight
    pairs = []
    for factor, alpha in weights.items():
        x = factor_inputs.get(factor, 0.0)
        if alpha > 0:
            pairs.append((alpha, max(0.0, x)))

    if not pairs:
        return 0.0

    # Check if all inputs are zero
    if all(x == 0.0 for _, x in pairs):
        return 0.0

    # Leontief limit (sigma -> 0): Q = A * min(X_i / alpha_i)
    # Actually for CES as sigma->0: Q = A * min_i(X_i) when weights are equal
    # More precisely: Q = A * min_i((X_i / alpha_i)^alpha_i) but we use
    # the standard approximation min(alpha_i * X_i^rho)^(1/rho) -> min
    if sigma < _LEONTIEF_THRESHOLD:
        min_val = min(alpha * x if x > 0 else 0.0 for alpha, x in pairs)
        return scale * min_val

    # Cobb-Douglas limit (sigma -> 1): Q = A * prod(X_i^alpha_i)
    if _COBB_DOUGLAS_THRESHOLD < sigma < _COBB_DOUGLAS_UPPER:
        log_q = 0.0
        for alpha, x in pairs:
            if x <= 0:
                return 0.0  # CD with zero input = zero output
            log_q += alpha * math.log(x)
        return scale * math.exp(log_q)

    # General CES: Q = A * [sum(alpha_i * X_i^rho)]^(1/rho)
    rho = (sigma - 1.0) / sigma

    inner_sum = 0.0
    for alpha, x in pairs:
        if x <= 0:
            if rho < 0:
                # With rho < 0, X^rho -> infinity as X -> 0
                # This means zero input makes the sum blow up
                # and the output approaches zero (complementarity)
                return 0.0
            # With rho > 0, X^rho -> 0, so zero input contributes nothing
            continue
        inner_sum += alpha * (x ** rho)

    if inner_sum <= 0:
        return 0.0

    return scale * (inner_sum ** (1.0 / rho))


def compute_agent_output(
    *,
    agent_role: str,
    zone_economy,
    properties_in_zone: list,
    role_production: dict,
    zone_type_resources: dict,
    zone_type: str,
    default_sigma: float,
) -> tuple[str, float]:
    """Compute what and how much an agent produces in one tick.

    Args:
        agent_role: The agent's role (e.g. "farmer", "merchant").
        zone_economy: The ZoneEconomy instance for the agent's zone.
        properties_in_zone: List of Property instances in the zone.
        role_production: Template config mapping roles to goods + skill weights.
        zone_type_resources: Template config mapping zone types to factor abundances.
        zone_type: The zone's type (urban, rural, etc.).
        default_sigma: CES sigma from the template.

    Returns:
        Tuple of (good_code, quantity_produced). If the agent's role
        is not mapped, produces the zone's dominant good.
    """
    # Determine what good this agent produces
    role_config = role_production.get(agent_role.lower())
    if role_config:
        good_code = role_config["good"]
        skill_weight = role_config.get("skill_weight", 1.0)
    else:
        # Fallback: produce the zone's dominant good (highest scale factor)
        prod_config = zone_economy.production_config
        if prod_config:
            good_code = max(prod_config, key=lambda g: prod_config[g].get("scale", 0))
        else:
            return ("subsistence", 0.0)
        skill_weight = 0.8  # unmapped roles are less efficient

    # Get production config for this good in this zone
    good_prod = zone_economy.production_config.get(good_code, {})
    scale = good_prod.get("scale", 1.0)
    sigma = good_prod.get("sigma", default_sigma)
    factor_weights = good_prod.get("factors", {})

    # If no factor weights specified, use defaults from zone type
    if not factor_weights:
        factor_weights = zone_type_resources.get(zone_type, {"labor": 1.0})

    # Build factor inputs
    zone_resources = zone_economy.natural_resources
    zone_res = zone_type_resources.get(zone_type, {})

    # Capital: sum of production bonuses from properties in zone for this good
    capital_input = sum(
        p.production_bonus.get(good_code, 0.0)
        for p in properties_in_zone
    )

    factor_inputs = {
        "labor": skill_weight,
        "capital": capital_input,
        "natural_resources": zone_resources.get(
            "natural_resources", zone_res.get("natural_resources", 0.5)
        ),
        "knowledge": zone_resources.get(
            "knowledge", zone_res.get("knowledge", 0.5)
        ),
    }

    output = ces_production(
        scale=scale,
        sigma=sigma,
        factor_weights=factor_weights,
        factor_inputs=factor_inputs,
    )

    return (good_code, output)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `docker compose -f docker-compose.local.yml run --rm web pytest epocha/apps/economy/tests/test_production.py -v`

Expected: all PASS.

- [ ] **Step 5: Commit**

```
feat(economy): add CES production function with multi-factor support

CHANGE: Implement the CES production function (Arrow et al. 1961) with
automatic Cobb-Douglas (sigma~1) and Leontief (sigma~0) limit handling,
internal weight normalization (Shoven & Whalley 1992), and per-agent
output computation mapping roles to goods via template configuration.
```

---

### Task 7: Market clearing (Walrasian tatonnement)

**Files:**
- Create: `epocha/apps/economy/market.py`
- Create: `epocha/apps/economy/tests/test_market.py`

- [ ] **Step 1: Write the failing tests**

Create `epocha/apps/economy/tests/test_market.py`:

```python
"""Tests for Walrasian tatonnement market clearing.

Source: Walras (1874) for the mechanism. Scarf (1960) for the
non-convergence caveat. Shoven & Whalley (1992) ch. 4 for applied
CGE practice.
"""
import pytest

from epocha.apps.economy.market import (
    clear_market,
    collect_supply_and_demand,
    tatonnement_prices,
)


class TestTatonnementPrices:
    def test_excess_demand_raises_price(self):
        prices = {"subsistence": 3.0}
        supply = {"subsistence": 100.0}
        demand = {"subsistence": 150.0}
        new_prices, converged = tatonnement_prices(prices, supply, demand)
        assert new_prices["subsistence"] > 3.0

    def test_excess_supply_lowers_price(self):
        prices = {"subsistence": 3.0}
        supply = {"subsistence": 150.0}
        demand = {"subsistence": 100.0}
        new_prices, converged = tatonnement_prices(prices, supply, demand)
        assert new_prices["subsistence"] < 3.0

    def test_balanced_market_converges(self):
        prices = {"subsistence": 3.0}
        supply = {"subsistence": 100.0}
        demand = {"subsistence": 100.0}
        new_prices, converged = tatonnement_prices(prices, supply, demand)
        assert converged is True
        assert abs(new_prices["subsistence"] - 3.0) < 0.01

    def test_multiple_goods(self):
        prices = {"subsistence": 3.0, "luxury": 50.0}
        supply = {"subsistence": 100.0, "luxury": 10.0}
        demand = {"subsistence": 120.0, "luxury": 5.0}
        new_prices, converged = tatonnement_prices(prices, supply, demand)
        assert new_prices["subsistence"] > 3.0  # excess demand
        assert new_prices["luxury"] < 50.0  # excess supply

    def test_zero_supply_uses_epsilon_floor(self):
        prices = {"subsistence": 3.0}
        supply = {"subsistence": 0.0}
        demand = {"subsistence": 50.0}
        new_prices, converged = tatonnement_prices(prices, supply, demand)
        # Price should rise significantly but not to infinity
        assert new_prices["subsistence"] > 3.0
        assert new_prices["subsistence"] < 10000.0

    def test_prices_never_negative(self):
        prices = {"subsistence": 0.1}
        supply = {"subsistence": 1000.0}
        demand = {"subsistence": 1.0}
        new_prices, _ = tatonnement_prices(prices, supply, demand)
        assert new_prices["subsistence"] > 0.0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `docker compose -f docker-compose.local.yml run --rm web pytest epocha/apps/economy/tests/test_market.py -v`

Expected: ImportError.

- [ ] **Step 3: Implement market.py**

Create `epocha/apps/economy/market.py`:

```python
"""Walrasian tatonnement market clearing.

Each zone has a local market where supply meets demand. Prices adjust
iteratively toward equilibrium using the tatonnement mechanism.

Source: Walras, L. (1874). Elements of Pure Economics.
Warning: Scarf (1960) showed tatonnement may not converge with 3+ goods.
The max_iterations parameter is the safety net.
Implementation follows applied CGE practice: Shoven & Whalley (1992) ch. 4.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# Tatonnement parameters. Tunable design parameters without theoretical
# derivation for specific values. Consistent with applied CGE practice
# (Shoven & Whalley 1992).
ADJUSTMENT_RATE = 0.1
MAX_ITERATIONS = 50
CONVERGENCE_THRESHOLD = 0.01
EPSILON = 0.001  # prevents division by zero in supply


def tatonnement_prices(
    current_prices: dict[str, float],
    total_supply: dict[str, float],
    total_demand: dict[str, float],
    *,
    adjustment_rate: float = ADJUSTMENT_RATE,
    max_iterations: int = MAX_ITERATIONS,
    convergence_threshold: float = CONVERGENCE_THRESHOLD,
) -> tuple[dict[str, float], bool]:
    """Compute equilibrium prices via iterative tatonnement.

    For each good: P_new = P_old * (1 + rate * excess / max(supply, epsilon))
    Iterates until |excess/supply| < threshold for all goods, or max_iterations.

    Args:
        current_prices: {good_code: price} starting prices.
        total_supply: {good_code: quantity} total offered.
        total_demand: {good_code: quantity} total demanded.
        adjustment_rate: Step size per iteration. Tunable, default 0.1.
        max_iterations: Safety net for non-convergence (Scarf 1960).
        convergence_threshold: |excess/supply| target.

    Returns:
        Tuple of (new_prices, converged). If not converged, new_prices
        are the last iteration's values (approximate but not catastrophically
        wrong -- they reflect the direction of excess demand/supply).
    """
    prices = dict(current_prices)
    goods = list(prices.keys())

    for iteration in range(max_iterations):
        converged = True
        for good in goods:
            supply = max(total_supply.get(good, 0.0), EPSILON)
            demand = total_demand.get(good, 0.0)
            excess = demand - supply

            relative_excess = abs(excess) / supply
            if relative_excess > convergence_threshold:
                converged = False

            adjustment = adjustment_rate * excess / supply
            prices[good] = max(EPSILON, prices[good] * (1.0 + adjustment))

        if converged:
            return prices, True

    logger.warning(
        "Tatonnement did not converge after %d iterations. "
        "Using last computed prices (approximate). "
        "This is expected with 3+ goods (Scarf 1960).",
        max_iterations,
    )
    return prices, False


def collect_supply_and_demand(
    agent_inventories: list[dict],
    good_categories: list[dict],
    market_prices: dict[str, float],
) -> tuple[dict[str, float], dict[str, float], dict[str, list]]:
    """Collect supply and demand from all agents in a zone.

    Supply: agents offer holdings above subsistence reserve.
    Demand: agents want essential goods they lack, plus non-essential
    goods proportional to cash and inverse price elasticity.

    Args:
        agent_inventories: list of dicts with keys: agent_id, holdings,
            cash_amount, is_hoarding (bool).
        good_categories: list of dicts with keys: code, is_essential,
            price_elasticity.
        market_prices: current prices per good.

    Returns:
        (total_supply, total_demand, agent_orders) where agent_orders
        is a list of {agent_id, offers: {good: qty}, wants: {good: qty}}.
    """
    total_supply: dict[str, float] = {}
    total_demand: dict[str, float] = {}
    agent_orders: list[dict] = []

    essential_codes = {g["code"] for g in good_categories if g["is_essential"]}
    subsistence_need = 1.0  # 1 unit per essential good per tick

    for inv in agent_inventories:
        offers: dict[str, float] = {}
        wants: dict[str, float] = {}

        # Supply: offer surplus above subsistence reserve
        if not inv.get("is_hoarding", False):
            for good_code, qty in inv["holdings"].items():
                if good_code in essential_codes:
                    surplus = max(0.0, qty - subsistence_need)
                else:
                    surplus = qty
                if surplus > 0:
                    offers[good_code] = surplus
                    total_supply[good_code] = total_supply.get(good_code, 0.0) + surplus

        # Demand: essential needs + discretionary spending
        for cat in good_categories:
            code = cat["code"]
            current = inv["holdings"].get(code, 0.0)

            if cat["is_essential"]:
                need = max(0.0, subsistence_need - current)
                if need > 0:
                    wants[code] = need
                    total_demand[code] = total_demand.get(code, 0.0) + need
            else:
                # Non-essential demand proportional to cash / (price * elasticity)
                price = max(market_prices.get(code, 1.0), EPSILON)
                elasticity = max(cat.get("price_elasticity", 1.0), 0.1)
                cash = inv.get("cash_amount", 0.0)
                discretionary = (cash * 0.1) / (price * elasticity)
                if discretionary > 0.01:
                    wants[code] = discretionary
                    total_demand[code] = total_demand.get(code, 0.0) + discretionary

        agent_orders.append({
            "agent_id": inv["agent_id"],
            "offers": offers,
            "wants": wants,
        })

    return total_supply, total_demand, agent_orders


def execute_trades(
    agent_orders: list[dict],
    equilibrium_prices: dict[str, float],
    total_supply: dict[str, float],
    total_demand: dict[str, float],
) -> list[dict]:
    """Execute trades at equilibrium prices.

    When demand exceeds supply, each buyer gets a proportional share.
    When supply exceeds demand, each seller sells a proportional share.

    Returns list of trade records: {buyer_id, seller_id, good, qty, price, total}.
    """
    trades: list[dict] = []

    for good_code in set(list(total_supply.keys()) + list(total_demand.keys())):
        supply = total_supply.get(good_code, 0.0)
        demand = total_demand.get(good_code, 0.0)
        price = equilibrium_prices.get(good_code, 1.0)

        if supply <= 0 or demand <= 0:
            continue

        # Traded quantity is the minimum of supply and demand
        traded = min(supply, demand)

        # Rationing: if demand > supply, buyers get proportional shares
        demand_ratio = traded / demand if demand > 0 else 0.0
        supply_ratio = traded / supply if supply > 0 else 0.0

        # Collect sellers and buyers
        sellers = [(o["agent_id"], o["offers"].get(good_code, 0.0)) for o in agent_orders if o["offers"].get(good_code, 0.0) > 0]
        buyers = [(o["agent_id"], o["wants"].get(good_code, 0.0)) for o in agent_orders if o["wants"].get(good_code, 0.0) > 0]

        # Simple proportional matching
        for buyer_id, want_qty in buyers:
            actual_buy = want_qty * demand_ratio
            if actual_buy < 0.001:
                continue
            cost = actual_buy * price
            # Match with sellers proportionally
            for seller_id, offer_qty in sellers:
                actual_sell = offer_qty * supply_ratio
                if actual_sell < 0.001:
                    continue
                share = min(actual_buy, actual_sell)
                if share > 0.001:
                    trades.append({
                        "buyer_id": buyer_id,
                        "seller_id": seller_id,
                        "good_code": good_code,
                        "quantity": share,
                        "price": price,
                        "total": share * price,
                    })

    return trades
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `docker compose -f docker-compose.local.yml run --rm web pytest epocha/apps/economy/tests/test_market.py -v`

Expected: all PASS.

- [ ] **Step 5: Commit**

```
feat(economy): add Walrasian tatonnement market clearing

CHANGE: Implement iterative price adjustment toward equilibrium (Walras
1874) with convergence safety net for non-converging cases (Scarf 1960).
Supply/demand collection with subsistence reserve, discretionary spending
proportional to cash and price elasticity, and proportional trade
matching at equilibrium prices.
```

---

### Task 8: Distribution (rent, wages, taxes)

**Files:**
- Create: `epocha/apps/economy/distribution.py`
- Create: `epocha/apps/economy/tests/test_distribution.py`

- [ ] **Step 1: Write the failing tests**

Create `epocha/apps/economy/tests/test_distribution.py`:

```python
"""Tests for rent, wage, and tax distribution."""
import pytest

from epocha.apps.economy.distribution import (
    compute_rent,
    compute_wages,
    compute_taxes,
)


class TestComputeRent:
    def test_rent_proportional_to_bonus(self):
        # Property with 1.5x bonus gets 1.5x share
        zone_production = {"subsistence": 100.0}
        properties = [
            {"owner_id": 1, "production_bonus": {"subsistence": 1.5}},
            {"owner_id": 2, "production_bonus": {"subsistence": 1.0}},
        ]
        prices = {"subsistence": 3.0}
        rents = compute_rent(zone_production, properties, prices)
        assert rents[1] > rents[2]
        # Owner 1 gets 60% (1.5/2.5), Owner 2 gets 40% (1.0/2.5)
        assert abs(rents[1] / (rents[1] + rents[2]) - 0.6) < 0.01

    def test_no_properties_no_rent(self):
        rents = compute_rent({"subsistence": 100.0}, [], {"subsistence": 3.0})
        assert rents == {}

    def test_zero_production_zero_rent(self):
        properties = [{"owner_id": 1, "production_bonus": {"subsistence": 1.5}}]
        rents = compute_rent({"subsistence": 0.0}, properties, {"subsistence": 3.0})
        assert rents.get(1, 0.0) == 0.0


class TestComputeWages:
    def test_wage_is_share_of_output_value(self):
        agent_outputs = [
            {"agent_id": 1, "good_code": "subsistence", "quantity": 10.0, "owns_property": False},
        ]
        prices = {"subsistence": 3.0}
        wages = compute_wages(agent_outputs, prices, wage_share=0.6)
        # 10 * 3.0 * 0.6 = 18.0
        assert abs(wages[1] - 18.0) < 0.01

    def test_property_owner_gets_full_value(self):
        agent_outputs = [
            {"agent_id": 1, "good_code": "subsistence", "quantity": 10.0, "owns_property": True},
        ]
        prices = {"subsistence": 3.0}
        wages = compute_wages(agent_outputs, prices, wage_share=0.6)
        # Owner keeps full value: 10 * 3.0 = 30.0
        assert abs(wages[1] - 30.0) < 0.01

    def test_zero_output_zero_wage(self):
        agent_outputs = [
            {"agent_id": 1, "good_code": "subsistence", "quantity": 0.0, "owns_property": False},
        ]
        wages = compute_wages(agent_outputs, {"subsistence": 3.0}, wage_share=0.6)
        assert wages.get(1, 0.0) == 0.0


class TestComputeTaxes:
    def test_tax_is_rate_times_income(self):
        agent_incomes = {1: 100.0, 2: 50.0}
        taxes = compute_taxes(agent_incomes, tax_rate=0.15)
        assert abs(taxes["agent_taxes"][1] - 15.0) < 0.01
        assert abs(taxes["agent_taxes"][2] - 7.5) < 0.01
        assert abs(taxes["total_revenue"] - 22.5) < 0.01

    def test_zero_rate_zero_tax(self):
        taxes = compute_taxes({1: 100.0}, tax_rate=0.0)
        assert taxes["agent_taxes"][1] == 0.0
        assert taxes["total_revenue"] == 0.0

    def test_no_agents_no_tax(self):
        taxes = compute_taxes({}, tax_rate=0.15)
        assert taxes["total_revenue"] == 0.0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `docker compose -f docker-compose.local.yml run --rm web pytest epocha/apps/economy/tests/test_distribution.py -v`

Expected: ImportError.

- [ ] **Step 3: Implement distribution.py**

Create `epocha/apps/economy/distribution.py`:

```python
"""Economic distribution: rent, wages, and taxation.

Rent: emergent from zone production proportional to property bonus.
Source: Ricardo, D. (1817). On the Principles of Political Economy.
Simplification: proportional to bonus instead of differential surplus
vs marginal land. See spec for detailed rationale.

Wages: share of production value for non-property-owners.
In spec 1 this is a fixed share; spec 2 replaces with matching theory.

Taxes: flat income tax on wages + rent, collected into government treasury.
Source for bankruptcy-as-crisis: Doyle, W. (1989). The Oxford History
of the French Revolution.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def compute_rent(
    zone_production: dict[str, float],
    properties: list[dict],
    prices: dict[str, float],
) -> dict[int, float]:
    """Compute rent for each property owner in a zone.

    Rent for a property = (zone output of good * property's share of
    total bonus for that good) * market price of that good.

    This is a simplified Ricardian model: rent emerges proportionally
    from production bonus rather than being computed as differential
    surplus over marginal land (Ricardo 1817). The qualitative behavior
    is correct (productive property yields more rent). See spec for
    the full discussion of this simplification.

    Args:
        zone_production: {good_code: total_quantity_produced_in_zone}
        properties: list of dicts with owner_id, production_bonus
        prices: {good_code: market_price}

    Returns:
        {owner_id: total_rent_in_currency}. Owners with multiple
        properties accumulate rent from all of them.
    """
    if not properties:
        return {}

    # Sum total bonus per good across all properties in zone
    total_bonus: dict[str, float] = {}
    for prop in properties:
        for good, bonus in prop.get("production_bonus", {}).items():
            total_bonus[good] = total_bonus.get(good, 0.0) + bonus

    rents: dict[int, float] = {}
    for prop in properties:
        owner_id = prop.get("owner_id")
        if owner_id is None:
            continue
        prop_rent = 0.0
        for good, bonus in prop.get("production_bonus", {}).items():
            production = zone_production.get(good, 0.0)
            price = prices.get(good, 0.0)
            zone_total = total_bonus.get(good, 0.0)
            if zone_total > 0 and production > 0:
                share = bonus / zone_total
                prop_rent += production * share * price
        rents[owner_id] = rents.get(owner_id, 0.0) + prop_rent

    return rents


def compute_wages(
    agent_outputs: list[dict],
    prices: dict[str, float],
    wage_share: float = 0.6,
) -> dict[int, float]:
    """Compute wages for agents based on their production output.

    Property owners keep the full value of their output. Non-owners
    receive wage_share of the output value.

    wage_share is a template parameter (default 0.6 for pre-industrial).
    In spec 1 this is fixed; spec 2 replaces with Mortensen-Pissarides
    matching theory.

    Args:
        agent_outputs: list of {agent_id, good_code, quantity, owns_property}
        prices: {good_code: market_price}
        wage_share: fraction of output value paid as wages (0-1).
            Tunable design parameter, default 0.6.

    Returns:
        {agent_id: wage_amount}
    """
    wages: dict[int, float] = {}
    for output in agent_outputs:
        agent_id = output["agent_id"]
        good = output["good_code"]
        qty = output["quantity"]
        price = prices.get(good, 0.0)
        value = qty * price

        if output.get("owns_property", False):
            # Owner keeps full value
            wages[agent_id] = wages.get(agent_id, 0.0) + value
        else:
            # Worker gets wage_share
            wages[agent_id] = wages.get(agent_id, 0.0) + value * wage_share

    return wages


def compute_taxes(
    agent_incomes: dict[int, float],
    tax_rate: float,
) -> dict:
    """Compute flat income tax for all agents.

    Args:
        agent_incomes: {agent_id: taxable_income} (wages + rent)
        tax_rate: flat rate (0.0-1.0)

    Returns:
        {"agent_taxes": {agent_id: tax_amount}, "total_revenue": float}
    """
    agent_taxes: dict[int, float] = {}
    total_revenue = 0.0

    for agent_id, income in agent_incomes.items():
        tax = income * tax_rate
        agent_taxes[agent_id] = tax
        total_revenue += tax

    return {"agent_taxes": agent_taxes, "total_revenue": total_revenue}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `docker compose -f docker-compose.local.yml run --rm web pytest epocha/apps/economy/tests/test_distribution.py -v`

Expected: all PASS.

- [ ] **Step 5: Commit**

```
feat(economy): add rent, wage, and tax distribution

CHANGE: Implement emergent Ricardian rent proportional to property
production bonus (simplified vs differential surplus), wage computation
with fixed share for non-owners (default 0.6, spec 2 adds matching),
and flat income tax collected into government treasury. Every constant
is either sourced (Ricardo 1817, Doyle 1989) or marked as tunable.
```

---

### Task 9: Monetary update + wealth feedback

**Files:**
- Create: `epocha/apps/economy/monetary.py`
- Create: `epocha/apps/economy/tests/test_monetary.py`

- [ ] **Step 1: Write the failing tests**

Create `epocha/apps/economy/tests/test_monetary.py`:

```python
"""Tests for monetary velocity update and wealth/mood feedback."""
import math
import pytest

from epocha.apps.economy.monetary import (
    compute_velocity,
    compute_inflation,
    update_agent_wealth,
    compute_mood_delta,
)


class TestComputeVelocity:
    def test_velocity_from_transaction_volume(self):
        # V = transaction_volume / M
        v = compute_velocity(transaction_volume=5000.0, money_supply=50000.0)
        assert abs(v - 0.1) < 0.001

    def test_zero_supply_returns_zero(self):
        v = compute_velocity(transaction_volume=100.0, money_supply=0.0)
        assert v == 0.0

    def test_zero_transactions_returns_zero(self):
        v = compute_velocity(transaction_volume=0.0, money_supply=50000.0)
        assert v == 0.0


class TestComputeInflation:
    def test_positive_inflation(self):
        # Prices went up
        old = {"subsistence": 3.0, "luxury": 50.0}
        new = {"subsistence": 3.3, "luxury": 55.0}
        rate = compute_inflation(old, new)
        assert rate > 0.0

    def test_deflation(self):
        old = {"subsistence": 3.0}
        new = {"subsistence": 2.7}
        rate = compute_inflation(old, new)
        assert rate < 0.0

    def test_stable_prices_zero_inflation(self):
        prices = {"subsistence": 3.0, "luxury": 50.0}
        rate = compute_inflation(prices, prices)
        assert abs(rate) < 0.001

    def test_empty_prices(self):
        rate = compute_inflation({}, {})
        assert rate == 0.0


class TestComputeMoodDelta:
    def test_wealthy_agent_small_boost(self):
        # Kahneman & Deaton (2010): diminishing returns above satiation
        delta = compute_mood_delta(wealth=200.0, satiation_threshold=100.0)
        assert delta > 0.0
        assert delta < 0.02  # should be small (diminishing)

    def test_very_wealthy_near_zero_boost(self):
        delta = compute_mood_delta(wealth=1000.0, satiation_threshold=100.0)
        assert delta > 0.0
        assert delta < 0.005  # almost zero (plateau)

    def test_poor_agent_penalty(self):
        delta = compute_mood_delta(wealth=5.0, satiation_threshold=100.0)
        assert delta < 0.0

    def test_destitute_agent_severe_penalty(self):
        delta = compute_mood_delta(wealth=-10.0, satiation_threshold=100.0)
        assert delta < -0.05

    def test_moderate_wealth_no_change(self):
        delta = compute_mood_delta(wealth=50.0, satiation_threshold=100.0)
        # Moderate wealth: slight positive or near zero
        assert abs(delta) < 0.05
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `docker compose -f docker-compose.local.yml run --rm web pytest epocha/apps/economy/tests/test_monetary.py -v`

Expected: ImportError.

- [ ] **Step 3: Implement monetary.py**

Create `epocha/apps/economy/monetary.py`:

```python
"""Monetary velocity update, inflation computation, and wealth-mood feedback.

Fisher's equation MV=PQ is used as a DIAGNOSTIC check (is the simulated
economy internally consistent?), not as a price-determination mechanism.
Prices are set by the Walrasian market clearing, not by Fisher.

Source: Fisher, I. (1911). The Purchasing Power of Money.

Mood-wealth relationship follows Kahneman & Deaton (2010): emotional
well-being plateaus above a satiation threshold. Implemented as
exponential decay of mood boost above threshold.
"""
from __future__ import annotations

import logging
import math

logger = logging.getLogger(__name__)

# Mood constants. See economy.py (placeholder) for the original values.
# These are tunable parameters; the qualitative behavior (plateau) is
# from Kahneman & Deaton (2010).
_MOOD_BOOST_BASE = 0.02
_MOOD_SATIATION_DECAY = 0.005
_MOOD_PENALTY_POOR = 0.05
_MOOD_PENALTY_DESTITUTE = 0.10
_POVERTY_THRESHOLD = 10.0


def compute_velocity(
    transaction_volume: float,
    money_supply: float,
) -> float:
    """Compute monetary velocity V = transaction_volume / M.

    V is a MEASURED quantity (how many times money changed hands this
    tick), not a parameter. Storing it is caching, not asserting a
    constant.

    Source: Fisher (1911). V = PQ/M, here approximated as total
    transaction value / money supply.
    """
    if money_supply <= 0 or transaction_volume <= 0:
        return 0.0
    return transaction_volume / money_supply


def check_fisher_consistency(
    money_supply: float,
    velocity: float,
    price_level: float,
    output_level: float,
) -> float:
    """Check MV vs PQ consistency (Fisher's equation as diagnostic).

    Returns the relative divergence: |MV - PQ| / max(MV, PQ, 1).
    Values above 0.2 (20%) warrant investigation.

    This is a diagnostic, not an enforcement. The market determines
    prices; Fisher tells us if the money supply is consistent with
    the observed price level and output.
    """
    mv = money_supply * velocity
    pq = price_level * output_level
    denominator = max(mv, pq, 1.0)
    divergence = abs(mv - pq) / denominator

    if divergence > 0.2:
        logger.warning(
            "Fisher MV=PQ divergence: %.1f%%. MV=%.1f, PQ=%.1f. "
            "Money supply may be inconsistent with price level.",
            divergence * 100, mv, pq,
        )

    return divergence


def compute_inflation(
    old_prices: dict[str, float],
    new_prices: dict[str, float],
) -> float:
    """Compute inflation rate as average percentage change in prices.

    Returns a decimal rate (0.10 = 10% inflation, -0.05 = 5% deflation).
    """
    if not old_prices or not new_prices:
        return 0.0

    changes = []
    for good, old_price in old_prices.items():
        new_price = new_prices.get(good)
        if new_price is not None and old_price > 0:
            changes.append((new_price - old_price) / old_price)

    if not changes:
        return 0.0

    return sum(changes) / len(changes)


def update_agent_wealth(
    holdings: dict[str, float],
    cash: dict[str, float],
    property_values: list[float],
    prices: dict[str, float],
) -> float:
    """Compute total agent wealth as sum of inventory value + cash + property.

    This replaces the old Agent.wealth as a computed summary for
    backward compatibility with modules that read it.
    """
    inventory_value = sum(
        qty * prices.get(good, 0.0)
        for good, qty in holdings.items()
    )
    total_cash = sum(cash.values())
    total_property = sum(property_values)
    return inventory_value + total_cash + total_property


def compute_mood_delta(
    wealth: float,
    satiation_threshold: float = 100.0,
) -> float:
    """Compute mood change based on wealth level.

    Source: Kahneman, D. & Deaton, A. (2010). "High income improves
    evaluation of life but not emotional well-being." PNAS.

    Above satiation: diminishing mood boost approaching zero (exponential
    decay). The specific decay rate (_MOOD_SATIATION_DECAY = 0.005) is a
    tunable parameter; the qualitative behavior (plateau) is the paper's
    central finding.

    Below poverty: linear mood penalty. Below zero: severe penalty.
    """
    if wealth < 0:
        return -_MOOD_PENALTY_DESTITUTE
    elif wealth < _POVERTY_THRESHOLD:
        return -_MOOD_PENALTY_POOR
    elif wealth > satiation_threshold:
        # Kahneman & Deaton (2010): plateau above satiation
        excess = wealth - satiation_threshold
        return _MOOD_BOOST_BASE * math.exp(-_MOOD_SATIATION_DECAY * excess)
    else:
        # Moderate wealth: small positive delta
        return _MOOD_BOOST_BASE * 0.5
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `docker compose -f docker-compose.local.yml run --rm web pytest epocha/apps/economy/tests/test_monetary.py -v`

Expected: all PASS.

- [ ] **Step 5: Commit**

```
feat(economy): add monetary velocity, inflation, and wealth-mood feedback

CHANGE: Implement Fisher velocity as measured quantity (not constant),
MV=PQ consistency diagnostic, inflation computation from price changes,
agent wealth as computed summary (inventory + cash + property), and
Kahneman & Deaton (2010) satiation curve for mood-wealth relationship.
```

---

### Task 10: Tick pipeline orchestrator

**Files:**
- Create: `epocha/apps/economy/engine.py`
- Create: `epocha/apps/economy/tests/test_engine.py`

- [ ] **Step 1: Write the failing tests**

Create `epocha/apps/economy/tests/test_engine.py`:

```python
"""Integration tests for the economy tick pipeline.

Tests the full 7-step pipeline on a minimal scenario with real DB models.
"""
import pytest
from django.contrib.gis.geos import Point, Polygon

from epocha.apps.agents.models import Agent
from epocha.apps.economy.engine import process_economy_tick_new
from epocha.apps.economy.models import (
    AgentInventory, Currency, EconomicLedger, GoodCategory,
    PriceHistory, ProductionFactor, Property, TaxPolicy, ZoneEconomy,
)
from epocha.apps.simulation.models import Simulation
from epocha.apps.users.models import User
from epocha.apps.world.models import Government, World, Zone


@pytest.fixture
def user(db):
    return User.objects.create_user(email="eng@epocha.dev", username="enguser", password="pass1234")


@pytest.fixture
def simulation(user):
    return Simulation.objects.create(name="EngineTest", seed=42, owner=user)


@pytest.fixture
def setup_economy(simulation):
    """Create a minimal but complete economic scenario for testing."""
    world = World.objects.create(simulation=simulation, distance_scale=133.0, tick_duration_hours=24.0)
    gov = Government.objects.create(simulation=simulation, government_type="monarchy", government_treasury={})

    # Currency
    currency = Currency.objects.create(
        simulation=simulation, code="LVR", name="Livre",
        symbol="L", is_primary=True, total_supply=10000.0,
    )

    # Goods
    subsistence = GoodCategory.objects.create(
        simulation=simulation, code="subsistence", name="Subsistence",
        is_essential=True, base_price=3.0, price_elasticity=0.3,
    )
    luxury = GoodCategory.objects.create(
        simulation=simulation, code="luxury", name="Luxury",
        is_essential=False, base_price=50.0, price_elasticity=2.0,
    )

    # Factors
    ProductionFactor.objects.create(simulation=simulation, code="labor", name="Labor")
    ProductionFactor.objects.create(simulation=simulation, code="capital", name="Capital")

    # Tax
    TaxPolicy.objects.create(simulation=simulation, income_tax_rate=0.15)

    # Zone
    zone = Zone.objects.create(
        world=world, name="Paris", zone_type="urban",
        boundary=Polygon.from_bbox((0, 0, 100, 100)),
        center=Point(50, 50),
    )
    ze = ZoneEconomy.objects.create(
        zone=zone,
        natural_resources={"labor": 1.0, "capital": 0.5, "natural_resources": 0.3},
        production_config={
            "subsistence": {"scale": 5.0, "sigma": 0.5, "factors": {"labor": 0.6, "capital": 0.4}},
            "luxury": {"scale": 2.0, "sigma": 0.5, "factors": {"labor": 0.3, "capital": 0.7}},
        },
        market_prices={"subsistence": 3.0, "luxury": 50.0},
    )

    # Agents
    farmer = Agent.objects.create(
        simulation=simulation, name="Farmer", role="farmer",
        personality={"openness": 0.5}, location=Point(50, 50),
        zone=zone, health=1.0, wealth=50.0,
    )
    merchant = Agent.objects.create(
        simulation=simulation, name="Merchant", role="merchant",
        personality={"openness": 0.7}, location=Point(50, 50),
        zone=zone, health=1.0, wealth=200.0,
    )

    # Inventories
    AgentInventory.objects.create(
        agent=farmer,
        holdings={"subsistence": 5.0},
        cash={"LVR": 50.0},
    )
    AgentInventory.objects.create(
        agent=merchant,
        holdings={"subsistence": 2.0, "luxury": 1.0},
        cash={"LVR": 200.0},
    )

    # Property (merchant owns a shop)
    Property.objects.create(
        simulation=simulation, owner=merchant, owner_type="agent",
        zone=zone, property_type="shop", name="Merchant Shop",
        value=100.0, production_bonus={"luxury": 1.2},
    )

    return {
        "world": world, "government": gov, "currency": currency,
        "zone": zone, "zone_economy": ze,
        "farmer": farmer, "merchant": merchant,
        "subsistence": subsistence, "luxury": luxury,
    }


@pytest.mark.django_db
class TestProcessEconomyTick:
    def test_full_tick_runs_without_error(self, simulation, setup_economy):
        # Should complete without raising
        process_economy_tick_new(simulation, tick=1)

    def test_prices_recorded_in_history(self, simulation, setup_economy):
        process_economy_tick_new(simulation, tick=1)
        assert PriceHistory.objects.filter(
            zone_economy=setup_economy["zone_economy"], tick=1,
        ).exists()

    def test_transactions_recorded_in_ledger(self, simulation, setup_economy):
        process_economy_tick_new(simulation, tick=1)
        assert EconomicLedger.objects.filter(simulation=simulation, tick=1).exists()

    def test_agent_wealth_updated(self, simulation, setup_economy):
        old_wealth = setup_economy["farmer"].wealth
        process_economy_tick_new(simulation, tick=1)
        setup_economy["farmer"].refresh_from_db()
        # Wealth should have changed (produced goods, traded, paid tax)
        assert setup_economy["farmer"].wealth != old_wealth

    def test_government_treasury_receives_tax(self, simulation, setup_economy):
        process_economy_tick_new(simulation, tick=1)
        setup_economy["government"].refresh_from_db()
        treasury = setup_economy["government"].government_treasury
        assert treasury.get("LVR", 0.0) > 0.0

    def test_currency_velocity_updated(self, simulation, setup_economy):
        process_economy_tick_new(simulation, tick=1)
        setup_economy["currency"].refresh_from_db()
        # Velocity should reflect actual transactions
        assert setup_economy["currency"].cached_velocity >= 0.0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `docker compose -f docker-compose.local.yml run --rm web pytest epocha/apps/economy/tests/test_engine.py -v`

Expected: ImportError.

- [ ] **Step 3: Implement engine.py**

Create `epocha/apps/economy/engine.py`:

```python
"""Economy tick pipeline orchestrator.

Executes the 7-step economic cycle each tick:
1. Production (CES per agent per zone)
2. Market clearing (Walrasian tatonnement)
3. Rent (emergent, Ricardian)
4. Wages (output share)
5. Taxation (flat income tax -> treasury)
6. Monetary update (Fisher velocity)
7. Wealth + mood + stability feedback

This function replaces world/economy.py:process_economy_tick for
simulations that have the new economy app models initialized.
"""
from __future__ import annotations

import logging

from django.db.models import Sum

from epocha.apps.agents.models import Agent

from .distribution import compute_rent, compute_taxes, compute_wages
from .market import collect_supply_and_demand, execute_trades, tatonnement_prices
from .models import (
    AgentInventory,
    Currency,
    EconomicLedger,
    GoodCategory,
    PriceHistory,
    Property,
    TaxPolicy,
    ZoneEconomy,
)
from .monetary import (
    compute_inflation,
    compute_mood_delta,
    compute_velocity,
    update_agent_wealth,
)
from .production import compute_agent_output

logger = logging.getLogger(__name__)


def process_economy_tick_new(simulation, tick: int) -> None:
    """Execute one full economic tick for a simulation.

    This is the main entry point called by the simulation engine.
    It replaces process_economy_tick from world/economy.py for
    simulations with the new economy data layer.
    """
    currencies = list(Currency.objects.filter(simulation=simulation))
    if not currencies:
        logger.debug("Simulation %d has no currencies; skipping economy tick", simulation.id)
        return

    primary_currency = next((c for c in currencies if c.is_primary), currencies[0])
    goods = list(GoodCategory.objects.filter(simulation=simulation))
    good_map = {g.code: g for g in goods}

    try:
        tax_policy = TaxPolicy.objects.get(simulation=simulation)
    except TaxPolicy.DoesNotExist:
        tax_policy = None

    # Get template production config (from the first ZoneEconomy's config)
    zone_economies = list(
        ZoneEconomy.objects.filter(zone__world__simulation=simulation)
        .select_related("zone")
    )
    if not zone_economies:
        return

    # Default production config from the first zone (all zones share template)
    first_ze = zone_economies[0]
    prod_config = first_ze.production_config
    default_sigma = prod_config.get("default_sigma", 0.5) if isinstance(prod_config, dict) and "default_sigma" in prod_config else 0.5
    role_production = prod_config.get("role_production", {}) if isinstance(prod_config, dict) else {}
    zone_type_resources = prod_config.get("zone_type_resources", {}) if isinstance(prod_config, dict) else {}
    wage_share = prod_config.get("wage_share", 0.6) if isinstance(prod_config, dict) else 0.6

    total_transaction_volume = 0.0
    total_output = 0.0
    old_prices_all: dict[str, float] = {}
    new_prices_all: dict[str, float] = {}

    for ze in zone_economies:
        zone = ze.zone
        agents = list(
            Agent.objects.filter(simulation=simulation, zone=zone, is_alive=True)
            .select_related("inventory")
        )
        if not agents:
            continue

        properties = list(
            Property.objects.filter(simulation=simulation, zone=zone)
        )
        property_owner_ids = {p.owner_id for p in properties if p.owner_id}

        old_prices = dict(ze.market_prices)
        old_prices_all.update(old_prices)

        # === STEP 1: PRODUCTION ===
        zone_production: dict[str, float] = {}
        agent_outputs: list[dict] = []

        for agent in agents:
            good_code, quantity = compute_agent_output(
                agent_role=agent.role,
                zone_economy=ze,
                properties_in_zone=properties,
                role_production=role_production,
                zone_type_resources=zone_type_resources,
                zone_type=zone.zone_type,
                default_sigma=default_sigma,
            )

            if quantity > 0:
                zone_production[good_code] = zone_production.get(good_code, 0.0) + quantity
                total_output += quantity

                # Add to agent inventory
                try:
                    inv = agent.inventory
                except AgentInventory.DoesNotExist:
                    inv = AgentInventory.objects.create(agent=agent, holdings={}, cash={})

                inv.holdings[good_code] = inv.holdings.get(good_code, 0.0) + quantity
                inv.save(update_fields=["holdings"])

                # Record production transaction
                EconomicLedger.objects.create(
                    simulation=simulation, tick=tick,
                    from_agent=None, to_agent=agent,
                    currency=primary_currency,
                    good_category=good_map.get(good_code),
                    quantity=quantity, unit_price=0.0,
                    total_amount=0.0,
                    transaction_type="production",
                )

            agent_outputs.append({
                "agent_id": agent.id,
                "good_code": good_code,
                "quantity": quantity,
                "owns_property": agent.id in property_owner_ids,
            })

        # === STEP 2: MARKET CLEARING ===
        agent_inventories = []
        for agent in agents:
            try:
                inv = agent.inventory
            except AgentInventory.DoesNotExist:
                continue
            agent_inventories.append({
                "agent_id": agent.id,
                "holdings": dict(inv.holdings),
                "cash_amount": sum(inv.cash.values()),
                "is_hoarding": False,  # hoard action integration in Part 3
            })

        good_dicts = [{"code": g.code, "is_essential": g.is_essential, "price_elasticity": g.price_elasticity} for g in goods]
        total_supply, total_demand, agent_orders = collect_supply_and_demand(
            agent_inventories, good_dicts, old_prices,
        )

        equilibrium_prices, converged = tatonnement_prices(old_prices, total_supply, total_demand)

        # Execute trades
        trades = execute_trades(agent_orders, equilibrium_prices, total_supply, total_demand)

        # Apply trades to inventories
        inv_cache: dict[int, AgentInventory] = {}
        for agent in agents:
            try:
                inv_cache[agent.id] = agent.inventory
            except AgentInventory.DoesNotExist:
                pass

        for trade in trades:
            buyer_inv = inv_cache.get(trade["buyer_id"])
            seller_inv = inv_cache.get(trade["seller_id"])
            if buyer_inv and seller_inv:
                good = trade["good_code"]
                qty = trade["quantity"]
                cost = trade["total"]

                buyer_inv.holdings[good] = buyer_inv.holdings.get(good, 0.0) + qty
                seller_inv.holdings[good] = max(0.0, seller_inv.holdings.get(good, 0.0) - qty)

                cur_code = primary_currency.code
                buyer_inv.cash[cur_code] = buyer_inv.cash.get(cur_code, 0.0) - cost
                seller_inv.cash[cur_code] = seller_inv.cash.get(cur_code, 0.0) + cost

                total_transaction_volume += cost

                EconomicLedger.objects.create(
                    simulation=simulation, tick=tick,
                    from_agent_id=trade["buyer_id"],
                    to_agent_id=trade["seller_id"],
                    currency=primary_currency,
                    good_category=good_map.get(good),
                    quantity=qty, unit_price=trade["price"],
                    total_amount=cost,
                    transaction_type="trade",
                )

        # Save all modified inventories
        for inv in inv_cache.values():
            inv.save(update_fields=["holdings", "cash"])

        # === STEP 3: RENT ===
        prop_dicts = [{"owner_id": p.owner_id, "production_bonus": p.production_bonus} for p in properties if p.owner_type == "agent" and p.owner_id]
        rents = compute_rent(zone_production, prop_dicts, equilibrium_prices)

        for owner_id, rent_amount in rents.items():
            inv = inv_cache.get(owner_id)
            if inv:
                inv.cash[primary_currency.code] = inv.cash.get(primary_currency.code, 0.0) + rent_amount
                inv.save(update_fields=["cash"])
                total_transaction_volume += rent_amount
                EconomicLedger.objects.create(
                    simulation=simulation, tick=tick,
                    from_agent=None, to_agent_id=owner_id,
                    currency=primary_currency,
                    total_amount=rent_amount,
                    transaction_type="rent",
                )

        # === STEP 4: WAGES ===
        wages = compute_wages(agent_outputs, equilibrium_prices, wage_share=wage_share)

        for agent_id, wage_amount in wages.items():
            inv = inv_cache.get(agent_id)
            if inv and wage_amount > 0:
                inv.cash[primary_currency.code] = inv.cash.get(primary_currency.code, 0.0) + wage_amount
                inv.save(update_fields=["cash"])
                total_transaction_volume += wage_amount
                EconomicLedger.objects.create(
                    simulation=simulation, tick=tick,
                    from_agent=None, to_agent_id=agent_id,
                    currency=primary_currency,
                    total_amount=wage_amount,
                    transaction_type="wage",
                )

        # === STEP 5: TAXATION ===
        if tax_policy:
            agent_incomes: dict[int, float] = {}
            for agent_id in set(list(wages.keys()) + list(rents.keys())):
                income = wages.get(agent_id, 0.0) + rents.get(agent_id, 0.0)
                if income > 0:
                    agent_incomes[agent_id] = income

            tax_result = compute_taxes(agent_incomes, tax_policy.income_tax_rate)

            from epocha.apps.world.models import Government
            try:
                gov = Government.objects.get(simulation=simulation)
            except Government.DoesNotExist:
                gov = None

            for agent_id, tax_amount in tax_result["agent_taxes"].items():
                if tax_amount > 0:
                    inv = inv_cache.get(agent_id)
                    if inv:
                        inv.cash[primary_currency.code] = inv.cash.get(primary_currency.code, 0.0) - tax_amount
                        inv.save(update_fields=["cash"])
                        EconomicLedger.objects.create(
                            simulation=simulation, tick=tick,
                            from_agent_id=agent_id, to_agent=None,
                            currency=primary_currency,
                            total_amount=tax_amount,
                            transaction_type="tax",
                        )

            if gov and tax_result["total_revenue"] > 0:
                treasury = gov.government_treasury or {}
                treasury[primary_currency.code] = treasury.get(primary_currency.code, 0.0) + tax_result["total_revenue"]
                gov.government_treasury = treasury
                gov.save(update_fields=["government_treasury"])

        # Update zone prices and write history
        ze.market_prices = equilibrium_prices
        ze.market_supply = total_supply
        ze.market_demand = total_demand
        ze.save(update_fields=["market_prices", "market_supply", "market_demand"])
        new_prices_all.update(equilibrium_prices)

        for good_code, price in equilibrium_prices.items():
            PriceHistory.objects.create(
                zone_economy=ze, good_code=good_code, tick=tick,
                price=price,
                supply=total_supply.get(good_code, 0.0),
                demand=total_demand.get(good_code, 0.0),
            )

        # === STEP 6: ESSENTIAL CONSUMPTION ===
        # Every agent consumes 1 unit of essential goods per tick
        essential_codes = [g.code for g in goods if g.is_essential]
        for agent in agents:
            inv = inv_cache.get(agent.id)
            if inv:
                for code in essential_codes:
                    current = inv.holdings.get(code, 0.0)
                    inv.holdings[code] = max(0.0, current - 1.0)
                inv.save(update_fields=["holdings"])

    # === STEP 6 (global): MONETARY UPDATE ===
    primary_currency.cached_velocity = compute_velocity(
        transaction_volume=total_transaction_volume,
        money_supply=primary_currency.total_supply,
    )
    primary_currency.save(update_fields=["cached_velocity"])

    # === STEP 7: WEALTH + MOOD UPDATE ===
    all_agents = Agent.objects.filter(simulation=simulation, is_alive=True)
    agents_to_update = []

    for agent in all_agents:
        try:
            inv = agent.inventory
        except AgentInventory.DoesNotExist:
            continue

        property_values = list(
            Property.objects.filter(owner=agent, owner_type="agent")
            .values_list("value", flat=True)
        )

        agent.wealth = update_agent_wealth(
            holdings=inv.holdings,
            cash=inv.cash,
            property_values=property_values,
            prices=new_prices_all or old_prices_all,
        )

        mood_delta = compute_mood_delta(agent.wealth)
        agent.mood = max(0.0, min(1.0, agent.mood + mood_delta))

        agents_to_update.append(agent)

    if agents_to_update:
        Agent.objects.bulk_update(agents_to_update, ["wealth", "mood"])

    # Update world stability from inflation and economic state
    inflation = compute_inflation(old_prices_all, new_prices_all)
    try:
        world = simulation.world
        # Stability adjusts based on inflation (Alesina & Perotti 1996)
        # Tunable thresholds, not derived from specific studies
        if abs(inflation) > 0.15:
            world.stability_index = max(0.0, world.stability_index - 0.02)
        elif abs(inflation) < 0.05:
            world.stability_index = min(1.0, world.stability_index + 0.005)
        world.save(update_fields=["stability_index"])
    except Exception:
        pass

    logger.info(
        "Economy tick %d: output=%.1f, trades=%d, volume=%.1f, inflation=%.1f%%",
        tick, total_output, EconomicLedger.objects.filter(simulation=simulation, tick=tick, transaction_type="trade").count(),
        total_transaction_volume, inflation * 100,
    )
```

- [ ] **Step 4: Run engine tests**

Run: `docker compose -f docker-compose.local.yml run --rm web pytest epocha/apps/economy/tests/test_engine.py -v`

Expected: all PASS.

- [ ] **Step 5: Run full suite**

Run: `docker compose -f docker-compose.local.yml run --rm web pytest -q -m "not slow"`

Expected: all tests pass.

- [ ] **Step 6: Commit**

```
feat(economy): add tick pipeline orchestrator wiring all economic steps

CHANGE: Implement the 7-step economy tick pipeline: CES production per
agent, Walrasian market clearing with tatonnement, emergent Ricardian
rent, wage payment, flat tax collection into government treasury,
Fisher velocity update, essential consumption, and wealth/mood/stability
feedback. The pipeline reads from economy models and writes to
AgentInventory, PriceHistory, EconomicLedger, Currency, Government, and
Agent (wealth/mood via bulk_update).
```

---

## Self-Review Summary

After completing Tasks 6-10:

- CES production function with Cobb-Douglas and Leontief limits
- Walrasian tatonnement market clearing with convergence safety
- Emergent Ricardian rent from property production bonuses
- Wage computation with configurable share
- Flat income tax with government treasury
- Fisher velocity as measured quantity (not constant)
- MV=PQ consistency diagnostic
- Inflation computation
- Agent wealth as computed summary (backward compatible)
- Kahneman & Deaton mood satiation curve
- Full 7-step tick pipeline orchestrator

**What remains (Part 3):**
- Economic context in decision engine prompt
- `hoard` action
- Political feedback from economic indicators
- Economy initialization in world generator
- Deprecation of old economy.py
- Engine integration in simulation/engine.py

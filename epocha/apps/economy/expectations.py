"""Adaptive expectations engine based on Nerlove (1958).

Agents form price expectations using adaptive expectations:
    E_new = lambda * P_actual + (1 - lambda) * E_old

where lambda (adaptation speed) is modulated by Big Five personality
traits (Costa & McCrae 1992):
- Neuroticism: higher lambda (overreacts to new price signals)
- Openness: higher lambda (more receptive to change)
- Conscientiousness: lower lambda (more conservative, anchored)

The personality modulation follows a linear deviation model:
    lambda = lambda_base + (N - 0.5) * n_mod + (O - 0.5) * o_mod - (C - 0.5) * c_mod
clamped to [0.05, 0.95] to prevent degenerate behavior (pure naive
or pure static expectations).

References:
- Nerlove, M. (1958). Adaptive Expectations and Cobweb Phenomena.
  Quarterly Journal of Economics 72(2), 227-240.
- Costa, P.T. & McCrae, R.R. (1992). Revised NEO Personality Inventory
  (NEO PI-R) and NEO Five-Factor Inventory (NEO-FFI) Professional Manual.
  Psychological Assessment Resources.
"""

from __future__ import annotations

import logging

from epocha.apps.agents.models import Agent
from epocha.apps.economy.models import AgentExpectation, GoodCategory, ZoneEconomy

logger = logging.getLogger(__name__)

# Hard bounds for lambda to prevent degenerate expectations.
# At 0.05 the agent is almost purely backward-looking (static expectations).
# At 0.95 the agent is almost purely naive (expects last price to repeat).
# These are structural bounds, not tunable parameters.
_LAMBDA_MIN = 0.05
_LAMBDA_MAX = 0.95


def compute_lambda_from_personality(
    personality: dict,
    lambda_base: float,
    n_mod: float,
    o_mod: float,
    c_mod: float,
) -> float:
    """Compute the Nerlove adaptation rate modulated by Big Five traits.

    Each trait contributes a linear deviation from lambda_base centered
    at the population mean of 0.5. The signs follow Costa & McCrae (1992):
    high Neuroticism and Openness increase reactivity; high
    Conscientiousness decreases it.

    Args:
        personality: Agent personality dict with Big Five keys
            (neuroticism, openness, conscientiousness). Missing keys
            default to 0.5 (population mean, no modulation).
        lambda_base: Base adaptation rate before personality modulation.
            Tunable design parameter set per era in the template.
        n_mod: Neuroticism modulation coefficient (positive = increases lambda).
        o_mod: Openness modulation coefficient (positive = increases lambda).
        c_mod: Conscientiousness modulation coefficient (positive = decreases lambda).

    Returns:
        Clamped lambda in [0.05, 0.95].
    """
    neuroticism = personality.get("neuroticism", 0.5)
    openness = personality.get("openness", 0.5)
    conscientiousness = personality.get("conscientiousness", 0.5)

    raw = (
        lambda_base
        + (neuroticism - 0.5) * n_mod
        + (openness - 0.5) * o_mod
        - (conscientiousness - 0.5) * c_mod
    )
    return max(_LAMBDA_MIN, min(_LAMBDA_MAX, raw))


def detect_trend(
    expected: float,
    actual: float,
    threshold: float,
) -> str:
    """Classify the price trend relative to expectations.

    A price is "rising" if the actual price exceeds the expected price
    by more than the threshold fraction, "falling" if it falls short
    by more than the threshold, and "stable" otherwise.

    Args:
        expected: The agent's expected price (previous E).
        actual: The observed market price.
        threshold: Minimum fractional deviation to classify as
            rising/falling. Tunable design parameter.

    Returns:
        One of "rising", "falling", "stable".
    """
    if actual > expected * (1.0 + threshold):
        return "rising"
    if actual < expected * (1.0 - threshold):
        return "falling"
    return "stable"


def update_agent_expectations(simulation, tick: int) -> None:
    """Update price expectations for all agents in the simulation.

    For each living agent, for each good category in the simulation:
    1. Compute the agent's lambda_rate from personality + template config
    2. Get or create the AgentExpectation record
    3. Apply Nerlove adaptive expectations: E_new = lambda * P + (1 - lambda) * E_old
    4. Update trend direction and confidence

    Confidence increases when the agent's expectation was close to the
    actual price (prediction accuracy) and decreases otherwise.
    The confidence adjustment is +/- 0.05 per tick, clamped to [0.0, 1.0].
    These are tunable design parameters.

    This function should be called BEFORE market clearing in the tick
    pipeline, so that agent expectations reflect the previous tick's
    prices and can influence the current tick's trading decisions.

    Requires: ZoneEconomy records with market_prices populated from
    the previous tick.
    """
    # Load expectations config from simulation or use defaults.
    sim_config = simulation.config or {}
    exp_config = sim_config.get("expectations_config", {})
    lambda_base = exp_config.get("lambda_base", 0.3)
    n_mod = exp_config.get("neuroticism_mod", 0.15)
    o_mod = exp_config.get("openness_mod", 0.10)
    c_mod = exp_config.get("conscientiousness_mod", 0.10)
    threshold = exp_config.get("trend_threshold", 0.05)

    goods = list(GoodCategory.objects.filter(simulation=simulation))
    if not goods:
        return

    # Collect actual prices from all zone economies. For multi-zone
    # simulations, each agent uses their own zone's prices. For
    # simplicity in the MVP, we aggregate a single price map from
    # all zones (last-write-wins). Multi-zone price differentiation
    # will be refined in a future iteration.
    zone_economies = list(
        ZoneEconomy.objects.filter(zone__world__simulation=simulation)
    )
    actual_prices: dict[str, float] = {}
    for ze in zone_economies:
        actual_prices.update(ze.market_prices or {})

    if not actual_prices:
        return

    agents = list(Agent.objects.filter(simulation=simulation, is_alive=True))

    # Batch-fetch existing expectations to avoid N+1 queries.
    existing_expectations = {
        (exp.agent_id, exp.good_code): exp
        for exp in AgentExpectation.objects.filter(
            agent__simulation=simulation
        ).select_related("agent")
    }

    to_create: list[AgentExpectation] = []
    to_update: list[AgentExpectation] = []

    for agent in agents:
        personality = agent.personality or {}
        agent_lambda = compute_lambda_from_personality(
            personality,
            lambda_base,
            n_mod,
            o_mod,
            c_mod,
        )

        for good in goods:
            actual_price = actual_prices.get(good.code)
            if actual_price is None:
                continue

            key = (agent.id, good.code)
            existing = existing_expectations.get(key)

            if existing is None:
                # First time: initialize expectation to actual price.
                trend = "stable"
                new_exp = AgentExpectation(
                    agent=agent,
                    good_code=good.code,
                    expected_price=actual_price,
                    trend_direction=trend,
                    confidence=0.5,
                    lambda_rate=agent_lambda,
                    updated_at_tick=tick,
                )
                to_create.append(new_exp)
            else:
                # Nerlove (1958): E_new = lambda * P_actual + (1 - lambda) * E_old
                old_expected = existing.expected_price
                new_expected = (
                    agent_lambda * actual_price + (1.0 - agent_lambda) * old_expected
                )

                trend = detect_trend(old_expected, actual_price, threshold)

                # Confidence adjustment: increases when the prediction
                # was accurate, decreases otherwise. The 0.05 step size
                # is a tunable design parameter.
                prediction_error = abs(actual_price - old_expected)
                if actual_price > 0 and (prediction_error / actual_price) < threshold:
                    confidence_delta = 0.05
                else:
                    confidence_delta = -0.05

                existing.expected_price = new_expected
                existing.trend_direction = trend
                existing.confidence = max(
                    0.0, min(1.0, existing.confidence + confidence_delta)
                )
                existing.lambda_rate = agent_lambda
                existing.updated_at_tick = tick
                to_update.append(existing)

    if to_create:
        AgentExpectation.objects.bulk_create(to_create)

    if to_update:
        AgentExpectation.objects.bulk_update(
            to_update,
            [
                "expected_price",
                "trend_direction",
                "confidence",
                "lambda_rate",
                "updated_at_tick",
            ],
        )

    logger.debug(
        "Expectations tick %d: created=%d, updated=%d",
        tick,
        len(to_create),
        len(to_update),
    )

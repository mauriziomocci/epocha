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

# Mood constants. Tunable design parameters; the qualitative behavior
# (plateau above satiation, penalty below poverty) is from Kahneman &
# Deaton (2010). The specific numeric values are calibrated for the
# simulation's 0-1 mood scale and are not derived from empirical data.
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

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
        ze = ZoneEconomy.objects.get(zone=zone)
    except ZoneEconomy.DoesNotExist:
        return 0.0
    essentials = GoodCategory.objects.filter(simulation=simulation, is_essential=True)
    total = 0.0
    for good in essentials:
        price = ze.market_prices.get(good.code, good.base_price)
        total += price * SUBSISTENCE_NEED_PER_AGENT
    return total


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
    # Government.stability is non-nullable with default=0.5; the only case in
    # which it is unavailable is when the Government record does not exist
    # (economy not initialized), handled by the DoesNotExist branch.
    stability_norm = 0.0
    try:
        gov = Government.objects.get(simulation=agent.simulation)
        stability_norm = 2.0 * float(gov.stability) - 1.0
    except Government.DoesNotExist:
        pass
    return (mood_norm + conf_norm + stability_norm) / 3.0

"""Economic feedback on political stability.

Applies economic indicators (inflation, inequality, treasury balance)
to government stability and legitimacy. These are qualitative effects
grounded in political economy literature but with tunable thresholds
(not empirically calibrated).

References:
- Alesina, A. & Perotti, R. (1996). "Income distribution, political
  instability, and investment." European Economic Review 40(6).
  Finding: high inflation correlates with political instability.
  Implementation: stability penalty when inflation exceeds threshold.

- Acemoglu, D. & Robinson, J. (2006). "Economic Origins of
  Dictatorship and Democracy." Cambridge University Press.
  Finding: extreme inequality undermines democratic legitimacy.
  Implementation: legitimacy penalty when Gini exceeds threshold.

All thresholds are tunable design parameters, not derived from the
papers' quantitative estimates.
"""
from __future__ import annotations

import logging

from epocha.apps.agents.models import Agent
from epocha.apps.world.models import Government
from epocha.apps.world.stratification import compute_gini

from .models import Currency, PriceHistory, ZoneEconomy
from .monetary import compute_inflation

logger = logging.getLogger(__name__)

# -- Tunable design parameters -----------------------------------------------
# These are NOT empirically derived. They are qualitative approximations
# inspired by the cited literature, chosen to produce interesting simulation
# dynamics at the MVP scale (10-30 agents).

# Inflation above this threshold destabilizes the government.
INFLATION_CRISIS_THRESHOLD = 0.15  # tunable design parameter

# Stability penalty per tick when inflation exceeds threshold.
# Alesina & Perotti (1996) find a qualitative correlation; magnitude
# is a tunable design parameter.
INFLATION_STABILITY_PENALTY = 0.02  # tunable design parameter

# Gini coefficient above this threshold erodes popular legitimacy.
GINI_CRISIS_THRESHOLD = 0.6  # tunable design parameter

# Legitimacy penalty per tick when Gini exceeds threshold.
# Acemoglu & Robinson (2006) find a qualitative effect; magnitude
# is a tunable design parameter.
GINI_LEGITIMACY_PENALTY = 0.01  # tunable design parameter

# Stability penalty when government treasury goes negative.
TREASURY_CRISIS_PENALTY = 0.05  # tunable design parameter


def apply_economic_feedback(simulation, tick: int) -> None:
    """Update government indicators based on current economic state.

    Reads inflation from PriceHistory, Gini from agent wealth
    distribution, and treasury balance from Government. Applies
    penalties to stability and popular_legitimacy when thresholds
    are exceeded.

    Safe to call when no government exists (no-op).
    """
    try:
        government = Government.objects.get(simulation=simulation)
    except Government.DoesNotExist:
        return

    changed = False

    # --- Inflation feedback ---
    zone_economies = list(
        ZoneEconomy.objects.filter(zone__world__simulation=simulation)
    )

    if zone_economies and tick > 0:
        # Aggregate prices across all zones for current and previous tick
        old_prices: dict[str, float] = {}
        new_prices: dict[str, float] = {}
        old_count: dict[str, int] = {}
        new_count: dict[str, int] = {}

        for ze in zone_economies:
            for ph in PriceHistory.objects.filter(zone_economy=ze, tick=tick - 1):
                old_prices[ph.good_code] = old_prices.get(ph.good_code, 0.0) + ph.price
                old_count[ph.good_code] = old_count.get(ph.good_code, 0) + 1
            for ph in PriceHistory.objects.filter(zone_economy=ze, tick=tick):
                new_prices[ph.good_code] = new_prices.get(ph.good_code, 0.0) + ph.price
                new_count[ph.good_code] = new_count.get(ph.good_code, 0) + 1

        # Average across zones
        avg_old = {k: v / old_count[k] for k, v in old_prices.items() if old_count.get(k, 0) > 0}
        avg_new = {k: v / new_count[k] for k, v in new_prices.items() if new_count.get(k, 0) > 0}

        inflation = compute_inflation(avg_old, avg_new)

        if abs(inflation) > INFLATION_CRISIS_THRESHOLD:
            government.stability = max(
                0.0, government.stability - INFLATION_STABILITY_PENALTY,
            )
            changed = True
            logger.info(
                "Simulation %d tick %d: inflation %.1f%% exceeds threshold, "
                "stability penalty applied (now %.2f)",
                simulation.id, tick, inflation * 100, government.stability,
            )

    # --- Inequality feedback (Gini) ---
    wealths = list(
        Agent.objects.filter(simulation=simulation, is_alive=True)
        .values_list("wealth", flat=True)
    )
    if len(wealths) >= 2:
        gini = compute_gini(wealths)
        if gini > GINI_CRISIS_THRESHOLD:
            government.popular_legitimacy = max(
                0.0, government.popular_legitimacy - GINI_LEGITIMACY_PENALTY,
            )
            changed = True
            logger.info(
                "Simulation %d tick %d: Gini %.2f exceeds threshold, "
                "legitimacy penalty applied (now %.2f)",
                simulation.id, tick, gini, government.popular_legitimacy,
            )

    # --- Treasury feedback ---
    treasury = government.government_treasury or {}
    total_treasury = sum(treasury.values())
    if total_treasury < 0:
        government.stability = max(
            0.0, government.stability - TREASURY_CRISIS_PENALTY,
        )
        changed = True
        logger.info(
            "Simulation %d tick %d: negative treasury (%.1f), "
            "stability crisis penalty applied (now %.2f)",
            simulation.id, tick, total_treasury, government.stability,
        )

    if changed:
        government.save(update_fields=["stability", "popular_legitimacy"])

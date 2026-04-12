"""Institution health dynamics engine.

Updates the health of each social institution based on the government type's
natural effects and the institution's funding level. Healthy institutions
feed positive government indicators; degraded institutions accelerate decline.

Each tick, institution health evolves according to three additive forces:

1. Government type effect -- the ruling regime's structural tendency to strengthen
   or weaken each institution (e.g. democracies reinforce justice and free media;
   autocracies suppress them). Values come from GOVERNMENT_TYPES["institution_effects"].
   The raw config values are scaled by INSTITUTION_EFFECT_SCALE to convert them
   into per-tick deltas that produce realistic multi-decade trajectories.

2. Funding effect -- underfunded institutions deteriorate regardless of regime type.
   Above the 0.5 neutral funding level, institutions recover; below it, they decline.
   Calibrated so a fully defunded institution (funding=0) loses ~1% health per tick.

3. Entropy -- a small universal linear decay representing the bureaucratic and physical
   degradation all institutions face without active maintenance. Set at 0.5% per tick,
   producing 50% decay from maximum over 100 ticks of zero investment. Besley & Persson
   (2011, ch. 2) discuss state capacity decay; the specific rate is a design parameter.

Scientific grounding:
- Acemoglu & Robinson (2012). "Why Nations Fail." Crown Publishers.
  Inclusive vs extractive institutions as the core driver of national development.
- Besley, T. & Persson, T. (2011). "Pillars of Prosperity." Princeton University Press.
  State capacity decay and institutional investment models.
- The institution_effects values in GOVERNMENT_TYPES are design parameters inspired by
  qualitative patterns in the literature (see government_types.py for full citations).
"""
from __future__ import annotations

import logging

from .government_types import GOVERNMENT_TYPES
from .models import Government, Institution

logger = logging.getLogger(__name__)

# Scale divisor for institutional health effects. At 20.0, a democracy's justice effect
# of 0.30 produces +0.015/tick, reaching near-peak health in ~33 ticks. The timescale
# is a design parameter; it maps to approximately 2-3 years if one tick represents one
# month.
INSTITUTION_EFFECT_SCALE = 20.0

# Funding effect rate. Design parameter controlling how quickly funding levels affect
# institutional health. A funding level of 0.0 produces -0.02/tick; 1.0 produces
# +0.02/tick; 0.5 (neutral) produces 0.0. A severely underfunded institution
# (funding=0.1) in a supportive regime still degrades, because the funding penalty
# (-0.016/tick) exceeds the regime boost (+0.015/tick) plus entropy (-0.005/tick).
# The value 0.04/tick is a simulation design choice without direct empirical derivation.
FUNDING_EFFECT_RATE = 0.04

# Linear entropy: institutions lose 0.005 health per tick without investment. This
# produces 50% decay from maximum after 100 ticks of zero investment. Note: this is
# linear decay, not exponential half-life. Besley & Persson (2011) discuss state
# capacity decay in more general terms; the specific rate is a design parameter.
ENTROPY_PER_TICK = -0.005


def update_institutions(simulation) -> None:
    """Update health of all institutions for one political cycle tick.

    Fetches the current government type, resolves its institution_effects from
    the GOVERNMENT_TYPES config, then applies the three-force model to each
    institution in a single bulk-save loop. Health is clamped to [0.0, 1.0].

    Args:
        simulation: Simulation instance whose institutions are to be updated.

    Note:
        Requires Government and Institution records to exist for the simulation.
        If Government is missing, the function exits silently (no institutions
        can evolve without a governing authority). If a government type is not
        in GOVERNMENT_TYPES, the function exits silently and logs a warning.
    """
    try:
        government = Government.objects.get(simulation=simulation)
    except Government.DoesNotExist:
        logger.debug("No government found for simulation %s; skipping institution update.", simulation.pk)
        return

    type_config = GOVERNMENT_TYPES.get(government.government_type)
    if not type_config:
        logger.warning(
            "Unknown government type %r for simulation %s; skipping institution update.",
            government.government_type,
            simulation.pk,
        )
        return

    effects = type_config["institution_effects"]
    institutions = Institution.objects.filter(simulation=simulation)

    updated_count = 0
    for institution in institutions:
        raw_effect = effects.get(institution.institution_type, 0.0)
        government_effect = raw_effect / INSTITUTION_EFFECT_SCALE
        funding_effect = (institution.funding - 0.5) * FUNDING_EFFECT_RATE
        delta = government_effect + funding_effect + ENTROPY_PER_TICK
        institution.health = max(0.0, min(1.0, institution.health + delta))
        institution.save(update_fields=["health"])
        updated_count += 1

    logger.debug(
        "Updated %d institutions for simulation %s (government_type=%r).",
        updated_count,
        simulation.pk,
        government.government_type,
    )

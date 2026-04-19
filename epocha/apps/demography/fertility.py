"""Fertility model for demography: Hadwiger ASFR modulated by Becker (1991)
economic signals, bounded by a Malthusian soft ceiling.

Sources:
- Hadwiger, H. (1940). Eine analytische Reproduktionsfunktion.
  Skandinavisk Aktuarietidskrift 23, 101-113. Canonical normalization per
  Chandola, Coleman & Hiorns (1999) Population Studies 53(3) and
  Schmertmann (2003) Demographic Research 9.
- Becker, G.S. (1991). A Treatise on the Family. Harvard University Press.
- Malthus-Ricardo preventive check formalization inspired by
  Ashraf & Galor (2011) AER 101(5).
"""
from __future__ import annotations

import math
from typing import Mapping


def hadwiger_asfr(age: float, params: Mapping[str, float]) -> float:
    """Age-specific fertility rate at age a using the canonical Hadwiger form.

    f(a) = (H * T / (R * sqrt(pi))) * (R / a) ** 1.5 *
           exp(-T ** 2 * (R / a + a / R - 2))

    where H is the target total fertility rate (integral of f over fertile ages),
    R is the Hadwiger shape parameter related to peak fertility age, and T
    controls the spread of the distribution.

    Returns 0.0 for ages outside the biologically fertile window [12, 50] and
    for non-positive ages.
    """
    if age <= 0 or age < 12 or age > 50:
        return 0.0
    H = float(params["H"])
    R = float(params["R"])
    T = float(params["T"])
    ratio = R / age
    coef = (H * T) / (R * math.sqrt(math.pi))
    shape = ratio ** 1.5
    tail = math.exp(-(T ** 2) * (ratio + age / R - 2.0))
    return coef * shape * tail


def _female_role_employment_fraction(zone, simulation) -> float:
    """Fraction of adult females in a wage-earning role in the zone.

    Proxy for female labor force participation. Reads the last tick of
    EconomicLedger wage transactions where the recipient is female.
    """
    from epocha.apps.agents.models import Agent
    from epocha.apps.economy.models import EconomicLedger
    from django.db.models import F

    tick = simulation.current_tick
    females = Agent.objects.filter(
        simulation=simulation, zone=zone, is_alive=True, gender=Agent.Gender.FEMALE,
    )
    total = females.count()
    if total == 0:
        return 0.0
    earning_ids = set(
        EconomicLedger.objects.filter(
            simulation=simulation, tick=tick, transaction_type="wage",
            to_agent__in=females,
        ).values_list("to_agent_id", flat=True)
    )
    return len(earning_ids) / total


def _zone_mean_wage(zone, simulation, lookback_ticks: int = 5) -> float:
    """Mean wage in the zone averaged over the last lookback_ticks ticks."""
    from epocha.apps.economy.models import EconomicLedger
    from django.db.models import Avg

    tick = simulation.current_tick
    agg = EconomicLedger.objects.filter(
        simulation=simulation,
        tick__gte=max(0, tick - lookback_ticks),
        transaction_type="wage",
        to_agent__zone=zone,
    ).aggregate(avg_wage=Avg("total_amount"))
    return float(agg["avg_wage"] or 0.0)


def becker_modulation(agent, coeffs: Mapping[str, float]) -> float:
    """Scale baseline ASFR by Becker (1991) economic signals.

    Design inspired by Becker (1991) and Jones & Tertilt (2008). All
    coefficients are provisional seed values; calibration deferred to
    Plan 4 using synthetic shock tests.

    Returns a scaling factor in [0.05, 3.0].
    """
    from epocha.apps.demography.context import (
        compute_subsistence_threshold,
        compute_aggregate_outlook,
    )

    subsistence = compute_subsistence_threshold(agent.simulation, agent.zone)
    wealth_signal = math.log(max(agent.wealth / max(subsistence, 1e-6), 0.1))
    zone_flp = _female_role_employment_fraction(agent.zone, agent.simulation)
    outlook = compute_aggregate_outlook(agent)

    raw = (
        float(coeffs["beta_0"])
        + float(coeffs["beta_1"]) * wealth_signal
        + float(coeffs["beta_2"]) * float(agent.education_level or 0.0)
        + float(coeffs["beta_3"]) * zone_flp
        + float(coeffs["beta_4"]) * outlook
    )
    return max(0.05, min(3.0, math.exp(raw)))


# ---------------------------------------------------------------------------
# Task 3: Malthusian soft ceiling
# ---------------------------------------------------------------------------

def malthusian_soft_ceiling(
    prob: float,
    current_pop: int,
    max_pop: int,
    floor_ratio: float = 0.1,
) -> float:
    """Operational soft-cap on fertility near carrying capacity.

    Engineering heuristic inspired by the Malthusian preventive check
    (Malthus 1798; Ricardo 1817) and by the modern formalization in
    Ashraf & Galor (2011). Not itself the formalization those authors
    propose (which is in continuous time on income per capita); this
    is a discrete tick-based scaling.

    - Free fertility below 80% of cap.
    - Linear ramp-down between 80% and 100% of cap.
    - Floor at floor_ratio * baseline above cap so populations never
      stop reproducing entirely (Lee 1987 empirical floor).
    """
    if max_pop <= 0:
        return prob
    if current_pop < 0.8 * max_pop:
        return prob
    if current_pop < max_pop:
        saturation = (current_pop - 0.8 * max_pop) / (0.2 * max_pop)
        ceiling_factor = max(0.0, 1.0 - saturation)
        return prob * ceiling_factor
    return prob * floor_ratio


# ---------------------------------------------------------------------------
# Task 4: Combined tick_birth_probability
# ---------------------------------------------------------------------------

def tick_birth_probability(
    mother,
    params_era: Mapping[str, object],
    current_pop: int,
    tick_duration_hours: float,
    demography_acceleration: float = 1.0,
) -> float:
    """Compute the per-tick birth probability for a female agent.

    Assumes the caller already filtered for living female agents in the
    fertile age window. Returns 0.0 when the mother is not in an active
    couple (if required by the era) or when avoid_conception is flagged
    for the current tick.

    Scales the annual rate to a single tick using the linear
    approximation for small annual rates (typical for fertility).
    """
    from epocha.apps.demography.models import AgentFertilityState  # noqa: F401
    from epocha.apps.demography.couple import is_in_active_couple

    fertility_cfg = params_era["fertility"]
    require_couple = bool(fertility_cfg.get("require_couple_for_birth", True))
    if require_couple and not is_in_active_couple(mother):
        return 0.0
    if is_avoid_conception_active_this_tick(mother):
        return 0.0

    hadwiger_params = fertility_cfg["hadwiger"]
    annual_asfr = hadwiger_asfr(_effective_age_in_years(
        mother, tick_duration_hours, demography_acceleration,
    ), hadwiger_params)
    if annual_asfr <= 0.0:
        return 0.0
    becker_factor = becker_modulation(mother, fertility_cfg["becker_coefficients"])
    effective = annual_asfr * becker_factor
    effective = malthusian_soft_ceiling(
        effective,
        current_pop,
        int(params_era.get("max_population", 500)),
        float(fertility_cfg.get("malthusian_floor_ratio", 0.1)),
    )
    dt = (tick_duration_hours / 8760.0) * demography_acceleration
    return effective * dt


def _effective_age_in_years(
    agent,
    tick_duration_hours: float,
    demography_acceleration: float,
) -> float:
    """Compute the agent's age in years using birth_tick as canonical source."""
    if agent.birth_tick is None:
        return float(agent.age or 0)
    current_tick = agent.simulation.current_tick if agent.simulation else 0
    ticks_per_year = 8760.0 / tick_duration_hours
    return (current_tick - agent.birth_tick) / max(1e-9, ticks_per_year) * demography_acceleration


# ---------------------------------------------------------------------------
# Task 5: AgentFertilityState helpers
# ---------------------------------------------------------------------------

def set_avoid_conception_flag(agent) -> None:
    """Record the agent's intent to avoid conception this tick.

    The fertility check at tick+1 reads this flag. Tick+1 settlement
    matches the property market pattern from Economy Spec 2.
    """
    from epocha.apps.demography.models import AgentFertilityState

    tick = agent.simulation.current_tick
    state, _ = AgentFertilityState.objects.get_or_create(agent=agent)
    state.avoid_conception_flag_tick = tick
    state.save(update_fields=["avoid_conception_flag_tick"])


def is_avoid_conception_active_this_tick(agent) -> bool:
    """True when the agent flagged avoid_conception at the previous tick.

    Reading the flag set at tick T - 1 during tick T makes avoid_conception
    a tick+1-settled action, consistent with property-market semantics.
    """
    from epocha.apps.demography.models import AgentFertilityState

    try:
        state = agent.fertility_state
    except AgentFertilityState.DoesNotExist:
        return False
    if state.avoid_conception_flag_tick is None:
        return False
    return state.avoid_conception_flag_tick == agent.simulation.current_tick - 1


# ---------------------------------------------------------------------------
# Task 6: Joint mortality-fertility resolution
# ---------------------------------------------------------------------------

def resolve_childbirth_event(
    mother,
    params_era: Mapping[str, object],
    tick: int,
    rng,
) -> dict:
    """Resolve a pending birth alongside childbirth mortality.

    Returns a dict describing the outcome:
        {
            "mother_died": bool,
            "newborn_survived": bool,
            "death_cause": str | None,
        }

    Callers are responsible for persisting the state changes (mother's
    death, newborn creation) based on the outcome; this helper is a
    pure probabilistic resolver to keep the mortality path and the
    fertility path coupled but side-effect free.
    """
    mortality_cfg = params_era["mortality"]
    maternal_death_rate = float(
        mortality_cfg.get("maternal_mortality_rate_per_birth", 0.0)
    )
    neonatal_survival_when_mother_dies = float(
        mortality_cfg.get("neonatal_survival_when_mother_dies", 0.3)
    )

    mother_died = rng.random() < maternal_death_rate
    if mother_died:
        newborn_survived = rng.random() < neonatal_survival_when_mother_dies
        return {
            "mother_died": True,
            "newborn_survived": newborn_survived,
            "death_cause": "childbirth",
        }
    return {
        "mother_died": False,
        "newborn_survived": True,
        "death_cause": None,
    }

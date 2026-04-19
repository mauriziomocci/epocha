"""Unit tests for epocha/apps/demography/fertility.py.

Covers:
- hadwiger_asfr: boundary conditions, peak location, integral normalization
- becker_modulation: sign and zero-coefficient cases
- malthusian_soft_ceiling: all three branches (free, ramp-down, floor)
- tick_birth_probability: zero returns for no-couple and avoid-conception
- set_avoid_conception_flag / is_avoid_conception_active_this_tick: flag persistence
  and tick+1 settlement semantics
- resolve_childbirth_event: deterministic outcomes under seeded RNG
"""
from __future__ import annotations

import math
import random
import sys
import types
from unittest.mock import patch

import pytest
from django.contrib.gis.geos import Point, Polygon

from epocha.apps.agents.models import Agent
from epocha.apps.demography.fertility import (
    hadwiger_asfr,
    is_avoid_conception_active_this_tick,
    malthusian_soft_ceiling,
    resolve_childbirth_event,
    set_avoid_conception_flag,
)
from epocha.apps.demography.models import AgentFertilityState
from epocha.apps.economy.models import BankingState, GoodCategory, ZoneEconomy
from epocha.apps.simulation.models import Simulation
from epocha.apps.users.models import User
from epocha.apps.world.models import Government, World, Zone


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sim_with_zone(db):
    """Minimal scaffolding: user, simulation, world, zone."""
    user = User.objects.create_user(
        email="fertility@epocha.dev", username="fertilityuser", password="pass1234",
    )
    sim = Simulation.objects.create(
        name="FertilityTest", seed=42, owner=user, current_tick=0,
    )
    world = World.objects.create(simulation=sim, stability_index=0.7)
    zone = Zone.objects.create(
        world=world,
        name="FertZone",
        zone_type="commercial",
        boundary=Polygon.from_bbox((0, 0, 100, 100)),
        center=Point(50, 50),
    )
    return sim, zone


@pytest.fixture
def female_agent(sim_with_zone):
    """A living female agent aged 26 in the fertile window."""
    sim, zone = sim_with_zone
    agent = Agent.objects.create(
        simulation=sim,
        name="Femina",
        role="farmer",
        zone=zone,
        location=Point(50, 50),
        gender=Agent.Gender.FEMALE,
        health=1.0,
        wealth=200.0,
        age=26,
        birth_tick=0,
        mood=0.5,
        education_level=0.3,
        social_class="working",
    )
    return agent, sim, zone


# ---------------------------------------------------------------------------
# Pre-industrial Hadwiger parameters used across multiple tests.
# H=5.0, R=26, T=3.5 — corrected from Plan 1 templates (T was 0.35).
# Peak value at R=26 with T=3.5: H*T/(R*sqrt(pi)) = 5.0*3.5/(26*sqrt(pi)) ~= 0.379.
# Source: Chandola, Coleman & Hiorns (1999) Population Studies 53(3).
# ---------------------------------------------------------------------------
PRE_INDUSTRIAL_HADWIGER = {"H": 5.0, "R": 26, "T": 3.5}


# ---------------------------------------------------------------------------
# hadwiger_asfr
# ---------------------------------------------------------------------------


def test_hadwiger_asfr_below_12_returns_zero():
    """Ages below the biological fertile minimum must return 0.0."""
    assert hadwiger_asfr(11.9, PRE_INDUSTRIAL_HADWIGER) == 0.0
    assert hadwiger_asfr(0, PRE_INDUSTRIAL_HADWIGER) == 0.0
    assert hadwiger_asfr(-5.0, PRE_INDUSTRIAL_HADWIGER) == 0.0


def test_hadwiger_asfr_above_50_returns_zero():
    """Ages above the biological fertile maximum must return 0.0."""
    assert hadwiger_asfr(50.1, PRE_INDUSTRIAL_HADWIGER) == 0.0
    assert hadwiger_asfr(80.0, PRE_INDUSTRIAL_HADWIGER) == 0.0


def test_hadwiger_asfr_exactly_at_boundaries():
    """Boundary ages 12 and 50 are included in the fertile window."""
    assert hadwiger_asfr(12.0, PRE_INDUSTRIAL_HADWIGER) > 0.0
    assert hadwiger_asfr(50.0, PRE_INDUSTRIAL_HADWIGER) > 0.0


def test_hadwiger_asfr_peak_near_R():
    """The ASFR peak for H=5, R=26, T=3.5 must fall in the range [24, 28].

    The Hadwiger mode is slightly below R for typical T values; empirically
    for T=3.5 and R=26 the mode lands between 24 and 28 years.
    """
    rates = {age: hadwiger_asfr(float(age), PRE_INDUSTRIAL_HADWIGER) for age in range(14, 51)}
    peak_age = max(rates, key=rates.__getitem__)
    assert 24 <= peak_age <= 28, f"Expected peak in [24, 28], got {peak_age}"


def test_hadwiger_asfr_peak_value_approximate():
    """The Hadwiger peak for H=5.0, R=26, T=3.5 should be near 0.38.

    Theoretical peak coef = H*T/(R*sqrt(pi)) = 5.0*3.5/(26*sqrt(pi)) ~= 0.3792.
    The actual peak is close but can be slightly lower due to the shape and tail
    terms not evaluating to exactly 1 at age=R. Accept ±15%.
    """
    peak = hadwiger_asfr(26.0, PRE_INDUSTRIAL_HADWIGER)
    assert 0.30 <= peak <= 0.45, f"Expected peak ~0.38, got {peak:.4f}"


def test_hadwiger_asfr_integral_within_15pct_of_H():
    """Trapezoidal integral over [12, 50] should be within 15% of H=5.0.

    Canonical Hadwiger normalization ensures the integral over all fertile ages
    equals H (total fertility rate). The interval [12, 50] captures >99% of the
    mass for T=3.5, R=26.

    Source: Schmertmann (2003) Demographic Research 9, equation (1) and
    Chandola, Coleman & Hiorns (1999) Population Studies 53(3).
    """
    H = PRE_INDUSTRIAL_HADWIGER["H"]
    ages = [12 + i * 0.1 for i in range(0, 381)]  # step 0.1 years
    rates = [hadwiger_asfr(a, PRE_INDUSTRIAL_HADWIGER) for a in ages]
    integral = sum(
        0.5 * (rates[i] + rates[i + 1]) * 0.1 for i in range(len(rates) - 1)
    )
    assert abs(integral - H) / H < 0.15, (
        f"Integral {integral:.3f} deviates from H={H} by more than 15%"
    )


# ---------------------------------------------------------------------------
# becker_modulation
# ---------------------------------------------------------------------------


@pytest.fixture
def _full_db_for_becker(sim_with_zone):
    """Add ZoneEconomy + GoodCategory + Government + BankingState so the
    context helpers return finite values for becker_modulation tests."""
    from epocha.apps.economy.models import BankingState, GoodCategory, ZoneEconomy
    from epocha.apps.world.models import Government

    sim, zone = sim_with_zone
    GoodCategory.objects.create(
        simulation=sim,
        code="FOOD",
        name="Food",
        is_essential=True,
        base_price=10.0,
        price_elasticity=0.3,
    )
    ZoneEconomy.objects.create(zone=zone, market_prices={"FOOD": 10.0})
    BankingState.objects.create(
        simulation=sim,
        reserve_ratio=0.1,
        base_interest_rate=0.05,
        confidence_index=0.5,
    )
    Government.objects.create(simulation=sim, stability=0.5)
    return sim, zone


@pytest.mark.django_db
def test_becker_modulation_zero_coefficients(_full_db_for_becker):
    """All-zero coefficients: raw = 0 -> exp(0) = 1.0 -> scale factor 1.0."""
    from epocha.apps.demography.fertility import becker_modulation

    sim, zone = _full_db_for_becker
    agent = Agent.objects.create(
        simulation=sim, name="Neutral", role="farmer",
        zone=zone, location=Point(50, 50),
        gender=Agent.Gender.FEMALE, health=1.0, wealth=100.0,
        age=25, birth_tick=0, mood=0.5, education_level=0.5,
    )
    zero_coeffs = {"beta_0": 0.0, "beta_1": 0.0, "beta_2": 0.0, "beta_3": 0.0, "beta_4": 0.0}
    result = becker_modulation(agent, zero_coeffs)
    assert result == pytest.approx(1.0, abs=1e-6)


@pytest.mark.django_db
def test_becker_modulation_high_wealth_positive_beta1(_full_db_for_becker):
    """High wealth (well above subsistence) with positive beta_1 should produce > 1.0."""
    from epocha.apps.demography.fertility import becker_modulation

    sim, zone = _full_db_for_becker
    rich_agent = Agent.objects.create(
        simulation=sim, name="Rich", role="merchant",
        zone=zone, location=Point(50, 50),
        gender=Agent.Gender.FEMALE, health=1.0, wealth=10000.0,
        age=25, birth_tick=0, mood=0.5, education_level=0.3,
    )
    coeffs = {"beta_0": 0.0, "beta_1": 0.3, "beta_2": 0.0, "beta_3": 0.0, "beta_4": 0.0}
    result = becker_modulation(rich_agent, coeffs)
    assert result > 1.0, f"Expected > 1.0 for high wealth, got {result}"


@pytest.mark.django_db
def test_becker_modulation_low_wealth_positive_beta1(_full_db_for_becker):
    """Near-zero wealth with positive beta_1 should produce a small factor < 1.0."""
    from epocha.apps.demography.fertility import becker_modulation

    sim, zone = _full_db_for_becker
    poor_agent = Agent.objects.create(
        simulation=sim, name="Poor", role="servant",
        zone=zone, location=Point(50, 50),
        gender=Agent.Gender.FEMALE, health=1.0, wealth=0.01,
        age=25, birth_tick=0, mood=0.5, education_level=0.3,
    )
    coeffs = {"beta_0": 0.0, "beta_1": 0.3, "beta_2": 0.0, "beta_3": 0.0, "beta_4": 0.0}
    result = becker_modulation(poor_agent, coeffs)
    assert result < 1.0, f"Expected < 1.0 for low wealth, got {result}"


# ---------------------------------------------------------------------------
# malthusian_soft_ceiling
# ---------------------------------------------------------------------------


def test_malthusian_ceiling_below_80pct_unchanged():
    """Population below 80% of max_pop: fertility returned unchanged."""
    prob = 0.05
    result = malthusian_soft_ceiling(prob, current_pop=60, max_pop=100)
    assert result == pytest.approx(prob)


def test_malthusian_ceiling_at_exactly_80pct_unchanged():
    """Population exactly at the 80% threshold is still in the free zone."""
    prob = 0.05
    result = malthusian_soft_ceiling(prob, current_pop=80, max_pop=100)
    assert result == pytest.approx(prob)


def test_malthusian_ceiling_ramp_at_90pct():
    """Population at 90% of max: saturation=0.5, ceiling_factor=0.5, so result=prob*0.5."""
    prob = 0.05
    # saturation = (90 - 80) / 20 = 0.5; ceiling_factor = 0.5
    result = malthusian_soft_ceiling(prob, current_pop=90, max_pop=100)
    assert result == pytest.approx(prob * 0.5)


def test_malthusian_ceiling_at_100pct():
    """Population exactly at 100% of max_pop: returns prob * floor_ratio."""
    prob = 0.05
    floor_ratio = 0.1
    result = malthusian_soft_ceiling(prob, current_pop=100, max_pop=100, floor_ratio=floor_ratio)
    assert result == pytest.approx(prob * floor_ratio)


def test_malthusian_ceiling_above_cap():
    """Population exceeding max_pop: floor is applied (no full zeroing)."""
    prob = 0.05
    floor_ratio = 0.1
    result = malthusian_soft_ceiling(prob, current_pop=150, max_pop=100, floor_ratio=floor_ratio)
    assert result == pytest.approx(prob * floor_ratio)


def test_malthusian_ceiling_zero_max_pop():
    """max_pop <= 0 is a degenerate case: returns prob unchanged."""
    prob = 0.05
    assert malthusian_soft_ceiling(prob, current_pop=10, max_pop=0) == pytest.approx(prob)


# ---------------------------------------------------------------------------
# tick_birth_probability
# ---------------------------------------------------------------------------

# Minimal era params dict sufficient for tick_birth_probability.
# require_couple_for_birth=True so the no-couple path is tested.
_ERA_PARAMS_WITH_COUPLE_REQUIRED = {
    "fertility": {
        "require_couple_for_birth": True,
        "hadwiger": PRE_INDUSTRIAL_HADWIGER,
        "becker_coefficients": {
            "beta_0": 0.0,
            "beta_1": 0.0,
            "beta_2": 0.0,
            "beta_3": 0.0,
            "beta_4": 0.0,
        },
        "malthusian_floor_ratio": 0.1,
    },
    "max_population": 500,
    "mortality": {},
}


def _inject_couple_stub(return_value: bool):
    """Inject a dummy epocha.apps.demography.couple module into sys.modules if it
    does not exist yet (Task 8 creates the real module). This allows patching
    is_in_active_couple without depending on Task 8 being complete.

    The context manager yields and then restores the previous sys.modules state.
    """
    import contextlib

    @contextlib.contextmanager
    def _ctx():
        couple_key = "epocha.apps.demography.couple"
        preexisting = sys.modules.get(couple_key)
        if preexisting is None:
            stub = types.ModuleType(couple_key)
            stub.is_in_active_couple = lambda _agent: return_value
            sys.modules[couple_key] = stub
            try:
                yield stub
            finally:
                del sys.modules[couple_key]
        else:
            # Module already present: patch its attribute via unittest.mock
            with patch(f"{couple_key}.is_in_active_couple", return_value=return_value):
                yield preexisting

    return _ctx()


@pytest.mark.django_db
def test_tick_birth_probability_no_couple_returns_zero(female_agent):
    """When require_couple_for_birth=True and no active couple exists, result is 0.0.

    is_in_active_couple is stubbed to return False so this test does not depend
    on the couple module being present (Task 8 creates it).
    """
    from epocha.apps.demography import fertility as fertility_mod

    agent, sim, zone = female_agent
    # Set a plausible birth_tick so effective age puts the agent in the fertile window
    agent.birth_tick = sim.current_tick - 26 * 876  # ~26 years at 10h/tick
    agent.save()

    with _inject_couple_stub(return_value=False):
        # Force fertility module to re-import couple with the stub in place
        import importlib
        importlib.reload(fertility_mod)
        result = fertility_mod.tick_birth_probability(
            agent,
            _ERA_PARAMS_WITH_COUPLE_REQUIRED,
            current_pop=50,
            tick_duration_hours=10.0,
            demography_acceleration=1.0,
        )
    assert result == 0.0


@pytest.mark.django_db
def test_tick_birth_probability_avoid_conception_returns_zero(female_agent):
    """Returns 0.0 when the avoid_conception flag was set at the previous tick.

    Sequence:
    - current_tick=0: set flag (flag_tick=0)
    - current_tick=1: is_avoid_conception_active_this_tick returns True -> prob=0.0

    is_in_active_couple is stubbed True so the couple check is not the blocker.
    """
    from epocha.apps.demography import fertility as fertility_mod

    agent, sim, zone = female_agent
    # Tick 0: set the flag
    sim.current_tick = 0
    sim.save()
    set_avoid_conception_flag(agent)

    # Tick 1: check that probability is zero
    sim.current_tick = 1
    sim.save()
    # Refresh agent so it picks up the updated simulation tick
    agent.refresh_from_db()

    with _inject_couple_stub(return_value=True):
        import importlib
        importlib.reload(fertility_mod)
        result = fertility_mod.tick_birth_probability(
            agent,
            _ERA_PARAMS_WITH_COUPLE_REQUIRED,
            current_pop=50,
            tick_duration_hours=10.0,
            demography_acceleration=1.0,
        )
    assert result == 0.0


# ---------------------------------------------------------------------------
# set_avoid_conception_flag / is_avoid_conception_active_this_tick
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_set_avoid_conception_flag_persists(female_agent):
    """set_avoid_conception_flag stores avoid_conception_flag_tick == current_tick."""
    agent, sim, zone = female_agent
    sim.current_tick = 7
    sim.save()
    set_avoid_conception_flag(agent)
    state = AgentFertilityState.objects.get(agent=agent)
    assert state.avoid_conception_flag_tick == 7


@pytest.mark.django_db
def test_set_avoid_conception_flag_idempotent(female_agent):
    """Calling set_avoid_conception_flag twice at the same tick is idempotent."""
    agent, sim, zone = female_agent
    sim.current_tick = 3
    sim.save()
    set_avoid_conception_flag(agent)
    set_avoid_conception_flag(agent)
    assert AgentFertilityState.objects.filter(agent=agent).count() == 1


@pytest.mark.django_db
def test_is_avoid_conception_active_true_at_tick_plus_1(female_agent):
    """Flag set at tick T is active at tick T+1 (tick+1 settlement semantics)."""
    agent, sim, zone = female_agent
    # Tick 0: set flag
    sim.current_tick = 0
    sim.save()
    set_avoid_conception_flag(agent)
    # Tick 1: flag should be active
    sim.current_tick = 1
    sim.save()
    assert is_avoid_conception_active_this_tick(agent) is True


@pytest.mark.django_db
def test_is_avoid_conception_inactive_at_tick_plus_2(female_agent):
    """Flag set at tick T is no longer active at tick T+2 (single-tick window)."""
    agent, sim, zone = female_agent
    sim.current_tick = 0
    sim.save()
    set_avoid_conception_flag(agent)
    sim.current_tick = 2
    sim.save()
    assert is_avoid_conception_active_this_tick(agent) is False


@pytest.mark.django_db
def test_is_avoid_conception_inactive_when_no_state(female_agent):
    """Returns False when no AgentFertilityState row exists."""
    agent, sim, zone = female_agent
    # Ensure no state row exists
    AgentFertilityState.objects.filter(agent=agent).delete()
    assert is_avoid_conception_active_this_tick(agent) is False


# ---------------------------------------------------------------------------
# resolve_childbirth_event
# ---------------------------------------------------------------------------

_ERA_PARAMS_HIGH_MATERNAL_MORTALITY = {
    "fertility": {},
    "mortality": {
        "maternal_mortality_rate_per_birth": 1.0,
        "neonatal_survival_when_mother_dies": 0.3,
    },
}

_ERA_PARAMS_ZERO_MATERNAL_MORTALITY = {
    "fertility": {},
    "mortality": {
        "maternal_mortality_rate_per_birth": 0.0,
        "neonatal_survival_when_mother_dies": 0.3,
    },
}


def test_resolve_childbirth_event_certain_death():
    """maternal_mortality_rate=1.0 -> mother_died=True, deterministically."""
    rng = random.Random(42)
    # With maternal_death_rate=1.0, rng.random() < 1.0 is always True.
    result = resolve_childbirth_event(
        mother=None,
        params_era=_ERA_PARAMS_HIGH_MATERNAL_MORTALITY,
        tick=5,
        rng=rng,
    )
    assert result["mother_died"] is True
    assert result["death_cause"] == "childbirth"
    assert "newborn_survived" in result


def test_resolve_childbirth_event_certain_survival():
    """maternal_mortality_rate=0.0 -> mother_died=False, newborn_survived=True."""
    rng = random.Random(99)
    result = resolve_childbirth_event(
        mother=None,
        params_era=_ERA_PARAMS_ZERO_MATERNAL_MORTALITY,
        tick=5,
        rng=rng,
    )
    assert result["mother_died"] is False
    assert result["newborn_survived"] is True
    assert result["death_cause"] is None


def test_resolve_childbirth_event_reproducible():
    """Two calls with the same seeded RNG must produce identical outcomes."""
    params = {
        "fertility": {},
        "mortality": {
            "maternal_mortality_rate_per_birth": 0.2,
            "neonatal_survival_when_mother_dies": 0.5,
        },
    }
    rng_a = random.Random(7)
    rng_b = random.Random(7)
    result_a = resolve_childbirth_event(None, params, tick=1, rng=rng_a)
    result_b = resolve_childbirth_event(None, params, tick=1, rng=rng_b)
    assert result_a == result_b


def test_resolve_childbirth_event_keys_always_present():
    """The returned dict always contains all three keys regardless of outcome."""
    for seed in range(10):
        params = {
            "fertility": {},
            "mortality": {
                "maternal_mortality_rate_per_birth": 0.5,
                "neonatal_survival_when_mother_dies": 0.5,
            },
        }
        result = resolve_childbirth_event(None, params, tick=0, rng=random.Random(seed))
        assert "mother_died" in result
        assert "newborn_survived" in result
        assert "death_cause" in result

"""End-to-end integration test for Demography Plan 2.

Covers the full cycle pair_bond -> avoid_conception -> separate with
deterministic state-transition assertions at each step.

The modern_democracy template is used throughout because it has:
  fertility_agency="planned"  -> avoid_conception action is available
  divorce_enabled=true        -> separate action is available
  require_couple_for_birth=false -> tick_birth_probability is not gated by
      couple presence (the template is secular/planned); the test still
      exercises the avoid_conception gate and the fertile-age gate.

No stochastic draws are made. The test asserts properties:
  tick_birth_probability == 0.0  when the flag is active
  tick_birth_probability > 0.0   when the flag is stale and agent is fertile
"""
from __future__ import annotations

import json

import pytest
from django.contrib.gis.geos import Point, Polygon

from epocha.apps.agents.models import Agent, DecisionLog
from epocha.apps.demography.couple import (
    active_couple_for,
    is_in_active_couple,
    resolve_pair_bond_intents,
    resolve_separate_intents,
)
from epocha.apps.demography.fertility import (
    is_avoid_conception_active_this_tick,
    set_avoid_conception_flag,
    tick_birth_probability,
)
from epocha.apps.demography.models import AgentFertilityState
from epocha.apps.demography.template_loader import load_template
from epocha.apps.economy.models import GoodCategory, ZoneEconomy
from epocha.apps.simulation.models import Simulation
from epocha.apps.users.models import User
from epocha.apps.world.models import Government, World, Zone


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Tick anchor.  All relative tick offsets in the test use T as origin.
T = 10

# Ticks per year expressed in hours.  One tick = 24 hours.  Used both to
# configure the tick_birth_probability call and to set birth_tick so that
# _effective_age_in_years resolves to ~28 years at tick T.
TICK_DURATION_HOURS = 24.0
TICKS_PER_YEAR = 8760.0 / TICK_DURATION_HOURS  # 365 ticks/year


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def setup(db):
    """Create the full simulation scaffold for Plan 2 integration tests.

    Returns (sim, zone, A, B, C, D, template) where A/B are female and C/D
    are male, all in the fertile age window (approx 28 years old based on
    birth_tick), created in strict order so PKs are monotonic A<B<C<D.
    """
    # -- User and simulation --
    user = User.objects.create_user(
        email="integration2@epocha.dev",
        username="integ2user",
        password="pass1234",
    )
    sim = Simulation.objects.create(
        name="Plan2IntegrationTest",
        seed=99,
        owner=user,
        current_tick=T,
        config={"demography_template": "modern_democracy"},
    )

    # -- World and zone --
    world = World.objects.create(simulation=sim, stability_index=0.8)
    zone = Zone.objects.create(
        world=world,
        name="IntegZone",
        zone_type="commercial",
        boundary=Polygon.from_bbox((0, 0, 100, 100)),
        center=Point(50, 50),
    )

    # -- ZoneEconomy: required by compute_subsistence_threshold --
    ZoneEconomy.objects.create(
        zone=zone,
        market_prices={"food": 1.0},
        market_supply={"food": 100.0},
        market_demand={"food": 80.0},
    )

    # -- GoodCategory: at least one essential good so subsistence threshold
    # is non-zero (and becker_modulation wealth_signal is finite).
    GoodCategory.objects.create(
        simulation=sim,
        code="food",
        name="Food",
        is_essential=True,
        base_price=1.0,
        price_elasticity=0.3,
    )

    # -- Government: required by compute_aggregate_outlook --
    Government.objects.create(
        simulation=sim,
        government_type="democracy",
        stability=0.7,
        institutional_trust=0.6,
    )

    # -- Agents: created in insertion order to guarantee monotonic PKs.
    # birth_tick is set so that at tick T the effective age is ~28 years,
    # squarely in the fertile window for modern_democracy (H=1.8, R=30).
    # birth_tick = T - 28 * TICKS_PER_YEAR = T - 10220.  We use a negative
    # value which is legal (PositiveIntegerField allows 0 but in practice
    # the Django ORM accepts negative Python int; to stay safe, we pin
    # birth_tick=0 and set age=28 so _effective_age_in_years falls back to
    # agent.age when birth_tick==0 would give wrong age.
    # _effective_age_in_years: if birth_tick is None -> uses agent.age; if
    # birth_tick is set -> uses (current_tick - birth_tick)/ticks_per_year.
    # We use birth_tick=None and age=28 as the canonical approach: simpler
    # and deterministic.
    agent_defaults = dict(
        simulation=sim,
        zone=zone,
        location=Point(50, 50),
        health=1.0,
        wealth=200.0,
        mood=0.6,
        education_level=0.5,
        social_class="middle",
        is_alive=True,
        birth_tick=None,
        age=28,
    )
    # FEMALE A — created first, so A.pk < B.pk < C.pk < D.pk
    A = Agent.objects.create(
        name="AgentA_female",
        role="teacher",
        gender=Agent.Gender.FEMALE,
        **agent_defaults,
    )
    # FEMALE B
    B = Agent.objects.create(
        name="AgentB_female",
        role="nurse",
        gender=Agent.Gender.FEMALE,
        **agent_defaults,
    )
    # MALE C
    C = Agent.objects.create(
        name="AgentC_male",
        role="engineer",
        gender=Agent.Gender.MALE,
        **agent_defaults,
    )
    # MALE D
    D = Agent.objects.create(
        name="AgentD_male",
        role="farmer",
        gender=Agent.Gender.MALE,
        **agent_defaults,
    )

    # Verify monotonic PK ordering as required by the plan.
    assert A.pk < B.pk < C.pk < D.pk, (
        "Agent PK ordering violated; creation order must be A, B, C, D"
    )

    template = load_template("modern_democracy")
    return sim, zone, A, B, C, D, template


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _make_decision_log(sim, agent, tick, action, target=None, reason="integration test"):
    """Create a DecisionLog row matching the engine output format."""
    payload = {"action": action, "reason": reason}
    if target is not None:
        payload["target"] = target
    return DecisionLog.objects.create(
        simulation=sim,
        agent=agent,
        tick=tick,
        input_context="(integration-test)",
        output_decision=json.dumps(payload),
        llm_model="test",
        cost_tokens=0,
    )


# ---------------------------------------------------------------------------
# Integration test
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_full_pair_bond_avoid_conception_separate_cycle(setup):
    """Full deterministic cycle: pair_bond -> avoid_conception -> separate.

    Steps follow plan Task 22 exactly.  No stochastic draw is made; only
    property assertions (== 0.0 or > 0.0) are used for tick_birth_probability.
    """
    import random

    sim, zone, A, B, C, D, template = setup

    # Dummy RNG for resolvers (pair_bond resolver does not actually use it
    # but the signature requires one).
    rng = random.Random(42)

    # -----------------------------------------------------------------
    # Step 1: precondition — no couple exists for A or C yet
    # -----------------------------------------------------------------
    assert not is_in_active_couple(A), "A must not be in a couple before the test"
    assert not is_in_active_couple(C), "C must not be in a couple before the test"

    # -----------------------------------------------------------------
    # Step 2: verify agents are in the fertile window.
    # modern_democracy: H=1.8, R=30, T=4.2, fertile ages [12, 50].
    # age=28 is well inside the window.
    # The template has require_couple_for_birth=false, so a bare A (no
    # couple) already has tick_birth_probability > 0 at age 28.
    # We verify this baseline to confirm the context is wired correctly.
    # -----------------------------------------------------------------
    sim.current_tick = T
    sim.save(update_fields=["current_tick"])
    A.refresh_from_db()
    baseline_prob = tick_birth_probability(
        A,
        template,
        current_pop=4,
        tick_duration_hours=TICK_DURATION_HOURS,
    )
    assert baseline_prob > 0.0, (
        "Baseline tick_birth_probability must be > 0 for fertile female A "
        "with no active avoid_conception flag and no couple requirement. "
        f"Got {baseline_prob!r}. Check that ZoneEconomy and GoodCategory "
        "are set up and that becker_modulation returns a finite positive factor."
    )

    # -----------------------------------------------------------------
    # Step 3: create pair_bond DecisionLog entries at tick T for A and C
    # (mutual consent so resolve_pair_bond_intents forms the couple regardless
    # of implicit_mutual_consent value).
    # -----------------------------------------------------------------
    _make_decision_log(sim, A, T, "pair_bond", target="AgentC_male")
    _make_decision_log(sim, C, T, "pair_bond", target="AgentA_female")

    # -----------------------------------------------------------------
    # Step 4: advance to T+1 and resolve pair_bond intents
    # -----------------------------------------------------------------
    sim.current_tick = T + 1
    sim.save(update_fields=["current_tick"])

    formed = resolve_pair_bond_intents(simulation=sim, tick=T + 1, rng=rng)
    assert len(formed) == 1, (
        f"Expected exactly one Couple to form, got {len(formed)}: {formed}"
    )
    couple = formed[0]
    # Canonical ordering: lower-PK agent must be agent_a.
    # A.pk < C.pk, so agent_a must be A.
    assert couple.agent_a_id == A.pk, (
        f"Expected agent_a to be A (pk={A.pk}), got {couple.agent_a_id}"
    )
    assert couple.agent_b_id == C.pk, (
        f"Expected agent_b to be C (pk={C.pk}), got {couple.agent_b_id}"
    )
    assert couple.formed_at_tick == T + 1

    # -----------------------------------------------------------------
    # Step 5: assert both partners are now in an active couple
    # -----------------------------------------------------------------
    assert is_in_active_couple(A), "A must be in an active couple after pair_bond resolved"
    assert is_in_active_couple(C), "C must be in an active couple after pair_bond resolved"
    assert active_couple_for(A) is not None
    assert active_couple_for(C) is not None

    # -----------------------------------------------------------------
    # Step 6: at tick T+2, set avoid_conception flag for A (simulating the
    # action handler that calls set_avoid_conception_flag).
    # -----------------------------------------------------------------
    sim.current_tick = T + 2
    sim.save(update_fields=["current_tick"])
    A.refresh_from_db()
    set_avoid_conception_flag(A)

    # Verify the flag was persisted at the current tick T+2.
    A.refresh_from_db()
    fertility_state = AgentFertilityState.objects.get(agent=A)
    assert fertility_state.avoid_conception_flag_tick == T + 2, (
        f"Expected flag_tick={T + 2}, got {fertility_state.avoid_conception_flag_tick}"
    )

    # -----------------------------------------------------------------
    # Step 7: advance to T+3; the flag was set at T+2 so
    # is_avoid_conception_active_this_tick is True (flag_tick == current_tick - 1).
    # tick_birth_probability must return 0.0.
    # -----------------------------------------------------------------
    sim.current_tick = T + 3
    sim.save(update_fields=["current_tick"])
    A.refresh_from_db()

    assert is_avoid_conception_active_this_tick(A), (
        "is_avoid_conception_active_this_tick must be True at T+3 when flag set at T+2"
    )
    prob_with_flag = tick_birth_probability(
        A,
        template,
        current_pop=4,
        tick_duration_hours=TICK_DURATION_HOURS,
    )
    assert prob_with_flag == 0.0, (
        f"tick_birth_probability must be 0.0 when avoid_conception flag is active, "
        f"got {prob_with_flag!r}"
    )

    # -----------------------------------------------------------------
    # Step 8: advance to T+4; the flag is now stale (flag_tick = T+2,
    # current_tick - 1 = T+3).  A is in a fertile age (28) and the
    # template does not require a couple.  tick_birth_probability > 0.
    #
    # is_avoid_conception_active_this_tick reads agent.simulation.current_tick;
    # Django caches the FK object on the agent instance, so we must refresh A
    # from the DB to pick up the updated current_tick on its simulation.
    # -----------------------------------------------------------------
    sim.current_tick = T + 4
    sim.save(update_fields=["current_tick"])
    A.refresh_from_db()

    assert not is_avoid_conception_active_this_tick(A), (
        "is_avoid_conception_active_this_tick must be False at T+4 (flag set at T+2, stale)"
    )
    prob_stale_flag = tick_birth_probability(
        A,
        template,
        current_pop=4,
        tick_duration_hours=TICK_DURATION_HOURS,
    )
    assert prob_stale_flag > 0.0, (
        f"tick_birth_probability must be > 0 at T+4 when flag is stale and A is fertile, "
        f"got {prob_stale_flag!r}"
    )

    # -----------------------------------------------------------------
    # Step 9: create a separate DecisionLog at T+4 for A;
    # advance to T+5 and resolve separate intents.
    # -----------------------------------------------------------------
    _make_decision_log(sim, A, T + 4, "separate", reason="integration-test separation")

    sim.current_tick = T + 5
    sim.save(update_fields=["current_tick"])

    dissolved = resolve_separate_intents(simulation=sim, tick=T + 5)
    assert len(dissolved) == 1, (
        f"Expected exactly one Couple dissolved, got {len(dissolved)}: {dissolved}"
    )
    couple.refresh_from_db()
    assert couple.dissolved_at_tick == T + 5, (
        f"Expected dissolved_at_tick={T + 5}, got {couple.dissolved_at_tick}"
    )
    assert couple.dissolution_reason == "separate", (
        f"Expected dissolution_reason='separate', got '{couple.dissolution_reason}'"
    )

    # -----------------------------------------------------------------
    # Step 10: verify A is no longer in an active couple and can be
    # paired again by a subsequent resolve_pair_bond_intents call.
    # -----------------------------------------------------------------
    assert not is_in_active_couple(A), "A must not be in an active couple after separation"
    assert not is_in_active_couple(C), "C must not be in an active couple after separation"

    # Verify A can form a new couple (pair_bond with D).
    _make_decision_log(sim, A, T + 5, "pair_bond", target="AgentD_male")
    _make_decision_log(sim, D, T + 5, "pair_bond", target="AgentA_female")

    sim.current_tick = T + 6
    sim.save(update_fields=["current_tick"])

    new_formed = resolve_pair_bond_intents(simulation=sim, tick=T + 6, rng=rng)
    assert len(new_formed) == 1, (
        f"Expected A to re-pair with D after separation, got {len(new_formed)}: {new_formed}"
    )
    new_couple = new_formed[0]
    # A.pk < D.pk, so agent_a must be A.
    assert new_couple.agent_a_id == A.pk
    assert new_couple.agent_b_id == D.pk
    assert is_in_active_couple(A), "A must be in an active couple after re-pairing with D"

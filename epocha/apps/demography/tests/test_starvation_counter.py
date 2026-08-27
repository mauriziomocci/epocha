"""Tests for the persisted starvation counter (spec FR-011, FR-012, SC-003).

`evaluate_emergency_flight` takes `consecutive_ticks_under_subsistence` as an
explicit argument because no such field existed in the schema; Plan 3 left the
obligation in writing. Without that storage the emergency-flight module is dead
code in a live run: with the default empty mapping every agent evaluates to
"does not meet preconditions" and the path never fires.

This module covers the storage itself. The step that maintains it inside the
tick, and its position in the declared order, are covered where the
orchestrator is tested.
"""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model

from epocha.apps.agents.models import Agent
from epocha.apps.simulation.models import Simulation

User = get_user_model()


@pytest.fixture
def simulation(db):
    user = User.objects.create_user(
        email="starvation@epocha.dev",
        username="starvationuser",
        password="pass1234",
    )
    return Simulation.objects.create(
        name="StarvationCounterTest",
        seed=2026,
        owner=user,
        current_tick=10,
    )


def test_new_agent_starts_at_zero(simulation):
    """A fresh agent has never been under subsistence."""
    agent = Agent.objects.create(simulation=simulation, name="Chiara", age=30)

    agent.refresh_from_db()

    assert agent.consecutive_ticks_under_subsistence == 0


def test_counter_persists_across_reload(simulation):
    """The counter has to survive the process: the tick loop is a set of
    Celery tasks and in-memory state does not outlive one of them."""
    agent = Agent.objects.create(simulation=simulation, name="Nicola", age=41)

    Agent.objects.filter(pk=agent.pk).update(consecutive_ticks_under_subsistence=3)

    assert Agent.objects.get(pk=agent.pk).consecutive_ticks_under_subsistence == 3


# ---------------------------------------------------------------------------
# The step that maintains the counter, and the trigger that reads it.
# ---------------------------------------------------------------------------


@pytest.fixture
def sim_with_zone(db):
    """A simulation with the economy scaffolding the subsistence threshold
    needs: without a ZoneEconomy the threshold is zero and nobody starves."""
    from django.contrib.gis.geos import Point, Polygon

    from epocha.apps.economy.models import GoodCategory, ZoneEconomy
    from epocha.apps.world.models import Government, World, Zone

    user = User.objects.create_user(
        email="counterstep@epocha.dev",
        username="counterstepuser",
        password="pass1234",
    )
    sim = Simulation.objects.create(
        name="CounterStepTest",
        seed=2026,
        owner=user,
        current_tick=50,
        config={"demography_enabled": True},
    )
    world = World.objects.create(simulation=sim, stability_index=0.7)
    # The flight path reads government stability into its zone statistics.
    Government.objects.create(simulation=sim)
    zone = Zone.objects.create(
        world=world,
        name="CounterZone",
        zone_type="residential",
        boundary=Polygon.from_bbox((0, 0, 100, 100)),
        center=Point(50, 50),
    )
    good = GoodCategory.objects.create(
        simulation=sim,
        code="grain",
        name="Grain",
        base_price=10.0,
        is_essential=True,
        price_elasticity=0.3,
    )
    ZoneEconomy.objects.create(zone=zone, market_prices={good.code: 10.0})
    return sim, zone


def _agent(sim, zone, name, wealth, **kwargs):
    from django.contrib.gis.geos import Point

    defaults = dict(
        role="farmer",
        location=Point(50, 50),
        health=1.0,
        wealth=wealth,
        age=40,
        birth_tick=int(sim.current_tick - 40 * 365),
        education_level=0.5,
        social_class="working",
        gender=Agent.Gender.MALE,
        personality={},
    )
    defaults.update(kwargs)
    return Agent.objects.create(simulation=sim, name=name, zone=zone, **defaults)


def _context(sim):
    from epocha.apps.demography import orchestrator
    from epocha.apps.demography.template_loader import load_template

    return orchestrator.DemographyTickContext(
        simulation=sim,
        tick=sim.current_tick + 1,
        template=load_template("pre_industrial_christian"),
    )


class TestCounterStep:
    def test_it_increments_below_the_subsistence_threshold(self, sim_with_zone):
        from epocha.apps.demography import orchestrator

        sim, zone = sim_with_zone
        starving = _agent(sim, zone, "Affamato", wealth=0.0)

        orchestrator.run_starvation_counter_step(_context(sim))

        starving.refresh_from_db()
        assert starving.consecutive_ticks_under_subsistence == 1

    def test_it_resets_when_wealth_rises_above_the_line(self, sim_with_zone):
        from epocha.apps.demography import orchestrator

        sim, zone = sim_with_zone
        recovered = _agent(
            sim, zone, "Ripreso", wealth=10_000.0, consecutive_ticks_under_subsistence=7
        )

        orchestrator.run_starvation_counter_step(_context(sim))

        recovered.refresh_from_db()
        assert recovered.consecutive_ticks_under_subsistence == 0

    def test_it_accumulates_across_ticks(self, sim_with_zone):
        from epocha.apps.demography import orchestrator

        sim, zone = sim_with_zone
        starving = _agent(sim, zone, "Affamato", wealth=0.0)
        context = _context(sim)

        orchestrator.run_starvation_counter_step(context)
        orchestrator.run_starvation_counter_step(context)
        orchestrator.run_starvation_counter_step(context)

        starving.refresh_from_db()
        assert starving.consecutive_ticks_under_subsistence == 3

    def test_the_dead_are_not_counted(self, sim_with_zone):
        from epocha.apps.demography import orchestrator

        sim, zone = sim_with_zone
        dead = _agent(sim, zone, "Morto", wealth=0.0, is_alive=False, death_tick=40)

        orchestrator.run_starvation_counter_step(_context(sim))

        dead.refresh_from_db()
        assert dead.consecutive_ticks_under_subsistence == 0

    def test_the_predicate_is_the_one_the_flight_trigger_uses(self, sim_with_zone):
        """FR-011: counter and trigger must share the predicate, or they
        diverge in silence and the flight fires on a count nobody can trace.

        Measured against the trigger's own condition rather than restated:
        the agent sits just below the threshold the trigger computes, so an
        implementation using any other line disagrees here.
        """
        from epocha.apps.demography import orchestrator
        from epocha.apps.demography.context import compute_subsistence_threshold

        sim, zone = sim_with_zone
        threshold = compute_subsistence_threshold(sim, zone)
        assert threshold > 0.0, "fixture must produce a real threshold"

        just_below = _agent(sim, zone, "AppenaSotto", wealth=threshold - 0.01)
        just_above = _agent(sim, zone, "AppenaSopra", wealth=threshold + 0.01)

        orchestrator.run_starvation_counter_step(_context(sim))

        just_below.refresh_from_db()
        just_above.refresh_from_db()
        assert just_below.consecutive_ticks_under_subsistence == 1
        assert just_above.consecutive_ticks_under_subsistence == 0


class TestFlightReadsThePersistedCounter:
    def test_flight_fires_from_the_stored_counter_alone(self, sim_with_zone):
        """FR-012: `process_emergency_flight` reads the column instead of
        receiving a mapping, which is what makes the path reachable in a
        live run rather than only in unit tests."""
        from epocha.apps.demography.migration import process_emergency_flight
        from epocha.apps.demography.models import DemographyEvent
        from epocha.apps.demography.template_loader import load_template

        sim, zone = sim_with_zone
        trigger_ticks = load_template("pre_industrial_christian")["migration"][
            "flight_trigger_ticks"
        ]
        _agent(
            sim,
            zone,
            "Disperato",
            wealth=0.0,
            consecutive_ticks_under_subsistence=trigger_ticks + 1,
        )

        process_emergency_flight(sim, sim.current_tick + 1)

        assert DemographyEvent.objects.filter(
            simulation=sim,
            event_type__in=[
                DemographyEvent.EventType.MIGRATION,
                DemographyEvent.EventType.TRAPPED_CRISIS,
            ],
        ).exists()

    def test_a_short_counter_fires_nothing(self, sim_with_zone):
        from epocha.apps.demography.migration import process_emergency_flight
        from epocha.apps.demography.models import DemographyEvent

        sim, zone = sim_with_zone
        _agent(sim, zone, "Paziente", wealth=0.0, consecutive_ticks_under_subsistence=1)

        process_emergency_flight(sim, sim.current_tick + 1)

        assert not DemographyEvent.objects.filter(simulation=sim).exists()

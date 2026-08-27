"""Tests for the death path: mortality, the marking, the succession handoff.

`mortality.py` is four pure functions with no per-tick entry point, and
`process_inheritance_batch` calls itself "THE PLAN 4 DEATH-PATH ENTRY POINT
(orchestrator step 2/3)" while documenting a precondition it never verifies:
every agent handed to it already carries `is_alive=False`. Steps 1 and 3 --
deciding who dies and emitting the event -- are what this path adds.
"""

from __future__ import annotations

from dataclasses import replace

import pytest
from django.contrib.gis.geos import Point, Polygon

from epocha.apps.agents.models import Agent
from epocha.apps.demography import orchestrator
from epocha.apps.demography.models import DemographyEvent
from epocha.apps.demography.template_loader import load_template
from epocha.apps.simulation.models import Simulation
from epocha.apps.users.models import User
from epocha.apps.world.models import Government, World, Zone

TICKS_PER_YEAR = 365.0


@pytest.fixture
def sim_with_zone(db):
    user = User.objects.create_user(
        email="death@epocha.dev", username="deathuser", password="pass1234"
    )
    sim = Simulation.objects.create(
        name="DeathTest",
        seed=2026,
        owner=user,
        current_tick=50,
        config={"demography_enabled": True},
    )
    world = World.objects.create(simulation=sim, stability_index=0.7)
    # `process_inheritance_batch` credits estate tax to the government
    # treasury, so succession needs one to exist.
    Government.objects.create(simulation=sim)
    zone = Zone.objects.create(
        world=world,
        name="DeathZone",
        zone_type="residential",
        boundary=Polygon.from_bbox((0, 0, 100, 100)),
        center=Point(50, 50),
    )
    return sim, zone


def _agent(sim, zone, name, age=40, **kwargs):
    defaults = dict(
        role="farmer",
        location=Point(50, 50),
        health=1.0,
        wealth=100.0,
        age=age,
        birth_tick=int(sim.current_tick - age * TICKS_PER_YEAR),
        education_level=0.5,
        social_class="working",
        gender=Agent.Gender.MALE,
        personality={},
    )
    defaults.update(kwargs)
    return Agent.objects.create(simulation=sim, name=name, zone=zone, **defaults)


def _context(sim, template_name="pre_industrial_christian"):
    return orchestrator.DemographyTickContext(
        simulation=sim,
        tick=sim.current_tick + 1,
        template=load_template(template_name),
    )


class _AlwaysDies:
    """Every mortality draw lands below any positive probability."""

    def random(self):
        return 0.0

    def gauss(self, mu, sigma):
        return mu


class _NeverDies:
    def random(self):
        return 1.0

    def gauss(self, mu, sigma):
        return mu


class _ScriptedRandom:
    """Dictated draws, so exactly one agent of several dies.

    The step consumes one draw per living agent to decide, plus one more
    per death to attribute the cause, and it iterates in ascending id, so a
    script can single out a victim. Exhausted, it returns 1.0 -- nobody
    else dies -- rather than raising, which would turn a miscounted script
    into an error instead of a clear assertion failure.
    """

    def __init__(self, draws):
        self._draws = list(draws)

    def random(self):
        return self._draws.pop(0) if self._draws else 1.0

    def gauss(self, mu, sigma):
        return mu


class TestMortalityStep:
    def test_the_dead_are_marked_with_tick_and_cause(self, sim_with_zone):
        sim, zone = sim_with_zone
        agent = _agent(sim, zone, "Vittima", age=70)
        context = _context(sim)

        orchestrator.run_mortality_step(context, rng=_AlwaysDies())

        agent.refresh_from_db()
        assert agent.is_alive is False
        assert agent.death_tick == context.tick
        assert agent.death_cause in {c for c, _ in Agent.DeathCause.choices}

    def test_survivors_are_untouched(self, sim_with_zone):
        sim, zone = sim_with_zone
        agent = _agent(sim, zone, "Sopravvissuto", age=30)
        context = _context(sim)

        orchestrator.run_mortality_step(context, rng=_NeverDies())

        agent.refresh_from_db()
        assert agent.is_alive is True
        assert agent.death_tick is None

    def test_a_death_emits_an_event_carrying_the_step_index(self, sim_with_zone):
        sim, zone = sim_with_zone
        agent = _agent(sim, zone, "Vittima", age=70)
        context = _context(sim)

        orchestrator.run_mortality_step(context, rng=_AlwaysDies())

        event = DemographyEvent.objects.get(
            simulation=sim, event_type=DemographyEvent.EventType.DEATH
        )
        mortality_step = next(s for s in orchestrator.DEMOGRAPHY_STEPS if s.name == "mortality")
        assert event.payload["step_index"] == mortality_step.index
        assert event.payload["death_cause"] == agent.__class__.objects.get(pk=agent.pk).death_cause
        assert event.primary_agent_id == agent.id

    def test_the_event_index_follows_the_declared_order(self, sim_with_zone, monkeypatch):
        """A hardcoded index matching today's order proves nothing: move the
        step and the payload has to move with it."""
        sim, zone = sim_with_zone
        _agent(sim, zone, "Vittima", age=70)
        context = _context(sim)
        moved = tuple(
            step if step.name != "mortality" else replace(step, index=99)
            for step in orchestrator.DEMOGRAPHY_STEPS
        )
        monkeypatch.setattr(orchestrator, "DEMOGRAPHY_STEPS", moved)

        orchestrator.run_mortality_step(context, rng=_AlwaysDies())

        event = DemographyEvent.objects.get(
            simulation=sim, event_type=DemographyEvent.EventType.DEATH
        )
        assert event.payload["step_index"] == 99

    def test_already_dead_agents_are_not_killed_twice(self, sim_with_zone):
        sim, zone = sim_with_zone
        agent = _agent(sim, zone, "GiaMorto", age=70, is_alive=False, death_tick=10)
        context = _context(sim)

        orchestrator.run_mortality_step(context, rng=_AlwaysDies())

        agent.refresh_from_db()
        assert agent.death_tick == 10
        assert not DemographyEvent.objects.filter(
            simulation=sim, event_type=DemographyEvent.EventType.DEATH
        ).exists()

    def test_mortality_reads_birth_tick_and_not_the_frozen_age_column(self, sim_with_zone):
        """The two ageing sources must be able to disagree.

        A newborn's mortality is high under Heligman-Pollard and an adult's
        is low, so an implementation reading the frozen `age` column instead
        of `birth_tick` produces a visibly different hazard. The agent below
        carries `age=1` in the column and eighty years of birth ticks.
        """
        sim, zone = sim_with_zone
        elder = _agent(sim, zone, "Anziano", age=80)
        Agent.objects.filter(pk=elder.pk).update(age=1)
        # Reloaded before measuring: the queryset update does not touch the
        # in-memory instance, and measuring the stale object would compare
        # two identical `age` columns and prove nothing.
        elder.refresh_from_db()
        context = _context(sim)

        assert elder.age == 1
        probability_from_birth_tick = orchestrator.mortality_probability_for(
            elder, context, tick_duration_hours=24.0
        )
        infant = _agent(sim, zone, "Neonato", age=1)

        assert probability_from_birth_tick == pytest.approx(
            orchestrator.mortality_probability_for(
                _agent(sim, zone, "Coetaneo", age=80), context, tick_duration_hours=24.0
            ),
            rel=1e-9,
        )
        assert probability_from_birth_tick != pytest.approx(
            orchestrator.mortality_probability_for(
                infant, context, tick_duration_hours=24.0
            ),
            rel=1e-3,
        )

    def test_no_living_agent_is_a_no_op(self, sim_with_zone):
        sim, _ = sim_with_zone
        context = _context(sim)

        orchestrator.run_mortality_step(context, rng=_AlwaysDies())

        assert not DemographyEvent.objects.filter(simulation=sim).exists()


class TestSuccessionStep:
    def test_succession_settles_the_estates_of_this_tick_dead(self, sim_with_zone):
        """The succession step runs after mortality and reads the agents that
        died in this tick, satisfying the batch's documented precondition
        that `is_alive=False` is already set by the caller."""
        sim, zone = sim_with_zone
        deceased = _agent(sim, zone, "Defunto", age=70, wealth=500.0)
        heir = _agent(sim, zone, "Erede", age=30, wealth=0.0, parent_agent=deceased)
        context = _context(sim)

        # Draw one: the deceased (lowest id) dies. Draw two: the cause.
        # Nothing is left for the heir, so the heir survives to inherit.
        orchestrator.run_mortality_step(context, rng=_ScriptedRandom([0.0, 0.5]))
        orchestrator.run_succession_step(context)

        heir.refresh_from_db()
        deceased.refresh_from_db()
        assert deceased.is_alive is False
        assert heir.wealth > 0.0

    def test_succession_ignores_deaths_from_earlier_ticks(self, sim_with_zone):
        """Only this tick's dead are settled.

        An estate settles once. Without the tick filter every past death
        would be re-settled on every tick, multiplying every legacy for as
        long as the run lasts.
        """
        sim, zone = sim_with_zone
        long_dead = _agent(
            sim, zone, "MortoDaTempo", age=70, wealth=500.0, is_alive=False, death_tick=10
        )
        heir = _agent(sim, zone, "Erede", age=30, wealth=0.0, parent_agent=long_dead)
        context = _context(sim)

        orchestrator.run_succession_step(context)

        heir.refresh_from_db()
        assert heir.wealth == 0.0

    def test_succession_without_deaths_writes_nothing(self, sim_with_zone):
        sim, zone = sim_with_zone
        _agent(sim, zone, "Vivo", age=30)
        context = _context(sim)

        orchestrator.run_succession_step(context)

        assert not DemographyEvent.objects.filter(
            simulation=sim, event_type=DemographyEvent.EventType.INHERITANCE_TRANSFER
        ).exists()

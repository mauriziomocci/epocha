"""Tests for the death path: mortality, the marking, the succession handoff.

`mortality.py` is four pure functions with no per-tick entry point, and
`process_inheritance_batch` calls itself "THE PLAN 4 DEATH-PATH ENTRY POINT
(orchestrator step 2/3)" while documenting a precondition it never verifies:
every agent handed to it already carries `is_alive=False`. Steps 1 and 3 --
deciding who dies and emitting the event -- are what this path adds.
"""

from __future__ import annotations

import math
from dataclasses import replace
from statistics import NormalDist
from types import SimpleNamespace

import pytest
from django.contrib.gis.geos import Point, Polygon

from epocha.apps.agents.models import Agent
from epocha.apps.demography import orchestrator
from epocha.apps.demography.models import DemographyEvent
from epocha.apps.demography.mortality import annual_mortality_probability
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
            orchestrator.mortality_probability_for(infant, context, tick_duration_hours=24.0),
            rel=1e-3,
        )

    def test_the_stored_age_column_is_advanced_to_the_derived_age(self, sim_with_zone):
        """`Agent.age` has to become true, because two live paths read it.

        Found by the closure review over the whole branch diff. The column is
        written at world generation and, for agents BORN in the simulation,
        set to 0 by `build_newborn` -- and nothing ever advanced it, so every
        simulation-born agent carried age 0 for life. Two consumers read it
        and neither is ours to rewrite: `annuity_for_agent(agent.age, ...)`
        inside the third condition of emergency flight, which hands a newborn
        the longest working horizon the model admits and therefore the
        largest expected gain from any move; and `child.age >= adulthood_age`
        in the caretaker pass, which would assign a guardian to a
        forty-year-old born in the run.

        `birth_tick` remains the canonical source and the only thing that
        advances on its own. The column is a cache of it, and the mortality
        step is where it is refreshed because that step already derives the
        age of every living agent for the hazard.
        """
        sim, zone = sim_with_zone
        # Born in the simulation: the column says 0 and the derived age is 30.
        agent = _agent(sim, zone, "Nato", age=30)
        Agent.objects.filter(pk=agent.pk).update(age=0)
        context = _context(sim)

        orchestrator.run_mortality_step(context, rng=_ScriptedRandom([1.0] * 20))

        agent.refresh_from_db()
        assert agent.is_alive is True, "the scripted stream killed the agent"
        assert agent.age == 30, (
            f"the stored age is {agent.age}: nothing advances the column, so "
            "the annuity horizon and the minority test read a newborn"
        )

    def test_no_living_agent_is_a_no_op(self, sim_with_zone):
        sim, _ = sim_with_zone
        context = _context(sim)

        orchestrator.run_mortality_step(context, rng=_AlwaysDies())

        assert not DemographyEvent.objects.filter(simulation=sim).exists()


class TestFirstYearOfLife:
    """A birth cohort followed through its first year realizes `1q0 = q(0)`.

    Heligman-Pollard `q_x` is the probability of dying between EXACT ages
    `x` and `x + 1`, the life-table quantity (Preston, Heuveline & Guillot
    2001, ch. 3). Until the remediation of gate decision D-29-20 the
    mortality step evaluated it at the continuous age, so a newborn spent its
    first year on `q(0.02)`, `q(0.04)`, ... -- a curve that falls steeply in
    the first months -- and the realized first-year death probability came
    out near a third of the model's `q(0)`. Fourteen gate rounds missed it
    because no test followed a cohort through a whole year of ticks: every
    test pinned one tick at one age.

    Only the mortality step runs, on the simulation's own seeded stream:
    births, couples and migration would change who is exposed and are not
    the quantity under test.
    """

    COHORT_SIZE = 5000
    HOURS_PER_WEEK = 168.0
    # False-failure rate of the tolerance under the correct model. The draw
    # is seeded, so the outcome is fixed; alpha states how unusual a seed
    # would have to be to fail a correct implementation.
    ALPHA = 0.001

    @pytest.mark.parametrize("hours_per_tick", [24.0, 730.0, 4380.0, 8760.0])
    def test_the_ticks_of_the_first_year_compound_exactly_to_q0(self, hours_per_tick):
        """The per-tick probabilities a newborn meets before age 1 multiply back to `q(0)`.

        No draw is involved: this is the survival the step's own hazard
        implies, so it holds to rounding. Only tick lengths that divide the
        year are used, so that the year is a whole number of ticks.

        It also pins WHICH age a tick reads. The step of tick `t` decides
        death over the interval since `t - 1` -- a newborn of tick `b` is
        first exposed at `b + 1`, so that interval is the one it lived -- and
        reads the age at its start. Read at its end, the tick on which the
        first birthday falls was charged `q(1)`: harmless at a daily tick,
        one twelfth of the year at a monthly one, and the whole first year at
        a yearly one, where no newborn ever met `q(0)`.
        """
        template = load_template("pre_industrial_christian")
        context = orchestrator.DemographyTickContext(simulation=None, tick=0, template=template)
        newborn = SimpleNamespace(birth_tick=0, age=0)
        ticks_per_year = round(8760.0 / hours_per_tick)
        survival = 1.0
        for tick in range(1, ticks_per_year + 1):
            survival *= 1.0 - orchestrator.mortality_probability_for(
                newborn, replace(context, tick=tick), hours_per_tick
            )
        q0 = annual_mortality_probability(0, template["mortality"]["heligman_pollard"])

        assert 1.0 - survival == pytest.approx(q0, rel=1e-9)

    def test_a_weekly_cohort_realizes_q0_over_its_first_year(self, sim_with_zone):
        sim, zone = sim_with_zone
        World.objects.filter(simulation=sim).update(tick_duration_hours=self.HOURS_PER_WEEK)
        born_at = sim.current_tick
        Agent.objects.bulk_create(
            [
                Agent(
                    simulation=sim,
                    zone=zone,
                    name=f"Neonato {i}",
                    role="child",
                    location=Point(50, 50),
                    age=0,
                    birth_tick=born_at,
                    gender=Agent.Gender.FEMALE if i % 2 else Agent.Gender.MALE,
                    personality={},
                )
                for i in range(self.COHORT_SIZE)
            ]
        )
        template = load_template("pre_industrial_christian")
        ticks_per_year = 8760.0 / self.HOURS_PER_WEEK
        # Every tick at which the cohort is still below exact age 1.
        first_year_ticks = range(born_at + 1, born_at + 1 + math.floor(ticks_per_year))
        for tick in first_year_ticks:
            orchestrator.run_mortality_step(
                orchestrator.DemographyTickContext(simulation=sim, tick=tick, template=template)
            )

        dead = Agent.objects.filter(simulation=sim, is_alive=False).count()
        realized = dead / self.COHORT_SIZE
        q0 = annual_mortality_probability(0, template["mortality"]["heligman_pollard"])
        exposure_years = len(first_year_ticks) / ticks_per_year
        expected = 1.0 - (1.0 - q0) ** exposure_years
        standard_error = math.sqrt(expected * (1.0 - expected) / self.COHORT_SIZE)
        tolerance = NormalDist().inv_cdf(1.0 - self.ALPHA / 2.0) * standard_error

        assert abs(realized - expected) <= tolerance, (
            f"first-year death fraction {realized:.4f} against the model's "
            f"{expected:.4f} (q(0) = {q0:.4f} over {exposure_years:.4f} years), "
            f"tolerance {tolerance:.4f}: the hazard is not read at the "
            "completed age"
        )


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


class TestTransactionalBoundary:
    """A step that writes twice must not be able to write once.

    The four audited modules these steps drive each open their own
    `transaction.atomic()`; the steps written here did not, so a failure
    between a step's two writes left the database in a state the model
    forbids -- agents marked dead with no DEATH event, which is the
    invisible death this branch already had to fix once when a mother dying
    in childbirth arrived after succession had run.

    The failure is injected at the second write, which is the only place the
    gap is observable: the first write has happened and the step has not
    finished.
    """

    def test_a_failed_event_write_takes_the_deaths_with_it(self, sim_with_zone, monkeypatch):
        sim, zone = sim_with_zone
        victim = _agent(sim, zone, "Vittima", age=80)

        def _explode(*args, **kwargs):
            raise RuntimeError("event write failed")

        monkeypatch.setattr(DemographyEvent.objects, "bulk_create", _explode)

        with pytest.raises(RuntimeError):
            orchestrator.run_mortality_step(_context(sim), rng=_AlwaysDies())

        victim.refresh_from_db()
        assert victim.is_alive is True, (
            "the agent stayed dead after the event write failed: the step has "
            "no transactional boundary and a death exists with no event"
        )
        assert victim.death_tick is None

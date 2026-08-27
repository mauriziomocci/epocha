"""Tests for the birth path: name selection, the orchestrator, the step.

Nothing in production created a newborn before this work item. The fertility
module decides *whether* a birth happens and resolves childbirth mortality,
but it declares that "callers are responsible for persisting the state
changes" -- so who writes the `Agent` row, with what name, and who emits the
event was nobody's job until now.
"""

from __future__ import annotations

from dataclasses import replace

import pytest
from django.contrib.gis.geos import Point, Polygon

from epocha.apps.agents.models import Agent
from epocha.apps.demography import orchestrator
from epocha.apps.demography.couple import form_couple
from epocha.apps.demography.models import DemographyEvent
from epocha.apps.demography.template_loader import load_template
from epocha.apps.simulation.models import Simulation
from epocha.apps.users.models import User
from epocha.apps.world.models import World, Zone


@pytest.fixture
def sim_with_zone(db):
    user = User.objects.create_user(
        email="birth@epocha.dev", username="birthuser", password="pass1234"
    )
    sim = Simulation.objects.create(
        name="BirthTest",
        seed=2026,
        owner=user,
        current_tick=50,
        config={"demography_enabled": True},
    )
    world = World.objects.create(simulation=sim, stability_index=0.7)
    zone = Zone.objects.create(
        world=world,
        name="BirthZone",
        zone_type="residential",
        boundary=Polygon.from_bbox((0, 0, 100, 100)),
        center=Point(50, 50),
    )
    return sim, zone


TICKS_PER_YEAR = 365.0  # the default 24h tick


def _birth_tick_for_age(sim, age_years):
    """A living adult was born before the run started, so its birth tick is
    negative -- the convention `Agent.birth_tick` documents. Age is derived
    from it, never from the frozen `age` column."""
    return int(sim.current_tick - age_years * TICKS_PER_YEAR)


def _agent(sim, zone, name, age=30, **kwargs):
    defaults = dict(
        role="farmer",
        location=Point(50, 50),
        health=1.0,
        wealth=100.0,
        age=age,
        birth_tick=_birth_tick_for_age(sim, age),
        education_level=0.5,
        social_class="working",
        gender=Agent.Gender.FEMALE,
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


class TestNewbornName:
    """FR-001a: the name comes from the era template's pool, never the LLM.

    An LLM-generated name would make the birth non-reproducible from the
    seed, widening a reproducibility limit the whitepaper scopes to LLM
    sampling alone.
    """

    def test_name_comes_from_the_template_pool(self, sim_with_zone):
        sim, _ = sim_with_zone
        template = load_template("pre_industrial_christian")
        rng = orchestrator.stream_for(sim, tick=51, phase="fertility")

        name = orchestrator.pick_newborn_name(template, Agent.Gender.FEMALE, rng)

        assert name in template["names"]["female"]

    def test_gender_selects_the_pool(self, sim_with_zone):
        sim, _ = sim_with_zone
        template = load_template("pre_industrial_christian")
        rng = orchestrator.stream_for(sim, tick=51, phase="fertility")

        name = orchestrator.pick_newborn_name(template, Agent.Gender.MALE, rng)

        assert name in template["names"]["male"]

    def test_same_stream_reproduces_the_name(self, sim_with_zone):
        sim, _ = sim_with_zone
        template = load_template("pre_industrial_christian")

        first = orchestrator.pick_newborn_name(
            template, Agent.Gender.FEMALE, orchestrator.stream_for(sim, 51, "fertility")
        )
        second = orchestrator.pick_newborn_name(
            template, Agent.Gender.FEMALE, orchestrator.stream_for(sim, 51, "fertility")
        )

        assert first == second

    def test_a_gender_outside_the_pools_still_yields_a_name(self, sim_with_zone):
        """`Agent.Gender` carries a value the birth-sex pools do not model.

        `resolve_birth_attributes` cannot produce it -- it draws from the
        secondary sex ratio -- but the model can hold it, and a birth path
        that raised here would turn a data state into a crash.
        """
        sim, _ = sim_with_zone
        template = load_template("pre_industrial_christian")
        rng = orchestrator.stream_for(sim, tick=51, phase="fertility")

        name = orchestrator.pick_newborn_name(template, "non_binary", rng)

        assert name in template["names"]["male"] + template["names"]["female"]


class TestBirthOrchestrator:
    def test_newborn_is_persisted_with_its_lineage_and_birth_tick(self, sim_with_zone):
        sim, zone = sim_with_zone
        mother = _agent(sim, zone, "Madre", gender=Agent.Gender.FEMALE, age=28)
        father = _agent(sim, zone, "Padre", gender=Agent.Gender.MALE, age=31)
        context = _context(sim)
        rng = orchestrator.stream_for(sim, context.tick, "inheritance")

        newborn = orchestrator.build_newborn(context, mother, father, rng)
        Agent.objects.bulk_create([newborn])

        stored = Agent.objects.get(name=newborn.name, birth_tick=context.tick)
        assert stored.parent_agent_id == mother.id
        assert stored.other_parent_agent_id == father.id
        assert stored.birth_tick == context.tick
        assert stored.zone_id == zone.id
        assert stored.is_alive is True
        assert stored.age == 0

    def test_newborn_carries_inherited_attributes(self, sim_with_zone):
        """`apply_inheritance_at_birth` runs inside the orchestrator: the
        newborn is not a blank row with a name on it."""
        sim, zone = sim_with_zone
        mother = _agent(sim, zone, "Madre", social_class="wealthy", education_level=0.8)
        father = _agent(sim, zone, "Padre", gender=Agent.Gender.MALE, social_class="wealthy")
        context = _context(sim)
        rng = orchestrator.stream_for(sim, context.tick, "inheritance")

        newborn = orchestrator.build_newborn(context, mother, father, rng)

        assert newborn.gender in {g for g, _ in Agent.Gender.choices}
        assert newborn.sexual_orientation
        assert newborn.wealth == 0.0

    def test_a_birth_without_a_known_father_is_supported(self, sim_with_zone):
        sim, zone = sim_with_zone
        mother = _agent(sim, zone, "Madre")
        context = _context(sim)
        rng = orchestrator.stream_for(sim, context.tick, "inheritance")

        newborn = orchestrator.build_newborn(context, mother, None, rng)

        assert newborn.parent_agent_id == mother.id
        assert newborn.other_parent_agent_id is None


class _ScriptedRandom:
    """A stream whose draws are dictated, so a probabilistic step can be
    steered without reaching into the step's internals.

    Birth and childbirth mortality are both `rng.random() < p` decisions:
    a 0.0 makes the event certain and a 1.0 makes it impossible, whatever
    the underlying probability. Exhausting the script yields 0.5, which
    keeps a longer-than-expected run from raising instead of failing an
    assertion.
    """

    def __init__(self, draws):
        self._draws = list(draws)

    def random(self):
        return self._draws.pop(0) if self._draws else 0.5

    def gauss(self, mu, sigma):
        return mu

    def choice(self, seq):
        return seq[0]


BIRTH_HAPPENS = 0.0
MOTHER_SURVIVES = 1.0
MOTHER_DIES = 0.0
NEWBORN_SURVIVES = 0.0


class TestFertilityStep:
    def test_a_birth_emits_an_event_carrying_the_step_index(self, sim_with_zone):
        """US1 acceptance 2: the payload carries the position in the declared
        order. The event type already partitions by module in the schema, so
        it was never evidence of anything an implementation had to do."""
        sim, zone = sim_with_zone
        mother = _agent(sim, zone, "Madre", age=25)
        father = _agent(sim, zone, "Padre", gender=Agent.Gender.MALE, age=27)
        form_couple(mother, father, formed_at_tick=sim.current_tick - 1)
        context = _context(sim)

        orchestrator.run_fertility_step(
            context, rng=_ScriptedRandom([BIRTH_HAPPENS, MOTHER_SURVIVES])
        )

        event = DemographyEvent.objects.get(
            simulation=sim, event_type=DemographyEvent.EventType.BIRTH
        )
        fertility_step = next(s for s in orchestrator.DEMOGRAPHY_STEPS if s.name == "fertility")
        assert event.payload["step_index"] == fertility_step.index
        assert event.primary_agent_id is not None
        assert event.secondary_agent_id == mother.id
        assert Agent.objects.filter(parent_agent=mother, birth_tick=context.tick).count() == 1

    def test_maternal_death_is_persisted(self, sim_with_zone):
        """`resolve_childbirth_event` is a pure resolver: without the
        orchestrator persisting its verdict, a mother who dies in childbirth
        stays alive in the database."""
        sim, zone = sim_with_zone
        mother = _agent(sim, zone, "Madre", age=25)
        father = _agent(sim, zone, "Padre", gender=Agent.Gender.MALE, age=27)
        form_couple(mother, father, formed_at_tick=sim.current_tick - 1)
        context = _context(sim)

        orchestrator.run_fertility_step(
            context,
            rng=_ScriptedRandom([BIRTH_HAPPENS, MOTHER_DIES, NEWBORN_SURVIVES]),
        )

        mother.refresh_from_db()
        assert mother.is_alive is False
        assert mother.death_tick == context.tick
        assert mother.death_cause == Agent.DeathCause.CHILDBIRTH

    def test_a_newborn_that_does_not_survive_is_not_created(self, sim_with_zone):
        """The mother dies and the neonate does not make it: the tick must
        leave no half-born row behind."""
        sim, zone = sim_with_zone
        mother = _agent(sim, zone, "Madre", age=25)
        father = _agent(sim, zone, "Padre", gender=Agent.Gender.MALE, age=27)
        form_couple(mother, father, formed_at_tick=sim.current_tick - 1)
        context = _context(sim)

        orchestrator.run_fertility_step(
            context,
            rng=_ScriptedRandom([BIRTH_HAPPENS, MOTHER_DIES, 1.0]),
        )

        assert not Agent.objects.filter(parent_agent=mother).exists()
        assert not DemographyEvent.objects.filter(
            simulation=sim, event_type=DemographyEvent.EventType.BIRTH
        ).exists()

    def test_no_eligible_mother_writes_nothing(self, sim_with_zone):
        sim, zone = sim_with_zone
        _agent(sim, zone, "Solo", gender=Agent.Gender.MALE, age=40)
        context = _context(sim)

        orchestrator.run_fertility_step(context, rng=_ScriptedRandom([BIRTH_HAPPENS]))

        assert not DemographyEvent.objects.filter(simulation=sim).exists()

    def test_fertility_reads_birth_tick_and_not_the_frozen_age_column(self, sim_with_zone):
        """The two sources must be able to disagree, or the test cannot tell
        them apart.

        Every fixture where `age` matches `birth_tick` is satisfied by an
        implementation that filters the frozen column -- the blind spot this
        project has already paid for once: a probe declaring the same value
        as the fallback proves nothing about which one was read. Here the
        columns disagree on purpose. The agent's `age` column says 70, far
        outside the fertile window; her `birth_tick` says 25 years, inside
        it. Ageing comes from `birth_tick`, so she must be a candidate.
        """
        sim, zone = sim_with_zone
        mother = _agent(sim, zone, "Madre", age=25)
        Agent.objects.filter(pk=mother.pk).update(age=70)
        father = _agent(sim, zone, "Padre", gender=Agent.Gender.MALE, age=27)
        form_couple(mother, father, formed_at_tick=sim.current_tick - 1)
        context = _context(sim)

        orchestrator.run_fertility_step(
            context, rng=_ScriptedRandom([BIRTH_HAPPENS, MOTHER_SURVIVES])
        )

        assert Agent.objects.filter(parent_agent=mother, birth_tick=context.tick).exists()

    def test_an_agent_whose_frozen_age_looks_fertile_but_is_not_is_excluded(self, sim_with_zone):
        """The mirror case, so the property is pinned on both sides."""
        sim, zone = sim_with_zone
        elder = _agent(sim, zone, "Anziana", age=80)
        Agent.objects.filter(pk=elder.pk).update(age=30)
        partner = _agent(sim, zone, "Compagno", gender=Agent.Gender.MALE, age=80)
        form_couple(elder, partner, formed_at_tick=sim.current_tick - 1)
        context = _context(sim)

        orchestrator.run_fertility_step(
            context, rng=_ScriptedRandom([BIRTH_HAPPENS, MOTHER_SURVIVES])
        )

        assert not Agent.objects.filter(parent_agent=elder).exists()

    def test_the_event_index_follows_the_declared_order(self, sim_with_zone, monkeypatch):
        """The payload must carry the step's position as declared, not a
        number that happens to match it today.

        Asserting the payload against `DEMOGRAPHY_STEPS` alone cannot fail on
        a hardcoded index while the two agree. Moving the step in the
        declared order separates them.
        """
        sim, zone = sim_with_zone
        mother = _agent(sim, zone, "Madre", age=25)
        father = _agent(sim, zone, "Padre", gender=Agent.Gender.MALE, age=27)
        form_couple(mother, father, formed_at_tick=sim.current_tick - 1)
        context = _context(sim)

        moved = tuple(
            step if step.name != "fertility" else replace(step, index=99)
            for step in orchestrator.DEMOGRAPHY_STEPS
        )
        monkeypatch.setattr(orchestrator, "DEMOGRAPHY_STEPS", moved)

        orchestrator.run_fertility_step(
            context, rng=_ScriptedRandom([BIRTH_HAPPENS, MOTHER_SURVIVES])
        )

        event = DemographyEvent.objects.get(
            simulation=sim, event_type=DemographyEvent.EventType.BIRTH
        )
        assert event.payload["step_index"] == 99

    def test_a_mother_who_died_this_tick_does_not_give_birth(self, sim_with_zone):
        """FR-004 seen from the fertility side: the step reads living agents,
        so a death recorded earlier in the same tick removes her."""
        sim, zone = sim_with_zone
        mother = _agent(sim, zone, "Madre", age=25, is_alive=False, death_tick=51)
        father = _agent(sim, zone, "Padre", gender=Agent.Gender.MALE, age=27)
        form_couple(mother, father, formed_at_tick=sim.current_tick - 1)
        context = _context(sim)

        orchestrator.run_fertility_step(
            context, rng=_ScriptedRandom([BIRTH_HAPPENS, MOTHER_SURVIVES])
        )

        assert not Agent.objects.filter(parent_agent=mother).exists()

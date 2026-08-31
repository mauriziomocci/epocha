"""Tests for the birth path: name selection, the orchestrator, the step.

Nothing in production created a newborn before this work item. The fertility
module decides *whether* a birth happens and resolves childbirth mortality,
but it declares that "callers are responsible for persisting the state
changes" -- so who writes the `Agent` row, with what name, and who emits the
event was nobody's job until now.
"""

from __future__ import annotations

import copy
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
from epocha.apps.world.models import Government, World, Zone


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
    # A death in childbirth now settles the mother's estate, and the estate
    # tax is credited to the government treasury.
    Government.objects.create(simulation=sim)
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
    def test_two_births_in_one_step_run_draw_from_one_threaded_stream(self, sim_with_zone):
        """SC-006 at the seam the module-level proof cannot reach.

        `test_inheritance_birth_rng` proves that sixteen calls threading ONE
        stream produce distinct newborns -- by threading the stream itself.
        Nothing there constrains this step, which is where the original
        defect lived: re-deriving `stream_for(..., "inheritance")` per
        newborn restarts the same sequence per birth and hands every newborn
        of the tick identical draws, and the entire suite stayed green under
        exactly that mutation. So the step is run here with two forced
        births, and the newborns' continuous trait draws must differ --
        gauss residuals off one stream at different offsets cannot collide,
        while restarted streams cannot do anything else.
        """
        from epocha.apps.demography.tests.test_inheritance import SCALAR_HERITABLE_TRAITS

        sim, zone = sim_with_zone
        for i in range(2):
            mother = _agent(sim, zone, f"MadreGemella{i}", age=25)
            father = _agent(sim, zone, f"PadreGemello{i}", gender=Agent.Gender.MALE, age=27)
            form_couple(mother, father, formed_at_tick=sim.current_tick - 1)
        context = _context(sim)

        orchestrator.run_fertility_step(
            context,
            rng=_ScriptedRandom([BIRTH_HAPPENS, MOTHER_SURVIVES, BIRTH_HAPPENS, MOTHER_SURVIVES]),
        )

        newborns = list(
            Agent.objects.filter(simulation=sim, birth_tick=context.tick).order_by("id")
        )
        assert len(newborns) == 2, "the scripted stream did not force both births"
        first = tuple(getattr(newborns[0], name) for name in SCALAR_HERITABLE_TRAITS)
        second = tuple(getattr(newborns[1], name) for name in SCALAR_HERITABLE_TRAITS)
        assert first != second, (
            "two newborns of one tick carry identical trait residuals: the "
            "inheritance stream is being restarted per birth"
        )

    def test_the_candidate_query_alone_excludes_the_dead_and_the_male(self, sim_with_zone):
        """The two filters nothing else backs up, pinned without the couple
        gate masking them.

        Under the default era the couple requirement suppresses almost any
        candidate the query lets through -- a dead woman's couple was
        dissolved by succession, an unpartnered man was never in one -- so
        dropping `is_alive=True` or `gender=FEMALE` from the candidate query
        survived the entire suite. `modern_democracy` has
        `require_couple_for_birth: false`: here the query IS the gate, and a
        forced-birth stream turns any leak straight into a newborn.
        """
        sim, zone = sim_with_zone
        _agent(sim, zone, "Morta", age=25, is_alive=False, death_tick=sim.current_tick - 1)
        _agent(sim, zone, "UomoSolo", gender=Agent.Gender.MALE, age=25)
        context = _context(sim, template_name="modern_democracy")

        orchestrator.run_fertility_step(
            context,
            rng=_ScriptedRandom([BIRTH_HAPPENS, MOTHER_SURVIVES, BIRTH_HAPPENS, MOTHER_SURVIVES]),
        )

        assert not Agent.objects.filter(simulation=sim, birth_tick=context.tick).exists(), (
            "a dead woman or a man produced a birth: the candidate query "
            "stopped filtering on is_alive or gender"
        )

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

    def test_a_mother_who_dies_in_childbirth_is_settled_like_any_other_death(self, sim_with_zone):
        """A death is a death, whichever step produced it.

        Fertility is the seventh step and succession the fourth, so a mother
        who dies in childbirth arrives after the succession step has already
        run and, on the next tick, its `death_tick=current` filter no longer
        matches her. Without an explicit settlement here her estate is never
        distributed, her couple is never dissolved -- leaving a widower bound
        to a dead partner and unable to re-pair -- and no DEATH event is
        emitted, so she never appears in the crude death rate.
        """
        sim, zone = sim_with_zone
        mother = _agent(sim, zone, "Madre", age=25, wealth=500.0)
        father = _agent(sim, zone, "Padre", gender=Agent.Gender.MALE, age=27)
        heir = _agent(sim, zone, "Erede", age=4, wealth=0.0, parent_agent=mother)
        couple = form_couple(mother, father, formed_at_tick=sim.current_tick - 1)
        context = _context(sim)

        orchestrator.run_fertility_step(
            context,
            rng=_ScriptedRandom([BIRTH_HAPPENS, MOTHER_DIES, NEWBORN_SURVIVES]),
        )

        mother.refresh_from_db()
        heir.refresh_from_db()
        couple.refresh_from_db()
        assert mother.is_alive is False
        assert DemographyEvent.objects.filter(
            simulation=sim,
            event_type=DemographyEvent.EventType.DEATH,
            primary_agent=mother,
        ).exists(), "no DEATH event for a mother who died in childbirth"
        assert heir.wealth > 0.0, "her estate was never settled"
        assert couple.dissolved_at_tick == context.tick, "her couple was never dissolved"

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


class TestPreloadedValuesReachTheNewborn:
    """The preloads must carry the RIGHT value, not merely the right count.

    The per-birth N+1 was closed by hoisting two reads out of the loop: the
    mother's partner, and her zone's mean class rank. The guard added with
    that fix measures the query COUNT, and a query count is blind to which
    value a preload produced -- measured, handing every newborn of the tick
    an arbitrary father from the preloaded map left 880 demography tests of
    880 green. These are the witnesses for the values.
    """

    def test_each_newborn_gets_its_own_mothers_partner(self, sim_with_zone):
        """Several couples, and the mother on both sides of the pair.

        `Couple` stores its two agents in canonical id order, not by sex, so
        the mother is in `agent_a` for some couples and `agent_b` for others
        and a mapping built from one column alone is wrong for half the
        population. Three couples with the mother on both sides separate that
        case; a single couple could not, and neither could three couples that
        all put her on the same side.
        """
        from epocha.apps.demography.models import Couple

        sim, zone = sim_with_zone
        expected = {}
        for i in range(3):
            # `form_couple` routes both partners through `_ordered_pair`, which
            # sorts by id to satisfy the model's canonical-ordering constraint,
            # so the argument order at the call site decides NOTHING. Which
            # column the mother lands in is decided by which agent is created
            # first, and creating her first every time -- as the first version
            # of this test did -- puts her in `agent_a` for all three couples
            # and makes the alternation inert. Measured: with that fixture,
            # dropping the `agent_b` side of the mapping left all 22 tests in
            # this file green.
            if i % 2:
                mother = _agent(sim, zone, f"Madre{i}", age=25)
                father = _agent(sim, zone, f"Padre{i}", gender=Agent.Gender.MALE, age=27)
            else:
                father = _agent(sim, zone, f"Padre{i}", gender=Agent.Gender.MALE, age=27)
                mother = _agent(sim, zone, f"Madre{i}", age=25)
            form_couple(mother, father, formed_at_tick=sim.current_tick - 1)
            expected[mother.id] = father.id

        # The fixture asserts its own shape, because a fixture that silently
        # stops building the case it claims is the defect this file keeps
        # paying for.
        mothers = list(expected)
        assert Couple.objects.filter(simulation=sim, agent_a_id__in=mothers).exists(), (
            "no mother was stored in agent_a: the fixture no longer covers that column"
        )
        assert Couple.objects.filter(simulation=sim, agent_b_id__in=mothers).exists(), (
            "no mother was stored in agent_b: the fixture no longer covers that column, "
            "so a mapping reading agent_a alone would pass"
        )
        context = _context(sim)

        orchestrator.run_fertility_step(
            context,
            rng=_ScriptedRandom([BIRTH_HAPPENS, MOTHER_SURVIVES] * 3),
        )

        newborns = list(Agent.objects.filter(simulation=sim, birth_tick=context.tick))
        assert len(newborns) == 3, "the scripted stream did not force three births"
        for newborn in newborns:
            assert newborn.other_parent_agent_id == expected[newborn.parent_agent_id], (
                f"{newborn.name} was given agent {newborn.other_parent_agent_id} as a "
                f"father, but its mother's partner is {expected[newborn.parent_agent_id]}"
            )

    def test_an_unpartnered_mother_gets_no_father(self, sim_with_zone):
        """The other side, so the resolution cannot answer by always
        returning somebody. Under an era that admits unpartnered birth, a
        mother with no couple must produce a newborn with no second parent.
        """
        sim, zone = sim_with_zone
        alone = _agent(sim, zone, "Sola", age=26)
        partnered = _agent(sim, zone, "Accoppiata", age=27)
        form_couple(
            _agent(sim, zone, "Marito", gender=Agent.Gender.MALE, age=30),
            partnered,
            formed_at_tick=sim.current_tick - 1,
        )
        context = _context(sim, template_name="modern_democracy")

        orchestrator.run_fertility_step(
            context,
            rng=_ScriptedRandom([BIRTH_HAPPENS, MOTHER_SURVIVES] * 2),
        )

        by_mother = {
            a.parent_agent_id: a
            for a in Agent.objects.filter(simulation=sim, birth_tick=context.tick)
        }
        assert alone.id in by_mother, "the unpartnered mother did not give birth"
        assert by_mother[alone.id].other_parent_agent_id is None, (
            "a mother with no active couple was given a father: the resolution "
            "hands out somebody rather than her partner"
        )
        assert by_mother[partnered.id].other_parent_agent_id is not None

    def test_the_zone_class_mean_reaching_a_birth_is_that_zones_own(self, sim_with_zone):
        """The second preload, witnessed by value rather than by count.

        The mean class rank of the zone is what `apply_social_inheritance`
        consumes, so a fabricated value produces a plausible but wrong social
        class for every newborn and nothing sees it.

        TWO zones, each with a fertile mother, each with a different class
        composition, and both giving birth in the same tick. One zone cannot
        witness this: with a single entry in the per-zone cache, a resolution
        that reads the wrong entry reads the right one anyway. Measured -- a
        one-zone version of this test survived exactly that mutation.
        """
        from django.contrib.gis.geos import Point, Polygon

        from epocha.apps.demography.inheritance import compute_zone_class_mean
        from epocha.apps.world.models import World, Zone

        sim, rich = sim_with_zone
        poor = Zone.objects.create(
            world=World.objects.get(simulation=sim),
            name="ZonaPovera",
            zone_type="residential",
            boundary=Polygon.from_bbox((200, 200, 300, 300)),
            center=Point(250, 250),
        )

        mothers = {}
        for zone, label, klass, filler in (
            (rich, "Ricca", "wealthy", "working"),
            (poor, "Povera", "poor", "poor"),
        ):
            mother = _agent(sim, zone, f"Madre{label}", age=25, social_class=klass)
            form_couple(
                _agent(
                    sim, zone, f"Padre{label}", gender=Agent.Gender.MALE, age=28, social_class=klass
                ),
                mother,
                formed_at_tick=sim.current_tick - 1,
            )
            for i in range(4):
                _agent(
                    sim,
                    zone,
                    f"Riempitivo{label}{i}",
                    gender=Agent.Gender.MALE,
                    age=40,
                    social_class=filler,
                )
            mothers[mother.id] = zone

        context = _context(sim)
        expected = {z.id: compute_zone_class_mean(z) for z in (rich, poor)}
        assert expected[rich.id] != expected[poor.id], (
            "the two zones have the same mean class rank: reading the wrong "
            "zone would be invisible and this test would prove nothing"
        )

        seen = []
        real_build = orchestrator.build_newborn

        def _capturing(ctx, mother_arg, father, rng, zone_class_mean=None):
            seen.append((mother_arg.id, zone_class_mean))
            return real_build(ctx, mother_arg, father, rng, zone_class_mean=zone_class_mean)

        orchestrator.build_newborn = _capturing
        try:
            orchestrator.run_fertility_step(
                context,
                rng=_ScriptedRandom([BIRTH_HAPPENS, MOTHER_SURVIVES] * 2),
            )
        finally:
            orchestrator.build_newborn = real_build

        assert len(seen) == 2, f"expected a birth in each zone, got {len(seen)}"
        for mother_id, mean in seen:
            assert mean == expected[mothers[mother_id].id], (
                f"the birth to mother {mother_id} received the mean of another "
                "zone: the per-zone cache is being read by something other than "
                "the mother's own zone"
            )


class TestFertilityTransactionalBoundary:
    """The birth step writes up to four times and must not write partially.

    Dead mothers, their settlement, the newborn rows and the birth events are
    four separate writes. Without a boundary a failure at the last one leaves
    newborns in the database that no BIRTH event describes -- agents that
    exist demographically and not historically, which every downstream rate
    of the snapshot then miscounts in one direction and the event log in the
    other.
    """

    def test_a_failed_event_write_takes_the_newborns_with_it(self, sim_with_zone, monkeypatch):
        sim, zone = sim_with_zone
        mother = _agent(sim, zone, "Madre", age=25)
        father = _agent(sim, zone, "Padre", gender=Agent.Gender.MALE, age=27)
        form_couple(mother, father, formed_at_tick=sim.current_tick - 1)
        context = _context(sim)

        real_bulk_create = DemographyEvent.objects.bulk_create

        def _explode(objs, *args, **kwargs):
            objs = list(objs)
            if objs and objs[0].event_type == DemographyEvent.EventType.BIRTH:
                raise RuntimeError("birth event write failed")
            return real_bulk_create(objs, *args, **kwargs)

        monkeypatch.setattr(DemographyEvent.objects, "bulk_create", _explode)

        with pytest.raises(RuntimeError):
            orchestrator.run_fertility_step(
                context, rng=_ScriptedRandom([BIRTH_HAPPENS, MOTHER_SURVIVES])
            )

        assert not Agent.objects.filter(simulation=sim, birth_tick=context.tick).exists(), (
            "a newborn survived the failed event write: the step has no "
            "transactional boundary and an agent exists that no event records"
        )


class TestTheStepPersistsWhatItBuilt:
    """The step must not alter a newborn between building it and saving it.

    Measured on 2026-08-29 against the whole suite: eight corruptions applied
    inside `run_fertility_step` AFTER `build_newborn` returned -- the name,
    the gender, the sexual orientation, the eight scalar heritable traits
    halved, the social class, the education level, the wealth and the zone --
    left every test in the project green. `TestBirthOrchestrator` above does
    cover `build_newborn`, but it calls it directly, so it witnesses nothing
    about what the step does with the object it gets back.

    One test rather than eight, because all eight corruptions are the same
    defect wearing different clothes: the step overwriting its own producer.
    Witnessing the fields one at a time would also have forced a statistical
    assertion for gender and for orientation -- every era template draws
    heterosexual at 0.955 and the sex ratio is near even -- and a statistical
    witness for a deterministic defect is theatre.

    **The compared columns are derived from the model, never enumerated.**
    The first version of this test listed them in a hand-written tuple, and
    the round-5 gate measured that tuple already out of sync with the
    producer the day it was written: `personality`, `cunning`, `role` and
    `health` are all written on the newborn and none was compared, so wiping
    every newborn's inherited personality between building and saving left
    1719 tests of 1719 green. Deriving the set from
    `Agent._meta.concrete_fields` means a column added tomorrow is witnessed
    without anybody remembering to add it.

    What this does NOT witness, stated rather than left to be discovered: a
    corruption inside `build_newborn` itself, which is the subject of
    `TestBirthOrchestrator` and of the inheritance module's own audited tests.
    """

    # Excluded because they cannot match by construction, not because they do
    # not matter: `id` is unset until `bulk_create` assigns it, and
    # `created_at` is stamped at insert time.
    UNCOMPARABLE = frozenset({"id", "created_at"})

    def test_every_field_survives_the_trip_to_the_database(self, sim_with_zone, monkeypatch):
        from epocha.apps.demography import template_loader

        # The orientation draw needs an era that can contradict the
        # corruption. Measured: with the shipped templates this witness
        # SURVIVED `sexual_orientation = "heterosexual"`, because all five
        # draw heterosexual at 0.955, both newborns had drawn it already, and
        # the corruption overwrote a value with itself. A fixture that cannot
        # construct the case it claims is the defect this file keeps paying
        # for, so the distribution is replaced -- rather than a seed hunted
        # for a lucky draw. It is patched on the LOADER because
        # `apply_inheritance_at_birth` ignores the tick context's template and
        # loads its own from `simulation.config`.
        real_load = template_loader.load_template

        def _era_without_heterosexuality(name):
            era = copy.deepcopy(real_load(name))
            era["sexual_orientation_distribution"] = {"homosexual": 1.0}
            return era

        monkeypatch.setattr(template_loader, "load_template", _era_without_heterosexuality)

        fields = tuple(
            sorted(
                f.attname for f in Agent._meta.concrete_fields if f.attname not in self.UNCOMPARABLE
            )
        )
        # Named explicitly so the round-5 regression cannot come back quietly:
        # these five were written by the producer and absent from the tuple
        # the first version of this test compared.
        assert {"personality", "cunning", "role", "health", "location"} <= set(fields), (
            "the derived column set no longer covers the fields the round-5 gate found missing"
        )

        sim, first_zone = sim_with_zone
        second_zone = Zone.objects.create(
            world=World.objects.get(simulation=sim),
            name="SecondaZona",
            zone_type="residential",
            boundary=Polygon.from_bbox((200, 200, 300, 300)),
            center=Point(250, 250),
        )
        # Two zones and two paternal classes, because a fixture whose births
        # agree on a column cannot tell "the value of THIS newborn" from "a
        # constant". Measured on the one-zone, one-class version: assigning
        # every newborn the first candidate's zone, and pinning the social
        # class to the value both were going to inherit anyway, both left the
        # suite green.
        for zone, klass, edu in ((first_zone, "elite", 0.9), (second_zone, "poor", 0.1)):
            mother = _agent(
                sim, zone, f"Madre{klass}", age=25, social_class=klass, education_level=edu
            )
            father = _agent(
                sim,
                zone,
                f"Padre{klass}",
                gender=Agent.Gender.MALE,
                age=28,
                social_class=klass,
                education_level=edu,
            )
            form_couple(mother, father, formed_at_tick=sim.current_tick - 1)
        context = _context(sim)

        built = {}
        real_build = orchestrator.build_newborn

        def _capturing(ctx, mother_arg, father, rng, zone_class_mean=None):
            child = real_build(ctx, mother_arg, father, rng, zone_class_mean=zone_class_mean)
            built[mother_arg.id] = {f: getattr(child, f) for f in fields}
            return child

        orchestrator.build_newborn = _capturing
        try:
            orchestrator.run_fertility_step(
                context, rng=_ScriptedRandom([BIRTH_HAPPENS, MOTHER_SURVIVES] * 2)
            )
        finally:
            orchestrator.build_newborn = real_build

        assert len(built) == 2, f"expected two births, the step built {len(built)}"
        # The fixture asserts its own shape: without both of these the
        # comparison below cannot separate a per-newborn value from a
        # constant, and the witness goes inert without saying so.
        assert len({v["zone_id"] for v in built.values()}) == 2, (
            "both newborns were built in the same zone: the fixture no longer "
            "separates the mother's own zone from any zone"
        )
        assert len({v["social_class"] for v in built.values()}) == 2, (
            "both newborns inherited the same social class: a corruption "
            "pinning that column would overwrite the value with itself"
        )

        stored = {
            a.parent_agent_id: a
            for a in Agent.objects.filter(simulation=sim, birth_tick=context.tick)
        }
        assert set(stored) == set(built), "a newborn that was built was never persisted"
        for mother_id, expected in built.items():
            row = stored[mother_id]
            for field in fields:
                assert getattr(row, field) == expected[field], (
                    f"{field} of the newborn of mother {mother_id} is "
                    f"{getattr(row, field)!r} in the database but was "
                    f"{expected[field]!r} when the orchestrator built it: the "
                    "step altered the newborn after building it"
                )


class TestTheBirthEventDescribesItsOwnBirth:
    """Four properties of the BIRTH payload, none of which had a witness.

    Measured on 2026-08-29: pairing every event with `newborns[0]` and with
    `mothers_of_newborns[0]`, renaming the step to "mortality", and pinning
    `mother_died_in_childbirth` to False each left the whole suite green. A
    single birth cannot separate the pairing -- with one newborn `newborns[0]`
    IS the newborn -- so this runs two births, and one of the two mothers dies
    so the flag has both values to be wrong about.
    """

    def test_two_births_produce_two_correctly_paired_events(self, sim_with_zone):
        sim, zone = sim_with_zone
        survivor = _agent(sim, zone, "Sopravvive", age=25)
        form_couple(
            _agent(sim, zone, "PadreA", gender=Agent.Gender.MALE, age=28),
            survivor,
            formed_at_tick=sim.current_tick - 1,
        )
        dying = _agent(sim, zone, "MuoreInParto", age=26)
        form_couple(
            _agent(sim, zone, "PadreB", gender=Agent.Gender.MALE, age=29),
            dying,
            formed_at_tick=sim.current_tick - 1,
        )
        # Candidates are read in id order, so the survivor is resolved first
        # and the scripted stream below is aligned to that order. The fixture
        # asserts it rather than assuming it.
        assert survivor.id < dying.id, "the fixture no longer controls the resolution order"
        context = _context(sim)

        # Two draws for a birth whose mother lives, three when she dies:
        # `resolve_childbirth_event` only draws neonatal survival in the
        # branch where the mother died.
        orchestrator.run_fertility_step(
            context,
            rng=_ScriptedRandom(
                [BIRTH_HAPPENS, MOTHER_SURVIVES, BIRTH_HAPPENS, MOTHER_DIES, NEWBORN_SURVIVES]
            ),
        )

        events = list(
            DemographyEvent.objects.filter(
                simulation=sim, event_type=DemographyEvent.EventType.BIRTH
            ).select_related("primary_agent")
        )
        assert len(events) == 2, f"expected two birth events, found {len(events)}"

        by_mother = {e.secondary_agent_id: e for e in events}
        assert set(by_mother) == {survivor.id, dying.id}, (
            "the birth events do not name the two mothers who gave birth: "
            "they are all pointing at the same one"
        )
        for mother_id, event in by_mother.items():
            assert event.primary_agent.parent_agent_id == mother_id, (
                f"the event for mother {mother_id} names newborn "
                f"{event.primary_agent_id}, whose mother is "
                f"{event.primary_agent.parent_agent_id}"
            )
            assert event.payload["step_name"] == "fertility"
        assert by_mother[dying.id].payload["mother_died_in_childbirth"] is True
        assert by_mother[survivor.id].payload["mother_died_in_childbirth"] is False

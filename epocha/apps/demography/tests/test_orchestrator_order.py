"""Tests for the demography tick orchestrator: order, predicate, RNG stream.

The five demography modules are not commutative, and a wrong order produces a
credible population curve that no shallow test distinguishes: whoever dies at
tick T must not conceive at T, an estate settles after the death that caused
it, and a couple formed at T from an intent expressed at T-1 must be able to
conceive at T. Spec FR-003 therefore requires the order to be **data** rather
than a sequence of calls, so a test can read it and a test can permute it.

This module covers the declared order, the activation predicate (FR-008) and
the per-(tick, phase) RNG rule (FR-010). The ordering properties themselves are
proven by mutation further down, each by permuting the declared sequence.
"""

from __future__ import annotations

from dataclasses import replace

import pytest
from django.contrib.auth import get_user_model

from epocha.apps.demography import orchestrator
from epocha.apps.demography.template_loader import load_template
from epocha.apps.simulation.models import Simulation

User = get_user_model()


@pytest.fixture
def simulation(db):
    user = User.objects.create_user(
        email="orchestrator@epocha.dev",
        username="orchestratoruser",
        password="pass1234",
    )
    return Simulation.objects.create(
        name="OrchestratorTest",
        seed=2026,
        owner=user,
        current_tick=10,
    )


@pytest.fixture
def simulation_with_vital_events(db):
    """A population giving every randomness-consuming step real work.

    A fertile couple for the fertility step -- with `age` and `birth_tick`
    deliberately in disagreement, so nothing here can pass by reading the
    frozen column -- a zone for migration, and living agents for mortality.
    """
    from django.contrib.gis.geos import Point, Polygon

    from epocha.apps.agents.models import Agent
    from epocha.apps.demography.couple import form_couple
    from epocha.apps.world.models import Government, World, Zone

    user = User.objects.create_user(
        email="phases@epocha.dev", username="phasesuser", password="pass1234"
    )
    sim = Simulation.objects.create(
        name="PhasesTest",
        seed=2026,
        owner=user,
        current_tick=100,
        config={"demography_enabled": True},
    )
    world = World.objects.create(simulation=sim, stability_index=0.7)
    Government.objects.create(simulation=sim)
    zone = Zone.objects.create(
        world=world,
        name="PhasesZone",
        zone_type="residential",
        boundary=Polygon.from_bbox((0, 0, 100, 100)),
        center=Point(50, 50),
    )
    tick = sim.current_tick + 1

    def _agent(name, real_age, gender):
        return Agent.objects.create(
            simulation=sim,
            name=name,
            zone=zone,
            role="farmer",
            location=Point(50, 50),
            health=1.0,
            wealth=500.0,
            age=99,  # frozen column, deliberately wrong
            birth_tick=int(sim.current_tick - real_age * 365.0),
            education_level=0.4,
            social_class="working",
            gender=gender,
            personality={},
        )

    man = _agent("PhUomo", 32, Agent.Gender.MALE)
    woman = _agent("PhDonna", 28, Agent.Gender.FEMALE)
    form_couple(man, woman, formed_at_tick=sim.current_tick - 1)
    return sim, tick


class TestDeclaredOrder:
    def test_steps_are_data_not_a_call_sequence(self):
        """FR-003: the order is inspectable without reading a function body."""
        assert isinstance(orchestrator.DEMOGRAPHY_STEPS, tuple)
        assert orchestrator.DEMOGRAPHY_STEPS

    def test_indices_are_contiguous_from_one(self):
        indices = [step.index for step in orchestrator.DEMOGRAPHY_STEPS]

        assert indices == list(range(1, len(indices) + 1))

    def test_step_names_are_unique(self):
        names = [step.name for step in orchestrator.DEMOGRAPHY_STEPS]

        assert len(names) == len(set(names))

    def test_every_rng_phase_is_one_the_seeded_helper_admits(self):
        """A step that consumes randomness declares phases the RNG helper
        knows; a step that consumes none declares an empty tuple."""
        from epocha.apps.demography.rng import ALLOWED_PHASES

        for step in orchestrator.DEMOGRAPHY_STEPS:
            assert isinstance(step.rng_phases, tuple)
            for phase in step.rng_phases:
                assert phase in ALLOWED_PHASES

    def test_the_declared_phases_are_the_derived_ones(
        self, simulation_with_vital_events, monkeypatch
    ):
        """The declaration is held to the code, step by step.

        `rng_phases` had no production consumer and was wrong for two steps
        of eight -- separations and succession declared streams while
        consuming no randomness -- and the single-string shape could not even
        represent fertility, which derives two ("fertility" for the draws and
        "inheritance" for the newborns' attribute stream). Metadata nobody
        reads and nothing checks is exactly the kind of prose-only property
        this project keeps paying for, so the check is mechanical: every
        stream a step derives while running is recorded, and the recording
        must equal the declaration.

        The fixture gives every randomness-consuming step real work -- a
        fertile couple for fertility, a living population for mortality, a
        zone for migration -- because a step derives some streams only once
        it has something to do, and a step measured while idle proves only
        that idleness is cheap.
        """
        import epocha.apps.demography.rng as rng_module

        sim, tick = simulation_with_vital_events
        context = orchestrator.DemographyTickContext(
            simulation=sim,
            tick=tick,
            template=load_template("pre_industrial_christian"),
        )

        real_get_seeded_rng = rng_module.get_seeded_rng
        derived: list[str] = []

        def _recording(simulation, tick, phase):
            derived.append(phase)
            return real_get_seeded_rng(simulation, tick, phase=phase)

        monkeypatch.setattr(rng_module, "get_seeded_rng", _recording)
        monkeypatch.setattr(orchestrator, "get_seeded_rng", _recording)

        for step in orchestrator.DEMOGRAPHY_STEPS:
            derived.clear()
            step.run(context)
            assert tuple(dict.fromkeys(derived)) == step.rng_phases, (
                f"step {step.name!r} declares {step.rng_phases} and derived "
                f"{tuple(derived)}"
            )


class TestActivationPredicate:
    def test_absent_key_is_inactive(self, simulation):
        """FR-008: silence is not consent. A simulation that declares nothing
        must keep behaving exactly as it did before the wiring existed."""
        simulation.config = {}

        assert orchestrator.is_demography_enabled(simulation) is False

    def test_explicit_false_is_inactive(self, simulation):
        simulation.config = {"demography_enabled": False}

        assert orchestrator.is_demography_enabled(simulation) is False

    def test_explicit_true_is_active(self, simulation):
        simulation.config = {"demography_enabled": True}

        assert orchestrator.is_demography_enabled(simulation) is True

    def test_era_template_alone_does_not_activate(self, simulation):
        """The era template cannot serve as the predicate: seven production
        sites already apply `config.get("demography_template", <default>)`,
        so a simulation that declares nothing already behaves like one that
        declares the default, and the predicate that is needed does not exist.
        """
        simulation.config = {"demography_template": "pre_industrial_christian"}

        assert orchestrator.is_demography_enabled(simulation) is False

    def test_null_config_is_inactive(self, simulation):
        simulation.config = None

        assert orchestrator.is_demography_enabled(simulation) is False


class TestRngStream:
    def test_one_stream_per_tick_and_phase_is_shared(self, simulation):
        """FR-010: deriving one stream PER AGENT would satisfy the letter of
        'every call gets a seeded RNG' and hand every agent the same uniform
        draw, killing them in a block at an age threshold instead of
        independently. One stream, shared, is the rule migration.py applies.
        """
        stream = orchestrator.stream_for(simulation, tick=7, phase="mortality")

        draws = [stream.random() for _ in range(3)]

        assert len(set(draws)) == 3

    def test_same_tick_and_phase_reproduce_the_sequence(self, simulation):
        first = orchestrator.stream_for(simulation, tick=7, phase="mortality")
        second = orchestrator.stream_for(simulation, tick=7, phase="mortality")

        assert [first.random() for _ in range(3)] == [second.random() for _ in range(3)]

    def test_phases_do_not_share_a_sequence(self, simulation):
        mortality = orchestrator.stream_for(simulation, tick=7, phase="mortality")
        fertility = orchestrator.stream_for(simulation, tick=7, phase="fertility")

        assert mortality.random() != fertility.random()


# ---------------------------------------------------------------------------
# Ordering properties, each proven by permuting the declared order (SC-002).
#
# These are the tests the whole "order as data" design exists for. A wrong
# order produces a plausible population curve, so the only way to know the
# declared one is right is to swap two steps and watch a property break.
# ---------------------------------------------------------------------------


def _reordered(*, before: str, after: str):
    """Return DEMOGRAPHY_STEPS with `before` moved just after `after`."""
    steps = [s for s in orchestrator.DEMOGRAPHY_STEPS if s.name != before]
    moved = next(s for s in orchestrator.DEMOGRAPHY_STEPS if s.name == before)
    position = next(i for i, s in enumerate(steps) if s.name == after) + 1
    steps.insert(position, moved)
    return tuple(replace(s, index=i + 1) for i, s in enumerate(steps))


class TestDeclaredOrderIsTheRightOne:
    def test_mortality_precedes_fertility(self):
        """FR-004: whoever dies at T does not conceive at T."""
        names = [s.name for s in orchestrator.DEMOGRAPHY_STEPS]

        assert names.index("mortality") < names.index("fertility")

    def test_couple_steps_precede_fertility(self):
        """FR-005: a couple formed at T from an intent at T-1 must be able to
        conceive at T, or every birth is delayed by one tick across the whole
        population."""
        names = [s.name for s in orchestrator.DEMOGRAPHY_STEPS]

        assert names.index("couple_formation") < names.index("fertility")
        assert names.index("separations") < names.index("fertility")

    def test_separations_precede_formations(self):
        """FR-005a: one rule for every couple intent, applied symmetrically,
        and the couple state is coherent when formation reads it."""
        names = [s.name for s in orchestrator.DEMOGRAPHY_STEPS]

        assert names.index("separations") < names.index("couple_formation")

    def test_succession_follows_mortality(self):
        """FR-006: an estate settles after the death that caused it."""
        names = [s.name for s in orchestrator.DEMOGRAPHY_STEPS]

        assert names.index("mortality") < names.index("succession")

    def test_forced_migration_follows_mortality_and_succession(self):
        """FR-007: flight reads post-death population and post-succession
        wealth."""
        names = [s.name for s in orchestrator.DEMOGRAPHY_STEPS]

        assert names.index("mortality") < names.index("forced_migration")
        assert names.index("succession") < names.index("forced_migration")

    def test_the_counter_sits_between_succession_and_migration(self):
        """FR-011: the counter reads the post-succession wealth, and the
        trigger then reads the counter."""
        names = [s.name for s in orchestrator.DEMOGRAPHY_STEPS]

        assert names.index("succession") < names.index("starvation_counter")
        assert names.index("starvation_counter") < names.index("forced_migration")

    def test_the_snapshot_is_last(self):
        """FR-015: the snapshot describes the tick, so it is written once
        every mutation of that tick has happened."""
        assert orchestrator.DEMOGRAPHY_STEPS[-1].name == "population_snapshot"

    # The first version of the SC-002 proof built a permuted tuple and then
    # asserted on the tuple -- the assertion read the test's own input, no
    # edit to production code could turn it red, and the five plain index
    # assertions above already pinned everything it pinned. The executed
    # proofs live in `TestPermutedOrdersBreakObservably` below: the permuted
    # order RUNS, and the named property visibly breaks.


class TestPermutedOrdersBreakObservably:
    """SC-002 as the spec words it: swap two steps and watch a property break.

    Each test runs the SAME fixture twice, once under the declared order and
    once under a permuted one, through `run_demography_tick` itself -- not
    through a helper that inspects tuples. The declared run must satisfy the
    property and the permuted run must visibly violate it; a pair of runs
    that agree would mean the order is not load-bearing and the requirement
    pinning it is theatre.
    """

    def _world(self, label):
        from django.contrib.gis.geos import Point, Polygon

        from epocha.apps.agents.models import Agent
        from epocha.apps.demography.couple import form_couple
        from epocha.apps.world.models import Government, World, Zone

        user = User.objects.create_user(
            email=f"perm{label}@epocha.dev", username=f"permuser{label}", password="pass1234"
        )
        sim = Simulation.objects.create(
            name=f"PermTest{label}",
            seed=2026,
            owner=user,
            current_tick=200,
            config={"demography_enabled": True},
        )
        world = World.objects.create(simulation=sim, stability_index=0.7)
        Government.objects.create(simulation=sim)
        zone = Zone.objects.create(
            world=world,
            name=f"PermZone{label}",
            zone_type="residential",
            boundary=Polygon.from_bbox((0, 0, 100, 100)),
            center=Point(50, 50),
        )

        def _agent(name, real_age, gender, wealth=500.0):
            return Agent.objects.create(
                simulation=sim,
                name=name,
                zone=zone,
                role="farmer",
                location=Point(50, 50),
                health=1.0,
                wealth=wealth,
                age=99,  # frozen column, deliberately wrong (the recurring trap)
                birth_tick=int(sim.current_tick - real_age * 365.0),
                education_level=0.4,
                social_class="working",
                gender=gender,
                personality={},
            )

        from epocha.apps.agents.models import Agent as AgentModel

        mother = _agent("PermMadre", 28, AgentModel.Gender.FEMALE)
        father = _agent("PermPadre", 32, AgentModel.Gender.MALE)
        form_couple(mother, father, formed_at_tick=sim.current_tick - 1)
        return sim, mother, father

    class _AllDie:
        """Every mortality draw kills; fertility draws force one birth."""

        def random(self):
            return 0.0

        def gauss(self, mu, sigma):
            return mu

        def randrange(self, n):
            return 0

    class _ForcedBirth:
        """First draw forces the birth, second lets the mother survive it."""

        def __init__(self):
            self._draws = [0.0, 0.9]

        def random(self):
            return self._draws.pop(0) if self._draws else 1.0

        def gauss(self, mu, sigma):
            return mu

        def randrange(self, n):
            return 0

    def _run(self, sim, steps, monkeypatch, *, deadly_mortality, forced_birth):
        real_stream_for = orchestrator.stream_for

        def _scripted(simulation, tick, phase):
            if deadly_mortality and phase == "mortality":
                return self._AllDie()
            if forced_birth and phase == "fertility":
                return self._ForcedBirth()
            return real_stream_for(simulation, tick, phase)

        monkeypatch.setattr(orchestrator, "stream_for", _scripted)
        monkeypatch.setattr(orchestrator, "DEMOGRAPHY_STEPS", steps)
        try:
            orchestrator.run_demography_tick(sim, sim.current_tick + 1)
        finally:
            monkeypatch.undo()

    def test_a_dead_mother_conceives_when_fertility_precedes_mortality(self, db, monkeypatch):
        """FR-004 executed. Declared order: the mother dies at step 3 and the
        forced birth finds no living candidate. Mortality moved after
        fertility: the same draws produce a newborn whose mother is dead in
        the same tick -- the exact corpse-conception the requirement forbids.
        """
        from epocha.apps.agents.models import Agent

        declared_sim, _, _ = self._world("DeclaredFr004")
        self._run(
            declared_sim,
            orchestrator.DEMOGRAPHY_STEPS,
            monkeypatch,
            deadly_mortality=True,
            forced_birth=True,
        )
        assert not Agent.objects.filter(
            simulation=declared_sim, birth_tick=declared_sim.current_tick + 1
        ).exists(), "the declared order let a dead mother conceive"

        permuted_sim, _, _ = self._world("PermutedFr004")
        self._run(
            permuted_sim,
            _reordered(before="mortality", after="fertility"),
            monkeypatch,
            deadly_mortality=True,
            forced_birth=True,
        )
        newborns = Agent.objects.filter(
            simulation=permuted_sim, birth_tick=permuted_sim.current_tick + 1
        )
        assert newborns.exists(), (
            "the permuted order produced no birth: the fixture is not "
            "exercising the property and this proof is theatre"
        )
        mother = newborns.first().parent_agent
        mother.refresh_from_db()
        assert mother.is_alive is False, (
            "the permuted order's newborn has a living mother: the observable "
            "no longer distinguishes the two orders"
        )

    def _world_with_heir(self, label):
        """An elder with an estate and a living adult child: the heir ladder
        lands on the child, so a settled tick moves wealth and an unsettled
        one visibly does not. The elder is created first, so the scripted
        mortality stream's single killing draw lands on it by id order."""
        from django.contrib.gis.geos import Point, Polygon

        from epocha.apps.agents.models import Agent
        from epocha.apps.world.models import Government, World, Zone

        user = User.objects.create_user(
            email=f"perm{label}@epocha.dev", username=f"permuser{label}", password="pass1234"
        )
        sim = Simulation.objects.create(
            name=f"PermTest{label}",
            seed=2026,
            owner=user,
            current_tick=200,
            config={"demography_enabled": True},
        )
        world = World.objects.create(simulation=sim, stability_index=0.7)
        Government.objects.create(simulation=sim)
        zone = Zone.objects.create(
            world=world,
            name=f"PermZone{label}",
            zone_type="residential",
            boundary=Polygon.from_bbox((0, 0, 100, 100)),
            center=Point(50, 50),
        )

        def _agent(name, real_age, wealth, **kwargs):
            return Agent.objects.create(
                simulation=sim,
                name=name,
                zone=zone,
                role="farmer",
                location=Point(50, 50),
                health=1.0,
                wealth=wealth,
                age=99,  # frozen column, deliberately wrong (the recurring trap)
                birth_tick=int(sim.current_tick - real_age * 365.0),
                education_level=0.4,
                social_class="working",
                gender=Agent.Gender.MALE,
                personality={},
                **kwargs,
            )

        elder = _agent("PermAvo", 82, 800.0)
        heir = _agent("PermErede", 45, 50.0, parent_agent=elder)
        return sim, elder, heir

    class _FirstAgentDies:
        """The first mortality draw kills, everything after lets live; the
        cause draws are absorbed by fixed gauss/randrange values."""

        def __init__(self):
            self._draws = [0.0]

        def random(self):
            return self._draws.pop(0) if self._draws else 1.0

        def gauss(self, mu, sigma):
            return mu

        def randrange(self, n):
            return 0

    def test_a_death_goes_unsettled_when_succession_precedes_mortality(self, db, monkeypatch):
        """FR-006 executed. The DEATH event is emitted by the mortality step
        itself, so it cannot separate the two orders; what separates them is
        the settlement. Declared order: the elder dies at step 3 and step 4
        moves the estate to the heir -- an INHERITANCE_TRANSFER event exists
        and the heir's wealth grows. Mortality moved after succession: the
        settlement query runs before anyone has died, so the tick ends with
        a dead elder, an unmoved estate and no transfer -- the second-class
        death the childbirth fix of this branch already met once.
        """
        from epocha.apps.demography.models import DemographyEvent

        real_stream_for = orchestrator.stream_for

        def _scripted(simulation, tick, phase):
            if phase == "mortality":
                return self._FirstAgentDies()
            return real_stream_for(simulation, tick, phase)

        def _run(sim, steps):
            monkeypatch.setattr(orchestrator, "stream_for", _scripted)
            monkeypatch.setattr(orchestrator, "DEMOGRAPHY_STEPS", steps)
            try:
                orchestrator.run_demography_tick(sim, sim.current_tick + 1)
            finally:
                monkeypatch.undo()

        declared_sim, declared_elder, declared_heir = self._world_with_heir("DeclaredFr006")
        _run(declared_sim, orchestrator.DEMOGRAPHY_STEPS)
        declared_elder.refresh_from_db()
        declared_heir.refresh_from_db()
        assert declared_elder.is_alive is False, "nobody died: the fixture proves nothing"
        assert DemographyEvent.objects.filter(
            simulation=declared_sim,
            event_type=DemographyEvent.EventType.INHERITANCE_TRANSFER,
        ).exists(), "the declared order left the estate unsettled"
        assert declared_heir.wealth > 50.0, "the heir received nothing under the declared order"

        permuted_sim, permuted_elder, permuted_heir = self._world_with_heir("PermutedFr006")
        _run(permuted_sim, _reordered(before="mortality", after="succession"))
        permuted_elder.refresh_from_db()
        permuted_heir.refresh_from_db()
        assert permuted_elder.is_alive is False
        assert not DemographyEvent.objects.filter(
            simulation=permuted_sim,
            event_type=DemographyEvent.EventType.INHERITANCE_TRANSFER,
        ).exists(), (
            "succession running before mortality still settled the tick's "
            "dead: the settlement is no longer reading the declared order"
        )
        assert permuted_heir.wealth == 50.0


class TestBlockEntryPoint:
    def test_a_disabled_simulation_runs_no_step(self, simulation, monkeypatch):
        simulation.config = {}
        ran = []
        monkeypatch.setattr(
            orchestrator,
            "DEMOGRAPHY_STEPS",
            (
                replace(
                    orchestrator.DEMOGRAPHY_STEPS[0],
                    run=lambda context: ran.append("ran"),
                ),
            ),
        )

        orchestrator.run_demography_tick(simulation, tick=51)

        assert ran == []

    def test_an_enabled_simulation_runs_every_step_in_order(self, simulation, monkeypatch):
        simulation.config = {"demography_enabled": True}
        ran = []
        monkeypatch.setattr(
            orchestrator,
            "DEMOGRAPHY_STEPS",
            tuple(
                replace(step, run=lambda context, name=step.name: ran.append(name))
                for step in orchestrator.DEMOGRAPHY_STEPS
            ),
        )

        orchestrator.run_demography_tick(simulation, tick=51)

        assert ran == [step.name for step in orchestrator.DEMOGRAPHY_STEPS]

    def test_a_missing_template_degrades_instead_of_aborting_the_tick(
        self, simulation, monkeypatch
    ):
        simulation.config = {"demography_enabled": True, "demography_template": "does_not_exist"}
        ran = []
        monkeypatch.setattr(
            orchestrator,
            "DEMOGRAPHY_STEPS",
            (replace(orchestrator.DEMOGRAPHY_STEPS[0], run=lambda context: ran.append("ran")),),
        )

        orchestrator.run_demography_tick(simulation, tick=51)

        assert ran == []

    def test_an_invalid_template_degrades_too(self, simulation, monkeypatch):
        """A template that exists but fails schema validation is a different
        mistake from a missing file, and the engine's existing handler
        swallows it in a blind `except Exception`. This path names it."""
        simulation.config = {"demography_enabled": True}

        def _raise_value_error(name):
            raise ValueError(f"template {name} is invalid")

        monkeypatch.setattr(
            "epocha.apps.demography.template_loader.load_template", _raise_value_error
        )
        ran = []
        monkeypatch.setattr(
            orchestrator,
            "DEMOGRAPHY_STEPS",
            (replace(orchestrator.DEMOGRAPHY_STEPS[0], run=lambda context: ran.append("ran")),),
        )

        orchestrator.run_demography_tick(simulation, tick=51)

        assert ran == []

    def test_a_population_of_zero_does_not_raise(self, simulation):
        """When the last agent dies, the next tick must still complete.

        The world and its government exist -- what is empty is the
        population, which is the state this guards. A simulation with no
        world at all is a different failure and belongs to whoever creates
        simulations, not to the tick.
        """
        from django.contrib.gis.geos import Point, Polygon

        from epocha.apps.world.models import Government, World, Zone

        simulation.config = {"demography_enabled": True}
        simulation.save()
        world = World.objects.create(simulation=simulation, stability_index=0.7)
        Government.objects.create(simulation=simulation)
        Zone.objects.create(
            world=world,
            name="EmptyZone",
            zone_type="residential",
            boundary=Polygon.from_bbox((0, 0, 100, 100)),
            center=Point(50, 50),
        )

        orchestrator.run_demography_tick(simulation, tick=simulation.current_tick + 1)

        from epocha.apps.demography.models import DemographyEvent

        assert not DemographyEvent.objects.filter(simulation=simulation).exists()

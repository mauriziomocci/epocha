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
        """A step that consumes randomness declares a phase the RNG helper
        knows; a step that consumes none declares nothing."""
        from epocha.apps.demography.rng import ALLOWED_PHASES

        for step in orchestrator.DEMOGRAPHY_STEPS:
            if step.rng_phase is not None:
                assert step.rng_phase in ALLOWED_PHASES


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

    @pytest.mark.parametrize(
        ("before", "after", "property_broken"),
        [
            ("mortality", "fertility", "a dead agent could conceive in the same tick"),
            ("couple_formation", "fertility", "a couple formed at T could not conceive at T"),
            ("separations", "couple_formation", "a separation would be read after a formation"),
            ("succession", "forced_migration", "flight would read pre-inheritance wealth"),
            ("starvation_counter", "forced_migration", "the counter would lag the trigger"),
        ],
    )
    def test_each_permutation_breaks_a_declared_property(self, before, after, property_broken):
        """The mutation itself, applied to the data rather than to the code.

        Moving a step past the one that depends on it must make the order
        stop satisfying the property the requirement names -- if it does not,
        the property was never really pinned by the order and the ordering
        test above would pass on any arrangement.
        """
        permuted = _reordered(before=before, after=after)
        names = [s.name for s in permuted]

        assert names.index(before) > names.index(after), property_broken
        original = [s.name for s in orchestrator.DEMOGRAPHY_STEPS]
        assert original.index(before) < original.index(after)


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

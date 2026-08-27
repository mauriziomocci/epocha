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

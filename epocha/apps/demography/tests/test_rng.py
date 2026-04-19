"""Tests for the seeded per-subsystem RNG streams."""
from __future__ import annotations

import pytest

from epocha.apps.demography.rng import ALLOWED_PHASES, get_seeded_rng
from epocha.apps.simulation.models import Simulation
from epocha.apps.users.models import User


@pytest.fixture
def sim(db):
    user = User.objects.create_user(
        email="rng@epocha.dev", username="rnguser", password="pass1234",
    )
    return Simulation.objects.create(name="RngTest", seed=42, owner=user, current_tick=0)


@pytest.mark.django_db
def test_same_inputs_produce_same_sequence(sim):
    rng1 = get_seeded_rng(sim, tick=1, phase="mortality")
    rng2 = get_seeded_rng(sim, tick=1, phase="mortality")
    seq1 = [rng1.random() for _ in range(10)]
    seq2 = [rng2.random() for _ in range(10)]
    assert seq1 == seq2


@pytest.mark.django_db
def test_different_phases_produce_independent_streams(sim):
    rng_mort = get_seeded_rng(sim, tick=1, phase="mortality")
    rng_fert = get_seeded_rng(sim, tick=1, phase="fertility")
    seq_mort = [rng_mort.random() for _ in range(10)]
    seq_fert = [rng_fert.random() for _ in range(10)]
    assert seq_mort != seq_fert


@pytest.mark.django_db
def test_different_ticks_produce_different_streams(sim):
    rng_t1 = get_seeded_rng(sim, tick=1, phase="mortality")
    rng_t2 = get_seeded_rng(sim, tick=2, phase="mortality")
    assert rng_t1.random() != rng_t2.random()


@pytest.mark.django_db
def test_unknown_phase_raises(sim):
    with pytest.raises(ValueError):
        get_seeded_rng(sim, tick=1, phase="not_a_real_phase")


@pytest.mark.django_db
def test_all_allowed_phases_accepted(sim):
    for phase in ALLOWED_PHASES:
        assert get_seeded_rng(sim, tick=1, phase=phase) is not None

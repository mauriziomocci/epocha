"""Two newborns in one tick must not receive identical drawn attributes.

Spec SC-006, and the one defect in merged code this work item corrects.

`apply_inheritance_at_birth` used to re-derive its RNG stream inside the
function from `(simulation, tick, "inheritance")` and to consume a draw count
that does not depend on the parents: `len(heritability)` gauss draws fixed by
the template, one per trait on every branch by explicit declaration, then
exactly two `rng.random()` calls for sex and orientation. Two newborns in the
same tick therefore started at the same offset of the same sequence and came
out with identical sex and orientation, and identical residuals on every
trait. That is arithmetic on the draw count, not a hypothesis.

The defect was invisible while nothing created newborns. The birth
orchestrator makes it certain, which is why the correction belongs here and
not to a later work item.

The fix follows FR-010: one stream per `(tick, phase)`, derived once by the
caller and threaded through the newborns in a deterministic iteration order,
exactly the rule `migration.py` already applies to its own per-agent loop.
Reproducibility is preserved and is proven below in the way it should be —
by replaying the same stream, not by handing two different children the same
draws.
"""

from __future__ import annotations

import pytest

from epocha.apps.demography.inheritance import apply_inheritance_at_birth
from epocha.apps.demography.rng import get_seeded_rng
from epocha.apps.demography.tests.test_inheritance import (  # reused fixtures
    PERSONALITY_HERITABLE_TRAITS,
    SCALAR_HERITABLE_TRAITS,
    _make_agent,
    sim_with_zone,  # noqa: F401  (pytest fixture, imported for reuse)
)


def _parents(sim, zone, suffix):
    mother = _make_agent(
        sim,
        zone,
        f"Mother{suffix}",
        social_class="wealthy",
        education_level=0.6,
        personality={name: 0.6 for name in PERSONALITY_HERITABLE_TRAITS},
        **{name: 0.6 for name in SCALAR_HERITABLE_TRAITS},
    )
    father = _make_agent(
        sim,
        zone,
        f"Father{suffix}",
        social_class="middle",
        education_level=0.4,
        personality={name: 0.4 for name in PERSONALITY_HERITABLE_TRAITS},
        **{name: 0.4 for name in SCALAR_HERITABLE_TRAITS},
    )
    return mother, father


@pytest.mark.django_db
def test_two_newborns_in_one_tick_are_not_systematically_identical(sim_with_zone):  # noqa: F811
    """SC-006 on the sampled attributes, at a sample size where the old
    behaviour is impossible to reach by chance.

    Sixteen births share one tick's stream. Under the defect every one of
    them received the same sex and the same orientation; drawing sixteen
    identical sexes from a near-even split has probability below 1e-4, so a
    single differing pair is enough to separate the two implementations
    while staying immune to a lucky seed.
    """
    sim, zone = sim_with_zone
    mother, father = _parents(sim, zone, "Shared")
    rng = get_seeded_rng(sim, sim.current_tick, phase="inheritance")

    children = []
    for i in range(16):
        child = _make_agent(sim, zone, f"Child{i}")
        apply_inheritance_at_birth(child, mother, father, sim, sim.current_tick, rng)
        children.append(child)

    genders = {child.gender for child in children}
    orientations = {child.sexual_orientation for child in children}
    trait_values = {
        tuple(getattr(child, name) for name in SCALAR_HERITABLE_TRAITS) for child in children
    }

    assert len(genders) > 1 or len(orientations) > 1, (
        "sixteen newborns sharing one tick received the same sex and the same "
        "orientation: the stream is being restarted per call"
    )
    assert len(trait_values) == 16, "newborns received identical trait residuals"


@pytest.mark.django_db
def test_replaying_the_same_stream_reproduces_the_child(sim_with_zone):  # noqa: F811
    """Reproducibility, proven the way it actually holds.

    The property worth having is that one run, replayed from the same seed
    and tick, produces the same child — not that two different children in
    one tick receive the same draws, which is the defect wearing the mask of
    determinism. Two streams derived from the same `(simulation, tick,
    phase)` are the same sequence, so the first child of each run matches.
    """
    sim, zone = sim_with_zone
    mother, father = _parents(sim, zone, "Replay")

    first_run = _make_agent(sim, zone, "FirstRun")
    apply_inheritance_at_birth(
        first_run,
        mother,
        father,
        sim,
        sim.current_tick,
        get_seeded_rng(sim, sim.current_tick, phase="inheritance"),
    )

    second_run = _make_agent(sim, zone, "SecondRun")
    apply_inheritance_at_birth(
        second_run,
        mother,
        father,
        sim,
        sim.current_tick,
        get_seeded_rng(sim, sim.current_tick, phase="inheritance"),
    )

    assert first_run.gender == second_run.gender
    assert first_run.sexual_orientation == second_run.sexual_orientation
    for name in SCALAR_HERITABLE_TRAITS:
        assert getattr(first_run, name) == getattr(second_run, name), name
    for name in PERSONALITY_HERITABLE_TRAITS:
        assert first_run.personality[name] == second_run.personality[name], name


@pytest.mark.django_db
def test_the_stream_is_the_callers_to_own(sim_with_zone):  # noqa: F811
    """The RNG is a required argument, not an optional convenience.

    An optional parameter falling back to an internally derived stream would
    leave the defect alive for every caller that forgets it, and would give
    the subsystem two ways to do one thing. FR-010 puts the stream in the
    caller's hands precisely so the per-tick sharing is visible at the call
    site.
    """
    sim, zone = sim_with_zone
    mother, father = _parents(sim, zone, "NoRng")
    child = _make_agent(sim, zone, "ChildNoRng")

    # `match` is load-bearing: a bare `pytest.raises(TypeError)` is satisfied
    # by ANY TypeError, so making `rng` optional and adding a second required
    # keyword-only argument would leave this green while the defect returned.
    with pytest.raises(TypeError, match="rng"):
        apply_inheritance_at_birth(child, mother, father, sim, sim.current_tick)

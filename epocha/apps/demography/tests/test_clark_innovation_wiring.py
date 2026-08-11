"""The Clark rule must consume the calibrated innovation (amendment A3).

The calibration module solves the amplitude; this file asserts the RULE uses
it. Splitting the two matters because the solver can be perfectly correct
while nothing calls it, which is the failure phase 2.2 found for the
education mean one field over.
"""

from __future__ import annotations

import pytest
from django.contrib.gis.geos import Point, Polygon

from epocha.apps.demography.clark_calibration import (
    CLARK_PERSISTENCE,
    solve_clark_innovation,
)
from epocha.apps.demography.inheritance import apply_social_inheritance
from epocha.apps.simulation.models import Simulation
from epocha.apps.users.models import User
from epocha.apps.world.models import World, Zone

from .test_inheritance import _make_agent


@pytest.fixture
def sim_with_zone(db):
    user = User.objects.create_user(
        email="clark@epocha.dev", username="clarkuser", password="pass1234"
    )
    sim = Simulation.objects.create(name="ClarkTest", seed=1, owner=user, current_tick=0)
    world = World.objects.create(simulation=sim, stability_index=0.7)
    zone = Zone.objects.create(
        world=world,
        name="ClarkZone",
        zone_type="commercial",
        boundary=Polygon.from_bbox((0, 0, 100, 100)),
        center=Point(50, 50),
    )
    return sim, zone


def _template(target_dispersion: float = 1.0) -> dict:
    return {
        "social_inheritance": {
            "class_rule": "clark_regression",
            "education_regression_rho": 0.5,
            "era_noise": {
                "education": {"era_mean": 0.30, "era_sd": 0.15},
                "class_rank": {"target_dispersion": target_dispersion},
            },
        }
    }


class _ScriptedDraws:
    """Returns a fixed number of sigmas, and records every sigma it was asked for.

    Recording the sigma is the point: it is how a test can tell the CALIBRATED
    amplitude from any other number without re-deriving it.
    """

    def __init__(self, z: float = 0.0) -> None:
        self.z = z
        self.sigmas: list[float] = []

    def gauss(self, mu: float, sigma: float) -> float:
        self.sigmas.append(sigma)
        return mu + sigma * self.z


@pytest.mark.django_db
class TestTheRuleDrawsAtAll:
    """Before A3 the rule consumed no randomness, and froze."""

    def test_a_draw_is_consumed_by_the_class_rule(self, sim_with_zone):
        sim, zone = sim_with_zone
        mother = _make_agent(sim, zone, "Mother", social_class="middle")
        father = _make_agent(sim, zone, "Father", social_class="middle")
        child = _make_agent(sim, zone, "Child")
        rng = _ScriptedDraws()
        apply_social_inheritance(child, mother, father, _template(), 2.0, rng)
        # education draws once; the class rule must add its own
        assert len(rng.sigmas) >= 2, "clark_regression must draw its innovation"

    def test_two_draws_can_land_the_same_parents_in_different_classes(self, sim_with_zone):
        """The defect, stated as a test: a deterministic rule cannot do this."""
        sim, zone = sim_with_zone
        mother = _make_agent(sim, zone, "Mother", social_class="middle")
        father = _make_agent(sim, zone, "Father", social_class="middle")
        low = _make_agent(sim, zone, "Low")
        high = _make_agent(sim, zone, "High")
        apply_social_inheritance(low, mother, father, _template(), 2.0, _ScriptedDraws(-2.0))
        apply_social_inheritance(high, mother, father, _template(), 2.0, _ScriptedDraws(2.0))
        assert low.social_class != high.social_class


@pytest.mark.django_db
class TestTheAmplitudeIsTheCalibratedOne:
    """SC-012a at the call site: the sigma handed to the draw is the root."""

    def test_the_class_draw_uses_the_solved_amplitude(self, sim_with_zone):
        sim, zone = sim_with_zone
        mother = _make_agent(sim, zone, "Mother", social_class="middle")
        father = _make_agent(sim, zone, "Father", social_class="middle")
        child = _make_agent(sim, zone, "Child")
        rng = _ScriptedDraws()
        apply_social_inheritance(child, mother, father, _template(1.0), 2.0, rng)
        assert rng.sigmas[-1] == pytest.approx(solve_clark_innovation(1.0), rel=1e-12)

    def test_a_different_declared_target_changes_the_amplitude(self, sim_with_zone):
        """The template value must reach the solver, not a constant.

        1.0 is what every shipped era declares, so a hardcoded amplitude
        passes the test above and fails only here.
        """
        sim, zone = sim_with_zone
        mother = _make_agent(sim, zone, "Mother", social_class="middle")
        father = _make_agent(sim, zone, "Father", social_class="middle")
        seen = []
        for target in (1.0, 1.2):
            child = _make_agent(sim, zone, f"Child{target}")
            rng = _ScriptedDraws()
            apply_social_inheritance(child, mother, father, _template(target), 2.0, rng)
            seen.append(rng.sigmas[-1])
            assert seen[-1] == pytest.approx(solve_clark_innovation(target), rel=1e-12)
        assert seen[0] != seen[1]

    def test_the_amplitude_is_not_the_naive_identity_reading(self, sim_with_zone):
        """`s_rank * sqrt(1 - b^2)` is the continuous-scale answer and lands
        at 102.26% of the target once rounding and clamping bite."""
        sim, zone = sim_with_zone
        mother = _make_agent(sim, zone, "Mother", social_class="middle")
        father = _make_agent(sim, zone, "Father", social_class="middle")
        child = _make_agent(sim, zone, "Child")
        rng = _ScriptedDraws()
        apply_social_inheritance(child, mother, father, _template(1.0), 2.0, rng)
        naive = 1.0 * (1.0 - CLARK_PERSISTENCE**2) ** 0.5
        assert rng.sigmas[-1] != pytest.approx(naive, rel=1e-3)


@pytest.mark.django_db
class TestTheDeterministicPartIsUnchanged:
    """A3 adds an innovation; it does not retune the 70/30 weighting."""

    def test_a_zero_draw_reproduces_the_previous_rule(self, sim_with_zone):
        """With the residual at zero the rule must give exactly what the
        deterministic weighting gave, so the correction is additive and not a
        silent retune of a coefficient the amendment leaves alone."""
        sim, zone = sim_with_zone
        for parent_class, zone_mean, expected in (
            ("elite", 2.0, "wealthy"),  # 0.7*0 + 0.3*2 = 0.6 -> rank 1
            ("middle", 2.0, "middle"),  # 0.7*2 + 0.3*2 = 2.0 -> rank 2
            ("poor", 2.0, "working"),  # 0.7*4 + 0.3*2 = 3.4 -> rank 3
        ):
            mother = _make_agent(sim, zone, f"M{parent_class}", social_class=parent_class)
            father = _make_agent(sim, zone, f"F{parent_class}", social_class=parent_class)
            child = _make_agent(sim, zone, f"C{parent_class}")
            apply_social_inheritance(
                child, mother, father, _template(), zone_mean, _ScriptedDraws(0.0)
            )
            assert child.social_class == expected


@pytest.mark.django_db
class TestMobilityIsNoLongerZero:
    """SC-012's sanity check at the call site, over a synthetic population."""

    def test_children_of_identical_parents_do_not_all_share_one_class(self, sim_with_zone):
        import random

        sim, zone = sim_with_zone
        mother = _make_agent(sim, zone, "Mother", social_class="middle")
        father = _make_agent(sim, zone, "Father", social_class="middle")
        rng = random.Random(20260811)
        child = _make_agent(sim, zone, "Child")
        labels = set()
        for _ in range(200):
            apply_social_inheritance(child, mother, father, _template(), 2.0, rng)
            labels.add(child.social_class)
        assert len(labels) > 1, "a deterministic rule puts every child in one class"

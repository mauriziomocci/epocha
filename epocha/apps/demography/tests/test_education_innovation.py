"""FR-002b for education: the regression must carry an innovation term.

The defect: `_regress_education_level` was a pure deterministic contraction
toward the era mean, with no random component at all. Its fixed point is not
a reduced dispersion but ZERO. Measured on twenty thousand agents over eight
generations from a starting dispersion of 0.150, at the coefficients the five
templates actually ship:

    rho = 0.5 (both pre-industrial eras)   0.0187 -> 0.0023 -> 0.00004
    rho = 0.4 (industrial, modern)         0.0121 -> 0.0010 -> 0.00001
    rho = 0.2 (sci-fi)                     0.0030 -> 0.0001 -> 0.000000

Every agent converges on the era mean, so education becomes a constant. The
consequences propagate: the meritocratic class rule computes merit as the
mean of intelligence and education, and the homogamy score weights education
between 0.25 and 0.40 depending on the era, so between a quarter and two
fifths of the mating criterion switches off.

Amendment A3 gives education the same treatment as the traits: same family,
same three kinship branches, residual scaled by the same variance identity.
That is not an analogy - it is literally the same kernel, so this module
tests that education goes THROUGH it rather than reimplementing it beside it.
"""

from __future__ import annotations

import math
import random
import statistics

import pytest
from django.contrib.gis.geos import Point, Polygon

from epocha.apps.demography.inheritance import apply_social_inheritance
from epocha.apps.simulation.models import Simulation
from epocha.apps.users.models import User
from epocha.apps.world.models import World, Zone

from .test_inheritance import _make_agent

ERA_MEAN_EDU = 0.30
ERA_SD_EDU = 0.15


@pytest.fixture
def sim_with_zone(db):
    user = User.objects.create_user(email="edu@epocha.dev", username="eduuser", password="pass1234")
    sim = Simulation.objects.create(name="EduTest", seed=1, owner=user, current_tick=0)
    world = World.objects.create(simulation=sim, stability_index=0.7)
    zone = Zone.objects.create(
        world=world,
        name="EduZone",
        zone_type="commercial",
        boundary=Polygon.from_bbox((0, 0, 100, 100)),
        center=Point(50, 50),
    )
    return sim, zone


def _template(rho: float, era_mean: float = ERA_MEAN_EDU, era_sd: float = ERA_SD_EDU) -> dict:
    return {
        "social_inheritance": {
            "class_rule": "patrilineal_rigid",
            "education_regression_rho": rho,
            "era_noise": {
                "education": {"era_mean": era_mean, "era_sd": era_sd},
                "class_rank": {"target_dispersion": 1.0},
            },
        }
    }


class _FixedDraw:
    """Returns a caller-chosen number of sigmas from whatever it is asked for."""

    def __init__(self, z: float = 0.0) -> None:
        self.z = z
        self.calls = 0

    def gauss(self, mu: float, sigma: float) -> float:
        self.calls += 1
        return mu + sigma * self.z


@pytest.mark.django_db
class TestEducationDrawsAnInnovation:
    """The regression must consume randomness. Before A3 it consumed none."""

    def test_a_draw_is_consumed(self, sim_with_zone):
        sim, zone = sim_with_zone
        child = _make_agent(sim, zone, "Child")
        rng = _FixedDraw()
        apply_social_inheritance(child, None, None, _template(0.6), 2.0, rng)
        assert rng.calls >= 1, "education must draw; a deterministic contraction goes to zero"

    def test_two_different_draws_give_two_different_children(self, sim_with_zone):
        """Same parents, different randomness, different outcome.

        A deterministic contraction returns the same value for both and fails
        here - which is the whole defect, stated as a test.
        """
        sim, zone = sim_with_zone
        mother = _make_agent(sim, zone, "Mother", education_level=0.5)
        father = _make_agent(sim, zone, "Father", education_level=0.5)
        low = _make_agent(sim, zone, "Low")
        high = _make_agent(sim, zone, "High")
        apply_social_inheritance(low, mother, father, _template(0.6), 2.0, _FixedDraw(-1.0))
        apply_social_inheritance(high, mother, father, _template(0.6), 2.0, _FixedDraw(1.0))
        assert low.education_level != high.education_level


@pytest.mark.django_db
class TestEducationUsesTheAmendedKernel:
    """Same three branches and same residual scales as the traits.

    A3 says education receives the treatment of A1. These pin the coefficients
    exactly rather than by sampling, for the reason the amendment gives: a band
    on realized dispersion does not separate a correct kernel from one whose
    residual is mis-scaled.
    """

    @staticmethod
    def _residual_scale(rho: float, parents: int) -> float:
        if parents == 2:
            return math.sqrt(1.0 - rho**2 / 2.0)
        if parents == 1:
            return math.sqrt(1.0 - rho**2 / 4.0)
        return 1.0

    @pytest.mark.parametrize("rho", [0.2, 0.4, 0.5, 0.6])
    @pytest.mark.parametrize("parents", [2, 1, 0])
    def test_residual_scale_matches_the_variance_identity(self, sim_with_zone, rho, parents):
        sim, zone = sim_with_zone
        mother = _make_agent(sim, zone, "M", education_level=ERA_MEAN_EDU) if parents >= 1 else None
        father = _make_agent(sim, zone, "F", education_level=ERA_MEAN_EDU) if parents == 2 else None

        results = []
        for z in (1.0, -1.0):
            child = _make_agent(sim, zone, f"C{z}")
            apply_social_inheritance(child, mother, father, _template(rho), 2.0, _FixedDraw(z))
            results.append(child.education_level)
        assert all(0.0 < value < 1.0 for value in results), "probe must stay interior"

        measured = (results[0] - results[1]) / (2.0 * ERA_SD_EDU)
        assert measured == pytest.approx(self._residual_scale(rho, parents), rel=1e-12)

    @pytest.mark.parametrize("rho", [0.2, 0.4, 0.6])
    def test_single_parent_signal_is_half_the_two_parent_one(self, sim_with_zone, rho):
        sim, zone = sim_with_zone

        def child_for(parents: int, parent_edu: float) -> float:
            mother = _make_agent(sim, zone, f"M{parents}{parent_edu}", education_level=parent_edu)
            father = (
                _make_agent(sim, zone, f"F{parents}{parent_edu}", education_level=parent_edu)
                if parents == 2
                else None
            )
            child = _make_agent(sim, zone, f"C{parents}{parent_edu}")
            apply_social_inheritance(child, mother, father, _template(rho), 2.0, _FixedDraw(0.0))
            return child.education_level

        two = (child_for(2, 0.5) - child_for(2, 0.1)) / 0.4
        one = (child_for(1, 0.5) - child_for(1, 0.1)) / 0.4
        assert one == pytest.approx(two / 2.0, rel=1e-12)
        assert two == pytest.approx(rho, rel=1e-12)

    @pytest.mark.parametrize("era_sd", [0.05, 0.09, 0.12])
    def test_the_declared_amplitude_governs_and_not_a_constant(self, sim_with_zone, era_sd):
        """The declared education amplitude must reach the draw.

        Every other test in this file declares 0.15, which is also the trait
        fallback, so an implementation hardcoding that constant passes them
        all -- the same blind spot phase 2.2 found for the education MEAN,
        reappearing one field over. These amplitudes differ from it.
        """
        sim, zone = sim_with_zone
        rho = 0.6
        template = _template(rho, era_sd=era_sd)
        results = []
        for z in (1.0, -1.0):
            child = _make_agent(sim, zone, f"C{era_sd}{z}")
            apply_social_inheritance(child, None, None, template, 2.0, _FixedDraw(z))
            results.append(child.education_level)
        # no parent, so the residual scale is 1 and the displacement IS era_sd
        assert (results[0] - results[1]) / 2.0 == pytest.approx(era_sd, rel=1e-12)
        assert era_sd != ERA_SD_EDU, "the probe must differ from the value used elsewhere"

    def test_no_parent_child_resolves_to_the_declared_mean(self, sim_with_zone):
        sim, zone = sim_with_zone
        child = _make_agent(sim, zone, "Child")
        apply_social_inheritance(child, None, None, _template(0.6), 2.0, _FixedDraw(0.0))
        assert child.education_level == pytest.approx(ERA_MEAN_EDU)


@pytest.mark.django_db
class TestEducationDispersionSurvives:
    """SC-011 as the amendment restates it: the fixed point is not zero.

    The pre-amendment kernel reached 0.00004 of a 0.150 starting dispersion in
    eight generations at the highest shipped coefficient, and exact zero at the
    lowest. This is the integration check behind the exact probes above.
    """

    @pytest.mark.parametrize("rho", [0.2, 0.5, 0.6])
    def test_dispersion_holds_over_eight_generations(self, sim_with_zone, rho):
        sim, zone = sim_with_zone
        rng = random.Random(20260811)
        template = _template(rho)
        population = [min(1.0, max(0.0, rng.gauss(ERA_MEAN_EDU, ERA_SD_EDU))) for _ in range(4000)]

        mother = _make_agent(sim, zone, "M")
        father = _make_agent(sim, zone, "F")
        child = _make_agent(sim, zone, "C")
        for _ in range(8):
            shuffled = list(population)
            rng.shuffle(shuffled)
            half = len(shuffled) // 2
            children = []
            for m_edu, f_edu in zip(shuffled[:half], shuffled[half : 2 * half]):
                mother.education_level = m_edu
                father.education_level = f_edu
                apply_social_inheritance(child, mother, father, template, 2.0, rng)
                children.append(child.education_level)
            population = children * 2

        realized = statistics.pstdev(population)
        # The pre-amendment kernel measured below 0.0001 here; the amendment's
        # own criterion is at least half the starting dispersion.
        assert realized > 0.5 * ERA_SD_EDU
        # and it must land near the declared amplitude, not merely above a floor
        assert realized == pytest.approx(ERA_SD_EDU, rel=0.15)

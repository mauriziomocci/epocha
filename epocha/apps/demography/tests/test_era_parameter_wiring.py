"""FR-004: the declared per-era per-character parameters must reach the kernel.

Phase 1 shipped the `era_noise` sections and the loader that validates them
against A1's admissible region. Nothing proved the values were then READ. The
whole suite used 0.5 and 0.15 in its synthetic templates -- exactly the
constants the code falls back to -- so an implementation that ignored the
sections entirely passed every test. That is the pathology this work item has
corrected five times: a criterion that cannot fail where the requirement is
false.

Every template in this file therefore declares values that DIFFER from the
fallbacks, and asserts the difference shows up in the child. A regression that
reads a constant instead of the template fails here and nowhere else.
"""

from __future__ import annotations

import pytest
from django.contrib.gis.geos import Point, Polygon

from epocha.apps.demography.inheritance import (
    DEFAULT_ERA_MEAN,
    DEFAULT_ERA_SD,
    apply_social_inheritance,
    apply_trait_inheritance,
)
from epocha.apps.simulation.models import Simulation
from epocha.apps.users.models import User
from epocha.apps.world.models import World, Zone

from .test_inheritance import _make_agent


@pytest.fixture
def sim_with_zone(db):
    """Minimum scaffolding: user, simulation, world, zone."""
    user = User.objects.create_user(
        email="wiring@epocha.dev", username="wiringuser", password="pass1234"
    )
    sim = Simulation.objects.create(name="WiringTest", seed=1, owner=user, current_tick=0)
    world = World.objects.create(simulation=sim, stability_index=0.7)
    zone = Zone.objects.create(
        world=world,
        name="WiringZone",
        zone_type="commercial",
        boundary=Polygon.from_bbox((0, 0, 100, 100)),
        center=Point(50, 50),
    )
    return sim, zone


class _FixedDraw:
    """An rng returning the mean of whatever distribution it is asked for.

    With a zero draw the kernel reduces to its signal term, which makes the
    declared era mean directly observable in the child's value.
    """

    def __init__(self) -> None:
        self.calls = 0

    def gauss(self, mu: float, sigma: float) -> float:
        self.calls += 1
        return mu


def _trait_template(entries: dict[str, tuple[float, float, float]]) -> dict:
    """`entries` maps trait name to (heritability, era_mean, era_sd)."""
    return {
        "trait_inheritance": {
            "heritability": {name: h2 for name, (h2, _, _) in entries.items()},
            "era_noise": {
                name: {"era_mean": m, "era_sd": s} for name, (_, m, s) in entries.items()
            },
            "derived_trait_formulas": {},
        }
    }


@pytest.mark.django_db
class TestTraitParametersAreRead:
    """The declared (era_mean, era_sd) per trait must govern the child."""

    def test_declared_era_mean_governs_a_parentless_child(self, sim_with_zone):
        """With neither parent and a zero draw the child IS the era mean.

        Declared 0.62, which is neither the 0.5 fallback nor any other value
        in the file, so reading the constant lands 0.12 away.
        """
        sim, zone = sim_with_zone
        template = _trait_template({"openness": (0.55, 0.62, 0.15)})
        child = _make_agent(sim, zone, "Child")
        apply_trait_inheritance(child, None, None, template, _FixedDraw())
        assert child.personality["openness"] == pytest.approx(0.62)
        assert DEFAULT_ERA_MEAN != 0.62, "the probe must differ from the fallback"

    def test_each_trait_reads_its_own_entry_not_a_shared_one(self, sim_with_zone):
        """Two traits, two declared means, in one template.

        An implementation reading a single era mean for the whole section --
        or a constant -- collapses both onto one value and fails here.
        """
        sim, zone = sim_with_zone
        template = _trait_template(
            {"openness": (0.55, 0.20, 0.15), "conscientiousness": (0.44, 0.80, 0.15)}
        )
        child = _make_agent(sim, zone, "Child")
        apply_trait_inheritance(child, None, None, template, _FixedDraw())
        assert child.personality["openness"] == pytest.approx(0.20)
        assert child.personality["conscientiousness"] == pytest.approx(0.80)

    def test_declared_era_sd_scales_the_residual(self, sim_with_zone):
        """The amplitude reaches the draw, not just the mean.

        A one-sigma draw displaces the child by `residual_scale * era_sd`, so
        doubling the declared amplitude doubles the displacement. Reading the
        0.15 fallback would make both templates agree.
        """

        class _OneSigma:
            def gauss(self, mu: float, sigma: float) -> float:
                return mu + sigma

        sim, zone = sim_with_zone
        narrow = _make_agent(sim, zone, "Narrow")
        wide = _make_agent(sim, zone, "Wide")
        apply_trait_inheritance(
            narrow, None, None, _trait_template({"openness": (0.55, 0.5, 0.05)}), _OneSigma()
        )
        apply_trait_inheritance(
            wide, None, None, _trait_template({"openness": (0.55, 0.5, 0.10)}), _OneSigma()
        )
        narrow_displacement = narrow.personality["openness"] - 0.5
        wide_displacement = wide.personality["openness"] - 0.5
        assert wide_displacement == pytest.approx(2 * narrow_displacement)
        assert DEFAULT_ERA_SD not in (0.05, 0.10), "both probes must differ from the fallback"


class TestEducationMeanIsRead:
    """The education mean must come from the declared section.

    Until now `_regress_education_level` read `social_inheritance.era_mean_
    education`, a key amendment A9 made UNKNOWN to the schema -- the loader
    rejects it -- so the read could never find it and always fell to a
    hardcoded 0.3. A dead read behind a live-looking default.
    """

    @staticmethod
    def _social_template(era_mean_education: float, rho: float = 0.6) -> dict:
        return {
            "social_inheritance": {
                "class_rule": "patrilineal_rigid",
                "education_regression_rho": rho,
                "era_noise": {
                    "education": {"era_mean": era_mean_education, "era_sd": 0.15},
                    "class_rank": {"target_dispersion": 1.0},
                },
            }
        }

    @pytest.mark.django_db
    def test_declared_education_mean_governs_a_parentless_child(self, sim_with_zone):
        """Neither parent: the regression resolves to the declared mean.

        Declared 0.7, which is neither the 0.3 the dead read fell back to nor
        the 0.5 the traits use.
        """
        sim, zone = sim_with_zone
        child = _make_agent(sim, zone, "Child")
        apply_social_inheritance(child, None, None, self._social_template(0.7), 2.0, _FixedDraw())
        assert child.education_level == pytest.approx(0.7)

    @pytest.mark.django_db
    def test_two_eras_with_different_declared_means_diverge(self, sim_with_zone):
        """The read is per-template, so two templates must not agree."""
        sim, zone = sim_with_zone
        low = _make_agent(sim, zone, "Low")
        high = _make_agent(sim, zone, "High")
        apply_social_inheritance(low, None, None, self._social_template(0.2), 2.0, _FixedDraw())
        apply_social_inheritance(high, None, None, self._social_template(0.8), 2.0, _FixedDraw())
        assert low.education_level == pytest.approx(0.2)
        assert high.education_level == pytest.approx(0.8)

    @pytest.mark.django_db
    def test_the_retired_key_is_no_longer_consulted(self, sim_with_zone):
        """`era_mean_education` is unknown to the schema after A9.

        A template carrying it would be rejected at load; if the kernel still
        preferred it, a caller bypassing the loader would get the retired
        value. The declared section must win.
        """
        sim, zone = sim_with_zone
        template = self._social_template(0.7)
        template["social_inheritance"]["era_mean_education"] = 0.1
        child = _make_agent(sim, zone, "Child")
        apply_social_inheritance(child, None, None, template, 2.0, _FixedDraw())
        assert child.education_level == pytest.approx(0.7)


@pytest.mark.django_db
class TestShippedTemplatesFeedTheKernel:
    """End to end on the real fixtures, not synthetic ones."""

    def test_every_shipped_era_reaches_the_kernel_with_its_own_values(self, sim_with_zone):
        from epocha.apps.demography.template_loader import list_available_templates, load_template

        for name in list_available_templates():
            template = load_template(name)
            sim, zone = sim_with_zone
            era_noise = template["trait_inheritance"]["era_noise"]
            child = _make_agent(sim, zone, f"Child-{name}")
            apply_trait_inheritance(child, None, None, template, _FixedDraw())
            for trait, moments in era_noise.items():
                # scalar traits land on Agent columns, personality ones in the
                # JSON blob; both must take the declared mean
                actual = (
                    child.personality[trait]
                    if trait in child.personality
                    else getattr(child, trait)
                )
                assert actual == pytest.approx(moments["era_mean"]), (
                    f"{name}: {trait} did not take its declared era mean"
                )

"""Phase 3: the shari'a spousal share, exact tax conservation, and rho.

Three corrections that share a death event and nothing else, gathered here
because each is small and each has an exact criterion.

A5 -- the Quranic spousal share is GENDERED and the code applied one pair of
fractions to both sexes, so a widower received half of what Q4:12 gives him.

A6 -- estate tax and remainder were computed as two independent products and
their sum missed the estate by an ulp on 16.1% of trials at rate 0.15. The
module asserts exact conservation, and that assertion is load-bearing for the
whitepaper's accounting invariant, so the property is restored rather than the
claim weakened.

A11 -- the shipped education-regression coefficients trace to an attribution
that does not exist: no Chetty et al. (2014) paper reports an education
persistence coefficient of any value. The verified anchor is Black and
Devereux (2011) Table 3, whose Plug (2004) joint regression gives 0.30 on the
father AND 0.30 on the mother, so the coefficient comparable to a rho on the
midparent is their SUM.
"""

from __future__ import annotations

import math
import random

import pytest
from django.contrib.gis.geos import Point, Polygon

from epocha.apps.agents.models import Agent
from epocha.apps.demography.inheritance import (
    apply_estate_tax,
    distribute_estate,
    inherit_trait,
)
from epocha.apps.demography.template_loader import load_template
from epocha.apps.simulation.models import Simulation
from epocha.apps.users.models import User
from epocha.apps.world.models import Government, World, Zone

from .test_inheritance import _make_agent


class _FixedDraw:
    """Returns a caller-chosen number of sigmas from whatever it is asked for."""

    def __init__(self, z: float) -> None:
        self.z = z

    def gauss(self, mu: float, sigma: float) -> float:
        return mu + sigma * self.z


ALL_TEMPLATES = (
    "pre_industrial_christian",
    "pre_industrial_islamic",
    "industrial",
    "modern_democracy",
    "sci_fi",
)


@pytest.fixture
def sim_with_zone(db):
    user = User.objects.create_user(
        email="succession@epocha.dev", username="successionuser", password="pass1234"
    )
    sim = Simulation.objects.create(name="SuccessionTest", seed=1, owner=user, current_tick=0)
    world = World.objects.create(simulation=sim, stability_index=0.7)
    zone = Zone.objects.create(
        world=world,
        name="SuccessionZone",
        zone_type="commercial",
        boundary=Polygon.from_bbox((0, 0, 100, 100)),
        center=Point(50, 50),
    )
    return sim, zone


# ---------------------------------------------------------------------------
# A5 -- the gendered spousal share
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestTheSpousalShareIsGendered:
    """Quran 4:12, read on the primary text rather than through Powers.

    | surviving spouse | childless | with children |
    |------------------|-----------|---------------|
    | widower          | 1/2       | 1/4           |
    | widow            | 1/4       | 1/8           |

    The code applied 1/4 and 1/8 to both, so a widower received exactly half
    his entitlement. A non-binary spouse takes the widow's share, matching
    what the design spec already fixes for non-binary heirs under this rule.
    """

    @staticmethod
    def _heirs(sim, zone, spouse_gender, children):
        spouse = _make_agent(sim, zone, "Spouse", gender=spouse_gender)
        kids = [
            _make_agent(sim, zone, f"Child{i}", gender=Agent.Gender.FEMALE, birth_tick=i)
            for i in range(children)
        ]
        # A sibling keeps the childless case out of the "radd" branch, where
        # the spouse absorbs the whole estate and the fraction is invisible.
        sibling = _make_agent(sim, zone, "Sibling", gender=Agent.Gender.FEMALE)
        deceased = _make_agent(sim, zone, "Deceased", gender=Agent.Gender.FEMALE)
        return spouse, deceased, {"spouse": [spouse], "children": kids, "siblings": [sibling]}

    @pytest.mark.parametrize(
        ("gender", "children", "expected"),
        [
            (Agent.Gender.MALE, 0, 0.5),
            (Agent.Gender.MALE, 2, 0.25),
            (Agent.Gender.FEMALE, 0, 0.25),
            (Agent.Gender.FEMALE, 2, 0.125),
            (Agent.Gender.NON_BINARY, 0, 0.25),
            (Agent.Gender.NON_BINARY, 2, 0.125),
        ],
    )
    def test_each_cell_of_the_quranic_table(self, sim_with_zone, gender, children, expected):
        sim, zone = sim_with_zone
        spouse, deceased, heirs = self._heirs(sim, zone, gender, children)
        allocation = distribute_estate(deceased, heirs, "shari'a", 1000.0)
        assert allocation[spouse.id] == pytest.approx(1000.0 * expected, rel=1e-12)

    def test_a_widower_receives_twice_a_widow(self, sim_with_zone):
        """The defect, stated as a ratio so it cannot be satisfied by moving
        both fractions together."""
        sim, zone = sim_with_zone
        widower, deceased_a, widower_heirs = self._heirs(sim, zone, Agent.Gender.MALE, 2)
        widow, deceased_b, widow_heirs = self._heirs(sim, zone, Agent.Gender.FEMALE, 2)
        widower_share = distribute_estate(deceased_a, widower_heirs, "shari'a", 800.0)[widower.id]
        widow_share = distribute_estate(deceased_b, widow_heirs, "shari'a", 800.0)[widow.id]
        assert widower_share == pytest.approx(2.0 * widow_share, rel=1e-12)

    @pytest.mark.parametrize("gender", [Agent.Gender.MALE, Agent.Gender.FEMALE])
    def test_conservation_survives_the_gendered_fractions(self, sim_with_zone, gender):
        """A larger spousal fraction must come out of the residuary pool, not
        out of thin air. The widower's 1/2 is the case that would break a rule
        that assumed the spouse never takes more than a quarter."""
        sim, zone = sim_with_zone
        _, deceased, heirs = self._heirs(sim, zone, gender, 3)
        allocation = distribute_estate(deceased, heirs, "shari'a", 999.99)
        assert sum(allocation.values()) == pytest.approx(999.99, rel=1e-12)

    def test_the_childless_widower_leaves_half_to_the_residuary_heirs(self, sim_with_zone):
        sim, zone = sim_with_zone
        spouse, deceased, heirs = self._heirs(sim, zone, Agent.Gender.MALE, 0)
        allocation = distribute_estate(deceased, heirs, "shari'a", 400.0)
        residuary = sum(value for agent_id, value in allocation.items() if agent_id != spouse.id)
        assert residuary == pytest.approx(200.0, rel=1e-12)


# ---------------------------------------------------------------------------
# A6 -- exact conservation of the estate tax
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestTheEstateTaxConservesExactly:
    """`tax + remainder == estate` in floating point, over the whole domain.

    Not "up to rounding": exactly, for every rate the function accepts. The
    construction is A6's: always derive the SMALLER of the two terms by
    subtraction, so Sterbenz's lemma applies -- `a - b` is exact whenever
    `b/2 <= a <= 2b`, which holds for the smaller term on either side of 0.5.

    Recorded as inadequate, and re-checked here as mutations rather than
    trusted: deriving the remainder alone does not reach exactness even at the
    shipped rates, and deriving the tax alone is exact only up to 0.5 and
    breaks above it -- 12.68% of trials fail at rate 0.70.
    """

    @staticmethod
    def _government(sim):
        return Government.objects.create(simulation=sim, government_type="monarchy")

    @pytest.mark.parametrize(
        "rate", [0.0, 0.15, 0.40, 0.49, 0.5, 0.51, 0.55, 0.60, 0.70, 0.99, 1.0]
    )
    def test_conservation_is_exact_over_twenty_thousand_estates(self, sim_with_zone, rate):
        """The tax is READ FROM THE TREASURY, never re-derived here.

        A first version of this test computed `tax = estate - remainder` and
        then asserted `remainder + tax == estate`, which is the function's own
        arithmetic replaced by the test's -- a tautology that passed under a
        mutant deriving the wrong term. The function returns only the
        remainder, so the credited amount is the sole independent witness of
        what it actually split.
        """
        sim, _ = sim_with_zone
        government = self._government(sim)
        rng = random.Random(20260811)
        failures = 0
        trials = 20000
        for _ in range(trials):
            estate = rng.uniform(1e-6, 1_000_000.0)
            government.government_treasury = {}
            remainder = apply_estate_tax(estate, rate, government, "GOLD")
            credited = government.government_treasury.get("GOLD", 0.0)
            # The guarantee names this summation order: remainder first, then
            # tax. Floating-point addition is not associative, so a
            # conservation claim that does not state its order is not a claim.
            if remainder + credited != estate:
                failures += 1
        assert failures == 0, f"{failures}/{trials} estates lost or created money at rate {rate}"

    def test_the_treasury_receives_exactly_what_the_estate_lost(self, sim_with_zone):
        sim, _ = sim_with_zone
        government = self._government(sim)
        estate = 123456.789
        remainder = apply_estate_tax(estate, 0.15, government, "GOLD")
        credited = government.government_treasury["GOLD"]
        assert credited + remainder == estate

    @pytest.mark.parametrize("rate", [0.15, 0.40])
    def test_the_shipped_rates_still_return_the_same_remainder_they_did(self, sim_with_zone, rate):
        """A6 is a correction to the arithmetic, not to the model: the numbers
        must not move beyond an ulp, or the fix would silently retune the two
        eras that levy a tax."""
        sim, _ = sim_with_zone
        government = self._government(sim)
        estate = 250000.0
        remainder = apply_estate_tax(estate, rate, government, "GOLD")
        assert remainder == pytest.approx(estate * (1.0 - rate), rel=1e-15)


# ---------------------------------------------------------------------------
# A11 -- the education regression coefficients
# ---------------------------------------------------------------------------


class TestTheEducationCoefficientsMatchTheirSource:
    """0.60 in four eras, 0.30 in sci-fi, and the reason for each.

    0.60 is the SUM of Plug (2004)'s two joint coefficients as Black and
    Devereux (2011) Table 3 reports them, because the model applies one
    coefficient to the midparent while the source estimates one per parent in
    a single joint regression. Reading 0.30 as rho would apply a
    single-parent estimate to an average -- the trap this test names so it
    cannot be re-introduced by someone reading the table's cell rather than
    its structure.

    The single value across four eras is deliberate: varying rho on a
    progression no source supports would give the appearance of a measured
    historical series.
    """

    @pytest.mark.parametrize(
        ("template_name", "expected"),
        [
            ("pre_industrial_christian", 0.60),
            ("pre_industrial_islamic", 0.60),
            ("industrial", 0.60),
            ("modern_democracy", 0.60),
            ("sci_fi", 0.30),
        ],
    )
    def test_each_era_declares_the_amended_coefficient(self, template_name, expected):
        template = load_template(template_name)
        rho = template["social_inheritance"]["education_regression_rho"]
        assert rho == pytest.approx(expected, abs=1e-12)

    def test_the_anchored_value_is_the_sum_and_not_one_of_the_two_addends(self):
        """Plug's joint regression gives 0.30 on each parent."""
        modern = load_template("modern_democracy")
        rho = modern["social_inheritance"]["education_regression_rho"]
        assert rho == pytest.approx(0.30 + 0.30, abs=1e-12)
        assert rho != pytest.approx(0.30, abs=1e-9)

    def test_no_shipped_coefficient_leaves_the_admissible_region(self):
        """A larger rho feeds more parental variance forward, so the amplitude
        floor the loader enforces has to be re-checked at the new values
        rather than assumed to survive the change."""
        for name in ALL_TEMPLATES:
            template = load_template(name)  # raises if the region check fails
            rho = template["social_inheritance"]["education_regression_rho"]
            assert 0.0 <= rho <= 1.0

    def test_the_coefficient_still_leaves_a_residual_the_identity_admits(self):
        """`sqrt(1 - rho**2/2)` must stay real: at rho = 0.60 the two-parent
        residual scale is 0.905539, comfortably inside the domain, but the
        assertion states the boundary rather than trusting that 0.60 is far
        from it.

        NOTATION, corrected after the phase-6 audit: an earlier version of
        this docstring wrote `rho^4` and quoted 0.9330, which is neither
        `sqrt(1 - 0.6**2/2) = 0.905539` nor `sqrt(1 - 0.6**4/2) = 0.967057`.
        A1's convention that `h^4` means `h2**2` applies to HERITABILITY,
        which is already a square; `rho` is a regression coefficient and its
        residual is `sqrt(1 - rho**2/2)` with no fourth power anywhere. The
        code below always asserted on `rho**2`; it was the prose that
        carried the trap A1's own test constraint exists to prevent.
        """
        # Measured THROUGH the kernel, not asserted as a literal against a
        # literal: the phase-6 audit caught the first version of this line
        # doing exactly what it had just condemned elsewhere. A no-parent
        # probe isolates the residual scale, and the two-parent branch is the
        # one whose scale the value above names.
        rng = _FixedDraw(1.0)
        high = inherit_trait(0.30, 0.30, 0.60, 0.30, 0.15, rng)
        low = inherit_trait(0.30, 0.30, 0.60, 0.30, 0.15, _FixedDraw(-1.0))
        measured = (high - low) / (2.0 * 0.15)
        assert measured == pytest.approx(0.905539, abs=5e-7)
        for name in ALL_TEMPLATES:
            rho = load_template(name)["social_inheritance"]["education_regression_rho"]
            assert 1.0 - rho**2 / 2.0 > 0.0
            assert math.sqrt(1.0 - rho**2 / 2.0) < 1.0

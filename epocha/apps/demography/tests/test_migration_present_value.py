"""Phase 4: the migration gain becomes a present value (A7), and stability
is declared for what it is (A10).

A7 -- `(1 - u_j)*w_j - w_current - distance_cost_j` subtracts a COUNT OF
TICKS from a MONEY-PER-TICK. The design spec's own worked example hides it by
choosing a destination at zero distance cost. Monetising the cost does not fix
it either: that produces one money against two rates.

The sources separate cleanly, and the module cited the wrong one for the wrong
thing. Harris and Todaro (1970) is a ONE-PERIOD equilibrium equality,
`W_u*E_u/L_u = W_R`, with no horizon, no discounting and no cost -- it remains
the source of the employment-probability-weighted wage and CANNOT license a
horizon. Todaro (1969) states the decision as a discounted present value with
`n` periods and a lump-sum `C(0)` subtracted from a discounted flow, never
netted against a rate: the correct structure was in the literature all along.
Sjaastad (1962) supplies the horizon -- residual working life -- and the cost
definition, earnings foregone while travelling and searching, partly a
function of distance.

A10 -- `Government.stability` is ONE scalar per simulation, and the outlook
reported it per zone, unlabelled, for every destination. The decision is not
to invent a per-zone signal, which would be a new model rather than the
correction of a defect, but to report the value once and say what it is. The
defect being removed is precise: the block induces a language model to believe
it is comparing zones on a dimension where they are identical.
"""

from __future__ import annotations

import math

import pytest
from django.contrib.gis.geos import Point, Polygon

from epocha.apps.demography.migration import (
    SJAASTAD_ANNUAL_DISCOUNT_RATE,
    WORKING_LIFE_END_AGE,
    annuity_for_agent,
    build_migration_outlook,
    compute_expected_gain,
    present_value_annuity_ticks,
    residual_working_life_years,
)
from epocha.apps.simulation.models import Simulation
from epocha.apps.users.models import User
from epocha.apps.world.models import Government, World, Zone

from .test_inheritance import _make_agent

HOURS_PER_YEAR = 8760.0


@pytest.fixture
def sim_with_zones(db):
    user = User.objects.create_user(email="pv@epocha.dev", username="pvuser", password="pass1234")
    sim = Simulation.objects.create(name="PVTest", seed=1, owner=user, current_tick=0)
    world = World.objects.create(simulation=sim, stability_index=0.7, tick_duration_hours=24.0)
    Government.objects.create(simulation=sim, government_type="monarchy", stability=0.42)
    zones = []
    for index, name in enumerate(("Home", "Paris", "Countryside")):
        zones.append(
            Zone.objects.create(
                world=world,
                name=name,
                zone_type="commercial",
                boundary=Polygon.from_bbox((index * 10, 0, index * 10 + 5, 5)),
                center=Point(index * 10 + 2.5, 2.5),
            )
        )
    return sim, world, zones


class TestTheAnnuityMatchesItsSource:
    """Sjaastad prints two annuity factors on page 89; both are reproduced.

    At a 10% annual rate the present value of one unit of annual income over
    45 and 40 remaining years is 9.889 and 9.817. Those are the numbers the
    source publishes, and reproducing them is what makes the conversion to
    ticks auditable rather than asserted.
    """

    @pytest.mark.parametrize(("years", "expected"), [(45.0, 9.889), (40.0, 9.817)])
    def test_the_annual_scale_factors_sjaastad_prints(self, years, expected):
        # One "tick" of one year: the tick machinery must reduce to the
        # source's own units when a tick IS a year.
        ticks_per_year = 1.0
        factor = present_value_annuity_ticks(years * ticks_per_year, 0.10 / ticks_per_year)
        assert factor == pytest.approx(expected, abs=5e-4)

    def test_the_conversion_goes_through_tick_duration_and_not_a_day(self):
        """A tick is not assumed to be a day, and this must be asserted on
        the function that DOES the conversion.

        A first version of this test called `present_value_annuity_ticks`
        with a hand-computed `ticks_per_year`, which is the test doing the
        conversion itself: an implementation hardcoding 365 passed it. It is
        the same failure this whole work item keeps finding -- a criterion
        that cannot fail where the requirement is false -- and it was caught
        by mutation, not by reading. `annuity_for_agent` is the seam that
        reads `World.tick_duration_hours`, so the assertion belongs there.

        At age 22 the horizon is 40 years: 3583 ticks of present value at
        24-hour ticks, and double that at 12-hour ticks, because a tick is
        then half as much time and the same 40 years contain twice as many.
        """
        assert annuity_for_agent(22, 24.0) == pytest.approx(3583.15, rel=1e-4)
        assert annuity_for_agent(22, 12.0) == pytest.approx(7166.30, rel=1e-4)
        assert annuity_for_agent(22, 8760.0) == pytest.approx(9.817, abs=5e-4)

    def test_a_non_positive_tick_duration_is_rejected_rather_than_divided_by(self):
        for hours in (0.0, -24.0):
            with pytest.raises(ValueError):
                annuity_for_agent(30, hours)

    def test_the_limit_of_a_vanishing_rate_is_the_horizon_itself(self):
        """`(1 - e^-rH)/r -> H` as `r -> 0`. Undiscounted, the present value
        of a unit flow is just its duration, and a division by zero must not
        be what the caller discovers.
        """
        assert present_value_annuity_ticks(1000.0, 0.0) == pytest.approx(1000.0, rel=1e-12)

    def test_a_spent_working_life_discounts_nothing(self):
        assert present_value_annuity_ticks(0.0, 0.001) == pytest.approx(0.0, abs=1e-12)


class TestTheHorizonIsDerivedFromAgeAndNotChosen:
    """Sjaastad's horizon is residual working life, and it shortens with age.

    `WORKING_LIFE_END_AGE` is fixed at the value that reproduces BOTH of the
    figures the source prints: 45 remaining years at the midpoint of his 15-19
    bracket and 40 at the midpoint of his 20-24 bracket give 62 twice over.
    That is a derivation from the source, not a preference.
    """

    def test_the_end_age_reproduces_both_of_sjaastads_brackets(self):
        assert WORKING_LIFE_END_AGE - 17 == 45
        assert WORKING_LIFE_END_AGE - 22 == 40

    @pytest.mark.parametrize(("age", "expected"), [(17, 45.0), (22, 40.0), (40, 22.0)])
    def test_residual_working_life_shortens_with_age(self, age, expected):
        assert residual_working_life_years(age) == pytest.approx(expected)

    @pytest.mark.parametrize("age", [62, 70, 95])
    def test_past_the_end_the_horizon_is_zero_and_never_negative(self, age):
        """A negative horizon would flip the sign of the annuity and pay an
        agent to migrate for having grown old."""
        assert residual_working_life_years(age) == 0.0


class TestTheGainIsAPresentValue:
    """Every term is money, and the two that were not are now.

    `a * [money/tick] = money` and `distance_cost_ticks * [money/tick] =
    money`. The old form subtracted a bare tick count from a per-tick wage.
    """

    @staticmethod
    def _factor(hours=24.0, years=40.0):
        ticks_per_year = HOURS_PER_YEAR / hours
        return present_value_annuity_ticks(
            years * ticks_per_year, SJAASTAD_ANNUAL_DISCOUNT_RATE / ticks_per_year
        )

    def test_the_wage_differential_is_capitalised_over_the_horizon(self):
        """The amendment's worked example: a per-tick advantage of 4.8 at a
        40-year horizon and 24-hour ticks is a present value of 17,199, not
        4.8. The old form returned the per-tick figure and called it a gain.
        """
        gain = compute_expected_gain(
            unemployment_j=0.0,
            wage_j=14.8,
            wage_current=10.0,
            distance_cost_ticks=0,
            annuity_ticks=self._factor(),
        )
        assert gain == pytest.approx(17199.0, rel=1e-3)

    def test_the_distance_cost_is_earnings_foregone_and_not_a_bare_count(self):
        """Sjaastad p.84 defines the cost as earnings foregone while
        travelling and searching, so the tick count is priced at the wage the
        agent is currently earning. A test that only ever ran at zero distance
        cost -- which is what the design spec's worked example does -- cannot
        see the difference between that and subtracting the count itself.
        """
        common = dict(
            unemployment_j=0.0, wage_j=14.8, wage_current=10.0, annuity_ticks=self._factor()
        )
        near = compute_expected_gain(distance_cost_ticks=0, **common)
        far = compute_expected_gain(distance_cost_ticks=7, **common)
        assert near - far == pytest.approx(7 * 10.0, rel=1e-12)

    def test_the_break_even_distance_widens_by_the_annuity_factor(self):
        """The declared consequence, stated as a number rather than left for
        a reader to discover: capitalising the flow moves the break-even
        distance cost from 4.8 ticks to 220.5, against shipped costs of 0, 3
        and 5. Distance stops biting. Sjaastad says so himself on p.84 --
        reconciling the observed distance effect with the present value of the
        differential would need implausibly high marginal costs per mile,
        "even at very high discount rates". The investment model
        under-predicts the friction of distance, and its own author writes it.
        """
        # The design spec's own worked example: unemployment 0.08, a
        # destination wage of 90 against a current wage of 78, so the flow
        # advantage is (1 - 0.08) * 90 - 78 = 4.8 per tick and the break-even
        # distance cost is `a * 4.8 / 78`. The current wage is what prices the
        # travel time, so it belongs in the denominator -- reading 4.8 as if
        # the wage were the advantage itself gives 1719.9 and is wrong.
        annuity = self._factor()
        break_even = annuity * 4.8 / 78.0
        assert break_even == pytest.approx(220.5, rel=1e-3)
        gain_at_break_even = compute_expected_gain(
            unemployment_j=0.08,
            wage_j=90.0,
            wage_current=78.0,
            distance_cost_ticks=break_even,
            annuity_ticks=annuity,
        )
        assert gain_at_break_even == pytest.approx(0.0, abs=1e-6)

    def test_unemployment_still_weights_the_destination_wage(self):
        """Harris and Todaro keep the one thing they are a source for."""
        annuity = self._factor()
        certain = compute_expected_gain(0.0, 20.0, 10.0, 0, annuity)
        risky = compute_expected_gain(0.5, 20.0, 10.0, 0, annuity)
        assert certain == pytest.approx(annuity * 10.0, rel=1e-12)
        assert risky == pytest.approx(annuity * 0.0, abs=1e-9)

    def test_currency_scale_invariance_survives(self):
        """Doubling every monetary quantity doubles the gain and changes no
        decision: the annuity is dimensionless in the currency and the cost is
        priced in it."""
        annuity = self._factor()
        single = compute_expected_gain(0.2, 14.8, 10.0, 5, annuity)
        double = compute_expected_gain(0.2, 29.6, 20.0, 5, annuity)
        assert double == pytest.approx(2.0 * single, rel=1e-12)


@pytest.mark.django_db
class TestTheOutlookReportsAPresentValueAndOneStability:
    def test_the_outlook_uses_the_agents_own_horizon(self, sim_with_zones):
        """Two agents differing only in age must see different gains: the
        horizon is the agent's, not a constant."""
        sim, world, zones = sim_with_zones
        stats = _zone_stats(world, zones)
        young = _make_agent(sim, zones[0], "Young", age=20)
        old = _make_agent(sim, zones[0], "Old", age=55)
        young_gain = build_migration_outlook(young, sim, 0, stats)["reachable_zones"][zones[1].id][
            "expected_gain"
        ]
        old_gain = build_migration_outlook(old, sim, 0, stats)["reachable_zones"][zones[1].id][
            "expected_gain"
        ]
        assert young_gain > old_gain > 0.0

    def test_stability_is_reported_once_and_labelled(self, sim_with_zones):
        """A10: one line at outlook level, named for what it is. Repeating a
        constant per zone is the misleading part, not the constant.
        """
        sim, world, zones = sim_with_zones
        stats = _zone_stats(world, zones)
        agent = _make_agent(sim, zones[0], "Agent", age=30)
        outlook = build_migration_outlook(agent, sim, 0, stats)
        assert outlook["government_stability"] == pytest.approx(0.42)
        for entry in outlook["reachable_zones"].values():
            assert "zone_stability" not in entry

    def test_the_outlook_still_issues_no_queries(self, sim_with_zones, django_assert_num_queries):
        sim, world, zones = sim_with_zones
        stats = _zone_stats(world, zones)
        agent = _make_agent(sim, zones[0], "Agent", age=30)
        with django_assert_num_queries(0):
            build_migration_outlook(agent, sim, 0, stats)


def _zone_stats(world, zones):
    return {
        "world": world,
        "government_stability": 0.42,
        "zones": {
            zones[0].id: {"zone": zones[0], "wage": 10.0, "unemployment": 0.1},
            zones[1].id: {"zone": zones[1], "wage": 14.8, "unemployment": 0.2},
            zones[2].id: {"zone": zones[2], "wage": 9.0, "unemployment": 0.05},
        },
    }


class TestTheDiscountRateIsAnchoredAndDeclaredTunable:
    def test_the_rate_is_sjaastads_stated_assumption(self):
        """10% annual, which Sjaastad uses and explicitly declares as an
        assumption on p.92, entertaining lower values in note 23 and much
        higher ones in note 26. Todaro supplies neither `i` nor `n`.
        """
        assert SJAASTAD_ANNUAL_DISCOUNT_RATE == pytest.approx(0.10)

    def test_a_higher_rate_shortens_the_effective_horizon(self):
        ticks_per_year = HOURS_PER_YEAR / 24.0
        patient = present_value_annuity_ticks(40.0 * ticks_per_year, 0.05 / ticks_per_year)
        impatient = present_value_annuity_ticks(40.0 * ticks_per_year, 0.25 / ticks_per_year)
        assert patient > impatient
        # and neither may exceed the undiscounted horizon itself
        assert patient < 40.0 * ticks_per_year

    def test_the_factor_is_bounded_by_one_over_the_rate(self):
        """`(1 - e^-rH)/r < 1/r` for every finite horizon: an unbounded
        working life is worth a finite amount.

        The inequality is strict in mathematics and NOT in floating point --
        at a horizon of 1e9 ticks the exponential underflows to zero and the
        two sides come out bit-identical. Asserted as `<=` with the reason
        stated, rather than weakened silently or dodged by picking a horizon
        small enough to keep a strict test passing.
        """
        rate = 0.10 / (HOURS_PER_YEAR / 24.0)
        assert present_value_annuity_ticks(1e9, rate) <= 1.0 / rate
        assert math.isfinite(present_value_annuity_ticks(1e9, rate))
        # At a horizon the model can actually produce, the bound IS strict.
        assert present_value_annuity_ticks(45.0 * HOURS_PER_YEAR / 24.0, rate) < 1.0 / rate

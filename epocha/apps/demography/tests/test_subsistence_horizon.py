"""SC-014a: both consumers of the subsistence threshold share one horizon.

Amendment A8 changes no behaviour -- the incoherence was entirely in the
design document, which defined a global `N` as "the number of ticks the agent
can survive on current savings" and then used it as a threshold ON that same
quantity, reducing the condition to `wealth < wealth`. What A8 fixes is the
definition: the **survival horizon** is `wealth / subsistence_threshold`, a
derived ratio, and each consumer declares its own threshold on it.

That makes the criterion a criterion about AGREEMENT, and SC-014a says so
explicitly: verified by mutation, changing the definition in ONE consumer.
A document-only amendment with no test is exactly the shape of thing this
work item has been punished for four times, so the two consumers are pinned
against each other here.

The two are `fertility.becker_modulation`, which consumes the horizon
continuously through a logarithm, and `migration.evaluate_emergency_flight`,
which applies the threshold 1. They must divide by, and compare against, the
SAME zone-scoped quantity: `compute_subsistence_threshold(simulation, zone)`.
"""

from __future__ import annotations

import math

import pytest
from django.contrib.gis.geos import Point, Polygon

from epocha.apps.demography.context import compute_subsistence_threshold
from epocha.apps.demography.fertility import becker_modulation
from epocha.apps.demography.migration import evaluate_emergency_flight
from epocha.apps.economy.models import GoodCategory, ZoneEconomy
from epocha.apps.simulation.models import Simulation
from epocha.apps.users.models import User
from epocha.apps.world.models import Government, World, Zone

from .test_inheritance import _make_agent

SEED_COEFFS = {
    "beta_0": 0.0,
    "beta_1": 0.25,
    "beta_2": 0.0,
    "beta_3": 0.0,
    "beta_4": 0.0,
}


@pytest.fixture
def sim_with_zone(db):
    user = User.objects.create_user(
        email="horizon@epocha.dev", username="horizonuser", password="pass1234"
    )
    sim = Simulation.objects.create(name="HorizonTest", seed=1, owner=user, current_tick=10)
    world = World.objects.create(simulation=sim, stability_index=0.7)
    zone = Zone.objects.create(
        world=world,
        name="HorizonZone",
        zone_type="residential",
        boundary=Polygon.from_bbox((0, 0, 100, 100)),
        center=Point(50, 50),
    )
    Government.objects.create(simulation=sim, stability=0.7)
    # One essential good priced at 5.0 gives a per-tick subsistence threshold
    # this test can read back rather than assume.
    GoodCategory.objects.create(
        simulation=sim,
        code="FOOD",
        name="Food",
        is_essential=True,
        base_price=10.0,
        price_elasticity=0.3,
    )
    # 7.3 rather than a round number, DELIBERATELY: the threshold is
    # `price * SUBSISTENCE_NEED_PER_AGENT`, and a probe whose value happens
    # to equal a plausible hardcoded constant cannot tell a real divisor
    # from that constant. A first version of this fixture priced FOOD at 5.0
    # and a mutant dividing by the literal 5.0 survived every test in the
    # file. The assertion below states the requirement instead of trusting
    # the choice.
    ZoneEconomy.objects.create(zone=zone, market_prices={"FOOD": 7.3})
    return sim, zone


@pytest.mark.django_db
class TestBothConsumersDivideByTheSameThreshold:
    def test_fertility_divides_the_wealth_by_the_zone_threshold(self, sim_with_zone):
        """`w = log(wealth / T)`, so multiplying the wealth by `e` must move
        the Becker exponent by exactly one `beta_1`.

        Pinned as an EXACT ratio rather than a level, because a level would
        also be reproduced by an implementation dividing by any constant --
        the ratio is what identifies the divisor as the threshold.
        """
        sim, zone = sim_with_zone
        threshold = compute_subsistence_threshold(sim, zone)
        assert threshold > 0.0, "the fixture must produce a real threshold"
        # The divisor must be identifiable. A ratio test alone is NOT enough:
        # multiplying the wealth by `e` moves the log by 1 whatever the
        # divisor is, so the ratio is invariant to the very thing under test.
        # The level assertion below is what identifies it, and it only
        # discriminates if the threshold differs from the constants an
        # implementation might plausibly hardcode.
        assert threshold not in (1.0, 5.0, 10.0), (
            f"threshold {threshold} coincides with a plausible constant; "
            "the level assertion below would not discriminate"
        )

        at_one = _make_agent(sim, zone, "AtOne", wealth=threshold)
        at_e = _make_agent(sim, zone, "AtE", wealth=threshold * math.e)
        ratio = becker_modulation(at_e, SEED_COEFFS) / becker_modulation(at_one, SEED_COEFFS)
        assert ratio == pytest.approx(math.exp(SEED_COEFFS["beta_1"]), rel=1e-9)

    def test_fertility_reads_the_horizon_as_one_at_exactly_the_threshold(self, sim_with_zone):
        """At a horizon of exactly 1 the log is 0, so the wealth term drops
        out and the modulation is `exp(beta_0)`. That is the same horizon
        value the flight trigger uses as its threshold, which is the
        agreement this file exists to assert.
        """
        sim, zone = sim_with_zone
        threshold = compute_subsistence_threshold(sim, zone)
        agent = _make_agent(sim, zone, "Exactly", wealth=threshold)
        assert becker_modulation(agent, SEED_COEFFS) == pytest.approx(1.0, rel=1e-9)

    def test_flight_triggers_on_a_horizon_below_one_and_not_above(self, sim_with_zone):
        """The flight side of the same boundary, pinned from both directions.

        A single-sided test cannot separate "compares against T" from
        "compares against 2T", which is precisely the mutation SC-014a names.
        """
        sim, zone = sim_with_zone
        threshold = compute_subsistence_threshold(sim, zone)
        template = {"migration": {"flight_trigger_ticks": 1}}
        # A second, better-paying zone at the same centre: a triggered agent
        # gets a destination back, an untriggered one gets None. Without it
        # both cases return None -- trapped and not-starving are the same
        # value -- and the test could not tell them apart.
        better = Zone.objects.create(
            world=zone.world,
            name="BetterZone",
            zone_type="residential",
            boundary=Polygon.from_bbox((0, 0, 100, 100)),
            center=Point(50, 50),
        )
        zone_stats = {
            "world": zone.world,
            "government_stability": 0.7,
            "zones": {
                zone.id: {"zone": zone, "wage": 10.0, "unemployment": 0.1},
                better.id: {"zone": better, "wage": 90.0, "unemployment": 0.0},
            },
        }

        starving = _make_agent(sim, zone, "Starving", wealth=threshold * 0.999, age=30)
        fed = _make_agent(sim, zone, "Fed", wealth=threshold * 1.001, age=30)

        starving_destination = evaluate_emergency_flight(
            starving, sim, 10, template, zone_stats, consecutive_ticks_under_subsistence=5
        )
        fed_destination = evaluate_emergency_flight(
            fed, sim, 10, template, zone_stats, consecutive_ticks_under_subsistence=5
        )
        assert starving_destination is not None
        assert starving_destination.id == better.id
        assert fed_destination is None

    def test_the_two_consumers_read_the_same_zone_scoped_value(self, sim_with_zone, monkeypatch):
        """The threshold is per zone, and both must ask for the SAME zone.

        A consumer resolving it for a different zone -- or resolving a
        simulation-wide constant -- would still pass the boundary tests above
        in a single-zone fixture. This one puts the agent in a zone whose
        threshold DIFFERS from the other zone's, records every call, and
        compares the arguments.

        The two-zone construction is load-bearing and was missing from the
        first version, which the phase-6 audit killed by measurement: with
        one zone in the world, `set(seen)` is a singleton whatever the
        resolution rule is, and a mutant resolving `world.zones.first()`
        instead of `agent.zone` stayed green across all 724 demography tests.
        """
        sim, zone = sim_with_zone
        # A SECOND zone, priced differently, and the agent lives in it. A
        # consumer reading the wrong zone now reads a different number, and
        # the recorded arguments diverge.
        other = Zone.objects.create(
            world=zone.world,
            name="OtherHorizonZone",
            zone_type="residential",
            boundary=Polygon.from_bbox((200, 200, 300, 300)),
            center=Point(250, 250),
        )
        ZoneEconomy.objects.create(zone=other, market_prices={"FOOD": 19.7})
        assert compute_subsistence_threshold(sim, other) != compute_subsistence_threshold(
            sim, zone
        ), "the two zones must price subsistence differently or nothing is discriminated"

        real = compute_subsistence_threshold
        seen: list[tuple] = []

        def spy(simulation, target_zone):
            seen.append((simulation.id, getattr(target_zone, "id", None)))
            return real(simulation, target_zone)

        import epocha.apps.demography.context as context_module

        monkeypatch.setattr(context_module, "compute_subsistence_threshold", spy)

        agent = _make_agent(sim, other, "Both", wealth=1.0, age=30)
        becker_modulation(agent, SEED_COEFFS)
        template = {"migration": {"flight_trigger_ticks": 1}}
        zone_stats = {
            "world": zone.world,
            "government_stability": 0.7,
            "zones": {
                zone.id: {"zone": zone, "wage": 10.0, "unemployment": 0.1},
                other.id: {"zone": other, "wage": 10.0, "unemployment": 0.1},
            },
        }
        evaluate_emergency_flight(
            agent, sim, 10, template, zone_stats, consecutive_ticks_under_subsistence=5
        )

        assert len(seen) >= 2, f"both consumers must resolve the threshold; saw {seen!r}"
        assert len(set(seen)) == 1, (
            f"the two consumers resolved DIFFERENT (simulation, zone) pairs: {seen!r}"
        )

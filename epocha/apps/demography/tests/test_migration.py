"""Unit tests for demography/migration.py.

Covers `compute_zone_wage` and `compute_zone_unemployment` (Plan 3,
T030/T031, user story 4 -- "migrating with economic information"): the
two zone-level labor-market aggregates that feed the Harris & Todaro
(1970) expected-income migration comparison implemented in a later task
(T033's `compute_expected_gain`).

Also covers `compute_distance_cost` (Plan 3, T032): the zone-to-zone
travel cost in whole ticks, reusing the exact km<->grid-unit conversion
`agents/movement.py`'s `calculate_max_distance` already establishes
(`World.distance_scale`, `World.tick_duration_hours`), and the same
`TRAVEL_SPEEDS["foot"]` walking speed, WITHOUT that function's health /
stability / repression / terrain modifiers, which have no meaning for an
abstract zone-to-zone distance.

Also covers `compute_expected_gain` (Plan 3, T033): the declared
operational variant of Harris & Todaro (1970) this plan implements
verbatim, including its known, deliberately UNCORRECTED dimensional
inconsistency (a currency-rate term minus a raw tick count) -- see
`TestComputeExpectedGain`'s own module-level note and
`compute_expected_gain`'s docstring for the full disclosure.

Fixture conventions (`sim_with_zone`, `_make_agent`) mirror
`test_inheritance.py`'s own helpers by COPYING the pattern, not
importing it -- this file, like every other test module in this app,
owns its own fixtures.
"""

from __future__ import annotations

import pytest
from django.contrib.gis.geos import Point, Polygon

from epocha.apps.agents.models import Agent
from epocha.apps.demography.migration import (
    ZONE_UNEMPLOYMENT_WINDOW_TICKS,
    ZONE_WAGE_WINDOW_TICKS,
    compute_distance_cost,
    compute_expected_gain,
    compute_zone_unemployment,
    compute_zone_wage,
)
from epocha.apps.economy.models import Currency, EconomicLedger
from epocha.apps.simulation.models import Simulation
from epocha.apps.users.models import User
from epocha.apps.world.models import World, Zone


@pytest.fixture
def sim_with_zone(db):
    """Minimal scaffolding: user, simulation, world, zone (mirrors
    test_inheritance.py's own `sim_with_zone`).
    """
    user = User.objects.create_user(
        email="migration@epocha.dev",
        username="migrationuser",
        password="pass1234",
    )
    sim = Simulation.objects.create(
        name="MigrationTest",
        seed=2026,
        owner=user,
        current_tick=50,
    )
    world = World.objects.create(simulation=sim, stability_index=0.7)
    zone = Zone.objects.create(
        world=world,
        name="MigrationZone",
        zone_type="residential",
        boundary=Polygon.from_bbox((0, 0, 100, 100)),
        center=Point(50, 50),
    )
    return sim, zone


def _make_agent(sim, zone, name, **kwargs):
    """Helper: create an Agent with sensible defaults (mirrors
    test_inheritance.py's own `_make_agent`).
    """
    defaults = dict(
        role="farmer",
        location=Point(50, 50),
        health=1.0,
        wealth=100.0,
        age=30,
        birth_tick=0,
        mood=0.5,
        education_level=0.5,
        social_class="working",
        gender=Agent.Gender.FEMALE,
        personality={},
    )
    defaults.update(kwargs)
    return Agent.objects.create(simulation=sim, name=name, zone=zone, **defaults)


@pytest.fixture
def currency(sim_with_zone):
    """A real, saved `Currency` row -- `EconomicLedger.currency` is a
    non-null FK, so every ledger fixture row below needs one. Mirrors the
    `currency` fixture pattern already established in
    `economy/tests/test_models.py`.
    """
    sim, _zone = sim_with_zone
    return Currency.objects.create(
        simulation=sim,
        code="LVR",
        name="Livre",
        symbol="L",
        is_primary=True,
        total_supply=50_000.0,
    )


def _make_wage(sim, currency_row, to_agent, tick, amount=10.0, from_agent=None):
    """Helper: a `wage`-type `EconomicLedger` row crediting `to_agent`
    (the worker) at `tick`. Wage rows credit the WORKER, so this module's
    zone attribution reads `to_agent__zone`, never `from_agent__zone`
    (see `compute_zone_wage`'s own docstring for the full reasoning).
    """
    return EconomicLedger.objects.create(
        simulation=sim,
        tick=tick,
        from_agent=from_agent,
        to_agent=to_agent,
        currency=currency_row,
        total_amount=amount,
        transaction_type="wage",
    )


def _make_other_zone(world, name="OtherZone"):
    """A second `Zone` on the same `World`, for the zone-attribution
    exclusion tests below. Mirrors the pattern established in
    `test_inheritance.py`'s own `_make_other_zone`.
    """
    return Zone.objects.create(
        world=world,
        name=name,
        zone_type="residential",
        boundary=Polygon.from_bbox((200, 200, 300, 300)),
        center=Point(250, 250),
    )


def _make_zone_at(world, x, y, name):
    """A `Zone` whose `center` sits at the exact grid coordinates `(x,
    y)` -- for `compute_distance_cost` tests, where the center-to-center
    distance is the load-bearing quantity and must be a known, hand-
    verifiable value.
    """
    return Zone.objects.create(
        world=world,
        name=name,
        zone_type="residential",
        boundary=Polygon.from_bbox((x - 10, y - 10, x + 10, y + 10)),
        center=Point(x, y),
    )


# ---------------------------------------------------------------------------
# compute_zone_wage (Plan 3, T030/T031, user story 4)
# ---------------------------------------------------------------------------
#
# Operational definition PINNED by these tests (not otherwise specified
# upstream of this task): compute_zone_wage returns the mean per-capita,
# per-tick wage income in `zone` over the trailing window -- SUM(
# total_amount) for `wage`-type EconomicLedger rows credited to a worker
# in `zone` (`to_agent__zone`) within the CLOSED interval [tick - window,
# tick] (BOTH ends inclusive -- window=5 therefore spans 6 distinct tick
# values when every one has data), divided by (living population *
# window). Dividing by `window` in addition to population is what turns a
# window-cumulative sum into a single per-tick flow figure, comparable
# directly against another zone's own per-tick wage (T033's
# `compute_expected_gain` needs `wage_j` and `wage_current` on the same
# footing). Zero population returns 0.0 without dividing by zero (FR-028).


class TestComputeZoneWage:
    """compute_zone_wage: per-capita, per-tick average wage over the
    trailing ZONE_WAGE_WINDOW_TICKS-tick window.
    """

    @pytest.mark.django_db
    def test_averages_wage_rows_in_zone_per_capita_over_window(self, sim_with_zone, currency):
        sim, zone = sim_with_zone
        other_zone = _make_other_zone(zone.world)
        alice = _make_agent(sim, zone, "Alice")
        bob = _make_agent(sim, zone, "Bob")
        stranger = _make_agent(sim, other_zone, "Stranger")

        tick = 50
        # In-window, in-zone wage rows -- these are the only rows that
        # should count.
        _make_wage(sim, currency, alice, tick=46, amount=100.0)
        _make_wage(sim, currency, alice, tick=50, amount=200.0)
        _make_wage(sim, currency, bob, tick=48, amount=50.0)
        # Distractors, each excluded for a distinct documented reason.
        _make_wage(sim, currency, alice, tick=44, amount=999.0)  # outside window (< tick-5)
        _make_wage(sim, currency, stranger, tick=48, amount=999.0)  # wrong zone
        EconomicLedger.objects.create(
            simulation=sim,
            tick=48,
            to_agent=alice,
            currency=currency,
            total_amount=999.0,
            transaction_type="trade",  # wrong transaction_type
        )

        wage = compute_zone_wage(sim, zone, tick, window=5)

        # (100 + 200 + 50) / (population=2 * window=5) = 350 / 10 = 35.0
        assert wage == pytest.approx(35.0)

    @pytest.mark.django_db
    def test_wage_row_exactly_at_lower_window_bound_is_included(self, sim_with_zone, currency):
        sim, zone = sim_with_zone
        alice = _make_agent(sim, zone, "Alice")
        tick = 50
        _make_wage(sim, currency, alice, tick=tick - 5, amount=100.0)  # tick - window

        wage = compute_zone_wage(sim, zone, tick, window=5)

        assert wage == pytest.approx(100.0 / (1 * 5))

    @pytest.mark.django_db
    def test_wage_row_just_before_lower_window_bound_is_excluded(self, sim_with_zone, currency):
        sim, zone = sim_with_zone
        alice = _make_agent(sim, zone, "Alice")
        tick = 50
        _make_wage(sim, currency, alice, tick=tick - 6, amount=100.0)  # tick - window - 1

        wage = compute_zone_wage(sim, zone, tick, window=5)

        assert wage == pytest.approx(0.0)

    @pytest.mark.django_db
    def test_wage_row_exactly_at_current_tick_is_included(self, sim_with_zone, currency):
        sim, zone = sim_with_zone
        alice = _make_agent(sim, zone, "Alice")
        tick = 50
        _make_wage(sim, currency, alice, tick=tick, amount=100.0)

        wage = compute_zone_wage(sim, zone, tick, window=5)

        assert wage == pytest.approx(100.0 / (1 * 5))

    @pytest.mark.django_db
    def test_zero_population_zone_returns_zero_without_dividing_by_zero(
        self, sim_with_zone, currency
    ):
        sim, zone = sim_with_zone

        wage = compute_zone_wage(sim, zone, tick=50, window=5)

        assert wage == pytest.approx(0.0)

    @pytest.mark.django_db
    def test_dead_agent_excluded_from_population_denominator(self, sim_with_zone, currency):
        sim, zone = sim_with_zone
        _make_agent(sim, zone, "DeadAgent", is_alive=False)
        alice = _make_agent(sim, zone, "Alice")
        tick = 50
        _make_wage(sim, currency, alice, tick=tick, amount=100.0)

        wage = compute_zone_wage(sim, zone, tick, window=5)

        # Population is 1 (DeadAgent excluded), not 2.
        assert wage == pytest.approx(100.0 / (1 * 5))

    @pytest.mark.django_db
    def test_default_window_matches_the_module_constant(self, sim_with_zone, currency):
        assert ZONE_WAGE_WINDOW_TICKS == 5

    @pytest.mark.django_db
    def test_query_count_is_bounded_regardless_of_agent_or_ledger_row_count(
        self, sim_with_zone, currency, django_assert_num_queries
    ):
        sim, zone = sim_with_zone
        agents = [_make_agent(sim, zone, f"Agent{i}") for i in range(5)]
        tick = 50
        for i, agent in enumerate(agents):
            for offset in range(3):
                _make_wage(sim, currency, agent, tick=tick - offset, amount=10.0 + i)

        # 1 query for the living-population count, 1 aggregate query for
        # the wage sum -- bounded regardless of agent or ledger row count.
        with django_assert_num_queries(2):
            compute_zone_wage(sim, zone, tick, window=5)


# ---------------------------------------------------------------------------
# compute_zone_unemployment (Plan 3, T030/T031, user story 4)
# ---------------------------------------------------------------------------
#
# Operational definition PINNED by these tests: the denominator is the
# living population of `zone` that HAS a role (`Agent.role` non-blank);
# the numerator is the subset of that denominator that received NO
# `wage`-type EconomicLedger credit (`to_agent__zone`) within the CLOSED
# interval [tick - ZONE_UNEMPLOYMENT_WINDOW_TICKS, tick]. An agent with no
# role at all is excluded from BOTH numerator and denominator (this
# function measures joblessness among the nominally employed -- a role-
# holder drawing no wage -- not raw labor-force non-participation).
# Zero role-holders returns 0.0 without dividing by zero (FR-028).


class TestComputeZoneUnemployment:
    """compute_zone_unemployment: fraction of role-holding living agents
    in `zone` who drew no wage over the trailing
    ZONE_UNEMPLOYMENT_WINDOW_TICKS-tick window.
    """

    @pytest.mark.django_db
    def test_role_holders_without_wage_count_as_unemployed(self, sim_with_zone, currency):
        sim, zone = sim_with_zone
        paid = _make_agent(sim, zone, "Paid", role="blacksmith")
        unpaid_one = _make_agent(sim, zone, "UnpaidOne", role="farmer")
        unpaid_two = _make_agent(sim, zone, "UnpaidTwo", role="weaver")
        tick = 50
        _make_wage(sim, currency, paid, tick=tick, amount=10.0)

        unemployment = compute_zone_unemployment(sim, zone, tick)

        # 2 of 3 role-holders drew no wage: 2 / 3.
        assert unemployment == pytest.approx(2.0 / 3.0)
        assert unpaid_one.role and unpaid_two.role  # self-check: both are role-holders

    @pytest.mark.django_db
    def test_agent_without_a_role_is_excluded_from_the_denominator(self, sim_with_zone, currency):
        sim, zone = sim_with_zone
        _make_agent(sim, zone, "Roleless", role="")
        paid = _make_agent(sim, zone, "Paid", role="blacksmith")
        tick = 50
        _make_wage(sim, currency, paid, tick=tick, amount=10.0)

        unemployment = compute_zone_unemployment(sim, zone, tick)

        # Sole role-holder is paid: 0 / 1 = 0.0, not diluted by the
        # roleless agent.
        assert unemployment == pytest.approx(0.0)

    @pytest.mark.django_db
    def test_dead_role_holder_is_excluded_from_the_denominator(self, sim_with_zone, currency):
        sim, zone = sim_with_zone
        _make_agent(sim, zone, "DeadRoleHolder", role="farmer", is_alive=False)
        paid = _make_agent(sim, zone, "Paid", role="blacksmith")
        tick = 50
        _make_wage(sim, currency, paid, tick=tick, amount=10.0)

        unemployment = compute_zone_unemployment(sim, zone, tick)

        assert unemployment == pytest.approx(0.0)

    @pytest.mark.django_db
    def test_wage_exactly_at_window_lower_bound_counts_as_employed(self, sim_with_zone, currency):
        sim, zone = sim_with_zone
        agent = _make_agent(sim, zone, "Agent", role="farmer")
        tick = 50
        _make_wage(sim, currency, agent, tick=tick - 3, amount=10.0)  # tick - window

        unemployment = compute_zone_unemployment(sim, zone, tick)

        assert unemployment == pytest.approx(0.0)

    @pytest.mark.django_db
    def test_wage_just_before_window_lower_bound_still_counts_as_unemployed(
        self, sim_with_zone, currency
    ):
        sim, zone = sim_with_zone
        agent = _make_agent(sim, zone, "Agent", role="farmer")
        tick = 50
        _make_wage(sim, currency, agent, tick=tick - 4, amount=10.0)  # tick - window - 1

        unemployment = compute_zone_unemployment(sim, zone, tick)

        assert unemployment == pytest.approx(1.0)

    @pytest.mark.django_db
    def test_zero_role_holders_returns_zero_without_dividing_by_zero(self, sim_with_zone, currency):
        sim, zone = sim_with_zone
        _make_agent(sim, zone, "Roleless", role="")

        unemployment = compute_zone_unemployment(sim, zone, tick=50)

        assert unemployment == pytest.approx(0.0)

    @pytest.mark.django_db
    def test_default_window_matches_the_module_constant(self):
        assert ZONE_UNEMPLOYMENT_WINDOW_TICKS == 3

    @pytest.mark.django_db
    def test_query_count_is_bounded_regardless_of_agent_or_ledger_row_count(
        self, sim_with_zone, currency, django_assert_num_queries
    ):
        sim, zone = sim_with_zone
        agents = [_make_agent(sim, zone, f"Agent{i}", role="farmer") for i in range(5)]
        tick = 50
        for agent in agents[:3]:
            _make_wage(sim, currency, agent, tick=tick, amount=10.0)

        # 1 query for the role-holder denominator count, 1 query for the
        # unpaid-count (the wage-paid id set is embedded as a SQL
        # subquery, not a second round trip) -- bounded regardless of
        # agent or ledger row count.
        with django_assert_num_queries(2):
            compute_zone_unemployment(sim, zone, tick)


# ---------------------------------------------------------------------------
# compute_distance_cost (Plan 3, T032, user story 4)
# ---------------------------------------------------------------------------
#
# Conversion chain (pinned by these tests -- see compute_distance_cost's
# own docstring for the full unit-by-unit account): grid-unit distance
# between the two zone centers (math.hypot on Point.x/.y, matching
# agents/movement.py's own execute_movement) -> km (grid units *
# World.distance_scale meters-per-unit / 1000) -> ticks (km / (TRAVEL_
# SPEEDS["foot"] km/day * World.tick_duration_hours/24 days/tick)),
# ceiling-rounded to a whole number of ticks.


class TestComputeDistanceCost:
    """compute_distance_cost: whole-tick travel cost between two zone
    centers, reusing agents/movement.py's canonical km<->grid-unit
    conversion (never calculate_max_distance itself, which layers on
    health/stability/repression/terrain factors that do not belong in an
    abstract zone-to-zone cost).
    """

    @pytest.mark.django_db
    def test_same_zone_returns_zero(self, sim_with_zone):
        sim, zone = sim_with_zone

        cost = compute_distance_cost(zone, zone, zone.world)

        assert cost == 0

    @pytest.mark.django_db
    def test_zero_distance_between_distinct_zones_returns_zero(self, sim_with_zone):
        sim, zone = sim_with_zone
        world = zone.world
        same_spot = _make_zone_at(world, 50, 50, "SameSpot")

        cost = compute_distance_cost(zone, same_spot, world)

        assert cost == 0

    @pytest.mark.django_db
    def test_matches_hand_computed_conversion_chain_at_default_world_scale(self, sim_with_zone):
        """World defaults: distance_scale=133.0 m/grid-unit,
        tick_duration_hours=24.0 (verified against the Zone/World fixture
        `sim_with_zone` builds, which does not override either field).

        Hand computation: grid distance = hypot(300, 400) = 500 (a 3-4-5
        triangle scaled by 100). distance_km = 500 * 133.0 / 1000 = 66.5.
        km_per_tick = 25.0 (TRAVEL_SPEEDS["foot"]) * (24.0 / 24.0) = 25.0.
        ticks = ceil(66.5 / 25.0) = ceil(2.66) = 3.
        """
        sim, zone = sim_with_zone
        world = zone.world
        assert world.distance_scale == pytest.approx(133.0)  # self-check: default
        assert world.tick_duration_hours == pytest.approx(24.0)  # self-check: default

        origin = _make_zone_at(world, 0, 0, "Origin")
        destination = _make_zone_at(world, 300, 400, "Destination")

        cost = compute_distance_cost(origin, destination, world)

        assert cost == 3

    @pytest.mark.django_db
    def test_exact_multiple_of_daily_range_does_not_round_up(self, sim_with_zone):
        """distance_scale=1000.0 (1 grid unit = 1 km exactly) isolates the
        ceiling behavior from the default scale's arithmetic. km_per_tick
        = 25.0 km/day * 1.0 day/tick = 25.0. A distance of EXACTLY 50.0 km
        (two full days of walking) must return 2, not 3.
        """
        sim, zone = sim_with_zone
        world = zone.world
        world.distance_scale = 1000.0
        world.save(update_fields=["distance_scale"])

        origin = _make_zone_at(world, 0, 0, "Origin")
        destination = _make_zone_at(world, 50, 0, "Destination")

        cost = compute_distance_cost(origin, destination, world)

        assert cost == 2

    @pytest.mark.django_db
    def test_any_partial_tick_rounds_up(self, sim_with_zone):
        """Same setup as the exact-multiple test above, but the distance
        is 50.1 km, 0.1 km past two full days -- must round UP to 3, not
        truncate to 2. This is the ceil() contract itself, isolated from
        the exact-multiple case.
        """
        sim, zone = sim_with_zone
        world = zone.world
        world.distance_scale = 1000.0
        world.save(update_fields=["distance_scale"])

        origin = _make_zone_at(world, 0, 0, "Origin")
        destination = _make_zone_at(world, 50.1, 0, "Destination")

        cost = compute_distance_cost(origin, destination, world)

        assert cost == 3

    @pytest.mark.django_db
    def test_tick_duration_hours_shortens_the_per_tick_range(self, sim_with_zone):
        """A half-length tick (tick_duration_hours=12.0, i.e. 0.5 days per
        tick) must HALVE the distance coverable per tick, not be ignored
        -- this is the preflight's own critical conversion (a 24x mistake
        would silently ignore this field entirely).

        distance_scale=1000.0 (1 grid unit = 1 km). km_per_tick = 25.0 *
        (12.0 / 24.0) = 12.5. A 25 km distance takes ceil(25 / 12.5) = 2
        ticks at this shortened tick length -- it would take only 1 tick
        if tick_duration_hours were (wrongly) ignored and treated as a
        full 24-hour day.
        """
        sim, zone = sim_with_zone
        world = zone.world
        world.distance_scale = 1000.0
        world.tick_duration_hours = 12.0
        world.save(update_fields=["distance_scale", "tick_duration_hours"])

        origin = _make_zone_at(world, 0, 0, "Origin")
        destination = _make_zone_at(world, 25, 0, "Destination")

        cost = compute_distance_cost(origin, destination, world)

        assert cost == 2

    @pytest.mark.django_db
    def test_returns_a_plain_int(self, sim_with_zone):
        sim, zone = sim_with_zone
        world = zone.world
        origin = _make_zone_at(world, 0, 0, "Origin")
        destination = _make_zone_at(world, 300, 400, "Destination")

        cost = compute_distance_cost(origin, destination, world)

        assert isinstance(cost, int)


# ---------------------------------------------------------------------------
# compute_expected_gain (Plan 3, T033, user story 4)
# ---------------------------------------------------------------------------
#
# Pure arithmetic -- no database access, no fixtures needed for the
# formula itself. `E[gain_j] = (1 - unemployment_j) * wage_j -
# wage_current - distance_cost_j`, the declared operational variant of
# Harris & Todaro (1970) fixed by the design spec (Sezione 6) and
# implemented here VERBATIM, including its own known, UNCORRECTED
# dimensional inconsistency: `(1 - unemployment_j) * wage_j` and
# `wage_current` are a currency RATE (the design's own worked example
# reports "LVR/tick"), while `distance_cost_j` (T032's own return value)
# is a whole COUNT OF TICKS -- subtracting a tick count from a currency
# rate does not balance dimensionally. See `compute_expected_gain`'s own
# docstring for the full disclosure; this plan implements the CONVERGED
# design as specified and does NOT silently correct it -- that decision
# is reserved for the phase-6 audit (T046, tracked as handoff open
# question 11).
#
# The worked numbers below (wage_current=78.0, Paris wage_j=90.0,
# unemployment_j=0.08, Lyon wage_j=81.0, unemployment_j=0.12,
# distance_cost_j=3.0 for Lyon) are read directly off the design spec's
# own `migration_outlook` example (docs/superpowers/specs/2026-04-18-
# demography-design-it.md, Sezione 6): the differentials it prints
# ("Paris: +12 LVR/tick", "Lyon: +3 LVR/tick") are wage_j - wage_current,
# so wage_current = 78.0 is recovered from Paris's own stated result
# ("Expected gain... se ti muovi a Paris: +4.8 LVR/tick" == (1-0.08)*90 -
# wage_current - 0, solved for wage_current).


class TestComputeExpectedGain:
    """compute_expected_gain: the declared Harris-Todaro operational
    variant, implemented verbatim per the CONVERGED design.
    """

    @pytest.mark.django_db
    def test_matches_the_design_specs_worked_paris_example(self):
        """Paris: unemployment_j=0.08, wage_j=90.0, wage_current=78.0,
        distance_cost_j=0.0 (design spec: "Costo distanza in tick: Paris
        0"). Hand computation: (1 - 0.08) * 90.0 - 78.0 - 0.0 = 82.8 -
        78.0 = 4.8, exactly matching the design spec's own stated
        "Expected gain Harris-Todaro se ti muovi a Paris: +4.8 LVR/tick".
        """
        gain = compute_expected_gain(
            unemployment_j=0.08, wage_j=90.0, wage_current=78.0, distance_cost_j=0.0
        )

        assert gain == pytest.approx(4.8)

    @pytest.mark.django_db
    def test_matches_hand_computed_value_for_a_generic_nonzero_case(self):
        """A second, independently hand-computed case (not the design
        spec's own worked example) so this test cannot pass merely by
        replicating one known-good number: (1 - 0.2) * 50.0 - 30.0 - 2.0
        = 40.0 - 30.0 - 2.0 = 8.0.
        """
        gain = compute_expected_gain(
            unemployment_j=0.2, wage_j=50.0, wage_current=30.0, distance_cost_j=2.0
        )

        assert gain == pytest.approx(8.0)

    @pytest.mark.django_db
    def test_zero_unemployment_and_zero_distance_cost_reduces_to_the_wage_differential(self):
        """Degenerate case, sanity-checks the formula's structure: with
        no unemployment penalty and no distance cost, the expected gain
        collapses to the raw wage differential.
        """
        gain = compute_expected_gain(
            unemployment_j=0.0, wage_j=90.0, wage_current=78.0, distance_cost_j=0.0
        )

        assert gain == pytest.approx(90.0 - 78.0)

    @pytest.mark.django_db
    def test_pins_declared_not_endorsed_behavior_at_nonzero_distance_cost(self):
        """DECLARED, NOT ENDORSED: this test documents what the CURRENT
        formula outputs when `distance_cost_j` is non-zero (the design
        spec's own Lyon figures: unemployment_j=0.12, wage_j=81.0,
        wage_current=78.0, distance_cost_j=3.0 -- "Costo distanza in
        tick: ... Lyon 3"), making the dimensional-inconsistency effect
        VISIBLE rather than latent, per the mandatory scientific
        disclosure this task carries. Hand computation: (1 - 0.12) * 81.0
        - 78.0 - 3.0 = 71.28 - 78.0 - 3.0 = -9.72.

        The magnitude problem this pins: `distance_cost_j=3.0` here means
        "3 ticks of travel", yet the formula subtracts it as if it were
        "3.0 LVR/tick" -- the SAME 3.0 would be subtracted whether it
        meant three ticks or three currency units, because the formula
        cannot tell the difference. This is NOT a claim that -9.72 is the
        scientifically correct expected gain for moving to Lyon; it is a
        pin of what this implementation currently, deliberately,
        UNCORRECTED returns, so a future reader (in particular the
        phase-6 audit, T046) sees the effect's actual size rather than
        having to re-derive it.
        """
        gain = compute_expected_gain(
            unemployment_j=0.12, wage_j=81.0, wage_current=78.0, distance_cost_j=3.0
        )

        assert gain == pytest.approx(-9.72)

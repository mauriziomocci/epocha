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

Also covers `build_migration_outlook` (Plan 3, T034): the per-agent
migration_outlook block (wage differential, unemployment, distance cost,
zone stability, expected gain per reachable zone), built ENTIRELY from
the caller-supplied `zone_stats` bundle with zero further database
queries -- the N+1 risk the task explicitly flags, since Plan 4 will call
this once per agent, per tick.

Also covers `coordinate_family_migration` (Plan 3, T035, Mincer 1978):
moving a decider's partner and minor children into the decider's target
zone in the same tick, as the single persisting orchestrator entry point
for family coordination.

Fixture conventions (`sim_with_zone`, `_make_agent`) mirror
`test_inheritance.py`'s own helpers by COPYING the pattern, not
importing it -- this file, like every other test module in this app,
owns its own fixtures.
"""

from __future__ import annotations

import pytest
from django.contrib.gis.geos import Point, Polygon

from epocha.apps.agents.models import Agent, DecisionLog
from epocha.apps.demography.couple import form_couple
from epocha.apps.demography.migration import (
    ZONE_UNEMPLOYMENT_WINDOW_TICKS,
    ZONE_WAGE_WINDOW_TICKS,
    build_migration_outlook,
    compute_distance_cost,
    compute_expected_gain,
    compute_zone_unemployment,
    compute_zone_wage,
    coordinate_family_migration,
)
from epocha.apps.demography.models import DemographyEvent
from epocha.apps.economy.models import Currency, EconomicLedger
from epocha.apps.simulation.models import Simulation
from epocha.apps.users.models import User
from epocha.apps.world.models import Government, World, Zone


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


# ---------------------------------------------------------------------------
# build_migration_outlook (Plan 3, T034, user story 4)
# ---------------------------------------------------------------------------
#
# zone_stats SHAPE (this function's own contract, designed and pinned by
# these tests -- not specified upstream of this task):
#
#   {
#       "world": <World instance>,
#       "government_stability": <float, Government.stability>,
#       "zones": {
#           zone_id: {
#               "zone": <Zone instance>,
#               "wage": <float, compute_zone_wage's return value>,
#               "unemployment": <float, compute_zone_unemployment's
#                   return value>,
#           },
#           ...
#       },
#   }
#
# Generalizes the task's own "zone aggregates computed once per tick,
# never recomputed per agent" principle to EVERY per-tick-constant input
# build_migration_outlook needs, not only wage/unemployment: Government
# has exactly one row per simulation (a OneToOneField, see PREFLIGHT
# point 1), and World likewise -- both are exactly as safe to bundle into
# a once-per-tick precomputed structure as the zone aggregates are, and
# bundling them here is what lets the per-agent call below cost ZERO
# database queries, not merely zero ZONE queries.
#
# "Reachable zone" definition PINNED by these tests: every zone present
# in `zone_stats["zones"]` OTHER than the agent's own current zone
# (`agent.zone_id`). No distance or radius bound is applied -- there is
# no "maximum travel range" concept anywhere in the schema, and
# `compute_distance_cost` already assigns a (possibly large) whole-tick
# cost to every zone, so nothing is truly unreachable; the simplest
# defensible reading, and the one implemented, is "every other zone of
# the agent's world".


def _make_government(sim, stability=0.7):
    return Government.objects.create(simulation=sim, stability=stability)


class TestBuildMigrationOutlook:
    """build_migration_outlook: the per-agent migration_outlook block,
    built entirely from `zone_stats` with zero further database queries.
    """

    @pytest.mark.django_db
    def test_query_count_is_zero_for_the_per_agent_call(
        self, sim_with_zone, currency, django_assert_num_queries
    ):
        """PRIMARY test (per T034's own acceptance criterion): the
        per-agent call must add NO further queries -- not merely no zone
        queries, literally none, since `zone_stats` (built here via real
        T031 calls, OUTSIDE the asserted block, representing the
        once-per-tick precomputation) already carries every per-tick
        constant this function needs.
        """
        sim, zone = sim_with_zone
        world = zone.world
        other_zone = _make_other_zone(world)
        government = _make_government(sim)
        agent = _make_agent(sim, zone, "Agent")

        zone_stats = {
            "world": world,
            "government_stability": government.stability,
            "zones": {
                z.id: {
                    "zone": z,
                    "wage": compute_zone_wage(sim, z, tick=50),
                    "unemployment": compute_zone_unemployment(sim, z, tick=50),
                }
                for z in (zone, other_zone)
            },
        }

        with django_assert_num_queries(0):
            build_migration_outlook(agent, sim, tick=50, zone_stats=zone_stats)

    @pytest.mark.django_db
    def test_carries_all_five_metrics_per_reachable_zone(self, sim_with_zone):
        """Hand-computed: wage_current=78.0 (agent's own zone), wage_j=
        90.0 (other zone) -> wage_differential=12.0. unemployment_j=0.08.
        distance_cost: the other zone sits at a (300, 400) grid offset
        from the agent's zone (center (50, 50) from `sim_with_zone`) at
        the default World scale -- the same hand-verified 3-tick result
        `TestComputeDistanceCost.
        test_matches_hand_computed_conversion_chain_at_default_world_scale`
        pins. zone_stability=0.7 (the single simulation-wide Government
        row). expected_gain = (1 - 0.08) * 90.0 - 78.0 - 3 = 1.8.
        """
        sim, zone = sim_with_zone
        world = zone.world
        other_zone = _make_zone_at(world, 350, 450, "OtherZone")  # (50,50) + (300,400)
        government = _make_government(sim, stability=0.7)
        agent = _make_agent(sim, zone, "Agent")

        zone_stats = {
            "world": world,
            "government_stability": government.stability,
            "zones": {
                zone.id: {"zone": zone, "wage": 78.0, "unemployment": 0.5},
                other_zone.id: {"zone": other_zone, "wage": 90.0, "unemployment": 0.08},
            },
        }

        outlook = build_migration_outlook(agent, sim, tick=50, zone_stats=zone_stats)

        entry = outlook["reachable_zones"][other_zone.id]
        assert entry["wage_differential"] == pytest.approx(12.0)
        assert entry["unemployment"] == pytest.approx(0.08)
        assert entry["distance_cost"] == 3
        assert entry["zone_stability"] == pytest.approx(0.7)
        assert entry["expected_gain"] == pytest.approx(1.8)

    @pytest.mark.django_db
    def test_agents_own_zone_is_excluded_from_reachable_zones(self, sim_with_zone):
        sim, zone = sim_with_zone
        world = zone.world
        other_zone = _make_other_zone(world)
        government = _make_government(sim)
        agent = _make_agent(sim, zone, "Agent")

        zone_stats = {
            "world": world,
            "government_stability": government.stability,
            "zones": {
                zone.id: {"zone": zone, "wage": 50.0, "unemployment": 0.1},
                other_zone.id: {"zone": other_zone, "wage": 60.0, "unemployment": 0.1},
            },
        }

        outlook = build_migration_outlook(agent, sim, tick=50, zone_stats=zone_stats)

        assert zone.id not in outlook["reachable_zones"]
        assert other_zone.id in outlook["reachable_zones"]

    @pytest.mark.django_db
    def test_reports_the_simulation_wide_stability_for_every_reachable_zone(self, sim_with_zone):
        """PREFLIGHT point 1: there is no per-zone stability anywhere in
        the schema (`Government` is a `OneToOneField` to `Simulation`) --
        every reachable zone must report the SAME simulation-wide value,
        never a fabricated per-zone proxy.
        """
        sim, zone = sim_with_zone
        world = zone.world
        zone_b = _make_other_zone(world, "ZoneB")
        zone_c = _make_zone_at(world, 500, 500, "ZoneC")
        government = _make_government(sim, stability=0.42)
        agent = _make_agent(sim, zone, "Agent")

        zone_stats = {
            "world": world,
            "government_stability": government.stability,
            "zones": {
                zone.id: {"zone": zone, "wage": 50.0, "unemployment": 0.1},
                zone_b.id: {"zone": zone_b, "wage": 55.0, "unemployment": 0.2},
                zone_c.id: {"zone": zone_c, "wage": 45.0, "unemployment": 0.3},
            },
        }

        outlook = build_migration_outlook(agent, sim, tick=50, zone_stats=zone_stats)

        assert outlook["reachable_zones"][zone_b.id]["zone_stability"] == pytest.approx(0.42)
        assert outlook["reachable_zones"][zone_c.id]["zone_stability"] == pytest.approx(0.42)

    @pytest.mark.django_db
    def test_reports_the_agents_current_zone_id(self, sim_with_zone):
        sim, zone = sim_with_zone
        world = zone.world
        other_zone = _make_other_zone(world)
        government = _make_government(sim)
        agent = _make_agent(sim, zone, "Agent")

        zone_stats = {
            "world": world,
            "government_stability": government.stability,
            "zones": {
                zone.id: {"zone": zone, "wage": 50.0, "unemployment": 0.1},
                other_zone.id: {"zone": other_zone, "wage": 60.0, "unemployment": 0.1},
            },
        }

        outlook = build_migration_outlook(agent, sim, tick=50, zone_stats=zone_stats)

        assert outlook["current_zone_id"] == zone.id


# ---------------------------------------------------------------------------
# coordinate_family_migration (Plan 3, T035, user story 4, Mincer 1978)
# ---------------------------------------------------------------------------


def _minimal_template():
    """The minimal template slice coordinate_family_migration reads --
    mirrors `test_inheritance.py`'s own `_heir_template` pattern of
    isolating tests from unrelated template sections.
    """
    return {"migration": {"adulthood_age": 16}}


class TestCoordinateFamilyMigration:
    """coordinate_family_migration: partner and minor children follow the
    decider into `target_zone` in the same tick (Mincer 1978), as a
    single persisting orchestrator call.
    """

    @pytest.mark.django_db
    def test_partner_moves_with_the_agent(self, sim_with_zone):
        sim, zone = sim_with_zone
        world = zone.world
        target_zone = _make_other_zone(world)
        agent = _make_agent(sim, zone, "Agent")
        partner = _make_agent(sim, zone, "Partner")
        form_couple(agent, partner, formed_at_tick=1)

        coordinate_family_migration(agent, target_zone, tick=50, template=_minimal_template())

        partner.refresh_from_db()
        assert partner.zone_id == target_zone.id

    @pytest.mark.django_db
    def test_minor_child_moves_with_the_agent(self, sim_with_zone):
        sim, zone = sim_with_zone
        world = zone.world
        target_zone = _make_other_zone(world)
        agent = _make_agent(sim, zone, "Agent")
        minor_child = _make_agent(sim, zone, "MinorChild", parent_agent=agent, age=10)

        coordinate_family_migration(agent, target_zone, tick=50, template=_minimal_template())

        minor_child.refresh_from_db()
        assert minor_child.zone_id == target_zone.id

    @pytest.mark.django_db
    def test_adult_child_does_not_move(self, sim_with_zone):
        sim, zone = sim_with_zone
        world = zone.world
        target_zone = _make_other_zone(world)
        agent = _make_agent(sim, zone, "Agent")
        adult_child = _make_agent(sim, zone, "AdultChild", parent_agent=agent, age=20)

        result = coordinate_family_migration(
            agent, target_zone, tick=50, template=_minimal_template()
        )

        adult_child.refresh_from_db()
        assert adult_child.zone_id == zone.id  # unchanged
        assert adult_child.id not in result

    @pytest.mark.django_db
    def test_dead_partner_is_excluded(self, sim_with_zone):
        sim, zone = sim_with_zone
        world = zone.world
        target_zone = _make_other_zone(world)
        agent = _make_agent(sim, zone, "Agent")
        dead_partner = _make_agent(sim, zone, "DeadPartner", is_alive=False)
        form_couple(agent, dead_partner, formed_at_tick=1)

        result = coordinate_family_migration(
            agent, target_zone, tick=50, template=_minimal_template()
        )

        dead_partner.refresh_from_db()
        assert dead_partner.zone_id == zone.id  # unchanged
        assert dead_partner.id not in result

    @pytest.mark.django_db
    def test_dead_minor_child_is_excluded(self, sim_with_zone):
        sim, zone = sim_with_zone
        world = zone.world
        target_zone = _make_other_zone(world)
        agent = _make_agent(sim, zone, "Agent")
        dead_child = _make_agent(sim, zone, "DeadChild", parent_agent=agent, age=10, is_alive=False)

        result = coordinate_family_migration(
            agent, target_zone, tick=50, template=_minimal_template()
        )

        dead_child.refresh_from_db()
        assert dead_child.zone_id == zone.id  # unchanged
        assert dead_child.id not in result

    @pytest.mark.django_db
    def test_no_active_couple_yields_no_partner_in_household(self, sim_with_zone):
        sim, zone = sim_with_zone
        world = zone.world
        target_zone = _make_other_zone(world)
        agent = _make_agent(sim, zone, "Agent")

        result = coordinate_family_migration(
            agent, target_zone, tick=50, template=_minimal_template()
        )

        assert result == []

    @pytest.mark.django_db
    def test_return_value_matches_household_members_in_the_event_payload(self, sim_with_zone):
        sim, zone = sim_with_zone
        world = zone.world
        target_zone = _make_other_zone(world)
        agent = _make_agent(sim, zone, "Agent")
        partner = _make_agent(sim, zone, "Partner")
        form_couple(agent, partner, formed_at_tick=1)
        minor_child = _make_agent(sim, zone, "MinorChild", parent_agent=agent, age=10)

        result = coordinate_family_migration(
            agent, target_zone, tick=50, template=_minimal_template()
        )

        event = DemographyEvent.objects.get(
            simulation=sim, event_type=DemographyEvent.EventType.MIGRATION, primary_agent=agent
        )
        assert set(result) == {partner.id, minor_child.id}
        assert set(event.payload["household_members"]) == set(result)

    @pytest.mark.django_db
    def test_single_migration_event_has_the_documented_payload_shape(self, sim_with_zone):
        sim, zone = sim_with_zone
        world = zone.world
        target_zone = _make_other_zone(world)
        agent = _make_agent(sim, zone, "Agent")
        partner = _make_agent(sim, zone, "Partner")
        form_couple(agent, partner, formed_at_tick=1)

        coordinate_family_migration(agent, target_zone, tick=50, template=_minimal_template())

        events = DemographyEvent.objects.filter(
            simulation=sim, event_type=DemographyEvent.EventType.MIGRATION, primary_agent=agent
        )
        assert events.count() == 1
        event = events.get()
        assert event.tick == 50
        assert event.payload["from_zone"] == zone.id
        assert event.payload["to_zone"] == target_zone.id
        assert event.payload["reason"] == "voluntary"
        assert event.payload["household_members"] == [partner.id]

    @pytest.mark.django_db
    def test_no_decision_log_rows_or_extra_events_are_created_for_minors(self, sim_with_zone):
        """Pins the absence side of "minors are not called to the
        decision loop": no `DecisionLog` row and no additional
        `DemographyEvent` exist for the minor child -- enforcement of the
        decision loop itself (i.e. never OFFERING a minor a `move_to`
        choice) is Plan 4 orchestrator's responsibility, not asserted
        here; this function simply never creates either kind of row for
        anyone but the single household-level MIGRATION event.
        """
        sim, zone = sim_with_zone
        world = zone.world
        target_zone = _make_other_zone(world)
        agent = _make_agent(sim, zone, "Agent")
        minor_child = _make_agent(sim, zone, "MinorChild", parent_agent=agent, age=10)

        coordinate_family_migration(agent, target_zone, tick=50, template=_minimal_template())

        assert not DecisionLog.objects.filter(agent=minor_child).exists()
        assert (
            DemographyEvent.objects.filter(
                simulation=sim, event_type=DemographyEvent.EventType.MIGRATION
            ).count()
            == 1
        )

    @pytest.mark.django_db
    def test_empty_household_creates_no_event_and_returns_empty_list(self, sim_with_zone):
        sim, zone = sim_with_zone
        world = zone.world
        target_zone = _make_other_zone(world)
        agent = _make_agent(sim, zone, "Agent")

        result = coordinate_family_migration(
            agent, target_zone, tick=50, template=_minimal_template()
        )

        assert result == []
        assert not DemographyEvent.objects.filter(
            simulation=sim, event_type=DemographyEvent.EventType.MIGRATION
        ).exists()

    @pytest.mark.django_db
    def test_query_count_is_bounded_not_per_child(self, sim_with_zone, django_assert_num_queries):
        sim, zone = sim_with_zone
        world = zone.world
        target_zone = _make_other_zone(world)
        agent = _make_agent(sim, zone, "Agent")
        partner = _make_agent(sim, zone, "Partner")
        form_couple(agent, partner, formed_at_tick=1)
        for i in range(5):
            _make_agent(sim, zone, f"MinorChild{i}", parent_agent=agent, age=10)

        # active_couple_for (1) + partner fetch (1) + minor-children fetch
        # (1) + bulk_update (1) + event create (1) = 5, bounded regardless
        # of how many minor children exist.
        with django_assert_num_queries(5):
            coordinate_family_migration(agent, target_zone, tick=50, template=_minimal_template())

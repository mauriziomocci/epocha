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

Also covers `evaluate_emergency_flight` (Plan 3, T036/T037, user story 5,
O'Rourke 1994 / Simon 1955): the three-condition trapped-vs-flight
trigger (fix I-5), and the SIGNATURE CHANGE (user-approved, 2026-07-20)
that threads `consecutive_ticks_under_subsistence` in as an explicit
argument rather than reading or deriving it -- see
`evaluate_emergency_flight`'s own docstring for the full account of why.

Also covers `process_emergency_flight` (Plan 3, T038/T039, user story 5
closing task): the whole-population orchestrator driving
`evaluate_emergency_flight` over every living agent, executing forced
flight via `coordinate_family_migration`, emitting `TRAPPED_CRISIS` with
its MISS-3 co-zone memory propagation, and emitting `MASS_FLIGHT` above
the 30% threshold -- see `TestProcessEmergencyFlight*`'s own module-level
note for the mass-flight denominator/window reading this suite pins.

Fixture conventions (`sim_with_zone`, `_make_agent`) mirror
`test_inheritance.py`'s own helpers by COPYING the pattern, not
importing it -- this file, like every other test module in this app,
owns its own fixtures.
"""

from __future__ import annotations

import pytest
from django.contrib.gis.geos import Point, Polygon

from epocha.apps.agents.models import Agent, DecisionLog, Memory
from epocha.apps.demography.couple import form_couple
from epocha.apps.demography.migration import (
    EMERGENCY_FLIGHT_MEMORY_WEIGHT,
    TRAPPED_CRISIS_MEMORY_WEIGHT,
    ZONE_UNEMPLOYMENT_WINDOW_TICKS,
    ZONE_WAGE_WINDOW_TICKS,
    build_migration_outlook,
    compute_distance_cost,
    compute_expected_gain,
    compute_zone_unemployment,
    compute_zone_wage,
    coordinate_family_migration,
    evaluate_emergency_flight,
    process_emergency_flight,
)
from epocha.apps.demography.models import DemographyEvent
from epocha.apps.demography.template_loader import load_template
from epocha.apps.economy.models import Currency, EconomicLedger, GoodCategory, ZoneEconomy
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


# ---------------------------------------------------------------------------
# evaluate_emergency_flight (Plan 3, T036/T037, user story 5). O'Rourke,
# K.H. (1994) grounds forced, survival-driven migration (the Irish
# Famine as the calibration target); Simon, H.A. (1955) grounds bounded
# rationality -- below a survival threshold, deliberation itself is
# bypassed, not merely accelerated.
#
# SIGNATURE CHANGE (user-approved, 2026-07-20, recorded in the handoff's
# decisions section -- see evaluate_emergency_flight's own docstring for
# the full account): `consecutive_ticks_under_subsistence` does not exist
# anywhere in the schema (verified exhaustively by the coordinator -- no
# `Agent` field, no per-agent wealth history, `PopulationSnapshot` is
# simulation-aggregated, not per-agent). It is threaded in as an explicit
# argument, never read off `agent` and never derived -- Plan 4 owns
# creating the storage and feeding it; until it does, this function
# cannot fire in a live run, consistent with demography not being wired
# into the tick loop yet.
#
# The subsistence threshold fixture below (GoodCategory + ZoneEconomy)
# mirrors the exact pattern already established in
# demography/tests/test_context.py's own compute_subsistence_threshold
# tests: base_price=10.0, price_elasticity=0.3, market_prices={"FOOD":
# 5.0} -> threshold = 5.0 * SUBSISTENCE_NEED_PER_AGENT(1.0) = 5.0.


def _make_subsistence_threshold_of_five(sim, zone):
    """Sets up a GoodCategory + ZoneEconomy pair yielding
    compute_subsistence_threshold(sim, zone) == 5.0. Mirrors
    test_context.py's own fixture pattern exactly.
    """
    good = GoodCategory.objects.create(
        simulation=sim,
        code="FOOD",
        name="Food",
        is_essential=True,
        base_price=10.0,
        price_elasticity=0.3,
    )
    ZoneEconomy.objects.create(zone=zone, market_prices={good.code: 5.0})


def _flight_template(flight_trigger_ticks=30):
    """Minimal synthetic template slice, mirrors this file's own
    `_minimal_template` pattern for `coordinate_family_migration`.
    """
    return {"migration": {"flight_trigger_ticks": flight_trigger_ticks}}


class TestEvaluateEmergencyFlight:
    """evaluate_emergency_flight: fires ONLY when all three conditions
    hold simultaneously (fix I-5's third condition is what separates
    flight from the trapped case T038/T039 will handle).
    """

    @pytest.mark.django_db
    def test_fires_when_all_three_conditions_hold(self, sim_with_zone):
        sim, zone = sim_with_zone
        world = zone.world
        other_zone = _make_zone_at(world, 50, 50, "OtherZone")  # same center: 0 distance cost
        _make_subsistence_threshold_of_five(sim, zone)
        agent = _make_agent(sim, zone, "Agent", wealth=4.0)  # below the 5.0 threshold

        zone_stats = {
            "world": world,
            "government_stability": 0.5,
            "zones": {
                zone.id: {"zone": zone, "wage": 50.0, "unemployment": 0.1},
                other_zone.id: {"zone": other_zone, "wage": 90.0, "unemployment": 0.0},
            },
        }

        target = evaluate_emergency_flight(
            agent,
            sim,
            tick=50,
            template=_flight_template(30),
            zone_stats=zone_stats,
            consecutive_ticks_under_subsistence=30,
        )

        assert target == other_zone

    @pytest.mark.django_db
    def test_does_not_fire_when_wealth_is_not_below_threshold(self, sim_with_zone):
        """Two of three: ticks-under-subsistence and a positive-gain zone
        both hold, but wealth is NOT below the subsistence threshold.
        """
        sim, zone = sim_with_zone
        world = zone.world
        other_zone = _make_zone_at(world, 50, 50, "OtherZone")
        _make_subsistence_threshold_of_five(sim, zone)
        agent = _make_agent(sim, zone, "Agent", wealth=10.0)  # above the 5.0 threshold

        zone_stats = {
            "world": world,
            "government_stability": 0.5,
            "zones": {
                zone.id: {"zone": zone, "wage": 50.0, "unemployment": 0.1},
                other_zone.id: {"zone": other_zone, "wage": 90.0, "unemployment": 0.0},
            },
        }

        target = evaluate_emergency_flight(
            agent,
            sim,
            tick=50,
            template=_flight_template(30),
            zone_stats=zone_stats,
            consecutive_ticks_under_subsistence=30,
        )

        assert target is None

    @pytest.mark.django_db
    def test_does_not_fire_when_ticks_under_subsistence_is_below_the_trigger(self, sim_with_zone):
        """Two of three: wealth-below-threshold and a positive-gain zone
        both hold, but consecutive_ticks_under_subsistence has not yet
        reached the template's flight_trigger_ticks.
        """
        sim, zone = sim_with_zone
        world = zone.world
        other_zone = _make_zone_at(world, 50, 50, "OtherZone")
        _make_subsistence_threshold_of_five(sim, zone)
        agent = _make_agent(sim, zone, "Agent", wealth=4.0)

        zone_stats = {
            "world": world,
            "government_stability": 0.5,
            "zones": {
                zone.id: {"zone": zone, "wage": 50.0, "unemployment": 0.1},
                other_zone.id: {"zone": other_zone, "wage": 90.0, "unemployment": 0.0},
            },
        }

        target = evaluate_emergency_flight(
            agent,
            sim,
            tick=50,
            template=_flight_template(30),
            zone_stats=zone_stats,
            consecutive_ticks_under_subsistence=29,  # one short of the trigger
        )

        assert target is None

    @pytest.mark.django_db
    def test_does_not_fire_when_no_zone_offers_positive_gain_fix_i5_trapped_case(
        self, sim_with_zone
    ):
        """THE fix I-5 test: two of three hold -- wealth is below
        threshold AND the ticks-under-subsistence trigger is met -- but
        EVERY reachable zone's expected gain is non-positive. This is the
        TRAPPED case: T038/T039 (a later task) emits TRAPPED_CRISIS for
        exactly this state. If this function fired here instead, the
        trapped-crisis phenomenon would never be observable -- conflating
        the two would silently erase it.
        """
        sim, zone = sim_with_zone
        world = zone.world
        other_zone_a = _make_zone_at(world, 50, 50, "OtherZoneA")
        other_zone_b = _make_zone_at(world, 50, 50, "OtherZoneB")
        _make_subsistence_threshold_of_five(sim, zone)
        agent = _make_agent(sim, zone, "Agent", wealth=4.0)

        zone_stats = {
            "world": world,
            "government_stability": 0.5,
            "zones": {
                zone.id: {"zone": zone, "wage": 50.0, "unemployment": 0.1},
                # Both candidate zones are WORSE than staying: negative
                # expected gain each, so no positive-gain zone exists.
                other_zone_a.id: {"zone": other_zone_a, "wage": 50.0, "unemployment": 0.5},
                other_zone_b.id: {"zone": other_zone_b, "wage": 40.0, "unemployment": 0.2},
            },
        }

        target = evaluate_emergency_flight(
            agent,
            sim,
            tick=50,
            template=_flight_template(30),
            zone_stats=zone_stats,
            consecutive_ticks_under_subsistence=30,
        )

        assert target is None

    @pytest.mark.django_db
    def test_returns_the_highest_gain_zone_among_several_positive_options(self, sim_with_zone):
        sim, zone = sim_with_zone
        world = zone.world
        low_gain_zone = _make_zone_at(world, 50, 50, "LowGainZone")
        best_gain_zone = _make_zone_at(world, 50, 50, "BestGainZone")
        mid_gain_zone = _make_zone_at(world, 50, 50, "MidGainZone")
        _make_subsistence_threshold_of_five(sim, zone)
        agent = _make_agent(sim, zone, "Agent", wealth=4.0)

        zone_stats = {
            "world": world,
            "government_stability": 0.5,
            "zones": {
                zone.id: {"zone": zone, "wage": 50.0, "unemployment": 0.1},
                # expected_gain = (1-0.0)*wage - 50.0 - 0
                low_gain_zone.id: {"zone": low_gain_zone, "wage": 60.0, "unemployment": 0.0},  # 10
                best_gain_zone.id: {
                    "zone": best_gain_zone,
                    "wage": 90.0,
                    "unemployment": 0.0,
                },  # 40
                mid_gain_zone.id: {"zone": mid_gain_zone, "wage": 75.0, "unemployment": 0.0},  # 25
            },
        }

        target = evaluate_emergency_flight(
            agent,
            sim,
            tick=50,
            template=_flight_template(30),
            zone_stats=zone_stats,
            consecutive_ticks_under_subsistence=30,
        )

        assert target == best_gain_zone

    @pytest.mark.django_db
    def test_tie_break_is_zone_id_ascending(self, sim_with_zone):
        """Module convention (per T024's sibling tiebreak and this
        module's own established ordering discipline): equal expected
        gain breaks by zone id ascending.
        """
        sim, zone = sim_with_zone
        world = zone.world
        # Created in reverse id order so the lower-id zone is NOT simply
        # "whichever was inserted last" -- if the tiebreak silently
        # depended on insertion/iteration order instead of an explicit
        # id sort, this would catch it.
        higher_id_zone = _make_zone_at(world, 50, 50, "HigherIdZone")
        lower_id_zone = _make_zone_at(world, 50, 50, "LowerIdZoneCreatedSecond")
        assert higher_id_zone.id < lower_id_zone.id  # self-check on creation order

        # Re-fetch by explicit id comparison rather than trusting creation
        # order, since the ids ultimately decide the tiebreak, not which
        # variable name was used.
        ordered_pair = sorted([higher_id_zone, lower_id_zone], key=lambda z: z.id)
        expected_winner = ordered_pair[0]

        _make_subsistence_threshold_of_five(sim, zone)
        agent = _make_agent(sim, zone, "Agent", wealth=4.0)

        zone_stats = {
            "world": world,
            "government_stability": 0.5,
            "zones": {
                zone.id: {"zone": zone, "wage": 50.0, "unemployment": 0.1},
                higher_id_zone.id: {"zone": higher_id_zone, "wage": 90.0, "unemployment": 0.0},
                lower_id_zone.id: {"zone": lower_id_zone, "wage": 90.0, "unemployment": 0.0},
            },
        }

        target = evaluate_emergency_flight(
            agent,
            sim,
            tick=50,
            template=_flight_template(30),
            zone_stats=zone_stats,
            consecutive_ticks_under_subsistence=30,
        )

        assert target == expected_winner

    @pytest.mark.django_db
    def test_flight_trigger_ticks_is_read_from_the_template_not_hardcoded(self, sim_with_zone):
        """PREFLIGHT point 1: flight_trigger_ticks is 20 for industrial,
        10 for modern_democracy (verified against both template JSON
        files) -- NOT universally 30. With
        consecutive_ticks_under_subsistence=15, the SAME agent state
        fires under modern_democracy (15 >= 10) but does not fire under
        industrial (15 < 20), proving the value is actually read from the
        template rather than a hardcoded default.
        """
        sim, zone = sim_with_zone
        world = zone.world
        other_zone = _make_zone_at(world, 50, 50, "OtherZone")
        _make_subsistence_threshold_of_five(sim, zone)
        agent = _make_agent(sim, zone, "Agent", wealth=4.0)

        zone_stats = {
            "world": world,
            "government_stability": 0.5,
            "zones": {
                zone.id: {"zone": zone, "wage": 50.0, "unemployment": 0.1},
                other_zone.id: {"zone": other_zone, "wage": 90.0, "unemployment": 0.0},
            },
        }

        industrial_template = load_template("industrial")
        assert industrial_template["migration"]["flight_trigger_ticks"] == 20  # self-check

        modern_template = load_template("modern_democracy")
        assert modern_template["migration"]["flight_trigger_ticks"] == 10  # self-check

        target_under_industrial = evaluate_emergency_flight(
            agent,
            sim,
            tick=50,
            template=industrial_template,
            zone_stats=zone_stats,
            consecutive_ticks_under_subsistence=15,
        )
        target_under_modern = evaluate_emergency_flight(
            agent,
            sim,
            tick=50,
            template=modern_template,
            zone_stats=zone_stats,
            consecutive_ticks_under_subsistence=15,
        )

        assert target_under_industrial is None
        assert target_under_modern == other_zone

    @pytest.mark.django_db
    def test_wealth_exactly_at_threshold_does_not_fire(self, sim_with_zone):
        """Boundary: "wealth BELOW threshold" is a strict `<` -- wealth
        exactly equal to the threshold does not qualify.
        """
        sim, zone = sim_with_zone
        world = zone.world
        other_zone = _make_zone_at(world, 50, 50, "OtherZone")
        _make_subsistence_threshold_of_five(sim, zone)
        agent = _make_agent(sim, zone, "Agent", wealth=5.0)  # exactly the threshold

        zone_stats = {
            "world": world,
            "government_stability": 0.5,
            "zones": {
                zone.id: {"zone": zone, "wage": 50.0, "unemployment": 0.1},
                other_zone.id: {"zone": other_zone, "wage": 90.0, "unemployment": 0.0},
            },
        }

        target = evaluate_emergency_flight(
            agent,
            sim,
            tick=50,
            template=_flight_template(30),
            zone_stats=zone_stats,
            consecutive_ticks_under_subsistence=30,
        )

        assert target is None

    @pytest.mark.django_db
    def test_ticks_exactly_at_trigger_fires(self, sim_with_zone):
        """Boundary: `consecutive_ticks_under_subsistence >=
        flight_trigger_ticks` is inclusive -- exactly at the trigger
        value fires.
        """
        sim, zone = sim_with_zone
        world = zone.world
        other_zone = _make_zone_at(world, 50, 50, "OtherZone")
        _make_subsistence_threshold_of_five(sim, zone)
        agent = _make_agent(sim, zone, "Agent", wealth=4.0)

        zone_stats = {
            "world": world,
            "government_stability": 0.5,
            "zones": {
                zone.id: {"zone": zone, "wage": 50.0, "unemployment": 0.1},
                other_zone.id: {"zone": other_zone, "wage": 90.0, "unemployment": 0.0},
            },
        }

        target = evaluate_emergency_flight(
            agent,
            sim,
            tick=50,
            template=_flight_template(30),
            zone_stats=zone_stats,
            consecutive_ticks_under_subsistence=30,  # exactly the trigger
        )

        assert target == other_zone

    @pytest.mark.django_db
    def test_returns_none_when_no_reachable_zone_exists(self, sim_with_zone):
        sim, zone = sim_with_zone
        world = zone.world
        _make_subsistence_threshold_of_five(sim, zone)
        agent = _make_agent(sim, zone, "Agent", wealth=4.0)

        zone_stats = {
            "world": world,
            "government_stability": 0.5,
            "zones": {
                zone.id: {"zone": zone, "wage": 50.0, "unemployment": 0.1},
            },
        }

        target = evaluate_emergency_flight(
            agent,
            sim,
            tick=50,
            template=_flight_template(30),
            zone_stats=zone_stats,
            consecutive_ticks_under_subsistence=30,
        )

        assert target is None

    @pytest.mark.django_db
    def test_query_count_is_bounded(self, sim_with_zone, django_assert_num_queries):
        """Per PREFLIGHT point 6: this will be driven over the whole
        population by T039, so the per-agent call must add no zone-
        aggregate queries -- the only queries here come from
        `compute_subsistence_threshold`'s own cost (a ZoneEconomy get
        plus a GoodCategory fetch), never from re-deriving anything
        `zone_stats` already carries.
        """
        sim, zone = sim_with_zone
        world = zone.world
        other_zone = _make_zone_at(world, 50, 50, "OtherZone")
        _make_subsistence_threshold_of_five(sim, zone)
        agent = _make_agent(sim, zone, "Agent", wealth=4.0)

        zone_stats = {
            "world": world,
            "government_stability": 0.5,
            "zones": {
                zone.id: {"zone": zone, "wage": 50.0, "unemployment": 0.1},
                other_zone.id: {"zone": other_zone, "wage": 90.0, "unemployment": 0.0},
            },
        }

        with django_assert_num_queries(2):
            evaluate_emergency_flight(
                agent,
                sim,
                tick=50,
                template=_flight_template(30),
                zone_stats=zone_stats,
                consecutive_ticks_under_subsistence=30,
            )


# ---------------------------------------------------------------------------
# process_emergency_flight (Plan 3, T038/T039, user story 5 closing task).
# Design spec Sezione 6, "Emergency flight" and "Broadcast di mass
# flight". This is the Plan 4 orchestrator step 5 entry point (decision
# D3: no global state, every input passed explicitly).
#
# MASS-FLIGHT DENOMINATOR AND WINDOW (PINNED HERE, not specified
# precisely upstream -- a threshold whose denominator is ambiguous is not
# reproducible, per the task's own instruction): the denominator is each
# zone's LIVING population captured ONCE, at the START of this call,
# BEFORE any of this tick's flights execute -- the "baseline" a fleeing
# fraction is naturally measured against (measuring against the
# POST-flight, already-depleted population would inflate the fraction
# for the exact same underlying event). The numerator is every distinct
# agent who fled that zone via emergency flight (`DemographyEvent
# payload__reason="emergency_flight"`) with `tick` in the CLOSED-OPEN
# window `[tick - flight_trigger_ticks, tick)` for HISTORICAL flights
# (already persisted by earlier calls) PLUS every agent fleeing in THIS
# call (`tick` itself) -- i.e. exactly the flight_trigger_ticks-tick
# rolling window the design's own "fugge entro flight_trigger_ticks"
# wording describes. The threshold itself is STRICT: `> 0.30`, not `>=`.
#
# TRAPPED-VS-FLIGHT EXPOSURE: `process_emergency_flight` calls the same
# private `_resolve_flight_decision` helper `evaluate_emergency_flight`
# itself delegates to (see that helper's own docstring), getting BOTH
# `meets_preconditions` (conditions 1+2) and `target_zone` (the flight
# decision) from ONE call -- trapped is exactly `meets_preconditions and
# target_zone is None`.
#
# MISS-3 PROPAGATION SCOPE (an interpretive choice, flagged like the
# others made throughout this plan): "altri agenti testimoni" (OTHER
# witnessing agents) in the design's own rationale sentence reads as
# excluding the trapped agent from their own crisis's public-memory
# recipients -- they are living it, not witnessing it as public news.
# Pinned by `test_trapped_agent_does_not_receive_a_public_memory_about_
# their_own_crisis` below.


def _make_trapped_agent_setup(sim, zone, wealth=4.0, name="TrappedAgent"):
    """A starving agent with NO wage data anywhere -- expected_gain to
    every reachable zone is exactly 0.0 (wage_j=0, wage_current=0,
    distance_cost=0), which is NOT > 0, so the trapped path fires for any
    agent meeting the wealth/ticks preconditions. Requires
    `_make_subsistence_threshold_of_five` to have been called for `zone`
    first.
    """
    return _make_agent(sim, zone, name, wealth=wealth)


class TestProcessEmergencyFlightFlees:
    """A triggered flight migrates to the highest-gain zone, bypassing
    the LLM, applies family coordination, and writes the fleeing agent's
    own memory at emotional_weight=0.85.
    """

    @pytest.mark.django_db
    def test_triggered_flight_migrates_to_the_highest_gain_zone(self, sim_with_zone):
        sim, zone = sim_with_zone
        _make_government(sim)
        world = zone.world
        other_zone = _make_zone_at(world, 50, 50, "OtherZone")  # 0 distance cost
        currency = Currency.objects.create(
            simulation=sim, code="LVR", name="Livre", symbol="L", total_supply=50_000.0
        )
        worker = _make_agent(sim, other_zone, "Worker", role="")
        _make_wage(sim, currency, worker, tick=50, amount=250.0)  # wage(other) = 250/(1*5) = 50.0
        _make_subsistence_threshold_of_five(sim, zone)
        agent = _make_agent(sim, zone, "Agent", wealth=4.0)

        process_emergency_flight(
            sim, tick=50, consecutive_ticks_under_subsistence_by_agent_id={agent.id: 30}
        )

        agent.refresh_from_db()
        assert agent.zone_id == other_zone.id

    @pytest.mark.django_db
    def test_triggered_flight_applies_family_coordination(self, sim_with_zone):
        sim, zone = sim_with_zone
        _make_government(sim)
        world = zone.world
        other_zone = _make_zone_at(world, 50, 50, "OtherZone")
        currency = Currency.objects.create(
            simulation=sim, code="LVR", name="Livre", symbol="L", total_supply=50_000.0
        )
        worker = _make_agent(sim, other_zone, "Worker", role="")
        _make_wage(sim, currency, worker, tick=50, amount=250.0)
        _make_subsistence_threshold_of_five(sim, zone)
        agent = _make_agent(sim, zone, "Agent", wealth=4.0)
        partner = _make_agent(sim, zone, "Partner", wealth=100.0)
        form_couple(agent, partner, formed_at_tick=1)
        minor_child = _make_agent(sim, zone, "MinorChild", parent_agent=agent, age=10, wealth=0.0)

        process_emergency_flight(
            sim, tick=50, consecutive_ticks_under_subsistence_by_agent_id={agent.id: 30}
        )

        partner.refresh_from_db()
        minor_child.refresh_from_db()
        assert partner.zone_id == other_zone.id
        assert minor_child.zone_id == other_zone.id

    @pytest.mark.django_db
    def test_triggered_flight_writes_a_memory_at_weight_0_85(self, sim_with_zone):
        sim, zone = sim_with_zone
        _make_government(sim)
        world = zone.world
        other_zone = _make_zone_at(world, 50, 50, "OtherZone")
        currency = Currency.objects.create(
            simulation=sim, code="LVR", name="Livre", symbol="L", total_supply=50_000.0
        )
        worker = _make_agent(sim, other_zone, "Worker", role="")
        _make_wage(sim, currency, worker, tick=50, amount=250.0)
        _make_subsistence_threshold_of_five(sim, zone)
        agent = _make_agent(sim, zone, "Agent", wealth=4.0)

        process_emergency_flight(
            sim, tick=50, consecutive_ticks_under_subsistence_by_agent_id={agent.id: 30}
        )

        memory = Memory.objects.get(agent=agent, origin_agent=agent)
        assert memory.emotional_weight == pytest.approx(EMERGENCY_FLIGHT_MEMORY_WEIGHT)
        assert memory.emotional_weight == pytest.approx(0.85)
        assert memory.source_type == Memory.SourceType.DIRECT

    @pytest.mark.django_db
    def test_triggered_flight_bypasses_the_llm_no_decision_log_row(self, sim_with_zone):
        sim, zone = sim_with_zone
        _make_government(sim)
        world = zone.world
        other_zone = _make_zone_at(world, 50, 50, "OtherZone")
        currency = Currency.objects.create(
            simulation=sim, code="LVR", name="Livre", symbol="L", total_supply=50_000.0
        )
        worker = _make_agent(sim, other_zone, "Worker", role="")
        _make_wage(sim, currency, worker, tick=50, amount=250.0)
        _make_subsistence_threshold_of_five(sim, zone)
        agent = _make_agent(sim, zone, "Agent", wealth=4.0)

        process_emergency_flight(
            sim, tick=50, consecutive_ticks_under_subsistence_by_agent_id={agent.id: 30}
        )

        assert not DecisionLog.objects.filter(agent=agent).exists()

    @pytest.mark.django_db
    def test_flight_emits_a_migration_event_with_emergency_flight_reason(self, sim_with_zone):
        sim, zone = sim_with_zone
        _make_government(sim)
        world = zone.world
        other_zone = _make_zone_at(world, 50, 50, "OtherZone")
        currency = Currency.objects.create(
            simulation=sim, code="LVR", name="Livre", symbol="L", total_supply=50_000.0
        )
        worker = _make_agent(sim, other_zone, "Worker", role="")
        _make_wage(sim, currency, worker, tick=50, amount=250.0)
        _make_subsistence_threshold_of_five(sim, zone)
        agent = _make_agent(sim, zone, "Agent", wealth=4.0)

        process_emergency_flight(
            sim, tick=50, consecutive_ticks_under_subsistence_by_agent_id={agent.id: 30}
        )

        event = DemographyEvent.objects.get(
            simulation=sim, event_type=DemographyEvent.EventType.MIGRATION, primary_agent=agent
        )
        assert event.payload["reason"] == "emergency_flight"
        assert event.payload["from_zone"] == zone.id
        assert event.payload["to_zone"] == other_zone.id


class TestProcessEmergencyFlightTrapped:
    """An agent meeting the wealth/ticks preconditions but with no
    positive-gain zone is trapped: `TRAPPED_CRISIS` fires and propagates
    a memory to co-zone witnesses (fix MISS-3), never relocating anyone.
    """

    @pytest.mark.django_db
    def test_trapped_agent_emits_trapped_crisis_with_the_documented_payload(self, sim_with_zone):
        sim, zone = sim_with_zone
        _make_government(sim)
        _make_subsistence_threshold_of_five(sim, zone)
        agent = _make_trapped_agent_setup(sim, zone)

        process_emergency_flight(
            sim, tick=50, consecutive_ticks_under_subsistence_by_agent_id={agent.id: 30}
        )

        event = DemographyEvent.objects.get(
            simulation=sim,
            event_type=DemographyEvent.EventType.TRAPPED_CRISIS,
            primary_agent=agent,
        )
        assert event.payload["zone"] == zone.id
        assert event.payload["consecutive_under_subsistence"] == 30

    @pytest.mark.django_db
    def test_trapped_crisis_propagates_a_memory_to_every_co_zone_agent_fix_miss3(
        self, sim_with_zone
    ):
        sim, zone = sim_with_zone
        _make_government(sim)
        _make_subsistence_threshold_of_five(sim, zone)
        agent = _make_trapped_agent_setup(sim, zone)
        witness_one = _make_agent(sim, zone, "WitnessOne", wealth=100.0)
        witness_two = _make_agent(sim, zone, "WitnessTwo", wealth=100.0)

        process_emergency_flight(
            sim, tick=50, consecutive_ticks_under_subsistence_by_agent_id={agent.id: 30}
        )

        for witness in (witness_one, witness_two):
            memory = Memory.objects.get(agent=witness, origin_agent=agent)
            assert memory.emotional_weight == pytest.approx(TRAPPED_CRISIS_MEMORY_WEIGHT)
            assert memory.emotional_weight == pytest.approx(0.95)
            assert memory.source_type == Memory.SourceType.PUBLIC

    @pytest.mark.django_db
    def test_trapped_agent_does_not_receive_a_public_memory_about_their_own_crisis(
        self, sim_with_zone
    ):
        sim, zone = sim_with_zone
        _make_government(sim)
        _make_subsistence_threshold_of_five(sim, zone)
        agent = _make_trapped_agent_setup(sim, zone)

        process_emergency_flight(
            sim, tick=50, consecutive_ticks_under_subsistence_by_agent_id={agent.id: 30}
        )

        assert not Memory.objects.filter(
            agent=agent, origin_agent=agent, source_type=Memory.SourceType.PUBLIC
        ).exists()

    @pytest.mark.django_db
    def test_trapped_agent_is_never_relocated(self, sim_with_zone):
        sim, zone = sim_with_zone
        _make_government(sim)
        _make_subsistence_threshold_of_five(sim, zone)
        agent = _make_trapped_agent_setup(sim, zone)

        process_emergency_flight(
            sim, tick=50, consecutive_ticks_under_subsistence_by_agent_id={agent.id: 30}
        )

        agent.refresh_from_db()
        assert agent.zone_id == zone.id

    @pytest.mark.django_db
    def test_agent_with_only_two_of_three_conditions_triggers_neither_path(self, sim_with_zone):
        """Sanity check: not starving long enough (ticks below the
        trigger) yields neither a flight nor a trapped-crisis event, even
        though the agent IS below the subsistence threshold.
        """
        sim, zone = sim_with_zone
        _make_government(sim)
        _make_subsistence_threshold_of_five(sim, zone)
        agent = _make_trapped_agent_setup(sim, zone)

        process_emergency_flight(
            sim, tick=50, consecutive_ticks_under_subsistence_by_agent_id={agent.id: 5}
        )

        assert not DemographyEvent.objects.filter(simulation=sim).exists()
        assert not Memory.objects.filter(origin_agent=agent).exists()


class TestProcessEmergencyFlightMassFlight:
    """More than 30% of a zone's baseline living population fleeing
    within `flight_trigger_ticks` emits `MASS_FLIGHT` with the agent
    list.
    """

    @pytest.mark.django_db
    def test_mass_flight_emitted_when_over_30_percent_flee_in_one_call(self, sim_with_zone):
        sim, zone = sim_with_zone
        _make_government(sim)
        world = zone.world
        other_zone = _make_zone_at(world, 50, 50, "OtherZone")
        currency = Currency.objects.create(
            simulation=sim, code="LVR", name="Livre", symbol="L", total_supply=50_000.0
        )
        worker = _make_agent(sim, other_zone, "Worker", role="")
        _make_wage(sim, currency, worker, tick=50, amount=250.0)
        _make_subsistence_threshold_of_five(sim, zone)

        # 4 of 10 flee (40% > 30%); the other 6 are well-fed and stay.
        fleeing = [_make_agent(sim, zone, f"Fleeing{i}", wealth=4.0) for i in range(4)]
        for i in range(6):
            _make_agent(sim, zone, f"Stays{i}", wealth=100.0)

        counters = {agent.id: 30 for agent in fleeing}
        process_emergency_flight(
            sim, tick=50, consecutive_ticks_under_subsistence_by_agent_id=counters
        )

        event = DemographyEvent.objects.get(
            simulation=sim, event_type=DemographyEvent.EventType.MASS_FLIGHT
        )
        assert event.payload["from_zone"] == zone.id
        assert set(event.payload["agents"]) == {agent.id for agent in fleeing}
        assert event.payload["trigger_ticks"] == 30

    @pytest.mark.django_db
    def test_mass_flight_not_emitted_at_exactly_30_percent_strict_boundary(self, sim_with_zone):
        sim, zone = sim_with_zone
        _make_government(sim)
        world = zone.world
        other_zone = _make_zone_at(world, 50, 50, "OtherZone")
        currency = Currency.objects.create(
            simulation=sim, code="LVR", name="Livre", symbol="L", total_supply=50_000.0
        )
        worker = _make_agent(sim, other_zone, "Worker", role="")
        _make_wage(sim, currency, worker, tick=50, amount=250.0)
        _make_subsistence_threshold_of_five(sim, zone)

        # 3 of 10 flee: exactly 30%, NOT > 30% (strict).
        fleeing = [_make_agent(sim, zone, f"Fleeing{i}", wealth=4.0) for i in range(3)]
        for i in range(7):
            _make_agent(sim, zone, f"Stays{i}", wealth=100.0)

        counters = {agent.id: 30 for agent in fleeing}
        process_emergency_flight(
            sim, tick=50, consecutive_ticks_under_subsistence_by_agent_id=counters
        )

        assert not DemographyEvent.objects.filter(
            simulation=sim, event_type=DemographyEvent.EventType.MASS_FLIGHT
        ).exists()

    @pytest.mark.django_db
    def test_mass_flight_denominator_is_the_pre_flight_baseline_population(self, sim_with_zone):
        """Discriminating test for the denominator reading: 3 of 10 flee
        (exactly 30% of the PRE-flight population of 10, at the strict
        boundary, so it must NOT fire under the "before" reading this
        suite pins). Under a "post-flight remaining population" reading
        instead, the denominator would be 7 (10 - 3 fled), giving 3/7 ~=
        42.9% > 30%, which WOULD fire -- the two readings disagree on
        this exact scenario, which is why it is the discriminating case.
        """
        sim, zone = sim_with_zone
        _make_government(sim)
        world = zone.world
        other_zone = _make_zone_at(world, 50, 50, "OtherZone")
        currency = Currency.objects.create(
            simulation=sim, code="LVR", name="Livre", symbol="L", total_supply=50_000.0
        )
        worker = _make_agent(sim, other_zone, "Worker", role="")
        _make_wage(sim, currency, worker, tick=50, amount=250.0)
        _make_subsistence_threshold_of_five(sim, zone)

        fleeing = [_make_agent(sim, zone, f"Fleeing{i}", wealth=4.0) for i in range(3)]
        for i in range(7):
            _make_agent(sim, zone, f"Stays{i}", wealth=100.0)

        counters = {agent.id: 30 for agent in fleeing}
        process_emergency_flight(
            sim, tick=50, consecutive_ticks_under_subsistence_by_agent_id=counters
        )

        assert not DemographyEvent.objects.filter(
            simulation=sim, event_type=DemographyEvent.EventType.MASS_FLIGHT
        ).exists()

    @pytest.mark.django_db
    def test_mass_flight_window_combines_historical_and_new_flights(self, sim_with_zone):
        """A flight from an EARLIER tick (already persisted, its agent no
        longer even in `zone`) combines with THIS tick's new flight to
        cross the 30% baseline -- proving the rolling window looks
        backward across calls, not just at this single call's own
        fleeers.
        """
        sim, zone = sim_with_zone
        _make_government(sim)
        world = zone.world
        other_zone = _make_zone_at(world, 50, 50, "OtherZone")
        currency = Currency.objects.create(
            simulation=sim, code="LVR", name="Livre", symbol="L", total_supply=50_000.0
        )
        worker = _make_agent(sim, other_zone, "Worker", role="")
        _make_wage(sim, currency, worker, tick=50, amount=250.0)
        _make_subsistence_threshold_of_five(sim, zone)

        # Historical flight: already in other_zone, event persisted at
        # tick 25 (within the [20, 50) window for flight_trigger_ticks=30
        # at tick=50).
        # role="" keeps HistoricalFled out of other_zone's unemployment
        # denominator -- otherwise, being a role-holder with no wage row
        # of their own would push other_zone's unemployment to 100% and
        # its expected gain to 0, defeating this test's own setup.
        historical_agent = _make_agent(sim, other_zone, "HistoricalFled", wealth=100.0, role="")
        DemographyEvent.objects.create(
            simulation=sim,
            tick=25,
            event_type=DemographyEvent.EventType.MIGRATION,
            primary_agent=historical_agent,
            payload={
                "household_members": [],
                "from_zone": zone.id,
                "to_zone": other_zone.id,
                "reason": "emergency_flight",
            },
        )

        # 5 CURRENT living agents in zone -- the baseline population.
        new_fleeing = _make_agent(sim, zone, "NewFleeing", wealth=4.0)
        for i in range(4):
            _make_agent(sim, zone, f"Stays{i}", wealth=100.0)

        process_emergency_flight(
            sim,
            tick=50,
            consecutive_ticks_under_subsistence_by_agent_id={new_fleeing.id: 30},
        )

        # (1 historical + 1 new) / 5 baseline = 40% > 30%.
        event = DemographyEvent.objects.get(
            simulation=sim, event_type=DemographyEvent.EventType.MASS_FLIGHT
        )
        assert set(event.payload["agents"]) == {historical_agent.id, new_fleeing.id}

    @pytest.mark.django_db
    def test_query_count_stays_flat_as_population_grows(
        self, sim_with_zone, django_assert_num_queries
    ):
        """PREFLIGHT point 6: the real risk. Two population sizes (5 and
        50), zero agents actually starving in either case (all well
        above the subsistence threshold), so the ONLY cost is the FIXED
        per-tick machinery (zone_stats over 2 zones, the population
        aggregate, the historical-flight lookup, the one agent fetch) --
        never per-agent evaluation cost. The two calls must cost the
        SAME number of queries.
        """
        sim, zone = sim_with_zone
        _make_government(sim)
        world = zone.world
        # A second zone (unused directly by this test's own assertions,
        # but its mere existence is the point -- it makes zone_stats
        # construction cost 2 zones' worth of queries, not 1) -- see the
        # count breakdown below.
        _make_zone_at(world, 50, 50, "OtherZone")
        _make_subsistence_threshold_of_five(sim, zone)

        for i in range(5):
            _make_agent(sim, zone, f"WellFed{i}", wealth=100.0)

        # 17 = World(1) + Zone filter(1) + Government(1) + zone_stats over
        # 2 zones (`zone` HAS a ZoneEconomy from
        # _make_subsistence_threshold_of_five, so its subsistence-
        # threshold lookup costs 2 queries like wage/unemployment do;
        # `other_zone` has none, so its threshold lookup costs 1 via the
        # documented DoesNotExist early return -- (2+2+2) + (2+2+1) = 11)
        # + population aggregate(1) + historical-flight window(1) +
        # agent fetch(1) = 1+1+1+11+1+1+1 = 17.
        with django_assert_num_queries(17) as captured_small:
            process_emergency_flight(
                sim, tick=50, consecutive_ticks_under_subsistence_by_agent_id={}
            )
        small_population_queries = len(captured_small.captured_queries)

        for i in range(45):
            _make_agent(sim, zone, f"MoreWellFed{i}", wealth=100.0)

        with django_assert_num_queries(small_population_queries):
            process_emergency_flight(
                sim, tick=51, consecutive_ticks_under_subsistence_by_agent_id={}
            )

    @pytest.mark.django_db
    def test_empty_counters_mapping_is_a_well_defined_no_op(self, sim_with_zone):
        """PREFLIGHT point 1: an agent absent from the counters mapping
        is treated as zero consecutive ticks under subsistence and
        therefore cannot flee -- an empty mapping (the default) must not
        raise, and must produce no flight/trapped/mass-flight events.
        """
        sim, zone = sim_with_zone
        _make_government(sim)
        _make_subsistence_threshold_of_five(sim, zone)
        _make_agent(sim, zone, "Agent", wealth=4.0)  # starving, but absent from the mapping

        process_emergency_flight(sim, tick=50)  # counters mapping omitted entirely

        assert not DemographyEvent.objects.filter(simulation=sim).exists()

    @pytest.mark.django_db
    def test_memory_weight_ordering_flight_below_mourning_trapped_above(self):
        """PREFLIGHT point 3, self-check: the flight weight (0.85) sits
        BELOW the mourning weight (0.9, T027's MOURNING_MEMORY_WEIGHT in
        inheritance.py) while the trapped weight (0.95) sits ABOVE it --
        the design's own ordering, worth pinning explicitly since a
        reader will wonder why flight is "less" emotionally weighty than
        a death in the family while a trapped crisis is "more".
        """
        from epocha.apps.demography.inheritance import MOURNING_MEMORY_WEIGHT

        assert (
            EMERGENCY_FLIGHT_MEMORY_WEIGHT < MOURNING_MEMORY_WEIGHT < TRAPPED_CRISIS_MEMORY_WEIGHT
        )

    @pytest.mark.django_db
    def test_agent_relocated_via_family_coordination_is_not_double_evaluated(self, sim_with_zone):
        """An agent moved THIS tick as part of an earlier fleeing agent's
        household coordination must not be independently re-evaluated in
        their own turn using a stale (pre-move) zone -- pinned by
        constructing a minor child who, left in the original zone, would
        ALSO independently qualify for their own trapped-crisis emission
        (no positive-gain zone reachable from the ORIGINAL zone's
        perspective for a hypothetical solo evaluation), but having
        already moved with the fleeing parent must receive neither a
        flight event of their own nor a trapped-crisis event.
        """
        sim, zone = sim_with_zone
        _make_government(sim)
        world = zone.world
        other_zone = _make_zone_at(world, 50, 50, "OtherZone")
        currency = Currency.objects.create(
            simulation=sim, code="LVR", name="Livre", symbol="L", total_supply=50_000.0
        )
        worker = _make_agent(sim, other_zone, "Worker", role="")
        _make_wage(sim, currency, worker, tick=50, amount=250.0)
        _make_subsistence_threshold_of_five(sim, zone)

        parent = _make_agent(sim, zone, "Parent", wealth=4.0)
        minor_child = _make_agent(sim, zone, "MinorChild", parent_agent=parent, age=10, wealth=4.0)

        process_emergency_flight(
            sim,
            tick=50,
            consecutive_ticks_under_subsistence_by_agent_id={parent.id: 30, minor_child.id: 30},
        )

        minor_child.refresh_from_db()
        assert minor_child.zone_id == other_zone.id
        assert not DemographyEvent.objects.filter(
            simulation=sim,
            event_type=DemographyEvent.EventType.TRAPPED_CRISIS,
            primary_agent=minor_child,
        ).exists()
        assert not DemographyEvent.objects.filter(
            simulation=sim,
            event_type=DemographyEvent.EventType.MIGRATION,
            primary_agent=minor_child,
        ).exists()


# ---------------------------------------------------------------------------
# Flight-path determinism (Plan 3, T040, SC-003). The flight path draws NO
# randomness at all (no `get_seeded_rng` call anywhere in this module) --
# stated plainly per the task's own instruction: what this test guards is
# NOT seed reproducibility, it is ORDER INDEPENDENCE -- that no bare
# Python `set` iteration, `dict` ordering, or unordered queryset leaks
# into the observable outcome (the exact failure class the project's own
# determinism investigation names, roughly two dozen known instances in
# `agents` and `world`).
#
# GENUINE INDEPENDENCE: two ENTIRELY SEPARATE simulations (own user,
# world, zones, agents -- built by two independent calls to
# `_build_flight_scenario` below), never the same rows reused. Since
# auto-increment ids are a single global counter across every row created
# in the test database, "run B"'s ids are unconditionally higher than
# "run A"'s -- if anything in `process_emergency_flight` secretly depended
# on incidental id/hash/creation-order values rather than the explicitly
# documented `id`-ascending sort keys, the SAME the two runs' outcomes
# would diverge even though every INPUT VALUE (wealth, role, zone
# geometry, wage data) is identical between them. The comparison is by
# `Agent.name` (a value I control identically in both runs), never by id
# or object identity, since ids are NEVER expected to match across two
# independently built simulations.


def _build_flight_scenario(run_label):
    """Build a complete, independent flight scenario: its own user,
    simulation, world, three zones (an origin with both fleeing and
    staying agents, a destination with positive expected gain, and an
    isolated trapped zone with none reachable), Government, Currency, and
    the wage/subsistence fixtures `process_emergency_flight` needs.

    Every agent name is prefixed with `run_label` (e.g. "A", "B") so two
    calls with different labels produce structurally identical scenarios
    whose outcomes can be compared by name after stripping the prefix.

    Returns `(sim, tick, counters)` -- everything `process_emergency_
    flight` needs to run this scenario.
    """
    user = User.objects.create_user(
        email=f"flight-det-{run_label}@epocha.dev",
        username=f"flightdet{run_label}",
        password="pass1234",
    )
    sim = Simulation.objects.create(name=f"FlightDet{run_label}", seed=2026, owner=user)
    world = World.objects.create(simulation=sim, stability_index=0.7)
    origin_zone = Zone.objects.create(
        world=world,
        name=f"{run_label}Origin",
        zone_type="residential",
        boundary=Polygon.from_bbox((0, 0, 100, 100)),
        center=Point(50, 50),
    )
    destination_zone = Zone.objects.create(
        world=world,
        name=f"{run_label}Destination",
        zone_type="residential",
        boundary=Polygon.from_bbox((0, 0, 100, 100)),
        center=Point(50, 50),  # same center as origin: 0 distance cost
    )
    trapped_zone = Zone.objects.create(
        world=world,
        name=f"{run_label}Trapped",
        zone_type="residential",
        boundary=Polygon.from_bbox((99_900, 99_900, 100_100, 100_100)),
        center=Point(100_000, 100_000),  # very far: distance cost overwhelms any gain
    )
    Government.objects.create(simulation=sim, stability=0.5)
    currency = Currency.objects.create(
        simulation=sim, code="LVR", name="Livre", symbol="L", total_supply=50_000.0
    )

    worker = _make_agent(sim, destination_zone, f"{run_label}Worker", role="")
    _make_wage(sim, currency, worker, tick=50, amount=250.0)

    _make_subsistence_threshold_of_five(sim, origin_zone)
    # A second GoodCategory/ZoneEconomy pair for trapped_zone -- reusing
    # the origin_zone helper would try to create a second GoodCategory
    # row with the same (simulation, code) and collide with its own
    # unique_together constraint, so this zone's threshold is built
    # directly instead.
    GoodCategory.objects.create(
        simulation=sim,
        code=f"{run_label}FOOD2",
        name="Food",
        is_essential=True,
        base_price=10.0,
        price_elasticity=0.3,
    )
    ZoneEconomy.objects.create(zone=trapped_zone, market_prices={f"{run_label}FOOD2": 5.0})

    counters = {}

    fleeing_agents = [
        _make_agent(sim, origin_zone, f"{run_label}Fleeing{i}", wealth=4.0) for i in range(4)
    ]
    for agent in fleeing_agents:
        counters[agent.id] = 30
    for i in range(6):
        _make_agent(sim, origin_zone, f"{run_label}Stays{i}", wealth=100.0)

    trapped_agent = _make_agent(sim, trapped_zone, f"{run_label}TrappedAgent", wealth=4.0)
    counters[trapped_agent.id] = 30

    return sim, 50, counters


def _run_outcome_by_name(sim):
    """Extract the flight-path outcome from `sim`'s `DemographyEvent`
    rows, keyed by agent NAME (with the run-label prefix stripped) so two
    independently built simulations' outcomes compare by value.
    """
    fled_names = set()
    trapped_names = set()
    event_sequence = []  # [(event_type, name_without_prefix), ...], id-ascending
    for event in DemographyEvent.objects.filter(simulation=sim).order_by("id"):
        name = event.primary_agent.name if event.primary_agent else None
        stripped = name[1:] if name else None  # strip the single-char run_label prefix
        event_sequence.append((event.event_type, stripped))
        if event.event_type == DemographyEvent.EventType.MIGRATION:
            if event.payload.get("reason") == "emergency_flight":
                fled_names.add(stripped)
        elif event.event_type == DemographyEvent.EventType.TRAPPED_CRISIS:
            trapped_names.add(stripped)

    memory_count = Memory.objects.filter(agent__simulation=sim).count()

    return {
        "fled_names": fled_names,
        "trapped_names": trapped_names,
        "event_sequence": event_sequence,
        "memory_count": memory_count,
    }


class TestFlightPathDeterminismSC003:
    """SC-003: two independently constructed flight-path runs (own
    simulation, own agents, only their VALUES matching) produce identical
    outcomes -- the order-independence guarantee this module's flight
    path must hold, since it draws no randomness of its own.
    """

    @pytest.mark.django_db
    def test_two_independent_runs_produce_identical_outcomes(self):
        sim_a, tick_a, counters_a = _build_flight_scenario("A")
        sim_b, tick_b, counters_b = _build_flight_scenario("B")

        assert sim_a.id != sim_b.id  # self-check: genuinely different simulations

        process_emergency_flight(
            sim_a, tick=tick_a, consecutive_ticks_under_subsistence_by_agent_id=counters_a
        )
        process_emergency_flight(
            sim_b, tick=tick_b, consecutive_ticks_under_subsistence_by_agent_id=counters_b
        )

        outcome_a = _run_outcome_by_name(sim_a)
        outcome_b = _run_outcome_by_name(sim_b)

        assert (
            outcome_a["fled_names"]
            == outcome_b["fled_names"]
            == {
                "Fleeing0",
                "Fleeing1",
                "Fleeing2",
                "Fleeing3",
            }
        )
        assert outcome_a["trapped_names"] == outcome_b["trapped_names"] == {"TrappedAgent"}
        # Event TYPE/NAME sequence, in id-ascending order, must match
        # exactly between the two independently built runs -- this is
        # the order-independence proof itself, not just a same-set check.
        assert outcome_a["event_sequence"] == outcome_b["event_sequence"]
        assert outcome_a["memory_count"] == outcome_b["memory_count"] > 0

        mass_flight_a = DemographyEvent.objects.get(
            simulation=sim_a, event_type=DemographyEvent.EventType.MASS_FLIGHT
        )
        mass_flight_b = DemographyEvent.objects.get(
            simulation=sim_b, event_type=DemographyEvent.EventType.MASS_FLIGHT
        )
        assert mass_flight_a.payload["trigger_ticks"] == mass_flight_b.payload["trigger_ticks"]
        assert len(mass_flight_a.payload["agents"]) == len(mass_flight_b.payload["agents"])

"""Measurement of the per-tick write cost of the economy step.

Purpose: spec ``specs/20261112-233606-economy-batched-writes/spec.md``,
success criteria SC-002 (ratio of the economy step at 2,000 and 200
founders), SC-003 (economy step at 2,000 founders) and SC-004 (values
written bit-identical before and after batching), and plan PD-01 (choice
of the batch size) and PD-03 (this script).

This is a measurement, not a test of the suite: ``pyproject.toml`` collects
only ``test_*.py`` files, so the suite never collects this script. Run one
function per invocation:

    pytest scripts/measure_economy_write_cost.py -s -p no:cacheprovider \
        -k test_batch_size_candidates

Environment (every value is printed with the result):

- ``ECONOMY_COST_FOUNDERS`` number of founders (default 2000);
- ``ECONOMY_COST_TICKS`` measured ticks after the untimed tick 1 (default 5);
- ``ECONOMY_COST_SEED`` simulation seed (default 20261112).

Every function runs with ``transaction=True`` so every write is committed
and a timing does not carry the row versions of the previous one.
"""

from __future__ import annotations

import hashlib
import math
import os
import random
import statistics
import time
from collections import Counter, deque

import pytest
from django.contrib.gis.geos import Point, Polygon
from django.db import connection
from django.test.utils import CaptureQueriesContext

from epocha.apps.agents.models import Agent, Memory
from epocha.apps.economy.engine import process_economy_tick_new
from epocha.apps.economy.initialization import initialize_economy
from epocha.apps.economy.models import AgentExpectation
from epocha.apps.simulation.models import Simulation
from epocha.apps.users.models import User
from epocha.apps.world.models import Government, World, Zone
from epocha.apps.world.stratification import update_social_classes
from epocha.common.testing import case_update_rows

FOUNDERS = int(os.environ.get("ECONOMY_COST_FOUNDERS", "2000"))
TICKS = int(os.environ.get("ECONOMY_COST_TICKS", "5"))
SEED = int(os.environ.get("ECONOMY_COST_SEED", "20261112"))

# Plan PD-01: the batch sizes compared. A geometric grid from the size at
# which the per-statement overhead dominates to the size at which the
# quadratic CASE scan dominates; extended past an edge when the minimum
# lands on it.
CANDIDATE_BATCH_SIZES = (5, 10, 15, 25, 50, 100, 200, 500)

# Plan PD-01: repetitions per candidate; the median is reported.
REPETITIONS = 3

# Plan PD-01: a machine whose same candidate moves by more than a fifth
# between two timings of one session cannot rank candidates 10% apart.
# Tunable heuristic.
DRIFT_TOLERANCE = 0.20

# Plan PD-01: one-row updates timed to estimate the per-statement cost b.
ONE_ROW_SAMPLES = 20

# The five fields written by ``update_agent_expectations``
# (``epocha/apps/economy/expectations.py``).
FIVE_FIELDS = [
    "expected_price",
    "trend_direction",
    "confidence",
    "lambda_rate",
    "updated_at_tick",
]

# Roles that the pre_industrial template maps to a good
# (``template_loader._ROLE_PRODUCTION``) plus the default role.
FOUNDER_ROLES = ("farmer", "blacksmith", "craftsman", "merchant", "priest")

BIG_FIVE_TRAITS = ("openness", "conscientiousness", "extraversion", "agreeableness", "neuroticism")


def _create_zone(world: World, name: str, zone_type: str, west: float) -> Zone:
    """Create one square zone whose west edge is ``west`` degrees."""
    return Zone.objects.create(
        world=world,
        name=name,
        zone_type=zone_type,
        boundary=Polygon.from_bbox((west, 0, west + 50, 50)),
        center=Point(west + 25, 25),
    )


def _founder(simulation, zone, index: int, rng: random.Random) -> Agent:
    """Return an unsaved founder; role and Big Five come from ``rng``."""
    return Agent(
        simulation=simulation,
        name=f"Founder {index}",
        role=rng.choice(FOUNDER_ROLES),
        personality={trait: rng.random() for trait in BIG_FIVE_TRAITS},
        location=zone.center,
        zone=zone,
        health=1.0,
        wealth=50.0,
    )


def founded_economy_simulation(founders: int, seed: int) -> Simulation:
    """Build a simulation with ``founders`` agents and an initialised economy.

    No LLM call: the agents are created through one ``bulk_create`` with the
    fields of ``economy/tests/test_engine.py``, then ``initialize_economy``
    gives them inventories and wealth.
    """
    user = User.objects.create_user(
        email="cost@epocha.dev", username="costuser", password="pass1234"
    )
    simulation = Simulation.objects.create(name="EconomyCost", seed=seed, owner=user)
    world = World.objects.create(
        simulation=simulation, distance_scale=133.0, tick_duration_hours=730
    )
    Government.objects.create(simulation=simulation, government_type="monarchy")
    zones = [
        _create_zone(world, "Rural", "rural", 0),
        _create_zone(world, "Urban", "urban", 60),
    ]
    rng = random.Random(seed)
    Agent.objects.bulk_create(
        [_founder(simulation, zones[i % len(zones)], i, rng) for i in range(founders)]
    )
    initialize_economy(simulation, template_name="pre_industrial")
    return simulation


def _time_bulk_update(rows: list[AgentExpectation], batch_size: int) -> float:
    """Return the seconds taken by one full ``bulk_update`` at ``batch_size``."""
    started = time.perf_counter()
    AgentExpectation.objects.bulk_update(rows, FIVE_FIELDS, batch_size=batch_size)
    return time.perf_counter() - started


def _time_candidates(rows: list[AgentExpectation]) -> dict[int, list[float]]:
    """Time every candidate ``REPETITIONS`` times, candidates interleaved by round."""
    timings: dict[int, list[float]] = {size: [] for size in CANDIDATE_BATCH_SIZES}
    for _ in range(REPETITIONS):
        for size in CANDIDATE_BATCH_SIZES:
            timings[size].append(_time_bulk_update(rows, size))
    return timings


def _time_one_row_updates(rows: list[AgentExpectation]) -> float:
    """Return the median seconds of a one-row ``bulk_update`` (the cost b)."""
    return statistics.median(_time_bulk_update(rows[i : i + 1], 1) for i in range(ONE_ROW_SAMPLES))


def _solve_least_squares(points: list[tuple[float, float]]) -> tuple[float, float, float]:
    """Fit ``t = a*x**2 + c*x + b`` to ``points`` by the normal equations.

    Report only: the fit never chooses the batch size. Gaussian elimination
    with partial pivoting on the 3x3 system.
    """
    sums = [sum(x**k for x, _ in points) for k in range(5)]
    rhs = [sum(y * x**k for x, y in points) for k in range(3)]
    matrix = [[sums[row + col] for col in range(2, -1, -1)] + [rhs[row]] for row in (2, 1, 0)]
    for col in range(3):
        pivot = max(range(col, 3), key=lambda r: abs(matrix[r][col]))
        matrix[col], matrix[pivot] = matrix[pivot], matrix[col]
        for row in range(col + 1, 3):
            factor = matrix[row][col] / matrix[col][col]
            matrix[row] = [m - factor * p for m, p in zip(matrix[row], matrix[col])]
    solution = [0.0] * 3
    for row in (2, 1, 0):
        known = sum(matrix[row][col] * solution[col] for col in range(row + 1, 3))
        solution[row] = (matrix[row][3] - known) / matrix[row][row]
    return solution[0], solution[1], solution[2]


def _print_candidate_table(row_count, medians, drift_ratio, one_row_seconds) -> None:
    """Print R, b, the per-candidate table, the drift ratio and the fit."""
    print(f"FOUNDERS={FOUNDERS} SEED={SEED} R={row_count} REPETITIONS={REPETITIONS}")
    print(f"b (median one-row update) = {one_row_seconds:.6f} s")
    points = []
    for size in CANDIDATE_BATCH_SIZES:
        statements = math.ceil(row_count / size)
        per_statement = medians[size] / statements
        points.append((float(size), per_statement))
        print(
            f"B={size:>4} statements={statements:>5} "
            f"median_total={medians[size]:.3f} s per_statement={per_statement:.6f} s"
        )
    verdict = "within" if abs(drift_ratio - 1) <= DRIFT_TOLERANCE else "OUTSIDE"
    print(
        f"drift ratio (first candidate, second timing / median of first timings) = "
        f"{drift_ratio:.3f}, {verdict} the tolerance of {DRIFT_TOLERANCE:.2f}"
    )
    a, c, b = _solve_least_squares(points)
    print(f"fit per statement t(B) = a*B^2 + c*B + b: a={a:.3e} c={c:.3e} b={b:.3e} (report only)")


@pytest.mark.django_db(transaction=True)
def test_batch_size_candidates():
    """Plan PD-01: time the full expectation write per candidate batch size."""
    simulation = founded_economy_simulation(FOUNDERS, SEED)
    process_economy_tick_new(simulation, 1)
    rows = list(AgentExpectation.objects.filter(agent__simulation=simulation).order_by("id"))
    timings = _time_candidates(rows)
    medians = {size: statistics.median(values) for size, values in timings.items()}
    first = CANDIDATE_BATCH_SIZES[0]
    drift_ratio = _time_bulk_update(rows, first) / medians[first]
    _print_candidate_table(len(rows), medians, drift_ratio, _time_one_row_updates(rows))


# -- test_economy_step_cost: spec SC-002 to SC-004 (plan PD-03) --

# Fields written per row by the three batched sites.
EXPECTATION_FIELD_COUNT = len(FIVE_FIELDS)
AGENT_STEP_FIELD_COUNT = 2  # wealth, mood
SOCIAL_CLASS_FIELD_COUNT = 1


def _fingerprint(lines) -> str:
    """Return the SHA-256 hex digest of ``lines`` joined by newlines."""
    return hashlib.sha256("\n".join(lines).encode()).hexdigest()


def _update_statement_count(captured_queries) -> int:
    """Return how many captured statements are ``UPDATE`` statements."""
    return sum(1 for query in captured_queries if query["sql"].startswith("UPDATE"))


def _rows_per_statement(captured_queries, model, field_count) -> dict[int, int]:
    """Return ``{rows in a statement: number of such statements}`` for ``model``."""
    return dict(sorted(Counter(case_update_rows(captured_queries, model, field_count)).items()))


def _unbounded_query_log() -> None:
    """Replace the connection's query log by an empty unbounded one.

    Django keeps only the last 9000 statements (``queries_limit``) and
    ``CaptureQueriesContext`` slices that log by position, so past the
    limit it returns fewer statements than were run (or none). One economy
    step at 2,000 founders runs about 12,000 ``UPDATE`` statements alone.
    """
    connection.queries_log = deque()


def _timed_tick(simulation, tick: int):
    """Run one economy step; return its seconds and its captured queries."""
    _unbounded_query_log()
    with CaptureQueriesContext(connection) as ctx:
        started = time.perf_counter()
        process_economy_tick_new(simulation, tick)
        elapsed = time.perf_counter() - started
    return elapsed, ctx.captured_queries


def _print_tick_shape(tick, elapsed, queries) -> None:
    """Print the time, the UPDATE count and the batched-statement shape of one tick."""
    expectations = case_update_rows(queries, AgentExpectation, EXPECTATION_FIELD_COUNT)
    wealth = case_update_rows(queries, Agent, AGENT_STEP_FIELD_COUNT)
    print(
        f"tick={tick} seconds={elapsed:.3f} updates={_update_statement_count(queries)} "
        f"expectation_statements={len(expectations)} expectation_max_rows="
        f"{max(expectations, default=0)} wealth_statements={len(wealth)} "
        f"wealth_max_rows={max(wealth, default=0)}"
    )


def _step_fingerprint(simulation) -> str:
    """Fingerprint (a) of spec FR-006: the values the economy step wrote.

    Agents in ``id`` order by ordinal (wealth, mood), then expectations in
    (agent ordinal, good code) order (the five fields); floats as
    ``float.hex`` so the digest is bit-exact.
    """
    agents = list(Agent.objects.filter(simulation=simulation).order_by("id"))
    ordinal = {agent.id: index for index, agent in enumerate(agents)}
    lines = [f"A|{i}|{a.wealth.hex()}|{a.mood.hex()}" for i, a in enumerate(agents)]
    expectations = AgentExpectation.objects.filter(agent__simulation=simulation).order_by(
        "agent_id", "good_code"
    )
    lines += [
        f"E|{ordinal[e.agent_id]}|{e.good_code}|{e.expected_price.hex()}|{e.trend_direction}|"
        f"{e.confidence.hex()}|{e.lambda_rate.hex()}|{e.updated_at_tick}"
        for e in expectations
    ]
    return _fingerprint(lines)


def _living_agents(simulation) -> list[Agent]:
    """Return the living agents in ``id`` order."""
    return list(Agent.objects.filter(simulation=simulation, is_alive=True).order_by("id"))


def _class_fingerprints(simulation) -> tuple[str, str, int]:
    """Return fingerprint (b), the per-agent-id class hash and the tied-wealth count.

    (b) is tie-invariant (spec FR-006): the sorted multiset of
    (``wealth.hex()``, ``social_class``) over living agents plus the mobility
    memories sorted by (agent ``wealth.hex()``, content, emotional weight,
    tick). The per-agent-id hash and the count of agents sharing their
    wealth are information only (spec FR-004 limit).
    """
    agents = _living_agents(simulation)
    wealth_of = {agent.id: agent.wealth.hex() for agent in agents}
    multiset = sorted(f"{a.wealth.hex()}|{a.social_class}" for a in agents)
    memories = sorted(
        (wealth_of[m.agent_id], m.content, m.emotional_weight.hex(), m.tick_created)
        for m in Memory.objects.filter(agent__in=agents)
    )
    by_id = _fingerprint(f"{i}|{a.social_class}" for i, a in enumerate(agents))
    tied = sum(count for count in Counter(wealth_of.values()).values() if count > 1)
    return (
        _fingerprint(multiset + [repr(memory) for memory in memories]),
        by_id,
        tied,
    )


def _print_class_step(simulation) -> None:
    """Run ``update_social_classes`` once, untimed, and print its shape and fingerprints.

    Premise of the tie invariance of (b) (spec FR-006): every founder still
    has the model default class ``working``; the script fails otherwise.
    """
    classes = {agent.social_class for agent in _living_agents(simulation)}
    assert classes == {"working"}, f"founders' classes before the call: {classes}"
    _unbounded_query_log()
    with CaptureQueriesContext(connection) as ctx:
        update_social_classes(simulation)
    rows = _rows_per_statement(ctx.captured_queries, Agent, SOCIAL_CLASS_FIELD_COUNT)
    fingerprint_b, by_id, tied = _class_fingerprints(simulation)
    print(f"social_class rows per statement {rows}")
    print(f"fingerprint_b={fingerprint_b}")
    print(f"info class_hash_by_agent_id={by_id} tied_wealth_agents={tied}")


@pytest.mark.django_db(transaction=True)
def test_economy_step_cost():
    """Plan PD-03: time the economy step and print the fingerprints of SC-004."""
    simulation = founded_economy_simulation(FOUNDERS, SEED)
    process_economy_tick_new(simulation, 1)
    seconds = []
    shapes = []
    for tick in range(2, 2 + TICKS):
        elapsed, queries = _timed_tick(simulation, tick)
        _print_tick_shape(tick, elapsed, queries)
        seconds.append(elapsed)
        shapes.append(queries)
    print(f"FOUNDERS={FOUNDERS} TICKS={TICKS} SEED={SEED} simulation.id={simulation.id}")
    print(f"median_seconds={statistics.median(seconds):.3f}")
    print(
        f"expectation rows per statement "
        f"{_rows_per_statement(shapes[-1], AgentExpectation, EXPECTATION_FIELD_COUNT)}"
    )
    print(
        f"wealth_mood rows per statement "
        f"{_rows_per_statement(shapes[-1], Agent, AGENT_STEP_FIELD_COUNT)}"
    )
    print(f"fingerprint_a={_step_fingerprint(simulation)}")
    _print_class_step(simulation)

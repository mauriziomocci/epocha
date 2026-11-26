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

import math
import os
import random
import statistics
import time

import pytest
from django.contrib.gis.geos import Point, Polygon

from epocha.apps.agents.models import Agent
from epocha.apps.economy.engine import process_economy_tick_new
from epocha.apps.economy.initialization import initialize_economy
from epocha.apps.economy.models import AgentExpectation
from epocha.apps.simulation.models import Simulation
from epocha.apps.users.models import User
from epocha.apps.world.models import Government, World, Zone

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

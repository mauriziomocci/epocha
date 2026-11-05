"""Measure the cost of the rule-based marriage market (spec SC-005).

Run from the repository root, outside the test suite:

    PYTHONPATH=. python scripts/measure_marriage_market_cost.py [--seed N]

Declared complexity. The market of one tick matches S seekers against M
candidates with `couple.stable_matching` (Gale and Shapley 1962), which
sorts the M candidates once per seeker and evaluates the score 2 * S * M
times: O(S * M * log M). With the radius `world` seekers and candidates both
grow as N, so the declared cost is O(N^2 * log N), whose local exponent
between 10^3 and 10^5 is 2.11. The script fails (exit 1) when a measured
exponent exceeds 2.3, that is when the code grows faster than the
complexity the spec declares.

Two measurements, both on pure functions and on `SyntheticAgent` stand-ins
(a `types.SimpleNamespace` is unhashable and `stable_matching` keys its
dictionaries by agent), so no database is needed:

1. Step 2 of a weekly tick at N = 10^3, 10^4 and 10^5: `draw_seekers` on the
   Christian first-marriage schedule, then `match_markets` with the radius
   `world` and `homogamy_score(..., sentiments={}, ages=...)`. The time is
   the median of five repetitions; the exponent is the least-squares slope
   of log time on log N.
2. The founding match at N = 10^3 and 10^4 (`initialization.form_initial_couples`
   declares each eligible woman married with probability F*(x), then matches
   all declared women against all eligible men): time, and the peak memory
   of `tracemalloc` in a separate run, because tracemalloc slows the code
   and would distort the time. The exponents are two-point slopes, and the
   value at 10^5 is printed labelled "extrapolation": at 10^5 in one market
   the match would need about 10^9 score evaluations and a preference
   dictionary of the same order (tens of GB), so it is not run.

The population is synthetic and declared: half women, ages drawn from the
template `age_pyramid` (bracket chosen by its share, age uniform inside the
bracket), `social_class` uniform over the values the `Agent.social_class`
help text lists, `education_level` uniform on [0, 1], all in no zone.
"""

from __future__ import annotations

import argparse
import math
import random
import statistics
import sys
import time
import tracemalloc
from dataclasses import dataclass

from epocha.apps.demography.couple import draw_seekers, homogamy_score, match_markets
from epocha.apps.demography.nuptiality import first_marriage_schedule
from epocha.apps.demography.orchestrator import HOURS_PER_YEAR
from epocha.apps.demography.template_loader import load_template

TEMPLATE_NAME = "pre_industrial_christian"
DEFAULT_SEED = 20261029
STEP2_SIZES = (1_000, 10_000, 100_000)
FOUNDING_SIZES = (1_000, 10_000)
EXTRAPOLATION_SIZE = 100_000
REPETITIONS = 5
WEEK_HOURS = 168.0
# Declared exponent N^2 * log N has a local slope of 2.11 between 10^3 and
# 10^5; 2.3 leaves 0.19 for noise and cache effects (spec SC-005).
EXPONENT_LIMIT = 2.3
SOCIAL_CLASSES = ("elite", "wealthy", "middle", "working", "poor")


@dataclass(eq=False)
class SyntheticAgent:
    """The fields the market reads from an agent, hashable by identity.

    `stable_matching` keys its preference dictionaries by agent, so the
    stand-in must be hashable; `eq=False` keeps the identity hash.
    """

    id: int
    gender: str
    age: float
    social_class: str
    education_level: float
    zone_id: None = None


def build_population(n: int, rng: random.Random, template: dict) -> list[SyntheticAgent]:
    """Return n synthetic agents, the first half women, the second half men.

    Ages come from the template `age_pyramid`, a list of `[low, high, share]`
    brackets: the bracket is drawn by its share and the age is uniform inside
    it. `social_class` is uniform over `SOCIAL_CLASSES` and `education_level`
    uniform on [0, 1], so the score has the same spread of its three terms
    that a generated world has; every agent is in no zone.
    """
    brackets = template["age_pyramid"]
    shares = [bracket[2] for bracket in brackets]
    agents = []
    for index in range(n):
        low, high, _ = rng.choices(brackets, weights=shares)[0]
        agents.append(
            SyntheticAgent(
                id=index + 1,
                gender="female" if index < n // 2 else "male",
                age=rng.uniform(low, high),
                social_class=rng.choice(SOCIAL_CLASSES),
                education_level=rng.random(),
            )
        )
    return agents


def eligible_sides(agents: list, couple_cfg: dict) -> tuple[list, list, dict]:
    """Split the agents of marriage age into women and men, with the ages map."""
    women = [
        a for a in agents if a.gender == "female" and a.age >= couple_cfg["min_marriage_age_female"]
    ]
    men = [a for a in agents if a.gender == "male" and a.age >= couple_cfg["min_marriage_age_male"]]
    return women, men, {a.id: a.age for a in women + men}


def scorer(couple_cfg: dict, ages: dict):
    """The production score with no relationship history (`sentiments={}`)."""

    def score(woman, man) -> float:
        return homogamy_score(woman, man, couple_cfg["homogamy_weights"], sentiments={}, ages=ages)

    return score


def timed(function) -> tuple[float, object]:
    """Return the wall time of one call and its result."""
    start = time.perf_counter()
    result = function()
    return time.perf_counter() - start, result


def log_log_slope(sizes: list[int], seconds: list[float]) -> float:
    """Least-squares slope of log time on log N."""
    return statistics.linear_regression(
        [math.log(n) for n in sizes], [math.log(t) for t in seconds]
    ).slope


def two_point_exponent(sizes: tuple[int, int], values: tuple[float, float]) -> float:
    """Slope between two points of a log-log curve."""
    return math.log(values[1] / values[0]) / math.log(sizes[1] / sizes[0])


def measure_step2(n: int, seed: int, template: dict) -> tuple[float, float, int, float]:
    """Median seconds of one weekly step 2 at N agents, with the median S, M and pairs.

    S, the seekers of a tick, is a random count with a mean near 0.5 at
    N = 10^3, so the median time at the smallest N is a few microseconds and
    the least-squares exponent is noisy there; the medians of S and of the
    pairs are printed so the reader sees what the time was measured on.
    """
    couple_cfg = template["couple"]
    schedule = first_marriage_schedule(couple_cfg)
    years = WEEK_HOURS / HOURS_PER_YEAR
    women, men, ages = eligible_sides(
        build_population(n, random.Random(seed), template), couple_cfg
    )
    score = scorer(couple_cfg, ages)
    runs = []
    for repetition in range(REPETITIONS):
        rng = random.Random(seed + 1 + repetition)

        def step() -> tuple[int, int]:
            seekers = draw_seekers(
                women, lambda w: schedule.tick_probability(ages[w.id], years), rng
            )
            return len(seekers), len(match_markets(seekers, men, "world", score))

        seconds, (seekers, pairs) = timed(step)
        runs.append((seconds, seekers, pairs))
    median = statistics.median(seconds for seconds, _, _ in runs)
    return (
        median,
        statistics.median(r[1] for r in runs),
        len(men),
        statistics.median(r[2] for r in runs),
    )


def founding_match(n: int, seed: int, template: dict):
    """Return a callable running the founding declaration and match at N agents."""
    couple_cfg = template["couple"]
    schedule = first_marriage_schedule(couple_cfg)
    women, men, ages = eligible_sides(
        build_population(n, random.Random(seed), template), couple_cfg
    )
    score = scorer(couple_cfg, ages)

    def run() -> tuple[int, int, int]:
        rng = random.Random(seed + 1)
        declared = draw_seekers(women, lambda w: schedule.conditional_cdf(ages[w.id]), rng)
        return len(declared), len(men), len(match_markets(declared, men, "world", score))

    return run


def peak_memory_bytes(function) -> int:
    """Peak tracemalloc bytes allocated while `function` runs, above its start."""
    tracemalloc.start()
    baseline, _ = tracemalloc.get_traced_memory()
    function()
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return peak - baseline


def report_step2(seed: int, template: dict) -> float:
    """Print the step-2 table and return its exponent."""
    print(f"Step 2 of a weekly tick, radius world (median of {REPETITIONS} repetitions)")
    print(
        f"{'N':>9} {'seekers':>9} {'men':>9} {'pairs':>9} {'seconds':>12}"
    )  # seekers, pairs: medians
    seconds = []
    for n in STEP2_SIZES:
        median, seekers, men, pairs = measure_step2(n, seed, template)
        seconds.append(median)
        print(f"{n:>9d} {seekers:>9.1f} {men:>9d} {pairs:>9.1f} {median:>12.4f}")
    exponent = log_log_slope(list(STEP2_SIZES), seconds)
    print(f"step 2 exponent (least squares): {exponent:.3f} (limit {EXPONENT_LIMIT})")
    return exponent


def report_founding(seed: int, template: dict) -> list[float]:
    """Print the founding table and return its time and memory exponents."""
    print("\nFounding match, radius world (time without tracemalloc, memory in a second run)")
    print(f"{'N':>9} {'declared':>9} {'men':>9} {'pairs':>9} {'seconds':>12} {'peak MiB':>14}")
    seconds, peaks = [], []
    for n in FOUNDING_SIZES:
        run = founding_match(n, seed, template)
        elapsed, (declared, men, pairs) = timed(run)
        peak = peak_memory_bytes(run)
        seconds.append(elapsed)
        peaks.append(peak)
        print(
            f"{n:>9d} {declared:>9d} {men:>9d} {pairs:>9d} {elapsed:>12.4f} {peak / 2**20:>14.1f}"
        )
    time_exponent = two_point_exponent(FOUNDING_SIZES, tuple(seconds))
    memory_exponent = two_point_exponent(FOUNDING_SIZES, tuple(peaks))
    ratio = EXTRAPOLATION_SIZE / FOUNDING_SIZES[1]
    print(
        f"founding time exponent (two points): {time_exponent:.3f}, "
        f"memory exponent: {memory_exponent:.3f} (limit {EXPONENT_LIMIT})"
    )
    print(
        f"extrapolation to N = {EXTRAPOLATION_SIZE}: "
        f"{seconds[1] * ratio**time_exponent:.0f} s, "
        f"{peaks[1] * ratio**memory_exponent / 2**30:.1f} GiB (not measured)"
    )
    return [time_exponent, memory_exponent]


def main(argv: list[str] | None = None) -> int:
    """Run both measurements; return 1 when any exponent exceeds the limit."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    args = parser.parse_args(argv)
    template = load_template(TEMPLATE_NAME)
    exponents = [report_step2(args.seed, template), *report_founding(args.seed, template)]
    failed = [e for e in exponents if e > EXPONENT_LIMIT]
    verdict = f"FAIL, exponent above {EXPONENT_LIMIT}" if failed else "pass"
    print(f"\nRESULT: {verdict}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

"""Measure realized nuptiality and fertility of a couple era (couples SC-007, marital SC-005).

Run from the repository root, outside the test suite:

    PYTHONPATH=. python scripts/measure_nuptiality_fertility.py [--replicates 20] [--seed-base 1]

What it answers. In an era that requires a couple for a birth the base
schedule applies to women in a couple only, so the fertility a cohort realizes
is the integral of that schedule weighted by the share of women in a couple at
each age. The base schedule is the one the template's `fertility` block
selects through the single dispatch point `fertility.annual_base_rate` (N4):
the marital schedule r(a) = M * n(a) of Coale and Trussell (1974) in the three
eras that require a couple (`pre_industrial_christian` among them), equation
(4.2) of Hadwiger (1940) elsewhere. The script never reads a block by name.
This script follows a cohort of 20,000 women from 12 to 50 years at monthly
ticks and reports that fertility, in two configurations:

- A, no mortality (hence no widowhood and no remarriage). Judged from 5
  replicates (`MIN_REPLICATES_JUDGED`: with fewer, the 3-standard-error limit
  on a Student t statistic fails a correct model more than 5% of the time);
  below it the verdict is "not judged". Failure when the
  mean TFR of the replicates is further than 3 standard errors (sd /
  sqrt(replicates)) from the reference, the deterministic propagation of the
  first-marriage hazard at the same monthly ticks, computed here with the
  same `annual_base_rate` (`propagated_reference_tfr`, 4.306 for the
  Christian era, SC-002; never a hand-written number), or when a tick has
  more than 500 seekers (the always-available-men assumption would not hold).
- B, with mortality, widowhood, mourning and the remarriage rate. The TFR,
  with M(a) the share in a couple among the women alive at that age (SC-007),
  has no threshold (widowhood and the remarriage rate are heuristics); the net
  reproduction rate has two, failure when the upper bound of its 95% Student
  t interval is below 1 (inherited from the couples SC-007) or when its lower
  bound exceeds the analytic NRR without widowhood at the same monthly ticks
  in the engine's order (`analytic_nrr`, 1.92686 for the Christian era;
  marital fertility SC-005), because widowhood and mourning can only remove
  years in a couple.

Harness assumptions, every one declared:

- Step order of the engine (`orchestrator.DEMOGRAPHY_STEPS`): within a tick
  the market (couple formation, step 2) runs first, then mortality (step 3),
  then fertility (step 7), so a woman who marries at a tick counts for that
  tick's births and a woman or a husband who dies at it does not
  (`replicate_tick`, held by `test_measurement_harness_rules.py`). The base
  rate is evaluated at the age at the start of the tick
  (`_effective_age_in_years`). The reference of configuration A follows the
  same order and age: 4.306 against 4.283 with the married share one tick
  late and 4.318 with the marriage hazard at mid-tick (SC-002, decisions
  D-05-E-12 and D-12-E-3); `test_marital_fertility.py` ties it to the SC-002
  propagation of the tests.
- Men are female-dominant and always available: each tick the candidates
  are 500 never-married men redrawn from the template `age_pyramid` above
  `min_marriage_age_male` (a bracket partly below it is cut at it), not a
  simulated male population. Husbands are tracked only to die.
- Every woman and every candidate has `social_class = "working"` and
  `education_level = 0.3`, so only the age term of the homogamy score varies.
- One Heligman-Pollard schedule is used for both sexes, as `mortality.py` has
  no sex term. The husband dies at his own age.
- Becker modulation and the Malthusian ceiling are excluded by construction:
  the measure concerns the interaction of nuptiality and the base schedule
  (the realized Becker level is measured in a run by SC-006).
- Maternal mortality (0.008 per birth in the template) is not modelled, in
  both the harness and the analytic values.
- The seek probability is the production function `couple.seek_probability_for`.
  Eligibility (minimum age and mourning) is the reduced copy `is_ineligible`,
  checked against `couple.marriage_ineligibility` on a grid by
  `test_measurement_harness_rules.py`.
- Mourning is `couple.mourning_ticks` after a husband's death; a woman who
  has been in a couple draws on the remarriage rate `r_f`
  (`remarriage_annual_rate_female`), a never-married one on the first-marriage
  schedule (plan PD-07). Separation does not exist in the harness.
- Mortality uses the function the tick loop uses after D-29-20,
  `orchestrator.mortality_probability_for`, cached per whole month of age. It
  charges the engine's exposure age, the age at the PREVIOUS tick
  (`orchestrator.exposure_age`), while the market and fertility read the age
  at the current tick: a mother of fertility age a has survived to l(a), not
  to l(a + 1/12) (D-12-E-5, held by `test_measurement_harness_rules.py`).

Cost: about 2 score evaluations per seeker and candidate, roughly 2 * 10^7 per
replicate, acceptable for a script and not for the suite.
"""

from __future__ import annotations

import argparse
import math
import random
import statistics
import sys
import time
from types import SimpleNamespace

from scipy import stats
from scipy.integrate import quad

from epocha.apps.demography.couple import (
    MarketPopulation,
    MarriageHistory,
    draw_seekers,
    homogamy_score,
    match_markets,
    mourning_ticks,
    seek_probability_for,
)
from epocha.apps.demography.fertility import annual_base_rate
from epocha.apps.demography.mortality import annual_mortality_probability
from epocha.apps.demography.nuptiality import first_marriage_schedule
from epocha.apps.demography.orchestrator import HOURS_PER_YEAR, mortality_probability_for
from epocha.apps.demography.template_loader import load_template
from scripts.measure_marriage_market_cost import SyntheticAgent

TEMPLATE_NAME = "pre_industrial_christian"
COHORT_SIZE = 20_000
START_AGE = 12
END_AGE = 50
TICK_HOURS = 730.0
TICKS_PER_YEAR = 12
TICKS = (END_AGE - START_AGE) * TICKS_PER_YEAR
CANDIDATE_POOL = 500
MAX_SEEKERS = CANDIDATE_POOL
SEEKER_SD_LIMIT = 3.0
# Configuration A judges |gap| / SE with the SE estimated from the replicates,
# a Student t statistic with replicates - 1 degrees of freedom under a correct
# model. Its 3-SE limit then fails a correct model with probability
# 2 * t.sf(3, n - 1): 20.5% at 2 replicates (the T042 smoke run), 5.8% at 4,
# 4.0% at 5, 0.74% at the 20 of the full run. 5 is the first count under the
# conventional 5% level; below it configuration A prints "not judged".
MIN_REPLICATES_JUDGED = 5
# Both configurations need a standard error, undefined for one replicate.
MIN_REPLICATES = 2
CLASS = "working"
EDUCATION = 0.3
NEVER = -(10**9)


def tick_age(tick: int) -> float:
    """Age in years at the start of harness tick `tick` (12.0 at tick 0)."""
    return START_AGE + tick / TICKS_PER_YEAR


def death_probability_by_month(template: dict):
    """Return the tick-loop death probability at a tick, keyed by the age in months at that tick.

    The key is the age the market and fertility read at the tick
    (`age_in_years(agent, tick)`). The probability is the one the tick loop
    charges at that tick, `orchestrator.mortality_probability_for` (D-29-20),
    called on a stand-in agent born at tick 0 and a stand-in context at tick
    `months`: the production `exposure_age` then reads the age at the previous
    tick, `(months - 1) / 12`, so the shift between the two ages is the
    engine's own and not a copy of it (D-12-E-5). Defined for `months >= 1`,
    since a newborn is first exposed at the tick after its birth.
    """
    cache: dict[int, float] = {}

    def probability(months: int) -> float:
        if months not in cache:
            agent = SimpleNamespace(birth_tick=0, age=0)
            context = SimpleNamespace(tick=months, template=template)
            cache[months] = mortality_probability_for(agent, context, TICK_HOURS)
        return cache[months]

    return probability


def survival_to_twelve(death_probability) -> float:
    """l_tick(12): survival of a newborn of tick 0 to the tick it is 12, before that mortality.

    The product of 1 - p over ticks 1 to 143: the newborn is first exposed at
    the tick after its birth, and the mortality of the tick at which it is 12
    (exposure age 143/12) is charged by the first harness tick, not here.
    """
    result = 1.0
    for months in range(1, START_AGE * TICKS_PER_YEAR):
        result *= 1.0 - death_probability(months)
    return result


def candidate_age_sampler(template: dict):
    """Return a function drawing a candidate's age from the pyramid above the male minimum age."""
    minimum = template["couple"]["min_marriage_age_male"]
    cut = [
        (max(low, minimum), high, share * (high - max(low, minimum)) / (high - low))
        for low, high, share in template["age_pyramid"]
        if high > minimum
    ]
    weights = [weight for _, _, weight in cut]

    def draw(rng: random.Random) -> float:
        low, high, _ = rng.choices(cut, weights=weights)[0]
        return rng.uniform(low, high)

    return draw


class Cohort:
    """The 20,000 women of one replicate and what the market needs to know of each.

    State is in lists indexed by `woman.id - 1`: `husband_birth` is the harness
    tick at which the husband was born (his age in months at tick k is
    `k - husband_birth`), None when she is not in a couple; `widowed_at` the
    tick of the latest widowhood.
    """

    def __init__(self) -> None:
        self.women = [
            SyntheticAgent(i + 1, "female", START_AGE, CLASS, EDUCATION) for i in range(COHORT_SIZE)
        ]
        self.alive = [True] * COHORT_SIZE
        self.husband_birth: list[int | None] = [None] * COHORT_SIZE
        self.ever_partnered = [False] * COHORT_SIZE
        self.widowed_at = [NEVER] * COHORT_SIZE

    def alive_count(self) -> int:
        """Women of the cohort still alive."""
        return sum(self.alive)

    def in_couple_count(self) -> int:
        """Women of the cohort alive and in a couple."""
        return sum(
            1 for i in range(COHORT_SIZE) if self.alive[i] and self.husband_birth[i] is not None
        )


def is_ineligible(tick: int, widowed_at: int, context) -> bool:
    """Whether a woman may not marry at `tick`: below the minimum age or in mourning.

    The harness copy of the production rule `couple.marriage_ineligibility`
    (`meets_marriage_age` and mourning while `tick - widowed_at <
    mourning_ticks`), reduced to what the cohort varies: every woman has the
    harness age. A test compares the two on a grid of ticks and widowhoods.
    """
    return tick_age(tick) < context.min_age or tick - widowed_at < context.mourning


def tick_market(cohort, tick, context, rng, next_id) -> tuple[int, int]:
    """Run one tick of the market; return the seekers drawn and the next free candidate id."""
    a_k = tick_age(tick)
    free = [
        w
        for w in cohort.women
        if cohort.alive[w.id - 1]
        and cohort.husband_birth[w.id - 1] is None
        and not is_ineligible(tick, cohort.widowed_at[w.id - 1], context)
    ]
    ages = {w.id: a_k for w in free}
    history = MarriageHistory(
        ever_partnered=frozenset(w.id for w in free if cohort.ever_partnered[w.id - 1]),
        widowed_at_tick={},
    )
    population = MarketPopulation(women=free, men=[], ages=ages, history=history)
    # The production probability: first-marriage schedule at the canonical age,
    # remarriage rate for the women who have been in a couple.
    probability = seek_probability_for(
        population, context.schedule, context.remarriage_rate, context.years_per_tick
    )
    seekers = draw_seekers(free, probability, rng)
    if not seekers:
        return 0, next_id
    candidates = []
    for offset in range(CANDIDATE_POOL):
        age = context.candidate_age(rng)
        candidates.append(SyntheticAgent(next_id + offset, "male", age, CLASS, EDUCATION))
        ages[next_id + offset] = age
    weights = context.weights

    def score(woman, man) -> float:
        return homogamy_score(woman, man, weights, sentiments={}, ages=ages)

    for woman, man in match_markets(seekers, candidates, "world", score):
        cohort.husband_birth[woman.id - 1] = tick - math.floor(man.age * TICKS_PER_YEAR)
        cohort.ever_partnered[woman.id - 1] = True
    return len(seekers), next_id + CANDIDATE_POOL


def tick_mortality(cohort, tick, death_probability, rng) -> None:
    """Women and their husbands die at their own ages; a widow starts mourning.

    `death_probability` is keyed by the age in months at this tick (the
    fertility age) and charges the engine's exposure age, one tick younger.
    """
    woman_p = death_probability(tick + START_AGE * TICKS_PER_YEAR)
    for index in range(COHORT_SIZE):
        if not cohort.alive[index]:
            continue
        if rng.random() < woman_p:
            cohort.alive[index] = False
            continue
        birth = cohort.husband_birth[index]
        if birth is not None and rng.random() < death_probability(tick - birth):
            cohort.husband_birth[index] = None
            cohort.widowed_at[index] = tick


def replicate_tick(
    cohort, tick, context, rng, next_id, with_mortality
) -> tuple[int, int, int, int]:
    """Run one harness tick in the engine's step order; return what fertility reads.

    `orchestrator.DEMOGRAPHY_STEPS` runs couple formation (step 2), then
    mortality (step 3, the couple dissolved by succession at step 4), then
    fertility (step 7) on the living women and the active couples. So a woman
    who marries at this tick is already married when the base rate is
    applied, and a woman or a husband who dies at this tick is not.

    Returns the seekers drawn, the next free candidate id, and the women in a
    couple and alive at the moment the base rate is applied.
    """
    seekers, next_id = tick_market(cohort, tick, context, rng, next_id)
    if with_mortality:
        tick_mortality(cohort, tick, context.death_probability, rng)
    return seekers, next_id, cohort.in_couple_count(), cohort.alive_count()


def run_replicate(context, seed: int, with_mortality: bool) -> tuple[float, float, int]:
    """Follow one cohort; return its TFR, its births per initial woman, its busiest tick.

    The TFR weighs the base rate by the share of the women ALIVE who are in
    a couple, M(a) of SC-007 (survivors only). The births per initial woman
    weigh it by the share of the INITIAL cohort in a couple: that is the
    quantity the net reproduction rate needs, since it multiplies by the
    survival to 12. Without mortality the two are equal.
    """
    rng = random.Random(seed)
    cohort = Cohort()
    next_id = COHORT_SIZE + 1
    tfr = 0.0
    births_per_initial = 0.0
    most_seekers = 0
    for tick in range(TICKS):
        seekers, next_id, in_couple, alive = replicate_tick(
            cohort, tick, context, rng, next_id, with_mortality
        )
        most_seekers = max(most_seekers, seekers)
        rate = annual_base_rate(tick_age(tick), context.fertility) / TICKS_PER_YEAR
        births_per_initial += rate * in_couple / COHORT_SIZE
        tfr += rate * in_couple / max(alive, 1)
    return tfr, births_per_initial, most_seekers


def build_context(template: dict) -> SimpleNamespace:
    """Everything a replicate reads and does not change, computed once."""
    couple_cfg = template["couple"]
    schedule = first_marriage_schedule(couple_cfg)
    years = TICK_HOURS / HOURS_PER_YEAR
    return SimpleNamespace(
        schedule=schedule,
        # The base schedule through the single dispatch point (`marital` or
        # `hadwiger`, whichever block the template carries), never a block
        # read by name.
        fertility=template["fertility"],
        weights=couple_cfg["homogamy_weights"],
        min_age=couple_cfg["min_marriage_age_female"],
        mourning=mourning_ticks(couple_cfg, TICK_HOURS, 1.0),
        remarriage_rate=couple_cfg["remarriage_annual_rate_female"],
        first_marriage_probability=[
            schedule.tick_probability(tick_age(tick), years) for tick in range(TICKS)
        ],
        candidate_age=candidate_age_sampler(template),
        death_probability=death_probability_by_month(template),
        years_per_tick=years,
    )


def married_share_by_tick(context) -> list[float]:
    """The deterministic share of the cohort in a couple at each tick, as fertility reads it.

    At each monthly tick the share M first grows by the single share times the
    tick probability of the first-marriage schedule (couple formation, step 2)
    and is then read by fertility (step 7), the engine's step order
    (D-05-E-12), with the hazard at the age at the start of the tick. No random
    draws and no mortality: the propagation of SC-002.
    """
    married = 0.0
    shares = []
    for probability in context.first_marriage_probability:
        married += (1.0 - married) * probability
        shares.append(married)
    return shares


def propagated_reference_tfr(context) -> float:
    """The TFR of the deterministic propagation of the first-marriage hazard.

    The base rate at the age at the start of each tick weighted by the share in
    a couple after that tick's market (`married_share_by_tick`). This is the
    SC-002 propagation at the same ticks as the harness, with no random draws,
    so it measures what the draws should reproduce and not the discretization.
    """
    shares = married_share_by_tick(context)
    total = sum(
        annual_base_rate(tick_age(tick), context.fertility) * share
        for tick, share in enumerate(shares)
    )
    return total / TICKS_PER_YEAR


def continuous_tfr(context) -> float:
    """The continuous value (N3), the integral of the base rate times F*(a) on [m, 50].

    The integral is split in whole years for `quad` because the integrand has
    a kink at the minimum marriage age and the marital schedule jumps at the
    five-year group edges, which fall on whole years.
    """
    low = int(context.min_age)
    return sum(
        quad(
            lambda a: annual_base_rate(a, context.fertility) * context.schedule.conditional_cdf(a),
            year,
            year + 1,
        )[0]
        for year in range(low, END_AGE)
    )


def life_table(template: dict):
    """Return l(x) on whole ages with geometric interpolation inside the year.

    l(0) = 1 and l(x + 1) = l(x) * (1 - q_x), with q_x the annual probability
    of `mortality.annual_mortality_probability` at the whole age x;
    l(x + t) = l(x) * (1 - q_x)^t inside the year. One Heligman-Pollard
    schedule for both sexes, as `mortality.py` has no sex term.
    """
    hp = template["mortality"]["heligman_pollard"]

    def survival(age: float) -> float:
        whole = math.floor(age)
        result = 1.0
        for x in range(whole):
            result *= 1.0 - annual_mortality_probability(x, hp)
        return result * (1.0 - annual_mortality_probability(whole, hp)) ** (age - whole)

    return survival


def analytic_nrr(context, template: dict, survival) -> float:
    """The analytic net reproduction rate without widowhood, at the harness ticks (SC-005).

    NRR = sum over ticks k of f(a_k) M_k l(a_k) / 12 / (1 + sex_ratio_at_birth),
    with a_k the age at the start of tick k, f the base rate
    (`annual_base_rate`), M_k the share in a couple after the tick's market
    (`married_share_by_tick`) and l the whole-age life table (`life_table`).
    The engine's step order: market, then mortality, then fertility, with the
    tick's mortality charged at the previous tick's age
    (`orchestrator.exposure_age`), so a mother of fertility age a has survived
    to l(a), not to l(a + 1/12) (D-12-E-5). Maternal mortality is not modelled.
    For the Christian era it is 1.92686, against 1.92656 with l(a + 1/12) and
    1.92672 for the continuous integral (D-12-E-4, D-12-E-5).
    """
    total = sum(
        annual_base_rate(tick_age(tick), context.fertility) * share * survival(tick_age(tick))
        for tick, share in enumerate(married_share_by_tick(context))
    )
    return total / TICKS_PER_YEAR / (1.0 + template["sex_ratio_at_birth"])


def interval(values: list[float]) -> tuple[float, float, float]:
    """Mean, standard error and 95% Student t half-width of the replicates."""
    mean = statistics.fmean(values)
    error = statistics.stdev(values) / math.sqrt(len(values))
    return mean, error, stats.t.ppf(0.975, len(values) - 1) * error


def run_configuration(context, replicates: int, seed_base: int, with_mortality: bool) -> dict:
    """Run the replicates of one configuration: TFR, births per initial woman, busiest tick."""
    started = time.perf_counter()
    runs = [
        run_replicate(context, seed_base + index, with_mortality) for index in range(replicates)
    ]
    return {
        "tfr": [tfr for tfr, _, _ in runs],
        "births_per_initial": [births for _, births, _ in runs],
        "most_seekers": max(seekers for _, _, seekers in runs),
        "seconds": time.perf_counter() - started,
    }


def summarize_configuration_a(context, result: dict) -> tuple[dict, list[str], bool | None]:
    """Return the table row, the check lines and the verdict of configuration A.

    The verdict is None, "not judged", below `MIN_REPLICATES_JUDGED` replicates.
    """
    mean, error, half = interval(result["tfr"])
    reference = propagated_reference_tfr(context)
    continuous = continuous_tfr(context)
    gap = mean - reference
    distance = abs(gap) / error
    busiest = result["most_seekers"]
    row = {
        "configuration": "A, no mortality",
        "tfr": f"{mean:.4f} +- {half:.4f}",
        "tfr_value": f"{reference:.4f} (propagation)",
        "gap": f"{gap:+.4f}",
        "nrr": "-",
        "nrr_value": "-",
        "l25": "-",
        "seconds": f"{result['seconds']:.0f}",
    }
    notes = [
        f"A: gap {distance:.2f} standard errors (limit {SEEKER_SD_LIMIT}); standard error"
        f" {error:.4f}",
        f"A: continuous value {continuous:.4f}, discretization gap"
        f" {reference - continuous:+.4f} (reported, not gated)",
        f"A: most seekers in a tick {busiest} (limit {MAX_SEEKERS})",
    ]
    if len(result["tfr"]) < MIN_REPLICATES_JUDGED:
        notes.append(f"A: not judged, fewer than {MIN_REPLICATES_JUDGED} replicates")
        return row, notes, None
    return row, notes, distance <= SEEKER_SD_LIMIT and busiest <= MAX_SEEKERS


def summarize_configuration_b(
    context, template: dict, result: dict
) -> tuple[dict, list[str], bool]:
    """Return the table row, the check lines and the verdict of configuration B."""
    survival = life_table(template)
    l12 = survival_to_twelve(context.death_probability)
    divisor = 1.0 + template["sex_ratio_at_birth"]
    nrr_mean, _, nrr_half = interval(
        [l12 * births / divisor for births in result["births_per_initial"]]
    )
    tfr_mean, _, tfr_half = interval(result["tfr"])
    analytic = analytic_nrr(context, template, survival)
    lower, upper = nrr_mean - nrr_half, nrr_mean + nrr_half
    busiest = result["most_seekers"]
    row = {
        "configuration": "B, mortality, widowhood",
        "tfr": f"{tfr_mean:.4f} +- {tfr_half:.4f}",
        "tfr_value": "none (no threshold)",
        "gap": "-",
        "nrr": f"{nrr_mean:.4f} [{lower:.4f}, {upper:.4f}]",
        "nrr_value": f"{analytic:.4f} (gap {nrr_mean - analytic:+.4f})",
        "l25": f"{survival(25):.4f}",
        "seconds": f"{result['seconds']:.0f}",
    }
    notes = [
        f"B: survival to the first harness tick (engine exposure age 143/12, not the table"
        f" l(12) = {survival(12):.4f}) = {l12:.4f}; the analytic NRR"
        " has no widowhood and no maternal mortality (not modelled)",
        f"B: NRR upper bound {upper:.4f} (fails below 1, couples SC-007); lower bound"
        f" {lower:.4f} (fails above the analytic NRR without widowhood {analytic:.5f}, SC-005)",
        f"B: most seekers in a tick {busiest} (limit {MAX_SEEKERS})",
    ]
    # Widowhood and mourning can only remove years in a couple, so the
    # measured NRR cannot exceed the analytic value without widowhood (SC-005).
    coherent = lower <= analytic
    return row, notes, bool(upper >= 1.0 and coherent and busiest <= MAX_SEEKERS)


TABLE_COLUMNS = (
    ("configuration", "configuration"),
    ("tfr", "TFR mean +- 95% t"),
    ("tfr_value", "TFR reference"),
    ("gap", "gap"),
    ("nrr", "NRR harness [95% t]"),
    ("nrr_value", "NRR analytic"),
    ("l25", "l(25)"),
    ("seconds", "s"),
)


def print_table(rows: list[dict]) -> None:
    """Print the rows of both configurations as one aligned table."""
    widths = [max(len(title), *(len(row[key]) for row in rows)) for key, title in TABLE_COLUMNS]
    for cells in [
        [title for _, title in TABLE_COLUMNS],
        *([row[k] for k, _ in TABLE_COLUMNS] for row in rows),
    ]:
        print("  ".join(cell.ljust(width) for cell, width in zip(cells, widths)))


VERDICT_WORDS = {True: "pass", False: "FAIL", None: "not judged"}


def main(argv: list[str] | None = None) -> int:
    """Run both configurations; return 0 only when both pass ("not judged" returns 1)."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--replicates", type=int, default=20)
    parser.add_argument("--seed-base", type=int, default=1)
    args = parser.parse_args(argv)
    if args.replicates < MIN_REPLICATES:
        parser.error(f"--replicates must be at least {MIN_REPLICATES}: a standard error needs two")
    template = load_template(TEMPLATE_NAME)
    context = build_context(template)
    print(
        f"{args.replicates} replicates of {COHORT_SIZE} women, {TICKS} monthly ticks, seeds from"
        f" {args.seed_base}"
    )
    result_a = run_configuration(context, args.replicates, args.seed_base, with_mortality=False)
    row_a, notes_a, ok_a = summarize_configuration_a(context, result_a)
    result_b = run_configuration(context, args.replicates, args.seed_base, with_mortality=True)
    row_b, notes_b, ok_b = summarize_configuration_b(context, template, result_b)
    print()
    print_table([row_a, row_b])
    print()
    print("\n".join([*notes_a, *notes_b]))
    print(f"RESULT: A {VERDICT_WORDS[ok_a]}, B {VERDICT_WORDS[ok_b]}")
    return 0 if ok_a and ok_b else 1


if __name__ == "__main__":
    sys.exit(main())

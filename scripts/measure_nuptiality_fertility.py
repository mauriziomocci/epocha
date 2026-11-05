"""Measure the realized nuptiality and fertility of the rule-based couples (spec SC-007).

Run from the repository root, outside the test suite:

    PYTHONPATH=. python scripts/measure_nuptiality_fertility.py [--replicates 20] [--seed-base 1]

What it answers. With `require_couple_for_birth` the Hadwiger schedule of
equation (4.2) applies to married women only, so the fertility a cohort
realizes is the integral of the schedule weighted by the share of women in a
couple at each age. This script follows a cohort of 20,000 women from 12 to
50 years at monthly ticks and reports that fertility, in two configurations:

- A, no mortality (hence no widowhood and no remarriage). Failure when the
  mean TFR of the replicates is further than 3 standard errors (sd /
  sqrt(replicates)) from the reference, the deterministic propagation of the
  first-marriage hazard at the same monthly ticks, or when a tick has more
  than 500 seekers (the always-available-men assumption would not hold).
- B, with mortality, widowhood, mourning and the remarriage rate. The TFR,
  with M(a) the share in a couple among the women alive at that age (SC-007),
  has no threshold (widowhood and the remarriage rate are heuristics); the net
  reproduction rate has one: failure when the upper bound of its 95%
  Student t interval is below 1, because choice A of D-RBC-04 (keep the
  Hadwiger rate for married women for now) rests on the population not
  dying out under the wrong model.

Harness assumptions, every one declared:

- Men are female-dominant and always available: each tick the candidates
  are 500 never-married men redrawn from the template `age_pyramid` above
  `min_marriage_age_male` (a bracket partly below it is cut at it), not a
  simulated male population. Husbands are tracked only to die.
- Every woman and every candidate has `social_class = "working"` and
  `education_level = 0.3`, so only the age term of the homogamy score varies.
- One Heligman-Pollard schedule is used for both sexes, as `mortality.py` has
  no sex term. The husband dies at his own age.
- Becker modulation and the Malthusian ceiling are excluded by construction:
  the measure concerns the interaction of nuptiality and equation (4.2).
- Maternal mortality (0.008 per birth in the template) is not modelled, in
  both the harness and the analytic values.
- Mourning is `couple.mourning_ticks` after a husband's death; a woman who
  has been in a couple draws on the remarriage rate `r_f`
  (`remarriage_annual_rate_female`), a never-married one on the first-marriage
  schedule (plan PD-07). Separation does not exist in the harness.
- Mortality uses the function the tick loop uses after D-29-20,
  `orchestrator.mortality_probability_for`, evaluated at the age at the
  start of the tick's interval and cached per whole month of age.

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
    draw_seekers,
    homogamy_score,
    match_markets,
    mourning_ticks,
)
from epocha.apps.demography.fertility import hadwiger_asfr
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
CLASS = "working"
EDUCATION = 0.3
NEVER = -(10**9)


def tick_age(tick: int) -> float:
    """Age in years at the start of harness tick `tick` (12.0 at tick 0)."""
    return START_AGE + tick / TICKS_PER_YEAR


def death_probability_by_month(template: dict):
    """Return the tick-loop death probability as a cached function of age in months.

    It calls `orchestrator.mortality_probability_for`, the function the tick
    loop uses after D-29-20, on a stand-in agent born at tick 0 and a stand-in
    context at the tick whose interval opens at that age (exposure age is
    `age_in_years(agent, tick - 1, ...)`). The monthly tick makes the age
    exactly `months / 12`.
    """
    cache: dict[int, float] = {}

    def probability(months: int) -> float:
        if months not in cache:
            agent = SimpleNamespace(birth_tick=0, age=0)
            context = SimpleNamespace(tick=months + 1, template=template)
            cache[months] = mortality_probability_for(agent, context, TICK_HOURS)
        return cache[months]

    return probability


def survival_to_twelve(death_probability) -> float:
    """l_tick(12): the product of 1 - p_tick over the monthly ticks from age 0 to 12."""
    result = 1.0
    for month in range(START_AGE * TICKS_PER_YEAR):
        result *= 1.0 - death_probability(month)
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


def tick_market(cohort, tick, context, rng, next_id) -> tuple[int, int]:
    """Run one tick of the market; return the seekers drawn and the next free candidate id."""
    a_k = tick_age(tick)
    if a_k < context.min_age:
        return 0, next_id
    free = [
        w
        for w in cohort.women
        if cohort.alive[w.id - 1]
        and cohort.husband_birth[w.id - 1] is None
        and tick - cohort.widowed_at[w.id - 1] >= context.mourning
    ]
    first = context.first_marriage_probability[tick]

    def probability(woman) -> float:
        return context.remarriage if cohort.ever_partnered[woman.id - 1] else first

    seekers = draw_seekers(free, probability, rng)
    if not seekers:
        return 0, next_id
    candidates = []
    ages = {w.id: a_k for w in seekers}
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
    """Women and their husbands die at their own ages; a widow starts mourning."""
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


def run_replicate(context, seed: int, with_mortality: bool) -> tuple[float, float, int]:
    """Follow one cohort; return its TFR, its births per initial woman, its busiest tick.

    The TFR weighs the Hadwiger rate by the share of the women ALIVE who are in
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
        # The engine runs couple formation before fertility within a tick
        # (`orchestrator.DEMOGRAPHY_STEPS`), so a woman who marries at this
        # tick is already married when the Hadwiger rate is applied.
        seekers, next_id = tick_market(cohort, tick, context, rng, next_id)
        most_seekers = max(most_seekers, seekers)
        rate = hadwiger_asfr(tick_age(tick), context.hadwiger) / TICKS_PER_YEAR
        in_couple = cohort.in_couple_count()
        births_per_initial += rate * in_couple / COHORT_SIZE
        tfr += rate * in_couple / max(cohort.alive_count(), 1)
        if with_mortality:
            tick_mortality(cohort, tick, context.death_probability, rng)
    return tfr, births_per_initial, most_seekers


def build_context(template: dict) -> SimpleNamespace:
    """Everything a replicate reads and does not change, computed once."""
    couple_cfg = template["couple"]
    schedule = first_marriage_schedule(couple_cfg)
    years = TICK_HOURS / HOURS_PER_YEAR
    return SimpleNamespace(
        schedule=schedule,
        hadwiger=template["fertility"]["hadwiger"],
        weights=couple_cfg["homogamy_weights"],
        min_age=couple_cfg["min_marriage_age_female"],
        mourning=mourning_ticks(couple_cfg, TICK_HOURS, 1.0),
        remarriage=1.0 - math.exp(-couple_cfg["remarriage_annual_rate_female"] * years),
        first_marriage_probability=[
            schedule.tick_probability(tick_age(tick), years) for tick in range(TICKS)
        ],
        candidate_age=candidate_age_sampler(template),
        death_probability=death_probability_by_month(template),
        years_per_tick=years,
    )


def propagated_reference_tfr(context) -> float:
    """The TFR of the deterministic propagation of the first-marriage hazard.

    At each monthly tick the share of women in a couple, M, first grows by the
    single share times the tick probability of the schedule (couple formation)
    and then weighs the Hadwiger rate (fertility), the engine's step order,
    with the rate at the age at the start of the tick. This is the SC-002
    propagation at the same ticks as the harness, with no random draws, so it
    measures what the draws should reproduce and not the discretization.
    """
    married = 0.0
    tfr = 0.0
    for tick in range(TICKS):
        married += (1.0 - married) * context.first_marriage_probability[tick]
        tfr += hadwiger_asfr(tick_age(tick), context.hadwiger) * married / TICKS_PER_YEAR
    return tfr


def continuous_tfr(context) -> float:
    """The continuous value, the integral of the Hadwiger rate times F*(a) on [m, 50].

    The integral is split in whole years for `quad` because the schedule has
    a kink at the minimum marriage age and at the Hadwiger bounds.
    """
    low = int(context.min_age)
    return sum(
        quad(
            lambda a: hadwiger_asfr(a, context.hadwiger) * context.schedule.conditional_cdf(a),
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
    """The analytic net reproduction rate, without widowhood and maternal mortality.

    NRR = integral on [m, 50] of f_H(a) F*(a) l(a) da / (1 + sex_ratio_at_birth),
    f_H the Hadwiger rate, F* the conditioned share married, l the life table.
    """
    low = int(context.min_age)
    total = sum(
        quad(
            lambda a: (
                hadwiger_asfr(a, context.hadwiger)
                * context.schedule.conditional_cdf(a)
                * survival(a)
            ),
            year,
            year + 1,
        )[0]
        for year in range(low, END_AGE)
    )
    return total / (1.0 + template["sex_ratio_at_birth"])


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


def report_configuration_a(context, result: dict) -> bool:
    """Print configuration A against its references; return True when it passes."""
    mean, error, half = interval(result["tfr"])
    reference = propagated_reference_tfr(context)
    continuous = continuous_tfr(context)
    gap = mean - reference
    distance = abs(gap) / error
    busiest = result["most_seekers"]
    print("A, no mortality")
    print(f"  TFR mean {mean:.4f} +- {half:.4f} (95% t), standard error {error:.4f}")
    print(f"  reference (propagation, same ticks) {reference:.4f}")
    print(f"  gap {gap:+.4f} = {distance:.2f} standard errors (limit {SEEKER_SD_LIMIT})")
    print(f"  continuous value {continuous:.4f}")
    print(f"  discretization gap {reference - continuous:+.4f} (reported, not gated)")
    print(f"  most seekers in a tick {busiest} (limit {MAX_SEEKERS})")
    print(f"  runtime {result['seconds']:.0f} s")
    return distance <= SEEKER_SD_LIMIT and busiest <= MAX_SEEKERS


def report_configuration_b(context, template: dict, result: dict) -> bool:
    """Print configuration B with the life table and the NRR; return True when it passes."""
    survival = life_table(template)
    l12 = survival_to_twelve(context.death_probability)
    divisor = 1.0 + template["sex_ratio_at_birth"]
    nrr_mean, _, nrr_half = interval(
        [l12 * births / divisor for births in result["births_per_initial"]]
    )
    tfr_mean, _, tfr_half = interval(result["tfr"])
    analytic = analytic_nrr(context, template, survival)
    busiest = result["most_seekers"]
    print("B, mortality, widowhood, mourning and remarriage (maternal mortality not modelled)")
    print(f"  TFR mean {tfr_mean:.4f} +- {tfr_half:.4f} (95% t, no threshold)")
    print(f"  NRR harness {nrr_mean:.4f} +- {nrr_half:.4f}")
    print(f"  NRR interval [{nrr_mean - nrr_half:.4f}, {nrr_mean + nrr_half:.4f}]")
    print(f"  NRR analytic {analytic:.4f} (no widowhood, no maternal mortality)")
    print(f"  gap harness - analytic {nrr_mean - analytic:+.4f}")
    print(f"  life table l(25) = {survival(25):.4f}, table l(12) = {survival(12):.4f}")
    print(f"  tick-loop l_tick(12) = {l12:.4f}")
    print(f"  most seekers in a tick {busiest} (limit {MAX_SEEKERS})")
    print(f"  runtime {result['seconds']:.0f} s")
    return nrr_mean + nrr_half >= 1.0 and busiest <= MAX_SEEKERS


def main(argv: list[str] | None = None) -> int:
    """Run both configurations; return 1 on the failure condition of either."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--replicates", type=int, default=20)
    parser.add_argument("--seed-base", type=int, default=1)
    args = parser.parse_args(argv)
    template = load_template(TEMPLATE_NAME)
    context = build_context(template)
    print(
        f"{args.replicates} replicates of {COHORT_SIZE} women, {TICKS} monthly ticks, seeds from"
        f" {args.seed_base}"
    )
    result_a = run_configuration(context, args.replicates, args.seed_base, with_mortality=False)
    ok_a = report_configuration_a(context, result_a)
    result_b = run_configuration(context, args.replicates, args.seed_base, with_mortality=True)
    ok_b = report_configuration_b(context, template, result_b)
    print(f"RESULT: A {'pass' if ok_a else 'FAIL'}, B {'pass' if ok_b else 'FAIL'}")
    return 0 if ok_a and ok_b else 1


if __name__ == "__main__":
    sys.exit(main())

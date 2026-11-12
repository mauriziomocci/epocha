"""The eligibility rule of the SC-007 measurement harness agrees with production.

`scripts/measure_nuptiality_fertility.py` runs 20,000 women for 456 ticks, so it
cannot call `couple.marriage_ineligibility` once per woman and tick; it keeps a
reduced copy, `is_ineligible`, valid because every woman of the cohort has the
harness age. A copy of a production rule drifts silently, so this test compares
the two on the whole grid of ticks and widowhood ticks the harness can reach.
The seek probability needs no such test: the harness calls
`couple.seek_probability_for` itself.

The harness must also follow the engine's step order: `DEMOGRAPHY_STEPS` runs
mortality (step 3, with the couple dissolved by succession at step 4) before
fertility (step 7), so a woman or a husband who dies at a tick does not count
for that tick's births. The second and third tests hold the harness to it.

Mortality is charged at the engine's exposure age: `orchestrator.exposure_age`
reads the age at the PREVIOUS tick, while the market and fertility read the age
at the current one (decision D-12-E-5). The last two tests hold the harness's
per-tick death probability and its survival to 12 to the production function.

Configuration A judges the gap in standard errors estimated from the
replicates, a Student t statistic with replicates - 1 degrees of freedom: below
`MIN_REPLICATES_JUDGED` its 3-standard-error limit fails a correct model too
often, so the verdict is "not judged". Two tests hold that rule, one the guard
against a single replicate, whose standard error does not exist.

Configuration B has a coherence condition (marital fertility SC-005): widowhood
and mourning can only remove years in a couple, so the lower bound of the
measured NRR must not exceed the analytic NRR without widowhood, computed at
the same monthly ticks in the engine's step order. The last tests hold that
value to 1.92686 and the verdict to the condition.
"""

import random
from types import SimpleNamespace

import pytest

from epocha.apps.demography.couple import MarriageHistory, marriage_ineligibility
from epocha.apps.demography.orchestrator import mortality_probability_for
from epocha.apps.demography.template_loader import load_template
from scripts.measure_nuptiality_fertility import (
    NEVER,
    START_AGE,
    TEMPLATE_NAME,
    TICK_HOURS,
    TICKS,
    TICKS_PER_YEAR,
    Cohort,
    analytic_nrr,
    build_context,
    is_ineligible,
    life_table,
    main,
    propagated_reference_tfr,
    replicate_tick,
    summarize_configuration_a,
    summarize_configuration_b,
    survival_to_twelve,
)


def test_the_harness_eligibility_equals_the_production_rule_on_the_whole_grid():
    template = load_template(TEMPLATE_NAME)
    context = build_context(template)
    # Born START_AGE years before tick 0, as the harness cohort is.
    woman = SimpleNamespace(
        id=1, gender="female", birth_tick=-START_AGE * TICKS_PER_YEAR, age=START_AGE
    )
    checked = 0
    for tick in range(TICKS):
        for widowed_at in (
            NEVER,
            tick,
            tick - 1,
            tick - context.mourning + 1,
            tick - context.mourning,
            tick - context.mourning - 1,
        ):
            history = MarriageHistory(
                ever_partnered=frozenset(),
                widowed_at_tick={} if widowed_at == NEVER else {woman.id: widowed_at},
            )
            production = marriage_ineligibility(woman, template, tick, TICK_HOURS, history)
            assert is_ineligible(tick, widowed_at, context) == (production is not None), (
                tick,
                widowed_at,
                production,
            )
            checked += 1
    assert checked == TICKS * 6


# Harness tick 156: the women are 25, where the base rate is near its peak.
TICK_AT_25 = 13 * TICKS_PER_YEAR
HUSBAND_AGE_MONTHS = 60 * TICKS_PER_YEAR


def one_married_woman_cohort():
    """A cohort whose only living woman is 25 and married to a man of 60.

    Every other woman is dead, so the market has no seeker and the tick tests
    only the order of mortality and fertility.
    """
    cohort = Cohort()
    cohort.alive = [False] * len(cohort.alive)
    cohort.alive[0] = True
    cohort.husband_birth[0] = TICK_AT_25 - HUSBAND_AGE_MONTHS
    cohort.ever_partnered[0] = True
    return cohort


def context_with_death(death_probability):
    """The harness context of the template with a scripted death probability by age in months."""
    context = build_context(load_template(TEMPLATE_NAME))
    return SimpleNamespace(**{**vars(context), "death_probability": death_probability})


@pytest.mark.parametrize(
    ("who_dies", "death_probability", "alive_after"),
    [
        ("the woman", lambda months: 1.0, 0),
        ("the husband", lambda months: 1.0 if months >= HUSBAND_AGE_MONTHS else 0.0, 1),
    ],
)
def test_a_death_at_a_tick_removes_the_couple_from_that_tick_fertility(
    who_dies, death_probability, alive_after
):
    cohort = one_married_woman_cohort()
    context = context_with_death(death_probability)

    _, _, in_couple, alive = replicate_tick(
        cohort, TICK_AT_25, context, random.Random(1), 10**6, with_mortality=True
    )
    assert (in_couple, alive) == (0, alive_after), who_dies


def test_without_mortality_the_married_woman_counts_for_the_tick_fertility():
    cohort = one_married_woman_cohort()
    context = context_with_death(lambda months: 1.0)

    _, _, in_couple, alive = replicate_tick(
        cohort, TICK_AT_25, context, random.Random(1), 10**6, with_mortality=False
    )
    assert (in_couple, alive) == (1, 1)


def test_the_harness_charges_each_death_at_the_engine_exposure_age():
    """The woman and the husband of a harness tick die with the probability the
    tick loop gives an agent of their age at that tick (D-12-E-5).

    With the cohort born START_AGE years before tick 0 a harness tick is the
    engine tick of the same number, so the production call is made on agents
    born at the ticks the harness implies. The recorder returns 0 so that both
    draws happen and nobody dies; the real harness function is then evaluated
    on the arguments the tick passed.
    """
    template = load_template(TEMPLATE_NAME)
    harness_probability = build_context(template).death_probability
    passed = []

    def recorder(months):
        passed.append(months)
        return 0.0

    cohort = one_married_woman_cohort()
    replicate_tick(cohort, TICK_AT_25, context_with_death(recorder), random.Random(1), 10**6, True)

    engine_context = SimpleNamespace(tick=TICK_AT_25, template=template)
    woman = SimpleNamespace(birth_tick=-START_AGE * TICKS_PER_YEAR, age=None)
    husband = SimpleNamespace(birth_tick=cohort.husband_birth[0], age=None)
    expected = [
        mortality_probability_for(agent, engine_context, TICK_HOURS) for agent in (woman, husband)
    ]
    assert [harness_probability(months) for months in passed] == expected


def test_the_survival_to_twelve_stops_before_the_mortality_of_the_first_harness_tick():
    """l_tick(12) is the engine survival of a newborn of tick 0 up to the tick at
    which it is 12, BEFORE that tick's mortality, which the first harness tick
    charges: ticks 1 to 143, the newborn being first exposed at the tick after
    its birth (`orchestrator.exposure_age`)."""
    template = load_template(TEMPLATE_NAME)
    newborn = SimpleNamespace(birth_tick=0, age=None)
    expected = 1.0
    for tick in range(1, START_AGE * TICKS_PER_YEAR):
        context = SimpleNamespace(tick=tick, template=template)
        expected *= 1.0 - mortality_probability_for(newborn, context, TICK_HOURS)

    assert survival_to_twelve(build_context(template).death_probability) == pytest.approx(
        expected, rel=1e-12
    )


# SC-005: the analytic NRR without widowhood at monthly ticks in the engine's
# order, with l(a) at the fertility age a (D-12-E-5). The alternatives fall
# outside the 5e-5 tolerance: l(a + dt) gives 1.92656, the continuous integral
# 1.92672 (rounds 7 and 8 of the audit, D-12-E-4).
MONTHLY_ENGINE_ORDER_NRR = 1.92686
NRR_TOLERANCE = 5e-5


def test_the_analytic_nrr_is_the_monthly_engine_order_value():
    template = load_template(TEMPLATE_NAME)
    context = build_context(template)

    value = analytic_nrr(context, template, life_table(template))

    assert value == pytest.approx(MONTHLY_ENGINE_ORDER_NRR, abs=NRR_TOLERANCE)


def configuration_b_result(nrr_values, template, context):
    """A configuration-B result whose replicates give exactly `nrr_values`.

    `summarize_configuration_b` turns births per initial woman into the NRR as
    l_tick(12) * births / (1 + sex_ratio_at_birth); this inverts it.
    """
    l12 = survival_to_twelve(context.death_probability)
    divisor = 1.0 + template["sex_ratio_at_birth"]
    return {
        "tfr": [4.0] * len(nrr_values),
        "births_per_initial": [nrr * divisor / l12 for nrr in nrr_values],
        "most_seekers": 0,
        "seconds": 0.0,
    }


@pytest.mark.parametrize(
    ("nrr_values", "passes"),
    [
        # Interval about [1.80, 1.90]: below the analytic value, above 1.
        ((1.84, 1.85, 1.86), True),
        # Lower bound above the analytic value: widowhood added years in a couple.
        ((2.04, 2.05, 2.06), False),
        # Upper bound below 1, the condition inherited from the couples SC-007.
        ((0.94, 0.95, 0.96), False),
    ],
)
def test_the_configuration_b_verdict_holds_both_conditions(nrr_values, passes):
    template = load_template(TEMPLATE_NAME)
    context = build_context(template)

    _, _, verdict = summarize_configuration_b(
        context, template, configuration_b_result(nrr_values, template, context)
    )

    assert verdict is passes


def configuration_a_result(gap, replicates, context):
    """A configuration-A result: TFRs at reference + gap +- 0.001, `replicates` of them."""
    reference = propagated_reference_tfr(context)
    spread = [0.001 * (-1) ** index for index in range(replicates)]
    return {
        "tfr": [reference + gap + offset for offset in spread],
        "most_seekers": 0,
        "seconds": 0.0,
    }


@pytest.mark.parametrize(
    ("replicates", "verdict"),
    [
        # 4 replicates: 3 degrees of freedom, a 3-SE gap is a false fail 5.8% of the time.
        (4, None),
        # 5 replicates and a gap of tens of standard errors: judged, FAIL.
        (5, False),
    ],
)
def test_the_configuration_a_verdict_needs_the_minimum_replicates(replicates, verdict):
    template = load_template(TEMPLATE_NAME)
    context = build_context(template)

    _, _, judged = summarize_configuration_a(
        context, configuration_a_result(0.05, replicates, context)
    )

    assert judged is verdict


def test_the_configuration_a_verdict_passes_on_the_reference_with_the_minimum():
    template = load_template(TEMPLATE_NAME)
    context = build_context(template)

    _, _, judged = summarize_configuration_a(context, configuration_a_result(0.0, 5, context))

    assert judged is True


def test_the_script_refuses_a_single_replicate_before_running():
    with pytest.raises(SystemExit):
        main(["--replicates", "1"])

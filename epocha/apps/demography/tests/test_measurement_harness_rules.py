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
    build_context,
    is_ineligible,
    replicate_tick,
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


# Harness tick 156: the women are 25, where the Hadwiger rate is near its peak.
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

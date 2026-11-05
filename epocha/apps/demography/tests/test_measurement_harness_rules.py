"""The eligibility rule of the SC-007 measurement harness agrees with production.

`scripts/measure_nuptiality_fertility.py` runs 20,000 women for 456 ticks, so it
cannot call `couple.marriage_ineligibility` once per woman and tick; it keeps a
reduced copy, `is_ineligible`, valid because every woman of the cohort has the
harness age. A copy of a production rule drifts silently, so this test compares
the two on the whole grid of ticks and widowhood ticks the harness can reach.
The seek probability needs no such test: the harness calls
`couple.seek_probability_for` itself.
"""

from types import SimpleNamespace

from epocha.apps.demography.couple import MarriageHistory, marriage_ineligibility
from epocha.apps.demography.template_loader import load_template
from scripts.measure_nuptiality_fertility import (
    NEVER,
    START_AGE,
    TEMPLATE_NAME,
    TICK_HOURS,
    TICKS,
    TICKS_PER_YEAR,
    build_context,
    is_ineligible,
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

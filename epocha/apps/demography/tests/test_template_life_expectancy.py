"""Pin the life expectancy at birth implied by the shipped mortality templates.

Whitepaper section 4.1.1 publishes the `e0` that each era template gives
(70.7, 78.1 and 86.8 years) and compares the pre-industrial figure with
England in 1701. Those numbers describe the JSON parameters, which were never
fitted; this test keeps the published figures and the shipped parameters from
drifting apart silently, in either direction.

Convention: the COMPLETE expectation of life on a single-year life table,
with a constant force of mortality inside each year of age, so that the
person-years lived between exact ages x and x+1 are
L(x) = (l(x) - l(x+1)) / mu(x), with mu(x) = -ln(1 - q(x))
(Preston, Heuveline & Guillot 2001, Demography: Measuring and Modeling
Population Processes, ch. 3; page not verified). The curtate expectation,
which counts completed years only, is about half a year lower (70.24 for the
pre-industrial templates) and is NOT what the whitepaper reports.

`q(x)` is read from `annual_mortality_probability`, the function the tick
loop uses, so the test measures the schedule the simulation actually runs.
"""

from __future__ import annotations

import math

import pytest

from epocha.apps.demography.mortality import annual_mortality_probability
from epocha.apps.demography.template_loader import load_template

# Oldest age of the life table. With the shipped parameters the survivors at
# this age are below 1e-30 for every template tested here, so the omitted tail
# cannot move e0 at the one-decimal precision the whitepaper reports.
_LIFE_TABLE_MAX_AGE = 150


def complete_life_expectancy_at_birth(hp_params: dict[str, float]) -> float:
    """Return complete e0 under a constant force of mortality within each year.

    Preston, Heuveline & Guillot (2001), ch. 3: with mu(x) = -ln(1 - q(x))
    constant on [x, x+1), L(x) = (l(x) - l(x+1)) / mu(x); e0 = sum L(x) / l(0)
    with l(0) = 1. A year with q(x) = 0 contributes a full year, the limit of
    the same expression as mu(x) -> 0.
    """
    survivors = 1.0
    person_years = 0.0
    for age in range(_LIFE_TABLE_MAX_AGE + 1):
        death_probability = annual_mortality_probability(age, hp_params)
        next_survivors = survivors * (1.0 - death_probability)
        force = -math.log1p(-death_probability)
        if force > 0.0:
            person_years += (survivors - next_survivors) / force
        else:
            person_years += survivors
        survivors = next_survivors
    return person_years


@pytest.mark.parametrize(
    ("template_name", "published_e0"),
    [
        ("pre_industrial_christian", 70.7),
        ("pre_industrial_islamic", 70.7),
        ("industrial", 78.1),
        ("modern_democracy", 86.8),
    ],
)
def test_shipped_template_e0_matches_whitepaper(template_name, published_e0):
    """The e0 of each template with an empirical target equals section 4.1.1."""
    hp_params = load_template(template_name)["mortality"]["heligman_pollard"]

    e0 = complete_life_expectancy_at_birth(hp_params)

    assert round(e0, 1) == published_e0

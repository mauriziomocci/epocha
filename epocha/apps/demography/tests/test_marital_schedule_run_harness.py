"""The SC-006 run script records what it needs and judges what it should.

`scripts/measure_marital_schedule_run.py` runs 2,000 founders for 360 ticks,
so its instrumentation must not keep the agents it sees alive for the whole
run: the recorders replace `fertility.tick_birth_probability` and
`fertility.becker_modulation` and keep scalars only. The first test proves
that both replacements are reached the way the tick loop reaches them (the
orchestrator imports the first at call time, the first looks the second up as
a module global) and that no mother survives her call.

All tests are pure: no database, the run loop is replaced by a stand-in that
calls the fertility function exactly as `orchestrator.run_fertility_step` does.
"""

import gc
import weakref
from types import SimpleNamespace

import pytest

import scripts.measure_marital_schedule_run as run_script
from epocha.apps.demography.fertility import annual_base_rate
from epocha.apps.demography.template_loader import load_template

# A month, the SC-006 tick length.
TICK_HOURS = run_script.MONTHLY_TICK_HOURS
TICK = 600
# 25 years at TICK: a group (25-29) with a positive marital rate.
MOTHER_AGE_YEARS = 25
TICKS_PER_YEAR = 12


class StandInMother:
    """The attributes `tick_birth_probability` and `becker_modulation` read; weak-referenceable."""

    def __init__(self) -> None:
        self.id = 7
        self.birth_tick = TICK - MOTHER_AGE_YEARS * TICKS_PER_YEAR
        self.age = MOTHER_AGE_YEARS
        self.wealth = 10.0
        self.education_level = 0.3
        self.mood = 0.5
        self.fertility_state = SimpleNamespace(avoid_conception_flag_tick=None)


ZONE_CONTEXT = {"subsistence": 1.0, "zone_flp": 0.0, "outlook_terms": (0.0, 0.0)}


def call_as_the_orchestrator(template: dict, mother: StandInMother) -> float:
    """`run_fertility_step`'s call: imported at call time, the same arguments."""
    from epocha.apps.demography.fertility import tick_birth_probability

    return tick_birth_probability(
        mother,
        template,
        1,
        TICK_HOURS,
        1.0,
        current_tick=TICK,
        zone_context=ZONE_CONTEXT,
        partnered_agent_ids={mother.id},
    )


def test_the_recorders_are_reached_and_keep_no_mother_alive(monkeypatch):
    template = load_template(run_script.TEMPLATE_NAME)
    survivors = []

    def one_tick(_simulation_id):
        mother = StandInMother()
        reference = weakref.ref(mother)
        call_as_the_orchestrator(template, mother)
        del mother
        gc.collect()
        survivors.append(reference())

    monkeypatch.setattr(run_script, "run_simulation_loop", one_tick)
    monkeypatch.setattr(run_script, "TICKS", 2)
    recorder, _ = run_script.run_instrumented(SimpleNamespace(id=1))

    record = recorder.calls[(TICK, StandInMother().id)]
    assert record.exposure > 0
    assert record.becker is not None  # becker_modulation reached as a module global
    assert survivors == [None, None]


# Configuration A: realized rates per group against M * n(a) * c. One
# thousand woman-years in a couple per group put every group 15-19 to 40-44
# above the floor of 30 expected births and 45-49 under it (17.8).
WOMAN_YEARS = 1000.0


def configuration_a_groups(template: dict, **births_by_start) -> dict:
    """Groups whose births equal the expected count, except the ones given."""
    groups = {}
    for start in run_script.GROUP_STARTS:
        rate = annual_base_rate(start + 2.5, template["fertility"])
        expected = rate * run_script.survival_correction(template) * WOMAN_YEARS
        births = births_by_start.get(f"g{start}", round(expected))
        groups[start] = SimpleNamespace(exposure=WOMAN_YEARS, births=births, weighted=0.0)
    return groups


def test_configuration_a_passes_when_births_follow_the_schedule():
    template = load_template(run_script.TEMPLATE_NAME)
    assert run_script.evaluate_configuration_a(configuration_a_groups(template), template) == []


def test_configuration_a_fails_when_a_group_births_are_suppressed_below_30():
    # 40-44 expects 123.7 births; 20 observed is under the old floor of 30
    # observed births, which stopped judging exactly the suppressed group.
    template = load_template(run_script.TEMPLATE_NAME)
    groups = configuration_a_groups(template, g40=20)
    assert run_script.evaluate_configuration_a(groups, template) == [40]


def test_configuration_a_does_not_judge_a_group_under_30_expected_births():
    template = load_template(run_script.TEMPLATE_NAME)
    groups = configuration_a_groups(template, g45=0)
    assert run_script.evaluate_configuration_a(groups, template) == []


def test_configuration_a_fails_on_a_group_20_44_without_exposure():
    template = load_template(run_script.TEMPLATE_NAME)
    groups = configuration_a_groups(template)
    groups[30] = SimpleNamespace(exposure=0.0, births=0, weighted=0.0)
    groups[15] = SimpleNamespace(exposure=0.0, births=0, weighted=0.0)
    assert run_script.evaluate_configuration_a(groups, template) == [30]


def test_the_summed_probabilities_give_the_expected_written_births():
    # Two partnered calls in 25-29 and one unpartnered (no exposure, p = 0):
    # sum(p) = 0.9, so the expected written births are 0.9 * c.
    template = load_template(run_script.TEMPLATE_NAME)
    recorder = run_script.Recorder()
    month = 1 / 12
    recorder.calls = {
        (1, 1): run_script.CallRecord(26.0, 0.5, 1.0, 0.4, month),
        (1, 2): run_script.CallRecord(27.0, 0.5, 1.0, 0.5, month),
        (1, 3): run_script.CallRecord(27.0, 0.5, None, 0.0, 0),
    }
    groups = run_script.exposure_by_group(recorder)
    groups[25].births = 1
    expected = 0.9 * run_script.survival_correction(template)

    lines = run_script.expected_birth_lines("A", groups, template)

    assert groups[25].probability == 0.9
    assert groups[25].exposure == 2 * month
    assert f"A 25-29: births 1, sum(p) * c {expected:.2f}" in lines


def test_the_rho_bk_interval_carries_the_survival_correction():
    # TMFR = 5 * sum(B / E) / c, so Var(rho_BK) = (5 / (c * T_m))**2 * sum(B / E**2):
    # without the 1 / c**2 the half-width is short by the factor c.
    template = load_template(run_script.TEMPLATE_NAME)
    groups = configuration_a_groups(template)
    c = run_script.survival_correction(template)
    t_m = template["fertility"]["marital"]["total_marital_fertility_20_49"]
    tmfr_groups = [groups[start] for start in run_script.TMFR_GROUP_STARTS]
    rho = 5 * sum(g.births / g.exposure for g in tmfr_groups) / c / t_m
    variance = (5 / (c * t_m)) ** 2 * sum(g.births / g.exposure**2 for g in tmfr_groups)

    value, half = run_script.rho_bk(groups, template)

    assert value == pytest.approx(rho, rel=1e-12)
    assert half == pytest.approx(run_script.NORMAL_975 * variance**0.5, rel=1e-12)

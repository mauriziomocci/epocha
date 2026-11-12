"""Measure the marital fertility schedule realized in a run (marital fertility spec SC-006).

What it answers. The unit tests prove the marital rate r(a) = M * n(a) of
Coale and Trussell (1974), with n(a) the natural fertility schedule of Henry
(1961), in isolation; this script proves that the tick loop realizes it.
It runs `pre_industrial_christian` on a world built without any LLM, as the
integration run of the rule-based couples (User Story 1) does: K = 0
protagonists, 2,000 founders built by `build_rule_only_founders`, monthly
ticks (`tick_duration_hours = 730`), 360 ticks (30 simulated years), one
seed. The template is a test copy with `max_population = 10**6`, so the
Malthusian ceiling (4.4) stays at 1 (with an NRR near 1.9 the shipped 500 is
passed within a few years). The economy is initialized by the shipped path,
`economy.initialization.initialize_economy(simulation,
template_name="pre_industrial")`, the default of the world generator, so
every zone has its `ZoneEconomy`, the subsistence threshold is the model's
and the initial wealth is the one that path assigns; the economy step runs
every tick as in a normal run.

Two configurations, each one run:

- A, every Becker coefficient 0.0, so the Becker factor (4.3) is exactly 1
  whatever the wealth. Per five-year group 15-19 to 45-49 the realized marital
  rate is the births divided by the woman-years spent in a couple. Failure
  when a group with at least 30 EXPECTED births (woman-years times the
  expected rate) is further than 3 Poisson standard errors (sqrt(births) /
  woman-years) from M * n(a) * (1 - q_m * (1 - s_n)), or when a group 20-44
  has no woman-year in a couple: the factor, 0.9944 for the Christian era,
  corrects for `run_fertility_step` writing the BIRTH event only when the
  newborn survives. The floor is on the expected births because a floor on
  the observed ones would stop judging exactly a group whose births the model
  suppressed. Groups under 30 expected births are printed with their count
  and not judged.
- B, the shipped seed Becker coefficients. Per group 20-49 the mean Becker
  factor E[m_BK | g] over the woman-years in a couple, the realized marital
  TMFR 20-49 = 5 * sum_g(B_g / E_g) / 0.9944, rho_BK = TMFR / T_m (spec,
  definition under (N1a)), the Becker factor by decile and the share of
  woman-years whose effective rate r(a) * m_BK exceeds 1 birth per year.
  Failure when the point estimate of rho_BK is outside [0.90, 1.10] (D-MF-09,
  a Trinity heuristic, not a demographic quantity). The 95% interval of
  rho_BK, variance (5 / T_m)**2 * sum_g(B_g / E_g**2) as the spec writes it,
  is printed as conditional on one seed: it does not contain the
  between-run variability of the economic path, and it does not decide.

The result holds only for this configuration (economy `pre_industrial`
through `initialize_economy`, its initial wealth, monthly ticks, one seed),
and the script prints that line next to every number.

Instrumentation. `fertility.tick_birth_probability` and
`fertility.becker_modulation` are replaced with `unittest.mock.patch(...,
new=...)` by recorder methods that call the real functions: the orchestrator
imports the first inside `run_fertility_step` at every call and the first
calls the second as a module global, so both replacements are seen. The
recorders keep scalars only, never the mother: a `wraps=` Mock would keep
every call's arguments, hence every mother, for the whole run
(`test_marital_schedule_run_harness.py`). Per call the recorder keeps the
tick, the mother's id, her age (`orchestrator.age_in_years` with the call's
arguments), whether she is in a couple, the Becker factor returned during
that call and the probability returned. The exposure of a call is
`years_per_tick` when she is in a couple and the base rate is positive: the
woman-years in a couple the model used.
Births are the BIRTH events of the run joined to the mother's age recorded
at the same tick.

How to run it (never collected by the suite, since its name does not match
`test_*.py`):

    DATABASE_URL=<a database this session owns> pytest scripts/measure_marital_schedule_run.py -s

`SC006_FOUNDERS` and `SC006_TICKS` override the founders and the ticks for
a smoke run only; the values in use are printed next to every result.

Cost, measured on the smoke run of task T047 (200 founders, 24 ticks, the
isolated Docker project, 2026-11-12): 79 s of ticks for configuration A and
69 s for B. Extrapolated linearly in founders and ticks (x 150), the full run
takes about 3.3 h for A and 2.9 h for B, 6.2 h in all; this is an
extrapolation, not a measurement, and a population that grows by births
makes it a lower bound.
"""

from __future__ import annotations

import json
import math
import os
import random
import shutil
import statistics
import time
from dataclasses import dataclass, field
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from django.contrib.gis.geos import Point, Polygon

from epocha.apps.demography import fertility, template_loader
from epocha.apps.demography.fertility import (
    FIVE_YEAR_GROUP_WIDTH,
    HENRY_NATURAL_FERTILITY,
    MARITAL_SCHEDULE_MIN_AGE,
    annual_base_rate,
)
from epocha.apps.demography.initialization import initialize_demography
from epocha.apps.demography.models import DemographyEvent
from epocha.apps.demography.orchestrator import age_in_years, years_per_tick
from epocha.apps.economy.initialization import initialize_economy
from epocha.apps.simulation.models import Simulation
from epocha.apps.simulation.tasks import run_simulation_loop
from epocha.apps.simulation.tests.test_rule_based_couples_integration import (
    AGE_DRAW_SEED,
    FIXED_FACTION_IDENTITY,
    build_rule_only_founders,
)
from epocha.apps.users.models import User
from epocha.apps.world.models import Government, World, Zone

TEMPLATE_NAME = "pre_industrial_christian"
# SC-006: the economy template of the world generator's default path.
ECONOMY_TEMPLATE = "pre_industrial"
# SC-006: 2,000 founders, 360 monthly ticks (30 simulated years), K = 0.
FOUNDERS = int(os.environ.get("SC006_FOUNDERS", "2000"))
TICKS = int(os.environ.get("SC006_TICKS", "360"))
MONTHLY_TICK_HOURS = 730.0
# SC-006: max_population of the test copy, so the Malthusian ceiling stays at 1.
MAX_POPULATION = 10**6
# One seed (SC-006); the age draw keeps the couples integration run's seed.
SIMULATION_SEED = 2026
ZONES = 2
# SC-006, configuration A: a group is judged from 30 EXPECTED births (woman-years
# in a couple times the expected rate), at 3 standard errors. The floor is on the
# expected count: on the observed one it would stop judging exactly the group
# whose births the model suppressed.
MIN_EXPECTED_BIRTHS_JUDGED = 30
STANDARD_ERROR_LIMIT = 3.0
# SC-006, configuration B and D-MF-09: the band of rho_BK (a Trinity heuristic).
RHO_BAND = (0.90, 1.10)
NORMAL_975 = 1.959964  # two-sided 95% normal quantile
# Five-year groups 15-19 to 45-49: the marital schedule's lower bound and the
# group starts of n(a) (fertility.HENRY_NATURAL_FERTILITY).
GROUP_STARTS = (
    int(MARITAL_SCHEDULE_MIN_AGE),
    *(int(start) for start, _ in HENRY_NATURAL_FERTILITY),
)
TMFR_GROUP_STARTS = GROUP_STARTS[1:]  # 20-24 to 45-49, the T_m range
# Configuration A fails when one of these groups has no woman-year in a couple:
# with 2,000 founders over 30 years an empty one means that couples or the
# exposure count are broken (an assumption, not a measurement at this size).
# 15-19 (rare marriage under the Hajnal pattern) and 45-49 (17.8 expected
# births per 1,000 woman-years, under the floor) may be empty.
GROUPS_REQUIRING_EXPOSURE = tuple(start for start in TMFR_GROUP_STARTS if start < 45)


class EmptyGroupError(Exception):
    """A group 20-49 has no woman-year in a couple: rho_BK is undefined."""


def configuration_line() -> str:
    """The configuration the result holds for, printed next to every number."""
    return (
        f"configuration: economy {ECONOMY_TEMPLATE!r} via initialize_economy, initial wealth"
        f" of that path, monthly ticks ({MONTHLY_TICK_HOURS:.0f} h), one seed (simulation"
        f" {SIMULATION_SEED}, ages {AGE_DRAW_SEED}), founders {FOUNDERS}, ticks {TICKS}"
    )


def point_loader_at_test_copy(tmp_path, monkeypatch, zero_becker: bool) -> dict:
    """Copy the shipped templates into `tmp_path` and point the loader there.

    The Christian copy gets `max_population = 10**6` and, for configuration
    A, every Becker coefficient 0.0. `_load_template_cached` is keyed on the
    folder, so the copy is parsed afresh. Returns the modified template.
    """
    for source in template_loader.TEMPLATES_DIR.glob("*.json"):
        shutil.copy(source, tmp_path / source.name)
    path = tmp_path / f"{TEMPLATE_NAME}.json"
    template = json.loads(path.read_text())
    template["max_population"] = MAX_POPULATION
    if zero_becker:
        coefficients = template["fertility"]["becker_coefficients"]
        template["fertility"]["becker_coefficients"] = {name: 0.0 for name in coefficients}
    path.write_text(json.dumps(template))
    monkeypatch.setattr(template_loader, "TEMPLATES_DIR", tmp_path)
    return template_loader.load_template(TEMPLATE_NAME)


def founded_simulation(label: str) -> Simulation:
    """A monthly-tick, two-zone world of founders, economy then demography initialized.

    The order of the world generator: `initialize_economy` before
    `initialize_demography` (`world/generator.py`).
    """
    user = User.objects.create_user(
        email=f"sc006-{label}@epocha.dev", username=f"sc006{label}", password="pass1234"
    )
    simulation = Simulation.objects.create(
        name=f"SC006{label}",
        seed=SIMULATION_SEED,
        owner=user,
        current_tick=0,
        status=Simulation.Status.RUNNING,
        config={
            "demography_enabled": True,
            "demography_template": TEMPLATE_NAME,
            "max_protagonists": 0,
        },
    )
    world = World.objects.create(
        simulation=simulation, stability_index=0.7, tick_duration_hours=MONTHLY_TICK_HOURS
    )
    Government.objects.create(simulation=simulation)
    for index in range(ZONES):
        Zone.objects.create(
            world=world,
            name=f"Zone{index}",
            zone_type="residential",
            boundary=Polygon.from_bbox((0, 0, 100, 100)),
            center=Point(50, 50),
        )
    build_rule_only_founders(simulation, world, FOUNDERS, random.Random(AGE_DRAW_SEED))
    initialize_economy(simulation, template_name=ECONOMY_TEMPLATE)
    initialize_demography(simulation)
    return simulation


@dataclass
class CallRecord:
    """One evaluation of `tick_birth_probability` for one mother at one tick."""

    age: float
    base_rate: float
    becker: float | None
    probability: float
    exposure: float


@dataclass
class Recorder:
    """Records each fertility call in scalars; the replaced functions call the real ones."""

    real_probability: object = fertility.tick_birth_probability
    real_becker: object = fertility.becker_modulation
    calls: dict = field(default_factory=dict)
    _becker: float | None = None

    def becker(self, *args, **kwargs) -> float:
        self._becker = self.real_becker(*args, **kwargs)
        return self._becker

    def probability(self, mother, params_era, current_pop, tick_duration_hours, *args, **kwargs):
        self._becker = None
        probability = self.real_probability(
            mother, params_era, current_pop, tick_duration_hours, *args, **kwargs
        )
        acceleration = args[0] if args else kwargs.get("demography_acceleration", 1.0)
        tick = kwargs["current_tick"]
        age = age_in_years(mother, tick, tick_duration_hours, acceleration)
        partners = kwargs.get("partnered_agent_ids")
        partnered = partners is not None and mother.id in partners
        base = annual_base_rate(age, params_era["fertility"])
        exposure = (
            years_per_tick(tick_duration_hours, acceleration) if partnered and base > 0 else 0
        )
        self.calls[(tick, mother.id)] = CallRecord(age, base, self._becker, probability, exposure)
        return probability


def run_instrumented(simulation: Simulation) -> tuple[Recorder, float]:
    """Drive the configured ticks with the fertility calls recorded; return the seconds."""
    recorder = Recorder()
    decision_client = MagicMock(side_effect=AssertionError("the decision LLM was called"))
    started = time.perf_counter()
    with (
        patch("epocha.apps.agents.decision.get_llm_client", decision_client),
        patch(
            "epocha.apps.agents.factions._generate_faction_identity",
            return_value=FIXED_FACTION_IDENTITY,
        ),
        patch("epocha.apps.simulation.tasks.run_simulation_loop.apply_async"),
        # `new=`, not `wraps=`: a wrapping Mock keeps every call's arguments,
        # so every mother of the run would stay alive until the patch ends.
        patch.object(fertility, "tick_birth_probability", new=recorder.probability),
        patch.object(fertility, "becker_modulation", new=recorder.becker),
    ):
        for _ in range(TICKS):
            run_simulation_loop(simulation.id)
    decision_client.assert_not_called()
    return recorder, time.perf_counter() - started


def group_of(age: float) -> int | None:
    """The start of the five-year group of `age`, None outside 15-49."""
    start = int(age // FIVE_YEAR_GROUP_WIDTH * FIVE_YEAR_GROUP_WIDTH)
    return start if start in GROUP_STARTS else None


def group_statistics(simulation: Simulation, recorder: Recorder, first_tick: int) -> dict:
    """Per group: woman-years in a couple, births, Becker-weighted exposure, factors."""
    groups = {
        start: SimpleNamespace(exposure=0.0, births=0, weighted=0.0) for start in GROUP_STARTS
    }
    for record in recorder.calls.values():
        group = group_of(record.age)
        if group is not None and record.exposure > 0:
            groups[group].exposure += record.exposure
            groups[group].weighted += record.exposure * record.becker
    births = DemographyEvent.objects.filter(
        simulation=simulation,
        event_type=DemographyEvent.EventType.BIRTH,
        tick__gt=first_tick,
    ).values_list("tick", "secondary_agent_id")
    for tick, mother_id in births:
        group = group_of(recorder.calls[(tick, mother_id)].age)
        if group is not None:
            groups[group].births += 1
    return groups


def survival_correction(template: dict) -> float:
    """1 - q_m * (1 - s_n): the share of births whose BIRTH event is written (0.9944)."""
    mortality = template["mortality"]
    return 1.0 - mortality["maternal_mortality_rate_per_birth"] * (
        1.0 - mortality["neonatal_survival_when_mother_dies"]
    )


def expected_marital_rate(start: int, template: dict) -> float:
    """M * n(a) * (1 - q_m * (1 - s_n)) at the group's midpoint: the rate of written births."""
    midpoint = start + FIVE_YEAR_GROUP_WIDTH / 2
    return annual_base_rate(midpoint, template["fertility"]) * survival_correction(template)


def judge_group_a(start: int, group, expected: float) -> tuple[str, bool]:
    """The printed line of one group of configuration A and whether it fails."""
    label = f"A {start}-{start + 4}"
    if group.exposure == 0:
        required = start in GROUPS_REQUIRING_EXPOSURE
        return f"{label}: no woman-year in a couple{', FAIL' if required else ''}", required
    expected_births = group.exposure * expected
    realized = group.births / group.exposure
    error = math.sqrt(group.births) / group.exposure
    distance = abs(realized - expected) / error if error else math.inf
    judged = expected_births >= MIN_EXPECTED_BIRTHS_JUDGED
    fails = judged and distance > STANDARD_ERROR_LIMIT
    verdict = ("FAIL" if fails else "judged") if judged else "not judged (< 30 expected)"
    return (
        f"{label}: births {group.births}, expected births {expected_births:.1f},"
        f" woman-years {group.exposure:.1f}, realized {realized:.4f}, expected {expected:.4f},"
        f" {distance:.2f} standard errors, {verdict}"
    ), fails


def evaluate_configuration_a(groups: dict, template: dict) -> list[int]:
    """Print the realized rate of each group; return the groups that fail.

    A group fails when its expected births reach `MIN_EXPECTED_BIRTHS_JUDGED`
    and its realized rate is further than 3 Poisson standard errors from the
    expected one, or when it is in `GROUPS_REQUIRING_EXPOSURE` and has no
    woman-year in a couple.
    """
    failed = []
    for start, group in groups.items():
        line, fails = judge_group_a(start, group, expected_marital_rate(start, template))
        print(line)
        if fails:
            failed.append(start)
    return failed


def rho_bk(groups: dict, template: dict) -> tuple[float, float]:
    """rho_BK = TMFR 20-49 / T_m and the half-width of its one-seed 95% interval."""
    t_m = template["fertility"]["marital"]["total_marital_fertility_20_49"]
    tmfr_groups = [groups[start] for start in TMFR_GROUP_STARTS]
    if any(group.exposure == 0 for group in tmfr_groups):
        raise EmptyGroupError([start for start in TMFR_GROUP_STARTS if not groups[start].exposure])
    width = FIVE_YEAR_GROUP_WIDTH
    tmfr = width * sum(g.births / g.exposure for g in tmfr_groups) / survival_correction(template)
    variance = (width / t_m) ** 2 * sum(g.births / g.exposure**2 for g in tmfr_groups)
    return tmfr / t_m, NORMAL_975 * math.sqrt(variance)


def print_becker_distribution(groups: dict, recorder: Recorder) -> None:
    """Mean factor by group, factor deciles, and the share of rates above 1 per year."""
    for start in TMFR_GROUP_STARTS:
        group = groups[start]
        mean = group.weighted / group.exposure if group.exposure else math.nan
        print(f"B {start}-{start + 4}: E[m_BK | g] {mean:.4f}, births {group.births}")
    exposed = [record for record in recorder.calls.values() if record.exposure > 0]
    factors = [record.becker for record in exposed]
    deciles = statistics.quantiles(factors, n=10) if len(factors) > 1 else factors
    print("B Becker factor deciles: " + ", ".join(f"{value:.3f}" for value in deciles))
    above = sum(record.base_rate * record.becker > 1.0 for record in exposed)
    print(f"B share of woman-years with r(a) * m_BK > 1: {above / max(len(exposed), 1):.4f}")


def measure(tmp_path, monkeypatch, label: str, zero_becker: bool):
    """Build the world for one configuration, run it, return groups, template, seconds."""
    template = point_loader_at_test_copy(tmp_path, monkeypatch, zero_becker)
    simulation = founded_simulation(label)
    first_tick = simulation.current_tick
    recorder, seconds = run_instrumented(simulation)
    simulation.refresh_from_db()
    assert simulation.current_tick == first_tick + TICKS
    print(f"\n{label}: {seconds:.0f} s for {TICKS} ticks; {configuration_line()}")
    return group_statistics(simulation, recorder, first_tick), template, recorder


# Real transactions, as in the couples integration run (decision D-05-E-14):
# the engine commits once per tick, so PostgreSQL prunes superseded rows.
@pytest.mark.django_db(transaction=True)
def test_configuration_a_realizes_the_marital_schedule(tmp_path, monkeypatch):
    groups, template, _ = measure(tmp_path, monkeypatch, "A", zero_becker=True)
    failed = evaluate_configuration_a(groups, template)
    print(f"A RESULT: {'FAIL ' + str(failed) if failed else 'pass'}; {configuration_line()}")
    assert not failed


@pytest.mark.django_db(transaction=True)
def test_configuration_b_rho_bk_within_the_band(tmp_path, monkeypatch):
    groups, template, recorder = measure(tmp_path, monkeypatch, "B", zero_becker=False)
    print_becker_distribution(groups, recorder)
    rho, half = rho_bk(groups, template)
    inside = RHO_BAND[0] <= rho <= RHO_BAND[1]
    print(
        f"B rho_BK {rho:.4f}, 95% interval [{rho - half:.4f}, {rho + half:.4f}]"
        " (conditional on one seed, does not decide);"
        f" band {RHO_BAND}: {'pass' if inside else 'FAIL'}; {configuration_line()}"
    )
    assert inside

"""The per-tick query budget of the demography block (spec FR-016, SC-005).

Two things are measured here, and the distinction between them took three
rounds of the phase-2 gate to get right.

**No query per living agent.** Doubling the living population, at equal vital
events, must leave the block's query count *identical*. This is the property
that matters: an implementation that touches the database once per agent
degrades with the population and is what the requirement forbids.

**A declared upper bound per vital event.** Per-event cost is admitted,
because it is contractual in modules this work item may not rewrite:
`resolve_heirs` costs up to seven queries per death by its own docstring, and
resolving a couple intent costs a read and a write. The bound is therefore an
upper bound at worst-case coefficients, not an equality — an equality would be
unsatisfiable, since the per-death cost varies with the deceased's family
structure. At least one fixture has to *reach* the bound, or a generous bound
would prove nothing.

The zone count is held fixed in every measurement: the fixed term depends on
it, since the subsistence threshold is computed per zone.
"""

from __future__ import annotations

import pytest
from django.contrib.gis.geos import Point, Polygon
from django.db import connection
from django.test.utils import CaptureQueriesContext

from epocha.apps.agents.models import Agent
from epocha.apps.demography.orchestrator import run_demography_tick
from epocha.apps.simulation.models import Simulation
from epocha.apps.users.models import User
from epocha.apps.world.models import Government, World, Zone

TICKS_PER_YEAR = 365.0


def _simulation(label):
    user = User.objects.create_user(
        email=f"cost{label}@epocha.dev", username=f"costuser{label}", password="pass1234"
    )
    sim = Simulation.objects.create(
        name=f"CostTest{label}",
        seed=2026,
        owner=user,
        current_tick=50,
        config={"demography_enabled": True},
    )
    world = World.objects.create(simulation=sim, stability_index=0.7)
    Government.objects.create(simulation=sim)
    zone = Zone.objects.create(
        world=world,
        name="CostZone",
        zone_type="residential",
        boundary=Polygon.from_bbox((0, 0, 100, 100)),
        center=Point(50, 50),
    )
    return sim, zone


def _agent(sim, zone, name, age=40, **kwargs):
    defaults = dict(
        role="farmer",
        location=Point(50, 50),
        health=1.0,
        wealth=1000.0,
        age=age,
        birth_tick=int(sim.current_tick - age * TICKS_PER_YEAR),
        education_level=0.5,
        social_class="working",
        gender=Agent.Gender.MALE,
        personality={},
    )
    defaults.update(kwargs)
    return Agent.objects.create(simulation=sim, name=name, zone=zone, **defaults)


def _couples(sim, zone, count, label):
    """`count` fertile couples: the population the block actually costs.

    A fixture of men alone is worthless here. The fertility step filters
    female agents, so an all-male population never enters its per-candidate
    loop, and the measurement then reports the cost of a step that did not
    run -- which is precisely how the first version of this file passed while
    the block issued seven queries per fertile woman.
    """
    from epocha.apps.demography.couple import form_couple

    for i in range(count):
        man = _agent(sim, zone, f"{label}Uomo{i}", age=32, gender=Agent.Gender.MALE)
        woman = _agent(sim, zone, f"{label}Donna{i}", age=28, gender=Agent.Gender.FEMALE)
        form_couple(man, woman, formed_at_tick=sim.current_tick - 1)


def _count_queries(sim, tick):
    with CaptureQueriesContext(connection) as captured:
        run_demography_tick(sim, tick)
    return len(captured.captured_queries)


@pytest.mark.django_db
def test_doubling_the_living_population_does_not_change_the_count():
    """SC-005 part A: the equality that forbids per-agent queries.

    Both runs carry the same fertile structure -- couples of the same ages,
    one zone -- and differ only in how many of them there are, so any query
    the block issues per living agent shows up as a difference in the count.

    The population is female-bearing and partnered on purpose. An all-male
    fixture never enters the fertility step's per-candidate loop, so it
    measures a step that did not run: that is how the first version of this
    test stayed green while the block issued seven queries per fertile woman,
    and it is the fifth criterion-that-cannot-fail this work item has caught.
    """
    small, zone_small = _simulation("small")
    _couples(small, zone_small, 5, "P")

    large, zone_large = _simulation("large")
    _couples(large, zone_large, 10, "G")

    count_small = _count_queries(small, small.current_tick + 1)
    count_large = _count_queries(large, large.current_tick + 1)

    assert count_small == count_large, (
        f"{count_small} queries at 5 agents and {count_large} at 10: the block "
        "is issuing queries per living agent"
    )


@pytest.mark.django_db
def test_the_count_is_the_pinned_constant_at_zero_vital_events():
    """The fixed term of a tick that has fertile candidates, written down.

    A bound with no measured value is a bound nobody can regress against, so
    the number is asserted rather than described. It is expected to move when
    the block changes; what it must never do is grow with the population,
    which part A covers.
    """
    sim, zone = _simulation("fixed")
    _couples(sim, zone, 5, "F")

    assert _count_queries(sim, sim.current_tick + 1) == FIXED_TERM_WITH_CANDIDATES


@pytest.mark.django_db
def test_a_population_with_no_fertile_candidate_pays_none_of_the_fertility_preloads():
    """The other fixed term, and the reason there are two of them.

    The fertility step preloads what its candidates need -- the living
    population count, the active-couple membership, and the Becker inputs of
    each zone it meets -- and preloads none of it when the filtered candidate
    list comes back empty. So a tick with fertile women costs strictly more
    than a tick without, at the same population and the same zone count.

    Both numbers are pinned rather than one, because a single constant
    covering two populations this different is a constant that describes
    neither: it was one, and the deaths fixture below -- which has no fertile
    women at all -- was being measured against a term that included seven
    queries it never issues.

    The gap is a *conditional fixed* cost, not a per-agent one. FR-016 is
    about the second, and part A is what proves it: the same seven queries
    are paid once whether the zone holds one fertile woman or ten.
    """
    sim, zone = _simulation("nocandidates")
    for i in range(5):
        _agent(sim, zone, f"Vecchio{i}", age=70)

    observed = _count_queries(sim, sim.current_tick + 1)
    assert observed == FIXED_TERM_NO_CANDIDATES
    assert observed < FIXED_TERM_WITH_CANDIDATES, (
        "the two fixed terms have converged: either the preloads moved out of "
        "the candidate branch, or this fixture grew a fertile woman"
    )


class _Deadly:
    """Every mortality draw kills; the cause draw is arbitrary but fixed.

    The schedule is seeded, so at realistic ages a tick produces deaths only
    now and then -- and a cost bound on deaths has to be measured on a tick
    that actually has them.
    """

    def random(self):
        return 0.0

    def gauss(self, mu, sigma):
        return mu

    def randrange(self, n):
        return 0


@pytest.mark.django_db
@pytest.mark.parametrize("population", [2, 4])
def test_a_tick_with_deaths_stays_within_the_declared_bound(population, monkeypatch):
    """SC-005 part B: the upper bound, and fixtures that exercise it.

    Deaths are the expensive event -- up to seven queries each for heir
    resolution alone -- so the bound is measured where it binds, at two
    different death counts so the per-event slope is exercised rather than a
    single point.
    """
    from epocha.apps.demography import orchestrator

    sim, zone = _simulation(f"deaths{population}")
    for i in range(population):
        _agent(sim, zone, f"Anziano{i}", age=70)

    real_stream_for = orchestrator.stream_for
    monkeypatch.setattr(
        orchestrator,
        "stream_for",
        lambda simulation, tick, phase: (
            _Deadly() if phase == "mortality" else real_stream_for(simulation, tick, phase)
        ),
    )

    tick = sim.current_tick + 1
    observed = _count_queries(sim, tick)
    deaths = Agent.objects.filter(simulation=sim, is_alive=False, death_tick=tick).count()

    assert deaths == population, "the fixture did not produce the expected deaths"
    bound = FIXED_TERM_NO_CANDIDATES + PER_DEATH * deaths
    assert observed <= bound, (
        f"{observed} queries for {deaths} deaths exceeds the declared bound "
        f"{FIXED_TERM_NO_CANDIDATES} + {PER_DEATH} x {deaths} = {bound}"
    )
    # The bound has to be reached, not merely respected: a generous bound is
    # satisfied by any implementation and proves nothing. Measured at 12
    # queries per death for the first and 11 for each further one, the slack
    # here is one query per death.
    assert observed >= bound - deaths, (
        f"{observed} queries is well under the declared bound {bound}: the "
        "bound has drifted upward and no longer measures anything"
    )


# Measured, not guessed. Every number here is pinned so a regression is
# visible; they describe the block as it stands and are expected to be
# updated deliberately when it changes -- and only against a fresh
# measurement, never raised to make a red test green.
#
# There are two fixed terms because there are two shapes of tick, and one
# constant covering both described neither. A tick whose filtered candidate
# list is empty skips the fertility step's preloads entirely; a tick with at
# least one fertile candidate pays them once, whatever the population and
# whatever the number of candidates. Measured at one zone in both cases,
# since the fixed term scales with the zone count (FR-016a).
FIXED_TERM_NO_CANDIDATES = 35
FIXED_TERM_WITH_CANDIDATES = 42

# The worst case the inheritance module documents for a single death (seven
# queries for the heir ladder) plus the settlement writes its batch performs
# around them. Measured slope is 10 per death with a further 4 paid once when
# the tick has any death at all; declaring 12 as an upper-bound coefficient
# absorbs that one-off, which is why the bound is reached at two deaths and
# reached again at four rather than drifting loose.
PER_DEATH = 12

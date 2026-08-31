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

    # The stored `age` is made stale on purpose, in both runs. The mortality
    # step refreshes that column from `birth_tick` and writes only the rows
    # whose value actually moved -- so a fixture whose ages already agree
    # never exercises that write at all, and this equality would say nothing
    # about whether it scales with the population. With every row stale, the
    # write fires in both runs, and the counts still have to match: one
    # `bulk_update` for five agents and one for ten.
    Agent.objects.filter(simulation=small).update(age=0)
    Agent.objects.filter(simulation=large).update(age=0)

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
    about the second, and part A is what proves it: the preloads are paid
    once whether the zone holds one fertile woman or ten.

    The equality below is the whole guard, and it used to be followed by
    `assert observed < FIXED_TERM_WITH_CANDIDATES` carrying the message "the
    two fixed terms have converged: either the preloads moved out of the
    candidate branch, or this fixture grew a fertile woman". That assertion
    could not fail and was removed rather than repaired. It sat behind an
    equality that pins `observed` to a constant, so it reduced to a
    comparison of two module constants with no production input left in it;
    and measured with that shadow lifted, against the exact regression its
    message names -- the preloads hoisted above the empty-candidate return --
    it stayed green, because the inflated count is still below the other
    term. The equality catches that regression on its own, which the same
    measurement confirmed.
    """
    sim, zone = _simulation("nocandidates")
    for i in range(5):
        _agent(sim, zone, f"Vecchio{i}", age=70)

    assert _count_queries(sim, sim.current_tick + 1) == FIXED_TERM_NO_CANDIDATES


class _ForcedBirths:
    """A fertility stream that forces exactly `count` births, then stops.

    Each birth consumes two draws: one below the probability to conceive and
    one above the maternal-mortality rate so the mother survives. After the
    scripted pairs the stream returns 1.0, which is above every per-tick birth
    probability the Hadwiger schedule can produce.
    """

    def __init__(self, count):
        self._draws = [0.0, 1.0] * count

    def random(self):
        return self._draws.pop(0) if self._draws else 1.0

    def gauss(self, mu, sigma):
        return mu

    def randrange(self, n):
        return 0


@pytest.mark.django_db
def test_the_count_does_not_grow_with_the_number_of_births(monkeypatch):
    """FR-016a on the one event type it grants no term at all.

    The budget is `a + b*deaths + c*intents + d*flights`, and births are
    deliberately absent from it: the requirement states that they cost a
    number of queries independent of their number, because the newborns and
    their events are written in bulk and `apply_inheritance_at_birth` saves
    nothing by contract. The sentence it ends on is the criterion -- "one
    query per birth makes the cost measurement fail" -- so the assertion is
    equality, not a bound.

    No other fixture in this file has a single birth, so this cost went
    unmeasured while every guard above stayed green: measured before this
    test existed, four births cost nine queries more than one.
    """
    from epocha.apps.demography import orchestrator

    def _count_with_births(label, births):
        sim, zone = _simulation(label)
        _couples(sim, zone, 6, label.upper()[:2])
        real_stream_for = orchestrator.stream_for
        monkeypatch.setattr(
            orchestrator,
            "stream_for",
            lambda simulation, tick, phase: (
                _ForcedBirths(births)
                if phase == "fertility"
                else real_stream_for(simulation, tick, phase)
            ),
        )
        tick = sim.current_tick + 1
        observed = _count_queries(sim, tick)
        born = Agent.objects.filter(simulation=sim, birth_tick=tick).count()
        monkeypatch.undo()
        return observed, born

    one, born_one = _count_with_births("birthsone", 1)
    four, born_four = _count_with_births("birthsfour", 4)

    assert born_one == 1 and born_four == 4, (
        f"the scripted stream produced {born_one} and {born_four} births, not "
        "1 and 4: the fixture is not measuring what it claims"
    )
    assert one == four, (
        f"{one} queries for one birth and {four} for four: the block is "
        "issuing queries per birth, which FR-016a forbids by granting births "
        "no term of their own"
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
    bound = FIXED_TERM_NO_CANDIDATES + DEATH_TICK_ONCE + PER_DEATH * deaths
    assert observed <= bound, (
        f"{observed} queries for {deaths} deaths exceeds the declared bound "
        f"{FIXED_TERM_NO_CANDIDATES} + {DEATH_TICK_ONCE} + {PER_DEATH} x "
        f"{deaths} = {bound}"
    )
    # The bound has to be reached, not merely respected: a generous bound is
    # satisfied by any implementation and proves nothing. The measured slope
    # is 10 against a declared worst case of 12, so the slack is exactly two
    # queries per death and is pinned as such: a bound allowed to drift
    # upward stops measuring anything.
    assert observed >= bound - 2 * deaths, (
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
#
# Both include the block's one-query self-repair: it reads the living agents
# that still carry a NULL `birth_tick` and returns on the empty result, which
# is every tick of an initialized simulation. That query buys the guarantee
# that the population the steps see can age at all, and it is a fixed cost --
# it does not grow with the population, which is what FR-016 forbids.
#
# The candidate term also carries the single `in_bulk` that loads the
# candidates' partners, which is what lets a birth cost no query of its own:
# one read for any number of candidates, and none at all when none of them is
# partnered.
# Re-pinned on the measure after the phase-6 closure review, never by
# raising a threshold to let a red through. The remediation moved this
# DOWN by one: the starvation counter gained one read of the active
# couples for its household derivation, and the tick duration stopped
# being resolved with a query of its own in each of three steps, which
# is what `DemographyTickContext` existed for.
FIXED_TERM_NO_CANDIDATES = 35
FIXED_TERM_WITH_CANDIDATES = 43

# What a tick pays once for having any death at all, whatever their number:
# the mortality step's own writes -- the marking and the event batch -- and
# the transactional boundary around them, which shows up in a query count as
# the savepoint pair it is. The slope is an exactly linear 10 per death on an
# intercept that is this term on top of FIXED_TERM_NO_CANDIDATES above. The
# measurements are deliberately not reproduced here as literals: they were,
# and they went stale the moment that fixed term moved by one for the block's
# per-tick self-repair read. The bound tests above measure them instead, at
# two death counts, which is what keeps the slope honest without pinning a
# literal that no assertion reads.
#
# It is a conditional FIXED term, not a per-event one, and it is declared
# separately rather than folded into the per-death coefficient because
# folding it there is what made the bound unreachable at four deaths while
# binding at two -- one number describing two different things again.
# Re-pinned on the measure after the phase-6 closure review: resolving the
# tick duration once per context instead of once per step removed one
# query from this path too. Measured 60 queries at two deaths and 80 at
# four, so the slope is 10 and the intercept 40 = 35 + 5.
DEATH_TICK_ONCE = 5

# The worst case the inheritance module documents for a single death (seven
# queries for the heir ladder) plus the settlement writes its batch performs
# around them. Declared at 12 against a measured slope of 10, because the
# per-death cost varies with the deceased's family structure and the module's
# own docstring says so: the bound is an upper bound at worst-case
# coefficients, never an equality.
PER_DEATH = 12

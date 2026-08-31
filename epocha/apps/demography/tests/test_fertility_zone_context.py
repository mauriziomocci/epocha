"""The fertility step's per-candidate query cost, and the proof it changed nothing.

The phase-6 code gate measured seven queries for every living fertile woman
inside `run_fertility_step`: `is_in_active_couple`, the `AgentFertilityState`
resolution, and -- inside `becker_modulation` -- the subsistence threshold,
the female employment fraction and the two aggregate-outlook reads. Six of the
seven ask a question whose answer is the same for every candidate in the zone,
and the seventh is a reverse one-to-one the candidate queryset can carry.

That is an N+1 against FR-016, which forbids any query per living agent. The
remedy has to be provable in two directions at once, and both are asserted
here:

**It removes the queries.** With the per-zone context injected, resolving one
candidate costs zero queries. Asserting the count on a single call is what
makes a future reintroduction visible; the block-level budget in
`test_demography_cost.py` measures the same property from outside.

**It changes no result.** Every candidate's probability computed through the
injected context must equal, exactly, the value the uncached path produces.
Not "close": the injected values are the same numbers read by the same
formula, so any difference at all is a defect, and comparing with a tolerance
would hide precisely the class of error worth catching.

The fixture makes `Agent.age` and `birth_tick` disagree on purpose. A fixture
where they agree cannot say which of the two sources the code reads, and this
work item has already been caught by that three times: `age` is written once
at world generation and never advances, `birth_tick` is the only source that
does, so every woman here carries an `age` column that would put her outside
the fertile window while her `birth_tick` puts her inside it.
"""

from __future__ import annotations

import pytest
from django.contrib.gis.geos import Point, Polygon
from django.db import connection
from django.test.utils import CaptureQueriesContext

from epocha.apps.agents.models import Agent
from epocha.apps.demography.couple import form_couple, is_in_active_couple
from epocha.apps.demography.fertility import set_avoid_conception_flag, tick_birth_probability
from epocha.apps.demography.template_loader import load_template
from epocha.apps.economy.models import (
    BankingState,
    Currency,
    EconomicLedger,
    GoodCategory,
    ZoneEconomy,
)
from epocha.apps.simulation.models import Simulation
from epocha.apps.users.models import User
from epocha.apps.world.models import Government, World, Zone

TICKS_PER_YEAR = 365.0
TICK = 4000

# Far outside [12, 50]: whatever reads this column instead of `birth_tick`
# produces a zero probability, and the equality assertions below would then
# compare zero against zero and prove nothing -- which is why one of them
# requires a strictly positive probability.
MISLEADING_AGE_COLUMN = 99


def _world():
    user = User.objects.create_user(
        email="zonectx@epocha.dev", username="zonectx", password="pass1234"
    )
    sim = Simulation.objects.create(
        name="ZoneContext",
        seed=7,
        owner=user,
        current_tick=TICK,
        config={"demography_enabled": True},
    )
    world = World.objects.create(simulation=sim, stability_index=0.7)
    # Neither default: compute_aggregate_outlook maps 0.5 to exactly zero, so
    # defaults would make the two outlook reads invisible in the result.
    Government.objects.create(simulation=sim, stability=0.8)
    BankingState.objects.create(
        simulation=sim, confidence_index=0.3, reserve_ratio=0.2, base_interest_rate=0.05
    )
    zone = Zone.objects.create(
        world=world,
        name="ContextZone",
        zone_type="residential",
        boundary=Polygon.from_bbox((0, 0, 100, 100)),
        center=Point(50, 50),
    )
    GoodCategory.objects.create(
        simulation=sim,
        code="grain",
        name="Grain",
        is_essential=True,
        base_price=2.0,
        price_elasticity=0.3,
    )
    ZoneEconomy.objects.create(zone=zone, market_prices={"grain": 3.5})
    return sim, zone


def _woman(sim, zone, name, real_age, **kwargs):
    defaults = dict(
        role="farmer",
        location=Point(50, 50),
        health=1.0,
        wealth=800.0,
        age=MISLEADING_AGE_COLUMN,
        birth_tick=int(TICK - real_age * TICKS_PER_YEAR),
        education_level=0.4,
        social_class="working",
        gender=Agent.Gender.FEMALE,
        mood=0.6,
        personality={},
    )
    defaults.update(kwargs)
    return Agent.objects.create(simulation=sim, name=name, zone=zone, **defaults)


def _man(sim, zone, name, real_age=34, **kwargs):
    return _woman(sim, zone, name, real_age, gender=Agent.Gender.MALE, **kwargs)


def _population(sim, zone):
    """A deliberately uneven population: the cases must not all be alike."""
    partnered = _woman(sim, zone, "Partnered", 27, wealth=1500.0, education_level=0.2, mood=0.9)
    form_couple(_man(sim, zone, "PartnerA"), partnered, formed_at_tick=TICK - 200)

    poor = _woman(sim, zone, "Poor", 33, wealth=1.0, education_level=0.9, mood=0.1)
    form_couple(_man(sim, zone, "PartnerB"), poor, formed_at_tick=TICK - 40)

    avoiding = _woman(sim, zone, "Avoiding", 30, wealth=600.0)
    form_couple(_man(sim, zone, "PartnerC"), avoiding, formed_at_tick=TICK - 90)
    set_avoid_conception_flag(avoiding)
    avoiding.fertility_state.avoid_conception_flag_tick = TICK - 1
    avoiding.fertility_state.save(update_fields=["avoid_conception_flag_tick"])

    single = _woman(sim, zone, "Single", 29, wealth=400.0)

    # One of the four earns a wage this tick, so the female employment
    # fraction is 0.25 rather than zero. Without it the term is zero for the
    # whole fixture, `beta_3 * zone_flp` contributes nothing, and zeroing
    # that field of the bundle is a change no assertion can see -- which is
    # what a mutation found here.
    currency = Currency.objects.create(
        simulation=sim, code="DEN", name="Denarius", symbol="D", total_supply=1000.0
    )
    EconomicLedger.objects.create(
        simulation=sim,
        tick=TICK,
        to_agent=partnered,
        currency=currency,
        total_amount=12.0,
        transaction_type="wage",
    )
    return [partnered, poor, avoiding, single]


def _zone_context_for(sim, zone):
    from epocha.apps.demography.fertility import build_zone_fertility_context

    return build_zone_fertility_context(sim, zone)


def _active_couple_ids(sim):
    from epocha.apps.demography.couple import active_couple_partners

    return active_couple_partners(sim)


@pytest.mark.django_db
def test_the_bundle_holds_exactly_what_the_uncached_helpers_return():
    """The bundle's *contents*, checked against something that is not itself.

    The probability comparison below cannot do this job, and finding that out
    took a mutation: `becker_modulation` builds the same bundle when it is
    given none, so corrupting the builder corrupts both sides of that
    comparison equally and it stays green. It was written believing it
    covered the contents; it covers the plumbing.

    So the two zone quantities are checked against the audited helpers they
    are supposed to carry, and the two outlook terms against the stored
    values with the mapping applied by hand -- the documented one, `[0, 1]`
    onto `[-1, 1]` -- rather than through the helper that implements it.
    """
    from epocha.apps.demography.context import compute_subsistence_threshold
    from epocha.apps.demography.fertility import (
        _female_role_employment_fraction,
        build_zone_fertility_context,
    )

    sim, zone = _world()
    _population(sim, zone)

    bundle = build_zone_fertility_context(sim, zone)

    assert bundle["subsistence"] == compute_subsistence_threshold(sim, zone)
    assert bundle["subsistence"] > 0.0, "the fixture has no priced essential good"
    assert bundle["zone_flp"] == _female_role_employment_fraction(zone, sim)
    assert bundle["zone_flp"] > 0.0, (
        "no woman in the fixture earns a wage: the employment term is zero, "
        "and a zero term is one no assertion can distinguish from a dropped one"
    )
    assert bundle["outlook_terms"] == (
        2.0 * BankingState.objects.get(simulation=sim).confidence_index - 1.0,
        2.0 * Government.objects.get(simulation=sim).stability - 1.0,
    )


@pytest.mark.django_db
def test_the_outlook_terms_read_neutral_when_the_economy_was_never_initialized():
    """The fallback the loader inherited, which nothing exercised before.

    A simulation with no `BankingState` and no `Government` is the state of
    every world whose economy was not initialized. Both terms then read as
    neutral instead of raising, and moving the two lookups out of
    `compute_aggregate_outlook` is only behaviour-preserving if that survives
    the move.
    """
    from epocha.apps.demography.context import load_outlook_terms

    user = User.objects.create_user(email="bare@epocha.dev", username="bare", password="pass1234")
    bare = Simulation.objects.create(name="Bare", seed=1, owner=user, current_tick=TICK)

    assert load_outlook_terms(bare) == (0.0, 0.0)


@pytest.mark.django_db
def test_the_injected_context_reproduces_every_probability_exactly():
    """The remedy must be a pure cost change, asserted value by value.

    This compares the plumbing: the same bundle reaching the formula through
    an argument instead of through five queries. What the bundle *holds* is
    the sibling test above, and the two are needed separately.
    """
    sim, zone = _world()
    women = _population(sim, zone)
    template = load_template("pre_industrial_christian")

    legacy = [
        tick_birth_probability(w, template, len(women), 24.0, 1.0, current_tick=TICK) for w in women
    ]

    zone_context = _zone_context_for(sim, zone)
    couple_ids = _active_couple_ids(sim)
    injected = [
        tick_birth_probability(
            w,
            template,
            len(women),
            24.0,
            1.0,
            current_tick=TICK,
            zone_context=zone_context,
            partnered_agent_ids=couple_ids,
        )
        for w in women
    ]

    assert injected == legacy

    # Without this the equality above is satisfied by four zeros, which any
    # broken implementation also produces.
    assert any(p > 0.0 for p in legacy), (
        "no candidate reached a positive probability: the fixture proves nothing"
    )
    # And the two suppression paths must still suppress, or the fixture is
    # only exercising the arithmetic branch and neither early return is
    # covered by anything.
    by_name = {w.name: p for w, p in zip(women, legacy, strict=True)}
    assert by_name["Single"] == 0.0, "an unpartnered woman conceived under require_couple"
    assert by_name["Avoiding"] == 0.0, "avoid_conception did not suppress the birth"


@pytest.mark.django_db
def test_a_candidate_resolved_through_the_context_costs_no_query():
    """FR-016 at the level where it was violated: the single candidate."""
    sim, zone = _world()
    women = _population(sim, zone)
    template = load_template("pre_industrial_christian")
    mother = women[0]

    zone_context = _zone_context_for(sim, zone)
    couple_ids = _active_couple_ids(sim)
    # Reloaded the way the orchestrator loads its candidates: the reverse
    # one-to-one `avoid_conception` reads has to arrive already selected, or
    # it is the seventh per-candidate query on its own.
    mother = Agent.objects.select_related("fertility_state", "zone", "simulation").get(pk=mother.pk)

    with CaptureQueriesContext(connection) as captured:
        tick_birth_probability(
            mother,
            template,
            len(women),
            24.0,
            1.0,
            current_tick=TICK,
            zone_context=zone_context,
            partnered_agent_ids=couple_ids,
        )
    assert len(captured.captured_queries) == 0, [q["sql"] for q in captured.captured_queries]


@pytest.mark.django_db
def test_a_half_null_couple_keeps_its_surviving_partner_a_member():
    """The one shape where the mapping and the per-agent query can disagree.

    `Couple.agent_a` and `agent_b` are nullable, so an undissolved row can
    carry one live partner and one null. `is_in_active_couple` answers True
    for the survivor -- the `Q(agent_a=agent) | Q(agent_b=agent)` matches on
    the column that is set -- and the mapping that replaced it must agree,
    because `tick_birth_probability` documents the two as interchangeable and
    picks between them on whether the caller supplied one. The survivor is a
    member with no partner, which is exactly what the value `None` says.

    This row IS reachable in production, and the sentence that used to stand
    here said it was not. `dissolve_on_death` does null the FK and write
    `dissolved_at_tick` in the same save, so that path cannot produce it --
    but `agents/admin.py` registers `Agent` with the default `ModelAdmin`,
    so deleting an agent from the Django admin fires `on_delete=SET_NULL` on
    `Couple.agent_a`/`agent_b` without touching `dissolved_at_tick`, which is
    exactly this row and exactly why `SET_NULL` is there. The original
    enumeration looked for `.delete()` calls in the source and the admin path
    is not a call in the source. Corrected after the round-4 phase-6 gate;
    the consequence is substantial, because in that state the survivor now
    conceives under an era that requires a couple, where she was excluded
    before.
    """
    from epocha.apps.demography.couple import active_couple_partners, is_in_active_couple
    from epocha.apps.demography.models import Couple

    sim, zone = _world()
    survivor = _woman(sim, zone, "Superstite", 30)
    Couple.objects.create(
        simulation=sim,
        agent_a=survivor,
        agent_b=None,
        formed_at_tick=TICK - 100,
    )

    partners = active_couple_partners(sim)

    assert is_in_active_couple(survivor) is True
    assert survivor.id in partners, (
        "the surviving half of a half-null couple is a member for "
        "is_in_active_couple and not for the mapping that replaced it"
    )
    assert partners[survivor.id] is None


@pytest.mark.django_db
def test_membership_is_tested_by_key_and_never_by_the_truth_of_the_value():
    """The predicate, not just the mapping that feeds it.

    A half-null couple's survivor is a member whose value is `None`, so
    `mother.id in partnered_agent_ids` and
    `bool(partnered_agent_ids.get(mother.id))` disagree about her -- and only
    about her. Every other fixture in the suite has partners with real ids,
    which are truthy, so the two predicates agree everywhere else and the
    weaker one passes. Measured: swapping the membership test for a
    truthiness test left the whole suite green until this test existed.

    Under an era that requires a couple, she must therefore be allowed to
    conceive: she IS in an active couple, which is what the requirement asks,
    and the fact that her partner's row is gone does not un-couple her.
    """
    from epocha.apps.demography.fertility import tick_birth_probability
    from epocha.apps.demography.models import Couple

    sim, zone = _world()
    survivor = _woman(sim, zone, "Vedova", 28, wealth=1200.0)
    Couple.objects.create(simulation=sim, agent_a=survivor, agent_b=None, formed_at_tick=TICK - 100)

    template = load_template("pre_industrial_christian")
    assert template["fertility"]["require_couple_for_birth"] is True

    probability = tick_birth_probability(
        survivor,
        template,
        1,
        24.0,
        1.0,
        current_tick=TICK,
        zone_context=_zone_context_for(sim, zone),
        partnered_agent_ids=_active_couple_ids(sim),
    )

    assert probability > 0.0, (
        "the surviving half of a half-null couple was refused a birth under an "
        "era that requires a couple: membership is being read as the truth of "
        "the partner id rather than as presence of the key"
    )


@pytest.mark.django_db
def test_the_couple_membership_set_answers_what_the_per_agent_query_answers():
    """One query replacing N has to give the same verdict for each of the N."""
    sim, zone = _world()
    women = _population(sim, zone)
    everyone = list(Agent.objects.filter(simulation=sim).order_by("id"))
    assert len(everyone) > len(women), "the fixture has no unpartnered agents to separate"

    couple_ids = _active_couple_ids(sim)
    for agent in everyone:
        assert (agent.id in couple_ids) == is_in_active_couple(agent), agent.name

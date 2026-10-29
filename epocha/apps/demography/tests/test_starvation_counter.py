"""Tests for the persisted starvation counter (spec FR-011, FR-012, SC-003).

Plan 3's emergency-flight trigger took `consecutive_ticks_under_subsistence`
as an explicit argument because no such field existed in the schema, and left
the obligation in writing. Without that storage the emergency-flight module is dead
code in a live run: with the default empty mapping every agent evaluates to
"does not meet preconditions" and the path never fires.

This module covers the storage itself. The step that maintains it inside the
tick, and its position in the declared order, are covered where the
orchestrator is tested.
"""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model

from epocha.apps.agents.models import Agent
from epocha.apps.simulation.models import Simulation

User = get_user_model()


@pytest.fixture
def simulation(db):
    user = User.objects.create_user(
        email="starvation@epocha.dev",
        username="starvationuser",
        password="pass1234",
    )
    return Simulation.objects.create(
        name="StarvationCounterTest",
        seed=2026,
        owner=user,
        current_tick=10,
    )


def test_new_agent_starts_at_zero(simulation):
    """A fresh agent has never been under subsistence."""
    agent = Agent.objects.create(simulation=simulation, name="Chiara", age=30)

    agent.refresh_from_db()

    assert agent.consecutive_ticks_under_subsistence == 0


def test_counter_persists_across_reload(simulation):
    """The counter has to survive the process: the tick loop is a set of
    Celery tasks and in-memory state does not outlive one of them."""
    agent = Agent.objects.create(simulation=simulation, name="Nicola", age=41)

    Agent.objects.filter(pk=agent.pk).update(consecutive_ticks_under_subsistence=3)

    assert Agent.objects.get(pk=agent.pk).consecutive_ticks_under_subsistence == 3


# ---------------------------------------------------------------------------
# The step that maintains the counter, and the trigger that reads it.
# ---------------------------------------------------------------------------


@pytest.fixture
def sim_with_zone(db):
    """A simulation with the economy scaffolding the subsistence threshold
    needs: without a ZoneEconomy the threshold is zero and nobody starves."""
    from django.contrib.gis.geos import Point, Polygon

    from epocha.apps.economy.models import GoodCategory, ZoneEconomy
    from epocha.apps.world.models import Government, World, Zone

    user = User.objects.create_user(
        email="counterstep@epocha.dev",
        username="counterstepuser",
        password="pass1234",
    )
    sim = Simulation.objects.create(
        name="CounterStepTest",
        seed=2026,
        owner=user,
        current_tick=50,
        config={"demography_enabled": True},
    )
    world = World.objects.create(simulation=sim, stability_index=0.7)
    # The flight path reads government stability into its zone statistics.
    Government.objects.create(simulation=sim)
    zone = Zone.objects.create(
        world=world,
        name="CounterZone",
        zone_type="residential",
        boundary=Polygon.from_bbox((0, 0, 100, 100)),
        center=Point(50, 50),
    )
    good = GoodCategory.objects.create(
        simulation=sim,
        code="grain",
        name="Grain",
        base_price=10.0,
        is_essential=True,
        price_elasticity=0.3,
    )
    ZoneEconomy.objects.create(zone=zone, market_prices={good.code: 10.0})
    return sim, zone


def _agent(sim, zone, name, wealth, **kwargs):
    from django.contrib.gis.geos import Point

    defaults = dict(
        role="farmer",
        location=Point(50, 50),
        health=1.0,
        wealth=wealth,
        age=40,
        birth_tick=int(sim.current_tick - 40 * 365),
        education_level=0.5,
        social_class="working",
        gender=Agent.Gender.MALE,
        personality={},
    )
    defaults.update(kwargs)
    return Agent.objects.create(simulation=sim, name=name, zone=zone, **defaults)


def _context(sim):
    from epocha.apps.demography import orchestrator
    from epocha.apps.demography.template_loader import load_template

    return orchestrator.DemographyTickContext(
        simulation=sim,
        tick=sim.current_tick + 1,
        template=load_template("pre_industrial_christian"),
    )


class TestCounterStep:
    def test_it_increments_below_the_subsistence_threshold(self, sim_with_zone):
        from epocha.apps.demography import orchestrator

        sim, zone = sim_with_zone
        starving = _agent(sim, zone, "Affamato", wealth=0.0)

        orchestrator.run_starvation_counter_step(_context(sim))

        starving.refresh_from_db()
        assert starving.consecutive_ticks_under_subsistence == 1

    def test_it_resets_when_wealth_rises_above_the_line(self, sim_with_zone):
        from epocha.apps.demography import orchestrator

        sim, zone = sim_with_zone
        recovered = _agent(
            sim, zone, "Ripreso", wealth=10_000.0, consecutive_ticks_under_subsistence=7
        )

        orchestrator.run_starvation_counter_step(_context(sim))

        recovered.refresh_from_db()
        assert recovered.consecutive_ticks_under_subsistence == 0

    def test_it_accumulates_across_ticks(self, sim_with_zone):
        from epocha.apps.demography import orchestrator

        sim, zone = sim_with_zone
        starving = _agent(sim, zone, "Affamato", wealth=0.0)
        context = _context(sim)

        orchestrator.run_starvation_counter_step(context)
        orchestrator.run_starvation_counter_step(context)
        orchestrator.run_starvation_counter_step(context)

        starving.refresh_from_db()
        assert starving.consecutive_ticks_under_subsistence == 3

    def test_the_dead_are_not_counted(self, sim_with_zone):
        from epocha.apps.demography import orchestrator

        sim, zone = sim_with_zone
        dead = _agent(sim, zone, "Morto", wealth=0.0, is_alive=False, death_tick=40)

        orchestrator.run_starvation_counter_step(_context(sim))

        dead.refresh_from_db()
        assert dead.consecutive_ticks_under_subsistence == 0

    def test_the_predicate_is_the_one_the_flight_trigger_uses(self, sim_with_zone):
        """FR-011: counter and trigger must share the predicate, or they
        diverge in silence and the flight fires on a count nobody can trace.

        Measured against the trigger's own condition rather than restated:
        the agent sits just below the threshold the trigger computes, so an
        implementation using any other line disagrees here.
        """
        from epocha.apps.demography import orchestrator
        from epocha.apps.demography.context import compute_subsistence_threshold

        sim, zone = sim_with_zone
        threshold = compute_subsistence_threshold(sim, zone)
        assert threshold > 0.0, "fixture must produce a real threshold"

        just_below = _agent(sim, zone, "AppenaSotto", wealth=threshold - 0.01)
        just_above = _agent(sim, zone, "AppenaSopra", wealth=threshold + 0.01)

        orchestrator.run_starvation_counter_step(_context(sim))

        just_below.refresh_from_db()
        just_above.refresh_from_db()
        assert just_below.consecutive_ticks_under_subsistence == 1
        assert just_above.consecutive_ticks_under_subsistence == 0


class TestTheCounterIsAHouseholdProperty:
    """A dependent minor is not a starving household of one.

    Found by the closure review over the whole branch diff, and ratified as a
    model decision before being changed. The counter used to compare an
    agent's OWN wealth against the threshold, and `apply_inheritance_at_birth`
    writes `child.wealth = 0.0` on every newborn: so every child in the world
    entered permanently below the line and, after `flight_trigger_ticks` --
    thirty ticks under the default era, FIVE under `sci_fi` -- satisfied the
    first two conditions of emergency flight. Since mass flight fires above
    30% of a zone's reference population, the infant cohort alone was enough
    to trigger it.

    The subsistence question is a household question: the household's wealth
    against the sum of its members' thresholds. The derivation is the one the
    snapshot already had -- partners share a household, a minor belongs to
    its living parent's -- now shared rather than copied, because a second
    copy of a quantity is the defect this branch was carrying in four places.
    """

    def test_a_minor_in_a_solvent_household_does_not_starve(self, sim_with_zone):
        from epocha.apps.demography import orchestrator
        from epocha.apps.demography.context import compute_subsistence_threshold

        sim, zone = sim_with_zone
        threshold = compute_subsistence_threshold(sim, zone)
        parent = _agent(sim, zone, "Genitore", wealth=threshold * 10)
        child = _agent(
            sim,
            zone,
            "Figlio",
            wealth=0.0,
            age=2,
            birth_tick=int(sim.current_tick - 2 * 365),
            parent_agent=parent,
        )

        orchestrator.run_starvation_counter_step(_context(sim))

        child.refresh_from_db()
        parent.refresh_from_db()
        assert parent.consecutive_ticks_under_subsistence == 0
        assert child.consecutive_ticks_under_subsistence == 0, (
            "a child with no wealth of its own was counted as a starving "
            "household: every newborn in the world becomes a famine migrant"
        )

    def test_a_minor_in_an_insolvent_household_does_starve(self, sim_with_zone):
        """The other side, so the fix is not a blanket exemption for minors."""
        from epocha.apps.demography import orchestrator
        from epocha.apps.demography.context import compute_subsistence_threshold

        sim, zone = sim_with_zone
        threshold = compute_subsistence_threshold(sim, zone)
        parent = _agent(sim, zone, "GenitorePovero", wealth=threshold * 0.2)
        child = _agent(
            sim,
            zone,
            "FiglioPovero",
            wealth=0.0,
            age=2,
            birth_tick=int(sim.current_tick - 2 * 365),
            parent_agent=parent,
        )

        orchestrator.run_starvation_counter_step(_context(sim))

        child.refresh_from_db()
        parent.refresh_from_db()
        assert parent.consecutive_ticks_under_subsistence == 1
        assert child.consecutive_ticks_under_subsistence == 1, (
            "the household is below the line and the minor was not counted"
        )


class TestTheHouseholdKnowsBothParents:
    """A minor is anchored through whichever parent is alive, not only the first.

    Found by round 8, and it is the same signature the branch keeps
    producing: `inheritance.py` resolves "child of" through
    `Q(parent_agent=x) | Q(other_parent_agent=x)` -- both foreign keys --
    while the household derivation read one. So the household fix closed the
    starvation defect for the children of living mothers and left it open for
    everybody else, including the one population the fertility path creates
    on purpose: the newborn of a mother who dies bearing it.

    Measured before the fix: each of the three cases below left the minor at
    counter 1 with a solvent adult standing right next to it.
    """

    def test_a_minor_whose_mother_died_is_anchored_to_the_living_father(self, sim_with_zone):
        from epocha.apps.demography import orchestrator
        from epocha.apps.demography.context import compute_subsistence_threshold

        sim, zone = sim_with_zone
        threshold = compute_subsistence_threshold(sim, zone)
        father = _agent(sim, zone, "PadreVivo", wealth=threshold * 50)
        dead_mother = _agent(sim, zone, "MadreMorta", wealth=0.0)
        Agent.objects.filter(pk=dead_mother.pk).update(is_alive=False)
        orphan = _agent(
            sim,
            zone,
            "Orfano",
            wealth=0.0,
            age=3,
            birth_tick=int(sim.current_tick - 3 * 365),
            parent_agent=dead_mother,
            other_parent_agent=father,
        )

        orchestrator.run_starvation_counter_step(_context(sim))

        orphan.refresh_from_db()
        assert orphan.consecutive_ticks_under_subsistence == 0, (
            "the minor was anchored to its dead mother and became a starving "
            "household of one while its solvent father stood next to it"
        )

    def test_a_minor_in_care_is_anchored_to_its_caretaker(self, sim_with_zone):
        """Both parents dead, a caretaker assigned: the ward is a dependent.

        `assign_orphan_caretaker` exists precisely to place these children,
        and the derivation's own docstring says a household is a couple with
        the minors IN ITS CARE.
        """
        from epocha.apps.demography import orchestrator
        from epocha.apps.demography.context import compute_subsistence_threshold

        sim, zone = sim_with_zone
        threshold = compute_subsistence_threshold(sim, zone)
        guardian = _agent(sim, zone, "Tutore", wealth=threshold * 50)
        ward = _agent(
            sim,
            zone,
            "Pupillo",
            wealth=0.0,
            age=4,
            birth_tick=int(sim.current_tick - 4 * 365),
            caretaker_agent=guardian,
        )

        orchestrator.run_starvation_counter_step(_context(sim))

        ward.refresh_from_db()
        assert ward.consecutive_ticks_under_subsistence == 0, (
            "a ward with an assigned caretaker was counted as its own starving household"
        )

    def test_the_anchor_is_transitive_through_a_minor_parent(self, sim_with_zone):
        """The child of a minor mother belongs to the grandparent's household.

        The fertile window opens at twelve and adulthood is sixteen or
        eighteen depending on the era, so a four-to-six-year band of mothers
        is itself anchored to a parent. Without transitivity the newborn is a
        household of one and the grandparent's solvency never reaches it.
        """
        from epocha.apps.demography import orchestrator
        from epocha.apps.demography.context import compute_subsistence_threshold

        sim, zone = sim_with_zone
        threshold = compute_subsistence_threshold(sim, zone)
        grandparent = _agent(sim, zone, "Nonno", wealth=threshold * 50)
        young_mother = _agent(
            sim,
            zone,
            "MadreMinorenne",
            wealth=0.0,
            age=14,
            birth_tick=int(sim.current_tick - 14 * 365),
            parent_agent=grandparent,
        )
        baby = _agent(
            sim,
            zone,
            "Nipote",
            wealth=0.0,
            age=0,
            birth_tick=sim.current_tick,
            parent_agent=young_mother,
        )

        orchestrator.run_starvation_counter_step(_context(sim))

        baby.refresh_from_db()
        young_mother.refresh_from_db()
        assert young_mother.consecutive_ticks_under_subsistence == 0
        assert baby.consecutive_ticks_under_subsistence == 0, (
            "the anchor did not follow the minor mother up to the solvent "
            "grandparent: the household derivation is not transitive"
        )


class TestMarriageOutranksTheGuardianChain:
    """A married minor belongs to her marital household, not her parent's.

    Found by round 9. `_anchor` walked the guardian chain unconditionally, so
    a minor who was ALSO in an active couple was pulled into her parent's
    household while her husband's key still named her: her wealth counted in
    one household and her membership claimed by another. Measured, one year
    of age flipped the verdict on the same population -- at fourteen she was
    starving next to a husband holding ten thousand, at seventeen she was not.

    Reachable, and not a curiosity. When this was found the era's minimum
    marriage age gated only the founding matcher; it now gates the intent
    path as well (`couple.meets_marriage_age`), and the state remains legal:
    the pre-industrial eras set the female threshold at 14 against an
    adulthood age of 16, so a married fourteen-year-old is a minor there.

    The precedence -- marriage wins -- is a model decision taken here rather
    than left implicit: a couple IS a household, which is the first sentence
    of the derivation's own docstring, and a person cannot be a dependent of
    two households at once.
    """

    def test_a_married_minor_is_in_her_own_household_not_her_parents(self, sim_with_zone):
        from epocha.apps.demography import orchestrator
        from epocha.apps.demography.context import compute_subsistence_threshold
        from epocha.apps.demography.couple import form_couple

        sim, zone = sim_with_zone
        threshold = compute_subsistence_threshold(sim, zone)
        grandparent = _agent(sim, zone, "NonnoPovero", wealth=0.0)
        wife = _agent(
            sim,
            zone,
            "MoglieMinorenne",
            wealth=0.0,
            age=14,
            birth_tick=int(sim.current_tick - 14 * 365),
            parent_agent=grandparent,
            gender=Agent.Gender.FEMALE,
        )
        husband = _agent(sim, zone, "Marito", wealth=threshold * 100)
        form_couple(wife, husband, formed_at_tick=sim.current_tick - 1)

        orchestrator.run_starvation_counter_step(_context(sim))

        wife.refresh_from_db()
        husband.refresh_from_db()
        assert husband.consecutive_ticks_under_subsistence == 0
        assert wife.consecutive_ticks_under_subsistence == 0, (
            "the married minor was anchored to her destitute parent while her "
            "husband's household still claimed her: she is a dependent of two "
            "households at once"
        )


class TestFlightReadsThePersistedCounter:
    def test_flight_fires_from_the_stored_counter_alone(self, sim_with_zone):
        """FR-012: `process_emergency_flight` reads the column instead of
        receiving a mapping, which is what makes the path reachable in a
        live run rather than only in unit tests."""
        from epocha.apps.demography.migration import process_emergency_flight
        from epocha.apps.demography.models import DemographyEvent
        from epocha.apps.demography.template_loader import load_template

        sim, zone = sim_with_zone
        trigger_ticks = load_template("pre_industrial_christian")["migration"][
            "flight_trigger_ticks"
        ]
        _agent(
            sim,
            zone,
            "Disperato",
            wealth=0.0,
            consecutive_ticks_under_subsistence=trigger_ticks + 1,
        )

        process_emergency_flight(sim, sim.current_tick + 1)

        assert DemographyEvent.objects.filter(
            simulation=sim,
            event_type__in=[
                DemographyEvent.EventType.MIGRATION,
                DemographyEvent.EventType.TRAPPED_CRISIS,
            ],
        ).exists()

    def test_a_short_counter_fires_nothing(self, sim_with_zone):
        from epocha.apps.demography.migration import process_emergency_flight
        from epocha.apps.demography.models import DemographyEvent

        sim, zone = sim_with_zone
        _agent(sim, zone, "Paziente", wealth=0.0, consecutive_ticks_under_subsistence=1)

        process_emergency_flight(sim, sim.current_tick + 1)

        assert not DemographyEvent.objects.filter(simulation=sim).exists()


def _of_age(sim, years):
    """The `age` and `birth_tick` pair for an agent `years` old by the
    canonical age, at the fixture's daily ticks."""
    return {"age": years, "birth_tick": int(sim.current_tick - years * 365)}


class TestTheStateFeedsItsWards:
    """A minor with no living guardian is the state's ward, and the state is
    the implicit caretaker (design spec 2026-04-18, `caretaker_agent`): it
    feeds the ward, so the ward's subsistence need does not fall on the
    ward's own empty purse.

    Found by round 11 of the phase-6 gate (R4): `assign_orphan_caretaker`
    flags `"state_ward"` and nothing read the flag, so an eight-year-old
    with nothing to her name was a starving household of one, decided for
    herself, and fled alone. The rule is decided by the Trinity (variant b):
    the need counts zero while the flag is set, the member is a minor by the
    era's `migration.adulthood_age`, and the household is the ward alone. No
    treasury is debited; that limit is declared in whitepaper §4.1.0.
    """

    def test_a_state_ward_never_starves_nor_flees_alone(self, sim_with_zone):
        from epocha.apps.demography import orchestrator
        from epocha.apps.demography.migration import process_emergency_flight
        from epocha.apps.demography.models import DemographyEvent

        sim, zone = sim_with_zone
        ward = _agent(
            sim, zone, "Pupilla", wealth=0.0, conditions=["state_ward"], **_of_age(sim, 8)
        )

        orchestrator.run_starvation_counter_step(_context(sim))

        ward.refresh_from_db()
        assert ward.consecutive_ticks_under_subsistence == 0

        # Past the trigger by hand, as if a counter had run wild: the flight
        # path asks condition 1 through the same predicate, so neither a
        # flight nor a trapped crisis may follow.
        Agent.objects.filter(pk=ward.pk).update(consecutive_ticks_under_subsistence=30)
        process_emergency_flight(sim, sim.current_tick + 1)

        assert not DemographyEvent.objects.filter(simulation=sim).exists()

    def test_a_former_ward_who_came_of_age_starves_like_anyone(self, sim_with_zone):
        """The flag is never cleared, so the age test is what ends wardship."""
        from epocha.apps.demography import orchestrator

        sim, zone = sim_with_zone
        grown = _agent(
            sim, zone, "ExPupillo", wealth=0.0, conditions=["state_ward"], **_of_age(sim, 20)
        )

        orchestrator.run_starvation_counter_step(_context(sim))

        grown.refresh_from_db()
        assert grown.consecutive_ticks_under_subsistence == 1

    def test_wardship_ends_on_the_day_of_adulthood(self, sim_with_zone):
        """A minor is younger than `adulthood_age`; on the birthday itself
        the ward is an adult, like `household_keys` reads her."""
        from epocha.apps.demography import orchestrator

        sim, zone = sim_with_zone
        context = _context(sim)
        adulthood_age = context.template["migration"]["adulthood_age"]
        # Daily ticks make a year exactly 365 of them (`HOURS_PER_YEAR`
        # 8760), so this birth tick lands the age on the threshold itself.
        birthday = _agent(
            sim,
            zone,
            "Maggiorenne",
            wealth=0.0,
            conditions=["state_ward"],
            age=adulthood_age,
            birth_tick=int(context.tick - adulthood_age * 365),
        )

        orchestrator.run_starvation_counter_step(context)

        birthday.refresh_from_db()
        assert birthday.consecutive_ticks_under_subsistence == 1

    def test_a_lone_ward_in_debt_still_starves(self, sim_with_zone):
        """The declared limit of the state's care: it zeroes the ward's
        need, never her wealth, so a debt is not covered and a lone ward
        whose wealth is negative is below a need of zero. Round 13 of the
        phase-6 gate (N-a): a mutation that drops the ward's wealth with her
        need survived every test of this file."""
        from epocha.apps.demography import orchestrator

        sim, zone = sim_with_zone
        indebted = _agent(
            sim, zone, "Indebitata", wealth=-5.0, conditions=["state_ward"], **_of_age(sim, 8)
        )

        orchestrator.run_starvation_counter_step(_context(sim))

        indebted.refresh_from_db()
        assert indebted.consecutive_ticks_under_subsistence == 1

    def test_an_unflagged_minor_alone_is_not_covered(self, sim_with_zone):
        """The declared limit: the state feeds the wards it knows of. A minor
        with no living guardian and no flag -- a founder generated young, or
        a child whose guardian left the zoned population -- starves as a
        household of one."""
        from epocha.apps.demography import orchestrator

        sim, zone = sim_with_zone
        alone = _agent(sim, zone, "Solo", wealth=0.0, **_of_age(sim, 8))

        orchestrator.run_starvation_counter_step(_context(sim))

        alone.refresh_from_db()
        assert alone.consecutive_ticks_under_subsistence == 1

    def test_a_married_ward_eats_from_her_couple(self, sim_with_zone):
        """Marriage makes a household, and the household feeds its members:
        the state's care is for the ward alone. The husband's purse covers
        one threshold and a half, short of the two the couple needs."""
        from epocha.apps.demography import orchestrator
        from epocha.apps.demography.context import compute_subsistence_threshold
        from epocha.apps.demography.couple import form_couple

        sim, zone = sim_with_zone
        threshold = compute_subsistence_threshold(sim, zone)
        bride = _agent(
            sim,
            zone,
            "Sposa",
            wealth=0.0,
            conditions=["state_ward"],
            gender=Agent.Gender.FEMALE,
            **_of_age(sim, 15),
        )
        husband = _agent(sim, zone, "Marito", wealth=threshold * 1.5, **_of_age(sim, 20))
        form_couple(bride, husband, formed_at_tick=1)

        orchestrator.run_starvation_counter_step(_context(sim))

        for member in (bride, husband):
            member.refresh_from_db()
            assert member.consecutive_ticks_under_subsistence == 1, member.name

    def test_a_ward_mother_feeds_her_child_from_her_own_purse(self, sim_with_zone):
        """The state's care covers the ward's NEED, never her wealth, and only
        while she is alone: a ward with a child of her own heads a household
        of two, which eats from what its members own.

        Found by round 12 of the phase-6 gate (F1): the branch tested "anchor
        without a partner" instead of "alone in the household" and dropped
        the ward from the tally altogether, wealth included. A fifteen-year-old
        ward with ten thresholds to her name and a six-month-old child with
        nothing were then a household of the child alone, starving, and both
        counters rose to a trapped crisis."""
        from epocha.apps.demography import orchestrator
        from epocha.apps.demography.context import compute_subsistence_threshold
        from epocha.apps.demography.migration import process_emergency_flight
        from epocha.apps.demography.models import DemographyEvent

        sim, zone = sim_with_zone
        threshold = compute_subsistence_threshold(sim, zone)
        mother = _agent(
            sim,
            zone,
            "PupillaMadre",
            wealth=threshold * 10,
            conditions=["state_ward"],
            gender=Agent.Gender.FEMALE,
            **_of_age(sim, 15),
        )
        child = _agent(
            sim,
            zone,
            "Neonato",
            wealth=0.0,
            parent_agent=mother,
            age=0,
            birth_tick=int(sim.current_tick - 182),
        )

        orchestrator.run_starvation_counter_step(_context(sim))

        for member in (mother, child):
            member.refresh_from_db()
            assert member.consecutive_ticks_under_subsistence == 0, member.name

        # Past the trigger by hand: condition 1 of the flight path asks the
        # same predicate, so the household is fed and nothing may follow.
        Agent.objects.filter(pk__in=[mother.pk, child.pk]).update(
            consecutive_ticks_under_subsistence=30
        )
        process_emergency_flight(sim, sim.current_tick + 1)

        assert not DemographyEvent.objects.filter(simulation=sim).exists()

    def test_a_ward_mother_who_covers_one_threshold_and_a_half_starves(self, sim_with_zone):
        """The other side of the same rule: in a household of two the ward's
        need counts like anyone's. Her purse covers one threshold and a half,
        enough for the child alone and short of the two the household needs,
        so zeroing her need outside a household of one would feed them."""
        from epocha.apps.demography import orchestrator
        from epocha.apps.demography.context import compute_subsistence_threshold

        sim, zone = sim_with_zone
        threshold = compute_subsistence_threshold(sim, zone)
        mother = _agent(
            sim,
            zone,
            "PupillaPovera",
            wealth=threshold * 1.5,
            conditions=["state_ward"],
            gender=Agent.Gender.FEMALE,
            **_of_age(sim, 15),
        )
        child = _agent(
            sim,
            zone,
            "Neonata",
            wealth=0.0,
            parent_agent=mother,
            age=0,
            birth_tick=int(sim.current_tick - 182),
        )

        orchestrator.run_starvation_counter_step(_context(sim))

        for member in (mother, child):
            member.refresh_from_db()
            assert member.consecutive_ticks_under_subsistence == 1, member.name


class TestOneHouseholdOneCounter:
    """The members of one household carry one counter.

    The counter used to add the household's verdict to each person's OWN
    previous value, so whoever joined a starving household -- a spouse at
    marriage, a newborn, a minor anchored anew -- arrived at a count of
    their own and the household's members disagreed on how long it had been
    starving (phase-6 gate rows 20 and 33). Within ratified decision B1, a
    starving household now continues from the longest count among its
    members, and writes the same value to all of them; a fed household
    resets every member to zero.
    """

    def test_a_marriage_continues_from_the_longer_count(self, sim_with_zone):
        from epocha.apps.demography import orchestrator
        from epocha.apps.demography.couple import form_couple

        sim, zone = sim_with_zone
        long_hungry = _agent(sim, zone, "Lungo", wealth=0.0, consecutive_ticks_under_subsistence=29)
        newly_wed = _agent(
            sim,
            zone,
            "Sposa",
            wealth=0.0,
            gender=Agent.Gender.FEMALE,
            consecutive_ticks_under_subsistence=0,
        )
        form_couple(long_hungry, newly_wed, formed_at_tick=sim.current_tick)

        orchestrator.run_starvation_counter_step(_context(sim))

        for member in (long_hungry, newly_wed):
            member.refresh_from_db()
            assert member.consecutive_ticks_under_subsistence == 30, member.name

    def test_a_newborn_joins_the_count_of_its_household(self, sim_with_zone):
        from epocha.apps.demography import orchestrator

        sim, zone = sim_with_zone
        mother = _agent(
            sim,
            zone,
            "Madre",
            wealth=0.0,
            gender=Agent.Gender.FEMALE,
            consecutive_ticks_under_subsistence=10,
        )
        newborn = _agent(sim, zone, "Neonato", wealth=0.0, parent_agent=mother, **_of_age(sim, 0))

        orchestrator.run_starvation_counter_step(_context(sim))

        for member in (mother, newborn):
            member.refresh_from_db()
            assert member.consecutive_ticks_under_subsistence == 11, member.name

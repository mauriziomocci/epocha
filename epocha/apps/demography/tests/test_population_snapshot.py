"""Tests for the per-tick PopulationSnapshot writer.

Plan 1 modelled `PopulationSnapshot` and no production code ever wrote one, so
the aggregate demographic state of a run existed only as whatever a reader
could reconstruct by hand from the agent table. Historical validation is not
executable without it, which is why the writer belongs to this work item even
though the validation campaign does not.

Every field is asserted against a value computed by hand from a fixture that
carries at least one birth, one death, one zone move, an unbalanced sex ratio
and an active couple -- because six of the ten fields have a model default
that a fixture without those events would reproduce exactly, letting an
implementation that computes nothing pass.
"""

from __future__ import annotations

import pytest
from django.contrib.gis.geos import Point, Polygon

from epocha.apps.agents.models import Agent
from epocha.apps.demography import orchestrator, snapshot
from epocha.apps.demography.couple import form_couple
from epocha.apps.demography.models import Couple, DemographyEvent, PopulationSnapshot
from epocha.apps.demography.template_loader import load_template
from epocha.apps.simulation.models import Simulation
from epocha.apps.users.models import User
from epocha.apps.world.models import Government, World, Zone

TICKS_PER_YEAR = 365.0


@pytest.fixture
def sim_with_zones(db):
    user = User.objects.create_user(
        email="snap@epocha.dev", username="snapuser", password="pass1234"
    )
    sim = Simulation.objects.create(
        name="SnapshotTest",
        seed=2026,
        owner=user,
        current_tick=50,
        config={"demography_enabled": True},
    )
    world = World.objects.create(simulation=sim, stability_index=0.7)
    Government.objects.create(simulation=sim)
    home = Zone.objects.create(
        world=world,
        name="Home",
        zone_type="residential",
        boundary=Polygon.from_bbox((0, 0, 100, 100)),
        center=Point(50, 50),
    )
    away = Zone.objects.create(
        world=world,
        name="Away",
        zone_type="residential",
        boundary=Polygon.from_bbox((200, 200, 300, 300)),
        center=Point(250, 250),
    )
    return sim, home, away


def _agent(sim, zone, name, age, gender=Agent.Gender.MALE, **kwargs):
    defaults = dict(
        role="farmer",
        location=Point(50, 50),
        health=1.0,
        wealth=100.0,
        age=age,
        birth_tick=int(sim.current_tick - age * TICKS_PER_YEAR),
        education_level=0.5,
        social_class="working",
        gender=gender,
        personality={},
    )
    defaults.update(kwargs)
    return Agent.objects.create(simulation=sim, name=name, zone=zone, **defaults)


@pytest.fixture
def populated_tick(sim_with_zones):
    """A tick with every kind of event the snapshot has to see.

    Deliberately unbalanced: four men and two living women, so `sex_ratio`
    cannot coincide with its 1.0 default; one active couple, so
    `couples_active` cannot coincide with 0; one birth, one death and one
    zone move in this tick, so the three rate fields and the migration map
    cannot coincide with theirs either.
    """
    sim, home, away = sim_with_zones
    tick = sim.current_tick + 1

    man = _agent(sim, home, "Uomo", age=40)
    woman = _agent(sim, home, "Donna", age=30, gender=Agent.Gender.FEMALE)
    _agent(sim, home, "Altro", age=50)
    _agent(sim, home, "Terzo", age=20)
    form_couple(man, woman, formed_at_tick=sim.current_tick - 1)

    newborn = _agent(sim, home, "Neonata", age=0, gender=Agent.Gender.FEMALE)
    newborn.birth_tick = tick
    newborn.save(update_fields=["birth_tick"])
    DemographyEvent.objects.create(
        simulation=sim,
        tick=tick,
        event_type=DemographyEvent.EventType.BIRTH,
        primary_agent=newborn,
        secondary_agent=woman,
        payload={},
    )

    deceased = _agent(sim, home, "Defunto", age=80, is_alive=False, death_tick=tick)
    DemographyEvent.objects.create(
        simulation=sim,
        tick=tick,
        event_type=DemographyEvent.EventType.DEATH,
        primary_agent=deceased,
        payload={},
    )

    mover = _agent(sim, away, "Migrante", age=35)
    DemographyEvent.objects.create(
        simulation=sim,
        tick=tick,
        event_type=DemographyEvent.EventType.MIGRATION,
        primary_agent=mover,
        payload={"from_zone": home.id, "to_zone": away.id},
    )

    return sim, home, away, tick


def _context(sim, tick):
    return orchestrator.DemographyTickContext(
        simulation=sim, tick=tick, template=load_template("pre_industrial_christian")
    )


class TestSnapshotFields:
    """SC-007, field by field against hand-computed values."""

    def test_total_alive(self, populated_tick):
        sim, _, _, tick = populated_tick

        snapshot.write_population_snapshot(_context(sim, tick))

        row = PopulationSnapshot.objects.get(simulation=sim, tick=tick)
        assert row.total_alive == 6  # four adults, the newborn, the mover

    def test_sex_ratio_is_men_over_women(self, populated_tick):
        sim, _, _, tick = populated_tick

        snapshot.write_population_snapshot(_context(sim, tick))

        row = PopulationSnapshot.objects.get(simulation=sim, tick=tick)
        assert row.sex_ratio == pytest.approx(4 / 2)
        assert row.sex_ratio != 1.0  # the model default, which must not pass

    def test_avg_age_is_derived_from_birth_tick(self, populated_tick):
        sim, _, _, tick = populated_tick

        snapshot.write_population_snapshot(_context(sim, tick))

        row = PopulationSnapshot.objects.get(simulation=sim, tick=tick)
        # 40, 30, 50, 20, 35 and the newborn at 0, each measured at `tick`,
        # so every living agent is one tick older than its declared age.
        expected = (40 + 30 + 50 + 20 + 35 + 0) / 6 + 1 / TICKS_PER_YEAR
        assert row.avg_age == pytest.approx(expected, abs=0.01)

    def test_age_pyramid_buckets_the_living_by_sex(self, populated_tick):
        sim, _, _, tick = populated_tick

        snapshot.write_population_snapshot(_context(sim, tick))

        row = PopulationSnapshot.objects.get(simulation=sim, tick=tick)
        counted = sum(bucket[2] + bucket[3] for bucket in row.age_pyramid)
        assert counted == row.total_alive
        newborn_bucket = next(b for b in row.age_pyramid if b[0] == 0)
        assert newborn_bucket[3] == 1  # the newborn girl

    def test_crude_birth_and_death_rates_are_annualised_per_thousand(self, populated_tick):
        sim, _, _, tick = populated_tick

        snapshot.write_population_snapshot(_context(sim, tick))

        row = PopulationSnapshot.objects.get(simulation=sim, tick=tick)
        expected = 1 / 6 * 1000 * TICKS_PER_YEAR
        assert row.crude_birth_rate == pytest.approx(expected, rel=1e-6)
        assert row.crude_death_rate == pytest.approx(expected, rel=1e-6)
        assert row.crude_birth_rate != 0.0
        assert row.crude_death_rate != 0.0

    def test_tfr_instant_sums_the_age_specific_rates(self, populated_tick):
        sim, _, _, tick = populated_tick

        snapshot.write_population_snapshot(_context(sim, tick))

        row = PopulationSnapshot.objects.get(simulation=sim, tick=tick)
        # One birth to the only woman of her age in the fertile window, so
        # that single age contributes 1 / 1 annualised and every other
        # fertile age contributes nothing.
        assert row.tfr_instant == pytest.approx(TICKS_PER_YEAR, rel=1e-6)
        assert row.tfr_instant != 0.0

    def test_net_migration_by_zone_balances(self, populated_tick):
        sim, home, away, tick = populated_tick

        snapshot.write_population_snapshot(_context(sim, tick))

        row = PopulationSnapshot.objects.get(simulation=sim, tick=tick)
        assert row.net_migration_by_zone[str(away.id)] == 1
        assert row.net_migration_by_zone[str(home.id)] == -1
        assert row.net_migration_by_zone != {}

    def test_couples_active(self, populated_tick):
        sim, _, _, tick = populated_tick

        snapshot.write_population_snapshot(_context(sim, tick))

        row = PopulationSnapshot.objects.get(simulation=sim, tick=tick)
        assert row.couples_active == 1
        assert row.couples_active != 0

    def test_avg_household_size(self, populated_tick):
        sim, _, _, tick = populated_tick

        snapshot.write_population_snapshot(_context(sim, tick))

        row = PopulationSnapshot.objects.get(simulation=sim, tick=tick)
        # Six living agents across five households: the couple is one, and
        # the newborn belongs to its mother's, so the four remaining
        # unpartnered adults are one each.
        assert row.avg_household_size == pytest.approx(6 / 5, abs=0.01)
        assert row.avg_household_size != 0.0

    def test_tfr_denominator_counts_every_woman_of_the_mothers_age(self, sim_with_zones):
        """The two ways this rate silently lies, closed with one fixture.

        Two women share the mother's integer age and only one gives birth, so
        the age-specific rate is 1/2 -- an implementation that drops the
        denominator reads 1/1 and doubles the TFR. And the newborn girl is
        the only female at age zero, so an implementation that attributes the
        birth to the newborn instead of the mother also reads 1/1: with a
        single woman per age, as in the shared fixture, both mutations were
        exact wash-outs, which is how they survived a mutation pass.
        """
        sim, home, _ = sim_with_zones
        tick = sim.current_tick + 1
        mother = _agent(sim, home, "Madre", age=30, gender=Agent.Gender.FEMALE)
        _agent(sim, home, "Coetanea", age=30, gender=Agent.Gender.FEMALE)
        newborn = _agent(sim, home, "Neonata", age=0, gender=Agent.Gender.FEMALE)
        newborn.birth_tick = tick
        newborn.save(update_fields=["birth_tick"])
        DemographyEvent.objects.create(
            simulation=sim,
            tick=tick,
            event_type=DemographyEvent.EventType.BIRTH,
            primary_agent=newborn,
            secondary_agent=mother,
            payload={},
        )

        snapshot.write_population_snapshot(_context(sim, tick))

        row = PopulationSnapshot.objects.get(simulation=sim, tick=tick)
        assert row.tfr_instant == pytest.approx(TICKS_PER_YEAR / 2, rel=1e-6)

    def test_a_dissolved_couple_is_not_active_and_does_not_fuse_households(self, sim_with_zones):
        """The predicate the shared fixture never exercises: it forms one
        couple and never dissolves any, so dropping the dissolution filter
        changes nothing there. Here a dissolved pair must count zero and its
        two ex-partners must be two households, not one.
        """
        sim, home, _ = sim_with_zones
        tick = sim.current_tick + 1
        ex_a = _agent(sim, home, "ExUno", age=40)
        ex_b = _agent(sim, home, "ExDue", age=38, gender=Agent.Gender.FEMALE)
        couple = form_couple(ex_a, ex_b, formed_at_tick=sim.current_tick - 10)
        couple.dissolved_at_tick = sim.current_tick - 1
        couple.dissolution_reason = Couple.DissolutionReason.SEPARATE
        couple.save(update_fields=["dissolved_at_tick", "dissolution_reason"])

        snapshot.write_population_snapshot(_context(sim, tick))

        row = PopulationSnapshot.objects.get(simulation=sim, tick=tick)
        assert row.couples_active == 0
        assert row.avg_household_size == pytest.approx(1.0, abs=0.001)

    def test_an_adult_child_of_a_living_parent_is_their_own_household(self, sim_with_zones):
        """The docstring's own claim -- a household is a couple with the
        MINORS in its care -- against the sixty-year-old the derivation used
        to file under his eighty-five-year-old father's roof. Two adults,
        one a child of the other, are two households.
        """
        sim, home, _ = sim_with_zones
        tick = sim.current_tick + 1
        father = _agent(sim, home, "Padre", age=85)
        _agent(sim, home, "Figlio", age=60, parent_agent=father)

        snapshot.write_population_snapshot(_context(sim, tick))

        row = PopulationSnapshot.objects.get(simulation=sim, tick=tick)
        assert row.avg_household_size == pytest.approx(1.0, abs=0.001)

    def test_a_minor_child_of_a_living_parent_shares_their_household(self, sim_with_zones):
        """The other half of the same claim, so the fix cannot overshoot: a
        ten-year-old with a living mother is hers, and the pair is one
        household of two.
        """
        sim, home, _ = sim_with_zones
        tick = sim.current_tick + 1
        mother = _agent(sim, home, "MadreDiMinore", age=35, gender=Agent.Gender.FEMALE)
        _agent(sim, home, "Minore", age=10, parent_agent=mother)

        snapshot.write_population_snapshot(_context(sim, tick))

        row = PopulationSnapshot.objects.get(simulation=sim, tick=tick)
        assert row.avg_household_size == pytest.approx(2.0, abs=0.001)

    def test_ages_come_from_birth_tick_and_not_the_frozen_column(self, sim_with_zones):
        """The third time this trap appears in this work item, so it is worth
        naming: a fixture whose `age` column agrees with its `birth_tick`
        cannot tell which of the two an implementation read. Here they
        disagree, and `birth_tick` has to win -- it is the only source that
        advances as the run goes on.
        """
        sim, home, _ = sim_with_zones
        tick = sim.current_tick + 1
        agent = _agent(sim, home, "Sessantenne", age=60)
        Agent.objects.filter(pk=agent.pk).update(age=5)

        snapshot.write_population_snapshot(_context(sim, tick))

        row = PopulationSnapshot.objects.get(simulation=sim, tick=tick)
        assert row.avg_age == pytest.approx(60.0, abs=0.01)
        bucket = row.age_pyramid[0]
        assert bucket[0] == 60


class TestSnapshotSharesTheOrchestratorsClock:
    """One notion of time for the whole subsystem, or the validation series
    measures a different model from the one that produced it.

    Found by the closure review over the whole branch diff, which is the
    first pass that ever compared two modules against each other: the
    orchestrator derives an age as `(tick - birth_tick) / ticks_per_year *
    acceleration` while the snapshot dropped the acceleration factor. All
    five shipped templates set it to 1.0, so the two agreed and no test could
    tell them apart -- and `acceleration` is a per-era template parameter the
    schema admits, read by the orchestrator in three places. Under an
    accelerated era the age pyramid, the mean age, the TFR denominator and
    the household age threshold all describe a population that the mortality
    and fertility steps do not see.
    """

    def test_the_snapshot_ages_match_the_orchestrators_under_an_accelerated_era(
        self, sim_with_zones
    ):
        import copy

        sim, home, _ = sim_with_zones
        tick = sim.current_tick + 1
        agent = _agent(sim, home, "Accelerato", age=10)

        template = copy.deepcopy(load_template("pre_industrial_christian"))
        template["acceleration"] = 10.0
        context = orchestrator.DemographyTickContext(simulation=sim, tick=tick, template=template)
        expected = orchestrator.age_in_years(
            agent, tick, orchestrator._tick_duration_hours(sim), 10.0
        )
        # The fixture has to be able to tell the two formulas apart, or it
        # proves nothing: at acceleration 1.0 they coincide by construction.
        assert expected != pytest.approx(10.0, abs=0.5), (
            "the accelerated age is indistinguishable from the unaccelerated "
            "one: this fixture cannot separate the two clocks"
        )

        DemographyEvent.objects.create(
            simulation=sim,
            tick=tick,
            event_type=DemographyEvent.EventType.BIRTH,
            primary_agent=agent,
        )

        snapshot.write_population_snapshot(context)

        row = PopulationSnapshot.objects.get(simulation=sim, tick=tick)
        assert row.avg_age == pytest.approx(expected, abs=0.01), (
            "the snapshot dated the population on a different clock from the "
            "one mortality and fertility run on"
        )
        # The rates are annualised on the same clock, and they need their own
        # assertion: measured, once the ages stopped going through
        # `ticks_per_year`, dropping the acceleration from that conversion
        # left every test in this file green. One birth in a population of
        # one, annualised over an era where a tick is ten times longer.
        assert row.crude_birth_rate == pytest.approx(
            1 / 1 * 1000 * (TICKS_PER_YEAR / 10.0), rel=1e-6
        ), "the rates were annualised on the unaccelerated calendar"


class TestSnapshotLifecycle:
    def test_one_snapshot_per_tick(self, populated_tick):
        sim, _, _, tick = populated_tick

        snapshot.write_population_snapshot(_context(sim, tick))
        snapshot.write_population_snapshot(_context(sim, tick))

        assert PopulationSnapshot.objects.filter(simulation=sim, tick=tick).count() == 1

    def test_the_tick_writes_one_through_the_declared_order(self, populated_tick):
        """The snapshot is the last declared step, so a full block run leaves
        exactly one row describing that tick."""
        sim, _, _, tick = populated_tick

        orchestrator.run_demography_tick(sim, tick)

        assert PopulationSnapshot.objects.filter(simulation=sim, tick=tick).count() == 1

    def test_an_empty_population_still_writes_a_row(self, sim_with_zones):
        """A population that reached zero is a fact worth recording, not a
        reason to skip the tick's row."""
        sim, _, _ = sim_with_zones
        tick = sim.current_tick + 1

        snapshot.write_population_snapshot(_context(sim, tick))

        row = PopulationSnapshot.objects.get(simulation=sim, tick=tick)
        assert row.total_alive == 0
        # Fields whose computed empty-population value differs from the model
        # default, so a writer that skips computation on empty cannot pass.
        assert row.sex_ratio == 0.0  # zero males over zero females; default is 1.0
        assert Couple.objects.count() == 0

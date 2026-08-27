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
        assert Couple.objects.count() == 0

"""Tests for the demographic initialization of a founding population.

Two preconditions the demography modules assume, and that nothing satisfied.

`birth_tick` is the project's only source of ageing: `Agent.age` is written
once at world generation and never advances, so a population initialized
without `birth_tick` has mortality and fertility frozen for the whole run.

And nothing created couples. Three era templates of five, the default among
them, return a birth probability of exactly zero without an active couple,
so a founding population without couples makes birth impossible in the first
ticks -- and, with no births, the acceptance criterion for the whole work
item is unreachable.
"""

from __future__ import annotations

import pytest
from django.contrib.gis.geos import Point, Polygon

from epocha.apps.agents.models import Agent
from epocha.apps.demography import initialization
from epocha.apps.demography.models import Couple
from epocha.apps.simulation.models import Simulation
from epocha.apps.users.models import User
from epocha.apps.world.models import World, Zone

TICKS_PER_YEAR = 365.0


@pytest.fixture
def sim_with_zone(db):
    user = User.objects.create_user(
        email="init@epocha.dev", username="inituser", password="pass1234"
    )
    sim = Simulation.objects.create(
        name="InitTest",
        seed=2026,
        owner=user,
        current_tick=0,
        config={"demography_enabled": True},
    )
    world = World.objects.create(simulation=sim, stability_index=0.7)
    zone = Zone.objects.create(
        world=world,
        name="InitZone",
        zone_type="residential",
        boundary=Polygon.from_bbox((0, 0, 100, 100)),
        center=Point(50, 50),
    )
    return sim, zone


def _agent(sim, zone, name, age, gender=Agent.Gender.MALE, **kwargs):
    """A generated agent: `age` set by the world generator, `birth_tick` NULL,
    which is exactly the state initialization has to repair."""
    defaults = dict(
        role="farmer",
        location=Point(50, 50),
        health=1.0,
        wealth=100.0,
        age=age,
        birth_tick=None,
        education_level=0.5,
        social_class="working",
        gender=gender,
        personality={},
    )
    defaults.update(kwargs)
    return Agent.objects.create(simulation=sim, name=name, zone=zone, **defaults)


class TestBirthTickBackfill:
    def test_no_living_agent_is_left_without_a_birth_tick(self, sim_with_zone):
        """The post-condition FR-013 states, asserted as a post-condition
        rather than per agent: what matters is that the frozen-age path is
        unreachable afterwards."""
        sim, zone = sim_with_zone
        _agent(sim, zone, "Uno", age=20)
        _agent(sim, zone, "Due", age=45)
        _agent(sim, zone, "Tre", age=70)

        initialization.initialize_demography(sim)

        assert not Agent.objects.filter(
            simulation=sim, is_alive=True, birth_tick__isnull=True
        ).exists()

    def test_the_birth_tick_reproduces_the_generated_age(self, sim_with_zone):
        """Derived from the age the generator wrote, not invented: an agent
        the world describes as forty must still be forty on the tick the
        initialization runs, or the population's age structure is silently
        rewritten."""
        sim, zone = sim_with_zone
        agent = _agent(sim, zone, "Quarantenne", age=40)

        initialization.initialize_demography(sim)

        agent.refresh_from_db()
        derived_age = (sim.current_tick - agent.birth_tick) / TICKS_PER_YEAR
        assert derived_age == pytest.approx(40.0, abs=0.01)

    def test_an_existing_birth_tick_is_left_alone(self, sim_with_zone):
        """Initialization repairs what is missing; it does not overwrite a
        lineage a birth already recorded."""
        sim, zone = sim_with_zone
        newborn = _agent(sim, zone, "Neonato", age=0, birth_tick=-5)

        initialization.initialize_demography(sim)

        newborn.refresh_from_db()
        assert newborn.birth_tick == -5

    def test_the_dead_are_not_backfilled(self, sim_with_zone):
        sim, zone = sim_with_zone
        dead = _agent(sim, zone, "Morto", age=60, is_alive=False, death_tick=0)

        initialization.initialize_demography(sim)

        dead.refresh_from_db()
        assert dead.birth_tick is None


class TestInitialCouples:
    def test_couples_are_formed_among_eligible_adults(self, sim_with_zone):
        sim, zone = sim_with_zone
        for i in range(3):
            _agent(sim, zone, f"Uomo{i}", age=30, gender=Agent.Gender.MALE)
            _agent(sim, zone, f"Donna{i}", age=28, gender=Agent.Gender.FEMALE)

        initialization.initialize_demography(sim)

        assert Couple.objects.filter(simulation=sim, dissolved_at_tick__isnull=True).count() == 3

    def test_nobody_is_in_two_couples(self, sim_with_zone):
        sim, zone = sim_with_zone
        for i in range(4):
            _agent(sim, zone, f"Uomo{i}", age=30, gender=Agent.Gender.MALE)
            _agent(sim, zone, f"Donna{i}", age=28, gender=Agent.Gender.FEMALE)

        initialization.initialize_demography(sim)

        partnered = []
        for couple in Couple.objects.filter(simulation=sim):
            partnered += [couple.agent_a_id, couple.agent_b_id]
        assert len(partnered) == len(set(partnered))

    def test_agents_below_the_marriage_age_are_not_paired(self, sim_with_zone):
        """The era template's own minimum marriage ages, not an invented
        threshold."""
        sim, zone = sim_with_zone
        child_m = _agent(sim, zone, "Bambino", age=8, gender=Agent.Gender.MALE)
        child_f = _agent(sim, zone, "Bambina", age=7, gender=Agent.Gender.FEMALE)

        initialization.initialize_demography(sim)

        assert not Couple.objects.filter(simulation=sim, agent_a__in=[child_m, child_f]).exists()
        assert not Couple.objects.filter(simulation=sim, agent_b__in=[child_m, child_f]).exists()

    def test_the_male_threshold_alone_blocks_a_pairing(self, sim_with_zone):
        """Isolated on purpose: one candidate per side, so the only reason a
        couple can fail to form is the male minimum age.

        With two eligible men in the fixture the homogamy score would pick
        the closer-aged one anyway, and the test would pass whether or not
        the threshold was applied -- proving nothing about the threshold.
        """
        sim, zone = sim_with_zone
        boy = _agent(sim, zone, "Quindicenne", age=15, gender=Agent.Gender.MALE)
        _agent(sim, zone, "Adulta", age=30, gender=Agent.Gender.FEMALE)

        initialization.initialize_demography(sim)

        assert not Couple.objects.filter(simulation=sim).exists(), (
            f"{boy.name} is below the era's minimum marriage age for men and was paired anyway"
        )

    def test_the_female_threshold_alone_blocks_a_pairing(self, sim_with_zone):
        """The mirror case: the two minimums differ (16 and 14 in the default
        template), so each needs its own witness."""
        sim, zone = sim_with_zone
        girl = _agent(sim, zone, "Tredicenne", age=13, gender=Agent.Gender.FEMALE)
        _agent(sim, zone, "Adulto", age=30, gender=Agent.Gender.MALE)

        initialization.initialize_demography(sim)

        assert not Couple.objects.filter(simulation=sim).exists(), (
            f"{girl.name} is below the era's minimum marriage age for women and was paired anyway"
        )

    def test_it_is_idempotent(self, sim_with_zone):
        """Running twice must not double the couples: the founding
        population is initialized once, but nothing should break if a
        caller repeats it."""
        sim, zone = sim_with_zone
        _agent(sim, zone, "Uomo", age=30, gender=Agent.Gender.MALE)
        _agent(sim, zone, "Donna", age=28, gender=Agent.Gender.FEMALE)

        initialization.initialize_demography(sim)
        initialization.initialize_demography(sim)

        assert Couple.objects.filter(simulation=sim, dissolved_at_tick__isnull=True).count() == 1

    def test_the_pairing_is_reproducible_from_the_seed(self, sim_with_zone):
        sim, zone = sim_with_zone
        for i in range(3):
            _agent(sim, zone, f"Uomo{i}", age=30 + i, gender=Agent.Gender.MALE)
            _agent(sim, zone, f"Donna{i}", age=28 + i, gender=Agent.Gender.FEMALE)

        initialization.initialize_demography(sim)
        first = sorted(
            Couple.objects.filter(simulation=sim).values_list("agent_a_id", "agent_b_id")
        )

        Couple.objects.filter(simulation=sim).delete()
        initialization.initialize_demography(sim)
        second = sorted(
            Couple.objects.filter(simulation=sim).values_list("agent_a_id", "agent_b_id")
        )

        assert first == second


class TestActivationPredicate:
    def test_a_simulation_without_demography_is_left_untouched(self, sim_with_zone):
        """FR-009's invariance holds at generation time too: initializing a
        simulation that never opted in would write couples and birth ticks
        nobody asked for."""
        sim, zone = sim_with_zone
        sim.config = {}
        sim.save()
        agent = _agent(sim, zone, "Indifferente", age=30, gender=Agent.Gender.MALE)
        _agent(sim, zone, "Indifferente2", age=28, gender=Agent.Gender.FEMALE)

        initialization.initialize_demography(sim)

        agent.refresh_from_db()
        assert agent.birth_tick is None
        assert not Couple.objects.filter(simulation=sim).exists()

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


class TestBrokenTemplate:
    """A template that cannot load must not abort world generation.

    The generator calls `initialize_demography` unguarded, so before this
    guard an invalid `demography_template` name raised out of couple
    formation and took the whole world-generation call down with it. The
    per-tick orchestrator already skips the tick with a warning naming the
    template; initialization now behaves the same way, and still backfills
    `birth_tick` -- ageing does not depend on the template, and repairing it
    costs nothing even when couples cannot form.
    """

    def test_a_missing_template_does_not_abort_and_still_backfills(self, sim_with_zone, caplog):
        sim, zone = sim_with_zone
        sim.config["demography_template"] = "no_such_era"
        sim.save(update_fields=["config"])
        man = _agent(sim, zone, "Uomo", age=30)
        woman = _agent(sim, zone, "Donna", age=28, gender=Agent.Gender.FEMALE)

        import logging

        with caplog.at_level(logging.WARNING, logger="epocha.apps.demography.initialization"):
            initialization.initialize_demography(sim)

        man.refresh_from_db()
        woman.refresh_from_db()
        assert man.birth_tick is not None
        assert woman.birth_tick is not None
        assert Couple.objects.filter(simulation=sim).count() == 0
        assert any("no_such_era" in record.message for record in caplog.records), (
            "a skipped initialization must say which template failed, "
            "or a sterile founding population has no explanation in any log"
        )


class TestActivationOnAnAlreadyGeneratedWorld:
    """Turning demography on after the world exists must not produce a
    silently sterile population.

    `initialize_demography` has exactly one caller, the world generator, so
    every world generated before the flag was set carries agents with a NULL
    `birth_tick`. That is not a cosmetic gap: `birth_tick` is the only source
    of ageing, and the fertile window is filtered in SQL on it, so those
    agents are excluded from every candidate query -- they never conceive,
    never age, never die of senescence -- and nothing said so anywhere.
    """

    def _population(self, sim, zone, count=4):
        """Agents exactly as the generator leaves them: an `age` column and
        no `birth_tick` at all."""
        from epocha.apps.agents.models import Agent
        from epocha.apps.world.models import Government

        # The forced-migration step reads it; the shared fixture of this
        # module predates the block and does not create one.
        Government.objects.get_or_create(simulation=sim)

        made = []
        for i in range(count):
            # Female on purpose: the fertility step filters on sex, so an
            # all-male population returns from the step before it ever reads
            # the couple membership -- and a fixture that never reaches the
            # code it is measuring is the trap this work item keeps paying
            # for.
            agent = _agent(sim, zone, f"Preesistente{i}", age=28, gender=Agent.Gender.FEMALE)
            Agent.objects.filter(pk=agent.pk).update(birth_tick=None)
            agent.refresh_from_db()
            assert agent.birth_tick is None
            made.append(agent)
        return made

    def test_the_block_repairs_a_population_that_was_never_initialized(self, sim_with_zone, caplog):
        import logging

        from epocha.apps.demography.orchestrator import run_demography_tick

        sim, zone = sim_with_zone
        agents = self._population(sim, zone)

        # No logger named: the repair is the initialization module's own, so
        # pinning the orchestrator's logger would assert where the sentence
        # is emitted rather than that it is emitted at all.
        with caplog.at_level(logging.INFO):
            run_demography_tick(sim, sim.current_tick + 1)

        for agent in agents:
            agent.refresh_from_db()
            assert agent.birth_tick is not None, (
                "an agent generated before demography was enabled still has no "
                "birth_tick: it is invisible to every candidate query and ages "
                "never"
            )
        assert any("birth_tick" in record.message for record in caplog.records), (
            "the repair happened silently: nothing in the log explains it"
        )

    def test_the_repair_restores_the_age_the_generator_wrote(self, sim_with_zone):
        """The repair must not rewrite the population's age structure.

        `birth_tick` is derived from the `age` column at the tick the repair
        runs, so an agent the world describes as 28 has to still be 28
        afterwards. Deriving it at tick 0 instead would age the whole
        founding population by however many ticks the run had reached.
        """
        from epocha.apps.demography.orchestrator import run_demography_tick

        sim, zone = sim_with_zone
        sim.current_tick = 500
        sim.save(update_fields=["current_tick"])
        agent = self._population(sim, zone, count=1)[0]

        tick = sim.current_tick + 1
        run_demography_tick(sim, tick)

        agent.refresh_from_db()
        # Asserted on birth_tick and not through `age_in_years`, which falls
        # back to the frozen column when birth_tick is NULL and therefore
        # answers 28 whether or not the repair ran at all. The first version
        # of this test did exactly that and passed before the fix existed.
        assert agent.birth_tick is not None
        assert (tick - agent.birth_tick) / (8760.0 / 24.0) == pytest.approx(28.0, abs=0.01)

    def test_a_repaired_population_can_actually_conceive(self, sim_with_zone):
        """The observable the repair exists for, not the column it writes.

        Under an era that does not require a couple, a forced fertility
        stream must produce a birth from a population that had no
        `birth_tick`. Without the repair the candidate query returns nothing
        and the same stream produces nothing at all.
        """
        from epocha.apps.agents.models import Agent
        from epocha.apps.demography import orchestrator

        sim, zone = sim_with_zone
        from epocha.apps.world.models import Government

        Government.objects.get_or_create(simulation=sim)
        sim.config["demography_template"] = "modern_democracy"
        sim.save(update_fields=["config"])
        for i in range(3):
            woman = _agent(sim, zone, f"Donna{i}", age=27, gender=Agent.Gender.FEMALE)
            Agent.objects.filter(pk=woman.pk).update(birth_tick=None)

        tick = sim.current_tick + 1
        real_stream_for = orchestrator.stream_for

        class _ForcedBirth:
            def __init__(self):
                self._draws = [0.0, 0.9]

            def random(self):
                return self._draws.pop(0) if self._draws else 1.0

            def gauss(self, mu, sigma):
                return mu

            def randrange(self, n):
                return 0

        def _scripted(simulation, t, phase):
            return _ForcedBirth() if phase == "fertility" else real_stream_for(simulation, t, phase)

        orchestrator.stream_for = _scripted
        try:
            orchestrator.run_demography_tick(sim, tick)
        finally:
            orchestrator.stream_for = real_stream_for

        assert Agent.objects.filter(simulation=sim, birth_tick=tick).exists(), (
            "a population repaired by the block still produced no birth under a "
            "forced stream: the repair writes a column nothing consumes"
        )

    def test_an_era_that_needs_no_couple_is_not_warned_about_couples(self, sim_with_zone, caplog):
        """The other side of the predicate, without which the warning fires
        on eras where having no couple is simply normal.

        `modern_democracy` returns a positive birth probability for an
        unpartnered mother, so a population with no couple is not sterile
        there and saying it is would be noise -- and noise in a log is how a
        real warning stops being read.
        """
        import logging

        from epocha.apps.demography.orchestrator import run_demography_tick
        from epocha.apps.world.models import Government

        sim, zone = sim_with_zone
        Government.objects.get_or_create(simulation=sim)
        sim.config["demography_template"] = "modern_democracy"
        sim.save(update_fields=["config"])
        self._population(sim, zone)

        with caplog.at_level(logging.WARNING):
            run_demography_tick(sim, sim.current_tick + 1)

        assert not any("couple" in record.message for record in caplog.records), (
            "an era that allows unpartnered birth was warned about having no "
            "couple: the warning does not read the era's own predicate"
        )

    def test_a_population_with_no_couple_says_so_when_the_era_needs_one(
        self, sim_with_zone, caplog
    ):
        """The other half of the sterility, and the one no column repairs.

        Three of the five era templates return a birth probability of exactly
        zero for a mother not in an active couple. A world whose founding
        couples were never formed is therefore sterile until enough pair-bond
        intents accumulate through step 2 -- which is correct behaviour, and
        completely invisible. It is reported using the couple membership the
        fertility step has already read, so saying it costs no query.
        """
        import logging

        from epocha.apps.demography.orchestrator import run_demography_tick

        sim, zone = sim_with_zone
        self._population(sim, zone)

        with caplog.at_level(logging.WARNING):
            run_demography_tick(sim, sim.current_tick + 1)

        assert any(
            "couple" in record.message and record.levelno >= logging.WARNING
            for record in caplog.records
        ), (
            "a population that cannot conceive under this era produced no "
            "warning: the sterility is silent"
        )


class TestBirthTickSharesTheOrchestratorsClock:
    """The backfill writes `birth_tick`; `age_in_years` reads it. One clock.

    Found by round 9 of the phase-6 gate, reading the whole branch diff
    rather than the last remediation. `initialization.py` was the only module
    of the subsystem that never named `acceleration` -- zero occurrences
    against fifteen in `orchestrator.py` -- so the round trip returned the
    written age multiplied by the era's acceleration factor. The function's
    own docstring states the invariant it broke: an agent the world describes
    as forty has to still be forty on the tick this runs.

    Not cosmetic under an accelerated era: the Heligman-Pollard hazard would
    be evaluated at four hundred years instead of forty, and the fertile
    window -- which scales the other way -- would exclude the entire founding
    population, so nobody would ever conceive.
    """

    def test_the_written_birth_tick_reads_back_as_the_written_age(self, sim_with_zone):
        import copy

        from epocha.apps.demography import orchestrator
        from epocha.apps.demography.initialization import backfill_birth_ticks
        from epocha.apps.demography.template_loader import load_template

        sim, zone = sim_with_zone
        agent = _agent(sim, zone, "Quarantenne", age=40)
        Agent.objects.filter(pk=agent.pk).update(birth_tick=None)

        template = copy.deepcopy(load_template("pre_industrial_christian"))
        template["acceleration"] = 10.0
        backfill_birth_ticks(sim, template=template)

        agent.refresh_from_db()
        read_back = orchestrator.age_in_years(
            agent, sim.current_tick, orchestrator._tick_duration_hours(sim), 10.0
        )
        assert read_back == pytest.approx(40.0, abs=0.05), (
            f"written as 40 and read back as {read_back}: the backfill and "
            "the orchestrator are on different clocks"
        )


class TestTheFoundingPairingSharesTheIntentPathsAgeRule:
    """One marriage-age rule for both paths that form couples.

    Round 9 of the phase-6 gate found the era's minimum marriage age applied
    on the founding pairing and ignored on the intent path. The fix is one
    predicate used by both, on the canonical age -- `age_in_years` over
    `birth_tick` -- where the founding pairing used to read the `age` column.
    """

    def test_an_existing_birth_tick_outranks_the_column(self, sim_with_zone):
        """The backfill never overwrites a recorded `birth_tick`, so a founder
        can carry one that disagrees with the column. Each is made to say
        the opposite of the other, in both directions: a rule that reads the
        column pairs the wrong one.
        """
        sim, zone = sim_with_zone
        # The column says 30, the birth tick says 12: under the female 14.
        _agent(
            sim,
            zone,
            "ColonnaAdulta",
            age=30,
            gender=Agent.Gender.FEMALE,
            birth_tick=sim.current_tick - int(12 * TICKS_PER_YEAR),
        )
        # The column says 10, the birth tick says 25: well over the male 16.
        groom = _agent(
            sim,
            zone,
            "ColonnaBambino",
            age=10,
            gender=Agent.Gender.MALE,
            birth_tick=sim.current_tick - int(25 * TICKS_PER_YEAR),
        )
        bride = _agent(sim, zone, "Sposa", age=24, gender=Agent.Gender.FEMALE)

        initialization.initialize_demography(sim)

        pairs = set(Couple.objects.filter(simulation=sim).values_list("agent_a_id", "agent_b_id"))
        assert pairs == {tuple(sorted((groom.id, bride.id)))}, (
            "the founding pairing read the frozen `age` column instead of the "
            "canonical age from `birth_tick`"
        )


class TestTheBackfillNeverMakesAFounderYounger:
    """`birth_tick` is an integer, so the inverse of `age_in_years` is rounded.

    Rounding to the NEAREST tick makes the read-back age fall below the
    written one whenever a year is not a whole number of ticks: a weekly
    world has 52.14 of them, and 40 of the 91 ages 0-90 came back short on
    it. The read-back age then
    truncates to one year less: the mortality step's age refresh rewrites the
    column to that, and a founder written at exactly the era's minimum
    marriage age is refused by the canonical age rule. The backfill now lets
    `age_in_years` judge the written tick and moves it one tick into the past
    when the reader comes back short, so the integer part of the read-back
    age is the written age. Age 63 on a weekly world is the float case: the
    exact inverse is a whole number of ticks and the reader still returned
    62.999..., which is why rounding toward the past alone was not the fix.
    """

    WEEK_HOURS = 168.0

    def test_every_integer_age_reads_back_as_itself_on_a_weekly_world(self, sim_with_zone):
        from epocha.apps.demography import orchestrator

        sim, zone = sim_with_zone
        World.objects.filter(simulation=sim).update(tick_duration_hours=self.WEEK_HOURS)
        agents = [_agent(sim, zone, f"Eta{age}", age=age) for age in range(0, 91)]

        initialization.backfill_birth_ticks(sim)

        younger = []
        for agent in agents:
            agent.refresh_from_db()
            read_back = orchestrator.age_in_years(agent, sim.current_tick, self.WEEK_HOURS, 1.0)
            if int(read_back) != agent.age:
                younger.append((agent.age, round(read_back, 4)))
        assert younger == [], (
            f"written ages that read back as another integer: {younger[:5]} ({len(younger)} of 91)"
        )

    def test_a_founder_at_exactly_the_threshold_is_paired_on_a_weekly_world(self, sim_with_zone):
        """The consequence that matters: under `industrial` the women's
        threshold is 16, and 16 years is 834.29 weekly ticks."""
        sim, zone = sim_with_zone
        sim.config = {"demography_enabled": True, "demography_template": "industrial"}
        sim.save()
        World.objects.filter(simulation=sim).update(tick_duration_hours=self.WEEK_HOURS)
        _agent(sim, zone, "Sedicenne", age=16, gender=Agent.Gender.FEMALE)
        _agent(sim, zone, "Adulto", age=30, gender=Agent.Gender.MALE)

        initialization.initialize_demography(sim)

        assert Couple.objects.filter(simulation=sim).count() == 1, (
            "a sixteen-year-old founder was refused under a threshold of 16: "
            "the backfill made her younger than the world wrote her"
        )

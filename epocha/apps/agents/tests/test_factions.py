"""Tests for the faction dynamics engine."""

import pytest
from django.conf import settings

from epocha.apps.agents.affinity import compute_affinity
from epocha.apps.agents.factions import (
    _check_join_existing_groups,
    compute_leadership_score,
    update_group_cohesion,
    update_group_leadership,
)
from epocha.apps.agents.models import Agent, DecisionLog, Group, Memory, Relationship
from epocha.apps.simulation.models import Simulation
from epocha.apps.users.models import User
from epocha.apps.world.models import World

# Big Five trait keys, mirrored from epocha.apps.agents.affinity._BIG_FIVE
# (kept literal here so the tests do not depend on a private constant).
_BIG_FIVE_TRAITS = (
    "openness",
    "conscientiousness",
    "extraversion",
    "agreeableness",
    "neuroticism",
)


@pytest.fixture
def user(db):
    return User.objects.create_user(email="fac@epocha.dev", username="factest", password="pass123")


@pytest.fixture
def simulation(user):
    return Simulation.objects.create(name="FacTest", seed=42, owner=user)


@pytest.fixture
def world(simulation):
    return World.objects.create(simulation=simulation)


@pytest.fixture
def group_with_members(simulation):
    group = Group.objects.create(
        simulation=simulation,
        name="The Guild",
        objective="Protect artisans",
        cohesion=0.6,
        formed_at_tick=1,
    )
    marco = Agent.objects.create(
        simulation=simulation,
        name="Marco",
        role="blacksmith",
        personality={
            "openness": 0.5,
            "conscientiousness": 0.5,
            "extraversion": 0.5,
            "agreeableness": 0.5,
            "neuroticism": 0.5,
        },
        charisma=0.8,
        intelligence=0.7,
        wealth=60.0,
        group=group,
    )
    elena = Agent.objects.create(
        simulation=simulation,
        name="Elena",
        role="farmer",
        personality={
            "openness": 0.5,
            "conscientiousness": 0.5,
            "extraversion": 0.5,
            "agreeableness": 0.5,
            "neuroticism": 0.5,
        },
        charisma=0.4,
        intelligence=0.5,
        wealth=30.0,
        group=group,
    )
    carlo = Agent.objects.create(
        simulation=simulation,
        name="Carlo",
        role="priest",
        personality={
            "openness": 0.5,
            "conscientiousness": 0.5,
            "extraversion": 0.5,
            "agreeableness": 0.5,
            "neuroticism": 0.5,
        },
        charisma=0.6,
        intelligence=0.6,
        wealth=45.0,
        group=group,
    )
    group.leader = marco
    group.save(update_fields=["leader"])
    # Memories for seniority tracking
    Memory.objects.create(
        agent=marco,
        content="I helped found The Guild",
        emotional_weight=0.3,
        source_type="direct",
        tick_created=1,
    )
    Memory.objects.create(
        agent=elena,
        content="I helped found The Guild",
        emotional_weight=0.3,
        source_type="direct",
        tick_created=1,
    )
    Memory.objects.create(
        agent=carlo,
        content="I joined The Guild",
        emotional_weight=0.3,
        source_type="direct",
        tick_created=5,
    )
    return group, marco, elena, carlo


@pytest.mark.django_db
class TestLeadershipScore:
    def test_charismatic_wealthy_agent_scores_high(self, group_with_members):
        group, marco, elena, carlo = group_with_members
        Relationship.objects.create(
            agent_from=marco,
            agent_to=elena,
            relation_type="friendship",
            strength=0.7,
            sentiment=0.6,
            since_tick=0,
        )
        Relationship.objects.create(
            agent_from=marco,
            agent_to=carlo,
            relation_type="professional",
            strength=0.5,
            sentiment=0.3,
            since_tick=0,
        )
        score = compute_leadership_score(marco, group, tick=10)
        assert score > 0.5

    def test_low_charisma_agent_scores_low(self, group_with_members):
        group, marco, elena, carlo = group_with_members
        score = compute_leadership_score(elena, group, tick=10)
        assert score < compute_leadership_score(marco, group, tick=10)

    def test_score_range_zero_to_one(self, group_with_members):
        group, marco, elena, carlo = group_with_members
        for agent in [marco, elena, carlo]:
            score = compute_leadership_score(agent, group, tick=10)
            assert 0.0 <= score <= 1.0


@pytest.mark.django_db
class TestCohesionUpdate:
    def test_cooperation_increases_cohesion(self, simulation, world, group_with_members):
        group, marco, elena, carlo = group_with_members
        # Marco helps Elena (cooperation)
        DecisionLog.objects.create(
            simulation=simulation,
            agent=marco,
            tick=9,
            input_context="",
            output_decision='{"action": "help", "target": "Elena"}',
            llm_model="test",
        )
        initial_cohesion = group.cohesion
        update_group_cohesion(group, simulation, tick=10)
        group.refresh_from_db()
        assert group.cohesion > initial_cohesion

    def test_conflict_decreases_cohesion(self, simulation, world, group_with_members):
        group, marco, elena, carlo = group_with_members
        # Marco argues with Elena (conflict)
        DecisionLog.objects.create(
            simulation=simulation,
            agent=marco,
            tick=9,
            input_context="",
            output_decision='{"action": "argue", "target": "Elena"}',
            llm_model="test",
        )
        initial_cohesion = group.cohesion
        update_group_cohesion(group, simulation, tick=10)
        group.refresh_from_db()
        assert group.cohesion < initial_cohesion

    def test_cohesion_clamped_to_range(self, simulation, world, group_with_members):
        group, marco, elena, carlo = group_with_members
        group.cohesion = 0.99
        group.save(update_fields=["cohesion"])
        update_group_cohesion(group, simulation, tick=10)
        group.refresh_from_db()
        assert 0.0 <= group.cohesion <= 1.0


@pytest.mark.django_db
class TestLeadershipContestaton:
    def test_legitimate_leader_stays(self, simulation, world, group_with_members):
        group, marco, elena, carlo = group_with_members
        Relationship.objects.create(
            agent_from=marco,
            agent_to=elena,
            relation_type="friendship",
            strength=0.7,
            sentiment=0.6,
            since_tick=0,
        )
        Relationship.objects.create(
            agent_from=marco,
            agent_to=carlo,
            relation_type="professional",
            strength=0.5,
            sentiment=0.3,
            since_tick=0,
        )
        update_group_leadership(group, tick=10)
        group.refresh_from_db()
        assert group.leader == marco

    def test_unpopular_leader_replaced(self, simulation, world, group_with_members):
        group, marco, elena, carlo = group_with_members
        # Marco has terrible relationships with everyone
        Relationship.objects.create(
            agent_from=marco,
            agent_to=elena,
            relation_type="rivalry",
            strength=0.8,
            sentiment=-0.8,
            since_tick=0,
        )
        Relationship.objects.create(
            agent_from=marco,
            agent_to=carlo,
            relation_type="distrust",
            strength=0.7,
            sentiment=-0.6,
            since_tick=0,
        )
        # Lower group cohesion enough that legitimacy falls below the 0.3 threshold.
        # With cohesion=0.05, leader_sentiment=0.15 (from avg normalized -0.7),
        # score_rank=1.0: legitimacy = 0.05*0.4 + 0.15*0.4 + 1.0*0.2 = 0.28 < 0.3.
        group.cohesion = 0.05
        group.save(update_fields=["cohesion"])
        update_group_leadership(group, tick=10)
        group.refresh_from_db()
        assert group.leader != marco


def _make_join_agent(simulation, name, *, group=None, **overrides):
    """Create an agent tuned for join-check scenarios.

    Defaults give any two such agents a no-relationship affinity of exactly
    0.3 (personality, identical defaults) + 0.4 * 0.60 (same class, same
    wealth quartile, same role) = 0.54, just above the 0.5 threshold, so a
    single positive relationship is the only extra ingredient a suggestion
    needs. Overrides let a test push individual agents far above or below
    the threshold.
    """
    fields = {
        "simulation": simulation,
        "name": name,
        "role": "farmer",
        "social_class": "working",
        "mood": 0.5,
        "wealth": 50.0,
        "group": group,
    }
    fields.update(overrides)
    return Agent.objects.create(**fields)


@pytest.mark.django_db
class TestJoinExistingGroups:
    """Round 3 hardening contract for _check_join_existing_groups (FR-002)."""

    def test_join_check_averages_all_members(self, simulation, world):
        """The join suggestion must reflect the average over ALL living members.

        Fixture: one group with 10 living members -- the first 5 created
        (lowest ids) have engineered HIGH affinity (~0.77) with the ungrouped
        agent, the last 5 have LOW affinity (~0.06). The all-10 average
        (~0.415) is BELOW the 0.5 threshold, so the post-fix contract is
        that NO suggestion Memory is created. The positive-relationship
        precondition is satisfied (sentiment 0.5 > 0 with the high members),
        so the average is the only deciding gate.

        Pre-fix behavior note (recorded per task T005): the old code
        averaged an unordered `[:5]` slice, so its outcome here is
        implementation-defined -- if Postgres returns the 5 high-affinity
        members (likely on a freshly-inserted table, insertion order), the
        subset average (~0.77) crosses the threshold and a spurious
        suggestion is created (test RED); a mixed slice may pass by luck.
        The deterministic guarantee that this test pins down exists only
        after the all-members refactor. The expected outcome is computed
        in-test from compute_affinity over all 10 members, so the assertion
        encodes the semantics, not a magic number.
        """
        threshold = getattr(settings, "EPOCHA_FACTION_AFFINITY_THRESHOLD", 0.5)
        group = Group.objects.create(
            simulation=simulation, name="Ironhold", cohesion=0.7, formed_at_tick=1
        )
        high_traits = {t: 0.9 for t in _BIG_FIVE_TRAITS}
        low_traits = {t: 0.1 for t in _BIG_FIVE_TRAITS}

        # 5 high-affinity members FIRST (lowest ids -> most likely pre-fix slice).
        high_members = [
            _make_join_agent(
                simulation,
                f"High{i}",
                group=group,
                personality=dict(high_traits),
                mood=0.3,
            )
            for i in range(5)
        ]
        # 5 low-affinity members: opposite personality, different class,
        # high mood, remote wealth quartile, different role.
        low_members = [
            _make_join_agent(
                simulation,
                f"Low{i}",
                group=group,
                personality=dict(low_traits),
                social_class="elite",
                mood=0.9,
                wealth=5000.0,
                role="priest",
            )
            for i in range(5)
        ]

        seeker = _make_join_agent(simulation, "Seeker", personality=dict(high_traits), mood=0.3)
        # Positive relationships with the high members only: satisfies the
        # has_positive_rel precondition and lifts high-pair affinity to ~0.77.
        for member in high_members:
            Relationship.objects.create(
                agent_from=seeker,
                agent_to=member,
                relation_type="friendship",
                strength=0.5,
                sentiment=0.5,
                since_tick=0,
            )

        tick = 10
        all_members = high_members + low_members
        expected_avg = sum(compute_affinity(seeker, m, tick) for m in all_members) / len(
            all_members
        )
        # Fixture sanity: the all-10 average is below threshold while every
        # subset made only of high members is above it.
        assert expected_avg < threshold
        high_avg = sum(compute_affinity(seeker, m, tick) for m in high_members) / len(high_members)
        assert high_avg >= threshold

        _check_join_existing_groups(simulation, tick)

        suggestions = Memory.objects.filter(agent=seeker, content__contains="shares my values")
        assert not suggestions.exists(), (
            "suggestion created although the all-members average "
            f"({expected_avg:.3f}) is below the threshold ({threshold})"
        )

    def test_join_check_query_budget(self, simulation, world, django_assert_num_queries):
        """_check_join_existing_groups runs on a FIXED per-tick query budget.

        Post-fix budget: 8 queries, independent of the number of
        (agent, group) pairs and of the number of suggestions generated:
          1. ungrouped agents fetch (order_by id)
          2. active groups fetch (order_by id)
          3. living members of ALL groups in one query (order_by id)
          4. affinity context -- Relationship superset query
          5. affinity context -- Memory (PUBLIC window) query
          6. positive-relationship pairs prefetch (sentiment > 0)
          7. dedup -- ALL recent memories of ungrouped agents (tick-5 window)
          8. bulk_create of the suggestion memories

        Pre-fix this scenario costs O(pairs) queries (~3 per compute_affinity
        call alone, plus per-agent member refetch, per-pair positive-rel
        exists and per-agent dedup exists), so the assertion fails RED with
        the observed count in the failure message.

        The second scenario doubles the ungrouped agents and asserts the
        SAME budget -- the constant-cost contract of SC-001.
        """
        groups = [
            Group.objects.create(
                simulation=simulation, name=f"Order{g}", cohesion=0.7, formed_at_tick=1
            )
            for g in range(4)
        ]
        members_by_group = {
            g.id: [_make_join_agent(simulation, f"G{gi}M{i}", group=g) for i in range(10)]
            for gi, g in enumerate(groups)
        }

        def _add_ungrouped(batch, count):
            agents = [_make_join_agent(simulation, f"Free{batch}_{i}") for i in range(count)]
            # Positive relationship with a member of the first group: enables
            # the positive-rel branch and guarantees a suggestion per agent,
            # so bulk_create fires in both scenarios.
            for agent in agents:
                Relationship.objects.create(
                    agent_from=agent,
                    agent_to=members_by_group[groups[0].id][0],
                    relation_type="friendship",
                    strength=0.5,
                    sentiment=0.5,
                    since_tick=0,
                )
            return agents

        _add_ungrouped(batch=1, count=8)
        with django_assert_num_queries(8):
            _check_join_existing_groups(simulation, tick=10)

        # Double the ungrouped population; the budget must not change.
        # (tick=20 keeps the first run's suggestions outside the tick-5
        # dedup window, so the second run also generates suggestions.)
        _add_ungrouped(batch=2, count=8)
        with django_assert_num_queries(8):
            _check_join_existing_groups(simulation, tick=20)

    def test_join_check_dedup_semantics(self, simulation, world):
        """Any recent memory containing the group name suppresses the suggestion.

        The dedup filter is content__contains=group.name over the tick-5
        window with NO source/type restriction: a non-suggestion memory such
        as "Alpha has dissolved." must suppress a new suggestion for group
        "Alpha". This broad semantics is intentional and must survive the
        refactor unchanged (passes both pre-fix and post-fix).
        """
        group = Group.objects.create(
            simulation=simulation, name="Alpha", cohesion=0.7, formed_at_tick=1
        )
        members = [_make_join_agent(simulation, f"Member{i}", group=group) for i in range(3)]
        agent = _make_join_agent(simulation, "Hopeful")
        Relationship.objects.create(
            agent_from=agent,
            agent_to=members[0],
            relation_type="friendship",
            strength=0.5,
            sentiment=0.5,
            since_tick=0,
        )
        # Recent NON-suggestion memory containing the group name.
        Memory.objects.create(
            agent=agent,
            content="Alpha has dissolved.",
            emotional_weight=0.3,
            source_type=Memory.SourceType.DIRECT,
            tick_created=8,
        )

        _check_join_existing_groups(simulation, tick=10)

        assert not Memory.objects.filter(agent=agent, content__contains="shares my values").exists()

    def test_join_check_deterministic(self, user, world):
        """Two identical database states produce identical suggestion sets.

        Builds the same scenario twice (two simulations with identical
        creation order for groups, members and ungrouped agents) and asserts
        the (agent name, memory content) suggestion sets are equal. Post-fix
        this is guaranteed by the explicit order_by("id") iteration and the
        all-members average; pre-fix the unordered [:5] slice made both the
        outcome and the members[0] name in the content implementation-defined.
        """

        def _build_scenario(sim):
            group = Group.objects.create(
                simulation=sim, name="Circle of Trust", cohesion=0.7, formed_at_tick=1
            )
            members = [_make_join_agent(sim, f"Member{i}", group=group) for i in range(6)]
            free_agents = [_make_join_agent(sim, f"Free{i}") for i in range(3)]
            for agent in free_agents:
                Relationship.objects.create(
                    agent_from=agent,
                    agent_to=members[0],
                    relation_type="friendship",
                    strength=0.5,
                    sentiment=0.5,
                    since_tick=0,
                )
            return free_agents

        sim1 = Simulation.objects.create(name="DetRun1", seed=42, owner=user)
        sim2 = Simulation.objects.create(name="DetRun2", seed=42, owner=user)
        free1 = _build_scenario(sim1)
        free2 = _build_scenario(sim2)

        _check_join_existing_groups(sim1, tick=10)
        _check_join_existing_groups(sim2, tick=10)

        def _suggestion_set(free_agents):
            return {
                (m.agent.name, m.content)
                for m in Memory.objects.filter(
                    agent__in=free_agents, content__contains="shares my values"
                )
            }

        set1 = _suggestion_set(free1)
        set2 = _suggestion_set(free2)
        assert set1, "fixture must generate at least one suggestion"
        assert set1 == set2

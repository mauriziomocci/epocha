"""Tests for the faction dynamics engine."""

import itertools

import pytest
from django.conf import settings

from epocha.apps.agents import factions as factions_module
from epocha.apps.agents.affinity import compute_affinity
from epocha.apps.agents.factions import (
    _check_dissolution,
    _check_join_existing_groups,
    _check_schism,
    _create_faction,
    _detect_and_propose_factions,
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


@pytest.fixture
def mock_llm(monkeypatch):
    """Force `_generate_faction_identity` onto its deterministic fallback path.

    `_generate_faction_identity` imports `get_llm_client` lazily, inside the
    function body (`from epocha.apps.llm_adapter.client import
    get_llm_client`), to avoid a circular import at module load time (see
    factions.py docstring). That means patching a `factions`-module-level
    name has no effect here -- the patch must target the import's source,
    `epocha.apps.llm_adapter.client.get_llm_client`. The stub's `.complete()`
    raises, which `_generate_faction_identity` already catches (broad except,
    by design: faction creation must never be blocked by LLM unavailability),
    so every call falls through to the caller-supplied fallback name and
    objective. This keeps the atomicity tests below fast, deterministic and
    network-free, and is only needed because `_check_schism` and
    `_create_faction` both call `_generate_faction_identity` before their
    first database write.
    """

    class _FailingLLMClient:
        def complete(self, *args, **kwargs):
            raise RuntimeError("LLM unavailable in test")

    monkeypatch.setattr(
        "epocha.apps.llm_adapter.client.get_llm_client",
        lambda: _FailingLLMClient(),
    )


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


@pytest.mark.django_db
class TestLeadershipDeN1:
    """Round 3 hardening contract for leadership scoring de-N+1 (FR-004).

    Covers SC-002 (constant query budget for compute_legitimacy + succession,
    independent of group size) and SC-003 (exact numeric equivalence between
    the self-fetch and members+context prefetched paths of
    compute_leadership_score).
    """

    def test_leadership_query_budget(self, simulation, world, django_assert_num_queries):
        """update_group_leadership runs on a FIXED query budget, independent of group size.

        Query breakdown (no leadership transition happens -- see fixture
        below, the leader keeps high legitimacy so the election branch
        never runs and the budget below covers only the legitimacy-check
        path):
          1. `group.leader` FK access (fresh Group instance, uncached)
          2. living members fetch inside compute_legitimacy (order_by id)
          3. leadership context -- Relationship query
             (`_build_leadership_context`)
          4. leadership context -- Memory (join-tick) query
        Total: 4, independent of member count.

        Pre-fix this scenario costs O(N): compute_legitimacy's own
        `scores = [(m, compute_leadership_score(m, group, tick)) for m in
        members]` loop calls compute_leadership_score once per member, and
        each call independently refetches `group=group` members plus its
        own Relationship and Memory queries -- three extra queries per
        member.

        The second scenario doubles the member count and asserts the SAME
        budget -- the constant-cost contract of SC-002.
        """

        def _build_legitimate_group(name, member_count):
            group = Group.objects.create(
                simulation=simulation, name=name, cohesion=0.7, formed_at_tick=1
            )
            members = [
                _make_join_agent(simulation, f"{name}M{i}", group=group, wealth=50.0 + i)
                for i in range(member_count)
            ]
            leader = members[0]
            group.leader = leader
            group.save(update_fields=["leader"])
            # Strong positive relationships from the leader to every other
            # member: leader_sentiment stays high (~0.8), keeping legitimacy
            # comfortably above EPOCHA_FACTION_LEGITIMACY_THRESHOLD (0.3)
            # regardless of score_rank, so the election branch never runs
            # and the budget below covers ONLY compute_legitimacy's path.
            for other in members[1:]:
                Relationship.objects.create(
                    agent_from=leader,
                    agent_to=other,
                    relation_type="friendship",
                    strength=0.6,
                    sentiment=0.6,
                    since_tick=0,
                )
            Memory.objects.create(
                agent=leader,
                content=f"I helped found {name}",
                emotional_weight=0.3,
                source_type=Memory.SourceType.DIRECT,
                tick_created=1,
            )
            return group

        group8 = _build_legitimate_group("Order8", 8)
        fresh8 = Group.objects.get(id=group8.id)
        with django_assert_num_queries(4):
            update_group_leadership(fresh8, tick=10)

        group16 = _build_legitimate_group("Order16", 16)
        fresh16 = Group.objects.get(id=group16.id)
        with django_assert_num_queries(4):
            update_group_leadership(fresh16, tick=10)

    def test_leadership_score_equivalence(self, simulation, world):
        """compute_leadership_score's self-fetch and prefetched-context paths agree exactly.

        Heterogeneous fixture: 7 members with distinct wealth/charisma/
        intelligence, a mix of single- and multi-row (both direction, both
        relation_type) Relationship pairs, staggered and tied join-memory
        `tick_created` values, and one member (E6) with NEITHER
        relationships NOR a join memory (exercises both fallback branches:
        internal_sentiment=0.3 and join_tick=tick). For every member, the
        value returned by the no-argument self-fetch path must equal the
        value returned by the members+context prefetched path EXACTLY
        (SC-003), downstream of the FR-011 deterministic tie-break and the
        id-ordered Relationship queries in both compute_leadership_score
        and _build_leadership_context (identical summation order, so
        identical floating-point sums -- not just identical row sets).

        RED today: `members`/`context` are not accepted parameters by
        compute_leadership_score -- TypeError.
        """
        group = Group.objects.create(
            simulation=simulation, name="Round3 Circle", cohesion=0.6, formed_at_tick=1
        )
        wealths = [20.0, 35.0, 50.0, 65.0, 80.0, 95.0, 110.0]
        charismas = [0.9, 0.1, 0.5, 0.3, 0.7, 0.4, 0.6]
        intelligences = [0.2, 0.8, 0.5, 0.7, 0.3, 0.6, 0.4]
        members = [
            _make_join_agent(
                simulation,
                f"E{i}",
                group=group,
                wealth=wealths[i],
                charisma=charismas[i],
                intelligence=intelligences[i],
            )
            for i in range(7)
        ]
        e0, e1, e2, e3, e4, e5, e6 = members

        # Multi-row pair (both directions, different relation_type): both
        # rows must be summed for e0 AND for e1.
        Relationship.objects.create(
            agent_from=e0,
            agent_to=e1,
            relation_type="friendship",
            strength=0.6,
            sentiment=0.5,
            since_tick=0,
        )
        Relationship.objects.create(
            agent_from=e1,
            agent_to=e0,
            relation_type="rivalry",
            strength=0.3,
            sentiment=-0.2,
            since_tick=0,
        )
        Relationship.objects.create(
            agent_from=e0,
            agent_to=e2,
            relation_type="professional",
            strength=0.4,
            sentiment=0.1,
            since_tick=0,
        )
        Relationship.objects.create(
            agent_from=e2,
            agent_to=e3,
            relation_type="friendship",
            strength=0.5,
            sentiment=0.3,
            since_tick=0,
        )
        Relationship.objects.create(
            agent_from=e3,
            agent_to=e4,
            relation_type="distrust",
            strength=0.2,
            sentiment=-0.6,
            since_tick=0,
        )
        Relationship.objects.create(
            agent_from=e4,
            agent_to=e5,
            relation_type="friendship",
            strength=0.7,
            sentiment=0.8,
            since_tick=0,
        )
        Relationship.objects.create(
            agent_from=e5,
            agent_to=e0,
            relation_type="romantic",
            strength=0.5,
            sentiment=0.4,
            since_tick=0,
        )
        # e6 deliberately has NO relationship: exercises the
        # internal_sentiment=0.3 fallback on both paths.

        # Staggered join memories, including a same-agent tie on
        # tick_created (e1) -- ties resolve to the same tick_created value
        # regardless of which tied row wins, so they cannot break
        # equivalence (see _build_leadership_context docstring).
        Memory.objects.create(
            agent=e0,
            content=f"I joined {group.name}",
            emotional_weight=0.3,
            source_type=Memory.SourceType.DIRECT,
            tick_created=1,
        )
        Memory.objects.create(
            agent=e1,
            content=f"I joined {group.name}",
            emotional_weight=0.3,
            source_type=Memory.SourceType.DIRECT,
            tick_created=5,
        )
        Memory.objects.create(
            agent=e1,
            content=f"I truly joined {group.name}",
            emotional_weight=0.3,
            source_type=Memory.SourceType.DIRECT,
            tick_created=5,
        )
        for i, member in enumerate((e2, e3, e4, e5), start=2):
            Memory.objects.create(
                agent=member,
                content=f"I joined {group.name}",
                emotional_weight=0.3,
                source_type=Memory.SourceType.DIRECT,
                tick_created=i,
            )
        # e6 deliberately has NO join memory: exercises the join_tick=tick
        # fallback on both paths.

        tick = 20
        prefetched_members = list(Agent.objects.filter(group=group, is_alive=True).order_by("id"))
        context = factions_module._build_leadership_context(group, prefetched_members)

        for member in members:
            self_fetch_score = compute_leadership_score(member, group, tick)
            prefetched_score = compute_leadership_score(
                member, group, tick, members=prefetched_members, context=context
            )
            assert prefetched_score == self_fetch_score, (
                f"leadership score mismatch for {member.name}: "
                f"self-fetch={self_fetch_score!r} prefetched={prefetched_score!r}"
            )


@pytest.mark.django_db
class TestCreateFactionDeN1:
    """Founder-election de-N+1 and election correctness in _create_faction.

    Coordinator-approved extension of FR-004 to the founder-election loop in
    `_create_faction` (same defect class as the leadership pipeline N+1,
    caught during T012-T014 and escalated per Exhaustive Bug Analysis).
    Covers the constant query budget AND the declared behavior fix that came
    with it: on develop the election ran before the founders' group FK
    bulk-update, scored against the EMPTY new group (every founder 0.0) and
    crowned founders[0] by stable-sort order.
    """

    def test_create_faction_elects_highest_scoring_founder(self, simulation, world, mock_llm):
        """The faction leader is the founder with the highest leadership score.

        Declared behavior fix (audit F1): on develop, `_create_faction`
        ran its election BEFORE `Agent.objects.filter(id__in=founder_ids)
        .update(group=group)`, so `compute_leadership_score`'s self-fetch
        of `group=group` members returned an EMPTY set, every founder
        scored 0.0, and the stable sort crowned founders[0] regardless of
        traits or relationships -- contradicting the function's docstring
        ("assigns the agent with the highest leadership score as leader").
        Post-fix the election is fed `members=founders` plus a leadership
        context, so it operates on the actual founding membership.

        Fixture: the intended winner sits at index 2 (NOT index 0), with
        dominant charisma/intelligence (0.9 vs 0.1), the top wealth rank
        (distinct wealths, no rank ties) and strong positive relationships
        from every other founder (sentiment 0.8). Its score (~0.78) beats
        every other founder (<= ~0.33) by construction, so the expected
        ordering is unambiguous. The assertion targets leader IDENTITY:
        the expected winner is recomputed in-test as the argmax of
        `compute_leadership_score(..., members=founders, context=...)`
        over all founders (post-creation scores equal election-time
        scores: the founding memories created after the election all
        carry tick_created == tick == formed_at_tick, so seniority is 0.0
        on both sides, and relationships are untouched by creation).
        """
        weak_wealths = [10.0, 20.0, 30.0]
        founders = [
            _make_join_agent(
                simulation, f"Weak{i}", wealth=weak_wealths[i], charisma=0.1, intelligence=0.1
            )
            for i in range(2)
        ]
        strong = _make_join_agent(
            simulation, "Strong", wealth=100.0, charisma=0.9, intelligence=0.9
        )
        founders.append(strong)
        founders.append(
            _make_join_agent(
                simulation, "Weak2", wealth=weak_wealths[2], charisma=0.1, intelligence=0.1
            )
        )
        assert founders[2] is strong and founders[0] is not strong
        for weak in founders:
            if weak is strong:
                continue
            Relationship.objects.create(
                agent_from=weak,
                agent_to=strong,
                relation_type="friendship",
                strength=0.5,
                sentiment=0.8,
                since_tick=0,
            )

        tick = 10
        _create_faction(simulation, founders, tick=tick)

        group = Group.objects.get(simulation=simulation)
        recompute_context = factions_module._build_leadership_context(group, founders)
        expected_winner = max(
            founders,
            key=lambda f: compute_leadership_score(
                f, group, tick, members=founders, context=recompute_context
            ),
        )
        assert expected_winner is strong, "fixture must make the strong founder the argmax"
        assert group.leader_id == strong.id, (
            f"leader is {group.leader.name}, expected {strong.name} -- "
            "the election did not pick the highest-scoring founder"
        )
        assert group.leader_id != founders[0].id, (
            "leader must not be founders[0] by position (pre-fix degenerate behavior)"
        )

    def test_create_faction_founder_election_query_budget(
        self, simulation, world, mock_llm, django_assert_num_queries
    ):
        """_create_faction runs on a FIXED query budget, independent of founder count.

        Query breakdown (the whole function runs inside `transaction.atomic`,
        which under pytest-django's outer test transaction compiles to a
        SAVEPOINT / RELEASE SAVEPOINT pair):
           1. SAVEPOINT (atomic entry)
           2. Group INSERT
           3. founder leadership context -- Relationship query
              (`_build_leadership_context`)
           4. founder leadership context -- Memory (join-tick) query
           5. `group.save(update_fields=["leader"])` UPDATE
           6. founders bulk `update(group=group)`
           7. founder memories `bulk_create` INSERT (batched -- required for
              this constant-budget contract; the pre-fix per-founder
              `Memory.objects.create` loop was the second O(N) term in this
              function, alongside the election's per-founder member fetch)
           8. outsiders SELECT (public announcement recipients)
           9. public memories `bulk_create` INSERT
          10. RELEASE SAVEPOINT (atomic exit)
        Total: 10, independent of founder count.

        Pre-fix this costs O(N): the election loop called
        compute_leadership_score once per founder and each call refetched
        `group=group` members (one query per founder -- returning EMPTY,
        see the behavior note in _create_faction), and the founder-memory
        loop issued one INSERT per founder: 18 queries for 6 founders,
        30 for 12.

        A persistent outsider guarantees the public-announcement
        `bulk_create` fires in both scenarios (bulk_create of an empty
        list issues no query); in the second scenario the first faction's
        founders are additional outsiders, which changes row counts but
        not query counts.
        """
        _make_join_agent(simulation, "Bystander")

        founders6 = [_make_join_agent(simulation, f"F6_{i}") for i in range(6)]
        with django_assert_num_queries(10):
            factions_module._create_faction(simulation, founders6, tick=10)

        founders12 = [_make_join_agent(simulation, f"F12_{i}") for i in range(12)]
        with django_assert_num_queries(10):
            factions_module._create_faction(simulation, founders12, tick=10)


@pytest.mark.django_db
class TestDetectClustersQueryBudget:
    """Query budget contract for _detect_and_propose_factions (FR-003, audit F2)."""

    def test_detect_clusters_query_budget(self, simulation, world, django_assert_num_queries):
        """_detect_and_propose_factions runs on a FIXED per-tick query budget.

        Contract chosen (documented per the audit instruction): the budget
        is pinned at the SAME constant for both scenarios by ensuring each
        scenario creates at least one proposal memory -- `bulk_create` of a
        non-empty list is ONE query regardless of how many memories or
        clusters it covers, so the constant holds independent of agent,
        pair and cluster count; only the degenerate no-proposal tick would
        cost one query less (the bulk_create is skipped entirely).

        Query breakdown (5, no transaction wrapper -- proposal memories are
        signals, not one of the four FR-005 mutation paths):
          1. ungrouped candidates fetch (order_by name, id)
          2. affinity context -- Relationship superset query
             (`build_affinity_context`)
          3. affinity context -- Memory (PUBLIC window) query
          4. already-proposed dedup -- ALL recent memories of candidates
             (tick-5 window) in one aggregated query
          5. `bulk_create` of the proposal memories

        Scenario 1: 8 mutually-affine candidates (pairwise 0.54 >= 0.5
        threshold via `_make_join_agent` defaults) plus 2 engineered
        outliers (affinity ~0.18 vs the clusterables; mutually affine with
        each other but only 2 of them, below EPOCHA_FACTION_MIN_MEMBERS=3,
        so they can never cluster) -> one cluster of 8 (the
        MAX_INITIAL_MEMBERS cap). Scenario 2 doubles the clusterable
        population to 16 (at tick 20, so the tick-5 dedup window has
        expired for scenario 1's proposals): the cap splits them into TWO
        clusters of 8 -- same 5 queries, demonstrating independence from
        both candidate count and cluster count.

        Pre-Round-3 (before commit 5ba7bc9) the affinity loop cost
        O(pairs) queries (~3 per compute_affinity call) plus one
        already-proposed exists() per cluster member; this test pins the
        post-fix contract against regression.
        """
        low_traits = {t: 0.1 for t in _BIG_FIVE_TRAITS}

        def _add_clusterables(batch, count):
            return [_make_join_agent(simulation, f"Kin{batch}_{i}") for i in range(count)]

        # Outliers: opposite personality vs the clusterables' empty-dict
        # default (which resolves to 0.5 per trait), different class, high
        # mood, remote wealth quartile, different role -> ~0.18 affinity
        # with every clusterable, well below the 0.5 threshold.
        for i in range(2):
            _make_join_agent(
                simulation,
                f"Loner{i}",
                personality=dict(low_traits),
                social_class="elite",
                mood=0.9,
                wealth=5000.0,
                role="priest",
            )

        _add_clusterables(batch=1, count=8)
        with django_assert_num_queries(5):
            _detect_and_propose_factions(simulation, tick=10)
        assert Memory.objects.filter(content__contains="share common ground").exists(), (
            "scenario 1 must generate at least one proposal (bulk_create must fire)"
        )

        first_run_proposals = Memory.objects.filter(content__contains="share common ground").count()
        _add_clusterables(batch=2, count=8)
        with django_assert_num_queries(5):
            _detect_and_propose_factions(simulation, tick=20)
        assert (
            Memory.objects.filter(content__contains="share common ground").count()
            > first_run_proposals
        ), "scenario 2 must generate new proposals (bulk_create must fire)"


def _make_hostile_subclique(simulation, group, ally_names, rest_names):
    """Build a group with a hostile sub-clique that `_check_schism` detects.

    `ally_names` get mutual sentiment 0.6 (> _ALLY_SENTIMENT_THRESHOLD=0.2)
    among themselves and -0.5 (< _SCHISM_OUTWARD_SENTIMENT_THRESHOLD=-0.2)
    toward every agent in `rest_names`. Only ONE Relationship row per
    unordered pair is needed: `_check_schism._get_sentiment` falls back to
    the reverse-direction key, so the sentiment is symmetric regardless of
    which agent is `agent_from`. This makes the schism detected regardless
    of which of the `ally_names` agents `_check_schism` happens to pick as
    its iteration seed (no explicit `order_by` on `Agent.objects.filter
    (group=group, is_alive=True)` in `_check_schism` -- out of FR-011 scope
    for this branch, unchanged).

    Returns (allies, rest) as lists of Agent instances.
    """
    allies = [_make_join_agent(simulation, n, group=group) for n in ally_names]
    rest = [_make_join_agent(simulation, n, group=group) for n in rest_names]
    for a, b in itertools.combinations(allies, 2):
        Relationship.objects.create(
            agent_from=a,
            agent_to=b,
            relation_type="friendship",
            strength=0.5,
            sentiment=0.6,
            since_tick=0,
        )
    for ally in allies:
        for outsider in rest:
            Relationship.objects.create(
                agent_from=ally,
                agent_to=outsider,
                relation_type="rivalry",
                strength=0.5,
                sentiment=-0.5,
                since_tick=0,
            )
    return allies, rest


@pytest.mark.django_db
class TestAtomicityAndWriteDiscipline:
    """Round 3 hardening contract for transaction.atomic and bulk membership writes.

    Covers FR-005 (per-mutation atomicity across the four group-membership
    write paths) and FR-006 (unified bulk `update()` migration discipline).
    """

    def test_schism_rolls_back_on_failure(self, simulation, world, monkeypatch, mock_llm):
        """An exception after splinter creation and ally migration rolls back everything.

        `_check_schism` has no separate `_elect_new_leader` call on this
        path -- that helper is only used by `update_group_leadership`
        (module-level grep confirms exactly two call sites, both there).
        The step `_check_schism` runs immediately after the splinter Group
        is created and the allies are migrated is the inline splinter
        leader election, via `compute_leadership_score` (factions.py, the
        `splinter_scores = [...]` line right after the ally loop) -- this
        is the equivalent "called after Group creation and ally migration"
        step to fail for this test's purpose. Monkeypatched to raise, it
        simulates a failure mid-mutation.

        RED today (pre-T010): the splinter Group, the ally `Agent.group`
        changes and the ally Memory rows all persist despite the raised
        exception, because the mutation block is not yet wrapped in
        `transaction.atomic`.
        """
        group = Group.objects.create(
            simulation=simulation, name="The Guild", cohesion=0.6, formed_at_tick=1
        )
        allies, rest = _make_hostile_subclique(
            simulation, group, ("Ada", "Bea", "Cleo"), ("Deb", "Eve", "Fay")
        )

        def _raise(*args, **kwargs):
            raise RuntimeError("boom")

        monkeypatch.setattr(factions_module, "compute_leadership_score", _raise)

        with pytest.raises(RuntimeError):
            factions_module._check_schism(group, simulation, tick=10)

        assert not Group.objects.filter(parent_group=group).exists(), (
            "splinter Group persisted despite the exception"
        )
        for member in allies + rest:
            member.refresh_from_db()
            assert member.group_id == group.id, f"{member.name} changed group despite the exception"
        assert not Memory.objects.filter(content__icontains="I left").exists(), (
            "ally migration Memory persisted despite the exception"
        )
        assert not Memory.objects.filter(content__icontains="has split from").exists(), (
            "remaining-member Memory persisted despite the exception"
        )
        group.refresh_from_db()
        assert group.cohesion == pytest.approx(0.6), (
            "parent group cohesion decrement persisted despite the exception"
        )

    def test_create_faction_rolls_back_on_failure(self, simulation, world, monkeypatch, mock_llm):
        """An exception in the trailing public-memory bulk_create rolls back the whole faction.

        Monkeypatches `Memory.objects.bulk_create` to raise on its SECOND
        invocation: since the FR-004 scope extension batched the founder
        memories, `_create_faction` calls bulk_create twice -- founder
        memories first, then the public announcement to non-members, which
        remains the LAST write the function performs. Failing on that very
        last statement (while letting the founder-memory batch through) is
        the strongest probe of "whole function atomic" (FR-005, "l'intera
        funzione"): if the atomic block truly wraps the entire function,
        even a failure here must undo every earlier write, founder
        memories included.

        RED today (pre-T010): the Group, the founders' `Agent.group`
        change and their Memory rows all persist despite the raised
        exception.
        """
        founders = [_make_join_agent(simulation, n) for n in ("Gino", "Hana", "Ivo")]
        outsider = _make_join_agent(simulation, "Outsider")

        real_bulk_create = Memory.objects.bulk_create
        calls = {"count": 0}

        def _raise_on_second(*args, **kwargs):
            calls["count"] += 1
            if calls["count"] >= 2:
                raise RuntimeError("boom")
            return real_bulk_create(*args, **kwargs)

        monkeypatch.setattr(Memory.objects, "bulk_create", _raise_on_second)

        with pytest.raises(RuntimeError):
            factions_module._create_faction(simulation, founders, tick=10)

        assert not Group.objects.filter(simulation=simulation).exists(), (
            "faction Group persisted despite the exception"
        )
        for founder in founders:
            founder.refresh_from_db()
            assert founder.group_id is None, f"{founder.name} changed group despite the exception"
        assert not Memory.objects.filter(agent__in=founders).exists(), (
            "founder Memory rows persisted despite the exception"
        )
        assert not Memory.objects.filter(agent=outsider).exists(), (
            "public announcement Memory persisted despite the exception"
        )

    def test_dissolution_atomic_and_bulk(self, simulation, world, django_assert_num_queries):
        """Dissolution moves every member out via a single bulk update, pinned by budget.

        `_check_dissolution` already used `Agent.objects.filter(group=group)
        .update(group=None)` (bulk) before this branch of work -- FR-006
        only needed to extend the SAME discipline to the other three
        mutation paths, not to change this one. This test protects that
        pre-existing bulk path through the FR-006 unification and pins the
        query budget so a future regression back to a per-agent loop is
        caught.

        Query breakdown for 4 living members, verified with `-v` query dump
        (T010 wraps the block in `transaction.atomic`, which under
        pytest-django's own outer test-transaction wrapper compiles down to
        a SAVEPOINT / RELEASE SAVEPOINT pair rather than a real BEGIN --
        that pair is the +2 relative to the 6 underlying statements):
          1. SAVEPOINT (transaction.atomic entry)
          2. living members fetch (needed for the per-member Memory content)
          3. bulk `Agent.objects.filter(group=group).update(group=None)`
          4-7. one `Memory.objects.create()` per member -- FR-005/FR-006 do
               NOT require batching these into `bulk_create`; only the
               membership write discipline is unified across the four
               paths (see spec FR-005/FR-006, and module docstring "Write
               discipline").
          8. RELEASE SAVEPOINT (transaction.atomic exit)
        Total: 8 queries for 4 members. The 6 non-savepoint statements are
        unchanged from before T010 (dissolution already used bulk
        `update()`); this test protects that pre-existing bulk path through
        the FR-006 unification of the other three functions.
        """
        group = Group.objects.create(
            simulation=simulation, name="Fading Circle", cohesion=0.1, formed_at_tick=1
        )
        members = [_make_join_agent(simulation, n, group=group) for n in ("A", "B", "C", "D")]

        with django_assert_num_queries(8):
            _check_dissolution(group, tick=10)

        for member in members:
            member.refresh_from_db()
            assert member.group_id is None

    def test_membership_write_discipline(self, simulation, world, mock_llm):
        """Post-schism and post-creation, every moved agent's group FK is correct.

        Runs a successful schism (no injected failure) and a successful
        faction creation, then reads each moved agent back from the
        database with `refresh_from_db()`. This is the post-fix contract
        of FR-006: the bulk `update()` path must produce EXACTLY the same
        end state the old per-agent `.save(update_fields=["group"])` loop
        produced -- only in fewer queries. Numeric/behavioral outcome is
        unaffected by which write mechanism moves the rows.
        """
        group = Group.objects.create(
            simulation=simulation, name="The Order", cohesion=0.6, formed_at_tick=1
        )
        allies, rest = _make_hostile_subclique(
            simulation, group, ("Nia", "Omar", "Pia"), ("Quin", "Rex", "Sia")
        )

        _check_schism(group, simulation, tick=10)

        splinter = Group.objects.get(parent_group=group)
        for ally in allies:
            ally.refresh_from_db()
            assert ally.group_id == splinter.id
        for outsider in rest:
            outsider.refresh_from_db()
            assert outsider.group_id == group.id

        existing_group_ids = set(
            Group.objects.filter(simulation=simulation).values_list("id", flat=True)
        )
        founders = [_make_join_agent(simulation, n) for n in ("Tao", "Uma", "Vik")]
        _create_faction(simulation, founders, tick=10)

        new_group = (
            Group.objects.filter(simulation=simulation).exclude(id__in=existing_group_ids).get()
        )
        for founder in founders:
            founder.refresh_from_db()
            assert founder.group_id == new_group.id

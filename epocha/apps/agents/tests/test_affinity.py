"""Tests for agent pairwise affinity calculation."""

import pytest

from epocha.apps.agents.affinity import compute_affinity
from epocha.apps.agents.models import Agent, Memory, Relationship
from epocha.apps.simulation.models import Simulation
from epocha.apps.users.models import User
from epocha.apps.world.models import World


@pytest.fixture
def user(db):
    return User.objects.create_user(email="aff@epocha.dev", username="afftest", password="pass123")


@pytest.fixture
def simulation(user):
    return Simulation.objects.create(name="AffTest", seed=42, owner=user)


@pytest.fixture
def world(simulation):
    return World.objects.create(simulation=simulation)


@pytest.fixture
def marco(simulation):
    return Agent.objects.create(
        simulation=simulation,
        name="Marco",
        role="blacksmith",
        social_class="working",
        mood=0.3,
        wealth=30.0,
        personality={
            "openness": 0.8,
            "conscientiousness": 0.6,
            "extraversion": 0.4,
            "agreeableness": 0.3,
            "neuroticism": 0.7,
        },
    )


@pytest.fixture
def elena(simulation):
    return Agent.objects.create(
        simulation=simulation,
        name="Elena",
        role="farmer",
        social_class="working",
        mood=0.3,
        wealth=35.0,
        personality={
            "openness": 0.7,
            "conscientiousness": 0.5,
            "extraversion": 0.5,
            "agreeableness": 0.4,
            "neuroticism": 0.6,
        },
    )


@pytest.fixture
def carlo(simulation):
    return Agent.objects.create(
        simulation=simulation,
        name="Carlo",
        role="priest",
        social_class="middle",
        mood=0.7,
        wealth=80.0,
        personality={
            "openness": 0.2,
            "conscientiousness": 0.9,
            "extraversion": 0.3,
            "agreeableness": 0.8,
            "neuroticism": 0.1,
        },
    )


@pytest.mark.django_db
class TestComputeAffinity:
    def test_similar_agents_high_affinity(self, simulation, world, marco, elena):
        """Agents with similar personality, same class, both low mood = high affinity."""
        Relationship.objects.create(
            agent_from=marco,
            agent_to=elena,
            relation_type="friendship",
            strength=0.7,
            sentiment=0.5,
            since_tick=0,
        )
        score = compute_affinity(marco, elena, tick=10)
        assert score > 0.5

    def test_dissimilar_agents_low_affinity(self, simulation, world, marco, carlo):
        """Agents with very different personality, different class, different mood."""
        score = compute_affinity(marco, carlo, tick=10)
        assert score < 0.4

    def test_no_relationship_zero_relationship_score(self, simulation, world, marco, elena):
        """Without a relationship, the relationship component is 0."""
        score_no_rel = compute_affinity(marco, elena, tick=10)
        Relationship.objects.create(
            agent_from=marco,
            agent_to=elena,
            relation_type="friendship",
            strength=0.8,
            sentiment=0.6,
            since_tick=0,
        )
        score_with_rel = compute_affinity(marco, elena, tick=10)
        assert score_with_rel > score_no_rel

    def test_shared_public_memory_increases_affinity(self, simulation, world, marco, elena):
        """Agents sharing a recent public memory have higher affinity."""
        score_before = compute_affinity(marco, elena, tick=10)
        Memory.objects.create(
            agent=marco,
            content="Plague outbreak: terrible plague",
            emotional_weight=0.9,
            source_type="public",
            tick_created=8,
        )
        Memory.objects.create(
            agent=elena,
            content="Plague outbreak: terrible plague",
            emotional_weight=0.9,
            source_type="public",
            tick_created=8,
        )
        score_after = compute_affinity(marco, elena, tick=10)
        assert score_after > score_before

    def test_same_role_increases_affinity(self, simulation, world, marco):
        """Two agents with the same role get a small boost."""
        marco2 = Agent.objects.create(
            simulation=simulation,
            name="Luigi",
            role="blacksmith",
            social_class="working",
            mood=0.5,
            wealth=40.0,
            personality={
                "openness": 0.3,
                "conscientiousness": 0.3,
                "extraversion": 0.3,
                "agreeableness": 0.3,
                "neuroticism": 0.3,
            },
        )
        score = compute_affinity(marco, marco2, tick=10)
        marco2.role = "farmer"
        marco2.save(update_fields=["role"])
        score_diff_role = compute_affinity(marco, marco2, tick=10)
        assert score > score_diff_role

    def test_affinity_is_symmetric(self, simulation, world, marco, elena):
        """affinity(A, B) == affinity(B, A)."""
        Relationship.objects.create(
            agent_from=marco,
            agent_to=elena,
            relation_type="friendship",
            strength=0.6,
            sentiment=0.4,
            since_tick=0,
        )
        score_ab = compute_affinity(marco, elena, tick=10)
        score_ba = compute_affinity(elena, marco, tick=10)
        assert abs(score_ab - score_ba) < 0.01

    def test_affinity_range_zero_to_one(self, simulation, world, marco, carlo):
        """Affinity score must be between 0.0 and 1.0."""
        score = compute_affinity(marco, carlo, tick=10)
        assert 0.0 <= score <= 1.0

    def test_relationship_score_tie_break_deterministic(self, simulation, world, marco, elena):
        """On a relationship-strength tie, the LOWEST-id relationship must win.

        Round 3 hardening, FR-011. Before the fix, `_relationship_score`
        falls back to `.order_by("-strength").first()` with no secondary
        key on a tie, so which of two equal-strength rows Postgres returns
        is implementation-defined (no ORDER BY guarantee). This test builds
        two relationships between the same pair with equal strength but
        opposite sentiment, so picking the wrong row produces a visibly
        different score (0.7 expected from the low-id row vs 0.25 from the
        high-id row) and asserts the score matches the low-id row exactly.

        Note: on a small, freshly-inserted table, Postgres's default scan
        order often coincides with insertion order, so this test MAY already
        pass before the fix by coincidence -- that is acceptable for this
        test only (see task T002). The guarantee of a stable, always-correct
        outcome exists only after `.order_by("-strength", "id")` is added.
        """
        from epocha.apps.agents.affinity import (
            _W_CIRCUMSTANCE,
            _W_PERSONALITY,
            _W_RELATIONSHIP,
            _circumstance_score,
            _personality_similarity,
        )

        rel_low = Relationship.objects.create(
            agent_from=marco,
            agent_to=elena,
            relation_type="friendship",
            strength=0.5,
            sentiment=0.9,
            since_tick=0,
        )
        rel_high = Relationship.objects.create(
            agent_from=marco,
            agent_to=elena,
            relation_type="rivalry",
            strength=0.5,
            sentiment=-0.9,
            since_tick=0,
        )
        assert rel_low.id < rel_high.id

        expected_relationship = (rel_low.strength + max(0.0, rel_low.sentiment)) / 2.0
        expected_personality = _personality_similarity(marco.personality, elena.personality)
        expected_circumstance = _circumstance_score(marco, elena, tick=10)
        expected_score = max(
            0.0,
            min(
                1.0,
                _W_PERSONALITY * expected_personality
                + _W_RELATIONSHIP * expected_relationship
                + _W_CIRCUMSTANCE * expected_circumstance,
            ),
        )

        score_first_call = compute_affinity(marco, elena, tick=10)
        score_second_call = compute_affinity(marco, elena, tick=10)

        assert score_first_call == score_second_call
        assert score_first_call == expected_score


@pytest.mark.django_db
class TestBuildAffinityContext:
    """Equivalence and query-budget guarantees for the prefetched affinity context.

    `build_affinity_context` (Round 3 hardening, FR-001) performs the same
    DB reads that the non-batched path performs per pair, aggregated into
    two queries regardless of how many agents or pairs are involved. Every
    numeric result must be identical to the non-batched path (SC-003), which
    requires the deterministic tie-break of FR-011 to be in place on BOTH
    paths -- otherwise a tie has no single correct answer to compare
    against.
    """

    def test_affinity_context_equivalence(self, simulation, world, marco, elena, carlo):
        """compute_affinity(a, b, tick, context=ctx) must equal
        compute_affinity(a, b, tick) exactly, for every (a, b) pair across
        agents_a x agents_b, covering: a relationship-strength tie, a
        relationship stored in the REVERSE direction, a pair with no
        relationship at all, and public memories that fall inside/outside
        the shared-memory window or fail the source_type/is_active filters.

        RED today: `build_affinity_context` does not exist yet -- the local
        import below raises ImportError. Once it exists but before
        `compute_affinity` gains its `context` kwarg, calling with
        `context=ctx` would instead raise TypeError. Either failure mode is
        the expected red for this test.
        """
        luigi = Agent.objects.create(
            simulation=simulation,
            name="Luigi",
            role="mason",
            social_class="working",
            mood=0.6,
            wealth=45.0,
            personality={
                "openness": 0.4,
                "conscientiousness": 0.4,
                "extraversion": 0.6,
                "agreeableness": 0.5,
                "neuroticism": 0.5,
            },
        )

        # Tie case: two relationships marco->elena, equal strength, opposite
        # sentiment (same shape as test_relationship_score_tie_break_deterministic).
        Relationship.objects.create(
            agent_from=marco,
            agent_to=elena,
            relation_type="friendship",
            strength=0.5,
            sentiment=0.6,
            since_tick=0,
        )
        Relationship.objects.create(
            agent_from=marco,
            agent_to=elena,
            relation_type="rivalry",
            strength=0.5,
            sentiment=-0.6,
            since_tick=0,
        )

        # Reverse-direction pair: relationship stored carlo->marco; must
        # still resolve for compute_affinity(marco, carlo, ...).
        Relationship.objects.create(
            agent_from=carlo,
            agent_to=marco,
            relation_type="professional",
            strength=0.7,
            sentiment=0.3,
            since_tick=0,
        )

        # marco/luigi: no relationship at all (baseline -- relationship
        # component must be 0.0 on both paths).

        tick = 30  # window = tick - 10 = 20
        # Shared public memory INSIDE the window: counted on both paths.
        Memory.objects.create(
            agent=marco,
            content="Shared crisis A",
            source_type=Memory.SourceType.PUBLIC,
            is_active=True,
            tick_created=25,
        )
        Memory.objects.create(
            agent=elena,
            content="Shared crisis A",
            source_type=Memory.SourceType.PUBLIC,
            is_active=True,
            tick_created=22,
        )
        # Same content but OUTSIDE the window: must not count on either path.
        Memory.objects.create(
            agent=marco,
            content="Old public",
            source_type=Memory.SourceType.PUBLIC,
            is_active=True,
            tick_created=5,
        )
        Memory.objects.create(
            agent=elena,
            content="Old public",
            source_type=Memory.SourceType.PUBLIC,
            is_active=True,
            tick_created=5,
        )
        # Same content but INACTIVE (faded): must not count on either path.
        Memory.objects.create(
            agent=marco,
            content="Inactive public",
            source_type=Memory.SourceType.PUBLIC,
            is_active=False,
            tick_created=28,
        )
        Memory.objects.create(
            agent=elena,
            content="Inactive public",
            source_type=Memory.SourceType.PUBLIC,
            is_active=False,
            tick_created=28,
        )
        # Same content but non-PUBLIC source: must not count on either path.
        Memory.objects.create(
            agent=marco,
            content="Direct experience",
            source_type=Memory.SourceType.DIRECT,
            is_active=True,
            tick_created=28,
        )
        Memory.objects.create(
            agent=elena,
            content="Direct experience",
            source_type=Memory.SourceType.DIRECT,
            is_active=True,
            tick_created=28,
        )

        from epocha.apps.agents.affinity import build_affinity_context

        agents_a = [marco]
        agents_b = [elena, carlo, luigi]
        ctx = build_affinity_context(agents_a, agents_b, tick)

        for a in agents_a:
            for b in agents_b:
                score_context = compute_affinity(a, b, tick, context=ctx)
                score_plain = compute_affinity(a, b, tick)
                assert score_context == score_plain, (
                    f"context/non-context mismatch for pair ({a.name}, {b.name})"
                )

    def test_affinity_context_query_budget(self, simulation, world, django_assert_num_queries):
        """build_affinity_context costs a FIXED number of queries regardless
        of how many agents/pairs it covers, and evaluating compute_affinity
        through the context afterwards costs zero queries.

        Query breakdown for build_affinity_context (2 queries total,
        independent of set size):
          1. Relationship -- one query over
             `agent_from_id__in=ids, agent_to_id__in=ids`, covering both
             directions and every relation_type for the union of agents_a
             and agents_b (superset fetch).
          2. Memory -- one query over `agent_id__in=ids` with
             `source_type=PUBLIC, is_active=True, tick_created__gte=tick-10`
             for the same union.

        RED today: `build_affinity_context` does not exist (ImportError on
        the local import below).
        """
        from epocha.apps.agents.affinity import build_affinity_context

        agents_a = [
            Agent.objects.create(simulation=simulation, name=f"CandidateA{i}") for i in range(3)
        ]
        agents_b = [
            Agent.objects.create(simulation=simulation, name=f"MemberB{i}") for i in range(5)
        ]

        with django_assert_num_queries(2):
            ctx = build_affinity_context(agents_a, agents_b, tick=10)

        with django_assert_num_queries(0):
            for a in agents_a:
                for b in agents_b:
                    compute_affinity(a, b, tick=10, context=ctx)

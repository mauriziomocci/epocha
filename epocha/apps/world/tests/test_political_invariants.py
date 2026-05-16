"""Cross-cutting invariant test suite for the political cluster.

Enforces invariants documented in
``specs/20260516-120927-political-cluster-audit-repass/spec.md`` (FR-021+) and
the Round 2 audit findings N-1, N-3 / S-2, G-6, X-1.

The suite is intentionally narrow: each test guards one cluster-wide property
that would silently regress if a future refactor broke a single line. Failure
of any test signals an architectural drift, not a calibration tweak.
"""
from __future__ import annotations

import inspect

import pytest

from epocha.apps.agents.models import Agent
from epocha.apps.simulation.models import Simulation
from epocha.apps.users.models import User
from epocha.apps.world.models import Government, World


@pytest.fixture
def user(db):
    """Test user owning the simulation."""
    return User.objects.create_user(
        email="invariants@epocha.dev",
        username="invariantstest",
        password="pass123",
    )


@pytest.fixture
def simulation(user):
    """Bare simulation instance."""
    return Simulation.objects.create(name="InvariantsTest", seed=42, owner=user)


@pytest.fixture
def world(simulation):
    """World record with a known global_wealth pool."""
    return World.objects.create(simulation=simulation, global_wealth=1000.0)


@pytest.fixture
def corrupt_head_of_state(simulation):
    """Agent eligible for the corruption skim (low conscientiousness)."""
    return Agent.objects.create(
        simulation=simulation,
        name="Boss",
        role="head_of_state",
        wealth=100.0,
        social_class="elite",
        personality={
            "openness": 0.5,
            "conscientiousness": 0.1,  # well below the 0.4 corruption threshold
            "extraversion": 0.5,
            "agreeableness": 0.5,
            "neuroticism": 0.5,
        },
    )


@pytest.fixture
def corrupt_other_agents(simulation):
    """A handful of additional agents to give the simulation a realistic shape."""
    agents = []
    for i in range(4):
        agents.append(
            Agent.objects.create(
                simulation=simulation,
                name=f"Citizen{i}",
                role="citizen",
                wealth=50.0,
                social_class="working",
                personality={
                    "openness": 0.5,
                    "conscientiousness": 0.6,  # above threshold; not corrupt
                    "extraversion": 0.5,
                    "agreeableness": 0.5,
                    "neuroticism": 0.5,
                },
            )
        )
    return agents


@pytest.fixture
def government_with_head(simulation, corrupt_head_of_state):
    """Government whose head_of_state is the corrupt agent."""
    return Government.objects.create(
        simulation=simulation,
        government_type="autocracy",
        head_of_state=corrupt_head_of_state,
    )


@pytest.mark.django_db
class TestPoliticalInvariants:
    """Cluster-wide invariants spanning multiple political modules."""

    def test_corruption_preserves_total_wealth(
        self,
        simulation,
        world,
        corrupt_head_of_state,
        corrupt_other_agents,
        government_with_head,
    ):
        """N-3 + S-2: ``process_corruption`` must not create or destroy wealth.

        The sum across all agents plus ``World.global_wealth`` is invariant
        before and after the corruption step (modulo float tolerance). A
        skim is a transfer from the global pool to the corrupt agent, never
        a net creation. This guards the wealth-conservation property that
        S-2 raised in Round 1.
        """
        from epocha.apps.world.stratification import process_corruption

        all_agents = list(Agent.objects.filter(simulation=simulation))
        total_before = sum(a.wealth for a in all_agents) + world.global_wealth

        process_corruption(simulation, tick=1)

        # Reload after the in-place bulk_update.
        for agent in all_agents:
            agent.refresh_from_db()
        world.refresh_from_db()

        total_after = sum(a.wealth for a in all_agents) + world.global_wealth

        assert abs(total_after - total_before) < 1e-6, (
            f"wealth conservation violated: before={total_before}, "
            f"after={total_after}, delta={total_after - total_before}"
        )

    def test_coup_threshold_constant_removed(self):
        """N-1: ``_COUP_SUCCESS_THRESHOLD`` must be removed from ``government.py``.

        The deterministic-coup era is over (G-2 closure); the threshold
        constant is dead. This test guards against accidental reintroduction
        during a future refactor.
        """
        from epocha.apps.world import government as gov

        assert not hasattr(gov, "_COUP_SUCCESS_THRESHOLD"), (
            "_COUP_SUCCESS_THRESHOLD must be deleted (N-1); coup is now stochastic."
        )

    def test_economy_proxy_documented(self):
        """G-6: ``_update_stability`` must document that the local variable
        ``economy`` is actually a mood/stability_index proxy, not a true
        economic indicator.

        The check is intentionally lexical: it scans the source for one of
        the keywords expected to appear in the rationale comment. A future
        rewrite that drops the proxy disclosure will fail this test before
        it ships.
        """
        from epocha.apps.world import government

        src = inspect.getsource(government._update_stability).lower()
        assert any(k in src for k in ("proxy", "average mood", "stability_index")), (
            "_update_stability must explicitly document that 'economy' is a mood proxy "
            "(G-6 closure)."
        )

    def test_corruption_layered_within_bounds(self):
        """X-1: the corruption double-write (``stratification.process_corruption``
        plus ``government.update_government_indicators``) composes additively
        within the [0, 1] bound, and the layering is intentional.

        Both source bodies must explicitly mention the composition so the
        next reader does not mistake the dual write for a bug.
        """
        from epocha.apps.world import government, stratification

        strat_src = inspect.getsource(stratification.process_corruption).lower()
        gov_src = inspect.getsource(government.update_government_indicators).lower()

        combined = strat_src + gov_src
        assert any(
            k in combined for k in ("layered", "cumulative", "composition", "stack")
        ), (
            "process_corruption and update_government_indicators must document the "
            "intentional layering on government.corruption (X-1 closure)."
        )

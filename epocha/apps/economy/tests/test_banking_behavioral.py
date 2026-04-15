"""Tests for dynamic deposits and banking concern broadcast.

Spec 2 Part 3: total_deposits is recalculated each tick as the sum
of all agent cash. Banking concern memories are created when
confidence drops below 0.5 (Diamond & Dybvig 1983).
"""

import pytest

from epocha.apps.agents.models import Agent, Memory
from epocha.apps.economy.banking import (
    broadcast_banking_concern,
    recalculate_deposits,
)
from epocha.apps.economy.initialization import initialize_economy
from epocha.apps.economy.models import AgentInventory, BankingState
from epocha.apps.simulation.models import Simulation
from epocha.apps.users.models import User
from epocha.apps.world.models import World, Zone


@pytest.fixture
def banking_sim(db):
    """Create a simulation with economy and multiple agents."""
    user = User.objects.create_user(
        email="banking@epocha.dev", username="bankuser", password="pass1234",
    )
    sim = Simulation.objects.create(name="bank_test", seed=42, owner=user, config={})
    world = World.objects.create(
        simulation=sim,
        stability_index=0.8,
    )
    zone = Zone.objects.create(world=world, name="London", zone_type="urban")
    agents = []
    for name in ["Alice", "Bob", "Charlie", "Diana"]:
        agents.append(
            Agent.objects.create(
                simulation=sim,
                name=name,
                role="merchant",
                personality={"neuroticism": 0.5},
                zone=zone,
                wealth=100.0,
                mood=0.5,
                health=1.0,
            )
        )
    initialize_economy(sim, "pre_industrial")
    sim.refresh_from_db()
    return sim, agents, zone


@pytest.mark.django_db
class TestRecalculateDeposits:
    def test_deposits_equal_total_agent_cash(self, banking_sim):
        sim, agents, zone = banking_sim
        total_cash = 0.0
        for agent in agents:
            agent.refresh_from_db()
            try:
                inv = agent.inventory
                total_cash += sum(inv.cash.values())
            except AgentInventory.DoesNotExist:
                pass

        recalculate_deposits(sim)
        bs = BankingState.objects.get(simulation=sim)
        assert abs(bs.total_deposits - total_cash) < 0.01

    def test_deposits_update_after_cash_change(self, banking_sim):
        sim, agents, zone = banking_sim
        inv = agents[0].inventory
        inv.cash["LVR"] = inv.cash.get("LVR", 0.0) + 500.0
        inv.save(update_fields=["cash"])

        recalculate_deposits(sim)
        bs = BankingState.objects.get(simulation=sim)

        total_cash = 0.0
        for agent in agents:
            agent.refresh_from_db()
            try:
                agent_inv = agent.inventory
                total_cash += sum(agent_inv.cash.values())
            except AgentInventory.DoesNotExist:
                pass

        assert abs(bs.total_deposits - total_cash) < 0.01


@pytest.mark.django_db
class TestBroadcastBankingConcern:
    def test_broadcast_when_confidence_low(self, banking_sim):
        sim, agents, zone = banking_sim
        bs = BankingState.objects.get(simulation=sim)
        bs.confidence_index = 0.3
        bs.save()

        broadcast_banking_concern(sim, tick=5)
        concern_count = Memory.objects.filter(
            agent__simulation=sim,
            content__contains="banking system",
        ).count()
        assert concern_count > 0
        assert concern_count <= len(agents)

    def test_no_broadcast_when_confidence_high(self, banking_sim):
        sim, agents, zone = banking_sim
        bs = BankingState.objects.get(simulation=sim)
        bs.confidence_index = 0.8
        bs.save()

        broadcast_banking_concern(sim, tick=5)
        concern_count = Memory.objects.filter(
            agent__simulation=sim,
            content__contains="banking system",
        ).count()
        assert concern_count == 0

    def test_broadcast_regardless_of_solvency(self, banking_sim):
        """Diamond & Dybvig (1983): fear triggers runs, not actual insolvency."""
        sim, agents, zone = banking_sim
        bs = BankingState.objects.get(simulation=sim)
        bs.confidence_index = 0.3
        bs.is_solvent = True
        bs.save()

        broadcast_banking_concern(sim, tick=5)
        concern_count = Memory.objects.filter(
            agent__simulation=sim,
            content__contains="banking system",
        ).count()
        assert concern_count > 0

    def test_dedup_prevents_spam(self, banking_sim):
        """An agent who already received a concern memory within the dedup
        window (3 ticks) should not receive another one."""
        sim, agents, zone = banking_sim
        bs = BankingState.objects.get(simulation=sim)
        bs.confidence_index = 0.3
        bs.save()

        # Manually create a concern memory for ALL agents at tick 5
        # so the dedup check will prevent any new memories at tick 6.
        for agent in agents:
            Memory.objects.create(
                agent=agent,
                content="The banking system is under stress. Some depositors "
                        "are worried about the safety of their savings.",
                emotional_weight=0.6,
                source_type="public",
                tick_created=5,
            )
        count_before = Memory.objects.filter(
            agent__simulation=sim,
            content__contains="banking system",
        ).count()

        broadcast_banking_concern(sim, tick=6)
        count_after = Memory.objects.filter(
            agent__simulation=sim,
            content__contains="banking system",
        ).count()
        # No new memories created because all agents already have one
        assert count_after == count_before

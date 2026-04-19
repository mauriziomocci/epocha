"""Unit tests for the demography models and Agent extensions."""
from __future__ import annotations

import pytest
from django.contrib.gis.geos import Point, Polygon

from epocha.apps.agents.models import Agent
from epocha.apps.demography.models import (
    AgentFertilityState,
    Couple,
    DemographyEvent,
    PopulationSnapshot,
)
from epocha.apps.simulation.models import Simulation
from epocha.apps.users.models import User
from epocha.apps.world.models import World, Zone


@pytest.fixture
def sim_with_zone(db):
    user = User.objects.create_user(
        email="demo@epocha.dev", username="demouser", password="pass1234",
    )
    sim = Simulation.objects.create(
        name="DemographyTest", seed=42, owner=user, current_tick=0,
    )
    world = World.objects.create(simulation=sim, stability_index=0.7)
    zone = Zone.objects.create(
        world=world, name="TestZone", zone_type="commercial",
        boundary=Polygon.from_bbox((0, 0, 100, 100)),
        center=Point(50, 50),
    )
    return sim, zone


@pytest.mark.django_db
def test_agent_birth_tick_field(sim_with_zone):
    sim, zone = sim_with_zone
    agent = Agent.objects.create(
        simulation=sim, name="A", role="farmer",
        zone=zone, location=Point(50, 50),
        health=1.0, wealth=0.0, age=30, birth_tick=0,
    )
    assert agent.birth_tick == 0
    assert agent.death_tick is None


@pytest.mark.django_db
def test_agent_other_parent_relation(sim_with_zone):
    sim, zone = sim_with_zone
    parent = Agent.objects.create(
        simulation=sim, name="P", role="farmer", zone=zone,
        location=Point(50, 50), health=1.0, age=40, birth_tick=0,
    )
    other = Agent.objects.create(
        simulation=sim, name="O", role="farmer", zone=zone,
        location=Point(50, 50), health=1.0, age=42, birth_tick=0,
    )
    child = Agent.objects.create(
        simulation=sim, name="C", role="farmer", zone=zone,
        location=Point(50, 50), health=1.0, age=5, birth_tick=25,
        parent_agent=parent, other_parent_agent=other,
    )
    assert child.other_parent_agent_id == other.id
    assert list(parent.children.all()) == [child]
    assert list(other.other_parent_children.all()) == [child]


@pytest.mark.django_db
def test_couple_creation_and_snapshot(sim_with_zone):
    sim, zone = sim_with_zone
    a = Agent.objects.create(
        simulation=sim, name="A", role="weaver", zone=zone,
        location=Point(50, 50), health=1.0, age=25, birth_tick=0,
    )
    b = Agent.objects.create(
        simulation=sim, name="B", role="merchant", zone=zone,
        location=Point(50, 50), health=1.0, age=28, birth_tick=0,
    )
    couple = Couple.objects.create(
        simulation=sim, agent_a=a, agent_b=b,
        formed_at_tick=1, couple_type=Couple.CoupleType.MONOGAMOUS,
    )
    assert couple.dissolved_at_tick is None
    couple.agent_a_name_snapshot = a.name
    couple.agent_a = None
    couple.dissolved_at_tick = 5
    couple.dissolution_reason = Couple.DissolutionReason.DEATH
    couple.save()
    couple.refresh_from_db()
    assert couple.agent_a_name_snapshot == "A"
    assert couple.agent_a is None


@pytest.mark.django_db
def test_demography_event_payload(sim_with_zone):
    sim, zone = sim_with_zone
    agent = Agent.objects.create(
        simulation=sim, name="X", role="farmer", zone=zone,
        location=Point(50, 50), health=1.0, age=30, birth_tick=0,
    )
    event = DemographyEvent.objects.create(
        simulation=sim, tick=5,
        event_type=DemographyEvent.EventType.BIRTH,
        primary_agent=agent,
        payload={"newborn_id": 42, "zone_id": zone.id},
    )
    assert event.payload["newborn_id"] == 42


@pytest.mark.django_db
def test_population_snapshot_unique(sim_with_zone):
    sim, _ = sim_with_zone
    PopulationSnapshot.objects.create(
        simulation=sim, tick=1, total_alive=10, sex_ratio=1.05, avg_age=25.0,
    )
    with pytest.raises(Exception):
        PopulationSnapshot.objects.create(
            simulation=sim, tick=1, total_alive=10, sex_ratio=1.05, avg_age=25.0,
        )


@pytest.mark.django_db
def test_agent_fertility_state_one_to_one(sim_with_zone):
    sim, zone = sim_with_zone
    agent = Agent.objects.create(
        simulation=sim, name="F", role="farmer", zone=zone,
        location=Point(50, 50), health=1.0, age=30, birth_tick=0,
    )
    state = AgentFertilityState.objects.create(agent=agent, avoid_conception_flag_tick=5)
    assert agent.fertility_state == state

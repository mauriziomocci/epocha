"""The demography block, seen from the tick loop that now calls it.

The largest gap this project carried was a complete, audited scientific model
that never ran: five demography modules and a tick loop that called none of
them. These tests cover the seam -- where the block hangs in the tick, and
that a simulation which never opted in is left exactly as it was.
"""

from __future__ import annotations

import pytest
from django.contrib.gis.geos import Point, Polygon

from epocha.apps.agents.models import Agent
from epocha.apps.demography import orchestrator as orchestrator_module
from epocha.apps.demography.models import DemographyEvent
from epocha.apps.simulation.models import Simulation
from epocha.apps.simulation.tasks import run_simulation_loop
from epocha.apps.users.models import User
from epocha.apps.world.models import Government, World, Zone

TICKS_PER_YEAR = 365.0


def _simulation(db_marker, *, demography: bool):
    user = User.objects.create_user(
        email=f"wiring{demography}@epocha.dev",
        username=f"wiringuser{demography}",
        password="pass1234",
    )
    config = {"demography_enabled": True} if demography else {}
    sim = Simulation.objects.create(
        name=f"WiringTest{demography}",
        seed=2026,
        owner=user,
        current_tick=50,
        status=Simulation.Status.RUNNING,
        config=config,
    )
    world = World.objects.create(simulation=sim, stability_index=0.7)
    Government.objects.create(simulation=sim)
    zone = Zone.objects.create(
        world=world,
        name="WiringZone",
        zone_type="residential",
        boundary=Polygon.from_bbox((0, 0, 100, 100)),
        center=Point(50, 50),
    )
    return sim, zone


def _agent(sim, zone, name, age=40, **kwargs):
    defaults = dict(
        role="farmer",
        location=Point(50, 50),
        health=1.0,
        wealth=100.0,
        age=age,
        birth_tick=int(sim.current_tick - age * TICKS_PER_YEAR),
        education_level=0.5,
        social_class="working",
        gender=Agent.Gender.MALE,
        personality={},
    )
    defaults.update(kwargs)
    return Agent.objects.create(simulation=sim, name=name, zone=zone, **defaults)


@pytest.mark.django_db
def test_demography_runs_before_the_agent_chord(monkeypatch):
    """The order the plan settled on, asserted where it is observable.

    Agents deciding at tick T must see the population tick T actually has,
    so the block runs before the chord header is built. The visible
    consequence: an agent who dies in the block is absent from that header.
    """
    sim, zone = _simulation(None, demography=True)
    victim = _agent(sim, zone, "Vittima", age=95)
    survivor = _agent(sim, zone, "Superstite", age=25)

    observed_headers = []

    def _fake_chord(header):
        observed_headers.append(header)
        return lambda callback: None

    monkeypatch.setattr("epocha.apps.simulation.tasks.chord", _fake_chord)

    # The oldest agent dies and the younger one survives: the block certainly
    # changes the living population before the header is built, without
    # emptying it. An empty population would make the loop call its own
    # callback and re-enqueue itself, which under eager Celery recurses --
    # a pre-existing property of the loop, and not what this test is about.
    real_stream_for = orchestrator_module.stream_for

    def _scripted_mortality(simulation, tick, phase):
        if phase == "mortality":
            return _ScriptedRandom([0.0, 0.5])  # victim dies, then its cause
        return real_stream_for(simulation, tick, phase)

    monkeypatch.setattr(orchestrator_module, "stream_for", _scripted_mortality)

    run_simulation_loop(sim.id)

    victim.refresh_from_db()
    survivor.refresh_from_db()
    assert victim.is_alive is False
    assert survivor.is_alive is True
    assert observed_headers, "the chord header was never built"
    header_agent_ids = {sig.args[0] for sig in observed_headers[0]}
    assert victim.id not in header_agent_ids, (
        "an agent who died in the demography block is still in this tick's chord: "
        "the block is running after the header is built"
    )
    assert survivor.id in header_agent_ids


class _ScriptedRandom:
    """Dictated draws, so exactly one agent dies. Exhausted, it returns 1.0,
    which lets everyone else live."""

    def __init__(self, draws):
        self._draws = list(draws)

    def random(self):
        return self._draws.pop(0) if self._draws else 1.0

    def gauss(self, mu, sigma):
        return mu

    def randrange(self, n):
        return 0

    def choice(self, seq):
        return seq[0]


@pytest.mark.django_db
def test_a_simulation_without_demography_is_untouched(monkeypatch):
    """FR-009 and SC-004: same behaviour, no demography events.

    Silence is not consent -- a simulation that never declared the dedicated
    key must run exactly as it did before this subsystem was wired.
    """
    sim, zone = _simulation(None, demography=False)
    agent = _agent(sim, zone, "Indifferente", age=40)

    monkeypatch.setattr(
        "epocha.apps.simulation.tasks.chord", lambda header: (lambda callback: None)
    )

    run_simulation_loop(sim.id)

    agent.refresh_from_db()
    assert agent.is_alive is True
    assert not DemographyEvent.objects.filter(simulation=sim).exists()


@pytest.mark.django_db
def test_disabled_demography_costs_no_query(monkeypatch, django_assert_num_queries):
    """The block returns before touching the database when it is off.

    This is what makes the invariance measurable rather than asserted: a
    single call, wrapped, counted.
    """
    from epocha.apps.demography.orchestrator import run_demography_tick

    sim, zone = _simulation(None, demography=False)
    _agent(sim, zone, "Indifferente", age=40)

    with django_assert_num_queries(0):
        run_demography_tick(sim, tick=51)


@pytest.mark.django_db
def test_a_missing_template_does_not_abort_the_tick(monkeypatch):
    """Degradation by name, not by a blind `except Exception`."""
    sim, zone = _simulation(None, demography=True)
    sim.config = {"demography_enabled": True, "demography_template": "no_such_era"}
    sim.save()
    agent = _agent(sim, zone, "Immune", age=40)

    monkeypatch.setattr(
        "epocha.apps.simulation.tasks.chord", lambda header: (lambda callback: None)
    )

    run_simulation_loop(sim.id)

    agent.refresh_from_db()
    assert agent.is_alive is True
    assert not DemographyEvent.objects.filter(simulation=sim).exists()

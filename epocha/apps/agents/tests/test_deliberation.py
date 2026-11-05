"""Tests for the protagonist budget (max_protagonists) of the deliberation step."""

import logging
from unittest.mock import patch

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from epocha.apps.agents.deliberation import (
    is_valid_max_protagonists,
    max_protagonists,
    select_deliberating_agents,
)
from epocha.apps.agents.models import Agent, Group
from epocha.apps.simulation.models import Simulation
from epocha.apps.users.models import User
from epocha.apps.world.models import Government, World


@pytest.mark.parametrize("value", [0, 5, 30, 1000])
def test_a_non_negative_integer_is_a_valid_budget(value):
    assert is_valid_max_protagonists(value) is True


@pytest.mark.parametrize("value", [-1, True, False, 2.5, 5.0, "5", None])
def test_anything_else_is_not_a_valid_budget(value):
    assert is_valid_max_protagonists(value) is False


def _simulation(config):
    return Simulation(id=7, config=config)


def test_an_absent_key_gives_the_default_without_logging(caplog):
    with caplog.at_level(logging.DEBUG):
        assert max_protagonists(_simulation({})) == 30
    assert caplog.records == []


def test_a_valid_value_is_returned_as_it_is(caplog):
    with caplog.at_level(logging.DEBUG):
        assert max_protagonists(_simulation({"max_protagonists": 5})) == 5
        assert max_protagonists(_simulation({"max_protagonists": 0})) == 0
    assert caplog.records == []


@pytest.mark.parametrize("value", [-1, True, None])
def test_an_invalid_value_gives_the_default_and_one_error(value, caplog):
    with caplog.at_level(logging.ERROR):
        assert max_protagonists(_simulation({"max_protagonists": value})) == 30
    assert len(caplog.records) == 1
    record = caplog.records[0]
    assert record.levelno == logging.ERROR
    assert "Simulation 7 " in record.getMessage()
    assert repr(value) in record.getMessage()


def test_every_read_of_an_invalid_value_logs_again(caplog):
    simulation = _simulation({"max_protagonists": -1})
    with caplog.at_level(logging.ERROR):
        max_protagonists(simulation)
        max_protagonists(simulation)
    assert len(caplog.records) == 2


# --- select_deliberating_agents (plan PD-12) --------------------------------


@pytest.fixture
def owner(db):
    return User.objects.create_user(email="delib@epocha.dev", username="delib", password="pw12345")


def _new_simulation(owner, name, config=None):
    return Simulation.objects.create(
        name=name, seed=1, owner=owner, config={} if config is None else config
    )


def _make_agents(simulation, count):
    """Create `count` agents; creation order equals id order."""
    return [Agent.objects.create(simulation=simulation, name=f"a{i}") for i in range(count)]


def test_priority_agents_come_first_then_the_lowest_ids(owner):
    simulation = _new_simulation(owner, "S1", {"max_protagonists": 5})
    agents = _make_agents(simulation, 200)
    head, leader = agents[149], agents[119]
    Government.objects.create(simulation=simulation, head_of_state=head)
    Group.objects.create(simulation=simulation, name="g", leader=leader)

    selected = select_deliberating_agents(simulation, tick=1)

    assert [a.id for a in selected] == [head.id, leader.id] + [a.id for a in agents[:3]]


def test_an_absent_key_selects_every_agent_by_id(owner):
    simulation = _new_simulation(owner, "S2")
    agents = _make_agents(simulation, 25)

    assert [a.id for a in select_deliberating_agents(simulation, tick=1)] == [a.id for a in agents]


def test_a_zero_budget_selects_nobody_with_no_query(owner):
    """Under demography, where `minor_agent_ids` WOULD query, K = 0 must not reach it.

    Without demography the minor set is empty with no query and `[:0]` runs
    none, so the early return would save nothing and its removal would go
    unnoticed; the saving the guard buys is the minor read, hence the double
    that raises.
    """
    simulation = _new_simulation(owner, "S3", {"demography_enabled": True, "max_protagonists": 0})
    _make_agents(simulation, 4)

    with (
        patch(
            "epocha.apps.demography.orchestrator.minor_agent_ids",
            side_effect=AssertionError("the minor set was read with K = 0"),
        ),
        CaptureQueriesContext(connection) as queries,
    ):
        assert select_deliberating_agents(simulation, tick=1) == []
    assert len(queries) == 0


def test_a_budget_above_the_population_selects_everyone(owner):
    simulation = _new_simulation(owner, "S4", {"max_protagonists": 1000})
    agents = _make_agents(simulation, 7)

    assert len(select_deliberating_agents(simulation, tick=1)) == len(agents)


def test_a_dead_head_of_state_is_not_selected(owner):
    simulation = _new_simulation(owner, "S5", {"max_protagonists": 2})
    agents = _make_agents(simulation, 5)
    head = agents[4]
    Government.objects.create(simulation=simulation, head_of_state=head)
    Agent.objects.filter(id=head.id).update(is_alive=False)

    assert [a.id for a in select_deliberating_agents(simulation, tick=1)] == [
        agents[0].id,
        agents[1].id,
    ]


def test_a_leader_of_a_group_of_another_simulation_has_no_priority(owner):
    simulation = _new_simulation(owner, "S6", {"max_protagonists": 2})
    other = _new_simulation(owner, "S6-other")
    agents = _make_agents(simulation, 5)
    Group.objects.create(simulation=other, name="foreign", leader=agents[4])

    assert [a.id for a in select_deliberating_agents(simulation, tick=1)] == [
        agents[0].id,
        agents[1].id,
    ]


def _query_count(simulation):
    with CaptureQueriesContext(connection) as queries:
        select_deliberating_agents(simulation, tick=1)
    return len(queries)


def test_the_query_count_does_not_depend_on_the_population(owner):
    small = _new_simulation(owner, "S7a", {"max_protagonists": 5})
    large = _new_simulation(owner, "S7b", {"max_protagonists": 5})
    _make_agents(small, 20)
    _make_agents(large, 200)

    assert _query_count(small) == _query_count(large)


def test_the_query_count_does_not_depend_on_the_population_under_demography(owner):
    """With demography on, the minor read adds queries but still a constant number."""
    config = {"demography_enabled": True, "max_protagonists": 5}
    small = _new_simulation(owner, "S7c", config)
    large = _new_simulation(owner, "S7d", config)
    for simulation in (small, large):
        World.objects.create(simulation=simulation)
    # Children, so that a per-minor query would show: adults never reach one.
    for simulation, count in ((small, 20), (large, 200)):
        Agent.objects.bulk_create(
            [Agent(simulation=simulation, name=f"c{i}", age=5) for i in range(count)]
        )

    assert _query_count(small) == _query_count(large)

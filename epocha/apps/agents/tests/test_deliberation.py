"""Tests for the protagonist budget (max_protagonists) of the deliberation step."""

import logging

import pytest

from epocha.apps.agents.deliberation import is_valid_max_protagonists, max_protagonists
from epocha.apps.simulation.models import Simulation


@pytest.mark.parametrize("value", [0, 5, 30, 1000])
def test_a_non_negative_integer_is_a_valid_budget(value):
    assert is_valid_max_protagonists(value) is True


@pytest.mark.parametrize("value", [-1, True, False, 2.5, "5", None])
def test_anything_else_is_not_a_valid_budget(value):
    assert is_valid_max_protagonists(value) is False


def _simulation(config):
    return Simulation(id=7, config=config)


def test_an_absent_key_gives_the_default_without_logging(caplog):
    assert max_protagonists(_simulation({})) == 30
    assert caplog.records == []


def test_a_valid_value_is_returned_as_it_is(caplog):
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
    assert "7" in record.getMessage()
    assert repr(value) in record.getMessage()


def test_every_read_of_an_invalid_value_logs_again(caplog):
    simulation = _simulation({"max_protagonists": -1})
    with caplog.at_level(logging.ERROR):
        max_protagonists(simulation)
        max_protagonists(simulation)
    assert len(caplog.records) == 2

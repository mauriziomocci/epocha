"""Tests for the protagonist budget (max_protagonists) of the deliberation step."""

import pytest

from epocha.apps.agents.deliberation import is_valid_max_protagonists


@pytest.mark.parametrize("value", [0, 5, 30, 1000])
def test_a_non_negative_integer_is_a_valid_budget(value):
    assert is_valid_max_protagonists(value) is True


@pytest.mark.parametrize("value", [-1, True, False, 2.5, "5", None])
def test_anything_else_is_not_a_valid_budget(value):
    assert is_valid_max_protagonists(value) is False

"""The chat system prompt states the agent's age.

Plan 4 makes agents be born inside a run. The prompt used to say only
"You are {name}, a {role}", so a ten-month-old answered like an adult. The
age comes from demography's canonical `current_age_in_years` (birth tick,
tick length, acceleration), never from the frozen `Agent.age` column; the
dashboard only words it.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from django.contrib.gis.geos import Point

from epocha.apps.agents.models import Agent
from epocha.apps.dashboard.views import _build_chat_system_prompt
from epocha.apps.simulation.models import Simulation
from epocha.apps.users.models import User
from epocha.apps.world.models import World

TICKS_PER_YEAR = 365.0  # the default 24h tick
CURRENT_TICK = 5000


@pytest.fixture
def sim(db):
    user = User.objects.create_user(email="chat@epocha.dev", username="chatuser", password="pw1234")
    simulation = Simulation.objects.create(
        name="ChatPrompt", seed=1, owner=user, current_tick=CURRENT_TICK
    )
    World.objects.create(simulation=simulation)
    return simulation


def _prompt_for(sim, **agent_fields):
    agent = Agent.objects.create(
        simulation=sim, name="Anselmo", role="farmer", location=Point(1, 1), **agent_fields
    )
    request = SimpleNamespace(session={})
    return _build_chat_system_prompt(agent, request, "", "", "")


def test_an_infant_is_described_in_months(sim):
    # 330 ticks old: 330 / 365 * 12 = 10.85 months; completed months, not
    # rounded, so 10.
    prompt = _prompt_for(sim, age=0, birth_tick=CURRENT_TICK - 330)

    assert "10 months old" in prompt
    assert "as a person of that age would" in prompt


def test_an_adult_is_described_in_completed_years(sim):
    # 34.9 years old: the completed years are 34 (rounding would say 35).
    prompt = _prompt_for(sim, age=1, birth_tick=int(CURRENT_TICK - 34.9 * TICKS_PER_YEAR))

    assert "34 years old" in prompt
    assert "months old" not in prompt


def test_age_comes_from_birth_tick_not_the_frozen_column(sim):
    prompt = _prompt_for(sim, age=70, birth_tick=int(CURRENT_TICK - 12.5 * TICKS_PER_YEAR))

    assert "12 years old" in prompt
    assert "70 years old" not in prompt


def test_without_birth_tick_the_age_column_is_used(sim):
    prompt = _prompt_for(sim, age=52, birth_tick=None)

    assert "52 years old" in prompt


def test_one_month_is_singular(sim):
    prompt = _prompt_for(sim, age=0, birth_tick=CURRENT_TICK - 31)

    assert "1 month old" in prompt
    assert "1 months" not in prompt


def test_months_are_used_up_to_two_years_and_years_from_two(sim):
    toddler = _prompt_for(sim, age=0, birth_tick=int(CURRENT_TICK - 1.5 * TICKS_PER_YEAR))
    two_year_old = _prompt_for(sim, age=0, birth_tick=CURRENT_TICK - 2 * int(TICKS_PER_YEAR))

    assert "18 months old" in toddler
    assert "2 years old" in two_year_old


def test_the_group_chat_prompt_states_each_agents_age(sim):
    """The group chat builds its own prompt; it says the same thing about
    the speaker as the private chat, so a newborn in a group does not answer
    like an adult either."""
    import json
    from unittest.mock import MagicMock, patch

    from django.test import Client

    infant = Agent.objects.create(
        simulation=sim,
        name="Pietro",
        role="child",
        location=Point(1, 1),
        age=30,
        birth_tick=CURRENT_TICK - 330,
    )
    llm = MagicMock()
    llm.complete.return_value = "..."
    client = Client()
    client.force_login(sim.owner)

    with patch("epocha.apps.llm_adapter.client.get_chat_llm_client", return_value=llm):
        response = client.post(
            f"/simulations/{sim.id}/group-chat/",
            data=json.dumps({"message": "Hello", "agent_ids": [infant.id]}),
            content_type="application/json",
            headers={"X-Requested-With": "XMLHttpRequest"},
        )

    assert response.status_code == 200
    system_prompt = llm.complete.call_args.kwargs["system_prompt"]
    assert "You are Pietro, a child, 10 months old." in system_prompt
    assert "as a person of that age would" in system_prompt

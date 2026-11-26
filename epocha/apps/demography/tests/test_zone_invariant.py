"""Structural guard: every agent created by world generation has a zone.

The demography subsystem assumes that whenever a world has zones, every
living agent sits in one. Two consumers would disagree if that broke:
`orchestrator.run_starvation_counter_step` prices an unzoned agent at a
subsistence threshold of 0.0, while `migration.process_emergency_flight`
selects agents with `zone__in=zones` and never sees an unzoned one, so the
two would partition the same households differently. Nothing writes
`zone=None` today; `world.generator` assigns zones round-robin. This test
pins that on the prompt path of `generate_world_from_prompt`, so the
assumption cannot rot silently.
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from epocha.apps.agents.models import Agent
from epocha.apps.simulation.models import Simulation
from epocha.apps.users.models import User
from epocha.apps.world.generator import generate_world_from_prompt
from epocha.apps.world.models import Zone

# More agents than zones, so the round-robin wraps at least once: the last
# two agents are placed by `idx % len(zones)` returning to the first zones,
# which is where an off-by-one would leave someone outside.
_ZONE_NAMES = ["Harbour", "Market", "Fields"]
_AGENT_NAMES = ["Anna", "Bruno", "Carla", "Dario", "Elsa"]

_LLM_WORLD = json.dumps(
    {
        "world": {"economy_level": "base", "stability_index": 0.7},
        "zones": [{"name": name, "type": "urban", "resources": {}} for name in _ZONE_NAMES],
        "agents": [
            {"name": name, "age": 30, "role": "farmer", "gender": "female", "personality": {}}
            for name in _AGENT_NAMES
        ],
    }
)


@pytest.fixture
def simulation(db):
    owner = User.objects.create_user(
        email="zone-invariant@epocha.dev", username="zoneinvariant", password="pass1234"
    )
    return Simulation.objects.create(name="ZoneInvariant", seed=7, owner=owner)


@pytest.mark.django_db
class TestGeneratedAgentsAreZoned:
    # Both LLM boundaries are stubbed: the generator's own client, and the
    # enrichment pipeline, which builds a second client and calls Wikipedia.
    # Neither decides zone placement, which is the generator's own loop.
    @pytest.mark.usefixtures("no_enrichment")
    @patch("epocha.apps.world.generator.get_llm_client")
    def test_every_generated_agent_has_a_zone(self, mock_get_client, simulation):
        mock_client = MagicMock()
        mock_client.complete.return_value = _LLM_WORLD
        mock_get_client.return_value = mock_client

        generate_world_from_prompt(prompt="A small port town", simulation=simulation)

        world_zone_ids = set(
            Zone.objects.filter(world__simulation=simulation).values_list("id", flat=True)
        )
        placements = dict(
            Agent.objects.filter(simulation=simulation).values_list("name", "zone_id")
        )
        # Precondition, so the invariant below is not vacuously true.
        assert len(world_zone_ids) == len(_ZONE_NAMES)
        assert sorted(placements) == sorted(_AGENT_NAMES)
        assert [name for name, zone_id in placements.items() if zone_id is None] == []

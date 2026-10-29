"""Fixtures shared by test packages that have no common parent below the root.

`tests/` and `epocha/apps/*/tests/` are siblings, so a fixture used by both
lives here. Nothing here is autouse: each module opts in by name.
"""

from unittest.mock import patch

import pytest


@pytest.fixture
def no_enrichment():
    """Keep the enrichment pipeline out of world generation.

    `generate_world_from_prompt` ends by calling `enrich_simulation_agents`,
    which builds its own client through `enrichment.get_llm_client` and may
    query Wikipedia: patching `generator.get_llm_client` does not reach it.
    Until round 16 of the Plan 4 phase-6 gate the generator tests and the
    end-to-end flow sent one real classification request per run with the
    developer's key; blanking the keys in the test settings made them fail at
    client construction instead.
    """
    with patch(
        "epocha.apps.world.generator.enrich_simulation_agents",
        return_value={"classified": 0, "researched": 0, "enriched": 0},
    ) as mock:
        yield mock

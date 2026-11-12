"""Guard on the delivered shape of the simulation, agent and decision-log API.

The rule-based couples work item changes one thing at the API boundary: the
``400`` of ``config.max_protagonists`` (FR-020). Every other response keeps its
shape (SC-013, part 1). ``AgentSerializer`` and ``DecisionLogSerializer`` use
``fields = "__all__"``, so a new model field would silently become a new
response field; the literal lists below were written from the tree realigned
on the Plan 4 branch, before any change of this work item, and a change to any
of them is a contract change that needs the owner's permission first.
"""

from epocha.apps.agents.serializers import AgentSerializer, DecisionLogSerializer
from epocha.apps.simulation.serializers import SimulationSerializer

FROZEN_SIMULATION_FIELDS = [
    "branch_point",
    "config",
    "created_at",
    "current_tick",
    "description",
    "id",
    "name",
    "owner",
    "parent",
    "seed",
    "speed",
    "status",
    "updated_at",
]

FROZEN_AGENT_FIELDS = [
    "age",
    "agility",
    "birth_tick",
    "caretaker_agent",
    "charisma",
    "conditions",
    "consecutive_ticks_under_subsistence",
    "created_at",
    "creativity",
    "cunning",
    "death_cause",
    "death_tick",
    "education_level",
    "emotional_intelligence",
    "fertility",
    "gender",
    "group",
    "health",
    "id",
    "intelligence",
    "is_alive",
    "location",
    "mental_health",
    "mood",
    "name",
    "other_parent_agent",
    "parent_agent",
    "personality",
    "role",
    "sexual_orientation",
    "simulation",
    "social_class",
    "stamina",
    "strength",
    "wealth",
    "zone",
]

FROZEN_DECISION_LOG_FIELDS = [
    "agent",
    "cost_tokens",
    "created_at",
    "id",
    "input_context",
    "llm_model",
    "output_decision",
    "simulation",
    "tick",
]


def test_the_serializer_field_sets_are_frozen():
    assert sorted(SimulationSerializer().fields) == FROZEN_SIMULATION_FIELDS
    assert sorted(AgentSerializer().fields) == FROZEN_AGENT_FIELDS
    assert sorted(DecisionLogSerializer().fields) == FROZEN_DECISION_LOG_FIELDS

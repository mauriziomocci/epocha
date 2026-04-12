"""DRF serializers for Knowledge Graph API endpoints.

Serializes KnowledgeNode and KnowledgeRelation instances for the graph
data JSON API. The node serializer includes a ``linked`` field that
resolves optional foreign keys to simulation-model entities into a
compact {kind, id} dict.
"""
from __future__ import annotations

from rest_framework import serializers

from epocha.apps.knowledge.models import KnowledgeNode, KnowledgeRelation
from epocha.apps.knowledge.ontology import RELATION_CATEGORIES

# Mapping from linked FK field suffix to the "kind" label returned in the API.
_LINKED_FIELDS = {
    "linked_agent_id": "agent",
    "linked_group_id": "group",
    "linked_zone_id": "zone",
    "linked_institution_id": "institution",
    "linked_event_id": "event",
}


class KnowledgeNodeSerializer(serializers.ModelSerializer):
    """Serialize a KnowledgeNode for the graph data endpoint.

    The ``linked`` field resolves whichever optional FK is set to a
    compact ``{"kind": "<type>", "id": <pk>}`` dict, or null if no
    simulation-model entity is linked.
    """

    linked = serializers.SerializerMethodField()

    class Meta:
        model = KnowledgeNode
        fields = [
            "id",
            "entity_type",
            "name",
            "canonical_name",
            "description",
            "mention_count",
            "source_type",
            "linked",
        ]

    def get_linked(self, obj: KnowledgeNode) -> dict | None:
        """Return {kind, id} for the first non-null linked FK, or None."""
        for field_name, kind in _LINKED_FIELDS.items():
            fk_value = getattr(obj, field_name)
            if fk_value is not None:
                return {"kind": kind, "id": fk_value}
        return None


class KnowledgeEdgeSerializer(serializers.ModelSerializer):
    """Serialize a KnowledgeRelation as a graph edge.

    ``source`` and ``target`` are raw FK ids (no nested serialization)
    for lightweight transport. ``category`` is derived from the relation
    type via the ontology RELATION_CATEGORIES mapping.
    """

    source = serializers.IntegerField(source="source_node_id")
    target = serializers.IntegerField(source="target_node_id")
    category = serializers.SerializerMethodField()

    class Meta:
        model = KnowledgeRelation
        fields = [
            "id",
            "source",
            "target",
            "relation_type",
            "category",
            "weight",
        ]

    def get_category(self, obj: KnowledgeRelation) -> str:
        """Return the relation category from the ontology mapping."""
        return RELATION_CATEGORIES.get(obj.relation_type, "unknown")

"""Serializers for agents."""
from rest_framework import serializers

from .models import Agent, DecisionLog, Memory, Relationship


class AgentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Agent
        fields = "__all__"
        read_only_fields = ["id", "created_at"]


class AgentDetailSerializer(AgentSerializer):
    """Serializer with relationships and recent memories."""
    memories = serializers.SerializerMethodField()
    relationships = serializers.SerializerMethodField()

    def get_memories(self, obj):
        return MemorySerializer(obj.memories.filter(is_active=True)[:5], many=True).data

    def get_relationships(self, obj):
        rels = obj.relationships_from.all()[:10]
        return RelationshipSerializer(rels, many=True).data


class MemorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Memory
        fields = "__all__"


class RelationshipSerializer(serializers.ModelSerializer):
    class Meta:
        model = Relationship
        fields = "__all__"


class DecisionLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = DecisionLog
        fields = "__all__"

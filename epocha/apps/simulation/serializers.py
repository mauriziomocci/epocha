"""Serializers for the simulation."""
from rest_framework import serializers

from .models import Event, Simulation


class SimulationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Simulation
        fields = [
            "id", "name", "description", "status", "seed",
            "current_tick", "speed", "config", "owner",
            "parent", "branch_point", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "owner", "current_tick", "created_at", "updated_at"]


class SimulationCreateExpressSerializer(serializers.Serializer):
    """Input for Express mode: free text only."""

    prompt = serializers.CharField(help_text="Description of the world to simulate")


class EventSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = "__all__"
        read_only_fields = ["id", "created_at"]

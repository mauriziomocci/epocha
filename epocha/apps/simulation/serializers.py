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
    """Input for Express mode: text prompt, file upload, or both."""

    prompt = serializers.CharField(
        required=False, help_text="Description of the world to simulate",
    )
    file = serializers.FileField(
        required=False, help_text="Document upload (PDF, DOCX, MD, TXT)",
    )

    def validate(self, data):
        if not data.get("prompt") and not data.get("file"):
            raise serializers.ValidationError("Either 'prompt' or 'file' must be provided.")
        return data


class EventSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = "__all__"
        read_only_fields = ["id", "created_at"]

"""Serializers for the simulation."""

from rest_framework import serializers

from epocha.apps.agents.deliberation import is_valid_max_protagonists

from .models import Event, Simulation

MAX_PROTAGONISTS_ERROR = (
    "Must be a whole number of 0 or more; omit the key to use the default of 30."
)


class SimulationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Simulation
        fields = [
            "id",
            "name",
            "description",
            "status",
            "seed",
            "current_tick",
            "speed",
            "config",
            "owner",
            "parent",
            "branch_point",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "owner", "current_tick", "created_at", "updated_at"]

    def validate_config(self, value):
        """Reject an invalid ``max_protagonists`` at the API boundary (FR-020).

        The error is a dict keyed by the config key so that DRF nests it under
        ``config`` in the response body. Other keys stay unvalidated, as before.
        """
        if (
            isinstance(value, dict)
            and "max_protagonists" in value
            and not is_valid_max_protagonists(value["max_protagonists"])
        ):
            raise serializers.ValidationError({"max_protagonists": [MAX_PROTAGONISTS_ERROR]})
        return value


class SimulationCreateExpressSerializer(serializers.Serializer):
    """Input for Express mode: text prompt, file upload, or both."""

    prompt = serializers.CharField(
        required=False,
        help_text="Description of the world to simulate",
    )
    file = serializers.FileField(
        required=False,
        help_text="Document upload (PDF, DOCX, MD, TXT)",
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

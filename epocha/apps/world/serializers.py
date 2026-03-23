"""Serializers for the world."""
from rest_framework import serializers

from .models import World, Zone


class ZoneSerializer(serializers.ModelSerializer):
    class Meta:
        model = Zone
        fields = "__all__"


class WorldSerializer(serializers.ModelSerializer):
    zones = ZoneSerializer(many=True, read_only=True)

    class Meta:
        model = World
        fields = "__all__"

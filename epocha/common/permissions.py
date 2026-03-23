"""Custom DRF permissions."""
from rest_framework import permissions


class IsSimulationOwner(permissions.BasePermission):
    """Only the simulation owner can access it."""

    def has_object_permission(self, request, view, obj):
        if hasattr(obj, "owner"):
            return obj.owner == request.user
        if hasattr(obj, "simulation"):
            return obj.simulation.owner == request.user
        return False

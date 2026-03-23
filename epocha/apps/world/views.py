"""Views for the world."""
from rest_framework import permissions, viewsets

from .models import World
from .serializers import WorldSerializer


class WorldViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = WorldSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return World.objects.filter(simulation__owner=self.request.user)

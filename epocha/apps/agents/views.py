"""Views for agents."""
from rest_framework import permissions, viewsets

from .models import Agent
from .serializers import AgentDetailSerializer, AgentSerializer


class AgentViewSet(viewsets.ReadOnlyModelViewSet):
    """List and detail view for agents in a simulation."""

    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.action == "retrieve":
            return AgentDetailSerializer
        return AgentSerializer

    def get_queryset(self):
        return Agent.objects.filter(
            simulation__owner=self.request.user,
            simulation_id=self.kwargs.get("simulation_pk"),
        )

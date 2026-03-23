"""Views for the simulation."""
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Event, Simulation
from .serializers import EventSerializer, SimulationCreateExpressSerializer, SimulationSerializer


class SimulationViewSet(viewsets.ModelViewSet):
    """Simulation CRUD + play/pause/speed actions."""

    serializer_class = SimulationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Simulation.objects.filter(owner=self.request.user)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    @action(detail=False, methods=["post"], serializer_class=SimulationCreateExpressSerializer)
    def express(self, request):
        """Create a simulation from text input (Express mode)."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # TODO: generate world from prompt via LLM
        return Response({"detail": "To be implemented"}, status=status.HTTP_501_NOT_IMPLEMENTED)

    @action(detail=True, methods=["post"])
    def play(self, request, pk=None):
        """Start or resume the simulation."""
        simulation = self.get_object()
        simulation.status = Simulation.Status.RUNNING
        simulation.save(update_fields=["status"])
        # TODO: start the Celery loop
        return Response(SimulationSerializer(simulation).data)

    @action(detail=True, methods=["post"])
    def pause(self, request, pk=None):
        """Pause the simulation."""
        simulation = self.get_object()
        simulation.status = Simulation.Status.PAUSED
        simulation.save(update_fields=["status"])
        return Response(SimulationSerializer(simulation).data)

    @action(detail=True, methods=["get"])
    def events(self, request, pk=None):
        """List simulation events."""
        simulation = self.get_object()
        events = Event.objects.filter(simulation=simulation)
        return Response(EventSerializer(events, many=True).data)

"""Views for the simulation API.

Provides CRUD for simulations, the Express endpoint for one-prompt world
generation, and play/pause actions that control the Celery tick loop.
"""
from __future__ import annotations

import random

from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from epocha.apps.world.generator import generate_world_from_prompt

from .models import Event, Simulation
from .serializers import EventSerializer, SimulationCreateExpressSerializer, SimulationSerializer


class SimulationViewSet(viewsets.ModelViewSet):
    """Simulation CRUD + Express creation + play/pause control."""

    serializer_class = SimulationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Simulation.objects.filter(owner=self.request.user).order_by("-created_at")

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    @action(detail=False, methods=["post"], serializer_class=SimulationCreateExpressSerializer)
    def express(self, request):
        """Create a simulation from a text prompt (Express mode).

        Generates a complete world (zones, agents, economy) from the
        user's description via LLM, then sets the simulation to PAUSED
        so the user can review before pressing play.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        prompt = serializer.validated_data["prompt"]
        simulation = Simulation.objects.create(
            name="Express Simulation",
            description=prompt[:500],
            seed=random.randint(0, 2**32),
            status=Simulation.Status.INITIALIZING,
            owner=request.user,
        )

        try:
            result = generate_world_from_prompt(prompt=prompt, simulation=simulation)
            simulation.status = Simulation.Status.PAUSED
            simulation.save(update_fields=["status"])

            return Response(
                {"simulation_id": simulation.id, "world": result, "status": "ready"},
                status=status.HTTP_201_CREATED,
            )
        except Exception as e:
            simulation.status = Simulation.Status.ERROR
            simulation.save(update_fields=["status"])
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=["post"])
    def play(self, request, pk=None):
        """Start or resume the simulation by launching the Celery tick loop."""
        from .tasks import run_simulation_loop

        simulation = self.get_object()
        simulation.status = Simulation.Status.RUNNING
        simulation.save(update_fields=["status"])

        run_simulation_loop.delay(simulation.id)

        return Response(SimulationSerializer(simulation).data)

    @action(detail=True, methods=["post"])
    def pause(self, request, pk=None):
        """Pause the simulation. The current tick will complete before stopping."""
        simulation = self.get_object()
        simulation.status = Simulation.Status.PAUSED
        simulation.save(update_fields=["status"])
        return Response(SimulationSerializer(simulation).data)

    @action(detail=True, methods=["get"])
    def events(self, request, pk=None):
        """List simulation events ordered by tick."""
        simulation = self.get_object()
        events = Event.objects.filter(simulation=simulation).order_by("tick")
        return Response(EventSerializer(events, many=True).data)

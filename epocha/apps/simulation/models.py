"""Simulation Engine models — core of the system."""
from django.conf import settings
from django.db import models


class Simulation(models.Model):
    """A simulation with its state and configuration."""

    class Status(models.TextChoices):
        CREATED = "created", "Created"
        INITIALIZING = "initializing", "Initializing"
        RUNNING = "running", "Running"
        PAUSED = "paused", "Paused"
        STOPPED = "stopped", "Stopped"
        ERROR = "error", "Error"

    class Visibility(models.TextChoices):
        PRIVATE = "private", "Private"
        SHARED = "shared", "Shared"
        PUBLIC = "public", "Public"

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.CREATED)
    visibility = models.CharField(
        max_length=10, choices=Visibility.choices, default=Visibility.PRIVATE,
        help_text="Private: only owner. Shared: owner + collaborators. Public: everyone can view and fork.",
    )
    seed = models.BigIntegerField(help_text="Seed for reproducibility (non-LLM part)")
    current_tick = models.PositiveIntegerField(default=0)
    speed = models.FloatField(default=1.0, help_text="Simulation speed multiplier")
    config = models.JSONField(default=dict, help_text="Complete simulation configuration")
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="simulations")
    parent = models.ForeignKey("self", null=True, blank=True, on_delete=models.SET_NULL, help_text="Simulation from which this was forked")
    branch_point = models.PositiveIntegerField(null=True, blank=True, help_text="Divergence tick from parent")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} (tick {self.current_tick})"


class Event(models.Model):
    """Event that occurred in the simulation (historical record)."""

    class EventType(models.TextChoices):
        ECONOMIC = "economic", "Economic"
        POLITICAL = "political", "Political"
        SOCIAL = "social", "Social"
        MILITARY = "military", "Military"
        SCIENTIFIC = "scientific", "Scientific"
        CULTURAL = "cultural", "Cultural"
        NATURAL = "natural", "Natural"
        CUSTOM = "custom", "Custom"

    simulation = models.ForeignKey(Simulation, on_delete=models.CASCADE, related_name="events")
    tick = models.PositiveIntegerField()
    event_type = models.CharField(max_length=20, choices=EventType.choices)
    title = models.CharField(max_length=255)
    description = models.TextField()
    severity = models.FloatField(default=0.5, help_text="0.0 = negligible, 1.0 = catastrophic")
    consequences = models.JSONField(default=dict)
    caused_by = models.CharField(max_length=255, blank=True, help_text="Agent or system that caused the event")
    is_seldon_crisis = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["tick"]

    def __str__(self):
        return f"[Tick {self.tick}] {self.title}"

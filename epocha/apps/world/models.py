"""World models — map, economy, resources."""
from django.db import models

from epocha.apps.simulation.models import Simulation


class World(models.Model):
    """World state for a simulation."""

    simulation = models.OneToOneField(Simulation, on_delete=models.CASCADE, related_name="world")
    economy_level = models.CharField(max_length=20, default="base", help_text="simplified, base, full")
    global_wealth = models.FloatField(default=1000.0)
    stability_index = models.FloatField(default=0.7, help_text="0.0 = chaos, 1.0 = total peace")
    config = models.JSONField(default=dict)

    def __str__(self):
        return f"World for {self.simulation.name}"


class Zone(models.Model):
    """Geographic zone of the world."""

    class ZoneType(models.TextChoices):
        URBAN = "urban", "Urban"
        RURAL = "rural", "Rural"
        WILDERNESS = "wilderness", "Wilderness"
        COMMERCIAL = "commercial", "Commercial"
        INDUSTRIAL = "industrial", "Industrial"

    world = models.ForeignKey(World, on_delete=models.CASCADE, related_name="zones")
    name = models.CharField(max_length=255)
    zone_type = models.CharField(max_length=20, choices=ZoneType.choices)
    position_x = models.FloatField(default=0.0)
    position_y = models.FloatField(default=0.0)
    width = models.FloatField(default=100.0)
    height = models.FloatField(default=100.0)
    resources = models.JSONField(default=dict, help_text="Resources available in the zone")
    population_capacity = models.PositiveIntegerField(default=100)

    def __str__(self):
        return f"{self.name} ({self.zone_type})"


class EconomicTransaction(models.Model):
    """Economic transaction between agents or zones."""

    world = models.ForeignKey(World, on_delete=models.CASCADE, related_name="transactions")
    tick = models.PositiveIntegerField()
    from_agent_id = models.PositiveIntegerField(null=True, blank=True)
    to_agent_id = models.PositiveIntegerField(null=True, blank=True)
    amount = models.FloatField()
    description = models.CharField(max_length=255)

    class Meta:
        ordering = ["-tick"]

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


class Government(models.Model):
    """Political system governing the simulation world."""

    simulation = models.OneToOneField(Simulation, on_delete=models.CASCADE, related_name="government")
    government_type = models.CharField(max_length=30, default="democracy")
    stability = models.FloatField(default=0.5, help_text="0.0 = collapsing, 1.0 = rock solid")
    ruling_faction = models.ForeignKey(
        "agents.Group", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="ruled_governments",
    )
    head_of_state = models.ForeignKey(
        "agents.Agent", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="headed_governments",
    )

    # Political indicators (0.0-1.0)
    institutional_trust = models.FloatField(default=0.5)
    repression_level = models.FloatField(default=0.1)
    corruption = models.FloatField(default=0.2)
    popular_legitimacy = models.FloatField(default=0.5)
    military_loyalty = models.FloatField(default=0.5)

    # Electoral tracking
    last_election_tick = models.PositiveIntegerField(default=0)

    formed_at_tick = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.government_type} ({self.simulation.name})"


class GovernmentHistory(models.Model):
    """Historical record of government transitions."""

    simulation = models.ForeignKey(Simulation, on_delete=models.CASCADE, related_name="government_history")
    government_type = models.CharField(max_length=30)
    head_of_state_name = models.CharField(max_length=255, blank=True)
    ruling_faction_name = models.CharField(max_length=255, blank=True)
    from_tick = models.PositiveIntegerField()
    to_tick = models.PositiveIntegerField(null=True, blank=True)
    transition_cause = models.CharField(max_length=50)

    class Meta:
        ordering = ["-from_tick"]

    def __str__(self):
        return f"{self.government_type} from tick {self.from_tick}"


class Institution(models.Model):
    """Social institution with health that affects government indicators."""

    class InstitutionType(models.TextChoices):
        JUSTICE = "justice", "Justice"
        EDUCATION = "education", "Education"
        HEALTH = "health", "Health"
        MILITARY = "military", "Military"
        MEDIA = "media", "Media"
        RELIGION = "religion", "Religion"
        BUREAUCRACY = "bureaucracy", "Bureaucracy"

    simulation = models.ForeignKey(Simulation, on_delete=models.CASCADE, related_name="institutions")
    institution_type = models.CharField(max_length=20, choices=InstitutionType.choices)
    health = models.FloatField(default=0.5, help_text="0.0 = failed, 1.0 = thriving")
    independence = models.FloatField(default=0.5, help_text="0.0 = government controlled, 1.0 = fully independent")
    funding = models.FloatField(default=0.5, help_text="0.0 = defunded, 1.0 = well funded")

    class Meta:
        unique_together = ["simulation", "institution_type"]

    def __str__(self):
        return f"{self.institution_type} ({self.simulation.name})"

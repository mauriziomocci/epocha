"""Agent models — personality, memory, decisions."""
from django.db import models

from epocha.apps.simulation.models import Simulation


class Agent(models.Model):
    """An AI agent with personality and state."""

    simulation = models.ForeignKey(Simulation, on_delete=models.CASCADE, related_name="agents")
    name = models.CharField(max_length=255)
    age = models.PositiveIntegerField(default=25)
    personality = models.JSONField(default=dict, help_text="Big Five traits + background + values + weaknesses")
    position_x = models.FloatField(default=0.0)
    position_y = models.FloatField(default=0.0)
    health = models.FloatField(default=1.0, help_text="0.0 = dead, 1.0 = perfect health")
    wealth = models.FloatField(default=50.0)
    role = models.CharField(max_length=100, blank=True, help_text="Role in society (blacksmith, priest, farmer...)")
    mood = models.FloatField(default=0.5, help_text="0.0 = desperate, 1.0 = euphoric")
    is_alive = models.BooleanField(default=True)
    group = models.ForeignKey("Group", null=True, blank=True, on_delete=models.SET_NULL, related_name="members")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.role})"


class Group(models.Model):
    """Emergent social group."""

    simulation = models.ForeignKey(Simulation, on_delete=models.CASCADE, related_name="groups")
    name = models.CharField(max_length=255)
    objective = models.TextField(blank=True)
    cohesion = models.FloatField(default=0.5, help_text="0.0 = fragmented, 1.0 = monolithic")
    leader = models.ForeignKey(Agent, null=True, blank=True, on_delete=models.SET_NULL, related_name="led_groups")
    parent_group = models.ForeignKey("self", null=True, blank=True, on_delete=models.SET_NULL, related_name="subgroups")

    def __str__(self):
        return self.name


class Memory(models.Model):
    """Agent memory entry — with emotional weight and decay."""

    class SourceType(models.TextChoices):
        DIRECT = "direct", "Direct experience"
        HEARSAY = "hearsay", "Hearsay"
        PUBLIC = "public", "Public source"
        RUMOR = "rumor", "Rumor"

    agent = models.ForeignKey(Agent, on_delete=models.CASCADE, related_name="memories")
    content = models.TextField()
    emotional_weight = models.FloatField(default=0.5, help_text="0.0 = trivial, 1.0 = traumatic/ecstatic")
    source_type = models.CharField(max_length=20, choices=SourceType.choices, default=SourceType.DIRECT)
    reliability = models.FloatField(default=1.0, help_text="0.0 = unreliable, 1.0 = certain")
    tick_created = models.PositiveIntegerField()
    is_active = models.BooleanField(default=True, help_text="False = faded memory")

    class Meta:
        ordering = ["-emotional_weight", "-tick_created"]

    def __str__(self):
        return f"Memory of {self.agent.name}: {self.content[:50]}..."


class Relationship(models.Model):
    """Relationship between two agents."""

    class RelationType(models.TextChoices):
        FRIENDSHIP = "friendship", "Friendship"
        RIVALRY = "rivalry", "Rivalry"
        FAMILY = "family", "Family"
        ROMANTIC = "romantic", "Romantic"
        PROFESSIONAL = "professional", "Professional"
        DISTRUST = "distrust", "Distrust"

    agent_from = models.ForeignKey(Agent, on_delete=models.CASCADE, related_name="relationships_from")
    agent_to = models.ForeignKey(Agent, on_delete=models.CASCADE, related_name="relationships_to")
    relation_type = models.CharField(max_length=20, choices=RelationType.choices)
    strength = models.FloatField(default=0.5, help_text="0.0 = weak, 1.0 = very strong")
    sentiment = models.FloatField(default=0.0, help_text="-1.0 = hatred, 1.0 = love")
    since_tick = models.PositiveIntegerField()

    class Meta:
        unique_together = ["agent_from", "agent_to", "relation_type"]

    def __str__(self):
        return f"{self.agent_from.name} → {self.agent_to.name} ({self.relation_type})"


class DecisionLog(models.Model):
    """Log of every decision made by an agent (for replay and debug)."""

    simulation = models.ForeignKey(Simulation, on_delete=models.CASCADE, related_name="decision_logs")
    agent = models.ForeignKey(Agent, on_delete=models.CASCADE, related_name="decisions")
    tick = models.PositiveIntegerField()
    input_context = models.TextField(help_text="Context sent to the LLM")
    output_decision = models.TextField(help_text="Decision made by the LLM")
    llm_model = models.CharField(max_length=100)
    cost_tokens = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["tick"]

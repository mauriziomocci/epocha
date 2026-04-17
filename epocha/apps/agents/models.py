"""Agent models — personality, memory, decisions."""
from django.contrib.gis.db import models as gis_models
from django.db import models

from epocha.apps.simulation.models import Simulation


class Agent(models.Model):
    """An AI agent — a complete person with identity, personality, abilities, and state."""

    class Gender(models.TextChoices):
        MALE = "male", "Male"
        FEMALE = "female", "Female"
        NON_BINARY = "non_binary", "Non-binary"

    class SexualOrientation(models.TextChoices):
        HETEROSEXUAL = "heterosexual", "Heterosexual"
        HOMOSEXUAL = "homosexual", "Homosexual"
        BISEXUAL = "bisexual", "Bisexual"
        ASEXUAL = "asexual", "Asexual"

    # Identity
    simulation = models.ForeignKey(Simulation, on_delete=models.CASCADE, related_name="agents")
    name = models.CharField(max_length=255)
    age = models.PositiveIntegerField(default=25)
    gender = models.CharField(max_length=20, choices=Gender.choices, default=Gender.MALE)
    sexual_orientation = models.CharField(max_length=20, choices=SexualOrientation.choices, default=SexualOrientation.HETEROSEXUAL)
    role = models.CharField(max_length=100, blank=True, help_text="Role in society (blacksmith, priest, farmer...)")

    # Personality and psychology (Big Five + extended traits stored as JSONB)
    personality = models.JSONField(default=dict, help_text=(
        "Full personality profile: Big Five (openness, conscientiousness, extraversion, "
        "agreeableness, neuroticism), character traits, temperament, ambitions, fears, "
        "values, beliefs, humor style, attachment style"
    ))

    # Cognitive abilities
    intelligence = models.FloatField(default=0.5, help_text="0.0 = very low, 0.5 = average, 1.0 = genius")
    emotional_intelligence = models.FloatField(default=0.5, help_text="0.0 = oblivious, 1.0 = deeply empathetic")
    creativity = models.FloatField(default=0.5, help_text="0.0 = conventional, 1.0 = highly creative")
    cunning = models.FloatField(default=0.5, help_text="0.0 = naive, 1.0 = extremely shrewd")

    # Physical abilities
    strength = models.FloatField(default=0.5, help_text="0.0 = frail, 1.0 = extremely strong")
    stamina = models.FloatField(default=0.5, help_text="0.0 = no endurance, 1.0 = tireless")
    agility = models.FloatField(default=0.5, help_text="0.0 = clumsy, 1.0 = extremely agile")

    # Health
    health = models.FloatField(default=1.0, help_text="0.0 = dead, 1.0 = perfect health")
    mental_health = models.FloatField(default=0.8, help_text="0.0 = severe disorder, 1.0 = thriving")
    conditions = models.JSONField(default=list, help_text="List of active conditions: diseases, disabilities, addictions")
    fertility = models.FloatField(default=0.8, help_text="0.0 = infertile, 1.0 = highly fertile")

    # Social and economic state
    wealth = models.FloatField(default=50.0)
    mood = models.FloatField(default=0.5, help_text="0.0 = desperate, 1.0 = euphoric")
    charisma = models.FloatField(default=0.5, help_text="0.0 = repulsive, 1.0 = magnetic")
    education_level = models.FloatField(default=0.3, help_text="0.0 = illiterate, 1.0 = scholar")
    social_class = models.CharField(max_length=30, default="working", help_text="elite, wealthy, middle, working, poor, enslaved")

    # Position and status
    location = gis_models.PointField(
        null=True, blank=True, srid=4326,
        help_text="Current geographic position (WGS84)",
    )
    zone = models.ForeignKey(
        "world.Zone", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="agents_in_zone",
        help_text="Current zone (denormalized for performance)",
    )
    is_alive = models.BooleanField(default=True)
    group = models.ForeignKey("Group", null=True, blank=True, on_delete=models.SET_NULL, related_name="members")
    parent_agent = models.ForeignKey("self", null=True, blank=True, on_delete=models.SET_NULL, related_name="children", help_text="Biological parent (for lineage tracking)")

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
    formed_at_tick = models.PositiveIntegerField(default=0, help_text="Tick when the group was formed")

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
    origin_agent = models.ForeignKey(
        "Agent", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="originated_memories",
        help_text="Agent who originally performed the action (for dedup and traceability)",
    )

    class Meta:
        ordering = ["-emotional_weight", "-tick_created"]
        indexes = [
            models.Index(
                fields=["agent", "is_active", "-tick_created"],
                name="memory_dedup_idx",
            ),
            models.Index(
                fields=["origin_agent", "tick_created", "source_type"],
                name="memory_propagation_idx",
            ),
        ]

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
        indexes = [
            models.Index(fields=["simulation", "tick"]),
        ]


class ReputationScore(models.Model):
    """Per-agent perception of another agent's trustworthiness.

    Implements the Castelfranchi-Conte-Paolucci (1998) distinction between
    image (direct experience) and reputation (social evaluation via gossip).

    Source: Castelfranchi, C., Conte, R. & Paolucci, M. (1998). "Normative
    reputation and the costs of compliance." Journal of Artificial Societies
    and Social Simulation, vol. 1, no. 3.
    """

    holder = models.ForeignKey(Agent, on_delete=models.CASCADE, related_name="reputation_assessments")
    target = models.ForeignKey(Agent, on_delete=models.CASCADE, related_name="reputation_scores")
    image = models.FloatField(default=0.0, help_text="-1.0 = terrible, 0.0 = neutral, 1.0 = excellent (direct experience)")
    reputation = models.FloatField(default=0.0, help_text="-1.0 = terrible, 0.0 = neutral, 1.0 = excellent (social evaluation)")
    last_updated_tick = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ["holder", "target"]
        indexes = [
            models.Index(fields=["holder", "target"], name="reputation_lookup_idx"),
        ]

    def get_combined_score(self) -> float:
        """Return a single trustworthiness score combining image and reputation.

        Weights: image (direct experience) 0.6, reputation (social evaluation) 0.4.

        The primacy of direct experience over hearsay is a well-established principle
        in social psychology (Castelfranchi et al. 1998 for the conceptual distinction),
        but the specific 60/40 ratio is a tunable parameter without empirical derivation.

        Returns:
            Combined score in [-1.0, 1.0].
        """
        return self.image * 0.6 + self.reputation * 0.4

    def get_combined_score_normalized(self) -> float:
        """Return the combined reputation score normalized to [0, 1].

        Convenience method that normalizes the [-1, 1] combined score to
        [0, 1] for use by modules that need a non-negative scale (belief
        filter, elections). Centralizes the normalization that was
        previously scattered across consuming modules.

        Returns:
            Combined score in [0.0, 1.0]. Neutral (0.0) maps to 0.5.
        """
        raw = self.image * 0.6 + self.reputation * 0.4
        return (raw + 1.0) / 2.0

    def __str__(self):
        return f"{self.holder.name}'s view of {self.target.name}: img={self.image:.2f} rep={self.reputation:.2f}"

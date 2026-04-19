"""Demography models: Couple, DemographyEvent, PopulationSnapshot, AgentFertilityState.

Scientific foundations:
- Gale & Shapley (1962) — stable matching for initialization
- Goode (1963) — arranged marriage patterns
- Couple as unit of analysis for inheritance and family migration
"""
from django.db import models
from django.db.models import F, Q


class Couple(models.Model):
    """An active or dissolved couple between two agents.

    Polygamous couple types (polygynous, polyandrous) are not supported
    in MVP — the two-FK model cannot represent more than two partners.
    See the Known Limitations of the spec.

    When a partner dies the FK is nullified but the name snapshot
    preserves the genealogical record for audit purposes.
    """

    class CoupleType(models.TextChoices):
        MONOGAMOUS = "monogamous", "Monogamous"
        ARRANGED = "arranged", "Arranged"

    class DissolutionReason(models.TextChoices):
        DEATH = "death", "Death of a partner"
        SEPARATE = "separate", "Voluntary separation"
        ANNULMENT = "annulment", "Annulment"

    simulation = models.ForeignKey(
        "simulation.Simulation",
        on_delete=models.CASCADE,
        related_name="couples",
    )
    agent_a = models.ForeignKey(
        "agents.Agent",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="couple_as_a",
    )
    agent_b = models.ForeignKey(
        "agents.Agent",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="couple_as_b",
    )
    agent_a_name_snapshot = models.CharField(max_length=255, blank=True)
    agent_b_name_snapshot = models.CharField(max_length=255, blank=True)
    formed_at_tick = models.PositiveIntegerField()
    dissolved_at_tick = models.PositiveIntegerField(null=True, blank=True)
    dissolution_reason = models.CharField(
        max_length=20,
        choices=DissolutionReason.choices,
        blank=True,
    )
    couple_type = models.CharField(
        max_length=20,
        choices=CoupleType.choices,
        default=CoupleType.MONOGAMOUS,
    )

    class Meta:
        indexes = [
            models.Index(fields=["simulation", "dissolved_at_tick"]),
            models.Index(fields=["agent_a", "dissolved_at_tick"]),
            models.Index(fields=["agent_b", "dissolved_at_tick"]),
        ]
        constraints = [
            # Canonical ordering: when both partners are present, agent_a.id
            # must be strictly lower than agent_b.id. This prevents two
            # distinct rows representing the same pair with swapped FKs, a
            # class of bug that would corrupt heir resolution and duplicate
            # couple counts. When one partner has been nulled (death),
            # the constraint becomes vacuous.
            models.CheckConstraint(
                condition=(
                    Q(agent_a__isnull=True)
                    | Q(agent_b__isnull=True)
                    | Q(agent_a__lt=F("agent_b"))
                ),
                name="couple_canonical_ordering",
            ),
        ]

    def __str__(self):
        a = self.agent_a.name if self.agent_a else self.agent_a_name_snapshot or "?"
        b = self.agent_b.name if self.agent_b else self.agent_b_name_snapshot or "?"
        status = "active" if self.dissolved_at_tick is None else "dissolved"
        return f"Couple<{a} + {b} ({status})>"


class DemographyEvent(models.Model):
    """Ledger of demographic events for analytics, audit trail, paper reproducibility.

    Payload schema per event_type is documented in the spec
    (§DemographyEvent Payload Schemas).
    """

    class EventType(models.TextChoices):
        BIRTH = "birth", "Birth"
        DEATH = "death", "Death"
        PAIR_BOND = "pair_bond", "Pair bond"
        SEPARATE = "separate", "Separate"
        MIGRATION = "migration", "Migration"
        INHERITANCE_TRANSFER = "inheritance_transfer", "Inheritance transfer"
        MASS_FLIGHT = "mass_flight", "Mass flight"
        TRAPPED_CRISIS = "trapped_crisis", "Trapped crisis"
        DEMOGRAPHIC_INITIALIZER = "demographic_initializer", "Demographic initializer"

    simulation = models.ForeignKey(
        "simulation.Simulation",
        on_delete=models.CASCADE,
        related_name="demography_events",
    )
    tick = models.PositiveIntegerField()
    event_type = models.CharField(max_length=30, choices=EventType.choices)
    primary_agent = models.ForeignKey(
        "agents.Agent",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="demography_events_primary",
    )
    secondary_agent = models.ForeignKey(
        "agents.Agent",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="demography_events_secondary",
    )
    payload = models.JSONField(default=dict)

    class Meta:
        indexes = [
            models.Index(fields=["simulation", "tick"]),
            models.Index(fields=["simulation", "event_type", "tick"]),
        ]

    def __str__(self):
        return f"DemographyEvent<{self.event_type}@tick{self.tick}>"


class PopulationSnapshot(models.Model):
    """Per-tick aggregate demographic state for dashboards and validation."""

    simulation = models.ForeignKey(
        "simulation.Simulation",
        on_delete=models.CASCADE,
        related_name="population_snapshots",
    )
    tick = models.PositiveIntegerField()
    total_alive = models.PositiveIntegerField(default=0)
    age_pyramid = models.JSONField(
        default=list,
        help_text=(
            "List of [age_bucket_low, age_bucket_high, count_male, count_female]"
        ),
    )
    sex_ratio = models.FloatField(default=1.0)
    avg_age = models.FloatField(default=0.0)
    crude_birth_rate = models.FloatField(default=0.0)
    crude_death_rate = models.FloatField(default=0.0)
    tfr_instant = models.FloatField(default=0.0)
    net_migration_by_zone = models.JSONField(default=dict)
    couples_active = models.PositiveIntegerField(default=0)
    avg_household_size = models.FloatField(default=0.0)

    class Meta:
        unique_together = ("simulation", "tick")
        indexes = [
            models.Index(fields=["simulation", "tick"]),
        ]

    def __str__(self):
        return (
            f"PopulationSnapshot<sim={self.simulation_id} "
            f"tick={self.tick} alive={self.total_alive}>"
        )


class AgentFertilityState(models.Model):
    """Per-agent fertility control state for planned-fertility eras.

    Populated only when the template fertility_agency is "planned".
    The avoid_conception_flag_tick records the last tick at which the
    agent invoked the avoid_conception action; fertility checks this
    flag at tick T+1 (property-market-style tick+1 settlement).
    """

    agent = models.OneToOneField(
        "agents.Agent",
        on_delete=models.CASCADE,
        related_name="fertility_state",
    )
    avoid_conception_flag_tick = models.PositiveIntegerField(null=True, blank=True)

    def __str__(self):
        return f"FertilityState<{self.agent_id} flag={self.avoid_conception_flag_tick}>"

"""Relationship formation, evolution, and decay.

Models how social bonds form from interactions, evolve over time, and
can flip (a betrayal turns friendship into rivalry). Weak relationships
that are not reinforced fade away.

The interaction effects are qualitative; post-MVP these should be
calibrated with social psychology research (e.g., Baumeister & Leary,
1995 "The need to belong" for relationship formation thresholds).
"""
from __future__ import annotations

import logging

from .models import Agent, Relationship

logger = logging.getLogger(__name__)

# How each interaction type affects sentiment and relationship strength.
# Sentiment: positive = friendly, negative = hostile.
# Strength: how significant the relationship is (regardless of sentiment).
INTERACTION_EFFECTS: dict[str, dict[str, float | str]] = {
    "help": {"sentiment_delta": 0.15, "strength_delta": 0.1, "type": "friendship"},
    "socialize": {"sentiment_delta": 0.1, "strength_delta": 0.08, "type": "friendship"},
    "trade": {"sentiment_delta": 0.05, "strength_delta": 0.05, "type": "professional"},
    "work": {"sentiment_delta": 0.03, "strength_delta": 0.05, "type": "professional"},
    "argue": {"sentiment_delta": -0.2, "strength_delta": 0.1, "type": "rivalry"},
    "betray": {"sentiment_delta": -0.8, "strength_delta": 0.3, "type": "rivalry"},
    "avoid": {"sentiment_delta": -0.05, "strength_delta": -0.05, "type": "distrust"},
}

# Relationships decay by this amount per tick of no interaction.
DECAY_RATE = 0.002

# Decay only kicks in after this many ticks without reinforcement.
DECAY_THRESHOLD_TICKS = 30

# Relationships weaker than this are deleted (faded away).
MIN_STRENGTH_TO_SURVIVE = 0.05

# Sentiment threshold for flipping relationship type.
# A friendship flips to rivalry when sentiment crosses zero into negative
# territory — any negativity from a formerly positive relationship signals
# a meaningful break. Similarly, rivalry flips to friendship when sentiment
# crosses zero into positive.
FLIP_THRESHOLD = 0.0


def find_potential_relationships(agent: Agent, proximity_threshold: float = 20) -> list[Agent]:
    """Find nearby agents who could form new relationships.

    Returns agents in proximity that do not already have a relationship with
    the given agent. Uses PostGIS spatial distance for agents with locations;
    falls back to all alive simulation agents if no location is set.

    Args:
        agent: The agent looking for potential relationships.
        proximity_threshold: Maximum distance in meters for spatially-located agents.
    """
    existing_targets = Relationship.objects.filter(agent_from=agent).values_list("agent_to_id", flat=True)

    if agent.location is None:
        return list(
            Agent.objects.filter(simulation=agent.simulation, is_alive=True)
            .exclude(id=agent.id)
            .exclude(id__in=existing_targets)
        )

    from django.contrib.gis.measure import D
    return list(
        Agent.objects.filter(
            simulation=agent.simulation,
            is_alive=True,
            location__distance_lte=(agent.location, D(m=proximity_threshold)),
        )
        .exclude(id=agent.id)
        .exclude(id__in=existing_targets)
    )


def update_relationship_from_interaction(
    agent_from: Agent,
    agent_to: Agent,
    interaction: str,
    tick: int,
) -> None:
    """Update or create a relationship based on an interaction.

    Positive interactions build friendship; negative build rivalry.
    Strong betrayals can flip a friendship into rivalry and vice versa.
    """
    effects = INTERACTION_EFFECTS.get(
        interaction,
        {"sentiment_delta": 0, "strength_delta": 0, "type": "professional"},
    )

    try:
        rel = Relationship.objects.get(agent_from=agent_from, agent_to=agent_to)

        rel.sentiment = max(-1.0, min(1.0, rel.sentiment + effects["sentiment_delta"]))
        rel.strength = max(0.0, min(1.0, rel.strength + abs(effects["strength_delta"])))

        # Flip type on strong sentiment shift
        if rel.sentiment < -FLIP_THRESHOLD and rel.relation_type == "friendship":
            rel.relation_type = "rivalry"
            logger.info("%s and %s: friendship turned to rivalry", agent_from.name, agent_to.name)
        elif rel.sentiment > FLIP_THRESHOLD and rel.relation_type == "rivalry":
            rel.relation_type = "friendship"
            logger.info("%s and %s: rivalry turned to friendship", agent_from.name, agent_to.name)

        rel.save(update_fields=["sentiment", "strength", "relation_type"])

    except Relationship.DoesNotExist:
        Relationship.objects.create(
            agent_from=agent_from,
            agent_to=agent_to,
            relation_type=effects["type"],
            strength=abs(effects["strength_delta"]),
            sentiment=effects["sentiment_delta"],
            since_tick=tick,
        )


def evolve_relationships(simulation, current_tick: int) -> None:
    """Decay relationships that have had no recent interaction.

    Strong emotional bonds (love or hate) resist decay. Weak, neutral
    relationships fade and are eventually deleted.
    """
    relationships = Relationship.objects.filter(agent_from__simulation=simulation)

    for rel in relationships:
        age = current_tick - rel.since_tick
        if age < DECAY_THRESHOLD_TICKS:
            continue

        # Strong emotions (love or hate) resist decay
        emotional_anchor = abs(rel.sentiment)
        effective_decay = DECAY_RATE * (1 - emotional_anchor * 0.8)

        rel.strength = max(0.0, rel.strength - effective_decay)

        if rel.strength < MIN_STRENGTH_TO_SURVIVE:
            logger.debug("Relationship %s -> %s faded away", rel.agent_from.name, rel.agent_to.name)
            rel.delete()
        else:
            rel.save(update_fields=["strength"])

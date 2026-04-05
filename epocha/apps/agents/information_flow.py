"""Information flow propagation engine.

Runs once per tick after agent decisions. Collects significant actions and
public events, then propagates them through the social network with delay
(1 hop per tick), distortion (rule-based), and filtering (belief-based).

Scientific basis for the propagation model:
- Serial reproduction and information degradation: Bartlett (1932).
  "Remembering: A Study in Experimental and Social Psychology."
  Cambridge University Press.
- Social network information diffusion: Granovetter (1973). "The Strength
  of Weak Ties." American Journal of Sociology, 78(6), 1360-1380.
"""
from __future__ import annotations

import logging
import math

from django.conf import settings
from django.db.models import Q

from epocha.apps.simulation.models import Event, Simulation

from .belief import should_believe
from .distortion import distort_information
from .models import Agent, Memory, Relationship

logger = logging.getLogger(__name__)


def propagate_information(simulation: Simulation, tick: int) -> None:
    """Propagate information through the social network for one tick.

    Executes four phases in order:
    1. Direct memories from this tick above the significance threshold become
       hearsay for connected agents (hop 1).
    2. Hearsay created in the previous tick propagates as rumor (hop 2).
    3. Rumors created in the previous tick propagate as rumor if within
       the configured max_hops limit.
    4. Public events from this tick are broadcast instantly to all living agents.

    Each propagation step applies personality-driven distortion (transmitter)
    and a belief filter (recipient + relationship). Deduplication prevents an
    agent from receiving the same origin information more than once per tick.

    Args:
        simulation: The Simulation instance whose agents are ticking.
        tick:       The current tick number.
    """
    threshold = getattr(settings, "EPOCHA_INFO_FLOW_PROPAGATION_THRESHOLD", 0.3)
    decay = getattr(settings, "EPOCHA_INFO_FLOW_RELIABILITY_DECAY", 0.7)
    max_hops = getattr(settings, "EPOCHA_INFO_FLOW_MAX_HOPS", 3)
    max_recipients = getattr(settings, "EPOCHA_INFO_FLOW_MAX_RECIPIENTS", 20)

    # Phase 1: direct memories from this tick -> hearsay
    direct_memories = (
        Memory.objects.filter(
            agent__simulation=simulation,
            source_type=Memory.SourceType.DIRECT,
            tick_created=tick,
            emotional_weight__gte=threshold,
            is_active=True,
        )
        .select_related("agent", "origin_agent")
    )
    for memory in direct_memories:
        _propagate_memory(
            memory=memory,
            simulation=simulation,
            tick=tick,
            target_source_type=Memory.SourceType.HEARSAY,
            max_recipients=max_recipients,
            decay=decay,
            max_hops=max_hops,
        )

    # Phase 2: hearsay from the previous tick -> rumor
    hearsay_memories = (
        Memory.objects.filter(
            agent__simulation=simulation,
            source_type=Memory.SourceType.HEARSAY,
            tick_created=tick - 1,
            is_active=True,
        )
        .select_related("agent", "origin_agent")
    )
    for memory in hearsay_memories:
        _propagate_memory(
            memory=memory,
            simulation=simulation,
            tick=tick,
            target_source_type=Memory.SourceType.RUMOR,
            max_recipients=max_recipients,
            decay=decay,
            max_hops=max_hops,
        )

    # Phase 3: rumors from the previous tick -> rumor (if within max_hops)
    rumor_memories = (
        Memory.objects.filter(
            agent__simulation=simulation,
            source_type=Memory.SourceType.RUMOR,
            tick_created=tick - 1,
            is_active=True,
        )
        .select_related("agent", "origin_agent")
    )
    for memory in rumor_memories:
        current_hop = _estimate_hop(memory.reliability, decay)
        if current_hop >= max_hops:
            continue
        _propagate_memory(
            memory=memory,
            simulation=simulation,
            tick=tick,
            target_source_type=Memory.SourceType.RUMOR,
            max_recipients=max_recipients,
            decay=decay,
            max_hops=max_hops,
        )

    # Phase 4: public events -> all living agents
    public_events = Event.objects.filter(simulation=simulation, tick=tick)
    living_agents = Agent.objects.filter(simulation=simulation, is_alive=True)

    for event in public_events:
        content = f"{event.title}: {event.description}"
        for agent in living_agents:
            Memory.objects.get_or_create(
                agent=agent,
                source_type=Memory.SourceType.PUBLIC,
                tick_created=tick,
                origin_agent=None,
                defaults={
                    "content": content,
                    "emotional_weight": event.severity,
                    "reliability": 1.0,
                },
            )

    logger.debug(
        "propagate_information: simulation=%s tick=%d "
        "direct=%d hearsay=%d rumor=%d events=%d",
        simulation.pk,
        tick,
        direct_memories.count(),
        hearsay_memories.count(),
        rumor_memories.count(),
        public_events.count(),
    )


def _propagate_memory(
    memory: Memory,
    simulation: Simulation,
    tick: int,
    target_source_type: str,
    max_recipients: int,
    decay: float,
    max_hops: int,
) -> None:
    """Spread one memory to the social neighbours of its agent.

    Finds all living agents connected to the transmitter via any Relationship
    (bidirectional lookup), then for each candidate:
    - Skips the origin agent (no echo back to source).
    - Skips agents that already received information from the same origin this tick.
    - Applies distortion using the transmitter's personality.
    - Applies the belief filter using the recipient's personality and the
      relationship between recipient and transmitter.
    - Creates the Memory record if accepted.

    The new reliability is decayed by the configured decay factor.

    Args:
        memory:             The source Memory to propagate.
        simulation:         The simulation context (used only for scoping queries).
        tick:               Current tick number (used for the new Memory's tick_created).
        target_source_type: SourceType value for the new Memory (hearsay or rumor).
        max_recipients:     Cap on how many agents receive this memory per call.
        decay:              Reliability multiplier per hop (0.0 < decay < 1.0).
        max_hops:           Maximum number of propagation hops allowed.
    """
    transmitter = memory.agent
    origin = memory.origin_agent or memory.agent

    # Bidirectional relationship lookup: transmitter is either agent_from or agent_to
    relationships = (
        Relationship.objects.filter(
            Q(agent_from=transmitter) | Q(agent_to=transmitter)
        )
        .select_related("agent_from", "agent_to")
    )

    # Gather already-informed agents (dedup): recipients who already have hearsay
    # or rumor from this origin agent for this tick.
    already_informed = set(
        Memory.objects.filter(
            agent__simulation=simulation,
            source_type__in=[Memory.SourceType.HEARSAY, Memory.SourceType.RUMOR],
            origin_agent=origin,
            tick_created=tick,
        ).values_list("agent_id", flat=True)
    )

    new_reliability = memory.reliability * decay
    distorted_content = distort_information(memory.content, transmitter.personality)

    recipients_created = 0

    for rel in relationships:
        if recipients_created >= max_recipients:
            break

        # Identify the other party in the relationship
        recipient = rel.agent_to if rel.agent_from_id == transmitter.pk else rel.agent_from

        # Never send back to the origin agent
        if recipient.pk == origin.pk:
            continue

        # Skip dead agents
        if not recipient.is_alive:
            continue

        # Deduplication
        if recipient.pk in already_informed:
            continue

        # Relationship context from recipient's perspective toward transmitter:
        # use the same relationship record we already have (direction-agnostic).
        rel_strength = rel.strength
        rel_sentiment = rel.sentiment

        # Belief filter
        if not should_believe(
            reliability=new_reliability,
            receiver_personality=recipient.personality,
            relationship_strength=rel_strength,
            relationship_sentiment=rel_sentiment,
        ):
            continue

        Memory.objects.create(
            agent=recipient,
            content=distorted_content,
            emotional_weight=memory.emotional_weight,
            source_type=target_source_type,
            reliability=new_reliability,
            tick_created=tick,
            origin_agent=origin,
        )

        already_informed.add(recipient.pk)
        recipients_created += 1


def _estimate_hop(reliability: float, decay: float) -> int:
    """Estimate the current hop count from a memory's reliability and the decay factor.

    Derived by inverting the compounding formula reliability = decay^hop:
        hop = log(reliability) / log(decay)

    Args:
        reliability: Current reliability value of the memory (0.0 to 1.0).
        decay:       Per-hop decay factor (0.0 < decay < 1.0).

    Returns:
        Estimated hop count as a non-negative integer. Returns 0 if reliability
        is at maximum (1.0) or if decay is degenerate. Returns 99 if reliability
        has decayed to zero, indicating the information is exhausted.
    """
    if reliability >= 1.0 or decay >= 1.0 or decay <= 0.0:
        return 0
    if reliability <= 0.0:
        return 99
    return round(math.log(reliability) / math.log(decay))

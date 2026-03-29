"""Agent memory management — retrieval, creation, and realistic decay.

Models the imperfection of human memory: recent and emotionally intense
memories are vivid, while ordinary memories fade over time. This follows
the Ebbinghaus forgetting curve principle, simplified into a threshold
model with emotional anchoring.

Reference: Ebbinghaus, H. (1885). "Memory: A Contribution to Experimental
Psychology." The emotional modulation of memory is supported by extensive
research on amygdala-mediated memory consolidation (McGaugh, 2004.
"The amygdala modulates the consolidation of memories of emotionally
arousing experiences." Annual Review of Neuroscience, 27, 1-28).
"""
from __future__ import annotations

from .models import Memory

# Memories begin to decay after this many ticks without reinforcement.
# Represents the transition from short-term to long-term memory.
# Source: Ebbinghaus curve shows steepest forgetting in the first hours/days.
# In simulation terms, 50 ticks at daily resolution ~ 50 days.
DECAY_THRESHOLD_TICKS = 50

# Memories with emotional weight above this value resist decay strongly.
# High-emotion events (trauma, joy, betrayal) consolidate into long-term memory.
# Source: McGaugh (2004) — emotional arousal enhances memory consolidation.
EMOTIONAL_PERSISTENCE_THRESHOLD = 0.6


def get_relevant_memories(
    agent,
    current_tick: int,
    max_memories: int = 10,
) -> list[Memory]:
    """Retrieve the most relevant active memories for an agent.

    Ranking: emotional weight (descending), then recency (descending).
    This mirrors how humans recall: emotionally charged events first,
    then the most recent ordinary events.
    """
    return list(
        Memory.objects.filter(agent=agent, is_active=True)
        .order_by("-emotional_weight", "-tick_created")[:max_memories]
    )


def decay_memories(agent, current_tick: int) -> None:
    """Apply time-based decay to an agent's memories.

    Memories with low emotional weight that have aged beyond the decay
    threshold are deactivated. High emotional weight memories persist
    much longer, modeling the amygdala-mediated consolidation effect.

    The decay factor formula:
        decay = age / (threshold * (1 + weight * dampening))

    When decay > 1.0, the memory is deactivated.

    - `age`: ticks since memory creation
    - `threshold`: DECAY_THRESHOLD_TICKS (base forgetting window)
    - `weight`: emotional_weight (0.0-1.0)
    - `dampening`: multiplier for how much emotion slows forgetting (5x)
    """
    memories = Memory.objects.filter(agent=agent, is_active=True)

    for memory in memories:
        age = current_tick - memory.tick_created

        # Recent memories never decay regardless of weight
        if age <= DECAY_THRESHOLD_TICKS:
            continue

        # Emotionally significant memories resist decay
        if memory.emotional_weight >= EMOTIONAL_PERSISTENCE_THRESHOLD:
            continue

        # Decay formula: emotion dampens forgetting by up to 5x
        dampening_factor = 1 + memory.emotional_weight * 5
        decay = age / (DECAY_THRESHOLD_TICKS * dampening_factor)

        if decay > 1.0:
            memory.is_active = False
            memory.save(update_fields=["is_active"])

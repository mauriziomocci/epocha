"""Social stratification engine — dynamic class mobility, Gini coefficient, and corruption mechanics.

Wealth-based social class assignment follows a percentile approach: agents are ranked by wealth
each political cycle and assigned to one of five strata. Class transitions generate memories that
shape future agent decisions.

The Gini coefficient is the standard measure of income inequality.
Reference: Gini, C. (1912). "Variabilita e mutabilita." Reprinted in Pizetti & Salvemini (1955).

Corruption mechanics are grounded in the predatory state literature:
Reference: Acemoglu, D., & Robinson, J. A. (2006). "Economic Origins of Dictatorship and Democracy."
Cambridge University Press. Chapter 2: agents controlling political institutions extract rents from
the public pool rather than creating new wealth.
"""
from __future__ import annotations

import logging

from epocha.apps.agents.models import Agent, Memory
from epocha.apps.world.models import Government, World

logger = logging.getLogger(__name__)

# Social class strata defined as (label, lower_percentile_inclusive, upper_percentile_exclusive).
# The top 5% of agents by wealth are elite, the next 10% are wealthy, etc.
# Simplified 5-class model inspired by Gilbert (2011) but with adjusted thresholds for simulation
# dynamics. Gilbert's original model uses 6 classes with different boundaries (capitalist 1%,
# upper-middle 14%, middle 30%, working 30%, working-poor 13%, underclass 12%). The 5/15/50/80
# split here is a design simplification that collapses adjacent classes for tractability.
# Reference: Gilbert, D. (2011). "The American Class Structure in an Age of Growing Inequality."
# SAGE Publications. Chapter 1.
_CLASS_THRESHOLDS: list[tuple[str, float, float]] = [
    ("elite",   0.00, 0.05),   # top 5%
    ("wealthy", 0.05, 0.15),   # next 10%
    ("middle",  0.15, 0.50),   # next 35%
    ("working", 0.50, 0.80),   # next 30%
    ("poor",    0.80, 1.00),   # bottom 20%
]

# Class rank used to detect significant mobility (2+ rank jumps).
_CLASS_RANK: dict[str, int] = {
    "elite": 0,
    "wealthy": 1,
    "middle": 2,
    "working": 3,
    "poor": 4,
}

# Corruption skimming rate per tick for agents in power.
# Calibrated so that a fully corrupt head of state (conscientiousness=0) extracts
# ~2% of their own wealth per tick, consistent with historical estimates of petty
# corruption in extractive states.
# Reference: Acemoglu & Robinson (2006), Chapter 2; Transparency International CPI data.
_CORRUPTION_SKIM_RATE = 0.02

# Emotional weight assigned to class-change memories.
# Upward mobility is mildly positive; downward mobility is more emotionally salient.
# The ratio 0.7 / 0.4 = 1.75:1 (downward vs upward) is approximately consistent with the
# loss aversion coefficient of ~2:1 from Prospect Theory. The specific magnitudes (0.4 upward,
# 0.7 downward) are tunable design parameters, not empirically derived values.
# Reference: Kahneman, D., & Tversky, A. (1979). "Prospect Theory: An Analysis of Decision
# under Risk." Econometrica, 47(2), 263-292.
_UPWARD_MOBILITY_WEIGHT = 0.4
_DOWNWARD_MOBILITY_WEIGHT = 0.7


def compute_gini(wealths: list[float]) -> float:
    """Compute the Gini coefficient from a list of wealth values.

    Uses the standard sorted-array formula:
        G = sum((2i - n + 1) * w_i) / (n * sum(w))   for i in [0, n-1], w sorted ascending.

    This is equivalent to twice the area between the Lorenz curve and the line of
    perfect equality.

    Reference: Gini, C. (1912). "Variabilita e mutabilita." In Pizetti & Salvemini (1955),
    Memorie di metodologica statistica. Libreria Eredi Virgilio Veschi, Rome.

    Args:
        wealths: List of non-negative wealth values (one per agent). May contain zeros.

    Returns:
        Gini coefficient in [0.0, 1.0]. Returns 0.0 for empty or single-element lists,
        and 0.0 when total wealth is zero (all agents are equally poor).
    """
    n = len(wealths)
    if n <= 1:
        return 0.0

    sorted_w = sorted(wealths)
    total = sum(sorted_w)
    if total == 0.0:
        return 0.0

    cumulative = sum((2 * i - n + 1) * w for i, w in enumerate(sorted_w))
    return cumulative / (n * total)


def _assign_class(rank: int, total: int) -> str:
    """Return the social class label for an agent at a given sorted rank.

    Args:
        rank: 0-based rank with 0 = wealthiest agent.
        total: Total number of agents.

    Returns:
        Social class label (elite, wealthy, middle, working, poor).
    """
    percentile = rank / total
    for label, lower, upper in _CLASS_THRESHOLDS:
        if lower <= percentile < upper:
            return label
    # Fallback: the last agent sits exactly at percentile=1.0 and must be poor.
    return "poor"


def update_social_classes(simulation) -> None:
    """Rank all living agents by wealth and assign social class labels by percentile.

    Agents are ranked wealthiest-first. Class boundaries:
    - top 5%  → elite
    - 5-15%   → wealthy
    - 15-50%  → middle
    - 50-80%  → working
    - 80-100% → poor

    When an agent moves two or more class ranks, a Memory entry is created to record
    the experience, giving that event narrative weight in future LLM decision contexts.

    Args:
        simulation: Simulation instance. Only living agents are considered.
    """
    agents = list(
        Agent.objects.filter(simulation=simulation, is_alive=True)
        .only("id", "name", "wealth", "social_class")
        .order_by("-wealth")
    )
    total = len(agents)
    if total == 0:
        return

    memories_to_create: list[Memory] = []
    agents_to_update: list[Agent] = []
    tick = simulation.current_tick

    for rank, agent in enumerate(agents):
        new_class = _assign_class(rank, total)
        old_class = agent.social_class

        agent.social_class = new_class
        agents_to_update.append(agent)

        # Create a memory only when mobility is significant (2+ rank jumps).
        old_rank = _CLASS_RANK.get(old_class, _CLASS_RANK["working"])
        new_rank = _CLASS_RANK[new_class]
        delta = old_rank - new_rank  # positive = upward, negative = downward

        if abs(delta) >= 2:
            if delta > 0:
                content = (
                    f"I rose from {old_class} to {new_class} class — "
                    f"a significant improvement in my social standing."
                )
                emotional_weight = _UPWARD_MOBILITY_WEIGHT
            else:
                content = (
                    f"I fell from {old_class} to {new_class} class — "
                    f"a painful loss of social standing."
                )
                emotional_weight = _DOWNWARD_MOBILITY_WEIGHT

            memories_to_create.append(Memory(
                agent=agent,
                content=content,
                emotional_weight=emotional_weight,
                source_type=Memory.SourceType.DIRECT,
                reliability=1.0,
                tick_created=tick,
            ))

    Agent.objects.bulk_update(agents_to_update, ["social_class"])
    if memories_to_create:
        Memory.objects.bulk_create(memories_to_create)

    logger.debug(
        "update_social_classes: simulation=%d tick=%d agents=%d mobility_memories=%d",
        simulation.pk, tick, total, len(memories_to_create),
    )


def process_corruption(simulation, tick: int) -> None:
    """Model corruption as wealth extraction by agents in power with low conscientiousness.

    Agents eligible for corruption:
    - Head of state (Government.head_of_state)
    - Leaders of groups (Group.leader)

    Corruption mechanic: an eligible agent skims a fraction of the global wealth pool
    proportional to (1 - conscientiousness). This represents diversion of public resources
    to personal enrichment — a transfer, not a creation. Each agent's skim is capped at
    1% of global_wealth per tick to prevent a single actor from draining the economy
    in a single tick. This is a simplified model; a more realistic version would skim from
    tax revenue or public services budgets.
    Reference: Acemoglu, D., & Robinson, J. A. (2006). "Economic Origins of Dictatorship
    and Democracy." Cambridge University Press. Chapter 2.

    Conscientiousness threshold for corruption susceptibility: agents with conscientiousness
    below 0.4 are considered susceptible. Low conscientiousness as a correlate of
    rule-breaking behavior is supported by personality-deviance research (e.g., Miller, J. D.,
    & Lynam, D. R. (2001). "Structural models of personality and their relation to antisocial
    behavior." Criminology, 39(4), 765-798), but the specific 0.4 cutoff is a tunable
    simulation parameter, not empirically derived.

    When the head of state is the corrupt agent, the Government.corruption indicator rises.

    Args:
        simulation: Simulation instance.
        tick: Current simulation tick (used for Memory records).
    """
    # Fetch the world to track global_wealth transfers.
    try:
        world = World.objects.get(simulation=simulation)
    except World.DoesNotExist:
        world = None

    # Collect all agents in power.
    agents_in_power: list[Agent] = []

    try:
        government = Government.objects.select_related("head_of_state").get(simulation=simulation)
        if government.head_of_state and government.head_of_state.is_alive:
            agents_in_power.append(government.head_of_state)
    except Government.DoesNotExist:
        government = None

    from epocha.apps.agents.models import Group  # avoid circular import at module level

    group_leaders = (
        Agent.objects.filter(
            simulation=simulation,
            is_alive=True,
            led_groups__simulation=simulation,
        ).distinct()
        .only("id", "name", "wealth", "personality")
    )
    agents_in_power.extend(group_leaders)

    # Deduplicate: the head of state may also be a faction leader.
    seen_ids: set[int] = set()
    unique_agents: list[Agent] = []
    for agent in agents_in_power:
        if agent.pk not in seen_ids:
            seen_ids.add(agent.pk)
            unique_agents.append(agent)

    # Conscientiousness threshold below which an agent engages in corruption.
    CONSCIENTIOUSNESS_THRESHOLD = 0.4

    agents_to_update: list[Agent] = []
    memories_to_create: list[Memory] = []
    is_head_of_state_corrupt = False

    for agent in unique_agents:
        conscientiousness = agent.personality.get("conscientiousness", 0.5)
        if conscientiousness >= CONSCIENTIOUSNESS_THRESHOLD:
            continue

        # Skim rate scales linearly: fully corrupt agent (c=0) skims at max rate;
        # agent at threshold (c=0.4) skims nothing.
        skim_fraction = _CORRUPTION_SKIM_RATE * (1.0 - conscientiousness / CONSCIENTIOUSNESS_THRESHOLD)
        skim_amount = agent.wealth * skim_fraction
        # Corruption transfers wealth from the global pool to the corrupt agent.
        # The 1% cap prevents a single agent from draining the economy in one tick.
        # This is a simplified model; a more realistic version would skim from tax
        # revenue or public services.
        if world is not None:
            skim_amount = min(skim_amount, world.global_wealth * 0.01)
            world.global_wealth -= skim_amount
        agent.wealth += skim_amount
        agents_to_update.append(agent)

        memories_to_create.append(Memory(
            agent=agent,
            content=(
                f"I used my position of power to extract {skim_amount:.1f} units of wealth "
                f"at tick {tick}."
            ),
            emotional_weight=0.3,
            source_type=Memory.SourceType.DIRECT,
            reliability=1.0,
            tick_created=tick,
        ))

        # Track whether the head of state was corrupt this tick.
        if government and government.head_of_state_id == agent.pk:
            is_head_of_state_corrupt = True

    if agents_to_update:
        Agent.objects.bulk_update(agents_to_update, ["wealth"])

    if memories_to_create:
        Memory.objects.bulk_create(memories_to_create)

    # Persist the updated global_wealth after all agents have been processed.
    if world is not None and agents_to_update:
        world.save(update_fields=["global_wealth"])

    # Raise government corruption index when the head of state personally extracts rent.
    # Corruption decays slowly when the head of state is clean.
    if government:
        if is_head_of_state_corrupt:
            # Each corrupt tick nudges the index upward by 0.02 (capped at 1.0).
            government.corruption = min(1.0, government.corruption + 0.02)
        else:
            # Slow institutional decay toward clean governance when leader is honest.
            government.corruption = max(0.0, government.corruption - 0.005)
        government.save(update_fields=["corruption"])

    logger.debug(
        "process_corruption: simulation=%d tick=%d corrupt_agents=%d head_corrupt=%s",
        simulation.pk, tick, len(agents_to_update), is_head_of_state_corrupt,
    )

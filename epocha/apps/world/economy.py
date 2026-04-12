"""Basic economic logic for the MVP.

A simplified economy where agents earn income based on their role and pay
a fixed cost of living each tick. Wealth affects mood, and average mood
determines world stability.

This is a placeholder economy for the MVP. Post-MVP versions will implement
supply/demand, inflation, trade, and class dynamics as described in the
design spec (Scientific Models Engine section).

Income values are relative (not calibrated to any real currency), designed
to produce interesting dynamics within 50-100 ticks.
"""
from __future__ import annotations

import logging
import math

from epocha.apps.agents.models import Agent

logger = logging.getLogger(__name__)

# Base income per tick by role. Higher-skilled roles earn more.
# These values are game-balanced for MVP dynamics, not historically calibrated.
# Post-MVP: replace with supply/demand model calibrated on historical data.
ROLE_INCOME: dict[str, float] = {
    "farmer": 5.0,
    "blacksmith": 8.0,
    "merchant": 10.0,
    "priest": 3.0,
    "soldier": 6.0,
    "craftsman": 7.0,
    "healer": 6.0,
    "leader": 12.0,
}
DEFAULT_INCOME = 2.0

# Fixed cost of living per tick (food, shelter, basic needs).
COST_OF_LIVING = 3.0

# Mood adjustment rates per tick based on wealth.
# Source (qualitative): Kahneman & Deaton (2010) showed income affects
# emotional well-being up to a satiation point. We model this as
# diminishing mood gains for wealth and sharper mood drops for poverty.
# The satiation effect is implemented as an exponential decay of the mood
# boost above the threshold. The specific decay rate is a tunable parameter;
# the qualitative behavior (mood plateau at high wealth) is the paper's
# central finding.
MOOD_BOOST_WEALTHY = 0.02     # Base mood boost at the satiation threshold (Kahneman & Deaton, 2010)
MOOD_PENALTY_POOR = 0.05      # Wealth < 10: moderate mood decrease
MOOD_PENALTY_DESTITUTE = 0.10  # Wealth < 0: severe mood decrease
HEALTH_PENALTY_STARVING = 0.01  # Wealth < 0: health decreases (starvation)

# Kahneman & Deaton (2010): emotional well-being plateaus above ~$75k income.
# We model this satiation point as wealth = 100 (relative units).
# The decay constant controls how fast the mood boost diminishes above the
# threshold. Tunable parameter; not derived empirically -- the qualitative
# plateau behavior is the paper's finding.
_WEALTH_SATIATION_THRESHOLD = 100.0
_MOOD_SATIATION_DECAY = 0.005  # Controls how fast the boost diminishes above satiation


def process_economy_tick(world, tick: int) -> None:
    """Process one economic tick for all living agents in the world.

    For each agent:
    1. Earn role-based income
    2. Pay cost of living
    3. Adjust mood based on wealth (with Kahneman & Deaton satiation above threshold)
    4. Reduce health if starving (negative wealth)

    Then update world stability as the average mood of all agents.

    Uses bulk_update at the end to avoid N+1 individual saves.
    """
    agents = list(Agent.objects.filter(simulation=world.simulation, is_alive=True))

    mood_sum = 0.0
    agents_to_update = []

    for agent in agents:
        # Income and expenses
        income = ROLE_INCOME.get(agent.role, DEFAULT_INCOME)
        agent.wealth += income - COST_OF_LIVING

        # Wealth affects mood (ordered from worst to best).
        # Above the satiation threshold the boost decays exponentially toward zero:
        # Kahneman & Deaton (2010) show emotional well-being does not increase
        # beyond a satiation income level. The exponential decay captures this
        # plateau qualitatively; the specific decay rate is a tunable parameter.
        if agent.wealth < 0:
            agent.mood = max(0.0, agent.mood - MOOD_PENALTY_DESTITUTE)
            agent.health = max(0.0, agent.health - HEALTH_PENALTY_STARVING)
        elif agent.wealth < 10:
            agent.mood = max(0.0, agent.mood - MOOD_PENALTY_POOR)
        elif agent.wealth > _WEALTH_SATIATION_THRESHOLD:
            # Kahneman & Deaton (2010): mood boost diminishes above satiation.
            excess = agent.wealth - _WEALTH_SATIATION_THRESHOLD
            diminishing_boost = MOOD_BOOST_WEALTHY * math.exp(-_MOOD_SATIATION_DECAY * excess)
            agent.mood = min(1.0, agent.mood + diminishing_boost)

        agents_to_update.append(agent)
        mood_sum += agent.mood

    if agents_to_update:
        Agent.objects.bulk_update(agents_to_update, ["wealth", "mood", "health"])

    # World stability = average mood of all agents
    agent_count = len(agents_to_update)
    if agent_count > 0:
        world.stability_index = mood_sum / agent_count
    world.save(update_fields=["stability_index"])

"""Government engine -- political cycle orchestrator.

This module implements the main political processing pipeline for a simulation tick.
It ties together institution health, social stratification, corruption dynamics,
indicator updates, regime transitions, elections, and coups into a single
``process_political_cycle`` call.

The engine is fully data-driven by the GOVERNMENT_TYPES configuration:
adding a new regime type requires only a new dictionary entry there.

Scientific grounding:
- Acemoglu, D. & Robinson, J.A. (2006). Economic Origins of Dictatorship and
  Democracy. Cambridge University Press. Endogenous regime transition mechanics.
- Geddes, B. (1999). "What Do We Know About Democratization After Twenty Years?"
  Annual Review of Political Science, 2, 115-144. Regime survival and transition.
- Polity IV Project (Marshall & Gurr, 2020): regime type classification and
  transition scoring. https://www.systemicpeace.org/polityproject.html
- Powell, J.M. & Thyne, C.L. (2011). "Global instances of coups from 1950 to 2010:
  A new dataset." Journal of Peace Research, 48(2), 249-259. Coup frequency data.
"""
from __future__ import annotations

import logging
import random

from django.conf import settings

from epocha.apps.agents.models import Agent, Group, Memory
from epocha.apps.world.government_types import GOVERNMENT_TYPES
from epocha.apps.world.institutions import update_institutions
from epocha.apps.world.models import Government, GovernmentHistory, Institution, World
from epocha.apps.world.stratification import compute_gini, process_corruption, update_social_classes

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Indicator update constants
# ---------------------------------------------------------------------------

# Scale factor for per-cycle institutional_trust delta.
# A 0.1 weight factor on a 0.5 health institution yields +0.05 contribution,
# minus 0.05 base decay = 0.0 net at neutral institutions.
_TRUST_SCALE: float = 0.1

# Base decay applied to institutional_trust each political cycle.
# Represents the natural erosion of trust without active reinforcement.
# Trust decay rate 0.05 per political cycle. Qualitatively consistent with gradual
# institutional erosion observed in declining democracies (Freedom House annual reports
# document such patterns). The specific rate is a tunable parameter; the tick-to-year
# mapping depends on simulation configuration.
_TRUST_DECAY: float = 0.05

# Rate at which repression_level drifts toward the government type's repression_tendency.
# 10% per cycle: a totalitarian regime (tendency=0.9) starting at 0.1 reaches 0.9 in ~22 cycles.
# Source: Freedom House annual repression trend data.
_REPRESSION_DRIFT_RATE: float = 0.10

# Contribution weights for popular_legitimacy calculation.
# Component weights for legitimacy computation are design parameters reflecting the
# assumed relative importance of institutional domains. No empirical source for the
# specific values.
_LEGITIMACY_W_HEALTH: float = 0.20
_LEGITIMACY_W_EDUCATION: float = 0.15
_LEGITIMACY_W_ECONOMY: float = 0.35
_LEGITIMACY_W_MEDIA: float = 0.30

# Media independence threshold below which state propaganda inflates reported legitimacy.
# When media independence < 0.3, we cannot trust media-reported legitimacy signals.
# Source: Freedom House Press Freedom methodology.
_MEDIA_INDEPENDENCE_THRESHOLD: float = 0.3
# Propaganda inflation factor: biased media reports 30% higher than actual.
_PROPAGANDA_FACTOR: float = 0.30

# Contribution weights for military_loyalty calculation.
_LOYALTY_W_HEALTH: float = 0.40
_LOYALTY_W_FUNDING: float = 0.30
_LOYALTY_W_CHARISMA: float = 0.30

# Coup success probability is evaluated stochastically: the computed score is used as
# a probability in a random draw, not as a deterministic threshold. This reflects the
# inherent uncertainty of coup outcomes (Powell & Thyne 2011 report ~50% success rate
# across all attempts 1950-2010).
# _COUP_SUCCESS_THRESHOLD is no longer used; retained as a reference calibration point.
_COUP_SUCCESS_THRESHOLD: float = 0.50

# ---------------------------------------------------------------------------
# Transition condition thresholds
# ---------------------------------------------------------------------------

# Named thresholds used by _evaluate_trigger to map trigger strings to
# indicator comparisons. Each entry is (field, operator, threshold).
#
# Threshold values are simulation design parameters. Regime transition logic is
# inspired by the institutional dynamics described in Acemoglu & Robinson (2006)
# and Geddes (1999), but the specific numeric thresholds are not derived from any
# empirical dataset.
_TRIGGER_CONDITIONS: dict[str, list[tuple[str, str, float]]] = {
    # democracy -> illiberal_democracy
    "low_trust_high_repression": [
        ("institutional_trust", "<", 0.3),
        ("repression_level", ">", 0.35),
    ],
    # democracy -> autocracy
    "very_low_trust_low_military_loyalty": [
        ("institutional_trust", "<", 0.2),
        ("military_loyalty", "<", 0.3),
    ],
    # democracy, illiberal_democracy, junta -> anarchy
    "very_low_stability": [
        ("stability", "<", 0.15),
    ],
    # illiberal_democracy -> autocracy
    "high_repression_low_trust": [
        ("repression_level", ">", 0.55),
        ("institutional_trust", "<", 0.25),
    ],
    # illiberal_democracy -> democracy, kleptocracy -> democracy
    "high_legitimacy_low_corruption": [
        ("popular_legitimacy", ">", 0.65),
        ("corruption", "<", 0.25),
    ],
    # autocracy -> democracy
    "high_legitimacy_low_military_loyalty": [
        ("popular_legitimacy", ">", 0.7),
        ("military_loyalty", "<", 0.35),
    ],
    # autocracy -> totalitarian
    "very_high_repression": [
        ("repression_level", ">", 0.75),
    ],
    # autocracy -> junta
    "very_high_military_loyalty": [
        ("military_loyalty", ">", 0.80),
    ],
    # monarchy -> autocracy
    "low_legitimacy_high_repression": [
        ("popular_legitimacy", "<", 0.3),
        ("repression_level", ">", 0.45),
    ],
    # monarchy -> democracy, theocracy -> democracy, junta -> democracy
    "high_legitimacy_high_trust": [
        ("popular_legitimacy", ">", 0.7),
        ("institutional_trust", ">", 0.6),
    ],
    # oligarchy -> democracy
    "high_legitimacy": [
        ("popular_legitimacy", ">", 0.70),
    ],
    # oligarchy -> autocracy, totalitarian -> anarchy
    "low_stability_low_military_loyalty": [
        ("stability", "<", 0.25),
        ("military_loyalty", "<", 0.35),
    ],
    # oligarchy -> kleptocracy
    "very_high_corruption": [
        ("corruption", ">", 0.75),
    ],
    # theocracy -> autocracy
    "low_legitimacy": [
        ("popular_legitimacy", "<", 0.30),
    ],
    # totalitarian -> autocracy
    "repression_drops": [
        ("repression_level", "<", 0.45),
    ],
    # terrorist_regime -> autocracy, anarchy -> autocracy
    "stability_rises": [
        ("stability", ">", 0.45),
    ],
    # terrorist_regime -> anarchy
    "stability_falls": [
        ("stability", "<", 0.15),
    ],
    # anarchy -> democracy
    "high_trust_high_legitimacy": [
        ("institutional_trust", ">", 0.55),
        ("popular_legitimacy", ">", 0.55),
    ],
    # anarchy -> junta, kleptocracy -> autocracy
    "high_military_loyalty": [
        ("military_loyalty", ">", 0.70),
    ],
    # federation -> anarchy
    "low_stability": [
        ("stability", "<", 0.25),
    ],
    # federation -> democracy
    "high_trust": [
        ("institutional_trust", ">", 0.65),
    ],
    # junta -> autocracy
    "military_loyalty_drops": [
        ("military_loyalty", "<", 0.30),
    ],
}


# ---------------------------------------------------------------------------
# Helper classes and functions
# ---------------------------------------------------------------------------

class _Stub:
    """Placeholder object for a missing institution.

    Provides the same attribute interface as an Institution record so that
    indicator calculations degrade gracefully when an institution has not been
    created yet (e.g. in seeded simulations with partial data).
    """

    def __init__(self, default: float = 0.3) -> None:
        self.health = default
        self.independence = default
        self.funding = default


def _clamp(value: float) -> float:
    """Clamp value to the [0.0, 1.0] indicator range."""
    return max(0.0, min(1.0, value))


def _get_institution(institutions_by_type: dict[str, Institution], key: str) -> Institution | _Stub:
    """Return the institution for the given type key, or a degraded stub."""
    return institutions_by_type.get(key, _Stub())


def _evaluate_trigger(government: Government, trigger: str) -> bool:
    """Return True if all conditions for the given trigger name are satisfied.

    Trigger names map to lists of (field, operator, threshold) tuples defined
    in _TRIGGER_CONDITIONS. If a trigger name is unknown, returns False and logs
    a warning so that new trigger names added to GOVERNMENT_TYPES are caught early.

    Args:
        government: Government instance with current indicator values.
        trigger: Trigger name string from a GOVERNMENT_TYPES transitions entry.

    Returns:
        True when every condition in the trigger is satisfied, False otherwise.
    """
    conditions = _TRIGGER_CONDITIONS.get(trigger)
    if conditions is None:
        logger.warning("Unknown transition trigger %r -- skipping.", trigger)
        return False

    for field, operator, threshold in conditions:
        value = getattr(government, field, None)
        if value is None:
            return False
        if operator == "<" and not (value < threshold):
            return False
        if operator == ">" and not (value > threshold):
            return False

    return True


# ---------------------------------------------------------------------------
# Core indicator update
# ---------------------------------------------------------------------------

def update_government_indicators(simulation) -> None:
    """Recompute all five political indicators from institution health and state.

    The five indicators updated are:
    - institutional_trust: weighted average of justice, media, bureaucracy,
      education, and health institutions, scaled by ``_TRUST_SCALE`` minus
      ``_TRUST_DECAY`` as a base decay representing natural trust erosion.
    - corruption: rises when justice, bureaucracy, and media are weak; resisted
      by the government type's corruption_resistance parameter.
    - popular_legitimacy: weighted combination of health, education, economy,
      and media signals. When media independence < 0.3, media reports are
      upwardly biased by ``_PROPAGANDA_FACTOR``.
    - military_loyalty: military institution health and funding, plus
      head-of-state charisma. Charisma matters most in personalist regimes.
    - repression_level: drifts toward the government type's repression_tendency
      at ``_REPRESSION_DRIFT_RATE`` per cycle.

    All indicators are clamped to [0.0, 1.0] after update.

    Args:
        simulation: Simulation instance.

    Note:
        Silently returns when no Government or World record exists, so the
        function is safe to call even on partially initialised simulations.
    """
    try:
        government = Government.objects.select_related("head_of_state").get(simulation=simulation)
    except Government.DoesNotExist:
        logger.debug("No government for simulation %d; skipping indicator update.", simulation.pk)
        return

    try:
        world = World.objects.get(simulation=simulation)
        # Note: World.stability_index is currently computed as average agent mood in
        # the economy module. It serves as a proxy for economic conditions but does
        # not measure economic performance directly. The new economy app (in
        # development) will provide proper economic indicators.
        economy = world.stability_index
    except World.DoesNotExist:
        economy = 0.5

    type_config = GOVERNMENT_TYPES.get(government.government_type, {})
    repression_tendency = type_config.get("repression_tendency", 0.5)
    corruption_resistance = type_config.get("corruption_resistance", 0.3)

    # Build a lookup from institution_type -> Institution for O(1) access.
    institutions_by_type: dict[str, Institution] = {
        inst.institution_type: inst
        for inst in Institution.objects.filter(simulation=simulation)
    }

    justice = _get_institution(institutions_by_type, "justice")
    education = _get_institution(institutions_by_type, "education")
    health_inst = _get_institution(institutions_by_type, "health")
    military_inst = _get_institution(institutions_by_type, "military")
    media = _get_institution(institutions_by_type, "media")
    bureaucracy = _get_institution(institutions_by_type, "bureaucracy")

    # --- institutional_trust ---
    # Weighted sum of institution health scores, scaled and decayed.
    # Media contribution is modulated by independence: captured media (independence < 0.5)
    # reduces its positive contribution to real institutional trust.
    trust_raw = (
        justice.health * 0.3
        + media.health * media.independence * 0.3
        + bureaucracy.health * 0.2
        + education.health * 0.1
        + health_inst.health * 0.1
    )
    trust_delta = trust_raw * _TRUST_SCALE - _TRUST_DECAY
    government.institutional_trust = _clamp(government.institutional_trust + trust_delta)

    # --- corruption ---
    # Corruption rises when oversight institutions are weak. The government type's
    # corruption_resistance sets a structural ceiling on how fast corruption spreads.
    # Source: Rose-Ackerman & Palifka (2016): oversight gap = 1 - avg(justice, media, bureaucracy).
    # Note: corruption was already adjusted by stratification.py:process_corruption earlier in this
    # political cycle (based on head-of-state personality). This step adds the institutional oversight
    # effect. The stacking is intentional: personality of the head of state AND institutional health
    # both independently influence the corruption index within the same cycle.
    oversight = (justice.health + media.health * media.independence + bureaucracy.health) / 3.0
    corruption_pressure = (1.0 - oversight) * (1.0 - corruption_resistance) * 0.05
    # Slow decay when oversight is strong.
    corruption_decay = oversight * 0.02
    government.corruption = _clamp(government.corruption + corruption_pressure - corruption_decay)

    # --- popular_legitimacy ---
    # Media signal: if media independence is low, the state controls the narrative
    # and reports inflated legitimacy. We model this as a cap on the media
    # contribution rather than a real legitimacy gain.
    if media.independence < _MEDIA_INDEPENDENCE_THRESHOLD:
        media_reported = min(1.0, media.health + _PROPAGANDA_FACTOR)
    else:
        media_reported = media.health

    legitimacy_raw = (
        health_inst.health * _LEGITIMACY_W_HEALTH
        + education.health * _LEGITIMACY_W_EDUCATION
        + economy * _LEGITIMACY_W_ECONOMY
        + media_reported * _LEGITIMACY_W_MEDIA
    )
    # Legitimacy converges toward legitimacy_raw; delta is proportional to gap.
    legitimacy_delta = (legitimacy_raw - government.popular_legitimacy) * 0.15
    government.popular_legitimacy = _clamp(government.popular_legitimacy + legitimacy_delta)

    # --- military_loyalty ---
    head_charisma = government.head_of_state.charisma if government.head_of_state else 0.5
    loyalty_raw = (
        military_inst.health * _LOYALTY_W_HEALTH
        + military_inst.funding * _LOYALTY_W_FUNDING
        + head_charisma * _LOYALTY_W_CHARISMA
    )
    loyalty_delta = (loyalty_raw - government.military_loyalty) * 0.15
    government.military_loyalty = _clamp(government.military_loyalty + loyalty_delta)

    # --- repression_level ---
    # Drifts toward the government type's natural repression tendency.
    repression_delta = (repression_tendency - government.repression_level) * _REPRESSION_DRIFT_RATE
    government.repression_level = _clamp(government.repression_level + repression_delta)

    government.save(update_fields=[
        "institutional_trust",
        "corruption",
        "popular_legitimacy",
        "military_loyalty",
        "repression_level",
    ])

    logger.debug(
        "update_government_indicators: simulation=%d trust=%.3f corruption=%.3f "
        "legitimacy=%.3f loyalty=%.3f repression=%.3f",
        simulation.pk,
        government.institutional_trust,
        government.corruption,
        government.popular_legitimacy,
        government.military_loyalty,
        government.repression_level,
    )


# ---------------------------------------------------------------------------
# Regime transitions
# ---------------------------------------------------------------------------

def check_transitions(simulation) -> str | None:
    """Evaluate all possible regime transitions and execute the most likely one.

    Reads the ``transitions`` dictionary from the current government type's config.
    For each target type, evaluates whether the associated trigger's conditions are
    all satisfied. If multiple targets qualify, the one with the most conditions
    (i.e. the most constrained, hence most specifically triggered) wins.

    On transition:
    - ``government.government_type`` is updated.
    - A ``GovernmentHistory`` record closes the previous era and opens the new one.
    - A public memory is written to all living agents.

    Args:
        simulation: Simulation instance.

    Returns:
        The new government type string if a transition occurred, None otherwise.
    """
    try:
        government = Government.objects.get(simulation=simulation)
    except Government.DoesNotExist:
        return None

    type_config = GOVERNMENT_TYPES.get(government.government_type)
    if not type_config:
        logger.warning(
            "Unknown government type %r for simulation %d; skipping transitions.",
            government.government_type, simulation.pk,
        )
        return None

    current_tick = simulation.current_tick
    transitions = type_config.get("transitions", {})

    # Evaluate all qualifying targets and pick the most constrained.
    qualifying: list[tuple[str, int]] = []
    for target_type, config in transitions.items():
        trigger = config.get("trigger", "")
        if _evaluate_trigger(government, trigger):
            condition_count = len(_TRIGGER_CONDITIONS.get(trigger, []))
            qualifying.append((target_type, condition_count))

    if not qualifying:
        return None

    # Break ties toward the most constrained trigger (more conditions = more specific).
    target_type, _ = max(qualifying, key=lambda x: x[1])

    previous_type = government.government_type
    government.government_type = target_type
    government.formed_at_tick = current_tick
    government.save(update_fields=["government_type", "formed_at_tick"])

    # Close the previous era in history.
    GovernmentHistory.objects.filter(
        simulation=simulation,
        to_tick__isnull=True,
    ).update(to_tick=current_tick)

    # Open the new era.
    GovernmentHistory.objects.create(
        simulation=simulation,
        government_type=target_type,
        head_of_state_name=government.head_of_state.name if government.head_of_state else "",
        ruling_faction_name=government.ruling_faction.name if government.ruling_faction else "",
        from_tick=current_tick,
        transition_cause="indicator_threshold",
    )

    # Broadcast as a public memory to all living agents.
    memory_content = (
        f"The government transitioned from {previous_type} to {target_type} at tick {current_tick}."
    )
    all_agents = Agent.objects.filter(simulation=simulation, is_alive=True)
    Memory.objects.bulk_create([
        Memory(
            agent=agent,
            content=memory_content,
            emotional_weight=0.6,
            source_type=Memory.SourceType.PUBLIC,
            tick_created=current_tick,
        )
        for agent in all_agents
    ])

    logger.info(
        "Regime transition: simulation=%d tick=%d %s -> %s",
        simulation.pk, current_tick, previous_type, target_type,
    )
    return target_type


# ---------------------------------------------------------------------------
# Coups
# ---------------------------------------------------------------------------

def check_coups(simulation, tick: int) -> dict | None:
    """Evaluate faction coup attempts and execute a successful one if it occurs.

    Coup eligibility: the faction must not be the current ruling faction,
    its cohesion must exceed 0.6, and its leader's charisma must exceed 0.5.

    Success probability formula inspired by the coup literature:
        P(success) = cohesion * 0.4 + leader_charisma * 0.3 + (1 - military_loyalty) * 0.3

    The components (faction cohesion, leader charisma, military disloyalty) are
    commonly discussed factors in the coup literature (Powell & Thyne 2011 for
    frequency data, Geddes 1999 for regime vulnerability). The specific weights
    (0.4/0.3/0.3) are tunable design parameters, not derived from any empirical
    model.

    Stochastic evaluation: the computed score is used as a probability in a random
    draw, not as a deterministic threshold. This reflects the inherent uncertainty
    of coup outcomes (Powell & Thyne 2011 report ~50% success rate across all
    attempts 1950-2010).

    When a coup succeeds:
    - ``government.head_of_state`` is set to the faction leader.
    - ``government.ruling_faction`` is set to the faction.
    - ``government.government_type`` is set to "autocracy".
    - A GovernmentHistory record is created.
    - A public memory is written to all living agents.

    Only attempted when stability is below ``EPOCHA_GOVERNMENT_COUP_STABILITY_THRESHOLD``
    (default 0.3) to avoid constant coup churn in stable regimes.

    Args:
        simulation: Simulation instance.
        tick: Current simulation tick.

    Returns:
        A dict with keys ``faction`` (Group) and ``leader`` (Agent) on success,
        None if no coup succeeded.
    """
    try:
        government = Government.objects.select_related("ruling_faction", "head_of_state").get(
            simulation=simulation
        )
    except Government.DoesNotExist:
        return None

    coup_threshold = getattr(settings, "EPOCHA_GOVERNMENT_COUP_STABILITY_THRESHOLD", 0.3)
    if government.stability > coup_threshold:
        return None

    eligible_factions = (
        Group.objects.filter(simulation=simulation)
        .exclude(pk=government.ruling_faction_id)
        .select_related("leader")
        .prefetch_related("members")
    )

    best_candidate: tuple[float, Group, Agent] | None = None

    for faction in eligible_factions:
        leader = faction.leader
        if leader is None or not leader.is_alive:
            continue
        if faction.cohesion <= 0.6 or leader.charisma <= 0.5:
            continue

        success_probability = (
            faction.cohesion * 0.4
            + leader.charisma * 0.3
            + (1.0 - government.military_loyalty) * 0.3
        )

        # Stochastic evaluation: the computed score is used as a probability,
        # not a threshold. This reflects the inherent uncertainty of coup
        # outcomes (Powell & Thyne 2011 report ~50% success rate across all
        # attempts).
        if random.random() < success_probability:
            if best_candidate is None or success_probability > best_candidate[0]:
                best_candidate = (success_probability, faction, leader)

    if best_candidate is None:
        return None

    _, faction, leader = best_candidate
    previous_type = government.government_type

    government.head_of_state = leader
    government.ruling_faction = faction
    government.government_type = "autocracy"
    government.formed_at_tick = tick
    government.save(update_fields=["head_of_state", "ruling_faction", "government_type", "formed_at_tick"])

    # Close any open history era.
    GovernmentHistory.objects.filter(
        simulation=simulation,
        to_tick__isnull=True,
    ).update(to_tick=tick)

    GovernmentHistory.objects.create(
        simulation=simulation,
        government_type="autocracy",
        head_of_state_name=leader.name,
        ruling_faction_name=faction.name,
        from_tick=tick,
        transition_cause="coup",
    )

    memory_content = (
        f"{leader.name} led a coup at tick {tick}, overthrowing the {previous_type} "
        f"and establishing an autocracy."
    )
    all_agents = Agent.objects.filter(simulation=simulation, is_alive=True)
    Memory.objects.bulk_create([
        Memory(
            agent=agent,
            content=memory_content,
            emotional_weight=0.8,
            source_type=Memory.SourceType.PUBLIC,
            tick_created=tick,
        )
        for agent in all_agents
    ])

    logger.info(
        "Coup succeeded: simulation=%d tick=%d faction=%r leader=%r",
        simulation.pk, tick, faction.name, leader.name,
    )
    return {"faction": faction, "leader": leader}


# ---------------------------------------------------------------------------
# Stability update
# ---------------------------------------------------------------------------

def _update_stability(simulation) -> None:
    """Recompute government stability from weighted indicators.

    Stability is a composite of economy, popular legitimacy, and military loyalty,
    weighted by the current government type's ``stability_weights`` configuration.
    Economy is read from ``World.stability_index``, which is updated by the
    economic engine. The weighted formula follows Bueno de Mesquita et al. (2003):
    regime stability derives from the satisfaction of the winning coalition
    (modelled here as the weighted combination of key resource holders).

    Reference: Bueno de Mesquita et al. (2003). "The Logic of Political Survival."
    MIT Press. Chapter 3: coalition satisfaction and regime durability.

    Args:
        simulation: Simulation instance.
    """
    try:
        government = Government.objects.get(simulation=simulation)
    except Government.DoesNotExist:
        return

    try:
        world = World.objects.get(simulation=simulation)
        # Note: World.stability_index is currently computed as average agent mood in
        # the economy module. It serves as a proxy for economic conditions but does
        # not measure economic performance directly. See update_government_indicators.
        economy = world.stability_index
    except World.DoesNotExist:
        economy = 0.5

    type_config = GOVERNMENT_TYPES.get(government.government_type, {})
    weights = type_config.get("stability_weights", {"economy": 0.4, "legitimacy": 0.4, "military": 0.2})

    stability = (
        economy * weights["economy"]
        + government.popular_legitimacy * weights["legitimacy"]
        + government.military_loyalty * weights["military"]
    )
    government.stability = _clamp(stability)
    government.save(update_fields=["stability"])

    logger.debug(
        "_update_stability: simulation=%d stability=%.3f", simulation.pk, government.stability
    )


# ---------------------------------------------------------------------------
# Main orchestrator
# ---------------------------------------------------------------------------

def process_political_cycle(simulation, tick: int) -> None:
    """Run the full political cycle for one government interval.

    This is the main entry point called by the tick engine every
    ``EPOCHA_GOVERNMENT_CYCLE_INTERVAL`` ticks (default: 10).

    Execution order:
    1. Institution health update (government type effects + funding + entropy).
    2. Social class reassignment by wealth percentile.
    3. Corruption extraction by agents in power.
    4. Government indicator update (trust, corruption, legitimacy, loyalty, repression).
    5. Regime transition check (indicator-threshold-based).
    6. Election (if the current type supports elections and the election interval
       has elapsed since ``last_election_tick``).
    7. Coup check (only when stability is below the coup threshold).
    8. Stability recomputation from updated indicators.

    Args:
        simulation: Simulation instance.
        tick: Current simulation tick.
    """
    logger.info("process_political_cycle: simulation=%d tick=%d", simulation.pk, tick)

    # Step 1: institution health dynamics.
    update_institutions(simulation)

    # Step 2: social class mobility.
    update_social_classes(simulation)

    # Step 3: corruption extraction.
    process_corruption(simulation, tick)

    # Step 4: recompute political indicators.
    update_government_indicators(simulation)

    # Step 5: check for regime transitions.
    check_transitions(simulation)

    # Step 6: elections (reload government after potential transition in step 5).
    try:
        government = Government.objects.get(simulation=simulation)
    except Government.DoesNotExist:
        return

    type_config = GOVERNMENT_TYPES.get(government.government_type, {})
    election_enabled = type_config.get("election_enabled", False)
    election_interval = getattr(settings, "EPOCHA_GOVERNMENT_ELECTION_INTERVAL", 50)

    if election_enabled and (tick - government.last_election_tick) >= election_interval:
        from epocha.apps.world.election import run_election  # avoid circular import at module level
        run_election(simulation, tick)

    # Step 7: coup attempt.
    check_coups(simulation, tick)

    # Step 8: recompute stability from updated indicators.
    _update_stability(simulation)

    logger.info(
        "process_political_cycle complete: simulation=%d tick=%d type=%r",
        simulation.pk, tick, government.government_type,
    )

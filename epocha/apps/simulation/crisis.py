"""Epochal Crisis detection engine.

Crises are composite threshold events: they fire when a set of simulation
KPIs simultaneously breach empirically-grounded thresholds. Each definition
cites the scientific source that justifies its threshold values.

A cooldown mechanism (_CRISIS_COOLDOWN_TICKS) prevents the same crisis from
re-firing until the simulation has advanced enough ticks, avoiding event spam
during sustained instability.
"""
from django.db.models import Max

from epocha.apps.agents.models import Agent, Group, Memory
from epocha.apps.simulation.models import Event, SimulationSnapshot

# Minimum tick gap before the same crisis type can fire again.
# 10 ticks provides enough separation to avoid duplicate events during
# sustained threshold breaches while still capturing re-emergent crises.
_CRISIS_COOLDOWN_TICKS = 10

# Event title prefix used for cooldown detection queries.
_CRISIS_TITLE_PREFIX = "[EPOCHAL CRISIS]"

# Maps snapshot field names to (model_field, direction) tuples.
# "above" means crisis fires when value > threshold;
# "below" means crisis fires when value < threshold.
_SNAPSHOT_CONDITIONS: dict[str, tuple[str, str]] = {
    "gini_above": ("gini_coefficient", "above"),
    "government_stability_below": ("government_stability", "below"),
    "institutional_trust_below": ("institutional_trust", "below"),
    "corruption_above": ("corruption", "above"),
    "popular_legitimacy_below": ("popular_legitimacy", "below"),
    "avg_mood_below": ("avg_mood", "below"),
    "military_loyalty_below": ("military_loyalty", "below"),
}

# Conditions that require a live database query rather than a snapshot field.
_LIVE_CONDITIONS: set[str] = {"max_faction_cohesion_above"}

# Crisis definitions. Each entry documents its scientific grounding.
# Threshold values are calibrated against historical political-science datasets
# cited inline per crisis.
CRISIS_DEFINITIONS: dict[str, dict] = {
    "inequality_crisis": {
        # Gini >= 0.6 is the empirical threshold above which social unrest
        # becomes likely; government instability compounds the risk.
        # Source: Milanovic (2016) "Global Inequality", Harvard UP; World Bank
        # Development Report 2006, Table 4 (Gini of 0.60+ correlates with
        # heightened civil conflict probability).
        "label": "Inequality Crisis",
        "description": (
            "Extreme wealth concentration combined with weak governance has destabilised "
            "the social contract. Public grievance is approaching critical mass."
        ),
        "conditions": {
            "gini_above": 0.6,
            "government_stability_below": 0.4,
        },
        "severity": 0.7,
    },
    "coup_risk": {
        # Military loyalty < 0.3 signals near-defection; a highly cohesive
        # faction (cohesion > 0.7) provides the organisational capacity for
        # a coup attempt.
        # Source: Luttwak (1979) "Coup d'Etat: A Practical Handbook" (loyalty
        # threshold); Powell & Thyne (2011) "Coups d'Etat or Coups d'Autocracy?",
        # Foreign Policy Analysis 7:3 (faction cohesion as enabling condition).
        "label": "Coup Risk",
        "description": (
            "Military loyalty has collapsed and a highly organised faction has emerged. "
            "Conditions for an extra-constitutional seizure of power are present."
        ),
        "conditions": {
            "military_loyalty_below": 0.3,
            "max_faction_cohesion_above": 0.7,
        },
        "severity": 0.9,
    },
    "institutional_collapse": {
        # Trust < 0.2 and corruption > 0.6 identify a state where institutions
        # have lost legitimacy and are captured by predatory actors.
        # Source: Acemoglu & Robinson (2012) "Why Nations Fail", ch. 8;
        # Transparency International CPI research notes that societies with
        # CPI scores equivalent to corruption > 0.6 experience institutional
        # erosion cascades.
        "label": "Institutional Collapse",
        "description": (
            "Public trust in institutions has reached critically low levels while "
            "corruption has become systemic. The state is losing its capacity to govern."
        ),
        "conditions": {
            "institutional_trust_below": 0.2,
            "corruption_above": 0.6,
        },
        "severity": 0.85,
    },
    "revolution_risk": {
        # Legitimacy < 0.2 removes the normative barrier to revolt; Gini > 0.5
        # provides the material grievance. Tocqueville's paradox notwithstanding,
        # this combination predicts mass mobilisation.
        # Source: Skocpol (1979) "States and Social Revolutions", Cambridge UP;
        # Gurr (1970) "Why Men Rebel" (relative deprivation + legitimacy deficit).
        "label": "Revolution Risk",
        "description": (
            "The government has lost popular legitimacy while inequality has created "
            "profound social grievances. Revolutionary mobilisation is plausible."
        ),
        "conditions": {
            "popular_legitimacy_below": 0.2,
            "gini_above": 0.5,
        },
        "severity": 0.8,
    },
    "social_despair": {
        # avg_mood < 0.25 captures a society in collective psychological distress;
        # government instability < 0.3 means no credible relief is forthcoming.
        # Source: Layard (2005) "Happiness: Lessons from a New Science", ch. 5;
        # Helliwell, Layard & Sachs (2022) World Happiness Report — populations
        # with life-evaluation scores in the lowest quartile under unstable
        # governance show amplified social disintegration.
        "label": "Social Despair",
        "description": (
            "Collective mood has collapsed to historic lows under an unstable government. "
            "The population is experiencing pervasive hopelessness and social disintegration."
        ),
        "conditions": {
            "avg_mood_below": 0.25,
            "government_stability_below": 0.3,
        },
        "severity": 0.75,
    },
}


def detect_crises(simulation, snapshot: SimulationSnapshot) -> list[dict]:
    """Evaluate all crisis definitions against the current snapshot and fire any that trigger.

    For each crisis whose composite conditions are all met and whose cooldown
    has expired, this function:
      - Creates an Event record with type "political".
      - Broadcasts a public Memory to every alive agent via bulk_create.
      - Returns a list of dicts describing the crises that fired.

    Args:
        simulation: Simulation instance for the current run.
        snapshot: SimulationSnapshot captured at the current tick.

    Returns:
        List of dicts, one per triggered crisis, each containing at minimum
        a "type" key with the crisis name.
    """
    fired: list[dict] = []
    for crisis_type, crisis in CRISIS_DEFINITIONS.items():
        if _is_on_cooldown(simulation, crisis_type, snapshot.tick):
            continue
        all_conditions_met = all(
            _evaluate_condition(simulation, snapshot, condition_name, threshold)
            for condition_name, threshold in crisis["conditions"].items()
        )
        if all_conditions_met:
            _fire_crisis(simulation, snapshot.tick, crisis_type, crisis)
            fired.append({"type": crisis_type, **crisis})
    return fired


def _evaluate_condition(
    simulation,
    snapshot: SimulationSnapshot,
    condition_name: str,
    threshold: float,
) -> bool:
    """Check whether a single named condition is met.

    Snapshot-backed conditions read directly from the snapshot fields.
    Live conditions execute a fresh database query.

    Args:
        simulation: Simulation instance (needed for live queries).
        snapshot: Current SimulationSnapshot.
        condition_name: Key from _SNAPSHOT_CONDITIONS or _LIVE_CONDITIONS.
        threshold: Numeric threshold value from the crisis definition.

    Returns:
        True if the condition is satisfied, False otherwise.

    Raises:
        ValueError: If condition_name is not recognised in either lookup.
    """
    if condition_name in _LIVE_CONDITIONS:
        if condition_name == "max_faction_cohesion_above":
            result = Group.objects.filter(simulation=simulation, cohesion__gt=0).aggregate(
                max_cohesion=Max("cohesion")
            )
            max_cohesion = result["max_cohesion"] or 0.0
            return max_cohesion > threshold
        # Unreachable if _LIVE_CONDITIONS is kept in sync, but guards future additions.
        raise ValueError(f"Unhandled live condition: {condition_name}")  # pragma: no cover

    if condition_name not in _SNAPSHOT_CONDITIONS:
        raise ValueError(f"Unknown condition: {condition_name}")  # pragma: no cover

    field, direction = _SNAPSHOT_CONDITIONS[condition_name]
    value = getattr(snapshot, field)
    if direction == "above":
        return value > threshold
    return value < threshold


def _is_on_cooldown(simulation, crisis_type: str, current_tick: int) -> bool:
    """Return True if this crisis type fired too recently to fire again.

    Checks whether an Event with the matching crisis title prefix and type
    exists within the last _CRISIS_COOLDOWN_TICKS ticks.

    Args:
        simulation: Simulation instance to scope the query.
        crisis_type: The CRISIS_DEFINITIONS key.
        current_tick: Tick of the snapshot being evaluated.

    Returns:
        True if a matching Event was created within the cooldown window.
    """
    label = CRISIS_DEFINITIONS[crisis_type]["label"]
    title = f"{_CRISIS_TITLE_PREFIX} {label}"
    min_tick = current_tick - _CRISIS_COOLDOWN_TICKS
    return simulation.events.filter(
        title=title,
        tick__gte=min_tick,
        tick__lt=current_tick,
    ).exists()


def _fire_crisis(simulation, tick: int, crisis_type: str, crisis: dict) -> None:
    """Persist the crisis as an Event and broadcast a public Memory to all alive agents.

    The Event is created with type "political" and a severity drawn from the
    crisis definition. A public Memory is bulk-created for every alive agent so
    that the crisis propagates into the agents' cognitive context on their next
    decision turn.

    Args:
        simulation: Simulation instance.
        tick: Current simulation tick.
        crisis_type: The CRISIS_DEFINITIONS key (used in memory content).
        crisis: The crisis definition dict.
    """
    label = crisis["label"]
    title = f"{_CRISIS_TITLE_PREFIX} {label}"
    description = crisis["description"]
    severity = crisis["severity"]

    Event.objects.create(
        simulation=simulation,
        tick=tick,
        event_type=Event.EventType.POLITICAL,
        title=title,
        description=description,
        severity=severity,
    )

    memory_content = f"[EPOCHAL CRISIS] {label}: {description}"
    alive_agents = list(
        Agent.objects.filter(simulation=simulation, is_alive=True).values_list("id", flat=True)
    )
    if not alive_agents:
        return

    Memory.objects.bulk_create([
        Memory(
            agent_id=agent_id,
            content=memory_content,
            emotional_weight=severity,
            source_type=Memory.SourceType.PUBLIC,
            reliability=1.0,
            tick_created=tick,
        )
        for agent_id in alive_agents
    ])

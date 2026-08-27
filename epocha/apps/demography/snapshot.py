"""Per-tick aggregate demographic state: the `PopulationSnapshot` writer.

Plan 1 modelled `PopulationSnapshot` and nothing ever wrote one, so a run's
aggregate demographic state existed only as whatever a reader could
reconstruct by hand from the agent table. That is the machine historical
validation needs: comparing a simulated population against Human Mortality
Database schedules or Wrigley-Schofield series means comparing rates per
tick, and rates that are never computed cannot be compared.

**Definitions.** The rate measures follow the standard demographic
conventions set out in Preston, Heuveline and Guillot, *Demography:
Measuring and Modeling Population Processes* (Wiley-Blackwell, 2001), the
discipline's reference text for population measurement. No page is cited
because none was verified: the definitions used here are the conventional
ones, and each is written out below in the exact operational form this module
computes, so a reader can check the code against the definition rather than
against a memory of it.

- **Crude birth rate**: live births per 1000 population per year. Measured
  over one tick and annualised, since a tick is a fraction of a year.
- **Crude death rate**: deaths per 1000 population per year, same treatment.
- **Total fertility rate (instantaneous)**: the sum, over the single years of
  age in the fertile window, of the age-specific fertility rates observed in
  this tick, annualised. It answers "how many children would a woman bear if
  this tick's rates held for her whole reproductive life".

**A limit worth stating rather than discovering.** All three are computed
from a single tick's events over a small population, so they are extremely
noisy: one birth in a population of a few hundred annualises into a large
rate. They are per-tick observations, not estimates, and any validation that
consumes them must smooth over many ticks. Recording them per tick is what
makes that smoothing possible; presenting a single tick's value as a
demographic rate of the simulated society would be wrong.
"""

from __future__ import annotations

from typing import Any

HOURS_PER_YEAR = 8760.0
AGE_BUCKET_YEARS = 5
OLDEST_BUCKET_START = 100


def write_population_snapshot(context: Any) -> None:
    """Write this tick's `PopulationSnapshot`, replacing any existing one.

    Last step of the declared order: the snapshot describes the tick, so it
    runs once every mutation of that tick has happened.

    Idempotent by `(simulation, tick)`, so a re-run of the same tick corrects
    the row instead of adding a second, contradictory one.

    Query shape: a small fixed number of aggregate reads plus one write.
    Nothing here scales with the population in queries -- the counting is
    done in Python over one pass of the living agents, which the block has to
    read anyway.
    """
    from epocha.apps.agents.models import Agent
    from epocha.apps.demography.models import Couple, DemographyEvent, PopulationSnapshot

    simulation = context.simulation
    tick = context.tick
    ticks_per_year = HOURS_PER_YEAR / max(1e-9, _tick_duration_hours(simulation))

    living = list(
        Agent.objects.filter(simulation=simulation, is_alive=True)
        .only("id", "gender", "birth_tick", "age", "zone_id", "parent_agent_id")
        .order_by("id")
    )
    total_alive = len(living)

    ages = [_age_of(agent, tick, ticks_per_year) for agent in living]
    males = sum(1 for a in living if a.gender == Agent.Gender.MALE)
    females = sum(1 for a in living if a.gender == Agent.Gender.FEMALE)

    events = list(
        DemographyEvent.objects.filter(simulation=simulation, tick=tick).values(
            "event_type", "primary_agent_id", "secondary_agent_id", "payload"
        )
    )
    births = [e for e in events if e["event_type"] == DemographyEvent.EventType.BIRTH]
    deaths = [e for e in events if e["event_type"] == DemographyEvent.EventType.DEATH]
    migrations = [e for e in events if e["event_type"] == DemographyEvent.EventType.MIGRATION]

    couples_active = Couple.objects.filter(
        simulation=simulation, dissolved_at_tick__isnull=True
    ).count()

    PopulationSnapshot.objects.update_or_create(
        simulation=simulation,
        tick=tick,
        defaults={
            "total_alive": total_alive,
            "age_pyramid": _age_pyramid(living, ages),
            "sex_ratio": (males / females) if females else float(males),
            "avg_age": (sum(ages) / total_alive) if total_alive else 0.0,
            "crude_birth_rate": _per_thousand_per_year(len(births), total_alive, ticks_per_year),
            "crude_death_rate": _per_thousand_per_year(len(deaths), total_alive, ticks_per_year),
            "tfr_instant": _tfr_instant(births, living, ages, ticks_per_year),
            "net_migration_by_zone": _net_migration(migrations),
            "couples_active": couples_active,
            "avg_household_size": _avg_household_size(
                living,
                ages,
                simulation,
                adulthood_age=float(context.template["migration"]["adulthood_age"]),
            ),
        },
    )


def _age_of(agent: Any, tick: int, ticks_per_year: float) -> float:
    """Age in years from `birth_tick`, the only source that advances."""
    if agent.birth_tick is None:
        return float(agent.age or 0)
    return (tick - agent.birth_tick) / ticks_per_year


def _age_pyramid(living: list, ages: list[float]) -> list[list[int]]:
    """Five-year buckets of `[low, high, males, females]`.

    Only non-empty buckets are stored: a fixed grid of twenty entries mostly
    at zero would make the row larger and no more informative, and a reader
    can reconstruct the gaps.
    """
    from epocha.apps.agents.models import Agent

    buckets: dict[int, list[int]] = {}
    for agent, age in zip(living, ages, strict=True):
        low = min(int(age) // AGE_BUCKET_YEARS * AGE_BUCKET_YEARS, OLDEST_BUCKET_START)
        entry = buckets.setdefault(low, [0, 0])
        if agent.gender == Agent.Gender.MALE:
            entry[0] += 1
        elif agent.gender == Agent.Gender.FEMALE:
            entry[1] += 1
    return [
        [low, low + AGE_BUCKET_YEARS - 1, counts[0], counts[1]]
        for low, counts in sorted(buckets.items())
    ]


def _per_thousand_per_year(count: int, population: int, ticks_per_year: float) -> float:
    """Events per 1000 population per year, from one tick's count."""
    if not population:
        return 0.0
    return count / population * 1000.0 * ticks_per_year


def _tfr_instant(
    births: list[dict],
    living: list,
    ages: list[float],
    ticks_per_year: float,
) -> float:
    """Sum of this tick's age-specific fertility rates, annualised.

    The age-specific rate at age x is this tick's births to mothers of age x
    divided by the women of age x alive at the tick; the TFR is their sum
    over the fertile window. With one tick of events the sum is dominated by
    whichever ages happened to give birth, which is why the module docstring
    calls these observations rather than estimates.
    """
    from epocha.apps.agents.models import Agent

    women_by_age: dict[int, int] = {}
    for agent, age in zip(living, ages, strict=True):
        if agent.gender == Agent.Gender.FEMALE:
            women_by_age[int(age)] = women_by_age.get(int(age), 0) + 1

    age_by_agent_id = {
        agent.id: int(age) for agent, age in zip(living, ages, strict=True)
    }
    births_by_age: dict[int, int] = {}
    for event in births:
        mother_age = age_by_agent_id.get(event["secondary_agent_id"])
        if mother_age is None:
            continue
        births_by_age[mother_age] = births_by_age.get(mother_age, 0) + 1

    total = 0.0
    for age, count in births_by_age.items():
        women = women_by_age.get(age, 0)
        if women:
            total += count / women * ticks_per_year
    return total


def _net_migration(migrations: list[dict]) -> dict[str, int]:
    """Net arrivals minus departures per zone, keyed by zone id as a string.

    JSON object keys are strings, so an integer zone id would come back from
    the database as one anyway; writing it as a string keeps what is read
    identical to what was written.
    """
    net: dict[str, int] = {}
    for event in migrations:
        payload = event.get("payload") or {}
        origin = payload.get("from_zone")
        destination = payload.get("to_zone")
        if origin is not None:
            net[str(origin)] = net.get(str(origin), 0) - 1
        if destination is not None:
            net[str(destination)] = net.get(str(destination), 0) + 1
    return net


def _avg_household_size(
    living: list,
    ages: list[float],
    simulation: Any,
    adulthood_age: float,
) -> float:
    """Living agents divided by households.

    A household is a couple with the minors in its care, or a single adult.
    The model has no household entity, so it is derived: partners share one,
    a MINOR child -- younger than the era template's `migration.adulthood_age`,
    the same threshold household migration coordination uses -- belongs to
    its living parent's, and everyone else is their own. The age test is
    load-bearing: without it a sixty-year-old files under his
    eighty-five-year-old father's roof, and the series overstates household
    size by exactly the adult children of living parents. Stating the
    derivation matters because "household" is the unit historical sources
    report, and a different derivation would produce a different series that
    looks equally plausible.
    """
    from epocha.apps.demography.models import Couple

    if not living:
        return 0.0

    living_ids = {agent.id for agent in living}
    partner_of: dict[int, int] = {}
    for a_id, b_id in Couple.objects.filter(
        simulation=simulation, dissolved_at_tick__isnull=True
    ).values_list("agent_a_id", "agent_b_id"):
        partner_of[a_id] = b_id
        partner_of[b_id] = a_id

    households: set[tuple[int, ...]] = set()
    for agent, age in zip(living, ages, strict=True):
        is_anchored_minor = agent.parent_agent_id in living_ids and age < adulthood_age
        anchor = agent.parent_agent_id if is_anchored_minor else agent.id
        partner = partner_of.get(anchor)
        key = tuple(sorted((anchor, partner))) if partner else (anchor,)
        households.add(key)

    return len(living) / len(households) if households else 0.0


def _tick_duration_hours(simulation: Any) -> float:
    from epocha.apps.world.models import World

    world = World.objects.filter(simulation=simulation).first()
    return float(getattr(world, "tick_duration_hours", 24.0) or 24.0) if world else 24.0

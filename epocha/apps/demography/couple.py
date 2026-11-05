"""Couple formation infrastructure for demography: Gale-Shapley stable
matching, homogamy scoring (Kalmijn 1998), and runtime pair_bond /
separate intent handling with canonical ordering enforcement.

Sources:
- Gale, D. & Shapley, L.S. (1962). College admissions and the stability
  of marriage. American Mathematical Monthly 69(1), 9-15.
- Kalmijn, M. (1998). Intermarriage and homogamy. Annual Review of
  Sociology 24, 395-421.
- Goode, W.J. (1963). World Revolution and Family Patterns (arranged
  marriage patterns).
"""

from __future__ import annotations

import logging
import math
from collections import deque
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING

from django.db.models import Q

from epocha.apps.demography.nuptiality import first_marriage_schedule

if TYPE_CHECKING:
    # Type-check-only import: the runtime imports live inside the functions that
    # touch the ORM, to avoid a circular import at module load. With
    # `from __future__ import annotations`, annotations are lazy strings, so this
    # block is never executed at runtime.
    from epocha.apps.agents.models import Agent
    from epocha.apps.demography.models import Couple

logger = logging.getLogger(__name__)


def _ordered_pair(agent_a, agent_b) -> tuple:
    """Return (lower_id_agent, higher_id_agent) for Couple canonical ordering.

    The Couple model enforces agent_a.id < agent_b.id via CheckConstraint.
    Every caller that creates a Couple must route both partners through
    this helper to avoid IntegrityError.
    """
    if agent_a.id is None or agent_b.id is None:
        raise ValueError("Both agents must be saved (have a primary key) before forming a Couple")
    if agent_a.id == agent_b.id:
        raise ValueError("Cannot form a Couple between an agent and itself")
    if agent_a.id < agent_b.id:
        return agent_a, agent_b
    return agent_b, agent_a


def is_in_active_couple(agent) -> bool:
    """True when the agent is one of the partners in an undissolved Couple."""
    from epocha.apps.demography.models import Couple

    return Couple.objects.filter(
        Q(agent_a=agent) | Q(agent_b=agent),
        dissolved_at_tick__isnull=True,
    ).exists()


def active_couple_partners(simulation) -> dict[int, int | None]:
    """Each partnered agent id mapped to the id of its partner.

    `is_in_active_couple` and `active_couple_for` answer this one agent at a
    time. A caller iterating a whole population -- the fertility step is the
    one that does -- would pay a query per candidate for membership and
    another per birth for the partner, which is the per-agent and per-event
    cost FR-016 and FR-016a forbid. Both answers come from the same single
    read here: membership is `agent_id in mapping`, the partner is the value.

    Partner FKs are nullable (`SET_NULL` preserves the genealogical record
    when an agent row goes away), so a value can be `None`: the surviving
    half of a half-null couple is a member with no partner to name. Testing
    membership with `in` is therefore correct and testing it by truthiness of
    the value is not.

    Cost: exactly one query, whatever the population.
    """
    from epocha.apps.demography.models import Couple

    pairs = Couple.objects.filter(
        simulation=simulation,
        dissolved_at_tick__isnull=True,
    ).values_list("agent_a_id", "agent_b_id")
    partners: dict[int, int | None] = {}
    for a_id, b_id in pairs:
        # Each side is entered on its own, so a half-null row still makes its
        # surviving partner a MEMBER -- with the value `None`, which says
        # there is no partner to name. Dropping the whole row instead would
        # make this function disagree with `is_in_active_couple`, which
        # matches on whichever column is set, for the one agent the two are
        # documented to answer identically.
        if a_id is not None:
            partners[a_id] = b_id
        if b_id is not None:
            partners[b_id] = a_id
    return partners


def active_couple_for(agent):
    """Return the agent's active Couple (or None)."""
    from epocha.apps.demography.models import Couple

    return Couple.objects.filter(
        Q(agent_a=agent) | Q(agent_b=agent),
        dissolved_at_tick__isnull=True,
    ).first()


def pair_key(a_id: int, b_id: int) -> tuple[int, int]:
    """Order-free key of a pair of agents: `(lower id, higher id)`.

    The sentiment map is keyed by it, so a lookup does not depend on which
    side of the pair is the seeker.
    """
    return (a_id, b_id) if a_id < b_id else (b_id, a_id)


def read_sentiments(seeker_ids, candidate_ids) -> dict[tuple[int, int], float]:
    """Sentiment of every acquainted seeker-candidate pair, in one query.

    The homogamy score used to read the database once per scored pair
    (`Relationship...first()`), which the market would multiply by every
    pair of every tick. This reads all the pairs at once; the score then
    only looks a key up.

    A pair can carry several `Relationship` rows (`unique_together` includes
    `relation_type`) and in either direction. The row kept is the lowest
    primary key, which is the row `.first()` returned (the model has no
    `Meta.ordering`, so `.first()` orders by pk): the choice of the relation
    type is arbitrary, a known limit left to the owners of the agents model
    (plan R4). A pair without a row is absent from the map.

    Queryset dependencies: none beyond the single filtered `values_list`.
    """
    from epocha.apps.agents.models import Relationship

    seekers, candidates = set(seeker_ids), set(candidate_ids)
    rows = (
        Relationship.objects.filter(
            Q(agent_from_id__in=seekers, agent_to_id__in=candidates)
            | Q(agent_from_id__in=candidates, agent_to_id__in=seekers)
        )
        .order_by("id")
        .values_list("agent_from_id", "agent_to_id", "sentiment")
    )
    sentiments: dict[tuple[int, int], float] = {}
    for agent_from_id, agent_to_id, sentiment in rows:
        sentiments.setdefault(pair_key(agent_from_id, agent_to_id), sentiment)
    return sentiments


@dataclass(frozen=True)
class MarriageHistory:
    """What the dissolved couples of a simulation say about each agent.

    Attributes:
        ever_partnered: ids of the agents who were in a couple that has since
            ended, for whatever reason (a deceased partner has no id left
            here). The remarriage rate of the marriage market applies to
            these women, the first-marriage schedule to the others.
        widowed_at_tick: id of each agent whose partner died, mapped to the
            tick of the latest such death. Mourning follows death only, not
            separation.
    """

    ever_partnered: frozenset[int]
    widowed_at_tick: Mapping[int, int]


def read_marriage_history(simulation) -> MarriageHistory:
    """Read the marriage history of a simulation in one query.

    `dissolve_on_death` nulls the deceased partner's foreign key and leaves
    the survivor's, so in a couple dissolved by death the non-null side is the
    widow or widower. A separated or annulled couple keeps both sides: both
    were partnered, neither is widowed. A couple still active contributes
    nothing, and a couple whose partners both died holds no living agent.

    Queryset dependencies: one `values_list` on the simulation's dissolved
    couples, no join.
    """
    from epocha.apps.demography.models import Couple

    rows = Couple.objects.filter(
        simulation=simulation, dissolved_at_tick__isnull=False
    ).values_list("agent_a_id", "agent_b_id", "dissolved_at_tick", "dissolution_reason")
    ever_partnered: set[int] = set()
    widowed_at_tick: dict[int, int] = {}
    for agent_a_id, agent_b_id, dissolved_at_tick, reason in rows:
        survivors = [agent_id for agent_id in (agent_a_id, agent_b_id) if agent_id is not None]
        ever_partnered.update(survivors)
        if reason == Couple.DissolutionReason.DEATH:
            for survivor in survivors:
                widowed_at_tick[survivor] = max(dissolved_at_tick, widowed_at_tick.get(survivor, 0))
    return MarriageHistory(frozenset(ever_partnered), widowed_at_tick)


def mourning_ticks(couple_config: dict, tick_duration_hours: float, acceleration: float) -> int:
    """Length of the era's mourning interval, in ticks.

    `ceil(mourning_days * 24 / (tick_duration_hours * acceleration))`: a tick
    covers `tick_duration_hours * acceleration` hours of simulated time, and a
    partial tick of mourning counts as a whole one, so the interval is never
    shortened. The conversion is written literally, not through an inverted
    tick length: on a daily world the inverted form reads 365.00000000000006
    and rounds up to 366.

    The interval itself, `mourning_days`, is a tunable heuristic of the era
    template, not a measured quantity (no cited source; Appendix A of the
    whitepaper labels it so).
    """
    return math.ceil(couple_config["mourning_days"] * 24 / (tick_duration_hours * acceleration))


def homogamy_score(
    a,
    b,
    weights: dict,
    *,
    sentiments: dict[tuple[int, int], float],
    ages: dict[int, float],
    age_tolerance_years: float = 10.0,
) -> float:
    """Kalmijn-inspired compatibility score between two candidate partners.

    Components (all in [0, 1] before weighting):
    - class similarity: 1.0 if same social_class, 0.0 otherwise
    - education proximity: exp(-|e_a - e_b|)
    - age proximity: exp(-|age_a - age_b| / age_tolerance), on the canonical
      ages in `ages` (`age_in_years` over `birth_tick`), not on the `age`
      column, which holds completed years only and is refreshed by the
      mortality step after step 2, so it can lag the canonical age by up to
      a year and would give the score a second source of age
    - relationship: the sentiment in [-1, 1] of the pair, from the
      per-tick `sentiments` map (`read_sentiments`), mapped to [0, 1]; a pair
      absent from the map reads the neutral 0.5

    Returns the weighted sum. Weights come from the era template and are
    design heuristics (see spec §Sezione 3). The function reads no database
    row: the two maps are computed once per tick by the caller, so scoring a
    pair costs no query.
    """
    same_class = 1.0 if a.social_class == b.social_class else 0.0
    edu_diff = abs(float(a.education_level or 0.0) - float(b.education_level or 0.0))
    edu_prox = math.exp(-edu_diff)
    age_diff = abs(ages[a.id] - ages[b.id])
    age_prox = math.exp(-age_diff / max(1e-9, age_tolerance_years))

    sentiment = sentiments.get(pair_key(a.id, b.id))
    relationship_score = 0.5 if sentiment is None else (sentiment + 1.0) / 2.0

    return (
        float(weights.get("w_class", 0.4)) * same_class
        + float(weights.get("w_edu", 0.25)) * edu_prox
        + float(weights.get("w_age", 0.20)) * age_prox
        + float(weights.get("w_relationship", 0.15)) * relationship_score
    )


def stable_matching(
    proposers: list,
    respondents: list,
    score_fn,
) -> list[tuple]:
    """Gale-Shapley stable matching.

    Returns a list of (proposer, respondent) pairs. Both sides must rank
    each other via score_fn(proposer, respondent) -> float. Higher score
    is preferred.

    Complexity: O(n·m·log m) for n proposers and m respondents: at most n·m
    proposals (Gale & Shapley 1962), each proposer's list is sorted once
    (m·log m), and the score function is evaluated 2·n·m times (once per pair
    to rank each proposer's list, once per pair to build each respondent's
    table). Gale & Shapley (1962) prove existence and stability.

    When len(proposers) != len(respondents), the smaller side is fully
    matched and the larger side has unmatched members.
    """
    # Build preference lists: each proposer sorts respondents by descending score
    proposer_prefs = {
        p: sorted(
            respondents,
            key=lambda r: score_fn(p, r),
            reverse=True,
        )
        for p in proposers
    }
    respondent_prefs = {r: {p: score_fn(p, r) for p in proposers} for r in respondents}

    # A deque takes the free proposers in the same first-in-first-out order as
    # the list did, so the run is step-for-step identical, ties included, but
    # popleft() is O(1) where list.pop(0) is O(n) inside the proposal loop.
    free_proposers = deque(proposers)
    engagements: dict = {}
    next_proposal_index: dict = {p: 0 for p in proposers}

    while free_proposers:
        p = free_proposers.popleft()
        pref_list = proposer_prefs[p]
        if next_proposal_index[p] >= len(pref_list):
            continue
        r = pref_list[next_proposal_index[p]]
        next_proposal_index[p] += 1

        current = engagements.get(r)
        if current is None:
            engagements[r] = p
        elif respondent_prefs[r][p] > respondent_prefs[r][current]:
            engagements[r] = p
            free_proposers.append(current)
        else:
            free_proposers.append(p)

    return [(p, r) for r, p in engagements.items()]


def form_couple(
    agent_x,
    agent_y,
    formed_at_tick: int,
    couple_type: str = "monogamous",
) -> Couple:
    """Create a Couple with canonical ordering enforced.

    Raises ValueError when the agents are the same or one of them is
    unsaved. Raises IntegrityError upstream if a duplicate active couple
    already exists between the pair (prevented by business logic in
    handlers, not by a unique constraint).
    """
    from epocha.apps.demography.models import Couple

    a, b = _ordered_pair(agent_x, agent_y)
    return Couple.objects.create(
        simulation=a.simulation,
        agent_a=a,
        agent_b=b,
        formed_at_tick=formed_at_tick,
        couple_type=couple_type,
    )


def seeks_a_partner_of_the_other_sex(agent) -> bool:
    """Whether the agent's orientation admits a partner of the other sex.

    The ONE orientation rule of the rule-based couple formation: the
    founding pairing applies it, and the rule-based marriage market of the
    couples spec applies the same one to both sides («orientamento
    eterosessuale o bisessuale», FR-003). Heterosexual and bisexual agents
    meet it; homosexual and asexual agents do not, because the pairing forms
    the era's marriage between a man and a woman and no verified source
    gives a schedule for the other cases. Round 15 of the Plan 4 phase-6
    gate found the founding pairing admitting heterosexual founders only,
    which excluded every bisexual one; written once here, the two paths
    cannot drift apart again. The intent path is not gated by it: a
    protagonist's declared intent stays the way any other couple can form.
    """
    from epocha.apps.agents.models import Agent

    return agent.sexual_orientation in (
        Agent.SexualOrientation.HETEROSEXUAL,
        Agent.SexualOrientation.BISEXUAL,
    )


def meets_marriage_age(agent, template: dict, tick: int, tick_duration_hours: float) -> bool:
    """Whether the agent has reached the era's minimum age at marriage.

    The ONE marriage-age rule of the subsystem, used by both paths that form
    couples: the founding pairing (`initialization.form_initial_couples`) and
    the intent resolver (`resolve_pair_bond_intents`). Round 9 of the Plan 4
    phase-6 gate found the rule applied on the first path and absent from the
    second, so every couple formed by intent ignored the era's threshold --
    the minority test that the household derivation then had to arbitrate.
    Applying the rule on both paths through a second copy would have
    reproduced the defect class the gate kept finding; this function is the
    copy there is.

    The age is `orchestrator.age_in_years` over `birth_tick`, the canonical
    source, and not the `age` column, which is a cache refreshed by the
    mortality step. It therefore carries the era's `acceleration` exactly as
    the hazard and the fertile window do.

    Thresholds are the template's `couple.min_marriage_age_male` and
    `couple.min_marriage_age_female`, in completed years and inclusive: an
    agent exactly at the threshold may marry. The templates carry no third
    threshold, so an agent of any other gender value meets the HIGHER of the
    two -- a conservative choice where the era's data is silent, since it
    never admits a marriage either declared threshold would refuse. The values
    themselves are era data audited with the templates and are not decided
    here.
    """
    from epocha.apps.agents.models import Agent
    from epocha.apps.demography.orchestrator import age_in_years

    couple_cfg = template["couple"]
    male = couple_cfg["min_marriage_age_male"]
    female = couple_cfg["min_marriage_age_female"]
    if agent.gender == Agent.Gender.MALE:
        threshold = male
    elif agent.gender == Agent.Gender.FEMALE:
        threshold = female
    else:
        threshold = max(male, female)
    acceleration = float(template.get("acceleration", 1.0))
    return age_in_years(agent, tick, tick_duration_hours, acceleration) >= threshold


def marriage_ineligibility(
    agent, template: dict, tick: int, tick_duration_hours: float, history: MarriageHistory
) -> str | None:
    """The reason an agent may not marry at this tick, or None when they may.

    The ONE eligibility rule of the marriage market, the founding pairing and
    the pair-bond intent resolver: `meets_marriage_age` (the era's minimum age
    on the canonical age) and the mourning interval after the death of a
    partner. Today only the resolver calls it; the market adopts it with the
    wiring of step 2 (group G9) and the founding pairing with the founding
    schedule (group G10), so until then those two keep their own age check.
    The resolver logs the reason, so the two refusals read differently in the
    record.

    Mourning holds while `tick - widowed_at_tick < mourning_ticks`: the death
    tick is day 0, and exactly `mourning_ticks` later the agent is free. It
    applies to both sexes. The mourning interval is a tunable heuristic of the
    era template (see `mourning_ticks`).

    Args:
        history: from `read_marriage_history`, read once by the caller.
    """
    if not meets_marriage_age(agent, template, tick, tick_duration_hours):
        return "below the era's minimum marriage age"
    widowed_at = history.widowed_at_tick.get(agent.id)
    if widowed_at is None:
        return None
    acceleration = float(template.get("acceleration", 1.0))
    if tick - widowed_at < mourning_ticks(template["couple"], tick_duration_hours, acceleration):
        return "in mourning"
    return None


@dataclass(frozen=True)
class MarketPopulation:
    """The people the marriage market of one tick can see.

    Attributes:
        women: the eligible women, sorted by id. They are the proposers: the
            market is female-dominant (the one-queue idea of SOCSIM, cited as
            an idea in the spec).
        men: the eligible men, sorted by id. They are the respondents.
        ages: canonical age (`age_in_years` over `birth_tick`) of every agent
            in `women` and `men`, computed once per tick.
        history: the marriage history the eligibility was judged on; the
            remarriage rate applies to the women in `history.ever_partnered`.
    """

    women: list
    men: list
    ages: dict[int, float]
    history: MarriageHistory


def read_market_population(context) -> MarketPopulation:
    """Read who can marry at this tick, in three queries whatever the size.

    Eligible means alive, a man or a woman, heterosexual or bisexual (the one
    orientation rule, `seeks_a_partner_of_the_other_sex`), in no active couple,
    and free of `marriage_ineligibility` (the era's minimum age and the
    mourning interval). Queries: the living men and women with their
    simulation joined in, the active couples, the marriage history.

    Queryset dependencies: `select_related("simulation")`, because
    `form_couple` reads `agent.simulation` and would otherwise cost a query
    per couple formed.
    """
    from epocha.apps.agents.models import Agent
    from epocha.apps.demography.orchestrator import age_in_years

    simulation, tick, template = context.simulation, context.tick, context.template
    hours = context.hours_per_tick()
    acceleration = float(template.get("acceleration", 1.0))
    partnered = active_couple_partners(simulation)
    history = read_marriage_history(simulation)
    candidates = (
        Agent.objects.filter(
            simulation=simulation,
            is_alive=True,
            gender__in=(Agent.Gender.MALE, Agent.Gender.FEMALE),
        )
        .select_related("simulation")
        .order_by("id")
    )
    eligible = [
        agent
        for agent in candidates
        if agent.id not in partnered
        and seeks_a_partner_of_the_other_sex(agent)
        and marriage_ineligibility(agent, template, tick, hours, history) is None
    ]
    return MarketPopulation(
        women=[a for a in eligible if a.gender == Agent.Gender.FEMALE],
        men=[a for a in eligible if a.gender == Agent.Gender.MALE],
        ages={a.id: age_in_years(a, tick, hours, acceleration) for a in eligible},
        history=history,
    )


def seek_probability_for(
    population: MarketPopulation,
    schedule,
    remarriage_rate: float,
    years_per_tick: float,
) -> Callable[[Agent], float]:
    """Return the function giving each eligible woman her chance of a marriage
    event in one tick.

    A woman never in a couple draws on the era's first-marriage schedule at her
    canonical age (`FirstMarriageSchedule.tick_probability`, hazard of
    Kaneko 2003, eq. 1-4). A woman who has been in a couple that ended draws
    on a constant annual remarriage rate `r`, turned into a per-tick
    probability as `1 - exp(-r * dt)`; `r` is a tunable heuristic of the era
    template (`remarriage_annual_rate_female`), not a measured quantity, and
    does not depend on age (a stated limit of the model). `dt` is the tick
    length in simulated years.

    The remarriage probability is computed once; the closure reads two maps
    already in `population`, so it costs no query.
    """
    remarriage = 1.0 - math.exp(-remarriage_rate * years_per_tick)

    def probability(woman) -> float:
        if woman.id in population.history.ever_partnered:
            return remarriage
        return schedule.tick_probability(population.ages[woman.id], years_per_tick)

    return probability


def draw_seekers(women: list, probability: Callable[[Agent], float], rng) -> list:
    """Return the women whose marriage event falls on this tick.

    One `rng.random()` per woman, in the order given, whatever her
    probability: the stream is consumed the same way for any set of
    probabilities, so changing a template value never shifts the draws of the
    women who come after (plan PD-01). A woman is a seeker when her draw is
    strictly below her probability, so a probability of 0.0 never selects her
    and 1.0 always does (`random()` is in [0, 1)).
    """
    return [woman for woman in women if rng.random() < probability(woman)]


def partition_by_market(agents: list, radius: str) -> list[tuple]:
    """Split agents into the markets they can meet in, by the era's radius.

    `same_zone` makes one market per `zone_id` (the null zone is an ordinary
    key); `world` makes one market for everybody, keyed `None`. Markets come
    out with the null key first, then ascending `zone_id`, so the result does
    not depend on dictionary order (plan PD-02); inside a market the agents
    keep the order they were given. The loader admits only these two radii
    (`ALLOWED_MARRIAGE_MARKET_RADII`); the check here keeps a corrupted
    template dict loud instead of silently falling into one of them.
    """
    if radius == "world":
        return [(None, list(agents))]
    if radius != "same_zone":
        raise ValueError(f"unknown marriage_market_radius {radius!r}")
    groups: dict = {}
    for agent in agents:
        groups.setdefault(agent.zone_id, []).append(agent)
    return [(key, groups[key]) for key in sorted(groups, key=lambda k: (k is not None, k or 0))]


def match_markets(seekers: list, candidates: list, radius: str, score) -> list[tuple]:
    """Match the seekers with the candidates inside each market of the radius.

    Both sides are partitioned with `partition_by_market`; in every market
    that has both, `stable_matching` (Gale and Shapley 1962, audited) runs
    with the seekers as proposers. A market with only one side forms nothing.
    Surplus on either side stays unmatched, so no candidate is taken twice.
    The pairs are returned `(seeker, candidate)` in ascending seeker id,
    whatever the order the markets were visited in, so the couples written
    from them have a stable order (plan PD-03).
    """
    candidates_by_market = dict(partition_by_market(candidates, radius))
    pairs: list[tuple] = []
    for key, market_seekers in partition_by_market(seekers, radius):
        market_candidates = candidates_by_market.get(key)
        if market_candidates:
            pairs.extend(stable_matching(market_seekers, market_candidates, score))
    return sorted(pairs, key=lambda pair: pair[0].id)


def form_matched_couples(context, population: MarketPopulation, seekers: list) -> list[Couple]:
    """Match the tick's seekers with the unpartnered men and form the couples.

    With no seeker or no man nothing is read and nothing is written. Otherwise
    one query reads the sentiments of the seeker-candidate pairs, the score is
    `homogamy_score` (Kalmijn 1998, equation 4.6) on the era weights and the
    canonical ages already in `population`, the markets are those of the era's
    `marriage_market_radius`, and every couple is written by `form_couple`
    inside one transaction, in ascending seeker id, with the era's
    `default_type`, as the intent resolver does.
    """
    from django.db import transaction

    if not seekers or not population.men:
        return []
    couple_cfg = context.template["couple"]
    sentiments = read_sentiments([w.id for w in seekers], [m.id for m in population.men])

    def score(woman, man) -> float:
        return homogamy_score(
            woman,
            man,
            couple_cfg["homogamy_weights"],
            sentiments=sentiments,
            ages=population.ages,
        )

    pairs = match_markets(seekers, population.men, couple_cfg["marriage_market_radius"], score)
    with transaction.atomic():
        return [
            form_couple(
                woman,
                man,
                formed_at_tick=context.tick,
                couple_type=couple_cfg["default_type"],
            )
            for woman, man in pairs
        ]


def run_marriage_market(context, rng) -> list[Couple]:
    """Run the rule-based marriage market of one tick.

    Reads the eligible population, gives each woman her marriage-event
    probability (first-marriage schedule or remarriage rate), draws the
    seekers on the tick's `couple` stream, and forms the matched couples.
    `years_per_tick` is the tick length in simulated years, written inline
    as `fertility.py` does (plan PD-07).
    """
    from epocha.apps.demography.orchestrator import HOURS_PER_YEAR

    couple_cfg = context.template["couple"]
    acceleration = float(context.template.get("acceleration", 1.0))
    years_per_tick = context.hours_per_tick() / HOURS_PER_YEAR * acceleration
    population = read_market_population(context)
    probability = seek_probability_for(
        population,
        first_marriage_schedule(couple_cfg),
        couple_cfg["remarriage_annual_rate_female"],
        years_per_tick,
    )
    seekers = draw_seekers(population.women, probability, rng)
    return form_matched_couples(context, population, seekers)


def resolve_pair_bond_intents(
    simulation,
    tick: int,
    rng,
    tick_duration_hours: float | None = None,
) -> list[Couple]:
    """Process pair_bond intents from tick - 1, form couples where mutual.

    Reads DecisionLog.output_decision (TextField, JSON blob). Pre-filters
    with __contains then parses each match via json.loads to extract the
    action and payload. The resolver:
    1. Collects pair_bond DecisionLog entries from tick - 1.
    2. Two-pass intent ingestion to satisfy Goode (1963) arranged-marriage
       semantics (fix for audit finding B2-06):
       - Pass A: direct intents where the proposer is the DecisionLog
         author. These represent the agent acting on her own behalf.
       - Pass B: `for_child` payloads where a parent proposes on behalf
         of a child. These are recorded ONLY when the child has not
         already expressed a direct intent in Pass A, so parental
         initiative cannot override the child's own choice.
    3. Forms a couple when both ends of an edge pair_bonded each other,
       or when the era template sets implicit_mutual_consent=True.
    4. Skips pairs where either agent is already in an active couple.
    5. Resolution is wrapped in a transaction and uses deterministic
       (sorted) iteration so two runs with the same seed produce the
       same matching (fix for audit finding B2-03).
    6. Malformed DecisionLog JSON is logged at WARNING level instead of
       being silently skipped (fix for audit finding B2-02).
    7. Refuses, and logs at WARNING level, a pairing in which either side is
       below the era's minimum marriage age (`meets_marriage_age`). The
       check sits in the formation loop, the one place every couple passes
       through whether its intent was direct or arranged, and it reads
       objects the loop already holds, so it costs no query.

    `tick_duration_hours` is the world's tick length, which the age rule
    needs. The orchestrator passes the value its tick context has already
    resolved; a caller without one -- the tests calling this directly --
    leaves it out and pays one query, and only when there is an intent to
    judge.

    Sources:
    - Tick+1 settlement pattern from Economy Spec 2 Plan 3b (property market).
    - Arranged marriage reattribution follows Goode (1963) §7.
    """
    import json

    from django.db import transaction

    from epocha.apps.agents.models import Agent, DecisionLog
    from epocha.apps.demography.template_loader import load_template

    sim_config = simulation.config or {}
    template_name = sim_config.get("demography_template", "pre_industrial_christian")
    template = load_template(template_name)
    couple_cfg = template["couple"]
    implicit_consent = bool(couple_cfg.get("implicit_mutual_consent", True))

    entries = (
        DecisionLog.objects.filter(
            simulation=simulation,
            tick=tick - 1,
            output_decision__contains='"pair_bond"',
        )
        .select_related("agent")
        .order_by("agent_id", "id")
    )

    direct_intents: dict[int, list[int]] = {}
    arranged_intents: list[tuple[int, int]] = []
    by_id: dict[int, Agent] = {}

    def _resolve_agent_by_name(name: str) -> Agent | None:
        """Resolve an intent's target, refusing an ambiguous name.

        `.first()` used to win here, which silently married whichever living
        namesake carried the lowest id -- an agent bound to somebody it never
        named. The ambiguity was theoretical while nothing in production
        created agents after world generation; demography Plan 4 makes
        newborns, and the era name pools hold TWELVE entries per sex with no
        uniqueness check, so a collision is certain by the thirteenth birth
        of a sex.

        Refusing does not remove the ambiguity, it stops the wrong marriage
        and leaves a record. Resolving by id rather than by name would remove
        it and is tracked separately, because it changes the action schema
        the decision loop hands the model. Two rows are fetched rather than
        one, which is the same single query.
        """
        if not name:
            return None
        matches = list(
            Agent.objects.filter(
                simulation=simulation,
                name=name,
                is_alive=True,
            ).order_by("id")[:2]
        )
        if len(matches) > 1:
            logging.getLogger(__name__).warning(
                "demography: pair-bond target %r is ambiguous in simulation %s "
                "-- at least two living agents carry that name, so the intent "
                "is dropped rather than bound to an arbitrary one",
                name,
                simulation.id,
            )
            return None
        return matches[0] if matches else None

    def _add_direct(proposer: Agent, match_id: int) -> None:
        by_id[proposer.id] = proposer
        bucket = direct_intents.setdefault(proposer.id, [])
        if match_id not in bucket:
            bucket.append(match_id)

    # Pass A: direct and arranged-marriage intents.
    for entry in entries:
        try:
            decision = json.loads(entry.output_decision)
        except (json.JSONDecodeError, TypeError):
            logger.warning(
                "pair_bond intent dropped: malformed JSON for DecisionLog id=%d",
                entry.id,
            )
            continue
        if decision.get("action") != "pair_bond":
            continue
        target_payload = decision.get("target")
        if isinstance(target_payload, dict) and target_payload.get("for_child"):
            # Arranged marriage: record for Pass B, not applied yet
            child_name = target_payload.get("for_child")
            match_name = target_payload.get("match")
            child = _resolve_agent_by_name(child_name) if isinstance(child_name, str) else None
            match = _resolve_agent_by_name(match_name) if isinstance(match_name, str) else None
            if child is None or match is None:
                continue
            by_id[child.id] = child
            arranged_intents.append((child.id, match.id))
            continue
        if isinstance(target_payload, dict):
            match_name = target_payload.get("match")
        elif isinstance(target_payload, str):
            match_name = target_payload
        else:
            continue
        match = _resolve_agent_by_name(match_name) if isinstance(match_name, str) else None
        if match is None:
            continue
        _add_direct(entry.agent, match.id)

    # Pass B: arranged intents applied ONLY when the child has no direct intent.
    # Deterministic order by (child_id, match_id).
    for child_id, match_id in sorted(arranged_intents):
        if child_id in direct_intents:
            continue
        child = by_id.get(child_id)
        if child is None:
            continue
        _add_direct(child, match_id)

    formed: list = []

    history: MarriageHistory | None = None

    def _eligible(agent: Agent) -> bool:
        # The tick length and the marriage history are read on the first
        # call, so a tick without intents pays for neither, and a tick with
        # intents pays one history query, not one per intent.
        nonlocal tick_duration_hours, history
        if tick_duration_hours is None:
            from epocha.apps.demography.orchestrator import _tick_duration_hours

            tick_duration_hours = _tick_duration_hours(simulation)
        if history is None:
            history = read_marriage_history(simulation)
        reason = marriage_ineligibility(agent, template, tick, tick_duration_hours, history)
        if reason is None:
            return True
        logger.warning(
            "demography: pair-bond intent involving %r (agent %s) refused in simulation %s -- %s",
            agent.name,
            agent.id,
            simulation.id,
            reason,
        )
        return False

    used: set[int] = set()
    with transaction.atomic():
        # Deterministic iteration (fix B2-03): sort by proposer id
        for proposer_id in sorted(direct_intents):
            if proposer_id in used:
                continue
            proposer = by_id[proposer_id]
            if not _eligible(proposer) or is_in_active_couple(proposer):
                continue
            for target_id in direct_intents[proposer_id]:
                if target_id in used:
                    continue
                target = Agent.objects.filter(id=target_id, is_alive=True).first()
                if target is None or not _eligible(target):
                    continue
                if is_in_active_couple(target):
                    continue
                mutual = target_id in direct_intents and proposer_id in direct_intents.get(
                    target_id, []
                )
                if not mutual and not implicit_consent:
                    continue
                couple = form_couple(
                    proposer,
                    target,
                    formed_at_tick=tick,
                    couple_type=couple_cfg.get("default_type", "monogamous"),
                )
                formed.append(couple)
                used.add(proposer_id)
                used.add(target_id)
                break
    return formed


def resolve_separate_intents(simulation, tick: int) -> list[Couple]:
    """Process separate intents from tick - 1, dissolve active couples.

    Reads DecisionLog.output_decision (JSON blob) with __contains pre-filter
    and json.loads verification, same pattern as resolve_pair_bond_intents.

    Skips entirely when the era template has divorce_enabled=False.
    Returns the list of dissolved Couples.
    """
    import json

    from epocha.apps.agents.models import DecisionLog
    from epocha.apps.demography.template_loader import load_template

    sim_config = simulation.config or {}
    template_name = sim_config.get("demography_template", "pre_industrial_christian")
    template = load_template(template_name)
    if not bool(template["couple"].get("divorce_enabled", False)):
        return []

    entries = DecisionLog.objects.filter(
        simulation=simulation,
        tick=tick - 1,
        output_decision__contains='"separate"',
    ).select_related("agent")

    dissolved: list = []
    for entry in entries:
        try:
            decision = json.loads(entry.output_decision)
        except (json.JSONDecodeError, TypeError):
            # Fix for audit finding B2-02: malformed JSON should be logged,
            # not silently dropped. A dropped separate intent would leave a
            # couple active that was supposed to dissolve, a subtle bug.
            logger.warning(
                "separate intent dropped: malformed JSON for DecisionLog id=%d",
                entry.id,
            )
            continue
        if decision.get("action") != "separate":
            continue
        couple = active_couple_for(entry.agent)
        if couple is None:
            continue
        couple.dissolved_at_tick = tick
        couple.dissolution_reason = "separate"
        couple.save(update_fields=["dissolved_at_tick", "dissolution_reason"])
        dissolved.append(couple)
    return dissolved


def _null_deceased_partner(couple: Couple, deceased_agent) -> None:
    """Capture the deceased partner's name snapshot and null their FK.

    Determines which side of the Couple (agent_a or agent_b) the deceased
    occupies and updates only that side, leaving the other partner's FK
    untouched. Shared by both branches of dissolve_on_death so the same
    capture-then-null logic is not duplicated.
    """
    if couple.agent_a_id == deceased_agent.id:
        couple.agent_a_name_snapshot = deceased_agent.name
        couple.agent_a = None
    else:
        couple.agent_b_name_snapshot = deceased_agent.name
        couple.agent_b = None


def dissolve_on_death(deceased_agent, tick: int) -> Couple | None:
    """Dissolve the Couple where the deceased agent is a partner.

    Idempotent per partner, not once per couple: safe to call once for
    EACH deceased partner, even when both partners of the same Couple
    die in the same tick. The normal case resolves the couple via
    active_couple_for and sets dissolved_at_tick / dissolution_reason.
    When active_couple_for finds nothing -- because a couple dissolved
    earlier THIS SAME tick is no longer "active" under its
    dissolved_at_tick__isnull=True filter -- this function falls back to
    a couple already dissolved at this SAME tick in which deceased_agent
    is still a non-null partner, and completes that partner's snapshot
    capture and FK nulling without touching dissolved_at_tick or
    dissolution_reason (already set by the first call). Resolving
    "dissolved at this same tick" needs only deceased_agent and tick,
    both already parameters -- no batch state from the caller is
    required (rejected alternative in design decision D1).

    Captures the deceased's name into the appropriate *_name_snapshot
    field before nulling the FK, so the genealogical record survives
    the delete cascade.
    """
    from epocha.apps.demography.models import Couple

    couple = active_couple_for(deceased_agent)
    if couple is not None:
        _null_deceased_partner(couple, deceased_agent)
        couple.dissolved_at_tick = tick
        couple.dissolution_reason = "death"
        couple.save(
            update_fields=[
                "agent_a",
                "agent_b",
                "agent_a_name_snapshot",
                "agent_b_name_snapshot",
                "dissolved_at_tick",
                "dissolution_reason",
            ]
        )
        return couple

    # Same-tick double-death fallback (D1): the first partner's death
    # already dissolved this couple this tick, so active_couple_for no
    # longer finds it. Look for a couple dissolved at this SAME tick
    # where deceased_agent is still a non-null partner.
    couple = Couple.objects.filter(
        Q(agent_a=deceased_agent) | Q(agent_b=deceased_agent),
        dissolved_at_tick=tick,
    ).first()
    if couple is None:
        return None

    _null_deceased_partner(couple, deceased_agent)
    couple.save(
        update_fields=[
            "agent_a",
            "agent_b",
            "agent_a_name_snapshot",
            "agent_b_name_snapshot",
        ]
    )
    return couple

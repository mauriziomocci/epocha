"""Context helpers bridging demography with the economy subsystem.

Defines the integration contracts listed in the spec §Integration
Contracts. These helpers compute quantities that do not exist as
named fields in the economy subsystem but are derivable from its
state.
"""

from __future__ import annotations

from typing import Any

from epocha.apps.economy.market import SUBSISTENCE_NEED_PER_AGENT
from epocha.apps.economy.models import GoodCategory, ZoneEconomy


def _to_signed_unit(value) -> float:
    """Map a fraction in [0, 1] onto [-1, 1].

    The three signals `compute_aggregate_outlook` combines are all recorded
    as fractions and all enter the mean on the same signed scale, so the
    mapping is written once here rather than three times inline: an outlook
    where one term used a different scale would be a silent modelling error.
    """
    return 2.0 * float(value or 0.0) - 1.0


def load_outlook_terms(simulation) -> tuple[float, float]:
    """Return the two simulation-wide terms of the aggregate outlook.

    Banking confidence and government stability are properties of the
    *simulation*, not of the agent, so every agent evaluated in a tick reads
    the same two numbers. `compute_aggregate_outlook` used to fetch both on
    every call, which inside the fertility step meant two queries for every
    living fertile woman -- an N+1 against FR-016. Loading them once per tick
    and passing them in removes the per-agent cost without touching the
    formula that consumes them.

    Both records are optional: a simulation whose economy was never
    initialized has neither, and the outlook then reads the corresponding
    term as neutral (0.0 on the signed scale) rather than failing.

    Returns:
        `(confidence_term, stability_term)`, both already on the signed
        [-1, 1] scale the outlook mean expects.
    """
    from epocha.apps.economy.models import BankingState
    from epocha.apps.world.models import Government

    try:
        confidence_term = _to_signed_unit(
            BankingState.objects.get(simulation=simulation).confidence_index
        )
    except BankingState.DoesNotExist:
        confidence_term = 0.0
    # Government.stability is non-nullable with default=0.5; the only case in
    # which it is unavailable is when the Government record does not exist
    # (economy not initialized), handled by the DoesNotExist branch.
    try:
        stability_term = _to_signed_unit(Government.objects.get(simulation=simulation).stability)
    except Government.DoesNotExist:
        stability_term = 0.0
    return confidence_term, stability_term


def compute_subsistence_threshold(simulation, zone) -> float:
    """Return the per-agent per-tick subsistence cost in the primary currency.

    Uses the GoodCategory.is_essential flag, the SUBSISTENCE_NEED_PER_AGENT
    constant (extracted from economy/market.py), and current market prices
    in the zone. The result is the minimum wealth flow required to consume
    essential goods at subsistence quantity.
    """
    try:
        ze = ZoneEconomy.objects.get(zone=zone)
    except ZoneEconomy.DoesNotExist:
        return 0.0
    essentials = GoodCategory.objects.filter(simulation=simulation, is_essential=True)
    total = 0.0
    for good in essentials:
        price = ze.market_prices.get(good.code, good.base_price)
        total += price * SUBSISTENCE_NEED_PER_AGENT
    return total


def compute_aggregate_outlook(agent, *, outlook_terms: tuple[float, float] | None = None) -> float:
    """Return a scalar in [-1, 1] summarizing the agent's economic perception.

    Design heuristic combining:
    - agent mood (0..1 mapped to -1..1)
    - banking confidence (BankingState.confidence_index, 0..1 mapped to -1..1)
    - zone stability (Government.stability, 0..1 mapped to -1..1)

    Equal weights; tunable design parameter. Not derived from Jones &
    Tertilt (2008); it is a pragmatic proxy for Becker modulation where
    gender-segmented wages are unavailable.

    Args:
        agent: the agent whose perception is summarized. Only `mood` is read
            off the agent; the other two terms describe the simulation.
        outlook_terms: the pair `load_outlook_terms` returns, when the caller
            already loaded it. Callers that evaluate many agents in one tick
            SHOULD pass it: the two records are simulation-wide, so fetching
            them per agent is the per-living-agent query cost FR-016 forbids.
            Omitted, the pair is loaded here, which is what a single ad-hoc
            call wants and what every caller did before the fertility step
            began evaluating a whole population at once.
    """
    if outlook_terms is None:
        outlook_terms = load_outlook_terms(agent.simulation)
    confidence_term, stability_term = outlook_terms
    return (_to_signed_unit(agent.mood) + confidence_term + stability_term) / 3.0


def household_keys(
    living: list,
    ages: list[float],
    simulation: Any,
    adulthood_age: float,
) -> dict[int, tuple[int, ...]]:
    """Map every living agent to the key of the household it belongs to.

    A household is a couple with the minors in its care, or a single adult.
    The model has no household entity, so it is derived: partners share one,
    a MINOR child -- younger than the era template's `migration.adulthood_age`,
    the same threshold household migration coordination uses -- belongs to
    the household of whichever guardian is still alive, and everyone else is
    their own. The age test is load-bearing: without it a sixty-year-old
    files under his eighty-five-year-old father's roof. The guardian search
    and the chain that follows it are documented at the call site below.

    Lives here, and is shared, because two callers need the same notion and
    a second copy of a quantity is precisely the defect the phase-6 closure
    review found in four places on this branch: the snapshot reports average
    household size, and the starvation counter asks whether a household can
    feed itself. A dependent minor owns nothing -- `apply_inheritance_at_birth`
    writes `wealth = 0.0` on every newborn -- so asking that question of the
    individual makes every child in the world a chronic starveling.

    The partner map skips null sides explicitly. `Couple.agent_a`/`agent_b`
    are nullable and `SET_NULL` keeps the genealogical record when an agent
    row is deleted, so an undissolved row can carry one live partner and one
    null; writing a `None` key would put every such survivor in one shared
    household.
    """
    from epocha.apps.demography.couple import active_couple_partners

    # The partner map comes from `couple.active_couple_partners`, not from a
    # second copy of its body. Round 9 counted this file re-implementing that
    # function line for line, both of them added by this same work item --
    # code that is born duplicated next to its original, which is the pattern
    # the gate has now caught six times.
    partner_of = active_couple_partners(simulation)
    living_ids = {agent.id for agent in living}

    # A minor is anchored through WHICHEVER guardian is alive, in the order
    # mother, father, appointed caretaker. Reading `parent_agent` alone --
    # which is what the first version of this function did -- left every
    # child whose mother had died as a household of one standing next to a
    # solvent father, which is the starvation defect this derivation exists
    # to close, still open for that population. `inheritance.py` already
    # resolves "child of" as `Q(parent_agent=x) | Q(other_parent_agent=x)`,
    # so a second, narrower definition of the same relation in the module
    # next door is exactly the duplication the phase-6 closure review named.
    # `caretaker_agent` joins them because the docstring says "the minors in
    # its care" and `assign_orphan_caretaker` exists to put them there.
    guardian_of: dict[int, int] = {}
    for agent, age in zip(living, ages, strict=True):
        if age >= adulthood_age:
            continue
        for candidate in (
            agent.parent_agent_id,
            agent.other_parent_agent_id,
            agent.caretaker_agent_id,
        ):
            if candidate is not None and candidate in living_ids:
                guardian_of[agent.id] = candidate
                break

    def _anchor(agent_id: int) -> int:
        # Transitive, because a mother can herself be a minor: the fertile
        # window opens at twelve and adulthood is sixteen or eighteen, so a
        # four-to-six-year band of mothers is anchored to a parent of their
        # own, and without following the chain their newborn is a household
        # of one that the grandparent's solvency never reaches. The visited
        # set bounds a cycle that the data model does not forbid.
        #
        # MARRIAGE OUTRANKS THE CHAIN, and the walk stops at the first node
        # that is in an active couple -- starting with the agent itself. A
        # couple IS a household, which is the first sentence of this
        # docstring, so a married minor cannot also be a dependent of her
        # parent's: measured before this guard, she was pulled into the
        # parent's household while her partner's key still named her, so her
        # wealth was counted in one household and her membership claimed by
        # another, and one year of age flipped the verdict on the same
        # population. Reachable when this guard was written because the era's
        # minimum marriage age gated only the founding matcher; since
        # `couple.meets_marriage_age` it gates the intent path too, and the
        # guard stays necessary all the same: the pre-industrial eras set the
        # female threshold at 14 against an adulthood age of 16, so a married
        # minor is a legitimate state there.
        seen: set[int] = set()
        current = agent_id
        while current not in partner_of and current in guardian_of and current not in seen:
            seen.add(current)
            current = guardian_of[current]
        return current

    keys: dict[int, tuple[int, ...]] = {}
    for agent in living:
        anchor = _anchor(agent.id)
        partner = partner_of.get(anchor)
        keys[agent.id] = tuple(sorted((anchor, partner))) if partner else (anchor,)
    return keys

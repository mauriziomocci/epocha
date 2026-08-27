"""Context helpers bridging demography with the economy subsystem.

Defines the integration contracts listed in the spec §Integration
Contracts. These helpers compute quantities that do not exist as
named fields in the economy subsystem but are derivable from its
state.
"""

from __future__ import annotations

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

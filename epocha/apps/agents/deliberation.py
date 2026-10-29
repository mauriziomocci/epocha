"""Protagonist budget: how many agents deliberate with the LLM at each tick.

``max_protagonists``: number of agents that deliberate with the LLM at each
tick; 0 means rules only, no LLM decision call; an absent key means 30.

The cap is a compute budget, not a scientific parameter (decision D-RBC-02 of
the rule-based couples work item): it bounds the cost of the decision step and
carries no claim about human behaviour, so it has no literature source.
Everything outside the protagonists is driven by the rule-based demography and
economy models, whose parameters are cited where they are defined.
"""

import logging

logger = logging.getLogger(__name__)

# Upper bound of the agents ``world/generator.py`` asks the LLM for ("10-30
# agents"), so a generated world that respects the request keeps deliberating
# in full at birth. It is not a guarantee: the generator creates every agent the
# LLM returns, and the knowledge-graph path creates one agent per person of the
# graph, so a world with more than 30 founders sees only the first 30 deliberate.
DEFAULT_MAX_PROTAGONISTS = 30


def is_valid_max_protagonists(value) -> bool:
    """Return True when ``value`` is a whole number of 0 or more.

    A ``bool`` is rejected explicitly: in Python ``True`` is an ``int``, so an
    ``isinstance`` check alone would accept it as a budget of 1.
    """
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def max_protagonists(simulation) -> int:
    """Return the protagonist budget K of ``simulation``.

    An absent key silently gives ``DEFAULT_MAX_PROTAGONISTS``. An invalid value
    can only come from a write that bypassed the API (the serializer rejects
    it), and it gives the default too, but logs an ERROR at every read: a
    configuration error must stay loud, not be absorbed once and forgotten.
    """
    if "max_protagonists" not in simulation.config:
        return DEFAULT_MAX_PROTAGONISTS
    value = simulation.config["max_protagonists"]
    if is_valid_max_protagonists(value):
        return value
    logger.error(
        "Simulation %s has an invalid max_protagonists %r (expected a whole number of 0 or "
        "more); using the default of %d",
        simulation.id,
        value,
        DEFAULT_MAX_PROTAGONISTS,
    )
    return DEFAULT_MAX_PROTAGONISTS

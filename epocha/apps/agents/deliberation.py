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


def select_deliberating_agents(simulation, tick: int) -> list:
    """Return the at most K living agents that deliberate at ``tick``.

    Priority, then id: the head of state of the simulation's ``Government``
    first, the leaders of the simulation's ``Group`` rows next, every other
    agent last, each class ordered by id (creation order). The query is one
    ``Exists`` annotation sliced to K rows, so the query count is constant.
    The rows read are O(N) under demography, because the minor ids are read and
    passed to the database as an ``IN`` list of up to N values, until the
    life-course work item replaces ``minor_agent_ids`` (FR-008). K = 0 returns
    ``[]`` before any query.

    Minors are excluded through ``minor_agent_ids``: a newborn must not choose
    ``move_to`` and leave its household alone (the guarantee
    ``coordinate_family_migration`` documents). The set is read AFTER the
    demography block of the tick, so a child born this tick is already in the
    population. It is empty, with no query, when the simulation has not opted
    into demography, which keeps the selection exactly as it was: without
    demography every living agent is eligible, a child included (D-29-4).
    """
    from django.db.models import Case, Exists, IntegerField, OuterRef, Value, When

    from epocha.apps.agents.models import Agent, Group
    from epocha.apps.demography.orchestrator import minor_agent_ids
    from epocha.apps.world.models import Government

    budget = max_protagonists(simulation)
    if budget == 0:
        return []
    is_head = Exists(Government.objects.filter(simulation=simulation, head_of_state=OuterRef("pk")))
    is_leader = Exists(Group.objects.filter(simulation=simulation, leader=OuterRef("pk")))
    return list(
        Agent.objects.filter(simulation=simulation, is_alive=True)
        .exclude(id__in=minor_agent_ids(simulation, tick))
        .annotate(
            priority=Case(
                When(is_head, then=Value(0)),
                When(is_leader, then=Value(1)),
                default=Value(2),
                output_field=IntegerField(),
            )
        )
        .order_by("priority", "id")[:budget]
    )

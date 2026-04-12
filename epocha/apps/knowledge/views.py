"""Dashboard views for the Knowledge Graph visualization.

Renders the Sigma.js-based graph explorer, embedding initial graph
data in the template context to avoid a separate AJAX call on first
load.
"""
from __future__ import annotations

import json

from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404, render

from epocha.apps.knowledge.models import KnowledgeGraph, KnowledgeNode, KnowledgeRelation
from epocha.apps.knowledge.serializers import KnowledgeEdgeSerializer, KnowledgeNodeSerializer
from epocha.apps.simulation.models import Simulation

# 10 distinct colors for entity types, chosen for perceptual
# distinguishability on dark backgrounds (WCAG AA contrast).
ENTITY_COLORS = {
    "person": "#f87171",      # red-400
    "group": "#fb923c",       # orange-400
    "place": "#34d399",       # emerald-400
    "institution": "#60a5fa",  # blue-400
    "event": "#c084fc",       # purple-400
    "concept": "#fbbf24",     # amber-400
    "ideology": "#f472b6",    # pink-400
    "object": "#a3e635",      # lime-400
    "norm": "#2dd4bf",        # teal-400
    "value": "#e879f9",       # fuchsia-400
}

# 9 distinct colors for relation categories.
CATEGORY_COLORS = {
    "membership": "#60a5fa",   # blue-400
    "spatial": "#34d399",      # emerald-400
    "temporal": "#fbbf24",     # amber-400
    "belief": "#c084fc",       # purple-400
    "social": "#f87171",       # red-400
    "kinship": "#f472b6",      # pink-400
    "causal": "#fb923c",       # orange-400
    "participation": "#2dd4bf",  # teal-400
    "production": "#a3e635",   # lime-400
}

INITIAL_NODE_LIMIT = 100


@login_required(login_url="/login/")
def knowledge_graph_view(request, sim_id):
    """Render the knowledge graph explorer page.

    Embeds initial JSON data (top 100 nodes by confidence, with their
    connecting edges) directly in the template context so the graph
    renders immediately without an extra AJAX round-trip.
    """
    simulation = get_object_or_404(Simulation, pk=sim_id, owner=request.user)
    graph = KnowledgeGraph.objects.filter(simulation=simulation, status="ready").first()
    if graph is None:
        raise Http404("No ready knowledge graph for this simulation.")

    # Fetch initial nodes (ordered by confidence desc, then canonical_name)
    nodes_qs = KnowledgeNode.objects.filter(graph=graph).select_related(
        "linked_agent", "linked_group", "linked_zone",
        "linked_institution", "linked_event",
    )[:INITIAL_NODE_LIMIT]

    node_ids = set(nodes_qs.values_list("id", flat=True))

    # Only edges connecting nodes in the initial set
    edges_qs = KnowledgeRelation.objects.filter(
        graph=graph,
        source_node_id__in=node_ids,
        target_node_id__in=node_ids,
    )

    initial_data = {
        "nodes": KnowledgeNodeSerializer(nodes_qs, many=True).data,
        "edges": KnowledgeEdgeSerializer(edges_qs, many=True).data,
        "stats": {
            "total_nodes": KnowledgeNode.objects.filter(graph=graph).count(),
            "returned_nodes": len(node_ids),
        },
    }

    return render(request, "knowledge/graph.html", {
        "simulation": simulation,
        "graph": graph,
        "initial_data_json": json.dumps(initial_data),
        "entity_colors": ENTITY_COLORS,
        "category_colors": CATEGORY_COLORS,
        "entity_colors_json": json.dumps(ENTITY_COLORS),
        "category_colors_json": json.dumps(CATEGORY_COLORS),
    })

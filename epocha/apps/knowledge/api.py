"""DRF API views for the Knowledge Graph.

Provides three endpoints:
- Graph data (nodes + edges) for visualization
- Document upload with synchronous extraction
- Graph status polling
"""
from __future__ import annotations

import logging
import tempfile

from django.shortcuts import get_object_or_404
from rest_framework import permissions, status
from rest_framework.parsers import MultiPartParser
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from epocha.apps.knowledge.models import KnowledgeGraph, KnowledgeNode, KnowledgeRelation
from epocha.apps.knowledge.serializers import KnowledgeEdgeSerializer, KnowledgeNodeSerializer
from epocha.apps.simulation.models import Simulation

logger = logging.getLogger(__name__)

# Hard ceiling on nodes returned in a single request to prevent
# unbounded memory usage on large graphs.
MAX_LIMIT = 1000
DEFAULT_LIMIT = 100


class KnowledgeGraphDataView(APIView):
    """Return graph nodes and edges as JSON for Sigma.js rendering.

    GET /api/v1/knowledge/<sim_id>/graph/

    Query parameters:
        entity_types: comma-separated entity type filter (e.g. "person,place")
        limit: max nodes returned (default 100, max 1000)
        offset: pagination offset for nodes

    Only edges whose both endpoints are in the returned node set are
    included, ensuring the frontend never receives dangling references.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request: Request, sim_id: int) -> Response:
        simulation = get_object_or_404(Simulation, pk=sim_id, owner=request.user)
        graph = KnowledgeGraph.objects.filter(simulation=simulation, status="ready").first()
        if graph is None:
            return Response(
                {"detail": "No ready knowledge graph for this simulation."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Parse query parameters
        limit = min(int(request.query_params.get("limit", DEFAULT_LIMIT)), MAX_LIMIT)
        offset = int(request.query_params.get("offset", 0))
        entity_types_raw = request.query_params.get("entity_types", "")

        # Build node queryset with select_related to avoid N+1 on linked FKs
        nodes_qs = KnowledgeNode.objects.filter(graph=graph).select_related(
            "linked_agent", "linked_group", "linked_zone",
            "linked_institution", "linked_event",
        )
        if entity_types_raw:
            types = [t.strip() for t in entity_types_raw.split(",") if t.strip()]
            nodes_qs = nodes_qs.filter(entity_type__in=types)

        total_nodes = nodes_qs.count()
        nodes = nodes_qs[offset:offset + limit]
        node_ids = set(nodes.values_list("id", flat=True))

        # Only return edges where both endpoints are in the returned node set
        edges_qs = KnowledgeRelation.objects.filter(
            graph=graph,
            source_node_id__in=node_ids,
            target_node_id__in=node_ids,
        )

        return Response({
            "nodes": KnowledgeNodeSerializer(nodes, many=True).data,
            "edges": KnowledgeEdgeSerializer(edges_qs, many=True).data,
            "stats": {
                "total_nodes": total_nodes,
                "returned_nodes": len(node_ids),
                "has_more": (offset + limit) < total_nodes,
            },
        })


class KnowledgeGraphUploadView(APIView):
    """Upload documents and run the extraction pipeline synchronously.

    POST /api/v1/knowledge/upload/
    Content-Type: multipart/form-data

    Fields:
        name: simulation name (required)
        prompt: optional user prompt for generation
        documents: one or more uploaded files

    Runs the full extract_and_generate pipeline and returns 202 with
    the resulting graph metadata.
    """

    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser]

    def post(self, request: Request) -> Response:
        name = request.data.get("name", "").strip()
        if not name:
            return Response(
                {"detail": "The 'name' field is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        files = request.FILES.getlist("documents")
        if not files:
            return Response(
                {"detail": "At least one document file is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        prompt = request.data.get("prompt", "")

        # Parse uploaded files into raw text via the document parser
        from epocha.apps.world.document_parser import extract_text

        documents_data = []
        for uploaded_file in files:
            with tempfile.NamedTemporaryFile(
                suffix=f"_{uploaded_file.name}", delete=True,
            ) as tmp:
                for chunk in uploaded_file.chunks():
                    tmp.write(chunk)
                tmp.flush()

                raw_text = extract_text(tmp.name)

            documents_data.append({
                "raw_text": raw_text,
                "title": uploaded_file.name,
                "mime_type": uploaded_file.content_type or "application/octet-stream",
                "original_filename": uploaded_file.name,
            })

        # Create a simulation for this knowledge graph
        import random
        simulation = Simulation.objects.create(
            name=name,
            description=prompt[:500] if prompt else "",
            seed=random.randint(0, 2**32),
            status=Simulation.Status.CREATED,
            owner=request.user,
        )

        # Run the extraction pipeline synchronously
        from epocha.apps.knowledge.tasks import extract_and_generate

        result = extract_and_generate(
            simulation_id=simulation.id,
            user_id=request.user.id,
            documents_data=documents_data,
            prompt=prompt,
        )

        return Response(
            {
                "simulation_id": simulation.id,
                "status": result.get("status", "failed"),
                "graph_id": result.get("graph_id"),
                "nodes": result.get("nodes", 0),
                "relations": result.get("relations", 0),
            },
            status=status.HTTP_202_ACCEPTED,
        )


class KnowledgeGraphStatusView(APIView):
    """Return the current status of a simulation's knowledge graph.

    GET /api/v1/knowledge/<sim_id>/status/

    Returns the graph status, error message (if any), and node/relation
    counts for a quick health check or polling endpoint.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request: Request, sim_id: int) -> Response:
        simulation = get_object_or_404(Simulation, pk=sim_id, owner=request.user)
        graph = KnowledgeGraph.objects.filter(simulation=simulation).first()
        if graph is None:
            return Response(
                {"status": "no_graph", "error": "", "nodes": 0, "relations": 0},
            )

        return Response({
            "status": graph.status,
            "error": graph.error_message,
            "nodes": graph.nodes.count(),
            "relations": graph.relations.count(),
        })

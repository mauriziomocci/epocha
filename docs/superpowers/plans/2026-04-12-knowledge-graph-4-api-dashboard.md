# Knowledge Graph Implementation Plan — Part 4: API, Dashboard, Housekeeping

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expose the Knowledge Graph to users: an upload API endpoint for document-driven world generation, a status endpoint for extraction progress, a JSON API for graph data, a Sigma.js dashboard page, and a cache cleanup management command. After this plan, the full feature is user-facing.

**Architecture:** Three API layers: (1) DRF endpoint for document upload + extraction trigger, (2) DRF endpoint for graph data in Sigma.js format, (3) Django template view for the dashboard page. The dashboard follows the same pattern as the existing social graph page: Sigma.js with force layout, Alpine.js for interactivity.

**Tech Stack:** DRF, Django templates, Sigma.js, Alpine.js, Tailwind CDN.

**Spec:** `docs/superpowers/specs/2026-04-11-knowledge-graph-design.md` (API Changes, Visualization sections)

**Depends on:** Parts 1-3 completed. Full pipeline functional.

---

## File Structure (Part 4 scope)

| File | Responsibility | New/Modify |
|------|---------------|------------|
| `epocha/apps/knowledge/serializers.py` | DRF serializers for nodes, relations, graph data | New |
| `epocha/apps/knowledge/api.py` | DRF views for upload, status, graph data | New |
| `epocha/apps/knowledge/urls.py` | API URL routes | New |
| `epocha/apps/knowledge/views.py` | Dashboard view for knowledge graph page | New |
| `epocha/apps/knowledge/templates/knowledge/graph.html` | Sigma.js template | New |
| `epocha/apps/knowledge/management/commands/cleanup_extraction_cache.py` | Cache cleanup | New |
| `config/urls.py` | Register knowledge API URLs | Modify |
| `epocha/apps/dashboard/urls.py` | Register knowledge graph dashboard route | Modify |
| `epocha/apps/knowledge/tests/test_api.py` | API tests | New |
| `epocha/apps/knowledge/tests/test_views.py` | Dashboard view tests | New |
| `epocha/apps/knowledge/tests/test_cleanup_command.py` | Management command tests | New |

---

## Tasks summary (Part 4 scope)

13. **Serializers and graph data API** — DRF serializers + GET endpoint for Sigma.js-compatible graph data
14. **Upload and status API** — POST endpoint for document upload + GET for extraction status
15. **Dashboard view and template** — Sigma.js visualization page
16. **Cache cleanup management command** — cleanup_extraction_cache

---

### Task 13: Serializers and graph data API

**Files:**
- New: `epocha/apps/knowledge/serializers.py`
- New: `epocha/apps/knowledge/api.py`
- New: `epocha/apps/knowledge/urls.py`
- Modify: `config/urls.py`
- New: `epocha/apps/knowledge/tests/test_api.py`

- [ ] **Step 1: Write the failing tests**

Create `epocha/apps/knowledge/tests/test_api.py`:

```python
"""Tests for the Knowledge Graph API endpoints."""
import pytest
from django.test import TestCase
from rest_framework.test import APIClient

from epocha.apps.knowledge.models import (
    ExtractionCache,
    KnowledgeDocument,
    KnowledgeGraph,
    KnowledgeNode,
    KnowledgeRelation,
)
from epocha.apps.simulation.models import Simulation
from epocha.apps.users.models import User


@pytest.fixture
def user(db):
    return User.objects.create_user(
        email="api@epocha.dev", username="apiuser", password="pass1234",
    )


@pytest.fixture
def api_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def simulation(user):
    return Simulation.objects.create(name="APITest", seed=42, owner=user)


@pytest.fixture
def cache_entry(db):
    return ExtractionCache.objects.create(
        cache_key="api" + "0" * 61,
        documents_hash="api" + "0" * 61,
        ontology_version="v1",
        extraction_prompt_version="v1",
        llm_model="test",
        extracted_data={},
        stats={},
    )


@pytest.fixture
def graph_with_data(simulation, cache_entry):
    graph = KnowledgeGraph.objects.create(
        simulation=simulation,
        extraction_cache=cache_entry,
        status="ready",
    )
    rob = KnowledgeNode.objects.create(
        graph=graph, entity_type="person",
        name="Robespierre", canonical_name="robespierre",
        description="Leader of the Jacobins",
        source_type="document", confidence=0.9, mention_count=5,
        embedding=[0.1] * 1024,
    )
    jac = KnowledgeNode.objects.create(
        graph=graph, entity_type="institution",
        name="Jacobin Club", canonical_name="jacobin club",
        description="A political society",
        source_type="document", confidence=0.85, mention_count=3,
        embedding=[0.2] * 1024,
    )
    KnowledgeRelation.objects.create(
        graph=graph, source_node=rob, target_node=jac,
        relation_type="member_of", source_type="document",
        confidence=0.9, weight=0.8,
        temporal_start_iso="1789", temporal_start_year=1789,
    )
    return graph


@pytest.mark.django_db
class TestKnowledgeGraphDataAPI:
    def test_returns_nodes_and_edges(self, api_client, simulation, graph_with_data):
        url = f"/api/v1/knowledge/{simulation.id}/graph/"
        response = api_client.get(url)
        assert response.status_code == 200
        data = response.json()
        assert len(data["nodes"]) == 2
        assert len(data["edges"]) == 1
        assert data["stats"]["total_nodes"] == 2

    def test_filters_by_entity_type(self, api_client, simulation, graph_with_data):
        url = f"/api/v1/knowledge/{simulation.id}/graph/?entity_types=person"
        response = api_client.get(url)
        assert response.status_code == 200
        data = response.json()
        assert len(data["nodes"]) == 1
        assert data["nodes"][0]["entity_type"] == "person"

    def test_respects_limit(self, api_client, simulation, graph_with_data):
        url = f"/api/v1/knowledge/{simulation.id}/graph/?limit=1"
        response = api_client.get(url)
        assert response.status_code == 200
        data = response.json()
        assert len(data["nodes"]) == 1
        assert data["stats"]["has_more"] is True

    def test_node_has_linked_info(self, api_client, simulation, graph_with_data):
        url = f"/api/v1/knowledge/{simulation.id}/graph/"
        response = api_client.get(url)
        data = response.json()
        # linked fields should be present (null for this test since no agents linked)
        for node in data["nodes"]:
            assert "linked" in node

    def test_edge_has_category(self, api_client, simulation, graph_with_data):
        url = f"/api/v1/knowledge/{simulation.id}/graph/"
        response = api_client.get(url)
        data = response.json()
        assert data["edges"][0]["category"] == "membership"

    def test_404_for_no_graph(self, api_client, simulation):
        url = f"/api/v1/knowledge/{simulation.id}/graph/"
        response = api_client.get(url)
        assert response.status_code == 404

    def test_unauthenticated_returns_401(self, simulation, graph_with_data):
        client = APIClient()
        url = f"/api/v1/knowledge/{simulation.id}/graph/"
        response = client.get(url)
        assert response.status_code == 401
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `docker compose -f docker-compose.local.yml run --rm web pytest epocha/apps/knowledge/tests/test_api.py -v`

Expected: ImportError or 404 (no URL configured).

- [ ] **Step 3: Implement serializers.py**

Create `epocha/apps/knowledge/serializers.py`:

```python
"""DRF serializers for Knowledge Graph API endpoints."""
from __future__ import annotations

from rest_framework import serializers

from .models import KnowledgeNode, KnowledgeRelation
from .ontology import RELATION_CATEGORIES


class KnowledgeNodeSerializer(serializers.ModelSerializer):
    """Serializer for knowledge graph nodes in Sigma.js format."""

    linked = serializers.SerializerMethodField()

    class Meta:
        model = KnowledgeNode
        fields = [
            "id", "entity_type", "name", "canonical_name",
            "description", "mention_count", "source_type", "linked",
        ]

    def get_linked(self, obj):
        """Return linked simulation entity info if any."""
        if obj.linked_agent_id:
            return {"kind": "agent", "id": obj.linked_agent_id}
        if obj.linked_group_id:
            return {"kind": "group", "id": obj.linked_group_id}
        if obj.linked_zone_id:
            return {"kind": "zone", "id": obj.linked_zone_id}
        if obj.linked_event_id:
            return {"kind": "event", "id": obj.linked_event_id}
        if obj.linked_institution_id:
            return {"kind": "institution", "id": obj.linked_institution_id}
        return None


class KnowledgeEdgeSerializer(serializers.ModelSerializer):
    """Serializer for knowledge graph edges in Sigma.js format."""

    source = serializers.IntegerField(source="source_node_id")
    target = serializers.IntegerField(source="target_node_id")
    category = serializers.SerializerMethodField()

    class Meta:
        model = KnowledgeRelation
        fields = ["id", "source", "target", "relation_type", "category", "weight"]

    def get_category(self, obj):
        return RELATION_CATEGORIES.get(obj.relation_type, "other")
```

- [ ] **Step 4: Implement api.py**

Create `epocha/apps/knowledge/api.py`:

```python
"""DRF API views for the Knowledge Graph."""
from __future__ import annotations

import logging

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import KnowledgeGraph, KnowledgeNode, KnowledgeRelation
from .serializers import KnowledgeEdgeSerializer, KnowledgeNodeSerializer

logger = logging.getLogger(__name__)


class KnowledgeGraphDataView(APIView):
    """GET /api/v1/knowledge/<sim_id>/graph/ -- Sigma.js-compatible graph data."""

    permission_classes = [IsAuthenticated]

    def get(self, request, sim_id):
        try:
            graph = KnowledgeGraph.objects.get(simulation_id=sim_id)
        except KnowledgeGraph.DoesNotExist:
            return Response(
                {"error": "No knowledge graph for this simulation"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Parse query params
        entity_types_param = request.query_params.get("entity_types", "")
        entity_types = [t.strip() for t in entity_types_param.split(",") if t.strip()] or None
        limit = min(int(request.query_params.get("limit", 100)), 1000)
        offset = int(request.query_params.get("offset", 0))

        # Query nodes
        nodes_qs = graph.nodes.select_related(
            "linked_agent", "linked_group", "linked_zone",
            "linked_event", "linked_institution",
        ).order_by("-mention_count")

        if entity_types:
            nodes_qs = nodes_qs.filter(entity_type__in=entity_types)

        total_nodes = nodes_qs.count()
        nodes = list(nodes_qs[offset:offset + limit])
        node_ids = {n.id for n in nodes}

        # Query edges between returned nodes
        edges = list(
            graph.relations.filter(
                source_node_id__in=node_ids,
                target_node_id__in=node_ids,
            ).select_related("source_node", "target_node")
        )

        return Response({
            "nodes": KnowledgeNodeSerializer(nodes, many=True).data,
            "edges": KnowledgeEdgeSerializer(edges, many=True).data,
            "stats": {
                "total_nodes": total_nodes,
                "returned_nodes": len(nodes),
                "has_more": (offset + limit) < total_nodes,
            },
        })
```

- [ ] **Step 5: Implement urls.py**

Create `epocha/apps/knowledge/urls.py`:

```python
"""URL routes for the Knowledge Graph API."""
from django.urls import path

from . import api

app_name = "knowledge"

urlpatterns = [
    path("<int:sim_id>/graph/", api.KnowledgeGraphDataView.as_view(), name="graph-data"),
]
```

- [ ] **Step 6: Register knowledge URLs in config/urls.py**

In `config/urls.py`, add after the existing API path registrations:

```python
    path("api/v1/knowledge/", include("epocha.apps.knowledge.urls")),
```

- [ ] **Step 7: Run API tests**

Run: `docker compose -f docker-compose.local.yml run --rm web pytest epocha/apps/knowledge/tests/test_api.py -v`

Expected: all PASS.

- [ ] **Step 8: Run full suite**

Run: `docker compose -f docker-compose.local.yml run --rm web pytest -q -m "not slow"`

Expected: all tests pass.

- [ ] **Step 9: Commit**

```
feat(knowledge): add graph data API with Sigma.js-compatible schema

CHANGE: Add DRF serializers for nodes and edges, a KnowledgeGraphDataView
returning paginated Sigma.js-compatible JSON with entity_type filtering,
linked simulation entity info, and relation categories. Register the
knowledge API URLs in the main URL configuration.
```

---

### Task 14: Upload and status API

**Files:**
- Modify: `epocha/apps/knowledge/api.py` (add upload and status views)
- Modify: `epocha/apps/knowledge/urls.py` (add new routes)
- Modify: `epocha/apps/knowledge/tests/test_api.py` (add upload and status tests)

- [ ] **Step 1: Add upload and status tests**

Append to `epocha/apps/knowledge/tests/test_api.py`:

```python
@pytest.mark.django_db(transaction=True)
class TestUploadAndStatusAPI:
    def test_upload_creates_simulation_and_returns_202(self, api_client):
        from pathlib import Path
        fixture_path = Path(__file__).parent / "fixtures" / "small_french_rev.txt"
        with open(fixture_path, "rb") as f:
            response = api_client.post(
                "/api/v1/knowledge/upload/",
                {"name": "Test Upload", "prompt": "French Revolution", "documents": [f]},
                format="multipart",
            )
        assert response.status_code == 202
        data = response.json()
        assert "simulation_id" in data
        assert "status" in data

    def test_status_endpoint(self, api_client, simulation, graph_with_data):
        url = f"/api/v1/knowledge/{simulation.id}/status/"
        response = api_client.get(url)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"

    def test_status_404_for_no_graph(self, api_client, simulation):
        url = f"/api/v1/knowledge/{simulation.id}/status/"
        response = api_client.get(url)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "no_graph"
```

- [ ] **Step 2: Run new tests to verify they fail**

Run: `docker compose -f docker-compose.local.yml run --rm web pytest epocha/apps/knowledge/tests/test_api.py::TestUploadAndStatusAPI -v`

Expected: 404 (no URL configured).

- [ ] **Step 3: Add upload and status views to api.py**

Append to `epocha/apps/knowledge/api.py`:

```python
from rest_framework.parsers import MultiPartParser, FormParser

from epocha.apps.simulation.models import Simulation
from epocha.apps.world.document_parser import extract_text


class KnowledgeGraphUploadView(APIView):
    """POST /api/v1/knowledge/upload/ -- upload documents and trigger extraction."""

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        name = request.data.get("name", "Unnamed Simulation")
        prompt = request.data.get("prompt", "")
        seed = int(request.data.get("seed", 42))
        files = request.FILES.getlist("documents")

        if not files:
            return Response(
                {"error": "At least one document file is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        simulation = Simulation.objects.create(
            name=name, seed=seed, owner=request.user,
        )

        documents_data = []
        for f in files:
            # Save temporarily and extract text
            import tempfile
            import os
            ext = os.path.splitext(f.name)[1]
            with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
                for chunk in f.chunks():
                    tmp.write(chunk)
                tmp_path = tmp.name

            try:
                raw_text = extract_text(tmp_path)
            finally:
                os.unlink(tmp_path)

            documents_data.append({
                "raw_text": raw_text,
                "title": f.name,
                "mime_type": f.content_type or "application/octet-stream",
                "original_filename": f.name,
            })

        # Run pipeline synchronously for MVP (Celery task in production)
        from .tasks import extract_and_generate

        result = extract_and_generate(
            simulation_id=simulation.id,
            user_id=request.user.id,
            documents_data=documents_data,
            prompt=prompt,
        )

        return Response(
            {
                "simulation_id": simulation.id,
                "status": result.get("status", "unknown"),
                "graph_id": result.get("graph_id"),
                "nodes": result.get("nodes", 0),
                "relations": result.get("relations", 0),
            },
            status=status.HTTP_202_ACCEPTED,
        )


class KnowledgeGraphStatusView(APIView):
    """GET /api/v1/knowledge/<sim_id>/status/ -- extraction status."""

    permission_classes = [IsAuthenticated]

    def get(self, request, sim_id):
        try:
            graph = KnowledgeGraph.objects.get(simulation_id=sim_id)
            return Response({
                "status": graph.status,
                "error": graph.error_message or None,
                "nodes": graph.nodes.count() if graph.status == "ready" else 0,
                "relations": graph.relations.count() if graph.status == "ready" else 0,
            })
        except KnowledgeGraph.DoesNotExist:
            return Response({"status": "no_graph"})
```

- [ ] **Step 4: Add new URL routes**

Update `epocha/apps/knowledge/urls.py`:

```python
"""URL routes for the Knowledge Graph API."""
from django.urls import path

from . import api

app_name = "knowledge"

urlpatterns = [
    path("upload/", api.KnowledgeGraphUploadView.as_view(), name="upload"),
    path("<int:sim_id>/graph/", api.KnowledgeGraphDataView.as_view(), name="graph-data"),
    path("<int:sim_id>/status/", api.KnowledgeGraphStatusView.as_view(), name="status"),
]
```

- [ ] **Step 5: Run all API tests**

Run: `docker compose -f docker-compose.local.yml run --rm web pytest epocha/apps/knowledge/tests/test_api.py -v`

Expected: all PASS.

- [ ] **Step 6: Run full suite**

Run: `docker compose -f docker-compose.local.yml run --rm web pytest -q -m "not slow"`

Expected: all tests pass.

- [ ] **Step 7: Commit**

```
feat(knowledge): add upload and extraction status API endpoints

CHANGE: Add POST /api/v1/knowledge/upload/ for document upload and
extraction trigger (creates simulation, parses files, runs pipeline),
and GET /api/v1/knowledge/<sim_id>/status/ for checking extraction
progress. Upload runs synchronously for MVP; Celery async path can be
added later. The status endpoint returns graph node/relation counts
when ready.
```

---

### Task 15: Dashboard view and template

**Files:**
- New: `epocha/apps/knowledge/views.py`
- New: `epocha/apps/knowledge/templates/knowledge/graph.html`
- Modify: `epocha/apps/dashboard/urls.py` (add knowledge graph route)
- New: `epocha/apps/knowledge/tests/test_views.py`

- [ ] **Step 1: Write the failing tests**

Create `epocha/apps/knowledge/tests/test_views.py`:

```python
"""Tests for the knowledge graph dashboard view."""
import pytest
from django.test import Client

from epocha.apps.knowledge.models import (
    ExtractionCache, KnowledgeGraph, KnowledgeNode,
)
from epocha.apps.simulation.models import Simulation
from epocha.apps.users.models import User


@pytest.fixture
def user(db):
    return User.objects.create_user(
        email="view@epocha.dev", username="viewuser", password="pass1234",
    )


@pytest.fixture
def logged_in_client(user):
    client = Client()
    client.login(username="viewuser", password="pass1234")
    return client


@pytest.fixture
def simulation(user):
    return Simulation.objects.create(name="ViewTest", seed=42, owner=user)


@pytest.fixture
def graph_with_nodes(simulation):
    cache = ExtractionCache.objects.create(
        cache_key="view" + "0" * 60, documents_hash="v" * 64,
        ontology_version="v1", extraction_prompt_version="v1",
        llm_model="test", extracted_data={}, stats={},
    )
    graph = KnowledgeGraph.objects.create(
        simulation=simulation, extraction_cache=cache, status="ready",
    )
    KnowledgeNode.objects.create(
        graph=graph, entity_type="person",
        name="Robespierre", canonical_name="robespierre",
        description="Leader", source_type="document",
        confidence=0.9, mention_count=5, embedding=[0.1] * 1024,
    )
    return graph


@pytest.mark.django_db
class TestKnowledgeGraphView:
    def test_returns_200_with_graph(self, logged_in_client, simulation, graph_with_nodes):
        url = f"/simulations/{simulation.id}/knowledge-graph/"
        response = logged_in_client.get(url)
        assert response.status_code == 200

    def test_contains_sigma_js(self, logged_in_client, simulation, graph_with_nodes):
        url = f"/simulations/{simulation.id}/knowledge-graph/"
        response = logged_in_client.get(url)
        content = response.content.decode()
        assert "sigma" in content.lower()

    def test_contains_simulation_name(self, logged_in_client, simulation, graph_with_nodes):
        url = f"/simulations/{simulation.id}/knowledge-graph/"
        response = logged_in_client.get(url)
        content = response.content.decode()
        assert simulation.name in content

    def test_redirects_unauthenticated(self, simulation, graph_with_nodes):
        client = Client()
        url = f"/simulations/{simulation.id}/knowledge-graph/"
        response = client.get(url)
        assert response.status_code == 302

    def test_404_without_graph(self, logged_in_client, simulation):
        url = f"/simulations/{simulation.id}/knowledge-graph/"
        response = logged_in_client.get(url)
        assert response.status_code == 404
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `docker compose -f docker-compose.local.yml run --rm web pytest epocha/apps/knowledge/tests/test_views.py -v`

Expected: 404 (no URL configured).

- [ ] **Step 3: Implement views.py**

Create `epocha/apps/knowledge/views.py`:

```python
"""Dashboard views for the Knowledge Graph."""
from __future__ import annotations

import json

from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404, render

from epocha.apps.simulation.models import Simulation

from .models import KnowledgeGraph, KnowledgeNode
from .ontology import RELATION_CATEGORIES
from .serializers import KnowledgeEdgeSerializer, KnowledgeNodeSerializer


@login_required
def knowledge_graph_view(request, sim_id):
    """Render the knowledge graph visualization page."""
    simulation = get_object_or_404(Simulation, pk=sim_id)

    try:
        graph = KnowledgeGraph.objects.get(simulation=simulation)
    except KnowledgeGraph.DoesNotExist:
        raise Http404("No knowledge graph for this simulation")

    # Inline initial data (top 100 nodes by mention_count)
    nodes = list(
        graph.nodes.select_related(
            "linked_agent", "linked_group", "linked_zone",
            "linked_event", "linked_institution",
        ).order_by("-mention_count")[:100]
    )
    node_ids = {n.id for n in nodes}
    edges = list(
        graph.relations.filter(
            source_node_id__in=node_ids,
            target_node_id__in=node_ids,
        )
    )

    # Entity type color mapping
    entity_colors = {
        "person": "#e74c3c",
        "group": "#e67e22",
        "place": "#2ecc71",
        "institution": "#3498db",
        "event": "#9b59b6",
        "concept": "#1abc9c",
        "ideology": "#f39c12",
        "object": "#95a5a6",
        "norm": "#34495e",
        "value": "#e91e63",
    }

    # Relation category color mapping
    category_colors = {
        "membership": "#3498db",
        "spatial": "#2ecc71",
        "temporal": "#9b59b6",
        "belief": "#e74c3c",
        "social": "#e67e22",
        "kinship": "#e91e63",
        "causal": "#f39c12",
        "participation": "#1abc9c",
        "production": "#95a5a6",
    }

    return render(request, "knowledge/graph.html", {
        "simulation": simulation,
        "graph": graph,
        "initial_nodes_json": json.dumps(KnowledgeNodeSerializer(nodes, many=True).data),
        "initial_edges_json": json.dumps(KnowledgeEdgeSerializer(edges, many=True).data),
        "total_nodes": graph.nodes.count(),
        "entity_colors": json.dumps(entity_colors),
        "category_colors": json.dumps(category_colors),
        "entity_types": list(entity_colors.keys()),
        "relation_categories": json.dumps(RELATION_CATEGORIES),
    })
```

- [ ] **Step 4: Create the template**

Create `epocha/apps/knowledge/templates/knowledge/graph.html`:

```html
{% extends "dashboard/base.html" %}
{% block title %}Knowledge Graph - {{ simulation.name }}{% endblock %}

{% block content %}
<div class="container-fluid px-4 py-3">
    <div class="d-flex justify-content-between align-items-center mb-3">
        <h2>Knowledge Graph: {{ simulation.name }}</h2>
        <div>
            <span class="badge bg-info">{{ total_nodes }} nodes</span>
            <a href="{% url 'simulation-detail' simulation.id %}" class="btn btn-sm btn-outline-secondary ms-2">Back</a>
        </div>
    </div>

    <!-- Filter toggles -->
    <div x-data="{ filters: {{ entity_types|safe }} }" class="mb-3">
        <div class="d-flex flex-wrap gap-2">
            {% for etype in entity_types %}
            <button
                class="btn btn-sm"
                :class="filters.includes('{{ etype }}') ? 'btn-primary' : 'btn-outline-secondary'"
                @click="toggleFilter('{{ etype }}')"
            >
                {{ etype }}
            </button>
            {% endfor %}
        </div>
    </div>

    <!-- Graph container -->
    <div id="kg-container" style="width: 100%; height: 600px; border: 1px solid #333; border-radius: 8px; background: #1a1a2e;"></div>

    <!-- Detail panel -->
    <div id="kg-detail" class="mt-3 p-3 border rounded" style="display: none;">
        <h5 id="kg-detail-name"></h5>
        <p id="kg-detail-type" class="text-muted small"></p>
        <p id="kg-detail-description"></p>
        <div id="kg-detail-linked" class="mt-2"></div>
    </div>
</div>

<!-- Sigma.js -->
<script src="https://cdnjs.cloudflare.com/ajax/libs/sigma.js/2.4.0/sigma.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/graphology/0.25.4/graphology.umd.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/graphology-layout-forceatlas2/0.10.1/graphology-layout-forceatlas2.min.js"></script>

<script>
(function() {
    const nodes = {{ initial_nodes_json|safe }};
    const edges = {{ initial_edges_json|safe }};
    const entityColors = {{ entity_colors|safe }};
    const categoryColors = {{ category_colors|safe }};

    const graph = new graphology.Graph();

    // Add nodes
    nodes.forEach(function(node) {
        graph.addNode(node.id, {
            label: node.name,
            x: Math.random() * 100,
            y: Math.random() * 100,
            size: Math.max(3, Math.min(15, node.mention_count * 2)),
            color: entityColors[node.entity_type] || "#999",
            entityType: node.entity_type,
            description: node.description,
            linked: node.linked,
        });
    });

    // Add edges
    edges.forEach(function(edge) {
        if (graph.hasNode(edge.source) && graph.hasNode(edge.target)) {
            graph.addEdge(edge.source, edge.target, {
                label: edge.relation_type,
                size: Math.max(1, edge.weight * 3),
                color: categoryColors[edge.category] || "#666",
            });
        }
    });

    // Force layout
    var settings = graphology.library
        ? graphology.library.ForceAtlas2.inferSettings(graph)
        : { gravity: 1, scalingRatio: 2 };

    if (typeof ForceAtlas2Layout !== "undefined") {
        ForceAtlas2Layout.assign(graph, { iterations: 100, settings: settings });
    } else if (typeof graphologyLayoutForceAtlas2 !== "undefined") {
        graphologyLayoutForceAtlas2.assign(graph, { iterations: 100, settings: settings });
    }

    // Render
    const container = document.getElementById("kg-container");
    const renderer = new Sigma(graph, container, {
        renderLabels: true,
        labelFont: "12px sans-serif",
        labelColor: { color: "#ccc" },
    });

    // Click handler for detail panel
    renderer.on("clickNode", function(event) {
        var nodeId = event.node;
        var attrs = graph.getNodeAttributes(nodeId);
        document.getElementById("kg-detail").style.display = "block";
        document.getElementById("kg-detail-name").textContent = attrs.label;
        document.getElementById("kg-detail-type").textContent = attrs.entityType;
        document.getElementById("kg-detail-description").textContent = attrs.description || "No description";

        var linkedDiv = document.getElementById("kg-detail-linked");
        if (attrs.linked) {
            linkedDiv.innerHTML = '<a href="#" class="text-info">Linked: ' + attrs.linked.kind + ' #' + attrs.linked.id + '</a>';
        } else {
            linkedDiv.innerHTML = '<span class="text-muted">Not linked to simulation entity</span>';
        }
    });

    // Filter toggle function
    window.toggleFilter = function(entityType) {
        graph.forEachNode(function(node, attrs) {
            if (attrs.entityType === entityType) {
                graph.setNodeAttribute(node, "hidden", !graph.getNodeAttribute(node, "hidden"));
            }
        });
        renderer.refresh();
    };
})();
</script>
{% endblock %}
```

- [ ] **Step 5: Add dashboard URL route**

In `epocha/apps/dashboard/urls.py`, add after the existing graph routes:

```python
    path("simulations/<int:sim_id>/knowledge-graph/", knowledge_graph_view, name="knowledge-graph"),
```

And at the top of the file, add the import:

```python
from epocha.apps.knowledge.views import knowledge_graph_view
```

- [ ] **Step 6: Run view tests**

Run: `docker compose -f docker-compose.local.yml run --rm web pytest epocha/apps/knowledge/tests/test_views.py -v`

Expected: all PASS.

- [ ] **Step 7: Run full suite**

Run: `docker compose -f docker-compose.local.yml run --rm web pytest -q -m "not slow"`

Expected: all tests pass.

- [ ] **Step 8: Commit**

```
feat(knowledge): add dashboard visualization page with Sigma.js

CHANGE: Add a knowledge graph dashboard view at
/simulations/<id>/knowledge-graph/ rendering the top 100 nodes by
mention_count with Sigma.js force layout. Nodes are color-coded by
entity type, edges by relation category. Entity type filter toggles,
click-to-detail panel with description and linked entity info. The
page follows the same pattern as the existing social graph page.
```

---

### Task 16: Cache cleanup management command

**Files:**
- New: `epocha/apps/knowledge/management/commands/cleanup_extraction_cache.py`
- New: `epocha/apps/knowledge/tests/test_cleanup_command.py`

- [ ] **Step 1: Write the failing tests**

Create `epocha/apps/knowledge/tests/test_cleanup_command.py`:

```python
"""Tests for the cleanup_extraction_cache management command."""
from datetime import timedelta

import pytest
from django.core.management import call_command
from django.utils import timezone

from epocha.apps.knowledge.models import ExtractionCache


@pytest.fixture
def old_unused_cache(db):
    return ExtractionCache.objects.create(
        cache_key="old" + "0" * 61,
        documents_hash="old" + "0" * 61,
        ontology_version="v0",
        extraction_prompt_version="v0",
        llm_model="old-model",
        extracted_data={},
        stats={},
        hit_count=0,
    )


@pytest.fixture
def recent_unused_cache(db):
    return ExtractionCache.objects.create(
        cache_key="new" + "0" * 61,
        documents_hash="new" + "0" * 61,
        ontology_version="v1",
        extraction_prompt_version="v1",
        llm_model="current",
        extracted_data={},
        stats={},
        hit_count=0,
    )


@pytest.fixture
def old_used_cache(db):
    entry = ExtractionCache.objects.create(
        cache_key="used" + "0" * 60,
        documents_hash="used" + "0" * 60,
        ontology_version="v0",
        extraction_prompt_version="v0",
        llm_model="old",
        extracted_data={},
        stats={},
        hit_count=5,
    )
    return entry


@pytest.mark.django_db
class TestCleanupCommand:
    def test_deletes_old_unused_entries(self, old_unused_cache):
        # Manually set created_at to 60 days ago
        ExtractionCache.objects.filter(pk=old_unused_cache.pk).update(
            created_at=timezone.now() - timedelta(days=60),
        )
        call_command("cleanup_extraction_cache", "--min-age-days", "30", "--max-hit-count", "0")
        assert not ExtractionCache.objects.filter(pk=old_unused_cache.pk).exists()

    def test_keeps_recent_entries(self, recent_unused_cache):
        call_command("cleanup_extraction_cache", "--min-age-days", "30", "--max-hit-count", "0")
        assert ExtractionCache.objects.filter(pk=recent_unused_cache.pk).exists()

    def test_keeps_used_entries(self, old_used_cache):
        ExtractionCache.objects.filter(pk=old_used_cache.pk).update(
            created_at=timezone.now() - timedelta(days=60),
        )
        call_command("cleanup_extraction_cache", "--min-age-days", "30", "--max-hit-count", "0")
        assert ExtractionCache.objects.filter(pk=old_used_cache.pk).exists()

    def test_dry_run_does_not_delete(self, old_unused_cache):
        ExtractionCache.objects.filter(pk=old_unused_cache.pk).update(
            created_at=timezone.now() - timedelta(days=60),
        )
        call_command("cleanup_extraction_cache", "--min-age-days", "30", "--max-hit-count", "0", "--dry-run")
        assert ExtractionCache.objects.filter(pk=old_unused_cache.pk).exists()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `docker compose -f docker-compose.local.yml run --rm web pytest epocha/apps/knowledge/tests/test_cleanup_command.py -v`

Expected: CommandError or ImportError.

- [ ] **Step 3: Implement the management command**

Create `epocha/apps/knowledge/management/commands/cleanup_extraction_cache.py`:

```python
"""Management command to clean up unused extraction cache entries."""
from __future__ import annotations

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from epocha.apps.knowledge.models import ExtractionCache


class Command(BaseCommand):
    help = "Delete old, unused ExtractionCache entries to prevent unbounded growth."

    def add_arguments(self, parser):
        parser.add_argument(
            "--min-age-days", type=int, default=30,
            help="Minimum age in days before an entry is eligible for deletion (default: 30)",
        )
        parser.add_argument(
            "--max-hit-count", type=int, default=0,
            help="Maximum hit_count for an entry to be eligible for deletion (default: 0)",
        )
        parser.add_argument(
            "--dry-run", action="store_true",
            help="Show what would be deleted without actually deleting",
        )

    def handle(self, *args, **options):
        min_age_days = options["min_age_days"]
        max_hit_count = options["max_hit_count"]
        dry_run = options["dry_run"]

        cutoff = timezone.now() - timedelta(days=min_age_days)

        candidates = ExtractionCache.objects.filter(
            created_at__lt=cutoff,
            hit_count__lte=max_hit_count,
        )

        # Exclude entries that have active graphs pointing to them
        candidates = candidates.exclude(graphs__isnull=False)

        count = candidates.count()

        if dry_run:
            self.stdout.write(
                f"[DRY RUN] Would delete {count} cache entries "
                f"(older than {min_age_days} days, hit_count <= {max_hit_count})"
            )
            return

        deleted, _ = candidates.delete()
        self.stdout.write(self.style.SUCCESS(
            f"Deleted {deleted} cache entries "
            f"(older than {min_age_days} days, hit_count <= {max_hit_count})"
        ))
```

- [ ] **Step 4: Run cleanup command tests**

Run: `docker compose -f docker-compose.local.yml run --rm web pytest epocha/apps/knowledge/tests/test_cleanup_command.py -v`

Expected: all PASS.

- [ ] **Step 5: Run full suite**

Run: `docker compose -f docker-compose.local.yml run --rm web pytest -q -m "not slow"`

Expected: all tests pass.

- [ ] **Step 6: Commit**

```
feat(knowledge): add cache cleanup management command

CHANGE: Add cleanup_extraction_cache management command that deletes
ExtractionCache entries older than N days with hit_count at or below
a threshold, excluding entries with active graphs. Supports --dry-run
for safe preview.
```

---

## Self-Review Summary

After completing Tasks 13-16 in this plan:

- Graph data JSON API with Sigma.js-compatible schema, entity type filtering, pagination
- Document upload API endpoint creating simulations and triggering extraction
- Extraction status API for progress monitoring
- Dashboard visualization page with Sigma.js force layout, entity type color coding, filter toggles, click-to-detail
- Cache cleanup management command with dry-run support

**The Knowledge Graph feature is now complete end-to-end:**
documents -> chunk -> embed -> cache check -> extract -> merge -> cache -> materialize -> generate agents -> visualize

**All four plans delivered:**
- Part 1 (Foundations): models, embedding, chunking, cache
- Part 2 (Extraction): prompts, per-chunk extraction, merge
- Part 3 (Graph + orchestration): graph models, materialization, Celery, generator integration
- Part 4 (API + dashboard): upload, status, visualization, cleanup

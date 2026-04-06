# Social Relationship Graph Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a dedicated full-viewport graph page to the dashboard that visualizes agent relationships, factions, and government structure using Sigma.js.

**Architecture:** A new Django view + template at `/dashboard/simulation/<id>/graph/`. A JSON data endpoint provides nodes/edges/power_flow. Sigma.js renders the graph with ForceAtlas2 layout. Alpine.js handles the detail panel and filters. All CDN, no build step.

**Tech Stack:** Django views, Sigma.js (CDN), graphology + graphology-layout-forceatlas2 (CDN), Alpine.js, Tailwind CSS CDN

**Spec:** `docs/superpowers/specs/2026-04-06-social-graph-design.md`

---

## File Structure

| File | Responsibility | New/Modify |
|------|---------------|------------|
| `epocha/apps/dashboard/views.py` | graph_view, graph_data_view, graph_agent_detail_view | Modify |
| `epocha/apps/dashboard/urls.py` | 3 new routes | Modify |
| `epocha/apps/dashboard/templates/dashboard/simulation_graph.html` | Graph page template | New |
| `epocha/apps/dashboard/templates/dashboard/simulation_detail.html` | "Relationships" button | Modify |

---

### Task 1: Graph data endpoint

JSON API that provides nodes, edges, power flow lines, and government metadata for the graph.

**Files:**
- Modify: `epocha/apps/dashboard/views.py`
- Modify: `epocha/apps/dashboard/urls.py`

- [ ] **Step 1: Write the failing test**

Create `epocha/apps/dashboard/tests/test_graph.py`:

```python
"""Tests for the social graph data endpoints."""
import json

import pytest
from django.test import Client

from epocha.apps.agents.models import Agent, Group, Relationship
from epocha.apps.simulation.models import Simulation
from epocha.apps.users.models import User
from epocha.apps.world.models import Government, World


@pytest.fixture
def user(db):
    return User.objects.create_user(email="graph@epocha.dev", username="graphtest", password="pass123")


@pytest.fixture
def logged_in_client(user):
    client = Client()
    client.login(email="graph@epocha.dev", password="pass123")
    return client


@pytest.fixture
def simulation(user):
    return Simulation.objects.create(name="GraphTest", seed=42, owner=user)


@pytest.fixture
def world(simulation):
    return World.objects.create(simulation=simulation)


@pytest.fixture
def setup_graph_data(simulation):
    faction = Group.objects.create(
        simulation=simulation, name="The Guild", objective="Protect",
        cohesion=0.7, formed_at_tick=1,
    )
    marco = Agent.objects.create(
        simulation=simulation, name="Marco", role="blacksmith",
        charisma=0.8, mood=0.6, social_class="middle", group=faction,
        personality={"openness": 0.5},
    )
    elena = Agent.objects.create(
        simulation=simulation, name="Elena", role="farmer",
        charisma=0.5, mood=0.4, social_class="working",
        personality={"openness": 0.5},
    )
    faction.leader = marco
    faction.save(update_fields=["leader"])
    Relationship.objects.create(
        agent_from=marco, agent_to=elena,
        relation_type="friendship", strength=0.7, sentiment=0.5, since_tick=0,
    )
    government = Government.objects.create(
        simulation=simulation, government_type="democracy",
        head_of_state=marco, ruling_faction=faction,
        stability=0.6,
    )
    return marco, elena, faction, government


@pytest.mark.django_db
class TestGraphDataEndpoint:
    def test_returns_nodes_and_edges(self, logged_in_client, simulation, world, setup_graph_data):
        marco, elena, faction, government = setup_graph_data
        response = logged_in_client.get(f"/simulations/{simulation.id}/graph/data/")
        assert response.status_code == 200
        data = response.json()
        assert len(data["nodes"]) == 2
        assert len(data["edges"]) == 1
        assert data["government"]["type"] == "Democracy"

    def test_nodes_have_required_fields(self, logged_in_client, simulation, world, setup_graph_data):
        response = logged_in_client.get(f"/simulations/{simulation.id}/graph/data/")
        data = response.json()
        node = data["nodes"][0]
        required = {"id", "label", "role", "faction", "faction_color", "is_leader",
                     "is_head_of_state", "charisma", "mood", "social_class", "is_alive"}
        assert required.issubset(set(node.keys()))

    def test_edges_have_required_fields(self, logged_in_client, simulation, world, setup_graph_data):
        response = logged_in_client.get(f"/simulations/{simulation.id}/graph/data/")
        data = response.json()
        edge = data["edges"][0]
        assert "source" in edge
        assert "target" in edge
        assert "type" in edge
        assert "strength" in edge
        assert "sentiment" in edge

    def test_power_flow_lines_present(self, logged_in_client, simulation, world, setup_graph_data):
        response = logged_in_client.get(f"/simulations/{simulation.id}/graph/data/")
        data = response.json()
        assert "power_flow" in data
        assert len(data["power_flow"]) >= 1

    def test_faction_color_is_consistent(self, logged_in_client, simulation, world, setup_graph_data):
        """Same faction should always produce the same color."""
        r1 = logged_in_client.get(f"/simulations/{simulation.id}/graph/data/")
        r2 = logged_in_client.get(f"/simulations/{simulation.id}/graph/data/")
        nodes1 = {n["id"]: n for n in r1.json()["nodes"]}
        nodes2 = {n["id"]: n for n in r2.json()["nodes"]}
        for nid in nodes1:
            assert nodes1[nid]["faction_color"] == nodes2[nid]["faction_color"]

    def test_requires_authentication(self, simulation, world, setup_graph_data):
        client = Client()
        response = client.get(f"/simulations/{simulation.id}/graph/data/")
        assert response.status_code in (302, 403)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `docker compose -f docker-compose.local.yml exec -T web pytest epocha/apps/dashboard/tests/test_graph.py -v`
Expected: FAIL (view does not exist).

- [ ] **Step 3: Implement the graph data endpoint**

In `epocha/apps/dashboard/views.py`, add this function:

```python
def _faction_color(name: str) -> str:
    """Generate a deterministic hex color from a faction name."""
    import hashlib
    h = hashlib.md5(name.encode()).hexdigest()
    # Use hue from hash, keep saturation/lightness in a pleasant range
    r = int(h[:2], 16)
    g = int(h[2:4], 16)
    b = int(h[4:6], 16)
    # Ensure colors are visible on dark background (boost brightness)
    r = max(80, r)
    g = max(80, g)
    b = max(80, b)
    return f"#{r:02x}{g:02x}{b:02x}"


@login_required(login_url="/login/")
def graph_data_view(request, sim_id):
    """JSON endpoint providing graph data for Sigma.js rendering."""
    from epocha.apps.agents.models import Group, Relationship
    from epocha.apps.world.models import Government

    simulation = get_object_or_404(Simulation, id=sim_id, owner=request.user)

    # Government info
    try:
        government = Government.objects.get(simulation=simulation)
        from epocha.apps.world.government_types import GOVERNMENT_TYPES
        gov_label = GOVERNMENT_TYPES.get(government.government_type, {}).get("label", government.government_type)
        head_of_state_id = government.head_of_state_id
        ruling_faction_id = government.ruling_faction_id
        gov_data = {
            "type": gov_label,
            "head_of_state_id": head_of_state_id,
            "ruling_faction": government.ruling_faction.name if government.ruling_faction else None,
            "stability": round(government.stability, 2),
        }
    except Government.DoesNotExist:
        head_of_state_id = None
        ruling_faction_id = None
        gov_data = {"type": "None", "head_of_state_id": None, "ruling_faction": None, "stability": 0.0}

    # Nodes
    agents = Agent.objects.filter(simulation=simulation).select_related("group")
    faction_leaders = set(
        Group.objects.filter(simulation=simulation, leader__isnull=False)
        .values_list("leader_id", flat=True)
    )

    nodes = []
    for agent in agents:
        faction_name = agent.group.name if agent.group else None
        nodes.append({
            "id": agent.id,
            "label": agent.name,
            "role": agent.role,
            "faction": faction_name,
            "faction_color": _faction_color(faction_name) if faction_name else "#6b7280",
            "is_leader": agent.id in faction_leaders,
            "is_head_of_state": agent.id == head_of_state_id,
            "charisma": round(agent.charisma, 2),
            "mood": round(agent.mood, 2),
            "social_class": agent.social_class,
            "is_alive": agent.is_alive,
        })

    # Edges
    relationships = Relationship.objects.filter(
        agent_from__simulation=simulation,
    ).select_related("agent_from", "agent_to")

    edges = [
        {
            "source": rel.agent_from_id,
            "target": rel.agent_to_id,
            "type": rel.relation_type,
            "strength": round(rel.strength, 2),
            "sentiment": round(rel.sentiment, 2),
        }
        for rel in relationships
    ]

    # Power flow lines
    power_flow = []
    if head_of_state_id and ruling_faction_id:
        ruling_faction = Group.objects.filter(id=ruling_faction_id).first()
        if ruling_faction and ruling_faction.leader_id:
            # Head of state -> ruling faction leader (if different)
            if head_of_state_id != ruling_faction.leader_id:
                power_flow.append({
                    "source": head_of_state_id,
                    "target": ruling_faction.leader_id,
                    "type": "power_flow",
                })
            # Ruling faction leader -> faction members
            member_ids = list(
                Agent.objects.filter(group=ruling_faction, is_alive=True)
                .exclude(id=ruling_faction.leader_id)
                .values_list("id", flat=True)
            )
            for mid in member_ids:
                power_flow.append({
                    "source": ruling_faction.leader_id,
                    "target": mid,
                    "type": "power_flow",
                })

    return JsonResponse({
        "nodes": nodes,
        "edges": edges,
        "power_flow": power_flow,
        "government": gov_data,
    })
```

Add the URL in `epocha/apps/dashboard/urls.py`:

```python
    path("simulations/<int:sim_id>/graph/data/", views.graph_data_view, name="graph-data"),
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `docker compose -f docker-compose.local.yml exec -T web pytest epocha/apps/dashboard/tests/test_graph.py -v`
Expected: All 6 tests PASS.

- [ ] **Step 5: Commit**

```
feat(dashboard): add graph data JSON endpoint

CHANGE: Implement graph_data_view serving nodes (agents with faction,
charisma, political role), edges (relationships with type, strength,
sentiment), power flow lines (chain of command), and government metadata.
Faction colors are deterministic hashes for consistency.
```

---

### Task 2: Agent detail endpoint (lazy load)

JSON endpoint for agent details + recent memories, loaded when the user clicks a node.

**Files:**
- Modify: `epocha/apps/dashboard/views.py`
- Modify: `epocha/apps/dashboard/urls.py`
- Test: `epocha/apps/dashboard/tests/test_graph.py`

- [ ] **Step 1: Write the failing test**

Add to `epocha/apps/dashboard/tests/test_graph.py`:

```python
@pytest.mark.django_db
class TestGraphAgentDetailEndpoint:
    def test_returns_agent_details(self, logged_in_client, simulation, world, setup_graph_data):
        marco, elena, faction, government = setup_graph_data
        response = logged_in_client.get(f"/simulations/{simulation.id}/graph/agent/{marco.id}/")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Marco"
        assert data["role"] == "blacksmith"
        assert "relationships" in data
        assert "recent_memories" in data

    def test_includes_relationships(self, logged_in_client, simulation, world, setup_graph_data):
        marco, elena, faction, government = setup_graph_data
        response = logged_in_client.get(f"/simulations/{simulation.id}/graph/agent/{marco.id}/")
        data = response.json()
        assert len(data["relationships"]) >= 1
        rel = data["relationships"][0]
        assert "agent" in rel
        assert "type" in rel
        assert "sentiment" in rel

    def test_includes_recent_memories(self, logged_in_client, simulation, world, setup_graph_data):
        from epocha.apps.agents.models import Memory
        marco, elena, faction, government = setup_graph_data
        Memory.objects.create(
            agent=marco, content="I argued with Elena about the trade deal.",
            emotional_weight=0.5, source_type="direct", tick_created=10,
        )
        response = logged_in_client.get(f"/simulations/{simulation.id}/graph/agent/{marco.id}/")
        data = response.json()
        assert len(data["recent_memories"]) >= 1
        assert "argued" in data["recent_memories"][0]["content"].lower()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `docker compose -f docker-compose.local.yml exec -T web pytest epocha/apps/dashboard/tests/test_graph.py::TestGraphAgentDetailEndpoint -v`

- [ ] **Step 3: Implement agent detail endpoint**

In `epocha/apps/dashboard/views.py`:

```python
@login_required(login_url="/login/")
def graph_agent_detail_view(request, sim_id, agent_id):
    """JSON endpoint for agent details in the graph detail panel."""
    from epocha.apps.agents.models import Memory, Relationship

    simulation = get_object_or_404(Simulation, id=sim_id, owner=request.user)
    agent = get_object_or_404(Agent, id=agent_id, simulation=simulation)

    # Relationships (bidirectional)
    from django.db.models import Q
    relationships = Relationship.objects.filter(
        Q(agent_from=agent) | Q(agent_to=agent)
    ).select_related("agent_from", "agent_to")

    rels = []
    for rel in relationships:
        other = rel.agent_to if rel.agent_from_id == agent.id else rel.agent_from
        rels.append({
            "agent": other.name,
            "agent_id": other.id,
            "type": rel.relation_type,
            "strength": round(rel.strength, 2),
            "sentiment": round(rel.sentiment, 2),
        })

    # Recent memories: agent's own + mentions of related agents
    related_names = [r["agent"] for r in rels]
    own_memories = Memory.objects.filter(
        agent=agent, is_active=True,
    ).order_by("-tick_created")[:5]

    # Memories mentioning related agents
    from django.db.models import Q as DQ
    name_filters = DQ()
    for name in related_names[:5]:
        name_filters |= DQ(content__icontains=name)

    if name_filters:
        related_memories = Memory.objects.filter(
            agent=agent, is_active=True,
        ).filter(name_filters).order_by("-tick_created")[:5]
    else:
        related_memories = Memory.objects.none()

    # Merge and deduplicate, limit to 5
    seen_ids = set()
    memories = []
    for m in list(related_memories) + list(own_memories):
        if m.id not in seen_ids and len(memories) < 5:
            seen_ids.add(m.id)
            memories.append({
                "content": m.content,
                "tick": m.tick_created,
                "source_type": m.source_type,
            })

    return JsonResponse({
        "id": agent.id,
        "name": agent.name,
        "role": agent.role,
        "faction": agent.group.name if agent.group else None,
        "social_class": agent.social_class,
        "health": round(agent.health, 2),
        "mood": round(agent.mood, 2),
        "wealth": round(agent.wealth, 1),
        "charisma": round(agent.charisma, 2),
        "is_alive": agent.is_alive,
        "relationships": rels,
        "recent_memories": memories,
    })
```

Add URL:

```python
    path("simulations/<int:sim_id>/graph/agent/<int:agent_id>/", views.graph_agent_detail_view, name="graph-agent-detail"),
```

- [ ] **Step 4: Run tests**

Run: `docker compose -f docker-compose.local.yml exec -T web pytest epocha/apps/dashboard/tests/test_graph.py -v`
Expected: All 9 tests PASS.

- [ ] **Step 5: Commit**

```
feat(dashboard): add agent detail endpoint for graph panel

CHANGE: Implement graph_agent_detail_view returning agent info plus
recent memories that mention related agents. The detail panel turns the
graph from a static snapshot into a narrative gateway.
```

---

### Task 3: Graph page template with Sigma.js

The full-viewport graph template with Sigma.js rendering, ForceAtlas2 layout, and Alpine.js interactivity.

**Files:**
- Create: `epocha/apps/dashboard/templates/dashboard/simulation_graph.html`
- Modify: `epocha/apps/dashboard/views.py` (add graph_view)
- Modify: `epocha/apps/dashboard/urls.py` (add route)

- [ ] **Step 1: Add the graph view function**

In `epocha/apps/dashboard/views.py`:

```python
@login_required(login_url="/login/")
def graph_view(request, sim_id):
    """Render the social relationship graph page."""
    simulation = get_object_or_404(Simulation, id=sim_id, owner=request.user)
    return render(request, "dashboard/simulation_graph.html", {
        "simulation": simulation,
    })
```

Add URL (BEFORE the graph/data/ and graph/agent/ routes):

```python
    path("simulations/<int:sim_id>/graph/", views.graph_view, name="graph"),
```

- [ ] **Step 2: Create the graph template**

Create `epocha/apps/dashboard/templates/dashboard/simulation_graph.html`:

```html
{% extends "dashboard/base.html" %}
{% block title %}{{ simulation.name }} - Relationships - Epocha{% endblock %}

{% block extra_head %}
<!-- Sigma.js + graphology via CDN -->
<script src="https://cdn.jsdelivr.net/npm/graphology@0.25.4/dist/graphology.umd.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/graphology-layout-forceatlas2@0.10.1/dist/graphology-layout-forceatlas2.umd.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/sigma@2.4.0/build/sigma.min.js"></script>
<style>
#graph-container { width: 100%; height: calc(100vh - 140px); }
@keyframes pulse-tension { 0%, 100% { opacity: 0.6; } 50% { opacity: 1.0; } }
.filter-btn { transition: all 0.2s; }
.filter-btn.active { ring: 2px; }
.detail-panel { transition: transform 0.2s ease; }
.detail-panel.hidden { transform: translateX(100%); }
</style>
{% endblock %}

{% block content %}
<div x-data="graphPage()">
    <!-- Header -->
    <div class="flex justify-between items-start mb-4">
        <div>
            <h1 class="text-2xl font-bold">{{ simulation.name }} -- Relationships</h1>
            <p class="text-gray-400 text-sm mt-1">Social graph with factions and government structure</p>
        </div>
        <div class="flex gap-2">
            <a href="{% url 'dashboard:simulation-detail' sim_id=simulation.id %}" class="bg-gray-600 hover:bg-gray-500 text-white px-4 py-2 rounded font-medium">Back to simulation</a>
            <button @click="refreshData()" class="bg-indigo-600 hover:bg-indigo-500 text-white px-4 py-2 rounded font-medium">Refresh</button>
        </div>
    </div>

    <!-- Filters -->
    <div class="flex flex-wrap gap-2 mb-3">
        <template x-for="(color, type) in edgeTypes" :key="type">
            <button @click="toggleFilter(type)"
                    class="filter-btn text-xs px-3 py-1 rounded-full border"
                    :class="filters[type] ? 'opacity-100 border-white' : 'opacity-40 border-gray-600'"
                    :style="'background-color:' + color + '33; color:' + color + '; border-color:' + (filters[type] ? color : '#4b5563')">
                <span x-text="type"></span>
            </button>
        </template>
        <button @click="showDead = !showDead"
                class="filter-btn text-xs px-3 py-1 rounded-full border"
                :class="showDead ? 'opacity-100 border-white text-gray-300 bg-gray-700' : 'opacity-40 border-gray-600 text-gray-500'">
            dead agents
        </button>
    </div>

    <!-- Mobile fallback -->
    <div class="block md:hidden text-center py-20 text-gray-500">
        <p class="text-lg">Open on desktop to explore the relationship graph.</p>
    </div>

    <!-- Graph + Detail Panel -->
    <div class="hidden md:flex relative">
        <!-- Graph canvas -->
        <div id="graph-container" class="bg-gray-950 rounded-lg border border-gray-800"></div>

        <!-- Agent detail panel (right overlay) -->
        <div class="detail-panel absolute top-0 right-0 w-80 h-full bg-gray-800 border-l border-gray-700 rounded-r-lg overflow-y-auto p-4"
             :class="selectedAgent ? '' : 'hidden'">
            <template x-if="selectedAgent">
                <div>
                    <div class="flex justify-between items-start mb-3">
                        <div>
                            <h3 class="text-lg font-bold" x-text="selectedAgent.name"></h3>
                            <p class="text-sm text-gray-400" x-text="selectedAgent.role"></p>
                        </div>
                        <button @click="selectedAgent = null" class="text-gray-500 hover:text-gray-300">&times;</button>
                    </div>
                    <div class="space-y-2 mb-4">
                        <div class="flex justify-between text-xs">
                            <span class="text-gray-500">Faction</span>
                            <span x-text="selectedAgent.faction || 'None'" class="text-indigo-400"></span>
                        </div>
                        <div class="flex justify-between text-xs">
                            <span class="text-gray-500">Class</span>
                            <span x-text="selectedAgent.social_class"></span>
                        </div>
                        <div class="text-xs">
                            <span class="text-gray-500">Health</span>
                            <div class="w-full bg-gray-700 rounded-full h-1.5 mt-1">
                                <div class="bg-green-500 h-1.5 rounded-full" :style="'width:' + (selectedAgent.health*100) + '%'"></div>
                            </div>
                        </div>
                        <div class="text-xs">
                            <span class="text-gray-500">Mood</span>
                            <div class="w-full bg-gray-700 rounded-full h-1.5 mt-1">
                                <div class="bg-yellow-500 h-1.5 rounded-full" :style="'width:' + (selectedAgent.mood*100) + '%'"></div>
                            </div>
                        </div>
                        <div class="flex justify-between text-xs">
                            <span class="text-gray-500">Wealth</span>
                            <span x-text="selectedAgent.wealth"></span>
                        </div>
                    </div>

                    <!-- Relationships -->
                    <h4 class="text-sm font-semibold mb-2 text-gray-300">Relationships</h4>
                    <div class="space-y-1 mb-4">
                        <template x-for="rel in selectedAgent.relationships" :key="rel.agent_id">
                            <div class="flex justify-between text-xs py-1 border-b border-gray-700">
                                <span x-text="rel.agent" class="text-gray-200"></span>
                                <span :class="rel.sentiment > 0 ? 'text-green-400' : rel.sentiment < 0 ? 'text-red-400' : 'text-gray-500'"
                                      x-text="rel.type + ' (' + rel.sentiment + ')'"></span>
                            </div>
                        </template>
                    </div>

                    <!-- Recent memories -->
                    <h4 class="text-sm font-semibold mb-2 text-gray-300">Recent memories</h4>
                    <div class="space-y-2">
                        <template x-for="mem in selectedAgent.recent_memories" :key="mem.tick + mem.content.slice(0,20)">
                            <div class="text-xs bg-gray-900 rounded p-2">
                                <span class="text-gray-500">#<span x-text="mem.tick"></span></span>
                                <span class="text-gray-400 ml-1" x-text="'(' + mem.source_type + ')'"></span>
                                <p class="text-gray-300 mt-1" x-text="mem.content"></p>
                            </div>
                        </template>
                        <p x-show="!selectedAgent.recent_memories || selectedAgent.recent_memories.length === 0"
                           class="text-xs text-gray-500">No recent memories.</p>
                    </div>
                </div>
            </template>
        </div>

        <!-- Government badge -->
        <div class="absolute top-3 left-3 bg-gray-800/90 border border-gray-700 rounded-lg px-3 py-2 text-xs">
            <span class="text-gray-500">Government:</span>
            <span class="text-indigo-400 font-medium" x-text="governmentInfo.type"></span>
            <span class="text-gray-600 ml-1" x-text="'(' + governmentInfo.stability + ')'"></span>
        </div>

        <!-- Legend -->
        <div class="absolute bottom-3 left-3 bg-gray-800/90 border border-gray-700 rounded-lg px-3 py-2 text-[10px] space-y-1">
            <div><span style="color:#eab308">&#9679;</span> Head of state</div>
            <div><span style="color:#ffffff">&#9675;</span> Faction leader</div>
            <div><span style="color:#eab308">- - -</span> Chain of command</div>
        </div>
    </div>
</div>

<script>
function graphPage() {
    return {
        renderer: null,
        graph: null,
        selectedAgent: null,
        governmentInfo: { type: 'Loading...', stability: '...' },
        showDead: false,
        edgeTypes: {
            friendship: '#22c55e',
            rivalry: '#ef4444',
            family: '#3b82f6',
            romantic: '#ec4899',
            professional: '#a855f7',
            distrust: '#f97316',
        },
        filters: {
            friendship: true, rivalry: true, family: true,
            romantic: true, professional: true, distrust: true,
        },
        graphData: null,

        init() {
            this.loadGraph();
        },

        async loadGraph() {
            const resp = await fetch('{% url "dashboard:graph-data" sim_id=simulation.id %}');
            this.graphData = await resp.json();
            this.governmentInfo = this.graphData.government;
            this.renderGraph();
        },

        renderGraph() {
            if (this.renderer) { this.renderer.kill(); }
            const container = document.getElementById('graph-container');
            if (!container) return;

            const Graph = graphology;
            this.graph = new Graph();
            const data = this.graphData;

            // Add nodes
            data.nodes.forEach(n => {
                if (!n.is_alive && !this.showDead) return;
                const size = 8 + n.charisma * 16;
                this.graph.addNode(n.id, {
                    label: n.label,
                    x: Math.random() * 100,
                    y: Math.random() * 100,
                    size: size,
                    color: n.faction_color,
                    borderColor: n.is_head_of_state ? '#eab308' : (n.is_leader ? '#ffffff' : null),
                    type: (n.is_head_of_state || n.is_leader) ? 'bordered' : 'circle',
                    opacity: n.is_alive ? 1.0 : 0.3,
                    agentData: n,
                });
            });

            // Add edges
            data.edges.forEach((e, i) => {
                if (!this.filters[e.type]) return;
                if (!this.graph.hasNode(e.source) || !this.graph.hasNode(e.target)) return;
                const isTension = e.sentiment < -0.5 && e.strength > 0.5;
                this.graph.addEdge(e.source, e.target, {
                    color: this.edgeTypes[e.type] || '#6b7280',
                    size: 1 + e.strength * 4,
                    opacity: 0.2 + Math.abs(e.sentiment) * 0.8,
                    type: isTension ? 'tension' : 'line',
                });
            });

            // Add power flow lines
            (data.power_flow || []).forEach((pf, i) => {
                if (!this.graph.hasNode(pf.source) || !this.graph.hasNode(pf.target)) return;
                this.graph.addEdge(pf.source, pf.target, {
                    color: '#eab308',
                    size: 1,
                    opacity: 0.3,
                    type: 'dashed',
                });
            });

            // Layout
            const fa2 = graphologyLayoutForceAtlas2;
            fa2.assign(this.graph, { iterations: 100, settings: { gravity: 1, scalingRatio: 10 } });

            // Render
            this.renderer = new Sigma(this.graph, container, {
                renderEdgeLabels: false,
                defaultNodeColor: '#6b7280',
                labelColor: { color: '#e5e7eb' },
                labelFont: 'Inter, system-ui, sans-serif',
                labelSize: 12,
                nodeReducer: (node, data) => {
                    const res = { ...data };
                    if (this._hoveredNode && this._hoveredNode !== node) {
                        if (!this.graph.hasEdge(this._hoveredNode, node) && !this.graph.hasEdge(node, this._hoveredNode)) {
                            res.color = '#2a2a3a';
                            res.label = '';
                        }
                    }
                    return res;
                },
                edgeReducer: (edge, data) => {
                    const res = { ...data };
                    if (this._hoveredNode) {
                        const [src, tgt] = this.graph.extremities(edge);
                        if (src !== this._hoveredNode && tgt !== this._hoveredNode) {
                            res.color = '#1a1a2a';
                        }
                    }
                    return res;
                },
            });

            // Hover
            this._hoveredNode = null;
            this.renderer.on('enterNode', ({ node }) => {
                this._hoveredNode = node;
                this.renderer.refresh();
            });
            this.renderer.on('leaveNode', () => {
                this._hoveredNode = null;
                this.renderer.refresh();
            });

            // Click
            this.renderer.on('clickNode', async ({ node }) => {
                const resp = await fetch(`/simulations/{{ simulation.id }}/graph/agent/${node}/`);
                this.selectedAgent = await resp.json();
            });
        },

        toggleFilter(type) {
            this.filters[type] = !this.filters[type];
            this.renderGraph();
        },

        async refreshData() {
            await this.loadGraph();
        },
    };
}
</script>
{% endblock %}
```

- [ ] **Step 3: Run all tests**

Run: `docker compose -f docker-compose.local.yml exec -T web pytest epocha/apps/dashboard/ -v`
Expected: All pass.

- [ ] **Step 4: Commit**

```
feat(dashboard): add social relationship graph page with Sigma.js

CHANGE: Full-viewport graph page at /simulations/<id>/graph/ rendering
agents as nodes (sized by charisma, colored by faction) and relationships
as edges (colored by type, weighted by strength). Features: ForceAtlas2
layout, hover-to-focus, click-for-details with memories, tension pulse
on high-conflict edges, power flow dashed lines, filter toggles, and
government badge. Mobile shows fallback message.
```

---

### Task 4: Add "Relationships" button to simulation detail page

**Files:**
- Modify: `epocha/apps/dashboard/templates/dashboard/simulation_detail.html`

- [ ] **Step 1: Add the button**

In `simulation_detail.html`, find the header buttons section (around line 37):

```html
            <a href="{% url 'dashboard:simulation-report' sim_id=simulation.id %}" class="bg-indigo-600 hover:bg-indigo-500 text-white px-4 py-2 rounded font-medium">{{ ui.report }}</a>
```

Add AFTER this line:

```html
            <a href="{% url 'dashboard:graph' sim_id=simulation.id %}" class="bg-purple-600 hover:bg-purple-500 text-white px-4 py-2 rounded font-medium">Relationships</a>
```

- [ ] **Step 2: Run all tests**

Run: `docker compose -f docker-compose.local.yml exec -T web pytest -q`
Expected: All pass.

- [ ] **Step 3: Commit**

```
feat(dashboard): add Relationships button to simulation detail page

CHANGE: Add a purple "Relationships" button in the simulation header
next to Play/Pause/Report, linking to the full-viewport graph page.
```

---

### Task 5: Update engine docstring

**Files:**
- Modify: `epocha/apps/simulation/engine.py:1-19`

- [ ] **Step 1: Update docstring**

No change needed to the engine docstring -- the graph is a read-only visualization that doesn't affect the tick engine. This task is a no-op.

Instead, verify the full test suite passes:

Run: `docker compose -f docker-compose.local.yml exec -T web pytest -q`
Expected: All pass.

- [ ] **Step 2: Push**

```bash
git push origin develop
```

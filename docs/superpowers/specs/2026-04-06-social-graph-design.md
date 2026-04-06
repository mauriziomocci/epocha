# Social Relationship Graph -- Design Spec

## Goal

Add a dedicated full-viewport page to the dashboard that visualizes agent relationships, factions, and government structure as an interactive graph using Sigma.js. The graph provides at-a-glance understanding of the social and political fabric of the simulation.

## Architecture

A new Django view serving a template with Sigma.js (CDN). A JSON data endpoint provides nodes (agents) and edges (relationships) with faction and government metadata. The graph page reuses the simulation header and status bar for context continuity. No build step, no React -- same stack as the existing dashboard (Django templates + Alpine.js + Tailwind CDN).

## Page Location and Navigation

**URL:** `/dashboard/simulation/<id>/graph/`

**Navigation:** A "Relationships" button added to the simulation detail page header, next to Play/Pause/Report. Styled consistently with the existing buttons (indigo background, white text). The graph page has a "Back to simulation" link in the header.

**UX rationale:** The graph serves analysis and reflection, not real-time monitoring. Users navigate to it when they want to understand social structure, then return to the main dashboard. This separation matches the cognitive mode difference -- monitoring vs. analysis. Source: UX analysis recommending dedicated analytical views rather than cramped inline panels.

## Data Endpoint

**URL:** `/dashboard/simulation/<id>/graph/data/` (JSON, login required)

**Response format:**

```json
{
  "nodes": [
    {
      "id": 1,
      "label": "Marco",
      "role": "blacksmith",
      "faction": "The Guild",
      "faction_color": "#6366f1",
      "is_leader": true,
      "is_head_of_state": false,
      "charisma": 0.8,
      "mood": 0.6,
      "social_class": "middle",
      "is_alive": true
    }
  ],
  "edges": [
    {
      "source": 1,
      "target": 2,
      "type": "friendship",
      "strength": 0.7,
      "sentiment": 0.5
    }
  ],
  "government": {
    "type": "Democracy",
    "head_of_state_id": 3,
    "stability": 0.6
  }
}
```

**Data sources:**
- Nodes: `Agent.objects.filter(simulation=sim).select_related("group")` + `Government.objects.get(simulation=sim)` for head_of_state identification
- Edges: `Relationship.objects.filter(agent_from__simulation=sim).select_related("agent_from", "agent_to")`
- Faction color: deterministic hash of faction name to hex color (consistent across refreshes)

## Node Rendering

| Property | Visual mapping |
|----------|---------------|
| Faction membership | Fill color (hashed from faction name). No faction = gray (#6b7280) |
| Head of state | Gold border (#eab308), 3px |
| Faction leader | White border (#ffffff), 2px |
| Charisma | Node size (min 8px, max 24px, linear scale on charisma 0-1) |
| Dead agent | Opacity 0.3 |
| Alive agent | Opacity 1.0 |

## Edge Rendering

| Relationship type | Color |
|-------------------|-------|
| friendship | #22c55e (green) |
| rivalry | #ef4444 (red) |
| family | #3b82f6 (blue) |
| romantic | #ec4899 (pink) |
| professional | #a855f7 (purple) |
| distrust | #f97316 (orange) |

| Property | Visual mapping |
|----------|---------------|
| Strength | Edge thickness (min 1px, max 5px, linear on strength 0-1) |
| Sentiment | Edge opacity (0.2 for neutral sentiment near 0, 1.0 for extreme sentiment near +/-1) |

## Interactivity

**Click node:** Opens a detail panel (Alpine.js overlay, right side, 320px wide) showing:
- Agent name, role, faction, social class
- Health, mood, wealth (with visual bars like the agent list)
- List of relationships with sentiment indicators
- "Chat with agent" link (navigates to main dashboard with chat open)

**Hover node:** Sigma.js "reducers" dim all nodes/edges except the hovered node and its direct connections. Provides immediate focus on one agent's network.

**Zoom/Pan:** Native Sigma.js controls (scroll to zoom, drag to pan).

**Filters toolbar** (top of graph area):
- Toggle buttons for each relationship type (friendship, rivalry, etc.). All on by default. Click to hide/show edges of that type.
- Toggle "Show dead agents" (off by default)
- "Refresh data" button (re-fetches the JSON endpoint)

## Graph Layout

ForceAtlas2, the force-directed layout algorithm included with Sigma.js (via graphology-layout-forceatlas2). Agents in the same faction cluster naturally because they share more relationships. The layout runs for a fixed number of iterations on page load (not continuously) to avoid CPU drain.

**Libraries (all CDN):**
- `sigma` -- graph rendering (WebGL)
- `graphology` -- graph data structure
- `graphology-layout-forceatlas2` -- layout algorithm

## Template Structure

```
simulation_graph.html (extends base.html)
  - Same header as simulation_detail (reused via include or copy)
  - Status bar (same 5 metrics, reused)
  - Filters toolbar
  - Sigma.js canvas container (full remaining viewport)
  - Agent detail overlay panel (Alpine.js, hidden by default)
  - Mobile fallback message (hidden above 768px)
```

## Data Refresh

No automatic polling. The graph is a snapshot for analysis. A "Refresh" button re-fetches data and re-runs the layout. If the simulation is running, each visit shows the latest state.

## Mobile

Below 768px: hide the graph canvas, show a centered message "Open on desktop to explore the relationship graph." The graph is not functional on small screens with 20+ nodes.

## Files

**New files:**

| File | Responsibility |
|------|---------------|
| `epocha/apps/dashboard/templates/dashboard/simulation_graph.html` | Graph page template with Sigma.js |

**Modified files:**

| File | Change |
|------|--------|
| `epocha/apps/dashboard/views.py` | Add graph_view and graph_data_view functions |
| `epocha/apps/dashboard/urls.py` | Add routes for graph page and data endpoint |
| `epocha/apps/dashboard/templates/dashboard/simulation_detail.html` | Add "Relationships" button in header |

## What This Does NOT Cover

- Editing relationships from the graph (read-only visualization)
- Historical timeline / graph playback over ticks
- Export graph as image or data
- Alternative layout algorithms (ForceAtlas2 only)
- Multiple simultaneous graphs or comparison views

## Performance

With 20-50 agents and ~100 relationships, Sigma.js handles this trivially (it's designed for thousands of nodes). ForceAtlas2 layout with 50 nodes completes in under 100ms. No performance concerns at MVP scale.

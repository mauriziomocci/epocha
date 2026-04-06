# PostGIS + GeoDjango Setup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace plain float coordinates with PostGIS geometry fields, enabling spatial queries for movement, proximity, epidemic spread, and the 2D map.

**Architecture:** Infrastructure-first: Docker image swap + Dockerfile deps + settings change, then model migrations (Zone PolygonField + Agent PointField), then generator update, then test fixes, then verify full stack.

**Tech Stack:** PostGIS/PostgreSQL, GeoDjango (django.contrib.gis), GDAL/GEOS/PROJ

**Spec:** `docs/superpowers/specs/2026-04-06-postgis-geodjango-design.md`

---

## File Structure

| File | Change | New/Modify |
|------|--------|------------|
| `docker-compose.local.yml` | DB image: postgis | Modify |
| `docker-compose.production.yml` | DB image: postgis | Modify |
| `compose/django/Dockerfile` | Add GDAL/GEOS/PROJ | Modify |
| `.envs/.local/.django` | postgis:// scheme | Modify |
| `config/settings/base.py` | django.contrib.gis | Modify |
| `epocha/apps/world/models.py` | Zone: PolygonField + PointField | Modify |
| `epocha/apps/agents/models.py` | Agent: PointField + FK Zone | Modify |
| `epocha/apps/agents/relationships.py` | Fix proximity function | Modify |
| `epocha/apps/world/generator.py` | Generate geometry | Modify |
| `epocha/apps/agents/tests/test_relationships.py` | Fix position references | Modify |
| Various test files | Remove position_x/y references | Modify |

---

### Task 1: Docker + Django settings for PostGIS

Infrastructure changes: DB image, Dockerfile deps, DATABASE_URL scheme, Django settings.

**Files:**
- Modify: `docker-compose.local.yml`
- Modify: `docker-compose.production.yml`
- Modify: `compose/django/Dockerfile`
- Modify: `.envs/.local/.django`
- Modify: `config/settings/base.py`

- [ ] **Step 1: Change DB image in docker-compose.local.yml**

Find line `image: postgres:16-alpine` and replace with:
```yaml
    image: postgis/postgis:16-3.4-alpine
```

- [ ] **Step 2: Change DB image in docker-compose.production.yml**

Find line `image: postgres:16-alpine` (around line 33) and replace with:
```yaml
    image: postgis/postgis:16-3.4-alpine
```

- [ ] **Step 3: Add spatial libraries to Dockerfile**

In `compose/django/Dockerfile`, change the `apt-get install` line from:
```dockerfile
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*
```
to:
```dockerfile
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    gdal-bin \
    libgdal-dev \
    libgeos-dev \
    libproj-dev \
    && rm -rf /var/lib/apt/lists/*
```

- [ ] **Step 4: Change DATABASE_URL scheme**

In `.envs/.local/.django`, change:
```
DATABASE_URL=postgres://epocha:epocha@db:5432/epocha
```
to:
```
DATABASE_URL=postgis://epocha:epocha@db:5432/epocha
```

- [ ] **Step 5: Add django.contrib.gis to INSTALLED_APPS**

In `config/settings/base.py`, find the `DJANGO_APPS` list and add `django.contrib.gis` after `django.contrib.contenttypes`:

```python
DJANGO_APPS = [
    "daphne",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.gis",
    "django.contrib.sessions",
    # ... rest unchanged
]
```

- [ ] **Step 6: Rebuild and verify Docker starts**

```bash
docker compose -f docker-compose.local.yml down -v
docker compose -f docker-compose.local.yml up --build -d
```

Wait for containers to start, then verify:
```bash
docker compose -f docker-compose.local.yml exec -T web python -c "from django.contrib.gis.db.backends.postgis.base import DatabaseWrapper; print('PostGIS backend OK')"
docker compose -f docker-compose.local.yml exec -T db psql -U epocha -d epocha -c "SELECT PostGIS_Version();"
```

Expected: PostGIS version string returned (e.g., `3.4 USE_GEOS=1 USE_PROJ=1 USE_STATS=1`).

- [ ] **Step 7: Commit**

```
feat(infra): switch to PostGIS database and add GeoDjango support

CHANGE: Replace postgres:16-alpine with postgis/postgis:16-3.4-alpine
in both Docker Compose files. Add GDAL/GEOS/PROJ to the Django
Dockerfile. Change DATABASE_URL scheme to postgis://. Add
django.contrib.gis to INSTALLED_APPS. This enables spatial queries
for all subsequent geographic features.
```

---

### Task 2: Zone model -- PolygonField + PointField

Replace position_x/y/width/height with PostGIS geometry fields.

**Files:**
- Modify: `epocha/apps/world/models.py`
- Migration: `epocha/apps/world/migrations/`

- [ ] **Step 1: Update Zone model**

In `epocha/apps/world/models.py`, add the import at the top:
```python
from django.contrib.gis.db import models as gis_models
```

Replace the Zone model fields. Remove `position_x`, `position_y`, `width`, `height` and add `boundary` and `center`:

```python
class Zone(models.Model):
    """Geographic zone of the world."""

    class ZoneType(models.TextChoices):
        URBAN = "urban", "Urban"
        RURAL = "rural", "Rural"
        WILDERNESS = "wilderness", "Wilderness"
        COMMERCIAL = "commercial", "Commercial"
        INDUSTRIAL = "industrial", "Industrial"

    world = models.ForeignKey(World, on_delete=models.CASCADE, related_name="zones")
    name = models.CharField(max_length=255)
    zone_type = models.CharField(max_length=20, choices=ZoneType.choices)
    boundary = gis_models.PolygonField(
        null=True, blank=True, srid=4326,
        help_text="Geographic boundary of the zone (WGS84)",
    )
    center = gis_models.PointField(
        null=True, blank=True, srid=4326,
        help_text="Center point for quick distance calculations",
    )
    resources = models.JSONField(default=dict, help_text="Resources available in the zone")
    population_capacity = models.PositiveIntegerField(default=100)

    def __str__(self):
        return f"{self.name} ({self.zone_type})"
```

- [ ] **Step 2: Generate and apply migration**

```bash
docker compose -f docker-compose.local.yml exec -T web python manage.py makemigrations world --name zone_postgis_geometry
docker compose -f docker-compose.local.yml exec -T web python manage.py migrate world
```

- [ ] **Step 3: Commit**

```
feat(world): replace Zone float coordinates with PostGIS geometry

CHANGE: Remove position_x, position_y, width, height from Zone. Add
boundary (PolygonField) for geographic boundaries and center (PointField)
for quick distance calculations. Both use SRID 4326 (WGS84).
```

---

### Task 3: Agent model -- PointField + FK Zone

Replace position_x/y with PointField and add FK to Zone.

**Files:**
- Modify: `epocha/apps/agents/models.py`
- Migration: `epocha/apps/agents/migrations/`

- [ ] **Step 1: Update Agent model**

In `epocha/apps/agents/models.py`, add the import:
```python
from django.contrib.gis.db import models as gis_models
```

In the Agent class, replace `position_x` and `position_y` (around lines 61-62) with:

```python
    # Position and status
    location = gis_models.PointField(
        null=True, blank=True, srid=4326,
        help_text="Current geographic position (WGS84)",
    )
    zone = models.ForeignKey(
        "world.Zone", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="agents_in_zone",
        help_text="Current zone (denormalized for performance)",
    )
    is_alive = models.BooleanField(default=True)
```

Remove the old lines:
```python
    position_x = models.FloatField(default=0.0)  # REMOVE
    position_y = models.FloatField(default=0.0)  # REMOVE
```

- [ ] **Step 2: Update relationships.py proximity function**

In `epocha/apps/agents/relationships.py`, find `find_potential_relationships` (around line 50). It currently uses Euclidean distance on position_x/y. Replace with PostGIS distance:

```python
def find_potential_relationships(agent: Agent, proximity_threshold: float = 20) -> list[Agent]:
    """Find nearby agents who could form relationships.

    Uses PostGIS spatial distance for agents with locations, falls back
    to returning all simulation agents if no location is set.
    """
    if agent.location is None:
        # No spatial data -- return all agents in simulation as candidates
        return list(
            Agent.objects.filter(simulation=agent.simulation, is_alive=True)
            .exclude(id=agent.id)
        )

    from django.contrib.gis.measure import D
    return list(
        Agent.objects.filter(
            simulation=agent.simulation,
            is_alive=True,
            location__distance_lte=(agent.location, D(m=proximity_threshold)),
        ).exclude(id=agent.id)
    )
```

- [ ] **Step 3: Generate and apply migration**

```bash
docker compose -f docker-compose.local.yml exec -T web python manage.py makemigrations agents --name agent_postgis_location
docker compose -f docker-compose.local.yml exec -T web python manage.py migrate agents
```

- [ ] **Step 4: Commit**

```
feat(agents): replace Agent float coordinates with PostGIS PointField

CHANGE: Remove position_x, position_y from Agent. Add location
(PointField) for geographic position and zone (FK to Zone) for
efficient zone membership queries. Update proximity function in
relationships.py to use PostGIS spatial distance.
```

---

### Task 4: World generator + test fixes

Update the generator to create geometry and fix all tests referencing old position fields.

**Files:**
- Modify: `epocha/apps/world/generator.py`
- Modify: `epocha/apps/agents/tests/test_relationships.py`
- Modify: various other test files with position_x/y references

- [ ] **Step 1: Update world generator**

In `epocha/apps/world/generator.py`, update the Zone creation (around line 121-128):

Add import at top:
```python
from django.contrib.gis.geos import Point, Polygon
```

Replace the Zone.objects.create call:
```python
        # Generate zone geometry: rectangular boundary on an abstract grid
        zone_idx = idx  # 0-based index
        col = zone_idx % 3
        row = zone_idx // 3
        x_offset = col * 120
        y_offset = row * 120
        boundary = Polygon.from_bbox((x_offset, y_offset, x_offset + 100, y_offset + 100))
        center = Point(x_offset + 50, y_offset + 50)

        Zone.objects.create(
            world=world,
            name=zone_data["name"],
            zone_type=zone_data.get("type", "urban"),
            boundary=boundary,
            center=center,
            resources=zone_data.get("resources", {}),
        )
```

Update the Agent creation (around line 135-143). Replace `position_x`/`position_y` with `location`:

```python
        import random
        # Place agent in a random position within the first zone
        zones = list(Zone.objects.filter(world=world))
        agent_zone = zones[idx % len(zones)] if zones else None
        if agent_zone and agent_zone.center:
            # Random offset within the zone
            cx, cy = agent_zone.center.x, agent_zone.center.y
            loc = Point(cx + random.uniform(-40, 40), cy + random.uniform(-40, 40))
        else:
            loc = None

        agent = Agent.objects.create(
            simulation=simulation,
            name=agent_data["name"],
            role=agent_data.get("role", ""),
            personality=personality,
            location=loc,
            zone=agent_zone,
        )
```

Remove the old `position_x`/`position_y` assignments.

- [ ] **Step 2: Fix test_relationships.py**

In `epocha/apps/agents/tests/test_relationships.py`, replace `position_x=...` / `position_y=...` with `location=Point(...)`:

Add import:
```python
from django.contrib.gis.geos import Point
```

Line 27-29: replace:
```python
        a1 = Agent.objects.create(simulation=simulation, name="Marco", location=Point(10, 10), personality={})
        a2 = Agent.objects.create(simulation=simulation, name="Elena", location=Point(12, 10), personality={})
        Agent.objects.create(simulation=simulation, name="Luca", location=Point(90, 90), personality={})
```

Line 37-38: replace similarly.

- [ ] **Step 3: Search and fix all other test files**

Search for any remaining `position_x` or `position_y` in test files and source code. These files may have references:
- `epocha/apps/agents/tests/test_*.py`
- `epocha/apps/simulation/tests/test_*.py`
- `epocha/apps/world/tests/test_*.py`

For tests that create Agents without needing a position, simply remove the `position_x`/`position_y` kwargs (the new `location` field is nullable).

For tests that create Zones, remove `position_x`/`position_y`/`width`/`height` kwargs (the new `boundary` and `center` are nullable).

- [ ] **Step 4: Run full test suite**

```bash
docker compose -f docker-compose.local.yml exec -T web pytest --reuse-db -q
```

Expected: All tests pass. If any fail due to remaining position_x/y references, fix them.

- [ ] **Step 5: Commit**

```
feat(world): update generator and tests for PostGIS geometry

CHANGE: World generator now creates zones with PostGIS polygon
boundaries and places agents with PointField locations inside zones.
Updated all tests to use Point() instead of position_x/position_y.
```

---

### Task 5: Full verification + push

- [ ] **Step 1: Rebuild from clean state**

```bash
docker compose -f docker-compose.local.yml down -v
docker compose -f docker-compose.local.yml up --build -d
sleep 10
docker compose -f docker-compose.local.yml exec -T web python manage.py migrate
```

- [ ] **Step 2: Verify PostGIS works**

```bash
docker compose -f docker-compose.local.yml exec -T db psql -U epocha -d epocha -c "SELECT PostGIS_Version();"
```

- [ ] **Step 3: Run full test suite from clean DB**

```bash
docker compose -f docker-compose.local.yml exec -T web pytest -q
```

Expected: All tests pass.

- [ ] **Step 4: Verify spatial queries work**

```bash
docker compose -f docker-compose.local.yml exec -T web python manage.py shell -c "
from django.contrib.gis.geos import Point, Polygon
from epocha.apps.world.models import Zone
from epocha.apps.agents.models import Agent
from epocha.apps.simulation.models import Simulation
from epocha.apps.users.models import User
from epocha.apps.world.models import World

# Quick spatial query verification
u = User.objects.create_user(email='test@test.com', username='test', password='test123')
sim = Simulation.objects.create(name='GeoTest', seed=42, owner=u)
world = World.objects.create(simulation=sim)
zone = Zone.objects.create(world=world, name='TestZone', zone_type='urban',
    boundary=Polygon.from_bbox((0, 0, 100, 100)), center=Point(50, 50))
agent = Agent.objects.create(simulation=sim, name='Marco', personality={},
    location=Point(50, 50), zone=zone)

# Spatial query: agent within zone
from django.contrib.gis.measure import D
nearby = Agent.objects.filter(location__distance_lte=(Point(50, 50), D(m=10)))
print(f'Nearby agents: {nearby.count()}')
assert nearby.count() == 1
print('PostGIS spatial queries WORKING')
"
```

- [ ] **Step 5: Push**

```bash
git push origin develop
```

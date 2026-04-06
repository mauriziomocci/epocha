# PostGIS + GeoDjango Setup -- Design Spec

## Goal

Replace plain float coordinates with PostGIS geometry fields across the codebase, enabling spatial queries (proximity, containment, adjacency) that are the foundation for realistic movement, spatial information propagation, epidemic spread, and the 2D map visualization.

## Architecture

Infrastructure change: swap the PostgreSQL Docker image for PostGIS, configure GeoDjango in Django settings, convert Zone boundaries from rectangles (4 floats) to PostGIS polygons, and convert Agent positions from coordinate pairs to PostGIS points. Add a Zone FK on Agent for efficient zone membership queries without spatial computation on every read.

## Docker Infrastructure

### Database image

Change `postgres:16-alpine` to `postgis/postgis:16-3.4-alpine` in both `docker-compose.local.yml` and `docker-compose.production.yml`. This image includes the PostGIS extension pre-installed.

### Django Dockerfile

Add system dependencies for GeoDjango. The Dockerfile uses `python:3.12-slim` (Debian-based), so the packages are:

```
gdal-bin libgdal-dev libgeos-dev libproj-dev
```

These provide the GDAL, GEOS, and PROJ libraries that GeoDjango requires for spatial operations. On Alpine-based images the names would be different (`gdal-dev geos-dev proj-dev`).

## Django Settings

In `config/settings/base.py`:

1. Add `django.contrib.gis` to `INSTALLED_APPS`
2. Change database engine from `django.db.backends.postgresql` to `django.contrib.gis.db.backends.postgis`

The engine change is done via the `DATABASE_URL` environment variable. Update `.envs/.local/.postgres` (and production equivalent) to use the `postgis://` scheme instead of `postgres://`, or override the engine directly in settings.

Note: `django-environ` recognizes the `postgis://` scheme and maps it to the correct engine automatically.

## Model Changes

### Zone -- from rectangle to polygon

**Remove:** `position_x`, `position_y`, `width`, `height` (4 FloatFields)

**Add:**

```python
from django.contrib.gis.db import models as gis_models

class Zone(models.Model):
    # ... existing fields ...
    boundary = gis_models.PolygonField(
        null=True, blank=True, srid=4326,
        help_text="Geographic boundary of the zone (WGS84)",
    )
    center = gis_models.PointField(
        null=True, blank=True, srid=4326,
        help_text="Center point for quick distance calculations",
    )
```

SRID 4326 is WGS84, the standard GPS coordinate system. For abstract simulations (not based on real maps), coordinates are arbitrary but consistent within the simulation.

The `center` field is redundant with `boundary` (can be computed as centroid) but avoids repeated centroid calculations on common queries like "nearest zone to agent."

### Agent -- from float pair to point

**Remove:** `position_x`, `position_y` (2 FloatFields)

**Add:**

```python
location = gis_models.PointField(
    null=True, blank=True, srid=4326,
    help_text="Current geographic position (WGS84)",
)
zone = models.ForeignKey(
    "world.Zone", null=True, blank=True, on_delete=models.SET_NULL,
    related_name="agents_in_zone",
    help_text="Current zone the agent is in (denormalized for performance)",
)
```

The `zone` FK is denormalized: it could be computed from `ST_Within(agent.location, zone.boundary)` but that spatial query is expensive for routine lookups. The FK is updated whenever the agent moves.

### Spatial Index

PostGIS automatically creates GiST indexes on geometry fields. No manual index creation needed.

## Enabled Spatial Queries

After this setup, these queries become possible:

```python
from django.contrib.gis.measure import D
from django.contrib.gis.geos import Point

# Agents within 500 units of a point
Agent.objects.filter(location__distance_lte=(point, D(m=500)))

# Agents inside a zone
Agent.objects.filter(location__within=zone.boundary)

# Zones that touch/overlap another zone
Zone.objects.filter(boundary__touches=zone.boundary)
Zone.objects.filter(boundary__intersects=zone.boundary)

# Nearest zone to an agent
Zone.objects.filter(center__isnull=False).distance(agent.location).order_by("distance").first()

# Distance between two agents
from django.contrib.gis.db.models.functions import Distance
Agent.objects.annotate(dist=Distance("location", other_agent.location))
```

## Migration Strategy

Since existing simulation data is not preserved (user decision), the migration is straightforward:

1. Remove `position_x`, `position_y`, `width`, `height` from Zone
2. Add `boundary` (PolygonField, nullable) and `center` (PointField, nullable) to Zone
3. Remove `position_x`, `position_y` from Agent
4. Add `location` (PointField, nullable) and `zone` (FK, nullable) to Agent

Existing simulations will have `NULL` geometry fields and need to be recreated.

## World Generator Update

The world generator (`epocha/apps/world/generator.py`) must be updated to:

1. Create zones with actual geometry. For abstract simulations, generate zones as rectangular polygons arranged in a grid or cluster pattern:

```python
from django.contrib.gis.geos import Point, Polygon

# Example: create a zone as a 100x100 rectangle at position (x, y)
boundary = Polygon.from_bbox((x, y, x + 100, y + 100))
center = Point(x + 50, y + 50)
```

2. Place agents inside zones with random positions within the zone boundary:

```python
from django.contrib.gis.geos import Point
import random

# Random point inside a rectangular zone
px = random.uniform(zone_bbox[0], zone_bbox[2])
py = random.uniform(zone_bbox[1], zone_bbox[3])
agent.location = Point(px, py)
agent.zone = zone
```

## Test Updates

Tests that create Agent or Zone objects need to be updated:
- Remove `position_x=...` / `position_y=...` from Agent creation
- Remove `position_x=...` / `position_y=...` / `width=...` / `height=...` from Zone creation
- Optionally add `location=Point(0, 0)` and `zone=zone` where needed

Since geometry fields are nullable, most tests will work with `None` values (no geometry needed for non-spatial tests).

## Files

**Modified files:**

| File | Change |
|------|--------|
| `docker-compose.local.yml` | `postgis/postgis:16-3.4-alpine` |
| `docker-compose.production.yml` | `postgis/postgis:16-3.4-alpine` |
| `compose/django/Dockerfile` | Add `gdal-dev geos-dev proj-dev` |
| `config/settings/base.py` | Add `django.contrib.gis` to INSTALLED_APPS |
| `.envs/.local/.postgres` | Change `postgres://` to `postgis://` in DATABASE_URL |
| `epocha/apps/world/models.py` | Zone: replace 4 floats with PolygonField + PointField |
| `epocha/apps/agents/models.py` | Agent: replace 2 floats with PointField + FK Zone |
| `epocha/apps/world/generator.py` | Create zones with geometry, place agents in zones |
| `epocha/apps/world/migrations/` | New migration for zone geometry changes |
| `epocha/apps/agents/migrations/` | New migration for agent location changes |
| Various test files | Remove old position_x/y references |

## What This Does NOT Cover

- Agent movement system (next step -- agents will move between zones each tick)
- Spatial information flow (info flow will use proximity, not just relationships)
- Spatial epidemic propagation (SIR model will use distance)
- 2D map visualization (Pixi.js -- after movement and models are implemented)
- Real-world geographic data import (for historical simulations with real maps)

## Database Volume

The Docker volume `epocha_postgres_data` must be **recreated** because the PostGIS image requires the PostGIS extension to be created in the database. The simplest approach is to remove the volume and let Docker recreate it:

```bash
docker compose -f docker-compose.local.yml down -v
docker compose -f docker-compose.local.yml up --build -d
```

This destroys all existing data (simulations, users, etc.) which is acceptable per user decision.

## Performance

PostGIS spatial indexes (GiST) handle queries on thousands of points efficiently. At our scale (20-50 agents, 5-10 zones), spatial queries are sub-millisecond. No performance concerns.

# Knowledge Graph Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a scientifically rigorous Knowledge Graph app that extracts ontologically classified entities and relations from user-uploaded documents, caches LLM extractions across simulations, and feeds the world generator with structured context to produce coherent agents.

**Architecture:** A new Django app `epocha.apps.knowledge` owns document ingestion, chunking, embedding, LLM extraction, caching, and materialization. Documents and chunks are deduplicated via content hash and shared across simulations. The expensive LLM extraction step is cached keyed on a composite of documents hash + ontology version + extraction prompt version + LLM model. Each simulation gets its own isolated materialized graph cloned cheaply from the cached extraction. World generation is extended to build its prompt from the graph structure when available.

**Tech Stack:** Django 5.x, pgvector (Postgres extension + Python package), fastembed (ONNX-based BAAI/bge-m3 1024-dim multilingual embeddings), langchain-text-splitters, Celery, DRF, Sigma.js.

**Spec:** `docs/superpowers/specs/2026-04-11-knowledge-graph-design.md`

---

## File Structure

| File | Responsibility | New/Modify |
|------|---------------|------------|
| `compose/postgres/Dockerfile` | Custom Postgres image extending postgis with pgvector | New |
| `docker-compose.local.yml` | Build postgres from custom Dockerfile | Modify |
| `docker-compose.production.yml` | Build postgres from custom Dockerfile | Modify |
| `requirements/base.txt` | Add pgvector, fastembed, langchain-text-splitters | Modify |
| `config/settings/base.py` | New EPOCHA_KG_* settings and knowledge app registration | Modify |
| `epocha/apps/knowledge/__init__.py` | App init | New |
| `epocha/apps/knowledge/apps.py` | Django AppConfig | New |
| `epocha/apps/knowledge/versions.py` | ONTOLOGY_VERSION, EXTRACTION_PROMPT_VERSION, model params | New |
| `epocha/apps/knowledge/ontology.py` | Entity and relation vocabularies with validators | New |
| `epocha/apps/knowledge/normalizer.py` | Canonical name normalization | New |
| `epocha/apps/knowledge/models.py` | All 8 Knowledge* Django models | New |
| `epocha/apps/knowledge/migrations/0001_initial.py` | Initial migration with VectorExtension and cross-app deps | New |
| `epocha/apps/knowledge/embedding.py` | fastembed wrapper with bge-m3 | New |
| `epocha/apps/knowledge/chunking.py` | Recursive text splitter wrapper | New |
| `epocha/apps/knowledge/ingestion.py` | Document parse + normalize + hash + store | New |
| `epocha/apps/knowledge/cache.py` | Cache key builder | New |
| `epocha/apps/knowledge/prompts.py` | Extraction system prompt with ontology and examples | New |
| `epocha/apps/knowledge/extraction.py` | Per-chunk LLM extraction with validation | New |
| `epocha/apps/knowledge/merge.py` | Merge and dedup across chunks | New |
| `epocha/apps/knowledge/materialization.py` | Turn extracted data into per-simulation rows | New |
| `epocha/apps/knowledge/tasks.py` | Celery orchestration task | New |
| `epocha/apps/knowledge/api.py` | DRF views for upload, status, graph JSON | New |
| `epocha/apps/knowledge/serializers.py` | DRF serializers | New |
| `epocha/apps/knowledge/urls.py` | API URL routes | New |
| `epocha/apps/knowledge/views.py` | Dashboard HTML view | New |
| `epocha/apps/knowledge/templates/knowledge/graph.html` | Sigma.js visualization template | New |
| `epocha/apps/knowledge/management/commands/cleanup_extraction_cache.py` | Cache cleanup command | New |
| `epocha/apps/knowledge/tests/` | Test files for each module | New |
| `epocha/apps/knowledge/tests/fixtures/small_french_rev.txt` | Test fixture document | New |
| `epocha/apps/world/generator.py` | Add _generate_from_knowledge_graph function | Modify |
| `config/urls.py` | Register knowledge URLs | Modify |

---

## Tasks summary

1. **Infrastructure setup** — custom Postgres Dockerfile, dependencies, app creation, settings
2. **Versioning and ontology modules** — versions.py, ontology.py, normalizer.py with unit tests
3. **Document models and ingestion** — KnowledgeDocument, KnowledgeDocumentAccess, ingestion service
4. **Chunk model, chunking, embedding** — KnowledgeChunk, chunking.py, embedding.py
5. **ExtractionCache model and cache key** — cache model, key builder
6. **Extraction prompt and per-chunk extraction** — prompts.py, extraction.py with mocked LLM tests
7. **Merge and deduplication** — merge.py with cluster dedup and merge rules
8. **Graph models and materialization** — KnowledgeGraph, KnowledgeNode, KnowledgeRelation, citation models, materialization.py
9. **Celery orchestration task** — extract_and_generate task with progress broadcast
10. **World generator integration** — _generate_from_knowledge_graph in world/generator.py
11. **Upload and status API endpoints** — express-with-documents and extraction-status endpoints
12. **Visualization JSON API** — knowledge-graph GET endpoint with DRF ViewSet
13. **Dashboard view and template** — knowledge-graph dashboard page with Sigma.js
14. **Cache cleanup management command** — cleanup_extraction_cache command

Each task is self-contained, has tests, and ends with a commit. Tasks must be completed in order because later tasks depend on models and services from earlier ones.

---

---

### Task 1: Infrastructure setup

**Files:**
- Create: `compose/postgres/Dockerfile`
- Modify: `docker-compose.local.yml`
- Modify: `docker-compose.production.yml`
- Modify: `requirements/base.txt`
- Create: `epocha/apps/knowledge/__init__.py`
- Create: `epocha/apps/knowledge/apps.py`
- Modify: `config/settings/base.py`

- [ ] **Step 1: Create the custom Postgres Dockerfile**

Create `compose/postgres/Dockerfile`:

```dockerfile
FROM postgis/postgis:16-3.4

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       postgresql-16-pgvector \
    && rm -rf /var/lib/apt/lists/*
```

- [ ] **Step 2: Update docker-compose.local.yml**

Replace the postgres service `image: postgis/postgis:16-3.4-alpine` line with a build section. Open `docker-compose.local.yml`, find the postgres service block, and replace:

```yaml
    image: postgis/postgis:16-3.4-alpine
```

with:

```yaml
    build:
      context: .
      dockerfile: compose/postgres/Dockerfile
```

- [ ] **Step 3: Update docker-compose.production.yml**

Apply the same change in `docker-compose.production.yml`: find the postgres service image line and replace with the same build block.

- [ ] **Step 4: Add Python dependencies**

Open `requirements/base.txt` and append at the end (after the existing sections):

```
# Knowledge Graph
pgvector>=0.3.6
fastembed>=0.3.6
langchain-text-splitters>=0.2.2
```

- [ ] **Step 5: Create the knowledge app skeleton**

Run:

```bash
mkdir -p epocha/apps/knowledge/migrations epocha/apps/knowledge/tests epocha/apps/knowledge/tests/fixtures epocha/apps/knowledge/management/commands epocha/apps/knowledge/templates/knowledge
touch epocha/apps/knowledge/__init__.py
touch epocha/apps/knowledge/migrations/__init__.py
touch epocha/apps/knowledge/tests/__init__.py
touch epocha/apps/knowledge/management/__init__.py
touch epocha/apps/knowledge/management/commands/__init__.py
```

Create `epocha/apps/knowledge/apps.py`:

```python
"""Knowledge Graph Django app."""
from django.apps import AppConfig


class KnowledgeConfig(AppConfig):
    """App configuration for the Knowledge Graph module."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "epocha.apps.knowledge"
    label = "knowledge"
    verbose_name = "Knowledge Graph"
```

- [ ] **Step 6: Register the app and add settings**

In `config/settings/base.py`, find the `LOCAL_APPS` list and add `"epocha.apps.knowledge"`. Then add a new section at the end of the file (before any final guard):

```python
# Knowledge Graph feature configuration
EPOCHA_KG_ENABLED = env.bool("EPOCHA_KG_ENABLED", default=True)
EPOCHA_KG_MAX_CHUNKS_PER_DOC = env.int("EPOCHA_KG_MAX_CHUNKS_PER_DOC", default=50)
EPOCHA_KG_MAX_DOCUMENT_CHARS = env.int("EPOCHA_KG_MAX_DOCUMENT_CHARS", default=500000)
EPOCHA_KG_EMBEDDING_BATCH_SIZE = env.int("EPOCHA_KG_EMBEDDING_BATCH_SIZE", default=10)
```

- [ ] **Step 7: Rebuild the Postgres image and verify it starts**

Run:

```bash
docker compose -f docker-compose.local.yml build postgres
docker compose -f docker-compose.local.yml up -d postgres
docker compose -f docker-compose.local.yml exec -T postgres psql -U epocha -d epocha -c "CREATE EXTENSION IF NOT EXISTS vector;"
docker compose -f docker-compose.local.yml exec -T postgres psql -U epocha -d epocha -c "SELECT extname FROM pg_extension;"
```

Expected output: the extensions list includes `postgis` and `vector`.

- [ ] **Step 8: Install Python dependencies and verify the app loads**

Run:

```bash
docker compose -f docker-compose.local.yml build web
docker compose -f docker-compose.local.yml run --rm web python -c "from epocha.apps.knowledge.apps import KnowledgeConfig; print(KnowledgeConfig.name)"
```

Expected output: `epocha.apps.knowledge`

- [ ] **Step 9: Run existing test suite to confirm no regression**

Run:

```bash
docker compose -f docker-compose.local.yml exec -T web pytest -q
```

Expected: all existing tests pass.

- [ ] **Step 10: Commit**

```
chore(knowledge): scaffold knowledge graph app with pgvector support

CHANGE: Add a custom Postgres image extending postgis with pgvector,
new Python dependencies (pgvector, fastembed, langchain-text-splitters),
empty knowledge app registered in settings, and new EPOCHA_KG_*
configuration keys. No models yet, no business logic yet.
```

---

### Task 2: Versioning, ontology, and normalizer modules

**Files:**
- Create: `epocha/apps/knowledge/versions.py`
- Create: `epocha/apps/knowledge/ontology.py`
- Create: `epocha/apps/knowledge/normalizer.py`
- Create: `epocha/apps/knowledge/tests/test_versions.py`
- Create: `epocha/apps/knowledge/tests/test_ontology.py`
- Create: `epocha/apps/knowledge/tests/test_normalizer.py`

- [ ] **Step 1: Create the versions module**

Create `epocha/apps/knowledge/versions.py`:

```python
"""Versioning constants for the Knowledge Graph extraction pipeline.

Any change to ONTOLOGY_VERSION, EXTRACTION_PROMPT_VERSION, or
EMBEDDING_MODEL invalidates the extraction cache automatically because
these values compose the cache key. Other constants affect behavior but
not cache identity.
"""
from __future__ import annotations

ONTOLOGY_VERSION = "v1"
EXTRACTION_PROMPT_VERSION = "v1"

EMBEDDING_MODEL = "BAAI/bge-m3"
EMBEDDING_DIM = 1024

CHUNK_SIZE_TOKENS = 800
CHUNK_OVERLAP_TOKENS = 150
CHUNK_CHARS_PER_TOKEN = 4

DEDUP_SIMILARITY_THRESHOLD = 0.85
EXTRACTION_TEMPERATURE = 0.1
```

- [ ] **Step 2: Write the failing tests for ontology**

Create `epocha/apps/knowledge/tests/test_ontology.py`:

```python
"""Tests for the ontology validators and vocabularies."""
import pytest

from epocha.apps.knowledge.ontology import (
    ENTITY_TYPES,
    RELATION_TYPES,
    SOURCE_TYPES,
    is_valid_entity_type,
    is_valid_relation_type,
    is_valid_source_type,
)


class TestEntityTypes:
    def test_exactly_ten_entity_types(self):
        assert len(ENTITY_TYPES) == 10

    def test_contains_expected_types(self):
        expected = {
            "person", "group", "place", "institution", "event",
            "concept", "ideology", "object", "norm", "value",
        }
        assert set(ENTITY_TYPES) == expected

    def test_is_valid_accepts_all_known(self):
        for t in ENTITY_TYPES:
            assert is_valid_entity_type(t) is True

    def test_is_valid_rejects_unknown(self):
        assert is_valid_entity_type("unknown") is False
        assert is_valid_entity_type("") is False
        assert is_valid_entity_type("PERSON") is False  # case sensitive


class TestRelationTypes:
    def test_exactly_twenty_relation_types(self):
        assert len(RELATION_TYPES) == 20

    def test_contains_kinship_relations(self):
        assert "married_to" in RELATION_TYPES
        assert "parent_of" in RELATION_TYPES
        assert "sibling_of" in RELATION_TYPES

    def test_no_kin_of_umbrella(self):
        assert "kin_of" not in RELATION_TYPES

    def test_is_valid_accepts_all_known(self):
        for t in RELATION_TYPES:
            assert is_valid_relation_type(t) is True

    def test_is_valid_rejects_unknown(self):
        assert is_valid_relation_type("friend_of") is False
        assert is_valid_relation_type("") is False


class TestSourceTypes:
    def test_exactly_two_source_types(self):
        assert len(SOURCE_TYPES) == 2

    def test_no_llm_knowledge_in_mvp(self):
        assert "llm_knowledge" not in SOURCE_TYPES

    def test_is_valid(self):
        assert is_valid_source_type("document") is True
        assert is_valid_source_type("document_inferred") is True
        assert is_valid_source_type("llm_knowledge") is False
```

- [ ] **Step 3: Run ontology tests to verify they fail**

Run:

```bash
docker compose -f docker-compose.local.yml exec -T web pytest epocha/apps/knowledge/tests/test_ontology.py -v
```

Expected: ImportError / ModuleNotFoundError for `epocha.apps.knowledge.ontology`.

- [ ] **Step 4: Implement the ontology module**

Create `epocha/apps/knowledge/ontology.py`:

```python
"""Ontology definitions for the Knowledge Graph.

The entity type vocabulary follows Searle (1995) for the brute/
institutional distinction, CIDOC-CRM (ISO 21127:2014) for event and
object modeling, and Freeden (1996) for the concept/ideology/value/norm
distinction. The relation vocabulary is a controlled set of 20 types
chosen for operational distinguishability by an LLM.
"""
from __future__ import annotations

# Entity type vocabulary (10 types)
ENTITY_TYPES: tuple[str, ...] = (
    "person",
    "group",
    "place",
    "institution",
    "event",
    "concept",
    "ideology",
    "object",
    "norm",
    "value",
)

# Relation type vocabulary (20 types, grouped by category)
RELATION_TYPES: tuple[str, ...] = (
    # Membership
    "member_of", "founder_of", "leader_of",
    # Spatial
    "located_in", "occurred_in",
    # Temporal
    "occurred_during",
    # Belief
    "believes_in", "opposes", "supports",
    # Social
    "ally_of", "enemy_of", "influences",
    # Kinship
    "married_to", "parent_of", "sibling_of",
    # Causal
    "caused_by", "led_to",
    # Participation
    "participated_in",
    # Production
    "authored", "enacted",
)

# Source type vocabulary (2 types; llm_knowledge excluded from MVP)
SOURCE_TYPES: tuple[str, ...] = (
    "document",
    "document_inferred",
)

# Category mapping for relation colors in visualization
RELATION_CATEGORIES: dict[str, str] = {
    "member_of": "membership",
    "founder_of": "membership",
    "leader_of": "membership",
    "located_in": "spatial",
    "occurred_in": "spatial",
    "occurred_during": "temporal",
    "believes_in": "belief",
    "opposes": "belief",
    "supports": "belief",
    "ally_of": "social",
    "enemy_of": "social",
    "influences": "social",
    "married_to": "kinship",
    "parent_of": "kinship",
    "sibling_of": "kinship",
    "caused_by": "causal",
    "led_to": "causal",
    "participated_in": "participation",
    "authored": "production",
    "enacted": "production",
}


def is_valid_entity_type(value: str) -> bool:
    """Return True if value is a recognized entity type code."""
    return value in ENTITY_TYPES


def is_valid_relation_type(value: str) -> bool:
    """Return True if value is a recognized relation type code."""
    return value in RELATION_TYPES


def is_valid_source_type(value: str) -> bool:
    """Return True if value is a recognized source type code."""
    return value in SOURCE_TYPES
```

- [ ] **Step 5: Run ontology tests to verify they pass**

Run:

```bash
docker compose -f docker-compose.local.yml exec -T web pytest epocha/apps/knowledge/tests/test_ontology.py -v
```

Expected: all PASS.

- [ ] **Step 6: Write the failing tests for the normalizer**

Create `epocha/apps/knowledge/tests/test_normalizer.py`:

```python
"""Tests for canonical name normalization."""
import pytest

from epocha.apps.knowledge.normalizer import (
    normalize_canonical_name,
    name_contained_in_passage,
)


class TestNormalize:
    def test_lowercase(self):
        assert normalize_canonical_name("Robespierre") == "robespierre"

    def test_strip_accents_french(self):
        assert normalize_canonical_name("Déclaration") == "declaration"

    def test_strip_accents_italian(self):
        assert normalize_canonical_name("Libertà") == "liberta"

    def test_strip_accents_german(self):
        assert normalize_canonical_name("Brüder") == "bruder"

    def test_strip_honorific_m(self):
        assert normalize_canonical_name("M. Robespierre") == "robespierre"

    def test_strip_honorific_dr(self):
        assert normalize_canonical_name("Dr. Marat") == "marat"

    def test_strip_honorific_mme(self):
        assert normalize_canonical_name("Mme. Roland") == "roland"

    def test_strip_honorific_citoyen(self):
        assert normalize_canonical_name("Citoyen Robespierre") == "robespierre"
        assert normalize_canonical_name("Citoyenne Roland") == "roland"

    def test_collapse_whitespace(self):
        assert normalize_canonical_name("Louis   XVI") == "louis xvi"

    def test_trim(self):
        assert normalize_canonical_name("  Danton  ") == "danton"

    def test_empty_string(self):
        assert normalize_canonical_name("") == ""

    def test_single_char(self):
        assert normalize_canonical_name("A") == "a"

    def test_all_caps(self):
        assert normalize_canonical_name("VERSAILLES") == "versailles"


class TestNameContained:
    def test_exact_match(self):
        assert name_contained_in_passage(
            "Robespierre", "Robespierre spoke to the assembly."
        ) is True

    def test_accent_insensitive(self):
        assert name_contained_in_passage(
            "Déclaration", "The declaration was read aloud."
        ) is True

    def test_case_insensitive(self):
        assert name_contained_in_passage(
            "ROBESPIERRE", "Robespierre spoke."
        ) is True

    def test_not_present(self):
        assert name_contained_in_passage(
            "Danton", "Robespierre spoke to the assembly."
        ) is False

    def test_partial_match_within_word(self):
        # "Paris" inside "Parisian" should still count as contained
        assert name_contained_in_passage(
            "Paris", "The Parisian crowds gathered."
        ) is True

    def test_empty_passage(self):
        assert name_contained_in_passage("Robespierre", "") is False

    def test_empty_name(self):
        assert name_contained_in_passage("", "some passage") is False
```

- [ ] **Step 7: Run normalizer tests to verify they fail**

Run:

```bash
docker compose -f docker-compose.local.yml exec -T web pytest epocha/apps/knowledge/tests/test_normalizer.py -v
```

Expected: ImportError for `epocha.apps.knowledge.normalizer`.

- [ ] **Step 8: Implement the normalizer module**

Create `epocha/apps/knowledge/normalizer.py`:

```python
"""Canonical name normalization and passage containment checks.

Normalization is used for deduplication (two mentions with minor
orthographic differences collapse to the same canonical form) and for
the mechanical source_type assignment (is the name contained in the
passage?).
"""
from __future__ import annotations

import re
import unicodedata

# Honorific prefixes stripped during normalization. Order matters: longer
# forms must come before shorter ones to avoid partial matches.
_HONORIFICS: tuple[str, ...] = (
    "citoyenne",
    "citoyen",
    "madame",
    "monsieur",
    "mme.",
    "mme",
    "mlle.",
    "mlle",
    "mrs.",
    "mrs",
    "mr.",
    "mr",
    "ms.",
    "ms",
    "dr.",
    "dr",
    "prof.",
    "prof",
    "m.",
)

_WHITESPACE_RE = re.compile(r"\s+")


def _strip_accents(text: str) -> str:
    """Return text with combining marks removed via Unicode NFD decomposition."""
    decomposed = unicodedata.normalize("NFD", text)
    return "".join(c for c in decomposed if not unicodedata.combining(c))


def _strip_honorifics(text: str) -> str:
    """Remove leading honorific tokens (iteratively)."""
    result = text
    changed = True
    while changed:
        changed = False
        for honorific in _HONORIFICS:
            if result.startswith(honorific + " "):
                result = result[len(honorific) + 1:]
                changed = True
                break
            if result == honorific:
                return ""
    return result


def normalize_canonical_name(name: str) -> str:
    """Normalize an entity name into its canonical form.

    Steps: lowercase, strip accents, strip honorific prefixes, collapse
    whitespace, trim. Empty or whitespace-only input returns an empty string.
    """
    if not name:
        return ""
    text = _strip_accents(name).lower().strip()
    text = _WHITESPACE_RE.sub(" ", text)
    text = _strip_honorifics(text)
    text = _WHITESPACE_RE.sub(" ", text).strip()
    return text


def name_contained_in_passage(name: str, passage: str) -> bool:
    """Return True if name appears in passage (accent/case insensitive).

    Substring match: "Paris" is considered contained in "Parisian". This
    is intentional because LLM excerpts often use inflected forms; the
    trade-off accepts rare false positives for broader recall.
    """
    if not name or not passage:
        return False
    normalized_name = _strip_accents(name).lower()
    normalized_passage = _strip_accents(passage).lower()
    return normalized_name in normalized_passage
```

- [ ] **Step 9: Run normalizer tests to verify they pass**

Run:

```bash
docker compose -f docker-compose.local.yml exec -T web pytest epocha/apps/knowledge/tests/test_normalizer.py -v
```

Expected: all PASS.

- [ ] **Step 10: Write and run the versions smoke test**

Create `epocha/apps/knowledge/tests/test_versions.py`:

```python
"""Smoke tests for the versions module."""
from epocha.apps.knowledge import versions


def test_ontology_version_is_string():
    assert isinstance(versions.ONTOLOGY_VERSION, str)
    assert versions.ONTOLOGY_VERSION != ""


def test_embedding_dim_is_1024():
    assert versions.EMBEDDING_DIM == 1024


def test_chunk_params_are_positive():
    assert versions.CHUNK_SIZE_TOKENS > 0
    assert versions.CHUNK_OVERLAP_TOKENS >= 0
    assert versions.CHUNK_OVERLAP_TOKENS < versions.CHUNK_SIZE_TOKENS


def test_dedup_threshold_in_range():
    assert 0.0 < versions.DEDUP_SIMILARITY_THRESHOLD < 1.0
```

Run: `docker compose -f docker-compose.local.yml exec -T web pytest epocha/apps/knowledge/tests/test_versions.py -v`

Expected: all PASS.

- [ ] **Step 11: Run the full knowledge test suite**

Run: `docker compose -f docker-compose.local.yml exec -T web pytest epocha/apps/knowledge/ -v`

Expected: all tests PASS.

- [ ] **Step 12: Commit**

```
feat(knowledge): add versioning, ontology, and normalizer modules

CHANGE: Add versions.py with pipeline constants, ontology.py with the
10-entity and 20-relation controlled vocabularies and validators, and
normalizer.py with canonical name normalization and passage containment
checks used by the mechanical source_type assignment rule.
```

---

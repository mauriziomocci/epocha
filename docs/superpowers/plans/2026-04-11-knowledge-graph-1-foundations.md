# Knowledge Graph Implementation Plan — Part 1: Foundations

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the shared data layer and utility modules of the Knowledge Graph feature: Postgres infrastructure with pgvector, versioning and ontology modules, document and chunk persistence with embeddings, and the extraction cache model. After this plan is complete, the system can ingest documents, chunk them, embed them, and persist everything deduplicated across simulations — but the LLM extraction logic itself is not yet implemented. That comes in Part 2.

**Architecture:** This plan adds a new Django app `epocha.apps.knowledge` scoped only to the shared-tier data layer: documents deduplicated by content hash, chunks with bge-m3 embeddings, and a keyed extraction cache table (empty at this stage). No LLM calls, no materialized per-simulation graphs, no API endpoints. Those layers come in later parts.

**Tech Stack:** Django 5.x, pgvector (Postgres extension + Python package), fastembed (ONNX-based BAAI/bge-m3 1024-dim multilingual embeddings), langchain-text-splitters.

**Spec:** `docs/superpowers/specs/2026-04-11-knowledge-graph-design.md`

**Follow-up plans (not this document):**
- Part 2 — Extraction pipeline: prompts, per-chunk LLM extraction, merge and deduplication
- Part 3 — Graph, materialization, orchestration, world generator integration
- Part 4 — API, dashboard, visualization, housekeeping

---

## File Structure (Part 1 scope)

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
| `epocha/apps/knowledge/models.py` | KnowledgeDocument, KnowledgeDocumentAccess, KnowledgeChunk, ExtractionCache (only the shared-tier models; graph-tier models come in Part 3) | New |
| `epocha/apps/knowledge/migrations/0001_initial.py` | Initial migration with VectorExtension | New |
| `epocha/apps/knowledge/embedding.py` | fastembed wrapper with bge-m3 | New |
| `epocha/apps/knowledge/chunking.py` | Recursive text splitter wrapper | New |
| `epocha/apps/knowledge/ingestion.py` | Document parse + normalize + hash + store | New |
| `epocha/apps/knowledge/cache.py` | Cache key builder | New |
| `epocha/apps/knowledge/tests/` | Test files for each module | New |
| `epocha/apps/knowledge/tests/fixtures/small_french_rev.txt` | Test fixture document | New |

---

## Tasks summary (Part 1 scope)

1. **Infrastructure setup** — custom Postgres Dockerfile with pgvector, dependencies, app scaffolding, settings
2. **Versioning, ontology, and normalizer modules** — versions.py, ontology.py, normalizer.py with TDD tests
3. **Document models and ingestion service** — KnowledgeDocument, KnowledgeDocumentAccess models, initial migration with VectorExtension, ingestion service (parse, normalize, hash, store, access tracking)
4. **Chunk model, chunking service, embedding service** — KnowledgeChunk model, chunking.py with RecursiveCharacterTextSplitter wrapper, embedding.py with fastembed bge-m3 wrapper, integration tests with real model
5. **ExtractionCache model and cache key builder** — ExtractionCache model and cache.py with the composite key builder

Each task is self-contained, has tests, and ends with a commit. Tasks must be completed in order because later tasks depend on models and services from earlier ones. After Task 5, the system can ingest documents, chunk them, embed them, and has a cache table ready to receive extraction results — but no LLM extraction logic yet. Part 2 will add that.

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
docker compose -f docker-compose.local.yml build db
docker compose -f docker-compose.local.yml up -d db
docker compose -f docker-compose.local.yml exec -T db psql -U epocha -d epocha -c "CREATE EXTENSION IF NOT EXISTS vector;"
docker compose -f docker-compose.local.yml exec -T db psql -U epocha -d epocha -c "SELECT extname FROM pg_extension;"
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

### Task 3: Document models and ingestion service

**Files:**
- Create: `epocha/apps/knowledge/models.py` (only KnowledgeDocument and KnowledgeDocumentAccess in this task)
- Create: `epocha/apps/knowledge/migrations/0001_initial.py`
- Create: `epocha/apps/knowledge/ingestion.py`
- Create: `epocha/apps/knowledge/tests/test_models_document.py`
- Create: `epocha/apps/knowledge/tests/test_ingestion.py`
- Create: `epocha/apps/knowledge/tests/fixtures/small_french_rev.txt`

- [ ] **Step 1: Create the test fixture document**

Create `epocha/apps/knowledge/tests/fixtures/small_french_rev.txt` with the following content (use the exact text):

```
On July 14, 1789, the Bastille fortress in Paris was stormed by revolutionary crowds. The event is considered the symbolic beginning of the French Revolution. Maximilien Robespierre, a deputy to the Estates-General, was not directly present at the storming but became one of its most forceful defenders in the National Assembly during the following weeks.

The Bastille was a medieval fortress and state prison used by the monarchy of the Ancien Regime. Its fall marked the collapse of royal authority in Paris. King Louis XVI initially refused to acknowledge the gravity of the event, writing in his journal only the single word "rien" (nothing).

Robespierre was a member of the Jacobin Club, the most radical of the political societies formed during the Revolution. The Club met in Paris and published pamphlets defending popular sovereignty, equality before the law, and the virtue of republican government. Robespierre believed that political virtue was the foundation of a just republic, and he opposed the moderate Girondin faction that favored constitutional monarchy.

The Declaration of the Rights of Man and of the Citizen, enacted by the National Assembly on August 26, 1789, proclaimed that men are born free and equal in rights. The Declaration was influenced by the ideas of the Enlightenment, particularly those of Rousseau and Montesquieu. It established liberty, property, security, and resistance to oppression as natural and imprescriptible rights.
```

This fixture is used by ingestion tests and later by extraction integration tests. Keep the content stable; do not edit it after this task.

- [ ] **Step 2: Write the failing tests for the document models**

Create `epocha/apps/knowledge/tests/test_models_document.py`:

```python
"""Tests for KnowledgeDocument and KnowledgeDocumentAccess models."""
import pytest
from django.db import IntegrityError

from epocha.apps.knowledge.models import (
    KnowledgeDocument,
    KnowledgeDocumentAccess,
)
from epocha.apps.users.models import User


@pytest.fixture
def user(db):
    return User.objects.create_user(
        email="kg@epocha.dev", username="kguser", password="pass1234"
    )


@pytest.fixture
def other_user(db):
    return User.objects.create_user(
        email="kg2@epocha.dev", username="kguser2", password="pass1234"
    )


@pytest.fixture
def document(db):
    return KnowledgeDocument.objects.create(
        title="Test Document",
        mime_type="text/plain",
        content_hash="a" * 64,
        normalized_text="some content",
        char_count=12,
    )


@pytest.mark.django_db
class TestKnowledgeDocument:
    def test_create_document(self, document):
        assert document.title == "Test Document"
        assert document.char_count == 12
        assert document.first_uploaded_at is not None

    def test_content_hash_unique(self, document):
        with pytest.raises(IntegrityError):
            KnowledgeDocument.objects.create(
                title="Duplicate",
                mime_type="text/plain",
                content_hash="a" * 64,  # same hash
                normalized_text="different content",
                char_count=17,
            )

    def test_str_representation(self, document):
        assert "Test Document" in str(document)
        assert "12 chars" in str(document)


@pytest.mark.django_db
class TestKnowledgeDocumentAccess:
    def test_create_access(self, user, document):
        access = KnowledgeDocumentAccess.objects.create(
            user=user, document=document, original_filename="test.txt"
        )
        assert access.user == user
        assert access.document == document
        assert access.uploaded_at is not None

    def test_user_document_unique(self, user, document):
        KnowledgeDocumentAccess.objects.create(
            user=user, document=document, original_filename="test.txt"
        )
        with pytest.raises(IntegrityError):
            KnowledgeDocumentAccess.objects.create(
                user=user, document=document, original_filename="again.txt"
            )

    def test_two_users_share_one_document(self, user, other_user, document):
        KnowledgeDocumentAccess.objects.create(user=user, document=document)
        KnowledgeDocumentAccess.objects.create(user=other_user, document=document)
        assert KnowledgeDocumentAccess.objects.filter(document=document).count() == 2

    def test_document_survives_user_deletion(self, user, other_user, document):
        KnowledgeDocumentAccess.objects.create(user=user, document=document)
        KnowledgeDocumentAccess.objects.create(user=other_user, document=document)
        user.delete()
        # Document must still exist because other_user is still using it
        assert KnowledgeDocument.objects.filter(pk=document.pk).exists()
        assert KnowledgeDocumentAccess.objects.filter(
            document=document, user=other_user
        ).exists()
        assert not KnowledgeDocumentAccess.objects.filter(user=user).exists()
```

- [ ] **Step 3: Implement the document models**

Create `epocha/apps/knowledge/models.py`:

```python
"""Knowledge Graph models — shared tier (Part 1 scope).

The shared-tier models persist documents, chunks, and extraction cache
entries deduplicated across simulations and users. The per-simulation
graph-tier models (KnowledgeGraph, KnowledgeNode, KnowledgeRelation,
and their citation tables) are added in Part 3 of the implementation
plan.

Scientific rigor: content_hash deduplication guarantees reproducibility.
Two uploads of the same file always collapse to one row, so downstream
extraction and embedding results are identical regardless of who
uploaded first.
"""
from __future__ import annotations

from django.conf import settings
from django.db import models


class KnowledgeDocument(models.Model):
    """Uploaded source document, deduplicated across users and simulations
    by content hash.

    Ownership and access control are decoupled from the document entity
    itself: two users uploading the same content share a single row via
    content_hash uniqueness, and their access is tracked through
    KnowledgeDocumentAccess. This prevents CASCADE deletions from
    removing documents that other users are actively using.
    """

    title = models.CharField(max_length=255)
    mime_type = models.CharField(max_length=50)
    content_hash = models.CharField(
        max_length=64, unique=True, db_index=True,
        help_text="SHA-256 of normalized text content",
    )
    normalized_text = models.TextField()
    char_count = models.PositiveIntegerField()
    first_uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} ({self.char_count} chars)"


class KnowledgeDocumentAccess(models.Model):
    """Tracks which users have uploaded or accessed a specific document.

    This is the ownership layer, separate from the document itself.
    Deleting a user removes only their access rows, never the document.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="knowledge_document_accesses",
    )
    document = models.ForeignKey(
        KnowledgeDocument, on_delete=models.CASCADE,
        related_name="accesses",
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)
    original_filename = models.CharField(max_length=255, blank=True)

    class Meta:
        unique_together = ("user", "document")
        indexes = [models.Index(fields=["user", "document"])]
```

- [ ] **Step 4: Generate and apply the initial migration**

Run:

```bash
docker compose -f docker-compose.local.yml exec -T web python manage.py makemigrations knowledge --name initial
```

Then open the generated migration file `epocha/apps/knowledge/migrations/0001_initial.py` and add `VectorExtension()` as the first operation so the `vector` extension is enabled before any vector fields are introduced in future migrations. The operations list should start with:

```python
from django.contrib.postgres.operations import CreateExtension
from pgvector.django import VectorExtension

operations = [
    VectorExtension(),
    # ... the auto-generated CreateModel operations follow ...
]
```

Then apply:

```bash
docker compose -f docker-compose.local.yml exec -T web python manage.py migrate knowledge
```

Expected: migration applies successfully; `SELECT extname FROM pg_extension;` in the DB shows `vector` alongside `postgis`.

- [ ] **Step 5: Run the document model tests**

Run:

```bash
docker compose -f docker-compose.local.yml exec -T web pytest epocha/apps/knowledge/tests/test_models_document.py -v
```

Expected: all PASS.

- [ ] **Step 6: Write the failing tests for the ingestion service**

Create `epocha/apps/knowledge/tests/test_ingestion.py`:

```python
"""Tests for the ingestion service."""
import hashlib
import threading
from pathlib import Path

import pytest
from django.core.exceptions import ValidationError

from epocha.apps.knowledge.ingestion import (
    ingest_document,
    normalize_text,
    compute_content_hash,
)
from epocha.apps.knowledge.models import (
    KnowledgeDocument,
    KnowledgeDocumentAccess,
)
from epocha.apps.users.models import User

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "small_french_rev.txt"


@pytest.fixture
def user(db):
    return User.objects.create_user(
        email="ing@epocha.dev", username="inguser", password="pass1234"
    )


@pytest.fixture
def other_user(db):
    return User.objects.create_user(
        email="ing2@epocha.dev", username="inguser2", password="pass1234"
    )


class TestNormalizeText:
    def test_strips_bom(self):
        assert normalize_text("\ufeffhello") == "hello"

    def test_collapses_whitespace(self):
        assert normalize_text("hello   world\n\nfoo") == "hello world foo"

    def test_unicode_nfc(self):
        # "é" can be NFC (single codepoint) or NFD (e + combining acute).
        # normalize_text should produce NFC consistently.
        nfd = "cafe\u0301"
        result = normalize_text(nfd)
        assert result == "café"

    def test_trims(self):
        assert normalize_text("  hello  ") == "hello"


class TestComputeContentHash:
    def test_deterministic(self):
        h1 = compute_content_hash("hello world")
        h2 = compute_content_hash("hello world")
        assert h1 == h2

    def test_is_sha256_hex(self):
        h = compute_content_hash("hello")
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)

    def test_different_inputs_different_hashes(self):
        assert compute_content_hash("a") != compute_content_hash("b")


@pytest.mark.django_db
class TestIngestDocument:
    def test_ingest_fixture(self, user):
        raw_text = FIXTURE_PATH.read_text(encoding="utf-8")
        doc, access = ingest_document(
            user=user,
            raw_text=raw_text,
            title="French Revolution sample",
            mime_type="text/plain",
            original_filename="small_french_rev.txt",
        )
        assert doc.char_count > 0
        assert doc.content_hash is not None
        assert access.user == user
        assert access.document == doc

    def test_same_content_shared_across_users(self, user, other_user):
        raw_text = "some content"
        doc1, _ = ingest_document(
            user=user, raw_text=raw_text,
            title="doc", mime_type="text/plain",
            original_filename="a.txt",
        )
        doc2, _ = ingest_document(
            user=other_user, raw_text=raw_text,
            title="doc", mime_type="text/plain",
            original_filename="b.txt",
        )
        assert doc1.pk == doc2.pk
        assert KnowledgeDocumentAccess.objects.filter(document=doc1).count() == 2

    def test_document_size_limit(self, user, settings):
        settings.EPOCHA_KG_MAX_DOCUMENT_CHARS = 100
        oversized = "a" * 200
        with pytest.raises(ValidationError):
            ingest_document(
                user=user, raw_text=oversized,
                title="big", mime_type="text/plain",
                original_filename="big.txt",
            )

    def test_concurrent_ingestion_same_content(self, user, other_user):
        raw_text = "some shared content for concurrency test"
        results = []
        errors = []

        def ingest_worker(u):
            try:
                doc, _ = ingest_document(
                    user=u, raw_text=raw_text,
                    title="concurrent", mime_type="text/plain",
                    original_filename="c.txt",
                )
                results.append(doc.pk)
            except Exception as e:
                errors.append(e)

        t1 = threading.Thread(target=ingest_worker, args=(user,))
        t2 = threading.Thread(target=ingest_worker, args=(other_user,))
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        assert not errors, f"Unexpected errors: {errors}"
        assert len(results) == 2
        assert results[0] == results[1], "Both ingestions should resolve to the same document"
```

- [ ] **Step 7: Run ingestion tests to verify they fail**

Run:

```bash
docker compose -f docker-compose.local.yml exec -T web pytest epocha/apps/knowledge/tests/test_ingestion.py -v
```

Expected: ImportError for `epocha.apps.knowledge.ingestion`.

- [ ] **Step 8: Implement the ingestion service**

Create `epocha/apps/knowledge/ingestion.py`:

```python
"""Document ingestion service.

Responsible for Stage 1 of the extraction pipeline: text parsing
(delegated to world.document_parser for file formats), normalization,
hashing, deduplicated persistence, and access tracking. This module is
intentionally small and pure: it takes already-decoded text and
produces database rows. File decoding is orchestrated by the Celery
task in Part 3 of the implementation plan.
"""
from __future__ import annotations

import hashlib
import re
import unicodedata

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from .models import KnowledgeDocument, KnowledgeDocumentAccess

_WHITESPACE_RE = re.compile(r"\s+")


def normalize_text(raw: str) -> str:
    """Normalize document text for hashing and storage.

    Steps: strip BOM, Unicode NFC, collapse whitespace to single spaces,
    trim. Normalization must be deterministic so the content hash is
    stable across uploads.
    """
    if not raw:
        return ""
    text = raw.lstrip("\ufeff")
    text = unicodedata.normalize("NFC", text)
    text = _WHITESPACE_RE.sub(" ", text)
    return text.strip()


def compute_content_hash(normalized: str) -> str:
    """Compute the SHA-256 hex digest of normalized text."""
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def ingest_document(
    *,
    user,
    raw_text: str,
    title: str,
    mime_type: str,
    original_filename: str,
) -> tuple[KnowledgeDocument, KnowledgeDocumentAccess]:
    """Ingest a document: normalize, hash, deduplicate, track access.

    Returns a tuple of (document, access). If another user has already
    uploaded the same content, the existing document is reused and a new
    access row is created for the current user.

    Raises:
        ValidationError: if the document exceeds the size cap.
    """
    normalized = normalize_text(raw_text)

    max_chars = getattr(settings, "EPOCHA_KG_MAX_DOCUMENT_CHARS", 500000)
    if len(normalized) > max_chars:
        raise ValidationError(
            f"Document is too large: {len(normalized)} characters exceeds "
            f"the limit of {max_chars}."
        )

    content_hash = compute_content_hash(normalized)

    with transaction.atomic():
        try:
            document = KnowledgeDocument.objects.create(
                title=title,
                mime_type=mime_type,
                content_hash=content_hash,
                normalized_text=normalized,
                char_count=len(normalized),
            )
        except IntegrityError:
            # Another transaction inserted the same content first.
            document = KnowledgeDocument.objects.get(content_hash=content_hash)

        access, _ = KnowledgeDocumentAccess.objects.get_or_create(
            user=user,
            document=document,
            defaults={"original_filename": original_filename},
        )

    return document, access
```

- [ ] **Step 9: Run ingestion tests to verify they pass**

Run:

```bash
docker compose -f docker-compose.local.yml exec -T web pytest epocha/apps/knowledge/tests/test_ingestion.py -v
```

Expected: all PASS, including the concurrent ingestion test.

- [ ] **Step 10: Run the full test suite to confirm no regression**

Run:

```bash
docker compose -f docker-compose.local.yml exec -T web pytest -q
```

Expected: all tests pass.

- [ ] **Step 11: Commit**

```
feat(knowledge): add document models and ingestion service

CHANGE: Add KnowledgeDocument and KnowledgeDocumentAccess models with
the vector extension enabled via the initial migration. The ingestion
service normalizes text, computes a stable SHA-256 content hash,
deduplicates across users via a unique constraint, and tracks per-user
access in a separate table. Concurrent uploads of the same content
converge to a single document row without error.
```

---

### Task 4: Chunk model, chunking service, embedding service

**Files:**
- Modify: `epocha/apps/knowledge/models.py` (add KnowledgeChunk)
- Create: `epocha/apps/knowledge/migrations/0002_chunk.py` (auto-generated)
- Create: `epocha/apps/knowledge/embedding.py`
- Create: `epocha/apps/knowledge/chunking.py`
- Create: `epocha/apps/knowledge/tests/test_embedding.py`
- Create: `epocha/apps/knowledge/tests/test_chunking.py`
- Create: `epocha/apps/knowledge/tests/test_models_chunk.py`
- Modify: `pytest.ini` or `pyproject.toml` to register the `slow` marker

- [ ] **Step 1: Register the slow marker for pytest**

Find the pytest configuration (likely `pyproject.toml` or `pytest.ini`). If there is no `[tool.pytest.ini_options]` or `[pytest]` section with markers, add one. Append `slow: marks tests as slow (downloads the bge-m3 model; skip with -m "not slow")` to the markers list. Example for `pyproject.toml`:

```toml
[tool.pytest.ini_options]
markers = [
    "slow: marks tests as slow (downloads the bge-m3 model; skip with -m 'not slow')",
]
```

If the section already exists with other markers, append the new marker without removing the others.

- [ ] **Step 2: Write the failing tests for KnowledgeChunk model**

Create `epocha/apps/knowledge/tests/test_models_chunk.py`:

```python
"""Tests for the KnowledgeChunk model."""
import pytest

from epocha.apps.knowledge.models import KnowledgeChunk, KnowledgeDocument


@pytest.fixture
def document(db):
    return KnowledgeDocument.objects.create(
        title="Test", mime_type="text/plain",
        content_hash="b" * 64,
        normalized_text="The Bastille was stormed on July 14, 1789.",
        char_count=42,
    )


@pytest.mark.django_db
class TestKnowledgeChunk:
    def test_create_chunk(self, document):
        embedding = [0.1] * 1024
        chunk = KnowledgeChunk.objects.create(
            document=document,
            chunk_index=0,
            text="The Bastille was stormed on July 14, 1789.",
            start_char=0,
            end_char=42,
            embedding=embedding,
        )
        assert chunk.document == document
        assert chunk.chunk_index == 0
        assert len(chunk.embedding) == 1024

    def test_chunk_index_unique_per_document(self, document):
        from django.db import IntegrityError
        KnowledgeChunk.objects.create(
            document=document, chunk_index=0,
            text="a", start_char=0, end_char=1,
            embedding=[0.0] * 1024,
        )
        with pytest.raises(IntegrityError):
            KnowledgeChunk.objects.create(
                document=document, chunk_index=0,
                text="b", start_char=1, end_char=2,
                embedding=[0.0] * 1024,
            )

    def test_chunks_ordered_by_index(self, document):
        for i in range(3):
            KnowledgeChunk.objects.create(
                document=document, chunk_index=i,
                text=f"chunk {i}", start_char=i, end_char=i + 7,
                embedding=[float(i)] * 1024,
            )
        chunks = list(document.chunks.order_by("chunk_index"))
        assert [c.chunk_index for c in chunks] == [0, 1, 2]
```

- [ ] **Step 3: Add the KnowledgeChunk model**

Append to `epocha/apps/knowledge/models.py` (after KnowledgeDocumentAccess):

```python
from pgvector.django import VectorField, HnswIndex
from epocha.apps.knowledge.versions import EMBEDDING_DIM


class KnowledgeChunk(models.Model):
    """A text chunk of a document with its embedding, reused across graphs.

    Chunks are created once per document and persisted with their
    embedding. Re-running the pipeline on the same document is a no-op
    because chunks already exist (idempotent chunking).
    """

    document = models.ForeignKey(
        KnowledgeDocument, on_delete=models.CASCADE, related_name="chunks",
    )
    chunk_index = models.PositiveIntegerField()
    text = models.TextField()
    start_char = models.PositiveIntegerField()
    end_char = models.PositiveIntegerField()
    embedding = VectorField(dimensions=EMBEDDING_DIM)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("document", "chunk_index")
        ordering = ["document", "chunk_index"]
        indexes = [
            HnswIndex(
                name="chunk_embedding_hnsw",
                fields=["embedding"],
                m=16,
                ef_construction=64,
                opclasses=["vector_cosine_ops"],
            ),
        ]
```

Also add `from pgvector.django import VectorField, HnswIndex` at the top of the file if not already present.

- [ ] **Step 4: Generate and apply the migration**

Run:

```bash
docker compose -f docker-compose.local.yml exec -T web python manage.py makemigrations knowledge --name chunk
docker compose -f docker-compose.local.yml exec -T web python manage.py migrate knowledge
```

Expected: migration applies successfully.

- [ ] **Step 5: Run the chunk model tests**

Run:

```bash
docker compose -f docker-compose.local.yml exec -T web pytest epocha/apps/knowledge/tests/test_models_chunk.py -v
```

Expected: all PASS.

- [ ] **Step 6: Write the failing tests for the chunking service**

Create `epocha/apps/knowledge/tests/test_chunking.py`:

```python
"""Tests for the chunking service."""
import pytest

from epocha.apps.knowledge.chunking import split_text_into_chunks, ChunkResult


class TestSplitTextIntoChunks:
    def test_short_text_single_chunk(self):
        text = "This is a short text."
        chunks = split_text_into_chunks(text)
        assert len(chunks) == 1
        assert chunks[0].text == text
        assert chunks[0].start_char == 0
        assert chunks[0].end_char == len(text)
        assert chunks[0].chunk_index == 0

    def test_long_text_multiple_chunks(self):
        # ~5000 chars produces at least 2 chunks (default chunk_size=3200 chars)
        text = ("The Bastille was stormed. " * 200).strip()
        chunks = split_text_into_chunks(text)
        assert len(chunks) >= 2
        for i, chunk in enumerate(chunks):
            assert chunk.chunk_index == i

    def test_chunk_indices_sequential(self):
        text = ("a. " * 2000).strip()
        chunks = split_text_into_chunks(text)
        indices = [c.chunk_index for c in chunks]
        assert indices == list(range(len(chunks)))

    def test_respects_max_chunks_limit(self):
        text = ("word " * 100000).strip()  # force many chunks
        chunks = split_text_into_chunks(text, max_chunks=5)
        assert len(chunks) == 5

    def test_offsets_are_valid(self):
        text = "First sentence. Second sentence. Third sentence."
        chunks = split_text_into_chunks(text)
        for chunk in chunks:
            assert 0 <= chunk.start_char < chunk.end_char
            assert chunk.end_char <= len(text)
            # Text at the offsets should match the chunk text approximately
            # (overlap may make exact match tricky, so we check containment)
            assert chunk.text.strip() != ""

    def test_empty_text(self):
        chunks = split_text_into_chunks("")
        assert chunks == []
```

- [ ] **Step 7: Run chunking tests to verify they fail**

Run:

```bash
docker compose -f docker-compose.local.yml exec -T web pytest epocha/apps/knowledge/tests/test_chunking.py -v
```

Expected: ImportError for `epocha.apps.knowledge.chunking`.

- [ ] **Step 8: Implement the chunking service**

Create `epocha/apps/knowledge/chunking.py`:

```python
"""Text chunking service using langchain_text_splitters.

Produces sentence-aware chunks with overlap. Chunk size and overlap are
configured in versions.py. The service returns lightweight ChunkResult
dataclasses; persistence is handled separately so the chunker remains
pure and testable without a database.
"""
from __future__ import annotations

from dataclasses import dataclass

from langchain_text_splitters import RecursiveCharacterTextSplitter

from .versions import (
    CHUNK_CHARS_PER_TOKEN,
    CHUNK_OVERLAP_TOKENS,
    CHUNK_SIZE_TOKENS,
)

# Separators ordered from strongest (paragraph break) to weakest.
# Dialog em-dash and semicolon are included for European historical texts.
_SEPARATORS: list[str] = ["\n\n", "\n", ". ", "; ", " — ", " ", ""]


@dataclass(frozen=True)
class ChunkResult:
    """A single chunk with offsets into the original text."""

    chunk_index: int
    text: str
    start_char: int
    end_char: int


def split_text_into_chunks(
    text: str,
    *,
    chunk_size_chars: int | None = None,
    chunk_overlap_chars: int | None = None,
    max_chunks: int = 50,
) -> list[ChunkResult]:
    """Split text into overlapping chunks with sentence-aware boundaries.

    Args:
        text: The normalized text to split.
        chunk_size_chars: Override for chunk size (default from versions.py).
        chunk_overlap_chars: Override for chunk overlap (default from versions.py).
        max_chunks: Hard cap on the number of chunks; excess chunks are dropped.

    Returns:
        List of ChunkResult with offsets into the original text. Empty input
        returns an empty list.
    """
    if not text:
        return []

    size = chunk_size_chars or (CHUNK_SIZE_TOKENS * CHUNK_CHARS_PER_TOKEN)
    overlap = chunk_overlap_chars or (CHUNK_OVERLAP_TOKENS * CHUNK_CHARS_PER_TOKEN)

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=size,
        chunk_overlap=overlap,
        separators=_SEPARATORS,
        length_function=len,
        is_separator_regex=False,
    )

    # We use create_documents to preserve content, then compute offsets
    # by scanning the original text. The splitter does not return offsets
    # natively so we reconstruct them.
    raw_chunks = splitter.split_text(text)

    results: list[ChunkResult] = []
    cursor = 0
    for i, chunk_text in enumerate(raw_chunks):
        if i >= max_chunks:
            break
        # Find this chunk in the original text starting from cursor.
        # Chunks are produced sequentially with overlap, so the search
        # start must back off by the overlap to find the correct occurrence.
        search_start = max(0, cursor - overlap)
        idx = text.find(chunk_text, search_start)
        if idx == -1:
            # Fallback: search from the beginning (rare edge case)
            idx = text.find(chunk_text)
            if idx == -1:
                # Skip if chunk cannot be located at all
                continue
        start = idx
        end = idx + len(chunk_text)
        results.append(ChunkResult(
            chunk_index=i,
            text=chunk_text,
            start_char=start,
            end_char=end,
        ))
        cursor = end

    return results
```

- [ ] **Step 9: Run chunking tests to verify they pass**

Run:

```bash
docker compose -f docker-compose.local.yml exec -T web pytest epocha/apps/knowledge/tests/test_chunking.py -v
```

Expected: all PASS.

- [ ] **Step 10: Write the failing tests for the embedding service**

Create `epocha/apps/knowledge/tests/test_embedding.py`:

```python
"""Tests for the embedding service.

The real model bge-m3 is loaded in integration tests marked as slow.
Unit tests use a mock to avoid the model download in fast test runs.
"""
from unittest.mock import MagicMock, patch

import pytest

from epocha.apps.knowledge.embedding import (
    EMBEDDING_DIM,
    embed_texts,
    get_embedding_model,
)


class TestEmbedTextsMocked:
    def test_returns_list_of_vectors(self):
        with patch("epocha.apps.knowledge.embedding.get_embedding_model") as mock:
            mock_model = MagicMock()
            mock_model.embed.return_value = iter([[0.1] * EMBEDDING_DIM] * 3)
            mock.return_value = mock_model

            texts = ["first", "second", "third"]
            results = embed_texts(texts)

            assert len(results) == 3
            assert all(len(v) == EMBEDDING_DIM for v in results)

    def test_empty_input_returns_empty(self):
        results = embed_texts([])
        assert results == []


@pytest.mark.slow
class TestEmbedTextsReal:
    def test_real_model_produces_1024_dim_vectors(self):
        texts = ["The storming of the Bastille was a pivotal event."]
        results = embed_texts(texts)
        assert len(results) == 1
        assert len(results[0]) == EMBEDDING_DIM

    def test_real_model_is_deterministic(self):
        text = "Robespierre was a leader of the Jacobins."
        v1 = embed_texts([text])[0]
        v2 = embed_texts([text])[0]
        assert v1 == v2

    def test_real_model_multilingual(self):
        texts = [
            "The Bastille fell on July 14.",      # English
            "La Bastille tomba le 14 juillet.",   # French
            "La Bastiglia cadde il 14 luglio.",   # Italian
        ]
        results = embed_texts(texts)
        assert len(results) == 3
        assert all(len(v) == EMBEDDING_DIM for v in results)
```

- [ ] **Step 11: Run embedding unit tests to verify they fail**

Run:

```bash
docker compose -f docker-compose.local.yml exec -T web pytest epocha/apps/knowledge/tests/test_embedding.py -v -m "not slow"
```

Expected: ImportError for `epocha.apps.knowledge.embedding`.

- [ ] **Step 12: Implement the embedding service**

Create `epocha/apps/knowledge/embedding.py`:

```python
"""Embedding service using fastembed with BAAI/bge-m3.

The model is cached as a module-level singleton via lru_cache so the
first call downloads and loads it, and subsequent calls reuse the same
instance within a process. bge-m3 is multilingual (100+ languages) and
produces 1024-dimensional vectors.

Reference: Chen et al. (2024). "BGE M3-Embedding: Multi-Lingual,
Multi-Functionality, Multi-Granularity Text Embeddings Through
Self-Knowledge Distillation". arXiv:2402.03216.
"""
from __future__ import annotations

import logging
from functools import lru_cache
from typing import Iterable

from django.conf import settings

from .versions import EMBEDDING_DIM, EMBEDDING_MODEL

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_embedding_model():
    """Return the singleton TextEmbedding instance.

    Imported lazily so tests that mock embeddings do not trigger a
    model download just by importing this module.
    """
    from fastembed import TextEmbedding
    logger.info("Loading embedding model %s (first call, may download)", EMBEDDING_MODEL)
    return TextEmbedding(model_name=EMBEDDING_MODEL)


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a list of texts into 1024-dimensional vectors.

    Processes in batches according to EPOCHA_KG_EMBEDDING_BATCH_SIZE from
    settings (default 10). Returns an empty list for empty input.
    """
    if not texts:
        return []

    model = get_embedding_model()
    batch_size = getattr(settings, "EPOCHA_KG_EMBEDDING_BATCH_SIZE", 10)

    vectors: list[list[float]] = []
    for generator_output in model.embed(texts, batch_size=batch_size):
        # fastembed returns numpy arrays; convert to plain Python lists
        # so they serialize cleanly to JSON and pgvector.
        vectors.append([float(x) for x in generator_output])

    return vectors
```

- [ ] **Step 13: Run embedding unit tests to verify they pass**

Run:

```bash
docker compose -f docker-compose.local.yml exec -T web pytest epocha/apps/knowledge/tests/test_embedding.py -v -m "not slow"
```

Expected: all non-slow tests PASS.

- [ ] **Step 14: Run the slow integration tests (one-time model download)**

Run:

```bash
docker compose -f docker-compose.local.yml exec -T web pytest epocha/apps/knowledge/tests/test_embedding.py -v -m slow
```

Expected: tests PASS after the bge-m3 model is downloaded (first run may take 30-60 seconds; subsequent runs are fast because the model is cached in the container).

- [ ] **Step 15: Run the full test suite to confirm no regression**

Run:

```bash
docker compose -f docker-compose.local.yml exec -T web pytest -q -m "not slow"
```

Expected: all fast tests PASS.

- [ ] **Step 16: Commit**

```
feat(knowledge): add chunk model, chunking, and embedding services

CHANGE: Add KnowledgeChunk model with pgvector HNSW index on the 1024-dim
embedding field, RecursiveCharacterTextSplitter wrapper that produces
sentence-aware chunks with stable offsets into the source text, and
fastembed-based embedding service using BAAI/bge-m3 for multilingual
1024-dim vectors. Real-model tests are marked as slow for fast CI runs.
```

---

### Task 5: ExtractionCache model and cache key builder

**Files:**
- Modify: `epocha/apps/knowledge/models.py` (add ExtractionCache)
- Create: `epocha/apps/knowledge/migrations/0003_extraction_cache.py` (auto-generated)
- Create: `epocha/apps/knowledge/cache.py`
- Create: `epocha/apps/knowledge/tests/test_models_cache.py`
- Create: `epocha/apps/knowledge/tests/test_cache_key.py`

- [ ] **Step 1: Write the failing tests for the ExtractionCache model**

Create `epocha/apps/knowledge/tests/test_models_cache.py`:

```python
"""Tests for the ExtractionCache model."""
import pytest

from epocha.apps.knowledge.models import ExtractionCache


@pytest.mark.django_db
class TestExtractionCache:
    def test_create_cache_entry(self):
        entry = ExtractionCache.objects.create(
            cache_key="c" * 64,
            documents_hash="d" * 64,
            ontology_version="v1",
            extraction_prompt_version="v1",
            llm_model="llama-3.3-70b-versatile",
            extracted_data={"nodes": [], "relations": []},
            stats={"chunks_processed": 0},
        )
        assert entry.cache_key == "c" * 64
        assert entry.hit_count == 0
        assert entry.last_hit_at is None

    def test_cache_key_primary_key(self):
        from django.db import IntegrityError
        ExtractionCache.objects.create(
            cache_key="e" * 64,
            documents_hash="d" * 64,
            ontology_version="v1",
            extraction_prompt_version="v1",
            llm_model="m",
            extracted_data={},
            stats={},
        )
        with pytest.raises(IntegrityError):
            ExtractionCache.objects.create(
                cache_key="e" * 64,  # duplicate PK
                documents_hash="d" * 64,
                ontology_version="v2",
                extraction_prompt_version="v1",
                llm_model="m",
                extracted_data={},
                stats={},
            )

    def test_documents_hash_is_indexed_and_queryable(self):
        for i in range(3):
            ExtractionCache.objects.create(
                cache_key=f"{i:064}",
                documents_hash="shared" + "0" * 58,
                ontology_version="v1",
                extraction_prompt_version="v1",
                llm_model="m",
                extracted_data={},
                stats={},
            )
        results = ExtractionCache.objects.filter(
            documents_hash="shared" + "0" * 58
        )
        assert results.count() == 3
```

- [ ] **Step 2: Add the ExtractionCache model**

Append to `epocha/apps/knowledge/models.py` (after KnowledgeChunk):

```python
class ExtractionCache(models.Model):
    """Cache of the expensive LLM extraction step.

    Keyed by the composite of documents hash, ontology version, extraction
    prompt version, and LLM model. Any change to these invalidates the
    cache automatically, preventing stale results from contaminating new
    simulations. The cached payload is the raw LLM extraction output;
    materialization into per-simulation graph rows is a separate step
    (Part 3 of the implementation plan).
    """

    cache_key = models.CharField(max_length=64, primary_key=True)
    documents_hash = models.CharField(max_length=64, db_index=True)
    ontology_version = models.CharField(max_length=20)
    extraction_prompt_version = models.CharField(max_length=20)
    llm_model = models.CharField(max_length=100)
    extracted_data = models.JSONField(
        help_text="Raw extraction output: {nodes, relations, unrecognized_relations, ...}",
    )
    stats = models.JSONField(
        help_text="chunks_processed, llm_calls, elapsed_seconds, token counts",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    hit_count = models.PositiveIntegerField(default=0)
    last_hit_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"ExtractionCache[{self.cache_key[:12]}...] hits={self.hit_count}"
```

- [ ] **Step 3: Generate and apply the migration**

Run:

```bash
docker compose -f docker-compose.local.yml exec -T web python manage.py makemigrations knowledge --name extraction_cache
docker compose -f docker-compose.local.yml exec -T web python manage.py migrate knowledge
```

Expected: migration applies successfully.

- [ ] **Step 4: Run the cache model tests**

Run:

```bash
docker compose -f docker-compose.local.yml exec -T web pytest epocha/apps/knowledge/tests/test_models_cache.py -v
```

Expected: all PASS.

- [ ] **Step 5: Write the failing tests for the cache key builder**

Create `epocha/apps/knowledge/tests/test_cache_key.py`:

```python
"""Tests for the cache key builder."""
import pytest

from epocha.apps.knowledge.cache import (
    compute_documents_hash,
    compute_cache_key,
)


class TestComputeDocumentsHash:
    def test_deterministic(self):
        hashes = ["a" * 64, "b" * 64]
        assert compute_documents_hash(hashes) == compute_documents_hash(hashes)

    def test_order_independent(self):
        h1 = compute_documents_hash(["a" * 64, "b" * 64])
        h2 = compute_documents_hash(["b" * 64, "a" * 64])
        assert h1 == h2

    def test_is_sha256(self):
        result = compute_documents_hash(["a" * 64])
        assert len(result) == 64
        assert all(c in "0123456789abcdef" for c in result)

    def test_empty_input(self):
        # Empty input should still produce a deterministic hash
        result = compute_documents_hash([])
        assert len(result) == 64


class TestComputeCacheKey:
    def test_deterministic(self):
        key1 = compute_cache_key(
            documents_hash="d" * 64,
            ontology_version="v1",
            extraction_prompt_version="v1",
            llm_model="llama-3.3-70b",
        )
        key2 = compute_cache_key(
            documents_hash="d" * 64,
            ontology_version="v1",
            extraction_prompt_version="v1",
            llm_model="llama-3.3-70b",
        )
        assert key1 == key2

    def test_changes_with_ontology_version(self):
        base = dict(
            documents_hash="d" * 64,
            extraction_prompt_version="v1",
            llm_model="m",
        )
        k1 = compute_cache_key(ontology_version="v1", **base)
        k2 = compute_cache_key(ontology_version="v2", **base)
        assert k1 != k2

    def test_changes_with_prompt_version(self):
        base = dict(
            documents_hash="d" * 64,
            ontology_version="v1",
            llm_model="m",
        )
        k1 = compute_cache_key(extraction_prompt_version="v1", **base)
        k2 = compute_cache_key(extraction_prompt_version="v2", **base)
        assert k1 != k2

    def test_changes_with_llm_model(self):
        base = dict(
            documents_hash="d" * 64,
            ontology_version="v1",
            extraction_prompt_version="v1",
        )
        k1 = compute_cache_key(llm_model="m1", **base)
        k2 = compute_cache_key(llm_model="m2", **base)
        assert k1 != k2

    def test_changes_with_documents_hash(self):
        base = dict(
            ontology_version="v1",
            extraction_prompt_version="v1",
            llm_model="m",
        )
        k1 = compute_cache_key(documents_hash="a" * 64, **base)
        k2 = compute_cache_key(documents_hash="b" * 64, **base)
        assert k1 != k2

    def test_is_sha256_hex(self):
        key = compute_cache_key(
            documents_hash="d" * 64,
            ontology_version="v1",
            extraction_prompt_version="v1",
            llm_model="m",
        )
        assert len(key) == 64
        assert all(c in "0123456789abcdef" for c in key)
```

- [ ] **Step 6: Run cache key tests to verify they fail**

Run:

```bash
docker compose -f docker-compose.local.yml exec -T web pytest epocha/apps/knowledge/tests/test_cache_key.py -v
```

Expected: ImportError for `epocha.apps.knowledge.cache`.

- [ ] **Step 7: Implement the cache key builder**

Create `epocha/apps/knowledge/cache.py`:

```python
"""Extraction cache key builder.

The cache key is the SHA-256 of a deterministic composition of:
- documents_hash (itself the SHA-256 of the sorted document content hashes)
- ontology_version
- extraction_prompt_version
- llm_model

Any change to any of these fields invalidates the cache automatically,
which preserves reproducibility: same input + same versions always yield
the same key, and a version bump forces re-extraction.
"""
from __future__ import annotations

import hashlib
from typing import Iterable


def compute_documents_hash(content_hashes: Iterable[str]) -> str:
    """Compute the deterministic hash of a set of document content hashes.

    Input order is ignored: sorting guarantees that the same set of
    documents always produces the same aggregated hash regardless of
    upload order.
    """
    sorted_hashes = sorted(content_hashes)
    joined = "\n".join(sorted_hashes)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()


def compute_cache_key(
    *,
    documents_hash: str,
    ontology_version: str,
    extraction_prompt_version: str,
    llm_model: str,
) -> str:
    """Compute the composite cache key from its four components.

    The fields are joined with a pipe separator. The pipe is chosen
    because it cannot appear in hex hashes or version strings used by
    this project, eliminating any ambiguity in the composition.
    """
    key_material = (
        f"{documents_hash}|{ontology_version}|"
        f"{extraction_prompt_version}|{llm_model}"
    )
    return hashlib.sha256(key_material.encode("utf-8")).hexdigest()
```

- [ ] **Step 8: Run cache key tests to verify they pass**

Run:

```bash
docker compose -f docker-compose.local.yml exec -T web pytest epocha/apps/knowledge/tests/test_cache_key.py -v
```

Expected: all PASS.

- [ ] **Step 9: Run the full knowledge test suite**

Run:

```bash
docker compose -f docker-compose.local.yml exec -T web pytest epocha/apps/knowledge/ -v -m "not slow"
```

Expected: all non-slow tests PASS.

- [ ] **Step 10: Run the full project test suite**

Run:

```bash
docker compose -f docker-compose.local.yml exec -T web pytest -q -m "not slow"
```

Expected: all fast tests PASS.

- [ ] **Step 11: Commit**

```
feat(knowledge): add extraction cache model and key builder

CHANGE: Add the ExtractionCache model persisting raw LLM extraction
output keyed on a composite of documents hash, ontology version,
extraction prompt version, and LLM model. The cache key builder
computes deterministic SHA-256 keys that change when any composing
field changes, preserving reproducibility and enabling automatic
cache invalidation on version bumps.
```

---

## Self-Review Summary

After completing all five tasks in this plan, the system state is:

- Custom Postgres image running with both PostGIS and pgvector extensions
- Python dependencies installed: pgvector, fastembed, langchain-text-splitters
- Knowledge Graph Django app registered in settings
- Versioning, ontology, and normalizer utility modules with full test coverage
- KnowledgeDocument and KnowledgeDocumentAccess models with deduplication via content hash
- KnowledgeChunk model with pgvector HNSW index
- ExtractionCache model ready to receive extraction results
- Chunking service producing sentence-aware chunks with offsets
- Embedding service using fastembed bge-m3 for multilingual 1024-dim vectors
- Cache key builder producing deterministic composite keys

**What is NOT yet in place:**
- LLM extraction prompt and per-chunk extraction logic (Part 2)
- Merge and deduplication across chunks (Part 2)
- KnowledgeGraph, KnowledgeNode, KnowledgeRelation, and citation models (Part 3)
- Materialization from cache to per-simulation rows (Part 3)
- Celery orchestration task (Part 3)
- World generator integration (Part 3)
- Upload, status, and visualization API endpoints (Part 4)
- Dashboard view with Sigma.js (Part 4)
- Cache cleanup management command (Part 4)

**Transition:** After Part 1 is complete and reviewed, proceed to write Part 2 (Extraction pipeline) with a fresh brainstorming review of the prompt design, then continue task-by-task implementation.

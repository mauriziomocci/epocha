# Knowledge Graph Design Specification

**Date**: 2026-04-11
**Status**: Approved for implementation
**Authors**: design session with three-step critical review process

## Purpose and Scope

Build a scientifically rigorous Knowledge Graph extracted from user-uploaded
documents. The graph serves two complementary purposes:

1. **Improve agent generation** by feeding the world generator a structured,
   ontologically classified set of entities and relations instead of raw text
   or free-form prompts. Generated agents become coherent with the historical
   and thematic context of the source documents.
2. **Provide a rich visualization layer** showing hundreds of nodes (people,
   places, events, concepts, ideologies, norms, objects, values) and their
   relations, complementing the existing social graph.

**Out of scope for this iteration**: semantic retrieval from the graph during
live simulation (agents recalling graph facts tick-by-tick), natural language
search for users, tab-unification with the social graph, pre-generation
review UI for the extracted graph. All deferred to later features.

The graph is an integral part of the world generation pipeline, not a
decorative layer. When no documents are uploaded, generation falls back to
the existing prompt-only pipeline.

## Scientific Foundations

The design rests on established literature:

- **Ontology distinctions**: Searle, J. R. (1995). *The Construction of Social
  Reality*. Free Press. (Distinction between brute facts and institutional
  facts, ground for separating `person`/`group`/`institution` in the ontology.)
- **Historical event modeling**: CIDOC-CRM (ISO 21127:2014). The reference
  ontology for cultural heritage, basis for `event`, `place`, `object` modeling.
- **Concept vs ideology vs value**: Freeden, M. (1996). *Ideologies and
  Political Theory: A Conceptual Approach*. Oxford University Press.
  (Ideologies as clusters of political concepts; operational criteria for
  distinguishing `concept`, `ideology`, `value`, `norm`.)
- **Chunking strategy**: Lewis, P. et al. (2020). *Retrieval-Augmented
  Generation for Knowledge-Intensive NLP Tasks*. NeurIPS. (Foundation for
  chunk-based extraction; parameters adapted to 2024 standards.)
- **Multilingual embeddings**: Chen, J. et al. (2024). *BGE M3-Embedding:
  Multi-Lingual, Multi-Functionality, Multi-Granularity Text Embeddings*.
  arXiv:2402.03216. (Source for choice of BAAI/bge-m3 as embedding model.)
- **Entity deduplication**: standard practice in information extraction;
  embedding similarity threshold derived from MTEB benchmark evaluations.

## Architecture Overview

A new Django app `epocha.apps.knowledge` owns the entire Knowledge Graph
lifecycle: document ingestion, chunking, embedding, LLM extraction, caching,
materialization, and visualization queries.

The app sits upstream of world generation. `epocha.apps.world.generator`
depends on `knowledge` to build agent generation prompts from structured
graph data, but `knowledge` does not import from `world` or `agents`. The
linked fields on `KnowledgeNode` use string references, resolved at
runtime by Django.

### End-to-end pipeline

```
1. User uploads documents (one or more files)
   │
   ▼
2. knowledge: parse + normalize + hash each document
   (reuse existing document_parser.py)
   │
   ▼
3. knowledge: chunk each new document (recursive text splitter)
   parameters: 800 tokens per chunk, 150 overlap
   │
   ▼
4. knowledge: embed each chunk via fastembed (BAAI/bge-m3, 1024 dim)
   │
   ▼
5. knowledge: compute composite cache key and check ExtractionCache
   key = sha256(documents_hash || ontology_version ||
                extraction_prompt_version || llm_model)
   │
   ├── cache hit ─────────► skip to step 7
   │
   ▼
6. knowledge: Celery task extract_knowledge_graph
   for each chunk:
     LLM call with structured extraction prompt
     validate output against ontology and vocabulary
     collect nodes, relations, unrecognized_relations
   merge across chunks:
     normalize canonical names
     dedupe by embedding similarity (threshold 0.85)
     union source references, sum mention counts
   persist extracted_data to ExtractionCache
   │
   ▼
7. knowledge: materialize per-simulation graph
   create KnowledgeGraph(simulation=X, status="materializing")
   create KnowledgeNode rows
   create KnowledgeRelation rows
   create KnowledgeNodeCitation / KnowledgeRelationCitation rows
   set KnowledgeGraph.status = "ready"
   │
   ▼
8. world.generator: generate_world_from_prompt(simulation, graph)
   build agent generation prompt from graph.nodes filtered by entity_type
   LLM call for world/zones/agents
   for each generated entity:
     link back: node.linked_agent = agent, etc.
   │
   ▼
9. Simulation ready
   graph visible at /dashboard/simulation/<id>/knowledge-graph/
```

## Ontology

Ten entity types, ten relation categories, and three source types. The
design prioritizes operational distinguishability over theoretical purity:
every type must be reliably assignable by an LLM given clear criteria and
examples.

### Entity types

| Code | Type | Operational criterion | Example (French Revolution) |
|------|------|----------------------|----------------------------|
| `person` | Person | Individually identifiable historical human | Robespierre, Louis XVI, Marie Antoinette |
| `group` | Group | Informal social aggregate or movement without formalized roles | Sans-culottes, Girondins, Jacobins as movement |
| `place` | GeographicPlace | Physical location with potential coordinates | Versailles, Faubourg Saint-Antoine, Paris |
| `institution` | Institution | Formalized organization with defined roles, procedures, continuity | National Assembly, Committee of Public Safety, Jacobin Club as institution |
| `event` | HistoricalEvent | Datable occurrence with actors and location | Storming of the Bastille, Reign of Terror, Flight to Varennes |
| `concept` | AbstractConcept | Political-philosophical idea usable as a building block for ideologies | Liberty, Reason, Virtue, Equality, Popular sovereignty |
| `ideology` | Ideology | Coherent political system configuring concepts into a vision | Jacobinism, Liberal monarchism, Girondism |
| `object` | MaterialObject | Physically existing artifact with historical significance | Guillotine, Phrygian cap, tricolor cockade |
| `norm` | NormOrLaw | Codified rule, law, or explicit decree | Declaration of the Rights of Man, Law of Suspects, Constitution of 1791 |
| `value` | CulturalValue | Cultural commitment of everyday life, not a political system | Noble honor, piety, frugality, Fraternité as lived value |

The distinction between `concept`, `ideology`, `value`, and `norm` follows
Freeden (1996): concepts are building blocks, ideologies are coherent
configurations of concepts into political visions, values are everyday
cultural commitments, norms are codified rules. The extraction prompt
includes these operational criteria with at least three examples per type.

### Relation vocabulary (controlled)

Eighteen relation types grouped by category. Any LLM output using a
different type is dropped and logged in
`ExtractionCache.extracted_data.unrecognized_relations` for future
vocabulary review.

| Category | Code | Meaning |
|----------|------|---------|
| Membership | `member_of` | X is member of group/institution Y |
| Membership | `founder_of` | X founded Y |
| Membership | `leader_of` | X leads Y |
| Spatial | `located_in` | X is located in place Y |
| Spatial | `occurred_in` | event X occurred in place Y |
| Temporal | `occurred_during` | event X occurred during event/period Y |
| Belief | `believes_in` | X believes in ideology/concept Y |
| Belief | `opposes` | X opposes Y |
| Belief | `supports` | X supports Y |
| Social | `ally_of` | X is ally of Y (symmetric semantics) |
| Social | `enemy_of` | X is enemy of Y (symmetric semantics) |
| Social | `kin_of` | X is family of Y (symmetric semantics) |
| Social | `influences` | X influences Y (asymmetric) |
| Causal | `caused_by` | event X was caused by Y |
| Causal | `led_to` | X led to Y |
| Participation | `participated_in` | X participated in event Y |
| Production | `authored` | X authored object Y |
| Production | `enacted` | X enacted norm Y |

### Source types

Every node and every relation carries a `source_type` field with one of:

- `document`: literal mention in a document with explicit citation
- `document_inferred`: derived from document context (not a literal
  statement but a reasonable inference from the passage)
- `llm_knowledge`: added by the model from its pre-training knowledge
  during the research-agent enrichment step

This distinction is enforced at the LLM prompt level: the model must pick
one value per item and justify its choice in the description field.

## Data Model

### Shared tier (cross-simulation reuse)

```python
# epocha/apps/knowledge/models.py

from pgvector.django import VectorField, HnswIndex
from django.db import models
from django.conf import settings


class KnowledgeDocument(models.Model):
    """Uploaded source document, deduplicated across simulations by content hash."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="knowledge_documents",
    )
    title = models.CharField(max_length=255)
    mime_type = models.CharField(max_length=50)
    content_hash = models.CharField(
        max_length=64, unique=True, db_index=True,
        help_text="SHA-256 of normalized text content",
    )
    normalized_text = models.TextField()
    char_count = models.PositiveIntegerField()
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} ({self.char_count} chars)"


class KnowledgeChunk(models.Model):
    """A text chunk of a document with its embedding, reused across graphs."""

    document = models.ForeignKey(
        KnowledgeDocument, on_delete=models.CASCADE, related_name="chunks",
    )
    chunk_index = models.PositiveIntegerField()
    text = models.TextField()
    start_char = models.PositiveIntegerField()
    end_char = models.PositiveIntegerField()
    embedding = VectorField(dimensions=1024)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("document", "chunk_index")
        indexes = [
            HnswIndex(
                name="chunk_embedding_hnsw",
                fields=["embedding"],
                m=16,
                ef_construction=64,
                opclasses=["vector_cosine_ops"],
            ),
        ]


class ExtractionCache(models.Model):
    """Cache of the expensive LLM extraction step.

    Keyed by the composite of documents hash, ontology version, extraction
    prompt version, and LLM model. Any change to these invalidates the
    cache automatically, preventing stale results from contaminating new
    simulations.
    """

    cache_key = models.CharField(max_length=64, primary_key=True)
    documents_hash = models.CharField(max_length=64, db_index=True)
    ontology_version = models.CharField(max_length=20)
    extraction_prompt_version = models.CharField(max_length=20)
    llm_model = models.CharField(max_length=100)
    extracted_data = models.JSONField(
        help_text="Raw extraction output: {nodes, relations, unrecognized_relations}",
    )
    stats = models.JSONField(
        help_text="chunks_processed, llm_calls, elapsed_seconds, token_count",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    hit_count = models.PositiveIntegerField(default=0)
    last_hit_at = models.DateTimeField(null=True, blank=True)
```

### Per-simulation tier (materialized graph)

```python
class KnowledgeGraph(models.Model):
    """Materialized knowledge graph for a single simulation.

    Nodes and relations are cloned from the extraction cache into this
    graph at materialization time. Each simulation gets its own isolated
    set of rows; the cache only holds the LLM extraction output, not the
    materialized graph.
    """

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("extracting", "Extracting"),
        ("materializing", "Materializing"),
        ("ready", "Ready"),
        ("failed", "Failed"),
    ]

    simulation = models.OneToOneField(
        "simulation.Simulation", on_delete=models.CASCADE,
        related_name="knowledge_graph",
    )
    documents = models.ManyToManyField(KnowledgeDocument, related_name="graphs")
    extraction_cache = models.ForeignKey(
        ExtractionCache, on_delete=models.PROTECT, related_name="graphs",
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    materialized_at = models.DateTimeField(null=True, blank=True)


class KnowledgeNode(models.Model):
    """A single entity in the knowledge graph.

    Nodes carry the full ontology classification, provenance, confidence,
    and embedding for semantic retrieval. Links to simulation models are
    nullable and set after the world generator produces the live entities.
    """

    ENTITY_TYPES = [
        ("person", "Person"),
        ("group", "Group"),
        ("place", "Geographic Place"),
        ("institution", "Institution"),
        ("event", "Historical Event"),
        ("concept", "Abstract Concept"),
        ("ideology", "Ideology"),
        ("object", "Material Object"),
        ("norm", "Norm or Law"),
        ("value", "Cultural Value"),
    ]

    SOURCE_TYPES = [
        ("document", "Document (literal)"),
        ("document_inferred", "Document inferred"),
        ("llm_knowledge", "LLM knowledge"),
    ]

    graph = models.ForeignKey(
        KnowledgeGraph, on_delete=models.CASCADE, related_name="nodes",
    )
    entity_type = models.CharField(max_length=20, choices=ENTITY_TYPES)
    name = models.CharField(max_length=255)
    canonical_name = models.CharField(max_length=255, db_index=True)
    description = models.TextField(blank=True)
    attributes = models.JSONField(default=dict)
    source_type = models.CharField(max_length=20, choices=SOURCE_TYPES)
    confidence = models.FloatField(default=1.0)
    mention_count = models.PositiveIntegerField(default=1)
    embedding = VectorField(dimensions=1024)

    linked_agent = models.ForeignKey(
        "agents.Agent", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="knowledge_nodes",
    )
    linked_group = models.ForeignKey(
        "agents.Group", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="knowledge_nodes",
    )
    linked_zone = models.ForeignKey(
        "world.Zone", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="knowledge_nodes",
    )
    linked_event = models.ForeignKey(
        "simulation.Event", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="knowledge_nodes",
    )
    linked_institution = models.ForeignKey(
        "world.Institution", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="knowledge_nodes",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("graph", "entity_type", "canonical_name")
        indexes = [
            models.Index(fields=["graph", "entity_type"]),
            HnswIndex(
                name="node_embedding_hnsw",
                fields=["embedding"],
                m=16,
                ef_construction=64,
                opclasses=["vector_cosine_ops"],
            ),
        ]


class KnowledgeRelation(models.Model):
    """A directed relation between two nodes with optional temporal scope."""

    RELATION_TYPES = [
        ("member_of", "member of"),
        ("founder_of", "founder of"),
        ("leader_of", "leader of"),
        ("located_in", "located in"),
        ("occurred_in", "occurred in"),
        ("occurred_during", "occurred during"),
        ("believes_in", "believes in"),
        ("opposes", "opposes"),
        ("supports", "supports"),
        ("ally_of", "ally of"),
        ("enemy_of", "enemy of"),
        ("kin_of", "kin of"),
        ("influences", "influences"),
        ("caused_by", "caused by"),
        ("led_to", "led to"),
        ("participated_in", "participated in"),
        ("authored", "authored"),
        ("enacted", "enacted"),
    ]

    graph = models.ForeignKey(
        KnowledgeGraph, on_delete=models.CASCADE, related_name="relations",
    )
    source_node = models.ForeignKey(
        KnowledgeNode, on_delete=models.CASCADE, related_name="outgoing_relations",
    )
    target_node = models.ForeignKey(
        KnowledgeNode, on_delete=models.CASCADE, related_name="incoming_relations",
    )
    relation_type = models.CharField(max_length=30, choices=RELATION_TYPES)
    description = models.TextField(blank=True)
    source_type = models.CharField(max_length=20, choices=KnowledgeNode.SOURCE_TYPES)
    confidence = models.FloatField(default=1.0)
    weight = models.FloatField(default=0.5)

    temporal_start_iso = models.CharField(max_length=20, blank=True)
    temporal_start_year = models.IntegerField(null=True, blank=True, db_index=True)
    temporal_end_iso = models.CharField(max_length=20, blank=True)
    temporal_end_year = models.IntegerField(null=True, blank=True, db_index=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["graph", "source_node"]),
            models.Index(fields=["graph", "target_node"]),
            models.Index(fields=["graph", "relation_type"]),
        ]


class KnowledgeNodeCitation(models.Model):
    """Citation linking a node back to a specific chunk with passage excerpt."""

    node = models.ForeignKey(
        KnowledgeNode, on_delete=models.CASCADE, related_name="citations",
    )
    chunk = models.ForeignKey(
        KnowledgeChunk, on_delete=models.CASCADE, related_name="node_citations",
    )
    passage_excerpt = models.CharField(max_length=500)

    class Meta:
        unique_together = ("node", "chunk")


class KnowledgeRelationCitation(models.Model):
    """Citation linking a relation back to a specific chunk with passage excerpt."""

    relation = models.ForeignKey(
        KnowledgeRelation, on_delete=models.CASCADE, related_name="citations",
    )
    chunk = models.ForeignKey(
        KnowledgeChunk, on_delete=models.CASCADE, related_name="relation_citations",
    )
    passage_excerpt = models.CharField(max_length=500)

    class Meta:
        unique_together = ("relation", "chunk")
```

## Extraction Pipeline

The extraction runs as a Celery task `extract_knowledge_graph(documents_ids)`.
On completion it enqueues world generation with the materialized graph.

### Stage 1: document ingestion and normalization

For each uploaded file:

1. Parse via existing `world.document_parser.extract_text`
2. Normalize: strip BOM, normalize whitespace to single spaces, Unicode NFC
3. Compute SHA-256 of normalized text
4. `get_or_create(KnowledgeDocument, content_hash=hash, defaults=...)` in a
   transaction to handle concurrent uploads

### Stage 2: chunking

For each new `KnowledgeDocument` (only if just created):

1. Use `langchain_text_splitters.RecursiveCharacterTextSplitter` with:
   - `chunk_size = 800 * 4` characters (approximately 800 tokens at the
     standard 4-chars-per-token ratio)
   - `chunk_overlap = 150 * 4` characters
   - `separators = ["\n\n", "\n", ". ", " ", ""]` for sentence-aware splits
2. For each chunk: record `start_char`, `end_char`, and text
3. Enforce `MAX_CHUNKS_PER_DOCUMENT = 50` limit (configurable via settings).
   Documents exceeding the limit generate a warning and are truncated after
   the limit.

### Stage 3: chunk embedding

For each chunk without an embedding:

1. Load the `BAAI/bge-m3` model once per task via `fastembed`
2. Batch embed chunks in groups of 10 for efficiency
3. Store the 1024-dimensional vector on the `KnowledgeChunk.embedding` field
4. Embeddings are reproducible: same text plus same model version always
   yield the same vector

### Stage 4: extraction cache check

1. Compute `documents_hash = sha256(sorted([doc.content_hash for doc in docs]))`
2. Compute `cache_key = sha256(documents_hash || ontology_version ||
   extraction_prompt_version || llm_model)`
3. `ExtractionCache.objects.filter(cache_key=cache_key).first()`
4. If hit: increment `hit_count`, set `last_hit_at`, skip to Stage 6

### Stage 5: per-chunk LLM extraction

For each chunk in the documents:

1. Build the extraction prompt:
   - System prompt: ontology definitions (10 types with operational criteria
     and 3+ examples each), relation vocabulary (18 types), source type rules,
     JSON output schema
   - User prompt: the chunk text plus instruction "cite the exact passage
     supporting each extracted item"
2. Call the LLM client (`get_llm_client`) with temperature 0.1 for
   reproducibility
3. Parse the JSON output using `clean_llm_json`
4. Validate against ontology:
   - Drop entities with unknown `entity_type`, log them
   - Drop relations with unknown `relation_type`, append to
     `unrecognized_relations` list
   - Drop items without a `passage_excerpt`

Collect per-chunk results into a merge buffer.

### Stage 6: merge and deduplication

1. Normalize `canonical_name` for each entity:
   - Lowercase
   - Strip accents via Unicode NFD then filter combining marks
   - Strip titles like "M.", "Dr.", "Mrs."
   - Collapse whitespace
2. Group entities by `entity_type`, then iterate and deduplicate:
   - Within each group, embed `name + " " + description` via bge-m3
   - Pairs with cosine similarity above `DEDUP_THRESHOLD = 0.85` are merged
   - Merged entity: union `source_refs`, max `confidence`, sum `mention_count`
3. Deduplicate relations by `(source_canonical, target_canonical,
   relation_type, temporal_start_year, temporal_end_year)` tuple
4. Package the merged output into a JSON structure ready for the cache:
   ```json
   {
     "nodes": [...],
     "relations": [...],
     "unrecognized_relations": [...],
     "stats": {...}
   }
   ```

### Stage 7: persist to cache

```python
ExtractionCache.objects.create(
    cache_key=cache_key,
    documents_hash=documents_hash,
    ontology_version="v1",
    extraction_prompt_version="v1",
    llm_model=llm.get_model_name(),
    extracted_data=merged_data,
    stats=stats,
)
```

### Stage 8: materialize per-simulation graph

```python
graph = KnowledgeGraph.objects.create(
    simulation=simulation,
    extraction_cache=cache_entry,
    status="materializing",
)
graph.documents.set(documents)

# Bulk create nodes with deferred FK resolution
for node_data in merged_data["nodes"]:
    KnowledgeNode.objects.create(graph=graph, ...)

# Then relations, using the created node IDs
for rel_data in merged_data["relations"]:
    KnowledgeRelation.objects.create(
        graph=graph,
        source_node=node_by_canonical[rel_data["source"]],
        target_node=node_by_canonical[rel_data["target"]],
        ...,
    )

# Then citations
for citation_data in merged_data["node_citations"]:
    KnowledgeNodeCitation.objects.create(...)

graph.status = "ready"
graph.materialized_at = timezone.now()
graph.save(update_fields=["status", "materialized_at"])
```

### Stage 9: trigger world generation

The task that runs the extraction enqueues `generate_world_from_knowledge_graph`
as the next step. This is a new function in `epocha.apps.world.generator`
that replaces `generate_world_from_prompt` for the document-driven flow.

## World Generation Integration

The existing `generate_world_from_prompt` is refactored to accept an optional
`knowledge_graph` parameter:

```python
def generate_world_from_prompt(prompt, simulation, knowledge_graph=None):
    if knowledge_graph is not None:
        return _generate_from_graph(simulation, knowledge_graph)
    return _generate_from_prompt_only(prompt, simulation)
```

When called with a graph, the agent generation prompt is built from the
structured data:

```
SYSTEM: You are generating agents for a civilization simulation.

The historical context is defined by the following knowledge graph.

PERSONS (will become agents):
- Robespierre: description... | believes in Jacobinism, Virtue, Reason |
  member of Jacobin Club, Committee of Public Safety
- Louis XVI: description... | believes in Divine Right | head of
  French Monarchy
- ...

PLACES (will become zones):
- Versailles: description...
- Paris centre: description...

INSTITUTIONS:
- National Assembly: description...
- Committee of Public Safety: description...

EVENTS IN RECENT CONTEXT:
- Storming of the Bastille (1789-07-14)
- Flight to Varennes (1791-06-20)

IDEOLOGIES ACTIVE:
- Jacobinism: description...
- Liberal Monarchism: description...

Generate personality profiles for each person consistent with their
described beliefs, group memberships, and the ideological climate.
```

After the LLM produces the agents, the generator code sets the link fields
on the graph nodes:

```python
for person_node in graph.nodes.filter(entity_type="person"):
    agent = Agent.objects.create(
        simulation=simulation,
        name=person_node.name,
        personality=llm_response["personalities"][person_node.canonical_name],
        ...,
    )
    person_node.linked_agent = agent
    person_node.save(update_fields=["linked_agent"])
```

Same pattern for zones, groups, institutions.

## Visualization

A new route `GET /dashboard/simulation/<id>/knowledge-graph/` renders the
graph using Sigma.js, following the same pattern as the existing social
graph page.

Initial load strategy for scalability:

- Top 100 nodes by `mention_count` (plus their connecting relations)
- Nodes filtered by `entity_type` via UI toggles (all 10 types on by default)
- "Load more" button progressively fetches additional nodes ordered by
  mention count
- Detail panel on node click showing description, source citations, and
  linked simulation entity (if any)

Node colors by `entity_type`, edge colors by `relation_type` category
(membership, spatial, belief, social, causal, production). Force Atlas 2
layout via the inline JS adapted from the social graph page.

## Configuration and Versioning

A new module `epocha/apps/knowledge/versions.py`:

```python
ONTOLOGY_VERSION = "v1"              # 10 entity types + 18 relations
EXTRACTION_PROMPT_VERSION = "v1"     # increments on prompt changes
EMBEDDING_MODEL = "BAAI/bge-m3"
EMBEDDING_DIM = 1024
CHUNK_SIZE_TOKENS = 800
CHUNK_OVERLAP_TOKENS = 150
CHUNK_CHARS_PER_TOKEN = 4            # approximate, used for char-based splitter
MAX_CHUNKS_PER_DOCUMENT = 50
DEDUP_SIMILARITY_THRESHOLD = 0.85
EXTRACTION_TEMPERATURE = 0.1
```

Any change to these values increments the relevant version and automatically
invalidates the extraction cache. This preserves reproducibility while
allowing controlled evolution.

Django settings exposed via `django-environ`:

```python
EPOCHA_KG_ENABLED = env.bool("EPOCHA_KG_ENABLED", default=True)
EPOCHA_KG_MAX_CHUNKS_PER_DOC = env.int("EPOCHA_KG_MAX_CHUNKS_PER_DOC", default=50)
EPOCHA_KG_EMBEDDING_BATCH_SIZE = env.int("EPOCHA_KG_EMBEDDING_BATCH_SIZE", default=10)
```

## Dependencies

Additions to `requirements/base.txt`:

```
pgvector==0.3.6
fastembed==0.3.6
langchain-text-splitters==0.2.2
```

- `pgvector` is the Django integration for Postgres vector operations (using
  the `pgvector` Postgres extension already required by the earlier PostGIS
  migration path).
- `fastembed` provides ONNX-based embeddings without the torch dependency
  chain, keeping the Docker image under 500 MB overhead.
- `langchain-text-splitters` is the standalone text splitting package
  extracted from langchain, with minimal dependencies.

The Postgres `vector` extension must be enabled:

```python
# In a migration
from django.db import migrations
from pgvector.django import VectorExtension

operations = [
    VectorExtension(),
]
```

This runs in addition to the existing PostGIS extension.

## Error Handling and Observability

- Extraction failures (LLM returns unparsable output, rate limit hit) are
  retried up to 3 times per chunk. Final failures are logged and the chunk
  contributes an empty result to the merge buffer.
- A `KnowledgeGraph` with `status="failed"` carries the error message in
  `error_message` for user-facing display.
- Celery task progress is broadcast via WebSocket to the simulation channel
  so the user sees "extracting chunk 12/50" in real time.
- Logging via standard Django logger at info level for task lifecycle and
  warning level for dropped entities/relations.

## Testing Strategy

- Unit tests for the ontology validator (accepts all 10 types, rejects
  others, validates source_type)
- Unit tests for the canonical name normalizer (accent stripping, title
  removal, whitespace collapse)
- Integration test for the full pipeline using a fixed small document, a
  mocked LLM returning deterministic output, and fastembed with the real
  model: verify the resulting graph structure matches expectations
- Test for cache hit: run extraction twice on the same documents, assert
  only one LLM call path was exercised
- Test for cache invalidation: change `ONTOLOGY_VERSION`, assert a new
  extraction runs
- Test for concurrent uploads: two simultaneous `get_or_create` on the
  same content_hash should produce only one `KnowledgeDocument` row
- Test for relation vocabulary: LLM returns an unknown relation type,
  assert it lands in `unrecognized_relations` and not in the graph

All tests use PostgreSQL with pgvector. No SQLite.

## Migration Path

The feature is additive: existing simulations are unaffected. The flag
`EPOCHA_KG_ENABLED` allows emergency disabling without code changes. The
Express endpoint gains a new "Upload documents" flow that runs the
Knowledge Graph extraction before generating the world. The old
prompt-only flow remains available for users who do not upload documents.

## Known Limitations

- Documents longer than 50 chunks are truncated. The limit is configurable
  but high values lead to long extraction times.
- Relations are extracted per chunk; cross-chunk relations (e.g., "Robespierre
  authored the Declaration" where the two entities are mentioned in
  different chunks) can only be produced by the research-agent enrichment
  phase, not the primary extraction.
- The dedup similarity threshold is a heuristic calibrated for historical
  texts in European languages. Specialized domains may require tuning.
- Temporal parsing is string-based with year extraction for range queries.
  Month and day precision are preserved in the ISO string for display but
  not queryable.

## Out of Scope Reminder

Not in this iteration, deferred to follow-up features:

- Retrieval of graph facts into agent memories during simulation ticks
- Natural language search over the graph by end users
- Tab unification with the social graph page
- Pre-generation review UI for the extracted graph
- Cross-chunk relation extraction beyond per-chunk LLM calls
- Advanced visualization features (community detection, knowledge pruning,
  timeline view)

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
  the embedding similarity threshold of 0.85 is an initial heuristic
  without a specific empirical derivation, to be recalibrated after
  observing actual extraction quality on representative documents.
- **HNSW index tuning**: Malkov, Y. A., & Yashunin, D. A. (2018).
  *Efficient and robust approximate nearest neighbor search using
  Hierarchical Navigable Small World graphs*. IEEE Transactions on
  Pattern Analysis and Machine Intelligence. (Source of the default
  HNSW parameters `m=16, ef_construction=64`.)

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
| `group` | Group | Informal social aggregate or movement without formalized roles | Sans-culottes, Girondins |
| `place` | GeographicPlace | Physical location with potential coordinates | Versailles, Faubourg Saint-Antoine, Paris |
| `institution` | Institution | Formalized organization with defined roles, procedures, continuity | National Assembly, Committee of Public Safety, Jacobin Club |
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

**Disambiguation rule for overlapping types**: some real-world entities
legitimately satisfy more than one type. The Jacobin Club, for example, is
both an organized institution and the social movement of jacobins. To
ensure consistent extraction, the prompt instructs the LLM to pick the
**most specific formalization level** available when multiple types fit,
in this priority order (high to low):

1. `institution` (formalized roles and procedures)
2. `group` (organized social aggregate without formal procedures)
3. `concept` or `ideology` (abstract rather than concrete)

Applied to the example: the Jacobin Club is extracted as `institution`
because it has formalized membership and procedures, not as `group` even
though it is also a social movement. The same rule resolves place/object
ambiguities ("the Bastille" is extracted as `place` when referring to the
fortress, as `event` when the storming is referenced).

### Relation vocabulary (controlled)

Twenty relation types grouped by category. Any LLM output using a
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
| Social | `influences` | X influences Y (asymmetric) |
| Kinship | `married_to` | X is married to Y (symmetric) |
| Kinship | `parent_of` | X is parent of Y (asymmetric) |
| Kinship | `sibling_of` | X is sibling of Y (symmetric) |
| Causal | `caused_by` | event X was caused by Y |
| Causal | `led_to` | X led to Y |
| Participation | `participated_in` | X participated in event Y |
| Production | `authored` | X authored object Y |
| Production | `enacted` | X enacted norm Y |

The kinship category replaces the earlier `kin_of` umbrella with three
specific relations. For historical scenarios, genealogical detail
(marriage, parentage, sibling ties) carries significant political weight
and should be preserved rather than collapsed. Any other family relation
(cousin, uncle, in-law) is dropped to the unrecognized log and should be
added in v2 if it proves frequent enough to justify.

### Source types

Every node and every relation carries a `source_type` field with one of
two values:

- `document`: the entity or relation is mentioned literally in a document
  passage and the passage contains the entity name verbatim
- `document_inferred`: derived from document context (a reasonable
  inference from the surrounding passage, but the entity name is not
  literally present in the citation)

The distinction is assigned **mechanically after extraction**, not by
asking the LLM to self-report. Self-reported provenance is unreliable in
practice. The rule is deterministic:

- If `passage_excerpt` is present and contains the entity `name` (case-
  insensitive, accent-insensitive substring match): `source_type = document`
- If `passage_excerpt` is present but does not contain the entity name:
  `source_type = document_inferred`
- If `passage_excerpt` is absent: the item is dropped entirely (we only
  accept extractions with evidence)

A third source type `llm_knowledge` (facts added from the LLM's
pre-training knowledge via a separate enrichment step) is explicitly
**out of scope** for this iteration. Its integration with the existing
`agents.research` module will be designed and implemented as a follow-up
feature. Only `document` and `document_inferred` exist in the MVP.

## Data Model

### Shared tier (cross-simulation reuse)

```python
# epocha/apps/knowledge/models.py

from pgvector.django import VectorField, HnswIndex
from django.db import models
from django.conf import settings


class KnowledgeDocument(models.Model):
    """Uploaded source document, deduplicated across users and simulations
    by content hash.

    Ownership and access control are decoupled from the document entity
    itself: two users uploading the same content share a single row via
    content_hash uniqueness, and their access is tracked through
    KnowledgeDocumentAccess. This prevents CASCADE deletions from removing
    documents that other users are actively using.
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
    """Tracks which users have uploaded/accessed a specific document.

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
        ("influences", "influences"),
        ("married_to", "married to"),
        ("parent_of", "parent of"),
        ("sibling_of", "sibling of"),
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
            models.Index(fields=["graph", "temporal_start_year", "temporal_end_year"]),
        ]

    def clean(self):
        """Validate that both endpoints belong to the same graph as this relation."""
        from django.core.exceptions import ValidationError
        if self.source_node.graph_id != self.graph_id:
            raise ValidationError("source_node must belong to the same graph")
        if self.target_node.graph_id != self.graph_id:
            raise ValidationError("target_node must belong to the same graph")


class KnowledgeNodeCitation(models.Model):
    """Citation linking a node back to a specific chunk with passage excerpt."""

    node = models.ForeignKey(
        KnowledgeNode, on_delete=models.CASCADE, related_name="citations",
    )
    chunk = models.ForeignKey(
        KnowledgeChunk, on_delete=models.CASCADE, related_name="node_citations",
    )
    passage_excerpt = models.TextField()

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
    passage_excerpt = models.TextField()

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
3. Enforce `MAX_DOCUMENT_CHARS = 500000` limit (configurable). Documents
   exceeding the limit raise a user-facing validation error before any
   further processing.
4. Compute SHA-256 of normalized text
5. `get_or_create(KnowledgeDocument, content_hash=hash, defaults=...)`;
   rely on the unique constraint on `content_hash` to handle concurrent
   uploads (catch `IntegrityError` and re-fetch the existing row)
6. Create or get the `KnowledgeDocumentAccess` row linking the current
   user to the document

### Stage 2: chunking (idempotent)

For each document, regardless of whether it was just created or already
existed:

1. Check `if not document.chunks.exists()`. Skip if chunks already exist.
2. If no chunks exist, produce them with
   `langchain_text_splitters.RecursiveCharacterTextSplitter`:
   - `chunk_size = CHUNK_SIZE_TOKENS * CHUNK_CHARS_PER_TOKEN` characters
     (default: 800 tokens approximated at 4 chars/token)
   - `chunk_overlap = CHUNK_OVERLAP_TOKENS * CHUNK_CHARS_PER_TOKEN`
   - `separators = ["\n\n", "\n", ". ", "; ", " — ", " ", ""]` for
     sentence-aware splits handling dialog dashes and semicolons common
     in European historical texts
3. For each chunk: record `start_char`, `end_char`, and text
4. Enforce `MAX_CHUNKS_PER_DOCUMENT = 50` limit. Documents exceeding the
   limit are truncated after the limit and a warning is broadcast to the
   user via WebSocket.

Idempotency rationale: a crash between document creation and chunk creation
must not leave the document permanently unchunked. Re-running the pipeline
must always converge to the correct state.

### Stage 3: chunk embedding (idempotent)

For each chunk that was just created in Stage 2:

1. Load the `BAAI/bge-m3` model once per task via `fastembed` (the model
   is cached globally by fastembed after the first load, ~5 seconds cold
   start, then near-zero for subsequent calls within the same process)
2. Batch embed chunks in groups of `EPOCHA_KG_EMBEDDING_BATCH_SIZE`
   (default 10)
3. Store the 1024-dimensional vector on the `KnowledgeChunk.embedding`
   field at chunk creation time (embedding is not-nullable, so the chunk
   row is only INSERTed once the embedding is computed)
4. Embeddings are reproducible by construction: fastembed pins the ONNX
   model weights to a specific revision; the same text plus same model
   version always yields the same vector.

Since chunks are only created when none exist (Stage 2 idempotent check),
and embeddings are computed atomically with chunk creation, re-running
the pipeline never re-embeds already-persisted chunks.

### Stage 4: extraction cache check

1. Compute the aggregated documents hash:
   ```python
   doc_hashes = sorted(doc.content_hash for doc in docs)
   documents_hash = hashlib.sha256(
       "\n".join(doc_hashes).encode("utf-8")
   ).hexdigest()
   ```
2. Compute the composite cache key:
   ```python
   key_material = f"{documents_hash}|{ONTOLOGY_VERSION}|" \
                  f"{EXTRACTION_PROMPT_VERSION}|{llm_model}"
   cache_key = hashlib.sha256(key_material.encode("utf-8")).hexdigest()
   ```
3. `ExtractionCache.objects.filter(pk=cache_key).first()`
4. If hit: increment `hit_count`, set `last_hit_at`, skip to Stage 8
   (materialization); Stages 5-7 are bypassed.

### Stage 5: per-chunk LLM extraction

For each chunk in the documents:

1. Build the extraction prompt:
   - **System prompt** includes: ontology definitions (10 types with
     operational criteria and at least 3 examples each), disambiguation
     rule (institution > group > concept/ideology), relation vocabulary
     (20 types), JSON output schema, multilingual instruction ("The
     document may be in any European language. Keep entity `name` values
     in the original language of the document; provide the `description`
     and `passage_excerpt` in the original language as well, without
     translation").
   - **User prompt** is the chunk text plus instruction: "Extract entities
     and relations present in or directly inferable from this passage.
     Cite the exact excerpt from the passage that supports each extracted
     item in `passage_excerpt`. Do NOT extract facts from your general
     knowledge that are not supported by the passage."
2. Call the LLM client (`get_llm_client`) with `temperature=0.1` for
   reproducibility
3. Parse the JSON output using `clean_llm_json`
4. Validate and enrich each extracted item:
   - Drop entities with unknown `entity_type`, log them to
     `unrecognized_entities`
   - Drop entities without a `passage_excerpt` (no evidence, no entry)
   - Drop relations with unknown `relation_type`, append to
     `unrecognized_relations`
   - Drop relations without a `passage_excerpt`
   - **Assign `source_type` mechanically**: compute a normalized,
     accent-stripped, case-insensitive substring check of the entity
     `name` inside `passage_excerpt`. If the name is literally present:
     `source_type = "document"`. Otherwise: `source_type = "document_inferred"`.

Collect validated items into a per-chunk result buffer tagged with the
chunk id for citation.

### Stage 6: merge and deduplication

1. Normalize `canonical_name` for each extracted entity:
   - Lowercase
   - Strip accents via Unicode NFD then filter combining marks
   - Strip honorific titles (`M.`, `Dr.`, `Mrs.`, `Mme.`, `Citoyen`,
     `Citoyenne`)
   - Collapse consecutive whitespace to single spaces
   - Trim leading and trailing whitespace
2. Group entities by `entity_type` (never merge across types, even if
   names are similar)
3. Within each type group, compute pairwise similarity and merge:
   - Embed `f"{name} {description}"` via bge-m3 for each candidate
   - Build an N×N cosine similarity matrix
   - Perform single-linkage clustering with threshold
     `DEDUP_SIMILARITY_THRESHOLD = 0.85` (pairs above threshold become
     the same cluster, transitively)
4. Apply merge rules per cluster to produce a single merged entity:
   - `name` = name of the cluster member with the highest mention_count;
     tie-break by longest string length, then alphabetical order
   - `canonical_name` = the normalized form of the chosen `name`
   - `description` = concatenation of unique non-empty descriptions from
     all cluster members, separated by " | ", truncated to 2000 characters
   - `source_type` = "document" if any cluster member has it, else
     "document_inferred"
   - `confidence` = max confidence across members
   - `mention_count` = sum of mention counts across members
   - `attributes` = dict-merge across members; on key collision, keep the
     value from the highest-confidence member
   - `embedding` = re-computed on the final merged `f"{name} {description}"`
     via bge-m3 (not the average of input vectors)
   - `citations` = union of all citations from all cluster members
5. Deduplicate relations by the tuple
   `(source_canonical_name, source_entity_type, target_canonical_name,
   target_entity_type, relation_type, temporal_start_year,
   temporal_end_year)`. Duplicate relations take the max confidence, max
   weight, and union of citations.
6. Package the merged output into a JSON structure ready for the cache:
   ```json
   {
     "nodes": [...],
     "relations": [...],
     "unrecognized_entities": [...],
     "unrecognized_relations": [...],
     "stats": {
       "chunks_processed": 42,
       "llm_calls": 42,
       "elapsed_seconds": 58.3,
       "token_count_input": 123456,
       "token_count_output": 34567,
       "nodes_before_merge": 312,
       "nodes_after_merge": 187,
       "relations_before_merge": 450,
       "relations_after_merge": 289
     }
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

The materialization step turns the cached extraction output into
relational rows scoped to a single simulation. It runs inside a database
transaction so the graph is either fully created or not at all.

```python
from django.db import transaction

with transaction.atomic():
    graph = KnowledgeGraph.objects.create(
        simulation=simulation,
        extraction_cache=cache_entry,
        status="materializing",
    )
    graph.documents.set(documents)

    # Pass 1: create nodes, keyed by (entity_type, canonical_name) to
    # avoid collisions between different types sharing the same canonical
    # form (e.g., "paris" as place AND as concept).
    node_index: dict[tuple[str, str], KnowledgeNode] = {}
    for node_data in merged_data["nodes"]:
        node = KnowledgeNode.objects.create(
            graph=graph,
            entity_type=node_data["entity_type"],
            name=node_data["name"],
            canonical_name=node_data["canonical_name"],
            description=node_data["description"],
            attributes=node_data.get("attributes", {}),
            source_type=node_data["source_type"],
            confidence=node_data["confidence"],
            mention_count=node_data["mention_count"],
            embedding=node_data["embedding"],
        )
        node_index[(node.entity_type, node.canonical_name)] = node

    # Pass 2: create relations, resolving FKs from the index.
    # The tuple key prevents the bug where "paris" as place overwrites
    # "paris" as concept in a single-key dictionary.
    for rel_data in merged_data["relations"]:
        source_key = (rel_data["source_entity_type"], rel_data["source_canonical_name"])
        target_key = (rel_data["target_entity_type"], rel_data["target_canonical_name"])
        source = node_index.get(source_key)
        target = node_index.get(target_key)
        if source is None or target is None:
            logger.warning(
                "Dropping relation with unresolved endpoint: %s -> %s",
                source_key, target_key,
            )
            continue
        KnowledgeRelation.objects.create(
            graph=graph,
            source_node=source,
            target_node=target,
            relation_type=rel_data["relation_type"],
            description=rel_data["description"],
            source_type=rel_data["source_type"],
            confidence=rel_data["confidence"],
            weight=rel_data["weight"],
            temporal_start_iso=rel_data.get("temporal_start_iso", ""),
            temporal_start_year=rel_data.get("temporal_start_year"),
            temporal_end_iso=rel_data.get("temporal_end_iso", ""),
            temporal_end_year=rel_data.get("temporal_end_year"),
        )

    # Pass 3: create citations linking nodes and relations back to chunks.
    # (See the detailed implementation in knowledge/materialization.py)

    graph.status = "ready"
    graph.materialized_at = timezone.now()
    graph.save(update_fields=["status", "materialized_at"])
```

### Stage 9: trigger world generation

The task that runs the extraction synchronously calls
`generate_world_from_prompt(simulation, prompt, knowledge_graph=graph)`
as its final step. The existing generator function is extended with an
optional `knowledge_graph` parameter; see the next section for details.
There is no separate `generate_world_from_knowledge_graph` function.

## World Generation Integration

The existing `generate_world_from_prompt(prompt, simulation)` signature in
`epocha.apps.world.generator` is extended to accept an optional
`knowledge_graph` parameter:

```python
def generate_world_from_prompt(prompt, simulation, knowledge_graph=None):
    """Generate a world for a simulation from a text prompt or a knowledge graph.

    When knowledge_graph is provided, the generator builds the agent
    generation prompt from the structured graph data (nodes filtered by
    entity type) instead of from raw text. The free-text prompt is still
    used as an optional hint for stylistic or scenario-specific guidance.
    """
    if knowledge_graph is not None:
        return _generate_from_knowledge_graph(simulation, knowledge_graph, hint_prompt=prompt)
    return _generate_from_prompt_only(prompt, simulation)
```

The existing single-call generator remains unchanged under
`_generate_from_prompt_only`. The new `_generate_from_knowledge_graph`
lives in the same file.

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

The agent generation prompt requires the LLM to return personalities
keyed by the `canonical_name` of each Person node provided in the input.
The prompt explicitly lists the canonical names and instructs the LLM:
"Return a JSON object where the key for each personality is exactly the
canonical_name I provided, not a modified form." After parsing, the
generator matches personalities to nodes:

```python
raw = client.complete(system_prompt=system, prompt=user_prompt, ...)
llm_response = json.loads(clean_llm_json(raw))
personalities = llm_response.get("personalities", {})

for person_node in graph.nodes.filter(entity_type="person"):
    personality = personalities.get(person_node.canonical_name)
    if personality is None:
        # Fallback: fuzzy match on normalized names (strip accents,
        # lowercase) in case the LLM did not echo the exact canonical.
        personality = _match_personality_fuzzy(personalities, person_node)
    if personality is None:
        logger.warning(
            "No personality returned for %s (canonical=%s); using neutral defaults",
            person_node.name, person_node.canonical_name,
        )
        personality = _neutral_personality()

    agent = Agent.objects.create(
        simulation=simulation,
        name=person_node.name,
        role=person_node.attributes.get("role", "citizen"),
        personality=personality,
        # ...other fields from node attributes...
    )
    person_node.linked_agent = agent
    person_node.save(update_fields=["linked_agent"])
```

The same pattern applies to zones (from `place` nodes), groups (from
`group` nodes), institutions (from `institution` nodes), and events
(from `event` nodes). The fallback fuzzy match and neutral defaults
prevent the pipeline from failing when the LLM produces imperfect
echoing of canonical names.

## Visualization

A new dashboard route and a new JSON API endpoint expose the graph.

### Dashboard route

`GET /dashboard/simulation/<id>/knowledge-graph/` renders an HTML template
with Sigma.js and the filter UI. The template contains an initial JSON
payload embedded inline for fast first paint (top 100 nodes by
`mention_count`), plus a JavaScript call to the JSON API for progressive
loading of additional nodes.

### JSON API endpoint

`GET /api/v1/simulations/<id>/knowledge-graph/` returns the graph data in
a Sigma.js-compatible structure. Query parameters:

- `entity_types` (optional, comma-separated): filter nodes by type
- `limit` (optional, default 100, max 1000): maximum number of nodes to
  return, ordered by `mention_count` descending
- `offset` (optional, default 0): pagination cursor

Response schema:

```json
{
  "nodes": [
    {
      "id": 42,
      "entity_type": "person",
      "name": "Robespierre",
      "canonical_name": "robespierre",
      "description": "...",
      "mention_count": 17,
      "source_type": "document",
      "linked": {"kind": "agent", "id": 8}
    }
  ],
  "edges": [
    {
      "id": 101,
      "source": 42,
      "target": 77,
      "relation_type": "member_of",
      "category": "membership",
      "weight": 0.8
    }
  ],
  "stats": {
    "total_nodes": 312,
    "returned_nodes": 100,
    "has_more": true
  }
}
```

A DRF `ViewSet` in `epocha/apps/knowledge/api.py` implements the endpoint
using serializers `KnowledgeNodeListSerializer` and
`KnowledgeRelationListSerializer`, with `select_related` on `source_node`,
`target_node`, and `linked_agent`/`linked_zone`/`linked_group`/
`linked_event`/`linked_institution` to avoid N+1 queries.

### Rendering

Node colors by `entity_type` (10 colors defined in
`knowledge/templates/knowledge/graph.html` as a static mapping). Edge
colors by `relation_type` category: membership, spatial, temporal, belief,
social, kinship, causal, participation, production (9 categories, 9
colors). Force Atlas 2 layout via the inline JavaScript already used by
the social graph page (`templates/dashboard/partials/graph_layout.html`).

Detail panel on node click: description, source citations with excerpt
preview and link to the originating document, linked simulation entity
(if `linked_agent`/`linked_zone`/etc. is set) with a deep link to the
entity's page. Implementation in Alpine.js, consistent with the existing
dashboard stack.

## Configuration and Versioning

A new module `epocha/apps/knowledge/versions.py`:

```python
ONTOLOGY_VERSION = "v1"              # 10 entity types + 20 relations
EXTRACTION_PROMPT_VERSION = "v1"     # increments on prompt changes
EMBEDDING_MODEL = "BAAI/bge-m3"
EMBEDDING_DIM = 1024
CHUNK_SIZE_TOKENS = 800
CHUNK_OVERLAP_TOKENS = 150
CHUNK_CHARS_PER_TOKEN = 4            # approximate, used for char-based splitter
MAX_CHUNKS_PER_DOCUMENT = 50
MAX_DOCUMENT_CHARS = 500000
DEDUP_SIMILARITY_THRESHOLD = 0.85
EXTRACTION_TEMPERATURE = 0.1
```

Any change to `ONTOLOGY_VERSION`, `EXTRACTION_PROMPT_VERSION`, or the
`EMBEDDING_MODEL` invalidates the extraction cache automatically because
these values are part of the composite cache key. The other constants
affect behavior but not the cache key; changes to them take effect on
the next run without requiring re-extraction.

Django settings exposed via `django-environ`:

```python
EPOCHA_KG_ENABLED = env.bool("EPOCHA_KG_ENABLED", default=True)
EPOCHA_KG_MAX_CHUNKS_PER_DOC = env.int("EPOCHA_KG_MAX_CHUNKS_PER_DOC", default=50)
EPOCHA_KG_MAX_DOCUMENT_CHARS = env.int("EPOCHA_KG_MAX_DOCUMENT_CHARS", default=500000)
EPOCHA_KG_EMBEDDING_BATCH_SIZE = env.int("EPOCHA_KG_EMBEDDING_BATCH_SIZE", default=10)
```

### Cache maintenance

A Django management command `cleanup_extraction_cache` purges unused
cache entries to prevent unbounded growth after version bumps:

```bash
python manage.py cleanup_extraction_cache --min-age-days 30 --max-hit-count 0
```

The command deletes `ExtractionCache` rows where `hit_count` is at or
below the threshold and `created_at` is older than the minimum age. It
is intended to be run manually or from a scheduled cron job; no periodic
task is installed by default.

## Dependencies

### Python packages

Additions to `requirements/base.txt`:

```
pgvector==0.3.6
fastembed==0.3.6
langchain-text-splitters==0.2.2
```

- `pgvector` is the Django integration for Postgres vector operations.
  The single PyPI package provides both `VectorField` and the
  `VectorExtension` migration operation.
- `fastembed` provides ONNX-based embeddings without the torch
  dependency chain, keeping the Docker image footprint under 500 MB
  of additional weight.
- `langchain-text-splitters` is the standalone text splitting package
  extracted from the broader langchain project, with minimal
  dependencies.

### Postgres extension

The Postgres `vector` extension must be installed in the database image
and enabled via migration. The existing project uses
`postgis/postgis:16-3.4-alpine` which includes PostGIS but does **not**
include pgvector. The alternative community image `pgvector/pgvector:pg16`
includes pgvector but does not include PostGIS. Neither image alone
covers both extensions.

**Solution**: a custom Postgres image built from `postgis/postgis:16-3.4`
(Debian-based, not Alpine) with pgvector added from the PGDG apt
repository. The switch from Alpine to Debian is motivated by ease of
installing pgvector from a maintained package source; the image grows
by ~200 MB but gains a trivially reproducible build recipe.

New file `compose/postgres/Dockerfile`:

```dockerfile
FROM postgis/postgis:16-3.4

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       postgresql-16-pgvector \
    && rm -rf /var/lib/apt/lists/*
```

Update `docker-compose.local.yml` and `docker-compose.production.yml` to
build this custom image instead of pulling `postgis/postgis` directly:

```yaml
services:
  postgres:
    build:
      context: .
      dockerfile: compose/postgres/Dockerfile
    # ...existing env and volume configuration unchanged...
```

Then a Django migration enables both extensions in the target database:

```python
# epocha/apps/knowledge/migrations/0001_initial.py

from django.contrib.postgres.operations import CreateExtension
from django.db import migrations
from pgvector.django import VectorExtension

class Migration(migrations.Migration):
    dependencies = [
        ("world", "0004_world_distance_scale"),  # latest world migration
        ("agents", "0xxx_latest"),                # latest agents migration
        ("simulation", "0xxx_latest"),            # latest simulation migration
    ]

    operations = [
        VectorExtension(),  # enables the vector extension in the DB
        # ... model creation operations ...
    ]
```

The PostGIS extension is already enabled by the existing
`world/migrations/0003_postgis.py`; this new migration adds only the
`vector` extension on top.

### Migration dependencies

Because `KnowledgeNode` has foreign keys to `agents.Agent`, `agents.Group`,
`world.Zone`, `world.Institution`, and `simulation.Event`, the
`knowledge` app's initial migration must declare dependencies on the
latest migrations of all four apps. This ensures Django applies
migrations in the correct order on a fresh database. The concrete
dependency list goes into the initial migration file's `dependencies`
tuple as shown above; the placeholder `0xxx_latest` entries are resolved
to actual migration names when the migration is generated via
`makemigrations`.

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

### Fixtures

- `epocha/apps/knowledge/tests/fixtures/small_french_rev.txt`: a ~3000
  character excerpt in English describing the storming of the Bastille,
  containing named entities for Robespierre, Louis XVI, the Bastille,
  July 14 1789, and relations like Robespierre member of Jacobin Club.
  This is the primary fixture for deterministic pipeline tests.
- `epocha/apps/knowledge/tests/fixtures/multilingual_sample.txt`: a
  shorter mixed Italian/French fixture for multilingual embedding
  verification.

### Unit tests

- `test_normalizer.py`: canonical name normalization (accent stripping
  for French, Italian, German; honorific removal; whitespace collapse;
  edge cases like all-caps, empty string, single character)
- `test_ontology_validator.py`: accepts all 10 entity types and all 20
  relation types, rejects unknown types, validates source_type assignment
- `test_source_type_assignment.py`: the mechanical rule for assigning
  `document` vs `document_inferred` given name and passage_excerpt
- `test_merge_rules.py`: cluster merging with predefined input sets,
  verifying name selection, description concatenation, citation union,
  embedding recomputation
- `test_cache_key_builder.py`: cache key is deterministic, changes when
  any of the four composing fields changes

### Integration tests

- `test_pipeline_full.py`: end-to-end with the small fixture and a
  **mocked LLM** returning a fixed deterministic output. Uses real
  `fastembed` with the actual bge-m3 model. The model is downloaded
  once and cached in a pytest fixture shared across tests. Marked as
  `slow` so fast test runs can skip via `-m "not slow"`.
- `test_cache_hit.py`: run extraction twice on the same documents,
  assert the LLM mock is called only during the first run
- `test_cache_invalidation.py`: change `ONTOLOGY_VERSION` between runs,
  assert the LLM mock is called on both runs
- `test_concurrent_upload.py`: two simultaneous `get_or_create` on the
  same content_hash should produce a single `KnowledgeDocument` row
  (uses `pytest-django` transactional_db and threading)
- `test_unrecognized_vocabulary.py`: mocked LLM returns an unknown
  relation type; assert it lands in `unrecognized_relations` and never
  in `KnowledgeRelation`
- `test_visualization_api.py`: the JSON API endpoint returns the
  expected structure with `select_related` verification (zero extra
  queries beyond the expected minimum)

All tests use PostgreSQL with pgvector. No SQLite. The bge-m3 model
download in CI is cached via a persistent volume or artifact store to
avoid repeated downloads.

## API Changes

### New endpoint: document upload + world generation

`POST /api/v1/simulations/express-with-documents/`

Request (multipart/form-data):
- `name` (string, required): simulation name
- `seed` (integer, optional): simulation seed
- `prompt` (string, optional): free-text scenario hint passed along the
  graph to the generator
- `documents[]` (file, 1..N): one or more document files (PDF, DOCX,
  MD, TXT)

Response (202 Accepted):
```json
{
  "simulation_id": 42,
  "task_id": "celery-task-uuid",
  "status_url": "/api/v1/simulations/42/extraction-status/",
  "websocket_channel": "simulation_42"
}
```

The endpoint:
1. Creates the `Simulation` row immediately
2. Stores the uploaded files temporarily and parses them to
   `KnowledgeDocument` + `KnowledgeDocumentAccess` rows
3. Enqueues the Celery task `extract_and_generate(simulation_id,
   document_ids, prompt)` which runs the full pipeline (Stages 1-9)
4. Returns the 202 response with the task ID and WebSocket channel the
   client should subscribe to for progress updates

Status endpoint:

`GET /api/v1/simulations/<id>/extraction-status/`

Response:
```json
{
  "status": "extracting",
  "progress": {"chunks_processed": 12, "chunks_total": 42},
  "knowledge_graph_id": null,
  "error": null
}
```

Possible `status` values: `pending`, `extracting`, `materializing`,
`generating_world`, `ready`, `failed`.

### Existing endpoint unchanged

The existing `POST /api/v1/simulations/express/` (prompt-only flow)
remains unchanged. Users who do not upload documents continue to use it
as before.

## Migration Path

The feature is additive: existing simulations are unaffected. The flag
`EPOCHA_KG_ENABLED` allows emergency disabling without code changes. The
new `express-with-documents` endpoint runs the Knowledge Graph extraction
before generating the world. The old prompt-only flow remains available
for users who do not upload documents. No schema changes are required on
pre-existing tables (World, Agent, Zone, etc.); only new tables and new
nullable FKs from `KnowledgeNode` toward existing models are added.

## Known Limitations

- **Chunk truncation**: documents longer than 50 chunks (roughly 40000
  tokens or 160 KB of text) are truncated after the limit. The cap is
  configurable via `EPOCHA_KG_MAX_CHUNKS_PER_DOC` but high values lead
  to long extraction times.
- **Document size cap**: documents larger than 500000 characters
  (~500 KB) are rejected at upload. The cap is configurable via
  `EPOCHA_KG_MAX_DOCUMENT_CHARS`.
- **Cross-chunk relations not extracted**: the pipeline extracts
  relations per chunk. If "Robespierre" is mentioned in chunk 5 and
  "Declaration of the Rights of Man" is mentioned in chunk 20 without
  appearing together anywhere, the `authored` relation between them is
  missed. Cross-chunk relation extraction is deferred to a follow-up
  feature (potentially via the research-agent enrichment).
- **Dedup similarity threshold is a heuristic**: the value 0.85 is an
  initial guess, not derived from a specific benchmark. It must be
  recalibrated against empirical extraction quality once the pipeline
  has processed representative historical documents. The threshold is
  exposed as `DEDUP_SIMILARITY_THRESHOLD` in the versions module.
- **Temporal precision**: temporal fields store both an ISO-8601 string
  for display fidelity and an integer year for range queries. Month and
  day granularity cannot be used in SQL range queries; if needed later,
  dedicated indexed columns should be added.
- **Quadratic dedup**: within each entity type, the deduplication
  compares all entity pairs (O(N²) time). For typical documents
  producing a few hundred entities per type, this is sub-second. For
  pathological cases with thousands of entities per type, it can take
  tens of seconds. A future optimization is approximate clustering via
  pgvector cosine similarity search.
- **Source type distinction depends on LLM passage fidelity**: the
  mechanical assignment of `document` vs `document_inferred` relies on
  the LLM returning a `passage_excerpt` that actually comes from the
  input chunk. If the LLM hallucinates an excerpt, the mechanical check
  still runs but against a fabricated passage. Mitigation: post-hoc
  validation that the excerpt is a literal substring of the source
  chunk text; items failing this check are demoted to
  `document_inferred` or dropped entirely.
- **Extraction cost**: a typical document producing 40-50 chunks results
  in 40-50 LLM calls, approximately 100-200 KB of total prompt tokens,
  completing in 1-3 minutes on Groq with llama-3.3-70b. Users should be
  warned that the initial extraction for a new document set is not
  instantaneous.
- **HNSW index parameters**: `m=16, ef_construction=64` on the pgvector
  HNSW indexes follow the defaults recommended by Malkov & Yashunin
  (2018) "Efficient and robust approximate nearest neighbor search
  using Hierarchical Navigable Small World graphs" for datasets under
  100k vectors. Larger datasets require tuning.

## Out of Scope Reminder

Not in this iteration, deferred to follow-up features:

- Retrieval of graph facts into agent memories during simulation ticks
- Natural language search over the graph by end users
- Tab unification with the social graph page
- Pre-generation review UI for the extracted graph
- Cross-chunk relation extraction beyond per-chunk LLM calls
- Advanced visualization features (community detection, knowledge pruning,
  timeline view)
- LLM-knowledge enrichment step: adding facts from the model's
  pre-training knowledge via the research agent. The `source_type`
  `llm_knowledge` does not exist in the MVP and will be introduced with
  this follow-up feature.
- Updating an existing simulation's graph when new documents are added
  mid-simulation
- Full-text search inside documents and chunks (only vector similarity
  is supported in this iteration)

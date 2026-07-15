# Implementation Plan: Factions Round 3 hardening

**Branch**: `20260715-111119-factions-round3-hardening` | **Date**: 2026-07-15 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/20260715-111119-factions-round3-hardening/spec.md`

## Summary

Close the five deferred behavioral findings of the factions Round 2 audit: introduce a prefetched affinity context in `affinity.py` (data injection into the existing DB-coupled helpers, no twin logic), refactor `_check_join_existing_groups` to average affinity over ALL living members with an O(1)-in-pairs query budget, remove the two verified nondeterminism sources (unordered slices, strength tie-break), wrap the four multi-row mutation paths in `transaction.atomic` with defined units, unify group-membership writes on bulk `update()` (safe: no signals, no save() override, no auto_now on Agent — verified), and de-N+1 the leadership pipeline. Whitepaper §4.7 deferred-hardening bullet resolved (EN+IT). Formulas (4.38)-(4.41) untouched.

## Technical Context

**Language/Version**: Python 3.12, Django 5.x

**Primary Dependencies**: stdlib only (`django.db.transaction`); test-side `pytest-django>=4.9` (`django_assert_num_queries`, first use in repo)

**Storage**: no schema change, no migration

**Testing**: pytest in container (`docker compose -f docker-compose.local.yml exec -T web pytest`), baseline 810

**Target Platform**: unchanged

**Project Type**: Django monolith, apps under `epocha/apps/`

**Performance Goals**: `_check_join_existing_groups` query count independent of pair/suggestion count (today ~4250 worst-case at 50×5×5); leadership pipeline constant query budget per group

**Constraints**: numeric equivalence batched/non-batched (exact float equality, post FR-011 deterministic tie-break); formulas and parameters untouched; suite green with no weakened assertions; ruff clean; EN/IT whitepaper mirrored

**Scale/Scope**: 2 code files (`factions.py`, `affinity.py`), 2 test files (extended), 2 whitepaper files (one bullet each), memory tracking files

## Constitution Check

- **I. Scientific Method**: no formula/parameter change; the behavioral changes (all-members averaging, deterministic tie-break) correct implementation defects against the documented model intent. PASS.
- **II. Verify Before Asserting**: all load-bearing facts verified in the investigation dossier and re-verified by the Round 1 spec audit (no signals/save-override/auto_now on Agent; 3-4 queries per affinity pair; unordered querysets; tie-break nondeterminism; §4.7 doc surface = one bullet). Tasks carry file:line preflight anchors. PASS.
- **III. Adversarial Audit**: spec audit Round 1 → 8 findings + verified set; all fixed; Round 2 convergence check (this gate). Code audit fires at phase 6. PASS.
- **IV. Three-Step Design**: performed before spec (design decisions: eliminate sampling instead of seeding RNG; bulk-update policy; per-mutation atomic units; data-injection batching). Recorded in spec FAQ. PASS.
- **V. Evidence-Based Verification**: SCs mechanically checkable (query-count assertions, exact-equality tests, rollback tests, grep). Confidence at closure: container suite only (no production env involved). PASS.
- **Documentation Discipline**: factions is a §4.7 (chapter 4) module → doc-sync applies; surface verified as the single deferred-hardening bullet EN ~1877 / IT ~1944; frozen-pin update at closure. PASS.

No violations → Complexity Tracking not needed.

## Project Structure

### Documentation (this feature)

```text
specs/20260715-111119-factions-round3-hardening/
├── spec.md              # Phase 2 artifact (audit loop → CONVERGED)
├── plan.md              # This file
├── tasks.md             # Phase 4 artifact
└── checklists/
    └── requirements.md
```

research.md/data-model.md/contracts/ not materialized: no unknowns survived the spec audit, no schema change, no external interface change (artifact-materialization gradation).

### Source Code (repository root)

```text
epocha/apps/agents/affinity.py          # prefetched-context mechanism injected into _relationship_score/_circumstance_score; FR-011 tie-break
epocha/apps/agents/factions.py          # join-check refactor, leadership de-N+1, atomic wraps, bulk-update policy, explicit orderings, docstring updates
epocha/apps/agents/tests/test_affinity.py   # equivalence + tie-break + context tests
epocha/apps/agents/tests/test_factions.py   # query-budget, rollback, policy, determinism, all-members tests
docs/whitepaper/epocha-whitepaper.md    # §4.7 deferred bullet resolved (~1877)
docs/whitepaper/epocha-whitepaper.it.md # §4.7 mirror (~1944)
docs/memory-backup/...                  # session tracking at closure
```

**Structure Decision**: all changes live in the existing `agents` app modules that own the behavior; no new modules (Golden Rule: no new app responsibilities introduced).

## Implementation approach (phase ordering)

1. **AffinityContext (FR-001, FR-011 in affinity.py)** — TDD: equivalence and tie-break tests first.
   - `build_affinity_context(pairs_or_agents, tick)`: one Relationship query over all involved pairs (both directions, `Q(agent_from__in=A, agent_to__in=B) | Q(agent_from__in=B, agent_to__in=A)` superset then in-memory pair grouping), one Memory query over all involved agents (filters exactly `source_type=PUBLIC, is_active=True, tick_created__gte=tick-10`), per-agent content-sets built once (memoization).
   - `_relationship_score(a, b, context=None)`, `_circumstance_score(a, b, tick, context=None)`: context path picks from in-memory maps with tie-break key `(-strength, id)`; query path gets `order_by("-strength", "id")`. `compute_affinity(a, b, tick, context=None)` threads it through.
2. **Join-check refactor (FR-002)** — members per group fetched once per tick with `order_by("id")`; affinity over all living members via context; `has_positive_rel` from the context's relationship map; dedup via ONE aggregated Memory query loading ALL recent memories (tick-5 window, any content, no type pre-filter) of ungrouped agents, replicating `group.name in content` case-sensitive substring per (agent, group) in-memory; suggestions via `bulk_create`; docstring rewritten.
3. **Cluster detection (FR-003)** — `_detect_and_propose_factions` consumes the same context; seed ordering becomes `order_by("name", "id")` (preserves the existing name order at factions.py:679, adds only the id tiebreak — greedy clustering itself is F-4, out of scope).
4. **Leadership de-N+1 (FR-004)** — `compute_leadership_score(..., members=None, context=None)`; `compute_legitimacy`/`update_group_leadership`/`_elect_new_leader` fetch members once and pass down; relationship/memory data prefetched per group.
5. **Atomicity + write policy (FR-005, FR-006)** — atomic units as specified: per-schism, per-faction (whole `_create_faction`), per-dissolution, per-join-decision (single agent's group move + join Memory at factions.py:828-834 + cohesion decrement); form branch relies on `_create_faction`'s atomic, no outer wrap; membership moves become queryset `update()` (`id__in`; single-row in the join branch — discipline consistency, not cardinality) inside the atomic blocks; module docstring documents the policy and its verified precondition.
6. **Docs (FR-008)** — §4.7 bullet EN+IT resolved; factions.py Known Limitations bullet (f) updated with corrected characterization.
7. **Gates (FR-007, FR-009)** — every behavioral fix lands test-first where red is observable; full container suite; ruff host+container; phase-6 adversarial audit on the diff.

## Risks

- **Exact-equality flakiness**: mitigated by FR-011 (deterministic tie-break in both paths) and by testing equivalence on constructed fixtures with known ties.
- **Query-budget test brittleness**: `django_assert_num_queries` pins exact counts; counts documented in-test with a breakdown comment so future legitimate changes adjust consciously.
- **Behavioral drift beyond intent**: all-members averaging and defined tie-breaks change emergent dynamics in declared ways; existing test expectations change only where the old expectation encoded the defect (each such change justified in the commit).
- **Atomic block scope creep**: per-mutation units keep lock windows small; no outer wrap around loops.

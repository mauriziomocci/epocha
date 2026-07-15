# Tasks: Factions Round 3 hardening

**Input**: Design documents from `/specs/20260715-111119-factions-round3-hardening/`

**Prerequisites**: plan.md, spec.md (CONVERGED after 4 adversarial audit rounds)

**Tests**: test-first mandatory (RED before implementation wherever red is observable).

**Organization**: US1 = affinity context + join-check (FR-001/002/003/011), US2 = atomicity + write policy (FR-005/006), US3 = leadership de-N+1 (FR-004), US4 = docs (FR-008). Container is the test/lint authority.

## Phase 1: Setup

- [ ] T001 Preflight anchors: `grep -n "order_by(\"name\")" epocha/apps/agents/factions.py` → :679; `grep -n "\[:5\]" epocha/apps/agents/factions.py` → :753; `grep -n "content__contains" epocha/apps/agents/factions.py` → :762; `grep -n "update(group=None)" epocha/apps/agents/factions.py` → :515; `grep -n "save(update_fields=\[\"group\"\])" epocha/apps/agents/factions.py` → :618, :827, :908 (three sites; :908 is inside `_create_faction`); `grep -n "MultipleObjectsReturned" epocha/apps/agents/affinity.py` → tie-break block ~:166-174; `grep -n "def compute_leadership_score\|def compute_legitimacy" epocha/apps/agents/factions.py` → :170, :263. If any anchor drifted: STOP, re-verify, escalate (constitution Principle II).

## Phase 2: Foundational — US1a Affinity context (FR-001, FR-011)

- [ ] T002 RED tests in `epocha/apps/agents/tests/test_affinity.py`: (1) `test_relationship_score_tie_break_deterministic` — two relationships between the same pair with equal strength but different sentiment and distinct ids: `compute_affinity` result must reflect the relationship with the LOWEST id (will fail today: arbitrary pick); (2) `test_affinity_context_equivalence` — build a scenario with relationships (including a tie case and a reverse-direction pair) and public memories; assert `compute_affinity(a, b, tick, context=ctx) == compute_affinity(a, b, tick)` exactly, for every pair (will fail today: no context parameter — expect TypeError, that IS the red); (3) `test_affinity_context_query_budget` — with `django_assert_num_queries`: building the context for A agents × B members costs a fixed number of queries (pin exact count with breakdown comment) and per-pair evaluation with context costs 0 queries. Run in container, confirm RED with expected failure modes.
- [ ] T003 Implement in `epocha/apps/agents/affinity.py`: (a) deterministic tie-break — `.order_by("-strength")` → `.order_by("-strength", "id")` in `_relationship_score`; (b) `build_affinity_context(agents_a, agents_b, tick)` → context object holding: pair-keyed relationship map (one query over both directions, tie-break key `(-strength, id)` applied in-memory), per-agent public-memory content sets (one query, filters exactly `source_type=PUBLIC, is_active=True, tick_created__gte=tick-10`, sets built once per agent); (c) optional `context=None` parameter threaded through `compute_affinity` → `_relationship_score`/`_circumstance_score` (data injection; helpers remain the single home of scoring logic — NO twin functions). English docstrings with the determinism rationale. GREEN: T002 tests pass; existing 7 affinity tests untouched and green.
- [ ] T004 Gates: container pytest `epocha/apps/agents/tests/test_affinity.py` green; `ruff check` + `ruff format --check` on `epocha/apps/agents/` clean (host + container). Commit via git-commit-assistant: `feat(agents): add prefetched affinity context and deterministic tie-break`.

## Phase 3: US1b Join-check refactor (FR-002, FR-003)

- [ ] T005 [US1] RED tests in `epocha/apps/agents/tests/test_factions.py`: (1) `test_join_check_averages_all_members` — group with 10 members of heterogeneous affinity vs one ungrouped agent constructed so that avg(all 10) crosses the threshold differently than any 5-subset average; assert the suggestion outcome reflects all-10 (fails today); (2) `test_join_check_query_budget` — 4 groups × 10 members × 8 ungrouped: pin exact query count with `django_assert_num_queries` (breakdown comment: groups fetch, per-group members OR single members query, context queries, dedup query, bulk_create) and assert the count does not change when doubling ungrouped agents (fails today: O(pairs)); (3) `test_join_check_dedup_semantics` — agent with a recent non-suggestion memory containing the group name (e.g. "X has dissolved") must NOT receive a suggestion (protects the broad `content__contains` semantics through the refactor; passes today, must still pass after); (4) `test_join_check_deterministic` — two identical runs on identical fixtures produce identical Memory sets (may already pass; keep as regression). Confirm RED where expected.
- [ ] T006 [US1] Implement `_check_join_existing_groups` refactor in `epocha/apps/agents/factions.py` per FR-002(a-f): members per group fetched once per tick (`order_by("id")`, dict group→members), `build_affinity_context` over ungrouped × all members, average over ALL living members, `has_positive_rel` resolved from the context's relationship map (sentiment>0 with any member, both directions), dedup via ONE aggregated query of ALL recent memories (tick-5 window, no type filter) of ungrouped agents with in-memory case-sensitive `group.name in content` per (agent, group), suggestions via `bulk_create`, docstring rewritten to the real behavior. Iterations over ungrouped and groups get `order_by("id")`.
- [ ] T007 [US1] Implement FR-003 in `_detect_and_propose_factions`: seed ordering `order_by("name")` → `order_by("name", "id")` (only the id tiebreak — clustering logic untouched, F-4 out of scope); cluster affinity loop (`factions.py:700`) consumes a context built once for the candidate set; the `already_proposed` per-agent exists (`:708`) folded into the same aggregated-dedup approach if trivially shareable, otherwise left as-is and its cost documented (decision recorded in code comment; escalate if ambiguous).
- [ ] T008 [US1] GREEN + gates: T005 tests green, all existing factions/affinity tests green in container; ruff clean. Commit: `feat(agents): de-bias and de-N+1 faction join suggestions`.

## Phase 4: US2 Atomicity + write policy (FR-005, FR-006)

- [ ] T009 [US2] RED tests: (1) `test_schism_rolls_back_on_failure` — monkeypatch `_elect_new_leader` (called after splinter creation and ally migration) to raise; run `_check_schism` on a fixture that schisms; assert NO splinter Group, NO agent moved, NO schism Memory rows (fails today: partial rows persist); (2) `test_create_faction_rolls_back_on_failure` — monkeypatch the memory-creation step or `_generate_faction_identity` consumer path inside `_create_faction` after the Group insert to raise; assert no Group/agent/Memory residue (fails today); (3) `test_dissolution_atomic_and_bulk` — dissolution moves all members out in one queryset update inside a transaction (assert final state + query pattern); (4) `test_membership_write_discipline` — post-schism and post-creation, every moved agent's `group` is correct via bulk update path (behavioral state assertions). Confirm RED for (1)(2).
- [ ] T010 [US2] Implement FR-005/FR-006 in `factions.py`: `transaction.atomic` per-schism (wrap the mutation block :603-644), whole `_create_faction`, per-dissolution, per-join-decision (agent move + join Memory :828-834 + cohesion decrement :835); form branch relies on `_create_faction`'s atomic (no outer wrap); membership moves become queryset `update()` with `id__in` (schism allies, faction founders) or single-row filter (join branch); module docstring gains the write-discipline policy paragraph with its verified precondition (no signals, no save() override, no auto_now on Agent — verified 2026-07-15) and the revisit-if-signals-added note. `import transaction` from django.db.
- [ ] T011 [US2] GREEN + gates + commit: `fix(agents): make faction mutations atomic and unify membership writes`.

## Phase 5: US3 Leadership de-N+1 (FR-004)

- [ ] T012 [US3] RED tests: (1) `test_leadership_query_budget` — group of 8 members: `update_group_leadership` (which runs legitimacy + possible succession scoring) under `django_assert_num_queries` with a pinned constant budget; assert budget unchanged with 16 members (fails today: O(N)); (2) `test_leadership_score_equivalence` — `compute_leadership_score(member, group, tick)` (self-fetch path) == `compute_leadership_score(member, group, tick, members=prefetched, context=ctx)` exact equality for every member of a heterogeneous fixture (fails today: no such parameters — TypeError is the red).
- [ ] T013 [US3] Implement FR-004: `compute_leadership_score(..., members=None, context=None)` — when provided, skip the member refetch (:209) and resolve Relationship (:224-227) and Memory (:242-249) needs from prefetched data (same aggregated-query approach as the affinity context; reuse `build_affinity_context` structures where the filters match, otherwise a small leadership context built once per group); `compute_legitimacy` (:263) fetches members ONCE (`order_by("id")`) and passes them down (:310); `update_group_leadership` and `_elect_new_leader` thread the same data. Numeric equivalence preserved (same arithmetic, same tie handling).
- [ ] T014 [US3] GREEN + gates + commit: `fix(agents): remove N+1 from faction leadership pipeline`.
- [ ] T014-bis [US3] (escalation recepita, spec FR-004 amendment): estendere il fix alla founder election di `_create_faction` (stessa classe N+1): members=founders + leadership context, founder memories in bulk_create, budget pinnato (19→10 a 6 founder, invariante a 12); fix comportamentale dichiarato dell'elezione degenere (scoring su gruppo vuoto → vinceva sempre founders[0]) con regression test sull'identità del leader eletto; test di budget per `_detect_and_propose_factions`; guardia difensiva contro self-relationship nel bucketing del leadership context.

## Phase 6: US4 Documentation (FR-008)

- [ ] T015 [US4] Update `factions.py` module docstring Known Limitations: bullet (f) deferred hardening → resolved (date + branch), corrected sample characterization (unordered queryset, not "PK-stable"); keep F-4 clustering and club-goods bullets as still-open.
- [ ] T016 [P] [US4] Whitepaper §4.7: EN line ~1877 and IT line ~1944 "Deferred behavioral hardening" bullet rewritten as resolved (2026-07-15, this branch): member-sampling bias removed via all-members averaging with prefetched context, transaction.atomic on all four mutation paths, membership writes unified on queryset update (verified no-signal precondition), N+1 removed from join/detect/leadership, deterministic relationship tie-break. Equations and Algorithm prose untouched. EN/IT mirrored.
- [ ] T017 [US4] Doc-sync grep gate: `grep -n "Deferred behavioral hardening" docs/whitepaper/*.md` shows resolved wording in both; equations (4.38)-(4.41) diff-clean; commit: `docs: mark factions behavioral hardening as resolved in whitepaper`.

## Final Phase: Verification

- [ ] T018 Full container suite `pytest --cov=epocha -q`: zero failures, baseline 810 + new tests; zero new skips/xfail.
- [ ] T019 `ruff check .` and `ruff format --check .` exit 0 (host + container).
- [ ] T020 8-point code review on the full diff.
- [ ] T021 Phase-6 adversarial code audit (critical-analyzer on the diff; loop to CONVERGED): marker points — exact dedup semantics preserved, equivalence tests actually cover tie cases, atomic blocks cover ALL writes of each mutation, no behavior drift beyond the declared ones, whitepaper EN/IT mirror.
- [ ] T022 Closure prep: PR to develop (Draft), evidence in description; memory session tracking; frozen-pin at merge (whitepaper touched).

## Dependencies

- T001 → all. US1a (T002-T004) → US1b (T005-T008) → US3 (T012-T014, reuses context infra). US2 (T009-T011) independent of US1 (can follow US1b to avoid factions.py merge friction — sequential execution chosen). US4 after all code. Final phase last.

## Implementation Strategy

Sequential story order: US1a → US1b → US2 → US3 → US4 → Final. One commit per story phase via git-commit-assistant, no push until closure. Query-count tests pin exact budgets with in-test breakdown comments. Sonnet implementer subagents per phase with escalation on any strategic ambiguity (bright line: not derivable from task+spec → escalate).

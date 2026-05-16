# Feature Specification: Factions Audit Re-pass (Round 2)

**Feature Branch**: `20260516-183045-factions-audit-repass`

**Created**: 2026-05-16

**Status**: Draft (post Round 1 audit, pre Round 2 verification + fixes)

**Input**: User description: "Round 2 adversarial audit re-pass for the factions module (`epocha/apps/agents/factions.py`) — close the 4 Round 1 findings catalogued against this module and promote it from whitepaper §8.1 to a new §4.7."

## Context

This feature is **Branch 5 of 6** in the F-CAMPAIGN audit re-pass batch documented in `docs/superpowers/plans/2026-05-12-audit-repass-campaign.md` (legacy plan, archival). Factions is a single-module cluster: `epocha/apps/agents/factions.py` (876 LOC, the largest single source file under audit in this campaign) with companion test file `epocha/apps/agents/tests/test_factions.py` (153 LOC). The 2026-04-12 batch adversarial audit (`docs/scientific-audit-2026-04-12.md`) opened 4 outstanding Round 1 findings against this module:

- **F-1 INCORRECT**: Stogdill (1948) is cited in the `compute_leadership_score()` docstring and module header as the source for the trait-weighted leadership formula. Stogdill's 1948 meta-review identifies trait correlates of leadership (intelligence, dependability, social participation) but does NOT supply a weighted-sum formula. Charisma in particular is Weber's (1922) sociological concept, not a Stogdill trait. The current code (`factions.py:111-116`) already softens the claim to "broadly consistent with… Stogdill 1948 identified… Judge et al. 2002 provide meta-analytic effect sizes" but the wording still implies more empirical anchoring than is warranted. Better primary citation for the meta-analytic trait-leadership relationship: Judge, T. A., Bono, J. E., Ilies, R., and Gerhardt, M. W. (2002), "Personality and leadership: A qualitative and quantitative review", *Journal of Applied Psychology*, 87(4), 765-780.
- **F-2 INCORRECT**: Dunbar (1992) is cited in the `update_group_cohesion()` docstring for the size-penalty threshold of 5. Dunbar's number is 150, not 5. The "5" figure refers to the intimate-clique stratum of Dunbar's nested-group hierarchy (Zhou et al. 2005), NOT to a coordination cost boundary. The current code (`factions.py:247-251`) already partially distances itself ("while Dunbar (1992) identifies a hierarchy of group sizes (5, 15, 50, 150), the use of 5 here as a coordination cost boundary is a simulation design choice, not a direct application of Dunbar's model") but the citation still implies Dunbar grounds the parameter, which is misleading. Round 2 must reframe the threshold as a tunable design parameter and either drop the Dunbar attribution or qualify it more strongly.
- **F-3 UNJUSTIFIED**: the cohesion-update delta coefficients (`cooperation_ratio * 0.10`, `conflict_ratio * 0.15`, `size_penalty * 0.02`, `leader_effectiveness * 0.05`) at `factions.py:316-321` carry an inline attribution to Baumeister et al. (2001) "Bad is stronger than good" for the asymmetry between the 0.10 and 0.15 coefficients. Baumeister (2001) is a qualitative review article documenting that negative events tend to have a larger psychological impact than positive events of equivalent magnitude; it does NOT supply a quantitative 1.5:1 ratio, nor does it speak to the absolute magnitudes of 0.10, 0.15, 0.02, or 0.05 used in the delta formula. The current code (`factions.py:43-49`) already acknowledges that "the specific values are not empirically derived" but the Baumeister attribution still implies he grounds the ratio. Round 2 must reframe all four coefficients as tunable design parameters with Baumeister cited only for the *qualitative direction* of the asymmetry.
- **F-4 MISSING**: the schism detection loop (`_check_schism()` at `factions.py:469-475`) iterates over the group's queryset and treats the first agent as the seed of a candidate splinter ("for seed in members: allies = [seed] …"). Because the queryset order is determined by the default Django ORM ordering (typically primary key), two overlapping potential schisms within the same group cannot both be detected in the same tick — whichever cluster contains the lowest-PK member wins, even if a different cluster has a stronger schism signal. The current code (`factions.py:465-468`) already documents the limitation inline ("Known limitation: schism detection seeds from the first agent in the queryset, making the result order-dependent. Overlapping potential schisms may exist; which one is detected depends on iteration order. A more robust approach would use clustering algorithms.") but the documentation is buried mid-function and is not surfaced in the module docstring or in the whitepaper. Round 2 must promote this limitation to the module docstring header and either accept the doc-only resolution or escalate to a robust clustering implementation.

Branch 1 (Reputation cluster, merged via PR#5), Branch 2 (Rumor cluster, merged via PR#6 with promotion to §4.4), Branch 3 (Political-institutions cluster, merged via PR#7 with promotion to §4.5), and Branch 4 (Movement cluster, merged via PR#8 with promotion to §4.6) preceded this work. The conventions established by those branches — word-boundary regex for citation searches, `transaction.atomic` for any concurrent state write, lowest-risk fix posture, mandatory invariant tests for behavioral fixes, mandatory Round 2 audit dispatch with convergence loop, doc-only resolution preferred where defensible — apply unchanged to this branch.

A spot-check of the current code on develop @ `0afca1d` (post Branch 4 closure) confirms that all 4 Round 1 findings remain open in the form documented above — the partial mitigations already in place are documentation softenings, not full resolutions. The factions module is qualitatively different from the four previously closed clusters in three ways that justify a heavier-than-usual Round 2 audit scope:

1. **Scale**: 876 LOC versus 250 LOC (movement), making the surface area for new findings during Round 2 re-audit materially larger.
2. **Concurrency**: faction dynamics run on the slow tick interval (`EPOCHA_FACTION_DYNAMICS_INTERVAL` default 5) and mutate `Group.cohesion`, `Group.leader`, `Agent.group`, and create `Memory` and `Group` rows. The Round 2 audit must verify these writes are inside `transaction.atomic` blocks where required to avoid lost updates under parallel simulation runs.
3. **DRY surface**: factions.py reuses `compute_affinity()` from `affinity.py` (closed in Branch 2) and `compute_leadership_score()` / `compute_legitimacy()` are called from multiple paths (`update_group_leadership`, `_check_schism`, formation processing). DRY drift against the Branch 1+2+3+4 helpers must be checked.

This branch resolves the 4 catalogued Round 1 findings AND admits Round 2 may surface additional findings during re-audit — the spec explicitly leaves room for one optional User Story (US3 below) for UNJUSTIFIED additions that the Round 2 auditor flags during fresh-eyes re-pass. The §4.7 promotion is gated on full Round 2 CONVERGED, not just the 4 R1 findings.

This spec is constitutional-compliant per `.specify/memory/constitution.md` v1.0.0: Principles I (Scientific Method), II (Verify Before Asserting), III (Adversarial Audit), V (Evidence-Based Verification).

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Close 2 INCORRECT findings on citation accuracy (Priority: P1)

The Round 1 audit identified two INCORRECT findings that BLOCK the §8.1 → §4.7 whitepaper promotion until each is resolved with a corrected citation or a behavioral parameter adjustment. The two items are: leadership weighted formula falsely attributed to Stogdill (1948) for the weights themselves (F-1, current code softens but still implies more empirical anchoring than is warranted), and size-penalty threshold of 5 falsely attributed to Dunbar (1992) — Dunbar's number is 150, the "5" refers to intimate cliques in the nested-group hierarchy and is not a coordination-cost boundary in Dunbar's model (F-2, current code partially distances itself but the Dunbar attribution remains misleading).

**Why this priority**: per the audit verdict, the whitepaper §4.7 promotion (the deliverable that closes this branch) requires all INCORRECT findings resolved. Citation accuracy is a Principle I non-negotiable.

**Independent Test**: dispatch Round 2 `critical-analyzer` subagent audit limited to the F-1 and F-2 findings; verdict must be CONVERGED for each. Optional `pytest` regression on `test_factions.py` to confirm that no behavioral test depends on the citation text.

**Acceptance Scenarios**:

1. **Given** the `compute_leadership_score()` docstring at `factions.py:96-117` and the module-level header "Scientific basis" block at `factions.py:14-19`, **When** auditing the leadership formula attribution, **Then** Stogdill (1948) is cited ONLY as the meta-review establishing the *principle* that traits correlate with leadership emergence; Judge et al. (2002) is added as the primary meta-analytic reference for Big Five trait effect sizes; the weights themselves (0.30/0.20/0.15/0.20/0.15) are explicitly labelled as tunable design parameters with no empirical derivation; charisma is correctly attributed to Weber (1922) or its modern operationalization (e.g. Antonakis et al. 2016) rather than implied to be a Stogdill trait.

2. **Given** the `update_group_cohesion()` docstring at `factions.py:240-256` and the size-penalty derivation, **When** auditing the threshold value 5, **Then** the threshold is explicitly labelled as a tunable design parameter; the Dunbar (1992) citation is either dropped entirely OR retained only with a clarifying note that the threshold is NOT derived from Dunbar's nested-group hierarchy (in which "5" is the intimate-clique stratum, not a coordination cost boundary); the docstring states that coordination cost above a small-group threshold is a generic principle in organizational psychology (e.g. Hackman 2002, "Leading Teams") without claiming a specific empirical anchor.

3. **Given** the module-level "Scientific basis" docstring header at `factions.py:14-23`, **When** auditing the citation list, **Then** Stogdill (1948) attribution matches the corrected language; Judge et al. (2002) is added with a complete reference (DOI `10.1037/0021-9010.87.4.765`); Dunbar (1992) is either removed or qualified per Acceptance Scenario 2; Festinger et al. (1950), Olson (1965), Axelrod (1984), and Baumeister et al. (2001) remain (with Baumeister per US2 below).

---

### User Story 2 — Close 1 UNJUSTIFIED finding on cohesion delta coefficients + 1 MISSING finding on schism detection (Priority: P2)

The Round 1 audit identified one UNJUSTIFIED finding (F-3): the cohesion-update delta coefficients (0.10 cooperation, 0.15 conflict, 0.02 size penalty, 0.05 leader effectiveness) at `factions.py:316-321` are presented with a Baumeister et al. (2001) attribution that implies he supplies the 1.5:1 ratio. Baumeister's review documents the qualitative direction of negativity bias but does not supply quantitative ratios. The four coefficients must be reframed as tunable design parameters; Baumeister is retained only as the source of the *qualitative direction* of the asymmetry.

The same audit identified one MISSING finding (F-4): the schism detection loop at `factions.py:469-475` is order-dependent because it seeds the candidate-splinter cluster from the first agent in the queryset. Two overlapping potential schisms cannot both be detected in the same tick. The inline limitation note (`factions.py:465-468`) acknowledges the issue but is buried mid-function and is not surfaced in the module docstring or the whitepaper. Round 2 must either (a) promote the limitation to the module docstring header AND the whitepaper §4.7 Simplifications block (doc-only resolution), or (b) escalate to a robust clustering implementation (behavioral fix — out of branch scope, separate spec).

**Why this priority**: P2 because individually non-blocking but collectively required for CONVERGED verdict. Grouped fix in one commit.

**Independent Test**: dispatch Round 2 audit on the resolved file; verdict CONVERGED.

**Acceptance Scenarios**:

1. **Given** the `update_group_cohesion()` formula at `factions.py:316-321`, the inline comment at `factions.py:43-49`, and the docstring at `factions.py:240-256`, **When** auditing the four coefficients (0.10, 0.15, 0.02, 0.05), **Then** the comment block carries an explicit "tunable design parameters" disclaimer for all four magnitudes; Baumeister et al. (2001) is retained only as the source of the qualitative direction of the asymmetry (conflict has stronger psychological impact than cooperation of equivalent magnitude); the 1.5:1 ratio between conflict and cooperation is explicitly labelled as a design choice consistent with negativity bias direction but not derived from a specific empirical fit; the absolute magnitudes (0.10 sets a cohesion change rate of ~0.10 per tick under maximal cooperation, calibrated against the simulation's tick frequency and the desired group-formation timescale) are documented as part of the simulation's calibration budget rather than as universal constants.

2. **Given** the module-level docstring at `factions.py:1-23`, **When** auditing the Known Limitations block (if present), **Then** a dedicated "Known Limitations" subsection exists at the end of the module docstring that enumerates: (a) the schism detection order-dependence per F-4, with the explicit note that a future migration to a robust clustering algorithm (e.g. graph-based connected components on the sentiment graph, or hierarchical clustering with average-linkage on the sentiment matrix) is bound to a separate work item; (b) the cohesion delta coefficients are tunable per F-3; (c) the leadership weights are tunable per F-1; (d) the cluster-detection greedy algorithm in `_detect_and_propose_factions()` shares the same order-dependence as the schism detection and is noted under the same item.

3. **Given** the inline comment at `factions.py:465-468` (the existing buried Known Limitation note), **When** the docstring promotion of Acceptance Scenario 2 is applied, **Then** the inline comment is preserved (it documents the local code path for a reader who lands at that line) but is shortened to a single-line forward reference to the module docstring's Known Limitations block.

---

### User Story 3 — Optional UNJUSTIFIED additions surfaced by Round 2 (Priority: P3)

If the Round 2 re-audit, in its fresh-eyes scope (per Constitution Principle III — the auditor has a mandate to find NEW issues, not just verify the R1 catalogue), surfaces additional UNJUSTIFIED parameters that were not in the R1 catalogue, those findings are admitted to this branch's scope at the auditor's discretion. Likely candidates include:

- `_SCHISM_OUTWARD_SENTIMENT_THRESHOLD = -0.2` at `factions.py:55` — a hostility threshold below which a subcluster's average sentiment toward non-allies triggers a schism. Currently documented as "negative sentiment below -0.2 indicates genuine hostility, not mere indifference" without further empirical grounding.
- `_ALLY_SENTIMENT_THRESHOLD = 0.2` at `factions.py:58` — the dual threshold above which two agents are considered allies for cluster-detection purposes.
- The `internal_sentiment = 0.3` fallback (`factions.py:151`) for the no-established-relationships case in `compute_leadership_score()` — set "slightly below neutral" without empirical grounding.
- The `leader_sentiment = 0.3` fallback (`factions.py:218`) in `compute_legitimacy()` — same pattern.
- The `leader_effectiveness = -0.1` value (`factions.py:314`) for leaderless groups — "Leaderless groups destabilize" without grounding.
- The `-0.05` cohesion penalty for leadership transitions (referenced in `update_group_leadership()` docstring) — "power struggle cost" without grounding.
- The splinter group seed cohesion `cohesion=0.5` (`factions.py:508`) — fresh-faction default without grounding.
- The cohesion penalty `group.cohesion - 0.1` (`factions.py:529`) applied to the parent group when a schism completes — without grounding.

**Why this priority**: P3 because the R1 catalogue does not require these closures and the auditor may rule them in or out depending on whether they are independently INCORRECT/UNJUSTIFIED or merely calibration-budget parameters that fit the existing tunable-design-parameter discipline. The fix path for each additional finding is uniform: add the missing tunable-disclaimer language to the inline comment and to the module docstring's Known Limitations block.

**Independent Test**: dispatch Round 2 audit; if verdict is CONVERGED on R1 findings (F-1 through F-4) but the auditor flags additional findings, the fix-implementer adds the missing disclaimer language in a single follow-up commit and the audit re-runs to confirm closure.

**Acceptance Scenarios**:

1. **Given** the Round 2 audit verdict report, **When** the auditor surfaces additional UNJUSTIFIED parameters beyond F-3, **Then** each additional finding is addressed with the same tunable-disclaimer language pattern (inline comment + Known Limitations entry) without behavioral change; the additional fix is committed under the same User Story 3 with the commit message `docs(agents): close round 2 fresh-pass UNJUSTIFIED findings on factions tunable parameters`.

2. **Given** the auditor's verdict does NOT surface additional findings, **When** US3 is the final User Story, **Then** US3 is closed without a commit and the branch proceeds directly to US4.

---

### User Story 4 — Promote §8.1 → §4.7 in bilingual whitepaper after Round 2 CONVERGED (Priority: P1)

After the Round 2 re-audit verdict is CONVERGED, the factions module must be promoted from `§8.1 Factions` (currently chapter 8 first slot after the Branch 4 §8.1 → §4.6 promotion renumbered Factions to §8.1) to a new `§4.7 Factions` (audited Methods) of the bilingual whitepaper. This is the campaign deliverable that closes the branch.

**Why this priority**: P1 — closes the branch and unlocks the next campaign branch (Knowledge Graph + Economy base layer, currently §8.2 and §8.3 respectively).

**Independent Test**: whitepaper EN+IT both contain a new `§4.7 Factions` chapter following the canonical Methods schema (Background, Model, Equations, Parameters table, Algorithm, Simplifications, Status header). `§8.1` is removed and subsequent `§8.x` renumbered (§8.2 Knowledge Graph → §8.1, §8.3 Economy base layer → §8.2). README EN+IT status table flips the factions module to "yes (CONVERGED YYYY-MM-DD round 2)". Doc-sync memory `feedback_whitepaper_doc_sync.md` adds 1 mapping row for `epocha/apps/agents/factions.py` → §4.7.

**Acceptance Scenarios**:

1. **Given** Round 2 audit CONVERGED on the factions module, **When** inspecting the whitepaper EN at `§4`, **Then** a new `§4.7 Factions` chapter exists following the canonical Methods schema; `§8.1` is removed; subsequent `§8.x` are renumbered (Knowledge Graph → §8.1, Economy base layer → §8.2).

2. **Given** EN promotion applied, **When** inspecting the IT mirror, **Then** the same structure exists translated, with equation numbering preserved.

3. **Given** the promotion commit, **When** inspecting `README.md` and `README.it.md` status table, **Then** the factions module row shows "yes (CONVERGED YYYY-MM-DD round 2)" / "sì (CONVERGENTE YYYY-MM-DD round 2)".

4. **Given** the promotion commit, **When** inspecting `docs/memory-backup/feedback_whitepaper_doc_sync.md`, **Then** one new mapping row exists for `epocha/apps/agents/factions.py` → `§4.7`.

5. **Given** the merge commit on develop, **When** running a follow-up commit `docs: pin factions chapter 4.7 frozen-at-commit`, **Then** the §4.7 status header in EN+IT replaces `<filled-on-merge>` with the merge SHA.

---

### Edge Cases

- **Round 2 surfaces > 3 new findings (scope explosion)**: factions.py is the largest module in this campaign (876 LOC) and the Round 2 audit operates with the explicit mandate to find new issues. If the fresh-eyes pass produces more than 3 new INCORRECT/UNJUSTIFIED findings beyond the R1 catalogue, STOP and escalate to user before bundling them into US3 — a separate spec may be warranted to keep this branch tractable.
- **F-4 escalation to robust clustering**: if the Round 2 auditor rejects the doc-only resolution for F-4 (insisting on graph-based connected components or hierarchical clustering with average-linkage on the sentiment matrix), the branch scope expands materially (algorithm choice decision, complexity analysis, regression on all schism tests, possible behavior change in detection rate). Escalate to user before any behavioral expansion; this is a scope-positive item that belongs to its own spec under a future "robust faction clustering" work item.
- **Concurrency findings on `Group.cohesion` / `Group.leader` / `Agent.group` writes**: the Round 2 auditor must check that mutations to these fields are inside `transaction.atomic` blocks where required (e.g. inside `_check_schism` which creates a `Group` row AND mutates `Agent.group` for each ally AND creates `Memory` rows). If the auditor flags lost-update potential under parallel simulation runs, the fix wraps the affected blocks in `transaction.atomic` and adds a regression test under `test_factions.py` for the concurrent-write invariant.
- **DRY drift against Branch 1+2+3+4 helpers**: the Round 2 auditor must verify that `compute_affinity()` (Branch 2 affinity.py) is the only path used for personality-affinity computations within factions.py; if a local re-implementation has crept in, the fix replaces it with the canonical call. Same for any reputation lookups (Branch 1).
- **Bare `except Exception` audit**: the Round 2 auditor checks for any `except Exception` blocks that hide a more specific exception type that should be caught explicitly. Current code at `factions.py:282-285` uses `except (json.JSONDecodeError, TypeError)` which is correctly specific; the auditor verifies this discipline holds across the file.
- **N+1 query audit**: the per-group loop in `process_faction_dynamics()` (`factions.py:81-86`) calls `update_group_cohesion`, `update_group_leadership`, `_check_dissolution`, `_check_schism` for each active group. Each of these may issue its own queries against `Agent`, `Relationship`, `DecisionLog`, `Memory`. The Round 2 auditor checks for missing `select_related`/`prefetch_related` annotations that would cause N+1 patterns at scale (50+ groups in a single simulation).
- **Citation drift in whitepaper §13**: Stogdill (1948), Judge et al. (2002), Dunbar (1992), Festinger et al. (1950), Olson (1965), Axelrod (1984), Baumeister et al. (2001), Weber (1922), Iannaccone (1992), Antonakis et al. (2016), Hackman (2002) — the whitepaper §13 bibliography must carry full entries for every author cited in the new §4.7 chapter. Cross-check at T003 before any §13 edit; add missing entries with DOI or ISBN as available.
- **Pre-remediated state drift**: the partial doc mitigations already in factions.py docstrings (R1 catalogue describes the pre-mitigation state, current code carries softened wording) mean US1 acceptance scenarios are documentation refinements rather than fresh writes. The plan tasks must re-verify at T003 before any commit.
- **Test count drift**: factions.py has 153 test LOC across multiple `Test*` classes. If the fix-implementer adds new tests for the tunable-disclaimer documentation (unusual — docs don't need tests), the pytest baseline gate must account for the delta. Default expectation: pytest baseline holds (no new tests for doc-only fixes).
- **Pytest skip without authorization**: per Constitution Principle V, no `pytest.mark.skip` may be introduced. If a Round 2 finding forces a test to be skipped, escalate to user.
- **Whitepaper §8 renumbering ripple**: any narrative reference to "§8.1 Factions" elsewhere in the whitepaper (the Discussion of §10 and the Roadmap of §9 both reference §8.x sections by number) must be updated in lock-step with the renumbering. The plan tasks must include a full-document grep pass for `§8.x` references before the promotion commit.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST reframe the `compute_leadership_score()` docstring and the module-level "Scientific basis" header to cite Stogdill (1948) ONLY for the principle that traits correlate with leadership emergence, NOT for the specific weighted formula; add Judge et al. (2002) `J Appl Psychol 87(4):765-780` as the primary meta-analytic reference for Big Five trait effect sizes; label the weights (0.30/0.20/0.15/0.20/0.15) as tunable design parameters; correctly attribute charisma to Weber (1922) or to its modern operationalization rather than imply it is a Stogdill trait. Closes F-1.
- **FR-002**: System MUST reframe the `update_group_cohesion()` size-penalty threshold of 5 as a tunable design parameter; the Dunbar (1992) citation MUST be either dropped entirely or retained only with a clarifying note that the threshold is NOT derived from Dunbar's nested-group hierarchy (in which "5" is the intimate-clique stratum, not a coordination cost boundary); coordination cost above a small-group threshold MUST be described as a generic principle in organizational psychology without claiming a specific empirical anchor. Closes F-2.
- **FR-003**: System MUST reframe the four cohesion-delta coefficients (0.10 cooperation, 0.15 conflict, 0.02 size penalty, 0.05 leader effectiveness) at `factions.py:316-321` as tunable design parameters; Baumeister et al. (2001) MUST be retained only as the source of the *qualitative direction* of the asymmetry (negativity bias), NOT as the source of the 1.5:1 ratio; the absolute magnitudes MUST be documented as part of the simulation's calibration budget tied to tick frequency and desired group-formation timescale. Closes F-3.
- **FR-004**: System MUST promote the schism detection order-dependence limitation (currently buried inline at `factions.py:465-468`) to the module docstring's Known Limitations block at `factions.py:1-23`; the inline comment MUST be preserved but shortened to a single-line forward reference to the module docstring; the same order-dependence in `_detect_and_propose_factions()` cluster building MUST be acknowledged in the same Known Limitations entry. Closes F-4 via doc-only resolution; behavioral fix (graph-based clustering) bound to a future "robust faction clustering" work item.
- **FR-005**: System MUST add a dedicated "Known Limitations" subsection to the module docstring (`factions.py:1-23`) enumerating: (a) schism + cluster detection order-dependence per FR-004; (b) cohesion delta coefficients as tunable per FR-003; (c) leadership weights as tunable per FR-001; (d) Dunbar size-penalty threshold as a design choice per FR-002.
- **FR-006**: System MAY (optional, per Round 2 auditor verdict) add tunable-disclaimer language to additional parameters surfaced by the Round 2 fresh-eyes pass, including `_SCHISM_OUTWARD_SENTIMENT_THRESHOLD`, `_ALLY_SENTIMENT_THRESHOLD`, the no-relationship fallback values `0.3`, the leaderless-group value `-0.1`, the leadership-transition penalty `-0.05`, the splinter seed cohesion `0.5`, and the parent-cohesion-penalty `0.1`. Each addition follows the FR-003 disclaimer pattern.
- **FR-007**: System MUST reach Round 2 audit CONVERGED verdict before whitepaper promotion. The audit MUST check: (a) all R1 findings closed; (b) no new INCORRECT/UNJUSTIFIED introduced by the fix commits; (c) concurrency discipline on `Group.cohesion`/`Group.leader`/`Agent.group`/`Memory` writes; (d) DRY against `affinity.py` and other audited helpers; (e) bare `except Exception` discipline (none expected); (f) N+1 query patterns in the per-group loop.
- **FR-008**: System MUST promote `§8.1 Factions` → `§4.7 Factions` in bilingual whitepaper per User Story 4 acceptance scenarios, including renumbering subsequent §8.x sections (Knowledge Graph → §8.1, Economy base layer → §8.2) and updating all internal cross-references in §9 and §10 body text.
- **FR-009**: System MUST verify the §13 whitepaper bibliography carries entries for every author cited in the new §4.7 chapter: Stogdill (1948), Judge et al. (2002), Festinger et al. (1950), Olson (1965), Axelrod (1984), Baumeister et al. (2001). Dunbar (1992) entry is removed only if the citation is dropped per FR-002. Weber (1922), Iannaccone (1992), Antonakis et al. (2016), Hackman (2002) added if introduced by the FR-001 / FR-002 rewrites. Each entry uses DOI when available and ISBN for pre-DOI monographs.
- **FR-010**: System SHOULD preserve all existing inline disclaimers on parameters that are NOT in the R1 catalogue and that the Round 2 auditor does NOT flag in the fresh-eyes pass; Round 2 verifies they have not regressed during this branch's work.

### Key Entities

- **Agent.group, Agent.charisma, Agent.intelligence, Agent.wealth, Agent.is_alive** (existing model `epocha/apps/agents/models.py`): no schema change.
- **Group.cohesion, Group.leader, Group.parent_group, Group.formed_at_tick, Group.simulation, Group.objective, Group.name** (existing): no schema change.
- **Relationship.sentiment, Relationship.agent_from, Relationship.agent_to** (existing): no schema change.
- **Memory.content, Memory.tick_created, Memory.emotional_weight, Memory.source_type, Memory.is_active, Memory.agent** (existing): no schema change.
- **DecisionLog.output_decision, DecisionLog.tick, DecisionLog.agent_id, DecisionLog.simulation** (existing): no schema change.
- **Whitepaper EN/IT** (`docs/whitepaper/epocha-whitepaper.{md,it.md}`): receives new `§4.7` chapter, loses `§8.1` (factions), renumbers §8.2-§8.3 to §8.1-§8.2. Up to 4 new §13 citations possible (Judge 2002 added; Weber/Iannaccone/Antonakis/Hackman conditionally added; Dunbar conditionally removed).
- **README EN/IT**: status table update for factions row.
- **Doc-sync memory** (`docs/memory-backup/feedback_whitepaper_doc_sync.md` + live): 1 new mapping row.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Round 2 `critical-analyzer` audit on `epocha/apps/agents/factions.py` returns verdict CONVERGED with zero INCORRECT, zero UNJUSTIFIED unresolved, zero MISSING unresolved.
- **SC-002**: `pytest --cov=epocha -v` passes with zero failures (baseline measured at T002; expected ≥809 after Branch 4 closure; expected baseline unchanged with doc-only fixes; baseline + N if Round 2 concurrency findings force regression test additions).
- **SC-003**: Whitepaper EN at `§4.7` contains the canonical Methods-schema chapter; `§8.1` removed; subsequent `§8.x` sections renumbered to §8.1-§8.2; all narrative cross-references updated.
- **SC-004**: Whitepaper IT mirrors §4.7 structure with translated content and identical equation numbering.
- **SC-005**: README EN+IT status table row for the factions module shows "CONVERGED YYYY-MM-DD round 2" / "CONVERGENTE YYYY-MM-DD round 2".
- **SC-006**: Doc-sync memory `feedback_whitepaper_doc_sync.md` contains 1 new mapping row for `epocha/apps/agents/factions.py` → `§4.7`.
- **SC-007**: Branch merged to develop via PR with merge commit; `<filled-on-merge>` placeholder in the new §4.7 status header replaced with merge SHA in a follow-up commit on develop.

## Assumptions

- The Round 1 audit findings catalogue (user-supplied, 4 items F-1 through F-4) is the authoritative input. No re-running of the original Round 1 audit; Round 2 verification + fixes go directly into execution.
- The fix-implementer prefers the lowest-risk path per Constitution Principle V; documentation upgrades are sufficient for all four Round 1 findings (F-1, F-2, F-3, F-4 all accept doc-only resolutions per spec).
- The Round 2 auditor operates with the explicit mandate to find new issues beyond the R1 catalogue (per Constitution Principle III). Reasonable scope ceiling: ≤3 new INCORRECT/UNJUSTIFIED findings rolled into US3; beyond that, escalate.
- The whitepaper promotion procedure follows the standard documented in project memory `project_whitepaper_promotion_pipeline.md` and reproduced in Branch 1, 2, 3, 4 tasks files.
- No new external runtime dependencies introduced. No graph-clustering library (networkx clustering, scikit-learn hierarchical) added in this branch.
- No migration on existing models. No schema change. The R1 + R2 resolutions are purely documentation refinements.
- Italian whitepaper translation follows the established style from prior promotions.
- Pytest runs in Docker via `docker compose -f docker-compose.local.yml exec -T web pytest`.
- All 4 Round 1 findings carry partial mitigations already in the code (softened docstring language, buried inline limitation note). The spec treats them as "verify and strengthen" rather than "fix from scratch", but the plan must include a fallback fix-path if verification fails.
- The Round 2 fresh-eyes pass on this 876-LOC module is expected to take longer than the comparable Branch 4 audit on the 250-LOC movement module; the audit-dispatch task must budget accordingly.

## Constitution Compliance

This spec is constitutional-compliant per `.specify/memory/constitution.md` v1.0.0:

- **Principle I (Scientific Method)**: every Round 1 finding resolution must produce either a corrected citation (Judge 2002 added per FR-001; Dunbar attribution dropped or qualified per FR-002; Baumeister scope narrowed per FR-003), an explicit Known Limitation (FR-004 schism order-dependence; FR-005 docstring promotion), or a documented tunable parameter (FR-001 leadership weights; FR-002 size threshold; FR-003 cohesion coefficients; FR-006 optional Round 2 additions). No magic numbers introduced.
- **Principle II (Verify Before Asserting)**: every file path, function signature, and line range mentioned in this spec was verified against current code on develop @ commit `0afca1d` (post Branch 4 closure).
- **Principle III (Adversarial Audit)**: Round 2 audit dispatch via `critical-analyzer` subagent is mandatory before any whitepaper promotion. Convergence loop: audit → fix → re-audit → CONVERGED, or repeat. The auditor has explicit mandate to find new issues; US3 admits up to ~3 additional findings.
- **Principle IV (Three-Step Design)**: this spec is the consolidated output of the Round 1 audit catalogue + controller-side re-review; no further design iteration before plan.
- **Principle V (Evidence-Based Verification)**: pytest gate at every fix commit; promotion requires Round 2 CONVERGED verdict. No `pytest.mark.skip` without explicit user authorization.

## Out of Scope

- Round 1 audit re-execution (already done 2026-04-12, output is the input to this spec).
- Other campaign branches (Knowledge Graph, Economy base layer) — separate Spec Kit features in subsequent timestamps.
- Demography Plan 4 (engine wiring) — post-campaign work item.
- Validation experiments execution — post-campaign work item.
- Behavioral F-4 fix (graph-based connected-components or hierarchical clustering on the sentiment matrix to replace the order-dependent greedy seed loop) — bound to a future "robust faction clustering" work item; this branch resolves F-4 with documentation only.
- Behavioral concurrency hardening (wrapping `_check_schism`, `_create_faction`, and similar Group/Agent/Memory write blocks in `transaction.atomic`) — admitted only if the Round 2 auditor flags lost-update potential; otherwise out of scope and deferred to a future "concurrent simulation runs hardening" item.
- Iannaccone (1992) club-goods costly-signal cohesion mechanism — explicitly NOT implemented per the current whitepaper §8.1 narrative; bound to a future "club-goods cohesion mechanics" work item.
- Faction-to-faction relationship modeling (alliance, war, treaty) — out of scope; current code models only intra-faction dynamics.
- LLM-driven faction identity generation review (`_generate_faction_identity` referenced at `factions.py:497`) — covered by a separate llm-adapter audit branch, not by this branch.

---
description: "Tasks for political-cluster audit re-pass — Round 1 catalogue to CONVERGED + chapter 4.5 promotion"
---

# Tasks: Political Cluster Audit Re-pass (Round 2)

**Input**: Design documents from `specs/20260516-120927-political-cluster-audit-repass/`

**Prerequisites**: spec.md (20 findings + 2 already-closed cross-module → 4 user stories), plan.md (Constitution Check PASS, no data-model/contracts/quickstart), research.md (Weber+Merolla-Zechmeister+Miller-Lynam DOIs + X-1 layering decision + G-2 fix-safety)

**Tests**: included — FR-021 mandates invariant test suite (wealth conservation + dead-constant absence). Plus regression pytest gate.

**Organization**: tasks grouped by Spec user story. MVP = US1 (5 INCORRECT findings closed → unblocks promotion path). US2 + US3 + US4 incremental.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: parallel-safe (different files, no dependencies)
- **[Story]**: US1/US2/US3/US4/SETUP/FOUND/POLISH
- Absolute or repo-relative file paths

## Path Conventions

Django backend single project. Source at `epocha/apps/world/`, tests at `epocha/apps/world/tests/`, whitepaper at `docs/whitepaper/`.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: pre-flight verification before any fix.

- [ ] T001 [SETUP] Verify Docker compose stack up: `docker compose -f docker-compose.local.yml ps`. Start if needed with `docker compose -f docker-compose.local.yml up -d`. Confirm web container healthy via `docker compose -f docker-compose.local.yml exec -T web python -c "import django; print(django.get_version())"`.
- [ ] T002 [SETUP] Baseline pytest run: `docker compose -f docker-compose.local.yml exec -T web pytest 2>&1 | tail -5`. Record baseline count (expected ≥804 after Branch 2 closure). Pin the number in a scratch note for downstream gate comparisons.
- [ ] T003 [SETUP] Re-verify Round 1 finding code references still match develop @ `1c75854`. Spot-check 8 critical line refs from spec.md: `government.py:84-85` (_COUP_SUCCESS_THRESHOLD deprecation comment), `government.py:587` (random.random() stochastic coup), `government.py:296-302` and `government.py:675-680` (economy=stability_index Note blocks), `government.py:339-342` (X-1 layering Note), `stratification.py:207-212` (S-3 Miller-Lynam inline cite), `stratification.py:58-63` (S-4 loss-aversion ratio docstring), `stratification.py:271-278` (S-2 wealth flow — verify whether world.global_wealth is decremented on skim), `election.py:28-30` (E-1 charisma citations), `election.py` full file (E-2 absence of `_memory_influence_score`), `institutions.py:55-59` (I-3 linear-decay clarifying comment). Record drift in a scratch note before proceeding.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: shared scaffolding that other user-story tasks build on, plus the single behavioral fix (S-2) that the invariant test requires.

- [ ] T004 [FOUND] Create new file `epocha/apps/world/tests/test_political_invariants.py` with module docstring describing it as "Cross-module invariant test suite for the political institutions cluster — wealth conservation, dead-constant absence, naming-clarity contracts per Constitution Principle V". Empty test module scaffold; concrete tests added in T011/T015/T036.
- [ ] T005 [FOUND] In `epocha/apps/world/stratification.py:process_corruption` (around lines 271-278), enforce wealth conservation: every increment to a corrupt agent's `wealth` MUST be matched by an equal decrement of `world.global_wealth` in the same `transaction.atomic` block. If the current code already decrements (verified at T003), this task becomes a doc-only "make the invariant explicit in the function docstring". If not, the fix: capture `skim_amount`, do `agent.wealth += skim_amount; world.global_wealth -= skim_amount; agent.save(update_fields=['wealth']); world.save(update_fields=['global_wealth'])` inside `transaction.atomic`.
- [ ] T006 [FOUND] Run targeted test: `docker compose -f docker-compose.local.yml exec -T web pytest epocha/apps/world/tests/test_stratification.py -v`. Verify all existing green; no regression from T005.

**Checkpoint**: foundation ready. User stories can begin.

---

## Phase 3: User Story 1 — Close 5 INCORRECT findings (Priority: P1) 🎯 MVP

**Goal**: close G-1, G-2 (verify), S-1, S-2 (verify behavior), E-1 + record E-2 closed-by-Branch-1.

**Independent Test**: dispatch Round 2 critical-analyzer audit limited to these five findings (+ E-2 absence check); verdict CONVERGED for each.

### G-1 — Powell-Thyne cited as dataset only, not formula source

- [ ] T007 [US1] In `epocha/apps/world/government.py` `check_coups` docstring (around lines 522-548), rewrite the Powell-Thyne attribution: cite P&T 2011 *only* as the empirical dataset source for the ~50% coup-success base-rate calibration. Remove any "Table 2" or "formula from P&T" language. Add explicit "The multi-term weighted success-probability formula is a simulation design parameter inspired by the coup literature (Powell & Thyne 2011 dataset; Belkin & Schofer 2003 on coup risk factors); weights are tunable."

### G-2 — Stochastic coup verification + optional dead-constant removal

- [ ] T008 [US1] Re-verify on develop tip that `government.py:587` uses `random.random() < success_probability` (already confirmed at T003). Verify `_COUP_SUCCESS_THRESHOLD` at line 85 carries the "no longer used" comment. Decision: leave constant in place with explicit `# DEPRECATED: retained as reference calibration point only; not used in any decision branch (verified Round 2)` OR remove the constant entirely. Default to remove since grep returned zero non-declaration references (per research.md Lookup 4). If removed, also delete the line-84 comment.

### S-1 — Gilbert 2011 inspiration with acknowledged simplification

- [ ] T009 [US1] In `epocha/apps/world/stratification.py` (around lines 25-31), verify the existing docstring already says "Simplified 5-class model inspired by Gilbert (2011) but with adjusted thresholds for simulation dynamics. Gilbert's original model uses 6 classes with different boundaries (capitalist 1%, ...)". If yes, S-1 is already closed by interim commits — record in commit message. If the wording is weaker than this, strengthen it to explicit "inspired by ... simplified to 5 classes ... percentile thresholds adjusted".

### S-2 — Wealth-conservation behavioral fix verified

- [ ] T010 [US1] Re-confirm T005 covered the wealth-conservation invariant. Extend `stratification.py:process_corruption` docstring with an "Invariant" block: "Wealth conservation: every skim increment to an agent's wealth is matched by an equal decrement of `world.global_wealth` within the same atomic transaction. Test: `test_political_invariants.test_corruption_conserves_total_wealth`."
- [ ] T011 [US1] Add invariant test in `epocha/apps/world/tests/test_political_invariants.py`: `test_corruption_conserves_total_wealth`. Setup: simulation + world (initial `global_wealth`=W₀) + 3 agents (head-of-state with conscientiousness < 0.4, two others with conscientiousness ≥ 0.4). Pre-condition: `total = sum(agent.wealth) + world.global_wealth`. Call `process_corruption(simulation, tick=10)`. Post-condition: `sum(agent.wealth) + world.global_wealth == total` within `1e-6` float tolerance.
- [ ] T012 [US1] Run targeted: `pytest epocha/apps/world/tests/test_political_invariants.py epocha/apps/world/tests/test_stratification.py -v`. Green.

### E-1 — Replace Zonis with Weber + Merolla-Zechmeister

- [ ] T013 [US1] In `epocha/apps/world/election.py` (around lines 28-30), verify the existing citation is `Weber 1922` (already confirmed at T003). If Zonis & Joseph (1994) appears anywhere in the file, remove it. Strengthen the inline comment to: "Charisma contribution to vote: theoretically grounded in Weber (1922) on charismatic authority; empirically supported by Merolla & Zechmeister (2011) on Chávez's charisma and Venezuelan vote choice. Optional secondary: Bass (1985) on transformational leadership."

### E-2 — Verify dead code already removed by Branch 1

- [ ] T014 [US1] Run `grep -rn "_memory_influence_score" epocha/apps/world/election.py`. Expected zero matches. Record E-2 as ALREADY CLOSED by Branch 1 in commit message at T016. If matches found unexpectedly, escalate to user.

### US1 checkpoint

- [ ] T015 [US1] Full pytest gate: `docker compose -f docker-compose.local.yml exec -T web pytest 2>&1 | tail -3`. Expected baseline + 1 new invariant test (from T011) = baseline+1 passed.
- [ ] T016 [US1] Commit `fix(world): close round 1 INCORRECT findings G-1 G-2 S-1 S-2 E-1 + verify E-2 in political cluster`. Stage only the touched files: `government.py`, `stratification.py`, `election.py`, `tests/test_political_invariants.py`, and `tests/test_stratification.py` if touched.

---

## Phase 4: User Story 2 — Close 2 INCONSISTENT findings (Priority: P1)

**Goal**: verify E-5 already-cached, document X-1 corruption layering as deliberate co-existence.

**Independent Test**: dispatch Round 2 audit subset on resolved files; verdict CONVERGED.

### E-5 — Verify voter count already cached

- [ ] T017 [US2] Run `grep -n "len(list(voters))" epocha/apps/world/election.py`. Expected zero matches. Verify `voters.count()` or equivalent cached value is used. Record E-5 as VERIFIED CLOSED in commit message. If the N+1 pattern is still present, fix: capture `voter_count = voters.count()` before the manipulation-bonus loop and reuse inside.

### X-1 — Document corruption layering at BOTH sites

- [ ] T018 [US2] In `epocha/apps/world/government.py` around lines 339-342, verify the existing `Note: corruption was already adjusted by stratification.py:process_corruption earlier in this ... both independently influence the corruption index within the same cycle.` block. Strengthen if needed to explicitly say: "Layering is DELIBERATE: step 3 (stratification.process_corruption) models personality-driven petty corruption by head-of-state (driver: agent conscientiousness; ref: Miller-Lynam 2001). Step 4 (this function, update_government_indicators) models institutional-oversight-driven systemic corruption pressure (driver: justice+bureaucracy+media oversight, bounded by government_type.corruption_resistance; ref: Acemoglu-Robinson 2006). The two compose additively within `_clamp([0,1])`. See research.md Lookup 3 for the design decision."
- [ ] T019 [US2] In `epocha/apps/world/stratification.py:process_corruption` docstring, add a mirror Note block: "This function applies the personality-driven petty-corruption layer. The institutional-oversight layer is applied later in the same tick by `government.update_government_indicators` (see lines 335-347 there). The two layers are deliberately separate; see research.md Lookup 3."

### US2 checkpoint

- [ ] T020 [US2] Full pytest gate. Expected baseline + 1 (no new tests in this phase).
- [ ] T021 [US2] Commit `fix(world): close round 1 INCONSISTENT findings E-5 X-1 in political cluster`. Stage: `government.py`, `stratification.py`.

---

## Phase 5: User Story 3 — Close 12 UNJUSTIFIED + 1 MISSING findings (Priority: P2)

**Goal**: documentation upgrades + citation cleanup + naming clarification per US3 acceptance scenarios.

### G-3 — Trust-decay 0.05 per tick documentation

- [ ] T022 [US3] In `epocha/apps/world/government.py` around lines 49-56 (current Freedom House annual repression trend comment), strengthen to: "Trust-decay rate `0.05` per tick is a tunable design parameter inspired by Freedom House annual repression-trend reports (e.g. *Freedom in the World 2024*). Assuming 1 tick ≈ 1 month, 0.05/tick corresponds to ~60% trust erosion over 24 months of zero counter-investment, consistent with the qualitative pattern observed in declining democracies. Specific magnitude tunable per `EPOCHA_GOVERNMENT_TRUST_DECAY_RATE` setting (if exposed)."

### G-4 — Remove "Polity IV Table 3" attribution

- [ ] T023 [US3] In `epocha/apps/world/government_types.py` around line 87 (and any other "Polity IV Table 3" attribution), remove the false citation. Replace with: "Transition condition thresholds are design parameters inspired by Acemoglu & Robinson (2006) on regime-transition dynamics and Geddes (1999) *What Do We Know About Democratization After Twenty Years?* on autocracy survival. Specific values tunable per government-type config."

### G-5 — Legitimacy weights documentation

- [ ] T024 [US3] In `epocha/apps/world/government.py` around the legitimacy weights (`_LEGITIMACY_W_HEALTH = 0.20`, `_LEGITIMACY_W_EDUCATION = 0.15`, `_LEGITIMACY_W_ECONOMY = 0.35`, `_LEGITIMACY_W_MEDIA = 0.30`), add a docstring block: "Legitimacy component weights are tunable design parameters. The economy-dominant weighting (0.35) reflects the broad consensus in political-economy literature (Lewis-Beck & Stegmaier 2000) that economic performance is the strongest single predictor of regime legitimacy in modern systems. Health and education weights anchor on welfare-state legitimacy literature; media weight reflects the role of information control in non-democratic regimes. Sum = 1.00."

### G-6 — Resolve economy/stability_index naming

- [ ] T025 [US3] In `epocha/apps/world/government.py:_update_stability` (around lines 670-690) and `update_government_indicators` (around lines 290-310), rename the local variable `economy` to `economy_proxy` for clarity. Update the inline `Note` block to: "`economy_proxy = world.stability_index`. `World.stability_index` is currently computed as average agent mood by the economy module (see `epocha/apps/world/economy.py`). It serves as a PROXY for economic conditions, not as a direct GDP-style indicator. When the new economy app exposes a dedicated economic-output indicator, replace this proxy with the direct reading." The rename is local-only; no public API change.

### GT-1 — Module disclaimer covers all 4 dicts

- [ ] T026 [US3] In `epocha/apps/world/government_types.py` module docstring (around lines 22-29), verify the existing disclaimer covers all four dictionaries (`repression_tendency`, `corruption_resistance`, `institution_effects`, `stability_weights`). If incomplete, extend to explicit list: "All values in `repression_tendency`, `corruption_resistance`, `institution_effects`, and `stability_weights` are design parameters inspired by qualitative patterns described in the cited literature (Polity IV, Freedom House, Acemoglu & Robinson 2006, Bueno de Mesquita et al. 2003). They are NOT directly derived from any single source; all are tunable per simulation calibration."

### S-3 — Threshold tunable + Miller-Lynam cite

- [ ] T027 [US3] In `epocha/apps/world/stratification.py:process_corruption` docstring (around lines 207-212), verify the existing Miller-Lynam (2001) inline citation is present and that Acemoglu-Robinson (2006) is NOT cited as the threshold source. Strengthen the wording: "The `CONSCIENTIOUSNESS_THRESHOLD = 0.4` is a tunable design parameter inspired by the personality-deviance link established in Miller & Lynam (2001) meta-analysis. Acemoglu & Robinson (2006) discusses institutional constraints on corruption, not personality cutoffs, and is NOT the source of this threshold."

### S-4 — Loss-aversion ratio documentation

- [ ] T028 [US3] In `epocha/apps/world/stratification.py` around lines 58-63 (mobility weights `_UPWARD_MOBILITY_WEIGHT = 0.4`, `_DOWNWARD_MOBILITY_WEIGHT = 0.7`), verify the existing docstring already explains "The ratio 0.7 / 0.4 = 1.75:1 (downward vs upward) is approximately consistent with the loss aversion coefficient of ~2:1 from Prospect Theory (Kahneman & Tversky 1979). The specific magnitudes (0.4 upward, 0.7 downward) are tunable design choices preserving the ratio anchor." Strengthen if weaker than this.

### E-3 — Vote weights documentation

- [ ] T029 [US3] In `epocha/apps/world/election.py` (around lines 26-32 and the `_W_RELATIONSHIP`, `_W_PERSONALITY`, `_W_ECONOMIC`, `_W_REPUTATION`, `_W_CHARISMA` constant block), add a docstring block: "Vote-component weights (relationship 0.25, personality 0.15, economic 0.20, reputation 0.25, charisma 0.15; sum = 1.00) are tunable design parameters. The cited literature (Lewis-Beck & Stegmaier 2000 *Annual Review of Political Science* 3, 183-219) establishes that economic performance is typically the largest single voting factor in democratic systems; future calibration may shift the economic weight upward. Current allocation balances structural (economic, reputation) and personal (charisma, personality) factors approximately equally."

### E-4 — Wealth-saturation cap derivation

- [ ] T030 [US3] In `epocha/apps/world/election.py` (around the `WEALTH_SATURATION = 100.0` constant), update its docstring: "Wealth-saturation cap `100.0` is anchored to the `Agent.wealth` default value of 50.0 (2× default). It is NOT derived from real-world median household wealth — that justification was circular (Agent.wealth default is itself a design choice). Tunable per `EPOCHA_ELECTION_WEALTH_SATURATION` if exposed."

### I-1 — INSTITUTION_EFFECT_SCALE timescale documentation

- [ ] T031 [US3] In `epocha/apps/world/institutions.py` around `INSTITUTION_EFFECT_SCALE = 20.0` (line 45), extend the docstring: "Scale factor 20.0 controls how fast government effects translate into institution-health delta per tick. Assuming 1 tick ≈ 1 month, 33 ticks ≈ 2.75 years to near-peak institution recovery from a baseline of 0.5, consistent with the qualitative timescale of state-capacity building observed in post-conflict institutional reform studies. Tunable design parameter."

### I-2 — Remove Gupta cite from FUNDING_EFFECT_RATE

- [ ] T032 [US3] In `epocha/apps/world/institutions.py` around `FUNDING_EFFECT_RATE = 0.04` (line 53), remove any Gupta et al. (2002) citation. Replace with: "Funding effect rate `0.04` per tick is a tunable design parameter controlling how strongly institution funding translates into health delta. NOT derived from Gupta et al. (2002) (which discusses public-spending vs poverty elasticity, off-topic for institution-health). Specific value tunable."

### I-3 — Verify linear-decay docstring correction

- [ ] T033 [US3] In `epocha/apps/world/institutions.py` around `ENTROPY_PER_TICK = -0.005` (lines 21 and 57-59), verify the existing clarifying comment "linear decay, not exponential half-life" is present. Strengthen the module docstring around line 21 to: "Entropy per tick `-0.005` implements LINEAR decay: institution health drops by `0.005` per tick of zero investment, reaching 50% of maximum after 100 ticks (NOT exponential half-life despite legacy 'half-life' language in earlier comments). Besley & Persson (2011) *Pillars of Prosperity* state-capacity dynamics inspired the timescale anchor; the specific rate is a tunable design choice."

### US3 checkpoint

- [ ] T034 [US3] Full pytest gate. Expected baseline + 1 (no new tests in this phase unless T036 added).
- [ ] T035 [US3] Optionally extend `test_political_invariants.py` with `test_coup_success_threshold_constant_deprecated_or_absent`: assert that `_COUP_SUCCESS_THRESHOLD` is either absent from `government.py` or carries a `DEPRECATED` marker in the source comment. Use `inspect.getsource(government_module)` or a file-read check.
- [ ] T036 [US3] Commit `fix(world): close round 1 UNJUSTIFIED findings G-3 G-4 G-5 G-6 GT-1 S-3 S-4 E-3 E-4 I-1 I-2 I-3 in political cluster`. Stage: `government.py`, `government_types.py`, `stratification.py`, `election.py`, `institutions.py`, `tests/test_political_invariants.py` (if T035 ran).

---

## Phase 6: Round 2 Adversarial Audit (Convergence Loop)

**Purpose**: per Constitution Principle III, re-audit before promotion. Loop until CONVERGED.

- [ ] T037 [US4 prep] Dispatch `critical-analyzer` subagent (Opus) for Round 2 audit on `epocha/apps/world/{government,government_types,stratification,election,institutions}.py` + new `tests/test_political_invariants.py`. Prompt includes: original 20 Round 1 findings + 2 already-closed-by-prior-branch findings + their resolution per US1+US2+US3 commits; mandate to verify each fix landed AND no new INCORRECT/UNJUSTIFIED introduced; new §13 citations (Weber 1922, Merolla-Zechmeister 2011, Miller-Lynam 2001) DOI-verified via Crossref; spec.md acceptance scenarios mapped to commits; verify X-1 layering documentation is sufficient at BOTH call sites; verify wealth-conservation invariant test exists and passes.
- [ ] T038 [US4 prep] If verdict NOT CONVERGED: dispatch fix-implementer for residual findings with same lowest-risk strategy. Repeat T037. Expect ≤2 round-trips per Branch 1+2 precedent.
- [ ] T039 [US4 prep] When verdict CONVERGED: record Round 2 audit transcript hash or summary in a brief commit note (not a new file under `docs/superpowers/`; per Spec Kit rule). Audit transcript may be embedded as appendix in the future tasks-completion log.

---

## Phase 7: User Story 4 — Whitepaper §8.1 → §4.5 Promotion (Priority: P1)

**Goal**: campaign deliverable. Promote 5 modules from designed-pending to audited-Methods.

### Whitepaper EN promotion

- [ ] T040 [US4] In `docs/whitepaper/epocha-whitepaper.md`, REMOVE `§8.1 Cluster: Political institutions (Government + Institutions + Stratification)` entirely (around line 1468). Renumber subsequent `§8.x`: §8.2 Movement → §8.1, §8.3 Factions → §8.2, §8.4 Knowledge Graph → §8.3, §8.5 Economy base layer → §8.4. Update all internal cross-references in the body (search for `§8.1`, `§8.2`, etc. throughout the document and update accordingly).
- [ ] T041 [US4] Insert new `§4.5` between current `§4.4 Rumor propagation` and `§5 Implementation`. Title: `## 4.5 Political institutions`. Status header: `> Status: implemented as of commit <filled-on-merge>, code audit CONVERGED 2026-05-16 round 2.`
- [ ] T042 [US4] §4.5 body — 5 sub-sections per canonical Methods schema:
  - §4.5.1 Government dynamics (Acemoglu-Robinson 2006 economic origins; Polity IV Marshall-Gurr 2020 regime classification; Powell-Thyne 2011 coup dataset for ~50% base rate; Freedom House annual indicators)
  - §4.5.2 Government types (12 government types as Polity-IV-anchored design parameters; Bueno de Mesquita et al. 2003 selectorate theory; Geddes 1999 autocracy survival)
  - §4.5.3 Social stratification (Gini coefficient; 5-class simplification inspired by Gilbert 2011; Acemoglu-Robinson 2006 on extractive institutions; Kahneman-Tversky 1979 loss aversion as mobility-asymmetry anchor; Miller-Lynam 2001 personality-deviance link for corruption threshold)
  - §4.5.4 Elections (Weber 1922 charismatic authority; Merolla-Zechmeister 2011 empirical charisma-vote link; Lewis-Beck-Stegmaier 2000 economic voting; Bass 1985 transformational leadership as optional secondary)
  - §4.5.5 Institutions (Besley-Persson 2011 state-capacity dynamics inspiring the linear-decay timescale; Acemoglu-Robinson 2012 *Why Nations Fail* on institution-health drivers)
  Each sub-section: Background, Model, Equations (numbered following the existing 4.1.x-4.4.x sequence), Parameters table, Algorithm, Simplifications (documenting G-1/G-2/G-3/G-4/G-5/G-6/GT-1/S-1/S-3/S-4/E-1/E-3/E-4/I-1/I-2/I-3/X-1 design parameters and known limitations explicitly), Status header.
- [ ] T043 [US4] In §13 of `epocha-whitepaper.md`, add the missing bibliography entries alphabetically (skip any already present from prior catch-up):
  - `Bass, B. M. (1985). *Leadership and Performance Beyond Expectations*. Free Press, New York. ISBN 978-0-02-901810-7.` (optional, only if §4.5.4 cites Bass as secondary)
  - `Geddes, B. (1999). What do we know about democratization after twenty years? *Annual Review of Political Science*, 2, 115-144. https://doi.org/10.1146/annurev.polisci.2.1.115`
  - `Lewis-Beck, M. S., and Stegmaier, M. (2000). Economic determinants of electoral outcomes. *Annual Review of Political Science*, 3, 183-219. https://doi.org/10.1146/annurev.polisci.3.1.183`
  - `Merolla, J. L., and Zechmeister, E. J. (2011). The nature, determinants, and consequences of Chávez's charisma: evidence from a study of Venezuelan public opinion. *Comparative Political Studies*, 44(1), 28-54. https://doi.org/10.1177/0010414010381076`
  - `Miller, J. D., and Lynam, D. (2001). Structural models of personality and their relation to antisocial behavior: a meta-analytic review. *Criminology*, 39(4), 765-798. https://doi.org/10.1111/j.1745-9125.2001.tb00940.x`
  - `Weber, M. (1922). *Wirtschaft und Gesellschaft: Grundriss der verstehenden Soziologie*. J.C.B. Mohr, Tübingen. English ed.: Weber, M. (1978). *Economy and Society* (G. Roth and C. Wittich, Eds. and Trans.). University of California Press, Berkeley. ISBN 978-0-520-03500-3.`

### Whitepaper IT mirror

- [ ] T044 [US4] Mirror T040 in `docs/whitepaper/epocha-whitepaper.it.md`: remove §8.1 IT, renumber §8.x.
- [ ] T045 [US4] Mirror T041+T042 in IT: insert `## 4.5 Istituzioni politiche` with 5 sub-sections translated, equation numbering identical to EN. Status header in IT: `> Stato: implementato a partire dal commit <filled-on-merge>, audit del codice CONVERGENTE 2026-05-16 round 2.`
- [ ] T046 [US4] [P] Mirror T043 in IT §13 (bibliography is verbatim EN/IT identical).

### README EN+IT status table

- [ ] T047 [US4] In `README.md` Status table flip 5 rows (government, government_types, stratification, election, institutions — currently listed under "Other modules (...)" or §8.1 cluster row) to `yes (CONVERGED 2026-05-16 round 2)`.
- [ ] T048 [US4] [P] Mirror T047 in `README.it.md` with `sì (CONVERGENTE 2026-05-16 round 2)`.

### Doc-sync memory

- [ ] T049 [US4] In `docs/memory-backup/feedback_whitepaper_doc_sync.md` mapping table add 5 rows:
  - `| epocha/apps/world/government.py | §4.5.1 (EN) | §4.5.1 (IT) |`
  - `| epocha/apps/world/government_types.py | §4.5.2 (EN) | §4.5.2 (IT) |`
  - `| epocha/apps/world/stratification.py | §4.5.3 (EN) | §4.5.3 (IT) |`
  - `| epocha/apps/world/election.py | §4.5.4 (EN) | §4.5.4 (IT) |`
  - `| epocha/apps/world/institutions.py | §4.5.5 (EN) | §4.5.5 (IT) |`
  Copy updated file to live memory at `~/.claude/projects/-Users-mauriziomocci-Documents-workspace-Opensource-epocha/memory/feedback_whitepaper_doc_sync.md`.

### US4 checkpoint

- [ ] T050 [US4] Full pytest gate. Expected baseline + 1 or 2 (whitepaper/README/memory edits don't touch tests; only T035 may have added an extra test).
- [ ] T051 [US4] Commit `docs: promote political cluster from chapter 8.1 to chapter 4.5 after audit CONVERGED`. Stage: 2 whitepapers, 2 READMEs, doc-sync memory backup.

---

## Phase 8: Polish & Closure

**Purpose**: branch closure per Spec Kit conventions + frozen-at-commit pin.

- [ ] T052 [POLISH] Push branch: `git push -u origin 20260516-120927-political-cluster-audit-repass`.
- [ ] T053 [POLISH] Open draft PR via `gh pr create --base develop --head 20260516-120927-political-cluster-audit-repass --title "fix(science): political cluster Round 2 audit CONVERGED + promote to whitepaper §4.5" --body "..."`. Body summarizes 20 Round 1 findings closed + 2 closed-by-prior-branch + Round 2 verdict + whitepaper promotion + Spec Kit conformance.
- [ ] T054 [POLISH] `gh pr merge <PR#> --merge --delete-branch`. Pull develop.
- [ ] T055 [POLISH] Frozen-at-commit pin: in `docs/whitepaper/epocha-whitepaper.md` and `.it.md`, replace 2 placeholders `<filled-on-merge>` in §4.5 status headers with the merge commit SHA from `gh pr view <PR#> --json mergeCommit -q .mergeCommit.oid`. Commit `docs: pin political cluster §4.5 frozen-at-commit`. Push develop.
- [ ] T056 [POLISH] Update project memory: edit `~/.claude/projects/-Users-mauriziomocci-Documents-workspace-Opensource-epocha/memory/project_session_resume_2026_05_16.md` to mark political-cluster CLOSED + record next-step pointer to movement branch. Sync to `docs/memory-backup/`. Commit `docs: mark political cluster session resume CLOSED + memory sync`. Push develop.

---

## Dependencies

| From | Blocks |
|------|--------|
| T001-T003 (SETUP) | all subsequent |
| T004-T006 (FOUND new test file + S-2 verify/fix) | T011 (invariant test depends on T004 file + T005 fix) |
| T011 wealth-conservation test | T015 pytest gate |
| T016 US1 commit | T017+ US2 (can begin in parallel with US3 actually but sequential simpler) |
| T021 US2 commit | T022+ US3 |
| T037 CONVERGED | T040+ US4 promotion |
| T051 promotion commit | T052-T056 closure |

## Parallel Opportunities

- T043 and T046 ([P] EN and IT whitepaper §13 additions — different files)
- T047 and T048 ([P] EN and IT README status table)
- US2 and US3 fixes can interleave on different files (X-1 in government.py+stratification.py / GT-1 in government_types.py / I-1/I-2/I-3 in institutions.py) — but pytest gate between US blocks recommended for traceability.

## MVP Suggestion

US1 (T007-T016) IS the MVP: the 5 INCORRECT findings unblock the whitepaper promotion path. Without US1 CONVERGED on those five, the promotion (US4) is blocked. US2+US3 can ship incrementally; US4 ships when all upstream CONVERGED.

## Format Validation

All 56 tasks above use the `- [ ] T<NNN> [TAG] description` checkbox format. Story tags map to `SETUP/FOUND/US1/US2/US3/US4/POLISH`. File paths absolute or repo-relative. Parallel markers `[P]` applied where independent.

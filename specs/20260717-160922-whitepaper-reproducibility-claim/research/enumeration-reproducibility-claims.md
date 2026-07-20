# Adversarial Enumeration of Reproducibility Claims in Both Whitepapers

**Agent**: critical-analyzer (adversarial mode)
**Date**: 2026-07-17
**Scope**: All reproducibility/determinism claims in `docs/whitepaper/epocha-whitepaper.md` (EN) and `epocha-whitepaper.it.md` (IT)
**Method**: Each claim verified against source code; each EN claim cross-checked against its IT counterpart one-by-one (not derived by offset)

## Three code facts that decide every verdict

1. **Every agent decision at every tick** is an unseeded LLM call at temperature 0.7: `epocha/apps/agents/decision.py:381-386` (`client.complete(prompt=..., temperature=0.7, max_tokens=150)`).
2. **World and initial agents** are born from an unseeded LLM call at temperature 0.8: `epocha/apps/world/generator.py:101-107`.
3. **The LLM layer exposes no seed**: `grep -rn seed epocha/apps/llm_adapter/` = empty. The project declares it in its own model: `seed = models.BigIntegerField(help_text="Seed for reproducibility (non-LLM part)")` (`simulation/models.py:35`).

Additional: global RNG is unseeded in the live path: `random.random()` decides coup success in `government.py:618`, `random.uniform` scatters positions in `movement.py:245-246`.

## Complete inventory (19 claims)

EN-IT mirroring is one-to-one on all points, verified counterpart by counterpart.

| # | Section | EN lines | IT lines | Claim (synopsis) | Verdict | Load-bearing |
|---|---------|----------|----------|-------------------|---------|-------------|
| 1 | Abstract | 43-45 | 45-47 | "Reproducibility infrastructure rests on era templates, per-phase seeded RNG streams, frozen-at-commit references..." | SCOPED-BUT-AMBIGUOUS | Abstract |
| 2 | S1.2 objective | 143 | 150 | "...while remaining auditable, reproducible, and grounded in primary scientific sources" | SCOPED-BUT-AMBIGUOUS | Declared objective |
| 3 | S1.3 contribution | 160-162 | 167-170 | "A reproducibility infrastructure... so that any reported result can be regenerated from a known state" | SCOPED-BUT-AMBIGUOUS | **Contribution S1.3** |
| 4 | S2.2 | 259 | 277 | "Reproducibility is also fragile, since model versions evolve and sampling stochasticity is rarely fully controllable" | TRUE (anchor) | Prose |
| 5 | S2.2 | 267-270 | 287-290 | "Reproducibility is enforced at the simulation boundary through seeded PRNG..." | SCOPED-BUT-AMBIGUOUS (->FALSE) | Method prose |
| 6 | S3.1 | 404-407 | 435-438 | "...any non-determinism comes from the LLM call and the per-tick seeded RNG streams... never from scheduling" | TRUE (anchor) | **Method S3.1** |
| 7 | S3.1 | 411 | 442 | "per-tick reproducibility is the contract the validation suite of Chapter 7 depends on" | SCOPED-BUT-AMBIGUOUS | Method rationale |
| 8 | S3.4 | 499-501 | 534-536 | "Given the commit hash, the simulation.seed, and the initial state of the database, every tick of a run is deterministic and reproducible across machines" | **FALSE** | **Method S3.4** |
| 9 | S3.4 A-5 | 501-507 | 536-542 | Debt A-5: fallback to 0 if seed and id are None | TRUE but INCOMPLETE | Method S3.4 |
| 10 | S4.6 N-8 | 1795 | 1862 | "random.uniform uses Python's global RNG... Two runs with identical seed produce different arrival-scatter offsets" | TRUE (anchor) | Simplification S4.6 |
| 11 | S4.8 | 1940 | 2007 | "...every iteration order... is pinned... so identically-seeded runs reproduce bit-identical state" | **FALSE** | **Method S4.8** |
| 12 | S7.3 Tab.7.2 | 2119 | 2186 | "...the audited invariants (... seeded determinism) are enforced by the regression suite" | SCOPED-BUT-AMBIGUOUS | Validation table |
| 13 | S7.4 | 2124 | 2191 | Title "Reproducibility commands" + pytest commands | TRUE (scoped to tests) | Method S7.4 |
| 14 | S10 | 2278 | 2248 | "...the seeded RNG of S3.4 makes the run reproducible" | **FALSE** | Discussion |
| 15 | S10 | 2282-2284 | 2248 | "narrative reproducibility across runs -- the same scenario re-run with the same seed produces the same per-agent decision log and the same emergent narrative arc" | **FALSE (most grave)** | **Discussion, research capability** |
| 16 | S12 | 2433-2435 | 2305 | "...a per-phase seeded RNG strategy that makes every run reproducible across machines from the commit hash, the seed, and the initial database state" | **FALSE** | **Conclusions S12** |
| 17 | S12 | 2455-2458 | 2307 | "...seeded RNG streams are partitioned... so that a refactor cannot silently shift the random sequence one subsystem sees, and Appendix B records the exact commands by which any reported result can be regenerated" | SCOPED-BUT-AMBIGUOUS | Conclusions S12 |
| 18 | App. B intro | 3033-3037 | 2888-2892 | "...any result reported in this whitepaper can be regenerated from a clean checkout" | SCOPED-BUT-AMBIGUOUS | Reproducibility appendix |
| 19 | App. B RNG | 3098-3106 | 2953-2963 | "...two runs with the same simulation.id, simulation.seed, and code revision produce identical per-tick draws across the lifetime of the simulation" | TRUE (scoped to "draws") | Appendix, anchor |

## The 5 FALSE claims (certain)

1. **S3.4** (EN:499-501): "every tick of a run is deterministic and reproducible across machines" -- the "given initial database state" premise absorbs world genesis but NOT per-tick LLM decisions at temperature 0.7
2. **S4.8** (EN:1940): "identically-seeded runs reproduce bit-identical state" -- economy consumes DecisionLog (LLM output) and agent wealth/zone (LLM-derived); confuses "deterministic given inputs" with "reproducible from seed"
3. **S10** (EN:2278): "the seeded RNG of S3.4 makes the run reproducible" -- repeats S3.4's false claim
4. **S10** (EN:2282-2284): "the same scenario re-run with the same seed produces the same per-agent decision log" -- the DecisionLog IS the transcription of LLM output at 0.7 without seed; **most grave** because it claims seed-reproducibility of the exact artifact that is pure LLM sampling
5. **S12** (EN:2433-2435): "makes every run reproducible across machines from the commit hash, the seed, and the initial database state" -- conclusions repeating S3.4

## The 7 SCOPED-BUT-AMBIGUOUS claims (to qualify)

1. Abstract (EN:43-45)
2. S1.2 (EN:143)
3. S1.3 (EN:160-162)
4. S3.1 contract (EN:411)
5. S7.3 Tab.7.2 (EN:2119)
6. S12 partitioning (EN:2455-2458)
7. App. B intro (EN:3033-3037)

## The 3 correct anchors (models for rewrite)

1. **S3.1** (EN:404-407): "any non-determinism comes from the LLM call" -- names the LLM call explicitly as source of non-determinism
2. **S4.6 N-8** (EN:1795): surgical declaration of a single global-RNG defect with cause, mechanism, observable consequence, future work
3. **App. B RNG** (EN:3098-3106): claims only "identical per-tick draws" (RNG draws), not state, not decisions

## 4 internal contradictions

1. **S3.1 vs S3.4/S4.8/S10/S12/App.B**: S3.1 admits "any non-determinism comes from the LLM call"; the other five claim full seed reproducibility
2. **S4.6 N-8 vs the same five**: "two runs with identical seed produce different arrival-scatter offsets" is the operational negation of "identically-seeded runs reproduce bit-identical state"
3. **Internal to S2.2**: EN:259 admits "reproducibility is fragile... sampling stochasticity is rarely fully controllable"; 8 lines later EN:267 claims "Reproducibility is enforced..."
4. **S7.5/S7.4 vs App. B**: validation suite "is not yet implemented" (EN:2135) yet S7.4 titles "Reproducibility commands" and App. B promises regeneration of "any reported result"

## Undeclared defect found during verification

`government.py:618` (`random.random()` for coup success) is the same class of defect as S4.6 N-8 (global RNG, not seeded) but is NOT declared anywhere in the whitepaper. Should be added as a sibling simplification note in S4.5 (political institutions).

## Corrective direction (not the rewrite itself)

Bring the qualification of S3.1 and S4.6-N-8 into S3.4, S4.8, S10, S12, and App. B: every time "reproducible from the seed" is stated, add the constraint that this holds for the non-LLM part (seeded demography and economy), while per-agent decisions, world generation, and global-RNG uses in movement/government are NOT seed-reproducible -- exactly what `models.py:35` calls "non-LLM part".

## Counts

- **5 FALSE** claims per language (certain)
- **1 borderline FALSE** (S2.2 "enforced", EN:267)
- **7 SCOPED-BUT-AMBIGUOUS** to qualify per language
- **3 correct anchors** (do not correct; use as model)
- Total edits: **12 loci per language = 24 modifications** (13+13=26 if S2.2 "enforced" included)

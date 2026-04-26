# README and Whitepaper Catch-up Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Phase 5 implementation runs primarily on Sonnet 4.6 per the model selection policy; foundation tasks (W1, F6 audits, IT translation review, README review) run on Opus 4.7. Escalation to Opus is triggered by any strategic decision outside the specified execution (e.g. a citation cannot be verified, a code-spec mismatch surfaces).

**Goal:** Deliver the bilingual scientific whitepaper (`docs/whitepaper/epocha-whitepaper.md` + `.it.md`) covering Demography Plan 1+2 and Economy Behavioral as audited Methods chapters, plus a rewritten developer-focused bilingual README that links to the whitepaper as the authoritative documentation. Close the documentation debt accumulated since February 2026 before resuming Demography Plan 3.

**Architecture:** Single feature branch `feature/readme-and-whitepaper-catchup`. Whitepaper-first then README-distilled. Five sequential implementation blocks: W1 foundation, W2 audited Methods, W3 completion, W4 IT translation, R README EN+IT. Three independent adversarial audits at the heavy gate (bibliography, scientific consistency, EN-IT consistency) with convergence loops. The whitepaper is text-only in this iteration; figures and validation plots are deferred to a separate follow-up.

**Tech Stack:** Markdown only. No code changes. No new runtime dependencies. Cross-references between EN and IT documents use anchor names that match between the two files.

**Spec:** `docs/superpowers/specs/2026-04-26-readme-and-whitepaper-catchup-design.md` (authoritative Italian, approved 2026-04-26).

**Depends on:** `develop` branch at commit `3202800` (CLAUDE.md condensation).

**Follow-up plans (already memorized):**
- `project_audit_repass_batch_2026_04_12_pending.md` — Round 2 re-audit on 8 modules currently in §8 (priority: HIGH, after Demography Plan 3).
- `project_validation_experiments_pending.md` — execution of Validation methodology described in §7 (priority: medium, before paper submission).
- `project_whitepaper_promotion_pipeline.md` — standard procedure to promote a §8 module to §4 once a CONVERGED audit lands.

**IMPORTANT notes for implementers:**
- All artifacts in this plan are documentation. The `pytest` suite is not modified; run it once at fase 6 to confirm no regression (none expected since no code touches).
- Whitepaper EN is the authoritative document. IT is a translation; semantic content must match exactly. Numbering of chapters, equations, and tables is identical between EN and IT.
- Citations in §4 (Methods) are **primary-source strict**: every formula, parameter, and algorithm cites the original paper/book/dataset with author-year-DOI. The internal spec file is NOT a valid citation source for §4. Re-verify each citation against the original source before declaring a §4 task complete.
- Citations in §3 (Architecture descriptive) and §8 (Designed Subsystems) are "literature pointers" — bibliographic references without claimed fidelity verification.
- Validation experiments are NOT executed in this plan. §7 documents methodology only. Status header in §7.5 must explicitly state "validation experiments specified, not yet executed".
- Any time a §4 chapter cannot be written because a formula in the code does not match the cited source, STOP and escalate to Opus: a code fix branch must be opened, audited, merged, then this plan resumes. Do not document false claims.
- Frozen-at-commit hash in the whitepaper frontmatter is filled at fase 7 closure with the actual merge commit hash; until then it is `<filled-on-merge>`.
- All commit messages follow Conventional Commits, no AI attribution, no emoji. Use `docs` type for everything in this plan. Scope is omitted (documentation crosses multiple apps).
- Italian is used ONLY in the spec file (already committed). All other artifacts (plan, whitepaper EN, README EN, commit messages, CLAUDE.md, code) are in English. The bilingual whitepaper has both EN and IT files.

---

## File Structure

| File | Responsibility | New/Modify |
|------|---------------|------------|
| `docs/whitepaper/` | Directory for the whitepaper | New |
| `docs/whitepaper/epocha-whitepaper.md` | Authoritative scientific whitepaper (EN) | New |
| `docs/whitepaper/epocha-whitepaper.it.md` | Italian translation of the whitepaper | New |
| `README.md` | Developer-focused entry point (EN) | Modify (full rewrite) |
| `README.it.md` | Developer-focused entry point (IT) | Modify (full rewrite) |
| `CLAUDE.md` | Add whitepaper-doc-sync rule under Documentation Sync section | Modify |

The plan adds 3 files, modifies 3 files. No code is touched.

---

## Tasks summary

**Block W1 — Whitepaper foundation (7 tasks)**
1. Create `docs/whitepaper/` and the EN whitepaper skeleton (frontmatter, abstract placeholder, status legend, all 14 chapter headers as scaffold)
2. Write §1 Introduction (4 sub-sections)
3. Write §2 Background and Related Work, sub-sections 2.1 and 2.2
4. Write §2 Background and Related Work, sub-sections 2.3, 2.4, 2.5
5. Write §3 System Architecture, sub-sections 3.1, 3.2, 3.3, 3.4
6. Write §3 System Architecture, sub-sections 3.5, 3.6, 3.7, 3.8
7. Write §13 References — initial bibliography seeded from spec §11 (verified)

**Block W2 — Methods per audited module (12 tasks)**
8. Draft §4.1 Demography intro + §4.1.1 Mortality (Heligman-Pollard)
9. Review §4.1.1 — citation cross-check + code-spec consistency
10. Draft §4.1.2 Fertility (Hadwiger + Becker + Malthusian)
11. Review §4.1.2 — citation cross-check + code-spec consistency
12. Draft §4.1.3 Couple formation/dissolution (Gale-Shapley + Goode 1963)
13. Review §4.1.3 — citation cross-check + code-spec consistency
14. Draft §4.2 Economy Behavioral intro + §4.2.1 Adaptive expectations (Cagan)
15. Review §4.2.1 — citation cross-check + code-spec consistency
16. Draft §4.2.2 Credit & banking (Diamond-Dybvig)
17. Review §4.2.2 — citation cross-check + code-spec consistency
18. Draft §4.2.3 Property market
19. Review §4.2.3 — citation cross-check + code-spec consistency

**Block W3 — Whitepaper completion (10 tasks)**
20. Write §5 Implementation (repository layout, module-to-spec mapping, LLM adapter, persistence)
21. Write §6 Calibration (parameter tables consolidated from §4)
22. Write §7 Validation Methodology (datasets, metrics, thresholds, reproducibility commands, status)
23. Write §8 Designed Subsystems (7 paragraphs, one per module/cluster)
24. Write §9 Roadmap
25. Write §10 Discussion
26. Write §11 Known Limitations
27. Write §12 Conclusions
28. Write §14 Appendix A (Full parameter tables with provenance)
29. Write §14 Appendix B (Reproducibility) + Appendix C (Era templates) + finalize frontmatter

**Block W4 — Italian translation (8 tasks)**
30. Create `epocha-whitepaper.it.md` skeleton (frontmatter IT, abstract IT, status legend IT, 14 chapter scaffolds)
31. Translate §1 Introduction + §2 Background
32. Translate §3 System Architecture
33. Translate §4.1 Demography (Methods)
34. Translate §4.2 Economy Behavioral (Methods)
35. Translate §5 Implementation + §6 Calibration + §7 Validation Methodology
36. Translate §8 Designed Subsystems + §9 Roadmap + §10 Discussion + §11 Limitations + §12 Conclusions
37. Mirror §13 References (identical EN/IT) + translate §14 Appendices A/B/C + EN-IT consistency self-check

**Block R — README rewrite (4 tasks)**
38. Rewrite `README.md` (EN) per spec §4.2 skeleton
39. Rewrite `README.it.md` (IT) per spec §4.2 skeleton, link to whitepaper IT
40. Add whitepaper-doc-sync rule paragraph to `CLAUDE.md` under Documentation Sync section
41. Cross-link verification: every link in README EN → file exists; every link in README IT → file exists; every README cross-reference to whitepaper anchor matches an actual heading in the whitepaper

**Block F6 — Heavy gate (3 audit tasks + dynamic remediation)**
42. Dispatch bibliography audit on whitepaper EN; loop until CONVERGED
43. Dispatch scientific consistency audit (whitepaper §4 vs code in develop); loop until CONVERGED
44. Dispatch EN-IT consistency audit; loop until CONVERGED

**Block F7 — Closure (4 tasks)**
45. Run full test suite (`pytest --cov=epocha -v`); confirm green; document the run
46. Update whitepaper frontmatter (EN + IT) with the actual merge commit hash placeholder strategy
47. Sync memory backup `docs/memory-backup/` with the live memory directory
48. Open final draft PR with summary, request human heavy gate validation

Total: 48 tasks across 7 blocks (W1, W2, W3, W4, R, F6, F7).

---

### Task 1: Create whitepaper directory and EN scaffold

**Files:**
- Create: `docs/whitepaper/epocha-whitepaper.md`

**Sources to consult:**
- Spec §3.2 (Indice analitico) — definitive chapter list
- Spec §3.3 (Versioning) — frontmatter format
- Spec §3.1 (Status legend table) — 3-level legend

- [ ] **Step 1: Create `docs/whitepaper/` and the file**

Use the Bash tool to confirm the directory does not exist, then Write the file with this exact content (replace the abstract body with a one-line placeholder; it is filled at end of W3):

```markdown
---
title: "Epocha — A Scientifically Grounded Civilization Simulator"
authors: ["Maurizio Mocci"]
affiliation: "Independent project"
date: "2026-04-26"
version: "0.1"
frozen-at-commit: "<filled-on-merge>"
license: "Apache 2.0"
---

# Epocha — A Scientifically Grounded Civilization Simulator

## Abstract

<placeholder — written at end of W3 once Methods and Validation chapters are in place>

## Keywords

agent-based modeling, computational social science, demographic micro-simulation,
economic agent-based models, large language models, social simulation,
psychohistory, reputation systems

## Document structure and status legend

This document distinguishes three levels of maturity for each subsystem:

- **Audited (CONVERGED)** — chapters in §4 Methods. Adversarial scientific
  audit has reached convergence on the underlying spec or code. Background,
  model, equations, parameters with primary-source citations, algorithm,
  simplifications, and a status header are provided for each module.
- **Implemented, audit pending** — chapters in §8 Designed Subsystems. The
  module exists in the codebase but has not yet completed the convergence
  loop of the project's adversarial audit policy. Each entry is a 5-10
  sentence paragraph linking to the design spec.
- **Specified or planned** — listed in §9 Roadmap as a short bullet.

Status headers in §4 use the form:
> Status: implemented as of commit `<hash>`, spec audit CONVERGED `<date>`.

---

## Table of contents

1. Introduction
2. Background and Related Work
3. System Architecture
4. Methods — Audited Modules
5. Implementation
6. Calibration
7. Validation Methodology
8. Designed Subsystems (implemented, audit pending)
9. Roadmap
10. Discussion
11. Known Limitations
12. Conclusions
13. References
14. Appendices

---

# 1. Introduction

<draft in Task 2>

## 1.1 Context

<draft in Task 2>

## 1.2 Research gap addressed

<draft in Task 2>

## 1.3 Contributions

<draft in Task 2>

## 1.4 Document structure and status legend

<draft in Task 2 — extends the legend in the front matter with cross-references>

---

# 2. Background and Related Work

## 2.1 Agent-based modeling of societies

<draft in Task 3>

## 2.2 LLM-driven simulations and the role of personality

<draft in Task 3>

## 2.3 Demographic micro-simulation

<draft in Task 4>

## 2.4 Economic agent-based models

<draft in Task 4>

## 2.5 Reputation and information diffusion in MAS

<draft in Task 4>

---

# 3. System Architecture

## 3.1 Tick engine and time scales

<draft in Task 5>

## 3.2 Agent decision pipeline (Big Five + memory + LLM)

<draft in Task 5>

## 3.3 Cross-module integration contracts (treasury, subsistence, outlook)

<draft in Task 5>

## 3.4 RNG strategy and reproducibility

<draft in Task 5>

## 3.5 LLM provider adapter and rate limiting

<draft in Task 6>

## 3.6 Economic substrate (production, monetary, market clearing, distribution)

<draft in Task 6 — note: descriptive, NOT Methods-grade>

## 3.7 Persistence model

<draft in Task 6>

## 3.8 Interaction layer (Dashboard, Chat WebSocket)

<draft in Task 6>

---

# 4. Methods — Audited Modules

## 4.1 Demography

> Status: implemented as of commit `<filled-on-merge>`, spec audit CONVERGED 2026-04-18 round 4.

<draft in Tasks 8-13>

### 4.1.1 Mortality model (Heligman-Pollard)

<draft in Task 8>

### 4.1.2 Fertility model (Hadwiger ASFR + Becker modulation + Malthusian ceiling)

<draft in Task 10>

### 4.1.3 Couple formation and dissolution (Gale-Shapley + Goode 1963)

<draft in Task 12>

## 4.2 Economy — Behavioral integration

> Status: implemented as of commit `<filled-on-merge>`, spec audit CONVERGED 2026-04-15.

<draft in Tasks 14-19>

### 4.2.1 Adaptive expectations (Cagan 1956)

<draft in Task 14>

### 4.2.2 Credit and banking (Diamond-Dybvig 1983, fractional reserve)

<draft in Task 16>

### 4.2.3 Property market

<draft in Task 18>

---

# 5. Implementation

<draft in Task 20>

## 5.1 Repository layout

<draft in Task 20>

## 5.2 Module-to-spec mapping

<draft in Task 20>

## 5.3 LLM provider adapter and rate limiting

<draft in Task 20>

## 5.4 Persistence model details

<draft in Task 20>

---

# 6. Calibration

<draft in Task 21>

## 6.1 Parameter tables per audited module

<draft in Task 21>

## 6.2 Era templates and tunable heuristics

<draft in Task 21>

## 6.3 Fitting procedures

<draft in Task 21>

---

# 7. Validation Methodology

> Status: validation experiments specified, not yet executed. Execution is tracked as a separate follow-up (see project memory `project_validation_experiments_pending.md`).

<draft in Task 22>

## 7.1 Target datasets per audited module

<draft in Task 22>

## 7.2 Comparison metrics

<draft in Task 22>

## 7.3 Acceptance thresholds

<draft in Task 22>

## 7.4 Reproducibility commands

<draft in Task 22>

## 7.5 Status

<draft in Task 22>

---

# 8. Designed Subsystems (implemented, audit pending)

<draft in Task 23>

## 8.1 Cluster: Rumor propagation (Information Flow + Distortion + Belief Filter)

<draft in Task 23>

## 8.2 Cluster: Political institutions (Government + Institutions + Stratification)

<draft in Task 23>

## 8.3 Movement

<draft in Task 23>

## 8.4 Factions

<draft in Task 23>

## 8.5 Reputation (Castelfranchi-Conte-Paolucci 1998)

<draft in Task 23>

## 8.6 Knowledge Graph

<draft in Task 23>

## 8.7 Economy base layer

<draft in Task 23>

---

# 9. Roadmap

<draft in Task 24>

---

# 10. Discussion

<draft in Task 25>

---

# 11. Known Limitations

<draft in Task 26>

---

# 12. Conclusions

<draft in Task 27>

---

# 13. References

<draft in Task 7 (initial seed) and updated incrementally through W2 and W3>

---

# 14. Appendices

## Appendix A — Full parameter tables

<draft in Task 28>

## Appendix B — Reproducibility

<draft in Task 29>

## Appendix C — Era templates JSON schema and source

<draft in Task 29>
```

- [ ] **Step 2: Verify the file structure**

Run: `ls docs/whitepaper/ && wc -l docs/whitepaper/epocha-whitepaper.md`
Expected: directory exists, file is approximately 200 lines (scaffold only).

- [ ] **Step 3: Commit**

```bash
git add docs/whitepaper/epocha-whitepaper.md
git commit -m "$(cat <<'EOF'
docs: scaffold bilingual whitepaper EN with status legend

CHANGE: Create docs/whitepaper/ directory and the English whitepaper
skeleton with frontmatter, abstract placeholder, status legend, 14
chapter scaffolds, and per-section placeholders pointing to the task
that fills each one. Frozen-at-commit field is filled at merge in
fase 7. The Italian companion file is created in Task 30.
EOF
)"
```

---

### Task 2: Write §1 Introduction

**Files:**
- Modify: `docs/whitepaper/epocha-whitepaper.md` (replace `# 1. Introduction` placeholder block with full content)

**Sources to consult:**
- Spec §3.2 lines 46-50 (chapter outline)
- `docs/superpowers/specs/2026-03-22-epocha-design.md` (master design — for Vision framing)
- Current `README.md` Overview section (for the Asimov framing already established)
- Spec §10 FAQ for examples of "research gap addressed"

- [ ] **Step 1: Replace the §1 placeholder block**

Replace the entire block from `# 1. Introduction` through `## 1.4 Document structure and status legend` (and its placeholder line) with a fully written introduction containing:

- **§1.1 Context** (2 paragraphs): psychohistory as fictional discipline (Asimov), real research lineage (Schelling 1971; Epstein & Axtell 1996; Bonabeau 2002), the recent emergence of LLM-augmented agent simulations (e.g. Park et al. 2023 generative agents, Argyle et al. 2023 LLMs simulating humans). Frame Epocha as the intersection of these two lines.
- **§1.2 Research gap addressed** (1 paragraph): existing LLM agent simulations focus on small-group emergent behavior over short horizons; existing demographic and economic micro-simulators model long horizons but with rule-based agents lacking personality and rich memory. Epocha targets the gap of long-horizon multi-scale simulation with LLM-driven personality-rich agents grounded in published demographic/economic models.
- **§1.3 Contributions** (bullet list of 4-6 items): bilingual rigorous whitepaper, end-to-end open-source civilization simulator, integration of audited demographic and economic models with LLM decision pipeline, 7-phase canonical workflow with mandatory adversarial scientific audits, Italian and English documentation produced jointly, reproducibility infrastructure (era templates, seeded RNG, frozen-at-commit references).
- **§1.4 Document structure and status legend** (1 paragraph + table): cross-reference to the front matter status legend, brief tour of the chapter sequence (background → architecture → audited methods → implementation → calibration → validation methodology → designed subsystems → roadmap → discussion → references → appendices).

Length target: 1.5-2 pages of rendered Markdown.

- [ ] **Step 2: Cross-check**

For every author-year citation introduced (Schelling 1971; Epstein & Axtell 1996; Bonabeau 2002; Park et al. 2023; Argyle et al. 2023), append a corresponding entry to §13 References at the end of the document with full bibliographic data (DOI/URL when available). Do not leave any citation unmatched.

- [ ] **Step 3: Verify no placeholder remains in §1**

Run: `grep -n "<draft in Task" docs/whitepaper/epocha-whitepaper.md | grep -E "^[0-9]+:.*1\.[0-9]"`
Expected: no output (no §1.x placeholder markers left).

- [ ] **Step 4: Commit**

```bash
git add docs/whitepaper/epocha-whitepaper.md
git commit -m "$(cat <<'EOF'
docs: write whitepaper chapter 1 introduction

CHANGE: Fill chapter 1 of the whitepaper with the four sub-sections
(Context, Research gap, Contributions, Document structure). Adds the
matching bibliography entries to chapter 13 for each cited reference.
EOF
)"
```

---

### Task 3: Write §2.1 and §2.2 (Background — ABM and LLM-driven simulations)

**Files:**
- Modify: `docs/whitepaper/epocha-whitepaper.md` (§2.1 and §2.2 placeholders)

**Sources to consult:**
- Same as Task 2
- `docs/letture-consigliate.md` — recommended reading list
- `reference_paolucci_social_simulation.md` (memory) — CNR group on social simulation
- `reference_mirofish_comparison.md` (memory) — competing system gap analysis

- [ ] **Step 1: Replace §2.1 and §2.2 placeholders**

- **§2.1 Agent-based modeling of societies** (2 paragraphs): historical lineage (Schelling 1971 segregation; Axelrod 1984 cooperation; Epstein & Axtell 1996 Sugarscape; Bonabeau 2002 review). Strengths and limits of rule-based ABM. Mention the rise of large-scale models (NetLogo, Mesa, Repast HPC). Position Epocha as a long-horizon multi-scale ABM with LLM-driven decision module.
- **§2.2 LLM-driven simulations and the role of personality** (2 paragraphs): Park et al. (2023) generative agents in Smallville; Argyle et al. (2023) LLMs as silicon sample; Aher et al. (2023) using LLMs to simulate human subjects. Discussion of personality models in LLM agents (Big Five integration, prompted persona). Limits: hallucination, prompt sensitivity, cost. How Epocha mitigates: rule-based scaffolding around LLM decisions, reputation/memory caches reducing context drift, deterministic seed-RNG for reproducibility.

Length target: 1.5 pages.

- [ ] **Step 2: Cross-check citations and append to §13**

Same as Task 2 step 2. New entries: Schelling 1971, Axelrod 1984, Epstein & Axtell 1996, Bonabeau 2002, Park et al. 2023, Argyle et al. 2023, Aher et al. 2023.

- [ ] **Step 3: Verify**

Run: `grep -n "<draft in Task" docs/whitepaper/epocha-whitepaper.md | grep -E "2\.[12]"`
Expected: no output.

- [ ] **Step 4: Commit**

```bash
git add docs/whitepaper/epocha-whitepaper.md
git commit -m "$(cat <<'EOF'
docs: write whitepaper chapters 2.1 and 2.2 background on ABM and LLM agents

CHANGE: Cover the two background subsections on agent-based modeling of
societies and on LLM-driven simulations with personality, positioning
Epocha at their intersection. Adds the matching bibliography entries.
EOF
)"
```

---

### Task 4: Write §2.3, §2.4, §2.5 (Background — Demographic, Economic, Reputation)

**Files:**
- Modify: `docs/whitepaper/epocha-whitepaper.md` (§2.3, §2.4, §2.5 placeholders)

**Sources to consult:**
- Spec §11 bibliographic seed
- `docs/superpowers/specs/2026-04-18-demography-design.md` Background section
- `docs/superpowers/specs/2026-04-12-economy-base-design.md` Background section
- `docs/superpowers/specs/2026-04-13-economy-behavioral-design.md` Background section
- `docs/superpowers/specs/2026-04-06-reputation-model-design.md` Background section
- `docs/superpowers/specs/2026-04-15-economy-behavioral-integration-design.md`

- [ ] **Step 1: Replace §2.3, §2.4, §2.5 placeholders**

- **§2.3 Demographic micro-simulation** (1.5 paragraphs): lineage (van Imhoff & Post 1998; Spielauer 2011 review; Zinn et al. 2009 MicSim; SOCSIM Berkeley). Distinction macro vs micro vs agent-based demography. Models of mortality (Gompertz 1825; Heligman-Pollard 1980), fertility (Coale-Trussell 1974; Hadwiger 1940), nuptiality (Hajnal 1965). Position Epocha as agent-based with audited HP and Hadwiger.
- **§2.4 Economic agent-based models** (1.5 paragraphs): EURACE (Deissenberg, van der Hoog, Dawid 2008); JAMEL (Seppecher 2012); Mark0 (Gualdi et al. 2015). Macroeconomic ABM strengths (heterogeneity, out-of-equilibrium dynamics) and limits (calibration, identification). Behavioral economics integration (Cagan 1956 expectations; Diamond-Dybvig 1983 banking; Minsky 1986 financial instability). Position Epocha behavioral layer.
- **§2.5 Reputation and information diffusion in MAS** (1 paragraph): Conte & Paolucci 2002 reputation in MAS; Castelfranchi, Conte, Paolucci 1998 normative reputation; Allport & Postman 1947 rumor; Bartlett 1932 serial reproduction. Note: Epocha's reputation module exists in code but is in §8 awaiting Round 2 audit; this paragraph frames the literature, the actual implementation is referenced in §8.5.

Length target: 2 pages.

- [ ] **Step 2: Cross-check citations and append to §13**

Append: van Imhoff & Post 1998, Spielauer 2011, Zinn et al. 2009, Gompertz 1825, Coale-Trussell 1974, Heligman-Pollard 1980 (already seeded), Hadwiger 1940 (already seeded), Hajnal 1965 (already seeded), Deissenberg/van der Hoog/Dawid 2008, Seppecher 2012, Gualdi et al. 2015, Cagan 1956 (already seeded), Diamond-Dybvig 1983 (already seeded), Minsky 1986, Conte & Paolucci 2002, Castelfranchi/Conte/Paolucci 1998 (already seeded), Allport & Postman 1947, Bartlett 1932.

- [ ] **Step 3: Verify**

Run: `grep -n "<draft in Task" docs/whitepaper/epocha-whitepaper.md | grep -E "2\.[345]"`
Expected: no output.

- [ ] **Step 4: Commit**

```bash
git add docs/whitepaper/epocha-whitepaper.md
git commit -m "$(cat <<'EOF'
docs: write whitepaper chapter 2 background subsections 3 to 5

CHANGE: Cover background on demographic micro-simulation, economic
agent-based models, and reputation/information-diffusion literature.
Adds matching bibliography entries.
EOF
)"
```

---

### Task 5: Write §3.1, §3.2, §3.3, §3.4 (System Architecture core)

**Files:**
- Modify: `docs/whitepaper/epocha-whitepaper.md` (§3.1-3.4 placeholders)

**Sources to consult:**
- `epocha/apps/simulation/engine.py` — tick loop and orchestration
- `epocha/apps/simulation/tasks.py` — Celery tasks `run_simulation_loop`, `process_agent_turn`
- `epocha/apps/agents/decision.py` — agent decision pipeline
- `epocha/apps/agents/personality.py` — Big Five
- `epocha/apps/agents/memory.py` — memory model
- `epocha/apps/demography/context.py` — `add_to_treasury`, `compute_subsistence_threshold`, `compute_aggregate_outlook` (cross-module contracts)
- `epocha/apps/demography/rng.py` — `get_seeded_rng`
- Spec `2026-04-18-demography-design.md` §Cross-module contracts

- [ ] **Step 1: Replace §3.1-3.4 placeholders**

- **§3.1 Tick engine and time scales** (1 paragraph + diagram in ASCII): describe `run_simulation_loop` self-enqueuing pattern, tick = 1 month/year/decade depending on simulation config, tick atomicity (snapshot before, processing chord, snapshot after), per-tick agents iterated in deterministic order, why this design over real-time event-driven.
- **§3.2 Agent decision pipeline** (1.5 paragraphs): the four-stage pipeline (memory recall → context build → LLM prompt → action parse) with explicit reference to `agents/decision.py`. Big Five trait injection into system prompt (cite McCrae & Costa 1987). Memory with emotional weight model (cite Brown & Kulik 1977 flashbulb memories). Explicit caveat: this whole pipeline is in §3 (architecture) NOT §4 because the personality and memory implementations have not yet completed Round 2 audit.
- **§3.3 Cross-module integration contracts** (1 paragraph + table): the three contracts `add_to_treasury(zone, amount)`, `compute_subsistence_threshold(zone, n_agents)`, `compute_aggregate_outlook(simulation, tick)`. For each: signature, semantics, who calls it, who implements it. Why explicit contracts over implicit globals: testability + auditability.
- **§3.4 RNG strategy and reproducibility** (1 paragraph): seeded streams via `get_seeded_rng(simulation_id, tick, stream_label)`, why per-stream isolation (one stream per concern: mortality, fertility, couple, decision noise), guarantee of reproducibility given commit hash + simulation seed + initial state. Note known debt A-5 (RNG collision when both seed and id are None) tracked for Plan 4.

Length target: 2-2.5 pages.

- [ ] **Step 2: Verify code references**

For each file path mentioned (`epocha/apps/simulation/engine.py`, `epocha/apps/agents/decision.py`, etc.), Read the actual file and confirm the function/class names quoted in the chapter exist. If a name does not exist (renamed, moved), STOP and escalate to Opus.

- [ ] **Step 3: Cross-check citations and append to §13**

Append: McCrae & Costa 1987, Brown & Kulik 1977.

- [ ] **Step 4: Commit**

```bash
git add docs/whitepaper/epocha-whitepaper.md
git commit -m "$(cat <<'EOF'
docs: write whitepaper chapter 3 architecture core sections

CHANGE: Cover tick engine, agent decision pipeline, cross-module
integration contracts, and seeded RNG strategy. Includes file path
references verified against the codebase and explicit caveat that
the agent pipeline awaits Round 2 audit before promotion to chapter 4.
EOF
)"
```

---

### Task 6: Write §3.5, §3.6, §3.7, §3.8 (System Architecture remainder)

**Files:**
- Modify: `docs/whitepaper/epocha-whitepaper.md` (§3.5-3.8 placeholders)

**Sources to consult:**
- `epocha/apps/llm_adapter/client.py`
- `epocha/apps/llm_adapter/providers/`
- `epocha/apps/llm_adapter/rate_limiter.py`
- `epocha/apps/economy/{production,monetary,market,distribution,initialization}.py`
- `epocha/apps/economy/models.py`
- `config/settings/base.py` — DATABASES, persistence config
- `epocha/apps/dashboard/views.py` and `epocha/apps/chat/consumers.py`

- [ ] **Step 1: Replace §3.5-3.8 placeholders**

- **§3.5 LLM provider adapter and rate limiting** (1 paragraph): provider abstraction over OpenAI-compatible APIs, current providers (LM Studio local, OpenAI, Groq with 4-key rotation per `feedback_groq_failover.md` memory), rate limiter design, retry behavior. Explicit configuration knob `EPOCHA_DEFAULT_LLM_PROVIDER`.
- **§3.6 Economic substrate** (2 paragraphs): the underlying economic engine (production CES, monetary base, market clearing via Walrasian tatonnement, distribution). Implementation pointer to literature (Arrow et al. 1961 CES; Walras 1874 tatonnement) WITHOUT claiming Methods-grade verified fidelity. Explicit note: this substrate has no Round 2 adversarial audit yet, hence its presence in §3 not §4. The audited Behavioral integration on top of this substrate is documented in §4.2.
- **§3.7 Persistence model** (1 paragraph): PostgreSQL relational store, model conventions (UUID primary keys for agents/simulations, integer auto for child entities, signed `birth_tick` per Plan 1), planned PostGIS migration (currently in `project_roadmap_post_mvp.md`).
- **§3.8 Interaction layer (Dashboard, Chat)** (1 paragraph): Django Channels WebSocket for real-time simulation observation (`ws/simulation/<id>/`) and agent conversation (`ws/chat/<agent_id>/`). Dashboard server-rendered Django templates with HTMX-style enrichment, no SPA. Why server-side: audit trail simplicity + low ops complexity.

Length target: 2 pages.

- [ ] **Step 2: Verify code references**

Same procedure as Task 5 Step 2: every path quoted must exist. Specifically check for `epocha/apps/llm_adapter/providers/` (directory) and the rate limiter module name.

- [ ] **Step 3: Cross-check citations and append to §13**

Append: Arrow et al. 1961, Walras 1874.

- [ ] **Step 4: Commit**

```bash
git add docs/whitepaper/epocha-whitepaper.md
git commit -m "$(cat <<'EOF'
docs: write whitepaper chapter 3 architecture remainder sections

CHANGE: Cover LLM provider adapter and rate limiting, economic
substrate (descriptive only with literature pointers), persistence
model, and interaction layer. Includes the explicit caveat that the
economic substrate is not Methods-grade audited and lives in chapter 3
rather than chapter 4.
EOF
)"
```

---

### Task 7: Write §13 References — initial bibliography

**Files:**
- Modify: `docs/whitepaper/epocha-whitepaper.md` (§13 placeholder)

**Sources to consult:**
- All citations introduced in Tasks 2-6 (already appended incrementally)
- Spec §11 bibliographic seed (verify each entry against original)
- For each citation: Google Scholar / DOI lookup to confirm author, year, title, venue

- [ ] **Step 1: Consolidate the references list**

Replace the §13 placeholder with a single Author-Date sorted list. For each entry: `Author Last, Initial. (Year). Title. Venue, volume(issue), pages. DOI: <doi>` (or URL if no DOI). Include all citations introduced in Tasks 2-6 (~25 entries).

- [ ] **Step 2: Verify each entry against primary source**

For each entry, perform a verification step using WebFetch or grep through `docs/letture-consigliate.md` and the spec files. Specifically confirm:
- Author surname spelled correctly
- Year matches the original publication
- Title matches (no fabricated subtitles)
- Venue exists and the paper appeared there
- DOI resolves (if quoted)

If any entry cannot be verified, mark it `[VERIFICATION PENDING]` inline and add it to a list at the bottom of the chapter for the bibliography audit at fase 6 to handle. Do NOT leave a citation in §1-§3 that resolves to a `[VERIFICATION PENDING]` reference; if such a citation cannot be verified, replace it with a different verifiable source or remove the claim.

- [ ] **Step 3: Verify**

Run: `grep -c "DOI\|http" docs/whitepaper/epocha-whitepaper.md`
Expected: at least 20 matches (most entries have DOI or URL).

Run: `grep -n "VERIFICATION PENDING" docs/whitepaper/epocha-whitepaper.md`
Expected: ideally 0; if non-zero, those entries are queued for fase 6 audit.

- [ ] **Step 4: Commit**

```bash
git add docs/whitepaper/epocha-whitepaper.md
git commit -m "$(cat <<'EOF'
docs: seed whitepaper chapter 13 references

CHANGE: Consolidate the bibliography from chapters 1 to 3 into a
single Author-Date sorted references list with DOI or URL where
available. Each entry verified against its primary source; any entry
that could not be verified is flagged for the fase 6 bibliography
audit.
EOF
)"
```

---

### Task 8: Draft §4.1 Demography intro and §4.1.1 Mortality (Heligman-Pollard)

**Files:**
- Modify: `docs/whitepaper/epocha-whitepaper.md` (§4.1 intro + §4.1.1 placeholders)

**Sources to consult:**
- `docs/superpowers/specs/2026-04-18-demography-design.md` §Mortality + §Inheritance + §Section on HP fitting
- `epocha/apps/demography/mortality.py` — the actual implementation
- `epocha/apps/demography/template_loader.py` — era HP parameters
- `epocha/apps/demography/templates/*.json` — 5 era files with HP coefficients
- Heligman, L., Pollard, J.H. (1980). The age pattern of mortality. Journal of the Institute of Actuaries 107(1), 49-80. **VERIFY this paper directly** (the spec cites it; the whitepaper must verify against the paper itself).

- [ ] **Step 1: Verify the Heligman-Pollard paper before writing**

Use WebFetch on the JIA paper or a reputable secondary source (e.g. Pitacco 2004 Survival Models in Actuarial Science) to confirm:
- The Heligman-Pollard formula has 8 parameters: A1, A2, A3 (infant), B1, B2, C (accident hump), D, E, F, G, H (senescent) — note the canonical naming may differ; check.
- The functional form: `q(x)/p(x) = A1^((x+A2)^A3) + B1*exp(-B2*(ln(x/C))^2) + D*exp(-E*x)`. Confirm against original paper.
- The standard age range and units.

If the implementation in `mortality.py` does NOT match the verified canonical form, STOP and escalate to Opus. A code fix is required before this chapter can be written.

- [ ] **Step 2: Write the §4.1 intro and §4.1.1 content**

§4.1 intro (1 paragraph): scope of the Demography module (mortality, fertility, couple), spec source, audit status (Round 4 CONVERGED 2026-04-18), code mapping (`epocha/apps/demography/`), data flow within the tick loop.

§4.1.1 sub-section per the canonical schema:
- **Background** (1 paragraph): why HP, alternatives considered (Gompertz too simple, Lee-Carter wrong scale)
- **Model** (1 paragraph + numbered equation): the full HP formula, definition of variables
- **Equations** (numbered): equation (4.1) with full HP formula
- **Parameters** (table): the 8 parameters with their semantic meaning, valid ranges, calibration source. For each era template (5 of them): the parameter values used. Cite era data sources.
- **Algorithm** (1 paragraph): per-agent per-tick mortality probability draw using `get_seeded_rng(sim_id, tick, "mortality")`, implementation in `mortality.py:resolve_tick_deaths()` (verify the function name).
- **Simplifications** (1 paragraph): no cohort effects, no cause-of-death decomposition (death_cause is set heuristically), no extrapolation beyond age 110.
- **Status header** (1 line at top of §4.1.1): `> Status: implemented as of commit <filled-on-merge>, spec audit CONVERGED 2026-04-18 round 4.`

Length target: 2.5 pages.

- [ ] **Step 3: Append citation entries to §13**

Heligman & Pollard 1980 is already seeded. Verify spelling and DOI. Add Pitacco 2004 if used as secondary verification source.

- [ ] **Step 4: Verify**

Run: `grep -n "<draft in Task" docs/whitepaper/epocha-whitepaper.md | grep "4\.1"`
Expected: lines for §4.1.2 and §4.1.3 only (not §4.1 intro or §4.1.1).

- [ ] **Step 5: Commit**

```bash
git add docs/whitepaper/epocha-whitepaper.md
git commit -m "$(cat <<'EOF'
docs: write whitepaper chapter 4.1 demography intro and 4.1.1 mortality

CHANGE: Draft chapter 4.1 introduction and the mortality subsection
covering Heligman-Pollard with the full canonical formula, the eight
parameters, the per-era calibration table, the per-tick algorithm,
documented simplifications, and the audit status header.
EOF
)"
```

---

### Task 9: Review §4.1.1 Mortality

**Files:**
- Read-only review of: `docs/whitepaper/epocha-whitepaper.md` §4.1.1
- Read-only consultation of: `epocha/apps/demography/mortality.py`, `epocha/apps/demography/templates/*.json`

**Sources to consult:**
- Same as Task 8

- [ ] **Step 1: Citation cross-check**

For every author-year citation in §4.1 intro and §4.1.1:
- Locate it in §13 References
- Verify the §13 entry has author, year, title, venue, DOI/URL
- Verify the verification was done in Task 7 or Task 8 (no new `VERIFICATION PENDING` introduced)

Print a list `Citation X → §13 entry confirmed` for each. If any miss, fix immediately.

- [ ] **Step 2: Code-spec consistency check**

For each formula, parameter, and algorithm in §4.1.1:
- Open `epocha/apps/demography/mortality.py`
- Confirm the parameter name and semantics match (e.g. if §4.1.1 says "parameter B2 controls childhood accident peak position", the code must use a parameter with that meaning under that name).
- Confirm the algorithm step (e.g. "draw uniform [0,1) and compare to mortality probability") matches the code.

For each era template under `epocha/apps/demography/templates/`:
- Open the JSON file
- Confirm the HP parameter values listed in the §4.1.1 table match exactly.

If any mismatch is found:
- If the code is wrong relative to the cited source, STOP and escalate to Opus (open a code fix branch).
- If the chapter is wrong relative to the code, fix the chapter.

- [ ] **Step 3: 8-point Mandatory Code Review (adapted for documentation)**

Verify against the project's mandatory review checklist, adapted:
1. Style: chapter follows the Author-Date scientific paper convention.
2. DRY: no parameter table duplicated between §4.1.1 and §6.1; either move the full table to §6.1 and keep a summary in §4.1.1, or keep both with explicit cross-reference.
3. (n/a) — exception handling
4. Codebase consistency: parameter names match the code.
5. (n/a) — query performance
6. Security: no sensitive data leaked (none expected).
7. Documentation language: English, scientific tone.
8. Documentation sync: this IS the documentation update; no other docs need changing for §4.1.1 alone.

- [ ] **Step 4: Verify**

Run: `grep -c "Heligman" docs/whitepaper/epocha-whitepaper.md`
Expected: at least 3 (intro, §4.1.1 body, §13).

- [ ] **Step 5: Commit (only if fixes were applied)**

If §4.1.1 was modified in Step 2 or Step 3:
```bash
git add docs/whitepaper/epocha-whitepaper.md
git commit -m "$(cat <<'EOF'
docs: tighten whitepaper chapter 4.1.1 after code-spec review

CHANGE: Apply review fixes to chapter 4.1.1 mortality. Parameter table
and algorithm description aligned with the implementation in
demography/mortality.py and the era template JSON files.
EOF
)"
```

If no changes were made: log "Task 9 review passed, no commit" and proceed to Task 10.

---

### Task 10: Draft §4.1.2 Fertility (Hadwiger + Becker + Malthusian)

**Files:**
- Modify: `docs/whitepaper/epocha-whitepaper.md` (§4.1.2 placeholder)

**Sources to consult:**
- `docs/superpowers/specs/2026-04-18-demography-design.md` §Fertility
- `epocha/apps/demography/fertility.py` (start with the docstring at top of file — it cites the canonical normalization per Chandola, Coleman & Hiorns 1999 and Schmertmann 2003)
- Hadwiger, H. (1940). Eine analytische Reproduktionsfunktion für biologische Gesamtheiten. Skandinavisk Aktuarietidskrift 23, 101-113. **VERIFY directly** (note: the original is in German; English-language secondary sources include Chandola/Coleman/Hiorns 1999 and Schmertmann 2003).
- Becker, G.S. (1991). A Treatise on the Family. Harvard University Press. (Note: the spec cites Becker 1960 in some places and 1991 in others — pick the one used by `fertility.py` docstring and verify.)
- Ashraf, Q., Galor, O. (2011). Dynamics and stagnation in the Malthusian epoch. AER 101(5), 2003-2041.
- Critical: spec round 1 audit caught a Hadwiger T parameter off-by-factor-10 bug (commit `07ab8d4`). Verify the spec snippet vs the actual code values for T (correct range is [3.5, 4.2]).

- [ ] **Step 1: Verify Hadwiger and Becker before writing**

Use WebFetch on Schmertmann (2003) Demographic Research 9 or a reputable secondary source to confirm the canonical Hadwiger normalization:

`f(a) = (H * T / (R * sqrt(pi))) * (R / a) ** 1.5 * exp(-T ** 2 * (R / a + a / R - 2))`

Confirm:
- H is the target TFR (integral of f over fertile ages)
- R is related to peak fertility age
- T controls spread
- The integral over [12, 50] equals approximately H (the canonical normalization property)

For Becker (1991 or 1960 per code): verify the framework of opportunity cost of children scaled by income/education. Becker does NOT prescribe specific numerical modulation coefficients; the Epocha-specific coefficients should be marked as "tunable, inspired by Becker framework" not "derived from Becker".

For Ashraf-Galor (2011): verify the Malthusian preventive check formalization is consistent with their model.

If any of these checks fail, STOP and escalate.

- [ ] **Step 2: Write §4.1.2 per the canonical schema**

- **Background**: why Hadwiger over Coale-Trussell, why Becker modulation layer, why Malthusian soft ceiling.
- **Model**: three-layer composition (Hadwiger ASFR base × Becker modulation × Malthusian soft cap).
- **Equations** (4.2) Hadwiger ASFR, (4.3) Becker modulation function, (4.4) Malthusian ceiling, (4.5) combined `tick_birth_probability`. Reference the actual function signature in `fertility.py`.
- **Parameters** (table): H, R, T per era template; Becker coefficients per template (note B2-07 debt: identical across templates pending Plan 4 calibration); Malthusian floor (0.1 per spec).
- **Algorithm**: `tick_birth_probability(agent, env)` → uniform draw → joint mortality-fertility resolution per spec §1 C-1 fix (childbirth mortality combined with HP draw).
- **Simplifications**: deterministic ASFR (no stochastic family planning beyond avoid-conception action), no twin/multiple-birth modeling, no infertility heterogeneity beyond `AgentFertilityState` flags, Becker coefficients homogeneous (B2-07).
- **Status header** at top: `> Status: implemented as of commit <filled-on-merge>, spec audit CONVERGED 2026-04-18 round 4.`

Length target: 3 pages.

- [ ] **Step 3: Append citation entries to §13**

Hadwiger 1940, Becker 1991, Ashraf-Galor 2011, Chandola/Coleman/Hiorns 1999, Schmertmann 2003. Verify spellings and DOI.

- [ ] **Step 4: Verify**

Run: `grep -n "<draft in Task" docs/whitepaper/epocha-whitepaper.md | grep "4\.1\.2"`
Expected: no output.

- [ ] **Step 5: Commit**

```bash
git add docs/whitepaper/epocha-whitepaper.md
git commit -m "$(cat <<'EOF'
docs: write whitepaper chapter 4.1.2 fertility model

CHANGE: Draft the fertility subsection covering Hadwiger ASFR with the
canonical Schmertmann normalization, the Becker modulation layer
labeled as tunable framework-inspired coefficients, and the Malthusian
soft ceiling. Includes the joint mortality-fertility resolution noted
in the spec, the per-era parameter table, and explicit acknowledgement
of debt B2-07 on identical Becker coefficients across templates.
EOF
)"
```

---

### Task 11: Review §4.1.2 Fertility

**Files:** read-only review

Same procedure as Task 9 applied to §4.1.2:
- [ ] **Step 1: Citation cross-check** — every author-year matches §13.
- [ ] **Step 2: Code-spec consistency check** — open `fertility.py` and the era templates, confirm equations, parameter names, parameter values match.
- [ ] **Step 3: 8-point review adapted** as in Task 9.
- [ ] **Step 4: Verify** — `grep -c "Hadwiger" docs/whitepaper/epocha-whitepaper.md` ≥ 3.
- [ ] **Step 5: Commit only if fixes applied** with message `docs: tighten whitepaper chapter 4.1.2 after code-spec review`.

---

### Task 12: Draft §4.1.3 Couple formation and dissolution (Gale-Shapley + Goode 1963)

**Files:**
- Modify: `docs/whitepaper/epocha-whitepaper.md` (§4.1.3 placeholder)

**Sources to consult:**
- `docs/superpowers/specs/2026-04-18-demography-design.md` §Couple
- `epocha/apps/demography/couple.py` — the actual implementation
- Gale, D., Shapley, L.S. (1962). College admissions and the stability of marriage. American Mathematical Monthly 69(1), 9-15.
- Goode, W.J. (1963). World Revolution and Family Patterns. Free Press.

- [ ] **Step 1: Verify Gale-Shapley and Goode before writing**

For Gale-Shapley: confirm the deferred acceptance algorithm, stability property, complexity O(n²), and the asymmetry property (proposing side gets best feasible match).

For Goode 1963: confirm the framework on family structures across societies; Goode does not prescribe a specific parameter for "arranged marriage probability" — the Epocha implementation uses an era flag, which should be documented as tunable consistent with Goode's typology, not derived numerically from Goode.

- [ ] **Step 2: Write §4.1.3 per canonical schema**

- **Background**: why stable matching for couple formation initialization, why runtime intent + tick+1 resolution mirroring the property market pattern, two-pass resolution covering both direct LLM intent and arranged marriage.
- **Model**: dual mode (initialization-time stable matching + runtime intent-driven). Homogamy scoring function. Arranged marriage flag per era. Canonical ordering invariant (`agent_a.id < agent_b.id`).
- **Equations** (4.6) homogamy score, (4.7) Gale-Shapley deferred acceptance pseudocode, (4.8) two-pass resolution algorithm.
- **Parameters** (table): per-era arranged marriage flag, homogamy weights for Big Five components.
- **Algorithm**: `stable_matching` library function + `form_couple` enforcing canonical ordering + `resolve_pair_bond_intents` two-pass + `resolve_separate_intents` + `dissolve_on_death` signal handler.
- **Simplifications**: monogamous only, two genders only (per current schema), no remarriage cooldown, Gale-Shapley applied at initialization only (runtime is purely intent-driven).
- **Status header**: `> Status: implemented as of commit <filled-on-merge>, spec audit CONVERGED 2026-04-18 round 4.`

Length target: 2.5 pages.

- [ ] **Step 3: Append citation entries to §13**

Gale-Shapley 1962 already seeded. Goode 1963 already seeded. Verify.

- [ ] **Step 4: Verify**

Run: `grep -n "<draft in Task" docs/whitepaper/epocha-whitepaper.md | grep "4\.1\.3"`
Expected: no output.

- [ ] **Step 5: Commit**

```bash
git add docs/whitepaper/epocha-whitepaper.md
git commit -m "$(cat <<'EOF'
docs: write whitepaper chapter 4.1.3 couple formation and dissolution

CHANGE: Draft the couple subsection covering Gale-Shapley stable
matching for initialization, the runtime intent plus tick+1 resolution
pattern with arranged-marriage two-pass support, the canonical
ordering invariant, and on-death dissolution. Documented limits
include monogamy and binary-gender schema.
EOF
)"
```

---

### Task 13: Review §4.1.3 Couple

Same procedure as Task 9 applied to §4.1.3.
- [ ] **Step 1: Citation cross-check.**
- [ ] **Step 2: Code-spec consistency check** — open `couple.py`, confirm function names, two-pass algorithm structure, canonical ordering enforcement, dissolve_on_death signal.
- [ ] **Step 3: 8-point review adapted.**
- [ ] **Step 4: Verify** — `grep -c "Gale-Shapley\|Goode" docs/whitepaper/epocha-whitepaper.md` ≥ 4.
- [ ] **Step 5: Commit only if fixes applied** with message `docs: tighten whitepaper chapter 4.1.3 after code-spec review`.

---

### Task 14: Draft §4.2 Economy Behavioral intro and §4.2.1 Adaptive expectations (Cagan)

**Files:**
- Modify: `docs/whitepaper/epocha-whitepaper.md` (§4.2 intro + §4.2.1 placeholder)

**Sources to consult:**
- `docs/superpowers/specs/2026-04-15-economy-behavioral-integration-design.md` (CONVERGED 2026-04-15)
- `docs/superpowers/specs/2026-04-13-economy-behavioral-design.md` (Spec 2 base for behavioral)
- `epocha/apps/economy/expectations.py` — implementation
- Cagan, P. (1956). The monetary dynamics of hyperinflation. In M. Friedman (ed.) Studies in the Quantity Theory of Money. University of Chicago Press, 25-117.

- [ ] **Step 1: Verify Cagan adaptive expectations before writing**

Confirm: `E_{t+1}[π] = E_t[π] + λ * (π_t − E_t[π])` with λ ∈ (0, 1] (adaptive expectations form). Verify that Epocha's implementation matches this functional form. Confirm the value of λ used per era template against the Cagan paper or contemporary calibrations (Cagan original calibrations were on hyperinflation episodes).

- [ ] **Step 2: Write §4.2 intro and §4.2.1**

§4.2 intro (1 paragraph): scope of Behavioral integration (expectations, credit, property), spec source, audit status (CONVERGED 2026-04-15), code mapping (`epocha/apps/economy/{expectations,credit,banking,property_market}.py`), distinction from Economy base which is in §3.6.

§4.2.1 per canonical schema:
- **Background**: why adaptive expectations over rational expectations for an LLM-agent simulation (LLMs do not satisfy RE assumptions; Cagan's adaptive form maps naturally to an agent updating from observed data each tick).
- **Model + Equations** (4.9) Cagan adaptive expectations.
- **Parameters** (table): λ per era; trend threshold (5% per spec, documented as design choice not derived).
- **Algorithm**: per-tick update of agent expectation state.
- **Simplifications**: single-variable adaptive (price level only); homogeneous λ across agents within an era; no learning of λ.
- **Status header**: `> Status: implemented as of commit <filled-on-merge>, spec audit CONVERGED 2026-04-15.`

Length target: 1.5 pages.

- [ ] **Step 3: Append citation entries to §13**

Cagan 1956 already seeded.

- [ ] **Step 4: Verify**

Run: `grep -n "<draft in Task" docs/whitepaper/epocha-whitepaper.md | grep "4\.2\.1"`
Expected: no output.

- [ ] **Step 5: Commit**

```bash
git add docs/whitepaper/epocha-whitepaper.md
git commit -m "$(cat <<'EOF'
docs: write whitepaper chapter 4.2 intro and 4.2.1 adaptive expectations

CHANGE: Draft chapter 4.2 introduction and the adaptive expectations
subsection covering Cagan with the canonical update rule, the per-era
lambda parameter, the simplification to a single-variable model with
homogeneous lambda, and the audit status header.
EOF
)"
```

---

### Task 15: Review §4.2.1 Adaptive expectations

Same procedure as Task 9 applied to §4.2.1.
- [ ] Steps 1-5 identical pattern. Code path: `epocha/apps/economy/expectations.py`.

---

### Task 16: Draft §4.2.2 Credit and banking (Diamond-Dybvig)

**Files:**
- Modify: `docs/whitepaper/epocha-whitepaper.md` (§4.2.2 placeholder)

**Sources to consult:**
- `docs/superpowers/specs/2026-04-15-economy-behavioral-integration-design.md` §Credit
- `epocha/apps/economy/credit.py`, `banking.py`
- Diamond, D.W., Dybvig, P.H. (1983). Bank runs, deposit insurance, and liquidity. Journal of Political Economy 91(3), 401-419.

- [ ] **Step 1: Verify Diamond-Dybvig before writing**

Confirm: the model uses two-period preferences, fractional reserve banking, withdrawal sequencing, and deposit insurance as a coordination device. Confirm Epocha implementation uses the bank-run condition `confidence < 0.5` alone (per spec audit fix C-3) and not the original "confidence + insolvency" mistake.

- [ ] **Step 2: Write §4.2.2**

- **Background**: why D-D for the credit/banking layer of an agent simulation, what is omitted vs the full D-D model.
- **Model + Equations** (4.10) bank-run condition, (4.11) loan issuance condition, (4.12) collateral pledge logic.
- **Parameters** (table): risk_premium (0.5 per spec, documented as design choice), confidence threshold (0.5).
- **Algorithm**: credit market step (auto-default for dead agents per spec audit fix M-3, exclude pledged properties from collateral per M-6, no double-pledging).
- **Simplifications**: single bank entity per simulation; no inter-bank lending; deposit insurance abstract; multi-round negotiation deferred (single-round take-it-or-leave-it).
- **Status header**.

Length target: 2 pages.

- [ ] **Step 3: Append citation entries**

Diamond-Dybvig 1983 already seeded.

- [ ] **Step 4: Verify** as previous tasks.
- [ ] **Step 5: Commit** with message `docs: write whitepaper chapter 4.2.2 credit and banking`.

---

### Task 17: Review §4.2.2

Same procedure as Task 9.

---

### Task 18: Draft §4.2.3 Property market

**Files:**
- Modify: `docs/whitepaper/epocha-whitepaper.md` (§4.2.3 placeholder)

**Sources to consult:**
- `docs/superpowers/specs/2026-04-15-economy-behavioral-integration-design.md` §Property
- `epocha/apps/economy/property_market.py`
- Shiller (2000) Irrational Exuberance — note spec audit fix I-4 reattributing a previous Gordon claim to Shiller.

- [ ] **Step 1: Verify Shiller and the property-market mechanics**

Confirm Shiller (2000) "bubble territory" claim and that Epocha's property market does not over-claim the bubble dynamics (it is a single-tick clearing market, not a multi-period forward-looking model).

- [ ] **Step 2: Write §4.2.3**

- **Background**: zone-based listings, intent-driven via LLM `buy_property` action.
- **Model + Equations** (4.13) listing-clearing condition, (4.14) collateral conversion on mortgage default.
- **Parameters** (table): trend_threshold (5% per spec C-5), zone-matching rule (current zone at matching time per M-4).
- **Algorithm**: buyer/seller matching with self-purchase exclusion (M-5), zone consistency check (M-4), explicit borrowing requirement (A-5 design choice removing auto-loan).
- **Simplifications**: single-round clearing, no multi-round negotiation, listings reset per tick.
- **Status header**.

Length target: 1.5 pages.

- [ ] **Step 3: Append citations**

Shiller 2000 verify and append.

- [ ] **Step 4: Verify** as previous.
- [ ] **Step 5: Commit** with message `docs: write whitepaper chapter 4.2.3 property market`.

---

### Task 19: Review §4.2.3

Same procedure as Task 9.

---

### Task 20: Write §5 Implementation

**Files:**
- Modify: `docs/whitepaper/epocha-whitepaper.md` (§5 placeholders 5.1-5.4)

**Sources to consult:**
- All app paths under `epocha/apps/`
- All spec files under `docs/superpowers/specs/`
- `config/settings/base.py` for stack details

- [ ] **Step 1: Write §5 content**

- **§5.1 Repository layout**: a tree-style listing of `config/`, `epocha/apps/<each>`, `epocha/common/`, `docs/`. One line per directory describing its responsibility.
- **§5.2 Module-to-spec mapping** (table): each app under `epocha/apps/` mapped to its design spec under `docs/superpowers/specs/`. For modules with no spec (e.g. `users`), mark "n/a — boilerplate".
- **§5.3 LLM provider adapter and rate limiting**: cross-reference to §3.5; add LM Studio setup note (link to `epocha/apps/llm_adapter/providers/`), Groq 4-key rotation per memory.
- **§5.4 Persistence model details**: PostgreSQL config, migration discipline, JSONField usage for cash/treasury per Plan 1, signed birth_tick conventions.

Length target: 1.5 pages.

- [ ] **Step 2: Verify** all paths exist (`ls` each).
- [ ] **Step 3: Commit** with message `docs: write whitepaper chapter 5 implementation`.

---

### Task 21: Write §6 Calibration

**Files:**
- Modify: `docs/whitepaper/epocha-whitepaper.md` (§6 placeholders)

**Sources to consult:**
- §4.1 and §4.2 parameter tables (already in document)
- `epocha/apps/demography/templates/*.json` (5 era files)
- `epocha/apps/demography/template_loader.py`
- spec §Calibration where present

- [ ] **Step 1: Write §6 content**

- **§6.1 Parameter tables per audited module**: consolidated tables for each §4.x module. If duplication arises with §4 inline tables, replace inline tables with summary + cross-reference to §6.1 (DRY).
- **§6.2 Era templates and tunable heuristics**: explanation of the era template design (5 templates: pre-industrial, early-modern, industrial, late-industrial, modern), JSON schema, file paths, who reads them.
- **§6.3 Fitting procedures**: scipy.curve_fit usage for Heligman-Pollard, the `template_loader.py` API. Note the B-5 debt for HP fit bounds justification deferred to Plan 4.

Length target: 2 pages.

- [ ] **Step 2: Verify** and **Step 3: Commit** with message `docs: write whitepaper chapter 6 calibration`.

---

### Task 22: Write §7 Validation Methodology

**Files:**
- Modify: `docs/whitepaper/epocha-whitepaper.md` (§7 placeholders)

**Sources to consult:**
- `project_validation_experiments_pending.md` (memory) — the candidate datasets and acceptance thresholds are listed there
- Spec §3.5 for the methodology-only scope decision

- [ ] **Step 1: Write §7 content**

- **§7.1 Target datasets** (table): for each audited module, the dataset (HMD UK 1851-1900 for HP fit, Wrigley-Schofield 1981 for ASFR/TFR, Mokyr 1985 for Irish Famine analog, Hajnal 1965 for couple formation; for Economy Behavioral the dataset is intentionally left as "to be defined in Plan 4 calibration" since spec §3.5 deferred validation execution). Each row: dataset name, citation, DOI/URL, scope.
- **§7.2 Comparison metrics**: RMSE on rates, KS test on distributions, log-likelihood for fit quality.
- **§7.3 Acceptance thresholds**: the explicit thresholds from the memory.
- **§7.4 Reproducibility commands**: the exact pytest invocations and any Python script paths planned (or to be planned in Plan 4).
- **§7.5 Status**: clear statement "Validation experiments specified, not yet executed. Execution tracked as separate follow-up `project_validation_experiments_pending.md`."

Length target: 2 pages.

- [ ] **Step 2: Verify** and **Step 3: Commit** with message `docs: write whitepaper chapter 7 validation methodology`.

---

### Task 23: Write §8 Designed Subsystems

**Files:**
- Modify: `docs/whitepaper/epocha-whitepaper.md` (§8.1-8.7 placeholders)

**Sources to consult:**
- For each subsystem: its spec under `docs/superpowers/specs/`
- `docs/scientific-audit-2026-04-12.md` for context on the audit pending status
- `project_audit_repass_batch_2026_04_12_pending.md` (memory)

- [ ] **Step 1: Write each §8.x sub-section**

For each of the 7 sub-sections (8.1 Rumor cluster, 8.2 Political cluster, 8.3 Movement, 8.4 Factions, 8.5 Reputation, 8.6 Knowledge Graph, 8.7 Economy base):
- 5-10 sentences describing scope, intent, key models cited (literature pointers, NOT primary-source verified), code path
- Status line: `> Status: implemented in code, scientific audit pending. See <spec path>.`
- Link to the spec file under `docs/superpowers/specs/`

Length target: 3-4 pages total (40-70 sentences).

- [ ] **Step 2: Verify** every spec path resolves (`ls` each path).
- [ ] **Step 3: Commit** with message `docs: write whitepaper chapter 8 designed subsystems`.

---

### Task 24: Write §9 Roadmap

**Files:**
- Modify: `docs/whitepaper/epocha-whitepaper.md` (§9 placeholder)

**Sources to consult:**
- `project_roadmap_post_mvp.md`, `project_roadmap_immediate.md`, `project_audit_repass_batch_2026_04_12_pending.md`, `project_validation_experiments_pending.md` (memories)

- [ ] **Step 1: Write §9 content**

A bullet list of planned work, each with one-line description and rough priority. Top of list: "Re-audit pass on 2026-04-12 batch (8 modules) — HIGH PRIORITY, after Demography Plan 3". Then: Demography Plan 3 (Inheritance + Migration), Plan 4 (Init + Engine + Validation execution), Economy financial markets (Spec 3 to write), Validation experiments execution, Analytics psicostoriografia, PostGIS migration, Multi-level agents, Narrative generator, Media layer.

Length target: 1 page.

- [ ] **Step 2: Verify** and **Step 3: Commit** with message `docs: write whitepaper chapter 9 roadmap`.

---

### Task 25: Write §10 Discussion

**Files:**
- Modify: `docs/whitepaper/epocha-whitepaper.md` (§10 placeholder)

- [ ] **Step 1: Write §10 content**

3-4 paragraphs discussing: trade-offs accepted (LLM cost vs realism, simplifications in Methods, deferred validations), scientific limits (audit-pending modules, calibration heuristics), comparison with alternative approaches (pure rule-based vs pure LLM vs hybrid), open research questions Epocha enables (long-horizon emergence, intervention experiments).

Length target: 1.5-2 pages.

- [ ] **Step 2: Verify** and **Step 3: Commit** with message `docs: write whitepaper chapter 10 discussion`.

---

### Task 26: Write §11 Known Limitations

**Files:**
- Modify: `docs/whitepaper/epocha-whitepaper.md` (§11 placeholder)

**Sources to consult:**
- All `Known Limitations` sections of audited specs (`2026-04-18-demography-design.md`, `2026-04-15-economy-behavioral-integration-design.md`)
- Per-module simplifications already written in §4

- [ ] **Step 1: Write §11 content**

Consolidated bullet list grouping known limits by module. Each item: 1-2 sentences. No new limitations introduced — only consolidation.

Length target: 1 page.

- [ ] **Step 2: Verify** and **Step 3: Commit** with message `docs: write whitepaper chapter 11 known limitations`.

---

### Task 27: Write §12 Conclusions

**Files:**
- Modify: `docs/whitepaper/epocha-whitepaper.md` (§12 placeholder)

- [ ] **Step 1: Write §12 content**

2-3 paragraphs: summary of what Epocha provides today (audited Demography + audited Economy Behavioral on top of LLM-driven agent pipeline), what differentiates it from alternatives, the rigorous documentation discipline (7-phase workflow + adversarial audits), invitation for collaboration (open source, bilingual docs).

Length target: 1 page.

- [ ] **Step 2: Verify** and **Step 3: Commit** with message `docs: write whitepaper chapter 12 conclusions`.

---

### Task 28: Write §14 Appendix A — Full parameter tables

**Files:**
- Modify: `docs/whitepaper/epocha-whitepaper.md` (Appendix A placeholder)

- [ ] **Step 1: Write Appendix A**

Complete parameter table for every parameter used in the audited Methods chapters (§4.1, §4.2). Each row: parameter name, semantic meaning, valid range, value per era template, source/citation, status (verified/tunable/heuristic).

Length target: 2-3 pages depending on table size.

- [ ] **Step 2: Verify** and **Step 3: Commit** with message `docs: write whitepaper appendix A parameter tables`.

---

### Task 29: Write Appendix B (Reproducibility) and Appendix C (Era templates) and finalize abstract + frontmatter

**Files:**
- Modify: `docs/whitepaper/epocha-whitepaper.md` (Appendix B + C + abstract placeholder)

**Sources to consult:**
- `requirements/base.txt`, `requirements/local.txt`
- `epocha/apps/demography/templates/*.json` (5 era files)
- `Dockerfile`, `docker-compose.local.yml`

- [ ] **Step 1: Write Appendix B (Reproducibility)**

A list of reproducibility steps:
- Repository: `https://github.com/mauriziomocci/epocha`
- Commit hash: `<filled-on-merge>` (placeholder for now; fase 7 fills it)
- Python version, key dependencies pinned (point to `requirements/base.txt`)
- Docker setup: `docker compose -f docker-compose.local.yml up --build`
- Test invocation: `pytest --cov=epocha -v`
- Seeded RNG note: `get_seeded_rng(simulation_id, tick, stream_label)` ensures determinism
- Era template loading: paths and validation procedure
- Validation experiments: refer to §7 and the follow-up `project_validation_experiments_pending.md`

- [ ] **Step 2: Write Appendix C (Era templates)**

Inline JSON schema description (1 paragraph). Then for each of the 5 era files: name, file path, brief description (era covered, calibration intent), key parameter values (HP, Hadwiger, Becker, Malthusian floor). Avoid pasting full JSON if it would inflate the document; instead paste the file path and a summary table.

- [ ] **Step 3: Finalize the Abstract**

Replace the abstract placeholder with a 200-300 word abstract synthesizing: motivation (psychohistory + LLM agent simulation gap), approach (long-horizon multi-scale ABM with audited demographic and economic models + LLM decision pipeline), what is delivered (Demography Plan 1+2 audited, Economy Behavioral audited, dashboard + chat infrastructure, bilingual whitepaper), what is in progress (audit re-pass on remaining modules, validation experiments execution), reproducibility infrastructure.

- [ ] **Step 4: Verify** all placeholders resolved

Run: `grep -n "<placeholder\|<draft in Task" docs/whitepaper/epocha-whitepaper.md`
Expected: only `<filled-on-merge>` strings remain (those are intentional, filled in fase 7).

- [ ] **Step 5: Commit** with message:

```bash
git commit -m "$(cat <<'EOF'
docs: complete whitepaper appendices and finalize abstract

CHANGE: Write Appendix B (reproducibility steps with commit hash
placeholder, Docker and pytest commands, seeded RNG note) and
Appendix C (era templates: schema, file paths, summary table).
Finalize the abstract synthesizing motivation, approach, delivered
and in-progress modules, and reproducibility infrastructure. The
English whitepaper now has no <draft in Task> placeholders.
EOF
)"
```

---

### Task 30: Create IT whitepaper skeleton

**Files:**
- Create: `docs/whitepaper/epocha-whitepaper.it.md`

**Sources to consult:**
- `docs/whitepaper/epocha-whitepaper.md` (the EN file just completed)

- [ ] **Step 1: Create the IT scaffold**

Mirror the EN file structure exactly: same frontmatter (translated), same chapter numbering, same status legend (translated), same equation numbering. Each chapter and sub-chapter has an `<da tradurre nel Task X>` placeholder corresponding to the EN draft tasks (use the same task numbers).

- [ ] **Step 2: Verify** the file structure mirrors EN.

Run: `diff <(grep -E "^#" docs/whitepaper/epocha-whitepaper.md) <(grep -E "^#" docs/whitepaper/epocha-whitepaper.it.md) | head`
Expected: only differences are translated heading text; structure identical.

- [ ] **Step 3: Commit** with message `docs: scaffold whitepaper italian companion`.

---

### Task 31: Translate §1 + §2

**Files:** modify `docs/whitepaper/epocha-whitepaper.it.md`

- [ ] **Step 1: Translate §1 and §2 from EN**

Translate semantic content faithfully. Italian scientific style (e.g. "agent-based modeling" → "modellazione ad agenti", "psychohistory" → "psicostoriografia"). Keep author-year citations identical (Cagan 1956 stays Cagan 1956). Equation numbering identical. Cross-references identical (point to §4.1 in IT same way EN does).

- [ ] **Step 2: Verify** placeholders for §1 and §2 are resolved.
- [ ] **Step 3: Commit** with message `docs: translate whitepaper chapters 1 and 2 to italian`.

---

### Task 32: Translate §3

Same procedure as Task 31 applied to §3. Commit message: `docs: translate whitepaper chapter 3 to italian`.

### Task 33: Translate §4.1

Same procedure for §4.1 (intro + 4.1.1 + 4.1.2 + 4.1.3). Commit: `docs: translate whitepaper chapter 4.1 demography to italian`.

### Task 34: Translate §4.2

Same procedure for §4.2 (intro + 4.2.1 + 4.2.2 + 4.2.3). Commit: `docs: translate whitepaper chapter 4.2 economy behavioral to italian`.

### Task 35: Translate §5 + §6 + §7

Commit: `docs: translate whitepaper chapters 5 to 7 to italian`.

### Task 36: Translate §8 + §9 + §10 + §11 + §12

Commit: `docs: translate whitepaper chapters 8 to 12 to italian`.

### Task 37: Mirror §13 References + translate Appendices A/B/C + EN-IT self-check

- [ ] **Step 1: §13 References** — copy EN §13 verbatim (bibliography is identical between EN and IT — same authors, same years, same DOI).
- [ ] **Step 2: Translate Appendices A/B/C** — same procedure.
- [ ] **Step 3: EN-IT self-check before commit**

For each numbered equation (4.1) through (4.14) in EN: confirm it appears with identical numbering and identical mathematical content in IT.
For each citation in EN: confirm same author-year tag in IT (translated body, same tag).
For each parameter table: confirm same parameter names, ranges, and values.
For each cross-reference (§X.Y format): confirm same target.

If any divergence found, fix it and re-check.

- [ ] **Step 4: Verify** the IT file has no `<da tradurre>` markers.
- [ ] **Step 5: Commit** with message `docs: complete whitepaper italian translation with appendices and en-it self-check`.

---

### Task 38: Rewrite README.md (EN)

**Files:**
- Modify: `README.md`

**Sources to consult:**
- Spec §4.2 README skeleton
- Current `README.md` (for vision tagline distillation)
- `docs/whitepaper/epocha-whitepaper.md` (final source of truth for status table)

- [ ] **Step 1: Replace README.md with the new content**

Per spec §4.2 skeleton: language switch + badges, one-line tagline, banner image placeholder (intentional — not filled), Vision (4-5 sentences), Authoritative documentation (whitepaper EN + IT, CLAUDE.md, letture-consigliate), Quickstart (Docker + pytest + LLM provider), Project Structure (mapping), Status table, Roadmap, Contributing (with link to whitepaper-doc-sync rule in CLAUDE.md), License, Citing Epocha (BibTeX placeholder pointing to whitepaper).

Target ~200 lines (current is 493).

- [ ] **Step 2: Verify links resolve**

For each link in the rewritten README.md: confirm the file/anchor exists. Anchors in the whitepaper file should match heading text (Markdown auto-anchors).

- [ ] **Step 3: Commit** with message:

```bash
git commit -m "$(cat <<'EOF'
docs: rewrite README as developer-focused entry point

CHANGE: Replace the marketing-style README with a developer-focused
entry point per the catch-up spec. Keeps a four-sentence Vision block
at the top, links the bilingual whitepaper as the authoritative
documentation, and condenses the rest into Quickstart, Project
Structure, Status table, Roadmap, Contributing with the whitepaper
doc-sync rule, License, and a BibTeX citation snippet.
EOF
)"
```

---

### Task 39: Rewrite README.it.md (IT)

**Files:**
- Modify: `README.it.md`

Same procedure as Task 38. Italian translation of the new README.md, links pointing to `docs/whitepaper/epocha-whitepaper.it.md`. Commit message: `docs: rewrite italian README mirroring the english entry point`.

---

### Task 40: Add whitepaper-doc-sync rule to CLAUDE.md

**Files:**
- Modify: `CLAUDE.md`

**Sources to consult:**
- `feedback_whitepaper_doc_sync.md` (memory) for the rule wording

- [ ] **Step 1: Locate Documentation Sync section**

Run: `grep -n "Documentation Sync" CLAUDE.md`
Expected: at least one match. Identify the precise section.

- [ ] **Step 2: Add the rule**

Append (after the existing rules in that section) the following paragraph:

```markdown
**Whitepaper-code doc-sync rule**: PRs that modify code under
`epocha/apps/demography/` or
`epocha/apps/economy/{expectations,credit,banking,property_market}.py`
must update the corresponding chapter of the bilingual whitepaper
(`docs/whitepaper/epocha-whitepaper.md` and `.it.md`, chapters §4.1
and §4.2 respectively) in the same commit, or explain in the PR
description why the change does not affect the model. The mapping is
maintained in the project memory `feedback_whitepaper_doc_sync.md` and
will be expanded as modules in §8 are promoted to §4 after their
Round 2 audits converge.
```

- [ ] **Step 3: Commit** with message `docs: add whitepaper-doc-sync rule to CLAUDE.md`.

---

### Task 41: Cross-link verification across README EN, README IT, whitepaper EN, whitepaper IT

**Files:** read-only verification

- [ ] **Step 1: Check README → whitepaper links**

Run: `grep -nE "docs/whitepaper" README.md README.it.md`
Expected: every match references an existing file under `docs/whitepaper/`.

For every cross-reference like `[chapter X]` or `(#anchor-name)`: verify the heading exists in the target file.

- [ ] **Step 2: Check internal whitepaper cross-references**

Run: `grep -nE "§[0-9]+(\.[0-9]+)*" docs/whitepaper/epocha-whitepaper.md docs/whitepaper/epocha-whitepaper.it.md | head`
Spot-check: every §X.Y reference points to an existing chapter.

- [ ] **Step 3: Check spec backlinks**

For every spec referenced in §8 of the whitepaper, confirm the spec file exists.

If any link is broken, fix it inline.

- [ ] **Step 4: Commit only if fixes applied** with message `docs: fix cross-links in README and whitepaper after audit`.

---

### Task 42: Bibliography audit on whitepaper EN

**Files:** dispatch a critical-analyzer subagent (Opus); apply remediation in the whitepaper EN; convergence loop.

- [ ] **Step 1: Dispatch the audit**

Use the Agent tool with subagent_type `critical-analyzer`, model `opus`. Prompt template:

```
You are an adversarial bibliography auditor for a scientific whitepaper.
Your mandate is to find INCORRECT, UNJUSTIFIED, INCONSISTENT, or MISSING
citations. Be hostile.

Read `docs/whitepaper/epocha-whitepaper.md` end to end. For every
author-year citation in the body and every entry in §13 References:

1. Verify the entry has full bibliographic data (author, year, title,
   venue, DOI/URL).
2. Verify against primary source (use WebFetch on DOI or canonical
   archive when in doubt) that the citation reflects what the paper
   actually says.
3. Flag every citation in the body that has no entry in §13.
4. Flag every entry in §13 that is not cited anywhere in the body.
5. Flag every parameter or formula in §4 that is presented as derived
   from a cited source but is actually a tunable design choice.

Output: a categorized table INCORRECT/UNJUSTIFIED/INCONSISTENT/MISSING/
VERIFIED with row per finding. End with a verdict line:
"VERDICT: CONVERGED" or "VERDICT: NOT CONVERGED — N findings to
resolve".
```

- [ ] **Step 2: Resolve findings**

For each non-VERIFIED finding: apply fix in the whitepaper EN. Re-run the audit (Step 1) until VERDICT: CONVERGED. The convergence loop typically requires 2-4 rounds (per Demography precedent).

- [ ] **Step 3: Commit** the final remediation as a single commit (or one commit per round) with message `docs: bibliography audit round N findings resolved` per round.

---

### Task 43: Scientific consistency audit (whitepaper §4 vs code in develop)

- [ ] **Step 1: Dispatch the audit**

Subagent_type `critical-analyzer`, model `opus`. Prompt:

```
You are an adversarial scientific reviewer auditing whether the methods
chapters of the whitepaper accurately describe the implementation in
the codebase. Be hostile: find divergences.

Read:
- `docs/whitepaper/epocha-whitepaper.md` chapter 4
- `epocha/apps/demography/{mortality,fertility,couple,context,rng,template_loader}.py`
- `epocha/apps/economy/{expectations,credit,banking,property_market}.py`

For every formula, parameter value, algorithm step, and simplification
in chapter 4: verify it matches the code. Flag every divergence.

Output: INCORRECT/INCONSISTENT/MISSING/VERIFIED categorized table.
End: "VERDICT: CONVERGED" or "VERDICT: NOT CONVERGED".
```

- [ ] **Step 2: Resolve findings** — same loop pattern as Task 42.

If a finding indicates the whitepaper is wrong relative to the code: fix the whitepaper.
If a finding indicates the code is wrong relative to the cited source: STOP, escalate to Opus, open a code fix branch, audit, merge to develop, then resume.

- [ ] **Step 3: Commit** with message `docs: scientific consistency audit round N findings resolved`.

---

### Task 44: EN-IT consistency audit

- [ ] **Step 1: Dispatch the audit**

Subagent_type `critical-analyzer`, model `opus`. Prompt:

```
You are an adversarial reviewer of the EN-IT translation consistency
of the Epocha bilingual whitepaper. Be hostile: find content that
appears in one version and not the other, or whose meaning differs.

Read:
- `docs/whitepaper/epocha-whitepaper.md`
- `docs/whitepaper/epocha-whitepaper.it.md`

For every chapter, sub-chapter, equation, parameter table, citation,
and figure caption: verify the IT version matches the EN version
semantically. Flag:
- Content present in EN but absent in IT (or vice versa)
- Equations with different mathematical content
- Parameter tables with different values
- Citations with different author-year tags
- Cross-references pointing to different targets

Output: INCONSISTENT/MISSING categorized table.
End: "VERDICT: CONVERGED" or "VERDICT: NOT CONVERGED".
```

- [ ] **Step 2: Resolve findings** — fix the IT file (default — EN is authoritative); only fix EN if the EN itself is wrong.

- [ ] **Step 3: Commit** with message `docs: EN-IT consistency audit round N findings resolved`.

---

### Task 45: Run full pytest suite

**Files:** read-only

- [ ] **Step 1: Bring up Docker if needed**

Run: `docker compose -f docker-compose.local.yml ps`
If services are down: `docker compose -f docker-compose.local.yml up -d`

- [ ] **Step 2: Run the full test suite**

Run: `docker compose -f docker-compose.local.yml exec web pytest --cov=epocha -v`
Expected: 0 failed, 0 errors. The exact count should match the count from the previous merge of `develop` (no code changes were made in this branch, so test count is identical).

If any test fails: STOP — this branch should not have caused regressions since no code changed. Investigate (could be pre-existing flake or environmental).

- [ ] **Step 3: Document the run**

In the PR description draft (Task 48), include the exact pytest output line "X passed, 0 failed in Y seconds".

No commit — pytest run leaves no artifact.

---

### Task 46: Update whitepaper frontmatter with merge commit hash strategy

**Files:**
- Modify: `docs/whitepaper/epocha-whitepaper.md` and `docs/whitepaper/epocha-whitepaper.it.md`

The actual merge commit hash is unknown until the merge happens. Strategy:

- [ ] **Step 1: Verify the placeholder is in place**

Run: `grep -n "<filled-on-merge>" docs/whitepaper/epocha-whitepaper.md docs/whitepaper/epocha-whitepaper.it.md`
Expected: at least one occurrence each (frontmatter `frozen-at-commit` field, status headers in §4.1 and §4.2, Appendix B reproducibility section).

- [ ] **Step 2: Document the substitution procedure**

Add a one-line note at the top of the closure PR description (Task 48): "After merge, replace `<filled-on-merge>` with the actual merge commit hash via a follow-up commit `docs: pin whitepaper frozen-at-commit` on develop."

This avoids trying to predict the commit hash before the merge happens. The follow-up commit is small (sed-like replacement) and can be done immediately after merge.

No commit in this task — the substitution happens post-merge.

---

### Task 47: Sync memory backup

**Files:**
- Modify: `docs/memory-backup/*.md`

- [ ] **Step 1: Sync from live memory**

Run:
```bash
cp ~/.claude/projects/-Users-mauriziomocci-Documents-workspace-Opensource-epocha/memory/*.md docs/memory-backup/
git status docs/memory-backup/
```

Expected: 4-5 modified or new files (the new memories created in this branch: `project_audit_repass_batch_2026_04_12_pending.md`, `project_validation_experiments_pending.md`, `feedback_whitepaper_doc_sync.md`, `project_whitepaper_promotion_pipeline.md`, plus updated `MEMORY.md`).

- [ ] **Step 2: Commit** with message:

```bash
git add docs/memory-backup/
git commit -m "$(cat <<'EOF'
docs: sync memory backup with whitepaper catch-up follow-ups

CHANGE: Persist the four new memories created during the whitepaper
catch-up branch (audit re-pass debt, validation experiments follow-up,
whitepaper-code doc-sync rule, promotion pipeline) plus the updated
MEMORY.md index.
EOF
)"
```

---

### Task 48: Open final draft PR with summary and request heavy gate

**Files:** GitHub PR via `gh` CLI

- [ ] **Step 1: Push the branch**

Run: `git push -u origin feature/readme-and-whitepaper-catchup`

- [ ] **Step 2: Open draft PR**

Run:
```bash
gh pr create --draft --title "docs: bilingual whitepaper and developer-focused README catch-up" --body "$(cat <<'EOF'
## Summary

- Introduce the bilingual scientific whitepaper at `docs/whitepaper/epocha-whitepaper.md` and `.it.md`, covering Demography Plan 1+2 and Economy Behavioral as audited Methods chapters and listing other implemented modules in §8 as audit-pending.
- Replace the marketing-style README with a developer-focused entry point that links the whitepaper as authoritative documentation; mirror the rewrite in `README.it.md`.
- Add the whitepaper-doc-sync rule to `CLAUDE.md` and the corresponding mapping memory.
- Persist four follow-up memories: audit re-pass debt for the 2026-04-12 batch (HIGH priority after Plan 3), validation experiments execution (medium priority before paper submission), whitepaper-code doc-sync rule, and the §8 → §4 promotion pipeline.

## Heavy gate checklist

- [ ] Whitepaper EN bibliography audit CONVERGED (Task 42)
- [ ] Whitepaper EN scientific consistency audit CONVERGED (Task 43)
- [ ] EN-IT consistency audit CONVERGED (Task 44)
- [ ] Full pytest suite green (Task 45)
- [ ] Memory backup synced (Task 47)
- [ ] Post-merge follow-up tracked: replace `<filled-on-merge>` with the actual merge commit hash via a small `docs: pin whitepaper frozen-at-commit` commit on develop.

## Test plan

- [ ] Whitepaper EN renders correctly on GitHub
- [ ] Whitepaper IT renders correctly on GitHub
- [ ] README EN links resolve (whitepaper EN, CLAUDE.md, letture-consigliate)
- [ ] README IT links resolve (whitepaper IT, CLAUDE.md, letture-consigliate)
- [ ] CLAUDE.md whitepaper-doc-sync paragraph appears under Documentation Sync section
EOF
)"
```

- [ ] **Step 3: Report PR URL**

The `gh pr create` command outputs the PR URL. Report it back so the user can open the heavy gate review.

---

## Self-review

After writing this plan, performed inline self-review:

**Spec coverage** — every section of `docs/superpowers/specs/2026-04-26-readme-and-whitepaper-catchup-design.md` has at least one task implementing it:
- Spec §3 (whitepaper architecture) → Tasks 1-29 + 30-37 (translation)
- Spec §4 (README architecture) → Tasks 38-39
- Spec §5 (workflow + audits) → Tasks 42-44
- Spec §6 (doc-sync rule) → Task 40
- Spec §7 (decisions) → embedded in writing decisions
- Closure → Tasks 45-48

**Placeholder scan** — no `TBD/TODO/implement later` patterns in the plan body. Intentional placeholders are limited to:
- `<filled-on-merge>` strings in the whitepaper (closed by Task 46 follow-up post-merge)
- `<draft in Task X>` markers in the scaffold (closed task by task)

**Type consistency** — chapter and section numbers (`§4.1`, `§4.1.1`, etc.) match between the spec and this plan; equation numbering (4.1)-(4.14) is consistent across W2 tasks; file paths quoted are real paths in the repository.

**Spec gaps** — none identified.

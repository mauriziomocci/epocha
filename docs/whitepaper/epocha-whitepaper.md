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

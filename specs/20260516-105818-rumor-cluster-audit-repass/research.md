# Phase 0 Research: Rumor Cluster Audit Re-pass

**Branch**: `20260516-105818-rumor-cluster-audit-repass`
**Date**: 2026-05-16
**Source spec**: [spec.md](./spec.md)
**Plan**: [plan.md](./plan.md)

Three lookups required by `plan.md` Phase 0. Output below feeds into tasks.md (citation entries to add to whitepaper §13 + N-3 fix safety + N-8 citation candidate).

---

## Lookup 1 — Crossref DOI verification for 4 missing §13 citations (N-2)

### 1.1 Mayer, Davis, Schoorman (1995)

- **Decision**: cite as `Mayer, R. C., Davis, J. H., and Schoorman, F. D. (1995). An integrative model of organizational trust. *Academy of Management Review*, 20(3), 709-734.` DOI `10.2307/258792`.
- **Rationale**: Crossref query returned `10.2307/258792 — An Integrative Model of Organizational Trust` as the canonical AMR record. The spec.md originally suggested `10.5465/amr.1995.9508080335`; Crossref direct lookup on that DOI returns HTTP 200 metadata for the same paper (alternate identifier), but the JSTOR DOI is the canonical primary anchor used in most modern Author-Date citations. Both resolve.
- **Alternatives considered**: `10.5465/amr.1995.9508080335` (AMA-issued DOI) is also valid; `10.1093/oso/9780199288496.003.0004` is a 2006 OUP book chapter reprint, NOT the primary 1995 paper. Use JSTOR DOI as primary.

### 1.2 Graziano, Tobin (2002)

- **Decision**: cite as `Graziano, W. G., and Tobin, R. M. (2002). Agreeableness: dimension of personality or social desirability artifact? *Journal of Personality*, 70(5), 695-727.` DOI `10.1111/1467-6494.05021`.
- **Rationale**: Crossref direct lookup on `10.1111/1467-6494.05021` returned title "Agreeableness: Dimension of Personality or Social Desirability Artifact?", year 2002, container *Journal of Personality*. Exact match with the spec.md suggestion.
- **Alternatives considered**: none. Spec.md initially mentioned "JPSP 70(5), 695-727 OR Journal of Personality 70(5), 695-727" as ambiguous; Crossref confirms *Journal of Personality* is correct, not *Journal of Personality and Social Psychology*.

### 1.3 Castelfranchi, Falcone, Tan — CITATION YEAR CORRECTION REQUIRED

- **Decision**: cite as `Castelfranchi, C., Falcone, R., and Tan, Y.-H. (2001). The role of trust and deception in virtual societies. In Proceedings of the 34th Annual Hawaii International Conference on System Sciences (HICSS-34).` DOI `10.1109/hicss.2001.927042`.
- **Rationale**: Crossref search for "Castelfranchi Falcone Tan virtual societies" returned the HICSS-34 paper at DOI `10.1109/hicss.2001.927042`, year 2001 (conference held Jan 2001). The `belief.py` module docstring currently attributes this paper to 1998, which is INCORRECT. The 2001 HICSS paper is the canonical primary publication. A 2002 reprint exists at DOI `10.1080/10864415.2002.11044243` (Int. J. Electronic Commerce) but is derivative.
- **Alternatives considered**: spec.md said "1998" per the original 2026-04-12 audit and `belief.py` docstring. Cross-checked Crossref — no 1998 publication by these three authors with this title exists. The reference is the 2001 HICSS paper. **belief.py docstring must be fixed to year 2001** as part of N-2 resolution, ALONG WITH adding the §13 entry.

### 1.4 McCrae, Costa (2003)

- **Decision**: cite as `McCrae, R. R., and Costa, P. T. (2003). *Personality in Adulthood: A Five-Factor Theory Perspective* (2nd ed.). Guilford Press, New York.` ISBN `978-1-57230-827-2`.
- **Rationale**: pre-DOI monograph; ISBN is the canonical identifier. Title and edition confirmed by Guilford Publications catalog (no Crossref record for this specific monograph, as expected for books).
- **Alternatives considered**: McCrae & Costa (1987) JPSP 52(1) is already in §13 from prior catch-up; Costa & McCrae (1992) NEO PI-R manual is already in §13. The 2003 *Personality in Adulthood* second edition is a distinct work cited by `affinity.py` and must be added as a separate entry.

---

## Lookup 2 — N-8 design-rationale citation candidate for rival-coalition formation

- **Decision**: cite Axelrod (1984) *The Evolution of Cooperation* (already in §13 from prior catch-up commit `bf16d7f`).
- **Rationale**: Axelrod 1984 is the canonical reference for repeated dyadic interaction and conditional cooperation, including the observation that "rivals" in iterated games can act as coalition partners through tit-for-tat reciprocity. Already in the whitepaper bibliography → zero new §13 entry needed. The `affinity.py:_relationship_score` docstring update for N-8 cites this existing entry.
- **Alternatives considered**: Coleman, J. S. (1990) *Foundations of Social Theory* (Belknap/Harvard ISBN 978-0-674-31226-5) is also defensible and is the foundational work on social capital and coalition stability. But (a) it would require a new §13 entry, expanding scope, and (b) Axelrod's mechanism (tit-for-tat under repeated interaction) is closer to the actual code semantics (the existing `Relationship.relation_type` enum includes rivalry as a persisting dyadic state, which is the iterated-interaction setup). Use Axelrod, document Coleman as alternative in N-8 docstring footnote.
- **Decision risk**: if a future adversarial reviewer requires Coleman, add as separate finding in a later round.

---

## Lookup 3 — N-3 fix safety: `extract_action_sentiment` downstream consumer audit

Grep result (full):

```
epocha/apps/agents/reputation.py:136     # comment header for sentiment keyword tables
epocha/apps/agents/reputation.py:302     def extract_action_sentiment(content: str) -> float:   # definition
epocha/apps/agents/tests/test_reputation.py:6     from .reputation import extract_action_sentiment
epocha/apps/agents/tests/test_reputation.py:105   assert extract_action_sentiment("I decided to help. ...") > 0
epocha/apps/agents/tests/test_reputation.py:108   assert extract_action_sentiment("I decided to betray. ...") < 0
epocha/apps/agents/tests/test_reputation.py:111   assert extract_action_sentiment("I decided to rest. tired") == 0.0
epocha/apps/agents/tests/test_reputation.py:114   s = extract_action_sentiment("I decided to argue. angry")
epocha/apps/agents/information_flow.py:34      from .reputation import extract_action_sentiment, get_combined_score, update_reputation
epocha/apps/agents/information_flow.py:236     action_sentiment = extract_action_sentiment(distorted_content)
```

- **Decision**: N-3 fix is SAFE. The single non-test call site is `information_flow.py:236` and it feeds directly into `update_reputation` at line 269. Moving the call before the distortion pass (line 232) and passing the original `memory.content` to `extract_action_sentiment` does NOT affect any other consumer. The post-distortion `distorted_content` continues to feed downstream rumor retransmission (line 240+) unchanged.
- **Rationale**: zero cross-cutting impact. Refactor is local.
- **Alternatives considered**: thread both `original_sentiment` and `distorted_content` separately through the propagation step (more invasive); compute sentiment from a structured `action_type` field on Memory if present (requires Memory schema change — escalation per spec.md Edge Cases). Default to the lowest-risk fix: move the existing call before distortion.

---

## Output

All three lookups CLOSED. Findings to propagate to tasks.md:

1. **Spec.md correction needed**: spec.md citation candidates for N-2 list "Castelfranchi-Falcone-Tan 1998" — actual year is **2001** (HICSS-34). Update spec.md User Story 2 acceptance scenario 2 + FR-005 to read "2001". Also update `belief.py` docstring at module top to fix the year attribution. This is an additional micro-finding caught by the Phase 0 lookup; track in tasks.md as part of N-2.

2. **DOI confirmed for 3 of 4 citations** (Mayer 10.2307/258792, Graziano-Tobin 10.1111/1467-6494.05021, Castelfranchi-Falcone-Tan 10.1109/hicss.2001.927042) and ISBN confirmed for the monograph (McCrae-Costa 2003 ISBN 978-1-57230-827-2).

3. **N-8 cites existing Axelrod 1984 §13 entry**; no new §13 entry; docstring footnote mentions Coleman 1990 as alternative.

4. **N-3 fix safety confirmed**; move `extract_action_sentiment` call before distortion pass; no downstream consumer affected.

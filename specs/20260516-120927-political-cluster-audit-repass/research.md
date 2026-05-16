# Phase 0 Research: Political Cluster Audit Re-pass

**Branch**: `20260516-120927-political-cluster-audit-repass`
**Date**: 2026-05-16
**Source spec**: [spec.md](./spec.md)
**Plan**: [plan.md](./plan.md)

Four lookups required by `plan.md` Phase 0. Output feeds into tasks.md (replacement citations for E-1 and S-3, design decision on X-1 layering, fix-safety verification for G-2 regression risk).

---

## Lookup 1 — Crossref DOI verification for E-1 candidate citations (charisma in elections)

### 1.1 Weber (1922)

- **Decision**: cite as `Weber, M. (1922). *Wirtschaft und Gesellschaft: Grundriss der verstehenden Soziologie*. J.C.B. Mohr (Paul Siebeck), Tübingen.` Pre-DOI monograph. English translation `Weber, M. (1978). *Economy and Society: An Outline of Interpretive Sociology* (G. Roth & C. Wittich, Eds. & Trans.). University of California Press, Berkeley.` ISBN `978-0-520-03500-3` for the canonical English edition.
- **Rationale**: Weber's *Wirtschaft und Gesellschaft* is the foundational work on charismatic authority as a distinct legitimacy mode alongside legal-rational and traditional. The §13 entry should anchor on the 1922 original date with the 1978 University of California English edition as the practical reference. No Crossref record for the 1922 work as expected for pre-DOI monographs.
- **Alternatives considered**: Weber's 1919 essay "Politik als Beruf" ("Politics as a Vocation") also discusses charisma but is narrower in scope. The monograph is the canonical citation for charismatic authority as an analytical construct used in modern political science.

### 1.2 Merolla & Zechmeister (2011)

- **Decision**: cite as `Merolla, J. L., and Zechmeister, E. J. (2011). The nature, determinants, and consequences of Chávez's charisma: evidence from a study of Venezuelan public opinion. *Comparative Political Studies*, 44(1), 28-54.` DOI `10.1177/0010414010381076`.
- **Rationale**: Crossref direct lookup returned full bibliographic metadata. The paper empirically links candidate charisma to voter behavior in a comparative-politics setting and is the strongest specific empirical anchor for "charisma influences voting" claims in modern political science.
- **Alternatives considered**: Bligh, M. C., & Robinson, J. L. (2010) on charisma transfer (broader-scope, less specific to electoral outcomes). The Merolla-Zechmeister 2011 paper is preferred because it is in the standard comparative-politics top venue and directly cited in election-modeling reviews.

### 1.3 Bass (1985)

- **Decision**: cite as `Bass, B. M. (1985). *Leadership and Performance Beyond Expectations*. Free Press, New York.` ISBN `978-0-02-901810-7`. Pre-DOI monograph.
- **Rationale**: Bass 1985 is the foundational monograph on transformational leadership, which subsumes charisma as one of the four dimensions (idealized influence). Often cited in election studies as the bridge between Weberian charisma and modern leadership-effectiveness research. No Crossref DOI for the monograph as expected.
- **Alternatives considered**: Bass & Riggio (2006) *Transformational Leadership* 2nd ed. is a popular textbook restatement but the 1985 work is the primary source.

### 1.4 Election charisma replacement strategy

- **Decision**: replace Zonis & Joseph (1994) with `Weber 1922 + Merolla-Zechmeister 2011` as the primary anchor pair. Bass 1985 is the optional secondary citation for the transformational-leadership framing if `election.py` discusses leadership-quality dimensions beyond charisma proper. Note that `election.py` already cites Weber 1922 inline at line 30 (verified by code grep on develop @ `1c75854`); the §13 bibliography just needs to include the matching entry.
- **Rationale**: minimal-scope replacement. Weber provides the theoretical foundation, Merolla-Zechmeister provides the empirical electoral-context evidence. Two-citation anchor is defensible and parsimonious.

---

## Lookup 2 — Crossref DOI verification for S-3 alternative citation (Miller-Lynam 2001)

- **Decision**: cite as `Miller, J. D., and Lynam, D. (2001). Structural models of personality and their relation to antisocial behavior: a meta-analytic review. *Criminology*, 39(4), 765-798.` DOI `10.1111/j.1745-9125.2001.tb00940.x`.
- **Rationale**: Crossref direct lookup confirmed full bibliographic metadata. The meta-analysis links low conscientiousness and low agreeableness to antisocial behavior, which is the strongest empirical anchor for the `conscientiousness < 0.4` corruption-susceptibility threshold in `stratification.py:process_corruption`. The paper is already cited inline in the current code (verified at `stratification.py:208-211`), so the §13 entry just needs to be added if missing.
- **Alternatives considered**: Sutin, A. R., et al. (2010) on conscientiousness and unethical behavior is more recent but narrower. Miller-Lynam 2001 is the meta-analytic anchor and is the cleaner citation for the threshold's directional anchoring (low conscientiousness → higher corruption susceptibility).

---

## Lookup 3 — X-1 design decision: unify corruption update OR document layering

- **Decision**: document the layering as deliberate; do NOT unify.
- **Rationale**: the two corruption-update sites encode mechanistically distinct phenomena that compose additively:
  - `stratification.py:process_corruption` (step 3 of the political-tick pipeline) models personality-driven petty corruption by the head-of-state. Driver: `conscientiousness` of the agent in power. Mechanism: wealth extraction with bounded skim rate. Frequency: per-tick.
  - `government.py:update_government_indicators` (step 4) models institutional-oversight-driven systemic corruption pressure. Driver: `oversight = (justice + bureaucracy + media) / 3`. Mechanism: pressure-vs-decay differential bounded by `corruption_resistance` (a government-type parameter). Frequency: per-tick.

  Unifying the two into a single path would lose the analytical distinction between actor-level corruption (personality) and system-level corruption (institutional design). Both mechanisms are independently sourced in the literature (Miller-Lynam 2001 for personality; Acemoglu-Robinson 2006 for institutional design). The current code already carries an inline `Note` comment at `government.py:339-342` documenting the co-existence. Round 2 verification target: the documentation must be sufficiently explicit at BOTH call sites (one at step 3, one at step 4) to make the layering obvious to a future auditor.
- **Alternatives considered**: unification via a single `apply_corruption_update(personality_component, institutional_component)` aggregator would require an architectural refactor of the political-tick pipeline (step ordering, transaction boundary, idempotency). Out of scope for a fix branch; would need its own spec.
- **Decision risk**: if a Round 3 reviewer (future) insists on unification, escalate as a separate spec, not a Round 2 expansion.

---

## Lookup 4 — G-2 fix safety: existing coup-test determinism audit

Grep result for the coup test file and the deprecated constant:

```
epocha/apps/world/tests/test_government.py:107:    def test_coup_succeeds_when_conditions_met(...):
epocha/apps/world/tests/test_government.py:108:        """Coup evaluation is stochastic. We seed the RNG so the test is deterministic."""
epocha/apps/world/tests/test_government.py:119:        from epocha.apps.world.government import check_coups
epocha/apps/world/tests/test_government.py:120:        # Seed produces a low first random.random() value, ensuring the coup
epocha/apps/world/tests/test_government.py:122:        random.seed(42)
epocha/apps/world/tests/test_government.py:123:        result = check_coups(simulation, tick=20)

epocha/apps/world/government.py:84:# _COUP_SUCCESS_THRESHOLD is no longer used; retained as a reference calibration point.
epocha/apps/world/government.py:85:_COUP_SUCCESS_THRESHOLD: float = 0.50
epocha/apps/world/government.py:587:        if random.random() < success_probability:
```

- **Decision**: G-2 is ALREADY FIXED on develop @ `1c75854`. The coup decision at line 587 already uses `random.random() < success_probability` (stochastic). The constant `_COUP_SUCCESS_THRESHOLD` at line 85 is retained only as a reference calibration point with a clarifying comment at line 84. The test at line 107-123 already acknowledges stochastic behavior and seeds the RNG for determinism.
- **Rationale**: zero behavioral change required. Round 2 work for G-2 is documentation verification: confirm the line-84 comment explicitly says "deprecated" or "no longer used as a decision threshold", AND confirm `_COUP_SUCCESS_THRESHOLD` is exported (currently a module-level name with underscore prefix indicating private — acceptable). Optional cleanup: remove `_COUP_SUCCESS_THRESHOLD` entirely since no caller references it. The grep returned zero non-declaration references, so removal is safe.
- **Alternatives considered**: leave as-is with the existing comment (status quo); remove the constant entirely (cleanest, zero-regression-risk per grep). Plan tasks default to "leave with documented deprecation comment" for minimal-diff posture; if Round 2 auditor flags the dead constant as a smell, the removal fix is a one-line follow-up.

---

## Output

All four lookups CLOSED. Findings to propagate to tasks.md:

1. **E-1 citation replacement**: use Weber (1922) + Merolla-Zechmeister (2011) `10.1177/0010414010381076` as the primary anchor pair. Bass (1985) optional secondary. Weber is already cited inline at `election.py:30`; the §13 bibliography needs a Weber 1922 entry (verify whether already present from prior catch-up) and a new Merolla-Zechmeister 2011 entry.

2. **S-3 alternative citation**: Miller-Lynam (2001) `10.1111/j.1745-9125.2001.tb00940.x` is already cited inline in `stratification.py:208-211`. The §13 bibliography needs the corresponding entry if not already present.

3. **X-1 decision**: document the corruption layering as deliberate co-existence; do NOT unify. Verify the inline `Note` at `government.py:339-342` is sufficiently explicit, and add a mirror note at `stratification.py:process_corruption` describing the same layering from the other side.

4. **G-2 status**: ALREADY FIXED on develop. Round 2 work is verification + optional removal of the deprecated `_COUP_SUCCESS_THRESHOLD` constant (zero non-declaration references confirmed by grep). No test breakage risk.

5. **E-3 Lewis-Beck-Stegmaier (2000) bonus DOI verification**: Crossref confirmed `10.1146/annurev.polisci.3.1.183`, *Annual Review of Political Science* 3, 183-219. Useful when adding the forward-pointer for FR-014 in `election.py` docstring; if a §13 entry is desired, the DOI is verified.

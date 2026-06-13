# Phase 0 Research: Factions Audit Re-pass

**Branch**: `20260516-183045-factions-audit-repass`
**Date**: 2026-05-16
**Source spec**: [spec.md](./spec.md)
**Plan**: [plan.md](./plan.md)

Three lookups required by `plan.md` Phase 0. Output feeds into tasks.md (citation-rewrite text for F-1, F-2, plus Known Limitations text for F-3 and F-4).

---

## Lookup 1 — Judge et al. (2002) primary reference verification

### 1.1 Canonical citation

- **Decision**: cite as `Judge, T. A., Bono, J. E., Ilies, R., and Gerhardt, M. W. (2002). "Personality and leadership: A qualitative and quantitative review". Journal of Applied Psychology, 87(4), 765-780.` DOI `10.1037/0021-9010.87.4.765`. Crossref-resolvable. Open peer-reviewed venue published by the American Psychological Association.

- **Rationale**: this paper is the canonical meta-analytic review of the trait-leadership relationship for the Five-Factor Model era. It aggregates 222 correlations from 73 samples, reports corrected meta-analytic correlations between each Big Five dimension and leadership emergence / leadership effectiveness, and explicitly establishes Extraversion as the strongest correlate (ρ ≈ 0.31 for leadership emergence), followed by Conscientiousness (ρ ≈ 0.28), Openness (ρ ≈ 0.24), Neuroticism (ρ ≈ −0.24, inverse), with Agreeableness near zero (ρ ≈ 0.08). This is the primary empirical anchor that justifies the trait-based scoring approach in `compute_leadership_score()` WITHOUT claiming that the specific weight tuple (0.30/0.20/0.15/0.20/0.15) is derived from these effect sizes.

- **Mapping to factions.py weights**: the 0.30 weight on charisma is roughly proportional to the Extraversion effect size; the 0.20 on intelligence overlaps with the Openness-as-cognitive-ability proxy; the 0.20 on internal_sentiment captures the social-attractiveness component that the Extraversion effect partly reflects; the 0.15 on wealth_rank and 0.15 on seniority are non-Big-Five components (status and tenure) that do not map to Judge 2002 directly. The mapping is qualitative and the spec frames the weights as tunable design parameters consistent with the *direction* of the Judge 2002 effect sizes but not derived from them.

- **Alternatives considered**: Bono and Judge (2004), "Personality and transformational and transactional leadership: A meta-analysis", *Journal of Applied Psychology* 89(5):901-910, DOI `10.1037/0021-9010.89.5.901` — narrower scope, focused on transformational leadership style rather than emergence. Antonakis, House, and Simonton (2017), "Can super smart leaders suffer too much of a good thing? The curvilinear effect of intelligence on perceived leadership behavior", *Journal of Applied Psychology* 102(7):1003-1021 — relevant to the intelligence weight but cites Judge 2002 itself as the meta-analytic anchor. Judge 2002 remains the standard citation.

### 1.2 Citation-rewrite text for tasks.md

For the `compute_leadership_score()` docstring at `factions.py:96-117` and the module-level "Scientific basis" block at `factions.py:14-19`:

> Leadership emergence score. The trait-based scoring approach is grounded in Judge, Bono, Ilies, and Gerhardt (2002), "Personality and leadership: A qualitative and quantitative review", *Journal of Applied Psychology* 87(4):765-780, DOI 10.1037/0021-9010.87.4.765, which provides meta-analytic effect sizes for the Big Five trait-leadership relationship: Extraversion is the strongest correlate of leadership emergence (ρ ≈ 0.31), followed by Conscientiousness (≈ 0.28), Openness (≈ 0.24), and Neuroticism (≈ −0.24). Stogdill (1948), "Personal factors associated with leadership", *Journal of Psychology* 25(1):35-71, supports the broader principle that personal traits correlate with leadership emergence; Stogdill's literature survey does NOT supply a weighted-sum formula and charisma in particular is a Weberian sociological concept (Weber 1922) rather than a Stogdill trait correlate. The specific weights in this implementation (charisma 0.30, intelligence 0.20, wealth_rank 0.15, internal_sentiment 0.20, seniority 0.15) are tunable design parameters consistent with the *direction* of Judge 2002 effect sizes but not derived from them; they are part of the simulation's calibration budget per the Known Limitations block in this module's docstring header.

---

## Lookup 2 — Stogdill (1948) actual content verification

### 2.1 Canonical citation

- **Decision**: cite as `Stogdill, R. M. (1948). "Personal factors associated with leadership: A survey of the literature". Journal of Psychology, 25(1), 35-71.` DOI `10.1080/00223980.1948.9917362`. Pre-DOI archival paper now indexed by Taylor & Francis. The follow-up monograph `Stogdill, R. M. (1974). Handbook of Leadership: A Survey of Theory and Research. Free Press, New York.` (ISBN `978-0-02-931810-3`) is the canonical extended version and is often cited interchangeably.

- **Rationale**: Stogdill's 1948 paper is a literature review aggregating findings across roughly 124 prior studies of leadership traits. It identifies five categories of traits associated with leadership: capacity (intelligence, alertness, verbal facility, originality, judgment), achievement (scholarship, knowledge, athletic accomplishment), responsibility (dependability, initiative, persistence, aggressiveness, self-confidence, desire to excel), participation (activity, sociability, cooperation, adaptability, humour), and status (socio-economic position, popularity). The paper does NOT supply a weighted-sum formula combining these traits into a single leadership score. It explicitly cautions against pure trait-based explanations of leadership and was historically influential in shifting the field toward contingency theories (Stogdill's own later position).

- **Charisma absence**: charisma is NOT among Stogdill's trait categories. The concept of charisma as a leadership attribute is most closely associated with Max Weber's sociology of authority (Weber 1922, *Wirtschaft und Gesellschaft*, posthumous; English edition Weber, M. (1978), *Economy and Society: An Outline of Interpretive Sociology* (G. Roth and C. Wittich, Eds.), University of California Press, ISBN `978-0-520-03500-3`). Modern operationalizations of charisma in leadership research draw on Conger and Kanungo (1987), "Toward a behavioral theory of charismatic leadership in organizational settings", *Academy of Management Review* 12(4):637-647, and Antonakis, Bastardoz, Jacquart, and Shamir (2016), "Charisma: An ill-defined and ill-measured gift", *Annual Review of Organizational Psychology and Organizational Behavior* 3:293-319, DOI `10.1146/annurev-orgpsych-041015-062305`.

### 2.2 Citation-rewrite text for tasks.md

For the module-level "Scientific basis" block at `factions.py:14-19`, the Stogdill clause becomes:

> Stogdill (1948), "Personal factors associated with leadership: A survey of the literature", *Journal of Psychology* 25(1):35-71, supports the broader principle that personal traits (intelligence, dependability, social participation, status) correlate with leadership emergence. Stogdill's literature survey identified five trait categories but did NOT propose a weighted-sum scoring formula and explicitly cautioned against pure trait-based explanations of leadership. Charisma is NOT a Stogdill trait category: in this module charisma is treated as a leadership attribute in the Weberian tradition (Weber 1922) and its modern operationalizations (Antonakis et al. 2016).

---

## Lookup 3 — Dunbar (1992) nested-group hierarchy actual claim verification

### 3.1 Canonical citation

- **Decision**: cite as `Dunbar, R. I. M. (1992). "Neocortex size as a constraint on group size in primates". Journal of Human Evolution, 22(6), 469-493.` DOI `10.1016/0047-2484(92)90081-J`. The 5/15/50/150 nested hierarchy is from later work: `Zhou, W.-X., Sornette, D., Hill, R. A., and Dunbar, R. I. M. (2005). "Discrete hierarchical organization of social group sizes". Proceedings of the Royal Society B, 272(1561), 439-444.` DOI `10.1098/rspb.2004.2970`.

- **Rationale**: Dunbar's 1992 paper establishes the cognitive constraint hypothesis: in primates the size of stable social groups correlates with neocortex ratio, and for *Homo sapiens* this projects to a cognitive limit of approximately 148 (commonly rounded to 150) stable social relationships. The paper does NOT introduce the 5/15/50/150 nested-hierarchy structure. That decomposition comes from the 2005 Zhou-Sornette-Hill-Dunbar discrete-hierarchical-organization paper, which fits a scaling law to observed group-size distributions in hunter-gatherer societies, modern social networks, and primate troops, finding ratios of approximately 3 between successive layers. In that nested hierarchy, the "5" is the innermost layer commonly interpreted as the support clique (closest emotional ties, daily-contact intimates), NOT a coordination-cost boundary in any organizational-design sense.

- **Implication for factions.py threshold of 5**: the size-penalty threshold of 5 in `update_group_cohesion()` at `factions.py:306` is a simulation design choice. It is NOT derived from Dunbar's neocortex-ratio cognitive limit (which is 150) nor from the support-clique interpretation of the 5-layer in Zhou et al. 2005 (which is a stable-tie estimate, not an organizational-coordination cost boundary). Coordination cost above small-group thresholds is a generic principle in organizational psychology — see for example `Hackman, J. R. (2002). Leading Teams: Setting the Stage for Great Performances. Harvard Business School Press.` ISBN `978-1-57851-333-1`, which argues that teams of 4-6 are typically the upper bound for fully-cohesive collaborative units before coordination overhead dominates — but no widely accepted empirical anchor pins the value to 5 specifically.

### 3.2 Citation-rewrite text for tasks.md

For the `update_group_cohesion()` docstring at `factions.py:240-256` (size-penalty derivation), the Dunbar clause is dropped or strongly qualified:

> size_penalty = max(0, member_count − 5): coordination cost above a small-group threshold. The threshold value of 5 is a tunable design parameter; coordination cost above small-group thresholds is a generic principle in organizational psychology (see Hackman 2002, "Leading Teams", for the argument that teams of 4-6 are typically the upper bound for fully-cohesive collaborative units before coordination overhead dominates), but no widely accepted empirical anchor pins the value to 5 specifically. The 5 is NOT derived from Dunbar's nested-group hierarchy (Zhou et al. 2005), in which "5" is the innermost intimate-clique stratum representing closest emotional ties — not a coordination cost boundary. Dunbar's number proper (Dunbar 1992) is approximately 150 and addresses the cognitive limit on stable social relationships, which is orders of magnitude beyond the typical Epocha group size.

### 3.3 Disposition of Dunbar (1992) in whitepaper §13

Two options:

- **Option A (preferred)**: keep Dunbar (1992) in §13 with full citation; remove it from the factions.py docstring and from the §4.7 chapter body; add Hackman (2002) and Zhou et al. (2005) to §13 as the actual conceptual anchors used.
- **Option B**: remove Dunbar (1992) from §13 entirely; add Hackman (2002) as the sole new entry.

Decision: Option A. Dunbar (1992) is the canonical reference for the nested-hierarchy concept that the size-penalty threshold ALLUDES to even if not directly derived from it; keeping it in the bibliography with the explicit "not the source of the 5 threshold" disclaimer in the §4.7 narrative is the lowest-risk path and preserves the cross-reference for readers familiar with the literature.

---

## Output

All three lookups CLOSED. Findings to propagate to tasks.md:

1. **F-1 leadership citation rewrite**: use the Lookup 1.2 text for the `compute_leadership_score()` docstring and the module-level "Scientific basis" block. Judge et al. (2002) added with DOI `10.1037/0021-9010.87.4.765` as the primary meta-analytic anchor. Stogdill (1948) retained as the trait-correlate principle source with explicit "did NOT propose a weighted-sum formula" disclaimer. Charisma attributed to Weber (1922) and modern operationalizations (Antonakis et al. 2016). Weights labelled as tunable design parameters.

2. **F-2 Dunbar rewrite**: use the Lookup 3.2 text for the `update_group_cohesion()` docstring. Threshold value 5 labelled as a tunable design parameter. Dunbar (1992) attribution dropped from the inline derivation; retained in §13 with explicit "NOT the source of the 5 threshold" disclaimer in the §4.7 narrative. Hackman (2002) added as the generic-principle anchor.

3. **F-3 cohesion coefficients reframing**: doc-only. All four coefficients (0.10 cooperation, 0.15 conflict, 0.02 size penalty, 0.05 leader effectiveness) labelled as tunable design parameters in the inline comment at `factions.py:43-49` and the docstring at `factions.py:240-256`. Baumeister et al. (2001) retained only as the source of the qualitative direction of the asymmetry (negativity bias direction), NOT as the source of the 1.5:1 ratio. The absolute magnitudes documented as part of the simulation's calibration budget tied to tick frequency.

4. **F-4 schism order-dependence promotion**: doc-only. Move the buried inline limitation note at `factions.py:465-468` to the module docstring's Known Limitations block per FR-005. Preserve a shortened inline forward reference at the original location. Also document the same order-dependence in `_detect_and_propose_factions()` cluster building.

5. **§13 bibliography updates**: add Judge et al. (2002) entry with DOI; add Hackman (2002) entry with ISBN; conditionally add Weber (1922) and Antonakis et al. (2016) entries if introduced by the §4.7 narrative rewrite; conditionally add Zhou et al. (2005) if the §4.7 narrative references the nested-hierarchy disclaimer explicitly; retain Dunbar (1992) entry per Lookup 3.3 Option A; retain Stogdill (1948), Festinger et al. (1950), Olson (1965), Axelrod (1984), Baumeister et al. (2001).

6. **Pytest baseline expectation**: ≥809 after Branch 4 closure (per Branch 4 tasks.md T002 expectation); doc-only fixes add zero tests; conditional concurrency or DRY regression tests under Round 2 auditor flag add ≤2.

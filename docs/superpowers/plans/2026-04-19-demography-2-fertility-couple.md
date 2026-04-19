# Demography Implementation — Plan 2: Fertility, Couple, LLM Actions

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Phase 5 implementation runs on Sonnet 4.6 per the model selection policy; escalation to Opus is triggered by any strategic decision outside the specified execution.

**Goal:** Deliver fertility dynamics (Hadwiger ASFR × Becker × Malthusian ceiling with joint mortality-fertility resolution), couple formation infrastructure (Gale-Shapley stable matching library + runtime pair_bond / separate handlers with canonical ordering enforcement + arranged marriage support), and the three new LLM-driven actions (`pair_bond`, `separate`, `avoid_conception`) integrated into the decision pipeline with era-aware filtering.

**Architecture:** Two new modules (`fertility.py`, `couple.py`) and targeted extensions to existing files. Fertility produces a per-agent tick birth probability gated by Couple presence and avoid-conception flag, with childbirth mortality resolved jointly with the ordinary HP draw per spec §Sezione 1 C-1 fix. Couple provides a pure-function Gale-Shapley matcher (to be invoked by Plan 4 initialization) plus runtime intent registration and tick+1 resolution consistent with the property market pattern from Economy Spec 2. Three actions hook into the existing `decision.py` + `simulation/engine.py` handler surface with mood/weight calibration. Dynamic filter at prompt build time removes era-unavailable actions.

**Tech Stack:** Django ORM, PostgreSQL, pytest. No new runtime dependencies.

**Spec:** `docs/superpowers/specs/2026-04-18-demography-design-it.md` (authoritative Italian, CONVERGED round 4)

**Depends on:** Plan 1 merged into develop (commit `41bf508`).

**Follow-up plans:**
- Plan 3 — Inheritance + Migration
- Plan 4 — Initialization + Engine orchestration + Historical validation

**IMPORTANT notes for implementers:**
- Tests run in Docker: `docker compose -f docker-compose.local.yml exec web pytest ...`
- All new tests use PostgreSQL, no SQLite.
- `SUBSISTENCE_NEED_PER_AGENT`, `add_to_treasury`, `compute_subsistence_threshold`, `compute_aggregate_outlook`, and `get_seeded_rng` are already available from Plan 1. Use them directly; do not re-define.
- `AgentFertilityState` model was created in Plan 1 but never populated; this plan is the first writer.
- `Couple.CheckConstraint couple_canonical_ordering` already enforces `agent_a.id < agent_b.id`. Couple creation must ORDER the agents before saving, or the save raises `IntegrityError`. Helper `_ordered_pair()` in `couple.py` does this.
- Real implementation code has English comments and docstrings. Italian only in the spec.
- The spec code blocks for Becker modulation and the bodies of `compute_subsistence_threshold`/`compute_aggregate_outlook` had bugs fixed during Plan 1 implementation; trust the code that exists under `epocha/apps/demography/context.py`, not the spec snippets for those helpers.

---

## File Structure (Plan 2 scope)

| File | Responsibility | New/Modify |
|------|---------------|------------|
| `epocha/apps/demography/fertility.py` | Hadwiger ASFR × Becker × Malthusian + joint childbirth mortality | New |
| `epocha/apps/demography/couple.py` | Gale-Shapley + homogamy scoring + pair_bond/separate handlers + canonical ordering | New |
| `epocha/apps/agents/decision.py` | Add pair_bond, separate, avoid_conception to system prompt + era filter | Modify |
| `epocha/apps/simulation/engine.py` | Action handlers + mood delta + emotional weight entries | Modify |
| `epocha/apps/dashboard/formatters.py` | Verb entries for the three new actions | Modify |
| `epocha/apps/demography/tests/test_fertility.py` | Fertility unit tests | New |
| `epocha/apps/demography/tests/test_couple.py` | Couple and Gale-Shapley tests | New |
| `epocha/apps/demography/tests/test_decision_actions.py` | Decision prompt filtering and action handler tests | New |
| `epocha/apps/demography/tests/test_integration_plan2.py` | End-to-end integration: borrow+pair_bond+birth+separate cycle | New |

---

## Tasks summary

1. Fertility module skeleton with Hadwiger ASFR
2. Becker modulation function
3. Malthusian soft ceiling
4. Combined `tick_birth_probability`
5. AgentFertilityState helper: `set_avoid_conception_flag`, `is_avoid_conception_active_this_tick`
6. Joint mortality-fertility resolution (pregnancy detection + childbirth outcome)
7. Fertility unit tests
8. Couple module skeleton + `_ordered_pair` helper + homogamy scoring
9. Gale-Shapley stable matching library function
10. `form_couple` helper enforcing canonical ordering + couple_type
11. Pair-bond intent registration (tick N) and tick+1 resolution
12. Separate intent registration + tick+1 resolution with era flag
13. Automatic couple dissolution on partner death (signal or direct utility)
14. Arranged marriage extended payload parser
15. Couple module unit tests
16. Extend `agents/decision.py` system prompt with three actions
17. Dynamic era filter removes unavailable actions at prompt build
18. Action handler dispatch in `simulation/engine.py`
19. Mood delta and emotional weight entries for the three actions
20. Dashboard verb entries
21. Decision + handlers unit tests
22. End-to-end integration test covering a full pair_bond → birth → separate cycle
23. Plan 2 closing: full suite green, draft PR opened, adversarial audit dispatched

---

### Task 1: Fertility module skeleton with Hadwiger ASFR

**Files:**
- Create: `epocha/apps/demography/fertility.py`

- [ ] **Step 1: Create the module**

```python
"""Fertility model for demography: Hadwiger ASFR modulated by Becker (1991)
economic signals, bounded by a Malthusian soft ceiling.

Sources:
- Hadwiger, H. (1940). Eine analytische Reproduktionsfunktion.
  Skandinavisk Aktuarietidskrift 23, 101-113. Canonical normalization per
  Chandola, Coleman & Hiorns (1999) Population Studies 53(3) and
  Schmertmann (2003) Demographic Research 9.
- Becker, G.S. (1991). A Treatise on the Family. Harvard University Press.
- Malthus-Ricardo preventive check formalization inspired by
  Ashraf & Galor (2011) AER 101(5).
"""
from __future__ import annotations

import math
from typing import Mapping


def hadwiger_asfr(age: float, params: Mapping[str, float]) -> float:
    """Age-specific fertility rate at age a using the canonical Hadwiger form.

    f(a) = (H * T / (R * sqrt(pi))) * (R / a) ** 1.5 *
           exp(-T ** 2 * (R / a + a / R - 2))

    where H is the target total fertility rate (integral of f over fertile ages),
    R is the Hadwiger shape parameter related to peak fertility age, and T
    controls the spread of the distribution.

    Returns 0.0 for ages outside the biologically fertile window [12, 50] and
    for non-positive ages.
    """
    if age <= 0 or age < 12 or age > 50:
        return 0.0
    H = float(params["H"])
    R = float(params["R"])
    T = float(params["T"])
    ratio = R / age
    coef = (H * T) / (R * math.sqrt(math.pi))
    shape = ratio ** 1.5
    tail = math.exp(-(T ** 2) * (ratio + age / R - 2.0))
    return coef * shape * tail
```

- [ ] **Step 2: Manual sanity check**

Run: `docker compose -f docker-compose.local.yml exec web python -c "from epocha.apps.demography.fertility import hadwiger_asfr; print(hadwiger_asfr(26, {'H': 5.0, 'R': 26, 'T': 3.5}))"`

Expected: a finite positive number in the vicinity of 0.38 (peak of a Hadwiger distribution with H=5, R=26, T=3.5 is H·T/(R·sqrt(pi)) ≈ 0.38). The T values in Plan 1's JSON templates (0.35, 0.38, 0.42, 0.40) are a factor-of-ten error and must be corrected to (3.5, 3.8, 4.2, 4.0). A companion fix commit in this plan updates the templates and the spec tables accordingly — see the note below.

**Spec and template correction (carried by this plan)**: the Hadwiger `T` values shipped in Plan 1 were off by a factor of ten — Chandola, Coleman & Hiorns (1999) and Schmertmann (2003) both use T in the range [2, 10] for realistic fertility distributions. With the original T=0.35 the peak drops to ~0.04 and the distribution peaks at the lower age bound instead of at R. Fix applied in this plan on the same feature branch: update the five JSON templates in `epocha/apps/demography/templates/` and the Hadwiger tables in both spec files. Plan 1 tests are unaffected because Plan 1 never computes Hadwiger values.

- [ ] **Step 3: No commit yet**

Commit lands in Task 7 together with the fertility tests.

---

### Task 2: Becker modulation function

**Files:**
- Modify: `epocha/apps/demography/fertility.py`

- [ ] **Step 1: Append the Becker modulation function**

Use the integration-contract helpers from Plan 1 (`compute_subsistence_threshold`, `compute_aggregate_outlook`). For the female labor participation and zone mean wage proxies, compute them inline using the existing `EconomicLedger` wage transactions:

```python
def _female_role_employment_fraction(zone, simulation) -> float:
    """Fraction of adult females in a wage-earning role in the zone.

    Proxy for female labor force participation. Reads the last tick of
    EconomicLedger wage transactions where the recipient is female.
    """
    from epocha.apps.agents.models import Agent
    from epocha.apps.economy.models import EconomicLedger
    from django.db.models import F

    tick = simulation.current_tick
    females = Agent.objects.filter(
        simulation=simulation, zone=zone, is_alive=True, gender=Agent.Gender.FEMALE,
    )
    total = females.count()
    if total == 0:
        return 0.0
    earning_ids = set(
        EconomicLedger.objects.filter(
            simulation=simulation, tick=tick, transaction_type="wage",
            to_agent__in=females,
        ).values_list("to_agent_id", flat=True)
    )
    return len(earning_ids) / total


def _zone_mean_wage(zone, simulation, lookback_ticks: int = 5) -> float:
    """Mean wage in the zone averaged over the last lookback_ticks ticks."""
    from epocha.apps.economy.models import EconomicLedger
    from django.db.models import Avg

    tick = simulation.current_tick
    agg = EconomicLedger.objects.filter(
        simulation=simulation,
        tick__gte=max(0, tick - lookback_ticks),
        transaction_type="wage",
        to_agent__zone=zone,
    ).aggregate(avg_wage=Avg("total_amount"))
    return float(agg["avg_wage"] or 0.0)


def becker_modulation(agent, coeffs: Mapping[str, float]) -> float:
    """Scale baseline ASFR by Becker (1991) economic signals.

    Design inspired by Becker (1991) and Jones & Tertilt (2008). All
    coefficients are provisional seed values; calibration deferred to
    Plan 4 using synthetic shock tests.

    Returns a scaling factor in [0.05, 3.0].
    """
    from epocha.apps.demography.context import (
        compute_subsistence_threshold,
        compute_aggregate_outlook,
    )

    subsistence = compute_subsistence_threshold(agent.simulation, agent.zone)
    wealth_signal = math.log(max(agent.wealth / max(subsistence, 1e-6), 0.1))
    zone_flp = _female_role_employment_fraction(agent.zone, agent.simulation)
    outlook = compute_aggregate_outlook(agent)

    raw = (
        float(coeffs["beta_0"])
        + float(coeffs["beta_1"]) * wealth_signal
        + float(coeffs["beta_2"]) * float(agent.education_level or 0.0)
        + float(coeffs["beta_3"]) * zone_flp
        + float(coeffs["beta_4"]) * outlook
    )
    return max(0.05, min(3.0, math.exp(raw)))
```

---

### Task 3: Malthusian soft ceiling

**Files:**
- Modify: `epocha/apps/demography/fertility.py`

- [ ] **Step 1: Append the Malthusian soft ceiling function**

```python
def malthusian_soft_ceiling(
    prob: float,
    current_pop: int,
    max_pop: int,
    floor_ratio: float = 0.1,
) -> float:
    """Operational soft-cap on fertility near carrying capacity.

    Engineering heuristic inspired by the Malthusian preventive check
    (Malthus 1798; Ricardo 1817) and by the modern formalization in
    Ashraf & Galor (2011). Not itself the formalization those authors
    propose (which is in continuous time on income per capita); this
    is a discrete tick-based scaling.

    - Free fertility below 80% of cap.
    - Linear ramp-down between 80% and 100% of cap.
    - Floor at floor_ratio * baseline above cap so populations never
      stop reproducing entirely (Lee 1987 empirical floor).
    """
    if max_pop <= 0:
        return prob
    if current_pop < 0.8 * max_pop:
        return prob
    if current_pop < max_pop:
        saturation = (current_pop - 0.8 * max_pop) / (0.2 * max_pop)
        ceiling_factor = max(0.0, 1.0 - saturation)
        return prob * ceiling_factor
    return prob * floor_ratio
```

---

### Task 4: Combined `tick_birth_probability`

**Files:**
- Modify: `epocha/apps/demography/fertility.py`

- [ ] **Step 1: Append the combined formula**

```python
def tick_birth_probability(
    mother,
    params_era: Mapping[str, object],
    current_pop: int,
    tick_duration_hours: float,
    demography_acceleration: float = 1.0,
) -> float:
    """Compute the per-tick birth probability for a female agent.

    Assumes the caller already filtered for living female agents in the
    fertile age window. Returns 0.0 when the mother is not in an active
    couple (if required by the era) or when avoid_conception is flagged
    for the current tick.

    Scales the annual rate to a single tick using the linear
    approximation for small annual rates (typical for fertility).
    """
    from epocha.apps.demography.models import AgentFertilityState
    from epocha.apps.demography.couple import is_in_active_couple

    fertility_cfg = params_era["fertility"]
    require_couple = bool(fertility_cfg.get("require_couple_for_birth", True))
    if require_couple and not is_in_active_couple(mother):
        return 0.0
    if is_avoid_conception_active_this_tick(mother):
        return 0.0

    hadwiger_params = fertility_cfg["hadwiger"]
    annual_asfr = hadwiger_asfr(_effective_age_in_years(
        mother, tick_duration_hours, demography_acceleration,
    ), hadwiger_params)
    if annual_asfr <= 0.0:
        return 0.0
    becker_factor = becker_modulation(mother, fertility_cfg["becker_coefficients"])
    effective = annual_asfr * becker_factor
    effective = malthusian_soft_ceiling(
        effective,
        current_pop,
        int(params_era.get("max_population", 500)),
        float(fertility_cfg.get("malthusian_floor_ratio", 0.1)),
    )
    dt = (tick_duration_hours / 8760.0) * demography_acceleration
    return effective * dt


def _effective_age_in_years(
    agent,
    tick_duration_hours: float,
    demography_acceleration: float,
) -> float:
    """Compute the agent's age in years using birth_tick as canonical source."""
    if agent.birth_tick is None:
        return float(agent.age or 0)
    current_tick = agent.simulation.current_tick if agent.simulation else 0
    ticks_per_year = 8760.0 / tick_duration_hours
    return (current_tick - agent.birth_tick) / max(1e-9, ticks_per_year) * demography_acceleration
```

---

### Task 5: AgentFertilityState helpers

**Files:**
- Modify: `epocha/apps/demography/fertility.py`

- [ ] **Step 1: Append flag helpers**

```python
def set_avoid_conception_flag(agent) -> None:
    """Record the agent's intent to avoid conception this tick.

    The fertility check at tick+1 reads this flag. Tick+1 settlement
    matches the property market pattern from Economy Spec 2.
    """
    from epocha.apps.demography.models import AgentFertilityState

    tick = agent.simulation.current_tick
    state, _ = AgentFertilityState.objects.get_or_create(agent=agent)
    state.avoid_conception_flag_tick = tick
    state.save(update_fields=["avoid_conception_flag_tick"])


def is_avoid_conception_active_this_tick(agent) -> bool:
    """True when the agent flagged avoid_conception at the previous tick.

    Reading the flag set at tick T - 1 during tick T makes avoid_conception
    a tick+1-settled action, consistent with property-market semantics.
    """
    from epocha.apps.demography.models import AgentFertilityState

    try:
        state = agent.fertility_state
    except AgentFertilityState.DoesNotExist:
        return False
    if state.avoid_conception_flag_tick is None:
        return False
    return state.avoid_conception_flag_tick == agent.simulation.current_tick - 1
```

---

### Task 6: Joint mortality-fertility resolution

**Files:**
- Modify: `epocha/apps/demography/fertility.py`

- [ ] **Step 1: Append the joint resolution function**

Childbirth mortality must be applied before the ordinary HP draw for the mother (spec §Sezione 1 fix C-1). This plan implements the helper; Plan 4's engine orchestrator will call it during the joint step.

```python
def resolve_childbirth_event(
    mother,
    params_era: Mapping[str, object],
    tick: int,
    rng,
) -> dict:
    """Resolve a pending birth alongside childbirth mortality.

    Returns a dict describing the outcome:
        {
            "mother_died": bool,
            "newborn_survived": bool,
            "death_cause": str | None,
        }

    Callers are responsible for persisting the state changes (mother's
    death, newborn creation) based on the outcome; this helper is a
    pure probabilistic resolver to keep the mortality path and the
    fertility path coupled but side-effect free.
    """
    mortality_cfg = params_era["mortality"]
    maternal_death_rate = float(
        mortality_cfg.get("maternal_mortality_rate_per_birth", 0.0)
    )
    neonatal_survival_when_mother_dies = float(
        mortality_cfg.get("neonatal_survival_when_mother_dies", 0.3)
    )

    mother_died = rng.random() < maternal_death_rate
    if mother_died:
        newborn_survived = rng.random() < neonatal_survival_when_mother_dies
        return {
            "mother_died": True,
            "newborn_survived": newborn_survived,
            "death_cause": "childbirth",
        }
    return {
        "mother_died": False,
        "newborn_survived": True,
        "death_cause": None,
    }
```

---

### Task 7: Fertility unit tests

**Files:**
- Create: `epocha/apps/demography/tests/test_fertility.py`

- [ ] **Step 1: Write the test file**

Cover:
- `hadwiger_asfr` returns 0 outside [12, 50]
- `hadwiger_asfr` peaks near R with typical pre_industrial params (verify by scanning ages 14..50 and checking that max falls at 24..28)
- `hadwiger_asfr` integral (by trapezoidal rule over fertile ages) is within 15% of the declared H (sanity of normalization)
- `becker_modulation` returns > 1 when wealth is high and < 1 when wealth is low (qualitative signs)
- `becker_modulation` returns 1.0 when all coefficients are zero
- `malthusian_soft_ceiling` returns input unchanged below 80% of cap
- `malthusian_soft_ceiling` returns floor_ratio * baseline above cap
- `tick_birth_probability` returns 0.0 when require_couple_for_birth and no couple exists
- `tick_birth_probability` returns 0.0 when avoid_conception flag is active at previous tick
- `set_avoid_conception_flag` persists the flag at the current tick
- `is_avoid_conception_active_this_tick` returns True when flag_tick == current_tick - 1
- `resolve_childbirth_event` with `maternal_mortality_rate_per_birth=1.0` deterministically returns mother_died=True
- `resolve_childbirth_event` with `maternal_mortality_rate_per_birth=0.0` deterministically returns mother_died=False
- `resolve_childbirth_event` with a seeded RNG is reproducible

Use `random.Random(seed)` for stochastic tests. Reuse the `sim_with_zone` fixture pattern from `test_models.py`; create couples explicitly by calling `Couple.objects.create` with `_ordered_pair` so the constraint is satisfied.

- [ ] **Step 2: Run tests**

Run: `docker compose -f docker-compose.local.yml exec web pytest epocha/apps/demography/tests/test_fertility.py --reuse-db -v --tb=short`

Expected: all tests pass.

- [ ] **Step 3: Commit**

```
feat(demography): add fertility module with Hadwiger x Becker x Malthusian

CHANGE: demography/fertility.py implements Hadwiger ASFR (canonical
normalized form), Becker modulation with existing integration contract
helpers, Malthusian soft ceiling, combined tick_birth_probability,
avoid_conception flag helpers (tick+1 settlement), and the joint
childbirth mortality resolver. Unit tests cover age window, peak,
integral normalization, sign of Becker factor, ceiling branches, and
childbirth outcome determinism under seeded RNG.
```

---

### Task 8: Couple module skeleton + `_ordered_pair` + homogamy scoring

**Files:**
- Create: `epocha/apps/demography/couple.py`

- [ ] **Step 1: Create the module**

```python
"""Couple formation infrastructure for demography: Gale-Shapley stable
matching, homogamy scoring (Kalmijn 1998), and runtime pair_bond /
separate intent handling with canonical ordering enforcement.

Sources:
- Gale, D. & Shapley, L.S. (1962). College admissions and the stability
  of marriage. American Mathematical Monthly 69(1), 9-15.
- Kalmijn, M. (1998). Intermarriage and homogamy. Annual Review of
  Sociology 24, 395-421.
- Goode, W.J. (1963). World Revolution and Family Patterns (arranged
  marriage patterns).
"""
from __future__ import annotations

from typing import Iterable

from django.db.models import Q


def _ordered_pair(agent_a, agent_b) -> tuple:
    """Return (lower_id_agent, higher_id_agent) for Couple canonical ordering.

    The Couple model enforces agent_a.id < agent_b.id via CheckConstraint.
    Every caller that creates a Couple must route both partners through
    this helper to avoid IntegrityError.
    """
    if agent_a.id is None or agent_b.id is None:
        raise ValueError(
            "Both agents must be saved (have a primary key) before forming a Couple"
        )
    if agent_a.id == agent_b.id:
        raise ValueError("Cannot form a Couple between an agent and itself")
    if agent_a.id < agent_b.id:
        return agent_a, agent_b
    return agent_b, agent_a


def is_in_active_couple(agent) -> bool:
    """True when the agent is one of the partners in an undissolved Couple."""
    from epocha.apps.demography.models import Couple

    return Couple.objects.filter(
        Q(agent_a=agent) | Q(agent_b=agent),
        dissolved_at_tick__isnull=True,
    ).exists()


def active_couple_for(agent):
    """Return the agent's active Couple (or None)."""
    from epocha.apps.demography.models import Couple

    return Couple.objects.filter(
        Q(agent_a=agent) | Q(agent_b=agent),
        dissolved_at_tick__isnull=True,
    ).first()


def homogamy_score(
    a, b, weights: dict, age_tolerance_years: float = 10.0,
) -> float:
    """Kalmijn-inspired compatibility score between two candidate partners.

    Components (all in [0, 1] before weighting):
    - class similarity: 1.0 if same social_class, 0.0 otherwise
    - education proximity: exp(-|e_a - e_b|)
    - age proximity: exp(-|age_a - age_b| / age_tolerance)
    - relationship: existing Relationship.sentiment in [-1, 1] mapped to [0, 1]

    Returns the weighted sum. Weights come from the era template and are
    design heuristics (see spec §Sezione 3).
    """
    import math
    same_class = 1.0 if a.social_class == b.social_class else 0.0
    edu_diff = abs(float(a.education_level or 0.0) - float(b.education_level or 0.0))
    edu_prox = math.exp(-edu_diff)
    age_diff = abs(float(a.age or 0) - float(b.age or 0))
    age_prox = math.exp(-age_diff / max(1e-9, age_tolerance_years))

    relationship_score = 0.5
    from epocha.apps.agents.models import Relationship

    rel = Relationship.objects.filter(
        Q(agent_from=a, agent_to=b) | Q(agent_from=b, agent_to=a)
    ).first()
    if rel is not None:
        relationship_score = (rel.sentiment + 1.0) / 2.0

    return (
        float(weights.get("w_class", 0.4)) * same_class
        + float(weights.get("w_edu", 0.25)) * edu_prox
        + float(weights.get("w_age", 0.20)) * age_prox
        + float(weights.get("w_relationship", 0.15)) * relationship_score
    )
```

---

### Task 9: Gale-Shapley stable matching library

**Files:**
- Modify: `epocha/apps/demography/couple.py`

- [ ] **Step 1: Append the Gale-Shapley algorithm**

```python
def stable_matching(
    proposers: list,
    respondents: list,
    score_fn,
) -> list[tuple]:
    """Gale-Shapley stable matching.

    Returns a list of (proposer, respondent) pairs. Both sides must rank
    each other via score_fn(proposer, respondent) -> float. Higher score
    is preferred.

    Complexity: O(n * m) total proposals for n proposers and m respondents.
    Gale & Shapley (1962) prove existence and stability.

    When len(proposers) != len(respondents), the smaller side is fully
    matched and the larger side has unmatched members.
    """
    # Build preference lists: each proposer sorts respondents by descending score
    proposer_prefs = {
        p: sorted(
            respondents,
            key=lambda r: score_fn(p, r),
            reverse=True,
        )
        for p in proposers
    }
    respondent_prefs = {
        r: {p: score_fn(p, r) for p in proposers}
        for r in respondents
    }

    free_proposers = list(proposers)
    engagements: dict = {}
    next_proposal_index: dict = {p: 0 for p in proposers}

    while free_proposers:
        p = free_proposers.pop(0)
        pref_list = proposer_prefs[p]
        if next_proposal_index[p] >= len(pref_list):
            continue
        r = pref_list[next_proposal_index[p]]
        next_proposal_index[p] += 1

        current = engagements.get(r)
        if current is None:
            engagements[r] = p
        elif respondent_prefs[r][p] > respondent_prefs[r][current]:
            engagements[r] = p
            free_proposers.append(current)
        else:
            free_proposers.append(p)

    return [(p, r) for r, p in engagements.items()]
```

---

### Task 10: `form_couple` helper

**Files:**
- Modify: `epocha/apps/demography/couple.py`

- [ ] **Step 1: Append couple-creation helper**

```python
def form_couple(
    agent_x,
    agent_y,
    formed_at_tick: int,
    couple_type: str = "monogamous",
) -> "Couple":
    """Create a Couple with canonical ordering enforced.

    Raises ValueError when the agents are the same or one of them is
    unsaved. Raises IntegrityError upstream if a duplicate active couple
    already exists between the pair (prevented by business logic in
    handlers, not by a unique constraint).
    """
    from epocha.apps.demography.models import Couple

    a, b = _ordered_pair(agent_x, agent_y)
    return Couple.objects.create(
        simulation=a.simulation,
        agent_a=a,
        agent_b=b,
        formed_at_tick=formed_at_tick,
        couple_type=couple_type,
    )
```

---

### Task 11: Pair-bond intent registration + tick+1 resolution

**Files:**
- Modify: `epocha/apps/demography/couple.py`

- [ ] **Step 1: Append intent registration + resolver**

The intent is stored in `DecisionLog` via the existing `apply_agent_action` pipeline; no new model is required. The resolver reads the previous tick's log and forms couples for mutually consenting pairs.

**DecisionLog actual schema** (verified in `epocha/apps/agents/models.py:217`): the model has ONLY `output_decision = TextField` containing the full JSON blob from the LLM. There are no separate `action`, `target`, or `target_payload` columns. The resolver parses the JSON via `json.loads()` and reads the `action` key from the decoded dict. This matches the pattern used by Economy Spec 2 Plan 3b for `hoard` / `buy_property` intents. Pre-filter via `output_decision__contains='"pair_bond"'` for a fast substring scan, then JSON-parse only the matches for correctness.

```python
def resolve_pair_bond_intents(simulation, tick: int, rng) -> list["Couple"]:
    """Process pair_bond intents from tick - 1, form couples where mutual.

    Reads DecisionLog.output_decision (TextField, JSON blob). Pre-filters
    with __contains then parses each match via json.loads to extract the
    action and payload. The resolver:
    1. Collects pair_bond DecisionLog entries from tick - 1.
    2. Builds a graph of directed intents (proposer -> target agent id).
    3. Forms a couple when both ends of an edge pair_bonded each other,
       or when the era template sets implicit_mutual_consent=True.
    4. Skips pairs where either agent is already in an active couple.
    5. Handles arranged marriage: when the payload contains for_child,
       the intent is reattributed to the named child toward the match.
    """
    import json
    from epocha.apps.agents.models import Agent, DecisionLog
    from epocha.apps.demography.template_loader import load_template

    sim_config = simulation.config or {}
    template_name = sim_config.get("demography_template", "pre_industrial_christian")
    template = load_template(template_name)
    couple_cfg = template["couple"]
    implicit_consent = bool(couple_cfg.get("implicit_mutual_consent", True))

    entries = DecisionLog.objects.filter(
        simulation=simulation,
        tick=tick - 1,
        output_decision__contains='"pair_bond"',
    ).select_related("agent")

    intents: dict[int, set[int]] = {}
    by_id: dict[int, Agent] = {}

    for entry in entries:
        try:
            decision = json.loads(entry.output_decision)
        except (json.JSONDecodeError, TypeError):
            continue
        if decision.get("action") != "pair_bond":
            continue
        proposer = entry.agent
        # Arranged marriage: extract child from payload and reattribute intent
        target_payload = decision.get("target")
        match_name: str | None = None
        if isinstance(target_payload, dict):
            child_name = target_payload.get("for_child")
            if child_name:
                child = Agent.objects.filter(
                    simulation=simulation, name=child_name, is_alive=True,
                ).first()
                if child is None:
                    continue
                proposer = child
            match_name = target_payload.get("match")
        elif isinstance(target_payload, str):
            match_name = target_payload
        if not match_name:
            continue
        match = Agent.objects.filter(
            simulation=simulation, name=match_name, is_alive=True,
        ).first()
        if match is None:
            continue
        by_id[proposer.id] = proposer
        intents.setdefault(proposer.id, set()).add(match.id)

    formed: list = []
    used: set[int] = set()
    for proposer_id, targets in intents.items():
        if proposer_id in used:
            continue
        proposer = by_id[proposer_id]
        if is_in_active_couple(proposer):
            continue
        for target_id in targets:
            if target_id in used:
                continue
            target = Agent.objects.filter(id=target_id, is_alive=True).first()
            if target is None or is_in_active_couple(target):
                continue
            mutual = proposer_id in intents.get(target_id, set())
            if not mutual and not implicit_consent:
                continue
            couple = form_couple(
                proposer,
                target,
                formed_at_tick=tick,
                couple_type=couple_cfg.get("default_type", "monogamous"),
            )
            formed.append(couple)
            used.add(proposer_id)
            used.add(target_id)
            break
    return formed
```

---

### Task 12: Separate intent registration + tick+1 resolution

**Files:**
- Modify: `epocha/apps/demography/couple.py`

- [ ] **Step 1: Append separate resolver**

```python
def resolve_separate_intents(simulation, tick: int) -> list["Couple"]:
    """Process separate intents from tick - 1, dissolve active couples.

    Reads DecisionLog.output_decision (JSON blob) with __contains pre-filter
    and json.loads verification, same pattern as resolve_pair_bond_intents.

    Skips entirely when the era template has divorce_enabled=False.
    Returns the list of dissolved Couples.
    """
    import json
    from epocha.apps.agents.models import DecisionLog
    from epocha.apps.demography.template_loader import load_template

    sim_config = simulation.config or {}
    template_name = sim_config.get("demography_template", "pre_industrial_christian")
    template = load_template(template_name)
    if not bool(template["couple"].get("divorce_enabled", False)):
        return []

    entries = DecisionLog.objects.filter(
        simulation=simulation,
        tick=tick - 1,
        output_decision__contains='"separate"',
    ).select_related("agent")

    dissolved: list = []
    for entry in entries:
        try:
            decision = json.loads(entry.output_decision)
        except (json.JSONDecodeError, TypeError):
            continue
        if decision.get("action") != "separate":
            continue
        couple = active_couple_for(entry.agent)
        if couple is None:
            continue
        couple.dissolved_at_tick = tick
        couple.dissolution_reason = "separate"
        couple.save(update_fields=["dissolved_at_tick", "dissolution_reason"])
        dissolved.append(couple)
    return dissolved
```

---

### Task 13: Automatic dissolution on partner death

**Files:**
- Modify: `epocha/apps/demography/couple.py`

- [ ] **Step 1: Append death-driven dissolution helper**

Plan 4 will wire this into the mortality step; Plan 3 may also call it from the inheritance path. Expose it as a pure utility.

```python
def dissolve_on_death(deceased_agent, tick: int) -> "Couple | None":
    """Dissolve any active Couple where the deceased is a partner.

    Captures the deceased's name into the appropriate *_name_snapshot
    field before nulling the FK, so the genealogical record survives
    the delete cascade.
    """
    couple = active_couple_for(deceased_agent)
    if couple is None:
        return None
    if couple.agent_a_id == deceased_agent.id:
        couple.agent_a_name_snapshot = deceased_agent.name
        couple.agent_a = None
    else:
        couple.agent_b_name_snapshot = deceased_agent.name
        couple.agent_b = None
    couple.dissolved_at_tick = tick
    couple.dissolution_reason = "death"
    couple.save(update_fields=[
        "agent_a", "agent_b",
        "agent_a_name_snapshot", "agent_b_name_snapshot",
        "dissolved_at_tick", "dissolution_reason",
    ])
    return couple
```

---

### Task 14: Arranged marriage payload parser

**Files:**
- Modify: `epocha/apps/demography/couple.py`

- [ ] **Step 1: No additional code needed — Task 11 already handles the extended payload**

The arranged marriage path reuses `pair_bond` with `{"for_child": ..., "match": ...}` in the target payload, as per the spec. The resolver in Task 11 already treats the parent's intent as originating from the named child. No new action name is introduced.

Mark this task as complete when the parser logic in Task 11 is verified by the dedicated test in Task 15.

---

### Task 15: Couple module unit tests

**Files:**
- Create: `epocha/apps/demography/tests/test_couple.py`

- [ ] **Step 1: Write test file**

Cover:
- `_ordered_pair` returns (lower_id, higher_id)
- `_ordered_pair` raises on same agent or unsaved agents
- `form_couple` creates a Couple satisfying the canonical ordering constraint
- `is_in_active_couple` / `active_couple_for` return correct values pre- and post-dissolution
- `homogamy_score` is higher for same-class, similar-age, similar-education pairs than for disparate pairs
- `stable_matching` with 3×3 produces 3 pairs, all stable (no rogue pair prefers each other over their current partner)
- `stable_matching` with asymmetric sizes (3 proposers, 2 respondents) matches exactly 2
- `resolve_pair_bond_intents` forms a couple when both agents pair_bonded each other
- `resolve_pair_bond_intents` forms a couple with implicit_mutual_consent when only one side proposed
- `resolve_pair_bond_intents` skips when either party is already in a couple
- `resolve_pair_bond_intents` handles the arranged marriage payload (parent proposes for child)
- `resolve_separate_intents` dissolves when divorce_enabled=True, is a no-op when False
- `dissolve_on_death` captures the name snapshot and nulls the FK

Use the `sim_with_zone` fixture pattern. Create agents in a specific order to control their IDs. Use `DecisionLog.objects.create` directly to simulate intents (Task 11 reads from the log).

- [ ] **Step 2: Run tests**

Run: `docker compose -f docker-compose.local.yml exec web pytest epocha/apps/demography/tests/test_couple.py --reuse-db -v --tb=short`

Expected: all tests pass.

- [ ] **Step 3: Commit**

```
feat(demography): add couple module with Gale-Shapley + runtime handlers

CHANGE: demography/couple.py implements canonical-ordering pair
helper, Kalmijn-inspired homogamy score, Gale-Shapley stable matching
library, form_couple creator, runtime pair_bond / separate intent
resolvers with tick+1 settlement, arranged-marriage payload parser
reusing pair_bond, and death-driven dissolution with name snapshot.
Unit tests cover all paths including asymmetric matching and
arranged-marriage flow.
```

---

### Task 16: Extend decision system prompt

**Files:**
- Modify: `epocha/apps/agents/decision.py`

- [ ] **Step 1: Add three actions to the allowed set**

Find the existing action vocabulary (whether it's a constant, an enum, or embedded in the system prompt string) and add `pair_bond`, `separate`, `avoid_conception`. Document each briefly so the LLM understands the semantics.

This task has no standalone test; it is covered by Task 21.

- [ ] **Step 2: Verify the prompt builds without regression**

Run: `docker compose -f docker-compose.local.yml exec web pytest epocha/apps/agents/ --reuse-db -q`

Expected: zero regressions.

---

### Task 17: Dynamic era filter

**Files:**
- Modify: `epocha/apps/agents/decision.py`

- [ ] **Step 1: Filter action list by era template**

At prompt build time, remove actions that are unavailable in the current era:
- `separate` is removed when `couple.divorce_enabled == false`
- `avoid_conception` is removed when `fertility_agency == "biological"`
- `pair_bond` is unconditionally present

Read the era template via `demography.template_loader.load_template(name)` using the simulation's configured template name (fallback to `pre_industrial_christian` when the simulation has no demography config, to preserve behavior for Economy-only simulations).

---

### Task 18: Action handler dispatch

**Files:**
- Modify: `epocha/apps/simulation/engine.py`

- [ ] **Step 1: Dispatch the three actions**

**DecisionLog contract**: `DecisionLog.output_decision` is a TextField containing `json.dumps(action_dict)` where `action_dict` has the shape `{"action": "...", "target": ..., "reason": ...}`. The existing `apply_agent_action` in `simulation/engine.py` already writes the log entry with the LLM's decision; per-action handlers run AFTER the log is written and perform side effects specific to the action. For `pair_bond` and `separate` the side effect is *nothing at this tick* — the resolvers in Tasks 11 and 12 read the log at tick + 1. For `avoid_conception` the side effect is immediate: set the fertility-state flag.

Implementation:
- `pair_bond`: no handler body beyond the existing `DecisionLog` write. Task 11 resolver picks up the intent at tick + 1 by scanning `output_decision__contains='"pair_bond"'` and parsing JSON to extract the `target` payload.
- `separate`: same pattern. Task 12 resolver at tick + 1.
- `avoid_conception`: import and call `demography.fertility.set_avoid_conception_flag(agent)`. Guard with an era check — if the era template has `fertility_agency != "planned"`, log a warning and skip the flag mutation.

The target payload for arranged marriage is an object `{"for_child": "<child_name>", "match": "<other_name>"}` rather than a plain string. The LLM is instructed to emit this shape via the system-prompt extension in Task 16; the resolver in Task 11 handles both shapes (string target vs object target with `for_child`).

---

### Task 19: Mood delta and emotional weight entries

**Files:**
- Modify: `epocha/apps/simulation/engine.py`

- [ ] **Step 1: Add calibration entries**

Following spec §Sezione 8 table:

```python
_MOOD_DELTAS["pair_bond"] = 0.10
_MOOD_DELTAS["separate"] = -0.15
_MOOD_DELTAS["avoid_conception"] = -0.01

_EMOTIONAL_WEIGHTS["pair_bond"] = 0.7
_EMOTIONAL_WEIGHTS["separate"] = 0.8
_EMOTIONAL_WEIGHTS["avoid_conception"] = 0.2
```

Match the exact dict names used in `simulation/engine.py`; the spec values are Holmes & Rahe (1967) calibrated.

---

### Task 20: Dashboard verb entries

**Files:**
- Modify: `epocha/apps/dashboard/formatters.py`

- [ ] **Step 1: Add verb entries**

```python
_ACTION_VERBS.update({
    "pair_bond": "formed a couple with",
    "separate": "separated from",
    "avoid_conception": "chose to delay having children",
})
```

---

### Task 21: Decision + handlers unit tests

**Files:**
- Create: `epocha/apps/demography/tests/test_decision_actions.py`

- [ ] **Step 1: Write tests**

Cover:
- Prompt filter removes `separate` when divorce_enabled=false
- Prompt filter keeps `separate` when divorce_enabled=true
- Prompt filter removes `avoid_conception` when fertility_agency=biological
- pair_bond handler writes a DecisionLog entry with action="pair_bond"
- separate handler writes a DecisionLog entry with action="separate"
- avoid_conception handler populates AgentFertilityState.avoid_conception_flag_tick

- [ ] **Step 2: Run tests**

Run: `docker compose -f docker-compose.local.yml exec web pytest epocha/apps/demography/tests/test_decision_actions.py --reuse-db -v --tb=short`

- [ ] **Step 3: Commit**

```
feat(demography): wire pair_bond / separate / avoid_conception actions

CHANGE: Extend agents/decision.py system prompt with three new actions
filtered by era template. simulation/engine.py dispatches each action
to the right demography helper (DecisionLog for pair_bond / separate,
AgentFertilityState.set_avoid_conception_flag for avoid_conception).
Mood deltas and emotional weights calibrated per spec Section 8
(Holmes & Rahe 1967). Dashboard verb entries added.
```

---

### Task 22: End-to-end integration test

**Files:**
- Create: `epocha/apps/demography/tests/test_integration_plan2.py`

- [ ] **Step 1: Write the integration test (deterministic)**

The test asserts state transitions, NOT stochastic outcomes. It does not actually sample births — it asserts that `tick_birth_probability` is zero when expected (avoid_conception active, no couple, or outside fertile window) and non-zero otherwise. This keeps the test deterministic and independent of the RNG stream.

Scenario (using `demography_template="modern_democracy"` which has `fertility_agency="planned"` and `divorce_enabled=true`):

1. Create the simulation + world + zone. Populate `ZoneEconomy`, `GoodCategory` (at least one essential), and a `Government` so `compute_subsistence_threshold` and `compute_aggregate_outlook` return finite values.
2. Create four adult agents with deterministic creation order so their PKs are monotonic: female A, female B, male C, male D. All in the fertile age window; set `education_level`, `wealth`, `mood` to plausible values.
3. Create `DecisionLog` entries at tick T simulating `apply_agent_action` output — for A: `output_decision=json.dumps({"action": "pair_bond", "target": "C", "reason": "..."})`; mirror entry from C toward A for explicit mutual consent.
4. Advance `simulation.current_tick = T + 1` and call `resolve_pair_bond_intents(simulation, tick=T+1, rng=...)`. Assert exactly one Couple formed with `(A, C)` (or `(C, A)` after canonical ordering).
5. Assert `is_in_active_couple(A) is True` and `is_in_active_couple(C) is True`.
6. At tick `T + 2`, call `set_avoid_conception_flag(A)` (simulating the action handler). Assert `AgentFertilityState` row for A has `avoid_conception_flag_tick == T + 2`.
7. Advance `simulation.current_tick = T + 3`. Call `tick_birth_probability(A, template, ...)`. Assert return is `0.0` because `is_avoid_conception_active_this_tick(A)` is True (`flag_tick == T+2 == current_tick - 1`).
8. Advance `simulation.current_tick = T + 4`. Assert `tick_birth_probability(A, template, ...) > 0.0` — the flag is now stale (`flag_tick != current_tick - 1`), A is in an active couple, and A is in the fertile window.
9. Create `DecisionLog` entry at tick `T + 4` for A: `output_decision=json.dumps({"action": "separate", ...})`. Advance to tick `T + 5` and call `resolve_separate_intents(simulation, tick=T+5)`. Assert the Couple is dissolved (`dissolved_at_tick == T+5`, `dissolution_reason == "separate"`).
10. Assert `is_in_active_couple(A) is False` and that A can be paired again by a subsequent `resolve_pair_bond_intents` call.

This flow exercises every moving piece of Plan 2 without relying on any single probabilistic draw to go a specific way. All stochastic logic (Becker modulation, Malthusian ceiling) is exercised indirectly through the `tick_birth_probability > 0` assertion which is a property, not an event.

- [ ] **Step 2: Run the test**

Run: `docker compose -f docker-compose.local.yml exec web pytest epocha/apps/demography/tests/test_integration_plan2.py --reuse-db -v --tb=short`

- [ ] **Step 3: Commit**

```
test(demography): add end-to-end Plan 2 integration test

CHANGE: Covers a full pair_bond -> avoid_conception -> separate cycle
with tick+1 settlement verified at each transition. Uses the
modern_democracy template to exercise the divorce_enabled and
fertility_agency=planned branches.
```

---

### Task 23: Plan 2 closing

**Files:** (no new files; verification and PR)

- [ ] **Step 1: Full suite**

Run: `docker compose -f docker-compose.local.yml exec web pytest epocha/ --reuse-db -q --tb=short`

Expected: all tests pass. Target: >= 760 / 0.

- [ ] **Step 2: Migrations clean**

Run: `docker compose -f docker-compose.local.yml exec web python manage.py migrate --plan | tail -5`

Expected: no pending migrations.

- [ ] **Step 3: Push and create PR**

```
git push -u origin feature/demography-2-fertility-couple
gh pr create --base develop --title "Demography Plan 2: fertility + couple + LLM actions" --body "..."
```

- [ ] **Step 4: Dispatch adversarial code audit and iterate to CONVERGED**

Use the `critical-analyzer` subagent with hostile mandate. Fix findings, re-audit. Same loop pattern as Plan 1.

- [ ] **Step 5: Merge --no-ff to develop after CONVERGED + human validation**

- [ ] **Step 6: Sync memory backup**

Add `project_demography_plan2_complete.md` to the project memory and `docs/memory-backup/`.

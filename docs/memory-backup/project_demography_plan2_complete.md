---
name: demography-plan2-complete
description: Demography Plan 2 (Fertility + Couple + LLM Actions) completata e mergiata in develop il 2026-04-19
type: project
originSessionId: f9bc7a55-71c4-45ed-9602-f5e328a6175e
---
# Demography Plan 2 -- COMPLETATA

**Data merge**: 2026-04-19, commit `715d5fa` su `develop`.
**PR**: https://github.com/mauriziomocci/epocha/pull/3 (merged)
**Spec**: `docs/superpowers/specs/2026-04-18-demography-design-it.md`
**Plan**: `docs/superpowers/plans/2026-04-19-demography-2-fertility-couple.md` (23 task, tutti flaggati)

## Deliverable consegnato

- `fertility.py`: Hadwiger ASFR canonical normalizzato, Becker modulation (integration contracts Plan 1), Malthusian soft ceiling, `tick_birth_probability`, AgentFertilityState helpers con tick+1 settlement, joint childbirth mortality resolver (spec fix C-1)
- `couple.py`: `_ordered_pair` enforcement CheckConstraint Plan 1, Kalmijn homogamy score, Gale-Shapley library, `form_couple`, `resolve_pair_bond_intents` con two-pass arranged marriage Goode 1963, `resolve_separate_intents`, `dissolve_on_death` con name snapshot
- 3 nuove LLM actions (`pair_bond`, `separate`, `avoid_conception`) con era-filter dinamico, handler in simulation/engine, mood/emotional weight spec Section 8 (Holmes & Rahe 1967), dashboard verbs
- UniqueConstraint `unique_active_couple` su Couple (fix audit B2-01): max una coppia attiva per pair
- 80 test nuovi (26 fertility + 23 couple + 9 decision + 1 integration + minor refactor)

## Spec/templates bug fix (critical, globale)

Durante Task 1 Sonnet ha escalato correttamente: valore Hadwiger T parameter off-by-factor-10 in spec EN + IT e 5 template JSON. Fix applicato:
- pre_industrial_christian/islamic: T 0.35 → 3.5
- industrial: 0.38 → 3.8
- modern_democracy: 0.42 → 4.2
- sci_fi: 0.40 → 4.0

Verificato matematicamente: peak f(26) con T=3.5 H=5 = 0.380; integrale [12,50] = 4.999 ≈ H. Sfuggito a 4 round audit Plan 1 perche` auditor non aveva fatto integrazione numerica.

## Fase 6 canonical workflow

- Adversarial code audit round 1: CONDITIONAL_ACCEPT, 6 MAJOR + 7 MINOR, 0 BLOCKER
- Fix commit `be63bb3`:
  - B2-01 UniqueConstraint active couple + transaction.atomic
  - B2-02 logger.warning su JSON malformato
  - B2-03 sorted iteration per determinismo
  - B2-04 explicit current_tick parameter (fix FK cache staleness in Celery chord)
  - B2-05 FileNotFoundError template: log e skip (no silent planned fallback)
  - B2-06 two-pass intent: arranged marriage NON override direct intent child
  - B2-07 Becker coefficients identical across templates: DEFERRED_DOCUMENTED a Plan 4 calibration
- Re-audit round 2: CONVERGED, zero new issues
- Merge --no-ff a develop commit `715d5fa`

## Debt tracked per Plan 3/4

- B2-07: Becker coefficients calibration (Plan 4)
- B2-08 math.exp overflow clamp in becker_modulation
- B2-09 stable_matching empty input tests
- B2-10 _female_role_employment_fraction N+1 performance cache (Plan 4)
- B2-11 unused Iterable import cleanup
- B2-12 mock.patch preferito a importlib.reload in test_fertility
- B2-13 type hint precision su stable_matching
- B2-14 form_couple docstring update (ora accurata post B2-01)
- Follow-up coverage: test "child direct intent sopprime arranged" (gap post-B2-06)
- Follow-up opzionale: set_avoid_conception_flag accetta current_tick esplicito

## Prossimi step obbligati

**PRIMA di Plan 3** (richiesta utente 2026-04-19):
1. **Riscrivere README.md + README.it.md** (entrambi molto obsoleti per user feedback)
2. **Creare whitepaper bilingue**: `docs/whitepaper/epocha-whitepaper.md` (EN) + `docs/whitepaper/epocha-whitepaper.it.md` (IT) linkati dai rispettivi README, publication-grade con struttura paper scientifico (Abstract/Methods/Validation/References/Appendices/reproducibility notes), living documents da sincronizzare sempre col codice merged

Vedi `feedback_readme_bilingual_maintenance`, `feedback_whitepaper_bilingual`, `project_readme_rewrite_todo` per le regole.

**DOPO follow-up doc**: Plan 3 (Inheritance + Migration) parte da `develop` al commit `715d5fa`.

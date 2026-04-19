---
name: demography-plan1-complete
description: Demography Plan 1 (Foundations + Mortality) completata e mergiata in develop il 2026-04-19
type: project
originSessionId: f9bc7a55-71c4-45ed-9602-f5e328a6175e
---
# Demography Plan 1 -- COMPLETATA

**Data merge**: 2026-04-19, commit `41bf508` su `develop`.
**Spec**: `docs/superpowers/specs/2026-04-18-demography-design-it.md` (italiano, CONVERGED)
**Plan**: `docs/superpowers/plans/2026-04-18-demography-1-foundations.md` (25 task, tutti flaggati)

## Deliverable consegnato

- Nuova app `epocha.apps.demography` con 4 modelli: Couple, DemographyEvent, PopulationSnapshot, AgentFertilityState
- Agent extensions: `birth_tick` (BigIntegerField signed, canonical age source), `death_tick`, `death_cause`, `other_parent_agent`, `caretaker_agent`
- Integration contracts helpers:
  - `world.government.add_to_treasury()` centralizza accumulo treasury
  - `economy.market.SUBSISTENCE_NEED_PER_AGENT` costante condivisa
  - `demography.context.compute_subsistence_threshold()` derivato per-zone
  - `demography.context.compute_aggregate_outlook()` scalare [-1,1] da mood+banking+stability
- RNG seeded per-sottosistema (`demography.rng.get_seeded_rng(sim, tick, phase)`)
- Template loader con schema validation + 5 JSON d'era (pre_industrial_christian, pre_industrial_islamic, industrial, modern_democracy, sci_fi)
- Mortality module Heligman-Pollard (1980): annual + tick scaled (linear for q<0.1, geometric for q>=0.1), cause attribution, scipy.optimize.curve_fit fitting infrastructure
- Couple CheckConstraint canonical ordering (agent_a.id < agent_b.id)
- 31 test nuovi, full suite 739/0, zero regressioni

## Fase 6 canonical workflow

- Adversarial code audit round 1 → 8 MAJOR findings
- Fix commit `d813627`: 6 RESOLVED + 2 verified FALSE_POSITIVE
- Re-audit round 2 → CONVERGED
- Merge --no-ff a develop

## Bug fix discovered durante implementazione Sonnet

Durante i task Sonnet ha rilevato e corretto 4 bug nei code block della spec:
1. `ZoneEconomy` non ha campo `simulation` (OneToOne su Zone)
2. `gov.stability or 0.5` tratta 0.0 come falsy
3. `fit_heligman_pollard` con all-zero input converge a valori senza senso (aggiunto guard)
4. `test_geometric_branch_half_year` redesign con custom params

## Debt tracked per Plan 2+

- A-5: RNG collision su simulation.id/seed entrambi None → alzare ValueError
- A-6: birth_tick backfill O(N) save → bulk update per simulazione
- A-7: `noop_reverse` migration → reset NULL esplicito
- B-5: HP fit bounds justification → citare HP 1980 tables in Plan 4 calibration
- E-1..E-6: test rigour (validation storica, fit con initial_guess default, demography_acceleration coverage, fallback base_price test)
- G-4: template `acceleration` key dead in Plan 1 (wire-up in Plan 4)
- G-5: `sexual_orientation_distribution` non in REQUIRED_TOP_LEVEL_KEYS

## Spec errata da correggere nella spec italiana (separatamente)

Durante l'implementazione sono emerse alcune imprecisioni nei code block della spec:
- `ZoneEconomy.objects.get(zone=zone, simulation=simulation)` → `ZoneEconomy.objects.get(zone=zone)` (OneToOne su Zone)
- `float(gov.stability or 0.5)` → null guard impossibile, `default=0.5` non nullable
- `fit_heligman_pollard` non ha guard su input all-zero
Tutte applicate nel codice ma la spec italiana nei suoi code block ha ancora le versioni errate. Da correggere nella spec in un commit futuro dedicato.

## Prossimo step

**Plan 2**: Fertility + Couple formation + LLM actions. Attese ~22 task. Dipende da Plan 1 mergiato. Parte da `develop` al commit 41bf508 con branch `feature/demography-2-fertility-couple`.

---
name: behavioral-integration-progress
description: Spec 2 Part 3 COMPLETATA al 2026-04-17: Plan 3a+3b+3c tutti implementati, merged in develop
type: project
originSessionId: f9bc7a55-71c4-45ed-9602-f5e328a6175e
---
# Economy Behavioral Integration -- COMPLETATA

Spec 2 Part 3 chiusa il 2026-04-17.

**Branch**: `feature/economy-behavioral-integration` mergiato in `develop` con `--no-ff`.
**Spec**: `docs/superpowers/specs/2026-04-15-economy-behavioral-integration-design.md`

## Plan 3a -- Foundations: COMPLETATO
Extended context, hoard link, banking init, deposit recalc, banking concern, dead agent loans, double-pledge protection, nuovi transaction types.

## Plan 3b -- Property Market + Actions: COMPLETATO
Gordon valuation, process_property_listings (tick+1 matching), process_expropriation, borrow/sell_property/buy_property, expropriation hook su government transitions e coup, dashboard verbs, credit.py transaction types aggiornati.

## Plan 3c -- Integration test: COMPLETATO
File `epocha/apps/economy/tests/test_integration_behavioral.py`: 7 test end-to-end verificano expectations update, hoard reduces supply, borrow issues loan, property cycle transfers ownership, deposits track cash, banking concern broadcast, full scenario Minsky cycle.

## Stato test
252 test economy passano. 4 fallimenti project-wide sono pre-esistenti e infrastrutturali (redis name resolution in test_tasks/test_consumers), verificati non causati dalle nostre modifiche.

## Prossimo step della roadmap
**Demografia (Fase 2)**. Ciclo completo: brainstorming -> three-step design -> spec con FAQ -> adversarial audit -> plan -> implementation -> re-audit -> CONVERGED.

Scope: Lotka 1925, Lee-Carter 1992, eredita' tratti, migrazione push-pull, fertility Becker 1991, ABM Billari 2006.

---
name: audit-repass-batch-2026-04-12-pending
description: HIGH-PRIORITY follow-up after Demography Plan 3 -- re-audit pass on the 8 modules audited in batch 2026-04-12 with remediation done but no Round 2 verification
type: project
originSessionId: b165274d-a708-4e8c-abed-b28a018c163f
---
# Audit re-pass debt -- batch 2026-04-12

## Stato

Nel 2026-04-12 fu eseguito un adversarial scientific audit su 8+ moduli implementati pre-canonical-workflow. L'audit produsse 14 INCORRECT + 19 UNJUSTIFIED + 6 INCONSISTENT + 12 MISSING findings.

Tre commit di remediation seguirono:
- `17f046a` fix(science): correct false citations and unjustified parameters in reputation, distortion, economy, movement
- `7744016` fix(science): correct false citations in belief, government, stratification + fix corruption bug and deterministic coup
- `951a606` fix(science): complete scientific audit remediation across all modules

**Nessun Round 2 audit fu eseguito.** Per definizione del project workflow (CLAUDE.md "Mandatory convergence loop"), questi moduli sono in stato "Round 1 done, remediation done, Round 2 pending" -- NON CONVERGED.

Audit log originale: `docs/scientific-audit-2026-04-12.md`.

## Moduli interessati

| Modulo | Path | Status whitepaper | Promozione attesa |
|---|---|---|---|
| Reputation | `epocha/apps/agents/reputation.py` | cap. 8 (audit pending) | cap. 4 dopo CONVERGED |
| Distortion (rumor) | `epocha/apps/agents/distortion.py` | cap. 8 cluster rumor | cap. 4 dopo CONVERGED |
| Information Flow | `epocha/apps/agents/information_flow.py` | cap. 8 cluster rumor | cap. 4 dopo CONVERGED |
| Belief Filter | `epocha/apps/agents/belief.py` | cap. 8 cluster rumor | cap. 4 dopo CONVERGED |
| Government | `epocha/apps/world/government.py`, `government_types.py` | cap. 8 cluster political | cap. 4 dopo CONVERGED |
| Stratification | `epocha/apps/world/stratification.py` | cap. 8 cluster political | cap. 4 dopo CONVERGED |
| Movement | `epocha/apps/agents/movement.py` | cap. 8 | cap. 4 dopo CONVERGED |
| Factions | `epocha/apps/agents/factions.py` | cap. 8 | cap. 4 dopo CONVERGED |

## Priorita' e collocazione nel roadmap

**Subito dopo Demography Plan 3** (Inheritance + Migration), prima di Plan 4 o di nuovi sottosistemi. Motivo: il debt aumenta con ogni nuova feature che si appoggia sui moduli non re-auditati.

## Procedura raccomandata

Per ogni modulo (uno per branch dedicato `audit-repass/<modulo>`):
1. Re-leggere findings originali in `docs/scientific-audit-2026-04-12.md`
2. Verificare ogni finding contro il codice corrente (potrebbe essere gia' risolto o regredito)
3. Dispatch `critical-analyzer` Round 2 con mandato "verify Round 1 resolutions and hunt for new issues"
4. Loop fino a CONVERGED
5. Aggiornare il capitolo del whitepaper: promuovere il modulo da cap. 8 a `4.x` con sub-section dedicata
6. Aggiornare README.md + README.it.md status table
7. Merge a develop

## Why

- Il whitepaper bilingue dichiara questi moduli "audit pending" in cap. 8: e' onesto ma e' un debito tracciato.
- Senza re-audit, ogni claim su questi moduli e' indifendibile in peer review.
- Il pattern Demography (Round 4 to converge) suggerisce 2-4 round per modulo. Lavoro stimato: 1-2 settimane per modulo, 8 moduli totali. Si puo' parallelizzare a coppie (rumor cluster, political cluster).

## How to apply

Quando l'utente chiede "cosa e' rimasto da fare prima di feature X", segnala questo debt come priorita' alta dopo Plan 3. Quando un modulo sta per essere modificato, suggerisci il re-audit nello stesso branch (un colpo, due benefici).

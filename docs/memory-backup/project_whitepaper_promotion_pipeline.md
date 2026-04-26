---
name: whitepaper-promotion-pipeline
description: Procedura standard per promuovere un modulo da cap. 8 (Designed Subsystems) a cap. 4 (Methods) del whitepaper dopo audit CONVERGED
type: project
originSessionId: b165274d-a708-4e8c-abed-b28a018c163f
---
# Whitepaper promotion pipeline -- da cap. 8 a cap. 4

## Quando si attiva

Un modulo descritto in cap. 8 del whitepaper (status: "audit pending" o "implemented, audit pending") raggiunge un adversarial scientific audit CONVERGED.

Esempi attesi: ogni modulo del batch `project_audit_repass_batch_2026_04_12_pending.md` man mano che viene re-auditato. Anche moduli nuovi che nascono direttamente con audit (es. Demography Plan 3 Inheritance/Migration una volta auditata).

## Procedura

1. **Verifica pre-condizioni**
   - Audit CONVERGED documentato nella spec del modulo (es. "Round 4 Convergence Verdict: CONVERGED" come per Demography)
   - Codice implementato e mergiato in develop
   - Test passing al 100%

2. **Branch dedicato**: `whitepaper-promote/<modulo>` da develop

3. **Aggiornare whitepaper EN** (`docs/whitepaper/epocha-whitepaper.md`)
   - Rimuovere il paragrafo del modulo da cap. 8
   - Aggiungere sotto-sezione `4.x.y` con schema canonico: Background → Model → Equations → Parameters → Algorithm → Simplifications → Status header (`> Status: implemented as of commit <hash>, spec audit CONVERGED <date>`)
   - Aggiornare cap. 6 Calibration con la parameter table del modulo
   - Aggiornare cap. 7 Validation Methodology con dataset target e metriche del modulo
   - Aggiornare cap. 13 References con citazioni primary-source verificate

4. **Aggiornare whitepaper IT** (`docs/whitepaper/epocha-whitepaper.it.md`) -- traduzione 1:1

5. **Aggiornare README.md + README.it.md** -- spostare il modulo nella status table da "audited: pending" a "audited: yes (CONVERGED)"

6. **Aggiornare il mapping in `feedback_whitepaper_doc_sync.md`** -- aggiungere la nuova entry

7. **Aggiornare CHANGELOG.md** (se esiste) o aggiungere entry nelle Revision history del whitepaper

8. **Adversarial audit pass su nuova sotto-sezione**: dispatch `critical-analyzer` con mandato "verify the new chapter cites only verified primary sources, math matches code"

9. **Merge a develop** con `--no-ff`

10. **Sync memoria backup** (`docs/memory-backup/`)

## Why

La promozione e' il segnale che un modulo ha raggiunto maturita' scientifica documentabile. La procedura standardizzata evita che ogni promozione reinventi i passi e dimentichi qualche aggiornamento (es. README status table).

Il whitepaper cresce per tappe verifiable invece che per ondate o ad-hoc. Ogni release del whitepaper diventa una "milestone scientifica" tracciabile.

## How to apply

Quando l'utente segnala "audit X CONVERGED" o "Plan Y mergiato con audit", offrire spontaneamente di aprire il branch `whitepaper-promote/...` e seguire questa procedura.

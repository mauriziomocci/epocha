---
name: audit-repass-batch-2026-04-12-pending
description: F-CAMPAIGN chiusa 6/6 (2026-07-15). Economy base layer CONVERGED round 12 (2026-07-16) e promosso a paragraph 4.8. Questo file traccia ora SOLO il residuo -- paragraph 8.1 Knowledge Graph, audit pendente. E' l'ULTIMO modulo in paragraph 8.
type: project
originSessionId: b165274d-a708-4e8c-abed-b28a018c163f
---
# Audit re-pass -- batch 2026-04-12: campagna chiusa, residuo tracciato

## Perche' il nome file resta "pending"

Il whitepaper bilingue cita questo file per nome in piu' punti (paragrafi 10 Discussion, 11 Known Limitations, 12 Conclusions) come tracker del Round 2 residuo. Il nome storico e' quindi mantenuto anche se la campagna F-CAMPAIGN e' chiusa: il contenuto e' stato riscritto (2026-07-15) e ora traccia solo il residuo fuori-batch che il whitepaper gli attribuisce.

## Stato campagna F-CAMPAIGN: CHIUSA 6/6

Piano campagna: `docs/superpowers/plans/2026-05-12-audit-repass-campaign.md` (legacy pre-Spec-Kit). Retrospettiva: [[project_audit_repass_2026_04_12_completed]].

| # | Branch | Esito | PR | Merge SHA |
|---|--------|-------|----|-----------|
| 1 | Reputation | CONVERGED Round 2 (2026-05-12), promosso a paragraph 4.3 | PR#5 | c196281 |
| 2 | Rumor cluster (info flow, distortion, belief, affinity) | CONVERGED Round 2 (2026-05-16), promosso a paragraph 4.4 | PR#6 | a0ea075 |
| 3 | Political cluster (government, gov_types, institutions, stratification, election) | CONVERGED Round 2 (2026-05-16), promosso a paragraph 4.5 | PR#7 | dfeb709 |
| 4 | Movement | CONVERGED Round 2 (2026-05-16), promosso a paragraph 4.6 | PR#8 | c543c10 |
| 5 | Factions | CONVERGED Round 2 (2026-05-16), promosso a paragraph 4.7 | PR#9 | 5406b95 |
| 6 | World economy deprecation (path B: marker, fallback invariato) | Chiuso via Spec Kit `specs/20260715-094457-world-economy-deprecation/` | PR#12 | 4341a7a |

## Residuo tracciato da questo file (fuori scope campagna)

**Aggiornamento 2026-07-17: resta UN SOLO modulo in paragraph 8.**

| Modulo | Whitepaper | Stato |
|--------|-----------|-------|
| Knowledge Graph | paragraph 8.1 | Audit PENDENTE -- unico residuo; findings originali in `docs/scientific-audit-2026-04-12.md`. E' l'item HIGH PRIORITY della roadmap paragraph 9. Codice in `epocha/apps/knowledge/` (19 moduli), **zero chiamate dal tick engine** (verificato 2026-07-17). |
| ~~Economy base layer~~ | ~~paragraph 8.2~~ -> **paragraph 4.8** | **CHIUSO**: CONVERGED round 12 (2026-07-16), 7/7 moduli, unresolved=0, money=BOUNDED_INJECTION_ONLY, goods=YES, tax=YES, deterministic=YES. Promosso a paragraph 4.8 sul branch `20260715-132752-economy-base-layer-audit` (commit promozione `d353de2`). Suite 911 verdi. |

Gate: la promozione da paragraph 8 a paragraph 4.x, l'ingresso dei parametri nelle tabelle di calibrazione paragraph 6 e l'ingresso nella campagna di validazione paragraph 7 dipendono dall'audit CONVERGED del modulo (procedura in [[project_whitepaper_promotion_pipeline]]).

Nota sul numero di round: l'economy base layer NON era nel batch 2026-04-12, quindi ha fatto il suo PRIMO audit (non un Round 2) e ha richiesto 12 round di convergenza -- molto piu' dei 2 round tipici dei moduli della campagna, perche' l'implementazione pre-audit aveva difetti strutturali di conservazione (iniettava piu' del doppio del valore prodotto come cassa nuova, fabbricava beni al settlement, M scollegata dalla cassa circolante).

## Storia (sintesi)

Nel 2026-04-12 un adversarial scientific audit su 8+ moduli pre-canonical-workflow produsse 14 INCORRECT + 19 UNJUSTIFIED + 6 INCONSISTENT + 12 MISSING findings. Remediation nei commit `17f046a`, `7744016`, `951a606` senza Round 2 di verifica. La campagna F-CAMPAIGN (2026-05-12 -> 2026-07-15) ha eseguito il Round 2 su tutti i moduli in scope fino a CONVERGED e li ha promossi a paragraph 4; il modulo legacy `world/economy.py` e' stato deprecato invece che re-auditato perche' superato dal package economy auditato.

## Follow-up correlati

- Factions Round 3 hardening: 5 finding behavioral deferred a chiusura factions (NEW-1, NEW-7, NEW-8, NEW-10, NEW-12/13) -- work item separato, vedi session resume.
- Audit log originale: `docs/scientific-audit-2026-04-12.md`.

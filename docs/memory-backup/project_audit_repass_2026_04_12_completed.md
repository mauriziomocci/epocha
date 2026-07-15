---
name: audit-repass-2026-04-12-completed
description: Retrospettiva F-CAMPAIGN (2026-05-12 -> 2026-07-15) -- Round 2 su tutti i moduli batch 2026-04-12 fino a CONVERGED, 5 promozioni a paragraph 4, world/economy.py deprecato. Residuo fuori campagna in [[audit-repass-batch-2026-04-12-pending]].
type: project
---
# Retrospettiva campagna F-CAMPAIGN (audit re-pass batch 2026-04-12)

## Perimetro e durata

Campagna aperta il 2026-05-12 (piano legacy `docs/superpowers/plans/2026-05-12-audit-repass-campaign.md`), chiusa il 2026-07-15 col branch 6. Obiettivo: eseguire il Round 2 avversariale mancante sui moduli del batch audit 2026-04-12 (14 INCORRECT + 19 UNJUSTIFIED + 6 INCONSISTENT + 12 MISSING findings originali, remediation fatta nel 2026-04 senza verifica di convergenza) e promuovere i convergiti da paragraph 8 a paragraph 4 del whitepaper bilingue.

## Esiti per branch

Tutti i branch auditati sono convergiti al Round 2 -- meglio della stima di piano (2-4 round per branch, pattern Demography = 4 round):

| # | Branch | Round a CONVERGED | Promozione | PR / merge |
|---|--------|-------------------|-----------|------------|
| 1 | Reputation | 2 (2026-05-12) | paragraph 4.3 | PR#5 c196281 |
| 2 | Rumor cluster | 2 (2026-05-16) | paragraph 4.4 | PR#6 a0ea075 |
| 3 | Political cluster | 2 (2026-05-16) | paragraph 4.5 | PR#7 dfeb709 |
| 4 | Movement | 2 (2026-05-16) | paragraph 4.6 | PR#8 c543c10 |
| 5 | Factions | 2 (2026-05-16) | paragraph 4.7 | PR#9 5406b95 |
| 6 | World economy deprecation | n/a (deprecation, non re-audit) | nessuna (modulo legacy fuori architettura documentata) | Spec Kit `specs/20260715-094457-world-economy-deprecation/` |

Il branch 6 ha scelto il path B del piano (marker di deprecazione) perche' la verifica caller ha trovato il modulo ancora vivo come fallback dell'engine (`simulation/engine.py`, gate su `Currency`) e nel percorso Celery (`simulation/tasks.py:46` -> `run_economy`): la rimozione fisica avrebbe cambiato comportamento ed e' rimandata a un work item di migrazione caller.

## Cosa ha insegnato la campagna

1. **Il Round 2 trova cio' che il Round 1 e la remediation non vedono.** Esempio documentato: IF-5 (deduplicazione eventi pubblici chiavata sul content in `information_flow.py`) e' un fix emerso al Round 2 del 2026-05-16 -- la forma pre-audit coalesceva eventi distinti dello stesso tick. La convenzione di progetto "citation drift after Round 1 remediation is a known failure mode" (constitution, Documentation Discipline) e' confermata empiricamente.
2. **I conteggi di stato nel whitepaper degradano a ogni promozione.** A fine campagna il conteggio "moduli pendenti in paragraph 8" era stale in 11 punti tra EN e IT (valori diversi: tre, quattro, sei, undici a seconda della sezione) con factions e in un caso movement omessi dagli elenchi dei convergiti; l'EN paragraph 11 diceva "four" dove l'IT diceva "tre", e abstract + paragraph 12 erano sfuggiti sia all'inventario della spec sia al primo gate grep (troppo stretto: cercava "modules/moduli" ma non "subsystems/sottosistemi"). Li ha trovati l'audit avversariale di fase 6. Lezioni operative: (a) ogni promozione paragraph 8 -> paragraph 4 deve includere un grep di coerenza in ENTRAMBE le lingue esteso a tutti i sinonimi dell'enumerazione (moduli, sottosistemi, cluster), abstract e conclusioni comprese; (b) meglio eliminare i conteggi numerici fragili dove la prosa lo consente (l'abstract ora dice "the audited scientific modules" senza numero).
3. **Le memorie tracker citate dal whitepaper non si marcano "DONE" a cuor leggero.** Il file `project_audit_repass_batch_2026_04_12_pending.md` e' citato per nome nei paragrafi 10/11/12: il branch 6 lo ha riscritto mantenendo il nome e ridefinendone il contenuto sul residuo effettivo, invece di archiviarlo come dicevano i task originali del piano (Task 6.5).
4. **Deprecation e' un esito legittimo di un re-audit.** Non tutto il debito si estingue re-auditando: quando esiste un sostituto auditato, marcare il legacy e tracciare la migrazione dei caller costa meno e produce piu' chiarezza di un audit su codice destinato alla rimozione.

## Residuo dichiarato a fine campagna

- **paragraph 8.1 Knowledge Graph** e **paragraph 8.2 economy base layer**: Round 2 pendente, fuori scope campagna, tracciati da [[audit-repass-batch-2026-04-12-pending]].
- **Factions Round 3 hardening**: 5 finding behavioral deferred (NEW-1, NEW-7, NEW-8, NEW-10, NEW-12/13), catalogati nel Known Limitations bullet (f) di `factions.py`.
- **Validation experiments**: campagna paragraph 7 ancora pendente, vedi [[project_validation_experiments_pending]].

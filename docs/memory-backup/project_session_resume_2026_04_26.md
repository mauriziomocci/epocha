---
name: session-resume-2026-04-26
description: CLOSED -- catchup README+whitepaper bilingue completato e mergiato in develop. PR#4 (merge 168d90b), frozen-at-commit pinned (591024c). Prossimo step: Demography Plan 3 (Inheritance + Migration).
type: project
originSessionId: b165274d-a708-4e8c-abed-b28a018c163f
---

# Sessione 2026-04-26 -- catchup README + whitepaper bilingue

## STATUS: CLOSED

**PR**: https://github.com/mauriziomocci/epocha/pull/4 -- MERGED 2026-04-26T19:27Z
**Merge commit**: `168d90bad94f9edd51bcd5b54166321456fc6f43` (short `168d90b`)
**Frozen-at-commit pin**: `591024c` (post-merge follow-up su develop, sostituisce 20 placeholder)
**Develop HEAD**: `591024c` (pushato a origin)
**Branch feature**: cancellato local + remote

## Cosa e' stato consegnato

- `docs/whitepaper/epocha-whitepaper.md` -- ~2180 righe, ~33k parole, EN authoritative, 14 capitoli + 3 appendici, 72 entries §13, 15 equazioni numerate
- `docs/whitepaper/epocha-whitepaper.it.md` -- ~2010 righe, ~36k parole, IT mirror, EN-IT parity verified
- `README.md` + `README.it.md` -- 127 righe ciascuno, developer-focused entry point (era 493 righe marketing-style)
- `CLAUDE.md` -- aggiunta whitepaper-code doc-sync rule sotto Documentation Sync
- `docs/superpowers/specs/2026-04-26-readme-and-whitepaper-catchup-design.md` -- spec IT (b9067f3)
- `docs/superpowers/plans/2026-04-26-readme-and-whitepaper-catchup.md` -- plan EN 48 task (8781844)
- 4 nuove memorie progetto persistite in `docs/memory-backup/`

## Tutti gli 8 blocchi del plan completati (48/48 task)

| Block | Tasks | Esito |
|---|---|---|
| W1 Whitepaper foundation | 1-7 | DONE |
| W2 Methods audited | 8-19 | DONE (review tasks 13/15/17/19 skippati, sostituiti da F6 Task 43 audit) |
| W3 Whitepaper completion | 20-29 | DONE |
| W4 Italian translation | 30-37 | DONE |
| R README + CLAUDE.md | 38-41 | DONE |
| F6 Audits | 42 (bibliography), 43 (sci consistency), 44 (EN-IT) | tutti CONVERGED dopo round 1 fix |
| F7 Closure | 45 (pytest 800/0), 46 (pin strategy), 47 (memory sync), 48 (push + draft PR) | DONE |

## Heavy gate evidence (per future reference)

- pytest 800/0 (zero regressioni; nessun code change in branch)
- 3 adversarial audit (bibliography + sci consistency + EN-IT) tutti CONVERGED
- EN-IT parity finale: 72/72 §13, 15/15 equazioni, 17/17 status header, 66/66 H1+H2

## Findings critici scoperti durante la sessione (NON DIMENTICARE)

1. **GAP CRITICO**: Demography Plan 1+2 mortality/fertility/couple sono unit-tested ma MAI invocate dal simulation engine. L'unica funzione demografica gia' wired e' `set_avoid_conception_flag` per l'azione tick+1. Wiring completo demandato a Plan 4 (Init + Engine + Validation execution). Whitepaper §4.1 lo dichiara onestamente.

2. **Economy diversa**: i moduli Economy Behavioral SONO genuinely live nel tick loop. `process_economy_tick_new()` chiama expectations/credit/property correttamente. Asimmetria importante con demography, documentata in §4.2 intro.

3. **14+ plan signature errate** scoperte durante implementation grazie a verify-before-asserting:
   - `add_to_treasury(government, currency_code, amount)` NON `(zone, amount)`
   - `compute_subsistence_threshold(simulation, zone)` NON `(zone, n_agents)`
   - `compute_aggregate_outlook(agent)` NON `(simulation, tick)`
   - `get_seeded_rng(simulation, tick, phase)` NON `stream_label`/`simulation_id`
   - UUID PKs era FALSO -- BigAutoField
   - PostGIS gia' implementata
   - HTMX era FALSO -- Alpine.js
   - LM Studio/OpenAI/Groq NON provider separati -- single OpenAIProvider
   - rate limiter NON token bucket -- Redis sliding window
   - mortality `resolve_tick_deaths()` NON esiste
   - `malthusian_ceiling()` NON esiste -- `_soft_ceiling()`
   - codice cita Nerlove 1958 NON Cagan 1956 (algebricamente equivalenti, dual lineage documentato)
   - `marriage_market_type` NON `arranged_marriage` boolean
   - homogamy = class/edu/age/relationship NON Big Five
   - `dissolve_on_death` regular function NON Django signal
   - economy ha 4 templates NON 5

4. **B2-07 debt**: Becker coefficients identici across 5 templates demografici. Plan 4 calibrazione.

5. **Lee 1987 nel docstring di `fertility.py:malthusian_soft_ceiling()`** non e' in §13 e non e' citato nel whitepaper -- minor, decision pendente.

## Follow-up persistiti come memorie

- [Audit re-pass batch 2026-04-12 pending](project_audit_repass_batch_2026_04_12_pending.md) -- HIGH priority post-Plan 3
- [Validation experiments pending](project_validation_experiments_pending.md) -- pre-paper-submission
- [Whitepaper doc-sync rule](feedback_whitepaper_doc_sync.md) -- regola permanente
- [Whitepaper promotion pipeline](project_whitepaper_promotion_pipeline.md) -- procedura cap.8 -> cap.4

## Pattern operativi che hanno funzionato

1. **Strict subagent-driven**: implementer + spec/quality review + fix-implementer pattern.
2. **Verify-before-asserting** ha catturato 14+ plan inaccuracies. Phase 4 task breakdown future devono includere code-verification preflight.
3. **§13 alphabetical maintained at every commit** invece di consolidation pass at end -- piu' robusto.
4. **HTML comments per VERIFICATION PENDING** al posto di visible body text.
5. **Lessons learned baked into next implementer prompts** ha ridotto i fix-cycle.
6. **Batching W3 e W4** ha accelerato significativamente.
7. **F6 audit dispatch a fine ciclo** invece di review per-task ha ridotto overhead mantenendo rigore (audit pesanti finali catturano tutto).

## Prossimo step

**Demography Plan 3 -- Inheritance + Migration**

Scope dalla spec `docs/superpowers/specs/2026-04-18-demography-design.md`:
- `inheritance.py`: polygenic additive, derived_trait_formulas (cunning), social class per-era, education regression, estate tax con `add_to_treasury`, loans-as-lender transfer, simultaneous deaths ordering, multi-gen cascade, mourning memory, orphan caretaker
- `migration.py`: context enrichment (wage differential, Harris-Todaro), family coordination Mincer 1978, emergency flight con guard ragionato, trapped_crisis broadcast, mass flight threshold

Stima: ~22 task + audit loop. Una volta che Plan 3 e' mergiato, **promuovere il modulo demografia da §4.1 (gia' presente) NON cambia** ma DEVI aggiornare il whitepaper:
- §9 Roadmap: rimuovere "Plan 3" come voce, aggiornare lo stato di Plan 4
- §4.1 Status header: aggiornare commit hash via doc-sync rule
- (eventualmente) §4.1 add new sub-section per Inheritance / Migration se appropriato

PRIMA di iniziare Plan 3 valuta se anche fare il **re-audit batch 2026-04-12** (8 moduli in §8 cap. 8) per liberare debt prima di nuove feature -- vedi `project_audit_repass_batch_2026_04_12_pending.md`. Decisione utente.

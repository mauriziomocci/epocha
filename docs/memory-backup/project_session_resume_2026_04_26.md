---
name: session-resume-2026-04-26
description: READ FIRST AT SESSION START -- riepilogo sessione 2026-04-26 catchup README+whitepaper. Branch in volo a F6 Task 43, 30 commit prima del merge.
type: project
originSessionId: b165274d-a708-4e8c-abed-b28a018c163f
---
# Sessione 2026-04-26 -- catchup README + whitepaper bilingue

## Stato al momento dello stop

**Branch attiva**: `feature/readme-and-whitepaper-catchup`
**HEAD**: `077d78c` (F6 audit fix round 1 commit)
**Working tree**: clean
**Su develop**: 30 commit ahead (non pushato)

**Deliverable creati**:
- `docs/whitepaper/epocha-whitepaper.md` -- 2176 righe, ~33k parole, bilingue EN authoritative
- `docs/whitepaper/epocha-whitepaper.it.md` -- 1985 righe, ~36k parole, IT mirror
- `README.md` -- 127 righe, developer-focused entry point (era 493 righe marketing-style)
- `README.it.md` -- 127 righe, IT mirror
- `CLAUDE.md` -- aggiunta whitepaper-code doc-sync rule sotto Documentation Sync
- `docs/superpowers/specs/2026-04-26-readme-and-whitepaper-catchup-design.md` -- spec IT (commit `b9067f3`)
- `docs/superpowers/plans/2026-04-26-readme-and-whitepaper-catchup.md` -- plan EN 48 task (commit `8781844`)

**Memorie create durante la sessione** (gia' nella memory live + aggiungere a backup):
- `project_audit_repass_batch_2026_04_12_pending.md` -- HIGH-PRIORITY post-Plan 3
- `project_validation_experiments_pending.md` -- pre-paper-submission
- `feedback_whitepaper_doc_sync.md` -- regola permanente
- `project_whitepaper_promotion_pipeline.md` -- procedura cap.8 -> cap.4

## Lavoro completato (Task 1-42 del plan + fix 1)

| Block | Tasks | Status | Commits |
|---|---|---|---|
| W1 Whitepaper foundation | 1-7 | DONE | fcf269a, f2b42ce, 4eadeb0, bf16d7f, bcfe570, 5b0204a, 095c0ad, 2ec2104, 5e05604, a6b812d |
| W2 Methods audited | 8-19 (review 13/15/17/19 skippati, F6 li audita) | DONE | a0d68c0, 16f0938, 2874dd5, 4292f55, 773c16f, cbb5f78, 5291ea4, 8858a88 |
| W3 Whitepaper completion | 20-29 | DONE | 56669d7, 4390a5f, 2dcdb1e |
| W4 Italian translation | 30-37 | DONE | 411b2f8, 7482dc6, beefc65, 5c9d8c4 |
| R README + CLAUDE.md | 38-41 | DONE | 54c066f |
| F6 audit Task 42 (bibliography) | 42 | DONE round 1 | 077d78c |
| F6 audit Task 43 (sci consistency) | 43 | **PENDING** | -- |
| F6 audit Task 44 (EN-IT consistency) | 44 | **PENDING** | -- |
| F7 closure | 45-48 | **PENDING** | -- |

## Findings importanti scoperti durante la sessione (NON DIMENTICARE)

1. **Plan signatures errate (~14 discrepanze)**: durante implementazione, i subagent hanno scoperto che il plan task descriptions estrapolavano funzioni che non esistevano o avevano signature diverse. Lessons:
   - `add_to_treasury(government, currency_code, amount)` -- NON `(zone, amount)`
   - `compute_subsistence_threshold(simulation, zone)` -- NON `(zone, n_agents)`
   - `compute_aggregate_outlook(agent)` -- NON `(simulation, tick)`
   - `get_seeded_rng(simulation, tick, phase)` -- NON `stream_label`, e simulation NON simulation_id
   - UUID PKs erano FALSO -- BigAutoField
   - PostGIS gia' implementata -- NON pianificata
   - HTMX era FALSO -- Alpine.js
   - LM Studio/OpenAI/Groq NON sono provider separati -- single OpenAIProvider con base_url
   - rate limiter NON token bucket -- Redis sliding window
   - mortality `resolve_tick_deaths()` NON esiste
   - `malthusian_ceiling()` NON esiste -- `malthusian_soft_ceiling()`
   - codice cita Nerlove 1958 NON Cagan 1956 (algebricamente equivalenti, dual lineage documentato)
   - `marriage_market_type` (autonomous|arranged) NON `arranged_marriage` boolean
   - homogamy weights = class/edu/age/relationship NON Big Five
   - `dissolve_on_death` regular function NON Django signal
   - economy ha 4 templates NON 5 come demography
   - economy `expectations` template config Python NON JSON

2. **GAP CRITICO scoperto**: **Demography Plan 1+2 mortality/fertility/couple sono implementate e unit-tested ma MAI invocate dal simulation engine**. Le funzioni esistono solo nei test. L'integrazione nel tick loop e' demandata a Plan 4 (Init + Engine + Validation execution). Whitepaper §4.1 lo dichiara onestamente. Plan 4 deve fare:
   - `from epocha.apps.demography.mortality import tick_mortality_probability, sample_death_cause`
   - `from epocha.apps.demography.fertility import tick_birth_probability, resolve_childbirth_event`
   - `from epocha.apps.demography.couple import resolve_pair_bond_intents, resolve_separate_intents, dissolve_on_death`
   - integrare nel `simulation/engine.py` tick loop con ordine `mortality -> fertility -> couple formation`
   - **Economy modules INVECE sono live nel tick loop** (verificato in Task 14/16/18) -- economy `process_economy_tick_new()` chiama expectations/credit/property correttamente. Asimmetria importante.

3. **B2-07 debt ancora aperto**: Becker coefficients identici across 5 templates demografici. Plan 4 deve calibrarli per epoca.

4. **Lee 1987 nel docstring di `fertility.py:malthusian_soft_ceiling()`** non e' in §13 e non e' citato nel whitepaper. Va aggiunto al docstring un commento o rimosso (decisione futura, non critica).

5. **F6 Task 42 round 1 fix** ha risolto:
   - F-01 Iannaccone 1992 added to §13
   - F-02 Reinhart-Rogoff 2009 added to §13
   - F-03 Jones-Tertilt 2008 added to §13
   - F-04 "Polity IV" -> "Polity5" factual fix
   - F-05 Castelfranchi citation form normalized (body line 1196)
   - F-07/F-08 5 unparenthesized citations parenthesized
   - F-09/F-10/F-11 deferiti come acceptable
   - F-06 deferito (model name vs citation, deliberate)

## Cosa resta da fare (in ordine)

### IMMEDIATO -- F6 audit completion

#### Task 42 re-audit per CONVERGED verdict (round 2)

Dispatch un'altra critical-analyzer (Opus) sull'EN whitepaper con stesso mandato di Task 42 ma focus: verificare che round 1 fixes hanno chiuso F-01..F-08 e non hanno introdotto nuovi problemi. Loop fino a CONVERGED.

#### Task 43 -- Scientific consistency audit

Dispatch critical-analyzer (Opus). Mandato: leggere whitepaper §4 Methods E codice in `epocha/apps/{demography,economy}/` e verificare che ogni formula/parametro/algoritmo nel whitepaper sia coerente col codice. Output: INCORRECT/INCONSISTENT/MISSING/VERIFIED. Loop fino CONVERGED.

Probabili findings (mio prediction): pochi -- gli implementer hanno fatto verify-before-asserting bene durante drafting.

#### Task 44 -- EN-IT consistency audit

Dispatch critical-analyzer (Opus). Mandato: confrontare EN e IT whitepaper. Verificare che IT non introduca/perda contenuti scientifici, formule, parametri, citazioni. Loop fino CONVERGED.

Probabili findings: pochi -- W4 batch D ha gia' fatto self-check con esiti positivi.

### POI -- F7 Closure (Tasks 45-48)

#### Task 45 -- Full pytest run

```bash
docker compose -f docker-compose.local.yml ps  # potrebbe servire up -d se spenti
docker compose -f docker-compose.local.yml exec web pytest --cov=epocha -v
```

Atteso: 800/0 (no code changes in this branch, no regression expected).

#### Task 46 -- Pin frozen-at-commit hash

Strategia: `<filled-on-merge>` placeholders (10 in EN + 10 in IT) restano come placeholder durante questo branch; vengono sostituiti con hash effettivo del merge commit via `docs: pin whitepaper frozen-at-commit` follow-up commit DOPO il merge in develop.

NON tentare di predire l'hash prima del merge.

#### Task 47 -- Sync memory backup

```bash
cp ~/.claude/projects/-Users-mauriziomocci-Documents-workspace-Opensource-epocha/memory/*.md docs/memory-backup/
git add docs/memory-backup/
git commit -m "docs: sync memory backup with whitepaper catch-up follow-ups"
```

Le 4 nuove memorie sono gia' nella live; questo le persiste nel repo.

#### Task 48 -- Open draft PR e heavy gate

```bash
git push -u origin feature/readme-and-whitepaper-catchup
gh pr create --draft --title "docs: bilingual whitepaper and developer-focused README catch-up" --body ...
```

Attendere validazione umana heavy gate prima del merge.

### Closure post-merge

1. Replace `<filled-on-merge>` placeholders con hash effettivo del merge -- piccolo commit `docs: pin whitepaper frozen-at-commit` su develop
2. Sync memory backup finale
3. Aggiornare `project_session_resume_2026_04_26.md` con stato CHIUSO
4. Riprendere rotta verso **Demography Plan 3 (Inheritance + Migration)**

## Riferimento file chiave

- Branch: `feature/readme-and-whitepaper-catchup`
- HEAD: `077d78c`
- Spec: `docs/superpowers/specs/2026-04-26-readme-and-whitepaper-catchup-design.md`
- Plan: `docs/superpowers/plans/2026-04-26-readme-and-whitepaper-catchup.md`
- EN whitepaper: `docs/whitepaper/epocha-whitepaper.md` (2176 righe)
- IT whitepaper: `docs/whitepaper/epocha-whitepaper.it.md` (1985 righe)
- README EN: `README.md` (127 righe)
- README IT: `README.it.md` (127 righe)
- CLAUDE.md: con whitepaper-doc-sync rule

## Pattern operativo che ha funzionato

1. **Strict subagent-driven**: dispatch implementer (Sonnet/Opus per task complexity), poi spec+quality review combinato (Sonnet light o Opus per critical), poi fix-implementer se findings.
2. **Verify-before-asserting** ha catturato 14+ plan inaccuracies. NON fidarsi mai di plan task descriptions per code references; sempre verificare contro file reali.
3. **§13 alphabetical maintained at every commit** invece di consolidation pass at end -- piu' robusto.
4. **HTML comments** per VERIFICATION PENDING al posto di visible body text.
5. **Lessons learned baked into next implementer prompts** ha ridotto i fix-cycle subseguenti.
6. **Batching W3 e W4** ha accelerato significativamente (4 dispatch invece di 18).

## Sessione modello selection

- W1 Tasks 2-7: Opus (substantive scientific writing)
- W1 Task 1 + R: Sonnet (mechanical scaffold/translation)
- W2 Tasks 8/10/12/14/16/18 (drafts): Opus (research + verification)
- W2 Tasks 9/11 (reviews): Sonnet (mostly mechanical verification)
- W3 batches: Opus (cross-module judgment)
- W4 batches: Opus (translation needs scientific terminology accuracy)
- F6 audits: Opus (critical-analyzer subagent)

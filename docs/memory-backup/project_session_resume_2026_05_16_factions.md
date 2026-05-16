---
name: session-resume-2026-05-16-factions
description: READ FIRST. Branch 5 factions in flight. Spec Kit docs autorate, Round 2 audit DONE — NOT CONVERGED, 16 findings (4 R1 OPEN + 12 new = 4× spec ceiling). ESCALAZIONE UTENTE necessaria prima fix. Recommended split: 11 in-branch + 5 deferred to Round 3 hardening spec separato.
type: project
originSessionId: b165274d-a708-4e8c-abed-b28a018c163f
---

# Sessione 2026-05-16 (parte 3) — Branch 5 factions IN FLIGHT

## STATUS: Spec Kit docs DONE. Round 2 audit DONE. NESSUN fix applicato. ESCALAZIONE pendente.

## Branch state

- Branch: `20260516-183045-factions-audit-repass`
- HEAD: `0c1ecd7` (tasks.md commit)
- 3 commit ahead develop, working tree pulito
- Su develop @ `0afca1d` (post-movement Branch 4 closure)

## Cosa fatto in questa sessione (2026-05-16 finale)

### Branch 4 movement CHIUSO (precedente)

- PR#8 mergiato `c543c10`, pin `5e0087f`
- §4.6 promotion EN+IT
- 5 R1 + 3 R2 doc findings CLOSED
- Pytest 809
- 5 R2 non-blocking findings deferred (N-3 cross-module, N-4 GIST-indexed N+1, N-5 test gaps, N-7 project-wide clamp DRY, N-8 RNG reproducibility)

Dettagli completi in `project_session_resume_2026_05_16_movement.md`.

### Branch 5 factions IN FLIGHT

**Spec Kit docs (3 commit)**:
- `f03e231` spec.md — 4 R1 findings → 4 user stories + 10 FR + 7 SC
- `0ded6b7` plan.md + research.md — Constitution PASS, 3 lookups (Judge 2002 Crossref, Stogdill 1948 actual content verify, Dunbar 1992 actual claim verify)
- `0c1ecd7` tasks.md — 37 tasks across 8 phases, MVP = US1

**Round 2 audit eseguito**: verdetto **NOT CONVERGED — 16 findings** (4 R1 OPEN + 12 NEW). Scope esplode 4× il ceiling spec (~3 nuovi).

## 4 R1 findings (TUTTI OPEN, partial mitigation only)

- **F-1 INCORRECT**: Stogdill 1948 cited per leadership weighted formula. Mitigazione parziale a `factions.py:111-116`. Fix: cite Stogdill per principio; weights design params; aggiungere Judge et al. 2002 *Journal of Applied Psychology* DOI per meta-analytic effect sizes. Charisma a Weber 1922 non Stogdill.
- **F-2 INCORRECT**: Dunbar 1992 cited per size penalty threshold 5. Mitigazione parziale a `factions.py:247-251`. Fix: reframe come tunable design parameter; Hackman 2002 e Zhou et al. 2005 mancanti come alternative.
- **F-3 UNJUSTIFIED**: Cohesion delta coefficients 0.10/0.15/0.02/0.05 unsourced. Mitigazione parziale a `factions.py:43-49`. Fix: reframe assoluto come tunable params, 1.5:1 ratio inspired-by Baumeister 2001 ma non derivato.
- **F-4 MISSING**: Schism order-dependence inline note `factions.py:465-468` buried mid-function. Fix: promuovere a docstring header Known Limitations + estendere a 2nd site `_detect_and_propose_factions:579-591`.

## 12 NEW findings Round 2

**INCORRECT (1)**:
- **NEW-1**: `_check_join_existing_groups:641` `Agent.objects.filter(group, is_alive)[:5]` default PK ordering biased sample. Stable but unrepresentative for long-lived groups. Fix: random sample `order_by("?")` OR rewrite docstring per ammettere bias. **BEHAVIORAL** → defer to Round 3 hardening spec.

**UNJUSTIFIED (6)**:
- **NEW-2**: F-4 scope widening — 3 siti order-dependent non 2. Aggiungere a Known Limitations bullet (d).
- **NEW-3**: Fallback sentiment 0.3 dopo normalize = raw -0.4 (non "slightly below neutral" come dice comment). 2 occorrenze `factions.py:151, 218`. Fix: reword OR change value.
- **NEW-4**: `_ALLY_SENTIMENT_THRESHOLD ±0.2` symmetric magic numbers (linee 55, 58). Inline tunable disclaimer.
- **NEW-5**: Splinter cohesion 0.5 vs new faction cohesion 0.6 — differenza 0.1 plausibile ma undocumented (linee 508, 782). One-line justification.
- **NEW-6**: Memory `emotional_weight` (0.2, 0.3, 0.4) scattered 8 sites no justification. Module docstring acknowledge grading.
- **NEW-9**: `EPOCHA_FACTION_DISSOLUTION_THRESHOLD/LEGITIMACY_THRESHOLD/AFFINITY_THRESHOLD` defaults (linee 340, 409, 566) unsourced. §4.7 Parameters table.

**INCONSISTENT (2)**:
- **NEW-8**: `_check_dissolution:414` usa `.update(group=None)` (no signal) ma `_check_schism/_create_faction/_process_formation_decisions` usano per-agent `agent.save()` (signal fires). Inconsistenza policy. **CROSS-CUTTING** → defer to Round 3.
- **NEW-10**: `_check_join_existing_groups:625-628` docstring dice "average affinity with first 5 group members" ma è biased sample (NEW-1). Fix docstring O implementation. **CON NEW-1** → defer Round 3.

**MISSING (1)**:
- **NEW-7**: No `transaction.atomic` su `_check_schism` (lines 504-547) né `_create_faction` (lines 778-819). Multi-row mutations vulnerabili a race condition (analogo Branch 1 reputation N-11). Fix: `@transaction.atomic` decorator. **BEHAVIORAL RISK** (savepoint nesting se chiamato dentro outer atomic) → defer to Round 3.

**LOW (2)**:
- **NEW-11**: `_generate_faction_identity:872` bare `except Exception`. Fix: narrow a `(json.JSONDecodeError, KeyError, ConnectionError, TimeoutError, llm_client.LLMError)`. Trivial 2-line.
- **NEW-12 + NEW-13**: N+1 patterns. NEW-12 `_check_join_existing_groups:638-644` 1250 affinity computations per tick (50 agents × 5 groups × 5 members). NEW-13 `compute_legitimacy:221` Relationship N+1 per member. **PERFORMANCE** → defer to Round 3.

## ESCALAZIONE PENDENTE — Recommended Convergence Path

Spec ceiling: ~3 new findings su US3. Audit ha trovato 12. Split necessario.

### Keep in this branch (US1+US2+US3): 11 items

US1 + US2 → close 4 R1 doc-only (F-1, F-2, F-3, F-4) per existing task text
US3 → close 7 NEW doc-only:
- NEW-2 (folds into F-4 bullet (d) widening)
- NEW-3 (reword comment "slightly" misrepresenta -0.4 raw)
- NEW-4 (tunable disclaimer ±0.2 symmetric)
- NEW-5 (one-line splinter vs new cohesion 0.1 differential)
- NEW-6 (module docstring emotional_weight grading note)
- NEW-9 (3 settings defaults inline disclaimers + §4.7 Parameters rows)
- NEW-11 (narrow except 2-line fix, no behavior change)

US4 → §4.7 promotion include Known Limitations covering deferred items.

### Defer to separate "factions Round 3 hardening" spec: 5 items

- **NEW-1** biased member sample (behavioral, changes which agents receive join suggestions, coord-test updates)
- **NEW-7** transaction.atomic wrapping multi-row writes (behavioral risk, regression tests for concurrent-write invariant)
- **NEW-8** Agent migration discipline standardization (signal-firing vs single-update, cross-cutting policy)
- **NEW-10** join_existing_groups docstring-vs-implementation (con NEW-1)
- **NEW-12 + NEW-13** N+1 batching (performance branch with benchmarks)

## DA FARE DOMANI

### IMMEDIATO (richiede decisione utente)

1. **ESCALATION**: utente conferma split 11+5 o vuole diverso scope? Default proposto: accetta 11 in-branch + 5 deferred.

### Se split accettato

2. Dispatch fix-implementer per:
   - US1 close F-1, F-2 (doc fixes con Judge 2002 + Hackman 2002 additions)
   - US2 close F-3, F-4 (cohesion coefficients reframe + schism order-dependence Known Limitations promoted)
   - US3 close 7 NEW items doc-only
3. Round 3 audit verify CONVERGED
4. US4 promote §8.1 (currently Factions post-movement renumber) → §4.7 EN+IT
5. README EN+IT status table flip Factions row
6. Doc-sync memory mapping
7. PR + merge + frozen-pin per merge SHA
8. Memory closure

### Nuovo spec da creare per i 5 deferred items

`specs/<timestamp>-factions-round3-hardening/` separate branch via specify workflow. Scope:
- NEW-1 biased sample fix
- NEW-7 transaction.atomic con concurrency tests
- NEW-8 Agent migration policy decision + standardization
- NEW-10 docstring-vs-impl sync (con NEW-1)
- NEW-12+NEW-13 N+1 batching con benchmark

Stima: 30-40 tasks separato branch.

### Dopo Branch 5 factions chiuso

Branch 6 (ultimo F-CAMPAIGN): `<timestamp>-world-economy-deprecation` — `epocha/apps/world/economy.py` legacy MVP placeholder. Decisione: deprecate o re-audit? Default deprecation procedure documented in `project_audit_repass_batch_2026_04_12_pending.md`.

### Post-campagna

- Demography Plan 4 (engine wiring mortality/fertility/couple)
- Validation experiments execution
- Eventuale Round 3 hardening spec per factions

## Develop HEAD

`0afca1d` (post-Branch 4 movement closure).

## Branch attivo locale

`20260516-183045-factions-audit-repass` @ `0c1ecd7` (Spec Kit docs only). Non pushato.

## Campagna F-CAMPAIGN progress

| # | Branch | Status | PR | Merge |
|---|--------|--------|----|-------|
| 1 | Reputation | CHIUSO | PR#5 | c196281 |
| 2 | Rumor cluster | CHIUSO | PR#6 | a0ea075 |
| 3 | Political cluster | CHIUSO | PR#7 | dfeb709 |
| 4 | Movement | CHIUSO | PR#8 | c543c10 |
| 5 | **Factions** | **IN FLIGHT** | — | — |
| 6 | World economy deprecation | PENDENTE | — | — |

Whitepaper §4: 6 capitoli audited (4.1 Demography, 4.2 Economy Behavioral, 4.3 Reputation, 4.4 Rumor, 4.5 Political, 4.6 Movement). Prossimo §4.7 Factions. §13 a 105+ entries.

## Lessons learned this session

1. **Round 2 audit factions ha trovato 4× il ceiling** — il modulo da 876 LOC è il più grande della campagna, scope explosion atteso ma più severa del previsto. Per future audits su moduli >500 LOC: dimensione ceiling proporzionale.
2. **NEW-1 biased sample** è un pattern Python comune (default ordering PK ASC) che probabilmente esiste in altri moduli — grep `\.filter\(.*\)\[:` su tutto agents/ + world/ in future audit.
3. **NEW-7 transaction.atomic MISSING su multi-row mutations**: pattern già visto in reputation (Branch 1 N-11), government (Branch 3 N-3+N-6). Sistemico — agents/ + world/ tutti possibili candidati. Future audit: grep `bulk_update\|bulk_create\|\.save\(\)` in funzioni che mutano multiple rows.
4. **NEW-8 Agent migration discipline**: 2 pattern coesistono (`.update()` no-signal vs per-agent `.save()` signal-fires). Policy decision necessaria a livello progetto.
5. **N+1 patterns NEW-12/13**: il caso join_existing_groups (50 × 5 × 5 = 1250 compute_affinity per tick) è alto-impact runtime. Performance audit necessario post-campagna.
6. **Spec Kit ceiling enforcement funziona**: spec.md plan.md tasks.md hanno stop conditions esplicite che catturano scope explosion. Utente notificato prima di fix dispatch.

## File chiave per ripresa

- `specs/20260516-183045-factions-audit-repass/spec.md` — 4 R1 + 4 user stories + 10 FR + 7 SC
- `specs/20260516-183045-factions-audit-repass/plan.md` — Constitution Check PASS, stop conditions documented
- `specs/20260516-183045-factions-audit-repass/research.md` — Judge 2002 + Stogdill 1948 + Dunbar 1992 lookups
- `specs/20260516-183045-factions-audit-repass/tasks.md` — 37 tasks across 8 phases
- `epocha/apps/agents/factions.py` (876 LOC) — current state
- `docs/scientific-audit-2026-04-12.md` — original R1 audit transcript

## Pytest baseline

Last confirmed: 809 (post Branch 4 movement). Atteso 809 anche dopo Branch 5 spec/plan/tasks (no code touched). Dopo fixes: 809-812 (eventual invariant tests US3).

## Spec Kit Constitution compliance

- Principle I (Scientific Method): tutti fix devono produrre verified citation OR tunable doc
- Principle II (Verify Before Asserting): line refs verificate al pre-flight, già drift catturato
- Principle III (Adversarial Audit): Round 2 fatto, Round 3 mandatory dopo fixes
- Principle IV (Three-Step Design): spec è output consolidato
- Principle V (Evidence-Based): pytest gate per task, no skip senza authorization

## NON DIMENTICARE

- Branch 5 factions audit ha esposto pattern sistemici (concurrency, biased sampling, N+1, migration discipline) che probabilmente esistono in moduli non-ancora-auditati. Future Plan 4 demography engine wiring deve grep questi pattern preventivamente.
- Spec Kit absolute rule rimane in vigore — nessun work item via legacy `docs/superpowers/`. Round 3 hardening spec sarà nuovo `specs/<timestamp>-factions-round3-hardening/`.
- Whitepaper-code doc-sync rule attiva. Promotion di §4.7 richiederà aggiornare CLAUDE.md doc-sync mapping.

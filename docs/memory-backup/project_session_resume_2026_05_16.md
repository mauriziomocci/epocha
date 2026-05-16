---
name: session-resume-2026-05-16
description: READ FIRST. Spec Kit adottato (commit 19279a1), regola assoluta. Branch audit-repass/rumor-cluster da retrofittare in formato Spec Kit. 16 findings Round 2 da migrare in spec.md.
type: project
originSessionId: b165274d-a708-4e8c-abed-b28a018c163f
---
# Sessione 2026-05-16 -- Spec Kit adoption + rumor-cluster retrofit

## STATUS: Spec Kit adottato. Retrofit rumor-cluster in corso.

## Cosa e' stato fatto

1. **Spec Kit installato** (`specify init . --here --ai claude --no-git --branch-numbering timestamp --force`). Files:
   - `.specify/memory/constitution.md` populated v1.0.0 (5 core principles dalla CLAUDE.md)
   - `.specify/templates/{spec,plan,tasks,checklist,constitution}-template.md`
   - `.specify/scripts/bash/` (create-new-feature.sh, setup-plan.sh, etc.)
   - `.specify/workflows/`, `.specify/integrations/`
   - `.claude/skills/speckit-{specify,plan,tasks,implement,clarify,analyze,checklist,constitution,taskstoissues}/`
   - `.gitignore` aggiornato: allow `.claude/skills/speckit-*`, ignore `.claude/settings.local.json`
   - CLAUDE.md SPECKIT section populated con rule absolute

2. **Regola permanente assoluta** in `feedback_speckit_mandatory.md`: tutti i nuovi work item via Spec Kit, branch `<timestamp>-<slug>`, layout `specs/<branch>/{spec,plan,tasks}.md`. Niente nuovi file sotto `docs/superpowers/`.

3. **Commit Spec Kit adoption** `19279a1` su develop, pushato a origin.

4. **Branch `audit-repass/rumor-cluster` rebased on develop** dopo Spec Kit adoption. Zero commit ancora.

## Da fare nella ripresa (immediato)

### Retrofit rumor-cluster in formato Spec Kit

1. Switch to develop, delete `audit-repass/rumor-cluster` local + remote (sicuro: zero commit)
2. Run `.specify/scripts/bash/create-new-feature.sh --short-name "rumor-cluster-audit-repass" --json` → genera branch `<timestamp>-rumor-cluster-audit-repass` + `specs/<branch>/spec.md`
3. Migrate 16 findings Round 2 da `project_session_resume_2026_05_12.md` in spec.md come requirements/acceptance scenarios
4. `/speckit-plan` → genera `plan.md`
5. `/speckit-tasks` → genera `tasks.md`
6. `/speckit-implement` o dispatch subagent fix-implementer
7. Loop fino CONVERGED, promote §8.1 → §4.4, merge, frozen-at-commit pin

### 16 findings Round 2 da migrare (sintesi)

Vedi `project_session_resume_2026_05_12.md` per dettaglio completo. Severita':
- 3 INCORRECT: IF-5 multi-event dedup, N-1 vocabulary mismatch cross-module, N-3 distortion-induced reputation drift
- 9 UNJUSTIFIED: IF-1 (Granovetter cited not impl), IF-4 (estimate_hop assumption), D-4 (openness accumulation), D-5 (proper noun anonymize), N-5 (DRY normalize), N-6 (weak-rumor magic), N-7 (affinity missing-trait docstring), N-8 (rivalry-coalition unsourced), N-9 (Phase 2 threshold asymmetry)
- 4 INCONSISTENT: D-1 (sharpening/assimilation contradiction), N-2 (4 missing §13 citations), N-4 (first-pattern-wins), N-10 (test coverage gaps)
- 11 VERIFIED (Round 1 fixes che hanno tenuto)

### Strategia fix lowest-risk (riprendi da qui)

- IF-1: rimuovere "tre famiglie" da §8.1 testualmente
- IF-4: documentare definitivamente come known limitation
- IF-5: behavioral fix (add `event_id` to lookup)
- D-1: riconciliare comments inline
- D-4, D-5: documentare definitivamente
- N-1: estendere keyword tables OR rewrite `_propagate_memory` per parsing structured action_type
- N-2: aggiungere 4 entries §13 EN+IT (Mayer 1995, Graziano-Tobin 2002, Castelfranchi-Falcone-Tan 1998, McCrae-Costa 2003)
- N-3: behavioral fix (spostare extract_action_sentiment prima di distortion)
- N-4: documentare design choice
- N-5: extract `_normalize_reputation` helper
- N-6: settings extraction
- N-7, N-8: docstring fixes / mark as tunable
- N-9: documentare asimmetria
- N-10: aggiungere `tests/test_rumor_invariants.py`

## Stato develop

HEAD `19279a1` (Spec Kit adoption commit). Pushato.

## Branch rimanenti dopo rumor-cluster

Tutti seguiranno Spec Kit:
3. `<timestamp>-political-cluster-audit-repass` -- government + government_types + institutions + stratification + election (22 findings originali)
4. `<timestamp>-movement-audit-repass` -- 5 findings
5. `<timestamp>-factions-audit-repass` -- 4 findings
6. `<timestamp>-world-economy-deprecation` -- legacy MVP placeholder

Post-campagna: Demography Plan 4 (engine wiring) + validation experiments execution. Sempre via Spec Kit.

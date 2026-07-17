---
name: speckit-mandatory-absolute
description: REGOLA PERMANENTE ASSOLUTA dal 2026-05-16. Tutti i nuovi work item DEVONO usare GitHub Spec Kit precisamente e senza eccezioni. Niente piu' nuove spec o plan sotto docs/superpowers/ -- solo specs/<timestamp>-<slug>/{spec,plan,tasks}.md.
type: feedback
originSessionId: b165274d-a708-4e8c-abed-b28a018c163f
---
# Spec Kit obbligatorio assoluto

Dal 2026-05-16 ogni nuovo work item (feature, fix campaign, refactor, deprecation) deve usare GitHub Spec Kit con conformita' precisa e assoluta. Nessuna eccezione tollerata, neanche per work in-flight.

## Cosa significa "precisamente e assolutamente"

1. **Branch naming**: timestamp + short-name produced by `.specify/scripts/bash/create-new-feature.sh` (formato `YYYYMMDD-HHMMSS-<slug>`). NIENTE branch ad-hoc tipo `audit-repass/rumor-cluster` o `feature/whatever`. Sempre via specify workflow.

2. **Spec layout**: `specs/<branch-name>/spec.md` + `plan.md` + `tasks.md`. NIENTE nuovi file sotto `docs/superpowers/specs/` o `docs/superpowers/plans/` (quelli restano solo come archivio storico).

3. **Authoring path**: usare le skill `/speckit-specify`, `/speckit-plan`, `/speckit-tasks`, `/speckit-implement`, `/speckit-constitution`. Optional: `/speckit-clarify`, `/speckit-analyze`, `/speckit-checklist`.

4. **Constitution-first**: ogni spec deve dichiarare conformita' alla constitution `.specify/memory/constitution.md`. Eccezioni motivate esplicitamente.

5. **Template fedelta'**: `.specify/templates/{spec,plan,tasks,checklist,constitution}-template.md` sono il contratto. Non improvvisare struttura alternativa.

6. **Workflow integration**: il canonical 7-phase workflow rimane in vigore. Spec Kit e' il framework di authoring; il 7-phase e' la procedura di gating (HEAVY GATE phases 2 + 6, LIGHT GATE phases 3 + 4).

## Cosa rimane legacy (NON migrare retroattivamente)

Artifacts sotto `docs/superpowers/{specs,plans}/` PRIMA del 2026-05-16:
- Demography Plan 1+2 + spec
- Economy base + behavioral spec/plans
- Reputation pre-promotion plan
- Catch-up README/whitepaper spec
- F-CAMPAIGN audit re-pass campaign plan (`2026-05-12-audit-repass-campaign.md`)
- Etc.

Mantenere git history. Continuare ad editare in place se servono amendments. Ma nuovi work items sotto Spec Kit.

## Retrofit eccezione (2026-05-16 transition)

Branch in flight `audit-repass/rumor-cluster` aveva ZERO commit al momento dell'adozione Spec Kit. Retrofittato deletando + ricreando via `specify` workflow conforme. Le 16 findings Round 2 migrate dal session resume memory in `specs/<timestamp>-rumor-cluster-audit-repass/spec.md`.

Future work-in-flight con commit non-banali: caso-per-caso. Default: completare sotto legacy e applicare Spec Kit alla feature successiva.

## Why

Decisione utente esplicita 2026-05-16. Spec Kit:
- Canonicalizza la struttura spec/plan/tasks che il progetto gia' praticava informalmente
- Costituzione formale supersede CLAUDE.md code-quality dove conflitto
- Skills `/speckit-*` integrano nativamente con Claude Code
- Branch numbering timestamp preserva continuita' col naming convention preesistente
- Templates eliminano improvvisazione struttura

## How to apply

- Inizio nuovo work item: `/speckit-specify "<descrizione breve>"` → crea branch + spec.md scaffold
- Spec drafting: editare `specs/<branch>/spec.md` seguendo template
- Plan: `/speckit-plan` → `specs/<branch>/plan.md`
- Tasks: `/speckit-tasks` → `specs/<branch>/tasks.md`
- Implementation: `/speckit-implement` o subagent-driven-development con tasks.md come input
- Heavy gate phase 2: adversarial audit del spec.md (CONVERGED required)
- Heavy gate phase 6: adversarial audit del codice (CONVERGED required) + final pytest
- Closure: merge to develop, frozen-at-commit pin se whitepaper toccato, memoria aggiornata

## Note operative (dalla sessione 2026-05-16, riverificare se cambiate)

- **`/speckit-plan` potrebbe NON essere invocabile via Skill tool.** Nella sessione 2026-05-16 risultava una procedura da seguire inline: eseguire `.specify/scripts/bash/setup-plan.sh --json` e poi riempire il template a mano, invece di chiamare la skill. Lo stesso potrebbe valere per altre `/speckit-*`. Verificare al momento dell'uso; questa nota corregge il punto 3 "Authoring path" sopra, dove le `/speckit-*` sono elencate come skill.
- **Dopo aver esteso keyword/parameter tables, fare sempre un grep o un runtime check per collisioni di substring.** Origine: la regex senza word-boundary faceva matchare `avoid` dentro `avoid_conception` (regressione introdotta da un fix doc-only del Round 1, intercettata solo dalla self-review dell'implementer). Usare word-boundary `\b` quando si matchano keyword.
- **I fix doc-only del Round 1 spesso lasciano problemi sostanziali**: dopo un giro di sole correzioni documentali, rifare grep/runtime check sul codice toccato prima di dichiararlo chiuso.

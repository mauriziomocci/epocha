---
name: session-resume-2026-05-16
description: CLOSED. Spec Kit adottato + F-CAMPAIGN Branch 2 rumor-cluster CONVERGED e mergiato (PR#6 merge a0ea075, pin 7a7ab3a). Prossimo Branch 3 political-cluster (22 findings) via Spec Kit.
type: project
originSessionId: b165274d-a708-4e8c-abed-b28a018c163f
---

# Sessione 2026-05-16 -- Spec Kit adoption + Branch 2 rumor-cluster

## STATUS: Branch 2 CHIUSO

## Spec Kit adoption (commits 19279a1 + 2b436ec)

- `.specify/` dir + 9 `/speckit-*` skills + constitution.md v1.0.0 (5 principles dalla CLAUDE.md)
- `.gitignore`: allow `.claude/skills/speckit-*`, ignore `.claude/settings.local.json`
- Regola permanente assoluta in `feedback_speckit_mandatory.md`
- CLAUDE.md SPECKIT section absolute (nessun nuovo file sotto `docs/superpowers/`)
- Branch naming: timestamp `<YYYYMMDD-HHMMSS>-<slug>` via `.specify/scripts/bash/create-new-feature.sh`
- Spec dir: `specs/<branch>/{spec,plan,tasks,research}.md` (NB: repo root `specs/`, NOT `.specify/specs/`)

## Branch 2 rumor-cluster (commits 12c0b08 → 5f14074, PR#6 mergato a0ea075, pin 7a7ab3a)

**Retrofit**: vecchio `audit-repass/rumor-cluster` (0 commit) cancellato. Nuovo branch Spec Kit conformante `20260516-105818-rumor-cluster-audit-repass`.

**Artifacts** (Spec Kit canonical):
- `specs/20260516-105818-rumor-cluster-audit-repass/spec.md` (16 findings → 4 user stories + 12 FR + 8 SC)
- `specs/20260516-105818-rumor-cluster-audit-repass/plan.md` (Constitution Check PASS, 43-52 task estimate)
- `specs/20260516-105818-rumor-cluster-audit-repass/research.md` (Crossref DOI verification + N-3 safety + N-8 cite Axelrod)
- `specs/20260516-105818-rumor-cluster-audit-repass/tasks.md` (55 tasks 8 phases)

**Round 2 findings 16 tutti CLOSED**:
- 3 INCORRECT: IF-5 dedup, N-1 vocabulary mismatch, N-3 distortion-induced reputation drift
- 9 UNJUSTIFIED: IF-1, IF-4, D-4, D-5, N-5, N-6, N-7, N-8, N-9
- 4 INCONSISTENT: D-1, N-2 (4 missing §13 citations: Castelfranchi-Falcone-Tan 2001, Graziano-Tobin 2002, Mayer-Davis-Schoorman 1995, McCrae-Costa 2003), N-4, N-10 (3 invariant test classes)
- Round 3 trovò 2 trivial doc-staleness (Graziano-Tobin page 695-727→728 + docstring 0.1 literal) — entrambi chiusi commit 50ff67e

**Findings critici scoperti durante US1**:
- Race condition word-boundary: `avoid` matchava `avoid_conception` (substring collision). Fix word-boundary regex `\b` + `re` import. Commit 9be6ab3.
- 14 action types in `_IMAGE_DELTAS` ma assenti dai keyword tables (rotto dual-track Castelfranchi-Conte-Paolucci sul hearsay path). Fix: estensione keyword tables.

**Promotion §8.1 → §4.4 EN+IT (commit 5f14074)**:
- §4.4 Rumor propagation con 4 sub-sections (4.4.1 Information flow, 4.4.2 Distortion, 4.4.3 Belief filter, 4.4.4 Affinity)
- Canonical Methods schema per ognuno
- Equation numbering 4.19-4.25
- §8 renumbering: 8.2→8.1 Political, 8.3→8.2 Movement, 8.4→8.3 Factions, 8.5→8.4 Knowledge Graph, 8.6→8.5 Economy base
- §9 Roadmap rumor cluster promosso nella completed-list
- README EN+IT status table 4 rows flippate
- Doc-sync memory 4 mapping rows aggiunte

**Pytest finale 805** (baseline 801 + 3 invariant tests +1 N-10 supplementary).

## Develop HEAD

`7a7ab3a` (pin rumor §4.4 frozen-at-commit). Pushato.

## Branch rimanenti dopo rumor-cluster (Spec Kit obbligatorio per ognuno)

3. `<timestamp>-political-cluster-audit-repass` — government + government_types + institutions + stratification + election (22 findings originali)
4. `<timestamp>-movement-audit-repass` — 5 findings
5. `<timestamp>-factions-audit-repass` — 4 findings
6. `<timestamp>-world-economy-deprecation` — legacy MVP placeholder

Post-campagna: Demography Plan 4 (engine wiring) + validation experiments execution. Tutto via Spec Kit.

## Lessons learned (per future Spec Kit features)

1. **Spec Kit canonical path è `specs/<branch>/`**, NON `.specify/specs/<branch>/`. Documentato in CLAUDE.md, constitution, feedback_speckit_mandatory, project_session_resume.

2. **Round 1 doc-only fixes spesso lasciano problemi sostanziali**. Word-boundary regex collision (`avoid`/`avoid_conception`) era una regressione introdotta da N-1 fix — caught da implementer's self-review, fixato in patch commit successivo. Sempre fare grep/runtime check dopo extending tabelle parametri.

3. **Cross-module verify-before-asserting** è critico: vocabulary mismatch tra `_IMAGE_DELTAS` (reputation.py) e `_POSITIVE_KEYWORDS`/`_NEGATIVE_KEYWORDS` era invisibile a single-module audit; emerso solo da Round 2 cross-module analysis.

4. **Pattern di promotion confermato** (procedure in `project_whitepaper_promotion_pipeline.md`): §8.x rimosso + renumbered, §4.x nuovo capitolo con canonical Methods schema, README status, doc-sync mapping, IT mirror, frozen-at-commit pin post-merge.

5. **Spec Kit `/speckit-plan` non è invocabile via Skill tool** — è una procedura documentata da seguire inline. Run `.specify/scripts/bash/setup-plan.sh --json` poi fillare il template.

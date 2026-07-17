---
name: session-resume-2026-06-22
description: "READ FIRST. Ruff repo-wide cleanup CHIUSO (PR#10, merge ed5e9e1). CI lint gate ora VERDE su develop. Resta Branch 6 (world economy deprecation, ultimo F-CAMPAIGN) + factions Round 3 hardening + post-campagna Demography Plan 4."
metadata: 
  node_type: memory
  type: project
  originSessionId: c0fe38ea-15e1-44b8-8624-3d4503b5a8f2
---

# Sessione 2026-06-22 — Ruff repo-wide cleanup CHIUSO

## STATUS: ruff cleanup completo e mergiato in develop. develop HEAD = ed5e9e1.

## Cosa fatto questa sessione

Nuovo work item via Spec Kit completo (fasi 1-7): `specs/20260622-152915-ruff-repo-wide-cleanup/`.

- Obiettivo: gate CI lint da rosso a verde. Era `ruff check .` exit 1 (1183 errori/150 file) + `ruff format --check .` 212 file.
- Risultato: **`ruff check .` e `ruff format --check .` exit 0 su develop**, pytest 809 invariato, zero behavior change.
- PR#10 mergiato in develop, merge SHA `ed5e9e1626e2022f993471f348c9d14477e3692d`. Niente frozen-pin (no whitepaper toccato).
- Dettagli completi in [[ruff-cleanup-pending]] (ora CLOSED).

Gate heavy fase 2 (spec) + fase 6 (review avversariale) chiusi con approvazione utente. Light gate fase 3+4 confermati. Decisioni utente upfront: line-length 100, format-all, naming noqa-con-rationale su scientifico.

## DA FARE — prossime sessioni (ordine consigliato)

### 1. Branch 6 — world economy deprecation (ULTIMO F-CAMPAIGN)

`<timestamp>-world-economy-deprecation` via Spec Kit. `epocha/apps/world/economy.py` legacy MVP placeholder. Decisione: deprecate o re-audit? Default = deprecation procedure documentata in [[audit-repass-batch-2026-04-12-pending]]. Chiude la campagna F-CAMPAIGN (6/6).

### 2. factions Round 3 hardening spec

`specs/<timestamp>-factions-round3-hardening/` via Spec Kit. Scope = i 5 deferred behavioral catalogati a chiusura factions: NEW-1 biased member sample, NEW-7 transaction.atomic su _check_schism/_create_faction, NEW-8 agent migration discipline, NEW-10 docstring-vs-sample, NEW-12/13 N+1. Tracciabili via factions.py Known Limitations bullet (f). Behavioral -> richiede regression test. Stima 30-40 task.

### 3. Post-campagna

- Demography Plan 4 (engine wiring mortality/fertility/couple in simulation/engine.py) -- vedi [[demography-plan2-complete]]
- Validation experiments execution -- vedi [[validation-experiments-pending]]

## F-CAMPAIGN progress

| # | Branch | Status | PR | Merge |
|---|--------|--------|----|-------|
| 1 | Reputation | CHIUSO | PR#5 | c196281 |
| 2 | Rumor cluster | CHIUSO | PR#6 | a0ea075 |
| 3 | Political cluster | CHIUSO | PR#7 | dfeb709 |
| 4 | Movement | CHIUSO | PR#8 | c543c10 |
| 5 | Factions | CHIUSO | PR#9 | 5406b95 |
| 6 | World economy deprecation | PENDENTE (ultimo) | -- | -- |

Whitepaper §4: 7 capitoli auditati (4.1-4.7). §8 residuo: 8.1 Knowledge Graph, 8.2 Economy base layer.

Side work (fuori F-CAMPAIGN): ruff cleanup CHIUSO (PR#10).

## NOTE tecniche ambiente

- `gh` aliasato a `git hist` nella shell: usare `/opt/homebrew/bin/gh` per comandi GitHub.
- Spec Kit: `create-new-feature.sh` ha un bug bashism (`${word^^}` sotto sh) che fa cadere su numbering sequenziale invece di timestamp. Workaround: dopo lo script, rinominare branch+dir a `<YYYYMMDD-HHMMSS>-<slug>` e aggiornare `.specify/feature.json`. (Fix permanente dello script: work item separato se desiderato.)
- Merge target campagna = develop. Release in main = PR develop->main separato.
- Docker `docker-compose.local.yml`; pytest `exec -T web pytest`; baseline 809. Container ruff 0.15.11 (authority, non host).
- ruff cleanup lessons: format DOPO line-length; auto-fix F401 puo' rompere re-export (check collection pytest); per prompt LLM preferire per-file-ignore E501 a restructure.

## Spec Kit absolute rule attiva

Branch 6 e factions Round 3 = nuovi `specs/<timestamp>-<slug>/`. Niente legacy `docs/superpowers/`.

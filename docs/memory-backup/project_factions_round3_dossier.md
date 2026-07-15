---
name: factions-round3-dossier
description: "Dossier di investigazione (2026-07-15) per la spec factions Round 3 hardening -- i 5 finding deferred verificati contro il codice corrente, tutti ANCORA PRESENTI, con file:line, test coverage e una correzione alla stima query di NEW-12."
metadata: 
  node_type: memory
  type: project
  originSessionId: 858a67ce-53c0-401c-90dd-a7785c88e106
---

# Factions Round 3 hardening -- dossier requisiti (verificato 2026-07-15)

Input per la spec `specs/<timestamp>-factions-round3-hardening/` (da creare via Spec Kit). Verifica fatta su codice corrente (`epocha/apps/agents/factions.py`, 997 righe; entry point `process_faction_dynamics` invocato da `simulation/engine.py:490`). Tutti e 5 i finding del Round 2 factions (2026-05-16) sono ANCORA PRESENTI, nessuno risolto nel frattempo.

## NEW-1 -- campione membri biased (Medium)

`_check_join_existing_groups`, `factions.py:753`: `Agent.objects.filter(group=group, is_alive=True)[:5]` con ordinamento default per PK -- campione stabile ma non rappresentativo per gruppi longevi. Nessun test unitario isola il sampling.

## NEW-7 -- manca transaction.atomic (High)

`_check_schism` (righe 603-644: crea Group, aggiorna alleati con save() per-agent, elegge leader, aggiorna coesione, crea Memory) e `_create_faction` (righe 889-930: crea Group, set leader, aggiorna founders, bulk_create Memory): mutazioni multi-tabella senza wrapper transazionale. Race condition analoga a reputation N-11 (Branch 1). Nessun test di concorrenza esistente.

## NEW-8 -- disciplina migrazione agenti incoerente (Medium)

`_check_dissolution:515` usa `Agent.objects.filter(group=group).update(group=None)` (bulk, NO segnali) mentre `_check_schism:618`, `_create_faction:908`, `_process_formation_decisions:827` usano `agent.save(update_fields=["group"])` per-agent (segnali attivi). Policy da unificare, in qualunque direzione, con rationale.

## NEW-10 -- docstring vs implementazione (Low, dipende da NEW-1)

`_check_join_existing_groups` docstring (righe 735-744) dice "average affinity with the first 5 group members" senza dichiarare che "first" = PK ascendente (il bias di NEW-1). Fix docstring O implementazione, coerente con la scelta su NEW-1.

## NEW-12/13 -- N+1 (High)

- NEW-12 `_check_join_existing_groups:756`: loop annidato 50 agenti x 5 gruppi x 5 membri con `compute_affinity` per cella. ATTENZIONE: la stima audit originale (1250 computazioni) SOTTOSTIMA le query -- `compute_affinity` (`affinity.py:62-92`) fa ~3 query per chiamata (`_relationship_score` 1-2 + `_circumstance_score` 2 su Memory, righe 214-229) => ~3750 query/tick.
- NEW-13 `compute_legitimacy:310` chiama `compute_leadership_score` per ogni membro, e `compute_leadership_score:209` RI-fetcha tutti i membri del gruppo a ogni chiamata (N+1 su Agent) piu' Relationship (224-227) e Memory (242-249) per membro. Chiamato da `update_group_leadership:446` per ogni gruppo per tick.

## Test coverage attuale (gap)

`epocha/apps/agents/tests/test_factions.py`: TestLeadershipScore (compute_leadership_score diretto), TestLeadershipContestaton (update_group_leadership). NESSUN test per `_check_join_existing_groups`, `_check_dissolution`, `_check_schism`, `_create_faction`; zero assertion su query count; zero test di concorrenza. Il Round 3 e' behavioral => regression test obbligatori per ogni fix (regola campagna).

## Vincoli di design noti

- `Agent.group` FK nullable verso Group; `Group.leader` FK nullable verso Agent; nessun constraint DB che prevenga stati intermedi invalidi (rilevante per NEW-7).
- Fix N+1: preferire prefetch/annotate e batching di `compute_affinity` (le query Relationship/Memory interne sono il vero moltiplicatore); vedi regola query performance in CLAUDE.md globale.
- Stima piano: 30-40 task (da session resume 2026-06-22), spec via Spec Kit con heavy gate fase 2.

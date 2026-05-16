---
name: session-resume-2026-05-16-political
description: READ FIRST. Branch 3 political-cluster in flight. Spec Kit docs authored (spec+plan+research+tasks). Round 2 audit DONE — NOT CONVERGED, 13 findings (4 Major + 6 Minor + 3 PARTIAL R1). Nessun fix applicato. Riprendere da fix-implementer.
type: project
originSessionId: b165274d-a708-4e8c-abed-b28a018c163f
---

# Sessione 2026-05-16 (parte 2) — Branch 3 political-cluster

## STATUS

Branch creato e Spec Kit docs autorate. Round 2 audit eseguito. NESSUN fix applicato. Stop per limiti context.

## Branch state

- Branch: `20260516-120927-political-cluster-audit-repass`
- HEAD: `b63423a` (commit tasks.md)
- 3 commit ahead develop:
  - `9c10ce8` — spec.md (215 lines, 25 FR, 4 user stories)
  - `31e242f` — plan.md + research.md
  - `b63423a` — tasks.md (56 tasks)
- Working tree pulito
- Spec Kit conformante (`specs/20260516-120927-political-cluster-audit-repass/`)
- Pytest baseline 805 confermato

## Round 2 audit verdict: NOT CONVERGED — 13 findings

### Round 1 status (20 original findings)

- **CLOSED 17**: G-1, G-2, G-3, G-4, G-5, GT-1, S-1, S-3, S-4, E-1, E-2, E-3, E-4, E-5, I-1, I-2, I-3
- **PARTIAL 3**: G-6 (naming `economy` ancora misleading), S-2 (arithmetic ok ma no @transaction.atomic), X-1 (composition documented ma saturation envelope non testato)

### Round 2 new findings (13)

**Major (4)**:
- **N-1**: `_COUP_SUCCESS_THRESHOLD = 0.50` ancora definito a `government.py:85` con docstring "no longer used". Delete o rename.
- **N-2**: **CITATION DRIFT MASSICCIO** — §13 whitepaper EN+IT manca ~20 di ~26 citazioni della cluster politica. Solo Acemoglu-Robinson 2006 e Powell-Thyne 2011 presenti. Missing: Weber 1922, Bass 1985, Merolla-Zechmeister 2011, Miller-Lynam 2001, Bueno de Mesquita 2003, Geddes 1999, Gilbert 2011, Lewis-Beck-Stegmaier 2000, Levitsky-Way 2010, Caprara 2006, Huckfeldt-Sprague 1987, Lodge-Steenbergen-Brau 1995, Kahneman-Tversky 1979, Rose-Ackerman-Palifka 2016, Besley-Persson 2011, Freedom House, Polity IV (Marshall-Gurr 2020), Linz 2000, Arendt 1951, Winters 2011, Cronin 2009, Riker 1964, Fish 2002, Finer 1962, Hobbes 1651, Kalyvas 2006. **P1 blocker per §4.5 promotion**.
- **N-3**: `process_corruption` (`stratification.py:191`) NO `@transaction.atomic`. Crash mid-funzione → wealth creato dal nulla. Fix: aggiungere decorator + import.
- **N-4**: FR-021 invariant test file `epocha/apps/world/tests/test_political_invariants.py` NON esiste. Spec richiede `test_corruption_preserves_total_wealth`, `test_coup_threshold_constant_deprecated`, `test_economy_proxy_documented`.

**Minor (6+3)**:
- **N-5**: `election.py:100` inline `(reputation_raw + 1.0) / 2.0` invece di `_normalize_reputation` helper di Branch 1.
- **N-6**: Race condition pattern (analogo reputation N-11): `government.corruption` doppio write senza `select_for_update`. Fix: `select_for_update` su `process_political_cycle` start.
- **N-7**: `government.py:658-663` Bueno de Mesquita 2003 Ch.3 cited per weighted-sum stability formula — selectorate non discute weighted sum. Soften docstring.
- **N-8**: `government.py:54-57` repression drift Freedom House cited come source — annual indices, non per-tick rates. Apply G-3 treatment.
- **N-9**: `stratification.py:50-54` corruption skim Transparency CPI cited — perceptions composite, non quantitative per-period rate. Soften.
- **N-10**: `government.py:68-73` media independence + propaganda factor Freedom House Press Freedom methodology cited — composite 0-100, non derivable. Soften.
- **N-11**: `government.py:498-499, 638-639` bare `except Exception` su expropriation — CLAUDE.md vieta. Replace con `except (ImportError, Economy.DoesNotExist)`.
- **N-12**: `institutions.py:96-104` per-row `save()` in loop. Replace con `bulk_update(institutions, ["health"])`.
- **N-13**: Coup candidate selection bias — per-faction roll con score-tiebreak ignora ranking. Document or randomize.

### PARTIAL Round 1 (3)

- **G-6**: doc ok ma variabile locale ancora `economy` (non `economy_proxy`). Decisione: rename O test invariant.
- **S-2**: arithmetic ok, no transaction guard (vedi N-3), no invariant test (vedi N-4). Strettamente legato a N-3+N-4.
- **X-1**: composition documented ma cumulative-clamp saturation non testata. Add invariant test O document silent-saturation.

## Minimum convergence path (~12-15 task)

1. Delete `_COUP_SUCCESS_THRESHOLD` (N-1)
2. Add `@transaction.atomic` to `process_corruption` (N-3 + S-2 transactional)
3. Create `test_political_invariants.py` con 3 test (N-4 + S-2 test + G-6)
4. Add ~20 §13 entries a EN+IT whitepapers (N-2) — group by author cluster: regime typology, voting, corruption, charisma, mobility, institutions
5. Migrate election.py reputation normalization to helper (N-5) — 2 line patch
6. Guard process_political_cycle con select_for_update (N-6)
7. Soften 4 docstring citations (N-7, N-8, N-9, N-10)
8. Replace bare `except Exception` (N-11)
9. Convert institutions.py per-row save to bulk_update (N-12)
10. Document coup selection bias o randomize iteration (N-13)
11. Decide G-6 final (rename `economy` o explicit assertion)
12. Document X-1 saturation o add invariant test

## Da fare nella ripresa (immediato)

1. `git checkout 20260516-120927-political-cluster-audit-repass`. HEAD `b63423a`.
2. Dispatch fix-implementer Opus con i 13 findings sopra. Strategia ordine: prima Major (N-1..N-4), poi PARTIAL R1 (G-6, S-2 vedi N-3+N-4, X-1), poi Minor (N-5..N-13). Pytest gate dopo blocchi.
3. **N-2 strategia**: aggiungere 20 §13 entries in batches:
   - Batch A regime typology: Geddes 1999, Linz 2000, Levitsky-Way 2010, Bueno de Mesquita 2003, Polity IV (Marshall-Gurr 2020), Freedom House
   - Batch B charisma/leadership: Weber 1922, Bass 1985, Merolla-Zechmeister 2011
   - Batch C voting: Caprara 2006, Huckfeldt-Sprague 1987, Lewis-Beck-Stegmaier 2000, Lodge-Steenbergen-Brau 1995, Riker 1964
   - Batch D corruption/state: Rose-Ackerman-Palifka 2016, Miller-Lynam 2001, Besley-Persson 2011, Cronin 2009, Kalyvas 2006
   - Batch E mobility/equality: Gilbert 2011, Kahneman-Tversky 1979 (gia' presente probabilmente), Arendt 1951, Hobbes 1651, Winters 2011, Fish 2002, Finer 1962
   - Verificare DOI Crossref dove possibile prima di committare
4. Round 3 audit dopo fix
5. Loop fino CONVERGED
6. Promote §8.1 → §4.5 EN+IT (5 sub-sections: 4.5.1 Government, 4.5.2 Government types, 4.5.3 Institutions, 4.5.4 Stratification, 4.5.5 Election)
7. README + memory + pytest + PR + merge + frozen-pin

## Develop HEAD

`1c75854` (post-Branch 2 rumor closure + memory sync).

## Branch rimanenti dopo political-cluster

4. `<timestamp>-movement-audit-repass` — 5 findings
5. `<timestamp>-factions-audit-repass` — 4 findings
6. `<timestamp>-world-economy-deprecation` — legacy MVP placeholder

Post-campagna: Demography Plan 4 + validation experiments execution. Tutto via Spec Kit.

## Lessons learned this session

1. **Round 2 audit cattura sempre molte più issue del previsto**. Branch 2: 16 findings vs 5 originali. Branch 3: 13 nuovi + 3 PARTIAL R1 (totale ~16 vs 20 originali — alcuni R1 già fissati). Plan task count estimate va corretto verso alto durante audit.

2. **§13 citation gap è molto più ampio del previsto** per ogni cluster. Branch 2 = 4 missing; Branch 3 = ~20 missing. Hypothesis: tutti i cluster con audit pre-policy (movement, factions) avranno gaps simili. Quando si scrive spec.md prossima volta, includere upfront un comprehensive grep di tutte le citation in body vs §13.

3. **Spec Kit canonical path = `specs/` non `.specify/specs/`** — già documentato in memorie.

4. **Branch 1 helper `_normalize_reputation` non era stato applicato cross-cluster** (election.py ancora inline duplicate). Cross-module DRY enforcement debole.

5. **Bare `except Exception` ancora sparso nel codice politico** — pattern da grep per future branch.

6. **Race conditions multi-tick concorrenza Celery** sistematiche — reputation N-11 chiuso, government.corruption ancora aperto, da grep simili pattern in altri moduli.

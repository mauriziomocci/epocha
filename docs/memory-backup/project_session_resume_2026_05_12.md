---
name: session-resume-2026-05-12
description: READ FIRST. Campagna audit re-pass batch 2026-04-12 in corso. Branch 1 (Reputation) CHIUSO e mergato. Branch 2 (Rumor cluster) creato, Round 2 audit eseguito (16 findings NOT CONVERGED), nessun fix ancora applicato. Riprendere da fix-implementer del Round 2 rumor.
type: project
originSessionId: b165274d-a708-4e8c-abed-b28a018c163f
---
# Sessione 2026-05-12 -- F-CAMPAIGN audit re-pass IN CORSO

## STATUS: CAMPAGNA IN CORSO. Stop richiesto dall'utente per riprendere domani.

## Stato develop

**HEAD develop**: `b859ee5` (pin reputation §4.3 frozen-at-commit)
**Branch attivo locale**: `audit-repass/rumor-cluster` (working tree clean, ZERO commit dopo creazione branch)
**Push su origin**: il branch rumor-cluster non e' ancora pushato (no commit)

## Cosa abbiamo fatto in questa sessione

### Branch 1 -- Reputation: COMPLETATO

PR #5 mergata su develop con commit merge `c196281`, frozen-at-commit pinnato in `b859ee5`. Branch deleted local+remote.

Round 2 audit ha trovato 11 findings (10 actionable + 1 verified), inclusi:
- N-11 race condition concorrenza Celery su `update_image`/`update_reputation`
- N-3 loudest-keyword-wins bias in `extract_action_sentiment`
- N-6 silent under-coverage di 8/17 action types nell'`_IMAGE_DELTAS`
- N-5 + R3-1 DRY violation 0.6/0.4 weights duplicati in models.py + reputation.py + decision.py
- N-1 docstring citava range 2:1-3:1 ma valori violavano (5.33:1)
- 5 nuove citazioni aggiunte a §13 (Diamond 1989, Greif 1993, Josang-Ismail 2002, Karlan 2005, Sabater-Sierra 2002)
- Nuovo capitolo §4.3 Reputation EN+IT
- Nuovi `_LOAN_DEFAULT_OBSERVER_SENTIMENT`/`_LOAN_DEFAULT_LENDER_SENTIMENT` constants in reputation.py importati da credit.py

Pytest finale: **801 passed**, 0 failed.

### Branch 2 -- Rumor cluster: AUDIT FATTO, FIX NON ANCORA APPLICATI

Branch `audit-repass/rumor-cluster` creato da develop. Round 2 adversarial audit eseguito su:
- `epocha/apps/agents/information_flow.py`
- `epocha/apps/agents/distortion.py`
- `epocha/apps/agents/belief.py`
- `epocha/apps/agents/affinity.py`

Verdetto: **NOT CONVERGED -- 16 findings da risolvere**.

## 16 findings Round 2 rumor cluster (DA APPLICARE alla ripresa)

### Round 1 follow-up findings (5 unfixed/partial)

**IF-1 UNJUSTIFIED** -- Granovetter (1973) cited but NOT implemented in `_propagate_memory`. Whitepaper §8.1 still claims "three families" of literature (Allport-Postman + Bartlett + Granovetter) but Granovetter's tie-strength weighting is absent. Fix: rimuovere claim "tre famiglie" da §8.1 OR implementare differential propagation.

**IF-4 UNJUSTIFIED** -- `_estimate_hop` ancora assume initial reliability=1.0; bias propagazione documentato ma NON fixato. Fix raccomandato dal piano (track explicit `hop_count` su Memory model) NON applicato. Decisione: aggiungere `hop_count` PositiveSmallIntegerField su Memory + migration, oppure documentare definitivamente come limitazione accettata.

**IF-5 INCORRECT** -- Phase 4 public-event dedup in `information_flow.py:141-159` swallow silently due distinct events stesso tick stesso agente (lookup non include `content`/`event_id`). NOT FIXED, motivato con commento ipotetico. Fix: aggiungere `event_id` o content_hash al lookup; aggiungere test invariante.

**D-1 INCONSISTENT** -- Module docstring `distortion.py:11-15` dice "only assimilation implemented" ma inline pattern comments alle linee 43, 97 ancora attribuiscono a "sharpening". Contraddizione interna da riconciliare.

**D-4, D-5 UNJUSTIFIED** -- High-openness pattern accumulation e low-conscientiousness anonymizing of non-person proper nouns: documentato come limitazione, behavior inalterato. Decisione: limitare regex (es. solo prima frase per openness) OR pattern-position restriction (es. solo dopo verbi relazionali per conscientiousness) OR accettare come known limitations definitive.

### New Round 2 findings (11)

**N-1 INCORRECT (cross-module reputation+information_flow)** -- Action vocabulary mismatch tra `_IMAGE_DELTAS` (reputation.py) e `_POSITIVE_KEYWORDS`/`_NEGATIVE_KEYWORDS`. Direct memories `"I decided to {action_type}. {reason}"` per azioni come `pair_bond`, `separate`, `borrow`, `form_group`, `protest`, `hoard`, ecc. hanno entry in `_IMAGE_DELTAS` (image direct fires) ma NON in keyword tables -> `extract_action_sentiment` returns 0.0 -> reputation update via hearsay viene skippato silenziosamente. Castelfranchi-Conte-Paolucci dual-track e' broken in half. Fix: aggiungere ai keyword tables OR rewrite `_propagate_memory` per parsing structured action_type. Test invariante: per ogni key in `_IMAGE_DELTAS` non-zero, `extract_action_sentiment` di `f'I decided to {key}. reason'` deve avere stesso segno.

**N-2 INCONSISTENT (whitepaper §13)** -- 4 citation in body senza §13 entry:
- Mayer, Davis & Schoorman (1995) -- DOI 10.5465/amr.1995.9508080335
- Graziano & Tobin (2002) -- DOI 10.1111/1467-6494.05021
- Castelfranchi, Falcone & Tan (1998) -- HICSS-31 proceedings IEEE
- McCrae & Costa (2003) -- Guilford ISBN 1-57230-827-1

Fix: aggiungere a §13 EN+IT. Verificare DOI via Crossref prima di committare.

**N-3 INCORRECT (cross-module distortion+reputation)** -- Distortion-induced reputation drift. `_propagate_memory` distorts content first (linea 232) THEN extracts sentiment from distorted content (linea 236). High-neuroticism transmitter "argued" -> "fought bitterly" cambia sentiment -0.5 -> -0.7. Cumulative drift biases reputation in direzione personality bias del transmitter. Fix: spostare `extract_action_sentiment(memory.content)` PRIMA della distortion pass. Test invariante: reputation delta su hearsay dipende da source action, non da transmitter personality.

**N-4 INCONSISTENT (distortion)** -- First-pattern-wins-by-source-order in `_apply_patterns:218-222`. Per high-neuroticism patterns ordinati come `argued, disagreed, criticized, ...`, "Marco disagreed and argued con Elena" matcha `argued` per primo (perche' dichiarato per primo) lasciando `disagreed` non distorto. Stesso pattern bias di N-3 reputation loudest-keyword. Fix: pattern ordering by linguistic salience OR document deliberate source-order assumption OR match-all-pick-strongest.

**N-5 UNJUSTIFIED (belief+models)** -- Inline reputation normalization in `belief.py:81-85` duplicato da `ReputationScore.get_combined_score_normalized()`. Misleading comment "should migrate to centralized method" -- impossibile letteralmente perche' `should_believe` accetta float non instance. Fix: estrarre `_normalize_reputation(raw: float) -> float` in reputation.py, chiamare da entrambi.

**N-6 UNJUSTIFIED (information_flow)** -- Magic numbers `emotional_weight=0.1` e `reliability=new_reliability * 0.3` in lines 311, 313 (weak-rumor block). Fix: promuovere a settings `EPOCHA_INFO_FLOW_WEAK_RUMOR_WEIGHT`, `EPOCHA_INFO_FLOW_WEAK_RUMOR_DAMP`.

**N-7 UNJUSTIFIED (affinity)** -- `_personality_similarity` docstring (linee 100-103) dice "missing traits contribute zero" ma e' falso quando solo UN agente ha trait missing (default 0.5 vs altro 0.9 = (0.4)^2 = 0.16). Fix: rewrite docstring per descrivere correttamente comportamento asimmetrico.

**N-8 UNJUSTIFIED (affinity)** -- `_relationship_score` `MultipleObjectsReturned` con `order_by("-strength").first()` in linee 153-162 picks strongest record regardless of relation_type. Caso friendship+rivalry: rivalry vince. Olson 1965 cited a livello modulo non copre dyadic rival-coalition dynamics. Fix: cite Coleman 1990 o Axelrod 1984 OR mark as tunable design heuristic.

**N-9 UNJUSTIFIED (information_flow)** -- Phase 2 (hearsay->rumor) in linee 92-111 SKIP threshold mentre Phase 1 in linee 71-91 enforces. Asimmetria undocumented; mina design intent "prevents trivial observations from flooding network". Fix: applicare threshold a tutte le fasi OR documentare asimmetria esplicitamente.

**N-10 INCONSISTENT (tests)** -- Test coverage gaps per Round 1 invariants (IF-4, IF-5, D-4, D-5) e Round 2 (N-1, N-3, N-4). Reputation cluster ha invariant test (`tests/test_reputation.py:test_negativity_bias_qualitative_direction` commit `01ac4ad`). Rumor cluster non lo ha. Fix: aggiungere `tests/test_rumor_invariants.py` con un test per finding (skip-marked se behavior accettato ma undocumented; failing se bug).

## Riepilogo per ripresa

Severita' totali: **3 INCORRECT (IF-5, N-1, N-3) + 9 UNJUSTIFIED (IF-1, IF-4, D-4, D-5, N-5, N-6, N-7, N-8, N-9) + 4 INCONSISTENT (D-1, N-2, N-4, N-10) + 11 VERIFIED**.

Per la promozione §8.1 -> §4.4 servono almeno: IF-5, N-1, N-3, D-1, N-2, N-4, N-10 risolti (i 3 INCORRECT + 4 INCONSISTENT). Le UNJUSTIFIED possono essere documentation upgrades.

Cross-module touch points: reputation.py + models.py + simulation/engine.py + tests/test_*.py + whitepaper.md + .it.md.

## Da dove riprendere domani

1. **Verifica stato branch**: `git checkout audit-repass/rumor-cluster && git status`. Atteso: working tree clean, 0 commit dopo creazione (ripresa pulita).
2. **Dispatch fix-implementer Opus** con i 16 findings sopra. Strategia lowest-risk simile a Reputation:
   - Documentation-only fixes per IF-1 (rimuovere "tre famiglie" da whitepaper §8.1 testualmente, **non** implementare Granovetter come behavioral change in questa branch)
   - IF-4: documentare definitivamente come known limitation accettata (NO migration `hop_count` -- scope creep)
   - IF-5: behavioral fix (aggiungere `event_id` al lookup)
   - D-1: riconciliare comments inline
   - D-4, D-5: documentare definitivamente come known limitations
   - N-1: aggiungere ai keyword tables (low-risk batch)
   - N-2: aggiungere 4 entries a §13 EN+IT
   - N-3: behavioral fix (spostare extract_action_sentiment prima di distortion)
   - N-4: documentare design choice
   - N-5: extract `_normalize_reputation` helper
   - N-6: settings extraction
   - N-7, N-8: docstring fixes / mark as tunable
   - N-9: documentare asimmetria
   - N-10: aggiungere `tests/test_rumor_invariants.py` con almeno N-1 e N-3 invariants
3. Loop fino a CONVERGED (probabilmente 1-2 round addizionali).
4. Promote §8.1 -> §4.4 EN+IT (4-sub-section chapter: information_flow + distortion + belief + affinity).
5. Update README EN+IT status table per i 4 moduli.
6. Update doc-sync mapping memory per i 4 paths.
7. Pytest gate.
8. PR + merge + frozen-at-commit pin.

## Stato memoria altri follow-up

- `project_audit_repass_batch_2026_04_12_pending.md` -- Branch 1 (Reputation) gia' fatto. Aggiornare alla chiusura della campagna intera.
- `project_validation_experiments_pending.md` -- invariato.
- `feedback_whitepaper_doc_sync.md` -- aggiunto mapping reputation §4.3. Aggiungere mapping rumor §4.4 alla chiusura del Branch 2.
- `project_whitepaper_promotion_pipeline.md` -- procedura applicata con successo per reputation, valida.
- Plan 2026-05-12-audit-repass-campaign.md sotto `docs/superpowers/plans/` -- guida operativa.

## Branch rimanenti dopo Branch 2

3. `audit-repass/political-cluster` -- government + government_types + institutions + stratification + election (22 findings originali)
4. `audit-repass/movement` -- 5 findings originali
5. `audit-repass/factions` -- 4 findings originali
6. `audit-repass/world-economy-deprecation` -- 4 findings -> deprecation procedure

Dopo campagna: Demography Plan 4 (wiring nel tick loop) + validation experiments execution. User ha esplicitamente richiesto "tutto" sequenziale.

## Pytest baseline

801 passed (post-Branch 1 reputation con +1 invariant test).

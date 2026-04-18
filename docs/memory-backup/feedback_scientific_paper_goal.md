---
name: scientific-paper-goal
description: Il progetto Epocha produrra' un paper scientifico a fine lavoro -- ogni scelta deve essere documentata a livello di rigore publication-grade
type: feedback
originSessionId: f9bc7a55-71c4-45ed-9602-f5e328a6175e
---
# Paper scientifico come outcome del progetto

**Regola**: ogni scelta di design, modello, parametro, formula o algoritmo in Epocha deve essere documentata con rigore publication-grade, perche' alla fine del progetto verra' prodotto un paper scientifico sulla qualita' del lavoro.

**Why**: l'utente ha dichiarato esplicitamente il 2026-04-18 che il deliverable finale include un paper scientifico che giustifica la bonta' del progetto. Ogni decisione oggi e' un'evidenza citabile domani. Documentazione incompleta oggi = sezione debole del paper domani.

**How to apply**:
1. Ogni spec (spec di design, FAQ, audit resolution log) deve includere:
   - Riferimenti bibliografici completi (autore, anno, titolo, journal/publisher) per ogni claim scientifico
   - Confronto esplicito con alternative considerate e motivazione della scelta
   - Parametri con fonte o marcati esplicitamente "tunable design parameter"
   - Limiti noti e trade-off documentati
2. Ogni commit su modelli scientifici deve avere commenti nel codice con citazione alla fonte (gia' in CLAUDE.md)
3. Ogni brainstorming deve produrre un audit trail delle decisioni prese (quale opzione, perche', cosa e' stato scartato)
4. I template scenario-era dichiarano esplicitamente le fonti dei parametri calibrati (es. "pre-industrial mortality da Wrigley & Schofield 1981")
5. Al termine di ogni spec: verificare che un lettore esterno (reviewer) possa valutare scientificamente ogni scelta senza chiedere chiarimenti.

Il paper a fine progetto dovra' poter citare ogni modulo di Epocha come "implementazione documentata e verificata di [modello scientifico] con parametri da [fonte]", con audit trail avversari (adversarial audit) che dimostrano la qualita' della verifica.

Questa regola si combina con:
- GOLDEN RULE (metodo scientifico sopra tutto)
- Verify Every Assertion
- Adversarial Scientific Audit
- Every Spec Includes FAQ

Ma la eleva: non basta essere scientificamente corretti, bisogna essere scientificamente *documentati per pubblicazione*.

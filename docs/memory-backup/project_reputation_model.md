---
name: reputation-model-done
description: Castelfranchi-Conte-Paolucci reputation model implemented (DONE 2026-04-06)
type: project
---

Modello di reputazione implementato il 2026-04-06. Basato su:
- Castelfranchi, Conte & Paolucci (1998) "Normative reputation and the costs of compliance"
- Paolucci, Marsero & Conte (2000) "What is the use of Gossip?"

Il modello richiede:

1. **Nuovo modello ReputationScore** -- holder (FK Agent), target (FK Agent),
   image (float -1 a 1, valutazione diretta), reputation (float -1 a 1,
   valutazione sociale), last_updated_tick.

2. **Image si aggiorna** quando l'agente vive un'interazione diretta (memorie
   "direct" con target). Positiva per help/socialize, negativa per argue/betray.

3. **Reputation si aggiorna** quando l'agente riceve hearsay/rumor su qualcuno.
   L'agente puo' trasmettere reputation senza crederci (il gossip si propaga
   indipendentemente dal belief filter).

4. **Belief filter aggiornato** -- usa reputation del trasmettitore (non solo
   sentiment della relazione) per decidere se credere a un'informazione.

5. **Decisioni aggiornate** -- il contesto include la reputazione degli altri
   agenti. Un agente evita di cooperare con chi ha cattiva reputazione (la
   funzione "tabu" del paper).

6. **Elezioni aggiornate** -- il vote score usa reputation esplicita invece del
   proxy _memory_influence.

**Why:** L'utente ha esplicitamente chiesto rigore scientifico. Il proxy basato
sulle memorie funziona ma non implementa correttamente il modello
Castelfranchi-Conte-Paolucci.

**How to apply:** Brainstorming -> spec -> plan -> implementation. Tocca
belief.py, information_flow.py, decision.py, election.py, e aggiunge un
modello nuovo. Costo: N*N record (20 agenti = 400, 50 = 2500).

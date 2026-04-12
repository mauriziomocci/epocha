---
name: economic-model-realistic
description: Modello economico realistico con economia reale + mercati finanziari, priorita' massima dopo Knowledge Graph
type: project
originSessionId: 0a27799c-3d4b-4995-b144-424ee45e5764
---
L'utente ha confermato il 2026-04-12 la volonta' di implementare un modello
economico completo con due layer sovrapposti:

**Layer 1 -- Economia reale**
Produzione per zona/ruolo, commercio spaziale, domanda/offerta, prezzi di
equilibrio. Riferimenti: modelli CGE (Computable General Equilibrium)
semplificati, economia classica agent-based.

**Layer 2 -- Mercati finanziari**
Asset pricing, speculazione, bolle, contagio finanziario, panico dei
mercati. Con interesse specifico per le principali borse mondiali.
Riferimenti:
- Minsky, H. P. (1986). "Stabilizing an Unstable Economy"
- Shiller, R. J. (2000). "Irrational Exuberance"
- LeBaron, B. (2006). "Agent-based Computational Finance"
- Modelli ABM del Santa Fe Institute (Arthur, 1994; Farmer & Foley, 2009)

**Feedback tra i due layer**: la produzione influenza i mercati, i crash
finanziari impattano l'economia reale, l'instabilita' economica alimenta
l'instabilita' politica (gia' modellata nel sistema di governo).

**Stato attuale**: l'economia e' un placeholder MVP con reddito fisso per
ruolo e costo di vita fisso. Nessun mercato, nessun prezzo, nessuna
domanda/offerta. Il codice e' in `epocha/apps/world/economy.py`.

**Why:** L'utente vuole che Epocha simuli dinamiche economiche realistiche
incluse fluttuazioni di prezzo e panico dei mercati. E' la prossima
feature dopo il completamento del Knowledge Graph.

**How to apply:** Appena il Knowledge Graph e' completato (tutti e 4 i
piani), partire immediatamente con il brainstorming del modello economico
seguendo il ciclo three-step design. L'economia attuale va sostituita,
non estesa: il placeholder e' troppo semplice per reggere un layer
finanziario sopra.

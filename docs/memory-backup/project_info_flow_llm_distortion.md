---
name: info-flow-llm-distortion
description: Future option -- LLM-based distortion engine for information flow, deferred for cost reasons
type: project
---

Per l'Information Flow, l'utente ha scelto distorsione rule-based (C) per pragmatismo.
Opzione ibrida valutata e rinviata: setting switchabile tra rule_based e llm,
con riscrittura LLM via provider chat, batched per trasmettitore, solo su azioni
ad alto impatto emotivo (emotional_weight >= 0.3).

**Why:** Il costo LLM per la riscrittura e' significativo (3-5 chiamate extra per tick
su provider economico, di piu' su free tier). Il rule-based produce distorsione
interessante e testabile a costo zero.

**How to apply:** Quando l'utente chiede di migliorare la qualita' della distorsione
o di aggiungere riscrittura LLM, proporre l'approccio ibrido con setting switchabile.
L'architettura del distortion engine e' gia' disegnata con interfaccia sostituibile.

---
name: feedback-graph-improvement
description: User wants the relationship graph to look as good as MiroFish -- denser, more colorful, integrated dashboard
type: feedback
---

L'utente ha confrontato il nostro grafo con MiroFish (https://github.com/666ghj/MiroFish)
e il loro sembra migliore. Differenze chiave da colmare:

1. **Archi piu' spessi e colorati** -- i nostri sono troppo sottili con pochi dati.
   Aumentare lo spessore minimo e usare colori piu' saturi.
2. **Clustering visivo** -- con piu' agenti e fazioni il layout ForceAtlas-like
   dovrebbe raggruppare naturalmente. Con 15 agenti e' sparso.
3. **Dashboard integrata** -- MiroFish ha il grafo + statistiche + log sulla stessa
   pagina. Il nostro e' su pagine separate. Considerare un layout integrato.
4. **Il grafo migliora con piu' dati** -- la differenza principale e' la quantita'
   di agenti/relazioni, non la tecnologia. Con la Rivoluzione Francese dopo
   50+ tick dovrebbe essere molto piu' ricco.

**Why:** L'utente vuole un risultato visivamente impressionante, non solo
funzionale.

Secondo screenshot MiroFish (运行截图6.png) -- grafo ancora piu' impressionante:
5. **Sfondo chiaro** -- per grafi densi, il bianco fa risaltare nodi e archi
   meglio del dark mode. Considerare un toggle light/dark per il grafo.
6. **Nodi multi-tipo** -- MiroFish ha Entity, Organization, Disaster come tipi
   diversi di nodi. Noi potremmo aggiungere fazioni e istituzioni come nodi
   del grafo (non solo agenti).
7. **Cluster visivi per tipo di relazione** -- archi rossi (conflitto) creano
   un cluster separato. L'effetto e' molto bello con centinaia di nodi.
8. **Densita'** -- il fattore wow viene dalla quantita'. Con 15 agenti non ci
   arriviamo. Ma con 50+ e fazioni/istituzioni come nodi, si'.

**How to apply:** Nella prossima sessione di miglioramento del grafo:
- Aumentare spessore archi e saturazione colori
- Considerare sfondo chiaro come opzione
- Aggiungere fazioni e istituzioni come nodi del grafo
- Considerare layout integrato con statistiche
- Il vero salto di qualita' viene dalla quantita' di agenti/relazioni
- Aggiungere tab nella pagina grafo per viste diverse:
  (a) Relationships -- agenti + relazioni (attuale)
  (b) Factions -- nodi = fazioni, archi = relazioni inter-fazione
  (c) Power -- struttura del potere (governo, istituzioni, catena comando)
  Ispirato ai tab di MiroFish che offrono viste diverse dello stesso dato

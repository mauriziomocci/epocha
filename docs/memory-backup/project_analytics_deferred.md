---
name: analytics-deferred-features
description: Analytics features deferred to future iterations -- branch comparison, pattern detection, temporal zoom, export
type: project
---

Features escluse dalla prima iterazione della dashboard analytics che devono
essere implementate in futuro:

1. **Confronto tra branch** -- grafici sovrapposti che mostrano come la stessa
   societa' evolve diversamente in scenari diversi. Analisi delta. Richiede il
   sistema di branching (fase 3 della roadmap).

2. **Pattern detection automatico** -- il sistema identifica correlazioni
   ricorrenti su piu' simulazioni (es. "ogni volta che Gini > X, entro Y tick
   scoppia una rivolta"). Richiede abbastanza dati storici da piu' simulazioni.
   Le Epochal Crisis con soglie predefinite sono il placeholder funzionale.

3. **Zoom temporale avanzato** -- scala di visualizzazione
   giorni/mesi/anni/decenni/secoli. Il tick e' l'unita' base nella prima
   iterazione. Lo zoom richiede un sistema di risoluzione temporale variabile.

4. **Export dati** -- export dei grafici come immagine, export dei dati come
   CSV/JSON. Utile per analisi esterna.

**Why:** Tutte queste feature sono nel design doc originale (sezione 7 --
Analytics Module) e sono parte della visione completa della psicostoriografia.
Sono state rinviate per pragmatismo, non perche' non servano.

**How to apply:** Quando si lavora su branching (fase 3), includere il confronto
tra branch nella dashboard analytics. Pattern detection e' un progetto a se'.
Zoom temporale si aggancia al sistema di risoluzione variabile del tick engine.
Export e' una feature standalone che puo' essere aggiunta in qualsiasi momento.

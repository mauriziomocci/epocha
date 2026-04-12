---
name: scientific-documentation
description: Ogni feature deve essere accompagnata da documentazione che spieghi il valore scientifico, i modelli usati e le fonti
type: feedback
originSessionId: 0a27799c-3d4b-4995-b144-424ee45e5764
---
Ogni feature di Epocha deve essere documentata in modo che un lettore
esterno (ricercatore, reviewer, investitore, utente avanzato) possa
comprendere il valore scientifico del sistema senza leggere il codice.

**Why:** L'utente ha stabilito il 2026-04-12 che tutto il lavoro
scientifico deve essere documentato per comunicare il valore di Epocha.
Il progetto non e' solo codice: e' un contributo alla simulazione
sociale computazionale. Se il rigore scientifico non e' visibile e
spiegato, non ha valore comunicativo.

**How to apply:**
- Ogni spec include una sezione "Scientific Foundations" con citazioni
  complete (autore, anno, titolo, editore/journal)
- Ogni spec include una FAQ che spiega il perche' di ogni scelta
- Il file docs/letture-consigliate.md viene aggiornato con ogni nuova
  fonte aggiunta al progetto
- I docstring dei moduli citano le fonti direttamente nel codice
- Alla fine di ogni macro-feature (economia, Knowledge Graph, ecc.)
  aggiornare un documento di overview che sintetizzi i modelli usati,
  le assunzioni fatte, i limiti noti, e le fonti per chi vuole
  approfondire
- Lo stile della documentazione e' accademico-divulgativo: rigoroso
  ma comprensibile, non jargon-only

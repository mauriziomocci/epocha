---
name: extensible-architecture
description: Ogni sistema deve essere progettato per estensione futura senza riscrittura del codice esistente
type: feedback
originSessionId: 0a27799c-3d4b-4995-b144-424ee45e5764
---
Ogni modulo di Epocha deve essere aperto ad aggiunte e modifiche future
senza richiedere riscritture del codice esistente.

**Why:** L'utente ha stabilito il 2026-04-12 durante il brainstorming
del modello economico che il sistema deve restare sempre aperto a
nuove categorie, nuovi meccanismi, nuovi tipi di dati. Epocha simula
qualsiasi cosa, dal neolitico alla galassia di Asimov: non si puo'
prevedere in anticipo cosa servira'. Confermato come principio
permanente, non solo per l'economia.

**How to apply:**
- Tipi di beni, fattori produttivi, strumenti finanziari: definiti in
  configurazione (JSON/DB), mai hardcoded in Python
- Nuove categorie si registrano tramite configurazione, non modifica codice
- Interfacce tra moduli definite in modo che nuovi componenti possano
  inserirsi senza alterare quelli esistenti (Open/Closed Principle)
- I template economici per era sono configurazioni, non classi separate
- I modelli Django usano JSONField per attributi estensibili dove
  la struttura puo' variare tra scenari
- Test parametrizzati che funzionano con qualsiasi configurazione,
  non solo con i valori hardcoded di un singolo scenario

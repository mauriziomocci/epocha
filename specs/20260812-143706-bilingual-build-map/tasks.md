# Tasks — Build map bilingue

Ordine e numerazione seguono `plan.md`. Ogni voce chiusa porta il commit.

## Fase 1 — Struttura

- [x] **1.1** Script di trasformazione: legge il file, avvolge ogni nodo di testo traducibile in una coppia `<span data-k data-lang>`, chiave derivata dalla posizione strutturale. Non tocca gli esenti di FR-003a.
- [x] **1.2** Selettore: CSS che mostra `it` a riposo e `en` sotto `[data-lang-sel="en"]`, bottone, persistenza in `try/catch`.
- [x] **1.3** Verifica: la pagina si apre in italiano senza JS; con JS commuta; nessuna risorsa esterna.

## Fase 2 — Traduzione

- [x] **2.1** Titoli, descrizioni, pill, needs dei quindici blocchi.
- [x] **2.2** Masthead, here-band, legenda, etichette di blocco, intestazioni di colonna, note.
- [x] **2.3** Il pannello delle regole a destra.
- [x] **2.4** I tre paragrafi narrativi, il maggiore da ~24 000 caratteri.

## Fase 3 — Impronte e guardia

- [x] **3.1** `scripts/build_map_fingerprints.py`: calcola e riscrive `data-fp`/`data-fp-self`.
- [x] **3.2** Guardia, test 1: chiave presente in una lingua sola → rosso (FR-006).
- [x] **3.3** Guardia, test 2: token di stato divergente → rosso (FR-007).
- [x] **3.4** Guardia, test 3: numero divergente dopo normalizzazione → rosso (FR-007a).
- [x] **3.5** Guardia, test 4: impronta stale → rosso (FR-007b).
- [x] **3.6** Guardia, test 5: testo visibile non chiavato fuori dalle esenzioni → rosso (FR-003b).
- [x] **3.7** Ogni test provato per mutazione; docstring con i quattro limiti di FR-008.

## Fase 4 — Chiusura

- [ ] **4.1** Le otto sedi di FR-010.
- [x] **4.2** Suite intera, ruff, `test_citation_hygiene.py` a zero offender.
- [ ] **4.3** Audit singolo secondo il criterio del piano.
- [ ] **4.4** Merge in `develop`, artifact ripubblicato, memoria sincronizzata.

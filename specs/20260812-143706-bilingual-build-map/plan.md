# Piano di implementazione — Build map bilingue

**Branch**: `20260812-143706-bilingual-build-map` — **Spec**: [spec.md](spec.md) (CONVERGED al round 7)

## Criterio di arresto, scritto PRIMA di cominciare

Sette round di gate sulla spec sono stati troppi, e almeno tre li ha generati il
documento raccontando la propria storia. Per l'implementazione il criterio è
fissato adesso, non dopo aver visto il risultato:

- **un solo round di audit sul codice.** Bloccano soltanto: un difetto nel file
  pubblicato (contenuto sbagliato, pagina rotta, lingua che non commuta) e un
  test che non può fallire. Non bloccano prosa, cifre nei commenti, formulazioni.
- se il round non trova bloccanti, **si chiude**. Se ne trova, si correggono e
  si chiude comunque: nessuna serie di round.
- ogni test della guardia è provato **per mutazione** prima di dichiararlo tale.

## Architettura

Un solo file, `docs/build-map/epocha-build-map.html`, con entrambe le lingue.

**Rappresentazione.** Ogni blocco traducibile diventa una coppia di elementi
gemelli con la stessa chiave:

```html
<span data-k="ph1a.title" data-lang="it">Economia, strato base</span>
<span data-k="ph1a.title" data-lang="en" data-fp="a3f9">Economy base layer</span>
```

- `data-k` è la **chiave stabile** (FR-006). Univoca nel documento per coppia.
- `data-lang` distingue normativo (`it`) e mirror (`en`) — D-3.
- `data-fp` sul mirror è l'**impronta** del testo normativo corrispondente
  (FR-007b), più `data-fp-self` con l'impronta del proprio testo.

**Commutazione.** CSS puro, nessuno script necessario per lo stato a riposo
(FR-002): `[data-lang="en"] { display: none }` sotto `:root:not([data-lang-sel="en"])`
e viceversa. Il bottone imposta un attributo sul root e salva in `localStorage`
dentro `try/catch`. Senza JS resta l'italiano, che è il default a riposo.

**Impronta.** SHA-256 troncato a 12 caratteri esadecimali del testo normalizzato
(whitespace flattened, entità risolte). Calcolata da uno script di manutenzione
che vive accanto alla guardia.

## Moduli

| file | ruolo |
|---|---|
| `docs/build-map/epocha-build-map.html` | il deliverable |
| `epocha/apps/dashboard/tests/test_build_map_bilingual.py` | la guardia (FR-006, 007, 007a, 007b, 003b) |
| `scripts/build_map_fingerprints.py` | ricalcolo delle impronte, uso manuale |

**Collocazione della guardia**: `dashboard` è l'app che ha a che fare con la
presentazione del progetto, ed è l'unica il cui dominio non è la simulazione. Non
si imita `demography/tests/test_citation_hygiene.py`, che sta lì per ragioni
storiche — FR-009a e il rilievo del round 5.

## Ordine di esecuzione

1. Chiavatura e struttura bilingue del file, italiano primo.
2. Selettore CSS + bottone.
3. Traduzione completa.
4. Script delle impronte, e impronte popolate.
5. Guardia con cinque test, ciascuno provato per mutazione.
6. Le otto sedi di FR-010.
7. Audit, merge, artifact.

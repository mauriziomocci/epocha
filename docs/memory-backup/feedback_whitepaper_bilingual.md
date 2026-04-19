---
name: whitepaper-bilingual
description: REGOLA PERMANENTE -- Due whitepaper scientifici living document (EN + IT) che descrivono il comportamento corrente del sistema, linkati dai rispettivi README, sempre aggiornati e rigorosi
type: feedback
originSessionId: f9bc7a55-71c4-45ed-9602-f5e328a6175e
---
# Whitepaper scientifici bilingui — living documents

**Regola**: il progetto mantiene due documenti scientifici rigorosi che descrivono **come il sistema si comporta in quel momento**:

- `docs/whitepaper/epocha-whitepaper.md` (inglese, primario)
- `docs/whitepaper/epocha-whitepaper.it.md` (italiano, companion)

Entrambi sono **living documents**: descrivono lo stato corrente del codice mergiato in `develop`, non lo stato passato o futuro. Ogni merge a `develop` che tocchi modelli scientifici, parametri, algoritmi, calibrazione, o integration surface **deve** aggiornare i whitepaper nello stesso commit o in un commit dedicato prima del merge.

## Linkaggio dai README

- `README.md` contiene un link visibile (sezione "Scientific documentation" in homepage, o all'inizio del file) a `docs/whitepaper/epocha-whitepaper.md`.
- `README.it.md` contiene il link equivalente a `docs/whitepaper/epocha-whitepaper.it.md`.
- Il link non punta al sito esterno; punta al file nel repository per garantire che versione del whitepaper e versione del codice corrispondano sempre.

## Contenuto richiesto

I whitepaper descrivono, per ogni sottosistema attualmente implementato:

1. **Obiettivo scientifico**: cosa il sottosistema modella e perche'
2. **Modelli e formule**: funzioni matematiche correnti, con citazioni primarie (autore, anno, titolo, journal)
3. **Parametri calibrati**: valori correnti per ciascuna era/scenario, con fonte o marcatura come "tunable design parameter"
4. **Assunzioni e semplificazioni**: esplicite, con ragionamento
5. **Integration surface**: come il sottosistema interagisce con gli altri (input/output/side effect)
6. **Validation status**: se il sottosistema e' stato validato contro dati reali, quali dati, quale tolleranza raggiunta
7. **Known limitations**: cosa il sottosistema NON cattura e perche'

La struttura deve riflettere l'ordine logico di sviluppo (Economy Spec 1 → Spec 2 Parts 1-3 → Demography Plan 1-4 → ...) o un ordine tematico (popolazione → economia → politica → informazione) — la scelta definitiva la prende il primo commit del whitepaper e resta stabile.

## Disciplina di sincronizzazione EN + IT

Come per i README, EN e IT devono sempre essere allineati:
- Stesse sezioni, stessi modelli descritti
- Citazioni bibliografiche invariate (lingua originale)
- Formule, nomi di codice, parametri invariati
- Prosa tradotta fedelmente
- Divergenza fattuale = bug di documentazione da chiudere immediatamente

## Rigore scientifico

I whitepaper sono **publication-grade**: devono poter essere linkati in un paper o inviati a un reviewer esterno senza imbarazzo. Cio' significa:
- Nessuna affermazione senza citazione o marcatura esplicita come tunable
- Nessun parametro magic number senza derivazione o fonte
- Nessun modello descritto in modo impreciso rispetto al codice
- Nessuna semplificazione non dichiarata
- Linguaggio preciso, tecnico, verifiabile

Nessuna eccezione: un whitepaper che scivola su queste regole vale ZERO per il paper finale del progetto (`feedback_scientific_paper_goal`).

## Best practice paper scientifici (obbligatorie)

I whitepaper seguono la struttura e le convenzioni standard dei paper scientifici. Non sono note tecniche libere ne' README estesi:

### Struttura

Ordine canonico delle sezioni (adattabile ma non omissibile senza giustificazione):

1. **Title + Authors + Affiliation + Date of last update + Version**
2. **Abstract** (150-300 parole): problema, approccio, risultati principali, limiti. Deve essere autocontenuto.
3. **Keywords**: 5-8 termini chiave per ricerca.
4. **Introduction**: contesto scientifico, problema, gap nella letteratura, contributo del progetto, struttura del documento.
5. **Background / Related Work**: letteratura di riferimento, modelli alternativi considerati, stato dell'arte.
6. **Methods**: per ogni sottosistema, i modelli matematici implementati, le equazioni con numerazione, i parametri con fonte, gli algoritmi con pseudocodice o riferimento al modulo.
7. **Implementation**: mapping modello → codice (nomi dei moduli Django, percorsi file), scelte ingegneristiche che impattano il modello scientifico, integration contracts cross-app.
8. **Calibration**: per ogni parametro tunable, fonte o procedura di fitting. Per ogni parametro fittato, dati sorgente, metodologia, tolleranze raggiunte.
9. **Validation**: benchmark storici, confronto output-dati, tolleranze misurate. Tabelle di risultati con errori assoluti/relativi.
10. **Discussion**: interpretazione dei risultati, limiti di validita', assunzioni che possono rompere, trade-off di design.
11. **Known Limitations**: sintesi esplicita delle semplificazioni, con road-map di estensioni future.
12. **Conclusions**: contributo, applicabilita', prossimi passi.
13. **References**: bibliografia completa, stile Chicago Author-Date o APA (scegliere uno e mantenere consistenza).
14. **Appendices**:
    - A. Full parameter tables per era/template
    - B. Proofs o derivazioni formali
    - C. Extended validation tables
    - D. Reproducibility notes (seed RNG, versioni dipendenze)

### Convenzioni di formattazione

- **Numerazione sezioni**: 1., 1.1, 1.1.1 (massimo 3 livelli)
- **Equazioni numerate** in parentesi tonde sul lato destro, riferite nel testo come (Eq. 3.2)
- **Figure e tabelle numerate** con caption descrittiva sotto la figura / sopra la tabella, riferite nel testo (Fig. 2, Tab. 4). Ogni figura/tabella autocontenuta.
- **Citazioni inline** in stile Author-Date: "(Wrigley & Schofield 1981)" o "Wrigley & Schofield (1981)".
- **Bibliografia** completa con: autore, anno, titolo, journal/publisher, volume, pagine, DOI/URL dove disponibile.
- **Variabili matematiche** in italico (notazione LaTeX-like in Markdown: `$\alpha_i$`, `$R$`, ecc.).
- **Nomi di codice** in `monospace`.
- **Acronimi**: al primo uso espansi (es. "age-specific fertility rate (ASFR)"), poi usati come acronimo.

### Lunghezza attesa

- Minimo: ~4.000 parole per un sistema con 1-2 sottosistemi.
- Atteso: 10.000-25.000 parole quando il progetto ha tutti i sottosistemi della roadmap.
- Massimo: nessun limite hard; ma sezioni molto lunghe (> 10 pagine) possono essere estratte in appendici o sub-documenti linkati.

### Reproducibility

Ogni whitepaper chiude con:
- Commit hash del repository a cui il whitepaper si riferisce
- Versione Python + dipendenze principali (requirements.txt hash)
- Comandi esatti per rigenerare i benchmark di validation
- Seed RNG usati nei benchmark

Questo permette a un reviewer esterno di clonare il repo a un commit specifico e ottenere ESATTAMENTE i risultati riportati.

## Quando creare / aggiornare

**Creazione**: la prima stesura dei due whitepaper e' un task one-shot in follow-up al Plan 2 demografia, insieme alla riscrittura dei README. Vedi `project_readme_rewrite_todo` — da estendere a whitepaper_todo.

**Aggiornamento**: ogni merge a `develop` di una PR che tocchi un qualsiasi aspetto scientifico del sistema triggera l'aggiornamento. La regola CLAUDE.md `### Documentation Sync` e' estesa per includere i whitepaper accanto ai README.

## Relazione con altre regole

- **feedback_scientific_paper_goal**: i whitepaper sono la rampa di lancio per il paper finale. Ogni capitolo del paper a fine progetto potra' attingere al whitepaper corrispondente.
- **feedback_italian_specs**: le spec in `docs/superpowers/specs/` sono solo in italiano e sono artefatti di design (snapshot del momento in cui la spec e' stata scritta). I whitepaper sono diversi: bilingui, living, descrivono il comportamento corrente del codice.
- **feedback_readme_bilingual_maintenance**: stessa filosofia di manutenzione applicata ai whitepaper.

## Data di codificazione

2026-04-19 — codificata dopo che l'utente ha richiesto due documenti scientifici rigorosi che descrivano il comportamento corrente del sistema, linkati dai README, in inglese e italiano.

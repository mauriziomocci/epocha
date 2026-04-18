---
name: italian-specs
description: REGOLA PERMANENTE -- spec file solo in italiano per approvazione. Code, commit, plan, docstring, README restano solo inglese
type: feedback
originSessionId: f9bc7a55-71c4-45ed-9602-f5e328a6175e
---
# Spec file in italiano (regola permanente)

**Regola**: tutti i file di specifica in `docs/superpowers/specs/` sono scritti in **italiano**. Una sola versione per ciascuna spec; nessun sync bilingue.

## Ambito della regola

**SI applica a**:
- Spec file in `docs/superpowers/specs/`
- Tutte le sezioni narrative: scope, architettura, design decisions log, FAQ, known limitations, audit resolution log
- La bibliografia mantiene i titoli originali (inglese per paper inglesi, tedesco per paper tedeschi come Hadwiger 1940, ecc.) perché i titoli di paper non si traducono mai

**NON si applica a** (restano inglese only):
- Codice sorgente
- Commenti e docstring nel codice
- Commit messages
- Log applicativi
- File di piano in `docs/superpowers/plans/`
- Test file
- README tecnici
- CLAUDE.md
- Memory files di progetto

## Why

L'utente ha dichiarato il 2026-04-18 di trovarsi "meglio leggendo in italiano" e che la gestione bilingue e' "complessa" (sync burden). La scelta ottima per il review/approval workflow e' una sola lingua — italiano, quella che rende piu' profonda la validazione umana.

Conseguenze:
- Zero sync burden tra versioni
- Un solo file autorevole per spec
- L'utente legge nella lingua piu' fluente per catch migliori errori durante il gate di validazione umana
- Il codice e il resto del repo resta inglese (international standard)

## Traduzione inglese: quando

**Solo al momento della pubblicazione del paper scientifico** (o su richiesta esplicita dell'utente). La traduzione non e' un artefatto continuo mantenuto; e' un'operazione one-shot da eseguirsi quando un documento deve essere pubblicato in un venue internazionale. La traduzione si fa dall'italiano stabile, non viceversa.

## Gestione storica

La demography spec (2026-04-18-demography-design.md + 2026-04-18-demography-design-it.md) era stata scritta in entrambe le lingue durante la transizione della regola. Entrambe le versioni restano nel repo: la versione italiana (`-it.md`) e' **autoritativa** per ogni revisione futura; la versione inglese e' un **artefatto storico** non piu' mantenuto e marcato come "legacy" nella sua intestazione. Tutte le revisioni post-2026-04-18 si applicano SOLO all'italiano.

## Convenzione di naming

Spec italiana: `YYYY-MM-DD-<nome>-design.md` — naming standard senza suffisso.

Esempio: `2026-04-19-technology-design.md` (futuro sottosistema tecnologia, solo in italiano).

Per la demography transitoria: `-it.md` resta come suffisso del file autoritativo per mantenere la history git del commit iniziale; l'inglese `2026-04-18-demography-design.md` rimane come legacy.

## Applicazione retroattiva

- Economy Spec 1, Economy Spec 2 Parts 1-3: restano in inglese (già finite, non riapribili senza necessita' scientifica)
- Demography: versione italiana autoritativa, inglese marcata legacy
- Ogni nuova spec: italiano dal primo tick

## Cost impact

Nullo / positivo. Singola versione = meno effort di scrittura, zero sync drift, approval umana piu' profonda e veloce.

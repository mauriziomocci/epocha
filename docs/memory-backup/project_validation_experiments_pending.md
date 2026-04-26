---
name: validation-experiments-pending
description: Follow-up dopo whitepaper -- esecuzione validation experiments (HMD fit, Wrigley-Schofield, Irish Famine analog) sui modelli Demography
type: project
originSessionId: b165274d-a708-4e8c-abed-b28a018c163f
---
# Validation experiments execution -- pending

## Stato

Il whitepaper (cap. 7 Validation Methodology) descrive la metodologia di validation per ogni modulo audited (Demography Plan 1+2, Economy Behavioral) ma **non** esegue i benchmark. Status dichiarato in whitepaper: "Validation experiments specified, not yet executed."

Questa scelta fu fatta nel brainstorming del 2026-04-26 per evitare scope creep nella branch del whitepaper (vedi spec `docs/superpowers/specs/2026-04-26-readme-and-whitepaper-catchup-design.md`).

## Esperimenti da eseguire

Dataset target con DOI/URL da spec Demography:

1. **Heligman-Pollard fit** su Human Mortality Database (HMD) -- UK 1851-1900, Sweden 1751-1900
   - Procedura: download HMD, fit con scipy.curve_fit gia' implementato, RMSE per fascia eta'
   - Acceptance threshold: RMSE < 0.005 sui rate annuali per eta', shape qualitativamente coerente con curva HP

2. **Hadwiger ASFR fit** su Wrigley-Schofield (1981) "Population History of England 1541-1871"
   - Procedura: estrarre TFR e ASFR per coorti pre-industriali, calibrare T/H/p
   - Acceptance: TFR simulato in ranged [4.5, 6.5] per era preindustriale

3. **Crisis mortality analog** -- Irish Famine 1845-1849 (Mokyr 1985)
   - Procedura: simulare 5-tick crisis con disponibilita' calorica ridotta, confrontare excess mortality
   - Acceptance: excess mortality rate consistente con stime storiche (~12% over 5 years)

4. **Couple formation rates** -- Hajnal (1965) European Marriage Pattern
   - Procedura: simulare societa' preindustriale 100-tick, misurare SMAM (Singulate Mean Age at Marriage), proportion never-married
   - Acceptance: SMAM in [25, 28] anni, never-married proportion in [10%, 20%] per "European pattern"

5. **Economy behavioral** -- da definire (Cagan expectation horizon, credit cycle period)

## Output atteso

Un mini-paper (5-10 pagine) o, alternativamente, una sezione "Validation Results" da aggiungere come `epocha-whitepaper-validation.md` (companion document) o come Appendice D al whitepaper principale.

Plot generati salvati in `docs/whitepaper/figures/` (path da definire), referenziati dal whitepaper.

## Effort stimato

5-10 giorni di lavoro: setup dataset (1-2 giorni), calibrazione e fit (2-3 giorni), generazione plot (1 giorno), scrittura e review (2-3 giorni).

## Priorita'

Media. Va eseguita **prima** della prima sottomissione del paper a venue scientifico. Non blocca lo sviluppo simulativo (Plan 3, audit re-pass, ecc.).

## Why

Il whitepaper senza validation reale e' "publication-grade documentation" ma non "publication-ready paper". Per pubblicare serve almeno una validation eseguita end-to-end.

## How to apply

Quando l'utente chiede "cosa serve per pubblicare il paper" segnala questa voce. Quando si introduce una nuova feature scientifica con dataset di reference disponibile, considerare di includere la validation immediata invece di accumularla qui.

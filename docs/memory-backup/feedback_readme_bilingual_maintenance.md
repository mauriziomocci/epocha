---
name: readme-bilingual-maintenance
description: REGOLA PERMANENTE -- README.md (inglese) e README.it.md (italiano) sempre aggiornati e sincronizzati a ogni cambiamento rilevante
type: feedback
originSessionId: f9bc7a55-71c4-45ed-9602-f5e328a6175e
---
# README bilingue — manutenzione obbligatoria

**Regola**: sia `README.md` (inglese, primario) sia `README.it.md` (italiano, companion) devono essere **sempre aggiornati e sincronizzati** ad ogni cambiamento rilevante del progetto.

## Cosa triggera l'aggiornamento

Un cambiamento e' "rilevante" per i README quando tocca uno dei seguenti:
- Architettura (nuove app Django, modelli principali, moduli scientifici, integration contracts)
- Stack tecnico (nuove dipendenze runtime, nuovi servizi Docker, nuovo framework)
- Regole di progetto (CLAUDE.md, workflow, policy di model selection, italian-specs, ecc.)
- Roadmap / stato progetto (nuovo sottosistema completato, milestone chiusa, debt tracciato)
- Istruzioni di setup o operative (docker-compose, pytest config, variabili d'ambiente)
- Scientific references principali (nuovi modelli/fonti aggiunti come base di un sottosistema)
- Validation benchmarks documentati
- API pubblica / contratti di integrazione cross-app

**Non triggera aggiornamento README**: bug fix interno, refactor che non cambia l'interfaccia, rename di variabili private, test aggiunti senza nuova feature.

## Quando aggiornare

Tre momenti canonici (almeno uno deve applicarsi):

1. **All'interno dello stesso commit** che introduce il cambiamento, quando il delta README e' piccolo e diretto.
2. **Come parte del commit di chiusura** di un plan (prima del merge alla develop), quando il delta cumulato del plan richiede una sezione nuova o una revisione sostanziale.
3. **Come follow-up dedicato** su branch separato (fix/docs-readme-*) quando la riscrittura e' ampia (es. > 50 righe di diff sui README) e merita review indipendente.

L'opzione 3 e' accettabile ma la regola di default e' 1 o 2: non rimandare oltre il merge.

## Sincronizzazione EN + IT

**Le due versioni sono sempre allineate nel contenuto e nella struttura**. Divergenza = bug di documentazione da fixare immediatamente.

- **README.md** (inglese): primario, pubblicabile, citabile in paper e review internazionali.
- **README.it.md** (italiano): companion, per contributor italofoni. Traduzione fedele di README.md tranne per riferimenti culturali localizzati (es. citazioni italiane se rilevanti al progetto).
- Quando si aggiorna uno, si aggiorna anche l'altro nello stesso commit.
- Citazioni bibliografiche restano nella lingua originale in entrambe le versioni.
- Nomi di codice, comandi, file path, identifier restano invariati.

## Controllo di qualita'

Prima del merge di un branch a develop, il tester verifica:
- README.md e README.it.md riflettono lo stato nuovo del codice e non contengono info obsolete
- Ogni sezione del README.it.md corrisponde semanticamente alla sezione equivalente in README.md
- Le due versioni non divergono su fatti tecnici

## Relazione con le altre regole

Questa regola **estende** la "Documentation Sync" gia' presente in CLAUDE.md (sezione `### Documentation Sync` che richiede update in-commit di docstring + README). La regola qui **specializza** alla coppia README bilingue: non basta aggiornare uno dei due, devono stare allineati.

**Non in conflitto con** la regola `feedback_italian_specs`: le spec in `docs/superpowers/specs/` restano solo in italiano; i README sono bilingue perche' sono il primo punto di contatto del progetto e devono essere leggibili in inglese per review internazionali (paper) e in italiano per l'utente.

## Data di codificazione

2026-04-19 — codificata dopo che l'utente ha segnalato che entrambi i README erano molto obsoleti e ha richiesto una regola permanente per garantirne la manutenzione continua.

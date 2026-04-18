---
name: model-selection-policy
description: REGOLA PERMANENTE -- assegnazione modelli Claude per fase del canonical workflow (Opus per fasi critiche, Sonnet per implementazione, mai Haiku), con escalation protocol
type: feedback
originSessionId: f9bc7a55-71c4-45ed-9602-f5e328a6175e
---
# Model selection policy per Epocha

**Regola**: ogni fase del canonical 7-phase workflow usa un modello Claude specifico. La scelta NON e' opzionale per-sessione: e' codificata per ottimizzare rigore scientifico dove conta e costo/velocita' dove non conta meno.

## Assegnazione modello per fase

| Fase | Modello | Motivazione |
|------|---------|-------------|
| 1. Ideazione | **Opus 4.7** | Esplorazione concettuale, chiarimenti iniziali |
| 2. Requisiti (brainstorming, spec, adversarial audit, convergence loop) | **Opus 4.7 con extended thinking** | Rigore scientifico, bibliografia, formule, gate pesante. Errori qui si propagano in tutto il resto della pipeline. |
| 3. Design del piano architetturale | **Opus 4.7** | Architettura, trade-off cross-modulo, integrazione con subsistemi esistenti |
| 4. Task breakdown + revisione critica post-validazione | **Opus 4.7** | Decomposizione accurata, individuazione di gap nascosti prima del codice |
| 5. Implementazione (task-per-task) | **Sonnet 4.6** | Esecuzione di task gia' pienamente specificati; 3-5x piu' veloce e ~5x meno costoso di Opus |
| 5-bis. Code review per-task (routine) | **Sonnet 4.6** | 8 punti Mandatory Code Review su task atomico |
| 5-ter. Code review finale di integrazione cross-task | **Opus 4.7** | Giudizio architetturale complessivo, coerenza fra task |
| 6. Test generale + adversarial code audit finale | **Opus 4.7** | Gate finale pesante; scientific correctness del codice; auditor ostile e approfondito |
| 7. Chiusura (merge, sync backup, push) | **Sonnet 4.6** | Operazioni meccaniche e deterministiche |

## Escalation protocol (NON NEGOZIABILE)

Durante la fase 5 (implementazione con Sonnet), se un task rivela:
- Edge case non previsto nel piano
- Assunzione sbagliata nella spec
- Refactor non dichiarato che diventa necessario
- Incoerenza fra task e codice esistente
- Dubbio scientifico su una formula/citazione

il subagent Sonnet NON prova a risolverlo inventando. **Escala a Opus** con richiesta esplicita di revisione. Sonnet puo' continuare solo dopo che Opus ha aggiornato spec/piano/task.

Trigger dell'escalation: ogni volta che il task richiede una **decisione strategica** invece di una **esecuzione specificata**. Linea di demarcazione: se la risposta alla domanda "cosa faccio?" non e' pienamente derivabile dal task e dalla spec, e' escalation.

## Regole aggiuntive

**Scientific citation accuracy**: i commenti docstring di Epocha citano fonti precise (Heligman & Pollard 1980, Jones & Tertilt 2008, etc.). Le citazioni nel codice DEVONO corrispondere esattamente a quelle nella spec — nessuna invenzione, nessuna parafrasi. Code review di Sonnet deve verificare questo punto esplicitamente su ogni task con docstring scientifico.

**Context preservation paradox**: Sonnet ha context window piu' piccola di Opus 1M. Per renderlo utilizzabile in fase 5, i task prodotti in fase 4 devono essere **davvero atomici** (file-focused, scope ristretto). Se un task richiederebbe a Sonnet di tenere in context l'intero plan + spec + codebase di riferimento, e' segno che il task e' troppo grande e va spezzato in fase 4.

**Haiku NON e' mai usato**. Haiku e' troppo leggero per i vincoli di Epocha (scientific rigor, OWASP security, 8 punti Mandatory Review, citazioni esatte). La bilancia e' Opus-dove-conta, Sonnet-dove-non-conta-meno, **Haiku mai**.

## Meccanismo tecnico

La delegazione per-modello si implementa tramite lo skill `superpowers:subagent-driven-development`:

- Dispatcher principale (Opus) gestisce fasi 1-4 e 6-7, orchestra la fase 5
- Per ogni task di fase 5, il dispatcher crea un subagent con modello esplicito `sonnet`
- Il subagent esegue il task, ritorna l'output, il dispatcher flagga il task come risolto
- In caso di escalation, il subagent ritorna una flag di escalation al dispatcher; il dispatcher (Opus) prende il controllo, rivede il task, e rilancia o modifica il piano

Claude Code CLI supporta il model override via parametro `model` in Agent tool call (es. `model: "sonnet"` per esplicito downgrade). Il dispatcher Opus ne ha piena facolta'.

## Stima di costo/beneficio (per sottosistema tipico come Demografia)

- Implementazione totale: ~300-500K token
- Tutto su Opus: $15/M input + $75/M output
- Con policy (fase 5 su Sonnet): fase 5 ~$3/M input + $15/M output
- Risparmio stimato: 70-80% sulla fase 5, che e' il 60-70% del volume totale
- Nessuna degradazione di qualita' attesa grazie all'escalation protocol

## Revisione della policy

Solo su richiesta esplicita dell'utente. La regola non si modifica autonomamente.

## Data di codificazione

2026-04-18 — codificata dopo la formalizzazione del canonical 7-phase workflow e della task-breakdown rule.

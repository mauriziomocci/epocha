---
name: task-breakdown-mandatory
description: OBBLIGATORIO per ogni PIANO DI IMPLEMENTAZIONE -- suddivisione in task dettagliati con checkbox, esecuzione sequenziale con flag
type: feedback
originSessionId: f9bc7a55-71c4-45ed-9602-f5e328a6175e
---
# Task breakdown obbligatorio nei piani di implementazione

**Regola**: ogni **piano di implementazione** deve essere suddiviso in quanti piu' task possibili, ciascuno con:
1. Attivita' ben dettagliata (passi eseguibili, no ambiguita')
2. Flag di risolto (checkbox `- [ ]` / `- [x]` o equivalente)
3. Esecuzione sequenziale: si esegue un task alla volta, si flagga come completato, poi si passa al prossimo fino alla fine del piano

**Ambito di applicazione (trigger)**: la regola si attiva quando c'e' una **spec approvata** (completata la fase design + adversarial audit + CONVERGED) e si passa alla stesura/esecuzione del piano di implementazione. Si applica quindi ai plan file di `docs/superpowers/plans/`.

**NON si applica a**:
- Edit singoli estemporanei
- Risposte a domande
- Commit di documentazione non collegati a un piano di implementazione
- Micro-operazioni di manutenzione

Applicare la regola a operazioni fuori ambito creerebbe overhead burocratico senza beneficio. La linea di demarcazione e' netta: e' un piano se vive in `docs/superpowers/plans/` o se sta portando una spec in codice; altrimenti no.

**Why**: l'utente ha richiesto esplicitamente il 2026-04-18 questa regola come obbligatoria per i piani di implementazione, con la sfumatura che non si applica alle micro-operazioni. Il reasoning:
- **Trasparenza**: per un piano l'utente vuole vedere in tempo reale cosa e' fatto e cosa resta, senza leggere i diff
- **Isolamento fallimenti**: task piccolo = rollback mirato se qualcosa rompe
- **Publication-grade audit trail**: ogni task completato e' evidenza documentata, coerente con `feedback_scientific_paper_goal`
- **Resumability**: se una sessione si interrompe, si riprende dal primo task non flaggato
- **Context preservation per l'agente AI (Claude)**: in piani lunghi con decine di task, il task attualmente "in corso" (non ancora flaggato) e' il focus pointer dell'agente. Lavorando task-per-task, Claude mantiene il contesto necessario per QUEL task specifico senza disperdersi sull'intero plan. Questo e' un driver operativo, non solo metodologico: senza breakdown + flagging, l'agente rischia di perdere dettagli, dimenticare step gia' fatti, o saltare file richiesti. Il flagging e' il meccanismo di sincronizzazione stato-del-lavoro / stato-cognitivo-dell'agente.

**How to apply**:
1. Quando il trigger si attiva (spec approvata + inizio implementazione):
   - Suddividere il lavoro in task piccoli: 2-5 minuti / una modifica atomica / un gruppo di file strettamente correlati
   - Ogni task ha checkbox `- [ ] **Step N**: ...`
   - NESSUN task vago ("implement the feature"); sempre dettagliato ("Create file X with class Y containing method Z that does W, with tests T1-T3")
2. Durante l'esecuzione:
   - Si prende UN task alla volta
   - Si implementa con precisione
   - Si flagga come `- [x]` nel piano
   - Si passa al task successivo
   - NON saltare avanti, NON batch-processare piu' task senza flagging intermedio
3. Al completamento di tutti i task, il piano e' finito e si procede alla chiusura (merge, PR, sync memory)

**Si combina con**:
- `superpowers:writing-plans` skill (supporta gia' il pattern checkbox)
- CLAUDE.md "Plan before acting"
- `feedback_scientific_paper_goal` (task dettagliati = audit trail pubblicabile)

**Applicazione retroattiva**: nessuna. I piani Plan 3a/3b/3c di Economy gia' usano questo pattern; allineati senza retrofit.

**Scala tipica per Epocha**: per un sottosistema complesso come la Demografia, ci si aspetta 60-80 task distribuiti su 3-5 plan sequenziali, ciascuno contenente 15-25 task da 2-5 minuti.

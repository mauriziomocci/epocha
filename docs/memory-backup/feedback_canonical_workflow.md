---
name: canonical-workflow
description: REGOLA RIGOROSA -- flusso canonico obbligatorio per ogni sottosistema Epocha: 7 fasi con gate di validazione, codificato il 2026-04-18
type: feedback
originSessionId: f9bc7a55-71c4-45ed-9602-f5e328a6175e
---
# Flusso canonico obbligatorio per lo sviluppo di Epocha

**Regola**: ogni nuovo sottosistema, feature maggiore o spec del progetto segue questo flusso senza eccezioni. Il flusso e' rigoroso: saltare fasi o confondere gate e' violazione.

## Le 7 fasi

```
1. IDEAZIONE
   Input: descrizione in linguaggio naturale dall'utente
   Output: intento chiaro su cosa costruire

2. REQUISITI
   - Brainstorming: agente fa domande di chiarimento approfondite
   - Raccolta delle decisioni tramite Q&A iterativa
   - Stesura della spec file (docs/superpowers/specs/YYYY-MM-DD-<nome>.md)
   - La spec include: scientific foundations (bibliografia), architettura,
     alternative considerate, design decisions log, FAQ, known limitations
   GATE REQUISITI:
   - Three-step design process (proposta -> self-review critica -> 2a review)
   - Adversarial scientific audit (dispatch critical-analyzer subagent)
   - Mandatory convergence loop: audit -> fix -> re-audit finche' CONVERGED
   - Validazione umana esplicita sulla spec finale

3. DESIGN DEL PIANO ARCHITETTURALE
   - Agente prepara il piano partendo da spec validata
   - Il piano definisce: moduli da creare, file changes, pipeline ordering,
     architectural choices, integrazione con sottosistemi esistenti
   - Il piano NON contiene ancora il task breakdown operativo
   GATE DESIGN:
   - Validazione umana del piano architetturale

4. TASK BREAKDOWN
   - Decomposizione del piano in task piccoli e dettagliati (regola
     obbligatoria feedback_task_breakdown_mandatory)
   - Ogni task: checkbox + descrizione dettagliata + file/funzioni coinvolte
     + test da far passare + commit message proposto
   - Nessun task vago; granularita' 2-5 minuti per task
   GATE TASK BREAKDOWN:
   - Validazione umana del task breakdown
   - Fase di revisione critica dell'agente con occhi freschi post-validazione:
     l'agente rilegge e solleva qualsiasi dubbio residuo PRIMA di toccare codice
     (trigger: transizione da design a implementazione; scope: dettagli non
     esplicitati che rischiano di essere persi durante scrittura; NON e' un
     secondo round di domande generiche)

5. IMPLEMENTAZIONE (task-per-task, sequenziale)
   Per ogni task:
   - Scrittura del codice esattamente come descritto nel task
   - Test del task (unit test per il pezzo nuovo + regressione sui test vicini)
   - Code review critica, puntuale, approfondita (CLAUDE.md Mandatory Code Review
     8 punti: pythonic, DRF, DRY, eccezioni, consistency, scalability, security,
     documentazione, doc sync)
   - Flag task come risolto (checkbox -> [x])
   - Passaggio al task successivo SOLO dopo completamento + flag

6. TEST GENERALE DELL'IMPLEMENTAZIONE
   - Full test suite (pytest --cov=epocha -v)
   - Integration test end-to-end del nuovo sottosistema
   - Zero test falliti; zero xfail (solo skip con reason TODO)
   GATE FINALE:
   - Adversarial review finale (critical-analyzer sul codice, non piu' sulla spec)
   - Validazione umana della chiusura

7. CHIUSURA
   - Merge della feature branch su develop (--no-ff per preservare milestone)
   - Sync memory backup (docs/memory-backup/)
   - Push
   - Aggiornamento progress memory (project_<feature>_progress.md)
```

## Principi operativi (non negoziabili)

1. **Sequenzialita' stretta fra le fasi**: non si passa alla fase N+1 senza aver
   completato il gate di N. Nessuna scorciatoia.

2. **Gate pesanti vs gate leggeri**:
   - **Gate pesanti** (tutto deve essere validato rigorosamente):
     - Gate REQUISITI (chiude la fase scientifica; la spec e' il fondamento)
     - Gate FINALE (prima del merge; chiude il lavoro)
   - **Gate leggeri** (review rapida, non deep dive perche' i prerequisiti sono
     gia' stati rigorosamente validati):
     - Gate DESIGN (rileggere il piano, confermare coerenza con spec)
     - Gate TASK BREAKDOWN (confermare granularita' e completezza)
   Distinzione serve a evitare "gate fatigue": ogni sottosistema ha 4 gate,
   di cui 2 pesanti e 2 leggeri.

3. **Adversarial review in due momenti diversi**:
   - Gate REQUISITI: adversarial sulla SPEC (scientific rigor, citazioni, formule)
   - Gate FINALE: adversarial sul CODICE (correttezza, security, performance)
   Sono due review distinte con scope diverso.

4. **Revisione critica post-validazione (fase 4 gate)**:
   - Trigger specifico: transizione da design a scrittura codice
   - Scope specifico: dettagli che rischiano di essere persi perche' non esplicitati
   - NON e' un secondo round di brainstorming
   - NON e' un secondo adversarial audit
   - E' il "ultimo controllo di coerenza" prima di scrivere codice

5. **Regola task-breakdown** (feedback_task_breakdown_mandatory) si attiva nella
   fase 4 e governa l'esecuzione della fase 5.

6. **Regola verify-before-asserting** e **GOLDEN RULE** sono sempre attive,
   in tutte le fasi. Non si disattivano mai.

## Mappatura con gli skill superpowers

- Fase 2 (Requisiti): skill `superpowers:brainstorming`
- Fase 3 + 4 (Design + Task breakdown): skill `superpowers:writing-plans`
- Fase 5 (Implementazione): skill `superpowers:executing-plans` oppure
  `superpowers:subagent-driven-development`
- Fase 6 (Test generale): skill `superpowers:verification-before-completion`
- Fase 7 (Chiusura): skill `superpowers:finishing-a-development-branch`

## Applicazione storica

Economy Spec 1, Spec 2 Parts 1-3 e il lavoro corrente di Demografia sono
stati svolti con un flusso molto simile ma implicito. Questa codificazione
formalizza la pratica esistente come regola rigorosa e impedisce la deriva.

## Quando rivedere questa regola

Solo su richiesta esplicita dell'utente. Il flusso non si modifica
autonomamente; le lezioni apprese producono **nuove** feedback memories,
non alterazioni silenti di questa.

# Specification Quality Checklist: Build map bilingue in un solo file

**Revisione**: 9 — **Feature**: [spec.md](../spec.md)

> **Questo file è un registro, non un racconto.** Fino alla revisione 6 era una
> cronaca di 278 righe. I tre bloccanti del round 4 stavano nella spec; i tre
> del round 5 stavano qui, ed è la ragione del taglio — la frase che attribuiva
> al racconto anche quelli del round 4 era falsa e il round 6 l'ha colta. Il
> round 5 lo ha detto con precisione: «il verbale non è sottoposto alla disciplina che
> il verbale impone alla spec». Il rimedio non è scrivere meglio la cronaca, è
> **non tenerne una**: una riga per round, e le regole di processo qui perché
> sono l'unico contenuto che sopravvive al work item.

## Checklist

- [x] Nessun dettaglio implementativo, **con un'eccezione dichiarata in sette
      siti**, non tre: FR-007 e D-2 nominano i token `s-done`/`s-prog`/`s-todo`;
      FR-007b prescrive un meccanismo; FR-009 e SC-005 nominano
      `test_citation_hygiene.py`; FR-009a prescrive un test nella suite; e il
      test 3 di User Story 2 fissa `beautifulsoup4` in `requirements/base.txt`.
      Senza, i requisiti non sarebbero decidibili. L'elenco parziale presentato
      come chiuso era il difetto che questo work item insegue da sei round.
- [x] Centrata sul valore per l'utente
- [x] Tutte le sezioni obbligatorie presenti, FAQ inclusa
- [x] Nessun marcatore [NEEDS CLARIFICATION]
- [x] Requisiti verificabili e non ambigui
- [x] Criteri di successo misurabili
- [x] Scenari di accettazione definiti, casi limite identificati
- [x] Ambito delimitato, dipendenze e assunzioni identificate
- [x] I criteri manuali hanno **una sola sede autoritativa**, in coda ai Success
      Criteria della spec. Questo file non li rienumera: rienumerarli è ciò che
      li ha fatti divergere in cinque round consecutivi.

## Registro dei round

| round | verdetto | rilievi | bloccanti | il rilievo che conta |
|---|---|---|---|---|
| 1 | NOT CONVERGED | 13 | 4 | la feature creava una seconda eccezione a una frase costituzionale che diceva «the only exception» |
| 2 | NOT CONVERGED | 16 | 5 | l'emendamento contraddiceva se stesso: vietava la prosa come collante e citava come meccanismo una checklist manuale |
| 3 | NOT CONVERGED | 9 | 1 | il corpo della costituzione corretto, il suo log no — recidiva del bloccante del round 2 |
| 4 | NOT CONVERGED | 7 | 3 | la terza regola non applicata a se stessa: tre affermazioni corrette sopravvivevano stale |
| 5 | NOT CONVERGED | 8 | 3 | **la spec è pulita**; tutti e tre i bloccanti erano in questo file |
| 6 | NOT CONVERGED | 6 | 1 | il bloccante torna nel **normativo**: due elenchi chiusi degli stessi «tre limiti», con contenuti diversi, che in unione sono quattro |
| 7 | **CONVERGED** | 5 | 0 | nessun bloccante: nessun requisito contraddittorio o indecidibile, nessun criterio infalsificabile, nessuna affermazione falsa alla misura |

Totale 64 rilievi, 17 bloccanti, chiusi in sette round. Non esistono file di rapporto separati per
questo work item. Circa due terzi dei rilievi sono ricostruibili dai messaggi di
commit — `git log develop..HEAD` — e i restanti, tutti non bloccanti e tutti
chiusi, vivono nella cronaca alla revisione 6: `git show b2b3120:specs/20260812-143706-bilingual-build-map/checklists/requirements.md`.
La frase che li dichiarava tutti nei commit era misurata a occhio e il round 6
l'ha contata.

## Le quattro regole di processo

Sono il prodotto che sopravvive al work item. Le prime due vengono dal gate di
fase 6 della demografia, la terza e la quarta da qui.

1. **Una guardia strutturale si estende solo per una violazione osservata nel
   repository, mai per una costruita da chi rivede.** Lo spazio degli input
   costruibili è infinito, quello dei casi reali è piccolo e osservabile.
2. **Quando cambia un payload o una costante, la batteria di mutazioni si
   rilancia anche contro la versione precedente.** Una correzione si giudica dai
   mutanti che smette di uccidere, non da quelli che uccide.
3. **Prima di scrivere «chiuso», si greppa l'affermazione corretta su tutto il
   branch, non il rilievo che la nominava.** Il difetto non è dove l'hai visto.
4. **Una verifica deve dimostrare di poter fallire prima di essere creduta.**
   Controlla che i propri bersagli esistano, non silenzia gli errori, e porta un
   controllo positivo e uno negativo. Nata perché una procedura pubblicata come
   prova cercava in un percorso inesistente e restituiva undici zeri, nessuno
   dei quali una misura.

Una quinta, implicita in tutte: **il rimedio a un'informazione che diverge non è
tenerla allineata in più posti, è tenerla in un posto solo.** Il conteggio dei
criteri manuali è divergito cinque volte perché ogni correzione aggiungeva una
sede invece di eliminarne una.

## Gate di fase 2: CHIUSO

Round 7 **CONVERGED** sulla revisione 8. Cinque rilievi, nessuno bloccante.
Il piu' sostanziale — FR-003 non assegnato ad alcun predicato, quindi un blocco
non chiavato sarebbe passato — e' stato chiuso nella revisione 9 con FR-003b
invece di essere rimandato al piano, perche' era un buco di copertura e costava
una riga. Gli altri quattro sono migliorabilita' e si chiudono durante il piano.

**Prossimo passo**: `/speckit-plan`, poi `/speckit-tasks`, poi implementazione.

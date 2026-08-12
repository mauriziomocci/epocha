# Specification Quality Checklist: Build map bilingue in un solo file

**Revisione**: 7 — **Feature**: [spec.md](../spec.md)

> **Questo file è un registro, non un racconto.** Fino alla revisione 6 era una
> cronaca di 278 righe, e i round 4 e 5 hanno speso sei dei loro sei rilievi
> bloccanti su contraddizioni interne al racconto invece che alla spec. Il round
> 5 lo ha detto con precisione: «il verbale non è sottoposto alla disciplina che
> il verbale impone alla spec». Il rimedio non è scrivere meglio la cronaca, è
> **non tenerne una**: una riga per round, e le regole di processo qui perché
> sono l'unico contenuto che sopravvive al work item.

## Checklist

- [x] Nessun dettaglio implementativo, **con un'eccezione dichiarata**: FR-007 e
      D-2 nominano i token `s-done`/`s-prog`/`s-todo` e FR-007b prescrive un
      meccanismo. Senza, i requisiti non sarebbero decidibili.
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

Totale 53 rilievi, 16 bloccanti. Non esistono file di rapporto separati per
questo work item: i rilievi e le loro chiusure vivono nei messaggi di commit,
che sono l'artefatto verificabile — `git log develop..HEAD`.

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

## Aperto

Round 6 sulla revisione 7. Se converge: `/speckit-plan`, `/speckit-tasks`,
implementazione.

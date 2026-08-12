# Specification Quality Checklist: Build map bilingue in un solo file

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-08-12
**Revisione**: 2, dopo il round 1 del gate pesante di fase 2
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs)
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous
- [x] Success criteria are measurable
- [x] Success criteria are technology-agnostic (no implementation details)
- [x] All acceptance scenarios are defined
- [x] Edge cases are identified
- [x] Scope is clearly bounded
- [ ] **Dependencies and assumptions identified** — NON spuntata, e la ragione e'
      la sola che tenga: la feature dipende da un **emendamento alla
      costituzione** che nessuno ha ancora ratificato. Vedi sotto.

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria
- [x] User scenarios cover primary flows
- [ ] **Feature meets measurable outcomes defined in Success Criteria** — cinque
      dei criteri sono **verifiche manuali dichiarate** (lingua del contenuto,
      comportamento del selettore, persistenza, apertura da file locale): non
      sono automatizzabili senza un driver browser che il progetto non ha, e
      dichiararli tali e' obbligatorio dopo aver contato sedici criteri che
      passavano senza verificare nulla.
- [x] No implementation details leak into specification

## Stato del gate di fase 2

**Round 1: NOT CONVERGED**, 13 rilievi, 4 bloccanti. Tutti e 13 chiusi nella
revisione 2 della spec **tranne F-1**, che non e' chiudibile da chi scrive.

I quattro bloccanti, e cosa e' cambiato:

- **F-1 governance — APERTO, richiede l'utente.** `constitution.md:96` dice che
  il mirror italiano del whitepaper e' «the only exception» alla regola per cui
  tutto cio' che non e' spec sta in inglese. Questa feature ne crea una seconda.
  L'emendamento e' scritto nella spec; ratificarlo richiede approvazione
  esplicita, voce di memoria, version bump e migration guidance, e nessuno dei
  quattro spetta a chi redige.
- **F-2 chiuso**: FR-003 e FR-007 si contraddicevano sulle etichette di stato —
  una pill tradotta correttamente era insieme dovuta e vietata. Lo stato ora si
  confronta sul token di classe che il file gia' porta (`s-done`/`s-prog`/`s-todo`),
  che e' indipendente dalla lingua.
- **F-3 chiuso**: FR-006 non diceva come si identifica un blocco. Ora la chiave
  stabile e' un requisito, e FR-008 — che senza chiavi era contraddittorio e con
  le chiavi era vuoto — e' cancellato e sostituito dall'obbligo di dichiarare il
  limite.
- **F-4 chiuso, ed era il piu' grave**: prosa riscritta in una lingua sola, senza
  toccare stati ne' numeri, passava ogni controllo — sul caso piu' frequente a un
  checkpoint, su un paragrafo di 24 750 caratteri di prosa pura. Chiuso da
  FR-007b, l'impronta del blocco normativo, che rende obsoleto il mirror quando
  il normativo cambia.

I nove non bloccanti sono chiusi: la stima sulle regioni di citazione era falsa
su entrambe le meta' e il rischio vero e' la co-locazione; il tetto del 2% non
era un tetto e come criterio non poteva fallire (0,09 ms contro 9,71 s, tre
ordini di grandezza); byte e caratteri erano scambiati; due conteggi di
caratteri e parole non erano riproducibili e sono rimossi; due cifre
autoinvalidanti residue sono state riscritte in forma relazionale; sette criteri
sono ora dichiarati manuali; la lingua normativa e' dichiarata (italiano, con
l'inglese mirror); i due casi d'ambiente — JavaScript assente e persistenza non
disponibile nell'artifact — sono requisiti espliciti; e l'argomento del «perche'
farlo» e' stato riscritto, perche' quello della prima stesura inventava una
causalita' che i numeri della spec stessa contraddicevano.

**Prossimo passo**: ratifica dell'emendamento costituzionale, poi round 2
dell'audit sulla revisione 2.

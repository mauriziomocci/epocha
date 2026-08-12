# Specification Quality Checklist: Build map bilingue in un solo file

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-08-12
**Revisione**: 4, dopo il round 3 del gate pesante di fase 2
**Feature**: [spec.md](../spec.md)

## Content Quality

- [~] **No implementation details** — parzialmente, e deliberatamente. FR-007 e
      D-2 nominano i token `s-done`/`s-prog`/`s-todo`, che sono classi CSS del
      file, e FR-007b prescrive un meccanismo. Senza di essi i requisiti non
      sarebbero decidibili: sono le chiusure dei due bloccanti del round 1. La
      spunta piena era falsa e nascondeva la scelta invece di dichiararla.
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed — **inclusa la FAQ**, che la revisione 2
      non aveva mentre questa casella era spuntata. Rilievo bloccante del round 2.

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous
- [x] Success criteria are measurable
- [x] Success criteria are technology-agnostic (no implementation details)
- [x] All acceptance scenarios are defined
- [x] Edge cases are identified
- [x] Scope is clearly bounded
- [x] **Dependencies and assumptions identified** — l'emendamento alla
      costituzione e' **ratificato** (1.1.0, 2026-08-12) e la dipendenza e'
      sciolta.

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria
- [x] User scenarios cover primary flows
- [x] **Feature meets measurable outcomes defined in Success Criteria** — con i
      criteri manuali **enumerati** nella spec invece che contati: il round 2 ha mostrato che
      il default e la presenza delle varianti sono statici e quindi
      automatizzabili con `beautifulsoup4`. Restano manuali il comportamento del
      comando di alternanza e la persistenza, che richiedono un browser che il
      progetto non ha. Dichiararli tali resta obbligatorio dopo aver contato
      sedici criteri che passavano senza verificare nulla.
- [~] **No implementation details leak** — vedi sopra: qui il meccanismo
      appartiene alla spec perche' e' cio' che rende i requisiti verificabili.

## Stato del gate di fase 2

**Round 1: NOT CONVERGED**, 13 rilievi, 4 bloccanti. Tutti e 13 chiusi nella
revisione 2 della spec; F-1 e' stato chiuso dalla ratifica dell'utente.

I quattro bloccanti, e cosa e' cambiato:

- **F-1 governance — CHIUSO.** La costituzione diceva che il mirror italiano del
  whitepaper era «the only exception»; questa feature ne creava una seconda.
  **Ratificato dall'utente il 2026-08-12**, costituzione a 1.1.0 con tutti e
  quattro gli adempimenti. Il round 2 ha poi trovato che l'emendamento
  contraddiceva se stesso (R2-2) e che questo verbale continuava a dichiararlo
  aperto (R2-1): entrambi chiusi nella revisione 3.
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
  checkpoint, su un paragrafo di 24 750 caratteri di HTML interno, 762 dei quali marcatura. Chiuso da
  FR-007b, l'impronta del blocco normativo, che rende obsoleto il mirror quando
  il normativo cambia.

I nove non bloccanti sono chiusi: la stima sulle regioni di citazione era falsa
su entrambe le meta' e il rischio vero e' la co-locazione; il tetto del 2% non
era un tetto e come criterio non poteva fallire (0,09 ms contro 9,71 s, tre
ordini di grandezza); byte e caratteri erano scambiati; due conteggi di
caratteri e parole non erano riproducibili e sono rimossi; due cifre
autoinvalidanti residue sono state riscritte in forma relazionale; il round 2 ha mostrato che il default e la presenza delle
varianti sono statici e quindi automatizzabili con `beautifulsoup4`; i criteri
manuali residui sono **enumerati una volta sola nella spec** invece di essere
contati, perche' un conteggio derivato in due sedi diverge e infatti era
divergito; la lingua normativa e' dichiarata (italiano, con
l'inglese mirror); i due casi d'ambiente — JavaScript assente e persistenza non
disponibile nell'artifact — sono requisiti espliciti; e l'argomento del «perche'
farlo» e' stato riscritto, perche' quello della prima stesura inventava una
causalita' che i numeri della spec stessa contraddicevano.

Con la ratifica, tutti e 13 i rilievi del round 1 risultano chiusi.


## Round 2 — NOT CONVERGED, 16 rilievi, 5 bloccanti

Tutti chiusi nella revisione 3. I cinque bloccanti:

- **R2-1**: il verbale del gate dichiarava aperto l'emendamento che la
  costituzione dello stesso branch dichiarava ratificato, e citava
  `constitution.md:96` per un testo che quella riga non porta piu'. Difetto
  creato dal commit dell'emendamento senza rilavorare la spec. Chiuso.
- **R2-2**: l'emendamento **contraddiceva se stesso** — vietava l'allineamento
  affidato alla sola prosa e citava come meccanismo la doc-sync rule, che e' una
  checklist di PR con zero hook attivi. Corretto nella costituzione, che ora
  dichiara l'asimmetria.
- **R2-3**: FR-007b si comprava con l'edit di un token, ricalcolando l'impronta
  senza tradurre. Chiuso **dichiarando il limite** invece di promettere cio' che
  nessun checksum puo' dare, ritirando la parola «inderogabile» da D-4 e
  registrando le impronte di entrambi i testi perche' l'aggiramento resti
  leggibile nel diff.
- **R2-4**: FR-003 enumerava cinque categorie e lasciava fuori dell'altro testo
  visibile, **fra cui la riga che enuncia la regola della mappa**. Invertito:
  traducibile e' tutto il testo visibile, con esenzione per elenco chiuso e
  dichiarata per singolo elemento.
- **R2-5**: mancava la FAQ, obbligatoria per regola CRITICAL, mentre la casella
  «All mandatory sections completed» era spuntata. Aggiunta.

Undici non bloccanti chiusi: la citazione di memoria che non nominava la build
map, l'intervallo dei numeri a lettere con il metodo dichiarato, i caratteri
di marcatura contati come prosa, il `try/catch` attribuito a uno storage
inesistente, il conteggio dei criteri manuali dato in due modi, le due spunte
false, le tre sedi mancanti di FR-010, l'asimmetria dell'impronta, i due criteri
automatizzabili spediti al manuale, la collocazione della guardia e il tempo di
parete dentro un requisito.

**Prossimo passo**: round 3 sulla revisione 3.


## Round 3 — NOT CONVERGED, 9 rilievi, 1 bloccante

Tutti chiusi nella revisione 4.

**Il bloccante, R3-1, e' la recidiva esatta di R2-1**: la correzione dell'emendamento
ha riparato il CORPO della costituzione e non il LOG dell'emendamento nello stesso
file, ne' la memoria che lo registra — che `constitution.md:108` elenca fra i
quattro adempimenti che rendono valido un emendamento, quindi era il record
costitutivo a dire il falso sul proprio contenuto. Le tre copie sono ora
rilavorate insieme.

Otto non bloccanti: tre frasi altrove promettevano ancora l'inderogabilita' che
D-4 aveva appena ritirato, e una l'aveva scritta il commit stesso della
correzione; il conteggio dei criteri manuali era di nuovo dato in due modi, dopo
che il round 2 aveva chiuso proprio quel rilievo; la dispersione dei tempi era
calcolata sul massimo e dichiarata sul minimo (69,6%, non 41%); l'etichetta del
terzo metodo di conteggio era sbagliata; due cifre secche sopravvivevano accanto
all'intervallo che le sostituiva; l'elenco chiuso di FR-003a non copriva nomi di
branch e citazioni autore-anno; FR-010 diceva «tutte le sedi» e ne nominava
cinque su sette; «quasi tremila caratteri» erano 3 252.

## LA TERZA REGOLA DI PROCESSO, che e' il prodotto di questo round

> **Prima di scrivere «chiuso», si greppa l'AFFERMAZIONE corretta su tutto il
> branch, non il rilievo che la nominava.**

Tre round di fila hanno prodotto lo stesso guasto: la correzione viene applicata
dove il rilievo puntava e non dove la stessa affermazione vive. Il round 2 ha
trovato un emendamento committato senza rilavorare il verbale; il round 3 ha
trovato un corpo corretto senza il suo log, un «inderogabile» ritirato in un
punto su quattro, un intervallo adottato accanto a due cifre secche rimaste, e
un conteggio ricalcolato senza guardare le marcature che lo contraddicevano.
**Quattro dei nove rilievi di questo round sparirebbero con quel solo passo.**

E' la terza dopo quelle nate dal gate di fase 6 — si estende una guardia solo per
una violazione osservata; una correzione si giudica dai mutanti che smette di
uccidere. Tutte e tre dicono la stessa cosa da tre angoli: **il difetto non e'
dove lo si e' visto**.

**Prossimo passo**: round 4 sulla revisione 4.

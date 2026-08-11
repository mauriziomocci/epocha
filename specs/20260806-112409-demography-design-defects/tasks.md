# Tasks — Demography design defects

> **Ricostruito il 2026-08-11, al gate di fase 6.** Questo file mancava: il
> percorso Spec Kit lo elenca come deliverable della fase 4 e l'audit del
> codice lo ha rilevato come assente. È ricostruito dal `plan.md` e dalla
> storia dei commit, quindi registra ciò che è stato **eseguito**, non ciò che
> era stato pianificato prima di eseguirlo. La distinzione va tenuta: un
> tasks.md scritto dopo non ha svolto la funzione di guida per cui esiste, e
> il modo di non ripetere l'omissione è scriverlo prima, non scriverlo meglio.

Ordine e numerazione seguono `plan.md`. Ogni voce chiusa porta il commit che
la ha chiusa.

## Fase 0 — Deliberazioni scientifiche (GATE PESANTE)

- [x] **0.1a** Famiglia distribuzionale: normale troncata contro scala latente logit. Deciso per la troncata; il logit era stato adottato in `research.md` e poi ribaltato quando l'argomento sulla massa di bordo è collassato (la banda che lo comprava era chiusa dai valori dichiarati dall'emendamento stesso).
- [x] **0.1b** Orizzonte di pianificazione della migrazione: valore attuale scontato per Todaro (1969) con orizzonte e definizione di costo di Sjaastad (1962). Harris & Todaro (1970) è a un solo periodo e non può licenziare un orizzonte.
- [x] **0.1c** Orizzonte di sussistenza: grandezza derivata, nessun `N` globale.
- [x] **0.2** Ordini di grandezza dei parametri.
- [x] **0.3** Verifica dell'attribuzione a Chetty: **fabbricata**. Sostituita con Black & Devereux (2011), Tabella 3, Plug congiunto, `ρ = 0,60` come SOMMA.
- [x] **0.4** Scrittura dell'emendamento A1-A12 in coda alla spec di design.
- [x] **0.5** GATE PESANTE: audit avversariale fino a CONVERGED. Converso al round 11, dopo due cancellazioni strutturali (tetto sulla massa di bordo, banda di ampiezza), entrambe di soglie ancorate al valore che dovevano ammettere.

## Fase 1 — Validazione dei template (US 7, FR-014, SC-015a)

- [x] **1.1** Schema dichiarativo e sei clausole di `validate_template`, ciascuna provata per mutazione.
- [x] **1.2** `truncated_moments.py`: punto fisso deterministico su griglia, regione ammissibile, dispersione di rango.
- [x] **1.3** I cinque template dichiarano `era_noise`; rimozione di `heritability.default`.
- [x] **1.4** Chiusura dell'insieme dei caratteri trasmessi.
- [x] **1.5** Whitepaper §6.2 in entrambe le lingue + riga di doc-sync mancante.

## Fase 2 — Nucleo della trasmissione

- [x] **2.1** Famiglia distribuzionale e kernel poligenico (FR-002, FR-003) — le tre scale del residuo dall'identità di varianza, coefficiente a genitore singolo dimezzato, segnale sullo scostamento dalla media d'era.
- [x] **2.2** Parametri di rumore per era (FR-004) — e la scoperta che l'istruzione leggeva una chiave che lo schema ora rifiuta.
- [x] **2.3** Innovazione dell'istruzione e di Clark (FR-002b) — `5e28677`, `4d3a17a`, `40dcc8b`.
- [x] **2.4** Accoppiamento assortativo (FR-013, SC-017) — `6fb8ca4`. Ha richiesto lo strumento che mancava: nessun solver committato poteva rigenerare le soglie che A4 pubblicava come misurate.

## Fase 3 — Successione ed economia

- [x] **3.1** Quota coniugale shari'a per genere (FR-005) — `ca4e519`.
- [x] **3.2** Conservazione esatta dell'imposta, costruzione di Sterbenz (FR-007) — `ca4e519`.
- [x] **3.3** Valori di regressione dei template, `ρ = 0,60` (FR-009) — `ca4e519`.

## Fase 4 — Migrazione

- [x] **4.1** Guadagno atteso come valore attuale (FR-006) — `923846f`.
- [x] **4.2** Orizzonte di sussistenza applicato a migrazione e fertilità (FR-008) — `923846f`, `8a969fc`.
- [x] **4.3** Stabilità di zona dichiarata valore di simulazione (FR-015) — `923846f`.

## Fase 5 — Chiusura

- [x] **5.1** Whitepaper §4.1.2, §4.1.4, §4.1.5, §6.2 e §11 in entrambe le lingue (FR-010), con la dichiarazione esplicita di non comparabilità.
- [x] **5.2** Suite intera, lint, controllo migrazioni.
- [ ] **5.3** GATE PESANTE: audit avversariale sul codice fino a CONVERGED. Round 1: **NOT CONVERGED**, 18 rilievi. Round 2: **NOT CONVERGED**, 9, di cui il bloccante introdotto dalla remediation del round 1. Round 3: **NOT CONVERGED**, 13, con la stessa classe di difetto sulla citazione colta per la terza volta. Round 4: **NOT CONVERGED**, 7, di nuovo la citazione — chiusa ora con una guardia strutturale (`test_citation_hygiene.py`) invece che con una quinta passata a mano; ha trovato sette occorrenze in più al primo colpo. Tutti e 47 chiusi; round 5 da lanciare.
- [ ] **5.4** Merge e ri-pin del whitepaper al commit di merge. **Richiede ratifica esplicita dell'utente**: il piano la colloca qui e nessun gate la sostituisce.

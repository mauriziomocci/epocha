# Feature Specification: Demografia Plan 4 — inizializzazione, cablaggio, validazione

**Branch**: `20260826-144432-demography-plan4-wiring`
**Creata**: 2026-08-26

## Il problema

I cinque moduli demografici sono scritti, auditati e coperti da test unitari:
`mortality`, `fertility`, `couple`, `inheritance`, `migration`, per un totale di
quarantatré funzioni pubbliche. Il §4.1 del whitepaper li documenta come Methods.

**Il tick loop non ne chiama nessuno.** L'unico contatto è
`set_avoid_conception_flag`, invocato da `apply_agent_action` quando un agente
sceglie di evitare il concepimento. Nessun agente nasce, nessuno muore di
mortalità demografica, nessun asse ereditario si liquida, nessuno migra.

Questo è lo scarto peggiore che il progetto porti: un modello scientifico
completo, auditato e pubblicato, che **non gira**. La build map lo dichiara da
mesi con la formula «i modelli sono auditati ma il loop non li chiama mai», e
finché resta vero ogni risultato del simulatore descrive una popolazione che non
nasce, non muore e non si sposta.

## Scope

Il Plan 4 chiude quello scarto. Tre parti, in quest'ordine:

1. **Inizializzazione**: una popolazione di partenza che soddisfi le precondizioni
   dei moduli — età, sesso, coppie, classe sociale, istruzione — invece della
   popolazione piatta che il generatore LLM produce oggi.
2. **Cablaggio**: i cinque moduli chiamati dal tick loop, in un ordine dichiarato
   e giustificato.
3. **Validazione storica**: la popolazione simulata confrontata con dati
   demografici reali, che è ciò che distingue un simulatore scientifico da un
   gioco.

**Fuori scope**, e dichiarato: la validazione contro i benchmark pubblicati
(Human Mortality Database, Wrigley-Schofield, carestia irlandese, Hajnal) resta
il work item separato che la memoria `project_validation_experiments_pending.md`
già traccia. Qui si costruisce la macchina che rende quegli esperimenti
eseguibili, non gli esperimenti.

## User Scenarios & Testing *(mandatory)*

### US1 — La popolazione vive (P1)

Un operatore avvia una simulazione con la demografia attiva e, al passare dei
tick, vede nascite, morti, formazioni di coppia, successioni e migrazioni
comparire negli eventi.

**Test di accettazione**:
1. Su una simulazione di N tick con un template d'era dichiarato, il registro
   eventi contiene almeno una nascita e almeno una morte, e la popolazione varia.
2. Ogni evento demografico è tracciabile al modulo che l'ha prodotto.
3. Una simulazione **senza** demografia configurata gira esattamente come prima,
   senza errori e senza eventi demografici: il cablaggio non rompe le
   simulazioni economiche.

### US2 — L'ordine del tick è dichiarato e rispettato (P1)

I cinque moduli non sono commutativi. Chi muore in questo tick non deve poter
concepire nello stesso tick; l'asse ereditario di chi muore si liquida dopo che
la morte è registrata; chi migra lo fa sulla base dei salari di zona di questo
tick, non del precedente.

**Test di accettazione**:
1. L'ordine è **scritto** nel codice come sequenza esplicita, non implicito
   nell'ordine delle chiamate.
2. Un agente che muore al tick T non genera nascite al tick T.
3. La successione di un agente morto al tick T avviene al tick T, dopo la morte.
4. Ogni proprietà d'ordine sopra è provata **per mutazione**: si scambiano due
   passi e il test diventa rosso.

### US3 — Il contatore di fame esiste (P1)

`evaluate_emergency_flight` prende `consecutive_ticks_under_subsistence` come
argomento perché nessun campo del genere esiste nello schema. È l'obbligo che il
Plan 3 ha lasciato scritto: senza quello storage la fuga d'emergenza non può
scattare in un'esecuzione viva, e il modulo è codice morto.

**Test di accettazione**:
1. Il contatore è persistito, si incrementa quando l'agente è sotto la soglia di
   sussistenza e si azzera quando risale sopra.
2. `process_emergency_flight` legge quel valore invece di riceverlo dal chiamante.
3. Provato per mutazione: un contatore che non si azzera fa fallire un test.

### Edge Cases

- **Simulazione senza template d'era**: il cablaggio deve degradare in silenzio,
  come già fa `apply_agent_action`, e non abortire il tick.
- **Popolazione a zero**: quando l'ultimo agente muore, il tick successivo non
  deve sollevare eccezioni.
- **Costo per tick**: cinque moduli su N agenti possono introdurre N+1 query. Il
  budget va misurato e dichiarato, non scoperto in produzione.
- **Determinismo**: i moduli demografici usano `get_seeded_rng`; il tick loop
  deve passare il seme, altrimenti la demografia eredita il difetto dell'RNG
  globale non seminato che i rischi trasversali della build map già registrano.

## Requirements *(mandatory)*

- **FR-001**: il tick loop chiama i cinque moduli demografici quando la
  simulazione dichiara un template d'era, e non li chiama quando non lo dichiara.
- **FR-002**: l'ordine dei passi demografici dentro il tick è **dichiarato come
  dato**, non come sequenza di istruzioni, così che sia leggibile e verificabile
  senza rileggere il corpo della funzione.
- **FR-003**: la mortalità precede la fertilità nello stesso tick.
- **FR-004**: la successione di un agente segue la sua morte nello stesso tick.
- **FR-005**: la migrazione usa le statistiche di zona del tick corrente.
- **FR-006**: il contatore di tick consecutivi sotto la soglia di sussistenza è
  **persistito** sull'agente, incrementato e azzerato dal tick loop.
- **FR-007**: `process_emergency_flight` legge il contatore persistito.
- **FR-008**: ogni chiamata demografica riceve un RNG seminato, mai il `random`
  globale.
- **FR-009**: una simulazione senza demografia configurata resta invariata: stesso
  numero di query, nessun evento nuovo, nessun errore.
- **FR-010**: il costo per tick del blocco demografico è **misurato e dichiarato**
  in numero di query e in tempo, su una popolazione di riferimento nominata.
- **FR-011**: l'inizializzazione produce una popolazione le cui precondizioni
  soddisfano i cinque moduli: età distribuita, sesso assegnato, classe sociale e
  istruzione presenti.
- **FR-012**: il whitepaper §4.1 in entrambe le lingue documenta il cablaggio e
  l'ordine dichiarato, nello stesso commit del codice.

## Success Criteria *(mandatory)*

- **SC-001**: su una simulazione di riferimento la popolazione cambia nel tempo,
  con nascite e morti registrate.
- **SC-002**: l'ordine dei passi è verificabile leggendo un dato, e ogni proprietà
  d'ordine è provata per mutazione.
- **SC-003**: il contatore di fame si incrementa e si azzera come prescritto,
  provato per mutazione.
- **SC-004**: una simulazione economica pura non cambia comportamento: stesso
  conteggio di query, nessun evento demografico.
- **SC-005**: il costo per tick è dichiarato con un numero misurato.
- **SC-006**: suite intera verde, `test_citation_hygiene.py` e
  `test_build_map_bilingual.py` compresi.

## Assumptions

- I cinque moduli sono corretti come auditati: questo work item li **chiama**, non
  li rivede. Un difetto trovato nei moduli va escalato, non corretto qui.
- La popolazione di riferimento per le misure di costo è quella dell'MVP.
- La validazione contro benchmark storici è un work item successivo.

## Non-goals

- Non si riscrive alcun modulo demografico.
- Non si esegue la validazione contro HMD, Wrigley-Schofield, Hajnal.
- Non si tocca l'economia, se non per leggere i salari di zona che la migrazione
  già consuma.

## Rischi dichiarati

- **Il rischio maggiore è l'ordine.** Cinque moduli che mutano lo stesso stato in
  un tick hanno un ordine giusto e molti sbagliati, e uno sbagliato produce
  risultati plausibili — una popolazione che cresce o cala in modo credibile — che
  nessun test superficiale distingue. È per questo che FR-002 chiede l'ordine
  come dato e SC-002 lo prova per mutazione.
- **Il secondo è il costo.** `process_inheritance_batch` e
  `build_migration_outlook` sono le due funzioni più pesanti del sottosistema; il
  budget va misurato prima di dichiarare il lavoro finito, non dopo.
- **Il terzo è il determinismo.** I moduli sono pronti per un RNG seminato ma il
  tick loop vive in un'app dove il `random` globale non è mai seminato. Cablare
  senza passare il seme estenderebbe alla demografia un difetto che la build map
  registra fra i rischi trasversali.

## FAQ

**Perché non si valida contro i dati storici in questo work item?** Perché la
validazione richiede che la macchina giri, e oggi non gira. Costruire le due cose
insieme significherebbe non sapere, davanti a uno scostamento, se è sbagliato il
modello o il cablaggio.

**Perché l'ordine come dato e non come codice?** Perché un ordine scritto come
sequenza di chiamate si verifica solo rileggendo la funzione, e si cambia per
sbaglio spostando una riga. Come dato è ispezionabile da un test.

**Il contatore di fame non poteva stare in memoria?** No: il tick loop è
distribuito su task Celery e lo stato in memoria non sopravvive al processo. La
regola del progetto dice stato nel database, mai in variabili globali.

**Che cosa succede alle simulazioni esistenti?** Nulla, se non dichiarano un
template d'era. FR-009 lo rende un requisito verificato, non una speranza.

**Come si saprà che l'ordine scelto è quello giusto?** Non lo si saprà da questo
work item: si saprà dalla validazione storica, che è il work item successivo.
Qui l'ordine è dichiarato, giustificato e reso verificabile, il che è la
precondizione perché quella validazione significhi qualcosa.

# Implementation Plan: Correzione dei difetti di design della demografia

**Branch**: `20260806-112409-demography-design-defects` | **Date**: 2026-08-06 | **Spec**: [spec.md](./spec.md)

**Input**: la specifica convergente al gate pesante di fase 2, round 5 ([report](./audit/phase2-round-5-CONVERGED.md)).

## Summary

Questo work item non aggiunge una funzionalità: **corregge un modello scientifico sbagliato**, e la sua forma è di conseguenza inusuale. Il deliverable primario non è codice ma un **emendamento a `docs/superpowers/specs/2026-04-18-demography-design-it.md`**, una spec dichiarata CONVERGED nell'aprile 2026 dopo quattro round di audit. Il codice segue l'emendamento; non lo precede.

Dieci difetti sono in ambito. Sette hanno una correzione già derivata e pubblicata, e per essi l'emendamento **registra** una decisione. Tre richiedono deliberazione vera, e sono il cuore della fase 0:

1. **quale famiglia distribuzionale** per un carattere limitato a `[0,1]` che oggi si campiona da una normale non limitata e poi si tronca;
2. **quale orizzonte di pianificazione** rende dimensionalmente coerente il guadagno atteso di migrazione;
3. **quale orizzonte di sussistenza** — test di fame o test di risparmio precauzionale — e la riscrittura della riga 153 del design, che è internamente incoerente.

Da queste tre discende tutto il resto: la famiglia distribuzionale determina la scala del residuo di ogni ramo di parentela, l'orizzonte di migrazione determina la formula, l'orizzonte di sussistenza ricade su due consumatori.

## Technical Context

**Language/Version**: Python 3.12, Django 5.x.

**Moduli toccati**: `epocha/apps/demography/{inheritance,migration,fertility,template_loader}.py`, i cinque template in `epocha/apps/demography/templates/*.json`, i test in `epocha/apps/demography/tests/`.

**Documenti toccati**: `docs/superpowers/specs/2026-04-18-demography-design-it.md` (l'emendamento), `docs/whitepaper/epocha-whitepaper.md` e `.it.md` (§4.1.4, §4.1.5, §4.1.2, §6.2, §11).

**Testing**: pytest nel container (`docker compose -f docker-compose.local.yml exec -T web pytest`), PostgreSQL. Autorità per lint: `ruff` nel container.

**Baseline**: suite di progetto a 1191 test verdi, demografia a 372, zero migrazioni pendenti al merge `1cdcfa4`.

**Vincolo di schema**: a differenza della Plan 3, **questo piano non è vincolato a zero migrazioni**. Se la famiglia distribuzionale o i parametri per tratto richiedono un campo, si può aggiungere — ma ogni migrazione va giustificata nell'emendamento, non decisa in fase di implementazione.

**Performance**: nessun obiettivo nuovo. I meccanismi toccati sono per-nascita e per-decisione, già dentro budget di query documentati; l'unico rischio è che aggiungere un'estrazione casuale dove non c'era alteri il consumo del flusso RNG, il che è un problema di **determinismo**, non di prestazioni (vedi sotto).

**Scale/Scope**: dieci difetti, otto user story, diciassette requisiti funzionali, sedici criteri di successo.

## Constitution Check

*GATE: da superare prima della fase 0, da ricontrollare dopo la fase 1.*

| Principio | Stato | Note |
|---|---|---|
| **I — Metodo scientifico** | **passa, ed è il motivo per cui il work item esiste** | Ogni correzione deve citare una fonte primaria. Tre parametri nuovi nasceranno (innovazione dell'istruzione, innovazione di Clark, orizzonte di migrazione) e nessuno può essere un numero scelto: o è derivato da una fonte, o è dichiarato euristica tarabile con la sua giustificazione. |
| **II — Verificare prima di asserire** | **passa con obbligo esplicito** | Il preflight di verifica del codice è obbligatorio prima di ogni task. Questo piano ne eredita uno già svolto: cinque round di gate hanno misurato ogni cifra della spec contro il codice. Le misure restano valide finché il codice non cambia, e vanno ri-verificate dopo ogni correzione, perché le correzioni interagiscono. |
| **III — Audit avversariale** | **passa** | Due gate: sulla spec di design emendata (fase 0, prima di qualunque codice) e sul codice prima del merge. Entrambi con ciclo di convergenza fino a CONVERGED esplicito. |
| **IV — Processo di design in tre passi** | **passa, e vincola la fase 0** | L'emendamento è un documento di design: proposta iniziale, prima autocritica, seconda autocritica e consolidamento — poi si scrive. Saltare passi è vietato. |
| **V — Verifica basata su evidenza** | **passa con una limitazione dichiarata** | La demografia **non è cablata nel tick loop**: il cablaggio è del Plan 4. Nessuna correzione di questo work item è quindi osservabile in un ambiente reale finché quel piano non atterra. Ogni affermazione di questo work item sarà quindi al massimo "verificata su popolazione sintetica e suite", mai "verificata in produzione", e va dichiarato così. |

**Nessuna violazione da giustificare.** La tabella di Complexity Tracking resta vuota.

## Project Structure

### Documentation (this feature)

```text
specs/20260806-112409-demography-design-defects/
├── spec.md                            # fase 2, CONVERGED round 5
├── checklists/requirements.md         # checklist di qualità della spec
├── audit/phase2-round-5-CONVERGED.md  # verdetto del gate pesante
├── plan.md                            # questo file
├── research.md                        # fase 0 — LE TRE DELIBERAZIONI, il cuore del lavoro
└── tasks.md                           # fase 4, via /speckit-tasks
```

**`data-model.md` e `contracts/` non vengono materializzati.** Non c'è un modello di dati nuovo da descrivere: il lavoro modifica formule e parametri dentro moduli esistenti, e le uniche strutture dati toccate sono sezioni di template JSON, che la spec già enumera. Non c'è interfaccia esterna: la demografia è consumata dall'orchestratore del Plan 4, non da API o CLI. Materializzarli produrrebbe cerimonia, coerentemente con la scelta già fatta nella Plan 3 per la stessa ragione.

**`research.md` viene invece materializzato, ed è il documento più importante di questa fase.** È l'opposto della Plan 3, dove non c'era nulla da ricercare perché il design era convergente: qui la ricerca *è* il lavoro, perché tre decisioni scientifiche vanno prese e nessuna ha oggi una risposta nel progetto.

### Source code (repository root)

```text
docs/superpowers/specs/
└── 2026-04-18-demography-design-it.md   # L'EMENDAMENTO — deliverable primario

epocha/apps/demography/
├── inheritance.py       # kernel poligenico, istruzione, Clark, imposta di successione
├── migration.py         # guadagno atteso, condizione di fuga, stabilità di zona
├── fertility.py         # segnale di ricchezza (eredita la decisione sull'orizzonte)
├── template_loader.py   # validazione oggi assente
├── templates/*.json     # parametri di rumore, valori di regressione
└── tests/               # test-first per ogni correzione

docs/whitepaper/
├── epocha-whitepaper.md      # §4.1.2, §4.1.4, §4.1.5, §6.2, §11
└── epocha-whitepaper.it.md   # le stesse, in lockstep
```

**Structure Decision**: nessun modulo nuovo, nessuna app nuova. Tutte le correzioni vivono dove vive il difetto. La sola domanda di collocazione non banale — dove risiedano i parametri di rumore per tratto e per era — è una delle tre deliberazioni di fase 0, e la sua risposta determina se serva una sezione di template nuova o un parametro di progetto.

## Build order

Strettamente sequenziale. Ogni passo termina verde e con la suite intera in bolla.

### Fase 0 — L'emendamento al design (nessun codice)

**0.1 — Le tre deliberazioni**, ciascuna col processo in tre passi del principio IV, consolidate in `research.md`:

- **La famiglia distribuzionale.** Alternative da valutare esplicitamente: Beta, normale logit-trasformata, normale troncata con adattamento dei momenti. Criterio: l'ampiezza dichiarata deve essere quella realizzata, e la proprietà deve reggere anche quando la media d'era non è centrata — verificato che a media 0,8 il troncamento attuale costa otto punti. Vincolo noto: una famiglia che tenga la normale troncata e risolva una media per tratto a 0,8 porterebbe il ramo senza genitori all'86,4% e **fallirebbe** SC-013, quindi il cambio di famiglia è di fatto obbligato.
- **L'orizzonte di pianificazione della migrazione.** Todaro (1969) è la fonte più vicina, perché il modello da riparare è il suo e la sua formulazione porta già un orizzonte scontato; Sjaastad (1962) è la fondazione più generale. Da decidere: quale istanziare, con quale orizzonte e quale tasso di sconto, e con quale effetto sulla soglia migratoria.
- **L'orizzonte di sussistenza.** Test di fame (un tick) o test di risparmio precauzionale (`N` tick)? La riga 153 va riscritta in ogni caso, perché è incoerente. Va dichiarata l'interazione con `flight_trigger_ticks`, che vale anch'esso 30, e la decisione ricade su fertilità e migrazione insieme.

**0.2 — Le magnitudini dei parametri nuovi**: l'ampiezza di innovazione dell'istruzione e quella di Clark. La mobilità alla Becker-Tomes ha già la propria, con giustificazione misurata, e va presa a modello.

**0.3 — La verifica dell'attribuzione a Chetty**, prima che 0,35 diventi il bersaglio di FR-009. La spec di design cita la stessa fonte in due punti per due grandezze diverse.

**0.4 — Scrittura dell'emendamento** a `2026-04-18-demography-design-it.md`, con FAQ obbligatoria per le decisioni non ovvie.

**0.5 — GATE PESANTE: audit avversariale sull'emendamento**, ciclo di convergenza fino a CONVERGED esplicito. **Nessun codice prima di questo verdetto.**

### Fase 1 — La guardia strutturale, per prima

**1.1 — Validazione dei template** (User Story 7). Va per prima, e non è un dettaglio di sequenza: è il meccanismo che ha lasciato entrare metà dei difetti che stiamo correggendo. Un caricatore che accetta un'aliquota di 40 e una regressione negativa non impedirà alla prossima modifica di reintrodurre la stessa classe di difetto. Costruirlo prima significa che ogni correzione successiva atterra dentro una rete già tesa. Include la correzione del §6.2 del whitepaper, che oggi pubblica come vera una proprietà assente.

### Fase 2 — Il nucleo di trasmissione

**2.1 — La famiglia distribuzionale e il kernel poligenico** (FR-002, FR-002a, FR-003): residuo corretto in **tutti e tre** i rami di parentela, coefficiente a genitore singolo dimezzato.
**2.2 — I parametri di rumore per era e per tratto** (FR-004). Interagisce con 2.1: risolvere le medie sposta il troncamento.
**2.3 — L'innovazione dell'istruzione e di Clark** (FR-002b). Dipende da 2.2 per i propri parametri.
**2.4 — L'accoppiamento assortativo** (FR-013): 2.3 lo risveglia in tutte e cinque le ere, non nella sola sci-fi.

Ordine obbligato: 2.1 prima di 2.2 perché la famiglia determina cosa significhi "ampiezza"; 2.2 prima di 2.3 perché l'istruzione ha bisogno di un parametro che oggi non esiste; 2.4 per ultimo perché è la conseguenza di 2.3.

### Fase 3 — Successione ed economia

**3.1 — La quota coniugale shari'a** (FR-005), con la fonte primaria corretta e il trattamento del coniuge non binario.
**3.2 — La conservazione esatta dell'imposta** (FR-007), sull'intero dominio di aliquote, non sulle sole spedite.
**3.3 — I valori di regressione dei template** (FR-009), dopo 0.3.

Indipendenti fra loro e dalla fase 2; ordinabili come conviene.

### Fase 4 — Migrazione

**4.1 — Il guadagno atteso** (FR-006), con l'orizzonte deciso in 0.1. Attenzione all'interazione con la correzione del divisore del salario già atterrata nella Plan 3, che ha spostato quel valore del venti per cento.
**4.2 — L'orizzonte di sussistenza** (FR-008), applicato a migrazione **e** fertilità.
**4.3 — La stabilità di zona** (FR-015): o un segnale reale per zona, o la dichiarazione esplicita che è un valore di simulazione.

### Fase 5 — Chiusura

**5.1 — Whitepaper §4.1.2, §4.1.4, §4.1.5, §6.2 e §11 in entrambe le lingue** (FR-010): sostituire la dichiarazione dei difetti con la descrizione dei modelli corretti, e **dichiarare la non comparabilità** fra risultati prodotti prima e dopo. Include la correzione dei due rimedi errati che il §4.1.4 oggi pubblica.
**5.2 — Suite intera, lint, controllo migrazioni.**
**5.3 — GATE PESANTE: audit avversariale sul codice**, fino a CONVERGED.
**5.4 — Merge, re-pin del `frozen-at-commit` al SHA del merge, sincronizzazione delle memorie.**

## Rischi e insidie note

**Il determinismo è il rischio principale, e non è ovvio.** Le fasi 2.3 e 2.4 aggiungono estrazioni casuali dove oggi non ce ne sono. Ogni estrazione nuova **sposta il flusso RNG condiviso**, quindi ogni test che oggi fissa un valore atteso da un seme cambierà risultato — non perché sia sbagliato, ma perché la sequenza è cambiata. Vanno distinti i fallimenti dovuti alla sequenza da quelli dovuti a un difetto, e i secondi vanno indagati, non riallineati. La disciplina del progetto è chiara: un seme non si cambia per far tornare un test.

**Le correzioni interagiscono, e le misure di baseline scadono.** Il collasso al 48,8%, i tre rami di parentela, il costo del troncamento: sono misure sul codice attuale. Ogni fase ne invalida alcune. Le cifre della spec sono la fotografia del punto di partenza, non un riferimento perenne.

**Il rischio di riallineare i test invece del modello.** Nessun benchmark di calibrazione eseguibile esiste oggi — verificato — quindi non c'è una rete indipendente che dica se il modello corretto è più realistico di quello sbagliato. Il criterio FR-012 vincola i benchmark futuri, non un insieme esistente, e questo va tenuto presente: le correzioni si giudicano sulle fonti, non sui test che scriviamo noi.

**L'errore che si è ripetuto cinque volte nel gate di fase 2**, e che si ripeterà qui se non lo si sorveglia: scrivere un criterio che non può fallire dove il requisito è falso. Ogni test di questo work item va provato per mutazione — iniettare il difetto, vederlo fallire, ripristinare — non per sola ispezione.

## Integration surface

- **Consumato, invariato**: `get_seeded_rng`, `load_template`, `compute_subsistence_threshold`, `add_to_treasury`.
- **Modificato**: i quattro moduli demografici elencati, i cinque template, il design spec, i due whitepaper.
- **Non toccato**: `epocha/apps/simulation/engine.py`. Il cablaggio resta del Plan 4 — e poiché la demografia non è ancora guidata dal tick, nessuna correzione di questo work item cambia il comportamento di una simulazione in esecuzione finché quel piano non atterra.
- **Ereditato dal Plan 4**: il contatore di tick consecutivi sotto sussistenza, che oggi è un argomento perché il campo non esiste a schema. Se la fase 4.2 dovesse richiederne uno diverso, va coordinato.

## Complexity Tracking

Nessuna violazione della costituzione da giustificare.

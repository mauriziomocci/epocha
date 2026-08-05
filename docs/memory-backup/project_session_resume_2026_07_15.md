---
name: session-resume-2026-07-15
description: "AGG. 2026-08-05: DEMOGRAFIA PLAN 3 CHIUSA E MERGIATA in develop (merge SHA 1cdcfa4), 47/47 task, audit fase 6 CONVERGED al round 4, suite 1191. inheritance.py (13 funzioni) e migration.py (8) esistono; whitepaper §4.1 esteso EN+IT; frozen-pin risolto a 1cdcfa4 (14 posizioni/lingua). Frontiera ora: Plan 4 (initialization + engine wiring + validazione storica) e audit KG §8.1. Plan 4 EREDITA un obbligo: evaluate_emergency_flight riceve il contatore di fame come argomento perche' il campo non esiste a schema -- Plan 4 deve crearlo. Aperto anche il work item separato sugli 8 difetti di DESIGN (kernel poligenico non conserva la varianza in testa). Sezione precedente: CHIUSO 2026-07-17 economy base layer CONVERGED round 12, promosso a §4.8, mergiato (368e972, PR#14). Frozen-pin risolto (9893bba: 8a2bc71 E 7ec6548 -> 368e972, 12 posizioni per lingua). Suite 911 verdi, ruff pulito su develop post-merge. Residuo §8 = solo 8.1 Knowledge Graph. Frontiera progetto: cablaggio demografia Plan 4 (i modelli §4.1 sono auditati ma il tick loop NON li chiama) + audit KG. STATO DI BUILD: non leggerlo qui, la fonte di verita' e' la build map -- vedi [[build-map-source-of-truth]]. Decisioni ratificate dell'economia (non rilitigare): [[economy-ratified-decisions]]. Gli handoff handoff-economy-audit-2026-07-15/17.md sono stati RIMOSSI a lavoro chiuso: il loro contenuto durevole vive nella spec committata specs/20260715-132752-economy-base-layer-audit/ e in [[economy-ratified-decisions]]. Storia Round 1-12 sotto."
metadata: 
  node_type: memory
  type: project
  originSessionId: 974793b8-cb10-48cc-b5ea-ac2703f04516
  modified: 2026-08-05T14:44:29.707Z
---

# Sessione 2026-08-05 -- Chiusura demografia Plan 3 (mergiata in develop)

**CHIUSO E MERGIATO**: merge SHA **`1cdcfa4`**, `--no-ff` da `20260717-120706-demography-inheritance-migration`. **NON pushato** (regola: mai auto-push). 47/47 task. Suite intera **1191 passed**, ruff pulito, zero migrazioni pendenti.

## Cosa e' stato costruito

`inheritance.py` (13 funzioni pubbliche: kernel poligenico, evaluator AST ristretto, classe sociale, istruzione, scala eredi, imposta di successione, cinque regole successorie, trasferimento prestiti, caretaker orfani, cascata del lutto, batch morti simultanee) e `migration.py` (8: salario e disoccupazione di zona, costo distanza, guadagno atteso Harris-Todaro, outlook, coordinamento familiare Mincer, fuga d'emergenza, crisi intrappolata, fuga di massa). Suite demografia da 183 a **372** test. `engine.py` byte-identico al merge base: il cablaggio e' Plan 4.

## L'audit di fase 6 -- quattro round, la lezione della sessione

**Round 1: 22 finding su una suite gia' verde a 308 test.** Il peggiore: sotto `becker_tomes` (regola della democrazia moderna) il rumore gaussiano spingeva il rango oltre la fine della scala sociale, e li' c'era `enslaved` -- **25,2% dei figli di genitori poveri in zona povera**, senza alcun genitore schiavo. Anche: `mental_health` mai ereditata perche' i template dichiaravano un campo inesistente (`mental_health_baseline`).

**Round 2: due dei fix del round 1 avevano introdotto difetti PEGGIORI.** Un `KeyError` in `transfer_loans_as_lender` sotto `matrilineal` che faceva rollback dell'INTERO batch di successioni; e il fix M-3 che, allargando l'esclusione dei testimoni, portava a **zero** la propagazione FR-026 proprio nello scenario di carestia per cui era stato scritto.

**Round 3: un test dichiarato risolto moltiplicava per zero il coefficiente che diceva di fissare** (genitori `elite` = rango 0, quindi `0.7 * 0`). Lo sweep mostrava che 0.65, 0.70, 0.75, 0.79, 0.80 passavano tutti la suite.

**Round 4: CONVERGED.** Verificato con sweep indipendenti dei coefficienti, 46 famiglie di payload al parser, 45 all'evaluator, 7 mutazioni, 12.730 allocazioni di conservazione.

**LA LEZIONE, da non dimenticare: una suite verde non dice quasi nulla sulla correttezza scientifica.** Ogni difetto grave conviveva con test tutti verdi, e in due casi c'era un test che *proteggeva* il difetto. I test di determinismo confrontavano una funzione pura con se stessa; quelli di conservazione passavano anche contro divisione ingenua, perche' l'importo scelto come "non divisibile" divide esatto in IEEE 754.

## Trappole tecniche verificate (valgono oltre questo branch)

- **`PYTHONHASHSEED` randomizza solo str/bytes, MAI int.** Un test di determinismo in sottoprocesso non cattura iterazioni su `set` di id interi. In `migration.py` (chiavi intere) era inutile; in `inheritance.py` (`set[str]` di nomi di tratti) e' lo strumento giusto. E attenzione alle fixture: id consecutivi rendono `list(set)` e `sorted(set)` identici per costruzione.
- **`sum()` di CPython 3.12 usa sommatoria compensata di Neumaier**, quindi differisce dall'accumulo sinistra-destra nel ~41% dei casi a 11 addendi. Una fixture di conservazione "avversariale" deve soddisfare DUE condizioni, non una.
- **`get_seeded_rng` semina sulla CHIAVE PRIMARIA** oltre che sul seme -- vedi [[determinism-enumeration-pending]] punto 4.

## Cosa resta APERTO

1. **Push di develop** (mai fatto in automatico) e valutazione PR.
2. **Plan 4**: initialization + engine wiring + validazione storica. Chiama `assign_orphan_caretaker` (step 3) e `process_emergency_flight` (step 5), entrambi esistenti. **EREDITA UN OBBLIGO**: `evaluate_emergency_flight` riceve `consecutive_ticks_under_subsistence` come ARGOMENTO perche' quel campo non esiste a schema e SC-005 vietava migrazioni. Plan 4 deve creare lo storage, altrimenti la fuga d'emergenza non puo' scattare in una run reale.
3. **Work item separato sugli 8 difetti di DESIGN** (gate di fase 2 proprio, spec CONVERGED da emendare): kernel poligenico non variance-preserving (varianza dei tratti al 48,8% entro 3 generazioni), fallback genitore singolo che non dimezza il segnale, quota coniugale shari'a gender-blind contro Q4:12, imposta calcolata come due prodotti indipendenti, confronto stock-vs-flusso nel trigger di fuga, tre valori di `education_regression_rho` che contraddicono le fonti citate, parametri era-noise segnaposto, Harris-Todaro dimensionalmente incoerente (sottrae tick da un tasso monetario). **Tutti gia' documentati in whitepaper §4.1 come attualmente veri del modello.**
4. **Audit KG §8.1**, ultimo residuo del capitolo 8.

## Report d'audit committati

`specs/20260717-120706-demography-inheritance-migration/audit/T046-round-{1,2,3}-NOT-CONVERGED.md` e `T046-round-4-CONVERGED.md`. Contengono l'evidenza a file:riga di ogni finding e cosa ogni auditor ha tentato SENZA trovare nulla, per giudicare la copertura e non solo l'output.

---

# Sessione 2026-07-17 -- Chiusura economy base layer (promozione committata, fase 6 fatta)

Lavoro CHIUSO e mergiato (`368e972`, PR#14). Gli handoff di sessione sono stati rimossi: il contenuto durevole vive nella spec committata `specs/20260715-132752-economy-base-layer-audit/` e le decisioni ratificate in [[economy-ratified-decisions]].

## Stato

Branch `20260715-132752-economy-base-layer-audit`, tip **`d353de2`**, **27 commit** su develop, **NON pushato**. Suite container **911 passed**, ruff check + format --check exit 0 (verificati oggi).

## Fatto oggi

- **Mappa 13 fasi** (artifact one-page) + **memoria roadmap rinfrescata** ([[post-mvp-roadmap]]) con stato VERIFICATO contro codice, non contro la memoria stale di 94 giorni. Scoperte chiave: economia cablata (`process_economy_tick_new` a `simulation/engine.py:394,486`); **demografia NON cablata** nel tick (mortality/fertility/couple definiti e testati ma zero chiamate: solo `set_avoid_conception_flag` viene invocato) -> fase 2 è PROG non DONE; **Knowledge Graph zero chiamate dal tick engine**.
- **R12-NEW-1 FIXATO**: anchor `recalculate_deposits()` `banking.py:293-334` -> `:293-320` (corpo finisce a 320; 323-334 sono le costanti `_CONCERN_*`). EN+IT.
- **Dicitura round 6 -> 12**: la handoff diceva 3 punti (§4.8 Status ×2 + Background) ma il grep esaustivo ne ha trovati **8 per lingua** — contaminava anche §3.6 legend, §8 intro, §9 ×2, §11. Lasciarne indietro = whitepaper internamente incoerente (§4.8 dice 12, §8 dice 6). Tutti corretti, verificato 0 residui.
- ~~**R12-DET-1 flaggato** come work item demografia/agents separato~~ -- **RITIRATO 2026-07-17: era un NON-DIFETTO**. `.first()` su queryset non ordinato riceve `order_by("pk")` dall'ORM stesso, quindi i siti erano gia' deterministici e il fix sarebbe stato un no-op. Vedi [[economy-ratified-decisions]]. Il difetto vero e' il caso opposto (`Meta.ordering`/`order_by` parziale che SOPPRIME il tiebreak) ed e' tracciato in [[determinism-enumeration-pending]].
- **Promozione committata**: `d353de2` `docs(economy): promote economy base layer from §8.2 to §4.8` — 2 whitepaper + 8 `audit-workflow-round{5..12}.js`. Docs-only (verificato: `git diff a50358c..HEAD -- epocha/` VUOTO).
- **Fase 6 audit avversariale ESEGUITO** (critical-analyzer sul diff develop..HEAD).

## Verdetto fase 6: codice CONVERGED, un blocco documentale

VERIFIED dall'auditor con evidenza a file:line: conservazione (money BOUNDED_INJECTION_ONLY — uniche iniezioni rent/wage/profit ledgered `from_agent=None`; goods conservati; tax a due gambe gated su Government; partizione fattoriale somma a V senza doppio pagamento), determinismo (tutti i selettori pinnati; due apparenti eccezioni non-difetti: `property_market.py:91-96` legge solo `.tick`, `political_feedback.py:123-125` alimenta `compute_gini` che ordina internamente), credit lifecycle (default terminale una volta, lien a 4 gate, cascade net-of-collateral dal tick corrente, maturity `__lte`), Fisher non tautologico (M si cancella), eq. 4.42-4.45 + tabella parametri fedeli al codice, anchor tutti risolvono, parità EN/IT, nessun bug/race/N+1 nuovo. 382 test economy+simulation verdi.

**UNICO BLOCCO — pin §4.8 stale**: il §4.8 pinna `7ec65484...` che è il commit **round 7**. L'auditor ha PROVATO che quel frame non contiene R7-NEW-1 né R8-NEW-5 e che `recalculate_deposits` lì sta a riga 288 (non 293), quindi l'anchor `banking.py:293-320` non risolverebbe. **NON è un difetto reale**: `7ec6548` è il placeholder noto che va sostituito col **merge SHA** allo step di merge, insieme a `8a2bc71`. L'auditor non conosceva questa convenzione e proponeva `a50358c` — sbagliato, verrebbe sovrascritto al merge. **Il gate NON è chiuso finché il pin non atterra al merge.**

## Rimane (in ordine)

1. Push branch + **Draft PR** verso develop (`/opt/homebrew/bin/gh`).
2. **FERMARSI**: ratifica esplicita dell'utente dei due heavy gate (fase 2 spec + fase 6 chiusura). **BLOCCANTE, nessun merge senza sì esplicito.**
3. Al sì: `merge --no-ff`; **frozen-pin**: sostituire **8a2bc714477f445b46cd610725df40c93fce1557** (frontmatter + header Status §4.x + Appendice B) **E 7ec65484dea8a97236af2912b613d26ed428bb7c** (§4.8 Status ×2 per lingua: EN 1884/1959, IT 1951/2026) -> merge SHA, EN+IT. **NON toccare** i pin non-economia (§4.1/§4.6/§5.4, pinnati ai LORO commit). Poi sync memoria backup (`cp` live -> `docs/memory-backup/`, commit su develop, push).

## Dopo questo branch

Residuo §8 = **solo §8.1 Knowledge Graph** ([[audit-repass-batch-2026-04-12-pending]]). Frontiera progetto: cablaggio demografia Plan 4 + audit KG.

---

# Sessione 2026-07-15 SERA -- Economy base layer audit (Round 1-5)

## STATUS ECONOMY AUDIT (leggere la handoff nella root per i dettagli)

Branch `20260715-132752-economy-base-layer-audit`, 16 commit avanti su develop, tip `bfa0f3d`, NON pushato. Primo audit scientifico avversariale del substrato economico (whitepaper §8.2, 5 moduli). Loop di convergenza:
- Round 1 (10 finding), Round 2 (8), Round 3 (8), Round 4 (determinismo + Fisher + ledger + doc-sync): TUTTI chiusi con fix test-first, un commit per gruppo via git-commit-assistant.
- **LOOP DI AUDIT: Round 1-7 TUTTI CHIUSI, Round 8 IN VOLO** (run `wf_75faf0db-ad2`). 20 commit su develop (tip `21f503b`), NON pushato. Ogni round ha trovato finding sempre più periferici e li ha chiusi test-first (un commit per gruppo): R5 (`7aeb41d`+`7ec6548`) default terminal state + cascade su loss record + Fisher PQ per-zona + doc-sync §4.2.1; R6 (`be260db`) lost-update sulla cassa della prima zona [INCORRECT/high, mancato da 5 round, trovato dal verificatore di conservazione end-to-end] + hardening credit lifecycle + determinismo un livello sopra; R7 (`21f503b`) interesse periodo finale sul rimborso + validazione boundary LLM del borrow + seizure/expropriation consistency + somme SQL→Python id-ordered + RNG namespaced. production/market/distribution stabilmente CONVERGED; conservazione money=BOUNDED_INJECTION_ONLY, goods=YES, tax=YES. Il fix del credit bug (§4.2) ratificato dall'utente (AskUserQuestion 2026-07-16).
- **PROMOZIONE WHITEPAPER §4.8 GIÀ SCRITTA nel working tree (uncommitted, EN+IT)**: capitolo completo (eq. 4.42-4.45, tabella parametri, Simplifications), §8.2 rimossa, conteggio §8 residuo = solo Knowledge Graph riconciliato ovunque, 5 riferimenti §13 nuovi/lingua, Tabella 6.1 + §7.1/7.2. ATTENZIONE: reca "round 6/sei round" — al CONVERGED aggiornare al round reale prima di committare.
- Suite completa container **899 passed**, 0 failed (tip `21f503b`). Ruff check + format --check exit 0. Nessuna azione autonoma schedulata.

STORICO: questa sezione descrive lo stato al 2026-07-15, quando il loop di audit era ancora in volo. Tutto CHIUSO il 2026-07-17 (Round 12 CONVERGED, merge `368e972`) -- vedi la sezione in cima. Decisioni ratificate da NON rilitigare: [[economy-ratified-decisions]].

---

# Sessione 2026-07-15 MATTINA -- Branch 6 world economy deprecation (F-CAMPAIGN chiusa)

## STATUS

Branch `20260715-094457-world-economy-deprecation` completo: spec+plan+tasks Spec Kit, audit spec 3 round (CONVERGED), implementazione TDD, audit codice fase 6 in 2 round (CONVERGED). Suite container 810 passed (baseline 809 +1 test warning), ruff check/format exit 0. Supersede [[session-resume-2026-06-22]].

**GATE RATIFICATI**: l'utente ha ratificato entrambi gli heavy gate con "procedi" (2026-07-15). PR#12 mergiata in develop, merge SHA `4341a7a5efd59a1438a13603b20eed403ee45b2b`. Frozen-at-commit pin aggiornato a quel SHA in entrambi i whitepaper (frontmatter + 8 header Status par. 4 + Appendice B, 10 occorrenze per lingua). NOTA STORICA: i branch 1-5 non aggiornarono mai il pin (rimasto a 168d90b/PR#4 dal 2026-04-26) pur toccando il whitepaper -- drift di procedura sanato da questa chiusura in avanti.

## Cosa contiene il branch (5 commit + eventuali successivi)

1. `1d5db19` docs(world): artefatti Spec Kit (spec convergiuta in 3 round di audit avversariale).
2. `ce5e47d` chore(world): marker deprecazione su `epocha/apps/world/economy.py` (docstring DEPRECATED con inventario caller verificato + `warnings.warn` DeprecationWarning a import, stacklevel=2) + test regression `test_module_emits_deprecation_warning` (reload dentro `pytest.warns`, RED-first). Logica tick byte-identica (verificata via md5 in audit).
3. `49a3059` docs: chiusura campagna -- 7 conteggi stale whitepaper corretti (§8/§9/§11 EN+IT), memoria tracker riscritta (traccia solo residuo §8.1 KG + §8.2 economy base, nome file mantenuto perche' citato dal whitepaper), retrospettiva `project_audit_repass_2026_04_12_completed.md`.
4. `94f4dcd` docs: fix round audit fase 6 -- altri 4 conteggi stale trovati dall'auditor (abstract EN+IT, §12 EN+IT; totale 11), conteggi numerici fragili abstract rimossi, gate grep SC-004 allargato a sinonimi (subsystems/sottosistemi), spec emendata, retrospettiva riconciliata.
5. Commit finale: tidy spec scenario US3 + sync memoria backup + questo resume.

## Decisioni chiave (per non ri-litigarle)

- **Path B (marker), non rimozione**: `process_economy_tick` e' fallback vivo in `simulation/engine.py` (`run_economy`:354, `run_tick`:446, gate su `Currency.objects.exists()`) e nel path Celery `simulation/tasks.py:46`. Rimozione = work item futuro di migrazione caller (decidere: auto-init economia nuova vs errore esplicito).
- **Memoria tracker NON marcata DONE secco** (il piano legacy Task 6.5 lo chiedeva): whitepaper la cita in §10/§11/§12 come tracker del residuo -- riscritta mantenendo il nome.
- **DeprecationWarning e non FutureWarning**: pubblico = sviluppatori; filtri default Python la silenziano in produzione, pytest la mostra. Nessun filterwarnings in pyproject.

## Lezioni di campagna (vedi retrospettiva per esteso)

- Conteggi di stato whitepaper degradano a ogni promozione: 11 punti stale tra EN/IT con 4 valori diversi. Gate grep bilingue con sinonimi (moduli/sottosistemi/cluster) su TUTTO il documento, abstract e conclusioni comprese. Meglio prose senza numeri fragili.
- Il grep stretto da' falso verde: la prima versione SC-004 copriva "modules/moduli" e manco' abstract e §12 -- li ha trovati solo l'audit avversariale fase 6.

## DA FARE -- prossime sessioni

1. ~~Chiusura branch 6~~ FATTO: PR#12 mergiata (4341a7a), frozen-pin aggiornato, memoria sincronizzata.
2. ~~Factions Round 3 hardening~~ FATTO E MERGIATO: PR#13 merge SHA `8a2bc714477f445b46cd610725df40c93fce1557` in develop, gate ratificati dall'utente ("procedi"). Spec CONVERGED (4 round audit), audit codice fase 6 CONVERGED al round 2. Suite container 826 passed. Frozen-pin aggiornato a 8a2bc71 (whitepaper §4.7 toccato). Fix inclusi: affinity context + tie-break deterministico FR-011, join-check su tutti i membri (budget 154->8), atomicita' 4 percorsi + policy bulk update, leadership de-N+1 36->4 e founder election 19->10 CON fix del difetto degenere scoperto (elezione su gruppo vuoto -> vinceva sempre founders[0]).
3. **Post-campagna**: Demography Plan 4 (engine wiring) -- vedi [[demography-plan2-complete]]; validation experiments -- vedi [[validation-experiments-pending]]; Round 2 di §8.1 Knowledge Graph e §8.2 economy base layer -- vedi [[audit-repass-batch-2026-04-12-pending]]. Lesson di processo dall'auditor fase 6: i behavior-fix emersi in fase 5 devono avere il loro test comportamentale NELLO STESSO commit del fix, non in un commit di chiusura successivo.

## NOTE tecniche ambiente

- `gh` aliasato a `git hist` nella shell: usare `/opt/homebrew/bin/gh`.
- Bug bashism `create-new-feature.sh` RISOLTO (PR#11, merge 9ed2252): timestamp naming funziona.
- Docker `docker-compose.local.yml`; pytest `exec -T web pytest`; baseline ora 810. Container ruff 0.15.11 (authority).
- Audit avversariale riusabile via SendMessage sullo stesso agent id per i round successivi (mantiene contesto, round 2-3 rapidi).

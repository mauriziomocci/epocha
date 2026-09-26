# Specification Quality Checklist: Sito pubblico divulgativo di Epocha

**Purpose**: validare completezza e qualità della spec prima del piano, e tenere il registro dei round di audit del gate di fase 2 (unica sede).
**Created**: 2026-09-26
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs) — eccezione dichiarata: la scelta della tecnologia (D-2) è una decisione dell'utente presa nel brainstorming e registrata come tale; i requisiti funzionali restano comportamentali
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed, FAQ compresa

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous — FR-002 e FR-004 sono verificati dalla revisione, e la spec lo dichiara (D-5)
- [x] Success criteria are measurable
- [x] Success criteria are technology-agnostic
- [x] All acceptance scenarios are defined
- [x] Edge cases are identified
- [x] Scope is clearly bounded (Non-goals)
- [x] Dependencies and assumptions identified

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria
- [x] User scenarios cover primary flows
- [x] Feature meets measurable outcomes defined in Success Criteria
- [x] No implementation details leak into specification oltre D-2

## Criterio di arresto del gate (scritto prima del round 1)

Il gate converge quando un round non produce nessun rilievo in queste classi:

1. un'affermazione della spec falsa rispetto al codice, al whitepaper, alla build map o a una fonte esterna citata;
2. un requisito o un criterio di successo che non può fallire o non può essere soddisfatto;
3. una contraddizione fra requisiti, o fra un requisito e una decisione di design;
4. una promessa del sito più forte di quanto il progetto sostenga (validazione, riproducibilità, capacità simulate).

Cifre sbagliate non ostative, refusi e formulazioni si correggono nello stesso commit e non riaprono il gate.

## Registro dei round

| Round | Data | Verdetto | Rilievi | Note |
|---|---|---|---|---|
| 1 | 2026-09-26 | NOT CONVERGED | 19 (R1-R19), tutte e quattro le classi | Bloccante principale R1: terzo deliverable bilingue con italiano normativo senza emendamento della costituzione. L'utente ha scelto l'inglese normativo; FR-022 chiede l'emendamento 1.2.0 per elencare sito e README. Altri: permessi di deploy insufficienti (R2), guardie sull'output richieste prima della generazione (R3), fatti non ancorati e Plan 4 imminente (R4), `robots.txt` inefficace sotto `/epocha/` (R7), guardia dell'avvertenza solo sul modello (R8), nessun controllo sulle PR (R9), catena di pubblicazione (R10), titolare di FR-020 (R11), citazione §3.4 incompleta (R12), promesse del README non coperte (R13), privacy assoluta (R14). La revisione 2 li affronta tutti; il round 2 ne ha trovati chiusi quindici e in parte quattro (R4, R11, R13, R17). Cifre corrette: Hugo 0.166.0 del 2026-09-09, MkDocs 1.6.1 del 2024-08-30. |
| 2 | 2026-09-26 | NOT CONVERGED | 14 nuovi (NEW-1..NEW-14): 5 nelle classi (NEW-1..NEW-5), 9 non ostativi | NEW-1: la regola «rivedi l'avvertenza quando cambia il whitepaper» affidata alla tabella di doc-sync, che scatta al contrario (dal codice al capitolo). NEW-2: FR-004 vietava anche le affermazioni vere (l'economia è cablata) e contraddiceva US1 e FR-001. NEW-3: FR-020 affidato al Plan 4, che al momento della verifica non esiste più; `hb.p0` mancava fra i difetti noti; il limite di FR-021 poggiava su quella stessa collocazione. NEW-4: SC-005 «non pubblica» su una PR non può fallire. NEW-5: pagina 404 senza eccezione in FR-016. Revisione 3: regola dell'avvertenza come voce propria dichiarata manuale; FR-004 ammette solo le partecipazioni vere al commit pubblicato (incondizionate, opzionali se dietro un flag); FR-020 a carico di questo work item dopo il merge del Plan 4; SC-005 diviso in 5a e 5b; 404 come eccezione dichiarata. Chiusi anche i nove non ostativi: riverifiche post-merge (NEW-6), sezione Status intera e annotazioni «(audited)» (NEW-7, NEW-8), limiti di SC-006 ed eccezione di accessibilità della build map (NEW-9), permessi per job e regola d'ambiente come controllo primario (NEW-10), «sorvegliato, non garantito» (NEW-11), esempio della 0.146.0 riformulato (NEW-12), cache di 10 minuti (NEW-13), «nessun modulo del codice» (NEW-14). |
| 3 | 2026-09-26 | NOT CONVERGED | 8 nuovi (N3-1..N3-8): 3 nelle classi, 1 di classe 1 correggibile nel testo, 4 non ostativi | Ristretto alla remediation. NEW-1, 3, 5, 7-14 chiusi; NEW-2, 4, 6 in parte. N3-1: SC-005b non poteva fallire (a messa online spenta il passo di pubblicazione non parte in nessun caso). N3-2: il test «chiamato senza condizioni» di FR-004 non era decidibile sul codice reale (economia dietro l'esistenza di valute, modelli legati all'azione scelta, elezioni legate al regime) e vietava ancora il vero; il riferimento indicato non coincideva con il percorso di produzione. N3-3: nessuna regola faceva rivedere le frasi sulle capacità quando cambia il codice del turno. N3-4: il mirror inglese di `hb.p1` era già stato corretto con `91b9599`. Revisione 4: FR-004 ancorato al percorso di produzione (`run_simulation_loop` → `process_agent_turn` → `finalize_tick`) con la condizione detta in parole comuni; FR-019 aggiunge la revisione manuale delle frasi sulle capacità e §11 all'avvertenza, e si estende alle otto sedi della regola della build map; SC-005b sostituito dalla guardia strutturale sul workflow (FR-025); fatti su `hb.p1` aggiornati; US4 esclude la 404; FR-009 lega le catture al percorso di produzione. La voce `13.desc` nel worktree è riformulata («sulle pagine generate dal sito») con impronte ricalcolate in un ambiente locale, guardia bilingue 9 su 9. |
| 4 | 2026-09-26 | NOT CONVERGED | 5 nuovi (F4-1..F4-5): 2 nelle classi, 3 non ostativi | N3-2..N3-8 chiusi, N3-1 in parte. F4-1: la spec diceva che il cruscotto usa il percorso sincrono; falso, `simulation_play_view` e l'API `play` chiamano `run_simulation_loop`, e il percorso sincrono lo usano solo i test di integrazione. F4-2: FR-025 parlava di dipendenze fra «passi», che in GitHub Actions esistono solo fra job, e non vedeva uno step di guardia con `continue-on-error`. Revisione 5: FR-025 riscritto su job e `needs`, con elenco esplicito dei job di guardia, divieto di `continue-on-error` e delle condizioni `always()`/`failure()`/`cancelled()`/`!cancelled()`, tre mutazioni e il limite `|| true` dichiarato; SC-005b allineato; «Problemi trovati» riscritto (test di integrazione su un percorso non di produzione, docstring superato di `SimulationEngine`); FR-004 precisa quale docstring dice «legacy/fallback»; parser YAML rinviato al piano (F4-4); riepilogo aggiornato (F4-3, ma l'intestazione è rimasta a «4»: corretta nella revisione 6); F4-5, «la demografia entra solo nel percorso di produzione», era impreciso perché il flag `avoid_conception` passa dal gestore d'azione comune: la frase è stata riscritta come «blocco demografico per turno». |
| 5 | 2026-09-26 | NOT CONVERGED | 3 nuovi (F5-1..F5-3): 1 di classe 2, 1 di classe 1 correggibile nel testo, 1 non ostativo | F4-1 e F4-4 chiusi, F4-2 in parte. F5-1: FR-025(a) prometteva di cogliere un job di guardia nuovo non elencato, ma un controllo guidato da un elenco non vede ciò che non è elencato, e nessuna mutazione provava quel caso. F5-2: il percorso sincrono lo chiamano anche i test unitari del motore, e il task `run_tick` non lo chiama nessuno. F5-3: anche il docstring del task `run_tick` è superato. Revisione 6: FR-025 a mondo chiuso (il job di pubblicazione dipende da tutti gli altri job; `continue-on-error` vietato su tutti gli altri job e step; (c) completo sulle quattro funzioni di stato), quarta mutazione «job nuovo fuori da `needs`» in FR-025 e SC-005b; «Problemi trovati» corretto su chiamanti e docstring; intestazione a revisione 6. |
| 6 | 2026-09-26 | **CONVERGED** | 4 non ostativi (F6-1..F6-4), nessuno nelle classi | F5-1, F5-2, F5-3 chiusi. Verificate le coerenze di FR-025 con FR-011 (sulle PR il job di pubblicazione è saltato dal suo `if` senza funzioni di stato), con FR-012 (nessuna circolarità) e con SC-006. Corretti nello stesso commit, come il criterio prevede: F6-1, `SimulationEngine.run_tick` lo chiama anche il task `run_tick`, che però non ha chiamanti; F6-2, (c) vieta tutte e quattro le funzioni di stato, compresa `success()` esplicita in una disgiunzione, eliminando il caso speciale; F6-3, dichiarato il limite della rimozione di un job di guardia insieme alla sua voce in `needs`; F6-4, ogni job diverso dalla pubblicazione deve girare anche su push e avvio manuale da `develop`. |

**Esito tecnico del gate**: CONVERGED al round 6. Il gate pesante di fase 2 resta aperto fino all'approvazione esplicita dell'utente.

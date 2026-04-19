---
name: session-resume-2026-04-20
description: READ FIRST AT SESSION START 2026-04-20 -- riepilogo ultima sessione + prossimi step obbligati
type: project
originSessionId: f9bc7a55-71c4-45ed-9602-f5e328a6175e
---
# Sessione del 2026-04-20 -- riprendere da qui

## Contesto al rientro

Branch corrente: `develop` (HEAD `0894e0c` al momento dello stop).
Test suite: **800/0** (zero fallimenti).
Container Docker: possono essere stati spenti, riavviarli con `docker compose -f docker-compose.local.yml up -d` prima di qualsiasi pytest.

## Cosa e' stato fatto nella sessione del 2026-04-19

### Demography Plan 1 e Plan 2 -- mergiati in develop

- **Plan 1 (Foundations + Mortality)**: 25 task, mergiato `41bf508`. Models (Couple, DemographyEvent, PopulationSnapshot, AgentFertilityState), Agent extensions (birth_tick signed, death_tick, death_cause, other_parent_agent, caretaker_agent), integration contracts (add_to_treasury, SUBSISTENCE_NEED_PER_AGENT, compute_subsistence_threshold, compute_aggregate_outlook), seeded RNG streams, template loader + 5 era JSON, Heligman-Pollard mortality + scipy fitting. Adversarial audit CONVERGED round 2.
- **Plan 2 (Fertility + Couple + LLM actions)**: 23 task, mergiato `715d5fa`. Hadwiger ASFR canonical, Becker modulation, Malthusian ceiling, tick_birth_probability, avoid_conception tick+1, childbirth mortality resolver, Gale-Shapley + form_couple + resolve_pair_bond_intents (two-pass con arranged marriage Goode 1963) + resolve_separate_intents + dissolve_on_death, UniqueConstraint active couple, 3 nuove azioni LLM con era-filter, 80 test nuovi. Adversarial audit CONVERGED round 2 (6 MAJOR resolved, B2-07 deferred).

### Fix critici scoperti durante Plan 2 implementation

- **Hadwiger T off-by-factor-10**: spec e 5 template avevano T in [0.35, 0.42] invece di [3.5, 4.2]. Sonnet ha escalato al Task 1. Corretto in spec EN + IT e tutti i 5 template. Verificato matematicamente: peak f(26) con T=3.5 H=5 = 0.380, integrale [12,50] = 4.999 ≈ H. Bug sfuggito a 4 round audit Plan 1 perche' nessun auditor aveva integrato numericamente.
- **Redis infrastructure test failures**: 4 test pre-esistenti con error di connessione Redis. Root cause: `config/settings/test.py` aveva creds hard-coded `postgres/postgres@localhost` mai funzionanti in Docker, percio' veniva bypassato via `.envs/.local/.django:DJANGO_SETTINGS_MODULE=config.settings.local` che vince su pyproject.toml. Fix: test.py eredita DATABASES da base.py (usa `DATABASE_URL` env), CELERY broker/backend a `memory://`, pyproject.toml addopts forza `--ds=config.settings.test`. Fixture `sim_with_agents` ora crea simulazione con status PAUSED di default (i test che vogliono RUNNING lo settano esplicitamente) per evitare Celery chord in EAGER che tenta di contattare result backend. Branch: `fix/redis-test-infrastructure`, PR #2 merged in develop.

### Regole permanenti aggiunte durante la sessione

Tutte in CLAUDE.md + memoria live + backup, codificate su richiesta utente:

1. **Canonical 7-phase workflow** (`feedback_canonical_workflow.md`): ideazione → requisiti (heavy gate) → design piano → task breakdown (con critical post-validation review) → implementazione task-per-task → test generale + final adversarial code audit (heavy gate) → chiusura.
2. **Task breakdown mandatory** (`feedback_task_breakdown_mandatory.md`): ogni implementation plan in task checkboxed eseguiti sequenzialmente. Quattro driver: trasparenza, granularita', audit trail publication-grade, **context preservation per l'agente AI**.
3. **Model selection policy** (`feedback_model_selection_policy.md`): Opus 4.7 fasi critiche (1-4, 6-7), Sonnet 4.6 fase 5 implementazione + routine code review, Haiku MAI. Escalation protocol da Sonnet a Opus su decisioni strategiche.
4. **Italian specs** (`feedback_italian_specs.md`): spec file solo in italiano per approvazione (eliminato il sync bilingue). Code, commit, plan, docstring, README -> inglese.
5. **README bilingual maintenance** (`feedback_readme_bilingual_maintenance.md`): README.md + README.it.md sempre aggiornati e sincronizzati.
6. **Whitepaper bilingual** (`feedback_whitepaper_bilingual.md`): due whitepaper scientifici living document (EN + IT) linkati dai README, publication-grade, struttura paper completa (Abstract/Methods/Validation/References/Appendices/reproducibility notes), sempre in sync col codice merged.

## Prossimi step PRIMA di Plan 3

**Obbligatorio per regole nuove**:

### 1. Riscrivere README.md + README.it.md

Entrambi molto obsoleti. Devono riflettere:
- Architettura corrente (Economy app + Demography app + nuovi moduli)
- Stack (scipy aggiunto come runtime dependency)
- Regole di progetto aggiornate (canonical 7-phase workflow, task breakdown, model selection, italian-specs, README bilingual, whitepaper bilingual)
- Roadmap aggiornata (Economy Spec 1+2 done, Demography Plan 1+2 done, Plan 3 Inheritance + Migration prossimo, Plan 4 Init + Engine + Validation)
- Visione paper scientifico come outcome del progetto
- Istruzioni setup aggiornate (test.py fix, pytest ds default, scipy)
- Link al whitepaper rispettivo in testa

### 2. Creare whitepaper bilingue

Path:
- `docs/whitepaper/epocha-whitepaper.md` (EN, linkato da README.md)
- `docs/whitepaper/epocha-whitepaper.it.md` (IT, linkato da README.it.md)

Living documents con struttura paper scientifico canonica:
1. Title / Authors / Affiliation / Date / Version
2. Abstract (150-300 parole)
3. Keywords (5-8)
4. Introduction (contesto, gap, contributo, struttura)
5. Background / Related Work
6. Methods (per Economy + Demography: modelli matematici con equazioni numerate, parametri con fonte, algoritmi)
7. Implementation (mapping modello → moduli Django)
8. Calibration (parametri tunable, fitting procedures)
9. Validation (benchmarks historici attesi: Wrigley-Schofield, HMD, Irish Famine analog)
10. Discussion (trade-off, limiti)
11. Known Limitations (sintesi esplicita)
12. Conclusions
13. References (Author-Date, DOI/URL)
14. Appendices (parameter tables complete, reproducibility notes con commit hash, dependencies, seed RNG, exact benchmark commands)

Descrive lo stato CORRENTE al merge del whitepaper (commit hash referenziato esplicitamente).

### 3. Processo suggerito per README + whitepaper

Segui canonical workflow adattato (non e' un nuovo subsistema ma e' un task di scrittura documentale strutturato):
- Branch: `feature/readme-and-whitepaper-catchup`
- Fase 2 breve: brainstorming su TOC del whitepaper (< 1 ora)
- Fase 3-4: plan con checkbox sui capitoli (~1 giorno)
- Fase 5: Sonnet per draft capitoli esecutivi (Methods, Implementation, parameter tables), Opus per scientific polish + cross-check con spec e bibliografia (assicurarsi di NON introdurre citazioni inesistenti come Chandra 1999 titolo sbagliato -- verificare ogni citation)
- Fase 6: adversarial audit con `critical-analyzer` sul whitepaper: stesse regole della spec (nessuna citation inventata, nessun parametro senza fonte, nessuna semplificazione non documentata). Round fino a CONVERGED.
- Fase 7: merge a develop, cleanup branch, sync memory

### 4. Dopo follow-up: Plan 3 Demography

**Plan 3 Inheritance + Migration**: parte da `develop` aggiornato con README + whitepaper.
Scope (dalla spec e overview):
- `inheritance.py`: polygenic additive, derived_trait_formulas (cunning), regole social class per-era, education regression, estate tax con add_to_treasury, loans-as-lender transfer, simultaneous deaths ordering, multi-gen cascade, mourning memory, orphan caretaker
- `migration.py`: context enrichment (wage differential, Harris-Todaro), family coordination Mincer 1978, emergency flight con guard ragionato, trapped_crisis broadcast, mass flight threshold

Stima: ~22 task + audit loop.

## File chiave di memoria da leggere per riprendere

- Questo file (session resume)
- `project_demography_plan1_complete.md`
- `project_demography_plan2_complete.md`
- `project_readme_rewrite_todo.md` (follow-up)
- `feedback_canonical_workflow.md`
- `feedback_task_breakdown_mandatory.md`
- `feedback_model_selection_policy.md`
- `feedback_italian_specs.md`
- `feedback_readme_bilingual_maintenance.md`
- `feedback_whitepaper_bilingual.md`
- `feedback_scientific_paper_goal.md`
- `feedback_verify_assertions.md`

## Debt tracked per Plan 3/4/futuro

Da Plan 1:
- A-5 RNG collision su seed/id entrambi None
- A-6 backfill O(N) save per birth_tick
- A-7 noop_reverse data migration
- B-5 HP fit bounds justification (Plan 4)

Da Plan 2:
- B2-07 Becker coefficients identical across templates (Plan 4 calibration)
- B2-08 math.exp overflow clamp
- B2-09 stable_matching empty input tests
- B2-10 _female_role_employment_fraction N+1 cache (Plan 4)
- B2-11 unused Iterable import cleanup
- B2-12 mock.patch preferito a importlib.reload in test_fertility
- B2-13 type hint precision stable_matching
- B2-14 form_couple docstring update
- Coverage gap: test "child direct intent sopprime arranged" (post-B2-06)
- Opzionale: set_avoid_conception_flag con current_tick esplicito

## Stato workflow canonico

- Fase 1-7 applicate pulitamente per Plan 1 e Plan 2
- Model selection policy rispettata: Opus fasi critiche, Sonnet fase 5 per-task con escalation corretta (Hadwiger T bug)
- Ogni commit autoreviewed 8-punti Mandatory Code Review
- Memory backup sync dopo ogni merge (regola critica rispettata)

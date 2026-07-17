# Specification Quality Checklist: R12-DET-1 non-difetto (scope finale)

**Purpose**: Validate specification completeness and quality before proceeding
**Created**: 2026-07-17
**Revised**: 2026-07-17, quarta stesura, dopo tre round di audit
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs)
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

**Nota.** Lo spec cita il sorgente di Django e l'SQL emesso perche' *sono* l'oggetto: la tesi e' che un difetto ratificato non esiste, e quella tesi non ha una formulazione fedele che ometta la prova. Lo stakeholder di riferimento e' il revisore scientifico del paper.

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous
- [x] Success criteria are measurable
- [x] Success criteria are technology-agnostic (no implementation details)
- [x] All acceptance scenarios are defined
- [x] Edge cases are identified
- [x] Scope is clearly bounded
- [x] Dependencies and assumptions identified

**Su "acceptance scenarios" ed "edge cases".** Lo spec non ha una sezione User Scenarios, e non e' un'omissione: non c'e' alcun comportamento nuovo da accettare. Il criterio di accettazione e' FR-004 — la suite passa **senza che un solo test cambi**, perche' se ne cambiasse uno la premessa del branch sarebbe falsa. E' un criterio piu' stringente di uno scenario Given/When/Then, non piu' debole.

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria
- [x] User scenarios cover primary flows
- [x] Feature meets measurable outcomes defined in Success Criteria
- [x] No implementation details leak into specification

## Validation status

Quattro stesure. Le prime tre passavano questa checklist ed erano **sbagliate**:

| Stesura | Checklist | Esito audit | Perche' |
|---|---|---|---|
| 1 (scope R12-DET-1) | tutta verde | NOT CONVERGED | Premessa falsa: `.first()` non ordinato riceve `order_by("pk")`. I 3 FR erano no-op. |
| 2 (3 difetti veri) | 2 item aperti | NOT CONVERGED | Predicato piu' stretto del vero (ometteva `Meta.ordering`, ignorava gli slice). Popolazione reale molto maggiore. |
| 3 (13 difetti) | non compilata | NOT CONVERGED | Predicato sintattico (`[:N]` invece di "troncamento a N"). ~10 siti mancati, 2 dentro funzioni gia' enumerate. D2 su premessa falsa (`agent_id` seed-stabile). |
| 4 (questa) | verde | — | **Non enumera nulla.** Ogni asserzione e' verificata direttamente, non dedotta da un predicato di ricerca. |

**Il dato piu' istruttivo di questo file**: la checklist era verde sulla stesura 1, la peggiore delle quattro. Nessun item chiede *"hai verificato alla fonte le asserzioni tecniche su cui poggia il difetto?"*, quindi nessun item poteva fallire. **La checklist misura la forma dello spec, non la verita' del suo contenuto.** Solo l'audit avversariale ha trovato l'errore — tre volte su tre.

## Notes

- Heavy gate fase 2: tre round di audit avversariale eseguiti con auditor indipendenti. Round 1, 2 e 3 = NOT CONVERGED, ciascuno ha demolito lo scope allora vigente. La quarta stesura e' la sola parte su cui tutti e tre concordano, e non dipende da alcuna enumerazione.
- Heavy gate fase 6: suite 911 verdi (invariata), ruff pulito, diff su `epocha/` verificato privo di righe non-commento.
- Cio' che questo branch NON risolve e' tracciato in `project_determinism_enumeration_pending.md` con l'evidenza file:riga, e sulla build map come rischio trasversale aperto.

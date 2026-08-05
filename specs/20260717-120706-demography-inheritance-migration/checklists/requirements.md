# Specification Quality Checklist: Demografia Plan 3 — Ereditarietà e Migrazione

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-07-17
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
- [x] Dependencies and assumptions identified

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria
- [x] User scenarios cover primary flows
- [x] Feature meets measurable outcomes defined in Success Criteria
- [x] No implementation details leak into specification

## Notes

Due voci del checklist standard sono state valutate contro le regole di progetto invece che alla lettera, e la deviazione è deliberata.

**"No implementation details" e "Success criteria are technology-agnostic"**: il checklist di Spec Kit nasce per prodotti applicativi, dove nominare framework e tabelle in una spec è rumore che confonde gli stakeholder. Epocha è una simulazione scientifica e la sua GOLDEN RULE impone l'opposto: nessuna formula senza fonte citata, nessun parametro senza valore giustificato, nessuna semplificazione senza trade-off documentato. Una spec che dicesse "il figlio somiglia ai genitori" invece di `child_T = h²·midparent + (1-h²)·ε` sarebbe non verificabile e non auditabile, e fallirebbe il gate pesante di fase 6. I riferimenti a moduli, campi e formule qui presenti non sono dettagli implementativi lasciati sfuggire: sono il contenuto scientifico, e sono ancorati a simboli stabili verificati contro il source tree, non a numeri di riga. Lo stesso vale per SC-001 e SC-005, che nominano il comando di test e `makemigrations`: sono i criteri di accettazione operativi che il progetto richiede esplicitamente.

Il precedente è coerente: le tre spec Spec Kit più recenti (`20260715-132752-economy-base-layer-audit`, `20260715-111119-factions-round3-hardening`, `20260715-094457-world-economy-deprecation`) adottano tutte questa lettura, in italiano e con il contenuto scientifico in chiaro.

**"Written for non-technical stakeholders"**: lo stakeholder di questa spec è chi approva il gate, che è il proprietario del progetto e un lettore tecnico. La spec resta leggibile in prosa e spiega ogni termine, ma non finge un pubblico che non esiste.

**Zero [NEEDS CLARIFICATION]**: nessun marker è stato necessario. Il design è CONVERGED dopo quattro round e copre le sezioni 4, 5 e 6 con formule, tabelle di parametri e fix ratificati; le uniche incognite plausibili (esistenza dei contratti d'integrazione, completezza dello schema dei template, necessità di migrazioni) sono state risolte per verifica diretta contro il source tree il 2026-07-17 anziché per domanda, e il risultato è nella tabella del Contesto.

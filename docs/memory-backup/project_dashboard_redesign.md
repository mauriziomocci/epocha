---
name: project-dashboard-redesign
description: The Epocha operator dashboard is minimal and must be redesigned as its own Spec Kit work item, led by Riccardo mode, driven by the public API so external dashboards can be built; it shows nothing of demography yet.
metadata:
  type: project
---

On 2026-10-29, after seeing the local dashboard with a test simulation, the
user said the dashboard will have to be redesigned ("questa è davvero
minimale"). Today it is a list of simulations plus a few detail pages; no page
reads `PopulationSnapshot` or the demography events, so the Plan 4 work is
invisible from the UI. A simulation created from the dashboard also has
demography disabled, because `simulation_create_view` never sets
`demography_enabled` and the form has no control for it.

**Why:** the dashboard is how the project is seen; the user wants it to show
where the simulation actually is.

API-driven (user 2026-10-29): the definitive dashboard must be driven by the
API, so external dashboards can be built on the same data. The dashboard is
a client of `/api/v1/` like any other, never a set of views reading the ORM
directly (today `epocha/apps/dashboard/views.py` does read it). Consequences:
the demography data (snapshots, events, households) needs API endpoints
first; the API is user experience, so Riccardo has a say on responses and
bodies before the spec; and once delivered, the contract never changes
(global rule), so its shape is designed with the external client in mind.

Understandable AND rigorous (user 2026-10-29): in the end the dashboard must
return everything in a way that is both comprehensible and rigorous. For a
psychohistory-style goal ([[project-vision-psychohistory]]) that means showing
distributions and uncertainty across seeded runs, never a single run presented
as the answer; every number with its unit, provenance (model, era template,
seed, commit) and the model's stated limits; plain-language explanations next
to the figures.

**How to apply:** a separate Spec Kit work item, not part of demography Plan 4.
Riccardo mode leads (signed UX study before code, one adversarial round with
Matteo, Utente mode on the main tasks), with the global interface gate:
both themes, WCAG AA measured in every state, widths 375/768/1280, simplicity
first. Record it in the build map when it is opened. Related:
[[feedback-master-rules-apply]], [[feedback-build-map-source-of-truth]].

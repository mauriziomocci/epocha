---
name: project-life-course-behavior
description: User requirement 2026-10-29 -- agents must behave according to their age across the whole life course, from newborn to elder; a separate Spec Kit work item grounded in science, plus a minimal guard inside demography Plan 4.
metadata:
  type: project
---

On 2026-10-29, after a 10-month-old newborn (Pietro, test simulation 2)
answered a hug in the dashboard chat like an adult, the user stated:
"le persone devono comportarsi anche in base all'età, da neonato a vecchio".

Verified the same day: the dashboard chat prompt
(`epocha/apps/dashboard/views.py: _build_chat_system_prompt`) gives the LLM
only name and role, no age; the agent decision loop
(`epocha/apps/simulation/engine.py`, around line 505) asks the LLM to decide
for every living agent with no age filter, so newborns deliberate like
adults. A docstring in `demography/migration.py` (`coordinate_family_migration`)
already assigns "minors never presented a choice" to the Plan 4 orchestrator,
which never implemented it.

**Why:** a scientific simulation of a population is wrong if behaviour does
not depend on age; births exist only since demography Plan 4.

**How to apply:** two levels. (1) Inside Plan 4, the minimal guard decided by
the Trinity for the defect the branch introduced (newborns in the decision
loop). (2) A separate Spec Kit work item for life-course behaviour: what each
age can do and choose (infancy, childhood, adolescence, adulthood, old age)
in decisions, actions, mobility, work, relationships and in the chat, with
cited sources and an adversarial audit, approved by the user at the phase-2
gate. Related: [[project-dashboard-redesign]], [[feedback-master-rules-apply]].

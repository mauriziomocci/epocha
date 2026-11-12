---
name: project-world-setting-lost
description: "Bug reported by the user 2026-10-29: Express world generation loses the era, the starting year and the founding event of the prompt; agents answer as if it were 2026. Separate work item after the Plan 4 merge."
metadata:
  node_type: memory
  type: project
  originSessionId: f3c14087-5073-413f-8363-93f01142295b
  modified: 2026-10-29T10:41:35.340Z
---

Reported by the user on 2026-10-29 on simulation 4 (prompt: Italian village of
10 people, around 2500, an alien ship has landed). In chat an inhabitant said
nothing was happening and the year was 2026.

Causes verified in the code and in the local DB the same day:
1. `epocha/apps/world/generator.py` `_WORLD_GENERATION_PROMPT`: the JSON schema
   has no field for era, starting year or founding event, so the premise
   survives only as scattered hints in agent backgrounds (one says "since
   2065", inconsistent with 2500) and zero `Event` rows are created.
2. `Simulation.description` holds the prompt, but no agent prompt reads it: the
   chat system prompt in `dashboard/views.py` (`_build_chat_system_prompt`)
   asks to react "given their ... era" without ever stating the era, so the
   model falls back to its own present.
3. The local 8B model makes it worse, but it is not the root cause.

**Why:** the setting (era, calendar, starting year) is also scientific state:
it decides which demographic template and which world calendar apply.

**How to apply:** separate Spec Kit work item after the Plan 4 merge, not in the
Plan 4 branch (in the phase-6 gate). Where the setting lives (World fields vs
`World.config`) is a data-model decision for the user. Add it to the build map
at the next map update. Related: [[project-dashboard-redesign]],
[[project-life-course-behavior]].

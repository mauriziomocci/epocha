---
name: project-chat-coherence
description: "Bug reported by the user 2026-10-29: dashboard chat answers do not follow the conversation. Four causes verified in dashboard/views.py chat_send_api; small work item after the Plan 4 merge, together with the Express world setting."
metadata:
  node_type: memory
  type: project
  originSessionId: f3c14087-5073-413f-8363-93f01142295b
  modified: 2026-10-29T11:39:12.168Z
---

Reported on 2026-10-29 (simulation 4, chat session 5 with the alien Zarath
Nex): replies drift, and a kick or a punch is answered with "I feel the meteorite
falling". Causes verified the same day in `epocha/apps/dashboard/views.py`
`chat_send_api` and in the local DB:

1. Every visitor message gets the last 3 `Event` rows appended with "React to
   this as <name>" -- an instruction on every turn, not context. Simulation 4
   holds the same injected event ("meterite in testa") three times at tick 0, so
   all three slots repeat it; event injection is not idempotent either.
2. The agent's own previous replies enter the history truncated to 50
   characters (`_MAX_AGENT_MSG_LENGTH = 50`): the model cannot see what it said.
3. Only the last 5 prior messages, as flat text inside the system prompt, plus
   the rule "React ONLY to the visitor's latest message", which works against
   continuity.
4. The local 8B model (qwen3-8b) amplifies all of the above; not the root cause.

**Why:** chat is secondary for Epocha (scale is the goal), but a demo that
reads as nonsense undermines trust in the rest.

**How to apply:** one small work item after the Plan 4 merge, together with
[[project-world-setting-lost]] (both are about what context the agent prompt
carries); the dashboard redesign [[project-dashboard-redesign]] may absorb it.
Fix with red tests on the assembled prompt, not by tuning the wording blind.

---
name: project-demography-couple-followups
description: "Two couple-formation work items deferred out of demography Plan 4 with explicit user authorization -- unconsumed couple-template keys, and pair-bond intents resolved by id instead of by name."
metadata:
  node_type: memory
  type: project
  originSessionId: f3c14087-5073-413f-8363-93f01142295b
  modified: 2026-09-26T15:05:41.511Z
---

Two separate work items were deferred out of demography Plan 4 (branch
`20260826-144432-demography-plan4-wiring`) with explicit user authorization.
Neither is started. Both touch `epocha/apps/demography/couple.py`, an audited
Plan 2 module, so each needs its own Spec Kit work item with a phase-2 gate.

1. **Unconsumed couple-template keys** (deferred by the user on 2026-09-26,
   while phase-6 gate round 10 was running). `mourning_ticks`,
   `marriage_market_radius`, `marriage_market_type` and `allowed_types` are
   validated by `template_loader.py` and listed per era in Table 4.5 of
   whitepaper §4.1.3, yet no code reads them. §4.1.3 says
   `marriage_market_type` "selects" between autonomous and arranged
   marriage, while `resolve_pair_bond_intents` accepts a `for_child`
   (arranged) intent in every era. Decision to take: implement each key, or
   remove it from the templates and the whitepaper. Found while applying the
   era's minimum marriage age to the intent path (commit `86d9f25`), the same
   defect class: a template rule declared and applied nowhere.

2. **Resolve pair-bond intents by agent id instead of by name** (deferred
   with authorization at round 9, C3). Era name pools hold twelve names per
   sex with no uniqueness check, so name collisions are certain once births
   run; the resolver now refuses an ambiguous name and logs it, which stops
   the wrong marriage but not the ambiguity. The fix changes the action
   schema the decision loop hands the LLM.

**Why:** the user chose to keep Plan 4's scope closed rather than widen it
inside the phase-6 gate.

**How to apply:** when Plan 4 closes, both items must appear in the build map
as deferred work items (trigger 5). Before starting either, re-verify the
keys against the source: this note reflects 2026-09-26. Related:
[[project-session-resume]], [[feedback-build-map-source-of-truth]].

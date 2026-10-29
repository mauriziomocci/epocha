---
name: feedback-speckit-stale-pin
description: "Spec Kit's setup-plan.sh follows the pin in .specify/feature.json: a stale pin made it overwrite another feature's plan.md on 2026-10-29. Check the pin before /speckit-plan."
metadata:
  node_type: memory
  type: feedback
  originSessionId: f3c14087-5073-413f-8363-93f01142295b
  modified: 2026-10-29T20:51:16.007Z
---

On 2026-10-29 the plan agent of the marital fertility work item ran
`.specify/scripts/bash/setup-plan.sh`, which resolved the feature from
`.specify/feature.json`; on `develop` that file still pinned
`specs/20260812-143706-bilingual-build-map`, so the script overwrote that
work item's `plan.md`. The agent restored it with `git checkout` before any
commit and repointed the pin (PD-10 of that plan).

**Why:** the pin is not updated when a branch is created by hand or from an
older base, and the script trusts it silently.

**How to apply:** before `/speckit-plan` or `/speckit-tasks`, read
`.specify/feature.json` and fix it to the current feature; after the skill,
check `git status` shows nothing outside the feature directory except the
Spec Kit pointer lines (feature.json and the "Active feature plan" line of
CLAUDE.md, which the user was told about as a Spec Kit mechanism). Put both
checks in every plan brief. Related: [[feedback-speckit-mandatory]].

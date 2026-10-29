---
name: project-github-issues-trial
description: Trial agreed 2026-10-29 -- track the rule-based couples work item with one GitHub issue (task checklist from tasks.md, PRs linked), then give the user a pragmatic report on usefulness.
metadata:
  type: project
---

Agreed with the user (2026-10-29): try GitHub Issues/Projects for development
tracking on ONE work item, rule-based couple formation (step 2 of
[[project-agreed-order-2026-10-29]]), and report pragmatically on its
usefulness at the end.

**Why:** the user asked whether GitHub issues could help follow development
step by step; the concern is duplicating state already held in the build map
(project status) and `tasks.md` (task granularity), which would drift.

**How to apply:** open the issue only when the work item starts (together
with its spec), never an empty container. One issue per work item, never one
per task (same rule as the Jira budget of the global CLAUDE.md). Description:
plain-language part, then a checklist of the `tasks.md` IDs, ticked in the
same block as the commit that closes each task; `tasks.md` stays the source of
truth. PRs reference the issue. The build map links to the issue for
operational status. Personal repo github.com/mauriziomocci/epocha, `gh` at
/opt/homebrew/bin/gh. At the end of the work item, report to the user: upkeep
cost, any contradiction with the build map or tasks.md, whether it helped
follow the work more than the build map and PRs already do, and whether to
extend it.

Comparison with the current way of working (user, 2026-10-29: "verifica
l'effettiva utilità rispetto a come lavoriamo adesso"): the baseline is how
demography Plan 4 was tracked (build map + `tasks.md` + PR + gate document).
Count, never estimate, during the couples work item: issue updates made and
the commits they cost; contradictions found between issue, `tasks.md` and the
build map; times the user or a session used the issue to know the state
instead of the build map or `tasks.md`; anything the issue gave that the
baseline did not (e.g. PR linking, public visibility). The verdict is keep,
change or drop, with those numbers.

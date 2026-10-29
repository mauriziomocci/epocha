---
name: feedback-master-rules-apply
description: "From 2026-10-29 Epocha follows the same working rules as the RapsodiaTrace/IoPollicino master session (autonomous work, Trinity, daily token budget, decisions when the user is away, night work)."
metadata:
  node_type: memory
  type: feedback
  originSessionId: f3c14087-5073-413f-8363-93f01142295b
  modified: 2026-10-29T08:00:00.528Z
---

On 2026-10-29 the user decided that Epocha, from then on, uses the same rules
as the coordinating "master" session of the Pollicino (RapsodiaTrace
multi-experiment) work. Those rules are the global CLAUDE.md ones as the
master applies them: the Trinity (Domenico frames, Riccardo on UX and API
responses, Matteo on evidence, Utente mode on UI), mutual skepticism, the
daily token ceiling ((85% - weekly used) / days to reset, 15% reserve
untouched), decisions when the user is away (technical ones taken by Matteo
alone, scope or interface by Domenico after hearing both, data model and API
contract never, all logged provisionally and reported first thing), and the
night-work and office-hours rules.

**Why:** one way of working across the user's projects instead of a
different discipline per repository.

**How to apply:** on every Epocha session load `trinity-working-modes` at the
start of a piece of work, compute the daily ceiling with `get_usage` at the
first block, and follow the master's practice for logging decisions.

The master's own practice, as it explained it on 2026-10-29 (an explanation,
not a permission; the global CLAUDE.md and the skills prevail):
- Absence counts only when the user says so, or after 30 minutes without an
  answer to a blocking question in office hours. Never decided in absence:
  data model, API contract, changed requirements (provisional proposal on a
  local branch, dependent tasks parked). Merges, deletions, irreversible
  actions and production stay with the user.
- Decision log: one `D-<day>-<n>` entry per decision in
  `~/Documents/workspace/Diario/AAAA/MM/AAAA-MM-GG/decisioni.md` (who decides,
  both positions, the five costs, status). For Epocha the gate document of
  the work item stays the canonical record; the diary entry points to it.
- First message on the user's return: tasks done with confidence level,
  parked items and why, provisional decisions, budget used; also written as a
  file in the feature's spec folder.
- Budget read before every block; the reserve is never spent "because it
  resets tomorrow". Opus for judgment and review, Sonnet for written tasks.
- Matteo is an Opus agent on every delivery, reviewing the delta with the
  thresholds written in the brief and scoring with `quality-scoring` (8/10
  gate). Domenico as an agent only for big scope decisions, with a three-line
  pre-mortem. Riccardo only for interfaces, texts shown to people, API
  responses. One complete message per brief, reports under 10-15 lines.
- Personal GitHub repos may be pushed at any hour; company remotes never
  outside office hours.
- After many rounds without convergence, the next round is not the answer:
  name the pattern that generates the defects, fix its root or bring the
  options with their cost to the user.
- Diary dates from `date`, never estimated; never `rm` outside the worktree;
  stop only what you started, by name; prove an environment red is
  environmental; never claim done without one of the three evidence levels.

Developer agents (user 2026-10-29): the coordinating session starts the
developer agents itself -- Agent tool with `isolation: "worktree"`, Sonnet
for written tasks -- instead of proposing chips for the user to click. Each
gets its own branch off the current HEAD, its own Docker project
(`docker compose -p epocha-<name>`, no host ports, own database) and a
complete brief; the coordinator integrates.

Dashboard pages (the `dashboard` app, the operator UI): Riccardo is the expert
(user 2026-10-29) -- every new or changed page goes through `riccardo-mode`
first, then one adversarial round with Matteo, then Utente mode on the main
tasks, with screenshots in both themes and the measured interface gate of
the global CLAUDE.md.

Epocha specifics still hold on top: the build map rule, Spec Kit, the bilingual
whitepapers, and the scientific-method golden rule of the project
CLAUDE.md. Related: [[feedback-build-map-source-of-truth]],
[[feedback-speckit-mandatory]].

---
name: feedback-gh-alias-trap
description: "In the user's shell `gh` is an alias for `git hist`; call the GitHub CLI as /opt/homebrew/bin/gh. Also: the night guard cannot resolve a git path held in a shell variable, so pushes must use literal paths."
metadata:
  node_type: memory
  type: feedback
  originSessionId: f3c14087-5073-413f-8363-93f01142295b
  modified: 2026-10-29T13:18:49.858Z
---

Found on 2026-10-29 in the Epocha coordinating session:
1. `gh` in the user's zsh profile is an alias for `git hist`, so `gh issue view 19`
   prints "git: 'hist' is not a git command". The GitHub CLI is
   `/opt/homebrew/bin/gh`. Subagents get a clean shell and did not hit it.
2. `~/.claude/hooks/night-guard.sh` blocks a `git -C $W push` whose path is a
   shell variable ("una cartella che non so risolvere"), even in office hours.

**Why:** both look like real failures (missing tool, night rule) and waste a
round trip or lead to a wrong diagnosis.

**How to apply:** in Bash calls use `/opt/homebrew/bin/gh` and literal paths
for any `git push`. Commits still go through `git-commit-assistant`.

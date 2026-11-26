---
name: reference-git-backup-bundle
description: "Full git bundle of every Epocha branch taken before the 2026-10-29 branch cleanup: ~/Documents/workspace/Epocha-backup/; recover any deleted branch from it."
metadata:
  type: reference
---

Before deleting 12 remote and 26 local branches on 2026-10-29 (user's go: «le
cancellazioni falle pure tu ma in sicurezza»), a bundle of all local and remote
refs was made and verified:
`~/Documents/workspace/Epocha-backup/epocha-all-refs-2026-10-29.bundle` (67
heads) plus `refs-2026-10-29.txt` (sha per branch). Recover a branch with
`git fetch ~/Documents/workspace/Epocha-backup/epocha-all-refs-2026-10-29.bundle <name>:<name>`.
The full list of what was deleted is in
`Diario/2026/10/2026-10-29/epocha-ricognizione-branch.md`.

Also found that day: `main` was 586 commits behind `develop` (last on
2026-03-23) -- a release merge is the user's decision, proposed after the Plan 4
merge.

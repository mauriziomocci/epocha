---
name: feedback-conversations-are-data
description: "User 2026-10-29: conversations with Epocha characters are valuable to the user and must never be lost; keep them persisted, backed up outside the public repo, resumable."
metadata:
  type: feedback
---

On 2026-10-29 the user asked to keep the character Kael Vrith and his
conversation forever, then: «tieni queste criticità in mente in modo che non
si ripetano».

**Why:** the only copy lived in a local Docker volume; the group chat is not
persisted at all; nothing could export or import a character. Losing a
conversation the user cares about is a real loss, not a dev-data cleanup.

**How to apply:**
- Before any operation that can touch the local `epocha` database (migrations,
  volume work, `down`, restores, test runs pointed at it), take a fresh
  `pg_dump -Fc` into `~/Documents/workspace/Epocha-personaggi/`.
- Never put a DB dump in a versioned repo, public or private (it holds the
  test-user password hash); transcripts and character JSON may go in the
  private diary.
- When chat or dashboard work is planned, the persistence gaps in
  [[project-chat-coherence]] point 5 (group chat not saved, duplicated injected
  memories, no character export/import) are requirements, not nice-to-haves.
- Off-site copy of the backups only with the user's explicit go.
Related: [[project-kael-vrith-keep]].

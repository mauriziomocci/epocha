---
name: project-public-website
description: Public website for Epocha requested 2026-09-26 as a separate Spec Kit work item; static site from repo docs recommended over WordPress; must not claim validated results.
metadata:
  node_type: memory
  type: project
  originSessionId: f3c14087-5073-413f-8363-93f01142295b
  modified: 2026-09-26T15:47:15.896Z
---

On 2026-09-26 the user asked whether a WordPress site for Epocha was premature
and chose to open it as a separate work item, in a separate session (not on the
demography Plan 4 branch, which was mid phase-6 gate). A session chip was
prepared to run phases 1-2 only (spec, adversarial audit, stop at the user's
phase-2 approval).

Recommendation given, to be evaluated in brainstorming, not assumed: a static
site generated from the repo's own documents (READMEs, bilingual whitepapers,
build map), e.g. MkDocs on GitHub Pages, instead of WordPress -- a CMS is a
third copy of content that changes at every merge, plus a database, security
updates and hosting. The choice is the user's.

**Why:** content drift is this project's recurring failure (the build map once
went 94 days stale), and the paper goal makes an unsupported public claim the
hardest damage to undo.

**How to apply:** the site must present vision, methods and status as "in
development, not validated": historical validation has never run, and runs with
the same seed do not reproduce the same agents
([[project-determinism-enumeration-pending]]). Bilingual IT/EN. Open it in the
build map when the work item starts ([[feedback-build-map-source-of-truth]]).

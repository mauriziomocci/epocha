---
name: feedback-mirofish-ethics
description: Rule 2026-10-29 -- take ideas and background from MiroFish, never code or prompts, and cite it wherever an idea comes from it.
metadata:
  type: feedback
---

User rule (2026-10-29): Epocha may take ideas and, where possible, background
from MiroFish (https://github.com/666ghj/MiroFish), but never copies its code
or prompts, and cites MiroFish wherever it is correct to do so.

**Why:** ethics first ("dobbiamo essere etici"), and licensing: MiroFish is
AGPL-3.0 and Epocha is Apache-2.0, so copied code or prompts would impose
AGPL on Epocha; an idea re-implemented independently is free, but its origin
is credited.

**How to apply:** a spec or whitepaper section that adopts an idea first seen
in MiroFish (e.g. the tool-using report agent, current vs superseded facts,
interviewing agents without advancing the simulation) cites it in its
background/related-work part with the repository URL and the date read;
implementation is written from Epocha's own design, never by reading
MiroFish's code side by side while writing. If an idea's origin is the OASIS
paper or another source, cite that source instead. Related:
[[mirofish-comparison]], [[project-scalability-analysis]].

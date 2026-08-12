# Phase-6 audit on the CODE, rounds 1 to 8 — register, with its limit declared

**Why this file exists.** Round 9 found that no phase-6 report had been filed: `audit/` held only the phase-0 and phase-2 rounds. Eight rounds and 83 findings were asserted closed in `tasks.md` and on the build map with **no artifact a reader could check**, and that assertion is what the merge ratification rests on. This register does not manufacture the missing reports. It records what is reconstructible from the commits and from `tasks.md:55`, and states plainly what is not.

**What is reconstructible.** Each round's remediation is a commit, and the diff shows what was changed. The narrative of each round survives in `tasks.md:55` and in the build map paragraph, both written at the time. Round 9 independently re-verified four of round 8's ten findings.

**What is NOT reconstructible, and must not be read as verified**: the per-finding text of rounds 1 to 8 — their exact wording, their classification, and the evidence each carried. The claim "83 findings, all closed" is therefore **supported by the remediation commits and by the narrative, not by a checkable per-finding record**. Anyone ratifying the merge should know that.

**The rule this cost.** File the report in the same commit as the remediation. A round whose findings exist only in a conversation is a round nobody can audit, which is the exact failure this project's audit policy exists to prevent.

## The rounds

| Round | Verdict | Findings | Remediation commit | What it was about |
|---|---|---|---|---|
| 1 | NOT CONVERGED | 18 | `2a82632` | Not one formula error. The docstring of `inherit_trait` still described the defect as current; the present-value horizon reaching zero at 62 was declared nowhere; the whitepapers contradicted themselves between §4.1.5 and §11 in both languages; two acceptance criteria had no witness; three tests could not fail. |
| 2 | NOT CONVERGED | 9 | `5a2713e` | The blocking finding was self-inflicted: round 1's own remediation promoted a citation the amendment declares unverified into an asserted one, and attached one chapter's title to another. |
| 3 | NOT CONVERGED | 13 | `b9350b8` | The citation class a third time — a section heading promoted to a chapter title, published in five files by the sentence certifying it verified. Also two guards unable to fail: the copula's asymmetry invisible through the only observable exposed, and a cache-mutation guard exercising one of three passes while claiming all three. |
| 4 | NOT CONVERGED | 7 | `a6d4ffe` | The citation a fourth time, with two occurrences missed inside the very module that had just written the no-titles rule. Closed with the structural guard instead of a fifth hand pass; it found seven more on its first run. |
| 5 | NOT CONVERGED | 7 | `d25574f` | The guard did not catch the defect it was built for: it skipped a whole window as soon as one correct citation appeared, and every real citation contains one. Rebuilt to judge each reference on its own, walk the whole repository, and prove itself with probes. |
| 6 | NOT CONVERGED | 11 | `0dcfc75` | Five demonstrated escapes against the rebuilt guard, all from a bound expressed as a count of lines. Replaced by the citation region. |
| 7 | NOT CONVERGED | 8 | `aac0917` | A retracted sentence still standing on the build map; the paragraph bound producing false positives; the list split cutting an author-date entry in half. |
| 8 | NOT CONVERGED | 10 | `f0e3261` | `PROXIMITY_CHARS` suppressed a false positive that does not exist and opened a real blind spot at 812 characters. Deleted with two tests that bound nothing. The process rule was adopted here. |
| 9 | NOT CONVERGED | 6 | `64be598` | See `phase6-round-9-NOT-CONVERGED.md`, filed in full. |
| 10 | NOT CONVERGED | 5 | this branch | See `phase6-round-10-NOT-CONVERGED.md`, filed in full. First round run against a written stopping criterion (`5b33d4b`). |

## Round 8's findings, as far as round 9 could check them

Four of the ten are independently verified: the proximity bound removed; its false justification removed from all four artifacts that carried it; the two tests that bound nothing removed; the process rule written into the guard. The remaining six are not checkable from any artifact.

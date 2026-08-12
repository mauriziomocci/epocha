# Phase-6 adversarial audit on the CODE, round 11 — CONVERGED

**Scope**: narrow, `git diff 5b33d4b..37cc452` — the single remediation commit of round 10. Seven files, +206/-48.

**Verdict**: **CONVERGED**, against the criterion committed at `5b33d4b` *before* round 10 ran. Seven findings, **none in either blocking class**: zero defects in production code, zero criteria that cannot fail. All seven are figures and sentences, which the written criterion declares non-obstructive; all seven are corrected in the remediation commit for this round.

## The principal question: did round 10 do to round 9 what it accused round 9 of doing?

**No.** A 34-mutation battery run in full against `64be598` and against `37cc452`. **No mutant that killed before survives now**, and four more die:

| mutation | `64be598` | `37cc452` |
|---|---|---|
| `_normalise`: flattening removed (strict) | SURVIVES | **KILLED** |
| `FORBIDDEN_TITLES`: drop `componenti della varianza` | SURVIVES | **KILLED** |
| `ANY_CHAPTER`: drop `capp?\.?` | SURVIVES | **KILLED** |
| `FORBIDDEN_TITLES`: add a fifth string with no probe | SURVIVES | **KILLED** |

The two changed payloads are identical after normalisation, so the wrap-broken payload could lose nothing; the only possible difference lay in the normalisation mutations, and there the new version is strictly stronger. Deleting the three `HTML_ENTITIES` entries could not remove coverage: no payload used them and they occur nowhere in the repository.

Four mutants survive at HEAD. Three — `&amp;`, `capitoli`, `IGNORECASE` on `SOURCE` — are the inventory round 10 filed as F-4 and F-5, with no observed violation behind them. The fourth, `fullmatch`→`search` in `_chapter_offenders`, was shown **equivalent**: over 3 528 synthetic strings (14 keywords × 5 separators × 7 numbers, with and without a range) plus every real match across the repository's 53 regions, the two never diverge.

## Findings, all non-blocking, all closed

**R11-1 INCORRECT — round 10's own evidence table does not reproduce as written.** It names the mutation as blanking `_normalise` while printing the numbers of the strict mutation. Re-measured, all four cells: strict gives 1 failed at `ad1d942` and 18 passed at `64be598`; whole-body gives 2 failed and 1 failed, because blanking the body also disables `&nbsp;` resolution. The finding it proves is still true; the label on the proof was wrong, and the loose wording had propagated verbatim to `tasks.md` and the build map. **Closed** by naming the strict mutation and printing both columns.

**R11-2 INCORRECT — `&nbsp;` rests on a provenance git denies.** `git log -S` over all refs: it has never appeared in the build map, or anywhere outside the guard file, in any reachable commit. Round 6 introduced it as a live escape; it was constructed. **Closed** by keeping the entry as a **declared** exception with the judgement written beside it — the surveyed set includes a hand-rewritten HTML page, `&nbsp;` is that format's commonest entity, and `ANY_CHAPTER` matches on `\s*`, so one such entity between keyword and number would silently disarm the chapter guard on the very file carrying the citation. Removing a cheap defence is not the same decision as adding one, and the process rule governs additions. The docstring calling all those cases live escapes is corrected.

**R11-3 INCORRECT — "12 real occurrences" of `&amp;` is a line count published as an occurrence count.** Measured: 13 occurrences over 12 lines, line 365 carrying two. A unit switch, two paragraphs below the sentence about unit switches. **Closed.**

**R11-4 INCORRECT — round 9's "full series" is not full.** Every commit touching the file: 167, **275 (`d25574f`)**, 445, 543, 453, 480. Round 10 re-verified three of the four printed figures, called them exact, and could not see the missing one — a completeness claim checked by re-verifying its members is the one check that cannot detect an omission. **Closed.**

**R11-5 INCONSISTENT — the comment above `INJECTION_CASES` said the opposite of what the code did.** It promised the completeness test reads the named list "instead of reaching into pytest's marks"; the test read `...pytestmark[0].args[1]`, which is also fragile by position. **Closed** by reading `INJECTION_CASES`, which was in scope three lines away.

**R11-6 INCONSISTENT — the register was titled "rounds 1 to 8" and tabulated ten.** **Closed** by renaming the file to `phase6-REGISTER.md` and recording why: a filename is an assertion, and it goes stale the way a docstring does.

**R11-7 INCONSISTENT — round 9's F-1 still read "Closed" with no note**, although round 10 proved that closure destroyed a witness. Whoever read only the round-9 report learned the wrong thing. **Closed** by marking it REOPENED with the pointer.

## VERIFIED

- **The completeness test fails in both directions**: a fifth forbidden string with no probe → 1 failed, and it is that test alone; a probe whose `expected_title` is not in the list → 2 failed.
- **The identity assertion hides no silent false positive**: injecting `"quantitative genetics"`, which really does occur in probe 2's payload, gives 3 failed including the whole-repository title guard. It fails loudly on three fronts, never green when it should not be.
- **Deleting the three entities opened no hole.** Survey at HEAD: 53 regions, 20 files, zero title offenders and zero chapter offenders, identical with and without the numbered-list marker. Paragraph-only rule: exactly two false positives, both Markdown, zero from HTML.
- **The decisive reproduction is still red**: `2 failed, 18 passed`, both guards firing at `epocha/_probe.py:669`.
- **No live line count survives anywhere.** The only remaining `480` is an assertion about the frozen commit `64be598`, not about the file now.
- **All twenty tests are killable**, each by a named mutation, including `SANCTIONED_REFERENCE` made inert (7 failed, 13 passed).
- **Class 1 empty**: the diff touches no `epocha/apps/**/*.py` outside `tests/`.
- **The register's arithmetic**: 83 + 6 + 5 = 94, which is the figure `tasks.md` carries.

## What converged, and what that does and does not mean

Eleven rounds, 101 findings, all closed. The last four rounds found nothing in the production code, because **the executable scientific code has not moved since round 3** — which is what the stopping criterion was written to recognise rather than to excuse. What the last eight rounds were really auditing is the guard that stops one defect from recurring, and its final state is proven the only way that matters: every one of its twenty tests has a mutation that kills it, and the defect it exists for still turns it red when reinjected.

**Sixteen criteria that could not fail** were found on this work item. That is the number worth carrying forward, and the two process rules it produced are worth more than either fix that occasioned them.

**THE THING**: nothing blocking remains. The gate is closed and the merge is now a decision for the user to ratify, not for another round to postpone.

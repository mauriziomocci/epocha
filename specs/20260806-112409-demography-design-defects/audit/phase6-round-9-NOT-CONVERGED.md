# Phase-6 adversarial audit on the CODE, round 9 — NOT CONVERGED

**Scope**: narrow, `git diff aac0917..f0e3261` — the single remediation commit of round 8. Four files, +88/-178, almost all of it in `epocha/apps/demography/tests/test_citation_hygiene.py`.

**Verdict**: NOT CONVERGED. 2 INCORRECT, 1 INCONSISTENT, 2 UNJUSTIFIED, 1 MISSING. All six closed in the same session; every finding below was re-measured independently before being accepted, and every fix is mutation-proven.

**Method**: nineteen mutations applied to the guard one at a time, each followed by the file's suite and a `git checkout`. Fourteen killed, five survived. Three independent surveys of the real repository (paragraph-only rule, whole-file rule, effect of the numbered-list marker) run outside the test. The decisive reproduction executed and cleaned up.

## F-1 INCORRECT — the defence against the citation *as it was actually written* had no witness

`test_citation_hygiene.py:232` compares `FORBIDDEN_TITLES` against `window.lower()`, and all four entries are lower-case. Removing `.lower()` left **18 of 18 tests green**, and no module outside the file imports the guard.

This is not a constructed shape. The historical violation carried initial capitals, because it came from an index entry — a chapter title. At commit `5a2713e`:

- `docs/superpowers/specs/2026-04-18-demography-design-it.md:1893` — `9 *Resemblance between Relatives*`
- `epocha/apps/demography/inheritance.py:6` — `9 "Resemblance between ..."`
- `specs/.../research/0.1a-distributional-family-INPUT.md:166` — `9 Resemblance between Relatives`

`git log -S "Resemblance between Relatives"` returns two commits, `5a2713e` and `b9350b8`; the all-lower-case variant appears in neither. Case-folding is therefore the single line that catches the real form of the defect, and it was the line nothing defended — in a file that had just been through a size-reduction refactor, where anything without a witness is what gets deleted.

**Closed** by capitalising the payload already present at the "title broken across two lines by wrapping" case. Zero new cases, zero new constants. Mutation: dropping `.lower()` now fails 1 of 18.

## F-2 INCORRECT — "back under 300 lines" is false, and was published in four artifacts

`wc -l`: **453** at `f0e3261`, not under 300. The full series in total lines is 167 at birth (`a6d4ffe`), 445, 543 at round 8's peak (`aac0917`), 453 after the cut. Round 8's cut is **16.6%**, not "to a third of its size", which is the subject line of the commit that made it. In code lines — blanks, comments and docstrings excluded — 305 to 255.

Worse than the number is the unit switch inside one sentence: 167 and 543 are total lines, "under 300" holds only for code lines. The claim appeared in `test_citation_hygiene.py:34`, `docs/build-map/epocha-build-map.html:365`, `HANDOFF-2026-08-12.md:46`, `tasks.md:55`, and in the commit subject. A file that exists to stop an unverified figure from circulating had published one about itself.

**Closed** by replacing the claim with the measured series in all four artifacts, each stating its unit. The commit subject stands wrong in the history and is not rewritten.

## F-3 INCONSISTENT — a retracted premise still standing on the source of truth

`docs/build-map/epocha-build-map.html:365` said the paragraph rule "manufactured false positives wherever there is nothing to split on, since in HTML a paragraph is one 22 kB run", and three sentences later, in the same paragraph, "the false positive justifying it did not exist".

Measured. Under the paragraph-only rule the repository yields **exactly two** false positives, `ch. 29` at `docs/whitepaper/epocha-whitepaper.md:2873` and `docs/whitepaper/epocha-whitepaper.it.md:2653` — the Solon (1999) bibliography entry, both Markdown. **HTML yields zero**: the build map has a single region naming the source, at line 413, 2 844 characters long, carrying no chapter reference at all. This is the same class round 7 already caught on this page: a retracted sentence surviving on the source of truth.

**Closed** by rewriting the sentence with the measurement.

## F-4 UNJUSTIFIED — the numbered-list branch kills nothing and rests on a case that does not exist

`LIST_ITEM` at line 123. Dropping `|\d+\.` left 18 of 18 green. Surveyed against the repository, with and without it: **53 regions naming the source, across 20 files, zero offenders, identical in both**. The justification written above it — that dropping the numbered form let a numbered entry sweep in its neighbour's legitimate chapter — describes a bibliography this repository does not contain.

**Closed by deletion**, per the process rule the file itself carries. The comment now records the measurement and names the condition for restoring it: a numbered bibliography, with the file and line that carries it.

## F-5 MISSING — three further live branches with no witness, all masked by one structural cause

Surviving mutants, all on a green suite: dropping `capitolo|capitoli` from `ANY_CHAPTER`; dropping the two Italian titles; dropping `components of variance`.

One cause: `caught = _title_offenders(...) + _chapter_offenders(...)` asserted the **union**. Every end-to-end payload carries a forbidden title *and* an out-of-range chapter, so a payload exercising two branches proves neither. This is the fourteenth occurrence on this work item of a criterion that cannot fail where the requirement is false.

**Closed** by asserting the two lists separately. All three mutants now fail 1 of 18. No payload added.

## F-6 UNJUSTIFIED — an end-to-end test whose stated reason to exist had been deleted

Its docstring claimed the value of the test is exercising `_text_files`, the window and the offender assembly, "which is where all three holes were". After the move to `tmp_path` the helpers are called with `files=[probe]` and `_text_files` is never touched — as a comment eight lines below says. The test also killed nothing its sibling did not already kill.

**Closed** without deleting it: F-5's separated assertions make all three payloads discriminating, and the docstring now says what the test covers and what covers the walk instead.

## VERIFIED

- **Decisive reproduction: RED.** `git show b9350b8:...inheritance.py > epocha/_probe.py` → `2 failed, 16 passed`, both guards firing at `epocha/_probe.py:669` on `'resemblance between relatives'` and `'chapter 8'`. Probe removed, tree clean.
- **`PROXIMITY_CHARS` removed from all four artifacts.** `grep -rn` over the repository returns only narrative occurrences, all correct. (Round 10 noted that the count stated here — two — was a snapshot the filing of this very report invalidated, since the report and the register add two more. The count is dropped; the property is what matters.)
- **Probes are outside the walk.** `REPO_ROOT` is `/app`, `tempfile.gettempdir()` is `/tmp`, no `basetemp` in `pyproject.toml`; `_text_files()` cannot reach them.
- **The declared limit is honest**: in the reproduction, the `chapter 9` and `chapter 8` in the defective module's header do not fire because a blank line separates them from the region naming the source — exactly what the docstring declares.
- **"138 violations against 0"** under the whole-file rule: measured 138 exactly.
- **Suite**: 1571 before, unchanged after; the guard runs in ~10s, under 2% of the suite.

## The guard fired on this round's own remediation

Worth recording, because it is the first time it has caught something nobody was looking for. Rewriting the build map's retracted sentence introduced the source's name into a paragraph that already carried two `chapter 8` references and had just gained a `chapter 29` — and the guard went red on `docs/build-map/epocha-build-map.html` before the commit. Not a probe, not a mutation: the ninth reviewer of this defect nearly wrote the tenth occurrence of it, into the source of truth, while documenting why it keeps happening. The prose was fixed; the guard was not touched.

## THE PATTERN

Five consecutive rounds have caught the same thing and this one catches it twice: **a property declared in prose and not enforced by a mechanism**. Round 8 deleted a constant justified by a false positive that does not exist; the commit under review restored a branch justified by a case that does not exist, kept three payloads that mask three branches, and published on four artifacts a measurement of its own slimming that does not survive `wc -l`. The remedy is not additive: delete what kills no mutant, split what was summed.

**THE THING**: `.lower()` was the only defence against the form the violation actually had in this repository, and it could have been deleted without a single test noticing.

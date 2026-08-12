# Phase-6 adversarial audit on the CODE, round 10 — NOT CONVERGED

**Scope**: narrow, `git diff ad1d942..64be598` — the single remediation commit of round 9. Six files, +159/-21.

**First round judged against a written criterion.** The stopping criterion was committed at `5b33d4b`, *before* this round ran, because nine rounds had gone by without one and a criterion read after seeing the result is a negotiation. It blocks on two classes only: a defect in production code, or a criterion that cannot fail. Wrong figures, contradictory sentences and outdated docstrings are corrected in the same commit and do not reopen the gate.

**Verdict**: NOT CONVERGED. Two findings in the blocking class, three outside it. **Zero in class 1** — the diff touches no production file, and neither did rounds 6 to 9.

**Method**: 33 mutations applied one at a time, each followed by the file's suite and a byte-for-byte restore; 24 killed, 9 survived. The decisive reproduction executed and cleaned up. Every measurement re-run independently before the finding was accepted.

## F-1 INCORRECT — **BLOCKING** — the remediation deleted a witness while adding others

`test_citation_hygiene.py`, the case labelled `"title broken across two lines by wrapping"`. Before `64be598` the payload really did break the forbidden title across the wrap (`...on resemblance\n  between relatives...`). Round 9 capitalised it to give `.lower()` a witness — correctly, that mutant now dies — and in the same edit moved the whole title onto the second line. The line break stayed in the payload; the title stopped straddling it.

Measured, both sides. The mutation is the STRICT one — replace the flattening return, `return " ".join(text.split())` → `return text`, leaving entity resolution in place. Round 11 caught this table naming it loosely: blanking the whole function body also disables `&nbsp;` resolution and yields different numbers, so anyone re-running it as first written gets 2 failed where they read 1.

| version | strict: flattening removed | whole body → `return text` |
|---|---|---|
| `ad1d942` (before) | **1 failed** — and the test that falls is exactly this case | 2 failed |
| `64be598` (after) | **18 passed** | 1 failed (the `&nbsp;` case) |
| after this round's fix | 1 failed | 2 failed |

Whitespace flattening is a live branch — it is the only thing that makes a wrap-broken title match the flat string it is compared against — and it is asserted twice in prose. From that commit it was defended by nothing, while the case label went on claiming the shape the payload had stopped having. Class 2 to the letter. **Occurrence fifteen.**

**Closed** by breaking the title across the wrap *and* keeping the capitals, so the one payload carries both properties. Both mutants now die.

## F-2 MISSING — **BLOCKING** — the fourth forbidden title had no witness

Deleting `"componenti della varianza"` from `FORBIDDEN_TITLES` left **18 of 18 green**. The other three each kill a mutant.

Not a constructed form: `docs/whitepaper/epocha-whitepaper.it.md:901` at commit `5a2713e` carried `capp. 8-10: componenti della varianza, somiglianza fra parenti, ereditabilità` — chapter titles attached to the source, which is the defect the guard exists for.

The structural cause is that round 9's fix was half a fix. Separating the two offender lists was necessary but `assert titles` only checks **non-vacuity**: three payloads cannot testify for four strings, and nothing notices. Round 9's own docstring claimed the separation made all the masked branches discriminating; measured, it made one of the two Italian entries discriminating.

**Closed on the class, not the instance**: the assertion now names WHICH title it expects (`{title for ...} == {expected_title}`), a fourth payload carries the observed Italian form reduced to that single title, and `test_every_forbidden_title_has_a_witness` fails the moment a fifth string is added with no probe behind it. Without that last test the next entry would be silently deletable, which is exactly how the fourth one arrived.

## F-3 INCORRECT — non-blocking — a wrong figure inside the paragraph written to stop wrong figures

The module docstring said round 9 "spent 25 lines". `git show --numstat 64be598` gives +45/−18 on the file, net **+27**, and 480 − 453 = 27. Wrong under the other reading too. Inside the paragraph headed "THE SIZE, counted rather than asserted".

The rest of the series was re-counted by hand and holds exactly: 167 at birth (`a6d4ffe`), 543 at the peak (`aac0917`), 453 after the cut (`f0e3261`); 305 → 255 code lines; cut 90/543 = 16.6%.

**Closed** by removing the per-round line-spend figure entirely. It is a number that invalidates itself at every edit of the file that states it, which is a design defect in the sentence, not an arithmetic slip.

## F-4 INCONSISTENT — non-blocking — the rule applied to `\d+\.` was not applied to `HTML_ENTITIES`

Round 9 deleted the numbered-list marker because it killed nothing and rested on a bibliography the repository does not contain. Three entries of `HTML_ENTITIES` were in the identical condition: `&#160;`, `&ndash;` and `&mdash;` occur **zero times** in the repository and removing any of them leaves 18 of 18 green.

**Closed by deletion.** `&amp;` stays and the reason is stated: it normalises an entity the surveyed text actually contains — 13 occurrences over 12 lines of the build map; this report first published the line count as an occurrence count, which round 11 corrected — even though the guard does not depend on it today, since `SOURCE` matches the surname alone.

**Round 11 addendum**: the same measurement reaches `&nbsp;`, which this round left standing. `git log -S` over all refs shows it has never appeared outside the guard file, so round 6 introduced it as an escape that was constructed rather than observed. It is kept, but now as a **declared** exception with its judgement written beside it, and the docstring that called all those cases live escapes is corrected.

## F-5 MISSING — non-blocking — three further branches without a witness, and no observed violation behind them

`capp?\.?` and `capitoli` in `ANY_CHAPTER`, and `re.IGNORECASE` on `SOURCE`, all survive mutation. Recorded as inventory, not as a request for payloads: in the repository `capp.` occurs 4 times and `capitoli` 34, always inside correct citations, and the surname is always capitalised. The process rule cuts the other way here, and that is precisely the difference from F-2, which is why F-2 blocks and this does not.

## VERIFIED

- **The union left standing in the other parametrized test is correct.** Measured payload by payload: six cases fire only the chapter guard, one only the title guard, two neither. No payload fires both, so the sum masks nothing and splitting it would kill no additional mutant.
- **Deleting `\d+\.` opened no hole.** Re-measured outside the test: 53 regions naming the source, across 20 files, zero offenders, with and without the marker, and the file sets are identical.
- **The false-positive measurement is exact**: under the paragraph-only rule, exactly two, both Markdown, zero from HTML.
- **The decisive reproduction is still red**: `2 failed, 16 passed`, both guards firing at `epocha/_probe.py:669`.
- **The three mutants named in round 9's F-5 are genuinely dead.** The closure is real; it is the finer grain — one of the two Italian entries — that escaped.
- **The register is honest and deposits something checkable.** All eight remediation commits exist and their subjects match their rows; 18+9+13+7+7+11+8+10 = 83, plus round 9's 6 = 89, the figure in `tasks.md`; `audit/` did hold only the phase-0 and phase-2 reports. Its declared limit distinguishes what the commits prove from what nothing proves, and tells whoever ratifies the merge what they cannot lean on.
- **Class 1 of the criterion is empty**: the diff touches no `epocha/apps/**/*.py` outside `tests/`.

## THE PATTERN

For the second round running, repairing one witness destroyed another, and both times the destroyed one defended a property asserted in prose: round 8 deleted a constant together with the two tests that bound it, round 9 rewrote the one payload that bound whitespace flattening. The common cause is not carelessness. It is that **mutation coverage is measured only after the fix, never as a difference**. Nobody re-ran the battery against the previous version to see what the fix had stopped killing.

**Adopted, and written into the file**: when a payload or a constant changes, run the mutation battery against the PREVIOUS version too. A fix is not judged by the mutants it kills but by the ones it stops killing.

**THE THING**: the wrap-broken title had to go back into the payload that round 9 rewrote — and the rule that catches this class in future is to diff mutation coverage, not to inspect it.

# Audit Re-pass Campaign 2026-04-12 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Phase 5 implementation runs Opus 4.7 for adversarial audits and Sonnet 4.6 for mechanical fix-implementer rounds; escalation to Opus is triggered by any scientific decision outside specified execution.

**Goal:** Resolve the documentation debt accumulated since the 2026-04-12 batch scientific audit by running a Round 2 adversarial re-audit on the 13 originally-audited modules, applying fixes until each module reaches CONVERGED, promoting the audited modules from chapter 8 (Designed Subsystems, audit pending) to chapter 4 (Methods, audited) of the bilingual whitepaper, and deprecating the legacy world/economy.py placeholder superseded by the new economy package.

**Architecture:** Six sequential feature branches off develop, one per cluster. Each branch follows a standard audit-fix-promote-merge procedure documented in section "Common Procedures" below. The whitepaper section §8 receives two new entries (affinity and election) before the promotion campaign begins, so that all modules in scope can move through the §8 → §4.x pipeline uniformly. The world/economy.py legacy module is deprecated rather than re-audited.

**Tech Stack:** No code-architecture changes. Modifications are scientific corrections to existing modules (citation attribution fixes, parameter justification, formula corrections), markdown updates to the bilingual whitepaper, and one deprecation comment block on world/economy.py.

**Spec:** None separate from this plan. The original audit findings are in `docs/scientific-audit-2026-04-12.md` and act as the requirements baseline.

**Depends on:** `develop` HEAD `ab1a725` (catch-up README+whitepaper merged 2026-04-26).

**Follow-up plans:**
- After this campaign: Demography Plan 3 (Inheritance + Migration) — the next scheduled major work item.
- Long-term: Validation experiments execution per `project_validation_experiments_pending.md`.

**IMPORTANT notes for implementers:**

- The original audit transcript at `docs/scientific-audit-2026-04-12.md` is a JSON-encoded subagent transcript. Use the Python parsing snippet at the top of this plan's "Common Procedures" section to extract the per-module findings.
- Three remediation commits already exist: `17f046a`, `7744016`, `951a606`. Each fix-implementer must verify that the original Round 1 finding is actually closed in the current code, not just that a commit was made.
- The whitepaper EN authoritative file is `docs/whitepaper/epocha-whitepaper.md`. The IT mirror is `docs/whitepaper/epocha-whitepaper.it.md`. The `<filled-on-merge>` placeholder strategy applies to every promoted §4.x status header: leave the placeholder during the branch, replace with merge SHA via post-merge follow-up commit (per `project_whitepaper_promotion_pipeline.md`).
- The `feedback_whitepaper_doc_sync.md` memory must be updated to add the new §4.x mapping rows after each promotion.
- The `README.md` and `README.it.md` status tables must be updated after each promotion to flip the audit column from "Round 1 audit + remediation, Round 2 pending" to "yes (CONVERGED `<date>`)".
- All documentation in English; only spec files would be Italian (no specs in this campaign).
- No emoji, no AI/Claude attribution, anywhere in code or commits.
- Conventional Commits format. Allowed types: `fix(science)` for code corrections to scientific modules; `docs` for whitepaper/README updates; `chore(deprecation)` for the legacy world/economy.py marking. Scope per CLAUDE.md.
- `python -m pytest --cov=epocha -v` must remain at 800 passing tests with zero failures at every commit. If a fix changes test expectations, update the test in the same commit.

---

## File Structure

| File | Responsibility | Touched by branch(es) |
|------|---------------|----------------------|
| `epocha/apps/agents/reputation.py` | Reputation model fixes | #1 |
| `epocha/apps/agents/information_flow.py` | Granovetter weak-tie wiring fix | #2 |
| `epocha/apps/agents/distortion.py` | Allport-Postman / Bartlett attribution | #2 |
| `epocha/apps/agents/belief.py` | Personality-weighted acceptance fixes | #2 |
| `epocha/apps/agents/affinity.py` | Affinity score citation fixes + audit pending → audited | #2 |
| `epocha/apps/world/government.py` | Acemoglu-Robinson / Powell-Thyne / coup determinism fixes | #3 |
| `epocha/apps/world/government_types.py` | Polity 5 reference fixes | #3 |
| `epocha/apps/world/institutions.py` | 6 findings on institutional dynamics | #3 |
| `epocha/apps/world/stratification.py` | Alesina-Perotti / Gini scope fixes | #3 |
| `epocha/apps/world/election.py` | Voting model citation fixes | #3 |
| `epocha/apps/agents/movement.py` | Chandler / Braudel attribution fixes | #4 |
| `epocha/apps/agents/factions.py` | Olson collective action fixes | #5 |
| `epocha/apps/world/economy.py` | Add deprecation marker | #6 |
| `docs/whitepaper/epocha-whitepaper.md` | Promote §8 entries to §4.x as each cluster converges | all branches |
| `docs/whitepaper/epocha-whitepaper.it.md` | Italian mirror of promotions | all branches |
| `README.md` + `README.it.md` | Status table updated as each cluster converges | all branches |
| `docs/memory-backup/feedback_whitepaper_doc_sync.md` | Add new §4.x mapping rows | all branches |

The plan adds zero new files (the whitepaper/README updates are edits, not creations).

---

## Common Procedures

These are referenced repeatedly per branch. Each branch executes the same procedure with module-specific arguments.

### CP-1: Extract findings for a module set

```python
import json, re
path = 'docs/scientific-audit-2026-04-12.md'
modules_of_interest = ['MODULE_A', 'MODULE_B', ...]   # set per branch
with open(path) as f:
    events = [json.loads(l) for l in f.read().splitlines() if l.strip()]
report = next(c.get('text','') for ev in events for c in (ev.get('message',{}).get('content',[]) if isinstance(ev.get('message',{}).get('content',''),list) else []) if isinstance(c,dict) and c.get('type')=='text' and 'INCORRECT' in c.get('text',''))
sections = re.split(r'### Module: ', report)[1:]
for sec in sections:
    name = sec.split(' (')[0]
    if name in modules_of_interest:
        print('===', name, '===')
        print(sec[:5000])
```

### CP-2: Verify Round 1 remediation

For each finding extracted in CP-1, open the corresponding code file at the cited line(s), compare current implementation against the finding's "Fix:" recommendation, classify as:
- **CLOSED**: Round 1 commit fixed the finding correctly. No new action.
- **PARTIAL**: Round 1 commit addressed part of the finding. Round 2 fix needed for residual.
- **NOT FIXED**: Round 1 did not address the finding. Round 2 fix needed.
- **REGRESSED**: Round 1 introduced a new issue. Round 2 fix needed.

Build a status matrix (one row per finding) and commit it as a working note in the branch (file `audit-repass-status-MODULE.md` in branch root, deleted before merge).

### CP-3: Dispatch Round 2 adversarial audit

Use the Agent tool with `subagent_type=critical-analyzer`, `model=opus`. Prompt template:

```
F-CAMPAIGN Round 2 audit on Epocha module(s): MODULE_LIST.

Working dir: /Users/mauriziomocci/Documents/workspace/Opensource/epocha
Branch: BRANCH_NAME
Files to audit:
- LIST_OF_FILES

Original 2026-04-12 audit findings for these modules (extracted via CP-1):
[paste extracted findings verbatim]

Round 1 remediation commits applied: 17f046a, 7744016, 951a606.

Mandate: be hostile. For each Round 1 finding:
1. Verify the fix was applied correctly to the current code.
2. Verify the fix did not introduce a new issue.

Then independently audit the current code for:
- New scientific claims added since 2026-04-12 that might be unjustified
- Citations that lack §13 entry in the whitepaper
- Cross-module inconsistencies introduced by remediation

Output a categorized table with severity (INCORRECT / UNJUSTIFIED / INCONSISTENT / MISSING / VERIFIED) and a verdict line: CONVERGED or NOT CONVERGED — N findings.

Be ruthless. Every finding will be addressed.
```

### CP-4: Convergence loop

Apply fixes via fix-implementer subagent (Opus or Sonnet depending on judgment vs mechanical). Re-dispatch CP-3 audit. Repeat until verdict CONVERGED. Demography precedent: 2-4 rounds typical.

### CP-5: Whitepaper promotion §8 → §4.x

For each converged module:

1. Open `docs/whitepaper/epocha-whitepaper.md`. Find the §8.x entry for the module/cluster. Remove or rewrite it (a converged module no longer belongs in §8).
2. Add a new §4.x sub-section in chapter 4 Methods. Use the canonical schema:
   - Background (1 paragraph): why the model, alternatives considered
   - Model (1 paragraph + numbered equation if applicable)
   - Equations (numbered following the existing 4.1-4.15 sequence)
   - Parameters (table per era if applicable)
   - Algorithm (per-tick or per-event procedure with file:line references)
   - Simplifications (deliberate trade-offs documented)
   - Status header: `> Status: implemented as of commit <filled-on-merge>, code audit CONVERGED <date> round 2.`
3. Update §6 Calibration parameter tables if new parameters added.
4. Update §7 Validation Methodology if new validation targets identified.
5. Update §13 References with any new citations introduced.
6. Update §3.x or §5 if implementation/architecture details changed.

### CP-6: Whitepaper IT mirror

Apply the same edits to `docs/whitepaper/epocha-whitepaper.it.md`. Translate per the established style. Equation numbering identical. §13 References block kept verbatim from EN (already mirrored).

### CP-7: README status table update EN+IT

In `README.md` and `README.it.md`, find the "Status" table. Update the row for the promoted module(s):
- Audited column: change "Round 1 audit + remediation, Round 2 pending" → "yes (CONVERGED YYYY-MM-DD round 2)"

### CP-8: Doc-sync memory update

Edit `docs/memory-backup/feedback_whitepaper_doc_sync.md`. Add a new row to the mapping table:

```
| `epocha/apps/<path>` | §4.x (EN) | §4.x (IT) |
```

Then also copy the updated file to `~/.claude/projects/.../memory/feedback_whitepaper_doc_sync.md` to keep live and backup in sync.

### CP-9: Pytest gate

```bash
docker compose -f docker-compose.local.yml ps
docker compose -f docker-compose.local.yml up -d   # if needed
docker compose -f docker-compose.local.yml exec -T web pytest --tb=short 2>&1 | tail -20
```

Expected: 800 passed (or current baseline), 0 failed.

### CP-10: Branch closure (PR + merge + frozen-at-commit pin)

```bash
git push -u origin BRANCH_NAME
\gh pr create --draft --base develop --head BRANCH_NAME --title "TITLE" --body "BODY"
\gh pr ready PR_NUMBER
\gh pr merge PR_NUMBER --merge --delete-branch
git checkout develop && git pull --ff-only origin develop
```

Then sed-replace the new `<filled-on-merge>` placeholders introduced by the promoted §4.x status headers with the actual merge SHA. Commit `docs: pin whitepaper frozen-at-commit for <module> promotion`. Push.

---

## Branch 1 — Reputation re-audit and promotion

**Modules**: `epocha/apps/agents/reputation.py`
**Original findings**: 4 (1 INCORRECT, 2 UNJUSTIFIED, 1 MISSING)
**Whitepaper §8 entry**: §8.5 Reputation (Castelfranchi-Conte-Paolucci 1998) — to be removed and re-emerge as §4.3 (or similar position after Demography and Economy Behavioral)

### Task 1.1: Create branch

- [ ] **Step 1: Branch off develop**

```bash
git checkout develop && git pull --ff-only origin develop
git checkout -b audit-repass/reputation
git status
```

Expected: clean tree on `audit-repass/reputation`.

### Task 1.2: Extract Round 1 findings for reputation

- [ ] **Step 1: Run CP-1 with `modules_of_interest=['reputation']`**

Save the output as `audit-repass-status-reputation.md` in branch root with the following structure:

```
# Reputation — Round 1 findings status matrix

Source: docs/scientific-audit-2026-04-12.md
Round 1 remediation: 17f046a (touched reputation.py)

| ID | Original severity | Original finding | Round 1 fix? | Current status |
|----|-------------------|------------------|--------------|----------------|
| R-1 | UNJUSTIFIED | Image delta magnitudes (help=0.15, betray=-0.80) attributed to Baumeister 2001 ratios that don't exist | TBD verify | TBD |
| R-2 | INCORRECT | 0.6/0.4 image/reputation weights attributed to Castelfranchi 1998 with no source basis | TBD verify | TBD |
| R-3 | UNJUSTIFIED | 0.5 dampening factor in update_reputation undocumented | TBD verify | TBD |
| R-4 | MISSING | No temporal decay of image or reputation | TBD verify | TBD |
| R-V1 | VERIFIED | image/reputation distinction correctly separate fields | n/a | n/a |
```

### Task 1.3: Verify Round 1 remediation per CP-2

- [ ] **Step 1: Read `epocha/apps/agents/reputation.py` end to end**
- [ ] **Step 2: For R-1**: search for the docstring or comment that justifies `help=0.15`, `betray=-0.80`, `argue=-0.20`. Confirm the docstring now correctly labels these as "tunable parameters inspired by the negativity-bias principle" rather than claiming Baumeister 2001 ratios.
- [ ] **Step 3: For R-2**: search for `image * 0.6 + reputation * 0.4` weighting in `get_combined_score`. Confirm the attribution is now "design choice" not "Castelfranchi 1998".
- [ ] **Step 4: For R-3**: search for `0.5` dampening in `update_reputation`. Confirm it is documented as design rationale.
- [ ] **Step 5: For R-4**: confirm temporal decay is either implemented or explicitly documented as a known simplification.
- [ ] **Step 6: Update `audit-repass-status-reputation.md`** with CLOSED/PARTIAL/NOT_FIXED/REGRESSED per finding.

### Task 1.4: Dispatch Round 2 audit per CP-3

- [ ] **Step 1: Build the audit prompt with**:
  - `MODULE_LIST = ['reputation']`
  - `BRANCH_NAME = audit-repass/reputation`
  - Files: `epocha/apps/agents/reputation.py`, `epocha/apps/agents/models.py` (for ReputationScore model)
  - Findings extracted in Task 1.2 with Round 1 status from Task 1.3

- [ ] **Step 2: Dispatch via Agent tool** with `subagent_type=critical-analyzer`, `model=opus`
- [ ] **Step 3: Receive verdict**: CONVERGED → skip to Task 1.6. NOT CONVERGED → Task 1.5.

### Task 1.5: Convergence loop per CP-4

- [ ] **Step 1: For each Round 2 finding**, dispatch fix-implementer (Sonnet for mechanical, Opus for scientific judgment) with finding details.
- [ ] **Step 2: Apply each fix in a separate commit** with message `fix(science): close reputation audit finding R-N <description>`.
- [ ] **Step 3: Re-dispatch CP-3 audit** after fixes applied.
- [ ] **Step 4: Loop** until CONVERGED. Expect 2-3 rounds.

### Task 1.6: Promote reputation §8.5 → §4.3 in whitepaper EN per CP-5

- [ ] **Step 1: Read existing §8.5** to identify the paragraph + status header to remove.
- [ ] **Step 2: Read existing §4.1 and §4.2** structure to mirror the canonical schema for §4.3.
- [ ] **Step 3: Write the new §4.3 Reputation section** with:
  - Status header: `> Status: implemented as of commit <filled-on-merge>, code audit CONVERGED <today's date> round 2.`
  - Background: image vs reputation distinction per Castelfranchi-Conte-Paolucci 1998, why this conceptual model
  - Model: image score (direct experience) and reputation score (transmitted), normalized to [-1, 1]
  - Equations: combined score (e.g. equation 4.16) with tunable weights, image update equation, reputation update equation
  - Parameters table: image deltas per action type (with tunable status), dampening factor, combined-score weights
  - Algorithm: when an action is observed, image is updated; when reputation propagates via information_flow, reputation is updated with dampening.
  - Simplifications: no temporal decay (documented), no contextual reputation (one global score per agent pair), no role-specific reputation
- [ ] **Step 4: Remove §8.5 entry**.
- [ ] **Step 5: Renumber §8.6, §8.7** if needed (Knowledge Graph and Economy base).
- [ ] **Step 6: Update §13 References** if any new citations introduced (probably none, Castelfranchi 1998 already in §13).
- [ ] **Step 7: Verify with grep**: `<draft in Task` does not appear in §4.3.

### Task 1.7: Mirror §4.3 in IT whitepaper per CP-6

- [ ] **Step 1: Translate §4.3 EN to IT** at the corresponding position in `epocha-whitepaper.it.md`.
- [ ] **Step 2: Remove §8.5 from IT** at the same time.
- [ ] **Step 3: Renumber §8.6, §8.7** in IT.

### Task 1.8: Update README EN+IT status tables per CP-7

- [ ] **Step 1: In `README.md`** find "Reputation" row in Status table; change audit column.
- [ ] **Step 2: In `README.it.md`** mirror.

### Task 1.9: Update doc-sync memory per CP-8

- [ ] **Step 1: Edit `docs/memory-backup/feedback_whitepaper_doc_sync.md`**: add row `| epocha/apps/agents/reputation.py | §4.3 (EN) | §4.3 (IT) |`
- [ ] **Step 2: Copy to live memory** at `~/.claude/projects/-Users-mauriziomocci-Documents-workspace-Opensource-epocha/memory/feedback_whitepaper_doc_sync.md`

### Task 1.10: Delete the working status matrix file

- [ ] **Step 1: `rm audit-repass-status-reputation.md`** (working note, not for merge)
- [ ] **Step 2: Verify with `git status`** that no .md residue remains in branch root

### Task 1.11: Pytest gate per CP-9

- [ ] **Step 1: Run pytest** as documented. Expected 800/0.

### Task 1.12: Branch closure per CP-10

- [ ] **Step 1: Push branch** `git push -u origin audit-repass/reputation`
- [ ] **Step 2: Create draft PR** with summary listing R-1..R-4 resolution + Round 2 audit verdict + promotion to §4.3
- [ ] **Step 3: Mark ready, merge --merge --delete-branch**
- [ ] **Step 4: Pull develop, replace `<filled-on-merge>` with merge SHA, commit `docs: pin whitepaper frozen-at-commit for reputation promotion`, push develop**

---

## Branch 2 — Rumor cluster re-audit and promotion

**Modules**: `epocha/apps/agents/{information_flow,distortion,belief,affinity}.py`
**Original findings**: 17 (5+5+4+3)
**Whitepaper §8 entry**: §8.1 Rumor cluster — to be removed and re-emerge as §4.4 (4-sub-section chapter)
**Special note**: affinity is NOT currently in §8 — first add an §8 entry for it as part of Branch 1's §8 reorg, OR include it directly in §4.4 as part of the rumor cluster promotion. Recommended: include directly in §4.4 (cleaner, no transitional §8 entry).

### Task 2.1: Create branch

- [ ] **Step 1: Branch off develop**

```bash
git checkout develop && git pull --ff-only origin develop
git checkout -b audit-repass/rumor-cluster
```

### Task 2.2-2.5: Same structure as Tasks 1.2-1.5 with `MODULE_LIST = ['information_flow', 'distortion', 'belief', 'affinity']`

For verification per CP-2 the implementer must check Round 1 remediation in `17f046a` (distortion) + `7744016` (belief) + `951a606` (information_flow, affinity) for each finding.

### Task 2.6: Promote rumor cluster §8.1 → §4.4 in whitepaper EN per CP-5

- [ ] **Step 1: Write §4.4 Rumor propagation** as a chapter with 4 sub-sections:
  - §4.4.1 Information flow (Bartlett 1932 serial reproduction + Granovetter 1973 weak ties — confirm Granovetter is now actually wired into propagation probability per the original audit's R-INC1 finding)
  - §4.4.2 Distortion (Allport-Postman 1947 levelling/sharpening/assimilation, Bartlett 1932)
  - §4.4.3 Belief filter (personality-weighted acceptance per McCrae-Costa 1987)
  - §4.4.4 Affinity (relationship-strength scoring)
- [ ] **Step 2: Each sub-section** uses the canonical schema (Background, Model, Equations, Parameters, Algorithm, Simplifications, Status header).
- [ ] **Step 3: Remove §8.1**.

### Task 2.7-2.12: Same structure as Tasks 1.7-1.12

---

## Branch 3 — Political cluster re-audit and promotion

**Modules**: `epocha/apps/world/{government,government_types,institutions,stratification,election}.py`
**Original findings**: 22 (6+1+6+4+5)
**Whitepaper §8 entry**: §8.2 Political institutions — to be removed and re-emerge as §4.5 (5-sub-section chapter)
**Special note**: election is NOT currently in §8 — include directly in §4.5 (same approach as affinity in §4.4).

### Task 3.1: Create branch

```bash
git checkout develop && git pull --ff-only origin develop
git checkout -b audit-repass/political-cluster
```

### Task 3.2-3.5: Same structure with `MODULE_LIST = ['government', 'government_types', 'institutions', 'stratification', 'election']`

Round 1 commits to verify: `7744016` (government, government_types, institutions, stratification) + `951a606` (election, government addendum, stratification addendum).

### Task 3.6: Promote political cluster §8.2 → §4.5 in whitepaper EN

- [ ] **Step 1: Write §4.5 Political institutions** as chapter with 5 sub-sections:
  - §4.5.1 Government types (Acemoglu-Robinson 2006, Polity 5 dataset)
  - §4.5.2 Coup dynamics (Powell-Thyne 2011, with stochastic correction per audit C-INC2)
  - §4.5.3 Institutions (the 6 findings cleared)
  - §4.5.4 Stratification (Alesina-Perotti 1996, Gini scope corrected per audit S-INC2)
  - §4.5.5 Elections (voting model corrected per audit E-INC1)
- [ ] **Step 2: Each sub-section** canonical schema.
- [ ] **Step 3: Remove §8.2**.

### Task 3.7-3.12: Same structure as Tasks 1.7-1.12

---

## Branch 4 — Movement re-audit and promotion

**Modules**: `epocha/apps/agents/movement.py`
**Original findings**: 5 (2 INCORRECT, 2 UNJUSTIFIED, 1 INCONSISTENT)
**Whitepaper §8 entry**: §8.3 Movement → promote to §4.6

### Task 4.1: Create branch

```bash
git checkout develop && git pull --ff-only origin develop
git checkout -b audit-repass/movement
```

### Task 4.2-4.5: Same with `MODULE_LIST = ['movement']`

Round 1 commit: `17f046a` (movement).

### Task 4.6: Promote §8.3 → §4.6 Movement system

Canonical schema with Chandler / Braudel attributions verified.

### Task 4.7-4.12: Same structure

---

## Branch 5 — Factions re-audit and promotion

**Modules**: `epocha/apps/agents/factions.py`
**Original findings**: 4 (2 INCORRECT, 1 UNJUSTIFIED, 1 MISSING)
**Whitepaper §8 entry**: §8.4 Factions → promote to §4.7

### Task 5.1: Create branch

```bash
git checkout develop && git pull --ff-only origin develop
git checkout -b audit-repass/factions
```

### Task 5.2-5.5: Same with `MODULE_LIST = ['factions']`

Round 1 commit: `951a606` (factions).

### Task 5.6: Promote §8.4 → §4.7 Factions

Canonical schema with collective action attribution corrected.

### Task 5.7-5.12: Same structure

---

## Branch 6 — Deprecate world/economy.py legacy placeholder

**Module**: `epocha/apps/world/economy.py`
**Original findings**: 4 — but this module is **superseded** by `epocha/apps/economy/*` which is already CONVERGED 2026-04-15 and audited as §4.2 of the whitepaper. The right action is deprecation, not re-audit.

### Task 6.1: Create branch

```bash
git checkout develop && git pull --ff-only origin develop
git checkout -b audit-repass/world-economy-deprecation
```

### Task 6.2: Verify world/economy.py is genuinely unused

- [ ] **Step 1: Grep for any callers** outside `world/economy.py` itself:

```bash
grep -rn "from epocha.apps.world.economy\|from epocha.apps.world import economy\|world\.economy" --include="*.py" epocha/ | grep -v "world/economy.py"
```

- [ ] **Step 2: If unused**: proceed with full removal (Task 6.3 path A).
- [ ] **Step 3: If used by callers**: proceed with deprecation marker (Task 6.3 path B). Document each caller.

### Task 6.3 path A: Remove the file

- [ ] **Step 1: `git rm epocha/apps/world/economy.py`**
- [ ] **Step 2: Update any test files** that import from it (probably none).
- [ ] **Step 3: Pytest gate**: ensure no regression.

### Task 6.3 path B: Add deprecation marker

- [ ] **Step 1: Prepend file** with deprecation block:

```python
"""
DEPRECATED: This module is the legacy MVP economy placeholder.

Superseded by `epocha.apps.economy.*` (audited CONVERGED 2026-04-15,
documented in the whitepaper §4.2 Economy Behavioral integration).

Do not extend. Existing callers should be migrated to the new economy
package and this file removed in a follow-up.
"""

import warnings
warnings.warn(
    "epocha.apps.world.economy is deprecated, use epocha.apps.economy.* instead",
    DeprecationWarning,
    stacklevel=2,
)
```

- [ ] **Step 2: List callers** in a comment block above the warning.

### Task 6.4: Update whitepaper §8.7 entry

- [ ] **Step 1: §8.7 Economy base layer** currently describes `epocha/apps/economy/*` (the new audited base) NOT the legacy `world/economy.py`. Verify this distinction in current §8.7.
- [ ] **Step 2: If §8.7 mentions `world/economy.py`**: remove that mention. The world/economy.py module is now legacy and not in the documented architecture.
- [ ] **Step 3: Mirror in §8.7 IT**.

### Task 6.5: Update memory: mark audit re-pass batch as DONE

- [ ] **Step 1: Edit `docs/memory-backup/project_audit_repass_batch_2026_04_12_pending.md`** — change description to "DONE" with completion date.
- [ ] **Step 2: Edit `MEMORY.md`** index entry to reflect DONE status.
- [ ] **Step 3: Copy to live memory**.

### Task 6.6-6.12: Same structure as Tasks 1.7-1.12

---

## Closure: Campaign retrospective

After Branch 6 merges, write a brief retrospective note in `docs/memory-backup/`:

- File: `project_audit_repass_2026_04_12_completed.md`
- Content: total rounds per branch, total findings closed, total tests passing, time elapsed, lessons learned (in particular: any findings that the original 2026-04-12 audit MISSED that this Round 2 caught — those are the most valuable insights for the next batch audit).
- Memory cleanup: rename `project_audit_repass_batch_2026_04_12_pending.md` → mark as superseded.

Also update the whitepaper §9 Roadmap: remove "Re-audit pass on 2026-04-12 batch" from the high-priority list. Promote "Demography Plan 3" to top.

---

## Self-review

After writing this plan, performed inline self-review:

**Spec coverage**: this plan IS the spec equivalent (no separate spec file). The original audit findings in `docs/scientific-audit-2026-04-12.md` are the requirements. Coverage: all 13 audited modules accounted for across 6 branches.

**Placeholder scan**: zero `TBD/TODO/implement later/fill in details` patterns in the plan body. The "TBD verify" entries in the status matrix template (Task 1.2) are intentional — they are columns to be filled by the implementer at runtime.

**Type consistency**: section numbers (§4.3, §4.4, §4.5, §4.6, §4.7) follow the existing §4.1 (Demography), §4.2 (Economy Behavioral) sequence. §8 entries (§8.1-§8.5) are removed in order; §8.6 (Knowledge Graph) and §8.7 (Economy base layer) are renumbered as needed at each promotion.

**Spec gaps**: none identified.

**Estimated effort**: 6 branches × 2-4 audit rounds × per-finding fix work. At established Demography pacing (Round 1+remediation in 1 day, audit dispatch + fix loop in 1-2 sessions per round), estimate 2-4 working sessions per branch. Total: 12-24 sessions for the campaign. Branches 1, 4, 5, 6 are smaller and faster; branches 2 and 3 are the heaviest.

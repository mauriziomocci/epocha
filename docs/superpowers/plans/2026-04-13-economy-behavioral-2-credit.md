# Economy Behavioral Plan — Part 2: Credit System

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the complete credit system: loan creation with credit rationing, interest servicing, rollover (Minsky speculative stage), default with collateral seizure and cascade, banking fractional reserve mechanics, and interest rate determination via credit market equilibrium. After this plan, agents can borrow, lend, default, and the Minsky cycle (hedge → speculative → Ponzi → crisis) emerges from the interaction of debt, refinancing, and economic conditions.

**Architecture:** Two new modules: `credit.py` (loan lifecycle, Minsky classification, default cascade) and `banking.py` (fractional reserve, interest rate, solvency). Integrated into the tick pipeline as steps 5-6 (after property market, before rent).

**Tech Stack:** Django ORM.

**Spec:** `docs/superpowers/specs/2026-04-13-economy-behavioral-design.md` (Debt and Credit System section)

**Depends on:** Part 1 completed (Loan, BankingState models exist, templates have credit_config).

---

## File Structure (Part 2 scope)

| File | Responsibility | New/Modify |
|------|---------------|------------|
| `epocha/apps/economy/credit.py` | Loan lifecycle, rollover, default, cascade, Minsky classification | New |
| `epocha/apps/economy/banking.py` | Fractional reserve, interest rate adjustment, solvency | New |
| `epocha/apps/economy/engine.py` | Add credit + banking steps to tick pipeline | Modify |
| `epocha/apps/economy/tests/test_credit.py` | Credit system tests | New |
| `epocha/apps/economy/tests/test_banking.py` | Banking tests | New |

---

## Tasks summary

4. **Credit engine** — loan creation, interest, rollover, default, cascade, Minsky classification
5. **Banking engine** — fractional reserve, interest rate determination, solvency check
6. **Pipeline integration** — wire credit + banking into tick engine

---

### Task 4: Credit engine

**Files:**
- Create: `epocha/apps/economy/credit.py`
- Create: `epocha/apps/economy/tests/test_credit.py`

The credit engine handles the full loan lifecycle each tick: evaluate credit requests, issue loans, collect interest, handle maturity (repay or rollover), process defaults with collateral seizure, and propagate cascades.

### Task 5: Banking engine

**Files:**
- Create: `epocha/apps/economy/banking.py`
- Create: `epocha/apps/economy/tests/test_banking.py`

The banking engine manages the aggregate banking system: tracks deposits/loans, computes the actual money multiplier, adjusts the base interest rate via credit market equilibrium (Wicksell 1898), and monitors solvency.

### Task 6: Pipeline integration

**Files:**
- Modify: `epocha/apps/economy/engine.py`

Wire credit and banking into the tick pipeline between market clearing and rent distribution.

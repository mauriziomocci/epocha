# Economy Base Implementation Plan — Part 3: Integration

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire the economy engine into the simulation: initialize economy from templates at world generation, replace the old economy tick in the simulation engine, inject economic context into agent decision prompts, add the `hoard` action, and connect economic indicators to the political system. After this plan, new simulations run with a real economy producing emergent dynamics.

**Architecture:** Modifications to existing modules (world/generator.py, simulation/engine.py, agents/decision.py) plus a new initialization module in the economy app. The old world/economy.py is deprecated but kept for backward compatibility with existing simulations.

**Tech Stack:** Django ORM, existing LLM adapter, existing Celery tasks.

**Spec:** `docs/superpowers/specs/2026-04-12-economy-base-design.md` (Initialization, Economic Context, Feedback sections)

**Depends on:** Part 1 (Data Layer) + Part 2 (Engine) — both completed. 524 tests pass.

---

## File Structure (Part 3 scope)

| File | Responsibility | New/Modify |
|------|---------------|------------|
| `epocha/apps/economy/initialization.py` | Initialize economy from template at world generation | New |
| `epocha/apps/economy/context.py` | Build economic context string for decision prompts | New |
| `epocha/apps/economy/political_feedback.py` | Economic indicators → political system | New |
| `epocha/apps/world/generator.py` | Call initialize_economy after world creation | Modify |
| `epocha/apps/simulation/engine.py` | Switch to new economy engine | Modify |
| `epocha/apps/agents/decision.py` | Add economic_context + hoard action | Modify |
| `epocha/apps/dashboard/formatters.py` | Add hoard verb | Modify |
| `epocha/apps/economy/tests/test_initialization.py` | Tests | New |
| `epocha/apps/economy/tests/test_context.py` | Tests | New |
| `epocha/apps/economy/tests/test_political_feedback.py` | Tests | New |
| `epocha/apps/economy/tests/test_integration.py` | End-to-end test | New |

---

## Tasks summary (Part 3 scope)

11. **Economy initialization** — initialize_economy function called by world generator
12. **Economic context for decisions + hoard action** — context builder + decision prompt update
13. **Political feedback + engine switch** — economic indicators to government + simulation engine integration
14. **End-to-end integration test** — full simulation tick with new economy

---

### Task 11: Economy initialization

**Files:**
- Create: `epocha/apps/economy/initialization.py`
- Modify: `epocha/apps/world/generator.py`
- Create: `epocha/apps/economy/tests/test_initialization.py`

The initialization function reads a template and creates all economic entities for a new simulation: currencies, goods, factors, zone economies, agent inventories, properties, tax policy. Called by the world generator after creating World, Zones, and Agents.

### Task 12: Economic context for decisions + hoard action

**Files:**
- Create: `epocha/apps/economy/context.py`
- Modify: `epocha/apps/agents/decision.py`
- Modify: `epocha/apps/dashboard/formatters.py`
- Create: `epocha/apps/economy/tests/test_context.py`

The context builder produces a formatted string showing the agent's economic situation (cash, inventory, properties, income, market prices) for the LLM decision prompt. The `hoard` action is added to the decision vocabulary — an agent choosing hoard does not offer goods to the market, reducing supply.

### Task 13: Political feedback + engine switch

**Files:**
- Create: `epocha/apps/economy/political_feedback.py`
- Modify: `epocha/apps/simulation/engine.py`
- Create: `epocha/apps/economy/tests/test_political_feedback.py`

Economic indicators (inflation, Gini, unemployment, treasury) feed into government stability and legitimacy. The simulation engine switches from old economy to new economy for simulations that have economy data initialized.

### Task 14: End-to-end integration test

**Files:**
- Create: `epocha/apps/economy/tests/test_integration.py`

Full simulation tick with new economy: create simulation with template, initialize economy, run 3 ticks, verify prices change, agents trade, taxes collected, political indicators updated.

# Decision Quality Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix three simulation quality issues: agents hallucinating non-existent targets, duplicate memories saturating context, and raw JSON in the activity feed.

**Architecture:** All three fixes are isolated changes in different files. Fix 1 adds living agent names to the LLM decision context. Fix 2 adds a dedup check before memory creation. Fix 3 parses `output_decision` JSON into readable text in the dashboard views.

**Tech Stack:** Django ORM, pytest, JSON parsing

---

### Task 1: Pass living agent names into decision context

Agents currently invent targets that do not exist because the LLM has no list of valid agents. The fix queries living agents from the same simulation (excluding self) and adds their names and roles to the context prompt, with an explicit constraint.

**Files:**
- Modify: `epocha/apps/agents/decision.py:37-67` (`_build_context` signature and body)
- Modify: `epocha/apps/agents/decision.py:70-98` (`process_agent_decision` to query agents and pass them)
- Test: `epocha/apps/agents/tests/test_decision.py`

- [ ] **Step 1: Write the failing test**

Add to `epocha/apps/agents/tests/test_decision.py`:

```python
@patch("epocha.apps.agents.decision.get_llm_client")
def test_context_includes_living_agents_list(self, mock_get_client, agent, world, simulation):
    """The LLM prompt must list living agents so the agent only targets real people."""
    Agent.objects.create(
        simulation=simulation, name="Elena", role="farmer",
        personality={"openness": 0.5},
    )
    Agent.objects.create(
        simulation=simulation, name="Ghost", role="priest",
        personality={"openness": 0.5}, is_alive=False,
    )
    mock_client = MagicMock()
    mock_client.complete.return_value = '{"action": "socialize", "target": "Elena"}'
    mock_client.get_model_name.return_value = "gpt-4o-mini"
    mock_get_client.return_value = mock_client

    process_agent_decision(agent, world, tick=1)

    call_args = mock_client.complete.call_args
    prompt = call_args.kwargs.get("prompt", call_args.args[0] if call_args.args else "")
    # Living agent Elena must appear in the prompt
    assert "Elena" in prompt
    assert "farmer" in prompt
    # Dead agent Ghost must NOT appear
    assert "Ghost" not in prompt
    # The agent itself must NOT appear in its own list
    assert prompt.count("Marco") == 1  # Only the "You are Marco" line
    # Must include constraint
    assert "ONLY" in prompt
```

The test needs the `simulation` fixture. It already exists in the file but is not a parameter of `TestProcessAgentDecision` methods. Update the `agent` fixture to take `simulation` as a parameter and add `simulation` as a method parameter via the existing fixture.

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest epocha/apps/agents/tests/test_decision.py::TestProcessAgentDecision::test_context_includes_living_agents_list -v`
Expected: FAIL because the prompt does not contain "Elena" or "ONLY".

- [ ] **Step 3: Implement the fix**

In `epocha/apps/agents/decision.py`, update `_build_context` to accept a `living_agents` parameter:

```python
def _build_context(agent, world_state, tick: int, memories, relationships, recent_events=None, living_agents=None) -> str:
    """Assemble the situational context string sent as the LLM user prompt."""
    parts = [
        f"You are {agent.name}, a {agent.role}.",
        f"Tick: {tick}. Health: {agent.health:.1f}, wealth: {agent.wealth:.1f}, mood: {agent.mood:.1f}.",
        f"World stability: {world_state.stability_index:.1f}.",
    ]

    # List of living agents the agent can interact with
    if living_agents:
        parts.append("\nOther people in your world:")
        for a in living_agents:
            parts.append(f"- {a.name} ({a.role})")
        parts.append("You can ONLY interact with people listed above. Do not invent names.")

    # Injected events that the agent should react to
    if recent_events:
        parts.append("\nIMPORTANT - Recent events that happened in your world:")
        for event in recent_events:
            parts.append(f"- {event.title}: {event.description}")
        parts.append("React to these events based on your personality and situation.")

    if memories:
        parts.append("\nYour recent memories:")
        for m in memories:
            source_label = f" ({m.source_type})" if m.source_type != "direct" else ""
            parts.append(f"- {m.content}{source_label}")

    if relationships:
        parts.append("\nYour relationships:")
        for rel in relationships:
            sentiment_word = "positively" if rel.sentiment > 0 else "negatively"
            parts.append(
                f"- {rel.agent_to.name} ({rel.relation_type}, "
                f"you feel {sentiment_word}, strength: {rel.strength:.1f})"
            )

    return "\n".join(parts)
```

In `process_agent_decision`, query living agents (excluding self) and pass them:

```python
# After the relationships query, before building context:
living_agents = list(
    Agent.objects.filter(simulation=agent.simulation, is_alive=True)
    .exclude(id=agent.id)
    .only("name", "role")[:20]
)
context = _build_context(agent, world_state, tick, memories, relationships, recent_events, living_agents)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest epocha/apps/agents/tests/test_decision.py -v`
Expected: All tests PASS.

- [ ] **Step 5: Commit**

```
feat(agents): include living agent names in decision context

CHANGE: Pass a list of living agents (name, role) into the LLM decision
prompt so agents only target real characters. Prevents hallucination of
non-existent targets.
```

---

### Task 2: Prevent duplicate memories in consecutive ticks

The engine creates a memory every tick via `Memory.objects.create()` in `apply_agent_action`. When an agent repeats the same action across ticks, this produces dozens of identical "I decided to argue" memories that saturate context. The fix checks whether the agent already has an active memory with the same action type within the last N ticks before creating a new one.

**Files:**
- Modify: `epocha/apps/simulation/engine.py:61-96` (`apply_agent_action`)
- Test: `epocha/apps/simulation/tests/test_engine.py`

- [ ] **Step 1: Write the failing test**

Add to `epocha/apps/simulation/tests/test_engine.py`:

```python
@patch("epocha.apps.simulation.engine.process_agent_decision")
def test_no_duplicate_memories_for_same_action(self, mock_decision, sim_with_world):
    """Repeating the same action in consecutive ticks should not create duplicate memories."""
    mock_decision.return_value = {"action": "argue", "reason": "angry at priest"}

    engine = SimulationEngine(sim_with_world)
    engine.run_tick()  # tick 1 - creates memory
    engine.run_tick()  # tick 2 - same action, should skip memory
    engine.run_tick()  # tick 3 - same action, should skip memory

    marco = Agent.objects.get(name="Marco")
    argue_memories = Memory.objects.filter(agent=marco, content__startswith="I decided to argue")
    assert argue_memories.count() == 1

@patch("epocha.apps.simulation.engine.process_agent_decision")
def test_different_actions_create_separate_memories(self, mock_decision, sim_with_world):
    """Different actions in consecutive ticks should each create a memory."""
    mock_decision.side_effect = [
        {"action": "argue", "reason": "angry"},
        {"action": "rest", "reason": "tired"},
        {"action": "argue", "reason": "still angry"},
    ]

    engine = SimulationEngine(sim_with_world)
    engine.run_tick()  # tick 1 - argue
    engine.run_tick()  # tick 2 - rest (different action)
    engine.run_tick()  # tick 3 - argue again (different from previous tick)

    marco = Agent.objects.get(name="Marco")
    assert Memory.objects.filter(agent=marco).count() == 3
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest epocha/apps/simulation/tests/test_engine.py::TestSimulationEngine::test_no_duplicate_memories_for_same_action -v`
Expected: FAIL because 3 memories are created instead of 1.

- [ ] **Step 3: Implement the fix**

In `epocha/apps/simulation/engine.py`, modify `apply_agent_action`:

```python
# Number of recent ticks to check for duplicate memories.
# If the agent performed the same action within this window, skip memory creation.
_MEMORY_DEDUP_TICKS = 3


def apply_agent_action(agent: Agent, action: dict, tick: int) -> None:
    """Apply consequences of an agent's action and create a memory.

    Extracted as a standalone function so it can be called from both
    the SimulationEngine and the process_agent_turn Celery task.

    Memory deduplication: if the agent already has an active memory for
    the same action type within the last _MEMORY_DEDUP_TICKS ticks,
    skip creation to prevent context saturation from repetitive behavior.

    Args:
        agent: The agent performing the action.
        action: Dict with at least "action" key (e.g. "work", "rest", "argue")
            and optionally "reason".
        tick: Current simulation tick number.
    """
    action_type = action.get("action", "rest")

    # Mood adjustment
    mood_delta = _ACTION_MOOD_DELTA.get(action_type, 0.0)
    agent.mood = max(0.0, min(1.0, agent.mood + mood_delta))

    # Rest restores a small amount of health
    if action_type == "rest":
        agent.health = min(1.0, agent.health + 0.02)

    agent.save(update_fields=["mood", "health"])

    # Create memory of the action (skip if duplicate within recent ticks)
    dedup_prefix = f"I decided to {action_type}."
    recent_duplicate = Memory.objects.filter(
        agent=agent,
        is_active=True,
        content__startswith=dedup_prefix,
        tick_created__gte=max(0, tick - _MEMORY_DEDUP_TICKS),
    ).exists()

    if not recent_duplicate:
        emotional_weight = _ACTION_EMOTIONAL_WEIGHT.get(
            action_type, _DEFAULT_EMOTIONAL_WEIGHT
        )
        reason = action.get("reason", "")
        Memory.objects.create(
            agent=agent,
            content=f"I decided to {action_type}. {reason}".strip(),
            emotional_weight=emotional_weight,
            source_type="direct",
            tick_created=tick,
        )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest epocha/apps/simulation/tests/test_engine.py -v`
Expected: All tests PASS.

- [ ] **Step 5: Commit**

```
fix(simulation): prevent duplicate memories for repeated actions

CHANGE: Before creating a memory in apply_agent_action, check whether
the agent already has an active memory for the same action type within
the last 3 ticks. Prevents context saturation from 40+ identical
"I decided to argue" memories during tick loops.
```

---

### Task 3: Format activity feed decisions as readable text

The activity feed shows raw JSON like `{"action": "argue", "target": "Elena"}`. The fix adds a `format_decision_text` utility that parses the JSON and produces readable text like "argues with Elena: she disrespected me". Applied in both the initial page load and the polling endpoint.

**Files:**
- Create: `epocha/apps/dashboard/formatters.py`
- Modify: `epocha/apps/dashboard/views.py:188-189` (polling endpoint)
- Modify: `epocha/apps/dashboard/views.py:228-229` (initial page load)
- Test: `epocha/apps/dashboard/tests/__init__.py` (create empty)
- Test: `epocha/apps/dashboard/tests/test_formatters.py`

- [ ] **Step 1: Write the failing test**

Create `epocha/apps/dashboard/tests/__init__.py` (empty file) and `epocha/apps/dashboard/tests/test_formatters.py`:

```python
"""Tests for dashboard decision formatting."""
import pytest

from epocha.apps.dashboard.formatters import format_decision_text


class TestFormatDecisionText:
    def test_action_with_target_and_reason(self):
        raw = '{"action": "argue", "target": "Elena", "reason": "she disrespected me"}'
        result = format_decision_text(raw)
        assert result == "argues with Elena: she disrespected me"

    def test_action_with_reason_only(self):
        raw = '{"action": "work", "reason": "need money"}'
        result = format_decision_text(raw)
        assert result == "works: need money"

    def test_action_only(self):
        raw = '{"action": "rest"}'
        result = format_decision_text(raw)
        assert result == "rests"

    def test_invalid_json_returns_truncated_raw(self):
        raw = "I think I should rest for a while and maybe explore."
        result = format_decision_text(raw)
        assert result == raw[:100]

    def test_empty_target_ignored(self):
        raw = '{"action": "explore", "target": "", "reason": "curious"}'
        result = format_decision_text(raw)
        assert result == "explores: curious"

    def test_unknown_action_uses_verb_as_is(self):
        raw = '{"action": "pray", "reason": "seeking guidance"}'
        result = format_decision_text(raw)
        assert result == "prays: seeking guidance"

    def test_truncated_input(self):
        """The view truncates output_decision to 100 chars, which can break JSON."""
        raw = '{"action": "argue", "target": "Elena", "reason": "she disrespected me in fro'
        result = format_decision_text(raw)
        # Should not crash, returns the raw string
        assert result == raw
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest epocha/apps/dashboard/tests/test_formatters.py -v`
Expected: FAIL with ImportError (module does not exist).

- [ ] **Step 3: Implement the formatter**

Create `epocha/apps/dashboard/formatters.py`:

```python
"""Formatting utilities for dashboard display."""
from __future__ import annotations

import json

# Maps action keywords to English third-person verb forms.
# Standard actions come from the decision pipeline; unknown actions
# get a naive "s" suffix as a reasonable default.
_ACTION_VERBS: dict[str, str] = {
    "work": "works",
    "rest": "rests",
    "socialize": "socializes",
    "explore": "explores",
    "trade": "trades",
    "argue": "argues",
    "help": "helps",
    "avoid": "avoids",
    "betray": "betrays",
    "pray": "prays",
}


def format_decision_text(raw_decision: str) -> str:
    """Convert a raw JSON decision string into human-readable narrative text.

    Expected input format: '{"action": "argue", "target": "Elena", "reason": "..."}'
    Output: "argues with Elena: she disrespected me"

    Handles malformed JSON gracefully by returning the raw string (truncated to 100 chars).
    """
    try:
        data = json.loads(raw_decision)
    except (json.JSONDecodeError, TypeError):
        return raw_decision[:100]

    if not isinstance(data, dict) or "action" not in data:
        return raw_decision[:100]

    action = data["action"]
    verb = _ACTION_VERBS.get(action, f"{action}s")
    target = data.get("target", "")
    reason = data.get("reason", "")

    parts = [verb]
    if target:
        parts.append(f"with {target}")
    result = " ".join(parts)
    if reason:
        result = f"{result}: {reason}"
    return result
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest epocha/apps/dashboard/tests/test_formatters.py -v`
Expected: All tests PASS.

- [ ] **Step 5: Integrate into dashboard views**

In `epocha/apps/dashboard/views.py`, add the import and use it in both endpoints.

Add import at top:

```python
from epocha.apps.dashboard.formatters import format_decision_text
```

Change the polling endpoint (line ~189):

```python
"decisions": [
    {"agent": d.agent.name, "tick": d.tick, "decision": format_decision_text(d.output_decision)}
    for d in decisions
],
```

Change the initial page load (line ~229):

```python
decisions_json = json.dumps([
    {"agent": d.agent.name, "tick": d.tick, "decision": format_decision_text(d.output_decision)}
    for d in decisions
])
```

- [ ] **Step 6: Run full test suite**

Run: `pytest epocha/apps/dashboard/tests/ epocha/apps/agents/tests/ epocha/apps/simulation/tests/ -v`
Expected: All tests PASS.

- [ ] **Step 7: Commit**

```
feat(dashboard): format activity feed decisions as readable text

CHANGE: Parse raw JSON decisions into narrative text in the activity feed.
"{"action": "argue", "target": "Elena"}" becomes "argues with Elena".
Applied to both the initial page load and the polling endpoint.
```

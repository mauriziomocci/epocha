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
    "form_group": "forms a group",
    "join_group": "joins a group",
    "crime": "commits a crime against",
    "protest": "protests",
    "campaign": "campaigns for leadership",
    "move_to": "travels to",
    "hoard": "hoards goods",
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
        # "move_to" already has "to" in the verb; other actions use "with"
        preposition = "" if action == "move_to" else "with "
        parts.append(f"{preposition}{target}")
    result = " ".join(parts)
    if reason:
        result = f"{result}: {reason}"
    return result

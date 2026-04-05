"""Tests for dashboard decision formatting."""
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

    def test_unknown_action_gets_naive_s_suffix(self):
        """Actions not in _ACTION_VERBS get a fallback verb form with 's' suffix."""
        raw = '{"action": "dance", "reason": "feeling joyful"}'
        result = format_decision_text(raw)
        assert result == "dances: feeling joyful"

    def test_truncated_input(self):
        """The view truncates output_decision to 100 chars, which can break JSON."""
        raw = '{"action": "argue", "target": "Elena", "reason": "she disrespected me in fro'
        result = format_decision_text(raw)
        # Should not crash, returns the raw string
        assert result == raw

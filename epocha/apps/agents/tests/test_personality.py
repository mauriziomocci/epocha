"""Tests for personality prompt construction from agent traits."""
from epocha.apps.agents.personality import build_personality_prompt


class TestBuildPersonalityPrompt:
    def test_returns_non_empty_string(self):
        """A full personality profile should produce a substantial prompt."""
        traits = {
            "openness": 0.8,
            "conscientiousness": 0.3,
            "extraversion": 0.6,
            "agreeableness": 0.4,
            "neuroticism": 0.7,
            "background": "A blacksmith in a medieval village",
            "ambitions": "Become the village leader",
            "weaknesses": "Quick temper, distrustful of strangers",
            "values": "Hard work, loyalty to family",
        }
        result = build_personality_prompt(traits)
        assert isinstance(result, str)
        assert len(result) > 100

    def test_includes_background(self):
        """The prompt must reference the agent's background story."""
        traits = {
            "openness": 0.5,
            "conscientiousness": 0.5,
            "extraversion": 0.5,
            "agreeableness": 0.5,
            "neuroticism": 0.5,
            "background": "A corrupt priest who steals from donations",
        }
        result = build_personality_prompt(traits)
        assert "corrupt priest" in result.lower() or "priest" in result.lower()

    def test_handles_missing_optional_fields(self):
        """Only Big Five traits are required; other fields are optional."""
        traits = {
            "openness": 0.5,
            "conscientiousness": 0.5,
            "extraversion": 0.5,
            "agreeableness": 0.5,
            "neuroticism": 0.5,
        }
        result = build_personality_prompt(traits)
        assert isinstance(result, str)
        assert len(result) > 50

    def test_high_trait_produces_high_description(self):
        """A trait value >= 0.7 should produce the 'high' description."""
        traits = {"openness": 0.9, "conscientiousness": 0.5, "extraversion": 0.5,
                  "agreeableness": 0.5, "neuroticism": 0.5}
        result = build_personality_prompt(traits)
        assert "curious" in result.lower() or "creative" in result.lower()

    def test_low_trait_produces_low_description(self):
        """A trait value <= 0.3 should produce the 'low' description."""
        traits = {"openness": 0.1, "conscientiousness": 0.5, "extraversion": 0.5,
                  "agreeableness": 0.5, "neuroticism": 0.5}
        result = build_personality_prompt(traits)
        assert "practical" in result.lower() or "conventional" in result.lower()

    def test_character_enforces_consistency(self):
        """The prompt must instruct the LLM to stay in character."""
        traits = {"openness": 0.5, "conscientiousness": 0.5, "extraversion": 0.5,
                  "agreeableness": 0.5, "neuroticism": 0.5}
        result = build_personality_prompt(traits)
        assert "character" in result.lower() or "consistently" in result.lower()

    def test_empty_traits_does_not_crash(self):
        """An empty dict should still produce a valid prompt, using defaults."""
        result = build_personality_prompt({})
        assert isinstance(result, str)
        assert len(result) > 20

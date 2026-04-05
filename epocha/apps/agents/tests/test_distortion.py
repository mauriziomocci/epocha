"""Tests for the rule-based distortion engine."""
from epocha.apps.agents.distortion import distort_information


class TestDistortInformation:
    def test_neutral_personality_no_distortion(self):
        """Traits between 0.3-0.7 produce no distortion."""
        content = "Marco argued with Elena."
        personality = {
            "neuroticism": 0.5, "agreeableness": 0.5,
            "openness": 0.5, "extraversion": 0.5,
            "conscientiousness": 0.5,
        }
        result = distort_information(content, personality)
        assert result == content

    def test_high_neuroticism_amplifies_negativity(self):
        """High neuroticism amplifies negative language."""
        content = "Marco argued with Elena."
        personality = {"neuroticism": 0.9}
        result = distort_information(content, personality)
        assert result != content
        assert "argued" not in result  # Should be replaced with stronger word

    def test_low_neuroticism_minimizes(self):
        """Low neuroticism softens language."""
        content = "Marco fought bitterly with Elena."
        personality = {"neuroticism": 0.1}
        result = distort_information(content, personality)
        assert "fought bitterly" not in result

    def test_high_agreeableness_softens(self):
        """High agreeableness softens conflict language."""
        content = "Marco betrayed Elena."
        personality = {"agreeableness": 0.9}
        result = distort_information(content, personality)
        assert "betrayed" not in result

    def test_low_agreeableness_exaggerates_conflict(self):
        """Low agreeableness exaggerates conflict."""
        content = "Marco argued with Elena."
        personality = {"agreeableness": 0.1}
        result = distort_information(content, personality)
        assert "argued" not in result

    def test_high_extraversion_exaggerates_scale(self):
        """High extraversion exaggerates scope."""
        content = "Someone complained about the food."
        personality = {"extraversion": 0.9}
        result = distort_information(content, personality)
        assert "someone" not in result.lower()

    def test_max_two_traits_applied(self):
        """Only the 2 most extreme traits apply, even if more are extreme."""
        content = "Marco argued with Elena."
        personality = {
            "neuroticism": 0.95,     # most extreme
            "agreeableness": 0.05,   # second most extreme
            "openness": 0.9,         # third -- should NOT apply
            "extraversion": 0.5,
            "conscientiousness": 0.5,
        }
        result = distort_information(content, personality)
        # Neuroticism and agreeableness should apply, openness should not.
        # Openness would add speculation ("perhaps because...") -- check it's absent
        assert "perhaps" not in result.lower()

    def test_empty_personality_no_distortion(self):
        """Missing personality traits default to neutral (no distortion)."""
        content = "Marco helped Elena."
        result = distort_information(content, {})
        assert result == content

    def test_distortion_strength_proportional_to_extremity(self):
        """Trait at 0.75 should distort less than trait at 0.95."""
        content = "Marco argued with Elena."
        mild = distort_information(content, {"neuroticism": 0.75})
        extreme = distort_information(content, {"neuroticism": 0.95})
        # Both should differ from original, but extreme should use stronger words
        assert mild != content
        assert extreme != content
        assert mild != extreme

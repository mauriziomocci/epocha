"""Tests for the belief filter -- decides whether an agent accepts incoming information."""
from epocha.apps.agents.belief import should_believe


class TestShouldBelieve:
    def test_trusted_friend_fresh_hearsay_accepted(self):
        """High reliability + strong relationship + average personality = accept."""
        result = should_believe(
            reliability=0.7,
            receiver_personality={"agreeableness": 0.5, "openness": 0.5},
            relationship_strength=0.8,
            relationship_sentiment=0.8,
        )
        assert result is True

    def test_stranger_third_hand_rumor_rejected(self):
        """Low reliability + no relationship + average personality = reject."""
        result = should_believe(
            reliability=0.3,
            receiver_personality={"agreeableness": 0.5, "openness": 0.5},
            relationship_strength=0.0,
            relationship_sentiment=0.0,
        )
        assert result is False

    def test_weak_rumor_gullible_agent_accepted(self):
        """Low reliability but very agreeable/open agent = accept."""
        result = should_believe(
            reliability=0.3,
            receiver_personality={"agreeableness": 0.9, "openness": 0.9},
            relationship_strength=0.3,
            relationship_sentiment=0.3,
        )
        assert result is True

    def test_reliable_news_skeptical_agent_accepted(self):
        """High reliability overcomes low personality factor."""
        result = should_believe(
            reliability=0.7,
            receiver_personality={"agreeableness": 0.2, "openness": 0.2},
            relationship_strength=0.5,
            relationship_sentiment=0.5,
        )
        assert result is True

    def test_no_relationship_uses_default_trust(self):
        """When strength and sentiment are both 0, trust defaults to stranger level."""
        result = should_believe(
            reliability=0.5,
            receiver_personality={"agreeableness": 0.5, "openness": 0.5},
            relationship_strength=0.0,
            relationship_sentiment=0.0,
        )
        # score = 0.5*0.4 + 0.0*0.3 + 0.5*0.3 = 0.20 + 0.0 + 0.15 = 0.35
        assert result is False

    def test_missing_personality_traits_use_defaults(self):
        """If personality dict is missing Big Five traits, defaults to 0.5."""
        result = should_believe(
            reliability=0.7,
            receiver_personality={},
            relationship_strength=0.5,
            relationship_sentiment=0.5,
        )
        # personality_factor = 0.5*0.6 + 0.5*0.4 = 0.5
        # rel_trust = (0.5 + 0.5) / 2 = 0.5
        # score = 0.7*0.4 + 0.5*0.3 + 0.5*0.3 = 0.28 + 0.15 + 0.15 = 0.58
        assert result is True

    def test_negative_sentiment_clamped_to_zero(self):
        """Negative sentiment should not increase trust (clamped to 0)."""
        result = should_believe(
            reliability=0.3,
            receiver_personality={"agreeableness": 0.5, "openness": 0.5},
            relationship_strength=0.5,
            relationship_sentiment=-0.8,
        )
        # rel_trust = (0.5 + max(0, -0.8)) / 2 = 0.5 / 2 = 0.25
        # score = 0.3*0.4 + 0.25*0.3 + 0.5*0.3 = 0.12 + 0.075 + 0.15 = 0.345
        assert result is False

    def test_exact_threshold_is_accepted(self):
        """Score exactly at threshold should be accepted (>=, not >)."""
        result = should_believe(
            reliability=0.4,
            receiver_personality={"agreeableness": 0.4, "openness": 0.4},
            relationship_strength=0.4,
            relationship_sentiment=0.4,
        )
        assert result is True

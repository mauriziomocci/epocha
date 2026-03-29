"""Tests for the Redis-based LLM rate limiter."""
from unittest.mock import MagicMock

from epocha.apps.llm_adapter.rate_limiter import RateLimiter


class TestRateLimiter:
    def setup_method(self):
        self.redis = MagicMock()
        self.limiter = RateLimiter(
            redis_client=self.redis,
            provider="openai",
            max_requests_per_minute=60,
        )

    def test_can_proceed_when_under_limit(self):
        self.redis.get.return_value = b"10"
        assert self.limiter.can_proceed() is True

    def test_cannot_proceed_when_at_limit(self):
        self.redis.get.return_value = b"60"
        assert self.limiter.can_proceed() is False

    def test_cannot_proceed_when_over_limit(self):
        self.redis.get.return_value = b"100"
        assert self.limiter.can_proceed() is False

    def test_can_proceed_when_no_key_exists(self):
        """First request ever — no counter in Redis yet."""
        self.redis.get.return_value = None
        assert self.limiter.can_proceed() is True

    def test_record_request_uses_pipeline(self):
        """Recording a request must use a Redis pipeline for atomicity."""
        mock_pipe = MagicMock()
        self.redis.pipeline.return_value = mock_pipe

        self.limiter.record_request()

        mock_pipe.incr.assert_called_once()
        mock_pipe.expire.assert_called_once()
        mock_pipe.execute.assert_called_once()

    def test_key_includes_provider_name(self):
        """The Redis key must be namespaced by provider to avoid collisions."""
        assert "openai" in self.limiter._key

    def test_different_providers_have_different_keys(self):
        limiter_gemini = RateLimiter(
            redis_client=self.redis,
            provider="gemini",
            max_requests_per_minute=30,
        )
        assert self.limiter._key != limiter_gemini._key

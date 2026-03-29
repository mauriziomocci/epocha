"""Redis-based rate limiting for LLM API calls.

Implements a sliding window counter per provider to respect API rate limits.
Each provider has its own Redis key with a TTL of 60 seconds, ensuring the
counter resets automatically after the window expires.

Reference: Redis INCR pattern for rate limiting.
https://redis.io/commands/incr/#pattern-rate-limiter-1
"""
from __future__ import annotations


class RateLimiter:
    """Sliding window rate limiter backed by Redis.

    Uses a single Redis key per provider with INCR + EXPIRE for atomic
    counting. The key auto-expires after TTL_SECONDS, creating a fixed
    window that resets every minute.
    """

    KEY_PREFIX = "epocha:ratelimit"
    TTL_SECONDS = 60

    def __init__(
        self,
        redis_client,
        provider: str,
        max_requests_per_minute: int = 50,
    ):
        self.redis = redis_client
        self.provider = provider
        self.max_rpm = max_requests_per_minute
        self._key = f"{self.KEY_PREFIX}:{provider}"

    def can_proceed(self) -> bool:
        """Check whether the next request is within the rate limit."""
        current = self.redis.get(self._key)
        if current is None:
            return True
        return int(current) < self.max_rpm

    def record_request(self) -> None:
        """Record a completed request atomically via pipeline.

        INCR creates the key if it does not exist (starting at 1).
        EXPIRE ensures the window resets after TTL_SECONDS.
        """
        pipe = self.redis.pipeline()
        pipe.incr(self._key)
        pipe.expire(self._key, self.TTL_SECONDS)
        pipe.execute()

"""Rate limiting for LLM calls via Redis."""


class RateLimiter:
    """Redis-based rate limiter to respect provider limits."""

    def __init__(self, redis_client, provider: str, max_requests_per_minute: int = 50):
        self.redis = redis_client
        self.provider = provider
        self.max_rpm = max_requests_per_minute

    def can_proceed(self) -> bool:
        """Check if the request can proceed."""
        raise NotImplementedError("To be implemented in MVP")

    def record_request(self):
        """Record a completed request."""
        raise NotImplementedError("To be implemented in MVP")

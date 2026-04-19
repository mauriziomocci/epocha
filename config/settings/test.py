"""Overrides for pytest — no async Celery, no Redis-backed channels.

Inherits database configuration from base (which uses DATABASE_URL from
the environment) so the same file works on developer laptop and in the
Docker Compose stack without hard-coding host/credentials.
"""
from .base import *  # noqa: F401, F403

SECRET_KEY = "test-secret-key"

# Run Celery tasks synchronously in tests. No broker/result-backend needed.
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
CELERY_BROKER_URL = "memory://"
CELERY_RESULT_BACKEND = "cache+memory://"

# Use the in-memory channel layer so tests never reach a real Redis service.
CHANNEL_LAYERS = {"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}

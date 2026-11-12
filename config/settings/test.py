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

# No test reaches a real LLM endpoint. The suite runs inside the same
# containers as the dashboard and inherits their environment, real keys
# included, so a test that patched the wrong factory sent a paid request with
# the developer's own chat key on every run (round 16 of the Plan 4 phase-6
# gate). With the keys blank, `OpenAIProvider` cannot be built at all, so an
# unpatched path fails at once instead of reaching the network. Guarded by
# `llm_adapter/tests/test_client.py`.
EPOCHA_LLM_API_KEY = ""
EPOCHA_LLM_BASE_URL = ""
EPOCHA_CHAT_LLM_API_KEY = ""
EPOCHA_CHAT_LLM_MODEL = ""
EPOCHA_CHAT_LLM_BASE_URL = ""

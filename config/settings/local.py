"""Overrides for local development."""
from .base import *  # noqa: F401, F403
from .base import env

DEBUG = True
SECRET_KEY = env("DJANGO_SECRET_KEY", default="local-dev-secret-key-change-me")
ALLOWED_HOSTS = ["localhost", "0.0.0.0", "127.0.0.1"]
CORS_ALLOW_ALL_ORIGINS = True

# Celery local: eager mode for debugging (optional)
# CELERY_TASK_ALWAYS_EAGER = True
